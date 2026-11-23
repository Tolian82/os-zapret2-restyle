#!/usr/bin/env python3
"""TZ6v5 S04b OPNsense read-only facts adapter. NEVER a lifecycle authority.

This private inventory only reads installed pkg, fixed native file paths and
the already existing shared owner/IPFW inspector. It never creates a journal,
acquires FD9, signals processes, modifies Config or authorizes transitions.
Unknown/racing evidence MUST fail closed, not be repaired by this reader.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True  # Read-only import: do not create __pycache__.

from component_inventory import classify

PKG = "/usr/local/sbin/pkg"  # Not /usr/sbin/pkg: that bootstrap shim can install pkg!
PACKAGE = "os-zapret2-restyle"
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
CONFIG = Path("/conf/config.xml")
MAX_CONFIG = 16 * 1024 * 1024
MAX_ENGINE = 64 * 1024 * 1024


def _read_fixed(path: Path, limit: int, owner: int, *, prefix: bool = False) -> bytes:
    """No user paths, symlinks, group writers, unbounded reads or file creation."""
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner or
            before.st_nlink != 1 or before.st_mode & 0o022 or
            before.st_size < 1 or before.st_size > limit):
        raise ValueError("UNTRUSTED_READONLY_COMPONENT")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        pinned = os.fstat(fd)
        if (pinned.st_dev, pinned.st_ino, pinned.st_size) != (
                before.st_dev, before.st_ino, before.st_size):
            raise ValueError("RACING_READONLY_COMPONENT")
        data = os.read(fd, min(64, pinned.st_size) if prefix else limit + 1)
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns):
            raise ValueError("RACING_READONLY_COMPONENT")
        return data
    finally:
        os.close(fd)


def probe_plugin(*, pkg: str = PKG, runner=subprocess.run) -> str:
    # Only the installed pkg binary; the FreeBSD bootstrap shim may mutate.
    if not os.path.isfile(pkg) or not os.access(pkg, os.X_OK):
        return "unknown"
    try:
        result = runner([pkg, "info", "-e", PACKAGE], capture_output=True,
                        timeout=6, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if result.returncode == 0:
        return "installed"
    if result.returncode == 1:
        return "absent"
    return "unknown"


def probe_engine(*, path: Path = ENGINE, owner: int = 0) -> str:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unknown"
    try:
        if not (info.st_mode & 0o111):
            return "invalid"
        header = _read_fixed(path, MAX_ENGINE, owner, prefix=True)
        # Native FreeBSD/amd64 ELF shape; this is NOT a version, hash or
        # lifecycle readiness receipt. Upstream provenance remains separate.
        if (len(header) < 64 or header[:4] != b"\x7fELF" or
                header[4:6] != b"\x02\x01" or header[7] not in (0, 9) or
                struct.unpack_from("<H", header, 16)[0] not in (2, 3) or
                struct.unpack_from("<H", header, 18)[0] != 62):
            return "invalid"
        return "valid"
    except (OSError, ValueError, struct.error):
        return "invalid"


def probe_config(*, path: Path = CONFIG, owner: int = 0) -> str:
    try:
        path.lstat()
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unknown"
    try:
        raw = _read_fixed(path, MAX_CONFIG, owner)
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            return "invalid"
        root = ET.fromstring(raw)
        if root.tag != "opnsense":
            return "invalid"
        model = root.find("./OPNsense/Zapret")
        if model is None:
            return "absent"
        general = model.find("general")
        if general is None or general.findtext("enabled") not in ("0", "1"):
            return "invalid"
        return "initialized"
    except (OSError, ValueError, ET.ParseError):
        return "invalid"


def probe_owner(*, read_record=None, verify=None, manifest_reader=None,
                examine=None, absent=None) -> tuple[str, str]:
    """Reuse original shared seal+owner+runtime/IPFW reader, never re-match PID."""
    from shared_apply_operation import SharedApplyOperation, committed_owner
    from shared_apply_seal import WORK, verify_seal
    from voice_ipfw_adapter import shared_release_manifest
    from voice_live_inspect import examine_shared, _ipfw_kernel_confirmed_absent

    read_record = read_record or (lambda: SharedApplyOperation(owner=0).read())
    verify = verify or verify_seal
    manifest_reader = manifest_reader or shared_release_manifest
    examine = examine or examine_shared
    absent = absent or _ipfw_kernel_confirmed_absent

    try:
        record = read_record()
        if record is None:
            # Existing strict original no-process/no-kernel witness only.
            return "missing", "STOPPED" if absent() else "UNKNOWN"
        if record["phase"] not in ("committed", "restored"):
            return "stale", "INCOMPLETE"
        original = committed_owner(record)
        if original is None:
            return "missing", "UNKNOWN"
        work = WORK / original["id"]
        verify(work, owner=0)
        native_manifest = manifest_reader(work / "release")
        if type(native_manifest) is not dict:
            return "invalid", "INCOMPLETE"
        observed = examine(record)
        if observed is None or observed.get("source") != "native-common":
            return "invalid", "INCOMPLETE"
        state = observed.get("state")
        if state == "ready":
            return "valid", "RUNNING"
        if state == "stopped":
            return "valid", "STOPPED"
        if state == "foreign-or-modified-rules":
            return "valid", "FOREIGN_OR_UNVERIFIED"
        if state == "interrupted":
            if observed.get("condition") == "common-runtime-unverified-release":
                return "stale", "INCOMPLETE"
            return "valid", "INCOMPLETE"
        return "invalid", "INCOMPLETE"
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        # Includes original journal/seal/manifest/owner refusal; no raw error.
        return "invalid", "INCOMPLETE"


def collect(*, plugin=probe_plugin, engine=probe_engine, config=probe_config,
            owner=probe_owner) -> dict:
    manifest, runtime = owner()
    facts = {"plugin": plugin(), "engine": engine(), "config": config(),
             "manifest": manifest, "runtime": runtime}
    return classify(facts)


def main(argv: list[str]) -> int:
    if argv != ["component_inventory_opnsense.py"]:
        print("usage: component_inventory_opnsense.py", file=sys.stderr)
        return 64
    try:
        print(json.dumps(collect(), sort_keys=True, separators=(",", ":")))
    except (OSError, ValueError, RuntimeError, TypeError):
        print("COMPONENT_INVENTORY_UNQUALIFIED", file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    raise SystemExit(main([Path(sys.argv[0]).name, *sys.argv[1:]]))
