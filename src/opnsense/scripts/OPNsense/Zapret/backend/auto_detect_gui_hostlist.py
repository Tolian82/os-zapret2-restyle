#!/usr/bin/env python3
"""#1052: native root-owned GUI editor for the shared final Auto HOSTLIST.

Only `read` and explicit revisioned `save` are exposed via configd. This does
not install or enable the native auto-detect observer, a cron worker or any
additional Config writer. Native domain syntax stays in domain_policy.py.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from auto_detect_destination_commit import (
    DestinationRefused, _target, _replace, _sync, exclusive_destination_lock,
)
from domain_policy import DomainPolicyError, AutoDomainPolicyError, normalize

AUTO_HOSTLIST = Path('/usr/local/etc/zapret2/ipset/auto-domains.txt')
AUTO_LOCK = Path('/usr/local/etc/zapret2/ipset/.auto-domains.lock')
LEGACY_HOSTLIST = Path('/usr/local/etc/zapret2/ipset/zapret-hosts-auto.txt')
MAX_GUI_BYTES = 40 * 1024  # bounded configd argv; native hostlist may be larger
MAX_TOKEN = 57000
HASH = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
ENCODED = re.compile(r'[A-Za-z0-9_-]{1,57000}\Z', re.ASCII)


class AutoHostlistRefused(ValueError):
    pass


def _revision(data: bytes | None) -> str:
    return hashlib.sha256(b'missing\0' if data is None else b'present\0' + data).hexdigest()


def _read_current(path: Path, uid: int) -> bytes | None:
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
            parent.st_mode & 0o022):
        raise AutoHostlistRefused('unsafe_directory')
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    # The shared destination writer also uses this nofollow/owner/link check.
    try:
        contents, _ = _target(path, uid)
    except DestinationRefused as exc:
        raise AutoHostlistRefused('unsafe_or_unreadable_file') from exc
    if len(contents) > MAX_GUI_BYTES:
        raise AutoHostlistRefused('file_exceeds_gui_transfer_limit')
    return contents


def _migrate_legacy_if_missing(path: Path, legacy: Path, uid: int) -> None:
    """Copy old file only when target has never been created, keeping source."""
    if path == legacy or path.parent != legacy.parent:
        raise AutoHostlistRefused('unsafe_legacy_source')
    if _read_current(path, uid) is not None:
        return
    old = _read_current(legacy, uid)
    if old is not None:
        _create(path, old, uid)


def read_current(path: Path = AUTO_HOSTLIST, lock: Path = AUTO_LOCK, *,
                 legacy: Path = LEGACY_HOSTLIST, owner_uid: int = 0) -> dict:
    """Return missing/empty/populated, preserving any absent-file legacy first."""
    with exclusive_destination_lock(lock, owner_uid):
        _migrate_legacy_if_missing(path, legacy, owner_uid)
        data = _read_current(path, owner_uid)
        return {
            'result': 'ok',
            'status': 'missing' if data is None else ('empty' if not data else 'populated'),
            'revision': _revision(data),
            'content': '' if data is None else data.decode('utf-8'),
        }


def _create(path: Path, data: bytes, uid: int) -> None:
    """Write a complete temporary inode, then link-once an absent name."""
    temp = path.parent / ('.auto-hostlist-' + secrets.token_hex(16) + '.tmp')
    fd = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o600)
        os.fchmod(fd, 0o644)
        os.fchown(fd, uid, 0 if uid == 0 else os.getegid())
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise AutoHostlistRefused('short_write')
            view = view[n:]
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.link(temp, path, follow_symlinks=False)
        _sync(path.parent)
    finally:
        if fd is not None:
            os.close(fd)
        if temp.exists():
            temp.unlink()
            _sync(path.parent)


def save_current(revision: str, content: str, path: Path = AUTO_HOSTLIST,
                 lock: Path = AUTO_LOCK, *, legacy: Path = LEGACY_HOSTLIST,
                 owner_uid: int = 0) -> dict:
    """One revision-check + normalized atomic write under the worker's lock."""
    if (not isinstance(revision, str) or not HASH.fullmatch(revision) or
            not isinstance(content, str) or len(content.encode('utf-8')) > MAX_GUI_BYTES):
        raise AutoHostlistRefused('invalid_revision_or_content')
    # Canonical policy owns modifiers, hosts, invalid input and deduplication.
    try:
        result = normalize(content, 'user')
    except (DomainPolicyError, AutoDomainPolicyError) as exc:
        raise AutoHostlistRefused('invalid_domain_lines') from exc
    normalized = result['normalized']
    encoded = (normalized + '\n' if normalized else '').encode('utf-8')
    if len(encoded) > MAX_GUI_BYTES:
        raise AutoHostlistRefused('normalized_file_exceeds_limit')
    with exclusive_destination_lock(lock, owner_uid):
        _migrate_legacy_if_missing(path, legacy, owner_uid)
        before = _read_current(path, owner_uid)
        if _revision(before) != revision:
            return {'result': 'conflict', 'reason': 'revision_changed'}
        if before != encoded:
            if before is None:
                _create(path, encoded, owner_uid)
            else:
                _replace(path, before, encoded, owner_uid)
        return {'result': 'saved', 'revision': _revision(encoded),
                'status': 'empty' if not encoded else 'populated',
                'content': encoded.decode('utf-8')}


def _unpack(arg: str) -> tuple[str, str]:
    if not isinstance(arg, str) or not ENCODED.fullmatch(arg) or len(arg) > MAX_TOKEN:
        raise AutoHostlistRefused('invalid_envelope')
    raw = base64.urlsafe_b64decode(arg + '=' * (-len(arg) % 4))
    if len(raw) > 43000:
        raise AutoHostlistRefused('oversized_envelope')
    payload = json.loads(raw)
    if (not isinstance(payload, dict) or set(payload) != {'revision', 'content'} or
            type(payload['revision']) is not str or type(payload['content']) is not str):
        raise AutoHostlistRefused('invalid_envelope_fields')
    return payload['revision'], payload['content']


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if (not sys.platform.startswith('freebsd') or os.geteuid() != 0 or
            not argv or argv[0] not in ('read', 'save') or
            (argv[0] == 'read' and len(argv) != 1) or
            (argv[0] == 'save' and len(argv) != 2)):
        print(json.dumps({'result': 'error', 'reason': 'native_request_refused'}))
        return 0
    try:
        result = (read_current() if argv[0] == 'read'
                  else save_current(*_unpack(argv[1])))
    except (AutoHostlistRefused, DestinationRefused, OSError, ValueError,
            UnicodeError, TypeError, KeyError) as exc:
        # Never log user domains or the contents of a failed transport.
        result = {'result': 'error', 'reason': str(exc) if isinstance(exc, AutoHostlistRefused)
                  else 'native_file_unavailable'}
    print(json.dumps(result, ensure_ascii=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())