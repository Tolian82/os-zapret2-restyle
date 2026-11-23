#!/usr/bin/env python3
"""S05c1: genuine installed *plain* Status FD9 no-write witness on disposable OPNsense.

Unlike S05a JSON, this exercises the original service_with_lifecycle_lock and
requires no mutations of runtime, Config, pkgdb, journal, PID or IPFW. All
fixture modifications happen outside the bounded before/after status window.
"""
from __future__ import annotations

import ast
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
LOCK = Path("/var/run/zapret2-lifecycle.lock")


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(obj)
    return obj


s05a = load("s05c1_s05a", "tz6v5-s05a-status-json-native.py")
s04 = s05a.s04


def drift_class(before, after):
    labels = []
    for part in ("config", "engine", "process"):
        if before[part] != after[part]:
            labels.append(part)
    for part in ("rules", "tables", "ipfw_module", "ipdivert_module"):
        if before["kernel"][part] != after["kernel"][part]:
            labels.append("kernel_" + part)
    previous, current = before["tree"], after["tree"]
    changes = {key for key in previous.keys() | current.keys()
               if previous.get(key) != current.get(key)}
    if str(LOCK) in changes:
        labels.append("fd9_lockfile")
    if changes - {str(LOCK)}:
        labels.append("other_tree")
    return sorted(set(labels))


def verify_plain(label, message, rc, *, busy=False):
    exists_before = LOCK.is_file() and not LOCK.is_symlink()
    before = s04.snapshot()
    if not busy:
        response = s04.run([str(SERVICE), "status"], timeout=50)
    else:
        s04.need(exists_before, "S05C1_BUSY_NEEDS_PREEXISTING_ORIGINAL_FD9")
        # BSD flock(2), the same mechanism as FreeBSD lockf(1), on the
        # ORIGINAL file path and inode; no test lockfile, no alternate owner.
        fd = os.open(LOCK, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        child = None
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            child = subprocess.Popen([str(SERVICE), "status"],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True,
                                     env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            time.sleep(0.6)
            s04.need(child.poll() is None, "S05C1_BUSY_BYPASSED_ORIGINAL_FD9")
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        try:
            stdout, stderr = child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
            raise s04.Refusal("S05C1_BUSY_DID_NOT_RECOVER_AFTER_ORIGINAL_FD9_RELEASE")
        response = type("Reply", (), {"stdout": stdout, "stderr": stderr,
                                     "returncode": child.returncode})()
    after = s04.snapshot()
    flags = drift_class(before, after)
    s04.need(response.returncode == rc and response.stdout == message + "\n",
             "S05C1_PLAIN_STATUS_COMPATIBILITY_" + label + "_" + str(response.returncode))
    # Never echo private process cmdline, Config, stderr or IPFW rule text.
    s04.need(not any(item in response.stdout for item in
                     ("--filter-", "/conf/", "token=", "password")),
             "S05C1_PLAIN_SECRET_LEAK_" + label)
    if flags:
        raise s04.Refusal("S05C1_PLAIN_STATUS_WROTE_" + label + "__" +
                          "_".join(flags))
    return {"case": label, "rc": rc, "original_fd9": True,
            "no_write": True, "lockfile_preexisting": exists_before,
            "held_lock_serialized": busy}


def cold():
    clean = s04.load("s05c1_clean_cold", "stage2-opnsense-real-native-clean-install.py")
    s04.install(clean)
    s04.need(not s04.ENGINE.exists(), "S05C1_NOT_PLUGIN_ONLY")
    rows = [verify_plain("fresh-installed", "zapret is not running", 1)]
    rows.append(verify_plain("repeat-installed", "zapret is not running", 1))
    s04.upstream()
    s04.drop_config()
    rows.append(verify_plain("engine-no-config", "zapret is not running", 1))
    return rows


def hot():
    clean = s04.load("s05c1_clean_hot", "stage2-opnsense-real-native-clean-install.py")
    s04.install(clean)
    s04.upstream()
    g04 = s04.load("s05c1_g04", "stage2-opnsense-g04-native-runtime.py")
    node = g04.model()
    traffic = node.findtext("strategy/trafficargs") or ""
    hosts = node.findtext("hostlist/youtubedomains") or ""
    s04.need(traffic.count("--new") == 1 and len(hosts.splitlines()) == 10,
             "S05C1_DEFAULT_CONFIG_CHANGED")
    g04.authenticated_first_apply(traffic, hosts)
    rows = [verify_plain("common-running", "zapret is running", 0)]
    rows.append(verify_plain("common-running-busy", "zapret is running", 0, busy=True))
    s04.corrupt_config()
    s04.foreign_rule()
    rows.append(verify_plain("foreign-ipfw", "zapret is in an incomplete runtime state", 2))
    # Never Stop a contaminated owner or remove its foreign IPFW rule.
    return rows


def main(argv):
    if argv == ["--self-test"]:
        ast.parse(Path(__file__).read_text())
        s04.need("fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)" in Path(__file__).read_text()
                 and "s04.snapshot()" in Path(__file__).read_text(),
                 "S05C1_SOURCE_MISSING_REAL_FD9_AND_PHYSICAL_SNAPSHOT")
        print("S05C1_SOURCE_GATE=PASS")
        return 0
    if argv not in (["cold"], ["hot"]):
        return 64
    try:
        s04.guest_gate(argv[0])
        s04.need(os.environ.get("ZAPRET2_S05C1_DISPOSABLE_NATIVE") == "1",
                 "S05C1_NO_DISPOSABLE_OPTIN")
        rows = cold() if argv == ["cold"] else hot()
        print("S05C1_NATIVE=" + json.dumps({
            "status": "PASS", "cases": rows, "strict_no_write": True,
            "original_fd9": True, "operator_device_touched": False,
            "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        }, sort_keys=True, separators=(",", ":")))
        return 0
    except (s04.Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        label = str(exc).split(":", 1)[0][:160]
        if not re.fullmatch("[A-Z0-9_]+", label):
            label = "UNQUALIFIED"
        print("S05C1_NATIVE=REFUSED:" + label, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
