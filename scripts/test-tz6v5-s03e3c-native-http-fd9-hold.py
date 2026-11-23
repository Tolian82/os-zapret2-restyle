#!/usr/bin/env python3
"""TZ6v5 S03e3c: live PHP HTTP Stop/Restart RED while genuine original FD9 BUSY.

Only on a fresh disposable OPNsense 26.7 guest; called over the disposable
CI-only SSH key by installed Chromium test. Never touches an owner router.
It holds FD9 THROUGH both real HTTP requests, including delayed configd child
drain. No physical Stop/Restart can enter service_dispatch in this interval.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time

LOCK = Path("/var/run/zapret2-lifecycle.lock")
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
PKG_PENDING = Path("/var/db/zapret2/pkg-update/operation.json")
PUBKEY = Path("/root/s03e3c-disposable-ci.pub")
SOURCE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ACTIONS = Path("/usr/local/opnsense/service/conf/actions.d/actions_zapret.conf")
NO_RELEASE_BEFORE = 112

class Refuse(Exception):
    pass

def need(condition, reason):
    if not condition:
        raise Refuse(reason)

def cmd(argv, timeout=15, pass_fds=()):
    try:
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=False, pass_fds=pass_fds)
    except (OSError, subprocess.SubprocessError):
        raise Refuse("S03E3C_NATIVE_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None

def digest(value):
    return hashlib.sha256(value).hexdigest()

def verify_disposable():
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_STAGE5_BROWSER_WAN") == "1",
         "S03E3C_DISPOSABLE_FREEBSD_ONLY")
    auth = Path("/root/.ssh/authorized_keys")
    need(PUBKEY.is_file() and not PUBKEY.is_symlink() and
         auth.is_file() and not auth.is_symlink() and
         PUBKEY.read_bytes().strip() in auth.read_bytes().splitlines(),
         "S03E3C_EXACT_DISPOSABLE_SSH_KEY_NOT_ATTESTED")
    need(all(p.is_file() and not p.is_symlink()
             for p in (SOURCE, ACTIONS, CONFIG)),
         "S03E3C_INSTALLED_SOURCE_UNAVAILABLE")
    need(cmd(["pkg", "info", "-e", "os-zapret2-restyle"]).returncode == 0 and
         cmd(["opnsense-version", "-a"]).stdout.strip() == b"26.7",
         "S03E3C_WRONG_INSTALLED_GUEST")
    need(not ENGINE.exists() and not ENGINE.is_symlink() and
         not PKG_PENDING.exists() and not PKG_PENDING.is_symlink() and
         not Path("/var/run/zapret2-restyle/pkg-replacement.restart").exists(),
         "S03E3C_ENGINE_OR_PENDING_UPGRADE")
    src, actions = SOURCE.read_text(), ACTIONS.read_text()
    need("LIFECYCLE_LOCK_FILE=" in src and str(LOCK) in src and
         "service_with_lifecycle_lock" in src and "LOCKF_BIN" in src,
         "S03E3C_ORIGINAL_FD9_ENTRY_CHANGED")
    for verb in ("stop", "restart"):
        need("[" + verb + "]\ncommand:" + str(SOURCE) + " " + verb + "\n" in actions,
             "S03E3C_CONFIGD_ROUTE_CHANGED_" + verb)
    need(not LOCK.is_symlink(), "S03E3C_ORIGINAL_FD9_SYMLINK")
    if LOCK.exists():
        s = LOCK.stat()
        need(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and
             not s.st_mode & 0o022 and s.st_nlink == 1,
             "S03E3C_UNQUALIFIED_ORIGINAL_FD9_FILE")

def census():
    p = cmd(["ps", "-axo", "command="])
    need(p.returncode == 0 and
         b"dvtws2" not in p.stdout and
         b"supervisor_loop.sh" not in p.stdout and
         b"strategy_lab_worker.sh" not in p.stdout,
         "S03E3C_ENGINE_OR_LAB_OWNER_PRESENT")
    return p.stdout

def snapshot():
    processes = census()
    rules = cmd(["/sbin/ipfw", "-q", "list"])
    need(CONFIG.is_file() and not CONFIG.is_symlink(),
         "S03E3C_CONFIG_LOST")
    return (digest(CONFIG.read_bytes()),
            digest(str(rules.returncode).encode() + b"\0" +
                   rules.stdout + b"\0" + rules.stderr),
            not ENGINE.exists(), bool(processes))

def trylock():
    return cmd(["/bin/sh", "-c", 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',
                "s03e3c-independent-fd9-contender", str(LOCK)], 5).returncode

def acquire_original_fd9():
    need(trylock() == 0, "S03E3C_FD9_ALREADY_BUSY")
    flags = os.O_WRONLY | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(LOCK, flags, 0o600)
    try:
        s = os.fstat(fd)
        need(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and
             s.st_nlink == 1 and not s.st_mode & 0o022,
             "S03E3C_FD9_FILE_NOT_ROOT_OWNED")
        os.dup2(fd, 9, inheritable=True)
    finally:
        if fd != 9:
            os.close(fd)
    ret = cmd(["/usr/bin/lockf", "-s", "-t", "0", "9"], 5, pass_fds=(9,))
    need(ret.returncode == 0 and trylock() != 0,
         "S03E3C_REAL_FD9_HOLDER_NOT_ATTESTED")

def wait_out_async_children():
    deadline = time.monotonic() + 85
    while True:
        processes = census()
        if not re.search(rb"/zapret_service\.sh (?:stop|restart)(?:\s|$)",
                         processes):
            return
        need(time.monotonic() < deadline,
             "S03E3C_PENDING_CONFIGD_CHILD_DID_NOT_EXIT")
        time.sleep(2)

def hold():
    verify_disposable()
    before = snapshot()
    start = time.monotonic()
    # Ignore SSH hangup: the guest must NOT release FD9 early after a failed
    # host-side browser step while a configd child might still be pending.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    acquire_original_fd9()
    print("S03E3C_ORIGINAL_FD9_BUSY_READY", flush=True)
    success = False
    try:
        # Host sends VERIFY only after BOTH real PHP HTTP responses. EOF is a
        # failure, but must still retain the lock through the safety drain.
        r, _, _ = select.select([sys.stdin], [], [], 135)
        line = sys.stdin.readline().strip() if r else ""
        success = line == "VERIFY"
        wait_out_async_children()
        remaining = NO_RELEASE_BEFORE - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(remaining)
        need(trylock() != 0, "S03E3C_LOCK_LOST_DURING_HTTP_REQUESTS")
        need(before == snapshot(), "S03E3C_HTTP_CHANGED_CONFIG_IPFW_OR_ENGINE")
        need(success, "S03E3C_CLIENT_DID_NOT_VERIFY_TWO_REAL_HTTP_REQUESTS")
        print("S03E3C_NATIVE_HTTP_CONFIG_IPFW_ENGINE_UNCHANGED=PASS", flush=True)
    finally:
        # Deliberately keep the original FD9 held until the fixed safety
        # period even on parsing/errors/disconnected host.
        remaining = NO_RELEASE_BEFORE - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(remaining)
        os.close(9)

def selftest():
    need(digest(b"one") != digest(b"two") and NO_RELEASE_BEFORE >= 90,
         "S03E3C_GUARD_SELFTEST_FAILED")
    print("S03E3C_GUEST_HOLDER_SELFTEST=PASS")

def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            selftest()
        elif sys.argv[1:] == ["--hold"]:
            hold()
        else:
            raise Refuse("S03E3C_USAGE_REFUSED")
        return 0
    except (Refuse, OSError, ValueError) as exc:
        print("S03E3C_GUEST_REFUSED=" + str(exc)[:150], file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
