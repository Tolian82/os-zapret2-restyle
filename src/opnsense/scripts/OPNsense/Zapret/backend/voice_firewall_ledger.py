#!/usr/bin/env python3
"""Durable *staging-only* IPFW ownership / intent ledger for Voice Transmission.

No command-line activation, IPFW subprocess or live orchestrator hook exists.
The caller must own the existing lifecycle lock and must have inspected and
verified kernel state before seeding an initial ownership manifest.

Files are stored outside /var/run (e.g. /var/db/zapret2/voice-ipfw), in a
pre-created private owner-only directory. An intent is fsync'd BEFORE any
external mutation; on an interrupted operation, inspect() is read-only and
returns 'manual-review' unless exact known full states can be established.
This is an audit ledger, not proof of OS-level atomic multi-rule changes.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError, table_contents_equal,
)

SCHEMA = 1
FILES = ("ownership.json", "intent.json")
MAX_FILE_BYTES = 512 * 1024
IPFW_OPTION = re.compile(r"^[A-Za-z0-9_.,:/()=-]+$")
WAN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")


class LedgerError(VoiceFirewallError):
    pass


def _fail(message: str) -> None:
    raise LedgerError(message)


def _valid_ipv4(value: Any) -> str:
    if not isinstance(value, str):
        _fail("non-string IPFW address")
    try:
        net = ipaddress.IPv4Network(value if "/" in value else value + "/32", strict=True)
    except ValueError as exc:
        raise LedgerError("invalid IPv4/CIDR in ownership manifest") from exc
    canonical = str(net) if "/" in value else str(net.network_address)
    if canonical != value:
        _fail("noncanonical IPv4/CIDR in ownership manifest")
    return value


def canonical_manifest(state: dict) -> dict:
    """Fully bound and JSON-stable representation of a trusted in-memory manifest.

    Numeric rule keys must round-trip as integers. All known table names and
    argv shapes are checked, avoiding shell syntax and poisoned journal input.
    """
    if not isinstance(state, dict) or set(state) != {
        "rule_base", "rule_max", "rules", "tables"
    }:
        _fail("invalid manifest shape")
    first, last = state["rule_base"], state["rule_max"]
    if type(first) is not int or type(last) is not int or not 1 <= first <= last <= 65534:
        _fail("invalid owned rule interval")
    source_rules, source_tables = state["rules"], state["tables"]
    if not isinstance(source_rules, dict) or not isinstance(source_tables, dict) or \
       len(source_rules) > 32 or len(source_tables) > len(SERVICES):
        _fail("invalid owned resources")
    rules: list[dict] = []
    for num, argv in source_rules.items():
        if type(num) is not int or not first <= num <= last:
            _fail("invalid owned rule number")
        if not isinstance(argv, list) or len(argv) < 13 or len(argv) > 20 or any(
            not isinstance(tok, str) or not IPFW_OPTION.fullmatch(tok) for tok in argv
        ):
            _fail("invalid owned IPFW rule arguments")
        if argv[0] != "divert" or not argv[1].isdecimal() or \
           not 1 <= int(argv[1]) <= 65535 or argv[2] not in ("udp", "tcp") or \
           argv[3:6] != ["from", "any", "to"] or \
           argv[-7:-1] != ["out", "not", "diverted", "not", "sockarg", "xmit"] or \
           not WAN.fullmatch(argv[-1]):
            _fail("unexpected owned IPFW rule syntax")
        dest = argv[6]
        if dest != "any" and dest not in (
            f"table({TABLE_PREFIX}{name})" for name in SERVICES
        ):
            _fail("unknown IPFW destination in owned rule")
        if dest != "any":
            if argv[2] != "udp":
                _fail("Voice destination tables must be UDP-scoped")
            table_name = dest[6:-1]
            if table_name not in source_tables:
                _fail("Voice rule refers to a table absent from ownership")
            if len(argv) not in (14, 15):
                _fail("unrecognized Voice IPFW argument layout")
        elif len(argv) != 15:
            _fail("ordinary IPFW capture requires an explicit port selector")
        if len(argv) == 15:
            selector = argv[7]
            if not re.fullmatch(r"[0-9,-]{1,1024}", selector):
                _fail("invalid owned UDP/TCP port selector")
            for interval in selector.split(","):
                parts = interval.split("-")
                if not 1 <= len(parts) <= 2 or any(
                    not part.isdecimal() or not 1 <= int(part) <= 65535 for part in parts
                ) or int(parts[0]) > int(parts[-1]):
                    _fail("invalid owned UDP/TCP port interval")
        rules.append({"number": num, "argv": list(argv)})
    rules.sort(key=lambda v: v["number"])
    tables = []
    for name, values in source_tables.items():
        if name not in (TABLE_PREFIX + service for service in SERVICES) or \
           not isinstance(values, list) or not 1 <= len(values) <= 4096:
            _fail("invalid owned table name or size")
        parsed = [_valid_ipv4(v) for v in values]
        if len(set(parsed)) != len(parsed):
            _fail("duplicate owned IPFW table entries")
        tables.append({"name": name, "addresses": parsed})
    tables.sort(key=lambda v: v["name"])
    return {
        "schema": SCHEMA,
        "rule_base": first,
        "rule_max": last,
        "rules": rules,
        "tables": tables,
    }


def decode_manifest(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {
        "schema", "rule_base", "rule_max", "rules", "tables"
    } or value.get("schema") != SCHEMA:
        _fail("unsupported manifest schema")
    rules, tables = value["rules"], value["tables"]
    if not isinstance(rules, list) or not isinstance(tables, list):
        _fail("corrupted resource arrays")
    parsed_rules: dict[int, list[str]] = {}
    parsed_tables: dict[str, list[str]] = {}
    for item in rules:
        if not isinstance(item, dict) or set(item) != {"number", "argv"} or \
           type(item["number"]) is not int or item["number"] in parsed_rules:
            _fail("invalid or duplicate IPFW rule record")
        parsed_rules[item["number"]] = item["argv"]
    for item in tables:
        if not isinstance(item, dict) or set(item) != {"name", "addresses"} or \
           not isinstance(item["name"], str) or item["name"] in parsed_tables:
            _fail("invalid or duplicate IPFW table record")
        parsed_tables[item["name"]] = item["addresses"]
    parsed = {
        "rule_base": value["rule_base"], "rule_max": value["rule_max"],
        "rules": parsed_rules, "tables": parsed_tables,
    }
    if canonical_manifest(parsed) != value:
        _fail("noncanonical or corrupted ownership manifest")
    return parsed


def fingerprint(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class VoiceOwnershipStore:
    """Disk-only ledger. Must run with caller-held native lifecycle lock."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._check_directory()

    def _check_directory(self) -> None:
        try:
            status = os.lstat(self.directory)
        except OSError as exc:
            raise LedgerError("private Voice ledger directory is missing") from exc
        if not stat.S_ISDIR(status.st_mode) or status.st_uid != os.geteuid() or \
           status.st_mode & 0o077:
            _fail("Voice ledger directory must be a real owner-private directory")

    def _location(self, name: str) -> Path:
        if name not in FILES:
            _fail("unknown Voice ledger file")
        return self.directory / name

    def _read(self, name: str) -> dict | None:
        self._check_directory()
        filename = self._location(name)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(filename, flags)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise LedgerError("cannot securely open Voice ledger file") from exc
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or \
               info.st_uid != os.geteuid() or info.st_mode & 0o077 or \
               info.st_size > MAX_FILE_BYTES:
                _fail("Voice ledger file is not private or regular")
            raw = handle.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                _fail("Voice ledger is oversized")
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise LedgerError("corrupted Voice ledger JSON") from exc
        if not isinstance(record, dict) or set(record) != {"payload", "sha256"} or \
           not isinstance(record["payload"], dict) or \
           record["sha256"] != fingerprint(record["payload"]):
            _fail("Voice ledger checksum/shape mismatch")
        return record["payload"]

    def _write(self, name: str, payload: dict) -> None:
        self._check_directory()
        destination = self._location(name)
        # Verify that an existing target is trustworthy BEFORE replacing.
        self._read(name)
        record = {"payload": payload, "sha256": fingerprint(payload)}
        raw = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True)
               + "\n").encode("utf-8")
        if len(raw) > MAX_FILE_BYTES:
            _fail("Voice ledger exceeds maximum size")
        fd, temporary = tempfile.mkstemp(prefix=".voice-ledger-", dir=self.directory)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as file:
                fd = -1
                file.write(raw)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, destination)
            self._sync_directory()
        finally:
            if fd != -1:
                os.close(fd)
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _sync_directory(self) -> None:
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _remove(self, name: str) -> None:
        if self._read(name) is None:
            _fail("Voice ledger file unexpectedly absent")
        os.unlink(self._location(name))
        self._sync_directory()

    def owned(self) -> dict | None:
        payload = self._read("ownership.json")
        return None if payload is None else decode_manifest(payload)

    def pending(self) -> dict | None:
        payload = self._read("intent.json")
        if payload is None:
            return None
        if not isinstance(payload, dict) or set(payload) != {
            "schema", "phase", "previous", "desired", "previous_sha256",
            "desired_sha256",
        } or payload["schema"] != SCHEMA or \
           payload["phase"] not in ("prepared", "mutating"):
            _fail("invalid Voice intent schema")
        previous = decode_manifest(payload["previous"])
        desired = decode_manifest(payload["desired"])
        if fingerprint(payload["previous"]) != payload["previous_sha256"] or \
           fingerprint(payload["desired"]) != payload["desired_sha256"] or \
           previous["rule_base"] != desired["rule_base"] or \
           previous["rule_max"] != desired["rule_max"]:
            _fail("Voice intent is inconsistent")
        return payload

    def seed(self, verified_previous: dict) -> None:
        """One-time opt-in adoption AFTER caller independently verified kernel state.

        Does not interrogate the router and must not be used to auto-adopt the
        old Telegram PoC or foreign rules during upgrade.
        """
        if self._read("ownership.json") is not None or self.pending() is not None:
            _fail("Voice ownership is already initialized")
        self._write("ownership.json", canonical_manifest(verified_previous))

    def begin(self, previous: dict, desired: dict) -> None:
        if self.pending() is not None:
            _fail("unfinished Voice IPFW intent requires recovery review")
        stored = self._read("ownership.json")
        if stored is None or stored != canonical_manifest(previous):
            _fail("untrusted or missing previous Voice ownership")
        current, target = canonical_manifest(previous), canonical_manifest(desired)
        if (current["rule_base"], current["rule_max"]) != (
            target["rule_base"], target["rule_max"]
        ):
            _fail("Voice IPFW rule range changed unexpectedly")
        self._write("intent.json", {
            "schema": SCHEMA, "phase": "prepared",
            "previous": current, "desired": target,
            "previous_sha256": fingerprint(current),
            "desired_sha256": fingerprint(target),
        })

    def mark_mutating(self) -> None:
        pending = self.pending()
        if pending is None or pending["phase"] != "prepared":
            _fail("Voice IPFW intent not prepared")
        self._write("intent.json", {**pending, "phase": "mutating"})

    def commit(self, expected_desired: dict) -> None:
        """Caller MUST verify desired kernel state and runtime before commit."""
        pending = self.pending()
        if pending is None or pending["phase"] != "mutating" or \
           canonical_manifest(expected_desired) != pending["desired"]:
            _fail("cannot commit unverified or missing Voice IPFW intent")
        self._write("ownership.json", pending["desired"])
        # The intent stays durable until post-commit table cleanup has been
        # separately verified. A crash here must not silently erase evidence.

    def inspect(self, adapter) -> str:
        """READ-ONLY restart triage; never deletes unknown kernel resources."""
        intent = self.pending()
        if intent is None:
            return "no-pending-intent"
        first, last = intent["previous"]["rule_base"], intent["previous"]["rule_max"]
        live_rules = adapter.list_rules(first, last)
        prev = decode_manifest(intent["previous"])
        want = decode_manifest(intent["desired"])
        prev_tables, want_tables = prev["tables"], want["tables"]
        # Without a recorded per-operation stage phase, an orphan _stage
        # table is ambiguous even when active rules happen to match.
        # Fail closed rather than accepting a stale/foreign stage as safe.
        if any(adapter.get_table(TABLE_PREFIX + name + "_stage") is not None
               for name in SERVICES):
            return "manual-review"
        live_tables = {
            TABLE_PREFIX + name: adapter.get_table(TABLE_PREFIX + name)
            for name in SERVICES
        }
        known_active = lambda tables: all(
            table_contents_equal(live_tables[name], tables.get(name)) for name in live_tables
        )
        if live_rules == prev["rules"] and known_active(prev_tables):
            return "previous-intact"
        if live_rules == want["rules"] and known_active(want_tables):
            return "desired-intact"
        return "manual-review"

    def abort(self, adapter) -> None:
        """Discard an intent ONLY when exactly the trusted previous kernel state survives.

        A crash during incomplete installation or any lingering staging table
        must not silently clear the evidence needed for operator recovery.
        """
        intent = self.pending()
        if intent is None or self.inspect(adapter) != "previous-intact" or \
           self._read("ownership.json") != intent["previous"]:
            _fail("cannot abort Voice intent without verified previous kernel state")
        self._remove("intent.json")

    def finish(self, adapter) -> None:
        """Finish ONLY when desired is live and ALL stage tables are gone."""
        intent = self.pending()
        if intent is None or self.inspect(adapter) != "desired-intact" or \
           self._read("ownership.json") != intent["desired"]:
            _fail("cannot finish Voice intent before verified desired state")
        for name in SERVICES:
            if adapter.get_table(TABLE_PREFIX + name + "_stage") is not None:
                _fail("Voice staging tables must be cleaned before finishing")
        self._remove("intent.json")
