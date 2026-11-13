#!/usr/bin/env python3
"""#1052 P2 queue primitive, dormant until native attribution is integrated.

One short locked cycle: recover pending -> hardlink old inbox -> atomically
replace inbox -> wait for independent writer-FD and result-commit proofs -> ack.
No Config, daemon, GUI, runtime or managed HOSTLIST writes in this module.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import secrets
import stat

MAX_PENDING = 512
MAX_SEGMENT = 4 * 1024 * 1024


class QueueSafetyError(RuntimeError):
    """A content-free failure; never delete or truncate unacknowledged input."""


def _stat_regular(path: Path, uid: int, *, max_size: int | None = None) -> os.stat_result:
    result = path.lstat()  # no symlink following
    if not stat.S_ISREG(result.st_mode) or result.st_uid != uid or result.st_mode & 0o022:
        raise QueueSafetyError("unsafe_file")
    if max_size is not None and result.st_size > max_size:
        raise QueueSafetyError("oversized_segment")
    return result


def _check_directory(path: Path, uid: int) -> None:
    result = path.lstat()
    if not stat.S_ISDIR(result.st_mode) or result.st_uid != uid or result.st_mode & 0o077:
        raise QueueSafetyError("unsafe_directory")


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _identity(path: Path) -> tuple[int, int]:
    result = path.lstat()
    return result.st_dev, result.st_ino


class DurableInbox:
    def __init__(self, root: Path, *, owner_uid: int = 0):
        self.root = Path(root)
        self.pending = self.root / "pending"
        self.inbox = self.root / "inbox.txt"
        self.lock = self.root / "worker.lock"
        self.uid = owner_uid
        self._held = False

    def _require_lock(self) -> None:
        if not self._held:
            raise QueueSafetyError("worker_lock_required")

    def _verify(self) -> None:
        # Parent must be a trusted root-owned directory too; do not create a
        # hierarchy in worker or silently traverse a symlink-controlled state.
        _check_directory(self.root.parent, self.uid)
        _check_directory(self.root, self.uid)
        _check_directory(self.pending, self.uid)
        if self.root.stat().st_dev != self.pending.stat().st_dev:
            raise QueueSafetyError("cross_device_pending")
        _stat_regular(self.inbox, self.uid)

    @contextmanager
    def exclusive(self):
        self._verify()
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            _stat_regular(self.lock, self.uid)
            if os.fstat(fd).st_ino != self.lock.lstat().st_ino or os.fstat(fd).st_nlink != 1:
                raise QueueSafetyError("lock_replaced")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise QueueSafetyError("worker_busy") from None
            self._verify()
            if self._held:
                raise QueueSafetyError("already_locked")
            self._held = True
            try:
                yield self
            finally:
                self._held = False
        finally:
            os.close(fd)

    def segments(self) -> list[Path]:
        self._require_lock()
        self._verify()
        files = sorted(self.pending.iterdir())
        if len(files) > MAX_PENDING:
            raise QueueSafetyError("pending_limit")
        for path in files:
            if not path.name.endswith(".txt") or path.name.startswith("."):
                raise QueueSafetyError("unknown_pending_entry")
            _stat_regular(path, self.uid)
        return files

    def rotate(self) -> Path | None:
        """Must be called under exclusive(); recover link-before-replace."""
        self._require_lock()
        self._verify()
        old = _stat_regular(self.inbox, self.uid)
        existing = self.segments()
        same = [path for path in existing if _identity(path) == (old.st_dev, old.st_ino)]
        if len(same) > 1:
            raise QueueSafetyError("duplicate_live_hardlinks")
        if same:
            if old.st_nlink != 2:
                raise QueueSafetyError("unexpected_live_links")
            segment = same[0]
        else:
            if not old.st_size:
                return None
            if old.st_nlink != 1 or len(existing) >= MAX_PENDING:
                raise QueueSafetyError("unsafe_inbox_links_or_capacity")
            segment = self.pending / (secrets.token_hex(16) + ".txt")
        # A new inode is fully synced before the live name is replaced.
        temp = self.root / (".new-inbox-" + secrets.token_hex(16))
        fd = None
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, old.st_mode & 0o777)
            os.fchown(fd, old.st_uid, old.st_gid)
            os.fsync(fd)
            os.close(fd)
            fd = None
            if not same:
                if _identity(self.inbox) != (old.st_dev, old.st_ino):
                    raise QueueSafetyError("inbox_changed_before_link")
                os.link(self.inbox, segment, follow_symlinks=False)
                if _identity(segment) != (old.st_dev, old.st_ino) or segment.lstat().st_nlink != 2:
                    raise QueueSafetyError("link_identity_changed")
                _sync_directory(self.pending)
            if _identity(self.inbox) != (old.st_dev, old.st_ino):
                raise QueueSafetyError("inbox_changed_before_replace")
            os.replace(temp, self.inbox)
            _sync_directory(self.root)
            return segment
        finally:
            if fd is not None:
                os.close(fd)
            if temp.exists():
                temp.unlink()
                _sync_directory(self.root)

    def acknowledge(self, segment: Path, *, drained, committed) -> bool:
        """Both callbacks must independently prove safety, not just return data.

        drained(path, dev, inode) must be backed by native owner/FD evidence.
        committed(bytes) must durably persist *every* event/result and return
        True only when the complete segment can be acknowledged. Neither is
        supplied by this P2 queue primitive: fail closed until integrated.
        """
        self._require_lock()
        if not callable(drained) or not callable(committed):
            raise QueueSafetyError("missing_drain_or_commit_proof")
        self._verify()
        segment = Path(segment)
        if segment.parent != self.pending or segment not in self.segments():
            raise QueueSafetyError("foreign_segment")
        before = _stat_regular(segment, self.uid, max_size=MAX_SEGMENT)
        if _identity(self.inbox) == (before.st_dev, before.st_ino):
            return False  # crash after hardlink, before replace
        if before.st_nlink != 1:
            raise QueueSafetyError("unaccounted_pending_links")
        if not drained(segment, before.st_dev, before.st_ino):
            return False
        fd = os.open(segment, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            if (os.fstat(fd).st_dev, os.fstat(fd).st_ino) != (before.st_dev, before.st_ino):
                raise QueueSafetyError("pending_changed")
            data = os.read(fd, MAX_SEGMENT + 1)
        finally:
            os.close(fd)
        if len(data) > MAX_SEGMENT or (data and not data.endswith(b"\n")):
            return False  # never discard incomplete last line
        if not committed(data):
            return False
        after = _stat_regular(segment, self.uid, max_size=MAX_SEGMENT)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            return False  # idempotent callback may have persisted; retry
        segment.unlink()
        _sync_directory(self.pending)
        return True


def main() -> int:
    # Deliberately no cron/production invocation before P2 native map and FD
    # attestation integration. This module is importable by focused tests only.
    raise SystemExit("P2 queue primitive is not a standalone production worker")


if __name__ == "__main__":
    main()
