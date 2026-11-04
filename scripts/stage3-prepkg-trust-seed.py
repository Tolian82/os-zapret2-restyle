# Reviewed operator-side Python -I -B -c seed, NOT automatically trusted by
# being downloaded or checked into this repository. The verifier SHA-256 and
# this seed's bytes must be authenticated independently of the incoming pkg.
# Only a read-only, signed-provenance predecessor inspection is supported.
import hashlib
import hmac
import os
import re
import stat
import sys

PREFIX = "ZAPRET2_PREPKG_TRUST_SEED="
MAX_BYTES = 256 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")


def refuse(why):
    print(PREFIX + "REFUSED:" + why, file=sys.stderr)
    raise SystemExit(78)


def need(ok, why):
    if not ok:
        refuse(why)


def trusted_root_path(path):
    need(isinstance(path, str) and os.path.isabs(path) and
         os.path.normpath(path) == path and path.startswith("/root/") and
         path != "/root/" and "\x00" not in path and
         os.path.basename(path) == "stage3-prepkg-verified-eval.py",
         "VERIFIER_OUTSIDE_PRIVATE_ROOT")
    parent = os.path.dirname(path)
    while True:
        st = os.lstat(parent)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             not stat.S_IMODE(st.st_mode) & 0o022,
             "VERIFIER_PARENT_UNTRUSTED")
        if parent == "/root":
            break
        next_parent = os.path.dirname(parent)
        need(next_parent != parent, "VERIFIER_PARENT_ESCAPE")
        parent = next_parent


def verified_verifier(path, expected):
    need(isinstance(expected, str) and SHA.fullmatch(expected) is not None,
         "INDEPENDENT_VERIFIER_SHA256_REQUIRED")
    trusted_root_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        refuse("VERIFIER_OPEN_REFUSED")
    try:
        initial = os.fstat(fd)
        named = os.lstat(path)
        for st in (initial, named):
            need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
                 st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and
                 0 < st.st_size <= MAX_BYTES,
                 "VERIFIER_PRIVATE_REGULAR_REQUIRED")
        need((initial.st_dev, initial.st_ino) == (named.st_dev, named.st_ino),
             "VERIFIER_INODE_MISMATCH")
        payload = bytearray()
        while True:
            block = os.read(fd, 64 * 1024)
            if not block:
                break
            need(len(payload) + len(block) <= MAX_BYTES, "VERIFIER_OVERSIZE")
            payload.extend(block)
        final = os.fstat(fd)
        current = os.lstat(path)
        need((initial.st_dev, initial.st_ino, initial.st_size,
              initial.st_mtime_ns, initial.st_ctime_ns) ==
             (final.st_dev, final.st_ino, final.st_size,
              final.st_mtime_ns, final.st_ctime_ns) and
             (final.st_dev, final.st_ino) ==
             (current.st_dev, current.st_ino), "VERIFIER_CHANGED_DURING_READ")
        need(hmac.compare_digest(hashlib.sha256(payload).hexdigest(), expected),
             "VERIFIER_EXPECTED_SHA256_MISMATCH")
        return bytes(payload)
    finally:
        os.close(fd)


def main():
    # This exact mode is independently validated before external source code
    # executes. Never forward an arbitrary argv to verified Python code.
    need(len(sys.argv) == 15 and sys.argv[1] == "--verified-verifier" and
         sys.argv[4] == "--signed-provenance" and
         sys.argv[10] == "inspect-predecessor",
         "SIGNED_READ_ONLY_VERIFIER_COMMAND_REQUIRED")
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "ROOT_FREEBSD_AMD64_REQUIRED")
    path, digest = sys.argv[3], sys.argv[2]
    frozen = verified_verifier(path, digest)
    try:
        compiled = compile(frozen, path, "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError):
        refuse("VERIFIER_INVALID_PYTHON")
    sys.argv = ["-c"] + sys.argv[4:]
    sys.dont_write_bytecode = True
    print(PREFIX + "VERIFIED_SHA256:" + digest, file=sys.stderr, flush=True)
    exec(compiled, {"__name__": "__main__", "__file__": path,
                    "__package__": None, "__builtins__": __builtins__})


try:
    main()
except (OSError, ValueError, TypeError, UnicodeError) as exc:
    refuse("VERIFIER_VERIFY_UNAVAILABLE:" + type(exc).__name__)
