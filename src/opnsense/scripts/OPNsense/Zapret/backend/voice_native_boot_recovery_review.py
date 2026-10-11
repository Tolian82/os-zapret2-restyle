#!/usr/bin/env python3
"""Cold-boot Voice crash classification under existing FD9 and Config flock.

This is READ-ONLY even when real Config/runtime have been partially written.
The existing service's legacy start is already blocked by
voice_cutover_guard.py when any whole intent persists. Never auto-start,
auto-stop, mutate IPFW, delete a redo, or close the whole journal here.

The exact schema-4 journal, sealed prior files/security, both redo records,
native process inventory and previous IPFW owner are cross-checked. A boot
with a reset/unknown IPFW kernel is intentionally NOT auto-replayed.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA, BOUND_FIELD, bound_candidate_runtime, VoiceCutoverJournal
from voice_cutover_config_redo import ConfigRestoreRedo, may_resume_partial
from voice_cutover_runtime_restore import _read_redo
from voice_cutover_config_restore import _pinned_regular
from voice_native_file_observer import _hash_file, observe_live_files
from voice_native_recovery_quiescence import _locked_config, EXPECTED_SCRIPTS, PIDFILES
from voice_process_recovery_evidence import inspect_process_evidence
from voice_security_policy_evidence import SUPERVISOR_BOUND_POLICY_SCHEMA, inspect_security_policy
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_firewall_ledger import VoiceOwnershipStore, decode_manifest, canonical_manifest, fingerprint
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native


class BootReviewError(RuntimeError):
    pass


def _state(value: str, **fields):
    return {
        "state": value, "safe_to_start": False, "safe_to_rollback_automatically": False,
        "safe_to_close_intent": False, "voice_on": False, **fields,
    }


def inspect_boot_recovery(
    *, journal: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    previous_backup: Path, process_evidence: Path, security_evidence: Path,
    install_image: Path, config_path: Path, active_runtime: Path,
    probe: FreeBSDVoiceProcessProbe, adapter: FreeBSDIPFWAdapter,
    config_fd: int, config_owner: tuple[int,int],
    require_lifecycle_owner,
) -> dict:
    """Read-only exact crash evidence; caller owns FD9 and Config flock."""
    if not callable(require_lifecycle_owner) or (
        not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or Path(probe.previous_backup) != Path(previous_backup)
        or not isinstance(adapter, FreeBSDIPFWAdapter)
        or adapter.allow_mutations is not False
        or (adapter.rule_base, adapter.rule_max) != (19000,19010)
    ):
        raise BootReviewError("native read-only process/IPFW witnesses required")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record=journal.read()
    pending=ledger.pending()
    if record is None:
        if pending is not None:
            return _state("blocked", reason="orphan-ipfw-intent")
        return _state("no-whole-intent", reason="native-journal-absent")
    if record["phase"] != "mutating" or record["schema"] != RUNTIME_BOUND_SCHEMA:
        return _state("blocked", reason="no-schema4-mutating-cutover",
                      phase=record["phase"], schema=record["schema"])
    candidate_sha=bound_candidate_runtime(record)
    old=bound_resource_fingerprints(Path(previous_backup),record["previous"])
    prior_process=inspect_process_evidence(
        process_evidence, previous_backup, EXPECTED_SCRIPTS, record["previous"],
    )
    if prior_process["observation"]["engine"]["state"] != "running":
        raise BootReviewError("previous process topology is not one running engine")
    policy=inspect_security_policy(
        security_evidence, previous_backup, process_evidence,
        journal_record=record, expected_scripts=EXPECTED_SCRIPTS,
    )
    if policy["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA or (
        policy["policy"]["supervisor_argv"] != canonical_supervisor_argv(EXPECTED_SCRIPTS)
    ):
        raise BootReviewError("missing SHA-bound supervisor restart policy")
    if observe_live_files(
        Path(install_image)/"config.xml",Path(install_image)/"runtime",
        previous_backup=previous_backup,
    ) != old:
        raise BootReviewError("sealed previous install image differs")
    config_redo=ConfigRestoreRedo(journal.directory).read()
    runtime_redo=_read_redo(journal.directory)
    if config_redo is not None and (
        config_redo["cutover_check"] != record["check"]
        or config_redo["previous_sha256"] != record["previous"]["config"]
        or config_redo["before_sha256"] != record["candidate"]["saved_xml_sha256"]
    ):
        raise BootReviewError("Config redo belongs to a different cutover")
    if runtime_redo is not None and (
        runtime_redo["cutover_check"] != record["check"]
        or runtime_redo["candidate_sha256"] != candidate_sha
        or runtime_redo["previous_sha256"] != record["previous"]["runtime"]
        or runtime_redo["active_name"] != Path(active_runtime).name
    ):
        raise BootReviewError("runtime redo belongs to a different cutover")

    # Config is readable even when an interrupted ftruncate left a prefix:
    # use the pinned, borrowed flock descriptor and matching old-byte source.
    _pinned_regular(Path(config_path),config_fd,owner=config_owner)
    config_sha=_hash_file(Path(config_path))[0]
    if config_sha == old["config"]:
        config_status="previous"
    elif config_sha == record["candidate"]["saved_xml_sha256"]:
        config_status="candidate"
    elif config_redo is not None:
        source=os.open(Path(install_image)/"config.xml",
                       os.O_RDONLY | getattr(os,"O_NOFOLLOW",0))
        try:
            if may_resume_partial(
                config_redo, journal_record=record,
                live_info=os.fstat(config_fd),live_fd=config_fd,
                source_fd=source,
                saved_bytes=os.fstat(source).st_size,
            ):
                config_status="armed-previous-prefix"
            else:
                config_status="foreign"
        finally:
            os.close(source)
    else:
        config_status="foreign"

    # Never guess the digest from a missing runtime after the first rename.
    # The pending record contains the ONLY trusted candidate-tree digest.
    runtime_path=Path(active_runtime)
    if not runtime_path.exists() and not runtime_path.is_symlink():
        runtime_status="missing-after-rename" if runtime_redo else "missing-unowned"
    else:
        observed=observe_live_files(Path(install_image)/"config.xml",runtime_path)
        if observed["runtime"] == old["runtime"]:
            runtime_status="previous"
        elif observed["runtime"] == candidate_sha:
            runtime_status="candidate"
        else:
            runtime_status="foreign"
    if runtime_redo:
        info=os.lstat(runtime_path.parent)
        if (runtime_redo["parent_dev"],runtime_redo["parent_ino"]) != (
            info.st_dev,info.st_ino
        ):
            raise BootReviewError("runtime redo parent inode changed")
        # A caller cannot substitute custom ready/retired target paths.
        suffix=record["check"][:20]
        if runtime_redo["ready_name"]!=".voice-restore-ready-"+suffix or (
            runtime_redo["retired_name"]!=".voice-restore-retired-"+suffix
        ):
            raise BootReviewError("runtime redo recovery paths differ from sealed intent")

    first=probe.probe()
    second=probe.probe()
    if first != second:
        raise BootReviewError("process inventory changed during boot review")
    processes=first["engine"]["state"]
    if processes not in ("stopped","running") or first["supervisor"]["state"]!=processes:
        raise BootReviewError("mixed or invalid Voice engine/supervisor boot state")
    owned=ledger.owned()
    if owned is None or fingerprint(canonical_manifest(owned)) != (
        record["previous"]["firewall"]
    ):
        raise BootReviewError("previous Voice IPFW owner changed on disk")
    if pending is not None:
        if pending["phase"] != "mutating" or (
            pending["previous_sha256"] != record["previous"]["firewall"]
        ) or pending["desired_sha256"] != record["candidate"][BOUND_FIELD] or (
            decode_manifest(pending["previous"]) != owned
        ):
            raise BootReviewError("IPFW journal no longer belongs to whole cutover")
        kernel="pending-unverified"
    else:
        try:
            if observe_owned_ipfw(ledger,adapter) != record["previous"]["firewall"]:
                raise BootReviewError("kernel IPFW does not match previous owner")
        except (ValueError,RuntimeError,OSError):
            kernel="unknown-or-reset"
        else:
            kernel="previous"

    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    if journal.read()!=record or ledger.owned()!=owned or ledger.pending()!=pending:
        raise BootReviewError("cutover journals changed during boot review")
    if ConfigRestoreRedo(journal.directory).read()!=config_redo or (
        _read_redo(journal.directory)!=runtime_redo
    ):
        raise BootReviewError("Voice redo changed during boot review")
    # This is intentionally NOT a readiness report. Even a complete-looking
    # previous state requires independent native post-reboot image/argv attest.
    status=("previous-files-and-kernel-observed"
            if config_status=="previous" and runtime_status=="previous"
            and kernel=="previous" and processes=="running"
            else "manual-recovery-required")
    return _state(
        status, reason="durable-voice-intent-retained", phase="mutating",
        config=config_status,runtime=runtime_status,processes=processes,
        kernel=kernel,config_redo="present" if config_redo else "absent",
        runtime_redo="present" if runtime_redo else "absent",
        candidate_runtime_sha256=candidate_sha,
    )


def main(argv:list[str])->int:
    if len(argv)!=2 or argv[1]!="inspect":
        print("usage: voice_native_boot_recovery_review.py inspect",file=sys.stderr)
        return 64
    try:
        native.require_native_lock()
        journal=VoiceCutoverJournal(native.WHOLE)
        ledger=VoiceOwnershipStore(native.LEDGER)
        prior=native.WHOLE/"previous"
        probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS,PIDFILES,prior)
        fd=os.open(native.CONFIG, os.O_RDWR | getattr(os,"O_NOFOLLOW",0))
        try:
            import fcntl
            fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            result=inspect_boot_recovery(
                journal=journal, ledger=ledger, previous_backup=prior,
                process_evidence=native.WHOLE/"process-evidence",
                security_evidence=native.WHOLE/"process-security-policy",
                install_image=native.WHOLE/"restore-install-image",
                config_path=native.CONFIG,active_runtime=native.ACTIVE_ROOT,
                probe=probe,adapter=FreeBSDIPFWAdapter(19000,19010),
                config_fd=fd,config_owner=(0,0),
                require_lifecycle_owner=native.require_native_lock,
            )
        finally:
            os.close(fd)
        print("native-voice-boot-review="+result["state"])
        print("native-voice-boot-reason="+result["reason"])
        print("voice-on=blocked")
        return 0 if result["state"]=="no-whole-intent" else 69
    except (OSError,ValueError,RuntimeError) as exc:
        print("ERROR: native Voice boot review refused: "+str(exc),file=sys.stderr)
        return 69


if __name__=="__main__":
    raise SystemExit(main(sys.argv))
