#!/usr/bin/env python3
"""Staging-only restarted Voice argv comparison; NO boot/Apply/restart hooks.

A trusted future FreeBSD kernel argv provider must expose *arrays* rather
than human-rendered ps command text. This module accepts ONLY an injected
read-only provider; it does not implement kernel probing. The launcher reads
dvtws.args as awk whitespace fields and appends two immutable flags.
This witnesses argv and new process instances, NOT startup readiness,
media delivery, restoration permission, or a completed reboot.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from voice_cutover_backup import (
    VoiceBackupError, _read_private_file, inspect_previous,
)
from voice_process_recovery_evidence import (
    ProcessEvidenceError, _expected_paths, inspect_process_evidence,
)

MAX_ARGUMENT_FILE = 128 * 1024
MAX_ARGV = 512
MAX_ARG_BYTES = 8192
FIXED_TRAILER = ("--sockarg=0x200", "--user=nobody")
ROLES = ("engine", "daemon", "monitor")


class RestartArgvError(ValueError):
    pass


def _valid_token(value):
    return isinstance(value, str) and 0 < len(value) <= MAX_ARG_BYTES and \
        all(33 <= ord(ch) <= 126 for ch in value)


def _argv(value):
    if not isinstance(value, (list, tuple)) or not 1 <= len(value) <= MAX_ARGV or \
       any(not _valid_token(token) for token in value):
        raise RestartArgvError("untrusted or ambiguous native argv array")
    return list(value)


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")).hexdigest()


def expected_engine_argv(previous_backup: Path, engine_binary: str) -> list[str]:
    """Reconstruct exact awk-split launcher argv from sealed previous runtime."""
    if not _valid_token(engine_binary) or not Path(engine_binary).is_absolute():
        raise RestartArgvError("invalid expected dvtws2 executable")
    saved = inspect_previous(Path(previous_backup))
    record = saved["runtime"].get("dvtws.args")
    if not isinstance(record, dict) or record.get("type") != "file" or \
       type(record.get("bytes")) is not int or \
       record["bytes"] > MAX_ARGUMENT_FILE:
        raise RestartArgvError("missing bounded saved dvtws.args")
    raw = _read_private_file(Path(previous_backup) / "runtime/dvtws.args",
                             MAX_ARGUMENT_FILE)
    # awk default FS splits on space/tab/newline but does not interpret quotes.
    # Other control bytes are refused instead of guessing their serialization.
    if not raw or any(b not in (9, 10, 32) and not 33 <= b <= 126 for b in raw):
        raise RestartArgvError("unrepresentable launcher arguments")
    tokens = [word.decode("ascii") for word in raw.split()]
    if not tokens or len(tokens) + 3 > MAX_ARGV or \
       any(not _valid_token(t) for t in tokens):
        raise RestartArgvError("empty or oversized saved launcher argv")
    if any(t.startswith(("--sockarg=", "--user=")) for t in tokens):
        raise RestartArgvError("duplicate launcher-managed argument")
    return [engine_binary, *tokens, *FIXED_TRAILER]


def _expected_supervisor(paths, expected):
    if not isinstance(expected, dict) or set(expected) != {"daemon", "monitor"}:
        raise RestartArgvError("missing full expected supervisor argv")
    validated = {role: _argv(expected[role]) for role in ("daemon", "monitor")}
    if validated["daemon"][0] != paths["daemon"]:
        raise RestartArgvError("unbound expected daemon executable")
    monitor = validated["monitor"]
    if monitor[0] != paths["monitor"] and not (
        len(monitor) >= 2 and monitor[:2] in (
            ["/bin/sh", paths["monitor"]],
            ["/bin/csh", paths["monitor"]],
        )
    ):
        raise RestartArgvError("unbound expected supervisor script")
    return validated


def _normalize(value, previous, paths, expected):
    if not isinstance(value, dict) or set(value) != {"engine", "supervisor"}:
        raise RestartArgvError("incomplete kernel argv observation")
    if not isinstance(value["supervisor"], dict) or \
       set(value["supervisor"]) != {"daemon", "monitor"}:
        raise RestartArgvError("incomplete supervisor argv observation")
    roles = {"engine": value["engine"], **value["supervisor"]}
    old = {"engine": previous["engine"]["process"],
           "daemon": previous["supervisor"]["daemon"],
           "monitor": previous["supervisor"]["monitor"]}
    result = {}
    for role in ROLES:
        row = roles[role]
        if not isinstance(row, dict) or set(row) != {
            "pid", "start_ns", "executable", "argv",
        }:
            raise RestartArgvError("invalid native process record")
        pid, start = row["pid"], row["start_ns"]
        if type(pid) is not int or not 1 < pid <= 4194304 or \
           type(start) is not int or start <= 0 or \
           row["executable"] != paths[role] or \
           _argv(row["argv"]) != expected[role]:
            raise RestartArgvError("new process executable or argv mismatch")
        older = old[role]["start_ns"]
        if type(older) is not int or start <= older:
            raise RestartArgvError("native process instance is not newer")
        result[role] = {"pid": pid, "start_ns": start,
                        "executable": row["executable"],
                        "argv": _argv(row["argv"])}
    if len({result[role]["pid"] for role in ROLES}) != len(ROLES):
        raise RestartArgvError("process roles share a PID")
    return result


def inspect_restarted_argv(previous_backup: Path, process_evidence: Path,
                           expected_paths: dict, supervisor_argv: dict,
                           reader) -> dict:
    """Double-sampled argv comparison, always non-authorizing.

    Supervisor argv is supplied by a caller, not bound to durable desired
    journal schema 2. There is NO production kernel argv adapter yet.
    """
    deny = {"schema": 1, "state": "blocked",
            "reason": "untrusted-or-incomplete-restart-argv",
            "can_activate": False, "can_recover_automatically": False,
            "safe_to_mutate": False, "safe_to_finish_intent": False,
            "media_pass": False, "startup_ready": False}
    try:
        _expected_paths(expected_paths)
        old = inspect_process_evidence(process_evidence, previous_backup,
                                       expected_paths)
        previous = old["observation"]
        if previous["engine"]["state"] != "running":
            raise RestartArgvError("previous process was not running")
        expected = {"engine": expected_engine_argv(
            previous_backup, expected_paths["engine"]
        ), **_expected_supervisor(expected_paths, supervisor_argv)}
        first = _normalize(reader.observe_argv(), previous,
                           expected_paths, expected)
        second = _normalize(reader.observe_argv(), previous,
                            expected_paths, expected)
        if first != second or \
           inspect_process_evidence(
               process_evidence, previous_backup, expected_paths,
           )["previous"] != old["previous"] or \
           expected_engine_argv(
               previous_backup, expected_paths["engine"],
           ) != expected["engine"]:
            raise RestartArgvError("saved runtime or process changed during scan")
        return {**deny, "state": "review-required",
                "reason": "new-process-argv-matches-sealed-launcher-plan",
                "engine_argv_sha256": _digest(expected["engine"]),
                "instances": {role: {"pid": first[role]["pid"],
                                     "start_ns": first[role]["start_ns"]}
                              for role in ROLES}}
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, RuntimeError, VoiceBackupError, ProcessEvidenceError):
        return deny
