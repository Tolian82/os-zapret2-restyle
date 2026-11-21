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
            if slot.name == "anchor-native":
                self._erase_learning_records(slot)
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
                elif entry.name in {"native", "progress"}:
                    self._erase_learning_records(entry)
                elif re.fullmatch(r"(?:rebind|delete)-[0-9]{3}\.json", entry.name):
                    self._check_old_file(entry)
                    entry.unlink()
                else:
                    raise CursorChainRefused("foreign_old_cursor_artifact")
            slot.rmdir()
        _sync(path)
        path.rmdir()
        _sync(path.parent)

    def _erase_learning_records(self, path):
        _directory(path, self.receipts.uid)
        for child in path.iterdir():
            if not re.fullmatch(r"[0-9]{3}\.json", child.name):
                raise CursorChainRefused("foreign_old_learning_record")
            self._check_old_file(child)
            child.unlink()
        path.rmdir()

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
                        attest: Callable = attest_running_generation,
                        workspace: Path | None = None) -> None:
        """Crash-recover the same owner chain, then bound 512 fully ACKed slots.

        Original queue FD and running generation stay unchanged. First
        fsync the successor's immutable epoch-bound ACK anchor, then rename
        the old tree away, rename the successor into place, and only then
        unlink old ACKed receipts. Each interrupted rename is recoverable.
        """
        from auto_detect_owner import LearningGenerationProof
        if isinstance(proof, LearningGenerationProof):
            return self._ensure_learning_capacity(proof, workspace, attest=attest)
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
            # A prior WRITE-ONCE intent wins even if dvtws2 has added
            # more rows in the meantime. Original FD9/P2b must prove
            # the exact stored native+debug PREFIX, never recreate intent
            # from a newly grown producer tail. Future rows stay live and
            # retained for the next cursor slot, not this transaction.
            existing_root = (self.receipts.root / proof.generation / CHAIN)
            if existing_root.exists() or existing_root.is_symlink():
                _directory(existing_root, self.receipts.uid)
                if set(os.listdir(existing_root)) != {"00000000"}:
                    raise CursorChainRefused("learning_first_slot_foreign_chain_state")
                existing_slot = existing_root / "00000000"
                _directory(existing_slot, self.receipts.uid)
                entries = set(os.listdir(existing_slot))
                if "intent.json" in entries:
                    if not entries.issubset(
                            {"intent.json", "destination", "native-rebind"}):
                        # The separate native-rebind subfolder is part of
                        # this SAME original first-slot cursor journal, not
                        # a new queue or independent writer. Its manifest
                        # is validated by the original Config/FD9 model.
                        raise CursorChainRefused("learning_first_slot_foreign_artifacts")
                    # Once ANY post-rename physical inode seed exists,
                    # the original first-slot epoch cannot be replayed
                    # even if its old live filename later reappears.
                    # Only a future original FORWARD cursor / retained
                    # P2b+ACK transition may consume those suffixes.
                    # An empty interrupted observed/ directory also
                    # refuses: no implicit downgrade to first-slot replay.
                    if "native-rebind" in entries:
                        rebind = existing_slot / "native-rebind"
                        _directory(rebind, self.receipts.uid)
                        observed = rebind / "observed"
                        if observed.exists() or observed.is_symlink():
                            _directory(observed, self.receipts.uid)
                            raise CursorChainRefused(
                                "learning_first_slot_post_inode_seed_requires_forward_cursor")
                    source_raw = _read(existing_slot / "intent.json",
                                       self.receipts.uid)
                    source = json.loads(source_raw)
                    from auto_detect_original_v2_source import (
                        attest_original_learning_sealed_prefix_locked,
                    )
                    prefix = attest_original_learning_sealed_prefix_locked(
                        self.queue, self.receipts, proof, workspace, source,
                        attest=attest, inspect=inspect)
                    if (prefix["source_intent_sha256"] != _digest(source_raw)
                            or not prefix["p2b_drained"] or
                            prefix["commit_authorized"] is not False or
                            prefix["ack_authorized"] is not False):
                        raise CursorChainRefused("learning_first_slot_prefix_not_original")
                    return {
                        "slot": existing_slot,
                        "intent_sha256": _digest(source_raw),
                        "generation": proof.generation, "sequence": 0,
                        "commit_authorized": False,
                        "cleanup_authorized": False,
                        "ack_authorized": False,
                    }
                if entries:
                    raise CursorChainRefused("learning_first_slot_incomplete_prior")
                # Empty slot is a recoverable interrupted original mkdir.
                # It still requires the FULL new P2b/source cut below.
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

    # Schema3 uses these same source/destination/ACK folders from the very
    # first physical event. The historic three-slot fixtures are not a
    # prerequisite for an ordinary, independent N-inbox minute.
    def learning_epoch(self, proof, workspace):
        from auto_detect_owner import LearningGenerationProof
        if (not isinstance(proof, LearningGenerationProof) or not self.queue._held):
            raise CursorChainRefused("learning_cycle_original_queue_required")
        folder, seed, seed_raw = self.receipts._learning_pretraffic(
            proof, self.queue, workspace)
        epoch, encoded = _load(folder / "epoch.json", self.receipts.uid)
        if (encoded != _canonical(epoch) or epoch.get("schema") != 3 or
                epoch.get("kind") != "original-native-learning-epoch" or
                epoch.get("generation") != proof.generation or
                epoch.get("operation_id") != proof.operation_id or
                epoch.get("owner_pid") != proof.owner.pid or
                epoch.get("owner_start") != proof.owner.started or
                epoch.get("owner_candidate_sha256") != proof.owner_candidate_sha256 or
                epoch.get("native_map_sha256") != proof.native_map_sha256 or
                epoch.get("final_args_sha256") != proof.final_args_sha256 or
                epoch.get("pretraffic_sha256") != _digest(seed_raw) or
                epoch.get("learning") != seed["learning"] or
                epoch.get("files") != seed["files"] or
                epoch.get("ack_authorized") is not False):
            raise CursorChainRefused("learning_cycle_original_epoch_changed")
        return folder, seed, encoded

    def learning_tip(self, proof, workspace):
        folder, seed, epoch_raw = self.learning_epoch(proof, workspace)
        root = folder / CHAIN
        state = {}
        for n, label, path in proof.learning:
            zero = next(row for row in seed["learning"] if row["native_number"] == n)
            state[n] = dict(native_number=n, hostlist=label, path=path, streams=[dict(
                path=path, device=zero["device"], inode=zero["inode"],
                offset=0, prefix_sha256=EMPTY_HASH)])
        debug = dict(path=str(self.queue.root / "debug.log"),
                     device=seed["files"][1]["device"],
                     inode=seed["files"][1]["inode"], offset=0,
                     prefix_sha256=EMPTY_HASH)
        result = dict(root=root, sequence=0, cycle=0, state=state, debug=debug,
                      previous_ack_sha256=_digest(epoch_raw), slot=None,
                      intent=None, epoch_sha256=_digest(epoch_raw))
        if not root.exists() and not root.is_symlink():
            return result
        _directory(root, self.receipts.uid)
        entries = set(os.listdir(root))
        if ANCHOR in entries:
            anchor, state = _learning_checked_anchor(root, proof, epoch_raw, self.receipts.uid)
            result.update(cycle=anchor["cycle"], state=state, debug=anchor["debug"],
                          previous_ack_sha256=anchor["previous_ack_sha256"])
            entries -= {ANCHOR, "anchor-native"}
        if entries - {name for name in entries if STEP.fullmatch(name)}:
            raise CursorChainRefused("learning_cycle_foreign_chain_entry")
        for sequence, name in enumerate(sorted(entries)):
            if name != f"{sequence:08d}" or sequence >= MAX_STEPS:
                raise CursorChainRefused("learning_cycle_noncontiguous_chain")
            slot = root / name
            _directory(slot, self.receipts.uid)
            if not (slot / "intent.json").exists():
                if set(os.listdir(slot)) not in (set(), {"native"}):
                    raise CursorChainRefused("learning_cycle_unsealed_source_has_effects")
                # Before the aggregate intent exists no destination/native
                # mutation is permitted. Reclaim only that incomplete
                # private metadata, then freeze a new physical snapshot.
                staged = slot / "native"
                if staged.exists():
                    _directory(staged, self.receipts.uid)
                    for child in staged.iterdir():
                        if not re.fullmatch(r"[0-9]{3}\.json", child.name):
                            raise CursorChainRefused("learning_cycle_foreign_unsealed_N")
                        _read(child, self.receipts.uid)
                        child.unlink()
                    staged.rmdir()
                    _sync(slot)
                result.update(sequence=sequence, slot=slot)
                if name != max(entries):
                    raise CursorChainRefused("learning_cycle_gap_before_successor")
                return result
            intent, raw = _load(slot / "intent.json", self.receipts.uid)
            source = learning_cycle_source_fields(slot, intent, self.receipts.uid)
            native = _learning_native_records(slot / "native", intent,
                                               self.receipts.uid)
            if (intent["sequence"] != sequence or intent["cycle"] != result["cycle"] or
                    intent["epoch_sha256"] != result["epoch_sha256"] or
                    intent["previous_ack_sha256"] != result["previous_ack_sha256"] or
                    intent["debug"]["start"] != result["debug"] or
                    {n: _learning_start(row) for n, row in native.items()} != result["state"]):
                raise CursorChainRefused("learning_cycle_cursor_predecessor_changed")
            ack_file = slot / "ack.json"
            if not ack_file.exists() and not ack_file.is_symlink():
                if name != max(entries):
                    raise CursorChainRefused("learning_cycle_successor_before_ack")
                result.update(sequence=sequence, slot=slot, intent=intent)
                return result
            ack, ack_raw = _load(ack_file, self.receipts.uid)
            cp, cp_raw = learning_cycle_checkpoint(slot, intent, self.receipts.uid)
            progress = _learning_native_records(slot / "progress", intent,
                                                 self.receipts.uid, progress=True)
            expected = dict(schema=3, kind="original-learning-cursor-acked",
                            generation=proof.generation, sequence=sequence,
                            cycle=result["cycle"], source_intent_sha256=_digest(raw),
                            checkpoint_sha256=_digest(cp_raw),
                            previous_ack_sha256=result["previous_ack_sha256"],
                            native_sha256=_learning_records_digest(progress),
                            debug=intent["debug"]["end"], ack_authorized=False)
            if ack != expected or ack_raw != _canonical(ack):
                raise CursorChainRefused("learning_cycle_ack_not_original_checkpoint")
            result.update(sequence=sequence + 1, state=progress,
                          debug=ack["debug"], previous_ack_sha256=_digest(ack_raw),
                          slot=None, intent=None)
        return result

    def learning_debug_highwater_candidate(self, proof, workspace, *,
                                           attest, inspect=probe_pending_fd):
        """Read-only original FD9/P2a proof before a future schema3 debug cut.

        This does NOT replace, truncate, retire, or authorize replacing the
        debug inode. A physical cut must durably journal its *separate* old
        and new cursors before os.replace; reusing the schema2 raw-first
        path would lose native profile attribution. No extra worker exists.
        """
        from auto_detect_original_v2_model import _native_rebind_stable_snapshot
        from auto_detect_owner import LearningGenerationProof
        if (not isinstance(proof, LearningGenerationProof) or
                not self.queue._held or not callable(attest) or
                not callable(inspect) or attest() != proof):
            raise CursorChainRefused("learning_debug_cut_original_owner_required")
        self.queue._verify()
        tip = self.learning_tip(proof, workspace)
        if tip["slot"] is not None or tip["intent"] is not None:
            # An unfinished original destination WAL always takes priority.
            return None
        if tip["sequence"] == 0:
            # A zero-cut epoch alone is not proof of a durable postlaunch
            # source ACK; require an immutable completed original slot.
            return None
        expected_pending = {Path(cursor["path"])
                            for row in tip["state"].values()
                            for cursor in row["streams"]
                            if Path(cursor["path"]).parent == self.queue.pending}
        if set(self.queue.segments()) != expected_pending:
            raise CursorChainRefused("learning_debug_cut_foreign_pending")
        debug_cursor = tip["debug"]
        debug_path = Path(debug_cursor["path"])
        if debug_path != self.queue.root / "debug.log":
            raise CursorChainRefused("learning_debug_cut_foreign_debug_path")
        snapshots = {}
        # Native appenders ignore the original P2a flock. Independently
        # verify the exact same full images twice, including P2b all-PID
        # FD drainage and running original owner before AND after.
        for _ in range(2):
            current = {}
            cursors = [debug_cursor]
            cursors.extend(cursor for row in tip["state"].values()
                           for cursor in row["streams"])
            for cursor in cursors:
                path = Path(cursor["path"])
                st, data, identity = _native_rebind_stable_snapshot(
                    path, self.receipts.uid, self.queue.writer_gid,
                    allowed_links=(1,))
                _learning_prefix(cursor, st, data)
                if cursor["offset"] != len(data):
                    # A partial debug line or unmatched native append can
                    # never be suppressed merely to bound diagnostic size.
                    return None
                if inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                           writer_gid=self.queue.writer_gid) is not FDState.DRAINED:
                    raise CursorChainRefused("learning_debug_cut_native_fd_busy")
                current[str(path)] = (identity, _digest(data), len(data))
            if snapshots and snapshots != current:
                raise CursorChainRefused("learning_debug_cut_snapshot_raced")
            snapshots = current
            if attest() != proof:
                raise CursorChainRefused("learning_debug_cut_owner_raced")
        if snapshots[str(debug_path)][2] < MAX_DEBUG // 2:
            return None
        if self.learning_tip(proof, workspace) != tip or attest() != proof:
            raise CursorChainRefused("learning_debug_cut_anchor_changed")
        return {
            "schema": 3,
            "kind": "original-learning-debug-highwater-candidate",
            "generation": proof.generation,
            "native_map_sha256": proof.native_map_sha256,
            "final_args_sha256": proof.final_args_sha256,
            "cycle": tip["cycle"],
            "next_sequence": tip["sequence"],
            "previous_ack_sha256": tip["previous_ack_sha256"],
            "debug": debug_cursor,
            "debug_image_sha256": snapshots[str(debug_path)][1],
            "native_sha256": _learning_records_digest(tip["state"]),
            "source_fully_acked": True,
            "p2b_drained": True,
            "cut_authorized": False,
            "ack_authorized": False,
        }

    def _ensure_learning_capacity(self, proof, workspace, *, attest):
        """The original .next/.old anchor swap, carrying ALL N cursors.

        No pending inode, unread tail, destination or producer is removed.
        Only fully ACKed receipt history is reclaimed after the successor
        state has been fsynced and installed atomically.
        """
        from auto_detect_original_v2_model import _native_rebind_stable_snapshot
        if not self.queue._held or not callable(attest) or attest() != proof:
            raise CursorChainRefused("learning_rollover_original_owner_required")
        folder, seed, epoch_raw = self.learning_epoch(proof, workspace)
        root, prepared, retired = folder / CHAIN, folder / NEXT, folder / OLD
        if retired.exists() or retired.is_symlink():
            _directory(retired, self.receipts.uid)
            if not root.exists() and not root.is_symlink():
                retired.rename(root)
                _sync(folder)
            elif prepared.exists() or prepared.is_symlink():
                raise CursorChainRefused("learning_rollover_ambiguous_paths")
            else:
                _learning_checked_anchor(root, proof, epoch_raw, self.receipts.uid)
                self._erase_old_tree(retired)
        tip = self.learning_tip(proof, workspace)
        if tip["sequence"] < MAX_STEPS:
            if prepared.exists() or prepared.is_symlink():
                raise CursorChainRefused("learning_rollover_without_terminal_chain")
            return
        if tip["slot"] is not None or tip["intent"] is not None or tip["cycle"] >= (1 << 32) - 1:
            raise CursorChainRefused("learning_rollover_chain_not_terminal")
        expected_pending = {Path(s["path"]) for row in tip["state"].values()
                            for s in row["streams"] if Path(s["path"]).parent == self.queue.pending}
        if set(self.queue.segments()) != expected_pending:
            raise CursorChainRefused("learning_rollover_foreign_pending")
        expected = dict(schema=3, kind="original-learning-cursor-anchor",
                        generation=proof.generation, epoch_sha256=_digest(epoch_raw),
                        native_map_sha256=proof.native_map_sha256,
                        final_args_sha256=proof.final_args_sha256,
                        cycle=tip["cycle"] + 1,
                        previous_ack_sha256=tip["previous_ack_sha256"],
                        native_numbers=list(tip["state"]),
                        native_sha256=_learning_records_digest(tip["state"]),
                        debug=tip["debug"], ack_authorized=False)
        for cursor in [tip["debug"], *(s for row in tip["state"].values() for s in row["streams"])]:
            st, data, _ = _native_rebind_stable_snapshot(
                Path(cursor["path"]), self.receipts.uid, self.queue.writer_gid,
                allowed_links=(1,))
            _learning_prefix(cursor, st, data)
        if not prepared.exists():
            prepared.mkdir(mode=0o700)
            _sync(folder)
        _directory(prepared, self.receipts.uid)
        if set(os.listdir(prepared)) - {ANCHOR, "anchor-native"}:
            raise CursorChainRefused("learning_rollover_foreign_stage")
        records = prepared / "anchor-native"
        if not records.exists():
            records.mkdir(mode=0o700)
            _sync(prepared)
        for n, row in tip["state"].items():
            _write_once(records, f"{n:03d}.json", _canonical(row), self.receipts.uid)
        _write_once(prepared, ANCHOR, _canonical(expected), self.receipts.uid)
        proposed, state = _learning_checked_anchor(prepared, proof, epoch_raw, self.receipts.uid)
        if proposed != expected or state != tip["state"] or attest() != proof or self.learning_tip(proof, workspace) != tip:
            raise CursorChainRefused("learning_rollover_state_changed_before_swap")
        root.rename(retired)
        _sync(folder)
        prepared.rename(root)
        _sync(folder)
        self._erase_old_tree(retired)
        if attest() != proof or self.learning_tip(proof, workspace)["cycle"] != expected["cycle"]:
            raise CursorChainRefused("learning_rollover_successor_not_published")

    def prepare_learning_cycle(self, proof, workspace, *, attest,
                               inspect=probe_pending_fd):
        from auto_detect_original_v2_model import _native_rebind_stable_snapshot
        from auto_detect_debug_window import ADD, MAX_WINDOW, _hostname
        if not callable(attest) or attest() != proof or not callable(inspect):
            raise CursorChainRefused("learning_cycle_owner_required")
        self.queue._verify()
        tip = self.learning_tip(proof, workspace)
        if tip["sequence"] >= MAX_STEPS:
            raise CursorChainRefused("learning_cycle_capacity_requires_rollover")
        slot = tip["slot"] or tip["root"] / f'{tip["sequence"]:08d}'
        if tip["intent"] is not None:
            intent = tip["intent"]
            # After the original durable checkpoint, replay is ACK-only.
            # Cleaned native source paths need never be reopened for P1.
            if (slot / "destination" / "checkpoint.json").exists():
                learning_cycle_checkpoint(slot, intent, self.receipts.uid)
            else:
                self.attest_learning_cycle_prefix(proof, workspace, slot, intent,
                                                   attest=attest, inspect=inspect)
            return _learning_prepared(slot, intent)
        state = tip["state"]
        pending = {Path(s["path"]) for row in state.values()
                   for s in row["streams"] if Path(s["path"]).parent == self.queue.pending}
        if set(self.queue.segments()) != pending:
            raise CursorChainRefused("learning_cycle_unattributed_pending")
        snapshots = {}
        source_bytes = 0
        for row in state.values():
            for cursor in row["streams"]:
                path = Path(cursor["path"])
                st, data, ident = _native_rebind_stable_snapshot(
                    path, self.receipts.uid, self.queue.writer_gid, allowed_links=(1,))
                _learning_prefix(cursor, st, data)
                if inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                           writer_gid=self.queue.writer_gid) is not FDState.DRAINED:
                    raise CursorChainRefused("learning_cycle_native_busy")
                snapshots[str(path)] = (st, data, ident)
                source_bytes += len(data)
                if source_bytes > 4 * 1024 * 1024:
                    raise CursorChainRefused("learning_cycle_combined_native_limit")
        dc = tip["debug"]
        debug_st, debug_data, debug_ident = _native_rebind_stable_snapshot(
            Path(dc["path"]), self.receipts.uid, self.queue.writer_gid,
            allowed_links=(1,))
        _learning_prefix(dc, debug_st, debug_data)
        if source_bytes + len(debug_data) > 4 * 1024 * 1024:
            raise CursorChainRefused("learning_cycle_combined_debug_limit")
        if inspect(Path(dc["path"]), debug_st.st_dev, debug_st.st_ino,
                   owner=proof.owner, writer_gid=self.queue.writer_gid) is not FDState.DRAINED:
            raise CursorChainRefused("learning_cycle_debug_busy")
        positions = {path: cursor["offset"] for row in state.values()
                     for cursor in row["streams"] for path in [cursor["path"]]}
        by_path = {row["path"]: row for row in state.values()}
        observations = []
        end = dc["offset"]
        # A long-running dvtws2 can emit >2 MiB of *diagnostic-only* rows
        # without a single native hostlist append. Advancing that complete
        # non-positive suffix through the SAME original Config/P1 WAL and
        # physical ACK need not consume eight 256-KiB minute slots. This is
        # NOT a debug rotation, truncation, or inferred native attribution.
        # Only full ASCII lines with no native-positive marker qualify.
        # The original bounded stable snapshot and below source re-attest
        # still protect every byte; a trailing partial line remains unread.
        tail = debug_data[end:]
        complete_end = tail.rfind(b"\n") + 1
        diagnostic = tail[:complete_end]
        if diagnostic and b" : adding to " not in diagnostic:
            try:
                diagnostic.decode("ascii")
            except UnicodeDecodeError as exc:
                raise CursorChainRefused("learning_cycle_nonascii_diagnostic") from exc
            end += complete_end
        else:
            # An actual native positive (including malformed/unmatched
            # rows) keeps the existing exact ordered 256-KiB/N limit.
            for line in tail.splitlines(keepends=True):
                if not line.endswith(b"\n") or end + len(line) - dc["offset"] > MAX_WINDOW:
                    break
                try:
                    decoded = line[:-1].decode("ascii")
                except UnicodeDecodeError as exc:
                    raise CursorChainRefused("learning_cycle_nonascii_debug") from exc
                if " : adding to " in decoded:
                    event = ADD.fullmatch(decoded)
                    if (event is None or event["path"] not in by_path or
                            not _hostname(event["host"])):
                        raise CursorChainRefused("learning_cycle_foreign_positive")
                    row = by_path[event["path"]]
                    if int(event["profile"]) != row["native_number"]:
                        raise CursorChainRefused("learning_cycle_wrong_native_N")
                    encoded = (event["host"] + "\n").encode("ascii")
                    match = next((s for s in reversed(row["streams"])
                                  if snapshots[s["path"]][1][positions[s["path"]]:].startswith(encoded)), None)
                    if match is None:
                        # Native debug precedes append_to_list_file. Keep this
                        # line AND every unmatched raw byte for the next minute.
                        break
                    positions[match["path"]] += len(encoded)
                    observations.append(dict(hostname=event["host"], hostlist=row["hostlist"]))
                end += len(line)
                if len(observations) == 32:
                    break
        if end == dc["offset"]:
            return None
        native = {}
        for n, row in state.items():
            streams = []
            for cursor in row["streams"]:
                path = cursor["path"]
                st, data, ident = snapshots[path]
                streams.append(dict(start=cursor, end=dict(
                    path=path, device=st.st_dev, inode=st.st_ino,
                    offset=positions[path], prefix_sha256=_digest(data[:positions[path]])),
                    snapshot_size=len(data), snapshot_sha256=_digest(data)))
            native[n] = {**row, "streams": streams}
        intent = dict(schema=3, kind="original-learning-cycle-prepared",
                      generation=proof.generation, sequence=tip["sequence"],
                      cycle=tip["cycle"], operation_id=proof.operation_id,
                      owner_candidate_sha256=proof.owner_candidate_sha256,
                      owner_pid=proof.owner.pid, owner_start=proof.owner.started,
                      final_args_sha256=proof.final_args_sha256,
                      native_map_sha256=proof.native_map_sha256,
                      epoch_sha256=tip["epoch_sha256"],
                      previous_ack_sha256=tip["previous_ack_sha256"],
                      native_numbers=list(native),
                      native_sha256=_learning_records_digest(native),
                      debug=dict(start=dc, end=dict(path=dc["path"],
                          device=debug_st.st_dev, inode=debug_st.st_ino,
                          offset=end, prefix_sha256=_digest(debug_data[:end]))),
                      observations=observations, ack_authorized=False)
        for path, (st, data, ident) in snapshots.items():
            again = _native_rebind_stable_snapshot(Path(path), self.receipts.uid,
                self.queue.writer_gid, allowed_links=(1,))
            if again[1:] != (data, ident):
                raise CursorChainRefused("learning_cycle_snapshot_raced")
        if (_native_rebind_stable_snapshot(Path(dc["path"]), self.receipts.uid,
                self.queue.writer_gid, allowed_links=(1,))[1:] != (debug_data, debug_ident)
                or attest() != proof):
            raise CursorChainRefused("learning_cycle_debug_owner_raced")
        if not tip["root"].exists():
            tip["root"].mkdir(mode=0o700)
            _sync(tip["root"].parent)
        if not slot.exists():
            slot.mkdir(mode=0o700)
            _sync(tip["root"])
        native_dir = slot / "native"
        if not native_dir.exists():
            native_dir.mkdir(mode=0o700)
            _sync(slot)
        _directory(native_dir, self.receipts.uid)
        for n, row in native.items():
            _write_once(native_dir, f"{n:03d}.json", _canonical(row), self.receipts.uid)
        _write_once(slot, "intent.json", _canonical(intent), self.receipts.uid)
        self.attest_learning_cycle_prefix(proof, workspace, slot, intent,
                                          attest=attest, inspect=inspect)
        return _learning_prepared(slot, intent)

    def attest_learning_cycle_prefix(self, proof, workspace, slot, intent, *,
                                      attest, inspect=probe_pending_fd):
        from auto_detect_original_v2_model import _native_rebind_stable_snapshot
        self.learning_epoch(proof, workspace)
        learning_cycle_source_fields(slot, intent, self.receipts.uid)
        native = _learning_native_records(slot / "native", intent, self.receipts.uid)
        expected = {n: (label, path) for n, label, path in proof.learning}
        if (set(native) != set(expected) or attest() != proof or
                intent["owner_pid"] != proof.owner.pid or
                intent["owner_start"] != proof.owner.started or
                intent["native_map_sha256"] != proof.native_map_sha256):
            raise CursorChainRefused("learning_cycle_sealed_owner_changed")
        for n, row in native.items():
            if (row["hostlist"], row["path"]) != expected[n]:
                raise CursorChainRefused("learning_cycle_sealed_native_map_changed")
        cursors = [s["end"] for row in native.values() for s in row["streams"]]
        cursors.append(intent["debug"]["end"])
        snapshots = {}
        for _ in range(2):
            for cursor in cursors:
                path = Path(cursor["path"])
                st, data, _ = _native_rebind_stable_snapshot(
                    path, self.receipts.uid, self.queue.writer_gid, allowed_links=(1,))
                _learning_prefix(cursor, st, data)
                snapshots[str(path)] = (st, data)
                if inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                           writer_gid=self.queue.writer_gid) is not FDState.DRAINED:
                    raise CursorChainRefused("learning_cycle_sealed_native_busy")
            if attest() != proof:
                raise CursorChainRefused("learning_cycle_sealed_owner_raced")
        # Prefix hashes alone cannot authorize a forged observation. Apply
        # the original exact ADD/N/path/native-row correlation again to the
        # immutable start/end cuts, independently of later producer appends.
        from auto_detect_debug_window import ADD, _raw_hosts
        remaining = {}
        by_path = {row["path"]: row for row in native.values()}
        for row in native.values():
            for stream in row["streams"]:
                start, end = stream["start"], stream["end"]
                st, data = snapshots[end["path"]]
                _learning_prefix(start, st, data)
                cut = data[start["offset"]:end["offset"]]
                remaining[end["path"]] = _raw_hosts(cut) if cut else []
        start, end = intent["debug"]["start"], intent["debug"]["end"]
        st, data = snapshots[end["path"]]
        _learning_prefix(start, st, data)
        observations = []
        for line in data[start["offset"]:end["offset"]].splitlines(keepends=True):
            if not line.endswith(b"\n"):
                raise CursorChainRefused("learning_cycle_sealed_incomplete_debug")
            decoded = line[:-1].decode("ascii")
            if " : adding to " not in decoded:
                continue
            event = ADD.fullmatch(decoded)
            row = by_path.get(event["path"]) if event else None
            if row is None or int(event["profile"]) != row["native_number"]:
                raise CursorChainRefused("learning_cycle_sealed_foreign_positive")
            matched = next((s for s in reversed(row["streams"])
                            if remaining[s["end"]["path"]] and
                            remaining[s["end"]["path"]][0] == event["host"]), None)
            if matched is None:
                raise CursorChainRefused("learning_cycle_sealed_positive_without_native")
            remaining[matched["end"]["path"]].pop(0)
            observations.append(dict(hostname=event["host"], hostlist=row["hostlist"]))
        if any(remaining.values()) or observations != intent["observations"]:
            raise CursorChainRefused("learning_cycle_sealed_observations_changed")
        return dict(source_intent_sha256=_digest(_canonical(intent)),
                    p2b_drained=True, commit_authorized=False, ack_authorized=False)


def _learning_prefix(cursor, st, data):
    if (type(cursor) is not dict or set(cursor) != {
            "path", "device", "inode", "offset", "prefix_sha256"} or
            type(cursor["offset"]) is not int or
            not 0 <= cursor["offset"] <= len(data) or
            (st.st_dev, st.st_ino) != (cursor["device"], cursor["inode"]) or
            _digest(data[:cursor["offset"]]) != cursor["prefix_sha256"]):
        raise CursorChainRefused("learning_cycle_prefix_changed")


def _learning_start(row):
    return {**row, "streams": [s["start"] for s in row["streams"]]}


def _learning_records_digest(rows):
    return _digest(b"".join(_canonical(rows[n]) for n in sorted(rows)))


def _learning_native_records(folder, intent, uid, *, progress=False):
    _directory(folder, uid)
    expected = {f"{n:03d}.json" for n in intent["native_numbers"]}
    if set(os.listdir(folder)) != expected:
        raise CursorChainRefused("learning_cycle_missing_or_foreign_N")
    result = {}
    for n in intent["native_numbers"]:
        row, raw = _load(folder / f"{n:03d}.json", uid)
        if (raw != _canonical(row) or row.get("native_number") != n or
                row.get("hostlist") not in {"youtube", "user"} or
                type(row.get("path")) is not str or
                not Path(row["path"]).is_absolute() or
                type(row.get("streams")) is not list or
                not 1 <= len(row["streams"]) <= 2):
            raise CursorChainRefused("learning_cycle_invalid_N_record")
        source_path = Path(row["path"])
        if source_path.name != f'learning-{intent["generation"]}-{n}.txt':
            raise CursorChainRefused("learning_cycle_foreign_generation_filename")
        cursors = row["streams"] if progress else [s["start"] for s in row["streams"]]
        if cursors[0]["path"] != row["path"]:
            raise CursorChainRefused("learning_cycle_live_cursor_path_changed")
        for index, cursor in enumerate(cursors):
            if (set(cursor) != {"path", "device", "inode", "offset", "prefix_sha256"} or
                    any(type(cursor[k]) is not int or cursor[k] < 0
                        for k in ("device", "inode", "offset")) or cursor["inode"] == 0 or
                    not HEX64.fullmatch(str(cursor["prefix_sha256"]))):
                raise CursorChainRefused("learning_cycle_invalid_physical_cursor")
            if index:
                from auto_detect_queue import NATIVE_PENDING
                path = Path(cursor["path"])
                match = NATIVE_PENDING.fullmatch(path.name)
                if (path.parent != source_path.parent / "pending" or match is None or
                        match[1] != intent["generation"] or int(match[2]) != n):
                    raise CursorChainRefused("learning_cycle_foreign_old_cursor")
            if not progress:
                end = row["streams"][index]["end"]
                if (set(end) != set(cursor) or
                        any(end[k] != cursor[k] for k in ("path", "device", "inode")) or
                        type(end["offset"]) is not int or end["offset"] < cursor["offset"] or
                        not HEX64.fullmatch(str(end["prefix_sha256"]))):
                    raise CursorChainRefused("learning_cycle_invalid_end_cursor")
        if (len(cursors) == 2) != ("retained_prefix" in row):
            raise CursorChainRefused("learning_cycle_old_without_retained_prefix")
        result[n] = row
    if not progress and _learning_records_digest(result) != intent["native_sha256"]:
        raise CursorChainRefused("learning_cycle_source_N_digest_changed")
    return result


def _learning_checked_anchor(root, proof, epoch_raw, uid):
    anchor, raw = _load(root / ANCHOR, uid)
    if (raw != _canonical(anchor) or set(anchor) != {
            "schema", "kind", "generation", "epoch_sha256", "native_map_sha256",
            "final_args_sha256", "cycle", "previous_ack_sha256", "native_numbers",
            "native_sha256", "debug", "ack_authorized"} or
            anchor["schema"] != 3 or anchor["kind"] != "original-learning-cursor-anchor" or
            anchor["generation"] != proof.generation or
            anchor["epoch_sha256"] != _digest(epoch_raw) or
            anchor["native_map_sha256"] != proof.native_map_sha256 or
            anchor["final_args_sha256"] != proof.final_args_sha256 or
            type(anchor["cycle"]) is not int or not 0 < anchor["cycle"] < (1 << 32) or
            anchor["native_numbers"] != [n for n, _, _ in proof.learning] or
            not HEX64.fullmatch(str(anchor["previous_ack_sha256"])) or
            anchor["ack_authorized"] is not False):
        raise CursorChainRefused("learning_rollover_anchor_not_original_epoch")
    state = _learning_native_records(root / "anchor-native", anchor, uid, progress=True)
    if _learning_records_digest(state) != anchor["native_sha256"]:
        raise CursorChainRefused("learning_rollover_anchor_N_state_changed")
    return anchor, state


def _learning_prepared(slot, intent):
    return dict(slot=slot, generation=intent["generation"], sequence=intent["sequence"],
                intent_sha256=_digest(_canonical(intent)),
                cursor_advanced=False, commit_authorized=False, ack_authorized=False)


def learning_cycle_source_fields(folder, intent, uid):
    """Original DestinationCommit source codec; never reads mutable inodes."""
    sequence = intent.get("sequence")
    if (intent.get("schema") != 3 or
            intent.get("kind") != "original-learning-cycle-prepared" or
            type(sequence) is not int or not 0 <= sequence < MAX_STEPS or
            folder.name != f"{sequence:08d}" or folder.parent.name != CHAIN or
            folder.parent.parent.name != intent.get("generation") or
            intent.get("ack_authorized") is not False or
            _read(folder / "intent.json", uid) != _canonical(intent) or
            type(intent.get("observations")) is not list or
            len(intent["observations"]) > 32 or
            type(intent.get("native_numbers")) is not list or
            not 1 <= len(intent["native_numbers"]) <= 255 or
            intent["native_numbers"] != sorted(set(intent["native_numbers"])) or
            any(type(n) is not int or not 1 <= n <= 255 for n in intent["native_numbers"])):
        raise CursorChainRefused("learning_cycle_wal_not_original_source")
    _learning_native_records(folder / "native", intent, uid)
    if sequence:
        prev, prev_raw = _load(folder.parent / f"{sequence - 1:08d}" / "ack.json", uid)
        if (_digest(prev_raw) != intent["previous_ack_sha256"] or
                prev.get("generation") != intent["generation"] or
                prev.get("sequence") != sequence - 1):
            raise CursorChainRefused("learning_cycle_wal_previous_ack_changed")
    elif intent["cycle"] == 0:
        epoch = _read(folder.parent.parent / "epoch.json", uid)
        if _digest(epoch) != intent["previous_ack_sha256"]:
            raise CursorChainRefused("learning_cycle_wal_zero_not_original_epoch")
    else:
        anchor, _ = _load(folder.parent / ANCHOR, uid)
        if (anchor.get("previous_ack_sha256") != intent["previous_ack_sha256"] or
                anchor.get("cycle") != intent["cycle"] or
                anchor.get("generation") != intent["generation"] or
                anchor.get("epoch_sha256") != intent["epoch_sha256"]):
            raise CursorChainRefused("learning_cycle_wal_zero_not_original_anchor")
    end = intent["debug"]["end"]
    return dict(schema=3, kind="durable-destination-plan",
                generation=intent["generation"], pending_name="learning-" + folder.name,
                pending_sha256=_digest(_canonical({"observations": intent["observations"]})),
                evidence="learning-native-debug", debug_end_offset=end["offset"],
                debug_end_sha256=end["prefix_sha256"],
                source_intent_sha256=_digest(_canonical(intent)))


def learning_cycle_checkpoint(slot, intent, uid, *, targets=None):
    plan, raw = qualified_destination_plan(slot, intent, uid, targets=targets)
    source = learning_cycle_source_fields(slot, intent, uid)
    cp, cp_raw = _load(slot / "destination" / "checkpoint.json", uid)
    expected = dict(schema=1, kind="destination-and-cursor-committed",
                    generation=intent["generation"], pending_name=source["pending_name"],
                    plan_sha256=_digest(raw), evidence=source["evidence"],
                    committed_cursor_offset=source["debug_end_offset"],
                    committed_cursor_sha256=source["debug_end_sha256"], ack_authorized=False)
    if cp != expected or cp_raw != _canonical(cp):
        raise CursorChainRefused("learning_cycle_checkpoint_not_original")
    return cp, cp_raw
