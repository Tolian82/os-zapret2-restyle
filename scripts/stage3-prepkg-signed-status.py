#!/usr/bin/env python3
"""CI-only verifier for a signed *simulation* of a witness operation status.

No network client, no trusted remote issuer/clock, no persistent nonce cache,
no independent owner trust root, no pkg or production admission. The caller
supplies all expected identities; this code only checks signed byte bindings.
"""
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import sys
import tempfile

PREFIX = "ZAPRET2_STAGE3_SIGNED_STATUS="
SCHEMA = "zapret2-ci-signed-operation-status-v1"
REPO = "Tolian82/os-zapret2-restyle"
SHA = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset(("schema", "repository", "issuer", "operation_id",
                    "payload_sha256", "checkpoint_sha256", "checkpoint_sequence",
                    "witness_sequence", "challenge_sha256", "action",
                    "issued_at", "expires_at"))
ACTIONS = frozenset(("RESERVED", "CONSUMED", "ABORTED"))
MAX_RESPONSE = 4096
MAX_KEY = 8192
MAX_SIG = 1024
MAX_TTL = 120


class Refusal(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def digest(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None and value != "0" * 64


def strict_json(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise Refusal("STATUS_DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              Refusal("STATUS_NONFINITE_JSON_NUMBER")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Refusal("STATUS_INVALID_JSON:" + type(exc).__name__) from None


def signature_ok(raw, public_key, signature):
    # Signatures cover captured EXACT raw JSON bytes, not re-serialized fields.
    with tempfile.TemporaryDirectory(prefix="zapret2-ci-status-") as root:
        def put(name, value):
            path = os.path.join(root, name)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                while value:
                    count = os.write(fd, value)
                    need(count > 0, "STATUS_TEMP_WRITE_FAILED")
                    value = value[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
            return path
        key = put("witness.pem", public_key)
        sig = put("response.sig", signature)
        try:
            result = subprocess.run(
                ["/usr/bin/openssl", "dgst", "-sha256", "-verify", key,
                 "-signature", sig], input=raw, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=10)
        except (OSError, subprocess.SubprocessError):
            raise Refusal("STATUS_OPENSSL_UNAVAILABLE") from None
        need(result.returncode == 0 and result.stdout.strip() == b"Verified OK",
             "STATUS_RSA_SIGNATURE_INVALID")


def verify_response(raw, signature, public_key, expected_key_sha,
                    challenge, operation_id, payload_sha, checkpoint_sha,
                    checkpoint_sequence, witness_sequence, now):
    for field, value in (("key", expected_key_sha), ("challenge", challenge),
                         ("operation", operation_id), ("payload", payload_sha),
                         ("checkpoint", checkpoint_sha)):
        need(digest(value), "STATUS_EXPECTED_DIGEST_INVALID:" + field)
    need(type(checkpoint_sequence) is int and checkpoint_sequence > 0 and
         type(witness_sequence) is int and witness_sequence >= checkpoint_sequence and
         type(now) is int and now > 0, "STATUS_EXPECTATION_INVALID")
    need(isinstance(raw, bytes) and 0 < len(raw) <= MAX_RESPONSE and
         isinstance(signature, bytes) and 0 < len(signature) <= MAX_SIG and
         isinstance(public_key, bytes) and 0 < len(public_key) <= MAX_KEY,
         "STATUS_INPUT_SIZE_INVALID")
    need(hmac.compare_digest(hashlib.sha256(public_key).hexdigest(), expected_key_sha),
         "STATUS_WITNESS_KEY_FINGERPRINT_MISMATCH")
    signature_ok(raw, public_key, signature)
    value = strict_json(raw)
    need(isinstance(value, dict) and set(value) == FIELDS and
         value["schema"] == SCHEMA and value["repository"] == REPO and
         value["issuer"] == "CI_SIMULATED_WITNESS_NOT_OWNER_APPROVED" and
         isinstance(value["action"], str) and value["action"] in ACTIONS,
         "STATUS_SCHEMA_OR_ISSUER_INVALID")
    for field, expected in (("challenge_sha256", challenge),
                            ("operation_id", operation_id),
                            ("payload_sha256", payload_sha),
                            ("checkpoint_sha256", checkpoint_sha)):
        need(digest(value[field]) and hmac.compare_digest(value[field], expected),
             "STATUS_REQUEST_BINDING_MISMATCH:" + field)
    need(type(value["checkpoint_sequence"]) is int and
         value["checkpoint_sequence"] == checkpoint_sequence and
         type(value["witness_sequence"]) is int and
         value["witness_sequence"] == witness_sequence,
         "STATUS_WITNESS_SEQUENCE_MISMATCH")
    start, end = value["issued_at"], value["expires_at"]
    need(type(start) is int and type(end) is int and start > 0 and
         start < end <= start + MAX_TTL and start <= now <= end,
         "STATUS_EXPIRED_FUTURE_OR_INVALID_WINDOW")
    return {"status": "PASS_CI_SIGNED_RESPONSE_BINDING_ONLY",
            "operation_action": value["action"],
            "challenge_bound": True, "signature_verified": True,
            "witness_key_owner_approved": False,
            "independent_remote_witness_deployed": False,
            "nonce_one_use_proven": False,
            "trusted_clock_proven": False,
            "witness_latest_external_authoritative": False,
            "cross_store_pkg_atomicity_proven": False,
            "production_pkg_authorized": False, "pkg_invoked": False}


def private_read(path, maximum):
    need(isinstance(path, str) and os.path.isabs(path) and
         os.path.normpath(path) == path and "\x00" not in path,
         "STATUS_ABSOLUTE_FILE_REQUIRED")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
             st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o600 and
             0 < st.st_size <= maximum, "STATUS_PRIVATE_FILE_INVALID")
        chunks, count = [], 0
        while True:
            part = os.read(fd, min(4096, maximum - count + 1))
            if not part:
                break
            chunks.append(part)
            count += len(part)
            need(count <= maximum, "STATUS_FILE_TOO_LARGE")
        after = os.fstat(fd)
        need(count == st.st_size and (st.st_dev, st.st_ino, st.st_size,
             st.st_mtime_ns, st.st_ctime_ns) == (after.st_dev, after.st_ino,
             after.st_size, after.st_mtime_ns, after.st_ctime_ns),
             "STATUS_FILE_CHANGED_DURING_READ")
        return b"".join(chunks)
    finally:
        os.close(fd)


def main(args):
    try:
        need(os.environ.get("ZAPRET2_CI_SIGNED_STATUS_ONLY") == "1",
             "STATUS_DISPOSABLE_CI_OPT_IN_REQUIRED")
        need(len(args) == 12 and args[0] == "verify", "STATUS_EXACT_CLI_REQUIRED")
        _, keysha, challenge, op, payload, cp, cp_seq, witness_seq, now, key, response, sig = args  # noqa: E501
        outcome = verify_response(private_read(response, MAX_RESPONSE),
                                  private_read(sig, MAX_SIG),
                                  private_read(key, MAX_KEY), keysha,
                                  challenge, op, payload, cp,
                                  int(cp_seq), int(witness_seq), int(now))
        print(PREFIX + json.dumps(outcome, sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, TypeError) as exc:
        print(PREFIX + "REFUSED:" + str(exc), file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
