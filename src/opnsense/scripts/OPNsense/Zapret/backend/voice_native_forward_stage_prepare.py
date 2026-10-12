#!/usr/bin/env python3
"""Stage 3: write-once candidate stage + existing schema-4 PREPARED journal.

PRIVATE import-only handoff, not an autonomous CLI/configd/GUI/boot command.
Caller owns original FD9 AND the original Config flock for the entire call.
No process, active Config/runtime or IPFW kernel mutation. On ANY failure,
leave previously fsync'd stage/journal evidence available for operator review;
do not auto-delete an unknown partial forward candidate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile

from voice_cutover_backup import _copy_regular, _private_dir, _sync_dir
from voice_cutover_journal import VoiceCutoverJournal
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import _copy_candidate
from voice_native_recovery_quiescence import _locked_config
from voice_native_forward_prepare import prepare_forward_voice_intent
from voice_native_apply_route import sealed_prepared_handoff, STAGE

MANIFEST_FILE = "desired-ipfw.json"
TEMP_PREFIX = ".forward-candidate-"
RESTORE_STAGE = "restore-stage"
RESTORE_IMAGE = "restore-install-image"


class NativeVoiceStagePrepareError(RuntimeError):
    pass


def prepare_staged_forward_voice_intent(
    *, journal: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    previous_backup, process_evidence, security_evidence, previous_observer,
    config_path, active_runtime, source_config, source_runtime,
    proof, desired_manifest, expected_scripts, ipfw_adapter,
    config_fd, config_owner, require_lifecycle_owner,
) -> dict:
    """Copy a distinct precompiled release and journal it with original owner.

    The prior five-resource snapshot, native previous observer and previous
    IPFW ownership are validated by the ORIGINAL forward PREPARED writer.
    This function does not duplicate that policy. The source paths are
    internal, already compiled candidate artifacts, never CLI arguments.
    """
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not callable(require_lifecycle_owner)
    ):
        raise NativeVoiceStagePrepareError("invalid native preparation authorities")
    config_path, active_runtime = Path(config_path), Path(active_runtime)
    source_config, source_runtime = Path(source_config), Path(source_runtime)
    root = journal.directory
    stage = root / STAGE
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _private_dir(root)
    if source_config == config_path or source_runtime == active_runtime or (
        not source_config.is_absolute() or not source_runtime.is_absolute()
        or stage.is_symlink() or os.path.lexists(stage)
        or journal.read() is not None or ledger.pending() is not None
    ):
        raise NativeVoiceStagePrepareError("candidate is not a fresh detached release")
    if any(name.startswith(TEMP_PREFIX) for name in os.listdir(root)):
        raise NativeVoiceStagePrepareError("unresolved previous candidate staging residue")
    # The five-resource executor requires this immutable previous install image
    # before MUTATING. Unknown prior images must never be overwritten/adopted.
    if os.path.lexists(root / RESTORE_STAGE) or os.path.lexists(root / RESTORE_IMAGE):
        raise NativeVoiceStagePrepareError("previous recovery image already exists")
    desired = canonical_manifest(desired_manifest)
    if desired["rule_base"] != 19000 or desired["rule_max"] != 19010 or (
        not desired["rules"] or not desired["tables"]
    ):
        raise NativeVoiceStagePrepareError("unsupported candidate IPFW ownership")
    before = observe_live_files(source_config, source_runtime)
    if before["config"] != proof.get("saved_xml_sha256"):
        raise NativeVoiceStagePrepareError("candidate Config does not match its proof")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    # A persistent private same-parent working directory ensures that a power
    # cut never makes a partial stage look like a published one.
    temp = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=root))
    try:
        os.chmod(temp, 0o700)
        src = os.lstat(source_config)
        if not stat.S_ISREG(src.st_mode) or src.st_uid != os.geteuid() or (
            src.st_nlink != 1
        ):
            raise NativeVoiceStagePrepareError("untrusted candidate Config source")
        _copy_regular(source_config, temp / "config.xml", src)
        os.chmod(temp / "config.xml", stat.S_IMODE(src.st_mode))
        _copy_candidate(source_runtime, temp / "runtime")
        encoded = (json.dumps(
            canonical_manifest(desired_manifest), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        ) + "\n").encode("ascii")
        with (temp / MANIFEST_FILE).open("xb") as target:
            target.write(encoded)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temp / MANIFEST_FILE, 0o600)
        _sync_dir(temp)
        copied = observe_live_files(temp / "config.xml", temp / "runtime")
        if copied != before or observe_live_files(source_config, source_runtime) != before:
            raise NativeVoiceStagePrepareError("candidate source or staged bytes drifted")
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        if os.path.lexists(stage) or journal.read() is not None or ledger.pending() is not None:
            raise NativeVoiceStagePrepareError("another Voice cutover claimed candidate")
        os.rename(temp, stage)
        _sync_dir(root)
    except BaseException:
        # Intentionally never remove unknown on-disk partial evidence.
        raise
    result = prepare_forward_voice_intent(
        journal=journal, ledger=ledger, previous_backup=previous_backup,
        process_evidence=process_evidence, security_evidence=security_evidence,
        previous_observer=previous_observer,
        config_path=config_path, active_runtime=active_runtime,
        staged_config=stage / "config.xml", candidate_runtime=stage / "runtime",
        proof=proof, desired_manifest=desired_manifest,
        expected_scripts=expected_scripts, ipfw_adapter=ipfw_adapter,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if result.get("state") != "native-voice-forward-prepared-not-mutating" or (
        canonical_manifest(sealed_prepared_handoff(journal, stage)) != desired
    ):
        raise NativeVoiceStagePrepareError("journal does not bind published Voice stage")
    # PREPARED is now fsync'd. Reuse the existing mode-accurate previous
    # recovery staging primitives before any future path can enter MUTATING.
    # An interrupted/power-cut stage/image is RETAINED for operator review,
    # not cleaned up or silently adopted by a later attempt.
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    record = journal.read()
    if record is None or record["phase"] != "prepared" or (
        record["check"] != result["whole_check"]
    ):
        raise NativeVoiceStagePrepareError("forward journal changed before recovery image")
    old_files = {key: record["previous"][key] for key in ("config", "runtime")}
    staged_recovery = prepare_restore_stage(
        previous_backup, root / RESTORE_STAGE, record["previous"],
    )
    if staged_recovery["previous"] != old_files or (
        staged_recovery["activation_authorized"] is not False
    ):
        raise NativeVoiceStagePrepareError("old Config/runtime stage not bound")
    image = prepare_installable_restore(
        root / RESTORE_STAGE, root / RESTORE_IMAGE, record["previous"],
    )
    if image["previous"] != old_files or image["activation_authorized"] is not False:
        raise NativeVoiceStagePrepareError("old recovery install image not bound")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if journal.read() != record or ledger.pending() is not None or (
        canonical_manifest(sealed_prepared_handoff(journal, stage)) != desired
    ):
        raise NativeVoiceStagePrepareError("Voice recovery image or prepared intent raced")
    if observe_live_files(
        root / RESTORE_IMAGE / "config.xml",
        root / RESTORE_IMAGE / "runtime",
        previous_backup=previous_backup,
    ) != old_files:
        raise NativeVoiceStagePrepareError("previous recovery image changed after publish")
    return {
        "state": "native-voice-stage-and-forward-prepared",
        "previous_install_image": "sealed-not-installed",
        "whole_check": result["whole_check"],
        "candidate_runtime_sha256": result["candidate_runtime_sha256"],
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }
