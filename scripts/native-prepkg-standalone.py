#!/usr/bin/env python3
"""Standalone, root-only, *read-only* pre-pkg inspection entrypoint.

This file runs outside the predecessor installation AND outside a source
checkout. An authenticated operator must provision this file independently
and obtain both archive SHA-256 values through a trusted channel. Caller
arguments, metadata inside the archive and root ownership alone do NOT
authenticate the bootstrap or establish a supported firmware update gateway.

No upgrade/reinstall/remove/pkg mutation dispatch exists. A cold predecessor
screen is never sufficient authorization for destructive pkg replacement.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

NAME = "os-zapret2-restyle"
ARCHIVE_PREFIX = "/usr/local/opnsense/scripts/OPNsense/Zapret/backend/"
MODULES = ("native_pkg_managed.py", "native_pkg_handoff.py",
           "native_pkg_candidate.py", "native_pkg_old_owner.py")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+_[1-9][0-9]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_PKG = 512 * 1024 * 1024
MAX_MODULE = 512 * 1024
MAX_MANIFEST = 2 * 1024 * 1024
MAX_LIST = 4 * 1024 * 1024
PREFIX = "ZAPRET2_PREPKG_STANDALONE="
ROOT = Path("/root")


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def require_root_source():
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "ROOT_FREEBSD_AMD64_REQUIRED")
    source = Path(__file__)
    need(source.is_absolute() and not source.is_symlink(),
         "EXTERNAL_BOOTSTRAP_SOURCE_UNQUALIFIED")
    stat_source = source.lstat()
    need(stat.S_ISREG(stat_source.st_mode) and stat_source.st_uid == 0 and
         stat_source.st_nlink == 1 and
         not stat.S_IMODE(stat_source.st_mode) & 0o022,
         "EXTERNAL_BOOTSTRAP_SOURCE_OWNER_OR_MODE_UNQUALIFIED")
    # A trusted external SHA/signature for these bytes must be established
    # BEFORE invoking Python; checking our own hash here is not authentication.
    for directory in (source.parent, ROOT):
        st = directory.lstat()
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             not stat.S_IMODE(st.st_mode) & 0o022 and
             not directory.is_symlink(),
             "EXTERNAL_BOOTSTRAP_ROOT_DIRECTORY_UNTRUSTED")
    return hashlib.sha256(source.read_bytes()).hexdigest()


def identity(path, version, sha):
    need(isinstance(path, Path) and path.is_absolute() and
         not path.is_symlink() and VERSION.fullmatch(version or "") and
         SHA256.fullmatch(sha or "") and
         path.name == NAME + "-" + version + ".pkg",
         "ARCHIVE_EXPECTATION_UNQUALIFIED")


def verified_archive(path, version, sha):
    """Exact user-supplied digest, opened inode, no path-following, stable bytes."""
    identity(path, version, sha)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Refusal("ARCHIVE_OPEN_REFUSED") from None
    try:
        original = os.fstat(fd)
        found = path.lstat()
        for st in (original, found):
            need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
                 st.st_nlink == 1 and not stat.S_IMODE(st.st_mode) & 0o022 and
                 0 < st.st_size <= MAX_PKG,
                 "ARCHIVE_ROOT_OWNED_REGULAR_REQUIRED")
        need((original.st_dev, original.st_ino) == (found.st_dev, found.st_ino),
             "ARCHIVE_INODE_CHANGED")
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        final = os.fstat(fd)
        now = path.lstat()
        before = (original.st_dev, original.st_ino, original.st_size,
                  original.st_mtime_ns, original.st_ctime_ns)
        after = (final.st_dev, final.st_ino, final.st_size,
                 final.st_mtime_ns, final.st_ctime_ns)
        need(before == after and (now.st_dev, now.st_ino) ==
             (final.st_dev, final.st_ino), "ARCHIVE_CHANGED_DURING_READ")
        need(hmac.compare_digest(digest.hexdigest(), sha),
             "ARCHIVE_SHA256_MISMATCH")
        return (final.st_dev, final.st_ino, final.st_size)
    finally:
        os.close(fd)


def read_tar(archive, operation, member=None, limit=MAX_MODULE):
    args = ["/usr/bin/tar", operation, str(archive)]
    if member is not None:
        args.append(member)
    try:
        proc = subprocess.run(args, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=35, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_TAR_UNAVAILABLE_OR_TIMED_OUT") from None
    need(proc.returncode == 0 and len(proc.stdout) <= limit,
         "NATIVE_TAR_FAILED_OR_OVERSIZED:" + operation)
    return proc.stdout


def find_modules(archive):
    entries = read_tar(archive, "-tf", limit=MAX_LIST).decode("utf-8").splitlines()
    need(bool(entries), "NATIVE_ARCHIVE_MEMBERS_EMPTY")
    matches = {}
    for name in MODULES:
        expected = ARCHIVE_PREFIX + name
        exact = [entry for entry in entries
                 if ".." not in Path(entry).parts and
                 (entry == expected or
                  (not entry.startswith("/") and
                   entry.lstrip("./") == expected.lstrip("/")))]
        need(len(exact) == 1, "ARCHIVE_MODULE_ABSENT_OR_DUPLICATED:" + name)
        matches[name] = exact[0]
    return matches


def source_bytes(archive, version):
    raw = read_tar(archive, "-xOf", "+MANIFEST", MAX_MANIFEST)
    try:
        manifest = json.loads(raw)
    except (UnicodeError, ValueError):
        raise Refusal("NATIVE_MANIFEST_INVALID") from None
    need(isinstance(manifest, dict) and manifest.get("name") == NAME and
         manifest.get("version") == version and
         manifest.get("abi") == "FreeBSD:15:amd64" and
         manifest.get("arch") == "freebsd:15:x86:64",
         "NATIVE_MANIFEST_PRODUCT_OR_ABI_UNQUALIFIED")
    files = manifest.get("files")
    need(isinstance(files, dict), "NATIVE_MANIFEST_FILES_UNQUALIFIED")
    members = find_modules(archive)
    extracted = {}
    for name, member in members.items():
        need(isinstance(files.get(ARCHIVE_PREFIX + name), str) and
             bool(files[ARCHIVE_PREFIX + name]),
             "NATIVE_MANIFEST_MODULE_NOT_DECLARED:" + name)
        data = read_tar(archive, "-xOf", member, MAX_MODULE)
        need(0 < len(data) < MAX_MODULE and
             data.startswith(b"#!/usr/bin/env python3\n"),
             "NATIVE_ARCHIVED_PYTHON_SOURCE_INVALID:" + name)
        extracted[name] = data
    return extracted


def stage(root, data):
    st = root.lstat()
    need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
         stat.S_IMODE(st.st_mode) == 0o700 and not root.is_symlink(),
         "STAGING_PRIVATE_ROOT_UNTRUSTED")
    need(set(data) == set(MODULES), "STAGING_SOURCE_SET_UNQUALIFIED")
    for name in MODULES:
        target = root / name
        need(not target.exists() and not target.is_symlink(),
             "STAGING_OUTPUT_ALREADY_EXISTS:" + name)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            content = data[name]
            while content:
                count = os.write(fd, content)
                need(count > 0, "STAGING_SHORT_WRITE")
                content = content[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        st = target.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
             st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and
             target.read_bytes() == data[name],
             "STAGING_BYTE_OR_INODE_DRIFT:" + name)
    return root / "native_pkg_managed.py"


def inspect(incoming, version, expected, old, old_version, old_sha):
    source_sha = require_root_source()
    verified_archive(incoming, version, expected)
    verified_archive(old, old_version, old_sha)
    modules = source_bytes(incoming, version)
    verified_archive(incoming, version, expected)
    with tempfile.TemporaryDirectory(prefix="zapret2-prepkg-only-", dir=str(ROOT)) as temp:
        cli = stage(Path(temp), modules)
        argv = [sys.executable, "-E", "-B", str(cli), "inspect-predecessor",
                str(old), old_version, old_sha]
        # Discard untrusted Python env/PATH and operate outside checkout.
        env = {"PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin",
               "HOME": "/root", "LANG": "C"}
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, cwd=str(ROOT),
                                    env=env, capture_output=True, text=True,
                                    timeout=155, check=False)
        except (OSError, subprocess.SubprocessError):
            raise Refusal("READ_ONLY_MANAGED_WORKER_UNAVAILABLE") from None
        need(result.returncode == 0 and
             result.stdout.startswith("ZAPRET2_MANAGED=") and
             result.stdout.count("\n") == 1,
             "READ_ONLY_MANAGED_PREDECESSOR_REFUSED:" +
             result.stderr[-180:].replace("\n", " "))
        try:
            response = json.loads(result.stdout.split("=", 1)[1])
        except (ValueError, UnicodeError):
            raise Refusal("READ_ONLY_MANAGED_RESULT_UNTRUSTED") from None
        need(isinstance(response, dict) and
             response.get("status") == "PASS_MANAGED_READ_ONLY_PREDECESSOR_SCREEN" and
             response.get("predecessor_cold_screened") is True and
             response.get("archive_sha256") == old_sha and
             response.get("pkg_invoked") is False and
             response.get("old_owner_qualified") is False and
             response.get("lh08_ac11_accepted") is False,
             "READ_ONLY_MANAGED_RESULT_FALSE_AUTHORIZATION")
        verified_archive(incoming, version, expected)
        verified_archive(old, old_version, old_sha)
    return {"status": "PASS_STANDALONE_PREPKG_READ_ONLY_COLD",
            "incoming_sha256": expected, "old_sha256": old_sha,
            "bootstrap_self_sha256_diagnostic_only": source_sha,
            "modules_sha256": {n: hashlib.sha256(modules[n]).hexdigest()
                               for n in MODULES},
            "old_owner_qualified": False, "pkg_invoked": False,
            "supported_mandatory_entrypoint": False,
            "web_firmware_root_pkg_protected": False,
            "lh08_ac11_accepted": False}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        need(len(args) == 7 and args[0] == "inspect-predecessor",
             "NO_PKG_MUTATION_DISPATCH_OR_INVALID_ARGUMENTS")
        report = inspect(Path(args[1]), args[2], args[3],
                         Path(args[4]), args[5], args[6])
        print(PREFIX + json.dumps(report, sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, TypeError) as exc:
        print(PREFIX + "REFUSED:" + str(exc), file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main())
