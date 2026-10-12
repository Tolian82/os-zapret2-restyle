#!/usr/bin/env python3
"""Stage 3 legacy PoC reverse WAL admission: import-only, NO kernel writes.

Attest the exact clean kernel/three-process boundary under the ORIGINAL FD9
and original Config inode flock, and persist a fsynced, write-once PREPARED
reverse intent bound to the legacy previous/restore-plan seals. This does
NOT change IPFW, install marker/Config/runtime, restart processes, adopt
ownership, or authorize any automatic recovery. Ambiguous partial records
stay on disk and keep the existing boot/lifecycle guard closed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
from voice_native_legacy_previous_seal import NAME, _digest, _write_once
from voice_native_legacy_restore_plan import (
    PLAN_NAME, PLAN_LIMIT, inspect_legacy_restore_plan,
)
from voice_native_live_ipfw import OLD_TABLE, OLD_STAGE, RULE_BASE, RULE_MAX
from voice_firewall_transaction import SERVICES, TABLE_PREFIX
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_firewall_ledger import VoiceOwnershipStore
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_legacy_poc_guard import _legacy_read
from voice_native_recovery_quiescence import (
    EXPECTED_SCRIPTS, PIDFILES, _locked_config,
)

WAL_NAME = "legacy-reverse-wal"
WAL_FILES = frozenset(("wal.json", "wal.sha256"))
SCHEMA = 1
LIMIT = 16384
INITIAL = "prepared-clean-kernel-not-executable"


class LegacyReverseWALError(RuntimeError):
    pass


def _stopped(probe: FreeBSDVoiceProcessProbe):
    if not isinstance(probe, FreeBSDVoiceProcessProbe) or (
        probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
    ):
        raise LegacyReverseWALError("untrusted three-process observer")
    a = probe.observe_processes()
    b = probe.observe_processes()
    if a != b or not isinstance(a, dict) or set(a) != {"engine", "supervisor"}:
        raise LegacyReverseWALError("unstable native/legacy process quiescence")
    engine, supervisor = a["engine"], a["supervisor"]
    if not isinstance(engine, dict) or not isinstance(supervisor, dict) or (
        engine.get("state") != "stopped" or supervisor.get("state") != "stopped"
    ):
        raise LegacyReverseWALError("old/new Voice processes are still running")
    roles = {"engine":engine.get("process"),
             "daemon":supervisor.get("daemon"),
             "monitor":supervisor.get("monitor")}
    for role, row in roles.items():
        if row != {"pid":None, "start_ns":None,
                   "executable":EXPECTED_SCRIPTS[role]}:
            raise LegacyReverseWALError("stale or unknown quiescent process role")
    return "exact-three-role-absence"


def _ledger_clear(directory: Path):
    directory = Path(directory)
    try:
        disk = os.lstat(directory)
    except FileNotFoundError:
        return "no-native-ledger"
    if not stat.S_ISDIR(disk.st_mode) or (
        disk.st_uid != os.geteuid() or disk.st_mode & 0o077
    ):
        raise LegacyReverseWALError("unsafe Voice IPFW ledger directory")
    ledger = VoiceOwnershipStore(directory)
    if ledger.pending() is not None or ledger.owned() is not None or (
        os.listdir(directory)
    ):
        raise LegacyReverseWALError("native kernel ownership or pending ledger exists")
    return "empty-private-ledger"


def _kernel_empty(adapter):
    if not isinstance(adapter, FreeBSDIPFWAdapter) or (
        adapter.allow_mutations is not False or adapter.rule_base != RULE_BASE
        or adapter.rule_max != RULE_MAX
    ):
        raise LegacyReverseWALError("untrusted legacy reverse IPFW observer")
    def observe():
        if adapter.list_rules(RULE_BASE, RULE_MAX):
            raise LegacyReverseWALError("existing IPFW 19000..19010 rule or foreign owner")
        for service in SERVICES:
            name = TABLE_PREFIX + service
            if adapter.get_table(name) is not None or (
                adapter.get_table(name + "_stage") is not None
            ):
                raise LegacyReverseWALError("native Voice table still present")
        for name in (OLD_TABLE, OLD_STAGE):
            if adapter._run("table", name, "info", allow_missing=True) is not None:
                raise LegacyReverseWALError("old Telegram PoC table still present")
        return "fixed-IPFW-19000-19010-and-voice-tables-empty"
    if observe() != observe():
        raise LegacyReverseWALError("unstable empty IPFW evidence")
    return "fixed-IPFW-19000-19010-and-voice-tables-empty"


def _old_marker_off(marker, runtime):
    """Reject any live legacy PoC authority before recording reverse intent."""
    marker, runtime = Path(marker), Path(runtime)
    if runtime.is_symlink() or _legacy_read(marker) is not None:
        raise LegacyReverseWALError("legacy Telegram PoC marker still active")
    state = _legacy_read(runtime / "telegram-voice-poc.state")
    if state is not None and state.strip() != b"disabled":
        raise LegacyReverseWALError("legacy Telegram PoC runtime still enabled")
    return "legacy-marker-absent-and-runtime-not-enabled"


def _read_manifest(root):
    root = Path(root)
    _private_dir(root)
    directory = root / WAL_NAME
    _private_dir(directory)
    if set(os.listdir(directory)) != WAL_FILES:
        raise LegacyReverseWALError("unknown or incomplete reverse WAL entries")
    raw = _read_private_file(directory / "wal.json", LIMIT)
    seal = _read_private_file(directory / "wal.sha256", 65)
    if seal != (_digest(raw) + "\n").encode("ascii"):
        raise LegacyReverseWALError("corrupted reverse WAL checksum")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {
        "schema", "phase", "restore_plan_sha256", "previous_five",
        "legacy_ipfw_structure_sha256", "process_security_policy_sha256",
        "marker_sha256", "quiescent_kernel", "quiescent_processes",
        "legacy_authority",
        "native_ledger", "safe_to_execute", "safe_to_enable_voice",
    } or type(value["schema"]) is not int or value["schema"] != SCHEMA or (
        value["phase"] != INITIAL or value["safe_to_execute"] is not False
        or value["safe_to_enable_voice"] is not False
    ):
        raise LegacyReverseWALError("invalid reverse WAL schema or authority")
    return value


def inspect_legacy_reverse_wal(root):
    """Read-only reboot triage, recompute source bindings; no kernel trust."""
    root = Path(root)
    _private_dir(root)
    if set(os.listdir(root)) != {NAME, PLAN_NAME, WAL_NAME}:
        raise LegacyReverseWALError("reverse WAL is not the only staging artifact")
    record = _read_manifest(root)
    plan = inspect_legacy_restore_plan(root)
    digest = _digest(_read_private_file(root / PLAN_NAME / "plan.json", PLAN_LIMIT))
    if (record["restore_plan_sha256"] != digest or
        record["previous_five"] != plan["previous_five"] or
        record["legacy_ipfw_structure_sha256"] !=
            plan["legacy_ipfw_structure_sha256"] or
        record["process_security_policy_sha256"] !=
            plan["process_security_policy_sha256"] or
        record["marker_sha256"] != plan["marker"]["sha256"] or
        record["quiescent_kernel"] !=
            "fixed-IPFW-19000-19010-and-voice-tables-empty" or
        record["quiescent_processes"] != "exact-three-role-absence" or
        record["legacy_authority"] !=
            "legacy-marker-absent-and-runtime-not-enabled" or
        record["native_ledger"] not in ("no-native-ledger", "empty-private-ledger")
    ):
        raise LegacyReverseWALError("reverse WAL not bound to trusted previous state")
    return {**record, "state": "reverse-wal-sealed-not-executable",
            "safe_to_mutate": False, "public_voice_apply": False}


def prepare_legacy_reverse_wal(
    root, *, config_path, config_fd, config_owner, ledger_root,
    legacy_marker, active_runtime,
    process_probe, readonly_ipfw, require_lifecycle_owner,
):
    """Prepare and fsync a non-executable WAL AFTER witnessed quiescence.

    Never infer authority from this PREPARED record: a future production
    reverse executor MUST first establish its own durable per-action undo
    boundary and original lifecycle ownership after reboot/crash.
    """
    if not callable(require_lifecycle_owner) or (
        type(config_fd) is not int or config_fd < 0
    ):
        raise LegacyReverseWALError("missing original lifecycle/Config owner")
    root, config_path = Path(root), Path(config_path)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _private_dir(root)
    if set(os.listdir(root)) != {NAME, PLAN_NAME} or (
        os.path.lexists(root / WAL_NAME)
    ):
        raise LegacyReverseWALError("foreign, incomplete or pre-existing recovery state")
    plan = inspect_legacy_restore_plan(root)
    ledger = _ledger_clear(ledger_root)
    stopped = _stopped(process_probe)
    inactive = _old_marker_off(legacy_marker, active_runtime)
    clean = _kernel_empty(readonly_ipfw)
    record = {
        "schema": SCHEMA, "phase": INITIAL,
        "restore_plan_sha256": _digest(
            _read_private_file(root / PLAN_NAME / "plan.json", PLAN_LIMIT)
        ),
        "previous_five": plan["previous_five"],
        "legacy_ipfw_structure_sha256": plan["legacy_ipfw_structure_sha256"],
        "process_security_policy_sha256": plan["process_security_policy_sha256"],
        "marker_sha256": plan["marker"]["sha256"],
        "quiescent_kernel": clean,
        "quiescent_processes": stopped,
        "legacy_authority": inactive,
        "native_ledger": ledger,
        "safe_to_execute": False, "safe_to_enable_voice": False,
    }
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(raw) > LIMIT:
        raise LegacyReverseWALError("reverse WAL record exceeds bound")
    scratch = Path(tempfile.mkdtemp(prefix=".legacy-reverse-wal-", dir=root))
    os.chmod(scratch, 0o700)
    _sync_dir(root)
    # An interrupted write is NEVER silently discarded or retried.
    _write_once(scratch / "wal.json", raw)
    _write_once(scratch / "wal.sha256", (_digest(raw) + "\n").encode("ascii"))
    _sync_dir(scratch)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if (inspect_legacy_restore_plan(root) != plan or
        _ledger_clear(ledger_root) != ledger or
        _stopped(process_probe) != stopped or
        _old_marker_off(legacy_marker, active_runtime) != inactive or
        _kernel_empty(readonly_ipfw) != clean or
        set(os.listdir(root)) != {NAME, PLAN_NAME, scratch.name}):
        raise LegacyReverseWALError("reverse predecessor drift before WAL publication")
    os.rename(scratch, root / WAL_NAME)
    _sync_dir(root)
    return inspect_legacy_reverse_wal(root)
