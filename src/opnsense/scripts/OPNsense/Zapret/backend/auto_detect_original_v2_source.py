#!/usr/bin/env python3
"""#1052 P2k8o: independent original current-generation source for v2.

This module intentionally imports NO P2k8m/v1 intent coordinator. Retain
the original P2a DurableInbox, P2b native FD attester and P2c engine-owner
witness; these are stable lower-level authorities, not a second system.
Neither a stored receipt nor a raw filename can establish current ownership.
No standalone worker, polling, Config writer or collector is registered.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import os
from pathlib import Path
import re
import stat
import sys

from auto_detect_debug_window import MAX_RAW, _raw_hosts, DebugWindowRefused
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox, QueueSafetyError, MAX_SEGMENT, _identity, _stat_regular
from auto_detect_storage import _learning_names, StorageRefused

GEN = re.compile(r"[0-9a-f]{32}\Z")
MAX_READ = min(MAX_RAW, MAX_SEGMENT)


class OriginalSourceRefused(ValueError):
    """Original process or detached raw inode evidence is ambiguous."""


def qualified_current_source(proof: object, queue: DurableInbox) -> GenerationProof:
    """Demand an ORIGINAL current engine and exact original protected paths.

    Do not infer current generation from historical receipts, name prefixes,
    old process PIDs, or a second parser of the original Config.
    """
    if (not isinstance(queue, DurableInbox) or
            not isinstance(proof, GenerationProof) or
            not GEN.fullmatch(proof.generation) or
            proof.generation != proof.operation_id or
            type(proof.owner.pid) is not int or proof.owner.pid <= 1 or
            proof.raw_path != str(queue.inbox) or
            proof.debug_path != str(queue.root / "debug.log") or
            (proof.observer_native_number, "observer", None) not in proof.profiles):
        raise OriginalSourceRefused("unqualified_original_current_source")
    return proof



# TZ6v4: read-only original-P2a multi-inbox physical evidence.
# Native auto-HOSTLIST is a working list. Neither diagnostic debug nor
# this transient snapshot authorizes deleting its rows or ACKing a cursor.
# The production caller must bind these rows to the SAME sealed FD9 owner,
# prelaunch inode set, epoch, original P2b FD evidence and durable WAL.
@dataclass(frozen=True)
class LearningCursor:
    generation: str
    native_number: int
    hostlist: str
    path: str
    device: int
    inode: int
    offset: int
    prefix_sha256: str


@dataclass(frozen=True)
class LearningWindow:
    before: LearningCursor
    after: LearningCursor
    rows: bytes
    physical: tuple[int, int, int, int, int, int]



def preview_learning_pretraffic_cursors_locked(
    queue: DurableInbox,
    wire: str,
    learning: tuple[tuple[int, str, str], ...],
    *,
    root_gid: int,
    engine_uid: int,
    attest,
) -> dict[str, LearningCursor]:
    """Recreate zero-offset N-inbox cursors from the FULL original FD9 wire.

    This is the prelaunch *read-only* source half of a future single epoch
    seed, NOT a production autorun command or a cursor store. The original
    held FD9 + independently verified sealed schema3 owner must supply the
    wire, mapping, and attest callback. It refuses files touched before
    the pretraffic cut and never repairs/truncates an old producer.
    """
    from auto_detect_post_drop import (
        _witness_decode_learning, _check_layout, PostDropRefused)
    from auto_detect_debug_window import _read_exact
    if (not isinstance(queue, DurableInbox) or not queue._held or
            queue.writer_gid is None or type(root_gid) is not int or
            root_gid < 0 or type(engine_uid) is not int or engine_uid <= 0 or
            not callable(attest)):
        raise OriginalSourceRefused("learning_pretraffic_original_fd9_queue_required")
    try:
        witness = _witness_decode_learning(
            wire, learning, root=queue.root, root_uid=queue.uid,
            root_gid=root_gid, engine_uid=engine_uid,
            engine_gid=queue.writer_gid)
        if len(witness.identities) != 2 + len(learning) or attest() is not True:
            raise OriginalSourceRefused("learning_pretraffic_owner_or_source_changed")
        _check_layout(queue.root, queue.uid, root_gid, queue.writer_gid,
                      witness.learning_names)
        queue._verify()
        if queue.segments():
            raise OriginalSourceRefused("learning_pretraffic_has_unacknowledged_queue")
        paths = (queue.inbox, queue.root / "debug.log",
                 *(queue.root / name for name in witness.learning_names))
        seen = set()
        first = []
        for path, expected in zip(paths, witness.identities):
            physical, content = _read_exact(
                path, owner_uid=queue.uid, writer_gid=queue.writer_gid)
            identity = physical.st_dev, physical.st_ino, physical.st_nlink
            if (content or physical.st_size != 0 or identity != expected or
                    identity[:2] in seen):
                raise OriginalSourceRefused("learning_pretraffic_inode_not_empty_or_same")
            seen.add(identity[:2])
            first.append((identity, physical.st_mtime_ns, physical.st_ctime_ns))
        # Even with the original queue locked, dvtws2 can append without
        # this flock. Validate all N names/contents again as a single cut.
        for index, path in enumerate(paths):
            physical, content = _read_exact(
                path, owner_uid=queue.uid, writer_gid=queue.writer_gid)
            if (content or physical.st_size != 0 or
                    (physical.st_dev, physical.st_ino, physical.st_nlink,
                     physical.st_mtime_ns, physical.st_ctime_ns) !=
                    (*first[index][0], first[index][1], first[index][2])):
                raise OriginalSourceRefused("learning_pretraffic_raced_native_writer")
        _check_layout(queue.root, queue.uid, root_gid, queue.writer_gid,
                      witness.learning_names)
        queue._verify()
        if queue.segments() or attest() is not True:
            raise OriginalSourceRefused("learning_pretraffic_owner_changed_after_cut")
        return {
            path: LearningCursor(
                generation=witness.learning_names[0][9:41],
                native_number=number, hostlist=hostlist, path=path,
                device=witness.identities[index + 2][0],
                inode=witness.identities[index + 2][1],
                offset=0, prefix_sha256=hashlib.sha256(b"").hexdigest(),
            )
            for index, (number, hostlist, path) in enumerate(learning)
        }
    except OriginalSourceRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, QueueSafetyError,
            DebugWindowRefused, PostDropRefused) as exc:
        raise OriginalSourceRefused("learning_pretraffic_witness_refused") from exc


def preview_original_learning_windows_locked(
    queue: DurableInbox,
    learning: tuple[tuple[int, str, str], ...],
    cursors: dict[str, LearningCursor],
    *,
    attest,
) -> dict[str, LearningWindow]:
    """Read exact native append tails under the ONE original P2a queue FD.

    The learning tuples must come from the independently checked final
    native argv/source map and cursors from an immutable generation epoch,
    NOT caller-synthesized defaults. The attest callback must revalidate
    that exact running engine/epoch; injected callbacks serve tests only.
    No cursor persistence, rotation, writer-FD drain or ACK occurs here.
    """
    # Resolve the registered hostlists only when this inert preview runs.
    # Import-time resolution forms a cycle through EpochReceipts/P2 destination.
    from auto_detect_owned_sources import KNOWN_HOSTLISTS
    if (not isinstance(queue, DurableInbox) or not queue._held or
            queue.writer_gid is None or not callable(attest) or
            type(learning) is not tuple or not 1 <= len(learning) <= 255 or
            type(cursors) is not dict or len(cursors) != len(learning)):
        raise OriginalSourceRefused("original_learning_queue_and_epoch_required")
    try:
        numbers, paths, generations = [], [], set()
        for number, hostlist, pathname in learning:
            if (type(number) is not int or not 1 <= number <= 255 or
                    hostlist not in KNOWN_HOSTLISTS or
                    type(pathname) is not str):
                raise OriginalSourceRefused("unqualified_learning_profile")
            p = Path(pathname)
            if not p.is_absolute() or p.parent != queue.root:
                raise OriginalSourceRefused("learning_path_not_in_original_producer")
            generations.add(p.name[9:41])
            numbers.append(number)
            paths.append(pathname)
            if p.name != f"learning-{p.name[9:41]}-{number}.txt":
                raise OriginalSourceRefused("learning_filename_does_not_match_profile")
        _learning_names(tuple(Path(p).name for p in paths))
        if (len(generations) != 1 or
                numbers != list(range(numbers[0], numbers[0] + len(numbers))) or
                len(set(paths)) != len(paths) or set(cursors) != set(paths) or
                attest() is not True):
            raise OriginalSourceRefused("unqualified_learning_current_owner")
        generation = next(iter(generations))
        queue._verify()
        allowed = {"pending", "inbox.txt", "debug.log", "worker.lock"}
        allowed.update(Path(p).name for p in paths)
        if set(os.listdir(queue.root)) - allowed:
            raise OriginalSourceRefused("foreign_learning_producer_entry")

        results: dict[str, LearningWindow] = {}
        witnesses = {}
        total_new = 0
        def identity(st):
            return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns,
                    st.st_ctime_ns, st.st_nlink, st.st_uid, st.st_gid,
                    stat.S_IMODE(st.st_mode))
        for number, hostlist, pathname in learning:
            old = cursors[pathname]
            if (not isinstance(old, LearningCursor) or
                    (old.generation, old.native_number, old.hostlist, old.path) !=
                    (generation, number, hostlist, pathname) or
                    type(old.device) is not int or old.device < 0 or
                    type(old.inode) is not int or old.inode <= 0 or
                    type(old.offset) is not int or old.offset < 0 or
                    not re.fullmatch(r"[0-9a-f]{64}", old.prefix_sha256)):
                raise OriginalSourceRefused("unqualified_learning_sealed_cursor")
            p = Path(pathname)
            before = _stat_regular(p, queue.uid, max_size=MAX_SEGMENT,
                                   writer_gid=queue.writer_gid)
            if (before.st_nlink != 1 or
                    (before.st_dev, before.st_ino) != (old.device, old.inode) or
                    before.st_size < old.offset):
                raise OriginalSourceRefused("native_learning_inode_or_cursor_drift")
            fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                opened = os.fstat(fd)
                if identity(opened) != identity(before):
                    raise OriginalSourceRefused("native_learning_fd_changed")
                content = bytearray()
                while len(content) < before.st_size:
                    chunk = os.read(fd, min(65536, before.st_size - len(content)))
                    if not chunk:
                        raise OriginalSourceRefused("native_learning_short_read")
                    content.extend(chunk)
                finished = os.fstat(fd)
            finally:
                os.close(fd)
            named = _stat_regular(p, queue.uid, max_size=MAX_SEGMENT,
                                  writer_gid=queue.writer_gid)
            if (identity(before) != identity(finished) or
                    identity(finished) != identity(named) or
                    len(content) != before.st_size or
                    hashlib.sha256(content[:old.offset]).hexdigest() != old.prefix_sha256):
                raise OriginalSourceRefused("native_learning_content_or_prefix_changed")
            tail = bytes(content[old.offset:])
            total_new += len(tail)
            if total_new > MAX_READ:
                raise OriginalSourceRefused("native_learning_combined_raw_exceeds_limit")
            if tail:
                _raw_hosts(tail)
            new_cursor = replace(
                old, offset=len(content),
                prefix_sha256=hashlib.sha256(content).hexdigest())
            results[pathname] = LearningWindow(
                old, new_cursor, tail,
                (named.st_dev, named.st_ino, named.st_size,
                 named.st_mtime_ns, named.st_ctime_ns, named.st_nlink))
            witnesses[pathname] = identity(named)
        # Validate all N files once more, not just the last file. An append
        # racing a later read is NOT a stable all-sources snapshot.
        for pathname, pinned in witnesses.items():
            current = _stat_regular(Path(pathname), queue.uid,
                                    max_size=MAX_SEGMENT,
                                    writer_gid=queue.writer_gid)
            if identity(current) != pinned:
                raise OriginalSourceRefused("native_learning_changed_between_files")
        if set(os.listdir(queue.root)) - allowed:
            raise OriginalSourceRefused("foreign_learning_producer_entry")
        queue._verify()
        if attest() is not True:
            raise OriginalSourceRefused("native_learning_owner_changed_during_read")
        return results
    except OriginalSourceRefused:
        raise
    except (OSError, QueueSafetyError, StorageRefused, DebugWindowRefused,
            ValueError, TypeError, KeyError, AttributeError) as exc:
        raise OriginalSourceRefused("native_learning_physical_snapshot_refused") from exc




# ТЗ_6v4: the original P2 source-to-P1 *read-only* boundary.
# The current product never calls this function: schema3 requires a future
# original-FD9/P2b/WAL owner before any durable cursor, Found or ACK.
def preview_original_learning_candidates_locked(
    queue: DurableInbox, receipts, proof, workspace: Path, *, attest,
) -> dict:
    """Prove one stable all-N native/debug candidate from the sealed epoch.

    An immutable schema3 pretraffic/epoch and the independently reattested
    original running process are required. The native inbox files are WORKING
    hostlists: the result has no permission to clear, rotate or ACK them.
    """
    import json
    from auto_detect_debug_window import MAX_WINDOW, _read_exact
    from auto_detect_epoch_receipts import EpochReceipts, _read
    from auto_detect_origin_map import LEARNING_PROPOSAL
    from auto_detect_owner import (
        LearningGenerationProof, MAX_ARGS, MAX_MAP, _secure_bytes,
    )
    from auto_detect_original_v2_model import preview_learning_domains

    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(receipts, EpochReceipts) or
            receipts.uid != queue.uid or
            receipts.writer_gid != queue.writer_gid or
            not isinstance(proof, LearningGenerationProof) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            not callable(attest) or attest() != proof):
        raise OriginalSourceRefused("learning_original_epoch_and_queue_required")
    try:
        if sys.platform.startswith("freebsd"):
            from voice_ipfw_adapter import require_lifecycle_lock
            require_lifecycle_lock()
        queue._verify()
        if queue.segments():
            raise OriginalSourceRefused("learning_preview_pending_not_reconciled")
        folder, seed, pretraffic_raw = receipts._learning_pretraffic(
            proof, queue, workspace)
        epoch = json.loads(_read(folder / "epoch.json", receipts.uid))
        required = {
            "schema", "kind", "generation", "operation_id",
            "owner_candidate_sha256", "final_args_sha256",
            "native_map_sha256", "pretraffic_sha256", "owner_pid",
            "owner_start", "owner_executable", "files", "learning",
            "ack_authorized",
        }
        if (not isinstance(epoch, dict) or set(epoch) != required or
                type(epoch["schema"]) is not int or epoch["schema"] != 3 or
                epoch["kind"] != "original-native-learning-epoch" or
                epoch["generation"] != proof.generation or
                epoch["operation_id"] != proof.operation_id or
                epoch["owner_candidate_sha256"] != proof.owner_candidate_sha256 or
                epoch["final_args_sha256"] != proof.final_args_sha256 or
                epoch["native_map_sha256"] != proof.native_map_sha256 or
                epoch["pretraffic_sha256"] != hashlib.sha256(
                    pretraffic_raw).hexdigest() or
                (epoch["owner_pid"], epoch["owner_start"],
                 epoch["owner_executable"]) !=
                (proof.owner.pid, proof.owner.started, proof.owner.executable) or
                epoch["files"] != seed["files"] or
                epoch["learning"] != seed["learning"] or
                epoch["ack_authorized"] is not False):
            raise OriginalSourceRefused("learning_epoch_not_original_running_owner")
        release = workspace / "release"
        original = _secure_bytes(release / "dvtws.original.args",
                                 MAX_ARGS, receipts.uid)
        argv = _secure_bytes(release / "dvtws.args", MAX_ARGS, receipts.uid)
        active_map = json.loads(_secure_bytes(
            release / "auto-detect-generation.json", MAX_MAP, receipts.uid))
        # _learning_pretraffic independently reconstituted the sealed ACTIVE
        # map from the original generator. Reuse the strict original P1
        # decoder's proposal format without treating this conversion as an
        # extra activation or authority.
        projection = {**active_map, "evidence": LEARNING_PROPOSAL,
                      "activation_authorized": False}
        map_raw = json.dumps(
            projection, sort_keys=True, separators=(",", ":")).encode()
        cursors = {
            row["path"]: LearningCursor(
                proof.generation, row["native_number"], row["hostlist"],
                row["path"], row["device"], row["inode"], row["offset"],
                row["prefix_sha256"])
            for row in epoch["learning"]
        }

        debug = queue.root / "debug.log"
        debug_id = epoch["files"][1]
        first_stat, debug_bytes = _read_exact(
            debug, owner_uid=receipts.uid, writer_gid=queue.writer_gid)
        def fingerprint(st):
            return (st.st_dev, st.st_ino, st.st_nlink, st.st_uid, st.st_gid,
                    stat.S_IMODE(st.st_mode), st.st_size, st.st_mtime_ns,
                    st.st_ctime_ns)
        if ((first_stat.st_dev, first_stat.st_ino, first_stat.st_nlink) !=
                (debug_id["device"], debug_id["inode"], debug_id["nlink"]) or
                len(debug_bytes) > MAX_WINDOW or
                (debug_bytes and not debug_bytes.endswith(b"\n")) or
                b"\r" in debug_bytes or b"\x00" in debug_bytes):
            raise OriginalSourceRefused("learning_debug_not_sealed_complete_window")
        windows = preview_original_learning_windows_locked(
            queue, proof.learning, cursors, attest=lambda: attest() == proof)
        observations = preview_learning_domains(
            map_raw, {"id": proof.generation,
                      "candidate": proof.owner_candidate_sha256},
            original, argv,
            {path: window.rows for path, window in windows.items()},
            debug_bytes)
        second_stat, second_debug = _read_exact(
            debug, owner_uid=receipts.uid, writer_gid=queue.writer_gid)
        if (fingerprint(first_stat) != fingerprint(second_stat) or
                debug_bytes != second_debug):
            raise OriginalSourceRefused("learning_debug_raced_native_snapshot")
        for path, window in windows.items():
            now = _stat_regular(Path(path), queue.uid, max_size=MAX_SEGMENT,
                                writer_gid=queue.writer_gid)
            if ((now.st_dev, now.st_ino, now.st_size, now.st_mtime_ns,
                 now.st_ctime_ns, now.st_nlink) != window.physical):
                raise OriginalSourceRefused("learning_native_raced_debug_snapshot")
        queue._verify()
        if queue.segments() or attest() != proof:
            raise OriginalSourceRefused("learning_owner_changed_after_p1_preview")
        return {
            "observations": observations,
            "native_cursors": {path: window.after
                               for path, window in windows.items()},
            "debug_end_offset": len(debug_bytes),
            "debug_end_sha256": hashlib.sha256(debug_bytes).hexdigest(),
            "commit_authorized": False,
            "ack_authorized": False,
        }
    except OriginalSourceRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            QueueSafetyError, DebugWindowRefused, RuntimeError) as exc:
        raise OriginalSourceRefused(
            "learning_original_native_debug_candidate_refused") from exc


# One original P2b all-PID FD scan for the qualified schema3 candidate.
# Deliberately not a commit/ACK capability: native auto files are active
# working HOSTLISTs. Nothing may unlink, truncate or replace them here.
def attest_original_learning_drained_candidate_locked(
    queue: DurableInbox, receipts, proof, workspace: Path, *,
    attest, inspect=None,
) -> dict:
    """Recheck N native + debug inodes through original P2b, before P1 WAL.

    The existing P2b inspector scans ALL FreeBSD processes, not only dvtws2.
    A merely readable file or its current PID cannot prove a drained writer.
    Source snapshots are repeated after every inode's global FD check to
    reject any native append / epoch or owner switch across the scan.
    """
    from auto_detect_fd import FDState, probe_pending_fd
    from auto_detect_epoch_receipts import EpochReceipts
    from auto_detect_owner import LearningGenerationProof

    if inspect is None:
        inspect = probe_pending_fd
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(receipts, EpochReceipts) or
            not isinstance(proof, LearningGenerationProof) or
            not callable(attest) or not callable(inspect) or
            attest() != proof):
        raise OriginalSourceRefused("learning_original_p2b_owner_and_lock_required")
    before = preview_original_learning_candidates_locked(
        queue, receipts, proof, workspace, attest=attest)
    if not before["observations"]:
        raise OriginalSourceRefused("learning_no_native_candidate_to_drain")
    # The original epoch was already rechecked by the physical preview;
    # a second independent read pins the authentic prelaunch inode numbers
    # to the ONE current same-generation P2b drain inspection.
    _, seed, _ = receipts._learning_pretraffic(proof, queue, workspace)
    pinned = [
        (queue.root / row["name"], row["device"], row["inode"])
        for row in seed["files"][1:]  # debug + every N native profile
    ]
    if (len(pinned) != len(proof.learning) + 1 or
            pinned[0][0] != queue.root / "debug.log" or
            any(path != Path(source[2]) for (path, _, _), source in
                zip(pinned[1:], proof.learning))):
        raise OriginalSourceRefused("learning_p2b_epoch_sources_not_exact")
    for path, device, inode in pinned:
        if attest() != proof:
            raise OriginalSourceRefused("learning_p2b_owner_switched")
        state = inspect(path, device, inode, owner=proof.owner,
                        writer_gid=queue.writer_gid)
        if state is not FDState.DRAINED or attest() != proof:
            raise OriginalSourceRefused("learning_p2b_global_fd_not_drained")
    after = preview_original_learning_candidates_locked(
        queue, receipts, proof, workspace, attest=attest)
    if before != after or attest() != proof:
        raise OriginalSourceRefused("learning_p2b_sources_changed_during_scan")
    return {
        "observations": after["observations"],
        "native_cursors": after["native_cursors"],
        "debug_end_offset": after["debug_end_offset"],
        "debug_end_sha256": after["debug_end_sha256"],
        "p2b_drained": True,
        "commit_authorized": False,
        "ack_authorized": False,
    }


def detached_original_raw(queue: DurableInbox, pending: Path) -> bytes:
    """Read exact, detached original P2a raw inode with no symlink/truncation.

    The caller must retain the real P2a queue FD lock and independently
    inspect writer-FD state. This snapshot is NOT a drain or an ACK permit.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(pending, Path) or pending.parent != queue.pending):
        raise OriginalSourceRefused("original_queue_pending_lock_required")
    try:
        queue._verify()
        before = _stat_regular(pending, queue.uid, max_size=MAX_READ,
                               writer_gid=queue.writer_gid)
        if (before.st_nlink != 1 or before.st_size <= 0 or
                _identity(queue.inbox) == (before.st_dev, before.st_ino)):
            raise OriginalSourceRefused("pending_not_detached")
        fd = os.open(pending, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            open_stat = os.fstat(fd)
            data = bytearray()
            while len(data) <= MAX_READ:
                chunk = os.read(fd, min(65536, MAX_READ + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            end_stat = os.fstat(fd)
        finally:
            os.close(fd)
        final = pending.lstat()
        ident = lambda st: (st.st_dev, st.st_ino, st.st_size,
                            st.st_mtime_ns, st.st_nlink, stat.S_IMODE(st.st_mode))
        if (ident(before) != ident(open_stat) or
                ident(open_stat) != ident(end_stat) or
                ident(end_stat) != ident(final) or
                len(data) != before.st_size or not data.endswith(b"\n") or
                b"\x00" in data or b"\r" in data):
            raise OriginalSourceRefused("pending_raw_changed_or_incomplete")
        return bytes(data)
    except OSError as exc:
        raise OriginalSourceRefused("original_pending_snapshot_unavailable") from exc
