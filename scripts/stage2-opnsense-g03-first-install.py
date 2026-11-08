#!/usr/bin/env python3
"""G03 real configd → GUI-selected upstream first-install on disposable OPNsense."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle")
LAUNCHER = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh")
RELEASE = "v1.0.7"


class Refusal(Exception):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def run(argv, timeout=45):
    return subprocess.run(argv, text=True, capture_output=True,
                          timeout=timeout, check=False)


def status():
    p = run([str(LAUNCHER), "status"])
    need(p.returncode == 0, "G03_RUNTIME_STATUS_FAILED")
    data = dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)
    need(set(data) >= {"installed", "service", "version", "setup", "busy"},
         "G03_RUNTIME_STATUS_FIELDS_MISSING")
    return data


def dispatch_and_poll():
    # The actual selected-release action used by ServiceController.php.
    response = run(["/usr/local/sbin/configctl", "zapret", "setup_install", RELEASE])
    need(response.returncode == 0 and response.stdout.strip() == "OK",
         "G03_NATIVE_CONFIGD_DISPATCH_FAILED:" + response.stderr[-250:])
    deadline = time.monotonic() + 300
    saw_busy = False
    while time.monotonic() < deadline:
        current = status()
        saw_busy |= current["busy"] == "1" or current["setup"] == "installing"
        if (current["busy"] == "0" and current["setup"] == "ready" and
            current["installed"] == "1" and current["service"] == "stopped" and
            current["version"] == RELEASE and saw_busy):
            return current
        if current["busy"] == "0" and current["setup"] == "failed" and saw_busy:
            raise Refusal("G03_SETUP_WORKER_REPORTED_FAILURE")
        time.sleep(1)
    raise Refusal("G03_INSTALL_DID_NOT_REACH_VERIFIED_READY_STOPPED")


def native_template_snapshot():
    """Stock configd may have rendered three non-engine outputs already."""
    names = {"zapret.conf", "hostlist.txt", "hostlist-exclude.txt"}
    need(not ROOT.is_symlink(), "G03_UPSTREAM_ROOT_IS_SYMLINK")
    if not ROOT.exists():
        return {}
    need(ROOT.is_dir(), "G03_UPSTREAM_ROOT_NOT_DIRECTORY")
    found = {}
    for p in ROOT.iterdir():
        need(p.name in names and p.is_file() and not p.is_symlink(),
             "G03_FOREIGN_UPSTREAM_ROOT_ENTRY:" + p.name)
        found[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return found


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "G03_DISPOSABLE_OPNSENSE_ONLY")
    need(Path("/usr/local/opnsense").is_dir() and LAUNCHER.is_file(),
         "G03_NOT_AN_INSTALLED_OPNSENSE_PLUGIN")
    template_before = native_template_snapshot()
    need(not (ROOT / ".git").exists() and
         not (ROOT / "binaries/my/dvtws2").exists(),
         "G03_ALREADY_HAS_UPSTREAM_ENGINE")
    need(not (STATE / "runtime.release").exists() and
         not (STATE / "first-install.intent").exists() and
         not (STATE / "runtime-rollback").exists(),
         "G03_OLD_RELEASE_OR_RECOVERY_PRESENT")
    initial = status()
    need(initial["installed"] == "0" and initial["busy"] == "0",
         "G03_ENGINE_ALREADY_INSTALLED")
    cfg = Path("/conf/config.xml")
    need(cfg.is_file() and not cfg.is_symlink(), "G03_CONFIG_MISSING")
    config_before = hashlib.sha256(cfg.read_bytes()).hexdigest()
    # A freshly installed disposable OPNsense guest may not have loaded
    # the IPFW kernel module yet. That is an acceptable baseline: this
    # first-runtime setup must not activate IPFW or create rules by itself.
    ipfw_before = run(["/sbin/ipfw", "list"], timeout=15)
    module_before = run(["/sbin/kldstat", "-n", "ipfw"], timeout=15)

    first = dispatch_and_poll()
    need((ROOT / "binaries/my/dvtws2").is_file() and
         os.access(ROOT / "binaries/my/dvtws2", os.X_OK),
         "G03_COMPILED_DVTWS2_MISSING")
    for relative, target in {
        "nfq2/dvtws2": "../binaries/my/dvtws2",
        "ip2net/ip2net": "../binaries/my/ip2net",
        "mdig/mdig": "../binaries/my/mdig",
    }.items():
        symlink = ROOT / relative
        need(symlink.is_symlink() and os.readlink(symlink) == target,
             "G03_EXPECTED_COMPILER_LINK_MISSING_OR_UNSAFE:" + relative)
    commit = run(["/usr/local/bin/git", "-C", str(ROOT), "rev-parse", "HEAD"])
    tag = run(["/usr/local/bin/git", "-C", str(ROOT), "rev-parse",
               "refs/tags/" + RELEASE + "^{commit}"])
    need(commit.returncode == 0 and tag.returncode == 0 and
         commit.stdout.strip() == tag.stdout.strip(),
         "G03_GIT_TARGET_NOT_EXACT_RELEASE")
    need((STATE / "runtime.release").read_text().strip() == RELEASE,
         "G03_COMMITTED_RELEASE_MARKER_MISSING")
    need(not Path(str(ROOT) + ".first-install").exists() and
         not (STATE / "first-install.intent").exists() and
         not (STATE / "runtime-rollback").exists(),
         "G03_FIRST_INSTALL_RESIDUE")
    for name, expected in template_before.items():
        candidate = ROOT / name
        need(candidate.is_file() and not candidate.is_symlink() and
             hashlib.sha256(candidate.read_bytes()).hexdigest() == expected,
             "G03_STOCK_CONFIGD_TEMPLATE_NOT_PRESERVED:" + name)
    # One genuine same-release reinstall tests the existing old-runtime path,
    # not a second package build or a separate VM.
    second = dispatch_and_poll()
    need(second == first, "G03_SAME_RELEASE_REINSTALL_STATE_CHANGED")
    need(hashlib.sha256(cfg.read_bytes()).hexdigest() == config_before,
         "G03_UNEXPECTED_OPNSENSE_CONFIG_MUTATION")
    after = run(["/sbin/ipfw", "list"], timeout=15)
    module_after = run(["/sbin/kldstat", "-n", "ipfw"], timeout=15)
    need(after.returncode == ipfw_before.returncode and
         after.stdout == ipfw_before.stdout and
         module_after.returncode == module_before.returncode and
         module_after.stdout == module_before.stdout,
         "G03_FIRST_INSTALL_CHANGED_IPFW_STATE")
    print("G03_NATIVE=" + json.dumps({
        "status": "PASS_G03_REAL_CONFIGD_FIRST_INSTALL_AND_REINSTALL",
        "engine_release": RELEASE,
        "installed": True,
        "service_stopped": True,
        "same_release_reinstalled": True,
        "original_fd9_transaction": True,
        "stock_configd_templates_preserved": True,
        "ipfw_initially_loaded": ipfw_before.returncode == 0,
        "no_foreign_config_or_ipfw_change": True,
        "owner_browser_tested": False
    }, sort_keys=True))


def bounded_disposable_failure_evidence():
    """Only on this disposable CI guest; never print Config or secrets."""
    log = Path("/var/log/zapret2/setup.log")
    if not log.is_file() or log.is_symlink():
        print("G03_SETUP_LOG=missing", file=sys.stderr)
    else:
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-36:]
        print("G03_SETUP_LOG_TAIL_BEGIN", file=sys.stderr)
        for line in tail:
            line = re.sub(r"https?://\S+", "[external-url]", line)
            line = re.sub(r"\b[A-Fa-f0-9]{40,}\b", "[digest]", line)
            if re.search(r"token|authorization|password|secret|api[_-]?key|credential", line, re.I):
                line = "[redacted sensitive log line]"
            print("G03_SETUP_LOG: " + line[:220], file=sys.stderr)
        print("G03_SETUP_LOG_TAIL_END", file=sys.stderr)
    for path in (STATE / "setup.status", STATE / "first-install.intent"):
        if path.is_file() and not path.is_symlink():
            # Intent/status contain only a bounded release identity/phase.
            values = path.read_text(errors="replace").splitlines()[:3]
            print(f"G03_STATE:{path.name}=" + "|".join(v[:65] for v in values),
                  file=sys.stderr)
    for item in (ROOT / ".git", Path(str(ROOT) + ".first-install"),
                 STATE / "runtime.release"):
        print(f"G03_PATH:{item.name} present={item.exists()} linked={item.is_symlink()}",
              file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print("G03_NATIVE=REFUSED:" + str(exc), file=sys.stderr)
        if os.environ.get("ZAPRET2_G03_DISPOSABLE_NATIVE") == "1":
            bounded_disposable_failure_evidence()
        sys.exit(1)
