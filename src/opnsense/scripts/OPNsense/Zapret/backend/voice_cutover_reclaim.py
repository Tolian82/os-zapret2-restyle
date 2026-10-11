#!/usr/bin/env python3
"""Schema-4 Voice retired-candidate quarantine, phase one of rollback reclaim.

Write-ahead proof + same-parent rename only. Never delete a candidate tree,
redo, receipt, backup, Config, IPFW, or the whole-system intent. The marker is
write-once and binds the ORIGINAL MUTATING SHA to terminal ROLLED_BACK.
A crash either side of the directory rename is classifiable and retryable.
No CLI/boot hook: only an explicit native owner already holding original FD9
and Config inode flock may call stage_retired_candidate().
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA, mutating_predecessor
from voice_cutover_cleanup_prepare import read_cleanup_plan
from voice_cutover_recovery_receipt import read_receipt
from voice_cutover_runtime_restore import _read_redo, _safe_parent
from voice_native_file_observer import observe_live_files
from voice_native_recovery_quiescence import _locked_config
from voice_cutover_config_restore import _pinned_regular

NAME = "previous-reclaim-intent.json"
MAX_BYTES = 8192
HEX = frozenset("0123456789abcdef")


class ReclaimError(RuntimeError):
    pass


def _sha(value):
    return type(value) is str and len(value) == 64 and set(value) <= HEX


def _digest(fields):
    return hashlib.sha256(json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _validate(record):
    names = {
        "schema", "phase", "terminal_check", "original_check",
        "plan_check", "receipt_check", "runtime_redo_check",
        "candidate_sha256", "config_dev", "config_inode",
        "parent_dev", "parent_inode", "retired_name", "quarantine_name",
        "check",
    }
    if not isinstance(record, dict) or set(record) != names or (
        type(record["schema"]) is not int or record["schema"] != 1
        or record["phase"] != "quarantine-intent"
    ):
        raise ReclaimError("invalid Voice reclaim-intent schema")
    for key in ("terminal_check", "original_check", "plan_check",
                "receipt_check", "runtime_redo_check", "candidate_sha256",
                "check"):
        if not _sha(record[key]):
            raise ReclaimError("invalid Voice reclaim fingerprint")
    for key in ("config_dev", "config_inode", "parent_dev", "parent_inode"):
        if type(record[key]) is not int or record[key] < 0:
            raise ReclaimError("invalid Voice reclaim inode")
    suffix = record["original_check"][:20]
    if record["retired_name"] != ".voice-restore-retired-" + suffix or (
        record["quarantine_name"] != ".voice-reclaim-held-" + suffix
    ):
        raise ReclaimError("untrusted Voice reclaim directory name")
    if _digest({k:v for k,v in record.items() if k != "check"}) != record["check"]:
        raise ReclaimError("Voice reclaim intent checksum mismatch")
    return record


def read_reclaim_intent(directory: Path):
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
            or info.st_size > MAX_BYTES
        ):
            raise ReclaimError("unsafe reclaim-intent file")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ReclaimError("oversized reclaim-intent file")
    try:
        return _validate(json.loads(raw))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ReclaimError("corrupt reclaim-intent record") from exc


def expected_reclaim_intent(*, terminal, plan, receipt, runtime_redo,
                            config_path: Path, active_runtime: Path):
    """Fully bound expected marker, derived only from sealed, native evidence."""
    prior = mutating_predecessor(terminal)
    if terminal["schema"] != RUNTIME_BOUND_SCHEMA or (
        plan is None or receipt is None or runtime_redo is None
        or plan["whole_check"] != prior["check"]
        or receipt["whole_check"] != prior["check"]
        or plan["receipt_check"] != receipt["check"]
        or plan["retired_name"] != runtime_redo["retired_name"]
        or plan["runtime_redo_check"] != runtime_redo["checksum"]
        or plan["retired_sha256"] != prior["candidate"]["candidate_runtime_sha256"]
        or runtime_redo["cutover_check"] != prior["check"]
        or runtime_redo["candidate_sha256"] != plan["retired_sha256"]
        or runtime_redo["previous_sha256"] != prior["previous"]["runtime"]
        or runtime_redo["active_name"] != Path(active_runtime).name
    ):
        raise ReclaimError("reclaim requires a sealed, runtime-redo-bound rollback")
    cfg = os.lstat(config_path)
    parent = _safe_parent(Path(active_runtime).parent)
    if (cfg.st_dev, cfg.st_ino) != (
        plan["config_dev"], plan["config_inode"]
    ) or (receipt["config_dev"], receipt["config_inode"]) != (
        cfg.st_dev, cfg.st_ino
    ) or (parent.st_dev, parent.st_ino) != (
        runtime_redo["parent_dev"], runtime_redo["parent_ino"]
    ):
        raise ReclaimError("original Config/runtime directory identity changed")
    fields = {
        "schema":1, "phase":"quarantine-intent",
        "terminal_check":terminal["check"], "original_check":prior["check"],
        "plan_check":plan["check"], "receipt_check":receipt["check"],
        "runtime_redo_check":runtime_redo["checksum"],
        "candidate_sha256":plan["retired_sha256"],
        "config_dev":cfg.st_dev, "config_inode":cfg.st_ino,
        "parent_dev":parent.st_dev, "parent_inode":parent.st_ino,
        "retired_name":runtime_redo["retired_name"],
        "quarantine_name":".voice-reclaim-held-" + prior["check"][:20],
    }
    return _validate({**fields, "check":_digest(fields)})


def inspect_reclaim_placement(*, journal, plan, receipt, runtime_redo,
                              config_path: Path, active_runtime: Path,
                              install_config: Path):
    """READ-ONLY placement and exact candidate SHA check for native boot review."""
    from voice_cutover_prune import read_prune_intent, inspect_prune_placement
    record = journal.read()
    marker = read_reclaim_intent(journal.directory)
    prune = read_prune_intent(journal.directory)
    if record is None or record["phase"] != "rolled_back":
        if marker is not None or prune is not None:
            raise ReclaimError("reclaim intent without terminal rollback")
        return "not-applicable"
    if runtime_redo is None:
        if marker is not None or prune is not None:
            raise ReclaimError("reclaim marker without retired candidate redo")
        if plan is not None and plan["retired_name"] is not None:
            raise ReclaimError("retired plan without runtime redo")
        return "not-applicable"
    expected = expected_reclaim_intent(
        terminal=record, plan=plan, receipt=receipt, runtime_redo=runtime_redo,
        config_path=config_path, active_runtime=active_runtime,
    )
    if marker is not None and marker != expected:
        raise ReclaimError("foreign or changed reclaim-intent proof")
    root = Path(active_runtime).parent
    retired = root / expected["retired_name"]
    held = root / expected["quarantine_name"]
    ready = root / runtime_redo["ready_name"]
    if ready.exists() or ready.is_symlink():
        raise ReclaimError("foreign Voice runtime ready tree")
    a = retired.exists() or retired.is_symlink()
    b = held.exists() or held.is_symlink()
    if prune is not None:
        if marker is None or marker != expected or a or not b:
            raise ReclaimError("prune requires an exclusively quarantined candidate")
        return inspect_prune_placement(
            directory=journal.directory, parent=root, reclaim_record=marker,
            plan=plan, journal_record=record,
            quarantine_name=expected["quarantine_name"],
        )
    if a == b or (marker is None and b):
        raise ReclaimError("missing or duplicate retired/quarantined candidate")
    target = held if b else retired
    if target.is_symlink() or not target.is_dir() or (
        observe_live_files(install_config, target)["runtime"]
        != expected["candidate_sha256"]
    ):
        raise ReclaimError("untrusted Voice candidate retained tree")
    return ("candidate-quarantined" if b else
            "write-ahead-retired" if marker else "retired-awaiting-reclaim")


def _publish(root: Path, record: dict):
    if read_reclaim_intent(root) is not None:
        raise ReclaimError("reclaim write-once marker already exists")
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(raw) > MAX_BYTES:
        raise ReclaimError("oversized reclaim-intent")
    fd = os.open(root / NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    _sync_dir(root)
    if read_reclaim_intent(root) != record:
        raise ReclaimError("reclaim intent not durably published")


def stage_retired_candidate(
    *, journal, ledger, previous_backup, process_evidence, security_evidence,
    install_image, config_path, active_runtime, probe, adapter,
    config_fd, config_owner, require_lifecycle_owner,
):
    """Durably quarantine retired candidate; never unlink any data.

    Requires native FD9 + original Config flock and stable *current* old
    kernel/process observations; read-only boot review is the preflight.
    On retry the source can already be at the quarantine target.
    """
    from voice_native_boot_recovery_review import inspect_boot_recovery
    config_path = Path(config_path)
    active_runtime = Path(active_runtime)
    install_image = Path(install_image)
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
        or report["safe_to_close_intent"] is not False
        or report["voice_on"] is not False
    ):
        raise ReclaimError("native postrollback preflight not current or safe")
    record = journal.read()
    plan = read_cleanup_plan(journal.directory)
    receipt = read_receipt(journal.directory)
    redo = _read_redo(journal.directory)
    if redo is None:
        raise ReclaimError("no retired candidate to quarantine")
    expected = expected_reclaim_intent(
        terminal=record, plan=plan, receipt=receipt, runtime_redo=redo,
        config_path=config_path, active_runtime=active_runtime,
    )
    source_state = inspect_reclaim_placement(
        journal=journal, plan=plan, receipt=receipt, runtime_redo=redo,
        config_path=config_path, active_runtime=active_runtime,
        install_config=install_image / "config.xml",
    )
    if source_state == "candidate-quarantined":
        return {"state":"candidate-already-quarantined",
                "safe_to_close_intent":False, "voice_on":False}
    if source_state not in ("retired-awaiting-reclaim", "write-ahead-retired"):
        raise ReclaimError("no recoverable candidate retirement state")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    existing = read_reclaim_intent(journal.directory)
    if existing is None:
        _publish(journal.directory, expected)
    elif existing != expected:
        raise ReclaimError("foreign write-ahead reclaim marker")
    if inspect_reclaim_placement(
        journal=journal, plan=plan, receipt=receipt, runtime_redo=redo,
        config_path=config_path, active_runtime=active_runtime,
        install_config=install_image / "config.xml",
    ) != "write-ahead-retired":
        raise ReclaimError("source changed before quarantine rename")
    parent = active_runtime.parent
    before = _safe_parent(parent)
    if (before.st_dev, before.st_ino) != (
        expected["parent_dev"], expected["parent_inode"]
    ):
        raise ReclaimError("runtime parent changed before rename")
    dirfd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                    getattr(os, "O_NOFOLLOW", 0))
    try:
        statfd = os.fstat(dirfd)
        if (statfd.st_dev, statfd.st_ino) != (
            expected["parent_dev"], expected["parent_inode"]
        ):
            raise ReclaimError("runtime parent swapped during rename")
        if os.path.lexists(parent / expected["quarantine_name"]):
            raise ReclaimError("reclaim target already exists")
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        os.rename(expected["retired_name"], expected["quarantine_name"],
                  src_dir_fd=dirfd, dst_dir_fd=dirfd)
        os.fsync(dirfd)
    finally:
        os.close(dirfd)
    if inspect_reclaim_placement(
        journal=journal, plan=plan, receipt=receipt, runtime_redo=redo,
        config_path=config_path, active_runtime=active_runtime,
        install_config=install_image / "config.xml",
    ) != "candidate-quarantined":
        raise ReclaimError("candidate quarantine not durably observable")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if journal.read() != record or read_cleanup_plan(journal.directory) != plan or (
        read_receipt(journal.directory) != receipt
        or _read_redo(journal.directory) != redo
    ):
        raise ReclaimError("whole Voice rollback changed after rename")
    return {"state":"candidate-quarantined",
            "safe_to_close_intent":False, "voice_on":False}
