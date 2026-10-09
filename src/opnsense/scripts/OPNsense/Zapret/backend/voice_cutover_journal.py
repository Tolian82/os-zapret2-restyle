#!/usr/bin/env python3
"""Private, durable, read-only-by-default journal for future complete Voice cutover.

Stores intent spanning the saved model, active runtime tree, one dvtws2,
supervisor and separately owned IPFW resources. THIS IS NOT THE IPFW LEDGER:
a real adapter must coordinate BOTH under the existing native lifecycle lock.
No automatic crash replay or command-line executor is provided.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

SCHEMA = 1
BOUND_SCHEMA = 2  # explicitly bound desired IPFW ownership (staging only)
SECURITY_BOUND_SCHEMA = 3  # also pins previous native process security policy
BOUND_FIELD = "firewall_manifest_sha256"
SECURITY_FIELD = "process_security_policy_sha256"
MAX_BYTES = 65536
FILES = ("intent.json",)
SHA = "0123456789abcdef"
PHASES = ("prepared", "mutating", "committed")
RESOURCE_NAMES = ("config", "runtime", "engine", "firewall", "supervisor")
PROOF_NAMES = ("saved_xml_sha256", "merged_sha256", "native_argv_sha256")


class CutoverJournalError(ValueError):
    pass


def _digest(content: dict) -> str:
    return hashlib.sha256(json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _sha(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in SHA for ch in value)


def validate_record(record: dict) -> dict:
    if not isinstance(record, dict) or set(record) != {
        "schema", "phase", "previous", "candidate", "check",
    } or type(record.get("schema")) is not int or \
       record["schema"] not in (SCHEMA, BOUND_SCHEMA, SECURITY_BOUND_SCHEMA) or \
       record.get("phase") not in PHASES:
        raise CutoverJournalError("invalid durable Voice cutover journal schema")
    previous = record["previous"]
    desired = record["candidate"]
    if not isinstance(previous, dict) or set(previous) != set(RESOURCE_NAMES) or \
       any(not _sha(value) for value in previous.values()):
        raise CutoverJournalError("incomplete previous system snapshot")
    expected_candidate = set(PROOF_NAMES)
    if record["schema"] >= BOUND_SCHEMA:
        expected_candidate.add(BOUND_FIELD)
    if record["schema"] == SECURITY_BOUND_SCHEMA:
        expected_candidate.add(SECURITY_FIELD)
    if not isinstance(desired, dict) or set(desired) != expected_candidate or \
       any(not _sha(value) for value in desired.values()):
        raise CutoverJournalError("unverified desired Voice fingerprints")
    if record["check"] != _digest({
        "schema": record["schema"], "phase": record["phase"],
        "previous": previous, "candidate": desired,
    }):
        raise CutoverJournalError("Voice cutover journal checksum mismatch")
    return record


def new_record(previous: dict, proof: dict) -> dict:
    if not isinstance(previous, dict) or not isinstance(proof, dict) or \
       set(previous) != set(RESOURCE_NAMES):
        raise CutoverJournalError("invalid cutover snapshot fields")
    previous_digests = {name: previous.get(name) for name in RESOURCE_NAMES}
    candidate = {name: proof.get(name) for name in PROOF_NAMES}
    record = {
        "schema": SCHEMA, "phase": "prepared",
        "previous": previous_digests, "candidate": candidate,
    }
    record["check"] = _digest(record)
    return validate_record(record)


def new_bound_record(previous: dict, proof: dict, desired_manifest: dict) -> dict:
    """Explicit schema 2; bind desired IPFW ownership, never infer readiness.

    This is a *staging-only* data contract, NOT the production cutover
    coordinator. Invalid desired rule/table manifests fail before journaling.
    """
    from voice_firewall_ledger import canonical_manifest, fingerprint
    base = new_record(previous, proof)
    body = {name: value for name, value in base.items() if name != "check"}
    body["schema"] = BOUND_SCHEMA
    body["candidate"] = {
        **base["candidate"],
        BOUND_FIELD: fingerprint(canonical_manifest(desired_manifest)),
    }
    body["check"] = _digest(body)
    return validate_record(body)



def new_security_bound_record(previous: dict, proof: dict,
                              desired_manifest: dict,
                              security_policy_sha256: str) -> dict:
    """Schema 3: explicit desired firewall AND previous process policy digest.

    A digest alone is not evidence: the caller must verify a sealed policy
    and both immutable previous snapshots before writing this intent.
    """
    if not _sha(security_policy_sha256):
        raise CutoverJournalError("invalid prior Voice security policy fingerprint")
    base = new_bound_record(previous, proof, desired_manifest)
    body = {k: v for k, v in base.items() if k != "check"}
    body["schema"] = SECURITY_BOUND_SCHEMA
    body["candidate"] = {**body["candidate"],
                         SECURITY_FIELD: security_policy_sha256}
    body["check"] = _digest(body)
    return validate_record(body)


class VoiceCutoverJournal:
    """Disk-only journal: CALLER must hold Config and native lifecycle locks."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._secure_dir()

    def _secure_dir(self) -> None:
        try:
            info = os.lstat(self.directory)
        except OSError as exc:
            raise CutoverJournalError("private Voice cutover journal directory is missing") from exc
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or \
           info.st_mode & 0o077:
            raise CutoverJournalError("Voice cutover directory is not owner-private")

    def _target(self) -> Path:
        return self.directory / "intent.json"

    def read(self) -> dict | None:
        self._secure_dir()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self._target(), flags)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise CutoverJournalError("unsafe Voice cutover journal file") from exc
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or \
               info.st_uid != os.geteuid() or info.st_mode & 0o077 or \
               info.st_size > MAX_BYTES:
                raise CutoverJournalError("Voice journal file is not private and regular")
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CutoverJournalError("oversized Voice cutover journal")
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise CutoverJournalError("corrupted Voice journal JSON") from exc
        return validate_record(record)

    def _sync_dir(self) -> None:
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _store(self, record: dict) -> None:
        self._secure_dir()
        validate_record(record)
        # Existing untrusted symlink/permissions must never be overwritten.
        self.read()
        raw = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True)
               + "\n").encode("ascii")
        if len(raw) > MAX_BYTES:
            raise CutoverJournalError("Voice cutover journal exceeds storage bound")
        fd, path = tempfile.mkstemp(prefix=".voice-cutover-", dir=self.directory)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                fd = -1
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(path, self._target())
            self._sync_dir()
        finally:
            if fd != -1:
                os.close(fd)
            if os.path.exists(path):
                os.unlink(path)

    def begin(self, previous: dict, proof: dict) -> None:
        if self.read() is not None:
            raise CutoverJournalError("Voice cutover intent already exists; inspect first")
        self._store(new_record(previous, proof))

    def begin_bound(self, previous: dict, proof: dict, desired_manifest: dict) -> None:
        """Future schema-2 intent: staging only, no production caller."""
        if self.read() is not None:
            raise CutoverJournalError("Voice cutover intent already exists; inspect first")
        self._store(new_bound_record(previous, proof, desired_manifest))

    def begin_security_bound(self, previous: dict, proof: dict,
                             desired_manifest: dict, policy_dir: Path,
                             previous_backup: Path, process_evidence: Path,
                             expected_scripts: dict) -> None:
        """Staging-only; verify actual sealed policy before durable intent."""
        from voice_security_policy_evidence import inspect_security_policy
        if self.read() is not None:
            raise CutoverJournalError("Voice cutover intent already exists; inspect first")
        report = inspect_security_policy(
            policy_dir, previous_backup, process_evidence,
            expected_scripts=expected_scripts,
        )
        if report["policy"]["previous"] != previous:
            raise CutoverJournalError("security policy refers to another previous state")
        self._store(new_security_bound_record(
            previous, proof, desired_manifest, report["policy_sha256"],
        ))

    def _transition(self, expected: str, new: str) -> None:
        current = self.read()
        if current is None or current["phase"] != expected:
            raise CutoverJournalError("unexpected previous Voice cutover journal phase")
        body = {name: val for name, val in current.items() if name != "check"}
        body["phase"] = new
        body["check"] = _digest(body)
        self._store(body)

    def mark_mutating(self) -> None:
        self._transition("prepared", "mutating")

    def commit(self) -> None:
        self._transition("mutating", "committed")

    def _finish(self) -> None:
        self.read()
        os.unlink(self._target())
        self._sync_dir()

    def abort_verified_previous(self, *, previous_verified: bool) -> None:
        current = self.read()
        if current is None or current["phase"] not in ("prepared", "mutating") or \
           previous_verified is not True:
            raise CutoverJournalError("cannot abort without verified previous complete state")
        self._finish()

    def finish_verified_desired(self, *, desired_verified: bool, cleanup_verified: bool) -> None:
        current = self.read()
        if current is None or current["phase"] != "committed" or \
           desired_verified is not True or cleanup_verified is not True:
            raise CutoverJournalError("cannot finish without verified committed desired state")
        self._finish()

    def inspect(self) -> str:
        """Read-only crash triage; never auto-discard an ambiguous intent."""
        current = self.read()
        if current is None:
            return "no-intent"
        if current["phase"] == "prepared":
            return "prepared-needs-previous-verification"
        if current["phase"] == "mutating":
            return "interrupted-needs-kernel-runtime-review"
        return "committed-needs-cleanup-review"
