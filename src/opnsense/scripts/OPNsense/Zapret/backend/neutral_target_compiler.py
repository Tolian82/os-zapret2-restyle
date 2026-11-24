#!/usr/bin/env python3
"""TZ6v5 S08a: pure, nonactivating native Target Mode/profile projection.

Use the existing profile_policy parser/normalizer and bytes of the original
Target Mode shell policy; never execute a shell or infer target defaults.
This is a narrow precompiler, NOT the S08 Voice/Exclude/Found compiler,
structural fingerprint, runtime manifest or service action planner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re

import profile_policy
from neutral_config_model import RequestedConfig, SourceId

_MAX_SOURCE = 128 * 1024
_MAX_STRATEGY = 256 * 1024
_MODES = ("all", "list", "auto")
_BRANCH = re.compile(r"(?ms)^[ \t]{8}(all|list|auto)\)[ \t]*\n(.*?)(?=^[ \t]{12};;)")
_ROW = re.compile(r"printf '((?:HOSTLIST|IPSET))\\t([a-z][a-z0-9_-]*)\\n'")


class TargetCompileError(ValueError):
    """Unqualified original source or input. Do not build/activate a runtime."""


@dataclass(frozen=True)
class ModePolicy:
    mode: str
    defaults: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class OriginalPolicy:
    modes: tuple[ModePolicy, ...]
    source_sha256: str


@dataclass(frozen=True)
class TargetedProfile:
    source_number: int
    authored: tuple[tuple[str, str], ...]
    effective: tuple[tuple[str, str], ...]
    original_sha256: str
    content: bytes = field(repr=False)
    normalized: tuple[bytes, ...] = field(repr=False)


@dataclass(frozen=True)
class TargetProjection:
    mode: str
    policy_sha256: str
    profiles: tuple[TargetedProfile, ...]
    status: str = "SOURCE_TARGETS_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def parse_original_policy(source: bytes) -> OriginalPolicy:
    """Read original static target_mode_policy() rows, never duplicate IDs.

    The result depends on the EXACT existing shell declaration. Dynamic or
    unfamiliar changes refuse; native validation must then be requalified.
    """
    if type(source) is not bytes or not source or len(source) > _MAX_SOURCE:
        raise TargetCompileError("INVALID_ORIGINAL_POLICY")
    try:
        body = source.decode("utf-8").split("\ntarget_mode_policy()\n{", 1)[1].split(
            "\ntarget_mode_profile_has_explicit_targets()\n{", 1)[0]
    except (UnicodeDecodeError, IndexError) as exc:
        raise TargetCompileError("ORIGINAL_POLICY_SOURCE_CHANGED") from exc
    matches = list(_BRANCH.finditer(body))
    if len(matches) != 3 or {match[1] for match in matches} != set(_MODES):
        raise TargetCompileError("ORIGINAL_POLICY_BRANCHES_CHANGED")
    rows = {}
    for match in matches:
        mode = match[1]
        found = []
        for line in match[2].splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped == "return 0":
                continue
            row = _ROW.fullmatch(stripped)
            if not row:
                raise TargetCompileError("ORIGINAL_POLICY_DECLARATION_CHANGED")
            found.append((row[1], row[2]))
        if len(found) != len(set(found)) or len(found) > 128 or (mode == "all" and found):
            raise TargetCompileError("INVALID_ORIGINAL_POLICY_ROWS")
        rows[mode] = tuple(found)
    return OriginalPolicy(tuple(ModePolicy(mode, rows[mode]) for mode in _MODES),
                          hashlib.sha256(source).hexdigest())


def compile_target_profiles(requested: RequestedConfig, strategy: bytes,
                            policy: OriginalPolicy) -> TargetProjection:
    """Mirror original Target Mode precedence and Python selector expansion.

    strategy is the *real* traffic strategy input bytes from the original
    compiler interface, not S07 legacy XML presence metadata. Registered
    source identifiers come exclusively from S07 native registry projection.
    No shell, filesystem, Config, PID, IPFW, FD9 or generated argv.
    """
    if (type(requested) is not RequestedConfig or requested.schema != 1 or
            requested.authorization != "NONE" or requested.physical_transition_allowed or
            requested.target_mode not in _MODES or type(strategy) is not bytes or
            (len(strategy) > _MAX_STRATEGY or b"\x00" in strategy) or
            type(policy) is not OriginalPolicy or
            type(policy.source_sha256) is not str or not re.fullmatch(
                r"[0-9a-f]{64}", policy.source_sha256) or
            tuple(entry.mode for entry in policy.modes) != _MODES):
        raise TargetCompileError("UNQUALIFIED_TARGET_INPUT")
    registry = {}
    for row in requested.registered_sources:
        if type(row) is not SourceId or (row.kind, row.name) in registry:
            raise TargetCompileError("INVALID_TARGET_REGISTRY")
        registry[(row.kind, row.name)] = row
    if not registry:
        raise TargetCompileError("INVALID_TARGET_REGISTRY")
    known = {}
    for entry in policy.modes:
        if type(entry) is not ModePolicy or type(entry.defaults) is not tuple:
            raise TargetCompileError("UNQUALIFIED_TARGET_POLICY")
        if len(entry.defaults) != len(set(entry.defaults)) or len(entry.defaults) > 128:
            raise TargetCompileError("INVALID_TARGET_DEFAULTS")
        for row in entry.defaults:
            if (type(row) is not tuple or len(row) != 2 or row not in registry or
                    row == ("HOSTLIST", "auto")):
                raise TargetCompileError("UNREGISTERED_OR_IMPLICIT_AUTO_DEFAULT")
        known[entry.mode] = entry.defaults
    if known["all"]:
        raise TargetCompileError("ALL_MODE_MUST_NOT_INJECT_TARGETS")
    try:
        originals = profile_policy.split_profiles(strategy)
        projected = []
        total_normalized = 0
        for number, original in enumerate(originals, 1):
            profile_policy.validate_syntax(original, number)
            authored = tuple(profile_policy._supported(original))
            # The original shell suppresses defaults for ANY well-formed
            # placeholder; a foreign placeholder must fail rather than
            # accidentally acquiring our own default targets.
            if set(profile_policy._tokens(original)) != set(authored):
                raise TargetCompileError("UNSUPPORTED_EXPLICIT_TARGET")
            effective = authored or known[requested.target_mode]
            for row in effective:
                if row not in registry:
                    raise TargetCompileError("UNREGISTERED_EXPLICIT_TARGET")
            content = original
            if not authored:
                content += b"".join(
                    f"<{kind}:{name}>\n".encode("ascii") for kind, name in effective)
            normalized = tuple(profile_policy.expand_profiles([content]))
            total_normalized += len(normalized)
            if total_normalized > profile_policy.MAX_PROFILES:
                raise TargetCompileError("TOO_MANY_NORMALIZED_PROFILES")
            projected.append(TargetedProfile(
                number, authored, effective, hashlib.sha256(original).hexdigest(),
                content, normalized))
    except (profile_policy.ProfilePolicyError, UnicodeError) as exc:
        raise TargetCompileError("INVALID_ORIGINAL_PROFILE") from exc
    return TargetProjection(requested.target_mode, policy.source_sha256, tuple(projected))
