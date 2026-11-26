#!/usr/bin/env python3
"""Disposable installed G03: prove original PREPARED no-write cold closure."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

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
        allowed = {"stage", "stage-partial", "stage-config", "stage-ordinary", "durable",
                   "crash-partial", "crash-config-save", "shared-apply-prepare",
                   "found-cold", "found-recover", "found-recover-prepared",
                   "attest", "bind"}
        if action not in allowed:
            action = "unknown"
        diagnostics = re.findall(
            r"^G03_(?:FIRST|MANAGED)_REPLY=rc:(?:-?[0-9]{1,3}|unknown);receipt:(?:invalid|empty|exact|mismatch);"
            r"wal:(?:prepared|activating|activated|config-saved|managed-writing|managed-config-saving|committed|restored|requires-review|unknown);"
            r"stderr:(?:save-uncertain|review|other|empty)$", p.stderr or "", re.MULTILINE)
        for trace in re.findall(
            r"^(?:G03_FIRST_TRACE=D(?:[012][0-9]|3[0-4])|G03_MANAGED_TRACE=(?:D(?:[012][0-9]|3[0-4])|(?:M(?:0[1-9]|1[0-4])|P0[1-3]):[1-9][0-9]{0,4})|G03_MANAGED_STEP=(?:write|begin|confirm|recover))$",
            p.stderr or "", re.MULTILINE)[:64]:
            print(trace, flush=True)
        if len(diagnostics) == 1:
            print(diagnostics[0], flush=True)
        reason = (re.search(r"^G03_BOUND_NATIVE_REFUSED_[A-Z0-9_]{1,100}$",
                            p.stderr or "", re.MULTILINE) or
                  re.search(r"G03_[A-Z0-9_]+(?:=REFUSED:[A-Z0-9_]+)?", p.stderr or ""))
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
    # Same original FD9 and genuine PHP Config FD4. Read-only P2/CAS.
    attested = call([PHP, NATIVE, "attest", op], locked=True)
    need(attested == "original-found-prepared-source-cas-attested" and
         json.loads(WAL.read_bytes()) == pending and snapshot() == original,
         "G03_S10_FOUND_PREPARED_SOURCE_CAS_DRIFT")
    print("G03_S10_FOUND_SOURCE_CAS=PASS_REAL_ORIGINAL_FD4_FD9_P2_SEAL_NO_WRITES",
          flush=True)
    # Real candidate sibling + single original WAL bind, in the actual
    # inherited native Config FD4/FD9/P2 route. The old running owner is
    # legacy (unbound); do not forge a committed old immutable manifest.
    work = Path("/var/db/zapret2/shared-work") / op
    root = work / "manifest.json"
    seal = (work / "bundle-seal.json").read_bytes()
    need("manifest" not in pending and "previous_manifest" not in pending
         and not root.exists() and not root.is_symlink(),
         "G03_FOUND_BIND_INITIAL_PREIMAGE_REQUIRED")
    result = call([PHP, NATIVE, "bind", op], locked=True)
    bound = json.loads(WAL.read_bytes())
    pin = bound.get("manifest", {})
    need(result == "original-found-prepared-root-bound" and
         bound == dict(pending, manifest=pin) and
         pin.get("generation") == op and
         pin.get("candidate_sha256") == pending["detail"]["candidate"] and
         root.is_file() and not root.is_symlink() and
         pin.get("root_sha256") == hashlib.sha256(root.read_bytes()).hexdigest() and
         pin.get("seal_sha256") == hashlib.sha256(seal).hexdigest() and
         (work / "bundle-seal.json").read_bytes() == seal and
         snapshot() == original,
         "G03_FOUND_NATIVE_BOUND_OR_PHYSICAL_DRIFT")
    print("G03_S10_FOUND_BIND=PASS_REAL_FD4_FD9_P2_LEGACY_PREDECESSOR_NO_WRITES",
          flush=True)
    print("G03_S10_FOUND_SEMANTIC=PASS_REAL_LEGACY_RESTART_REQUIRED_NO_ACTION",
          flush=True)
    # Separate native PHP owner invocation after the binding child has
    # exited: recovery must rediscover the immutable candidate from disk.
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
         restored.get("manifest") == pin and
         "previous_manifest" not in restored and
         pin["root_sha256"] == hashlib.sha256(root.read_bytes()).hexdigest() and
         (work / "bundle-seal.json").read_bytes() == seal and
         "found" not in restored and snapshot() == original and
         subprocess.run([SERVICE, "status"], timeout=30).returncode == 0,
         "G03_COLD_RESTORED_PREVIOUS_OWNER_UNPROVEN")
    print("G03_COLD_PREPARED=PASS_ORIGINAL_FD9_CONFIG_FD4_P2_NO_WRITES",
          flush=True)
    print("G03_S10_FOUND_BIND_RECOVER=PASS_REAL_NATIVE_PREPARED_NO_PHYSICAL_TRANSITION",
          flush=True)


def verify_first_bound_commit(record, op, receipt, root, original, saved, status):
    """Test-only readback: no success based solely on coordinator stdout."""
    detail = record.get("detail", {})
    pin = record.get("manifest", {})
    need(record.get("phase") == "committed" and detail.get("id") == op and
         detail.get("page") == "strategies" and detail.get("base") != detail.get("candidate") and
         detail.get("changed_fields") == ["hostlist.mode"] and
         "previous" not in record and "previous_manifest" not in record and "found" not in record and
         pin.get("schema") == 1 and pin.get("generation") == op and
         pin.get("candidate_sha256") == detail.get("candidate") and
         re.fullmatch(r"[a-f0-9]{64}", record.get("first_running_sha256", "")) is not None and
         root.is_file() and not root.is_symlink() and
         receipt == "G03_BOUND_NATIVE_COMMIT=" + hashlib.sha256(root.read_bytes()).hexdigest() and
         pin.get("root_sha256") == receipt.split("=", 1)[1],
         "G03_FIRST_BOUND_COMMIT_WAL_OR_PIN_UNPROVEN")
    need(saved == {"result": "committed", "snapshot": detail["candidate"], "enabled": "1"} and
         status.returncode == 0 and status.stdout.strip() == "zapret is running" and
         PIDFILE.is_file() and not PIDFILE.is_symlink() and
         re.fullmatch(r"[1-9][0-9]*", PIDFILE.read_text().strip()) is not None and
         snapshot()[2] == original[2],
         "G03_FIRST_BOUND_COMMIT_NATIVE_READBACK_UNPROVEN")


def verify_successor_commit(record, previous, op, receipt, root, original,
                            observed, saved, status, saved_list, expected_list):
    """Independent terminal readback of one linked-list change."""
    detail = record.get("detail", {})
    pin = record.get("manifest", {})
    need(record.get("phase") == "committed" and detail.get("id") == op and
         op != previous["detail"]["id"] and detail.get("page") == "strategies" and
         detail.get("base") == previous["detail"]["candidate"] and
         detail.get("candidate") != detail.get("base") and
         detail.get("changed_fields") == ["hostlist.youtubedomains"] and
         record.get("previous") == previous["detail"] and
         record.get("previous_manifest") == previous["manifest"] and
         "managed" not in record and "found" not in record and
         pin.get("schema") == 1 and pin.get("generation") == op and
         pin.get("candidate_sha256") == detail["candidate"] and
         pin.get("root_sha256") != previous["manifest"]["root_sha256"] and
         root.is_file() and not root.is_symlink() and
         receipt == "G03_BOUND_SUCCESSOR_COMMIT=" + hashlib.sha256(root.read_bytes()).hexdigest() and
         pin.get("root_sha256") == receipt.split("=", 1)[1],
         "G03_BOUND_SUCCESSOR_WAL_OR_PIN_UNPROVEN")
    need(saved == {"result": "committed", "snapshot": detail["candidate"], "enabled": "1"} and
         saved_list.splitlines() == expected_list.splitlines() and
         status.returncode == 0 and status.stdout.strip() == "zapret is running" and
         observed[1:] == original[1:] and observed[0] != original[0],
         "G03_BOUND_SUCCESSOR_NATIVE_READBACK_UNPROVEN")


def bound_manifest_main(*, stopped=False, cold=False, first_commit=False, successor=False):
    """Existing PREPARED proofs, plus the disposable first/successor commits.

    The STOPPED branch follows an explicit service stop on the guest.
    Only the opt-in two-generation journey calls the original coordinator.
    """
    script = Path(SERVICE).parent
    backend = script / "backend"
    def journal():
        return (None if not WAL.exists() and not WAL.is_symlink()
                else json.loads(WAL.read_bytes()))

    previous = journal()
    prior = None if previous is None else previous.get("detail" if successor else "previous")
    expected_status = 1 if stopped or cold else 0
    native_status = subprocess.run([SERVICE, "status"], capture_output=True,
                                   text=True, timeout=30)
    need(not (cold and stopped) and (not first_commit or cold) and
         (not successor or not (cold or stopped or first_commit)) and
         (previous is None if cold else (
             isinstance(previous, dict) and
             previous.get("phase") == ("committed" if successor else "restored") and
             isinstance(prior, dict))) and
         native_status.returncode == expected_status and
         (not cold or native_status.stdout.strip() == "zapret is not running"),
         "G03_BOUND_PREVIOUS_OWNER_STATE_UNPROVEN")
    original = snapshot()
    expected_list = None
    if cold:
        # G03's existing native lo0 fixture, before the first ordinary Apply.
        # Use the actual original native request worker, not a fabricated XML.
        model = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
        need(model is not None and
             model.findtext("general/enabled") == "1" and
             model.findtext("general/waninterface") == "lo0" and
             model.findtext("hostlist/mode", "all") == "all",
             "G03_PRISTINE_COLD_NATIVE_SAVED_MODEL_UNPROVEN")
        request = {"page": "strategies", "fields": {"hostlist": {"mode": "list"}},
                   "sync": {"telegramips_baseline":
                            model.findtext("hostlist/telegramips") or ""}}
        encoded = base64.urlsafe_b64encode(json.dumps(
            request, separators=(",", ":")).encode()).decode().rstrip("=")
        staged = call([PHP, str(script / "shared_apply_request.php"), "stage",
                       encoded], locked=True)
    elif successor:
        model = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
        need(model is not None and model.findtext("general/enabled") == "1" and
             model.findtext("hostlist/mode") == "list" and
             model.findtext("general/waninterface") == "lo0",
             "G03_BOUND_SUCCESSOR_SAVED_MODEL_UNPROVEN")
        old_list = model.findtext("hostlist/youtubedomains") or ""
        domain = "s10-g03-successor.example.org"
        need(domain not in old_list.splitlines(), "G03_BOUND_SUCCESSOR_DOMAIN_PRESENT")
        expected_list = old_list + ("" if not old_list or old_list.endswith("\n") else "\n") + domain
        request = {"page": "strategies", "fields": {"hostlist": {"youtubedomains": expected_list}},
                   "sync": {"telegramips_baseline": model.findtext("hostlist/telegramips") or ""}}
        encoded = base64.urlsafe_b64encode(json.dumps(
            request, separators=(",", ":")).encode()).decode().rstrip("=")
        staged = call([PHP, str(script / "shared_apply_request.php"), "stage", encoded], locked=True)
    else:
        staged = call([PHP, NATIVE, "stage-ordinary"], locked=True)
    need(re.fullmatch(r"prepared-id=[a-f0-9]{32}", staged) is not None and
         snapshot() == original and journal() == previous,
         "G03_BOUND_ORDINARY_STAGE_DRIFT")
    op = staged.split("=", 1)[1]
    prepared = call([SERVICE, "shared-apply-prepare", op])
    need(not prepared.startswith("preflight-rejected=") and
         snapshot() == original and journal() == previous,
         "G03_BOUND_ORIGINAL_SEAL_BUILD_REFUSED")
    # The test uses the actual native rendered template / original loader
    # and exact NUL wire under the existing original FreeBSD FD9. The
    # installed backend, PHP Config, setup marker, Git/ELF, root and WAL
    # writer are all real; there is no fixture replacement of them.
    shell = r'''
set -eu
script=/usr/local/opnsense/scripts/OPNsense/Zapret
work="/var/db/zapret2/shared-work/$1"
. "$script/backend/config.sh"
config_load "$work/templates/usr/local/etc/zapret2/zapret.conf"
{
    printf 'S10C2B1_ORIGINAL_INPUT_V1\0'
    printf '%s\0' "${TRAFFIC_ARGS:-}" "${YOUTUBE_DOMAINS:-}" "${USER_DOMAINS:-}" \
        "${TELEGRAM_IPS:-}" "${DISCORD_IPS:-}" "${X_IPS:-}" \
        "${SIP_IPS:-}" "${CUSTOM_IPS:-}" "${EXCLUDE_DOMAINS:-}" \
        "${EXCLUDE_IPSET:-}" "${HOSTLIST_MODE:-}" "${DIVERT_PORT:-}" "${WAN_IF:-}"
} | "$script/python_runtime.sh" -c "$2" "$1" "$3"
'''
    child = r'''
import sys
import json
from hashlib import sha256
from pathlib import Path
sys.path.insert(0, "/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
from shared_apply_operation import SharedApplyOperation, SharedOperationError
from shared_apply_seal import WORK, verify_seal, _release_hash
from neutral_root_stage import verify_original_operation_pins
from neutral_schema3_previous_physical import (
    CompletePriorPreimage, _full_prior_tree, _running_native, COMMON_ACTIVE, CHILD_PID, MONITOR_PID)
from neutral_schema3_saved_wan_preimage import _native_preflight
from neutral_schema3_quiescent_preimage import QuiescentPreimage
from neutral_shared_apply_source_gate import (
    native_bind_original_prepared_fd9, native_plan_original_prepared_fd9,
    native_coordinate_original_prepared_fd9, MAX_PIPE)
from voice_ipfw_adapter import require_lifecycle_lock
def first_trace_lines(raw):
    if type(raw) is not bytes or len(raw) > 16384:
        return ()
    allowed = {f"S10_FIRST_TRACE=D{i:02d}".encode() for i in range(35)}
    return tuple(line for line in raw.split(b"\n")[:-1] if line in allowed)[:64]

def managed_trace_lines(raw):
    import re
    if type(raw) is not bytes or len(raw) > 16384:
        return ()
    return tuple(line for line in raw.split(b"\n")[:-1] if re.fullmatch(
        rb"(?:S10_FIRST_TRACE=D(?:[012][0-9]|3[0-4])|S10_MANAGED_(?:TRACE=(?:M(?:0[1-9]|1[0-4])|P0[1-3]):[1-9][0-9]{0,4}|STEP=(?:write|begin|confirm|recover)))",
        line))[:64]


def coordinate_managed_diagnosed(op, raw, store, detail, coordinate):
    # Observe the exact joined call once; never alter its reply or retry it.
    import neutral_schema3_quiescent_preimage as quiescent
    original_join = quiescent._run_bound_restore_joined

    def diagnosed_join(command, **kwargs):
        reply = original_join(command, **kwargs)
        if list(command[-3:]) == ["managed-apply", op, "strategies"]:
            try:
                observed = store.read()
            except (OSError, RuntimeError, ValueError):
                observed = None
            for line in managed_trace_lines(reply.stderr):
                if line.startswith(b"S10_FIRST_TRACE="):
                    print("G03_MANAGED_TRACE=" + line[-3:].decode("ascii"), file=sys.stderr)
                else:
                    print("G03_" + line[4:].decode("ascii"), file=sys.stderr)
            print(first_reply_diagnostic(reply, observed, detail).replace(
                "G03_FIRST_REPLY=", "G03_MANAGED_REPLY=", 1), file=sys.stderr)
        return reply

    quiescent._run_bound_restore_joined = diagnosed_join
    try:
        return coordinate(op, raw)
    finally:
        quiescent._run_bound_restore_joined = original_join


def first_reply_diagnostic(reply, record, detail):
    # Never disclose Config, HOSTLIST, argv, digests or untrusted stderr.
    phase = record.get("phase") if type(record) is dict else None
    if phase not in ("prepared", "activating", "activated", "config-saved", "managed-writing", "managed-config-saving", "committed", "restored", "requires-review"):
        phase = "unknown"
    rc = reply.returncode
    rc = str(rc) if type(rc) is int and -255 <= rc <= 255 else "unknown"
    shape = "invalid"
    raw = reply.stdout
    if type(raw) is bytes and not raw:
        shape = "empty"
    elif (type(raw) is bytes and 0 < len(raw) <= 4096 and
          raw.count(b"\n") == 1 and raw.endswith(b"\n")):
        try:
            value = json.loads(raw)
            expected = {"result": "saved", "saved": True, "applied": False,
                        "snapshot": detail["candidate"], "change_count": len(detail["changed_fields"])}
            shape = "exact" if json.dumps(value, sort_keys=True) == json.dumps(expected, sort_keys=True) else "mismatch"
        except (ValueError, TypeError, RecursionError):
            pass
    stderr = reply.stderr
    if type(stderr) is bytes and len(stderr) <= 16384:
        import re
        stderr = re.sub(rb"(?m)^S10_FIRST_TRACE=D(?:[012][0-9]|3[0-4])\n", b"", stderr)
        stderr = re.sub(rb"(?m)^S10_MANAGED_(?:TRACE=(?:M(?:0[1-9]|1[0-4])|P0[1-3]):[1-9][0-9]{0,4}|STEP=(?:write|begin|confirm|recover))\n", b"", stderr)
    err = {b"ERROR: native shared Config save uncertain; retain recovery evidence\n": "save-uncertain",
           b"ERROR: original managed Config outcome requires journal review\n": "review"}.get(stderr, "other")
    if stderr == b"":
        err = "empty"
    return "G03_FIRST_REPLY=rc:" + rc + ";receipt:" + shape + ";wal:" + phase + ";stderr:" + err

op, mode = sys.argv[1:]
try:
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    prior = store.read()
    if mode not in ("running", "stopped", "cold", "first-commit", "successor"):
        raise RuntimeError("mode")
    if mode in ("cold", "first-commit"):
        if prior is not None:
            raise RuntimeError("G03_PRISTINE_COLD_WAL_ALREADY_PRESENT")
        old_owner = None
    elif mode == "successor":
        if (not isinstance(prior, dict) or prior["phase"] != "committed" or
                prior.get("manifest", {}).get("schema") != 1 or
                "previous" in prior or "previous_manifest" in prior or "found" in prior or
                "first_running_sha256" not in prior or "failure" in prior):
            raise RuntimeError("G03_BOUND_SUCCESSOR_PREDECESSOR_REQUIRED")
        old_owner = prior["detail"]
        verify_original_operation_pins(record=prior, parent=WORK, owner_uid=0)
        old_work = WORK / old_owner["id"]
        old_release = old_work / "release"
        old_tree = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
        running = _running_native(old_release, owner_uid=0, child_pidfile=CHILD_PID,
                                  monitor_pidfile=MONITOR_PID)
    else:
        if not isinstance(prior, dict) or prior["phase"] != "restored" or not prior.get("previous"):
            raise RuntimeError("previous")
        old_owner = prior["previous"]
    seal = verify_seal(WORK / op, owner=0)
    native = _native_preflight(op, "strategies")
    if native["enabled"] != "1" or native["result"] != "prepared":
        raise RuntimeError("candidate")
    detail = {"id": op, "page": "strategies", "base": native["base"],
              "candidate": native["candidate"], "changed_fields": native["fields"]}
    if mode == "successor":
        if (detail["base"] != old_owner["candidate"] or detail["base"] == detail["candidate"] or
                detail["changed_fields"] != ["hostlist.youtubedomains"] or store.read() != prior):
            raise RuntimeError("G03_BOUND_SUCCESSOR_PLAN_CHANGED")
        new_release = WORK / op / "release"
        name = "managed/hostlist-youtube.txt"
        before = (old_release / name).read_bytes()
        after = (new_release / name).read_bytes()
        new_tree = seal["sha256"]["release"]
        # Refuse any other release change before invoking the physical writer.
        marker = b"s10-g03-successor.example.org"
        if (before == after or marker in before.splitlines() or marker not in after.splitlines() or
                _release_hash(old_release, 0, replacement=(
                    name, sha256(before).hexdigest(), sha256(after).hexdigest())) != new_tree):
            raise RuntimeError("G03_BOUND_SUCCESSOR_NOT_SINGLE_FILE_DELTA")
    store.advance("prepared", detail)
    raw = sys.stdin.buffer.read(MAX_PIPE + 1)
    if mode == "successor":
        route, committed, source, semantic = coordinate_managed_diagnosed(
            op, raw, store, detail, native_coordinate_original_prepared_fd9)
        if (route != "managed-committed" or store.read() != committed or
                committed.get("phase") != "committed" or committed.get("detail") != detail or
                committed.get("previous") != old_owner or
                committed.get("previous_manifest") != prior["manifest"] or
                source.mode != "list" or source.requested_enabled is not True or
                semantic.lifecycle_proposal != "RELOAD" or
                semantic.decision.kind != "RELOAD_SAFE_CANDIDATE" or
                semantic.decision.changed_active != ("hostlist-youtube.txt",) or
                semantic.decision.changed_inactive or
                type(semantic.previous_physical) is not CompletePriorPreimage or
                semantic.previous_generation != old_owner["id"] or
                semantic.previous_root_sha256 != prior["manifest"]["root_sha256"] or
                semantic.candidate_root_sha256 != committed["manifest"]["root_sha256"]):
            raise RuntimeError("G03_BOUND_SUCCESSOR_COORDINATOR_OUTCOME_UNPROVEN")
        verify_original_operation_pins(record=committed, parent=WORK, owner_uid=0)
        if (_full_prior_tree(WORK / op, COMMON_ACTIVE, 0) != new_tree or
                verify_seal(old_work, owner=0)["sha256"]["release"] != old_tree or
                _running_native(new_release, owner_uid=0, child_pidfile=CHILD_PID,
                                monitor_pidfile=MONITOR_PID) != running or
                store.read() != committed):
            raise RuntimeError("G03_BOUND_SUCCESSOR_PHYSICAL_OWNER_CHANGED")
        print("G03_BOUND_SUCCESSOR_COMMIT=" + committed["manifest"]["root_sha256"])
        raise SystemExit(0)
    if mode == "first-commit":
        # Test-only observer of the same joined PHP call; never replace its
        # result, repeat the action, or mutate the original journal.
        import neutral_schema3_quiescent_preimage as quiescent
        import json
        original_join = quiescent._run_bound_restore_joined
        def diagnosed_join(command, **kwargs):
            reply = original_join(command, **kwargs)
            if list(command[-3:]) == ["first-enabled-apply", op, "strategies"]:
                try:
                    observed = store.read()
                except (OSError, RuntimeError, ValueError):
                    observed = None
                for line in first_trace_lines(reply.stderr):
                    print("G03_FIRST_TRACE=" + line[-3:].decode("ascii"), file=sys.stderr)
                print(first_reply_diagnostic(reply, observed, detail), file=sys.stderr)
            return reply
        quiescent._run_bound_restore_joined = diagnosed_join
        try:
            route, committed, source, semantic = native_coordinate_original_prepared_fd9(op, raw)
        finally:
            quiescent._run_bound_restore_joined = original_join
        if (route != "first-enabled-committed" or store.read() != committed or
                committed.get("phase") != "committed" or committed.get("detail") != detail or
                source.mode != "list" or source.requested_enabled is not True or
                semantic.lifecycle_proposal != "START" or
                type(semantic.previous_physical) is not QuiescentPreimage or
                semantic.previous_physical.old_state != "first-install-empty" or
                semantic.candidate_root_sha256 != committed["manifest"]["root_sha256"]):
            raise RuntimeError("G03_FIRST_BOUND_COORDINATOR_OUTCOME_UNPROVEN")
        print("G03_BOUND_NATIVE_COMMIT=" + committed["manifest"]["root_sha256"])
        raise SystemExit(0)
    source, bound = native_bind_original_prepared_fd9(op, raw)
    record = store.read()
    if (source.mode != "list" or source.requested_enabled is not True or
            record["phase"] != "prepared" or record.get("previous") != old_owner or
            (mode == "cold" and ("previous" in record or "previous_manifest" in record)) or
            record["manifest"]["root_sha256"] != bound.root_sha256 or
            record["manifest"]["seal_sha256"] != source.original_seal_sha256 or
            bound.authorization != "NONE" or bound.physical_transition_allowed or
            bound.promotion_allowed):
        raise RuntimeError("bound")
    # First conversion is not a reload/no-op, even if the original saved
    # model is unchanged. The old legacy generation has no structural pin.
    semantic = native_plan_original_prepared_fd9(source)
    if (semantic.decision.kind != "RESTART_REQUIRED" or
            semantic.previous_generation != (None if old_owner is None else old_owner["id"]) or
            semantic.previous_root_sha256 is not None or
            semantic.candidate_root_sha256 != bound.root_sha256 or
            semantic.authorization != "NONE" or
            semantic.physical_transition_allowed or semantic.promotion_allowed or
            semantic.final_original_fd9_reattest_required is not True or
            (mode == "running" and semantic.lifecycle_proposal != "RESTART") or
            (mode == "cold" and (
                semantic.lifecycle_proposal != "START" or
                type(semantic.previous_physical) is not QuiescentPreimage or
                semantic.previous_physical.old_state != "first-install-empty" or
                semantic.previous_physical.previous_generation is not None or
                semantic.previous_physical.previous_release_sha256 is not None or
                semantic.previous_physical.retirement_state != "no-prior-data" or
                semantic.previous_physical.verified_wan_device != "lo0" or
                semantic.previous_physical.kernel_state not in (
                    "native-kernel-absent", "native-managed-kernel-empty") or
                semantic.previous_physical.authorization != "NONE" or
                semantic.previous_physical.physical_transition_allowed or
                semantic.previous_physical.promotion_allowed or
                semantic.previous_physical.original_executor_recheck_required is not True)) or
            (mode == "stopped" and (
                semantic.lifecycle_proposal != "START" or
                type(semantic.previous_physical) is not QuiescentPreimage or
                semantic.previous_physical.old_state != "committed-stopped" or
                semantic.previous_physical.kernel_state not in (
                    "native-kernel-absent", "native-managed-kernel-empty") or
                semantic.previous_physical.retirement_state not in (
                    "original-epoch-ack-retired", "inert-no-producer-data") or
                semantic.previous_physical.authorization != "NONE" or
                semantic.previous_physical.physical_transition_allowed)) or
            store.read() != record):
        raise RuntimeError("semantic")
    try:
        store.advance("activating", detail)
    except SharedOperationError:
        pass
    else:
        raise RuntimeError("activation-fence")
    if store.read() != record:
        raise RuntimeError("journal")
    print("G03_BOUND_NATIVE_PIN=" + bound.root_sha256)
except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
    # Fixed exception type only: native user content is never exposed.
    import re
    reason = str(exc)
    if not re.fullmatch(r"[A-Z0-9_]{1,100}", reason):
        reason = type(exc).__name__.upper()
    print("G03_BOUND_NATIVE_REFUSED_" + reason, file=sys.stderr)
    raise SystemExit(69)
'''
    pinned = call(["/bin/sh", "-c", shell, "g03-bound-native", op,
                   child, "successor" if successor else ("first-commit" if first_commit else (
                       "cold" if cold else ("stopped" if stopped else "running")))],
                  locked=True, timeout=300 if first_commit or successor else 180)
    record = json.loads(WAL.read_bytes())
    root = Path("/var/db/zapret2/shared-work") / op / "manifest.json"
    if successor:
        saved = json.loads(call([PHP, str(script / "shared_apply_config.php"), "saved",
                                 op, "strategies"], locked=True))
        status = subprocess.run([SERVICE, "status"], capture_output=True,
                                text=True, timeout=30)
        saved_list = ET.fromstring(CONFIG.read_bytes()).findtext("./OPNsense/Zapret/hostlist/youtubedomains") or ""
        verify_successor_commit(record, previous, op, pinned, root, original,
                                snapshot(), saved, status, saved_list, expected_list)
        print("G03_S10_SUCCESSOR=PASS_REAL_TWO_BOUND_COMMITS_WITHOUT_RESTART", flush=True)
        return
    if first_commit:
        saved = json.loads(call([PHP, str(script / "shared_apply_config.php"), "saved",
                                 op, "strategies"], locked=True))
        status = subprocess.run([SERVICE, "status"], capture_output=True,
                                text=True, timeout=30)
        verify_first_bound_commit(record, op, pinned, root, original, saved, status)
        print("G03_S10_FIRST_BOUND=PASS_REAL_CONFIG_ENGINE_IPFW_COMMITTED", flush=True)
        return
    need(re.fullmatch(r"G03_BOUND_NATIVE_PIN=[a-f0-9]{64}", pinned) is not None and
         record.get("phase") == "prepared" and record.get("previous") == prior and
         record.get("manifest", {}).get("root_sha256") ==
         hashlib.sha256(root.read_bytes()).hexdigest() ==
         pinned.split("=", 1)[1] and
         snapshot() == original,
         "G03_BOUND_ROOT_PREPARED_OR_PHYSICAL_DRIFT")
    print(("G03_S10_SEMANTIC=PASS_REAL_PRISTINE_FIRST_INSTALL_START_PROPOSAL"
           if cold else
           ("G03_S10_SEMANTIC=PASS_REAL_STOPPED_LEGACY_OWNER_START_PROPOSAL"
            if stopped else
            "G03_S10_SEMANTIC=PASS_REAL_RUNNING_LEGACY_OWNER_RESTART_PROPOSAL")),
          flush=True)
    recovered = call([str(script / "python_runtime.sh"),
                      str(backend / "shared_apply_operation.py"),
                      "recover-prepared", op], locked=True)
    restored = json.loads(WAL.read_bytes())
    need(recovered == "prepared-restored" and
         restored.get("phase") == "restored" and
         restored.get("previous") == prior and
         restored.get("manifest") == record["manifest"] and
         snapshot() == original and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == expected_status and
         (not cold or ("previous" not in restored and "previous_manifest" not in restored)),
         "G03_BOUND_PREPARED_RECOVERY_DRIFT")
    print("G03_S10_BOUND_PREPARED=PASS_REAL_ENGINE_CONFIG_FD9_WAL_ROOT_RECOVERY",
          flush=True)



def pristine_cold_native_main(*, first_commit=False):
    """Disposable first bound commit or existing read-only PREPARED proof."""
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    release = Path("/var/db/zapret2-restyle/runtime.release")
    work = Path("/var/db/zapret2/shared-work")
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_COLD_PREPARED") == "1" and
         os.environ.get("ZAPRET2_G03_PRISTINE_COLD") == "1" and
         (not first_commit or os.environ.get("ZAPRET2_G03_PRISTINE_FIRST_COMMIT") == "1") and
         sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         Path(SERVICE).is_file() and engine.is_file() and
         not engine.is_symlink() and release.is_file() and
         not WAL.exists() and not WAL.is_symlink() and
         not work.is_symlink() and
         (not work.exists() or (work.is_dir() and not any(work.iterdir()))),
         "G03_PRISTINE_COLD_DISPOSABLE_BASELINE_REQUIRED")
    original = snapshot()
    engine_sha = hashlib.sha256(engine.read_bytes()).hexdigest()
    release_bytes = release.read_bytes()
    bound_manifest_main(cold=True, first_commit=first_commit)
    final = json.loads(WAL.read_bytes())
    if first_commit:
        need(final.get("phase") == "committed" and
             "previous" not in final and "previous_manifest" not in final and
             snapshot()[2] == original[2] and
             hashlib.sha256(engine.read_bytes()).hexdigest() == engine_sha and
             release.read_bytes() == release_bytes,
             "G03_PRISTINE_FIRST_COMMIT_OWNER_DRIFT")
        # Same disposable guest and genuine predecessor; no journal reset.
        bound_manifest_main(successor=True)
        need(hashlib.sha256(engine.read_bytes()).hexdigest() == engine_sha and
             release.read_bytes() == release_bytes,
             "G03_BOUND_SUCCESSOR_ENGINE_PROVENANCE_DRIFT")
        return
    need(final.get("phase") == "restored" and "previous" not in final and
         "previous_manifest" not in final and isinstance(final.get("manifest"), dict) and
         snapshot() == original and
         hashlib.sha256(engine.read_bytes()).hexdigest() == engine_sha and
         release.read_bytes() == release_bytes,
         "G03_PRISTINE_COLD_RESTORED_OWNER_DRIFT")
    print("G03_S10_PRISTINE_COLD=PASS_NATIVE_FIRST_INSTALL_START_PROPOSAL_NO_PHYSICAL_ACTION",
          flush=True)


def stopped_native_main():
    """G03 disposable: actual service STOP then repeat ORIGINAL FD9/S08d proof.

    No synthetic state, Config rewrite, kill, orphan deletion, or IPFW bypass.
    It is deliberate only in the discarded guest, never a live auto-detect
    pause. The original STOPPED read-only preimage must qualify completely.
    """
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_COLD_PREPARED") == "1" and
         sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         json.loads(WAL.read_bytes()).get("phase") == "restored" and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 0,
         "G03_STOPPED_DISPOSABLE_RUNNING_BASELINE_REQUIRED")
    stopped = subprocess.run([SERVICE, "stop"], capture_output=True,
                             timeout=120)
    need(stopped.returncode == 0,
         "G03_STOPPED_ORIGINAL_EXPLICIT_STOP_FAILED")
    native_status = subprocess.run([SERVICE, "status"], capture_output=True,
                                   text=True, timeout=30)
    # The actual zapret_service.sh status contract is 0 RUNNING, 1 STOPPED,
    # 2 INCOMPLETE. Do not treat INCOMPLETE as evidence of clean STOP.
    need(native_status.returncode == 1 and
         native_status.stdout.strip() == "zapret is not running" and
         not PIDFILE.exists() and not PIDFILE.is_symlink(),
         "G03_STOPPED_ORIGINAL_EXPLICIT_STOP_NOT_CONFIRMED")
    prior = json.loads(WAL.read_bytes())
    base = snapshot()
    bound_manifest_main(stopped=True)
    final = json.loads(WAL.read_bytes())
    need(final.get("phase") == "restored" and
         final.get("previous") == prior.get("previous") and
         base == snapshot() and
         subprocess.run([SERVICE, "status"], capture_output=True,
                        timeout=30).returncode == 1 and
         not PIDFILE.exists() and not PIDFILE.is_symlink(),
         "G03_STOPPED_ORIGINAL_FD9_PROOF_CHANGED_OWNER")
    print("G03_S10_STOPPED=PASS_NATIVE_OLD_OWNER_START_PROPOSAL_NO_PHYSICAL_ACTION",
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
        elif sys.argv[1:] == ["pristine-cold"]:
            pristine_cold_native_main()
        elif sys.argv[1:] == ["pristine-first-commit"]:
            pristine_cold_native_main(first_commit=True)
        elif sys.argv[1:] == ["stopped"]:
            # Only after the baseline has finished; Stage5 Guest D still
            # requires a genuinely RUNNING predecessor for partial/Config
            # crash tests, and must never execute this destructive scenario.
            stopped_native_main()
        else:
            need(sys.argv[1:] == [], "G03_COLD_UNEXPECTED_ARGUMENTS")
            main()
            bound_manifest_main()
    except (RuntimeError, OSError, ValueError, KeyError,
            subprocess.TimeoutExpired) as exc:
        label = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        prefix = ("G03_COLD_PARTIAL" if sys.argv[1:] == ["partial"] else
                  "G03_COLD_CONFIG" if sys.argv[1:] == ["config-uncertain"] else
                  "G03_PRISTINE_COLD" if sys.argv[1:] in (["pristine-cold"], ["pristine-first-commit"]) else
                  "G03_COLD_STOPPED" if sys.argv[1:] == ["stopped"] else
                  "G03_COLD_PREPARED")
        print(prefix + "=REFUSED:" + label, file=sys.stderr)
        raise SystemExit(1)
