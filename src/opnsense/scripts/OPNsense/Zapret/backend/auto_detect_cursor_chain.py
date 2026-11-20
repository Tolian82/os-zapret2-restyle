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

from auto_detect_debug_window import (Cursor, DebugWindowRefused, MAX_DEBUG,
                                      _raw_hosts, _read_exact, propose_window)
from auto_detect_destination_commit import (DestinationCommit, DestinationRefused,
                                           qualified_destination_plan)
from auto_detect_epoch_receipts import (EMPTY_HASH, EpochReceipts, ReceiptRefused,
                                        _canonical, _directory, _read, _sync, _write_once)
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_v2_source import (qualified_current_source, detached_original_raw)
from auto_detect_owner import GenerationProof, GenerationRefused, attest_running_generation
from auto_detect_queue import DurableInbox, QueueSafetyError

CHAIN = "cursor-chain-v2"
ANCHOR = "anchor.json"
NEXT = CHAIN + ".next"
OLD = CHAIN + ".old"
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
    raw_first: bool
    cycle: int = 0


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
    plan, plan_raw = qualified_destination_plan(
        slot, intent, uid, targets=targets)
    checkpoint, checkpoint_raw = _load(journal / "checkpoint.json", uid)
    expected = {
        "schema": 1, "kind": "destination-and-cursor-committed",
        "generation": intent["generation"],
        "pending_name": intent["pending_name"],
        "plan_sha256": _digest(plan_raw),
        "evidence": intent["evidence"],
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


def _evidence_unchanged(proof: GenerationProof, intent: dict,
                        uid: int, writer_gid: int | None) -> bool:
    """Apply the SAME source proof at intent replay, Config and ACK.

    Native-debug remains tied to its strict prefix. Raw-first instead
    uses the original P2c/FD9 + P2b-drained native raw/Config transaction;
    protected current debug is only an unrelated diagnostic.
    """
    if intent.get("evidence") == "native-debug":
        return _debug_prefix(proof, intent["debug_end_offset"],
                             intent["debug_end_sha256"], uid, writer_gid,
                             intent["debug_device"], intent["debug_inode"])
    if intent.get("evidence") == "raw-first":
        _read_exact(Path(proof.debug_path), owner_uid=uid,
                    writer_gid=writer_gid)
        return True
    return False


def _completed_debug_evidence_unchanged(proof: GenerationProof, intent: dict,
                                        uid: int, writer_gid: int | None) -> bool:
    """Completed-checkpoint witness, never a pre-commit authorization.

    Before a checkpoint native-debug requires the original inode and SHA.
    Afterwards the immutable source-bound plan/checkpoint proves the
    authorized write already happened: a later protected replacement may
    permit exact same pending ACK, but never recomputation or reapplication.
    Same-inode truncation/tampering remains a hard refusal.
    """
    if _evidence_unchanged(proof, intent, uid, writer_gid):
        return True
    if intent.get("evidence") != "native-debug":
        return False
    current, _ = _read_exact(Path(proof.debug_path),
                             owner_uid=uid, writer_gid=writer_gid)
    return (current.st_dev, current.st_ino) != (
        intent["debug_device"], intent["debug_inode"])


def _ack(intent: dict, checkpoint: dict, cp_bytes: bytes) -> dict:
    return {
        "schema": 2, "kind": "cursor-chain-ack-after-pending-fsync",
        "generation": intent["generation"],
        "sequence": intent["sequence"],
        "pending_name": intent["pending_name"],
        "evidence": intent["evidence"],
        "previous_ack_sha256": intent["previous_ack_sha256"],
        "plan_sha256": checkpoint["plan_sha256"],
        "checkpoint_sha256": _digest(cp_bytes),
        "debug_end_offset": intent["debug_end_offset"],
        "debug_end_sha256": intent["debug_end_sha256"],
        "ack_authorized": False,
    }


def _resolved_intent(folder: Path, original: dict, original_raw: bytes,
                     uid: int) -> dict:
    """Derive effective UNKNOWN mode from one immutable crash recovery.

    The native-debug intent is NEVER overwritten. Original bytes plus one
    root-private write-once recovery receipt remain the journal authority;
    both the same original Config commit and subsequent ACK use the derived
    mode. An existing destination plan/checkpoint cannot be silently
    converted to another evidence mode.
    """
    recovery = folder / "recovery.json"
    if not recovery.exists() and not recovery.is_symlink():
        return original
    record, _ = _load(recovery, uid)
    expected = {
        "schema": 2, "kind": "original-native-debug-raw-first-recovery",
        "generation": original["generation"],
        "sequence": original["sequence"],
        "pending_name": original["pending_name"],
        "pending_sha256": original["pending_sha256"],
        "previous_ack_sha256": original["previous_ack_sha256"],
        "original_intent_sha256": _digest(original_raw),
        "ack_authorized": False,
    }
    if (original.get("evidence") != "native-debug" or
            type(record.get("new_debug_device")) is not int or
            type(record.get("new_debug_inode")) is not int or
            type(record.get("new_debug_size")) is not int or
            record["new_debug_device"] < 0 or
            record["new_debug_inode"] <= 0 or
            not 0 <= record["new_debug_size"] <= MAX_DEBUG or
            not isinstance(record.get("new_debug_sha256"), str) or
            not HEX64.fullmatch(record["new_debug_sha256"]) or
            (record["new_debug_device"], record["new_debug_inode"]) ==
            (original["debug_device"], original["debug_inode"]) or
            set(record) != set(expected) | {
                "new_debug_device", "new_debug_inode",
                "new_debug_size", "new_debug_sha256"} or
            any(record.get(name) != value for name, value in expected.items())):
        raise CursorChainRefused("original_native_debug_recovery_tampered")
    return {**original, "evidence": "raw-first",
            "debug_end_offset": original["debug_start_offset"],
            "debug_end_sha256": original["debug_start_sha256"]}


class CursorChain:
    """One append-only durable cursor chain; no alternate Config/queue owner."""

    def __init__(self, receipts: EpochReceipts, queue: DurableInbox):
        if (not isinstance(receipts, EpochReceipts) or
                not isinstance(queue, DurableInbox) or
                receipts.uid != queue.uid or
                receipts.writer_gid != queue.writer_gid):
            raise CursorChainRefused("original_epoch_and_queue_identity_required")
        self.receipts, self.queue = receipts, queue

    def _next_anchor(self, proof: GenerationProof, epoch_raw: bytes,
                     tip: ChainTip) -> dict:
        if (tip.open_folder is not None or tip.open_intent is not None or
                tip.next_sequence != MAX_STEPS or
                type(tip.cycle) is not int or not 0 <= tip.cycle < (1 << 32) - 1 or
                not HEX64.fullmatch(tip.previous_ack_sha256)):
            raise CursorChainRefused("incomplete_original_rollover_source")
        return {
            "schema": 2, "kind": "original-v2-cursor-anchor",
            "generation": proof.generation,
            "owner_operation_id": proof.operation_id,
            "final_args_sha256": proof.final_args_sha256,
            "epoch_sha256": _digest(epoch_raw),
            "cycle": tip.cycle + 1,
            "debug_device": tip.cursor.device,
            "debug_inode": tip.cursor.inode,
            "debug_offset": tip.cursor.offset,
            "debug_prefix_sha256": tip.cursor.prefix_sha256,
            "raw_first": tip.raw_first,
            "previous_ack_sha256": tip.previous_ack_sha256,
            "ack_authorized": False,
        }

    def _checked_anchor(self, proof: GenerationProof, epoch: dict,
                        epoch_raw: bytes, path: Path) -> dict:
        value, _ = _load(path, self.receipts.uid)
        required = {
            "schema", "kind", "generation", "owner_operation_id",
            "final_args_sha256", "epoch_sha256", "cycle",
            "debug_device", "debug_inode", "debug_offset",
            "debug_prefix_sha256", "raw_first", "previous_ack_sha256",
            "ack_authorized",
        }
        if (set(value) != required or value["schema"] != 2 or
                value["kind"] != "original-v2-cursor-anchor" or
                value["generation"] != proof.generation or
                value["owner_operation_id"] != proof.operation_id or
                value["final_args_sha256"] != proof.final_args_sha256 or
                value["epoch_sha256"] != _digest(epoch_raw) or
                type(value["cycle"]) is not int or
                not 1 <= value["cycle"] < (1 << 32) or
                type(value["debug_device"]) is not int or
                type(value["debug_inode"]) is not int or
                value["debug_device"] != epoch["debug_device"] or
                value["debug_inode"] != epoch["debug_inode"] or
                type(value["debug_offset"]) is not int or
                not 0 <= value["debug_offset"] <= MAX_DEBUG or
                not HEX64.fullmatch(str(value["debug_prefix_sha256"])) or
                type(value["raw_first"]) is not bool or
                not HEX64.fullmatch(str(value["previous_ack_sha256"])) or
                value["ack_authorized"] is not False):
            raise CursorChainRefused("invalid_original_rollover_anchor")
        return value

    def _erase_old_tree(self, path: Path) -> None:
        """Reclaim only an already superseded, root-private ACKed tree.

        The successor anchor was durably staged and atomically installed
        before this unlink. On crash, the same original queue lock repeats
        these idempotent, path/owner-checked removals. No live raw or
        debug producer path is even referenced here.
        """
        _directory(path, self.receipts.uid)
        for slot in sorted(path.iterdir()):
            if slot.name == ANCHOR:
                _load(slot, self.receipts.uid)
                slot.unlink()
                continue
            if not STEP.fullmatch(slot.name):
                raise CursorChainRefused("foreign_old_cursor_entry")
            _directory(slot, self.receipts.uid)
            for entry in list(slot.iterdir()):
                if entry.name == "destination":
                    _directory(entry, self.receipts.uid)
                    for child in list(entry.iterdir()):
                        if child.name not in {"plan.json", "checkpoint.json"}:
                            raise CursorChainRefused("foreign_old_destination_entry")
                        self._check_old_file(child)
                        child.unlink()
                    entry.rmdir()
                elif entry.name in {"intent.json", "ack.json", "recovery.json"}:
                    self._check_old_file(entry)
                    entry.unlink()
                else:
                    raise CursorChainRefused("foreign_old_cursor_artifact")
            slot.rmdir()
        _sync(path)
        path.rmdir()
        _sync(path.parent)

    def _check_old_file(self, path: Path) -> None:
        item = path.lstat()
        if (not stat.S_ISREG(item.st_mode) or item.st_uid != self.receipts.uid
                or item.st_nlink != 1 or item.st_mode & 0o077):
            raise CursorChainRefused("unsafe_old_cursor_receipt")

    def _recover_staged_anchor_write(self, prepared: Path) -> None:
        """Finish the original receipt writer's crash-torn hardlink stage.

        _write_once() fsyncs a private .<hex32>.part then hardlinks the
        identical inode to anchor.json. Under the same P2a queue lock only
        that one strict temporary name may be removed. A foreign entry,
        changed inode, or unsafe link count always refuses.
        """
        _directory(prepared, self.receipts.uid)
        names = set(os.listdir(prepared))
        staged = [name for name in names
                  if re.fullmatch(r"\.[0-9a-f]{32}\.part", name)]
        if (len(staged) > 1 or names - {ANCHOR, *staged}):
            raise CursorChainRefused("foreign_original_rollover_stage")
        if not staged:
            return
        temp = prepared / staged[0]
        st = temp.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != self.receipts.uid
                or stat.S_IMODE(st.st_mode) != 0o600
                or st.st_nlink not in (1, 2)):
            raise CursorChainRefused("unsafe_original_rollover_temp")
        anchor = prepared / ANCHOR
        if ANCHOR in names:
            named = anchor.lstat()
            if (not stat.S_ISREG(named.st_mode) or
                    named.st_uid != self.receipts.uid or
                    stat.S_IMODE(named.st_mode) != 0o600 or
                    named.st_nlink != 2 or st.st_nlink != 2 or
                    (named.st_dev, named.st_ino) != (st.st_dev, st.st_ino)):
                raise CursorChainRefused("rollover_hardlink_identity_changed")
        elif st.st_nlink != 1:
            raise CursorChainRefused("foreign_original_rollover_temp_link")
        temp.unlink()
        _sync(prepared)

    def ensure_capacity(self, proof: GenerationProof, *,
                        attest: Callable = attest_running_generation) -> None:
        """Crash-recover the same owner chain, then bound 512 fully ACKed slots.

        Original queue FD and running generation stay unchanged. First
        fsync the successor's immutable epoch-bound ACK anchor, then rename
        the old tree away, rename the successor into place, and only then
        unlink old ACKed receipts. Each interrupted rename is recoverable.
        """
        if (not self.queue._held or not callable(attest) or attest() != proof):
            raise CursorChainRefused("original_rollover_queue_owner_required")
        root, epoch, epoch_raw = self._root(proof, create=False)
        folder = root.parent
        prepared, retired = folder / NEXT, folder / OLD
        if retired.exists() or retired.is_symlink():
            _directory(retired, self.receipts.uid)
            if not root.exists() and not root.is_symlink():
                # Crash after old-root rename, before new-root rename.
                # Recover the complete predecessor first, then verify
                # the prepared next anchor against its genuine full tip.
                retired.rename(root)
                _sync(folder)
            elif prepared.exists() or prepared.is_symlink():
                raise CursorChainRefused("ambiguous_original_rollover_paths")
            else:
                _directory(root, self.receipts.uid)
                self._checked_anchor(proof, epoch, epoch_raw, root / ANCHOR)
                self._erase_old_tree(retired)
        if prepared.exists() or prepared.is_symlink():
            _directory(prepared, self.receipts.uid)
            if not root.exists() or root.is_symlink():
                raise CursorChainRefused("orphan_original_rollover_candidate")
            self._recover_staged_anchor_write(prepared)
            if not os.listdir(prepared):
                # Crash after staging mkdir, before durable anchor creation:
                # no committed state was changed, so recreate safely.
                prepared.rmdir()
                _sync(folder)
            else:
                tip = self.tip(proof)
                expected = self._next_anchor(proof, epoch_raw, tip)
                proposed = self._checked_anchor(
                    proof, epoch, epoch_raw, prepared / ANCHOR)
                if proposed != expected or set(os.listdir(prepared)) != {ANCHOR}:
                    raise CursorChainRefused("stale_original_rollover_candidate")
                if self.queue.segments() or attest() != proof:
                    raise CursorChainRefused("pending_or_changed_original_rollover")
                root.rename(retired)
                _sync(folder)
                prepared.rename(root)
                _sync(folder)
                self._erase_old_tree(retired)
        tip = self.tip(proof)
        if tip.next_sequence < MAX_STEPS:
            return
        if (tip.open_folder is not None or tip.open_intent is not None or
                self.queue.segments() or attest() != proof):
            raise CursorChainRefused("full_original_chain_not_terminal")
        expected = self._next_anchor(proof, epoch_raw, tip)
        if prepared.exists() or prepared.is_symlink() or (
                retired.exists() or retired.is_symlink()):
            raise CursorChainRefused("original_rollover_root_collision")
        prepared.mkdir(mode=0o700)
        _sync(folder)
        _write_once(prepared, ANCHOR, _canonical(expected), self.receipts.uid)
        _sync(prepared)
        if attest() != proof or self.tip(proof) != tip or self.queue.segments():
            raise CursorChainRefused("original_rollover_owner_changed_before_swap")
        root.rename(retired)
        _sync(folder)
        prepared.rename(root)
        _sync(folder)
        self._erase_old_tree(retired)
        if attest() != proof or self.tip(proof).cycle != tip.cycle + 1:
            raise CursorChainRefused("original_rollover_anchor_not_published")

    def _root(self, proof: GenerationProof, *, create: bool) -> tuple[Path, dict, bytes]:
        if not self.queue._held:
            raise CursorChainRefused("original_queue_lock_required")
        proof = qualified_current_source(proof, self.queue)
        epoch_folder, epoch = self.receipts._epoch(proof)
        names = set(os.listdir(epoch_folder))
        if (any(n.startswith("intent-") for n in names) or "destination" in names or
                names - {"pretraffic.json", "epoch.json", CHAIN, NEXT, OLD,
                         "retired.json", "retired-inbox.txt", "retired-debug.log",
                         "retired-debug-previous.log"}):
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
        raw_first = False
        if not root.exists():
            if (root.parent / NEXT).exists() or (root.parent / OLD).exists():
                raise CursorChainRefused("original_cursor_rollover_incomplete")
            return ChainTip(0, cursor, anchor, None, None, frozenset(), False)
        cycle = 0
        if (root / ANCHOR).exists() or (root / ANCHOR).is_symlink():
            checkpoint = self._checked_anchor(proof, epoch, epoch_raw,
                                              root / ANCHOR)
            cursor = Cursor(proof.generation, checkpoint["debug_device"],
                            checkpoint["debug_inode"], checkpoint["debug_offset"],
                            checkpoint["debug_prefix_sha256"])
            anchor = checkpoint["previous_ack_sha256"]
            raw_first = checkpoint["raw_first"]
            cycle = checkpoint["cycle"]
        slots = sorted(name for name in os.listdir(root) if name != ANCHOR)
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
            if ("intent.json" not in names or
                    names - {"intent.json", "destination", "ack.json",
                             "recovery.json"}):
                raise CursorChainRefused("incomplete_or_foreign_cursor_slot")
            intent, intent_raw = _load(folder / "intent.json", self.receipts.uid)
            expected_keys = {
                "schema", "kind", "generation", "sequence", "pending_name",
                "pending_device", "pending_inode", "pending_size", "pending_sha256",
                "debug_device", "debug_inode", "debug_start_offset",
                "debug_start_sha256", "debug_end_offset", "debug_end_sha256",
                "candidate_count", "evidence", "previous_ack_sha256", "ack_authorized",
            }
            if (set(intent) != expected_keys or intent.get("schema") != 2 or
                    intent.get("kind") != "cursor-chain-prepared" or
                    intent.get("generation") != proof.generation or
                    type(intent.get("sequence")) is not int or intent["sequence"] != index or
                    type(intent.get("pending_name")) is not str or
                    not PENDING.fullmatch(intent["pending_name"]) or
                    not intent["pending_name"].startswith(proof.generation + "-") or
                    intent["pending_name"] in used_pending_names or
                    (cycle > 0 and not intent["pending_name"].startswith(
                        proof.generation + "-" +
                        f"{cycle:08x}{index:06x}")) or
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
                    intent.get("evidence") not in ("native-debug", "raw-first") or
                    (raw_first and intent["evidence"] != "raw-first") or
                    (intent["evidence"] == "native-debug" and
                     intent["debug_end_offset"] <= cursor.offset) or
                    (intent["evidence"] == "raw-first" and
                     (intent["debug_end_offset"] != cursor.offset or
                      intent["debug_end_sha256"] != cursor.prefix_sha256)) or
                    intent.get("previous_ack_sha256") != anchor or
                    intent.get("ack_authorized") is not False):
                raise CursorChainRefused("cursor_chain_disagrees_with_previous_ack")
            used_pending_names.add(intent["pending_name"])
            # The original intent is validated against its predecessor
            # BEFORE resolving recovery. A durable original native-debug
            # mode must be explicitly anchored by recovery.json, never
            # rewritten or inferred from a changed pathname alone.
            intent = _resolved_intent(folder, intent, intent_raw,
                                      self.receipts.uid)
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
            raw_first = raw_first or intent["evidence"] == "raw-first"
            anchor = _digest(ack_raw)
        return ChainTip(len(slots), cursor, anchor, open_folder, open_intent,
                        frozenset(used_pending_names), raw_first, cycle)

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
                if (expected["pending_name"] != pending.name or
                        expected["pending_device"] != before.st_dev or
                        expected["pending_inode"] != before.st_ino or
                        expected["pending_size"] != len(raw) or
                        expected["pending_sha256"] != _digest(raw)):
                    raise CursorChainRefused("different_unacknowledged_cursor_pending")
                # A previously staged native-debug record may lose its
                # diagnostic inode before original Config commit. NEVER
                # rewrite its intent or use a partial destination plan.
                # Instead seal one separate immutable raw-first recovery
                # under this SAME held queue lock, original owner/P2b FD,
                # exact raw SHA and new protected diagnostic identity.
                if not _evidence_unchanged(proof, expected, self.receipts.uid,
                                           self.receipts.writer_gid):
                    # A fully sealed original destination checkpoint is
                    # already a durable commit witness. No new plan,
                    # destination write or raw-first receipt is permitted.
                    # Replaying the parent after a debug inode cut may
                    # resume only the exact original physical ACK.
                    completed = _checkpoint(
                        tip.open_folder, expected, self.receipts.uid)
                    if completed is not None:
                        if not _completed_debug_evidence_unchanged(
                                proof, expected, self.receipts.uid,
                                self.receipts.writer_gid) or attest() != proof:
                            raise CursorChainRefused(
                                "completed_debug_replacement_not_attested")
                        return tip.open_folder
                    if expected["evidence"] != "native-debug":
                        raise CursorChainRefused("different_unacknowledged_cursor_pending")
                    # The already sealed original destination plan contains
                    # all pre-write inode identities. Staging may read it,
                    # but only original Config/P1 under GUI lock can decide
                    # which exact physical writes may safely resume.
                    journal = tip.open_folder / "destination"
                    if journal.exists() or journal.is_symlink():
                        qualified_destination_plan(
                            tip.open_folder, expected, self.receipts.uid)
                        if not _completed_debug_evidence_unchanged(
                                proof, expected, self.receipts.uid,
                                self.receipts.writer_gid) or attest() != proof:
                            raise CursorChainRefused(
                                "partial_debug_replacement_not_attested")
                        return tip.open_folder
                    current, debug_bytes = _read_exact(
                        Path(proof.debug_path), owner_uid=self.receipts.uid,
                        writer_gid=self.receipts.writer_gid)
                    if ((current.st_dev, current.st_ino) ==
                            (expected["debug_device"], expected["debug_inode"]) or
                            tip.open_folder is None or
                            (tip.open_folder / "destination").exists() or
                            (tip.open_folder / "destination").is_symlink() or
                            (tip.open_folder / "recovery.json").exists() or
                            (tip.open_folder / "recovery.json").is_symlink()):
                        raise CursorChainRefused("original_native_debug_recovery_unsafe")
                    if (len(_raw_hosts(raw)) != expected["candidate_count"] or
                            inspect(pending, before.st_dev, before.st_ino,
                                    owner=proof.owner,
                                    writer_gid=self.queue.writer_gid)
                            is not FDState.DRAINED or
                            detached_original_raw(self.queue, pending) != raw or
                            attest() != proof):
                        raise CursorChainRefused("original_native_debug_recovery_source_changed")
                    original, original_raw = _load(
                        tip.open_folder / "intent.json", self.receipts.uid)
                    if original != expected:
                        raise CursorChainRefused("original_intent_changed_during_recovery")
                    recovery = {
                        "schema": 2,
                        "kind": "original-native-debug-raw-first-recovery",
                        "generation": proof.generation,
                        "sequence": original["sequence"],
                        "pending_name": pending.name,
                        "pending_sha256": _digest(raw),
                        "previous_ack_sha256": original["previous_ack_sha256"],
                        "original_intent_sha256": _digest(original_raw),
                        "new_debug_device": current.st_dev,
                        "new_debug_inode": current.st_ino,
                        "new_debug_size": len(debug_bytes),
                        "new_debug_sha256": _digest(debug_bytes),
                        "ack_authorized": False,
                    }
                    _write_once(tip.open_folder, "recovery.json",
                                _canonical(recovery), self.receipts.uid)
                    tip = self.tip(proof)
                    expected = tip.open_intent
                    if (expected is None or expected["evidence"] != "raw-first" or
                            expected["pending_name"] != pending.name or
                            not _evidence_unchanged(proof, expected,
                                                    self.receipts.uid,
                                                    self.receipts.writer_gid)):
                        raise CursorChainRefused("original_recovery_not_durable")
                if attest() != proof:
                    raise CursorChainRefused("owner_changed_during_intent_replay")
                return tip.open_folder
            if pending.name in tip.used_pending_names:
                raise CursorChainRefused("completed_pending_name_reused")
            if (tip.cycle > 0 and not pending.name.startswith(
                    proof.generation + "-" +
                    f"{tip.cycle:08x}{tip.next_sequence:06x}")):
                raise CursorChainRefused("historical_pending_cycle_reused")
            current_debug, _ = _read_exact(
                Path(proof.debug_path), owner_uid=self.receipts.uid,
                writer_gid=self.queue.writer_gid)
            # A native debug positive precedes its raw append. The original
            # P2a pending raw inode is discovery truth independently of it.
            # One debug replacement selects raw-first for the remainder
            # of this authenticated generation (no false cursor reset).
            raw_first = (tip.raw_first or
                         (current_debug.st_dev, current_debug.st_ino) !=
                         (tip.cursor.device, tip.cursor.inode))
            if raw_first:
                candidates = _raw_hosts(raw)
                next_cursor = tip.cursor
                evidence = "raw-first"
            else:
                window = propose_window(proof, tip.cursor, raw,
                                        owner_uid=self.receipts.uid,
                                        writer_gid=self.queue.writer_gid)
                candidates = window.candidates
                next_cursor = window.proposed_cursor
                evidence = "native-debug"
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
                "debug_end_offset": next_cursor.offset,
                "debug_end_sha256": next_cursor.prefix_sha256,
                "candidate_count": len(candidates),
                "evidence": evidence,
                "previous_ack_sha256": tip.previous_ack_sha256,
                "ack_authorized": False,
            }
            # Reverify owner/inode right before creating one persistent step.
            if (attest() != proof or
                    inspect(pending, before.st_dev, before.st_ino,
                            owner=proof.owner,
                            writer_gid=self.queue.writer_gid) is not FDState.DRAINED or
                    detached_original_raw(self.queue, pending) != raw or
                    not _evidence_unchanged(proof, intent, self.receipts.uid,
                                            self.receipts.writer_gid)):
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
            if not _evidence_unchanged(proof, intent, self.receipts.uid,
                                       self.receipts.writer_gid):
                # Never start/restart destination effects after a debug cut.
                # Only a pre-existing fully durable original checkpoint
                # permits an idempotent read-only return by _locked_commit.
                completed = _checkpoint(
                    folder, intent, self.receipts.uid, targets=writer.targets)
                if completed is None:
                    # A qualified ORIGINAL plan may be partially applied.
                    # Source replay is never a permit to bypass current P1
                    # or the all-target preimage GUI lock checks below.
                    qualified_destination_plan(
                        folder, intent, self.receipts.uid,
                        targets=writer.targets)
                if not _completed_debug_evidence_unchanged(
                        proof, intent, self.receipts.uid,
                        self.receipts.writer_gid):
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
                previous, previous_raw = _load(
                    last / "intent.json", self.receipts.uid)
                previous = _resolved_intent(
                    last, previous, previous_raw, self.receipts.uid)
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
            if not _completed_debug_evidence_unchanged(
                    proof, intent, self.receipts.uid, self.receipts.writer_gid):
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
                        _completed_debug_evidence_unchanged(
                            proof, intent, self.receipts.uid,
                            self.receipts.writer_gid) and
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

    def prepare_learning_first_slot(
            self, proof, workspace: Path, *,
            attest, inspect=probe_pending_fd,
    ) -> dict:
        """Source-only original schema3 WAL seed: one immutable N-file slot.

        Store the FIRST authenticated N-native/debug input in the original
        generation's cursor-chain-v2/00000000, under the same existing P2a
        FD and original FD9 owner. It is deliberately NOT an ACK, a second
        queue or a destination writer. An interrupted or different source
        cannot overwrite the first durable intent. Subsequent cursor slots
        and destination commits require a separate qualified continuation.
        """
        from auto_detect_owner import LearningGenerationProof
        from auto_detect_original_v2_source import (
            attest_original_learning_drained_candidate_locked,
        )
        from auto_detect_epoch_receipts import _read
        if (not isinstance(proof, LearningGenerationProof) or
                not isinstance(workspace, Path) or not workspace.is_absolute() or
                workspace.name != proof.generation or not self.queue._held or
                not callable(attest) or not callable(inspect) or
                attest() != proof):
            raise CursorChainRefused("learning_first_slot_original_owner_required")
        try:
            self.queue._verify()
            if self.queue.segments():
                raise CursorChainRefused("learning_first_slot_existing_pending")
            candidate = attest_original_learning_drained_candidate_locked(
                self.queue, self.receipts, proof, workspace,
                attest=attest, inspect=inspect)
            folder, seed, _ = self.receipts._learning_pretraffic(
                proof, self.queue, workspace)
            epoch_raw = _read(folder / "epoch.json", self.receipts.uid)
            epoch = json.loads(epoch_raw)
            if (epoch.get("schema") != 3 or
                    epoch.get("generation") != proof.generation or
                    epoch.get("owner_pid") != proof.owner.pid or
                    epoch.get("owner_start") != proof.owner.started or
                    epoch.get("learning") != seed["learning"] or
                    not candidate["p2b_drained"] or
                    candidate["commit_authorized"] is not False or
                    candidate["ack_authorized"] is not False):
                raise CursorChainRefused("learning_first_slot_epoch_not_original")
            native = []
            for number, hostlist, path in proof.learning:
                after = candidate["native_cursors"][path]
                seeded = next(
                    (r for r in seed["learning"] if r["path"] == path),
                    None)
                if (seeded is None or
                        (seeded["native_number"], seeded["hostlist"]) !=
                        (number, hostlist) or
                        after.generation != proof.generation or
                        after.native_number != number or
                        after.hostlist != hostlist or after.path != path or
                        (after.device, after.inode) !=
                        (seeded["device"], seeded["inode"]) or
                        seeded["offset"] != 0 or
                        seeded["prefix_sha256"] != EMPTY_HASH or
                        after.offset < 0 or
                        not HEX64.fullmatch(after.prefix_sha256)):
                    raise CursorChainRefused("learning_first_slot_native_cursor_not_zero")
                native.append({
                    "native_number": number, "hostlist": hostlist,
                    "path": path, "device": after.device, "inode": after.inode,
                    "start_offset": 0, "start_sha256": EMPTY_HASH,
                    "end_offset": after.offset,
                    "end_sha256": after.prefix_sha256,
                })
            observations = candidate["observations"]
            if (not isinstance(observations, list) or not observations or
                    len(observations) > 128 or
                    any(not isinstance(row, dict) or
                        set(row) != {"hostname", "hostlist"} or
                        row["hostlist"] not in {name for _, name, _ in proof.learning}
                        for row in observations)):
                raise CursorChainRefused("learning_first_slot_unbounded_observations")
            record = {
                "schema": 3, "kind": "original-learning-cursor-prepared",
                "generation": proof.generation, "sequence": 0,
                "operation_id": proof.operation_id,
                "owner_candidate_sha256": proof.owner_candidate_sha256,
                "owner_pid": proof.owner.pid,
                "owner_start": proof.owner.started,
                "final_args_sha256": proof.final_args_sha256,
                "native_map_sha256": proof.native_map_sha256,
                "epoch_sha256": _digest(epoch_raw),
                "previous_ack_sha256": _digest(epoch_raw),
                "debug_device": seed["files"][1]["device"],
                "debug_inode": seed["files"][1]["inode"],
                "debug_start_offset": 0,
                "debug_start_sha256": EMPTY_HASH,
                "debug_end_offset": candidate["debug_end_offset"],
                "debug_end_sha256": candidate["debug_end_sha256"],
                "native": native, "observations": observations,
                "ack_authorized": False,
            }
            encoded = _canonical(record)  # bounded original receipt writer
            # Recheck the entire N-source window BEFORE creating even an
            # empty durable slot. A native append racing this cut must
            # never strand a new root-private uncommitted intent directory.
            second = attest_original_learning_drained_candidate_locked(
                self.queue, self.receipts, proof, workspace,
                attest=attest, inspect=inspect)
            if second != candidate or attest() != proof:
                raise CursorChainRefused("learning_first_slot_changed_during_prepare")
            root = folder / CHAIN
            if root.exists() or root.is_symlink():
                _directory(root, self.receipts.uid)
                if set(os.listdir(root)) != {"00000000"}:
                    raise CursorChainRefused("learning_first_slot_foreign_chain_state")
                slot = root / "00000000"
                _directory(slot, self.receipts.uid)
                names = set(os.listdir(slot))
                if names not in (set(), {"intent.json"},
                                 {"intent.json", "destination"}):
                    raise CursorChainRefused("learning_first_slot_foreign_artifacts")
                if "intent.json" in names and (
                        _read(slot / "intent.json", self.receipts.uid) != encoded):
                    raise CursorChainRefused("learning_first_slot_prior_source_conflict")
                if "destination" in names:
                    journal = slot / "destination"
                    _directory(journal, self.receipts.uid)
                    files = set(os.listdir(journal))
                    if (not files.issubset({"plan.json", "checkpoint.json"}) or
                            "checkpoint.json" in files and
                            "plan.json" not in files):
                        raise CursorChainRefused("learning_first_slot_foreign_plan")
                    # The original Config/P1 owner, not the source reader,
                    # validates the full existing plan and checkpoint.
            else:
                # This is the ORIGINAL generation cursor-chain location,
                # not an independent WAL, SQLite or second queue.
                if attest() != proof:
                    raise CursorChainRefused("learning_first_slot_owner_changed_before_seed")
                root.mkdir(mode=0o700)
                _sync(folder)
                slot = root / "00000000"
                slot.mkdir(mode=0o700)
                _sync(root)
            # A crash after mkdir but before hardlinking the intent leaves
            # an exact *empty* slot; no previous durable source exists.
            # It may seal this same fully re-attested first candidate.
            _write_once(slot, "intent.json", encoded, self.receipts.uid)
            if _read(slot / "intent.json", self.receipts.uid) != encoded:
                raise CursorChainRefused("learning_first_slot_not_durable")
            return {
                "slot": slot, "intent_sha256": _digest(encoded),
                "generation": proof.generation, "sequence": 0,
                "commit_authorized": False, "cleanup_authorized": False,
                "ack_authorized": False,
            }
        except CursorChainRefused:
            raise
        except (ReceiptRefused, QueueSafetyError, DebugWindowRefused,
                DestinationRefused, GenerationRefused, OSError, ValueError,
                TypeError, KeyError, AttributeError, RuntimeError) as exc:
            raise CursorChainRefused("original_learning_first_slot_refused") from exc
