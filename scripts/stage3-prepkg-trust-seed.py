# Reviewed operator-side Python -I -B -c seed, NOT automatically trusted by
# being downloaded or checked into this repository. Its bytes must first be
# independently authenticated; a human-recorded receipt is NOT an issuer key.
# Only a read-only, signed-provenance predecessor inspection is supported.
import hashlib
import hmac
import json
import os
import re
import stat
import sys

PREFIX = "ZAPRET2_PREPKG_TRUST_SEED="
MAX_BYTES = 256 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+_[1-9][0-9]*\Z")
RECEIPT_SCHEMA = "zapret2-prepkg-operator-pins-v1"
REPO = "Tolian82/os-zapret2-restyle"
RECEIPT_STATUS = "PINS_RECORDED_NOT_AUTHENTICATED"
PIN_FIELDS = frozenset(("seed_sha256", "verifier_sha256", "public_key_sha256",
                        "source_commit", "incoming_version", "incoming_sha256",
                        "predecessor_version", "predecessor_sha256"))
RECEIPT_FIELDS = PIN_FIELDS | {"schema", "repository", "trust_status"}
MAX_RECEIPT = 4096


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



def operator_receipt(path):
    # This reads manual pins, it does NOT certify the operator or issuer.
    need(isinstance(path, str) and path.startswith("/root/") and
         os.path.isabs(path) and os.path.normpath(path) == path and
         os.path.basename(path) == "operator-pins.json" and
         "\x00" not in path, "OPERATOR_RECEIPT_PRIVATE_ROOT_REQUIRED")
    parent = os.path.dirname(path)
    leaf = parent
    while True:
        st = os.lstat(leaf)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             not stat.S_IMODE(st.st_mode) & 0o022,
             "OPERATOR_RECEIPT_PARENT_UNTRUSTED")
        if leaf == parent:
            need(stat.S_IMODE(st.st_mode) == 0o700,
                 "OPERATOR_RECEIPT_PARENT_0700_REQUIRED")
        if leaf == "/root":
            break
        leaf = os.path.dirname(leaf)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        refuse("OPERATOR_RECEIPT_OPEN_REFUSED")
    try:
        original = os.fstat(fd)
        named = os.lstat(path)
        for st in (original, named):
            need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
                 st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and
                 0 < st.st_size < MAX_RECEIPT,
                 "OPERATOR_RECEIPT_PRIVATE_REGULAR_REQUIRED")
        need((original.st_dev, original.st_ino) == (named.st_dev, named.st_ino),
             "OPERATOR_RECEIPT_INODE_MISMATCH")
        raw = bytearray()
        while True:
            block = os.read(fd, MAX_RECEIPT)
            if not block:
                break
            raw.extend(block)
            need(len(raw) < MAX_RECEIPT, "OPERATOR_RECEIPT_OVERSIZE")
        final = os.fstat(fd)
        named_after = os.lstat(path)
        need((original.st_dev, original.st_ino, original.st_size,
              original.st_mtime_ns, original.st_ctime_ns) ==
             (final.st_dev, final.st_ino, final.st_size,
              final.st_mtime_ns, final.st_ctime_ns) and
             (final.st_dev, final.st_ino) ==
             (named_after.st_dev, named_after.st_ino) and
             len(raw) == original.st_size,
             "OPERATOR_RECEIPT_CHANGED_DURING_READ")
    finally:
        os.close(fd)

    def unique(pairs):
        result = {}
        for name, value in pairs:
            need(name not in result, "OPERATOR_RECEIPT_DUPLICATE_KEY")
            result[name] = value
        return result
    try:
        value = json.loads(bytes(raw).decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError):
        refuse("OPERATOR_RECEIPT_INVALID_JSON")
    need(isinstance(value, dict) and set(value) == RECEIPT_FIELDS and
         value["schema"] == RECEIPT_SCHEMA and
         value["repository"] == REPO and
         value["trust_status"] == RECEIPT_STATUS,
         "OPERATOR_RECEIPT_IDENTITY_UNQUALIFIED")
    for key in ("seed_sha256", "verifier_sha256", "public_key_sha256",
                "incoming_sha256", "predecessor_sha256"):
        need(isinstance(value[key], str) and
             SHA.fullmatch(value[key]) is not None and
             value[key] != "0" * 64, "OPERATOR_RECEIPT_DIGEST_INVALID:" + key)
    need(isinstance(value["source_commit"], str) and
         COMMIT.fullmatch(value["source_commit"]) is not None and
         value["source_commit"] != "0" * 40,
         "OPERATOR_RECEIPT_COMMIT_INVALID")
    for key in ("incoming_version", "predecessor_version"):
        need(isinstance(value[key], str) and
             VERSION.fullmatch(value[key]) is not None,
             "OPERATOR_RECEIPT_VERSION_INVALID:" + key)
    need(value["incoming_version"] != value["predecessor_version"],
         "OPERATOR_RECEIPT_SAME_ARCHIVE_VERSION")
    return value


def main():
    # This exact mode is independently validated before external source code
    # executes. Never forward an arbitrary argv to verified Python code.
    need(len(sys.argv) == 15 and sys.argv[1] == "--operator-receipt" and
         sys.argv[3] == "--verified-verifier" and
         sys.argv[5] == "--signed-provenance" and
         sys.argv[10] == "inspect-predecessor",
         "SIGNED_READ_ONLY_VERIFIER_COMMAND_REQUIRED")
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "ROOT_FREEBSD_AMD64_REQUIRED")
    pins = operator_receipt(sys.argv[2])
    need(sys.argv[12] == pins["incoming_version"] and
         sys.argv[14] == pins["predecessor_version"] and
         os.path.basename(sys.argv[11]) ==
             "os-zapret2-restyle-" + pins["incoming_version"] + ".pkg" and
         os.path.basename(sys.argv[13]) ==
             "os-zapret2-restyle-" + pins["predecessor_version"] + ".pkg",
         "OPERATOR_RECEIPT_TARGET_NOT_MATCHED")
    path, digest = sys.argv[4], pins["verifier_sha256"]
    frozen = verified_verifier(path, digest)
    try:
        compiled = compile(frozen, path, "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError):
        refuse("VERIFIER_INVALID_PYTHON")
    # No digest/commit values supplied by command-line caller are forwarded.
    sys.argv = ["-c", "--expected-source-commit", pins["source_commit"],
                "--expected-archive-pins", pins["incoming_sha256"],
                pins["predecessor_sha256"], "--signed-provenance",
                pins["public_key_sha256"]] + sys.argv[6:]
    sys.dont_write_bytecode = True
    print(PREFIX + "VERIFIED_SHA256:" + digest, file=sys.stderr, flush=True)
    print(PREFIX + "RECEIPT_PINS_BOUND_NOT_AUTHENTICATED",
          file=sys.stderr, flush=True)
    exec(compiled, {"__name__": "__main__", "__file__": path,
                    "__package__": None, "__builtins__": __builtins__})


try:
    main()
except (OSError, ValueError, TypeError, UnicodeError) as exc:
    refuse("VERIFIER_VERIFY_UNAVAILABLE:" + type(exc).__name__)
