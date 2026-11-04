#!/usr/bin/env python3
"""Disposable OPNsense CI: immutable bytes snapshot -> native pkg add from stdin.

Never installed in a product package. Does not authorize a supported updater.
All actual package mutation remains restricted to a fresh disposable OPNsense
with original FD9 continuously owned by the calling configd worker.
"""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import signal
import stat
import subprocess

MAX_PACKAGE_BYTES = 512 * 1024 * 1024
SHA256 = re.compile(r'[a-f0-9]{64}\Z')
REVISION = re.compile(r'[1-9][0-9]*\Z')


class Refusal(Exception):
    pass


def need(ok, error):
    if not ok:
        raise Refusal(error)


def require_disposable():
    flags = ('GITHUB_ACTIONS', 'ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI',
             'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK',
             'ZAPRET2_NATIVE_BUILD_CI',
             'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI',
             'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF')
    need(all(os.environ.get(key) == ('true' if key == 'GITHUB_ACTIONS' else '1')
             for key in flags), 'STDIN_NATIVE_PKG_DISPOSABLE_GATE_REQUIRED')


@dataclass(frozen=True)
class VerifiedBytes:
    data: bytes
    sha256: str
    archive_name: str
    revision: str
    inode: int
    dev: int


def _identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_nlink, s.st_size)


def freeze_exact_candidate(path, expected_sha, revision, check_fd9):
    """Read a single owned native candidate inode into immutable Python bytes."""
    require_disposable()
    need(callable(check_fd9), 'STDIN_FD9_CHECKER_MISSING')
    need(isinstance(path, Path) and path.is_absolute() and
         os.path.normpath(str(path)) == str(path) and
         type(revision) is str and REVISION.fullmatch(revision) is not None and
         path.name == 'os-zapret2-restyle-0.6.2_' + revision + '.pkg' and
         type(expected_sha) is str and SHA256.fullmatch(expected_sha) is not None,
         'STDIN_CANDIDATE_IDENTITY_INVALID')
    check_fd9()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Refusal('STDIN_CANDIDATE_OPEN_REFUSED') from None
    try:
        st = os.fstat(fd)
        candidate = path.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
             st.st_uid == os.geteuid() and
             stat.S_IMODE(st.st_mode) & 0o022 == 0 and
             0 < st.st_size <= MAX_PACKAGE_BYTES and
             _identity(st) == _identity(candidate),
             'STDIN_CANDIDATE_INODE_UNTRUSTED')
        chunks = []
        total = 0
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            need(total <= st.st_size and total <= MAX_PACKAGE_BYTES,
                 'STDIN_CANDIDATE_READ_OVERFLOW')
            digest.update(chunk)
            chunks.append(chunk)
        need(total == st.st_size and digest.hexdigest() == expected_sha,
             'STDIN_CANDIDATE_SNAPSHOT_SHA_MISMATCH')
        need(_identity(os.fstat(fd)) == _identity(st) and
             _identity(path.lstat()) == _identity(st),
             'STDIN_CANDIDATE_CHANGED_DURING_SNAPSHOT')
        data = b''.join(chunks)
        need(len(data) == total and hashlib.sha256(data).hexdigest() == expected_sha,
             'STDIN_IMMUTABLE_SNAPSHOT_HASH_FAILED')
        check_fd9()
        return VerifiedBytes(data=data, sha256=expected_sha,
                             archive_name=path.name, revision=revision,
                             inode=st.st_ino, dev=st.st_dev)
    finally:
        os.close(fd)


def install_frozen_stdin(snapshot, env, check_fd9, *, popen=subprocess.Popen):
    """Native pkg consumes *only* verified bytes through its stdin, never a path."""
    require_disposable()
    need(type(snapshot) is VerifiedBytes and
         type(snapshot.data) is bytes and
         type(snapshot.revision) is str and
         REVISION.fullmatch(snapshot.revision) is not None and
         snapshot.archive_name == ('os-zapret2-restyle-0.6.2_' + snapshot.revision + '.pkg') and
         type(snapshot.sha256) is str and SHA256.fullmatch(snapshot.sha256) is not None and
         0 < len(snapshot.data) <= MAX_PACKAGE_BYTES and
         hashlib.sha256(snapshot.data).hexdigest() == snapshot.sha256,
         'STDIN_FROZEN_BYTES_NOT_EXACTLY_SIGNED')
    need(callable(check_fd9) and isinstance(env, dict),
         'STDIN_DISPATCH_ARGUMENTS_UNQUALIFIED')
    check_fd9()
    argv = ['/usr/sbin/pkg', '-o', 'REPO_AUTOUPDATE=false', 'add', '-f', '-']
    try:
        proc = popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=False, env=env,
                     pass_fds=(9,), start_new_session=True)
    except OSError:
        raise Refusal('STDIN_NATIVE_PKG_PROCESS_START_REFUSED') from None
    try:
        out, err = proc.communicate(input=snapshot.data, timeout=230)
    except subprocess.TimeoutExpired:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate(timeout=8)
        raise Refusal('STDIN_NATIVE_PKG_TIMEOUT_UNKNOWN_INSTALL_STATE') from None
    need(type(out) is bytes and type(err) is bytes and
         isinstance(proc.returncode, int),
         'STDIN_NATIVE_PKG_RESULT_INVALID')
    check_fd9()
    return (proc.returncode, out.decode('utf-8', 'replace'),
            err.decode('utf-8', 'replace'))
