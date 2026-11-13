#!/usr/bin/env python3
"""#1052 P3: compose effective known HOSTLISTs from manual and owned sources.

The real managed-target builder is the only product caller. A complete
sealed auto-owned snapshot is read under the existing destination flock.
Missing storage does not create any file or change the original manual build.
No native observer, writer, Config mutation, hot reload, or ACK is enabled.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

from auto_detect_destination_commit import (DestinationRefused, _target, _replace,
                                            exclusive_destination_lock)
from auto_detect_gui_hostlist import AUTO_LOCK
from auto_detect_owned_sources import (KNOWN_HOSTLISTS, OWNED_ROOT, read_owned,
                                       OwnedSourcesRefused)
from domain_policy import (normalize, _list_entries, _covers, DomainPolicyError,
                           AutoDomainPolicyError, MAX_INPUT_BYTES)


class EffectiveKnownRefused(RuntimeError):
    """Reject partial provenance or unsafe output rather than lose manual rows."""


def compose_known(manual: dict[str, str], owned: dict[str, str]) -> dict[str, str]:
    """Preserve manual modifiers and order; append only uncovered plain rows."""
    if (not isinstance(manual, dict) or not isinstance(owned, dict) or
            set(manual) != set(KNOWN_HOSTLISTS) or
            set(owned) != set(KNOWN_HOSTLISTS) or
            any(type(v) is not str for v in (*manual.values(), *owned.values()))):
        raise EffectiveKnownRefused('incomplete_known_hostlist_components')
    entries = {}
    negatives = []
    for name in KNOWN_HOSTLISTS:
        original = manual[name]
        normal = normalize(original, name)['normalized']
        canonical = normal + ('\n' if normal else '')
        if original != canonical:
            raise EffectiveKnownRefused('noncanonical_managed_hostlist')
        entries[name] = _list_entries(original, name)
        negatives.extend(row for row in entries[name] if row[1])
    result = {}
    for name in KNOWN_HOSTLISTS:
        manual_hosts = {row[0] for row in entries[name]}
        lines = manual[name].splitlines()
        for row in _list_entries(owned[name], name):
            host, excluded, exact = row
            if excluded or exact:
                raise EffectiveKnownRefused('noncanonical_automatic_hostlist')
            if host in manual_hosts or any(_covers(host, neg) for neg in negatives):
                continue
            if host not in lines:
                lines.append(host)
        effective = '\n'.join(lines) + ('\n' if lines else '')
        if len(effective.encode('utf-8')) > MAX_INPUT_BYTES:
            raise EffectiveKnownRefused('effective_hostlist_too_large')
        result[name] = effective
    return result


def compose_stage(youtube: Path, user: Path, *,
                  root: Path = OWNED_ROOT, lock: Path = AUTO_LOCK,
                  owner_uid: int = 0) -> dict:
    """Edit only detached staging outputs, never Config or private sources.

    A failed second replace rejects the entire detached release; it is not
    published by the original builder on any nonzero result.
    """
    paths = {'youtube': Path(youtube), 'user': Path(user)}
    if any(not path.is_absolute() for path in paths.values()) or len(set(paths.values())) != 2:
        raise EffectiveKnownRefused('unsafe_staging_paths')
    root = Path(root)
    if not root.exists() and not root.is_symlink():
        if read_owned(root, owner_uid=owner_uid) is not None:
            raise EffectiveKnownRefused('unqualified_source_absence')
        return {'status': 'uninitialized', 'changed': []}
    with exclusive_destination_lock(Path(lock), owner_uid):
        owned = read_owned(root, owner_uid=owner_uid)
        if owned is None:
            raise EffectiveKnownRefused('source_disappeared_under_lock')
        before = {name: _target(path, owner_uid)[0] for name, path in paths.items()}
        try:
            manual = {name: before[name].decode('utf-8') for name in paths}
        except UnicodeError as exc:
            raise EffectiveKnownRefused('invalid_managed_hostlist_encoding') from exc
        merged = compose_known(manual, owned)
        changed = []
        for name in KNOWN_HOSTLISTS:
            content = merged[name].encode('utf-8')
            if before[name] != content:
                _replace(paths[name], before[name], content, owner_uid)
                changed.append(name)
        return {'status': 'composed', 'changed': changed}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3 or argv[0] != 'compose':
        print('ERROR: native effective HOSTLIST invocation refused', file=sys.stderr)
        return 2
    # Portable offline builders have no native auto-owned storage. Their
    # strictly read-only no-op is required for existing Linux source tests;
    # only root on FreeBSD may read or mutate an initialized owned source.
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        try:
            if read_owned(OWNED_ROOT, owner_uid=0) is None:
                return 0
        except (OwnedSourcesRefused, OSError):
            pass
        print('ERROR: native effective HOSTLIST invocation refused', file=sys.stderr)
        return 2
    try:
        compose_stage(Path(argv[1]), Path(argv[2]))
        return 0
    except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
            DomainPolicyError, AutoDomainPolicyError, ValueError, OSError):
        print('ERROR: protected effective HOSTLIST composition unavailable', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
