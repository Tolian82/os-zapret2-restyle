#!/usr/bin/env python3
"""TZ6v4 disposable installed OPNsense schema3 canary: real FD9 service lifecycle.

NEVER run on the owner's firewall. This uses the physical official-Mk package
and actual pinned dvtws2, via the ordinary root shared-apply-run envelope and
operator Stop/Start/Restart commands. It does NOT simulate the process or
FD census, invent network discoveries, bypass Config, or write IPFW directly.

The CI-only opt-in is deliberately NOT a production feature. Refuse all other
platforms/contexts. --native-crash proves the original worker dies after a
physically fsynced native-N archive and ordinary Boot replays its immutable
intent. This is not a hardware power cut or positive ISP DPI test.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
CONFIG = Path("/conf/config.xml")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
PID = Path("/var/run/dvtws2.pid")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
PRODUCERS = Path("/var/db/zapret2-auto-detect")
NEEDED_ENV = {
    "GITHUB_ACTIONS": "true",
    "ZAPRET2_NATIVE_BUILD_CI": "1",
    "ZAPRET2_STAGE2_SCHEMA3_DISPOSABLE_NATIVE": "1",
    "ZAPRET2_TZ6V4_SCHEMA3_NATIVE_TRIAL": "1",
}


class Refused(RuntimeError):
    pass


def require(test: bool, error: str) -> None:
    if not test:
        raise Refused(error)


def module(filename: str):
    spec = importlib.util.spec_from_file_location(
        "tz6v4_" + filename.replace(".", "_").replace("-", "_"),
        HERE / filename)
    require(spec is not None and spec.loader is not None, "CANARY_IMPORT_MISSING")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def command(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True,
                          timeout=timeout, check=False)


def envelope(fields: dict, baseline: str) -> str:
    require(isinstance(fields, dict) and isinstance(baseline, str),
            "CANARY_INVALID_NATIVE_REQUEST")
    raw = json.dumps({
        "page": "strategies", "fields": fields,
        "sync": {"telegramips_baseline": baseline},
    }, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    value = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    require(len(value) <= 65536 and re.fullmatch(r"[A-Za-z0-9_-]+", value),
            "CANARY_REQUEST_TOO_LARGE")
    return value


def self_test() -> None:
    encoded = envelope(
        {"general": {"waninterface": "lo0", "enabled": "1"},
         "hostlist": {"mode": "auto"}}, "")
    decoded = json.loads(base64.urlsafe_b64decode(
        encoded + "=" * (-len(encoded) % 4)))
    require(list(decoded) == ["page", "fields", "sync"] and
            decoded["page"] == "strategies" and
            decoded["fields"]["hostlist"]["mode"] == "auto" and
            decoded["sync"] == {"telegramips_baseline": ""},
            "CANARY_ENVELOPE_ROUNDTRIP_INVALID")
    backend = HERE.parent / ("src/opnsense/scripts/OPNsense/Zapret/"
                             "backend/auto_detect_learning_retirement.py")
    require(backend.is_file(), "CANARY_ORIGINAL_BACKEND_SOURCE_MISSING")
    patched = _render_native_fault_overlay(backend.read_bytes(), "a" * 32)
    require(b"ZAPRET2_TZ6V4_INJECT_RETIRE_CRASH" in patched and
            b"os._exit(86)" in patched,
            "CANARY_DISPOSABLE_OVERLAY_PROJECTION_INVALID")
    print("TZ6V4_SCHEMA3_NATIVE_SOURCE=PASS")


def native_root() -> str:
    require(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
            Path("/usr/local/opnsense").is_dir() and
            all(os.environ.get(k) == v for k, v in NEEDED_ENV.items()) and
            os.environ.get("ZAPRET2_STAGE2_REAL_CLEAN_INSTALL") == "1" and
            os.environ.get("ZAPRET2_G04_DISPOSABLE_NATIVE") == "1" and
            os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1",
            "NOT_DISPOSABLE_OPNSENSE_SCHEMA3_NATIVE_TRIAL")
    sha = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None,
            "CANARY_EXACT_SOURCE_SHA_UNAVAILABLE")
    return sha


def check_process(expected_running: bool) -> int | None:
    status = command(str(SERVICE), "status", timeout=60)
    if expected_running:
        require(status.returncode == 0 and "zapret is running" in status.stdout,
                "CANARY_NATIVE_RUNNING_STATUS_REFUSED")
        require(PID.is_file() and not PID.is_symlink() and
                PID.read_text().strip().isdigit(),
                "CANARY_NATIVE_PID_MISSING")
        pid = int(PID.read_text().strip())
        require(pid > 1, "CANARY_PID_INVALID")
    else:
        require(status.returncode == 1 and
                "not running" in status.stdout and not PID.exists(),
                "CANARY_NATIVE_STOPPED_STATUS_REFUSED")
        pid = None
    ps = command("/bin/ps", "-ax", "-o", "pid=", "-o", "command=", timeout=15)
    require(ps.returncode == 0, "CANARY_GLOBAL_PROCESS_CENSUS_FAILED")
    actual = []
    for row in ps.stdout.splitlines():
        fields = row.strip().split(None, 1)
        if (len(fields) == 2 and fields[0].isdigit() and
                (fields[1] == str(ENGINE) or
                 fields[1].startswith(str(ENGINE) + " "))):
            actual.append(int(fields[0]))
    require(actual == ([pid] if expected_running else []),
            "CANARY_REAL_DVTWS2_OWNER_OR_CENSUS_CHANGED")
    return pid


def committed_id() -> str:
    require(JOURNAL.is_file() and not JOURNAL.is_symlink(),
            "CANARY_SHARED_APPLY_JOURNAL_MISSING")
    st = JOURNAL.lstat()
    require(st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o600 and
            st.st_nlink == 1, "CANARY_UNTRUSTED_SHARED_JOURNAL")
    receipt = json.loads(JOURNAL.read_text())
    detail = receipt.get("detail")
    require(receipt.get("phase") == "committed" and
            isinstance(detail, dict) and detail.get("page") == "strategies" and
            isinstance(detail.get("id"), str) and
            re.fullmatch(r"[0-9a-f]{32}", detail["id"]),
            "CANARY_NOT_ORIGINAL_COMMITTED_SHARED_APPLY")
    return detail["id"]


def schema3_receipts(generation: str, pid: int) -> tuple[list[dict], int]:
    path = ACTIVE / "auto-detect-generation.json"
    require(path.is_file() and not path.is_symlink(),
            "CANARY_ACTIVE_NATIVE_SCHEMA3_MAP_MISSING")
    mapping = json.loads(path.read_text())
    learning = [x for x in mapping.get("profiles", [])
                if isinstance(x, dict) and x.get("role") == "learning"]
    require(mapping.get("schema") == 3 and mapping.get("generation") == generation and
            mapping.get("activation_authorized") is True and
            1 <= len(learning) <= 255 and
            all(x.get("auto_inbox") == str(
                PRODUCERS / ("learning-" + generation + "-" +
                             str(x.get("native_number")) + ".txt"))
                for x in learning),
            "CANARY_SCHEMA3_NATIVE_MAP_NOT_LEARNING")
    args = (ACTIVE / "dvtws.args").read_text()
    require(args.count("--hostlist-auto=") == len(learning) and
            "--hostlist-auto-debug=" in args and
            "--hostlist-auto=" in args and
            "--filter-tcp=" in args,
            "CANARY_NATIVE_LAUNCH_ARGV_NOT_MULTI_INBOX")
    receipt_dir = EPOCHS / generation
    pretraffic = json.loads((receipt_dir / "pretraffic.json").read_text())
    epoch = json.loads((receipt_dir / "epoch.json").read_text())
    require(pretraffic.get("schema") == 3 and
            epoch.get("schema") == 3 and epoch.get("owner_pid") == pid and
            epoch.get("generation") == generation and
            len(pretraffic.get("learning", [])) == len(learning) and
            len(pretraffic.get("files", [])) == 2 + len(learning),
            "CANARY_ORIGINAL_FD9_LIVE_SCHEMA3_EPOCH_NOT_SEALED")
    for row in learning:
        n = int(row["native_number"])
        f = PRODUCERS / ("learning-" + generation + "-" + str(n) + ".txt")
        require(f.is_file() and not f.is_symlink() and
                f.stat().st_nlink == 1, "CANARY_PRODUCER_NATIVE_N_MISSING")
    debug = PRODUCERS / "debug.log"
    require(debug.is_file() and debug.stat().st_nlink == 1,
            "CANARY_NATIVE_DEBUG_PRODUCER_MISSING")
    return learning, debug.stat().st_ino


def stopped_receipts(generation: str, learning: list[dict],
                     old_debug_inode: int) -> None:
    folder = EPOCHS / generation / "learning-retirement"
    require(folder.is_dir() and not folder.is_symlink(),
            "CANARY_TERMINAL_ARCHIVE_MISSING")
    intent = json.loads((folder / "intent.json").read_text())
    ready = json.loads((folder / "ready.json").read_text())
    require(intent.get("schema") == 3 and ready.get("schema") == 3 and
            intent.get("generation") == generation and
            ready.get("generation") == generation and
            ready.get("intent_sha256") == hashlib.sha256(
                (folder / "intent.json").read_bytes()).hexdigest(),
            "CANARY_STOPPED_TERMINAL_READY_NOT_ATTESTED")
    for row in learning:
        original = Path(row["auto_inbox"])
        archived = folder / ("old-" + original.name)
        require(not original.exists() and archived.is_file() and
                not archived.is_symlink() and archived.stat().st_nlink == 1,
                "CANARY_TERMINAL_N_INBOX_NOT_RETIRED")
    old_debug = folder / "old-debug.log"
    new_debug = PRODUCERS / "debug.log"
    require(old_debug.is_file() and new_debug.is_file() and
            old_debug.stat().st_ino == old_debug_inode and
            new_debug.stat().st_ino != old_debug_inode and
            new_debug.stat().st_size == 0,
            "CANARY_NATIVE_STOPPED_DEBUG_INODE_NOT_RETIRED")


def stopped_start_projection(generation: str) -> None:
    # The real owner remains terminal on the disposable guest. Exercise the
    # installed projection on a detached copy without inventing a new WAL.
    probe = r'''
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

sys.path.insert(0, sys.argv[1])
from auto_detect_learning_gc import qualified_completed_learning
from auto_detect_origin_map import _learning_start_projection, verify_learning_start_successor
from auto_detect_post_drop import _original_epoch_queue
from shared_apply_operation import SharedApplyOperation
from shared_apply_seal import WORK, create_seal
from voice_ipfw_adapter import require_lifecycle_lock

require_lifecycle_lock()
store = SharedApplyOperation(owner=0)
record = store.read()
detail = record['detail']
if record['phase'] != 'committed' or detail['id'] != sys.argv[2] or record['manifest']['schema'] != 2:
    raise RuntimeError('S11_DETACHED_PROJECTION_WRONG_OWNER')
previous = WORK / detail['id']
candidate = detail['candidate']
queue, receipts = _original_epoch_queue()

def retirement_check(fd):
    return subprocess.run(
        ['/bin/sh', '-c', 'exec 3<&"$1"; shift; exec "$@"', 's11-retirement-fd3', str(fd),
         sys.executable, str(Path(sys.argv[1]) / 'auto_detect_minute.py'),
         '--retired-ready', '--inherited-queue'],
        pass_fds=(9, fd), capture_output=True, timeout=35, check=False)

with tempfile.TemporaryDirectory(prefix='s11-start-projection-') as private:
    work = Path(private) / uuid4().hex
    work.mkdir(mode=0o700)
    with queue.exclusive(existing_only=True):
        ready = retirement_check(queue.locked_fd)
        if ready.returncode != 0 or ready.stdout != b'auto-detect-retire=ready\n':
            raise RuntimeError('S11_ORIGINAL_P2A_BORROW_REFUSED:' + str(ready.returncode))
        separate = os.open(queue.lock, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            refused = retirement_check(separate)
            if refused.returncode != 69 or refused.stdout:
                raise RuntimeError('S11_SEPARATE_P2A_DESCRIPTION_ADMITTED')
        finally:
            os.close(separate)
        qualified_completed_learning(receipts, queue, detail['id'], expected_candidate=candidate)
        # Genuine held P2a does not authorize an unsigned new generation.
        # The original COMMITTED predecessor must remain pristine until an
        # exact linked ACTIVATING WAL exists under the same original FD9.
        from voice_live_inspect import COMMON_ACTIVE
        entries = tuple(sorted(os.listdir(queue.root)))
        refused = subprocess.run(
            ['/bin/sh', '-c', 'exec 3<&"$1"; shift; exec "$@"',
             's11-prepare-fd3', str(queue.locked_fd), sys.executable,
             str(Path(sys.argv[1]) / 'auto_detect_post_drop.py'),
             'capture-learning', str(COMMON_ACTIVE), '--inherited-queue'],
            pass_fds=(9, queue.locked_fd), capture_output=True,
            timeout=35, check=False)
        if (refused.returncode != 69 or refused.stdout or
                tuple(sorted(os.listdir(queue.root))) != entries or
                store.read() != record):
            raise RuntimeError('S11_UNBOUND_PREPARE_MUTATED_RETIRED_OWNER')
        print('S11_NATIVE_CAPTURE_REQUIRES_LINKED_WAL=PASS')
        for name in ('plan.json', 'candidate.xml'):
            shutil.copy2(previous / name, work / name)
        shutil.copytree(previous / 'release', work / 'release')
        for name, content in _learning_start_projection(previous, work.name, candidate).items():
            (work / 'release' / name).write_bytes(content)
        create_seal(work, owner=0)
        verify_learning_start_successor(previous, work, candidate)
        qualified_completed_learning(receipts, queue, detail['id'], expected_candidate=candidate)
        repeated = retirement_check(queue.locked_fd)
        if repeated.returncode != 0 or repeated.stdout != b'auto-detect-retire=ready\n':
            raise RuntimeError('S11_ORIGINAL_P2A_NOT_RETAINED')
        if store.read() != record:
            raise RuntimeError('S11_DETACHED_PROJECTION_CHANGED_OWNER')
print('S11_NATIVE_RETIREMENT_BORROWED_P2A=PASS')
print('S11_NATIVE_DETACHED_START_PROJECTION=PASS')
'''
    result = command("/bin/sh", "-c",
                     'exec 9</var/run/zapret2-lifecycle.lock; /usr/bin/lockf -s -t 0 9 && exec "$@"',
                     "s11-start-projection", str(SERVICE.with_name("python_runtime.sh")),
                     "-c", probe, str(SERVICE.parent / "backend"), generation)
    require(result.returncode == 0 and result.stdout.splitlines() == [
                "S11_NATIVE_CAPTURE_REQUIRES_LINKED_WAL=PASS",
                "S11_NATIVE_RETIREMENT_BORROWED_P2A=PASS",
                "S11_NATIVE_DETACHED_START_PROJECTION=PASS"],
            "S11_NATIVE_START_PROJECTION_REFUSED:rc=" + str(result.returncode) + ":" + result.stderr[-500:])
    print(result.stdout.strip(), flush=True)



def stopped_saved_start_build_admission(generation: str, saved_config: bytes) -> str:
    """Qualified PHP saved-unchanged staging; never advances the original WAL."""
    probe = r'''
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, sys.argv[1])
from shared_apply_operation import SharedApplyOperation, native_bound_saved_start_build_gate
from voice_ipfw_adapter import require_lifecycle_lock

require_lifecycle_lock()
store = SharedApplyOperation(owner=0)
old = store.read()
if old['phase'] != 'committed' or old['detail']['id'] != sys.argv[2]:
    raise RuntimeError('S11_SAVED_BUILD_PREDECESSOR_CHANGED')
reply = subprocess.run(
    ['/usr/local/bin/php', str(Path(sys.argv[1]).parent / 'shared_apply_request.php'),
     'saved-unchanged'], capture_output=True, timeout=35, check=False, pass_fds=(9,))
if reply.returncode or not re.fullmatch(rb'prepared-id=[a-f0-9]{32}\n', reply.stdout):
    raise RuntimeError('S11_SAVED_BUILD_PHP_ORIGINAL_CANDIDATE_REFUSED')
operation = reply.stdout.decode().strip().split('=', 1)[1]
native_bound_saved_start_build_gate(operation)
if store.read() != old:
    raise RuntimeError('S11_SAVED_BUILD_MODIFIED_ORIGINAL_WAL')
print('S11_NATIVE_SAVED_UNCHANGED_BUILD_ADMISSION=PASS')
print('qualified-id=' + operation)
'''
    check = command(
        "/bin/sh", "-c",
        'exec 9</var/run/zapret2-lifecycle.lock; /usr/bin/lockf -s -t 0 9 && exec "$@"',
        "s11-saved-build-admission", str(SERVICE.with_name("python_runtime.sh")),
        "-c", probe, str(SERVICE.parent / "backend"), generation, timeout=120)
    lines = check.stdout.splitlines()
    require(check.returncode == 0 and len(lines) == 2 and
            lines[0] == "S11_NATIVE_SAVED_UNCHANGED_BUILD_ADMISSION=PASS" and
            re.fullmatch(r"qualified-id=[a-f0-9]{32}", lines[1]) and
            CONFIG.read_bytes() == saved_config,
            "S11_NATIVE_SAVED_BUILD_ADMISSION_REFUSED:rc=" +
            str(check.returncode) + ":" + check.stderr[-600:])
    print(lines[0], flush=True)
    return lines[1].split("=", 1)[1]


def owner_service_environment() -> dict[str, str]:
    """Exercise real explicit Auto without a schema3 CI traffic switch.

    The CI host still needs its own guard flags to install and run the
    disposable OPNsense canary. None are passed as schema3 authorization to
    the *ordinary* original FD9 Apply/Start/Stop/Restart subprocesses.
    """
    env = os.environ.copy()
    env.pop("ZAPRET2_TZ6V4_SCHEMA3_NATIVE_TRIAL", None)
    env.pop("ZAPRET2_STAGE2_SCHEMA3_DISPOSABLE_NATIVE", None)
    return env


def service_action(verb: str) -> None:
    require(verb in ("start", "stop", "restart"),
            "CANARY_UNTRUSTED_SERVICE_VERB")
    result = subprocess.run([str(SERVICE), verb], env=owner_service_environment(),
                            capture_output=True, text=True, timeout=180,
                            check=False)
    require(result.returncode == 0,
            "CANARY_" + verb.upper() + "_REFUSED:rc=" +
            str(result.returncode) + ":" +
            (result.stdout + result.stderr)[-420:])



def _install_disposable_retirement_overlay(path: Path, content: bytes,
                                           original: bytes) -> None:
    """Atomic same-directory test-only source replacement on a throwaway VM."""
    require(path.is_file() and not path.is_symlink() and
            path.lstat().st_uid == 0 and path.lstat().st_nlink == 1 and
            path.read_bytes() in (original, content),
            "CANARY_INSTALLED_BACKEND_NOT_EXACT")
    current = path.lstat()
    pending = path.with_name(".tz6v4-retirement-crash-overlay")
    require(not pending.exists() and not pending.is_symlink(),
            "CANARY_DISPOSABLE_OVERLAY_LEFT_BEHIND")
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW, 0o600)
    try:
        os.fchown(fd, current.st_uid, current.st_gid)
        os.fchmod(fd, stat.S_IMODE(current.st_mode))
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(pending, path)
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    require(path.read_bytes() == content,
            "CANARY_DISPOSABLE_BACKEND_OVERLAY_NOT_ATOMIC")


def _render_native_fault_overlay(original: bytes, generation: str) -> bytes:
    """Pure test-fixture projection; no write until disposable root attested."""
    lf = chr(10)
    anchor = lf.join((
        '            _image(archived, receipts, queue, expected=old)',
        '            _drained(archived, old, proof, queue, inspect)',
        '        if name == "debug.log":',
    ))
    injected = lf.join((
        '            if (name == Path(proof.learning[0][2]).name and',
        '                    os.environ.get("ZAPRET2_TZ6V4_INJECT_RETIRE_CRASH")',
        '                    == proof.generation):',
        '                os.write(2, b"TZ6V4_DISPOSABLE_CRASH_AFTER_FIRST_N_ARCHIVE'
        + chr(92) + 'n")',
        '                os._exit(86)',
        '',
    ))
    require(isinstance(original, bytes) and
            re.fullmatch("[a-f0-9]{32}", generation) is not None,
            "CANARY_FAULT_PLAN_UNQUALIFIED")
    code = original.decode("utf-8")
    require(code.count(anchor) == 1 and
            "ZAPRET2_TZ6V4_INJECT_RETIRE_CRASH" not in code and
            "os._exit(86)" not in code,
            "CANARY_NATIVE_SOURCE_INJECTION_POINT_NOT_UNIQUE")
    altered = code.replace(anchor, anchor.replace(
        '        if name == "debug.log":', injected + '        if name == "debug.log":'))
    compile(altered, "<only-disposable-native-fault-injection>", "exec")
    return altered.encode("utf-8")


def _only_disposable_crash_overlay(generation: str):
    """Return (installed_path, original_source) after strictly guarded patch.

    This overlay exists ONLY in the VM, NEVER in the pkg or repository
    backend. Every ordinary engine/service call is made on unmodified
    product source; the deliberately interrupted Stop alone sees the patch.
    """
    native_root()  # refuse Linux/user/appliance misuse before any file edit
    source = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/"
                  "auto_detect_learning_retirement.py")
    repository_source = HERE.parent / (
        "src/opnsense/scripts/OPNsense/Zapret/backend/"
        "auto_detect_learning_retirement.py")
    require(repository_source.is_file() and
            not repository_source.is_symlink() and
            source.is_file() and not source.is_symlink() and
            source.read_bytes() == repository_source.read_bytes(),
            "CANARY_NATIVE_INSTALLED_SOURCE_NOT_SAME_GIT_BLOB")
    original = source.read_bytes()
    require(b"ZAPRET2_TZ6V4_INJECT_RETIRE_CRASH" not in original and
            b"os._exit(86)" not in original,
            "CANARY_FAULT_INJECTION_SHIPPED_IN_USER_PACKAGE")
    overlay = _render_native_fault_overlay(original, generation)
    _install_disposable_retirement_overlay(source, overlay, original)
    return source, original, overlay


def interrupted_original_retirement(generation: str, learning: list[dict],
                                    original_debug_inode: int,
                                    saved_config: bytes, g04_runtime) -> dict:
    """Abruptly terminate ONE root original STOPPED retirement worker.

    Original operator Stop already shuts down dvtws2 and scoped IPFW before
    the controlled worker exit. Confirm real incomplete files, without
    creating/editing an epoch, then use ordinary Boot to recover that exact
    immutable plan under the same FD9 policy and a new running epoch.
    """
    require(len(learning) >= 2, "CANARY_CRASH_REQUIRES_MULTI_N_LEARNING")
    source, original_source, overlay = _only_disposable_crash_overlay(generation)
    try:
        fault_env = dict(os.environ)
        fault_env["ZAPRET2_TZ6V4_INJECT_RETIRE_CRASH"] = generation
        stop = subprocess.run([str(SERVICE), "stop"], env=fault_env,
                              capture_output=True, text=True, timeout=180,
                              check=False)
    finally:
        # Even when Stop fails or the old worker exits abruptly, the parent
        # canary always restores the EXACT original installed source before
        # inspecting/restarting the original FD9 owner.
        _install_disposable_retirement_overlay(source, original_source, overlay)
    require(stop.returncode != 0 and
            "TZ6V4_DISPOSABLE_CRASH_AFTER_FIRST_N_ARCHIVE" in stop.stderr and
            source.read_bytes() == original_source,
            "CANARY_EXPECTED_ORIGINAL_WORKER_EXIT_NOT_OBSERVED:rc=" +
            str(stop.returncode) + ":" + stop.stderr[-300:])

    # A partial Stop may report 'incomplete' rather than 'not running';
    # physical PID census and IPFW determine actual safety at this point.
    process = command("/bin/ps", "-ax", "-o", "pid=", "-o", "command=", timeout=20)
    require(process.returncode == 0 and not PID.exists() and
            not PID.is_symlink() and
            not any(line.strip().split(None, 1)[-1].startswith(str(ENGINE) + " ")
                    for line in process.stdout.splitlines()
                    if line.strip().split(None, 1)[0].isdigit()),
            "CANARY_OLD_DVTWS2_OR_PID_SURVIVED_INTERRUPTED_STOP")
    require(not g04_runtime.owned_rules() and
            CONFIG.read_bytes() == saved_config and
            committed_id() == generation,
            "CANARY_PARTIAL_STOP_CHANGED_IPFW_CONFIG_OR_COMMITTED_OWNER")

    folder = EPOCHS / generation / "learning-retirement"
    intent_path = folder / "intent.json"
    require(intent_path.is_file() and not intent_path.is_symlink() and
            not (folder / "ready.json").exists() and
            not (folder / "ready.json").is_symlink(),
            "CANARY_PARTIAL_STOP_MISSING_INTENT_OR_EARLY_READY")
    intent = json.loads(intent_path.read_bytes())
    sources = intent.get("sources")
    require(intent.get("schema") == 3 and
            intent.get("generation") == generation and
            isinstance(sources, list) and len(sources) == len(learning) + 1 and
            all(isinstance(row, dict) for row in sources),
            "CANARY_INTERRUPTED_SOURCE_PLAN_NOT_ORIGINAL")
    first = sources[0]
    old = PRODUCERS / first["name"]
    archived = folder / ("old-" + first["name"])
    expected = first.get("image")
    require(first["name"] == Path(learning[0]["auto_inbox"]).name and
            not old.exists() and not old.is_symlink() and
            archived.is_file() and not archived.is_symlink() and
            type(expected) is list and len(expected) == 4 and
            [archived.stat().st_dev, archived.stat().st_ino,
             archived.stat().st_size,
             hashlib.sha256(archived.read_bytes()).hexdigest()] == expected,
            "CANARY_FIRST_NATIVE_N_WAS_NOT_SAFELY_FSYNC_ARCHIVED")
    for source in sources[1:]:
        live = PRODUCERS / source["name"]
        require(live.is_file() and not live.is_symlink() and
                not (folder / ("old-" + source["name"])).exists(),
                "CANARY_CRASH_NOT_AT_SINGLE_N_ARCHIVE")
    require((PRODUCERS / "debug.log").stat().st_ino == original_debug_inode,
            "CANARY_DEBUG_INODE_WAS_EARLY_REPLACED")

    # The next process has NO injection variable: ordinary protected
    # Boot first completes the exact old stopped plan, then creates a new
    # generation and one real engine without a second writer or IPFW owner.
    service_action("start")
    boot_pid = check_process(True)
    boot_id = committed_id()
    require(boot_pid is not None and boot_id != generation and
            CONFIG.read_bytes() == saved_config,
            "CANARY_ORIGINAL_BOOT_DID_NOT_RECOVER_OLD_PLAN")
    stopped_receipts(generation, learning, original_debug_inode)
    boot_learning, boot_debug_inode = schema3_receipts(boot_id, boot_pid)
    service_action("stop")
    check_process(False)
    stopped_receipts(boot_id, boot_learning, boot_debug_inode)
    require(not g04_runtime.owned_rules() and
            CONFIG.read_bytes() == saved_config and
            committed_id() == boot_id,
            "CANARY_RECOVERED_NATIVE_FINAL_STOP_NOT_CLEAN")
    return {
        "status": "PASS_TZ6V4_DISPOSABLE_SCHEMA3_INTERRUPTED_STOP_BOOT_RECOVERY",
        "crash_overlay_restored_before_real_boot": True,
        "packaged_backend_contains_no_crash_hook": True,
        "initial_generation": generation,
        "recovered_generation": boot_id,
        "recovered_real_dvtws2_pid": boot_pid,
        "worker_died_without_finally_after_fsync": True,
        "first_old_N_inode_and_immutable_intent_retained": True,
        "boot_finished_same_old_retirement_plan": True,
        "new_epoch_real_engine_after_recovery": True,
        "original_config_and_ipfw_protected": True,
        "physical_power_cut_tested": False,
        "owner_firewall_touched": False,
        "positive_isp_attribution_tested": False,
    }


def execute(*, crash: bool = False, start_preflight: bool = False) -> dict:
    head = native_root()
    g04 = module("stage2-opnsense-g04-native-config.py")
    # The SAME official-Mk physical archive, pkg installation and real
    # upstream v1.0.7 as ordinary G04/G07. No direct Config XML editing.
    g04.verify_native_pkg_and_first_config()
    require(not ENGINE.exists() and not JOURNAL.exists() and
            not PID.exists(), "CANARY_NOT_COLD_INSTALLED_NATIVE")
    # A native plugin .pkg intentionally does NOT bundle upstream dvtws2.
    # Reuse the already-accepted G04 genuine configctl setup/release witness,
    # without invoking its later ordinary GUI Apply or modifying Config.
    config_before_upstream = CONFIG.read_bytes()
    g04_runtime = module("stage2-opnsense-g04-native-runtime.py")
    # Same verified public tag used by the existing protected fixture;
    # actual installed G03 still clones, checks the tag and builds dvtws2.
    cache = module("stage5-native-protected-update.py")
    cache.seed_qualified_stable_tag_for_disposable_guest(
        module("stage2-opnsense-g03-first-install.py"), schema3_canary=True)
    try:
        engine_sha = g04_runtime.setup_upstream()
    except Exception as exc:
        # Never retry, skip or substitute the original G03 install owner.
        # A native setup failure must expose its actual bounded log/state,
        # not a misleading schema3 Apply failure or silent background task.
        g03 = module("stage2-opnsense-g03-first-install.py")
        g03.bounded_disposable_failure_evidence()
        raise Refused(
            "CANARY_ORIGINAL_G03_SETUP_FAILED:" +
            type(exc).__name__ + ":" + str(exc)[:200]) from exc
    require(ENGINE.is_file() and not ENGINE.is_symlink() and
            hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha and
            CONFIG.read_bytes() == config_before_upstream and
            not JOURNAL.exists() and not PID.exists(),
            "CANARY_UPSTREAM_SETUP_CHANGED_ORIGINAL_COLD_OWNER")
    before = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    require(before is not None and
            before.findtext("general/enabled") == "0" and
            (before.findtext("general/waninterface") or "") == "" and
            before.findtext("hostlist/mode") == "list" and
            "<HOSTLIST:youtube>" in (before.findtext("strategy/trafficargs") or ""),
            "CANARY_DEFAULT_LIST_LEARNABLE_PROFILE_MISSING")
    baseline_code = (
        "require_once('script/load_phalcon.php');"
        "$m=new \\OPNsense\\Zapret\\Zapret();"
        "$n=$m->getNodes();"
        "echo json_encode($n['hostlist']['telegramips']??null, JSON_THROW_ON_ERROR);"
    )
    baseline = command("/usr/local/bin/php", "-r", baseline_code, timeout=30)
    require(baseline.returncode == 0, "CANARY_NATIVE_PHP_MODEL_UNREADABLE")
    saved = json.loads(baseline.stdout)
    require(isinstance(saved, str), "CANARY_IPSET_GUI_BASELINE_INVALID")
    request = envelope(
        {"general": {"waninterface": "lo0", "enabled": "1"},
         "hostlist": {"mode": "auto"}}, saved)
    run = subprocess.run(
        [str(SERVICE), "shared-apply-run", "strategies", request],
        env=owner_service_environment(), capture_output=True, text=True,
        timeout=420, check=False)
    if run.returncode != 0 and JOURNAL.is_file() and not JOURNAL.is_symlink():
        try:
            wal = json.loads(JOURNAL.read_bytes()) if JOURNAL.stat().st_size <= 8192 else {}
            phase = wal.get("phase")
        except (OSError, ValueError, AttributeError):
            phase = None
        if phase not in ("prepared", "activating", "activated", "epoch-finalizing", "committed"):
            phase = "unknown"
        print("S11_FIRST_AUTO_WAL=" + phase, flush=True)
    require(run.returncode == 0 and
            re.search(r"(?m)^applied-id=[0-9a-f]{32}$", run.stdout),
            "CANARY_REAL_SHARED_APPLY_REFUSED:rc=" +
            str(run.returncode) + ":" + (run.stdout + run.stderr)[-700:])
    ident = committed_id()
    first_pid = check_process(True)
    require(first_pid is not None, "CANARY_START_PID_MISSING")
    learning, debug_inode = schema3_receipts(ident, first_pid)
    print("S11_NATIVE_FIRST_BOUND_AUTO_NO_REGRESSION=PASS", flush=True)
    saved_root = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    require(saved_root is not None and
            saved_root.findtext("general/enabled") == "1" and
            saved_root.findtext("general/waninterface") == "lo0" and
            saved_root.findtext("hostlist/mode") == "auto",
            "CANARY_SCHEMA3_NATIVE_CONFIG_NOT_COMMITTED")

    if crash:
        result = interrupted_original_retirement(
            ident, learning, debug_inode, CONFIG.read_bytes(), g04_runtime)
        return {"source_sha": head, **result}
    if start_preflight:
        # Exercise operator Start independently of the linked Apply/Boot RED
        # canary. This scope proves the old owner only, not a fresh launch.
        journal_image = JOURNAL.read_bytes()
        config_image = CONFIG.read_bytes()
        installed_args = (ACTIVE / "dvtws.args").read_bytes()
        active_rules = g04_runtime.owned_rules()
        require(json.loads(journal_image).get("manifest", {}).get("schema") == 2,
                "S11_START_PREFLIGHT_BOUND_AUTO_REQUIRED")
        for arguments in ((), ("--force",), ("--configd-receipt",)):
            result = subprocess.run([str(SERVICE), "start", *arguments],
                                    env=owner_service_environment(), capture_output=True,
                                    text=True, timeout=180, check=False)
            expected = ("zapret-api-lifecycle-v1:start:running" if arguments == ("--configd-receipt",)
                        else "native-common-boot=" + ident)
            require(result.returncode == 0 and expected in result.stdout.splitlines(),
                    "S11_RUNNING_START_REFUSED:rc=" + str(result.returncode) + ":" + result.stderr[-400:])
            require(check_process(True) == first_pid and
                    JOURNAL.read_bytes() == journal_image and CONFIG.read_bytes() == config_image and
                    (ACTIVE / "dvtws.args").read_bytes() == installed_args and
                    g04_runtime.owned_rules() == active_rules,
                    "S11_RUNNING_START_CHANGED_OWNER")
        service_action("stop")
        check_process(False)
        stopped_receipts(ident, learning, debug_inode)
        stopped_rules = g04_runtime.owned_rules()
        stopped_journal = JOURNAL.read_bytes()
        stopped_start_projection(ident)
        candidate_id = stopped_saved_start_build_admission(ident, config_image)
        # Real root FD9 shell builder; must produce only a new sealed
        # generation, not a WAL write or a replacement of the old runtime.
        candidate_build = command(str(SERVICE), "shared-apply-prepare", candidate_id, timeout=210)
        # The builder's 0 exit is deliberately NOT a receipt: its
        # 'preflight-rejected=...' reports also exit zero. Require a separate
        # genuine original FD9 witness from the immutable sealed successor.
        sealed = command(
            "/bin/sh", "-c",
            'exec 9</var/run/zapret2-lifecycle.lock; /usr/bin/lockf -s -t 0 9 && exec "$@"',
            "s11-sealed-build-witness", str(SERVICE.with_name("python_runtime.sh")),
            str(SERVICE.parent / "backend/shared_apply_operation.py"),
            "native-gate", "common-bound-saved-start-sealed", candidate_id,
            timeout=90)
        require(candidate_build.returncode == 0 and
                sealed.returncode == 0 and
                sealed.stdout.splitlines() == ["bound-saved-start-sealed=qualified"] and
                JOURNAL.read_bytes() == stopped_journal and
                CONFIG.read_bytes() == config_image and
                not PID.exists(),
                "S11_NATIVE_SAVED_BUILD_NOT_SEALED:build_rc=" +
                str(candidate_build.returncode) + ":sealed_rc=" +
                str(sealed.returncode) + ":" +
                (candidate_build.stdout + candidate_build.stderr + sealed.stderr)[-700:])
        print("S11_NATIVE_SAVED_BUILD_SEALED_SUCCESSOR=PASS", flush=True)
        result = subprocess.run([str(SERVICE), "start"], env=owner_service_environment(),
                                capture_output=True, text=True, timeout=180, check=False)
        require(result.returncode == 69 and not result.stdout.strip() and
                result.stderr.splitlines().count("native-common-boot-guard=sealed-stopped-start") == 1,
                "S11_STOPPED_START_PREIMAGE_REFUSED:rc=" + str(result.returncode) + ":" + result.stderr[-400:])
        check_process(False)
        stopped_receipts(ident, learning, debug_inode)
        require(JOURNAL.read_bytes() == stopped_journal and CONFIG.read_bytes() == config_image and
                (ACTIVE / "dvtws.args").read_bytes() == installed_args and
                g04_runtime.owned_rules() == stopped_rules,
                "S11_STOPPED_START_PREFLIGHT_CHANGED_OWNER")
        # /conf/config.xml is the original native Config, NOT an
        # exclusively private (0600) detached PHP candidate. Check it
        # independently without downgrading its root/inode/write safety.
        config_stat = CONFIG.lstat()
        print("S11_NATIVE_CANONICAL_CONFIG_METADATA=" + json.dumps({
            "file_type": ("regular" if stat.S_ISREG(config_stat.st_mode)
                          else "symlink" if stat.S_ISLNK(config_stat.st_mode)
                          else "other"),
            "uid": config_stat.st_uid,
            "gid": config_stat.st_gid,
            "mode": oct(stat.S_IMODE(config_stat.st_mode)),
            "link_count": config_stat.st_nlink,
        }, sort_keys=True), flush=True)
        def config_identity(info):
            return (info.st_dev, info.st_ino, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns,
                    info.st_mode, info.st_uid, info.st_nlink)
        parent_config = CONFIG.parent.lstat()
        require(stat.S_ISDIR(parent_config.st_mode) and
                not parent_config.st_mode & 0o022 and
                stat.S_ISREG(config_stat.st_mode) and
                config_stat.st_uid == parent_config.st_uid and
                config_stat.st_gid == parent_config.st_gid == 0 and
                config_stat.st_nlink == 1 and
                not config_stat.st_mode & 0o022,
                "S11_NATIVE_CANONICAL_CONFIG_UNTRUSTED")
        config_identity_before = config_identity(config_stat)
        # A PREPARED journal must come from the original single FD9 writer,
        # after the independently attested full sealed projection. Verify
        # the immutable predecessor pin, no process/IPFW change, unchanged
        # saved Config and precise single native WAL record.
        record_result = command(
            "/bin/sh", "-c",
            'exec 9</var/run/zapret2-lifecycle.lock; /usr/bin/lockf -s -t 0 9 && exec "$@"',
            "s11-record-prepared", str(SERVICE.with_name("python_runtime.sh")),
            str(SERVICE.parent / "backend/shared_apply_operation.py"),
            "native-gate", "common-bound-saved-start-record", candidate_id,
            timeout=120)
        prepared = json.loads(JOURNAL.read_bytes())
        old = json.loads(stopped_journal)
        expected_detail = {"id": candidate_id, "page": "strategies",
                           "base": old["detail"]["candidate"],
                           "candidate": old["detail"]["candidate"],
                           "changed_fields": []}
        require(record_result.returncode == 0 and
                record_result.stdout.splitlines() == ["bound-saved-start-record=prepared"] and
                prepared == {"schema": 1, "phase": "prepared", "detail": expected_detail,
                             "previous": old["detail"], "previous_manifest": old["manifest"]} and
                CONFIG.read_bytes() == config_image and
                config_identity(CONFIG.lstat()) == config_identity_before and
                g04_runtime.owned_rules() == stopped_rules and
                (ACTIVE / "dvtws.args").read_bytes() == installed_args and
                not PID.exists(),
                "S11_NATIVE_SAVED_START_PREPARED_WAL_REFUSED:rc=" +
                str(record_result.returncode) + ":" +
                (record_result.stdout + record_result.stderr)[-600:])
        # A duplicate PREPARED attempt cannot manufacture another successor
        # or silently treat this as an authorized physical Start.
        duplicate = command(
            "/bin/sh", "-c",
            'exec 9</var/run/zapret2-lifecycle.lock; /usr/bin/lockf -s -t 0 9 && exec "$@"',
            "s11-duplicate-prepared", str(SERVICE.with_name("python_runtime.sh")),
            str(SERVICE.parent / "backend/shared_apply_operation.py"),
            "native-gate", "common-bound-saved-start-record", candidate_id,
            timeout=30)
        require(duplicate.returncode == 69 and not duplicate.stdout.strip() and
                json.loads(JOURNAL.read_bytes()) == prepared and
                CONFIG.read_bytes() == config_image and
                g04_runtime.owned_rules() == stopped_rules and not PID.exists(),
                "S11_NATIVE_DUPLICATE_PREPARED_ALLOWED")
        print("S11_NATIVE_SAVED_START_ORIGINAL_WAL_PREPARED=PASS", flush=True)
        return {"status": "PASS_S11_START_PREFLIGHT", "source_sha": head,
                "generation": ident, "verified_running_noop": True,
                "verified_stopped_preimage": True, "verified_detached_projection": True,
                "verified_borrowed_retirement_queue": True,
                "verified_original_saved_prepared_wal": True,
                "physical_start_tested": False}

    # A genuine first Auto Apply was not sufficient: reproduce the owner's
    # failing action while a REAL schema3 learner is already RUNNING.
    # The ordinary native FD9 path must accept both unchanged and changed
    # Settings submissions, safely retire the preceding N/debug epoch,
    # retain the saved Config, and start exactly one new real dvtws2.
    initial_generation = ident
    initial_pid = first_pid
    def running_auto_apply(fields: dict, gate: str, old_generation: str,
                           old_pid: int) -> tuple[str, int]:
        submit = envelope(fields, saved)
        attempt = subprocess.run(
            [str(SERVICE), "shared-apply-run", "strategies", submit],
            env=owner_service_environment(), capture_output=True, text=True,
            timeout=420, check=False)
        # Retain the actual public behavior before asserting the historical
        # lifecycle expectation. A new immutable owner may not be bypassed.
        state = json.loads(JOURNAL.read_bytes())
        print("CANARY_RUNNING_AUTO_DISPATCH=" + json.dumps({
            "case": gate, "rc": attempt.returncode,
            "phase": state.get("phase") if state.get("phase") in
                ("committed", "prepared", "activating", "activated", "restored", "requires-review") else "other",
            "bound": "manifest" in state,
            "original_generation": state.get("detail", {}).get("id") == old_generation,
            "applied": bool(re.search(r"(?m)^applied-id=[0-9a-f]{32}$", attempt.stdout)),
            "old_pidfile_present": PID.is_file() and not PID.is_symlink(),
        }, sort_keys=True), flush=True)
        require(attempt.returncode == 0 and
                re.search(r"(?m)^applied-id=[0-9a-f]{32}$", attempt.stdout),
                "CANARY_RUNNING_SCHEMA3_" + gate + "_APPLY_REFUSED:rc=" +
                str(attempt.returncode) + ":" +
                (attempt.stdout + attempt.stderr)[-700:])
        new_generation = committed_id()
        new_pid = check_process(True)
        require(new_pid is not None and
                new_pid != old_pid and new_generation != old_generation,
                "CANARY_RUNNING_SCHEMA3_" + gate + "_OWNER_NOT_REPLACED")
        # The original Stop must durably retire the preceding learning
        # sources before a new generation may own the same native paths.
        old_retired = EPOCHS / old_generation / "learning-retirement"
        require((old_retired / "intent.json").is_file() and
                (old_retired / "ready.json").is_file() and
                not (old_retired / "ready.json").is_symlink(),
                "CANARY_RUNNING_SCHEMA3_" + gate + "_OLD_EPOCH_NOT_TERMINAL")
        return new_generation, new_pid

    # Independent observations on the real newly bound owner. The historical
    # positive test below still has to pass; never label a refusal as success.
    # A refused unchanged request must not prevent measuring a separate
    # actual changed request and a real Stop/Boot in this disposable guest.
    owner_record = JOURNAL.read_bytes()
    config_image = CONFIG.read_bytes()
    active_rules = g04_runtime.owned_rules()
    owner = json.loads(owner_record)
    if owner.get("manifest", {}).get("schema") == 2:
        def attempt_bound(fields, label):
            reply = subprocess.run(
                [str(SERVICE), "shared-apply-run", "strategies", envelope(fields, saved)],
                env=owner_service_environment(), capture_output=True, text=True,
                timeout=420, check=False)
            result = {
                "case": label, "rc": reply.returncode,
                "applied": bool(re.search(r"(?m)^applied-id=[0-9a-f]{32}$", reply.stdout)),
                "journal_unchanged": JOURNAL.read_bytes() == owner_record,
                "config_unchanged": CONFIG.read_bytes() == config_image,
                "ipfw_unchanged": g04_runtime.owned_rules() == active_rules,
                "pid_unchanged": PID.is_file() and not PID.is_symlink() and
                    PID.read_text().strip() == str(first_pid),
            }
            print("CANARY_BOUND_SCOPE=" + json.dumps(result, sort_keys=True), flush=True)
            return result

        unchanged = attempt_bound({"general": {"enabled": "1", "waninterface": "lo0"},
                                   "hostlist": {"mode": "auto"}}, "unchanged")
        if unchanged["rc"] != 0 and all(unchanged[key] for key in (
                "journal_unchanged", "config_unchanged", "ipfw_unchanged", "pid_unchanged")):
            changed = attempt_bound({"general": {"autorestart": "daily"}}, "changed")
            if changed["rc"] != 0 and all(changed[key] for key in (
                    "journal_unchanged", "config_unchanged", "ipfw_unchanged", "pid_unchanged")):
                service_action("stop")
                check_process(False)
                stopped_receipts(ident, learning, debug_inode)
                before_boot = JOURNAL.read_bytes()
                boot = command(str(SERVICE), "start", timeout=420)
                print("CANARY_BOUND_BOOT=" + json.dumps({
                    "rc": boot.returncode,
                    "journal_unchanged": JOURNAL.read_bytes() == before_boot,
                    "config_unchanged": CONFIG.read_bytes() == config_image,
                    "pid_present": PID.is_file() and not PID.is_symlink(),
                    "status_rc": command(str(SERVICE), "status").returncode,
                }, sort_keys=True), flush=True)
                raise Refused("CANARY_BOUND_PUBLIC_APPLY_REFUSED_SEPARATE_BOOT_MEASURED")
            raise Refused("CANARY_BOUND_PUBLIC_UNCHANGED_APPLY_REFUSED")
        if unchanged["rc"] != 0:
            raise Refused("CANARY_BOUND_UNCHANGED_REFUSAL_OWNER_CHANGED")
        # A successful no-op can be recognized only if every original
        # owner/config/IPFW fact stayed the same. The complete new semantics
        # still require independent source/effective evidence before changing
        # the historical expectation of the following acceptance sequence.
        require(all(unchanged[key] for key in (
                "journal_unchanged", "config_unchanged", "ipfw_unchanged", "pid_unchanged")),
                "CANARY_BOUND_PROBE_CHANGED_OWNER")

    # No changes to saved user fields (the original owner's failing case).
    ident, first_pid = running_auto_apply(
        {"general": {"enabled": "1", "waninterface": "lo0"},
         "hostlist": {"mode": "auto"}},
        "UNCHANGED", ident, first_pid)
    learning, debug_inode = schema3_receipts(ident, first_pid)
    require(ET.fromstring(CONFIG.read_bytes()).findtext(
                "./OPNsense/Zapret/hostlist/mode") == "auto",
            "CANARY_RUNNING_SCHEMA3_UNCHANGED_MODE_DRIFT")

    # A valid but harmless persisted preference change exercises the
    # other failed GUI case without changing WAN, profiles or target mode.
    ident, first_pid = running_auto_apply(
        {"general": {"autorestart": "daily"}}, "EDITED", ident, first_pid)
    learning, debug_inode = schema3_receipts(ident, first_pid)
    require(ET.fromstring(CONFIG.read_bytes()).findtext(
                "./OPNsense/Zapret/general/autorestart") == "daily",
            "CANARY_RUNNING_SCHEMA3_EDITED_CONFIG_NOT_SAVED")
    # Return the original user preference before the ordinary lifecycle
    # Stop/Boot/Restart test, and attest the third safe transition.
    ident, first_pid = running_auto_apply(
        {"general": {"autorestart": "off"}}, "RESTORED", ident, first_pid)
    learning, debug_inode = schema3_receipts(ident, first_pid)
    saved_root = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    require(saved_root is not None and
            saved_root.findtext("general/autorestart") == "off" and
            saved_root.findtext("general/waninterface") == "lo0" and
            saved_root.findtext("hostlist/mode") == "auto",
            "CANARY_RUNNING_SCHEMA3_ORIGINAL_MODEL_NOT_RESTORED")

    # Operator-authorized Stop only, no SIGSTOP/SIGCONT, no second daemon.
    service_action("stop")
    check_process(False)
    stopped_receipts(ident, learning, debug_inode)
    require(committed_id() == ident, "CANARY_STOP_CHANGED_FD9_GENERATION")

    # The original Boot code deliberately creates a fresh operation/epoch
    # from the SAME persisted Config after terminal old-generation retirement.
    # Reusing a stopped PID/birth or the first generation ID would be unsafe.
    saved_model = ET.tostring(saved_root, encoding="utf-8")
    service_action("start")
    boot_pid = check_process(True)
    boot_id = committed_id()
    require(boot_pid is not None and boot_pid != first_pid and
            boot_id != ident and
            ET.tostring(ET.fromstring(CONFIG.read_bytes()).find(
                "./OPNsense/Zapret"), encoding="utf-8") == saved_model,
            "CANARY_BOOT_NEW_FD9_OWNER_DID_NOT_PRESERVE_SAVED_CONFIG")
    boot_learning, boot_debug_inode = schema3_receipts(boot_id, boot_pid)
    service_action("restart")
    restart_pid = check_process(True)
    restart_id = committed_id()
    require(restart_pid is not None and restart_pid != boot_pid and
            restart_id not in {ident, boot_id} and
            ET.tostring(ET.fromstring(CONFIG.read_bytes()).find(
                "./OPNsense/Zapret"), encoding="utf-8") == saved_model,
            "CANARY_RESTART_NEW_FD9_OWNER_DID_NOT_PRESERVE_SAVED_CONFIG")
    restart_learning, restart_debug_inode = schema3_receipts(
        restart_id, restart_pid)
    service_action("stop")
    check_process(False)
    stopped_receipts(restart_id, restart_learning, restart_debug_inode)
    require(committed_id() == restart_id,
            "CANARY_FINAL_STOP_LOST_LAST_SAVED_OWNER")
    return {
        "status": "PASS_TZ6V4_DISPOSABLE_REAL_SCHEMA3_APPLY_STOP_BOOT_RESTART",
        "source_sha": head, "initial_generation": ident,
        "boot_generation": boot_id, "restart_generation": restart_id,
        "real_engine_start_pid": first_pid,
        "real_engine_boot_pid": boot_pid,
        "real_engine_restart_pid": restart_pid,
        "native_learning_profiles": len(learning),
        "original_fd9_config_and_p2c_process": True,
        "terminal_n_debug_retirement": True,
        "running_unchanged_apply": True,
        "running_edited_apply": True,
        "running_original_preference_restored": True,
        "pre_existing_generation": initial_generation,
        "pre_existing_pid": initial_pid,
        "new_epoch_on_boot_and_restart": True,
        "one_engine_at_each_active_checkpoint": True,
        "real_isp_positive_attribution_tested": False,
        "powerloss_recovery_tested": False,
        "owner_firewall_touched": False,
    }


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    if sys.argv[1:] not in (["--native"], ["--native-crash"], ["--native-start-preflight"]):
        print("TZ6V4_SCHEMA3_NATIVE=REFUSED_INVALID_COMMAND", file=sys.stderr)
        return 2
    try:
        record = execute(crash=sys.argv[1:] == ["--native-crash"],
                         start_preflight=sys.argv[1:] == ["--native-start-preflight"])
    except (Refused, OSError, ValueError, KeyError, TypeError,
            ET.ParseError, subprocess.TimeoutExpired) as error:
        print("TZ6V4_SCHEMA3_NATIVE=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("TZ6V4_SCHEMA3_NATIVE=" + json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
