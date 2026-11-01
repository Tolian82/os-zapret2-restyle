#!/usr/bin/env python3
"""Native original 0.6.2_1 deinstall in an authenticated disposable OPNsense guest.

Proves exact archived and installed old hook bytes, then traces the installed
old PRE_DEINSTALL with the actual old service in cold STOPPED state. Finally
asks real pkg to delete the authentic installed package with native hooks.
No replacement, no mock service, no IPFW/configd/Stop/Start or owner machine.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def module(file, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


pre = module("stage0-installed-predecessor-readonly.py", "predecessor")
fd9 = module("stage0-opnsense-old-service-fd9.py", "old_fd9")
DELETE = ("pkg", "-o", "REPO_AUTOUPDATE=false", "delete", "-y", pre.NAME)
STATUS_TRACE = re.compile(r"(?m)^\+\s+[^\n]*zapret_service\.sh status\s*$")
STOPPED_TRACE = re.compile(r"(?m)^\+\s+service_status=1\s*$")
STOP_TRACE = re.compile(r"(?m)^\+\s+[^\n]*zapret_service\.sh stop\s*$")


def ensure(ok, failure):
    if not ok:
        raise pre.Refusal(failure)


def run_command(args, **kwargs):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              check=False, timeout=120, **kwargs)
    except (OSError, subprocess.SubprocessError):
        raise pre.Refusal("NATIVE_COMMAND_FAILED_OR_TIMED_OUT") from None


def trace_original_pre_deinstall(hook_body, temporary):
    # This is a genuine historical script from installed pkgdb and a genuine
    # service; it is NOT an instrumented replacement hook or fake service.
    env = os.environ.copy()
    env.pop("PKG_UPGRADE", None)
    env.update(
        LIFECYCLE_LOCK_FILE=str(temporary / "lifecycle.lock"),
        LOCKF_BIN="/usr/bin/lockf",
        UPGRADE_STATE_DIR=str(temporary / "upgrade"),
        UPGRADE_RESTART_MARKER=str(temporary / "upgrade" / "pkg-upgrade.restart"),
        REPLACEMENT_RESTART_MARKER=str(temporary / "upgrade" / "pkg-replacement.restart"),
    )
    result = run_command(("/bin/sh", "-x"), input=hook_body, env=env)
    ensure(result.returncode == 0, "ORIGINAL_PRE_DEINSTALL_COLD_REFUSED:" +
           str(result.returncode))
    trace = result.stderr
    ensure(bool(STATUS_TRACE.search(trace)), "ORIGINAL_PRE_DEINSTALL_DID_NOT_QUERY_REAL_STATUS")
    ensure(bool(STOPPED_TRACE.search(trace)), "ORIGINAL_PRE_DEINSTALL_DID_NOT_CLASSIFY_STOPPED")
    ensure(not STOP_TRACE.search(trace), "ORIGINAL_PRE_DEINSTALL_UNEXPECTED_STOP")
    ensure(not (temporary / "upgrade").exists(), "ORIGINAL_PRE_DEINSTALL_CREATED_MARKER")
    return True


def native_delete():
    # Delete exactly the installed published package, no --force/-I/scripts
    # bypass and no repo or dependency mutation on the disposable OPNsense VM.
    result = run_command(DELETE)
    ensure(result.returncode == 0, "NATIVE_OLD_PKG_DELETE_REFUSED:" +
           str(result.returncode) + ":" +
           " ".join(result.stderr.split())[:220])
    installed = run_command(("pkg", "info", "-e", pre.NAME))
    ensure(installed.returncode == 1, "ORIGINAL_PACKAGE_STILL_IN_NATIVE_PKGDB")
    path = Path(pre.SERVICE)
    ensure(not path.exists() and not path.is_symlink(),
           "ORIGINAL_SERVICE_SURVIVED_NATIVE_PKG_DELETE")
    return True


def verify(archive):
    hostname = pre.run("hostname", "-s").decode().strip()
    report = pre.run_guest(archive, hostname)
    ensure(report["status"] == "PASS_READ_ONLY_PROVENANCE",
           "ORIGINAL_PACKAGE_INSTALLED_PROVENANCE_NOT_PASS")
    fd9.assert_fresh_no_shared_journal()
    archived, archived_service = pre.archive_data(archive)
    installed = pre.installed_manifest_from_json(
        pre.run("pkg", "info", "-R", "--raw-format", "json", pre.NAME))
    hooks = installed["scripts"]
    for phase in pre.PHASES:
        ensure(hooks[phase] == archived["scripts"][phase],
               "OLD_HOOK_NOT_EXACT_ARCHIVE:" + phase)
    ensure(report["service_sha256"] == pre.digest(archived_service),
           "OLD_SERVICE_BYTES_CHANGED")
    with tempfile.TemporaryDirectory(prefix="stage0-old-deinstall-") as folder:
        base = Path(folder)
        fd9.prove_stopped(fd9.call_status(base / "before.lock"))
        traced = trace_original_pre_deinstall(hooks["pre-deinstall"], base)
        fd9.prove_stopped(fd9.call_status(base / "after.lock"))
        fd9.assert_fresh_no_shared_journal()
        deleted = native_delete()
    return {
        "schema": 1,
        "status": "PASS_OPNSENSE_26_7_ORIGINAL_0_6_2_1_COLD_DEINSTALL",
        "archive_sha256": pre.ARCHIVE_SHA,
        "package": report["package"],
        "original_pre_deinstall_sha256": pre.digest(hooks["pre-deinstall"].encode()),
        "original_post_deinstall_sha256": pre.digest(hooks["post-deinstall"].encode()),
        "old_service_sha256": report["service_sha256"],
        "real_installed_original_pre_deinstall_traced": traced,
        "real_cold_old_service_status_before_after": "STOPPED",
        "old_service_stop_not_invoked_in_trace": True,
        "native_pkg_delete_original_hooks_enabled": deleted,
        "original_package_removed_from_pkgdb": True,
        "original_service_file_removed": True,
        "old_post_deinstall_independently_traced": False,
        "running_service_tested": False,
        "actual_pkg_replacement": False,
        "native_successor_tested": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_OLD_DEINSTALL=REFUSED:EXACT_PUBLISHED_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        result = verify(Path(sys.argv[1]))
    except (pre.Refusal, OSError, KeyError, ValueError, TypeError) as exc:
        print("STAGE0_OLD_DEINSTALL=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_OLD_DEINSTALL=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
