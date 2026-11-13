#!/usr/bin/env python3
"""Read-only verification of the original documentation streams at audit v0.6.5_15."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
manifest = json.loads(Path(__file__).with_name('DOCS-2026-11-13-PRESERVATION.json').read_text())
assert len(manifest['files']) == manifest['original_file_count']
total = 0
rewrites = 0
for original, record in manifest['files'].items():
    path = (root / record['location']).resolve()
    assert path.is_relative_to(root) and path.is_file(), (original, 'missing retained file')
    data = path.read_bytes()[record['offset']:record['offset'] + record['length']]
    assert hashlib.sha256(data).hexdigest() == record['retained_sha256'], (original, 'retained content changed')
    for change in reversed(record['link_rewrites']):
        before = change['before'].encode('utf-8', 'surrogateescape')
        after = change['after'].encode('utf-8', 'surrogateescape')
        assert data[change['start']:change['end']] == after, (original, 'unexpected rewrite')
        data = data[:change['start']] + before + data[change['end']:]
        rewrites += 1
    assert len(data) == record['original_bytes'], (original, 'original length mismatch')
    assert hashlib.sha256(data).hexdigest() == record['original_sha256'], (original, 'original digest mismatch')
    total += len(data)
assert total == manifest['original_bytes']
print(f"PRESERVATION=PASS: {len(manifest['files'])} original files, {total} original bytes, {rewrites} reversible Markdown edits")
