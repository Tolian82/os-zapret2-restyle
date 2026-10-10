#!/usr/bin/env python3
"""Private, non-activating materialization of a sealed previous Voice snapshot.

This staging-only helper copies verified Config/runtime bytes into an
independent 0700 directory. It NEVER touches current config.xml, active
runtime, dvtws2, supervisor or IPFW and has no CLI/production call site.

CALLER of any *future* production restore must hold both native locks,
check all five whole-cutover resource fingerprints and both IPFW journals,
and independently verify process/kernel state before activation.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import tempfile

from voice_cutover_backup import (
    VoiceBackupError, _copy_regular, _private_dir, _regular, _sync_dir,
    bound_resource_fingerprints, inspect_previous,
)


def _copy_checked(source: Path, target: Path, row: dict) -> None:
    """Copy through a no-follow descriptor and pin each file to its digest."""
    info = _regular(source)
    digest, size = _copy_regular(source, target, info)
    if digest != row["sha256"] or size != row["bytes"]:
        raise VoiceBackupError("staged Voice restore bytes differ from sealed snapshot")


def _sync_stage(root: Path) -> None:
    # Each file was already fsync'd while copying. Sync nested directory
    # entries bottom-up before the same-parent, final publication rename.
    for here, dirs, files in os.walk(root, topdown=False, followlinks=False):
        _sync_dir(Path(here))


def prepare_restore_stage(previous_backup: Path, output: Path,
                          expected_previous: dict) -> dict:
    """Safely prepare restorable bytes WITHOUT applying them.

    Private output directory must not exist. Both the source snapshot and
    the new stage are checked against the same manifest and journal's
    previous Config/runtime fingerprints before output is published.
    Metadata modes from the original files remain in the sealed manifest;
    copied staged files intentionally stay 0600 and directories 0700.
    No live-path operations, process control, or kernel operations.
    """
    source = Path(previous_backup)
    output = Path(output)
    original = inspect_previous(source)
    before = bound_resource_fingerprints(source, expected_previous)
    _private_dir(output.parent)
    if output.exists() or output.is_symlink():
        raise VoiceBackupError("Voice restore stage destination already exists")

    temporary = Path(tempfile.mkdtemp(prefix=".voice-restore-stage-",
                                      dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        config_dir = temporary / "config"
        runtime_dir = temporary / "runtime"
        config_dir.mkdir(mode=0o700)
        runtime_dir.mkdir(mode=0o700)
        _copy_checked(source / "config/config.xml",
                      config_dir / "config.xml", original["config"])

        # Iterate the verified source tree rather than trusting path strings
        # from JSON to create files. Extra, missing, changed or linked entries
        # cannot pass the subsequent complete re-inspection.
        for here, dirs, files in os.walk(source / "runtime",
                                         topdown=True, followlinks=False):
            current = Path(here)
            _private_dir(current)
            relative = current.relative_to(source / "runtime")
            target = runtime_dir / relative
            for name in dirs:
                item = current / name
                info = os.lstat(item)
                if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    raise VoiceBackupError("linked or unsafe staged runtime directory")
                if original["runtime"].get((relative / name).as_posix() + "/",
                                           {}).get("type") != "dir":
                    raise VoiceBackupError("unexpected staged runtime directory")
                (target / name).mkdir(mode=0o700)
            for name in files:
                key = (relative / name).as_posix()
                row = original["runtime"].get(key)
                if not isinstance(row, dict) or row.get("type") != "file":
                    raise VoiceBackupError("unexpected staged runtime file")
                _copy_checked(current / name, target / name, row)

        # Publish exact manifest and seal, not a fresh or silently adjusted
        # manifest that could accidentally bless corrupted copied bytes.
        for name in ("manifest.json", "manifest.sha256"):
            source_file = source / name
            info = _regular(source_file)
            _copy_regular(source_file, temporary / name, info)

        if inspect_previous(temporary) != original:
            raise VoiceBackupError("prepared restore stage manifest differs")
        if inspect_previous(source) != original or \
           bound_resource_fingerprints(source, expected_previous) != before:
            raise VoiceBackupError("previous backup changed while staging")
        _sync_stage(temporary)
        if output.exists() or output.is_symlink():
            raise VoiceBackupError("Voice restore destination appeared during staging")
        os.rename(temporary, output)
        _sync_dir(output.parent)
        return {"state": "staged-only", "activation_authorized": False,
                "previous": before, "manifest": original}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
