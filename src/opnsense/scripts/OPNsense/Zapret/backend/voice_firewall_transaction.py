#!/usr/bin/env python3
"""Transactional Voice IPFW rule/table algorithm (adapter-injected, NOT wired).

An adapter represents IPFW. Production adapter, lifecycle locking and
persistent ownership manifest are intentionally NOT included in this patch.
No executable CLI entrypoint is exposed and importing this module never
touches the kernel. Unit tests inject an in-memory IPFW simulator.
"""
from __future__ import annotations

from copy import deepcopy
import ipaddress
import re

SERVICES = ("telegram", "discord", "x", "sip", "custom")
TABLE_PREFIX = "zapret2_voice_"
PORTS = re.compile(r"^[0-9,-]+$")


class VoiceFirewallError(RuntimeError):
    pass


def table_contents_equal(observed, expected) -> bool:
    """IPFW tables are sets; their native list output order is not stable."""
    if observed is None or expected is None:
        return observed is None and expected is None
    if not isinstance(observed, list) or not isinstance(expected, list):
        return False
    if any(not isinstance(x, str) for x in observed + expected):
        return False
    if len(observed) != len(expected) or len(set(observed)) != len(observed):
        return False
    return set(observed) == set(expected)


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
    previous_service_index = -1
    for record in voice:
        if not isinstance(record, dict) or record.get("service") not in SERVICES:
            raise VoiceFirewallError("invalid Voice service record")
        name = record["service"]
        index = SERVICES.index(name)
        if index <= previous_service_index:
            raise VoiceFirewallError("Voice services are reordered or duplicated")
        previous_service_index = index
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
        if len(destinations) != record.get("destination_count"):
            raise VoiceFirewallError("Voice target count mismatch")
        canonical = []
        for destination in destinations:
            try:
                network = ipaddress.IPv4Network(
                    destination if "/" in destination else destination + "/32", strict=True
                )
            except ValueError as error:
                raise VoiceFirewallError("invalid Voice IPv4 destination") from error
            normal = str(network) if "/" in destination else str(network.network_address)
            if destination != normal:
                raise VoiceFirewallError("noncanonical Voice IPv4 destination")
            canonical.append(destination)
        if len(set(canonical)) != len(canonical):
            raise VoiceFirewallError("duplicate Voice IPv4 destination")
        if table in tables:
            raise VoiceFirewallError("duplicate Voice service")
        tables[table] = canonical
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
        if not table_contents_equal(actual, expected):
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
    deleted_old_rules = set()
    installed_rules = set()
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
            deleted_old_rules.add(number)
        for number, argv in sorted(desired["rules"].items()):
            # Only a successful add is ours. If a concurrent foreign rule
            # wins this number, never delete it during rollback.
            adapter.add_rule(number, argv)
            installed_rules.add(number)
    except Exception as original:
        # Roll back rules first while active tables still exist.
        rollback_errors = []
        for number in sorted(installed_rules):
            try:
                adapter.delete_rule(number)
            except Exception as exc:
                rollback_errors.append(str(exc))
        for number, argv in sorted(previous["rules"].items()):
            if number not in deleted_old_rules:
                continue
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



def plan_postcommit_cleanup(adapter, previous: dict, desired: dict) -> list[tuple[str, str, list[str]]]:
    """Plan cleanup only for verified obsolete and stage tables, without touching IPFW.

    Call after installing desired rules AND a durable ownership commit.
    Failed/partial cleanup can be retried, but only with the caller-held
    lifecycle lock. An unknown table or orphan stage fails closed.
    """
    if previous["rule_base"] != desired["rule_base"] or \
       previous["rule_max"] != desired["rule_max"]:
        raise VoiceFirewallError("cleanup ownership range changed")
    if adapter.list_rules(desired["rule_base"], desired["rule_max"]) != desired["rules"]:
        raise VoiceFirewallError("cannot clean Voice tables: live rules differ from commit")
    prior_tables, desired_tables = previous["tables"], desired["tables"]
    if any(name not in (TABLE_PREFIX + n for n in SERVICES)
           for name in set(prior_tables) | set(desired_tables)):
        raise VoiceFirewallError("unexpected table in cleanup manifest")
    steps: list[tuple[str, str, list[str]]] = []
    for service in SERVICES:
        name = TABLE_PREFIX + service
        active = adapter.get_table(name)
        stage = adapter.get_table(name + "_stage")
        if name in desired_tables:
            if not table_contents_equal(active, desired_tables[name]):
                raise VoiceFirewallError(f"Voice committed table mismatch: {name}")
            # After swap, stage contains old active contents. New table's
            # stage is empty. Already-cleaned stage is also valid on retry.
            allowed_stage = prior_tables.get(name, [])
            if stage is not None and not table_contents_equal(stage, allowed_stage):
                raise VoiceFirewallError(f"Voice staging table changed unexpectedly: {name}")
            if stage is not None:
                steps.append(("stage", name + "_stage", list(stage)))
        elif name in prior_tables:
            # A just-disabled service loses its rule immediately; its
            # previous table is removed only after durable ownership commit.
            if active is not None and not table_contents_equal(active, prior_tables[name]):
                raise VoiceFirewallError(f"unowned retired Voice table: {name}")
            if stage is not None:
                raise VoiceFirewallError(f"unexpected retired Voice stage table: {name}")
            if active is not None:
                steps.append(("retired", name, list(active)))
        elif active is not None or stage is not None:
            raise VoiceFirewallError(f"unexpected foreign Voice table: {name}")
    return steps


def rollback_uncommitted(adapter, previous: dict, desired: dict) -> None:
    """Restore the exact prior IPFW state while the whole cutover is uncommitted.

    This is a REAL reversible precommit operation. It requires the installed
    desired rules and all preserved old contents in the stage tables. A
    partially damaged/foreign state fails closed and retains the durable
    intent for operator recovery; it is never guessed or swept.
    """
    # This validates the full installed desired rules, every Voice table,
    # the former contents of all swapped stages and any retired tables.
    # No mutation occurs if the live state does not match the journal.
    plan_postcommit_cleanup(adapter, previous, desired)
    if adapter.list_rules(desired["rule_base"], desired["rule_max"]) != desired["rules"]:
        raise VoiceFirewallError("installed Voice cutover rules changed before rollback")
    for name in desired["tables"]:
        stage = name + "_stage"
        if adapter.get_table(stage) is None:
            raise VoiceFirewallError(
                "missing prior Voice table snapshot; rollback requires manual review"
            )
    try:
        for number in sorted(desired["rules"]):
            adapter.delete_rule(number)
        for number, argv in sorted(previous["rules"].items()):
            adapter.add_rule(number, argv)
        # New active tables were not owned by the previous release. Existing
        # tables are swapped BACK before their stage snapshots are removed.
        for name in desired["tables"]:
            stage = name + "_stage"
            if name in previous["tables"]:
                adapter.swap_tables(name, stage)
                adapter.destroy_table(stage)
            else:
                adapter.destroy_table(name)
                adapter.destroy_table(stage)
        verify_prior_state(adapter, previous, previous)
    except Exception as error:
        # The cross-resource journal and IPFW intent are deliberately left
        # intact. Never claim rollback if even one kernel command failed.
        raise VoiceFirewallError(
            "Voice IPFW rollback incomplete; durable intent retained for review"
        ) from error


def cleanup_committed(adapter, previous: dict, desired: dict) -> None:
    """Retryable post-commit cleanup; never remove unverified table contents."""
    steps = plan_postcommit_cleanup(adapter, previous, desired)
    for _, name, expected in steps:
        if not table_contents_equal(adapter.get_table(name), expected):
            raise VoiceFirewallError(f"Voice table changed during cleanup: {name}")
        adapter.destroy_table(name)
    # Callers must re-check desired kernel state and finish the intent after
    # cleanup. This function never silently clears the durable journal.
