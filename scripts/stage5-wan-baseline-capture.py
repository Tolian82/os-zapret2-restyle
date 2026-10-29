#!/usr/bin/env python3
"""One consent-gated, baseline-only WAN capture; NO Exclude/Config/IPFW changes.

Offline --check validates one generated plan. Live --execute requires a
separate, conspicuous opt-in and exact installed OPNsense 0.6.1_12.
Never infer WAN DPI/Exclude A07/A08 acceptance from a successful capture.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import argparse
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import select
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time

SCRIPT_DIR = Path(__file__).resolve().parent
PLAN_SCRIPT = SCRIPT_DIR / "stage5-wan-acquisition-plan.py"
BRIDGE_SCRIPT = SCRIPT_DIR / "stage5-installed-evidence.py"
OFFLINE_SCRIPT = SCRIPT_DIR / "stage5-wan-pcap-attribution.py"
OPT_IN = "ZAPRET2_ALLOW_ONE_BASELINE_WAN_CAPTURE"
TOKEN = "I_APPROVE_ONE_BASELINE_CAPTURE"
MAX_PLAN = 12000
MAX_CAPTURE_BYTES = 8 * 1024 * 1024
READY_TIMEOUT = 4.0
MAX_TOTAL_SECONDS = 18.0
MAX_CURL_SECONDS = 12.0
PCAP_MAGIC = (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4",
              b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")


class CaptureError(ValueError):
    pass


def module(name: str, file: Path):
    if not file.is_file():
        raise CaptureError("required trusted companion script absent: " + file.name)
    spec = importlib.util.spec_from_file_location(name, file)
    if spec is None or spec.loader is None:
        raise CaptureError("cannot load companion: " + file.name)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def safe_plan(path: Path) -> dict:
    try:
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > MAX_PLAN:
            raise CaptureError("unsafe or oversized plan")
        raw = path.read_bytes()
        if len(raw) > MAX_PLAN:
            raise CaptureError("oversized plan")
        doc = json.loads(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        raise CaptureError("invalid plan file") from exc
    if not isinstance(doc, dict):
        raise CaptureError("plan must be an object")
    identity = doc.get("analysis_manifest")
    if not isinstance(identity, dict):
        raise CaptureError("missing plan identity")
    endpoint = identity.get("baseline")
    if not isinstance(endpoint, dict):
        raise CaptureError("invalid baseline endpoint")
    generator = module("stage5_plan_companion", PLAN_SCRIPT)
    try:
        expected = generator.plan(
            identity["domain"], identity["remote_ip"], endpoint["source_ip"],
            endpoint["source_port"], identity["wan_interface"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CaptureError("untrusted plan identity") from exc
    if doc != expected:
        raise CaptureError("plan differs from current trusted generator; no commands allowed")
    return expected


def live_gate() -> None:
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        raise CaptureError("live operation requires FreeBSD root on installed OPNsense")
    if not Path("/conf/config.xml").is_file() or not Path("/usr/local/opnsense").is_dir():
        raise CaptureError("OPNsense installation not identified")
    if os.getenv(OPT_IN) != TOKEN:
        raise CaptureError("one-time baseline capture has not been explicitly authorized")


def checked(argv: list[str], *, timeout: float = 8.0) -> str:
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if p.returncode != 0 or len(p.stdout) > 32768:
        raise CaptureError("read-only preflight failed: " + Path(argv[0]).name)
    return p.stdout


def inspect(bridge) -> dict:
    out = io.StringIO()
    with redirect_stdout(out):
        if bridge.collect() != 0:
            raise CaptureError("native owner inspection refused capture")
    try:
        return bridge._parse_snapshot(out.getvalue().encode(), "single capture")
    except (ValueError, UnicodeError) as exc:
        raise CaptureError("native owner snapshot is not verified") from exc



# These are the *same two* native pidfiles attested by voice_live_inspect.py.
# A matching Config digest alone does not prove a continuous engine instance.
NATIVE_PID_FILES = (
    Path("/var/run/dvtws2.pid"),
    Path("/var/run/zapret2-supervisor-monitor.pid"),
)


def process_witness(*, pid_files=NATIVE_PID_FILES) -> tuple:
    """Read-only PID plus process start-time witness; never expose it in JSON."""
    result = []
    for path in pid_files:
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 1 <= info.st_size <= 24:
                raise CaptureError("untrusted native process pidfile: " + path.name)
            raw = path.read_text("ascii").strip()
        except (OSError, UnicodeError) as exc:
            raise CaptureError("unreadable native process pidfile: " + path.name) from exc
        if not re.fullmatch(r"[1-9][0-9]{0,9}", raw) or int(raw) <= 1:
            raise CaptureError("invalid native process pid: " + path.name)
        started = checked(["/bin/ps", "-p", raw, "-o", "lstart="], timeout=4).strip()
        if "\n" in started or not 8 <= len(started) <= 96:
            raise CaptureError("invalid native process start witness: " + path.name)
        result.append((path.name, int(raw), started))
    if len(result) != 2 or result[0][1] == result[1][1]:
        raise CaptureError("untrusted native engine/supervisor process identity")
    return tuple(result)


def preflight(plan: dict) -> None:
    manifest = plan["analysis_manifest"]
    wan = manifest["wan_interface"]
    source = ipaddress.ip_address(manifest["baseline"]["source_ip"])
    remote = ipaddress.ip_address(manifest["remote_ip"])
    address = str(source)
    interface = checked(["/sbin/ifconfig", wan])
    if source.version == 4:
        owned = re.search(r"(?m)^\s*inet\s+" + re.escape(address) + r"\s", interface)
    else:
        owned = re.search(r"(?m)^\s*inet6\s+" + re.escape(address) + r"(?:\s|%)", interface)
    if owned is None:
        raise CaptureError("source address is not configured on declared WAN")
    route = checked(["/sbin/route"] + (["-6"] if remote.version == 6 else []) +
                    ["-n", "get", str(remote)])
    found = re.search(r"(?m)^\s*interface:\s*([a-zA-Z0-9_.-]+)\s*$", route)
    if not found or found.group(1) != wan:
        raise CaptureError("target route is not on declared WAN")
    links = checked(["/usr/sbin/tcpdump", "-i", wan, "-L"])
    if not re.search(r"\bEN10MB\b", links):
        raise CaptureError("Ethernet DLT_EN10MB cannot be attested")
    # This proves availability at this instant, not exclusive lifetime
    # ownership of the local port during the future curl connection.
    try:
        with socket.socket(socket.AF_INET if source.version == 4 else socket.AF_INET6,
                           socket.SOCK_STREAM) as probe:
            if source.version == 6:
                probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            probe.bind((address, manifest["baseline"]["source_port"]))
    except OSError as exc:
        raise CaptureError("source port is not locally available") from exc


def terminate(proc, *, sig=signal.SIGINT) -> None:
    if proc is None or proc.poll() is not None:
        return
    # Only the freshly started process group is owned by this invocation.
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait(timeout=2)


def tcpdump_ready(proc, *, deadline: float) -> None:
    if proc.stderr is None:
        raise CaptureError("tcpdump readiness pipe missing")
    buf = b""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise CaptureError("tcpdump exited before capture became active")
        ready, _, _ = select.select([proc.stderr], [], [], min(.15, max(0, deadline-time.monotonic())))
        if ready:
            piece = os.read(proc.stderr.fileno(), 2048)
            buf = (buf + piece)[-4096:]
            if b"listening on " in buf.lower():
                return
            if not piece:
                raise CaptureError("tcpdump readiness stream closed")
    raise CaptureError("tcpdump did not confirm active capture before deadline")


def execute_one(plan: dict, *, popen=subprocess.Popen, now=time.monotonic,
                readiness=tcpdump_ready, owner_inspection=inspect,
                network_preflight=preflight, process_identity=process_witness,
                bridge=None, analyzer=None) -> dict:
    """One baseline capture only; dependency injection enables offline fake tests."""
    if bridge is None:
        bridge = module("stage5_bridge_companion", BRIDGE_SCRIPT)
    if analyzer is None:
        analyzer = module("stage5_pcap_companion", OFFLINE_SCRIPT)
    process_before = process_identity()
    before = owner_inspection(bridge)
    if process_identity() != process_before:
        raise CaptureError("native engine/supervisor changed during initial inspection")
    network_preflight(plan)
    first = plan["phases"]["baseline"]
    root = Path(tempfile.mkdtemp(prefix="zapret2-wan-one-", dir="/tmp"))
    root.chmod(0o700)
    capture = root / "baseline.pcap"
    tcpdump = None
    curl = None
    keep = False
    ended = False
    try:
        argv = list(first["capture_argv"])
        # Trusted generator is verified by safe_plan; no shell, no options
        # other than incremental unbuffered writing are allowed.
        argv[argv.index("-w") + 1] = str(capture)
        argv.insert(1, "-U")
        tcpdump = popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                        start_new_session=True)
        deadline = now() + min(MAX_TOTAL_SECONDS, first["capture_deadline_seconds"])
        readiness(tcpdump, deadline=min(deadline, now()+READY_TIMEOUT))
        if tcpdump.poll() is not None:
            raise CaptureError("capture process exited before controlled probe")
        curl = popen(first["probe_argv"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
        while curl.poll() is None:
            if now() >= deadline:
                raise CaptureError("hard capture/probe deadline exceeded")
            time.sleep(.05)
        ended = True
        if curl.returncode != 0:
            raise CaptureError("controlled HTTPS request did not complete successfully")
        terminate(tcpdump)
        tcpdump = None
        data = capture.read_bytes()
        if not 24 < len(data) <= MAX_CAPTURE_BYTES or data[:4] not in PCAP_MAGIC:
            raise CaptureError("no complete classic capture generated")
        if struct.unpack_from("<I" if data[:4] in (PCAP_MAGIC[0], PCAP_MAGIC[2]) else ">I",
                              data, 20)[0] != 1:
            raise CaptureError("capture is not Ethernet DLT_EN10MB")
        observed = analyzer.summarize(data, plan["analysis_manifest"], "baseline")
        if not observed["capture_correlated"]:
            raise CaptureError("capture did not contain unambiguous controlled outbound TCP payload")
        after = owner_inspection(bridge)
        bridge.compare(before, after)
        if process_identity() != process_before:
            raise CaptureError("native engine/supervisor restarted during baseline capture")
        keep = True
        return {
            "status": "BASELINE_CAPTURE_OBSERVED_ONLY",
            "local_pcap": str(capture),
            "capture_bytes": len(data),
            "family": observed["family"],
            "outgoing_packets": observed["outgoing_packets"],
            "payload_packets": observed["payload_packets"],
            "source_port_observed": observed["source_port"],
            "owner_state_consistent": True,
            "wan_origin_proven": False,
            "engine_strategy_modification_proven": False,
            "exclude_effect_proven": False,
            "installed_a07": "OPEN", "installed_a08": "OPEN",
            "note": "Raw capture is local, not uploaded. A single baseline five-tuple "
                    "was observed; no Exclude/GUI action or actual DPI modification was proven.",
        }
    finally:
        terminate(curl, sig=signal.SIGTERM)
        terminate(tcpdump)
        if not keep:
            shutil.rmtree(root, ignore_errors=True)


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--plan", type=Path, required=True)
    cli.add_argument("--check", action="store_true", help="offline plan validation only")
    cli.add_argument("--execute", action="store_true", help="one explicitly authorized baseline capture")
    args = cli.parse_args(argv)
    if args.check == args.execute:
        raise CaptureError("select exactly one of --check or --execute")
    plan = safe_plan(args.plan)
    if args.check:
        print(json.dumps({"status": "PLAN_VALIDATED_ONLY", "executed": False,
                          "installed_a07": "OPEN", "installed_a08": "OPEN"}, sort_keys=True))
        return 0
    live_gate()
    result = execute_one(plan)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CaptureError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print("WAN_BASELINE_CAPTURE=UNVERIFIED: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
