"""One temporary hostlist readable after dvtws2 drops to nobody.

The private /var/run/zapret2-restyle tree must never be made traversable to
nobody. Only the ephemeral domain-list copy is staged in the root-owned /var/run
namespace, with group-read-only permission for the runtime's actual group.
"""

from __future__ import annotations

import os
import pwd
import re
import stat
import tempfile
from pathlib import Path

JOB_ID = re.compile(r"^job\.[A-Za-z0-9]+$")
PREFIX = "zapret2-lab-hostlist-"


def path_for(job_id: str) -> Path:
    if not JOB_ID.fullmatch(job_id):
        raise ValueError("invalid Strategy Lab job id")
    return Path(os.environ.get("STRATEGY_LAB_HOSTLIST_STAGING_DIR", "/var/run")) / f"{PREFIX}{job_id}"


def stage(job_id: str, endpoints: list[str]) -> Path:
    """Atomically expose only the hostlist to nobody; never expose the job tree."""
    target = path_for(job_id)
    parent = target.parent
    if parent.is_symlink():
        raise RuntimeError("candidate hostlist staging directory cannot be a symlink")
    info = parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise RuntimeError("candidate hostlist staging directory must be owner-only writable")
    nobody_gid = pwd.getpwnam("nobody").pw_gid
    # Checking only the final directory reproduced the owner's original bug:
    # every ancestor must grant search access to the real post-drop group.
    for ancestor in (parent, *parent.parents):
        mode = ancestor.stat()
        if not stat.S_ISDIR(mode.st_mode) or not (
            mode.st_mode & stat.S_IXOTH
            or (mode.st_gid == nobody_gid and mode.st_mode & stat.S_IXGRP)
        ):
            raise RuntimeError("candidate hostlist staging path is not traversable by nobody")
    root = os.geteuid() == 0
    test_only = (
        not root
        and os.environ.get("STRATEGY_LAB_TEST_WAN_OVERRIDE") == "1"
        and os.environ.get("STRATEGY_LAB_TEST_HOSTLIST_STAGING") == "1"
        and parent != Path("/var/run")
    )
    if not root and not test_only:
        raise RuntimeError("candidate hostlist staging requires root")
    target_gid = nobody_gid if root else os.getegid()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(parent))
    try:
        if root:
            os.fchown(fd, 0, target_gid)
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write("".join(f"{name}\n" for name in endpoints))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    return target
