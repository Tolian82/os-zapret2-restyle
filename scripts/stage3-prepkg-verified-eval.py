# Operator-reviewed Python -I -B -c code, never run as an unauthenticated file.
# Read-only, pre-pkg signed-provenance verification. Both this -c code and the
# trusted PUBLIC KEY DIGEST must come from an independent authorized channel.
# A test-only signer/key does not qualify an actual production trust anchor.
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import sys
import tempfile

PREFIX = "ZAPRET2_PREPKG_VERIFY_EXEC="
MAX_BYTES = 256 * 1024
STAGING_ROOT = "/root"
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+_[1-9][0-9]*\Z")
SCHEMA = "zapret2-prepkg-provenance-v1"
REPO = "Tolian82/os-zapret2-restyle"
NAME = "os-zapret2-restyle"
EXPECTED_KEYS = frozenset(("schema", "repository", "source_commit",
    "entrypoint_sha256", "incoming_version", "incoming_sha256",
    "predecessor_version", "predecessor_sha256"))


def refuse(reason):
    print(PREFIX + "REFUSED:" + reason, file=sys.stderr)
    raise SystemExit(78)


def need(ok, reason):
    if not ok:
        refuse(reason)


def trusted_root_path(path):
    need(isinstance(path, str) and os.path.isabs(path) and
         os.path.normpath(path) == path and path.startswith("/root/") and
         path != "/root/" and "\x00" not in path,
         "EXTERNAL_SOURCE_OUTSIDE_PRIVATE_ROOT")
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


def private_root_bytes(path):
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
        return bytes(payload)
    finally:
        os.close(fd)


def verify_source_bytes(path, digest):
    need(SHA.fullmatch(digest) is not None,
         "EXTERNAL_SOURCE_SHA256_EXPECTATION_REQUIRED")
    payload = private_root_bytes(path)
    need(hmac.compare_digest(hashlib.sha256(payload).hexdigest(), digest),
         "EXTERNAL_SOURCE_EXPECTED_SHA256_MISMATCH")
    # Execute the frozen, authenticated bytes, never a second pathname open.
    return bytes(payload)


def write_private(directory, basename, payload):
    path = os.path.join(directory, basename)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
    return path


def signed_claims(key_path, pinned_key_sha, claims_path, sig_path):
    need(SHA.fullmatch(pinned_key_sha) is not None,
         "INDEPENDENT_PUBLIC_KEY_SHA256_REQUIRED")
    public_key = private_root_bytes(key_path)
    need(hmac.compare_digest(hashlib.sha256(public_key).hexdigest(),
                             pinned_key_sha),
         "PUBLIC_KEY_NOT_INDEPENDENTLY_PINNED")
    claims = private_root_bytes(claims_path)
    signature = private_root_bytes(sig_path)
    # OpenSSL operates ONLY on captured bytes, placed into fresh private paths.
    # It cannot be tricked into verifying different bytes through path swaps.
    with tempfile.TemporaryDirectory(prefix="zapret2-signed-prepkg-", dir=STAGING_ROOT) as td:
        pub = write_private(td, "pub.pem", public_key)
        sig = write_private(td, "claims.sig", signature)
        try:
            p = subprocess.run(["/usr/bin/openssl", "dgst", "-sha256",
                                "-verify", pub, "-signature", sig],
                               input=claims, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=10,
                               check=False)
        except (OSError, subprocess.SubprocessError):
            refuse("SIGNED_PROVENANCE_CRYPTO_UNAVAILABLE")
        need(p.returncode == 0 and p.stdout.strip() == b"Verified OK",
             "SIGNED_PROVENANCE_SIGNATURE_INVALID")
    try:
        value = json.loads(claims.decode("utf-8"),
                           object_pairs_hook=_reject_duplicate_keys)
    except (ValueError, UnicodeError, TypeError):
        refuse("SIGNED_PROVENANCE_JSON_INVALID")
    need(isinstance(value, dict) and set(value) == EXPECTED_KEYS and
         value["schema"] == SCHEMA and value["repository"] == REPO and
         isinstance(value["source_commit"], str) and
         COMMIT.fullmatch(value["source_commit"]) is not None and
         all(isinstance(value[k], str) and SHA.fullmatch(value[k]) is not None
             for k in ("entrypoint_sha256", "incoming_sha256",
                       "predecessor_sha256")) and
         all(isinstance(value[k], str) and VERSION.fullmatch(value[k]) is not None
             for k in ("incoming_version", "predecessor_version")) and
         value["incoming_version"] != value["predecessor_version"],
         "SIGNED_PROVENANCE_CLAIMS_UNQUALIFIED")
    return value


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def main():
    # Only this signed-provenance read-only command is accepted. In particular,
    # unsigned SHA arguments, mutating package operations and arbitrary Python
    # source commands are NOT accepted, even when the caller is root.
    need(len(sys.argv) == 14 and sys.argv[1] == "--expected-source-commit" and
         sys.argv[3] == "--signed-provenance" and
         sys.argv[9] == "inspect-predecessor",
         "SIGNED_READ_ONLY_PREDECESSOR_COMMAND_REQUIRED")
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "ROOT_FREEBSD_AMD64_REQUIRED")
    _, _, expected_commit, _, key_sha, public_key, claims_path, sig_path, \
        filename, _, incoming, incoming_version, predecessor, predecessor_version = sys.argv
    need(COMMIT.fullmatch(expected_commit) is not None,
         "INDEPENDENT_SOURCE_COMMIT_REQUIRED")
    value = signed_claims(public_key, key_sha, claims_path, sig_path)
    need(value["source_commit"] == expected_commit,
         "SIGNED_PROVENANCE_SOURCE_COMMIT_NOT_APPROVED")
    need(value["incoming_version"] == incoming_version and
         value["predecessor_version"] == predecessor_version and
         os.path.basename(incoming) == NAME + "-" + incoming_version + ".pkg" and
         os.path.basename(predecessor) == NAME + "-" + predecessor_version + ".pkg" and
         os.path.basename(filename) == "native-prepkg-standalone.py",
         "SIGNED_PROVENANCE_INTENDED_TARGET_MISMATCH")
    verified = verify_source_bytes(filename, value["entrypoint_sha256"])
    try:
        executable = compile(verified, filename, "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError):
        refuse("EXTERNAL_SOURCE_NOT_VALID_PYTHON")
    sys.argv = [filename, "inspect-predecessor", incoming, incoming_version,
                value["incoming_sha256"], predecessor, predecessor_version,
                value["predecessor_sha256"]]
    sys.dont_write_bytecode = True
    print(PREFIX + "VERIFIED_SIGNED_SHA256:" + value["entrypoint_sha256"],
          file=sys.stderr, flush=True)
    exec(executable, {"__name__": "__main__", "__file__": filename,
                      "__package__": None, "__builtins__": __builtins__})


try:
    main()
except (OSError, UnicodeError, ValueError, TypeError) as err:
    refuse("EXTERNAL_SOURCE_VERIFY_UNAVAILABLE:" + type(err).__name__)
