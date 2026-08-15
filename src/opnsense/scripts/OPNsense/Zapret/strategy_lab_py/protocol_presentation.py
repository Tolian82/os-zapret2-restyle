"""Human-facing RU/EN presentation for Strategy Lab protocol evidence."""

from __future__ import annotations

from typing import Any


class ProtocolPresentationError(ValueError):
    pass


def _tested_ids(result: dict[str, Any]) -> list[str]:
    tested = result.get("tested", [])
    if not isinstance(tested, list):
        raise ProtocolPresentationError("protocol tested set is invalid")
    ids: list[str] = []
    for item in tested:
        if not isinstance(item, dict):
            raise ProtocolPresentationError("protocol tested item is invalid")
        candidate_id = item.get("id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ProtocolPresentationError("protocol tested candidate id is invalid")
        ids.append(candidate_id)
    return ids


def _ids_text(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "—"


def stage30_message(
    language: str,
    mode: str,
    quic_enabled: bool,
    network: dict[str, Any],
) -> str:
    """Present measured connectivity separately from the QUIC execution choice."""
    if language not in {"en", "ru"} or mode not in {"standard", "extended"}:
        raise ProtocolPresentationError("invalid Strategy Lab presentation context")
    ipv4 = network.get("ipv4")
    ipv6 = network.get("ipv6")
    quic = network.get("quic_ipv4")
    if ipv4 != "available" or ipv6 not in {"available", "unavailable"} or quic not in {"available", "closed"}:
        raise ProtocolPresentationError("unexpected network capability classification")

    ru = language == "ru"
    if ru:
        parts = ["PASS — IPv4 доступен"]
        parts.append("IPv6 доступен" if ipv6 == "available" else "IPv6 недоступен")
        parts.append("QUIC открыт" if quic == "available" else "QUIC закрыт")
        if mode != "extended":
            parts.append("подбор QUIC-стратегий выполняется только в расширенном режиме")
        else:
            parts.append(
                "подбор QUIC-стратегий включён" if quic_enabled
                else "подбор QUIC-стратегий отключён"
            )
        if ipv6 == "unavailable":
            parts.append("проверки IPv6 исключены")
        return "; ".join(parts) + "."

    parts = ["PASS — IPv4 is available"]
    parts.append("IPv6 is available" if ipv6 == "available" else "IPv6 is unavailable")
    parts.append("QUIC is open" if quic == "available" else "QUIC is blocked")
    if mode != "extended":
        parts.append("QUIC strategy search runs only in Extended mode")
    else:
        parts.append(
            "QUIC strategy search is enabled" if quic_enabled
            else "QUIC strategy search is disabled"
        )
    if ipv6 == "unavailable":
        parts.append("IPv6 tests are excluded")
    return "; ".join(parts) + "."


def _quic_summary(language: str, result: dict[str, Any]) -> str:
    ru = language == "ru"
    status = result.get("status")
    if status == "skipped":
        if result.get("reason") == "disabled":
            return "QUIC: подбор стратегий отключён" if ru else "QUIC: strategy search is disabled"
        return "QUIC: проверка не выполнялась" if ru else "QUIC: testing was not performed"
    if status not in {"working", "not_found"}:
        raise ProtocolPresentationError("unexpected QUIC result status")
    ids = _tested_ids(result)
    count = len(ids)
    if status == "working":
        working = result.get("working")
        working_id = working.get("id") if isinstance(working, dict) else None
        if not isinstance(working_id, str) or not working_id:
            raise ProtocolPresentationError("working QUIC result is invalid")
        if ru:
            return f"QUIC: проверено стратегий {count} [{_ids_text(ids)}]; рабочая стратегия: {working_id}"
        return f"QUIC: {count} strategies tested [{_ids_text(ids)}]; working strategy: {working_id}"
    if ru:
        return f"QUIC: проверено стратегий {count} [{_ids_text(ids)}]; рабочая стратегия не найдена"
    return f"QUIC: {count} strategies tested [{_ids_text(ids)}]; no working strategy found"


def _udp_summary(language: str, result: dict[str, Any]) -> str:
    ru = language == "ru"
    status = result.get("status")
    if status == "skipped":
        return "UDP: проверка не настроена" if ru else "UDP: testing is not configured"
    if status not in {"working", "not_found"}:
        raise ProtocolPresentationError("unexpected UDP result status")

    port = result.get("port")
    payload_bytes = result.get("payload_bytes")
    control = result.get("control")
    if (
        isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535
        or isinstance(payload_bytes, bool) or not isinstance(payload_bytes, int) or not 1 <= payload_bytes <= 4096
        or not isinstance(control, dict)
    ):
        raise ProtocolPresentationError("configured UDP evidence is invalid")
    reply_observed = control.get("reply_observed")
    attempts = control.get("attempts")
    if not isinstance(reply_observed, bool) or not isinstance(attempts, list) or not attempts:
        raise ProtocolPresentationError("UDP control evidence is invalid")
    selected_ips: list[str] = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise ProtocolPresentationError("UDP control attempt is invalid")
        selected_ip = attempt.get("selected_ip")
        if isinstance(selected_ip, str) and selected_ip and selected_ip not in selected_ips:
            selected_ips.append(selected_ip)
    if not selected_ips:
        raise ProtocolPresentationError("UDP control endpoints are unavailable")

    ids = _tested_ids(result)
    count = len(ids)
    if ru:
        control_text = (
            "контрольный ответ получен" if reply_observed
            else "контрольный ответ не получен (это не означает, что порт закрыт)"
        )
        prefix = (
            f"UDP: порт {port}; payload {payload_bytes} байт; endpoints {', '.join(selected_ips)}; "
            f"{control_text}; проверено стратегий {count} [{_ids_text(ids)}]"
        )
        if status == "working":
            working = result.get("working")
            working_id = working.get("id") if isinstance(working, dict) else None
            if not isinstance(working_id, str) or not working_id:
                raise ProtocolPresentationError("working UDP result is invalid")
            return f"{prefix}; рабочая стратегия: {working_id}"
        return f"{prefix}; рабочая стратегия не найдена"

    control_text = (
        "control reply observed" if reply_observed
        else "no control reply observed (this does not mean the port is closed)"
    )
    prefix = (
        f"UDP: port {port}; payload {payload_bytes} bytes; endpoints {', '.join(selected_ips)}; "
        f"{control_text}; {count} strategies tested [{_ids_text(ids)}]"
    )
    if status == "working":
        working = result.get("working")
        working_id = working.get("id") if isinstance(working, dict) else None
        if not isinstance(working_id, str) or not working_id:
            raise ProtocolPresentationError("working UDP result is invalid")
        return f"{prefix}; working strategy: {working_id}"
    return f"{prefix}; no working strategy found"


def stage80_message(language: str, quic: dict[str, Any], udp: dict[str, Any]) -> str:
    if language not in {"en", "ru"}:
        raise ProtocolPresentationError("invalid Strategy Lab language")
    quic_text = _quic_summary(language, quic)
    udp_text = _udp_summary(language, udp)
    if language == "ru":
        return f"PASS — Расширенная проверка завершена. {quic_text}. {udp_text}."
    return f"PASS — Extended testing completed. {quic_text}. {udp_text}."
