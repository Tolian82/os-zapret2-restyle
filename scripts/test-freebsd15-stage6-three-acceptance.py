#!/usr/bin/env python3
"""Exactly THREE Stage 6 acceptance scenarios in disposable FreeBSD 15.1.

1. Real AAAA-only TLS Stage85 three-attempt shortlist through production
   candidate adapter, actual pinned upstream dvtws2 and CA-verified curl.
2. Persisted IPv6 OFF/ON network gate plus actual dual A+AAAA candidate.
3. Wrong-CA real TLS failure remains FAIL and restores owned IPFW/processes.
Existing mandatory CI remains separate; no appliance, WAN or GUI claimed.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
SCRIPTS = ROOT / "scripts"
MARK = "STAGE6_THREE_ACCEPTANCE"
STRATEGY = "--lua-desync=pktmod:ip_ttl=23:ip6_ttl=37\n"
PASS_TEXT = (
    "1=AAAA-only real Stage85 CA-verified 3/3; "
    "2=IPv6 OFF/ON and real A+AAAA pinned TLS; "
    "3=wrong-CA failure and exact cleanup"
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("native helper missing: " + path.name)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def shell(*argv: str, env=None):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=25, check=False, env=env)


def setup_cert(directory: Path, name: str) -> tuple[Path, Path]:
    key, cert = directory / (name + ".key"), directory / (name + ".crt")
    res = shell("/usr/bin/openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                "-sha256", "-days", "1", "-keyout", str(key), "-out", str(cert),
                "-subj", "/CN=aaaa.lab.test",
                "-addext", "subjectAltName=DNS:aaaa.lab.test,DNS:dual.lab.test")
    if res.returncode or not cert.is_file():
        raise RuntimeError("native CA fixture generation failed: " + res.stderr[-400:])
    return key, cert


class HttpsServer:
    def __init__(self, family: int, address: str, ctx: ssl.SSLContext):
        self.errors: list[str] = []
        self.stop = threading.Event()
        self.listener = socket.socket(family, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            self.listener.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.listener.bind((address, 443))
        self.listener.listen(16)
        self.listener.settimeout(0.3)
        self.ctx = ctx
        self.requests = 0
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                accepted, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                accepted.settimeout(3)
                with self.ctx.wrap_socket(accepted, server_side=True) as conn:
                    data = conn.recv(8192)
                    if b"GET /" not in data:
                        raise RuntimeError("non-HTTP request received")
                    self.requests += 1
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK")
            except ssl.SSLError:
                # Expected for the deliberate wrong-CA negative scenario.
                accepted.close()
            except (OSError, RuntimeError) as exc:
                self.errors.append(str(exc))
                accepted.close()

    def close(self):
        self.stop.set()
        self.listener.close()
        self.thread.join(timeout=2)


def create_job(state, epoch, home: Path, name: str, target: str, ipv6: str,
               ipv4: str | None, enabled: str) -> tuple[str, Path, object]:
    job_id = "job." + name
    job = home / "jobs" / job_id
    job.mkdir(parents=True)
    job.chmod(0o700)
    state.initialize(job_id, str(job / "status.json"), str(job / "events.ndjson"),
                     target, "standard", "ru", enabled)
    (job / "endpoints.txt").write_text(target + "\n", encoding="utf-8")
    state.set_target(job_id, str(job / "status.json"), target,
                     "domain", str(job / "endpoints.txt"))
    data = {"endpoint": target, "dns_aaaa": {"classification": "pass", "answers": [ipv6]}}
    if ipv4:
        data["dns_a"] = {"classification": "pass", "answers": [ipv4]}
    search = epoch.create(job, target, "domain", [target], [data])
    return job_id, job, search


def empty(kernel):
    if kernel.owned_rules():
        raise RuntimeError("Strategy Lab left owned IPFW rules")
    result = shell("/sbin/ipfw", "-q", "list")
    if result.returncode or not kernel.table.safe_default_rules(result.stdout):
        raise RuntimeError("native firewall default-only state not restored")


def test_1_aaaa_stage85(state, epoch, result, home: Path, kernel, servers):
    job_id, job, search = create_job(
        state, epoch, home, "AAAATest", "aaaa.lab.test", "::1", None, "1")
    (job / "stability.json").write_text(json.dumps({
        "search_epoch_id": search.epoch_id,
        "candidates": [{
            "id": "liveAAAA", "family": "pktmod",
            "strategy": STRATEGY, "stable": True,
            "search_epoch_id": search.epoch_id,
            "endpoints": [{
                "endpoint": "aaaa.lab.test", "selected_ip": "::1",
                "remote_ip": "::1", "status": "PASS",
            }],
        }],
    }) + "\n", encoding="utf-8")
    shortlist = result.build_shortlist(job_id)
    if shortlist.get("count") != 1:
        raise RuntimeError("real AAAA Stage85 did not publish one verified profile")
    item = shortlist["items"][0]
    replay = item["profile_replay"]
    if not replay["verified"] or replay["pass_count"] != 3 or replay["attempt_count"] != 3:
        raise RuntimeError("real AAAA Stage85 final replay not 3/3")
    for row in replay["results"]:
        endpoints = row.get("endpoints", [])
        if (len(endpoints) != 1 or row.get("runner_status") != 0
                or row.get("search_epoch_id") != search.epoch_id
                or not row.get("profile_exact")
                or endpoints[0].get("selected_ip") != "::1"
                or endpoints[0].get("remote_ip") != "::1"
                or endpoints[0].get("status") != "PASS"
                or endpoints[0].get("firewall", {}).get("intercepted") is not True
                or endpoints[0].get("reachability", {}).get("tls_verified") is not True
                or endpoints[0].get("reachability", {}).get("ssl_verify_result") != 0):
            raise RuntimeError("real Stage85 AAAA selected IP/CA/IPFW witness invalid: "
                               + str(row)[:1400])
    if servers[6].requests < 3:
        raise RuntimeError("real IPv6 HTTPS server did not receive all three replays")
    empty(kernel)
    print(MARK + "_1=PASS: AAAA-only real Stage85 3/3 verified TLS and IPFW")


def test_2_family_gate(state, epoch, candidate, probe, home, kernel, servers):
    class Stub:
        ok = True
        duration_ms = 1
        def evidence(self):
            return {"native_gate": True}

    for enabled, expected in (("0", ["ipv4"]), ("1", ["ipv4", "ipv6"])):
        temp = home / ("network" + enabled)
        temp.mkdir()
        (temp / "ipv6-enabled").write_text(enabled + "\n")
        families = []
        def curl(_host, *, scheme, family):
            families.append(family)
            return Stub()
        with (patch.object(probe.request, "binary", return_value="/bin/true"),
              patch.object(probe.request, "ipv6_default_route",
                           return_value=(True, Stub())),
              patch.object(probe.request, "curl_request", side_effect=curl),
              patch.object(probe.request, "quic_ipv4_request", return_value=Stub()),
              patch.object(probe.request, "combined_log", return_value=""),
              patch.object(probe.telemetry, "record")):
            if probe._network(temp, temp / "network.json") != 0:
                raise RuntimeError("actual Stage30 family gate returned failure")
        if families != expected:
            raise RuntimeError("IPv6 checkbox Stage30 did not gate probes: " + str(families))
    job_id, job, search = create_job(
        state, epoch, home, "DualTest", "dual.lab.test", "::1", "127.0.0.1", "1")
    strategy = home / "dual-strategy.args"
    output = home / "dual-candidate.json"
    strategy.write_text(STRATEGY, encoding="utf-8")
    rc = candidate.run_candidate(job_id, str(job / "endpoints.txt"), str(output),
                                 "liveDual", "pktmod", str(strategy), "1")
    if rc != 0 or not output.is_file():
        raise RuntimeError("real dual-family candidate did not produce evidence")
    proof = json.loads(output.read_text(encoding="utf-8"))
    rows = proof.get("endpoints", [])
    if (proof.get("all_pass") is not True
            or proof.get("search_epoch_id") != search.epoch_id
            or len(rows) != 2
            or [row.get("selected_ip") for row in rows] != ["127.0.0.1", "::1"]
            or any(row.get("status") != "PASS"
                   or row.get("firewall", {}).get("intercepted") is not True
                   or row.get("reachability", {}).get("tls_verified") is not True
                   for row in rows)):
        raise RuntimeError("native A+AAAA candidate family proof invalid: " + str(proof)[:1700])
    if servers[4].requests < 1 or servers[6].requests < 4:
        raise RuntimeError("real dual-family TLS servers did not receive both pinned requests")
    empty(kernel)
    print(MARK + "_2=PASS: native IPv6 OFF/ON Stage30 and real A+AAAA TLS candidate")


def test_3_fault_cleanup(state, epoch, candidate, home: Path, kernel, wrong_cert: Path):
    job_id, job, _ = create_job(
        state, epoch, home, "FaultTest", "aaaa.lab.test", "::1", None, "1")
    strategy = home / "bad-ca-strategy.args"
    output = home / "bad-ca-result.json"
    strategy.write_text(STRATEGY, encoding="utf-8")
    ca = os.environ.get("CURL_CA_BUNDLE")
    os.environ["CURL_CA_BUNDLE"] = str(wrong_cert)
    try:
        rc = candidate.run_candidate(job_id, str(job / "endpoints.txt"),
                                     str(output), "liveFault", "pktmod",
                                     str(strategy), "1")
    finally:
        if ca is None:
            os.environ.pop("CURL_CA_BUNDLE", None)
        else:
            os.environ["CURL_CA_BUNDLE"] = ca
    if rc != 0 or not output.is_file():
        raise RuntimeError("native wrong-CA candidate did not produce fail-closed result")
    proof = json.loads(output.read_text(encoding="utf-8"))
    rows = proof.get("endpoints", [])
    if (proof.get("all_pass") is not False
            or len(rows) != 1
            or rows[0].get("status") != "FAIL"
            or rows[0].get("reachability", {}).get("tls_verified") is True):
        raise RuntimeError("wrong-CA TLS result was accidentally accepted: " + str(proof)[:1500])
    if (job / "candidate-runtime" / "dvtws2.pid").exists():
        raise RuntimeError("failed TLS left candidate PID file")
    empty(kernel)
    print(MARK + "_3=PASS: real untrusted TLS fails closed; no owned process/IPFW remains")


def main():
    if len(sys.argv) != 2:
        raise RuntimeError("usage: script.py /pinned/upstream/dvtws2")
    if (platform.system() != "FreeBSD" or os.geteuid() != 0
            or os.environ.get("ZAPRET2_ISOLATED_FREEBSD_VM_EXCLUDE_WIRE_TEST") != "1"
            or os.environ.get("ZAPRET2_ISOLATED_FREEBSD_VM_TABLE_TEST") != "1"
            or os.environ.get("ZAPRET2_ISOLATED_FREEBSD_VM_THREE_ACCEPTANCE") != "1"):
        raise RuntimeError("three-scenario test requires explicit disposable FreeBSD15 root")
    guard = load("three_native_guard", SCRIPTS / "test-freebsd15-native-engine-exclude.py")
    _adapter, table = guard.guest_gate()
    kernel = load("three_native_lab", SCRIPTS / "test-freebsd15-native-strategy-lab-engine.py")
    kernel.table = table
    engine = Path(sys.argv[1]).resolve()
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise RuntimeError("pinned dvtws2 binary missing")
    if kernel.owned_rules():
        raise RuntimeError("foreign Strategy Lab rule owner present")
    if not Path("/usr/local/bin/curl").is_file() or not Path("/usr/bin/openssl").is_file():
        raise RuntimeError("native HTTPS prerequisites missing")
    upstream = engine.parent.parent
    with tempfile.TemporaryDirectory(prefix="stage6-three-real-") as temp:
        home = Path(temp)
        (home / "jobs").mkdir()
        for directory in (home, home / "jobs", upstream, upstream / "lua"):
            directory.chmod(0o755)
        private_key, trusted = setup_cert(home, "trusted")
        _, untrusted = setup_cert(home, "other-ca")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(trusted), str(private_key))
        env = os.environ.copy()
        env.update({
            "SCRIPT_DIR": str(BACKEND),
            "STRATEGY_LAB_RUN_DIR": str(home),
            "STRATEGY_LAB_JOBS_DIR": str(home / "jobs"),
            "STRATEGY_LAB_WAN_DEVICE": "lo0",
            "STRATEGY_LAB_DVTWS_BIN": str(engine),
            "STRATEGY_LAB_DAEMON_BIN": "/usr/sbin/daemon",
            "STRATEGY_LAB_PS_BIN": "/bin/ps",
            "STRATEGY_LAB_LUA_DIR": str(upstream / "lua"),
            "STRATEGY_LAB_RULE_BASE": "19100",
            "STRATEGY_LAB_RULE_MAX": "19131",
            "STRATEGY_LAB_DIVERT_PORT": "9989",
            "STRATEGY_LAB_RUNTIME_READY_POLL": "0.2",
            "STRATEGY_LAB_RUNTIME_START_TIMEOUT": "8",
            "STRATEGY_LAB_RUNTIME_STOP_TIMEOUT": "4",
            "STRATEGY_LAB_CURL_BIN": "/usr/local/bin/curl",
            "CURL_CA_BUNDLE": str(trusted),
            "NO_PROXY": "*", "no_proxy": "*",
            "HOME": str(home),
        })
        original = os.environ.copy()
        servers = {}
        try:
            servers = {
                4: HttpsServer(socket.AF_INET, "127.0.0.1", ctx),
                6: HttpsServer(socket.AF_INET6, "::1", ctx),
            }
            os.environ.update(env)
            sys.path.insert(0, str(BACKEND))
            from strategy_lab_py import candidate, endpoint_epoch, result, state, probe
            test_1_aaaa_stage85(state, endpoint_epoch, result, home, kernel, servers)
            test_2_family_gate(state, endpoint_epoch, candidate, probe, home, kernel, servers)
            test_3_fault_cleanup(state, endpoint_epoch, candidate, home, kernel, untrusted)
        finally:
            for server in servers.values():
                server.close()
            os.environ.clear()
            os.environ.update(original)
            for number in range(19100, 19132):
                if number in kernel.owned_rules():
                    shell("/sbin/ipfw", "-q", "delete", str(number))
            empty(kernel)
    print(MARK + "=PASS: " + PASS_TEXT)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(MARK + "=FAIL: " + str(exc), file=sys.stderr)
        sys.exit(1)
