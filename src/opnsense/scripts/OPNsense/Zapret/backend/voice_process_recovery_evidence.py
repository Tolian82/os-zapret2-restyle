#!/usr/bin/env python3
"""Staging-only previous Voice process topology evidence, NO live execution.

Only an injected read-only probe is accepted. This evidence describes an
observed engine/supervisor state; it cannot restore or authorize any process.
Caller must hold native Config + lifecycle locks and independently establish
kernel IPFW ownership, legacy adoption and actual process identity.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from voice_cutover_backup import (
    VoiceBackupError, _private_dir, _read_private_file, _sync_dir, inspect_previous,
)

SCHEMA = 1
MAX_RECORD = 32768
HEX = set("0123456789abcdef")
ROLES = ("engine", "daemon", "monitor")


class ProcessEvidenceError(ValueError):
    pass


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def _expected_paths(value):
    if not isinstance(value, dict) or set(value) != set(ROLES):
        raise ProcessEvidenceError("incomplete Voice process executable identities")
    for path in value.values():
        if not isinstance(path, str) or not 1 < len(path) <= 512 or \
           not Path(path).is_absolute() or ".." in Path(path).parts or \
           "\x00" in path or "\n" in path:
            raise ProcessEvidenceError("untrusted expected Voice process executable")
    return value


def _process(value, expected_path, running):
    if not isinstance(value, dict) or set(value) != {"pid", "start_ns", "executable"}:
        raise ProcessEvidenceError("malformed Voice process identity")
    if value["executable"] != expected_path:
        raise ProcessEvidenceError("foreign Voice process executable")
    pid, started = value["pid"], value["start_ns"]
    if running:
        if type(pid) is not int or not 1 < pid <= 4194304 or \
           type(started) is not int or started <= 0:
            raise ProcessEvidenceError("missing stable Voice process instance identity")
    elif pid is not None or started is not None:
        raise ProcessEvidenceError("stopped Voice process retained a stale pid")
    return {"pid": pid, "start_ns": started, "executable": expected_path}


def _normalize(observed, expected_paths, args_sha):
    _expected_paths(expected_paths)
    if not _sha(args_sha) or not isinstance(observed, dict) or \
       set(observed) != {"engine", "supervisor"}:
        raise ProcessEvidenceError("invalid previous Voice process observation")
    e, s = observed["engine"], observed["supervisor"]
    if not isinstance(e, dict) or set(e) != {"state", "process", "runtime_args_sha256"} or \
       not isinstance(s, dict) or set(s) != {"state", "daemon", "monitor"}:
        raise ProcessEvidenceError("incomplete Voice process observation")
    if e["state"] not in ("running", "stopped") or s["state"] != e["state"] or \
       e["runtime_args_sha256"] != args_sha:
        raise ProcessEvidenceError("inconsistent Voice engine/supervisor topology or args")
    running = e["state"] == "running"
    engine = {"state": e["state"],
              "process": _process(e["process"], expected_paths["engine"], running),
              "runtime_args_sha256": args_sha}
    supervisor = {
        "state": s["state"],
        "daemon": _process(s["daemon"], expected_paths["daemon"], running),
        "monitor": _process(s["monitor"], expected_paths["monitor"], running),
    }
    if running:
        pids = [engine["process"]["pid"], supervisor["daemon"]["pid"],
                supervisor["monitor"]["pid"]]
        if len(set(pids)) != len(pids):
            raise ProcessEvidenceError("Voice process roles share a pid")
    return {"schema": SCHEMA, "engine": engine, "supervisor": supervisor}


def _runtime_args_digest(snapshot):
    row = snapshot["runtime"].get("dvtws.args")
    if not isinstance(row, dict) or row.get("type") != "file" or not _sha(row.get("sha256")):
        raise ProcessEvidenceError("saved Voice runtime lacks a verified dvtws.args")
    return row["sha256"]


def _fingerprints(observation):
    return {
        "engine": _digest({"schema": SCHEMA, "engine": observation["engine"]}),
        "supervisor": _digest({"schema": SCHEMA, "supervisor": observation["supervisor"]}),
    }


def _check_record(record, expected_paths, args_sha):
    if not isinstance(record, dict) or set(record) != {
        "schema", "engine", "supervisor", "check",
    } or type(record.get("schema")) is not int or record["schema"] != SCHEMA or \
       not _sha(record["check"]):
        raise ProcessEvidenceError("invalid process evidence schema")
    observation = _normalize({
        "engine": record["engine"], "supervisor": record["supervisor"],
    }, expected_paths, args_sha)
    if record["check"] != _digest(observation):
        raise ProcessEvidenceError("Voice process evidence checksum mismatch")
    return observation


def inspect_process_evidence(directory: Path, previous_backup: Path,
                             expected_paths: dict, journal_previous: dict | None = None):
    """Read-only, bounded previous process evidence tied to sealed runtime."""
    directory = Path(directory)
    _private_dir(directory.parent)
    _private_dir(directory)
    if set(os.listdir(directory)) != {"processes.json"}:
        raise ProcessEvidenceError("untrusted Voice process evidence directory contents")
    saved = inspect_previous(previous_backup)
    raw = _read_private_file(directory / "processes.json", MAX_RECORD)
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ProcessEvidenceError("invalid Voice process evidence JSON") from exc
    observation = _check_record(record, expected_paths, _runtime_args_digest(saved))
    result = _fingerprints(observation)
    if journal_previous is not None and (not isinstance(journal_previous, dict) or
        any(journal_previous.get(k) != result[k] for k in result)):
        raise ProcessEvidenceError("Voice process evidence differs from whole-cutover journal")
    return {"state": "evidence-only", "can_activate": False,
            "can_recover_automatically": False, "previous": result,
            "observation": observation}


def capture_process_evidence(adapter, previous_backup: Path, output: Path,
                             expected_paths: dict):
    """Copy a stable read-only probe result to private, write-once evidence.

    The injected adapter must validate process identity against pidfile,
    executable and start time before returning a probe. No OS probe, command,
    stop/restart, or mutation API exists in this module.
    """
    output = Path(output)
    _private_dir(output.parent)
    _expected_paths(expected_paths)
    if output.exists() or output.is_symlink():
        raise ProcessEvidenceError("previous Voice process evidence already exists")
    saved = inspect_previous(previous_backup)
    args_sha = _runtime_args_digest(saved)
    first = _normalize(adapter.probe(), expected_paths, args_sha)
    if _normalize(adapter.probe(), expected_paths, args_sha) != first:
        raise ProcessEvidenceError("Voice process changed during read-only snapshot")
    temporary = Path(tempfile.mkdtemp(prefix=".voice-process-evidence-", dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        record = {**first, "check": _digest(first)}
        raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        if len(raw) > MAX_RECORD:
            raise ProcessEvidenceError("Voice process evidence too large")
        with (temporary / "processes.json").open("xb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if _normalize(adapter.probe(), expected_paths, args_sha) != first or \
           _runtime_args_digest(inspect_previous(previous_backup)) != args_sha:
            raise ProcessEvidenceError("Voice process or saved runtime changed before publish")
        inspect_process_evidence(temporary, previous_backup, expected_paths)
        _sync_dir(temporary)
        if output.exists() or output.is_symlink():
            raise ProcessEvidenceError("Voice process evidence destination appeared")
        os.rename(temporary, output)
        _sync_dir(output.parent)
        return _fingerprints(first)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
