#!/usr/bin/env python3
"""Receive the genuine Zapret2 lifecycle FD9 for a detached package supervisor.

A transport/identity primitive, not a package updater or authorization to run
pkg.  The caller must independently verify the complete installed owner,
transaction request and package bytes, and retain FD9 through the operation.
"""
import array
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import stat

LOCK = Path('/var/run/zapret2-lifecycle.lock')
HEAD = re.compile(r'[0-9a-f]{40}\Z')
NONCE = re.compile(r'[0-9a-f]{32}\Z')
FIELDS = frozenset(('head', 'nonce', 'created', 'inode'))


class HandoffRefusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise HandoffRefusal(reason)


def validate_envelope(fields, head, nonce):
    require(isinstance(head, str) and HEAD.fullmatch(head) is not None and
            isinstance(nonce, str) and NONCE.fullmatch(nonce) is not None,
            'UNQUALIFIED_EXPECTED_HANDOFF_IDENTITY')
    require(isinstance(fields, dict) and set(fields) == FIELDS and
            fields.get('head') == head and fields.get('nonce') == nonce and
            type(fields.get('created')) is bool and
            type(fields.get('inode')) is int and fields['inode'] > 0,
            'HANDOFF_ENVELOPE_UNTRUSTED')
    return fields


def verify_original_lock(fd, inode):
    """Never infer ownership just from FD number, pathname or ticket."""
    require(os.geteuid() == 0, 'ROOT_HANDOFF_REQUIRED')
    require(LOCK.is_absolute() and not LOCK.is_symlink(),
            'ORIGINAL_LOCK_PATH_UNTRUSTED')
    path = LOCK.lstat()
    held = os.fstat(fd)
    require(stat.S_ISREG(path.st_mode) and stat.S_ISREG(held.st_mode) and
            path.st_uid == held.st_uid == 0 and
            path.st_nlink == held.st_nlink == 1 and
            (path.st_dev, path.st_ino) == (held.st_dev, held.st_ino) and
            held.st_ino == inode, 'TRANSFERRED_FD9_NOT_ORIGINAL_INODE')
    # This is a DIFFERENT open file description: the original BSD flock must
    # reject a nonblocking competing lock. Never unlock the received FD.
    challenger = os.open(LOCK, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        probe = os.fstat(challenger)
        require((probe.st_dev, probe.st_ino) == (held.st_dev, held.st_ino),
                'ORIGINAL_LOCK_PATH_CHANGED_DURING_CHALLENGE')
        try:
            fcntl.flock(challenger, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            fcntl.flock(challenger, fcntl.LOCK_UN)
            raise HandoffRefusal('ORIGINAL_FD9_NOT_EXCLUSIVE')
    finally:
        os.close(challenger)


def receive_original_fd9(conn, *, head, nonce):
    """Return (owned_fd, envelope). Caller MUST close owned_fd on all exits.

    Socket binding, exact root-only directory, supervisor lifetime and
    authenticated ACK are checked by the orchestrator, never inferred here.
    No pkg, subprocess, file mutation or socket creation occurs in this module.
    """
    require(os.geteuid() == 0, 'ROOT_HANDOFF_REQUIRED')
    require(conn.family == socket.AF_UNIX and
            (conn.type & socket.SOCK_STREAM) == socket.SOCK_STREAM,
            'LOCAL_STREAM_HANDOFF_REQUIRED')
    payload, control, flags, _ = conn.recvmsg(500, socket.CMSG_SPACE(16))
    received = []
    bad_control = False
    try:
        for level, kind, data in control:
            if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
                bad_control = True
                continue
            integers = array.array('i')
            if len(data) % integers.itemsize:
                bad_control = True
            integers.frombytes(data[:len(data) - len(data) % integers.itemsize])
            received.extend(integers.tolist())
        require(not bad_control and flags == 0 and len(received) == 1,
                'MISSING_TRUNCATED_OR_EXTRA_FD9_RIGHTS')
        try:
            fields = json.loads(payload.decode('ascii'))
        except (UnicodeError, ValueError):
            raise HandoffRefusal('HANDOFF_ENVELOPE_NOT_JSON') from None
        validate_envelope(fields, head, nonce)
        verify_original_lock(received[0], fields['inode'])
        return received.pop(), fields
    finally:
        for fd in received:
            os.close(fd)
