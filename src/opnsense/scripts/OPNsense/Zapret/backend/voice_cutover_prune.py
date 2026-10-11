#!/usr/bin/env python3
"""Voice rollback reclaim phase two: write-ahead, inode-pinned candidate pruning.

This private native-only helper can remove files ONLY inside the previously
SHA-verified, quarantined old candidate, after a durable per-entry inventory
has been fsync'd. It keeps the quarantine root inode, all redo, backup,
receipt, cleanup and whole journals, Config/runtime, processes and IPFW.

After a crash, every remaining entry MUST be a byte-for-byte, same-inode
subset of the sealed inventory; unexpected paths or altered survivors refuse.
No automatic reboot replay, GUI command, journal close or Voice ON.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir, MAX_FILES, MAX_BYTES
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_cleanup_prepare import read_cleanup_plan
from voice_cutover_recovery_receipt import read_receipt
from voice_cutover_runtime_restore import _read_redo, _safe_parent
from voice_native_file_observer import _hash_file, observe_live_files
from voice_native_recovery_quiescence import _locked_config
from voice_cutover_reclaim import read_reclaim_intent, expected_reclaim_intent

NAME = "previous-prune-intent.json"
MAX_MANIFEST = 4 * 1024 * 1024
MAX_DEPTH = 32
HEX = set("0123456789abcdef")
DIR = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


class PruneError(RuntimeError):
    pass


def _digest(fields):
    return hashlib.sha256(json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _sha(value):
    return type(value) is str and len(value) == 64 and set(value) <= HEX


def _valid_rel(name):
    return (isinstance(name, str) and bool(name)
            and len(os.fsencode(name)) < 4096
            and all(part not in ("", ".", "..") for part in name.split("/"))
            and "\x00" not in name)


def _validate(obj):
    required = {"schema", "phase", "original_check", "terminal_check",
                "plan_check", "reclaim_check", "candidate_sha256",
                "parent_dev", "parent_inode", "held_name",
                "root_dev", "root_inode", "root_uid", "root_mode",
                "entries", "check"}
    if not isinstance(obj, dict) or set(obj) != required or (
        type(obj["schema"]) is not int or obj["schema"] != 1
        or obj["phase"] != "prune-write-ahead"
    ):
        raise PruneError("invalid Voice prune journal schema")
    for name in ("original_check", "terminal_check", "plan_check",
                 "reclaim_check", "candidate_sha256", "check"):
        if not _sha(obj[name]):
            raise PruneError("invalid Voice prune checksum field")
    for name in ("parent_dev", "parent_inode", "root_dev", "root_inode",
                 "root_uid", "root_mode"):
        if type(obj[name]) is not int or obj[name] < 0:
            raise PruneError("invalid Voice prune filesystem identity")
    if obj["held_name"] != ".voice-reclaim-held-" + obj["original_check"][:20]:
        raise PruneError("foreign Voice prune quarantine name")
    if not isinstance(obj["entries"], list) or len(obj["entries"]) > MAX_FILES:
        raise PruneError("invalid Voice prune entry inventory")
    seen = set()
    for row in obj["entries"]:
        if not isinstance(row, dict) or set(row) != {
            "path", "kind", "dev", "ino", "uid", "mode", "size", "sha256",
        } or not _valid_rel(row["path"]) or row["path"] in seen:
            raise PruneError("invalid or duplicate Voice prune inventory path")
        seen.add(row["path"])
        if row["kind"] not in ("file", "dir"):
            raise PruneError("unsafe Voice prune file type")
        for key in ("dev", "ino", "uid", "mode", "size"):
            if type(row[key]) is not int or row[key] < 0:
                raise PruneError("invalid Voice prune entry metadata")
        if row["kind"] == "dir":
            if row["size"] != 0 or row["sha256"] is not None:
                raise PruneError("invalid Voice prune directory row")
        elif not _sha(row["sha256"]):
            raise PruneError("invalid Voice prune file hash")
    if _digest({k:v for k,v in obj.items() if k != "check"}) != obj["check"]:
        raise PruneError("Voice prune inventory checksum mismatch")
    return obj


def read_prune_intent(directory: Path):
    root = Path(directory)
    _private_dir(root)
    try:
        fd = os.open(root / NAME, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (
            info.st_uid != os.geteuid() or info.st_mode & 0o077
            or info.st_size > MAX_MANIFEST
        ):
            raise PruneError("unsafe Voice prune journal")
        raw = stream.read(MAX_MANIFEST + 1)
    if len(raw) > MAX_MANIFEST:
        raise PruneError("oversized Voice prune journal")
    try:
        return _validate(json.loads(raw))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PruneError("corrupt Voice prune journal") from exc


def _meta(info, name, kind, sha=None):
    if info.st_uid != os.geteuid() or info.st_dev < 0 or info.st_ino < 1:
        raise PruneError("untrusted Voice prune entry owner")
    if kind == "file" and (not stat.S_ISREG(info.st_mode)
                           or info.st_nlink != 1 or info.st_size > MAX_BYTES):
        raise PruneError("untrusted Voice prune regular file")
    if kind == "dir" and not stat.S_ISDIR(info.st_mode):
        raise PruneError("untrusted Voice prune subdirectory")
    return {"path":name, "kind":kind, "dev":info.st_dev, "ino":info.st_ino,
            "uid":info.st_uid, "mode":stat.S_IMODE(info.st_mode),
            "size":info.st_size if kind == "file" else 0,
            "sha256":sha if kind == "file" else None}


def _scan(fd, prefix="", depth=0, out=None):
    if out is None:
        out = []
    if depth > MAX_DEPTH:
        raise PruneError("Voice candidate tree too deep to prune")
    for name in sorted(os.listdir(fd)):
        rel = prefix + name
        if not _valid_rel(rel) or len(out) >= MAX_FILES:
            raise PruneError("unbounded Voice candidate prune inventory")
        before = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(before.st_mode):
            child = os.open(name, DIR, dir_fd=fd)
            try:
                if os.fstat(child).st_ino != before.st_ino or (
                    os.fstat(child).st_dev != before.st_dev
                ):
                    raise PruneError("Voice prune directory changed during open")
                out.append(_meta(before, rel, "dir"))
                _scan(child, rel + "/", depth + 1, out)
            finally:
                os.close(child)
        elif stat.S_ISREG(before.st_mode):
            sha, size, mode = _hash_file(name, parent_fd=fd)
            after = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if (before.st_ino, before.st_dev, before.st_uid, before.st_size,
                stat.S_IMODE(before.st_mode)) != (
                after.st_ino, after.st_dev, after.st_uid, after.st_size,
                stat.S_IMODE(after.st_mode)
            ) or size != before.st_size or mode != stat.S_IMODE(before.st_mode):
                raise PruneError("Voice prune file changed during inventory")
            out.append(_meta(before, rel, "file", sha))
        else:
            raise PruneError("unexpected Voice prune symlink or special file")
    return out


def _open_held(parent: Path, expected: dict) -> int:
    parentinfo = _safe_parent(parent)
    if (parentinfo.st_dev, parentinfo.st_ino) != (
        expected["parent_dev"], expected["parent_inode"]
    ):
        raise PruneError("Voice runtime parent changed")
    pfd = os.open(parent, DIR)
    try:
        pstat = os.fstat(pfd)
        if (pstat.st_dev, pstat.st_ino) != (
            expected["parent_dev"], expected["parent_inode"]
        ):
            raise PruneError("Voice runtime parent changed while opening")
        held = os.open(expected["held_name"], DIR, dir_fd=pfd)
    finally:
        os.close(pfd)
    root = os.fstat(held)
    if (root.st_dev, root.st_ino, root.st_uid, stat.S_IMODE(root.st_mode)) != (
        expected["root_dev"], expected["root_inode"],
        expected["root_uid"], expected["root_mode"]
    ):
        os.close(held)
        raise PruneError("quarantined Voice runtime root identity changed")
    return held


def _check_inventory(fd, marker):
    sealed = {row["path"]:row for row in marker["entries"]}
    actual = _scan(fd)
    for row in actual:
        if row["path"] not in sealed or sealed[row["path"]] != row:
            raise PruneError("Voice prune candidate contains foreign/altered survivor")
    return actual


def inspect_prune_placement(*, directory, parent, reclaim_record, plan,
                            journal_record, quarantine_name):
    """Read-only proof of an interrupted prune; never permit Voice ON."""
    marker = read_prune_intent(directory)
    if marker is None:
        raise PruneError("Voice prune inventory absent")
    if marker["reclaim_check"] != reclaim_record["check"] or (
        marker["original_check"] != reclaim_record["original_check"]
        or marker["terminal_check"] != journal_record["check"]
        or marker["plan_check"] != plan["check"]
        or marker["candidate_sha256"] != reclaim_record["candidate_sha256"]
        or marker["held_name"] != quarantine_name
        or (marker["parent_dev"], marker["parent_inode"]) != (
            reclaim_record["parent_dev"], reclaim_record["parent_inode"]
        )
    ):
        raise PruneError("foreign Voice prune predecessor evidence")
    fd = _open_held(Path(parent), marker)
    try:
        remaining = _check_inventory(fd, marker)
    finally:
        os.close(fd)
    return "candidate-pruned-retained-root" if not remaining else "candidate-prune-interrupted"


def _publish(directory, record):
    if read_prune_intent(directory) is not None:
        raise PruneError("Voice prune marker already exists")
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(raw) > MAX_MANIFEST:
        raise PruneError("Voice prune inventory exceeds durable journal size")
    fd = os.open(Path(directory) / NAME,
                 os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    _sync_dir(Path(directory))
    if read_prune_intent(directory) != record:
        raise PruneError("Voice prune journal not durable")


def _parentfd(rootfd, rel):
    parts = rel.split("/")
    fd = os.dup(rootfd)
    try:
        for component in parts[:-1]:
            child = os.open(component, DIR, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def _remove_pinned_entry(rootfd, row, require_lifecycle_owner,
                         config_path, config_fd, config_owner):
    parentfd, name = _parentfd(rootfd, row["path"])
    try:
        info = os.stat(name, dir_fd=parentfd, follow_symlinks=False)
        if _meta(info, row["path"], row["kind"],
                 _hash_file(name,parent_fd=parentfd)[0] if row["kind"]=="file"
                 else None) != row:
            raise PruneError("Voice prune entry changed before unlink")
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        if row["kind"] == "file":
            os.unlink(name, dir_fd=parentfd)
        else:
            os.rmdir(name, dir_fd=parentfd)
        os.fsync(parentfd)
    finally:
        os.close(parentfd)


def prune_quarantined_candidate(
    *, journal, ledger, previous_backup, process_evidence, security_evidence,
    install_image, config_path, active_runtime, probe, adapter, config_fd,
    config_owner, require_lifecycle_owner,
):
    """Private native-only candidate prune, interrupted/retried under BOTH locks."""
    from voice_native_boot_recovery_review import inspect_boot_recovery
    config_path, active_runtime = Path(config_path), Path(active_runtime)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _pinned_regular(config_path, config_fd, owner=config_owner)
    report = inspect_boot_recovery(
        journal=journal, ledger=ledger, previous_backup=previous_backup,
        process_evidence=process_evidence, security_evidence=security_evidence,
        install_image=install_image, config_path=config_path,
        active_runtime=active_runtime, probe=probe, adapter=adapter,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if report["state"] != "previous-rollback-sealed-needs-manual-finalization" or (
        report["phase"] != "rolled_back" or report["config"] != "previous"
        or report["runtime"] != "previous" or report["kernel"] != "previous"
        or report["processes"] != "running"
        or report["previous_receipt"] != "process-epoch-matches-not-readiness"
        or report["candidate_reclaim"] not in (
            "candidate-quarantined", "candidate-prune-interrupted",
            "candidate-pruned-retained-root"
        ) or report["safe_to_close_intent"] is not False or report["voice_on"] is not False
    ):
        raise PruneError("current native five-resource rollback witness required")
    terminal = journal.read()
    plan = read_cleanup_plan(journal.directory)
    receipt = read_receipt(journal.directory)
    redo = _read_redo(journal.directory)
    reclaim = read_reclaim_intent(journal.directory)
    expected = expected_reclaim_intent(
        terminal=terminal, plan=plan, receipt=receipt, runtime_redo=redo,
        config_path=config_path, active_runtime=active_runtime,
    )
    if reclaim is None or reclaim != expected:
        raise PruneError("write-ahead quarantine evidence missing/foreign")
    marker = read_prune_intent(journal.directory)
    if marker is None:
        if report["candidate_reclaim"] != "candidate-quarantined":
            raise PruneError("cannot start candidate prune without full SHA preflight")
        base = {
            "schema":1, "phase":"prune-write-ahead",
            "original_check":reclaim["original_check"],
            "terminal_check":terminal["check"], "plan_check":plan["check"],
            "reclaim_check":reclaim["check"],
            "candidate_sha256":reclaim["candidate_sha256"],
            "parent_dev":reclaim["parent_dev"], "parent_inode":reclaim["parent_inode"],
            "held_name":reclaim["quarantine_name"],
        }
        parent = active_runtime.parent
        pfd = os.open(parent, DIR)
        try:
            rootfd = os.open(reclaim["quarantine_name"], DIR, dir_fd=pfd)
        finally:
            os.close(pfd)
        try:
            root = os.fstat(rootfd)
            if root.st_uid != os.geteuid():
                raise PruneError("foreign candidate directory root")
            entries = _scan(rootfd)
            if observe_live_files(
                Path(install_image)/"config.xml",
                active_runtime.parent / reclaim["quarantine_name"],
            )["runtime"] != reclaim["candidate_sha256"]:
                raise PruneError("candidate mutated before durable prune inventory")
            fields = {**base, "root_dev":root.st_dev, "root_inode":root.st_ino,
                      "root_uid":root.st_uid, "root_mode":stat.S_IMODE(root.st_mode),
                      "entries":entries}
            marker = _validate({**fields, "check":_digest(fields)})
        finally:
            os.close(rootfd)
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        _publish(journal.directory, marker)
    # This allows resumption only of a subset of previously exact-SHA-matched,
    # inode-pinned entries. Nothing unrelated or outside the fixed root unlinks.
    inspect_prune_placement(
        directory=journal.directory, parent=active_runtime.parent,
        reclaim_record=reclaim, plan=plan, journal_record=terminal,
        quarantine_name=reclaim["quarantine_name"],
    )
    fd = _open_held(active_runtime.parent, marker)
    try:
        remaining = _check_inventory(fd, marker)
        for row in sorted(remaining, key=lambda x:(
            -x["path"].count("/"), 0 if x["kind"]=="file" else 1,
            x["path"],
        )):
            _remove_pinned_entry(
                fd, row, require_lifecycle_owner,
                config_path, config_fd, config_owner,
            )
        os.fsync(fd)
    finally:
        os.close(fd)
    if inspect_prune_placement(
        directory=journal.directory, parent=active_runtime.parent,
        reclaim_record=reclaim, plan=plan, journal_record=terminal,
        quarantine_name=reclaim["quarantine_name"],
    ) != "candidate-pruned-retained-root":
        raise PruneError("candidate prune not complete")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if journal.read() != terminal or read_cleanup_plan(journal.directory) != plan or (
        read_receipt(journal.directory) != receipt
        or _read_redo(journal.directory) != redo
        or read_reclaim_intent(journal.directory) != reclaim
        or read_prune_intent(journal.directory) != marker
    ):
        raise PruneError("Voice rollback proofs changed during candidate prune")
    return {
        "state":"candidate-pruned-retained-root", "safe_to_close_intent":False,
        "voice_on":False,
    }
