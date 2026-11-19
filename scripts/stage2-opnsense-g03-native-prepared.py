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

def call(argv, *, locked=False, timeout=180, expected_rc=0):
    if locked:
        argv = ["/bin/sh", "-c",
                '(/usr/bin/lockf -s -t 30 9 || exit 75; exec "$@") '
                '9>/var/run/zapret2-lifecycle.lock', "g03-original-fd9", *argv]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "GITHUB_ACTIONS":"true",
                            "ZAPRET2_G03_COLD_PREPARED":"1"})
    if p.returncode != expected_rc:
        # Diagnostic is strictly test-only and does not print private XML,
        # HOSTLIST text or subprocess stdout/command line arguments.
        action = (argv[2] if argv[0] == PHP and len(argv) > 2 else
                  argv[1] if len(argv) > 1 and argv[0] == SERVICE else
                  "unknown")
        allowed = {"stage", "stage-partial", "stage-config", "durable",
                   "crash-partial", "crash-config-save", "shared-apply-prepare",
                   "found-cold", "found-recover", "found-recover-prepared"}
        if action not in allowed:
            action = "unknown"
        reason = re.search(r"G03_[A-Z0-9_]+(?:=REFUSED:[A-Z0-9_]+)?",
                           p.stderr or "")
        reason = reason.group(0) if reason else "NO_TEST_REASON"
        raise RuntimeError("G03_COLD_COMMAND_REFUSED_" + action + "_" +
                           str(p.returncode) + "_" + reason)
    return p.stdout.strip()

def image(path):
    # This function is ONLY an independent no-mutation observation. Native
    # source provenance is enforced separately by the original Python P2
    # under FD9 + Config fd4, not by assuming native PID/config.xml are
    # root-owned single-link HOSTLIST source files.
    name = ({CONFIG: "config", PIDFILE: "pid", **{
        target: ("youtube", "user", "auto")[i]
        for i, target in enumerate(TARGETS)}}).get(path, "foreign")
    need(name != "foreign", "G03_COLD_FOREIGN_SNAPSHOT_PATH")
    if not path.exists() and not path.is_symlink():
        return ("missing",)
    st = path.lstat()
    if path in TARGETS:
        need(st.st_uid == 0 and st.st_nlink == 1 and not path.is_symlink(),
             "G03_COLD_FOREIGN_PROTECTED_" + name)
    if path.is_symlink():
        return ("link", st.st_dev, st.st_ino, st.st_uid, st.st_nlink,
                st.st_mtime_ns, st.st_ctime_ns, os.readlink(path))
    import stat
    need(stat.S_ISREG(st.st_mode), "G03_COLD_NONREGULAR_" + name)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        data = b""
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            data += block
        end = os.fstat(fd)
    finally:
        os.close(fd)
    named = path.lstat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size,
                          x.st_mtime_ns, x.st_ctime_ns)
    need(identity(st) == identity(opened) ==
         identity(end) == identity(named),
         "G03_COLD_SNAPSHOT_RACE_" + name)
    return ("file", st.st_dev, st.st_ino, st.st_uid, st.st_nlink,
            st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns,
            hashlib.sha256(data).hexdigest())

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

def partial_main():
    """Exercise real first-file crash, NOT a mock journal or second writer."""
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_COLD_PREPARED") == "1" and
         sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         Path(NATIVE).is_file() and Path(SERVICE).is_file(),
         "G03_PARTIAL_DISPOSABLE_ONLY")
    previous = json.loads(WAL.read_bytes())
    prior = previous.get("previous")
    need(previous.get("phase") == "restored" and isinstance(prior, dict) and
         prior.get("page") == "strategies" and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 0,
         "G03_PARTIAL_COMMITTED_PREDECESSOR_MISSING")
    original = snapshot()
    staged = call([PHP, NATIVE, "stage-partial"], locked=True)
    need(re.fullmatch(r"prepared-id=[a-f0-9]{32}", staged) is not None and
         snapshot() == original and json.loads(WAL.read_bytes()) == previous,
         "G03_PARTIAL_STAGING_TOUCHED_ORIGINAL")
    op = staged.split("=", 1)[1]
    prepared = call([SERVICE, "shared-apply-prepare", op])
    need(not prepared.startswith("preflight-rejected=") and
         snapshot() == original and json.loads(WAL.read_bytes()) == previous,
         "G03_PARTIAL_DETACHED_BUILD_DRIFT")
    call([PHP, NATIVE, "durable", op], locked=True)
    pending = json.loads(WAL.read_bytes())
    need(pending.get("phase") == "prepared" and
         pending.get("previous") == prior and
         pending.get("detail", {}).get("id") == op and
         snapshot() == original, "G03_PARTIAL_PREPARED_NOT_DURABLE")
    # A separate FreeBSD/PHP process retains the genuine FD4 and FD9,
    # calls the ORIGINAL three-file P2 writer, then exits(73) immediately
    # after its FIRST atomically installed and WAL-pinned YouTube source.
    call([PHP, NATIVE, "crash-partial", op], locked=True)
    crashed = json.loads(WAL.read_bytes())
    broken = snapshot()
    stages = crashed.get("found", {}).get("stages", {})
    need(crashed.get("phase") == "found-files-writing" and
         crashed.get("previous") == prior and
         stages.get("youtube", {}).get("state") == "installed" and
         "user" not in stages and "auto" not in stages and
         broken[0:2] == original[0:2] and broken[3] == original[3] and
         broken[2][0][-1] != original[2][0][-1] and
         broken[2][1:] == original[2][1:] and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 2,
         "G03_PARTIAL_INDETERMINATE_OWNER_OR_FILE_PHASE")
    # Original status explicitly reports "incomplete" for a nonterminal WAL,
    # although the prior PID and IPFW are still physically unchanged.
    # No Start/Restart/Stop may run before the protected cold recovery.
    recovered = json.loads(call([
        PHP, "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php",
        "found-recover", op, "strategies"], locked=True))
    final = json.loads(WAL.read_bytes())
    restored = snapshot()
    need(recovered == {"result": "restored"} and
         final.get("phase") == "restored" and final.get("previous") == prior and
         "found" not in final and
         restored[0:2] == original[0:2] and restored[3] == original[3] and
         restored[2][0][0] == "file" and
         restored[2][0][-1] == original[2][0][-1] and
         restored[2][1:] == original[2][1:] and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 0,
         "G03_PARTIAL_RESTORE_CONFIG_IPFW_OWNER_OR_HOSTLIST_MISMATCH")
    print("G03_COLD_PARTIAL=PASS_ONE_REAL_STAGED_RENAME_RESTORED_ORIGINAL_FD9_CONFIG_P2",
          flush=True)


def config_save_uncertain_main():
    """Real native save returns, but WAL ack is lost with the PHP process."""
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_COLD_PREPARED") == "1" and
         sys.platform.startswith("freebsd") and os.geteuid() == 0,
         "G03_CONFIG_DISPOSABLE_ONLY")
    previous = json.loads(WAL.read_bytes())
    prior = previous.get("previous")
    need(previous.get("phase") == "restored" and isinstance(prior, dict) and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 0,
         "G03_CONFIG_PREVIOUS_RUNNING_OWNER_UNPROVEN")
    original = snapshot()
    staged = call([PHP, NATIVE, "stage-config"], locked=True)
    need(re.fullmatch(r"prepared-id=[a-f0-9]{32}", staged) is not None and
         snapshot() == original and json.loads(WAL.read_bytes()) == previous,
         "G03_CONFIG_STAGING_MUTATED_ACTIVE_STATE")
    op = staged.split("=", 1)[1]
    prepared = call([SERVICE, "shared-apply-prepare", op])
    need(not prepared.startswith("preflight-rejected=") and
         snapshot() == original and json.loads(WAL.read_bytes()) == previous,
         "G03_CONFIG_CANDIDATE_BUILD_REFUSED")
    # Unlike the first-file crash fixture, do NOT pre-create PREPARED.
    # The ORIGINAL found-save entry itself prepares the WAL under real
    # FD9/Config/P2 before writing. A second prepare is correctly forbidden
    # as an unfinished/reused original transaction.
    need(json.loads(WAL.read_bytes()) == previous and snapshot() == original,
         "G03_CONFIG_PRE_SAVE_ORIGINAL_OWNER_DRIFT")
    # Native PHP delegates its ONE actual Config::save to the real OPNsense
    # singleton. The test-only wrapper exit(73)s just AFTER that method
    # returns but BEFORE the original saved-Config acknowledgement can fsync.
    call([PHP, NATIVE, "crash-config-save", op],
         locked=True, expected_rc=73)
    crashed = json.loads(WAL.read_bytes())
    saved = snapshot()
    found = crashed.get("found", {})
    stages = found.get("stages", {})
    need(crashed.get("phase") == "found-config-saving" and
         crashed.get("previous") == prior and
         set(found.get("post", {})) == {"youtube", "user", "auto"} and
         all(stages.get(k, {}).get("state") == "installed"
             for k in ("youtube", "user", "auto")) and
         saved[0][-1] != original[0][-1] and
         saved[1] == original[1] and saved[3] == original[3] and
         all(saved[2][i] != original[2][i] for i in range(3)) and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 2,
         "G03_CONFIG_UNACKED_NATIVE_SAVE_NOT_PROVEN")
    worker = "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php"
    cold = json.loads(call([PHP, worker, "found-cold", op, "strategies"],
                           locked=True))
    need(cold.get("journal_phase") == "found-config-saving" and
         cold.get("config_image") == "candidate-image" and
         cold.get("file_image") == "contains-unattributed-after" and
         cold.get("commit_authorized") is False and
         cold.get("restore_authorized") is False and
         cold.get("save_attested") is False,
         "G03_CONFIG_COLD_EVIDENCE_FALSE_AUTHORITY")
    # Candidate bytes do not prove the interrupted PHP process confirmed
    # its save. This cold request MUST FAIL, leaving WAL, Config, all
    # protected files and the ORIGINAL engine/PID/IPFW untouched.
    call([PHP, worker, "found-recover", op, "strategies"],
         locked=True, expected_rc=69)
    need(json.loads(WAL.read_bytes()) == crashed and snapshot() == saved and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 2,
         "G03_CONFIG_COLD_REFUSAL_MUTATED_PREVIOUS_OWNER")
    print("G03_COLD_CONFIG=PASS_NATIVE_SAVE_RETURN_UNACKED_CANDIDATE_REFUSED",
          flush=True)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["partial"]:
            partial_main()
        elif sys.argv[1:] == ["config-uncertain"]:
            config_save_uncertain_main()
        else:
            need(sys.argv[1:] == [], "G03_COLD_UNEXPECTED_ARGUMENTS")
            main()
    except (RuntimeError, OSError, ValueError, KeyError,
            subprocess.TimeoutExpired) as exc:
        label = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        prefix = ("G03_COLD_PARTIAL" if sys.argv[1:] == ["partial"] else
                  "G03_COLD_CONFIG" if sys.argv[1:] == ["config-uncertain"] else
                  "G03_COLD_PREPARED")
        print(prefix + "=REFUSED:" + label, file=sys.stderr)
        raise SystemExit(1)
