#!/usr/bin/env python3
"""Read-only Stage 0 legacy FreeBSD.conf residue triage.

An exact old override and an apparently valid backup are NOT proof of plugin
ownership or absence of third-party edits. This tool never permits restoration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

OVERRIDE = b'FreeBSD-ports: { enabled: yes }\n'
LIMIT = 1024 * 1024


def observe(path):
    """Do not follow symlinks, print contents, or mutate paths."""
    try:
        entry = path.lstat()
    except FileNotFoundError:
        return {'kind': 'absent'}
    except OSError as exc:
        return {'kind': 'unreadable', 'error_category': type(exc).__name__}
    if stat.S_ISLNK(entry.st_mode):
        return {'kind': 'symlink'}
    if not stat.S_ISREG(entry.st_mode):
        return {'kind': 'nonregular'}
    if entry.st_size > LIMIT:
        return {'kind': 'oversize', 'size': entry.st_size}
    try:
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino):
                return {'kind': 'changed-during-read'}
            content = b''
            while len(content) <= LIMIT:
                part = os.read(fd, min(65536, LIMIT + 1 - len(content)))
                if not part:
                    break
                content += part
            after = os.fstat(fd)
            if len(content) > LIMIT or len(content) != opened.st_size or (after.st_mtime_ns, after.st_size) != (opened.st_mtime_ns, opened.st_size):
                return {'kind': 'changed-during-read'}
        finally:
            os.close(fd)
    except OSError as exc:
        return {'kind': 'unreadable', 'error_category': type(exc).__name__}
    return {'kind': 'regular', 'sha256': hashlib.sha256(content).hexdigest(),
            'size': len(content), 'legacy_template_exact': content == OVERRIDE,
            'legacy_disabled_marker': bool(re.search(rb'enabled:\s*no\b', content, re.IGNORECASE))}


def evaluate(repo, backup):
    a, b = observe(Path(repo)), observe(Path(backup))
    classification = 'ambiguous-refuse'
    if a['kind'] == b['kind'] == 'absent':
        classification = 'no-residue'
    elif a['kind'] not in ('absent', 'regular') or b['kind'] not in ('absent', 'regular'):
        classification = 'unsafe-filesystem-object-refuse'
    elif a['kind'] == 'regular' and not a['legacy_template_exact']:
        classification = 'foreign-or-edited-repo-refuse'
    elif a['kind'] == 'regular' and b['kind'] == 'regular':
        if b['size'] == 0 or b['legacy_template_exact'] or not b['legacy_disabled_marker']:
            classification = 'invalid-or-ambiguous-backup-refuse'
        else:
            classification = 'legacy-shape-candidate-requires-independent-ownership-proof'
    return {
        'schema': 1,
        'proof': 'read-only-shape-and-digests-not-ownership',
        'classification': classification,
        'repo': a,
        'backup': b,
        'automatic_restore_allowed': False,
        'ownership_verified': False,
        'foreign_edits_excluded': False,
        'recommended_action': ('no-residue-to-restore' if classification == 'no-residue'
                               else 'preserve-both-and-review-provenance-manually'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path,
                        default=Path('/usr/local/etc/pkg/repos/FreeBSD.conf'))
    parser.add_argument('--backup', type=Path,
                        default=Path('/var/db/zapret2-restyle/FreeBSD.conf.backup'))
    parser.add_argument('--json', type=Path, help='optional sanitized JSON output')
    args = parser.parse_args()
    result = evaluate(args.repo, args.backup)
    output = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.json:
        args.json.write_text(output, encoding='utf-8')
    print(output, end='')


if __name__ == '__main__':
    main()
