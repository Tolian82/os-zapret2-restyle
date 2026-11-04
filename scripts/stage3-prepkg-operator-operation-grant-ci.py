#!/usr/bin/env python3
"""CI-only signed operator *scope* check before the witness SQLite transition.

Not an owner-approved authorization. CI creates both operator keys and its
claimed trust fingerprint; the same runner still controls the signer/DB/clock.
This module cannot call pkg, mutate firewall state, or deploy a remote witness.
"""
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import time

REPO = "Tolian82/os-zapret2-restyle"
SCHEMA = "zapret2-ci-operator-operation-grant-v1"
ISSUER = "CI_EPHEMERAL_OPERATOR_NOT_OWNER_APPROVED"
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
FIELDS = frozenset(("schema", "repository", "issuer", "sequence",
                    "operator_authority_sha256", "status_signer_sha256",
                    "client_leaf_sha256", "source_commit",
                    "old_pkg_sha256", "new_pkg_sha256",
                    "old_pkg_version", "new_pkg_version",
                    "not_before", "not_after", "actions", "entries"))
ENTRY = frozenset(("operation_id", "payload_sha256", "checkpoint_sha256",
                   "checkpoint_sequence"))
ACTIONS = ("RESERVE", "CONSUME", "ABORT", "STATUS")
MAX_BYTES = 8192
MAX_PEM = 8192
MAX_SIG = 1024
MAX_ENTRIES = 8
MAX_TTL = 3600
MAX_PKG = 128 * 1024 * 1024
PKG_NAME = "os-zapret2-restyle"
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+_[1-9][0-9]*\Z")


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None and value != "0" * 64


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "GRANT_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _:
                          (_ for _ in ()).throw(Refusal("GRANT_NONFINITE_JSON")))
    except (UnicodeError, ValueError, TypeError):
        raise Refusal("GRANT_INVALID_JSON") from None


def private_bytes(path, limit):
    need(isinstance(path, str) and os.path.isabs(path) and
         os.path.normpath(path) == path and "\x00" not in path,
         "GRANT_PRIVATE_ABSOLUTE_PATH_REQUIRED")
    opened = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        first = os.fstat(opened)
        need(stat.S_ISREG(first.st_mode) and first.st_uid == os.getuid() and
             first.st_nlink == 1 and stat.S_IMODE(first.st_mode) == 0o600 and
             0 < first.st_size <= limit, "GRANT_PRIVATE_FILE_UNSAFE")
        chunks, length = [], 0
        while True:
            part = os.read(opened, min(4096, limit - length + 1))
            if not part:
                break
            length += len(part)
            need(length <= limit, "GRANT_PRIVATE_OVERSIZE")
            chunks.append(part)
        last = os.fstat(opened)
        need(length == first.st_size and
             (first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns,
              first.st_ctime_ns) ==
             (last.st_dev, last.st_ino, last.st_size, last.st_mtime_ns,
              last.st_ctime_ns), "GRANT_PRIVATE_FILE_CHANGED")
        return b"".join(chunks)
    finally:
        os.close(opened)


def verify_signature(raw, signature, public_pem):
    # Sign the ORIGINAL grant bytes; do not reserialize JSON.
    # On FreeBSD and Ubuntu CI, OpenSSL reads frozen data from stdin.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="zapret2-ci-operator-") as td:
        for label, data in (("authority.pem", public_pem),
                            ("operator.sig", signature)):
            filename = os.path.join(td, label)
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW, 0o600)
            try:
                while data:
                    count = os.write(fd, data)
                    need(count > 0, "GRANT_PRIVATE_WRITE_FAILED")
                    data = data[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
        try:
            result = subprocess.run(
                ["/usr/bin/openssl", "dgst", "-sha256", "-verify",
                 os.path.join(td, "authority.pem"), "-signature",
                 os.path.join(td, "operator.sig")],
                input=raw, capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            raise Refusal("GRANT_OPENSSL_UNAVAILABLE") from None
        need(result.returncode == 0 and
             result.stdout.strip() == b"Verified OK",
             "GRANT_OPERATOR_SIGNATURE_INVALID")


def signer_sha(private_key_file):
    try:
        result = subprocess.run(
            ["/usr/bin/openssl", "pkey", "-in", private_key_file, "-pubout"],
            capture_output=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("GRANT_STATUS_SIGNER_UNAVAILABLE") from None
    need(result.returncode == 0 and result.stdout.startswith(b"-----BEGIN PUBLIC KEY-----"),
         "GRANT_STATUS_SIGNER_INVALID")
    return hashlib.sha256(result.stdout).hexdigest()


def measured_archive(path, version, digest):
    """Measure actual immutable-looking CI archive bytes, never trust labels alone.

    This is a read-only point-in-time check, NOT a lock against privileged
    replacement or a claim that any package has been installed with pkg.
    """
    need(isinstance(path, str) and os.path.isabs(path) and
         os.path.normpath(path) == path and os.path.realpath(path) == path and
         "\x00" not in path, "GRANT_ARCHIVE_ABSOLUTE_NON_SYMLINK_REQUIRED")
    need(isinstance(version, str) and VERSION.fullmatch(version) is not None and
         os.path.basename(path) == PKG_NAME + "-" + version + ".pkg",
         "GRANT_ARCHIVE_NAME_VERSION_INVALID")
    need(sha(digest), "GRANT_ARCHIVE_SHA_REQUIRED")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_uid == os.getuid() and
             first.st_nlink == 1 and
             (stat.S_IMODE(first.st_mode) & 0o022) == 0 and
             0 < first.st_size <= MAX_PKG, "GRANT_ARCHIVE_FILE_UNSAFE")
        sha256 = hashlib.sha256()
        total = 0
        while True:
            part = os.read(fd, 1024 * 1024)
            if not part:
                break
            total += len(part)
            need(total <= MAX_PKG, "GRANT_ARCHIVE_OVERSIZE")
            sha256.update(part)
        last = os.fstat(fd)
        pathname = os.stat(path, follow_symlinks=False)
        stable = lambda v: (v.st_dev, v.st_ino, v.st_size,
                            v.st_mtime_ns, v.st_ctime_ns, v.st_mode, v.st_nlink)
        need(total == first.st_size and stable(first) == stable(last) ==
             stable(pathname), "GRANT_ARCHIVE_CHANGED_DURING_MEASUREMENT")
        need(hmac.compare_digest(sha256.hexdigest(), digest),
             "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST")
        return total
    finally:
        os.close(fd)


def check_archives(policy):
    need(measured_archive(policy["old_archive"], policy["old_pkg_version"],
                          policy["old_pkg_sha256"]) > 0,
         "GRANT_OLD_ARCHIVE_UNAVAILABLE")
    need(measured_archive(policy["new_archive"], policy["new_pkg_version"],
                          policy["new_pkg_sha256"]) > 0,
         "GRANT_NEW_ARCHIVE_UNAVAILABLE")


def load(grant_path, signature_path, authority_path, expected_authority_sha,
         status_signer_sha, client_leaf_sha, expected_source_commit,
         old_archive, new_archive, now=None):
    need(sha(expected_authority_sha) and sha(status_signer_sha) and
         sha(client_leaf_sha) and type(expected_source_commit) is str and
         COMMIT.fullmatch(expected_source_commit) is not None,
         "GRANT_EXPECTED_TRUST_INPUT_INVALID")
    raw = private_bytes(grant_path, MAX_BYTES)
    sig = private_bytes(signature_path, MAX_SIG)
    key = private_bytes(authority_path, MAX_PEM)
    need(hmac.compare_digest(hashlib.sha256(key).hexdigest(),
                             expected_authority_sha),
         "GRANT_OPERATOR_AUTHORITY_FINGERPRINT_MISMATCH")
    need(not hmac.compare_digest(expected_authority_sha, status_signer_sha),
         "GRANT_OPERATOR_AND_STATUS_SIGNER_MUST_DIFFER")
    verify_signature(raw, sig, key)
    value = strict_json(raw)
    need(isinstance(value, dict) and set(value) == FIELDS and
         value["schema"] == SCHEMA and value["repository"] == REPO and
         value["issuer"] == ISSUER and type(value["sequence"]) is int and
         value["sequence"] > 0, "GRANT_SCHEMA_OR_ISSUER_INVALID")
    for field, expected in (("operator_authority_sha256", expected_authority_sha),
                            ("status_signer_sha256", status_signer_sha),
                            ("client_leaf_sha256", client_leaf_sha)):
        need(sha(value[field]) and hmac.compare_digest(value[field], expected),
             "GRANT_TRUST_ROLE_BINDING_MISMATCH:" + field)
    need(isinstance(value["source_commit"], str) and
         COMMIT.fullmatch(value["source_commit"]) is not None and
         hmac.compare_digest(value["source_commit"], expected_source_commit),
         "GRANT_SOURCE_COMMIT_NOT_EXPECTED")
    need(sha(value["old_pkg_sha256"]) and sha(value["new_pkg_sha256"]) and
         type(value["old_pkg_version"]) is str and
         VERSION.fullmatch(value["old_pkg_version"]) is not None and
         type(value["new_pkg_version"]) is str and
         VERSION.fullmatch(value["new_pkg_version"]) is not None,
         "GRANT_PACKAGE_IDENTITY_INVALID")
    start, end = value["not_before"], value["not_after"]
    need(type(start) is int and type(end) is int and
         0 < start < end <= start + MAX_TTL, "GRANT_VALIDITY_INVALID")
    need(isinstance(value["actions"], list) and value["actions"] and
         all(type(action) is str and action in ACTIONS for action in value["actions"]) and
         value["actions"] == sorted(set(value["actions"]), key=ACTIONS.index),
         "GRANT_ACTION_RIGHTS_INVALID")
    entries = value["entries"]
    need(isinstance(entries, list) and 1 <= len(entries) <= MAX_ENTRIES,
         "GRANT_EXACT_ENTRIES_REQUIRED")
    identities = []
    for item in entries:
        need(isinstance(item, dict) and set(item) == ENTRY and
             type(item["checkpoint_sequence"]) is int and
             1 <= item["checkpoint_sequence"] <= 1000000 and
             all(sha(item[name]) for name in
                 ("operation_id", "payload_sha256", "checkpoint_sha256")),
             "GRANT_ENTRY_IDENTITY_INVALID")
        identities.append((item["operation_id"], item["payload_sha256"],
                           item["checkpoint_sha256"],
                           item["checkpoint_sequence"]))
    need(len(set(identities)) == len(identities), "GRANT_DUPLICATE_ENTRY")
    policy = {"not_before": start, "not_after": end,
              "actions": tuple(value["actions"]),
              "entries": frozenset(identities),
              "sha256": hashlib.sha256(raw).hexdigest(),
              "old_archive": old_archive, "new_archive": new_archive,
              "old_pkg_version": value["old_pkg_version"],
              "new_pkg_version": value["new_pkg_version"],
              "old_pkg_sha256": value["old_pkg_sha256"],
              "new_pkg_sha256": value["new_pkg_sha256"],
              "source_commit": expected_source_commit,
              "operator_authority_owner_approved": False,
              "source_pkg_claims_independently_verified": False}
    check_time(policy, int(time.time()) if now is None else now)
    check_archives(policy)
    return policy


def check_time(policy, now):
    need(type(now) is int and
         policy["not_before"] <= now <= policy["not_after"],
         "GRANT_EXPIRED_OR_NOT_YET_VALID")


def authorize(policy, request, now=None):
    check_time(policy, int(time.time()) if now is None else now)
    need(request["action"] in policy["actions"],
         "GRANT_ACTION_NOT_AUTHORIZED")
    identity = (request["operation_id"], request["payload_sha256"],
                request["checkpoint_sha256"], request["checkpoint_sequence"])
    need(identity in policy["entries"], "GRANT_OPERATION_NOT_AUTHORIZED")
    # Re-measure both archive pathnames for every accepted request before
    # reserving a challenge or changing a witnessed operation in SQLite.
    check_archives(policy)
    # No pkg grant. Return only evidence that the CI-only scope matches.
    return True
