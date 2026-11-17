#!/usr/bin/env python3
"""One disposable OPNsense: real native .pkg STOPPED protected reinstall.

Only genuine pkg/Mk hooks, installed source and installed native FD9 service;
no engine setup, no owner router, no synthetic service process.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAME = "os-zapret2-restyle"
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ACTIVE = Path("/var/db/zapret2/pkg-update/operation.json")
MARKER = Path("/var/run/zapret2-restyle/pkg-replacement.restart")
CONFIG = Path("/conf/config.xml")


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def run(argv, timeout=120):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=timeout, check=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_version():
    p = run(["pkg", "query", "%v", NAME])
    need(p.returncode == 0, "PKGDB_MISSING")
    return p.stdout.strip()


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_PROTECTED_PKG_NATIVE_TEST") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "NOT_DISPOSABLE_NATIVE_GUEST")
    ver = run(["opnsense-version", "-a"])
    need(ver.returncode == 0 and ver.stdout.strip().startswith("26.7"),
         "NATIVE_OPNSENSE_26_7_REQUIRED")
    project = (ROOT / "VERSION").read_text().strip()
    mk = (ROOT / "Makefile").read_text()
    match = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$", mk)
    need(match is not None, "SOURCE_REVISION_MISSING")
    target = project + "_" + match.group(1)
    archive = ROOT / "dist" / (NAME + "-" + target + ".pkg")
    need(archive.is_file() and archive.stat().st_size > 0 and
         "FreeBSD:15:amd64" == run(["pkg", "config", "ABI"]).stdout.strip(),
         "EXACT_CURRENT_NATIVE_ARCHIVE_REQUIRED")
    candidate_sha = sha(archive)
    need(not ACTIVE.exists() and not ACTIVE.is_symlink(), "BASELINE_UPDATE_RECORD_PRESENT")
    need(not MARKER.exists(), "BASELINE_RESTART_MARKER_PRESENT")

    first = run(["pkg", "add", "-f", str(archive)], timeout=180)
    need(first.returncode == 0 and installed_version() == target,
         "REAL_NATIVE_INITIAL_INSTALL_FAILED")
    before = run([str(SERVICE), "status"])
    need(before.returncode == 1, "EXPECTED_CLEAN_STOPPED_RUNTIME")
    config_before = sha(CONFIG)
    package_before = installed_version()
    again = run([str(SERVICE), "pkg-update", str(archive)], timeout=320)
    installed_after = installed_version()
    state = run([str(SERVICE), "status"])
    evidence = {
        "schema": 1,
        "platform": ver.stdout.strip(), "installed_version": installed_after,
        "same_archive_sha256": candidate_sha, "previous_status": before.returncode,
        "protected_update_rc": again.returncode,
        "verified_receipt": "pkg-update=verified-installed-and-restored" in again.stdout,
        "native_status_after": state.returncode,
        "pkgdb_unchanged_identity": package_before == installed_after == target,
        "owner_config_unchanged": config_before == sha(CONFIG),
        "no_active_update_record": not ACTIVE.exists() and not ACTIVE.is_symlink(),
        "no_restart_marker": not MARKER.exists(),
        "owner_appliance_modified": False,
    }
    print("NATIVE_PROTECTED_STOPPED=" + json.dumps(evidence, sort_keys=True),
          flush=True)
    need(all([evidence["protected_update_rc"] == 0,
              evidence["verified_receipt"],
              evidence["native_status_after"] == 1,
              evidence["pkgdb_unchanged_identity"],
              evidence["owner_config_unchanged"],
              evidence["no_active_update_record"],
              evidence["no_restart_marker"]]),
         "PROTECTED_NATIVE_STOPPED_REINSTALL_NOT_CONFIRMED")

    # Inject only one disposable plugin-owned INCOMPLETE update record;
    # prove it refuses before launching another pkg or touching Config.
    ACTIVE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    need(not ACTIVE.exists() and not ACTIVE.is_symlink(), "UNEXPECTED_RECORD")
    ACTIVE.write_text('{"schema":1,"phase":"requires-review"}\n')
    ACTIVE.chmod(0o600)
    try:
        pre = sha(CONFIG)
        blocked = run([str(SERVICE), "pkg-update", str(archive)], timeout=60)
        need(blocked.returncode != 0 and
             installed_version() == target and
             sha(CONFIG) == pre and
             ACTIVE.exists() and
             run([str(SERVICE), "status"]).returncode == 1,
             "UNSAFE_REPEAT_WITH_PENDING_UPDATE_RECORD")
        print("NATIVE_PROTECTED_PENDING_REFUSAL=PASS", flush=True)
    finally:
        # Fixture is an exact, test-owned disposable file; no owner cleanup.
        need(ACTIVE.read_text() == '{"schema":1,"phase":"requires-review"}\n',
             "TEST_RECORD_CHANGED_UNEXPECTEDLY")
        ACTIVE.unlink()
    need(not ACTIVE.exists(), "PENDING_TEST_CLEANUP_FAILED")
    print("NATIVE_PROTECTED_UPDATE=PASS_STOPPED_AND_PENDING_REFUSAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("NATIVE_PROTECTED_UPDATE=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
