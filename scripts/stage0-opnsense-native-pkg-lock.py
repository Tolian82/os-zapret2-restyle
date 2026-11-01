#!/usr/bin/env python3
"""Read-only OPNsense firmware route plus pkg-native lock on private fixtures.

Disposable OPNsense 26.7 KVM ONLY. Native pkg mutations use private pkgdb and
synthetic payload; never invoke OPNsense firmware actions or touch real Zapret2.
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

HERE = Path(__file__).resolve().parent
FW = Path("/usr/local/opnsense/scripts/firmware")
ACTIONS = Path("/usr/local/opnsense/service/conf/actions.d/actions_firmware.conf")
CTRL = Path("/usr/local/opnsense/mvc/app/controllers/OPNsense/Core/Api/FirmwareController.php")
SOURCE_PIN = "874c32d7e5e337f19f256066b9689e91e56d5277"
NAME = "zapret2-stage0-fd9-hook-fixture"


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".", "_").replace("-", "_"), HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call(args, env=None):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=95, check=False, env=env)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_PKG_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None


def status(pkg, env, path):
    p = call(pkg + ["query", "%n|%v", NAME], env)
    require(p.returncode in (0, 1), "PKGDB_QUERY_UNKNOWN")
    version = p.stdout.strip() if p.returncode == 0 else "ABSENT"
    require(not path.is_symlink(), "FIXTURE_PAYLOAD_FOREIGN_SYMLINK")
    payload = path.read_bytes() if path.is_file() else None
    return version, payload


def inspect_firmware():
    files = {name: FW / name for name in
             ("launcher.sh", "config.sh", "install.sh", "remove.sh", "reinstall.sh")}
    files.update({"actions_firmware.conf": ACTIONS, "FirmwareController.php": CTRL})
    observed = {}
    for name, path in files.items():
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and not path.is_symlink(),
                "FIRMWARE_FILE_NOT_REGULAR:" + name)
        data = path.read_bytes()
        require(100 <= len(data) <= 200000,
                "FIRMWARE_FILE_SIZE_UNQUALIFIED:" + name)
        observed[name] = (data.decode("utf-8"), hashlib.sha256(data).hexdigest())
    return observed


def validate_firmware(observed):
    # These are *semantic* checks of the actual installed guest path; the
    # historical stable/26.7 source is independently SHA-pinned in evidence.
    patterns = {
        "FirmwareController.php": (
            'configdpRun("firmware install"', 'configdpRun("firmware remove"',
            'configdpRun("firmware reinstall"'),
        "actions_firmware.conf": (
            "[install]", "[remove]", "[reinstall]",
            "/usr/local/opnsense/scripts/firmware/launcher.sh install",
            "/usr/local/opnsense/scripts/firmware/launcher.sh remove"),
        "launcher.sh": (
            "config.sh", "LOCKFILE", "FLOCK", "COMMAND", "BASEDIR"),
        "config.sh": (
            "LOCKFILE=", "FLOCK=", 'PKG="/usr/local/sbin/pkg"'),
        "install.sh": ("install -y", "PACKAGE"),
        "remove.sh": ("remove -y", "PACKAGE"),
        "reinstall.sh": ("opnsense-revert",),
    }
    missing = [name + ":" + item for name, phrases in patterns.items()
               for item in phrases if item not in observed[name][0]]
    require(not missing, "INSTALLED_FIRMWARE_ROUTE_CHANGED:" +
            ";".join(missing)[:250])
    return {name: observed[name][1] for name in patterns}


def verdict(before_delete, before_replace, unlocked):
    if before_delete == (NAME + "|0.6.2_1", b"old\n") and \
       before_replace == (NAME + "|0.6.2_1", b"old\n") and \
       unlocked == (NAME + "|0.6.2_39", b"new\n"):
        return "PKG_LOCK_BLOCKED_DELETE_AND_FORCED_ADD_UNTIL_UNLOCK"
    if before_delete[0] == "ABSENT" or before_replace != (NAME + "|0.6.2_1", b"old\n"):
        return "PKG_LOCK_BYPASS_OR_PARTIAL_MUTATION_OBSERVED"
    return "NATIVE_PKG_LOCK_INCONCLUSIVE"


def run(guest, fixture):
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "ONLY_ROOT_FREEBSD_AMD64")
    require(guest.evaluate(guest.observe()).get("status") ==
            "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
            "UNQUALIFIED_DISPOSABLE_OPNSENSE")
    hashes = validate_firmware(inspect_firmware())
    with tempfile.TemporaryDirectory(prefix="stage0-native-pkglock-") as tmp:
        root = Path(tmp)
        db, cache = root / "pkgdb", root / "cache"
        db.mkdir(mode=0o700)
        cache.mkdir(mode=0o700)
        env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
                   ASSUME_ALWAYS_YES="yes")
        pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
        lock = root / "unused-fd9.lock"
        old, marker = fixture.build(root, "old", "0.6.2_1", root / "trace", lock)
        successor, same_marker = fixture.build(
            root, "new", "0.6.2_39", root / "trace", lock)
        require(marker == same_marker, "SYNTHETIC_PAYLOAD_PATH_CHANGED")
        first = call(pkg + ["add", str(old)], env)
        require(first.returncode == 0 and
                status(pkg, env, marker) == (NAME + "|0.6.2_1", b"old\n"),
                "OLD_PRIVATE_FIXTURE_NOT_INSTALLED")
        locked = call(pkg + ["lock", "-y", NAME], env)
        require(locked.returncode == 0, "NATIVE_LOCK_COMMAND_FAILED")
        listed = call(pkg + ["lock", "-l"], env)
        require(listed.returncode == 0 and NAME in listed.stdout,
                "NATIVE_LOCK_NOT_REPORTED_BY_PKG")
        delete = call(pkg + ["delete", "-y", NAME], env)
        after_delete = status(pkg, env, marker)
        # A destructive bypass is an observed HAZARD, not a green safety proof.
        if after_delete == (NAME + "|0.6.2_1", b"old\n"):
            replaced = call(pkg + ["add", "-f", str(successor)], env)
            after_reinstall = status(pkg, env, marker)
        else:
            replaced = None
            after_reinstall = after_delete
        if after_reinstall == (NAME + "|0.6.2_1", b"old\n"):
            unlocked_cmd = call(pkg + ["unlock", "-y", NAME], env)
            require(unlocked_cmd.returncode == 0, "NATIVE_UNLOCK_FAILED")
            accepted = call(pkg + ["add", "-f", str(successor)], env)
            after_unlocked = status(pkg, env, marker)
            accepted_rc = accepted.returncode
        else:
            accepted_rc = None
            after_unlocked = after_reinstall
        result = verdict(after_delete, after_reinstall, after_unlocked)
        return {
            "schema": 1, "status": "OBSERVED_NATIVE_PKG_LOCK_AND_FIRMWARE_ROUTES",
            "pin_opnsense_core_26_7": SOURCE_PIN,
            "installed_firmware_file_sha256": hashes,
            "installed_web_configd_launcher_pkg_path_verified_readonly": True,
            "synthetic_private_pkgdb_only": True,
            "package": NAME, "native_lock_registered": True,
            "locked_delete_rc": delete.returncode,
            "locked_force_add_rc": replaced.returncode if replaced else None,
            "after_locked_delete": after_delete[0],
            "after_locked_force_add": after_reinstall[0],
            "unlocked_force_add_rc": accepted_rc,
            "after_unlock": after_unlocked[0],
            "outcome": result,
            "ordinary_pkg_lock_is_not_owner_state_validation": True,
            "root_may_unlock_or_use_other_unsafe_paths": True,
            "real_plugin_package_tested": False,
            "all_firmware_update_routes_covered": False,
            "product_safety_acceptance_passed": False,
            "stage0_closed": False,
        }


def main():
    guest = load("stage0-opnsense-guest-readonly.py")
    fixture = load("stage0-opnsense-pkg-fd9-contention.py")
    try:
        print("STAGE0_NATIVE_PKG_LOCK=" + json.dumps(run(guest, fixture), sort_keys=True))
        return 0
    except (Refusal, fixture.Refusal, guest.Refusal, OSError, ValueError,
            UnicodeDecodeError, KeyError) as e:
        print("STAGE0_NATIVE_PKG_LOCK=REFUSED:" + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
