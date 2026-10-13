#!/usr/bin/env python3
"""Single durable Strategies/Voice Apply operation, under original FD9.

No independent daemon, Config writer, IPFW ownership ledger or recovery
policy. This records the cross-resource transaction already coordinated by
the common native Apply worker. The existing lifecycle guard refuses all
ordinary mutations while this record is nonterminal or untrusted.

Only the installed root-owned FreeBSD service may call the CLI, with FD9
verified by the existing IPFW adapter. Pure class methods accept temporary
directories for fault tests; never pass an arbitrary root via production CLI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys

DEFAULT_ROOT = Path("/var/db/zapret2/shared-apply")
RECORD = "operation.json"
SCHEMA = 1
MAX_RECORD = 8192
DIGEST = re.compile(r"^[a-f0-9]{64}$")
OP_ID = re.compile(r"^[a-f0-9]{32}$")
FIELD = re.compile(r"^[a-z]+(?:\.[a-z]+){1,2}$")
PAGES = frozenset(("strategies", "voice"))
PHASES = frozenset((
    "prepared", "activating", "activated", "config-saved",
    "committed", "restored", "restore-failed", "requires-review",
))
TERMINAL = frozenset(("committed", "restored"))
NEXT = {
    "prepared": frozenset(("activating", "restored")),
    # An activation failure may have fully restored every resource without
    # ever publishing 'activated'; mark restored only after attested rollback.
    "activating": frozenset(("activated", "restored", "requires-review", "restore-failed")),
    "activated": frozenset(("config-saved", "restored", "restore-failed",
                            "requires-review")),
    "config-saved": frozenset(("committed", "requires-review")),
    "committed": frozenset(),
    "restored": frozenset(),
    "restore-failed": frozenset(),
    "requires-review": frozenset(),
}


class SharedOperationError(RuntimeError):
    pass


def _exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _secure(path: Path, *, directory: bool, owner: int) -> os.stat_result:
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) if directory
            else not stat.S_ISREG(info.st_mode)):
        raise SharedOperationError("untrusted shared Apply file type")
    if info.st_uid != owner or info.st_mode & 0o077 or (
        not directory and (info.st_nlink != 1 or info.st_size > MAX_RECORD)
    ):
        raise SharedOperationError("untrusted shared Apply owner or mode")
    return info


def _validate_detail(detail: object) -> dict:
    if not isinstance(detail, dict) or set(detail) != {
        "id", "page", "base", "candidate", "changed_fields"
    }:
        raise SharedOperationError("invalid common Apply detail keys")
    if not isinstance(detail["id"], str) or not OP_ID.fullmatch(detail["id"]):
        raise SharedOperationError("invalid common Apply operation ID")
    if detail["page"] not in PAGES:
        raise SharedOperationError("invalid common Apply page")
    if any(not isinstance(detail[k], str) or not DIGEST.fullmatch(detail[k])
           for k in ("base", "candidate")):
        raise SharedOperationError("invalid common Apply generation")
    fields = detail["changed_fields"]
    if not isinstance(fields, list) or len(fields) > 32 or any(
        not isinstance(f, str) or not FIELD.fullmatch(f) for f in fields
    ) or len(fields) != len(set(fields)):
        raise SharedOperationError("invalid common Apply field proof")
    return detail


def _validate_record(record: object) -> dict:
    if not isinstance(record, dict) or set(record) != {"schema", "phase", "detail"} \
            or type(record["schema"]) is not int or record["schema"] != SCHEMA \
            or record["phase"] not in PHASES:
        raise SharedOperationError("invalid common Apply record")
    _validate_detail(record["detail"])
    return record


class SharedApplyOperation:
    def __init__(self, root: Path = DEFAULT_ROOT, *, owner: int | None = None):
        self.root = Path(root)
        self.owner = os.geteuid() if owner is None else owner

    def read(self) -> dict | None:
        if not _exists(self.root):
            return None
        _secure(self.root, directory=True, owner=self.owner)
        target = self.root / RECORD
        if not _exists(target):
            raise SharedOperationError("orphan shared Apply root")
        _secure(target, directory=False, owner=self.owner)
        # Reject any leftover temporary file or unrelated artifact: a
        # partially written transaction cannot silently authorize start.
        if set(os.listdir(self.root)) != {RECORD}:
            raise SharedOperationError("untrusted common Apply directory entries")
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            pinned = os.fstat(fd)
            named = target.lstat()
            if (pinned.st_ino, pinned.st_dev) != (named.st_ino, named.st_dev):
                raise SharedOperationError("common Apply record inode changed")
            raw = os.read(fd, MAX_RECORD + 1)
        finally:
            os.close(fd)
        if len(raw) > MAX_RECORD:
            raise SharedOperationError("oversized common Apply record")
        try:
            return _validate_record(json.loads(raw))
        except (ValueError, TypeError, UnicodeError) as error:
            raise SharedOperationError("corrupt common Apply record") from error

    def advance(self, phase: str, detail: dict) -> dict:
        if phase not in PHASES:
            raise SharedOperationError("unrecognized common Apply phase")
        _validate_detail(detail)
        before = self.read()
        if phase == "prepared":
            if before is not None and before["phase"] not in TERMINAL:
                raise SharedOperationError("unfinished common Apply operation")
            if before is not None and before["detail"]["id"] == detail["id"]:
                raise SharedOperationError("reused common Apply transaction ID")
        else:
            if before is None or before["detail"] != detail:
                raise SharedOperationError("common Apply transaction identity changed")
            if phase not in NEXT[before["phase"]]:
                raise SharedOperationError("illegal common Apply phase transition")
        record = {"schema": SCHEMA, "phase": phase, "detail": detail}
        raw = (json.dumps(record, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True) + "\n").encode("ascii")
        if len(raw) > MAX_RECORD:
            raise SharedOperationError("common Apply record size exceeded")
        if not _exists(self.root):
            self.root.mkdir(mode=0o700)
        _secure(self.root, directory=True, owner=self.owner)
        # No directory entry is ever removed automatically during recovery;
        # a failed temporary write is preserved and blocks mutations.
        entries = set(os.listdir(self.root))
        if entries not in (set(), {RECORD}):
            raise SharedOperationError("untrusted common Apply root")
        temporary = self.root / ("." + detail["id"] + ".pending")
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temporary, self.root / RECORD)
        dirfd = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                        getattr(os, "O_NOFOLLOW", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        return record

    def recover_prepared(self, identity: str, attest) -> dict:
        """Only PREPARED can be closed without touching runtime/Config/IPFW.

        The journal write precedes the mutating transition; an executor can
        never change kernel/processes until the durable 'activating' fsync
        has returned. The same FD9 is held across witness and closure.
        """
        record = self.read()
        if record is None or record["phase"] != "prepared" or \
           record["detail"]["id"] != identity:
            raise SharedOperationError("prepared-only recovery refused")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("shared candidate attestation refused")
        if self.read() != record:
            raise SharedOperationError("shared Apply phase changed during recovery")
        return self.advance("restored", record["detail"])

    def advisory(self) -> dict:
        record = self.read()
        if record is None or record["phase"] in TERMINAL:
            return {"state": "clear", "safe_to_mutate": True}
        return {
            "state": "blocked", "reason": "shared-apply-pending",
            "phase": record["phase"], "safe_to_mutate": False,
        }


def main(argv: list[str]) -> int:
    inspection = len(argv) == 2 and argv[1] == "inspect"
    recording = len(argv) == 8 and argv[1] == "record"
    recovery = len(argv) == 3 and argv[1] == "recover-prepared" and bool(OP_ID.fullmatch(argv[2]))
    if not (inspection or recording or recovery):
        print("usage: shared_apply_operation.py inspect|record PHASE ID PAGE BASE CANDIDATE FIELDS",
              file=sys.stderr)
        return 64
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        if inspection:
            record = SharedApplyOperation(owner=0).read()
            if record is None:
                print("none")
            elif record["phase"] == "committed":
                detail = record["detail"]
                print("committed " + detail["id"] + " " + detail["page"])
            elif record["phase"] == "restored":
                print("restored")
            elif record["phase"] == "prepared":
                detail = record["detail"]
                print("prepared " + detail["id"] + " " + detail["page"])
            else:
                # Never make an incomplete operation look like no owner.
                raise SharedOperationError("unfinished common Apply blocks native boot")
        elif recovery:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            store.recover_prepared(
                argv[2],
                lambda: bool(verify_seal(WORK / argv[2], owner=0)),
            )
            print("prepared-restored")
        else:
            fields = [] if argv[7] == "-" else argv[7].split(",")
            detail = {
                "id": argv[3], "page": argv[4], "base": argv[5],
                "candidate": argv[6], "changed_fields": fields,
            }
            SharedApplyOperation(owner=0).advance(argv[2], detail)
    except (OSError, ValueError, SharedOperationError, RuntimeError) as error:
        print("ERROR: shared Apply operation cannot advance: " + str(error),
              file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
