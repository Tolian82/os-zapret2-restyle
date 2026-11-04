#!/usr/bin/env python3
"""Manual, source-only operator pin receipt. Never an authority for pkg mutation.

This script ITSELF must be obtained/authenticated outside the incoming package
before root executes it. An interactive receipt proves only input mechanics,
not publication identity, signer authorization or a protected update gateway.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

PREFIX = "ZAPRET2_OPERATOR_APPROVAL="
SCHEMA = "zapret2-prepkg-operator-pins-v1"
REPOSITORY = "Tolian82/os-zapret2-restyle"
NAME = "os-zapret2-restyle"
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
VERSION = re.compile(r"0\.6\.2_[1-9][0-9]*\Z")
PIN_FIELDS = ("seed_sha256", "verifier_sha256", "public_key_sha256",
              "source_commit", "incoming_version", "incoming_sha256",
              "predecessor_version", "predecessor_sha256")
ALL_FIELDS = frozenset((*PIN_FIELDS, "schema", "repository", "trust_status"))
TRUST_STATUS = "PINS_RECORDED_NOT_AUTHENTICATED"
MAX_FILE = 512 * 1024 * 1024
MAX_SOURCE = 256 * 1024
MAX_RECORD = 4096
EXPECTED_BASENAMES = ("stage3-prepkg-trust-seed.py",
                      "stage3-prepkg-verified-eval.py", "approved-public.pem")


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def qualify_runtime():
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "ROOT_FREEBSD_AMD64_REQUIRED")


def validate_pins(values):
    need(isinstance(values, dict) and set(values) == set(PIN_FIELDS),
         "EXACT_EIGHT_OPERATOR_PINS_REQUIRED")
    for field in ("seed_sha256", "verifier_sha256", "public_key_sha256",
                  "incoming_sha256", "predecessor_sha256"):
        value = values[field]
        need(isinstance(value, str) and SHA.fullmatch(value) is not None and
             value != "0" * 64, "INVALID_OPERATOR_DIGEST:" + field)
    need(isinstance(values["source_commit"], str) and
         COMMIT.fullmatch(values["source_commit"]) is not None and
         values["source_commit"] != "0" * 40,
         "INVALID_OPERATOR_SOURCE_COMMIT")
    for name in ("incoming_version", "predecessor_version"):
        value = values[name]
        need(isinstance(value, str) and VERSION.fullmatch(value) is not None,
             "INVALID_OPERATOR_PACKAGE_VERSION:" + name)
    need(values["incoming_version"] != values["predecessor_version"],
         "SAME_INCOMING_AND_PREDECESSOR_REFUSED")
    return dict(values)


def private_path(path, expected_name):
    need(isinstance(path, str) and path.startswith("/root/") and
         os.path.isabs(path) and os.path.normpath(path) == path and
         os.path.basename(path) == expected_name and "\x00" not in path,
         "PRIVATE_PATH_OR_BASENAME_REQUIRED")
    parent = os.path.dirname(path)
    leaf = parent
    while True:
        st = os.lstat(leaf)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
             not stat.S_IMODE(st.st_mode) & 0o022,
             "PRIVATE_ANCESTOR_UNTRUSTED")
        if leaf == "/root":
            break
        next_leaf = os.path.dirname(leaf)
        need(next_leaf != leaf, "PRIVATE_ANCESTOR_ESCAPE")
        leaf = next_leaf
    st = os.lstat(parent)
    need(stat.S_IMODE(st.st_mode) == 0o700,
         "OPERATOR_PRIVATE_DIRECTORY_0700_REQUIRED")
    return parent


def private_bytes(path, expected_name, limit):
    private_path(path, expected_name)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Refusal("OPERATOR_PRIVATE_SOURCE_OPEN_REFUSED") from None
    try:
        original = os.fstat(fd)
        named = os.lstat(path)
        for st in (original, named):
            need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
                 st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and
                 0 < st.st_size <= limit,
                 "OPERATOR_PRIVATE_SOURCE_MODE_OR_SIZE_REFUSED")
        need((original.st_dev, original.st_ino) ==
             (named.st_dev, named.st_ino), "OPERATOR_PRIVATE_INODE_CHANGED")
        digest = hashlib.sha256()
        raw = bytearray() if limit <= MAX_SOURCE else None
        size = 0
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            size += len(block)
            need(size <= limit, "OPERATOR_SOURCE_LIMIT_EXCEEDED")
            digest.update(block)
            if raw is not None:
                raw.extend(block)
        after = os.fstat(fd)
        current = os.lstat(path)
        need((original.st_dev, original.st_ino, original.st_size,
              original.st_mtime_ns, original.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size,
              after.st_mtime_ns, after.st_ctime_ns) and
             (after.st_dev, after.st_ino) ==
             (current.st_dev, current.st_ino) and size == original.st_size,
             "OPERATOR_SOURCE_CHANGED_DURING_HASH")
        return digest.hexdigest(), bytes(raw) if raw is not None else None
    finally:
        os.close(fd)


def decode_receipt(payload):
    def no_duplicates(items):
        value = {}
        for k, v in items:
            need(k not in value, "DUPLICATE_OPERATOR_RECEIPT_KEY")
            value[k] = v
        return value
    try:
        record = json.loads(payload.decode("utf-8"),
                            object_pairs_hook=no_duplicates)
    except (UnicodeError, ValueError, TypeError):
        raise Refusal("INVALID_OPERATOR_RECEIPT_JSON") from None
    need(isinstance(record, dict) and set(record) == ALL_FIELDS and
         record["schema"] == SCHEMA and
         record["repository"] == REPOSITORY and
         record["trust_status"] == TRUST_STATUS,
         "OPERATOR_RECEIPT_SCHEMA_OR_STATUS_INVALID")
    return validate_pins({name: record[name] for name in PIN_FIELDS})


def record_receipt(path, prompt=input):
    qualify_runtime()
    need(sys.stdin.isatty() and sys.stdout.isatty(),
         "REAL_INTERACTIVE_OPERATOR_TTY_REQUIRED")
    parent = private_path(path, "operator-pins.json")
    values = {}
    for name in PIN_FIELDS:
        values[name] = prompt(name + " [independently reviewed]: ").strip()
    values = validate_pins(values)
    confirmation = "APPROVE " + values["source_commit"] + " " + values["incoming_version"]
    need(prompt("Type exactly '" + confirmation + "' to record only: ") ==
         confirmation, "EXPLICIT_OPERATOR_CONFIRMATION_REQUIRED")
    record = dict(values, schema=SCHEMA, repository=REPOSITORY,
                  trust_status=TRUST_STATUS)
    raw = (json.dumps(record, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    need(len(raw) < MAX_RECORD, "OPERATOR_RECEIPT_OVERSIZE")
    dirname = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    created = False
    try:
        try:
            fd = os.open("operator-pins.json",
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=dirname)
            created = True
        except OSError:
            raise Refusal("OPERATOR_RECEIPT_EXISTS_OR_UNSAFE") from None
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(dirname)
    except BaseException:
        if fd is not None:
            os.close(fd)
        if created:
            os.unlink("operator-pins.json", dir_fd=dirname)
        raise
    finally:
        os.close(dirname)
    return {"status": "PASS_MANUAL_PINS_RECORDED_ONLY",
            "source_commit": values["source_commit"],
            "incoming_version": values["incoming_version"],
            "operator_source_authenticated": False,
            "signer_authenticated": False, "pkg_authorized": False}


def inspect_receipt(record_path, paths):
    qualify_runtime()
    need(len(paths) == 5, "EXACT_FIVE_PRIVATE_SOURCES_REQUIRED")
    _, data = private_bytes(record_path, "operator-pins.json", MAX_RECORD)
    pins = decode_receipt(data)
    expected_names = (EXPECTED_BASENAMES[0], EXPECTED_BASENAMES[1],
                      EXPECTED_BASENAMES[2],
                      NAME + "-" + pins["incoming_version"] + ".pkg",
                      NAME + "-" + pins["predecessor_version"] + ".pkg")
    digests = ("seed_sha256", "verifier_sha256", "public_key_sha256",
               "incoming_sha256", "predecessor_sha256")
    for path, filename, key in zip(paths, expected_names, digests):
        observed, _ = private_bytes(path, filename,
                                    MAX_FILE if filename.endswith(".pkg")
                                    else MAX_SOURCE)
        need(observed == pins[key], "OPERATOR_PIN_SHA256_MISMATCH:" + key)
    return {"status": "PASS_RECORDED_PINS_AND_PRIVATE_BYTES_ONLY",
            "source_commit": pins["source_commit"],
            "incoming_version": pins["incoming_version"],
            "predecessor_version": pins["predecessor_version"],
            "operator_source_authenticated": False,
            "signer_authenticated": False,
            "signed_manifest_verified": False,
            "old_owner_qualified": False,
            "supported_entrypoint_implemented": False,
            "pkg_invoked": False, "pkg_authorized": False,
            "lh08_ac11_accepted": False}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 2 and args[0] == "record":
            outcome = record_receipt(args[1])
        elif len(args) == 7 and args[0] == "inspect":
            outcome = inspect_receipt(args[1], args[2:])
        else:
            raise Refusal("READ_ONLY_RECORD_OR_INSPECT_ONLY")
        print(PREFIX + json.dumps(outcome, sort_keys=True))
        return 0
    except (Refusal, OSError, TypeError, ValueError, UnicodeError) as error:
        print(PREFIX + "REFUSED:" + str(error), file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main())
