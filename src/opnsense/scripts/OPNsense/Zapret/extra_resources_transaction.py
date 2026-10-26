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
import stat

from extra_resources_preflight import (
    PreflightError, inspect_collisions, resource_path, sha256, validate_runtime_path,
)
from extra_resources_reconcile import (make_plan, make_remove_plan, installed_resources,
                                       tracked_resources, _remove_head)

SCHEMA = 1
QUARANTINE_NAME = ".extra-resources-remove-quarantine"


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


def _validate_native_owner(owner: object) -> dict:
    if not isinstance(owner, dict) or set(owner) != {"id", "page", "candidate"}:
        raise TransactionError("invalid previous native common owner witness")
    if (not isinstance(owner["id"], str) or
            not re.fullmatch(r"[a-f0-9]{32}", owner["id"]) or
            owner["page"] not in ("strategies", "voice") or
            not isinstance(owner["candidate"], str) or
            not re.fullmatch(r"[a-f0-9]{64}", owner["candidate"])):
        raise TransactionError("invalid previous native common owner identity")
    return dict(owner)


def _remove_inode(path: Path) -> dict:
    """Observe the original filesystem inode, not just its Lua/BIN bytes.

    Quarantine and recovery MUST rename this very inode back. Rewriting a
    backup with _write_atomic would silently lose ACLs, flags, ownership and
    timestamps even if the SHA-256 digest still matched.
    """
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise TransactionError("unsafe or multiply linked Remove resource")
    return {
        "dev": info.st_dev, "ino": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid, "gid": info.st_gid,
        "size": info.st_size, "mtime_ns": info.st_mtime_ns,
        "flags": getattr(info, "st_flags", 0),
    }


def _validate_remove_inodes(inodes: object, previous: dict) -> dict:
    names = {"dev", "ino", "mode", "uid", "gid", "size", "mtime_ns", "flags"}
    if not isinstance(inodes, dict) or set(inodes) != set(previous):
        raise TransactionError("missing or mismatched original Remove inode witnesses")
    for name, record in inodes.items():
        if (not resource_path(name) or not isinstance(record, dict) or
                set(record) != names or
                any(type(value) is not int for value in record.values()) or
                record["ino"] <= 0 or record["dev"] < 0 or
                not 0 <= record["mode"] <= 0o7777 or
                min(record["uid"], record["gid"], record["size"], record["flags"]) < 0):
            raise TransactionError("invalid original Remove inode witness")
    return inodes


def _write_remove_phase(work: Path, phase: str, previous: dict, head: str,
                        native_owner: dict, inodes: dict,
                        *, new_owner: dict | None = None) -> None:
    # Single resource journal: verified old-owner rollback until COMMITTING;
    # after COMMITTING, only forward completion of the proven new owner.
    data = {
        "schema": SCHEMA, "mode": "remove", "phase": phase,
        "previous": previous, "incoming": {}, "source_commit": head,
        "native_owner": _validate_native_owner(native_owner),
        "original_inodes": _validate_remove_inodes(inodes, previous),
    }
    if phase == "committing":
        new = _validate_native_owner(new_owner)
        if new["id"] == data["native_owner"]["id"]:
            raise TransactionError("Remove commit did not replace native common owner")
        data["new_native_owner"] = new
    elif new_owner is not None:
        raise TransactionError("new owner may only be sealed at Remove commit")
    _json_write(work / "journal.json", data)


def _quarantine_path(root: Path) -> Path:
    return root / QUARANTINE_NAME


def _move_to_quarantine(root: Path, previous: dict, inodes: dict) -> None:
    """Rename attested extras out of the two active resource directories.

    The quarantine is INSIDE the original runtime filesystem: no EXDEV
    fallback, no second copy/move mechanism. The separate already-durable
    transaction/backup remains the authority for crash recovery.
    """
    q = _quarantine_path(root)
    if q.exists() or q.is_symlink():
        raise TransactionError("RECOVERY_REQUIRED: resource quarantine already exists")
    q.mkdir(mode=0o700)
    _sync_dir(root)
    for name, digest in sorted(previous.items()):
        source = validate_runtime_path(root, name)
        if (source.is_symlink() or not source.is_file() or
                _remove_inode(source) != inodes[name] or
                sha256(source.read_bytes()) != digest or
                _remove_inode(source) != inodes[name]):
            raise TransactionError("resource changed before quarantine: " + name)
        dest = _safe_subdir(q, name)
        if dest.exists() or dest.is_symlink():
            raise TransactionError("unsafe quarantine destination: " + name)
        os.replace(source, dest)
        _sync_dir(source.parent)
        _sync_dir(dest.parent)
        if _remove_inode(dest) != inodes[name]:
            raise TransactionError("original Remove inode changed after quarantine: " + name)


def _inspect_quarantine(root: Path, previous: dict) -> Path | None:
    q = _quarantine_path(root)
    if q.is_symlink():
        raise TransactionError("RESTORE_FAILED: quarantine is a symlink")
    if not q.exists():
        return None
    if not q.is_dir():
        raise TransactionError("RESTORE_FAILED: invalid quarantine directory")
    expected = set(previous)
    allowed_dirs = {"lua", "files", "files/fake"}
    for item in q.rglob("*"):
        rel = item.relative_to(q).as_posix()
        if item.is_symlink():
            raise TransactionError("RESTORE_FAILED: quarantine contains a symlink")
        if item.is_dir():
            if rel not in allowed_dirs:
                raise TransactionError("RESTORE_FAILED: foreign quarantine directory")
        elif rel not in expected or not item.is_file() or sha256(item.read_bytes()) != previous[rel]:
            raise TransactionError("RESTORE_FAILED: foreign quarantine resource")
    return q


def _clear_quarantine(root: Path, previous: dict) -> None:
    q = _inspect_quarantine(root, previous)
    if q is not None:
        shutil.rmtree(q)
        _sync_dir(root)


def _restore_remove(root: Path, work: Path, previous: dict, inodes: dict) -> None:
    """Return ONLY the original hardlink-free inodes through atomic rename.

    An absent source/foreign inode cannot be reconstructed faithfully from
    byte backups (ACLs and flags are not recoverable): retain the journal and
    report RESTORE_FAILED instead of pretending metadata was restored.
    """
    _validate_remove_inodes(inodes, previous)
    q = _inspect_quarantine(root, previous)
    moves = []
    # Verify the ENTIRE set before the first rename; a partial failure still
    # leaves the journal and permits an idempotent retry.
    for name, digest in sorted(previous.items()):
        _verified_staging(work, "backup", name, digest)
        target = validate_runtime_path(root, name)
        source = q / name if q is not None else None
        if source is not None and (source.exists() or source.is_symlink()):
            if (source.is_symlink() or target.exists() or target.is_symlink() or
                    _remove_inode(source) != inodes[name] or
                    sha256(source.read_bytes()) != digest):
                raise TransactionError("RESTORE_FAILED: foreign or changed Remove inode: " + name)
            moves.append((source, target))
        elif (target.is_symlink() or not target.is_file() or
              _remove_inode(target) != inodes[name] or
              sha256(target.read_bytes()) != digest):
            raise TransactionError("RESTORE_FAILED: original Remove inode missing: " + name)
    for source, target in moves:
        os.replace(source, target)
        _sync_dir(source.parent)
        _sync_dir(target.parent)


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


def _attest_prepared_remove(root: Path, state: Path, work: Path,
                            previous: dict, inodes: dict, owner: dict,
                            lifecycle) -> None:
    """Prove a pre-Stop Remove really left the pinned original state intact.

    PREPARED only means a durable snapshot exists. No Stop/quarantine was
    authorized yet, so there is nothing to roll back. Do not erase that
    evidence and claim RESTORED if another actor stopped the service, changed
    the native common owner, or replaced a Lua/BIN inode after the snapshot.
    Original setup.lock and FD9 are held by the caller throughout.
    """
    q = _quarantine_path(root)
    if q.exists() or q.is_symlink():
        raise TransactionError("PREPARED Remove has unexpected quarantine")
    lifecycle.assert_started()
    current_owner = getattr(lifecycle, "capture_previous_native_common_apply", None)
    if not callable(current_owner) or _validate_native_owner(current_owner()) != owner:
        raise TransactionError("PREPARED Remove previous native owner changed")
    _validate_remove_inodes(inodes, previous)
    for name, digest in sorted(previous.items()):
        _verified_staging(work, "backup", name, digest)
        current = validate_runtime_path(root, name)
        if (current.is_symlink() or not current.is_file() or
                _remove_inode(current) != inodes[name] or
                sha256(current.read_bytes()) != digest or
                _remove_inode(current) != inodes[name]):
            raise TransactionError("PREPARED Remove resource changed: " + name)
    original_metadata = work / "previous-installed.json"
    current_metadata = state / "installed.json"
    if original_metadata.is_symlink() or current_metadata.is_symlink():
        raise TransactionError("PREPARED Remove metadata is unsafe")
    if original_metadata.is_file():
        if (not current_metadata.is_file() or
                original_metadata.read_bytes() != current_metadata.read_bytes()):
            raise TransactionError("PREPARED Remove installed metadata changed")
    elif original_metadata.exists() or current_metadata.exists():
        raise TransactionError("PREPARED Remove unexpected installed metadata")


def _finish_committing_remove(root: Path, state: Path, work: Path,
                              journal: dict, lifecycle, *,
                              acceptance_fault: str | None = None) -> None:
    """Idempotent forward completion after a DURABLE healthy native trial.

    The source inodes are only discarded AFTER the authoritative shared Apply
    committed a new Started owner and this single resource journal sealed its
    new owner. Even if a cold cut occurs mid-cleanup, old inode restoration is
    never falsely attempted after original inodes may have been unlinked.
    """
    previous = journal["previous"]
    inodes = _validate_remove_inodes(journal["original_inodes"], previous)
    new_owner = _validate_native_owner(journal.get("new_native_owner"))
    old_owner = _validate_native_owner(journal.get("native_owner"))
    if new_owner["id"] == old_owner["id"]:
        raise TransactionError("committed Remove retained original native owner")
    retired = state / (".retired-remove-" + new_owner["id"])
    if retired.exists() or retired.is_symlink():
        raise TransactionError("retired Remove journal destination already exists")
    if _remove_head(root, "git") != journal["source_commit"]:
        raise TransactionError("upstream Git HEAD changed after Remove commit")
    if installed_resources(root) != tracked_resources(root):
        raise TransactionError("non-upstream or modified resources after Remove commit")
    q = _inspect_quarantine(root, previous)
    for name, digest in sorted(previous.items()):
        _verified_staging(work, "backup", name, digest)
        source = q / name if q is not None else None
        if source is not None and (source.exists() or source.is_symlink()):
            if (source.is_symlink() or _remove_inode(source) != inodes[name] or
                    sha256(source.read_bytes()) != digest or
                    _remove_inode(source) != inodes[name]):
                raise TransactionError("committed Remove quarantine inode changed: " + name)
    installed_file = state / "installed.json"
    backup = work / "previous-installed.json"
    if installed_file.is_symlink() or backup.is_symlink():
        raise TransactionError("unsafe committed Remove metadata")
    if installed_file.exists():
        if not backup.is_file() or installed_file.read_bytes() != backup.read_bytes():
            raise TransactionError("committed Remove managed metadata changed")
    elif backup.exists() and not backup.is_file():
        raise TransactionError("unsafe committed Remove metadata backup")

    # A power cut can leave the already committed new common owner Stopped.
    # Reboot exclusively via original shared Apply boot, after its own
    # Stopped attestation; foreign/mixed process and IPFW remain fail-closed.
    try:
        lifecycle.assert_started()
    except Exception:
        lifecycle.assert_stopped()
        lifecycle.start()
        lifecycle.assert_started()
    capture = getattr(lifecycle, "capture_previous_native_common_apply", None)
    if not callable(capture) or _validate_native_owner(capture()) != new_owner:
        raise TransactionError("committed Remove native owner is not attested")

    if installed_file.exists():
        installed_file.unlink()
        _sync_dir(state)
    if acceptance_fault == "interrupt-after-first-committed-inode":
        # Owner-console R4 only: new native owner + durable journal proven.
        # A missing original inode CANNOT be rolled back by copying bytes.
        if q is None:
            raise TransactionError("R4 quarantine missing after native commit")
        first_name = next((name for name in sorted(previous)
                           if (q / name).is_file()), None)
        if first_name is None:
            raise TransactionError("R4 requires an original quarantined inode")
        first = q / first_name
        if (first.is_symlink() or _remove_inode(first) != inodes[first_name] or
                sha256(first.read_bytes()) != previous[first_name] or
                _remove_inode(first) != inodes[first_name]):
            raise TransactionError("R4 first original inode changed")
        first.unlink()
        _sync_dir(first.parent)
        raise KeyboardInterrupt("OWNER_ACCEPTANCE_INTERRUPTED_AFTER_FIRST_COMMITTED_INODE")
    _clear_quarantine(root, previous)
    if installed_resources(root) != tracked_resources(root):
        raise TransactionError("post-commit upstream resources changed")
    lifecycle.assert_started()
    if _validate_native_owner(capture()) != new_owner:
        raise TransactionError("committed native owner drifted during finalization")

    # Atomic detachment from the pending journal path is a durable terminal
    # receipt. A crash while deleting retired backups cannot block Start or
    # make an already committed removal look like an unproven rollback.
    os.replace(work, retired)
    _sync_dir(state)
    try:
        shutil.rmtree(retired)
        _sync_dir(state)
    except OSError:
        # Private 0700 retired evidence can be inspected later. The new
        # native owner is already verified; it must not be rolled back.
        pass


def recover(root: Path, state: Path, lifecycle) -> str:
    """Must be called under the SAME setup and lifecycle locks as install."""
    _safe_state(state)
    work = state / "transaction"
    if not work.exists():
        return "NO_RECOVERY_NEEDED"
    journal = _load_journal(work)
    previous, incoming = journal["previous"], journal["incoming"]
    is_remove = journal.get("mode") == "remove"
    if journal.get("mode", "install") not in ("install", "remove"):
        raise TransactionError("unknown recovery transaction mode")
    if is_remove and incoming:
        raise TransactionError("invalid remove recovery journal")
    native_owner = _validate_native_owner(journal.get("native_owner")) if is_remove else None
    inodes = _validate_remove_inodes(journal.get("original_inodes"), previous) if is_remove else None
    if is_remove and journal.get("phase") == "committing":
        try:
            _finish_committing_remove(root, state, work, journal, lifecycle)
            return "REMOVED"
        except Exception as exc:
            raise TransactionError(f"RESTORE_FAILED: committed Remove finalization: {exc}") from exc
    if is_remove and "new_native_owner" in journal:
        raise TransactionError("foreign new owner in pre-commit Remove journal")
    try:
        if journal.get("phase") == "completed":
            raise TransactionError("completed journal requires post-commit audit")
        if journal.get("phase") == "prepared":
            # No mutation was scheduled, but original runtime/resource state
            # must still be attested before discarding the recovery evidence.
            if is_remove:
                _attest_prepared_remove(root, state, work, previous, inodes,
                                        native_owner, lifecycle)
        else:
            # A native Remove trial can replace the shared Apply owner. Blind
            # start() may then boot the *new* sealed release, not the prior
            # Config/runtime/Voice owner. Refuse before Stop when the original
            # owner-specific recovery callback is unavailable.
            restore_native = getattr(lifecycle, "restore_previous_native_common_apply", None)
            if is_remove and not callable(restore_native):
                raise TransactionError("native Remove rollback route is not available")
            if is_remove:
                # Power-cut after native common PREPARED but before ANY kernel
                # mutation: existing normal status/Stop refuse the nonterminal
                # common journal. Only the original FD9 read-only attestation
                # may close that journal, after proving the OLD stopped
                # release and empty engine/IPFW. Never skip Stop on a mere
                # status==2 or a guessed/foreign trial.
                complete_prepared = getattr(
                    lifecycle, "recover_prepared_native_common_apply", None)
                prepared_old_stopped = bool(complete_prepared(native_owner)) if (
                    journal.get("phase") == "restarting" and
                    callable(complete_prepared)) else False
                if not prepared_old_stopped:
                    try:
                        lifecycle.assert_stopped()
                    except Exception:
                        lifecycle.stop()
                        lifecycle.assert_stopped()
            else:
                lifecycle.stop()
                lifecycle.assert_stopped()
            if is_remove:
                _restore_remove(root, work, previous, inodes)
            else:
                _restore(root, work, previous, incoming)
            _rollback_metadata(state, work)
            if is_remove:
                restore_native(native_owner)
            else:
                lifecycle.start()
            lifecycle.assert_started()
        if is_remove:
            _clear_quarantine(root, previous)
        shutil.rmtree(work)
        _sync_dir(state)
        return "RESTORED"
    except Exception as exc:
        # Keep all evidence and backups for a controlled retry/inspection.
        raise TransactionError(f"RESTORE_FAILED: {exc}") from exc


def install(payloads: dict[str, bytes], revision: str, root: Path,
            state: Path, lifecycle, capabilities: dict | None = None,
            reconcile: bool = False) -> dict:
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
        if reconcile:
            plan = make_plan(payloads, root, installed_file)
            previous, incoming = plan["previous"], plan["incoming"]
        else:
            inspect_collisions(payloads, root, installed_file)
            previous = old_metadata["files"]
            incoming = {name: sha256(data) for name, data in payloads.items()}
    except PreflightError as exc:
        raise TransactionError(str(exc)) from exc
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
        for name in incoming:
            _store_file(work / "staged", name, payloads[name])
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
        if reconcile:
            verified = make_plan(payloads, root, installed_file)
            if verified["removed"] or verified["previous"] != incoming:
                raise TransactionError("exact Lua/BIN set not reached after publication")
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
                "removed": len(plan["removed"]) if reconcile else 0,
                "restarted": True}
    except Exception as exc:
        try:
            recover(root, state, lifecycle)
        except Exception as restore_error:
            raise TransactionError(f"RESTORE_FAILED after {exc}: {restore_error}") from restore_error
        raise TransactionError(f"INSTALL_FAILED_RESTORED: {exc}") from exc



def remove_with_native_trial(expected_witness: str, root: Path, state: Path,
                             lifecycle, *, config: Path = Path("/conf/config.xml"),
                             acceptance_fault: str | None = None) -> dict:
    """Remove extras with the ORIGINAL saved Config and an injected native Apply.

    This is INTERNAL and NOT connected to a GUI/configd operation. The native
    lifecycle must provide BOTH start_trial_native_common_apply() and
    restore_previous_native_common_apply(). The first must use the existing
    shared GUI Apply build/activation after quarantine; the second must
    restore the prior common owner without guessing via start()/cached boot.
    Both missing routes refuse BEFORE Stop or resource mutation. Pin the
    original sealed common owner ID/page/saved Config digest inside this
    existing resource transaction journal (no second owner database).
    """
    if acceptance_fault not in (None, "fail-after-quarantine", "interrupt-after-quarantine",
                                 "interrupt-after-first-committed-inode"):
        raise TransactionError("invalid owner-acceptance fault boundary")
    if not isinstance(expected_witness, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_witness):
        raise TransactionError("invalid confirmed removal witness")
    if state.is_symlink() or (state / "transaction").exists() or (state / "transaction").is_symlink():
        raise TransactionError("RECOVERY_REQUIRED: unsafe or unfinished resource transaction")
    if _quarantine_path(root).exists() or _quarantine_path(root).is_symlink():
        raise TransactionError("RECOVERY_REQUIRED: existing resource quarantine")

    # Uses the existing real Git HEAD/Config inventory, not catalog or
    # manually copied target lists. Callers already hold setup.lock and FD9.
    try:
        plan = make_remove_plan(root, state / "installed.json", config)
    except PreflightError as exc:
        raise TransactionError(str(exc)) from exc
    if plan["witness"]["inventory_sha256"] != expected_witness:
        raise TransactionError("confirmed removal plan is stale")
    previous = {record["path"]: record["sha256"] for record in plan["remove"]}
    if not previous:
        return {"status": "NO_EXTRA_RESOURCES", "lua": 0, "bin": 0,
                "removed": 0, "restarted": False}

    # The pair is mandatory. A real trial must never pass its early safety
    # gate with a native Apply start callback but no trustworthy path back to
    # the previously sealed common owner after a later failure.
    if not callable(getattr(lifecycle, "start_trial_native_common_apply", None)):
        raise TransactionError("native common Apply trial route is not available")
    if not callable(getattr(lifecycle, "restore_previous_native_common_apply", None)):
        raise TransactionError("native common Apply rollback route is not available")

    if not callable(getattr(lifecycle, "capture_previous_native_common_apply", None)):
        raise TransactionError("native common Apply previous-owner witness route is not available")
    old_identity = lifecycle.assert_started()
    old_owner = _validate_native_owner(lifecycle.capture_previous_native_common_apply())
    _safe_state(state)
    work = state / "transaction"
    if work.exists() or work.is_symlink():
        raise TransactionError("RECOVERY_REQUIRED: unfinished resource transaction")
    work.mkdir(mode=0o700)
    _sync_dir(state)
    inodes = {}
    try:
        (work / "backup").mkdir(mode=0o700)
        installed_file = state / "installed.json"
        if installed_file.exists():
            metadata = _owned_metadata(installed_file)
            _write_atomic(work / "previous-installed.json", installed_file.read_bytes())
            if any(name in plan["upstream"] or
                   name not in previous or previous[name] != digest
                   for name, digest in metadata["files"].items()):
                raise TransactionError("managed resource ownership changed")
        for name, digest in previous.items():
            path = validate_runtime_path(root, name)
            body = path.read_bytes()
            if sha256(body) != digest:
                raise TransactionError("extra resource changed before snapshot")
            inode = _remove_inode(path)
            if sha256(path.read_bytes()) != digest or _remove_inode(path) != inode:
                raise TransactionError("original resource inode changed during snapshot")
            inodes[name] = inode
            _store_file(work / "backup", name, body)
        _write_remove_phase(work, "prepared", previous, plan["upstream_head"], old_owner, inodes)
    except Exception:
        shutil.rmtree(work)
        _sync_dir(state)
        raise
    committing = False
    try:
        # The binding is rechecked immediately before Stop while original
        # FD9 remains held; a stale Confirm never authorizes any file move.
        renewed = make_remove_plan(root, state / "installed.json", config)
        if renewed["witness"]["inventory_sha256"] != expected_witness:
            raise TransactionError("resource or saved Config changed during preparation")
        if _validate_native_owner(lifecycle.capture_previous_native_common_apply()) != old_owner:
            raise TransactionError("previous native common owner changed before Stop")
        for name in previous:
            if _remove_inode(validate_runtime_path(root, name)) != inodes[name]:
                raise TransactionError("original resource inode changed before Stop")
        _write_remove_phase(work, "stopping", previous, plan["upstream_head"], old_owner, inodes)
        lifecycle.stop()
        lifecycle.assert_stopped()
        _write_remove_phase(work, "publishing", previous, plan["upstream_head"], old_owner, inodes)
        _move_to_quarantine(root, previous, inodes)
        # Check exact resource set before invoking the same real GUI compiler.
        if installed_resources(root) != plan["upstream"]:
            raise TransactionError("quarantine did not reach exact upstream resources")
        _write_remove_phase(work, "restarting", previous, plan["upstream_head"], old_owner, inodes)
        # Only the explicit root-console acceptance route can pass these
        # controlled fault points. They still use the ORIGINAL Stop and
        # inode-quarantine/recovery machinery (no synthetic runtime).
        if acceptance_fault == "fail-after-quarantine":
            raise TransactionError("OWNER_ACCEPTANCE_FORCED_ROLLBACK")
        if acceptance_fault == "interrupt-after-quarantine":
            raise KeyboardInterrupt("OWNER_ACCEPTANCE_INTERRUPTED_AFTER_QUARANTINE")
        lifecycle.start_trial_native_common_apply()
        new_identity = lifecycle.assert_started()
        if not new_identity or new_identity == old_identity:
            raise TransactionError("native trial did not produce a replacement service owner")
        if installed_resources(root) != plan["upstream"]:
            raise TransactionError("resources changed during native trial")
        # Commit exact new healthy common owner DURABLY before removing even
        # one original inode. If cut occurs later, recovery finishes forward.
        new_owner = _validate_native_owner(lifecycle.capture_previous_native_common_apply())
        if new_owner["id"] == old_owner["id"]:
            raise TransactionError("native Remove trial did not replace common owner")
        _write_remove_phase(work, "committing", previous, plan["upstream_head"],
                            old_owner, inodes, new_owner=new_owner)
        committing = True
        _finish_committing_remove(root, state, work, _load_journal(work), lifecycle,
                                  acceptance_fault=acceptance_fault)
        return {"status": "REMOVED", "lua": plan["counts"]["lua"],
                "bin": plan["counts"]["bin"], "removed": len(previous),
                "restarted": True}
    except Exception as exc:
        if committing:
            # The success commit is irrevocable. Old original inodes may
            # already be deleted; never claim a previous-owner rollback.
            raise TransactionError("REMOVE_COMMIT_PENDING: " + str(exc)) from exc
        try:
            recover(root, state, lifecycle)
        except Exception as restore_error:
            raise TransactionError("RESTORE_FAILED after native trial: " + str(restore_error)) from restore_error
        raise TransactionError("REMOVE_FAILED_RESTORED: " + str(exc)) from exc
