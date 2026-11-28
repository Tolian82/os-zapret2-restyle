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
MANAGED_WRITING = "managed-writing"
MANAGED_CONFIG_SAVING = "managed-config-saving"
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
    "found-config-saving", "found-config-saved", FOUND_RESTORING, MANAGED_WRITING,
    MANAGED_CONFIG_SAVING,
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


def _config_save_witness(detail: dict, plan_sha256: str) -> str:
    proof = "\0".join((detail["page"], detail["base"], detail["candidate"],
                       plan_sha256, ",".join(detail["changed_fields"])))
    return hashlib.sha256(proof.encode("ascii")).hexdigest()


def _config_observation_witness(detail: dict, plan_sha256: str, observed: str) -> str:
    proof = _config_save_witness(detail, plan_sha256) + "\0" + observed
    return hashlib.sha256(proof.encode("ascii")).hexdigest()


def _managed_restore_has_base(record: dict, saved_base: str | None) -> bool:
    return (record.get("phase") == MANAGED_CONFIG_SAVING and
            saved_base == record["detail"]["base"] and saved_base != record["detail"]["candidate"])



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
            type(binding["schema"]) is not int or binding["schema"] not in (1, 2) or
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
        _validate_stage_pin(row["pin"])
    return stages


def _validate_stage_pin(pin: object) -> None:
    fields = {"device", "inode", "mtime_ns", "size", "sha256"}
    if not isinstance(pin, dict) or set(pin) not in (fields, fields | {"temp"}) or \
            any(type(pin[k]) is not int or pin[k] <= 0
                for k in ("device", "inode", "mtime_ns")) or \
            type(pin["size"]) is not int or pin["size"] < 0 or \
            type(pin["sha256"]) is not str or not DIGEST.fullmatch(pin["sha256"]):
        raise SharedOperationError("invalid staged inode pin")
    if "temp" in pin and (not isinstance(pin["temp"], str) or not re.fullmatch(
            r"\.auto-(?:detect|hostlist)-[a-f0-9]{32}\.tmp", pin["temp"])):
        raise SharedOperationError("invalid staged temporary filename")


_MANAGED_BASE = {"name", "before_sha256", "after_sha256", "before_identity"}


def _validate_managed_write(record: dict) -> None:
    from neutral_effective_diff import _REF_FILE

    row = record["managed"]
    if (set(record) != {"schema", "phase", "detail", "previous", "manifest",
                        "previous_manifest", "managed"} or
            record["detail"]["page"] != "strategies" or
            record["previous"]["candidate"] != record["detail"]["base"] or
            record["manifest"]["schema"] != 1 or record["previous_manifest"]["schema"] != 1 or
            type(row) is not dict or not _MANAGED_BASE <= row.keys() or
            row.keys() - _MANAGED_BASE - {"ready", "barrier", "installed", "restore", "running_sha256"} or
            type(row["name"]) is not str or not _REF_FILE.fullmatch(row["name"]) or
            any(type(row[k]) is not str or not DIGEST.fullmatch(row[k])
                for k in ("before_sha256", "after_sha256")) or
            row["before_sha256"] == row["after_sha256"] or
            ("ready" not in row and ("installed" in row or "restore" in row))):
        raise SharedOperationError("invalid original managed write intent")
    if "running_sha256" in row and (type(row["running_sha256"]) is not str or
                                    not DIGEST.fullmatch(row["running_sha256"])):
        raise SharedOperationError("invalid managed running owner digest")
    if (record["phase"] == MANAGED_CONFIG_SAVING and
            not {"running_sha256", "installed"} <= row.keys()):
        raise SharedOperationError("managed Config save lacks installed owner")
    if (record["phase"] == MANAGED_CONFIG_SAVING and "restore" in row and
            record["detail"]["base"] == record["detail"]["candidate"]):
        raise SharedOperationError("managed Config restore requires distinct base image")
    for key in ("before_identity", "installed"):
        if key not in row:
            continue
        identity = row[key]
        if (type(identity) is not list or len(identity) != 9 or
                any(type(n) is not int or n < 0 for n in identity) or
                not identity[1] or identity[8] != 1 or not stat.S_ISREG(identity[5]) or
                identity[5] & 0o022):
            raise SharedOperationError("invalid managed file identity")
    for key, digest in (("ready", "after_sha256"), ("restore", "before_sha256")):
        if key in row:
            pin = row[key]
            _validate_stage_pin(pin)
            if (not pin.get("temp", "").startswith(".auto-detect-") or
                    pin["sha256"] != row[digest]):
                raise SharedOperationError("invalid managed file checkpoint")
    if "barrier" in row:
        from managed_inode_barrier import ManagedBarrierRefused, _validate_pin
        if "ready" not in row:
            raise SharedOperationError("managed barrier requires original ready WAL")
        try:
            _validate_pin(row["barrier"], row["ready"]["temp"])
        except ManagedBarrierRefused as exc:
            raise SharedOperationError("invalid managed scratch inode pin") from exc
    if "ready" in row and [row["ready"]["device"], row["ready"]["inode"]] == row["before_identity"][:2]:
        raise SharedOperationError("managed staged inode aliases the preimage")
    if "restore" in row and row["restore"]["temp"] == row["ready"]["temp"]:
        raise SharedOperationError("managed restore aliases the forward temporary name")
    if "installed" in row:
        if "barrier" not in row:
            raise SharedOperationError("managed installed inode lacks scratch WAL proof")
        installed = row["installed"]
        ready = row["ready"]
        if ([installed[i] for i in (0, 1, 3, 4)] !=
                [ready[k] for k in ("device", "inode", "mtime_ns", "size")] or
                installed[5:] != row["before_identity"][5:]):
            raise SharedOperationError("managed installed inode differs from ready")


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


def _first_running_pin_scope(record: dict) -> bool:
    return ("previous" not in record and "previous_manifest" not in record and
            "found" not in record and record.get("manifest", {}).get("schema") in (1, 2))


def _validate_first_running_pin(record: dict) -> None:
    has_running = "first_running_sha256" in record
    has_seed = "first_pretraffic_sha256" in record
    if not has_running and not has_seed:
        return
    learning = record.get("manifest", {}).get("schema") == 2
    phases = ("activated", "epoch-finalizing", "committed", "restored") if learning else (
        "activated", "config-saved", "committed", "restored")
    if (not _first_running_pin_scope(record) or record["phase"] not in phases or
            not has_running or has_seed != learning or
            any(type(record[key]) is not str or not DIGEST.fullmatch(record[key])
                for key in ("first_running_sha256", "first_pretraffic_sha256") if key in record)):
        raise SharedOperationError("invalid first bound running owner pin")


def _first_running_pin_matches(record: dict, running, config_fd: int, *,
                               pretraffic_sha256: str | None = None) -> bool:
    if not _first_running_pin_scope(record):
        return "first_running_sha256" not in record and "first_pretraffic_sha256" not in record
    learning = record["manifest"]["schema"] == 2
    if running is None:
        return (not learning and "first_running_sha256" not in record and
                "first_pretraffic_sha256" not in record and pretraffic_sha256 is None)
    pinned = record.get("first_running_sha256")
    if (pinned is None or (learning and (pretraffic_sha256 is None or
            pretraffic_sha256 != record.get("first_pretraffic_sha256"))) or
            (not learning and (pretraffic_sha256 is not None or "first_pretraffic_sha256" in record))):
        return False
    _validate_first_running_pin(record)
    from neutral_schema3_quiescent_preimage import _first_running_digest
    from shared_apply_seal import WORK
    return pinned == _first_running_digest(WORK / record["detail"]["id"] / "release",
                                           running, config_fd=config_fd)


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
            (keys - {"failure", "manifest", "previous_manifest", "managed", "first_running_sha256",
                     "first_pretraffic_sha256", "first_retry_archive"}) not in allowed or
            ("failure" in record and (record.get("phase") not in
                                      ("committed", "requires-review") or
                                      "found" in record)) or
            type(record["schema"]) is not int or record["schema"] != SCHEMA or
            record["phase"] not in PHASES):
        raise SharedOperationError("invalid common Apply record")
    _validate_detail(record["detail"])
    if "manifest" in record:
        _validate_manifest_binding(record["manifest"], record["detail"])
    if "first_retry_archive" in record:
        history = record["first_retry_archive"]
        detail = record["detail"]
        if (type(history) is not dict or set(history) != {"id", "sha256"} or
                type(history["id"]) is not str or not OP_ID.fullmatch(history["id"]) or
                history["id"] == detail["id"] or
                type(history["sha256"]) is not str or not DIGEST.fullmatch(history["sha256"]) or
                detail["page"] != "strategies" or detail["base"] == detail["candidate"] or
                "general.enabled" not in detail["changed_fields"] or
                {"previous", "previous_manifest", "found", "managed"} & keys or
                ("manifest" in record and record["manifest"].get("schema") != 2) or
                record["phase"] not in ("prepared", "activating", "activated", "epoch-finalizing",
                                        "committed", "restored", "restore-failed", "requires-review")):
            raise SharedOperationError("invalid original first retry archive provenance")
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
    if "previous_manifest" in record:
        if "previous" not in record:
            raise SharedOperationError("invalid original predecessor root pin")
        _validate_manifest_binding(record["previous_manifest"], record["previous"])
        if "found" in record and (
                record["previous"]["candidate"] != record["detail"]["base"] or
                (record["phase"] != "prepared" and "manifest" not in record)):
            raise SharedOperationError("pinned found cannot mutate before candidate binding")
        if ("manifest" not in record and
                record["phase"] not in ("prepared", "restored")):
            raise SharedOperationError("unbound successor of immutable root")
    if "found" in record and "manifest" in record:
        if record["phase"] in FOUND_RUNTIME_PHASES:
            raise SharedOperationError("bound Found runtime witness not integrated")
        prior = record.get("previous")
        if ((prior is None and record["phase"] != "prepared") or
                (prior is not None and prior["candidate"] != record["detail"]["base"])):
            raise SharedOperationError("bound found predecessor Config mismatch")
    if ("managed" in record) != (record["phase"] in (MANAGED_WRITING, MANAGED_CONFIG_SAVING)):
        raise SharedOperationError("managed write phase lacks original intent")
    if "managed" in record:
        _validate_managed_write(record)
    _validate_first_running_pin(record)
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


def committed_manifest(record: dict | None) -> dict | None:
    """Select only the actual terminal owner's pin, never an aborted candidate.

    An old unbound owner remains unbound. PREPARED and every nonterminal
    phase have no current committed root authority. The caller still
    needs original FD9, physical root and native owner preflight.
    """
    if committed_owner(record) is None:
        return None
    return record.get("manifest" if record["phase"] == "committed"
                      else "previous_manifest")


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
                      runtime_mode: str | None = None,
                      shared_work_parent: Path | None = None) -> dict:
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
        if restored_first_learning(before) or restored_first_retry(before):
            raise SharedOperationError("restored first learning Found successor not qualified")
        if before is not None and before["phase"] not in TERMINAL:
            raise SharedOperationError("unfinished original common Apply")
        # Preserve the predecessor root in the SAME durable original WAL.
        # The legacy Found writer still refuses before its first file write.
        previous = committed_owner(before)
        previous_manifest = committed_manifest(before)
        if before is not None and (
                before["detail"]["id"] == detail["id"] or
                (previous is not None and previous["id"] == detail["id"])):
            raise SharedOperationError("reused original common Apply operation")
        if previous_manifest is not None:
            from shared_apply_seal import WORK
            from neutral_root_stage import (
                _verify_original_pinned_root, RootStageRefused)
            from voice_ipfw_adapter import require_lifecycle_lock
            parent = WORK if shared_work_parent is None else shared_work_parent
            if (not isinstance(parent, Path) or
                    previous["candidate"] != detail["base"]):
                raise SharedOperationError("pinned found previous Config mismatch")
            try:
                require_lifecycle_lock()
                _verify_original_pinned_root(
                    detail=previous, binding=previous_manifest,
                    parent=parent, owner_uid=self.owner)
            except (RootStageRefused, RuntimeError, OSError, ValueError):
                raise SharedOperationError("pinned found predecessor proof refused") from None
        if not callable(attest) or attest(sealed_plan) is not True:
            raise SharedOperationError("sealed original found preimages unverified")
        if previous_manifest is not None:
            try:
                require_lifecycle_lock()
                _verify_original_pinned_root(
                    detail=previous, binding=previous_manifest,
                    parent=parent, owner_uid=self.owner)
            except (RootStageRefused, RuntimeError, OSError, ValueError):
                raise SharedOperationError("pinned found predecessor changed") from None
        if self.read() != before:
            raise SharedOperationError("common Apply owner changed during found attestation")
        result = {"schema": SCHEMA, "phase": "prepared", "detail": detail,
                  "found": {"schema": 1, "kind": FOUND_KIND,
                            "plan_sha256": hashlib.sha256(sealed_plan).hexdigest(),
                            "sources": list(FOUND_NAMES)}}
        if runtime_mode is not None:
            result["found"]["runtime_mode"] = runtime_mode
        if previous is not None:
            result["previous"] = previous
        if previous_manifest is not None:
            result["previous_manifest"] = previous_manifest
        return self._persist_record(result)

    def _attest_bound_found_checkpoint(self, record: dict, bound_attest) -> None:
        """Guard original file/Config WAL phases; never a launcher permit.

        For a bound transaction both immutable pins are checked with the
        existing root verifier on either side of the phase-specific native
        Config/P2 callback. The legacy caller has no bound callback and
        cannot enter any bound physical checkpoint. No extra WAL or lock.
        """
        if "manifest" not in record and "previous_manifest" not in record:
            if bound_attest is not None:
                raise SharedOperationError("unexpected bound found witness")
            return
        from shared_apply_seal import WORK
        from neutral_root_stage import verify_original_operation_pins
        from voice_ipfw_adapter import require_lifecycle_lock
        if ("manifest" not in record or "found" not in record or
                type(record.get("previous")) is not dict or
                record["previous"]["candidate"] != record["detail"]["base"] or
                not callable(bound_attest)):
            raise SharedOperationError("bound found original Config/P2 witness required")
        try:
            require_lifecycle_lock()
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=self.owner)
            if self.read() != record or bound_attest(record) is not True:
                raise SharedOperationError("bound found phase witness refused")
            require_lifecycle_lock()
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=self.owner)
            if self.read() != record:
                raise SharedOperationError("bound found phase owner changed")
        except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
            if isinstance(exc, SharedOperationError):
                raise
            raise SharedOperationError("bound found immutable proof refused") from None

    def _persist_found_checkpoint(self, before: dict, after: dict, bound_attest) -> dict:
        self._attest_bound_found_checkpoint(before, bound_attest)
        result = self._persist_record(after)
        if self.read() != result:
            raise SharedOperationError("original found durable readback refused")
        return result

    def advance_found_files(self, phase: str, detail: dict,
                            sealed_plan: bytes, attest, *,
                            post_images: dict | None = None,
                            bound_attest=None) -> dict:
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
        return self._persist_found_checkpoint(record, advanced, bound_attest)

    def advance_found_stage(self, detail: dict, sealed_plan: bytes,
                            name: str, phase: str, pin: dict, attest, *,
                            bound_attest=None) -> dict:
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
        return self._persist_found_checkpoint(
            record, {**record, "found": next_found}, bound_attest)

    def advance_found_config(self, phase: str, detail: dict,
                             sealed_plan: bytes, attest, *, bound_attest=None) -> dict:
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
        return self._persist_found_checkpoint(before, record, bound_attest)

    def record_found_rollback(self, record: dict, sealed_plan: bytes, *,
                              source: str | None = None, pin: dict | None = None,
                              complete: bool = False, bound_attest=None) -> dict:
        """Persist rollback intent and each before-inode pin under Config/P2."""
        if ("found" not in record or
                record["found"]["plan_sha256"] != hashlib.sha256(sealed_plan).hexdigest() or
                self.read() != record):
            raise SharedOperationError("original found rollback record changed")
        phase = record["phase"]
        if phase in FOUND_ROLLBACK_FROM and source is None and not complete:
            return self._persist_found_checkpoint(record, {
                **record, "phase": FOUND_RESTORING,
                "found": {**record["found"], "restoring": {}},
            }, bound_attest)
        if phase != FOUND_RESTORING:
            raise SharedOperationError("original found rollback phase mismatch")
        if complete and source is None:
            restored = dict(record)
            restored.pop("found")
            restored["phase"] = "restored"
            return self._persist_found_checkpoint(record, restored, bound_attest)
        if source not in record["found"]["stages"] or complete:
            raise SharedOperationError("source was not written by the found transaction")
        restoring = {**record["found"]["restoring"], source: pin}
        return self._persist_found_checkpoint(record, {
            **record, "found": {**record["found"], "restoring": restoring},
        }, bound_attest)

    def advance_found_runtime(self, phase: str, record: dict, sealed_plan: bytes, attest) -> dict:
        """Keep the file intent through the ordinary runtime/IPFW lifecycle."""
        if ("found" not in record or
                "manifest" in record or "previous_manifest" in record or
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
            if restored_first_learning(before) or restored_first_retry(before):
                raise SharedOperationError("restored first learning successor not qualified")
            if before is not None and before["phase"] not in TERMINAL:
                raise SharedOperationError("unfinished common Apply operation")
            if before is not None and before["detail"]["id"] == detail["id"]:
                raise SharedOperationError("reused common Apply transaction ID")
            previous = committed_owner(before)
            previous_manifest = committed_manifest(before)
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
            if "first_retry_archive" in before:
                raise SharedOperationError("first retry requires original bound transaction")
            if phase not in NEXT.get(before["phase"], frozenset()):
                raise SharedOperationError("illegal common Apply phase transition")
            # S10b1 never calls the launcher: a bound root must be freshly
            # attested by the actual S10b2 original owner BEFORE activating.
            # Ordinary legacy unbound Apply retains its established path.
            if phase == "activating" and (
                    "manifest" in before or "previous_manifest" in before):
                raise SharedOperationError("immutable root preactivation gate not implemented")
            if "manifest" in before or "previous_manifest" in before:
                if phase == "restored" and before["phase"] == "prepared":
                    raise SharedOperationError("bound prepared requires original pinned recovery")
                # The legacy record CLI cannot terminalize a future bound
                # operation merely because its phase is otherwise legal.
                raise SharedOperationError("bound phase requires original physical witness")
            previous = before.get("previous")
            previous_manifest = before.get("previous_manifest")
        record = {"schema": SCHEMA, "phase": phase, "detail": detail}
        if previous is not None:
            record["previous"] = previous
        if previous_manifest is not None:
            record["previous_manifest"] = previous_manifest
        if before is not None and "found" in before:
            record["found"] = before["found"]
        if phase != "prepared" and before is not None and "manifest" in before:
            record["manifest"] = before["manifest"]
        return self._persist_record(record)

    def attest_unbound_config_save(self, identity: str, witness_sha256: str, *,
                                   shared_work_parent: Path) -> None:
        """Check the original ordinary save under the caller's FD9/Config locks."""
        from neutral_root_stage import ROOT_NAME, PENDING_NAME
        from shared_apply_seal import verify_seal

        if (type(identity) is not str or not OP_ID.fullmatch(identity) or
                type(witness_sha256) is not str or not DIGEST.fullmatch(witness_sha256)):
            raise SharedOperationError("invalid ordinary Config save witness")
        record = self.read()
        if (record is None or record["phase"] != "activated" or
                record["detail"]["id"] != identity or
                {"found", "manifest", "previous_manifest"} & record.keys()):
            raise SharedOperationError("ordinary Config save requires unbound activated owner")
        work = shared_work_parent / identity

        def check_root():
            for directory in (work, work / "release"):
                if _exists(directory / ROOT_NAME) or _exists(directory / PENDING_NAME):
                    raise SharedOperationError("ordinary Config save has unbound root artifacts")

        check_root()
        seal = verify_seal(work, owner=self.owner)
        if _config_save_witness(record["detail"], seal["sha256"]["plan.json"]) != witness_sha256:
            raise SharedOperationError("ordinary Config save differs from original activation")
        check_root()
        if self.read() != record:
            raise SharedOperationError("ordinary Config save owner changed")

    def _checkpoint_managed_write(self, expected: dict, managed: dict | None, attest, *,
                                  shared_work_parent: Path, saved_base: str | None = None) -> dict:
        """Fsync one managed list intent or inode pin in the original WAL."""
        if self.read() != expected or not callable(attest):
            raise SharedOperationError("managed write owner changed")
        next_record = dict(expected)
        recovering_save = _managed_restore_has_base(expected, saved_base)
        if saved_base is not None and not recovering_save:
            raise SharedOperationError("managed restore requires exact saved base")
        if (expected["phase"] == "prepared" and type(managed) is dict and
                managed.keys() - {"running_sha256"} == _MANAGED_BASE):
            next_record.update(phase=MANAGED_WRITING, managed=managed)
        elif expected["phase"] == MANAGED_WRITING or recovering_save:
            if managed is None:
                next_record.pop("managed")
                next_record["phase"] = "restored"
            else:
                stage = expected["managed"]
                changed = {key for key in stage.keys() | managed.keys()
                           if stage.get(key) != managed.get(key)}
                available = {"restore"} if "ready" in stage else {"ready"}
                if "ready" in stage and not {"barrier", "installed", "restore"} & stage.keys():
                    available.add("barrier")
                if "barrier" in stage and not {"installed", "restore"} & stage.keys():
                    available.add("installed")
                if recovering_save:
                    available = {"restore"}
                if not stage.keys() <= managed.keys() or len(changed) != 1 or not changed <= available:
                    raise SharedOperationError("managed write checkpoint out of order")
                next_record["managed"] = managed
        else:
            raise SharedOperationError("managed write requires prepared owner")
        return self._persist_managed_checkpoint(expected, next_record, attest,
                                                shared_work_parent=shared_work_parent)

    def _checkpoint_managed_config(self, expected: dict, *, saved: bool, attest,
                                   shared_work_parent: Path) -> dict:
        """Begin the uncertain Config window or publish the verified new owner."""
        phase = MANAGED_CONFIG_SAVING if saved else MANAGED_WRITING
        if self.read() != expected or expected["phase"] != phase:
            raise SharedOperationError("managed Config checkpoint owner changed")
        row = expected["managed"]
        if not {"running_sha256", "installed"} <= row.keys() or "restore" in row:
            raise SharedOperationError("managed Config checkpoint lacks installed owner")
        next_record = {**expected, "phase": "committed" if saved else MANAGED_CONFIG_SAVING}
        if saved:
            next_record.pop("managed")
        return self._persist_managed_checkpoint(expected, next_record, attest,
                                                shared_work_parent=shared_work_parent)

    def _persist_managed_checkpoint(self, expected: dict, next_record: dict, attest, *,
                                    shared_work_parent: Path) -> dict:
        from neutral_root_stage import verify_original_operation_pins
        from voice_ipfw_adapter import require_lifecycle_lock

        _validate_record(next_record)

        def verify():
            require_lifecycle_lock()
            verify_original_operation_pins(record=expected, parent=shared_work_parent,
                                           owner_uid=self.owner)
            if self.read() != expected:
                raise SharedOperationError("managed write owner changed")

        verify()
        if attest() is not True:
            raise SharedOperationError("managed write physical witness refused")
        verify()
        result = self._persist_record(next_record)
        if self.read() != result:
            raise SharedOperationError("managed write durable readback refused")
        return result

    def _advance_bound_ordinary(self, phase: str, expected: dict, attest, *,
                                shared_work_parent: Path | None = None,
                                first_running_sha256: str | None = None,
                                first_pretraffic_sha256: str | None = None) -> dict:
        """Internal original FD9 transition with exact immutable pins.

        This is the same WAL writer and phase table as ordinary Apply.
        The original coordinator MUST supply the phase-specific native
        witness (not an analytic receipt or a generic CLI boolean).
        PREPARED abort remains recover_prepared; Found remains fenced until
        its original Config/P2 writer and recovery are integrated.
        """
        from neutral_root_stage import verify_original_operation_pins, RootStageRefused
        from shared_apply_seal import WORK
        from voice_ipfw_adapter import require_lifecycle_lock

        parent = WORK if shared_work_parent is None else shared_work_parent
        before = self.read()
        if (type(expected) is not dict or before != expected or
                type(before) is not dict or "found" in before or
                "manifest" not in before or not isinstance(parent, Path) or
                phase not in NEXT.get(before["phase"], frozenset()) or
                (before["phase"] == "prepared" and phase != "activating") or
                not callable(attest)):
            raise SharedOperationError("bound ordinary transition refused")
        if ("previous" in before and
                before["previous"]["candidate"] != before["detail"]["base"]):
            raise SharedOperationError("bound ordinary predecessor Config mismatch")

        next_record = {**before, "phase": phase}
        if first_running_sha256 is not None or first_pretraffic_sha256 is not None:
            if (phase != "activated" or before["phase"] != "activating" or
                    not _first_running_pin_scope(before) or
                    "first_running_sha256" in before or "first_pretraffic_sha256" in before):
                raise SharedOperationError("first running owner pin scope refused")
            if first_running_sha256 is not None:
                next_record["first_running_sha256"] = first_running_sha256
            if first_pretraffic_sha256 is not None:
                next_record["first_pretraffic_sha256"] = first_pretraffic_sha256
            _validate_first_running_pin(next_record)

        def pins():
            require_lifecycle_lock()
            verify_original_operation_pins(
                record=before, parent=parent, owner_uid=self.owner)
            if self.read() != before:
                raise SharedOperationError("bound ordinary journal changed")

        try:
            pins()
            if attest() is not True:
                raise SharedOperationError("bound ordinary native witness refused")
            pins()
        except (RootStageRefused, OSError, ValueError, RuntimeError) as exc:
            if isinstance(exc, SharedOperationError):
                raise
            raise SharedOperationError("bound ordinary pin or native proof refused") from None
        # Persist the exact candidate/predecessor bindings through every
        # allowed phase, including review/restore. No second writer or
        # physical action; failure before fsync leaves the old phase.
        result = self._persist_record(next_record)
        # Failure after fsync is uncertain, not a verified old phase.
        if self.read() != result:
            raise SharedOperationError("bound ordinary durable readback refused")
        return result

    def _record_native_bound_activated(self, record: dict, *, preimage,
                                       config_fd: int, config_digest: str,
                                       queue_fd: int | None = None) -> tuple[dict, "StagedBoundRuntimeReceipt"]:
        """Same original WAL after physical promotion, before Config save.

        An unqualified staged image retains ACTIVATING. This internal
        in-flight transition is not a cold recovery or launcher command.
        """
        from neutral_schema3_quiescent_preimage import (
            StagedBoundRuntimeReceipt, attest_bound_quiescent_staged_under_fd9)

        if (self.root != DEFAULT_ROOT or self.owner != 0 or
                type(record) is not dict or self.read() != record or
                record.get("phase") != "activating" or "found" in record or
                record.get("manifest", {}).get("schema") not in (1, 2)):
            raise SharedOperationError("bound native activated scope refused")

        if config_digest != record["detail"]["base"]:
            raise SharedOperationError("bound native activated Config base refused")
        receipt = None

        def attest():
            nonlocal receipt
            receipt = attest_bound_quiescent_staged_under_fd9(
                record, preimage=preimage, config_fd=config_fd,
                config_digest=config_digest, queue_fd=queue_fd)
            return (type(receipt) is StagedBoundRuntimeReceipt and
                    receipt.generation == record["detail"]["id"] and
                    receipt.root_sha256 == record["manifest"]["root_sha256"] and
                    receipt.config_base_sha256 == record["detail"]["base"] and
                    receipt.observed_config_sha256 == config_digest and
                    (receipt.pretraffic_sha256 is not None) == (record["manifest"]["schema"] == 2))

        if _first_running_pin_scope(record):
            if not attest():
                raise SharedOperationError("first activated physical witness refused")
            initial = receipt
            learning = record["manifest"]["schema"] == 2
            if learning and (initial.running is None or initial.pretraffic_sha256 is None):
                raise SharedOperationError("first learning activation requires running and pretraffic proof")
            if initial.running is not None:
                from neutral_schema3_quiescent_preimage import _first_running_digest
                from shared_apply_seal import WORK
                release = WORK / record["detail"]["id"] / "release"
                digest = _first_running_digest(release, initial.running, config_fd=config_fd)

                def attest_pinned():
                    return (attest() and receipt == initial and
                            _first_running_digest(release, receipt.running,
                                                  config_fd=config_fd) == digest)

                pins = {"first_running_sha256": digest}
                if learning:
                    pins["first_pretraffic_sha256"] = initial.pretraffic_sha256
                result = self._advance_bound_ordinary("activated", record, attest_pinned, **pins)
            else:
                result = self._advance_bound_ordinary("activated", record,
                    lambda: attest() and receipt == initial)
        else:
            result = self._advance_bound_ordinary("activated", record, attest)
        # Keep the actual PID, tree, backup and zero-cut from this checkpoint
        # in the SAME in-flight coordinator through Config::save. Do not
        # reconstruct them from a different post-save process.
        return result, receipt


    def _record_native_bound_saved(self, record: dict, *, preimage, activated_receipt,
                                   config_fd: int, config_digest: str,
                                   queue_fd: int | None = None) -> dict:
        """Original Config owner's post-save readback while rollback survives.

        The caller already holds a fresh native Config lock after Config::save;
        fsync that descriptor and recheck the SAME staged image. For Auto the
        original borrowed P2a remains held, and the zero receipt is still
        unfinished. The existing finalizer, not this checkpoint, writes epoch.
        """
        from dataclasses import replace
        from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
        from neutral_schema3_quiescent_preimage import (
            StagedBoundRuntimeReceipt, attest_bound_quiescent_staged_under_fd9)
        from voice_ipfw_adapter import require_lifecycle_lock
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                self.root != DEFAULT_ROOT or self.owner != 0 or
                type(record) is not dict or self.read() != record or
                record.get("phase") != "activated" or "found" in record or
                record.get("manifest", {}).get("schema") not in (1, 2) or
                type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
                config_digest != record["detail"]["candidate"] or
                type(activated_receipt) is not StagedBoundRuntimeReceipt or
                activated_receipt.generation != record["detail"]["id"] or
                activated_receipt.root_sha256 != record["manifest"]["root_sha256"] or
                activated_receipt.config_base_sha256 != record["detail"]["base"] or
                activated_receipt.observed_config_sha256 != record["detail"]["base"]):
            raise SharedOperationError("bound native saved scope refused")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        os.fsync(config_fd)
        learning = record["manifest"]["schema"] == 2

        def attest():
            receipt = attest_bound_quiescent_staged_under_fd9(
                record, preimage=preimage, config_fd=config_fd,
                config_digest=config_digest, queue_fd=queue_fd, saved=True)
            return (type(receipt) is StagedBoundRuntimeReceipt and
                    receipt.generation == record["detail"]["id"] and
                    receipt.root_sha256 == record["manifest"]["root_sha256"] and
                    receipt.config_base_sha256 == record["detail"]["base"] and
                    receipt == replace(activated_receipt, observed_config_sha256=config_digest) and
                    _first_running_pin_matches(record, receipt.running, config_fd,
                                               pretraffic_sha256=receipt.pretraffic_sha256) and
                    (receipt.pretraffic_sha256 is not None) == learning)

        return self._advance_bound_ordinary(
            "epoch-finalizing" if learning else "config-saved", record, attest)


    def _finish_native_bound_ordinary(self, record: dict, *, config_fd: int,
                                      config_digest: str, enabled: bool,
                                      runtime_mode: str, activated_receipt,
                                      queue_fd: int | None = None) -> dict:
        """Original FD9/FD4 terminal checkpoint; not a public command.

        Do not accept a generic callback, a synthetic committed predecessor,
        or a saved-image match as physical proof. Fsync the actual native
        Config descriptor before the final two read-only observations, then
        use the existing original WAL writer. Found runtime remains fenced.
        """
        from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
        from neutral_schema3_previous_physical import (
            FinalBoundRuntimeReceipt, attest_bound_candidate_final_under_fd9)
        from neutral_schema3_quiescent_preimage import StagedBoundRuntimeReceipt
        from voice_ipfw_adapter import require_lifecycle_lock

        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                self.root != DEFAULT_ROOT or self.owner != 0 or
                type(record) is not dict or self.read() != record or
                "found" in record or "manifest" not in record or
                record["phase"] not in ("config-saved", "epoch-finalizing") or
                type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
                config_digest != record["detail"]["candidate"] or
                type(activated_receipt) is not StagedBoundRuntimeReceipt or
                activated_receipt.generation != record["detail"]["id"] or
                activated_receipt.root_sha256 != record["manifest"]["root_sha256"] or
                activated_receipt.config_base_sha256 != record["detail"]["base"] or
                activated_receipt.observed_config_sha256 != record["detail"]["base"]):
            raise SharedOperationError("bound native terminal scope refused")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        os.fsync(config_fd)

        def attest():
            receipt = attest_bound_candidate_final_under_fd9(
                record, config_fd=config_fd, config_digest=config_digest,
                enabled=enabled, runtime_mode=runtime_mode,
                retired_ready_sha256=activated_receipt.retired_ready_sha256,
                queue_fd=queue_fd, expected_idle_producer=activated_receipt.idle_producer)
            return (type(receipt) is FinalBoundRuntimeReceipt and
                    receipt.generation == record["detail"]["id"] and
                    receipt.root_sha256 == record["manifest"]["root_sha256"] and
                    receipt.config_sha256 == config_digest and
                    receipt.release_sha256 == activated_receipt.release_sha256 and
                    receipt.running == activated_receipt.running and
                    _first_running_pin_matches(record, receipt.running, config_fd,
                                               pretraffic_sha256=receipt.pretraffic_sha256) and
                    receipt.pretraffic_sha256 == activated_receipt.pretraffic_sha256 and
                    receipt.retired_ready_sha256 == activated_receipt.retired_ready_sha256 and
                    receipt.idle_producer == activated_receipt.idle_producer and
                    (receipt.epoch_sha256 is not None) == (record["manifest"]["schema"] == 2) and
                    receipt.authorization == "NONE" and
                    receipt.physical_transition_allowed is False)

        return self._advance_bound_ordinary("committed", record, attest)


    def bind_prepared_manifest(self, generation: str, *,
                               effective, native, mode: str, enabled: bool,
                               shared_work_parent: Path | None = None,
                               schema3: bool = False,
                               found_plan_sha256: str | None = None) -> dict:
        """Pin S10a's already-staged root in THIS fsynced original FD9 WAL.

        No alternate journal/seal/config/launcher, no phase advance and no
        physical privilege. Genuine original S08/S09 inputs are required.
        Fixed production parent is shared_apply_seal.WORK; caller-supplied
        parent exists only for disposable protected unit/native fixtures.
        """
        from shared_apply_seal import WORK
        from voice_ipfw_adapter import require_lifecycle_lock
        from neutral_root_stage import (attest_staged_candidate,
                                        attest_staged_schema3_candidate,
                                        PreparedRootReceipt, RootStageRefused,
                                        _verify_original_pinned_root)
        try:
            require_lifecycle_lock()  # attests existing FreeBSD root FD9
        except (OSError, RuntimeError, ValueError):
            raise SharedOperationError("original FD9 required for root binding") from None
        if (type(generation) is not str or not OP_ID.fullmatch(generation) or
                type(schema3) is not bool or
                (schema3 and mode != "auto")):
            raise SharedOperationError("invalid original root generation or schema")
        work_parent = (WORK if shared_work_parent is None else shared_work_parent)
        if not isinstance(work_parent, Path):
            raise SharedOperationError("original shared-work parent required")
        before = self.read()
        if (before is None or before["phase"] != "prepared" or
                before["detail"]["id"] != generation or
                "manifest" in before or
                ("found" in before) != (found_plan_sha256 is not None) or
                (found_plan_sha256 is not None and
                 (type(found_plan_sha256) is not str or
                  before["found"]["plan_sha256"] != found_plan_sha256))):
            raise SharedOperationError("original PREPARED unbound journal required")
        # Existing original S10a staging/attestation and the existing journal
        # writer are shared. Only the source verifier differs: schema-2 MUST
        # prove real postpromotion refs rather than reusing S08d's old argv.
        verifier = (attest_staged_schema3_candidate if schema3
                    else attest_staged_candidate)
        args = dict(generation=generation, effective=effective, native=native,
                    enabled=enabled, parent=work_parent,
                    journal_root=self.root, owner_uid=self.owner)
        if not schema3:
            args["mode"] = mode
        if found_plan_sha256 is not None:
            args["found_plan_sha256"] = found_plan_sha256
        try:
            if "previous_manifest" in before:
                _verify_original_pinned_root(
                    detail=before["previous"], binding=before["previous_manifest"],
                    parent=work_parent, owner_uid=self.owner)
            receipt = verifier(**args)
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
        root = {"schema": 2 if schema3 else 1, "generation": generation,
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
            recheck_args = ({**args, "allow_bound_schema3": True}
                            if schema3 else args)
            rechecked = verifier(**recheck_args)
            if "previous_manifest" in result:
                _verify_original_pinned_root(
                    detail=result["previous"], binding=result["previous_manifest"],
                    parent=work_parent, owner_uid=self.owner)
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
        if "manifest" in before or "previous_manifest" in before:
            raise SharedOperationError("bound Remove requires original pinned recovery")
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
        self, identity: str, sealed_plan: bytes, attest, *,
        shared_work_parent: Path | None = None
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
        old_pin = record.get("previous_manifest")
        candidate_pin = record.get("manifest")
        if prior is not None and prior["candidate"] != detail["base"]:
            raise SharedOperationError("found pristine predecessor not Config base")
        if old_pin is not None or candidate_pin is not None:
            from shared_apply_seal import WORK
            from neutral_root_stage import (
                _verify_original_pinned_root, _original_plan_matches,
                RootStageRefused)
            from voice_ipfw_adapter import require_lifecycle_lock
            parent = WORK if shared_work_parent is None else shared_work_parent
            if not isinstance(parent, Path):
                raise SharedOperationError("original pinned work parent required")

            def check_pins():
                try:
                    require_lifecycle_lock()
                    if old_pin is not None:
                        _verify_original_pinned_root(
                            detail=prior, binding=old_pin,
                            parent=parent, owner_uid=self.owner)
                except (RootStageRefused, RuntimeError, OSError, ValueError):
                    raise SharedOperationError("found pristine predecessor pin refused") from None
                if candidate_pin is not None:
                    try:
                        _verify_original_pinned_root(
                            detail=detail, binding=candidate_pin,
                            parent=parent, owner_uid=self.owner)
                        if not _original_plan_matches(
                                parent=parent, generation=identity,
                                journal=record, owner_uid=self.owner):
                            raise RootStageRefused("FOUND_RECOVERY_PLAN_CHANGED")
                    except (RootStageRefused, RuntimeError, OSError, ValueError):
                        raise SharedOperationError("found pristine candidate pin refused") from None
            check_pins()
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
        if old_pin is not None or candidate_pin is not None:
            check_pins()
        if self.read() != record:
            raise SharedOperationError("found pristine journal changed under original locks")
        # Keep the aborted candidate pin as evidence, never as committed owner.
        # Only previous_manifest can identify the terminal RESTORED owner.
        completed = {"schema": SCHEMA, "phase": "restored", "detail": detail}
        if prior is not None:
            completed["previous"] = prior
        if old_pin is not None:
            completed["previous_manifest"] = old_pin
        if candidate_pin is not None:
            completed["manifest"] = candidate_pin
        return self._persist_record(completed)

    def recover_prepared(self, identity: str, attest, *,
                         shared_work_parent: Path | None = None) -> dict:
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
        # A first retry has no committed predecessor. A seal alone cannot
        # prove its archived abort and native Config/base/physical state.
        # Keep the same WAL pending until the dedicated recovery qualifies it.
        if "first_retry_archive" in record:
            raise SharedOperationError("first retry prepared recovery requires original archive proof")
        if "manifest" in record or "previous_manifest" in record:
            # The root is a sibling, deliberately outside the original bundle
            # seal. Boot's legacy seal callback cannot authenticate its pin.
            # Recover only the exact previously bound PREPARED record; never
            # authorize activation or downgrade to the old unbound path.
            from shared_apply_seal import WORK
            from neutral_root_stage import (
                verify_prepared_recovery_pin, RootStageRefused,
            )
            parent = WORK if shared_work_parent is None else shared_work_parent
            if not isinstance(parent, Path):
                raise SharedOperationError("original shared-work parent required")
            try:
                verify_prepared_recovery_pin(record=record, parent=parent,
                                             owner_uid=self.owner)
                if not callable(attest) or attest() is not True:
                    raise SharedOperationError("shared candidate attestation refused")
                verify_prepared_recovery_pin(record=record, parent=parent,
                                             owner_uid=self.owner)
            except RootStageRefused:
                raise SharedOperationError("bound prepared recovery pin refused") from None
            if self.read() != record:
                raise SharedOperationError("shared Apply phase changed during recovery")
            # Same original atomic/fsynced operation.json writer. Preserve
            # previous owner AND manifest pin for review; no physical effect.
            restored = dict(record)
            restored["phase"] = "restored"
            return self._persist_record(restored)
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
        if "manifest" in record or "previous_manifest" in record:
            return self._finish_bound_inert_cold_restore(record, attest)
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
        if "manifest" in record or "previous_manifest" in record:
            return self._finish_bound_inert_cold_restore(record, attest)
        if not callable(attest) or attest() is not True:
            raise SharedOperationError(phase + " rollback attestation refused")
        if self.read() != record:
            raise SharedOperationError(phase + " journal changed during recovery")
        return self.advance("restored", record["detail"])

    def _finish_bound_inert_cold_restore(self, record: dict, attest) -> dict:
        """Existing original cold recovery; never trust legacy seal alone."""
        from neutral_schema3_quiescent_preimage import native_finish_bound_cold_restore
        if self.root != DEFAULT_ROOT or self.owner != 0:
            raise SharedOperationError("bound cold restore requires native original store")
        if not callable(attest) or attest() is not True or self.read() != record:
            raise SharedOperationError("bound cold restore bundle witness refused")
        # The original PHP Config owner retains FD4 through the child WAL
        # fsync. Do not also write restored from this outer CLI process.
        return native_finish_bound_cold_restore(record)

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
        if "manifest" in before or "previous_manifest" in before:
            raise SharedOperationError("bound Remove requires original pinned recovery")
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
                "manifest" in record or "previous_manifest" in record or \
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
        if record is None or record["phase"] != "requires-review" or \
                "manifest" in record or "previous_manifest" in record:
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


def restored_retired_found_owner(record: dict | None) -> bool:
    """Read-only scope for the next stopped Found Apply, not a lifecycle permit.

    The original old root remains authoritative after RESTORED. The aborted
    candidate, if bound, must still be verified by the caller; never use it
    as the current root. No admission of other restored runtime classes.
    """
    if type(record) is not dict or record.get("phase") != "restored":
        return False
    _validate_record(record)
    prior = committed_owner(record)
    pin = committed_manifest(record)
    return (type(prior) is dict and type(pin) is dict and pin["schema"] == 2 and
            record["detail"]["page"] == "strategies" and
            prior["candidate"] == record["detail"]["base"] and
            ("manifest" not in record or record["manifest"]["schema"] == 1) and
            not any(key in record for key in ("found", "failure")))


def native_bound_stopped_gui_gate(operation: str | None = None) -> int:
    """Read-only FD9 admission for a disabled List/All Found successor.

    Stage/execution admission is NOT a physical permit. The original locked
    PHP/Python P1 writer and terminal owner reattest Config, immutable roots,
    saved files, journal, processes and IPFW before each actual mutation.
    """
    from neutral_root_stage import verify_original_operation_pins, _verify_original_pinned_root
    from neutral_schema3_previous_physical import _full_prior_tree
    from neutral_schema3_quiescent_preimage import (
        _zero_processes, _safe_empty_directory, _empty_kernel,
        CHILD_PID, MONITOR_PID, DAEMON_PID, PRODUCER_ROOT)
    from auto_detect_minute import inspect_inert_release
    from voice_live_inspect import COMMON_ACTIVE, examine_shared
    from shared_apply_seal import WORK, verify_seal
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            (operation is not None and
             (type(operation) is not str or not OP_ID.fullmatch(operation)))):
        raise SharedOperationError("bound GUI gate original native FD9 required")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    restored = restored_retired_found_owner(record)
    if (type(record) is not dict or
            (record["phase"] != "committed" and not restored) or
            (committed_manifest(record) or {}).get("schema") not in (1, 2) or
            "found" in record or "failure" in record):
        raise SharedOperationError("bound GUI gate inert terminal owner required")
    detail, pin = committed_owner(record), committed_manifest(record)
    old_work = WORK / detail["id"]
    retired = pin["schema"] == 2

    def observe_retired():
        # The same original FD9/P2a lifetime as the private retired save.
        # No repair, no queue creation, no ACK or physical mutation.
        import pwd
        from auto_detect_owner import attest_learning_stopped_generation
        from auto_detect_learning_retirement import retired_learning_stopped, RETIRE_DIR, READY
        from auto_detect_epoch_receipts import EpochReceipts, _read
        from auto_detect_queue import DurableInbox
        from auto_detect_storage import ROOT, ENGINE_USER
        from auto_detect_fd import _probe_original_inode
        from neutral_schema3_quiescent_preimage import _verify_idle_producer
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise SharedOperationError("bound GUI gate retired queue gid refused")
        queue = DurableInbox(ROOT, owner_uid=0, writer_gid=gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        with queue.exclusive(existing_only=True):
            def attest():
                require_lifecycle_lock()
                if store.read() != record:
                    raise SharedOperationError("bound GUI gate retired owner changed")
                return (attest_learning_stopped_generation(restored_record=record)
                        if restored else attest_learning_stopped_generation())
            def inspect(path, device, inode, *, owner, writer_gid):
                return _probe_original_inode(path, device, inode, owner=owner,
                    writer_gid=writer_gid, attest_owner=lambda: attest().owner == owner)
            proof = attest()
            if (proof.operation_id != detail["id"] or proof.generation != detail["id"] or
                    proof.owner_candidate_sha256 != detail["candidate"]):
                raise SharedOperationError("bound GUI gate retired historical owner changed")
            ready = receipts._generation(detail["id"], create=False) / RETIRE_DIR / READY
            raw = _read(ready, 0)
            if not retired_learning_stopped(receipts, queue, proof, old_work,
                    attest=attest, inspect=inspect, repair=False):
                raise SharedOperationError("bound GUI gate retirement incomplete")
            idle = _verify_idle_producer(queue, receipts)
            if (attest() != proof or _read(ready, 0) != raw or
                    _verify_idle_producer(queue, receipts) != idle or store.read() != record):
                raise SharedOperationError("bound GUI gate retired proof changed")
            return proof, hashlib.sha256(raw).hexdigest(), idle

    def observe_old():
        require_lifecycle_lock()
        if store.read() != record:
            raise SharedOperationError("bound GUI gate journal changed")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        root = json.loads(_verify_original_pinned_root(
            detail=detail, binding=pin, parent=WORK, owner_uid=0))
        if retired:
            if (root["service"]["enabled"] is not True or
                    root["service"]["target_mode"] != "auto"):
                raise SharedOperationError("bound GUI gate retired Auto root required")
        elif (root["service"]["enabled"] is not False or
                root["service"]["target_mode"] not in ("list", "all") or
                inspect_inert_release(old_work / "release", owner_uid=0) != "inactive"):
            raise SharedOperationError("bound GUI gate old root not inert")
        current = examine_shared(record)
        if (type(current) is not dict or current.get("state") != "stopped" or
                current.get("source") != "native-common" or
                current.get("config_digest") != detail["candidate"]):
            raise SharedOperationError("bound GUI gate previous owner not stopped")
        _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
        history = observe_retired() if retired else None
        if not retired:
            _safe_empty_directory(PRODUCER_ROOT, 0)
        tree = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
        kernel = _empty_kernel(old_work / "release")
        if store.read() != record:
            raise SharedOperationError("bound GUI gate predecessor changed")
        return tree, kernel, history

    previous = observe_old()
    if operation is not None:
        if operation in (detail["id"], record["detail"]["id"]):
            raise SharedOperationError("bound GUI gate cannot reuse generation")
        work = WORK / operation
        # The immutable candidate root is attached only by the existing
        # original bound P1 writer AFTER it durably enters PREPARED.
        # A detached sealed bundle does not yet contain manifest.json.
        signed = verify_seal(work, owner=0)
        raw = (work / "plan.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != signed["sha256"]["plan.json"]:
            raise SharedOperationError("bound GUI gate candidate plan changed")
        plan = json.loads(raw)
        candidate = plan.get("candidate") if type(plan) is dict else None
        general = candidate.get("general") if type(candidate) is dict else None
        hostlist = candidate.get("hostlist") if type(candidate) is dict else None
        mode = hostlist.get("mode") if type(hostlist) is dict else None
        if type(mode) is dict:
            selected = []
            for name, option in mode.items():
                flag = option.get("selected") if type(option) is dict else None
                if (name not in ("all", "list", "auto") or
                        type(flag) not in (bool, int, str) or
                        flag not in (0, 1, "0", "1")):
                    raise SharedOperationError("bound GUI gate invalid target option")
                if flag in (1, "1"):
                    selected.append(name)
            mode = selected[0] if len(selected) == 1 else None
        if (type(plan) is not dict or plan.get("page") != "strategies" or
                plan.get("result") != "prepared" or
                plan.get("dependencies") != detail["candidate"] or
                type(general) is not dict or general.get("enabled") != "0" or
                mode not in ("all", "list") or
                type(plan.get("changed_fields")) is not list or
                type(plan.get("found_intent")) is not dict or
                plan["found_intent"].get("commit_authorized") is not False or
                plan["found_intent"].get("config_revision") != detail["candidate"] or
                type(plan.get("found_batch")) is not dict):
            raise SharedOperationError("bound GUI gate candidate not stopped Found")
        from auto_detect_destination_commit import _qualified_shared_found_batch
        _qualified_shared_found_batch(plan["found_batch"])
        if verify_seal(work, owner=0) != signed:
            raise SharedOperationError("bound GUI gate candidate changed")
    if observe_old() != previous:
        raise SharedOperationError("bound GUI gate previous owner changed")
    return pin["schema"]


def native_bound_start_preflight(operation: str, page: str) -> str:
    """Read the committed Start preimage under original FD9 without changing it."""
    import subprocess

    from auto_detect_minute import inspect_inert_release
    from auto_detect_owner import (
        attest_learning_running_generation, attest_learning_stopped_generation,
    )
    from neutral_root_stage import verify_original_operation_pins
    from neutral_schema3_previous_physical import (
        _full_prior_tree, _running_executable_identity, _running_native,
    )
    from neutral_schema3_quiescent_preimage import (
        CHILD_PID, MONITOR_PID, DAEMON_PID, PRODUCER_ROOT,
        _empty_kernel, _observe_idle_producer, _retired_ready, _zero_processes,
    )
    from neutral_schema3_saved_wan_preimage import _CONFIG, _PHP, _native_call, _native_wan
    from neutral_shared_apply_source_gate import _read, _read_pinned_effective, _s10_native_bound_engine_readback
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock, shared_release_manifest
    from voice_live_inspect import CHILD_EXEC, COMMON_ACTIVE, examine_shared

    stage = "owner"
    try:
        require_lifecycle_lock()
        store = SharedApplyOperation(owner=0)
        record = store.read()
        if (record is None or record["phase"] != "committed" or
                "found" in record or "failure" in record):
            raise SharedOperationError("committed ordinary owner required")
        detail, pin = committed_owner(record), committed_manifest(record)
        if (detail["id"] != operation or detail["page"] != page or
                pin is None or pin["schema"] not in (1, 2)):
            raise SharedOperationError("exact pinned Start owner required")
        work = WORK / operation
        release = work / "release"
        learning = pin["schema"] == 2

        def observe():
            nonlocal stage
            stage = "owner"
            require_lifecycle_lock()
            if store.read() != record:
                raise SharedOperationError("Start journal changed")
            stage = "config"
            config = _native_call((_PHP, _CONFIG, "saved", operation, page))
            expected = {"result": "committed", "snapshot": detail["candidate"], "enabled": "1"}
            if config.count(b"\n") != 1 or not config.endswith(b"\n") or json.loads(config) != expected:
                raise SharedOperationError("saved Start owner changed or disabled")
            stage = "engine"
            engine = _s10_native_bound_engine_readback()
            stage = "release"
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
            effective, enabled = _read_pinned_effective(
                detail=detail, binding=pin, parent=WORK,
                sources=Path(__file__).resolve().parent, owner_uid=0,
                engine_version=engine["engine_version"])
            if not enabled:
                raise SharedOperationError("sealed Start owner disabled")
            tree = _full_prior_tree(work, COMMON_ACTIVE, 0)
            capture = json.loads(_read(release / "voice-plan.json", 0, 1_048_576))["capture"]
            stage = "wan"
            if _native_wan() != capture["wan"]:
                raise SharedOperationError("native WAN differs from sealed capture")
            stage = "firewall"
            manifest = shared_release_manifest(release)
            if (manifest["rule_base"], manifest["rule_max"]) != (19000, 19099):
                raise SharedOperationError("sealed ordinary IPFW range changed")
            stage = "runtime"
            state = examine_shared(record)
            if (type(state) is not dict or state.get("source") != "native-common" or
                    state.get("config_digest") != detail["candidate"]):
                raise SharedOperationError("native runtime has no matching owner")
            if state["state"] == "ready":
                running = _running_native(release, owner_uid=0, child_pidfile=CHILD_PID,
                                          monitor_pidfile=MONITOR_PID)
                executable = _running_executable_identity(
                    running.pid, engine["engine_sha256"], executable=Path(CHILD_EXEC),
                    runner=subprocess.run)
                runtime = ("running", running, executable)
            elif state["state"] == "stopped":
                _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
                stage = "firewall"
                runtime = ("stopped", _empty_kernel(release))
            else:
                raise SharedOperationError("native runtime is incomplete")
            stage = "epoch"
            if learning:
                if runtime[0] == "running":
                    proof = attest_learning_running_generation()
                    if (proof.owner.pid, proof.owner.started) != (running.pid, running.started):
                        raise SharedOperationError("running Start epoch process changed")
                else:
                    proof = attest_learning_stopped_generation()
                    _retired_ready(PRODUCER_ROOT, 0)
                if (proof.operation_id != operation or proof.generation != operation or
                        proof.owner_candidate_sha256 != detail["candidate"]):
                    raise SharedOperationError("Start epoch belongs to another owner")
                runtime += (proof,)
            else:
                if inspect_inert_release(release, owner_uid=0) != "inactive":
                    raise SharedOperationError("unexpected Auto producer in inert release")
                runtime += (_observe_idle_producer(PRODUCER_ROOT, 0),)
            stage = "owner"
            require_lifecycle_lock()
            if store.read() != record:
                raise SharedOperationError("Start journal changed during preflight")
            return runtime, engine, manifest, effective, tree

        before = observe()
        if observe() != before:
            stage = "owner"
            raise SharedOperationError("Start preimage changed")
        return before[0][0]
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError,
            subprocess.SubprocessError):
        raise SharedOperationError("bound-start-preflight:" + stage) from None


def native_bound_auto_stop_gate(operation: str) -> None:
    """Only the existing FD9 explicit Stop may retire a genuine schema2 owner.

    This is read-only admission, not a second Stop, ACK writer, or command.
    The original Stop immediately rechecks native Config, full active tree,
    exact running or stopped PID/birth, owned IPFW and epoch before altering
    any process. Do not admit a pending Found/Config or inert schema1 owner.
    """
    from auto_detect_owner import (
        attest_learning_running_generation, attest_learning_stopped_generation)
    from neutral_root_stage import verify_original_operation_pins, _verify_original_pinned_root
    from neutral_schema3_previous_physical import _full_prior_tree
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE, examine_shared
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not OP_ID.fullmatch(operation)):
        raise SharedOperationError("original schema2 FD9 Stop required")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if (type(record) is not dict or record.get("phase") != "committed" or
            "found" in record or "failure" in record or
            type(record.get("manifest")) is not dict or
            record["manifest"].get("schema") != 2 or
            record.get("detail", {}).get("id") != operation):
        raise SharedOperationError("original schema2 committed Stop owner required")
    detail, pin = record["detail"], record["manifest"]
    old_work = WORK / operation

    def observe():
        require_lifecycle_lock()
        if store.read() != record:
            raise SharedOperationError("original schema2 Stop journal changed")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        root = json.loads(_verify_original_pinned_root(
            detail=detail, binding=pin, parent=WORK, owner_uid=0))
        if (root["service"]["enabled"] is not True or
                root["service"]["target_mode"] != "auto"):
            raise SharedOperationError("original schema2 Auto root required")
        physical = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
        state = examine_shared(record)
        if (type(state) is not dict or state.get("source") != "native-common" or
                state.get("state") not in ("ready", "stopped") or
                state.get("config_digest") != detail["candidate"]):
            raise SharedOperationError("original schema2 Stop runtime not verified")
        proof = (attest_learning_running_generation() if state["state"] == "ready"
                 else attest_learning_stopped_generation())
        if (proof.operation_id != operation or proof.generation != operation or
                proof.owner_candidate_sha256 != detail["candidate"] or
                store.read() != record):
            raise SharedOperationError("original schema2 Stop owner changed")
        return physical, state["state"], proof
    first = observe()
    if observe() != first:
        raise SharedOperationError("original schema2 Stop owner raced")


def native_bound_prepare_gate(operation: str) -> None:
    """Only a fresh detached ordinary/Found candidate, never a lifecycle permit."""
    from neutral_root_stage import verify_original_operation_pins
    from shared_apply_render import regular
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not OP_ID.fullmatch(operation)):
        raise SharedOperationError("bound prepare requires original native FD9")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    restored = restored_retired_found_owner(record)
    if (type(record) is not dict or
            (record.get("phase") != "committed" and not restored) or
            (committed_manifest(record) or {}).get("schema") not in (1, 2) or
            "found" in record or "failure" in record or
            operation in (record["detail"]["id"], record.get("previous", {}).get("id"))):
        raise SharedOperationError("bound prepare requires ordinary terminal owner")
    owner = committed_owner(record)
    retired = committed_manifest(record)["schema"] == 2
    if retired and native_bound_stopped_gui_gate() != 2:
        raise SharedOperationError("bound prepare retired predecessor refused")
    work = WORK / operation

    def observe():
        require_lifecycle_lock()
        if store.read() != record:
            raise SharedOperationError("bound prepare owner changed")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        regular(WORK, 0, directory=True)
        regular(work, 0, directory=True)
        if set(os.listdir(work)) != {"candidate.xml", "plan.json"}:
            raise SharedOperationError("bound prepare requires fresh detached work")
        plan_path = work / "plan.json"
        xml_path = work / "candidate.xml"
        def identity(path):
            info = regular(path, 0)
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                    info.st_ctime_ns, info.st_mode, info.st_uid, info.st_nlink)

        identities = identity(plan_path), identity(xml_path)
        plan_raw, xml_raw = plan_path.read_bytes(), xml_path.read_bytes()
        if (identity(plan_path), identity(xml_path)) != identities:
            raise SharedOperationError("bound prepare detached source changed")
        plan = json.loads(plan_raw)
        candidate = plan.get("candidate") if type(plan) is dict else None
        general = candidate.get("general") if type(candidate) is dict else None
        hostlist = candidate.get("hostlist") if type(candidate) is dict else None
        # Unchanged OPNsense OptionField values retain native getNodes()
        # dictionaries. Match the selected-flag contract of VoiceModelValues
        # without treating a display label or an ambiguous selection as mode.
        mode = hostlist.get("mode") if type(hostlist) is dict else None
        if type(mode) is dict:
            selected = []
            for name, option in mode.items():
                flag = option.get("selected") if type(option) is dict else None
                if (name not in ("all", "list", "auto") or
                        type(flag) not in (bool, int, str) or flag not in (0, 1, "0", "1")):
                    raise SharedOperationError("bound prepare invalid native mode option")
                if flag in (1, "1"):
                    selected.append(name)
            mode = selected[0] if len(selected) == 1 else None
        if (type(plan) is not dict or plan.get("result") != "prepared" or
                plan.get("page") != "strategies" or
                plan.get("dependencies") != owner["candidate"] or
                type(general) is not dict or general.get("enabled") not in ("0", "1") or
                mode not in ("all", "list")):
            raise SharedOperationError("bound prepare detached plan scope refused")
        found_plan = "found_intent" in plan or "found_batch" in plan
        # Disabled ordinary candidates still require the later lifecycle
        # executor. A disabled Found plan is only a detached P1 after-image.
        # Native STOPPED owner/CAS/Config evidence is required before writes.
        if retired and (general["enabled"] != "0" or not found_plan):
            raise SharedOperationError("bound prepare retired successor must be disabled Found")
        if general["enabled"] == "0" and not found_plan:
            raise SharedOperationError("bound prepare detached plan scope refused")
        if found_plan:
            intent = plan.get("found_intent")
            if (type(intent) is not dict or
                    intent.get("config_revision") != plan["dependencies"] or
                    intent.get("commit_authorized") is not False or
                    type(plan.get("changed_fields")) is not list or
                    type(plan.get("found_batch")) is not dict):
                raise SharedOperationError("bound prepare detached Found intent refused")
            # Reuse the original canonical P1 batch validator. Detached
            # validation grants no physical CAS or Config permission;
            # the existing builder and FD4/P2 transaction reattest live preimages.
            from auto_detect_destination_commit import (
                DestinationRefused, _qualified_shared_found_batch)
            try:
                _qualified_shared_found_batch(plan["found_batch"])
            except (DestinationRefused, OSError, ValueError, TypeError) as exc:
                raise SharedOperationError("bound prepare detached Found batch refused") from exc
        if store.read() != record:
            raise SharedOperationError("bound prepare owner changed")
        return identities, plan_raw, xml_raw

    first = observe()
    if observe() != first:
        raise SharedOperationError("bound prepare detached source changed")
    if retired and (native_bound_stopped_gui_gate() != 2 or store.read() != record):
        raise SharedOperationError("bound prepare retired predecessor changed")



def _saved_start_plan_scope(plan: object, saved_digest: str) -> None:
    """Reject anything except PHP's exact no-change enabled Auto shape.

    This is a read-only scope validator, not a new serializer or an
    authorization to alter Config, the installed release or the WAL.
    """
    if (type(plan) is not dict or plan.get("result") != "prepared" or
            plan.get("page") != "strategies" or
            plan.get("dependencies") != saved_digest or
            plan.get("changed_fields") != [] or
            "found_intent" in plan or "found_batch" in plan):
        raise SharedOperationError("saved Start detached plan changed")
    candidate = plan.get("candidate")
    general = candidate.get("general") if type(candidate) is dict else None
    hostlist = candidate.get("hostlist") if type(candidate) is dict else None
    mode = hostlist.get("mode") if type(hostlist) is dict else None
    if type(mode) is dict:
        selected = []
        for name, option in mode.items():
            flag = option.get("selected") if type(option) is dict else None
            if (name not in ("all", "list", "auto") or
                    type(flag) not in (bool, int, str) or flag not in (0, 1, "0", "1")):
                raise SharedOperationError("saved Start invalid native mode")
            if flag in (1, "1"):
                selected.append(name)
        mode = selected[0] if len(selected) == 1 else None
    if (type(general) is not dict or general.get("enabled") != "1" or
            mode != "auto"):
        raise SharedOperationError("saved Start requires unchanged enabled Auto")


def native_bound_saved_start_build_gate(operation: str) -> None:
    """Read-only original FD9 admission of PHP saved-unchanged Start candidate.

    Only a fresh detached work directory may be inspected. The old root,
    Config, stopped processes, retirement ACK/archives, base-only queue and
    existing P2a lock must remain exact. This does NOT prepare a new WAL,
    acquire FD4, create inboxes, signal an engine or grant Start permission.
    """
    from auto_detect_post_drop import _original_epoch_queue
    from auto_detect_learning_gc import qualified_completed_learning
    from neutral_root_stage import verify_original_operation_pins
    from neutral_schema3_quiescent_preimage import (
        EPOCH_ROOT, _retired_ready_digest, _verify_idle_producer)
    from neutral_schema3_saved_wan_preimage import _native_preflight
    from shared_apply_render import regular
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not OP_ID.fullmatch(operation)):
        raise SharedOperationError("saved Start build requires original root FD9")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    pin = committed_manifest(record)
    prior = committed_owner(record)
    if (type(record) is not dict or record.get("phase") != "committed" or
            pin is None or pin["schema"] != 2 or type(prior) is not dict or
            prior["page"] != "strategies" or "failure" in record or
            "found" in record or "first_retry_archive" in record or
            operation in (prior["id"], record.get("previous", {}).get("id"))):
        raise SharedOperationError("saved Start build requires committed Auto predecessor")
    if native_bound_start_preflight(prior["id"], "strategies") != "stopped":
        raise SharedOperationError("saved Start build predecessor is not STOPPED")
    workspace = WORK / operation
    old_work = WORK / prior["id"]

    def identity(path: Path) -> tuple:
        info = regular(path, 0)
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                info.st_ctime_ns, info.st_mode, info.st_uid, info.st_nlink)

    def observe() -> tuple:
        require_lifecycle_lock()
        if store.read() != record:
            raise SharedOperationError("saved Start build journal changed")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        regular(WORK, 0, directory=True)
        regular(workspace, 0, directory=True)
        if set(os.listdir(workspace)) != {"candidate.xml", "plan.json"}:
            raise SharedOperationError("saved Start build requires detached original files")
        plan_path = workspace / "plan.json"
        xml_path = workspace / "candidate.xml"
        before = identity(plan_path), identity(xml_path)
        if before[0][2] > 65536 or before[1][2] > 16777216:
            raise SharedOperationError("saved Start candidate exceeds fixed bounds")
        plan_raw = plan_path.read_bytes()
        candidate_xml = xml_path.read_bytes()
        if (before != (identity(plan_path), identity(xml_path)) or
                len(plan_raw) != before[0][2] or
                len(candidate_xml) != before[1][2]):
            raise SharedOperationError("saved Start candidate inode changed")
        _saved_start_plan_scope(json.loads(plan_raw), prior["candidate"])
        # Original native Config lock is acquired by PHP's existing preflight.
        # Require exactly its saved digest and no changed user field.
        config = _native_preflight(operation, "strategies")
        if (type(config) is not dict or config.get("base") != prior["candidate"] or
                config.get("candidate") != prior["candidate"] or
                config.get("fields") != [] or config.get("enabled") != "1"):
            raise SharedOperationError("saved Start native Config does not match")
        # A no-change PHP candidate contains byte-identical saved XML. The
        # independent native Config probe brackets this read; it never writes.
        from auto_detect_original_lock_handoff import CONFIG_PATH
        fd = os.open(CONFIG_PATH, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            current = os.fstat(fd)
            if (not stat.S_ISREG(current.st_mode) or
                    current.st_size != len(candidate_xml) or
                    os.read(fd, len(candidate_xml) + 1) != candidate_xml or
                    os.fstat(fd) != current):
                raise SharedOperationError("saved Start XML differs from original Config")
        finally:
            os.close(fd)
        queue, receipts = _original_epoch_queue()
        with queue.exclusive(existing_only=True):
            idle = _verify_idle_producer(queue, receipts)
            ready = _retired_ready_digest(EPOCH_ROOT, prior["id"], 0)
            qualified_completed_learning(
                receipts, queue, prior["id"], expected_candidate=prior["candidate"],
                expected_ready_sha256=ready)
            if (_verify_idle_producer(queue, receipts) != idle or
                    _retired_ready_digest(EPOCH_ROOT, prior["id"], 0) != ready or
                    store.read() != record):
                raise SharedOperationError("saved Start retired original changed")
        if (identity(plan_path), identity(xml_path)) != before:
            raise SharedOperationError("saved Start detached inode changed")
        if store.read() != record:
            raise SharedOperationError("saved Start committed owner changed")
        return before, hashlib.sha256(plan_raw).hexdigest(), hashlib.sha256(candidate_xml).hexdigest(), ready, idle

    before = observe()
    if observe() != before or native_bound_start_preflight(prior["id"], "strategies") != "stopped":
        raise SharedOperationError("saved Start build preimage raced")


def restored_first_learning(record: dict | None) -> bool:
    """Recognize only an aborted first bound Auto owner; never a live owner."""
    return (type(record) is dict and record.get("phase") == "restored" and
            record.get("manifest", {}).get("schema") == 2 and
            not ({"previous", "previous_manifest", "found"} & record.keys()) and
            "first_running_sha256" in record and "first_pretraffic_sha256" in record)


def restored_first_retry(record: dict | None) -> bool:
    """Historical abort provenance is a fence, never an active predecessor."""
    return (type(record) is dict and record.get("phase") == "restored" and
            "first_retry_archive" in record)


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
        "common-existing-unbound-auto": "committed",
    }
    if action is not None and action not in exceptions:
        raise SharedOperationError("invalid native lifecycle gate action")
    record = SharedApplyOperation(root).read()
    if action == "common-existing-unbound-auto":
        # Preserve the existing pre-S10 ordinary Auto path only for an
        # actual committed unbound owner. This is NOT a bound-root fallback,
        # first-start admission, recovery action or physical authorization.
        if (record is not None and record["phase"] == "committed" and
                not ({"manifest", "previous_manifest", "first_retry_archive",
                      "first_running_sha256", "first_pretraffic_sha256",
                      "found", "managed", "failure"} & record.keys())):
            return {"state": "clear", "safe_to_mutate": True}
        return {"state": "blocked", "reason": "existing-unbound-auto-owner-required",
                "phase": None if record is None else record["phase"], "safe_to_mutate": False}
    if record is None:
        return {"state": "clear", "safe_to_mutate": True}
    phase = record["phase"]
    if restored_first_learning(record) or restored_first_retry(record):
        # Retain the aborted seed/producer and immutable work. A subsequent
        # first Apply needs a separately qualified admission, not legacy Start.
        return {"state": "blocked", "reason": "restored-first-learning-preflight-required",
                "phase": phase, "safe_to_mutate": False}
    # Legacy Apply/Lab must not retire or replace an immutable owner before
    # the new original bound preactivation path is available. A restored
    # candidate's own pin is NOT the active predecessor's pin.
    if committed_manifest(record) is not None or (
            phase not in TERMINAL and
            ("manifest" in record or "previous_manifest" in record)):
        # Only the existing pre-save cold recovery functions may reconcile
        # an exact inert bound owner. All Apply/Start/Stop/Lab, Found, live
        # Auto and saved/uncertain recovery remain fenced.
        if (root == DEFAULT_ROOT and "found" not in record and
                (action, phase) in (
                    ("common-recover-activating", "activating"),
                    ("common-recover-activated", "activated"))):
            from neutral_schema3_quiescent_preimage import attest_inert_bound_cold_recovery
            try:
                attest_inert_bound_cold_recovery(record, restored=False)
            except (OSError, ValueError, RuntimeError, TypeError, KeyError):
                pass
            else:
                return {"state": "clear", "safe_to_mutate": True}
        return {"state": "blocked", "reason": "immutable-root-preflight-required",
                "phase": phase, "safe_to_mutate": False}
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
    bound_prepare_request = (len(argv) == 4 and argv[1:3] == ["native-gate", "common-bound-prepare"] and
                             bool(OP_ID.fullmatch(argv[3])))
    bound_saved_start_build_request = (
        len(argv) == 4 and argv[1:3] == ["native-gate", "common-bound-saved-start-build"] and
        bool(OP_ID.fullmatch(argv[3])))
    bound_auto_stop_request = (
        len(argv) == 4 and argv[1:3] == ["native-gate", "common-bound-auto-stop"] and
        bool(OP_ID.fullmatch(argv[3])))
    bound_start_request = (
        len(argv) == 5 and argv[1:3] == ["native-gate", "common-bound-start"] and
        bool(OP_ID.fullmatch(argv[3])) and argv[4] in ("strategies", "voice"))
    retry_context = argv[1:] == ["first-retry-context"]
    retry_stage = argv[1:] == ["native-gate", "common-first-retry-stage"]
    retry_work = (len(argv) == 4 and argv[1] == "native-gate" and
                  argv[2] in ("common-first-retry-prepare", "common-first-retry-execute") and
                  bool(OP_ID.fullmatch(argv[3])))
    bound_gui_stage_request = argv[1:] == ["native-gate", "common-bound-stopped-stage"]
    bound_gui_execute_request = (
        len(argv) == 4 and argv[1:3] == ["native-gate", "common-bound-stopped-execute"] and
        bool(OP_ID.fullmatch(argv[3])))
    native_gate_request = len(argv) in (2, 3) and argv[1] == "native-gate" and (
        len(argv) == 2 or argv[2] in (
            "common-apply", "common-recover-saved",
            "common-recover-activating", "common-recover-activated",
            "common-recover-reviewed-legacy",
            "common-recover-reviewed-native", "strategy-lab-native",
            "common-existing-unbound-auto",
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
    archive_first = len(argv) == 3 and argv[1] == "archive-first-restored" and bool(OP_ID.fullmatch(argv[2]))
    first_pristine = len(argv) == 3 and argv[1] in (
        "recover-first-activating", "recover-first-activated", "recover-first-config-saved",
        "recover-first-epoch-finalizing") and bool(OP_ID.fullmatch(argv[2]))
    managed_recovery = len(argv) == 4 and argv[1] == "recover-managed" and all(
        OP_ID.fullmatch(value) for value in argv[2:4]
    )
    finish = len(argv) == 3 and argv[1] == "finish-saved" and bool(OP_ID.fullmatch(argv[2]))
    pristine_bound_only = len(argv) == 5 and argv[4] == "--bound-only"
    pristine = (len(argv) == 4 or pristine_bound_only) and argv[1] == "recover-activating" and all(
        OP_ID.fullmatch(value) for value in argv[2:4]
    )
    cold_bound_only = pristine_bound_only and argv[1] in ("finish-activated", "finish-activating")
    cold_restore = (len(argv) == 4 or cold_bound_only) and argv[1] in (
        "finish-activated", "finish-activating", "finish-remove-saved"
    ) and all(OP_ID.fullmatch(value) for value in argv[2:4])
    if not (inspection or found_pending or owner_witness or remove_prepared_context or remove_trial_context or remove_pair or remove_revert or review or finish_review or review_native or finish_review_native or recording or early_start or ipfw_attach or runtime_record or runtime_clear or recovery or archive_first or retry_context or retry_stage or retry_work or first_pristine or managed_recovery or finish or pristine or cold_restore or native_gate_request or bound_prepare_request or bound_saved_start_build_request or bound_auto_stop_request or
            bound_gui_stage_request or bound_gui_execute_request or bound_start_request):
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
        elif archive_first:
            from auto_detect_aborted_first import native_archive_first_restored
            native_archive_first_restored(argv[2])
            print("first-restored-archived=" + argv[2])
        elif bound_auto_stop_request:
            native_bound_auto_stop_gate(argv[3])
        elif bound_start_request:
            print("bound-start=" + native_bound_start_preflight(argv[3], argv[4]))
        elif bound_prepare_request:
            native_bound_prepare_gate(argv[3])
        elif bound_saved_start_build_request:
            native_bound_saved_start_build_gate(argv[3])
            print("bound-saved-start-build=qualified")
        elif retry_context:
            record = SharedApplyOperation(owner=0).read()
            print(record["detail"]["id"] if restored_first_learning(record) else "none")
        elif retry_stage or retry_work:
            from auto_detect_aborted_first import native_first_retry_gate
            native_first_retry_gate(None if retry_stage else argv[3],
                sealed=retry_work and argv[2] == "common-first-retry-execute")
        elif bound_gui_stage_request:
            native_bound_stopped_gui_gate()
        elif bound_gui_execute_request:
            schema = native_bound_stopped_gui_gate(argv[3])
            print("bound-stopped-schema=" + str(schema))
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
            elif (record["phase"] in ("activating", "activated", "config-saved") and
                    "previous" not in record and "found" not in record and
                    record.get("manifest", {}).get("schema") == 1):
                detail = record["detail"]
                print(record["phase"] + "-first " + detail["id"] + " " + detail["page"])
            elif (record["phase"] in ("activated", "epoch-finalizing") and
                    _first_running_pin_scope(record) and record["manifest"]["schema"] == 2 and
                    "first_running_sha256" in record and "first_pretraffic_sha256" in record):
                detail = record["detail"]
                print(record["phase"] + "-first " + detail["id"] + " " + detail["page"])
            elif record["phase"] == "prepared" and "first_retry_archive" in record:
                detail = record["detail"]
                print("prepared-first-retry " + detail["id"] + " " + detail["page"])
            elif record["phase"] in ("prepared", "config-saved"):
                detail = record["detail"]
                print(record["phase"] + " " + detail["id"] + " " + detail["page"])
            elif record["phase"] in ("activating", "activated", MANAGED_WRITING,
                                     MANAGED_CONFIG_SAVING) and "previous" in record:
                detail, previous = record["detail"], record["previous"]
                print(record["phase"] + " " + detail["id"] + " " + detail["page"] +
                      " " + previous["id"] + " " + previous["page"])
            else:
                # Never make an incomplete operation look like no owner.
                raise SharedOperationError("unfinished common Apply blocks native boot")
        elif first_pristine:
            from neutral_schema3_quiescent_preimage import native_finish_bound_cold_restore

            store = SharedApplyOperation(owner=0)
            record = store.read()
            if (record is None or record["phase"] != argv[1].removeprefix("recover-first-") or
                    record["detail"]["id"] != argv[2] or "previous" in record or
                    "previous_manifest" in record or "found" in record or
                    record.get("manifest", {}).get("schema") not in (1, 2)):
                raise SharedOperationError("first activating recovery owner mismatch")
            learning = record["manifest"]["schema"] == 2
            if learning and (record["phase"] not in ("activated", "epoch-finalizing") or
                    "first_running_sha256" not in record or "first_pretraffic_sha256" not in record):
                raise SharedOperationError("first learning recovery owner mismatch")
            if not learning and record["phase"] == "epoch-finalizing":
                raise SharedOperationError("first inert recovery phase mismatch")
            result = native_finish_bound_cold_restore(record)
            admitted = (("restored", "committed") if record["phase"] == "activated" else
                ("committed",)) if learning else {"activating": ("restored",),
                "activated": ("restored", "committed"), "config-saved": ("committed",)}[record["phase"]]
            if (result["phase"] not in admitted or result != {**record, "phase": result["phase"]} or
                    store.read() != result):
                raise SharedOperationError("first Config recovery readback mismatch")
            print("first-" + record["phase"] + "-" + result["phase"] + "=" + argv[2])
        elif managed_recovery:
            from neutral_schema3_quiescent_preimage import native_finish_bound_cold_restore

            record = SharedApplyOperation(owner=0).read()
            if (record is None or record["phase"] not in (MANAGED_WRITING, MANAGED_CONFIG_SAVING) or
                    (record["detail"]["id"], record["previous"]["id"]) != tuple(argv[2:4])):
                raise SharedOperationError("managed cold recovery owner mismatch")
            result = native_finish_bound_cold_restore(record)
            print("managed-" + result["phase"] + "=" + argv[2])
        elif recovery:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            record = store.read()
            if (record is not None and record["phase"] == "prepared" and
                    "first_retry_archive" in record):
                from auto_detect_aborted_first import native_recover_first_retry_prepared
                native_recover_first_retry_prepared(argv[2])
            else:
                store.recover_prepared(
                    argv[2],
                    lambda: bool(verify_seal(WORK / argv[2], owner=0)),
                )
            print("prepared-restored")
        elif pristine:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            if pristine_bound_only:
                # Exactly one private dispatch: only a positively identified
                # unbound original owner may use the legacy shell deletion.
                record = store.read()
                if (type(record) is not dict or record["phase"] != "activating" or
                        "found" in record or record["detail"]["id"] != argv[2] or
                        record.get("previous", {}).get("id") != argv[3]):
                    raise SharedOperationError("pristine recovery owner mismatch")
                if "manifest" not in record and "previous_manifest" not in record:
                    return 3
            store.recover_activating_pristine(
                argv[2], argv[3],
                lambda: bool(verify_seal(WORK / argv[2], owner=0) and
                             verify_seal(WORK / argv[3], owner=0)),
            )
            print("activating-pristine-restored")
        elif cold_restore:
            from shared_apply_seal import verify_seal, WORK
            store = SharedApplyOperation(owner=0)
            if cold_bound_only:
                record = store.read()
                if (type(record) is not dict or record["phase"] != argv[1][7:] or
                        "found" in record or record["detail"]["id"] != argv[2] or
                        record.get("previous", {}).get("id") != argv[3]):
                    raise SharedOperationError("installed recovery owner mismatch")
                if "manifest" not in record and "previous_manifest" not in record:
                    return 3
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
