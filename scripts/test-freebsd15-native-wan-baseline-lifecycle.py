#!/usr/bin/env python3
"""Isolated FreeBSD 15.1 native tcpdump lifecycle, never the installed WAN.

No IPFW/OPNsense mutations, no Internet traffic, no live Exclude Apply.
Only lo0 TCP sockets. lo0 is deliberately *not* Ethernet and must be refused
as an installed WAN capture by the production preflight/PCAP analyzer.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import os
from pathlib import Path
import platform
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

MARKER = 'NATIVE_WAN_BASELINE_LIFECYCLE'
GUARD = 'ZAPRET2_ISOLATED_FREEBSD_VM_WAN_BASELINE_TEST'
HERE = Path(__file__).resolve().parent


def get_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    if spec is None or spec.loader is None:
        raise RuntimeError('native test companion not found: ' + path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def require_isolated_freebsd() -> None:
    if os.environ.get(GUARD) != '1' or platform.system() != 'FreeBSD' or os.geteuid() != 0:
        raise RuntimeError('isolated FreeBSD root opt-in is required')
    version = subprocess.run(['/bin/freebsd-version', '-u'], capture_output=True,
                             text=True, check=True, timeout=6).stdout.strip()
    if not version.startswith('15.1'):
        raise RuntimeError('isolated FreeBSD 15.1 guest required')
    if not Path('/usr/sbin/tcpdump').is_file():
        raise RuntimeError('native tcpdump missing')


def probe_native_preflight(controller) -> None:
    # Real ifconfig, route [-6] -n get and tcpdump -L, no traffic created.
    # Both are loopback. They must never be accepted as Ethernet WAN.
    for remote in ('127.0.0.1', '::1'):
        addr = ipaddress.ip_address(remote)
        plan = {'analysis_manifest': {
            'wan_interface': 'lo0', 'remote_ip': remote,
            'baseline': {'source_ip': remote, 'source_port': 54111}}}
        try:
            controller.preflight(plan)
        except controller.CaptureError as exc:
            # If the route/source itself cannot be established, the test is not
            # evidence of the desired linktype gate, so fail instead.
            if 'DLT_EN10MB' not in str(exc):
                raise RuntimeError('native preflight refused the wrong cause for IPv%d: %s' %
                                   (addr.version, exc)) from exc
        else:
            raise RuntimeError('lo0 was improperly accepted as Ethernet WAN')


def actual_tcp_once(controller, analyzer, family: int, directory: Path) -> None:
    host = '127.0.0.1' if family == socket.AF_INET else '::1'
    name = 'ipv4' if family == socket.AF_INET else 'ipv6'
    path = directory / ('native-lo0-' + name + '.pcap')
    with socket.socket(family, socket.SOCK_STREAM) as server:
        if family == socket.AF_INET6:
            server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        server.bind((host, 0))
        port = server.getsockname()[1]
        server.listen(1)
        server.settimeout(3)
        argv = ['/usr/sbin/tcpdump', '-U', '-i', 'lo0', '-nn', '-s', '4096',
                '-c', '128', '-w', str(path),
                'tcp and host ' + host + ' and port ' + str(port)]
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                start_new_session=True)
        try:
            controller.tcpdump_ready(proc, deadline=time.monotonic() + 5)
            if proc.poll() is not None:
                raise RuntimeError('native tcpdump died after readiness')
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(3)
                client.connect((host, port))
                peer, _ = server.accept()
                with peer:
                    peer.settimeout(3)
                    client.sendall(b'isolated-freebsd15-native-wan-baseline-' + name.encode())
                    if not peer.recv(256).startswith(b'isolated-freebsd15-native'):
                        raise RuntimeError('native loopback request not delivered')
                    peer.sendall(b'local-response')
                    if client.recv(128) != b'local-response':
                        raise RuntimeError('native loopback reply not delivered')
            # Exercise the actual owner-controller wait, not a duplicate test
            # loop: -U does not guarantee immediate FreeBSD kernel BPF delivery.
            if not controller.wait_for_packet_flush(
                    proc, path, deadline=time.monotonic() + 3):
                raise RuntimeError('native BPF record was not flushed within bound')
        finally:
            controller.terminate(proc)
            if proc.poll() is None:
                raise RuntimeError('native tcpdump remained after cleanup')
            tcpdump_tail = proc.stderr.read(4096).decode('utf-8', 'replace') if proc.stderr else ''
            if proc.stderr:
                proc.stderr.close()
    raw = path.read_bytes()
    if len(raw) <= 24 or len(raw) > 8 * 1024 * 1024:
        raise RuntimeError('no bounded native packet capture for %s: bytes=%d; tcpdump=%r' %
                           (name, len(raw), tcpdump_tail[-650:]))
    if raw[:4] not in controller.PCAP_MAGIC:
        raise RuntimeError('unknown native pcap format')
    endian = '<' if raw[:4] in (controller.PCAP_MAGIC[0], controller.PCAP_MAGIC[2]) else '>'
    dlt = struct.unpack_from(endian + 'I', raw, 20)[0]
    if dlt == 1:
        raise RuntimeError('lo0 unexpectedly reports Ethernet DLT; fixture invalid')
    try:
        list(analyzer.pcap_packets(raw))
    except analyzer.EvidenceError as exc:
        if 'Ethernet PCAP' not in str(exc):
            raise RuntimeError('offline attribution refused wrong PCAP reason: ' + str(exc)) from exc
    else:
        raise RuntimeError('offline WAN analyzer incorrectly accepted loopback DLT')
    path.unlink()


def native_timeout_cleanup(controller) -> None:
    # Real owned process group that cannot ever produce tcpdump readiness.
    proc = subprocess.Popen(['/bin/sleep', '4'], stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, start_new_session=True)
    try:
        try:
            controller.tcpdump_ready(proc, deadline=time.monotonic() + .25)
        except controller.CaptureError as exc:
            if 'did not confirm active capture' not in str(exc):
                raise RuntimeError('unexpected readiness failure: ' + str(exc)) from exc
        else:
            raise RuntimeError('sleep was wrongly treated as tcpdump-ready')
    finally:
        controller.terminate(proc)
        if proc.poll() is None:
            raise RuntimeError('readiness timeout leaked process group')


def main() -> int:
    require_isolated_freebsd()
    controller = get_module('native_baseline_controller', 'stage5-wan-baseline-capture.py')
    analyzer = get_module('native_offline_analyzer', 'stage5-wan-pcap-attribution.py')
    with tempfile.TemporaryDirectory(prefix='zapret2-native-lo0-') as tmp:
        root = Path(tmp)
        try:
            probe_native_preflight(controller)
            for family in (socket.AF_INET, socket.AF_INET6):
                actual_tcp_once(controller, analyzer, family, root)
            native_timeout_cleanup(controller)
        finally:
            # Only paths in our temporary directory; never alter IPFW/routes.
            for path in root.iterdir():
                if path.is_file():
                    path.unlink()
    print(MARKER + '=PASS: FreeBSD15.1 real lo0 IPv4/IPv6 tcpdump readiness, '
          'bounded termination, unsupported-DLT refusal and cleanup')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(MARKER + '=FAIL: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
