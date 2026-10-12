#!/usr/bin/env python3
"""Stage 3: seal the previous five domains under the ORIGINAL native locks.

Import-only bridge to the existing old-backup, process-evidence and security-
policy writers. Does not seed/adopt IPFW, create a cutover intent, stop
processes, change the live Config/runtime, or authorize Voice ON.
The caller retains FD9 and the same Config flock through the subsequent
saved-release PREPARED preparation. On failure durable evidence is retained
for operator review; never infer success from a partial directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from voice_cutover_backup import (
    _private_dir, capture_previous, bound_resource_fingerprints,
)
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, fingerprint
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_file_observer import LiveFileObserver, observe_live_files
from voice_native_full_observer import NativePreviousObserver
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_kernel_argv import SYSTEM_PATHS
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_process_recovery_evidence import (
    capture_process_evidence, inspect_process_evidence,
)
from voice_security_policy_evidence import (
    SUPERVISOR_BOUND_POLICY_SCHEMA, capture_security_policy,
    inspect_security_policy, verify_current_security,
)

PREVIOUS = "previous"
PROCESSES = "process-evidence"
SECURITY = "process-security-policy"


class PreviousEvidencePrepareError(RuntimeError):
    pass


def prepare_native_previous_evidence(
    *, journal: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    config_path, active_runtime, probe: FreeBSDVoiceProcessProbe,
    security_reader: FreeBSDProcessSecurityReader,
    ipfw_adapter: FreeBSDIPFWAdapter, config_fd, config_owner,
    require_lifecycle_owner,
) -> dict:
    """Capture old Config/runtime/process/security, then reobserve five domains.

    The IPFW ledger must ALREADY contain an explicitly verified ordinary
    owner. This routine is NOT the missing initial adoption/migration step.
    No caller-specified images, executable paths, credentials, or file names
    are accepted: the reader must be pinned to native three-role paths.
    """
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or not isinstance(security_reader, FreeBSDProcessSecurityReader)
        or security_reader.probe is not probe
        or security_reader.expected_scripts != EXPECTED_SCRIPTS
        or security_reader.kernel_images != SYSTEM_PATHS
        or not isinstance(ipfw_adapter, FreeBSDIPFWAdapter)
        or ipfw_adapter.allow_mutations is not False
        or (ipfw_adapter.rule_base, ipfw_adapter.rule_max) != (19000, 19010)
        or not callable(require_lifecycle_owner)
    ):
        raise PreviousEvidencePrepareError("untrusted native previous-state sources")
    root = journal.directory
    prior_path = root / PREVIOUS
    process_path = root / PROCESSES
    security_path = root / SECURITY
    if Path(probe.previous_backup) != prior_path:
        raise PreviousEvidencePrepareError("previous process probe not bound to native backup")

    def held():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)

    held()
    _private_dir(root)
    # A leftover previous checkpoint/journal is NOT a fresh transaction.
    # Never overwrite or auto-remove an unknown partial/power-cut state.
    if os.listdir(root) or journal.read() is not None or ledger.pending() is not None:
        raise PreviousEvidencePrepareError("previous or incomplete Voice evidence present")
    previous_ipfw = ledger.owned()
    if previous_ipfw is None or (
        previous_ipfw["rule_base"], previous_ipfw["rule_max"]
    ) != (19000, 19010):
        raise PreviousEvidencePrepareError("no sealed matching previous IPFW owner")
    old_digest = fingerprint(canonical_manifest(previous_ipfw))
    if observe_owned_ipfw(ledger, ipfw_adapter) != old_digest:
        raise PreviousEvidencePrepareError("previous native kernel IPFW not owned")

    original_files = observe_live_files(Path(config_path), Path(active_runtime))
    previous_processes = probe.observe_processes()
    if previous_processes["engine"]["state"] != "running" or (
        previous_processes["supervisor"]["state"] != "running"
    ):
        raise PreviousEvidencePrepareError("partial or stopped previous native service")

    held()
    capture_previous(Path(config_path), Path(active_runtime), prior_path)
    previous_files = bound_resource_fingerprints(prior_path)
    if previous_files != original_files:
        raise PreviousEvidencePrepareError("captured previous Config/runtime drifted")
    process_digests = capture_process_evidence(
        probe, prior_path, process_path, EXPECTED_SCRIPTS,
    )
    old_process_record = inspect_process_evidence(
        process_path, prior_path, EXPECTED_SCRIPTS,
    )
    if old_process_record["previous"] != process_digests or (
        probe.observe_processes() != previous_processes
    ):
        raise PreviousEvidencePrepareError("previous process epochs changed during capture")
    old_five = {**previous_files, **process_digests, "firewall": old_digest}
    security = security_reader.inspect_twice()
    # The current kernel image+credential witness must match these exact
    # previous PID/start epochs before freezing the security policy.
    expected_instances = {
        "engine": previous_processes["engine"]["process"],
        "daemon": previous_processes["supervisor"]["daemon"],
        "monitor": previous_processes["supervisor"]["monitor"],
    }
    if security.get("state") != "review-required" or any(
        security.get("roles", {}).get(role, {}).get("pid") != row["pid"] or
        security["roles"][role].get("start_ns") != row["start_ns"]
        for role, row in expected_instances.items()
    ):
        raise PreviousEvidencePrepareError("kernel credentials/epochs changed before seal")
    policy_sha = capture_security_policy(
        prior_path, process_path, security_path, old_five,
        EXPECTED_SCRIPTS, SYSTEM_PATHS, security_reader.credentials,
        supervisor_argv=canonical_supervisor_argv(EXPECTED_SCRIPTS),
    )
    policy = inspect_security_policy(
        security_path, prior_path, process_path, expected_scripts=EXPECTED_SCRIPTS,
    )
    if policy["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA or (
        policy["policy_sha256"] != policy_sha
        or not verify_current_security(security, policy)
    ):
        raise PreviousEvidencePrepareError("previous supervisor security not verified")
    observer = NativePreviousObserver(
        config=Path(config_path), runtime=Path(active_runtime),
        previous_backup=prior_path, process_evidence=process_path,
        expected_executables=EXPECTED_SCRIPTS,
        process_probe=probe, firewall_store=ledger,
        firewall_adapter=ipfw_adapter,
        file_observer=LiveFileObserver(config_path, active_runtime, prior_path),
    )
    for _ in range(2):
        held()
        if observer.observe() != old_five or (
            probe.observe_processes() != previous_processes
            or observe_live_files(Path(config_path), Path(active_runtime)) != original_files
            or observe_owned_ipfw(ledger, ipfw_adapter) != old_digest
            or ledger.owned() != previous_ipfw
            or ledger.pending() is not None
            or journal.read() is not None
        ):
            raise PreviousEvidencePrepareError("previous five native domains drifted")
    return {
        "state": "native-previous-five-domains-sealed",
        "previous": old_five,
        "process_policy_sha256": policy_sha,
        "previous_backup": prior_path,
        "process_evidence": process_path,
        "security_evidence": security_path,
        "previous_observer": observer,
        "safe_to_enable_voice": False,
    }
