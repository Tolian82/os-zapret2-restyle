#!/usr/bin/env python3
"""Offline exact effective TLS profile Lua-action fingerprints; never runtime proof.

Use the installed production parser supplied by the evidence binder. Do not
interpret a configured action as an executed Lua action or a WAN mutation.
"""
from __future__ import annotations

import hashlib
import re

ACTION_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
ACTION_FAMILY = {
    'fake': 'FAKE',
    'fakedsplit': 'FAKE_SPLIT',
    'fakeddisorder': 'FAKE_SPLIT',
    'hostfakesplit': 'FAKE_SPLIT',
    'hostfakeddisorder': 'FAKE_SPLIT',
    'multisplit': 'SPLIT',
    'multidisorder': 'SPLIT',
    'tcpseg': 'SPLIT',
    'pktmod': 'HEADER_MUTATION',
}


class SignatureError(ValueError):
    pass


def candidate_signatures(argv: str, native, indexes: list[int], count: int) -> list[dict]:
    """Report only eligible executable ordinals. Never emit raw argv/Lua names."""
    if (not isinstance(count, int) or isinstance(count, bool) or count < 1 or
            count > 256 or not isinstance(indexes, list) or
            any(type(i) is not int or i < 1 or i > count for i in indexes) or
            len(indexes) != len(set(indexes))):
        raise SignatureError('invalid eligible profile ordinals')
    rows = native.segments(argv)
    templates, kinds = native.templates_and_imports(rows)
    if len(kinds) != len(rows):
        raise SignatureError('incomplete production parser profile types')
    selected = set(indexes)
    result, ordinal = [], 0
    for row, kind in zip(rows, kinds):
        if kind != 'profile':
            continue
        ordinal += 1
        if ordinal not in selected:
            continue
        tokens = native.inherited(native.visible(row), templates)
        if not isinstance(tokens, list) or any(not isinstance(t, str) for t in tokens):
            raise SignatureError('invalid production effective profile')
        families = []
        for token in tokens:
            if token == '--lua-desync' or token.startswith('--lua-desync='):
                if not token.startswith('--lua-desync='):
                    raise SignatureError('unverifiable positional Lua action')
                name = token.partition('=')[2].partition(':')[0]
                if not ACTION_NAME.fullmatch(name):
                    raise SignatureError('invalid effective Lua action')
                families.append(ACTION_FAMILY.get(name, 'OTHER_OR_CUSTOM'))
        fingerprint = hashlib.sha256('\x00'.join(tokens).encode('utf-8')).hexdigest()
        result.append({
            'profile_index': ordinal,
            'effective_profile_sha256': fingerprint,
            'lua_action_count': len(families),
            'lua_action_families': sorted(set(families)) if families else ['NONE'],
            'qualification': 'CONFIGURED_CANDIDATE_ONLY',
        })
    if ordinal != count or len(result) != len(indexes):
        raise SignatureError('production executable profile count changed')
    return result
