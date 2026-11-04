#!/usr/bin/env python3
"""Disposable CI-only local approval-ledger primitive. NEVER authorizes pkg.

This does not verify the issuer, signed policy freshness, OS trust, or an
owner-approved seed. It accepts test-only caller values AFTER the independent
read-only seed test has succeeded. Its writes are confined to a separate
throwaway private /root subtree; it never touches an installed OPNsense plugin.
A root-capable attacker may delete/replay the entire ledger. Not a gateway.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import re
import stat
import sys

PREFIX = "ZAPRET2_STAGE3_LOCAL_LEDGER="
REPO = "Tolian82/os-zapret2-restyle"
SCHEMA = "zapret2-prepkg-ci-ledger-entry-v1"
LOCK = "ledger.lock"
SHA = re.compile(r"[0-9a-f]{64}\Z")
ENTRY = re.compile(r"spent-([0-9]{12})-([0-9a-f]{64})\.json\Z")
FIELDS = {"schema", "repository", "sequence", "receipt_sha256",
          "policy_sha256", "authority_sha256", "previous_entry_sha256"}
MAX_ENTRIES = 512
MAX_ENTRY_BYTES = 1024
OPTIN = "ZAPRET2_STAGE3_DISPOSABLE_LEDGER"


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def qualify_runtime():
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.environ.get("ZAPRET2_STAGE3_PREPKG_ARCHIVE_BOOTSTRAP") == "1" and
         os.environ.get(OPTIN) == "1",
         "CI_ONLY_DISPOSABLE_FREEBSD_ROOT_REQUIRED")


def root_owner(st):
    return st.st_uid == 0


@contextlib.contextmanager
def private_root(path):
    need(isinstance(path, str) and os.path.isabs(path) and
         path.startswith("/root/") and os.path.normpath(path) == path and
         "\x00" not in path and os.path.basename(path) == "approval-ledger",
         "LEDGER_PRIVATE_CANONICAL_ROOT_REQUIRED")
    current = path
    while True:
        st = os.lstat(current)
        need(stat.S_ISDIR(st.st_mode) and root_owner(st) and
             stat.S_IMODE(st.st_mode) & 0o022 == 0,
             "LEDGER_ANCESTOR_UNTRUSTED")
        if current == path:
            need(stat.S_IMODE(st.st_mode) == 0o700,
                 "LEDGER_DIRECTORY_0700_REQUIRED")
        if current == "/root":
            break
        next_path = os.path.dirname(current)
        need(next_path != current, "LEDGER_ANCESTOR_ESCAPE")
        current = next_path
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.lstat(path)
        need(stat.S_ISDIR(before.st_mode) and root_owner(before) and
             stat.S_IMODE(before.st_mode) == 0o700 and
             (before.st_dev, before.st_ino) == (named.st_dev, named.st_ino),
             "LEDGER_DIRECTORY_INODE_CHANGED")
        yield fd
        after = os.fstat(fd)
        need((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
             "LEDGER_DIRECTORY_REPLACED")
    finally:
        os.close(fd)


def private_file(fd, basename, limit, expected_mode=0o600):
    need(isinstance(basename, str) and "/" not in basename and
         basename not in (".", ".."), "LEDGER_FILE_BASENAME_INVALID")
    file_fd = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                      dir_fd=fd)
    try:
        before = os.fstat(file_fd)
        named = os.stat(basename, dir_fd=fd, follow_symlinks=False)
        for st in (before, named):
            need(stat.S_ISREG(st.st_mode) and root_owner(st) and
                 st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == expected_mode and
                 0 <= st.st_size <= limit,
                 "LEDGER_FILE_NOT_ROOT_PRIVATE_SINGLE_LINK:" + basename)
        need((before.st_dev, before.st_ino) ==
             (named.st_dev, named.st_ino), "LEDGER_FILE_INODE_CHANGED")
        raw = bytearray()
        while True:
            chunk = os.read(file_fd, 4096)
            if not chunk:
                break
            raw.extend(chunk)
            need(len(raw) <= limit, "LEDGER_FILE_TOO_LARGE")
        after = os.fstat(file_fd)
        named_after = os.stat(basename, dir_fd=fd, follow_symlinks=False)
        need((before.st_dev, before.st_ino, before.st_size,
              before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size,
              after.st_mtime_ns, after.st_ctime_ns) and
             (after.st_dev, after.st_ino) ==
             (named_after.st_dev, named_after.st_ino) and
             len(raw) == before.st_size,
             "LEDGER_FILE_CHANGED_DURING_READ")
        return bytes(raw)
    finally:
        os.close(file_fd)


def strict_json(raw):
    def unique(pairs):
        out = {}
        for key, val in pairs:
            need(key not in out, "LEDGER_DUPLICATE_JSON_KEY")
            out[key] = val
        return out
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, TypeError, UnicodeError):
        raise Refusal("LEDGER_CORRUPT_JSON") from None


def entries_locked(fd):
    names = os.listdir(fd)
    need(LOCK in names, "LEDGER_LOCK_MISSING")
    need(len(names) <= MAX_ENTRIES + 1, "LEDGER_ENTRY_LIMIT")
    names.remove(LOCK)
    for name in names:
        need(ENTRY.fullmatch(name) is not None, "LEDGER_UNKNOWN_OR_PARTIAL_ENTRY")
    data = []
    for name in sorted(names):
        raw = private_file(fd, name, MAX_ENTRY_BYTES)
        entry = strict_json(raw)
        match = ENTRY.fullmatch(name)
        need(isinstance(entry, dict) and set(entry) == FIELDS and
             entry["schema"] == SCHEMA and entry["repository"] == REPO and
             type(entry["sequence"]) is int and
             entry["sequence"] == int(match.group(1)) and
             isinstance(entry["receipt_sha256"], str) and
             entry["receipt_sha256"] == match.group(2) and
             all(isinstance(entry[key], str) and SHA.fullmatch(entry[key])
                 for key in ("receipt_sha256", "policy_sha256",
                             "authority_sha256", "previous_entry_sha256")),
             "LEDGER_ENTRY_IDENTITY_INVALID")
        data.append((entry, raw))
    previous_hash = "0" * 64
    receipts, policies = set(), set()
    for seq, (entry, raw) in enumerate(data, 1):
        need(entry["sequence"] == seq and
             entry["previous_entry_sha256"] == previous_hash and
             entry["receipt_sha256"] not in receipts and
             entry["policy_sha256"] not in policies,
             "LEDGER_CHAIN_OR_SEQUENCE_ROLLBACK_DETECTED")
        receipts.add(entry["receipt_sha256"])
        policies.add(entry["policy_sha256"])
        previous_hash = hashlib.sha256(raw).hexdigest()
    return data, previous_hash


@contextlib.contextmanager
def lock_ledger(fd):
    lockfd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=fd)
    try:
        original = os.fstat(lockfd)
        named = os.stat(LOCK, dir_fd=fd, follow_symlinks=False)
        need(stat.S_ISREG(original.st_mode) and root_owner(original) and
             original.st_nlink == 1 and
             stat.S_IMODE(original.st_mode) == 0o600 and
             original.st_size == 0 and
             (original.st_dev, original.st_ino) == (named.st_dev, named.st_ino),
             "LEDGER_LOCK_UNTRUSTED")
        try:
            fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise Refusal("LEDGER_BUSY_FAIL_CLOSED") from None
        need((os.fstat(lockfd).st_dev, os.fstat(lockfd).st_ino) ==
             (os.stat(LOCK, dir_fd=fd, follow_symlinks=False).st_dev,
              os.stat(LOCK, dir_fd=fd, follow_symlinks=False).st_ino),
             "LEDGER_LOCK_REPLACED")
        yield
    finally:
        os.close(lockfd)


def initialize(directory):
    qualify_runtime()
    with private_root(directory) as fd:
        need(not os.listdir(fd), "LEDGER_ALREADY_INITIALIZED")
        lockfd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            os.fsync(lockfd)
        finally:
            os.close(lockfd)
        os.fsync(fd)
    return {"status": "CI_LEDGER_INITIALIZED_NOT_PRODUCTION",
            "pkg_invoked": False, "owner_issuer_authenticated": False}


def consumption(directory, authority, policy, receipt, sequence,
                fail_after_create=False):
    # Deliberately assumes inputs were verified by the separate _114
    # read-only seed. THIS primitive does not authenticate those inputs.
    qualify_runtime()
    for label, value in (("authority", authority), ("policy", policy),
                         ("receipt", receipt)):
        need(isinstance(value, str) and SHA.fullmatch(value) is not None and
             value != "0" * 64, "LEDGER_INVALID_DIGEST:" + label)
    need(type(sequence) is int and 1 <= sequence <= MAX_ENTRIES,
         "LEDGER_INVALID_SEQUENCE")
    with private_root(directory) as fd, lock_ledger(fd):
        history, previous_hash = entries_locked(fd)
        count = len(history)
        need(count < MAX_ENTRIES, "LEDGER_CAPACITY_EXCEEDED")
        need(sequence == count + 1, "LEDGER_SEQUENCE_REPLAY_OR_GAP")
        need(not any(record["receipt_sha256"] == receipt for record, _ in history),
             "LEDGER_RECEIPT_ALREADY_SPENT")
        need(not any(record["policy_sha256"] == policy for record, _ in history),
             "LEDGER_POLICY_ALREADY_SPENT")
        entry = {"schema": SCHEMA, "repository": REPO,
                 "sequence": sequence, "receipt_sha256": receipt,
                 "policy_sha256": policy, "authority_sha256": authority,
                 "previous_entry_sha256": previous_hash}
        raw = (json.dumps(entry, sort_keys=True, separators=(",", ":")) +
               "\n").encode("utf-8")
        need(len(raw) <= MAX_ENTRY_BYTES, "LEDGER_ENTRY_OVERSIZE")
        name = "spent-" + f"{sequence:012d}" + "-" + receipt + ".json"
        written = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                          os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            if fail_after_create:
                # Simulated process death after irreversible exclusive create:
                # the zero-byte poisoned entry MUST never be silently repaired.
                raise Refusal("LEDGER_INJECTED_INTERRUPTED_INTENT")
            offset = 0
            while offset < len(raw):
                step = os.write(written, raw[offset:])
                need(step > 0, "LEDGER_SHORT_WRITE_POISONED")
                offset += step
            os.fsync(written)
        finally:
            os.close(written)
        os.fsync(fd)
    return {"status": "CI_LOCAL_ATOMIC_SPENT_NOT_PRODUCTION_AUTHORITY",
            "sequence": sequence, "receipt_sha256": receipt,
            "policy_sha256": policy, "pkg_invoked": False,
            "production_pkg_authorized": False,
            "independent_policy_freshness": False,
            "durable_external_rollback_protection": False}


def inspect(directory):
    qualify_runtime()
    with private_root(directory) as fd, lock_ledger(fd):
        records, last_hash = entries_locked(fd)
    return {"status": "CI_LEDGER_LOCAL_CONSISTENCY_ONLY",
            "spent": len(records), "last_sequence": len(records),
            "last_entry_sha256": last_hash, "pkg_invoked": False,
            "production_pkg_authorized": False,
            "durable_external_rollback_protection": False}


def main(args):
    try:
        need(args and args[0] in ("initialize", "consume", "inspect"),
             "CI_LEDGER_COMMAND_REQUIRED")
        if len(args) == 2 and args[0] == "initialize":
            answer = initialize(args[1])
        elif len(args) == 2 and args[0] == "inspect":
            answer = inspect(args[1])
        elif len(args) == 6 and args[0] == "consume":
            need(re.fullmatch(r"[1-9][0-9]{0,11}\Z", args[5]) is not None,
                 "CI_LEDGER_DECIMAL_SEQUENCE_REQUIRED")
            answer = consumption(args[1], args[2], args[3], args[4],
                                 int(args[5]))
        else:
            raise Refusal("CI_LEDGER_EXACT_ARGUMENTS_REQUIRED")
    except (Refusal, OSError, ValueError, TypeError, UnicodeError) as exc:
        print(PREFIX + "REFUSED:" + str(exc), file=sys.stderr)
        return 78
    print(PREFIX + json.dumps(answer, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
