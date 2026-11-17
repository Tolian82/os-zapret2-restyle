#!/usr/bin/env python3
"""TZ6v2 STEP 5: five-source semantic preview, without granting a write.

The root Apply owner must hold the original Config + destination locks, verify
FD9/epoch and perform an all-resource durable commit before using any plan.
This module is pure: it reuses the original P1 parser and the STEP 5 three-way
source merge, never creates an alternative Config/Auto writer.
"""
from __future__ import annotations

from domain_policy import (_covers, _list_entries, AutoDomainPolicyError,
                           PublicSuffixList)
from auto_detect_editor_merge import (EditorMergeRefused, MAX_BYTES,
                                      preview_found_merge)

SOURCES = ('youtube', 'user', 'auto')
KNOWN = ('youtube', 'user')


class FiveEditorPlanRefused(ValueError):
    """Stable bounded diagnostic, never includes user-supplied domains."""

    def __init__(self, source: str, code: str):
        super().__init__(code)
        self.source, self.code = source, code

    def evidence(self) -> dict:
        return {'source': self.source, 'code': self.code}


def _rows(text: str, source: str, kind: str = 'user') -> list[tuple[str, bool, bool]]:
    if not isinstance(text, str) or len(text.encode('utf-8')) > 4 * 1024 * 1024:
        raise FiveEditorPlanRefused(source, 'unbounded_manual_or_exclusion')
    try:
        return _list_entries(text, kind)
    except (AutoDomainPolicyError, ValueError, TypeError):
        raise FiveEditorPlanRefused(source, 'invalid_manual_or_exclusion') from None


def preview_five_sources(baselines: dict, drafts: dict, currents: dict,
                         manual: dict, global_exclude: str = '', *,
                         psl: PublicSuffixList | None = None) -> dict:
    """Return prospective five-list dedup under original P1 coverage semantics.

    Each found source first rebases baseline->draft user edits onto current
    protected bytes (STEP 5), then manual broad/exact positives/negatives and
    known-list precedence determine which proposed positives remain. Unknown
    cross-known source provenance is refused rather than silently rehomed.
    Manual input is read/validated, never sorted, collapsed or returned as a
    proposed XML write here. This cannot authorize Config/files transaction.
    """
    if any(not isinstance(v, dict) for v in (baselines, drafts, currents, manual)) or (
            set(baselines) != set(SOURCES) or set(currents) != set(SOURCES) or
            set(drafts) != set(SOURCES) or set(manual) != set(KNOWN)):
        raise FiveEditorPlanRefused('all', 'incomplete_five_source_input')
    psl = psl if psl is not None else PublicSuffixList.load()
    manual_rows = {source: _rows(manual[source], source) for source in KNOWN}
    exclusions = _rows(global_exclude, 'global_exclude', 'exclude')
    # Existing P1 global exclusion and manual negative both veto discovered
    # positives regardless of the source the collector attributed them to.
    exclusions.extend(row for rows in manual_rows.values() for row in rows if row[1])

    merged = {}
    for source in SOURCES:
        try:
            merged[source] = preview_found_merge(
                source, baselines[source], drafts[source], currents[source], psl=psl)
        except EditorMergeRefused as exc:
            raise FiveEditorPlanRefused(source, exc.code) from None
    candidates = {source: set(merged[source]['content'].splitlines()) for source in SOURCES}
    removals = {source: {'excluded': 0, 'manual_covered': 0,
                         'known_covered': 0} for source in SOURCES}

    for source in SOURCES:
        for root in tuple(candidates[source]):
            if any(_covers(root, row) for row in exclusions):
                candidates[source].remove(root)
                removals[source]['excluded'] += 1
            elif source in KNOWN and any(
                    not row[1] and _covers(root, row) for row in manual_rows[source]):
                candidates[source].remove(root)
                removals[source]['manual_covered'] += 1
    # Original P1 does not guess the owner of an ambiguous cross-known root:
    # a running discovery can route it to the shared fallback only with its
    # authenticated profile provenance. Pure stale editor text is not that.
    if candidates['youtube'] & candidates['user']:
        raise FiveEditorPlanRefused('known', 'ambiguous_known_source_provenance')

    effective_known = {name: [row for row in manual_rows[name] if not row[1]]
                       + [(root, False, False) for root in candidates[name]]
                       for name in KNOWN}
    for root in tuple(candidates['auto']):
        if any(_covers(root, row) for rows in effective_known.values() for row in rows):
            candidates['auto'].remove(root)
            removals['auto']['known_covered'] += 1

    sources = {}
    for source in SOURCES:
        content = ''.join(root + '\n' for root in sorted(candidates[source]))
        if len(content.encode('utf-8')) > MAX_BYTES:
            raise FiveEditorPlanRefused(source, 'prospective_source_over_limit')
        sources[source] = {
            'content': content,
            'base_revision': merged[source]['base_revision'],
            'current_revision': merged[source]['current_revision'],
            'rebased': merged[source]['rebased'],
            'would_change_current': content != currents[source]['content'],
            'user_added': merged[source]['user_added'],
            'user_removed': merged[source]['user_removed'],
            'coverage_removals': removals[source],
        }
    return {
        'schema_version': 1, 'result': 'preview_only',
        'sources': sources, 'manual_untouched': True,
        'cross_source_validated': True, 'commit_authorized': False,
    }
