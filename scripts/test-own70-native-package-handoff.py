#!/usr/bin/env python3
"""OWN70 STEP 1: actual _70 -> staged exact .pkg FD9 rescue -> native pkg add.

ONE disposable OPNsense VM only. Never run on an owner appliance. The source
package is not an installer; its trusted, uninstalled service tree is used
only for the original FD9 recovery and for existing pkg-hook SERVICE_SCRIPT.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SERVICE_REL = "opnsense/scripts/OPNsense/Zapret"
SERVICE = Path("/usr/local") / SERVICE_REL / "zapret_service.sh"
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
PKG_NAME = "os-zapret2-restyle"
OLD_URL = ("https://github.com/Tolian82/os-zapret2-restyle/releases/"
           "download/v0.6.5_70/os-zapret2-restyle-0.6.5_70.pkg")
OLD_SHA256 = "18acb1793410c055820737c5a30eb9a317208f1aa6a70e7bbaccf1ad1c701644"
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class Refused(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refused(reason)


def run(argv, *, timeout=180, env=None):
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False, env=env)
    except (OSError, subprocess.SubprocessError):
        raise Refused("native_command_unavailable_or_timeout:" + argv[0]) from None


def require(argv, reason, *, timeout=180, env=None):
    result = run(argv, timeout=timeout, env=env)
    need(result.returncode == 0, reason + ":rc=" + str(result.returncode))
    return result.stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(pkg):
    return json.loads(require(
        ["/usr/bin/tar", "-xOf", str(pkg), "+MANIFEST"], "native_pkg_manifest"))


def request(mode):
    need(mode in ("list", "auto"), "invalid_test_mode")
    xml = ET.fromstring(Path("/conf/config.xml").read_bytes())
    tg = xml.find("./OPNsense/Zapret/hostlist/telegramips")
    baseline = "" if tg is None or tg.text is None else tg.text
    # First sealed List owner uses the native unchanged-saved candidate,
    # matching the real owner's prior base==candidate and empty field set.
    # The persisted List mode is set once with the original Model BEFORE
    # this transaction, never by detached guessed XML or a new writer.
    fields = {} if mode == "list" else {"hostlist": {"mode": "auto"}}
    payload = {"page": "strategies", "fields": fields,
               "sync": {"telegramips_baseline": baseline}}
    return base64.urlsafe_b64encode(json.dumps(
        payload, separators=(",", ":")).encode()).decode().rstrip("=")


def qualified_archive_member(names, key):
    """Accept exactly one harmless tar alias, without trusting write paths."""
    matches = []
    for name in names:
        candidate = (name[2:] if name.startswith("./")
                     else name[1:] if name.startswith("/")
                     else name)
        if candidate != key:
            continue
        need(not any(part in ("", ".", "..") for part in
                     name.removeprefix("./").removeprefix("/").split("/")),
             "unqualified_package_member_path")
        matches.append(name)
    need(len(matches) == 1, "missing_or_duplicated_exact_native_package_member")
    return matches[0]


def staged_source(pkg, root):
    """Read exact files from ONE .pkg; archive headers never select write paths.

    The source manifest and installed archive use absolute-looking tar names
    on some FreeBSD bsdtar versions. Never extract them as filesystem paths:
    read one named regular archive member into memory, require the exact
    trusted checkout bytes, then create the independently known destination.
    """
    need(root.is_dir() and not root.is_symlink() and
         root.stat().st_uid == 0 and stat.S_IMODE(root.stat().st_mode) == 0o700,
         "untrusted_staging_root")
    m = manifest(pkg)
    need(m.get("name") == PKG_NAME and m.get("abi") == "FreeBSD:15:amd64",
         "wrong_staged_native_manifest")
    names = require(["/usr/bin/tar", "-tf", str(pkg)],
                    "archive_index", timeout=40).splitlines()
    native = ROOT / "src" / SERVICE_REL
    api = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api"
    need(native.is_dir() and not native.is_symlink() and
         api.is_dir() and not api.is_symlink(),
         "untrusted_tracked_native_or_mvc_source")
    # The real original shared_apply_config.php loads apply_settings.php,
    # which requires MVC classes through relative __DIR__ directives.
    # A private service-only extraction is not executable from staging:
    # its saved native PHP entrypoint exits 255 without these classes.
    # Stage only package-owned API PHP files plus the original service tree.
    mvc = sorted(api.glob("*.php"))
    need(len(mvc) >= 12 and
         all(p.is_file() and not p.is_symlink() for p in mvc) and
         all((api / name).is_file() for name in (
             "SettingsApply.php", "DomainSetPolicyBridge.php",
             "IPSetPolicyBridge.php", "VoiceSettingsSnapshot.php",
             "VoiceModelValues.php", "WanRequirement.php")),
         "missing_same_package_mvc_dependencies")
    files = sorted([p for p in native.rglob("*") if p.is_file()] + mvc)
    need(len(files) >= 115, "incomplete_tracked_service_and_mvc_source")
    source_bytes = 0
    dest = root / "usr/local" / SERVICE_REL
    for source in files:
        need(not source.is_symlink() and
             stat.S_ISREG(source.lstat().st_mode),
             "foreign_tracked_source_type")
        rel = source.relative_to(ROOT / "src").as_posix()
        key = "usr/local/" + rel
        member = qualified_archive_member(names, key)
        need("/usr/local/" + rel in m.get("files", {}),
             "unmanifested_exact_native_package_member")
        # Use tar ONLY for -xOf data extraction; no filesystem path from the
        # package is ever passed to tar -xf, mkdir, rename or chmod.
        item = subprocess.run(["/usr/bin/tar", "-xOf", str(pkg), member],
                              capture_output=True, timeout=18, check=False)
        need(item.returncode == 0, "native_package_member_read_refused")
        source_data = source.read_bytes()
        source_bytes += len(source_data)
        need(len(source_data) <= 4 * 1024 * 1024 and
             source_bytes <= 32 * 1024 * 1024 and
             item.stdout == source_data, "native_package_source_bytes_differ")
        target = root / "usr/local" / rel
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        mode = stat.S_IMODE(source.stat().st_mode)
        need(mode in (0o644, 0o755) and
             not target.exists() and not target.is_symlink(),
             "unqualified_original_native_source_mode")
        with target.open("xb") as stream:
            stream.write(item.stdout)
            stream.flush()
            os.fsync(stream.fileno())
        target.chmod(mode)
        need(target.stat().st_uid == 0 and target.stat().st_nlink == 1 and
             sha(target) == sha(source), "staged_native_source_changed")
    need((dest / "zapret_service.sh").is_file() and
         stat.S_IMODE((dest / "zapret_service.sh").stat().st_mode) == 0o755 and
         (dest / "python_runtime.sh").is_file() and
         stat.S_IMODE((dest / "python_runtime.sh").stat().st_mode) == 0o755,
         "staged_original_service_or_interpreter_missing")
    return dest


def recovered_status(stage, action, *, optin=False, timeout=180):
    environment = dict(os.environ)
    environment.update({
        "SCRIPT_DIR": str(stage),
        "BACKEND_DIR": str(stage / "backend"),
        "PYTHON_RUNTIME": str(stage / "python_runtime.sh"),
        "ZAPRET_INSTALLED_SUPERVISOR_LOOP":
            str(SERVICE.parent / "supervisor_loop.sh"),
    })
    if optin:
        environment["ZAPRET_OWNER_REVIEW_RECOVERY"] = "1"
    else:
        environment.pop("ZAPRET_OWNER_REVIEW_RECOVERY", None)
    return run(["/bin/sh", str(stage / "zapret_service.sh"), action],
               env=environment, timeout=timeout)


def set_guest_list_mode():
    """Disposable ONLY: normal native Config/Model setup before any Apply."""
    php = r'''require_once("script/load_phalcon.php");
$c=\OPNsense\Core\Config::getInstance();$c->lock();try{
$m=new \OPNsense\Zapret\Zapret();
if(!$m->setNodeByReference("hostlist.mode","list") ||
 count($m->performValidation(false)) || !$m->serializeToConfig(false,true))
 throw new \RuntimeException("disposable-list-model-invalid");
$c->save(["description"=>"OWN70 disposable initial List mode"]);
}finally{$c->unlock();}'''
    require(["/usr/local/bin/php", "-r", php],
            "disposable_native_list_mode_setup_failed", timeout=35)


def native():
    import platform
    need(os.geteuid() == 0 and platform.system() == "FreeBSD" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_OWN70_NATIVE_BRIDGE") == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "disposable_opnsense_root_only")
    builder_spec = importlib.util.spec_from_file_location(
        "own70_native_pkg_builder", HERE / "native-opnsense-package.py")
    native_builder = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(native_builder)
    native_builder.gate()
    need(run(["pkg", "info", "-e", PKG_NAME], timeout=20).returncode == 1,
         "disposable_guest_already_has_plugin")
    result = native_builder.build()
    pkg = ROOT / result["output"]
    need(sha(pkg) == result["real_native_pkg"]["sha256"] and
         manifest(pkg).get("version") == (
             (ROOT / "VERSION").read_text().strip() + "_" +
             re.search(r"PLUGIN_REVISION=\s*(\d+)", (ROOT / "Makefile").read_text()).group(1)),
         "candidate_native_pkg_not_exact")

    old = Path("/root/os-zapret2-restyle-0.6.5_70.pkg")
    require(["fetch", "-o", str(old), OLD_URL], "published_old_archive_fetch",
            timeout=100)
    need(sha(old) == OLD_SHA256 and
         manifest(old).get("version") == "0.6.5_70" and
         manifest(old).get("abi") == "FreeBSD:15:amd64",
         "historical_owner_pkg_sha_or_abi_changed")
    require(["pkg", "add", "-f", str(old)], "old_pkg_genuine_install",
            timeout=180)
    need(run([str(SERVICE), "status"], timeout=20).returncode == 1,
         "old_installed_cold_status_missing")

    def load_hyphenated(filename, identity):
        spec = importlib.util.spec_from_file_location(identity, HERE / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    witness = load_hyphenated("p5b2b-native-witness.py", "own70_p5b_fixture")
    witness.set_guest_lo0()
    set_guest_list_mode()
    g03 = load_hyphenated("stage2-opnsense-g03-first-install.py", "own70_g03_fixture")
    status = g03.dispatch_and_poll()
    need(status["installed"] == "1", "old_upstream_install_refused")
    # The installed G03 runtime is deliberately STOPPED. First commit the
    # ordinary List Strategies candidate through original configd; do not
    # insert a legacy Start that has no sealed shared owner predecessor.
    need(run([str(SERVICE), "status"], timeout=20).returncode == 1,
         "old_native_cold_list_precondition_missing")

    # One genuine ordinary List common owner must exist as predecessor.
    old_list = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                    "strategies", request("list")], timeout=240)
    if old_list.returncode != 0 or "applied-id=" not in old_list.stdout:
        # A preflight rejection returns shell status zero. Do not interpret
        # it as successful first Apply or expose user Config/argv in CI.
        marker = re.search(r"preflight-rejected=[a-z-]{2,64}",
                           old_list.stdout)
        result = marker.group(0) if marker else "unqualified"
        phase = "no-journal"
        if JOURNAL.is_file():
            try:
                phase = str(json.loads(JOURNAL.read_bytes()).get("phase", "invalid"))
            except (OSError, ValueError):
                phase = "unreadable"
        print("OWN70_FIRST_LIST_DIAGNOSTIC=" + json.dumps({
            "native_configd_rc": old_list.returncode,
            "result_marker": result,
            "journal_phase": phase,
            "service_stopped_before_list": True
        }, sort_keys=True), flush=True)
        raise Refused("old_installed_list_owner_not_committed")
    baseline = json.loads(JOURNAL.read_bytes())
    need(baseline.get("phase") == "committed" and
         run([str(SERVICE), "status"], timeout=20).returncode == 0,
         "old_list_not_running_committed")
    base_id = baseline["detail"]["id"]

    # This is the owner's actual GUI/configd entrypoint and published _70
    # code; never fabricate journal/epoch or forcibly kill a real process.
    broken = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                  "strategies", request("auto")], timeout=240)
    state = json.loads(JOURNAL.read_bytes())
    generation = state["detail"]["id"]
    need(state.get("previous", {}).get("id") == base_id and
         state["detail"]["changed_fields"] == ["hostlist.mode"] and
         HEX32.fullmatch(generation), "native_old_auto_did_not_change_mode")
    reproduced = (broken.returncode != 0)
    if reproduced:
        need(state.get("phase") == "requires-review" and
             (EPOCHS / generation / "pretraffic.json").is_file() and
             not (EPOCHS / generation / "epoch.json").exists() and
             run([str(SERVICE), "status"], timeout=20).returncode == 2,
             "published_old_failure_did_not_match_observed_owner")
    else:
        # The fixture may produce shorter argv than the owner's real 2410
        # bytes. A successful ordinary Auto is NOT evidence of reviewed
        # recovery: qualify only the staged-hook RUNNING upgrade in this run.
        need(state.get("phase") == "committed" and
             (EPOCHS / generation / "epoch.json").is_file() and
             run([str(SERVICE), "status"], timeout=20).returncode == 0,
             "old_auto_was_neither_healthy_nor_reviewed")

    print("OWN70_OLD_AUTO_RESULT=" + json.dumps({
        "requires_review_reproduced": reproduced,
        "old_journal_phase": state["phase"],
        "original_pretraffic_present": (EPOCHS / generation / "pretraffic.json").is_file(),
        "original_epoch_present": (EPOCHS / generation / "epoch.json").is_file(),
    }, sort_keys=True), flush=True)
    before_config = sha(Path("/conf/config.xml"))
    engine_pid = Path("/var/run/dvtws2.pid").read_text().strip().split()[0]
    need(engine_pid.isdecimal() and
         (ACTIVE / "auto-detect-generation.json").is_file(),
         "original_engine_or_map_not_running")

    # Use the exact SAME future .pkg, without installing its files,
    # replacing the old service or skipping any pkg hook.
    with tempfile.TemporaryDirectory(prefix="zapret-pkg-bridge-", dir="/root") as tmp:
        root = Path(tmp)
        os.chmod(root, 0o700)
        stage = staged_source(pkg, root)
        denied = recovered_status(stage, "shared-apply-recover-reviewed-native")
        need(denied.returncode == 75, "root_optin_gate_not_enforced")
        if reproduced:
            need(not (EPOCHS / generation / "epoch.json").exists(),
                 "denied_root_optin_mutated_epoch")
            rescue = recovered_status(stage, "shared-apply-recover-reviewed-native",
                                      optin=True, timeout=150)
            need(rescue.returncode == 0 and
                 "recovered-reviewed-native-id=" + generation in rescue.stdout and
                 (EPOCHS / generation / "epoch.json").is_file() and
                 json.loads(JOURNAL.read_bytes())["phase"] == "committed" and
                 sha(Path("/conf/config.xml")) == before_config,
                 "staged_package_original_fd9_recovery_unproven")

        # Establish independent OLD and NEW-staged status before pkg. A
        # pre-install status=1 will silently take the "already STOPPED" path
        # and preserve a stale dvtws2 even though an outer status is RUNNING.
        # Do not infer hook execution from final pkg/version alone.
        source_status = run([str(SERVICE), "status"], timeout=25)
        staged_status = recovered_status(stage, "status", timeout=25)
        before_markers = {
            "replacement": Path(
                "/var/run/zapret2-restyle/pkg-replacement.restart").exists(),
            "upgrade": Path(
                "/var/run/zapret2-restyle/pkg-upgrade.restart").exists(),
        }
        print("OWN70_NATIVE_PKG_PREFLIGHT=" + json.dumps({
            "installed_service_status_rc": source_status.returncode,
            "staged_service_status_rc": staged_status.returncode,
            "installed_status_exact_running":
                source_status.stdout.strip() == "zapret is running",
            "staged_status_exact_running":
                staged_status.stdout.strip() == "zapret is running",
            "restart_markers_before_pkg": before_markers,
            "old_engine_pid_present": bool(engine_pid),
            "old_generation_phase_committed":
                json.loads(JOURNAL.read_bytes())["phase"] == "committed",
        }, sort_keys=True), flush=True)
        need(source_status.returncode == staged_status.returncode == 0 and
             source_status.stdout.strip() == "zapret is running" and
             staged_status.stdout.strip() == "zapret is running" and
             not any(before_markers.values()),
             "native_prepackage_running_owner_not_qualified")
        # The original Stop requires a stronger running-epoch proof
        # than GUI status. Probe exactly its pre-retire read-only gate under
        # the ORIGINAL held FD9 and queue lock without any service signal,
        # Config/IPFW change or new lifecycle owner.
        sys.path.insert(0, str(stage / "backend"))
        witness.hold_fd9()
        try:
            pre = subprocess.run([
                str(stage / "python_runtime.sh"),
                str(stage / "backend" / "auto_detect_minute.py"),
                "--pre-retire",
            ], capture_output=True, text=True, timeout=35,
               pass_fds=(9,), check=False)
            # Run the unchanged original Stop's OTHER read-only validators
            # under the SAME original FD9 before ever asking pkg to mutate
            # installed files. These are production entrypoints/functions,
            # not duplicated Config/IPFW parsers or new on-disk witnesses.
            work = Path("/var/db/zapret2/shared-work") / generation
            checks = {
                "sealed_bundle": [
                    str(stage / "python_runtime.sh"),
                    str(stage / "backend" / "shared_apply_seal.py"),
                    "verify", generation,
                ],
                "saved_original_config": [
                    "/usr/local/bin/php", str(stage / "shared_apply_config.php"),
                    "saved", generation, "strategies",
                ],
                "active_tree_exact": [
                    "/bin/sh", "-c",
                    'common_error() { :; }; . "$1"; atomic_verify_tree "$2" "$3"',
                    "own70-native-tree",
                    str(stage / "backend" / "atomic.sh"),
                    str(work / "release"), str(ACTIVE),
                ],
                "original_shell_child_and_monitor": [
                    "/bin/sh", "-c",
                    ('SCRIPT_DIR="$1"; BACKEND_DIR="$1/backend"; '
                     'DVTWS_BIN="$2"; SUPERVISOR_LOOP="$3"; '
                     '. "$BACKEND_DIR/common.sh"; '
                     '. "$BACKEND_DIR/launcher.sh"; '
                     '. "$BACKEND_DIR/supervisor.sh"; '
                     'launcher_is_running /var/run/dvtws2.pid && '
                     'supervisor_is_running /var/run/zapret2-supervisor-monitor.pid'),
                    "own70-native-real-process",
                    str(stage),
                    "/usr/local/etc/zapret2/binaries/my/dvtws2",
                    str(SERVICE.parent / "supervisor_loop.sh"),
                ],
                "original_observer_authorized": [
                    str(stage / "python_runtime.sh"),
                    str(stage / "backend" / "auto_detect_post_drop.py"),
                    "authorize", str(ACTIVE),
                ],
                "committed_original_ipfw": [
                    str(stage / "python_runtime.sh"),
                    str(stage / "backend" / "voice_ipfw_adapter.py"),
                    "shared", "verify", "-", str(ACTIVE),
                ],
            }
            proof = {}
            for name, command in checks.items():
                observation = subprocess.run(command, capture_output=True,
                                             text=True, timeout=35,
                                             pass_fds=(9,), check=False)
                valid = observation.returncode == 0
                if name == "saved_original_config" and valid:
                    try:
                        valid = json.loads(observation.stdout).get("result") == "committed"
                    except (TypeError, ValueError):
                        valid = False
                proof[name] = {"rc": observation.returncode, "verified": valid}
        finally:
            os.close(9)
        label = re.search(r"auto-detect-retire-refused=([A-Za-z]{3,50})",
                          pre.stderr)
        print("OWN70_NATIVE_STOP_PREFLIGHT=" + json.dumps({
            "original_fd9_pre_retire_rc": pre.returncode,
            "pre_retire_running_attested":
                pre.stdout.strip() == "auto-detect-retire=original-running-attested",
            "pre_retire_exception_class": label.group(1) if label else "none",
            "original_readonly_stop_gates": proof,
        }, sort_keys=True), flush=True)
        need(pre.returncode == 0 and
             pre.stdout.strip() == "auto-detect-retire=original-running-attested",
             "native_original_running_epoch_pre_retirement_refused")
        need(all(item["verified"] for item in proof.values()),
             "original_stop_readonly_gate_refused_before_pkg")
        # Both original hook generations expose SERVICE_SCRIPT. Whether
        # genuine FreeBSD pkg forwards that environment is what this
        # disposable native test must PROVE, not assume. Use the same real
        # pkg add -f with the pkg(8) global -d diagnostics enabled.
        override = dict(os.environ)
        override.update({
            "SERVICE_SCRIPT": str(stage / "zapret_service.sh"),
            "SCRIPT_DIR": str(stage),
            "BACKEND_DIR": str(stage / "backend"),
            "PYTHON_RUNTIME": str(stage / "python_runtime.sh"),
            "ZAPRET_INSTALLED_SUPERVISOR_LOOP":
                str(SERVICE.parent / "supervisor_loop.sh"),
        })
        update = run(["pkg", "-d", "add", "-f", str(pkg)],
                     timeout=210, env=override)
        debug = (update.stdout + "\n" + update.stderr).lower()
        phases = {
            label: (label in debug) for label in
            ("pre-install", "pre-deinstall", "post-install")
        }
        hook = {
            "new_preinstall_entered": "zapret-pkg-preinstall-entered=1" in debug,
            "new_preinstall_saw_running": "zapret-pkg-preinstall-status=0" in debug,
            "new_preinstall_saw_stopped": "zapret-pkg-preinstall-status=1" in debug,
            "new_preinstall_stop_verified":
                "zapret-pkg-preinstall-stop-verified=1" in debug,
            "new_preinstall_stop_command_rc":
                (int(re.search(r"zapret-pkg-preinstall-stop-rc=(\d+)",debug).group(1))
                 if re.search(r"zapret-pkg-preinstall-stop-rc=(\d+)",debug)
                 else "missing"),
            "new_preinstall_poststop_status":
                (int(re.search(r"zapret-pkg-preinstall-poststop-status=(\d+)",debug).group(1))
                 if re.search(r"zapret-pkg-preinstall-poststop-status=(\d+)",debug)
                 else "missing"),
            "new_postinstall_restart_intent":
                ("true" if "zapret-pkg-postinstall-restart-intent=1" in debug
                 else "false" if
                 "zapret-pkg-postinstall-restart-intent=0" in debug
                 else "missing"),
        }
        print("OWN70_NATIVE_PKG_DIAGNOSTIC=" + json.dumps({
            "native_pkg_rc": update.returncode,
            "pkg_debug_mentions_phases": phases,
            "native_original_hook_receipts": hook,
            "native_pkg_reports_stop_failure":
                "zapret service could not be stopped; package replacement aborted" in debug,
            "native_pkg_reports_poststop_failure":
                "zapret service still owns runtime state; package replacement aborted" in debug,
            "pkg_reports_successful_extract": "extracting" in debug,
            "pkg_debug_output_bounded": len(debug) <= 512 * 1024,
        }, sort_keys=True), flush=True)
        need(update.returncode == 0 and len(debug) <= 512 * 1024,
             "native_old_hook_handoff_refused:" + str(update.returncode))
    version = require(["pkg", "query", "%v", PKG_NAME],
                      "installed_successor_version")
    native_status = run([str(SERVICE), "status"], timeout=30)
    saved_config_preserved = sha(Path("/conf/config.xml")) == before_config
    marker_present = Path(
        "/var/run/zapret2-restyle/pkg-replacement.restart").exists()
    old_retired_before_assert = (EPOCHS / generation / "retired.json").is_file()
    current_record = json.loads(JOURNAL.read_bytes())
    current_id = current_record.get("detail", {}).get("id", "")
    post_output = update.stdout + "\n" + update.stderr
    diag = {
        "successor_pkg_version_qualified": version == manifest(pkg)["version"],
        "saved_config_unchanged": saved_config_preserved,
        "status_rc_after_postinstall": native_status.returncode,
        "status_exact_running_after_postinstall":
            native_status.stdout.strip() == "zapret is running",
        "replacement_restart_marker_present": marker_present,
        "old_retired_epoch_present": old_retired_before_assert,
        "new_operation_id_differs_from_old": current_id != generation,
        "current_journal_phase": current_record.get("phase", "invalid"),
        "postinstall_reports_start_failure":
            "zapret service could not be started after package replacement" in post_output,
        "postinstall_reports_status_failure":
            "zapret service did not reach running state after package replacement" in post_output,
        "postinstall_reports_template_failure":
            "OPNsense Zapret template could not be rendered after plugin installation" in post_output,
        "postinstall_reports_registration_failure":
            "os-zapret2-restyle could not be registered" in post_output,
        "pkg_reports_execute_error": "Execute error" in post_output,
    }
    print("OWN70_NATIVE_POSTINSTALL_STATUS=" + json.dumps(diag, sort_keys=True),
          flush=True)
    need(diag["successor_pkg_version_qualified"] and
         saved_config_preserved and native_status.returncode == 0 and
         not marker_present,
         "native_pkg_successor_did_not_resume")
    new = current_record
    new_id = new.get("detail", {}).get("id", "")
    replacement_pid = Path("/var/run/dvtws2.pid")
    after_pid = (replacement_pid.read_text().strip().split()[0]
                 if replacement_pid.is_file() and not replacement_pid.is_symlink()
                 else "missing")
    old_retired = (EPOCHS / generation / "retired.json").is_file()
    new_epoch = (HEX32.fullmatch(new_id) is not None and
                 (EPOCHS / new_id / "epoch.json").is_file())
    same_engine = after_pid == engine_pid
    result = {
        "old_requires_review_reproduced": reproduced,
        "original_generation_replaced": new_id != generation,
        "old_original_epoch_retired": old_retired,
        "replacement_epoch_present": new_epoch,
        "original_engine_pid_survived_pkg": same_engine,
        "new_journal_phase": new.get("phase", "invalid"),
        "installed_version_matched": version == manifest(pkg)["version"],
        "native_postinstall_message_seen": "os-zapret2-restyle was installed." in update.stdout,
        "native_postinstall_restart_marker_consumed":
            not Path("/var/run/zapret2-restyle/pkg-replacement.restart").exists(),
    }
    print("OWN70_NATIVE_HOOK_OUTCOME=" + json.dumps(result, sort_keys=True),
          flush=True)
    need(new["phase"] == "committed" and new_id != generation and
         old_retired and new_epoch and not same_engine,
         "old_auto_epoch_not_retired_or_successor_not_committed")
    print("OWN70_NATIVE_BRIDGE=" + json.dumps({
        "result": ("PASS_REAL_OLD_AUTO_FAIL_STAGED_RESCUE_PKG_ADD_RUNNING"
                   if reproduced else
                   "PASS_REAL_OLD_AUTO_RUNNING_STAGED_HOOK_PKG_ADD_ONLY"),
        "old_pkg_sha256": OLD_SHA256,
        "successor_pkg_sha256": sha(pkg),
        "old_requires_review_reproduced": reproduced,
        "original_fd9_epoch_completed": reproduced,
        "original_hook_source_bytes_unchanged": True,
        "native_pkg_add_completed": True,
        "old_auto_epoch_retired": True,
        "new_auto_epoch_committed": True,
        "saved_config_preserved": True,
        "new_service_running": True,
        "owner_appliance_modified": False,
    }, sort_keys=True))


def self_test():
    key = "usr/local/opnsense/scripts/OPNsense/Zapret/a.py"
    for prefix in ("", "./", "/"):
        need(qualified_archive_member([prefix + key], key) == prefix + key,
             "valid_original_native_tar_alias_rejected")
    for entries in ((key, "./" + key),
                    ("../../" + key,),
                    ("/../" + key,),
                    (key + ".foreign",)):
        try:
            qualified_archive_member(list(entries), key)
        except Refused:
            pass
        else:
            raise Refused("ambiguous_or_foreign_tar_alias_accepted")
    php_bridge = (ROOT / "src" / SERVICE_REL / "apply_settings.php").read_text()
    for name in ("SettingsApply.php", "DomainSetPolicyBridge.php",
                 "IPSetPolicyBridge.php"):
        need(("/Api/" + name) in php_bridge and
             (ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api" /
              name).is_file(), "private_staging_php_relative_dependency_missing")
    source = (ROOT / "src" / SERVICE_REL / "zapret_service.sh").read_text()
    need('ZAPRET_INSTALLED_SUPERVISOR_LOOP' in source and
         'unqualified native supervisor identity path' in source and
         '/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh' in source,
         "canonical_installed_supervisor_identity_override_missing")
    print("OWN70_NATIVE_BRIDGE_SOURCE=PASS")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["--native"]:
            native()
        else:
            raise Refused("explicit_self_test_or_disposable_native_required")
    except (OSError, ValueError, TypeError, KeyError, Refused) as exc:
        print("OWN70_NATIVE_BRIDGE=REFUSED:" + str(exc), file=sys.stderr)
        raise SystemExit(2)
