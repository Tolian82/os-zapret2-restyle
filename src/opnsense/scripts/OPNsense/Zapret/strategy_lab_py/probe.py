"""Python-owned Strategy Lab network precheck and clean-baseline probe orchestration."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Sequence

from . import request

EX_OK = 0
EX_PREREQUISITE = 2


class ProbeError(RuntimeError):
    pass


class UsageError(ProbeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    request.write_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeError(f"Strategy Lab JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ProbeError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _read_endpoints(path: Path) -> list[str]:
    try:
        endpoints = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as exc:
        raise ProbeError(f"Strategy Lab endpoints are unreadable: {path}") from exc
    if not endpoints:
        raise ProbeError("Strategy Lab endpoints are empty")
    return endpoints


def _network(workdir: Path, result_path: Path) -> int:
    for name in ("curl", "netstat", "openssl"):
        request.binary(name)
    route_available, route_result = request.ipv6_default_route()
    with ThreadPoolExecutor(max_workers=3) as pool:
        ipv4_future = pool.submit(request.curl_request, "yandex.ru", scheme="https", family="ipv4", tls_version="1.3")
        ipv6_future = (
            pool.submit(request.curl_request, "one.one.one.one", scheme="https", family="ipv6", tls_version="1.3")
            if route_available else None
        )
        quic_future = pool.submit(request.quic_ipv4_request)
        ipv4_result = ipv4_future.result()
        ipv6_result = ipv6_future.result() if ipv6_future is not None else None
        quic_result = quic_future.result()

    request.write_text(workdir / "control-ipv4.log", request.combined_log(ipv4_result))
    request.write_text(workdir / "control-ipv6.log", request.combined_log(ipv6_result) if ipv6_result is not None else "")
    request.write_text(workdir / "control-quic-ipv4.log", request.combined_log(quic_result))

    ipv4 = "available" if ipv4_result.ok else "unavailable"
    ipv6 = "available" if route_available and ipv6_result is not None and ipv6_result.ok else "unavailable"
    quic_ipv4 = "available" if quic_result.ok else "closed"
    quic_ipv6 = "eligible" if quic_ipv4 == "available" and ipv6 == "available" else "skipped"

    _write_json(result_path, {
        "ipv4": ipv4,
        "ipv6": ipv6,
        "quic_ipv4": quic_ipv4,
        "quic_ipv6": quic_ipv6,
    })
    _write_json(workdir / "network-evidence.json", {
        "ipv4": ipv4_result.evidence(),
        "ipv6_route": {"available": route_available, "execution": route_result.evidence()},
        "ipv6": ipv6_result.evidence() if ipv6_result is not None else None,
        "quic_ipv4": quic_result.evidence(),
    })
    return EX_OK if ipv4 == "available" else EX_PREREQUISITE


def _dns_failure_public(endpoint: str, log_text: str) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "status": "FAIL",
        "exit_code": 1,
        "transport": "dns-a",
        "detail": request.tail20(log_text),
    }


def _domain_public(endpoint: str, ipv4: request.CommandResult, ipv6: request.CommandResult | None) -> dict[str, Any]:
    ipv4_status = "PASS" if ipv4.ok else "FAIL"
    ipv6_status = "SKIPPED" if ipv6 is None else ("PASS" if ipv6.ok else "FAIL")
    ipv4_log = request.combined_log(ipv4)
    ipv6_log = request.combined_log(ipv6) if ipv6 is not None else ""
    return {
        "endpoint": endpoint,
        "status": ipv4_status,
        "exit_code": request.curl_exit(ipv4),
        "transport": "tls13-ipv4",
        "detail": request.tail20(ipv4_log),
        "ipv4": {
            "status": ipv4_status,
            "exit_code": request.curl_exit(ipv4),
            "detail": request.tail20(ipv4_log),
        },
        "ipv6": {
            "status": ipv6_status,
            "exit_code": None if ipv6 is None else request.curl_exit(ipv6),
            "detail": request.tail20(ipv6_log),
        },
    }


def _ip_public(endpoint: str, result: request.CommandResult) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "status": "PASS" if result.ok else "FAIL",
        "exit_code": result.returncode if result.returncode is not None and result.returncode >= 0 else 1,
        "transport": "tcp-443",
        "detail": request.tail20(request.combined_log(result)),
    }


def _domain_endpoint(endpoint: str, index: int, workdir: Path, ipv6_enabled: bool) -> tuple[dict[str, Any], dict[str, Any], bool, bool]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        dns_a_future = pool.submit(request.dns_request, endpoint, "A")
        dns_aaaa_future = pool.submit(request.dns_request, endpoint, "AAAA") if ipv6_enabled else None
        tls4_future = pool.submit(request.curl_request, endpoint, scheme="https", family="ipv4", tls_version="1.3")
        tls6_future = (
            pool.submit(request.curl_request, endpoint, scheme="https", family="ipv6", tls_version="1.3")
            if ipv6_enabled else None
        )
        dns_a = dns_a_future.result()
        dns_aaaa = dns_aaaa_future.result() if dns_aaaa_future is not None else None
        tls4 = tls4_future.result()
        tls6 = tls6_future.result() if tls6_future is not None else None

    dns_a_log = request.combined_log(dns_a.execution)
    request.write_text(workdir / f"endpoint-{index}.a.log", dns_a_log)
    if dns_aaaa is not None:
        request.write_text(workdir / f"endpoint-{index}.aaaa.log", request.combined_log(dns_aaaa.execution))
    request.write_text(workdir / f"endpoint-{index}.tls-ipv4.log", request.combined_log(tls4))
    if tls6 is not None:
        request.write_text(workdir / f"endpoint-{index}.tls-ipv6.log", request.combined_log(tls6))

    evidence = {
        "endpoint": endpoint,
        "dns_a": dns_a.evidence(),
        "dns_aaaa": dns_aaaa.evidence() if dns_aaaa is not None else None,
        "tls_ipv4": tls4.evidence(),
        "tls_ipv6": tls6.evidence() if tls6 is not None else None,
    }
    public = _dns_failure_public(endpoint, dns_a_log) if not dns_a.ok else _domain_public(endpoint, tls4, tls6)
    return public, evidence, not dns_a.ok, dns_aaaa is not None and not dns_aaaa.ok


def _ip_endpoint(endpoint: str, index: int, workdir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    result = request.tcp_request(endpoint, 443)
    request.write_text(workdir / f"endpoint-{index}.tcp.log", request.combined_log(result))
    return _ip_public(endpoint, result), {"endpoint": endpoint, "tcp_443": result.evidence()}


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
        request.binary("drill")
        request.binary("curl")
        dns_a_status = "PASS"
        dns_aaaa_status = "PASS" if ipv6_enabled else "SKIPPED"
        with ThreadPoolExecutor(max_workers=min(4, len(endpoints))) as pool:
            futures = [
                pool.submit(_domain_endpoint, endpoint, index, workdir, ipv6_enabled)
                for index, endpoint in enumerate(endpoints, 1)
            ]
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
        request.binary("nc")
        with ThreadPoolExecutor(max_workers=min(4, len(endpoints))) as pool:
            futures = [
                pool.submit(_ip_endpoint, endpoint, index, workdir)
                for index, endpoint in enumerate(endpoints, 1)
            ]
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
    _write_json(workdir / "baseline-evidence.json", {
        "target": target,
        "target_type": target_type,
        "endpoints": evidence_results,
    })
    return EX_PREREQUISITE if dns_failed else EX_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise UsageError("probe operation is required")
    if args[0] == "network":
        if len(args) != 3:
            raise UsageError("probe network requires RESULT WORKDIR")
        return _network(Path(args[2]), Path(args[1]))
    if args[0] == "baseline":
        if len(args) != 7:
            raise UsageError("probe baseline requires TARGET TYPE ENDPOINTS NETWORK WORKDIR RESULT")
        return _baseline(args[1], args[2], Path(args[3]), Path(args[4]), Path(args[5]), Path(args[6]))
    raise UsageError(f"unsupported Strategy Lab probe operation: {args[0]}")
