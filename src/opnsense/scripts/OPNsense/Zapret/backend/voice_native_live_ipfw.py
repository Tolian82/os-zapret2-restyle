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

from voice_firewall_transaction import SERVICES, TABLE_PREFIX
from voice_ipfw_adapter import (
    FreeBSDIPFWAdapter, IPFWAdapterError, checked_rule_argv,
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
