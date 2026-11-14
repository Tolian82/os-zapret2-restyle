#!/usr/bin/env python3
"""#1052 P2k8o: inert original P2a raw rotation -> P2k8n v2 intent.

This is a *current-generation-only* import helper, not a minute worker.
One ORIGINAL queue flock protects preflight, original crash recovery or
rotation, real P2b FD drain, P2k1 debug pairing and durable v2 prepare.
No Config/FD9 child, destination writes, ACK, cron or old-owner migration.
"""
from __future__ import annotations

import os
from pathlib import Path
import pwd
import sys
from typing import Callable

from auto_detect_cursor_chain import (CursorChain, CursorChainRefused,
                                      MAX_STEPS, PENDING)
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_fd import probe_pending_fd
from auto_detect_original_v2_source import (qualified_current_source, OriginalSourceRefused)
from auto_detect_owner import (GenerationProof, GenerationRefused,
                               attest_running_generation)
from auto_detect_queue import DurableInbox, QueueSafetyError
from auto_detect_storage import ENGINE_USER
from auto_detect_original_lock_handoff import QUEUE_ROOT


class OriginalV2PrepareRefused(RuntimeError):
    """Do not rotate or discard another generation's original raw segment."""


def prepare_original_v2_locked(
    queue: DurableInbox, receipts: EpochReceipts, *,
    attest: Callable[[], GenerationProof] = attest_running_generation,
    inspect: Callable = probe_pending_fd,
) -> Path | None:
    """Return one prepared ORIGINAL pending inode, without commit or ACK.

    The same queue.open-file-description must be held by the caller until
    its eventual separate Config-held processing. The exact protected
    *empty debug epoch* must already exist; no unauthenticated bootstrap.

    Preflight precedes any raw mutation:
      - v1/v2 journal mixing, corruption and chain capacity refuse;
      - pending from a different generation or >1 pending refuse;
      - an open v2 slot takes precedence over fresh inbox bytes;
      - an open slot with no original pending requires prior authorized
        ACK recovery, never a guessed new rotation.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(receipts, EpochReceipts) or
            queue.uid != receipts.uid or
            queue.writer_gid != receipts.writer_gid or
            not callable(attest) or not callable(inspect)):
        raise OriginalV2PrepareRefused("original_queue_epoch_lock_required")
    try:
        proof = qualified_current_source(attest(), queue)
        chain = CursorChain(receipts, queue)
        tip = chain.tip(proof)  # actual original P2k2a epoch, not fabricated
        pending = queue.segments()
        if (len(pending) > 1 or any(
                not PENDING.fullmatch(path.name) or
                not path.name.startswith(proof.generation + "-")
                for path in pending)):
            raise OriginalV2PrepareRefused("historical_or_ambiguous_pending_retained")
        if tip.open_intent is not None:
            # A crash after physical unlink but before slot ACK must recover
            # under a separate qualified original checkpoint/Config owner.
            # This source-only staging seam may never guess a completion.
            if not pending:
                raise OriginalV2PrepareRefused("unacknowledged_pending_needs_original_ack")
            if tip.open_intent["pending_name"] != pending[0].name:
                raise OriginalV2PrepareRefused("unacknowledged_pending_identity_mismatch")
        elif tip.next_sequence >= MAX_STEPS:
            raise OriginalV2PrepareRefused("bounded_cursor_chain_capacity")
        # The v2 tip includes its currently OPEN intent in used_pending_names.
        # Retrying that exact unacknowledged inode is necessary for durable
        # crash recovery. Only a name from a previously ACKed slot is reuse.
        if (pending and tip.open_intent is None and
                pending[0].name in tip.used_pending_names):
            raise OriginalV2PrepareRefused("acknowledged_pending_name_reused")
        if attest() != proof:
            raise OriginalV2PrepareRefused("original_owner_changed_before_rotation")
        if pending:
            # Reuse a fully rotated pending first, including if a new live
            # inbox already contains later data. For a P2a crash *after*
            # hardlink and before replace, complete only this exact inode.
            segment = pending[0]
            inode = segment.lstat()
            live = queue.inbox.lstat()
            if (inode.st_dev, inode.st_ino) == (live.st_dev, live.st_ino):
                segment = queue.rotate(generation=proof.generation)
        else:
            segment = queue.rotate(generation=proof.generation)
        if segment is None:
            return None
        if attest() != proof:
            raise OriginalV2PrepareRefused("original_owner_changed_after_rotation")
        # Native P2b FD.DRAINED and P2k1 exact debug/raw proof happen
        # INSIDE this same original queue lock, in the v2 primitive.
        slot = chain.prepare(proof, segment, attest=attest, inspect=inspect)
        if (not isinstance(slot, Path) or not slot.is_dir() or
                attest() != proof):
            raise OriginalV2PrepareRefused("original_owner_changed_after_intent")
        return segment
    except (OriginalSourceRefused, CursorChainRefused, QueueSafetyError,
            ReceiptRefused, GenerationRefused, OSError, ValueError, TypeError,
            AttributeError, KeyError) as exc:
        raise OriginalV2PrepareRefused("original_v2_prepared_intent_unavailable") from exc


def run_native_original_v2_prepare_once() -> Path | None:
    """Hard-coded future FreeBSD original worker seam; NOT registered."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise OriginalV2PrepareRefused("native_original_root_only")
    try:
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise OriginalV2PrepareRefused("native_original_writer_group_missing")
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        with queue.exclusive():
            return prepare_original_v2_locked(queue, receipts)
    except (QueueSafetyError, ReceiptRefused, KeyError, OSError) as exc:
        raise OriginalV2PrepareRefused("native_original_v2_unavailable") from exc


def main() -> None:
    raise OriginalV2PrepareRefused("original_fd9_worker_and_config_child_not_enabled")


if __name__ == "__main__":
    main()
