# Reviewed operator-side Python -I -B -c seed, NOT automatically trusted by
# being downloaded or checked into this repository. Its bytes must first be
# independently authenticated; a human-recorded receipt is NOT an issuer key.
# Only a read-only, signed-provenance predecessor inspection is supported.
import hashlib
import hmac
import json
import os
import re
import subprocess
import tempfile
import stat
import sys
import time

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
MAX_AUTHORITY_FILE = 8192
AUTHORITY_BASENAME = "operator-approval-authority.pem"
SIGNATURE_BASENAME = "operator-pins.sig"
POLICY_BASENAME = "operator-approval-policy.json"
POLICY_SIGNATURE_BASENAME = "operator-approval-policy.sig"
POLICY_SCHEMA = "zapret2-prepkg-approval-policy-v1"
POLICY_FIELDS = frozenset(("schema", "repository", "authority_sha256",
    "receipt_sha256", "sequence", "issued_at", "not_before", "not_after",
    "revoked_receipt_sha256", "revoked_authority_sha256"))
MAX_POLICY_AGE = 3600
MAX_REVOKED = 32


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




def authority_file(path, exact_name):
    # Dedicated trust role. Never read this digest from the incoming pkg or
    # from the unsigned (and potentially edited) manual receipt itself.
    need(isinstance(path, str) and path.startswith("/root/") and
         os.path.isabs(path) and os.path.normpath(path) == path and
         os.path.basename(path) == exact_name and "\x00" not in path,
         "OPERATOR_AUTHORITY_PATH_NOT_PRIVATE")
    parent = os.path.dirname(path)
    leaf = parent
    while True:
        st = os.lstat(leaf)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             not stat.S_IMODE(st.st_mode) & 0o022,
             "OPERATOR_AUTHORITY_PARENT_UNTRUSTED")
        if leaf == parent:
            need(stat.S_IMODE(st.st_mode) == 0o700,
                 "OPERATOR_AUTHORITY_PARENT_0700_REQUIRED")
        if leaf == "/root":
            break
        leaf = os.path.dirname(leaf)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        refuse("OPERATOR_AUTHORITY_OPEN_REFUSED")
    try:
        before = os.fstat(fd)
        named = os.lstat(path)
        for st in (before, named):
            need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
                 st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and
                 0 < st.st_size <= MAX_AUTHORITY_FILE,
                 "OPERATOR_AUTHORITY_PRIVATE_REGULAR_REQUIRED")
        need((before.st_dev, before.st_ino) ==
             (named.st_dev, named.st_ino),
             "OPERATOR_AUTHORITY_INODE_MISMATCH")
        raw = bytearray()
        while True:
            block = os.read(fd, MAX_AUTHORITY_FILE)
            if not block:
                break
            raw.extend(block)
            need(len(raw) <= MAX_AUTHORITY_FILE,
                 "OPERATOR_AUTHORITY_FILE_OVERSIZE")
        after = os.fstat(fd)
        named_after = os.lstat(path)
        need((before.st_dev, before.st_ino, before.st_size,
              before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size,
              after.st_mtime_ns, after.st_ctime_ns) and
             (after.st_dev, after.st_ino) ==
             (named_after.st_dev, named_after.st_ino) and
             len(raw) == before.st_size,
             "OPERATOR_AUTHORITY_CHANGED_DURING_READ")
        return bytes(raw)
    finally:
        os.close(fd)


def verify_detached_receipt(receipt_bytes, anchor_sha, authority_path,
                            signature_path, signature_basename=SIGNATURE_BASENAME):
    need(isinstance(anchor_sha, str) and SHA.fullmatch(anchor_sha) is not None
         and anchor_sha != "0" * 64,
         "OUT_OF_BAND_OPERATOR_AUTHORITY_SHA_REQUIRED")
    key = authority_file(authority_path, AUTHORITY_BASENAME)
    need(hmac.compare_digest(hashlib.sha256(key).hexdigest(), anchor_sha),
         "OPERATOR_AUTHORITY_NOT_INDEPENDENTLY_PINNED")
    signature = authority_file(signature_path, signature_basename)
    # Do not point OpenSSL at untrusted mutable input paths: the bytes have
    # already been captured from stable opened private FDs.
    with tempfile.TemporaryDirectory(prefix="zapret2-operator-approval-",
                                     dir="/root") as private_dir:
        def frozen(filename, payload):
            path = os.path.join(private_dir, filename)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            return path
        public = frozen("operator-authority.pem", key)
        signed = frozen("operator-approval.sig", signature)
        try:
            result = subprocess.run(
                ["/usr/bin/openssl", "dgst", "-sha256", "-verify", public,
                 "-signature", signed], input=bytes(receipt_bytes),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            refuse("OPERATOR_APPROVAL_CRYPTO_UNAVAILABLE")
        need(result.returncode == 0 and
             result.stdout.strip() == b"Verified OK",
             "OPERATOR_RECEIPT_SIGNATURE_INVALID")
    return True



def verified_approval_policy(receipt_bytes, authority_sha, authority_key,
                             expected_policy_sha, policy_path, policy_signature):
    # This is a *bounded read-only gate*, not durable one-use consumption.
    # A caller-chosen expected SHA, local wall clock or replayable snapshot
    # is never by itself an authenticated production authority.
    need(isinstance(expected_policy_sha, str) and
         SHA.fullmatch(expected_policy_sha) is not None and
         expected_policy_sha != "0" * 64,
         "OUT_OF_BAND_POLICY_SHA256_REQUIRED")
    raw = authority_file(policy_path, POLICY_BASENAME)
    need(hmac.compare_digest(hashlib.sha256(raw).hexdigest(),
                             expected_policy_sha),
         "APPROVAL_POLICY_NOT_INDEPENDENTLY_PINNED")
    verify_detached_receipt(raw, authority_sha, authority_key, policy_signature,
                            POLICY_SIGNATURE_BASENAME)

    def unique(pairs):
        result = {}
        for name, value in pairs:
            need(name not in result, "APPROVAL_POLICY_DUPLICATE_KEY")
            result[name] = value
        return result

    try:
        policy = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError):
        refuse("APPROVAL_POLICY_INVALID_JSON")
    need(isinstance(policy, dict) and set(policy) == POLICY_FIELDS and
         policy["schema"] == POLICY_SCHEMA and
         policy["repository"] == REPO and
         isinstance(policy["authority_sha256"], str) and
         policy["authority_sha256"] == authority_sha and
         isinstance(policy["receipt_sha256"], str) and
         policy["receipt_sha256"] ==
             hashlib.sha256(bytes(receipt_bytes)).hexdigest(),
         "APPROVAL_POLICY_WRONG_IDENTITY_OR_RECEIPT")
    for name in ("sequence", "issued_at", "not_before", "not_after"):
        need(type(policy[name]) is int and 0 <= policy[name] < 2 ** 63,
             "APPROVAL_POLICY_NONINTEGER:" + name)
    need(policy["sequence"] > 0 and
         policy["not_before"] <= policy["issued_at"] <= policy["not_after"] and
         0 < policy["not_after"] - policy["not_before"] <= MAX_POLICY_AGE,
         "APPROVAL_POLICY_UNBOUNDED_OR_INVALID_WINDOW")
    now = int(time.time())
    need(policy["not_before"] <= now <= policy["not_after"] and
         policy["issued_at"] <= now,
         "APPROVAL_POLICY_NOT_CURRENT")
    for name in ("revoked_receipt_sha256", "revoked_authority_sha256"):
        data = policy[name]
        need(isinstance(data, list) and len(data) <= MAX_REVOKED and
             all(isinstance(v, str) and SHA.fullmatch(v) is not None
                 for v in data) and len(set(data)) == len(data),
             "APPROVAL_POLICY_BAD_REVOKE_LIST:" + name)
    need(hashlib.sha256(bytes(receipt_bytes)).hexdigest() not in
         policy["revoked_receipt_sha256"],
         "OPERATOR_RECEIPT_REVOKED_IN_POLICY")
    need(authority_sha not in policy["revoked_authority_sha256"],
         "OPERATOR_APPROVAL_AUTHORITY_REVOKED_IN_POLICY")
    return policy


def operator_receipt(path, authority_sha, authority_key, signature_path,
                     policy_sha, policy_path, policy_signature):
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

    # Detached signature is over these EXACT stable bytes, never a re-encoded
    # or caller-selected JSON. A valid signature is necessary but insufficient:
    # the out-of-band anchor must itself be owner-authenticated separately.
    verify_detached_receipt(raw, authority_sha, authority_key, signature_path)
    verified_approval_policy(raw, authority_sha, authority_key, policy_sha,
                             policy_path, policy_signature)

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
    need(len(sys.argv) == 23 and sys.argv[1] == "--operator-receipt" and
         sys.argv[3] == "--operator-authority" and
         sys.argv[7] == "--approval-policy" and
         sys.argv[11] == "--verified-verifier" and
         sys.argv[13] == "--signed-provenance" and
         sys.argv[18] == "inspect-predecessor",
         "SIGNED_READ_ONLY_VERIFIER_COMMAND_REQUIRED")
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "ROOT_FREEBSD_AMD64_REQUIRED")
    pins = operator_receipt(sys.argv[2], sys.argv[4], sys.argv[5], sys.argv[6],
                            sys.argv[8], sys.argv[9], sys.argv[10])
    need(not hmac.compare_digest(sys.argv[4], pins["public_key_sha256"]),
         "RECEIPT_APPROVAL_AND_PACKAGE_SIGNER_MUST_DIFFER")
    need(sys.argv[20] == pins["incoming_version"] and
         sys.argv[22] == pins["predecessor_version"] and
         os.path.basename(sys.argv[19]) ==
             "os-zapret2-restyle-" + pins["incoming_version"] + ".pkg" and
         os.path.basename(sys.argv[21]) ==
             "os-zapret2-restyle-" + pins["predecessor_version"] + ".pkg",
         "OPERATOR_RECEIPT_TARGET_NOT_MATCHED")
    path, digest = sys.argv[12], pins["verifier_sha256"]
    frozen = verified_verifier(path, digest)
    try:
        compiled = compile(frozen, path, "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError):
        refuse("VERIFIER_INVALID_PYTHON")
    # No digest/commit values supplied by command-line caller are forwarded.
    sys.argv = ["-c", "--expected-source-commit", pins["source_commit"],
                "--expected-archive-pins", pins["incoming_sha256"],
                pins["predecessor_sha256"], "--signed-provenance",
                pins["public_key_sha256"]] + sys.argv[14:]
    sys.dont_write_bytecode = True
    print(PREFIX + "VERIFIED_SHA256:" + digest, file=sys.stderr, flush=True)
    print(PREFIX + "RECEIPT_RSA_VERIFIED_ANCHOR_NOT_OWNER_AUTHENTICATED",
          file=sys.stderr, flush=True)
    print(PREFIX + "SIGNED_POLICY_TIME_AND_REVOCATION_MATCHED_NOT_ONE_USE",
          file=sys.stderr, flush=True)
    print(PREFIX + "RECEIPT_PINS_BOUND_NOT_AUTHENTICATED",
          file=sys.stderr, flush=True)
    exec(compiled, {"__name__": "__main__", "__file__": path,
                    "__package__": None, "__builtins__": __builtins__})


try:
    main()
except (OSError, ValueError, TypeError, UnicodeError) as exc:
    refuse("VERIFIER_VERIFY_UNAVAILABLE:" + type(exc).__name__)
