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
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import sys

DEFAULT_ROOT = Path("/var/db/zapret2/shared-apply")
RECORD = "operation.json"
SCHEMA = 1
EARLY_START_CAUSES = frozenset(("no-live-pid", "stability-unverified"))
IPFW_ATTACH_CAUSES = frozenset(("rule-add-rejected",))
MAX_RECORD = 8192
MAX_FOUND_PLAN = 4 * 1024 * 1024
FOUND_NAMES = ("youtube", "user", "auto")
FOUND_KIND = "sealed-five-editor-three-file-intent"
# The original journal, not a second file ledger, persists the all-three
# physical write intent BEFORE the first P2-owned rename/link.
FOUND_FILE_PHASES = frozenset(("found-files-writing", "found-files-written"))
# Config::save on OPNsense releases its native flock. The original PHP
# owner must hold Config->P2 until save returns, RELEASE P2, then reacquire
# Config->P2 for independent post-save proof. Holding P2 while attempting
# a fresh Config lock reverses lock order and risks deadlocking P2a.
FOUND_CONFIG_PHASES = frozenset(("found-config-saving", "found-config-saved"))
FOUND_POST_PHASES = frozenset(("found-files-written", *FOUND_CONFIG_PHASES))
FOUND_ROLLBACK_FROM = frozenset((*FOUND_FILE_PHASES, "found-config-saving"))
FOUND_RESTORING = "found-restoring"
FOUND_RUNTIME_NEXT = {
    "found-config-saved": {"activating"},
    "activating": {"activated"},
    "activated": {"config-saved", "epoch-finalizing"},
    "config-saved": {"committed"},
    "epoch-finalizing": {"committed"},
}
FOUND_RUNTIME_PHASES = frozenset(FOUND_RUNTIME_NEXT) - {"found-config-saved"}
FOUND_NEXT = {"prepared": "found-files-writing",
              "found-files-writing": "found-files-written",
              "found-files-written": "found-config-saving",
              "found-config-saving": "found-config-saved"}
DIGEST = re.compile(r"^[a-f0-9]{64}$")
OP_ID = re.compile(r"^[a-f0-9]{32}$")
FIELD = re.compile(r"^[a-z]+(?:\.[a-z]+){1,2}$")
PAGES = frozenset(("strategies", "voice"))
PHASES = frozenset((
    "prepared", "activating", "activated", "config-saved",
    "epoch-finalizing", "committed", "restored", "restore-failed", "requires-review",
    "found-files-writing", "found-files-written",
    "found-config-saving", "found-config-saved", FOUND_RESTORING,
))
TERMINAL = frozenset(("committed", "restored"))
NEXT = {
    "prepared": frozenset(("activating", "restored")),
    # An activation failure may have fully restored every resource without
    # ever publishing 'activated'; mark restored only after attested rollback.
    "activating": frozenset(("activated", "restored", "requires-review", "restore-failed")),
    "activated": frozenset(("config-saved", "epoch-finalizing", "restored",
                            "restore-failed", "requires-review")),
    # The native observer never enters ordinary saved-only recovery.
    "config-saved": frozenset(("committed", "requires-review")),
    # A real native observer must finish its pretraffic epoch BEFORE
    # becoming a terminal common owner. This is the same original journal.
    "epoch-finalizing": frozenset(("committed", "requires-review")),
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



def _validate_manifest_binding(binding: object, detail: dict) -> dict:
    """One S10 immutable root pin in the EXISTING original durable journal.

    This field commits the exact sibling manifest SHA without putting it in
    the original release inventory, avoiding root -> seal -> root recursion.
    It NEVER authorizes activation or mutates a service. Only an original
    PREPARED operation may first attach it after physical S09b/S10a proof.
    """
    if (type(binding) is not dict or
            set(binding) != {"schema", "generation", "root_sha256",
                             "seal_sha256", "candidate_sha256"} or
            type(binding["schema"]) is not int or binding["schema"] != 1 or
            type(binding["generation"]) is not str or
            binding["generation"] != detail["id"] or
            any(type(binding[key]) is not str or not DIGEST.fullmatch(binding[key])
                for key in ("root_sha256", "seal_sha256", "candidate_sha256")) or
            binding["candidate_sha256"] != detail["candidate"]):
        raise SharedOperationError("untrusted original immutable-root binding")
    return binding


def _validate_found_intent(found: object, detail: dict, phase: str) -> dict:
    """Minimal original-journal binding, not a destination writer/validator.

    All full physical preimages, future after-bytes and Config candidate
    remain in the independently sealed shared-work plan. The journal holds
    only a fixed binding to its entire byte-for-byte sealed plan. No alternate
    file parser, Config reader or second write-ahead log is introduced.
    """
    basics = {"schema", "kind", "plan_sha256", "sources"}
    rollback = phase == FOUND_RESTORING
    pinned = phase in FOUND_POST_PHASES | FOUND_RUNTIME_PHASES or (
        rollback and isinstance(found, dict) and "post" in found)
    writing = rollback or pinned or phase == "found-files-writing"
    required = basics | ({"stages"} if writing else set()) | ({"post"} if pinned else set())
    if isinstance(found, dict) and "runtime_mode" in found:
        if found["runtime_mode"] not in ("0", "1"):
            raise SharedOperationError("invalid found runtime mode")
        required.add("runtime_mode")
    if rollback:
        required.add("restoring")
    if (not isinstance(found, dict) or
            set(found) != required or
            type(found["schema"]) is not int or found["schema"] != 1 or
            found["kind"] != FOUND_KIND or
            type(found["plan_sha256"]) is not str or
            not DIGEST.fullmatch(found["plan_sha256"]) or
            found["sources"] != list(FOUND_NAMES) or
            detail["page"] != "strategies" or
            phase not in {"prepared", FOUND_RESTORING} | FOUND_FILE_PHASES |
                         FOUND_CONFIG_PHASES | FOUND_RUNTIME_PHASES):
        raise SharedOperationError("invalid sealed found intent in original journal")
    if writing:
        _validate_found_stages(found["stages"])
    if pinned:
        _validate_found_post(found["post"])
    if rollback:
        restoring = found["restoring"]
        if not isinstance(restoring, dict) or not set(restoring).issubset(found["stages"]):
            raise SharedOperationError("invalid found rollback sources")
        for name, pin in restoring.items():
            if pin is None and name == "auto":
                continue
            _validate_found_stages({name: {"state": "ready", "pin": pin}})
    return found


def _validate_found_stages(stages: object) -> dict:
    """Each fsynced pre-rename inode pin belongs to the original FD9 writer.

    The journal is intentionally not a rollback instruction. Read-only
    recovery must independently check the sealed plan and physical inode.
    """
    if (not isinstance(stages, dict) or len(stages) > len(FOUND_NAMES) or
            not set(stages).issubset(FOUND_NAMES)):
        raise SharedOperationError("invalid found staged source set")
    for name, row in stages.items():
        if not isinstance(row, dict) or set(row) != {"state", "pin"} or \
                row["state"] not in ("ready", "installed"):
            raise SharedOperationError("invalid found staged source status")
        pin = row["pin"]
        fields = {"device", "inode", "mtime_ns", "size", "sha256"}
        if not isinstance(pin, dict) or set(pin) not in (fields, fields | {"temp"}) or \
                any(type(pin[k]) is not int or pin[k] <= 0
                    for k in ("device", "inode", "mtime_ns")) or \
                type(pin["size"]) is not int or pin["size"] < 0 or \
                type(pin["sha256"]) is not str or not DIGEST.fullmatch(pin["sha256"]):
            raise SharedOperationError("invalid found staged inode pin")
        if "temp" in pin and (not isinstance(pin["temp"], str) or not re.fullmatch(
                r"\.auto-(?:detect|hostlist)-[a-f0-9]{32}\.tmp", pin["temp"])):
            raise SharedOperationError("invalid found temporary filename")
    return stages


def _validate_found_post(post: object) -> dict:
    """Bounded actual writer-created destination inode witness.

    Captured under the same original P2 lock after this owner wrote all
    changed sources. A correct byte hash without the original inode/time
    identity must never authorize cold restore/forward completion.
    """
    # The ONE journal uses sort_keys=True; decoded object key order is not
    # causal source order. Require exact membership, not insertion order.
    if not isinstance(post, dict) or set(post) != set(FOUND_NAMES):
        raise SharedOperationError("invalid original found post-image pins")
    fields = {"status", "device", "inode", "ctime_ns", "mtime_ns", "size", "sha256"}
    for name in FOUND_NAMES:
        row = post[name]
        if (not isinstance(row, dict) or set(row) != fields or
                row["status"] not in ("present", "missing") or
                any(type(row[field]) is not int or row[field] < 0
                    for field in ("device", "inode", "ctime_ns", "mtime_ns", "size")) or
                type(row["sha256"]) is not str or not DIGEST.fullmatch(row["sha256"])):
            raise SharedOperationError("invalid original found post-image pins")
        if row["status"] == "missing":
            if (name != "auto" or
                    any(row[field] != 0 for field in
                        ("device", "inode", "ctime_ns", "mtime_ns", "size")) or
                    row["sha256"] != hashlib.sha256(b"missing\0").hexdigest()):
                raise SharedOperationError("unqualified missing found post-image")
        elif row["device"] <= 0 or row["inode"] <= 0:
            raise SharedOperationError("invalid original found post-image inode")
    return post


def _validate_record(record: object) -> dict:
    # Existing unextended records remain readable; a new transaction can
    # retain precisely ONE predecessor inside the SAME durable journal.
    # No external previous-owner database or second lifecycle is introduced.
    # Failure metadata is optional only on a formerly committed owner.
    # Every original schema-1 record without it remains byte-compatible.
    keys = set(record) if type(record) is dict else set()
    allowed = (
        {"schema", "phase", "detail"},
        {"schema", "phase", "detail", "previous"},
        {"schema", "phase", "detail", "found"},
        {"schema", "phase", "detail", "previous", "found"},
    )
    if (type(record) is not dict or
            (keys - {"failure", "manifest"}) not in allowed or
            ("failure" in record and (record.get("phase") not in
                                      ("committed", "requires-review") or
                                      "found" in record)) or
            type(record["schema"]) is not int or record["schema"] != SCHEMA or
            record["phase"] not in PHASES):
        raise SharedOperationError("invalid common Apply record")
    _validate_detail(record["detail"])
    if "manifest" in record:
        if "found" in record:
            raise SharedOperationError("found transaction cannot attach immutable root")
        _validate_manifest_binding(record["manifest"], record["detail"])
    # No old Voice/Strategies record may invent protected physical or
    # Config-save uncertainty checkpoints without this exact found intent.
    if record["phase"] in FOUND_FILE_PHASES | FOUND_CONFIG_PHASES | {FOUND_RESTORING} and "found" not in record:
        raise SharedOperationError("found checkpoint missing original intent")
    if "found" in record:
        _validate_found_intent(record["found"], record["detail"], record["phase"])
    if "previous" in record:
        _validate_detail(record["previous"])
        if record["previous"]["id"] == record["detail"]["id"]:
            raise SharedOperationError("common Apply predecessor ID reused")
    if "failure" in record:
        failure = record["failure"]
        late = record["phase"] == "committed"
        early = record["phase"] == "requires-review"
        base_fields = {"schema", "code", "action", "operation_id",
                       "observed_at", "exit_status"}
        if (type(failure) is not dict or
                set(failure) != (base_fields if late else base_fields | {"cause"}) or
                type(failure["schema"]) is not int or failure["schema"] != 1 or
                not ((late and failure["code"] == "ENGINE_EXIT_AFTER_READY" and
                      failure["action"] == "runtime-failure") or
                     (early and type(failure["cause"]) is str and
                      ((failure["code"] == "ENGINE_START_UNVERIFIED" and
                        failure["action"] == "engine-start" and
                        failure["cause"] in EARLY_START_CAUSES) or
                       (failure["code"] == "IPFW_ATTACH_FAILED" and
                        failure["action"] == "ipfw-attach" and
                        failure["cause"] in IPFW_ATTACH_CAUSES)))) or
                failure["operation_id"] != record["detail"]["id"] or
                failure["exit_status"] is not None or
                type(failure["observed_at"]) is not str or
                len(failure["observed_at"]) != 20):
            raise SharedOperationError("untrusted original runtime failure receipt")
        try:
            at = datetime.strptime(failure["observed_at"], "%Y-%m-%dT%H:%M:%SZ")
            if at.strftime("%Y-%m-%dT%H:%M:%SZ") != failure["observed_at"]:
                raise ValueError("noncanonical")
        except ValueError as exc:
            raise SharedOperationError("untrusted original runtime failure time") from exc
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


def native_committed_owner_witness(root: Path = DEFAULT_ROOT) -> dict:
    """Read exact common owner identity from the existing terminal journal.

    FD9 is required for the production CLI; the native shell additionally
    attests saved Config, sealed release, process census and managed IPFW.
    """
    record = SharedApplyOperation(root).read()
    if record is None or record["phase"] not in TERMINAL:
        raise SharedOperationError("no terminal common Apply owner")
    owner = committed_owner(record)
    if owner is None:
        raise SharedOperationError("no committed common Apply predecessor")
    return {key: owner[key] for key in ("id", "page", "candidate")}


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

    def prepare_found(self, detail: dict, sealed_plan: bytes, attest, *,
                      runtime_mode: str | None = None) -> dict:
        """One fsynced ORIGINAL prepared record, prior to any HOSTLIST write.

        The attest callback must check the original FD9, immutable full
        bundle seal, Config snapshot and P2-protected physical preimages.
        This internal primitive has NO production CLI or GUI route yet.
        Future implementation must hold the approved locks through physical
        mutation and add cold recovery before lifting the Apply veto.
        """
        _validate_detail(detail)
        if detail["page"] != "strategies":
            raise SharedOperationError("found intent requires Strategies")
        if (type(sealed_plan) is not bytes or
                not 0 < len(sealed_plan) <= MAX_FOUND_PLAN):
            raise SharedOperationError("invalid sealed found plan bytes")
        try:
            plan = json.loads(sealed_plan)
        except (ValueError, TypeError, UnicodeError) as exc:
            raise SharedOperationError("invalid sealed found plan") from exc
        if (not isinstance(plan, dict) or plan.get("result") != "prepared" or
                plan.get("page") != "strategies" or
                plan.get("dependencies") != detail["base"] or
                not isinstance(plan.get("found_intent"), dict) or
                plan["found_intent"].get("config_revision") != detail["base"] or
                plan["found_intent"].get("commit_authorized") is not False or
                not isinstance(plan.get("found_batch"), dict) or
                list(plan["found_batch"]) != list(FOUND_NAMES) or
                any(not isinstance(plan["found_batch"][name], dict)
                    for name in FOUND_NAMES)):
            raise SharedOperationError("unqualified original found candidate")
        before = self.read()
        if before is not None and before["phase"] not in TERMINAL:
            raise SharedOperationError("unfinished original common Apply")
        if before is not None and (
                before["detail"]["id"] == detail["id"] or
                (committed_owner(before) is not None and
                 committed_owner(before)["id"] == detail["id"])):
            raise SharedOperationError("reused original common Apply operation")
        if not callable(attest) or attest(sealed_plan) is not True:
            raise SharedOperationError("sealed original found preimages unverified")
        if self.read() != before:
            raise SharedOperationError("common Apply owner changed during found attestation")
        result = {"schema": SCHEMA, "phase": "prepared", "detail": detail,
                  "found": {"schema": 1, "kind": FOUND_KIND,
                            "plan_sha256": hashlib.sha256(sealed_plan).hexdigest(),
                            "sources": list(FOUND_NAMES)}}
        if runtime_mode is not None:
            result["found"]["runtime_mode"] = runtime_mode
        previous = committed_owner(before)
        if previous is not None:
            result["previous"] = previous
        return self._persist_record(result)

    def advance_found_files(self, phase: str, detail: dict,
                            sealed_plan: bytes, attest, *,
                            post_images: dict | None = None) -> dict:
        """Durable original-journal P2 file checkpoints; import-only.

        Caller's original FD9 + native Config FD + original P2 flock must
        remain held through the callback, journal fsync and later physical
        CAS. This function does not itself change any HOSTLIST, Config,
        runtime or kernel state. There is deliberately NO generic record/
        CLI permission and NO terminal success/restore transition.
        """
        _validate_detail(detail)
        if phase not in FOUND_FILE_PHASES or type(sealed_plan) is not bytes or \
                not 0 < len(sealed_plan) <= MAX_FOUND_PLAN:
            raise SharedOperationError("invalid original found-files checkpoint")
        record = self.read()
        if (record is None or record["detail"] != detail or
                "found" not in record or
                FOUND_NEXT.get(record["phase"]) != phase or
                record["found"]["plan_sha256"] !=
                hashlib.sha256(sealed_plan).hexdigest()):
            raise SharedOperationError("found-files original state/plan mismatch")
        if phase == "found-files-written":
            _validate_found_post(post_images)
            try:
                plan = json.loads(sealed_plan)
                rows = plan["found_batch"]
                if list(rows) != list(FOUND_NAMES):
                    raise ValueError("missing three source rows")
                for name in FOUND_NAMES:
                    source = rows[name]
                    absent = (source["before_status"] == "missing" and
                              source["before"] == source["after"])
                    expected_status = "missing" if absent else "present"
                    expected_hash = hashlib.sha256(
                        b"missing\0" if absent
                        else source["after"].encode("utf-8")).hexdigest()
                    if (post_images[name]["status"] != expected_status or
                            post_images[name]["sha256"] != expected_hash or
                            (expected_status == "present" and
                             post_images[name]["size"] !=
                             len(source["after"].encode("utf-8")))):
                        raise ValueError("unsealed post-image mismatch")
                    stage = record["found"]["stages"].get(name)
                    changed = source["before"] != source["after"]
                    if (changed and
                            (stage is None or stage["state"] != "installed" or
                             (stage["pin"]["device"], stage["pin"]["inode"],
                              stage["pin"]["mtime_ns"], stage["pin"]["size"],
                              stage["pin"]["sha256"]) !=
                             (post_images[name]["device"], post_images[name]["inode"],
                              post_images[name]["mtime_ns"], post_images[name]["size"],
                              post_images[name]["sha256"]))):
                        raise ValueError("missing installed staged inode")
                    if not changed and stage is not None:
                        raise ValueError("staged unchanged source")
            except (KeyError, ValueError, TypeError, AttributeError) as exc:
                raise SharedOperationError("original found post-image plan mismatch") from exc
        elif post_images is not None:
            raise SharedOperationError("premature original post-image pins")
        if not callable(attest) or attest(phase, sealed_plan) is not True:
            raise SharedOperationError("original Config/P2 found-files witness refused")
        if self.read() != record:
            raise SharedOperationError("found-files journal changed under original locks")
        advanced = dict(record)
        advanced["phase"] = phase
        if phase == "found-files-writing":
            advanced["found"] = {**record["found"], "stages": {}}
        if phase == "found-files-written":
            advanced["found"] = {**record["found"], "post": post_images}
        return self._persist_record(advanced)

    def advance_found_stage(self, detail: dict, sealed_plan: bytes,
                            name: str, phase: str, pin: dict, attest) -> dict:
        """One fsynced staged temp inode BEFORE rename, then installed proof.

        Called ONLY by the existing original Config->P2-held FD9 writer.
        This is NOT a second physical writer, CLI route or recovery grant.
        """
        _validate_detail(detail)
        if (name not in FOUND_NAMES or phase not in ("ready", "installed") or
                type(sealed_plan) is not bytes or
                not 0 < len(sealed_plan) <= MAX_FOUND_PLAN):
            raise SharedOperationError("invalid original staged found checkpoint")
        _validate_found_stages({name: {"state": phase, "pin": pin}})
        record = self.read()
        if (record is None or record["phase"] != "found-files-writing" or
                record["detail"] != detail or "found" not in record or
                record["found"]["plan_sha256"] !=
                hashlib.sha256(sealed_plan).hexdigest()):
            raise SharedOperationError("original staged found journal mismatch")
        try:
            rows = json.loads(sealed_plan)["found_batch"]
            if (list(rows) != list(FOUND_NAMES) or
                    any(not isinstance(rows[n], dict) for n in FOUND_NAMES)):
                raise ValueError("bad rows")
            row = rows[name]
            if (row["before"] == row["after"] or
                    len(row["after"].encode("utf-8")) != pin["size"] or
                    hashlib.sha256(row["after"].encode("utf-8")).hexdigest() !=
                    pin["sha256"]):
                raise ValueError("wrong staged after-image")
            changed = [n for n in FOUND_NAMES
                       if rows[n]["before"] != rows[n]["after"]]
        except (ValueError, UnicodeError, KeyError, TypeError, AttributeError) as exc:
            raise SharedOperationError("original staged found plan mismatch") from exc
        stages = record["found"]["stages"]
        previous = stages.get(name)
        if phase == "ready":
            if previous is not None or any(
                    other not in stages or stages[other]["state"] != "installed"
                    for other in changed[:changed.index(name)]):
                raise SharedOperationError("original staged found source reordered")
        elif (previous is None or previous["state"] != "ready" or
              previous["pin"] != pin):
            raise SharedOperationError("original staged found inode not ready")
        if not callable(attest) or attest(phase, sealed_plan, name, pin) is not True:
            raise SharedOperationError("original staged inode witness refused")
        if self.read() != record:
            raise SharedOperationError("original staged journal changed under locks")
        next_found = {**record["found"], "stages": {
            **stages, name: {"state": phase, "pin": pin}}}
        return self._persist_record({**record, "found": next_found})

    def advance_found_config(self, phase: str, detail: dict,
                             sealed_plan: bytes, attest) -> dict:
        """Two durable original FD9 Config checkpoints, import-only.

        'found-config-saving' MUST fsync before the first native
        Config::save attempt; 'found-config-saved' requires a fresh native
        Config readback AND all-three-file proof under Config->P2 locks.
        The caller alone owns the original Config singleton, FD9 and P2.
        Config::save drops Config flock: release P2 BEFORE a new Config
        lock, then reacquire P2 after Config; never hold P2 while waiting
        for Config. Neither phase authorizes an engine or terminal state.
        """
        _validate_detail(detail)
        if (phase not in FOUND_CONFIG_PHASES or
                type(sealed_plan) is not bytes or
                not 0 < len(sealed_plan) <= MAX_FOUND_PLAN):
            raise SharedOperationError("invalid original found Config checkpoint")
        before = self.read()
        if (before is None or before["detail"] != detail or
                "found" not in before or
                FOUND_NEXT.get(before["phase"]) != phase or
                before["found"]["plan_sha256"] !=
                hashlib.sha256(sealed_plan).hexdigest()):
            raise SharedOperationError("found Config original state/plan mismatch")
        if not callable(attest) or attest(phase, sealed_plan) is not True:
            raise SharedOperationError("original Config/P2 save witness refused")
        if self.read() != before:
            raise SharedOperationError("original Config journal changed under locks")
        record = dict(before)
        record["phase"] = phase
        return self._persist_record(record)

    def record_found_rollback(self, record: dict, sealed_plan: bytes, *,
                              source: str | None = None, pin: dict | None = None,
                              complete: bool = False) -> dict:
        """Persist rollback intent and each before-inode pin under Config/P2."""
        if ("found" not in record or
                record["found"]["plan_sha256"] != hashlib.sha256(sealed_plan).hexdigest() or
                self.read() != record):
            raise SharedOperationError("original found rollback record changed")
        phase = record["phase"]
        if phase in FOUND_ROLLBACK_FROM and source is None and not complete:
            return self._persist_record({
                **record, "phase": FOUND_RESTORING,
                "found": {**record["found"], "restoring": {}},
            })
        if phase != FOUND_RESTORING:
            raise SharedOperationError("original found rollback phase mismatch")
        if complete and source is None:
            restored = dict(record)
            restored.pop("found")
            restored["phase"] = "restored"
            return self._persist_record(restored)
        if source not in record["found"]["stages"] or complete:
            raise SharedOperationError("source was not written by the found transaction")
        restoring = {**record["found"]["restoring"], source: pin}
        return self._persist_record({
            **record, "found": {**record["found"], "restoring": restoring},
        })

    def advance_found_runtime(self, phase: str, record: dict, sealed_plan: bytes, attest) -> dict:
        """Keep the file intent through the ordinary runtime/IPFW lifecycle."""
        if ("found" not in record or
                record["found"].get("runtime_mode") not in ("0", "1") or
                phase not in FOUND_RUNTIME_NEXT.get(record["phase"], set()) or
                record["found"]["plan_sha256"] != hashlib.sha256(sealed_plan).hexdigest() or
                self.read() != record or attest() is not True or self.read() != record):
            raise SharedOperationError("original found runtime transition refused")
        result = {**record, "phase": phase}
        if phase == "committed":
            result.pop("found")
        return self._persist_record(result)

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
            previous = committed_owner(before)
            if previous is not None and previous["id"] == detail["id"]:
                raise SharedOperationError("reused common Apply predecessor ID")
        else:
            if before is None or before["detail"] != detail:
                raise SharedOperationError("common Apply transaction identity changed")
            # Found-file physical WAL phases intentionally have no generic
            # NEXT table. Refuse them BEFORE any ordinary phase lookup: a
            # KeyError traceback must never substitute for the FD9 refusal.
            if "found" in before:
                raise SharedOperationError("found files require original durable transaction")
            if phase not in NEXT.get(before["phase"], frozenset()):
                raise SharedOperationError("illegal common Apply phase transition")
            # S10b1 never calls the launcher: a bound root must be freshly
            # attested by the actual S10b2 original owner BEFORE activating.
            # Ordinary legacy unbound Apply retains its established path.
            if phase == "activating" and "manifest" in before:
                raise SharedOperationError("immutable root preactivation gate not implemented")
            previous = before.get("previous")
        record = {"schema": SCHEMA, "phase": phase, "detail": detail}
        if previous is not None:
            record["previous"] = previous
        if before is not None and "found" in before:
            record["found"] = before["found"]
        if phase != "prepared" and before is not None and "manifest" in before:
            record["manifest"] = before["manifest"]
        return self._persist_record(record)

    def bind_prepared_manifest(self, generation: str, *,
                               effective, native, mode: str, enabled: bool,
                               shared_work_parent: Path | None = None) -> dict:
        """Pin S10a's already-staged root in THIS fsynced original FD9 WAL.

        No alternate journal/seal/config/launcher, no phase advance and no
        physical privilege. Genuine original S08/S09 inputs are required.
        Fixed production parent is shared_apply_seal.WORK; caller-supplied
        parent exists only for disposable protected unit/native fixtures.
        """
        from shared_apply_seal import WORK
        from voice_ipfw_adapter import require_lifecycle_lock
        from neutral_root_stage import (attest_staged_candidate,
                                        PreparedRootReceipt, RootStageRefused)
        try:
            require_lifecycle_lock()  # attests existing FreeBSD root FD9
        except (OSError, RuntimeError, ValueError):
            raise SharedOperationError("original FD9 required for root binding") from None
        if type(generation) is not str or not OP_ID.fullmatch(generation):
            raise SharedOperationError("invalid original root generation")
        work_parent = (WORK if shared_work_parent is None else shared_work_parent)
        if not isinstance(work_parent, Path):
            raise SharedOperationError("original shared-work parent required")
        before = self.read()
        if (before is None or before["phase"] != "prepared" or
                before["detail"]["id"] != generation or
                "found" in before or "manifest" in before):
            raise SharedOperationError("original PREPARED unbound journal required")
        args = dict(generation=generation, effective=effective, native=native,
                    mode=mode, enabled=enabled, parent=work_parent,
                    journal_root=self.root, owner_uid=self.owner)
        try:
            receipt = attest_staged_candidate(**args)
        except (RootStageRefused, OSError, ValueError):
            raise SharedOperationError("original staged root cannot be attested") from None
        if (type(receipt) is not PreparedRootReceipt or
                receipt.generation != generation or
                receipt.original_candidate_sha256 != before["detail"]["candidate"] or
                receipt.status != "ORIGINAL_PREPARED_ROOT_STAGED_ONLY" or
                receipt.authorization != "NONE" or
                receipt.physical_transition_allowed or receipt.promotion_allowed or
                receipt.reattest_under_original_fd9 is not True or
                any(type(value) is not str or not DIGEST.fullmatch(value)
                    for value in (receipt.root_sha256, receipt.original_seal_sha256))):
            raise SharedOperationError("original S10 root receipt refused")
        if self.read() != before:
            raise SharedOperationError("original journal changed during root binding")
        root = {"schema": 1, "generation": generation,
                "root_sha256": receipt.root_sha256,
                "seal_sha256": receipt.original_seal_sha256,
                "candidate_sha256": receipt.original_candidate_sha256}
        _validate_manifest_binding(root, before["detail"])
        result = dict(before)
        result["manifest"] = root
        # The ONE original fsynced atomic operation.json writer. If fsync
        # succeeds but postread fails, leave PREPARED bound, NEVER roll back
        # or mark a physical generation COMMITTED here.
        self._persist_record(result)
        try:
            rechecked = attest_staged_candidate(**args)
        except (RootStageRefused, OSError, ValueError):
            raise SharedOperationError("post-bind S10 root reattestation refused") from None
        if rechecked != receipt or self.read() != result:
            raise SharedOperationError("original immutable root changed after binding")
        return result

    def revert_committed_remove(self, trial_id: str, old_id: str, attest) -> dict:
        """Return to the EXACT saved predecessor after a committed Remove trial.

        No new journal or Config writer. Only an unchanged native common
        candidate (same saved Config hash, zero changed fields) may use this
        transition. The FD9 shell must have restored the old sealed release,
        native process, and scoped IPFW before supplying a positive attest.
        """
        before = self.read()
        if before is None or before["phase"] != "committed":
            raise SharedOperationError("no committed Remove trial to revert")
        trial, old = before["detail"], before.get("previous")
        if not isinstance(old, dict) or trial["id"] != trial_id or old["id"] != old_id:
            raise SharedOperationError("Remove trial or predecessor identity mismatch")
        if (trial["page"] != "strategies" or trial["changed_fields"] or
                trial["base"] != old["candidate"] or
                trial["candidate"] != old["candidate"]):
            raise SharedOperationError("Remove trial altered saved Config")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("previous native owner is not attested")
        if self.read() != before:
            raise SharedOperationError("common Apply owner changed during Remove rollback")
        restored = dict(before)
        restored["phase"] = "restored"
        return self._persist_record(restored)

    def record_early_start_failure(self, operation_id: str, cause: str) -> dict:
        """Original FD9 Apply only: the real launcher could not prove readiness.

        No child wait status is obtained from daemon(8); this never asserts
        that the process exited, nor exposes stderr/arguments or private logs.
        """
        if (type(operation_id) is not str or not OP_ID.fullmatch(operation_id) or
                type(cause) is not str or cause not in EARLY_START_CAUSES):
            raise SharedOperationError("invalid original early-start receipt")
        before = self.read()
        if (before is None or before["phase"] != "requires-review" or
                before["detail"]["id"] != operation_id or "found" in before):
            raise SharedOperationError("original early-start owner changed")
        if "failure" in before:
            if (before["failure"]["code"] == "ENGINE_START_UNVERIFIED" and
                    before["failure"]["cause"] == cause):
                return before
            raise SharedOperationError("original early-start event conflict")
        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        event = {"schema": 1, "code": "ENGINE_START_UNVERIFIED",
                 "action": "engine-start", "operation_id": operation_id,
                 "observed_at": at, "exit_status": None, "cause": cause}
        if self.read() != before:
            raise SharedOperationError("original early-start journal raced")
        return self._persist_record({**before, "failure": event})

    def record_ipfw_attach_failure(self, operation_id: str, cause: str) -> dict:
        """Original held FD9 only, after native IPFW and previous runtime restoration."""
        if (type(operation_id) is not str or not OP_ID.fullmatch(operation_id) or
                type(cause) is not str or cause not in IPFW_ATTACH_CAUSES):
            raise SharedOperationError("invalid original IPFW attach receipt")
        before = self.read()
        if (before is None or before["phase"] != "requires-review" or
                before["detail"]["id"] != operation_id or "found" in before):
            raise SharedOperationError("original IPFW attach owner changed")
        if "failure" in before:
            if (before["failure"]["code"] == "IPFW_ATTACH_FAILED" and
                    before["failure"]["cause"] == cause):
                return before
            raise SharedOperationError("original IPFW attach event conflict")
        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        event = {"schema": 1, "code": "IPFW_ATTACH_FAILED",
                 "action": "ipfw-attach", "operation_id": operation_id,
                 "observed_at": at, "exit_status": None, "cause": cause}
        if self.read() != before:
            raise SharedOperationError("original IPFW attach journal raced")
        return self._persist_record({**before, "failure": event})

    def record_runtime_exit(self, operation_id: str) -> dict:
        """Original FD9 owner only: persist a *verified post-ready absence*.

        Caller already proved exact old PID, sealed release, scoped IPFW
        ownership, and completed the original Stop before this commit.
        The journal cannot infer a signal, engine exit code or raw stderr.
        """
        if type(operation_id) is not str or not OP_ID.fullmatch(operation_id):
            raise SharedOperationError("invalid original runtime failure ID")
        before = self.read()
        if (before is None or before["phase"] != "committed" or
                before["detail"]["id"] != operation_id):
            raise SharedOperationError("original runtime failure owner changed")
        if "failure" in before:
            return before  # duplicate callback never overwrites the first event
        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        event = {"schema": 1, "code": "ENGINE_EXIT_AFTER_READY",
                 "action": "runtime-failure", "operation_id": operation_id,
                 "observed_at": at, "exit_status": None}
        if self.read() != before:
            raise SharedOperationError("original runtime failure journal raced")
        return self._persist_record({**before, "failure": event})

    def clear_runtime_exit(self, operation_id: str) -> dict:
        """Only after original FD9 boot has verified the new RUNNING owner."""
        if type(operation_id) is not str or not OP_ID.fullmatch(operation_id):
            raise SharedOperationError("invalid original running owner ID")
        before = self.read()
        if (before is None or before["phase"] != "committed" or
                before["detail"]["id"] != operation_id):
            raise SharedOperationError("original runtime success owner changed")
        if "failure" not in before:
            return before
        if self.read() != before:
            raise SharedOperationError("original runtime success journal raced")
        restored = dict(before)
        del restored["failure"]
        return self._persist_record(restored)

    def _persist_record(self, record: dict) -> dict:
        """One fsynced atomic journal writer for shared Apply."""
        _validate_record(record)
        detail = record["detail"]
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

    def finish_found_prepared_pristine(
        self, identity: str, sealed_plan: bytes, attest
    ) -> dict:
        """Close ONLY an attested original found PREPARED no-mutation crash.

        The trusted original FD9 owner must keep the native Config→P2
        critical section and independently verify: the original seal,
        exact *current* Config base, all three unchanged physical before
        inodes and known-source provenance, plus the actual previous
        runtime/process/IPFW owner (or proven initial no-owner state).
        This journal helper cannot itself supply or weaken that proof.
        It deliberately has NO CLI, GUI route or automatic boot caller.
        Found FILES-WRITING and every later phase remain nonterminal.
        """
        if (not isinstance(identity, str) or not OP_ID.fullmatch(identity) or
                type(sealed_plan) is not bytes or
                not 0 < len(sealed_plan) <= MAX_FOUND_PLAN):
            raise SharedOperationError("invalid original found pristine recovery")
        record = self.read()
        if (record is None or record["phase"] != "prepared" or
                "found" not in record or record["detail"]["id"] != identity or
                record["found"]["plan_sha256"] !=
                hashlib.sha256(sealed_plan).hexdigest()):
            raise SharedOperationError("found pristine recovery phase/plan mismatch")
        detail = record["detail"]
        prior = record.get("previous")
        if prior is not None and prior["candidate"] != detail["base"]:
            raise SharedOperationError("found pristine predecessor not Config base")
        try:
            plan = json.loads(sealed_plan)
            found_intent = plan["found_intent"]
            batch = plan["found_batch"]
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            raise SharedOperationError("found pristine sealed plan unreadable") from exc
        if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
                plan.get("result") != "prepared" or
                plan.get("dependencies") != detail["base"] or
                plan.get("changed_fields") != detail["changed_fields"] or
                not isinstance(found_intent, dict) or
                found_intent.get("config_revision") != detail["base"] or
                found_intent.get("commit_authorized") is not False or
                not isinstance(batch, dict) or
                list(batch) != list(FOUND_NAMES) or
                any(not isinstance(batch[name], dict) for name in FOUND_NAMES)):
            raise SharedOperationError("found pristine sealed plan mismatches journal")
        if not callable(attest) or attest(sealed_plan, prior) is not True:
            raise SharedOperationError("original found pristine Config/P2/runtime refused")
        if self.read() != record:
            raise SharedOperationError("found pristine journal changed under original locks")
        # Drop the uncommitted found intent ONLY after all original no-write
        # attestations have succeeded; generic restored cannot carry it.
        completed = {"schema": SCHEMA, "phase": "restored", "detail": detail}
        if prior is not None:
            completed["previous"] = prior
        return self._persist_record(completed)

    def recover_prepared(self, identity: str, attest) -> dict:
        """Only PREPARED can be closed without touching runtime/Config/IPFW.

        The journal write precedes the mutating transition; an executor can
        never change kernel/processes until the durable 'activating' fsync
        has returned. The same FD9 is held across witness and closure.
        """
        record = self.read()
        if record is None or record["phase"] != "prepared" or \
           record["detail"]["id"] != identity or "found" in record:
            # The legacy seal-only attestation is NOT proof that three
            # physical sources remained untouched after an interrupted
            # found transaction. Do not grant cold recovery by old rules.
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

    def finish_saved_remove_restore(self, identity: str, previous_id: str, attest,
                                   state: Path = Path("/var/db/zapret2-restyle/extra-resources")) -> dict:
        """Close only a fully attested unchanged-Config Remove cold rollback.

        The ordinary Config-saved transition can ONLY commit the new owner.
        This special transition is not in NEXT, so generic 'record restored'
        cannot turn an ordinary post-save Apply into an old-owner rollback.
        The original root FD9 must first prove the prior sealed runtime,
        kernel and exact saved Config; no Config save or new journal occurs.
        """
        before = self.read()
        if before is None or before["phase"] != "config-saved":
            raise SharedOperationError("no config-saved Remove trial to restore")
        proof = native_remove_prepared_trial(self.root, state)
        if (proof is None or proof["phase"] != "config-saved" or
                proof["id"] != identity or proof["old"]["id"] != previous_id):
            raise SharedOperationError("foreign or changed saved Remove predecessor")
        old = before.get("previous")
        trial = before["detail"]
        if (not isinstance(old, dict) or trial["id"] != identity or
                old["id"] != previous_id or trial["page"] != "strategies" or
                trial["changed_fields"] or trial["base"] != old["candidate"] or
                trial["candidate"] != old["candidate"] or
                any(old[k] != proof["old"][k] for k in ("id", "page", "candidate"))):
            raise SharedOperationError("saved Remove altered Config or predecessor")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("saved Remove old runtime not attested")
        if self.read() != before:
            raise SharedOperationError("saved Remove journal changed during rollback")
        restored = dict(before)
        restored["phase"] = "restored"
        return self._persist_record(restored)

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


    def reviewed_legacy_detail(self) -> dict:
        """Inspect exactly one failed FIRST Voice handoff from Strategies."""
        record = self.read()
        if record is None or record["phase"] != "requires-review" or \
                "previous" in record or record["detail"]["page"] != "voice":
            raise SharedOperationError("not an initial reviewed Voice handoff")
        return record["detail"]


    def reviewed_native_detail(self) -> dict:
        """Only a failed in-place Strategies auto transition may be reviewed.

        The former journal phase is lost in requires-review, so this does NOT
        assume Config was saved, IPFW committed or an epoch completed.
        Those independent facts must be proved by the original FD9 service.
        """
        record = self.read()
        if record is None or record["phase"] != "requires-review":
            raise SharedOperationError("no reviewed native generation")
        current, previous = record["detail"], record.get("previous")
        if (not isinstance(previous, dict) or
                current["page"] != "strategies" or
                current["changed_fields"] != ["hostlist.mode"] or
                current["base"] != previous["candidate"] or
                current["candidate"] == current["base"]):
            raise SharedOperationError("foreign reviewed native operation")
        return current

    def finish_reviewed_native(self, identity: str, attest) -> dict:
        """Finish only an independently proved existing live generation.

        No generic requires-review transition is added to NEXT. The callback
        must re-attest original FD9, the saved Config, committed IPFW and a
        complete real pretraffic/epoch/engine receipt before journal write.
        """
        detail = self.reviewed_native_detail()
        before = self.read()
        if detail["id"] != identity:
            raise SharedOperationError("reviewed native operation ID differs")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("reviewed native generation not attested")
        if self.read() != before:
            raise SharedOperationError("reviewed native operation changed")
        result = dict(before)
        result["phase"] = "committed"
        return self._persist_record(result)

    def finish_reviewed_legacy(self, identity: str, attest) -> dict:
        """Terminalize only a fully attested old Strategies runtime.

        The FD9 service checks the saved Config, old root-owned release,
        scoped kernel rules/tables, exact engine PID and live supervisor
        both before and after reattaching its monitor.
        """
        detail = self.reviewed_legacy_detail()
        before = self.read()
        if detail["id"] != identity:
            raise SharedOperationError("reviewed Voice operation ID differs")
        if not callable(attest) or attest() is not True:
            raise SharedOperationError("reviewed legacy attestation refused")
        if self.read() != before:
            raise SharedOperationError("reviewed legacy record changed")
        return self._persist_record({"schema": SCHEMA, "phase": "restored",
                                     "detail": detail})

    def advisory(self) -> dict:
        record = self.read()
        if record is None or record["phase"] in TERMINAL:
            return {"state": "clear", "safe_to_mutate": True}
        return {
            "state": "blocked", "reason": "shared-apply-pending",
            "phase": record["phase"], "safe_to_mutate": False,
        }


def native_remove_prepared_trial(root: Path = DEFAULT_ROOT,
                                 state: Path = Path("/var/db/zapret2-restyle/extra-resources")) -> dict | None:
    """Bind exact old owner for Remove's pre-save cold rollback phases.

    The existing resource journal MUST own the unchanged trial. This only
    authorizes inspection of PREPARED/ACTIVATING/ACTIVATED; the original
    root-FD9 service and common Apply recovery perform all native release,
    process, IPFW and phase-specific verification before any mutation.
    Returning None for other phases never authorizes generic Stop.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from extra_resources_transaction import (
        _load_journal, _safe_state, _validate_native_owner,
    )
    _safe_state(state)
    resource = _load_journal(state / "transaction")
    if (resource.get("mode") != "remove" or
            resource.get("phase") != "restarting" or
            not resource.get("previous") or resource.get("incoming") != {}):
        raise SharedOperationError("no quarantined Remove recovery journal")
    owner = _validate_native_owner(resource.get("native_owner"))
    record = SharedApplyOperation(root).read()
    if record is None:
        raise SharedOperationError("native common journal absent during Remove")
    if record["phase"] not in ("prepared", "activating", "activated", "config-saved"):
        return None
    trial = record["detail"]
    previous = record.get("previous")
    if (not isinstance(previous, dict) or
            any(previous[k] != owner[k] for k in ("id", "page", "candidate")) or
            trial["page"] != "strategies" or trial["changed_fields"] or
            trial["id"] == owner["id"] or
            trial["base"] != owner["candidate"] or
            trial["candidate"] != owner["candidate"]):
        raise SharedOperationError("foreign or changed native Remove pre-save owner")
    return {"id": trial["id"], "phase": record["phase"], "old": owner}


def native_remove_trial_context(root: Path = DEFAULT_ROOT,
                                state: Path = Path("/var/db/zapret2-restyle/extra-resources")) -> dict:
    """Attest exact old owner still committed before a fresh trial starts.

    The resource journal is already in its durable restarting phase after
    quarantine, and the sole shared journal still owns the saved previous
    native common release. No new resource/XML interpreter or second WAL.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from extra_resources_transaction import (
        _load_journal, _safe_state, _validate_native_owner,
    )
    _safe_state(state)
    resource = _load_journal(state / "transaction")
    if (resource.get("mode") != "remove" or
            resource.get("phase") != "restarting" or
            not resource.get("previous") or resource.get("incoming") != {}):
        raise SharedOperationError("no prepared, quarantined native Remove trial")
    old = _validate_native_owner(resource.get("native_owner"))
    record = SharedApplyOperation(root).read()
    current = committed_owner(record) if record and record["phase"] in TERMINAL else None
    if current is None or any(current[k] != old[k] for k in ("id", "page", "candidate")):
        raise SharedOperationError("saved previous common owner changed before trial")
    return old


def native_remove_rollback_pair(root: Path = DEFAULT_ROOT,
                                state: Path = Path("/var/db/zapret2-restyle/extra-resources")) -> dict:
    """Require the original durable resource witness and exact Apply journal.

    Return only an unchanged Config common trial or the still-original old
    owner. No PID/argument guessing and no interpretation of user strategy.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from extra_resources_transaction import (
        _load_journal, _safe_state, _validate_native_owner,
    )

    _safe_state(state)
    resource = _load_journal(state / "transaction")
    if (resource.get("mode") != "remove" or not resource.get("previous") or
            resource.get("incoming") != {}):

        raise SharedOperationError("no pending Remove resource transaction")
    owner = _validate_native_owner(resource.get("native_owner"))
    record = SharedApplyOperation(root).read()
    current = committed_owner(record) if record and record["phase"] in TERMINAL else None
    if current and all(current[key] == owner[key] for key in ("id", "page", "candidate")):
        return {"state": "old", "old": owner, "trial": None}
    if record is None or record["phase"] != "committed" or "previous" not in record:
        raise SharedOperationError("Remove common owner is incomplete")
    old, trial = record["previous"], record["detail"]
    if (any(old[key] != owner[key] for key in ("id", "page", "candidate")) or
            trial["page"] != "strategies" or trial["changed_fields"] or
            trial["base"] != old["candidate"] or
            trial["candidate"] != old["candidate"]):
        raise SharedOperationError("Remove common predecessor or unchanged Config mismatch")
    if resource["phase"] not in ("restarting", "completed"):
        raise SharedOperationError("resource transaction did not reach native trial")
    return {"state": "trial", "old": owner, "trial": trial["id"]}


def native_lifecycle_gate(action: str | None = None, *,
                          root: Path = DEFAULT_ROOT) -> dict:
    """Read-only FD9 policy from the ONE current shared Apply journal.

    Old Telegram cutover roots are not a runtime ownership authority. Only
    a trusted common record may block/authorize this gate. Caller still
    verifies Config, processes, release seal and native IPFW independently.
    """
    exceptions = {
        "common-apply": None,
        "common-recover-saved": "config-saved",
        "common-recover-activating": "activating",
        "common-recover-activated": "activated",
        "common-recover-reviewed-legacy": "requires-review",
        "common-recover-reviewed-native": "requires-review",
        "strategy-lab-native": "committed",
    }
    if action is not None and action not in exceptions:
        raise SharedOperationError("invalid native lifecycle gate action")
    record = SharedApplyOperation(root).read()
    if record is None:
        return {"state": "clear", "safe_to_mutate": True}
    phase = record["phase"]
    if action == "strategy-lab-native":
        if phase in TERMINAL and committed_owner(record) is not None:
            # RESTORED with a sealed predecessor is still a native common
            # owner, not an invitation to run the legacy service.
            return {"state": "clear", "safe_to_mutate": True}
        return {"state": "blocked", "reason": "strategy-lab-requires-committed-native-owner",
                "phase": phase, "safe_to_mutate": False}
    if action is None and committed_owner(record) is not None:
        return {"state": "blocked", "reason": "shared-runtime-owned",
                "phase": phase, "safe_to_mutate": False}
    if phase in TERMINAL or (
        "found" not in record and action is not None and exceptions[action] == phase
    ):
        return {"state": "clear", "safe_to_mutate": True}
    return {"state": "blocked", "reason": "shared-apply-pending",
            "phase": phase, "safe_to_mutate": False}


def main(argv: list[str]) -> int:
    inspection = len(argv) == 2 and argv[1] == "inspect"
    found_pending = len(argv) == 2 and argv[1] == "found-pending"
    native_gate_request = len(argv) in (2, 3) and argv[1] == "native-gate" and (
        len(argv) == 2 or argv[2] in (
            "common-apply", "common-recover-saved",
            "common-recover-activating", "common-recover-activated",
            "common-recover-reviewed-legacy",
            "common-recover-reviewed-native", "strategy-lab-native",
        )
    )
    owner_witness = len(argv) == 2 and argv[1] == "owner-witness"
    remove_prepared_context = len(argv) == 2 and argv[1] == "remove-prepared-context"
    remove_trial_context = len(argv) == 2 and argv[1] == "remove-trial-context"
    remove_pair = len(argv) == 2 and argv[1] == "remove-rollback-pair"
    remove_revert = len(argv) == 4 and argv[1] == "remove-revert-committed" and all(
        OP_ID.fullmatch(value) for value in argv[2:]
    )
    review = len(argv) == 2 and argv[1] == "review-legacy"
    review_native = len(argv) == 2 and argv[1] == "review-native"
    finish_review_native = (len(argv) == 3 and argv[1] == "finish-reviewed-native" and
                            bool(OP_ID.fullmatch(argv[2])))
    finish_review = len(argv) == 3 and argv[1] == "finish-reviewed-legacy" and bool(OP_ID.fullmatch(argv[2]))
    early_start = (len(argv) == 4 and argv[1] == "record-early-start" and
                   bool(OP_ID.fullmatch(argv[2])) and argv[3] in EARLY_START_CAUSES)
    ipfw_attach = (len(argv) == 4 and argv[1] == "record-ipfw-attach" and
                   bool(OP_ID.fullmatch(argv[2])) and argv[3] in IPFW_ATTACH_CAUSES)
    runtime_record = (len(argv) == 3 and argv[1] == "runtime-exit-record" and
                      bool(OP_ID.fullmatch(argv[2])))
    runtime_clear = (len(argv) == 3 and argv[1] == "runtime-exit-clear" and
                     bool(OP_ID.fullmatch(argv[2])))
    recording = len(argv) == 8 and argv[1] == "record"
    recovery = len(argv) == 3 and argv[1] == "recover-prepared" and bool(OP_ID.fullmatch(argv[2]))
    finish = len(argv) == 3 and argv[1] == "finish-saved" and bool(OP_ID.fullmatch(argv[2]))
    pristine = len(argv) == 4 and argv[1] == "recover-activating" and all(
        OP_ID.fullmatch(value) for value in argv[2:]
    )
    cold_restore = len(argv) == 4 and argv[1] in (
        "finish-activated", "finish-activating", "finish-remove-saved"
    ) and all(OP_ID.fullmatch(value) for value in argv[2:])
    if not (inspection or found_pending or owner_witness or remove_prepared_context or remove_trial_context or remove_pair or remove_revert or review or finish_review or review_native or finish_review_native or recording or early_start or ipfw_attach or runtime_record or runtime_clear or recovery or finish or pristine or cold_restore or native_gate_request):
        print("usage: shared_apply_operation.py inspect|record PHASE ID PAGE BASE CANDIDATE FIELDS",
              file=sys.stderr)
        return 64
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        if runtime_record or runtime_clear:
            # The original FD9 alone is insufficient to invent an event.
            # Reuse the existing sealed Common/kernel/process inspector
            # immediately before the original journal writer. No PID matcher.
            from voice_live_inspect import examine_shared
            store = SharedApplyOperation(owner=0)
            original = store.read()
            observed = examine_shared(original)
            expected = "stopped" if runtime_record else "ready"
            if (original is None or original["phase"] != "committed" or
                    original["detail"]["id"] != argv[2] or
                    type(observed) is not dict or
                    observed.get("source") != "native-common" or
                    observed.get("state") != expected):
                raise SharedOperationError("original runtime receipt missing live owner proof")
            if runtime_record:
                store.record_runtime_exit(argv[2])
                print("original-runtime-exit=recorded")
            else:
                store.clear_runtime_exit(argv[2])
                print("original-runtime-exit=cleared")
        elif early_start:
            # Original held FD9 and exact requires-review operation; no
            # independent error database or event writer is created.
            SharedApplyOperation(owner=0).record_early_start_failure(argv[2], argv[3])
            print("original-engine-start=unverified")
        elif ipfw_attach:
            SharedApplyOperation(owner=0).record_ipfw_attach_failure(argv[2], argv[3])
            print("original-ipfw-attach=refused")
        elif found_pending:
            record = SharedApplyOperation().read()
            if record is not None and "found" in record:
                print(record["detail"]["id"])
        elif native_gate_request:
            action = argv[2] if len(argv) == 3 else None
            state = native_lifecycle_gate(action)
            if not state["safe_to_mutate"]:
                raise SharedOperationError("native common lifecycle gate blocked: " +
                                           state["reason"])
        elif remove_prepared_context:
            if (os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1" or
                    os.environ.get("EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE") != "1"):
                raise SharedOperationError("missing original Remove recovery owner")
            proof = native_remove_prepared_trial()
            if proof is None:
                print("remove-prepared none")
            else:
                old = proof["old"]
                print("remove-prepared " + proof["phase"] + " " + proof["id"] + " " + old["id"] +
                      " " + old["page"] + " " + old["candidate"])
        elif remove_trial_context:
            if (os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1" or
                    os.environ.get("EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL") != "1"):
                raise SharedOperationError("missing native Remove trial owner")
            old = native_remove_trial_context()
            print("remove-trial-owner " + old["id"] + " " + old["page"] +
                  " " + old["candidate"])
        elif remove_pair:
            if (os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1" or
                    os.environ.get("EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE") != "1"):
                raise SharedOperationError("missing native Remove recovery owner")
            proof = native_remove_rollback_pair()
            print("remove-rollback " + proof["state"] + " " + proof["old"]["id"] +
                  " " + proof["old"]["page"] + " " + proof["old"]["candidate"] +
                  " " + (proof["trial"] or "-"))
        elif remove_revert:
            if (os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1" or
                    os.environ.get("EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE") != "1"):
                raise SharedOperationError("missing native Remove recovery owner")
            proof = native_remove_rollback_pair()
            if proof["state"] != "trial" or proof["trial"] != argv[2] or proof["old"]["id"] != argv[3]:
                raise SharedOperationError("unexpected native Remove rollback pair")
            from shared_apply_seal import verify_seal, WORK
            j = SharedApplyOperation(owner=0)
            j.revert_committed_remove(argv[2], argv[3], lambda: bool(
                verify_seal(WORK / argv[2], owner=0) and
                verify_seal(WORK / argv[3], owner=0)
            ))
            print("remove-owner-restored")
        elif owner_witness:
            proof = native_committed_owner_witness()
            print("owner-witness " + proof["id"] + " " + proof["page"] +
                  " " + proof["candidate"])
        elif review:
            detail = SharedApplyOperation(owner=0).reviewed_legacy_detail()
            print("review-legacy " + detail["id"] + " " + detail["base"] +
                  " " + detail["candidate"])
        elif review_native:
            detail = SharedApplyOperation(owner=0).reviewed_native_detail()
            print("review-native " + detail["id"] + " " + detail["page"] +
                  " " + detail["base"] + " " + detail["candidate"])
        elif finish_review_native:
            # Original FD9 service has JUST rechecked Config/active tree/IPFW.
            # The terminal writer independently re-attests the real original
            # live process and the immutable pretraffic-derived epoch receipt.
            from auto_detect_owner import attest_reviewed_native_generation
            from auto_detect_epoch_receipts import EpochReceipts
            from shared_apply_seal import verify_seal, WORK
            def exact_native_receipt() -> bool:
                proof = attest_reviewed_native_generation(argv[2])
                verify_seal(WORK / argv[2], owner=0)
                EpochReceipts()._epoch(proof)
                return attest_reviewed_native_generation(argv[2]) == proof
            SharedApplyOperation(owner=0).finish_reviewed_native(
                argv[2], exact_native_receipt)
            print("reviewed-native-committed")
        elif finish_review:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            store.finish_reviewed_legacy(
                argv[2], lambda: bool(verify_seal(WORK / argv[2], owner=0)))
            print("reviewed-legacy-restored")
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
                print(record["phase"] + " " + detail["id"] + " " + detail["page"])
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
            if argv[1] == "finish-remove-saved":
                if (os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1" or
                        os.environ.get("EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE") != "1"):
                    raise SharedOperationError("missing original saved Remove recovery owner")
                finish_cold = store.finish_saved_remove_restore
            elif argv[1] == "finish-activated":
                finish_cold = store.finish_activated_restore
            else:
                finish_cold = store.finish_activating_installed_restore
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
