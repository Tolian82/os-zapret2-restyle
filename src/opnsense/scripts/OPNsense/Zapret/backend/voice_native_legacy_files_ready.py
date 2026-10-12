#!/usr/bin/env python3
"""Stage old Telegram PoC Config/runtime and marker after verified IPFW replay.

Import-only, not an owner-live recovery coordinator. Reuses existing sealed
Voice restore-stage and permission-accurate install-image helpers. Both remain
UNDER a private durable output directory; active /conf/config.xml, runtime-v2,
old marker and three process roles are NEVER written or started here.

Original FD9 + original Config inode flock must remain held, the old IPFW
kernel must exactly match a completely fsynced per-command replay, and
legacy and native process/marker/ledger state must remain quiescent. Crash
leaves an identifiable partial artifact which the boot lifecycle guard blocks.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from voice_cutover_backup import (
    _private_dir, _read_private_file, _sync_dir,
    bound_resource_fingerprints, inspect_previous,
)
from voice_native_legacy_previous_seal import NAME, _digest, _write_once
from voice_native_legacy_restore_plan import (
    PLAN_NAME, inspect_legacy_restore_plan,
)
from voice_native_legacy_reverse_wal import (
    WAL_NAME, inspect_legacy_reverse_wal, _stopped, _old_marker_off,
    _ledger_clear,
)
from voice_native_legacy_ipfw_replay import (
    REPLAY_NAME, _strict_snapshot, _steps, _expected_after,
)
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_native_file_observer import observe_live_files
from voice_native_recovery_quiescence import _locked_config

FILES_NAME = "legacy-files-ready"
FILES = frozenset(("restore-stage", "install-image", "marker.bin",
                   "ready.json", "ready.sha256"))
SCHEMA = 1
MAX_RECORD = 16384
EXPECTED_ROOT = frozenset((NAME, PLAN_NAME, WAL_NAME, REPLAY_NAME))


class LegacyFilesReadyError(RuntimeError):
    pass


def _snapshot(root):
    """Read-only evidence: all old IPFW replay commands completed and current."""
    plan = inspect_legacy_restore_plan(root)
    inspect_legacy_reverse_wal(root, allow_ipfw_replay=True)
    directory = root / REPLAY_NAME
    _private_dir(directory)
    done, active = _steps(directory, plan)
    if active or done != len(plan["legacy_ipfw_commands"]):
        raise LegacyFilesReadyError("previous Telegram IPFW restore still incomplete")
    return plan


def _contents(root, plan):
    source = root / NAME / "previous"
    fingerprints = bound_resource_fingerprints(source, plan["previous_five"])
    return source, fingerprints


def _read_ready(root, plan):
    directory = root / FILES_NAME
    _private_dir(directory)
    if set(os.listdir(directory)) != FILES:
        raise LegacyFilesReadyError("foreign or incomplete legacy file restore image")
    raw = _read_private_file(directory / "ready.json", MAX_RECORD)
    checksum = _read_private_file(directory / "ready.sha256", 65)
    if checksum != (_digest(raw) + "\n").encode("ascii"):
        raise LegacyFilesReadyError("legacy restore file-stage seal mismatch")
    record = json.loads(raw)
    required = {"schema", "phase", "previous_five",
                "process_security_policy_sha256", "legacy_ipfw_structure_sha256",
                "marker_sha256", "marker_mode", "marker_bytes",
                "safe_to_install", "safe_to_start", "safe_to_enable_voice"}
    if not isinstance(record, dict) or set(record) != required or (
        type(record["schema"]) is not int or record["schema"] != SCHEMA or
        record["phase"] != "previous-files-verified-only-not-installed" or
        record["safe_to_install"] is not False or
        record["safe_to_start"] is not False or
        record["safe_to_enable_voice"] is not False
    ):
        raise LegacyFilesReadyError("untrusted previous files-ready schema")
    if record["previous_five"] != plan["previous_five"] or (
        record["legacy_ipfw_structure_sha256"] !=
        plan["legacy_ipfw_structure_sha256"] or
        record["process_security_policy_sha256"] !=
        plan["process_security_policy_sha256"] or
        record["marker_sha256"] != plan["marker"]["sha256"] or
        record["marker_mode"] != plan["marker"]["mode"] or
        record["marker_bytes"] != plan["marker"]["bytes"]
    ):
        raise LegacyFilesReadyError("previous files image not bound to PoC")
    source, fingerprints = _contents(root, plan)
    stage = directory / "restore-stage"
    image = directory / "install-image"
    if bound_resource_fingerprints(stage, fingerprints) != fingerprints or (
        inspect_previous(stage) != inspect_previous(source)
    ):
        raise LegacyFilesReadyError("staged previous Config/runtime differs")
    if observe_live_files(image / "config.xml", image / "runtime",
                          previous_backup=stage) != fingerprints:
        raise LegacyFilesReadyError("install image differs from original file modes")
    marker = _read_private_file(directory / "marker.bin", 64)
    if len(marker) != record["marker_bytes"] or (
        _digest(marker) != record["marker_sha256"]
    ):
        raise LegacyFilesReadyError("previous PoC transient marker bytes changed")
    return record


def inspect_legacy_files_ready(root):
    """Disk-only reboot triage; cannot authorize installation or Voice ON."""
    root = Path(root)
    _private_dir(root)
    if set(os.listdir(root)) != EXPECTED_ROOT | {FILES_NAME}:
        raise LegacyFilesReadyError("foreign previous-file recovery artifact")
    plan = inspect_legacy_restore_plan(root)
    record = _read_ready(root, plan)
    return {
        "state": "legacy-previous-files-staged-not-installed",
        "previous_five": record["previous_five"],
        "marker_sha256": record["marker_sha256"],
        "process_security_policy_sha256": record["process_security_policy_sha256"],
        "safe_to_install": False,
        "safe_to_start": False,
        "safe_to_enable_voice": False,
        "whole_rollback_complete": False,
        "public_voice_apply": False,
    }


def stage_legacy_previous_files(
    *, root, config_path, config_fd, config_owner, active_runtime,
    legacy_marker, ledger_root, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """Fsync an accurate prior image under original locks, never install it."""
    if not callable(require_lifecycle_owner) or (
        type(config_fd) is not int or config_fd < 0
    ):
        raise LegacyFilesReadyError("missing original owner/Config FD")
    root, config_path = Path(root), Path(config_path)

    def held():
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)

    def prove_environment(plan):
        if _stopped(process_probe) != "exact-three-role-absence" or (
            _old_marker_off(legacy_marker, active_runtime) !=
            "legacy-marker-absent-and-runtime-not-enabled"
        ) or _ledger_clear(ledger_root) not in (
            "no-native-ledger", "empty-private-ledger"
        ):
            raise LegacyFilesReadyError("legacy PoC surroundings changed")
        if _strict_snapshot(readonly_ipfw) != (
            _expected_after(plan, len(plan["legacy_ipfw_commands"]))
        ):
            raise LegacyFilesReadyError("old PoC IPFW replay no longer matches")
        if _snapshot(root) != plan:
            raise LegacyFilesReadyError("previous replay seal changed")

    held()
    _private_dir(root)
    if set(os.listdir(root)) != EXPECTED_ROOT or (
        os.path.lexists(root / FILES_NAME)
    ):
        raise LegacyFilesReadyError("unknown or existing previous files stage")
    plan = _snapshot(root)
    prove_environment(plan)
    source, fingerprints = _contents(root, plan)

    scratch = Path(tempfile.mkdtemp(prefix=".legacy-files-ready-", dir=root))
    os.chmod(scratch, 0o700)
    _sync_dir(root)
    stage = scratch / "restore-stage"
    image = scratch / "install-image"
    staged = prepare_restore_stage(source, stage, plan["previous_five"])
    if staged["previous"] != fingerprints or (
        staged["activation_authorized"] is not False
    ):
        raise LegacyFilesReadyError("old Config/runtime staging was not verified")
    built = prepare_installable_restore(stage, image, plan["previous_five"])
    if built["previous"] != fingerprints or built["activation_authorized"] is not False:
        raise LegacyFilesReadyError("old install image was not verified")
    marker = _read_private_file(root / NAME / "marker.bin", 64)
    if len(marker) != plan["marker"]["bytes"] or (
        _digest(marker) != plan["marker"]["sha256"]
    ):
        raise LegacyFilesReadyError("old Telegram marker changed in backup")
    _write_once(scratch / "marker.bin", marker)
    record = {
        "schema": SCHEMA,
        "phase": "previous-files-verified-only-not-installed",
        "previous_five": plan["previous_five"],
        "process_security_policy_sha256": plan["process_security_policy_sha256"],
        "legacy_ipfw_structure_sha256": plan["legacy_ipfw_structure_sha256"],
        "marker_sha256": plan["marker"]["sha256"],
        "marker_mode": plan["marker"]["mode"],
        "marker_bytes": plan["marker"]["bytes"],
        "safe_to_install": False, "safe_to_start": False,
        "safe_to_enable_voice": False,
    }
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(raw) > MAX_RECORD:
        raise LegacyFilesReadyError("previous file stage record too large")
    _write_once(scratch / "ready.json", raw)
    _write_once(scratch / "ready.sha256", (_digest(raw)+"\n").encode("ascii"))
    _sync_dir(scratch)
    held()
    prove_environment(plan)
    if set(os.listdir(root)) != EXPECTED_ROOT | {scratch.name}:
        raise LegacyFilesReadyError("unexpected previous-file stage changed")
    # Check all copies before publication, including original modes.
    if bound_resource_fingerprints(stage, fingerprints) != fingerprints or (
        observe_live_files(image / "config.xml", image / "runtime",
                           previous_backup=stage) != fingerprints
    ):
        raise LegacyFilesReadyError("previous Config/runtime image changed before seal")
    os.rename(scratch, root / FILES_NAME)
    _sync_dir(root)
    return inspect_legacy_files_ready(root)
