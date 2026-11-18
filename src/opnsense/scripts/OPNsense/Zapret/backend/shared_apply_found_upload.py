#!/usr/bin/env python3
"""Read ONLY the PHP multipart upload for one original native FD9 Apply.

No target writes, additional Config writer, registered configd action, daemon,
or durable transport files. The upload exists for the current HTTP request.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import pwd
import re
import stat
import sys

MAX_BYTES = 320 * 1024
HASH = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
# Match PHP's mkstemp name with or without its newer base32 prefix.
NAME = re.compile(r"php(?:[0-9a-v]{13})?[A-Za-z0-9]{6}\Z", re.ASCII)


class UploadRefused(ValueError):
    pass


def read_qualified(path: Path, length: int, digest: str, owner_uid: int,
                   *, test_parent: Path | None = None) -> bytes:
    """Read one pinned inode via O_NOFOLLOW/O_NONBLOCK, never a symlink/FIFO.

    The disposable test_parent override is not reachable from the CLI.
    """
    if (type(length) is not int or length < 1 or length > MAX_BYTES or
            type(owner_uid) is not int or owner_uid < 0 or
            not isinstance(digest, str) or not HASH.fullmatch(digest)):
        raise UploadRefused("metadata")
    path = Path(path)
    parent_path = Path('/var/lib/php/tmp') if test_parent is None else test_parent
    if path.parent != parent_path or not NAME.fullmatch(path.name):
        raise UploadRefused("path")
    try:
        parent = path.parent.lstat()
        if test_parent is None:
            parent_mode = 0o1777
            allowed_owners = {0}
            if parent.st_uid != 0:
                try:
                    # OPNsense's PHP boot setup assigns the native WebGUI account.
                    allowed_owners.add(pwd.getpwnam("wwwonly").pw_uid)
                except KeyError:
                    pass
        else:
            parent_mode = 0o700
            allowed_owners = {os.geteuid()}
        if (not stat.S_ISDIR(parent.st_mode) or
                stat.S_IMODE(parent.st_mode) != parent_mode or
                parent.st_uid not in allowed_owners):
            raise UploadRefused("directory")
        named = path.lstat()
        if (not stat.S_ISREG(named.st_mode) or named.st_uid != owner_uid or
                named.st_nlink != 1 or stat.S_IMODE(named.st_mode) != 0o600 or
                named.st_size != length):
            raise UploadRefused("inode")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            pinned = os.fstat(fd)
            payload = os.read(fd, MAX_BYTES + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        listed = path.lstat()
    except FileNotFoundError as exc:
        raise UploadRefused("missing") from exc
    except OSError as exc:
        raise UploadRefused("reader") from exc
    identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_uid,
                           st.st_mode, st.st_mtime_ns, st.st_ctime_ns)
    if (identity(named) != identity(pinned) or
            identity(named) != identity(after) or
            identity(named) != identity(listed) or
            len(payload) != length or
            hashlib.sha256(payload).hexdigest() != digest):
        raise UploadRefused("changed")
    return payload


def main(argv: list[str]) -> int:
    if (not sys.platform.startswith('freebsd') or os.geteuid() != 0 or
            len(argv) != 4):
        return 69
    try:
        path, size, digest, uid = argv
        if (not size.isascii() or not size.isdecimal() or
                not uid.isascii() or not uid.isdecimal()):
            raise UploadRefused("metadata")
        data = read_qualified(Path(path), int(size), digest, int(uid))
    except UploadRefused as exc:
        # Report only the fixed failure code to the original PHP parent.
        print(str(exc))
        return 69
    except (ValueError, OSError):
        return 69
    sys.stdout.buffer.write(data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
