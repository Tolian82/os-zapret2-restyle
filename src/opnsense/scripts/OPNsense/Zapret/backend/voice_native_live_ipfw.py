#!/usr/bin/env python3
"""Read-only pre-cutover FreeBSD IPFW inventory, without ownership adoption.

This audits ONLY the fixed 19000..19010 plugin interval and bounded, fixed
Voice native/old-PoC table names. A live ordinary Zapret2 installation must
contain only already-running ordinary TCP/UDP divert rules, without Voice
destination tables, stale stage tables or legacy Telegram PoC tables.
The divert socket and WAN must agree across all ordinary rules, with the
actual dvtws2 --port=NNNN argument.

This is structural evidence, NOT proof of ledger ownership, correct WAN
routing, UDP media pass, IPFW readiness or permission to enable Voice.
No write path and no broader kernel sweep or custom rule deletion.
"""
from __future__ import annotations

import re

from voice_firewall_transaction import SERVICES, TABLE_PREFIX
from voice_ipfw_adapter import (
    FreeBSDIPFWAdapter, IPFWAdapterError, checked_rule_argv, checked_ipv4,
    RULE_LINE, TABLE_ENTRY, MAX_LINES, MAX_TABLE_ENTRIES, INTERFACE,
)
from voice_firewall_ledger import fingerprint

RULE_BASE=19000
RULE_MAX=19010
OLD_TABLE="zapret2_tgvoice"
OLD_STAGE="zapret2_tgvoice_stage"


class LiveIPFWError(RuntimeError):
    pass


def _engine_port(argv):
    ports=[word.split("=",1)[1] for word in argv[1:]
           if word.startswith("--port=")]
    if len(ports)!=1 or not ports[0].isdecimal() or (
        not 1<=int(ports[0])<=65535
    ):
        raise LiveIPFWError("live engine does not expose one bounded divert port")
    return ports[0]


def observe_ordinary_ipfw(adapter, engine_argv):
    """Return stable, bounded *structural* inventory; never claim IPFW ownership."""
    if not isinstance(adapter,FreeBSDIPFWAdapter) or adapter.allow_mutations is not False or (
        adapter.rule_base!=RULE_BASE or adapter.rule_max!=RULE_MAX
    ):
        raise LiveIPFWError("untrusted or mutating live Voice IPFW reader")
    port=_engine_port(engine_argv)
    try:
        rules=adapter.list_rules(RULE_BASE,RULE_MAX)
        if not 1<=len(rules)<=2:
            raise LiveIPFWError("ordinary TCP/UDP IPFW footprint is incomplete or foreign")
        protocols=set()
        wan=None
        for number,argv in sorted(rules.items()):
            checked_rule_argv(argv)
            if argv[2] not in ("tcp","udp") or argv[6]!="any" or (
                len(argv)!=15 or argv[1]!=port
            ):
                raise LiveIPFWError("non-ordinary or foreign rule in Voice interval")
            protocol=argv[2]
            if protocol in protocols:
                raise LiveIPFWError("duplicate ordinary IPFW protocol")
            protocols.add(protocol)
            if wan is None:
                wan=argv[-1]
            elif wan!=argv[-1]:
                raise LiveIPFWError("ordinary TCP/UDP rules disagree on WAN")
        for service in SERVICES:
            name=TABLE_PREFIX+service
            if adapter.get_table(name) is not None or (
                adapter.get_table(name+"_stage") is not None
            ):
                raise LiveIPFWError("native Voice table/stage remains in live kernel")
        # Legacy PoC table is explicitly NOT owned by the native Voice adapter.
        # Probe only these two fixed legacy names. No arbitrary table argument.
        if adapter._run("table",OLD_TABLE,"info",allow_missing=True) is not None or (
            adapter._run("table",OLD_STAGE,"info",allow_missing=True) is not None
        ):
            raise LiveIPFWError("legacy Telegram Voice table remains in kernel")
        record={
            "rule_base":RULE_BASE,"rule_max":RULE_MAX,
            "rules":{str(n):v for n,v in sorted(rules.items())},
            "wan":wan,"port":port,
        }
        return {
            "state":"unseeded-ordinary-structure-only",
            "rule_count":len(rules),
            "protocols":sorted(protocols),
            "structure_sha256":fingerprint(record),
            "kernel_ownership":"not-attested",
            "voice_tables":"absent",
            "legacy_table":"absent",
        }
    except (IPFWAdapterError,ValueError) as exc:
        if isinstance(exc,LiveIPFWError):
            raise
        raise LiveIPFWError("untrusted live FreeBSD IPFW evidence") from exc


def observe_legacy_poc_ipfw(adapter, engine_argv, expected_ipv4):
    """Attest historical Telegram PoC rules without adopting their ownership.

    expected_ipv4 must be obtained from the pinned managed runtime by a
    future FD9/Config-flock coordinator, never from the observed IPFW table.
    This function never authorizes mutation or calls the ordinary native
    adapter's rule parser, which intentionally excludes the old table name.
    """
    if not isinstance(adapter, FreeBSDIPFWAdapter) or (
        adapter.allow_mutations or
        (adapter.rule_base, adapter.rule_max) != (RULE_BASE, RULE_MAX)
    ):
        raise LiveIPFWError("untrusted read-only legacy IPFW adapter")
    if not isinstance(expected_ipv4, (tuple, list)) or (
        not 1 <= len(expected_ipv4) <= MAX_TABLE_ENTRIES
    ):
        raise LiveIPFWError("untrusted legacy managed IPv4 set")
    try:
        targets = [checked_ipv4(x) for x in expected_ipv4]
    except IPFWAdapterError as exc:
        raise LiveIPFWError("invalid managed Telegram IP address") from exc
    if len(set(targets)) != len(targets):
        raise LiveIPFWError("duplicate managed Telegram target")
    port = _engine_port(engine_argv)

    def sample():
        try:
            lines = adapter._run("-q", "list").splitlines()
            if len(lines) > MAX_LINES:
                raise LiveIPFWError("oversized legacy rule listing")
            rules = {}
            for line in lines:
                if not line.strip():
                    continue
                match = RULE_LINE.fullmatch(line)
                if match is None:
                    raise LiveIPFWError("malformed legacy rule listing")
                number = int(match.group(1))
                if RULE_BASE <= number <= RULE_MAX:
                    if number in rules:
                        raise LiveIPFWError("duplicate legacy rule")
                    rules[number] = match.group(2).split()
            if len(rules) not in (2, 3) or (
                sorted(rules) != list(range(RULE_BASE, RULE_BASE + len(rules)))
            ):
                raise LiveIPFWError("legacy rule layout incomplete or foreign")
            old = rules[RULE_BASE]
            if len(old) != 14 or old[:7] != [
                "divert", port, "udp", "from", "any", "to", f"table({OLD_TABLE})"
            ] or old[7:13] != [
                "out", "not", "diverted", "not", "sockarg", "xmit"
            ] or not INTERFACE.fullmatch(old[-1]):
                raise LiveIPFWError("unexpected legacy Telegram rule")
            protocols = set()
            for number in sorted(rules)[1:]:
                row = rules[number]
                checked_rule_argv(row)
                if len(row) != 15 or row[6] != "any" or (
                    row[1] != port or row[-1] != old[-1]
                    or row[2] in protocols
                ):
                    raise LiveIPFWError("unexpected ordinary rule in legacy IPFW")
                protocols.add(row[2])
            for service in SERVICES:
                name = TABLE_PREFIX + service
                if adapter.get_table(name) is not None or (
                    adapter.get_table(name + "_stage") is not None
                ):
                    raise LiveIPFWError("native tables conflict with legacy PoC")
            if adapter._run("table", OLD_STAGE, "info", allow_missing=True) is not None:
                raise LiveIPFWError("legacy staging table still present")
            info = adapter._run("table", OLD_TABLE, "info", allow_missing=True)
            if info is None or not re.search(r"(?im)\btype\s*:\s*addr\b", info):
                raise LiveIPFWError("legacy IPv4 table absent or wrong type")
            entries = []
            for line in adapter._run("table", OLD_TABLE, "list").splitlines():
                if not line.strip():
                    continue
                match = TABLE_ENTRY.fullmatch(line)
                if match is None:
                    raise LiveIPFWError("malformed legacy IPv4 entry")
                raw = match.group(1)
                entries.append(checked_ipv4(raw[:-3] if raw.endswith("/32") else raw))
                if len(entries) > MAX_TABLE_ENTRIES:
                    raise LiveIPFWError("oversized legacy table")
            if len(set(entries)) != len(entries) or set(entries) != set(targets):
                raise LiveIPFWError("legacy table mismatches trusted managed IPSET")
            return {"rules": {str(k): rules[k] for k in sorted(rules)},
                    "targets": sorted(entries), "wan": old[-1], "port": port}
        except (IPFWAdapterError, ValueError) as exc:
            raise LiveIPFWError("untrusted legacy IPFW evidence") from exc

    first = sample()
    if first != sample():
        raise LiveIPFWError("legacy IPFW changed during inspection")
    return {"state": "legacy-ipfw-observed-not-owned",
            "structure_sha256": fingerprint(first),
            "legacy_ipv4_count": len(targets),
            "ordinary_rule_count": len(first["rules"]) - 1,
            "kernel_ownership": "not-adopted", "safe_to_mutate": False,
            "safe_to_enable_voice": False, "public_voice_apply": False}
