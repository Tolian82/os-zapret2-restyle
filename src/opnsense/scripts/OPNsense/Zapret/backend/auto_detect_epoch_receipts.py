#!/usr/bin/env python3
"""#1052: one original pretraffic epoch and exact STOPPED source retirement.

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
from auto_detect_fd import _START
from auto_detect_owner import (GenerationProof, LearningGenerationProof,
                               GenerationRefused,
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
COMPLETED_HISTORY_KEEP = 4  # root-private ACKed runs, never domain count
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


def _digest_seal(seal) -> str:
    return hashlib.sha256(_canonical(seal)).hexdigest()


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
        if len(entries) > MAX_EPOCHS or any(
                not (HEX32.fullmatch(v) or
                     (v.startswith(".gc-") and HEX32.fullmatch(v[4:])) or
                     (v.startswith(".gc3-") and HEX32.fullmatch(v[5:])))
                for v in entries):
            raise ReceiptRefused("foreign_or_excessive_epoch_entries")

    def prune_completed(self, queue: DurableInbox, *, protect: str,
                        keep: int = COMPLETED_HISTORY_KEEP) -> int:
        """Reclaim ONLY fully ACKed prior epochs, never live discovery data.

        Called by the ORIGINAL FD9 pretraffic seed while holding P2a's
        original flock and only after the old owner was retired. A .gc-
        tombstone makes deletion recoverable if interrupted: a later native
        pretraffic seed finishes it, without trusting a half-erased receipt.
        No Config write, engine stop, live raw or pending mutation.
        """
        from auto_detect_cursor_chain import CursorChain, CursorChainRefused
        from auto_detect_fd import OwnerToken
        if (not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                not isinstance(protect, str) or not HEX32.fullmatch(protect) or
                type(keep) is not int or not 1 <= keep <= 16):
            raise ReceiptRefused("original_fd9_history_maintenance_owner_required")
        pinned_prior = None
        if sys.platform.startswith("freebsd"):
            from voice_ipfw_adapter import require_lifecycle_lock
            from shared_apply_operation import SharedApplyOperation
            require_lifecycle_lock()
            record = SharedApplyOperation(owner=0).read()
            if (record is not None and record["phase"] in ("activating", "activated") and
                    record["detail"]["id"] == protect and
                    record.get("previous_manifest", {}).get("schema") == 2):
                pinned_prior = record["previous"]["id"]
        _directory(self.root.parent, self.uid)
        if not self.root.exists() and not self.root.is_symlink():
            if pinned_prior is not None:
                raise ReceiptRefused("pinned_previous_learning_history_missing")
            return 0
        _directory(self.root, self.uid)
        all_names = os.listdir(self.root)
        if (len(all_names) > MAX_EPOCHS or
                any(not (HEX32.fullmatch(n) or
                         (n.startswith(".gc-") and HEX32.fullmatch(n[4:])) or
                         (n.startswith(".gc3-") and HEX32.fullmatch(n[5:])))
                    for n in all_names)):
            raise ReceiptRefused("foreign_historical_epoch_before_reclaim")

        # The in-flight bound predecessor remains rollback evidence even
        # if a modified directory timestamp would put it outside the last
        # four. This temporary pin lasts only through the original WAL.
        if pinned_prior is not None and (
                pinned_prior not in all_names or ".gc3-" + pinned_prior in all_names or
                ".gc-" + pinned_prior in all_names):
            raise ReceiptRefused("pinned_previous_learning_history_missing")

        # Finish only exact, already-renamed root-private deletion. A .gc
        # name is never an owner, log or ACK. Its allowed children are
        # checked without following symlinks after partial prior deletion.
        for name in sorted(n for n in all_names
                           if n.startswith(".gc-") or n.startswith(".gc3-")):
            if name.startswith(".gc3-"):
                from auto_detect_learning_gc import erase_completed_learning
                erase_completed_learning(self, queue, self.root / name)
            else:
                self._erase_completed_tree(self.root / name, "generation")

        completed = []
        for name in sorted(os.listdir(self.root)):
            if name == protect:
                continue
            folder = self.root / name
            _directory(folder, self.uid)
            if not (folder / "retired.json").exists():
                # Schema3 uses its own terminal receipt and exact N/debug
                # archives. Never reclaim unfinished/aborted learning runs.
                from auto_detect_learning_retirement import _entry as _learning_entry
                if _learning_entry(folder / "learning-retirement" / "ready.json"):
                    from auto_detect_learning_gc import qualified_completed_learning
                    try:
                        stamp = qualified_completed_learning(self, queue, name)
                    except (OSError, ValueError, TypeError, KeyError,
                            RuntimeError) as exc:
                        raise ReceiptRefused(
                            "historical_learning_not_qualified_for_reclaim") from exc
                    completed.append((stamp, name, "learning"))
                continue
            try:
                epoch = json.loads(_read(folder / "epoch.json", self.uid))
                if (not isinstance(epoch, dict) or
                        epoch.get("generation") != name or
                        epoch.get("operation_id") != name):
                    raise ReceiptRefused("foreign_completed_generation")
                owner = OwnerToken(epoch["owner_pid"],
                                   epoch["owner_start"],
                                   epoch["owner_executable"])
                proof = GenerationProof(
                    owner, name, name, epoch["final_args_sha256"],
                    epoch["raw_path"], epoch["debug_path"],
                    epoch["observer_native_number"],
                    tuple(tuple(row) for row in epoch["profiles"]))
                folder, verified_epoch = self._epoch(proof)
                if verified_epoch != epoch:
                    raise ReceiptRefused("changed_completed_epoch")
                # Refuse torn or unpublished cursor rollover: the newest
                # ACK must be proved by the exact immutable v2 chain.
                if any((folder / x).exists() or (folder / x).is_symlink()
                       for x in ("cursor-chain-v2.next", "cursor-chain-v2.old")):
                    raise ReceiptRefused("unfinished_historical_cursor_rollover")
                tip = CursorChain(self, queue).tip(proof)
                if tip.open_folder is not None or tip.open_intent is not None:
                    raise ReceiptRefused("unacknowledged_historical_generation")
                plan = json.loads(_read(folder / "retired.json", self.uid))
                if (not isinstance(plan, dict) or
                        set(plan) != {"schema", "kind", "generation",
                                     "owner_sha256", "last_ack_sha256",
                                     "cycle", "next_sequence", "sources"} or
                        plan["schema"] != 1 or
                        plan["kind"] != "original-stopped-source-retirement" or
                        plan["generation"] != name or
                        plan["owner_sha256"] != hashlib.sha256(
                            _canonical(_proof_fields(proof))).hexdigest() or
                        plan["last_ack_sha256"] != tip.previous_ack_sha256 or
                        plan["cycle"] != tip.cycle or
                        plan["next_sequence"] != tip.next_sequence or
                        not isinstance(plan["sources"], dict) or
                        set(plan["sources"]) != {"inbox", "debug", "previous"}):
                    raise ReceiptRefused("historical_final_ack_not_proven")
                for key, filename in (("inbox", "retired-inbox.txt"),
                                      ("debug", "retired-debug.log"),
                                      ("previous", "retired-debug-previous.log")):
                    expected = plan["sources"][key]
                    target = folder / filename
                    if expected is None:
                        if key != "previous" or target.exists() or target.is_symlink():
                            raise ReceiptRefused("unexpected_historical_archive")
                        continue
                    if (not isinstance(expected, list) or len(expected) != 4 or
                            any(type(n) is not int or n < 0 for n in expected[:3]) or
                            expected[1] <= 0 or
                            not isinstance(expected[3], str) or
                            not HEX64.fullmatch(expected[3])):
                        raise ReceiptRefused("corrupt_historical_inode_identity")
                    entry = target.lstat()
                    mode = 0o660 if self.writer_gid is not None else 0o600
                    if (not stat.S_ISREG(entry.st_mode) or
                            entry.st_uid != self.uid or entry.st_nlink != 1 or
                            stat.S_IMODE(entry.st_mode) != mode or
                            (self.writer_gid is not None and
                             entry.st_gid != self.writer_gid) or
                            entry.st_size > 4 * 1024 * 1024):
                        raise ReceiptRefused("untrusted_historical_archive")
                    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        opened = os.fstat(fd)
                        data = os.read(fd, 4 * 1024 * 1024 + 1)
                        after = os.fstat(fd)
                    finally:
                        os.close(fd)
                    final = target.lstat()
                    identity = lambda st: (st.st_dev, st.st_ino, st.st_size,
                                           st.st_mtime_ns, st.st_nlink)
                    if (identity(entry) != identity(opened) or
                            identity(opened) != identity(after) or
                            identity(after) != identity(final) or
                            [entry.st_dev, entry.st_ino, len(data),
                             hashlib.sha256(data).hexdigest()] != expected or
                            (key == "inbox" and data)):
                        raise ReceiptRefused("changed_historical_archive")
                completed.append((folder.stat().st_mtime_ns, name, "schema2"))
            except (OSError, ValueError, TypeError, KeyError, IndexError,
                    CursorChainRefused, GenerationRefused,
                    OriginalSourceRefused) as exc:
                raise ReceiptRefused("historical_epoch_not_qualified_for_reclaim") from exc

        # Active/new generation plus last four fully verified completed
        # runs never enter the deletion set. No date-only TTL.
        completed.sort()
        removed = 0
        for _, name, kind in completed[:-keep]:
            if name == pinned_prior:
                continue
            original = self.root / name
            tombstone = self.root / (
                (".gc3-" if kind == "learning" else ".gc-") + name)
            if tombstone.exists() or tombstone.is_symlink():
                raise ReceiptRefused("concurrent_historical_reclaim")
            original.rename(tombstone)
            _sync(self.root)
            if kind == "learning":
                from auto_detect_learning_gc import erase_completed_learning
                erase_completed_learning(self, queue, tombstone)
            else:
                self._erase_completed_tree(tombstone, "generation")
            removed += 1
        return removed

    def _erase_completed_tree(self, path: Path, kind: str) -> None:
        """Idempotent strict-name removal only inside sealed tombstones."""
        _directory(path, self.uid)
        from auto_detect_cursor_chain import STEP
        allowed_files = {
            "generation": {"pretraffic.json", "epoch.json", "retired.json",
                           "retired-inbox.txt", "retired-debug.log",
                           "retired-debug-previous.log"},
            "chain": {"anchor.json"},
            "slot": {"intent.json", "ack.json", "recovery.json"},
            "destination": {"plan.json", "checkpoint.json"},
        }
        for child in sorted(path.iterdir()):
            name = child.name
            childkind = (
                "chain" if kind == "generation" and name == "cursor-chain-v2"
                else "slot" if kind == "chain" and STEP.fullmatch(name)
                else "destination" if kind == "slot" and name == "destination"
                else None)
            if childkind is not None:
                self._erase_completed_tree(child, childkind)
                continue
            if name not in allowed_files[kind]:
                raise ReceiptRefused("foreign_completed_tree_entry")
            info = child.lstat()
            mode = stat.S_IMODE(info.st_mode)
            is_log = name.startswith("retired-") and name.endswith((".txt", ".log"))
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or
                    info.st_nlink != 1 or
                    (is_log and mode != (0o660 if self.writer_gid is not None
                                         else 0o600)) or
                    (not is_log and mode != 0o600) or
                    (is_log and self.writer_gid is not None and
                     info.st_gid != self.writer_gid)):
                raise ReceiptRefused("untrusted_completed_tree_file")
            child.unlink()
        _sync(path)
        path.rmdir()
        _sync(path.parent)

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
        # A rollover keeps the previous fully ACKed cursor tree as one
        # original-owner recovery witness while its sealed successor is
        # atomically published. No separate epoch, owner or Config writer.
        allowed = ("pretraffic.json", "epoch.json", "cursor-chain-v2",
                   "cursor-chain-v2.next", "cursor-chain-v2.old",
                   "retired.json", "retired-inbox.txt", "retired-debug.log",
                   "retired-debug-previous.log", "learning-retirement")
        if len(entries) > len(allowed) or any(name not in allowed for name in entries):
            raise ReceiptRefused("superseded_one_intent_epoch_refused")
        for name in ("cursor-chain-v2", "cursor-chain-v2.next",
                     "cursor-chain-v2.old", "learning-retirement"):
            if name in entries:
                _directory(folder / name, self.uid)
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
            # Qualify the original candidate, inodes and saved Config first;
            # reclaim only old fully ACKed epochs while the SAME original
            # FD9/P2a lock is held, before launching the real engine.
            self.prune_completed(queue, protect=workspace.name)
            folder = self._generation(workspace.name, create=True)
            if (folder / "epoch.json").exists() or (folder / "cursor-chain-v2").exists():
                raise ReceiptRefused("pretraffic_already_consumed")
            _write_once(folder, "pretraffic.json", _canonical(data), self.uid)
        except (OSError, ValueError, KeyError, TypeError, QueueSafetyError,
                GenerationRefused, DebugWindowRefused, SharedBundleError) as exc:
            raise ReceiptRefused("original_sealed_pretraffic_not_attested") from exc


    def seal_learning_pretraffic(self, queue: DurableInbox, *,
                                 workspace: Path, candidate_sha256: str,
                                 wire: str, root_gid: int, engine_uid: int,
                                 attest) -> dict:
        """Durable N-file zero-cut in the ORIGINAL epoch store; no activation.

        The proposed final argv must already be accompanied by the same
        fully sealed original args/source and an explicit active schema3 map.
        Even such a seed is NOT a P2c owner: the installed schema2 _epoch()
        will reject it, and no CLI currently exposes this entrypoint. It
        may only be called by the future original held-FD9 launcher BEFORE
        its native traffic and after original sealed-release promotion.
        """
        from auto_detect_origin_map import ORIGIN_FILE
        from auto_detect_owner import _valid_learning_active
        from auto_detect_post_drop import (
            PostDropRefused, _witness_decode_learning,
        )
        from auto_detect_original_v2_source import (
            preview_learning_pretraffic_cursors_locked,
        )
        if (not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                self.writer_gid is None or
                not isinstance(workspace, Path) or
                not workspace.is_absolute() or not HEX32.fullmatch(workspace.name) or
                not isinstance(candidate_sha256, str) or
                not HEX64.fullmatch(candidate_sha256) or
                not isinstance(wire, str) or type(root_gid) is not int or
                root_gid < 0 or type(engine_uid) is not int or
                engine_uid <= 0 or not callable(attest)):
            raise ReceiptRefused("learning_original_fd9_pretraffic_required")
        try:
            if sys.platform.startswith("freebsd"):
                if self.uid != 0 or os.geteuid() != 0:
                    raise ReceiptRefused("learning_root_original_fd9_required")
                from voice_ipfw_adapter import require_lifecycle_lock
                require_lifecycle_lock()
            queue._verify()
            if queue.segments():
                raise ReceiptRefused("learning_unacknowledged_pending_before_launch")
            seal = verify_seal(workspace, owner=self.uid)
            release = workspace / "release"
            original = _secure_bytes(
                release / "dvtws.original.args", MAX_ARGS, self.uid)
            final = _secure_bytes(release / "dvtws.args", MAX_ARGS, self.uid)
            native_map = _secure_bytes(
                release / "auto-detect-generation.json", MAX_MAP, self.uid)
            source_bytes = _secure_bytes(
                release / ORIGIN_FILE, MAX_MAP, self.uid)
            source = json.loads(source_bytes)
            approved = _valid_learning_active(
                native_map, {"id": workspace.name,
                             "candidate": candidate_sha256},
                source, original, final)
            if (not approved or
                    any(Path(path).parent != queue.root for _, _, path in approved)):
                raise ReceiptRefused("learning_original_native_paths_changed")
            producer = _witness_decode_learning(
                wire, approved, root=queue.root, root_uid=self.uid,
                root_gid=root_gid, engine_uid=engine_uid,
                engine_gid=self.writer_gid)
            cursors = preview_learning_pretraffic_cursors_locked(
                queue, wire, approved, root_gid=root_gid,
                engine_uid=engine_uid, attest=attest)
            if (attest() is not True or queue.segments() or
                    verify_seal(workspace, owner=self.uid) != seal or
                    _secure_bytes(release / "dvtws.args", MAX_ARGS, self.uid) != final or
                    _secure_bytes(release / "auto-detect-generation.json",
                                  MAX_MAP, self.uid) != native_map or
                    _secure_bytes(release / ORIGIN_FILE, MAX_MAP, self.uid) !=
                    source_bytes):
                raise ReceiptRefused("learning_pretraffic_release_or_owner_changed")
            # Repeat every physical zero check after verifying the exact
            # sealed map: no new append or changed inode can be silently
            # turned into an already-committed cursor.
            if (preview_learning_pretraffic_cursors_locked(
                    queue, wire, approved, root_gid=root_gid,
                    engine_uid=engine_uid, attest=attest) != cursors):
                raise ReceiptRefused("learning_pretraffic_zero_cut_changed")
            names = ("inbox.txt", "debug.log", *producer.learning_names)
            seed = {
                "schema": 3, "kind": "original-fd9-learning-pretraffic-zero",
                "generation": workspace.name,
                "owner_candidate_sha256": candidate_sha256,
                "release_seal_sha256": hashlib.sha256(
                    _canonical(seal)).hexdigest(),
                "original_args_sha256": hashlib.sha256(original).hexdigest(),
                "final_args_sha256": hashlib.sha256(final).hexdigest(),
                "native_map_sha256": hashlib.sha256(native_map).hexdigest(),
                "source_map_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "witness_sha256": hashlib.sha256(wire.encode()).hexdigest(),
                "files": [
                    {"name": name, "device": identity[0],
                     "inode": identity[1], "nlink": identity[2]}
                    for name, identity in zip(names, producer.identities)
                ],
                "learning": [
                    {"native_number": number, "hostlist": hostlist,
                     "path": path, "device": cursors[path].device,
                     "inode": cursors[path].inode,
                     "offset": cursors[path].offset,
                     "prefix_sha256": cursors[path].prefix_sha256}
                    for number, hostlist, path in approved
                ],
                "ack_authorized": False,
            }
            encoded = _canonical(seed)  # Bound by existing 16 KiB receipt.
            # The same original FD9/P2a reclaims only independently qualified
            # terminal schema2/schema3 history older than the last four.
            # It never touches current producer/Found/managed/Config.
            self.prune_completed(queue, protect=workspace.name)
            folder = self._generation(workspace.name, create=True)
            if ((folder / "epoch.json").exists() or
                    (folder / "cursor-chain-v2").exists()):
                raise ReceiptRefused("learning_pretraffic_epoch_already_consumed")
            _write_once(folder, "pretraffic.json", encoded, self.uid)
            return seed
        except ReceiptRefused:
            raise
        except (OSError, ValueError, TypeError, KeyError,
                QueueSafetyError, GenerationRefused, DebugWindowRefused,
                SharedBundleError, PostDropRefused, OriginalSourceRefused) as exc:
            raise ReceiptRefused("learning_sealed_pretraffic_not_attested") from exc



    def _learning_pretraffic(
        self, proof: LearningGenerationProof, queue: DurableInbox,
        workspace: Path,
    ) -> tuple[Path, dict, bytes]:
        """Revalidate schema3 zero-cut against the SAME sealed original release.

        Do not infer a live process from this pretraffic receipt. The caller
        additionally needs an independent original FD9/P2c owner attester.
        """
        from auto_detect_origin_map import ORIGIN_FILE
        from auto_detect_owner import _valid_learning_active
        if (not isinstance(proof, LearningGenerationProof) or
                not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                self.writer_gid is None or
                not isinstance(workspace, Path) or
                workspace.name != proof.operation_id or
                not HEX32.fullmatch(proof.operation_id) or
                proof.generation != proof.operation_id or
                not HEX64.fullmatch(proof.owner_candidate_sha256) or
                not HEX64.fullmatch(proof.final_args_sha256) or
                not HEX64.fullmatch(proof.native_map_sha256) or
                not isinstance(proof.learning, tuple) or
                not 1 <= len(proof.learning) <= 255):
            raise ReceiptRefused("unqualified_learning_epoch_source")
        folder = self._generation(proof.generation, create=False)
        seed_raw = _read(folder / "pretraffic.json", self.uid)
        try:
            seed = json.loads(seed_raw)
        except (UnicodeError, ValueError, TypeError) as exc:
            raise ReceiptRefused("invalid_learning_pretraffic_document") from exc
        required = {
            "schema", "kind", "generation", "owner_candidate_sha256",
            "release_seal_sha256", "original_args_sha256",
            "final_args_sha256", "native_map_sha256",
            "source_map_sha256", "witness_sha256",
            "files", "learning", "ack_authorized",
        }
        if (not isinstance(seed, dict) or set(seed) != required or
                seed_raw != _canonical(seed) or
                type(seed["schema"]) is not int or seed["schema"] != 3 or
                seed["kind"] != "original-fd9-learning-pretraffic-zero" or
                seed["generation"] != proof.generation or
                seed["owner_candidate_sha256"] != proof.owner_candidate_sha256 or
                seed["final_args_sha256"] != proof.final_args_sha256 or
                seed["native_map_sha256"] != proof.native_map_sha256 or
                any(not HEX64.fullmatch(str(seed[field]))
                    for field in ("release_seal_sha256", "original_args_sha256",
                                  "source_map_sha256", "witness_sha256")) or
                seed["ack_authorized"] is not False or
                not isinstance(seed["files"], list) or
                not isinstance(seed["learning"], list)):
            raise ReceiptRefused("learning_zero_cut_is_not_original_epoch")
        seal = verify_seal(workspace, owner=self.uid)
        release = workspace / "release"
        original = _secure_bytes(
            release / "dvtws.original.args", MAX_ARGS, self.uid)
        argv = _secure_bytes(release / "dvtws.args", MAX_ARGS, self.uid)
        native = _secure_bytes(
            release / "auto-detect-generation.json", MAX_MAP, self.uid)
        source_bytes = _secure_bytes(release / ORIGIN_FILE, MAX_MAP, self.uid)
        source = json.loads(source_bytes)
        approved = _valid_learning_active(
            native, {"id": proof.generation,
                     "candidate": proof.owner_candidate_sha256},
            source, original, argv)
        if (approved != proof.learning or
                hashlib.sha256(_canonical(seal)).hexdigest() !=
                seed["release_seal_sha256"] or
                hashlib.sha256(original).hexdigest() !=
                seed["original_args_sha256"] or
                hashlib.sha256(argv).hexdigest() != seed["final_args_sha256"] or
                hashlib.sha256(native).hexdigest() != seed["native_map_sha256"] or
                hashlib.sha256(source_bytes).hexdigest() !=
                seed["source_map_sha256"]):
            raise ReceiptRefused("learning_epoch_sealed_generation_changed")
        expected_names = [
            "inbox.txt", "debug.log", *(Path(path).name
                                        for _, _, path in approved)]
        if (len(seed["files"]) != len(expected_names) or
                len(seed["learning"]) != len(approved) or
                any(Path(path).parent != queue.root for _, _, path in approved)):
            raise ReceiptRefused("learning_epoch_missing_native_inode")
        seen: set[tuple[int, int]] = set()
        for name, row in zip(expected_names, seed["files"]):
            if (not isinstance(row, dict) or
                    set(row) != {"name", "device", "inode", "nlink"} or
                    row["name"] != name or
                    any(type(row[field]) is not int for field in
                        ("device", "inode", "nlink")) or
                    row["device"] < 0 or row["inode"] <= 0 or
                    row["nlink"] != 1 or
                    (row["device"], row["inode"]) in seen):
                raise ReceiptRefused("learning_epoch_foreign_inode_seed")
            seen.add((row["device"], row["inode"]))
        for index, (number, hostlist, path) in enumerate(approved):
            saved = seed["learning"][index]
            matched = seed["files"][index + 2]
            if (not isinstance(saved, dict) or
                    set(saved) != {"native_number", "hostlist", "path",
                                   "device", "inode", "offset", "prefix_sha256"} or
                    (saved["native_number"], saved["hostlist"], saved["path"]) !=
                    (number, hostlist, path) or
                    saved["device"] != matched["device"] or
                    saved["inode"] != matched["inode"] or
                    type(saved["offset"]) is not int or saved["offset"] != 0 or
                    saved["prefix_sha256"] != EMPTY_HASH):
                raise ReceiptRefused("learning_epoch_cursor_not_original_zero")
        return folder, seed, seed_raw

    def _attest_learning_running_seed(
        self, proof: LearningGenerationProof, queue: DurableInbox, *,
        workspace: Path, attest, unfinished: bool = False,
    ) -> tuple[Path, dict]:
        """One original live seed verifier, before either Config or epoch commit.

        Borrow the caller's existing P2a scope. Never create an epoch here.
        The native owner callback is independently rechecked around the
        original immutable pretraffic and all current producer identities.
        """
        from auto_detect_fd import OwnerToken
        from voice_live_inspect import CHILD_EXEC
        if (not isinstance(proof, LearningGenerationProof) or
                not isinstance(proof.owner, OwnerToken) or
                type(proof.owner.pid) is not int or proof.owner.pid <= 1 or
                type(proof.owner.started) is not str or
                not _START.fullmatch(proof.owner.started) or
                proof.owner.executable != CHILD_EXEC or
                not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                self.writer_gid is None or not callable(attest) or
                attest() != proof):
            raise ReceiptRefused("learning_original_running_owner_required")
        try:
            if sys.platform.startswith("freebsd"):
                if self.uid != 0 or os.geteuid() != 0:
                    raise ReceiptRefused("learning_fd9_running_root_required")
                from voice_ipfw_adapter import require_lifecycle_lock
                require_lifecycle_lock()
            queue._verify()
            if queue.segments():
                raise ReceiptRefused("learning_running_has_unacknowledged_pending")
            folder, seed, seed_raw = self._learning_pretraffic(
                proof, queue, workspace)
            from auto_detect_debug_window import _read_exact
            paths = [queue.inbox, queue.root / "debug.log",
                     *(Path(path) for _, _, path in proof.learning)]
            for path, identity in zip(paths, seed["files"]):
                native, _ = _read_exact(
                    path, owner_uid=self.uid, writer_gid=self.writer_gid)
                if (native.st_dev != identity["device"] or
                        native.st_ino != identity["inode"] or
                        native.st_nlink != identity["nlink"]):
                    raise ReceiptRefused("learning_running_inode_differs_from_zero")
            # Postlaunch append is ALLOWED. Cursor remains exactly zero
            # until the original verified P2a/P2b/P2c WAL and Found transfer.
            if attest() != proof or queue.segments():
                raise ReceiptRefused("learning_running_owner_changed_before_epoch")
            queue._verify()
            for path, identity in zip(paths, seed["files"]):
                native, _ = _read_exact(
                    path, owner_uid=self.uid, writer_gid=self.writer_gid)
                if (native.st_dev, native.st_ino, native.st_nlink) != (
                        identity["device"], identity["inode"], identity["nlink"]):
                    raise ReceiptRefused("learning_running_inode_changed_during_epoch")
            if attest() != proof:
                raise ReceiptRefused("learning_running_owner_changed_after_recheck")
            data = {
                "schema": 3, "kind": "original-native-learning-epoch",
                "generation": proof.generation,
                "operation_id": proof.operation_id,
                "owner_candidate_sha256": proof.owner_candidate_sha256,
                "final_args_sha256": proof.final_args_sha256,
                "native_map_sha256": proof.native_map_sha256,
                "pretraffic_sha256": hashlib.sha256(seed_raw).hexdigest(),
                "owner_pid": proof.owner.pid,
                "owner_start": proof.owner.started,
                "owner_executable": proof.owner.executable,
                "files": seed["files"],
                "learning": seed["learning"],
                "ack_authorized": False,
            }
            # Before Config commit only the original zero receipt may exist.
            # During finalization allow an exact already-written epoch for
            # idempotent retry, never cursor/retirement residue.
            allowed = {"pretraffic.json"} if unfinished else {"pretraffic.json", "epoch.json"}
            if set(os.listdir(folder)) - allowed:
                raise ReceiptRefused("learning_running_cursor_chain_already_exists")
            if (_read(folder / "pretraffic.json", self.uid) != seed_raw or
                    queue.segments() or attest() != proof):
                raise ReceiptRefused("learning_running_seed_changed")
            return folder, data
        except ReceiptRefused:
            raise
        except (OSError, ValueError, TypeError, KeyError, QueueSafetyError,
                GenerationRefused, DebugWindowRefused,
                SharedBundleError) as exc:
            raise ReceiptRefused("learning_running_epoch_not_attested") from exc


    def verify_learning_running_pretraffic(
        self, proof: LearningGenerationProof, queue: DurableInbox, *,
        workspace: Path, attest,
    ) -> str:
        """Read-only pre-Config proof; never write epoch, cursor or ACK."""
        _, data = self._attest_learning_running_seed(
            proof, queue, workspace=workspace, attest=attest, unfinished=True)
        return data["pretraffic_sha256"]

    def finish_learning_running(
        self, proof: LearningGenerationProof, queue: DurableInbox, *,
        workspace: Path, attest,
    ) -> dict:
        """Finish the same original epoch, only after native saved-Config phase."""
        folder, data = self._attest_learning_running_seed(
            proof, queue, workspace=workspace, attest=attest)
        _write_once(folder, "epoch.json", _canonical(data), self.uid)
        return data


    def verify_learning_stopped_epoch(
        self, proof: LearningGenerationProof, *, workspace: Path,
    ) -> dict:
        """Strict immutable schema3 epoch, originally used by STOPPED P2c.

        The historical method name is retained. This reads the original
        immutable receipt only, not current producer files or process state.
        The caller independently proves the required running/stopped owner.
        It is NOT the schema2 _epoch(), a live native source check, a
        retirement proof or an ACK permit. No producer inode or OLD archive
        is opened, changed, truncated or removed.
        """
        from auto_detect_origin_map import ORIGIN_FILE
        from auto_detect_owner import _valid_learning_active
        from auto_detect_storage import ROOT as PRODUCER_ROOT
        from voice_live_inspect import CHILD_EXEC
        if (not isinstance(proof, LearningGenerationProof) or
                not isinstance(workspace, Path) or not workspace.is_absolute() or
                workspace.name != proof.generation or
                proof.generation != proof.operation_id or
                not HEX32.fullmatch(proof.generation) or
                not HEX64.fullmatch(proof.owner_candidate_sha256) or
                not HEX64.fullmatch(proof.final_args_sha256) or
                not HEX64.fullmatch(proof.native_map_sha256) or
                proof.owner.pid <= 1 or
                not _START.fullmatch(proof.owner.started) or
                proof.owner.executable != CHILD_EXEC or
                not isinstance(proof.learning, tuple) or
                not 1 <= len(proof.learning) <= 255):
            raise ReceiptRefused("stopped_learning_proof_not_original")
        try:
            folder = self._generation(proof.generation, create=False)
            zero_raw = _read(folder / "pretraffic.json", self.uid)
            epoch_raw = _read(folder / "epoch.json", self.uid)
            zero, epoch = json.loads(zero_raw), json.loads(epoch_raw)
            if (zero_raw != _canonical(zero) or
                    epoch_raw != _canonical(epoch) or
                    type(zero) is not dict or type(epoch) is not dict):
                raise ReceiptRefused("stopped_learning_receipt_noncanonical")
            seal = verify_seal(workspace, owner=self.uid)
            release = workspace / "release"
            original = _secure_bytes(
                release / "dvtws.original.args", MAX_ARGS, self.uid)
            final = _secure_bytes(
                release / "dvtws.args", MAX_ARGS, self.uid)
            native = _secure_bytes(
                release / "auto-detect-generation.json", MAX_MAP, self.uid)
            source = _secure_bytes(
                release / ORIGIN_FILE, MAX_MAP, self.uid)
            authorized = _valid_learning_active(
                native, {"id": proof.generation,
                         "candidate": proof.owner_candidate_sha256},
                json.loads(source), original, final)
            if authorized != proof.learning:
                raise ReceiptRefused("stopped_learning_native_map_mismatch")
            file_names = [
                "inbox.txt", "debug.log",
                *(Path(path).name for _, _, path in authorized)]
            if (len(file_names) != len(set(file_names)) or
                    any(Path(path).parent != PRODUCER_ROOT
                        for _, _, path in authorized)):
                raise ReceiptRefused("stopped_learning_foreign_producer_root")
            records = zero.get("files")
            learning = zero.get("learning")
            if (type(records) is not list or
                    len(records) != len(file_names) or
                    type(learning) is not list or
                    len(learning) != len(authorized)):
                raise ReceiptRefused("stopped_learning_zero_missing_N")
            inode_ids = set()
            for name, record in zip(file_names, records):
                if (type(record) is not dict or
                        set(record) != {"name", "device", "inode", "nlink"} or
                        record["name"] != name or
                        any(type(record[k]) is not int
                            for k in ("device", "inode", "nlink")) or
                        record["device"] < 0 or record["inode"] <= 0 or
                        record["nlink"] != 1 or
                        (record["device"], record["inode"]) in inode_ids):
                    raise ReceiptRefused("stopped_learning_zero_inode_invalid")
                inode_ids.add((record["device"], record["inode"]))
            for index, (number, hostlist, path) in enumerate(authorized):
                row = learning[index]
                pinned = records[index + 2]
                if (type(row) is not dict or set(row) != {
                        "native_number", "hostlist", "path", "device",
                        "inode", "offset", "prefix_sha256"} or
                        (row["native_number"], row["hostlist"], row["path"]) !=
                        (number, hostlist, path) or
                        row["device"] != pinned["device"] or
                        row["inode"] != pinned["inode"] or
                        type(row["offset"]) is not int or row["offset"] != 0 or
                        row["prefix_sha256"] != EMPTY_HASH):
                    raise ReceiptRefused("stopped_learning_zero_N_unqualified")
            expected_zero = {
                "schema": 3, "kind": "original-fd9-learning-pretraffic-zero",
                "generation": proof.generation,
                "owner_candidate_sha256": proof.owner_candidate_sha256,
                "release_seal_sha256": _digest_seal(seal),
                "original_args_sha256": hashlib.sha256(original).hexdigest(),
                "final_args_sha256": proof.final_args_sha256,
                "native_map_sha256": proof.native_map_sha256,
                "source_map_sha256": hashlib.sha256(source).hexdigest(),
                "witness_sha256": zero.get("witness_sha256"),
                "files": records, "learning": learning,
                "ack_authorized": False,
            }
            if (not isinstance(zero.get("witness_sha256"), str) or
                    not HEX64.fullmatch(zero["witness_sha256"]) or
                    zero != expected_zero or
                    hashlib.sha256(final).hexdigest() !=
                    proof.final_args_sha256 or
                    hashlib.sha256(native).hexdigest() !=
                    proof.native_map_sha256):
                raise ReceiptRefused("stopped_learning_zero_not_sealed")
            expected_epoch = {
                "schema": 3, "kind": "original-native-learning-epoch",
                "generation": proof.generation,
                "operation_id": proof.operation_id,
                "owner_candidate_sha256": proof.owner_candidate_sha256,
                "final_args_sha256": proof.final_args_sha256,
                "native_map_sha256": proof.native_map_sha256,
                "pretraffic_sha256": hashlib.sha256(zero_raw).hexdigest(),
                "owner_pid": proof.owner.pid,
                "owner_start": proof.owner.started,
                "owner_executable": proof.owner.executable,
                "files": records, "learning": learning,
                "ack_authorized": False,
            }
            if epoch != expected_epoch:
                raise ReceiptRefused("stopped_learning_epoch_not_original")
            # Immutable sources are trusted only if they stayed EXACTLY
            # identical for both passes; never re-open old producer inodes.
            if (_read(folder / "pretraffic.json", self.uid) != zero_raw or
                    _read(folder / "epoch.json", self.uid) != epoch_raw or
                    verify_seal(workspace, owner=self.uid) != seal or
                    _secure_bytes(release / "dvtws.args",
                                  MAX_ARGS, self.uid) != final or
                    _secure_bytes(release / "auto-detect-generation.json",
                                  MAX_MAP, self.uid) != native or
                    _secure_bytes(release / "dvtws.original.args",
                                  MAX_ARGS, self.uid) != original or
                    _secure_bytes(release / ORIGIN_FILE,
                                  MAX_MAP, self.uid) != source):
                raise ReceiptRefused("stopped_learning_original_epoch_raced")
            return epoch
        except ReceiptRefused:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError,
                UnicodeError, GenerationRefused, SharedBundleError) as exc:
            raise ReceiptRefused(
                "stopped_learning_epoch_not_independently_attested") from exc

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


    def _retired_plan(self, proof: GenerationProof, queue: DurableInbox,
                      tip) -> dict:
        """One immutable old-generation retirement proof; no other log."""
        from auto_detect_original_v2_prepare import DEBUG_OLD, DEBUG_NEXT
        from auto_detect_fd import FDState, probe_stopped_pending_fd
        if (queue.segments() or tip.open_folder is not None or
                tip.open_intent is not None or
                (queue.root / DEBUG_NEXT).exists() or
                (queue.root / DEBUG_NEXT).is_symlink()):
            raise ReceiptRefused("unprocessed_or_interrupted_old_source")
        snapshot = {}
        for key, path in (("inbox", queue.inbox),
                          ("debug", Path(proof.debug_path)),
                          ("previous", queue.root / DEBUG_OLD)):
            if key == "previous" and not path.exists() and not path.is_symlink():
                snapshot[key] = None
                continue
            info, data = _read_exact(path, owner_uid=self.uid,
                                     writer_gid=self.writer_gid)
            if ((key == "inbox" and data) or
                    (key != "inbox" and
                     (b"\x00" in data or (data and not data.endswith(b"\n")))) or
                    info.st_nlink != 1 or
                    probe_stopped_pending_fd(
                        path, info.st_dev, info.st_ino, owner=proof.owner,
                        writer_gid=queue.writer_gid) is not FDState.DRAINED):
                raise ReceiptRefused("old_native_source_not_drained")
            snapshot[key] = [info.st_dev, info.st_ino, len(data),
                             hashlib.sha256(data).hexdigest()]
        return {
            "schema": 1, "kind": "original-stopped-source-retirement",
            "generation": proof.generation,
            "owner_sha256": hashlib.sha256(
                _canonical(_proof_fields(proof))).hexdigest(),
            "last_ack_sha256": tip.previous_ack_sha256,
            "cycle": tip.cycle,
            "next_sequence": tip.next_sequence,
            "sources": snapshot,
        }

    def _retired_sources(self, proof: GenerationProof, queue: DurableInbox,
                         plan: dict, *, repair: bool) -> bool:
        """Atomically retire exact STOPPED old inodes without losing live names.

        The original queue lock MUST remain obtainable through every crash:
        both native producer paths stay present across every hardlink/replace.
        An immutable epoch retirement plan pins the old dev/inode/SHA before
        any source change. No copytruncate, signal, parallel Config or owner.
        """
        from auto_detect_original_v2_prepare import DEBUG_OLD, DEBUG_NEXT
        from auto_detect_queue import _stat_regular, MAX_SEGMENT
        from auto_detect_debug_window import MAX_DEBUG

        if (not isinstance(plan, dict) or
                set(plan) != {"schema", "kind", "generation", "owner_sha256",
                             "last_ack_sha256", "cycle", "next_sequence", "sources"} or
                plan["schema"] != 1 or
                plan["kind"] != "original-stopped-source-retirement" or
                plan["generation"] != proof.generation or
                plan["owner_sha256"] != hashlib.sha256(
                    _canonical(_proof_fields(proof))).hexdigest() or
                not isinstance(plan["sources"], dict) or
                set(plan["sources"]) != {"inbox", "debug", "previous"}):
            raise ReceiptRefused("unqualified_old_retirement_plan")
        folder = self._generation(proof.generation, create=False)
        if (queue.segments() or
                (queue.root / DEBUG_NEXT).exists() or
                (queue.root / DEBUG_NEXT).is_symlink()):
            raise ReceiptRefused("foreign_pending_during_old_retirement")
        mode = 0o660 if self.writer_gid is not None else 0o600
        gid = self.writer_gid if self.writer_gid is not None else self.uid

        def exact_old(path: Path, expected: list, limit: int) -> os.stat_result:
            """Pinned nofollow snapshot allows nlink=2 ONLY during torn cut."""
            named = _stat_regular(path, self.uid, max_size=limit,
                                  writer_gid=self.writer_gid)
            if named.st_nlink not in (1, 2):
                raise ReceiptRefused("foreign_retired_source_links")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                opened = os.fstat(fd)
                data = os.read(fd, limit + 1)
                after = os.fstat(fd)
            finally:
                os.close(fd)
            final = path.lstat()
            identity = lambda st: (st.st_dev, st.st_ino, st.st_size,
                                   st.st_mtime_ns, st.st_nlink,
                                   stat.S_IMODE(st.st_mode))
            if (identity(named) != identity(opened) or
                    identity(opened) != identity(after) or
                    identity(after) != identity(final) or
                    len(data) != named.st_size or
                    [named.st_dev, named.st_ino, len(data),
                     hashlib.sha256(data).hexdigest()] != expected):
                raise ReceiptRefused("retired_original_source_changed")
            return named

        def fresh_empty(path: Path) -> os.stat_result:
            info, data = _read_exact(path, owner_uid=self.uid,
                                     writer_gid=self.writer_gid)
            if (data or info.st_nlink != 1 or
                    stat.S_IMODE(info.st_mode) != mode):
                raise ReceiptRefused("untrusted_fresh_original_producer")
            return info

        for key, (live, archived) in {
            "inbox": (queue.inbox, folder / "retired-inbox.txt"),
            "debug": (Path(proof.debug_path), folder / "retired-debug.log"),
            "previous": (queue.root / DEBUG_OLD,
                         folder / "retired-debug-previous.log"),
        }.items():
            expected = plan["sources"][key]
            archive_exists = archived.exists() or archived.is_symlink()
            live_exists = live.exists() or live.is_symlink()
            if expected is None:
                if key != "previous" or live_exists or archive_exists:
                    raise ReceiptRefused("unexpected_old_debug_archive")
                continue
            if (not isinstance(expected, list) or len(expected) != 4 or
                    any(type(x) is not int or x < 0 for x in expected[:3]) or
                    expected[1] <= 0 or not isinstance(expected[3], str) or
                    not HEX64.fullmatch(expected[3])):
                raise ReceiptRefused("invalid_old_source_identity")
            limit = MAX_SEGMENT if key == "inbox" else MAX_DEBUG
            if key == "previous":
                # An old diagnostic archive is not a live producer path.
                # Its rename is safe to resume after a crash.
                if live_exists and archive_exists:
                    raise ReceiptRefused("duplicate_previous_debug_archive")
                if not archive_exists:
                    if not repair:
                        return False
                    old = exact_old(live, expected, limit)
                    if old.st_nlink != 1 or old.st_dev != folder.stat().st_dev:
                        raise ReceiptRefused("old_previous_archive_not_owned")
                    os.rename(live, archived)
                    _sync(folder)
                    _sync(queue.root)
                if exact_old(archived, expected, limit).st_nlink != 1:
                    raise ReceiptRefused("previous_debug_retired_with_open_alias")
                continue

            # Raw and native debug must NEVER disappear from queue.root,
            # including after a power loss. A prepared empty replacement
            # lives in the SAME producer directory, never in the epoch.
            if not live_exists:
                raise ReceiptRefused("old_live_source_missing")
            temp = queue.root / (".original-retire-" + key + "-ready")
            temp_exists = temp.exists() or temp.is_symlink()
            if not archive_exists:
                if not repair:
                    return False
                old = exact_old(live, expected, limit)
                if (old.st_nlink != 1 or old.st_dev != folder.stat().st_dev):
                    raise ReceiptRefused("old_live_inode_not_archive_safe")
                if not temp_exists:
                    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                 os.O_NOFOLLOW, 0o600)
                    try:
                        os.fchown(fd, self.uid, gid)
                        os.fchmod(fd, mode)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    _sync(queue.root)
                prepared = fresh_empty(temp)
                if prepared.st_dev != old.st_dev:
                    raise ReceiptRefused("replacement_not_same_filesystem")
                os.link(live, archived, follow_symlinks=False)
                _sync(folder)
                archive_exists = True

            old = exact_old(archived, expected, limit)
            current = _stat_regular(live, self.uid, max_size=limit,
                                    writer_gid=self.writer_gid)
            if (current.st_dev, current.st_ino) == (old.st_dev, old.st_ino):
                # Crash after hardlink/fsync, before atomic replace. Both
                # names point at the EXACT original bytes (nlink=2). Do
                # not unlink either one until the fresh inode is installed.
                if (not repair):
                    return False
                if current.st_nlink != 2 or old.st_nlink != 2:
                    raise ReceiptRefused("torn_original_archive_links_unsafe")
                exact_old(live, expected, limit)
                if not (temp.exists() and not temp.is_symlink()):
                    raise ReceiptRefused("missing_prepared_original_replacement")
                prepared = fresh_empty(temp)
                if prepared.st_dev != old.st_dev:
                    raise ReceiptRefused("different_original_replacement_device")
                os.replace(temp, live)
                _sync(queue.root)
                old = exact_old(archived, expected, limit)
            if old.st_nlink != 1:
                raise ReceiptRefused("retired_original_still_has_alias")
            new = fresh_empty(live)
            if (new.st_dev != old.st_dev or new.st_ino == old.st_ino or
                    temp.exists() or temp.is_symlink()):
                raise ReceiptRefused("retired_original_replacement_not_complete")
        return True

    def retire_stopped(self, proof: GenerationProof, queue: DurableInbox, *,
                       attest=None) -> bool:
        """Finish the original ACKed source lifetime before the NEXT ID.

        Required by explicit Stop/Boot only after engine and supervisor exit.
        One original epoch receipt is written BEFORE retiring any pathname.
        """
        from auto_detect_cursor_chain import CursorChain
        if (not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                not callable(attest) or attest() != proof):
            raise ReceiptRefused("stopped_original_fd9_queue_required")
        folder, _ = self._epoch(proof)
        tip = CursorChain(self, queue).tip(proof)
        if (tip.open_intent is not None or queue.segments()):
            raise ReceiptRefused("unacknowledged_old_generation")
        plan_path = folder / "retired.json"
        if plan_path.exists() or plan_path.is_symlink():
            plan = json.loads(_read(plan_path, self.uid))
            if (plan["last_ack_sha256"] != tip.previous_ack_sha256 or
                    plan["cycle"] != tip.cycle or
                    plan["next_sequence"] != tip.next_sequence):
                raise ReceiptRefused("old_source_retirement_cursor_changed")
        else:
            plan = self._retired_plan(proof, queue, tip)
            if attest() != proof or queue.segments():
                raise ReceiptRefused("old_source_changed_before_retirement")
            _write_once(folder, "retired.json", _canonical(plan), self.uid)
        if attest() != proof:
            raise ReceiptRefused("stopped_owner_changed_after_retirement_plan")
        if not self._retired_sources(proof, queue, plan, repair=True):
            raise ReceiptRefused("original_retirement_not_complete")
        if attest() != proof or not self._retired_sources(
                proof, queue, plan, repair=False):
            raise ReceiptRefused("retired_source_not_attested")
        return True

    def verify_retired(self, proof: GenerationProof, queue: DurableInbox) -> bool:
        """Read-only verification; never an authority to start the old PID."""
        from auto_detect_cursor_chain import CursorChain
        if not isinstance(queue, DurableInbox) or not queue._held:
            raise ReceiptRefused("original_retirement_queue_required")
        folder, _ = self._epoch(proof)
        tip = CursorChain(self, queue).tip(proof)
        plan_path = folder / "retired.json"
        if not (plan_path.exists() and not plan_path.is_symlink()):
            return False
        plan = json.loads(_read(plan_path, self.uid))
        if (plan.get("last_ack_sha256") != tip.previous_ack_sha256 or
                plan.get("next_sequence") != tip.next_sequence or
                plan.get("cycle") != tip.cycle):
            raise ReceiptRefused("retired_old_ack_not_final")
        return self._retired_sources(proof, queue, plan, repair=False)

    def verify_stop_only_epoch(self, proof: GenerationProof,
                               queue: DurableInbox, *,
                               attest=attest_running_generation) -> bool:
        """Permit an explicit user Stop when only ps wall-clock birth drifted.

        This is NOT the strict v2 worker / raw ACK / cursor permission. The
        original FD9 and P2a flock, CURRENT native process/argv/supervisor
        attestation, sealed generation and every epoch/pretraffic field
        except the display-only owner_start must all be genuine. The receipt
        is never repaired or replaced. A different owner, missing evidence,
        stale callback or changed runtime remains refused. The caller may
        sacrifice uncommitted discovery during normal Stop, never Config,
        manual/known HOSTLIST, IPFW owner or the actual engine census.
        """
        if (not isinstance(queue, DurableInbox) or not queue._held or
                queue.uid != self.uid or queue.writer_gid != self.writer_gid or
                not callable(attest) or not isinstance(proof, GenerationProof)):
            raise ReceiptRefused("stop_requires_original_queue_and_owner")
        if sys.platform.startswith("freebsd"):
            from voice_ipfw_adapter import require_lifecycle_lock
            require_lifecycle_lock()
        if attest() != proof:
            raise ReceiptRefused("stop_owner_changed_before_epoch_read")
        queue._verify()
        folder, seed, seed_raw = self._pretraffic(proof)
        try:
            actual = json.loads(_read(folder / "epoch.json", self.uid))
        except (ValueError, UnicodeError, TypeError) as exc:
            raise ReceiptRefused("stop_epoch_unreadable") from exc
        expected = _proof_fields(proof)
        expected.update(
            owner_candidate_sha256=seed["owner_candidate_sha256"],
            pretraffic_sha256=hashlib.sha256(seed_raw).hexdigest(),
            raw_device=seed["raw_device"], raw_inode=seed["raw_inode"],
            debug_device=seed["debug_device"],
            debug_inode=seed["debug_inode"],
            committed_cursor_offset=0,
            committed_cursor_sha256=EMPTY_HASH,
        )
        if (not isinstance(actual, dict) or
                set(actual) != set(expected) or
                type(actual.get("owner_start")) is not str or
                _START.fullmatch(actual["owner_start"]) is None or
                any(actual.get(key) != value for key, value in expected.items()
                    if key != "owner_start")):
            raise ReceiptRefused("stop_epoch_not_same_original_owner")
        # A second live attestation closes the window between checking the
        # root-private receipts and the normal process/IPFW stop preflight.
        queue._verify()
        if attest() != proof:
            raise ReceiptRefused("stop_owner_changed_after_epoch_read")
        return actual["owner_start"] != expected["owner_start"]

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
