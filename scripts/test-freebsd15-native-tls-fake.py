#!/usr/bin/env python3
"""Real upstream TLS fake packet witness in opted-in disposable FreeBSD 15.1 only."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
MARKER = 'NATIVE_TLS_FAKE_PACKET'
RULE, DIVERT, PORT, BYPASS = 19008, 9992, 6544, 6545
FAKE = b'stage5-tls-fake-proof-v1'
ARGV = ['divert', str(DIVERT), 'tcp', 'from', 'any', 'to', 'any',
        str(PORT), 'out', 'not', 'diverted', 'not', 'sockarg', 'xmit', 'lo0']


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('native companion unavailable: '+path.name)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def attest(original, forged, baseline_port: int, active_port: int,
           bypass_port: int, phase: str) -> None:
    """The fake belongs only to the captured active TCP flow, never baseline/bypass."""
    if phase not in ('baseline', 'nonmatching', 'excluded'):
        raise RuntimeError('unknown phase')
    ids = {(port, dst) for port, dst in ((baseline_port, PORT),
                                         (active_port, PORT), (bypass_port, BYPASS))}
    if len(ids) != 3:
        raise RuntimeError('ambiguous reused TCP identity')
    for pair in ids:
        if not any(row[:2] == pair for row in original):
            raise RuntimeError('missing authentic ClientHello on attributed TCP flow')
    actual = {(src, dst) for src, dst, _hop in forged}
    expected = set() if phase == 'excluded' else {(active_port, PORT)}
    if actual != expected:
        raise RuntimeError('fake packet missing, misplaced, or leaked through Exclude')


def static_test() -> None:
    hello = b'\x16\x03\x03\x00\x03\x01\x00\x00'
    native = module('tls_fake_offline', HERE / 'test-freebsd15-native-tls-strategy.py')
    for family in (socket.AF_INET, socket.AF_INET6):
        # Synthetic DLT_NULL PCAP test: never presented as native runtime evidence.
        for payload in (hello, FAKE):
            frame = native.fixture_frame(family, payload)
            assert native.records(native.fixture_pcap(frame), family, payload) == [(55410, 6541, 64)]
        first = [(55100, PORT, 64), (55101, PORT, 64), (55102, BYPASS, 64)]
        attest(first, [(55101, PORT, 64)], 55100, 55101, 55102, 'baseline')
        attest(first, [(55101, PORT, 64)], 55100, 55101, 55102, 'nonmatching')
        attest(first, [], 55100, 55101, 55102, 'excluded')
        for forged, phase in (([], 'baseline'), ([(55100, PORT, 64)], 'baseline'),
                              ([(55101, PORT, 64)], 'excluded'),
                              ([(55102, BYPASS, 64)], 'baseline')):
            try:
                attest(first, forged, 55100, 55101, 55102, phase)
            except RuntimeError:
                pass
            else:
                raise RuntimeError('negative fake flow control accepted')
    print('NATIVE_TLS_FAKE_STATIC=PASS: IPv4/IPv6 packet decoder, unique fake and Exclude negative controls')


def compiled(root: Path, upstream: Path, phase: str) -> list[str]:
    from global_exclusions import audit, compose, segments
    from ipset_policy import LISTS, parse_ipset
    release = root / phase
    managed = release / 'managed'
    managed.mkdir(parents=True, exist_ok=True)
    (managed / 'hostlist-exclude.txt').write_text('')
    manifest = {'schema_version': 1, 'lists': {}}
    for name in LISTS:
        raw = ('127.0.0.1/32\n::1/128\n' if phase == 'excluded' else
               '192.0.2.1/32\n2001:db8::1/128\n' if phase == 'nonmatching' else '') if name == 'exclude' else ''
        normalized, proof = parse_ipset(raw.encode(), name, collapse=name == 'exclude')
        (managed / ('ipset-'+name+'.txt')).write_text(normalized)
        manifest['lists'][name] = proof
    (release / 'ipset-manifest.json').write_text(json.dumps(manifest))
    staged = root / 'lua'
    staged.mkdir(exist_ok=True)
    import shutil
    for name in ('zapret-lib.lua', 'zapret-antidpi.lua'):
        source = upstream / 'lua' / name
        if not source.is_file():
            raise RuntimeError('pinned real upstream Lua missing')
        shutil.copyfile(source, staged / name)
    raw = (f'--port={DIVERT}\n'
           + ''.join(f'--lua-init=@{staged/name}\n' for name in ('zapret-lib.lua', 'zapret-antidpi.lua'))
           + f'--blob=stage5_wire_fake:0x{FAKE.hex()}\n'
           + f'--filter-tcp={PORT}\n--filter-l7=tls\n--payload=tls_client_hello\n'
           + '--lua-desync=fake:blob=stage5_wire_fake:badsum\n')
    ipref = str(managed / 'ipset-exclude.txt')
    result = compose(raw, managed/'hostlist-exclude.txt', str(managed/'hostlist-exclude.txt'),
                     managed/'ipset-exclude.txt', ipref, release, release, upstream)
    audit(result, managed/'hostlist-exclude.txt', str(managed/'hostlist-exclude.txt'),
          managed/'ipset-exclude.txt', ipref, release, release, upstream)
    rows = segments(result)
    expected = 0 if phase == 'baseline' else 1
    if len(rows) != 1 or rows[0].count('--ipset-exclude='+ipref) != expected or rows[0].count(
            '--lua-desync=fake:blob=stage5_wire_fake:badsum') != 1:
        raise RuntimeError('real fake profile lost or wrong global Exclude scope')
    return result.split()


def capture(adapter, controller, native, engine: Path, upstream: Path,
            root: Path, phase: str, family: int, hello: bytes) -> None:
    host = '127.0.0.1' if family == socket.AF_INET else '::1'
    args = compiled(root, upstream, phase)
    log = root / f'fake-{phase}-{family}.log'
    cap = root / f'fake-{phase}-{family}.pcap'
    with log.open('wb') as output:
        proc = subprocess.Popen([str(engine), *args], stdout=output, stderr=subprocess.STDOUT)
        dump = None
        installed = False
        try:
            time.sleep(.6)
            if proc.poll() is not None:
                raise RuntimeError('native fake profile startup failed: '+log.read_text(errors='replace')[-1200:])
            dump = subprocess.Popen(['/usr/sbin/tcpdump', '-U', '-i', 'lo0', '-nn', '-s', '4096',
                                     '-c', '256', '-w', str(cap),
                                     f'tcp and dst host {host} and dst portrange {PORT}-{BYPASS}'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
            controller.tcpdump_ready(dump, deadline=time.monotonic()+5)
            baseline = native.send_hello(family, host, PORT, hello)
            adapter.add_rule(RULE, ARGV)
            installed = True
            if adapter.list_rules(19000, 19010) != {RULE: ARGV}:
                raise RuntimeError('unexpected test-only IPFW ownership')
            active = native.send_hello(family, host, PORT, hello)
            bypass = native.send_hello(family, host, BYPASS, hello)
            if (proc.poll() is not None or adapter.rule_counters(RULE, ARGV)[0] < 1
                    or not controller.wait_for_packet_flush(dump, cap, deadline=time.monotonic()+3)):
                raise RuntimeError('missing native capture, engine, or IPFW evidence')
            raw = cap.read_bytes()
            original = native.records(raw, family, hello)
            forged = native.records(raw, family, FAKE)
            attest(original, forged, baseline, active, bypass, phase)
        finally:
            if dump is not None:
                controller.terminate(dump)
                if dump.stderr is not None:
                    dump.stderr.close()
                if dump.poll() is None:
                    raise RuntimeError('tcpdump not cleaned')
            if installed:
                adapter.delete_rule(RULE)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            if adapter.list_rules(19000, 19010):
                raise RuntimeError('test-owned IPFW rule leaked')


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == '--static':
        static_test()
        return 0
    if len(sys.argv) != 2:
        raise RuntimeError('usage: test-freebsd15-native-tls-fake.py --static | /pinned/dvtws2')
    guard = module('stage5_fake_native_gate', HERE/'test-freebsd15-native-engine-exclude.py')
    adapter, table = guard.guest_gate()
    controller = module('stage5_fake_capture', HERE/'stage5-wan-baseline-capture.py')
    native = module('stage5_fake_tls', HERE/'test-freebsd15-native-tls-strategy.py')
    engine = Path(sys.argv[1]).resolve()
    if not engine.is_file() or not os.access(engine, os.X_OK) or not Path('/usr/sbin/tcpdump').is_file():
        raise RuntimeError('pinned dvtws2 or FreeBSD tcpdump missing')
    static_test()
    hello = native.hello_fixture()
    with tempfile.TemporaryDirectory(prefix='stage5-fake-native-') as folder:
        root = Path(folder)
        root.chmod(0o755)
        for phase in ('baseline', 'nonmatching', 'excluded'):
            for family in (socket.AF_INET, socket.AF_INET6):
                capture(adapter, controller, native, engine, engine.parent.parent,
                        root, phase, family, hello)
    if not table.safe_default_rules(guard.native('/sbin/ipfw', '-q', 'list').stdout):
        raise RuntimeError('native default-allow kernel rules not restored')
    print(MARKER+'=PASS: real TLS fake IPv4/IPv6 captured only without matching Exclude; original ClientHello preserved; IPFW cleaned')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(MARKER+'=FAIL: '+str(exc), file=sys.stderr)
        raise SystemExit(1)
