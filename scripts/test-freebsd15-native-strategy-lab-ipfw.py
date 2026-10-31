#!/usr/bin/env python3
"""Real Strategy Lab IPv4/IPv6 IPFW loopback proof in disposable FreeBSD 15.1.

Production Stage40 pins and candidate firewall adapter are exercised.
Not installed OPNsense, WAN, dvtws2 or Stage85 real engine replay.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
from contextlib import contextmanager

MARKER = "STAGE6_NATIVE_LAB_IPFW"
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
ADAPTER = SCRIPTS / "strategy_lab_candidate_adapter.sh"
TABLE_TEST = Path(__file__).with_name("test-freebsd15-native-ipfw-table.py")
PACKET_TEST = Path(__file__).with_name("test-freebsd15-native-ipfw-packet.py")
BASE, LIMIT, DIVERT = 19100, 19131, 9989
PORT, BYPASS = 55319, 55320


def run_command(*argv: str, env=None):
    return subprocess.run(argv, env=env, text=True, capture_output=True,
                          check=False, timeout=20)


def checked(*argv: str, env=None) -> str:
    result = run_command(*argv, env=env)
    if result.returncode:
        raise RuntimeError(f"command {argv[0]} returned {result.returncode}: "
                           f"{(result.stderr or result.stdout)[:300]}")
    return result.stdout


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"missing native prerequisite: {path}")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


@contextmanager
def with_env(values):
    old = os.environ.copy()
    os.environ.update(values)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


def counter(text: str) -> tuple[int, int]:
    parts = text.strip().split()
    if len(parts) != 2 or any(not value.isascii() or not value.isdecimal() for value in parts):
        raise ValueError("invalid production IPFW counter readback")
    return int(parts[0]), int(parts[1])


def static() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for snippet in ("firewall-install-protocol)", "cleanup)",
                    "strategy_lab_firewall_remove_rules",
                    "out not diverted not sockarg xmit",
                    "STRATEGY_LAB_DIVERT_PORT"):
        if snippet not in text:
            raise RuntimeError(f"production adapter contract missing: {snippet}")
    assert counter("5 100\n") == (5, 100)
    for bad in ("", "5\n", "-1 2", "one 2", "1 2 3"):
        try:
            counter(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"counter parser accepted malformed value: {bad!r}")
    print(f"{MARKER}_STATIC=PASS: production adapter and fail-closed readback")


def adapter(action: str, env: dict[str, str], *args: str) -> str:
    # Native shell trace is captured, never emitted on success. On failure,
    # preserve the actual first-run stderr rather than guessing the stage.
    result = run_command("/bin/sh", "-x", str(ADAPTER), action, *args, env=env)
    if result.returncode:
        raise RuntimeError(
            f"production adapter {action} returned {result.returncode}: "
            f"{result.stderr[-2500:]!r}"
        )
    return result.stdout


def empty_owned_rules() -> bool:
    # FreeBSD can return a non-zero status for an absent numbered rule.
    # Query the complete kernel listing once and inspect only this owner's
    # exact range, without relying on a missing-rule exit-code convention.
    lines = checked("/sbin/ipfw", "-q", "list").splitlines()
    for line in lines:
        parts = line.strip().split()
        if parts and parts[0].isascii() and parts[0].isdecimal():
            if BASE <= int(parts[0]) <= LIMIT:
                return False
    return True


def verify_packet(diverted, sender, receiver, ip: str, payload: bytes, rule: int, env):
    before = counter(adapter("counter", env, str(rule)))
    sender.sendto(payload, (ip, PORT))
    packet, source = diverted.recvfrom(4096)
    family = 6 if ":" in ip else 4
    if not packet or packet[0] >> 4 != family or not packet.endswith(payload):
        raise RuntimeError(f"IPv{family} diverted payload/identity mismatch")
    if diverted.sendto(packet, source) != len(packet):
        raise RuntimeError("native IPFW reinjection returned short send")
    if receiver.recvfrom(512)[0] != payload:
        raise RuntimeError(f"IPv{family} reinjected payload changed")
    after = counter(adapter("counter", env, str(rule)))
    if after[0] <= before[0] or after[1] <= before[1]:
        raise RuntimeError(f"IPv{family} native IPFW packets/bytes did not advance")


def native() -> int:
    if os.environ.get("ZAPRET2_ISOLATED_FREEBSD_VM_STRATEGY_LAB_IPFW_TEST") != "1":
        print(f"{MARKER}=SKIP: opt-in absent")
        return 0
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        print(f"{MARKER}=SKIP: isolated FreeBSD root unavailable")
        return 0
    table = load_module("lab_stage5_tables", TABLE_TEST)
    packet = load_module("lab_stage5_packets", PACKET_TEST)
    if not table.prerequisite():
        print(f"{MARKER}=SKIP: isolated kernel prerequisite unavailable")
        return 0
    if not checked("freebsd-version", "-u").startswith("15.1"):
        raise RuntimeError("native witness requires FreeBSD 15.1")
    packet.ensure_guest_kernel_ready()
    if not table.safe_default_rules(checked("/sbin/ipfw", "-q", "list")):
        raise RuntimeError("foreign IPFW owner detected; refusing changes")
    if not empty_owned_rules():
        raise RuntimeError("Strategy Lab rule range already occupied")
    with tempfile.TemporaryDirectory(prefix="native-lab-stage6-") as work:
        env = os.environ.copy()
        env.update({
            "SCRIPT_DIR": str(SCRIPTS),
            "STRATEGY_LAB_RUN_DIR": work,
            "STRATEGY_LAB_JOBS_DIR": str(Path(work) / "jobs"),
            "STRATEGY_LAB_RULE_BASE": str(BASE),
            "STRATEGY_LAB_RULE_MAX": str(LIMIT),
            "STRATEGY_LAB_DIVERT_PORT": str(DIVERT),
            "STRATEGY_LAB_IPFW_BIN": "/sbin/ipfw",
            "STRATEGY_LAB_KLDSTAT_BIN": "/sbin/kldstat",
            "STRATEGY_LAB_SYSCTL_BIN": "/sbin/sysctl",
        })
        try:
            with socket.socket(socket.PF_DIVERT, socket.SOCK_RAW, 0) as diverted, \
                 socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as recv4, \
                 socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as recv6, \
                 socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send4, \
                 socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as send6, \
                 socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as bypass:
                diverted.bind(("0.0.0.0", DIVERT))
                diverted.settimeout(5)
                recv4.bind(("127.0.0.1", PORT))
                recv6.bind(("::1", PORT))
                bypass.bind(("::1", BYPASS))
                for receiver in (recv4, recv6, bypass):
                    receiver.settimeout(5)
                sys.path.insert(0, str(SCRIPTS))
                from strategy_lab_py import candidate, endpoint_epoch
                job_id = "job.NativeDual"
                job = Path(env["STRATEGY_LAB_JOBS_DIR"]) / job_id
                job.mkdir(parents=True)
                endpoint_epoch.create(job, "example.test", "domain", ["example.test"], [{
                    "endpoint": "example.test",
                    "dns_a": {"classification": "pass", "answers": ["127.0.0.1"]},
                    "dns_aaaa": {"classification": "pass", "answers": ["::1"]},
                }])
                with with_env(env):
                    pins, _ = candidate._pinned_endpoints(job_id, ["example.test"])
                if ([item["selected_ip"] for item in pins] != ["127.0.0.1", "::1"]
                    or [item["family"] for item in pins] != ["ipv4", "ipv6"]
                    or [item["rule"] for item in pins] != [BASE, BASE + 1]):
                    raise RuntimeError("Stage40 family pin/rule binding mismatch")
                addresses = job / "candidate-runtime" / "addresses-ipv4.txt"
                adapter("firewall-install-protocol", env, str(addresses), "lo0", "udp", str(PORT))
                if empty_owned_rules():
                    raise RuntimeError("production adapter installed no rules")
                verify_packet(diverted, send4, recv4, "127.0.0.1", b"stage6-v4", BASE, env)
                verify_packet(diverted, send6, recv6, "::1", b"stage6-v6", BASE + 1, env)
                send6.sendto(b"stage6-bypass", ("::1", BYPASS))
                if bypass.recvfrom(512)[0] != b"stage6-bypass":
                    raise RuntimeError("nonmatching IPv6 port was not delivered")
                diverted.settimeout(0.25)
                try:
                    diverted.recvfrom(4096)
                except socket.timeout:
                    pass
                else:
                    raise RuntimeError("nonmatching IPv6 port was intercepted")
                # The PF_DIVERT test socket is deliberately not a dvtws2
                # process. Close it before invoking the production cleanup
                # guard: that guard correctly refuses a live listener on 9989.
                diverted.close()
                adapter("cleanup", env, job_id)
                if not empty_owned_rules():
                    raise RuntimeError("normal candidate cleanup left owned rules")
                adapter("firewall-install-protocol", env, str(addresses), "lo0", "udp", str(PORT))
                if empty_owned_rules():
                    raise RuntimeError("candidate rule reinstall failed")
                bad = Path(work) / "invalid-addresses.txt"
                bad.write_text("127.0.0.1\n2001:db8::zz\n", encoding="ascii")
                failed = run_command("/bin/sh", str(ADAPTER), "firewall-install-protocol",
                                     str(bad), "lo0", "udp", str(PORT), env=env)
                if failed.returncode == 0 or not empty_owned_rules():
                    raise RuntimeError("partial native install did not roll back")
        finally:
            for rule in range(BASE, LIMIT + 1):
                run_command("/sbin/ipfw", "-q", "delete", str(rule))
            if not empty_owned_rules():
                raise RuntimeError("Strategy Lab rule range not fully restored")
            if not table.safe_default_rules(checked("/sbin/ipfw", "-q", "list")):
                raise RuntimeError("global default-only kernel state not restored")
    print(f"{MARKER}=PASS: production Stage40 dual-stack pins, actual IPFW lo0 IPv4/IPv6 divert/reinject/counters, bypass, cleanup and failed-install restoration")
    return 0


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--static"]:
            static()
        elif not sys.argv[1:]:
            sys.exit(native())
        else:
            raise RuntimeError("invalid test arguments")
    except Exception as exc:
        print(f"{MARKER}=FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
