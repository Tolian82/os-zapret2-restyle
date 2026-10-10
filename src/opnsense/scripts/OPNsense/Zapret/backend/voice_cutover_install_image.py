#!/usr/bin/env python3
"""Build an installable previous Config/runtime image, WITHOUT installing it.

The earlier restore-staged snapshot intentionally stores all bytes as 0600 and
directories as 0700. Those permissions cannot be copied directly into the
running OPNsense tree. Here we materialize the *original modes* in an isolated,
owner-private 0700 parent, then verify them with the independent live-file
observer before durable publication. This module has no CLI, no live mutation,
no process control and no IPFW calls. Native activation remains gated.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import tempfile

from voice_cutover_backup import (
    VoiceBackupError, _private_dir, _sync_dir, bound_resource_fingerprints,
    inspect_previous,
)
from voice_cutover_restore_stage import _copy_checked, _sync_stage
from voice_native_file_observer import observe_live_files


def _restore_mode(path: Path, mode: int, *, directory: bool = False) -> None:
    """Set a sealed mode on the opened inode rather than a pathname symlink."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | \
        getattr(os, "O_CLOEXEC", 0)
    flags |= (getattr(os, "O_DIRECTORY", 0) if directory else
              getattr(os, "O_NONBLOCK", 0))
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or \
           (directory and not stat.S_ISDIR(info.st_mode)) or \
           (not directory and
            (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)):
            raise VoiceBackupError("unsafe Voice install-image inode")
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def prepare_installable_restore(private_stage: Path, output: Path,
                                expected_previous: dict) -> dict:
    """Create a permission-accurate recovery image under a private parent.

    No previous image may be overwritten. The operation consumes ONLY the
    sealed private stage (never live OPNsense paths) and does not activate it.
    Schema 1 lacks original runtime root permissions and cannot be installed.
    File ownership/group still require a separate trusted native owner policy
    and cutover transaction; an image is not authorization for a live swap.
    """
    source, output = Path(private_stage), Path(output)
    original = inspect_previous(source)
    if original["schema"] != 2:
        raise VoiceBackupError("Voice install image requires sealed runtime root mode")
    previous = bound_resource_fingerprints(source, expected_previous)
    _private_dir(output.parent)
    if output.exists() or output.is_symlink():
        raise VoiceBackupError("Voice install image destination already exists")
    temporary = Path(tempfile.mkdtemp(prefix=".voice-install-image-",
                                      dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        runtime = temporary / "runtime"
        runtime.mkdir(mode=0o700)
        _copy_checked(source / "config/config.xml", temporary / "config.xml",
                      original["config"])
        for here, dirs, files in os.walk(source / "runtime", followlinks=False):
            current = Path(here)
            _private_dir(current)
            relative = current.relative_to(source / "runtime")
            target = runtime / relative
            for name in dirs:
                item = current / name
                key = (relative / name).as_posix() + "/"
                info = os.lstat(item)
                if not stat.S_ISDIR(info.st_mode) or \
                   original["runtime"].get(key, {}).get("type") != "dir":
                    raise VoiceBackupError("unsafe Voice install-image directory")
                (target / name).mkdir(mode=0o700)
            for name in files:
                key = (relative / name).as_posix()
                row = original["runtime"].get(key)
                if not isinstance(row, dict) or row.get("type") != "file":
                    raise VoiceBackupError("unexpected Voice install-image file")
                _copy_checked(current / name, target / name, row)

        # Restore files first, subdirectories deepest first, runtime root last.
        # The private parent remains 0700 even if the old payload was public.
        for name, row in original["runtime"].items():
            if row["type"] == "file":
                _restore_mode(runtime / name, row["mode"])
        folders = sorted(
            ((name, row) for name, row in original["runtime"].items()
             if row["type"] == "dir"),
            key=lambda item: len(Path(item[0]).parts), reverse=True,
        )
        for name, row in folders:
            _restore_mode(runtime / name.rstrip("/"), row["mode"],
                          directory=True)
        _restore_mode(runtime, original["runtime_root_mode"], directory=True)
        _restore_mode(temporary / "config.xml", original["config"]["mode"])

        if observe_live_files(temporary / "config.xml", runtime,
                              previous_backup=source) != previous:
            raise VoiceBackupError("Voice install image differs from sealed prior")
        if inspect_previous(source) != original or \
           bound_resource_fingerprints(source, expected_previous) != previous:
            raise VoiceBackupError("Voice restore stage changed during install-image preparation")
        _sync_stage(temporary)
        if output.exists() or output.is_symlink():
            raise VoiceBackupError("Voice install image destination appeared")
        os.rename(temporary, output)
        _sync_dir(output.parent)
        # A post-publish failure leaves durable material for manual review.
        if observe_live_files(output / "config.xml", output / "runtime",
                              previous_backup=source) != previous:
            raise VoiceBackupError("published Voice install image is inconsistent")
        return {"state": "install-image-only",
                "activation_authorized": False, "previous": previous}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
