#!/usr/local/bin/python3.13
"""Durable, fail-closed managed Lua/BIN publication, independent of service wiring.

A caller MUST serialize setup.lock -> existing lifecycle FD9 and supply a
lifecycle adapter that controls the existing Zapret2 service under that FD9.
This module neither downloads automatically nor changes OPNsense Config.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil

from extra_resources_preflight import (
    PreflightError, inspect_collisions, resource_path, sha256, validate_runtime_path,
)

SCHEMA = 1


class TransactionError(RuntimeError):
    pass


def _sync_dir(directory: Path) -> None:
    fd = os.open(str(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_atomic(target: Path, body: bytes) -> None:
    tmp = target.with_name(target.name + ".new")
    if tmp.exists() or tmp.is_symlink():
        raise TransactionError(f"unexpected staging name already exists: {tmp}")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
        _sync_dir(target.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def _json_write(target: Path, value: dict) -> None:
    _write_atomic(target, (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _owned_metadata(path: Path) -> dict:
    if path.is_symlink():
        raise TransactionError("managed metadata may not be a symlink")
    if not path.exists():
        return {"schema": SCHEMA, "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TransactionError("managed metadata cannot be read") from exc
    owned = data.get("files") if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(owned, dict):
        raise TransactionError("invalid managed metadata")
    if any(not resource_path(k) or not isinstance(v, str) or
           re.fullmatch(r"[0-9a-f]{64}", v) is None for k, v in owned.items()):
        raise TransactionError("unsafe managed metadata entry")
    return data


def _safe_state(state: Path) -> None:
    if state.is_symlink():
        raise TransactionError("unsafe state directory")
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not state.is_dir():
        raise TransactionError("state path is not a directory")
    if (state / "transaction").is_symlink():
        raise TransactionError("transaction storage may not be a symlink")


def _safe_subdir(base: Path, rel: str) -> Path:
    if not resource_path(rel):
        raise TransactionError(f"invalid staged resource: {rel}")
    cursor = base
    for name in rel.split("/")[:-1]:
        cursor = cursor / name
        if cursor.is_symlink():
            raise TransactionError("unsafe transaction directory symlink")
        cursor.mkdir(exist_ok=True)
    return base / rel


def _store_file(base: Path, name: str, data: bytes) -> None:
    path = _safe_subdir(base, name)
    if path.exists() or path.is_symlink():
        raise TransactionError(f"duplicate staged resource: {name}")
    _write_atomic(path, data)


def _write_phase(work: Path, phase: str, old: dict, new: dict, rev: str) -> None:
    _json_write(work / "journal.json", {
        "schema": SCHEMA, "phase": phase, "previous": old,
        "incoming": new, "source_commit": rev,
    })


def _verified_staging(work: Path, folder: str, name: str, digest: str) -> bytes:
    path = work / folder / name
    if path.is_symlink() or not path.is_file():
        raise TransactionError(f"required {folder} copy is absent: {name}")
    data = path.read_bytes()
    if sha256(data) != digest:
        raise TransactionError(f"{folder} copy checksum mismatch: {name}")
    return data


def _current_is_approved(path: Path, old: str | None, new: str | None) -> bool:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return False
    if not path.exists():
        return old is None or new is None
    current = sha256(path.read_bytes())
    return current in {old, new}


def _publish(root: Path, work: Path, previous: dict, incoming: dict) -> None:
    for name in sorted(set(previous) | set(incoming)):
        target = validate_runtime_path(root, name)
        if not _current_is_approved(target, previous.get(name), incoming.get(name)):
            raise TransactionError(f"resource changed during publication: {name}")
        if name in incoming:
            body = _verified_staging(work, "staged", name, incoming[name])
            if target.exists() and sha256(target.read_bytes()) == incoming[name]:
                continue
            _write_atomic(target, body)
        elif target.exists():
            target.unlink()
            _sync_dir(target.parent)


def _restore(root: Path, work: Path, previous: dict, incoming: dict) -> None:
    # Never overwrite arbitrary bytes that appeared after the original snapshot.
    for name in sorted(set(previous) | set(incoming)):
        path = validate_runtime_path(root, name)
        if not _current_is_approved(path, previous.get(name), incoming.get(name)):
            raise TransactionError(f"RESTORE_FAILED: foreign bytes at {name}")
    for name in sorted(set(previous) | set(incoming)):
        target = validate_runtime_path(root, name)
        if name in previous:
            data = _verified_staging(work, "backup", name, previous[name])
            if not target.exists() or sha256(target.read_bytes()) != previous[name]:
                _write_atomic(target, data)
        elif target.exists():
            target.unlink()
            _sync_dir(target.parent)


def _rollback_metadata(state: Path, work: Path) -> None:
    old = work / "previous-installed.json"
    target = state / "installed.json"
    if old.is_symlink():
        raise TransactionError("RESTORE_FAILED: metadata backup is a symlink")
    if old.is_file():
        _write_atomic(target, old.read_bytes())
    elif target.exists():
        target.unlink()
        _sync_dir(state)


def _load_journal(work: Path) -> dict:
    journal = work / "journal.json"
    if journal.is_symlink() or not journal.is_file():
        raise TransactionError("recovery journal is absent or unsafe")
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TransactionError("recovery journal is unreadable") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise TransactionError("invalid recovery journal")
    previous, incoming = data.get("previous"), data.get("incoming")
    if not isinstance(previous, dict) or not isinstance(incoming, dict):
        raise TransactionError("incomplete recovery journal")
    for entries in (previous, incoming):
        for name, digest in entries.items():
            if not resource_path(name) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise TransactionError("unsafe recovery entry")
    return data


def recover(root: Path, state: Path, lifecycle) -> str:
    """Must be called under the SAME setup and lifecycle locks as install."""
    _safe_state(state)
    work = state / "transaction"
    if not work.exists():
        return "NO_RECOVERY_NEEDED"
    journal = _load_journal(work)
    previous, incoming = journal["previous"], journal["incoming"]
    try:
        if journal.get("phase") == "completed":
            raise TransactionError("completed journal requires post-commit audit")
        if journal.get("phase") == "prepared":
            # No runtime mutation has occurred. Backup copies were completed.
            pass
        else:
            lifecycle.stop()
            lifecycle.assert_stopped()
            _restore(root, work, previous, incoming)
            _rollback_metadata(state, work)
            lifecycle.start()
            lifecycle.assert_started()
        shutil.rmtree(work)
        _sync_dir(state)
        return "RESTORED"
    except Exception as exc:
        # Keep all evidence and backups for a controlled retry/inspection.
        raise TransactionError(f"RESTORE_FAILED: {exc}") from exc


def install(payloads: dict[str, bytes], revision: str, root: Path,
            state: Path, lifecycle, capabilities: dict | None = None) -> dict:
    """Prepare, stop, publish, restart and prove a new native process owner.

    Not a public entrypoint: the caller owns the existing FD9 and setup lock.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise TransactionError("source revision must be an immutable Git SHA")
    if not payloads or any(not resource_path(name) or not data for name, data in payloads.items()):
        raise TransactionError("unsafe or empty publication set")
    _safe_state(state)
    work = state / "transaction"
    if work.exists() or work.is_symlink():
        raise TransactionError("RECOVERY_REQUIRED: unfinished resource transaction")
    installed_file = state / "installed.json"
    old_metadata = _owned_metadata(installed_file)
    try:
        inspect_collisions(payloads, root, installed_file)
    except PreflightError as exc:
        raise TransactionError(str(exc)) from exc
    previous = old_metadata["files"]
    incoming = {name: sha256(data) for name, data in payloads.items()}
    # Existing native service must be genuinely running; stopped operation is
    # forbidden even if all incoming bytes are unchanged.
    old_identity = lifecycle.assert_started()
    work.mkdir(mode=0o700)
    _sync_dir(state)
    try:
        (work / "backup").mkdir(mode=0o700)
        (work / "staged").mkdir(mode=0o700)
        if installed_file.exists():
            _write_atomic(work / "previous-installed.json", installed_file.read_bytes())
        for name in previous:
            target = validate_runtime_path(root, name)
            data = target.read_bytes()
            if sha256(data) != previous[name]:
                raise TransactionError(f"managed resource drift before snapshot: {name}")
            _store_file(work / "backup", name, data)
        for name, body in payloads.items():
            _store_file(work / "staged", name, body)
        _write_phase(work, "prepared", previous, incoming, revision)
    except Exception:
        shutil.rmtree(work)
        raise
    # All resources and snapshots are durable before the first stop.
    try:
        _write_phase(work, "stopping", previous, incoming, revision)
        lifecycle.stop()
        lifecycle.assert_stopped()
        _write_phase(work, "publishing", previous, incoming, revision)
        _publish(root, work, previous, incoming)
        metadata = {
            "schema": SCHEMA, "source_commit": revision, "files": incoming,
            "capabilities": capabilities or {"schema": SCHEMA, "resources": []},
        }
        _json_write(installed_file, metadata)
        for name, digest in incoming.items():
            if sha256(validate_runtime_path(root, name).read_bytes()) != digest:
                raise TransactionError(f"post-publication mismatch: {name}")
        _write_phase(work, "restarting", previous, incoming, revision)
        lifecycle.start()
        new_identity = lifecycle.assert_started()
        if not new_identity or new_identity == old_identity:
            raise TransactionError("restart did not prove a replacement service process")
        _write_phase(work, "completed", previous, incoming, revision)
        shutil.rmtree(work)
        _sync_dir(state)
        return {"status": "INSTALLED", "revision": revision,
                "lua": sum(x.startswith("lua/") for x in incoming),
                "bin": sum(x.startswith("files/fake/") for x in incoming),
                "restarted": True}
    except Exception as exc:
        try:
            recover(root, state, lifecycle)
        except Exception as restore_error:
            raise TransactionError(f"RESTORE_FAILED after {exc}: {restore_error}") from restore_error
        raise TransactionError(f"INSTALL_FAILED_RESTORED: {exc}") from exc
