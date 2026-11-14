#!/usr/bin/env python3
"""P2b read-only FreeBSD inode/FD evidence; NOT an acknowledgement adapter.

Require a real P2c-bound current owner, then check ALL open references to
the exact detached inode. Inspecting only that current PID misses a still
open writer FD inherited from an older generation or an unrelated process.
The existing original v2 caller uses this inspector; no separate worker,
queue, Config writer, ACK grant or process owner is created here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


class FDState(str, Enum):
    BUSY = "busy"          # The target inode is still open, even for reading.
    DRAINED = "drained"    # Qualified process still exists, target FD absent.
    UNKNOWN = "unknown"    # Never means permission to acknowledge pending.


@dataclass(frozen=True)
class OwnerToken:
    pid: int
    started: str          # Exact native ps lstart token, fixed at engine launch.
    executable: str       # Exact absolute binary from qualified common owner.


_HEADER = ("USER", "CMD", "PID", "FD", "DEV", "INUM", "MODE", "SZ|DV", "R/W", "NAME")
_START = re.compile(r"^[A-Z][a-z]{2} [A-Z][a-z]{2}\s+\d{1,2} "
                    r"\d{2}:\d{2}:\d{2} \d{4}$", re.ASCII)
_DEVICE = re.compile(r"^0x[0-9a-fA-F]+$", re.ASCII)
_FD = re.compile(r"^\d+$", re.ASCII)


def _command(args: list[str], runner) -> str:
    reply = runner(args, capture_output=True, text=True, timeout=5, check=False)
    if reply.returncode != 0 or reply.stderr or len(reply.stdout) > 131072 or not reply.stdout:
        raise ValueError("native_command_untrusted")
    return reply.stdout


def _owner_snapshot(token: OwnerToken, runner) -> bool:
    output = _command(["/bin/ps", "-ww", "-p", str(token.pid),
                       "-o", "lstart=", "-o", "command="], runner)
    lines = output.strip().splitlines()
    if len(lines) != 1:
        return False
    fields = lines[0].split(maxsplit=5)
    if len(fields) != 6:
        return False
    born, executable = " ".join(fields[:5]), fields[5].split(maxsplit=1)[0]
    return born == token.started and executable == token.executable


def _all_rows(output: str, device: int, inode: int, *,
              inspector_pid: int, inspector_fd: int) -> FDState:
    """FreeBSD -n -v -m <file>: inspect every process, not just P2c PID.

    The inspector deliberately holds one read-only FD to pin the inode.
    Skip ONLY that exact own read FD; any other open reference (including
    former dvtws2 writer PID, children, readers, mmap) blocks or refuses.
    Unknown/partial rows, mismatched inodes or kernel warnings never drain.
    """
    lines = output.splitlines()
    if (not lines or tuple(lines[0].split()) != _HEADER or
            len(lines) > 4097 or type(inspector_pid) is not int or
            inspector_pid <= 1 or type(inspector_fd) is not int or
            inspector_fd < 0):
        return FDState.UNKNOWN
    busy = False
    for line in lines[1:]:
        columns = line.split()
        if (len(columns) < 10 or not columns[2].isdigit() or
                int(columns[2]) <= 1 or not _FD.fullmatch(columns[3])):
            return FDState.UNKNOWN
        found_dev = _DEVICE.fullmatch(columns[4])
        if (not found_dev or not columns[5].isdigit() or
                not columns[6].isdigit() or
                int(found_dev.group(0), 16) != device or
                int(columns[5]) != inode or
                columns[8] not in {"r", "w", "rw"}):
            return FDState.UNKNOWN
        if (int(columns[2]) == inspector_pid and
                int(columns[3]) == inspector_fd and columns[8] == "r"):
            continue
        busy = True
    return FDState.BUSY if busy else FDState.DRAINED

def probe_pending_fd(segment: Path, device_id: int, inode: int, *,
                     owner: OwnerToken, runner=subprocess.run,
                     platform: str | None = None,
                     writer_gid: int | None = None) -> FDState:
    """Attest current P2c process AND every open original raw inode FD.

    A currently running owner with no FD is insufficient: a historical
    engine/child may still append to the same hardlink. Kernel-wide -m
    fstat and exact protected inode/owner snapshots must all be stable.
    Never call the P2a ACK directly: original Config/v2 checkpoints rule.
    """
    if platform is None:
        platform = sys.platform
    if not platform.startswith("freebsd") or os.geteuid() != 0:
        return FDState.UNKNOWN
    if (not isinstance(owner, OwnerToken) or type(owner.pid) is not int or
            owner.pid <= 1 or not isinstance(owner.started, str) or
            not _START.fullmatch(owner.started) or
            not isinstance(owner.executable, str) or
            not owner.executable.startswith("/") or "\x00" in owner.executable or
            any(c.isspace() for c in owner.executable) or
            type(device_id) is not int or type(inode) is not int or
            device_id < 0 or inode <= 0):
        return FDState.UNKNOWN
    path = Path(segment)
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_dev != device_id or
                before.st_ino != inode or before.st_nlink != 1 or before.st_uid != 0):
            return FDState.UNKNOWN
        if writer_gid is None:
            if before.st_mode & 0o022:
                return FDState.UNKNOWN
        elif (type(writer_gid) is not int or writer_gid <= 0 or
              before.st_gid != writer_gid or
              stat.S_IMODE(before.st_mode) != 0o660):
            return FDState.UNKNOWN
        if not _owner_snapshot(owner, runner):
            return FDState.UNKNOWN
        # -m includes memory maps; -n produces a native hex dev_t (0x...).
        # Crucially NO -p filter: an older engine/child with a retained FD
        # is not the current P2c process, yet it can still append after ACK.
        evidence = _command(["/usr/bin/fstat", "-n", "-v", "-m", str(path)],
                            runner)
        state = _all_rows(evidence, before.st_dev, inode,
                          inspector_pid=os.getpid(), inspector_fd=fd)
        if state == FDState.UNKNOWN or not _owner_snapshot(owner, runner):
            return FDState.UNKNOWN
        after = os.fstat(fd)
        pathname = path.lstat()
        if (after.st_dev, after.st_ino, after.st_nlink, after.st_size,
                after.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_nlink,
                                       before.st_size, before.st_mtime_ns):
            return FDState.UNKNOWN
        if (pathname.st_dev, pathname.st_ino, pathname.st_nlink) != (
                before.st_dev, before.st_ino, 1):
            return FDState.UNKNOWN
        return state
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError):
        return FDState.UNKNOWN
    finally:
        if fd is not None:
            os.close(fd)


def main() -> int:
    raise SystemExit("P2b native FD probe is not a standalone production worker")


if __name__ == "__main__":
    main()
