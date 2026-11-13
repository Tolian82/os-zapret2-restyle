#!/usr/bin/env python3
"""#1052 P2k2b: dormant crash-replay-safe HOSTLIST destination transaction.

This is not a native worker or an FD/owner attester. The trusted caller must
hold the queue lock, prove original generation and drained writer FD, and
coordinate every GUI writer on the supplied destination lock. No ack here.
"""
from __future__ import annotations

from contextlib import contextmanager

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused, _canonical, _read, _sync, _write_once, _directory
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox

MAX_TARGET = 4 * 1024 * 1024
HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\Z")


class DestinationRefused(ReceiptRefused):
    """The unacknowledged source stays retained on any unsafe destination."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _target(path: Path, uid: int) -> tuple[bytes, os.stat_result]:
    """Strict regular-file snapshot; never trust a symlink or a stale FD."""
    try:
        parent = path.parent.lstat()
        st = path.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
                parent.st_mode & 0o022 or
                not stat.S_ISREG(st.st_mode) or st.st_uid != uid or
                st.st_nlink != 1 or st.st_mode & 0o022 or
                st.st_size > MAX_TARGET):
            raise DestinationRefused("unsafe_destination")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            a = os.fstat(fd)
            data = os.read(fd, MAX_TARGET + 1)
            b = os.fstat(fd)
        finally:
            os.close(fd)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_mode)
        if identity(st) != identity(a) or identity(a) != identity(b) or len(data) != st.st_size:
            raise DestinationRefused("destination_changed_during_read")
        data.decode("utf-8")
        return data, st
    except (OSError, UnicodeError) as exc:
        raise DestinationRefused("destination_read_failed") from exc


def _edit(before: bytes, add: list[str], remove: list[str]) -> bytes:
    if (not isinstance(add, list) or not isinstance(remove, list) or
            len(add) + len(remove) > 4096 or
            any(type(x) is not str or not HOST.fullmatch(x) or ".." in x
                for x in add + remove)):
        raise DestinationRefused("invalid_domain_effects")
    text = before.decode("utf-8")
    # Preserve every non-owned modifier, comment and existing user row verbatim.
    lines = text.splitlines(keepends=True)
    removed = set(remove)
    out = [line for line in lines if line.rstrip("\r\n") not in removed]
    present = {line.rstrip("\r\n") for line in out}
    for host in sorted(set(add)):
        if host not in present:
            if out and not out[-1].endswith("\n"):
                out.append("\n")
            out.append(host + "\n")
            present.add(host)
    result = "".join(out).encode("utf-8")
    if len(result) > MAX_TARGET:
        raise DestinationRefused("destination_growth_limit")
    return result


def _replace(path: Path, current: bytes, expected: bytes, uid: int) -> None:
    """One protected same-directory replace after read-side CAS under GUI lock."""
    now, st = _target(path, uid)
    if now != current:
        raise DestinationRefused("destination_conflict_with_gui")
    temp = path.parent / (".auto-detect-" + secrets.token_hex(16) + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchown(fd, st.st_uid, st.st_gid)
        os.fchmod(fd, stat.S_IMODE(st.st_mode))
        data = memoryview(expected)
        while data:
            n = os.write(fd, data)
            if n <= 0:
                raise DestinationRefused("short_destination_write")
            data = data[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    # Writers that ignore the shared GUI lock are not trusted. Recheck before
    # replace; the next GUI implementation MUST acquire this same lock.
    try:
        again, check = _target(path, uid)
        if again != current or (check.st_dev, check.st_ino) != (st.st_dev, st.st_ino):
            raise DestinationRefused("destination_conflict_with_gui")
        os.replace(temp, path)
        _sync(path.parent)
    finally:
        if temp.exists():
            temp.unlink()
            _sync(path.parent)



@contextmanager
def exclusive_destination_lock(gui_lock: Path, owner_uid: int):
    """Shared native root flock for GUI save/read and P2k4 destination writes.

    This lock is intentionally independent of queue/FD9/Config locks; GUI
    edits neither assume nor acquire authority to mutate config.xml.
    """
    path = Path(gui_lock)
    if not path.is_absolute():
        raise DestinationRefused("unsafe_gui_lock_path")
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != owner_uid
            or parent.st_mode & 0o022):
        raise DestinationRefused("unsafe_gui_lock_directory")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        name = path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != owner_uid or
                stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or
                (st.st_dev, st.st_ino) != (name.st_dev, name.st_ino)):
            raise DestinationRefused("unsafe_gui_lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DestinationRefused("gui_writer_busy") from None
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class DestinationCommit:
    """A prepared-intent journal: prepare -> per-file CAS -> checkpoint.

    The caller's owner/FD proofs are NOT implied by this API. No automatic
    invocation is installed. The queue lock must be held for every call, and
    GUI must use the same external lock before P3 enables native writes.
    """

    def __init__(self, receipts: EpochReceipts, queue: DurableInbox,
                 targets: dict[str, Path], gui_lock: Path):
        self.receipts, self.queue = receipts, queue
        self.targets = {k: Path(v) for k, v in targets.items()}
        self.gui_lock = Path(gui_lock)
        if (not self.targets or "auto" not in self.targets or
                any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", k)
                    for k in self.targets) or
                len(set(self.targets.values())) != len(self.targets) or
                any(not p.is_absolute() for p in self.targets.values()) or
                not self.gui_lock.is_absolute() or
                self.gui_lock in self.targets.values()):
            raise DestinationRefused("unqualified_destination_mapping")

    def _source(self, proof: GenerationProof, pending: Path) -> tuple[Path, dict, bytes]:
        folder, _ = self.receipts._epoch(proof)
        h = self.receipts.historical(proof.generation)
        intent = h.intent
        if (intent is None or not isinstance(pending, Path) or
                pending.parent != self.queue.pending or
                intent.get("pending_name") != pending.name or
                pending.name[:32] != proof.generation or
                not self.queue._held):
            raise DestinationRefused("no_locked_original_pending_intent")
        try:
            stat_before = pending.lstat()
            fd = os.open(pending, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                st = os.fstat(fd)
                raw = os.read(fd, MAX_TARGET + 1)
                after = os.fstat(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            raise DestinationRefused("pending_read_failed") from exc
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
        if (identity(stat_before) != identity(st) or identity(st) != identity(after) or
                not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
                st.st_uid != self.receipts.uid or
                stat.S_IMODE(st.st_mode) != (0o600 if self.queue.writer_gid is None else 0o660) or
                (self.queue.writer_gid is not None and st.st_gid != self.queue.writer_gid) or
                st.st_size != len(raw) or
                (st.st_dev, st.st_ino, st.st_size, _sha(raw)) !=
                (intent["pending_device"], intent["pending_inode"],
                 intent["pending_size"], intent["pending_sha256"])):
            raise DestinationRefused("pending_differs_from_original_intent")
        return folder, intent, raw

    def commit(self, proof: GenerationProof, pending: Path,
               effects: dict[str, dict[str, list[str]]]) -> dict:
        """Record effects only after an independently attested P1 decision.

        Explicit changes must already exclude manual-owned rows. This detached
        primitive cannot derive original native attribution or authorize ack.
        """
        folder, intent, raw = self._source(proof, Path(pending))
        if (not isinstance(effects, dict) or
                any(k not in self.targets or not isinstance(e, dict) or
                    set(e) != {"add", "remove"} or
                    (k == "auto" and bool(e["remove"]))
                    for k, e in effects.items())):
            raise DestinationRefused("unqualified_effects")
        with self.exclusive_targets():
            return self._locked_commit(folder, intent, raw, effects)

    @contextmanager
    def exclusive_targets(self):
        """Lock the P1 snapshot and P2k2b CAS under the same root flock."""
        if getattr(self, "_gui_held", False):
            raise DestinationRefused("gui_lock_already_held")
        with exclusive_destination_lock(self.gui_lock, self.receipts.uid):
            self._gui_held = True
            try:
                yield self
            finally:
                self._gui_held = False

    def _locked_commit(self, folder: Path, intent: dict, raw: bytes,
                       effects: dict) -> dict:
        if not getattr(self, "_gui_held", False):
            raise DestinationRefused("gui_lock_required")
        journal = folder / "destination"
        if not journal.exists() and not journal.is_symlink():
            journal.mkdir(mode=0o700)
            _sync(folder)
        _directory(journal, self.receipts.uid)
        names = set(os.listdir(journal))
        if names - {"plan.json", "checkpoint.json"}:
            raise DestinationRefused("foreign_destination_receipts")
        plan_path, checkpoint_path = journal / "plan.json", journal / "checkpoint.json"
        if "plan.json" not in names:
            writes = {}
            for name, change in sorted(effects.items()):
                path = self.targets[name]
                before, _ = _target(path, self.receipts.uid)
                after = _edit(before, change["add"], change["remove"])
                writes[name] = {"path": str(path), "before": _sha(before),
                                "after": _sha(after), "add": change["add"],
                                "remove": change["remove"]}
            plan = {"schema": 1, "kind": "durable-destination-plan",
                    "generation": intent["generation"],
                    "pending_name": intent["pending_name"],
                    "pending_sha256": intent["pending_sha256"],
                    "debug_end_offset": intent["debug_end_offset"],
                    "debug_end_sha256": intent["debug_end_sha256"],
                    "writes": writes}
            _write_once(journal, "plan.json", _canonical(plan), self.receipts.uid)
        plan_raw = _read(plan_path, self.receipts.uid)
        try:
            plan = json.loads(plan_raw)
        except ValueError as exc:
            raise DestinationRefused("corrupt_destination_plan") from exc
        if (not isinstance(plan, dict) or plan.get("kind") != "durable-destination-plan" or
                any(plan.get(k) != intent[k] for k in (
                    "generation", "pending_name", "pending_sha256",
                    "debug_end_offset", "debug_end_sha256")) or
                not isinstance(plan.get("writes"), dict)):
            raise DestinationRefused("destination_plan_identity_changed")
        if checkpoint_path.exists() or checkpoint_path.is_symlink():
            checkpoint = json.loads(_read(checkpoint_path, self.receipts.uid))
            if (checkpoint.get("plan_sha256") != _sha(plan_raw) or
                    checkpoint.get("committed_cursor_offset") != intent["debug_end_offset"] or
                    checkpoint.get("committed_cursor_sha256") != intent["debug_end_sha256"]):
                raise DestinationRefused("checkpoint_differs_from_plan")
            return checkpoint  # never undo later GUI deletion on acknowledged replay
        for name, change in sorted(plan["writes"].items()):
            if (name not in self.targets or change.get("path") != str(self.targets[name]) or
                    any(k not in change for k in ("before", "after", "add", "remove"))):
                raise DestinationRefused("destination_plan_target_changed")
            path = self.targets[name]
            current, _ = _target(path, self.receipts.uid)
            if _sha(current) == change["after"]:
                continue  # completed before crash; never append twice
            if _sha(current) != change["before"]:
                raise DestinationRefused("destination_conflict_with_gui")
            new = _edit(current, change["add"], change["remove"])
            if _sha(new) != change["after"]:
                raise DestinationRefused("destination_plan_diverged")
            _replace(path, current, new, self.receipts.uid)
        checkpoint = {"schema": 1, "kind": "destination-and-cursor-committed",
                      "generation": intent["generation"], "pending_name": intent["pending_name"],
                      "plan_sha256": _sha(plan_raw),
                      "committed_cursor_offset": intent["debug_end_offset"],
                      "committed_cursor_sha256": intent["debug_end_sha256"],
                      "ack_authorized": False}
        _write_once(journal, "checkpoint.json", _canonical(checkpoint), self.receipts.uid)
        return checkpoint


def run_native_destination_writer() -> None:
    raise DestinationRefused("original_owner_fd_and_gui_writer_not_integrated")