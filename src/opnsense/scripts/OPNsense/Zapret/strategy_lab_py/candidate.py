"""Python-owned Strategy Lab candidate runtime and endpoint screening."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from . import candidate_spec, endpoint_epoch, request, resources, telemetry

EX_OK = 0
EX_USAGE = 64

JOB_RE = re.compile(r"^job\.[A-Za-z0-9]+$")
FATAL_RE = re.compile(
    r"(^|[^a-z])(fatal|panic|syntax error|unknown option|invalid (argument|option)|"
    r"cannot (bind|open|load)|failed to (bind|load))([^a-z]|$)",
    re.IGNORECASE,
)
REMOTE_IP_RE = re.compile(r"(?:^|\s)remote_ip=([^\s]+)")


@dataclass(frozen=True)
class ProtocolSpec:
    protocol: str
    transport: str
    port: int
    l7: str
    payload_path: Path | None = None


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _port(value: str, name: str) -> int:
    try:
        port = int(value, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid port") from exc
    if port < 1 or port > 65535:
        raise ValueError(f"{name} must be a valid port")
    return port


def _protocol_spec() -> ProtocolSpec:
    protocol = os.environ.get("STRATEGY_LAB_CANDIDATE_PROTOCOL", "tls13")
    if protocol == "tls13":
        return ProtocolSpec("tls13", "tcp", _port(os.environ.get("STRATEGY_LAB_CANDIDATE_PORT", "443"), "candidate port"), os.environ.get("STRATEGY_LAB_CANDIDATE_L7", "tls"))
    if protocol == "tls12":
        return ProtocolSpec("tls12", "tcp", _port(os.environ.get("STRATEGY_LAB_CANDIDATE_PORT", "443"), "candidate port"), os.environ.get("STRATEGY_LAB_CANDIDATE_L7", "tls"))
    if protocol == "http":
        return ProtocolSpec("http", "tcp", _port(os.environ.get("STRATEGY_LAB_CANDIDATE_PORT", "80"), "candidate port"), os.environ.get("STRATEGY_LAB_CANDIDATE_L7", "http"))
    if protocol == "quic":
        return ProtocolSpec("quic", "udp", _port(os.environ.get("STRATEGY_LAB_CANDIDATE_PORT", "443"), "candidate port"), os.environ.get("STRATEGY_LAB_CANDIDATE_L7", "quic"))
    if protocol == "udp":
        port = _port(os.environ.get("STRATEGY_LAB_UDP_PORT", os.environ.get("STRATEGY_LAB_CANDIDATE_PORT", "")), "UDP port")
        payload_raw = os.environ.get("STRATEGY_LAB_UDP_PAYLOAD_FILE", "")
        payload = Path(payload_raw) if payload_raw else None
        if payload is None or not payload.is_file() or payload.stat().st_size <= 0:
            raise ValueError("UDP payload is unavailable")
        return ProtocolSpec("udp", "udp", port, "-", payload)
    raise ValueError(f"unsupported Strategy Lab candidate protocol: {protocol}")


def script_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ValueError("invalid Strategy Lab job id")
    return jobs_dir() / job_id


def runtime_dir(job_id: str) -> Path:
    return job_dir(job_id) / "candidate-runtime"


def adapter_path() -> Path:
    return Path(
        os.environ.get(
            "STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER",
            str(script_dir() / "strategy_lab_candidate_adapter.sh"),
        )
    )


def _adapter(action: str, *args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    adapter = adapter_path()
    if not adapter.is_file():
        raise RuntimeError(f"Strategy Lab candidate system adapter is unavailable: {adapter}")
    shell = os.environ.get("STRATEGY_LAB_SH_BIN", "/bin/sh")
    command = [shell, str(adapter), action, *map(str, args)]
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"candidate system adapter timed out during {action}") from exc
    except OSError as exc:
        raise RuntimeError(f"candidate system adapter could not run during {action}: {exc}") from exc


def _require_adapter(action: str, *args: str, timeout: int = 10) -> str:
    completed = _adapter(action, *args, timeout=timeout)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"candidate system adapter {action} failed" + (f": {detail}" if detail else ""))
    return completed.stdout


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


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _candidate_description(
    candidate_id: str,
    family: str,
    protocol: ProtocolSpec,
    strategy: str,
    use_hostlist: str,
    spec_file: str = "",
) -> candidate_spec.CandidateSpec:
    if spec_file:
        try:
            value = json.loads(Path(spec_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise candidate_spec.CandidateSpecError(
                f"candidate spec is unreadable: {spec_file}"
            ) from exc
        description = candidate_spec.CandidateSpec.from_dict(value)
        expected_l7 = None if protocol.l7 == "-" else protocol.l7
        strategy_lines = tuple(line for line in strategy.splitlines() if line)
        if (
            description.candidate_id != candidate_id
            or description.family != family
            or description.protocol != protocol.protocol
            or description.transport != protocol.transport
            or description.port != protocol.port
            or description.l7 != expected_l7
            or description.target_binding != (use_hostlist == "1")
            or description.strategy_lines != strategy_lines
            or description.render_mode != "fragment"
        ):
            raise candidate_spec.CandidateSpecError(
                "candidate spec does not match its runner invocation"
            )
        return description
    exact_profile = os.environ.get("STRATEGY_LAB_PROFILE_REPLAY_EXACT", "") == "1"
    selector = os.environ.get("STRATEGY_LAB_PROFILE_REPLAY_SELECTOR", "") if exact_profile else None
    return candidate_spec.CandidateSpec.from_strategy(
        candidate_id=candidate_id,
        family=family,
        protocol=protocol.protocol,
        transport=protocol.transport,
        port=protocol.port,
        l7=None if protocol.l7 == "-" else protocol.l7,
        strategy=strategy,
        target_binding=use_hostlist == "1",
        render_mode="profile" if exact_profile else "fragment",
        target_selector=selector,
        provenance="profile-replay" if exact_profile else "legacy-catalog",
    )


def _prepare_runtime_files(
    job_id: str,
    endpoints: list[str],
    description: candidate_spec.CandidateSpec,
    inventory: resources.ResourceInventory,
) -> tuple[str, ...]:
    work = runtime_dir(job_id)
    work.mkdir(parents=True, exist_ok=True)
    hostlist = work / "hostlist.txt"
    if description.target_binding:
        _write_text(hostlist, "".join(f"{endpoint}\n" for endpoint in endpoints))
    else:
        try:
            hostlist.unlink()
        except FileNotFoundError:
            pass
    divert_port = _port(os.environ.get("STRATEGY_LAB_DIVERT_PORT", "9989"), "candidate divert port")
    arguments = description.render_runtime_arguments(
        inventory,
        divert_port=divert_port,
        hostlist_path=hostlist if description.target_binding else None,
    )
    _write_text(work / "dvtws.args", "".join(f"{argument}\n" for argument in arguments))
    return arguments


def _read_endpoints(path: Path) -> list[str]:
    if not path.is_file():
        raise ValueError("candidate endpoints file is unavailable")
    endpoints = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not endpoints:
        raise ValueError("candidate endpoints file is empty")
    return endpoints


def _is_ipv4(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).version == 4
    except ValueError:
        return False


def _pinned_endpoints(
    job_id: str,
    endpoints: list[str],
) -> tuple[list[dict[str, Any]], endpoint_epoch.SearchEpoch]:
    work = runtime_dir(job_id)
    work.mkdir(parents=True, exist_ok=True)
    rule_base = _positive_int("STRATEGY_LAB_RULE_BASE", 19100)
    rule_max = _positive_int("STRATEGY_LAB_RULE_MAX", 19131)
    unique: list[str] = []
    bindings: list[dict[str, Any]] = []
    epoch = endpoint_epoch.load(job_dir(job_id), endpoints)

    for item in epoch.bindings:
        index = int(item["index"])
        endpoint = str(item["endpoint"])
        selected = str(item["selected_ip"])
        if selected not in unique:
            unique.append(selected)
        rule = rule_base + unique.index(selected)
        if rule > rule_max:
            raise RuntimeError("candidate endpoint set exceeds reserved firewall rule range")
        bindings.append(
            {
                "index": index,
                "endpoint": endpoint,
                "addresses": list(item["addresses"]),
                "selected_ip": selected,
                "rule": rule,
            }
        )

    _write_text(work / "addresses-ipv4.txt", "".join(f"{address}\n" for address in unique))
    _write_text(
        work / "endpoint-bindings.tsv",
        "".join(
            f"{item['index']}\t{item['endpoint']}\t{item['selected_ip']}\t{item['rule']}\n"
            for item in bindings
        ),
    )
    return bindings, epoch


def _runtime_snapshot(job_id: str) -> dict[str, Any]:
    raw = _require_adapter("snapshot", job_id)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("candidate system adapter returned invalid runtime snapshot") from exc
    if not isinstance(value, dict):
        raise RuntimeError("candidate runtime snapshot is not an object")
    return value


def _fatal_reason(log_text: str) -> str:
    for line in log_text.splitlines():
        if FATAL_RE.search(line):
            return line.strip()[:4096]
    return ""


def _readiness(job_id: str) -> dict[str, Any]:
    work = runtime_dir(job_id)
    output = work / "readiness.json"
    log_path = work / "dvtws2.log"
    attempts_limit = _positive_int("STRATEGY_LAB_RUNTIME_START_TIMEOUT", 3)
    interval = float(os.environ.get("STRATEGY_LAB_RUNTIME_READY_POLL", "1"))
    if interval <= 0:
        raise ValueError("STRATEGY_LAB_RUNTIME_READY_POLL must be positive")
    stable = 0
    last: dict[str, Any] = {}

    for attempt in range(1, attempts_limit + 1):
        snapshot = _runtime_snapshot(job_id)
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        fatal = _fatal_reason(log_text)
        identity = bool(snapshot.get("process_identity"))
        socket_ready = bool(snapshot.get("socket_ready"))
        log_clean = not fatal
        if identity and socket_ready and log_clean:
            stable += 1
        else:
            stable = 0
        ready = stable >= 2
        last = {
            "job_id": job_id,
            "pid": snapshot.get("pid"),
            "executable": snapshot.get("executable", os.environ.get("STRATEGY_LAB_DVTWS_BIN", "/usr/local/etc/zapret2/binaries/my/dvtws2")),
            "command": snapshot.get("command", ""),
            "divert_port": int(snapshot.get("divert_port", os.environ.get("STRATEGY_LAB_DIVERT_PORT", "9989"))),
            "process_identity": identity,
            "socket_ready": socket_ready,
            "log_clean": log_clean,
            "stable": ready,
            "ready": ready,
            "attempts": attempt,
            "stable_checks": stable,
            "fatal_reason": fatal,
        }
        _atomic_json(output, last)
        if ready:
            return last
        if fatal:
            break
        if attempt < attempts_limit:
            time.sleep(interval)

    return last or {
        "job_id": job_id,
        "pid": None,
        "executable": os.environ.get("STRATEGY_LAB_DVTWS_BIN", "/usr/local/etc/zapret2/binaries/my/dvtws2"),
        "command": "",
        "divert_port": int(os.environ.get("STRATEGY_LAB_DIVERT_PORT", "9989")),
        "process_identity": False,
        "socket_ready": False,
        "log_clean": False,
        "stable": False,
        "ready": False,
        "attempts": 0,
        "stable_checks": 0,
        "fatal_reason": "runtime snapshot unavailable",
    }


def _counter(rule: int) -> tuple[int, int]:
    raw = _require_adapter("counter", str(rule)).strip().split()
    if len(raw) != 2:
        raise RuntimeError(f"invalid firewall counter evidence for rule {rule}")
    try:
        return int(raw[0]), int(raw[1])
    except ValueError as exc:
        raise RuntimeError(f"invalid firewall counter evidence for rule {rule}") from exc


def _remote_ip(stdout: str) -> str:
    match = None
    for match in REMOTE_IP_RE.finditer(stdout):
        pass
    return "" if match is None else match.group(1)


def _detail(result: request.CommandResult) -> str:
    return request.tail20(request.combined_log(result))[:4096]


def _execution_status(result: request.CommandResult) -> int:
    if result.timed_out:
        return 124
    if result.returncode is None or result.returncode < 0:
        return 1
    return result.returncode


def _unsupported_execution(reason: str) -> request.CommandResult:
    return request.CommandResult(
        command=[], returncode=64, stdout="", stderr=reason, timed_out=False,
        termination="completed", signal=None, duration_ms=0,
    )


def _probe_endpoint(binding: dict[str, Any], spec: ProtocolSpec | None = None) -> dict[str, Any]:
    spec = spec or ProtocolSpec("tls13", "tcp", 443, "tls")
    endpoint = str(binding["endpoint"])
    selected = str(binding["selected_ip"])
    rule = int(binding["rule"])
    before_packets, before_bytes = _counter(rule)

    if spec.protocol == "udp":
        assert spec.payload_path is not None
        execution = request.udp_response_request(selected, spec.port, spec.payload_path)
        exit_code = _execution_status(execution)
        if exit_code == 0 and not execution.stdout:
            exit_code = 1
        remote_ip = selected
        transport = f"udp-{spec.port}"
    elif spec.protocol == "quic":
        if _is_ipv4(endpoint):
            execution = _unsupported_execution("QUIC hostname verification requires a domain endpoint")
            exit_code = 64
            remote_ip = ""
        else:
            execution = request.quic_target_request(endpoint, selected)
            exit_code = _execution_status(execution)
            remote_ip = selected
        transport = "quic-ipv4"
    elif _is_ipv4(endpoint):
        execution = request.tcp_request(selected, spec.port)
        exit_code = _execution_status(execution)
        remote_ip = selected
        transport = f"tcp-{spec.port}"
    elif spec.protocol == "http":
        execution = request.curl_request(endpoint, scheme="http", bound_ip=selected)
        exit_code = request.curl_exit(execution)
        remote_ip = _remote_ip(execution.stdout)
        transport = "http-ipv4"
    else:
        tls_version = "1.2" if spec.protocol == "tls12" else "1.3"
        execution = request.curl_request(endpoint, scheme="https", tls_version=tls_version, bound_ip=selected)
        exit_code = request.curl_exit(execution)
        remote_ip = _remote_ip(execution.stdout)
        transport = f"{spec.protocol}-ipv4"

    after_packets, after_bytes = _counter(rule)
    endpoint_match = remote_ip == selected
    intercepted = after_packets > before_packets
    passed = exit_code == 0 and endpoint_match and intercepted
    return {
        "endpoint": endpoint,
        "status": "PASS" if passed else "FAIL",
        "exit_code": int(exit_code),
        "transport": transport,
        "detail": _detail(execution),
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


def _error_result(
    candidate_id: str,
    family: str,
    strategy: str,
    runtime: dict[str, Any] | None,
    message: str,
    description: candidate_spec.CandidateSpec | None = None,
    inventory: resources.ResourceInventory | None = None,
    runtime_arguments: tuple[str, ...] = (),
    epoch: endpoint_epoch.SearchEpoch | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": candidate_id,
        "family": family,
        "strategy": strategy,
        "endpoints": [],
        "all_pass": False,
        "error": True,
        "message": message,
    }
    if runtime is not None:
        result["runtime"] = runtime
    if description is not None:
        result["candidate_spec"] = description.to_dict()
    if inventory is not None:
        result["resource_inventory_id"] = inventory.inventory_id
    if runtime_arguments:
        result["runtime_arguments"] = list(runtime_arguments)
    if epoch is not None:
        result["search_epoch_id"] = epoch.epoch_id
        result["search_epoch_generation"] = epoch.generation
        result["endpoint_bindings"] = list(epoch.bindings)
    return result


def run_candidate(
    job_id: str,
    endpoints_file: str,
    result_file: str,
    candidate_id: str,
    family: str,
    strategy_file: str,
    use_hostlist: str,
    spec_file: str = "",
) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    if use_hostlist not in {"0", "1"}:
        return EX_USAGE
    endpoints_path = Path(endpoints_file)
    strategy_path = Path(strategy_file)
    result_path = Path(result_file)
    if not strategy_path.is_file():
        return EX_USAGE
    strategy = strategy_path.read_text(encoding="utf-8")
    runtime_evidence: dict[str, Any] | None = None
    description: candidate_spec.CandidateSpec | None = None
    inventory: resources.ResourceInventory | None = None
    runtime_arguments: tuple[str, ...] = ()
    epoch: endpoint_epoch.SearchEpoch | None = None
    cleanup_error = ""
    total_started = time.monotonic()
    timings: dict[str, Any] = {
        "pre_cleanup_ms": 0,
        "endpoint_binding_ms": 0,
        "candidate_prepare_ms": 0,
        "resource_render_ms": 0,
        "firewall_install_ms": 0,
        "launch_ms": 0,
        "readiness_ms": 0,
        "probe_ms": 0,
        "cleanup_ms": 0,
        "resource_init_ms": None,
        "resource_init_scope": "included_in_launch_and_readiness",
        "total_ms": 0,
    }

    try:
        protocol = _protocol_spec()
        endpoints = _read_endpoints(endpoints_path)
        work = runtime_dir(job_id)
        work.mkdir(parents=True, exist_ok=True)
        phase_started = time.monotonic()
        _require_adapter("cleanup", job_id)
        timings["pre_cleanup_ms"] = telemetry.elapsed_ms(phase_started)
        phase_started = time.monotonic()
        bindings, epoch = _pinned_endpoints(job_id, endpoints)
        timings["endpoint_binding_ms"] = telemetry.elapsed_ms(phase_started)
        phase_started = time.monotonic()
        inventory = resources.ensure_job_inventory(job_dir(job_id))
        description = _candidate_description(
            candidate_id, family, protocol, strategy, use_hostlist, spec_file
        )
        timings["candidate_prepare_ms"] = telemetry.elapsed_ms(phase_started)
        phase_started = time.monotonic()
        runtime_arguments = _prepare_runtime_files(job_id, endpoints, description, inventory)
        timings["resource_render_ms"] = telemetry.elapsed_ms(phase_started)
        phase_started = time.monotonic()
        wan = _require_adapter("wan").strip()
        if not wan:
            raise RuntimeError("candidate WAN interface could not be resolved")
        _require_adapter(
            "firewall-install-protocol", str(work / "addresses-ipv4.txt"), wan,
            protocol.transport, str(protocol.port),
        )
        if use_hostlist == "1":
            _require_adapter("allow-access", job_id)
        timings["firewall_install_ms"] = telemetry.elapsed_ms(phase_started)
        phase_started = time.monotonic()
        _require_adapter("launch", job_id)
        timings["launch_ms"] = telemetry.elapsed_ms(phase_started)
        phase_started = time.monotonic()
        runtime_evidence = _readiness(job_id)
        timings["readiness_ms"] = telemetry.elapsed_ms(phase_started)
        if not runtime_evidence.get("ready"):
            reason = runtime_evidence.get("fatal_reason") or "candidate runtime did not become ready"
            raise RuntimeError(str(reason))
        phase_started = time.monotonic()
        endpoint_results = [_probe_endpoint(binding, protocol) for binding in bindings]
        timings["probe_ms"] = telemetry.elapsed_ms(phase_started)
        result = {
            "id": candidate_id,
            "family": family,
            "strategy": strategy,
            "candidate_spec": description.to_dict(),
            "resource_inventory_id": inventory.inventory_id,
            "runtime_arguments": list(runtime_arguments),
            "search_epoch_id": epoch.epoch_id,
            "search_epoch_generation": epoch.generation,
            "endpoint_bindings": bindings,
            "endpoints": endpoint_results,
            "all_pass": bool(endpoint_results) and all(item["status"] == "PASS" for item in endpoint_results),
            "runtime": runtime_evidence,
        }
        if protocol.protocol != "tls13":
            result["protocol"] = protocol.protocol
        _atomic_json(result_path, result)
        return EX_OK
    except (
        OSError,
        ValueError,
        RuntimeError,
        request.RequestError,
        endpoint_epoch.EndpointEpochError,
    ) as exc:
        if runtime_evidence is None:
            readiness_path = runtime_dir(job_id) / "readiness.json"
            if readiness_path.is_file():
                try:
                    runtime_evidence = json.loads(readiness_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    runtime_evidence = None
        _atomic_json(
            result_path,
            _error_result(
                candidate_id,
                family,
                strategy,
                runtime_evidence,
                str(exc),
                description,
                inventory,
                runtime_arguments,
                epoch,
            ),
        )
        return EX_OK
    finally:
        cleanup_started = time.monotonic()
        try:
            completed = _adapter("cleanup", job_id, timeout=15)
            if completed.returncode != 0:
                cleanup_error = (completed.stderr or completed.stdout).strip() or "candidate cleanup failed"
        except RuntimeError as exc:
            cleanup_error = str(exc)
        timings["cleanup_ms"] = telemetry.elapsed_ms(cleanup_started)
        timings["total_ms"] = telemetry.elapsed_ms(total_started)
        if result_path.is_file():
            try:
                current = json.loads(result_path.read_text(encoding="utf-8"))
                current["timing"] = timings
                if cleanup_error:
                    current["cleanup_error"] = cleanup_error
                    current["all_pass"] = False
                outcome = (
                    "pass"
                    if current.get("all_pass") is True
                    else ("error" if current.get("error") is True else "fail")
                )
                try:
                    telemetry.record(
                        job_dir(job_id),
                        "candidate_runtime",
                        int(timings["total_ms"]),
                        candidate_id=candidate_id,
                        protocol=(description.protocol if description is not None else ""),
                        outcome=outcome,
                        details={
                            "search_epoch_id": "" if epoch is None else epoch.epoch_id,
                            "phases": timings,
                        },
                    )
                except telemetry.TelemetryError as exc:
                    current["telemetry_error"] = str(exc)
                    current["error"] = True
                    current["all_pass"] = False
                _atomic_json(result_path, current)
            except (OSError, json.JSONDecodeError):
                pass


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in {8, 9} or args[0] != "run":
        raise ValueError(
            "candidate requires: run JOB ENDPOINTS RESULT ID FAMILY STRATEGY "
            "USE_HOSTLIST [SPEC]"
        )
    return run_candidate(*args[1:])
