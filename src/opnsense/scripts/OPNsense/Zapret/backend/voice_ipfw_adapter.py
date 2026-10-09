#!/usr/bin/env python3
"""Bounded FreeBSD IPFW adapter for the isolated Voice transaction work.

The adapter is NOT invoked by zapret_service.sh or the normal orchestrator.
It defaults to read-only. A caller may enable mutation only while holding
the existing lifecycle lock, after a trusted ownership manifest has been
loaded and a durable intent has been fsync'd.

No shell execution, arbitrary table/rule names, unbounded subprocess output,
or automatic adoption of existing/foreign rule numbers is permitted.
"""
from __future__ import annotations

import ipaddress
import re
import subprocess
from typing import Callable, Sequence

from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError,
)

MAX_IPFW_OUTPUT = 2 * 1024 * 1024
MAX_LINES = 8192
MAX_TABLE_ENTRIES = 4096
MAX_ARGS = 24
RULE_LINE = re.compile(r"^\s*([0-9]{1,5})\s+(.+?)\s*$")
TABLE_ENTRY = re.compile(r"^\s*(\S+)(?:\s+([0-9]+))?\s*$")
INTERFACE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
NUMERIC_PORTS = re.compile(r"^[0-9,-]{1,1024}$")
# FreeBSD ipfw table info for an absent table varies across versions.
# Only these explicit errors mean nonexistence; any other error fails closed.
MISSING_TABLE = re.compile(
    r"(table.+(?:does not exist|not found|no such table)|"
    r"(?:does not exist|no such table).+table)",
    re.IGNORECASE,
)


class IPFWAdapterError(VoiceFirewallError):
    pass


def checked_table_name(name: str) -> str:
    if name not in (
        TABLE_PREFIX + service + suffix
        for service in SERVICES
        for suffix in ("", "_stage")
    ):
        raise IPFWAdapterError("table is outside Voice-owned name allowlist")
    return name


def checked_rule_number(number: int, first: int, last: int) -> int:
    if type(number) is not int or not first <= number <= last <= 65534:
        raise IPFWAdapterError("rule number outside plugin-owned interval")
    return number


def checked_ipv4(value: str) -> str:
    if not isinstance(value, str):
        raise IPFWAdapterError("IPFW address must be a string")
    try:
        net = ipaddress.IPv4Network(
            value if "/" in value else value + "/32", strict=True
        )
    except ValueError as error:
        raise IPFWAdapterError("invalid Voice IPv4/CIDR") from error
    canon = str(net) if "/" in value else str(net.network_address)
    if value != canon:
        raise IPFWAdapterError("noncanonical Voice IPv4/CIDR")
    return canon


def checked_rule_argv(argv: Sequence[str]) -> list[str]:
    if not isinstance(argv, (list, tuple)) or not 14 <= len(argv) <= 15 or any(
        not isinstance(token, str) for token in argv
    ):
        raise IPFWAdapterError("unexpected owned rule structure")
    if argv[:6] != ["divert", argv[1], argv[2], "from", "any", "to"] or \
       not argv[1].isdecimal() or not 1 <= int(argv[1]) <= 65535 or \
       argv[2] not in ("udp", "tcp"):
        raise IPFWAdapterError("invalid IPFW divert/protocol")
    if argv[-7:-1] != ["out", "not", "diverted", "not", "sockarg", "xmit"] or \
       not INTERFACE.fullmatch(argv[-1]):
        raise IPFWAdapterError("unsafe WAN or missing divert loop guard")
    if argv[6] == "any":
        if len(argv) != 15:
            raise IPFWAdapterError("ordinary rule requires a port selector")
    elif argv[6] not in (f"table({TABLE_PREFIX}{service})" for service in SERVICES) or \
         argv[2] != "udp":
        raise IPFWAdapterError("destination scope outside Voice IPv4 tables")
    if len(argv) == 15:
        selector = argv[7]
        if not NUMERIC_PORTS.fullmatch(selector):
            raise IPFWAdapterError("unsafe UDP/TCP port selector")
        for token in selector.split(","):
            terms = token.split("-")
            if not 1 <= len(terms) <= 2 or any(
                not part.isdecimal() or not 1 <= int(part) <= 65535 for part in terms
            ) or int(terms[0]) > int(terms[-1]):
                raise IPFWAdapterError("invalid UDP/TCP port interval")
    return list(argv)


class FreeBSDIPFWAdapter:
    """Narrow IPFW process adapter with injectable runner for CI fixtures."""

    def __init__(self, rule_base: int, rule_max: int,
                 ipfw_binary: str = "/sbin/ipfw",
                 *, allow_mutations: bool = False,
                 runner: Callable | None = None):
        if type(rule_base) is not int or type(rule_max) is not int or \
           not 1 <= rule_base <= rule_max <= 65534:
            raise IPFWAdapterError("invalid Voice owned rule interval")
        if ipfw_binary != "/sbin/ipfw":
            raise IPFWAdapterError("unsupported IPFW executable path")
        self.rule_base, self.rule_max = rule_base, rule_max
        self.binary = ipfw_binary
        self.allow_mutations = allow_mutations
        self.runner = runner or subprocess.run

    def _run(self, *args: str, modifying: bool = False, allow_missing: bool = False):
        if modifying and not self.allow_mutations:
            raise IPFWAdapterError("Voice adapter is read-only until lifecycle preflight")
        if len(args) > MAX_ARGS or any(
            not isinstance(x, str) or not x or "\x00" in x for x in args
        ):
            raise IPFWAdapterError("invalid IPFW command tokens")
        result = self.runner(
            [self.binary, *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, check=False
        )
        if len(result.stdout) + len(result.stderr) > MAX_IPFW_OUTPUT:
            raise IPFWAdapterError("IPFW command output exceeds bound")
        if result.returncode != 0:
            if allow_missing and MISSING_TABLE.search(result.stderr):
                return None
            raise IPFWAdapterError("IPFW command failed: operation not completed")
        return result.stdout

    def _parse_rule_listing(self, text: str) -> dict[int, list[str]]:
        lines = text.splitlines()
        if len(lines) > MAX_LINES:
            raise IPFWAdapterError("IPFW rule listing is too large")
        rules: dict[int, list[str]] = {}
        for line in lines:
            if not line.strip():
                continue
            match = RULE_LINE.fullmatch(line)
            if match is None:
                raise IPFWAdapterError("unexpected IPFW list format")
            number, body = int(match.group(1)), match.group(2)
            if not self.rule_base <= number <= self.rule_max:
                continue
            if number in rules:
                raise IPFWAdapterError("duplicate IPFW rule number")
            # FreeBSD normalizes rules in 'ipfw list'; unsupported syntax
            # must NOT be accepted as plugin-owned or silently discarded.
            words = body.split()
            rules[number] = checked_rule_argv(words)
        return rules

    def list_rules(self, first: int, last: int) -> dict[int, list[str]]:
        if first != self.rule_base or last != self.rule_max:
            raise IPFWAdapterError("Voice requested rules outside owned range")
        output = self._run("-q", "list")
        return self._parse_rule_listing(output)

    def get_table(self, name: str) -> list[str] | None:
        name = checked_table_name(name)
        info = self._run("table", name, "info", allow_missing=True)
        if info is None:
            return None
        # Different installed table kinds (flow, iface, number) must not be
        # adopted as Voice IPv4 destination tables.
        if not re.search(r"(?im)\btype\s*:\s*addr\b", info):
            raise IPFWAdapterError("existing IPFW table is not address type")
        output = self._run("table", name, "list")
        values: list[str] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            match = TABLE_ENTRY.fullmatch(line)
            if not match:
                raise IPFWAdapterError("unexpected IPFW table listing format")
            raw_address = match.group(1)
            # FreeBSD often prints single-host keys as A.B.C.D/32 even
            # if the plugin's normalized managed file stores A.B.C.D.
            address = (raw_address[:-3] if raw_address.endswith("/32") else raw_address)
            address = checked_ipv4(address)
            if address in values:
                raise IPFWAdapterError("duplicate IPv4 in IPFW table")
            values.append(address)
            if len(values) > MAX_TABLE_ENTRIES:
                raise IPFWAdapterError("IPFW table exceeds configured bounds")
        return values

    def create_table(self, name: str) -> None:
        self._run("-q", "table", checked_table_name(name), "create", "type", "addr",
                  modifying=True)

    def destroy_table(self, name: str) -> None:
        self._run("-q", "table", checked_table_name(name), "destroy", modifying=True)

    def add_table_entry(self, name: str, address: str) -> None:
        self._run("-q", "table", checked_table_name(name), "add",
                  checked_ipv4(address), modifying=True)

    def swap_tables(self, active: str, stage: str) -> None:
        if not (active.startswith(TABLE_PREFIX) and stage == active + "_stage" and
                active in (TABLE_PREFIX + service for service in SERVICES)):
            raise IPFWAdapterError("invalid Voice table swap pair")
        self._run("-q", "table", active, "swap", stage, modifying=True)

    def delete_rule(self, number: int) -> None:
        number = checked_rule_number(number, self.rule_base, self.rule_max)
        self._run("-q", "delete", str(number), modifying=True)

    def add_rule(self, number: int, argv: Sequence[str]) -> None:
        number = checked_rule_number(number, self.rule_base, self.rule_max)
        arguments = checked_rule_argv(argv)
        self._run("-qf", "add", str(number), *arguments, modifying=True)
