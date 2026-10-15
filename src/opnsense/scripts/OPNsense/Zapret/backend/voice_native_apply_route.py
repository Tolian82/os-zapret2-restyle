#!/usr/bin/env python3
"""Stage-3 operator-only route to existing PREPARED five-resource Voice executor.

Must run as root/FreeBSD through the ORIGINAL zapret lifecycle lockf FD9.
No public GUI/configd/boot caller, no caller paths, no alternative rollback.
The imported executor holds the original Config inode flock through mutation.
"""
from __future__ import annotations

from pathlib import Path
import sys

from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
from voice_security_policy_evidence import SUPERVISOR_BOUND_POLICY_SCHEMA, inspect_security_policy
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_native_forward_apply import execute_prepared_voice_apply
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native

from voice_native_forward_stage_prepare import (
    STAGE, sealed_prepared_handoff,
    NativeVoiceStagePrepareError as NativeVoiceApplyRouteError,
)


def execute_operator_prepared(*, locked_config_fd: int | None = None) -> dict:
    """Standalone operator Apply OR one-FD9 PREPARED→Apply borrowed descriptor.

    The borrowed caller retains Config flock through the final commit/recovery;
    standalone execution preserves the previous self-owning Config lock path.
    No GUI/configd/boot caller may use this routine directly.
    """
    native.require_native_lock()
    if locked_config_fd is not None:
        if type(locked_config_fd) is not int or locked_config_fd < 0:
            raise NativeVoiceApplyRouteError("invalid borrowed original Config fd")
        _locked_config(native.CONFIG, locked_config_fd, (0, 0))
    journal = VoiceCutoverJournal(native.WHOLE)
    ledger = VoiceOwnershipStore(native.LEDGER)
    stage = native.WHOLE / STAGE
    desired = sealed_prepared_handoff(journal, stage)
    previous = native.WHOLE / "previous"
    process = native.WHOLE / "process-evidence"
    policy_dir = native.WHOLE / "process-security-policy"
    record = journal.read()
    policy = inspect_security_policy(
        policy_dir, previous, process, journal_record=record,
        expected_scripts=EXPECTED_SCRIPTS,
    )
    if policy["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA:
        raise NativeVoiceApplyRouteError("missing previous supervisor security policy")
    probe = FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS, PIDFILES, previous)
    kernel = FreeBSDKernelArgvReader(EXPECTED_SCRIPTS, probe)
    security = FreeBSDProcessSecurityReader(
        EXPECTED_SCRIPTS, policy["policy"]["images"],
        policy["policy"]["credentials"], probe,
    )

    def actions_factory(fd):
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, (0, 0))
        if journal.read() != record or inspect_security_policy(
            policy_dir, previous, process, journal_record=record,
            expected_scripts=EXPECTED_SCRIPTS,
        ) != policy:
            raise NativeVoiceApplyRouteError("previous process evidence changed")
        return FreeBSDVoiceProcessActions(
            probe=probe, journal=journal, previous_backup=previous,
            active_runtime=native.ACTIVE_ROOT, config_path=native.CONFIG,
            config_owner=(0, 0), config_fd=fd,
            require_lifecycle_owner=native.require_native_lock,
            process_evidence=process, security_evidence=policy_dir,
            security_reader=security, argv_reader=kernel,
        )

    native.require_native_lock()
    if journal.read() != record:
        raise NativeVoiceApplyRouteError("forward intent changed before execution")
    return execute_prepared_voice_apply(
        journal=journal, ledger=ledger, previous_backup=previous,
        process_evidence=process, security_evidence=policy_dir,
        install_image=native.WHOLE / "restore-install-image",
        config_path=native.CONFIG, active_runtime=native.ACTIVE_ROOT,
        staged_config=stage / "config.xml", candidate_runtime=stage / "runtime",
        desired_manifest=desired, probe=probe, kernel_reader=kernel,
        read_adapter=FreeBSDIPFWAdapter(19000, 19010),
        write_adapter=FreeBSDIPFWAdapter(19000, 19010, allow_mutations=True),
        require_lifecycle_owner=native.require_native_lock,
        actions_factory=actions_factory, config_owner=(0, 0),
        locked_config_fd=locked_config_fd,
    )


def main(argv: list[str]) -> int:
    # Deliberately refuse the retired standalone mutating operator CLI.
    # Helpers remain importable for isolated migration/recovery evidence only.
    if argv != ["execute-prepared"]:
        print("usage: voice_native_apply_route.py execute-prepared (retired)",
              file=sys.stderr)
        return 64
    print("ERROR: retired private Voice Apply; use shared Voice/Strategies Apply",
          file=sys.stderr)
    return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
