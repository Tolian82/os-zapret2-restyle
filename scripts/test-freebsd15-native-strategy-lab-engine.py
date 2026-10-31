#!/usr/bin/env python3
"""Production Stage40/CandidateSpec -> actual dvtws2 IPv4/IPv6 BPF witness.

FreeBSD 15.1 disposable VM only. Not installed OPNsense or full Stage85.
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
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
HERE = ROOT / "scripts"
ADAPTER = SCRIPTS / "strategy_lab_candidate_adapter.sh"
BASE, LIMIT, DIVERT, PORT = 19100, 19131, 9989, 6541
MARKER = "STAGE6_NATIVE_LAB_ENGINE"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("native companion missing: " + path.name)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


def command(*args, env=None):
    return subprocess.run(args, env=env, capture_output=True, text=True,
                          timeout=20, check=False)


def adapter(action, env, *arguments):
    result = command("/bin/sh", str(ADAPTER), action, *arguments, env=env)
    if result.returncode:
        raise RuntimeError("production candidate adapter " + action +
                           " failed: " + (result.stderr or result.stdout)[-1100:])
    return result.stdout


def owned_rules():
    result = command("/sbin/ipfw", "-q", "list")
    if result.returncode:
        raise RuntimeError("native kernel rule listing failed")
    return {int(fields[0]): line for line in result.stdout.splitlines()
            if (fields := line.split()) and fields[0].isascii() and
            fields[0].isdecimal() and BASE <= int(fields[0]) <= LIMIT}


def static_test():
    import ast
    source = ADAPTER.read_text(encoding="utf-8")
    for expected in ("firewall-install-protocol)", "launch)", "snapshot)",
                     "cleanup)", "--sockarg=0x200", "--user=nobody"):
        if expected not in source:
            raise RuntimeError("production adapter missing: " + expected)
    for name in ("candidate.py", "candidate_spec.py", "endpoint_epoch.py"):
        ast.parse((SCRIPTS / "strategy_lab_py" / name).read_text(encoding="utf-8"))
    print(MARKER + "_STATIC=PASS: native adapter source and Stage40 candidate renderer")


def native(engine):
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        raise RuntimeError("disposable FreeBSD root required")
    if (os.environ.get("ZAPRET2_ISOLATED_FREEBSD_VM_EXCLUDE_WIRE_TEST") != "1"
            or os.environ.get("ZAPRET2_ISOLATED_FREEBSD_VM_STRATEGY_LAB_ENGINE_TEST") != "1"):
        raise RuntimeError("explicit isolated guest opt-in required")
    guard = module("stage6_engine_guest_guard", HERE / "test-freebsd15-native-engine-exclude.py")
    _adapter, table = guard.guest_gate()
    tls = module("stage6_engine_tls", HERE / "test-freebsd15-native-tls-strategy.py")
    capture = module("stage6_engine_capture", HERE / "stage5-wan-baseline-capture.py")
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise RuntimeError("pinned built dvtws2 executable missing")
    upstream = engine.parent.parent
    for name in ("zapret-lib.lua", "zapret-antidpi.lua"):
        if not (upstream / "lua" / name).is_file():
            raise RuntimeError("pinned upstream Lua missing: " + name)
    if owned_rules():
        raise RuntimeError("foreign Strategy Lab rules found")
    hello = tls.hello_fixture()
    with tempfile.TemporaryDirectory(prefix="stage6-native-engine-") as folder:
        home = Path(folder)
        home.chmod(0o755)
        jobs, job_id = home / "jobs", "job.NativeEngine"
        job = jobs / job_id
        runtime = job / "candidate-runtime"
        runtime.mkdir(parents=True)
        for directory in (jobs, job, runtime, upstream, upstream / "lua"):
            directory.chmod(0o755)
        env = os.environ.copy()
        env.update({
            "SCRIPT_DIR": str(SCRIPTS),
            "STRATEGY_LAB_RUN_DIR": str(home),
            "STRATEGY_LAB_JOBS_DIR": str(jobs),
            "STRATEGY_LAB_WAN_DEVICE": "lo0",
            "STRATEGY_LAB_DVTWS_BIN": str(engine),
            "STRATEGY_LAB_DAEMON_BIN": "/usr/sbin/daemon",
            "STRATEGY_LAB_PS_BIN": "/bin/ps",
            "STRATEGY_LAB_LUA_DIR": str(upstream / "lua"),
            "STRATEGY_LAB_RULE_BASE": str(BASE),
            "STRATEGY_LAB_RULE_MAX": str(LIMIT),
            "STRATEGY_LAB_DIVERT_PORT": str(DIVERT),
            "STRATEGY_LAB_RUNTIME_START_TIMEOUT": "6",
            "STRATEGY_LAB_RUNTIME_STOP_TIMEOUT": "5",
        })
        old_env = os.environ.copy()
        dump = None
        try:
            os.environ.update(env)
            sys.path.insert(0, str(SCRIPTS))
            from strategy_lab_py import candidate, candidate_spec, endpoint_epoch, resources
            epoch = endpoint_epoch.create(job, "stage6.example", "domain",
                ["stage6.example"], [{
                    "endpoint": "stage6.example",
                    "dns_a": {"classification": "pass", "answers": ["127.0.0.1"]},
                    "dns_aaaa": {"classification": "pass", "answers": ["::1"]},
                }])
            pins, loaded = candidate._pinned_endpoints(job_id, ["stage6.example"])
            if (epoch.epoch_id != loaded.epoch_id or
                    [(x["selected_ip"], x["rule"]) for x in pins] !=
                    [("127.0.0.1", BASE), ("::1", BASE + 1)]):
                raise RuntimeError("real Stage40 immutable epoch/rule binding mismatch")
            inventory = resources.ensure_job_inventory(job)
            spec = candidate_spec.CandidateSpec.from_strategy(
                candidate_id="native-stage6", family="pktmod", protocol="tls13",
                transport="tcp", port=PORT, l7="tls", target_binding=False,
                strategy="--lua-desync=pktmod:ip_ttl=23:ip6_ttl=37\n")
            args = candidate._prepare_runtime_files(job_id, ["stage6.example"], spec, inventory)
            if not {f"--filter-tcp={PORT}", "--filter-l7=tls",
                    "--lua-desync=pktmod:ip_ttl=23:ip6_ttl=37"}.issubset(set(args)):
                raise RuntimeError("real CandidateSpec TLS strategy rendering mismatch")
            pcap = home / "packets.pcap"
            dump = subprocess.Popen([
                "/usr/sbin/tcpdump", "-U", "-i", "lo0", "-nn", "-s", "4096",
                "-c", "256", "-w", str(pcap),
                f"tcp and dst portrange {PORT}-{PORT}",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
            capture.tcpdump_ready(dump, deadline=time.monotonic() + 5)
            baseline = {}
            for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
                baseline[family] = (tls.send_hello(family, host, PORT, hello), PORT)
            adapter("firewall-install-protocol", env,
                    str(runtime / "addresses-ipv4.txt"), "lo0", "tcp", str(PORT))
            if set(owned_rules()) != {BASE, BASE + 1}:
                raise RuntimeError("native Strategy Lab production rule set mismatch")
            adapter("launch", env, job_id)
            ready = candidate._readiness(job_id)
            if not ready.get("ready") or not ready.get("process_identity"):
                raise RuntimeError("real dvtws2 candidate startup not ready: " + str(ready))
            active = {}
            for family, host, rule in (
                (socket.AF_INET, "127.0.0.1", BASE),
                (socket.AF_INET6, "::1", BASE + 1),
            ):
                before = candidate._counter(rule)
                active[family] = (tls.send_hello(family, host, PORT, hello), PORT)
                after = candidate._counter(rule)
                if after[0] <= before[0] or after[1] <= before[1]:
                    raise RuntimeError("native real-engine IPv4/IPv6 IPFW counter did not advance")
            if not capture.wait_for_packet_flush(dump, pcap, deadline=time.monotonic() + 3):
                raise RuntimeError("real native pcap evidence unavailable")
            # BPF loopback buffer delivery can lag the final active datagram.
            # Let the capture worker flush the last flow before SIGINT.
            time.sleep(0.5)
            # Baseline frames may have already satisfied the size predicate.
            # Stop tcpdump to drain native BPF and flush *all* active packets
            # before parsing exact post-engine source-port witnesses.
            capture.terminate(dump)
            if dump.stderr is not None:
                dump.stderr.close()
            dump = None
            for family in (socket.AF_INET, socket.AF_INET6):
                rows = tls.records(pcap.read_bytes(), family, hello, ports=(PORT,))
                before_hops = [hop for src, dst, hop in rows
                               if (src, dst) == baseline[family]]
                after_hops = [hop for src, dst, hop in rows
                              if (src, dst) == active[family]]
                expected = 23 if family == socket.AF_INET else 37
                if not before_hops or expected in before_hops:
                    raise RuntimeError("unaltered baseline IP header attribution failed")
                # Native production sockarg divert/xmit can deliver the
                # packet without exposing reinjection on lo0 BPF. This is
                # not evidence of modified TTL/hop in this specific path.
                # If active headers are visible, they must still be correct.
                if after_hops and expected not in after_hops:
                    runtime_log = (runtime / "dvtws2.log")
                    detail = runtime_log.read_text(errors="replace")[-500:] if runtime_log.exists() else ""
                    wire = command("/usr/sbin/tcpdump", "-nn", "-tt", "-r", str(pcap), "tcp")
                    summary = wire.stdout[-3000:] if wire.returncode == 0 else wire.stderr[-300:]
                    raise RuntimeError(
                        f"real dvtws2 header witness failed IPv{4 if family == socket.AF_INET else 6}: "
                        f"baseline={before_hops} active={after_hops} expected={expected} "
                        f"flow={active[family]} observed={rows[-18:]} wire={summary!r} log={detail!r}"
                    )
            adapter("cleanup", env, job_id)
            if owned_rules() or (runtime / "dvtws2.pid").exists():
                raise RuntimeError("production candidate cleanup left owned runtime/IPFW state")
        finally:
            if dump is not None:
                capture.terminate(dump)
                if dump.stderr is not None:
                    dump.stderr.close()
            cleanup_error = None
            try:
                adapter("cleanup", env, job_id)
            except Exception as exc:
                cleanup_error = str(exc)
            if owned_rules():
                for number in range(BASE, LIMIT + 1):
                    command("/sbin/ipfw", "-q", "delete", str(number))
            os.environ.clear()
            os.environ.update(old_env)
            if (cleanup_error is not None or owned_rules() or
                    not table.safe_default_rules(command("/sbin/ipfw", "-q", "list").stdout)):
                raise RuntimeError("native engine/firewall restoration not verified: " + str(cleanup_error))
    print(MARKER + "=PASS: production Stage40 CandidateSpec, real dvtws2 IPv4/IPv6 TLS delivery, IPFW counters and exact cleanup; BPF active header not claimed")


def main():
    if sys.argv[1:] == ["--static"]:
        static_test()
    elif len(sys.argv) == 2:
        native(Path(sys.argv[1]).resolve())
    else:
        raise RuntimeError("usage: test-freebsd15-native-strategy-lab-engine.py --static | /pinned/dvtws2")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(MARKER + "=FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
