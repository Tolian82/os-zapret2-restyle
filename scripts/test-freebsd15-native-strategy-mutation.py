#!/usr/bin/env python3
"""FreeBSD15.1 VM-only native TCP packet modification/Exclude byte witness.

Uses actual upstream dvtws2 Lua http_hostcase, production Exclude compiler and
real lo0 IPFW divert. Never run on an installed OPNsense appliance.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
MARKER = "NATIVE_STRATEGY_PACKET_ATTRIBUTION"
PORTS = (6531, 6532, 6533)
RULE, DIVERT = 19006, 9990
REQ = b"GET /proof HTTP/1.1\r\nHost: Stage5.Example\r\nConnection: close\r\n\r\n"
MOD = REQ.replace(b"Host:", b"host:", 1)
ARGV = ["divert", str(DIVERT), "tcp", "from", "any", "to", "any",
        "6531-6533", "out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]


def attest(observed: bytes, modified: bool) -> None:
    if observed != (MOD if modified else REQ) or len(observed) != len(REQ):
        raise RuntimeError("TCP receiver bytes differ from exact expected strategy/Exclude result")


def static_test() -> None:
    assert MOD != REQ and len(MOD) == len(REQ) and MOD.count(b"host:") == 1
    attest(MOD, True)
    attest(REQ, False)
    for data, selected in ((REQ, True), (MOD, False), (REQ[:-1], False)):
        try:
            attest(data, selected)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("ambiguous/native mutation regression was accepted")
    print("NATIVE_STRATEGY_ATTRIBUTION_STATIC=PASS: exact positive/negative bytes and fail-closed mismatch")


def guarded_vm():
    if (os.getenv("ZAPRET2_ISOLATED_FREEBSD_VM_EXCLUDE_WIRE_TEST") != "1"
            or platform.system() != "FreeBSD" or os.geteuid() != 0
            or Path("/conf/config.xml").exists() or Path("/usr/local/opnsense").exists()):
        raise RuntimeError("requires explicitly opted-in disposable FreeBSD VM, never OPNsense")
    spec = importlib.util.spec_from_file_location("native_exclude", HERE / "test-freebsd15-native-engine-exclude.py")
    if not spec or not spec.loader:
        raise RuntimeError("native engine guard unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter, table = module.guest_gate()
    return module, adapter, table


def compile_candidate(root: Path, upstream: Path, phase: str) -> list[str]:
    from global_exclusions import audit, compose, segments, templates_and_imports
    from ipset_policy import LISTS, parse_ipset
    release = root / phase
    managed = release / "managed"
    managed.mkdir(parents=True)
    (managed / "hostlist-exclude.txt").write_text("")
    manifest = {"schema_version": 1, "lists": {}}
    for name in LISTS:
        raw = ("127.0.0.1/32\n::1/128\n" if phase == "excluded" else
               "192.0.2.1/32\n2001:db8::1/128\n" if phase == "nonmatching" else "") if name == "exclude" else ""
        data, proof = parse_ipset(raw.encode(), name, collapse=name == "exclude")
        (managed / f"ipset-{name}.txt").write_text(data)
        manifest["lists"][name] = proof
    (release / "ipset-manifest.json").write_text(json.dumps(manifest))
    lua = [upstream / "lua" / name for name in ("zapret-lib.lua", "zapret-antidpi.lua")]
    if not all(p.is_file() for p in lua):
        raise RuntimeError("pinned upstream native strategy Lua missing")
    # The pinned upstream checkout is mktemp mode 0700. Native dvtws2 drops
    # privileges while loading Lua, so stage exact original bytes in a 0755
    # test-only tree instead of weakening permissions on the source checkout.
    staged = root / "lua"
    staged.mkdir(exist_ok=True)
    for original in lua:
        shutil.copyfile(original, staged / original.name)
    lua = [staged / p.name for p in lua]
    raw = f"--port={DIVERT}\n" + "".join(f"--lua-init=@{p}\n" for p in lua)
    for i, port in enumerate(PORTS):
        raw += (f"--filter-tcp={port}\n--filter-l7=http\n--payload=http_req\n"
                "--lua-desync=http_hostcase:spell=host\n")
        if i + 1 < len(PORTS):
            raw += "--new\n"
    ip_ref = str(managed / "ipset-exclude.txt")
    result = compose(raw, managed / "hostlist-exclude.txt", str(managed / "hostlist-exclude.txt"),
                     managed / "ipset-exclude.txt", ip_ref, release, release, upstream)
    audit(result, managed / "hostlist-exclude.txt", str(managed / "hostlist-exclude.txt"),
          managed / "ipset-exclude.txt", ip_ref, release, release, upstream)
    rows = segments(result)
    _, kinds = templates_and_imports(rows)
    expected = 0 if phase == "baseline" else len(PORTS)
    if (kinds != ["profile"] * 3
            or sum(row.count("--ipset-exclude=" + ip_ref) for row in rows) != expected
            or any(row.count("--lua-desync=http_hostcase:spell=host") != 1 for row in rows)):
        raise RuntimeError("real native Exclude/strategy profile binding mismatch")
    return result.split()


def receive_tcp(family: int, host: str, port: int) -> bytes:
    received, errors = [], []
    with socket.socket(family, socket.SOCK_STREAM) as server:
        # Sequential A/N/B connections can leave the listening port in
        # TIME_WAIT after shutdown; do not fail for a prior closed test flow.
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        server.bind((host, port))
        server.listen(1)
        server.settimeout(5)

        def worker():
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(5)
                    result = b""
                    while len(result) < len(REQ):
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        result += chunk
                    received.append(result)
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(5)
                client.connect((host, port))
                client.sendall(REQ)
                client.shutdown(socket.SHUT_WR)
        finally:
            thread.join(timeout=6)
        if thread.is_alive() or errors or len(received) != 1:
            raise RuntimeError("native TCP receiver observation incomplete")
        return received[0]


def phase_test(adapter, engine: Path, upstream: Path, root: Path, phase: str) -> None:
    args = compile_candidate(root, upstream, phase)
    log = root / (phase + ".log")
    with log.open("wb") as output:
        proc = subprocess.Popen([str(engine), *args], stdout=output, stderr=subprocess.STDOUT)
        installed = False
        try:
            time.sleep(0.6)
            if proc.poll() is not None:
                raise RuntimeError("native dvtws2 startup failed: " + log.read_text(errors="replace")[-1200:])
            for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
                attest(receive_tcp(family, host, PORTS[0]), False)
            adapter.add_rule(RULE, ARGV)
            installed = True
            if adapter.list_rules(19000, 19010) != {RULE: ARGV}:
                raise RuntimeError("native IPFW rule scope changed")
            for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
                for port in PORTS:
                    attest(receive_tcp(family, host, port), phase != "excluded")
                attest(receive_tcp(family, host, 6540), False)
            if adapter.rule_counters(RULE, ARGV)[0] < 6 or proc.poll() is not None:
                raise RuntimeError("native IPFW intercept/process continuity not confirmed")
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
                raise RuntimeError("native IPFW rule leaked after phase")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--static":
        static_test()
        return 0
    if len(sys.argv) != 2:
        raise RuntimeError("usage: test-freebsd15-native-strategy-mutation.py --static | /path/to/pinned/dvtws2")
    static_test()
    module, adapter, table = guarded_vm()
    engine = Path(sys.argv[1]).resolve()
    upstream = engine.parent.parent
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise RuntimeError("pinned native dvtws2 missing")
    with tempfile.TemporaryDirectory(prefix="stage5-strategy-wire-") as folder:
        root = Path(folder)
        root.chmod(0o755)  # native engine drops privileges before reading fixtures.
        for phase in ("baseline", "nonmatching", "excluded"):
            phase_test(adapter, engine, upstream, root, phase)
    if not table.safe_default_rules(module.native("/sbin/ipfw", "-q", "list").stdout):
        raise RuntimeError("default allow IPFW baseline not restored")
    print(MARKER + "=PASS: native HTTP strategy modifies IPv4/IPv6 TCP bytes; nonmatching Exclude modifies; exact matching Exclude preserves; owned IPFW restored")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(MARKER + "=FAIL: " + str(error), file=sys.stderr)
        raise SystemExit(1)
