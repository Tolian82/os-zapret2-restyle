#!/usr/bin/env python3
"""P0 generation-bound attribution, exercised only by the detached witness.

Not installed, imported by production, or authorized to enable observation.
Uses the existing profile splitter/expander and final-argv segmentation.
Stage artifacts must come from ONE generation; no filename/domain/IP guessing.
P2 must integrate capture/persistence with the original generator/FD9 owner.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

BACKEND = Path(__file__).resolve().parents[2] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
import profile_policy
from global_exclusions import ARGS_LIMIT, BASE, ExclusionError, is_stun, segments, templates_and_imports, visible


class AttributionError(ValueError):
    pass


def _text(data: bytes) -> str:
    if not isinstance(data, bytes) or len(data) > ARGS_LIMIT or b"\x00" in data:
        raise AttributionError("invalid or oversized generation artifact")
    try:
        return data.decode("utf-8")
    except UnicodeError as exc:
        raise AttributionError("generation artifact is not UTF-8") from exc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _has_ipset(data: bytes) -> bool:
    return (any(kind == "IPSET" for kind, _ in profile_policy._supported(data)) or
            any(t.partition("=")[0] in {"--ipset", "--ipset-ip"} for t in _text(data).split()))


def _native_list(tokens: list[str]) -> bool:
    return any(t.partition("=")[0] in {"--hostlist", "--hostlist-domains", "--hostlist-auto"}
               for t in tokens)


def _without_blob_shorthand(tokens: list[str]) -> list[str]:
    # The only token-removal transformation performed by existing blobs.sh.
    return [t for t in tokens if not (t.startswith("--blob=") and ":" not in t[7:])]


def build_map(*, generation: str, mode: str, strategy: bytes, bindings: bytes,
              effective: list[bytes], normalized: list[bytes], resolved: list[bytes],
              ordinary: bytes, voice: bytes, extra: bytes, preamble: bytes,
              assembled: bytes, final: bytes, overlays: tuple[str, ...]) -> dict:
    """Bind actual pipeline captures to final native numbers, without writes.

    ``effective`` is captured after Target Mode, ``normalized`` after Python
    expansion, ``resolved`` from the resolver's per-profile outputs BEFORE
    blobs, and ``assembled`` before the existing final exclusion pass.
    ``overlays`` names only that pass's exact generated exclusion tokens.
    Invalid/misaligned stages refuse the whole map rather than align by text.
    """
    if not isinstance(generation, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", generation):
        raise AttributionError("missing or invalid generation identity")
    if mode not in {"all", "list", "auto"}:
        raise AttributionError("invalid Target Mode")
    captures = [strategy, bindings, ordinary, voice, extra, preamble, assembled, final,
                *effective, *normalized, *resolved]
    for capture in captures:
        _text(capture)
    if any(len(group) > profile_policy.MAX_PROFILES for group in (effective, normalized, resolved)):
        raise AttributionError("too many captured profiles")
    selector_bindings = {}
    for line in _text(bindings).splitlines():
        selector, tab, native = line.partition("\t")
        if (not tab or not profile_policy.SELECTOR.fullmatch(selector)
                or selector in selector_bindings or len(native.split()) != 1):
            raise AttributionError("invalid captured registry/storage binding")
        selector_bindings[selector] = native
    try:
        originals = profile_policy.split_profiles(strategy)
        if len(originals) != len(effective):
            raise AttributionError("source/Target Mode profile count mismatch")
        expected = []
        origins = []
        for source_no, (source, targeted) in enumerate(zip(originals, effective), 1):
            # Target Mode can append selectors, never rewrite an authored profile.
            if not targeted.startswith(source):
                raise AttributionError("Target Mode capture changed source identity")
            suffix = _text(targeted[len(source):]).split()
            if any(not profile_policy.SELECTOR.fullmatch(t) for t in suffix):
                raise AttributionError("unrecognized Target Mode transformation")
            for expanded in profile_policy.expand_profiles([targeted]):
                expected.append(expanded)
                selected = profile_policy._supported(expanded)
                origins.append(dict(
                    source_number=source_no, source_sha256=_sha(source),
                    source_selectors=[f"<{kind}:{name}>" for kind, name in profile_policy._supported(source)],
                    authored_has_ipset=_has_ipset(source), source_has_ipset=_has_ipset(targeted),
                    selector=f"<{selected[0][0]}:{selected[0][1]}>" if len(selected) == 1 else None,
                    raw_native_list=_native_list(_text(targeted).split()),
                ))
        if expected != normalized or len(resolved) != len(expected):
            raise AttributionError("normalized capture lost source order or profile identity")

        resolved_rows = []
        for original, native in zip(normalized, resolved):
            tokens, replacements = _text(original).split(), _text(native).split()
            if len(tokens) != len(replacements):
                raise AttributionError("target resolution changed token count")
            bindings = {}
            for token, replacement in zip(tokens, replacements):
                if profile_policy.SELECTOR.fullmatch(token):
                    kind = token[1:].partition(":")[0]
                    option = "--hostlist=" if kind == "HOSTLIST" else "--ipset="
                    if (not replacement.startswith(option) or not replacement[len(option):].startswith("/")
                            or selector_bindings.get(token) != replacement):
                        raise AttributionError("unverifiable native selector replacement")
                    if token in bindings and bindings[token] != replacement:
                        raise AttributionError("inconsistent native selector replacement")
                    bindings[token] = replacement
                elif token != replacement:
                    raise AttributionError("target resolution changed an authored argument")
            row = _without_blob_shorthand(replacements)
            if len(segments("\n".join(row))) != 1:
                raise AttributionError("untracked inline native profile boundary")
            resolved_rows.append(row)
        ordinary_tokens = []
        for row in resolved_rows:
            if ordinary_tokens:
                ordinary_tokens.append("--new")
            ordinary_tokens.extend(row)
        if ordinary_tokens != _text(ordinary).split():
            raise AttributionError("blob/ordinary capture changed profile order or content")

        base = _text(preamble).split()
        if not base or any(t.partition("=")[0] not in BASE for t in base):
            raise AttributionError("unverifiable generated argument preamble")
        if any(not t.startswith(("--hostlist-exclude=/", "--ipset-exclude=/")) for t in overlays):
            raise AttributionError("unverifiable generated exclusion overlay")
        if len(overlays) != len(set(overlays)):
            raise AttributionError("duplicate generated exclusion identity")

        voice_tokens, extra_tokens = _text(voice).split(), _text(extra).split()
        traffic = voice_tokens + (["--new"] if voice_tokens and ordinary_tokens else []) + ordinary_tokens
        actual = _text(assembled).split()
        expected_tokens = base + traffic + extra_tokens
        # generator_build_args_mapped appends the synthetic domain exclusion.
        domain_tail = [t for t in overlays if t.startswith("--hostlist-exclude=")]
        if actual != expected_tokens + domain_tail:
            raise AttributionError("generator assembly is not the captured generation")
        before_rows, after_rows = segments(_text(assembled)), segments(_text(final))
        if len(before_rows) != len(after_rows) or any(
            [t for t in left if t not in overlays] != [t for t in right if t not in overlays]
            for left, right in zip(before_rows, after_rows)
        ):
            raise AttributionError("final policy changed native profile identity")
        _, kinds = templates_and_imports(after_rows)
        labels = [dict(role="voice") for _ in (segments(_text(voice)) if voice_tokens else [])]
        labels += [dict(origin, role="strategy") for origin in origins]
        if not labels:
            labels = [dict(role="engine-base")]
        if extra_tokens and extra_tokens[0] != "--new" and not extra_tokens[0].startswith("--new="):
            labels[-1] = dict(labels[-1], extra_modified=True)
        labels.extend(dict(role="extra") for token in extra_tokens
                      if token == "--new" or token.startswith("--new="))
        if len(labels) != len(after_rows):
            raise AttributionError("Voice/Extra composition changed native profile count")
    except (profile_policy.ProfilePolicyError, ExclusionError) as exc:
        raise AttributionError("unverifiable canonical profile structure") from exc

    records = []
    native_number = 0
    for ordinal, (row, kind, origin) in enumerate(zip(after_rows, kinds, labels), 1):
        tokens = visible(row)
        skip = "--skip" in tokens
        number = None
        if kind != "template" and not skip:
            native_number += 1
            number = native_number
        hostlist = None
        if skip or kind == "template":
            status = "non-executable-skip" if skip else "non-executable-template"
        elif origin["role"] == "voice":
            status = "excluded-voice"
        elif is_stun(tokens):
            status = "excluded-stun"
        elif origin.get("source_has_ipset") or _has_ipset("\n".join(tokens).encode()):
            status = "excluded-ipset"
        elif any(t == "--import" or t.startswith("--import=") for t in tokens):
            # Native dp_copy can replace targets and identity; never approximate it.
            status = "unknown-import"
        elif origin.get("raw_native_list"):
            status = "unknown-native-list"
        elif origin.get("extra_modified") or origin["role"] == "extra":
            status = "unknown-extra"
        elif (origin.get("selector") or "").startswith("<HOSTLIST:"):
            hostlist = origin["selector"][10:-1]
            status = "known-hostlist"
        else:
            status = "unknown-source"
        records.append(dict(
            id=f"{generation}:{ordinal}", native_number=number, role=origin["role"],
            source_number=origin.get("source_number"), source_sha256=origin.get("source_sha256"),
            source_selectors=origin.get("source_selectors", []),
            authored_has_ipset=origin.get("authored_has_ipset", False),
            source_has_ipset=origin.get("source_has_ipset", False),
            selector=origin.get("selector"), hostlist=hostlist, status=status,
        ))
    # Upstream appends a separate low-priority no_action profile numbered 0.
    records.append(dict(id=f"{generation}:default", native_number=0,
                        role="native-default", source_number=None, source_sha256=None,
                        source_selectors=[], authored_has_ipset=False, source_has_ipset=False,
                        selector=None, hostlist=None, status="unknown-native-default"))
    digest = hashlib.sha256()
    for capture in captures:
        digest.update(len(capture).to_bytes(8, "big"))
        digest.update(capture)
    return dict(schema=1, generation=generation, mode=mode,
                evidence="P0_DETACHED_GENERATOR_ONLY", final_args_sha256=_sha(final),
                strategy_sha256=_sha(strategy), captures_sha256=digest.hexdigest(), profiles=records)


def lookup(mapping: dict, generation: str, final: bytes, native_number: int) -> dict | None:
    """A stale/missing number is unknown; the future worker uses shared fallback.

    Excluded records are returned as excluded, never converted to HOSTLIST.
    Protected map/process/debug/pending publication is a separate P2 boundary.
    """
    if (not isinstance(mapping, dict) or type(native_number) is not int or native_number < 0 or mapping.get("schema") != 1
            or mapping.get("generation") != generation
            or mapping.get("final_args_sha256") != _sha(final)):
        return None
    records = mapping.get("profiles")
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        return None
    matches = [row for row in records if row.get("native_number") == native_number]
    return dict(matches[0]) if len(matches) == 1 else None
