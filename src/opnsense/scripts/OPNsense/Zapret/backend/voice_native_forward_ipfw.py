#!/usr/bin/env python3
"""Native forward Voice stage: audited engine-only -> IPFW desired PRECOMMIT.

This PRIVATE stage composes the pre-existing production ownership ledger and
transactional IPFW actuator. No public GUI/configd/boot dispatcher exists.
It never commits the whole cutover, starts a supervisor or edits Config.

The original FD9 lifecycle owner and original Config flock must be held
continuously. Original Config, retained old runtime, candidate active/runtime,
write-ahead runtime redo, sealed schema-4 MUTATING intent, old owner and
kernel IPFW are checked BEFORE any kernel mutation. The only live process
must be the candidate dvtws2, with stable native PID/start and exactly matching
FreeBSD kernel argv and executable. The bound desired IPFW manifest must
target that running engine's divert port; legacy Telegram PoC is forbidden.

Existing activate_verified() writes a separate fsynced IPFW PRECOMMIT journal
BEFORE changing kernel rules, retains previous table snapshots, and rolls back
its own partial changes on a known error. Ambiguous kernel state leaves the
ledger+whole MUTATING journals for explicit full-system recovery. Never infer
ownership from rule numbers, never automatically commit or enable Voice.
"""
from __future__ import annotations

from pathlib import Path
import os

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, BOUND_FIELD
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, fingerprint
from voice_firewall_transaction import verify_prior_state, plan_postcommit_cleanup
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import activate_verified, require_no_legacy
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_live_preflight import _current_engine_args
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import _read_redo


class ForwardIPFWError(RuntimeError):
    pass


def install_forward_voice_ipfw(
    *, journal, ledger, previous_backup, active_runtime, staged_config,
    candidate_runtime, config_path, desired_manifest, probe, kernel_reader,
    readonly_adapter, mutating_adapter, config_fd, config_owner,
    require_lifecycle_owner,
):
    """Write actual kernel Voice rules only after stable engine-only evidence.

    Caller must be the future complete native coordinator; this does not
    grant any standalone authority to mutate the firewall.
    """
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or Path(probe.previous_backup) != Path(previous_backup)
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(readonly_adapter, FreeBSDIPFWAdapter)
        or readonly_adapter.allow_mutations is not False
        or not isinstance(mutating_adapter, FreeBSDIPFWAdapter)
        or mutating_adapter.allow_mutations is not True
        or any(a.rule_base != 19000 or a.rule_max != 19010
               for a in (readonly_adapter, mutating_adapter))
        or not callable(require_lifecycle_owner)
        or type(config_fd) is not int or config_fd < 0
    ):
        raise ForwardIPFWError("untrusted native forward IPFW/process owner")
    previous_backup, active_runtime, config_path = map(
        Path, (previous_backup, active_runtime, config_path)
    )
    staged_config, candidate_runtime = map(
        Path, (staged_config, candidate_runtime)
    )
    desired = canonical_manifest(desired_manifest)
    desired_digest = fingerprint(desired)
    if not desired_manifest["tables"] or not desired_manifest["rules"]:
        raise ForwardIPFWError("empty candidate Voice IPFW rules are not an activation")
    divert_ports = {argv[1] for argv in desired_manifest["rules"].values()}
    if len(divert_ports) != 1:
        raise ForwardIPFWError("candidate IPFW uses inconsistent divert ports")

    def owner():
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        _pinned_regular(config_path, config_fd, owner=config_owner)

    def sealed():
        owner()
        record = journal.read()
        if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or (
            record["phase"] != "mutating"
            or record["candidate"][BOUND_FIELD] != desired_digest
        ):
            raise ForwardIPFWError("no exact schema-4 MUTATING Voice IPFW intent")
        original = bound_resource_fingerprints(previous_backup, record["previous"])
        current = observe_live_files(config_path, active_runtime)
        candidate = observe_live_files(staged_config, candidate_runtime)
        if current != {
            "config": original["config"],
            "runtime": record["candidate"]["candidate_runtime_sha256"],
        } or candidate != {
            "config": record["candidate"]["saved_xml_sha256"],
            "runtime": current["runtime"],
        }:
            raise ForwardIPFWError("staged or active Voice Config/runtime changed")
        retained = active_runtime.with_name(
            ".voice-forward-previous-" + record["check"][:20]
        )
        if retained.is_symlink() or not retained.is_dir() or (
            observe_live_files(staged_config, retained)["runtime"] != original["runtime"]
        ):
            raise ForwardIPFWError("previous runtime cannot be recovered")
        redo = _read_redo(journal.directory)
        if redo is None or (
            redo["whole_check"] != record["check"]
            or redo["candidate_sha256"] != current["runtime"]
            or redo["previous_sha256"] != original["runtime"]
            or redo["retained_name"] != retained.name
            or redo["active_name"] != active_runtime.name
            or os.path.lexists(active_runtime.with_name(redo["ready_name"]))
        ):
            raise ForwardIPFWError("forward runtime redo is not intact")
        cfg = os.fstat(config_fd)
        parent = os.lstat(active_runtime.parent)
        if (cfg.st_dev, cfg.st_ino) != (
            redo["config_dev"], redo["config_inode"]
        ) or (parent.st_dev, parent.st_ino) != (
            redo["parent_dev"], redo["parent_inode"]
        ):
            raise ForwardIPFWError("Config or runtime parent inode changed")
        expected, args_sha, _, _ = _current_engine_args(active_runtime)
        if args_sha != record["candidate"]["native_argv_sha256"] or (
            expected[1:] == []
            or desired_manifest["rules"] and divert_ports != {
                word.split("=", 1)[1] for word in expected
                if word.startswith("--port=")
            }
        ):
            raise ForwardIPFWError("desired IPFW divert differs from sealed engine port")
        return record, expected, args_sha

    def engine(expected):
        owner()
        one = probe.observe_candidate_engine_only()
        if one["state"] != "engine-only" or (
            type(one["pid"]) is not int or one["pid"] <= 1
            or type(one["start_ns"]) is not int or one["start_ns"] <= 0
        ):
            raise ForwardIPFWError("one candidate engine without supervisor required")
        if kernel_reader.argv(one["pid"]) != expected or (
            kernel_reader.binary(one["pid"]) != SYSTEM_PATHS["engine"]
        ):
            raise ForwardIPFWError("candidate FreeBSD kernel argv or image differs")
        return one

    initial, expected, arg_sha = sealed()
    if ledger.pending() is not None:
        raise ForwardIPFWError("an IPFW PRECOMMIT already exists; manual review")
    previous = ledger.owned()
    if previous is None or fingerprint(canonical_manifest(previous)) != (
        initial["previous"]["firewall"]
    ):
        raise ForwardIPFWError("original IPFW ledger not sealed by whole journal")

    # The old Telegram PoC has a separate unowned table/marker. NEVER adopt.
    require_no_legacy(readonly_adapter)
    first = engine(expected)
    if engine(expected) != first:
        raise ForwardIPFWError("candidate engine PID/start changed before IPFW")
    if observe_owned_ipfw(ledger, readonly_adapter) != initial["previous"]["firewall"]:
        raise ForwardIPFWError("old real kernel IPFW differs before cutover")
    verify_prior_state(mutating_adapter, previous, desired_manifest)
    if sealed() != (initial, expected, arg_sha) or engine(expected) != first:
        raise ForwardIPFWError("candidate/Config/whole journal raced before IPFW")
    if observe_owned_ipfw(ledger, readonly_adapter) != initial["previous"]["firewall"]:
        raise ForwardIPFWError("kernel IPFW raced before activation")

    # The pre-existing adapter atomically seals its separate IPFW PRECOMMIT
    # before touching the kernel. Its rollback preserves the whole journal.
    proof = {"native_argv_sha256": arg_sha}
    result = activate_verified(
        ledger, mutating_adapter, desired_manifest, journal, proof
    )
    if result != "installed-pending-whole-commit":
        raise ForwardIPFWError("native IPFW activation not in pending state")

    owner()
    pending = ledger.pending()
    if pending is None or pending["phase"] != "mutating" or (
        pending["previous_sha256"] != initial["previous"]["firewall"]
        or pending["desired_sha256"] != desired_digest
        or ledger.owned() != previous
    ):
        raise ForwardIPFWError("desired IPFW ownership is not durably pending")
    # In this phase stage tables intentionally RETAIN previous targets.
    # Do not use store.inspect(): it reserves stage tables for manual review
    # during generic boot recovery rather than this live locked coordinator.
    plan_postcommit_cleanup(mutating_adapter, previous, desired_manifest)
    if sealed() != (initial, expected, arg_sha) or (
        engine(expected) != first or engine(expected) != first
    ):
        raise ForwardIPFWError("candidate engine or whole intent changed after IPFW")
    if ledger.pending() != pending:
        raise ForwardIPFWError("IPFW PRECOMMIT changed after kernel activation")
    return {
        "state": "candidate-ipfw-installed-pending-whole-commit",
        "phase": "mutating",
        "candidate_pid": first["pid"],
        "desired_ipfw_sha256": desired_digest,
        "previous_ipfw_ownership_retained": True,
        "old_table_snapshots_retained": True,
        "supervisor_started": False,
        "can_commit": False,
        "voice_on": False,
        "media_pass": False,
    }
