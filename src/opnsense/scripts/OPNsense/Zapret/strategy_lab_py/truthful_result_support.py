"""Runtime compatibility layer for truthful Strategy Lab protocol/result classification.

This corrective boundary keeps the accepted search/lifecycle architecture intact while
making the production presentation match the evidence that Strategy Lab already owns:

* an authenticated/intercepted HTTP response remains proof that the DPI path worked even
  when the application returns an HTTP 4xx/5xx status;
* QUIC for a bare IPv4 target is skipped before candidate execution because hostname
  verification requires an explicit Host/SNI identity;
* a bare-IPv4 TLS certificate verification failure is recorded as missing service identity
  and a final empty search is reported as a partial result that asks for Host/SNI instead
  of claiming that no working bypass candidate exists.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Sequence

from . import adaptive_validation
from . import extended
from . import orchestrator
from . import probe
from . import protocol_presentation

MARKER_NAME = "tls-host-sni-required"
MARKER_REASON = "tls_identity_requires_host_sni"
QUIC_SKIP_REASON = "host_sni_required"

_installed = False
_host_sni_terminal_context = False


def _service_host(job: Path) -> str:
    try:
        return (job / "service-host").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _marker(job: Path) -> Path:
    return job / MARKER_NAME


def _clear_marker(job: Path) -> None:
    try:
        _marker(job).unlink()
    except FileNotFoundError:
        pass


def mark_bare_ip_tls_identity_requirement(
    job: Path,
    target_type: str,
    baseline: dict[str, Any],
) -> bool:
    """Persist job-local evidence that bare-IP TLS identity could not be verified.

    curl exit 60 means peer-certificate verification failed.  For an IPv4 target without
    an explicit service Host/SNI this is not evidence that DPI bypass is impossible; the
    user has not supplied the service identity needed for a meaningful HTTPS check.
    """
    _clear_marker(job)
    if target_type != "ip" or _service_host(job):
        return False
    endpoints = baseline.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        return False
    failed = [
        item for item in endpoints
        if isinstance(item, dict) and item.get("status") == "FAIL" and item.get("exit_code") == 60
    ]
    if not failed:
        return False
    payload = {
        "reason": MARKER_REASON,
        "curl_exit": 60,
        "endpoints": [str(item.get("endpoint", "")) for item in failed],
    }
    path = _marker(job)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(path, 0o644)
    return True


def _host_sni_required(job: Path) -> bool:
    try:
        value = json.loads(_marker(job).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and value.get("reason") == MARKER_REASON


def terminal_outcome_for(job: Path, outcome: str) -> str:
    if outcome == "NO_CANDIDATE" and _host_sni_required(job):
        return "PARTIAL"
    return outcome


def _http_application_response(
    replay: dict[str, Any],
    protocol: str,
    target_bytes: int,
) -> dict[str, Any] | None:
    """Return accepted evidence for a real intercepted HTTP 4xx/5xx response.

    This intentionally does not special-case 502 or any site.  The transport/TLS/profile
    proof must already be successful, every endpoint must be intercepted, and every curl
    writeout must contain a real HTTP status in the RFC application-response range.
    """
    if protocol not in {"tls13", "tls12", "http"}:
        return None
    if replay.get("all_pass") is not True or replay.get("profile_exact") is not True:
        return None
    endpoints = replay.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        return None

    statuses: list[int] = []
    byte_counts: list[int] = []
    for endpoint in endpoints:
        if not isinstance(endpoint, dict) or endpoint.get("status") != "PASS":
            return None
        firewall = endpoint.get("firewall")
        if not isinstance(firewall, dict) or firewall.get("intercepted") is not True:
            return None
        status, count = adaptive_validation._writeout(endpoint)
        if status is None or count is None or not 100 <= status <= 599 or count < 0:
            return None
        statuses.append(status)
        byte_counts.append(count)

    if not any(status >= 400 for status in statuses):
        return None
    return {
        "classification": "reachable_application_error",
        "accepted": True,
        "target_bytes": target_bytes,
        "bytes_received": min(byte_counts),
        "http_statuses": statuses,
        "reason": "http_application_response",
    }


def install() -> None:
    global _installed
    if _installed:
        return

    original_classify = adaptive_validation.classify_deep_replay

    def classify_deep_replay(
        replay: dict[str, Any], protocol: str, target_bytes: int
    ) -> dict[str, Any]:
        result = original_classify(replay, protocol, target_bytes)
        if result.get("reason") != "http_status_failed":
            return result
        application = _http_application_response(replay, protocol, target_bytes)
        return application if application is not None else result

    adaptive_validation.classify_deep_replay = classify_deep_replay

    original_probe_main = probe.main

    def probe_main(argv: Sequence[str] | None = None) -> int:
        args = list(argv or [])
        status = original_probe_main(args)
        if args[:1] == ["baseline"] and len(args) == 7:
            job = Path(args[5])
            try:
                baseline = probe._load_json(Path(args[6]))
            except Exception:
                _clear_marker(job)
            else:
                mark_bare_ip_tls_identity_requirement(job, args[2], baseline)
        return status

    probe.main = probe_main

    original_quic = extended.quic

    def quic(job_id: str, endpoints_file: str, network_file: str, result_file: str) -> int:
        endpoints = Path(endpoints_file)
        if not extended.JOB_RE.fullmatch(job_id) or not endpoints.is_file():
            return extended.EX_USAGE
        epoch = extended._search_epoch(job_id, endpoints)
        job = extended.job_dir(job_id)
        if epoch.target_type == "ip" and not _service_host(job):
            extended._atomic_json(Path(result_file), {
                "search_epoch_id": epoch.epoch_id,
                "enabled": True,
                "status": "skipped",
                "reason": QUIC_SKIP_REASON,
                "tested": [],
                "working": None,
            })
            return extended.EX_OK
        return original_quic(job_id, endpoints_file, network_file, result_file)

    extended.quic = quic

    original_quic_summary = protocol_presentation._quic_summary

    def quic_summary(language: str, result: dict[str, Any]) -> str:
        if result.get("status") == "skipped" and result.get("reason") == QUIC_SKIP_REASON:
            if language == "ru":
                return "QUIC: ПРОПУЩЕНО — для IPv4-цели требуется Host / SNI"
            return "QUIC: SKIPPED — an IPv4 target requires Host / SNI"
        return original_quic_summary(language, result)

    protocol_presentation._quic_summary = quic_summary

    original_terminal_message = orchestrator.terminal_message
    original_finish = orchestrator.Orchestrator.finish

    def terminal_message(
        language: str,
        mode: str,
        outcome: str,
        canceled: bool,
        count: int = 0,
    ) -> str:
        if _host_sni_terminal_context and outcome == "PARTIAL" and not canceled:
            if language == "ru":
                return (
                    "PARTIAL — TLS-сертификат IPv4-цели нельзя корректно проверить без имени сервиса; "
                    "укажите Host / SNI и повторите проверку."
                )
            return (
                "PARTIAL — The IPv4 target TLS certificate cannot be verified without the service identity; "
                "provide Host / SNI and run the test again."
            )
        return original_terminal_message(language, mode, outcome, canceled, count)

    orchestrator.terminal_message = terminal_message

    def finish(self: orchestrator.Orchestrator, outcome: str, canceled: bool) -> int:
        global _host_sni_terminal_context
        corrected = terminal_outcome_for(self.job_dir, outcome)
        use_context = corrected == "PARTIAL" and outcome == "NO_CANDIDATE"
        previous = _host_sni_terminal_context
        _host_sni_terminal_context = use_context
        try:
            return original_finish(self, corrected, canceled)
        finally:
            _host_sni_terminal_context = previous

    orchestrator.Orchestrator.finish = finish
    _installed = True
