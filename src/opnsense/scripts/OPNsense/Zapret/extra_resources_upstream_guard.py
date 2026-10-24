#!/usr/local/bin/python3.13
"""Attest and reconcile Lua/BIN only inside the native upstream setup transaction.

No Config or Git tag mutation. Unowned file deletion needs an independently
sealed original-byte snapshot and the parent durable mutating checkpoint.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

from extra_resources_preflight import PreflightError, sha256, validate_runtime_path, resource_path
from upstream_checkout_origin import InspectError, inspect_checkout
from extra_resources_reconcile import tracked_resources, installed_resources, previous_metadata
from extra_resources_transaction import (
    TransactionError, _owned_metadata, _safe_subdir, _sync_dir, _write_atomic,
)

RUNTIME = Path(os.environ.get("ZAPRET_DIR", "/usr/local/etc/zapret2"))
STATE = Path(os.environ.get("STATE_DIR", "/var/db/zapret2-restyle")) / "extra-resources"
ROLLBACK = Path(os.environ.get("ROLLBACK_DIR", "/var/db/zapret2-restyle/runtime-rollback")) / "extra-managed"
GIT = os.environ.get("GIT_BIN", "/usr/local/bin/git")
BACKUP_ROOT = ROLLBACK.parent
ATTESTATION = BACKUP_ROOT / "backup-attestation.json"
TARGET_IDENTITY = BACKUP_ROOT / "target-identity.json"


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


def verify_snapshot() -> None:
    """Read-only saved-byte attestation, valid even after a checkout removes live files.

    The prepared-phase caller must also call verify() to prove the working
    runtime is unchanged. Mutating-phase analysis cannot assume that.
    """
    if STATE.is_symlink() or (STATE / "transaction").exists() or (STATE / "transaction").is_symlink():
        raise TransactionError("unfinished Additional Resources operation blocks snapshot verification")
    metadata = _owned_metadata(STATE / "installed.json")["files"]
    if ROLLBACK.is_symlink():
        raise TransactionError("managed backup is a symlink")
    if not metadata:
        if ROLLBACK.exists():
            raise TransactionError("unexpected managed backup with empty manifest")
        return
    if not ROLLBACK.is_dir():
        raise TransactionError("managed snapshot missing")
    expected_files = set(metadata)
    expected_dirs = {part for name in metadata for part in
                     ("/".join(name.split("/")[:i]) for i in range(1, len(name.split("/"))))}
    for entry in ROLLBACK.rglob("*"):
        relative = entry.relative_to(ROLLBACK).as_posix()
        if entry.is_symlink():
            raise TransactionError(f"managed backup symlink: {relative}")
        if not (
            (entry.is_dir() and relative in expected_dirs)
            or (entry.is_file() and relative in expected_files)
        ):
            raise TransactionError(f"unexpected managed backup entry: {relative}")
    for name, digest in metadata.items():
        src = ROLLBACK / name
        # Reject symlinks in *any* intermediate directory as well as leaves.
        cursor = src
        while cursor != ROLLBACK:
            if cursor.is_symlink():
                raise TransactionError(f"managed backup symlink: {name}")
            cursor = cursor.parent
        if not src.is_file() or sha256(src.read_bytes()) != digest:
            raise TransactionError(f"managed backup missing or changed: {name}")



def _untracked_inventory() -> dict[str, str]:
    root = BACKUP_ROOT / "untracked-resources"
    if root.is_symlink() or not root.is_dir():
        raise TransactionError("untracked resource backup missing or linked")
    files: dict[str, str] = {}
    for entry in root.rglob("*"):
        name = entry.relative_to(root).as_posix()
        if entry.is_symlink():
            raise TransactionError(f"untracked backup symlink: {name}")
        if entry.is_dir():
            if name not in {"lua", "files", "files/fake"}:
                raise TransactionError(f"foreign untracked backup directory: {name}")
        elif entry.is_file() and resource_path(name):
            body = entry.read_bytes()
            if not body or len(body) > 2 * 1024 * 1024:
                raise TransactionError(f"invalid untracked backup size: {name}")
            files[name] = sha256(body)
        else:
            raise TransactionError(f"foreign untracked backup entry: {name}")
        if len(files) > 4096:
            raise TransactionError("untracked backup count exceeded")
    return files


def snapshot_untracked() -> None:
    """Snapshot every original non-Git Lua/BIN byte without removing live files."""
    if BACKUP_ROOT.is_symlink() or not BACKUP_ROOT.is_dir():
        raise TransactionError("unsafe upstream backup root")
    _owned()
    tracked = tracked_resources(RUNTIME, GIT)
    actual = installed_resources(RUNTIME)
    managed = previous_metadata(STATE / "installed.json")
    if set(tracked) & set(managed):
        raise TransactionError("upstream/managed resource overlap")
    for name, digest in {**tracked, **managed}.items():
        if actual.get(name) != digest:
            raise TransactionError(f"installed resource changed during snapshot: {name}")
    expected = {name: digest for name, digest in actual.items() if name not in tracked}
    root = BACKUP_ROOT / "untracked-resources"
    if root.exists() or root.is_symlink():
        raise TransactionError("previous untracked resource backup exists")
    root.mkdir(mode=0o700)
    try:
        for name, digest in sorted(expected.items()):
            body = validate_runtime_path(RUNTIME, name).read_bytes()
            if sha256(body) != digest:
                raise TransactionError(f"untracked resource changed during snapshot: {name}")
            _write_atomic(_safe_subdir(root, name), body)
        _sync_dir(root)
        if _untracked_inventory() != expected:
            raise TransactionError("untracked snapshot inventory mismatch")
    except Exception:
        shutil.rmtree(root)
        raise


def _attested_untracked() -> dict[str, str] | None:
    """Schema 1 is legacy; schema 2 attests the complete non-Git file set."""
    if ATTESTATION.is_symlink() or not ATTESTATION.is_file():
        raise TransactionError("upstream backup attestation missing or linked")
    try:
        evidence = json.loads(ATTESTATION.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise TransactionError("invalid upstream backup attestation") from exc
    if not isinstance(evidence, dict):
        raise TransactionError("invalid upstream backup attestation")
    old_keys = {"schema", "binaries", "managed_manifest_sha256"}
    if evidence.get("schema") == 1:
        if set(evidence) != old_keys or (BACKUP_ROOT / "untracked-resources").exists():
            raise TransactionError("invalid legacy attestation or foreign backup")
        return None
    if evidence.get("schema") != 2 or set(evidence) != old_keys | {"untracked"}:
        raise TransactionError("unsupported upstream attestation schema")
    expected = evidence["untracked"]
    if not isinstance(expected, dict) or len(expected) > 4096:
        raise TransactionError("invalid untracked snapshot inventory")
    for name, digest in expected.items():
        if (not isinstance(name, str) or not resource_path(name)
                or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise TransactionError("invalid untracked backup entry identity")
    if _untracked_inventory() != expected:
        raise TransactionError("untracked snapshot bytes changed")
    return expected


def verify_live_untracked() -> None:
    expected = _attested_untracked()
    if expected is None:
        return
    tracked = tracked_resources(RUNTIME, GIT)
    live = installed_resources(RUNTIME)
    actual = {name: digest for name, digest in live.items() if name not in tracked}
    if actual != expected:
        raise TransactionError("live untracked resource inventory changed")


def restore_untracked() -> None:
    """Restore absent originals only; do not overwrite conflicting live files."""
    expected = _attested_untracked()
    if expected is None:
        return
    tracked = tracked_resources(RUNTIME, GIT)
    if set(expected) & set(tracked):
        raise TransactionError("restoration would overwrite tracked upstream files")
    for name, digest in sorted(expected.items()):
        target = validate_runtime_path(RUNTIME, name)
        if target.exists() and sha256(target.read_bytes()) != digest:
            raise TransactionError(f"RESTORE_FAILED: live untracked conflict: {name}")
    for name in sorted(expected):
        target = validate_runtime_path(RUNTIME, name)
        if not target.exists():
            _write_atomic(target, (BACKUP_ROOT / "untracked-resources" / name).read_bytes())
    verify_live_untracked()


def _binary_snapshot_inventory() -> dict:
    """Enumerate only saved compiled binaries; reject links and foreign siblings."""
    binaries = BACKUP_ROOT / "binaries"
    if binaries.is_symlink():
        raise TransactionError("binary backup directory is a symlink")
    if not binaries.exists():
        return {"present": False, "dirs": [], "files": {}}
    if not binaries.is_dir():
        raise TransactionError("binary backup is not a directory")
    if {entry.name for entry in binaries.iterdir()} != {"my"}:
        raise TransactionError("unexpected binary backup entry")
    saved = binaries / "my"
    if saved.is_symlink() or not saved.is_dir():
        raise TransactionError("binary my backup missing or linked")
    dirs: list[str] = []
    files: dict[str, str] = {}
    for entry in saved.rglob("*"):
        relative = entry.relative_to(saved).as_posix()
        if entry.is_symlink():
            raise TransactionError(f"binary backup symlink: {relative}")
        if entry.is_dir():
            dirs.append(relative)
        elif entry.is_file():
            files[relative] = sha256(entry.read_bytes())
        else:
            raise TransactionError(f"unsafe binary backup entry: {relative}")
        if len(dirs) + len(files) > 4096:
            raise TransactionError("binary backup entry count exceeded")
    return {"present": True, "dirs": sorted(dirs), "files": files}


def _manifest_identity() -> str | None:
    if STATE.is_symlink() or (STATE / "transaction").exists() or (STATE / "transaction").is_symlink():
        raise TransactionError("unfinished Additional Resources transaction blocks recovery")
    metadata = STATE / "installed.json"
    _owned_metadata(metadata)  # Reject unsafe or malformed ownership metadata.
    if not metadata.exists():
        return None
    return sha256(metadata.read_bytes())


def create_backup_attestation(expected_binaries: bool) -> None:
    """Commit saved binary/manifest identity before a prepared checkpoint."""
    if BACKUP_ROOT.is_symlink() or not BACKUP_ROOT.is_dir():
        raise TransactionError("unsafe upstream backup root")
    if ATTESTATION.exists() or ATTESTATION.is_symlink():
        raise TransactionError("previous upstream backup attestation exists")
    inventory = _binary_snapshot_inventory()
    if inventory["present"] != expected_binaries:
        raise TransactionError("binary backup presence differs from checkpoint")
    # Saved managed files also need to be intact before the checkpoint is armed.
    verify_snapshot()
    resource_root = BACKUP_ROOT / "untracked-resources"
    if resource_root.is_symlink():
        raise TransactionError("untracked snapshot is linked")
    evidence = {"schema": 1, "binaries": inventory, "managed_manifest_sha256": _manifest_identity()}
    if resource_root.exists():
        evidence["schema"] = 2
        evidence["untracked"] = _untracked_inventory()
    _write_atomic(ATTESTATION, (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode())
    _sync_dir(BACKUP_ROOT)


def verify_backup_attestation(expected_binaries: bool) -> None:
    """Fail closed on lost/altered saved bytes without requiring live binaries/Lua."""
    if BACKUP_ROOT.is_symlink() or not BACKUP_ROOT.is_dir() or ATTESTATION.is_symlink() or not ATTESTATION.is_file():
        raise TransactionError("upstream backup attestation missing or linked")
    try:
        evidence = json.loads(ATTESTATION.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise TransactionError("invalid upstream backup attestation") from exc
    if not isinstance(evidence, dict) or evidence.get("schema") not in (1, 2):
        raise TransactionError("unsupported upstream backup attestation")
    if (evidence["schema"] == 1 and set(evidence) !=
            {"schema", "binaries", "managed_manifest_sha256"}) or (
            evidence["schema"] == 2 and set(evidence) !=
            {"schema", "binaries", "managed_manifest_sha256", "untracked"}):
        raise TransactionError("unrecognized upstream backup attestation entries")
    _attested_untracked()
    manifest = evidence["managed_manifest_sha256"]
    if manifest is not None and (not isinstance(manifest, str) or re.fullmatch(r"[0-9a-f]{64}", manifest) is None):
        raise TransactionError("invalid saved managed manifest digest")
    inventory = _binary_snapshot_inventory()
    if inventory["present"] != expected_binaries or evidence["binaries"] != inventory:
        raise TransactionError("compiled binary backup changed since snapshot")
    if manifest != _manifest_identity():
        raise TransactionError("managed resource manifest changed since snapshot")
    verify_snapshot()

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




def _commit_sha(ref: str) -> str:
    """Resolve a full immutable commit OID, not a mutable tag or FETCH_HEAD."""
    result = subprocess.run(
        [GIT, "-C", str(RUNTIME), "rev-parse", "--verify", ref + "^{commit}"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    sha = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise TransactionError("cannot resolve upstream Git commit: " + ref)
    return sha


def _mutating_old_identity() -> str:
    checkpoint = BACKUP_ROOT / "checkpoint"
    if BACKUP_ROOT.is_symlink() or not BACKUP_ROOT.is_dir() or checkpoint.is_symlink() or not checkpoint.is_file():
        raise TransactionError("upstream checkpoint missing or linked")
    try:
        lines = checkpoint.read_text(encoding="ascii").splitlines()
    except UnicodeError as exc:
        raise TransactionError("non-ASCII upstream checkpoint") from exc
    if (len(lines) != 6 or lines[0] != "schema=2" or
            lines[5] != "phase=mutating" or
            not re.fullmatch(r"previous_commit=[0-9a-f]{40}", lines[1])):
        raise TransactionError("valid mutating checkpoint required for target binding")
    return lines[1].split("=", 1)[1]


def bind_target(release: str, sha: str) -> None:
    """Seal fetched target before Lua/BIN pruning or checkout, under original FD9."""
    if (os.environ.get("SETUP_TRANSACTION_LOCK_OWNER") != "1" or
            os.environ.get("UPSTREAM_RUNTIME_LIFECYCLE_OWNER") != "1" or
            os.environ.get("STRATEGY_LAB_LIFECYCLE_OWNER") != "1"):
        raise TransactionError("target binding requires both lifecycle locks")
    try:
        os.fstat(9)
    except OSError as exc:
        raise TransactionError("native lifecycle FD9 unavailable") from exc
    if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+)+", release):
        raise TransactionError("invalid selected upstream release")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise TransactionError("invalid selected upstream commit")
    if TARGET_IDENTITY.exists() or TARGET_IDENTITY.is_symlink():
        raise TransactionError("upstream target identity already sealed")
    old = _mutating_old_identity()
    if _commit_sha("HEAD") != old:
        raise TransactionError("old checkout changed before target binding")
    if _commit_sha("FETCH_HEAD") != sha or _commit_sha("refs/tags/" + release) != sha:
        raise TransactionError("selected release tag, fetched commit and SHA differ")
    verify_backup_attestation(_binary_snapshot_inventory()["present"])
    record = {"schema": 1, "previous_commit": old,
              "target_release": release, "target_commit": sha}
    _write_atomic(TARGET_IDENTITY, (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
    _sync_dir(BACKUP_ROOT)


def verify_target_identity(ref: str | None = None) -> dict:
    """Read-only verification even when checkout or tracked worktree is partial."""
    old = _mutating_old_identity()
    if TARGET_IDENTITY.is_symlink() or not TARGET_IDENTITY.is_file():
        raise TransactionError("upstream target identity missing or linked")
    try:
        identity = json.loads(TARGET_IDENTITY.read_text(encoding="ascii"))
    except (ValueError, UnicodeError) as exc:
        raise TransactionError("invalid upstream target identity") from exc
    if (not isinstance(identity, dict) or set(identity) !=
            {"schema", "previous_commit", "target_release", "target_commit"} or
            identity["schema"] != 1 or identity["previous_commit"] != old or
            not isinstance(identity["target_release"], str) or
            not re.fullmatch(r"v[0-9]+(?:\.[0-9]+)+", identity["target_release"]) or
            not isinstance(identity["target_commit"], str) or
            not re.fullmatch(r"[0-9a-f]{40}", identity["target_commit"])):
        raise TransactionError("malformed or contradictory upstream target identity")
    target = identity["target_commit"]
    if _commit_sha(target) != target or _commit_sha(old) != old:
        raise TransactionError("saved old/target Git objects unavailable")
    if _commit_sha("refs/tags/" + identity["target_release"]) != target:
        raise TransactionError("upstream release tag differs from sealed target")
    if ref is not None and _commit_sha(ref) != target:
        raise TransactionError("Git checkout target differs from sealed commit")
    return identity


def _git_target_names(ref: str) -> set[str]:
    """Inspect target tracked Lua/BIN paths without touching installed files.

    A Git commit ref is resolved by Git, not guessed from a moving upstream.
    """
    if not re.fullmatch(r"[A-Za-z0-9_./^{}-]{1,100}", ref):
        raise TransactionError("invalid target Git revision")
    result = subprocess.run(
        [GIT, "-C", str(RUNTIME), "ls-tree", "-r", "-z", ref,
         "--", "lua", "files/fake"],
        capture_output=True, timeout=30, check=False,
    )
    if result.returncode:
        raise TransactionError("target upstream Git tree cannot be inspected")
    names: set[str] = set()
    for item in result.stdout.split(b"\0"):
        if not item:
            continue
        try:
            header, raw = item.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            name = raw.decode("utf-8", "strict")
        except (ValueError, UnicodeError) as exc:
            raise TransactionError("malformed target upstream tree") from exc
        if not resource_path(name):
            continue
        if (mode not in {"100644", "100755"} or kind != "blob"
                or not re.fullmatch(r"[0-9a-f]{40}", oid) or name in names):
            raise TransactionError(f"unsafe target upstream Git resource: {name}")
        names.add(name)
        if len(names) > 4096:
            raise TransactionError("target upstream resource limit exceeded")
    return names


def _protect_config_paths(names: set[str]) -> None:
    """Fail closed when a saved OPNsense strategy uses a removed/replaced path."""
    if RUNTIME != Path("/usr/local/etc/zapret2") or not names:
        return
    config = Path("/conf/config.xml")
    if config.is_symlink():
        raise TransactionError("saved OPNsense configuration is symlinked")
    if config.is_file():
        raw = config.read_bytes()
        for name in sorted(names):
            if name.encode() in raw or name.rsplit("/", 1)[1].encode() in raw:
                raise TransactionError(f"saved strategy references replaced/removed resource: {name}")


def _require_clean_upstream_tree() -> None:
    """A hard reset must not destroy modifications to unrelated tracked files."""
    status = subprocess.run(
        [GIT, "-C", str(RUNTIME), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True, timeout=30, check=False,
    )
    if status.returncode != 0:
        raise TransactionError("cannot verify complete upstream tracked working tree")
    if status.stdout.strip():
        raise TransactionError("upstream contains modified tracked files; refusing checkout/reset")


def preflight_switch(ref: str = "FETCH_HEAD") -> list[str]:
    """Read-only old and target check; tolerate only non-Git original orphans."""
    _require_clean_upstream_tree()
    managed = _owned()
    upstream = tracked_resources(RUNTIME, GIT)
    live = installed_resources(RUNTIME)
    if set(upstream) & set(managed):
        raise TransactionError("an additional resource is now upstream-owned")
    original = {**upstream, **managed}
    for name, digest in original.items():
        if live.get(name) != digest:
            raise TransactionError(f"original tracked or managed resource drift: {name}")
    desired = _git_target_names(ref)
    collisions = sorted(set(managed) & desired)
    if collisions:
        raise TransactionError("target upstream conflicts with managed extras: "
                               + ", ".join(collisions[:5]))
    orphans = sorted(set(live) - set(original))
    # A target can adopt an orphan's filename but not its historical semantics.
    _protect_config_paths(set(orphans) | (set(upstream) - desired))
    return orphans


def prune_orphans(ref: str = "FETCH_HEAD") -> None:
    """Remove only previously attested non-managed bytes; leave Git/extra files."""
    if BACKUP_ROOT.is_symlink() or not BACKUP_ROOT.is_dir():
        raise TransactionError("no safe upstream snapshot to reconcile")
    inventory = _binary_snapshot_inventory()
    verify_backup_attestation(inventory["present"])
    original = _attested_untracked()
    if original is None:
        raise TransactionError("full original Lua/BIN attestation required")
    orphans = preflight_switch(ref)
    verify_target_identity(ref)
    live = installed_resources(RUNTIME)
    upstream = tracked_resources(RUNTIME, GIT)
    current = {name: digest for name, digest in live.items() if name not in upstream}
    if current != original:
        raise TransactionError("original non-Git Lua/BIN changed after snapshot")
    managed = previous_metadata(STATE / "installed.json")
    if set(orphans) != set(original) - set(managed):
        raise TransactionError("orphan plan and original snapshot disagree")
    # The setup wrapper must have written a recoverable 'mutating' intent.
    checkpoint = BACKUP_ROOT / "checkpoint"
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise TransactionError("upstream mutation checkpoint is unavailable")
    lines = checkpoint.read_text(encoding="ascii").splitlines()
    if len(lines) != 6 or lines[0] != "schema=2" or lines[5] != "phase=mutating":
        raise TransactionError("upstream mutation checkpoint is not armed")
    old = subprocess.run([GIT, "-C", str(RUNTIME), "rev-parse", "--verify", "HEAD"],
                         capture_output=True, text=True, timeout=30, check=False)
    if old.returncode or lines[1] != "previous_commit=" + old.stdout.strip():
        raise TransactionError("mutating checkpoint does not identify current old Git HEAD")
    if lines[4] != "previous_binaries=" + ("1" if inventory["present"] else "0"):
        raise TransactionError("checkpoint and attested binary snapshot disagree")
    for name in orphans:
        path = validate_runtime_path(RUNTIME, name)
        if not path.is_file() or sha256(path.read_bytes()) != original[name]:
            raise TransactionError(f"orphan changed before removal: {name}")
        path.unlink()
    if orphans:
        _sync_dir(RUNTIME / "lua")
        _sync_dir(RUNTIME / "files/fake")
    verify_exact()


def verify_switch_complete() -> None:
    """Target Git HEAD and managed extras are exact; old backup still attested."""
    if _attested_untracked() is None:
        raise TransactionError("new upstream switch lacks full original snapshot")
    verify_target_identity("HEAD")
    verify_exact()


def verify_exact() -> None:
    """Read-only exact-set check: native upstream HEAD plus pinned extras."""
    _owned()
    upstream = tracked_resources(RUNTIME, GIT)
    actual = installed_resources(RUNTIME)
    managed = previous_metadata(STATE / "installed.json")
    if set(upstream) & set(managed):
        raise TransactionError("an additional resource is now upstream-owned")
    expected = set(upstream) | set(managed)
    if set(actual) != expected:
        extra = sorted(set(actual) - expected)
        missing = sorted(expected - set(actual))
        raise TransactionError(
            "exact upstream/extras set is not satisfied; "
            f"unexpected={extra[:3]} missing={missing[:3]}; "
            "run the manual Additional Resources action on the current version"
        )
    for name, digest in upstream.items():
        if actual[name] != digest:
            raise TransactionError(f"upstream tracked resource drift: {name}")
    for name, digest in managed.items():
        if actual[name] != digest:
            raise TransactionError(f"managed resource drift: {name}")


def preflight_exact(ref: str = "FETCH_HEAD") -> None:
    """Old HEAD must be exactly reconciled before the Git checkout starts."""
    verify_exact()
    preflight_switch(ref)

def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {"preflight", "preflight-exact", "preflight-switch", "prune-orphans", "verify-switch-complete", "verify-exact", "snapshot", "verify", "verify-snapshot", "restore", "snapshot-untracked", "verify-live-untracked", "restore-untracked", "snapshot-evidence", "verify-evidence", "bind-target", "verify-target", "inspect-target", "inspect-checkout"}:
        print("usage: extra_resources_upstream_guard.py {preflight [COMMIT]|preflight-exact [COMMIT]|verify-exact|snapshot|verify|verify-snapshot|restore|snapshot-evidence 0|1|verify-evidence 0|1}", file=sys.stderr)
        return 64
    try:
        if argv[1] == "bind-target":
            if len(argv) != 4:
                return 64
            bind_target(argv[2], argv[3])
        elif argv[1] == "inspect-checkout":
            if len(argv) != 2:
                return 64
            identity = verify_target_identity()
            report = inspect_checkout(RUNTIME, GIT, identity["previous_commit"], identity["target_commit"])
            print("checkout_origin=" + json.dumps(report, sort_keys=True, separators=(",", ":")))
            return 0
        elif argv[1] in {"verify-target", "inspect-target"}:
            if len(argv) != 2:
                return 64
            identity = verify_target_identity()
            if argv[1] == "inspect-target":
                print("target_release=" + identity["target_release"])
                print("target_commit=" + identity["target_commit"])
        elif argv[1] in {"preflight", "preflight-exact", "preflight-switch", "prune-orphans"}:
            if len(argv) > 3:
                return 64
            if argv[1] == "preflight":
                preflight(argv[2] if len(argv) == 3 else "FETCH_HEAD")
            elif argv[1] == "preflight-exact":
                preflight_exact(argv[2] if len(argv) == 3 else "FETCH_HEAD")
            elif argv[1] == "preflight-switch":
                preflight_switch(argv[2] if len(argv) == 3 else "FETCH_HEAD")
            else:
                prune_orphans(argv[2] if len(argv) == 3 else "FETCH_HEAD")
        elif argv[1] == "verify-switch-complete":
            if len(argv) != 2:
                return 64
            verify_switch_complete()
        elif argv[1] == "verify-exact":
            if len(argv) != 2:
                return 64
            verify_exact()
        elif argv[1] in {"snapshot-evidence", "verify-evidence"}:
            if len(argv) != 3 or argv[2] not in {"0", "1"}:
                return 64
            if argv[1] == "snapshot-evidence":
                create_backup_attestation(argv[2] == "1")
            else:
                verify_backup_attestation(argv[2] == "1")
        elif len(argv) != 2:
            return 64
        elif argv[1] == "snapshot":
            snapshot()
        elif argv[1] == "snapshot-untracked":
            snapshot_untracked()
        elif argv[1] == "verify-live-untracked":
            verify_live_untracked()
        elif argv[1] == "restore-untracked":
            restore_untracked()
        elif argv[1] == "verify":
            verify()
        elif argv[1] == "verify-snapshot":
            verify_snapshot()
        else:
            restore()
        print("PASS: managed additional resources are preserved")
        return 0
    except (TransactionError, PreflightError, InspectError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"RESOURCE_UPSTREAM_GUARD_FAILED: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
