#!/usr/local/bin/python3.13
"""Preserve *only* the extras owned by this plugin across upstream git checkout.

Invoked by the ordinary setup transaction while setup.lock is held.
No Git release, package metadata, OPNsense Config or user file is modified.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

from extra_resources_preflight import sha256, validate_runtime_path, resource_path
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


def verify_exact() -> None:
    """Read-only exact-set check at the current Git HEAD.

    Require prior manual extras reconciliation before release switching.
    Unknown/unowned resources are never deleted by the release updater.
    """
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
    """Both old and target inventories verified BEFORE checkout/Stop.

    This increment accepts only exact old sets and disjoint target resources.
    Deleting foreign files or reassigning an overlapping path is deferred
    until a separately attested old/target rollback is available.
    """
    verify_exact()
    desired = _git_target_names(ref)
    managed = previous_metadata(STATE / "installed.json")
    collisions = sorted(desired & set(managed))
    if collisions:
        raise TransactionError("target upstream conflicts with managed extras: "
                               + ", ".join(collisions[:5]))
    # Do not silently break saved strategies if a target drops a native file.
    removed = sorted(set(tracked_resources(RUNTIME, GIT)) - desired)
    if RUNTIME == Path("/usr/local/etc/zapret2"):
        config = Path("/conf/config.xml")
        if config.is_symlink():
            raise TransactionError("saved OPNsense configuration is symlinked")
        if config.is_file():
            raw = config.read_bytes()
            for name in removed:
                if name.encode() in raw or name.rsplit("/", 1)[1].encode() in raw:
                    raise TransactionError(f"saved strategy references removed upstream resource: {name}")

def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {"preflight", "preflight-exact", "verify-exact", "snapshot", "verify", "verify-snapshot", "restore", "snapshot-untracked", "verify-live-untracked", "restore-untracked", "snapshot-evidence", "verify-evidence"}:
        print("usage: extra_resources_upstream_guard.py {preflight [COMMIT]|preflight-exact [COMMIT]|verify-exact|snapshot|verify|verify-snapshot|restore|snapshot-evidence 0|1|verify-evidence 0|1}", file=sys.stderr)
        return 64
    try:
        if argv[1] in {"preflight", "preflight-exact"}:
            if len(argv) > 3:
                return 64
            if argv[1] == "preflight":
                preflight(argv[2] if len(argv) == 3 else "FETCH_HEAD")
            else:
                preflight_exact(argv[2] if len(argv) == 3 else "FETCH_HEAD")
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
    except (TransactionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"RESOURCE_UPSTREAM_GUARD_FAILED: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
