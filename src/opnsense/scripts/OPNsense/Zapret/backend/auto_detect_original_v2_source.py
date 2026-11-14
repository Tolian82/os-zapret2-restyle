#!/usr/bin/env python3
"""#1052 P2k8o: independent original current-generation source for v2.

This module intentionally imports NO P2k8m/v1 intent coordinator. Retain
the original P2a DurableInbox, P2b native FD attester and P2c engine-owner
witness; these are stable lower-level authorities, not a second system.
Neither a stored receipt nor a raw filename can establish current ownership.
No standalone worker, polling, Config writer or collector is registered.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

from auto_detect_debug_window import MAX_RAW
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox, MAX_SEGMENT, _identity, _stat_regular

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
