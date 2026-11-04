#!/usr/bin/env python3
"""Stage 3.26 CI-only read-only signed ledger high-watermark witness.

An independently delivered expected checkpoint SHA and independently approved
witness key fingerprint are REQUIRED for real rollback resistance. Here both
are test inputs generated on the same disposable VM: this is NOT an external
witness, production anti-rollback approval, or an updater. It never mutates
the ledger or the installed appliance and never executes pkg.
"""
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage3_ci_local_ledger", HERE / "stage3-prepkg-approval-ledger.py")
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

PREFIX = "ZAPRET2_STAGE3_CHECKPOINT_WITNESS="
SCHEMA = "zapret2-prepkg-external-ledger-checkpoint-v1"
FIELDS = frozenset(("schema", "repository", "sequence", "head_sha256",
                    "authority_sha256", "policy_sha256", "receipt_sha256"))
SHA = re.compile(r"[0-9a-f]{64}\Z")
PUBLIC = "checkpoint-witness-public.pem"
CHECKPOINT = "ledger-checkpoint.json"
SIGNATURE = "ledger-checkpoint.sig"
MAX_WITNESS_BYTES = 8192


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def digest_valid(value):
    return (isinstance(value, str) and SHA.fullmatch(value) is not None
            and value != "0" * 64)


def private_input(path, basename):
    need(isinstance(path, str) and os.path.isabs(path) and
         path.startswith("/root/") and os.path.normpath(path) == path and
         os.path.basename(path) == basename and "\x00" not in path,
         "WITNESS_PRIVATE_INPUT_PATH_REQUIRED")
    parent = os.path.dirname(path)
    current = parent
    while True:
        st = os.lstat(current)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             (stat.S_IMODE(st.st_mode) & 0o022) == 0,
             "WITNESS_UNTRUSTED_PARENT")
        if current == parent:
            need(stat.S_IMODE(st.st_mode) == 0o700,
                 "WITNESS_PRIVATE_PARENT_0700_REQUIRED")
        if current == "/root":
            break
        next_dir = os.path.dirname(current)
        need(next_dir != current, "WITNESS_PARENT_ESCAPE")
        current = next_dir
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Refusal("WITNESS_FILE_OPEN_REFUSED") from None
    try:
        original = os.fstat(fd)
        named = os.lstat(path)
        for item in (original, named):
            need(stat.S_ISREG(item.st_mode) and item.st_uid == 0 and
                 stat.S_IMODE(item.st_mode) == 0o600 and item.st_nlink == 1 and
                 0 < item.st_size <= MAX_WITNESS_BYTES,
                 "WITNESS_PRIVATE_REGULAR_SINGLE_LINK_REQUIRED")
        need((original.st_dev, original.st_ino) ==
             (named.st_dev, named.st_ino), "WITNESS_FILE_INODE_CHANGED")
        raw = bytearray()
        while True:
            block = os.read(fd, 4096)
            if not block:
                break
            raw.extend(block)
            need(len(raw) <= MAX_WITNESS_BYTES, "WITNESS_FILE_OVERSIZE")
        after = os.fstat(fd)
        named_after = os.lstat(path)
        need((original.st_dev, original.st_ino, original.st_size,
              original.st_mtime_ns, original.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size,
              after.st_mtime_ns, after.st_ctime_ns) and
             (after.st_dev, after.st_ino) ==
             (named_after.st_dev, named_after.st_ino) and
             len(raw) == original.st_size,
             "WITNESS_FILE_CHANGED_DURING_READ")
        return bytes(raw)
    finally:
        os.close(fd)


def verify_signature(payload, pubkey, signature):
    # OpenSSL sees copies of the captured stable bytes, never caller paths.
    with tempfile.TemporaryDirectory(prefix="zapret2-ci-witness-",
                                     dir="/root") as folder:
        def freeze(name, raw):
            path = os.path.join(folder, name)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            return path
        key = freeze("pinned-witness.pem", pubkey)
        sig = freeze("signed-checkpoint.sig", signature)
        try:
            completed = subprocess.run(
                ["/usr/bin/openssl", "dgst", "-sha256", "-verify", key,
                 "-signature", sig], input=payload, capture_output=True,
                timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            raise Refusal("WITNESS_OPENSSL_UNAVAILABLE") from None
        need(completed.returncode == 0 and
             completed.stdout.strip() == b"Verified OK",
             "WITNESS_CHECKPOINT_RSA_SIGNATURE_INVALID")


def verify(directory, public_sha, public_path, expected_sha,
           checkpoint_path, signature_path):
    ledger.qualify_runtime()  # The SAME four disposable-only opt-ins.
    need(digest_valid(public_sha), "WITNESS_OUT_OF_BAND_KEY_SHA_REQUIRED")
    need(digest_valid(expected_sha),
         "WITNESS_OUT_OF_BAND_LATEST_CHECKPOINT_SHA_REQUIRED")
    pub = private_input(public_path, PUBLIC)
    need(hmac.compare_digest(hashlib.sha256(pub).hexdigest(), public_sha),
         "WITNESS_PUBLIC_KEY_SHA_MISMATCH")
    snapshot = private_input(checkpoint_path, CHECKPOINT)
    need(hmac.compare_digest(hashlib.sha256(snapshot).hexdigest(),
                             expected_sha),
         "WITNESS_LATEST_CHECKPOINT_SHA_MISMATCH")
    signed = private_input(signature_path, SIGNATURE)
    verify_signature(snapshot, pub, signed)

    try:
        item = ledger.strict_json(snapshot)
    except ledger.Refusal as exc:
        raise Refusal("WITNESS_CHECKPOINT_" + str(exc)) from None
    need(isinstance(item, dict) and set(item) == FIELDS and
         item["schema"] == SCHEMA and item["repository"] == ledger.REPO,
         "WITNESS_CHECKPOINT_SCHEMA_OR_REPOSITORY")
    need(type(item["sequence"]) is int and
         1 <= item["sequence"] <= ledger.MAX_ENTRIES,
         "WITNESS_SEQUENCE_NOT_POSITIVE_INTEGER")
    for name in ("head_sha256", "authority_sha256", "policy_sha256",
                 "receipt_sha256"):
        need(digest_valid(item[name]),
             "WITNESS_CHECKPOINT_BAD_DIGEST:" + name)
    # All state qualification happens UNDER the same real local flock that
    # serializes _115 writers. The witness does not consume an authorization.
    with ledger.private_root(directory) as fd, ledger.lock_ledger(fd):
        history, last = ledger.entries_locked(fd)
        need(history and item["sequence"] == len(history) and
             hmac.compare_digest(item["head_sha256"], last),
             "WITNESS_LEDGER_SEQUENCE_OR_HEAD_ROLLBACK")
        record = history[-1][0]
        for name in ("authority_sha256", "policy_sha256", "receipt_sha256"):
            need(hmac.compare_digest(item[name], record[name]),
                 "WITNESS_LEDGER_LAST_ENTRY_IDENTITY_MISMATCH:" + name)
    return {"status": "PASS_CI_LOCAL_SIGNED_CHECKPOINT_MATCH_ONLY",
            "checkpoint_sequence": item["sequence"],
            "checkpoint_sha256": hashlib.sha256(snapshot).hexdigest(),
            "ledger_head_sha256": item["head_sha256"],
            "signature_verified": True,
            "checkpoint_out_of_band_latest_authenticated": False,
            "witness_signer_owner_approved": False,
            "witness_external_independent_storage": False,
            "root_rollback_resistance_proven": False,
            "production_one_use_pkg_gate": False,
            "pkg_invoked": False}


def main(args):
    try:
        need(len(args) == 7 and args[0] == "verify",
             "WITNESS_EXACT_READ_ONLY_COMMAND_REQUIRED")
        result = verify(*args[1:])
    except (Refusal, ledger.Refusal, OSError, ValueError, TypeError,
            UnicodeError) as exc:
        print(PREFIX + "REFUSED:" + str(exc), file=sys.stderr)
        return 78
    print(PREFIX + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
