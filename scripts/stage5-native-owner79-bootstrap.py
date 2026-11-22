#!/usr/bin/env python3
"""Owner-_79 bootstrap acceptance on ONE disposable native OPNsense.

A real, immutable published _79 package has NO installed guarded pkg-update
action. This fixture measures a *one-time controlled stopped-state migration*,
not arbitrary mid-pkg crash safety, full Voice or owner physical acceptance.
No external installer is delivered to an owner.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAME = "os-zapret2-restyle"
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
CONFIG = Path("/conf/config.xml")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
GUARD = Path("/var/db/zapret2/pkg-update/operation.json")
MARKER = Path("/var/run/zapret2-restyle/pkg-replacement.restart")
LEGACY_MARKER = Path("/var/run/zapret2-restyle/pkg-upgrade.restart")
DVTWS_PID = Path("/var/run/dvtws2.pid")
OLD_URL = ("https://github.com/Tolian82/os-zapret2-restyle/releases/"
           "download/v0.6.5_79/os-zapret2-restyle-0.6.5_79.pkg")
OLD_SHA = "7095e0b72098d181456c8cd16a8a844af9d1464de158dd5f27b706e0d7eef558"


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def run(args, timeout=120):
    return subprocess.run(args, capture_output=True, text=True,
                          timeout=timeout, check=False)


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def version():
    result = run(["pkg", "query", "%v", NAME])
    need(result.returncode == 0, "PRODUCT_NOT_IN_PKGDB")
    return result.stdout.strip()


def manifest(path):
    cmd = run(["/usr/bin/tar", "-xOf", str(path), "+MANIFEST"], timeout=50)
    need(cmd.returncode == 0, "MANIFEST_UNAVAILABLE")
    return json.loads(cmd.stdout)


def load_script(name, identity):
    spec = importlib.util.spec_from_file_location(identity, ROOT / "scripts" / name)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


def current_owner():
    state = json.loads(JOURNAL.read_text())
    need(state["phase"] == "committed", "SHARED_OWNER_NONTERMINAL")
    return state["detail"]["id"]


def running_pid():
    need(DVTWS_PID.is_file() and not DVTWS_PID.is_symlink(),
         "NATIVE_CHILD_PIDFILE_UNTRUSTED")
    pid = DVTWS_PID.read_text().strip().split()[0]
    need(pid.isdecimal(), "NATIVE_CHILD_PID_INVALID")
    return pid


def seed_verified_stable_tag_for_disposable_g03(g03):
    """Stock releases.cache, public REAL stable release; VM fixture only.

    GitHub API returns 403/Forbidden inside this disposable VM. The tag
    v1.0.7 was independently confirmed as a non-draft/non-prerelease via
    https://api.github.com/repos/bol-van/zapret2/releases/tags/v1.0.7
    (published 2026-11-05). No production fallback is introduced. Native
    setup still fetches/checks out and compiles real upstream bytes.
    """
    need(g03.RELEASE == "v1.0.7" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_OWNER79_BOOTSTRAP_NATIVE_TEST") == "1",
         "VERIFIED_STABLE_TAG_NOT_QUALIFIED")
    state = Path("/var/db/zapret2-restyle")
    state.mkdir(mode=0o755, parents=True, exist_ok=True)
    st = state.lstat()
    need(state.is_dir() and not state.is_symlink() and
         st.st_uid == 0 and not (st.st_mode & 0o022),
         "UNQUALIFIED_NATIVE_RELEASE_CACHE_PARENT")
    cache = state / "releases.cache"
    need(not cache.exists() and not cache.is_symlink(),
         "NATIVE_RELEASE_CACHE_PREEXISTS")
    fd = os.open(cache, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o644)
    try:
        with os.fdopen(fd, "wb") as writer:
            writer.write(b"v1.0.7\n")
            writer.flush()
            os.fsync(writer.fileno())
    finally:
        pass
    need(cache.read_bytes() == b"v1.0.7\n" and
         cache.stat().st_uid == 0 and cache.stat().st_mode & 0o777 == 0o644,
         "VERIFIED_NATIVE_RELEASE_CACHE_NOT_READY")
    print("NATIVE_79_TEST_ONLY_STABLE_CACHE=VERIFIED_PUBLIC_v1.0.7",
          flush=True)


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_OWNER79_BOOTSTRAP_NATIVE_TEST") == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "NOT_ISOLATED_NATIVE_GUEST")
    platform = run(["opnsense-version", "-a"])
    abi = run(["pkg", "config", "ABI"])
    need(platform.returncode == 0 and platform.stdout.strip().startswith("26.7") and
         abi.returncode == 0 and abi.stdout.strip() == "FreeBSD:15:amd64",
         "UNQUALIFIED_OPNSENSE_PLATFORM")
    need(run(["pkg", "info", "-e", NAME]).returncode == 1 and
         not GUARD.exists() and not GUARD.is_symlink() and
         not MARKER.exists() and not LEGACY_MARKER.exists(),
         "GUEST_NOT_CLEAN")
    mk = (ROOT / "Makefile").read_text()
    match = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$", mk)
    need(match is not None, "VERSION_REVISION_MISSING")
    target = (ROOT / "VERSION").read_text().strip() + "_" + match.group(1)
    candidate = ROOT / "dist" / f"{NAME}-{target}.pkg"
    need(candidate.is_file() and
         manifest(candidate).get("name") == NAME and
         manifest(candidate).get("version") == target and
         manifest(candidate).get("abi") == "FreeBSD:15:amd64",
         "NATIVE_SUCCESSOR_NOT_QUALIFIED")
    successor_sha = hash_file(candidate)

    # The immutable predecessor is the owner's actual published package,
    # not a synthetic prior source tree.
    old = Path("/root/os-zapret2-restyle-0.6.5_79.pkg")
    downloaded = run(["/usr/bin/fetch", "-o", str(old), OLD_URL], timeout=120)
    need(downloaded.returncode == 0 and
         hash_file(old) == OLD_SHA and
         manifest(old).get("name") == NAME and
         manifest(old).get("version") == "0.6.5_79" and
         manifest(old).get("abi") == "FreeBSD:15:amd64",
         "PUBLISHED_79_BYTES_OR_ABI_REFUSED")
    installed = run(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                     "add", "-f", str(old)], timeout=180)
    need(installed.returncode == 0 and version() == "0.6.5_79" and
         run([str(SERVICE), "status"]).returncode == 1 and
         not (SERVICE.parent / "protected_pkg_update.py").exists(),
         "PUBLISHED_79_NATIVE_INITIAL_INSTALL_FAILED")

    witness = load_script("p5b2b-native-witness.py", "published79_native_wan")
    bridge = load_script("test-own70-native-package-handoff.py",
                         "published79_native_strategies")
    g03 = load_script("stage2-opnsense-g03-first-install.py",
                      "published79_native_setup")
    witness.set_guest_lo0()
    bridge.set_guest_list_mode()
    seed_verified_stable_tag_for_disposable_g03(g03)
    try:
        setup = g03.dispatch_and_poll()
    except (g03.Refusal, OSError, subprocess.TimeoutExpired):
        # Only this guarded disposable CI guest. Existing G03 helper redacts
        # URLs, token-bearing lines and raw Config; do not conceal setup fail.
        g03.bounded_disposable_failure_evidence()
        raise
    need(setup["installed"] == "1" and setup["service"] == "stopped",
         "PUBLISHED_79_UPSTREAM_NOT_STOPPED_READY")

    manual = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                  "strategies", bridge.request("list")], timeout=240)
    need(manual.returncode == 0 and "applied-id=" in manual.stdout and
         run([str(SERVICE), "status"]).returncode == 0,
         "PUBLISHED_79_LIST_NOT_RUNNING")
    automatic = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                     "strategies", bridge.request("auto")], timeout=240)
    old_id = current_owner()
    old_pid = running_pid()
    need(automatic.returncode == 0 and "applied-id=" in automatic.stdout and
         (EPOCHS / old_id / "epoch.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 0,
         "PUBLISHED_79_AUTO_NOT_RUNNING_COMMITTED")
    saved_xml = hash_file(CONFIG)

    # Original _79 FD9 Stop, not a package hook and not a new writer.
    stopped = run([str(SERVICE), "stop"], timeout=150)
    stopped_rc = run([str(SERVICE), "status"]).returncode
    stop_evidence = {
        "old_original_stop_rc": stopped.returncode,
        "old_original_status_rc": stopped_rc,
        "retired_receipt_exists": (EPOCHS / old_id / "retired.json").is_file(),
        "config_digest_unchanged": hash_file(CONFIG) == saved_xml,
        "old_pkg_version_unchanged": version() == "0.6.5_79",
        "protected_guard_absent": not GUARD.exists(),
        "new_marker_absent": not MARKER.exists(),
        "legacy_marker_absent": not LEGACY_MARKER.exists(),
    }
    if not (stopped.returncode == 0 and stopped_rc == 1 and
            all(value is True for key, value in stop_evidence.items()
                if key not in ("old_original_stop_rc", "old_original_status_rc"))):
        # A previous native VM attempt refused while the earlier exact-head
        # native runs passed. Keep the strict fail-closed gate, but expose
        # ONLY bounded status booleans/exit codes, never stdout/stderr,
        # Config, argv, hostname, URL, or any private credential content.
        print("NATIVE_79_STOP_GATE=" + json.dumps(
            stop_evidence, sort_keys=True, separators=(",", ":")),
            flush=True)
    need(stopped.returncode == 0 and stopped_rc == 1 and
         all(value is True for key, value in stop_evidence.items()
             if key not in ("old_original_stop_rc", "old_original_status_rc")),
         "OLD79_ORIGINAL_FD9_STOP_NOT_QUALIFIED")
    print("NATIVE_79_PRETRANSACTION_STOP=PASS_RETIRED_EPOCH", flush=True)

    # Ordinary native pkg is invoked only AFTER an independently verified
    # physical STOPPED state. This one-time historical path is NOT protected
    # against arbitrary power loss or mid-extraction corruption.
    changed = run(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                   "add", "-f", str(candidate)], timeout=240)
    full = changed.stdout + "\n" + changed.stderr
    new_service_sha = hash_file(SERVICE)
    expected_service_sha = hash_file(
        ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
    xml = ET.fromstring(CONFIG.read_bytes())
    chosen = xml.find("./OPNsense/Zapret/hostlist/mode")
    need(changed.returncode == 0 and
         "zapret-pkg-preinstall-status=1" in full and
         "zapret-pkg-postinstall-restart-intent=0" in full and
         not any(x in full for x in (
             "PRE-INSTALL script failed", "PRE-DEINSTALL script failed",
             "POST-INSTALL script failed", "POST-DEINSTALL script failed")) and
         version() == target and new_service_sha == expected_service_sha and
         (SERVICE.parent / "protected_pkg_update.py").is_file() and
         hash_file(CONFIG) == saved_xml and
         chosen is not None and chosen.text == "auto" and
         run([str(SERVICE), "status"]).returncode == 1 and
         not GUARD.exists() and not GUARD.is_symlink() and
         not MARKER.exists() and not LEGACY_MARKER.exists(),
         "OLD79_TO_SUCCESSOR_NATIVE_PKG_NOT_SAFE_STOPPED")
    print("NATIVE_79_PACKAGE_REPLACED=PASS_STOPPED_CONFIG_PRESERVED",
          flush=True)

    # New installed service performs its own normal cold Start through
    # original FD9; the old retired observer can never be reused as a PID.
    start = run([str(SERVICE), "start"], timeout=180)
    new_id = current_owner()
    new_pid = running_pid()
    result = {
        "schema": 1, "from_version": "0.6.5_79", "to_version": target,
        "published_predecessor_sha256": OLD_SHA,
        "new_archive_sha256": successor_sha,
        "old_epoch_retired": (EPOCHS / old_id / "retired.json").is_file(),
        "new_epoch_committed": new_id != old_id and
            (EPOCHS / new_id / "epoch.json").is_file(),
        "different_native_pid": new_pid != old_pid,
        "start_rc": start.returncode,
        "native_status_rc": run([str(SERVICE), "status"]).returncode,
        "saved_config_unchanged": hash_file(CONFIG) == saved_xml,
        "native_package_installed": version() == target,
        "no_guard_or_restart_marker": not GUARD.exists() and
            not MARKER.exists() and not LEGACY_MARKER.exists(),
        "owner_appliance_modified": False,
    }
    print("NATIVE_79_BOOTSTRAP=" + json.dumps(result, sort_keys=True),
          flush=True)
    need(result["old_epoch_retired"] and result["new_epoch_committed"] and
         result["different_native_pid"] and result["start_rc"] == 0 and
         result["native_status_rc"] == 0 and result["saved_config_unchanged"] and
         result["native_package_installed"] and
         result["no_guard_or_restart_marker"],
         "PUBLISHED_79_TO_SUCCESSOR_RUNNING_ACCEPTANCE_FAILED")
    print("NATIVE_79_BOOTSTRAP=PASS_STOP_PKGBYTES_NEW_FD9_BOOT",
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("NATIVE_79_BOOTSTRAP=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
