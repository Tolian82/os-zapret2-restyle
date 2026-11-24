#!/usr/bin/env python3
"""TZ6v5 S09a: bounded, detached immutable-root *candidate* contract.

The bytes supplied here are from the ORIGINAL generator / S08d witness.
This module neither opens files nor attests an on-disk seal, generation,
Config, FD9, P1 or runtime. S09b/S10 must qualify original owner and files
before any immutable root can become active. No other writer is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from neutral_effective_diff import EffectiveSnapshot

_ID = re.compile(r"[0-9a-f]{32}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MUTABLE = re.compile(r"(?:hostlist|ipset)-[a-z][a-z0-9-]{0,63}\.txt\Z")
_MAX_ROOT = 16384
_MAX_ARGS = 262144
_MAX_MAP = 1048576
_NAMES = {"native_args": "dvtws.args", "native_source_map": "auto-detect-source-map.json"}
_KEYS = frozenset(("schema", "generation", "service", "resources", "refs"))
_REF_KEYS = frozenset(("id", "path", "generation", "uid", "mode", "size", "sha256", "seal_sha256"))


class RootManifestRefused(ValueError):
    """Fixed diagnostic codes; never echo private args, lists or JSON content."""


@dataclass(frozen=True)
class RootCandidate:
    json_bytes: bytes
    sha256: str
    status: str = "DETACHED_CANDIDATE_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(items: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in items:
        if key in out:
            raise RootManifestRefused("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _decode(data: bytes, limit: int) -> dict:
    if type(data) is not bytes or not 0 < len(data) <= limit:
        raise RootManifestRefused("BOUNDED_JSON_REQUIRED")
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(
                                RootManifestRefused("NONFINITE_JSON")))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, RootManifestRefused):
            raise
        raise RootManifestRefused("INVALID_JSON") from None
    if type(result) is not dict:
        raise RootManifestRefused("JSON_OBJECT_REQUIRED")
    return result


def _canonical(root: dict) -> bytes:
    try:
        raw = (json.dumps(root, sort_keys=True, ensure_ascii=True,
                          allow_nan=False, separators=(",", ":")) + "\n").encode("ascii")
    except (TypeError, ValueError, RecursionError):
        raise RootManifestRefused("INVALID_ROOT_ENCODING") from None
    if len(raw) > _MAX_ROOT:
        raise RootManifestRefused("ROOT_OVERSIZE")
    return raw


def _proof(effective: EffectiveSnapshot, original_args: bytes) -> list[dict]:
    if (type(effective) is not EffectiveSnapshot or
            effective.status != "DETACHED_EFFECTIVE_INPUT_ONLY" or
            effective.authorization != "NONE" or effective.physical_transition_allowed or
            type(effective.structural_sha256) is not str or not _SHA.fullmatch(effective.structural_sha256) or
            type(effective.argv_sha256) is not str or not _SHA.fullmatch(effective.argv_sha256) or
            type(effective.external_ref_count) is not int or effective.external_ref_count != 0 or
            type(original_args) is not bytes or not 0 < len(original_args) <= _MAX_ARGS or
            effective.argv_sha256 != _sha(original_args) or
            type(effective.linked) is not tuple or len(effective.linked) > 32):
        raise RootManifestRefused("UNQUALIFIED_S08_EFFECTIVE_INPUT")
    names = []
    for item in effective.linked:
        if (type(item) is not tuple or len(item) != 2 or
                type(item[0]) is not str or not _MUTABLE.fullmatch(item[0]) or
                type(item[1]) is not str or not _SHA.fullmatch(item[1])):
            raise RootManifestRefused("INVALID_MUTABLE_RESOURCE")
        names.append(item[0])
    if names != sorted(set(names)):
        raise RootManifestRefused("UNORDERED_OR_DUPLICATE_MUTABLE")
    return [{"name": name, "owner": "original-p1-cas-ack"} for name in names]


def _source_map(raw: bytes | None, generation: str, argv_sha: str, mode: str) -> None:
    if mode != "auto":
        if raw is not None:
            raise RootManifestRefused("NONAUTO_MAP_FORBIDDEN")
        return
    obj = _decode(raw, _MAX_MAP)
    if (obj.get("schema") != 1 or obj.get("generation") != generation or
            obj.get("mode") != "auto" or obj.get("final_args_sha256") != argv_sha or
            obj.get("activation_authorized") is not False or
            obj.get("observer_attached") is not False):
        raise RootManifestRefused("ORIGINAL_MAP_IDENTITY_MISMATCH")


def compile_candidate(*, effective: EffectiveSnapshot, generation: str,
                      target_mode: str, enabled: bool, original_args: bytes,
                      original_source_map: bytes | None, seal_sha256: str,
                      owner_uid: int = 0) -> RootCandidate:
    """Describe exact original artifacts; SHA/mode/owner are untrusted claims until S09b.

    Does not create a file or certify an active seal. S08c original source-map
    native parity and S08d structural proof must be established separately.
    """
    if (type(generation) is not str or not _ID.fullmatch(generation) or
            type(target_mode) is not str or target_mode not in ("all", "list", "auto") or
            type(enabled) is not bool or type(seal_sha256) is not str or
            not _SHA.fullmatch(seal_sha256) or type(owner_uid) is not int or
            not 0 <= owner_uid <= 65535):
        raise RootManifestRefused("INVALID_ROOT_IDENTITY")
    mutable = _proof(effective, original_args)
    _source_map(original_source_map, generation, effective.argv_sha256, target_mode)
    refs = []
    for kind, raw in (("native_args", original_args),
                      ("native_source_map", original_source_map)):
        if raw is None:
            continue
        refs.append({"id": kind, "path": _NAMES[kind], "generation": generation,
                     "uid": owner_uid, "mode": 0o600, "size": len(raw),
                     "sha256": _sha(raw), "seal_sha256": seal_sha256})
    root = {"schema": 1, "generation": generation,
            "service": {"enabled": enabled, "target_mode": target_mode,
                        "structural_sha256": effective.structural_sha256},
            "resources": {"mutable_refs": mutable}, "refs": refs}
    raw = _canonical(root)
    return RootCandidate(raw, _sha(raw))


def validate_candidate(raw: bytes, *, effective: EffectiveSnapshot,
                       expected_generation: str, expected_mode: str,
                       expected_enabled: bool, original_args: bytes,
                       original_source_map: bytes | None, expected_seal_sha256: str,
                       expected_uid: int = 0) -> RootCandidate:
    """Recheck a detached proposal, never on-disk file identity or authority."""
    root = _decode(raw, _MAX_ROOT)
    if set(root) != _KEYS or root.get("schema") != 1 or type(root.get("schema")) is not int:
        raise RootManifestRefused("ROOT_SCHEMA_REFUSED")
    if raw != _canonical(root):
        raise RootManifestRefused("NONCANONICAL_ROOT")
    service = root.get("service")
    resources = root.get("resources")
    refs = root.get("refs")
    if (type(service) is not dict or
            set(service) != {"enabled", "target_mode", "structural_sha256"} or
            type(resources) is not dict or set(resources) != {"mutable_refs"} or
            type(refs) is not list or len(refs) not in (1, 2)):
        raise RootManifestRefused("ROOT_FIELDS_REFUSED")
    if (type(resources["mutable_refs"]) is not list or
            resources["mutable_refs"] != _proof(effective, original_args) or
            service != {"enabled": expected_enabled, "target_mode": expected_mode,
                        "structural_sha256": effective.structural_sha256} or
            type(service["enabled"]) is not bool):
        raise RootManifestRefused("ROOT_PROOF_MISMATCH")
    reference_names = [r.get("id") for r in refs if type(r) is dict]
    wanted = ["native_args"] + (["native_source_map"] if expected_mode == "auto" else [])
    if reference_names != wanted or len(refs) != len(wanted):
        raise RootManifestRefused("ROOT_REFS_MISMATCH")
    _source_map(original_source_map, expected_generation, effective.argv_sha256, expected_mode)
    for ref, kind, source in zip(refs, wanted, (original_args, original_source_map)):
        if (set(ref) != _REF_KEYS or
                ref.get("path") != _NAMES[kind] or
                ref.get("generation") != expected_generation or
                type(ref.get("uid")) is not int or ref["uid"] != expected_uid or
                type(ref.get("mode")) is not int or ref["mode"] != 0o600 or
                type(ref.get("size")) is not int or ref["size"] != len(source) or
                ref.get("sha256") != _sha(source) or
                ref.get("seal_sha256") != expected_seal_sha256):
            raise RootManifestRefused("ROOT_REF_UNQUALIFIED")
    if root["generation"] != expected_generation:
        raise RootManifestRefused("ROOT_GENERATION_STALE")
    return RootCandidate(raw, _sha(raw))
