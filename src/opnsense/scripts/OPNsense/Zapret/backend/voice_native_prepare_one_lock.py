#!/usr/bin/env python3
"""Stage-3 single-original-lock Voice PREPARED coordinator, import-only.

The only bridge joining verified ordinary owner adoption, previous
five-resource capture and the saved GUI/native generator candidate.
The eventual native service supplies the SAME FD9 lifecycle owner and
original Config inode flock; the function NEVER releases/reacquires them.
It does NOT generate a candidate, execute MUTATING, expose configd/GUI/boot
commands, restart processes or modify the IPFW kernel.
"""
from __future__ import annotations

from pathlib import Path

from voice_native_recovery_quiescence import _locked_config
from voice_native_initial_ipfw_seed import bootstrap_native_ordinary_ipfw_owner
from voice_native_previous_evidence_prepare import prepare_native_previous_evidence
from voice_native_saved_release_prepare import prepare_saved_release_forward_intent


class NativeOneLockPrepareError(RuntimeError):
    pass


def prepare_native_voice_one_lock(
    *, journal, ledger, config_path, active_runtime,
    source_config, source_runtime, release_dir, managed_source,
    ordinary_source, tcp_ports, udp_ports, physical_wan, divert_port,
    probe, kernel_reader, security_reader, ipfw_adapter,
    config_fd, config_owner, require_lifecycle_owner,
) -> dict:
    """One FD9+Config flock from ordinary Voice-OFF through sealed PREPARED.

    Once IPFW ownership has been seeded, failure at ANY later boundary
    intentionally leaves the durable owner/evidence for operator recovery:
    the legacy service is blocked by its normal journal/owner guard.
    """
    if not callable(require_lifecycle_owner):
        raise NativeOneLockPrepareError("missing original native lifecycle authority")

    def held():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)

    held()
    seeded = bootstrap_native_ordinary_ipfw_owner(
        whole_root=journal.directory, ledger=ledger,
        config_path=config_path, active_runtime=active_runtime,
        ordinary_source=ordinary_source, physical_wan=physical_wan,
        divert_port=divert_port, probe=probe, kernel_reader=kernel_reader,
        ipfw_adapter=ipfw_adapter, config_fd=config_fd,
        config_owner=config_owner, require_lifecycle_owner=require_lifecycle_owner,
    )
    if seeded.get("state") != "native-ordinary-ipfw-owner-sealed" or (
        seeded.get("must_continue_prepared_under_same_locks") is not True
        or seeded.get("safe_to_enable_voice") is not False
    ):
        raise NativeOneLockPrepareError("ordinary IPFW bootstrap was not sealed")
    held()
    previous = prepare_native_previous_evidence(
        journal=journal, ledger=ledger, config_path=config_path,
        active_runtime=active_runtime, probe=probe,
        security_reader=security_reader, ipfw_adapter=ipfw_adapter,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if previous.get("state") != "native-previous-five-domains-sealed" or (
        previous.get("safe_to_enable_voice") is not False
        or previous["previous"].get("firewall") != seeded["owned_ipfw_sha256"]
    ):
        raise NativeOneLockPrepareError("previous five resources disagree with owner")
    held()
    prepared = prepare_saved_release_forward_intent(
        release_dir=release_dir, managed_source=managed_source,
        ordinary_source=ordinary_source, tcp_ports=tcp_ports, udp_ports=udp_ports,
        physical_wan=physical_wan, divert_port=divert_port,
        source_config=source_config, source_runtime=source_runtime,
        journal=journal, ledger=ledger,
        previous_backup=previous["previous_backup"],
        process_evidence=previous["process_evidence"],
        security_evidence=previous["security_evidence"],
        previous_observer=previous["previous_observer"],
        config_path=config_path, active_runtime=active_runtime,
        expected_scripts=probe.expected, ipfw_adapter=ipfw_adapter,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    held()
    if prepared.get("state") != "native-voice-stage-and-forward-prepared" or (
        prepared.get("safe_to_enable_voice") is not False
        or prepared.get("previous_install_image") != "sealed-not-installed"
    ):
        raise NativeOneLockPrepareError("native forward PREPARED is incomplete")
    record = journal.read()
    if record is None or record.get("phase") != "prepared" or (
        record.get("schema") != 4
        or record.get("previous") != previous["previous"]
        or record.get("check") != prepared["whole_check"]
    ):
        raise NativeOneLockPrepareError("five-resource journal not sealed on original lock")
    return {
        "state": "native-voice-original-lock-prepared",
        "previous_owner_sha256": seeded["owned_ipfw_sha256"],
        "whole_check": prepared["whole_check"],
        "previous_install_image": "sealed-not-installed",
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }
