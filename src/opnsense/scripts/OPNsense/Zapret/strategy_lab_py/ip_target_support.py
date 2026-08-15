"""IPv4 Strategy Lab target contract with optional Host/SNI service identity.

This module installs the target-aware behavior at the packaged Python entry point so the
existing domain path stays unchanged while IP jobs use a fixed destination IPv4 address.
For IP jobs the endpoint identity may be a separate service hostname; TLS/HTTP/QUIC probes
therefore connect to the pinned IP while preserving the endpoint Host/SNI identity.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import candidate, endpoint_epoch, probe, request, search_graph

JOB_RE = re.compile(r"^job\.[A-Za-z0-9]+$")
_INSTALLED = False
_IP_BASELINE_TARGET = ""

_ORIGINAL_EPOCH_CREATE = endpoint_epoch.create
_ORIGINAL_BASELINE = probe._baseline
_ORIGINAL_CANDIDATE_DESCRIPTION = candidate._candidate_description
_ORIGINAL_CANDIDATE_PROBE = candidate._probe_endpoint
_ORIGINAL_RUN_CANDIDATE = candidate.run_candidate
_ORIGINAL_SEARCH_SPEC = search_graph._spec


def _jobs_dir() -> Path:
    return Path(
        os.environ.get(
            "STRATEGY_LAB_JOBS_DIR",
            "/var/run/zapret2-restyle/strategy-lab/jobs",
        )
    )


def _target_type_from_job(job_id: str) -> str:
    if not JOB_RE.fullmatch(job_id):
        return ""
    path = _jobs_dir() / job_id / endpoint_epoch.SEARCH_EPOCH_FILE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    target_type = value.get("target_type") if isinstance(value, dict) else None
    return target_type if target_type in {"domain", "ip"} else ""


def _configure_target_type_from_argv() -> None:
    for value in sys.argv[1:]:
        if JOB_RE.fullmatch(value):
            target_type = _target_type_from_job(value)
            if target_type:
                os.environ["STRATEGY_LAB_TARGET_TYPE"] = target_type
            return


def _epoch_create(
    job_dir: Path,
    target: str,
    target_type: str,
    endpoints: Iterable[str],
    baseline_evidence: Iterable[dict[str, Any]],
) -> endpoint_epoch.SearchEpoch:
    if target_type != "ip":
        return _ORIGINAL_EPOCH_CREATE(
            job_dir, target, target_type, endpoints, baseline_evidence
        )

    endpoint_values = tuple(endpoints)
    evidence_values = tuple(baseline_evidence)
    if not target or not endpoint_values or len(endpoint_values) != len(evidence_values):
        raise endpoint_epoch.EndpointEpochError("search-epoch target contract is invalid")
    destination = endpoint_epoch._canonical_ipv4(target)
    raw_bindings: list[dict[str, Any]] = []
    for index, (endpoint, evidence) in enumerate(
        zip(endpoint_values, evidence_values, strict=True), 1
    ):
        if (
            not isinstance(endpoint, str)
            or not endpoint
            or not isinstance(evidence, dict)
            or evidence.get("endpoint") != endpoint
        ):
            raise endpoint_epoch.EndpointEpochError(
                "search-epoch endpoint evidence is invalid"
            )
        raw_bindings.append(
            {
                "index": index,
                "endpoint": endpoint,
                "addresses": [destination],
                "selected_ip": destination,
            }
        )
    bindings = endpoint_epoch._validated_bindings(raw_bindings)

    previous_path = job_dir / endpoint_epoch.SEARCH_EPOCH_FILE
    generation = 1
    if previous_path.is_file():
        generation = endpoint_epoch.load(job_dir).generation + 1
    payload = endpoint_epoch._identity_payload(
        job_dir.name, generation, target, target_type, bindings
    )
    epoch = endpoint_epoch.SearchEpoch(
        epoch_id=endpoint_epoch._epoch_id(payload),
        generation=generation,
        target=target,
        target_type=target_type,
        bindings=bindings,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source="stage40-baseline",
    )
    endpoint_epoch._atomic_json(previous_path, epoch.to_dict())
    return epoch


def _ip_endpoint(
    endpoint: str,
    index: int,
    workdir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not _IP_BASELINE_TARGET:
        raise probe.ProbeError("Strategy Lab IPv4 baseline target is unavailable")
    result = request.curl_request(
        endpoint,
        scheme="https",
        family="ipv4",
        tls_version="1.3",
        bound_ip=_IP_BASELINE_TARGET,
    )
    log = request.combined_log(result)
    request.write_text(workdir / f"endpoint-{index}.tls-ipv4.log", log)
    public = {
        "endpoint": endpoint,
        "status": "PASS" if result.ok else "FAIL",
        "exit_code": request.curl_exit(result),
        "transport": "tls13-ipv4",
        "detail": request.tail20(log),
    }
    evidence = {
        "endpoint": endpoint,
        "destination_ip": _IP_BASELINE_TARGET,
        "tls_ipv4": result.evidence(),
    }
    return public, evidence


def _baseline(
    target: str,
    target_type: str,
    endpoints_path: Path,
    network_path: Path,
    workdir: Path,
    result_path: Path,
) -> int:
    global _IP_BASELINE_TARGET
    if target_type != "ip":
        return _ORIGINAL_BASELINE(
            target, target_type, endpoints_path, network_path, workdir, result_path
        )
    previous = _IP_BASELINE_TARGET
    _IP_BASELINE_TARGET = endpoint_epoch._canonical_ipv4(target)
    try:
        return _ORIGINAL_BASELINE(
            target, target_type, endpoints_path, network_path, workdir, result_path
        )
    finally:
        _IP_BASELINE_TARGET = previous


def _candidate_description(*args: Any, **kwargs: Any) -> candidate.CandidateSpec:
    description = _ORIGINAL_CANDIDATE_DESCRIPTION(*args, **kwargs)
    if (
        os.environ.get("STRATEGY_LAB_TARGET_TYPE") == "ip"
        and description.target_binding
    ):
        return replace(description, target_binding=False)
    return description


def _candidate_probe(
    binding: dict[str, Any],
    spec: candidate.ProtocolSpec | None = None,
) -> dict[str, Any]:
    spec = spec or candidate.ProtocolSpec("tls13", "tcp", 443, "tls")
    endpoint = str(binding["endpoint"])
    selected = str(binding["selected_ip"])
    rule = int(binding["rule"])
    before_packets, before_bytes = candidate._counter(rule)

    if spec.protocol == "udp":
        assert spec.payload_path is not None
        execution = request.udp_response_request(selected, spec.port, spec.payload_path)
        exit_code = candidate._execution_status(execution)
        if exit_code == 0 and not execution.stdout:
            exit_code = 1
        remote_ip = selected
        transport = f"udp-{spec.port}"
    elif spec.protocol == "quic":
        if candidate._is_ipv4(endpoint):
            execution = candidate._unsupported_execution(
                "QUIC hostname verification requires Host / SNI for an IPv4 target"
            )
            exit_code = 64
            remote_ip = ""
        else:
            execution = request.quic_target_request(endpoint, selected)
            exit_code = candidate._execution_status(execution)
            remote_ip = selected
        transport = "quic-ipv4"
    elif spec.protocol == "http":
        execution = request.curl_request(
            endpoint, scheme="http", family="ipv4", bound_ip=selected
        )
        exit_code = request.curl_exit(execution)
        remote_ip = candidate._remote_ip(execution.stdout)
        transport = "http-ipv4"
    else:
        tls_version = "1.2" if spec.protocol == "tls12" else "1.3"
        execution = request.curl_request(
            endpoint,
            scheme="https",
            family="ipv4",
            tls_version=tls_version,
            bound_ip=selected,
        )
        exit_code = request.curl_exit(execution)
        remote_ip = candidate._remote_ip(execution.stdout)
        transport = f"{spec.protocol}-ipv4"

    after_packets, after_bytes = candidate._counter(rule)
    endpoint_match = remote_ip == selected
    intercepted = after_packets > before_packets
    passed = exit_code == 0 and endpoint_match and intercepted
    return {
        "endpoint": endpoint,
        "status": "PASS" if passed else "FAIL",
        "exit_code": int(exit_code),
        "transport": transport,
        "detail": candidate._detail(execution),
        "selected_ip": selected,
        "remote_ip": remote_ip,
        "endpoint_match": endpoint_match,
        "firewall": {
            "rule": rule,
            "packets_before": before_packets,
            "packets_after": after_packets,
            "bytes_before": before_bytes,
            "bytes_after": after_bytes,
            "intercepted": intercepted,
        },
        "execution": execution.evidence(),
    }


def _run_candidate(*args: Any, **kwargs: Any) -> int:
    job_id = str(args[0]) if args else str(kwargs.get("job_id", ""))
    previous = os.environ.get("STRATEGY_LAB_TARGET_TYPE")
    target_type = _target_type_from_job(job_id)
    if target_type:
        os.environ["STRATEGY_LAB_TARGET_TYPE"] = target_type
    try:
        return _ORIGINAL_RUN_CANDIDATE(*args, **kwargs)
    finally:
        if previous is None:
            os.environ.pop("STRATEGY_LAB_TARGET_TYPE", None)
        else:
            os.environ["STRATEGY_LAB_TARGET_TYPE"] = previous


def _search_spec(*args: Any, **kwargs: Any) -> Any:
    if os.environ.get("STRATEGY_LAB_TARGET_TYPE") == "ip":
        kwargs["target_binding"] = False
    return _ORIGINAL_SEARCH_SPEC(*args, **kwargs)


def install() -> None:
    """Install the IPv4 target behavior once for the packaged Python process."""
    global _INSTALLED
    if _INSTALLED:
        return
    _configure_target_type_from_argv()
    endpoint_epoch.create = _epoch_create
    probe._ip_endpoint = _ip_endpoint
    probe._baseline = _baseline
    candidate._candidate_description = _candidate_description
    candidate._probe_endpoint = _candidate_probe
    candidate.run_candidate = _run_candidate
    search_graph._spec = _search_spec
    _INSTALLED = True
