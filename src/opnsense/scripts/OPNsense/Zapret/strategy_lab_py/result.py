"""Python-owned Strategy Lab final profile replay and shortlist publication."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from . import candidate, endpoint_epoch, state as state_persistence

EX_OK = 0
JOB_RE = re.compile(r"^job\.[A-Za-z0-9]+$")
DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9-]+$")
PROFILE_REPLAY_ATTEMPTS = 3


class ResultError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProfileContract:
    protocol: str
    protocol_rank: int
    transport: str
    port: int
    l7: str | None


CONTRACTS = {
    "tls13": ProfileContract("tls13", 0, "tcp", 443, "tls"),
    "tls12": ProfileContract("tls12", 1, "tcp", 443, "tls"),
    "http": ProfileContract("http", 2, "tcp", 80, "http"),
    "quic": ProfileContract("quic", 3, "udp", 443, "quic"),
}


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ResultError("invalid Strategy Lab job id")
    return jobs_dir() / job_id


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResultError(f"Strategy Lab JSON is unreadable: {path}") from exc


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
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


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(name)
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


def _valid_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.version == 4 and str(address) == value


def _valid_domain(value: str) -> bool:
    if not value or len(value) > 253 or _valid_ipv4(value):
        return False
    labels = value.split(".")
    if len(labels) < 2:
        return False
    for label in labels:
        if not 1 <= len(label) <= 63 or not DOMAIN_LABEL_RE.fullmatch(label):
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return any(character.isalpha() for character in labels[-1])


def _valid_port(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 65535


def contract(protocol: str, port: int) -> ProfileContract:
    if protocol == "udp":
        if not _valid_port(port):
            raise ResultError("invalid generic UDP port")
        return ProfileContract("udp", 4, "udp", port, None)
    item = CONTRACTS.get(protocol)
    if item is None or port != item.port:
        raise ResultError(f"invalid Strategy Lab profile protocol/port: {protocol}/{port}")
    return item


def _selector_addresses(value: str) -> list[str]:
    if not value:
        raise ResultError("generic UDP selector addresses are unavailable")
    addresses = value.split(",")
    if not addresses or any(not _valid_ipv4(address) for address in addresses):
        raise ResultError("generic UDP selector addresses are invalid")
    return addresses


def selector_for(target: str, target_type: str, protocol: str, addresses: str = "") -> str:
    if target_type == "ip":
        if not _valid_ipv4(target):
            raise ResultError("invalid IPv4 target")
        return f"--ipset-ip={target}"
    if target_type != "domain" or not _valid_domain(target):
        raise ResultError("invalid domain target")
    if protocol == "udp":
        return "--ipset-ip=" + ",".join(_selector_addresses(addresses))
    return f"--hostlist-domains={target}"


def _fragment_line_allowed(line: str) -> bool:
    if not line or line == "--new" or line.startswith("--filter-"):
        return False
    if line.startswith((
        "--port=", "--lua-init=", "--sockarg=", "--user=", "--uid=", "--gid=",
        "--daemon", "--pidfile=", "--qnum=", "--bind-", "--socket=",
        "--hostlist", "--ipset",
    )):
        return False
    stripped = line.lstrip()
    return not (stripped.startswith("<HOSTLIST:") or stripped.startswith("<IPSET:"))


def build_profile(target: str, target_type: str, protocol: str, port: int, addresses: str, strategy: str) -> str:
    spec = contract(protocol, port)
    selector = selector_for(target, target_type, protocol, addresses)
    fragment_lines = [line for line in strategy.splitlines() if line]
    if not fragment_lines or any(not _fragment_line_allowed(line) for line in fragment_lines):
        raise ResultError("Strategy Lab candidate fragment is not publishable")
    lines = [f"--filter-{spec.transport}={spec.port}"]
    if spec.l7:
        lines.append(f"--filter-l7={spec.l7}")
    lines.extend([selector, *fragment_lines])
    profile = "\n".join(lines) + "\n"
    validate_profile(target, target_type, protocol, port, addresses, profile)
    return profile


def validate_profile(target: str, target_type: str, protocol: str, port: int, addresses: str, profile: str) -> None:
    spec = contract(protocol, port)
    selector = selector_for(target, target_type, protocol, addresses)
    lines = profile.splitlines()
    if not lines or lines.count(selector) != 1:
        raise ResultError("Strategy Lab profile target selector is invalid")
    selectors = [line for line in lines if line.startswith("--hostlist-domains=") or line.startswith("--ipset-ip=")]
    if selectors != [selector]:
        raise ResultError("Strategy Lab profile contains an unexpected target selector")
    expected_filter = f"--filter-{spec.transport}={spec.port}"
    filters = [line for line in lines if line.startswith("--filter-tcp=") or line.startswith("--filter-udp=")]
    if filters != [expected_filter]:
        raise ResultError("Strategy Lab profile transport filter is invalid")
    l7_filters = [line for line in lines if line.startswith("--filter-l7=")]
    if spec.l7 is None:
        if l7_filters:
            raise ResultError("generic UDP profile must not contain an L7 filter")
    elif l7_filters != [f"--filter-l7={spec.l7}"]:
        raise ResultError("Strategy Lab profile L7 filter is invalid")
    for prefix in ("--in-range=", "--out-range="):
        ranges = [line.removeprefix(prefix) for line in lines if line.startswith(prefix)]
        if len(ranges) > 1 or any(
            not value or any(character.isspace() for character in value)
            for value in ranges
        ):
            raise ResultError("Strategy Lab profile range is invalid")
    if not any(line.startswith("--lua-desync=") for line in lines):
        raise ResultError("Strategy Lab profile contains no desynchronization directive")
    for line in lines:
        if line == "--new" or line.lstrip().startswith(("<HOSTLIST:", "<IPSET:")):
            raise ResultError("Strategy Lab profile contains a forbidden separator or placeholder")
        if line.startswith((
            "--port=", "--lua-init=", "--sockarg=", "--user=", "--uid=", "--gid=",
            "--daemon", "--pidfile=", "--qnum=", "--bind-", "--socket=",
        )):
            raise ResultError("Strategy Lab profile contains runtime-only arguments")


def _selected_addresses(source: dict[str, Any]) -> str:
    values: list[str] = []
    for item in source.get("endpoints") if isinstance(source.get("endpoints"), list) else []:
        if isinstance(item, dict):
            value = item.get("selected_ip")
            if isinstance(value, str) and value and value not in values:
                values.append(value)
    for attempt in source.get("attempts") if isinstance(source.get("attempts"), list) else []:
        if not isinstance(attempt, dict):
            continue
        for item in attempt.get("endpoints") if isinstance(attempt.get("endpoints"), list) else []:
            if isinstance(item, dict):
                value = item.get("selected_ip")
                if isinstance(value, str) and value and value not in values:
                    values.append(value)
    return ",".join(sorted(values))


def _decorate(source: dict[str, Any], spec: ProfileContract) -> dict[str, Any]:
    result = dict(source)
    strategy = result.get("strategy")
    if not isinstance(strategy, str):
        raise ResultError("Strategy Lab candidate strategy is invalid")
    line_count = result.get("line_count")
    character_count = result.get("character_count")
    result.update(
        protocol=spec.protocol,
        protocol_rank=spec.protocol_rank,
        transport=spec.transport,
        port=spec.port,
        l7=spec.l7,
        selector_addresses=_selected_addresses(source),
        line_count=line_count if isinstance(line_count, int) and not isinstance(line_count, bool) else len([line for line in strategy.splitlines() if line]),
        character_count=character_count if isinstance(character_count, int) and not isinstance(character_count, bool) else len(strategy),
    )
    return result


def collect_sources(job: Path, stability: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    candidates = stability.get("candidates")
    if not isinstance(candidates, list):
        raise ResultError("Strategy Lab stability candidates are invalid")
    stable = [item for item in candidates if isinstance(item, dict) and item.get("stable") is True]
    stable.sort(key=lambda item: (int(item.get("line_count", 10**9)), int(item.get("character_count", 10**9)), str(item.get("id", ""))))
    sources = [_decorate(item, CONTRACTS["tls13"]) for item in stable[:3]]
    if mode == "extended":
        extended_path = job / "extended-tcp.json"
        if extended_path.is_file():
            extended = _read_json(extended_path)
            protocols = extended.get("protocols", {}) if isinstance(extended, dict) else {}
            for protocol in ("tls12", "http"):
                node = protocols.get(protocol, {}) if isinstance(protocols, dict) else {}
                working = node.get("working") if isinstance(node, dict) else None
                if isinstance(working, dict):
                    sources.append(_decorate(working, CONTRACTS[protocol]))
        quic_path = job / "quic.json"
        if quic_path.is_file():
            quic = _read_json(quic_path)
            working = quic.get("working") if isinstance(quic, dict) else None
            if isinstance(working, dict):
                sources.append(_decorate(working, CONTRACTS["quic"]))
        udp_path = job / "udp.json"
        if udp_path.is_file():
            udp = _read_json(udp_path)
            if isinstance(udp, dict):
                port = udp.get("port")
                working = udp.get("working")
                if _valid_port(port) and isinstance(working, dict):
                    sources.append(_decorate(working, contract("udp", port)))
    unique: dict[tuple[str, int, str], dict[str, Any]] = {}
    for item in sources:
        key = (str(item["protocol"]), int(item["port"]), str(item["strategy"]))
        if key not in unique:
            unique[key] = item
    result = list(unique.values())
    result.sort(key=lambda item: (int(item["protocol_rank"]), int(item["line_count"]), int(item["character_count"]), str(item.get("id", ""))))
    return result


@contextmanager
def _candidate_environment(spec: ProfileContract, selector: str, payload_path: Path | None) -> Iterator[None]:
    updates = {
        "STRATEGY_LAB_CANDIDATE_PROTOCOL": spec.protocol,
        "STRATEGY_LAB_CANDIDATE_PORT": str(spec.port),
        "STRATEGY_LAB_CANDIDATE_L7": spec.l7 or "-",
        "STRATEGY_LAB_PROFILE_REPLAY_EXACT": "1",
        "STRATEGY_LAB_PROFILE_REPLAY_SELECTOR": selector,
    }
    if payload_path is not None:
        updates["STRATEGY_LAB_UDP_PORT"] = str(spec.port)
        updates["STRATEGY_LAB_UDP_PAYLOAD_FILE"] = str(payload_path)
    previous = {key: os.environ.get(key) for key in updates}
    try:
        os.environ.update(updates)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _attempt_failure(source: dict[str, Any], profile: str, attempt: int, status: int, message: str) -> dict[str, Any]:
    return {
        "id": str(source.get("id", "")), "family": str(source.get("family", "")),
        "strategy": profile, "profile": profile, "protocol": str(source["protocol"]),
        "port": int(source["port"]), "attempt": attempt, "runner_status": status,
        "endpoints": [], "all_pass": False, "profile_exact": False, "message": message,
    }


def _fixture_replay_runner() -> str:
    """Temporary qualification bridge for pre-Patch-7 fixtures; production never sets it."""
    return os.environ.get("STRATEGY_LAB_PROFILE_REPLAY_RUNNER", "")


def _run_fixture_replay(
    runner: str,
    job_id: str,
    endpoints_path: Path,
    result_path: Path,
    source: dict[str, Any],
    profile_path: Path,
    target: str,
    target_type: str,
    spec: ProfileContract,
) -> int:
    try:
        completed = subprocess.run(
            [
                runner, job_id, str(endpoints_path), str(result_path), str(source.get("id", "")),
                str(source.get("family", "")), str(profile_path), target, target_type, spec.protocol,
                str(spec.port), str(source.get("selector_addresses", "")),
            ],
            env=os.environ.copy(),
            timeout=int(os.environ.get("STRATEGY_LAB_PROFILE_REPLAY_ATTEMPT_TIMEOUT", "45")),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 124
    return completed.returncode


def _replay_once(
    job_id: str,
    endpoints_path: Path,
    source: dict[str, Any],
    profile_path: Path,
    target: str,
    target_type: str,
    attempt: int,
    payload_path: Path | None,
    cancel_check: Callable[[], None] | None,
) -> dict[str, Any]:
    if cancel_check is not None:
        cancel_check()
    spec = contract(str(source["protocol"]), int(source["port"]))
    selector = selector_for(target, target_type, spec.protocol, str(source.get("selector_addresses", "")))
    result_path = profile_path.with_name(f"{profile_path.stem}.attempt-{attempt}.json")
    with _candidate_environment(spec, selector, payload_path):
        fixture_runner = _fixture_replay_runner()
        if fixture_runner:
            runner_status = _run_fixture_replay(
                fixture_runner, job_id, endpoints_path, result_path, source, profile_path,
                target, target_type, spec,
            )
        else:
            runner_status = candidate.run_candidate(
                job_id, str(endpoints_path), str(result_path), str(source.get("id", "")),
                str(source.get("family", "")), str(profile_path),
                "1" if target_type == "domain" and spec.protocol != "udp" else "0",
            )
    profile = profile_path.read_text(encoding="utf-8")
    if not result_path.is_file():
        return _attempt_failure(source, profile, attempt, runner_status, "candidate replay produced no result")
    value = _read_json(result_path)
    if not isinstance(value, dict):
        raise ResultError("Strategy Lab profile replay result is invalid")
    value["profile"] = profile
    value["target"] = target
    value["target_type"] = target_type
    value["protocol"] = spec.protocol
    value["port"] = spec.port
    value["profile_exact"] = value.get("strategy") == profile
    value["attempt"] = attempt
    value["runner_status"] = runner_status
    return value


def build_shortlist(job_id: str, stability_path: Path | None = None, shortlist_path: Path | None = None, cancel_check: Callable[[], None] | None = None) -> dict[str, Any]:
    job = job_dir(job_id)
    stability_path = stability_path or job / "stability.json"
    shortlist_path = shortlist_path or job / "shortlist.json"
    status_path = job / "status.json"
    endpoints_path = job / "endpoints.txt"
    if not stability_path.is_file() or not status_path.is_file() or not endpoints_path.is_file() or endpoints_path.stat().st_size <= 0:
        raise ResultError("Strategy Lab final shortlist inputs are unavailable")
    stability = _read_json(stability_path)
    status = _read_json(status_path)
    if not isinstance(stability, dict) or not isinstance(status, dict):
        raise ResultError("Strategy Lab final shortlist inputs are invalid")
    target = status.get("target")
    target_type = status.get("target_type")
    mode = status.get("mode", "standard")
    if not isinstance(target, str) or not isinstance(target_type, str) or mode not in {"standard", "extended"}:
        raise ResultError("Strategy Lab job identity is invalid")
    selector_for(target, target_type, "tls13", "")
    endpoint_values = [
        line.strip()
        for line in endpoints_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    try:
        epoch = endpoint_epoch.load(job, endpoint_values)
    except endpoint_epoch.EndpointEpochError as exc:
        raise ResultError(str(exc)) from exc
    if epoch.target != target or epoch.target_type != target_type:
        raise ResultError("Strategy Lab job target changed after the search epoch was created")
    if stability.get("search_epoch_id") != epoch.epoch_id:
        raise ResultError("Strategy Lab stability evidence belongs to another search epoch")
    work = job / "profile-replay"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    payload = job / "udp-payload.bin"
    payload_path = payload if payload.is_file() else None
    items: list[dict[str, Any]] = []
    for index, source in enumerate(collect_sources(job, stability, mode), 1):
        if cancel_check is not None:
            cancel_check()
        protocol = str(source["protocol"])
        port = int(source["port"])
        if source.get("search_epoch_id") != epoch.epoch_id:
            raise ResultError("Strategy Lab shortlist source belongs to another search epoch")
        addresses = str(source.get("selector_addresses", ""))
        if protocol == "udp" and target_type == "domain":
            try:
                _selector_addresses(addresses)
            except ResultError:
                continue
        strategy = source.get("strategy")
        if not isinstance(strategy, str):
            raise ResultError("Strategy Lab source strategy is invalid")
        profile = build_profile(target, target_type, protocol, port, addresses, strategy)
        profile_path = work / f"{index}.profile.args"
        _atomic_text(profile_path, profile)
        attempts = [
            _replay_once(job_id, endpoints_path, source, profile_path, target, target_type, attempt, payload_path, cancel_check)
            for attempt in range(1, PROFILE_REPLAY_ATTEMPTS + 1)
        ]
        pass_count = sum(1 for item in attempts if item.get("all_pass") is True and item.get("profile_exact") is True)
        endpoint_consistent = all(
            item.get("search_epoch_id") == epoch.epoch_id for item in attempts
        )
        resolved = sorted({
            str(endpoint.get("selected_ip"))
            for replay in attempts if isinstance(replay, dict)
            for endpoint in (replay.get("endpoints") if isinstance(replay.get("endpoints"), list) else [])
            if isinstance(endpoint, dict) and isinstance(endpoint.get("selected_ip"), str) and endpoint.get("selected_ip")
        })
        published = dict(source)
        published.update(
            target=target, target_type=target_type, profile=profile,
            search_epoch_id=epoch.epoch_id, resolved_addresses=resolved,
            profile_replay={
                "attempt_count": len(attempts), "pass_count": pass_count,
                "search_epoch_id": epoch.epoch_id,
                "endpoint_consistent": endpoint_consistent,
                "verified": (
                    len(attempts) == PROFILE_REPLAY_ATTEMPTS
                    and pass_count == PROFILE_REPLAY_ATTEMPTS
                    and endpoint_consistent
                ),
                "results": attempts,
            },
            circular_eligible=protocol == "tls13",
        )
        items.append(published)
    verified = [item for item in items if item["profile_replay"]["verified"] is True]
    verified.sort(key=lambda item: (int(item["protocol_rank"]), int(item["line_count"]), int(item["character_count"]), str(item.get("id", ""))))
    try:
        limit = int(os.environ.get("STRATEGY_LAB_SHORTLIST_LIMIT", "3"))
    except ValueError as exc:
        raise ResultError("invalid Strategy Lab shortlist limit") from exc
    if limit <= 0:
        raise ResultError("invalid Strategy Lab shortlist limit")
    tls13 = [item for item in verified if item["protocol"] == "tls13"][:limit]
    if mode == "extended":
        best: dict[str, dict[str, Any]] = {}
        for item in verified:
            best.setdefault(str(item["protocol"]), item)
        selected = sorted(best.values(), key=lambda item: (int(item["protocol_rank"]), int(item["line_count"]), int(item["character_count"]), str(item.get("id", ""))))[:limit]
    else:
        selected = tls13
    shortlist = {
        "search_epoch_id": epoch.epoch_id,
        "count": len(selected), "items": selected,
        "recommendation": selected[0] if selected else None,
        "circular_count": len(tls13), "circular_items": tls13,
    }
    _atomic_json(shortlist_path, shortlist)
    return shortlist


def circular_eligibility(job_id: str, final_state: str, final_outcome: str) -> tuple[bool, str, int]:
    job = job_dir(job_id)
    status_path = job / "status.json"
    shortlist_path = job / "shortlist.json"
    status = _read_json(status_path)
    if not isinstance(status, dict):
        raise ResultError("Strategy Lab status is invalid")
    shortlist: dict[str, Any] | None = None
    if shortlist_path.is_file():
        value = _read_json(shortlist_path)
        if isinstance(value, dict):
            shortlist = value
    count = 0
    if shortlist is not None:
        raw_count = shortlist.get("circular_count")
        if isinstance(raw_count, int) and not isinstance(raw_count, bool) and raw_count >= 0:
            count = raw_count
        elif isinstance(shortlist.get("circular_items"), list):
            count = len(shortlist["circular_items"])
        elif isinstance(shortlist.get("items"), list):
            count = len(shortlist["items"])
    eligible = False
    reason = "terminal_outcome"
    if final_state != "completed" or final_outcome != "SUCCESS":
        reason = "terminal_outcome"
    elif status.get("target_type") != "domain":
        reason = "domain_required"
    else:
        stages = status.get("stages")
        stage85 = stage90 = False
        if isinstance(stages, list):
            stage85 = any(isinstance(item, dict) and item.get("number") == "85" and item.get("status") == "PASS" for item in stages)
            stage90 = any(isinstance(item, dict) and item.get("number") == "90" and item.get("status") == "PASS" for item in stages)
        restoration = status.get("restoration")
        if not stage85 or not stage90 or not isinstance(restoration, dict) or restoration.get("verified") is not True:
            reason = "restoration_required"
        elif shortlist is None:
            reason = "shortlist_size"
        else:
            raw_items = shortlist.get("circular_items")
            if not isinstance(raw_items, list):
                historical = shortlist.get("items")
                raw_items = historical if isinstance(historical, list) else []
                raw_items = [
                    dict(item, protocol=item.get("protocol", "tls13"), circular_eligible=item.get("circular_eligible", True))
                    for item in raw_items if isinstance(item, dict)
                ]
            valid = 3 <= len(raw_items) <= 5 and all(
                isinstance(item, dict) and item.get("protocol") == "tls13"
                and item.get("circular_eligible") is True
                and isinstance(item.get("id"), str) and bool(item["id"])
                and isinstance(item.get("strategy"), str) and bool(item["strategy"])
                for item in raw_items
            )
            if valid:
                eligible, reason = True, "eligible"
            else:
                reason = "shortlist_size"
    state_persistence.set_circular_eligibility(job_id, str(status_path), eligible, reason, count)
    return eligible, reason, count


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or [])
    if not args:
        raise ResultError("missing Strategy Lab result operation")
    operation, rest = args[0], args[1:]
    if operation == "shortlist" and len(rest) == 1:
        build_shortlist(rest[0])
    elif operation == "eligibility" and len(rest) == 3:
        circular_eligibility(rest[0], rest[1], rest[2])
    else:
        raise ResultError("invalid Strategy Lab result operation")
    return EX_OK
