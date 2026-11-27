#!/usr/bin/env python3
"""Original managed-Apply scratch barrier; never a separate journal or owner.

The caller already holds original FD9/P2/Config ownership. A deterministic
64-byte marker does not grant authority: only the original WAL inode pin does.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import stat


class ManagedBarrierRefused(RuntimeError):
    pass


TOKEN = re.compile(r"\.auto-detect-([a-f0-9]{32})\.tmp\Z")
DIR_PREFIX = ".s10-managed-barrier-"


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_ctime_ns, info.st_mtime_ns,
            info.st_size, info.st_mode, info.st_uid, info.st_gid, info.st_nlink)


def _name(token):
    matched = TOKEN.fullmatch(token) if isinstance(token, str) else None
    if matched is None:
        raise ManagedBarrierRefused("invalid original ready token")
    return DIR_PREFIX + matched.group(1)


def _payload(token):
    _name(token)
    return hashlib.sha256(("s10-managed-barrier:" + token).encode("ascii")).hexdigest().encode("ascii")


def _secure_dir_fd(root, target_parent: Path, owner):
    info = root.lstat()
    target = target_parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != owner or
            info.st_mode & 0o022 or not stat.S_ISDIR(target.st_mode) or
            target.st_uid != owner or target.st_dev != info.st_dev or
            target.st_mode & 0o022):
        raise ManagedBarrierRefused("barrier root and managed file device differ")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    opened = os.fstat(fd)
    if _identity(opened) != _identity(root.lstat()):
        os.close(fd)
        raise ManagedBarrierRefused("barrier root replaced")
    return fd


@contextmanager
def _scratch(root_fd, name, owner):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
    try:
        opened = os.fstat(fd)
        named = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(opened.st_mode) or opened.st_uid != owner or
                stat.S_IMODE(opened.st_mode) != 0o700 or
                (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)):
            raise ManagedBarrierRefused("foreign barrier directory")
        yield fd
    finally:
        os.close(fd)


def _record(dir_fd, owner, payload):
    entries = set(os.listdir(dir_fd))
    if entries - {"record"}:
        raise ManagedBarrierRefused("foreign barrier entries")
    if "record" not in entries:
        return None
    before = os.stat("record", dir_fd=dir_fd, follow_symlinks=False)
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner or
            stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or
            before.st_size != len(payload)):
        raise ManagedBarrierRefused("foreign barrier record")
    fd = os.open("record", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    try:
        if (_identity(os.fstat(fd)) != _identity(before) or
                os.read(fd, len(payload) + 1) != payload or
                _identity(os.fstat(fd)) != _identity(before) or
                _identity(os.stat("record", dir_fd=dir_fd, follow_symlinks=False)) != _identity(before)):
            raise ManagedBarrierRefused("barrier record changed")
    finally:
        os.close(fd)
    return list(_identity(before))


def _validate_pin(pin, token):
    if (not isinstance(pin, dict) or set(pin) != {"directory", "record", "sha256"} or
            pin["sha256"] != hashlib.sha256(_payload(token)).hexdigest() or
            any(type(row) is not list or len(row) != 9 or
                any(type(value) is not int or value < 0 for value in row)
                for row in (pin["directory"], pin["record"])) or
            not stat.S_ISDIR(pin["directory"][5]) or
            stat.S_IMODE(pin["directory"][5]) != 0o700 or
            not stat.S_ISREG(pin["record"][5]) or
            stat.S_IMODE(pin["record"][5]) != 0o600 or
            pin["record"][8] != 1 or
            pin["directory"][0] != pin["record"][0] or
            pin["directory"][6] != pin["record"][6]):
        raise ManagedBarrierRefused("invalid barrier WAL identity")


def _check_scratch_pin(dir_fd, pin):
    observed = _identity(os.fstat(dir_fd))
    if (observed[0:2] != tuple(pin["directory"][0:2]) or
            observed[5:8] != tuple(pin["directory"][5:8])):
        raise ManagedBarrierRefused("foreign barrier directory inode")


def _check_named(root_fd, name, dir_fd):
    named = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    opened = os.fstat(dir_fd)
    if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
        raise ManagedBarrierRefused("barrier directory name changed")


def seed(root: Path, target_parent: Path, ready_temp: str, owner: int) -> dict:
    """Create owned scratch after original ready WAL, before target rename."""
    name, payload = _name(ready_temp), _payload(ready_temp)
    root_fd = _secure_dir_fd(root, target_parent, owner)
    try:
        os.mkdir(name, 0o700, dir_fd=root_fd)
        with _scratch(root_fd, name, owner) as dir_fd:
            if os.listdir(dir_fd):
                raise ManagedBarrierRefused("barrier scratch not empty")
            fd = os.open("record", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=dir_fd)
            try:
                if os.write(fd, payload) != len(payload):
                    raise ManagedBarrierRefused("short barrier seed")
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(dir_fd)
            _check_named(root_fd, name, dir_fd)
            os.fsync(root_fd)
            record = _record(dir_fd, owner, payload)
            if record is None:
                raise ManagedBarrierRefused("missing barrier seed")
            pin = {"directory": list(_identity(os.fstat(dir_fd))), "record": record,
                   "sha256": hashlib.sha256(payload).hexdigest()}
            _validate_pin(pin, ready_temp)
            return pin
    finally:
        os.close(root_fd)


def finish(root: Path, target_parent: Path, ready_temp: str, owner: int, pin: dict) -> None:
    """Strict live pin, same-inode rewrite/fsync, then remove before installed WAL."""
    _validate_pin(pin, ready_temp)
    name, payload = _name(ready_temp), _payload(ready_temp)
    root_fd = _secure_dir_fd(root, target_parent, owner)
    try:
        with _scratch(root_fd, name, owner) as dir_fd:
            _check_scratch_pin(dir_fd, pin)
            if _record(dir_fd, owner, payload) != pin["record"]:
                raise ManagedBarrierRefused("barrier record inode differs")
            fd = os.open("record", os.O_RDWR | os.O_NOFOLLOW, dir_fd=dir_fd)
            try:
                if _identity(os.fstat(fd)) != tuple(pin["record"]):
                    raise ManagedBarrierRefused("barrier record swapped at write")
                if os.write(fd, payload) != len(payload):
                    raise ManagedBarrierRefused("short barrier rewrite")
                os.fsync(fd)
                after = os.fstat(fd)
                if ((after.st_dev, after.st_ino, after.st_mode, after.st_uid,
                     after.st_gid, after.st_nlink, after.st_size) !=
                    (pin["record"][0], pin["record"][1], pin["record"][5],
                     pin["record"][6], pin["record"][7], pin["record"][8],
                     len(payload)) or _record(dir_fd, owner, payload) != list(_identity(after))):
                    raise ManagedBarrierRefused("barrier changed after rewrite")
            finally:
                os.close(fd)
            os.unlink("record", dir_fd=dir_fd)
            if os.listdir(dir_fd):
                raise ManagedBarrierRefused("barrier acquired foreign entries")
            os.fsync(dir_fd)
            _check_named(root_fd, name, dir_fd)
            os.rmdir(name, dir_fd=root_fd)
            os.fsync(root_fd)
    finally:
        os.close(root_fd)


def recover(root: Path, target_parent: Path, ready_temp: str, owner: int,
            pin: dict | None) -> None:
    """Never unlink a scratch without its exact original WAL inode proof.

    Crashes before pin persistence or after scratch rewrite leave a blocked
    original operation for explicit manual review, never guessed deletion.
    """
    name, payload = _name(ready_temp), _payload(ready_temp)
    root_fd = _secure_dir_fd(root, target_parent, owner)
    try:
        try:
            os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if pin is None:
            raise ManagedBarrierRefused("unbound barrier residue")
        _validate_pin(pin, ready_temp)
        with _scratch(root_fd, name, owner) as dir_fd:
            _check_scratch_pin(dir_fd, pin)
            record = _record(dir_fd, owner, payload)
            if record is not None:
                if record != pin["record"]:
                    raise ManagedBarrierRefused("foreign barrier inode on recovery")
                os.unlink("record", dir_fd=dir_fd)
            if os.listdir(dir_fd):
                raise ManagedBarrierRefused("foreign barrier recovery entries")
            os.fsync(dir_fd)
            _check_named(root_fd, name, dir_fd)
            os.rmdir(name, dir_fd=root_fd)
            os.fsync(root_fd)
    finally:
        os.close(root_fd)
