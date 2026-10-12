#!/usr/bin/env python3
"""Import-only legacy Telegram PoC reverse-install *plan*, never executor.

Reconstruct the bounded old IPFW table/rules and marker restoration contract
from the fsync'd previous PoC snapshot, independently of the untrusted kernel.
Refuses foreign syntax even if a saved manifest checksum was recomputed.
There is deliberately NO ipfw subprocess, live marker write, CLI, GUI or
configd path. No plan can authorize cutover, owner adoption or Voice ON.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
from voice_native_legacy_previous_seal import (
    NAME, LIMIT, _digest, _write_once, inspect_legacy_previous,
)
from voice_native_live_preflight import _current_engine_args
from voice_native_live_ipfw import _engine_port, OLD_TABLE, RULE_BASE, RULE_MAX
from voice_ipfw_adapter import checked_ipv4, checked_rule_argv, INTERFACE
from voice_native_recovery_quiescence import _locked_config

PLAN_NAME = "legacy-restore-plan"
SCHEMA = 1
MAX_IPS = 4096
PLAN_LIMIT = 1048576
PLAN_FILES = frozenset(("plan.json", "plan.sha256"))


class LegacyRestorePlanError(RuntimeError):
    pass


def _validate_old_kernel(old, saved_port, managed):
    """Recover exact trusted old syntax, not an arbitrary IPFW command list."""
    if not isinstance(old, dict) or set(old) != {"rules", "targets", "wan", "port"}:
        raise LegacyRestorePlanError("unknown old IPFW witness schema")
    port, wan, rules, targets = old["port"], old["wan"], old["rules"], old["targets"]
    if port != saved_port or not isinstance(wan, str) or (
        not INTERFACE.fullmatch(wan)
    ) or not isinstance(rules, dict) or len(rules) not in (2, 3):
        raise LegacyRestorePlanError("old divert port, WAN or rules untrusted")
    sequence = [str(RULE_BASE + i) for i in range(len(rules))]
    if set(rules) != set(sequence):
        raise LegacyRestorePlanError("old IPFW rule numbering has a foreign entry")
    first = rules[str(RULE_BASE)]
    if not isinstance(first, list) or len(first) != 14 or first[:7] != [
        "divert", port, "udp", "from", "any", "to", f"table({OLD_TABLE})"
    ] or first[7:] != [
        "out", "not", "diverted", "not", "sockarg", "xmit", wan
    ]:
        raise LegacyRestorePlanError("saved Telegram IPFW divert rule is foreign")
    seen = set()
    for number in sequence[1:]:
        rule = rules[number]
        checked_rule_argv(rule)
        if (len(rule) != 15 or rule[6] != "any" or rule[1] != port
            or rule[-1] != wan or rule[2] in seen):
            raise LegacyRestorePlanError("saved ordinary IPFW rule is foreign")
        seen.add(rule[2])
    if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_IPS or (
        any(not isinstance(v, str) for v in targets)
    ):
        raise LegacyRestorePlanError("invalid legacy IPv4 table size")
    clean = [checked_ipv4(v) for v in targets]
    if clean != sorted(set(clean)) or set(clean) != set(managed) or (
        len(clean) != len(managed)
    ):
        raise LegacyRestorePlanError("legacy IPFW targets differ from saved IPSET")
    return sequence, clean


def build_legacy_restore_plan(root: Path) -> dict:
    """Pure inspection. A plan is evidence, never permission to execute."""
    root = Path(root)
    previous = inspect_legacy_previous(root)
    archive = root / NAME
    record = json.loads(_read_private_file(archive / "legacy.json", LIMIT))
    runtime = archive / "previous" / "runtime"
    argv, argv_hash, _, _ = _current_engine_args(runtime)
    if argv_hash != record["active_argument_sha256"]:
        raise LegacyRestorePlanError("saved engine port differs from previous runtime")
    port = _engine_port(argv)
    managed_raw = _read_private_file(runtime / "managed" / "ipset-telegram.txt", 256 * 1024)
    if _digest(managed_raw) != record["managed_ipv4_sha256"]:
        raise LegacyRestorePlanError("saved managed IPSET hash mismatch")
    try:
        decoded = managed_raw.decode("ascii")
    except UnicodeError as exc:
        raise LegacyRestorePlanError("saved managed IPv4 file is non-ASCII") from exc
    if any(ord(c) not in range(32, 127) and c not in "\n\r" for c in decoded):
        raise LegacyRestorePlanError("unsafe saved managed IPv4 file")
    managed = [checked_ipv4(v) for v in decoded.splitlines() if v]
    if len(managed) != len(set(managed)) or not managed:
        raise LegacyRestorePlanError("duplicate or absent saved managed IPv4")
    old = record["legacy_ipfw_previous"]
    sequence, ips = _validate_old_kernel(old, port, managed)
    if _read_private_file(runtime / "telegram-voice-poc.state", 64) not in (
        b"enabled", b"enabled\n"
    ):
        raise LegacyRestorePlanError("previous Telegram PoC was not enabled")
    marker = record["marker"]
    if _digest(_read_private_file(archive / "marker.bin", 64)) != marker["sha256"]:
        raise LegacyRestorePlanError("saved marker no longer matches previous PoC")
    # An executor MUST require absence of *all* rules in 19000..19010,
    # absence of both old/native tables, complete prior owner/journal phase,
    # one original FD9 + Config flock, and a separate durable undo record
    # BEFORE issuing any of these ordered legacy commands.
    operations = [
        ["/sbin/ipfw", "-q", "table", OLD_TABLE, "create", "type", "addr"],
        *[["/sbin/ipfw", "-q", "table", OLD_TABLE, "add", ip] for ip in ips],
        *[["/sbin/ipfw", "-qf", "add", str(number), *old["rules"][number]]
          for number in sequence],
    ]
    return {
        "schema": SCHEMA,
        "state": "legacy-reverse-actions-sealed-not-authorized",
        "previous_five": record["previous_five"],
        "legacy_ipfw_structure_sha256": previous["legacy_ipfw_structure_sha256"],
        "process_security_policy_sha256": previous["process_security_policy_sha256"],
        "marker": marker,
        "marker_saved_relative": "legacy-previous/marker.bin",
        "marker_target": "/var/run/zapret2-telegram-voice-poc.enabled",
        "preconditions": [
            "original-fd9-and-original-config-inode-flock",
            "durable-undo-and-whole-mutating-journal-required",
            "all-19000-19010-rules-absent-and-all-related-tables-absent",
            "separately-verified-quiesced-processes-and-exact-owner",
            "no-foreign-rule-or-table-adoption",
        ],
        "legacy_ipfw_commands": operations,
        "safe_to_execute": False,
        "safe_to_mutate": False,
        "safe_to_enable_voice": False,
        "rollback_implemented": False,
        "public_voice_apply": False,
    }


def inspect_legacy_restore_plan(root: Path) -> dict:
    root = Path(root)
    _private_dir(root)
    directory = root / PLAN_NAME
    _private_dir(directory)
    if set(os.listdir(directory)) != PLAN_FILES:
        raise LegacyRestorePlanError("unknown or partial legacy reverse plan")
    body = _read_private_file(directory / "plan.json", PLAN_LIMIT)
    digest = _read_private_file(directory / "plan.sha256", 65)
    if digest != (_digest(body) + "\n").encode("ascii"):
        raise LegacyRestorePlanError("damaged legacy reverse plan")
    record = json.loads(body)
    if record != build_legacy_restore_plan(root):
        raise LegacyRestorePlanError("reverse plan differs from sealed previous evidence")
    return record


def prepare_legacy_restore_plan(root: Path, *, config_path, config_fd,
                                config_owner, require_lifecycle_owner):
    """Write-once preparation under ORIGINAL locks, no live operation."""
    if not callable(require_lifecycle_owner) or (
        type(config_fd) is not int or config_fd < 0
    ):
        raise LegacyRestorePlanError("missing original lifecycle/Config owner")
    root, config_path = Path(root), Path(config_path)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _private_dir(root)
    if set(os.listdir(root)) != {NAME} or os.path.lexists(root / PLAN_NAME):
        raise LegacyRestorePlanError("foreign/unfinished Voice staging in journal root")
    plan = build_legacy_restore_plan(root)
    body = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(body) > PLAN_LIMIT:
        raise LegacyRestorePlanError("legacy plan exceeds bounded size")
    temp = Path(tempfile.mkdtemp(prefix=".legacy-restore-plan-", dir=root))
    os.chmod(temp, 0o700)
    _sync_dir(root)
    # An interruption deliberately leaves the staging directory for operator
    # review; do not delete a possibly durable incomplete rollback plan.
    _write_once(temp / "plan.json", body)
    _write_once(temp / "plan.sha256", (_digest(body) + "\n").encode("ascii"))
    _sync_dir(temp)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if plan != build_legacy_restore_plan(root):
        raise LegacyRestorePlanError("sealed old PoC changed while planning rollback")
    os.rename(temp, root / PLAN_NAME)
    _sync_dir(root)
    return inspect_legacy_restore_plan(root)
