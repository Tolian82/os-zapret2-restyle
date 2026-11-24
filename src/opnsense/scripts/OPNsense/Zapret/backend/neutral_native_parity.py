#!/usr/bin/env python3
"""TZ6v5 S08c: detached, nonauthorizing witness of the ONE original builder.

Read-only integrity *comparison*, not an alternate dvtws args generator,
an independent source of profile numbers, or a platform/FD9 attester.
The S07/S08a/S08b inputs must already be from the same detached candidate;
original SourceMap and Voice plan are emitted by the original producer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

import auto_detect_origin_map as origin
import auto_detect_owner as owner
import profile_policy
from global_exclusions import ExclusionError, segments
from voice_capture_plan import CapturePlanError, compile_capture_plan
from neutral_config_model import RequestedConfig
from neutral_target_compiler import TargetProjection
from neutral_resource_compiler import ResourceProjection

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[0-9a-f]{32}\Z")
_MAX = 262144
_ORDINARY_FIRST = 19000
_ORDINARY_LAST = 19099


class NativeParityRefused(ValueError):
    """Fixed failure code; never print private profile, target or argv bytes."""


@dataclass(frozen=True)
class NativeSourceRow:
    native_number: int | None
    source_number: int | None
    selector: str | None
    role: str
    status: str
    hostlist: str | None


@dataclass(frozen=True)
class NativeParity:
    mode: str
    original_args_sha256: str
    proposed_args_sha256: str
    source_map_status: str
    voice_profile_count: int
    ordinary_native_count: int
    learning_native_count: int
    working_profiles: tuple[NativeSourceRow, ...]
    learning_profiles: tuple[NativeSourceRow, ...]
    native_capture_sha256: str
    ordinary_rule_start: int
    ordinary_rule_end: int
    status: str = "ORIGINAL_SOURCE_PARITY_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _record(row: dict) -> NativeSourceRow:
    return NativeSourceRow(
        row.get("native_number"), row.get("source_number"),
        row.get("selector"), row.get("role"), row.get("status"),
        row.get("hostlist"))


def inspect_original(*, requested: RequestedConfig, targets: TargetProjection,
                     resources: ResourceProjection, strategy: bytes,
                     original_args: bytes, voice_conf: bytes, voice_plan: dict,
                     source_map: dict | None, generation: str | None,
                     candidate_sha256: str | None,
                     rule_base: int, rule_max: int) -> NativeParity:
    """Compare actual original output + map to typed source-side projections.

    Never read a filesystem path; no process, shell, model save, FD9 or IPFW.
    The original owner alone can attest file identity, Config revision, WAN,
    epoch and activation. A schema3 proposal is NEVER an active schema3 map.
    """
    if (type(requested) is not RequestedConfig or
            type(targets) is not TargetProjection or
            type(resources) is not ResourceProjection or
            requested.schema != 1 or requested.authorization != "NONE" or
            targets.authorization != "NONE" or resources.authorization != "NONE" or
            requested.physical_transition_allowed or targets.physical_transition_allowed or
            resources.physical_transition_allowed or
            requested.target_mode not in ("all", "list", "auto") or
            targets.mode != requested.target_mode or
            resources.target_mode != requested.target_mode or
            type(strategy) is not bytes or type(original_args) is not bytes or
            type(voice_conf) is not bytes or not 0 < len(original_args) <= _MAX or
            len(strategy) > _MAX or len(voice_conf) > _MAX or
            b"\x00" in original_args or b"\x00" in strategy or
            type(voice_plan) is not dict or
            type(rule_base) is not int or type(rule_max) is not int or
            (rule_base, rule_max) != (_ORDINARY_FIRST, _ORDINARY_LAST) or
            type(requested.divert_port) is not int or
            not 1 <= requested.divert_port <= 65535):
        raise NativeParityRefused("UNQUALIFIED_ORIGINAL_INPUT")
    try:
        rows = segments(original_args.decode("utf-8"))
    except (UnicodeError, ExclusionError) as exc:
        raise NativeParityRefused("ORIGINAL_NATIVE_ARGS_INVALID") from None
    if (not original_args.startswith(f"--port={requested.divert_port}\n".encode())
            or any(t.startswith("--hostlist-auto") for t in original_args.decode().split())):
        raise NativeParityRefused("UNEXPECTED_ORIGINAL_NATIVE_ARGS")

    # Keep the old Voice compiler/capture allocator as the only authorities.
    src = voice_plan.get("source")
    capture = voice_plan.get("capture")
    declared = voice_plan.get("profiles")
    if (type(src) is not dict or type(capture) is not dict or
            type(declared) is not list or voice_plan.get("schema") != 1 or
            src.get("logical_wan") != requested.saved_wan or
            src.get("profile_count") != len(declared) or
            capture.get("rule_base") != rule_base or
            capture.get("rule_max") != rule_max or
            capture.get("divert_port") != requested.divert_port or
            capture.get("logical_wan") != requested.saved_wan or
            src.get("resolved_wan") != capture.get("wan") or
            type(src.get("resolved_wan")) is not str or
            len(declared) != sum(row.enabled for row in resources.voice) or
            len(declared) > 5 or
            resources.voice_native_args_sha256 !=
            (_sha(voice_conf) if declared else None)):
        raise NativeParityRefused("VOICE_ORIGINAL_ARTIFACT_MISMATCH")
    try:
        actual_capture = compile_capture_plan(
            {"schema": 1, "wan": src["logical_wan"], "profiles": declared},
            rule_base, rule_max, requested.divert_port,
            physical_wan=src["resolved_wan"])
    except (CapturePlanError, ValueError, TypeError) as exc:
        raise NativeParityRefused("NATIVE_CAPTURE_PLAN_REFUSED") from None
    if capture != actual_capture or len(capture["voice"]) != len(declared):
        raise NativeParityRefused("NATIVE_CAPTURE_PLAN_CHANGED")
    if [p.get("service") for p in declared] != [
        row.service for row in resources.voice if row.enabled]:
        raise NativeParityRefused("NATIVE_VOICE_ORDER_CHANGED")
    if [p.get("profile_sha256") for p in declared] != [
        row.native_profile_sha256 for row in resources.voice if row.enabled]:
        raise NativeParityRefused("NATIVE_VOICE_SHA_CHANGED")
    if capture["ordinary_rule_base"] != rule_base + len(declared):
        raise NativeParityRefused("ORDINARY_IPFW_RANGE_CHANGED")

    # Same original profile_policy expansion; never reconstruct argv.
    expected = [(profile.source_number, profile.original_sha256,
                 [f"<{k}:{n}>" for k, n in profile.authored],
                 (f"<{profile_policy._supported(data)[0][0]}:"
                  f"{profile_policy._supported(data)[0][1]}>"
                  if len(profile_policy._supported(data)) == 1 else None))
                for profile in targets.profiles for data in profile.normalized]
    if not isinstance(resources.resources, tuple) or any(
            row.linked and row.state != "READY" and row.state != "PRESENT_EMPTY_OPTIONAL"
            for row in resources.resources):
        raise NativeParityRefused("UNQUALIFIED_LINKED_RESOURCES")

    original_digest = _sha(original_args)
    proof_digest = _sha(json.dumps(capture, sort_keys=True, separators=(",", ":")).encode())
    if requested.target_mode in ("list", "all"):
        # Legacy ORIGINAL builder does NOT publish a source map for these
        # modes. Do not invent a substitute or claim source attribution.
        if source_map is not None or generation is not None or candidate_sha256 is not None:
            raise NativeParityRefused("UNEXPECTED_NONAUTO_SOURCE_MAP")
        if any(t.startswith("--hostlist-auto") for row in rows for t in row):
            raise NativeParityRefused("LEARNING_NOT_ALLOWED_IN_NONAUTO")
        return NativeParity(
            requested.target_mode, original_digest, original_digest,
            "ORIGINAL_NONAUTO_NO_SOURCE_MAP", len(declared), len(rows), 0,
            (), (), proof_digest, capture["ordinary_rule_base"], rule_max)

    if (type(source_map) is not dict or type(generation) is not str or
            not _ID.fullmatch(generation) or type(candidate_sha256) is not str or
            not _SHA.fullmatch(candidate_sha256) or
            source_map.get("schema") != 1 or
            source_map.get("evidence") != origin.NONACTIVATING or
            source_map.get("observer_attached") is not False or
            source_map.get("activation_authorized") is not False or
            source_map.get("generation") != generation or
            source_map.get("mode") != "auto" or
            source_map.get("strategy_sha256") != _sha(strategy) or
            source_map.get("final_args_sha256") != original_digest):
        raise NativeParityRefused("INVALID_ORIGINAL_SOURCE_MAP")
    original_rows = source_map.get("profiles")
    if (not isinstance(original_rows, list) or len(original_rows) != len(rows) + 1 or
            not isinstance(original_rows[-1], dict) or
            original_rows[-1].get("native_number") != 0 or
            original_rows[-1].get("role") != "native-default"):
        raise NativeParityRefused("ORIGINAL_PROFILE_MAP_COUNT")
    actual_voice = [record for record in original_rows[:-1]
                    if record.get("role") == "voice"]
    actual_strategy = [record for record in original_rows[:-1]
                       if record.get("role") == "strategy"]
    if len(actual_voice) != len(declared) or len(actual_strategy) != len(expected):
        raise NativeParityRefused("ORIGINAL_VOICE_OR_STRATEGY_MAP_COUNT")
    for item, row in zip(actual_strategy, expected):
        number, digest, authored, selector = row
        if (item.get("source_number") != number or
                item.get("source_sha256") != digest or
                item.get("source_selectors") != authored or
                item.get("selector") != selector):
            raise NativeParityRefused("ORIGINAL_SOURCE_PROFILE_IDENTITY_CHANGED")
    # Canonical real original preview planner + separate owner independent
    # validator: guarantee exact working first-match, learner last, global
    # exclusions before sealed FD9. No new clone generator here.
    try:
        proposed, learning = origin.plan_learning_tier(
            source_map, original_args, owner_id=generation,
            owner_candidate_sha256=candidate_sha256)
        qualified = owner._valid_learning_proposal(
            json.dumps(learning, sort_keys=True, separators=(",", ":")).encode(),
            {"id": generation, "candidate": candidate_sha256},
            original_args, proposed)
    except (origin.AttributionError, owner.GenerationRefused,
            ValueError, TypeError) as exc:
        raise NativeParityRefused("ORIGINAL_LEARNING_PROOF_REFUSED") from None
    found = [(number, host) for number, host, _ in qualified]
    observed = [(row["native_number"], row["hostlist"])
                for row in learning["profiles"] if row.get("role") == "learning"]
    if (found != observed or
            [row["native_number"] for row in learning["profiles"]
             if row.get("role") == "learning"] !=
            list(range(len(rows) + 1, len(rows) + 1 + len(qualified))) or
            learning["activation_authorized"] is not False or
            learning["schema"] != 3 or
            (bool(qualified) is False and proposed != original_args)):
        raise NativeParityRefused("UNQUALIFIED_FIRST_MATCH_OR_LEARNING_ORDER")
    return NativeParity(
        "auto", original_digest, _sha(proposed),
        "ORIGINAL_NONACTIVATING_MAP_AND_OWNER_INDEPENDENT_PROPOSAL",
        len(declared), len(rows), len(qualified),
        tuple(_record(x) for x in original_rows[:-1]),
        tuple(_record(x) for x in learning["profiles"] if x.get("role") == "learning"),
        proof_digest, capture["ordinary_rule_base"], rule_max)
