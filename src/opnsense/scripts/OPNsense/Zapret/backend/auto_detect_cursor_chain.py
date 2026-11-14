#!/usr/bin/env python3
"""#1052 P2k8n: import-only append-only same-generation cursor succession.

Retains the original P2k2a immutable zero-debug epoch, P2a queue flock,
P2b FD drain, P2k1 native debug correlation and P2k2b CAS destination
transaction. Each minute has its own immutable intent/destination/ACK
folder under the SAME generation. No producer, Config/FD9 owner, worker,
cron or compatibility migration is activated by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from auto_detect_debug_window import (Cursor, DebugWindowRefused, Window,
                                      _read_exact, propose_window)
from auto_detect_destination_commit import DestinationCommit, DestinationRefused
from auto_detect_epoch_receipts import (EMPTY_HASH, EpochReceipts, ReceiptRefused,
                                        _canonical, _directory, _read, _sync, _write_once)
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_v2_source import (qualified_current_source, detached_original_raw)
from auto_detect_owner import GenerationProof, GenerationRefused, attest_running_generation
from auto_detect_queue import DurableInbox, QueueSafetyError

CHAIN = "cursor-chain-v2"
MAX_STEPS = 512
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PENDING = re.compile(r"[0-9a-f]{32}-[0-9a-f]{32}\.txt\Z")
STEP = re.compile(r"[0-9]{8}\Z")


class CursorChainRefused(RuntimeError):
    """An ambiguous historical cursor or pending is never auto-consumed."""


@dataclass(frozen=True)
class ChainTip:
    next_sequence: int
    cursor: Cursor
    previous_ack_sha256: str
    open_folder: Path | None
    open_intent: dict | None
    used_pending_names: frozenset[str]


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path, uid: int) -> tuple[dict, bytes]:
    raw = _read(path, uid)
    try:
        value = json.loads(raw)
    except (TypeError, UnicodeError, ValueError) as exc:
        raise CursorChainRefused("corrupt_original_cursor_record") from exc
    if not isinstance(value, dict):
        raise CursorChainRefused("invalid_original_cursor_record")
    return value, raw


def _checkpoint(slot: Path, intent: dict, uid: int, *,
                targets: dict[str, Path] | None = None) -> tuple[dict, bytes] | None:
    journal = slot / "destination"
    if not journal.exists() and not journal.is_symlink():
        return None
    _directory(journal, uid)
    names = set(os.listdir(journal))
    if names - {"plan.json", "checkpoint.json"} or "checkpoint.json" not in names:
        if names - {"plan.json", "checkpoint.json"}:
            raise CursorChainRefused("foreign_cursor_destination_artifact")
        return None
    if "plan.json" not in names:
        raise CursorChainRefused("checkpoint_without_original_plan")
    plan, plan_raw = _load(journal / "plan.json", uid)
    expected_plan = {
        "schema": 1, "kind": "durable-destination-plan",
        "generation": intent["generation"],
        "pending_name": intent["pending_name"],
        "pending_sha256": intent["pending_sha256"],
        "debug_end_offset": intent["debug_end_offset"],
        "debug_end_sha256": intent["debug_end_sha256"],
    }
    if (set(plan) != set(expected_plan) | {"writes"} or
            any(plan.get(k) != v for k, v in expected_plan.items()) or
            not isinstance(plan.get("writes"), dict)):
        raise CursorChainRefused("checkpoint_plan_differs_from_original_intent")
    if targets is not None and (set(plan["writes"]) - set(targets) or
                                any(not isinstance(entry, dict) or
                                    entry.get("path") != str(targets[key])
                                    for key, entry in plan["writes"].items())):
        raise CursorChainRefused("original_destination_mapping_changed")
    checkpoint, checkpoint_raw = _load(journal / "checkpoint.json", uid)
    expected = {
        "schema": 1, "kind": "destination-and-cursor-committed",
        "generation": intent["generation"],
        "pending_name": intent["pending_name"],
        "plan_sha256": _digest(plan_raw),
        "committed_cursor_offset": intent["debug_end_offset"],
        "committed_cursor_sha256": intent["debug_end_sha256"],
        "ack_authorized": False,
    }
    if checkpoint != expected:
        raise CursorChainRefused("checkpoint_not_original_destination_commit")
    return checkpoint, checkpoint_raw


def _debug_prefix(proof: GenerationProof, end_offset: int, end_sha256: str,
                  uid: int, writer_gid: int | None,
                  debug_device: int, debug_inode: int) -> bool:
    """Allow later appended events but never a truncated or replaced debug."""
    info, content = _read_exact(Path(proof.debug_path),
                                owner_uid=uid, writer_gid=writer_gid)
    return (info.st_dev == debug_device and info.st_ino == debug_inode and
            type(end_offset) is int and 0 <= end_offset <= len(content) and
            _digest(content[:end_offset]) == end_sha256)


def _ack(intent: dict, checkpoint: dict, cp_bytes: bytes) -> dict:
    return {
        "schema": 2, "kind": "cursor-chain-ack-after-pending-fsync",
        "generation": intent["generation"],
        "sequence": intent["sequence"],
        "pending_name": intent["pending_name"],
        "previous_ack_sha256": intent["previous_ack_sha256"],
        "plan_sha256": checkpoint["plan_sha256"],
        "checkpoint_sha256": _digest(cp_bytes),
        "debug_end_offset": intent["debug_end_offset"],
        "debug_end_sha256": intent["debug_end_sha256"],
        "ack_authorized": False,
    }


class CursorChain:
    """One append-only durable cursor chain; no alternate Config/queue owner."""

    def __init__(self, receipts: EpochReceipts, queue: DurableInbox):
        if (not isinstance(receipts, EpochReceipts) or
                not isinstance(queue, DurableInbox) or
                receipts.uid != queue.uid or
                receipts.writer_gid != queue.writer_gid):
            raise CursorChainRefused("original_epoch_and_queue_identity_required")
        self.receipts, self.queue = receipts, queue

    def _root(self, proof: GenerationProof, *, create: bool) -> tuple[Path, dict, bytes]:
        if not self.queue._held:
            raise CursorChainRefused("original_queue_lock_required")
        proof = qualified_current_source(proof, self.queue)
        epoch_folder, epoch = self.receipts._epoch(proof)
        names = set(os.listdir(epoch_folder))
        if (any(n.startswith("intent-") for n in names) or "destination" in names or
                names - {"epoch.json", CHAIN}):
            raise CursorChainRefused("legacy_and_cursor_chain_cannot_mix")
        epoch_raw = _read(epoch_folder / "epoch.json", self.receipts.uid)
        root = epoch_folder / CHAIN
        if not root.exists() and not root.is_symlink() and create:
            root.mkdir(mode=0o700)
            _sync(epoch_folder)
        if root.exists() or root.is_symlink():
            _directory(root, self.receipts.uid)
        return root, epoch, epoch_raw

    def tip(self, proof: GenerationProof) -> ChainTip:
        root, epoch, epoch_raw = self._root(proof, create=False)
        cursor = Cursor(proof.generation, epoch["debug_device"],
                        epoch["debug_inode"], 0, EMPTY_HASH)
        anchor = _digest(epoch_raw)
        if not root.exists():
            return ChainTip(0, cursor, anchor, None, None, frozenset())
        slots = sorted(os.listdir(root))
        if len(slots) > MAX_STEPS or any(
                not STEP.fullmatch(name) or int(name) != i
                for i, name in enumerate(slots)):
            raise CursorChainRefused("noncontiguous_or_unbounded_original_cursor")
        open_folder = None
        open_intent = None
        used_pending_names: set[str] = set()
        for index, name in enumerate(slots):
            folder = root / name
            _directory(folder, self.receipts.uid)
            names = set(os.listdir(folder))
            if "intent.json" not in names or names - {"intent.json", "destination", "ack.json"}:
                raise CursorChainRefused("incomplete_or_foreign_cursor_slot")
            intent, _ = _load(folder / "intent.json", self.receipts.uid)
            expected_keys = {
                "schema", "kind", "generation", "sequence", "pending_name",
                "pending_device", "pending_inode", "pending_size", "pending_sha256",
                "debug_device", "debug_inode", "debug_start_offset",
                "debug_start_sha256", "debug_end_offset", "debug_end_sha256",
                "candidate_count", "previous_ack_sha256", "ack_authorized",
            }
            if (set(intent) != expected_keys or intent.get("schema") != 2 or
                    intent.get("kind") != "cursor-chain-prepared" or
                    intent.get("generation") != proof.generation or
                    type(intent.get("sequence")) is not int or intent["sequence"] != index or
                    type(intent.get("pending_name")) is not str or
                    not PENDING.fullmatch(intent["pending_name"]) or
                    not intent["pending_name"].startswith(proof.generation + "-") or
                    intent["pending_name"] in used_pending_names or
                    any(type(intent.get(k)) is not int or intent[k] <= 0 for k in
                        ("pending_inode", "pending_size", "candidate_count")) or
                    type(intent.get("pending_device")) is not int or
                    intent["pending_device"] < 0 or
                    not HEX64.fullmatch(str(intent.get("pending_sha256"))) or
                    not HEX64.fullmatch(str(intent.get("debug_end_sha256"))) or
                    intent.get("debug_device") != cursor.device or
                    intent.get("debug_inode") != cursor.inode or
                    intent.get("debug_start_offset") != cursor.offset or
                    intent.get("debug_start_sha256") != cursor.prefix_sha256 or
                    type(intent.get("debug_end_offset")) is not int or
                    intent["debug_end_offset"] <= cursor.offset or
                    intent.get("previous_ack_sha256") != anchor or
                    intent.get("ack_authorized") is not False):
                raise CursorChainRefused("cursor_chain_disagrees_with_previous_ack")
            used_pending_names.add(intent["pending_name"])
            checkpoint = _checkpoint(folder, intent, self.receipts.uid)
            if "ack.json" not in names:
                if index != len(slots) - 1:
                    raise CursorChainRefused("unacknowledged_cursor_predecessor")
                open_folder, open_intent = folder, intent
                break
            if checkpoint is None:
                raise CursorChainRefused("ack_without_durable_destination")
            cp, cp_raw = checkpoint
            actual, ack_raw = _load(folder / "ack.json", self.receipts.uid)
            if actual != _ack(intent, cp, cp_raw):
                raise CursorChainRefused("cursor_ack_not_bound_to_checkpoint")
            cursor = Cursor(proof.generation, cursor.device, cursor.inode,
                            intent["debug_end_offset"], intent["debug_end_sha256"])
            anchor = _digest(ack_raw)
        return ChainTip(len(slots), cursor, anchor, open_folder, open_intent,
                        frozenset(used_pending_names))

    def prepare(self, proof: GenerationProof, pending: Path, *,
                attest: Callable = attest_running_generation,
                inspect: Callable = probe_pending_fd) -> Path:
        """Save the next slot only after all prior slot ACKs, current P2c+FD.

        An in-flight slot is replayable, not a permit to replace its intent.
        This operation requires an ALREADY detached original queue inode.
        """
        if (not callable(attest) or not callable(inspect) or
                not self.queue._held or attest() != proof):
            raise CursorChainRefused("current_original_owner_required")
        try:
            qualified_current_source(proof, self.queue)
            pending = Path(pending)
            items = self.queue.segments()
            if (len(items) != 1 or items[0] != pending or
                    not PENDING.fullmatch(pending.name) or
                    not pending.name.startswith(proof.generation + "-")):
                raise CursorChainRefused("historical_or_ambiguous_pending")
            tip = self.tip(proof)
            if tip.next_sequence >= MAX_STEPS and tip.open_folder is None:
                raise CursorChainRefused("cursor_chain_capacity_exhausted")
            before = pending.lstat()
            if (inspect(pending, before.st_dev, before.st_ino, owner=proof.owner,
                        writer_gid=self.queue.writer_gid) is not FDState.DRAINED or
                    attest() != proof):
                raise CursorChainRefused("original_pending_fd_not_drained")
            raw = detached_original_raw(self.queue, pending)
            if tip.open_intent is not None:
                expected = tip.open_intent
                # After first staging, the original engine may append later
                # native events to debug. Verify its sealed *prefix* rather
                # than requiring an identical full debug tail on replay.
                if (expected["pending_name"] != pending.name or
                        expected["pending_device"] != before.st_dev or
                        expected["pending_inode"] != before.st_ino or
                        expected["pending_size"] != len(raw) or
                        expected["pending_sha256"] != _digest(raw) or
                        not _debug_prefix(proof, expected["debug_end_offset"],
                                          expected["debug_end_sha256"],
                                          self.receipts.uid, self.receipts.writer_gid,
                                          expected["debug_device"], expected["debug_inode"])):
                    raise CursorChainRefused("different_unacknowledged_cursor_pending")
                if attest() != proof:
                    raise CursorChainRefused("owner_changed_during_intent_replay")
                return tip.open_folder
            if pending.name in tip.used_pending_names:
                raise CursorChainRefused("completed_pending_name_reused")
            window = propose_window(proof, tip.cursor, raw,
                                    owner_uid=self.receipts.uid,
                                    writer_gid=self.queue.writer_gid)
            if attest() != proof:
                raise CursorChainRefused("owner_changed_during_debug_correlation")
            intent = {
                "schema": 2, "kind": "cursor-chain-prepared",
                "generation": proof.generation, "sequence": tip.next_sequence,
                "pending_name": pending.name,
                "pending_device": before.st_dev, "pending_inode": before.st_ino,
                "pending_size": len(raw), "pending_sha256": _digest(raw),
                "debug_device": tip.cursor.device, "debug_inode": tip.cursor.inode,
                "debug_start_offset": tip.cursor.offset,
                "debug_start_sha256": tip.cursor.prefix_sha256,
                "debug_end_offset": window.proposed_cursor.offset,
                "debug_end_sha256": window.proposed_cursor.prefix_sha256,
                "candidate_count": len(window.candidates),
                "previous_ack_sha256": tip.previous_ack_sha256,
                "ack_authorized": False,
            }
            # Reverify owner/inode right before creating one persistent step.
            if (attest() != proof or
                    inspect(pending, before.st_dev, before.st_ino,
                            owner=proof.owner,
                            writer_gid=self.queue.writer_gid) is not FDState.DRAINED or
                    detached_original_raw(self.queue, pending) != raw):
                raise CursorChainRefused("original_pending_changed_before_persist")
            root, _, _ = self._root(proof, create=True)
            slot = root / f"{tip.next_sequence:08d}"
            if slot.exists() or slot.is_symlink():
                raise CursorChainRefused("cursor_slot_already_claimed")
            slot.mkdir(mode=0o700)
            _sync(root)
            _write_once(slot, "intent.json", _canonical(intent), self.receipts.uid)
            if attest() != proof:
                raise CursorChainRefused("original_owner_changed_after_intent")
            return slot
        except (ReceiptRefused, QueueSafetyError, DebugWindowRefused,
                DestinationRefused, GenerationRefused, OSError, ValueError,
                TypeError, KeyError, AttributeError) as exc:
            raise CursorChainRefused("current_cursor_intent_evidence_unavailable") from exc

    def commit(self, proof: GenerationProof, pending: Path,
               effects: dict, writer: DestinationCommit, *,
               attest: Callable = attest_running_generation,
               inspect: Callable = probe_pending_fd) -> dict:
        """Reuse REAL P2k2b destination CAS for an isolated per-minute slot.

        Caller must be the original Config-locked P1 decision owner. The
        returned checkpoint alone never permits ACK or further cursor use.
        """
        if (not isinstance(writer, DestinationCommit) or
                writer.receipts is not self.receipts or
                writer.queue is not self.queue or not self.queue._held or
                not callable(attest) or not callable(inspect) or
                attest() != proof):
            raise CursorChainRefused("original_config_queue_writer_required")
        try:
            tip = self.tip(proof)
            folder, intent = tip.open_folder, tip.open_intent
            if folder is None or intent is None or intent["pending_name"] != pending.name:
                raise CursorChainRefused("no_prepared_original_cursor_slot")
            pending = Path(pending)
            before = pending.lstat()
            if (inspect(pending, before.st_dev, before.st_ino,
                        owner=proof.owner, writer_gid=self.queue.writer_gid)
                    is not FDState.DRAINED or attest() != proof):
                raise CursorChainRefused("original_writer_fd_not_drained")
            raw = detached_original_raw(self.queue, pending)
            if ((before.st_dev, before.st_ino, len(raw), _digest(raw)) !=
                    (intent["pending_device"], intent["pending_inode"],
                     intent["pending_size"], intent["pending_sha256"])):
                raise CursorChainRefused("original_pending_differs_from_cursor_intent")
            if not _debug_prefix(proof, intent["debug_end_offset"],
                                 intent["debug_end_sha256"], self.receipts.uid,
                                 self.receipts.writer_gid, intent["debug_device"],
                                 intent["debug_inode"]):
                raise CursorChainRefused("debug_changed_before_destination")
            with writer.exclusive_targets():
                checkpoint = writer._locked_commit(folder, intent, raw, effects)
            verified = _checkpoint(folder, intent, self.receipts.uid, targets=writer.targets)
            if (verified is None or checkpoint != verified[0] or attest() != proof):
                raise CursorChainRefused("original_cursor_destination_not_committed")
            return checkpoint
        except (ReceiptRefused, QueueSafetyError, DebugWindowRefused,
                DestinationRefused, GenerationRefused, OSError, ValueError,
                TypeError, KeyError, AttributeError) as exc:
            raise CursorChainRefused("original_cursor_destination_unavailable") from exc

    def acknowledge(self, proof: GenerationProof, pending: Path, completion: dict,
                    writer: DestinationCommit, *,
                    attest: Callable = attest_running_generation,
                    inspect: Callable = probe_pending_fd) -> bool:
        """Only the SAME genuine original PHP child may supply completion.

        Original queue lock is held through P2a physical unlink + ack fsync.
        If interrupted after unlink but before ACK receipt, a completed
        checkpoint + missing inode can finalize the cursor without replaying
        destinations. The entire chain is still revalidated on next tick.
        """
        if (not isinstance(writer, DestinationCommit) or
                writer.receipts is not self.receipts or
                writer.queue is not self.queue or not self.queue._held or
                not isinstance(completion, dict) or not callable(attest) or
                not callable(inspect) or attest() != proof):
            raise CursorChainRefused("original_config_completion_required")
        try:
            tip = self.tip(proof)
            folder, intent = tip.open_folder, tip.open_intent
            pending = Path(pending)
            if folder is None:
                # Idempotent replay after durable ack: no reapplication.
                root, _, _ = self._root(proof, create=False)
                if tip.next_sequence == 0:
                    raise CursorChainRefused("no_completed_original_cursor")
                last = root / f"{tip.next_sequence - 1:08d}"
                previous, _ = _load(last / "intent.json", self.receipts.uid)
                verified = _checkpoint(last, previous, self.receipts.uid,
                                       targets=writer.targets)
                if (previous["pending_name"] != pending.name or
                        verified is None or verified[0] != completion or
                        pending.exists() or pending.is_symlink()):
                    raise CursorChainRefused("different_or_missing_cursor_completion")
                return True
            if intent["pending_name"] != pending.name:
                raise CursorChainRefused("wrong_original_cursor_pending")
            verified = _checkpoint(folder, intent, self.receipts.uid,
                                   targets=writer.targets)
            if verified is None or completion != verified[0]:
                raise CursorChainRefused("original_child_checkpoint_mismatch")
            cp, cp_raw = verified
            if not _debug_prefix(proof, intent["debug_end_offset"],
                                 intent["debug_end_sha256"], self.receipts.uid,
                                 self.receipts.writer_gid, intent["debug_device"],
                                 intent["debug_inode"]):
                raise CursorChainRefused("debug_changed_before_original_ack")

            def still_original() -> bool:
                return attest() == proof

            def drained(path: Path, device: int, inode: int) -> bool:
                return (path == pending and
                        (device, inode) == (intent["pending_device"], intent["pending_inode"]) and
                        still_original() and
                        inspect(path, device, inode, owner=proof.owner,
                                writer_gid=self.queue.writer_gid) is FDState.DRAINED and
                        still_original())

            def committed(raw: bytes) -> bool:
                return (len(raw) == intent["pending_size"] and
                        _digest(raw) == intent["pending_sha256"] and
                        still_original() and
                        _debug_prefix(proof, intent["debug_end_offset"],
                                      intent["debug_end_sha256"],
                                      self.receipts.uid, self.receipts.writer_gid,
                                      intent["debug_device"], intent["debug_inode"]) and
                        _checkpoint(folder, intent, self.receipts.uid,
                                    targets=writer.targets) == verified and
                        still_original())

            if pending.exists() or pending.is_symlink():
                if not self.queue.acknowledge(pending, drained=drained,
                                              committed=committed):
                    return False
            else:
                # No unilateral missing-pending advance without a DURABLE
                # checkpoint and the authenticated exact current owner.
                if not still_original():
                    raise CursorChainRefused("owner_changed_after_pending_unlink")
            if not still_original():
                raise CursorChainRefused("owner_changed_after_physical_unlink")
            _write_once(folder, "ack.json", _canonical(_ack(intent, cp, cp_raw)),
                        self.receipts.uid)
            if not still_original():
                raise CursorChainRefused("owner_changed_after_ack_receipt")
            result = self.tip(proof)
            if result.open_folder is not None or result.cursor.offset != intent["debug_end_offset"]:
                raise CursorChainRefused("ack_cursor_chain_not_durable")
            return True
        except (ReceiptRefused, QueueSafetyError, DebugWindowRefused,
                DestinationRefused, GenerationRefused, OSError, ValueError,
                TypeError, KeyError, AttributeError) as exc:
            raise CursorChainRefused("original_cursor_ack_evidence_unavailable") from exc


def main() -> None:
    raise CursorChainRefused("original_fd9_multiminute_worker_not_enabled")


if __name__ == "__main__":
    main()
