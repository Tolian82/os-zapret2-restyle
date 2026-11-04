#!/usr/bin/env python3
"""CI-only mutation of an actual native .pkg after first signed admission.

This fixture is NEVER packaged as a production updater and NEVER invokes pkg.
It deliberately corrupts one byte in a validated, exclusive, owned test
archive on a disposable CI guest to prove final signature/sha revalidation.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

SHA256 = re.compile(r"[a-f0-9]{64}\Z")
REVISION = re.compile(r"[1-9][0-9]*\Z")
MAX_ARCHIVE = 512 * 1024 * 1024


class Refusal(Exception):
    pass


def need(ok, code):
    if not ok:
        raise Refusal(code)


def digest(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    value = hashlib.sha256()
    while True:
        part = os.read(fd, 1024 * 1024)
        if not part:
            break
        value.update(part)
    return value.hexdigest()


def stat_identity(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mode, st.st_uid, st.st_nlink)


def corrupt_native_archive(path, signed_sha256, revision, *, after_final=False):
    """Flip exactly the first byte after authentic expected archive digest.

    Only a disposable CI controller can invoke this helper. The original
    FD9 remains with the detached worker, not this controller.
    """
    need(type(after_final) is bool, 'CI_ARCHIVE_TAMPER_PHASE_INVALID')
    phase_flag=('ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER_CI'
                if after_final else
                'ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER_CI')
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get(phase_flag) == '1' and
         os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK') == '1' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1',
         'CI_LATE_ARCHIVE_TAMPER_NOT_DISPOSABLE')
    need(isinstance(path, Path) and path.is_absolute() and
         os.path.normpath(str(path)) == str(path) and
         type(revision) is str and REVISION.fullmatch(revision) is not None and
         path.name == 'os-zapret2-restyle-0.6.2_' + revision + '.pkg' and
         type(signed_sha256) is str and
         SHA256.fullmatch(signed_sha256) is not None,
         'CI_LATE_ARCHIVE_IDENTITY_INVALID')
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Refusal('CI_LATE_ARCHIVE_OPEN_REFUSED') from None
    try:
        before = os.fstat(fd)
        current = path.lstat()
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
             before.st_uid == os.geteuid() and
             stat.S_IMODE(before.st_mode) & 0o022 == 0 and
             0 < before.st_size <= MAX_ARCHIVE and
             stat_identity(before) == stat_identity(current),
             'CI_LATE_ARCHIVE_NOT_EXCLUSIVE_OWNED_FILE')
        original_sha = digest(fd)
        need(original_sha == signed_sha256,
             'CI_LATE_ARCHIVE_ALREADY_DIFFERENT_FROM_SIGNED_BYTES')
        need(stat_identity(os.fstat(fd)) == stat_identity(before) and
             stat_identity(path.lstat()) == stat_identity(before),
             'CI_LATE_ARCHIVE_CHANGED_DURING_PRECHECK')
        first = os.pread(fd, 1, 0)
        need(len(first) == 1, 'CI_LATE_ARCHIVE_FIRST_BYTE_UNAVAILABLE')
        need(os.pwrite(fd, bytes((first[0] ^ 1,)), 0) == 1,
             'CI_LATE_ARCHIVE_SHORT_WRITE')
        os.fsync(fd)
        after = os.fstat(fd)
        need(stat_identity(after) == stat_identity(before) and
             stat_identity(path.lstat()) == stat_identity(before),
             'CI_LATE_ARCHIVE_INODE_OR_SIZE_CHANGED')
        modified_sha = digest(fd)
        need(modified_sha != signed_sha256,
             'CI_LATE_ARCHIVE_BYTES_NOT_CORRUPTED')
        return {'status': ('CI_ARCHIVE_CORRUPTED_AFTER_FINAL_GRANT'
                           if after_final else
                           'CI_LATE_ARCHIVE_CORRUPTED_BEFORE_FINAL_GRANT'),
                'expected_sha256': signed_sha256,
                'modified_sha256': modified_sha,
                'original_fd9_touched': False,
                'native_pkg_invoked': False}
    finally:
        os.close(fd)
