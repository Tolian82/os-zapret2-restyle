#!/usr/bin/env python3
"""P5a: pure advisory profile-shape report using the ONE native profile policy.

No files, Config, lock, IPFW, process or dvtws2 are touched. This intentionally
does not implement the approved P5 native Validate/Preview endpoint by itself.
"""
from __future__ import annotations

import json
import re
import sys

import profile_policy

MAX_REQUEST_BYTES = 65536
MAX_PREVIEW_PROFILES = 128
MAX_ACTIONS_PER_PROFILE = 128
MODE = frozenset(("all", "list", "auto"))
OPTIONS = frozenset(("strategy", "target_mode", "extra_arguments",
                     "exclude_domains_configured", "exclude_ipset_configured"))
KNOWN_INSPECTED = frozenset((
    "--filter-tcp", "--filter-udp", "--filter-l7", "--payload",
    "--lua-desync", "--in-range", "--out-range",
))
NATIVE_UNVALIDATED = "not_run"
STRUCTURAL_ONLY = "canonical_profile_split_only"
TOKEN_CAP = 160


class PreviewRefused(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _uniquely_keyed(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PreviewRefused("DUPLICATE_REQUEST_KEY")
        result[key] = value
    return result


def _request(raw: bytes) -> dict[str, object]:
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise PreviewRefused("REQUEST_SIZE_INVALID")
    try:
        candidate = json.loads(raw.decode("utf-8"), object_pairs_hook=_uniquely_keyed)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        if isinstance(exc, PreviewRefused):
            raise
        raise PreviewRefused("REQUEST_JSON_INVALID") from exc
    if not isinstance(candidate, dict) or set(candidate) - OPTIONS or (
        not {"strategy", "target_mode"}.issubset(candidate)
    ):
        raise PreviewRefused("REQUEST_FIELDS_INVALID")
    if not all(isinstance(candidate[field], str)
               for field in ("strategy", "target_mode")):
        raise PreviewRefused("REQUEST_FIELD_TYPES_INVALID")
    if "extra_arguments" in candidate and not isinstance(
        candidate["extra_arguments"], str
    ):
        raise PreviewRefused("REQUEST_FIELD_TYPES_INVALID")
    if any(not isinstance(candidate.get(field, False), bool) for field in (
        "exclude_domains_configured", "exclude_ipset_configured"
    )):
        raise PreviewRefused("REQUEST_FIELD_TYPES_INVALID")
    if candidate["target_mode"] not in MODE:
        raise PreviewRefused("TARGET_MODE_INVALID")
    for field in ("strategy", "extra_arguments"):
        value = candidate.get(field, "")
        if any((ord(ch) < 32 and ch not in "\n\r\t") or ord(ch) == 127
               for ch in value):
            raise PreviewRefused("CONTROL_CHARACTER_REFUSED")
    return candidate


def _short(value: str, warnings: set[str]) -> str:
    if len(value) > TOKEN_CAP:
        warnings.add("DISPLAY_TOKEN_TRUNCATED")
        return value[:TOKEN_CAP] + "…"
    return value


def _shape(contents: bytes, index: int, mode: str) -> dict[str, object]:
    """Inspect existing canonical split output; never interpret native grammar."""
    lines = contents.decode("utf-8").splitlines()
    filters: dict[str, list[str]] = {"tcp": [], "udp": [], "l7": []}
    selectors: list[str] = []
    actions: list[dict[str, object]] = []
    warnings: set[str] = set()
    active: dict[str, str | None] = {
        "payload": None, "in_range": None, "out_range": None,
    }
    has_direct_native_selector = False
    other_options = False
    for line in lines:
        for match in profile_policy.SELECTOR.finditer(line):
            selectors.append(match.group())
        # Inspection of simple option=value annotations is not validation.
        for token in line.split():
            if token.startswith("<"):
                if not profile_policy.SELECTOR.fullmatch(token):
                    warnings.add("PLACEHOLDER_REQUIRES_NATIVE_VALIDATION")
                continue
            if token.startswith("--hostlist") or token.startswith("--ipset"):
                has_direct_native_selector = True
            if not token.startswith("--"):
                other_options = True
                continue
            name, equal, value = token.partition("=")
            if not equal:
                other_options = True
                continue
            if name.startswith("--filter-") and name not in (
                "--filter-tcp", "--filter-udp", "--filter-l7"
            ):
                other_options = True
            if name not in KNOWN_INSPECTED:
                other_options = True
                continue
            if name == "--filter-tcp":
                filters["tcp"].append(_short(value, warnings))
            elif name == "--filter-udp":
                filters["udp"].append(_short(value, warnings))
            elif name == "--filter-l7":
                filters["l7"].append(_short(value, warnings))
            elif name in ("--payload", "--in-range", "--out-range"):
                key = name[2:].replace("-", "_")
                active[key] = _short(value, warnings)
            elif name == "--lua-desync":
                if len(actions) >= MAX_ACTIONS_PER_PROFILE:
                    raise PreviewRefused("TOO_MANY_LUA_ACTIONS")
                actions.append({
                    "ordinal": len(actions) + 1,
                    "payload": active["payload"],
                    "in_range": active["in_range"],
                    "out_range": active["out_range"],
                    "lua": _short(value, warnings),
                })
    if len(selectors) != len(set(selectors)):
        warnings.add("REPEATED_TEXTUAL_TARGET_REFERENCE")
    if not filters["tcp"] and not filters["udp"]:
        warnings.add("MISSING_EXPLICIT_PORT_FILTER")
    if not actions:
        warnings.add("NO_LUA_ACTION_OBSERVED")
    if other_options:
        warnings.add("NATIVE_OPTIONS_NOT_CHECKED")
    if has_direct_native_selector:
        source = "native_direct_target_unresolved"
    elif selectors:
        source = "explicit_placeholders"
    else:
        source = "default_target_mode_pending_native_resolution"
    return {
        "number": index,
        "requested_ports": {"tcp": filters["tcp"], "udp": filters["udp"]},
        "requested_l7": filters["l7"],
        "explicit_selectors": selectors[:MAX_PREVIEW_PROFILES],
        "target_source": source,
        "requested_default_mode": mode,
        "lua_actions": actions,
        "warnings": sorted(warnings),
    }


def preview(candidate: dict[str, object]) -> dict[str, object]:
    strategy = candidate["strategy"]
    mode = candidate["target_mode"]
    assert isinstance(strategy, str) and isinstance(mode, str)
    if len(strategy.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise PreviewRefused("STRATEGY_SIZE_INVALID")
    try:
        originals = profile_policy.split_profiles(strategy.encode("utf-8"))
        expanded = profile_policy.expand_profiles(originals)
    except (UnicodeError, profile_policy.ProfilePolicyError, ValueError) as exc:
        # Not user-controlled strings: fixed diagnostic code only.
        raise PreviewRefused("CANONICAL_PROFILE_POLICY_REFUSED") from exc
    if len(expanded) > MAX_PREVIEW_PROFILES:
        raise PreviewRefused("TOO_MANY_DISPLAY_PROFILES")
    profiles = [_shape(raw, i, mode) for i, raw in enumerate(expanded, 1)]
    warnings: set[str] = set()
    if len(expanded) != len(originals):
        warnings.add("MULTI_TARGET_PROFILE_EXPANSION")
    if candidate.get("extra_arguments"):
        warnings.add("EXTRA_ARGUMENTS_SCOPE_NOT_RESOLVED")
    # Conservative, nonauthoritative first-match warning: same visible
    # requested filters and selectors may still differ by native conditions.
    previous: dict[tuple[object, ...], int] = {}
    for profile in profiles:
        signature = (
            tuple(profile["requested_ports"]["tcp"]),
            tuple(profile["requested_ports"]["udp"]),
            tuple(profile["requested_l7"]),
            tuple(profile["explicit_selectors"]),
            profile["target_source"],
        )
        if signature in previous:
            profile["warnings"].append("POSSIBLE_FIRST_MATCH_OVERLAP")
        else:
            previous[signature] = profile["number"]
    if not profiles:
        warnings.add("EMPTY_TRAFFIC_STRATEGY_ALLOWED")
    return {
        "schema": "p5a-structural-advisory-v1",
        "state": "advisory_not_native_validated",
        "canonical_source_profile_count": len(originals),
        "canonical_expanded_profile_count": len(expanded),
        "profiles": profiles,
        "candidate_extra_arguments_present": bool(candidate.get("extra_arguments")),
        "global_exclusions_configured": {
            "domains": candidate.get("exclude_domains_configured", False),
            "ipset": candidate.get("exclude_ipset_configured", False),
        },
        "engine_native_dry_run": NATIVE_UNVALIDATED,
        "effective_ipfw_port_coverage": "not_computed",
        "actual_resources": "not_checked",
        "actual_voice_merge": "not_checked",
        "real_network_bypass": "not_tested",
        "config_process_fd9_ipfw_mutation": "not_performed",
        "warnings": sorted(warnings),
    }


def main(argv: list[str]) -> int:
    if argv != ["inspect-stdin"]:
        print("P5A_STRUCTURAL_PREVIEW_REFUSED=INVALID_OPERATION", file=sys.stderr)
        return 64
    try:
        request = _request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
        report = preview(request)
    except (PreviewRefused, TypeError) as exc:
        reason = exc.code if isinstance(exc, PreviewRefused) else "REQUEST_TYPE_REFUSED"
        print("P5A_STRUCTURAL_PREVIEW_REFUSED=" + reason, file=sys.stderr)
        return 65
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
