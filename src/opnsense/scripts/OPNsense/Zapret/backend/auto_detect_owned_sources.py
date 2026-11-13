#!/usr/bin/env python3
"""#1052 P2k8b: dormant root-private known-HOSTLIST auto-owned components.

Only an already qualified native Config/FD9 owner may initialize them (no CLI
bootstrap). No user Config/XML changes or native engine/worker writes here.
The read CLI is root-only and obtains the SAME P2k4/P2k5 destination flock
for the shared final file and all known automatic components at one instant.
Missing ownership authority is reported as unavailable, never empty.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from auto_detect_destination_commit import DestinationRefused, exclusive_destination_lock, _sync
from auto_detect_gui_hostlist import AUTO_HOSTLIST, AUTO_LOCK, _read_current, _revision
from domain_policy import normalize, DomainPolicyError, AutoDomainPolicyError

OWNED_ROOT = Path('/var/db/zapret2/auto-detect-owned')
KNOWN_HOSTLISTS = ('youtube', 'user')  # registered HOSTLISTs except shared 'auto'
MAX_COMPONENT = 40 * 1024  # same bounded native PHP transport as final file
SHA256 = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)


class OwnedSourcesRefused(RuntimeError):
    """Unqualified ownership must never enable a P1 destination write."""


def _safe_dir(path: Path, uid: int) -> None:
    try:
        st = path.lstat()
    except OSError as exc:
        raise OwnedSourcesRefused('ownership_directory_unavailable') from exc
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != uid or
            stat.S_IMODE(st.st_mode) != 0o700):
        raise OwnedSourcesRefused('unsafe_ownership_directory')


def _safe_bytes(path: Path, uid: int, max_bytes: int) -> bytes:
    try:
        named = path.lstat()
        if (not stat.S_ISREG(named.st_mode) or named.st_uid != uid or
                named.st_nlink != 1 or stat.S_IMODE(named.st_mode) != 0o600 or
                not 0 <= named.st_size <= max_bytes):
            raise OwnedSourcesRefused('unsafe_owned_component')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            first = os.fstat(fd)
            data = os.read(fd, max_bytes + 1)
            last = os.fstat(fd)
        finally:
            os.close(fd)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode)
        if (identity(named) != identity(first) or identity(first) != identity(last) or
                len(data) != named.st_size):
            raise OwnedSourcesRefused('owned_component_changed_during_read')
        return data
    except OSError as exc:
        raise OwnedSourcesRefused('owned_component_unreadable') from exc


def _create_once(path: Path, data: bytes, uid: int) -> None:
    """No overwrite or symlink following; durable link of complete root file."""
    temp = path.parent / ('.owned-' + secrets.token_hex(16) + '.part')
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.fchown(fd, uid, 0 if uid == 0 else os.getegid())
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OwnedSourcesRefused('short_ownership_write')
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.link(temp, path, follow_symlinks=False)
        _sync(path.parent)
    finally:
        if temp.exists():
            temp.unlink()
            _sync(path.parent)


def read_owned(root: Path = OWNED_ROOT, *, owner_uid: int = 0) -> dict | None:
    """Return explicit protected known-list sources, or None if never seeded.

    Caller must own the cross-component destination lock; this operation does
    not claim Config is stable, nor that any future P2k4 write is authorized.
    """
    root = Path(root)
    # An initial installation may not yet have the original shared-work
    # parent. Read-only absence must not provision it or invent ownership.
    if not root.parent.exists() and not root.parent.is_symlink():
        return None
    _safe_dir(root.parent, owner_uid)
    if not root.exists() and not root.is_symlink():
        return None
    _safe_dir(root, owner_uid)
    if set(os.listdir(root)) != {'manifest.json', 'youtube.txt', 'user.txt'}:
        raise OwnedSourcesRefused('incomplete_or_foreign_owned_sources')
    raw = _safe_bytes(root / 'manifest.json', owner_uid, 2048)
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise OwnedSourcesRefused('invalid_owned_manifest') from exc
    if (not isinstance(manifest, dict) or
            set(manifest) != {'schema', 'kind', 'known', 'initial_config_sha256'} or
            type(manifest['schema']) is not int or manifest['schema'] != 1 or
            manifest['kind'] != 'native-auto-owned-known-hostlists' or
            manifest['known'] != list(KNOWN_HOSTLISTS) or
            not isinstance(manifest['initial_config_sha256'], str) or
            not SHA256.fullmatch(manifest['initial_config_sha256'])):
        raise OwnedSourcesRefused('invalid_owned_manifest')
    owned = {}
    for name in KNOWN_HOSTLISTS:
        data = _safe_bytes(root / f'{name}.txt', owner_uid, MAX_COMPONENT)
        try:
            content = data.decode('utf-8')
            result = normalize(content, 'user')
        except (UnicodeError, ValueError, DomainPolicyError, AutoDomainPolicyError) as exc:
            raise OwnedSourcesRefused('invalid_owned_component_syntax') from exc
        if (any(row.startswith(('!', '^')) for row in content.splitlines()) or
                content != (result['normalized'] + '\n' if result['normalized'] else '')):
            raise OwnedSourcesRefused('noncanonical_owned_component')
        owned[name] = content
    return owned


def bootstrap_empty(root: Path, *, original_config_sha256: str,
                    owner_uid: int = 0, authorized_clean_start: bool = False) -> None:
    """Dormant *explicit* empty origin seal; no CLI calls this initializer.

    Authorized native FD9 owner must prove no prior automatic known-list
    generation and own the Config+destination lock. A guessed empty ledger is
    never created by read, package install, migration, or normal GUI saving.
    """
    if not authorized_clean_start or not isinstance(original_config_sha256, str) or \
            not SHA256.fullmatch(original_config_sha256):
        raise OwnedSourcesRefused('original_clean_bootstrap_authority_required')
    root = Path(root)
    _safe_dir(root.parent, owner_uid)
    if root.exists() or root.is_symlink():
        raise OwnedSourcesRefused('ownership_already_present_or_partial')
    root.mkdir(mode=0o700)
    _sync(root.parent)
    _safe_dir(root, owner_uid)
    for name in KNOWN_HOSTLISTS:
        _create_once(root / f'{name}.txt', b'', owner_uid)
    manifest = {'schema': 1, 'kind': 'native-auto-owned-known-hostlists',
                'known': list(KNOWN_HOSTLISTS),
                'initial_config_sha256': original_config_sha256}
    _create_once(root / 'manifest.json',
                 (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode(), owner_uid)
    _sync(root)


def snapshot(final: Path = AUTO_HOSTLIST, gui_lock: Path = AUTO_LOCK,
             owned_root: Path = OWNED_ROOT, *, owner_uid: int = 0) -> dict:
    """A single file lock spans final Auto HOSTLIST and known owned components.

    The PHP caller additionally holds the native Config lock across this
    call. A *completed* snapshot still cannot authorize a P2k4 write after
    either lock is released; no worker is registered.
    """
    with exclusive_destination_lock(gui_lock, owner_uid):
        current = _read_current(final, owner_uid)
        owned = read_owned(owned_root, owner_uid=owner_uid)
        return {'result': 'ok',
                'status': 'missing' if current is None else ('empty' if not current else 'populated'),
                'content': '' if current is None else current.decode('utf-8'),
                'revision': _revision(current),
                'auto_owned_components': owned,
                'auto_owned_complete': owned is not None}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0 or argv != ['read']:
        print(json.dumps({'result': 'error', 'reason': 'root_native_snapshot_only'}))
        return 0
    try:
        result = snapshot()
    except (OwnedSourcesRefused, DestinationRefused, ValueError, OSError, UnicodeError) as exc:
        result = {'result': 'error', 'reason': 'protected_owned_sources_unavailable'}
    print(json.dumps(result, ensure_ascii=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())