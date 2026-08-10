"""Experiment-only Model-B warm-worker coexistence harness.

Model B is not a production Strategy Lab execution model.  This module consumes one
completed Model-A reference job, starts three exact reference candidates as distinct warm
dvtws2 workers, routes probes to one worker at a time, and records equivalence/isolation
measurements.  The lifecycle lock and normal-service restoration are owned by the narrow
shell worker that invokes this module.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import candidate_spec, request, resources

EX_OK = 0
EX_USAGE = 64
SCHEMA = 1
MODEL = "B-warm-worker-coexistence"
JOB_RE = re.compile(r"^job\.[A-Za-z0-9]{6,64}$")
REMOTE_IP_RE = re.compile(r"(?:^|\s)remote_ip=([^\s]+)")


class ModelBExperimentError(RuntimeError):
    """Model-B input or experiment evidence is invalid."""


@dataclass(frozen=True)
class Slot:
    name: str
    port: int
    rule: int
    role: str


SLOTS = (
    Slot("pass", 9990, 19128, "known-pass-repeated-blob-free"),
    Slot("builtin", 9991, 19129, "known-fail-builtin"),
    Slot("external", 9992, 19130, "known-fail-external-d8"),
)


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ModelBExperimentError(f"invalid Strategy Lab reference job id: {job_id}")
    return jobs_dir() / job_id


def session_dir() -> Path:
    raw = os.environ.get("STRATEGY_LAB_MODEL_B_SESSION_DIR", "")
    if not raw:
        raise ModelBExperimentError("Model B session directory is unavailable")
    return Path(raw)


def adapter_path() -> Path:
    return Path(
        os.environ.get(
            "STRATEGY_LAB_MODEL_B_SYSTEM_ADAPTER",
            str(Path(__file__).resolve().parent.parent / "strategy_lab_model_b_adapter.sh"),
        )
    )


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelBExperimentError(f"Model B JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ModelBExperimentError(f"Model B JSON root is invalid: {path}")
    return value


def _adapter(action: str, *args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    adapter = adapter_path()
    if not adapter.is_file():
        raise ModelBExperimentError(f"Model B system adapter is unavailable: {adapter}")
    shell = os.environ.get("STRATEGY_LAB_SH_BIN", "/bin/sh")
    try:
        return subprocess.run(
            [shell, str(adapter), action, *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ModelBExperimentError(f"Model B system adapter timed out during {action}") from exc
    except OSError as exc:
        raise ModelBExperimentError(f"Model B system adapter failed during {action}: {exc}") from exc


def _require_adapter(action: str, *args: str, timeout: int = 15) -> str:
    result = _adapter(action, *args, timeout=timeout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ModelBExperimentError(
            f"Model B system adapter {action} failed" + (f": {detail}" if detail else "")
        )
    return result.stdout


def _try_adapter(action: str, *args: str, timeout: int = 15) -> bool:
    try:
        return _adapter(action, *args, timeout=timeout).returncode == 0
    except ModelBExperimentError:
        return False


def _stage_paths(job: Path) -> Iterable[Path]:
    for path in sorted((job / "family-screening").glob("*.json")):
        yield path
    for path in sorted((job / "parameter-expansion").glob("*.json")):
        yield path
    for path in sorted((job / "stability").glob("*-attempts/*.json")):
        yield path
    for path in sorted((job / "profile-replay").glob("*.deep.json")):
        yield path


def _classification(value: dict[str, Any]) -> str:
    if value.get("timeout") is True:
        return "timeout"
    if value.get("error") is True:
        return "error"
    return "pass" if value.get("all_pass") is True else "fail"


def _reference_candidates(job: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    raw_records: list[tuple[Path, dict[str, Any]]] = []
    for path in _stage_paths(job):
        value = _load_json(path)
        spec = value.get("candidate_spec")
        if not isinstance(spec, dict):
            continue
        spec_id = spec.get("spec_id")
        if not isinstance(spec_id, str) or not spec_id:
            continue
        counts[spec_id] = counts.get(spec_id, 0) + 1
        raw_records.append((path, value))
    for path, value in raw_records:
        spec = value["candidate_spec"]
        records.append(
            {
                "path": str(path.relative_to(job)),
                "value": value,
                "spec": spec,
                "spec_id": spec["spec_id"],
                "classification": _classification(value),
                "repetitions": counts[spec["spec_id"]],
            }
        )
    return records


def _resource_classes(record: dict[str, Any]) -> set[str]:
    raw = record["spec"].get("resource_classes")
    return {item for item in raw if isinstance(item, str)} if isinstance(raw, list) else set()


def _compatible(record: dict[str, Any]) -> bool:
    spec = record["spec"]
    return (
        spec.get("protocol") == "tls13"
        and spec.get("transport") == "tcp"
        and spec.get("port") == 443
        and spec.get("l3") == "ipv4"
    )


def _select_reference_set(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    chosen: dict[str, dict[str, Any]] = {}
    for record in records:
        if not _compatible(record):
            continue
        classes = _resource_classes(record)
        ranges = record["spec"].get("ranges") if isinstance(record["spec"].get("ranges"), dict) else {}
        if (
            "pass" not in chosen
            and record["classification"] == "pass"
            and "blob-free" in classes
            and record["repetitions"] >= 3
        ):
            chosen["pass"] = record
        if (
            "builtin" not in chosen
            and record["classification"] == "fail"
            and "builtin" in classes
        ):
            chosen["builtin"] = record
        if (
            "external" not in chosen
            and record["classification"] == "fail"
            and "external" in classes
            and ranges.get("out") == "-d8"
        ):
            chosen["external"] = record
    missing = [slot.name for slot in SLOTS if slot.name not in chosen]
    if missing:
        raise ModelBExperimentError(
            "reference job does not contain the required Model B comparison corpus: "
            + ", ".join(missing)
        )
    return chosen


def _reference_contract(job: Path) -> tuple[dict[str, Any], resources.ResourceInventory, dict[str, Any], dict[str, dict[str, Any]]]:
    status = _load_json(job / "status.json")
    if status.get("state") != "completed" or status.get("outcome") != "SUCCESS":
        raise ModelBExperimentError("Model B requires a completed successful Model A reference job")
    if status.get("mode") != "standard" or status.get("target_type") != "domain":
        raise ModelBExperimentError("Model B first coexistence experiment requires a Standard domain reference")
    restoration = status.get("restoration") if isinstance(status.get("restoration"), dict) else {}
    if not (
        restoration.get("verified") is True
        and restoration.get("temporary_runtime_clean") is True
        and restoration.get("strategy_unchanged") is True
    ):
        raise ModelBExperimentError("Model A reference restoration evidence is not verified")
    inventory = resources.load_inventory(job / "resource-inventory.json")
    epoch = _load_json(job / "search-epoch.json")
    bindings = epoch.get("bindings")
    if not isinstance(bindings, list) or len(bindings) != 1 or not isinstance(bindings[0], dict):
        raise ModelBExperimentError("Model B first coexistence experiment requires one pinned endpoint")
    selected = bindings[0].get("selected_ip")
    endpoint = bindings[0].get("endpoint")
    if not isinstance(selected, str) or not selected or not isinstance(endpoint, str) or not endpoint:
        raise ModelBExperimentError("Model A reference endpoint binding is invalid")
    candidates = _select_reference_set(_reference_candidates(job))
    return status, inventory, {"endpoint": endpoint, "selected_ip": selected, "epoch_id": epoch.get("epoch_id")}, candidates


def _current_inventory(reference: resources.ResourceInventory) -> resources.ResourceInventory:
    current = resources.snapshot_inventory(Path(reference.lua_root), Path(reference.fake_root))
    if current.inventory_id != reference.inventory_id:
        raise ModelBExperimentError(
            "installed Zapret2 resources differ from the Model A reference inventory"
        )
    return current


def _write_worker_runtime(slot: Slot, record: dict[str, Any], inventory: resources.ResourceInventory, endpoint: str) -> dict[str, Any]:
    root = session_dir() / "workers" / slot.name
    root.mkdir(parents=True, exist_ok=True)
    spec = candidate_spec.CandidateSpec.from_dict(record["spec"])
    hostlist: Path | None = None
    if spec.target_binding:
        hostlist = root / "hostlist.txt"
        hostlist.write_text(endpoint + "\n", encoding="utf-8")
        os.chmod(hostlist, 0o644)
    arguments = spec.render_runtime_arguments(inventory, divert_port=slot.port, hostlist_path=hostlist)
    args_path = root / "dvtws.args"
    args_path.write_text("".join(f"{item}\n" for item in arguments), encoding="utf-8")
    os.chmod(args_path, 0o644)
    return {
        "slot": slot.name,
        "role": slot.role,
        "port": slot.port,
        "rule": slot.rule,
        "candidate_id": spec.candidate_id,
        "spec_id": spec.spec_id,
        "family": spec.family,
        "expected_classification": record["classification"],
        "resource_classes": list(record["spec"].get("resource_classes", [])),
        "out_range": (record["spec"].get("ranges") or {}).get("out"),
        "reference_path": record["path"],
        "runtime_arguments": list(arguments),
    }


def _snapshot(slot: Slot) -> dict[str, Any]:
    raw = _require_adapter("snapshot", slot.name, str(slot.port))
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelBExperimentError(f"invalid worker snapshot for {slot.name}") from exc
    if not isinstance(value, dict):
        raise ModelBExperimentError(f"invalid worker snapshot for {slot.name}")
    return value


def _wait_pool_ready(slots: Sequence[Slot]) -> dict[str, dict[str, Any]]:
    stable = {slot.name: 0 for slot in slots}
    latest: dict[str, dict[str, Any]] = {}
    for attempt in range(1, 5):
        all_ready = True
        for slot in slots:
            snap = _snapshot(slot)
            latest[slot.name] = snap
            good = bool(snap.get("process_identity")) and bool(snap.get("socket_ready")) and bool(snap.get("log_clean"))
            stable[slot.name] = stable[slot.name] + 1 if good else 0
            snap["stable_checks"] = stable[slot.name]
            snap["ready"] = stable[slot.name] >= 2
            if not snap["ready"]:
                all_ready = False
        if all_ready:
            return latest
        if attempt < 4:
            time.sleep(1)
    return latest


def _remote_ip(stdout: str) -> str:
    match = None
    for match in REMOTE_IP_RE.finditer(stdout):
        pass
    return "" if match is None else match.group(1)


def _counter(rule: int) -> tuple[int, int]:
    raw = _require_adapter("counter", str(rule)).strip().split()
    if len(raw) != 2:
        raise ModelBExperimentError(f"invalid Model B counter evidence for rule {rule}")
    try:
        return int(raw[0]), int(raw[1])
    except ValueError as exc:
        raise ModelBExperimentError(f"invalid Model B counter evidence for rule {rule}") from exc


def _inactive_rules_absent(selected: Slot, slots: Sequence[Slot]) -> bool:
    for slot in slots:
        if slot == selected:
            continue
        if _try_adapter("rule-present", str(slot.rule)):
            return False
    return True


def _probe(slot: Slot, slots: Sequence[Slot], endpoint: str, selected_ip: str, wan: str) -> dict[str, Any]:
    dispatch_started = time.monotonic()
    if not _inactive_rules_absent(slot, slots):
        raise ModelBExperimentError("an inactive Model B route is unexpectedly present")
    _require_adapter(
        "route-add", str(slot.rule), str(slot.port), selected_ip, wan, "tcp", "443"
    )
    dispatch_ms = round((time.monotonic() - dispatch_started) * 1000)
    try:
        before_packets, before_bytes = _counter(slot.rule)
        probe_started = time.monotonic()
        execution = request.curl_request(
            endpoint, scheme="https", tls_version="1.3", bound_ip=selected_ip
        )
        probe_ms = round((time.monotonic() - probe_started) * 1000)
        after_packets, after_bytes = _counter(slot.rule)
        remote_ip = _remote_ip(execution.stdout)
        endpoint_match = remote_ip == selected_ip
        intercepted = after_packets > before_packets
        classification = (
            "pass"
            if request.curl_exit(execution) == 0 and endpoint_match and intercepted
            else "fail"
        )
        return {
            "slot": slot.name,
            "rule": slot.rule,
            "port": slot.port,
            "endpoint": endpoint,
            "selected_ip": selected_ip,
            "remote_ip": remote_ip,
            "endpoint_match": endpoint_match,
            "classification": classification,
            "intercepted": intercepted,
            "counter": {
                "packets_before": before_packets,
                "packets_after": after_packets,
                "bytes_before": before_bytes,
                "bytes_after": after_bytes,
            },
            "inactive_rules_absent": _inactive_rules_absent(slot, slots),
            "dispatch_ms": dispatch_ms,
            "probe_ms": probe_ms,
            "execution": execution.evidence(),
        }
    finally:
        _require_adapter("route-del", str(slot.rule))


def _all_survivors_ready(slots: Sequence[Slot]) -> bool:
    for slot in slots:
        snap = _snapshot(slot)
        if not (
            snap.get("process_identity") is True
            and snap.get("socket_ready") is True
            and snap.get("log_clean") is True
        ):
            return False
    return True


def _rss_summary(pool: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values = [snap.get("rss_kb") for snap in pool.values()]
    numeric = [int(value) for value in values if isinstance(value, int) and not isinstance(value, bool) and value >= 0]
    return {
        "per_worker_kb": {name: snap.get("rss_kb") for name, snap in pool.items()},
        "aggregate_kb": sum(numeric) if len(numeric) == len(pool) else None,
        "all_numeric": len(numeric) == len(pool),
    }


def _write_report(output: Path, report: dict[str, Any]) -> None:
    _atomic_json(output, report)


def run(reference_job_id: str, output: str) -> int:
    output_path = Path(output)
    reference_job = job_dir(reference_job_id)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "model": MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reference_job": reference_job_id,
        "experiment_only": True,
        "parallel_probes": False,
        "production_approved": False,
        "checks": {},
        "restoration": {"verified": False, "pending": True},
        "conclusion": "inconclusive",
    }
    try:
        status, reference_inventory, binding, selected = _reference_contract(reference_job)
        current_inventory = _current_inventory(reference_inventory)
        report["reference"] = {
            "target": status.get("target"),
            "mode": status.get("mode"),
            "search_epoch_id": binding.get("epoch_id"),
            "resource_inventory_id": reference_inventory.inventory_id,
            "initial_service_state": (status.get("restoration") or {}).get("initial_state"),
        }
        report["checks"]["reference_inventory_match"] = True
        session_dir().mkdir(parents=True, exist_ok=True)
        workers = {
            slot.name: _write_worker_runtime(
                slot, selected[slot.name], current_inventory, str(binding["endpoint"])
            )
            for slot in SLOTS
        }
        report["workers"] = workers
        wan = _require_adapter("wan").strip()
        if not wan:
            raise ModelBExperimentError("Model B WAN interface could not be resolved")
        report["wan"] = wan
        _require_adapter("preflight")

        pool_started = time.monotonic()
        for slot in SLOTS:
            _require_adapter("launch", slot.name, str(slot.port))
        pool = _wait_pool_ready(SLOTS)
        pool_startup_ms = round((time.monotonic() - pool_started) * 1000)
        report["pool"] = {
            "startup_ms": pool_startup_ms,
            "snapshots": pool,
            "rss": _rss_summary(pool),
        }
        pids = [snap.get("pid") for snap in pool.values()]
        ports = [snap.get("divert_port") for snap in pool.values()]
        all_ready = all(snap.get("ready") is True for snap in pool.values())
        unique_identity = (
            all_ready
            and len(set(pids)) == len(SLOTS)
            and None not in pids
            and len(set(ports)) == len(SLOTS)
            and set(ports) == {slot.port for slot in SLOTS}
        )
        report["checks"]["all_workers_ready"] = all_ready
        report["checks"]["unique_worker_identity"] = unique_identity
        report["checks"]["rss_observed"] = bool(report["pool"]["rss"]["all_numeric"])
        if not all_ready:
            report["failed_readiness"] = {
                "failed_slots": [
                    slot.name
                    for slot in SLOTS
                    if pool.get(slot.name, {}).get("ready") is not True
                ],
                "downstream_actions_skipped": True,
            }
            raise ModelBExperimentError("Model B worker pool did not reach readiness")

        probes: list[dict[str, Any]] = []
        sequence = (SLOTS[0], SLOTS[1], SLOTS[2], SLOTS[0])
        for slot in sequence:
            probe = _probe(slot, SLOTS, str(binding["endpoint"]), str(binding["selected_ip"]), wan)
            probe["expected_classification"] = workers[slot.name]["expected_classification"]
            probe["equivalent_to_model_a"] = probe["classification"] == probe["expected_classification"]
            probe["all_workers_still_ready"] = _all_survivors_ready(SLOTS)
            probes.append(probe)
        report["probes"] = probes
        report["checks"]["result_equivalence"] = all(item["equivalent_to_model_a"] for item in probes)
        report["checks"]["route_attribution"] = all(
            item["intercepted"] is True and item["inactive_rules_absent"] is True for item in probes
        )
        report["checks"]["coexistence_stable"] = all(item["all_workers_still_ready"] for item in probes)
        report["checks"]["repeated_selection_stable"] = (
            probes[0]["classification"] == probes[3]["classification"]
            and probes[0]["classification"] == workers["pass"]["expected_classification"]
        )

        # Stop one worker deliberately while the others stay warm, then re-probe the known
        # passing worker.  This is the independent-stop part of the Model-B gate.
        _require_adapter("stop", SLOTS[1].name, str(SLOTS[1].port), timeout=20)
        independent_survivors = (SLOTS[0], SLOTS[2])
        independent_ready = _all_survivors_ready(independent_survivors)
        independent_probe = _probe(
            SLOTS[0], independent_survivors, str(binding["endpoint"]), str(binding["selected_ip"]), wan
        )
        independent_probe["expected_classification"] = workers["pass"]["expected_classification"]
        independent_probe["equivalent_to_model_a"] = (
            independent_probe["classification"] == independent_probe["expected_classification"]
        )
        report["independent_stop"] = {
            "stopped_slot": SLOTS[1].name,
            "survivors_ready": independent_ready,
            "probe": independent_probe,
        }
        report["checks"]["independent_stop"] = independent_ready and independent_probe["equivalent_to_model_a"]

        # Simulate one unexpected worker death.  Cleanup must remove that worker without
        # changing the remaining warm worker or its cold-reference result.
        _require_adapter("kill-owned", SLOTS[2].name, str(SLOTS[2].port), timeout=10)
        time.sleep(1)
        dead_snapshot = _snapshot(SLOTS[2])
        dead_absent = not bool(dead_snapshot.get("process_identity")) and not bool(dead_snapshot.get("socket_ready"))
        _require_adapter("stop", SLOTS[2].name, str(SLOTS[2].port), timeout=20)
        survivor_ready = _all_survivors_ready((SLOTS[0],))
        death_probe = _probe(
            SLOTS[0], (SLOTS[0],), str(binding["endpoint"]), str(binding["selected_ip"]), wan
        )
        death_probe["expected_classification"] = workers["pass"]["expected_classification"]
        death_probe["equivalent_to_model_a"] = death_probe["classification"] == death_probe["expected_classification"]
        report["controlled_worker_death"] = {
            "dead_slot": SLOTS[2].name,
            "dead_snapshot": dead_snapshot,
            "dead_worker_absent": dead_absent,
            "survivor_ready": survivor_ready,
            "survivor_probe": death_probe,
        }
        report["checks"]["controlled_worker_death_cleanup"] = dead_absent
        report["checks"]["remaining_worker_after_death"] = survivor_ready and death_probe["equivalent_to_model_a"]
        report["checks"]["sequential_probe_contract"] = True

        dispatch_values = [item["dispatch_ms"] for item in probes] + [independent_probe["dispatch_ms"], death_probe["dispatch_ms"]]
        probe_values = [item["probe_ms"] for item in probes] + [independent_probe["probe_ms"] for independent_probe in [independent_probe]] + [death_probe["probe_ms"]]
        report["timing"] = {
            "pool_startup_ms": pool_startup_ms,
            "dispatch_median_ms": round(statistics.median(dispatch_values), 3),
            "probe_median_ms": round(statistics.median(probe_values), 3),
        }
        required = (
            "reference_inventory_match",
            "all_workers_ready",
            "unique_worker_identity",
            "rss_observed",
            "result_equivalence",
            "route_attribution",
            "coexistence_stable",
            "repeated_selection_stable",
            "independent_stop",
            "controlled_worker_death_cleanup",
            "remaining_worker_after_death",
            "sequential_probe_contract",
        )
        report["required_checks"] = list(required)
        report["preliminary_accept"] = all(report["checks"].get(name) is True for name in required)
        report["conclusion"] = "pending_restoration" if report["preliminary_accept"] else "reject"
    except (ModelBExperimentError, candidate_spec.CandidateSpecError, resources.ResourceInventoryError, request.RequestError, OSError, ValueError) as exc:
        report["error"] = str(exc)
        report["preliminary_accept"] = False
        report["conclusion"] = "reject"
    finally:
        report["experiment_cleanup_requested"] = _try_adapter("cleanup-all", timeout=25)
        _write_report(output_path, report)
    return EX_OK


def finalize(output: str, initial_evidence: str, final_evidence: str, cleanup_ok: str) -> int:
    output_path = Path(output)
    report = _load_json(output_path)
    initial = _load_json(Path(initial_evidence))
    final = _load_json(Path(final_evidence))
    clean = cleanup_ok == "1"
    same_state = final.get("state") == initial.get("state")
    same_config = final.get("effective_config_hash") == initial.get("effective_config_hash")
    same_args = final.get("runtime_args_hash") == initial.get("runtime_args_hash")
    same_firewall = final.get("normal_firewall_hash") == initial.get("normal_firewall_hash")
    semantic = same_state and same_config and same_args and same_firewall
    report["restoration"] = {
        "verified": semantic and clean,
        "pending": False,
        "cleanup_ok": clean,
        "initial_state": initial.get("state"),
        "final_state": final.get("state"),
        "strategy_unchanged": same_config and same_args,
        "normal_firewall_unchanged": same_firewall,
        "temporary_runtime_clean": clean,
    }
    report.setdefault("checks", {})["restoration_verified"] = semantic and clean
    report["production_approved"] = False
    report["conclusion"] = (
        "accept"
        if report.get("preliminary_accept") is True and semantic and clean
        else "reject"
    )
    _write_report(output_path, report)
    return EX_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 3 and args[0] == "run":
        return run(args[1], args[2])
    if len(args) == 5 and args[0] == "finalize":
        return finalize(args[1], args[2], args[3], args[4])
    raise ValueError(
        "model-b requires: run REFERENCE_JOB OUTPUT | "
        "finalize OUTPUT INITIAL_EVIDENCE FINAL_EVIDENCE CLEANUP_OK"
    )
