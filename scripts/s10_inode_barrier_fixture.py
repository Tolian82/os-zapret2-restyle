#!/usr/bin/env python3
"""Test-only WAL-token-bound scratch prototype; never an Apply entrypoint."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat
import tempfile
import unittest


class ScratchRefused(RuntimeError):
    pass


def inode(info):
    return info.st_dev, info.st_ino


def scratch_name(ready_temp):
    if not isinstance(ready_temp, str) or not re.fullmatch(r"\.auto-detect-[a-f0-9]{32}\.tmp", ready_temp):
        raise ScratchRefused("invalid ready token")
    return ".s10-barrier-" + ready_temp[13:-4]


@contextmanager
def directory(path, uid, *, dir_fd=None, private=False):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
    try:
        opened = os.fstat(fd)
        named = os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
        if (inode(opened) != inode(named) or not stat.S_ISDIR(opened.st_mode) or
                opened.st_uid != uid or opened.st_mode & 0o022 or
                private and stat.S_IMODE(opened.st_mode) != 0o700):
            raise ScratchRefused("unsafe scratch directory")
        yield fd
    finally:
        os.close(fd)


def empty_file(fd, name, uid):
    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or
            stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or info.st_size != 0):
        raise ScratchRefused("foreign scratch entry")
    return inode(info)


def entries(fd, uid):
    names = set(os.listdir(fd))
    if names - {"record", "pending"}:
        raise ScratchRefused("unknown scratch entry")
    return {name: empty_file(fd, name, uid) for name in names}


def create_empty(fd, name, uid, fault):
    file_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                      0o600, dir_fd=fd)
    try:
        created = inode(os.fstat(file_fd))
        fault("create-" + name)
        os.fsync(file_fd)
        if empty_file(fd, name, uid) != created:
            raise ScratchRefused("scratch file replaced")
    finally:
        os.close(file_fd)
    return created


def assert_named(parent, name, fd):
    if inode(os.stat(name, dir_fd=parent, follow_symlinks=False)) != inode(os.fstat(fd)):
        raise ScratchRefused("scratch directory replaced")


def check_device(parent, target_parent):
    if os.fstat(parent).st_dev != target_parent.lstat().st_dev:
        raise ScratchRefused("scratch on different device")


def seed(root, target_parent, ready_temp, uid, fault=lambda _: None):
    """Call only AFTER ready is durable; no scratch before that point."""
    name = scratch_name(ready_temp)
    with directory(root, uid) as parent:
        check_device(parent, target_parent)
        os.mkdir(name, 0o700, dir_fd=parent)
        fault("mkdir")
        with directory(name, uid, dir_fd=parent, private=True) as fd:
            if entries(fd, uid):
                raise ScratchRefused("new scratch not empty")
            record = create_empty(fd, "record", uid, fault)
            os.fsync(fd)
            assert_named(parent, name, fd)
            os.fsync(parent)
            fault("seed-durable")
            return inode(os.fstat(fd)), record


def finish(root, target_parent, ready_temp, uid, pin, fault=lambda _: None):
    """Live writer: compare exact seeded directory and file before replacement."""
    name = scratch_name(ready_temp)
    with directory(root, uid) as parent:
        check_device(parent, target_parent)
        with directory(name, uid, dir_fd=parent, private=True) as fd:
            if inode(os.fstat(fd)) != pin[0] or entries(fd, uid) != {"record": pin[1]}:
                raise ScratchRefused("scratch seed replaced")
            pending = create_empty(fd, "pending", uid, fault)
            if entries(fd, uid) != {"record": pin[1], "pending": pending}:
                raise ScratchRefused("scratch pre-replace changed")
            os.replace("pending", "record", src_dir_fd=fd, dst_dir_fd=fd)
            fault("rename")
            os.fsync(fd)
            if entries(fd, uid) != {"record": pending}:
                raise ScratchRefused("scratch post-replace changed")
            os.unlink("record", dir_fd=fd)
            fault("unlink")
            os.fsync(fd)
            assert_named(parent, name, fd)
            os.rmdir(name, dir_fd=parent)
            fault("rmdir")
            os.fsync(parent)


def recover(root, target_parent, ready_temp, uid):
    """Fixture only: caller MUST prove exact original ready WAL and FD9 first.

    Scratch contents never authorize recovery of the actual HOSTLIST. Only the
    operation-token namespace is recognized; no unknown/nonempty object is removed.
    """
    name = scratch_name(ready_temp)
    with directory(root, uid) as parent:
        check_device(parent, target_parent)
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        with directory(name, uid, dir_fd=parent, private=True) as fd:
            observed = entries(fd, uid)
            for entry, identity in observed.items():
                if empty_file(fd, entry, uid) != identity:
                    raise ScratchRefused("scratch recovery entry replaced")
                os.unlink(entry, dir_fd=fd)
            os.fsync(fd)
            assert_named(parent, name, fd)
            os.rmdir(name, dir_fd=parent)
            os.fsync(parent)


class ScratchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root / "active"
        self.target.mkdir()
        self.token = ".auto-detect-" + "a" * 32 + ".tmp"
        self.path = self.root / scratch_name(self.token)
        self.args = self.root, self.target, self.token, os.geteuid()

    def test_token(self):
        self.assertEqual(self.path.name, ".s10-barrier-" + "a" * 32)
        for token in (None, "../x", ".auto-detect-" + "A" * 32 + ".tmp"):
            with self.assertRaises(ScratchRefused):
                scratch_name(token)

    def test_clean_finish(self):
        pin = seed(*self.args)
        finish(*self.args, pin)
        self.assertFalse(self.path.exists())
        recover(*self.args)
        self.assertEqual(set(self.root.iterdir()), {self.target})

    def test_crash_boundaries(self):
        for point in ("mkdir", "create-record", "seed-durable", "create-pending", "rename", "unlink", "rmdir"):
            with self.subTest(point=point):
                def fault(label):
                    if label == point:
                        raise InterruptedError(point)
                with self.assertRaisesRegex(InterruptedError, point):
                    pin = seed(*self.args, fault=fault)
                    finish(*self.args, pin, fault=fault)
                recover(*self.args)
                recover(*self.args)
                self.assertFalse(self.path.exists())

    def test_foreign_entries(self):
        for variant in ("unknown", "nonempty", "symlink", "hardlink", "mode"):
            with self.subTest(variant=variant):
                seed(*self.args)
                record = self.path / "record"
                foreign = self.path / "other"
                if variant == "unknown":
                    foreign.touch()
                elif variant == "nonempty":
                    record.write_bytes(b"foreign")
                elif variant == "symlink":
                    record.unlink()
                    record.symlink_to(self.target)
                elif variant == "hardlink":
                    os.link(record, foreign)
                else:
                    record.chmod(0o644)
                with self.assertRaises(ScratchRefused):
                    recover(*self.args)
                self.assertTrue(self.path.exists())
                if foreign.exists():
                    foreign.unlink()
                if record.exists() or record.is_symlink():
                    record.unlink()
                self.path.rmdir()

    def test_live_replaced_inode(self):
        pin = seed(*self.args)
        record = self.path / "record"
        record.rename(self.path / "old")
        (self.path / "record").touch(mode=0o600)
        (self.path / "old").unlink()
        with self.assertRaises(ScratchRefused):
            finish(*self.args, pin)
        self.assertTrue(record.exists())

    def test_directory_symlink(self):
        self.path.symlink_to(self.target, target_is_directory=True)
        with self.assertRaises(OSError):
            recover(*self.args)
        self.assertTrue(self.path.is_symlink())
        self.assertTrue(self.target.is_dir())


if __name__ == "__main__":
    unittest.main()
