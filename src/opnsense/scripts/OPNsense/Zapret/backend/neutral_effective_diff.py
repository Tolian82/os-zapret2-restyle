#!/usr/bin/env python3
"""TZ6v5 S08d: pure, detached effective/semantic change classifier.

Snapshot data must be produced by the ORIGINAL candidate generator; this
module cannot read/attest live files, generate dvtws args, acquire FD9,
authorize reload/Start/Stop, write a resource or signal a process.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from global_exclusions import ExclusionError, segments

_MANAGED = "/usr/local/etc/zapret2/runtime-v2/managed/"
_REF_OPTIONS = frozenset(("--hostlist", "--ipset", "--hostlist-exclude",
                          "--ipset-exclude"))
_REF_FILE = re.compile(r"(?:hostlist|ipset)-[a-z][a-z0-9-]{0,63}\.txt\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ENGINE = re.compile(r"[A-Za-z0-9_.+-]{1,64}\Z")
_WAN = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}\Z")
_SELECTOR = re.compile(r"<(?:HOSTLIST|IPSET):[a-z][a-z0-9_-]*>\Z")
_MAX_ARGS = 262144
_FIRST_RULE = 19000
_LAST_RULE = 19099


class EffectiveDiffRefused(ValueError):
    """Stable, content-free refusal. Never echo original args or user lists."""


@dataclass(frozen=True)
class EffectiveSnapshot:
    structural_sha256: str
    argv_sha256: str
    linked: tuple[tuple[str, str], ...]
    unlinked: tuple[tuple[str, str], ...]
    external_ref_count: int
    status: str = "DETACHED_EFFECTIVE_INPUT_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


@dataclass(frozen=True)
class EffectiveDecision:
    kind: str
    changed_active: tuple[str, ...]
    changed_inactive: tuple[str, ...]
    status: str = "PLANNER_PROPOSAL_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_hash(payload: object) -> str:
    # JSON object is internal ephemeral evidence, never an active manifest.
    return _sha(json.dumps(payload, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":"), allow_nan=False).encode("ascii"))


def _selector_order(value: object) -> list[list[str]]:
    if type(value) is not tuple or len(value) > 256:
        raise EffectiveDiffRefused("INVALID_AUTHORED_SELECTORS")
    result = []
    for row in value:
        if (type(row) is not tuple or len(row) > 32 or
                any(type(token) is not str or not _SELECTOR.fullmatch(token)
                    for token in row)):
            raise EffectiveDiffRefused("INVALID_AUTHORED_SELECTORS")
        if len(row) != len(set(row)):
            raise EffectiveDiffRefused("DUPLICATE_AUTHORED_SELECTORS")
        result.append(list(row))
    return result


def _source_map(mode: str, value: object, count: int) -> list[list[object]] | None:
    # This is only a *detached* reduced witness from the original source map.
    # S08c authenticates the full original map and generation separately.
    if mode != "auto":
        if value is not None:
            raise EffectiveDiffRefused("NONAUTO_SOURCE_MAP_NOT_ORIGINAL")
        return None
    if type(value) is not list or len(value) != count + 1:
        raise EffectiveDiffRefused("AUTO_SOURCE_MAP_MISSING_OR_PARTIAL")
    seen = set()
    numbers = []
    out = []
    for row in value:
        if (type(row) is not list or len(row) != 5 or
                type(row[0]) is not str or type(row[1]) is not str or
                row[0] not in ("voice", "strategy", "extra", "native-default", "engine-base") or
                row[1] not in (
                    "known-hostlist", "excluded-ipset", "excluded-voice", "excluded-stun",
                    "unknown-import", "unknown-native-list", "unknown-extra",
                    "unknown-source", "unknown-native-default", "non-executable-skip",
                    "non-executable-template") or
                (row[2] is not None and
                 (type(row[2]) is not str or not _SELECTOR.fullmatch(row[2]))) or
                (row[3] is not None and
                 (type(row[3]) is not str or not re.fullmatch(r"[a-z][a-z0-9_-]*", row[3]))) or
                (row[4] is not None and (type(row[4]) is not int or row[4] < 0))):
            raise EffectiveDiffRefused("INVALID_ORIGINAL_MAP_ROW")
        if row[4] is not None:
            if row[4] in seen:
                raise EffectiveDiffRefused("DUPLICATE_ORIGINAL_PROFILE_NUMBER")
            seen.add(row[4])
            numbers.append(row[4])
        out.append(list(row))
    if (out[-1][0] != "native-default" or out[-1][1] != "unknown-native-default" or
            out[-1][4] != 0 or sorted(n for n in numbers if n > 0) !=
            list(range(1, len([n for n in numbers if n > 0]) + 1))):
        raise EffectiveDiffRefused("INVALID_ORIGINAL_MAP_NUMBERING")
    return out


def snapshot(*, original_native_args: bytes, target_mode: str,
             original_source_rows: list | None, authored_selectors: tuple,
             saved_wan: str, resolved_wan: str, engine_version: str,
             original_capture: dict, original_tcp: bytes, original_udp: bytes,
             managed_sha256: dict[str, str]) -> EffectiveSnapshot:
    """Create an immutable digest witness of the ORIGINAL emitted candidate.

    The caller must independently attest that the supplied original files,
    references and source map belong to the same saved and sealed generation.
    No filesystem I/O takes place here. The detached witness is NOT trusted
    for runtime execution, file replacement, engine reload or FD9 ownership.
    """
    if (type(original_native_args) is not bytes or not 0 < len(original_native_args) <= _MAX_ARGS
            or b"\x00" in original_native_args or b"\r" in original_native_args
            or target_mode not in ("all", "list", "auto")
            or type(saved_wan) is not str or not _WAN.fullmatch(saved_wan)
            or type(resolved_wan) is not str or not _WAN.fullmatch(resolved_wan)
            or type(engine_version) is not str or not _ENGINE.fullmatch(engine_version)
            or type(original_tcp) is not bytes or type(original_udp) is not bytes
            or len(original_tcp) > 8192 or len(original_udp) > 8192
            or type(managed_sha256) is not dict or not 0 < len(managed_sha256) <= 32
            or type(original_capture) is not dict):
        raise EffectiveDiffRefused("UNQUALIFIED_EFFECTIVE_INPUT")
    if any(type(name) is not str or not _REF_FILE.fullmatch(name)
           or type(sha) is not str or not _SHA.fullmatch(sha)
           for name, sha in managed_sha256.items()):
        raise EffectiveDiffRefused("INVALID_MANAGED_DIGESTS")
    selectors = _selector_order(authored_selectors)
    try:
        rows = segments(original_native_args.decode("utf-8"))
    except (UnicodeError, ExclusionError) as exc:
        raise EffectiveDiffRefused("INVALID_NATIVE_ARGV") from None
    if (not original_native_args.startswith(b"--port=") or
            any(token.startswith("--hostlist-auto") for row in rows for token in row)):
        # S08d compares only old original nonactivating generator products.
        # S08c independently verifies proposed schema3 learning suffix.
        raise EffectiveDiffRefused("UNQUALIFIED_NATIVE_SOURCE")
    source_rows = _source_map(target_mode, original_source_rows, len(rows))
    capture = original_capture
    voice = capture.get("voice")
    if (capture.get("schema") != 1 or capture.get("rule_base") != _FIRST_RULE or
            capture.get("rule_max") != _LAST_RULE or
            capture.get("logical_wan") != saved_wan or
            capture.get("wan") != resolved_wan or
            type(voice) is not list or len(voice) > 5 or
            capture.get("ordinary_rule_base") != _FIRST_RULE + len(voice) or
            type(capture.get("divert_port")) is not int or not
            1 <= capture["divert_port"] <= 65535 or
            not original_native_args.startswith(
                f"--port={capture['divert_port']}\n".encode("ascii"))):
        raise EffectiveDiffRefused("UNQUALIFIED_NATIVE_IPFW_CAPTURE")
    if (type(capture.get("ordinary_rule_base")) is not int or
            capture["ordinary_rule_base"] + 1 > _LAST_RULE or
            any(type(item) is not dict or
                item.get("rule") != _FIRST_RULE + index
                for index, item in enumerate(voice))):
        raise EffectiveDiffRefused("ORDINARY_IPFW_RULE_BOUNDS")

    names = set()
    foreign = set()
    for row in rows:
        for token in row:
            flag, sep, value = token.partition("=")
            if flag not in _REF_OPTIONS:
                continue
            if not sep or not value:
                raise EffectiveDiffRefused("UNQUALIFIED_NATIVE_REFERENCE")
            if value.startswith(_MANAGED):
                name = value[len(_MANAGED):]
                if not _REF_FILE.fullmatch(name) or name not in managed_sha256:
                    raise EffectiveDiffRefused("MISSING_OR_ALIEN_ACTIVE_REFERENCE")
                names.add(name)
            else:
                # Native authored external references are structural but
                # we cannot prove their contents through managed snapshots.
                # Their identity is hashed; content-only claims are refused
                # unless ALL changed content is known managed active refs.
                foreign.add(_sha(value.encode("utf-8")))
    all_names = set(managed_sha256)
    linked = tuple((name, managed_sha256[name]) for name in sorted(names))
    unlinked = tuple((name, managed_sha256[name])
                     for name in sorted(all_names - names))
    # Exclusions/Voice/SourceMap/TargetMode/WAN/version are structurally
    # significant even if the engine argv happens to be byte-identical.
    structural_sha256 = _stable_hash({
        "schema": 1,
        "argv": _sha(original_native_args),
        "mode": target_mode,
        "source": source_rows,
        "authored_selectors": selectors,
        "saved_wan": saved_wan,
        "resolved_wan": resolved_wan,
        "engine": engine_version,
        "ipfw_capture": capture,
        "ordinary_tcp": _sha(original_tcp),
        "ordinary_udp": _sha(original_udp),
        "active_refs": sorted(names),
        "external_refs": sorted(foreign),
    })
    return EffectiveSnapshot(structural_sha256, _sha(original_native_args),
                             linked, unlinked, len(foreign))


def plan(before: EffectiveSnapshot, after: EffectiveSnapshot) -> EffectiveDecision:
    """Classify only; no Apply/reload side effect or executable authority."""
    if (type(before) is not EffectiveSnapshot or type(after) is not EffectiveSnapshot
            or before.authorization != "NONE" or after.authorization != "NONE"
            or before.physical_transition_allowed or after.physical_transition_allowed
            or before.status != "DETACHED_EFFECTIVE_INPUT_ONLY"
            or after.status != "DETACHED_EFFECTIVE_INPUT_ONLY"
            or not _SHA.fullmatch(before.structural_sha256)
            or not _SHA.fullmatch(after.structural_sha256)):
        raise EffectiveDiffRefused("UNQUALIFIED_EFFECTIVE_SNAPSHOT")
    old_links = dict(before.linked)
    new_links = dict(after.linked)
    old_drafts = dict(before.unlinked)
    new_drafts = dict(after.unlinked)
    if (len(old_links) != len(before.linked) or len(new_links) != len(after.linked)
            or len(old_drafts) != len(before.unlinked)
            or len(new_drafts) != len(after.unlinked)
            or any(not _REF_FILE.fullmatch(k) or not _SHA.fullmatch(v)
                   for rows in (before.linked, before.unlinked, after.linked, after.unlinked)
                   for k, v in rows)
            or (set(old_links) & set(old_drafts))
            or (set(new_links) & set(new_drafts))):
        raise EffectiveDiffRefused("UNQUALIFIED_RESOURCE_FINGERPRINT")
    change_active = tuple(sorted(name for name in set(old_links) | set(new_links)
                                 if old_links.get(name) != new_links.get(name)))
    change_inactive = tuple(sorted(name for name in set(old_drafts) | set(new_drafts)
                                   if old_drafts.get(name) != new_drafts.get(name)))
    if (before.structural_sha256 != after.structural_sha256
            or set(old_links) != set(new_links) or
            before.external_ref_count != after.external_ref_count):
        kind = "RESTART_REQUIRED"
    elif change_active:
        # Even structural equality alone does not attest live mutable refs,
        # or prove that the original FD9/epoch/PID is still the active owner.
        # The decision is analytic, not SIGHUP permission.
        kind = ("RESTART_REQUIRED" if before.external_ref_count or after.external_ref_count
                else "RELOAD_SAFE_CANDIDATE")
    elif change_inactive:
        kind = "SAVE_ONLY"
    else:
        kind = "NO_CHANGE"
    return EffectiveDecision(kind, change_active, change_inactive)
