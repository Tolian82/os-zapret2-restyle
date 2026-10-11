#!/usr/bin/env python3
"""Native Voice forward candidate Config write after supervisor/IPFW PRECOMMIT.

Private import-only step of the *existing* five-resource cutover, not a public
Apply, commit, restore, boot action, or license to enable Voice. Uses the same
OPNsense config.xml inode and original FD9 + continuously held flock.
An fsync'd, bound forward-only redo permits resuming precisely a prefix of the
sealed candidate bytes after power loss; it never adopts a foreign Config.
The old Config backup and both journals survive this step.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import (
    CHUNK, MAX_BYTES, _private_dir, _sync_dir, inspect_previous,
    bound_resource_fingerprints,
)
from voice_cutover_config_restore import _pinned_regular, _sha_fd, _write_all
from voice_cutover_journal import VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, BOUND_FIELD
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, fingerprint
from voice_firewall_transaction import plan_postcommit_cleanup
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import require_no_legacy
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS, _live_instances
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_live_preflight import _current_engine_args
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import _read_redo

NAME = "forward-config-redo.json"
MAX_MARKER = 4096


class ForwardConfigError(RuntimeError):
    pass


def _digest(body):
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _sealed(body):
    return {**body, "check": _digest(body)}


def _validate(marker):
    names = {
        "schema", "whole_check", "config_dev", "config_inode", "config_uid",
        "config_gid", "previous_sha256", "candidate_sha256",
        "candidate_bytes", "previous_mode", "source_path", "source_dev",
        "source_inode", "source_uid", "source_gid", "check",
    }
    if not isinstance(marker, dict) or set(marker) != names or (
        type(marker["schema"]) is not int or marker["schema"] != 1
    ):
        raise ForwardConfigError("invalid candidate Config redo schema")
    if any(type(marker[key]) is not int or marker[key] < 0 for key in (
        "config_dev", "config_inode", "config_uid", "config_gid",
        "candidate_bytes", "previous_mode", "source_dev", "source_inode",
        "source_uid", "source_gid",
    )) or marker["candidate_bytes"] > MAX_BYTES or marker["previous_mode"] > 0o7777:
        raise ForwardConfigError("invalid candidate Config inode/size/mode")
    path = marker["source_path"]
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 4096 or (
        "\x00" in path or ".." in Path(path).parts
    ):
        raise ForwardConfigError("invalid sealed candidate Config source path")
    if any(type(marker[key]) is not str or len(marker[key]) != 64 or (
        set(marker[key]) - set("0123456789abcdef")
    ) for key in ("whole_check", "previous_sha256", "candidate_sha256", "check")):
        raise ForwardConfigError("invalid candidate Config digest")
    if marker["check"] != _digest({k: v for k, v in marker.items() if k != "check"}):
        raise ForwardConfigError("candidate Config redo checksum mismatch")
    return marker


def read_forward_config_redo(root: Path):
    root = Path(root)
    _private_dir(root)
    try:
        fd = os.open(root / NAME, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (
            info.st_uid != os.geteuid() or info.st_mode & 0o077
            or info.st_size > MAX_MARKER
        ):
            raise ForwardConfigError("unsafe candidate Config redo inode")
        raw = os.read(fd, MAX_MARKER + 1)
        if len(raw) > MAX_MARKER:
            raise ForwardConfigError("oversized candidate Config redo")
        try:
            return _validate(json.loads(raw))
        except (ValueError, UnicodeError, TypeError) as exc:
            raise ForwardConfigError("corrupt candidate Config redo") from exc
    finally:
        os.close(fd)


def _arm(root, fields):
    root = Path(root)
    marker = _validate(_sealed(fields))
    old = read_forward_config_redo(root)
    if old is not None:
        if old != marker:
            raise ForwardConfigError("candidate Config redo belongs to another intent")
        return marker
    encoded = (json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(encoded) > MAX_MARKER:
        raise ForwardConfigError("candidate Config redo exceeds bound")
    fd = os.open(root / NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    _sync_dir(root)
    if read_forward_config_redo(root) != marker:
        raise ForwardConfigError("candidate Config redo not durably sealed")
    return marker


def _candidate_prefix(live_fd, source_fd, source_bytes):
    size = os.fstat(live_fd).st_size
    if size > source_bytes:
        return False
    os.lseek(live_fd, 0, os.SEEK_SET)
    os.lseek(source_fd, 0, os.SEEK_SET)
    remaining = size
    while remaining:
        old = os.read(live_fd, min(CHUNK, remaining))
        new = os.read(source_fd, len(old))
        if not old or old != new:
            return False
        remaining -= len(old)
    return True


def is_bound_forward_candidate_prefix(marker, journal_record, live_fd, live_info):
    """Allow *previous* rollback of a torn candidate Config only with exact redo.

    Validates the sealed candidate source again on a pinned no-follow inode.
    Called ONLY by the already locked five-resource previous Config restorer.
    This never authorizes forward execution or automatic reboot cleanup.
    """
    if marker is None:
        return False
    _validate(marker)
    if journal_record["schema"] != RUNTIME_BOUND_SCHEMA or (
        journal_record["phase"] != "mutating"
        or marker["whole_check"] != journal_record["check"]
        or marker["previous_sha256"] != journal_record["previous"]["config"]
        or marker["candidate_sha256"] != journal_record["candidate"]["saved_xml_sha256"]
        or (live_info.st_dev, live_info.st_ino, live_info.st_uid, live_info.st_gid) != (
            marker["config_dev"], marker["config_inode"],
            marker["config_uid"], marker["config_gid"],
        )
    ):
        raise ForwardConfigError("forward Config redo not bound to locked Config/intent")
    source = Path(marker["source_path"])
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        _pinned_regular(source, fd, owner=(marker["source_uid"], marker["source_gid"]))
        stat_source = os.fstat(fd)
        if (stat_source.st_dev, stat_source.st_ino) != (
            marker["source_dev"], marker["source_inode"]
        ) or _sha_fd(fd) != (marker["candidate_sha256"], marker["candidate_bytes"]):
            raise ForwardConfigError("forward Config source changed after redo")
        return _candidate_prefix(live_fd, fd, marker["candidate_bytes"])
    finally:
        os.close(fd)


def persist_forward_candidate_config(
    *, journal, ledger, previous_backup, config_path, locked_config_fd,
    config_owner, staged_config, candidate_runtime, active_runtime,
    desired_manifest, probe, kernel_reader, readonly_adapter,
    require_lifecycle_owner,
):
    """Write only the candidate Config in place after native supervisor start.

    The trusted future upper coordinator owns original FD9 and the Config
    flock throughout stop/runtime/engine/IPFW/supervisor/Config/commit.
    This call does not acquire/release either ownership and never commits.
    After a torn write, either retry this stage under the original locks OR
    let the existing previous-Config restorer verify the bound forward redo
    and exact candidate prefix under a five-resource rollback owner.
    No partial Config is treated as applied.
    """
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or Path(probe.previous_backup) != Path(previous_backup)
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(readonly_adapter, FreeBSDIPFWAdapter)
        or readonly_adapter.allow_mutations is not False
        or readonly_adapter.rule_base != 19000 or readonly_adapter.rule_max != 19010
        or type(locked_config_fd) is not int or locked_config_fd < 0
        or not callable(require_lifecycle_owner)
        or type(config_owner) is not tuple or len(config_owner) != 2
        or any(type(n) is not int or n < 0 for n in config_owner)
    ):
        raise ForwardConfigError("untrusted native candidate Config owner")
    config_path, staged_config, candidate_runtime, active_runtime = map(
        Path, (config_path, staged_config, candidate_runtime, active_runtime)
    )
    previous_backup = Path(previous_backup)
    desired = canonical_manifest(desired_manifest)
    desired_sha = fingerprint(desired)
    if not desired_manifest["rules"] or not desired_manifest["tables"]:
        raise ForwardConfigError("empty candidate IPFW plan")

    def owner():
        require_lifecycle_owner()
        _locked_config(config_path, locked_config_fd, config_owner)
        _pinned_regular(config_path, locked_config_fd, owner=config_owner)

    def native_proof():
        owner()
        record = journal.read()
        if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or (
            record["phase"] != "mutating"
            or record["candidate"][BOUND_FIELD] != desired_sha
        ):
            raise ForwardConfigError("missing exact MUTATING candidate Config intent")
        old = bound_resource_fingerprints(previous_backup, record["previous"])
        candidate = observe_live_files(staged_config, candidate_runtime)
        if candidate != {
            "config": record["candidate"]["saved_xml_sha256"],
            "runtime": record["candidate"]["candidate_runtime_sha256"],
        }:
            raise ForwardConfigError("staged candidate Config/runtime changed")
        if observe_live_files(staged_config, active_runtime)["runtime"] != candidate["runtime"]:
            raise ForwardConfigError("installed candidate runtime differs")
        retained = active_runtime.with_name(
            ".voice-forward-previous-" + record["check"][:20]
        )
        if retained.is_symlink() or not retained.is_dir() or (
            observe_live_files(staged_config, retained)["runtime"] != old["runtime"]
        ):
            raise ForwardConfigError("previous runtime was not retained")
        runtime_redo = _read_redo(journal.directory)
        cfg = os.fstat(locked_config_fd)
        parent = os.lstat(active_runtime.parent)
        if runtime_redo is None or (
            runtime_redo["whole_check"] != record["check"]
            or runtime_redo["previous_sha256"] != old["runtime"]
            or runtime_redo["candidate_sha256"] != candidate["runtime"]
            or runtime_redo["retained_name"] != retained.name
            or runtime_redo["active_name"] != active_runtime.name
            or (cfg.st_dev, cfg.st_ino) != (
                runtime_redo["config_dev"], runtime_redo["config_inode"]
            )
            or (parent.st_dev, parent.st_ino) != (
                runtime_redo["parent_dev"], runtime_redo["parent_inode"]
            )
            or os.path.lexists(active_runtime.with_name(runtime_redo["ready_name"]))
        ):
            raise ForwardConfigError("candidate runtime redo/inodes changed")
        old_owner, pending = ledger.owned(), ledger.pending()
        if old_owner is None or pending is None or (
            fingerprint(canonical_manifest(old_owner)) != record["previous"]["firewall"]
            or pending["phase"] != "mutating"
            or pending["previous_sha256"] != record["previous"]["firewall"]
            or pending["desired_sha256"] != desired_sha
            or pending["previous"] != canonical_manifest(old_owner)
            or pending["desired"] != desired
        ):
            raise ForwardConfigError("candidate IPFW PRECOMMIT no longer sealed")
        require_no_legacy(readonly_adapter)
        plan_postcommit_cleanup(readonly_adapter, old_owner, desired_manifest)
        engine_argv, argv_sha, _, _ = _current_engine_args(active_runtime)
        if argv_sha != record["candidate"]["native_argv_sha256"]:
            raise ForwardConfigError("candidate engine args differ")
        ports = {rule[1] for rule in desired_manifest["rules"].values()}
        if ports != {
            word.split("=", 1)[1] for word in engine_argv if word.startswith("--port=")
        }:
            raise ForwardConfigError("IPFW divert is not bound to candidate engine")
        instances = _live_instances(probe.observe_processes())
        expected = {
            "engine": engine_argv,
            **canonical_supervisor_argv(EXPECTED_SCRIPTS),
        }
        for role, identity in instances.items():
            if kernel_reader.argv(identity["pid"]) != expected[role] or (
                kernel_reader.binary(identity["pid"]) != SYSTEM_PATHS[role]
            ):
                raise ForwardConfigError("candidate kernel argv/binary differs")
        return record, old, pending, instances

    first = native_proof()
    if native_proof() != first:
        raise ForwardConfigError("candidate kernel/IPFW evidence changed")
    record, old, _, _ = first
    saved = inspect_previous(previous_backup)
    previous_mode = saved["config"]["mode"]
    source_fd = os.open(staged_config, os.O_RDONLY |
                        getattr(os, "O_NOFOLLOW", 0) |
                        getattr(os, "O_CLOEXEC", 0))
    try:
        _pinned_regular(staged_config, source_fd,
                        owner=(os.geteuid(), os.getegid()))
        source_hash, source_bytes = _sha_fd(source_fd)
        if source_hash != record["candidate"]["saved_xml_sha256"]:
            raise ForwardConfigError("sealed staged Config bytes changed")
        before_hash, before_size = _sha_fd(locked_config_fd)
        cfg = os.fstat(locked_config_fd)
        fields = {
            "schema": 1, "whole_check": record["check"],
            "config_dev": cfg.st_dev, "config_inode": cfg.st_ino,
            "config_uid": cfg.st_uid, "config_gid": cfg.st_gid,
            "previous_sha256": old["config"],
            "candidate_sha256": source_hash,
            "candidate_bytes": source_bytes,
            "previous_mode": previous_mode,
            "source_path": str(staged_config),
            "source_dev": os.fstat(source_fd).st_dev,
            "source_inode": os.fstat(source_fd).st_ino,
            "source_uid": os.fstat(source_fd).st_uid,
            "source_gid": os.fstat(source_fd).st_gid,
        }
        expected_marker = _sealed(fields)
        existing = read_forward_config_redo(journal.directory)
        if existing is not None and existing != expected_marker:
            raise ForwardConfigError("foreign candidate Config redo")
        candidate_sha = fields["candidate_sha256"]
        partial = existing is not None and _candidate_prefix(
            locked_config_fd, source_fd, source_bytes
        )
        if before_hash not in (old["config"], candidate_sha) and not partial:
            raise ForwardConfigError("foreign/partial Config cannot be overwritten")
        if existing is None and before_hash != old["config"]:
            raise ForwardConfigError("candidate Config changed without forward redo")
        if before_hash == candidate_sha and before_size == source_bytes and (
            stat.S_IMODE(cfg.st_mode) == previous_mode
        ):
            if existing is None:
                raise ForwardConfigError("candidate Config exists without redo")
            if native_proof() != first:
                raise ForwardConfigError("candidate moved after earlier write")
            return "candidate-config-already-persisted"
        # Intact previous Config MUST have its sealed original permissions.
        if existing is None and stat.S_IMODE(cfg.st_mode) != previous_mode:
            raise ForwardConfigError("previous Config mode changed")
        owner()
        if native_proof() != first or (
            _sha_fd(locked_config_fd) != (before_hash, before_size)
            or _sha_fd(source_fd) != (source_hash, source_bytes)
        ):
            raise ForwardConfigError("candidate changed before write-ahead")
        marker = _arm(journal.directory, fields)  # fsync BEFORE first truncate
        owner()
        if read_forward_config_redo(journal.directory) != marker or (
            native_proof() != first
            or _sha_fd(locked_config_fd) != (before_hash, before_size)
        ):
            raise ForwardConfigError("candidate changed after write-ahead")
        os.ftruncate(locked_config_fd, 0)
        os.lseek(locked_config_fd, 0, os.SEEK_SET)
        os.lseek(source_fd, 0, os.SEEK_SET)
        while True:
            data = os.read(source_fd, CHUNK)
            if not data:
                break
            _write_all(locked_config_fd, data)
        os.fchmod(locked_config_fd, previous_mode)
        os.fsync(locked_config_fd)
        if _sha_fd(locked_config_fd) != (source_hash, source_bytes) or (
            stat.S_IMODE(os.fstat(locked_config_fd).st_mode) != previous_mode
            or _sha_fd(source_fd) != (source_hash, source_bytes)
        ):
            raise ForwardConfigError("candidate Config write not verified")
        if native_proof() != first or (
            read_forward_config_redo(journal.directory) != marker
        ):
            raise ForwardConfigError("kernel/IPFW/whole intent changed after Config write")
        return "candidate-config-persisted-pending-whole-commit"
    finally:
        os.close(source_fd)
