#!/usr/bin/env python3
"""Transactional Voice IPFW rule/table algorithm (adapter-injected, NOT wired).

An adapter represents IPFW. Production adapter, lifecycle locking and
persistent ownership manifest are intentionally NOT included in this patch.
No executable CLI entrypoint is exposed and importing this module never
touches the kernel. Unit tests inject an in-memory IPFW simulator.
"""
from __future__ import annotations

from copy import deepcopy
import re

SERVICES = ("telegram", "discord", "x", "sip", "custom")
TABLE_PREFIX = "zapret2_voice_"
PORTS = re.compile(r"^[0-9,-]+$")


class VoiceFirewallError(RuntimeError):
    pass


def _validate_port_string(text: str, label: str) -> str:
    if not isinstance(text, str) or (text and not PORTS.fullmatch(text)):
        raise VoiceFirewallError(f"{label}: invalid ordinary port specification")
    if not text:
        return ""
    for part in text.split(","):
        try:
            endpoints = [int(value) for value in part.split("-")]
        except ValueError as exc:
            raise VoiceFirewallError(f"{label}: invalid port") from exc
        if not 1 <= len(endpoints) <= 2 or not (1 <= endpoints[0] <= 65535) or not (
            1 <= endpoints[-1] <= 65535
        ) or endpoints[0] > endpoints[-1]:
            raise VoiceFirewallError(f"{label}: invalid port range")
    return text


def prepare_desired(capture_plan: dict, tcp: str, udp: str) -> dict:
    """Turn a validated capture plan into an explicit plugin-owned manifest."""
    if not isinstance(capture_plan, dict) or capture_plan.get("schema") != 1:
        raise VoiceFirewallError("invalid capture plan schema")
    first, last = capture_plan.get("rule_base"), capture_plan.get("rule_max")
    ordinary_first = capture_plan.get("ordinary_rule_base")
    divert = capture_plan.get("divert_port")
    wan = capture_plan.get("wan")
    if type(first) is not int or type(last) is not int or type(ordinary_first) is not int:
        raise VoiceFirewallError("invalid plugin rule range")
    if not 1 <= first <= ordinary_first <= last <= 65534 or \
       type(divert) is not int or not 1 <= divert <= 65535 or \
       not isinstance(wan, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}", wan):
        raise VoiceFirewallError("unsafe plugin rule range, WAN or divert port")
    tcp = _validate_port_string(tcp, "ordinary TCP")
    udp = _validate_port_string(udp, "ordinary UDP")
    if not tcp and not udp:
        raise VoiceFirewallError("ordinary Strategy has neither TCP nor UDP ports")
    rules: dict[int, list[str]] = {}
    tables: dict[str, list[str]] = {}
    voice = capture_plan.get("voice")
    if not isinstance(voice, list) or len(voice) > len(SERVICES):
        raise VoiceFirewallError("invalid service count")
    expected_rule = first
    for record in voice:
        if not isinstance(record, dict) or record.get("service") not in SERVICES:
            raise VoiceFirewallError("invalid Voice service record")
        name = record["service"]
        table = TABLE_PREFIX + name
        if record.get("table") != table or record.get("rule") != expected_rule:
            raise VoiceFirewallError("nonsequential or inconsistent Voice rule")
        argv = record.get("argv")
        if not isinstance(argv, list) or not argv or any(
            not isinstance(item, str) for item in argv
        ):
            raise VoiceFirewallError("invalid Voice IPFW argument vector")
        if argv[:7] != ["divert", str(divert), "udp", "from", "any", "to", f"table({table})"] \
           or argv[-7:] != ["out", "not", "diverted", "not", "sockarg", "xmit", wan]:
            raise VoiceFirewallError("Voice IPFW arguments outside destination-scoped contract")
        expression = argv[7:-7]
        if len(expression) > 1:
            raise VoiceFirewallError("invalid Voice UDP port selector")
        if expression:
            _validate_port_string(expression[0], f"{name} UDP")
        destinations = record.get("destinations")
        if not isinstance(destinations, list) or not destinations or any(
            not isinstance(value, str) or not value for value in destinations
        ):
            raise VoiceFirewallError("empty or invalid Voice destination table")
        if table in tables:
            raise VoiceFirewallError("duplicate Voice service")
        tables[table] = list(destinations)
        rules[expected_rule] = list(argv)
        expected_rule += 1
    if expected_rule != ordinary_first:
        raise VoiceFirewallError("ordinary rule range overlaps Voice")
    next_number = ordinary_first
    guards = ["out", "not", "diverted", "not", "sockarg", "xmit", wan]
    for proto, ports in (("tcp", tcp), ("udp", udp)):
        if ports:
            if next_number > last:
                raise VoiceFirewallError("ordinary rules exceed plugin-owned rule range")
            rules[next_number] = ["divert", str(divert), proto, "from", "any",
                                  "to", "any", ports, *guards]
            next_number += 1
    return {"rule_base": first, "rule_max": last, "rules": rules, "tables": tables}


def verify_prior_state(adapter, previous: dict, desired: dict) -> None:
    """Fail closed if unowned/modified live rules or tables are found."""
    if not isinstance(previous, dict) or not isinstance(previous.get("rules"), dict) or \
       not isinstance(previous.get("tables"), dict):
        raise VoiceFirewallError("missing trusted previous ownership manifest")
    if previous.get("rule_base") != desired["rule_base"] or \
       previous.get("rule_max") != desired["rule_max"]:
        raise VoiceFirewallError("previous rule ownership range differs")
    current = adapter.list_rules(desired["rule_base"], desired["rule_max"])
    if current != previous["rules"]:
        raise VoiceFirewallError("foreign or modified rules in plugin-owned range")
    expected_table_names = set(previous["tables"]) | set(desired["tables"])
    expected_table_names.update(TABLE_PREFIX + name for name in SERVICES)
    for table in expected_table_names:
        actual = adapter.get_table(table)
        expected = previous["tables"].get(table)
        if actual != expected:
            raise VoiceFirewallError(f"foreign or modified IPFW table: {table}")
        if adapter.get_table(table + "_stage") is not None:
            raise VoiceFirewallError(f"stale or foreign IPFW stage table: {table}")


def apply_transaction(adapter, previous: dict, desired: dict) -> None:
    """Change only verified owned state, then restore it on an install failure.

    Requires caller-held exclusive lifecycle lock and a trusted previously
    committed manifest. Previous table removal/cleanup is post-commit and
    remains a separate lifecycle step, not performed here.
    """
    verify_prior_state(adapter, previous, desired)
    staged = []
    swapped = []
    newly_created = []
    prior_rule_numbers = set(previous["rules"])
    attempted_rules = set()
    try:
        # Prepare every new target set without disturbing active entries.
        for table, addresses in desired["tables"].items():
            stage = table + "_stage"
            adapter.create_table(stage)
            staged.append(stage)
            for address in addresses:
                adapter.add_table_entry(stage, address)
        # Atomically swap address contents, with old sets retained in stages.
        for table in desired["tables"]:
            if adapter.get_table(table) is None:
                adapter.create_table(table)
                newly_created.append(table)
            adapter.swap_tables(table, table + "_stage")
            swapped.append(table)
        # Existing verified plugin rules only. Never sweep the whole numeric
        # range or delete an unrelated rule that was not in previous manifest.
        for number in sorted(prior_rule_numbers):
            adapter.delete_rule(number)
        for number, argv in sorted(desired["rules"].items()):
            attempted_rules.add(number)
            adapter.add_rule(number, argv)
    except Exception as original:
        # Roll back rules first while active tables still exist.
        rollback_errors = []
        for number in sorted(attempted_rules):
            try:
                adapter.delete_rule(number)
            except Exception as exc:
                rollback_errors.append(str(exc))
        for number, argv in sorted(previous["rules"].items()):
            try:
                adapter.add_rule(number, argv)
            except Exception as exc:
                rollback_errors.append(str(exc))
        for table in reversed(swapped):
            if table in newly_created:
                try:
                    adapter.destroy_table(table)
                except Exception as exc:
                    rollback_errors.append(str(exc))
            else:
                try:
                    adapter.swap_tables(table, table + "_stage")
                except Exception as exc:
                    rollback_errors.append(str(exc))
        for table in newly_created:
            if table not in swapped:
                try:
                    adapter.destroy_table(table)
                except Exception as exc:
                    rollback_errors.append(str(exc))
        for stage in reversed(staged):
            try:
                adapter.destroy_table(stage)
            except Exception as exc:
                rollback_errors.append(str(exc))
        if rollback_errors:
            raise VoiceFirewallError(
                "Voice IPFW activation failed; rollback incomplete; appliance inspection required"
            ) from original
        raise VoiceFirewallError("Voice IPFW activation failed; previous owned state restored") from original
    # No errors: ordinary rules and Voice targets are now installed.
    # Keep old stage snapshots until orchestrator commits the replacement
    # and atomically records the new ownership manifest.
    # The orchestrator MUST finish/clean all stages after the commit.

