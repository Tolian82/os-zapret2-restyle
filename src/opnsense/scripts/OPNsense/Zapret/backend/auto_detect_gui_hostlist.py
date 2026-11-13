#!/usr/bin/env python3
"""#1052: native root-owned GUI editor for the shared final Auto HOSTLIST.

Only revisioned `read`, `save` and explicit reviewed legacy `migrate` use configd. This does
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
from auto_detect_epoch_receipts import (ReceiptRefused, _write_once,
                                        _read as _read_receipt, _directory, _canonical)

AUTO_HOSTLIST = Path('/usr/local/etc/zapret2/ipset/auto-domains.txt')
AUTO_LOCK = Path('/usr/local/etc/zapret2/ipset/.auto-domains.lock')
LEGACY_HOSTLIST = Path('/usr/local/etc/zapret2/ipset/zapret-hosts-auto.txt')
MAX_GUI_BYTES = 40 * 1024  # bounded configd argv; native hostlist may be larger
MAX_TOKEN = 57000
MIGRATION_DIR = ".auto-domains-legacy-migration"
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
        legacy_state = _legacy_status(path, legacy, data, owner_uid)
        return {
            'legacy': legacy_state,
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



def _root_migration(path: Path, uid: int, *, create: bool = False) -> Path:
    """A one-shot root-private receipt; never replace it on subsequent reads."""
    folder = path.parent / MIGRATION_DIR
    if create and not folder.exists() and not folder.is_symlink():
        folder.mkdir(mode=0o700)
        _sync(path.parent)
    if folder.exists() or folder.is_symlink():
        _directory(folder, uid)
        if set(os.listdir(folder)) - {'plan.json', 'done.json'}:
            raise AutoHostlistRefused('foreign_migration_receipts')
    return folder


def _receipt_state(folder: Path, uid: int) -> tuple[dict | None, dict | None]:
    if not folder.exists() and not folder.is_symlink():
        return None, None
    plan_path, done_path = folder / 'plan.json', folder / 'done.json'
    if not plan_path.exists() and not plan_path.is_symlink():
        # Crash after mkdir but before the first immutable plan: retry safely.
        if not list(folder.iterdir()):
            return None, None
        raise AutoHostlistRefused('missing_migration_plan')
    raw = _read_receipt(plan_path, uid)
    plan = json.loads(raw)
    if (not isinstance(plan, dict) or set(plan) != {'schema', 'kind', 'legacy',
            'before', 'after', 'added'} or type(plan['schema']) is not int or plan['schema'] != 1 or
            plan['kind'] != 'auto-hostlist-legacy-merge' or
            any(type(plan[k]) is not str or not HASH.fullmatch(plan[k])
                for k in ('legacy', 'before', 'after')) or
            type(plan['added']) is not int or not (0 <= plan['added'] <= 4096)):
        raise AutoHostlistRefused('invalid_migration_plan')
    done = None
    if done_path.exists() or done_path.is_symlink():
        done = json.loads(_read_receipt(done_path, uid))
        if (not isinstance(done, dict) or set(done) != {'schema', 'plan_sha256'} or
                type(done['schema']) is not int or done['schema'] != 1 or done['plan_sha256'] != hashlib.sha256(raw).hexdigest()):
            raise AutoHostlistRefused('invalid_migration_completion')
    return plan, done


def _write_done(folder: Path, plan: dict, uid: int) -> None:
    _write_once(folder, 'done.json', _canonical({
        'schema': 1, 'plan_sha256': hashlib.sha256(_canonical(plan)).hexdigest()
    }), uid)


def _domain_row(line: str) -> tuple[str, str, bool, bool]:
    prefix = line[:len(line)-len(line.lstrip('!^'))]
    host = line[len(prefix):]
    return line, host, '!' in prefix, '^' in prefix


def _overlaps(first: tuple, second: tuple) -> bool:
    a, b = first[1], second[1]
    if a == b:
        return True
    return ((not first[3] and b.endswith('.' + a)) or
            (not second[3] and a.endswith('.' + b)))


def _merge_bytes(current: bytes, legacy: bytes) -> tuple[bytes, int]:
    """Append ONLY previously absent normalized rows, keeping manual bytes.

    A mixed positive/negative overlap or duplicate host with different flags
    is ambiguous: leave BOTH files untouched for user review, never guess.
    """
    try:
        new_rows = normalize(current.decode('utf-8'), 'user')['normalized'].splitlines()
        old_rows = normalize(legacy.decode('utf-8'), 'user')['normalized'].splitlines()
    except (UnicodeError, DomainPolicyError, AutoDomainPolicyError) as exc:
        raise AutoHostlistRefused('legacy_requires_manual_review') from exc
    present = {_domain_row(line)[1]: _domain_row(line) for line in new_rows}
    inserted: list[str] = []
    for line in old_rows:
        row = _domain_row(line)
        existing = present.get(row[1])
        if existing:
            if existing != row:
                raise AutoHostlistRefused('legacy_modifier_conflict')
            continue
        # An exclusion that matches another positive from either file is
        # ambiguous under native local ! semantics, even for deep subdomains.
        for other in present.values():
            if _overlaps(row, other) and row[2] != other[2]:
                raise AutoHostlistRefused('legacy_exclusion_conflict')
        present[row[1]] = row
        inserted.append(line)
    extra = (b'' if not inserted else
             (b'\n' if current and not current.endswith(b'\n') else b'') +
             ('\n'.join(inserted) + '\n').encode('utf-8'))
    if len(current) + len(extra) > MAX_GUI_BYTES:
        raise AutoHostlistRefused('migration_would_exceed_gui_limit')
    return current + extra, len(inserted)


def _legacy_status(path: Path, legacy: Path, current: bytes | None,
                   uid: int) -> dict:
    """Read-only preview except safe same-content one-shot receipt seeding."""
    if current is None:
        return {'status': 'none'}
    try:
        if path == legacy or path.parent != legacy.parent:
            raise AutoHostlistRefused('unsafe_legacy_source')
        old = _read_current(legacy, uid)
        if old is None:
            return {'status': 'none'}
        folder = _root_migration(path, uid)
        plan, done = _receipt_state(folder, uid)
        digest = _revision(old)
        if plan is not None:
            if digest != plan['legacy']:
                return {'status': 'review_required', 'reason': 'legacy_changed'}
            if done is not None:
                return {'status': 'already_imported'}
            if _revision(current) in (plan['before'], plan['after']):
                return {'status': 'resume_available', 'digest': digest, 'added': plan['added']}
            return {'status': 'review_required', 'reason': 'interrupted_migration_conflict'}
        result, added = _merge_bytes(current, old)
        if result == current:
            # This also seals the old P2k5 first-copy path: a later user
            # deletion cannot become an implicit import candidate.
            plan = _record_migration(path, uid, digest, current, result, 0)
            _write_done(_root_migration(path, uid), plan, uid)
            return {'status': 'already_imported'}
        return {'status': 'available', 'digest': digest, 'added': added}
    except (AutoHostlistRefused, DestinationRefused, ReceiptRefused,
            ValueError, OSError, TypeError):
        return {'status': 'review_required', 'reason': 'legacy_unsafe_or_conflicting'}


def _record_migration(path: Path, uid: int, digest: str,
                      before: bytes, after: bytes, added: int) -> dict:
    folder = _root_migration(path, uid, create=True)
    plan = {'schema': 1, 'kind': 'auto-hostlist-legacy-merge',
            'legacy': digest, 'before': _revision(before),
            'after': _revision(after), 'added': added}
    _write_once(folder, 'plan.json', _canonical(plan), uid)
    return plan


def migrate_current(revision: str, legacy_digest: str,
                    path: Path = AUTO_HOSTLIST, lock: Path = AUTO_LOCK, *,
                    legacy: Path = LEGACY_HOSTLIST, owner_uid: int = 0) -> dict:
    """Explicit user-confirmed one-time legacy union; no removal of source."""
    if (type(revision) is not str or type(legacy_digest) is not str or
            not HASH.fullmatch(revision) or not HASH.fullmatch(legacy_digest)):
        raise AutoHostlistRefused('invalid_migration_tokens')
    if path == legacy or path.parent != legacy.parent:
        raise AutoHostlistRefused('unsafe_legacy_source')
    with exclusive_destination_lock(lock, owner_uid):
        current = _read_current(path, owner_uid)
        old = _read_current(legacy, owner_uid)
        if current is None or old is None or _revision(current) != revision or \
                _revision(old) != legacy_digest:
            return {'result': 'conflict', 'reason': 'source_changed'}
        folder = _root_migration(path, owner_uid)
        plan, done = _receipt_state(folder, owner_uid)
        if plan is not None:
            if plan['legacy'] != legacy_digest or done is not None:
                return {'result': 'conflict', 'reason': 'already_imported_or_changed'}
            if _revision(current) == plan['after']:
                _write_done(folder, plan, owner_uid)
                return {'result': 'migrated', 'revision': _revision(current),
                        'added': plan['added']}
            if _revision(current) != plan['before']:
                return {'result': 'conflict', 'reason': 'source_changed_after_prepare'}
            after, count = _merge_bytes(current, old)
            if _revision(after) != plan['after'] or count != plan['added']:
                raise AutoHostlistRefused('migration_plan_diverged')
        else:
            after, count = _merge_bytes(current, old)
            plan = _record_migration(path, owner_uid, legacy_digest, current, after, count)
            folder = _root_migration(path, owner_uid)
        if after != current:
            # Reconfirm the independently writable legacy source immediately
            # before replacing the new file: a changed inode/content refuses.
            if _revision(_read_current(legacy, owner_uid)) != legacy_digest:
                return {'result': 'conflict', 'reason': 'legacy_changed'}
            _replace(path, current, after, owner_uid)
        # A native writer might ignore our GUI lock on the *legacy* source.
        # Never seal completion if that source changed during replacement.
        if _revision(_read_current(legacy, owner_uid)) != legacy_digest:
            return {'result': 'conflict', 'reason': 'legacy_changed_during_merge'}
        _write_done(folder, plan, owner_uid)
        return {'result': 'migrated', 'revision': _revision(after),
                'added': count}


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
            not argv or argv[0] not in ('read', 'save', 'migrate') or
            (argv[0] == 'read' and len(argv) != 1) or
            (argv[0] == 'save' and len(argv) != 2) or
            (argv[0] == 'migrate' and len(argv) != 3)):
        print(json.dumps({'result': 'error', 'reason': 'native_request_refused'}))
        return 0
    try:
        result = (read_current() if argv[0] == 'read' else
                  save_current(*_unpack(argv[1])) if argv[0] == 'save' else
                  migrate_current(argv[1], argv[2]))
    except (AutoHostlistRefused, DestinationRefused, ReceiptRefused, OSError, ValueError,
            UnicodeError, TypeError, KeyError) as exc:
        # Never log user domains or the contents of a failed transport.
        result = {'result': 'error', 'reason': str(exc) if isinstance(exc, AutoHostlistRefused)
                  else 'native_file_unavailable'}
    print(json.dumps(result, ensure_ascii=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())