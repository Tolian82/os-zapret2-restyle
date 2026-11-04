#!/usr/bin/env python3
"""Disposable CI-only atomic archive PATH rebind after signed stdin snapshot.

Never run outside throwaway OPNsense; never packaged or offered as updater.
It only changes an already-built test .pkg path; it never calls pkg/FD9.
"""
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat

SHA256 = re.compile(r'[a-f0-9]{64}\Z')
REVISION = re.compile(r'[1-9][0-9]*\Z')
MAX_PACKAGE_BYTES = 512 * 1024 * 1024


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def qualify(path, expected_sha, revision):
    flags = ('ZAPRET2_STAGE3_NATIVE_STDIN_PKG',
             'ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI',
             'ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP_CI',
             'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK',
             'ZAPRET2_NATIVE_BUILD_CI')
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         all(os.environ.get(flag) == '1' for flag in flags),
         'CI_STDIN_PATH_SWAP_DISPOSABLE_OPTIN_REQUIRED')
    need(isinstance(path, Path) and path.is_absolute() and
         os.path.normpath(str(path)) == str(path) and
         type(revision) is str and REVISION.fullmatch(revision) is not None and
         path.name == 'os-zapret2-restyle-0.6.2_' + revision + '.pkg' and
         type(expected_sha) is str and SHA256.fullmatch(expected_sha) is not None,
         'CI_STDIN_PATH_SWAP_CANDIDATE_IDENTITY_INVALID')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def trusted_stat(st):
    return (stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid() and
            st.st_nlink == 1 and stat.S_IMODE(st.st_mode) & 0o022 == 0 and
            0 < st.st_size <= MAX_PACKAGE_BYTES)


def read_exact_fd(fd, st):
    os.lseek(fd, 0, os.SEEK_SET)
    parts = []
    total = 0
    while True:
        item = os.read(fd, 1024 * 1024)
        if not item:
            break
        total += len(item)
        need(total <= st.st_size and total <= MAX_PACKAGE_BYTES,
             'CI_STDIN_PATH_SWAP_READ_OVERFLOW')
        parts.append(item)
    need(total == st.st_size, 'CI_STDIN_PATH_SWAP_SHORT_SOURCE')
    return b''.join(parts)


def active_identity(path, sha, inode):
    st = path.lstat()
    need(trusted_stat(st) and st.st_ino == inode and sha_bytes(path.read_bytes()) == sha,
         'CI_STDIN_PATH_SWAP_ACTIVE_IDENTITY_CHANGED')
    return st


def atomic_rebind(path, expected_sha, revision):
    """Move pathname atomically to a corrupted DIFFERENT inode, retain old inode.

    Controller only, after the original FD9 worker has frozen bytes. The old
    inode remains via a same-directory temporary hardlink for safe restoration.
    """
    qualify(path, expected_sha, revision)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        original = path.lstat()
        need(trusted_stat(before) and
             (before.st_dev, before.st_ino, before.st_size, before.st_mode) ==
             (original.st_dev, original.st_ino, original.st_size, original.st_mode),
             'CI_STDIN_PATH_SWAP_ORIGINAL_NOT_EXCLUSIVE')
        raw = read_exact_fd(fd, before)
        need(sha_bytes(raw) == expected_sha and
             os.fstat(fd).st_ino == path.lstat().st_ino == before.st_ino,
             'CI_STDIN_PATH_SWAP_OLD_SOURCE_MISMATCH')
    finally:
        os.close(fd)
    modified = bytes((raw[0] ^ 1,)) + raw[1:]
    modified_sha = sha_bytes(modified)
    need(modified_sha != expected_sha, 'CI_STDIN_PATH_SWAP_MODIFICATION_FAILED')
    nonce = secrets.token_hex(12)
    backup = path.with_name('.' + path.name + '.' + nonce + '.original')
    forged = path.with_name('.' + path.name + '.' + nonce + '.forged')
    need(not backup.exists() and not backup.is_symlink() and
         not forged.exists() and not forged.is_symlink(),
         'CI_STDIN_PATH_SWAP_PRIVATE_NAME_COLLISION')
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
    f = os.open(forged, flags, 0o600)
    try:
        with os.fdopen(f, 'wb') as out:
            out.write(modified)
            out.flush()
            os.fsync(out.fileno())
        need(sha_bytes(forged.read_bytes()) == modified_sha and
             forged.lstat().st_ino != before.st_ino,
             'CI_STDIN_PATH_SWAP_FORGED_PREP_INVALID')
        os.link(path, backup, follow_symlinks=False)
        need(backup.lstat().st_ino == before.st_ino and
             path.lstat().st_ino == before.st_ino,
             'CI_STDIN_PATH_SWAP_ORIGINAL_BACKUP_MISMATCH')
        os.replace(forged, path)
        after = path.lstat()
        need(trusted_stat(after) and after.st_ino != before.st_ino and
             after.st_size == before.st_size and
             sha_bytes(path.read_bytes()) == modified_sha and
             backup.lstat().st_ino == before.st_ino and
             sha_bytes(backup.read_bytes()) == expected_sha,
             'CI_STDIN_PATH_SWAP_REBIND_NOT_PROVEN')
        return {'path': path, 'backup': backup, 'original_inode': before.st_ino,
                'replacement_inode': after.st_ino, 'original_sha256': expected_sha,
                'replacement_sha256': modified_sha, 'revision': revision,
                'status': 'CI_STDIN_PATH_REBOUND_TO_DIFFERENT_INODE',
                'original_fd9_touched': False, 'native_pkg_invoked': False}
    finally:
        if forged.exists() and not forged.is_symlink():
            forged.unlink()


def require_still_rebound(report):
    need(type(report) is dict and report.get('status') ==
         'CI_STDIN_PATH_REBOUND_TO_DIFFERENT_INODE',
         'CI_STDIN_PATH_SWAP_REPORT_INVALID')
    path, backup = report['path'], report['backup']
    qualify(path, report['original_sha256'], report['revision'])
    active_identity(path, report['replacement_sha256'], report['replacement_inode'])
    active_identity(backup, report['original_sha256'], report['original_inode'])
    need(report['replacement_inode'] != report['original_inode'],
         'CI_STDIN_PATH_SWAP_INODE_COLLISION')
    return True


def restore_original_after_verified_pkg(report):
    """Restore only the exact saved inode after the worker has reported PASS."""
    require_still_rebound(report)
    os.replace(report['backup'], report['path'])
    active_identity(report['path'], report['original_sha256'], report['original_inode'])
    need(not report['backup'].exists() and not report['backup'].is_symlink(),
         'CI_STDIN_PATH_SWAP_BACKUP_RESIDUE')
    return {'status': 'CI_STDIN_ORIGINAL_CANDIDATE_PATH_RESTORED',
            'original_sha256': report['original_sha256'],
            'replacement_sha256': report['replacement_sha256'],
            'original_inode': report['original_inode'],
            'replacement_inode': report['replacement_inode']}
