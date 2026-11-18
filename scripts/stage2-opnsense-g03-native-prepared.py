#!/usr/bin/env python3
"""Disposable installed G03: prove original PREPARED no-write cold closure."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

NATIVE = "/root/g03-native-prepared.php"
PHP = "/usr/local/bin/php"
SERVICE = "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
CONFIG = Path("/conf/config.xml")
WAL = Path("/var/db/zapret2/shared-apply/operation.json")
PIDFILE = Path("/var/run/dvtws2.pid")
TARGETS = [
    Path("/var/db/zapret2/auto-detect-owned/youtube.txt"),
    Path("/var/db/zapret2/auto-detect-owned/user.txt"),
    Path("/usr/local/etc/zapret2/ipset/auto-domains.txt"),
]

def need(ok, code):
    if not ok:
        raise RuntimeError(code)

def call(argv, *, locked=False, timeout=180):
    if locked:
        argv = ["/bin/sh", "-c",
                '(/usr/bin/lockf -s -t 30 9 || exit 75; exec "$@") '
                '9>/var/run/zapret2-lifecycle.lock', "g03-original-fd9", *argv]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "GITHUB_ACTIONS":"true",
                            "ZAPRET2_G03_COLD_PREPARED":"1"})
    need(p.returncode == 0, "G03_COLD_COMMAND_REFUSED_" + str(p.returncode))
    return p.stdout.strip()

def image(path):
    if not path.exists() and not path.is_symlink():
        return ("missing",)
    st = path.lstat()
    need(st.st_uid == 0 and st.st_nlink == 1 and not path.is_symlink(),
         "G03_COLD_FOREIGN_SOURCE")
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest())

def snapshot():
    return (image(CONFIG), image(PIDFILE), tuple(image(x) for x in TARGETS),
            tuple((p.returncode, hashlib.sha256(p.stdout).hexdigest())
                  for p in [
                      subprocess.run(["/sbin/ipfw","-q","list"],
                                     capture_output=True, timeout=10),
                      subprocess.run(["/sbin/ipfw","table","all","list"],
                                     capture_output=True, timeout=10),
                  ]))

def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_COLD_PREPARED") == "1" and
         sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         Path(NATIVE).is_file() and Path(SERVICE).is_file(),
         "G03_COLD_DISPOSABLE_FREEBSD_ONLY")
    previous = json.loads(WAL.read_bytes())
    need(previous.get("phase") == "committed" and
         previous.get("detail", {}).get("page") == "strategies" and
         subprocess.run([SERVICE, "status"], timeout=30).returncode == 0,
         "G03_COLD_PREVIOUS_RUNNING_OWNER_UNPROVEN")
    original = snapshot()
    staged = call([PHP, NATIVE, "stage"], locked=True)
    need(re.fullmatch(r"prepared-id=[a-f0-9]{32}", staged) is not None and
         snapshot() == original and json.loads(WAL.read_bytes()) == previous,
         "G03_COLD_STAGE_CHANGED_ORIGINAL_OWNER")
    op = staged.split("=",1)[1]
    prepared = call([SERVICE, "shared-apply-prepare", op])
    need(not prepared.startswith("preflight-rejected=") and
         snapshot() == original and json.loads(WAL.read_bytes()) == previous,
         "G03_COLD_BUILD_TOUCHED_OR_REFUSED_OWNER")
    call([PHP, NATIVE, "durable", op], locked=True)
    pending = json.loads(WAL.read_bytes())
    need(pending.get("phase") == "prepared" and
         pending.get("detail", {}).get("id") == op and
         pending.get("previous") == previous["detail"] and
         "found" in pending and snapshot() == original,
         "G03_COLD_PREPARED_NOT_DURABLE_OR_LIVE_OWNER_DRIFT")
    receipt = json.loads(call([
        PHP, "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php",
        "found-recover-prepared", op, "strategies"], locked=True))
    restored = json.loads(WAL.read_bytes())
    need(receipt == {
             "result":"original-found-prepared-pristine-restored",
             "phase":"restored", "previous_id":previous["detail"]["id"],
             "runtime_state":"ready", "config_saved":False,
             "files_written":False, "service_restarted":False
         } and restored.get("phase") == "restored" and
         restored.get("previous") == previous["detail"] and
         "found" not in restored and snapshot() == original and
         subprocess.run([SERVICE, "status"], timeout=30).returncode == 0,
         "G03_COLD_RESTORED_PREVIOUS_OWNER_UNPROVEN")
    print("G03_COLD_PREPARED=PASS_ORIGINAL_FD9_CONFIG_FD4_P2_NO_WRITES",
          flush=True)

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError,
            subprocess.TimeoutExpired) as exc:
        label = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print("G03_COLD_PREPARED=REFUSED:" + label, file=sys.stderr)
        raise SystemExit(1)
