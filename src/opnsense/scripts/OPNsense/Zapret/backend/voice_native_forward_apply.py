#!/usr/bin/env python3
"""One locked native Voice forward executor: PREPARED -> committed five domains.

PRIVATE, import-only: never a public GUI/configd/boot or old Telegram PoC path.
The caller supplies the independently prepared schema-4 whole intent and
pre-seeded old IPFW ownership. This composes the existing native stages, not
alternative process/Config/IPFW mutation mechanisms. It holds ONE original
OPNsense config.xml inode flock over the whole transition, in addition to
the ORIGINAL FD9 lifecycle owner; each stage rechecks both.

Any failed stage leaves a durable PREPARED/MUTATING/COMMITTED intent and the
previous checkpoint. In particular, NEVER implicitly restart an old engine
after partial IPFW/Config mutation. The existing five-resource recovery is
a separate fail-closed path pending safe same-FD integration. A successful
COMMITTED state also remains journaled for later postcommit cleanup/boot.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path

from voice_cutover_backup import bound_resource_fingerprints, inspect_previous
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import (
    VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, BOUND_FIELD,
    _digest, validate_record, mutating_predecessor,
)
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, fingerprint, decode_manifest
from voice_firewall_transaction import plan_postcommit_cleanup, verify_prior_state
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import commit_verified, require_no_legacy
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_process_recovery_evidence import ProcessEvidenceError, inspect_process_evidence
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS, _live_instances
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_process_actions import FreeBSDVoiceProcessActions, SCRIPT
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import _read_redo
from voice_native_forward_config import (
    persist_forward_candidate_config, read_forward_config_redo,
)
from voice_native_forward_stop import stop_previous_and_install_forward_runtime
from voice_native_candidate_engine_start import start_forward_candidate_engine
from voice_native_forward_ipfw import install_forward_voice_ipfw
from voice_native_forward_supervisor import start_forward_voice_supervisor
from voice_native_live_preflight import _current_engine_args
from voice_native_five_resource_recovery import preflight_native_recovery
from voice_native_boot_recovery_review import inspect_boot_recovery
from voice_cutover_five_resource_rollback import restore_previous_five_resources
from voice_native_restart_integrity import attest_previous_restart
from voice_cutover_recovery_receipt import seal_previous_receipt
from voice_cutover_cleanup_prepare import seal_previous_completion


class NativeForwardApplyError(RuntimeError):
    """A failed or ambiguous transition MUST retain all recovery evidence."""


def _authorities(*, journal, ledger, probe, kernel_reader, read_adapter,
                 write_adapter, previous_backup, require_lifecycle_owner):
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or Path(probe.previous_backup) != Path(previous_backup)
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(read_adapter, FreeBSDIPFWAdapter)
        or read_adapter.allow_mutations is not False
        or not isinstance(write_adapter, FreeBSDIPFWAdapter)
        or write_adapter.allow_mutations is not True
        or any(x.rule_base != 19000 or x.rule_max != 19010
               for x in (read_adapter, write_adapter))
        or not callable(require_lifecycle_owner)
    ):
        raise NativeForwardApplyError("untrusted native Voice forward authorities")


def attest_forward_five_resources(
    *, journal, ledger, previous_backup, config_path, config_fd,
    config_owner, staged_config, candidate_runtime, active_runtime,
    desired_manifest, probe, kernel_reader, read_adapter,
    require_lifecycle_owner, expected_phase="mutating",
    ipfw_committed=False, postcommit_pending=False,
):
    """Independently witness five real candidate domains under BOTH locks.

    A successful writer is not a permit to commit: re-open all read-only
    sources and compare twice, including process PID/start/kernel argv,
    original Config inode, bound previous bytes, installed runtime+redo,
    and actual IPFW tables/rules. In COMMITTED mode verify post-cleanup
    desired ownership instead of the now-absent IPFW pending intent.
    """
    if expected_phase not in ("mutating", "committed") or (
        (ipfw_committed or postcommit_pending) and expected_phase != "committed"
    ) or (ipfw_committed and postcommit_pending):
        raise NativeForwardApplyError("invalid forward attestation phase")
    _authorities(
        journal=journal, ledger=ledger, probe=probe,
        kernel_reader=kernel_reader, read_adapter=read_adapter,
        write_adapter=FreeBSDIPFWAdapter(19000, 19010, allow_mutations=True),
        previous_backup=previous_backup,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    config_path, staged_config, candidate_runtime, active_runtime = map(
        Path, (config_path, staged_config, candidate_runtime, active_runtime)
    )
    previous_backup = Path(previous_backup)
    desired = canonical_manifest(desired_manifest)
    wanted_sha = fingerprint(desired)

    def observe():
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        cfg = _pinned_regular(config_path, config_fd, owner=config_owner)
        record = journal.read()
        if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or (
            record["phase"] != expected_phase
            or record["candidate"][BOUND_FIELD] != wanted_sha
        ):
            raise NativeForwardApplyError("whole forward intent not at expected phase")
        # Runtime/forward-Config redo and retained directory use the original
        # MUTATING digest, never the later COMMITTED digest. Reconstruct
        # the predecessor from the validated persisted terminal journal.
        predecessor_body = {k: v for k, v in record.items() if k != "check"}
        predecessor_body["phase"] = "mutating"
        predecessor_body["check"] = _digest(predecessor_body)
        mutating = validate_record(predecessor_body)
        old = bound_resource_fingerprints(previous_backup, record["previous"])
        saved = inspect_previous(previous_backup)
        candidate = observe_live_files(staged_config, candidate_runtime)
        live = observe_live_files(config_path, active_runtime)
        if candidate != {
            "config": record["candidate"]["saved_xml_sha256"],
            "runtime": record["candidate"]["candidate_runtime_sha256"],
        } or live != candidate:
            raise NativeForwardApplyError("five-domain desired Config/runtime not active")
        if os.stat(config_path, follow_symlinks=False).st_ino != cfg.st_ino or (
            (cfg.st_dev, cfg.st_ino) != (os.fstat(config_fd).st_dev, os.fstat(config_fd).st_ino)
            or (cfg.st_mode & 0o7777) != saved["config"]["mode"]
        ):
            raise NativeForwardApplyError("Config inode/mode changed after candidate write")
        retained = active_runtime.with_name(
            ".voice-forward-previous-" + mutating["check"][:20]
        )
        if retained.is_symlink() or not retained.is_dir() or (
            observe_live_files(staged_config, retained)["runtime"] != old["runtime"]
        ):
            raise NativeForwardApplyError("previous runtime not retained")
        redo = _read_redo(journal.directory)
        parent = os.lstat(active_runtime.parent)
        if redo is None or (
            redo["whole_check"] != mutating["check"]
            or redo["candidate_sha256"] != candidate["runtime"]
            or redo["previous_sha256"] != old["runtime"]
            or redo["retained_name"] != retained.name
            or redo["active_name"] != active_runtime.name
            or (redo["config_dev"], redo["config_inode"]) != (cfg.st_dev, cfg.st_ino)
            or (redo["parent_dev"], redo["parent_inode"]) != (
                parent.st_dev, parent.st_ino
            )
            or os.path.lexists(active_runtime.with_name(redo["ready_name"]))
        ):
            raise NativeForwardApplyError("forward runtime redo/parent not intact")
        config_redo = read_forward_config_redo(journal.directory)
        if live["config"] != old["config"]:
            if config_redo is None or (
                config_redo["whole_check"] != mutating["check"]
                or config_redo["candidate_sha256"] != live["config"]
                or config_redo["previous_sha256"] != old["config"]
                or (config_redo["config_dev"], config_redo["config_inode"])
                    != (cfg.st_dev, cfg.st_ino)
            ):
                raise NativeForwardApplyError("candidate Config lacks durable forward redo")
        elif config_redo is not None and (
            config_redo["whole_check"] != mutating["check"]
        ):
            raise NativeForwardApplyError("foreign forward Config redo")
        old_owner, pending = ledger.owned(), ledger.pending()
        if ipfw_committed:
            if pending is not None or canonical_manifest(old_owner) != desired:
                raise NativeForwardApplyError("postcommit IPFW owner is not desired")
            verify_prior_state(read_adapter, desired_manifest, desired_manifest)
        elif postcommit_pending:
            # COMMITTED is irreversible. IPFW ownership may already have
            # switched to desired when power was interrupted. Admit only
            # the original sealed prior->desired ledger under full proof.
            if old_owner is None or pending is None or (
                pending["phase"] != "mutating"
                or pending["previous_sha256"] != record["previous"]["firewall"]
                or pending["desired_sha256"] != wanted_sha
                or pending["desired"] != desired
                or canonical_manifest(old_owner) not in (
                    pending["previous"], desired
                )
            ):
                raise NativeForwardApplyError("foreign committed IPFW redo/owner")
            plan_postcommit_cleanup(
                read_adapter, decode_manifest(pending["previous"]),
                desired_manifest,
            )
        else:
            if old_owner is None or pending is None or (
                fingerprint(canonical_manifest(old_owner)) != record["previous"]["firewall"]
                or pending["phase"] != "mutating"
                or pending["previous_sha256"] != record["previous"]["firewall"]
                or pending["desired_sha256"] != wanted_sha
                or pending["previous"] != canonical_manifest(old_owner)
                or pending["desired"] != desired
            ):
                raise NativeForwardApplyError("separate IPFW PRECOMMIT no longer bound")
            plan_postcommit_cleanup(read_adapter, old_owner, desired_manifest)
        require_no_legacy(read_adapter)
        argv, argv_sha, _, _ = _current_engine_args(active_runtime)
        if argv_sha != record["candidate"]["native_argv_sha256"] or (
            {part.split("=", 1)[1] for part in argv if part.startswith("--port=")}
            != {rule[1] for rule in desired_manifest["rules"].values()}
        ):
            raise NativeForwardApplyError("candidate engine digest/divert port mismatch")
        instances = _live_instances(probe.observe_processes())
        expected = {"engine": argv, **canonical_supervisor_argv(EXPECTED_SCRIPTS)}
        for role, identity in instances.items():
            if kernel_reader.argv(identity["pid"]) != expected[role] or (
                kernel_reader.binary(identity["pid"]) != SYSTEM_PATHS[role]
            ):
                raise NativeForwardApplyError("candidate native kernel args/image mismatch")
        return (record, old, candidate, instances,
                canonical_manifest(old_owner), pending, redo, config_redo)

    first = observe()
    if observe() != first:
        raise NativeForwardApplyError("five-resource state raced across attestation")
    return first


def commit_forward_voice_apply(
    *, journal, ledger, previous_backup, config_path, config_fd,
    config_owner, staged_config, candidate_runtime, active_runtime,
    desired_manifest, probe, kernel_reader, read_adapter, write_adapter,
    require_lifecycle_owner,
):
    """One-way COMMIT after independent 5-domain witness, no GUI/boot caller.

    The durable WHOLE commit MUST precede IPFW ownership cleanup (existing
    commit_verified contract); a crash between these states leaves COMMITTED
    plus IPFW MUTATING for explicit postcommit reconciliation. Never roll
    back after the whole intent is committed.
    """
    _authorities(
        journal=journal, ledger=ledger, probe=probe, kernel_reader=kernel_reader,
        read_adapter=read_adapter, write_adapter=write_adapter,
        previous_backup=previous_backup,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    shared = dict(
        journal=journal, ledger=ledger, previous_backup=previous_backup,
        config_path=config_path, config_fd=config_fd, config_owner=config_owner,
        staged_config=staged_config, candidate_runtime=candidate_runtime,
        active_runtime=active_runtime, desired_manifest=desired_manifest,
        probe=probe, kernel_reader=kernel_reader, read_adapter=read_adapter,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    before = attest_forward_five_resources(**shared)
    if journal.read() != before[0] or ledger.pending() != before[5]:
        raise NativeForwardApplyError("five resources raced before durable COMMIT")
    journal.commit()  # fsync whole journal BEFORE retiring old IPFW ownership
    committed = journal.read()
    if committed is None or committed["phase"] != "committed" or (
        committed["previous"] != before[0]["previous"]
        or committed["candidate"] != before[0]["candidate"]
    ):
        raise NativeForwardApplyError("whole durable COMMIT not sealed")
    return resume_committed_forward_voice_apply(
        **shared, write_adapter=write_adapter,
    )


def resume_committed_forward_voice_apply(
    *, journal, ledger, previous_backup, config_path, config_fd,
    config_owner, staged_config, candidate_runtime, active_runtime,
    desired_manifest, probe, kernel_reader, read_adapter, write_adapter,
    require_lifecycle_owner,
):
    """Resume COMMITTED-only IPFW cleanup, under original FD9 and Config flock.

    PRIVATE imported helper, never a boot/GUI/service entrypoint. It does
    not stop/restart engines, write XML or change runtime. Only the existing
    commit_verified actuator can mutate IPFW after full five-domain proof.
    """
    _authorities(
        journal=journal, ledger=ledger, probe=probe, kernel_reader=kernel_reader,
        read_adapter=read_adapter, write_adapter=write_adapter,
        previous_backup=previous_backup,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    shared = dict(
        journal=journal, ledger=ledger, previous_backup=previous_backup,
        config_path=config_path, config_fd=config_fd, config_owner=config_owner,
        staged_config=staged_config, candidate_runtime=candidate_runtime,
        active_runtime=active_runtime, desired_manifest=desired_manifest,
        probe=probe, kernel_reader=kernel_reader, read_adapter=read_adapter,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    committed = journal.read()
    if committed is None or committed["schema"] != RUNTIME_BOUND_SCHEMA or (
        committed["phase"] != "committed"
    ):
        raise NativeForwardApplyError("postcommit replay requires schema-4 COMMITTED")
    pending = ledger.pending()
    if pending is not None:
        before = attest_forward_five_resources(
            **shared, expected_phase="committed", postcommit_pending=True,
        )
        if journal.read() != before[0] or ledger.pending() != before[5]:
            raise NativeForwardApplyError("postcommit replay evidence raced")
        result = commit_verified(
            ledger, write_adapter, journal,
            {"native_argv_sha256": committed["candidate"]["native_argv_sha256"]},
        )
        if result != "committed":
            raise NativeForwardApplyError("IPFW postcommit replay incomplete")
    post = attest_forward_five_resources(
        **shared, expected_phase="committed", ipfw_committed=True,
    )
    if post[0] != committed:
        raise NativeForwardApplyError("whole journal changed during postcommit replay")
    # Previous snapshot/runtime/redos and whole journal remain for cleanup.
    return {
        "state": "native-forward-five-resources-committed",
        "whole_phase": "committed",
        "ipfw_owner": "desired",
        "config": "candidate", "runtime": "candidate",
        "engine": "candidate", "supervisor": "candidate",
        "previous_snapshot_retained": True,
        "postcommit_cleanup_pending": True,
        "public_voice_apply": False,
        "media_pass": False,
    }


def rollback_failed_precommit_voice_apply(
    *, journal, ledger, previous_backup, process_evidence, security_evidence,
    install_image, config_path, active_runtime, staged_config,
    config_fd, config_owner, probe, kernel_reader, read_adapter,
    write_adapter, require_lifecycle_owner, actions,
):
    """Use the EXISTING five-resource rollback with the ORIGINAL Config FD.

    Called only while the schema-4 whole journal remains MUTATING. The
    previous installation image and security policy must already be sealed.
    The existing process actuator must prove the candidate can be stopped:
    complete three-role state or a single fully kernel-attested candidate
    engine without supervisor. Foreign/orphan/partial supervisor remains blocked.
    No service boot/GUI route, IPFW ownership inference or fresh Config
    flock exists here. A successful rollback still retains its whole journal
    until the separately qualified durable previous-restart receipt/closure.
    """
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or Path(probe.previous_backup) != Path(previous_backup)
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(read_adapter, FreeBSDIPFWAdapter)
        or read_adapter.allow_mutations is not False
        or not isinstance(write_adapter, FreeBSDIPFWAdapter)
        or write_adapter.allow_mutations is not True
        or any(a.rule_base != 19000 or a.rule_max != 19010
               for a in (read_adapter, write_adapter))
        or not callable(require_lifecycle_owner)
    ):
        raise NativeForwardApplyError("untrusted native previous rollback authority")
    if not isinstance(actions, FreeBSDVoiceProcessActions) or (
        actions.journal is not journal or actions.probe is not probe
        or actions.config_fd != config_fd or actions.owner != config_owner
        or actions.previous_backup != Path(previous_backup)
        or actions.config_path != Path(config_path)
        or actions.active_runtime != Path(active_runtime)
    ):
        raise NativeForwardApplyError("recovery actuator does not own original locked Config")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record = journal.read()
    if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or (
        record["phase"] != "mutating"
    ):
        raise NativeForwardApplyError("only unfinished MUTATING Voice is eligible for rollback")
    # Validate the old install image, saved process security policy, and
    # scoped IPFW ledger BEFORE any partial candidate engine stop.
    checked = preflight_native_recovery(
        journal=journal, ledger=ledger, previous_backup=Path(previous_backup),
        process_evidence=Path(process_evidence),
        security_evidence=Path(security_evidence),
        install_image=Path(install_image), read_ipfw_adapter=read_adapter,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if checked["record"] != record:
        raise NativeForwardApplyError("previous recovery witnesses changed")
    # When the *production* actuator carries BOTH sealed native readers,
    # finish the previous recovery exactly as the manual five-resource
    # executor does: re-attest the restarted process, fsync the previous
    # receipt, then fsync the non-destructive cleanup plan / ROLLED_BACK
    # terminal journal, ALL before releasing this borrowed original FD.
    # Simulated runners lacking these independent kernel readers never
    # receive a fabricated receipt or terminal state.
    ready_to_seal = (
        actions.security_reader is not None
        and actions.argv_reader is not None
    )
    if ready_to_seal and (
        actions.process_evidence != Path(process_evidence)
        or actions.security_evidence != Path(security_evidence)
    ):
        raise NativeForwardApplyError("native previous restart readers not bound to evidence")
    if (actions.security_reader is None) != (actions.argv_reader is None):
        raise NativeForwardApplyError("incomplete previous restart integrity readers")
    seal = None
    if ready_to_seal:
        def seal(borrowed_fd):
            if borrowed_fd != config_fd:
                raise NativeForwardApplyError("previous receipt cannot change original Config fd")
            require_lifecycle_owner()
            _locked_config(Path(config_path), borrowed_fd, config_owner)
            proof = attest_previous_restart(
                journal=journal, previous_backup=Path(previous_backup),
                process_evidence=Path(process_evidence),
                security_evidence=Path(security_evidence),
                expected_scripts=EXPECTED_SCRIPTS,
                security_reader=actions.security_reader,
                argv_reader=actions.argv_reader,
                require_lifecycle_owner=require_lifecycle_owner,
                require_config_owner=lambda:_locked_config(
                    Path(config_path), borrowed_fd, config_owner,
                ),
            )
            receipt = seal_previous_receipt(
                journal=journal, ledger=ledger,
                previous_backup=Path(previous_backup),
                config_path=Path(config_path),
                active_runtime=Path(active_runtime),
                config_fd=borrowed_fd, config_owner=config_owner,
                probe=probe, adapter=read_adapter, integrity_report=proof,
                require_lifecycle_owner=require_lifecycle_owner,
            )
            prepared = seal_previous_completion(
                journal=journal, ledger=ledger,
                previous_backup=Path(previous_backup),
                install_image=Path(install_image),
                config_path=Path(config_path),
                active_runtime=Path(active_runtime),
                config_fd=borrowed_fd, config_owner=config_owner,
                probe=probe, adapter=read_adapter, integrity_report=proof,
                require_lifecycle_owner=require_lifecycle_owner,
            )
            if prepared["state"] != "previous-rollback-sealed" or (
                prepared["whole_intent_phase"] != "rolled_back"
                or prepared["safe_to_finish_intent"] is not False
            ):
                raise NativeForwardApplyError("previous recovery completion not durably sealed")
            return {**receipt, "whole_intent_phase":"rolled_back"}
    # A running three-role candidate uses the existing all-roles process
    # stop. The intentional intermediate phase (one candidate engine,
    # no supervisor) needs a narrowly attested engine-only stop; never
    # treat other partially started supervisors as engine-only.
    try:
        a = probe.observe_processes()
        b = probe.observe_processes()
    except ProcessEvidenceError:
        one = probe.observe_candidate_engine_only()
        two = probe.observe_candidate_engine_only()
        if one != two or one["state"] != "engine-only":
            raise NativeForwardApplyError(
                "partial or foreign Voice process topology; manual recovery"
            )
        candidate_argv, argv_sha, _, _ = _current_engine_args(Path(active_runtime))
        running = observe_live_files(Path(staged_config), Path(active_runtime))
        redo = _read_redo(journal.directory)
        cfg = os.fstat(config_fd)
        if argv_sha != record["candidate"]["native_argv_sha256"] or (
            running["runtime"] != record["candidate"]["candidate_runtime_sha256"]
            or running["config"] != record["candidate"]["saved_xml_sha256"]
            or redo is None or redo["whole_check"] != record["check"]
            or redo["candidate_sha256"] != running["runtime"]
            or redo["previous_sha256"] != record["previous"]["runtime"]
            or (redo["config_dev"], redo["config_inode"])
                != (cfg.st_dev, cfg.st_ino)
            or redo["active_name"] != Path(active_runtime).name
        ):
            raise NativeForwardApplyError(
                "single candidate engine runtime/redo not bound to forward intent"
            )
        if kernel_reader.argv(one["pid"]) != candidate_argv or (
            kernel_reader.binary(one["pid"]) != SYSTEM_PATHS["engine"]
        ):
            raise NativeForwardApplyError("foreign engine-only kernel argv/image")
        pending = ledger.pending()
        if pending is not None:
            if ledger.owned() is None:
                raise NativeForwardApplyError("previous IPFW ownership absent")
            plan_postcommit_cleanup(read_adapter, ledger.owned(), decode_manifest(pending["desired"]))
        # Final pre-stop identity under the SAME FD9+Config flock. The
        # actuator checks PID/start + kernel image again immediately before
        # dispatching the fixed no-PID shell helper.
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        if journal.read() != record or (
            probe.observe_candidate_engine_only() != one
        ):
            raise NativeForwardApplyError("engine-only recovery state raced")
        actions.stop_forward_engine_only(
            kernel_reader=kernel_reader, expected_argv=candidate_argv,
            expected_pid=one["pid"], expected_start_ns=one["start_ns"],
        )
        a = probe.observe_processes()
        b = probe.observe_processes()
    if a != b:
        raise NativeForwardApplyError("unstable candidate process topology before recovery")

    # Crash after the previous engine/supervisor were restarted, but before
    # previous-receipt/ROLLED_BACK was fsynced. Never stop those now-live old
    # processes as if they were a candidate. The journal remains MUTATING;
    # only a FRESH sealed FreeBSD kernel image/credential/argv attestation
    # can finish it, under this exact original FD9 + Config flock.
    if a["engine"]["state"] == "running" and (
        a["supervisor"]["state"] == "running"
        and ledger.pending() is None
    ):
        old = bound_resource_fingerprints(
            Path(previous_backup), record["previous"],
        )
        try:
            restored = observe_live_files(
                Path(config_path), Path(active_runtime),
                previous_backup=Path(previous_backup),
            ) == old
        except (OSError, ValueError):
            restored = False
        owned = ledger.owned()
        if restored and owned is not None and (
            fingerprint(canonical_manifest(owned)) == record["previous"]["firewall"]
            and observe_owned_ipfw(ledger, read_adapter)
                == record["previous"]["firewall"]
        ):
            # Reject the pre-STOP case: the exact original PID/start epochs
            # still running after journal.mark_mutating() do NOT prove that
            # rollback ever occurred. The native verifier additionally
            # attests new epochs and both independent kernel readers.
            saved = inspect_process_evidence(
                Path(process_evidence), Path(previous_backup),
                EXPECTED_SCRIPTS, record["previous"],
            )["observation"]
            original_instances = {
                "engine": saved["engine"]["process"],
                "daemon": saved["supervisor"]["daemon"],
                "monitor": saved["supervisor"]["monitor"],
            }
            current_instances = _live_instances(a)
            if any(current_instances[role] == {
                "pid": original_instances[role]["pid"],
                "start_ns": original_instances[role]["start_ns"],
            } for role in ("engine", "daemon", "monitor")):
                raise NativeForwardApplyError(
                    "original pre-STOP process epochs are not previous rollback"
                )
            if not ready_to_seal or seal is None:
                raise NativeForwardApplyError(
                    "restarted previous Voice requires native kernel security/argv attestation"
                )
            sealed = seal(config_fd)
            if sealed.get("whole_intent_phase") != "rolled_back" or (
                journal.read() is None
                or journal.read()["phase"] != "rolled_back"
                or mutating_predecessor(journal.read()) != record
                or probe.observe_processes() != a
            ):
                raise NativeForwardApplyError(
                    "interrupted previous recovery failed durable closure"
                )
            return {
                "state": "forward-failed-five-previous-domains-observed",
                "whole_phase": "rolled_back",
                "safe_to_enable_voice": False,
                "requires_durable_previous_finalization": False,
                "requires_owner_acceptance": True,
            }

    candidate_stop_proof = None
    if a["engine"]["state"] == "stopped" and (
        a["supervisor"]["state"] == "stopped"
    ):
        pass  # global ps + all three pidfile absence was independently verified
    else:
        instances = _live_instances(a)
        argv, argv_sha, _, _ = _current_engine_args(Path(active_runtime))
        if argv_sha != record["candidate"]["native_argv_sha256"] or (
            observe_live_files(
                Path(staged_config), Path(active_runtime),
            )["runtime"] != record["candidate"]["candidate_runtime_sha256"]
        ):
            raise NativeForwardApplyError("candidate runtime not sealed before rollback stop")
        for role, identity in instances.items():
            expected = (
                argv if role == "engine"
                else canonical_supervisor_argv(EXPECTED_SCRIPTS)[role]
            )
            if kernel_reader.argv(identity["pid"]) != expected or (
                kernel_reader.binary(identity["pid"]) != SYSTEM_PATHS[role]
            ):
                raise NativeForwardApplyError("foreign candidate kernel argv/image before stop")
        if probe.observe_processes() != a:
            raise NativeForwardApplyError("candidate process PID/start changed before stop")
        # Pass the pinned exact native inventory all the way into the
        # independently gated shell actuator, not just its upper preflight.
        candidate_stop_proof = {
            "expected_instances": instances,
            "kernel_reader": kernel_reader,
            "expected_argv": {
                "engine": argv,
                **canonical_supervisor_argv(EXPECTED_SCRIPTS),
            },
        }
    # Borrow the existing Config FD. Do not create a new process actuator,
    # do not take a second flock, and never pass test callbacks into the
    # real recovery executor. All runtime/kernel/file mutations are delegated
    # to the established five-resource rollback primitive.
    result = restore_previous_five_resources(
        journal=journal, ledger=ledger,
        previous_backup=Path(previous_backup),
        install_image=Path(install_image),
        process_evidence=Path(process_evidence),
        expected_scripts=EXPECTED_SCRIPTS,
        config_path=Path(config_path), active_runtime=Path(active_runtime),
        expected_owner=config_owner,
        expected_candidate_runtime_sha256=checked["candidate_runtime_sha256"],
        candidate_proof=checked["native_candidate_proof"],
        process_probe=probe, read_ipfw_adapter=read_adapter,
        write_ipfw_adapter=write_adapter,
        require_lifecycle_owner=require_lifecycle_owner,
        process_actions_factory=lambda borrowed: actions if borrowed == config_fd else None,
        expected_candidate_stop_proof=candidate_stop_proof,
        locked_config_fd=config_fd,
        seal_previous=seal,
    )
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    final = journal.read()
    phase = result.get("whole_intent_phase")
    if result.get("state") != "five-previous-domains-observed" or (
        result.get("safe_to_enable_voice") is not False
        or ledger.pending() is not None
        or phase not in ("mutating", "rolled_back")
    ):
        raise NativeForwardApplyError("failed Voice forward rollback not independently verified")
    if phase == "rolled_back":
        if not ready_to_seal or final is None or (
            final["phase"] != "rolled_back"
            or mutating_predecessor(final) != record
        ):
            raise NativeForwardApplyError("foreign terminal rollback after candidate stop")
    elif ready_to_seal or final != record:
        raise NativeForwardApplyError("native previous recovery receipt missing or intent changed")
    return {
        "state": "forward-failed-five-previous-domains-observed",
        "whole_phase": phase,
        "safe_to_enable_voice": False,
        "requires_durable_previous_finalization": phase != "rolled_back",
        "requires_owner_acceptance": True,
    }


def execute_prepared_voice_apply(
    *, journal, ledger, previous_backup, process_evidence,
    security_evidence, install_image, config_path, active_runtime, staged_config,
    candidate_runtime, desired_manifest, probe, kernel_reader,
    read_adapter, write_adapter, require_lifecycle_owner,
    actions_factory, config_owner, engine_runner=None,
    supervisor_runner=None, engine_actuator=SCRIPT,
    supervisor_actuator=SCRIPT,
):
    """Compose ALL existing real native forward stages under ONE Config fd.

    Caller MUST already own original FD9 for the entire function and have
    an audited, root-controlled actions_factory that binds this exact
    supplied Config descriptor to native process security evidence.
    This private API has no OS entrypoint. After a MUTATING failure, use
    ONLY the existing independently gated five-resource rollback with the
    SAME FD; incomplete native process/redo/owner evidence remains blocked.
    An already COMMITTED transaction is never rolled back: retry only its
    verified IPFW postcommit finish using the same lock and executor.
    An interrupted MUTATING transaction re-enters the established guarded
    previous five-resource rollback with the original locked Config fd,
    NEVER the forward mutation chain. An already ROLLED_BACK terminal is
    inspected READ-ONLY using the existing boot/terminal receipt/cleanup
    proof under that SAME Config lock: never another actuator, IPFW change,
    service start or implicit Voice ON.
    """
    _authorities(
        journal=journal, ledger=ledger, probe=probe, kernel_reader=kernel_reader,
        read_adapter=read_adapter, write_adapter=write_adapter,
        previous_backup=previous_backup,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if not callable(actions_factory) or (
        type(config_owner) is not tuple or len(config_owner) != 2
        or any(type(n) is not int or n < 0 for n in config_owner)
    ):
        raise NativeForwardApplyError("native Config and process owner required")
    config_path = Path(config_path)
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    require_lifecycle_owner()
    fd = os.open(config_path, flags)
    try:
        _pinned_regular(config_path, fd, owner=config_owner)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _locked_config(config_path, fd, config_owner)
        record = journal.read()
        if record is not None and record["phase"] == "rolled_back":
            # A crash immediately AFTER durable ROLLED_BACK must not try
            # PREPARED/COMMITTED apply or repeat the previous engine stop.
            # Reuse the existing read-only terminal proof, not an invented
            # second process/IPFW/Config ownership mechanism. A cold boot
            # with a different process epoch or unknown kernel remains
            # manual-review, never a success or service readiness.
            if record["schema"] != RUNTIME_BOUND_SCHEMA or (
                record["candidate"][BOUND_FIELD] != fingerprint(
                    canonical_manifest(desired_manifest)
                )
            ):
                raise NativeForwardApplyError("foreign rolled-back Voice intent")
            review = inspect_boot_recovery(
                journal=journal, ledger=ledger,
                previous_backup=Path(previous_backup),
                process_evidence=Path(process_evidence),
                security_evidence=Path(security_evidence),
                install_image=Path(install_image),
                config_path=config_path, active_runtime=Path(active_runtime),
                probe=probe, adapter=read_adapter,
                config_fd=fd, config_owner=config_owner,
                require_lifecycle_owner=require_lifecycle_owner,
            )
            if review["state"] != (
                "previous-rollback-sealed-needs-manual-finalization"
            ) or any((
                review.get("phase") != "rolled_back",
                review.get("config") != "previous",
                review.get("runtime") != "previous",
                review.get("kernel") != "previous",
                review.get("processes") != "running",
                review.get("previous_receipt") != "process-epoch-matches-not-readiness",
                review.get("cleanup_plan") != "prepared-only",
                review.get("voice_on") is not False,
                review.get("safe_to_close_intent") is not False,
                journal.read() != record,
                ledger.pending() is not None,
            )):
                raise NativeForwardApplyError(
                    "terminal Voice rollback cannot be re-attested; manual review"
                )
            return {
                "state": "native-voice-rolled-back-read-only-verified",
                "whole_phase": "rolled_back",
                "safe_to_enable_voice": False,
                "safe_to_close_intent": False,
                "requires_owner_acceptance": True,
                "process_action_performed": False,
                "ipfw_mutation_performed": False,
            }
        # A retry after the durable WHOLE COMMIT is FORWARD-ONLY. Re-enter
        # the same private FD9+Config-lock executor; do not re-run stop,
        # runtime/Config writes, IPFW activation or old-state rollback.
        if record is not None and record["phase"] == "committed":
            if record["schema"] != RUNTIME_BOUND_SCHEMA or (
                record["candidate"][BOUND_FIELD] != fingerprint(
                    canonical_manifest(desired_manifest)
                )
            ):
                raise NativeForwardApplyError("foreign committed Voice intent")
            return resume_committed_forward_voice_apply(
                journal=journal, ledger=ledger, previous_backup=previous_backup,
                config_path=config_path, config_fd=fd, config_owner=config_owner,
                staged_config=staged_config, candidate_runtime=candidate_runtime,
                active_runtime=active_runtime, desired_manifest=desired_manifest,
                probe=probe, kernel_reader=kernel_reader,
                read_adapter=read_adapter, write_adapter=write_adapter,
                require_lifecycle_owner=require_lifecycle_owner,
            )
        if record is None or record["phase"] not in ("prepared", "mutating") or (
            record["schema"] != RUNTIME_BOUND_SCHEMA
            or record["candidate"][BOUND_FIELD] != fingerprint(
                canonical_manifest(desired_manifest)
            )
            or (record["phase"] == "prepared" and ledger.pending() is not None)
        ):
            raise NativeForwardApplyError(
                "no sealed PREPARED/MUTATING schema-4 native forward intent"
            )
        original = bound_resource_fingerprints(
            Path(previous_backup), record["previous"],
        )
        if observe_live_files(
            Path(install_image) / "config.xml", Path(install_image) / "runtime",
            previous_backup=Path(previous_backup),
        ) != original:
            raise NativeForwardApplyError(
                "previous install image is not sealed before any Voice mutation"
            )
        actions = actions_factory(fd)
        if not isinstance(actions, FreeBSDVoiceProcessActions) or (
            actions.config_fd != fd or actions.journal is not journal
            or actions.probe is not probe
            or actions.previous_backup != Path(previous_backup)
            or actions.config_path != config_path
            or actions.active_runtime != Path(active_runtime)
        ):
            raise NativeForwardApplyError("process actions not bound to this Config lock")
        common = dict(
            journal=journal, ledger=ledger, previous_backup=previous_backup,
            active_runtime=active_runtime, staged_config=staged_config,
            candidate_runtime=candidate_runtime, config_path=config_path,
            probe=probe, kernel_reader=kernel_reader,
            config_fd=fd, config_owner=config_owner,
            require_lifecycle_owner=require_lifecycle_owner,
        )
        if record["phase"] == "mutating":
            # A power cut after the first irreversible stop MUST NOT replay
            # forward work. Delegate only to the established five-resource
            # previous rollback with the SAME original locked Config fd.
            # Its independent native process/kernel/IPFW/redo preflight can
            # refuse a partial or foreign state without touching services.
            try:
                rollback_failed_precommit_voice_apply(
                    journal=journal, ledger=ledger,
                    previous_backup=previous_backup,
                    process_evidence=process_evidence,
                    security_evidence=security_evidence,
                    install_image=install_image, config_path=config_path,
                    active_runtime=active_runtime, staged_config=staged_config,
                    config_fd=fd, config_owner=config_owner,
                    probe=probe, kernel_reader=kernel_reader,
                    read_adapter=read_adapter, write_adapter=write_adapter,
                    require_lifecycle_owner=require_lifecycle_owner,
                    actions=actions,
                )
            except Exception as recovery_error:
                raise NativeForwardApplyError(
                    "interrupted MUTATING Voice recovery refused; "
                    "journal retained for manual review"
                ) from recovery_error
            raise NativeForwardApplyError(
                "interrupted MUTATING Voice forward recovered previous domains; "
                "Voice ON remains refused pending durable finalization"
            )
        try:
            stop_previous_and_install_forward_runtime(
                **common, process_evidence=process_evidence,
                security_evidence=security_evidence, actions=actions,
                ipfw_adapter=read_adapter,
            )
            start_forward_candidate_engine(
                **common, read_ipfw_adapter=read_adapter,
                runner=engine_runner, actuator=engine_actuator,
            )
            install_forward_voice_ipfw(
                **common, desired_manifest=desired_manifest,
                readonly_adapter=read_adapter, mutating_adapter=write_adapter,
            )
            start_forward_voice_supervisor(
                **common, desired_manifest=desired_manifest,
                readonly_adapter=read_adapter, runner=supervisor_runner,
                actuator=supervisor_actuator,
            )
            persist_forward_candidate_config(
                **{k: v for k, v in common.items() if k != "config_fd"},
                locked_config_fd=fd, desired_manifest=desired_manifest,
                readonly_adapter=read_adapter,
            )
            return commit_forward_voice_apply(
                **{k: v for k, v in common.items() if k != "config_fd"},
                config_fd=fd, desired_manifest=desired_manifest,
                read_adapter=read_adapter, write_adapter=write_adapter,
            )
        except Exception as forward_error:
            # Nothing after a durable whole COMMIT may run previous recovery:
            # an incomplete IPFW postcommit must instead be reconciled forward.
            # An unmodified PREPARED intent similarly never stops the old
            # live service simply because a preflight failed.
            require_lifecycle_owner()
            _locked_config(config_path, fd, config_owner)
            unfinished = journal.read()
            if unfinished is None or unfinished["schema"] != RUNTIME_BOUND_SCHEMA or (
                unfinished["previous"] != record["previous"]
                or unfinished["candidate"] != record["candidate"]
            ):
                raise NativeForwardApplyError(
                    "forward failed with foreign/unreadable cutover; manual review"
                ) from forward_error
            if unfinished["phase"] != "mutating":
                raise
            try:
                recovery = rollback_failed_precommit_voice_apply(
                    journal=journal, ledger=ledger,
                    previous_backup=previous_backup,
                    process_evidence=process_evidence,
                    security_evidence=security_evidence,
                    install_image=install_image,
                    config_path=config_path, active_runtime=active_runtime,
                    staged_config=staged_config,
                    config_fd=fd, config_owner=config_owner,
                    probe=probe, kernel_reader=kernel_reader, read_adapter=read_adapter,
                    write_adapter=write_adapter,
                    require_lifecycle_owner=require_lifecycle_owner,
                    actions=actions,
                )
            except Exception as recovery_error:
                raise NativeForwardApplyError(
                    "Voice forward failed and safe rollback was refused; "
                    "MUTATING intent retained for manual recovery"
                ) from recovery_error
            require_lifecycle_owner()
            _locked_config(config_path, fd, config_owner)
            final = journal.read()
            # The lower five-resource executor already verifies the
            # previous state, receipt and terminal proof. Check its durable
            # phase is consistent before reporting completion to the future
            # GUI/service: a successful terminal rollback is NOT MUTATING,
            # and neither result authorizes Voice ON.
            if recovery.get("state") != "forward-failed-five-previous-domains-observed" or (
                recovery.get("safe_to_enable_voice") is not False
                or recovery.get("whole_phase") not in ("mutating", "rolled_back")
            ):
                raise NativeForwardApplyError(
                    "forward rollback result is not a verified previous state"
                ) from forward_error
            if recovery["whole_phase"] == "rolled_back":
                if final is None or final["phase"] != "rolled_back" or (
                    mutating_predecessor(final) != unfinished
                ):
                    raise NativeForwardApplyError(
                        "forward rollback terminal result disagrees with journal"
                    ) from forward_error
                raise NativeForwardApplyError(
                    "Voice forward failed; five previous domains durably "
                    "ROLLED_BACK; Voice ON refused pending owner acceptance"
                ) from forward_error
            if final != unfinished:
                raise NativeForwardApplyError(
                    "forward rollback MUTATING result disagrees with journal"
                ) from forward_error
            raise NativeForwardApplyError(
                "Voice forward failed; all previous five domains restored, "
                "but MUTATING intent retained until durable finalization"
            ) from forward_error
    finally:
        os.close(fd)
