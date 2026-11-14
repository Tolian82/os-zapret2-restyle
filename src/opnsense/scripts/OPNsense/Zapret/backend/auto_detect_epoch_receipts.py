#!/usr/bin/env python3
"""#1052 P2k8q2: one forward-only original pretraffic seed and live completion.

The original held FD9 must seal an authenticated schema-2 shared candidate
and the *real empty* debug/raw inodes BEFORE dvtws2 starts. The later genuine
P2c process proof can complete that same immutable seed even if debug now
contains first-packet events. A receipt never itself authorizes observation,
Config, final targets, pending ACK or cron. No postlaunch zero-init fallback.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from auto_detect_debug_window import _read_exact, DebugWindowRefused
from auto_detect_owner import (GenerationProof, GenerationRefused,
                               MAX_ARGS, MAX_MAP, _secure_bytes, _valid_map,
                               attest_running_generation)
from auto_detect_original_v2_source import qualified_current_source, OriginalSourceRefused
from auto_detect_queue import DurableInbox, QueueSafetyError
from shared_apply_seal import (SEAL, SharedBundleError, verify_seal)

ROOT = Path("/var/db/zapret2/auto-detect-epochs")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
EMPTY_HASH = hashlib.sha256(b"").hexdigest()
MAX_EPOCHS = 128
MAX_RECORD = 16 * 1024


class ReceiptRefused(RuntimeError):
    """Never use a receipt to acknowledge a pending inode on uncertainty."""


def _directory(path: Path, uid: int) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ReceiptRefused("untrusted_root_private_directory") from exc
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
        "schema": 2, "kind": "original-native-debug-epoch",
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
        if (len(entries) > 3 or
                any(name not in ("pretraffic.json", "epoch.json",
                                 "cursor-chain-v2") for name in entries)):
            raise ReceiptRefused("superseded_one_intent_epoch_refused")
        if "cursor-chain-v2" in entries:
            _directory(folder / "cursor-chain-v2", self.uid)
        return folder

    def _pretraffic(self, proof: GenerationProof) -> tuple[Path, dict, bytes]:
        folder = self._generation(proof.generation, create=False)
        raw = _read(folder / "pretraffic.json", self.uid)
        try:
            seed = json.loads(raw)
        except (UnicodeError, TypeError, ValueError) as exc:
            raise ReceiptRefused("corrupt_original_pretraffic_seed") from exc
        required = {
            "schema", "kind", "generation", "owner_candidate_sha256",
            "release_seal_sha256", "final_args_sha256", "raw_path",
            "debug_path", "raw_device", "raw_inode", "debug_device",
            "debug_inode", "observer_native_number", "profiles",
            "ack_authorized",
        }
        if (not isinstance(seed, dict) or set(seed) != required or
                seed["schema"] != 2 or seed["kind"] != "original-fd9-pretraffic-zero" or
                seed["generation"] != proof.operation_id or
                seed["generation"] != proof.generation or
                not HEX64.fullmatch(str(seed["owner_candidate_sha256"])) or
                not HEX64.fullmatch(str(seed["release_seal_sha256"])) or
                seed["final_args_sha256"] != proof.final_args_sha256 or
                seed["raw_path"] != proof.raw_path or
                seed["debug_path"] != proof.debug_path or
                seed["observer_native_number"] != proof.observer_native_number or
                seed["profiles"] != [list(row) for row in proof.profiles] or
                any(type(seed[k]) is not int or seed[k] <= 0
                    for k in ("raw_inode", "debug_inode")) or
                any(type(seed[k]) is not int or seed[k] < 0
                    for k in ("raw_device", "debug_device")) or
                (seed["raw_device"], seed["raw_inode"]) ==
                    (seed["debug_device"], seed["debug_inode"]) or
                seed["ack_authorized"] is not False):
            raise ReceiptRefused("pretraffic_seed_differs_from_running_generation")
        return folder, seed, raw

    def seal_pretraffic(self, queue: DurableInbox, *, workspace: Path,
                        candidate_sha256: str) -> None:
        """Original-FD9 prelaunch only: durable immutable zero BEFORE a packet.

        Caller MUST own original FD9 and the original P2a flock and provide
        the independently obtained native PHP candidate digest. A detached P2h
        preview is insufficient: the actual sealed release must contain the
        genuine authorized schema-2 map and exact live observer argv. No API
        accepts a synthetic running GenerationProof at this stage.
        """
        if (not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                not isinstance(workspace, Path) or not workspace.is_absolute() or
                not HEX32.fullmatch(workspace.name) or
                not isinstance(candidate_sha256, str) or
                not HEX64.fullmatch(candidate_sha256)):
            raise ReceiptRefused("original_fd9_pretraffic_queue_and_candidate_required")
        try:
            # Production seed is valid ONLY from the original inherited held
            # FD9, not from a private root script or a second lock owner.
            # Portable source fixtures exercise the same file-level proof.
            if sys.platform.startswith("freebsd"):
                if self.uid != 0 or self.writer_gid is None or os.geteuid() != 0:
                    raise ReceiptRefused("original_root_fd9_required")
                from voice_ipfw_adapter import require_lifecycle_lock
                require_lifecycle_lock()
            queue._verify()
            if queue.segments():
                raise ReceiptRefused("unacknowledged_original_pending_before_launch")
            seal = verify_seal(workspace, owner=self.uid)
            argv = _secure_bytes(workspace / "release" / "dvtws.args",
                                 MAX_ARGS, self.uid)
            original_map = _secure_bytes(
                workspace / "release" / "auto-detect-generation.json",
                MAX_MAP, self.uid)
            mapping, profiles = _valid_map(
                original_map,
                {"id": workspace.name, "candidate": candidate_sha256}, argv)
            if (mapping["generation"] != workspace.name or
                    mapping["raw_path"] != str(queue.inbox) or
                    mapping["debug_path"] != str(queue.root / "debug.log")):
                raise ReceiptRefused("sealed_original_paths_or_generation_changed")
            locations = (queue.inbox, queue.root / "debug.log")
            a, b = (
                _read_exact(path, owner_uid=self.uid,
                            writer_gid=self.writer_gid)
                for path in locations
            )
            if (a[1] or b[1] or
                    (a[0].st_dev, a[0].st_ino) ==
                    (b[0].st_dev, b[0].st_ino)):
                raise ReceiptRefused("pretraffic_original_inodes_not_empty_and_distinct")
            # Reattest no initial bytes and exact same identities just before
            # durable write; the original shared FD9 ensures no engine has
            # launched between the two original queue snapshots.
            again = tuple(_read_exact(path, owner_uid=self.uid,
                                      writer_gid=self.writer_gid)
                          for path in locations)
            for original, current in zip((a, b), again):
                if (original[1] or current[1] or
                        (original[0].st_dev, original[0].st_ino,
                         original[0].st_size, original[0].st_mtime_ns) !=
                        (current[0].st_dev, current[0].st_ino,
                         current[0].st_size, current[0].st_mtime_ns)):
                    raise ReceiptRefused("pretraffic_native_inode_changed")
            if verify_seal(workspace, owner=self.uid) != seal or queue.segments():
                raise ReceiptRefused("pretraffic_shared_seal_or_queue_changed")
            data = {
                "schema": 2, "kind": "original-fd9-pretraffic-zero",
                "generation": workspace.name,
                "owner_candidate_sha256": candidate_sha256,
                "release_seal_sha256": hashlib.sha256(
                    _canonical(seal)).hexdigest(),
                "final_args_sha256": hashlib.sha256(argv).hexdigest(),
                "raw_path": str(locations[0]), "debug_path": str(locations[1]),
                "raw_device": a[0].st_dev, "raw_inode": a[0].st_ino,
                "debug_device": b[0].st_dev, "debug_inode": b[0].st_ino,
                "observer_native_number": mapping["observer_native_number"],
                "profiles": [list(row) for row in profiles],
                "ack_authorized": False,
            }
            folder = self._generation(workspace.name, create=True)
            if (folder / "epoch.json").exists() or (folder / "cursor-chain-v2").exists():
                raise ReceiptRefused("pretraffic_already_consumed")
            _write_once(folder, "pretraffic.json", _canonical(data), self.uid)
        except (OSError, ValueError, KeyError, TypeError, QueueSafetyError,
                GenerationRefused, DebugWindowRefused, SharedBundleError) as exc:
            raise ReceiptRefused("original_sealed_pretraffic_not_attested") from exc

    def finish_running(self, proof: GenerationProof, queue: DurableInbox, *,
                       attest=attest_running_generation) -> None:
        """Complete the exact original pretraffic seed AFTER live P2c attest.

        Debug and raw may ALREADY contain events. Never re-test zero or seed
        a new cursor from the postlaunch file: reuse its original inode at
        zero offset and retain every appended byte for P2k1/v2 inspection.
        """
        if (not isinstance(proof, GenerationProof) or
                not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                not callable(attest) or attest() != proof):
            raise ReceiptRefused("original_running_queue_and_owner_required")
        try:
            qualified_current_source(proof, queue)
            queue._verify()
            folder, seed, seed_raw = self._pretraffic(proof)
            if queue.segments():
                raise ReceiptRefused("original_pending_before_epoch_completion")
            a = _read_exact(queue.inbox, owner_uid=self.uid,
                            writer_gid=self.writer_gid)
            b = _read_exact(Path(proof.debug_path), owner_uid=self.uid,
                            writer_gid=self.writer_gid)
            if ((a[0].st_dev, a[0].st_ino) !=
                    (seed["raw_device"], seed["raw_inode"]) or
                    (b[0].st_dev, b[0].st_ino) !=
                    (seed["debug_device"], seed["debug_inode"])):
                raise ReceiptRefused("pretraffic_inode_replaced_after_launch")
            if attest() != proof:
                raise ReceiptRefused("original_engine_changed_before_epoch_completion")
            data = _proof_fields(proof)
            data.update(
                owner_candidate_sha256=seed["owner_candidate_sha256"],
                pretraffic_sha256=hashlib.sha256(seed_raw).hexdigest(),
                raw_device=seed["raw_device"], raw_inode=seed["raw_inode"],
                debug_device=seed["debug_device"],
                debug_inode=seed["debug_inode"],
                committed_cursor_offset=0,
                committed_cursor_sha256=EMPTY_HASH)
            if (folder / "cursor-chain-v2").exists():
                raise ReceiptRefused("cursor_chain_precedes_original_epoch")
            _write_once(folder, "epoch.json", _canonical(data), self.uid)
        except (OSError, ValueError, TypeError, QueueSafetyError,
                DebugWindowRefused, OriginalSourceRefused) as exc:
            raise ReceiptRefused("original_postlaunch_epoch_not_attested") from exc

    def _epoch(self, proof: GenerationProof) -> tuple[Path, dict]:
        expected = _proof_fields(proof)
        folder, seed, seed_raw = self._pretraffic(proof)
        try:
            doc = json.loads(_read(folder / "epoch.json", self.uid))
        except (ValueError, UnicodeError) as exc:
            raise ReceiptRefused("corrupt_generation_epoch") from exc
        additional = {
            "owner_candidate_sha256": seed["owner_candidate_sha256"],
            "pretraffic_sha256": hashlib.sha256(seed_raw).hexdigest(),
            "raw_device": seed["raw_device"],
            "raw_inode": seed["raw_inode"],
            "debug_device": seed["debug_device"],
            "debug_inode": seed["debug_inode"],
            "committed_cursor_offset": 0,
            "committed_cursor_sha256": EMPTY_HASH,
        }
        if (not isinstance(doc, dict) or
                set(doc) != set(expected) | set(additional) or
                any(doc.get(k) != v for k, v in expected.items()) or
                any(doc.get(k) != v for k, v in additional.items())):
            raise ReceiptRefused("epoch_differs_from_original_pretraffic_or_owner")
        return folder, doc
