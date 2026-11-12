#!/usr/bin/env python3
"""P0 #1052: isolated native auto-hostlist observer witness (no product mutation).

One genuine upstream v1.0.7 FreeBSD dvtws2, with two ordered profiles:
  1) existing legitimate hostlist-bound HTTP strategy (Lua multisplit);
  2) after it, hostlist-auto observer with NO Lua actions and TCP RST disabled.
Only localhost test packets on a disposable, attested OPNsense guest.
A dry-run or source-only result is not accepted as packet-level proof.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
MARK = "P0_NATIVE_AUTO_OBSERVER"
HOST, PORT, DIVERT = "127.0.0.1", 6545, 19899
RULES = (19351, 19352)
KNOWN, UNKNOWN = "known.p0.invalid", "unknown.p0.invalid"


def need(ok: bool, code: str) -> None:
    if not ok:
        raise RuntimeError(code)


def guard_module():
    path = HERE / "test-p4c3-native-tls-loopback.py"
    spec = importlib.util.spec_from_file_location("p0_existing_native_guard", path)
    need(spec is not None and spec.loader is not None, "NATIVE_GUARD_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def request(host: str) -> bytes:
    return ("GET /p0 HTTP/1.1\r\nHost: " + host +
            "\r\nConnection: close\r\n\r\n").encode("ascii")


def engine_args(checkout: Path, tmp: Path) -> list[str]:
    return [
        f"--port={DIVERT}", "--debug=1",
        f"--hostlist-auto-debug={tmp / 'debug.log'}",
        f"--lua-init=@{checkout / 'lua/zapret-lib.lua'}",
        f"--lua-init=@{checkout / 'lua/zapret-antidpi.lua'}",
        f"--filter-tcp={PORT}", "--filter-l7=http",
        f"--hostlist={tmp / 'known.txt'}", "--payload=http_req",
        "--lua-desync=multisplit:pos=method+2", "--new",
        f"--filter-tcp={PORT}", "--filter-l7=http",
        f"--hostlist-auto={tmp / 'inbox.txt'}",
        "--hostlist-auto-fail-threshold=1",
        "--hostlist-auto-retrans-reset=0",
    ]


def rules() -> tuple[list[str], list[str]]:
    # Two narrow loopback-only divert directions; no catch-all IPFW capture.
    common = ["out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]
    client = ["divert", str(DIVERT), "tcp",
              "from", HOST, "to", HOST, str(PORT), *common]
    server = ["divert", str(DIVERT), "tcp",
              "from", HOST, str(PORT), "to", HOST, *common]
    return client, server


def self_test() -> None:
    args = engine_args(Path("/tmp/p4c3-native-fake"), Path("/tmp/p0-fake"))
    need(args.count("--new") == 1 and args[args.index("--new") + 1:]
         == [f"--filter-tcp={PORT}", "--filter-l7=http",
             "--hostlist-auto=/tmp/p0-fake/inbox.txt",
             "--hostlist-auto-fail-threshold=1",
             "--hostlist-auto-retrans-reset=0"],
         "OBSERVER_HAS_ACTION_OR_RST")
    need(any(a.startswith("--lua-desync=") for a in args[:args.index("--new")])
         and not any(a.startswith("--lua-desync=")
                     for a in args[args.index("--new") + 1:]),
         "NATIVE_ACTION_ISOLATION_INVALID")
    a, b = rules()
    need(a != b and all("lo0" in x and "not" in x for x in (a, b)),
         "NON_SCOPED_RULE")
    need(19351 not in range(19000, 19011) and
         19352 not in range(19100, 19132), "PRODUCTION_RULE_COLLISION")
    need(request(UNKNOWN).endswith(b"\r\n\r\n") and
         request(UNKNOWN) != request(KNOWN), "HTTP_FIXTURE_INVALID")
    guard = guard_module()
    need(guard.safe_default_rules("65535 allow ip from any to any\n"),
         "DEFAULT_RULE_GUARD_MISSING")
    need(not guard.safe_default_rules(
        "19351 divert 19899 tcp from any to any\n65535 allow ip from any to any\n"),
        "FOREIGN_RULE_NOT_REJECTED")
    print(MARK + "_SELF_TEST=PASS_SOURCE_ONLY", flush=True)


def exchange(host: str, *, force_rst: bool) -> bytes:
    observed: list[bytes] = []
    failures: list[str] = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST, PORT))
        listener.listen(1)
        listener.settimeout(5)

        def server() -> None:
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    data = bytearray()
                    while b"\r\n\r\n" not in data and len(data) < 1024:
                        piece = conn.recv(1024)
                        if not piece:
                            break
                        data.extend(piece)
                    observed.append(bytes(data))
                    if force_rst:
                        conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                        struct.pack("ii", 1, 0))
                    else:
                        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            except (OSError, TimeoutError) as exc:
                failures.append(type(exc).__name__)

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(4)
            client.connect((HOST, PORT))
            try:
                client.sendall(request(host))
                client.recv(4096)
            except (ConnectionResetError, BrokenPipeError, TimeoutError, OSError):
                pass  # An intentional synthetic RST is part of the test.
        worker.join(6)
        need(not worker.is_alive() and not failures, "TEST_TCP_PEER_FAILED")
        need(len(observed) == 1, "NO_SYNTHETIC_TCP_DELIVERY")
        return observed[0]


def native(checkout: Path) -> None:
    guard = guard_module()
    root, engine, before = guard.guest_gate(checkout)
    self_test()
    with tempfile.TemporaryDirectory(prefix="p0-auto-observer-") as dirname:
        tmp = Path(dirname)
        tmp.chmod(0o755)
        for name, data in (("known.txt", KNOWN + "\n"),
                           ("inbox.txt", ""), ("debug.log", "")):
            f = tmp / name
            f.write_text(data, encoding="ascii")
            f.chmod(0o666 if name != "known.txt" else 0o644)
        log = tmp / "engine.log"
        installed: list[int] = []
        process = None
        cleanup: list[str] = []
        try:
            with log.open("wb") as output:
                process = subprocess.Popen([str(engine), *engine_args(root, tmp)],
                                           cwd=root, stdout=output,
                                           stderr=subprocess.STDOUT)
                time.sleep(0.5)
                need(process.poll() is None, "NATIVE_ENGINE_START_FAILED")
                for number, args in zip(RULES, rules()):
                    added = guard.cmd("/sbin/ipfw", "-q", "add", str(number), *args)
                    need(added.returncode == 0, "ISOLATED_DIVERT_ADD_FAILED")
                    installed.append(number)
                need(exchange(KNOWN, force_rst=False) is not None,
                     "KNOWN_FLOW_NOT_CAPTURED")
                unknown_before = exchange(UNKNOWN, force_rst=True)
                time.sleep(0.5)
                # A successful native raw append is mandatory: the debuglog
                # 'adding to' line alone is not sufficient evidence.
                inbox = (tmp / "inbox.txt").read_text(encoding="ascii")
                need(inbox.splitlines() == [UNKNOWN], "NATIVE_RAW_APPEND_NOT_ATTESTED")
                unknown_after = exchange(UNKNOWN, force_rst=False)
                need(unknown_before == request(UNKNOWN) and
                     unknown_after == request(UNKNOWN),
                     "OBSERVER_COVERTLY_MUTATED_UNKNOWN_HTTP")
                need(process.poll() is None, "ENGINE_EXITED_AFTER_DISCOVERY")
                counters = [guard.cmd("/sbin/ipfw", "-a", "list", str(n))
                            for n in RULES]
                need(all(c.returncode == 0 and re.search(
                    rf"(?m)^0*{n}\s+[1-9]\d*\s+", c.stdout)
                         for n, c in zip(RULES, counters)),
                     "NATIVE_BIDIRECTIONAL_DIVERT_NOT_ATTESTED")
        finally:
            for number in reversed(installed):
                if guard.cmd("/sbin/ipfw", "-q", "delete", str(number)).returncode:
                    cleanup.append("TEST_RULE_DELETE_FAILED")
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            listing = guard.cmd("/sbin/ipfw", "-q", "list")
            if listing.returncode != 0 or listing.stdout != before:
                cleanup.append("NATIVE_IPFW_RESTORE_FAILED")
            need(not cleanup, ";".join(cleanup))
        content = log.read_text(errors="replace")
        debug = (tmp / "debug.log").read_text(errors="replace")
        need(f"adding to {tmp / 'inbox.txt'}" in debug and
             f" : profile 2 " in debug, "DEBUG_NOT_CORRELATED_TO_RAW_APPEND")
        need("desync profile 1 " in content and
             "autohostlist profile 2 " in content,
             "FIRST_MATCH_PROFILE_EVIDENCE_MISSING")
        need("* lua 'multisplit" in content,
             "EXISTING_AUTHORIZED_LUA_NOT_EXERCISED")
        # The unknown observer has NO Lua actions by native profile construction;
        # the synthetic HTTP request reaches its server unchanged both before
        # and after raw inclusion, and native RST injection is disabled.
        print(MARK + "=PASS_NATIVE_LOOPBACK_OBSERVER_NON_ACTIVATING_ONLY",
              flush=True)


def main() -> None:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 3 and sys.argv[1] == "--native":
        native(Path(sys.argv[2]))
    else:
        raise RuntimeError("usage: --self-test | --native /tmp/p4c3-native-*")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(MARK + "=REFUSED:" + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
