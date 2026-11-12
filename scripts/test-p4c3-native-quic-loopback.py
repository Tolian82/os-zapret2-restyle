#!/usr/bin/env python3
"""P4c3c: real QUIC Initial UDP/Lua fake witness on disposable OPNsense lo0.

Not a real WAN, successful QUIC handshake, ISP bypass, or installed plugin.
The native fixture files are immutable v1.0.7 upstream captured datagrams.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import os
from pathlib import Path
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
MARK = "P4C3_QUIC_INITIAL"
RULE, DIVERT, PORT = 19351, 19899, 6545
HOST = "127.0.0.1"
ORIGINAL = ("quic_initial_www_google_com.bin",
            "80a07cc8870c88be6d8ac7f9bf9dc9bb1979468b")
FORGED = ("quic_initial_rutracker_org.bin",
          "25b3edcd6500ae11e55727995235ff7dd917bd2f")
FAKE_MARKER = re.compile(r"(?m)^LUA:\s+fake:\s+[0-9a-fA-F]")


def guard_module():
    path = HERE / "test-p4c3-native-tls-loopback.py"
    spec = importlib.util.spec_from_file_location("p4c3c_qualified_guest_guard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("PINNED_P4C3A_GUARD_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quic_header_shape(data: bytes) -> bool:
    """Bounded exact v1/v2 long-header QUIC Initial structural predicate.

    This is a negative/static check, not proof that encrypted TLS CRYPTO frames
    decrypt. Native input is a captured file in the pinned upstream commit.
    """
    if not (1200 <= len(data) <= 1500):
        return False
    version = int.from_bytes(data[1:5], "big")
    is_v2 = version in (0x6b3343cf, 0x709a50c4)
    if version not in (1, 0x6b3343cf, 0x709a50c4):
        return False
    if (data[0] & 0xF0) != (0xD0 if is_v2 else 0xC0):
        return False
    at = 5
    for _ in range(2):
        if at >= len(data) or data[at] > 20:
            return False
        at += data[at] + 1
    if at >= len(data):
        return False

    def varint(pos: int):
        if pos >= len(data):
            return None
        size = 1 << (data[pos] >> 6)
        if size > len(data)-pos:
            return None
        value = int.from_bytes(data[pos:pos+size], "big")
        value &= (1 << (size*8-2))-1
        return pos+size, value

    token = varint(at)
    if token is None:
        return False
    at, token_size = token
    at += token_size
    if at >= len(data):
        return False
    length = varint(at)
    if length is None:
        return False
    at, ciphertext_len = length
    return (32 <= ciphertext_len <= 1490 and
            at+ciphertext_len <= len(data))


def self_fixture() -> bytes:
    """Synthetic header-only negative parser fixture; NEVER native evidence."""
    header = (b"\xc0\x00\x00\x00\x01\x08" + bytes(range(8)) +
              b"\x08" + bytes(range(8, 16)) + b"\x00" + b"\x44\x96")
    data = header + bytes(1200-len(header))
    if not quic_header_shape(data):
        raise RuntimeError("STATIC_QUIC_SHAPE_WRONG")
    return data


def pinned_blob(guard, root: Path, name_sha: tuple[str, str]) -> bytes:
    name, sha = name_sha
    path = root / "files" / "fake" / name
    guard.need(path.is_file() and not path.is_symlink() and
               path.resolve().is_relative_to(root) and path.stat().st_size == 1200,
               "PINNED_QUIC_FIXTURE_MISSING")
    got = guard.cmd("git", "-C", str(root), "hash-object", str(path))
    guard.need(got.returncode == 0 and got.stdout.strip() == sha,
               "PINNED_QUIC_GIT_BLOB_SHA_MISMATCH")
    data = path.read_bytes()
    guard.need(quic_header_shape(data), "UPSTREAM_QUIC_INITIAL_NOT_STRUCTURAL")
    return data


def args(guard, checkout: Path) -> list[str]:
    files = checkout / "files/fake"
    return [f"--port={DIVERT}", "--debug=1",
            "--lua-init=@" + str(checkout / "lua/zapret-lib.lua"),
            "--lua-init=@" + str(checkout / "lua/zapret-antidpi.lua"),
            "--blob=quic_probe:@" + str(files / FORGED[0]),
            f"--filter-udp={PORT}", "--filter-l7=quic",
            "--payload=quic_initial", "--lua-desync=fake:blob=quic_probe"]


def udp_rows(raw: bytes) -> list[tuple[int, int, bytes]]:
    """Strict bounded native FreeBSD lo0 DLT_NULL/LOOP IPv4 UDP capture."""
    guard = guard_module()
    decoder = guard.load_pcap_parser()
    if not 24 <= len(raw) <= 8*1024*1024 or raw[:4] not in decoder.PCAP_ENDIAN:
        raise RuntimeError("BAD_NATIVE_UDP_PCAP")
    fmt = decoder.PCAP_ENDIAN[raw[:4]]
    major, minor, _tz, _sig, snaplen, dlt = struct.unpack_from(fmt+"HHiIII", raw, 4)
    if (major, minor) != (2, 4) or not 1 <= snaplen <= 4096 or dlt not in (0, 108):
        raise RuntimeError("NOT_FREEBSD_LOOPBACK_PCAP")
    pos, count, rows = 24, 0, []
    while pos < len(raw):
        if len(raw)-pos < 16:
            raise RuntimeError("TRUNCATED_PCAP_RECORD")
        _sec, _usec, cap, orig = struct.unpack_from(fmt+"IIII", raw, pos)
        pos += 16
        count += 1
        if count > 512 or cap != orig or cap > snaplen or cap > len(raw)-pos:
            raise RuntimeError("OVERSIZED_OR_TRUNCATED_PCAP_PACKET")
        frame = raw[pos:pos+cap]
        pos += cap
        if len(frame) < 24:
            raise RuntimeError("TRUNCATED_LOOPBACK_IPV4")
        family = int.from_bytes(frame[:4], sys.byteorder if dlt == 0 else "big")
        if family != socket.AF_INET:
            continue
        if frame[4] >> 4 != 4:
            raise RuntimeError("LOOPBACK_IPV4_VERSION_INVALID")
        ihl = (frame[4] & 15)*4
        if ihl < 20 or 4+ihl+8 > len(frame):
            raise RuntimeError("IPV4_UDP_IHL_INVALID")
        total = struct.unpack_from("!H", frame, 6)[0]
        if total != len(frame)-4 or total < ihl+8 or frame[13] != 17:
            raise RuntimeError("IPV4_UDP_PACKET_LENGTH_INVALID")
        if struct.unpack_from("!H", frame, 10)[0] & 0x3fff:
            raise RuntimeError("IPV4_FRAGMENTED_UDP_NOT_ACCEPTED")
        if (ipaddress.ip_address(frame[16:20]) != ipaddress.ip_address(HOST) or
                ipaddress.ip_address(frame[20:24]) != ipaddress.ip_address(HOST)):
            continue
        segment = frame[4+ihl:4+total]
        sport, dport, udp_len, _sum = struct.unpack_from("!HHHH", segment)
        if udp_len != len(segment):
            raise RuntimeError("UDP_LENGTH_MISMATCH")
        if dport == PORT:
            rows.append((sport, dport, segment[8:]))
    if count < 1:
        raise RuntimeError("EMPTY_UDP_PCAP")
    return rows


def attest(rows: list[tuple[int, int, bytes]], original: bytes,
           forged: bytes, baseline: int, active: int) -> None:
    if baseline == active or not (0 < baseline < 65536 and 0 < active < 65536):
        raise RuntimeError("UDP_SOURCE_FLOW_NOT_UNIQUE")
    if original == forged:
        raise RuntimeError("QUIC_PROBE_BLOB_NOT_DISTINGUISHABLE")
    if not any(src == baseline and dst == PORT and data == original
               for src, dst, data in rows):
        raise RuntimeError("QUIC_BASELINE_ORIGINAL_MISSING")
    if not any(src == active and dst == PORT and data == original
               for src, dst, data in rows):
        raise RuntimeError("QUIC_ACTIVE_ORIGINAL_MISSING")
    if not any(src == active and dst == PORT and data == forged
               for src, dst, data in rows):
        raise RuntimeError("QUIC_INJECTED_FAKE_NOT_ON_WIRE")
    if any(src == baseline and dst == PORT and data == forged
           for src, dst, data in rows):
        raise RuntimeError("QUIC_FAKE_PRESENT_IN_CONTROL_FLOW")


def pcap_fixture(rows: list[tuple[int, bytes]]) -> bytes:
    """Offline parser-only IPv4 UDP packets; never native proof."""
    pcap = struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 4096, 0)
    for source, payload in rows:
        udp = struct.pack("!HHHH", source, PORT, 8+len(payload), 0)+payload
        ip = (b"\x45\x00" + struct.pack("!H", 20+len(udp)) +
              b"\x00\x00\x00\x00" + b"\x40\x11\x00\x00" +
              socket.inet_aton(HOST)*2)
        frame = socket.AF_INET.to_bytes(4, sys.byteorder)+ip+udp
        pcap += struct.pack("<IIII", 1, 0, len(frame), len(frame))+frame
    return pcap


def self_test(guard) -> None:
    inp = self_fixture()
    fake = inp[:-1]+b"\x01"
    assert inp != fake
    assert not quic_header_shape(inp[:100])
    assert not quic_header_shape(b"\x40"+inp[1:])
    assert not quic_header_shape(inp[:1]+bytes(4)+inp[5:])
    assert args(guard, Path("/tmp/p4c3-native-fixture"))[-4:] == [
        f"--filter-udp={PORT}", "--filter-l7=quic", "--payload=quic_initial",
        "--lua-desync=fake:blob=quic_probe"]
    assert RULE not in range(19000, 19011)
    assert RULE not in range(19100, 19132)
    assert guard.safe_default_rules("65535 allow ip from any to any\n")
    baseline, active = 55100, 55101
    good = pcap_fixture([(baseline, inp), (active, inp), (active, fake)])
    attest(udp_rows(good), inp, fake, baseline, active)
    for wrong in (
        [(baseline, inp), (active, inp)],
        [(baseline, inp), (active, fake)],
        [(active, inp), (active, fake)],
        [(baseline, inp), (baseline, fake), (active, inp)],
    ):
        try:
            attest(udp_rows(pcap_fixture(wrong)), inp, fake, baseline, active)
        except RuntimeError:
            continue
        raise RuntimeError("FALSE_POSITIVE_UDP_PCAP_ACCEPTED")
    for bad in (good[:-1], good[:20], good[:20]+b"\x01\x00\x00\x00"+good[24:]):
        try:
            udp_rows(bad)
        except RuntimeError:
            continue
        raise RuntimeError("TRUNCATED_UDP_PCAP_ACCEPTED")
    assert FAKE_MARKER.search("LUA: fake: 0001 : fixture\n")
    assert not FAKE_MARKER.search("LUA RUN FILE: zapret-antidpi.lua\n")
    print(MARK + "_SELF_TEST=PASS_SOURCE_ONLY", flush=True)


def native_run(guard, checkout: Path) -> None:
    # Existing exact-head-qualified owner/FD/IPFW cold-load guard.
    root, engine, before = guard.guest_gate(checkout)
    original = pinned_blob(guard, root, ORIGINAL)
    forged = pinned_blob(guard, root, FORGED)
    guard.need(original != forged, "UPSTREAM_QUIC_BLOBS_NOT_DISTINCT")
    self_test(guard)
    rule_args = ["divert", str(DIVERT), "udp", "from", HOST, "to", HOST,
                 str(PORT), "out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]
    with tempfile.TemporaryDirectory(prefix="p4c3c-quic-evidence-") as tmp:
        folder = Path(tmp)
        pcap = folder / "lo0.pcap"
        log = folder / "dvtws2.log"
        with log.open("wb") as writer:
            engine_proc = subprocess.Popen([str(engine), *args(guard, root)],
                                           cwd=root, stdout=writer,
                                           stderr=subprocess.STDOUT)
            tcpdump = None
            installed = False
            try:
                time.sleep(0.5)
                guard.need(engine_proc.poll() is None, "QUIC_DVTWS_START_FAILED")
                tcpdump = subprocess.Popen(
                    ["/usr/sbin/tcpdump", "-U", "-i", "lo0", "-nn", "-s", "4096",
                     "-c", "128", "-w", str(pcap),
                     f"udp and dst host {HOST} and dst port {PORT}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    start_new_session=True)
                time.sleep(0.6)
                guard.need(tcpdump.poll() is None, "QUIC_TCPDUMP_START_FAILED")
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, \
                     socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control, \
                     socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as selected:
                    receiver.bind((HOST, PORT))
                    receiver.settimeout(3)
                    control.bind((HOST, 0))
                    selected.bind((HOST, 0))
                    baseline = control.getsockname()[1]
                    active = selected.getsockname()[1]
                    guard.need(baseline != active, "UDP_FLOW_REUSED")
                    guard.need(control.sendto(original, (HOST, PORT)) == len(original),
                               "QUIC_BASELINE_SEND_FAILED")
                    received, addr = receiver.recvfrom(2000)
                    guard.need(received == original and addr[1] == baseline,
                               "QUIC_BASELINE_ORIGINAL_NOT_DELIVERED")
                    change = guard.cmd("/sbin/ipfw", "-q", "add", str(RULE), *rule_args)
                    guard.need(change.returncode == 0, "QUIC_DIVERT_ADD_FAILED")
                    installed = True
                    listing = guard.cmd("/sbin/ipfw", "-q", "list", str(RULE))
                    guard.need(listing.returncode == 0 and
                               listing.stdout.strip().startswith(str(RULE)),
                               "QUIC_DIVERT_RULE_MISSING")
                    guard.need(selected.sendto(original, (HOST, PORT)) == len(original),
                               "QUIC_ACTIVE_SEND_FAILED")
                    time.sleep(1.2)
                    counter = guard.cmd("/sbin/ipfw", "-a", "list", str(RULE))
                    guard.need(counter.returncode == 0 and
                               re.search(rf"(?m)^0*{RULE}\s+([1-9]\d*)\s+",
                                         counter.stdout) is not None,
                               "QUIC_DIVERT_COUNTER_ZERO")
                    guard.need(engine_proc.poll() is None, "QUIC_ENGINE_EXITED")
            finally:
                failures = []
                if tcpdump is not None:
                    if tcpdump.poll() is None:
                        tcpdump.send_signal(signal.SIGINT)
                    try:
                        tcpdump.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        tcpdump.kill()
                        tcpdump.wait(timeout=4)
                    if tcpdump.stderr is not None:
                        tcpdump.stderr.close()
                if installed and guard.cmd("/sbin/ipfw", "-q", "delete",
                                           str(RULE)).returncode != 0:
                    failures.append("QUIC_DIVERT_DELETE_FAILED")
                if engine_proc.poll() is None:
                    engine_proc.terminate()
                try:
                    engine_proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    engine_proc.kill()
                    engine_proc.wait(timeout=4)
                state = guard.cmd("/sbin/ipfw", "-q", "list")
                if state.returncode != 0 or state.stdout != before:
                    failures.append("QUIC_IPFW_STATE_NOT_RESTORED")
                guard.need(not failures, ";".join(failures))
            writer.flush()
            debug = log.read_text(errors="replace")
            selected_filter = "payload_type 'quic_initial' satisfy filter" in debug
            called = bool(FAKE_MARKER.search(debug))
            if not (selected_filter and called):
                print(f"{MARK}_TRACE=lines:{len(debug.splitlines())} "
                      f"quic_filter:{int(selected_filter)} "
                      f"fake_handler:{int(called)}", flush=True)
            guard.need(selected_filter and called,
                       "QUIC_NATIVE_FAKE_HANDLER_NOT_ATTESTED")
            print(MARK + "_NATIVE_HANDLER=PASS", flush=True)
            guard.need(pcap.is_file() and pcap.stat().st_size > 24,
                       "QUIC_LOOPBACK_PCAP_MISSING")
            attest(udp_rows(pcap.read_bytes()), original, forged, baseline, active)
            print(MARK + "=PASS_NATIVE_QUIC_HANDLER_AND_FORGED_UDP_PCAP_ONLY",
                  flush=True)


def main() -> None:
    guard = guard_module()
    if sys.argv[1:] == ["--self-test"]:
        self_test(guard)
    elif len(sys.argv) == 3 and sys.argv[1] == "--native":
        native_run(guard, Path(sys.argv[2]))
    else:
        raise RuntimeError("usage: --self-test | --native /tmp/p4c3-native-*")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(MARK + "=REFUSED:" + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
