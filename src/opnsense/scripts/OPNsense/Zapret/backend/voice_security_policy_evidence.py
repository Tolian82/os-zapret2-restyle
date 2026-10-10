#!/usr/bin/env python3
"""Private, write-once *staging-only* Voice native process security policy.

Pins expected three-role kernel image path and numeric UID/GID policy to the
SAME sealed previous Config/runtime, process-evidence fingerprints and old
whole-cutover five-resource identity. The digest can be inserted in a schema-3
whole-cutover journal, which is ALWAYS fail-closed unless the record is
reopened and checked against the journal.

Policy data are supplied by an injected caller; this module does NOT derive
an authoritative policy from OPNsense, trust arbitrary owner-provided
privileges, query live PIDs, acquire locks, restart services or touch IPFW.
Even a fully verified policy never authorizes Apply/recovery.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from voice_cutover_backup import (
    VoiceBackupError, _private_dir, _read_private_file, _sync_dir,
    bound_resource_fingerprints,
)
from voice_cutover_journal import RESOURCE_NAMES, SECURITY_BOUND_SCHEMA, SECURITY_FIELD
from voice_freebsd_process_security import (
    FIELDS, ROLES, ProcessSecurityError, _expected_map,
)
from voice_process_recovery_evidence import (
    ProcessEvidenceError, inspect_process_evidence,
)

POLICY_SCHEMA = 1
MAX_POLICY_BYTES = 16384
_HEX = set("0123456789abcdef")


class SecurityPolicyError(ValueError):
    pass


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _hash(data):
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def _normalize(previous, scripts, images, credentials):
    if not isinstance(previous, dict) or set(previous) != set(RESOURCE_NAMES) or \
       any(not _sha(value) for value in previous.values()):
        raise SecurityPolicyError("incomplete previous five-resource identity")
    _expected_map(scripts, images, credentials)
    return {"schema": POLICY_SCHEMA,
            "previous": {role: previous[role] for role in RESOURCE_NAMES},
            "scripts": {role: scripts[role] for role in ROLES},
            "images": {role: images[role] for role in ROLES},
            "credentials": {
                role: {field: credentials[role][field] for field in FIELDS}
                for role in ROLES
            }}


def _reopen_original(previous_backup, process_evidence, body):
    prior = body["previous"]
    bound_resource_fingerprints(previous_backup, prior)
    observed = inspect_process_evidence(
        process_evidence, previous_backup, body["scripts"], prior,
    )
    if observed["observation"]["engine"]["state"] != "running":
        raise SecurityPolicyError("no running three-role process identity to bind")
    if any(observed["previous"][name] != prior[name]
           for name in ("engine", "supervisor")):
        raise SecurityPolicyError("previous process identity differs")


def inspect_security_policy(directory: Path, previous_backup: Path,
                            process_evidence: Path, *,
                            journal_record=None, expected_scripts=None):
    """Reopen sealed 0600 policy; verify previous backup, processes and journal."""
    directory = Path(directory)
    _private_dir(directory.parent)
    _private_dir(directory)
    if set(os.listdir(directory)) != {"policy.json"}:
        raise SecurityPolicyError("untrusted security policy directory entries")
    raw = _read_private_file(directory / "policy.json", MAX_POLICY_BYTES)
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise SecurityPolicyError("invalid security policy JSON") from exc
    if not isinstance(record, dict) or set(record) != {
        "schema", "previous", "scripts", "images", "credentials", "check",
    } or type(record.get("schema")) is not int or \
       record["schema"] != POLICY_SCHEMA or not _sha(record.get("check")):
        raise SecurityPolicyError("invalid security policy record schema")
    body = _normalize(record["previous"], record["scripts"],
                      record["images"], record["credentials"])
    digest = _hash(body)
    if digest != record["check"]:
        raise SecurityPolicyError("modified policy checksum")
    if expected_scripts is not None and body["scripts"] != expected_scripts:
        raise SecurityPolicyError("foreign native process scripts")
    if journal_record is not None:
        if not isinstance(journal_record, dict) or \
           journal_record.get("schema") != SECURITY_BOUND_SCHEMA or \
           journal_record.get("previous") != body["previous"] or \
           not isinstance(journal_record.get("candidate"), dict) or \
           journal_record["candidate"].get(SECURITY_FIELD) != digest:
            raise SecurityPolicyError("security policy not pinned by durable cutover journal")
    _reopen_original(previous_backup, process_evidence, body)
    return {"schema": POLICY_SCHEMA, "state": "evidence-only",
            "policy_sha256": digest, "policy": body,
            "can_activate": False, "can_recover_automatically": False,
            "safe_to_mutate": False}


def capture_security_policy(previous_backup: Path, process_evidence: Path,
                            output: Path, previous: dict, scripts: dict,
                            images: dict, credentials: dict) -> str:
    """Private, fsync'd, write-once policy; does not create a journal itself."""
    output = Path(output)
    _private_dir(output.parent)
    if output.exists() or output.is_symlink():
        raise SecurityPolicyError("previous Voice security policy exists")
    body = _normalize(previous, scripts, images, credentials)
    _reopen_original(previous_backup, process_evidence, body)
    digest = _hash(body)
    record = {**body, "check": digest}
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":"))
           + "\n").encode("ascii")
    if len(raw) > MAX_POLICY_BYTES:
        raise SecurityPolicyError("security policy too large")
    temporary = Path(tempfile.mkdtemp(prefix=".voice-security-policy-", dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        with (temporary / "policy.json").open("xb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        proof = inspect_security_policy(
            temporary, previous_backup, process_evidence,
            expected_scripts=body["scripts"],
        )
        if proof["policy_sha256"] != digest:
            raise SecurityPolicyError("policy changed before publication")
        _sync_dir(temporary)
        _reopen_original(previous_backup, process_evidence, body)
        if output.exists() or output.is_symlink():
            raise SecurityPolicyError("policy destination appeared")
        os.rename(temporary, output)
        _sync_dir(output.parent)
        return digest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def verify_current_security(report: dict, verified_policy: dict) -> bool:
    """Match an injected read-only native witness to sealed policy (NOT readiness)."""
    try:
        policy = verified_policy["policy"]
        if verified_policy["state"] != "evidence-only" or \
           _hash(policy) != verified_policy["policy_sha256"] or \
           not isinstance(report, dict) or report.get("state") != "review-required" or \
           report.get("can_activate") is not False or \
           report.get("safe_to_mutate") is not False or \
           report.get("can_recover_automatically") is not False or \
           not isinstance(report.get("roles"), dict) or \
           set(report["roles"]) != set(ROLES):
            return False
        for role in ROLES:
            row = report["roles"][role]
            if not isinstance(row, dict) or \
               row.get("image") != policy["images"][role] or \
               row.get("credentials") != policy["credentials"][role] or \
               type(row.get("pid")) is not int or not 1 < row["pid"] <= 4194304 or \
               type(row.get("start_ns")) is not int or row["start_ns"] <= 0:
                return False
        return len({report["roles"][role]["pid"] for role in ROLES}) == len(ROLES)
    except (TypeError, ValueError, KeyError, AttributeError):
        return False
