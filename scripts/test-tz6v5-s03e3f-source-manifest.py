#!/usr/bin/env python3
"""S03e3f CI-host exact Git-tracked byte manifest; no native side effects.

Host Git HEAD is authoritative before vmactions sync:tar. On the OPNsense
guest, the transported .git may be stale; require exact sealed file contents.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / "s03e3f-source-manifest.json"


class Refused(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refused(reason)


def safe_path(name):
    return (isinstance(name, str) and 0 < len(name) <= 350 and
            not name.startswith("/") and "\\" not in name and "\0" not in name
            and all(piece not in ("", ".", "..") for piece in name.split("/")))


def identity(path):
    entry = path.lstat()
    if stat.S_ISREG(entry.st_mode):
        return "file", hashlib.sha256(path.read_bytes()).hexdigest()
    if stat.S_ISLNK(entry.st_mode):
        return "link", hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    raise Refused("S03E3F_NOT_TRACKED_REGULAR_OR_LINK")


def create():
    expected = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         re.fullmatch(r"[a-f0-9]{40}", expected) is not None,
         "S03E3F_MANIFEST_HOST_CI_GATE")
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, check=False, timeout=20)
    need(head.returncode == 0 and head.stdout.decode().strip() == expected,
         "S03E3F_MANIFEST_HOST_GIT_HEAD_NOT_EXACT")
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                             capture_output=True, check=False, timeout=30)
    need(tracked.returncode == 0 and tracked.stdout.endswith(b"\0"),
         "S03E3F_MANIFEST_HOST_GIT_INVENTORY")
    names = [x.decode("utf-8") for x in tracked.stdout[:-1].split(b"\0")]
    need(len(names) >= 100 and len(set(names)) == len(names) and
         all(safe_path(name) for name in names),
         "S03E3F_MANIFEST_HOST_UNSAFE_PATHS")
    entries = []
    for name in sorted(names):
        kind, digest = identity(ROOT / name)
        entries.append({"path": name, "kind": kind, "sha256": digest})
    payload = (json.dumps({"schema": 1, "source_sha": expected,
                           "files": entries}, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("utf-8")
    need(len(payload) <= 2097152 and not MARKER.exists() and
         not MARKER.is_symlink(), "S03E3F_MANIFEST_HOST_OUTPUT_UNSAFE")
    fd = os.open(MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(payload)
        out.flush()
        os.fsync(out.fileno())
    return hashlib.sha256(payload).hexdigest()


def attest(root: Path, expected: str):
    need(root == ROOT and re.fullmatch(r"[a-f0-9]{40}", expected) is not None,
         "S03E3F_MANIFEST_GUEST_SOURCE_IDENTITY")
    digest = os.environ.get("ZAPRET2_S03E3F_SOURCE_MANIFEST_SHA256", "")
    need(re.fullmatch(r"[a-f0-9]{64}", digest) is not None and
         MARKER.is_file() and not MARKER.is_symlink(),
         "S03E3F_MANIFEST_GUEST_BOUNDARY_MISSING")
    payload = MARKER.read_bytes()
    need(len(payload) <= 2097152 and
         hashlib.sha256(payload).hexdigest() == digest,
         "S03E3F_MANIFEST_DIGEST_CHANGED")
    data = json.loads(payload)
    need(type(data) is dict and
         set(data) == {"schema", "source_sha", "files"} and
         data["schema"] == 1 and data["source_sha"] == expected and
         type(data["files"]) is list and len(data["files"]) >= 100,
         "S03E3F_MANIFEST_SOURCE_NOT_EXACT")
    prior = ""
    for item in data["files"]:
        need(type(item) is dict and
             set(item) == {"path", "kind", "sha256"} and
             safe_path(item["path"]) and item["path"] > prior and
             item["kind"] in ("file", "link") and
             type(item["sha256"]) is str and
             re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is not None,
             "S03E3F_MANIFEST_FILE_LIST_UNSAFE")
        prior = item["path"]
        need(identity(ROOT / item["path"]) ==
             (item["kind"], item["sha256"]),
             "S03E3F_MANIFEST_TRACKED_BYTES_MISMATCH")
    return len(data["files"])


def main():
    try:
        need(sys.argv[1:] == ["create"], "S03E3F_MANIFEST_CREATE_ONLY")
        print(create())
        return 0
    except (Refused, OSError, UnicodeError, ValueError,
            subprocess.TimeoutExpired) as error:
        print("S03E3F_MANIFEST=REFUSED:" + str(error)[:120], file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
