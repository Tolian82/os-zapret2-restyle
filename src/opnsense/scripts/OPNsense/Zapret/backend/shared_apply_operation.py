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

import hashlib
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
    # Existing unextended records remain readable; a new transaction can
    # retain precisely ONE predecessor inside the SAME durable journal.
    # No external previous-owner database or second lifecycle is introduced.
    if not isinstance(record, dict) or set(record) not in (
        {"schema", "phase", "detail"},
        {"schema", "phase", "detail", "previous"},
        {"schema", "phase", "detail", "legacy_predecessor"},
    ) or type(record["schema"]) is not int or record["schema"] != SCHEMA \
            or record["phase"] not in PHASES:
        raise SharedOperationError("invalid common Apply record")
    _validate_detail(record["detail"])
    if "legacy_predecessor" in record:
        if record["phase"] != "prepared" or record["detail"]["page"] != "voice" or \
           not isinstance(record["legacy_predecessor"], str) or \
           not DIGEST.fullmatch(record["legacy_predecessor"]):
            raise SharedOperationError("invalid armed legacy predecessor proof")
    if "previous" in record:
        _validate_detail(record["previous"])
        if record["previous"]["id"] == record["detail"]["id"]:
            raise SharedOperationError("common Apply predecessor ID reused")
    return record


def committed_owner(record: dict | None) -> dict | None:
    """The live common owner is not erased by a subsequent rolled-back Apply."""
    if record is None:
        return None
    _validate_record(record)
    if record["phase"] == "committed":
        return record["detail"]
    if record["phase"] == "restored":
        return record.get("previous")
    return None


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

    def advance(
        self, phase: str, detail: dict, *, legacy_predecessor: str | None = None
    ) -> dict:
        if phase not in PHASES:
            raise SharedOperationError("unrecognized common Apply phase")
        _validate_detail(detail)
        before = self.read()
        if phase == "prepared":
            if legacy_predecessor is not None and (
                detail["page"] != "voice" or not DIGEST.fullmatch(legacy_predecessor)
                or before is not None
            ):
                raise SharedOperationError("legacy predecessor requires new Voice owner and proof")
            if before is not None and before["phase"] not in TERMINAL:
                raise SharedOperationError("unfinished common Apply operation")
            if before is not None and before["detail"]["id"] == detail["id"]:
                raise SharedOperationError("reused common Apply transaction ID")
            previous = committed_owner(before)
            if previous is not None and previous["id"] == detail["id"]:
                raise SharedOperationError("reused common Apply predecessor ID")
        else:
            if legacy_predecessor is not None:
                raise SharedOperationError("cannot inject predecessor after preparation")
            if before is not None and "legacy_predecessor" in before:
                # A running legacy owner cannot be stopped by the ordinary
                # shared Apply path, generic record CLI, or boot recovery.
                # A future separately attested ONE-coordinator actuator
                # must explicitly perform this transition.
                raise SharedOperationError("armed legacy predecessor requires reviewed executor")
            if before is None or before["detail"] != detail:
                raise SharedOperationError("common Apply transaction identity changed")
            if phase not in NEXT[before["phase"]]:
                raise SharedOperationError("illegal common Apply phase transition")
            previous = before.get("previous")
        record = {"schema": SCHEMA, "phase": phase, "detail": detail}
        if previous is not None:
            record["previous"] = previous
        if legacy_predecessor is not None:
            record["legacy_predecessor"] = legacy_predecessor
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

    def prepare_legacy_predecessor(self, detail: dict, attest) -> dict:
        """Durably arm STOP intent only after a complete sealed old snapshot.

        This does not stop any old processes or modify kernel/Config/marker.
        It only binds one immutable previous-state digest into the EXISTING
        common journal; generic activating and boot close remain forbidden.
        """
        _validate_detail(detail)
        if detail["page"] != "voice" or self.read() is not None:
            raise SharedOperationError("legacy STOP intent requires fresh Voice owner")
        if not callable(attest):
            raise SharedOperationError("legacy predecessor attestation required")
        digest = attest()
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise SharedOperationError("invalid sealed legacy predecessor fingerprint")
        if self.read() is not None:
            raise SharedOperationError("shared owner appeared while arming legacy")
        return self.advance("prepared", detail, legacy_predecessor=digest)

    def recover_prepared(self, identity: str, attest) -> dict:
        """Only PREPARED can be closed without touching runtime/Config/IPFW.

        The journal write precedes the mutating transition; an executor can
        never change kernel/processes until the durable 'activating' fsync
        has returned. The same FD9 is held across witness and closure.
        """
        record = self.read()
        if record is None or record["phase"] != "prepared" or \
           record["detail"]["id"] != identity or \
           "legacy_predecessor" in record:
            # This candidate never used the ordinary prepared lifecycle.
            # Legacy is still a distinct LIVE owner; do not auto-dismiss
            # its bound previous snapshot on boot.
            raise SharedOperationError("prepared-only recovery refused")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("shared candidate attestation refused")
        if self.read() != record:
            raise SharedOperationError("shared Apply phase changed during recovery")
        return self.advance("restored", record["detail"])

    def recover_activating_pristine(self, identity: str, previous_id: str, attest) -> dict:
        """Close only a no-mutation crash with an attested previous owner.

        The caller under original root FD9 must prove that native Config,
        installed runtime bytes, all engine processes and scoped IPFW still
        describe the *previous* sealed owner. A replaced/partial runtime or
        an initial legacy owner has no safe automatic recovery here.
        """
        record = self.read()
        if record is None or record["phase"] != "activating" or \
                record["detail"]["id"] != identity or \
                record.get("previous", {}).get("id") != previous_id:
            raise SharedOperationError("pristine activating recovery refused")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("pristine activating attestation refused")
        if self.read() != record:
            raise SharedOperationError("activating journal changed during attestation")
        return self.advance("restored", record["detail"])

    def _finish_cold_pre_save_restore(
        self, phase: str, identity: str, previous_id: str, attest
    ) -> dict:
        """Finish only the attested cold old-Config rollback for this phase.

        Both activating (after a full atomic rename) and activated can have
        an exactly installed new release. All real Config/process/IPFW/tree
        proofs are enforced by the original root-FD9 service before this
        terminal durable write. The seal is checked again inside the CLI.
        """
        record = self.read()
        if record is None or record["phase"] != phase or \
                record["detail"]["id"] != identity or \
                record.get("previous", {}).get("id") != previous_id:
            raise SharedOperationError(phase + " rollback completion refused")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError(phase + " rollback attestation refused")
        if self.read() != record:
            raise SharedOperationError(phase + " journal changed during recovery")
        return self.advance("restored", record["detail"])

    def finish_activated_restore(self, identity: str, previous_id: str, attest) -> dict:
        return self._finish_cold_pre_save_restore(
            "activated", identity, previous_id, attest
        )

    def finish_activating_installed_restore(
        self, identity: str, previous_id: str, attest
    ) -> dict:
        return self._finish_cold_pre_save_restore(
            "activating", identity, previous_id, attest
        )

    def finish_saved(self, identity: str, attest) -> dict:
        """Close Config-saved only after external FD9 Config/kernel attestation.

        This in-memory transition cannot itself certify a runtime: its caller
        MUST first verify saved Config, no preexisting kernel/proc ownership,
        re-activate the sealed release and successfully commit shared IPFW.
        """
        record = self.read()
        if record is None or record["phase"] != "config-saved" or \
           record["detail"]["id"] != identity:
            raise SharedOperationError("saved-only completion refused")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("saved candidate attestation refused")
        if self.read() != record:
            raise SharedOperationError("shared Apply changed during saved recovery")
        return self.advance("committed", record["detail"])

    def advisory(self) -> dict:
        record = self.read()
        if record is None or record["phase"] in TERMINAL:
            return {"state": "clear", "safe_to_mutate": True}
        return {
            "state": "blocked", "reason": "shared-apply-pending",
            "phase": record["phase"], "safe_to_mutate": False,
        }


def fingerprint_legacy_predecessor(work: Path, *, owner: int = 0) -> str:
    """Read-only digest of sealed common bundle AND exact old five-domain plan.

    No second journal, arbitrary filesystem root from CLI or inferred owner.
    """
    from shared_apply_seal import verify_seal
    from voice_cutover_backup import _private_dir
    from voice_native_legacy_previous_seal import (
        NAME, inspect_legacy_previous,
    )
    from voice_native_legacy_restore_plan import (
        PLAN_NAME, inspect_legacy_restore_plan,
    )
    if not OP_ID.fullmatch(work.name):
        raise SharedOperationError("invalid legacy predecessor operation ID")
    seal = verify_seal(work, owner=owner)
    root = work / "legacy-backup"
    _private_dir(root)
    if set(os.listdir(root)) != {NAME, PLAN_NAME}:
        raise SharedOperationError("untrusted old predecessor backup entries")
    previous = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    if plan["previous_five"] != previous["previous_five"]:
        raise SharedOperationError("legacy restore plan and prior owner differ")
    proof = {"candidate_seal": seal, "previous": previous, "plan": plan}
    return hashlib.sha256(json.dumps(
        proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def main(argv: list[str]) -> int:
    legacy_arm = len(argv) == 6 and argv[1] == "arm-legacy" and bool(
        OP_ID.fullmatch(argv[2]) and DIGEST.fullmatch(argv[3])
        and DIGEST.fullmatch(argv[4])
    )
    inspection = len(argv) == 2 and argv[1] == "inspect"
    recording = len(argv) == 8 and argv[1] == "record"
    recovery = len(argv) == 3 and argv[1] == "recover-prepared" and bool(OP_ID.fullmatch(argv[2]))
    finish = len(argv) == 3 and argv[1] == "finish-saved" and bool(OP_ID.fullmatch(argv[2]))
    pristine = len(argv) == 4 and argv[1] == "recover-activating" and all(
        OP_ID.fullmatch(value) for value in argv[2:]
    )
    cold_restore = len(argv) == 4 and argv[1] in (
        "finish-activated", "finish-activating"
    ) and all(OP_ID.fullmatch(value) for value in argv[2:])
    if not (inspection or recording or recovery or finish or pristine or cold_restore or legacy_arm):
        print("usage: shared_apply_operation.py inspect|record PHASE ID PAGE BASE CANDIDATE FIELDS",
              file=sys.stderr)
        return 64
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        if legacy_arm:
            from shared_apply_seal import WORK
            fields = [] if argv[5] == "-" else argv[5].split(",")
            detail = {
                "id": argv[2], "page": "voice", "base": argv[3],
                "candidate": argv[4], "changed_fields": fields,
            }
            result = SharedApplyOperation(owner=0).prepare_legacy_predecessor(
                detail, lambda: fingerprint_legacy_predecessor(WORK / argv[2])
            )
            print("legacy-armed-id=" + result["detail"]["id"])
            print("legacy-armed-predecessor=" + result["legacy_predecessor"])
            print("legacy-handoff-authorized=0")
        elif inspection:
            record = SharedApplyOperation(owner=0).read()
            if record is None:
                print("none")
            elif record["phase"] == "committed":
                detail = record["detail"]
                print("committed " + detail["id"] + " " + detail["page"])
            elif record["phase"] == "restored":
                prior = committed_owner(record)
                if prior is None:
                    print("restored")
                else:
                    # Returning 'restored' here would send the ordinary
                    # service to LEGACY boot over the preceding common owner.
                    print("committed " + prior["id"] + " " + prior["page"])
            elif record["phase"] in ("prepared", "config-saved"):
                detail = record["detail"]
                prefix = "legacy-prepared" if "legacy_predecessor" in record else record["phase"]
                print(prefix + " " + detail["id"] + " " + detail["page"])
            elif record["phase"] in ("activating", "activated") and "previous" in record:
                detail, previous = record["detail"], record["previous"]
                print(record["phase"] + " " + detail["id"] + " " + detail["page"] +
                      " " + previous["id"] + " " + previous["page"])
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
        elif pristine:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            store.recover_activating_pristine(
                argv[2], argv[3],
                lambda: bool(verify_seal(WORK / argv[2], owner=0) and
                             verify_seal(WORK / argv[3], owner=0)),
            )
            print("activating-pristine-restored")
        elif cold_restore:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            finish_cold = (
                store.finish_activated_restore
                if argv[1] == "finish-activated"
                else store.finish_activating_installed_restore
            )
            finish_cold(
                argv[2], argv[3],
                lambda: bool(verify_seal(WORK / argv[2], owner=0) and
                             verify_seal(WORK / argv[3], owner=0)),
            )
            print(argv[1][7:] + "-restored")
        elif finish:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            store.finish_saved(
                argv[2],
                lambda: bool(verify_seal(WORK / argv[2], owner=0)),
            )
            print("saved-committed")
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
