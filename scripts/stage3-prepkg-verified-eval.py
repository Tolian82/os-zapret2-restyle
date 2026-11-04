# Trusted operator-reviewed input to Python -I -B -c; NEVER execute this
# downloaded code as a file without separately authenticating its origin.
# External pre-execution hash expectation is supplied independently of the
# target .py. No pkg dispatch, no network, no project/old-plugin imports.
import hashlib
import hmac
import os
import re
import stat
import sys

PREFIX = "ZAPRET2_PREPKG_VERIFY_EXEC="
MAX_BYTES = 256 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")


def refuse(reason):
    print(PREFIX + "REFUSED:" + reason, file=sys.stderr)
    raise SystemExit(78)


def need(ok, reason):
    if not ok:
        refuse(reason)


def trusted_root_path(path):
    need(os.path.isabs(path) and
         os.path.normpath(path) == path and
         path.startswith("/root/") and
         path != "/root/" and
         "\x00" not in path,
         "EXTERNAL_SOURCE_OUTSIDE_PRIVATE_ROOT")
    # Every ancestor must be owned by root and not writable by others.
    parent = os.path.dirname(path)
    while True:
        st = os.lstat(parent)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             not stat.S_IMODE(st.st_mode) & 0o022,
             "EXTERNAL_SOURCE_PARENT_UNTRUSTED")
        if parent == "/root":
            break
        next_parent = os.path.dirname(parent)
        need(next_parent != parent, "EXTERNAL_SOURCE_PARENT_ESCAPE")
        parent = next_parent


def verify_source_bytes(path, digest):
    trusted_root_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        refuse("EXTERNAL_SOURCE_OPEN_REFUSED")
    try:
        original = os.fstat(fd)
        current = os.lstat(path)
        for st in (original, current):
            need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
                 st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and
                 0 < st.st_size <= MAX_BYTES,
                 "EXTERNAL_SOURCE_REGULAR_PRIVATE_ROOT_FILE_REQUIRED")
        need((original.st_dev, original.st_ino) ==
             (current.st_dev, current.st_ino),
             "EXTERNAL_SOURCE_INODE_MISMATCH")
        payload = bytearray()
        while True:
            block = os.read(fd, 64 * 1024)
            if not block:
                break
            need(len(payload) + len(block) <= MAX_BYTES,
                 "EXTERNAL_SOURCE_OVERSIZE")
            payload.extend(block)
        after = os.fstat(fd)
        pathname = os.lstat(path)
        need((original.st_dev, original.st_ino, original.st_size,
              original.st_mtime_ns, original.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size,
              after.st_mtime_ns, after.st_ctime_ns) and
             (after.st_dev, after.st_ino) ==
             (pathname.st_dev, pathname.st_ino),
             "EXTERNAL_SOURCE_CHANGED_DURING_VERIFICATION")
        observed = hashlib.sha256(payload).hexdigest()
        need(hmac.compare_digest(observed, digest),
             "EXTERNAL_SOURCE_EXPECTED_SHA256_MISMATCH")
        # Return immutable verified bytes. Nothing opens the filename a second
        # time for execution, avoiding the verification->execution path race.
        return bytes(payload)
    finally:
        os.close(fd)


def main():
    need(len(sys.argv) >= 4 and sys.argv[3] == "inspect-predecessor" and
         len(sys.argv) == 10,
         "ONLY_READ_ONLY_PREDECESSOR_COMMAND_SUPPORTED")
    digest, filename = sys.argv[1:3]
    need(SHA.fullmatch(digest) is not None,
         "EXTERNAL_SOURCE_SHA256_EXPECTATION_REQUIRED")
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "ROOT_FREEBSD_AMD64_REQUIRED")
    verified = verify_source_bytes(filename, digest)
    try:
        executable = compile(verified, filename, "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError):
        refuse("EXTERNAL_SOURCE_NOT_VALID_PYTHON")
    # The verified code is now in-memory; never re-open the script for Python
    # source execution. The candidate still has its own root-inode check.
    sys.argv = [filename] + sys.argv[3:]
    sys.dont_write_bytecode = True
    print(PREFIX + "VERIFIED_SHA256:" + digest, file=sys.stderr, flush=True)
    exec(executable, {"__name__": "__main__", "__file__": filename,
                      "__package__": None, "__builtins__": __builtins__})


try:
    main()
except (OSError, UnicodeError, ValueError, TypeError) as err:
    refuse("EXTERNAL_SOURCE_VERIFY_UNAVAILABLE:" + type(err).__name__)
