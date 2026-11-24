#!/usr/bin/env python3
"""S05e2: execute original Apply runtime shell and audit private GUI source path."""
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
runtime = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh").read_text()
firewall = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh").read_text()
api = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api"
settings = (api / "SettingsController.php").read_text()
voice = (api / "VoiceController.php").read_text()
general = (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
voice_gui = (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt").read_text()
service = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()

def need(ok, case):
    if not ok:
        raise SystemExit("S05E2_REFUSED=" + case)

def actual(name):
    a = runtime.index(name + "()\n{")
    return runtime[a:runtime.index("\n}\n", a)+2]

# Exercise the ACTUAL wrapper with a separate Python exit/marker. The wrapper
# must keep the fixed receipt in shell scope and never echo untrusted stdout.
def actual_firewall():
    a = firewall.index("firewall_shared_runtime()\n{")
    return firewall[a:firewall.index("\n}\n", a)+2]

with tempfile.TemporaryDirectory() as temp:
    fake = Path(temp) / "fake-python"
    fake.write_text("""#!/bin/sh
case "$FAKE_RESULT" in
    typed) printf '%s\\n' 'ipfw-attach-failure=rule-add-rejected'; exit 1 ;;
    extra) printf '%s\\n' 'ipfw-attach-failure=rule-add-rejected private'; exit 1 ;;
    generic) exit 1 ;;
    success) exit 0 ;;
esac
""")
    fake.chmod(0o700)
    for response, expected in (("typed", "rule-add-rejected"),
                               ("extra", ""), ("generic", ""), ("success", "")):
        fixture = (actual_firewall() + "\n" +
                   "PYTHON_BIN=" + shlex.quote(str(fake)) + "\n" +
                   "BACKEND_DIR=/safe\nFAKE_RESULT=" + response + "\n" +
                   "export FAKE_RESULT\n" +
                   'firewall_shared_runtime install /old /new; rc=$?\n' +
                   'printf "cause=%s;rc=%s\\n" "$FIREWALL_SHARED_ATTACH_CAUSE" "$rc"\n')
        res = subprocess.run(["/bin/sh"], input=fixture, capture_output=True,
                             text=True, timeout=5)
        need(res.returncode == 0 and res.stdout.endswith(
            "cause={};rc={}\n".format(expected, 0 if response == "success" else 1)),
            "REAL_WRAPPER_" + response)

source = "\n".join(actual(n) for n in (
    "apply_runtime_clear", "apply_runtime_restore", "apply_runtime_abort",
    "apply_runtime_activate",
))
mark = "ipfw-attach-failure=rule-add-rejected"
need(all(mark in s for s in (firewall, service, settings, voice)), "ONE_FIXED_CAUSE_CHAIN")
need(all("ipfw-attach-failed" in s for s in (settings, voice, general, voice_gui)),
     "GUI_ALLOWED_CAUSE")
need(all("IPFW отклонил правило" in s for s in (general, voice_gui)),
     "RUSSIAN_LOCALIZATION")
need("record-ipfw-attach" in service and "record-ipfw-attach" not in runtime,
     "ONE_ORIGINAL_FD9_WRITER")

with tempfile.TemporaryDirectory() as tmp:
    active = Path(tmp) / "active"
    active.mkdir()
    (active / "dvtws.args").write_text("--filter-tcp=443\n")
    for mode, verify_error, restore_error, expected in (
        ("typed", "0", "0", (1, "rule-add-rejected")),
        ("generic", "0", "0", (1, "")),
        ("contaminated", "0", "0", (1, "")),
        ("typed", "1", "0", (70, "")),
        ("typed", "0", "1", (70, "")),
        ("success", "0", "0", (0, "")),
    ):
        stubs = """
ACTIVE_DIR=__ACTIVE__
DVTWS_BIN=/test/dvtws2
CHILD_PIDFILE=/test/dvtws2.pid
DVTWS_LOG=/test/log
MODE=__MODE__
VERIFY_ERROR=__VERIFY__
RESTORE_ERROR=__RESTORE__
apply_runtime_preflight() {
    APPLY_CANDIDATE=$1
    APPLY_NEW_RUNNING=$2
    APPLY_OLD_RUNNING=0
    APPLY_PHASE=prepared
    APPLY_BACKUP=
    APPLY_OLD=-
    APPLY_NEW=-
    APPLY_IPFW_INSTALLED=0
    return 0
}
atomic_install_tree() { printf '%s\\n' /test/backup; }
atomic_restore_tree() { [ "$RESTORE_ERROR" != 1 ]; }
supervisor_stop() { return 0; }
supervisor_start() { return 0; }
launcher_stop() { return 0; }
apply_runtime_original_launcher_once() { return 0; }
common_error() { :; }
firewall_shared_runtime() {
    case "$1" in
        install)
            case "$MODE" in
                typed) FIREWALL_SHARED_ATTACH_CAUSE=rule-add-rejected; return 1 ;;
                generic) FIREWALL_SHARED_ATTACH_CAUSE=; return 1 ;;
                contaminated) FIREWALL_SHARED_ATTACH_CAUSE=; return 1 ;;
                success) FIREWALL_SHARED_ATTACH_CAUSE=; return 0 ;;
            esac ;;
        verify) [ "$VERIFY_ERROR" != 1 ] ;;
        verify-staged) return 0 ;;
        *) return 0 ;;
    esac
}
"""
        stubs = (stubs.replace("__ACTIVE__", shlex.quote(str(active)))
                 .replace("__MODE__", mode)
                 .replace("__VERIFY__", verify_error)
                 .replace("__RESTORE__", restore_error))
        script = (source + "\n" + stubs +
                  "\nif apply_runtime_activate /test/candidate 1; then code=0; else code=$?; fi\n" +
                  'printf "rc=%s;cause=%s\\n" "$code" "$APPLY_IPFW_ATTACH_FAILURE"\n')
        proc = subprocess.run(["/bin/sh"], input=script, capture_output=True,
                              text=True, timeout=5)
        need(proc.returncode == 0, "ACTUAL_FUNCTION_EXEC_" + mode)
        need(proc.stdout.endswith("rc={};cause={}\n".format(*expected)),
             "ACTUAL_FUNCTION_CAUSE_" + mode + "_" + verify_error + restore_error)
print("S05E2_ACTUAL_SHELL_CAUSE_RU_EN_SOURCE=PASS")
