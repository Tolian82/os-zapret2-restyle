#!/usr/bin/env python3
"""Render the ONE native OPNsense Zapret template from detached Config XML.

The shared runtime generator must never consume live zapret.conf for a Voice
candidate prepared from browser XML. The official native Python template
engine supports a target_root_directory and set_config(Config(candidate).get()).
No Config singleton, template reload, IPFW or running service is touched.

Production CLI accepts ONLY an operation ID; the private staging root is
fixed. A future FD9 worker creates/seals candidate.xml in that workspace,
and the existing shell orchestrator consumes this output. Nothing here
writes or promotes OPNsense's actual /conf/config.xml.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import sys
import xml.etree.ElementTree as ET

WORK_ROOT = Path("/var/db/zapret2/shared-work")
OPERATION = re.compile(r"^[a-f0-9]{32}$")
MAX_XML = 16 * 1024 * 1024
MODULE = "OPNsense/Zapret"
TARGETS = {
    "zapret.conf": "/usr/local/etc/zapret2/zapret.conf",
    "hostlist.txt": "/usr/local/etc/zapret2/hostlist.txt",
    "hostlist-exclude.txt": "/usr/local/etc/zapret2/hostlist-exclude.txt",
}


class NativeDetachedRenderError(RuntimeError):
    pass


def regular(path: Path, uid: int, *, directory: bool = False) -> os.stat_result:
    info = path.lstat()
    if directory:
        valid = stat.S_ISDIR(info.st_mode)
    else:
        valid = stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    if not valid or info.st_uid != uid or info.st_mode & 0o077:
        raise NativeDetachedRenderError("unsafe native detached candidate path")
    if not directory and info.st_size > MAX_XML:
        raise NativeDetachedRenderError("oversized detached Config")
    return info


def render_detached(
    candidate: Path, target_root: Path, *,
    template_factory=None, config_factory=None, owner: int | None = None
) -> list[Path]:
    """Render exactly the installed Zapret +TARGETS, in a fresh private root.

    Test callers may inject the native module facades; production uses the
    OPNsense modules and reads the complete detached XML through OPNsense's
    standard Python Config parser. No user-supplied template names or paths.
    """
    candidate, target_root = Path(candidate), Path(target_root)
    uid = os.geteuid() if owner is None else owner
    regular(candidate.parent, uid, directory=True)
    regular(candidate, uid)
    if target_root.parent != candidate.parent or target_root.name != "templates":
        raise NativeDetachedRenderError("template target outside single operation")
    if target_root.exists() or target_root.is_symlink():
        raise NativeDetachedRenderError("shared detached template root not empty")
    try:
        # No external DTDs or XML entities. A valid native Config is always
        # the complete <opnsense> document, not a Zapret subtree fragment.
        raw = candidate.read_bytes()
        if not raw or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise NativeDetachedRenderError("unsafe detached Config document")
        document = ET.fromstring(raw)
        if document.tag != "opnsense" or len(document.findall("OPNsense")) != 1 or \
           len(document.findall("./OPNsense/Zapret")) != 1:
            raise NativeDetachedRenderError("detached native Config lacks one Zapret mount")
    except (ET.ParseError, UnicodeError, OSError) as error:
        raise NativeDetachedRenderError("invalid detached native Config") from error

    if template_factory is None or config_factory is None:
        # The same installed modules that configd template reload uses.
        # Script execution from /usr/local/opnsense/scripts is not otherwise
        # guaranteed to include /usr/local/opnsense/service in sys.path.
        sys.path.insert(0, "/usr/local/opnsense/service")
        from modules import config, template
        template_factory = template.Template
        config_factory = config.Config

    target_root.mkdir(mode=0o700)
    mode = os.umask(0o077)
    try:
        tmpl = template_factory(target_root_directory=str(target_root))
        configured = tmpl.list_module(MODULE)
        if not isinstance(configured, dict) or configured.get("+TARGETS") != TARGETS:
            raise NativeDetachedRenderError("unexpected Zapret native template targets")
        tmpl.set_config(config_factory(str(candidate)).get())
        filenames = tmpl.generate(MODULE)
        expected = {
            target_root / rel.lstrip("/") for rel in TARGETS.values()
        }
        if not isinstance(filenames, list) or set(map(Path, filenames)) != expected:
            raise NativeDetachedRenderError("native template output set differs from Zapret +TARGETS")
        for item in expected:
            regular(item, uid)
            # Ensure no symlink appeared in the generated target path.
            pointer = item.parent
            while pointer != target_root:
                regular(pointer, uid, directory=True)
                pointer = pointer.parent
        return sorted(expected)
    finally:
        os.umask(mode)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] != "render" or not OPERATION.fullmatch(argv[2]):
        print("usage: shared_apply_render.py render OPERATION_ID", file=sys.stderr)
        return 64
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        regular(WORK_ROOT, 0, directory=True)
        work = WORK_ROOT / argv[2]
        regular(work, 0, directory=True)
        output = render_detached(work / "candidate.xml", work / "templates", owner=0)
        for item in output:
            print(item)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print("ERROR: common detached template refused: " + str(error), file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
