#!/usr/bin/env python3
"""Opt-in real FreeBSD 15 IPFW table smoke in a disposable CI VM.

Never run on an installed OPNsense appliance: this script creates and swaps
existing plugin-named tables. It changes no IPFW rules, routes, or service.
The installed Stage 5 packet/reinjection/FD9 acceptance remains independent.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

ACTIVE = "zapret2_voice_custom"
STAGE = ACTIVE + "_stage"
FIRST = ["192.0.2.10", "2001:db8:1::/48", "2001:db8::10"]
SECOND = ["198.51.100.11", "2001:db8:2::/48", "2001:db8::11"]


def native(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False, timeout=15)


def safe_default_rules(text: str) -> bool:
    """Match the existing firewall_cold_load_ipfw FreeBSD15 allow-only gate."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    allow = 0
    for line in lines:
        if line == "65535 allow ip from any to any":
            allow += 1
        elif re.fullmatch(r"65535 count ip from any to any not(?: .*)?", line):
            # FreeBSD15 orphaned-dynamic-states counter on the default rule.
            continue
        else:
            print("STAGE5_NATIVE_TABLE=FAIL: foreign IPFW rule " + repr(line))
            return False
    return allow == 1


def prerequisite() -> bool:
    if os.getenv("ZAPRET2_ISOLATED_FREEBSD_VM_TABLE_TEST") != "1":
        print("STAGE5_NATIVE_TABLE=SKIP: isolated FreeBSD VM opt-in not set")
        return False
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        print("STAGE5_NATIVE_TABLE=SKIP: this test requires FreeBSD root in an isolated VM")
        return False
    if not Path("/sbin/ipfw").is_file():
        print("STAGE5_NATIVE_TABLE=SKIP: no native /sbin/ipfw")
        return False
    listing = native("/sbin/ipfw", "-q", "list")
    if listing.returncode == 0:
        # Do not modify even an isolated VM when an unrelated IPFW owner
        # has rules. The only safe baseline is the default allow rule.
        if not safe_default_rules(listing.stdout):
            raise RuntimeError("FreeBSD VM IPFW has non-default rules; refusing mutation")
        return True
    # Reuse the production cold-boot safety contract, but ONLY inside the
    # explicitly opted-in disposable VM. No owner OPNsense device is touched.
    module = native("/sbin/kldstat", "-q", "-m", "ipfw")
    if module.returncode != 1 or listing.returncode != 71 or (
        "retrieving config failed: Protocol not available" not in listing.stderr
    ):
        print("STAGE5_NATIVE_TABLE=SKIP: VM IPFW cold-load prerequisites are not verified")
        return False
    result = native("/bin/kenv", "net.inet.ip.fw.default_to_accept=1")
    if result.returncode != 0:
        print("STAGE5_NATIVE_TABLE=SKIP: cannot safely set guest default-accept")
        return False
    setting = native("/bin/kenv", "-qv", "net.inet.ip.fw.default_to_accept")
    if setting.returncode != 0 or setting.stdout.strip() not in (
        'net.inet.ip.fw.default_to_accept="1"',
        "net.inet.ip.fw.default_to_accept=1",
    ):
        print("STAGE5_NATIVE_TABLE=SKIP: default-accept not attested")
        return False
    loaded = native("/sbin/kldload", "ipfw")
    if loaded.returncode != 0:
        print("STAGE5_NATIVE_TABLE=SKIP: native IPFW module unavailable in CI VM")
        return False
    sysctl = native("/sbin/sysctl", "-n", "net.inet.ip.fw.default_to_accept")
    rules = native("/sbin/ipfw", "-q", "list")
    if sysctl.returncode != 0 or sysctl.stdout.strip() != "1" or rules.returncode != 0:
        raise RuntimeError("FreeBSD VM IPFW failed safe default-accept activation")
    if not safe_default_rules(rules.stdout):
        raise RuntimeError("FreeBSD VM IPFW default rules are not exclusively allow")
    return True


def run() -> int:
    if not prerequisite():
        return 0
    from voice_firewall_transaction import table_contents_equal
    from voice_ipfw_adapter import FreeBSDIPFWAdapter
    adapter = FreeBSDIPFWAdapter(19000, 19010, allow_mutations=True)
    # Fail before touching kernel ownership if any plugin table or rule exists.
    original_rules = adapter.list_rules(19000, 19010)
    if original_rules:
        raise RuntimeError("CI VM has pre-existing plugin-owned IPFW rules")
    if adapter.get_table(ACTIVE) is not None or adapter.get_table(STAGE) is not None:
        raise RuntimeError("CI VM has pre-existing plugin-owned IPFW tables")
    created: list[str] = []
    result = "FAIL"
    try:
        adapter.create_table(ACTIVE)
        created.append(ACTIVE)
        adapter.create_table(STAGE)
        created.append(STAGE)
        for key in FIRST:
            adapter.add_table_entry(ACTIVE, key)
        for key in SECOND:
            adapter.add_table_entry(STAGE, key)
        if not table_contents_equal(adapter.get_table(ACTIVE), FIRST):
            raise RuntimeError("native mixed-family add/list failed for active table")
        if not table_contents_equal(adapter.get_table(STAGE), SECOND):
            raise RuntimeError("native mixed-family add/list failed for stage table")
        adapter.swap_tables(ACTIVE, STAGE)
        if not table_contents_equal(adapter.get_table(ACTIVE), SECOND):
            raise RuntimeError("native mixed-family stage/swap failed")
        if not table_contents_equal(adapter.get_table(STAGE), FIRST):
            raise RuntimeError("native mixed-family rollback snapshot failed")
        adapter.swap_tables(ACTIVE, STAGE)
        if not table_contents_equal(adapter.get_table(ACTIVE), FIRST):
            raise RuntimeError("native mixed-family swap-back failed")
        if not table_contents_equal(adapter.get_table(STAGE), SECOND):
            raise RuntimeError("native mixed-family stage restoration failed")
        result = "PASS"
    finally:
        # No rule changes; clean exactly the two tables created in this VM.
        for name in reversed(created):
            adapter.destroy_table(name)
        if adapter.get_table(ACTIVE) is not None or adapter.get_table(STAGE) is not None:
            raise RuntimeError("native IPFW table cleanup incomplete")
        if adapter.list_rules(19000, 19010) != original_rules:
            raise RuntimeError("foreign IPFW rule changed during native table test")
    print("STAGE5_NATIVE_TABLE=" + result + ": FreeBSD15 live kernel add/list/swap/restore/cleanup")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as error:
        print(f"STAGE5_NATIVE_TABLE=FAIL: {error}", file=sys.stderr)
        sys.exit(1)
