#!/usr/local/bin/python3.13
"""Native locked saved-Strategies *input* for prospective upstream-only compilation.

Import-only, no public CLI or service/configd operation. The future native
preflight owner must hold original FD9 AND the existing exclusive Config inode
flock for the *entire* context. This never starts an engine or changes IPFW,
Config, runtime, service or installed Lua/BIN resources.

It deliberately cannot issue a compatible/removal-authorized result. The
renderer is exactly shared_apply_render.render_detached; the saved pair and
upstream-only view use the existing authoritative guards.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Iterator

# Existing native compiler modules import their siblings by unqualified name.
# Resolve that same installed, package-owned directory before using the
# original Config flock and lifecycle lock guards (no duplicate implementation).
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from backend.shared_apply_render import MAX_XML, render_detached, TARGETS
from backend.voice_ipfw_adapter import require_lifecycle_lock
from backend.voice_native_lifecycle_router import _locked_config
from extra_resources_preflight import PreflightError
from extra_resources_upstream_view import upstream_only_view

# The existing native pair guard limits saved Config to four MiB.
MAX_SAVED = 4 * 1024 * 1024


def _locked_bytes(config: Path, fd: int, owner: tuple[int, int],
                  check_lifecycle) -> bytes:
    """Read the same locked original inode, rejecting changes/foreign owners."""
    check_lifecycle()
    _locked_config(config, fd, owner)
    before = os.fstat(fd)
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or not 0 < before.st_size <= min(MAX_SAVED, MAX_XML)):
        raise PreflightError("unsafe or oversized native saved Config")
    data = os.pread(fd, before.st_size + 1, 0)
    after = os.fstat(fd)
    same = (
        before.st_dev, before.st_ino, before.st_size,
        before.st_mtime_ns, before.st_ctime_ns, before.st_mode,
    ) == (
        after.st_dev, after.st_ino, after.st_size,
        after.st_mtime_ns, after.st_ctime_ns, after.st_mode,
    )
    if (not same or len(data) != before.st_size or
            b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper()):
        raise PreflightError("native saved Config changed or contains unsafe XML")
    return data


def _private_workspace(path: Path, runtime: Path) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise PreflightError("prospective Config workspace must be absolute and private")
    try:
        info = path.lstat()
        resolved, production = path.resolve(strict=True), runtime.resolve(strict=True)
    except OSError as exc:
        raise PreflightError("prospective Config workspace is missing") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or resolved == production or production in resolved.parents):
        raise PreflightError("unsafe prospective Config workspace")


@contextmanager
def locked_saved_strategies_view(
    runtime: Path,
    managed_manifest: Path,
    *,
    config_path: Path = Path("/conf/config.xml"),
    config_fd: int,
    config_owner: tuple[int, int],
    workspace_root: Path,
    expected_witness: str | None = None,
    check_lifecycle=None,
    template_factory=None,
    config_factory=None,
    git_bin: str = "git",
) -> Iterator[tuple[dict, Path, Path, Path]]:
    """Yield (unauthorized-plan, upstream-only-files, saved-XML, native-template).

    The caller already holds original FD9 and Config inode flock. Unless a
    test injects an explicit checker, the existing FreeBSD FD9 attestor runs.
    Only the existing native OPNsense renderer is used; mock factories are
    supported for source tests as they are in shared_apply_render.
    """
    runtime, manifest = Path(runtime), Path(managed_manifest)
    config, workspace = Path(config_path), Path(workspace_root)
    verifier = require_lifecycle_lock if check_lifecycle is None else check_lifecycle
    if not callable(verifier):
        raise PreflightError("native lifecycle verifier is unavailable")
    _private_workspace(workspace, runtime)
    saved_bytes = _locked_bytes(config, config_fd, config_owner, verifier)
    digest = hashlib.sha256(saved_bytes).hexdigest()

    with tempfile.TemporaryDirectory(prefix="zapret-saved-prospective-",
                                     dir=workspace) as name:
        local = Path(name)
        snapshot = local / "candidate.xml"
        fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(saved_bytes)
            output.flush()
            os.fsync(output.fileno())

        # shared_apply_render owns exact OPNsense +TARGETS and native Config
        # XML parsing: a second special-purpose renderer is prohibited.
        render_detached(
            snapshot, local / "templates",
            template_factory=template_factory,
            config_factory=config_factory,
        )
        rendered = local / "templates/usr/local/etc/zapret2/zapret.conf"
        # Prevent a forged or stale template from being treated as Config.
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest:
            raise PreflightError("saved prospective Config snapshot changed during rendering")
        if _locked_bytes(config, config_fd, config_owner, verifier) != saved_bytes:
            raise PreflightError("native saved Config changed during detached rendering")

        try:
            with upstream_only_view(
                runtime, manifest, config, workspace_root=local,
                expected_witness=expected_witness,
                saved_template=rendered, git_bin=git_bin,
            ) as (plan, resource_view):
                if plan["authorized"] is not False or plan["compatibility"] != "unknown":
                    raise PreflightError("prospective saved Strategies view cannot authorize removal")
                yield plan, resource_view, snapshot, rendered
        finally:
            # Post-compile revalidation runs even if the consumer threw.
            # A failed lifecycle/config witness must invalidate the result.
            if _locked_bytes(config, config_fd, config_owner, verifier) != saved_bytes:
                raise PreflightError("native saved Config changed during prospective compilation")
            if hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest:
                raise PreflightError("saved prospective Config snapshot changed during compilation")
