#!/usr/bin/env python3
"""Unwired original-lock legacy PoC IPFW replay with per-operation durable redo.

This IS a real, bounded IPFW mutation algorithm, but has NO CLI, configd,
GUI, boot hook or service dispatch. It must NOT be called as a standalone
replacement for the full five-domain restoration coordinator. It requires
the exact sealed previous/plan/quiescent WAL and rechecks kernel, marker,
processes and native ledger before every command.

A write-ahead start-N is fsynced BEFORE each kernel operation, and done-N
AFTER its exact observed result. An interrupted command can be retried only
if the live kernel matches the complete BEFORE or AFTER prefix. Unknown
partial state, foreign rules/tables, owner drift or changed previous evidence
fails closed. This does not restart the old engine, install marker/runtime/
Config or claim whole-cutover recovery success.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
from voice_native_legacy_previous_seal import NAME, _digest, _write_once
from voice_native_legacy_restore_plan import (
    PLAN_NAME, inspect_legacy_restore_plan,
)
from voice_native_legacy_reverse_wal import (
    WAL_NAME, _stopped, _ledger_clear, _old_marker_off,
    inspect_legacy_reverse_wal,
)
from voice_native_live_ipfw import RULE_BASE, RULE_MAX, OLD_TABLE, OLD_STAGE
from voice_ipfw_adapter import (
    FreeBSDIPFWAdapter, RULE_LINE, TABLE_ENTRY, MAX_LINES, MAX_TABLE_ENTRIES,
    checked_ipv4, INTERFACE,
)
from voice_firewall_transaction import TABLE_PREFIX, SERVICES
from voice_native_recovery_quiescence import _locked_config

REPLAY_NAME = "legacy-ipfw-replay"
SCHEMA = 1
LIMIT = 65536
STEP_NAME = re.compile(r"^(start|done)-([0-9]{4})\.txt$")


class LegacyIPFWReplayError(RuntimeError):
    pass


def _encoded(data):
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def _strict_snapshot(readonly):
    if not isinstance(readonly, FreeBSDIPFWAdapter) or (
        readonly.allow_mutations or (readonly.rule_base, readonly.rule_max) !=
        (RULE_BASE, RULE_MAX)
    ):
        raise LegacyIPFWReplayError("untrusted FreeBSD IPFW reader")
    def sample():
        listing = readonly._run("-q", "list").splitlines()
        if len(listing) > MAX_LINES:
            raise LegacyIPFWReplayError("IPFW rule listing too large")
        rules = {}
        for line in listing:
            if not line.strip():
                continue
            match = RULE_LINE.fullmatch(line)
            if match is None:
                raise LegacyIPFWReplayError("foreign kernel rule syntax")
            number = int(match.group(1))
            if RULE_BASE <= number <= RULE_MAX:
                if str(number) in rules:
                    raise LegacyIPFWReplayError("duplicate rule number")
                rules[str(number)] = match.group(2).split()
        for service in SERVICES:
            name = TABLE_PREFIX + service
            if readonly.get_table(name) is not None or (
                readonly.get_table(name + "_stage") is not None
            ):
                raise LegacyIPFWReplayError("native Voice table still exists")
        if readonly._run("table", OLD_STAGE, "info", allow_missing=True) is not None:
            raise LegacyIPFWReplayError("old Telegram staging table still exists")
        info = readonly._run("table", OLD_TABLE, "info", allow_missing=True)
        if info is None:
            return {"rules":rules, "targets":None}
        if not re.search(r"(?im)\btype\s*:\s*addr\b", info):
            raise LegacyIPFWReplayError("old Telegram table has foreign type")
        entries = []
        for line in readonly._run("table", OLD_TABLE, "list").splitlines():
            if not line.strip():
                continue
            match = TABLE_ENTRY.fullmatch(line)
            if match is None:
                raise LegacyIPFWReplayError("foreign old Telegram IPv4 entry")
            raw = match.group(1)
            entry = checked_ipv4(raw[:-3] if raw.endswith("/32") else raw)
            if match.group(2) not in (None,"0"):
                raise LegacyIPFWReplayError("unexpected old Telegram IPv4 table value")
            entries.append(entry)
            if len(entries)>MAX_TABLE_ENTRIES:
                raise LegacyIPFWReplayError("old Telegram table too large")
        if len(set(entries)) != len(entries):
            raise LegacyIPFWReplayError("duplicate old Telegram IPFW table address")
        return {"rules":rules, "targets":sorted(entries)}
    before = sample()
    if sample() != before:
        raise LegacyIPFWReplayError("IPFW kernel changed during observation")
    return before


def _expected_after(plan, number):
    commands = plan["legacy_ipfw_commands"]
    if type(number) is not int or not 0 <= number <= len(commands):
        raise LegacyIPFWReplayError("out-of-range IPFW replay step")
    ip_adds = [c for c in commands if c[1:5] ==
               ["-q", "table", OLD_TABLE, "add"]]
    if not ip_adds:
        raise LegacyIPFWReplayError("IPFW reverse plan has no managed IPv4")
    ip_count = len(ip_adds)
    if number == 0:
        return {"rules":{}, "targets":None}
    # First operation creates the old table, then adds canonical addresses.
    entry_count = min(max(number-1,0),ip_count)
    rules = {}
    for cmd in commands[1+ip_count:number]:
        if cmd[:3] != ["/sbin/ipfw","-qf","add"]:
            raise LegacyIPFWReplayError("untrusted old rule restoration command")
        key = cmd[3]
        if key in rules:
            raise LegacyIPFWReplayError("duplicate old rule restoration")
        rules[key] = cmd[4:]
    return {"rules":rules,"targets":sorted(c[5] for c in ip_adds[:entry_count])}


def _steps(path, plan):
    """Validate contiguous write-once start/done evidence for each step."""
    directory = Path(path)
    names = set(os.listdir(directory))
    if not {"intent.json","intent.sha256"} <= names:
        raise LegacyIPFWReplayError("missing replay intent")
    raw = _read_private_file(directory / "intent.json", LIMIT)
    if _read_private_file(directory / "intent.sha256", 65) != (
        _digest(raw) + "\n"
    ).encode("ascii"):
        raise LegacyIPFWReplayError("damaged replay intent")
    intent = json.loads(raw)
    if intent != {
        "schema":SCHEMA, "state":"legacy-ipfw-replay-attempt-not-full-recovery",
        "plan_sha256":_digest(_encoded(plan)),
        "commands":len(plan["legacy_ipfw_commands"]),
        "safe_to_enable_voice":False,
    }:
        raise LegacyIPFWReplayError("foreign replay intent or previous plan drift")
    names -= {"intent.json","intent.sha256"}
    started, completed = set(),set()
    for name in names:
        match = STEP_NAME.fullmatch(name)
        if match is None:
            raise LegacyIPFWReplayError("unknown IPFW redo evidence")
        kind, num=match.group(1),int(match.group(2))
        if num >= intent["commands"]:
            raise LegacyIPFWReplayError("out-of-bounds IPFW redo step")
        expected=(str(num)+":"+_digest(_encoded(plan["legacy_ipfw_commands"][num]))+"\n").encode("ascii")
        if _read_private_file(directory/name, 256) != expected:
            raise LegacyIPFWReplayError("foreign/corrupted IPFW redo step")
        (started if kind=="start" else completed).add(num)
    count=0
    while count in completed:
        if count not in started:
            raise LegacyIPFWReplayError("completed IPFW step without durable START")
        count+=1
    if completed != set(range(count)) or not started <= set(range(count+1)):
        raise LegacyIPFWReplayError("noncontiguous IPFW redo history")
    return count, count in started


def _step_write(path, kind, number, cmd):
    if kind not in ("start","done") or type(number) is not int or (
        not 0 <= number <= 9999
    ):
        raise LegacyIPFWReplayError("unsafe redo checkpoint")
    row=(str(number)+":"+_digest(_encoded(cmd))+"\n").encode("ascii")
    _write_once(Path(path)/f"{kind}-{number:04d}.txt",row)
    _sync_dir(path)


def _make_intent(root, plan):
    root=Path(root)
    directory=Path(tempfile.mkdtemp(prefix=".legacy-ipfw-replay-",dir=root))
    os.chmod(directory,0o700)
    _sync_dir(root)
    body=_encoded({
        "schema":SCHEMA,"state":"legacy-ipfw-replay-attempt-not-full-recovery",
        "plan_sha256":_digest(_encoded(plan)),
        "commands":len(plan["legacy_ipfw_commands"]),
        "safe_to_enable_voice":False,
    })
    _write_once(directory/"intent.json",body)
    _write_once(directory/"intent.sha256",(_digest(body)+"\n").encode("ascii"))
    _sync_dir(directory)
    os.rename(directory,root/REPLAY_NAME)
    _sync_dir(root)


def replay_legacy_ipfw(
    *, root, config_path, config_fd, config_owner, ledger_root,
    legacy_marker, active_runtime, process_probe,
    readonly_ipfw, mutating_ipfw, require_lifecycle_owner,
):
    """Internal guarded real mutation, deliberately NO production dispatcher."""
    if not callable(require_lifecycle_owner) or (
        type(config_fd) is not int or config_fd < 0
        or not isinstance(mutating_ipfw,FreeBSDIPFWAdapter)
        or not mutating_ipfw.allow_mutations
        or (mutating_ipfw.rule_base,mutating_ipfw.rule_max)!=(RULE_BASE,RULE_MAX)
    ):
        raise LegacyIPFWReplayError("untrusted original owner or write adapter")
    root,config_path=Path(root),Path(config_path)
    def held():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
    def surroundings():
        if _stopped(process_probe) != "exact-three-role-absence" or (
            _old_marker_off(legacy_marker,active_runtime) !=
            "legacy-marker-absent-and-runtime-not-enabled"
        ) or _ledger_clear(ledger_root) not in (
            "no-native-ledger","empty-private-ledger"
        ):
            raise LegacyIPFWReplayError("old Telegram recovery surroundings changed")
    held()
    _private_dir(root)
    entries=set(os.listdir(root))
    expected={"legacy-previous","legacy-restore-plan","legacy-reverse-wal"}
    if entries not in (expected,expected|{REPLAY_NAME}):
        raise LegacyIPFWReplayError("foreign recovery files; manual review required")
    had_intent=REPLAY_NAME in entries
    inspect_legacy_reverse_wal(root,allow_ipfw_replay=had_intent)
    plan=inspect_legacy_restore_plan(root)
    commands=plan["legacy_ipfw_commands"]
    if not isinstance(commands,list) or not 3 <= len(commands) <= 4100:
        raise LegacyIPFWReplayError("invalid trusted old IPFW operation count")
    surroundings()
    if not had_intent:
        if _strict_snapshot(readonly_ipfw) != _expected_after(plan,0):
            raise LegacyIPFWReplayError("nonempty or foreign IPFW before replay intent")
        _make_intent(root,plan)
    progress=root/REPLAY_NAME
    _private_dir(progress)
    first_done,_=_steps(progress,plan)
    for i in range(first_done,len(commands)):
        cmd=commands[i]
        held()
        surroundings()
        done,started=_steps(progress,plan)
        if done != i:
            raise LegacyIPFWReplayError("IPFW redo history is inconsistent")
        current=_strict_snapshot(readonly_ipfw)
        old=_expected_after(plan,i)
        new=_expected_after(plan,i+1)
        if not started:
            if current != old:
                raise LegacyIPFWReplayError("foreign kernel before started step")
            _step_write(progress,"start",i,cmd)
            held()
            surroundings()
            current=_strict_snapshot(readonly_ipfw)
        # Power cut can occur after kernel add succeeded but before done-N.
        if current==old:
            if cmd[0]!="/sbin/ipfw" or cmd[1:] != commands[i][1:]:
                raise LegacyIPFWReplayError("invalid restoring IPFW command")
            mutating_ipfw._run(*cmd[1:],modifying=True)
        elif current!=new:
            raise LegacyIPFWReplayError("ambiguous kernel after partially completed step")
        if _strict_snapshot(readonly_ipfw)!=new:
            raise LegacyIPFWReplayError("restored kernel differs from sealed plan")
        held()
        surroundings()
        _step_write(progress,"done",i,cmd)
    if _steps(progress,plan) != (len(commands),False) or (
        _strict_snapshot(readonly_ipfw)!=_expected_after(plan,len(commands))
    ):
        raise LegacyIPFWReplayError("legacy IPFW replay final attestation failed")
    return {"state":"legacy-ipfw-replayed-other-four-domains-not-restored",
            "rules":len([c for c in commands if c[1]=="-qf"]),
            "entries":len([c for c in commands if c[1:5]==
                           ["-q","table",OLD_TABLE,"add"]]),
            "journal":"durable-per-command-start-and-done",
            "safe_to_enable_voice":False,"public_voice_apply":False,
            "whole_rollback_complete":False}
