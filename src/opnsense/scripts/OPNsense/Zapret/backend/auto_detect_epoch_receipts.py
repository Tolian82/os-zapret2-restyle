#!/usr/bin/env python3
"""#1052 P2k2a: root-private immutable debug epoch and pending-intent receipts.

NOT a worker, not an authenticated FD9 caller and NOT commit/ack authority.
Only an original-FD9-attested GenerationProof may be supplied by a future
caller. The stored record is HISTORICAL PROVENANCE, not a fresh PID/FD proof.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from auto_detect_debug_window import (Cursor, Window, _hostname,
                                      empty_epoch, propose_window, DebugWindowRefused)
from auto_detect_owner import GenerationProof

ROOT = Path("/var/db/zapret2/auto-detect-epochs")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PENDING = re.compile(r"[0-9a-f]{32}-[0-9a-f]{32}\.txt\Z")
EMPTY_HASH = hashlib.sha256(b"").hexdigest()
MAX_EPOCHS = 128
MAX_RECORD = 16 * 1024
MAX_SEGMENT = 4 * 1024 * 1024


class ReceiptRefused(RuntimeError):
    """Never use a receipt to acknowledge a pending inode on uncertainty."""


@dataclass(frozen=True)
class HistoricalReceipt:
    """An archive of what the original trusted owner once attested.

    It is deliberately NOT GenerationProof and cannot attest a live process.
    """
    epoch: dict
    intent: dict | None


def _directory(path: Path, uid: int) -> None:
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or
            stat.S_IMODE(info.st_mode) != 0o700):
        raise ReceiptRefused("untrusted_root_private_directory")


def _sync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW |
                 getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read(path: Path, uid: int) -> bytes:
    try:
        a = path.lstat()
        if (not stat.S_ISREG(a.st_mode) or a.st_uid != uid or a.st_nlink != 1 or
                stat.S_IMODE(a.st_mode) != 0o600 or
                not 0 < a.st_size <= MAX_RECORD):
            raise ReceiptRefused("untrusted_receipt")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            b = os.fstat(fd)
            content = os.read(fd, MAX_RECORD + 1)
            c = os.fstat(fd)
        finally:
            os.close(fd)
        if ((a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns) !=
                (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns) or
                (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns) !=
                (c.st_dev, c.st_ino, c.st_size, c.st_mtime_ns) or
                len(content) != a.st_size):
            raise ReceiptRefused("changed_receipt_during_read")
        return content
    except OSError as exc:
        raise ReceiptRefused("protected_receipt_read_failed") from exc


def _canonical(data: dict) -> bytes:
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_RECORD:
        raise ReceiptRefused("receipt_too_large")
    return raw


def _write_once(folder: Path, name: str, raw: bytes, uid: int) -> None:
    """Create, fsync, hardlink into place, fsync directory. NEVER overwrite."""
    target = folder / name
    if target.exists() or target.is_symlink():
        if _read(target, uid) != raw:
            raise ReceiptRefused("conflicting_existing_receipt")
        return
    temp = folder / ("." + secrets.token_hex(16) + ".part")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise ReceiptRefused("receipt_short_write")
            remaining = remaining[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.link(temp, target, follow_symlinks=False)
        os.unlink(temp)
        _sync(folder)
    except FileExistsError as exc:
        # Refuse an independent writer, even if content happened to match.
        raise ReceiptRefused("concurrent_receipt_creation") from exc
    # A crash may leave a .part file or 2-link file; the next operation refuses.
    if _read(target, uid) != raw:
        raise ReceiptRefused("receipt_write_not_durable")


def _proof_fields(proof: GenerationProof) -> dict:
    if (not isinstance(proof, GenerationProof) or
            not HEX32.fullmatch(proof.operation_id) or
            proof.generation != proof.operation_id or
            not HEX64.fullmatch(proof.final_args_sha256) or
            proof.owner.pid <= 1 or
            not proof.owner.started or not proof.owner.executable or
            not Path(proof.raw_path).is_absolute() or
            not Path(proof.debug_path).is_absolute() or
            proof.raw_path == proof.debug_path or
            (proof.observer_native_number, "observer", None) not in proof.profiles):
        raise ReceiptRefused("unqualified_original_owner_proof")
    return {
        "schema": 1, "kind": "historical-native-debug-epoch",
        "generation": proof.generation, "operation_id": proof.operation_id,
        "final_args_sha256": proof.final_args_sha256,
        "owner_pid": proof.owner.pid, "owner_start": proof.owner.started,
        "owner_executable": proof.owner.executable,
        "raw_path": proof.raw_path, "debug_path": proof.debug_path,
        "observer_native_number": proof.observer_native_number,
        "profiles": [list(p) for p in proof.profiles],
        "ack_authorized": False
    }


class EpochReceipts:
    """Dormant root-private writes; NEVER a substitute for FD9/P2c attestation."""

    def __init__(self, root: Path = ROOT, *, owner_uid: int = 0,
                 writer_gid: int | None = None):
        self.root = Path(root)
        self.uid = owner_uid
        self.writer_gid = writer_gid
        if (not self.root.is_absolute() or self.root == self.root.parent or
                type(owner_uid) is not int or owner_uid < 0 or
                (writer_gid is not None and
                 (type(writer_gid) is not int or writer_gid <= 0))):
            raise ReceiptRefused("invalid_private_epoch_store")

    def _base(self, *, create: bool) -> None:
        _directory(self.root.parent, self.uid)
        if create and not self.root.exists() and not self.root.is_symlink():
            self.root.mkdir(mode=0o700)
            _sync(self.root.parent)
        _directory(self.root, self.uid)
        entries = os.listdir(self.root)
        if len(entries) > MAX_EPOCHS or any(not HEX32.fullmatch(v) for v in entries):
            raise ReceiptRefused("foreign_or_excessive_epoch_entries")

    def _generation(self, generation: str, *, create: bool) -> Path:
        if not isinstance(generation, str) or not HEX32.fullmatch(generation):
            raise ReceiptRefused("invalid_historical_generation")
        self._base(create=create)
        folder = self.root / generation
        if create and not folder.exists() and not folder.is_symlink():
            folder.mkdir(mode=0o700)
            _sync(self.root)
        _directory(folder, self.uid)
        entries = os.listdir(folder)
        expected_prefix = "intent-" + generation + "-"
        if (len(entries) > 2 or any(
                name != "epoch.json" and not (
                    name.startswith(expected_prefix) and
                    re.fullmatch(r"intent-[a-f0-9]{32}-[a-f0-9]{32}\.txt\.json", name))
                for name in entries) or
                sum(name.startswith("intent-") for name in entries) > 1):
            raise ReceiptRefused("foreign_or_ambiguous_generation_receipt")
        return folder

    def begin(self, proof: GenerationProof, cursor: Cursor) -> None:
        """Initialize exactly once from a future independently attested FD9.

        No old debug file is silently cleared or inherited; P2k1 empty_epoch
        must already have proved a new zero-length native debug inode.
        """
        if (not isinstance(cursor, Cursor) or
                not isinstance(proof, GenerationProof) or
                cursor.generation != proof.generation or
                cursor.offset != 0 or cursor.prefix_sha256 != EMPTY_HASH or
                type(cursor.device) is not int or cursor.device < 0 or
                type(cursor.inode) is not int or cursor.inode <= 0):
            raise ReceiptRefused("unqualified_initial_debug_cursor")
        # Independently read the actual protected zero-length native inode.
        # Never pin a fabricated dev/ino or inherit a prior generation's log.
        try:
            actual = empty_epoch(proof, owner_uid=self.uid,
                                 writer_gid=self.writer_gid)
        except DebugWindowRefused as exc:
            raise ReceiptRefused("no_trusted_empty_debug_epoch") from exc
        if actual != cursor:
            raise ReceiptRefused("initial_debug_inode_does_not_match")
        data = _proof_fields(proof)
        data.update(debug_device=cursor.device, debug_inode=cursor.inode,
                    committed_cursor_offset=0, committed_cursor_sha256=EMPTY_HASH)
        folder = self._generation(proof.generation, create=True)
        _write_once(folder, "epoch.json", _canonical(data), self.uid)

    def _epoch(self, proof: GenerationProof) -> tuple[Path, dict]:
        expected = _proof_fields(proof)
        folder = self._generation(proof.generation, create=False)
        try:
            doc = json.loads(_read(folder / "epoch.json", self.uid))
        except (ValueError, UnicodeError) as exc:
            raise ReceiptRefused("corrupt_generation_epoch") from exc
        if (not isinstance(doc, dict) or
                set(doc) != set(expected) | {
                    "debug_device", "debug_inode", "committed_cursor_offset",
                    "committed_cursor_sha256"} or
                any(doc.get(key) != value for key, value in expected.items()) or
                type(doc.get("debug_device")) is not int or
                type(doc.get("debug_inode")) is not int or
                doc["debug_device"] < 0 or doc["debug_inode"] <= 0 or
                doc.get("committed_cursor_offset") != 0 or
                doc.get("committed_cursor_sha256") != EMPTY_HASH):
            raise ReceiptRefused("epoch_differs_from_original_owner")
        return folder, doc

    def stage(self, proof: GenerationProof, cursor: Cursor, window: Window,
              pending: Path) -> None:
        """Persist only one immutable per-generation *uncommitted* intent.

        This never advances cursor and never acknowledges or deletes pending.
        The real future writer must prove FD.DRAINED plus native debug and
        idempotent destination sink before a distinct commit implementation.
        """
        folder, epoch = self._epoch(proof)
        pending = Path(pending)
        allowed = re.fullmatch(
            re.escape(proof.generation) + r"-[0-9a-f]{32}\.txt\Z",
            pending.name)
        if (not allowed or pending.parent != Path(proof.raw_path).parent / "pending" or
                not isinstance(window, Window) or not isinstance(cursor, Cursor) or
                cursor.generation != proof.generation or
                (cursor.device, cursor.inode, cursor.offset, cursor.prefix_sha256) !=
                (epoch["debug_device"], epoch["debug_inode"], 0, EMPTY_HASH) or
                window.proposed_cursor.generation != proof.generation or
                (window.proposed_cursor.device, window.proposed_cursor.inode) !=
                (cursor.device, cursor.inode) or
                window.proposed_cursor.offset <= 0 or
                not HEX64.fullmatch(window.proposed_cursor.prefix_sha256)):
            raise ReceiptRefused("segment_or_proposed_debug_cursor_untrusted")
        _directory(pending.parent, self.uid)
        try:
            before = pending.lstat()
            correct_mode = (0o600 if self.writer_gid is None else 0o660)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != self.uid or
                    before.st_nlink != 1 or
                    stat.S_IMODE(before.st_mode) != correct_mode or
                    (self.writer_gid is not None and
                     before.st_gid != self.writer_gid) or
                    not 0 < before.st_size <= MAX_SEGMENT):
                raise ReceiptRefused("pending_inode_not_fully_rotated")
            fd = os.open(pending, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                pinned = os.fstat(fd)
                data = os.read(fd, MAX_SEGMENT + 1)
                after = os.fstat(fd)
            finally:
                os.close(fd)
            if (pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) or
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) or
                    len(data) != before.st_size):
                raise ReceiptRefused("pending_changed_during_receipt")
        except OSError as exc:
            raise ReceiptRefused("pending_snapshot_unavailable") from exc
        if not data.endswith(b"\n") or b"\r" in data or b"\x00" in data:
            raise ReceiptRefused("incomplete_pending_segment")
        try:
            hosts = [line.decode("ascii") for line in data.split(b"\n")[:-1]]
        except UnicodeError as exc:
            raise ReceiptRefused("invalid_pending_encoding") from exc
        if (not hosts or any(not _hostname(v) for v in hosts) or
                [c.host for c in window.candidates] != hosts or
                any(c.native_number != proof.observer_native_number
                    for c in window.candidates)):
            raise ReceiptRefused("raw_and_debug_intent_disagree")
        # Re-run the REAL P2k1 inode/offset/raw comparison on the bounded
        # same-generation data. A caller's forged Window cannot stage intent.
        try:
            actual_window = propose_window(proof, cursor, data,
                                           owner_uid=self.uid,
                                           writer_gid=self.writer_gid)
        except DebugWindowRefused as exc:
            raise ReceiptRefused("native_debug_does_not_support_pending") from exc
        if actual_window != window:
            raise ReceiptRefused("caller_window_differs_from_native_debug")
        receipt_name = "intent-" + pending.name + ".json"
        existing = [name for name in os.listdir(folder) if name.startswith("intent-")]
        if existing and existing != [receipt_name]:
            raise ReceiptRefused("older_pending_intent_not_committed")
        intent = {
            "schema": 1, "kind": "pending-debug-intent-not-commit",
            "generation": proof.generation, "pending_name": pending.name,
            "pending_device": before.st_dev, "pending_inode": before.st_ino,
            "pending_size": before.st_size,
            "pending_sha256": hashlib.sha256(data).hexdigest(),
            "debug_device": cursor.device, "debug_inode": cursor.inode,
            "debug_start_offset": 0, "debug_start_sha256": EMPTY_HASH,
            "debug_end_offset": window.proposed_cursor.offset,
            "debug_end_sha256": window.proposed_cursor.prefix_sha256,
            "candidate_count": len(hosts), "ack_authorized": False
        }
        _write_once(folder, receipt_name,
                    _canonical(intent), self.uid)

    def historical(self, generation: str) -> HistoricalReceipt:
        """Read-only recovery. A receipt is NOT authorization for an old owner."""
        folder = self._generation(generation, create=False)
        try:
            epoch = json.loads(_read(folder / "epoch.json", self.uid))
            names = [n for n in os.listdir(folder) if n.startswith("intent-")]
            intent = (json.loads(_read(folder / names[0], self.uid)) if names else None)
        except (ValueError, UnicodeError) as exc:
            raise ReceiptRefused("corrupt_historical_receipt") from exc
        if (not isinstance(epoch, dict) or epoch.get("generation") != generation or
                epoch.get("kind") != "historical-native-debug-epoch" or
                epoch.get("ack_authorized") is not False or
                (intent is not None and
                 (not isinstance(intent, dict) or
                  intent.get("generation") != generation or
                  intent.get("kind") != "pending-debug-intent-not-commit" or
                  intent.get("ack_authorized") is not False))):
            raise ReceiptRefused("untrusted_historical_receipt")
        return HistoricalReceipt(epoch, intent)


def run_native_epoch_worker() -> None:
    raise ReceiptRefused("no_live_fd9_or_durable_destination_commit")


if __name__ == "__main__":
    run_native_epoch_worker()
