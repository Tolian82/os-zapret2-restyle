#!/usr/bin/env python3
"""Durable evidence for completed OLD Telegram PoC five-domain rollback.

IMPORT ONLY; no service, GUI, configd, or boot entrypoint. The separate
sibling receipt avoids changing strict legacy stage-root allowlists. Its
presence is NEVER authorization for Voice Apply, lifecycle start or MEDIA_PASS.

The receipt freezes every byte and file mode in the six step journals and
the three immutable source records. At cold boot its *disk* reader checks
all sealed evidence without issuing IPFW commands or starting processes.
Live reconciliation is an explicit original-FD9/Config-lock operation; a
changed process epoch or unknown post-reboot kernel fails closed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
from voice_native_legacy_previous_seal import NAME, inspect_legacy_previous, _write_once
from voice_native_legacy_restore_plan import PLAN_NAME, inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import WAL_NAME, inspect_legacy_reverse_wal
from voice_native_legacy_files_ready import FILES_NAME, inspect_legacy_files_ready
from voice_native_legacy_process_restart import (
    PROCESS_NAME, FINAL_FILES, _read_record, restart_legacy_processes,
)
from voice_native_recovery_quiescence import _locked_config
from voice_native_legacy_ipfw_replay import REPLAY_NAME
from voice_native_legacy_runtime_restore import NAME_RESTORE
from voice_native_legacy_config_restore import CONFIG_NAME
from voice_native_legacy_marker_restore import MARKER_NAME

SCHEMA = 1
SUFFIX = "-legacy-whole-receipt"
FILES = frozenset(("receipt.json", "receipt.sha256"))
JOURNALS = (NAME, PLAN_NAME, WAL_NAME, REPLAY_NAME, FILES_NAME,
            NAME_RESTORE, CONFIG_NAME, MARKER_NAME, PROCESS_NAME)
STAGES = JOURNALS[3:]
MAX_FILES = 30000
MAX_BYTES = 1 << 30
MAX_RECORD = 16384


class LegacyWholeReceiptError(RuntimeError):
    pass


def receipt_directory(root):
    root = Path(root)
    return root.with_name(root.name + SUFFIX)


def _canonical(row):
    return (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def _hash_journals(root):
    """Nofollow, bounded, stable content/mode fingerprint of ALL nine trees."""
    root = Path(root)
    _private_dir(root)
    if set(os.listdir(root)) != set(JOURNALS):
        raise LegacyWholeReceiptError("not exactly the complete old five-domain journal")
    digest = hashlib.sha256()
    count = 0
    total = 0
    for name in JOURNALS:
        start = root / name
        _private_dir(start)
        for directory, dirs, files in os.walk(start, topdown=True, followlinks=False):
            dirs.sort()
            files.sort()
            current = Path(directory)
            dstat = os.lstat(current)
            if not stat.S_ISDIR(dstat.st_mode) or dstat.st_uid != os.geteuid():
                raise LegacyWholeReceiptError("unsafe journal directory")
            rel = current.relative_to(root).as_posix()
            digest.update(_canonical(["dir", rel, stat.S_IMODE(dstat.st_mode)]))
            for child in dirs:
                info = os.lstat(current / child)
                if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
                    raise LegacyWholeReceiptError("unsafe nested journal directory")
            for child in files:
                file = current / child
                info = os.lstat(file)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_size > MAX_BYTES - total):
                    raise LegacyWholeReceiptError("unsafe or oversized journal file")
                count += 1
                total += info.st_size
                if count > MAX_FILES:
                    raise LegacyWholeReceiptError("too many journal entries")
                fd = os.open(file, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                try:
                    opened = os.fstat(fd)
                    if (opened.st_ino != info.st_ino or opened.st_dev != info.st_dev
                        or opened.st_size != info.st_size):
                        raise LegacyWholeReceiptError("journal file changed while opening")
                    h = hashlib.sha256()
                    while True:
                        data = os.read(fd, 1024 * 1024)
                        if not data:
                            break
                        h.update(data)
                    after = os.fstat(fd)
                    if (after.st_size != info.st_size or
                        after.st_mtime_ns != info.st_mtime_ns or
                        after.st_ctime_ns != info.st_ctime_ns):
                        raise LegacyWholeReceiptError("journal file changed during hashing")
                finally:
                    os.close(fd)
                digest.update(_canonical([
                    "file", file.relative_to(root).as_posix(),
                    stat.S_IMODE(info.st_mode), info.st_size, h.hexdigest(),
                ]))
    return digest.hexdigest()


def _inputs(root):
    old = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    wal = inspect_legacy_reverse_wal(
        root, allow_ipfw_replay=True, allow_files_stage=FILES_NAME,
        allow_runtime_restore=True, allow_config_restore=True,
        allow_marker_restore=True, allow_process_restart=True,
    )
    ready = inspect_legacy_files_ready(
        root, allow_runtime_restore=True, allow_config_restore=True,
        allow_marker_restore=True, allow_process_restart=True,
    )
    directory = root / PROCESS_NAME
    _private_dir(directory)
    if set(os.listdir(directory)) != FINAL_FILES:
        raise LegacyWholeReceiptError("old three-role process verification not sealed")
    verified = _read_record(directory, "verified")
    if (old["previous_five"] != plan["previous_five"]
        or ready["previous_five"] != plan["previous_five"]
        or wal["previous_five"] != plan["previous_five"]
        or wal["process_security_policy_sha256"] !=
           verified["process_security_policy_sha256"]):
        raise LegacyWholeReceiptError("foreign five-domain evidence")
    return plan, wal, verified


def _expected(root, report=None):
    plan, wal, verified = _inputs(root)
    if report is not None and (
        report.get("state") != "legacy-three-roles-restarted-needs-whole-owner-acceptance"
        or report.get("instances") != verified["instances"]
        or report.get("process_security_policy_sha256") !=
           verified["process_security_policy_sha256"]
        or report.get("kernel_argv_sha256") != verified["engine_argv_sha256"]
    ):
        raise LegacyWholeReceiptError("process attestation differs from sealed old receipt")
    first = _hash_journals(root)
    if _hash_journals(root) != first:
        raise LegacyWholeReceiptError("unstable five-domain journals")
    return {
        "schema": SCHEMA, "phase": "old-five-domains-disk-sealed-live-boot-pending",
        "root": str(root.absolute()),
        "previous_five": plan["previous_five"],
        "restore_plan_sha256": wal["restore_plan_sha256"],
        "process_security_policy_sha256": verified["process_security_policy_sha256"],
        "process_instances": verified["instances"],
        "engine_argv_sha256": verified["engine_argv_sha256"],
        "journal_tree_sha256": first,
        "phases_completed": list(STAGES),
        "safe_to_enable_voice": False, "safe_to_close_intent": False,
        "public_voice_apply": False, "boot_recovery_validated": False,
        "media_pass": False,
    }


def inspect_legacy_whole_receipt(root):
    """Cold-boot disk triage. NEVER represents a post-reboot live acceptance."""
    root = Path(root)
    directory = receipt_directory(root)
    _private_dir(directory)
    if set(os.listdir(directory)) != FILES:
        raise LegacyWholeReceiptError("partial or foreign whole rollback receipt")
    raw = _read_private_file(directory / "receipt.json", MAX_RECORD)
    digest = _read_private_file(directory / "receipt.sha256", 65)
    if digest != (hashlib.sha256(raw).hexdigest() + "\n").encode("ascii"):
        raise LegacyWholeReceiptError("corrupt whole rollback receipt checksum")
    record = json.loads(raw)
    if record != _expected(root) or raw != _canonical(record):
        raise LegacyWholeReceiptError("whole rollback receipt no longer matches journals")
    return {
        **record, "state": "legacy-whole-receipt-disk-valid-live-recheck-required",
        "whole_rollback_complete": True, "safe_to_mutate": False,
    }


def seal_legacy_whole_receipt(
    *, root, config_path, config_fd, config_owner,
    require_lifecycle_owner, process_report,
):
    """Sealed only AFTER the original coordinator attests live five domains."""
    if not callable(require_lifecycle_owner):
        raise LegacyWholeReceiptError("missing original FD9 owner")
    root = Path(root)
    def held():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
    held()
    row = _expected(root, process_report)
    directory = receipt_directory(root)
    if os.path.lexists(directory):
        existing = inspect_legacy_whole_receipt(root)
        if {k: existing[k] for k in row} != row:
            raise LegacyWholeReceiptError("foreign pre-existing whole receipt")
        held()
        return existing
    raw = _canonical(row)
    if len(raw) > MAX_RECORD:
        raise LegacyWholeReceiptError("whole receipt exceeds bound")
    held()
    if _expected(root, process_report) != row:
        raise LegacyWholeReceiptError("five-domain drift before receipt publication")
    # Exact-path directory is the write-ahead boundary. A partial write is
    # retained for manual review; no deletion or opportunistic repair.
    os.mkdir(directory, 0o700)
    _sync_dir(root.parent)
    _write_once(directory / "receipt.json", raw)
    _write_once(directory / "receipt.sha256",
                (hashlib.sha256(raw).hexdigest() + "\n").encode("ascii"))
    _sync_dir(directory)
    _sync_dir(root.parent)
    held()
    return inspect_legacy_whole_receipt(root)


def reconcile_legacy_whole_receipt_live(
    *, root, config_path, config_fd, config_owner, active_runtime,
    marker_path, ledger_root, process_probe, readonly_ipfw, security_reader,
    argv_reader, require_lifecycle_owner,
):
    """Explicit readback, not automatic boot/start/restart or Voice permission."""
    root = Path(root)
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    saved = inspect_legacy_whole_receipt(root)
    # A verified intent already exists; this imported restarter only
    # reattests the same running process epochs, never invokes start again.
    observed = restart_legacy_processes(
        root=root, config_path=config_path, config_fd=config_fd,
        config_owner=config_owner, active_runtime=active_runtime,
        marker_path=marker_path, ledger_root=ledger_root,
        process_probe=process_probe, readonly_ipfw=readonly_ipfw,
        security_reader=security_reader, argv_reader=argv_reader,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if (saved["process_instances"] != observed["instances"]
        or saved["process_security_policy_sha256"] !=
           observed["process_security_policy_sha256"]
        or saved["engine_argv_sha256"] != observed["kernel_argv_sha256"]):
        raise LegacyWholeReceiptError("old process changed since sealed receipt")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    if inspect_legacy_whole_receipt(root) != saved:
        raise LegacyWholeReceiptError("receipt changed during live reconciliation")
    return {
        **saved, "state": "legacy-whole-receipt-live-reconciled-boot-uat-pending",
        "safe_to_mutate": False, "boot_recovery_validated": False,
    }
