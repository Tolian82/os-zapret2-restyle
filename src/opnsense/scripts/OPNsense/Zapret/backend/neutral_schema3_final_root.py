#!/usr/bin/env python3
"""TZ6v5 S10b2b2a: truthful final schema3 root proposal, DETACHED ONLY.

Use the genuine P2e/S08 original witness and S10b2b1 sealed postpromotion
receipt. This is NOT a new generator, S08d final EffectiveSnapshot, original
FD9 activation authority, second journal, or physical root writer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_manifest import (
    RootCandidate, RootManifestRefused, _canonical, _proof, _sha,
)
from neutral_schema3_source_bridge import (
    OriginalSchema3Receipt, OriginalSchema3Refused, _json,
    _validate_typed_source,
)


class FinalSchema3Refused(ValueError):
    """Fixed content-free refusal, never reveal argv, hostlists or Config."""


@dataclass(frozen=True)
class FinalSchema3Proposal:
    candidate: RootCandidate
    structural_sha256: str
    generation: str
    status: str = "DETACHED_SCHEMA3_FINAL_PROPOSAL_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    original_fd9_reattest_required: bool = True


def compile_final_schema3(*, proof: OriginalSchema3Receipt,
                          native: NativeParity, original_effective: EffectiveSnapshot,
                          original_args: bytes, final_args: bytes,
                          original_source_map: bytes, active_generation_map: bytes,
                          enabled: bool, owner_uid: int = 0) -> FinalSchema3Proposal:
    """Project exact old+final native identities into a nonauthorizing root.

    Every byte input must have been pinned under the ORIGINAL FD9 by S10b2b1;
    recheck the physical original seal/journal and modes at the future stage.
    The legacy S09a/S10a parser intentionally REFUSES this schema-2 proposal.
    """
    if (type(proof) is not OriginalSchema3Receipt or
            proof.status != "ORIGINAL_SCHEMA3_S08_SOURCE_BRIDGE_ONLY" or
            proof.authorization != "NONE" or proof.physical_transition_allowed or
            proof.promotion_allowed or proof.original_fd9_recheck_required is not True or
            type(native) is not NativeParity or native.mode != "auto" or
            type(original_effective) is not EffectiveSnapshot or
            type(enabled) is not bool or type(owner_uid) is not int or
            not 0 <= owner_uid <= 65535 or
            any(type(raw) is not bytes or not 0 < len(raw) <= maximum
                for raw, maximum in ((original_args, 262144), (final_args, 262144),
                                     (original_source_map, 262144),
                                     (active_generation_map, 1048576)))):
        raise FinalSchema3Refused("FINAL_SCHEMA3_ORIGINAL_PROOF_REQUIRED")
    if (proof.generation == "" or
            proof.old_args_sha256 != _sha(original_args) or
            proof.final_args_sha256 != _sha(final_args) or
            proof.original_source_map_sha256 != _sha(original_source_map) or
            proof.active_generation_sha256 != _sha(active_generation_map) or
            proof.old_args_sha256 == proof.final_args_sha256 or
            native.original_args_sha256 != proof.old_args_sha256 or
            native.proposed_args_sha256 != proof.final_args_sha256 or
            proof.working_native_count != native.ordinary_native_count or
            proof.learning_native_count != native.learning_native_count or
            proof.learning_native_count <= 0):
        raise FinalSchema3Refused("FINAL_SCHEMA3_SHA_OR_COUNTS_MISMATCH")
    try:
        mutable = _proof(original_effective, original_args)
        source = _json(original_source_map, maximum=262144)
        active = _json(active_generation_map, maximum=1048576)
        _validate_typed_source(native, original_effective, source, active,
                               original_args, final_args,
                               proof.candidate_sha256, proof.generation)
        if (len(proof.seal_sha256) != 64 or
                any(c not in "0123456789abcdef" for c in proof.seal_sha256)):
            raise FinalSchema3Refused("FINAL_SCHEMA3_SEAL_REQUIRED")
        # The real original promoter's schema3 active map owns the native
        # learning inbox paths; their LIVE content is NOT immutable root data.
        # Its bytes are signed by the only original bundle seal and included
        # in the final structural fingerprint, not copied into a second map.
        projection = {
            "schema": 2,
            "original_structural_sha256": original_effective.structural_sha256,
            "original_args_sha256": proof.old_args_sha256,
            "final_args_sha256": proof.final_args_sha256,
            "original_source_map_sha256": proof.original_source_map_sha256,
            "active_generation_sha256": proof.active_generation_sha256,
            "native_capture_sha256": native.native_capture_sha256,
            "working_native_count": proof.working_native_count,
            "learning_native_count": proof.learning_native_count,
        }
        structural = hashlib.sha256(_canonical(projection)).hexdigest()
        # The original writer produces old/final/active with 0644, original
        # P2e source-map with 0600. S10b2b2b must independently check each
        # physical mode/inode against the SAME source seal; we do not certify.
        refs = []
        for kind, name, mode, raw in (
            ("native_args", "dvtws.args", 0o644, final_args),
            ("original_native_args", "dvtws.original.args", 0o644, original_args),
            ("native_source_map", "auto-detect-source-map.json", 0o600,
             original_source_map),
            ("native_active_map", "auto-detect-generation.json", 0o644,
             active_generation_map),
        ):
            refs.append({"id": kind, "path": name, "generation": proof.generation,
                         "uid": owner_uid, "mode": mode, "size": len(raw),
                         "sha256": _sha(raw), "seal_sha256": proof.seal_sha256})
        root = {
            "schema": 2, "generation": proof.generation,
            "service": {"enabled": enabled, "target_mode": "auto",
                        "structural_sha256": structural,
                        "original_structural_sha256": original_effective.structural_sha256},
            "resources": {"mutable_refs": mutable,
                          "learning_native_numbers": [row.native_number
                                                      for row in native.learning_profiles]},
            "refs": refs,
        }
        raw = _canonical(root)
        return FinalSchema3Proposal(RootCandidate(raw, _sha(raw)),
                                    structural, proof.generation)
    except (RootManifestRefused, OriginalSchema3Refused, KeyError,
            TypeError, ValueError, RecursionError):
        raise FinalSchema3Refused("FINAL_SCHEMA3_UNQUALIFIED") from None


def validate_final_schema3(raw: bytes, **inputs) -> FinalSchema3Proposal:
    """Pure byte-exact recompile, not an original FD9/read/transition gate."""
    result = compile_final_schema3(**inputs)
    if type(raw) is not bytes or raw != result.candidate.json_bytes:
        raise FinalSchema3Refused("FINAL_SCHEMA3_ROOT_MISMATCH")
    return result
