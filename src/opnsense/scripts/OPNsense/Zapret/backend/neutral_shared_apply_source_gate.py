#!/usr/bin/env python3
"""S10c2b3a: original FD9 preseal and final sealed source/native witnesses.

The existing shared_apply_prepare_service is the only installed caller.
This module never creates a Config writer, journal, release, PID, or IPFW
operation. Pure compilation is NOT an authorization to activate. The original
FD9 owner must re-attest its seal, P1 and previous runtime at physical commit.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
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


def qualify_source_to_managed(*, work: Path, sources: Path,
                              inputs: dict[str, bytes],
                              owned_known: dict[str, bytes] | None,
                              runtime_auto: bytes | None = None,
                              candidate_sha256: str | None = None,
                              owner_uid: int = 0,
                              active_managed: Path = Path(
                                  "/usr/local/etc/zapret2/runtime-v2/managed"),
                              sealed: bool = False,
                              engine_version: str | None = None) -> SourceGateReceipt:
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
        for root in (work / "manifest.json", work / ".manifest.json.pending",
                     release / "manifest.json", release / ".manifest.json.pending"):
            if root.exists() or root.is_symlink():
                raise OriginalSourceGateRefused("PREMATURE_OR_SECOND_ROOT_FORBIDDEN")
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
                        engine_version: str | None = None) -> SourceGateReceipt:
    """Only the installed original FD9 wrapper can invoke this native action."""
    from voice_ipfw_adapter import require_lifecycle_lock
    from shared_apply_seal import WORK
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    require_lifecycle_lock()
    inputs = decode_pipe(raw_pipe)
    work = WORK / operation
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
        engine_version=engine_version)
    require_lifecycle_lock()
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
        candidate_sha256: str | None = None) -> SourceGateReceipt:
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
        engine_version=bound["engine_version"])
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
    # The original template's heredoc is loaded by shell command
    # substitution; it strips trailing LF. The original builder then
    # writes one LF. The portable original loader can preserve trailing LF.
    # Permit ONLY that insignificant trailing-LF difference from the sealed
    # model; never trust unsealed traffic.input as independent provenance.
    strategy = model["strategy"].get("trafficargs")
    if type(strategy) is not str:
        raise OriginalSourceGateRefused("S10_PINNED_STRATEGY_MISSING")
    traffic = _read(work / "traffic.input", owner_uid, 262145)
    if (not traffic.endswith(b"\n") or
            traffic.rstrip(b"\n") != strategy.encode("utf-8").rstrip(b"\n")):
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
                          "inert-no-producer-data"))) or
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
        decision = (EffectiveDecision("RESTART_REQUIRED", (), ())
                    if old is None else plan(old[0], candidate[0]))
        if lifecycle is None:
            # Physical state (RUNNING) dominates OFF even if equal S08d.
            lifecycle = ("STOP" if source.requested_enabled is False else {
                "NO_CHANGE": "NO_CHANGE",
                "SAVE_ONLY": "SAVE_ONLY",
                "RELOAD_SAFE_CANDIDATE": "RELOAD",
                "RESTART_REQUIRED": "RESTART",
            }[decision.kind])
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

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
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
    raise SystemExit(main())
