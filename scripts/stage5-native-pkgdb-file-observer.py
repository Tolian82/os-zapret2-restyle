#!/usr/bin/env python3
"""One-guest pkgdb file metadata only; NEVER open a SQLite connection.

Diagnostic only, NEVER a pkgdb eligibility witness. This uses O_RDONLY and
O_NOFOLLOW and reads at most 100 header bytes per fixed path. It cannot
detect a hot journal or claim consistency. No archive, Config or hostlists
are inspected. No database/journal contents are printed or copied.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat

DEFAULT_DB_DIR = Path("/var/db/pkg")
FILES = {
    "main": "local.sqlite",
    "rollback_journal": "local.sqlite-journal",
    "wal": "local.sqlite-wal",
    "shm": "local.sqlite-shm",
}
ALLOWED_PHASES = (
    "pre-extract", "post-sigkill", "post-reset-before-explicit-pkg-query",
    "post-reset-after-explicit-pkg-query", "post-reviewed-dual-probe",
)
SQLITE_MAGIC = b"SQLite format 3\x00"


def file_info(path, *, main=False):
    try:
        initial = path.lstat()
    except FileNotFoundError:
        return {"state": "missing"}
    except OSError:
        return {"state": "inaccessible"}
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        return {"state": "unsafe-file"}
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
        try:
            pinned = os.fstat(fd)
            if not stat.S_ISREG(pinned.st_mode) or (
                pinned.st_dev, pinned.st_ino, pinned.st_size
            ) != (initial.st_dev, initial.st_ino, initial.st_size):
                return {"state": "changed-during-open"}
            header = os.read(fd, 100 if main else 8)
        finally:
            os.close(fd)
    except OSError:
        return {"state": "inaccessible"}
    result = {
        "state": "regular", "size": pinned.st_size,
        "mtime_ns": pinned.st_mtime_ns,
        "root_owned": pinned.st_uid == 0,
    }
    if main:
        valid = len(header) >= 100 and header[:16] == SQLITE_MAGIC
        result["sqlite_header"] = "recognized" if valid else "unrecognized"
        if valid:
            page = int.from_bytes(header[16:18], "big")
            if page == 1:
                page = 65536
            result["page_size_valid"] = (
                512 <= page <= 65536 and page & (page - 1) == 0)
            result["read_version"] = header[19] if header[19] in (1, 2) else 0
            result["write_version"] = header[18] if header[18] in (1, 2) else 0
            result["change_counter"] = int.from_bytes(header[24:28], "big")
    elif path.name == FILES["rollback_journal"]:
        # Journal presence/signature is NOT enough to declare it 'hot'.
        result["rollback_header_magic"] = (
            header == b"\xd9\xd5\x05\xf9\x20\xa1\x63\xd7")
    return result


def snapshot(root=None):
    if root is None:
        root = DEFAULT_DB_DIR
    return {
        category: file_info(root / filename, main=(category == "main"))
        for category, filename in FILES.items()
    }


def report(phase):
    if phase not in ALLOWED_PHASES:
        raise ValueError("NOT_AN_ALLOWED_FORENSIC_PHASE")
    print("NATIVE_PKGDB_FILE_READONLY=" + json.dumps({
        "phase": phase, "assumed_default_pkgdb_dir_not_runtime_verified": True,
        "files": snapshot(), "sqlite_connection_opened": False,
        "native_pkg_command_executed": False, "write_attempted": False,
        "hot_journal_or_integrity_proven": False,
    }, sort_keys=True), flush=True)
