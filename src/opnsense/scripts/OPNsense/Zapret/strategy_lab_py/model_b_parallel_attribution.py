"""Correct route-attribution semantics for controlled parallel Model-B probes.

The `_20` parallel harness required curl write-out to report the connected remote IP and
local source port even for failed/blocked probes.  That is too strict: when the TCP/TLS
connection never establishes, curl may have no connected socket values to report although
IPFW has already observed the exact source-port-qualified packet.

For successful candidate classification the observed remote IP and local port remain
mandatory.  For route attribution of a failed probe, the executed curl command must prove
the exact controlled --local-port and --resolve binding, and the exact IPFW rule must show
counter growth.  The rule itself matches source port + pinned destination IPv4 + tcp/443.
"""

from __future__ import annotations

import time
from typing import Any, Sequence

from . import model_b, model_b_parallel, request


def _option_value(command: Sequence[str], option: str) -> str | None:
    indexes = [index for index, value in enumerate(command) if value == option]
    if len(indexes) != 1:
        return None
    index = indexes[0]
    if index + 1 >= len(command):
        return None
    return str(command[index + 1])


def _command_binding_matches(
    execution: request.CommandResult,
    endpoint: str,
    selected_ip: str,
    local_port: int,
) -> tuple[bool, bool]:
    source_port_match = _option_value(execution.command, "--local-port") == str(local_port)
    resolve_match = _option_value(execution.command, "--resolve") == f"{endpoint}:443:{selected_ip}"
    return source_port_match, resolve_match


def _probe_endpoint(
    slot: model_b.Slot,
    binding: dict[str, Any],
    wan: str,
    local_port: int,
) -> dict[str, Any]:
    endpoint = str(binding["endpoint"])
    selected_ip = str(binding["selected_ip"])
    if not model_b._try_adapter("source-port-free", str(local_port)):
        raise model_b_parallel.ModelBParallelError(f"controlled source port is already in use: {local_port}")

    dispatch_started = time.monotonic()
    model_b._require_adapter(
        "route-add-source",
        str(slot.rule),
        str(slot.port),
        selected_ip,
        wan,
        "tcp",
        "443",
        str(local_port),
    )
    dispatch_ms = round((time.monotonic() - dispatch_started) * 1000)
    result: dict[str, Any] | None = None
    route_cleanup_ok = False
    try:
        before_packets, before_bytes = model_b._counter(slot.rule)
        probe_started = time.monotonic()
        execution = model_b_parallel._parallel_curl_request(endpoint, selected_ip, local_port)
        probe_ms = round((time.monotonic() - probe_started) * 1000)
        after_packets, after_bytes = model_b._counter(slot.rule)

        remote_ip = model_b_parallel._last_match(model_b_parallel.REMOTE_IP_RE, execution.stdout)
        observed_local_port_raw = model_b_parallel._last_match(model_b_parallel.LOCAL_PORT_RE, execution.stdout)
        observed_local_port = int(observed_local_port_raw) if observed_local_port_raw else None
        intercepted = after_packets > before_packets
        endpoint_match = remote_ip == selected_ip
        local_port_match = observed_local_port == local_port
        command_source_port_match, command_endpoint_match = _command_binding_matches(
            execution, endpoint, selected_ip, local_port
        )

        classification = (
            "pass"
            if request.curl_exit(execution) == 0 and endpoint_match and intercepted and local_port_match
            else "fail"
        )
        result = {
            "slot": slot.name,
            "rule": slot.rule,
            "port": slot.port,
            "endpoint": endpoint,
            "selected_ip": selected_ip,
            "requested_local_port": local_port,
            "observed_local_port": observed_local_port,
            "local_port_match": local_port_match,
            "command_source_port_match": command_source_port_match,
            "source_port_selector": True,
            "dispatch_ms": dispatch_ms,
            "probe_ms": probe_ms,
            "counter_before": {"packets": before_packets, "bytes": before_bytes},
            "counter_after": {"packets": after_packets, "bytes": after_bytes},
            "intercepted": intercepted,
            "remote_ip": remote_ip,
            "endpoint_match": endpoint_match,
            "command_endpoint_match": command_endpoint_match,
            "classification": classification,
            "execution": execution.evidence(),
        }
    finally:
        route_cleanup_ok = model_b._try_adapter("route-del", str(slot.rule))

    if result is None:
        raise model_b_parallel.ModelBParallelError("Model B parallel endpoint probe produced no result")

    result["route_cleanup_ok"] = route_cleanup_ok
    result["attribution_ok"] = bool(
        result["source_port_selector"]
        and result["command_source_port_match"]
        and result["command_endpoint_match"]
        and result["intercepted"]
        and route_cleanup_ok
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    original_probe_endpoint = model_b_parallel._probe_endpoint
    model_b_parallel._probe_endpoint = _probe_endpoint
    try:
        return model_b_parallel.main(argv)
    finally:
        model_b_parallel._probe_endpoint = original_probe_endpoint
