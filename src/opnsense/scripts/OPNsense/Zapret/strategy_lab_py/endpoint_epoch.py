"""Fixed search-epoch endpoint identity and binding evidence."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SEARCH_EPOCH_SCHEMA = 1
SEARCH_EPOCH_FILE = "search-epoch.json"


class EndpointEpochError(RuntimeError):
    """Search-epoch evidence is unavailable or inconsistent."""


def _canonical_ipv4(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise EndpointEpochError(f"invalid search-epoch IPv4 address: {value}") from exc
    if address.version != 4:
        raise EndpointEpochError(f"invalid search-epoch IPv4 address: {value}")
    return str(address)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(name)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o644)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _identity_payload(
    job_id: str,
    generation: int,
    target: str,
    target_type: str,
    bindings: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "schema": SEARCH_EPOCH_SCHEMA,
        "job_id": job_id,
        "generation": generation,
        "target": target,
        "target_type": target_type,
        "bindings": list(bindings),
    }


def _epoch_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "se1-" + hashlib.blake2b(encoded, digest_size=16).hexdigest()


@dataclass(frozen=True)
class SearchEpoch:
    epoch_id: str
    generation: int
    target: str
    target_type: str
    bindings: tuple[dict[str, Any], ...]
    created_at: str
    source: str

    @property
    def endpoints(self) -> tuple[str, ...]:
        return tuple(str(item["endpoint"]) for item in self.bindings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SEARCH_EPOCH_SCHEMA,
            "epoch_id": self.epoch_id,
            "generation": self.generation,
            "target": self.target,
            "target_type": self.target_type,
            "bindings": list(self.bindings),
            "created_at": self.created_at,
            "source": self.source,
        }


def _validated_bindings(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise EndpointEpochError("search-epoch bindings are invalid")
    bindings: list[dict[str, Any]] = []
    seen_endpoints: set[str] = set()
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict):
            raise EndpointEpochError("search-epoch binding is invalid")
        endpoint = item.get("endpoint")
        addresses = item.get("addresses")
        selected = item.get("selected_ip")
        if (
            not isinstance(endpoint, str)
            or not endpoint
            or endpoint in seen_endpoints
            or not isinstance(addresses, list)
            or not addresses
            or not all(isinstance(address, str) for address in addresses)
            or not isinstance(selected, str)
        ):
            raise EndpointEpochError("search-epoch binding is invalid")
        normalized = tuple(dict.fromkeys(_canonical_ipv4(address) for address in addresses))
        selected_ip = _canonical_ipv4(selected)
        if selected_ip not in normalized:
            raise EndpointEpochError("search-epoch selected address is not in its endpoint set")
        seen_endpoints.add(endpoint)
        bindings.append(
            {
                "index": index,
                "endpoint": endpoint,
                "addresses": list(normalized),
                "selected_ip": selected_ip,
            }
        )
    return tuple(bindings)


def create(
    job_dir: Path,
    target: str,
    target_type: str,
    endpoints: Iterable[str],
    baseline_evidence: Iterable[dict[str, Any]],
) -> SearchEpoch:
    """Create a new recorded epoch from one completed Stage-40 resolution."""
    endpoint_values = tuple(endpoints)
    evidence_values = tuple(baseline_evidence)
    if target_type not in {"domain", "ip"} or not target or not endpoint_values:
        raise EndpointEpochError("search-epoch target contract is invalid")
    if len(endpoint_values) != len(evidence_values):
        raise EndpointEpochError("search-epoch evidence does not match the endpoint set")

    raw_bindings: list[dict[str, Any]] = []
    for index, (endpoint, evidence) in enumerate(
        zip(endpoint_values, evidence_values, strict=True), 1
    ):
        if not isinstance(endpoint, str) or not endpoint or not isinstance(evidence, dict):
            raise EndpointEpochError("search-epoch endpoint evidence is invalid")
        if evidence.get("endpoint") != endpoint:
            raise EndpointEpochError("search-epoch endpoint evidence order changed")
        if target_type == "ip":
            addresses = [_canonical_ipv4(endpoint)]
        else:
            dns = evidence.get("dns_a")
            answers = dns.get("answers") if isinstance(dns, dict) else None
            if (
                not isinstance(dns, dict)
                or dns.get("classification") != "pass"
                or not isinstance(answers, list)
                or not answers
                or not all(isinstance(answer, str) for answer in answers)
            ):
                raise EndpointEpochError(
                    f"search-epoch DNS evidence is unavailable for {endpoint}"
                )
            addresses = list(dict.fromkeys(_canonical_ipv4(answer) for answer in answers))
        raw_bindings.append(
            {
                "index": index,
                "endpoint": endpoint,
                "addresses": addresses,
                "selected_ip": addresses[0],
            }
        )
    bindings = _validated_bindings(raw_bindings)

    previous_path = job_dir / SEARCH_EPOCH_FILE
    generation = 1
    if previous_path.is_file():
        previous = load(job_dir)
        generation = previous.generation + 1
    payload = _identity_payload(job_dir.name, generation, target, target_type, bindings)
    epoch = SearchEpoch(
        epoch_id=_epoch_id(payload),
        generation=generation,
        target=target,
        target_type=target_type,
        bindings=bindings,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source="stage40-baseline",
    )
    _atomic_json(previous_path, epoch.to_dict())
    return epoch


def load(job_dir: Path, expected_endpoints: Iterable[str] | None = None) -> SearchEpoch:
    path = job_dir / SEARCH_EPOCH_FILE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EndpointEpochError(f"Strategy Lab search epoch is unreadable: {path}") from exc
    if not isinstance(value, dict) or value.get("schema") != SEARCH_EPOCH_SCHEMA:
        raise EndpointEpochError("Strategy Lab search epoch is invalid")
    generation = value.get("generation")
    target = value.get("target")
    target_type = value.get("target_type")
    epoch_id = value.get("epoch_id")
    created_at = value.get("created_at")
    source = value.get("source")
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or generation <= 0
        or not isinstance(target, str)
        or not target
        or target_type not in {"domain", "ip"}
        or not isinstance(epoch_id, str)
        or not epoch_id.startswith("se1-")
        or not isinstance(created_at, str)
        or not created_at
        or source != "stage40-baseline"
    ):
        raise EndpointEpochError("Strategy Lab search epoch identity is invalid")
    bindings = _validated_bindings(value.get("bindings"))
    payload = _identity_payload(job_dir.name, generation, target, target_type, bindings)
    if _epoch_id(payload) != epoch_id:
        raise EndpointEpochError("Strategy Lab search epoch identity does not match its bindings")
    epoch = SearchEpoch(
        epoch_id=epoch_id,
        generation=generation,
        target=target,
        target_type=target_type,
        bindings=bindings,
        created_at=created_at,
        source=source,
    )
    if expected_endpoints is not None and tuple(expected_endpoints) != epoch.endpoints:
        raise EndpointEpochError("Strategy Lab candidate endpoints do not match the search epoch")
    return epoch
