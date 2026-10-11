#!/usr/bin/env python3
"""Native root/FreeBSD FD9-owned five-resource Voice rollback (manual-only).

This is NOT the Voice ON workflow. It can only restore a previously sealed,
MUTATING schema-4 cutover, and ONLY when both original journal/ledger and
prior install-image/process-security evidence are intact. This command is
called exclusively by zapret_service.sh under its EXISTING lockf FD9 and
acquires one Config inode flock inside the five-resource executor.

NO GUI/configd/boot action, journal close, retired cleanup or forward cutover.
An interrupted retry uses the immutable schema-4 candidate-runtime digest,
never a hash derived from the current /usr/local/etc/zapret2/runtime-v2
(which might have been renamed or be absent after power loss).

Full on-device FreeBSD process-title/UID/kernel argv qualification and boot
replay are STILL required before any Voice ON or automatic rollback policy.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_journal import (
    RUNTIME_BOUND_SCHEMA, VoiceCutoverJournal, BOUND_FIELD,
    bound_candidate_runtime,
)
from voice_firewall_ledger import (
    VoiceOwnershipStore, canonical_manifest, decode_manifest, fingerprint,
)
from voice_native_file_observer import observe_live_files
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES
from voice_security_policy_evidence import (
    SUPERVISOR_BOUND_POLICY_SCHEMA, inspect_security_policy,
)
from voice_process_recovery_evidence import inspect_process_evidence
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_freebsd_kernel_argv import FreeBSDKernelArgvReader
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_cutover_five_resource_rollback import restore_previous_five_resources
import voice_ipfw_runtime as native


class NativeFiveResourceRecoveryError(RuntimeError):
    pass


def preflight_native_recovery(
    *, journal: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    previous_backup: Path, process_evidence: Path, security_evidence: Path,
    install_image: Path, read_ipfw_adapter: FreeBSDIPFWAdapter,
    require_lifecycle_owner,
) -> dict:
    """Check source proofs WITHOUT mutation; no extra or caller-chosen paths.

    A pending IPFW transaction can have the candidate kernel active; the
    actual revert is delegated to the checked IPFW transaction. When there is
    NO pending IPFW transaction, previous kernel ownership must already be
    independently observed. Never auto-adopt missing/foreign IPFW rules.
    """
    if not callable(require_lifecycle_owner) or \
       not isinstance(read_ipfw_adapter, FreeBSDIPFWAdapter) or \
       read_ipfw_adapter.allow_mutations is not False or \
       read_ipfw_adapter.rule_base != 19000 or \
       read_ipfw_adapter.rule_max != 19010:
        raise NativeFiveResourceRecoveryError("read-only native kernel witness required")
    require_lifecycle_owner()
    record=journal.read()
    if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or \
       record["phase"] != "mutating":
        raise NativeFiveResourceRecoveryError(
            "rollback requires an unfinished sealed schema-4 native cutover"
        )
    candidate_sha=bound_candidate_runtime(record)
    previous_backup=Path(previous_backup)
    previous_files=bound_resource_fingerprints(
        previous_backup, record["previous"],
    )
    if observe_live_files(
        Path(install_image)/"config.xml", Path(install_image)/"runtime",
        previous_backup=previous_backup,
    ) != previous_files:
        raise NativeFiveResourceRecoveryError(
            "previous install image is missing or differs from sealed backup"
        )
    saved_process=inspect_process_evidence(
        process_evidence, previous_backup,
        EXPECTED_SCRIPTS, record["previous"],
    )
    if saved_process["observation"]["engine"]["state"] != "running":
        raise NativeFiveResourceRecoveryError(
            "native production recovery requires saved one-engine topology"
        )
    policy=inspect_security_policy(
        security_evidence,previous_backup,process_evidence,
        journal_record=record,expected_scripts=EXPECTED_SCRIPTS,
    )
    if policy["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA or \
       policy["policy"]["supervisor_argv"] != canonical_supervisor_argv(
           EXPECTED_SCRIPTS
       ):
        raise NativeFiveResourceRecoveryError(
            "previous supervisor security policy is not sealed v2"
        )
    owned=ledger.owned()
    pending=ledger.pending()
    if owned is None or fingerprint(canonical_manifest(owned)) != \
       record["previous"]["firewall"]:
        raise NativeFiveResourceRecoveryError("previous IPFW ownership missing")
    if pending is None:
        if observe_owned_ipfw(ledger,read_ipfw_adapter) != \
           record["previous"]["firewall"]:
            raise NativeFiveResourceRecoveryError(
                "no pending IPFW rollback and previous native kernel absent"
            )
    else:
        if pending["phase"] != "mutating" or \
           pending["previous_sha256"] != record["previous"]["firewall"] or \
           pending["desired_sha256"] != record["candidate"][BOUND_FIELD] or \
           decode_manifest(pending["previous"]) != owned:
            raise NativeFiveResourceRecoveryError(
                "native IPFW pending ownership not bound to schema-4 intent"
            )
    require_lifecycle_owner()
    if journal.read()!=record or ledger.owned()!=owned or ledger.pending()!=pending:
        raise NativeFiveResourceRecoveryError("recovery evidence changed during preflight")
    return {
        "record":record,
        "candidate_runtime_sha256":candidate_sha,
        "policy":policy["policy"],
        "native_candidate_proof":{
            # BOUND by the durable checksum-protected schema-4 journal. Do
            # not use native.load_candidate(): Config/active runtime may
            # legitimately have changed or disappeared during rollback.
            "native_argv_sha256":record["candidate"]["native_argv_sha256"],
        },
        "state":"eligible-for-five-resource-rollback-only",
        "voice_on":False,
    }


def execute_native_recovery(
    *, journal: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    previous_backup: Path, process_evidence: Path, security_evidence: Path,
    install_image: Path, active_runtime: Path, config_path: Path,
    read_ipfw_adapter: FreeBSDIPFWAdapter, write_ipfw_adapter: FreeBSDIPFWAdapter,
    require_lifecycle_owner,
    process_probe: FreeBSDVoiceProcessProbe | None = None,
    native_actions_factory=None,
    rollback_executor=restore_previous_five_resources,
) -> dict:
    """One explicit five-domain executor call, no implicit retry loop."""
    before=preflight_native_recovery(
        journal=journal,ledger=ledger,previous_backup=previous_backup,
        process_evidence=process_evidence,security_evidence=security_evidence,
        install_image=install_image,read_ipfw_adapter=read_ipfw_adapter,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if not isinstance(write_ipfw_adapter,FreeBSDIPFWAdapter) or \
       write_ipfw_adapter.allow_mutations is not True or \
       write_ipfw_adapter.rule_base != 19000 or \
       write_ipfw_adapter.rule_max != 19010:
        raise NativeFiveResourceRecoveryError("bounded mutable IPFW adapter required")
    previous_backup,process_evidence,security_evidence=map(
        Path,(previous_backup,process_evidence,security_evidence),
    )
    config_path,active_runtime=Path(config_path),Path(active_runtime)
    probe = process_probe if process_probe is not None else FreeBSDVoiceProcessProbe(
        EXPECTED_SCRIPTS,PIDFILES,previous_backup,
    )
    if not isinstance(probe,FreeBSDVoiceProcessProbe) or \
       probe.expected != EXPECTED_SCRIPTS or \
       probe.pidfiles != PIDFILES or probe.previous_backup != previous_backup:
        raise NativeFiveResourceRecoveryError("untrusted FreeBSD process inventory")
    if native_actions_factory is None:
        # These readers are read-only; every kernel check uses the SAME
        # three-role process probe and sealed policy, not arbitrary objects.
        live_policy=before["policy"]
        sec_reader=FreeBSDProcessSecurityReader(
            EXPECTED_SCRIPTS,live_policy["images"],live_policy["credentials"],probe,
        )
        argv_reader=FreeBSDKernelArgvReader(EXPECTED_SCRIPTS,probe)
        def factory(fd):
            return FreeBSDVoiceProcessActions(
                probe=probe,journal=journal,previous_backup=previous_backup,
                active_runtime=active_runtime,config_path=config_path,
                config_owner=(0,0),config_fd=fd,
                require_lifecycle_owner=require_lifecycle_owner,
                process_evidence=process_evidence,
                security_evidence=security_evidence,
                security_reader=sec_reader,argv_reader=argv_reader,
            )
    else:
        # Injected factories are accepted by isolated regression tests only;
        # production CLI never passes this parameter.
        factory=native_actions_factory
    result=rollback_executor(
        journal=journal,ledger=ledger,previous_backup=previous_backup,
        install_image=Path(install_image),process_evidence=process_evidence,
        expected_scripts=EXPECTED_SCRIPTS,config_path=config_path,
        active_runtime=active_runtime,expected_owner=(0,0),
        expected_candidate_runtime_sha256=before["candidate_runtime_sha256"],
        candidate_proof=before["native_candidate_proof"],
        process_probe=probe,read_ipfw_adapter=read_ipfw_adapter,
        write_ipfw_adapter=write_ipfw_adapter,
        process_actions_factory=factory,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if result.get("state")!="five-previous-domains-observed" or \
       result.get("safe_to_clear_intent") is not False or \
       result.get("safe_to_enable_voice") is not False or \
       journal.read()!=before["record"]:
        raise NativeFiveResourceRecoveryError(
            "five-resource rollback did not retain durable whole-system intent"
        )
    return result


def main(argv:list[str]) -> int:
    if len(argv)!=2 or argv[1]!="rollback":
        print("usage: voice_native_five_resource_recovery.py rollback",file=sys.stderr)
        return 64
    try:
        native.require_native_lock()
        result=execute_native_recovery(
            journal=VoiceCutoverJournal(native.WHOLE),
            ledger=VoiceOwnershipStore(native.LEDGER),
            previous_backup=native.WHOLE/"previous",
            process_evidence=native.WHOLE/"process-evidence",
            security_evidence=native.WHOLE/"process-security-policy",
            install_image=native.WHOLE/"restore-install-image",
            active_runtime=native.ACTIVE_ROOT,
            config_path=native.CONFIG,
            read_ipfw_adapter=FreeBSDIPFWAdapter(19000,19010),
            write_ipfw_adapter=FreeBSDIPFWAdapter(
                19000,19010,allow_mutations=True,
            ),
            require_lifecycle_owner=native.require_native_lock,
        )
        print("native-voice-rollback="+result["state"])
        print("native-voice-whole-intent=mutating")
        print("voice-enable=blocked")
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print("ERROR: native Voice five-resource recovery refused: "+str(exc),
              file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main(sys.argv))
