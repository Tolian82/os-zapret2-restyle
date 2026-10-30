#!/usr/bin/env python3
"""Real pinned dvtws2 TLS ClientHello packet-header witness; disposable FreeBSD only.

Use the production global Exclude compiler, upstream pktmod strategy, actual
IPFW divert and native lo0 tcpdump. Never run on an installed OPNsense box.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
MARKER = "NATIVE_TLS_CLIENTHELLO_HEADER"
RULE, DIVERT = 19007, 9991
PORTS = (6541, 6542, 6543)
BYPASS = 6550
TTL4, HOP6 = 23, 37
ARGV = ["divert", str(DIVERT), "tcp", "from", "any", "to", "any",
        "6541-6543", "out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]
PCAP_ENDIAN = {b"\xd4\xc3\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">",
               b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\x3c\x4d": ">"}


def hello_fixture() -> bytes:
    """Real OpenSSL-generated TLS ClientHello, no network or TLS peer needed."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # A fixed TLS 1.2 offer has a single, bounded record; newer OpenSSL
    # defaults may emit >1500-byte TLS 1.3 hybrid-key ClientHellos that would
    # be split across TCP segments and defeat exact packet attribution.
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    stream = ctx.wrap_bio(incoming, outgoing, server_side=False,
                          server_hostname="stage5.example")
    try:
        stream.do_handshake()
    except ssl.SSLWantReadError:
        pass
    else:
        raise RuntimeError("ClientHello generator unexpectedly completed handshake")
    hello = outgoing.read()
    if (not 150 <= len(hello) <= 1200 or hello[:2] != b"\x16\x03"
            or hello[5] != 1 or int.from_bytes(hello[3:5], "big") != len(hello)-5
            or b"stage5.example" not in hello):
        raise RuntimeError("invalid or oversized TLS ClientHello fixture")
    return hello


def records(raw: bytes, family: int, hello: bytes):
    """Bounded test-only FreeBSD lo0 DLT_NULL or DLT_LOOP IPv4/IPv6 parser."""
    if len(raw) < 24 or len(raw) > 8 * 1024 * 1024 or raw[:4] not in PCAP_ENDIAN:
        raise RuntimeError("invalid or oversized isolated lo0 PCAP")
    fmt = PCAP_ENDIAN[raw[:4]]
    major, minor, _zone, _sig, snaplen, dlt = struct.unpack_from(fmt+"HHiIII", raw, 4)
    if (major, minor) != (2, 4) or not 1 <= snaplen <= 4096 or dlt not in (0, 108):
        raise RuntimeError("isolated capture must be FreeBSD lo0 DLT_NULL/LOOP")
    pos, count, seen = 24, 0, []
    while pos < len(raw):
        if len(raw)-pos < 16:
            raise RuntimeError("truncated native capture record")
        _sec, _usec, cap, orig = struct.unpack_from(fmt+"IIII", raw, pos)
        pos += 16
        count += 1
        if count > 512 or cap != orig or cap > snaplen or cap > len(raw)-pos:
            raise RuntimeError("unbounded/truncated native packet")
        frame = raw[pos:pos+cap]
        pos += cap
        if len(frame) < 4:
            raise RuntimeError("truncated loopback address family")
        af = int.from_bytes(frame[:4], sys.byteorder if dlt == 0 else "big")
        if af != family:
            continue
        if family == socket.AF_INET:
            if len(frame) < 24 or frame[4] >> 4 != 4:
                raise RuntimeError("invalid native IPv4 frame")
            ihl = (frame[4] & 15)*4
            if ihl < 20 or len(frame) < 4+ihl:
                raise RuntimeError("invalid IPv4 IHL")
            total = struct.unpack_from("!H", frame, 6)[0]
            if total < ihl or total > len(frame)-4 or frame[13] != 6:
                raise RuntimeError("invalid native IPv4 TCP datagram")
            if struct.unpack_from("!H", frame, 10)[0] & 0x3fff:
                raise RuntimeError("fragmented TCP packet is ambiguous")
            src, dst = frame[16:20], frame[20:24]
            hop = frame[12]
            tcp = frame[4+ihl:4+total]
        else:
            if len(frame) < 44 or frame[4] >> 4 != 6:
                raise RuntimeError("invalid native IPv6 frame")
            plen = struct.unpack_from("!H", frame, 8)[0]
            if not plen or plen > len(frame)-44 or frame[10] != 6:
                raise RuntimeError("unsupported native IPv6 extension/jumbo TCP packet")
            src, dst = frame[12:28], frame[28:44]
            hop = frame[11]
            tcp = frame[44:44+plen]
        address = ipaddress.ip_address(src), ipaddress.ip_address(dst)
        if len(tcp) < 20:
            raise RuntimeError("truncated native TCP segment")
        srcport, dstport = struct.unpack_from("!HH", tcp)
        offset = (tcp[12] >> 4)*4
        if offset < 20 or offset > len(tcp):
            raise RuntimeError("invalid native TCP header")
        payload = tcp[offset:]
        if (address[0] == address[1] and str(address[1]) ==
                ("127.0.0.1" if family == socket.AF_INET else "::1")
                and dstport in PORTS and payload == hello):
            seen.append((srcport, dstport, hop))
    if count < 1:
        raise RuntimeError("empty native capture")
    return seen


def attest(rows: list[tuple[int, int, int]], baseline: tuple[int, int],
           active: list[tuple[int, int]], phase: str, family: int) -> None:
    """Only uniquely attributed sender-port+destination-port observations count."""
    target = TTL4 if family == socket.AF_INET else HOP6
    pairs = [baseline, *active]
    if len(set(pairs)) != 4:
        raise RuntimeError("TCP source/destination pair reused in one capture")
    for pair in pairs:
        vals = [hop for src, dst, hop in rows if (src, dst) == pair]
        if not vals:
            raise RuntimeError("missing exact ClientHello on native capture")
        if pair == baseline or phase == "excluded":
            if target in vals:
                raise RuntimeError("unmodified/Excluded flow has Strategy TTL/hop value")
        elif target not in vals:
            raise RuntimeError("selected active TLS Strategy header mutation not captured")


def fixture_frame(family: int, hello: bytes, *, srcport: int = 55410,
                  dstport: int = 6541, hop: int = 64) -> bytes:
    """Offline parser fixture: not used as native PASS evidence."""
    tcp = struct.pack("!HHIIHHHH", srcport, dstport, 7, 0, 5 << 12, 0, 0, 0)+hello
    if family == socket.AF_INET:
        ip = b"\x45\x00"+struct.pack("!H", 20+len(tcp))+b"\x00\x00\x00\x00"+bytes((hop, 6))+b"\x00\x00"+socket.inet_aton("127.0.0.1")*2
    else:
        ip = b"\x60\x00\x00\x00"+struct.pack("!H", len(tcp))+bytes((6, hop))+socket.inet_pton(socket.AF_INET6, "::1")*2
    return family.to_bytes(4, sys.byteorder)+ip+tcp


def fixture_pcap(frame: bytes, dlt: int = 0) -> bytes:
    return (struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 4096, dlt)
            + struct.pack("<IIII", 1, 0, len(frame), len(frame))+frame)


def static_test() -> None:
    hello = hello_fixture()
    for family, expected in ((socket.AF_INET, TTL4), (socket.AF_INET6, HOP6)):
        original = records(fixture_pcap(fixture_frame(family, hello)), family, hello)
        changed = records(fixture_pcap(fixture_frame(family, hello, hop=expected,
                                                     srcport=55411)), family, hello)
        assert original == [(55410, 6541, 64)]
        assert changed == [(55411, 6541, expected)]
        # Full attribution requires 4 distinct flow identities.
        pairs = [(55410, 6541), (55411, 6541), (55412, 6542), (55413, 6543)]
        active = pairs[1:]
        proper = original+changed+[(55412, 6542, expected), (55413, 6543, expected)]
        attest(proper, pairs[0], active, "baseline", family)
        for p, modified, phase in ((proper, False, "excluded"),
                                   (original+[(55411, 6541, 64)], True, "baseline"),
                                   (proper[:-1], False, "baseline")):
            try:
                attest(p, pairs[0], active, phase, family)
            except RuntimeError:
                pass
            else:
                raise RuntimeError("negative native capture attribution control accepted")
        excluded = [(p[0], p[1], 64) for p in pairs]
        attest(excluded, pairs[0], active, "excluded", family)
        for invalid in (fixture_pcap(fixture_frame(family, hello))[:-1],
                        fixture_pcap(fixture_frame(family, hello), dlt=1)):
            try:
                records(invalid, family, hello)
            except RuntimeError:
                pass
            else:
                raise RuntimeError("malformed/untrusted loopback PCAP accepted")
    # Exercise the real policy compiler twice per phase: the native harness
    # reuses its same managed policy for IPv4 and IPv6. Static tests must catch
    # path/idempotence failures before the expensive FreeBSD job.
    backend = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    with tempfile.TemporaryDirectory(prefix="stage5-tls-static-") as folder:
        root = Path(folder)
        upstream = root / "upstream"
        (upstream / "lua").mkdir(parents=True)
        for name in ("zapret-lib.lua", "zapret-antidpi.lua"):
            (upstream / "lua" / name).write_text("-- static fixture only\n")
        for phase in ("baseline", "nonmatching", "excluded"):
            before = compiled(root, upstream, phase)
            again = compiled(root, upstream, phase)
            if before != again:
                raise RuntimeError("IPv4/IPv6 repeated native TLS candidate changed")
    print("NATIVE_TLS_HEADER_STATIC=PASS: OpenSSL ClientHello, both lo0 packet decoders, exact flow/hop controls")


def module(name: str, script: Path):
    spec = importlib.util.spec_from_file_location(name, script)
    if not spec or not spec.loader:
        raise RuntimeError("native companion missing: "+script.name)
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


def compiled(root: Path, upstream: Path, phase: str) -> list[str]:
    from global_exclusions import audit, compose, segments, templates_and_imports
    from ipset_policy import LISTS, parse_ipset
    release = root / phase
    managed = release / "managed"
    # Both IP families share one immutable phase-specific policy directory.
    managed.mkdir(parents=True, exist_ok=True)
    (managed / "hostlist-exclude.txt").write_text("")
    manifest = {"schema_version": 1, "lists": {}}
    for name in LISTS:
        raw = ("127.0.0.1/32\n::1/128\n" if phase == "excluded" else
               "192.0.2.1/32\n2001:db8::1/128\n" if phase == "nonmatching" else "") if name == "exclude" else ""
        normalized, proof = parse_ipset(raw.encode(), name, collapse=name == "exclude")
        (managed / ("ipset-"+name+".txt")).write_text(normalized)
        manifest["lists"][name] = proof
    (release / "ipset-manifest.json").write_text(json.dumps(manifest))
    staged = root / "lua"
    staged.mkdir(exist_ok=True)
    for name in ("zapret-lib.lua", "zapret-antidpi.lua"):
        original = upstream / "lua" / name
        if not original.is_file():
            raise RuntimeError("pinned upstream Lua not found")
        shutil.copyfile(original, staged/name)
    raw = f"--port={DIVERT}\n" + "".join(f"--lua-init=@{staged/name}\n" for name in ("zapret-lib.lua", "zapret-antidpi.lua"))
    for index, port in enumerate(PORTS):
        raw += (f"--filter-tcp={port}\n--filter-l7=tls\n--payload=tls_client_hello\n"
                f"--lua-desync=pktmod:ip_ttl={TTL4}:ip6_ttl={HOP6}\n")
        if index < 2:
            raw += "--new\n"
    ipref = str(managed / "ipset-exclude.txt")
    result = compose(raw, managed / "hostlist-exclude.txt", str(managed / "hostlist-exclude.txt"),
                     managed / "ipset-exclude.txt", ipref, release, release, upstream)
    audit(result, managed / "hostlist-exclude.txt", str(managed / "hostlist-exclude.txt"),
          managed / "ipset-exclude.txt", ipref, release, release, upstream)
    rows = segments(result)
    _, kinds = templates_and_imports(rows)
    expected = 0 if phase == "baseline" else 3
    if kinds != ["profile"]*3 or sum(row.count("--ipset-exclude="+ipref) for row in rows) != expected:
        raise RuntimeError("TLS Strategy production compiler/Exclude binding mismatch")
    expected_strategy = f"--lua-desync=pktmod:ip_ttl={TTL4}:ip6_ttl={HOP6}"
    if any(row.count(expected_strategy) != 1 for row in rows):
        raise RuntimeError("real upstream TLS Strategy missing from generated executable profile")
    return result.split()


def send_hello(family: int, host: str, port: int, hello: bytes) -> int:
    result, errors, sender = [], [], []
    with socket.socket(family, socket.SOCK_STREAM) as server:
        # Sequential A/N/B connections can leave the listening port in
        # TIME_WAIT after shutdown; do not fail for a prior closed test flow.
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        server.bind((host, port))
        server.listen(1)
        server.settimeout(5)

        def reader():
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(5)
                    buf = b""
                    while len(buf) < len(hello):
                        piece = conn.recv(2048)
                        if not piece:
                            break
                        buf += piece
                    result.append(buf)
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(5)
                client.connect((host, port))
                sender.append(client.getsockname()[1])
                client.sendall(hello)
                client.shutdown(socket.SHUT_WR)
        finally:
            thread.join(6)
        if thread.is_alive() or errors or result != [hello] or len(sender) != 1:
            raise RuntimeError("TLS ClientHello was not delivered intact")
        return sender[0]


def capture_phase(controller, adapter, engine: Path, upstream: Path,
                  root: Path, phase: str, family: int, hello: bytes) -> None:
    host = "127.0.0.1" if family == socket.AF_INET else "::1"
    args = compiled(root, upstream, phase)
    log = root / (f"{phase}-{family}.log")
    cap = root / (f"{phase}-{family}.pcap")
    with log.open("wb") as output:
        proc = subprocess.Popen([str(engine), *args], stdout=output, stderr=subprocess.STDOUT)
        installed = False
        dump = None
        try:
            time.sleep(.6)
            if proc.poll() is not None:
                raise RuntimeError("dvtws2 did not start: "+log.read_text(errors="replace")[-1200:])
            argv = ["/usr/sbin/tcpdump", "-U", "-i", "lo0", "-nn", "-s", "4096",
                    "-c", "256", "-w", str(cap),
                    "tcp and dst host "+host+" and dst portrange 6541-6543"]
            dump = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    start_new_session=True)
            controller.tcpdump_ready(dump, deadline=time.monotonic()+5)
            first = (send_hello(family, host, PORTS[0], hello), PORTS[0])
            adapter.add_rule(RULE, ARGV)
            installed = True
            if adapter.list_rules(19000, 19010) != {RULE: ARGV}:
                raise RuntimeError("unexpected test-only IPFW owner")
            active = [(send_hello(family, host, port, hello), port) for port in PORTS]
            send_hello(family, host, BYPASS, hello)
            if (adapter.rule_counters(RULE, ARGV)[0] < 3
                    or proc.poll() is not None
                    or not controller.wait_for_packet_flush(dump, cap, deadline=time.monotonic()+3)):
                raise RuntimeError("missing native kernel/engine/capture evidence")
            found = records(cap.read_bytes(), family, hello)
            attest(found, first, active, phase, family)
        finally:
            if dump is not None:
                controller.terminate(dump)
                if dump.stderr is not None:
                    dump.stderr.close()
                if dump.poll() is None:
                    raise RuntimeError("native tcpdump leaked")
            if installed:
                adapter.delete_rule(RULE)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            if adapter.list_rules(19000, 19010):
                raise RuntimeError("native IPFW owner leaked")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--static":
        static_test()
        return 0
    if len(sys.argv) != 2:
        raise RuntimeError("usage: test-freebsd15-native-tls-strategy.py --static | /pinned/dvtws2")
    # Exact existing VM guard, including no OPNsense filesystem and default allow.
    probe = module("native_engine_tls_guard", HERE/"test-freebsd15-native-engine-exclude.py")
    adapter, table = probe.guest_gate()
    controller = module("native_tls_capture_controller", HERE/"stage5-wan-baseline-capture.py")
    if not Path("/usr/sbin/tcpdump").is_file():
        raise RuntimeError("FreeBSD native BPF tcpdump missing")
    engine = Path(sys.argv[1]).resolve()
    upstream = engine.parent.parent
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise RuntimeError("pinned real dvtws2 unavailable")
    static_test()
    hello = hello_fixture()
    with tempfile.TemporaryDirectory(prefix="stage5-native-tls-") as tmp:
        root = Path(tmp)
        root.chmod(0o755)
        for phase in ("baseline", "nonmatching", "excluded"):
            for family in (socket.AF_INET, socket.AF_INET6):
                capture_phase(controller, adapter, engine, upstream, root, phase, family, hello)
    if not table.safe_default_rules(probe.native("/sbin/ipfw", "-q", "list").stdout):
        raise RuntimeError("FreeBSD test kernel not restored to default allow")
    print(MARKER+"=PASS: native TLS ClientHello selected pktmod TTL IPv4/IPv6, nonmatching Exclude modifies, exact matching Exclude preserves, IPFW/pcap cleaned")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(MARKER+"=FAIL: "+str(exc), file=sys.stderr)
        raise SystemExit(1)
