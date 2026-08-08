"""Python-owned Strategy Lab extended TLS/HTTP/QUIC/generic-UDP orchestration."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from . import search

EX_OK = 0
EX_USAGE = 64
EX_CANCEL = 125
JOB_RE = re.compile(r"^job\.[A-Za-z0-9]+$")


def script_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def module_dir() -> Path:
    return Path(os.environ.get("MODULE_DIR", str(script_dir() / "strategy_lab")))


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ValueError("invalid Strategy Lab job id")
    return jobs_dir() / job_id


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Strategy Lab JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _catalog(path: Path, fields: int) -> list[tuple[str, ...]]:
    if not path.is_file():
        raise RuntimeError(f"Strategy Lab catalog is unavailable: {path}")
    rows: list[tuple[str, ...]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        values = tuple(part.strip() for part in raw.split("\t"))
        if len(values) != fields or not all(values):
            raise RuntimeError(f"invalid Strategy Lab catalog row: {path}")
        rows.append(values)
    return rows


def _runner(env_name: str, default: str = "strategy_lab_candidate_runner.sh") -> Path:
    path = Path(os.environ.get(env_name, str(script_dir() / default)))
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"Strategy Lab candidate runner is unavailable: {path}")
    return path


def _timeout(env_name: str) -> float:
    return search._positive_float(env_name, 5)


def _candidate(
    job_id: str,
    endpoints: Path,
    candidate_path: Path,
    candidate_id: str,
    family: str,
    strategy_path: Path,
    use_hostlist: str,
    *,
    runner: Path,
    timeout: float,
    protocol: str,
    port: str,
    l7: str,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any] | int:
    try:
        candidate_path.unlink()
    except FileNotFoundError:
        pass
    env = {
        "STRATEGY_LAB_CANDIDATE_PROTOCOL": protocol,
        "STRATEGY_LAB_CANDIDATE_PORT": port,
        "STRATEGY_LAB_CANDIDATE_L7": l7,
    }
    if extra_env:
        env.update(extra_env)
    command = [
        str(runner), job_id, str(endpoints), str(candidate_path), candidate_id,
        family, str(strategy_path), use_hostlist,
    ]
    status, timed_out = search._run_candidate(command, timeout, job_id, extra_env=env)
    if status == EX_CANCEL:
        return EX_CANCEL
    if timed_out:
        value = search._timeout_result(candidate_id, family, strategy_path.read_text(encoding="utf-8"))
        value["protocol"] = protocol
        _atomic_json(candidate_path, value)
        return value
    if status != 0:
        raise RuntimeError(f"Strategy Lab {protocol} candidate runner failed for {candidate_id} with status {status}")
    return search._read_candidate(candidate_path, candidate_id)


def tcp(job_id: str, endpoints_file: str, result_file: str) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    if not endpoints.is_file():
        return EX_USAGE
    output = Path(result_file)
    catalog_path = Path(os.environ.get("STRATEGY_LAB_EXTENDED_CATALOG", str(module_dir() / "catalog/extended-tcp.tsv")))
    args_dir = Path(os.environ.get("STRATEGY_LAB_EXTENDED_ARGS_DIR", str(module_dir() / "catalog/extended-tcp")))
    rows = _catalog(catalog_path, 7)
    runner = _runner("STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER")
    timeout = _timeout("STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT")
    work = job_dir(job_id) / "extended-tcp"
    work.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "protocols": {
            "tls12": {"tested": [], "working": None},
            "http": {"tested": [], "working": None},
        }
    }
    _atomic_json(output, result)

    for protocol, candidate_id, family, port, l7, hostlist, args_name in rows:
        if protocol not in result["protocols"]:
            raise RuntimeError(f"unsupported Strategy Lab extended TCP protocol: {protocol}")
        if result["protocols"][protocol]["working"] is not None:
            continue
        if search._cancel_requested(job_id):
            return EX_CANCEL
        strategy_path = args_dir / args_name
        if not strategy_path.is_file():
            raise RuntimeError(f"Strategy Lab extended args are unavailable: {strategy_path}")
        candidate_path = work / f"{candidate_id}.json"
        value = _candidate(
            job_id, endpoints, candidate_path, candidate_id, family, strategy_path, hostlist,
            runner=runner, timeout=timeout, protocol=protocol, port=port, l7=l7,
        )
        if value == EX_CANCEL:
            return EX_CANCEL
        assert isinstance(value, dict)
        result["protocols"][protocol]["tested"].append(value)
        if value.get("all_pass") is True:
            result["protocols"][protocol]["working"] = value
        _atomic_json(output, result)
    return EX_OK


def quic(job_id: str, endpoints_file: str, network_file: str, result_file: str) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    network_path = Path(network_file)
    if not endpoints.is_file() or not network_path.is_file():
        return EX_USAGE
    output = Path(result_file)
    capability = _load_json(network_path).get("quic_ipv4", "unknown")
    if not isinstance(capability, str):
        raise RuntimeError("Strategy Lab QUIC capability is invalid")
    result: dict[str, Any] = {"capability": capability, "status": "pending", "tested": [], "working": None}
    _atomic_json(output, result)
    if capability != "available":
        result["status"] = "skipped"
        result["reason"] = f"quic_ipv4_{capability}"
        _atomic_json(output, result)
        return EX_OK

    catalog_path = Path(os.environ.get("STRATEGY_LAB_QUIC_CATALOG", str(module_dir() / "catalog/quic.tsv")))
    args_dir = Path(os.environ.get("STRATEGY_LAB_QUIC_ARGS_DIR", str(module_dir() / "catalog/quic")))
    rows = _catalog(catalog_path, 4)
    runner = _runner("STRATEGY_LAB_QUIC_CANDIDATE_RUNNER")
    timeout = _timeout("STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT")
    work = job_dir(job_id) / "quic"
    work.mkdir(parents=True, exist_ok=True)

    for candidate_id, family, hostlist, args_name in rows:
        if search._cancel_requested(job_id):
            return EX_CANCEL
        strategy_path = args_dir / args_name
        if not strategy_path.is_file():
            raise RuntimeError(f"Strategy Lab QUIC args are unavailable: {strategy_path}")
        candidate_path = work / f"{candidate_id}.json"
        value = _candidate(
            job_id, endpoints, candidate_path, candidate_id, family, strategy_path, hostlist,
            runner=runner, timeout=timeout, protocol="quic", port="443", l7="quic",
        )
        if value == EX_CANCEL:
            return EX_CANCEL
        assert isinstance(value, dict)
        result["tested"].append(value)
        if value.get("all_pass") is True:
            result["working"] = value
            result["status"] = "working"
            _atomic_json(output, result)
            return EX_OK
        _atomic_json(output, result)

    result["status"] = "not_found"
    _atomic_json(output, result)
    return EX_OK


def _udp_input(job_id: str) -> tuple[int | None, Path | None, str | None]:
    direct_port = os.environ.get("STRATEGY_LAB_UDP_PORT", "").strip()
    direct_payload = os.environ.get("STRATEGY_LAB_UDP_PAYLOAD_FILE", "").strip()
    if direct_port or direct_payload:
        if not direct_port:
            return None, None, "udp_port_not_configured"
        try:
            port = int(direct_port, 10)
        except ValueError:
            return None, None, "udp_port_invalid"
        if port < 1 or port > 65535:
            return None, None, "udp_port_invalid"
        payload = Path(direct_payload) if direct_payload else None
        if payload is None or not payload.is_file() or payload.stat().st_size <= 0:
            return None, None, "udp_payload_not_configured"
        return port, payload, None

    status_path = job_dir(job_id) / "status.json"
    if not status_path.is_file():
        return None, None, "udp_port_not_configured"
    status = _load_json(status_path)
    udp_request = status.get("udp_request", {})
    if not isinstance(udp_request, dict) or udp_request.get("configured") is not True:
        return None, None, "udp_port_not_configured"
    port_file = job_dir(job_id) / "udp-port"
    payload = job_dir(job_id) / "udp-payload.bin"
    try:
        port = int(port_file.read_text(encoding="utf-8").strip(), 10)
    except (OSError, ValueError) as exc:
        raise RuntimeError("configured Strategy Lab UDP port file is invalid") from exc
    if port < 1 or port > 65535:
        raise RuntimeError("configured Strategy Lab UDP port is invalid")
    if not payload.is_file() or payload.stat().st_size <= 0:
        raise RuntimeError("configured Strategy Lab UDP payload is unavailable")
    return port, payload, None


def udp(job_id: str, endpoints_file: str, result_file: str) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    if not endpoints.is_file():
        return EX_USAGE
    output = Path(result_file)
    result: dict[str, Any] = {"status": "pending", "port": None, "tested": [], "working": None}
    _atomic_json(output, result)
    port, payload, reason = _udp_input(job_id)
    if reason is not None:
        result["status"] = "skipped"
        result["reason"] = reason
        _atomic_json(output, result)
        return EX_OK
    assert port is not None and payload is not None
    result["port"] = port
    _atomic_json(output, result)

    catalog_path = Path(os.environ.get("STRATEGY_LAB_UDP_CATALOG", str(module_dir() / "catalog/udp.tsv")))
    args_dir = Path(os.environ.get("STRATEGY_LAB_UDP_ARGS_DIR", str(module_dir() / "catalog/udp")))
    rows = _catalog(catalog_path, 3)
    runner = _runner("STRATEGY_LAB_UDP_CANDIDATE_RUNNER")
    timeout = _timeout("STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT")
    work = job_dir(job_id) / "udp"
    work.mkdir(parents=True, exist_ok=True)

    for candidate_id, family, args_name in rows:
        if search._cancel_requested(job_id):
            return EX_CANCEL
        strategy_path = args_dir / args_name
        if not strategy_path.is_file():
            raise RuntimeError(f"Strategy Lab UDP args are unavailable: {strategy_path}")
        candidate_path = work / f"{candidate_id}.json"
        value = _candidate(
            job_id, endpoints, candidate_path, candidate_id, family, strategy_path, "0",
            runner=runner, timeout=timeout, protocol="udp", port=str(port), l7="-",
            extra_env={
                "STRATEGY_LAB_UDP_PORT": str(port),
                "STRATEGY_LAB_UDP_PAYLOAD_FILE": str(payload),
            },
        )
        if value == EX_CANCEL:
            return EX_CANCEL
        assert isinstance(value, dict)
        result["tested"].append(value)
        if value.get("all_pass") is True:
            result["working"] = value
            result["status"] = "working"
            _atomic_json(output, result)
            return EX_OK
        _atomic_json(output, result)

    result["status"] = "not_found"
    _atomic_json(output, result)
    return EX_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise ValueError("extended operation is required")
    if args[0] == "tcp" and len(args) == 4:
        return tcp(args[1], args[2], args[3])
    if args[0] == "quic" and len(args) == 5:
        return quic(args[1], args[2], args[3], args[4])
    if args[0] == "udp" and len(args) == 4:
        return udp(args[1], args[2], args[3])
    raise ValueError(
        "extended requires: tcp JOB ENDPOINTS RESULT | quic JOB ENDPOINTS NETWORK RESULT | udp JOB ENDPOINTS RESULT"
    )
