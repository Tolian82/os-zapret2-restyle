#!/usr/local/bin/python3.13
"""Isolated upstream-only Lua/BIN view for prospective native compilation.

Stage 2 foundation ONLY. Building the view is not a Strategies/Voice
compatibility result or permission to Stop, delete or restart the service.
The caller must hold the approved native locks and use the authoritative
Strategies/Voice compiler against this view before compatibility may be true.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
from typing import Iterator

from extra_resources_preflight import PreflightError, sha256, validate_runtime_path
from extra_resources_reconcile import (
    MAX_FILE, _remove_file_attestation, installed_resources, make_remove_plan,
)


@contextmanager
def upstream_only_view(
    root: Path,
    managed: Path,
    config: Path,
    *,
    workspace_root: Path | None = None,
    expected_witness: str | None = None,
    git_bin: str = "git",
) -> Iterator[tuple[dict, Path]]:
    """Create a private, self-cleaning view containing ONLY verified HEAD resources.

    No source resource is hardlinked or modified; every staged file is a
    separately verified copy of the installed Git HEAD bytes. Never place
    this view underneath the production runtime or other shared directories.
    The full inventory witness and saved Config are re-attested both sides
    of the copy. The caller must separately attest them again before mutation.
    """
    plan = make_remove_plan(root, managed, config, git_bin)
    if expected_witness is not None and (
        expected_witness != plan["witness"]["inventory_sha256"]
    ):
        raise PreflightError("removal preview is stale: upstream/config/inventory changed")
    if workspace_root is not None and (
        workspace_root.is_symlink() or not workspace_root.is_dir()
        or workspace_root.resolve() == root.resolve()
        or root.resolve() in workspace_root.resolve().parents
    ):
        raise PreflightError("unsafe prospective resource workspace")

    with tempfile.TemporaryDirectory(
        prefix="zapret-upstream-only-", dir=workspace_root
    ) as tmp:
        view = Path(tmp)
        (view / "lua").mkdir(mode=0o700)
        (view / "files").mkdir(mode=0o700)
        (view / "files/fake").mkdir(mode=0o700)
        for name, expected_digest in sorted(plan["upstream"].items()):
            source = validate_runtime_path(root, name)
            contents, evidence = _remove_file_attestation(source, MAX_FILE)
            if not contents or evidence["sha256"] != expected_digest:
                raise PreflightError(f"upstream byte witness changed while staging: {name}")
            target = view / name
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o400)
            with os.fdopen(fd, "wb") as staged:
                staged.write(contents)
                staged.flush()
                os.fsync(staged.fileno())
            if sha256(target.read_bytes()) != expected_digest:
                raise PreflightError(f"prospective upstream copy checksum mismatch: {name}")
        if installed_resources(view) != plan["upstream"]:
            raise PreflightError("prospective upstream view differs from installed Git HEAD")
        if make_remove_plan(root, managed, config, git_bin) != plan:
            raise PreflightError("resource/config inventory changed during prospective staging")
        # The staged view is an inert input. No full native compile, Lua-export
        # proof or Voice/OFF-draft validation happens in this helper.
        yield plan, view
