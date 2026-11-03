#!/usr/bin/env python3
"""Bound one root-owned official-native package archive to a held original FD9.

This is a read-only admission *component*, never an upgrader: it does not
classify the installed service, call pkg, stop anything or change system state.
The orchestrator must perform a complete owner gate and recheck immediately
before dispatching pkg, then retain the original FD9 through completion.
"""
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat

try:
    from . import native_pkg_handoff
except ImportError:
    import native_pkg_handoff

PACKAGE_NAME = 'os-zapret2-restyle'
PKG_VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+_[1-9][0-9]*\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
MAX_PACKAGE_BYTES = 512 * 1024 * 1024


class CandidateRefusal(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise CandidateRefusal(reason)


def identity(path, expected_version, expected_sha256):
    require(isinstance(path, Path) and path.is_absolute() and
            isinstance(expected_version, str) and
            PKG_VERSION.fullmatch(expected_version) is not None and
            isinstance(expected_sha256, str) and
            SHA256.fullmatch(expected_sha256) is not None and
            path.name == f'{PACKAGE_NAME}-{expected_version}.pkg',
            'PACKAGE_REQUEST_IDENTITY_INVALID')
    return expected_version


def _trusted_regular(st, reason):
    require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1
            and stat.S_IMODE(st.st_mode) & 0o022 == 0 and
            0 < st.st_size <= MAX_PACKAGE_BYTES,
            reason)


def inspect_archive(path, expected_version, expected_sha256):
    """Read actual opened inode, never follow symlinks or trust name alone.

    Returns an immutable identity witness for an *already trusted* root-only
    supervisor request. Not an authorization to run pkg; caller must repeat
    before its actual dispatch and verify installed old owner separately.
    """
    identity(path, expected_version, expected_sha256)
    require(os.geteuid() == 0, 'ROOT_PACKAGE_REQUEST_REQUIRED')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise CandidateRefusal('NATIVE_PKG_ARCHIVE_UNQUALIFIED') from None
    try:
        before = os.fstat(fd)
        _trusted_regular(before, 'NATIVE_PKG_ARCHIVE_UNQUALIFIED')
        original = path.lstat()
        _trusted_regular(original, 'NATIVE_PKG_ARCHIVE_UNQUALIFIED')
        require((before.st_dev, before.st_ino) ==
                (original.st_dev, original.st_ino),
                'NATIVE_PKG_ARCHIVE_PATH_CHANGED')
        sha = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            sha.update(block)
        after = os.fstat(fd)
        try:
            current = path.lstat()
        except OSError:
            raise CandidateRefusal('NATIVE_PKG_ARCHIVE_PATH_CHANGED') from None
        require((before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns) and
                (after.st_dev, after.st_ino) ==
                (current.st_dev, current.st_ino),
                'NATIVE_PKG_ARCHIVE_CHANGED_DURING_READ')
        require(hmac.compare_digest(sha.hexdigest(), expected_sha256),
                'NATIVE_PKG_ARCHIVE_SHA256_MISMATCH')
        return {'status': 'READ_ONLY_NATIVE_PKG_ARCHIVE_BOUND',
                'name': PACKAGE_NAME, 'version': expected_version,
                'sha256': sha.hexdigest(), 'dev': after.st_dev,
                'inode': after.st_ino, 'size': after.st_size,
                'native_pkg_mutation_invoked': False,
                'lh08_ac11_accepted': False}
    finally:
        os.close(fd)


def inspect_with_original_fd9(path, expected_version, expected_sha256,
                              expected_lock_inode):
    """Check the same historical FD9 both before and after archive I/O.

    This does NOT establish old-process/IPFW/Config safety, make the package
    immutable after return or defend against arbitrary privileged root pkg.
    """
    require(type(expected_lock_inode) is int and expected_lock_inode > 0,
            'ORIGINAL_FD9_REQUEST_INODE_INVALID')
    try:
        native_pkg_handoff.verify_original_lock(9, expected_lock_inode)
    except (OSError, native_pkg_handoff.HandoffRefusal):
        raise CandidateRefusal('NATIVE_PKG_ORIGINAL_FD9_UNQUALIFIED') from None
    verified = inspect_archive(path, expected_version, expected_sha256)
    try:
        native_pkg_handoff.verify_original_lock(9, expected_lock_inode)
    except (OSError, native_pkg_handoff.HandoffRefusal):
        raise CandidateRefusal('NATIVE_PKG_ORIGINAL_FD9_CHANGED') from None
    return verified
