#!/usr/bin/env python3
"""G10A separate immutable published stable _1 RUNNING -> published _33 witness.

This tests the exact old installed running owner while the accepted nine-stage
smoke separately tests an originally stopped old owner. Never runs on an owner
appliance; no unpublished package, repository substitution, or unsafe fallback.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    if spec is None or spec.loader is None:
        raise RuntimeError("G10A_RUNNING_MISSING_NATIVE_TEST_LIBRARY")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

nine = load("g10a_nine_staged", "stage11-published-nine-step-native.py")
old = nine.historical
REPORT = ROOT / "dist/g11-published-running-stable.json"

class Refusal(RuntimeError):
    pass

def need(what, why):
    if not what:
        raise Refusal(why)

def call(argv, *, timeout=300, env=None):
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refusal("RUNNING_NATIVE_COMMAND_UNAVAILABLE:" + Path(argv[0]).name) from exc
    need(p.returncode == 0, "RUNNING_NATIVE_COMMAND_FAILED:" +
         Path(argv[0]).name + ":rc=" + str(p.returncode))
    return p.stdout

def plugin_rules():
    output = call(["/sbin/ipfw", "-q", "list"], timeout=20)
    return [line for line in output.splitlines()
            if re.match(r"^\s*0*190(?:0[0-9]|10)\s+", line)]

def actual_owner(label):
    service = nine.SERVICE
    engine = nine.RUNTIME / "binaries/my/dvtws2"
    pidfile = Path("/var/run/dvtws2.pid")
    need(service.is_file() and engine.is_file() and pidfile.is_file(),
         "RUNNING_" + label + "_NATIVE_FILES_MISSING")
    need("zapret is running" in call([str(service), "status"], timeout=35),
         "RUNNING_" + label + "_SERVICE_STOPPED")
    raw = pidfile.read_text().strip()
    need(raw.isdecimal() and int(raw) > 1, "RUNNING_" + label + "_PID_INVALID")
    proc = call(["/bin/ps", "-p", raw, "-o", "command="], timeout=20)
    need(str(engine) in proc, "RUNNING_" + label + "_ENGINE_UNATTESTED")
    rules = plugin_rules()
    need(any(re.match(r"^\s*0*19000\s+", x) and "divert 989" in x and
             "65431" in x and "lo0" in x for x in rules),
         "RUNNING_" + label + "_OWNED_IPFW_ABSENT")
    return {"pid": int(raw), "engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
            "owned_rule_count": len(rules)}

def run():
    nine.native_gate()
    need(os.environ.get("ZAPRET2_G10A_RUNNING_STABLE") == "1",
         "G10A_RUNNING_PREDECESSOR_EXPLICIT_DISPOSABLE_OPTIN_REQUIRED")
    need(not REPORT.exists(), "G10A_RUNNING_REPORT_ALREADY_EXISTS")
    stable = old.package(*nine.OLD)
    successor = old.package(*nine.NEW)
    need(nine.INSTALLER.is_file() and nine.sha(nine.INSTALLER) == nine.INSTALLER_SHA,
         "G10A_RUNNING_PUBLISHED_INSTALLER_MISMATCH")

    # This stable predecessor is the actual published _1, not historical 0.6.2.
    call(["/usr/sbin/pkg", "add", "-f", str(stable)], timeout=300)
    need(nine.version() == nine.OLD[0], "G10A_RUNNING_OLD_PKG_NOT_INSTALLED")
    old.seed_existing_saved_config()

    # On stable _1, setup.sh is the actual manual runtime install exposed to
    # the owner; do not substitute the _33 transaction script before upgrade.
    native_setup = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh")
    need(native_setup.is_file(), "STABLE_1_NATIVE_UPSTREAM_SETUP_NOT_INSTALLED")
    call(["/bin/sh", str(native_setup), "install", "v1.0.7"], timeout=390)
    need((nine.RUNTIME / "binaries/my/dvtws2").is_file(),
         "STABLE_1_NATIVE_UPSTREAM_ENGINE_NOT_PRESENT")
    old.enable_loopback_only_for_running_purge()
    call([str(nine.SERVICE), "start"], timeout=180)
    before = actual_owner("OLD_STABLE")
    user_before = nine.saved()
    foreign_before = old.other_config(old.xml())
    lock = Path("/var/run/zapret2-lifecycle.lock")
    need(lock.is_file() and not lock.is_symlink(), "ORIGINAL_FD9_LOCK_NOT_PRESENT")
    lock_inode = lock.stat().st_ino

    # No Stop/Uninstall. This is the old RUNNING -> new SAME published native
    # pkg through the source-verified SHA-pinned companion installer.
    nine.published_installer(successor, "RUNNING_STABLE_UPGRADE")
    need(nine.version() == nine.NEW[0] and nine.saved() == user_before and
         old.other_config(old.xml()) == foreign_before,
         "RUNNING_STABLE_UPGRADE_CHANGED_SAVED_CONFIG")
    after = actual_owner("NEW_PUBLISHED")
    need(before["pid"] != after["pid"], "OLD_STABLE_PID_WAS_NOT_REPLACED")
    need(before["engine_sha256"] == after["engine_sha256"],
         "UPGRADE_CHANGED_UPSTREAM_ENGINE_BYTES")
    need(lock.is_file() and lock.stat().st_ino == lock_inode,
         "UPGRADE_REPLACED_ORIGINAL_FD9")
    call([str(nine.SERVICE), "stop"], timeout=180)
    old.assert_no_capture()
    need(nine.sha(stable) == nine.OLD[1] and
         nine.sha(successor) == nine.NEW[1] and
         nine.sha(nine.INSTALLER) == nine.INSTALLER_SHA,
         "RUNNING_PUBLISHED_ASSET_BYTES_CHANGED")
    result = {
        "status": "PASS_G10A_PUBLISHED_STABLE1_RUNNING_TO_PUBLISHED33",
        "old_version": nine.OLD[0], "new_version": nine.NEW[0],
        "old_archive_sha256": nine.OLD[1],
        "new_archive_sha256": nine.NEW[1],
        "companion_installer_sha256": nine.INSTALLER_SHA,
        "old_stable_engine_running_pre_upgrade": True,
        "old_pid_replaced_under_new_version": True,
        "one_original_fd9_inode": True,
        "upstream_engine_unchanged": True,
        "user_and_foreign_config_preserved": True,
        "scoped_loopback_ipfw": True,
        "full_nine_stage_sequential_acceptance": False,
        "full_A01_A22_owner_live": False,
        "owner_appliance_modified": False,
    }
    REPORT.parent.mkdir(exist_ok=True, parents=True)
    REPORT.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("G10A_RUNNING_OLD_STABLE=" + json.dumps(result, sort_keys=True), flush=True)

def self_test():
    need(nine.OLD[0] == "0.6.3_1" and nine.NEW[0] == "0.6.3_33"
         and nine.OLD[1] != nine.NEW[1] and
         nine.INSTALLER_SHA != nine.NEW[1],
         "G10A_RUNNING_SOURCE_PINS_INVALID")
    print("PASS_G10A_PUBLISHED_STABLE_RUNNING_SOURCE=1")

if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif not sys.argv[1:]:
            run()
        else:
            raise Refusal("INVALID_ARGUMENT")
    except (Refusal, nine.Refusal, old.Refusal, OSError, ValueError,
            TypeError, subprocess.TimeoutExpired) as exc:
        print("G10A_RUNNING_OLD_STABLE=REFUSED:" + str(exc)[:160],
              file=sys.stderr)
        sys.exit(2)
