"""Python-owned finite Strategy Lab request execution and probe parsing."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

EX_OK = 0
EX_PREREQUISITE = 2
EX_USAGE = 64
EX_SOFTWARE = 70

DEFAULT_BINARIES = {
    "curl": "/usr/local/bin/curl",
    "drill": "/usr/bin/drill",
    "openssl": "/usr/bin/openssl",
    "netstat": "/usr/bin/netstat",
    "nc": "/usr/bin/nc",
}
BINARY_ENV = {
    "curl": "STRATEGY_LAB_CURL_BIN",
    "drill": "STRATEGY_LAB_DRILL_BIN",
    "openssl": "STRATEGY_LAB_OPENSSL_BIN",
    "netstat": "STRATEGY_LAB_NETSTAT_BIN",
    "nc": "STRATEGY_LAB_NC_BIN",
}
SECTION_RE = re.compile(r"^;;\s+([A-Z]+)\s+SECTION:\s*$")
CURL_EXIT_RE = re.compile(r"(?:^|\s)exit=(\d+)(?:\s|$)", re.MULTILINE)


class ProbeError(RuntimeError):
    pass


class UsageError(ProbeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    termination: str
    signal: int | None
    duration_ms: int

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.returncode == 0

    def evidence(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DnsResult:
    classification: str
    answers: list[str]
    execution: CommandResult

    @property
    def ok(self) -> bool:
        return self.classification == "pass"

    def evidence(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "answers": self.answers,
            "execution": self.execution.evidence(),
        }


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _binary(name: str) -> str:
    value = os.environ.get(BINARY_ENV[name], DEFAULT_BINARIES[name])
    if not os.path.isfile(value) or not os.access(value, os.X_OK):
        raise ProbeError(f"required Strategy Lab executable is unavailable: {value}")
    return value


def run_command(
    command: Sequence[str],
    *,
    timeout: float,
    stdin_devnull: bool = False,
) -> CommandResult:
    if timeout <= 0:
        raise UsageError("Strategy Lab subprocess timeout must be positive")
    argv = [str(item) for item in command]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL if stdin_devnull else None,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = max(0, round((time.monotonic() - started) * 1000))
        return CommandResult(
            command=argv,
            returncode=None,
            stdout=_text(exc.stdout),
            stderr=_text(exc.stderr),
            timed_out=True,
            termination="timeout",
            signal=None,
            duration_ms=duration,
        )
    except OSError as exc:
        raise ProbeError(f"Strategy Lab subprocess could not start: {argv[0]}: {exc}") from exc

    duration = max(0, round((time.monotonic() - started) * 1000))
    returncode = completed.returncode
    signal_number = -returncode if returncode < 0 else None
    return CommandResult(
        command=argv,
        returncode=returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
        termination="signal" if signal_number is not None else "completed",
        signal=signal_number,
        duration_ms=duration,
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _combined_log(result: CommandResult) -> str:
    chunks = []
    if result.stdout:
        chunks.append(result.stdout)
    if result.stderr:
        chunks.append(result.stderr)
    text = "".join(chunks)
    if result.timed_out:
        text += "Strategy Lab subprocess timeout\n"
    return text


def _tail20(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-20:]) + "\n"


def parse_drill_answers(output: str, record_type: str) -> list[str]:
    qtype = record_type.upper()
    if qtype not in {"A", "AAAA"}:
        raise UsageError("unsupported DNS record type")
    in_answer = False
    answers: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        section = SECTION_RE.match(line)
        if section:
            in_answer = section.group(1) == "ANSWER"
            continue
        if not in_answer or not line or line.startswith(";"):
            continue
        fields = line.split()
        try:
            in_index = fields.index("IN")
        except ValueError:
            continue
        if in_index + 2 >= len(fields) or fields[in_index + 1].upper() != qtype:
            continue
        candidate = fields[in_index + 2].rstrip(".")
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if qtype == "A" and address.version != 4:
            continue
        if qtype == "AAAA" and address.version != 6:
            continue
        value = str(address)
        if value not in answers:
            answers.append(value)
    return answers


def _classify_dns(result: CommandResult, record_type: str) -> DnsResult:
    if result.timed_out:
        return DnsResult("timeout", [], result)
    if result.returncode != 0:
        return DnsResult("command_error", [], result)
    answers = parse_drill_answers(result.stdout, record_type)
    if not answers:
        return DnsResult("parser_rejected", [], result)
    return DnsResult("pass", answers, result)


def dns_request(host: str, record_type: str) -> DnsResult:
    return _classify_dns(run_command([_binary("drill"), host, record_type], timeout=2), record_type)


def _curl_tls13(host: str, family: str) -> CommandResult:
    if family not in {"ipv4", "ipv6"}:
        raise UsageError("invalid TLS address family")
    command = [
        _binary("curl"),
        f"--{family}",
        "--proto", "=https",
        "--tlsv1.3",
        "--tls-max", "1.3",
        "--http1.1",
        "--request", "GET",
        "--location",
        "--max-redirs", "2",
        "--connect-timeout", "2",
        "--max-time", "3",
        "--retry", "0",
        "--silent",
        "--show-error",
        "--header", "Connection: close",
        "--range", "0-65535",
        "--output", "/dev/null",
        "--write-out", "exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\\n",
        f"https://{host}/",
    ]
    return run_command(command, timeout=4)


def _curl_exit(result: CommandResult) -> int:
    match = None
    for match in CURL_EXIT_RE.finditer(result.stdout):
        pass
    if match is not None:
        return int(match.group(1), 10)
    if result.returncode is not None and result.returncode >= 0:
        return result.returncode
    return 1


def _ipv6_route() -> tuple[bool, CommandResult]:
    result = run_command([_binary("netstat"), "-rn", "-f", "inet6"], timeout=2)
    available = result.ok and any(
        line.split()[:1] == ["default"] for line in result.stdout.splitlines() if line.strip()
    )
    return available, result


def _quic_control() -> CommandResult:
    command = [
        _binary("openssl"), "s_client", "-4", "-quic",
        "-connect", "yandex.ru:443", "-servername", "yandex.ru",
        "-alpn", "h3", "-verify_hostname", "yandex.ru",
        "-verify_return_error", "-brief", "-no-interactive",
    ]
    return run_command(command, timeout=2, stdin_devnull=True)


def _tcp_request(host: str, port: int) -> CommandResult:
    return run_command([_binary("nc"), "-z", "-w", "2", host, str(port)], timeout=3)


def _network(workdir: Path, result_path: Path) -> int:
    for name in ("curl", "netstat", "openssl"):
        _binary(name)
    route_available, route_result = _ipv6_route()
    with ThreadPoolExecutor(max_workers=3) as pool:
        ipv4_future = pool.submit(_curl_tls13, "yandex.ru", "ipv4")
        ipv6_future = pool.submit(_curl_tls13, "one.one.one.one", "ipv6") if route_available else None
        quic_future = pool.submit(_quic_control)
        ipv4_result = ipv4_future.result()
        ipv6_result = ipv6_future.result() if ipv6_future is not None else None
        quic_result = quic_future.result()

    _write_text(workdir / "control-ipv4.log", _combined_log(ipv4_result))
    _write_text(workdir / "control-ipv6.log", _combined_log(ipv6_result) if ipv6_result is not None else "")
    _write_text(workdir / "control-quic-ipv4.log", _combined_log(quic_result))

    ipv4 = "available" if ipv4_result.ok else "unavailable"
    ipv6 = "available" if route_available and ipv6_result is not None and ipv6_result.ok else "unavailable"
    quic_ipv4 = "available" if quic_result.ok else "closed"
    quic_ipv6 = "eligible" if quic_ipv4 == "available" and ipv6 == "available" else "skipped"
    _write_json(result_path, {"ipv4": ipv4, "ipv6": ipv6, "quic_ipv4": quic_ipv4, "quic_ipv6": quic_ipv6})
    _write_json(workdir / "network-evidence.json", {
        "ipv4": ipv4_result.evidence(),
        "ipv6_route": {"available": route_available, "execution": route_result.evidence()},
        "ipv6": ipv6_result.evidence() if ipv6_result is not None else None,
        "quic_ipv4": quic_result.evidence(),
    })
    return EX_OK if ipv4 == "available" else EX_PREREQUISITE


def _endpoint_public_dns_failure(endpoint: str, log_text: str) -> dict[str, Any]:
    return {"endpoint": endpoint, "status": "FAIL", "exit_code": 1, "transport": "dns-a", "detail": _tail20(log_text)}


def _endpoint_public_domain(endpoint: str, ipv4: CommandResult, ipv6: CommandResult | None) -> dict[str, Any]:
    ipv4_status = "PASS" if ipv4.ok else "FAIL"
    ipv6_status = "SKIPPED" if ipv6 is None else ("PASS" if ipv6.ok else "FAIL")
    ipv4_log = _combined_log(ipv4)
    ipv6_log = _combined_log(ipv6) if ipv6 is not None else ""
    return {
        "endpoint": endpoint,
        "status": ipv4_status,
        "exit_code": _curl_exit(ipv4),
        "transport": "tls13-ipv4",
        "detail": _tail20(ipv4_log),
        "ipv4": {"status": ipv4_status, "exit_code": _curl_exit(ipv4), "detail": _tail20(ipv4_log)},
        "ipv6": {"status": ipv6_status, "exit_code": None if ipv6 is None else _curl_exit(ipv6), "detail": _tail20(ipv6_log)},
    }


def _endpoint_public_ip(endpoint: str, result: CommandResult) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "status": "PASS" if result.ok else "FAIL",
        "exit_code": result.returncode if result.returncode is not None and result.returncode >= 0 else 1,
        "transport": "tcp-443",
        "detail": _tail20(_combined_log(result)),
    }


def _domain_endpoint(endpoint: str, index: int, workdir: Path, ipv6_enabled: bool) -> tuple[dict[str, Any], dict[str, Any], bool, bool]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        dns_a_future = pool.submit(dns_request, endpoint, "A")
        dns_aaaa_future = pool.submit(dns_request, endpoint, "AAAA") if ipv6_enabled else None
        tls4_future = pool.submit(_curl_tls13, endpoint, "ipv4")
        tls6_future = pool.submit(_curl_tls13, endpoint, "ipv6") if ipv6_enabled else None
        dns_a = dns_a_future.result()
        dns_aaaa = dns_aaaa_future.result() if dns_aaaa_future is not None else None
        tls4 = tls4_future.result()
        tls6 = tls6_future.result() if tls6_future is not None else None

    dns_a_log = _combined_log(dns_a.execution)
    _write_text(workdir / f"endpoint-{index}.a.log", dns_a_log)
    if dns_aaaa is not None:
        _write_text(workdir / f"endpoint-{index}.aaaa.log", _combined_log(dns_aaaa.execution))
    _write_text(workdir / f"endpoint-{index}.tls-ipv4.log", _combined_log(tls4))
    if tls6 is not None:
        _write_text(workdir / f"endpoint-{index}.tls-ipv6.log", _combined_log(tls6))

    evidence = {
        "endpoint": endpoint,
        "dns_a": dns_a.evidence(),
        "dns_aaaa": dns_aaaa.evidence() if dns_aaaa is not None else None,
        "tls_ipv4": tls4.evidence(),
        "tls_ipv6": tls6.evidence() if tls6 is not None else None,
    }
    public = _endpoint_public_dns_failure(endpoint, dns_a_log) if not dns_a.ok else _endpoint_public_domain(endpoint, tls4, tls6)
    return public, evidence, not dns_a.ok, dns_aaaa is not None and not dns_aaaa.ok


def _ip_endpoint(endpoint: str, index: int, workdir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    result = _tcp_request(endpoint, 443)
    _write_text(workdir / f"endpoint-{index}.tcp.log", _combined_log(result))
    return _endpoint_public_ip(endpoint, result), {"endpoint": endpoint, "tcp_443": result.evidence()}


def _read_endpoints(path: Path) -> list[str]:
    try:
        endpoints = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as exc:
        raise ProbeError(f"Strategy Lab endpoints are unreadable: {path}") from exc
    if not endpoints:
        raise ProbeError("Strategy Lab endpoints are empty")
    return endpoints


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeError(f"Strategy Lab JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ProbeError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _baseline(target: str, target_type: str, endpoints_path: Path, network_path: Path, workdir: Path, result_path: Path) -> int:
    if target_type not in {"domain", "ip"}:
        raise UsageError("invalid Strategy Lab target type")
    endpoints = _read_endpoints(endpoints_path)
    network = _load_json(network_path)
    ipv6_enabled = network.get("ipv6") == "available"
    results_dir = workdir / "baseline-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for old in results_dir.glob("*.json"):
        old.unlink()

    public_results: list[dict[str, Any]] = []
    evidence_results: list[dict[str, Any]] = []
    dns_a_status = "SKIPPED"
    dns_aaaa_status = "SKIPPED"
    dns_failed = False

    if target_type == "domain":
        _binary("drill")
        _binary("curl")
        dns_a_status = "PASS"
        dns_aaaa_status = "PASS" if ipv6_enabled else "SKIPPED"
        with ThreadPoolExecutor(max_workers=min(4, len(endpoints))) as pool:
            futures = [pool.submit(_domain_endpoint, endpoint, index, workdir, ipv6_enabled) for index, endpoint in enumerate(endpoints, 1)]
            endpoint_values = [future.result() for future in futures]
        for index, (public, evidence, a_failed, aaaa_failed) in enumerate(endpoint_values, 1):
            public_results.append(public)
            evidence_results.append(evidence)
            _write_json(results_dir / f"{index}.json", public)
            if a_failed:
                dns_a_status = "FAIL"
                dns_failed = True
            if aaaa_failed and dns_aaaa_status == "PASS":
                dns_aaaa_status = "PARTIAL"
    else:
        _binary("nc")
        with ThreadPoolExecutor(max_workers=min(4, len(endpoints))) as pool:
            futures = [pool.submit(_ip_endpoint, endpoint, index, workdir) for index, endpoint in enumerate(endpoints, 1)]
            endpoint_values = [future.result() for future in futures]
        for index, (public, evidence) in enumerate(endpoint_values, 1):
            public_results.append(public)
            evidence_results.append(evidence)
            _write_json(results_dir / f"{index}.json", public)

    _write_json(workdir / "baseline-endpoints.json", public_results)
    _write_json(result_path, {
        "target": target,
        "target_type": target_type,
        "dns_a": dns_a_status,
        "dns_aaaa": dns_aaaa_status,
        "endpoints": public_results,
        "all_accessible": bool(public_results) and all(item.get("status") == "PASS" for item in public_results),
    })
    _write_json(workdir / "baseline-evidence.json", {"target": target, "target_type": target_type, "endpoints": evidence_results})
    return EX_PREREQUISITE if dns_failed else EX_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise UsageError("usage: probe network RESULT WORKDIR | probe baseline TARGET TYPE ENDPOINTS NETWORK WORKDIR RESULT")
    if args[0] == "network":
        if len(args) != 3:
            raise UsageError("probe network requires RESULT WORKDIR")
        return _network(Path(args[2]), Path(args[1]))
    if args[0] == "baseline":
        if len(args) != 7:
            raise UsageError("probe baseline requires TARGET TYPE ENDPOINTS NETWORK WORKDIR RESULT")
        return _baseline(args[1], args[2], Path(args[3]), Path(args[4]), Path(args[5]), Path(args[6]))
    raise UsageError(f"unsupported Strategy Lab probe operation: {args[0]}")
