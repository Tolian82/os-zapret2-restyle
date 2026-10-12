#!/usr/bin/env python3
"""Stage-3 operator-only route to existing PREPARED five-resource Voice executor.

Must run as root/FreeBSD through the ORIGINAL zapret lifecycle lockf FD9.
No public GUI/configd/boot caller, no caller paths, no alternative rollback.
The imported executor holds the original Config inode flock through mutation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys

from voice_cutover_backup import _private_dir
from voice_cutover_journal import VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, BOUND_FIELD, RUNTIME_FIELD
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, decode_manifest, fingerprint
from voice_native_file_observer import observe_live_files
from voice_security_policy_evidence import SUPERVISOR_BOUND_POLICY_SCHEMA, inspect_security_policy
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_native_forward_apply import execute_prepared_voice_apply
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import _json_file
import voice_ipfw_runtime as native

STAGE = "forward-candidate"


class NativeVoiceApplyRouteError(RuntimeError):
    pass


def sealed_prepared_handoff(journal: VoiceCutoverJournal, stage: Path) -> dict:
    """Accept no unsealed stage or ambiguous five-resource journal state."""
    record = journal.read()
    if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or record["phase"] != "prepared":
        raise NativeVoiceApplyRouteError("only sealed PREPARED schema-4 eligible")
    stage = Path(stage)
    _private_dir(stage.parent)
    _private_dir(stage)
    if set(os.listdir(stage)) != {"desired-ipfw.json", "config.xml", "runtime"}:
        raise NativeVoiceApplyRouteError("unexpected forward candidate files")
    desired = decode_manifest(_json_file(stage / "desired-ipfw.json"))
    if (desired["rule_base"], desired["rule_max"]) != (19000, 19010) or (
        not desired["rules"] or not desired["tables"]
    ) or fingerprint(canonical_manifest(desired)) != record["candidate"][BOUND_FIELD]:
        raise NativeVoiceApplyRouteError("candidate IPFW differs from journal")
    files = observe_live_files(stage / "config.xml", stage / "runtime")
    if files["runtime"] != record["candidate"][RUNTIME_FIELD]:
        raise NativeVoiceApplyRouteError("candidate runtime tree differs from journal")
    if files["config"] != record["candidate"]["saved_xml_sha256"]:
        raise NativeVoiceApplyRouteError("candidate Config differs from journal")
    args = stage / "runtime" / "dvtws.args"
    if args.is_symlink() or not args.is_file():
        raise NativeVoiceApplyRouteError("candidate engine argv absent")
    with args.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != record["candidate"]["native_argv_sha256"]:
        raise NativeVoiceApplyRouteError("candidate engine argv differs from journal")
    return desired


def execute_operator_prepared() -> dict:
    native.require_native_lock()
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
    )


def main(argv: list[str]) -> int:
    if argv != ["execute-prepared"]:
        print("usage: voice_native_apply_route.py execute-prepared", file=sys.stderr)
        return 64
    try:
        result = execute_operator_prepared()
        if result.get("state") != "native-forward-five-resources-committed" or result.get("whole_phase") != "committed":
            raise NativeVoiceApplyRouteError("five-resource forward COMMIT not attested")
        print("native-voice-whole-apply=committed")
        print("native-voice-public-apply=disabled")
        return 0
    except (OSError, ValueError, RuntimeError):
        print("ERROR: native Voice Apply refused; inspect durable rollback evidence", file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
