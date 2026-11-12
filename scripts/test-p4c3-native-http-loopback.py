#!/usr/bin/env python3
"""P4c3b HTTP/multisplit real-packet witness, disposable OPNsense 26.7 only.

Reuse P4c3a's attested VM/IPFW prerequisites, socket sender and strict lo0
decoder. No installed plugin, WAN, working owner appliance or DPI-bypass claim.
"""
from __future__ import annotations

import importlib.util
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "P4C3_HTTP_MULTISPLIT"
METHOD_SPLIT = 2


def tls_probe():
    path = HERE / "test-p4c3-native-tls-loopback.py"
    spec = importlib.util.spec_from_file_location("p4c3b_existing_tls_guard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("P4C3A_GUARD_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def http_fixture() -> bytes:
    """Literal valid synthetic HTTP/1.1 request, no external connection."""
    request = (b"GET /p4c3b HTTP/1.1\r\n"
               b"Host: p4c3.example\r\n"
               b"User-Agent: zapret2-native-test\r\n"
               b"Connection: close\r\n\r\n")
    if (not request.startswith(b"GET ") or
            b"\r\nHost: p4c3.example\r\n" not in request or
            not request.endswith(b"\r\n\r\n") or not 40 < len(request) < 500):
        raise RuntimeError("HTTP_FIXTURE_INVALID")
    return request


def native_args(guard, checkout: Path) -> list[str]:
    args = guard.engine_args(checkout)
    if not (len(args) == 8 and args[-4] == f"--filter-tcp={guard.PORT}"):
        raise RuntimeError("P4C3A_ENGINE_ARGS_CONTRACT_CHANGED")
    return args[:5] + ["--filter-l7=http", "--payload=http_req",
                       "--lua-desync=multisplit:pos=method+2"]


def split_position(guard, log: str, payload: bytes) -> int:
    """Verify actual upstream Lua send-attempt shapes and HTTP marker."""
    if "payload_type 'http_req' satisfy filter" not in log:
        raise RuntimeError("HTTP_PAYLOAD_HANDLER_NOT_SELECTED")
    matches = list(guard.HANDLER_LOG.finditer(log))
    parts: dict[str, tuple[int, int, int, int]] = {}
    for m in matches:
        part = m.group("part")
        shape = tuple(int(m.group(key)) for key in
                      ("start", "end", "length", "overlap"))
        if part in parts and parts[part] != shape:
            raise RuntimeError("AMBIGUOUS_HTTP_SPLIT_MARKERS")
        parts[part] = shape
    if set(parts) != {"1", "2"}:
        raise RuntimeError("HTTP_SPLIT_NOT_EXECUTED")
    first = parts["1"]
    second = parts["2"]
    # Upstream protocol.c HttpPos(PM_HTTP_METHOD,+2) => 0-based offset 2
    # on this GET fixture; no TCP sequence overlap was configured.
    if not (payload.startswith(b"GET ") and
            first == (0, METHOD_SPLIT-1, METHOD_SPLIT, 0) and
            second == (METHOD_SPLIT, len(payload)-1,
                       len(payload)-METHOD_SPLIT, 0)):
        raise RuntimeError("HTTP_SPLIT_SHAPE_NOT_METHOD_PLUS_TWO")
    return METHOD_SPLIT


def attest_capture(guard, decoder, raw: bytes, data: bytes,
                   baseline: int, active: int) -> None:
    if baseline == active or not (0 < baseline < 65536 and 0 < active < 65536):
        raise RuntimeError("HTTP_FLOW_IDENTITY_COLLISION")
    # The active full request is intentionally replaced by real split pieces.
    # All three observations must be on their uniquely attributed source ports.
    def rows(payload: bytes):
        return decoder.records(raw, socket.AF_INET, payload,
                               ports=(guard.PORT,))
    baseline_seen = rows(data)
    active_a = rows(data[:METHOD_SPLIT])
    active_b = rows(data[METHOD_SPLIT:])
    if not any(src == baseline and dst == guard.PORT
               for src, dst, _ in baseline_seen):
        raise RuntimeError("HTTP_BASELINE_REQUEST_MISSING_FROM_PCAP")
    if not (any(src == active and dst == guard.PORT
                for src, dst, _ in active_a) and
            any(src == active and dst == guard.PORT
                for src, dst, _ in active_b)):
        raise RuntimeError("HTTP_NATIVE_SPLIT_PACKETS_MISSING_FROM_PCAP")


def self_test(guard) -> None:
    data = http_fixture()
    args = native_args(guard, Path("/tmp/p4c3-native-selftest"))
    if args[-3:] != ["--filter-l7=http", "--payload=http_req",
                     "--lua-desync=multisplit:pos=method+2"]:
        raise RuntimeError("HTTP_PROFILE_ARGUMENTS_WRONG")
    if not (METHOD_SPLIT == 2 and data[:METHOD_SPLIT] == b"GE" and
            data[METHOD_SPLIT:METHOD_SPLIT+2] == b"T "):
        raise RuntimeError("HTTP_METHOD_SPLIT_WRONG")
    selected = "* lua 'multisplit.1.1' : payload_type 'http_req' satisfy filter\n"
    part1 = "LUA: multisplit: sending part 1 0-1 len=2 seqovl=0 : fixture\n"
    part2 = (f"LUA: multisplit: sending part 2 2-{len(data)-1} "
             f"len={len(data)-2} seqovl=0 : fixture\n")
    good = selected + part1 + part2
    if split_position(guard, good, data) != 2:
        raise RuntimeError("HTTP_STATIC_SPLIT_POS_FALSE")
    wrong = (selected + part1, selected + part2, part1 + part2,
             good.replace("http_req", "tls_client_hello"),
             good.replace("part 2 2-", "part 2 3-"),
             good.replace("seqovl=0", "seqovl=1", 1),
             good.replace("part 1 0-1", "part 1 0-2"))
    for bad in wrong:
        try:
            split_position(guard, bad, data)
        except RuntimeError:
            continue
        raise RuntimeError("HTTP_STATIC_FALSE_LOG_ACCEPTED")
    decoder = guard.load_pcap_parser()
    def frame(payload: bytes, srcport: int) -> bytes:
        return decoder.fixture_frame(socket.AF_INET, payload,
                                     srcport=srcport, dstport=guard.PORT)
    baseline, active = 55100, 55101
    a = decoder.fixture_pcap(frame(data, baseline))
    b = decoder.fixture_pcap(frame(data[:2], active))[24:]
    c = decoder.fixture_pcap(frame(data[2:], active))[24:]
    attest_capture(guard, decoder, a+b+c, data, baseline, active)
    for invalid in (a, a+b, a+c, a+b+c[:-1],
                    decoder.fixture_pcap(frame(data, active))+b+c):
        try:
            attest_capture(guard, decoder, invalid, data, baseline, active)
        except RuntimeError:
            continue
        raise RuntimeError("HTTP_STATIC_FALSE_PCAP_ACCEPTED")
    if not guard.safe_default_rules("65535 allow ip from any to any\n"):
        raise RuntimeError("DEFAULT_ALLOW_GUARD_MISSING")
    print(MARK + "_SELF_TEST=PASS_SOURCE_ONLY", flush=True)


def native_run(guard, checkout: Path) -> None:
    # Important: this is the same verified cold-IPFW and foreign-owner guard
    # as the qualified P4c3a TLS test, not a new firewall implementation.
    root, engine, rules_before = guard.guest_gate(checkout)
    self_test(guard)
    decoder = guard.load_pcap_parser()
    request = http_fixture()
    with tempfile.TemporaryDirectory(prefix="p4c3b-http-evidence-") as tmp:
        dirpath = Path(tmp)
        capture = dirpath / "lo0.pcap"
        logs = dirpath / "dvtws2.log"
        with logs.open("wb") as writer:
            engine_proc = subprocess.Popen([str(engine), *native_args(guard, root)],
                                           cwd=root, stdout=writer,
                                           stderr=subprocess.STDOUT)
            tcpdump = None
            installed = False
            try:
                time.sleep(0.5)
                guard.need(engine_proc.poll() is None, "HTTP_DVTWS2_START_FAILED")
                tcpdump = subprocess.Popen(
                    ["/usr/sbin/tcpdump", "-U", "-i", "lo0", "-nn",
                     "-s", "4096", "-c", "128", "-w", str(capture),
                     f"tcp and dst host {guard.HOST} and dst port {guard.PORT}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    start_new_session=True)
                time.sleep(0.6)
                guard.need(tcpdump.poll() is None, "HTTP_TCPDUMP_START_FAILED")
                baseline = guard.send_hello(request, require_delivery=True)
                added = guard.cmd("/sbin/ipfw", "-q", "add", str(guard.RULE),
                                  *guard.RULE_ARGS)
                guard.need(added.returncode == 0, "HTTP_ISOLATED_DIVERT_ADD_FAILED")
                installed = True
                current = guard.cmd("/sbin/ipfw", "-q", "list", str(guard.RULE))
                guard.need(current.returncode == 0 and
                           current.stdout.strip().startswith(str(guard.RULE)),
                           "HTTP_ISOLATED_DIVERT_RULE_NOT_ATTESTED")
                active = guard.send_hello(request, require_delivery=False)
                guard.need(active != baseline, "HTTP_FLOW_IDENTITY_COLLISION")
                time.sleep(1)
                counter = guard.cmd("/sbin/ipfw", "-a", "list", str(guard.RULE))
                guard.need(counter.returncode == 0 and re.search(
                    rf"(?m)^0*{guard.RULE}\s+([1-9]\d*)\s+",
                    counter.stdout) is not None,
                    "HTTP_ISOLATED_DIVERT_COUNTER_ZERO")
                guard.need(engine_proc.poll() is None,
                           "HTTP_ENGINE_STOPPED_UNEXPECTEDLY")
            finally:
                errors: list[str] = []
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
                                           str(guard.RULE)).returncode != 0:
                    errors.append("HTTP_DIVERT_DELETE_FAILED")
                if engine_proc.poll() is None:
                    engine_proc.terminate()
                try:
                    engine_proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    engine_proc.kill()
                    engine_proc.wait(timeout=4)
                restored = guard.cmd("/sbin/ipfw", "-q", "list")
                if restored.returncode != 0 or restored.stdout != rules_before:
                    errors.append("HTTP_IPFW_DEFAULT_RULES_NOT_RESTORED")
                guard.need(not errors, ";".join(errors))
            writer.flush()
            log = logs.read_text(errors="replace")
            try:
                offset = split_position(guard, log, request)
            except RuntimeError:
                # Only bounded metadata: no captured request, no Lua hex dump.
                present = {m.group("part") for m in
                           guard.HANDLER_LOG.finditer(log)}
                print(f"{MARK}_TRACE=lines:{len(log.splitlines())} "
                      f"parts:{','.join(sorted(present)) or 'none'} "
                      f"http_filter:{int('payload_type ' + chr(39) + 'http_req' + chr(39) + ' satisfy filter' in log)}",
                      flush=True)
                raise
            guard.need(offset == METHOD_SPLIT, "HTTP_METHOD_OFFSET_MISMATCH")
            print(MARK + "_NATIVE_HANDLER=PASS", flush=True)
            guard.need(capture.is_file() and capture.stat().st_size > 24,
                       "HTTP_NATIVE_LOOPBACK_PCAP_MISSING")
            attest_capture(guard, decoder, capture.read_bytes(), request,
                           baseline, active)
            print(MARK + "=PASS_NATIVE_HTTP_HANDLER_AND_SPLIT_PCAP_ONLY", flush=True)


def main() -> None:
    guard = tls_probe()
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
