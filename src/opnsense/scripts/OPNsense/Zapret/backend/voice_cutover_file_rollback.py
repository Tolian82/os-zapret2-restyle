#!/usr/bin/env python3
"""Real two-file-domain rollback while holding ONE OPNsense Config flock.

An isolated filesystem transaction primitive with NO native service action,
GUI path or boot replay. The eventual FreeBSD owner MUST call through the
verified FD9 lifecycle lease and a native process/kernel quiescence observer.
The injected witnesses here are for offline regression only.

This restorer deliberately leaves both redo files, retired candidate runtime
and the whole journal in MUTATING. Config+runtime alone are NOT sufficient to
clear intent or restart Voice: dvtws2, supervisor and IPFW must be restored and
independently verified under the same lifecycle authority.
"""
from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
from typing import Callable

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import (
    VoiceConfigRestoreError, _pinned_regular, restore_previous_config_in_place,
)
from voice_cutover_journal import VoiceCutoverJournal
from voice_cutover_runtime_restore import restore_previous_runtime, _sync_dir, _read_redo as read_restore_redo
from voice_native_forward_runtime import _read_redo as read_forward_redo
from voice_native_file_observer import observe_live_files


class VoiceFileRollbackError(RuntimeError):
    """Never close or abort the whole journal on partial file restoration."""


def _complete_interrupted_forward_rename(
    *, active: Path, install_image: Path, previous_backup: Path,
    journal: VoiceCutoverJournal, locked_config_fd: int, config_path: Path,
    config_owner: tuple[int, int], require_lifecycle_owner,
    require_quiescent,
) -> str:
    """Resume ONLY the missing-active forward rename under original locks.

    Power loss after previous->retained but before ready->active leaves
    active absent. The original write-ahead forward redo and BOTH unchanged
    directories prove this exact state. Publish the verified candidate tree
    while processes are stopped and the previous IPFW is already restored;
    then hand control back to the ordinary five-resource rollback. No new
    Config write, engine start, IPFW mutation or journal transition occurs.
    """
    from voice_native_recovery_quiescence import _locked_config
    active=Path(active)
    if os.path.lexists(active):
        return "active-present"
    # A missing active in the middle of a PREVIOUS rollback is handled by
    # the established restore-redo, not misclassified as a forward gap.
    if read_restore_redo(journal.directory) is not None:
        return "previous-restore-redo-owns-missing-active"
    require_lifecycle_owner()
    _locked_config(Path(config_path),locked_config_fd,config_owner)
    if require_quiescent() is not True:
        raise VoiceFileRollbackError("forward rename crash repair requires stopped engine and previous IPFW")
    record=journal.read()
    if record is None or record["phase"]!="mutating" or record["schema"]!=4:
        raise VoiceFileRollbackError("forward rename crash repair requires schema-4 MUTATING")
    sealed=bound_resource_fingerprints(Path(previous_backup),record["previous"])
    redo=read_forward_redo(journal.directory)
    parent=os.lstat(active.parent)
    cfg=os.fstat(locked_config_fd)
    suffix=record["check"][:20]
    ready_name=".voice-forward-ready-"+suffix
    retained_name=".voice-forward-previous-"+suffix
    if redo is None or any((
        redo["whole_check"]!=record["check"],
        redo["candidate_sha256"]!=record["candidate"]["candidate_runtime_sha256"],
        redo["previous_sha256"]!=sealed["runtime"],
        redo["active_name"]!=active.name,
        redo["ready_name"]!=ready_name,
        redo["retained_name"]!=retained_name,
        (redo["config_dev"],redo["config_inode"])!=(cfg.st_dev,cfg.st_ino),
        (redo["parent_dev"],redo["parent_inode"])!=(parent.st_dev,parent.st_ino),
    )):
        raise VoiceFileRollbackError("missing or foreign durable forward runtime redo")
    ready=active.with_name(ready_name)
    retained=active.with_name(retained_name)
    for tree,expected in (
        (ready,record["candidate"]["candidate_runtime_sha256"]),
        (retained,sealed["runtime"]),
    ):
        if tree.is_symlink() or not tree.is_dir() or (
            observe_live_files(
                Path(install_image)/"config.xml",tree,
                **({"previous_backup":previous_backup} if tree==retained else {}),
            )["runtime"]!=expected
        ):
            raise VoiceFileRollbackError("forward crash trees do not match sealed intent")
    require_lifecycle_owner()
    _locked_config(Path(config_path),locked_config_fd,config_owner)
    if require_quiescent() is not True or journal.read()!=record or (
        read_forward_redo(journal.directory)!=redo or os.path.lexists(active)
        or (os.lstat(active.parent).st_dev,os.lstat(active.parent).st_ino)
            !=(parent.st_dev,parent.st_ino)
    ):
        raise VoiceFileRollbackError("forward crash evidence raced before rename")
    os.rename(ready,active)
    _sync_dir(active.parent)
    if observe_live_files(
        Path(install_image)/"config.xml",active
    )["runtime"]!=record["candidate"]["candidate_runtime_sha256"] or (
        os.path.lexists(ready) or journal.read()!=record
    ):
        raise VoiceFileRollbackError("forward crash rename not durably recovered")
    return "candidate-rename-resumed-for-previous-rollback"


def restore_previous_files(
    config_path: Path, active_runtime: Path, install_image: Path,
    previous_backup: Path, journal: VoiceCutoverJournal, *,
    expected_owner: tuple[int, int],
    expected_candidate_runtime_sha256: str,
    require_lifecycle_owner: Callable[[], None],
    require_quiescent: Callable[[], bool],
    locked_config_fd: int | None = None,
) -> dict:
    """Restore both filesystem resources holding one exclusive Config flock.

    The caller MUST prove the actual dvtws2/supervisor are quiescent and
    IPFW previous ownership can be restored; here we can only check the
    injected gate returns literal True. This is not a production adapter.

    Runtime restore runs first so an interrupted directory rename leaves
    the OPNsense Config unchanged. Config restore then runs on the SAME
    locked Config inode with a durable redo. A crash between/inside calls
    can be retried with both redo markers; *neither* is cleared here.
    """
    if not callable(require_lifecycle_owner) or \
       not callable(require_quiescent) or \
       type(expected_owner) is not tuple or len(expected_owner) != 2 or \
       any(type(x) is not int or x < 0 for x in expected_owner):
        raise VoiceFileRollbackError("native lifecycle/quiescence/owner authority required")

    def gate() -> None:
        require_lifecycle_owner()
        if require_quiescent() is not True:
            raise VoiceFileRollbackError(
                "one-engine/supervisor and IPFW quiescence not proven"
            )

    gate()
    original = journal.read()
    if original is None or original.get("phase") != "mutating" or \
       original.get("schema", 0) < 2:
        raise VoiceFileRollbackError("no bound, mutating whole Voice cutover")
    sealed = bound_resource_fingerprints(Path(previous_backup), original["previous"])
    install_image = Path(install_image)
    if observe_live_files(
        install_image / "config.xml", install_image / "runtime",
        previous_backup=previous_backup,
    ) != sealed:
        raise VoiceFileRollbackError("previous install image changed")

    config_path = Path(config_path)
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | \
        getattr(os, "O_CLOEXEC", 0)
    if locked_config_fd is not None and (
        type(locked_config_fd) is not int or locked_config_fd < 0
    ):
        raise VoiceFileRollbackError("invalid borrowed Config descriptor")
    owns_fd = locked_config_fd is None
    fd = os.open(config_path, flags) if owns_fd else locked_config_fd
    try:
        _pinned_regular(config_path, fd, owner=expected_owner)
        if owns_fd:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise VoiceFileRollbackError(
                        "another OPNsense Config writer owns the flock"
                    ) from exc
                raise
        else:
            # A valid FD number or fstat is NOT proof of an acquired flock.
            # The owner above us must keep the same inode locked through
            # process/IPFW, file restoration and native restart verification.
            from voice_native_recovery_quiescence import _locked_config
            _locked_config(config_path, fd, expected_owner)
        initial = _pinned_regular(config_path, fd, owner=expected_owner)
        gate()
        if journal.read() != original:
            raise VoiceFileRollbackError("whole Voice intent changed after Config lock")

        _complete_interrupted_forward_rename(
            active=Path(active_runtime),install_image=install_image,
            previous_backup=Path(previous_backup),journal=journal,
            locked_config_fd=fd,config_path=config_path,
            config_owner=expected_owner,
            require_lifecycle_owner=require_lifecycle_owner,
            require_quiescent=require_quiescent,
        )
        restored_runtime = restore_previous_runtime(
            Path(active_runtime), install_image, Path(previous_backup), journal,
            expected_candidate_runtime_sha256=expected_candidate_runtime_sha256,
            require_lifecycle_owner=require_lifecycle_owner,
        )
        gate()
        if journal.read() != original:
            raise VoiceFileRollbackError("whole Voice journal changed after runtime restore")
        _pinned_regular(config_path, fd, owner=expected_owner)

        restored_config = restore_previous_config_in_place(
            config_path, install_image, Path(previous_backup), journal,
            require_lifecycle_owner=require_lifecycle_owner,
            expected_owner=expected_owner, locked_config_fd=fd,
        )
        gate()
        end = _pinned_regular(config_path, fd, owner=expected_owner)
        if (initial.st_dev, initial.st_ino) != (end.st_dev, end.st_ino):
            raise VoiceFileRollbackError("Config inode changed during file-domain rollback")
        if journal.read() != original:
            raise VoiceFileRollbackError("whole Voice journal changed after Config restore")
        if observe_live_files(
            config_path, Path(active_runtime), previous_backup=previous_backup,
        ) != sealed:
            raise VoiceFileRollbackError("combined previous files failed verification")

        return {
            "state": "previous-files-restored",
            "config": restored_config,
            "runtime": restored_runtime,
            "whole_intent_phase": "mutating",
            "complete_rollback_authorized": False,
            "safe_to_restart_engine": False,
            "safe_to_clear_intent": False,
        }
    finally:
        # This releases only the Config lock held throughout both writes.
        # Original backups, redo and whole intent stay intact for kernel,
        # engine and supervisor restoration in the future coordinator.
        if owns_fd:
            os.close(fd)
