#!/usr/bin/env python3
"""Build an inert, transactional Voice candidate bundle from persisted OPNsense settings.

No IPFW, configctl, dvtws2, proxy, routes or live runtime actions take place.
This performs a pre-activation consistency gate using the normalised managed
IPSET files produced by the *same* candidate release. Runtime wiring remains
a separate, explicitly reviewed step.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from voice_model_export import VoiceModelError, read_voice_model
from voice_profile_compiler import (
    SERVICES, VoiceConfigurationError, compile_candidate, normalize_targets,
)
from voice_capture_plan import CapturePlanError, compile_capture_plan
from voice_traffic_merge import VoiceMergeError, merge_profiles


class VoiceStageError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    """Stream-hash a regular staging source without retaining its contents."""
    if path.is_symlink() or not path.is_file():
        raise VoiceStageError("Voice staging source must be a regular non-symlink file")
    if path.stat().st_size > 128 * 1024 * 1024:
        raise VoiceStageError("Voice staging source exceeds configured bound")
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_managed_match(state: dict, managed_source: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for service in SERVICES:
        if not state["services"][service]["enabled"]:
            continue
        expected, _ = normalize_targets(state["services"][service]["ips"], service)
        if not expected:
            raise VoiceStageError(f"{service}: enabled Voice IPSET is empty")
        filename = managed_source / f"ipset-{service}.txt"
        if filename.is_symlink() or not filename.is_file():
            raise VoiceStageError(f"{service}: managed IPSET is missing or unsafe")
        if filename.stat().st_size > 1_048_576:
            raise VoiceStageError(f"{service}: managed IPSET is oversized")
        # Exact equality preserves order, deduplication and strict CIDR
        # normalisation. No automatic fallback to 'any' or stale targets.
        raw = filename.read_text(encoding="utf-8")
        actual = raw.splitlines()
        if actual != expected or raw != "".join(f"{line}\n" for line in expected):
            raise VoiceStageError(
                f"{service}: managed IPSET does not match saved Voice targets"
            )
        hashes[service] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return hashes


def compile_bundle(config: Path, managed_source: Path, active_root: Path,
                   physical_wan: str, first_rule: int, last_rule: int,
                   divert_port: int, ordinary_source: Path | None = None) -> dict[str, str]:
    if not active_root.is_absolute():
        raise VoiceStageError("active runtime directory must be absolute")
    if not isinstance(physical_wan, str) or not physical_wan:
        raise VoiceStageError("resolved kernel WAN must be supplied")
    source_sha = file_sha256(config)
    state = read_voice_model(config)
    profile, candidate = compile_candidate(state, active_root / "managed")
    hashes = require_managed_match(state, managed_source)
    # Source settings contain a logical OPNsense name, e.g. WAN. IPFW needs
    # the resolved kernel interface, e.g. vtnet1, which is supplied by the
    # orchestrator after config_resolve_interface.
    capture = compile_capture_plan(candidate, first_rule, last_rule, divert_port,
                                   physical_wan=physical_wan)
    if capture["wan"] != physical_wan or capture["logical_wan"] != candidate["wan"]:
        raise VoiceStageError("logical/physical WAN mismatch")
    for row in capture["voice"]:
        name = row["service"]
        if name not in hashes:
            raise VoiceStageError(f"{name}: missing verified managed IPSET")
    metadata = {
        "schema": 1,
        "saved_xml_sha256": source_sha,
        "mode": "staged-only",
        "activation_authorized": False,
        "logical_wan": candidate["wan"],
        "resolved_wan": physical_wan,
        "profile_count": len(capture["voice"]),
        "ipset_sha256": hashes,
    }
    artifacts = {
        "voice.conf": profile,
        "profile-plan.json": json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "capture-plan.json": json.dumps(capture, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }
    if ordinary_source is not None:
        ordinary_sha = file_sha256(ordinary_source)
        ordinary = ordinary_source.read_text(encoding="utf-8")
        merged = merge_profiles(profile, ordinary)
        artifacts["traffic.conf"] = merged
        metadata["ordinary_sha256"] = hashlib.sha256(ordinary.encode()).hexdigest()
        metadata["merged_sha256"] = hashlib.sha256(merged.encode()).hexdigest()
    # Prevent an internally coherent-looking bundle being created from
    # different generations of saved XML, managed IPSET or ordinary traffic.
    # A real Apply must still re-check these under its lifecycle/Config lock.
    if file_sha256(config) != source_sha:
        raise VoiceStageError("saved Voice configuration changed during candidate staging")
    if require_managed_match(state, managed_source) != hashes:
        raise VoiceStageError("managed IPSET changed during Voice candidate staging")
    if ordinary_source is not None and file_sha256(ordinary_source) != ordinary_sha:
        raise VoiceStageError("ordinary Strategy changed during Voice candidate staging")
    artifacts["metadata.json"] = json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return artifacts


def stage_bundle(output: Path, content: dict[str, str]) -> None:
    if not output.is_absolute():
        raise VoiceStageError("staging output directory must be absolute")
    if output.exists() or output.is_symlink():
        raise VoiceStageError("refusing to overwrite an existing Voice stage")
    parent = output.parent
    if not parent.is_dir() or parent.is_symlink():
        raise VoiceStageError("Voice stage parent must exist and not be a symlink")
    temp = Path(tempfile.mkdtemp(prefix=".voice-stage-", dir=parent))
    try:
        os.chmod(temp, 0o700)
        for name, value in content.items():
            if name not in {"voice.conf", "traffic.conf", "profile-plan.json", "capture-plan.json", "metadata.json"}:
                raise VoiceStageError("unknown staged artifact")
            path = temp / name
            with path.open("x", encoding="utf-8") as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(path, 0o600)
        os.rename(temp, output)
        # Persist the newly published candidate directory entry as well as
        # its individually fsync'd files. This is not an activation commit.
        fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main(argv: list[str]) -> int:
    if len(argv) not in (9, 10):
        print("usage: voice_release_stage.py CONFIG.XML MANAGED_SOURCE ACTIVE_ROOT "
              "RESOLVED_WAN RULE_BASE RULE_MAX DIVERT_PORT [ORDINARY_TRAFFIC.conf] OUTPUT_DIR", file=sys.stderr)
        return 64
    config, source, root = map(Path, argv[1:4])
    physical_wan = argv[4]
    try:
        ordinary_source = Path(argv[8]) if len(argv) == 10 else None
        candidate = compile_bundle(
            config, source, root, physical_wan, int(argv[5]),
            int(argv[6]), int(argv[7]), ordinary_source,
        )
        stage_bundle(Path(argv[-1]), candidate)
    except (ValueError, OSError, UnicodeError, VoiceConfigurationError,
            CapturePlanError, VoiceModelError) as exc:
        # No IPSET contents, secret XML fields or raw profile data in errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
