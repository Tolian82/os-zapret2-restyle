#!/usr/local/bin/python3.13
"""Read-only, point-in-time origin classification of a partial upstream checkout.

This is diagnostic evidence, NOT permission to reset a dirty Git worktree.
Untracked files, concurrent edits, and a matching blob created by a third
party cannot be attributed to the updater. Never modifies Git or the runtime.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess

MAX_TRACKED = 30000
MAX_BYTES_PER_FILE = 256 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{40}\Z")


class InspectError(ValueError):
    pass


def _git(git: str, runtime: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(
            [git, "-C", str(runtime), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InspectError("unable to inspect upstream Git metadata") from exc
    if proc.returncode:
        raise InspectError("unable to inspect upstream Git metadata")
    return proc.stdout


def _path(raw: bytes) -> str:
    try:
        name = raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise InspectError("non-UTF8 tracked pathname") from exc
    parts = name.split("/")
    if (not name or name.startswith("/") or any(p in ("", ".", "..") for p in parts)
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in name)):
        raise InspectError("unsafe tracked pathname")
    return name


def _tree(git: str, runtime: Path, commit: str) -> dict[str, tuple[str, str]]:
    tree = {}
    for item in _git(git, runtime, "ls-tree", "-rz", commit).split(bytes([0])):
        if not item:
            continue
        try:
            header, raw = item.split(b"\t", 1)
            mode, kind, blob = header.decode("ascii").split()
        except (UnicodeError, ValueError) as exc:
            raise InspectError("invalid Git tree record") from exc
        name = _path(raw)
        # A symlink/gitlink is recorded, but never dereferenced for inspection.
        if (kind not in ("blob", "commit") or mode not in
                ("100644", "100755", "120000", "160000") or
                not SHA.fullmatch(blob)):
            raise InspectError("unsupported Git tree entry")
        if name in tree or len(tree) >= MAX_TRACKED:
            raise InspectError("duplicate or excessive Git tree paths")
        tree[name] = (mode, blob)
    return tree


def _index(git: str, runtime: Path) -> dict[str, list[tuple[str, str, str]]]:
    index = {}
    for item in _git(git, runtime, "ls-files", "--stage", "-z").split(bytes([0])):
        if not item:
            continue
        try:
            header, raw = item.split(b"\t", 1)
            mode, blob, stage = header.decode("ascii").split()
        except (UnicodeError, ValueError) as exc:
            raise InspectError("invalid Git index record") from exc
        name = _path(raw)
        if not SHA.fullmatch(blob) or mode not in ("100644", "100755", "120000", "160000") or stage not in ("0", "1", "2", "3"):
            raise InspectError("unsafe Git index entry")
        index.setdefault(name, []).append((mode, blob, stage))
        if len(index) > MAX_TRACKED:
            raise InspectError("excessive Git index paths")
    return index


def _worktree_entry(runtime: Path, name: str) -> tuple[str, str] | str | None:
    # Use directory descriptors to reject symlink ancestors and TOCTOU path
    # replacement. Never open FIFOs, devices, or symlinks as regular files.
    fd = None
    try:
        fd = os.open(runtime, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        parts = name.split("/")
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES_PER_FILE:
                return "unsafe"
            h = hashlib.sha1()
            h.update(f"blob {info.st_size}\0".encode("ascii"))
            with os.fdopen(os.dup(file_fd), "rb") as stream:
                while True:
                    block = stream.read(1024 * 1024)
                    if not block:
                        break
                    h.update(block)
            if os.fstat(file_fd).st_size != info.st_size:
                return "unsafe"
            mode = "100755" if info.st_mode & 0o111 else "100644"
            return mode, h.hexdigest()
        finally:
            os.close(file_fd)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return "unsafe"
    finally:
        if fd is not None:
            os.close(fd)


def _origin(value: tuple[str, str] | str | None,
            old: tuple[str, str] | None,
            target: tuple[str, str] | None) -> str:
    if value == "unsafe":
        return "unsafe"
    matches_old = value == old
    matches_target = value == target
    if matches_old and matches_target:
        return "both"
    if matches_old:
        return "old"
    if matches_target:
        return "target"
    return "missing" if value is None else "foreign"


def inspect_checkout(runtime: Path, git: str, old: str, target: str) -> dict:
    """Return bounded, read-only classifications; *never* a reset authorization."""
    if not SHA.fullmatch(old) or not SHA.fullmatch(target):
        raise InspectError("invalid sealed commit identities")
    if runtime.is_symlink() or (runtime / ".git").is_symlink():
        raise InspectError("linked upstream runtime or Git metadata")
    old_tree = _tree(git, runtime, old)
    target_tree = _tree(git, runtime, target)
    index = _index(git, runtime)
    paths = set(old_tree) | set(target_tree) | set(index)
    if len(paths) > MAX_TRACKED:
        raise InspectError("excessive checkout inspection scope")
    head = _git(git, runtime, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    head_origin = "old" if head == old else "target" if head == target else "foreign"
    counts = {"index": {}, "worktree": {}}
    anomalies = []
    anomaly_count = 0
    for name in sorted(paths):
        previous = old_tree.get(name)
        selected = target_tree.get(name)
        stages = index.get(name, [])
        if len(stages) == 1 and stages[0][2] == "0":
            stage = stages[0][:2]
        elif stages:
            stage = "unsafe"
        else:
            stage = None
        # Index-only entries outside both sealed commits are foreign, not
        # proof that the updater adopted/created them.
        stage_origin = _origin(stage, previous, selected)
        live_origin = _origin(_worktree_entry(runtime, name), previous, selected)
        for group, outcome in (("index", stage_origin), ("worktree", live_origin)):
            counts[group][outcome] = counts[group].get(outcome, 0) + 1
        if stage_origin in ("foreign", "missing", "unsafe") or live_origin in ("foreign", "missing", "unsafe"):
            anomaly_count += 1
            if len(anomalies) < 20:
                anomalies.append({"path": name, "index": stage_origin, "worktree": live_origin})
    return {
        "schema": 1, "mode": "read-only-point-in-time",
        "old_commit": old, "target_commit": target, "head": head_origin,
        "tracked_paths": len(paths), "index": counts["index"],
        "worktree": counts["worktree"], "anomalies_sample": anomalies,
        "anomalies_truncated": anomaly_count > len(anomalies),
        "automatic_dirty_reset_authorized": False,
        "untracked_files_inspected": False,
    }
