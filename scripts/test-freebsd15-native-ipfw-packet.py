#!/usr/bin/env python3
"""Opt-in, isolated FreeBSD 15.1 VM native IPv6 IPFW divert round trip.

Never run on an OPNsense appliance. This smoke exercises the production
FreeBSDIPFWAdapter and loopback only, not dvtws2, WAN, or installed Apply.
All rule/table mutations are restricted to a verified disposable VM with
only the default allow rule; the original kernel ownership is reattested.
"""
from __future__ import annotations

import importlib.util
import os
import platform
from pathlib import Path
import socket
import subprocess
import sys

MARKER = "STAGE5_NATIVE_IPV6_PACKET"
TABLE_TEST = Path(__file__).with_name("test-freebsd15-native-ipfw-table.py")

RULE = 19000
DIVERT = 9989
DESTINATION = "::1"
TARGET_PORT = 597
BYPASS_PORT = 610
TABLE_NAME = "zapret2_voice_custom"
STUN_REQUEST = bytes.fromhex("000100002112a4420123456789abcdef01234567")
ARGV = ["divert", str(DIVERT), "udp", "from", "any", "to",
        f"table({TABLE_NAME})", "596-599", "out", "not", "diverted",
        "not", "sockarg", "xmit", "lo0"]


def native(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)


def ensure_guest_kernel_ready() -> None:
    for name in ("net.inet.ip.fw.one_pass", "net.inet6.ip6.fw.enable",
                 "net.inet.ip.fw.enable"):
        check = native("/sbin/sysctl", "-n", name)
        if check.returncode != 0 or check.stdout.strip() != "1":
            raise RuntimeError(f"FreeBSD VM {name} is not enabled; refusing packet test")
    loaded = native("/sbin/kldstat", "-q", "-m", "ipdivert")
    if loaded.returncode == 1:
        attempt = native("/sbin/kldload", "ipdivert")
        if attempt.returncode != 0:
            raise RuntimeError("FreeBSD VM ipdivert cannot be loaded")
    elif loaded.returncode != 0:
        raise RuntimeError("FreeBSD VM ipdivert state is indeterminate")
    if native("/sbin/kldstat", "-q", "-m", "ipdivert").returncode != 0:
        raise RuntimeError("FreeBSD VM ipdivert module was not verified")


def run() -> int:
    if os.getenv("ZAPRET2_ISOLATED_FREEBSD_VM_IPV6_PACKET_TEST") != "1":
        print(f"{MARKER}=SKIP: isolated VM opt-in not set")
        return 0
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        print(f"{MARKER}=SKIP: requires isolated FreeBSD root")
        return 0
    spec = importlib.util.spec_from_file_location("stage5_native_table", TABLE_TEST)
    if spec is None or spec.loader is None:
        raise RuntimeError("existing native table prerequisite is missing")
    table_test = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(table_test)
    if not table_test.prerequisite():
        print(f"{MARKER}=SKIP: native FreeBSD VM prerequisite absent")
        return 0
    from voice_ipfw_adapter import FreeBSDIPFWAdapter
    from voice_firewall_transaction import table_contents_equal
    version = native("freebsd-version", "-u")
    if version.returncode != 0 or not version.stdout.startswith("15.1"):
        raise RuntimeError("packet test requires FreeBSD 15.1 kernel")
    ensure_guest_kernel_ready()
    adapter = FreeBSDIPFWAdapter(RULE, 19010, allow_mutations=True)
    previous_rules = adapter.list_rules(RULE, 19010)
    if previous_rules or adapter.get_table(TABLE_NAME) is not None or \
       adapter.get_table(TABLE_NAME + "_stage") is not None:
        raise RuntimeError("VM plugin rule/table ownership is not empty")
    table_created = False
    rule_added = False
    try:
        # Open the divert listener before adding any rule. Traffic is local
        # to ::1 on lo0; the actual WAN and installed Config are untouched.
        with socket.socket(socket.PF_DIVERT, socket.SOCK_RAW, 0) as diverted, \
             socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as receiver, \
             socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as bypass, \
             socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sender:
            diverted.bind(("0.0.0.0", DIVERT))
            diverted.settimeout(4)
            receiver.bind((DESTINATION, TARGET_PORT))
            receiver.settimeout(4)
            bypass.bind((DESTINATION, BYPASS_PORT))
            bypass.settimeout(4)

            adapter.create_table(TABLE_NAME)
            table_created = True
            adapter.add_table_entry(TABLE_NAME, DESTINATION)
            if not table_contents_equal(adapter.get_table(TABLE_NAME), [DESTINATION]):
                raise RuntimeError("native IPv6 destination table did not attest")
            adapter.add_rule(RULE, ARGV)
            rule_added = True
            if adapter.list_rules(RULE, 19010) != {RULE: ARGV}:
                raise RuntimeError("native IPv6 destination-scoped divert rule mismatch")

            sender.sendto(STUN_REQUEST, (DESTINATION, TARGET_PORT))
            packet, address = diverted.recvfrom(4096)
            if not packet or packet[0] >> 4 != 6 or not packet.endswith(STUN_REQUEST):
                raise RuntimeError("divert did not capture exact IPv6 UDP/STUN payload")
            if diverted.sendto(packet, address) != len(packet):
                raise RuntimeError("divert IPv6 reinjection returned a short send")
            result, _ = receiver.recvfrom(512)
            if result != STUN_REQUEST:
                raise RuntimeError("re-injected IPv6 UDP/STUN payload was not delivered")
            if adapter.rule_counters(RULE, ARGV)[0] < 1:
                raise RuntimeError("native IPv6 divert rule packet counter stayed zero")

            # A port not covered by STUN must be delivered without capture.
            sender.sendto(b"outside-STUN-range", (DESTINATION, BYPASS_PORT))
            result, _ = bypass.recvfrom(512)
            if result != b"outside-STUN-range":
                raise RuntimeError("unmatched IPv6 UDP packet was not delivered")
            diverted.settimeout(0.2)
            try:
                diverted.recvfrom(4096)
            except socket.timeout:
                pass
            else:
                raise RuntimeError("non-STUN UDP packet was unexpectedly diverted")
    finally:
        if rule_added:
            adapter.delete_rule(RULE)
        if table_created:
            adapter.destroy_table(TABLE_NAME)
        if adapter.list_rules(RULE, 19010) != previous_rules or \
           adapter.get_table(TABLE_NAME) is not None:
            raise RuntimeError("VM IPv6 divert IPFW cleanup is not exact")
    print(f"{MARKER}=PASS: FreeBSD15.1 lo0 IPv6 UDP divert/reinject and STUN port scope")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as error:
        print(f"{MARKER}=FAIL: {error}", file=sys.stderr)
        sys.exit(1)
