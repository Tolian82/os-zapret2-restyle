#!/usr/local/bin/python3.13
"""Preserve *only* the extras owned by this plugin across upstream git checkout.

Invoked by the ordinary setup transaction while setup.lock is held.
No Git release, package metadata, OPNsense Config or user file is modified.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from extra_resources_preflight import sha256, validate_runtime_path
from extra_resources_transaction import (
    TransactionError, _owned_metadata, _safe_subdir, _sync_dir, _write_atomic,
)

RUNTIME = Path(os.environ.get("ZAPRET_DIR", "/usr/local/etc/zapret2"))
STATE = Path(os.environ.get("STATE_DIR", "/var/db/zapret2-restyle")) / "extra-resources"
ROLLBACK = Path(os.environ.get("ROLLBACK_DIR", "/var/db/zapret2-restyle/runtime-rollback")) / "extra-managed"
GIT = os.environ.get("GIT_BIN", "/usr/local/bin/git")


def _owned() -> dict:
    if STATE.is_symlink() or (STATE / "transaction").exists() or (STATE / "transaction").is_symlink():
        raise TransactionError("unfinished Additional Resources operation blocks upstream replacement")
    owned = _owned_metadata(STATE / "installed.json")["files"]
    for name, digest in owned.items():
        path = validate_runtime_path(RUNTIME, name)
        if not path.exists() or sha256(path.read_bytes()) != digest:
            raise TransactionError(f"managed Additional Resource missing or changed: {name}")
    return owned


def preflight(commit: str = "FETCH_HEAD") -> None:
    owned = _owned()
    if not owned:
        return
    result = subprocess.run([GIT, "-C", str(RUNTIME), "ls-tree", "-r", "--name-only", commit],
                            text=True, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        raise TransactionError("cannot inspect target upstream release tree")
    target = set(result.stdout.splitlines())
    collisions = sorted(target.intersection(owned))
    if collisions:
        raise TransactionError("target upstream release conflicts with managed resources: "
                               + ", ".join(collisions[:5]))


def snapshot() -> None:
    owned = _owned()
    if ROLLBACK.is_symlink() or ROLLBACK.exists():
        raise TransactionError("previous resource rollback snapshot not cleared")
    if not owned:
        return
    ROLLBACK.mkdir(mode=0o700, parents=True)
    try:
        for name, digest in owned.items():
            data = validate_runtime_path(RUNTIME, name).read_bytes()
            if sha256(data) != digest:
                raise TransactionError(f"resource changed during snapshot: {name}")
            dest = _safe_subdir(ROLLBACK, name)
            _write_atomic(dest, data)
        _sync_dir(ROLLBACK)
    except Exception:
        shutil.rmtree(ROLLBACK)
        raise


def verify() -> None:
    _owned()


def restore() -> None:
    metadata = _owned_metadata(STATE / "installed.json")["files"]
    if not metadata:
        return
    if ROLLBACK.is_symlink() or not ROLLBACK.is_dir():
        raise TransactionError("RESTORE_FAILED: managed resource backup unavailable")
    for name, digest in metadata.items():
        src = ROLLBACK / name
        if src.is_symlink() or not src.is_file():
            raise TransactionError(f"RESTORE_FAILED: backup missing {name}")
        body = src.read_bytes()
        if sha256(body) != digest:
            raise TransactionError(f"RESTORE_FAILED: backup altered {name}")
        target = validate_runtime_path(RUNTIME, name)
        if target.exists() and sha256(target.read_bytes()) != digest:
            raise TransactionError(f"RESTORE_FAILED: unexpected bytes at {name}")
    for name, digest in metadata.items():
        dest = validate_runtime_path(RUNTIME, name)
        if not dest.exists():
            _write_atomic(dest, (ROLLBACK / name).read_bytes())
    verify()


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {"preflight", "snapshot", "verify", "restore"}:
        print("usage: extra_resources_upstream_guard.py {preflight [COMMIT]|snapshot|verify|restore}", file=sys.stderr)
        return 64
    try:
        if argv[1] == "preflight":
            if len(argv) > 3:
                return 64
            preflight(argv[2] if len(argv) == 3 else "FETCH_HEAD")
        elif len(argv) != 2:
            return 64
        elif argv[1] == "snapshot":
            snapshot()
        elif argv[1] == "verify":
            verify()
        else:
            restore()
        print("PASS: managed additional resources are preserved")
        return 0
    except (TransactionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"RESOURCE_UPSTREAM_GUARD_FAILED: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
