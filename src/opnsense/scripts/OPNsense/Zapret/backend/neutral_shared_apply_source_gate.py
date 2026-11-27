#!/usr/bin/env python3
"""S10c2b3a: original FD9 preseal and final sealed source/native witnesses.

The existing shared_apply_prepare_service is the only installed caller.
This module never creates a Config writer, journal, release, PID, or IPFW
operation. Pure compilation is NOT an authorization to activate. The original
FD9 owner must re-attest its seal, P1 and previous runtime at physical commit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from config_projection_opnsense import registered_ids, xml_snapshot
from neutral_config_model import project, ConfigModelError
from neutral_target_compiler import compile_target_profiles, parse_original_policy, TargetCompileError
from neutral_resource_compiler import (
    compile_resources, compare_original_managed_bytes, parse_original_storage,
    ResourceCompileError)
from neutral_native_parity import NativeParity, inspect_original, NativeParityRefused
from neutral_effective_diff import EffectiveDecision, EffectiveSnapshot, plan, snapshot
from shared_apply_seal import _stat, verify_seal
from voice_profile_compiler import SERVICES

FIELDS = (
    "strategy", "youtube", "user", "telegram", "discord", "x", "sip",
    "custom", "exclude_domains", "exclude_ipset", "mode", "port", "wan")
MARKER = b"S10C2B1_ORIGINAL_INPUT_V1"
MAX_PIPE = 12 * 1024 * 1024
MAX_XML = 16 * 1024 * 1024
MAX_FILE = 4 * 1024 * 1024
_ID = re.compile(r"[a-f0-9]{32}\Z")


class OriginalSourceGateRefused(ValueError):
    """No user data, paths, WAN, domains, addresses or Lua in errors."""


@dataclass(frozen=True)
class SourceGateReceipt:
    mode: str
    candidate_input_sha256: str
    managed_locators: tuple[str, ...]
    status: str = "ORIGINAL_NONACTIVATING_SOURCE_MANAGED_PARITY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    original_args_sha256: str = ""
    native_source_map_status: str = ""
    native_profile_count: int = 0
    known_learning_count: int = 0
    final_args_sha256: str = ""
    original_seal_sha256: str = ""
    generation: str = ""
    native_candidate_sha256: str | None = None
    native: NativeParity | None = None
    effective: EffectiveSnapshot | None = None
    requested_enabled: bool | None = None


def _fixed_unclassified_reason(error: BaseException) -> str:
    """Only literal source-owned identifiers; never emit private error data."""
    kind = (type(error).__module__, type(error).__name__)
    source_codes = {
        ("config_projection_opnsense", "NativeProjectionError"): {
            "INVALID_OR_DUPLICATE_XML_NODE": "INVALID_OR_DUPLICATE_XML_NODE",
            "INVALID_XML_INPUT": "INVALID_XML_INPUT",
            "INVALID_XML": "INVALID_XML",
            "INVALID_XML_ROOT": "INVALID_XML_ROOT",
            "OPNSENSE_MODEL_MISSING_OR_DUPLICATE": "OPNSENSE_MODEL_MISSING_OR_DUPLICATE",
            "ZAPRET_MODEL_MISSING_OR_DUPLICATE": "ZAPRET_MODEL_MISSING_OR_DUPLICATE",
            "INVALID_MODEL_ATTRIBUTES": "INVALID_MODEL_ATTRIBUTES",
            "INVALID_MODEL_BRANCH": "INVALID_MODEL_BRANCH",
            "INVALID_LEGACY_VOICE_WAN": "INVALID_LEGACY_VOICE_WAN",
            "INVALID_VOICE_MODEL": "INVALID_VOICE_MODEL",
            "INVALID_REGISTRY_SOURCE": "INVALID_REGISTRY_SOURCE",
            "UNKNOWN_REGISTRY_DECLARATION": "UNKNOWN_REGISTRY_DECLARATION",
            "INVALID_REGISTRY_OPTION": "INVALID_REGISTRY_OPTION",
            "INVALID_REGISTRY_STORAGE": "INVALID_REGISTRY_STORAGE",
            "INVALID_REGISTRY_MEMBERS": "INVALID_REGISTRY_MEMBERS",
            "UNQUALIFIED_CONFIG_OWNER": "UNQUALIFIED_CONFIG_OWNER",
            "UNQUALIFIED_SAVED_CONFIG": "UNQUALIFIED_SAVED_CONFIG",
        },
        ("auto_detect_owned_sources", "OwnedSourcesRefused"): {
            "ownership_directory_unavailable": "P1_OWNERSHIP_DIRECTORY_UNAVAILABLE",
            "unsafe_ownership_directory": "P1_UNSAFE_OWNERSHIP_DIRECTORY",
            "unsafe_owned_component": "P1_UNSAFE_OWNED_COMPONENT",
            "owned_component_changed_during_read": "P1_OWNED_COMPONENT_CHANGED_DURING_READ",
            "owned_component_unreadable": "P1_OWNED_COMPONENT_UNREADABLE",
            "short_ownership_write": "P1_SHORT_OWNERSHIP_WRITE",
            "incomplete_or_foreign_owned_sources": "P1_INCOMPLETE_OR_FOREIGN_OWNED_SOURCES",
            "invalid_owned_manifest": "P1_INVALID_OWNED_MANIFEST",
            "invalid_owned_component_syntax": "P1_INVALID_OWNED_COMPONENT_SYNTAX",
            "noncanonical_owned_component": "P1_NONCANONICAL_OWNED_COMPONENT",
            "original_clean_bootstrap_authority_required": "P1_ORIGINAL_CLEAN_BOOTSTRAP_AUTHORITY_REQUIRED",
            "ownership_already_present_or_partial": "P1_OWNERSHIP_ALREADY_PRESENT_OR_PARTIAL",
            "invalid_initial_shared_destination": "P1_INVALID_INITIAL_SHARED_DESTINATION",
            "native_original_config_proof_required": "P1_NATIVE_ORIGINAL_CONFIG_PROOF_REQUIRED",
            "unsafe_initial_runtime_root": "P1_UNSAFE_INITIAL_RUNTIME_ROOT",
            "historical_epochs_preclude_clean_baseline": "P1_HISTORICAL_EPOCHS_PRECLUDE_CLEAN_BASELINE",
            "initial_native_owned_source_not_sealed": "P1_INITIAL_NATIVE_OWNED_SOURCE_NOT_SEALED",
        },
        ("auto_detect_destination_commit", "DestinationRefused"): {
            "unsafe_gui_lock_path": "P1_UNSAFE_GUI_LOCK_PATH",
            "unsafe_gui_lock_directory": "P1_UNSAFE_GUI_LOCK_DIRECTORY",
            "unsafe_gui_lock": "P1_UNSAFE_GUI_LOCK",
            "gui_writer_busy": "P1_GUI_WRITER_BUSY",
            "gui_lock_already_held": "P1_GUI_LOCK_ALREADY_HELD",
            "gui_lock_required": "P1_GUI_LOCK_REQUIRED",
        },
    }
    if kind in source_codes:
        return source_codes[kind].get(str(error), {
            ("config_projection_opnsense", "NativeProjectionError"): "ORIGINAL_PROJECTION_UNCLASSIFIED",
            ("auto_detect_owned_sources", "OwnedSourcesRefused"): "P1_OWNED_SOURCE_UNCLASSIFIED",
            ("auto_detect_destination_commit", "DestinationRefused"): "P1_DESTINATION_UNCLASSIFIED",
        }[kind])
    if kind == ("builtins", "FileNotFoundError"):
        # Only predefined artifact roles are returned, never actual paths.
        missing = error.filename
        if type(missing) is str:
            basename = Path(missing).name
            fixed = {
                "candidate.xml": "MISSING_CANDIDATE_XML",
                "plan.json": "MISSING_SOURCE_PLAN",
                "traffic.input": "MISSING_STRATEGY_INPUT",
                "target-registry.tsv": "MISSING_TARGET_REGISTRY",
                "storage-catalog.tsv": "MISSING_STORAGE_CATALOG",
                "registry.sh": "MISSING_REGISTRY_SOURCE",
                "storage.sh": "MISSING_STORAGE_SOURCE",
                "target_mode.sh": "MISSING_MODE_POLICY_SOURCE",
                "dvtws.args": "MISSING_ORIGINAL_ARGV",
                "voice.conf": "MISSING_VOICE_PROFILE",
                "voice-plan.json": "MISSING_VOICE_PLAN",
                "hostlist-exclude.txt": "MISSING_HOSTLIST_EXCLUSIONS",
                "ipset-exclude.txt": "MISSING_IPSET_EXCLUSIONS",
                "auto-detect-source-map.json": "MISSING_AUTO_SOURCE_MAP",
                "auto-domains.txt": "MISSING_AUTO_HOSTLIST",
                "ipset": "MISSING_GUI_IPSET_DIRECTORY",
                "shared-work": "MISSING_SHARED_WORK_DIRECTORY",
                "auto-detect-owned": "MISSING_P1_OWNED_DIRECTORY",
                "managed": "MISSING_MANAGED_DIRECTORY",
            }
            if basename in fixed:
                return fixed[basename]
            if Path(missing).parent.name == "managed":
                return "MISSING_MANAGED_OUTPUT"
        return "ORIGINAL_FILE_MISSING"
    return {
        ("shared_apply_seal", "SharedBundleError"): "ORIGINAL_BUNDLE_REFUSAL",
        ("voice_ipfw_adapter", "IPFWAdapterError"): "ORIGINAL_FD9_LOCK_REFUSAL",
        ("auto_detect_effective_known", "EffectiveKnownRefused"): "ORIGINAL_KNOWN_SOURCE_REFUSAL",
        ("builtins", "FileNotFoundError"): "ORIGINAL_FILE_MISSING",
        ("builtins", "PermissionError"): "ORIGINAL_FILE_DENIED",
        ("builtins", "OSError"): "ORIGINAL_OS_REFUSAL",
        ("builtins", "ValueError"): "ORIGINAL_VALUE_REFUSAL",
        ("builtins", "TypeError"): "ORIGINAL_TYPE_REFUSAL",
        ("builtins", "KeyError"): "ORIGINAL_KEY_REFUSAL",
        ("builtins", "IndexError"): "ORIGINAL_INDEX_REFUSAL",
        ("json.decoder", "JSONDecodeError"): "ORIGINAL_JSON_REFUSAL",
        ("neutral_effective_diff", "EffectiveDiffRefused"): "ORIGINAL_EFFECTIVE_REFUSAL",
        ("auto_detect_gui_hostlist", "AutoHostlistRefused"): "ORIGINAL_GUI_HOSTLIST_REFUSAL",
        ("auto_detect_origin_map", "AttributionError"): "ORIGINAL_ORIGIN_MAP_REFUSAL",
        ("shared_apply_operation", "SharedOperationError"): "ORIGINAL_SHARED_OPERATION_REFUSAL",
        ("auto_detect_epoch_receipts", "ReceiptRefused"): "ORIGINAL_P1_RECEIPT_REFUSAL",
        ("neutral_resource_compiler", "ResourceCompileError"): "RESOURCE_COMPILE_UNCLASSIFIED",
        ("neutral_target_compiler", "TargetCompileError"): "TARGET_COMPILE_UNCLASSIFIED",
        ("neutral_native_parity", "NativeParityRefused"): "NATIVE_PARITY_UNCLASSIFIED",
        ("neutral_config_model", "ConfigModelError"): "CONFIG_MODEL_UNCLASSIFIED",
    }.get(kind, 'UNCLASSIFIED_PARITY_REFUSAL')

def decode_pipe(raw: bytes) -> dict[str, bytes]:
    """Exact fixed framing: original shell uses printf %s\\0, never argv secrets."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_PIPE or not raw.endswith(b"\0"):
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_PIPE")
    chunks = raw[:-1].split(b"\0")
    if len(chunks) != 1 + len(FIELDS) or chunks[0] != MARKER:
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_FIELDS")
    data = dict(zip(FIELDS, chunks[1:]))
    for name in ("strategy", "youtube", "user", "exclude_domains"):
        if len(data[name]) > MAX_FILE:
            raise OriginalSourceGateRefused("INVALID_ORIGINAL_FIELD_SIZE")
    for name in ("telegram", "discord", "x", "sip", "custom", "exclude_ipset"):
        if len(data[name]) > 262144:
            raise OriginalSourceGateRefused("INVALID_ORIGINAL_FIELD_SIZE")
    if (len(data["strategy"]) > 262144 or
            data["mode"] not in (b"all", b"list", b"auto") or
            not re.fullmatch(rb"[0-9]{1,5}", data["port"]) or
            not re.fullmatch(rb"[A-Za-z][A-Za-z0-9_.:-]{0,63}", data["wan"])):
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_SOURCE_SELECTOR")
    return data


def read_inherited_original_source(source_fd: int) -> bytes:
    """Bounded original NUL frame; never read source data from argv or a path."""
    if type(source_fd) is not int or source_fd < 3 or source_fd == 9:
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_PIPE")
    if not stat.S_ISFIFO(os.fstat(source_fd).st_mode):
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_PIPE")
    with os.fdopen(os.dup(source_fd), "rb") as stream:
        raw = stream.read(MAX_PIPE + 1)
    decode_pipe(raw)
    return raw


def _read(path: Path, uid: int, maximum: int, *, allow_empty: bool = False) -> bytes:
    """Read one existing owned single-link file with no symlink or replacement."""
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid or
            before.st_mode & 0o022 or before.st_nlink != 1 or
            before.st_size > maximum or (not allow_empty and before.st_size == 0)):
        raise OriginalSourceGateRefused("UNTRUSTED_ORIGINAL_FILE")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        pinned = os.fstat(fd)
        if (pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise OriginalSourceGateRefused("ORIGINAL_FILE_CHANGED")
        data = os.read(fd, maximum + 1)
        after = os.fstat(fd)
        latest = path.lstat()
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                  value.st_mtime_ns, value.st_ctime_ns)
        if len(data) != before.st_size or identity(before) != identity(after) or (
                identity(before) != identity(latest)):
            raise OriginalSourceGateRefused("ORIGINAL_FILE_CHANGED")
        return data
    finally:
        os.close(fd)


def _check_original_source_root(work: Path, owner_uid: int,
                                bound_root_sha256: str | None) -> None:
    """No root before binding; only the exact sibling pin afterwards."""
    sibling = work / "manifest.json"
    for root in (work / ".manifest.json.pending",
                 work / "release/manifest.json",
                 work / "release/.manifest.json.pending"):
        if root.exists() or root.is_symlink():
            raise OriginalSourceGateRefused("PREMATURE_OR_SECOND_ROOT_FORBIDDEN")
    if bound_root_sha256 is None:
        if sibling.exists() or sibling.is_symlink():
            raise OriginalSourceGateRefused("PREMATURE_OR_SECOND_ROOT_FORBIDDEN")
    elif (type(bound_root_sha256) is not str or
            re.fullmatch(r"[a-f0-9]{64}", bound_root_sha256) is None or
            hashlib.sha256(_read(sibling, owner_uid, 16384)).hexdigest() != bound_root_sha256):
        raise OriginalSourceGateRefused("ORIGINAL_BOUND_SOURCE_ROOT_CHANGED")


def qualify_source_to_managed(*, work: Path, sources: Path,
                              inputs: dict[str, bytes],
                              owned_known: dict[str, bytes] | None,
                              runtime_auto: bytes | None = None,
                              candidate_sha256: str | None = None,
                              owner_uid: int = 0,
                              active_managed: Path = Path(
                                  "/usr/local/etc/zapret2/runtime-v2/managed"),
                              sealed: bool = False,
                              engine_version: str | None = None,
                              bound_root_sha256: str | None = None) -> SourceGateReceipt:
    """Pure observational witness of actual producer staged files.

    The original native wrapper supplies P2-qualified owned after-images.
    This import-only function is also exercised with the genuine original
    disposable P2e generator; it has no authority or physical effects.
    """
    if (not isinstance(work, Path) or not isinstance(sources, Path) or
            not isinstance(active_managed, Path) or not work.is_absolute() or
            not sources.is_absolute() or not active_managed.is_absolute() or
            not _ID.fullmatch(work.name) or type(owner_uid) is not int or
            owner_uid < 0 or type(sealed) is not bool or type(inputs) is not dict or
            set(inputs) != set(FIELDS) or
            (bound_root_sha256 is not None and not sealed) or
            any(type(value) is not bytes for value in inputs.values())):
        raise OriginalSourceGateRefused("UNQUALIFIED_ORIGINAL_CONTEXT")
    inputs = decode_pipe(MARKER + b"\0" + b"\0".join(inputs[key] for key in FIELDS) + b"\0")
    release = work / "release"
    managed = release / "managed"
    for directory in (work.parent, work, release, managed):
        _stat(directory, owner_uid, directory=True)
    # Final observation is AFTER the one original promotion and seal.
    if sealed:
        original_seal = _read(work / "bundle-seal.json", owner_uid, 1024)
        initial_seal = verify_seal(work, owner=owner_uid)
        _check_original_source_root(work, owner_uid, bound_root_sha256)
    else:
        original_seal = None
        initial_seal = None
    xml = _read(work / "candidate.xml", owner_uid, MAX_XML)
    saved = project(xml_snapshot(xml),
                    registered_ids(_read(sources / "registry.sh", owner_uid, 128 * 1024)))
    if (saved.target_mode != inputs["mode"].decode("ascii") or
            saved.divert_port != int(inputs["port"]) or
            saved.saved_wan != inputs["wan"].decode("ascii")):
        raise OriginalSourceGateRefused("ORIGINAL_CONFIG_SOURCE_DRIFT")
    traffic = _read(work / "traffic.input", owner_uid, 262145, allow_empty=True)
    if traffic != inputs["strategy"] + b"\n":
        raise OriginalSourceGateRefused("ORIGINAL_STRATEGY_SOURCE_DRIFT")
    registry = saved.registered_sources
    expected_registry = b"".join((
        f"{row.kind}\t{row.name}\t"
        f"{'--hostlist' if row.kind == 'HOSTLIST' else '--ipset'}\t"
        f"{row.storage_key}\t{int(row.content_required)}\n").encode("ascii")
        for row in registry)
    if _read(work / "target-registry.tsv", owner_uid, 128 * 1024) != expected_registry:
        raise OriginalSourceGateRefused("ORIGINAL_REGISTRY_SOURCE_DRIFT")
    original_storage = _read(sources / "storage.sh", owner_uid, 128 * 1024)
    storage = parse_original_storage(original_storage)
    expected_catalog = b"".join((
        f"{row.storage_key}\t{row.provider}\t{row.locator}\n").encode("ascii")
        for row in storage.entries)
    if _read(work / "storage-catalog.tsv", owner_uid, 128 * 1024) != expected_catalog:
        raise OriginalSourceGateRefused("ORIGINAL_STORAGE_SOURCE_DRIFT")
    policy = parse_original_policy(_read(sources / "target_mode.sh", owner_uid, 128 * 1024))
    targets = compile_target_profiles(saved, traffic, policy)
    prepared = {
        "hostlist.youtube": inputs["youtube"],
        "hostlist.user": inputs["user"],
        "hostlist.exclude": inputs["exclude_domains"],
        "ipset.exclude": inputs["exclude_ipset"],
    }
    for service in SERVICES:
        prepared["ipset." + service] = inputs[service]
    # The original registry is extensible; an unrepresented GUI source is NOT
    # silently mapped to existing User data. Future editors require an
    # explicit same-operation source binding, otherwise fail closed.
    expected = {row.storage_key for row in storage.entries if row.provider == "managed"}
    if set(prepared) != expected | {"hostlist.exclude", "ipset.exclude"}:
        raise OriginalSourceGateRefused("ORIGINAL_MANAGED_SOURCE_SET_DRIFT")
    resources = compile_resources(
        saved, targets, storage, prepared, owned_known,
        runtime_auto=runtime_auto, voice_managed_root=active_managed)
    observed = {}
    for row in storage.entries:
        if row.provider == "managed":
            observed[row.locator] = _read(managed / row.locator, owner_uid, MAX_FILE,
                                          allow_empty=True)
    for filename in ("hostlist-exclude.txt", "ipset-exclude.txt"):
        observed[filename] = _read(managed / filename, owner_uid, MAX_FILE, allow_empty=True)
    matched = compare_original_managed_bytes(resources, storage, observed)

    # S10c2b2: S08c consumes the very SAME pure S07/S08a/S08b projections,
    # only original producer bytes (never a second argv/Voice generator).
    # Auto's candidate SHA is supplied exclusively by original native PHP
    # preflight under FD9. It is not guessed from detached XML or test data.
    final_args = _read(release / "dvtws.args", owner_uid, 262144)
    active_map = release / "auto-detect-generation.json"
    old_args = release / "dvtws.original.args"
    promoted = active_map.exists() or active_map.is_symlink()
    if promoted and (not sealed or saved.target_mode != "auto"):
        raise OriginalSourceGateRefused("UNEXPECTED_ORIGINAL_PROMOTION")
    if saved.target_mode != "auto" and (old_args.exists() or old_args.is_symlink()):
        raise OriginalSourceGateRefused("NONAUTO_OLD_ARGS_FORBIDDEN")
    if sealed and saved.target_mode == "auto" and not promoted and (
            old_args.exists() or old_args.is_symlink()):
        raise OriginalSourceGateRefused("UNFINISHED_ORIGINAL_PROMOTION")
    args = (_read(old_args, owner_uid, 262144) if promoted else final_args)
    voice_conf = _read(release / "voice.conf", owner_uid, 262144, allow_empty=True)
    voice_plan = json.loads(_read(release / "voice-plan.json", owner_uid, MAX_FILE))
    source_file = release / "auto-detect-source-map.json"
    if saved.target_mode == "auto":
        if (type(candidate_sha256) is not str or
                re.fullmatch(r"[a-f0-9]{64}", candidate_sha256) is None):
            raise OriginalSourceGateRefused("ORIGINAL_NATIVE_CANDIDATE_DIGEST_REQUIRED")
        source_map = json.loads(_read(source_file, owner_uid, MAX_FILE))
        generation = work.name
    else:
        if (candidate_sha256 is not None or source_file.exists() or
                source_file.is_symlink()):
            raise OriginalSourceGateRefused("ORIGINAL_NONAUTO_MAP_OR_DIGEST_FORBIDDEN")
        source_map = None
        generation = None
    native = inspect_original(
        requested=saved, targets=targets, resources=resources,
        strategy=traffic, original_args=args, voice_conf=voice_conf,
        voice_plan=voice_plan, source_map=source_map,
        generation=generation, candidate_sha256=candidate_sha256,
        rule_base=19000, rule_max=19099)
    if native.authorization != "NONE" or native.physical_transition_allowed:
        raise OriginalSourceGateRefused("ORIGINAL_NATIVE_PROOF_NOT_READONLY")
    if promoted:
        # Only the ORIGINAL promoter can validate its exact final native map.
        from auto_detect_origin_map import verify_learning_promotion
        active = verify_learning_promotion(work, candidate_sha256)
        if (type(active) is not dict or active.get("schema") != 3 or
                hashlib.sha256(final_args).hexdigest() != native.proposed_args_sha256):
            raise OriginalSourceGateRefused("FINAL_ORIGINAL_NATIVE_REFS_MISMATCH")
    # Recheck actual ORIGINAL producer file bytes after the entire pure
    # inspection; later original seal independently hashes this same release.
    if (args != _read(old_args if promoted else release / "dvtws.args",
                      owner_uid, 262144) or
            final_args != _read(release / "dvtws.args", owner_uid, 262144) or
            voice_conf != _read(release / "voice.conf", owner_uid, 262144,
                               allow_empty=True) or
            (saved.target_mode == "auto" and
             source_map != json.loads(_read(source_file, owner_uid, MAX_FILE)))):
        raise OriginalSourceGateRefused("ORIGINAL_NATIVE_ARTIFACT_CHANGED")
    # Re-attest the two independent input source locations and strategy file
    # before handing control to original Auto/schema2 and eventual seal.
    if (xml != _read(work / "candidate.xml", owner_uid, MAX_XML) or
            traffic != _read(work / "traffic.input", owner_uid, 262145, allow_empty=True) or
            original_storage != _read(sources / "storage.sh", owner_uid, 128 * 1024) or
            expected_registry != _read(work / "target-registry.tsv", owner_uid, 128 * 1024)):
        raise OriginalSourceGateRefused("ORIGINAL_INPUT_CHANGED_DURING_CHECK")
    # S08d must use the same S07/S08a/S08b/S08c observation. A native
    # caller must supply its independently qualified installed engine version;
    # never substitute the plugin version or an assumed upstream version.
    effective = None
    if engine_version is not None:
        if not sealed:
            raise OriginalSourceGateRefused("EFFECTIVE_SOURCE_REQUIRES_FINAL_SEAL")
        rows = (None if source_map is None else [
            [row["role"], row["status"], row.get("selector"),
             row.get("hostlist"), row.get("native_number")]
            for row in source_map["profiles"]])
        capture = voice_plan["capture"]
        effective = snapshot(
            original_native_args=args, target_mode=saved.target_mode,
            original_source_rows=rows,
            authored_selectors=tuple(
                tuple(f"<{kind}:{key}>" for kind, key in row.authored)
                for row in targets.profiles),
            saved_wan=saved.saved_wan, resolved_wan=capture["wan"],
            engine_version=engine_version, original_capture=capture,
            original_tcp=_read(release / "tcp-ports.txt", owner_uid, 8192,
                               allow_empty=True),
            original_udp=_read(release / "udp-ports.txt", owner_uid, 8192,
                               allow_empty=True),
            managed_sha256={name: hashlib.sha256(raw).hexdigest()
                            for name, raw in observed.items()})
    if sealed:
        _check_original_source_root(work, owner_uid, bound_root_sha256)
        if (verify_seal(work, owner=owner_uid) != initial_seal or
                _read(work / "bundle-seal.json", owner_uid, 1024) != original_seal or
                final_args != _read(release / "dvtws.args", owner_uid, 262144) or
                (promoted and active != verify_learning_promotion(
                    work, candidate_sha256))):
            raise OriginalSourceGateRefused("FINAL_ORIGINAL_SEAL_CHANGED")
    return SourceGateReceipt(
        saved.target_mode, hashlib.sha256(xml).hexdigest(), matched,
        original_args_sha256=native.original_args_sha256,
        native_source_map_status=native.source_map_status,
        native_profile_count=native.ordinary_native_count,
        known_learning_count=native.learning_native_count,
        status=("ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY" if sealed else
                "ORIGINAL_NONACTIVATING_SOURCE_MANAGED_PARITY"),
        final_args_sha256=hashlib.sha256(final_args).hexdigest(),
        original_seal_sha256=(hashlib.sha256(original_seal).hexdigest()
                              if original_seal is not None else ""),
        generation=work.name, native_candidate_sha256=candidate_sha256,
        native=native if effective is not None else None, effective=effective,
        requested_enabled=saved.enabled)


def _owned_under_original_p2(work: Path, uid: int, *, mode: bytes) -> dict[str, bytes] | None:
    """Read original known P1 snapshot; never replace it with generated files."""
    from auto_detect_destination_commit import (
        SHARED_FOUND_NAMES, _qualified_shared_found_batch, exclusive_destination_lock)
    from auto_detect_effective_known import _verify_planned_preimages_locked
    from auto_detect_gui_hostlist import AUTO_LOCK, AUTO_HOSTLIST
    from auto_detect_owned_sources import (
        OWNED_ROOT, KNOWN_HOSTLISTS, read_owned, _safe_dir)

    plan = json.loads(_read(work / "plan.json", uid, MAX_FILE))
    if type(plan) is not dict:
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_PLAN")
    found = ("found_intent" in plan, "found_batch" in plan)
    if found[0] != found[1]:
        raise OriginalSourceGateRefused("INCOMPLETE_ORIGINAL_FOUND_PLAN")
    # All/List without Found or previously initialized P1-owned rows must
    # not require an unrelated Auto GUI directory that does not yet exist.
    # The ORIGINAL caller has already attested FD9; only a proven *absence*
    # is observed here, never unguarded P1 bytes. The accepted P1 bootstrap
    # requires that same FD9, so it cannot race this read-only absence proof.
    if (not found[0] and mode in (b"all", b"list") and
            not AUTO_LOCK.parent.exists() and
            not AUTO_LOCK.parent.is_symlink()):
        _safe_dir(OWNED_ROOT.parent, uid)
        try:
            OWNED_ROOT.lstat()
        except FileNotFoundError:
            return None
        raise OriginalSourceGateRefused("P1_OWNER_PRESENT_BUT_GUI_LOCK_ABSENT")
    with exclusive_destination_lock(AUTO_LOCK, uid):
        if found[0]:
            if (plan.get("page") != "strategies" or
                    plan.get("result") != "prepared" or
                    type(plan["found_intent"]) is not dict or
                    plan["found_intent"].get("commit_authorized") is not False):
                raise OriginalSourceGateRefused("INVALID_ORIGINAL_FOUND_INTENT")
            validated = _qualified_shared_found_batch(plan["found_batch"])
            targets = {"youtube": OWNED_ROOT / "youtube.txt",
                       "user": OWNED_ROOT / "user.txt", "auto": AUTO_HOSTLIST}
            _verify_planned_preimages_locked(
                validated, targets, owned_root=OWNED_ROOT, owner_uid=uid)
            return {name: validated[name][1] for name in KNOWN_HOSTLISTS}
        known = read_owned(OWNED_ROOT, owner_uid=uid)
        return None if known is None else {
            name: known[name].encode("utf-8") for name in KNOWN_HOSTLISTS}


def native_original_fd9(operation: str, raw_pipe: bytes,
                        candidate_sha256: str | None = None,
                        *, sealed: bool = False,
                        engine_version: str | None = None,
                        bound_record: dict | None = None) -> SourceGateReceipt:
    """Only the installed original FD9 wrapper can invoke this native action."""
    from voice_ipfw_adapter import require_lifecycle_lock
    from shared_apply_seal import WORK
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    require_lifecycle_lock()
    inputs = decode_pipe(raw_pipe)
    work = WORK / operation
    root_sha = None
    if bound_record is not None:
        from shared_apply_operation import SharedApplyOperation
        from neutral_root_stage import verify_original_operation_pins
        store = SharedApplyOperation(owner=0)
        if (not sealed or type(bound_record) is not dict or
                store.read() != bound_record or bound_record.get("phase") != "prepared" or
                "found" in bound_record or "manifest" not in bound_record or
                bound_record["detail"]["id"] != operation):
            raise OriginalSourceGateRefused("ORIGINAL_BOUND_SOURCE_OWNER_REQUIRED")
        verify_original_operation_pins(record=bound_record, parent=WORK, owner_uid=0)
        root_sha = bound_record["manifest"]["root_sha256"]
    known = _owned_under_original_p2(work, 0, mode=inputs["mode"])
    auto_bytes = None
    # Shared Auto is a runtime provider, NOT a managed hostlist and never
    # becomes an implicit learner. Only read its native source if referenced.
    if b"<HOSTLIST:auto>" in inputs["strategy"]:
        auto_bytes = _read(Path("/usr/local/etc/zapret2/ipset/auto-domains.txt"),
                           0, MAX_FILE, allow_empty=True)
    receipt = qualify_source_to_managed(
        work=work, sources=Path(__file__).parent, inputs=inputs,
        owned_known=known, runtime_auto=auto_bytes,
        candidate_sha256=candidate_sha256, owner_uid=0, sealed=sealed,
        engine_version=engine_version,
        **({"bound_root_sha256": root_sha} if root_sha is not None else {}))
    require_lifecycle_lock()
    if bound_record is not None:
        verify_original_operation_pins(record=bound_record, parent=WORK, owner_uid=0)
        if store.read() != bound_record:
            raise OriginalSourceGateRefused("ORIGINAL_BOUND_SOURCE_OWNER_CHANGED")
    return receipt



def _s10_native_bound_engine_readback() -> dict:
    """Reuse the original setup guard under inherited FD9, not a new reader.

    The guard lives immediately above this backend directory. Do not use a
    caller-provided version, display-only tag, env override or new lock.
    """
    parent = str(Path(__file__).resolve().parent.parent)
    sys.path.insert(0, parent)
    try:
        from extra_resources_upstream_guard import native_bound_engine_for_s10_readback
        return native_bound_engine_for_s10_readback()
    except (ImportError, ValueError, RuntimeError, OSError):
        raise OriginalSourceGateRefused("S10_BOUND_ENGINE_UNQUALIFIED") from None
    finally:
        sys.path.pop(0)


def native_original_bound_effective_fd9(
        operation: str, raw_pipe: bytes,
        candidate_sha256: str | None = None, *,
        bound_record: dict | None = None) -> SourceGateReceipt:
    """Strict opt-in S10 source → genuine bound engine → S08d, read-only.

    No original Apply path calls this automatically: current legacy Apply and
    the S10 activation fence are unchanged. This original-FD9 bridge refuses
    before producing an effective witness unless the ORIGINAL setup record
    and real sealed original source both qualify.
    """
    from voice_ipfw_adapter import require_lifecycle_lock
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    require_lifecycle_lock()
    bound = _s10_native_bound_engine_readback()
    keys = {"engine_version", "source_commit", "engine_sha256", "status",
            "authorization", "physical_transition_allowed",
            "build_provenance_verified"}
    if (type(bound) is not dict or set(bound) != keys or
            bound["status"] != "S10_ORIGINAL_BOUND_ENGINE_VERSION_READ_ONLY" or
            bound["authorization"] != "NONE" or
            bound["physical_transition_allowed"] is not False or
            bound["build_provenance_verified"] is not False or
            type(bound["engine_version"]) is not str or
            re.fullmatch(r"v[0-9]+(?:\.[0-9]+)+", bound["engine_version"]) is None or
            type(bound["source_commit"]) is not str or
            re.fullmatch(r"[a-f0-9]{40}", bound["source_commit"]) is None or
            type(bound["engine_sha256"]) is not str or
            re.fullmatch(r"[a-f0-9]{64}", bound["engine_sha256"]) is None):
        raise OriginalSourceGateRefused("S10_BOUND_ENGINE_UNQUALIFIED")
    source = native_original_fd9(
        operation, raw_pipe, candidate_sha256, sealed=True,
        engine_version=bound["engine_version"],
        **({"bound_record": bound_record} if bound_record is not None else {}))
    if (type(source) is not SourceGateReceipt or
            source.generation != operation or
            source.status != "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY" or
            source.authorization != "NONE" or
            source.physical_transition_allowed is not False or
            type(source.native) is not NativeParity or
            type(source.effective) is not EffectiveSnapshot or
            source.effective.status != "DETACHED_EFFECTIVE_INPUT_ONLY" or
            source.effective.authorization != "NONE" or
            source.effective.physical_transition_allowed is not False or
            source.effective.argv_sha256 != source.original_args_sha256 or
            source.native.original_args_sha256 != source.original_args_sha256 or
            not re.fullmatch(r"[a-f0-9]{64}", source.original_seal_sha256)):
        raise OriginalSourceGateRefused("S10_EFFECTIVE_SOURCE_UNQUALIFIED")
    if bound != _s10_native_bound_engine_readback():
        raise OriginalSourceGateRefused("S10_BOUND_ENGINE_CHANGED")
    require_lifecycle_lock()
    return source




@dataclass(frozen=True)
class FoundPreparedSourceReceipt:
    """Read-only joint source/CAS evidence, NOT a durable root or commit grant."""

    source: SourceGateReceipt
    plan_sha256: str
    config_base_sha256: str
    config_candidate_sha256: str
    status: str = "ORIGINAL_FOUND_PREPARED_SOURCE_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    final_original_fd9_reattest_required: bool = True


def native_attest_found_prepared_fd9(
        operation: str, raw_pipe: bytes, config_fd: int, *,
        _expected_record: dict | None = None) -> FoundPreparedSourceReceipt:
    """Join the existing Found WAL/CAS to the original sealed S08d source.

    Import-only, called with the genuine inherited Config FD and original
    FD9. No PHP Config lock acquisition in this child, no recursive P2,
    no root stage/bind, no new WAL or writes. This is not a proof of current
    Config revision or previous runtime: the original Config owner must
    supply those at the future combined binding/commit. Only the explicit
    internal binding path may supply the exact expected WAL with old pin.
    A staged candidate is still forbidden by the original source reader.
    """
    from auto_detect_destination_commit import (
        _native_found_wal_context, _qualified_shared_found_batch,
        exclusive_destination_lock)
    from auto_detect_effective_known import _verify_planned_preimages_locked
    from auto_detect_gui_hostlist import AUTO_LOCK
    from auto_detect_owned_sources import OWNED_ROOT
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock
    try:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                type(operation) is not str or not _ID.fullmatch(operation) or
                type(config_fd) is not int or config_fd < 3):
            raise OriginalSourceGateRefused("S10_FOUND_NATIVE_LOCK_REQUIRED")
        require_lifecycle_lock()
        inputs = decode_pipe(raw_pipe)
        store, record, raw, rows, targets, attest = _native_found_wal_context(
            operation, config_fd)
        if (type(record) is not dict or record.get("phase") != "prepared" or
                "manifest" in record or
                (_expected_record is None and "previous_manifest" in record) or
                (_expected_record is not None and record != _expected_record) or
                record["detail"]["id"] != operation or
                type(raw) is not bytes or
                hashlib.sha256(raw).hexdigest() != record["found"]["plan_sha256"]):
            raise OriginalSourceGateRefused("S10_FOUND_PREPARED_REQUIRED")
        detail = record["detail"]
        if (record.get("previous") is not None and
                record["previous"]["candidate"] != detail["base"]):
            raise OriginalSourceGateRefused("S10_FOUND_PREVIOUS_CONFIG_MISMATCH")
        verified = _qualified_shared_found_batch(rows)

        def recheck():
            # The shared source reader takes this SAME P2 lock itself.
            # Never keep it held across that call or wait on Config here.
            with exclusive_destination_lock(AUTO_LOCK, 0):
                if store.read() != record or attest() is not True:
                    raise OriginalSourceGateRefused("S10_FOUND_WAL_OR_SEAL_CHANGED")
                _verify_planned_preimages_locked(
                    verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
                if "previous_manifest" in record:
                    from neutral_root_stage import _verify_original_pinned_root
                    _verify_original_pinned_root(
                        detail=record["previous"], binding=record["previous_manifest"],
                        parent=WORK, owner_uid=0)
                if (attest() is not True or store.read() != record or
                        _read(WORK / operation / "plan.json", 0, MAX_FILE) != raw):
                    raise OriginalSourceGateRefused("S10_FOUND_WAL_OR_SEAL_CHANGED")
                seal_digest = hashlib.sha256(_read(
                    WORK / operation / "bundle-seal.json", 0, 1024)).hexdigest()
                if attest() is not True or store.read() != record:
                    raise OriginalSourceGateRefused("S10_FOUND_WAL_OR_SEAL_CHANGED")
                return seal_digest

        seal = recheck()
        digest = detail["candidate"] if inputs["mode"] == b"auto" else None
        source = native_original_bound_effective_fd9(operation, raw_pipe, digest)
        if (type(source) is not SourceGateReceipt or
                source.native_candidate_sha256 != digest or
                source.generation != operation or
                source.mode != inputs["mode"].decode("ascii") or
                source.status != "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY" or
                source.authorization != "NONE" or
                source.physical_transition_allowed is not False or
                type(source.native) is not NativeParity or
                type(source.effective) is not EffectiveSnapshot or
                type(source.requested_enabled) is not bool or
                source.original_seal_sha256 != seal or recheck() != seal):
            raise OriginalSourceGateRefused("S10_FOUND_SOURCE_CHANGED")
        require_lifecycle_lock()
        return FoundPreparedSourceReceipt(
            source, record["found"]["plan_sha256"], detail["base"], detail["candidate"])
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        raise OriginalSourceGateRefused("S10_FOUND_PREPARED_SOURCE_REFUSED") from None


def native_bind_found_prepared_fd9(operation: str, raw_pipe: bytes,
                                   config_fd: int, *, config_digest: str):
    """Attach one candidate root to the existing Found PREPARED only.

    The existing native Config owner supplies its fresh whole-model base
    digest under inherited FD4. Reuse original FD9, P2 and sealed source.
    The original source reader forbids an existing root: obtain that typed
    receipt BEFORE staging, then re-attest seal/CAS/root without bypassing
    that fence. This import-only step grants no physical authorization.
    """
    from auto_detect_destination_commit import (
        _native_found_wal_context, _qualified_shared_found_batch,
        exclusive_destination_lock)
    from auto_detect_effective_known import _verify_planned_preimages_locked
    from auto_detect_gui_hostlist import AUTO_LOCK
    from auto_detect_owned_sources import OWNED_ROOT
    from neutral_root_stage import (
        attest_prepared_source_root, _stage_candidate, _verify_original_pinned_root)
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock

    try:
        require_lifecycle_lock()
        store, before, raw, rows, targets, attest = _native_found_wal_context(
            operation, config_fd)
        if (type(config_digest) is not str or
                not re.fullmatch(r"[a-f0-9]{64}", config_digest) or
                before["phase"] != "prepared" or "manifest" in before or
                before["detail"]["base"] != config_digest):
            raise OriginalSourceGateRefused("S10_FOUND_BIND_BASE_REQUIRED")
        engine = _s10_native_bound_engine_readback()
        first = native_attest_found_prepared_fd9(
            operation, raw_pipe, config_fd, _expected_record=before)
        source = first.source
        detail = before["detail"]
        plan_sha = hashlib.sha256(raw).hexdigest()
        if (first.plan_sha256 != plan_sha or
                first.config_base_sha256 != config_digest or
                first.config_candidate_sha256 != detail["candidate"] or
                first.authorization != "NONE" or first.physical_transition_allowed or
                first.promotion_allowed or store.read() != before or
                _s10_native_bound_engine_readback() != engine):
            raise OriginalSourceGateRefused("S10_FOUND_BIND_SOURCE_CHANGED")
        enabled = source.requested_enabled
        schema3 = (source.mode == "auto" and
                   source.final_args_sha256 != source.original_args_sha256)
        if schema3 != (source.mode == "auto" and enabled):
            raise OriginalSourceGateRefused("S10_FOUND_BIND_SCHEMA_CHANGED")
        candidate = attest_prepared_source_root(
            source=source, candidate_sha256=detail["candidate"], enabled=enabled,
            parent=WORK, journal_root=store.root, owner_uid=0,
            found_plan_sha256=plan_sha)
        verified = _qualified_shared_found_batch(rows)

        def recheck_locked(expected):
            # No source reader or Config acquisition inside this P2 section.
            if (store.read() != expected or attest() is not True or
                    _read(WORK / operation / "plan.json", 0, MAX_FILE) != raw or
                    hashlib.sha256(_read(
                        WORK / operation / "bundle-seal.json", 0, 1024)
                    ).hexdigest() != source.original_seal_sha256):
                raise OriginalSourceGateRefused("S10_FOUND_BIND_WAL_OR_SEAL_CHANGED")
            _verify_planned_preimages_locked(
                verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
            for pin, key in (("previous_manifest", "previous"),
                             ("manifest", "detail")):
                if pin in expected:
                    _verify_original_pinned_root(
                        detail=expected[key], binding=expected[pin],
                        parent=WORK, owner_uid=0)
            if attest() is not True or store.read() != expected:
                raise OriginalSourceGateRefused("S10_FOUND_BIND_WAL_CHANGED")

        # The ordinary S10a writer does not acquire P2. Keep original
        # Config->P2 held across staging, binding and final CAS verification.
        with exclusive_destination_lock(AUTO_LOCK, 0):
            recheck_locked(before)
            staged = _stage_candidate(
                generation=operation, candidate=candidate, effective=source.effective,
                native=source.native, mode=source.mode, enabled=enabled,
                parent=WORK, journal_root=store.root, owner_uid=0, schema3=schema3,
                found_plan_sha256=plan_sha)
            recheck_locked(before)
            if (staged.root_sha256 != candidate.sha256 or
                    staged.original_seal_sha256 != source.original_seal_sha256):
                raise OriginalSourceGateRefused("S10_FOUND_STAGED_SOURCE_CHANGED")
            bound = store.bind_prepared_manifest(
                generation=operation, effective=source.effective, native=source.native,
                mode=source.mode, enabled=enabled, shared_work_parent=WORK,
                schema3=schema3, found_plan_sha256=plan_sha)
            expected = dict(before, manifest={
                "schema": 2 if schema3 else 1, "generation": operation,
                "root_sha256": staged.root_sha256,
                "seal_sha256": staged.original_seal_sha256,
                "candidate_sha256": detail["candidate"]})
            if bound != expected:
                raise OriginalSourceGateRefused("S10_FOUND_BOUND_SOURCE_CHANGED")
            recheck_locked(expected)
        if (_s10_native_bound_engine_readback() != engine or
                store.read() != expected or attest() is not True):
            raise OriginalSourceGateRefused("S10_FOUND_BIND_ENGINE_OR_OWNER_CHANGED")
        # No service/Config/P1 operation follows from this receipt.
        return first, staged
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        raise OriginalSourceGateRefused("S10_FOUND_BIND_REFUSED") from None


def _bind_original_prepared_source(*, store, parent: Path, before: dict,
                                   source: SourceGateReceipt,
                                   read_config, config_receipt: dict):
    """One original WAL + sibling writer, with the same source in memory.

    The native wrapper fixes the work/journal paths and uses the original
    locked PHP preflight. The parameters here permit disposable tests of
    the same original atomic staging and binding, never another writer.
    Found has its own durable phase family and is deliberately excluded
    until that existing WAL can bind before its first P1/Config mutation.
    """
    from neutral_root_stage import attest_prepared_source_root, _stage_candidate
    from neutral_root_bound_preflight import _attest_bound_candidate
    from neutral_schema3_saved_wan_preimage import _qualified_config
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()
    if (type(before) is not dict or before.get("phase") != "prepared" or
            "found" in before or "manifest" in before or
            store.read() != before or type(source) is not SourceGateReceipt or
            source.generation != before["detail"]["id"] or
            type(source.requested_enabled) is not bool):
        raise OriginalSourceGateRefused("S10_ORIGINAL_PREPARED_REQUIRED")
    detail = before["detail"]
    enabled = source.requested_enabled
    generation = detail["id"]
    identity = _qualified_config(config_receipt, detail, enabled)
    # A Found plan without its original Found WAL must not be treated as
    # ordinary merely because the outer PREPARED record has no found key.
    plan = json.loads(_read(parent / generation / "plan.json",
                            store.owner, MAX_FILE))
    if type(plan) is not dict or "found_intent" in plan or "found_batch" in plan:
        raise OriginalSourceGateRefused("S10_FOUND_PREPARED_NOT_ORDINARY")
    schema3 = (source.mode == "auto" and
               source.final_args_sha256 != source.original_args_sha256)
    if schema3 != (source.mode == "auto" and enabled):
        raise OriginalSourceGateRefused("S10_ORIGINAL_PROMOTION_MISMATCH")

    def recheck_config(expected_record):
        require_lifecycle_lock()
        if (store.read() != expected_record or
                _qualified_config(read_config(), detail, enabled) != identity or
                store.read() != expected_record):
            raise OriginalSourceGateRefused("S10_PREPARED_CONFIG_CHANGED")

    # Original S10a compiler authenticates exact original plan/XML/seal and
    # actual S08c/S08d bytes, not a caller-created root or extra receipt file.
    candidate = attest_prepared_source_root(
        source=source, candidate_sha256=detail["candidate"], enabled=enabled,
        parent=parent, journal_root=store.root, owner_uid=store.owner)
    recheck_config(before)
    common = dict(generation=generation, effective=source.effective,
                  native=source.native, mode=source.mode, enabled=enabled,
                  parent=parent, journal_root=store.root, owner_uid=store.owner,
                  schema3=schema3)
    staged = _stage_candidate(candidate=candidate, **common)
    # If any proof is lost after staging, leave its actual evidence for the
    # original PREPARED recovery. Never delete it or silently activate old.
    recheck_config(before)
    bound = store.bind_prepared_manifest(
        generation=generation, effective=source.effective,
        native=source.native, mode=source.mode, enabled=enabled,
        shared_work_parent=parent, schema3=schema3)
    expected = dict(before, manifest={
        "schema": 2 if schema3 else 1, "generation": generation,
        "root_sha256": staged.root_sha256,
        "seal_sha256": staged.original_seal_sha256,
        "candidate_sha256": detail["candidate"]})
    if bound != expected:
        raise OriginalSourceGateRefused("S10_ORIGINAL_BINDING_CHANGED")
    receipt = _attest_bound_candidate(**common)
    if (receipt.root_sha256 != candidate.sha256 or
            receipt.original_seal_sha256 != source.original_seal_sha256 or
            receipt.original_candidate_sha256 != detail["candidate"] or
            receipt.authorization != "NONE" or
            receipt.physical_transition_allowed is not False or
            receipt.promotion_allowed is not False):
        raise OriginalSourceGateRefused("S10_ORIGINAL_BOUND_ROOT_UNQUALIFIED")
    recheck_config(bound)
    return receipt


def native_bind_original_prepared_fd9(operation: str, raw_pipe: bytes):
    """Bind the actual original sealed source to the actual PREPARED owner.

    Import-only transaction step for the existing Apply owner; no public
    command, configd verb, second FD9, Config writer or activation. The
    ordinary unbound Apply dispatcher is not switched until its physical
    rollback and the separate Found phase are qualified.
    """
    from shared_apply_operation import SharedApplyOperation
    from shared_apply_seal import WORK
    from neutral_schema3_saved_wan_preimage import _native_preflight, _qualified_config
    from voice_ipfw_adapter import require_lifecycle_lock
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    require_lifecycle_lock()
    inputs = decode_pipe(raw_pipe)
    store = SharedApplyOperation(owner=0)
    before = store.read()
    if (type(before) is not dict or before.get("phase") != "prepared" or
            "found" in before or "manifest" in before or
            before["detail"]["id"] != operation):
        raise OriginalSourceGateRefused("S10_ORIGINAL_PREPARED_REQUIRED")
    detail = before["detail"]

    def read_config():
        return _native_preflight(operation, detail["page"])

    # Reuse original native PHP under native Config lock and inherited FD9.
    # Derive the logical digest from PHP, not XML hashing or user arguments.
    config = read_config()
    if type(config) is not dict or config.get("enabled") not in ("0", "1"):
        raise OriginalSourceGateRefused("S10_PREPARED_CONFIG_UNQUALIFIED")
    enabled = config["enabled"] == "1"
    _qualified_config(config, detail, enabled)
    source = native_original_bound_effective_fd9(
        operation, raw_pipe, detail["candidate"] if inputs["mode"] == b"auto" else None)
    if source.requested_enabled is not enabled:
        raise OriginalSourceGateRefused("S10_PREPARED_CONFIG_ENABLED_MISMATCH")
    receipt = _bind_original_prepared_source(
        store=store, parent=WORK, before=before, source=source,
        read_config=read_config, config_receipt=config)
    # Retain this same typed source in memory for the future existing owner
    # semantic preflight; do not turn the immutable pin into a Start permit.
    return source, receipt



def _read_pinned_effective(*, detail: dict, binding: dict, parent: Path,
                           sources: Path, owner_uid: int,
                           engine_version: str) -> tuple[EffectiveSnapshot, bool]:
    """Reconstruct S08d from the original sealed model/release and old pin.

    The original manifest stores structural identity and mutable locators,
    NOT a serialized EffectiveSnapshot. Never substitute current GUI values
    or current Found/P1 files for the previous sealed snapshot. Reuse the
    same S07/S08a/S08d projection; require the reproduced structural hash
    and mutable reference set to match the existing exact durable root.
    """
    from neutral_root_stage import _verify_original_pinned_root
    from neutral_root_manifest import _decode, _proof
    raw = _verify_original_pinned_root(
        detail=detail, binding=binding, parent=parent, owner_uid=owner_uid)
    root = _decode(raw, 16384)
    work = parent / detail["id"]
    release = work / "release"
    model = xml_snapshot(_read(work / "candidate.xml", owner_uid, MAX_XML))
    saved = project(model, registered_ids(
        _read(sources / "registry.sh", owner_uid, 128 * 1024)))
    mode = saved.target_mode
    service = root.get("service")
    if (type(service) is not dict or root.get("schema") != binding["schema"] or
            root.get("generation") != detail["id"] or
            type(saved.enabled) is not bool or
            type(service.get("enabled")) is not bool or
            service["enabled"] is not saved.enabled or
            service.get("target_mode") != mode or
            binding["schema"] != (2 if mode == "auto" and saved.enabled else 1)):
        raise OriginalSourceGateRefused("S10_PINNED_MODEL_MISMATCH")
    # A committed predecessor must not depend on unsealed builder
    # intermediates that can be removed after the original Apply. The
    # exact pinned seal authenticates candidate.xml. Reproduce the original
    # shell heredoc's trailing-LF normalization from that sealed model,
    # then compare the resulting S08d identity to the immutable root below.
    # If traffic.input still exists, it must agree; never use it as
    # independent provenance or fall back from a mismatching input.
    strategy = model["strategy"].get("trafficargs")
    if type(strategy) is not str:
        raise OriginalSourceGateRefused("S10_PINNED_STRATEGY_MISSING")
    traffic = strategy.encode("utf-8").rstrip(b"\n") + b"\n"
    intermediate = work / "traffic.input"
    if intermediate.exists() or intermediate.is_symlink():
        observed_traffic = _read(intermediate, owner_uid, 262145)
        if (not observed_traffic.endswith(b"\n") or
                observed_traffic.rstrip(b"\n") != traffic.rstrip(b"\n")):
            raise OriginalSourceGateRefused("S10_PINNED_STRATEGY_MISMATCH")
    targets = compile_target_profiles(saved, traffic, parse_original_policy(
        _read(sources / "target_mode.sh", owner_uid, 128 * 1024)))
    storage = parse_original_storage(
        _read(sources / "storage.sh", owner_uid, 128 * 1024))
    locators = {row.locator for row in storage.entries
                if row.provider == "managed"} | {
                    "hostlist-exclude.txt", "ipset-exclude.txt"}
    managed = release / "managed"
    _stat(managed, owner_uid, directory=True)
    observed = {name: hashlib.sha256(_read(
        managed / name, owner_uid, MAX_FILE, allow_empty=True)).hexdigest()
        for name in sorted(locators)}
    schema3 = binding["schema"] == 2
    args = _read(release / ("dvtws.original.args" if schema3 else "dvtws.args"),
                 owner_uid, 262144)
    source_map = None
    if mode == "auto":
        source_map = json.loads(_read(release / "auto-detect-source-map.json",
                                      owner_uid, MAX_FILE))
    rows = (None if source_map is None else [
        [row["role"], row["status"], row.get("selector"), row.get("hostlist"),
         row.get("native_number")] for row in source_map["profiles"]])
    capture = json.loads(_read(release / "voice-plan.json",
                               owner_uid, MAX_FILE))["capture"]
    effective = snapshot(
        original_native_args=args, target_mode=mode,
        original_source_rows=rows,
        authored_selectors=tuple(
            tuple(f"<{kind}:{key}>" for kind, key in row.authored)
            for row in targets.profiles),
        saved_wan=saved.saved_wan, resolved_wan=capture["wan"],
        engine_version=engine_version, original_capture=capture,
        original_tcp=_read(release / "tcp-ports.txt", owner_uid, 8192,
                           allow_empty=True),
        original_udp=_read(release / "udp-ports.txt", owner_uid, 8192,
                           allow_empty=True),
        managed_sha256=observed)
    original_key = ("original_structural_sha256" if schema3
                    else "structural_sha256")
    if (service.get(original_key) != effective.structural_sha256 or
            root["resources"]["mutable_refs"] != _proof(effective, args) or
            _verify_original_pinned_root(
                detail=detail, binding=binding, parent=parent,
                owner_uid=owner_uid) != raw):
        raise OriginalSourceGateRefused("S10_PINNED_EFFECTIVE_MISMATCH")
    return effective, saved.enabled


@dataclass(frozen=True)
class FoundSemanticReceipt:
    """Bound Found comparison, never a file/Config/lifecycle permission."""

    generation: str
    previous_generation: str
    candidate_root_sha256: str
    previous_root_sha256: str | None
    plan_sha256: str
    previous_state: str
    candidate_enabled: bool
    decision: EffectiveDecision
    reload_candidate: bool
    previous_running_epoch_sha256: str | None = None
    status: str = "ORIGINAL_FOUND_BOUND_SEMANTIC_PROPOSAL_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    final_original_fd9_reattest_required: bool = True


def _found_effective_decision(old, candidate, changed_sources: int) -> EffectiveDecision:
    """Use S08d; no old equality or atomic multi-list proof means restart."""
    if old is None:
        return EffectiveDecision("RESTART_REQUIRED", (), ())
    decision = plan(old[0], candidate[0])
    if (old[1] != candidate[1] or
            (decision.kind == "RELOAD_SAFE_CANDIDATE" and
             (len(decision.changed_active) > 1 or changed_sources > 1))):
        return EffectiveDecision("RESTART_REQUIRED", decision.changed_active,
                                 decision.changed_inactive)
    return decision


def native_plan_found_prepared_fd9(witness: FoundPreparedSourceReceipt,
                                  config_fd: int, *,
                                  config_digest: str) -> FoundSemanticReceipt:
    """Read-only native comparison, without a write continuation."""
    return _with_native_found_prepared_semantic(
        witness, config_fd, config_digest=config_digest)


def _with_native_found_prepared_semantic(witness: FoundPreparedSourceReceipt,
                                        config_fd: int, *, config_digest: str,
                                        continue_locked=None):
    """Read bound Found source and old native owner under original FD9/FD4/P2.

    The original PHP Config owner supplies its current whole-model digest
    while retaining the inherited FD4. Do NOT invoke ordinary PHP preflight
    again from this child. This comparison itself does not stage/bind,
    create a journal, save Config or change P1/runtime. Even a reload
    candidate needs the separate original commit/rollback contract.
    A running pinned Auto predecessor also needs its original immutable
    epoch. STOPPED remains observational, not full retired-epoch proof.
    Never acquire the queue lock after Config FD4. The private original
    file writer may continue inside this same P2 scope after all checks;
    the public comparison never supplies that continuation.
    """
    from auto_detect_owner import attest_prepared_found_learning_predecessor
    from auto_detect_destination_commit import (
        _native_found_wal_context, _qualified_shared_found_batch,
        exclusive_destination_lock)
    from auto_detect_effective_known import _verify_planned_preimages_locked
    from auto_detect_gui_hostlist import AUTO_LOCK
    from auto_detect_owned_sources import OWNED_ROOT
    from neutral_root_bound_preflight import BoundRootReceipt, _attest_bound_candidate
    from neutral_schema3_previous_physical import _full_prior_tree, _running_native
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock
    from voice_live_inspect import (
        COMMON_ACTIVE, CHILD_PID, MONITOR_PID, examine_pending_found_previous)

    try:
        require_lifecycle_lock()
        if (type(witness) is not FoundPreparedSourceReceipt or
                witness.status != "ORIGINAL_FOUND_PREPARED_SOURCE_ONLY" or
                witness.authorization != "NONE" or witness.physical_transition_allowed or
                witness.promotion_allowed or
                witness.final_original_fd9_reattest_required is not True or
                type(witness.source) is not SourceGateReceipt or
                type(config_digest) is not str or
                not re.fullmatch(r"[a-f0-9]{64}", config_digest)):
            raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_WITNESS_REQUIRED")
        source = witness.source
        if (source.status != "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY" or
                source.authorization != "NONE" or source.physical_transition_allowed or
                type(source.native) is not NativeParity or
                type(source.effective) is not EffectiveSnapshot or
                type(source.requested_enabled) is not bool):
            raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_SOURCE_REQUIRED")
        generation = source.generation
        store, before, raw, rows, targets, attest = _native_found_wal_context(
            generation, config_fd)
        detail = before["detail"]
        prior = before.get("previous")
        old_pin = before.get("previous_manifest")
        pin = before.get("manifest")
        plan_sha = hashlib.sha256(raw).hexdigest()
        schema3 = source.mode == "auto" and source.requested_enabled
        if (before["phase"] != "prepared" or type(pin) is not dict or
                type(prior) is not dict or prior["id"] == generation or
                detail["id"] != generation or
                prior["candidate"] != config_digest or
                detail["base"] != config_digest or
                witness.config_base_sha256 != config_digest or
                witness.config_candidate_sha256 != detail["candidate"] or
                witness.plan_sha256 != plan_sha or
                before["found"]["plan_sha256"] != plan_sha or
                pin["seal_sha256"] != source.original_seal_sha256 or
                pin["candidate_sha256"] != detail["candidate"] or
                pin["schema"] != (2 if schema3 else 1)):
            raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_BOUND_REQUIRED")
        verified = _qualified_shared_found_batch(rows)
        changed_sources = sum(row[0] != row[1] for row in verified.values())
        engine = _s10_native_bound_engine_readback()
        read = dict(parent=WORK, sources=Path(__file__).parent, owner_uid=0,
                    engine_version=engine["engine_version"])
        bound_args = dict(
            generation=generation, effective=source.effective, native=source.native,
            mode=source.mode, enabled=source.requested_enabled, parent=WORK,
            journal_root=store.root, owner_uid=0, schema3=schema3,
            found_plan_sha256=plan_sha)

        def observe_locked():
            if store.read() != before or attest() is not True:
                raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_OWNER_CHANGED")
            _verify_planned_preimages_locked(
                verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
            root = _attest_bound_candidate(**bound_args)
            if (type(root) is not BoundRootReceipt or root.authorization != "NONE" or
                    root.physical_transition_allowed or root.promotion_allowed or
                    root.generation != generation or
                    root.root_sha256 != pin["root_sha256"] or
                    root.original_seal_sha256 != pin["seal_sha256"] or
                    root.original_candidate_sha256 != detail["candidate"]):
                raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_ROOT_CHANGED")
            candidate = _read_pinned_effective(detail=detail, binding=pin, **read)
            if candidate != (source.effective, source.requested_enabled):
                raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_EFFECTIVE_CHANGED")
            old = None if old_pin is None else _read_pinned_effective(
                detail=prior, binding=old_pin, **read)
            observed = examine_pending_found_previous(before)
            if (observed.get("id") != prior["id"] or
                    observed.get("state") not in ("ready", "stopped") or
                    (observed["state"] == "ready" and old is not None and not old[1])):
                raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_PREVIOUS_REQUIRED")
            tree = _full_prior_tree(WORK / prior["id"], COMMON_ACTIVE, 0)
            runtime = (_running_native(
                WORK / prior["id"] / "release", owner_uid=0,
                child_pidfile=CHILD_PID, monitor_pidfile=MONITOR_PID)
                if observed["state"] == "ready" else None)
            epoch_sha = None
            if (old_pin is not None and old_pin["schema"] == 2 and
                    observed["state"] == "ready"):
                learning, epoch_sha = attest_prepared_found_learning_predecessor(
                    before, config_fd)
                if (learning.operation_id != prior["id"] or
                        learning.generation != prior["id"] or
                        learning.owner_candidate_sha256 != prior["candidate"] or
                        (learning.owner.pid, learning.owner.started) !=
                        (runtime.pid, runtime.started) or
                        type(epoch_sha) is not str or
                        not re.fullmatch(r"[a-f0-9]{64}", epoch_sha)):
                    raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_EPOCH_CHANGED")
            if store.read() != before or attest() is not True:
                raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_OWNER_CHANGED")
            return root, old, candidate, observed, tree, runtime, epoch_sha

        with exclusive_destination_lock(AUTO_LOCK, 0):
            first = observe_locked()
            if (observe_locked() != first or
                    _s10_native_bound_engine_readback() != engine or
                    store.read() != before or attest() is not True):
                raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_OBSERVATION_CHANGED")
            _, old, candidate, observed, _, _, epoch_sha = first
            decision = _found_effective_decision(old, candidate, changed_sources)
            receipt = FoundSemanticReceipt(
                generation, prior["id"], pin["root_sha256"],
                None if old_pin is None else old_pin["root_sha256"],
                plan_sha, observed["state"], source.requested_enabled, decision,
                observed["state"] == "ready" and source.requested_enabled and
                decision.kind == "RELOAD_SAFE_CANDIDATE",
                previous_running_epoch_sha256=epoch_sha)
            if continue_locked is None:
                return receipt
            if not callable(continue_locked):
                raise OriginalSourceGateRefused("S10_FOUND_CONTINUATION_INVALID")
            return continue_locked(receipt, store, before, raw, rows, targets, attest)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        raise OriginalSourceGateRefused("S10_FOUND_SEMANTIC_REFUSED") from None


@dataclass(frozen=True)
class OriginalSemanticReceipt:
    generation: str
    previous_generation: str | None
    candidate_root_sha256: str
    previous_root_sha256: str | None
    decision: EffectiveDecision
    previous_physical: object
    lifecycle_proposal: str = "UNCLASSIFIED"
    status: str = "ORIGINAL_PREPARED_SEMANTIC_PROPOSAL_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    final_original_fd9_reattest_required: bool = True


def _ordinary_effective_decision(old, candidate) -> EffectiveDecision:
    """S08d proposal plus original ordinary Apply's multi-list safety fence.

    No atomic multi-file active update has been proved for this path. An
    active list change together with any other managed list change must
    therefore be classified before mutation, not upgraded to Restart
    after a failed Reload. Inactive-only edits remain SAVE_ONLY.
    """
    if old is None:
        return EffectiveDecision("RESTART_REQUIRED", (), ())
    decision = plan(old[0], candidate[0])
    if (decision.kind == "RELOAD_SAFE_CANDIDATE" and
            len(decision.changed_active) + len(decision.changed_inactive) > 1):
        return EffectiveDecision("RESTART_REQUIRED", decision.changed_active,
                                 decision.changed_inactive)
    return decision


def _running_lifecycle_proposal(enabled: bool, decision: EffectiveDecision) -> str:
    return ("STOP" if enabled is False else {
        "NO_CHANGE": "NO_CHANGE",
        "SAVE_ONLY": "SAVE_ONLY",
        "RELOAD_SAFE_CANDIDATE": "RELOAD",
        "RESTART_REQUIRED": "RESTART",
    }[decision.kind])


def native_plan_original_prepared_fd9(source: SourceGateReceipt) -> OriginalSemanticReceipt:
    """Classify an original bound PREPARED by exact old-owner state, never act.

    Reuse the one original FD9, pinned S08d and the existing native old-owner
    observers. READY must pass full running P2c/Config/IPFW; STOPPED must pass
    the separate full quiescent P2/epoch/tree/kernel proof. A failed branch
    NEVER falls through to the other branch. First install is strictly cold.
    """
    from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
    from shared_apply_seal import WORK
    from neutral_schema3_previous_preimage import (
        PreviousRuntimeReceipt, attest_prepared_previous_under_fd9)
    from neutral_schema3_previous_physical import (
        CompletePriorPreimage, attest_previous_physical_under_fd9)
    from neutral_schema3_quiescent_preimage import (
        QuiescentPreimage, attest_quiescent_under_fd9)
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()
    try:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                type(source) is not SourceGateReceipt or
                source.status != "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY" or
                source.authorization != "NONE" or source.physical_transition_allowed or
                type(source.native) is not NativeParity or
                type(source.effective) is not EffectiveSnapshot or
                type(source.requested_enabled) is not bool):
            raise OriginalSourceGateRefused("S10_SEMANTIC_NATIVE_SOURCE_REQUIRED")
        store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
        before = store.read()
        if (type(before) is not dict or before.get("phase") != "prepared" or
                "found" in before or type(before.get("detail")) is not dict or
                type(before.get("manifest")) is not dict or
                before["detail"].get("id") != source.generation or
                before["manifest"].get("seal_sha256") != source.original_seal_sha256):
            raise OriginalSourceGateRefused("S10_SEMANTIC_ORIGINAL_PREPARED_REQUIRED")
        prior = before.get("previous")
        old_pin = before.get("previous_manifest")
        if (("previous" in before and type(prior) is not dict) or
                (prior is None and "previous_manifest" in before) or
                ("previous_manifest" in before and type(old_pin) is not dict) or
                (prior is not None and
                 (prior.get("id") == source.generation or
                  prior.get("candidate") != before["detail"].get("base")))):
            raise OriginalSourceGateRefused("S10_SEMANTIC_PREVIOUS_PIN_INVALID")
        current_pin = before["manifest"]
        engine = _s10_native_bound_engine_readback()
        read = dict(parent=WORK, sources=Path(__file__).parent, owner_uid=0,
                    engine_version=engine["engine_version"])
        candidate = _read_pinned_effective(
            detail=before["detail"], binding=current_pin, **read)
        if candidate != (source.effective, source.requested_enabled):
            raise OriginalSourceGateRefused("S10_SEMANTIC_CANDIDATE_CHANGED")
        old = None if old_pin is None else _read_pinned_effective(
            detail=prior, binding=old_pin, **read)
        proof_args = dict(
            generation=source.generation, native=source.native,
            effective=source.effective, enabled=source.requested_enabled)
        observed = None
        if prior is not None:
            observed = attest_prepared_previous_under_fd9(**proof_args)
            if (type(observed) is not PreviousRuntimeReceipt or
                    observed.authorization != "NONE" or
                    observed.physical_transition_allowed or
                    observed.promotion_allowed or
                    observed.generation != source.generation or
                    observed.root_sha256 != current_pin["root_sha256"] or
                    observed.previous_generation != prior["id"] or
                    observed.previous_candidate_sha256 != prior["candidate"] or
                    observed.status != "ORIGINAL_SCHEMA3_PREPARED_PREVIOUS_READ_ONLY" or
                    observed.observed_previous_state not in ("ready", "stopped") or
                    (observed.observed_previous_state == "stopped" and
                     (observed.previous_rule_count != 0 or
                      observed.previous_table_count != 0))):
                raise OriginalSourceGateRefused("S10_SEMANTIC_PREVIOUS_UNQUALIFIED")
        if observed is not None and observed.observed_previous_state == "ready":
            # A prior pinned model declaring OFF cannot be a genuine
            # verified RUNNING owner. Legacy unpinned models remain RESTART.
            if old is not None and old[1] is not True:
                raise OriginalSourceGateRefused("S10_SEMANTIC_OLD_RUNNING_DISABLED")
            physical = attest_previous_physical_under_fd9(**proof_args)
            if (type(physical) is not CompletePriorPreimage or
                    physical.authorization != "NONE" or
                    physical.physical_transition_allowed or physical.promotion_allowed or
                    physical.root_sha256 != current_pin["root_sha256"] or
                    physical.previous_generation != prior["id"] or
                    physical.saved_config_base_sha256 != before["detail"]["base"] or
                    (source.requested_enabled is False and
                     physical.resolved_wan_device is not None) or
                    (source.requested_enabled is True and
                     type(physical.resolved_wan_device) is not str)):
                raise OriginalSourceGateRefused("S10_SEMANTIC_PHYSICAL_UNQUALIFIED")
            lifecycle = None  # resolved from S08d below
        else:
            # Genuine committed STOPPED, or no predecessor with original
            # strict cold proof. Neither is a fallback from a READY failure.
            physical = attest_quiescent_under_fd9(**proof_args)
            expected = ("committed-stopped" if prior is not None
                        else "first-install-empty")
            if (type(physical) is not QuiescentPreimage or
                    physical.authorization != "NONE" or
                    physical.physical_transition_allowed or physical.promotion_allowed or
                    physical.original_executor_recheck_required is not True or
                    physical.generation != source.generation or
                    physical.root_sha256 != current_pin["root_sha256"] or
                    physical.old_state != expected or
                    physical.previous_generation != (
                        None if prior is None else prior["id"]) or
                    (prior is None and
                     (physical.previous_release_sha256 is not None or
                      physical.retirement_state != "no-prior-data")) or
                    (prior is not None and
                     (type(physical.previous_release_sha256) is not str or
                      physical.retirement_state not in (
                          "original-epoch-ack-retired",
                          "inert-no-producer-data",
                          "inert-idle-producer") or
                      (physical.retirement_state == "inert-idle-producer" and
                       (type(physical.idle_producer) is not tuple or
                        len(physical.idle_producer) != 2 or
                        any(type(row) is not tuple or len(row) != 4
                            for row in physical.idle_producer))) or
                      (physical.retirement_state == "inert-no-producer-data" and
                       physical.idle_producer is not None))) or
                    physical.kernel_state not in (
                        "native-kernel-absent", "native-managed-kernel-empty") or
                    physical.config_base_sha256 != before["detail"]["base"] or
                    physical.config_candidate_sha256 != before["detail"]["candidate"] or
                    (source.requested_enabled is False and
                     physical.verified_wan_device is not None) or
                    (source.requested_enabled is True and
                     (type(physical.verified_wan_device) is not str or
                      not physical.verified_wan_device))):
                raise OriginalSourceGateRefused("S10_SEMANTIC_QUIESCENT_UNQUALIFIED")
            lifecycle = ("START" if source.requested_enabled else "SAVE_ONLY")
        # S08d remains the ONE pure structural classifier. Old unpinned
        # and true cold have no equality evidence, hence structural RESTART.
        decision = _ordinary_effective_decision(old, candidate)
        if lifecycle is None:
            # Physical state (RUNNING) dominates OFF even if equal S08d.
            lifecycle = _running_lifecycle_proposal(source.requested_enabled, decision)
        if (candidate != _read_pinned_effective(
                detail=before["detail"], binding=current_pin, **read) or
                (old is not None and old != _read_pinned_effective(
                    detail=prior, binding=old_pin, **read)) or
                engine != _s10_native_bound_engine_readback() or
                store.read() != before):
            raise OriginalSourceGateRefused("S10_SEMANTIC_ORIGINAL_OWNER_CHANGED")
        require_lifecycle_lock()
        return OriginalSemanticReceipt(
            source.generation, None if prior is None else prior["id"],
            current_pin["root_sha256"],
            None if old_pin is None else old_pin["root_sha256"],
            decision, physical, lifecycle_proposal=lifecycle)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        raise OriginalSourceGateRefused("S10_SEMANTIC_PREPARED_REFUSED") from None

def _managed_change_preimages(old: EffectiveSnapshot, candidate: EffectiveSnapshot,
                              decision: EffectiveDecision, *, previous_release: Path,
                              candidate_release: Path, active: Path, owner_uid: int) -> tuple:
    """Read exact changed managed bytes and CAS identities, never replace them.

    Only same-structure no-restart proposals qualify. The sealed old bytes
    must equal the live old bytes; the sealed candidate must match S08d.
    Return in-flight evidence, not a durable intent or a Reload permit.
    """
    from auto_detect_destination_commit import _target, _target_identity

    if (decision != _ordinary_effective_decision((old, True), (candidate, True)) or
            decision.kind not in ("NO_CHANGE", "SAVE_ONLY", "RELOAD_SAFE_CANDIDATE")):
        raise OriginalSourceGateRefused("S10_MANAGED_PREIMAGE_DECISION_INVALID")
    old_hashes = dict(old.linked + old.unlinked)
    new_hashes = dict(candidate.linked + candidate.unlinked)
    names = tuple(sorted(decision.changed_active + decision.changed_inactive))
    if (set(old_hashes) != set(new_hashes) or len(names) != len(set(names)) or
            names != tuple(sorted(name for name in old_hashes
                                  if old_hashes[name] != new_hashes[name]))):
        raise OriginalSourceGateRefused("S10_MANAGED_PREIMAGE_SCOPE_INVALID")
    if not names:
        return ()
    roots = (previous_release, candidate_release, active)
    if len(set(roots)) != 3:
        raise OriginalSourceGateRefused("S10_MANAGED_PREIMAGE_ROOT_ALIAS")
    for root in roots:
        _stat(root, owner_uid, directory=True)
        _stat(root / "managed", owner_uid, directory=True)

    def read(root, name, expected):
        data, info = _target(root / "managed" / name, owner_uid)
        if hashlib.sha256(data).hexdigest() != expected:
            raise OriginalSourceGateRefused("S10_MANAGED_PREIMAGE_BYTES_CHANGED")
        return data, _target_identity(info)

    rows = []
    for name in names:
        if re.fullmatch(r"(?:hostlist|ipset)-[a-z][a-z0-9-]{0,63}\.txt", name) is None:
            raise OriginalSourceGateRefused("S10_MANAGED_PREIMAGE_LOCATOR_INVALID")
        former, former_id = read(previous_release, name, old_hashes[name])
        wanted, wanted_id = read(candidate_release, name, new_hashes[name])
        current, current_id = read(active, name, old_hashes[name])
        if former != current or former == wanted or len({former_id[:2], wanted_id[:2], current_id[:2]}) != 3:
            raise OriginalSourceGateRefused("S10_MANAGED_PREIMAGE_ALIAS_OR_DRIFT")
        rows.append((name, old_hashes[name], new_hashes[name], former_id, wanted_id, current_id))
    return tuple(rows)


def native_recheck_running_prepared_fd9(
        operation: str, raw_pipe: bytes, *, source: SourceGateReceipt,
        semantic: OriginalSemanticReceipt, config_fd: int, config_digest: str):
    """Join the ordinary PREPARED proposal to the original locked native owner.

    The original coordinator must obtain source/semantic before Config lock,
    then supply the same original input and the actual locked Config digest.
    No nested PHP preflight, no P2a acquisition, no WAL advance or signal.
    This is not a Reload permit: observe exact managed-list CAS preimages
    and executable/argv, but mutation-bound CAS, atomic promotion and
    recovery still belong to the original transaction coordinator.
    """
    from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
    from shared_apply_seal import WORK
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from neutral_schema3_previous_physical import (
        CompletePriorPreimage, LockedRunningPredecessor,
        attest_bound_running_predecessor_under_fd9, _running_executable_identity,
        _running_native, CHILD_EXEC, CHILD_PID, MONITOR_PID, COMMON_ACTIVE)
    from voice_ipfw_adapter import require_lifecycle_lock

    try:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                type(operation) is not str or not _ID.fullmatch(operation) or
                type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
                type(config_digest) is not str or not re.fullmatch(r"[a-f0-9]{64}", config_digest) or
                type(source) is not SourceGateReceipt or source.generation != operation or
                type(source.requested_enabled) is not bool or
                type(semantic) is not OriginalSemanticReceipt or semantic.generation != operation or
                type(semantic.previous_physical) is not CompletePriorPreimage or
                semantic.status != "ORIGINAL_PREPARED_SEMANTIC_PROPOSAL_ONLY" or
                semantic.authorization != "NONE" or semantic.physical_transition_allowed or
                semantic.promotion_allowed or semantic.final_original_fd9_reattest_required is not True):
            raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_SCOPE_REQUIRED")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
        before = store.read()
        if (type(before) is not dict or before.get("phase") != "prepared" or
                "found" in before or type(before.get("manifest")) is not dict or
                type(before.get("previous_manifest")) is not dict or
                type(before.get("previous")) is not dict):
            raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_BOUND_REQUIRED")
        detail, prior = before["detail"], before["previous"]
        pin, old_pin = before["manifest"], before["previous_manifest"]
        if (detail["id"] != operation or prior["id"] == operation or
                detail["base"] != config_digest or prior["candidate"] != config_digest or
                semantic.previous_generation != prior["id"] or
                semantic.candidate_root_sha256 != pin["root_sha256"] or
                semantic.previous_root_sha256 != old_pin["root_sha256"] or
                source.original_seal_sha256 != pin["seal_sha256"]):
            raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_IDENTITY_CHANGED")
        inputs = decode_pipe(raw_pipe)
        digest = detail["candidate"] if inputs["mode"] == b"auto" else None

        def observe():
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != before:
                raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_JOURNAL_CHANGED")
            engine = _s10_native_bound_engine_readback()
            fresh = native_original_bound_effective_fd9(
                operation, raw_pipe, digest, bound_record=before)
            if fresh != source:
                raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_SOURCE_CHANGED")
            read = dict(parent=WORK, sources=Path(__file__).parent, owner_uid=0,
                        engine_version=engine["engine_version"])
            candidate = _read_pinned_effective(detail=detail, binding=pin, **read)
            old = _read_pinned_effective(detail=prior, binding=old_pin, **read)
            if candidate != (fresh.effective, fresh.requested_enabled) or old[1] is not True:
                raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_EFFECTIVE_CHANGED")
            decision = _ordinary_effective_decision(old, candidate)
            if (decision != semantic.decision or
                    _running_lifecycle_proposal(fresh.requested_enabled, decision) != semantic.lifecycle_proposal):
                raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_DECISION_CHANGED")
            physical = attest_bound_running_predecessor_under_fd9(
                before, preimage=semantic.previous_physical,
                config_fd=config_fd, config_digest=config_digest)
            if (type(physical) is not LockedRunningPredecessor or
                    physical.generation != operation or physical.previous_generation != prior["id"] or
                    physical.previous_root_sha256 != old_pin["root_sha256"] or
                    physical.config_base_sha256 != config_digest or
                    physical.authorization != "NONE" or physical.physical_transition_allowed or
                    physical.executable_identity is not None or
                    physical.managed_preimages is not None):
                raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_PHYSICAL_CHANGED")
            executable = _running_executable_identity(
                physical.running.pid, engine["engine_sha256"],
                executable=Path(CHILD_EXEC), runner=subprocess.run)
            managed = None
            if fresh.requested_enabled and decision.kind in (
                    "NO_CHANGE", "SAVE_ONLY", "RELOAD_SAFE_CANDIDATE"):
                managed = _managed_change_preimages(
                    old[0], candidate[0], decision,
                    previous_release=WORK / prior["id"] / "release",
                    candidate_release=WORK / detail["id"] / "release",
                    active=COMMON_ACTIVE, owner_uid=0)
            # Bracket TEXT and list observation with original PID/birth/argv census,
            # and original installed-engine guard, not a second provenance.
            if (_running_native(WORK / prior["id"] / "release", owner_uid=0,
                                child_pidfile=CHILD_PID, monitor_pidfile=MONITOR_PID)
                    != physical.running or engine != _s10_native_bound_engine_readback() or
                    store.read() != before):
                raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_EXECUTABLE_CHANGED")
            physical = replace(physical, executable_identity=executable,
                               managed_preimages=managed)
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            return fresh, candidate, old, decision, physical, engine

        first = observe()
        if observe() != first or store.read() != before:
            raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_WITNESS_CHANGED")
        # In-flight observation only. A caller must not manufacture an
        # ACTIVATING or terminal record from this return value.
        return first[4]
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError,
            subprocess.SubprocessError):
        raise OriginalSourceGateRefused("S10_LOCKED_RUNNING_PRECHECK_REFUSED") from None


def _managed_running_digest(running, executable: tuple) -> str:
    from dataclasses import astuple

    return hashlib.sha256(json.dumps((astuple(running), executable),
                                     separators=(",", ":")).encode("ascii")).hexdigest()


def _native_managed_running_digest(prior_release: Path, config_fd: int) -> str:
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from neutral_schema3_previous_physical import (
        _running_native, _running_executable_identity, CHILD_EXEC, CHILD_PID, MONITOR_PID,
    )
    from voice_firewall_transaction import verify_prior_state
    from voice_ipfw_adapter import (
        require_lifecycle_lock, FreeBSDIPFWAdapter, shared_release_manifest,
    )

    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    observed = _running_native(prior_release, owner_uid=0,
                               child_pidfile=CHILD_PID, monitor_pidfile=MONITOR_PID)
    engine = _s10_native_bound_engine_readback()
    executable = _running_executable_identity(observed.pid, engine["engine_sha256"],
                                               executable=Path(CHILD_EXEC), runner=subprocess.run)
    capture = shared_release_manifest(prior_release)
    if capture["rule_base"] != 19000 or capture["rule_max"] not in (19010, 19099):
        raise OriginalSourceGateRefused("S10_MANAGED_KERNEL_SCOPE_INVALID")
    verify_prior_state(FreeBSDIPFWAdapter(19000, 19099), capture, capture)
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return _managed_running_digest(observed, executable)


def native_write_running_managed_file_fd9(
        operation: str, raw_pipe: bytes, *, source: SourceGateReceipt,
        semantic: OriginalSemanticReceipt, config_fd: int, config_digest: str) -> dict:
    """Stage and replace one referenced list under the original three locks."""
    from auto_detect_destination_commit import (
        exclusive_destination_lock, _write_bound_managed_file_locked,
        _restore_bound_managed_file_locked)
    from auto_detect_gui_hostlist import AUTO_LOCK
    from neutral_schema3_previous_physical import COMMON_ACTIVE
    from shared_apply_operation import SharedApplyOperation, MANAGED_WRITING
    from shared_apply_seal import WORK

    physical = native_recheck_running_prepared_fd9(
        operation, raw_pipe, source=source, semantic=semantic,
        config_fd=config_fd, config_digest=config_digest)
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if (type(record) is not dict or record.get("phase") != "prepared" or "found" in record or
            record["detail"]["id"] != physical.generation or
            record["detail"]["base"] != physical.config_base_sha256 or
            physical.config_base_sha256 != config_digest or
            record["manifest"]["root_sha256"] != semantic.candidate_root_sha256 or
            record["previous"]["id"] != physical.previous_generation or
            record["previous_manifest"]["root_sha256"] != physical.previous_root_sha256 or
            record["manifest"]["schema"] != 1 or record["previous_manifest"]["schema"] != 1 or
            physical.epoch_sha256 is not None or physical.executable_identity is None or
            semantic.lifecycle_proposal != "RELOAD" or semantic.decision.kind != "RELOAD_SAFE_CANDIDATE" or
            semantic.decision.changed_inactive or len(semantic.decision.changed_active) != 1 or
            not physical.managed_preimages or len(physical.managed_preimages) != 1 or
            physical.managed_preimages[0][0] != semantic.decision.changed_active[0]):
        raise OriginalSourceGateRefused("S10_MANAGED_SINGLE_ACTIVE_SCOPE_REQUIRED")
    prior_release = WORK / physical.previous_generation / "release"
    running_sha256 = _managed_running_digest(physical.running, physical.executable_identity)

    def attest():
        return _native_managed_running_digest(prior_release, config_fd) == running_sha256

    with exclusive_destination_lock(AUTO_LOCK, 0):
        try:
            return _write_bound_managed_file_locked(
                store, record, physical.managed_preimages[0], parent=WORK,
                active=COMMON_ACTIVE, attest=attest, running_sha256=running_sha256)
        except (OSError, ValueError, RuntimeError):
            pending = store.read()
            if (pending is not None and pending["phase"] == MANAGED_WRITING and
                    all(pending.get(key) == value for key, value in record.items()
                        if key != "phase")):
                try:
                    _restore_bound_managed_file_locked(store, pending, parent=WORK,
                                                       active=COMMON_ACTIVE, attest=attest)
                except (OSError, ValueError, RuntimeError):
                    raise OriginalSourceGateRefused("S10_MANAGED_RESTORE_UNCERTAIN") from None
            raise


def _managed_handoff_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _managed_handoff_digest(value) -> str:
    from dataclasses import asdict
    return hashlib.sha256(_managed_handoff_json(asdict(value))).hexdigest()


def _managed_handoff_scope(record, operation: str) -> dict:
    if (type(record) is not dict or record.get("phase") != "prepared" or
            "found" in record or record.get("manifest", {}).get("schema") != 1 or
            record.get("previous_manifest", {}).get("schema") != 1 or
            record["detail"]["id"] != operation or
            record["detail"]["page"] != "strategies" or
            record["detail"]["base"] == record["detail"]["candidate"] or
            not record["detail"]["changed_fields"] or
            record["previous"]["candidate"] != record["detail"]["base"]):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_SCOPE_REQUIRED")
    return record["detail"]


def _managed_handoff_wire(source: SourceGateReceipt, semantic: OriginalSemanticReceipt,
                          raw_pipe: bytes) -> bytes:
    from dataclasses import asdict
    from neutral_schema3_previous_physical import CompletePriorPreimage

    if (type(source) is not SourceGateReceipt or type(semantic) is not OriginalSemanticReceipt or
            type(semantic.previous_physical) is not CompletePriorPreimage or
            semantic.lifecycle_proposal != "RELOAD" or
            semantic.decision.kind != "RELOAD_SAFE_CANDIDATE" or
            len(semantic.decision.changed_active) != 1 or semantic.decision.changed_inactive or
            source.requested_enabled is not True or source.generation != semantic.generation or
            type(raw_pipe) is not bytes or len(raw_pipe) > MAX_PIPE):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_PROPOSAL_REQUIRED")
    header = _managed_handoff_json({"source": _managed_handoff_digest(source),
        "semantic": _managed_handoff_digest(semantic),
        "physical": asdict(semantic.previous_physical)})
    if len(header) > 8192:
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_HEADER_TOO_LARGE")
    return header + b"\n" + raw_pipe


def native_write_managed_handoff_locked(operation: str, witness: str, stream, *, config_fd: int) -> dict:
    """Private stdin from original FD9 parent, re-attested under native FD4.

    The transport carries observations only, never a phase grant. Rebuild
    the typed source and decision from the original pinned seal, and reuse
    the complete existing locked physical/CAS writer. No nested PHP call.
    """
    from dataclasses import asdict
    from neutral_schema3_previous_physical import CompletePriorPreimage
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from shared_apply_operation import SharedApplyOperation, _config_save_witness
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation) or
            type(config_fd) is not int or config_fd < 3 or config_fd == 9):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_NATIVE_REQUIRED")
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    before = store.read()
    detail = _managed_handoff_scope(before, operation)
    if witness != _config_save_witness(detail, verify_seal(WORK / operation, owner=0)["sha256"]["plan.json"]):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_CONFIG_CHANGED")
    line = stream.readline(8194)
    if not line.endswith(b"\n") or len(line) > 8193:
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_HEADER_INVALID")
    header = json.loads(line)
    if (type(header) is not dict or set(header) != {"source", "semantic", "physical"} or
            _managed_handoff_json(header) + b"\n" != line or
            any(type(header[k]) is not str or not re.fullmatch(r"[a-f0-9]{64}", header[k])
                for k in ("source", "semantic")) or type(header["physical"]) is not dict):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_HEADER_INVALID")
    data = header["physical"]
    fields = ("generation", "root_sha256", "previous_generation", "old_release_sha256",
              "active_release_sha256", "saved_config_base_sha256", "resolved_wan_device",
              "prior_pid", "prior_birth", "supervisor_pid", "supervisor_birth",
              "original_kernel_argv_sha256")
    physical = CompletePriorPreimage(**{key: data[key] for key in fields})
    if (_managed_handoff_json(asdict(physical)) != _managed_handoff_json(data) or
            any(type(data[k]) is not int or data[k] <= 0 for k in ("prior_pid", "supervisor_pid")) or
            any(type(data[k]) is not str or not 0 < len(data[k]) <= 256 for k in fields
                if k not in ("prior_pid", "supervisor_pid"))):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_PHYSICAL_INVALID")
    raw = stream.read(MAX_PIPE + 1)
    if len(raw) > MAX_PIPE or decode_pipe(raw)["mode"] not in (b"all", b"list"):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_SOURCE_INVALID")
    source = native_original_bound_effective_fd9(operation, raw, bound_record=before)
    if _managed_handoff_digest(source) != header["source"]:
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_SOURCE_CHANGED")
    pin, old_pin = before["manifest"], before["previous_manifest"]
    engine = _s10_native_bound_engine_readback()
    read = dict(parent=WORK, sources=Path(__file__).parent, owner_uid=0,
                engine_version=engine["engine_version"])
    old = _read_pinned_effective(detail=before["previous"], binding=old_pin, **read)
    candidate = _read_pinned_effective(detail=detail, binding=pin, **read)
    decision = _ordinary_effective_decision(old, candidate)
    semantic = OriginalSemanticReceipt(operation, before["previous"]["id"],
        pin["root_sha256"], old_pin["root_sha256"], decision, physical,
        lifecycle_proposal=_running_lifecycle_proposal(source.requested_enabled, decision))
    if (_managed_handoff_digest(semantic) != header["semantic"] or
            _managed_handoff_wire(source, semantic, raw) != line + raw or store.read() != before):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_SEMANTIC_CHANGED")
    return native_write_running_managed_file_fd9(operation, raw, source=source,
        semantic=semantic, config_fd=config_fd, config_digest=detail["base"])


def native_run_managed_apply_fd9(operation: str, raw_pipe: bytes, *,
                                 source: SourceGateReceipt, semantic: OriginalSemanticReceipt) -> dict:
    """Original prepared owner -> existing PHP writer -> exact terminal WAL.

    Private coordinator only; the public Apply switch is still gated on
    integrated first-bound promotion/recovery. Never retry an uncertain save.
    """
    from neutral_schema3_quiescent_preimage import _run_bound_restore_joined
    from shared_apply_operation import SharedApplyOperation
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    before = store.read()
    detail = _managed_handoff_scope(before, operation)
    wire = _managed_handoff_wire(source, semantic, raw_pipe)
    if (source.generation != operation or semantic.candidate_root_sha256 != before["manifest"]["root_sha256"] or
            semantic.previous_root_sha256 != before["previous_manifest"]["root_sha256"] or
            store.read() != before):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_OWNER_CHANGED")
    command = ["/usr/local/bin/php", str(Path(__file__).parent.parent / "shared_apply_config.php"),
               "managed-apply", operation, "strategies"]
    reply = _run_bound_restore_joined(command, budget=90, capture_output=True,
                                      pass_fds=(9,), input_data=wire)
    expected = {**before, "phase": "committed"}
    receipt = {"result": "saved", "saved": True, "applied": False,
               "snapshot": detail["candidate"], "change_count": len(detail["changed_fields"])}
    require_lifecycle_lock()
    if (reply.returncode != 0 or not 0 < len(reply.stdout) <= 16384 or
            _managed_handoff_json(json.loads(reply.stdout)) != _managed_handoff_json(receipt) or
            store.read() != expected):
        raise OriginalSourceGateRefused("S10_MANAGED_HANDOFF_OUTCOME_UNCERTAIN")
    return expected


def native_checkpoint_managed_config_fd9(operation: str, witness_sha256: str, *,
                                         config_fd: int, saved: bool) -> dict:
    """Original PHP owner: durable intent before save, exact commit after relock."""
    from auto_detect_destination_commit import (
        exclusive_destination_lock, _attest_bound_managed_installed_locked,
    )
    from auto_detect_gui_hostlist import AUTO_LOCK
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from neutral_schema3_previous_physical import COMMON_ACTIVE
    from shared_apply_operation import (
        SharedApplyOperation, MANAGED_WRITING, MANAGED_CONFIG_SAVING, DIGEST, _config_save_witness,
    )
    from shared_apply_seal import WORK, verify_seal
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation) or
            type(witness_sha256) is not str or not DIGEST.fullmatch(witness_sha256) or
            type(config_fd) is not int or config_fd < 3 or config_fd == 9 or type(saved) is not bool):
        raise OriginalSourceGateRefused("S10_MANAGED_CONFIG_NATIVE_SCOPE_REQUIRED")
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    record = store.read()
    phase = MANAGED_CONFIG_SAVING if saved else MANAGED_WRITING
    if (record is None or record["phase"] != phase or record["detail"]["id"] != operation or
            not {"running_sha256", "installed"} <= record["managed"].keys() or
            "restore" in record["managed"]):
        raise OriginalSourceGateRefused("S10_MANAGED_CONFIG_OWNER_REQUIRED")
    prior_release = WORK / record["previous"]["id"] / "release"

    def attest():
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        seal = verify_seal(WORK / operation, owner=0)
        if _config_save_witness(record["detail"], seal["sha256"]["plan.json"]) != witness_sha256:
            raise OriginalSourceGateRefused("S10_MANAGED_CONFIG_PLAN_CHANGED")
        _attest_bound_managed_installed_locked(store, record, parent=WORK, active=COMMON_ACTIVE)
        if saved:
            os.fsync(config_fd)
        return _native_managed_running_digest(prior_release, config_fd) == record["managed"]["running_sha256"]

    with exclusive_destination_lock(AUTO_LOCK, 0):
        return store._checkpoint_managed_config(record, saved=saved, attest=attest,
                                                shared_work_parent=WORK)


def native_begin_quiescent_bound_promotion_fd9(
        operation: str, raw_pipe: bytes) -> tuple[dict, "QuiescentPreimage"]:
    """Durable first ordinary bound checkpoint, under the existing FD9.

    Internal coordinator only: no new command or lifecycle action. A
    running predecessor (including one requiring retirement) is refused
    here. Both passes derive source and the native quiescent proof from
    the original readers, not a caller-supplied semantic receipt. Retain
    the exact preimage alongside the resulting record in the SAME in-flight
    FD9 coordinator; never reconstruct it after an interrupted promotion.
    The original physical coordinator must still implement final pre-action
    reattestation, actual promotion and recovery before calling this.
    """
    from shared_apply_operation import SharedApplyOperation
    from neutral_schema3_quiescent_preimage import QuiescentPreimage
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    try:
        require_lifecycle_lock()
        inputs = decode_pipe(raw_pipe)
        store = SharedApplyOperation(owner=0)
        before = store.read()
        if (type(before) is not dict or before["phase"] != "prepared" or
                "found" in before or "manifest" not in before or
                before["detail"]["id"] != operation):
            raise OriginalSourceGateRefused("S10_BOUND_PROMOTION_PREPARED_REQUIRED")
        digest = before["detail"]["candidate"] if inputs["mode"] == b"auto" else None

        def observe():
            if store.read() != before:
                raise OriginalSourceGateRefused("S10_BOUND_PROMOTION_OWNER_CHANGED")
            source = native_original_bound_effective_fd9(
                operation, raw_pipe, digest, bound_record=before)
            semantic = native_plan_original_prepared_fd9(source)
            if (type(semantic) is not OriginalSemanticReceipt or
                    type(semantic.previous_physical) is not QuiescentPreimage or
                    semantic.generation != operation or
                    semantic.candidate_root_sha256 != before["manifest"]["root_sha256"] or
                    semantic.lifecycle_proposal != ("START" if source.requested_enabled
                                                   else "SAVE_ONLY") or
                    semantic.previous_physical.old_state not in (
                        "first-install-empty", "committed-stopped") or
                    semantic.authorization != "NONE" or
                    semantic.physical_transition_allowed or semantic.promotion_allowed or
                    store.read() != before):
                raise OriginalSourceGateRefused("S10_BOUND_PROMOTION_QUIESCENT_REQUIRED")
            return source, semantic

        first = observe()
        record = store._advance_bound_ordinary(
            "activating", before, lambda: observe() == first)
        return record, first[1].previous_physical
    except (OSError, ValueError, RuntimeError, TypeError, KeyError):
        raise OriginalSourceGateRefused("S10_BOUND_PROMOTION_PRECHECK_REFUSED") from None


def native_run_first_enabled_apply_fd9(operation: str, raw_pipe: bytes, *,
                                       source: SourceGateReceipt,
                                       semantic: OriginalSemanticReceipt) -> dict:
    """Private first enabled Start with the original FD9/P2a/PHP Config owner."""
    from dataclasses import asdict
    from neutral_schema3_quiescent_preimage import (
        QuiescentPreimage, _run_bound_restore_joined)
    from shared_apply_operation import SharedApplyOperation, DIGEST
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    before = store.read()
    if (type(before) is not dict or before.get("phase") != "prepared" or
            before["detail"]["id"] != operation or "previous" in before or
            "previous_manifest" in before or "found" in before or
            before.get("manifest", {}).get("schema") not in (1, 2) or
            before["detail"]["base"] == before["detail"]["candidate"] or
            not before["detail"]["changed_fields"] or
            type(source) is not SourceGateReceipt or source.generation != operation or
            source.mode not in ("all", "list", "auto") or source.requested_enabled is not True or
            before["manifest"]["schema"] != (2 if source.mode == "auto" else 1) or
            source.original_seal_sha256 != before["manifest"]["seal_sha256"] or
            type(semantic) is not OriginalSemanticReceipt or
            type(semantic.previous_physical) is not QuiescentPreimage or
            semantic.previous_physical.old_state != "first-install-empty" or
            not semantic.previous_physical.verified_wan_device or
            semantic.previous_generation is not None or
            semantic.lifecycle_proposal != "START" or
            semantic.candidate_root_sha256 != before["manifest"]["root_sha256"] or
            semantic.authorization != "NONE" or semantic.physical_transition_allowed or
            semantic.promotion_allowed or not semantic.final_original_fd9_reattest_required or
            store.read() != before):
        raise OriginalSourceGateRefused("S10_FIRST_ENABLED_APPLY_SCOPE_REQUIRED")
    activating, physical = native_begin_quiescent_bound_promotion_fd9(operation, raw_pipe)
    if (physical != semantic.previous_physical or
            activating != {**before, "phase": "activating"} or store.read() != activating):
        raise OriginalSourceGateRefused("S10_FIRST_ENABLED_APPLY_PREIMAGE_CHANGED")
    wire = (json.dumps(asdict(physical), sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    if len(wire) > 4096:
        raise OriginalSourceGateRefused("S10_FIRST_ENABLED_APPLY_WIRE_TOO_LARGE")
    command = ["/usr/local/bin/php", str(Path(__file__).parent.parent / "shared_apply_config.php"),
               "first-enabled-apply", operation, before["detail"]["page"]]
    learning = before["manifest"]["schema"] == 2
    if learning:
        from auto_detect_post_drop import (_learning_release_sources, _qualified_learning_sources,
            native_prepare_learning_producer, _original_epoch_queue, _capture,
            _learning_pretraffic_owner)
        from auto_detect_storage import ROOT, ENGINE_USER
        from neutral_schema3_quiescent_preimage import _safe_empty_directory, EPOCH_ROOT
        import pwd
        from shared_apply_seal import WORK
        from neutral_root_stage import verify_original_operation_pins
        work = WORK / operation
        release = work / "release"
        workspace, candidate, sources = _learning_release_sources(release)
        if (workspace != work or candidate != before["detail"]["candidate"] or
                store.read() != activating):
            raise OriginalSourceGateRefused("S10_FIRST_LEARNING_SOURCE_CHANGED")
        verify_original_operation_pins(record=activating, parent=WORK, owner_uid=0)
        _safe_empty_directory(ROOT, 0)
        _safe_empty_directory(EPOCH_ROOT, 0)
        # Durable ACTIVATING precedes producer creation; no Config lock yet.
        native_prepare_learning_producer(release)
        _, names = _qualified_learning_sources(sources, ROOT)
        queue, _ = _original_epoch_queue(names)
        identity = pwd.getpwnam(ENGINE_USER)
        # The first lock may need creation. Keep the one real OFD held
        # continuously across the joined PHP/physical/confirmation children.
        with queue.exclusive():
            fd = queue.locked_fd
            if (_learning_pretraffic_owner(work, candidate, fd) != activating or
                    _learning_release_sources(release) != (workspace, candidate, sources)):
                raise OriginalSourceGateRefused("S10_FIRST_LEARNING_QUEUE_OWNER_CHANGED")
            _capture(ROOT, root_uid=0, root_gid=0, engine_uid=identity.pw_uid,
                     engine_gid=identity.pw_gid, learning_names=names, queue_fd=fd)
            _safe_empty_directory(EPOCH_ROOT, 0)
            reply = _run_bound_restore_joined(command + [f"--queue-fd={fd}"],
                pass_fds=(9, fd), budget=120, capture_output=True, input_data=wire)
    else:
        reply = _run_bound_restore_joined(command, pass_fds=(9,), budget=120,
                                          capture_output=True, input_data=wire)
    receipt = {"result": "saved", "saved": True, "applied": False,
               "snapshot": before["detail"]["candidate"],
               "change_count": len(before["detail"]["changed_fields"])}
    require_lifecycle_lock()
    committed = {**activating, "phase": "committed"}
    saved = store.read()
    pins = {"first_running_sha256", "first_pretraffic_sha256"} if learning else {"first_running_sha256"}
    if (reply.returncode != 0 or type(reply.stdout) is not bytes or
            not 0 < len(reply.stdout) <= 4096 or reply.stdout.count(b"\n") != 1 or
            not reply.stdout.endswith(b"\n") or
            _managed_handoff_json(json.loads(reply.stdout)) != _managed_handoff_json(receipt) or
            type(saved) is not dict or
            {k: v for k, v in saved.items() if k not in pins} != committed or
            any(type(saved.get(pin)) is not str or not DIGEST.fullmatch(saved[pin])
                for pin in pins)):
        raise OriginalSourceGateRefused("S10_FIRST_ENABLED_APPLY_OUTCOME_UNCERTAIN")
    return saved


def native_run_first_disabled_apply_fd9(operation: str, raw_pipe: bytes, *,
                                        source: SourceGateReceipt,
                                        semantic: OriginalSemanticReceipt) -> dict:
    """Private original FD9 coordinator; Config writer remains original PHP."""
    from dataclasses import asdict
    from neutral_schema3_quiescent_preimage import (
        QuiescentPreimage, _run_bound_restore_joined)
    from shared_apply_operation import SharedApplyOperation
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    before = store.read()
    if (type(before) is not dict or before.get("phase") != "prepared" or
            before["detail"]["id"] != operation or "previous" in before or
            "previous_manifest" in before or "found" in before or
            before.get("manifest", {}).get("schema") != 1 or
            before["detail"]["base"] == before["detail"]["candidate"] or
            not before["detail"]["changed_fields"] or
            type(source) is not SourceGateReceipt or source.generation != operation or
            source.mode not in ("all", "list") or source.requested_enabled is not False or
            source.original_seal_sha256 != before["manifest"]["seal_sha256"] or
            type(semantic) is not OriginalSemanticReceipt or
            type(semantic.previous_physical) is not QuiescentPreimage or
            semantic.previous_physical.old_state != "first-install-empty" or
            semantic.previous_generation is not None or
            semantic.lifecycle_proposal != "SAVE_ONLY" or
            semantic.candidate_root_sha256 != before["manifest"]["root_sha256"] or
            semantic.authorization != "NONE" or semantic.physical_transition_allowed or
            semantic.promotion_allowed or not semantic.final_original_fd9_reattest_required or
            store.read() != before):
        raise OriginalSourceGateRefused("S10_FIRST_DISABLED_APPLY_SCOPE_REQUIRED")
    activated, physical = native_begin_quiescent_bound_promotion_fd9(operation, raw_pipe)
    if (physical != semantic.previous_physical or
            activated != {**before, "phase": "activating"} or store.read() != activated):
        raise OriginalSourceGateRefused("S10_FIRST_DISABLED_APPLY_PREIMAGE_CHANGED")
    wire = (json.dumps(asdict(physical), sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    if len(wire) > 4096:
        raise OriginalSourceGateRefused("S10_FIRST_DISABLED_APPLY_WIRE_TOO_LARGE")
    command = ["/usr/local/bin/php", str(Path(__file__).parent.parent / "shared_apply_config.php"),
               "first-disabled-apply", operation, before["detail"]["page"]]
    reply = _run_bound_restore_joined(command, pass_fds=(9,), budget=90,
                                      capture_output=True, input_data=wire)
    receipt = {"result": "saved", "saved": True, "applied": False,
               "snapshot": before["detail"]["candidate"],
               "change_count": len(before["detail"]["changed_fields"])}
    require_lifecycle_lock()
    committed = {**activated, "phase": "committed"}
    if (reply.returncode != 0 or type(reply.stdout) is not bytes or
            not 0 < len(reply.stdout) <= 4096 or reply.stdout.count(b"\n") != 1 or
            not reply.stdout.endswith(b"\n") or
            _managed_handoff_json(json.loads(reply.stdout)) != _managed_handoff_json(receipt) or
            store.read() != committed):
        raise OriginalSourceGateRefused("S10_FIRST_DISABLED_APPLY_OUTCOME_UNCERTAIN")
    return committed


def native_coordinate_original_prepared_fd9(operation: str, raw_pipe: bytes) -> tuple:
    """One original PREPARED selection; only the qualified managed route acts.

    Retain the actual source and semantic witnesses for the in-flight caller.
    Unsupported paths remain bound PREPARED, never fall through to legacy or
    advance ACTIVATING before the physical executor is available.
    """
    from shared_apply_operation import SharedApplyOperation
    from neutral_schema3_previous_physical import CompletePriorPreimage
    from neutral_schema3_quiescent_preimage import QuiescentPreimage
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    require_lifecycle_lock()
    inputs = decode_pipe(raw_pipe)
    store = SharedApplyOperation(owner=0)
    before = store.read()
    if (type(before) is not dict or before.get("phase") != "prepared" or
            "found" in before or before["detail"]["id"] != operation):
        raise OriginalSourceGateRefused("S10_PREPARED_DISPATCH_OWNER_REQUIRED")
    if "manifest" not in before:
        source, _ = native_bind_original_prepared_fd9(operation, raw_pipe)
        bound = store.read()
        if (type(bound) is not dict or "manifest" not in bound or
                {k: v for k, v in bound.items() if k != "manifest"} != before):
            raise OriginalSourceGateRefused("S10_PREPARED_DISPATCH_BIND_CHANGED")
    else:
        bound = before
        digest = bound["detail"]["candidate"] if inputs["mode"] == b"auto" else None
        source = native_original_bound_effective_fd9(operation, raw_pipe, digest,
                                                     bound_record=bound)
    semantic = native_plan_original_prepared_fd9(source)
    if (type(source) is not SourceGateReceipt or type(semantic) is not OriginalSemanticReceipt or
            source.generation != operation or semantic.generation != operation or
            source.original_seal_sha256 != bound["manifest"]["seal_sha256"] or
            source.mode != inputs["mode"].decode("ascii") or
            type(semantic.previous_physical) not in (CompletePriorPreimage, QuiescentPreimage) or
            semantic.candidate_root_sha256 != bound["manifest"]["root_sha256"] or
            semantic.previous_generation != bound.get("previous", {}).get("id") or
            semantic.previous_root_sha256 != bound.get("previous_manifest", {}).get("root_sha256") or
            semantic.authorization != "NONE" or semantic.physical_transition_allowed or
            semantic.promotion_allowed or not semantic.final_original_fd9_reattest_required or
            store.read() != bound):
        raise OriginalSourceGateRefused("S10_PREPARED_DISPATCH_WITNESS_CHANGED")
    if (type(semantic.previous_physical) is CompletePriorPreimage and
            semantic.lifecycle_proposal == "RELOAD" and
            semantic.decision.kind == "RELOAD_SAFE_CANDIDATE" and
            len(semantic.decision.changed_active) == 1 and not semantic.decision.changed_inactive and
            source.requested_enabled is True and inputs["mode"] in (b"all", b"list") and
            bound["manifest"]["schema"] == 1 and bound.get("previous_manifest", {}).get("schema") == 1 and
            bound["detail"]["page"] == "strategies" and
            bound["detail"]["base"] != bound["detail"]["candidate"] and bound["detail"]["changed_fields"]):
        # No catch/retry/fallback: an uncertain Config save belongs to the
        # original managed WAL recovery, not to another lifecycle proposal.
        result = native_run_managed_apply_fd9(operation, raw_pipe, source=source, semantic=semantic)
        require_lifecycle_lock()
        if result != {**bound, "phase": "committed"} or store.read() != result:
            raise OriginalSourceGateRefused("S10_PREPARED_DISPATCH_OUTCOME_UNCERTAIN")
        return "managed-committed", result, source, semantic
    if (type(semantic.previous_physical) is QuiescentPreimage and
            semantic.previous_physical.old_state == "first-install-empty" and
            semantic.lifecycle_proposal == "START" and source.requested_enabled is True and
            inputs["mode"] in (b"all", b"list", b"auto") and
            bound["manifest"]["schema"] == (2 if inputs["mode"] == b"auto" else 1) and
            "previous" not in bound and "previous_manifest" not in bound and
            bound["detail"]["base"] != bound["detail"]["candidate"] and
            bound["detail"]["changed_fields"]):
        result = native_run_first_enabled_apply_fd9(operation, raw_pipe,
                                                    source=source, semantic=semantic)
        expected = {**bound, "phase": "committed"}
        pins = ({"first_running_sha256", "first_pretraffic_sha256"}
                if inputs["mode"] == b"auto" else {"first_running_sha256"})
        if (type(result) is not dict or
                {k: v for k, v in result.items() if k not in pins} != expected or
                any(type(result.get(pin)) is not str or
                    not re.fullmatch(r"[a-f0-9]{64}", result[pin]) for pin in pins) or
                store.read() != result):
            raise OriginalSourceGateRefused("S10_FIRST_ENABLED_APPLY_OUTCOME_UNCERTAIN")
        return "first-enabled-committed", result, source, semantic
    if (type(semantic.previous_physical) is QuiescentPreimage and
            semantic.previous_physical.old_state == "first-install-empty" and
            semantic.lifecycle_proposal == "SAVE_ONLY" and source.requested_enabled is False and
            inputs["mode"] in (b"all", b"list") and bound["manifest"]["schema"] == 1 and
            "previous" not in bound and "previous_manifest" not in bound and
            bound["detail"]["base"] != bound["detail"]["candidate"] and
            bound["detail"]["changed_fields"]):
        result = native_run_first_disabled_apply_fd9(operation, raw_pipe,
                                                     source=source, semantic=semantic)
        if result != {**bound, "phase": "committed"} or store.read() != result:
            raise OriginalSourceGateRefused("S10_FIRST_DISABLED_APPLY_OUTCOME_UNCERTAIN")
        return "first-disabled-committed", result, source, semantic
    route = ("quiescent-executor-required" if type(semantic.previous_physical) is QuiescentPreimage
             else "lifecycle-executor-required")
    require_lifecycle_lock()
    if store.read() != bound:
        raise OriginalSourceGateRefused("S10_PREPARED_DISPATCH_WITNESS_CHANGED")
    return route, bound, source, semantic


def native_first_auto_gui_handoff_fd9(operation: str, raw_pipe: bytes,
                                      candidate: str) -> None:
    """Narrow original combined Apply child: first enabled Auto only.

    The shell has durably prepared the ONE original journal. Re-attest
    the exact source and scope before binding; no generic CLI dispatch,
    no fallback and no new lock or Config writer.
    """
    from shared_apply_operation import SharedApplyOperation, DIGEST
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation) or
            type(candidate) is not str or not DIGEST.fullmatch(candidate)):
        raise OriginalSourceGateRefused("S10_FIRST_AUTO_GUI_NATIVE_REQUIRED")
    require_lifecycle_lock()
    if decode_pipe(raw_pipe)["mode"] != b"auto":
        raise OriginalSourceGateRefused("S10_FIRST_AUTO_GUI_SCOPE_REQUIRED")
    store = SharedApplyOperation(owner=0)
    before = store.read()
    if (type(before) is not dict or before.get("phase") != "prepared" or
            any(key in before for key in ("previous", "previous_manifest", "manifest", "found")) or
            before["detail"]["id"] != operation or before["detail"]["page"] != "strategies" or
            before["detail"]["candidate"] != candidate or before["detail"]["base"] == candidate or
            "general.enabled" not in before["detail"]["changed_fields"]):
        raise OriginalSourceGateRefused("S10_FIRST_AUTO_GUI_SCOPE_REQUIRED")
    source = native_original_bound_effective_fd9(operation, raw_pipe, candidate)
    if (type(source) is not SourceGateReceipt or source.mode != "auto" or
            source.requested_enabled is not True or source.generation != operation or
            store.read() != before):
        raise OriginalSourceGateRefused("S10_FIRST_AUTO_GUI_SCOPE_REQUIRED")
    route, result, actual, semantic = native_coordinate_original_prepared_fd9(operation, raw_pipe)
    require_lifecycle_lock()
    if (route != "first-enabled-committed" or actual != source or
            type(result) is not dict or result.get("phase") != "committed" or
            result.get("manifest", {}).get("schema") != 2 or
            result.get("detail") != before["detail"] or
            any(type(result.get(key)) is not str or not DIGEST.fullmatch(result[key])
                for key in ("first_running_sha256", "first_pretraffic_sha256")) or
            store.read() != result):
        raise OriginalSourceGateRefused("S10_FIRST_AUTO_GUI_OUTCOME_UNCERTAIN")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--first-auto-apply" in args:
        if len(args) != 3 or args[-1] != "--first-auto-apply":
            return 64
        try:
            raw = sys.stdin.buffer.read(MAX_PIPE + 1)
            native_first_auto_gui_handoff_fd9(args[0], raw, args[1])
            return 0
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, IndexError) as error:
            # The original PREPARED or later WAL remains the authority.
            # Never expose arbitrary exception text or return a preflight
            # refusal after recording the original intent.
            reason = str(error) if type(error) is OriginalSourceGateRefused else ""
            safe = {
                "S10_FIRST_AUTO_GUI_NATIVE_REQUIRED",
                "S10_FIRST_AUTO_GUI_SCOPE_REQUIRED",
                "S10_FIRST_AUTO_GUI_OUTCOME_UNCERTAIN",
                "S10_FIRST_ENABLED_APPLY_SCOPE_REQUIRED",
                "S10_FIRST_ENABLED_APPLY_PREIMAGE_CHANGED",
                "S10_FIRST_ENABLED_APPLY_OUTCOME_UNCERTAIN",
                "S10_FIRST_LEARNING_SOURCE_CHANGED",
                "S10_FIRST_LEARNING_QUEUE_OWNER_CHANGED",
                "S10_BOUND_ENGINE_UNQUALIFIED",
                "S10_BOUND_ENGINE_CHANGED",
                "S10_EFFECTIVE_SOURCE_UNQUALIFIED",
                "S10_ORIGINAL_PREPARED_REQUIRED",
                "S10_BOUND_PROMOTION_PRECHECK_REFUSED",
                "S10_PREPARED_DISPATCH_WITNESS_CHANGED",
                "S10_PREPARED_DISPATCH_BIND_CHANGED",
            }
            # Narrow finite diagnostics for the actual root-binding path.
            # All other exceptions remain classified by their fixed type.
            from neutral_root_stage import RootStageRefused
            from neutral_schema3_physical_refs import PhysicalSchema3Refused
            from neutral_root_bound_preflight import BoundRootRefused
            from neutral_schema3_saved_wan_preimage import SavedWanPreimageRefused
            from neutral_schema3_quiescent_preimage import QuiescentPreimageRefused
            fixed = {
                RootStageRefused: {"ORIGINAL_TYPED_SEALED_SOURCE_REQUIRED",
                    "ORIGINAL_PREPARED_SOURCE_IDENTITY_MISMATCH",
                    "ORIGINAL_AUTO_CANDIDATE_IDENTITY_MISMATCH",
                    "ORIGINAL_PREPARED_SOURCE_ROOT_UNQUALIFIED",
                    "ORIGINAL_SEALED_REFS_UNQUALIFIED", "STAGED_ROOT_UNQUALIFIED",
                    "ORIGINAL_STAGE_FILESYSTEM_REFUSED"},
                PhysicalSchema3Refused: {"ORIGINAL_SCHEMA3_PHYSICAL_UNQUALIFIED"},
                BoundRootRefused: {"ORIGINAL_BOUND_ROOT_UNQUALIFIED"},
                SavedWanPreimageRefused: {"ORIGINAL_CONFIG_PREIMAGE_MISMATCH",
                    "NATIVE_ORIGINAL_PROBE_REFUSED", "NATIVE_ORIGINAL_PROBE_UNAVAILABLE"},
                QuiescentPreimageRefused: {"ORIGINAL_QUIESCENT_PREIMAGE_REFUSED",
                    "FIRST_LEARNING_WAN_SOURCE_CHANGED", "FIRST_LEARNING_WAN_RESOLVER_REFUSED"},
            }
            if reason not in safe:
                reason = (str(error) if str(error) in fixed.get(type(error), set())
                          else _fixed_unclassified_reason(error))
            print("ORIGINAL_SOURCE_GATE_REFUSAL=" + reason, file=sys.stderr)
            return 70
    # Legacy original parity requests retain their exact old protocol.
    # Explicit S10 accepts only an exact sealed source, never a free-form
    # version argument or an unsealed/legacy-effective fallback.
    s10 = bool(args) and args[-1] == "--s10-effective"
    if "--s10-effective" in args and not s10:
        return 64
    if s10:
        if (len(args) not in (3, 4) or args[-2] != "--sealed"):
            return 64
        digest = args[1] if len(args) == 4 else None
        sealed = True
    else:
        if (len(args) not in (1, 2, 3) or
                (len(args) == 3 and args[2] != "--sealed")):
            return 64
        sealed = args[-1] == "--sealed"
        digest = args[1] if len(args) >= 2 and args[1] != "--sealed" else None
    try:
        raw = sys.stdin.buffer.read(MAX_PIPE + 1)
        if s10:
            result = native_original_bound_effective_fd9(args[0], raw, digest)
            # No native argv, Config, hostlists, WAN or file paths in stdout.
            # A digest-only observation is NOT an activation permit.
            print("S10_ORIGINAL_EFFECTIVE_INPUT_READ_ONLY=" +
                  result.effective.structural_sha256)
        else:
            native_original_fd9(args[0], raw, digest, sealed=sealed)
        return 0
    except (ValueError, RuntimeError, OSError, TypeError, UnicodeError,
            KeyError, IndexError, json.JSONDecodeError) as error:
        # The only diagnostic is a fixed, source-code-owned error identifier.
        # NEVER serialize exception details, source fields, user lists or paths.
        reason = (str(error) if type(error) in (
            OriginalSourceGateRefused, ConfigModelError, TargetCompileError,
            ResourceCompileError, NativeParityRefused) else "")
        approved = {
            "INVALID_ORIGINAL_PIPE",
            "INVALID_ORIGINAL_FIELDS",
            "INVALID_ORIGINAL_FIELD_SIZE",
            "INVALID_ORIGINAL_SOURCE_SELECTOR",
            "UNTRUSTED_ORIGINAL_FILE",
            "ORIGINAL_FILE_CHANGED",
            "UNQUALIFIED_ORIGINAL_CONTEXT",
            "PREMATURE_OR_SECOND_ROOT_FORBIDDEN",
            "ORIGINAL_CONFIG_SOURCE_DRIFT",
            "ORIGINAL_STRATEGY_SOURCE_DRIFT",
            "ORIGINAL_REGISTRY_SOURCE_DRIFT",
            "ORIGINAL_STORAGE_SOURCE_DRIFT",
            "ORIGINAL_MANAGED_SOURCE_SET_DRIFT",
            "UNEXPECTED_ORIGINAL_PROMOTION",
            "NONAUTO_OLD_ARGS_FORBIDDEN",
            "UNFINISHED_ORIGINAL_PROMOTION",
            "ORIGINAL_NATIVE_CANDIDATE_DIGEST_REQUIRED",
            "ORIGINAL_NONAUTO_MAP_OR_DIGEST_FORBIDDEN",
            "ORIGINAL_NATIVE_PROOF_NOT_READONLY",
            "FINAL_ORIGINAL_NATIVE_REFS_MISMATCH",
            "ORIGINAL_NATIVE_ARTIFACT_CHANGED",
            "ORIGINAL_INPUT_CHANGED_DURING_CHECK",
            "EFFECTIVE_SOURCE_REQUIRES_FINAL_SEAL",
            "FINAL_ORIGINAL_SEAL_CHANGED",
            "INVALID_ORIGINAL_PLAN",
            "INCOMPLETE_ORIGINAL_FOUND_PLAN",
            "INVALID_ORIGINAL_FOUND_INTENT",
            "NATIVE_ORIGINAL_FD9_REQUIRED",
            "S10_BOUND_ENGINE_UNQUALIFIED",
            "S10_BOUND_ENGINE_CHANGED",
            "S10_EFFECTIVE_SOURCE_UNQUALIFIED",
            "P1_OWNER_PRESENT_BUT_GUI_LOCK_ABSENT",
        }
        approved.update({
            "INVALID_MODEL_SECTION",
            "INVALID_MODEL_SCALAR",
            "INVALID_BOOLEAN",
            "INVALID_ENUM",
            "INVALID_PORT",
            "INVALID_MODEL_KEYS",
            "INVALID_VOICE_KEYS",
            "INVALID_REGISTRY",
            "INVALID_WAN_SELECTION",
            "INVALID_PORTS",
            "INVALID_ORIGINAL_POLICY",
            "ORIGINAL_POLICY_SOURCE_CHANGED",
            "ORIGINAL_POLICY_BRANCHES_CHANGED",
            "ORIGINAL_POLICY_DECLARATION_CHANGED",
            "INVALID_ORIGINAL_POLICY_ROWS",
            "UNQUALIFIED_TARGET_INPUT",
            "INVALID_TARGET_REGISTRY",
            "UNQUALIFIED_TARGET_POLICY",
            "INVALID_TARGET_DEFAULTS",
            "UNREGISTERED_OR_IMPLICIT_AUTO_DEFAULT",
            "ALL_MODE_MUST_NOT_INJECT_TARGETS",
            "UNSUPPORTED_EXPLICIT_TARGET",
            "UNREGISTERED_EXPLICIT_TARGET",
            "TOO_MANY_NORMALIZED_PROFILES",
            "INVALID_ORIGINAL_PROFILE",
            "INVALID_STORAGE_SOURCE",
            "STORAGE_SOURCE_CHANGED",
            "STORAGE_DECLARATION_CHANGED",
            "INVALID_STORAGE_LOCATOR",
            "INVALID_STORAGE_CATALOG",
            "INVALID_DOMAIN_INPUT",
            "INVALID_IPSET_INPUT",
            "INCOMPLETE_OWNED_KNOWN_SNAPSHOT",
            "INVALID_OWNED_KNOWN_SNAPSHOT",
            "NONCANONICAL_OWNED_KNOWN",
            "UNQUALIFIED_RESOURCE_PREVIEW",
            "INVALID_RESOURCE_REGISTRY",
            "REGISTRY_STORAGE_MISMATCH",
            "INCOMPLETE_PREPARED_RESOURCES",
            "INVALID_PREPARED_BYTES",
            "INVALID_SAVED_VOICE",
            "INVALID_TARGET_PROFILES",
            "INVALID_RESOURCE_TYPE",
            "UNKNOWN_LINKED_SOURCE",
            "INVALID_EFFECTIVE_KNOWN",
            "UNQUALIFIED_STORAGE_REFERENCE",
            "UNQUALIFIED_RUNTIME_RESOURCE",
            "UNPREPARED_MANAGED_RESOURCE",
            "LINKED_RESOURCE_NOT_PRESENT",
            "LINKED_RESOURCE_EMPTY",
            "VOICE_REQUIRES_SAVED_WAN",
            "VOICE_CANDIDATE_INVALID",
            "UNQUALIFIED_MANAGED_PARITY",
            "MANAGED_REFERENCE_MISMATCH",
            "MANAGED_EXPECTATION_MISSING",
            "INVALID_EXCLUSION_EXPECTATION",
            "ORIGINAL_MANAGED_SET_MISMATCH",
            "ORIGINAL_MANAGED_BYTES_MISMATCH",
            "UNQUALIFIED_ORIGINAL_INPUT",
            "ORIGINAL_NATIVE_ARGS_INVALID",
            "UNEXPECTED_ORIGINAL_NATIVE_ARGS",
            "VOICE_ORIGINAL_ARTIFACT_MISMATCH",
            "NATIVE_CAPTURE_PLAN_REFUSED",
            "NATIVE_CAPTURE_PLAN_CHANGED",
            "NATIVE_VOICE_ORDER_CHANGED",
            "NATIVE_VOICE_SHA_CHANGED",
            "ORDINARY_IPFW_RANGE_CHANGED",
            "UNQUALIFIED_LINKED_RESOURCES",
            "UNEXPECTED_NONAUTO_SOURCE_MAP",
            "LEARNING_NOT_ALLOWED_IN_NONAUTO",
            "INVALID_ORIGINAL_SOURCE_MAP",
            "ORIGINAL_PROFILE_MAP_COUNT",
            "ORIGINAL_VOICE_OR_STRATEGY_MAP_COUNT",
            "ORIGINAL_SOURCE_PROFILE_IDENTITY_CHANGED",
            "ORIGINAL_LEARNING_PROOF_REFUSED",
            "UNQUALIFIED_FIRST_MATCH_OR_LEARNING_ORDER",
        })
        if reason not in approved:
            reason = _fixed_unclassified_reason(error)
        print("ORIGINAL_SOURCE_GATE_REFUSAL=" + reason, file=sys.stderr)
        return 69


if __name__ == "__main__":
    # The original root compiler imports SourceGateReceipt from this
    # canonical module. Executing its classes as __main__ would create a
    # distinct Python type and fail the deliberately exact type check.
    # Run the existing CLI in the canonical module namespace instead.
    from neutral_shared_apply_source_gate import main as _canonical_main
    raise SystemExit(_canonical_main())
