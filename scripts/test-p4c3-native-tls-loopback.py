#!/usr/bin/env python3
"""P4c3a: real TLS/multisplit handler witness, disposable OPNsense 26.7 only.

Evidence is restricted to one selected TCP/TLS ClientHello on lo0. This is
not a successful TLS handshake, a provider DPI bypass, or an owner's device.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import platform
import re
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
PIN = "038c97e5819df10f8e8c22a2f1fffe57f2f7379b"
MARK = "P4C3_TLS_MULTISPLIT"
RULE, DIVERT, PORT = 19350, 19898, 6544
HOST = "127.0.0.1"
RULE_ARGS = ["divert", str(DIVERT), "tcp", "from", HOST, "to", HOST,
             str(PORT), "out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]
HANDLER_LOG = re.compile(\n    r"(?m)^LUA:\\s+multisplit:\\s+sending part ([12]) "\n    r"\\d+-\\d+ len=[1-9]\\d* seqovl=\\d+\\s+:")


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError(why)


def cmd(*args: str, timeout: int = 12) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True,
                          check=False, timeout=timeout)


def hello_fixture() -> bytes:
    """Actual OpenSSL MemoryBIO ClientHello; no external network request."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    tls = ctx.wrap_bio(incoming, outgoing, server_side=False,
                       server_hostname="p4c3.example")
    try:
        tls.do_handshake()
    except ssl.SSLWantReadError:
        pass
    else:
        raise RuntimeError("TLS fixture unexpectedly completed handshake")
    data = outgoing.read()
    need(150 <= len(data) <= 1200 and data[:2] == b"\x16\x03" and
         data[5] == 1 and int.from_bytes(data[3:5], "big") == len(data)-5 and
         b"p4c3.example" in data, "BAD_TLS_CLIENT_HELLO_FIXTURE")
    return data


def engine_args(checkout: Path) -> list[str]:
    return [f"--port={DIVERT}", "--debug=1",
            "--lua-init=@" + str(checkout / "lua/zapret-lib.lua"),
            "--lua-init=@" + str(checkout / "lua/zapret-antidpi.lua"),
            f"--filter-tcp={PORT}", "--filter-l7=tls",
            "--payload=tls_client_hello",
            "--lua-desync=multisplit:pos=midsld:seqovl=1"]


def self_test() -> None:
    data = hello_fixture()
    assert engine_args(Path("/tmp/p4c3-native-fixture"))[-4:] == [
        f"--filter-tcp={PORT}", "--filter-l7=tls", "--payload=tls_client_hello",
        "--lua-desync=multisplit:pos=midsld:seqovl=1"]
    # Real v1.0.7 Lua logs successful per-packet send attempts as
    # "LUA: multisplit: sending part ...", not as the C-side dispatch string.
    # Both parts are required for the expected single midsld split.
    selected = "* lua 'multisplit.1.1' : payload_type 'tls_client_hello' satisfy filter\n"
    part1 = "LUA: multisplit: sending part 1 0-93 len=95 seqovl=1 : fixture\n"
    part2 = "LUA: multisplit: sending part 2 94-185 len=92 seqovl=0 : fixture\n"
    assert observed_log(selected + part1 + part2)
    assert not observed_log(selected + part2)
    assert not observed_log(selected + part1)
    assert not observed_log(part1 + part2)
    assert not observed_log(selected + "LUA RUN FILE: zapret-antidpi.lua\n")
    assert not observed_log(selected + "LUA: fake: sending part 1 0-93 len=95 seqovl=1 : fixture\n")
    assert data.startswith(b"\x16\x03") and b"p4c3.example" in data
    assert RULE not in range(19000, 19011) and RULE not in range(19100, 19132)
    assert safe_default_rules("65535 allow ip from any to any\n")
    assert not safe_default_rules("19000 divert 989 tcp from any to any\n65535 allow ip from any to any\n")
    assert not safe_default_rules("65535 count ip from any to any not diverted\n")
    print(MARK + "_SELF_TEST=PASS_SOURCE_ONLY")


def safe_default_rules(text: str) -> bool:
    """Reuse the established native guest default-allow ownership contract."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return (lines.count("65535 allow ip from any to any") == 1 and
            all(line == "65535 allow ip from any to any" or
                re.fullmatch(r"65535 count ip from any to any not(?: .*)?", line)
                for line in lines))


def guest_gate(checkout: Path) -> tuple[Path, Path, str]:
    need(os.getenv("GITHUB_ACTIONS") == "true" and
         os.getenv("ZAPRET2_P4C3_DISPOSABLE_NATIVE") == "1",
         "DISPOSABLE_GITHUB_VM_OPT_IN_REQUIRED")
    need(platform.system() == "FreeBSD" and os.geteuid() == 0,
         "FREEBSD_ROOT_GUEST_REQUIRED")
    need(not checkout.is_symlink(), "CHECKOUT_SYMLINK")
    root = checkout.resolve(strict=True)
    need(root.parent == Path("/tmp") and root.name.startswith("p4c3-native-"),
         "TEMPORARY_PINNED_CHECKOUT_REQUIRED")
    need(cmd("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip() == PIN,
         "UPSTREAM_SHA_MISMATCH")
    engine = root / "nfq2/dvtws2"
    need(engine.is_file() and not engine.is_symlink() and
         os.access(engine, os.X_OK), "NATIVE_ENGINE_NOT_BUILT")
    for filename in ("zapret-lib.lua", "zapret-antidpi.lua"):
        path = root / "lua" / filename
        need(path.is_file() and not path.is_symlink() and path.stat().st_size > 1000,
             "PINNED_LUA_MISSING")
    need(Path("/usr/sbin/tcpdump").is_file(), "NATIVE_TCPDUMP_MISSING")
    need(cmd("pkg", "info", "-e", "os-zapret2-restyle").returncode != 0,
         "INSTALLED_PLUGIN_FORBIDDEN")
    need(cmd("pgrep", "-x", "dvtws2").returncode == 1,
         "ACTIVE_ENGINE_OR_PGREP_FAILURE")
    # Fresh OPNsense guests can have IPFW entirely UNLOADED. Reuse the
    # established cold-boot default-accept gate, never load over foreign rules.
    listing = cmd("/sbin/ipfw", "-q", "list")
    if listing.returncode != 0:
        module = cmd("/sbin/kldstat", "-q", "-m", "ipfw")
        need(listing.returncode == 71 and
             "retrieving config failed: Protocol not available" in listing.stderr and
             module.returncode == 1, "IPFW_COLD_LOAD_NOT_SAFE")
        need(cmd("/bin/kenv", "net.inet.ip.fw.default_to_accept=1").returncode == 0,
             "DISPOSABLE_DEFAULT_ACCEPT_KENV_FAILED")
        setting = cmd("/bin/kenv", "-qv", "net.inet.ip.fw.default_to_accept")
        need(setting.returncode == 0 and setting.stdout.strip() in (
             'net.inet.ip.fw.default_to_accept="1"',
             'net.inet.ip.fw.default_to_accept=1'),
             "DISPOSABLE_DEFAULT_ACCEPT_NOT_ATTESTED")
        need(cmd("/sbin/kldload", "ipfw").returncode == 0,
             "DISPOSABLE_IPFW_COLD_LOAD_FAILED")
        listing = cmd("/sbin/ipfw", "-q", "list")
    need(listing.returncode == 0 and safe_default_rules(listing.stdout),
         "NONDEFAULT_IPFW_RULES_PRESENT")
    for key in ("net.inet.ip.fw.one_pass", "net.inet.ip.fw.enable"):
        result = cmd("sysctl", "-n", key)
        need(result.returncode == 0 and result.stdout.strip() == "1",
             "DISPOSABLE_IPFW_NOT_READY:" + key)
    modules = cmd("kldstat", "-q", "-m", "ipdivert")
    need(modules.returncode in (0, 1), "IPDIVERT_STATE_UNKNOWN")
    if modules.returncode == 1:
        need(cmd("kldload", "ipdivert").returncode == 0,
             "DISPOSABLE_IPDIVERT_UNAVAILABLE")
    need(cmd("kldstat", "-q", "-m", "ipdivert").returncode == 0,
         "IPDIVERT_NOT_READY")
    return root, engine, listing.stdout


def send_hello(data: bytes, *, require_delivery: bool) -> int:
    received: list[bytes] = []
    errs: list[str] = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.settimeout(4)

        def read_once() -> None:
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(2)
                    buf = b""
                    while len(buf) < len(data):
                        piece = conn.recv(2048)
                        if not piece:
                            break
                        buf += piece
                    received.append(buf)
            except (OSError, TimeoutError) as exc:
                errs.append(type(exc).__name__)

        thread = threading.Thread(target=read_once, daemon=True)
        thread.start()
        sender_port = 0
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(4)
                client.connect((HOST, PORT))
                sender_port = client.getsockname()[1]
                try:
                    client.sendall(data)
                except (OSError, TimeoutError):
                    if require_delivery:
                        raise
                try:
                    client.shutdown(socket.SHUT_WR)
                except OSError:
                    if require_delivery:
                        raise
        finally:
            thread.join(5)
        need(not thread.is_alive() and sender_port > 0, "TLS_SENDER_NOT_COMPLETE")
        if require_delivery:
            need(not errs and received == [data], "CONTROL_CLIENTHELLO_NOT_DELIVERED")
        # A native split may legitimately prevent intact test-peer delivery.
        return sender_port


def observed_log(log: str) -> bool:
    # v1.0.7 upstream Lua prints one message per actually attempted segment;
    # declarations, function existence and mere Lua initialization cannot pass.
    # A positive native packet counter and independent PCAP are ALSO required.
    return (set(HANDLER_LOG.findall(log)) == {"1", "2"} and
            "payload_type 'tls_client_hello' satisfy filter" in log)


def native_run(checkout: Path) -> None:
    root, engine, rules_before = guest_gate(checkout)
    self_test()
    helper_path = HERE / "test-freebsd15-native-tls-strategy.py"
    spec = importlib.util.spec_from_file_location("p4c3_native_pcap_reader", helper_path)
    need(spec is not None and spec.loader is not None, "EXISTING_PCAP_READER_REQUIRED")
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    data = hello_fixture()
    with tempfile.TemporaryDirectory(prefix="p4c3-tls-evidence-") as tmp:
        evidence = Path(tmp)
        capture_path = evidence / "lo0.pcap"
        log_path = evidence / "dvtws2.log"
        with log_path.open("wb") as logfile:
            proc = subprocess.Popen([str(engine), *engine_args(root)], cwd=root,
                                    stdout=logfile, stderr=subprocess.STDOUT)
            dump = None
            installed = False
            try:
                time.sleep(0.5)
                need(proc.poll() is None, "DVTWS2_START_FAILED")
                dump = subprocess.Popen(
                    ["/usr/sbin/tcpdump", "-U", "-i", "lo0", "-nn", "-s", "4096",
                     "-c", "128", "-w", str(capture_path),
                     f"tcp and dst host {HOST} and dst port {PORT}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    start_new_session=True)
                time.sleep(0.6)
                need(dump.poll() is None, "NATIVE_TCPDUMP_START_FAILED")
                baseline = send_hello(data, require_delivery=True)
                add = cmd("/sbin/ipfw", "-q", "add", str(RULE), *RULE_ARGS)
                need(add.returncode == 0, "ISOLATED_DIVERT_ADD_FAILED")
                installed = True
                current = cmd("/sbin/ipfw", "-q", "list", str(RULE))
                need(current.returncode == 0 and current.stdout.strip().startswith(str(RULE)),
                     "ISOLATED_DIVERT_RULE_MISSING")
                active = send_hello(data, require_delivery=False)
                need(active != baseline, "TLS_SENDER_FLOW_REUSED")
                time.sleep(1)
                count = cmd("/sbin/ipfw", "-a", "list", str(RULE))
                need(count.returncode == 0 and re.search(
                    rf"(?m)^0*{RULE}\s+([1-9]\d*)\s+", count.stdout) is not None,
                    "ISOLATED_DIVERT_RULE_PACKET_COUNT_ZERO")
                need(proc.poll() is None, "DVTWS2_STOPPED_UNEXPECTEDLY")
            finally:
                cleanup_errors: list[str] = []
                if dump is not None:
                    if dump.poll() is None:
                        dump.send_signal(signal.SIGINT)
                    try:
                        dump.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        dump.kill()
                        dump.wait(timeout=4)
                    if dump.stderr:
                        dump.stderr.close()
                if installed:
                    remove = cmd("/sbin/ipfw", "-q", "delete", str(RULE))
                    if remove.returncode != 0:
                        cleanup_errors.append("ISOLATED_DIVERT_DELETE_FAILED")
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
                after = cmd("/sbin/ipfw", "-q", "list")
                if after.returncode != 0 or after.stdout != rules_before:
                    cleanup_errors.append("NATIVE_IPFW_RULES_NOT_RESTORED")
                need(not cleanup_errors, ";".join(cleanup_errors))
            logfile.flush()
            log = log_path.read_text(errors="replace")
            if not observed_log(log):
                # Disposable synthetic traffic only; bounded troubleshooting
                # receipt. Never print full engine log or packet content.
                # Do not print raw Lua hex dumps or the intercepted payload,
                # even in synthetic VM: only bounded evidence counters.
                tls_filter = "payload_type 'tls_client_hello' satisfy filter" in log
                parts = set(HANDLER_LOG.findall(log))
                print(f"{MARK}_TRACE=bytes:{len(log)} lines:{len(log.splitlines())} "
                      f"parts:{','.join(sorted(parts)) or 'none'} "
                      f"tls_filter:{int(tls_filter)}",
                      flush=True)
            need(observed_log(log), "NO_NATIVE_TLS_MULTISPLIT_PACKET_DISPATCH")
            print(MARK + "_NATIVE_HANDLER=PASS", flush=True)
            need(capture_path.is_file() and capture_path.stat().st_size > 24,
                 "MISSING_NATIVE_LOOPBACK_PCAP")
            found = parser.records(capture_path.read_bytes(), socket.AF_INET, data,
                                   ports=(PORT,))
            observed_ports = {source for source, dest, _ttl in found if dest == PORT}
            need({baseline, active}.issubset(observed_ports),
                 "NATIVE_PCAP_LACKS_BASELINE_AND_ACTIVE_CLIENTHELLO")
            print(MARK + "=PASS_NATIVE_TLS_HANDLER_DISPATCH_AND_PCAP_ONLY", flush=True)


def main() -> None:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 3 and sys.argv[1] == "--native":
        native_run(Path(sys.argv[2]))
    else:
        raise RuntimeError("usage: --self-test | --native /tmp/p4c3-native-...checkout")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(MARK + "=REFUSED:" + str(exc), file=sys.stderr)
        raise SystemExit(2)
