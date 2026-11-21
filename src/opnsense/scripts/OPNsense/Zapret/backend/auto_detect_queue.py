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
import re
import stat

MAX_PENDING = 512
MAX_SEGMENT = 4 * 1024 * 1024
# Native old inodes share the original P2a pending directory, but MUST
# never be interpreted as the raw inbox batch by the original raw ACK.
NATIVE_PENDING = re.compile(r"native-([0-9a-f]{32})-([1-9][0-9]{0,2})-([0-9a-f]{32})\.txt\Z")


class QueueSafetyError(RuntimeError):
    """A content-free failure; never delete or truncate unacknowledged input."""


def _stat_regular(path: Path, uid: int, *, max_size: int | None = None,
                  writer_gid: int | None = None) -> os.stat_result:
    result = path.lstat()  # no symlink following
    if not stat.S_ISREG(result.st_mode) or result.st_uid != uid:
        raise QueueSafetyError("unsafe_file")
    if writer_gid is None:
        if result.st_mode & 0o022:
            raise QueueSafetyError("unsafe_file")
    elif (result.st_gid != writer_gid or
          stat.S_IMODE(result.st_mode) != 0o660):
        # Only the explicitly qualified nobody-group producer inode is
        # group-writable. Old pending hardlinks retain this exact mode.
        raise QueueSafetyError("unsafe_native_producer_file")
    if max_size is not None and result.st_size > max_size:
        raise QueueSafetyError("oversized_segment")
    return result


def _check_directory(path: Path, uid: int) -> None:
    result = path.lstat()
    if not stat.S_ISDIR(result.st_mode) or result.st_uid != uid or result.st_mode & 0o077:
        raise QueueSafetyError("unsafe_directory")


def _check_producer_root(path: Path, uid: int, gid: int) -> None:
    parent = path.parent.lstat()
    root = path.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid
            or parent.st_mode & 0o022 or not parent.st_mode & 0o001
            or not stat.S_ISDIR(root.st_mode) or root.st_uid != uid
            or root.st_gid != gid or stat.S_IMODE(root.st_mode) != 0o710):
        raise QueueSafetyError("unsafe_native_producer_directory")


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
    def __init__(self, root: Path, *, owner_uid: int = 0,
                 writer_gid: int | None = None):
        self.root = Path(root)
        self.pending = self.root / "pending"
        self.inbox = self.root / "inbox.txt"
        self.lock = self.root / "worker.lock"
        self.uid = owner_uid
        if writer_gid is not None and (type(writer_gid) is not int or writer_gid <= 0):
            raise QueueSafetyError("unqualified_native_writer_group")
        self.writer_gid = writer_gid
        self._held = False
        self._lock_fd: int | None = None

    @property
    def locked_fd(self) -> int:
        """The already-held original queue FD, for a same-OFD native child."""
        self._require_lock()
        if self._lock_fd is None:
            raise QueueSafetyError("no_original_queue_fd")
        return self._lock_fd

    def _require_lock(self) -> None:
        if not self._held:
            raise QueueSafetyError("worker_lock_required")

    def _verify(self) -> None:
        # Parent must be a trusted root-owned directory too; do not create a
        # hierarchy in worker or silently traverse a symlink-controlled state.
        if self.writer_gid is None:
            _check_directory(self.root.parent, self.uid)
            _check_directory(self.root, self.uid)
        else:
            _check_producer_root(self.root, self.uid, self.writer_gid)
        _check_directory(self.pending, self.uid)
        if self.root.stat().st_dev != self.pending.stat().st_dev:
            raise QueueSafetyError("cross_device_pending")
        _stat_regular(self.inbox, self.uid, writer_gid=self.writer_gid)

    @contextmanager
    def exclusive(self):
        self._verify()
        # A new FreeBSD file inherits the parent directory group (nobody).
        # The ONE original P2a queue lock is instead root:root 0600.
        # Never reown or repair an EXISTING lock: reject all foreign state.
        fresh = False
        try:
            fd = os.open(self.lock, os.O_CREAT | os.O_EXCL |
                         os.O_RDWR | os.O_NOFOLLOW, 0o600)
            fresh = True
        except FileExistsError:
            fd = os.open(self.lock, os.O_RDWR | os.O_NOFOLLOW)
        try:
            if fresh:
                expected_gid = self.pending.lstat().st_gid
                if os.fstat(fd).st_gid != expected_gid:
                    os.fchown(fd, -1, expected_gid)
                os.fchmod(fd, 0o600)
                os.fsync(fd)
                _sync_directory(self.root)
            named = _stat_regular(self.lock, self.uid)
            if self.writer_gid is not None and (
                    named.st_gid != self.pending.lstat().st_gid or
                    stat.S_IMODE(named.st_mode) != 0o600):
                raise QueueSafetyError("unsafe_original_queue_lock")
            if (os.fstat(fd).st_dev, os.fstat(fd).st_ino) != (
                    named.st_dev, named.st_ino) or os.fstat(fd).st_nlink != 1:
                raise QueueSafetyError("lock_replaced")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise QueueSafetyError("worker_busy") from None
            self._verify()
            if self._held:
                raise QueueSafetyError("already_locked")
            self._held = True
            self._lock_fd = fd
            try:
                yield self
            finally:
                self._lock_fd = None
                self._held = False
        finally:
            os.close(fd)

    @contextmanager
    def inherited_exclusive(self, fd: int):
        """Borrow the ORIGINAL queue lock's inherited open-file description.

        The queue owner must already have acquired exclusive() in the
        original parent. A child must not try to take a second queue lock:
        that would deadlock the queue -> OPNsense Config -> target order.
        An unrelated or unlocked descriptor cannot impersonate this one.
        """
        if type(fd) is not int or fd < 3 or self._held:
            raise QueueSafetyError("unqualified_inherited_queue_fd")
        self._verify()
        try:
            held = os.fstat(fd)
            named = _stat_regular(self.lock, self.uid)
            if (self.writer_gid is not None and
                    (named.st_gid != self.pending.lstat().st_gid or
                     stat.S_IMODE(named.st_mode) != 0o600)):
                raise QueueSafetyError("unsafe_original_queue_lock")
            if (not stat.S_ISREG(held.st_mode) or
                    (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino) or
                    held.st_uid != self.uid or held.st_nlink != 1):
                raise QueueSafetyError("inherited_queue_inode_mismatch")
            # A separate open description MUST be blocked: otherwise a
            # caller could smuggle an unlocked descriptor into this API.
            separate = os.open(self.lock, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                try:
                    fcntl.flock(separate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    fcntl.flock(separate, fcntl.LOCK_UN)
                    raise QueueSafetyError("inherited_queue_was_not_locked")
            finally:
                os.close(separate)
            # A dup/inherited original lock succeeds; a competing, unrelated
            # open description does not. Never call LOCK_UN on this FD:
            # the original queue owner continues to hold it through PHP.
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise QueueSafetyError("foreign_queue_open_description") from None
            self._verify()
            self._lock_fd = fd
            self._held = True
            try:
                yield self
            finally:
                self._held = False
                self._lock_fd = None
        except OSError as exc:
            raise QueueSafetyError("inherited_queue_fd_unavailable") from exc

    def segments(self) -> list[Path]:
        self._require_lock()
        self._verify()
        files = sorted(self.pending.iterdir())
        if len(files) > MAX_PENDING:
            raise QueueSafetyError("pending_limit")
        for path in files:
            if not path.name.endswith(".txt") or path.name.startswith("."):
                raise QueueSafetyError("unknown_pending_entry")
            if path.name.startswith("native-"):
                match = NATIVE_PENDING.fullmatch(path.name)
                if match is None or int(match[2]) > 255:
                    raise QueueSafetyError("foreign_native_pending_name")
            _stat_regular(path, self.uid, writer_gid=self.writer_gid)
        return files

    def rotate(self, *, generation: str | None = None,
               cycle: int | None = None, sequence: int | None = None) -> Path | None:
        """Unchanged original raw P2a rotation, via its ONE inode primitive."""
        return self._rotate_original_source(
            self.inbox, replacement=b"", generation=generation,
            cycle=cycle, sequence=sequence,
        )

    def _rotate_original_source(
            self, source: Path, *, replacement: bytes,
            generation: str | None = None,
            cycle: int | None = None, sequence: int | None = None,
            expected_identity: tuple[int, int] | None = None,
            sealed_prefix: tuple[int, str] | None = None,
            expected_native_image: tuple[int, str] | None = None,
            native_pending_name: str | None = None,
    ) -> Path | None:
        """Same P2a protected hardlink→replace for one original source inode.

        The ordinary raw inbox uses the ORIGINAL public rotate(), unchanged.
        A native learning source MUST be one of this producer generation's
        original root files with original epoch dev/inode, sealed PREFIX and
        EXACT full source SHA/size already authorized by the P1 snapshot.
        The caller (original Config+FD9/GUI WAL owner) must qualify any
        removed known rows and a durable Found+managed checkpoint BEFORE
        calling this INTERNAL physical primitive. No such product caller is
        registered yet. This retains every old byte, including a concurrent
        late append on an open producer FD, through a root-only original
        P2a pending hardlink. This NEVER unlinks or ACKs that pending inode.

        Replacing a native working HOSTLIST changes its visible inode.
        Later crash/retirement must reconcile the retained old inode using
        the same original generation's WAL; this primitive cannot authorize
        that higher-level transition or reset the engine's in-memory state.
        """
        if generation is not None and (type(generation) is not str or
                                       re.fullmatch(r"[a-f0-9]{32}", generation) is None):
            raise QueueSafetyError("invalid_producer_generation")
        if ((cycle is None) != (sequence is None) or
                (cycle is not None and (
                    generation is None or type(cycle) is not int or
                    type(sequence) is not int or
                    not 0 <= cycle < (1 << 32) or
                    not 0 <= sequence < (1 << 24)))):
            raise QueueSafetyError("invalid_original_cursor_cycle")
        self._require_lock()
        self._verify()
        # The original v2 reader and physical ACK both refuse >4 MiB.
        # Qualify the live raw inode BEFORE creating a hardlink/replacing
        # the writer's path. Otherwise a too-large unprocessable event batch
        # is detached and indefinitely blocks later current-generation ACK.
        # This is bounded backpressure, NOT permission to discard/truncate
        # or claim that large native appends after rotation are impossible.
        old = _stat_regular(source, self.uid, max_size=MAX_SEGMENT,
                            writer_gid=self.writer_gid)
        if (not isinstance(source, Path) or not source.is_absolute()
                or source.parent != self.root or
                type(replacement) is not bytes or
                len(replacement) > MAX_SEGMENT or
                (replacement and not replacement.endswith(b"\n"))):
            raise QueueSafetyError("original_source_or_replacement_invalid")
        is_native = source != self.inbox
        if is_native:
            from auto_detect_storage import LEARNING_NAME
            import hashlib
            found = LEARNING_NAME.fullmatch(source.name)
            if (found is None or generation is None or
                    found[1] != generation or int(found[2]) > 255 or
                    expected_identity is None or
                    len(expected_identity) != 2 or
                    any(type(item) is not int or item <= 0
                        for item in expected_identity) or
                    sealed_prefix is None or
                    len(sealed_prefix) != 2 or
                    expected_native_image is None or
                    (native_pending_name is not None and (
                        type(native_pending_name) is not str or
                        NATIVE_PENDING.fullmatch(native_pending_name) is None or
                        not native_pending_name.startswith(
                            f"native-{generation}-{found[2]}-"))) or
                    type(expected_native_image) is not tuple or
                    len(expected_native_image) != 2 or
                    type(expected_native_image[0]) is not int or
                    not 0 <= expected_native_image[0] <= MAX_SEGMENT or
                    type(expected_native_image[1]) is not str or
                    re.fullmatch(r"[0-9a-f]{64}",
                                 expected_native_image[1]) is None or
                    type(sealed_prefix[0]) is not int or
                    not 0 <= sealed_prefix[0] <= MAX_SEGMENT or
                    type(sealed_prefix[1]) is not str or
                    re.fullmatch(r"[0-9a-f]{64}", sealed_prefix[1]) is None):
                raise QueueSafetyError("native_source_original_epoch_required")
        elif (replacement or expected_identity is not None or
              sealed_prefix is not None or expected_native_image is not None or
              native_pending_name is not None):
            raise QueueSafetyError("original_raw_rotation_must_remain_unchanged")
        if is_native:
            if (old.st_dev, old.st_ino) != expected_identity:
                raise QueueSafetyError("native_original_inode_changed")
            # The original P2b+WAL owner must additionally attest current
            # FD ownership. This read only ensures our physical inode and
            # byte-accurate cut cannot diverge from THAT sealed epoch.
            fd_probe = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                probe = os.fstat(fd_probe)
                if ((probe.st_dev, probe.st_ino) != expected_identity or
                        probe.st_size > MAX_SEGMENT):
                    raise QueueSafetyError("native_read_inode_changed")
                old_bytes = bytearray()
                while len(old_bytes) <= MAX_SEGMENT:
                    piece = os.read(fd_probe, MAX_SEGMENT + 1 - len(old_bytes))
                    if not piece:
                        break
                    old_bytes.extend(piece)
                old_bytes = bytes(old_bytes)
            finally:
                os.close(fd_probe)
            # Prefix-only evidence authenticates a historical event, NOT
            # the full working file chosen by original P1 for compaction.
            # Never accept an append that happened between P1's source
            # snapshot and this physical mutation, even when it leaves
            # generation, device, inode and historical prefix unchanged.
            if (len(old_bytes) != expected_native_image[0] or
                    hashlib.sha256(old_bytes).hexdigest() !=
                    expected_native_image[1]):
                raise QueueSafetyError("native_full_preimage_changed")
            if (len(old_bytes) != old.st_size or
                    old.st_size and not old_bytes.endswith(b"\n") or
                    sealed_prefix[0] > len(old_bytes) or
                    hashlib.sha256(old_bytes[:sealed_prefix[0]]).hexdigest()
                    != sealed_prefix[1] or
                    sealed_prefix[0] and old_bytes[sealed_prefix[0] - 1:
                                                    sealed_prefix[0]] != b"\n"):
                raise QueueSafetyError("native_original_prefix_not_sealed")
            # All retained rows must be an ordered SUBSEQUENCE of complete
            # original native lines. Removed rows still remain in pending.
            # The original P1/active managed WAL, NOT this helper, determines
            # which (if any) rows are actually eligible for removal.
            lines = old_bytes.splitlines(keepends=True)
            kept = replacement.splitlines(keepends=True)
            index = 0
            for row in kept:
                while index < len(lines) and lines[index] != row:
                    index += 1
                if index == len(lines):
                    raise QueueSafetyError("native_replacement_not_original_subset")
                index += 1
            if replacement and not old_bytes:
                raise QueueSafetyError("native_replacement_outside_original")
            # Upstream zapret2 v1.0.7 compares only mtime+SIZE in its
            # file_mod_signature, not inode. A real native compaction MUST
            # shrink the working image to guarantee same-PID reload even
            # when a replacement happens inside one timestamp quantum.
            if len(replacement) >= len(old_bytes):
                raise QueueSafetyError("native_compaction_must_shrink_hostlist")

        if is_native and (old.st_dev, old.st_ino) != expected_identity:
            raise QueueSafetyError("native_original_inode_changed")
        existing = self.segments()
        same = [path for path in existing if _identity(path) == (old.st_dev, old.st_ino)]
        if len(same) > 1:
            raise QueueSafetyError("duplicate_live_hardlinks")
        if same:
            if old.st_nlink != 2:
                raise QueueSafetyError("unexpected_live_links")
            segment = same[0]
            if generation is not None:
                expected_tag = (f"native-{generation}-{found[2]}-"
                                if is_native else generation + "-")
                if not segment.name.startswith(expected_tag):
                    raise QueueSafetyError("crash_recovery_generation_changed")
            if old.st_size == 0:
                # Interrupted link() before replace() with no raw event.
                # This is only a second NAME for the live inode, not a
                # detached pending batch. Removing the extra hardlink is
                # safe even if dvtws2 appends concurrently: its bytes stay
                # reachable through the original inbox name and open FD.
                # Never unlink an independently detached empty segment.
                live = _stat_regular(source, self.uid, writer_gid=self.writer_gid)
                alias = _stat_regular(segment, self.uid, writer_gid=self.writer_gid)
                if ((live.st_dev, live.st_ino) != (old.st_dev, old.st_ino) or
                        (alias.st_dev, alias.st_ino) != (old.st_dev, old.st_ino) or
                        live.st_nlink != 2 or alias.st_nlink != 2 or
                        live.st_size != 0 or alias.st_size != 0):
                    raise QueueSafetyError("empty_live_alias_changed")
                segment.unlink()
                _sync_directory(self.pending)
                remaining = _stat_regular(source, self.uid,
                                          writer_gid=self.writer_gid)
                if ((remaining.st_dev, remaining.st_ino) !=
                        (old.st_dev, old.st_ino) or remaining.st_nlink != 1):
                    raise QueueSafetyError("empty_live_alias_recovery_uncertain")
                return None
        else:
            if not old.st_size:
                return None
            if old.st_nlink != 1 or len(existing) >= MAX_PENDING:
                raise QueueSafetyError("unsafe_inbox_links_or_capacity")
            if is_native:
                # Original P2a directory, distinct profile-bound retained
                # class; never accepted by original raw acknowledge().
                segment = self.pending / (
                    native_pending_name if native_pending_name is not None
                    else f"native-{generation}-{found[2]}-"
                         f"{secrets.token_hex(16)}.txt")
            else:
                suffix = (f"{cycle:08x}{sequence:06x}{secrets.token_hex(9)}"
                          if cycle is not None else secrets.token_hex(16))
                segment = self.pending / (
                    (generation + "-" if generation is not None else "") +
                    suffix + ".txt")
        # A changed source cannot silently borrow an alias of a different
        # native profile or a different source generation. All aliases are
        # validated by the original segments() and by exact old inode.
        if is_native and same and (
                NATIVE_PENDING.fullmatch(same[0].name) is None or
                not same[0].name.startswith(
                    f"native-{generation}-{found[2]}-") or
                (native_pending_name is not None and
                 same[0].name != native_pending_name)):
            raise QueueSafetyError("native_foreign_pending_alias")
        # A new inode is fully synced before the live name is replaced.
        temp = self.root / (".new-inbox-" + secrets.token_hex(16))
        fd = None
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, old.st_mode & 0o777)
            os.fchown(fd, old.st_uid, old.st_gid)
            # Creation umask must not strip the qualified native writer's
            # exact group-write permission on the replacement inbox.
            os.fchmod(fd, old.st_mode & 0o777)
            if replacement:
                view = memoryview(replacement)
                while view:
                    count = os.write(fd, view)
                    if count <= 0:
                        raise QueueSafetyError("native_replacement_write_short")
                    view = view[count:]
            os.fsync(fd)
            os.close(fd)
            fd = None
            if not same:
                if _identity(source) != (old.st_dev, old.st_ino):
                    raise QueueSafetyError("inbox_changed_before_link")
                os.link(source, segment, follow_symlinks=False)
                if _identity(segment) != (old.st_dev, old.st_ino) or segment.lstat().st_nlink != 2:
                    raise QueueSafetyError("link_identity_changed")
                _sync_directory(self.pending)
            # The producer is not serialized by the root-only queue lock.
            # It can append AFTER the first <=4 MiB stat and while link()
            # is being fsynced. Re-read BOTH linked names at the last
            # pre-replace boundary. A changed/oversized raw inode stays
            # on its original live path, with the same pending hardlink
            # available for exactly attributed crash recovery; NEVER drop
            # or truncate its bytes to make the next tick pass.
            live_now = _stat_regular(source, self.uid,
                                     max_size=MAX_SEGMENT,
                                     writer_gid=self.writer_gid)
            pending_now = _stat_regular(segment, self.uid,
                                        max_size=MAX_SEGMENT,
                                        writer_gid=self.writer_gid)
            if (live_now.st_dev != old.st_dev or
                    live_now.st_ino != old.st_ino or
                    pending_now.st_dev != old.st_dev or
                    pending_now.st_ino != old.st_ino or
                    live_now.st_nlink != 2 or pending_now.st_nlink != 2 or
                    live_now.st_size != old.st_size or
                    pending_now.st_size != old.st_size or
                    live_now.st_mtime_ns != old.st_mtime_ns or
                    pending_now.st_mtime_ns != old.st_mtime_ns):
                raise QueueSafetyError("raw_changed_between_link_and_replace")
            os.replace(temp, source)
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
        if NATIVE_PENDING.fullmatch(segment.name):
            # Only a FUTURE original per-N cursor ACK may unlink this inode
            # after every late producer append has been reconciled.
            raise QueueSafetyError("native_pending_requires_qualified_ack")
        before = _stat_regular(segment, self.uid, max_size=MAX_SEGMENT,
                               writer_gid=self.writer_gid)
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
        after = _stat_regular(segment, self.uid, max_size=MAX_SEGMENT,
                              writer_gid=self.writer_gid)
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
