#!/usr/bin/env python3
"""TZ6v2 STEP 5: pure three-way merge preview for protected found-only sources.

No filesystem, Config, FD9, transaction, or service operations. Original
Config + destination owner must obtain fresh locked current bytes and perform
cross-source coverage checks before committing anything.
"""
from __future__ import annotations

import hashlib
import re

from domain_policy import (AutoDomainPolicyError, FoundEditorPolicyError,
                           PublicSuffixList, normalize_found_editor)

SOURCES = frozenset(('youtube', 'user', 'auto'))
MAX_BYTES = 40 * 1024
SHA256 = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)


class EditorMergeRefused(ValueError):
    """No untrusted domain text in the diagnostic."""

    def __init__(self, source: str, code: str):
        super().__init__(code)
        self.source, self.code = source, code

    def evidence(self) -> dict:
        return {'source': self.source, 'code': self.code}


def _verified_rows(source: str, record: dict, psl: PublicSuffixList) -> set[str]:
    if not isinstance(record, dict) or set(record) != {'status', 'revision', 'content'}:
        raise EditorMergeRefused(source, 'invalid_snapshot_shape')
    status, content, revision = record['status'], record['content'], record['revision']
    if status == 'uninitialized':
        # A pre-bootstrap known source is not a verified blank editor.
        raise EditorMergeRefused(source, 'owned_source_not_initialized')
    statuses = ('missing', 'empty', 'populated') if source == 'auto' else ('empty', 'populated')
    if status not in statuses or not isinstance(content, str) or len(content.encode('utf-8')) > MAX_BYTES:
        raise EditorMergeRefused(source, 'invalid_snapshot_state')
    if not isinstance(revision, str) or not SHA256.fullmatch(revision):
        raise EditorMergeRefused(source, 'invalid_snapshot_revision')
    expected = hashlib.sha256(b'missing\0' if status == 'missing'
                              else b'present\0' + content.encode('utf-8')).hexdigest()
    if expected != revision:
        raise EditorMergeRefused(source, 'revision_content_mismatch')
    if (status == 'missing' and content != '' or
            status == 'empty' and content != '' or
            status == 'populated' and not content):
        raise EditorMergeRefused(source, 'status_content_mismatch')
    try:
        normalized = normalize_found_editor(content, source, psl=psl)['normalized']
    except (AutoDomainPolicyError, FoundEditorPolicyError, ValueError, TypeError):
        raise EditorMergeRefused(source, 'unsafe_saved_domain_list') from None
    # Exact protected disk canonical bytes are line-sorted, newline-terminated.
    canonical = normalized + '\n' if normalized else ''
    if content != canonical:
        raise EditorMergeRefused(source, 'noncanonical_saved_domain_list')
    return set(normalized.splitlines())


def preview_found_merge(source: str, baseline: dict, draft: str,
                        current: dict, *, psl: PublicSuffixList | None = None) -> dict:
    """Apply user's baseline-relative membership deltas onto CURRENT storage.

    Explicit deletion of a baseline row wins; independently added current rows
    survive. Return only an uncommitted candidate, never an authorization to
    write; multi-source coverage, Config/FD9 and rollback are still REQUIRED.
    """
    if source not in SOURCES:
        raise EditorMergeRefused(str(source), 'unknown_source')
    if not isinstance(draft, str) or len(draft.encode('utf-8')) > MAX_BYTES:
        raise EditorMergeRefused(source, 'invalid_draft')
    psl = psl if psl is not None else PublicSuffixList.load()
    old = _verified_rows(source, baseline, psl)
    live = _verified_rows(source, current, psl)
    try:
        edited_text = normalize_found_editor(draft, source, psl=psl)['normalized']
    except FoundEditorPolicyError as error:
        raise EditorMergeRefused(source, 'invalid_draft_line_' + str(error.line) + '_' + error.code) from None
    except (ValueError, AutoDomainPolicyError, TypeError):
        raise EditorMergeRefused(source, 'invalid_draft') from None
    desired = set(edited_text.splitlines())
    # For known ownership, a vanished source cannot be mistaken for empty.
    if source == 'auto' and baseline['status'] != 'missing' and current['status'] == 'missing':
        raise EditorMergeRefused(source, 'source_disappeared_during_edit')
    remove = old - desired
    add = desired - old
    merged = sorted((live - remove) | add)
    candidate = ('\n'.join(merged) + '\n') if merged else ''
    if len(candidate.encode('utf-8')) > MAX_BYTES:
        raise EditorMergeRefused(source, 'merged_source_over_limit')
    return {
        'schema_version': 1, 'result': 'preview_only', 'source': source,
        'base_revision': baseline['revision'], 'current_revision': current['revision'],
        'rebased': baseline['revision'] != current['revision'],
        'user_added': len(add), 'user_removed': len(remove),
        'content': candidate, 'would_change_current': candidate != current['content'],
        'cross_source_validated': False, 'commit_authorized': False,
    }
