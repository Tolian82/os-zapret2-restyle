#!/usr/bin/env python3
"""Disposable FreeBSD 15.1 real dvtws2 IPv4/IPv6 Exclude IPSet A/B.

Never run on OPNsense. Real IPFW rules, packet interception and a test-only
DROP Lua function are permitted ONLY inside an opted-in isolated FreeBSD VM
with exactly the default allow rule. All test packets remain on lo0.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from global_exclusions import audit, compose, segments, templates_and_imports
from ipset_policy import LISTS, parse_ipset

MARKER = "NATIVE_ENGINE_EXCLUDE_WIRE"
RULE = 19005
PORT = 9989
TEST_PORTS = (596, 597, 598)
BYPASS_PORT = 610
TABLE_TEST = Path(__file__).with_name("test-freebsd15-native-ipfw-table.py")
PACKET_TEST = Path(__file__).with_name("test-freebsd15-native-ipfw-packet.py")
ARGV = ["divert", str(PORT), "udp", "from", "any", "to", "any", "596-598",
        "out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]


def candidate(root: Path, excluded: bool, nonmatching: bool = False) -> tuple[list[str], int]:
    """Use the production compiler; optionally test nonmatching Exclude entries."""
    if excluded and nonmatching:
        raise ValueError("Exclude test phase must have exactly one destination policy")
    release = root / ("excluded" if excluded else "nonmatching" if nonmatching else "baseline")
    managed = release / "managed"
    managed.mkdir(parents=True)
    (managed / "hostlist-exclude.txt").write_text("")
    manifest: dict = {"schema_version": 1, "lists": {}}
    for name in LISTS:
        raw = ""
        if name == "exclude":
            if excluded:
                raw = "127.0.0.1/32\n::1/128\n"
            elif nonmatching:
                # Documentation-only networks are intentionally not loopback.
                # The option must NOT bypass unrelated IPv4/IPv6 destinations.
                raw = "192.0.2.1/32\n2001:db8::1/128\n"
        normalized, proof = parse_ipset(raw.encode(), name, collapse=name == "exclude")
        (managed / f"ipset-{name}.txt").write_text(normalized)
        manifest["lists"][name] = proof
    (release / "ipset-manifest.json").write_text(json.dumps(manifest))
    lua = root / "probe.lua"
    lua.write_text("function test_drop(ctx, desync) return VERDICT_DROP end\n")
    # Distinct UDP ports force matching first, middle and last profiles.
    raw = (f"--port={PORT}\n--lua-init=@{lua}\n"
           "--filter-udp=596\n--lua-desync=test_drop\n"
           "--new\n--filter-udp=597\n--lua-desync=test_drop\n"
           "--new\n--filter-udp=598\n--lua-desync=test_drop\n")
    ip_ref = str(managed / "ipset-exclude.txt")
    result = compose(raw, managed / "hostlist-exclude.txt",
                     str(managed / "hostlist-exclude.txt"),
                     managed / "ipset-exclude.txt", ip_ref,
                     release, release, root / "upstream")
    audit(result, managed / "hostlist-exclude.txt",
          str(managed / "hostlist-exclude.txt"),
          managed / "ipset-exclude.txt", ip_ref,
          release, release, root / "upstream")
    rows = segments(result)
    _, kinds = templates_and_imports(rows)
    if kinds != ["profile"] * 3:
        raise RuntimeError("generated test must have three executable profiles")
    flag = "--ipset-exclude=" + ip_ref
    count = sum(row.count(flag) for row in rows)
    enabled = excluded or nonmatching
    expected = 3 if enabled else 0
    if count != expected or any(row.count(flag) != int(enabled) for row in rows):
        raise RuntimeError("generated test Exclude policy is not per-profile")
    return result.split(), count


def static_selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="native-exclude-static-") as tmp:
        root = Path(tmp)
        (root / "upstream").mkdir()
        before, n0 = candidate(root, False)
        unrelated, ncontrol = candidate(root, False, nonmatching=True)
        after, n1 = candidate(root, True)
        if n0 != 0 or ncontrol != 3 or n1 != 3 or len({tuple(before), tuple(unrelated), tuple(after)}) != 3:
            raise RuntimeError("A/B + nonmatching-control candidate construction failed")
        control = (root / "nonmatching/managed/ipset-exclude.txt").read_text().splitlines()
        control_networks = {ipaddress.ip_network(value) for value in control}
        if len(control_networks) != 2 or any(
            ipaddress.ip_address(destination) in network
            for destination in ("127.0.0.1", "::1")
            for network in control_networks
            if ipaddress.ip_address(destination).version == network.version
        ):
            raise RuntimeError("nonmatching Exclude negative control matches loopback")
        ips = (root / "excluded/managed/ipset-exclude.txt").read_text().splitlines()
        if {ipaddress.ip_network(x) for x in ips} != {
            ipaddress.ip_network("127.0.0.1/32"), ipaddress.ip_network("::1/128")
        }:
            raise RuntimeError("mixed-family witness mismatch")
    print("NATIVE_ENGINE_EXCLUDE_STATIC=PASS: same destination, 3 final profiles, both IP families, nonmatching negative control")


def native(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)


def guest_gate() -> tuple[object, object]:
    if os.getenv("ZAPRET2_ISOLATED_FREEBSD_VM_EXCLUDE_WIRE_TEST") != "1":
        raise RuntimeError("explicit isolated FreeBSD VM opt-in required")
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        raise RuntimeError("requires FreeBSD root in disposable VM")
    if Path("/conf/config.xml").exists() or Path("/usr/local/opnsense").exists():
        raise RuntimeError("OPNsense filesystem detected: refusing all mutations")
    version = native("freebsd-version", "-u")
    if version.returncode or not version.stdout.startswith("15.1"):
        raise RuntimeError("requires FreeBSD 15.1 guest kernel")
    spec = importlib.util.spec_from_file_location("stage5_table", TABLE_TEST)
    probe = importlib.util.spec_from_file_location("stage5_packet", PACKET_TEST)
    if not spec or not spec.loader or not probe or not probe.loader:
        raise RuntimeError("existing isolated native safeguards unavailable")
    table_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(table_mod)
    packet_mod = importlib.util.module_from_spec(probe)
    probe.loader.exec_module(packet_mod)
    if not table_mod.prerequisite():
        raise RuntimeError("FreeBSD kernel is not in exact default-allow state")
    packet_mod.ensure_guest_kernel_ready()
    from voice_ipfw_adapter import FreeBSDIPFWAdapter
    adapter = FreeBSDIPFWAdapter(19000, 19010, allow_mutations=True)
    if adapter.list_rules(19000, 19010):
        raise RuntimeError("foreign owned rules: refusing kernel changes")
    return adapter, table_mod


def check_transport(family: int, host: str, port: int) -> None:
    """Exact same payload and address are used in transparent and A/B phases."""
    with socket.socket(family, socket.SOCK_DGRAM) as receiver, \
         socket.socket(family, socket.SOCK_DGRAM) as sender:
        if family == socket.AF_INET6:
            receiver.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        receiver.bind((host, port))
        receiver.settimeout(2)
        payload = f"proof-{family}-{port}".encode()
        sender.sendto(payload, (host, port))
        if receiver.recvfrom(4096)[0] != payload:
            raise RuntimeError("unintercepted loopback path is not transparent")


def run_phase(adapter: object, engine: Path, root: Path, excluded: bool, nonmatching: bool = False) -> None:
    args, _ = candidate(root, excluded, nonmatching=nonmatching)
    phase = "excluded" if excluded else "nonmatching" if nonmatching else "baseline"
    log = root / f"{phase}.log"
    with log.open("wb") as logfile:
        proc = subprocess.Popen([str(engine), *args], stdout=logfile, stderr=subprocess.STDOUT)
        installed = False
        try:
            time.sleep(0.6)
            if proc.poll() is not None:
                raise RuntimeError("dvtws2 startup failed: " + log.read_text(errors="replace")[-2000:])
            for family, host in ((socket.AF_INET, "127.0.0.1"),
                                 (socket.AF_INET6, "::1")):
                for port in TEST_PORTS:
                    check_transport(family, host, port)
            adapter.add_rule(RULE, ARGV)
            installed = True
            if adapter.list_rules(19000, 19010) != {RULE: ARGV}:
                raise RuntimeError("divert rule differs from proposed exact loopback owner")
            for family, host in ((socket.AF_INET, "127.0.0.1"),
                                 (socket.AF_INET6, "::1")):
                for port in TEST_PORTS:
                    payload = f"proof-{family}-{port}".encode()
                    with socket.socket(family, socket.SOCK_DGRAM) as receiver, \
                         socket.socket(family, socket.SOCK_DGRAM) as sender:
                        if family == socket.AF_INET6:
                            receiver.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                        receiver.bind((host, port))
                        receiver.settimeout(1 if not excluded else 3)
                        sender.sendto(payload, (host, port))
                        try:
                            received, _ = receiver.recvfrom(4096)
                        except socket.timeout:
                            if excluded:
                                raise RuntimeError(f"matching Exclude {host}:{port} unexpectedly dropped")
                        else:
                            if not excluded or received != payload:
                                raise RuntimeError(f"unexpected payload/acceptance at {host}:{port}, phase={phase}")
                    if proc.poll() is not None:
                        raise RuntimeError("dvtws2 exited during active A/B phase")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, \
                 socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                receiver.bind(("127.0.0.1", BYPASS_PORT))
                receiver.settimeout(2)
                sender.sendto(b"out-of-scope", ("127.0.0.1", BYPASS_PORT))
                if receiver.recvfrom(512)[0] != b"out-of-scope":
                    raise RuntimeError("unmatched UDP was not transparently delivered")
            if adapter.rule_counters(RULE, ARGV)[0] < len(TEST_PORTS) * 2:
                raise RuntimeError("not all synthetic packets were captured by actual IPFW divert")
        finally:
            if installed:
                adapter.delete_rule(RULE)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            if adapter.list_rules(19000, 19010):
                raise RuntimeError("owned IPFW rules remain after test phase")


def real_native(engine: Path) -> None:
    adapter, table_mod = guest_gate()
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise RuntimeError("pinned upstream native dvtws2 binary missing")
    with tempfile.TemporaryDirectory(prefix="native-exclude-wire-") as tmp:
        root = Path(tmp)
        # dvtws2 intentionally drops privileges to UID/GID 2147483647
        # before loading Lua and native IPSET references. TemporaryDirectory
        # defaults to 0700; allow traversal but never grant write access.
        # This ephemeral tree exists ONLY inside the isolated guarded VM.
        root.chmod(0o755)
        (root / "upstream").mkdir()
        # Three independent native phases distinguish true membership checks
        # from an unsafe blanket bypass when any Exclude flag exists.
        for excluded, nonmatching in ((False, False), (False, True), (True, False)):
            run_phase(adapter, engine, root, excluded, nonmatching=nonmatching)
    if not table_mod.safe_default_rules(native("/sbin/ipfw", "-q", "list").stdout):
        raise RuntimeError("default-allow kernel guard not restored")
    print(f"{MARKER}=PASS: real dvtws2 v1.0.6 IPv4/IPv6 three-profile baseline DROP, nonmatching Exclude DROP, matching Exclude pass")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--static":
        static_selftest()
        return 0
    if len(sys.argv) != 2:
        raise RuntimeError("usage: test-freebsd15-native-engine-exclude.py --static | /path/to/pinned/dvtws2")
    if platform.system() != "FreeBSD" or os.getenv("ZAPRET2_ISOLATED_FREEBSD_VM_EXCLUDE_WIRE_TEST") != "1":
        raise RuntimeError("native test requires explicit FreeBSD 15.1 VM opt-in; run --static elsewhere")
    static_selftest()
    real_native(Path(sys.argv[1]).resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{MARKER}=FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
