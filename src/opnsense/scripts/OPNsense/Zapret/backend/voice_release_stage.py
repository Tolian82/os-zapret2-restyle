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
from ipset_policy import LISTS, LABELS, IPSetError, parse_ipset


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
    """Re-attest the ONE prepared Stage 1 manifest and all six actual IPSETs.

    Saved enabled Voice values are compared byte-for-byte to the canonical
    staged lists. Disabled drafts remain editable and are never activated.
    No second resolver, live Config writer or mutable Voice-side registry.
    """
    if managed_source.is_symlink() or not managed_source.is_dir():
        raise VoiceStageError("unsafe managed Voice candidate directory")
    manifest_path = managed_source.parent / "ipset-manifest.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or manifest_path.stat().st_size > 65536):
        raise VoiceStageError("prepared six-list IPSET manifest is missing or unsafe")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise VoiceStageError("invalid prepared six-list IPSET manifest") from exc
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or not isinstance(manifest.get("lists"), dict)
            or set(manifest["lists"]) != set(LISTS)):
        raise VoiceStageError("prepared six-list IPSET manifest schema differs")
    hashes: dict[str, str] = {}
    for name in LISTS:
        filename = managed_source / f"ipset-{name}.txt"
        if filename.is_symlink() or not filename.is_file():
            raise VoiceStageError(f"{name}: managed IPSET is missing or unsafe")
        raw = filename.read_bytes()
        if len(raw) > 262144:
            raise VoiceStageError(f"{name}: managed IPSET is oversized")
        try:
            canonical, proof = parse_ipset(
                raw, LABELS[name], collapse=name == "exclude")
        except IPSetError as exc:
            raise VoiceStageError(str(exc)) from exc
        # The exclusion output is *collapsed*. Its original manifest
        # family_counts represent pre-collapse source networks, while the
        # staged file records the smaller equivalent union. Do not compare
        # pre-collapse counts against a reparse of collapsed bytes.
        witness = manifest["lists"][name]
        if not isinstance(witness, dict) or raw != canonical.encode("utf-8") or (
            witness.get("sha256") != proof["sha256"]
            or witness.get("union") != proof["union"]
            or witness.get("entry_count") != proof["entry_count"]
            or witness.get("full_family") is not False
        ):
            raise VoiceStageError(f"{name}: managed IPSET/manifest mismatch")
        if name != "exclude" and witness != proof:
            raise VoiceStageError(f"{name}: managed IPSET/manifest mismatch")
        if name == "exclude":
            counts = witness.get("family_counts")
            if not isinstance(counts, dict) or set(counts) != {"ipv4", "ipv6"} or any(
                type(counts[family]) is not int
                or not proof["family_counts"][family] <= counts[family] <= 4096
                for family in ("ipv4", "ipv6")
            ):
                raise VoiceStageError("exclude: invalid pre-collapse IPSET counts")
        if name in SERVICES and state["services"][name]["enabled"]:
            expected, _ = normalize_targets(state["services"][name]["ips"], name)
            if not expected:
                raise VoiceStageError(f"{name}: enabled Voice IPSET is empty")
            if expected != canonical.splitlines():
                raise VoiceStageError(f"{name}: managed IPSET does not match saved Voice targets")
            hashes[name] = proof["sha256"]
    return hashes

def compile_bundle(config: Path, managed_source: Path, active_root: Path,
                   physical_wan: str, first_rule: int, last_rule: int,
                   divert_port: int, ordinary_source: Path | None = None,
                   expected_logical_wan: str | None = None) -> dict[str, str]:
    if not active_root.is_absolute():
        raise VoiceStageError("active runtime directory must be absolute")
    if not isinstance(physical_wan, str) or not physical_wan:
        raise VoiceStageError("resolved kernel WAN must be supplied")
    source_sha = file_sha256(config)
    state = read_voice_model(config)
    if expected_logical_wan is not None and state["strategy_wan"] != expected_logical_wan:
        raise VoiceStageError("rendered Strategies WAN does not match candidate XML")
    hashes = require_managed_match(state, managed_source)
    prepared = {name: (managed_source / f"ipset-{name}.txt").read_text(encoding="utf-8").splitlines()
                for name in hashes}
    profile, candidate = compile_candidate(state, active_root / "managed", prepared)
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
        "ipset_manifest_sha256": file_sha256(managed_source.parent / "ipset-manifest.json"),
    }
    artifacts = {
        "voice.conf": profile,
        "profile-plan.json": json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "capture-plan.json": json.dumps(capture, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }
    if ordinary_source is not None:
        ordinary_sha = file_sha256(ordinary_source)
        ordinary = ordinary_source.read_text(encoding="utf-8")
        # An ordinary Strategies STUN profile may legitimately reference a
        # managed IPSET for a DIFFERENT, disabled Voice service. Its scope
        # must survive the later native handoff just like enabled Voice
        # targets do, instead of being forgotten after the first merge.
        scopes = {}
        scope_hashes = {}
        for service in SERVICES:
            staged = managed_source / f"ipset-{service}.txt"
            if staged.is_symlink():
                raise VoiceStageError("ordinary STUN managed IPSET is a symlink")
            if not staged.exists():
                continue
            if not staged.is_file() or staged.stat().st_size > 1_048_576:
                raise VoiceStageError("ordinary STUN managed IPSET is unsafe")
            raw = staged.read_text(encoding="utf-8")
            scopes[str(active_root / "managed" / staged.name)] = raw.splitlines()
            scope_hashes[service] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        merged = merge_profiles(profile, ordinary, scopes)
        metadata["ordinary_scope_ipset_sha256"] = scope_hashes
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
    if file_sha256(managed_source.parent / "ipset-manifest.json") != metadata["ipset_manifest_sha256"]:
        raise VoiceStageError("prepared IPSET manifest changed during Voice staging")
    if ordinary_source is not None and file_sha256(ordinary_source) != ordinary_sha:
        raise VoiceStageError("ordinary Strategy changed during Voice candidate staging")
    if ordinary_source is not None:
        for service, digest in metadata["ordinary_scope_ipset_sha256"].items():
            staged = managed_source / f"ipset-{service}.txt"
            if (staged.is_symlink() or not staged.is_file()
                    or staged.stat().st_size > 1_048_576
                    or hashlib.sha256(staged.read_bytes()).hexdigest() != digest):
                raise VoiceStageError("managed ordinary STUN IPSET changed during staging")
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


def stage_common_runtime(output: Path, active_root: Path, content: dict[str, str]) -> None:
    """Add Voice to the ordinary release being built, never to the live tree.

    The common generator consumes traffic.conf directly. One release-local
    plan describes the profiles and capture; it has no lifecycle authority.
    Existing candidate files are not overwritten, including on a failed build.
    """
    if (not output.is_absolute() or output.is_symlink() or not output.is_dir()
            or output.resolve() == active_root.resolve()
            or active_root.resolve() in output.resolve().parents):
        raise VoiceStageError("common candidate must be outside the active runtime")
    if "traffic.conf" not in content:
        raise VoiceStageError("common candidate requires ordinary Traffic Strategy")
    plan = {
        "schema": 1,
        "source": {key: value for key, value in json.loads(content["metadata.json"]).items()
                   if key not in {"mode", "activation_authorized"}},
        "profiles": json.loads(content["profile-plan.json"])["profiles"],
        "capture": json.loads(content["capture-plan.json"]),
    }
    artifacts = {
        "traffic.conf": content["traffic.conf"],
        "voice-plan.json": json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }
    if any((output / name).exists() or (output / name).is_symlink() for name in artifacts):
        raise VoiceStageError("refusing to overwrite common candidate artifacts")
    created = []
    try:
        for name, value in artifacts.items():
            path = output / name
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                os.chmod(path, 0o600)
                stream.write(value)
    except OSError:
        for path in created:
            path.unlink()
        raise


def main(argv: list[str]) -> int:
    common_runtime = len(argv) > 1 and argv[1] == "--common-runtime"
    expected_logical_wan = None
    if common_runtime:
        if len(argv) < 3:
            return 64
        expected_logical_wan = argv[2]
        argv = [argv[0], *argv[3:]]
    if len(argv) not in (9, 10):
        print("usage: voice_release_stage.py [--common-runtime LOGICAL_WAN] CONFIG.XML MANAGED_SOURCE ACTIVE_ROOT "
              "RESOLVED_WAN RULE_BASE RULE_MAX DIVERT_PORT [ORDINARY_TRAFFIC.conf] OUTPUT_DIR", file=sys.stderr)
        return 64
    config, source, root = map(Path, argv[1:4])
    physical_wan = argv[4]
    try:
        ordinary_source = Path(argv[8]) if len(argv) == 10 else None
        candidate = compile_bundle(
            config, source, root, physical_wan, int(argv[5]),
            int(argv[6]), int(argv[7]), ordinary_source, expected_logical_wan,
        )
        if common_runtime:
            stage_common_runtime(Path(argv[-1]), root, candidate)
        else:
            stage_bundle(Path(argv[-1]), candidate)
    except (ValueError, OSError, UnicodeError, VoiceConfigurationError,
            CapturePlanError, VoiceModelError) as exc:
        # No IPSET contents, secret XML fields or raw profile data in errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
