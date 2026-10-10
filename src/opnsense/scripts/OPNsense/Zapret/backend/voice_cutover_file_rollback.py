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
from voice_cutover_runtime_restore import restore_previous_runtime
from voice_native_file_observer import observe_live_files


class VoiceFileRollbackError(RuntimeError):
    """Never close or abort the whole journal on partial file restoration."""


def restore_previous_files(
    config_path: Path, active_runtime: Path, install_image: Path,
    previous_backup: Path, journal: VoiceCutoverJournal, *,
    expected_owner: tuple[int, int],
    expected_candidate_runtime_sha256: str,
    require_lifecycle_owner: Callable[[], None],
    require_quiescent: Callable[[], bool],
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
    fd = os.open(config_path, flags)
    try:
        _pinned_regular(config_path, fd, owner=expected_owner)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise VoiceFileRollbackError(
                    "another OPNsense Config writer owns the flock"
                ) from exc
            raise
        initial = _pinned_regular(config_path, fd, owner=expected_owner)
        gate()
        if journal.read() != original:
            raise VoiceFileRollbackError("whole Voice intent changed after Config lock")

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
        os.close(fd)
