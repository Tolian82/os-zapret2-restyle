#!/usr/bin/env python3
"""S05c2c: genuine disposable OPNsense saved-WAN absent-engine HTTP no-write witness.

Pre/post witness surrounds ONLY authenticated HTTP Start (never backend mocks).
One original FD9 lockfile may be created by physical Start: this is explicitly
NOT claimed read-only. No user-appliance or general package test authority.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
CONFIG = Path("/conf/config.xml")
WAN = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh")
LOCK = Path("/var/run/zapret2-lifecycle.lock")
PIDS = tuple(Path(s) for s in (
    "/var/run/dvtws2.pid", "/var/run/zapret2-supervisor-daemon.pid",
    "/var/run/zapret2-supervisor-monitor.pid",
))
KEY = Path("stage5-browser-wan-ci.pub")
RECORD = Path("dist/s05c2c-actual-missing-engine-witness.json")

class Refusal(Exception):
    pass

def need(ok, message):
    if not ok:
        raise Refusal(message)

def run(*args):
    try:
        return subprocess.run(args, capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        raise Refusal("NATIVE_QUERY_UNAVAILABLE") from e

def sha(data):
    return hashlib.sha256(data).hexdigest()

def lock_state():
    try:
        s = LOCK.lstat()
    except FileNotFoundError:
        return None
    need(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1,
         "ORIGINAL_FD9_LOCK_UNSAFE")
    return (s.st_dev, s.st_ino)

def witness():
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_STAGE5_BROWSER_WAN") == "1" and
         KEY.is_file() and not KEY.is_symlink(),
         "ONLY_DISPOSABLE_OPNSENSE")
    need(CONFIG.is_file() and not CONFIG.is_symlink() and
         WAN.is_file() and not WAN.is_symlink() and
         not ENGINE.exists() and not ENGINE.is_symlink(),
         "REAL_PLUGIN_ONLY_ABSENT_ENGINE_NOT_ATTESTED")
    need(all(not p.exists() and not p.is_symlink() for p in PIDS),
         "ENGINE_OR_SUPERVISOR_PID_PRESENT")
    p = run(str(WAN), "require")
    need(p.returncode == 0 and p.stdout == b"wan-ready\n",
         "SAVED_WAN_NOT_READY")
    p = run("pkg", "info", "-e", "os-zapret2-restyle")
    need(p.returncode == 0, "PLUGIN_NOT_INSTALLED")
    p = run("/bin/ps", "-axo", "command=")
    need(p.returncode == 0 and b"supervisor_loop.sh" not in p.stdout and
         b"/binaries/my/dvtws2" not in p.stdout,
         "REAL_ENGINE_OR_SUPERVISOR_RUNNING")
    p = run("/sbin/ipfw", "-q", "list")
    firewall = sha(str(p.returncode).encode() + b"\0" +
                   p.stdout + b"\0" + p.stderr)
    return {"schema": 1, "config": sha(CONFIG.read_bytes()),
            "firewall": firewall, "wan": "ready", "engine": "absent"}

def prepare():
    need(not RECORD.exists() and not RECORD.is_symlink(),
         "WITNESS_ALREADY_EXISTS")
    before = witness()
    lock_state()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    with RECORD.open("x") as f:
        os.chmod(RECORD, 0o600)
        json.dump(before, f, sort_keys=True)
    print("S05C2C_NATIVE_SAVED_WAN_ABSENT_ENGINE_BEFORE=PASS")

def verify():
    need(RECORD.is_file() and not RECORD.is_symlink(),
         "WITNESS_NOT_PREPARED")
    before = json.loads(RECORD.read_text())
    after = witness()
    need(before == after, "MISSING_ENGINE_START_CHANGED_CONFIG_IPFW_OR_RUNTIME")
    # Physical Start may create the sole original FD9; this is expected
    # original lifecycle bookkeeping, NOT a second lock or no-write claim.
    lock_state()
    RECORD.unlink()
    print("S05C2C_REAL_HTTP_REFUSAL_PRESERVED_CONFIG_IPFW_ENGINE=PASS")

def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            need(sha(b"a") != sha(b"b"), "DIGEST")
            need(not sys.platform.startswith("freebsd") or
                 os.environ.get("ZAPRET2_STAGE5_BROWSER_WAN") != "1",
                 "SELF_TEST_ONLY_HOST")
            print("S05C2C_NATIVE_SELF_TEST=PASS")
        elif sys.argv[1:] == ["--prepare"]:
            prepare()
        elif sys.argv[1:] == ["--verify"]:
            verify()
        else:
            raise Refusal("UNRECOGNIZED_MODE")
    except (Refusal, OSError, ValueError, json.JSONDecodeError) as e:
        print("S05C2C_NATIVE_REFUSED=" + str(e)[:160], file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
