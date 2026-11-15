#!/usr/bin/env python3
"""#1052 P2i: P2h ORIGINAL builder preview -> real dvtws2, disposable guest.

This is not installed Apply, a second production engine, or a durable worker.
Only the existing P2e isolated OPNsense VM invokes --native; the old P0
guest/IPFW guard, pinned upstream SHA and loopback flow helper are reused.
"""
from __future__ import annotations

import hashlib
import fcntl
import errno
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
import auto_detect_origin_map as origin
import auto_detect_owner as owner
from auto_detect_post_drop import native_capture_before_launch, _witness_line
from auto_detect_storage import (_prepare, ROOT as PRODUCER, RAW_PATH, DEBUG_PATH)
from auto_detect_queue import DurableInbox
from auto_detect_debug_window import Cursor
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_cursor_chain import CursorChain
from auto_detect_destination_commit import DestinationCommit
from shared_apply_seal import create_seal
import auto_detect_original_v2_prepare as v2_prepare
from auto_detect_fd import FDState, OwnerToken, _owner_snapshot, probe_pending_fd

MARK = "P2I_ORIGINAL_FD9_PREVIEW_NATIVE"
KNOWN = "youtube.com"
UNKNOWN = "unknown.p2i.invalid"
UNKNOWN_AFTER = "rotated.p2i.invalid"
UNKNOWN_MIDCUT = "midcut.p2i.invalid"
UNKNOWN_QUIESCED = "quiesced.p2i.invalid"
UNKNOWN_SECOND = "secondcut.p2i.invalid"
PORT = 6545
DIVERT = 19899
RULES = (19351, 19352)


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


@contextmanager
def _native_test_original_fd9():
    """Same held original kernel FD9 in ONE disposable guest, no service."""
    lock = Path("/var/run/zapret2-lifecycle.lock")
    created = False
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        created = True
    except FileExistsError:
        fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    # Do not allow an open() that reuses vacant FD9 to become its own
    # "previous descriptor": keep an independent fd for proper unlock.
    if fd == 9:
        fd = os.dup(fd)
        os.close(9)
    old_fd = None
    fd9_set = False
    try:
        st = os.fstat(fd)
        named = lock.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
             st.st_nlink == 1 and st.st_mode & 0o022 == 0 and
             (st.st_dev, st.st_ino) == (named.st_dev, named.st_ino),
             "FOREIGN_ORIGINAL_FD9_FILE")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            old_fd = os.dup(9)
        except OSError:
            old_fd = None
        os.dup2(fd, 9, inheritable=True)
        fd9_set = True
        yield
    finally:
        if fd9_set:
            if old_fd is not None:
                os.dup2(old_fd, 9)
            else:
                try:
                    os.close(9)
                except OSError:
                    pass
        if old_fd is not None:
            os.close(old_fd)
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
        if created:
            # The loopback VM is disposed afterwards; preserve foreign
            # existing native lifecycle files and remove only our own.
            lock.unlink()


def load(name: str, file: Path):
    spec = importlib.util.spec_from_file_location(name, file)
    need(spec is not None and spec.loader is not None, "REQUIRED_TEST_MODULE_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def components():
    p0 = load("p2i_reused_p0_guard", HERE / "test-p0-native-auto-observer.py")
    fixture = load("p2i_original_shared_fixture", HERE / "test-p2e-original-shared-build.py")
    return p0, fixture


def _fixture(native_root: Path):
    """Use the original orchestrator, not P0's constructed test profile."""
    _, original = components()
    case = original.OriginalSharedGeneration("runTest")
    case.setUp()
    try:
        case.root.chmod(0o755)
        for lua in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
            real = native_root / "lua" / lua
            need(real.is_file() and not real.is_symlink(), "PINNED_UPSTREAM_LUA_MISSING")
            shutil.copyfile(real, case.static / "lua" / lua)
            (case.static / "lua" / lua).chmod(0o644)
        mapped, args = case.build(
            f"--filter-tcp={PORT}\n--filter-l7=http\n<HOSTLIST:youtube>\n"
            "--payload=http_req\n--lua-desync=multisplit:pos=method+2\n",
            voice_on=False, mode="auto")
        source = case.check_nonactivating(mapped, args)
        need(any(p["status"] == "known-hostlist" and p["hostlist"] == "youtube"
                 for p in source["profiles"]), "ORIGINAL_KNOWN_SOURCE_NOT_ATTESTED")
        original_argv = args.read_bytes()
        (case.work / "plan.json").write_text(json.dumps({
            "page": "strategies",
            "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        digest = "b" * 64  # Synthetic digest, not an OPNsense PHP receipt.
        preview = origin.stage_original_preview(case.work, digest)
        need(origin.verify_original_preview(case.work, digest) == preview,
             "SEALED_PREVIEW_RECONSTRUCTION_MISMATCH")
        need(args.read_bytes() == original_argv and
             not (case.release / owner.MAP_NAME).exists(),
             "INERT_RELEASE_ARGV_OR_OWNER_MAP_CHANGED")
        planned = (case.release / "auto-detect-observer-preview.args").read_bytes()
        expected_sha = preview["final_args_sha256"]
        need(hashlib.sha256(planned).hexdigest() == expected_sha,
             "SEALED_PREVIEW_DIGEST_MISMATCH")
        need(preview["evidence"] == "P2H_ORIGINAL_FD9_SEALED_PREVIEW_NONACTIVATING"
             and preview["activation_authorized"] is False,
             "PREVIEW_IMPROPERLY_AUTHORIZED")
        return case, planned, preview
    except BaseException:
        case.doCleanups()
        raise


def _remap_managed(case, planned: bytes) -> list[str]:
    """Same native validator map as installed engine, never rewrite selectors."""
    reference = str(case.active).rstrip("/") + "/"
    public = case.root / "native-public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    (public / "managed").mkdir(mode=0o755)
    (public / "managed").chmod(0o755)
    allowed = {"--hostlist", "--hostlist-exclude", "--ipset",
               "--ipset-exclude"}
    result = []
    for token in planned.decode("utf-8").split():
        key, equal, value = token.partition("=")
        if equal and value.startswith(reference):
            need(key in allowed, "UNEXPECTED_MAPPED_ENGINE_OPTION")
            rel = Path(value[len(reference):])
            need(len(rel.parts) == 2 and rel.parts[0] == "managed"
                 and re.fullmatch(r"(?:hostlist|ipset)-[a-z0-9-]+\.txt",
                                  rel.parts[1]) is not None,
                 "UNTRUSTED_MANAGED_REFERENCE")
            source = case.release / rel
            need(source.is_file() and not source.is_symlink(),
                 "MISSING_ORIGINAL_MANAGED_SOURCE")
            destination = public / rel
            if not destination.exists():
                shutil.copyfile(source, destination)
                destination.chmod(0o644)
            token = key + "=" + str(destination)
        result.append(token)
    need(result and result[0] == f"--port={DIVERT}" and
         any(t == f"--hostlist-auto={RAW_PATH}" for t in result) and
         any(t == f"--hostlist-auto-debug={DEBUG_PATH}" for t in result),
         "ORIGINAL_OBSERVER_ARGS_NOT_IN_NATIVE_VIEW")
    need(all(not (x.startswith(reference) or "shared-work" in x) for x in result),
         "PRIVATE_FD9_PATH_REACHES_POST_DROP_NATIVE")
    return result


def _native_file_modes(gid: int, *, phase: str) -> None:
    root = PRODUCER.lstat()
    pending = (PRODUCER / "pending").lstat()
    need(stat.S_ISDIR(root.st_mode) and root.st_uid == 0 and
         root.st_gid == gid and stat.S_IMODE(root.st_mode) == 0o710,
         "NATIVE_ROOT_OWNER_OR_MODE_CHANGED")
    need(stat.S_ISDIR(pending.st_mode) and pending.st_uid == 0 and
         pending.st_gid == 0 and stat.S_IMODE(pending.st_mode) == 0o700,
         "NATIVE_PENDING_PRIVATE_MODE_CHANGED")
    observed = set(os.listdir(PRODUCER))
    need(observed in (
         {"pending", "inbox.txt", "debug.log"},
         {"pending", "inbox.txt", "debug.log", "worker.lock"}),
         "UNEXPECTED_NATIVE_PRODUCER_ARTIFACT")
    if "worker.lock" in observed:
        held = (PRODUCER / "worker.lock").lstat()
        need(stat.S_ISREG(held.st_mode) and held.st_uid == 0 and
             held.st_gid == 0 and held.st_nlink == 1 and
             stat.S_IMODE(held.st_mode) == 0o600,
             "NATIVE_ORIGINAL_QUEUE_LOCK_NOT_PROTECTED")
    for file in (RAW_PATH, DEBUG_PATH):
        info = file.lstat()
        actual_mode = stat.S_IMODE(info.st_mode)
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
             actual_mode == 0o660 and info.st_uid == 0 and info.st_gid == gid,
             f"NATIVE_FILE_OWNER_OR_MODE_CHANGED:{phase}:{file.name}:"
             f"mode={actual_mode:04o}:uid={info.st_uid}:gid={info.st_gid}:"
             f"expected_gid={gid}:links={info.st_nlink}")


def _debug_match(content: str, number: int, host: str = UNKNOWN) -> bool:
    return any(f" : profile {number} " in line and
               " : adding to " + str(RAW_PATH) in line and
               host in line for line in content.splitlines())


def _exclusive_native_route(previous: str, current: str, host: str, *,
                            debug_number: int | None = None) -> str:
    """Classify one native append by physical pathname after an inode swap.

    Observational only: a valid previous-inode append is not permission to
    unlink/ACK it, reset debug cursor or schedule a live rollover.
    """
    if debug_number is None:
        old_count = previous.splitlines().count(host)
        new_count = current.splitlines().count(host)
    else:
        def count(text: str) -> int:
            return sum(
                1 for line in text.splitlines()
                if f" : profile {debug_number} " in line
                and " : adding to " + str(RAW_PATH) in line
                and host in line
            )
        old_count, new_count = count(previous), count(current)
    need(old_count + new_count == 1,
         "NATIVE_ROLLOVER_EVENT_MISSING_OR_DUPLICATED")
    return "previous" if old_count == 1 else "current"


def _native_stopped(guard, pid: int) -> bool:
    """Check actual FreeBSD kernel process stop state; never infer via sleep."""
    state = guard.cmd("ps", "-p", str(pid), "-o", "stat=")
    return state.returncode == 0 and state.stdout.strip().startswith("T")


def _scoped_divert_hits(guard, rule: int) -> int:
    """Read the original P0 scoped rule counter; fail without real evidence."""
    result = guard.cmd("/sbin/ipfw", "-a", "list", str(rule))
    match = re.search(rf"(?m)^0*{rule}\s+([0-9]+)\s+", result.stdout)
    need(result.returncode == 0 and match is not None,
         "NATIVE_SCOPED_DIVERT_COUNTER_UNAVAILABLE")
    return int(match.group(1))



def _seed_disposable_original_v2(case, native_args: bytes, preview: dict,
                                 queue: DurableInbox, gid: int):
    """Real P2k8n physical pretraffic seed from an isolated preview fixture.

    A test-only schema-2 projection of original P2h source identities is
    sealed under the same native FD9 and real producer inodes BEFORE launch.
    It is not an installed authorization, live Config/P1 or cron.
    """
    need(preview["activation_authorized"] is False and
         preview["generation"] == case.work.name,
         "NATIVE_V2_PREVIEW_NOT_ISOLATED")
    private = case.root / "native-v2-private"
    private.mkdir(mode=0o700)
    workspace_parent = private / "shared-work"
    workspace_parent.mkdir(mode=0o700)
    workspace = workspace_parent / case.work.name
    workspace.mkdir(mode=0o700)
    release = workspace / "release"
    release.mkdir(mode=0o700)
    shutil.copyfile(case.work / "candidate.xml", workspace / "candidate.xml")
    shutil.copyfile(case.work / "plan.json", workspace / "plan.json")
    (release / "dvtws.args").write_bytes(native_args)
    mapping = {key: value for key, value in preview.items()
               if key not in {"activation_authorized", "evidence"}}
    mapping["evidence"] = "ORIGINAL_SHARED_GENERATOR_CAPTURE"
    mapping["final_args_sha256"] = hashlib.sha256(native_args).hexdigest()
    (release / "auto-detect-generation.json").write_text(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")) + "\n")
    create_seal(workspace, owner=0)
    receipts = EpochReceipts(private / "epochs", owner_uid=0,
                             writer_gid=gid)
    with queue.exclusive():
        receipts.seal_pretraffic(
            queue, workspace=workspace,
            candidate_sha256=mapping["owner_candidate_sha256"])
    return private, receipts

def _native(checkout: Path, *, quiesced_cut: bool = False) -> None:
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
         "FREEBSD_ROOT_ONLY")
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_P2I_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_P4C3_DISPOSABLE_NATIVE") == "1",
         "EXPLICIT_DISPOSABLE_VM_OPT_IN_REQUIRED")
    p0, _ = components()
    guard = p0.guard_module()
    native_root, engine, initial_rules = guard.guest_gate(checkout)
    nobody = pwd.getpwnam("nobody")
    need(nobody.pw_uid > 0 and nobody.pw_gid > 0,
         "UNQUALIFIED_NATIVE_ENGINE_USER")
    need(not PRODUCER.exists() and not PRODUCER.is_symlink(),
         "PRODUCER_ROOT_NOT_CLEAN_DISPOSABLE_VM")

    case = None
    process = None
    installed = []
    started = False
    fd9_context = None
    logfile = None
    observed_native_log = ""
    observed_debug_log = ""
    archived_debug = None
    native_rollover = None
    first_debug_snapshot = ""
    stopped_by_test = False
    native_receipts = None
    native_private = None
    inflight_thread = None
    inflight_reply = {}
    try:
        case, planned, preview = _fixture(native_root)
        _prepare(PRODUCER, uid=0, engine_gid=nobody.pw_gid)
        original_queue = DurableInbox(
            PRODUCER, owner_uid=0, writer_gid=nobody.pw_gid)
        _native_file_modes(nobody.pw_gid, phase="prepared")
        # Original protected inode identities before launching real dvtws2.
        # Reuse the production P2k8h import-only primitive under native VM.
        prelaunch = native_capture_before_launch()
        producer_ids = dict(zip(("inbox.txt", "debug.log"), prelaunch.identities))
        fd9_context = _native_test_original_fd9()
        fd9_context.__enter__()
        bridge = BACKEND / "auto_detect_post_drop.py"
        missing_fd = subprocess.run(
            [sys.executable, str(bridge), "capture"],
            capture_output=True, text=True, timeout=15, check=False)
        need(missing_fd.returncode != 0,
             "UNHELD_NATIVE_FD9_ACCEPTED_PRELAUNCH")
        capture = subprocess.run(
            [sys.executable, str(bridge), "capture"],
            pass_fds=(9,), capture_output=True, text=True,
            timeout=15, check=False)
        need(capture.returncode == 0 and
             capture.stdout.strip() == _witness_line(prelaunch),
             "ORIGINAL_NATIVE_FD9_PRELAUNCH_WITNESS_REJECTED")
        fd9_witness = capture.stdout.strip()
        print(MARK + "_TRUE_FD9_PRELAUNCH=PASS", flush=True)
        print(MARK + "_PREPARED_NATIVE_PRODUCER=PASS", flush=True)
        args = _remap_managed(case, planned)
        # The original FD9/P2a pretraffic seed must be BEFORE even the
        # native dry-run: upstream may chown the existing producer files
        # while probing them, which fails the strict root-owned P2a gate.
        native_args = ("\n".join(args) + "\n").encode("utf-8")
        if not quiesced_cut:
            native_private, native_receipts = _seed_disposable_original_v2(
                case, native_args, preview, original_queue, nobody.pw_gid)
            print(MARK + "_REAL_NATIVE_V2_PRETRAFFIC=sealed_before_engine", flush=True)
        # First check the uninstrumented preview with real native parser.
        dry = subprocess.run([str(engine), *args, "--user=nobody", "--dry-run"],
                             capture_output=True, timeout=15, check=False)
        need(dry.returncode == 0, "NATIVE_ORIGINAL_PREVIEW_DRY_RUN_REJECTED")
        print(MARK + "_DRY_RUN=PASS_NATIVE_PARSER", flush=True)
        need(RAW_PATH.read_bytes() == b"" and DEBUG_PATH.read_bytes() == b"",
             "DRY_RUN_PRODUCED_RAW_OR_DEBUG")
        # Inject ONLY native --debug for flow-selection evidence; it is not a
        # product argv change, and all target/filter/profile flags are intact.
        diagnostic = [args[0], "--debug=1", *args[1:], "--user=nobody"]
        logfile = case.root / "native-preview-engine.log"
        with logfile.open("wb") as output:
            process = subprocess.Popen([str(engine), *diagnostic],
                                       cwd=native_root, stdout=output,
                                       stderr=subprocess.STDOUT)
            time.sleep(0.6)
            need(process.poll() is None, "NATIVE_PREVIEW_ENGINE_DID_NOT_START")
            started = True
            uid = guard.cmd("ps", "-p", str(process.pid), "-o", "uid=")
            need(uid.returncode == 0 and uid.stdout.strip() == str(nobody.pw_uid),
                 "REAL_ENGINE_DID_NOT_DROP_TO_NOBODY")
            birth = guard.cmd("ps", "-p", str(process.pid), "-o", "lstart=")
            need(birth.returncode == 0 and birth.stdout.strip(),
                 "NATIVE_PROCESS_BIRTH_MISSING")
            # The genuine same-held FD9 is inherited by the two short
            # product CLI calls. A corrupt prelaunch witness must be denied
            # before any chown and any loopback IPFW rule.
            incorrect = subprocess.run(
                [sys.executable, str(bridge), "restore",
                 "p2k8i:0:0:1:0:0:1", str(process.pid), str(engine)],
                pass_fds=(9,), capture_output=True, text=True,
                timeout=15, check=False)
            need(incorrect.returncode != 0 and
                 RAW_PATH.stat().st_uid == nobody.pw_uid,
                 "FALSE_FD9_WITNESS_ACCEPTED_OR_REPAIRED")
            result = subprocess.run(
                [sys.executable, str(bridge), "restore",
                 fd9_witness, str(process.pid), str(engine)],
                pass_fds=(9,), capture_output=True, text=True,
                timeout=15, check=False)
            need(result.returncode == 0 and
                 result.stdout.strip() == "original-fd9-postdrop=attested",
                 "TRUE_FD9_POSTDROP_REPAIR_REJECTED")
            print(MARK + "_TRUE_FD9_RESTORED_BEFORE_IPFW=PASS", flush=True)
            _native_file_modes(nobody.pw_gid, phase="before-ipfw")
            print(MARK + "_UPSTREAM_STARTUP_CHOWN=OBSERVED_AND_ROOT_RESTORED_BEFORE_IPFW", flush=True)
            print(MARK + "_REUSABLE_P2K8H_INODE_FD_REPAIR=PASS", flush=True)
            for rule, item in zip(RULES, p0.rules()):
                need(guard.cmd("/sbin/ipfw", "-q", "add",
                               str(rule), *item).returncode == 0,
                     "SCOPED_NATIVE_DIVERT_ADD_REFUSED")
                installed.append(rule)
            delivered = p0.exchange(KNOWN, force_rst=False)
            need(delivered == p0.request(KNOWN),
                 "AUTHORIZED_KNOWN_HTTP_NOT_DELIVERED")
            time.sleep(0.1)
            need(RAW_PATH.read_bytes() == b"",
                 "KNOWN_PROFILE_COVERTLY_ENTERED_OBSERVER")
            before = p0.exchange(UNKNOWN, force_rst=True)
            need(before == p0.request(UNKNOWN), "UNKNOWN_HTTP_CHANGED_BEFORE_APPEND")
            time.sleep(0.7)
            need(RAW_PATH.read_text(encoding="ascii").splitlines() == [UNKNOWN],
                 "REAL_NATIVE_RAW_APPEND_MISSING_OR_DUPLICATED")
            after = p0.exchange(UNKNOWN, force_rst=False)
            need(after == p0.request(UNKNOWN), "UNKNOWN_HTTP_CHANGED_AFTER_APPEND")
            need(RAW_PATH.read_text(encoding="ascii").splitlines() == [UNKNOWN],
                 "NATIVE_RAW_APPEND_DUPLICATED_AFTER_INCLUDED")
            current = guard.cmd("ps", "-p", str(process.pid), "-o", "lstart=")
            need(process.poll() is None and current.returncode == 0 and
                 birth.stdout == current.stdout, "NATIVE_PROCESS_IDENTITY_CHANGED")
            for rule in RULES:
                count = guard.cmd("/sbin/ipfw", "-a", "list", str(rule))
                need(count.returncode == 0 and
                     re.search(rf"(?m)^0*{rule}\s+[1-9]\d*\s+", count.stdout),
                     "LOOPBACK_DIVERT_RULE_NOT_EXERCISED")
            _native_file_modes(nobody.pw_gid, phase="after-native-append")
            need(all((file.stat().st_dev, file.stat().st_ino,
                      file.stat().st_nlink) == producer_ids[file.name]
                     for file in (RAW_PATH, DEBUG_PATH)),
                 "INODE_REPLACED_DURING_NATIVE_APPEND")

            # P2k8q3c1: disposable evidence for actual upstream reopen
            # behavior, not an enabled product debug/raw rollover. The
            # original P2a rotation happens under its ONE real worker.lock.
            # Keep the old raw hardlink; never ACK in this experiment.
            old_raw_identity = (RAW_PATH.stat().st_dev, RAW_PATH.stat().st_ino)
            actual_owner = OwnerToken(
                process.pid, birth.stdout.strip(), str(engine))
            native_proof = owner.GenerationProof(
                actual_owner, case.work.name, case.work.name,
                hashlib.sha256(native_args).hexdigest(),
                str(RAW_PATH), str(DEBUG_PATH),
                preview["observer_native_number"],
                tuple((row["native_number"], row["status"], row["hostlist"])
                      for row in preview["profiles"]))

            def attest_native():
                return native_proof if (
                    process.poll() is None and
                    not _native_stopped(guard, process.pid) and
                    _owner_snapshot(actual_owner, subprocess.run)) else None

            if not quiesced_cut:
                need(native_receipts is not None and
                     attest_native() == native_proof,
                     "REAL_NATIVE_V2_EPOCH_OWNER_NOT_ATTESTED")
                with original_queue.exclusive():
                    native_receipts.finish_running(
                        native_proof, original_queue, attest=attest_native)
                print(MARK + "_REAL_NATIVE_V2_POSTLAUNCH="
                      "same_initial_inodes_and_real_owner", flush=True)
            if quiesced_cut:
                # Only a disposable original PID can be stopped. Recheck
                # engine birth and dropped credentials immediately first.
                need(process.poll() is None and
                     guard.cmd("ps", "-p", str(process.pid), "-o",
                               "lstart=").stdout == birth.stdout and
                     guard.cmd("ps", "-p", str(process.pid), "-o",
                               "uid=").stdout.strip() == str(nobody.pw_uid),
                     "NATIVE_QUIESCENCE_OWNER_CHANGED_BEFORE_STOP")
                process.send_signal(signal.SIGSTOP)
                stopped_by_test = True
                for _ in range(60):
                    if _native_stopped(guard, process.pid):
                        break
                    time.sleep(0.05)
                need(_native_stopped(guard, process.pid) and
                     process.poll() is None,
                     "NATIVE_QUIESCENCE_SIGSTOP_NOT_KERNEL_CONFIRMED")

                # _57 sent NO packets while dvtws2 was STOPPED. Qualify
                # the missing traffic-continuity property using the SAME
                # original P0 loopback and scoped IPFW divert rule.
                # Known HOSTLIST must stay out of native auto hostlist.
                prior_hits = _scoped_divert_hits(guard, RULES[0])
                attempted = threading.Event()
                completed = threading.Event()

                def inflight_known() -> None:
                    attempted.set()
                    try:
                        inflight_reply["payload"] = p0.exchange(
                            KNOWN, force_rst=False)
                    except Exception as exc:
                        inflight_reply["error"] = type(exc).__name__ + ":" + str(exc)
                    finally:
                        completed.set()

                inflight_thread = threading.Thread(
                    target=inflight_known, name="disposable-p2i-stopped-divert",
                    daemon=True)
                inflight_thread.start()
                need(attempted.wait(timeout=2),
                     "NATIVE_STOPPED_DIVERT_REQUEST_NOT_STARTED")
                counted = False
                for _ in range(50):
                    if _scoped_divert_hits(guard, RULES[0]) > prior_hits:
                        counted = True
                        break
                    if completed.is_set():
                        break
                    time.sleep(0.04)
                need(counted,
                     "NATIVE_STOPPED_DIVERT_PACKET_NOT_COUNTED")
                need(_native_stopped(guard, process.pid) and
                     not completed.is_set(),
                     "NATIVE_STOPPED_DIVERT_NOT_STALLED")
                print(MARK + "_REAL_NATIVE_STOPPED_DIVERT="
                      "ipfw_packet_counted_request_stalled", flush=True)
            with original_queue.exclusive():
                previous_raw = original_queue.rotate(generation=case.work.name)
                need(previous_raw is not None and
                     previous_raw.read_text(encoding="ascii").splitlines() == [UNKNOWN] and
                     (previous_raw.stat().st_dev, previous_raw.stat().st_ino) ==
                     old_raw_identity and previous_raw.stat().st_nlink == 1 and
                     (RAW_PATH.stat().st_dev, RAW_PATH.stat().st_ino) !=
                     old_raw_identity and RAW_PATH.read_bytes() == b"",
                     "ORIGINAL_P2A_NATIVE_ROTATION_CHANGED_OR_LOST_FIRST_EVENT")
            print(MARK + "_REAL_ORIGINAL_P2A_RAW_ROTATE=PASS", flush=True)

            if not quiesced_cut:
                # P2k8q3e2: exact real-IPFW known traffic MUST complete in
                # the gap between two independent inode cuts, with the
                # original dvtws2 PID still running. A matching counter alone
                # is NOT sufficient (the _58 stopped test proved that).
                need(not _native_stopped(guard, process.pid),
                     "NATIVE_RUNNING_COHORT_ENGINE_STOPPED_BEFORE_GAP")
                gap_hits = _scoped_divert_hits(guard, RULES[0])
                known_gap = p0.exchange(KNOWN, force_rst=False)
                need(known_gap == p0.request(KNOWN) and
                     _scoped_divert_hits(guard, RULES[0]) > gap_hits and
                     not _native_stopped(guard, process.pid) and
                     previous_raw.read_text(encoding="ascii").splitlines() == [UNKNOWN] and
                     RAW_PATH.read_bytes() == b"",
                     "NATIVE_RUNNING_GAP_KNOWN_HTTP_NOT_DELIVERED_OR_MISATTRIBUTED")
                # P2k8q3c2: a real HTTP/RST event strictly BETWEEN the two
                # physical name replacements. The original raw has been cut,
                # but the original debug name is still current. The producer
                # is NOT synchronized by P2a's root-only queue flock.
                gap_observed = p0.exchange(UNKNOWN_MIDCUT, force_rst=True)
                need(gap_observed == p0.request(UNKNOWN_MIDCUT),
                     "MIDCUT_NATIVE_HTTP_NOT_DELIVERED")
                time.sleep(0.7)
                mid_old_raw = previous_raw.read_text(encoding="ascii")
                mid_new_raw = RAW_PATH.read_text(encoding="ascii")
                mid_old_debug = DEBUG_PATH.read_text(errors="replace")
                observer_num = preview["observer_native_number"]
                mid_raw_route = _exclusive_native_route(
                    mid_old_raw, mid_new_raw, UNKNOWN_MIDCUT)
                need(_debug_match(mid_old_debug, observer_num, UNKNOWN_MIDCUT),
                     "MIDCUT_NATIVE_DEBUG_EVENT_MISSING_ON_ORIGINAL_PATH")
                need(mid_old_raw.splitlines() == [UNKNOWN] and
                     mid_new_raw.splitlines() == [UNKNOWN_MIDCUT],
                     "MIDCUT_ORIGINAL_RAW_SEGMENT_LINEAGE_CHANGED")
                need(process.poll() is None and
                     guard.cmd("ps", "-p", str(process.pid),
                               "-o", "lstart=").stdout == birth.stdout,
                     "MIDCUT_ORIGINAL_NATIVE_PID_CHANGED")
                print(MARK + "_REAL_NATIVE_MIDCUT_ROUTE="
                      + "raw:" + mid_raw_route + ",debug:previous",
                      flush=True)

            # P2k8q3f1: exercise the ACTUAL source P2a original highwater
            # cut, not a second guest-only rename implementation. Only the
            # TEST lowers the 2 MiB trigger to zero. The native P2b
            # all-process inspector and genuine running PID/birth are used,
            # while the nonactivating preview's synthetic generation
            # cannot authorize installed production observation.
            archived_debug = PRODUCER / v2_prepare.DEBUG_OLD
            fresh_debug = PRODUCER / v2_prepare.DEBUG_NEXT
            need(not archived_debug.exists() and not archived_debug.is_symlink() and
                 not fresh_debug.exists() and not fresh_debug.is_symlink(),
                 "FOREIGN_DISPOSABLE_DEBUG_ARCHIVE")
            old_debug_identity = (DEBUG_PATH.stat().st_dev, DEBUG_PATH.stat().st_ino)
            native_cursor = Cursor(
                native_proof.generation, *old_debug_identity, 0,
                hashlib.sha256(b"").hexdigest())
            cut_epoch = (native_receipts if not quiesced_cut else EpochReceipts(
                case.root / "debug-cut-epoch-fixture",
                owner_uid=0, writer_gid=nobody.pw_gid))
            with original_queue.exclusive():
                with patch.object(v2_prepare, "DEBUG_HIGH_WATERMARK", 0):
                    need(v2_prepare._debug_cut_once(
                        original_queue, cut_epoch, native_proof,
                        native_cursor, False,
                        attest_native if not quiesced_cut else lambda: native_proof,
                        probe_pending_fd), "REAL_ORIGINAL_DEBUG_CUT_NOT_EXECUTED")
            need((archived_debug.stat().st_dev, archived_debug.stat().st_ino) ==
                 old_debug_identity and archived_debug.stat().st_nlink == 1 and
                 (DEBUG_PATH.stat().st_dev, DEBUG_PATH.stat().st_ino) !=
                 old_debug_identity and DEBUG_PATH.stat().st_nlink == 1 and
                 DEBUG_PATH.stat().st_size == 0 and
                 not fresh_debug.exists(),
                 "PRODUCT_P2A_NONBLOCKING_DEBUG_CUT_UNQUALIFIED")
            print(MARK + "_REAL_NATIVE_ATOMIC_DEBUG_CUT="
                  "original_p2a_highwater_old_retained_new_path_always_present",
                  flush=True)
            if not quiesced_cut:
                # P2 known HOSTLIST can still traverse actual scoped IPFW
                # immediately after BOTH cuts, with the same running engine.
                post_hits = _scoped_divert_hits(guard, RULES[0])
                known_post = p0.exchange(KNOWN, force_rst=False)
                need(known_post == p0.request(KNOWN) and
                     _scoped_divert_hits(guard, RULES[0]) > post_hits and
                     process.poll() is None and
                     guard.cmd("ps", "-p", str(process.pid),
                               "-o", "lstart=").stdout == birth.stdout and
                     not _native_stopped(guard, process.pid),
                     "NATIVE_RUNNING_POST_CUT_KNOWN_HTTP_NOT_DELIVERED")
                need(previous_raw.read_text(encoding="ascii").splitlines() == [UNKNOWN] and
                     RAW_PATH.read_text(encoding="ascii").splitlines() == [UNKNOWN_MIDCUT],
                     "KNOWN_HTTP_COVERTLY_ADDED_DURING_DEBUG_COHORT_CUT")
                print(MARK + "_REAL_NATIVE_RUNNING_DIVERT_CONTINUITY="
                      "known_http_delivered_before_and_after_debug_cut_no_stop",
                      flush=True)

            if quiesced_cut:
                # Validate the process is STILL STOPPED after BOTH cuts,
                # with first-event raw/debug preserved on previous inodes
                # and both freshly replaced live paths empty. There is
                # one bounded known request is outstanding in IPFW until CONT.
                need(_native_stopped(guard, process.pid) and
                     process.poll() is None and
                     guard.cmd("ps", "-p", str(process.pid), "-o",
                               "lstart=").stdout == birth.stdout,
                     "NATIVE_QUIESCENCE_OWNER_RESUMED_BEFORE_BOTH_CUTS")
                need(previous_raw.read_text(encoding="ascii").splitlines() ==
                     [UNKNOWN] and
                     _debug_match(archived_debug.read_text(errors="replace"),
                                  preview["observer_native_number"], UNKNOWN) and
                     RAW_PATH.read_bytes() == b"" and DEBUG_PATH.read_bytes() == b"",
                     "NATIVE_QUIESCENCE_CUT_FILES_CHANGED_WHILE_STOPPED")
                process.send_signal(signal.SIGCONT)
                for _ in range(60):
                    if not _native_stopped(guard, process.pid):
                        break
                    time.sleep(0.05)
                need(process.poll() is None and
                     not _native_stopped(guard, process.pid) and
                     guard.cmd("ps", "-p", str(process.pid), "-o",
                               "lstart=").stdout == birth.stdout,
                     "NATIVE_QUIESCENCE_ORIGINAL_PID_NOT_RESUMED")
                stopped_by_test = False
                # The request entered IPFW BEFORE the first raw cut and
                # could not finish while the same native PID was STOPPED.
                # It must now be delivered after SIGCONT without creating
                # any native auto positive for the known HOSTLIST.
                need(inflight_thread is not None,
                     "NATIVE_STOPPED_DIVERT_THREAD_MISSING")
                inflight_thread.join(timeout=7)
                need(not inflight_thread.is_alive() and
                     inflight_reply.get("payload") == p0.request(KNOWN),
                     "NATIVE_STOPPED_DIVERT_NOT_DELIVERED_AFTER_RESUME:"
                     + str(inflight_reply.get("error", "missing_payload")))
                need(previous_raw.read_text(encoding="ascii").splitlines() ==
                     [UNKNOWN] and RAW_PATH.read_bytes() == b"" and
                     not _debug_match(
                         archived_debug.read_text(errors="replace"),
                         preview["observer_native_number"], KNOWN) and
                     not _debug_match(
                         DEBUG_PATH.read_text(errors="replace"),
                         preview["observer_native_number"], KNOWN),
                     "NATIVE_STOPPED_DIVERT_KNOWN_ENTERED_AUTO_OBSERVER")
                print(MARK + "_REAL_NATIVE_STOPPED_DIVERT_RECOVERY="
                      "known_first_match_delivered_after_sigcont", flush=True)
                print(MARK + "_REAL_NATIVE_QUIESCED_CUT="
                      "same_pid_stopped_for_raw_and_debug_then_resumed",
                      flush=True)

            # One SECOND unknown hostname cannot inherit native inclusion
            # of the first. Real traffic proves where the same running
            # native PID actually appends after both physical swaps.
            after_host = UNKNOWN_QUIESCED if quiesced_cut else UNKNOWN_AFTER
            observed = p0.exchange(after_host, force_rst=True)
            need(observed == p0.request(after_host),
                 "SECOND_NATIVE_UNKNOWN_HTTP_CHANGED")
            time.sleep(0.8)
            first_raw = previous_raw.read_text(encoding="ascii")
            second_raw = RAW_PATH.read_text(encoding="ascii")
            first_debug = archived_debug.read_text(errors="replace")
            second_debug = DEBUG_PATH.read_text(errors="replace")
            number = preview["observer_native_number"]
            need(_debug_match(first_debug, number, UNKNOWN),
                 "FIRST_NATIVE_DEBUG_LOST_DURING_DISPOSABLE_ROTATION")
            if quiesced_cut:
                # Require first raw and debug to be preserved ONLY on old
                # inodes, while post-CONT host is absent from both old ones.
                need(first_raw.splitlines() == [UNKNOWN] and
                     not _debug_match(first_debug, number, after_host),
                     "NATIVE_QUIESCENCE_OLD_INODE_WRITTEN_AFTER_RESUME")
            else:
                # Retain actual _55 midcut native negative-control forever.
                need(_exclusive_native_route(
                     first_raw, second_raw, UNKNOWN_MIDCUT) == mid_raw_route and
                     _exclusive_native_route(
                         first_debug, second_debug, UNKNOWN_MIDCUT,
                         debug_number=number) == "previous",
                     "MIDCUT_RAW_DEBUG_PREVIOUS_CURRENT_COHORT_CHANGED")
            raw_route = _exclusive_native_route(
                first_raw, second_raw, after_host)
            debug_route = _exclusive_native_route(
                first_debug, second_debug, after_host, debug_number=number)
            if quiesced_cut:
                need(raw_route == "current" and debug_route == "current",
                     "NATIVE_QUIESCED_RESUME_NOT_A_NEW_INODE_PAIR")
            need(process.poll() is None and
                 guard.cmd("ps", "-p", str(process.pid),
                           "-o", "lstart=").stdout == birth.stdout,
                 "ORIGINAL_NATIVE_PID_CHANGED_DURING_ROLLOVER_WITNESS")
            original_owner = OwnerToken(
                process.pid, birth.stdout.strip(), str(engine))
            old_pending_stat = previous_raw.stat()
            # This is the actual all-PID P2b snapshot, never an ACK permit.
            fd_state = probe_pending_fd(
                previous_raw, old_pending_stat.st_dev,
                old_pending_stat.st_ino, owner=original_owner,
                writer_gid=nobody.pw_gid)
            # Independent OLD debug inode must remain physically addressable;
            # all-PID fstat is diagnostic, never guessed permission to ACK.
            old_debug_stat = archived_debug.stat()
            old_debug_fd = probe_pending_fd(
                archived_debug, old_debug_stat.st_dev, old_debug_stat.st_ino,
                owner=original_owner, writer_gid=nobody.pw_gid)
            native_rollover = (raw_route, debug_route, fd_state.value,
                               old_debug_fd.value)
            print(MARK + "_REAL_NATIVE_OLD_DEBUG_FD=" + old_debug_fd.value,
                  flush=True)
            if quiesced_cut:
                print(MARK + "_REAL_NATIVE_QUIESCED_POST_RESUME_ROUTE="
                      + "raw:" + raw_route + ",debug:" + debug_route
                      + ",old_inode_fd:" + fd_state.value, flush=True)
            else:
                print(MARK + "_REAL_NATIVE_POST_ROTATION_ROUTE="
                      + "raw:" + raw_route + ",debug:" + debug_route
                      + ",old_inode_fd:" + fd_state.value, flush=True)

            if not quiesced_cut:
                # P2k8q3f2b: actual real HTTP raw plus original P2k8n
                # checkpoint/ACK under the SINGLE native P2a queue.
                need(native_receipts is not None and native_private is not None,
                     "NATIVE_V2_PRETRAFFIC_EPOCH_MISSING")
                chain = CursorChain(native_receipts, original_queue)
                listdir = native_private / "lists"
                listdir.mkdir(mode=0o700)
                final = listdir / "auto-domains.txt"
                final.write_text("!manual.invalid\n")
                final.chmod(0o600)
                writer = DestinationCommit(
                    native_receipts, original_queue,
                    {"auto": final}, listdir / ".writer.lock")

                def commit_real_raw(pending, hosts):
                    need(pending is not None and pending.is_file(),
                         "NATIVE_V2_RAW_PENDING_MISSING")
                    receipt = chain.commit(
                        native_proof, pending,
                        {"auto": {"add": list(hosts), "remove": []}},
                        writer, attest=attest_native, inspect=probe_pending_fd)
                    need(chain.acknowledge(
                        native_proof, pending, receipt, writer,
                        attest=attest_native, inspect=probe_pending_fd),
                        "NATIVE_V2_RAW_ACK_NOT_DURABLE")
                    need(not pending.exists(), "NATIVE_V2_ACK_DID_NOT_RELEASE_PENDING")

                with original_queue.exclusive():
                    first_slot = chain.prepare(
                        native_proof, previous_raw, attest=attest_native,
                        inspect=probe_pending_fd)
                    need(first_slot.is_dir() and
                         chain.tip(native_proof).open_intent["evidence"] == "raw-first",
                         "NATIVE_V2_FIRST_RAW_FIRST_NOT_PREPARED")
                    commit_real_raw(previous_raw, (UNKNOWN,))
                    newer = v2_prepare.prepare_original_v2_locked(
                        original_queue, native_receipts, attest=attest_native,
                        inspect=probe_pending_fd, inspect_debug=probe_pending_fd)
                    need(newer is not None and
                         newer.read_text(encoding="ascii").splitlines() ==
                         [UNKNOWN_MIDCUT, UNKNOWN_AFTER],
                         "NATIVE_V2_SECOND_PHYSICAL_RAW_SEGMENT_LOST")
                    commit_real_raw(newer, (UNKNOWN_MIDCUT, UNKNOWN_AFTER))
                    tip = chain.tip(native_proof)
                    need(tip.raw_first and tip.open_folder is None and
                         tip.next_sequence == 2 and
                         (tip.cursor.device, tip.cursor.inode) ==
                         old_debug_identity and
                         not original_queue.segments() and
                         RAW_PATH.read_bytes() == b"",
                         "NATIVE_V2_DOUBLE_ACK_NOT_QUALIFIED")
                need(set(final.read_text(encoding="ascii").splitlines()) ==
                     {"!manual.invalid", UNKNOWN, UNKNOWN_MIDCUT, UNKNOWN_AFTER},
                     "NATIVE_V2_REAL_DISCOVERIES_NOT_ONCE_IN_FINAL")
                print(MARK + "_REAL_NATIVE_V2_CONFIG_CHECKPOINT_ACK="
                      "two_original_raw_segments_committed_once", flush=True)

                # A real historical reader FD (not just a mocked state) must
                # be seen BUSY by the unchanged all-process FreeBSD P2b gate.
                first_archived = archived_debug.lstat()
                first_debug_snapshot = archived_debug.read_text(errors="replace")
                need(_debug_match(first_debug_snapshot,
                                  preview["observer_native_number"], UNKNOWN) and
                     _debug_match(first_debug_snapshot,
                                  preview["observer_native_number"], UNKNOWN_MIDCUT),
                     "NATIVE_V2_FIRST_ARCHIVE_EVENT_NOT_VERIFIED_BEFORE_ACK_RETIRE")
                old_fd = os.open(archived_debug, os.O_RDONLY | os.O_NOFOLLOW)
                try:
                    need(probe_pending_fd(
                        archived_debug, first_archived.st_dev,
                        first_archived.st_ino, owner=actual_owner,
                        writer_gid=nobody.pw_gid) is FDState.BUSY,
                        "NATIVE_V2_ALL_PID_HISTORICAL_FD_BUSY_NOT_OBSERVED")
                    with original_queue.exclusive():
                        with patch.object(v2_prepare, "DEBUG_HIGH_WATERMARK", 0):
                            try:
                                v2_prepare._debug_cut_once(
                                    original_queue, native_receipts, native_proof,
                                    tip.cursor, tip.raw_first, attest_native,
                                    probe_pending_fd, retirement_tip=tip)
                            except v2_prepare.OriginalV2PrepareRefused as exc:
                                need(str(exc) == "retained_debug_writer_fd_not_drained",
                                     "NATIVE_V2_WRONG_BUSY_ARCHIVE_REFUSAL")
                            else:
                                raise RuntimeError("NATIVE_V2_BUSY_ARCHIVE_WAS_RETIRED")
                    need(archived_debug.stat().st_ino == first_archived.st_ino,
                         "NATIVE_V2_BUSY_ARCHIVE_WAS_REMOVED")
                finally:
                    os.close(old_fd)
                need(probe_pending_fd(
                    archived_debug, first_archived.st_dev, first_archived.st_ino,
                    owner=actual_owner, writer_gid=nobody.pw_gid) is FDState.DRAINED,
                    "NATIVE_V2_OLD_ARCHIVE_FD_NOT_DRAINED")
                print(MARK + "_REAL_NATIVE_V2_HISTORICAL_FD="
                      "busy_refused_then_all_pid_drained", flush=True)

                # Deliberately fault the real original fsync AFTER proven
                # alias unlink. A physical full disk/power loss remains open.
                before_second_inode = DEBUG_PATH.stat().st_ino
                sync_native = v2_prepare._sync_directory
                fault_seen = [False]
                def inject_post_retire_enospc(path):
                    if not archived_debug.exists() and not fault_seen[0]:
                        fault_seen[0] = True
                        raise OSError(errno.ENOSPC, "disposable-native-post-unlink")
                    return sync_native(path)
                with original_queue.exclusive():
                    with patch.object(v2_prepare, "DEBUG_HIGH_WATERMARK", 0):
                        with patch.object(v2_prepare, "_sync_directory",
                                          side_effect=inject_post_retire_enospc):
                            try:
                                v2_prepare._debug_cut_once(
                                    original_queue, native_receipts, native_proof,
                                    tip.cursor, tip.raw_first, attest_native,
                                    probe_pending_fd, retirement_tip=tip)
                            except OSError as exc:
                                need(exc.errno == errno.ENOSPC and fault_seen[0],
                                     "NATIVE_V2_INJECTED_ENOSPC_NOT_PROPAGATED")
                            else:
                                raise RuntimeError("NATIVE_V2_INJECTED_ENOSPC_IGNORED")
                need(not archived_debug.exists() and
                     DEBUG_PATH.stat().st_ino == before_second_inode and
                     RAW_PATH.read_bytes() == b"",
                     "NATIVE_V2_ENOSPC_LOST_UNPROCESSED_DATA")
                print(MARK + "_REAL_NATIVE_V2_SYNTHETIC_ENOSPC="
                      "post_unlink_no_raw_or_debug_loss", flush=True)
                with original_queue.exclusive():
                    need(chain.tip(native_proof).next_sequence == 2,
                         "NATIVE_V2_ENOSPC_ACK_CHAIN_CHANGED")
                # Send genuine known HTTP in the exact archive-retired,
                # second-cut-not-yet-published gap, while dvtws2 is RUNNING.
                gap_count = _scoped_divert_hits(guard, RULES[0])
                gap_reply = p0.exchange(KNOWN, force_rst=False)
                need(gap_reply == p0.request(KNOWN) and
                     _scoped_divert_hits(guard, RULES[0]) > gap_count and
                     attest_native() == native_proof and
                     RAW_PATH.read_bytes() == b"",
                     "NATIVE_V2_REAL_IPFW_HTTP_STALLED_IN_RETIRE_GAP")
                with original_queue.exclusive():
                    with patch.object(v2_prepare, "DEBUG_HIGH_WATERMARK", 0):
                        need(v2_prepare._debug_cut_once(
                            original_queue, native_receipts, native_proof,
                            tip.cursor, tip.raw_first, attest_native,
                            probe_pending_fd, retirement_tip=tip),
                            "NATIVE_V2_SECOND_ORIGINAL_DEBUG_CUT_DID_NOT_COMPLETE")
                need(archived_debug.stat().st_ino == before_second_inode and
                     DEBUG_PATH.stat().st_ino != before_second_inode and
                     DEBUG_PATH.stat().st_nlink == 1 and
                     DEBUG_PATH.read_bytes() == b"" and
                     not fresh_debug.exists(),
                     "NATIVE_V2_SECOND_DEBUG_RETENTION_NOT_QUALIFIED")
                with original_queue.exclusive():
                    need(chain.tip(native_proof).next_sequence == 2,
                         "NATIVE_V2_SECOND_CUT_ACK_CHAIN_CHANGED")
                second_count = _scoped_divert_hits(guard, RULES[0])
                second_known = p0.exchange(KNOWN, force_rst=False)
                need(second_known == p0.request(KNOWN) and
                     _scoped_divert_hits(guard, RULES[0]) > second_count and
                     attest_native() == native_proof and
                     not _native_stopped(guard, process.pid),
                     "NATIVE_V2_HTTP_STALLED_AFTER_SECOND_CUT")

                # The next previously unknown domain must enter ONLY the
                # new native debug/raw and be ACKed by the original chain.
                last_reply = p0.exchange(UNKNOWN_SECOND, force_rst=True)
                need(last_reply == p0.request(UNKNOWN_SECOND),
                     "NATIVE_V2_SECOND_DEBUG_POST_CUT_RAW_HTTP_FAILED")
                time.sleep(0.7)
                need(RAW_PATH.read_text(encoding="ascii").splitlines() ==
                     [UNKNOWN_SECOND] and
                     _debug_match(DEBUG_PATH.read_text(errors="replace"),
                                  preview["observer_native_number"], UNKNOWN_SECOND) and
                     not _debug_match(archived_debug.read_text(errors="replace"),
                                      preview["observer_native_number"], UNKNOWN_SECOND),
                     "NATIVE_V2_POST_SECOND_CUT_EVENT_NOT_EXACTLY_NEW")
                with original_queue.exclusive():
                    with patch.object(v2_prepare, "DEBUG_HIGH_WATERMARK", 0):
                        try:
                            refused_cut = v2_prepare._debug_cut_once(
                                original_queue, native_receipts, native_proof,
                                tip.cursor, tip.raw_first, attest_native,
                                probe_pending_fd,
                                retirement_tip=chain.tip(native_proof))
                        except v2_prepare.OriginalV2PrepareRefused as exc:
                            need(str(exc) in {
                                "retained_debug_ack_not_proven",
                                "retained_debug_writer_fd_not_drained"},
                                "NATIVE_V2_UNPROVEN_THIRD_CUT_WRONG_REFUSAL")
                        else:
                            # No old archive can be cut while this new raw
                            # discovery is still awaiting a destination ACK.
                            # The current source intentionally returns False
                            # (no cut), not an exception, in that state.
                            need(refused_cut is False,
                                 "NATIVE_V2_UNPROVEN_THIRD_CUT_ACCEPTED")
                    need(RAW_PATH.read_text(encoding="ascii").splitlines() ==
                         [UNKNOWN_SECOND], "NATIVE_V2_UNPROVEN_THIRD_CUT_DROPPED_RAW")
                    final_pending = v2_prepare.prepare_original_v2_locked(
                        original_queue, native_receipts, attest=attest_native,
                        inspect=probe_pending_fd, inspect_debug=probe_pending_fd)
                    need(final_pending is not None, "NATIVE_V2_FINAL_RAW_NOT_PREPARED")
                    commit_real_raw(final_pending, (UNKNOWN_SECOND,))
                    need(chain.tip(native_proof).next_sequence == 3,
                         "NATIVE_V2_FINAL_CURSOR_ACK_NOT_PERSISTED")
                need(set(final.read_text(encoding="ascii").splitlines()) ==
                     {"!manual.invalid", UNKNOWN, UNKNOWN_MIDCUT,
                      UNKNOWN_AFTER, UNKNOWN_SECOND},
                     "NATIVE_V2_POST_SECOND_CUT_USER_DATA_MISSING")
                print(MARK + "_REAL_NATIVE_SECOND_DEBUG_CUT="
                      "real_ipfw_running_same_pid_two_ack_before_retire_"
                      "busy_fd_refused_enospc_recovered_final_raw_acked", flush=True)

    finally:
        failures = []
        # Unconditional safe unwind for SIGSTOP even after a failed check,
        # before terminating the original engine and restoring original FD9.
        if stopped_by_test and process is not None and process.poll() is None:
            process.send_signal(signal.SIGCONT)
        # The bounded synthetic traffic client must not survive into IPFW
        # rule cleanup even when the stopped-PID experiment refuses.
        if inflight_thread is not None:
            inflight_thread.join(timeout=8)
            if inflight_thread.is_alive():
                failures.append("NATIVE_STOPPED_DIVERT_CLIENT_LEAKED")
        for rule in reversed(installed):
            if guard.cmd("/sbin/ipfw", "-q", "delete", str(rule)).returncode:
                failures.append("SCOPED_DIVERT_RULE_LEAKED")
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        rules_now = guard.cmd("/sbin/ipfw", "-q", "list")
        if rules_now.returncode != 0 or rules_now.stdout != initial_rules:
            failures.append("IPFW_NOT_RESTORED_TO_INITIAL_RULES")
        # Capture only bounded local evidence before disposable cleanup.
        if logfile is not None and logfile.is_file():
            observed_native_log = logfile.read_text(errors="replace")[-262144:]
        # The intentional disposable debug swap may leave native writes on
        # the previous inode; the original first-match assertion must check
        # BOTH files rather than silently discarding their historical bytes.
        debug_parts = []
        if first_debug_snapshot:
            debug_parts.append(first_debug_snapshot[-32768:])
        if archived_debug is not None and archived_debug.is_file():
            debug_parts.append(archived_debug.read_text(errors="replace")[-32768:])
        if DEBUG_PATH.is_file():
            debug_parts.append(DEBUG_PATH.read_text(errors="replace")[-32768:])
        observed_debug_log = "\n".join(debug_parts)
        if started and guard.cmd("pgrep", "-x", "dvtws2").returncode != 1:
            failures.append("ISOLATED_ENGINE_NOT_STOPPED")
        if PRODUCER.is_dir() and not PRODUCER.is_symlink():
            shutil.rmtree(PRODUCER)
        if PRODUCER.exists() or PRODUCER.is_symlink():
            failures.append("PRODUCER_ROOT_NOT_CLEANED")
        if case is not None:
            case.doCleanups()
        # Keep the SAME original FD9 through BOTH engine and scoped IPFW
        # cleanup; never release the kernel lifecycle lock first.
        if fd9_context is not None:
            fd9_context.__exit__(None, None, None)
        need(not failures, ";".join(failures))
    need(started and logfile is not None, "ENGINE_NOT_EXERCISED")
    need(native_rollover is not None,
         "POST_ROTATION_NATIVE_WRITER_EVIDENCE_MISSING")
    native_number = preview["observer_native_number"]
    need(_debug_match(observed_debug_log, native_number),
         "RAW_APPEND_DEBUG_PROFILE_NOT_CORRELATED")
    need(f"autohostlist profile {native_number} " in observed_native_log,
         "NATIVE_OBSERVER_PROFILE_NOT_SELECTED")
    need("desync profile 1 " in observed_native_log,
         "NATIVE_KNOWN_FIRST_MATCH_NOT_SELECTED")
    need("* lua 'multisplit" in observed_native_log,
         "ORIGINAL_AUTHORIZED_LUA_NOT_EXERCISED")
    # No raw, debug or process output retained; no owner-machine changes.
    if quiesced_cut:
        print(MARK + "_REAL_NATIVE_QUIESCED_SAME_PID=PASS", flush=True)
    print(MARK + "=PASS_NATIVE_PINNED_PREVIEW_FIRST_MATCH_RAW_DEBUG_ONLY",
          flush=True)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            p0, _ = components()
            need(_debug_match(f"hello : profile 2 (tail) : client 127.0.0.1:111 : "
                              f"proto http : adding to {RAW_PATH} {UNKNOWN}", 2),
                 "DEBUG_CORRELATION_PARSER_REJECTED_VALID")
            need(not _debug_match("hello : profile 1 : adding to /tmp/wrong", 2),
                 "DEBUG_CORRELATION_FALSE_POSITIVE")
            need(_exclusive_native_route(
                UNKNOWN_QUIESCED + "\n", "", UNKNOWN_QUIESCED) == "previous" and
                 _exclusive_native_route(
                     "", UNKNOWN_QUIESCED + "\n", UNKNOWN_QUIESCED) == "current",
                 "QUIESCED_NEW_RAW_ROUTE_MISCLASSIFIED")
            need(_exclusive_native_route(
                UNKNOWN_MIDCUT + "\n", "", UNKNOWN_MIDCUT) == "previous" and
                 _exclusive_native_route(
                     "", UNKNOWN_MIDCUT + "\n", UNKNOWN_MIDCUT) == "current",
                 "NATIVE_MIDCUT_RAW_ROUTE_MISCLASSIFIED")
            need(_exclusive_native_route(
                UNKNOWN_AFTER + "\n", "", UNKNOWN_AFTER) == "previous",
                 "OLD_RAW_ROUTE_MISCLASSIFIED")
            need(_exclusive_native_route(
                "", UNKNOWN_AFTER + "\n", UNKNOWN_AFTER) == "current",
                 "NEW_RAW_ROUTE_MISCLASSIFIED")
            fake = (f"hello : profile 2 (tail) : client 127.0.0.1:111 : "
                    f"proto http : adding to {RAW_PATH} {UNKNOWN_AFTER}\n")
            need(_exclusive_native_route(fake, "", UNKNOWN_AFTER,
                                         debug_number=2) == "previous" and
                 _exclusive_native_route("", fake, UNKNOWN_AFTER,
                                         debug_number=2) == "current",
                 "NATIVE_DEBUG_ROUTE_MISCLASSIFIED")
            mid_debug = fake.replace(UNKNOWN_AFTER, UNKNOWN_MIDCUT)
            need(_exclusive_native_route(
                    "", UNKNOWN_MIDCUT + "\n", UNKNOWN_MIDCUT) == "current" and
                 _exclusive_native_route(
                    mid_debug, "", UNKNOWN_MIDCUT,
                    debug_number=2) == "previous",
                 "NATIVE_SPLIT_GENERATION_ROUTE_MISCLASSIFIED")
            try:
                _exclusive_native_route(UNKNOWN_AFTER + "\n",
                                        UNKNOWN_AFTER + "\n", UNKNOWN_AFTER)
            except RuntimeError:
                pass
            else:
                raise RuntimeError("DUPLICATE_NATIVE_ROLLOVER_ACCEPTED")
            need(UNKNOWN_SECOND not in {UNKNOWN, UNKNOWN_AFTER, UNKNOWN_MIDCUT},
                 "SECOND_NATIVE_DEBUG_TEST_HOST_COLLISION")
            print(MARK + "_SELF_TEST=PASS_SOURCE_ONLY")
        elif len(sys.argv) == 3 and sys.argv[1] in (
                "--native", "--native-quiesced"):
            _native(Path(sys.argv[2]),
                    quiesced_cut=sys.argv[1] == "--native-quiesced")
        else:
            raise RuntimeError("usage: --self-test | --native /tmp/p4c3-native-*")
    except Exception as exc:
        print(MARK + "=REFUSED:" + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
