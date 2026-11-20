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

from auto_detect_debug_window import MAX_RAW, _raw_hosts, DebugWindowRefused
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox, QueueSafetyError, MAX_SEGMENT, _identity, _stat_regular
from auto_detect_storage import _learning_names, StorageRefused
from auto_detect_owned_sources import KNOWN_HOSTLISTS

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
