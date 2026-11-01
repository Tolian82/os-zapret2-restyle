#!/usr/bin/env python3
"""Stage 0: real OPNsense firmware routes and isolated native pkg root limits.

No real plugin service start/stop, IPFW mutation, firmware execution or pkg
replacement. All pkg mutations use temporary synthetic private PKG_DBDIR.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
NAME = "zapret2-stage0-sidecar-only-fixture"
OLD = (NAME + "|0.6.2_1", b"old\n")
NEW = (NAME + "|0.6.2_41", b"direct\n")


class Refusal(Exception):
    pass


def need(condition, error):
    if not condition:
        raise Refusal(error)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".", "_").replace("-", "_"), HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def firmware_routes(native):
    hashes = native.validate_firmware(native.inspect_firmware())
    required = {
        "lock.sh": (chr(36) + "{PKG} lock -y",),
        "unlock.sh": (chr(36) + "{PKG} unlock -y",),
        "update.sh": ("opnsense-update",),
        "upgrade.sh": ("opnsense-update -u",),
    }
    for name, tokens in required.items():
        file = Path("/usr/local/opnsense/scripts/firmware") / name
        info = file.lstat()
        need(stat.S_ISREG(info.st_mode) and not file.is_symlink(),
             "FIRMWARE_ROUTE_NOT_REGULAR:" + name)
        raw = file.read_bytes()
        need(100 < len(raw) < 30000 and
             all(token in raw.decode("utf-8") for token in tokens),
             "NATIVE_FIRMWARE_ROUTE_CHANGED:" + name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    actions = native.ACTIONS.read_text()
    for token in ("[install]", "[remove]", "[reinstall]", "[update]",
                  "[upgrade]", "[lock]", "[unlock]", "[auto-update]"):
        need(token in actions, "OPNSENSE_FIRMWARE_ACTION_MISSING:" + token)
    return hashes


def cold(guard, archive):
    try:
        result = guard.snapshot(archive)
    except guard.Refusal as exc:
        raise Refusal(str(exc)) from None
    need(result.get("status") == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
         result.get("old_package") == "os-zapret2-restyle-0.6.2_1" and
         result.get("real_old_status") == "STOPPED" and
         result.get("safe_pkg_transaction_authorized") is False,
         "OLD_OWNER_NOT_PROVEN_COLD")
    return result


def lookalike_process_refusal(guard, archive):
    """Own shell /dvtws2 argument is NOT a real Zapret2 engine."""
    child = subprocess.Popen(
        ["/bin/sh", "-c", "while :; do sleep 1; done", "/dvtws2"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    try:
        need(child.poll() is None, "OWNED_PROCESS_NOT_LIVE")
        found = False
        for _ in range(40):
            result = guard.command(["/bin/ps", "-ax", "-o", "command="])
            need(result.returncode == 0, "PROCESS_CENSUS_FAILED")
            if "/dvtws2" in result.stdout:
                found = True
                break
            time.sleep(0.1)
        need(found, "LOOKALIKE_PROCESS_NOT_VISIBLE")
        try:
            cold(guard, archive)
        except Refusal as exc:
            need(str(exc) == "POSSIBLE_ZAPRET_PROCESS_PRESENT",
                 "WRONG_LOOKALIKE_OWNER_REFUSAL:" + str(exc))
        else:
            raise Refusal("LOOKALIKE_PROCESS_FALSELY_AUTHORIZED")
        return "REFUSED_POSSIBLE_ZAPRET_PROCESS_PRESENT"
    finally:
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=8)


def classify_force(kind, before, after):
    need(before == OLD, "UNVERIFIED_PRIVATE_BASELINE")
    if after == OLD:
        return "NATIVE_LOCK_PRESERVED_FOR_TESTED_FORCE_COMMAND"
    if kind == "delete" and after == ("ABSENT", None):
        return "LOCK_BYPASSED_BY_FORCED_DELETE"
    if kind == "add" and after == NEW:
        return "LOCK_BYPASSED_BY_FORCED_ADD"
    return "UNEXPECTED_PARTIAL_OR_FOREIGN_PKG_MUTATION"


def private_case(root, kind, native, locks, fixture):
    scope = root / kind
    scope.mkdir(mode=0o700)
    for part in ("pkgdb", "cache"):
        (scope / part).mkdir(mode=0o700)
    env = dict(os.environ, PKG_DBDIR=str(scope / "pkgdb"),
               PKG_CACHEDIR=str(scope / "cache"), ASSUME_ALWAYS_YES="yes")
    pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
    original, marker = fixture.build_fixture(
        scope, "old", "0.6.2_1", scope / "trace", scope / "payload")
    need(native.call(pkg + ["add", str(original)], env).returncode == 0,
         "PRIVATE_ORIGINAL_INSTALL_FAILED")
    before = locks.fixture_state(native, pkg, env, marker)
    need(before == OLD, "PRIVATE_BASELINE_INCORRECT")
    locks.lock_exact(native, pkg, env)
    if kind == "delete":
        arguments = ["delete", "-f", "-y", NAME]
    elif kind == "add":
        next_pkg, next_marker = fixture.build_fixture(
            scope, "direct", "0.6.2_41", scope / "trace", scope / "payload")
        need(next_marker == marker, "PRIVATE_MARKER_CHANGED")
        arguments = ["add", "-f", str(next_pkg)]
    elif kind == "unlock_then_delete":
        unlock = native.call(pkg + ["unlock", "-y", NAME], env)
        need(unlock.returncode == 0 and not locks.is_locked(native, pkg, env),
             "DIRECT_PRIVILEGED_UNLOCK_FAILED")
        arguments = ["delete", "-y", NAME]
    else:
        raise Refusal("UNKNOWN_PRIVATE_CASE")
    command = native.call(pkg + arguments, env)
    after = locks.fixture_state(native, pkg, env, marker)
    if kind == "unlock_then_delete":
        need(command.returncode == 0 and after == ("ABSENT", None),
             "UNCOORDINATED_ROOT_PKG_DELETE_NOT_OBSERVED")
        label = "ROOT_EXPLICIT_UNLOCK_THEN_DELETE_SUCCEEDED"
    else:
        label = classify_force(kind, before, after)
    return {"native_pkg_rc": command.returncode, "after": after[0],
            "verdict": label, "native_locked_after":
            locks.is_locked(native, pkg, env), "product_safety": False}


def run(archive):
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "ONLY_DISPOSABLE_ROOT_FREEBSD_AMD64")
    guest = load("stage0-opnsense-guest-readonly.py")
    installed = load("stage0-opnsense-installed-predecessor.py")
    guard = load("stage0-opnsense-prepkg-readonly.py")
    native = load("stage0-opnsense-native-pkg-lock.py")
    locks = load("stage0-opnsense-pkg-relock-failures.py")
    fixture = load("stage0-opnsense-pkg-sidecar-bypass.py")
    need(guest.evaluate(guest.observe()).get("status") ==
         "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY", "NOT_OPNSENSE_KVM")
    firmware = firmware_routes(native)
    installed.install_and_verify(archive)
    pre = installed.pre
    hostname = pre.run("hostname", "-s").decode().strip()
    original = pre.run_guest(archive, hostname)
    need(original.get("status") == "PASS_READ_ONLY_PROVENANCE",
         "ORIGINAL_PUBLISHED_PACKAGE_UNQUALIFIED")
    cold(guard, archive)
    lookalike = lookalike_process_refusal(guard, archive)
    cold(guard, archive)
    with tempfile.TemporaryDirectory(prefix="stage0-native-pkg-root-") as work:
        results = {name: private_case(Path(work), name, native, locks, fixture)
                   for name in ("delete", "add", "unlock_then_delete")}
    need(pre.run_guest(archive, hostname) == original,
         "REAL_ORIGINAL_INSTALLED_PACKAGE_CHANGED")
    cold(guard, archive)
    return {"schema": 1,
            "status": "OBSERVED_NATIVE_PKG_ROOT_ENTRYPOINTS_AND_PROCESS_REFUSAL",
            "firmware_installed_sha256": firmware,
            "test_owned_lookalike_process": lookalike,
            "private_pkg_operations": results,
            "authentic_old_predecessor_unchanged": True,
            "genuine_old_stopped_and_cold_after": True,
            "genuine_running_engine_tested": False,
            "foreign_ipfw_kernel_tested": False,
            "package_manager_pre_transaction_veto_proved": False,
            "uncoordinated_root_pkg_excluded": False,
            "actual_original_to_successor_replacement_tested": False,
            "product_safety_acceptance_passed": False,
            "stage0_closed": False}


def main():
    if len(sys.argv) != 2:
        print("STAGE0_ROOT_PKG=REFUSED:ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        report = run(Path(sys.argv[1]))
        print("STAGE0_ROOT_PKG=" + json.dumps(report, sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE0_ROOT_PKG=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
