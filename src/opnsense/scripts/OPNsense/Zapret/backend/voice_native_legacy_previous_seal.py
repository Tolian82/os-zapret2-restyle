#!/usr/bin/env python3
"""Stage 3 import-only: durable previous legacy PoC files, marker and IPFW witness.

NO configd, GUI, CLI, boot or service dispatch. This refuses to authorize
migration: old rule/table ownership and rollback execution
still require a separate atomic, reviewed cutover contract. The caller MUST
hold original FD9 plus the original Config inode flock throughout.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from voice_cutover_backup import (
    _private_dir, _read_private_file, _sync_dir, capture_previous,
    bound_resource_fingerprints,
)
from voice_firewall_ledger import fingerprint
from voice_native_legacy_poc_guard import _legacy_read
from voice_native_legacy_live_preflight import (
    inspect_running_legacy_poc, _old_poc_snapshot,
)
from voice_native_live_ipfw import observe_legacy_poc_ipfw
from voice_native_live_preflight import _current_engine_args, _instances
from voice_native_kernel_argv import SYSTEM_PATHS
from voice_native_recovery_quiescence import _locked_config
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_process_recovery_evidence import capture_process_evidence, inspect_process_evidence
from voice_security_policy_evidence import (
    SUPERVISOR_BOUND_POLICY_SCHEMA, capture_security_policy,
    inspect_security_policy, verify_current_security,
)

NAME = "legacy-previous"
SCHEMA = 2
LIMIT = 1048576
FILES = frozenset(("previous", "marker.bin", "legacy.json", "legacy.sha256",
                   "process-evidence", "process-security-policy"))


class LegacyPreviousSealError(RuntimeError):
    pass


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if os.write(fd, data) != len(data):
            raise LegacyPreviousSealError("short previous evidence write")
        os.fsync(fd)
    finally:
        os.close(fd)


def inspect_legacy_previous(root: Path) -> dict:
    """Read fsynced immutable evidence strictly; a digest is NOT ownership."""
    root = Path(root)
    _private_dir(root)
    archive = root / NAME
    _private_dir(archive)
    if set(os.listdir(archive)) != FILES:
        raise LegacyPreviousSealError("missing or foreign previous PoC artifact")
    body = _read_private_file(archive / "legacy.json", LIMIT)
    checksum = _read_private_file(archive / "legacy.sha256", 65)
    if checksum != (_digest(body) + "\n").encode("ascii"):
        raise LegacyPreviousSealError("previous PoC manifest seal mismatch")
    record = json.loads(body)
    if not isinstance(record, dict) or set(record) != {
        "schema", "previous", "marker", "legacy_ipfw_previous",
        "legacy_ipfw_structure_sha256", "managed_ipv4_sha256",
        "active_argument_sha256", "process_instances", "phase",
        "previous_five", "process_security_policy_sha256",
    } or type(record["schema"]) is not int or record["schema"] != SCHEMA or (
        record["phase"] != "previous-evidence-only-not-owned"
    ):
        raise LegacyPreviousSealError("untrusted legacy PoC manifest schema")
    if record["previous"] != bound_resource_fingerprints(archive / "previous"):
        raise LegacyPreviousSealError("saved previous Config/runtime mismatch")
    m = record["marker"]
    if not isinstance(m, dict) or set(m) != {"mode", "sha256", "bytes"} or (
        type(m["mode"]) is not int or not 0 <= m["mode"] <= 0o777
        or type(m["bytes"]) is not int or not 0 <= m["bytes"] <= 64
    ):
        raise LegacyPreviousSealError("invalid saved transient PoC marker")
    marker = _read_private_file(archive / "marker.bin", 64)
    if len(marker) != m["bytes"] or _digest(marker) != m["sha256"]:
        raise LegacyPreviousSealError("saved Telegram marker bytes are corrupt")
    if fingerprint(record["legacy_ipfw_previous"]) != (
        record["legacy_ipfw_structure_sha256"]
    ):
        raise LegacyPreviousSealError("legacy PoC IPFW witness mismatch")
    for field in ("managed_ipv4_sha256", "active_argument_sha256"):
        value = record[field]
        if not isinstance(value, str) or len(value) != 64 or (
            any(ch not in "0123456789abcdef" for ch in value)
        ):
            raise LegacyPreviousSealError("invalid previous PoC source hash")
    if not isinstance(record["process_instances"], dict) or (
        set(record["process_instances"]) != {"engine", "daemon", "monitor"}
    ):
        raise LegacyPreviousSealError("missing previous PoC process epochs")
    process = inspect_process_evidence(
        archive / "process-evidence", archive / "previous", EXPECTED_SCRIPTS,
        record["previous_five"],
    )
    if record["previous_five"] != {
        **record["previous"], **process["previous"],
        "firewall": record["legacy_ipfw_structure_sha256"],
    }:
        raise LegacyPreviousSealError("previous PoC five-domain binding mismatch")
    observed = process["observation"]
    identities = {
        "engine": observed["engine"]["process"],
        "daemon": observed["supervisor"]["daemon"],
        "monitor": observed["supervisor"]["monitor"],
    }
    if any(record["process_instances"].get(role) != {
        "pid": row["pid"], "start_ns": row["start_ns"],
    } for role, row in identities.items()):
        raise LegacyPreviousSealError("old PoC PID/start differs from process evidence")
    policy = inspect_security_policy(
        archive / "process-security-policy",
        archive / "previous", archive / "process-evidence",
        expected_scripts=EXPECTED_SCRIPTS,
    )
    if policy["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA or (
        policy["policy_sha256"] != record["process_security_policy_sha256"]
        or policy["policy"]["previous"] != record["previous_five"]
    ):
        raise LegacyPreviousSealError("previous PoC process security policy mismatch")
    return {
        "state": "legacy-poc-previous-five-domains-sealed-not-owned",
        "legacy_ipfw_structure_sha256": record["legacy_ipfw_structure_sha256"],
        "previous": record["previous"],
        "marker_bytes": len(marker),
        "process_security_sealed": True,
        "process_security_policy_sha256": policy["policy_sha256"],
        "previous_five": record["previous_five"],
        "rollback_implemented": False,
        "safe_to_mutate": False,
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }


def inspect_legacy_previous_live_identity(root: Path) -> dict:
    """Extract the exact old live witness from an independently VERIFIED seal.

    The public previous inspector intentionally returns a smaller safe summary,
    not the PID/argv/IPFW payload. The shared legacy begin/cancel route needs
    the complete recorded identity to compare it with the LIVE owner. Never
    treat an unverified legacy.json as an old-owner authorization.
    """
    root = Path(root)
    before = inspect_legacy_previous(root)
    archive = root / NAME
    body = _read_private_file(archive / "legacy.json", LIMIT)
    checksum = _read_private_file(archive / "legacy.sha256", 65)
    if checksum != (_digest(body) + "\n").encode("ascii"):
        raise LegacyPreviousSealError("old live identity lost its manifest seal")
    record = json.loads(body)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA or (
        record.get("previous") != before["previous"]
        or record.get("previous_five") != before["previous_five"]
        or record.get("legacy_ipfw_structure_sha256") !=
            before["legacy_ipfw_structure_sha256"]
        or record.get("process_security_policy_sha256") !=
            before["process_security_policy_sha256"]
    ):
        raise LegacyPreviousSealError("old live identity is not the sealed previous-five")
    # Validate the exact CURRENT bytes again: a swapped manifest must never
    # yield an identity that was not inspected and bound to the old files.
    if inspect_legacy_previous(root) != before:
        raise LegacyPreviousSealError("previous PoC changed during identity inspection")
    fields = (
        "marker", "legacy_ipfw_previous", "legacy_ipfw_structure_sha256",
        "managed_ipv4_sha256", "active_argument_sha256", "process_instances",
    )
    return {key: record[key] for key in fields}


def capture_legacy_previous(
    *, root, config_path, active_runtime, legacy_marker, ledger_root,
    probe, kernel_reader, ipfw_adapter, security_reader,
    config_fd, config_owner,
    require_lifecycle_owner,
) -> dict:
    """Persist old Config/runtime, transient marker, exact IPFW with fsync.

    On an interrupted capture leave the untrusted temp root for operator
    review. Never silently clear it or resume ordinary lifecycle from it.
    """
    if not isinstance(probe, FreeBSDVoiceProcessProbe) or (
        not isinstance(security_reader, FreeBSDProcessSecurityReader)
        or security_reader.probe is not probe
        or security_reader.expected_scripts != EXPECTED_SCRIPTS
        or security_reader.kernel_images != SYSTEM_PATHS
    ):
        raise LegacyPreviousSealError("untrusted legacy PoC process security source")
    root, config_path, active_runtime, legacy_marker = map(
        Path, (root, config_path, active_runtime, legacy_marker)
    )
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    # Full qualified read-only baseline must predate ANY durable staging.
    baseline = inspect_running_legacy_poc(
        config_path=config_path, active_runtime=active_runtime,
        legacy_marker=legacy_marker, whole_root=root, ledger_root=ledger_root,
        probe=probe, kernel_reader=kernel_reader, ipfw_adapter=ipfw_adapter,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if baseline["state"] != "legacy-poc-full-live-baseline-observed-not-owned":
        raise LegacyPreviousSealError("live PoC qualification incomplete")
    before = _old_poc_snapshot(legacy_marker, active_runtime)
    _private_dir(root)
    if os.listdir(root) or os.path.lexists(root / NAME):
        raise LegacyPreviousSealError("legacy previous evidence already exists")
    work = Path(tempfile.mkdtemp(prefix=".legacy-previous-", dir=root))
    os.chmod(work, 0o700)
    _sync_dir(root)
    # Save all previous Config/runtime bytes using the existing schema-2
    # no-follow, mode-preserving, atomic and fsynced Voice backup mechanism.
    capture_previous(config_path, active_runtime, work / "previous")
    saved = bound_resource_fingerprints(work / "previous")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    marker = _legacy_read(legacy_marker)
    if marker is None or _old_poc_snapshot(legacy_marker, active_runtime) != before:
        raise LegacyPreviousSealError("legacy source changed while capturing")
    marker_mode = stat.S_IMODE(os.lstat(legacy_marker).st_mode)
    _write_once(work / "marker.bin", marker)
    kernel = observe_legacy_poc_ipfw(
        ipfw_adapter, _current_engine_args(active_runtime)[0],
        before["managed"]["ipv4"],
    )
    if kernel["state"] != "legacy-ipfw-observed-not-owned" or (
        kernel["structure_sha256"] != baseline["legacy_ipfw_structure_sha256"]
        or kernel["previous_ipfw"] != baseline["legacy_ipfw_previous"]
    ):
        raise LegacyPreviousSealError("legacy PoC IPFW changed during backup")
    instances = _instances(probe.observe_processes())
    if instances != baseline["instances"]:
        raise LegacyPreviousSealError("old three-role processes changed during backup")
    expected = {
        "engine": _current_engine_args(active_runtime)[0],
        **canonical_supervisor_argv(EXPECTED_SCRIPTS),
    }
    if _current_engine_args(active_runtime)[1] != baseline["active_argument_sha256"]:
        raise LegacyPreviousSealError("old engine args changed during backup")
    for role, entry in instances.items():
        if kernel_reader.argv(entry["pid"]) != expected[role] or (
            kernel_reader.binary(entry["pid"]) != SYSTEM_PATHS[role]
        ):
            raise LegacyPreviousSealError("old process kernel identity drifted")
    original_probe_backup = probe.previous_backup
    try:
        # Reuse the existing validated two-copy process evidence and previous
        # supervisor-bound security policy. The probe resolves the *staged*
        # previous tree solely during this locked capture; restore its
        # original binding even if verification or fsync fails.
        probe.previous_backup = work / "previous"
        process_digests = capture_process_evidence(
            probe, work / "previous", work / "process-evidence", EXPECTED_SCRIPTS,
        )
        process = inspect_process_evidence(
            work / "process-evidence", work / "previous", EXPECTED_SCRIPTS,
        )
        if process["previous"] != process_digests or (
            _instances(probe.observe_processes()) != instances
        ):
            raise LegacyPreviousSealError("previous PoC process evidence drifted")
        old_five = {
            **saved, **process_digests,
            "firewall": kernel["structure_sha256"],
        }
        security = security_reader.inspect_twice()
        if security.get("state") != "review-required" or any(
            security.get("roles", {}).get(role, {}).get("pid") != row["pid"] or
            security["roles"][role].get("start_ns") != row["start_ns"]
            for role, row in instances.items()
        ):
            raise LegacyPreviousSealError("old PoC kernel credentials/epochs drifted")
        policy_sha = capture_security_policy(
            work / "previous", work / "process-evidence",
            work / "process-security-policy", old_five,
            EXPECTED_SCRIPTS, SYSTEM_PATHS, security_reader.credentials,
            supervisor_argv=canonical_supervisor_argv(EXPECTED_SCRIPTS),
        )
        policy = inspect_security_policy(
            work / "process-security-policy", work / "previous",
            work / "process-evidence", expected_scripts=EXPECTED_SCRIPTS,
        )
        if policy["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA or (
            policy["policy_sha256"] != policy_sha
            or not verify_current_security(security, policy)
        ):
            raise LegacyPreviousSealError("old PoC supervisor security seal invalid")
        if security_reader.inspect_twice() != security or (
            _instances(probe.observe_processes()) != instances
        ):
            raise LegacyPreviousSealError("old PoC process credentials changed")
    finally:
        probe.previous_backup = original_probe_backup
    record = {
        "schema": SCHEMA, "phase": "previous-evidence-only-not-owned",
        "previous": saved,
        "marker": {"mode": marker_mode, "sha256": _digest(marker),
                   "bytes": len(marker)},
        "legacy_ipfw_previous": kernel["previous_ipfw"],
        "legacy_ipfw_structure_sha256": kernel["structure_sha256"],
        "managed_ipv4_sha256": baseline["managed_ipv4_sha256"],
        "active_argument_sha256": baseline["active_argument_sha256"],
        "process_instances": instances,
        "previous_five": old_five,
        "process_security_policy_sha256": policy_sha,
    }
    body = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(body) > LIMIT:
        raise LegacyPreviousSealError("legacy previous evidence exceeds bound")
    _write_once(work / "legacy.json", body)
    _write_once(work / "legacy.sha256", (_digest(body) + "\n").encode("ascii"))
    _sync_dir(work)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if _old_poc_snapshot(legacy_marker, active_runtime) != before or (
        _instances(probe.observe_processes()) != instances
    ):
        raise LegacyPreviousSealError("previous PoC changed before atomic seal")
    final_ipfw = observe_legacy_poc_ipfw(
        ipfw_adapter, _current_engine_args(active_runtime)[0],
        before["managed"]["ipv4"],
    )
    if final_ipfw["previous_ipfw"] != kernel["previous_ipfw"] or (
        final_ipfw["structure_sha256"] != kernel["structure_sha256"]
    ):
        raise LegacyPreviousSealError("old IPFW changed before publishing evidence")
    os.rename(work, root / NAME)
    _sync_dir(root)
    result = inspect_legacy_previous(root)
    if result["legacy_ipfw_structure_sha256"] != baseline["legacy_ipfw_structure_sha256"]:
        raise LegacyPreviousSealError("published legacy PoC evidence untrusted")
    return result
