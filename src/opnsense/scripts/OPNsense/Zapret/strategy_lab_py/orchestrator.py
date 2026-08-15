"""Python-owned Strategy Lab stage orchestration, budgets, cancellation, and finalization."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import protocol_presentation, resources, state as state_persistence, telemetry

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70

RUNNING_EVENTS = {
    "00": "Validating target and resolving required endpoints",
    "10": "Capturing the initial Zapret2 lifecycle state",
    "20": "Stopping and verifying the normal Zapret2 service",
    "30": "Checking IPv4, IPv6, and QUIC capabilities",
    "40": "Testing the clean target baseline without Zapret2",
    "50": "Running one isolated Zapret2 smoke candidate",
    "60": "Expanding TLS 1.3 candidates using Stage-50 evidence for priority",
    "70": "Confirming candidate stability with three sequential fresh-connection attempts",
    "80": "Testing extended TLS, HTTP, QUIC, and configured UDP branches",
    "85": "Building the final stable-candidate shortlist",
    "90": "Cleaning temporary state and restoring Zapret2",
}

STAGE_LIMIT_ENV = {
    "30": "STRATEGY_LAB_STAGE30_TIMEOUT",
    "40": "STRATEGY_LAB_STAGE40_TIMEOUT",
    "50": "STRATEGY_LAB_CANDIDATE_TIMEOUT",
    "60": "STRATEGY_LAB_STAGE60_TIMEOUT",
    "70": "STRATEGY_LAB_STAGE70_TIMEOUT",
    "80": "STRATEGY_LAB_STAGE80_TIMEOUT",
}

DEFAULT_LIMITS = {
    "STRATEGY_LAB_STAGE30_TIMEOUT": 6,
    "STRATEGY_LAB_STAGE40_TIMEOUT": 20,
    "STRATEGY_LAB_CANDIDATE_TIMEOUT": 45,
    "STRATEGY_LAB_STAGE60_TIMEOUT": 60,
    "STRATEGY_LAB_STAGE70_TIMEOUT": 60,
    "STRATEGY_LAB_STAGE80_TIMEOUT": 120,
    "STRATEGY_LAB_STANDARD_BUDGET": 150,
    "STRATEGY_LAB_EXTENDED_BUDGET": 120,
}

VALID_RESULT_KINDS = {"pass", "error", "prerequisite", "accessible", "timeout", "cancel"}


class OrchestrationError(RuntimeError):
    pass


class UsageError(OrchestrationError):
    pass


class CancellationRequested(OrchestrationError):
    pass


class StageTimedOut(OrchestrationError):
    def __init__(self, stage: str):
        super().__init__(stage)
        self.stage = stage


@dataclass(frozen=True)
class AdapterResult:
    kind: str
    message: str = ""
    initial_state: str = ""


class Budget:
    """Absolute Strategy Lab budget owner with the existing standard/extended semantics."""

    def __init__(self, mode: str, state_path: Path, job_id: str) -> None:
        if mode not in {"standard", "extended"}:
            raise UsageError("invalid Strategy Lab mode")
        self.mode = mode
        self.state_path = state_path
        self.job_id = job_id
        self.standard_budget = _positive_env("STRATEGY_LAB_STANDARD_BUDGET")
        self.extended_budget = _positive_env("STRATEGY_LAB_EXTENDED_BUDGET")
        self.stage80_limit = _positive_env("STRATEGY_LAB_STAGE80_TIMEOUT")
        self.started_epoch = self.now()
        self.standard_deadline = self.started_epoch + self.standard_budget
        self.search_budget = self.standard_budget
        self.overall_deadline = self.standard_deadline
        if mode == "extended":
            self.search_budget = self.standard_budget + self.extended_budget
            self.overall_deadline = self.started_epoch + self.search_budget
        self.stage80_started: int | None = None
        self.stage80_deadline: int | None = None

    @staticmethod
    def now() -> int:
        clock = os.environ.get("STRATEGY_LAB_NOW_EPOCH_FILE", "")
        if clock:
            try:
                raw = Path(clock).read_text(encoding="utf-8").strip()
                value = int(raw, 10)
            except (OSError, ValueError) as exc:
                raise OrchestrationError("Strategy Lab budget clock is invalid") from exc
            if value < 0:
                raise OrchestrationError("Strategy Lab budget clock is invalid")
            return value
        return int(time.time())

    @staticmethod
    def iso8601(epoch: int) -> str:
        return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def record_initial(self) -> None:
        state_persistence.set_budget(
            self.job_id,
            str(self.state_path),
            self.iso8601(self.started_epoch),
            self.iso8601(self.standard_deadline),
            self.iso8601(self.overall_deadline),
            str(self.standard_budget),
            str(self.extended_budget),
            str(self.search_budget),
            str(self.stage80_limit),
        )

    def begin_stage80(self) -> None:
        now = self.now()
        if now >= self.overall_deadline:
            raise StageTimedOut("80")
        self.stage80_started = now
        self.stage80_deadline = min(now + self.stage80_limit, self.overall_deadline)
        state_persistence.set_stage80_budget(
            self.job_id,
            str(self.state_path),
            self.iso8601(self.stage80_started),
            self.iso8601(self.stage80_deadline),
        )

    def deadline_for(self, stage: str) -> int:
        if stage == "80":
            if self.stage80_deadline is None:
                raise OrchestrationError("Strategy Lab stage-80 budget is not initialized")
            return self.stage80_deadline
        if stage == "85":
            return self.overall_deadline
        return self.standard_deadline

    def timeout_for(self, stage: str, operation_limit: int) -> int:
        if operation_limit <= 0:
            raise OrchestrationError("Strategy Lab operation timeout is invalid")
        remaining = self.deadline_for(stage) - self.now()
        if remaining <= 0:
            raise StageTimedOut(stage)
        return min(operation_limit, remaining)

    def require(self, stage: str) -> None:
        self.timeout_for(stage, 2_147_483_647)


def _positive_env(name: str) -> int:
    raw = os.environ.get(name, str(DEFAULT_LIMITS[name]))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise UsageError(f"invalid Strategy Lab setting: {name}") from exc
    if value <= 0:
        raise UsageError(f"invalid Strategy Lab setting: {name}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OrchestrationError(f"Strategy Lab JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise OrchestrationError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _message(language: str, key: str) -> str:
    ru = language == "ru"
    values = {
        "cancel_skip": "SKIPPED — отменено" if ru else "SKIPPED — canceled",
        "prerequisite_skip": "SKIPPED — предварительная проверка не пройдена" if ru else "SKIPPED — prerequisite failed",
        "accessible_skip": "SKIPPED — цель доступна без обхода" if ru else "SKIPPED — target accessible without bypass",
        "error_skip": "SKIPPED — не выполнено" if ru else "SKIPPED — not executed",
        "timeout_skip": "SKIPPED — лимит времени исчерпан" if ru else "SKIPPED — time budget exhausted",
        "stage_timeout": "TIMEOUT — превышен лимит этапа." if ru else "TIMEOUT — stage time limit exceeded.",
        "stage80_skip": "SKIPPED — расширенные ветви отключены в основном режиме." if ru else "SKIPPED — extended branches are disabled in standard mode.",
        "restore_running": "PASS — Временные процессы и правила удалены; исходная служба Zapret2 снова запущена и полностью исправна." if ru else "PASS — Temporary processes and rules were removed; the original Zapret2 service was restarted and is fully operational.",
        "restore_stopped": "PASS — Временные процессы и правила удалены; Zapret2 оставлен в исходном остановленном состоянии." if ru else "PASS — Temporary processes and rules were removed; Zapret2 was left in its original stopped state.",
        "restore_noop": "PASS — Изменения состояния Zapret2 не выполнялись." if ru else "PASS — No Zapret2 service-state changes were made.",
        "restore_failed": "RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось." if ru else "RESTORE_FAILED — The original Zapret2 state could not be restored.",
    }
    return values[key]


def terminal_state(outcome: str) -> str:
    return "error" if outcome in {"ERROR", "TIMEOUT", "RESTORE_FAILED"} else "completed"


def terminal_report_status(outcome: str) -> str:
    return "FAIL" if outcome in {"ERROR", "TIMEOUT", "RESTORE_FAILED"} else "PASS"


def terminal_message(language: str, mode: str, outcome: str, canceled: bool, count: int = 0) -> str:
    ru = language == "ru"
    if outcome == "SUCCESS":
        if ru and mode == "standard":
            return f"SUCCESS — Основной поиск завершён; стабильных рабочих стратегий: {count}."
        if ru:
            return f"SUCCESS — Расширенный поиск завершён; стабильных рабочих стратегий: {count}."
        if mode == "standard":
            return f"SUCCESS — Standard search completed with {count} stable working strategies."
        return f"SUCCESS — Extended search completed with {count} stable working strategies."
    if outcome == "NO_CANDIDATE":
        if ru and mode == "standard":
            return "NO_CANDIDATE — Основной поиск завершён; стабильная рабочая стратегия не найдена."
        if ru:
            return "NO_CANDIDATE — Расширенный поиск завершён; стабильная рабочая стратегия не найдена."
        if mode == "standard":
            return "NO_CANDIDATE — Standard search completed; no stable working strategy was found."
        return "NO_CANDIDATE — Extended search completed; no stable working strategy was found."
    if outcome == "TARGET_ACCESSIBLE":
        return "TARGET_ACCESSIBLE — Цель доступна без обхода; поиск стратегий не требуется." if ru else "TARGET_ACCESSIBLE — The target is accessible without bypass; strategy search is not required."
    if outcome == "PARTIAL":
        if canceled:
            return "PARTIAL — Тест отменён; результаты завершённых этапов сохранены." if ru else "PARTIAL — Test canceled; completed stage results were preserved."
        return "PARTIAL — Поиск завершён не полностью; доступные результаты сохранены." if ru else "PARTIAL — The search ended before completion; available results were preserved."
    if outcome == "TIMEOUT":
        return "TIMEOUT — Лимит времени исчерпан; доступные результаты сохранены." if ru else "TIMEOUT — The time limit was reached; available results were preserved."
    if outcome == "ERROR":
        return "ERROR — Внутренняя ошибка Strategy Lab; доступные результаты сохранены." if ru else "ERROR — Strategy Lab failed internally; available results were preserved."
    if outcome == "RESTORE_FAILED":
        return "RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось." if ru else "RESTORE_FAILED — The original Zapret2 state could not be restored."
    return f"ERROR — Unsupported Strategy Lab outcome: {outcome}."


class Orchestrator:
    def __init__(self, job_id: str) -> None:
        self.run_started = time.monotonic()
        self.job_id = job_id
        run_dir = Path(os.environ.get("STRATEGY_LAB_RUN_DIR", "/var/run/zapret2-restyle/strategy-lab"))
        jobs_dir = Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", str(run_dir / "jobs")))
        self.job_dir = jobs_dir / job_id
        self.state_path = self.job_dir / "status.json"
        self.events_path = self.job_dir / "events.ndjson"
        self.cancel_path = self.job_dir / "cancel.request"
        self.active_path = Path(os.environ.get("STRATEGY_LAB_ACTIVE_FILE", str(run_dir / "active.job")))
        self.adapter = Path(os.environ.get("STRATEGY_LAB_STAGE_ADAPTER", "/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage_adapter.sh"))
        self.shell = os.environ.get("STRATEGY_LAB_SH_BIN", "/bin/sh")
        status = _load_json(self.state_path)
        self.language = str(status.get("language", "en"))
        self.mode = str(status.get("mode", "standard"))
        if self.language not in {"en", "ru"} or self.mode not in {"standard", "extended"}:
            raise OrchestrationError("Strategy Lab job language or mode is invalid")
        self.budget = Budget(self.mode, self.state_path, self.job_id)
        self.current_stage = "00"
        self.finalizing = False
        self.signal_cancel = False
        self.previous_handlers: dict[int, Any] = {}

    def install_signals(self) -> None:
        for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            self.previous_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._signal)

    def restore_signals(self) -> None:
        for sig, handler in self.previous_handlers.items():
            signal.signal(sig, handler)
        self.previous_handlers.clear()

    def _signal(self, _signum: int, _frame: Any) -> None:
        self.signal_cancel = True

    def cancel_requested(self) -> bool:
        return self.signal_cancel or self.cancel_path.exists()

    def check_cancel(self) -> None:
        if self.cancel_requested() and not self.finalizing:
            raise CancellationRequested("Strategy Lab cancellation requested")

    def _update_stage(self, stage: str, status: str, message: str) -> None:
        state_persistence.update_stage(self.job_id, str(self.state_path), stage, status, message)
        state_persistence.append_event(self.job_id, str(self.state_path), str(self.events_path), stage, status, message)

    def _begin(self, stage: str) -> None:
        self.current_stage = stage
        self.check_cancel()
        state_persistence.update_stage(self.job_id, str(self.state_path), stage, "RUNNING", "")
        state_persistence.append_event(
            self.job_id, str(self.state_path), str(self.events_path), stage, "RUNNING", RUNNING_EVENTS[stage]
        )

    def _pass(self, stage: str, message: str) -> None:
        self._update_stage(stage, "PASS", message)

    def _skip(self, stage: str, message: str) -> None:
        self.current_stage = stage
        self._update_stage(stage, "SKIPPED", message)

    def _fd_pass(self) -> tuple[int, ...]:
        try:
            os.fstat(9)
        except OSError:
            return ()
        return (9,)

    @staticmethod
    def _terminate_process_group(proc: subprocess.Popen[bytes]) -> None:
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 2.0
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass

    def _run_adapter(
        self,
        action: str,
        *,
        operation_timeout: int | None = None,
        cancel_interruptible: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> AdapterResult:
        started = time.monotonic()
        outcome = "error"
        try:
            result = self._run_adapter_process(
                action,
                operation_timeout=operation_timeout,
                cancel_interruptible=cancel_interruptible,
                extra_env=extra_env,
            )
            outcome = result.kind
            return result
        except CancellationRequested:
            outcome = "cancel"
            raise
        except StageTimedOut:
            outcome = "timeout"
            raise
        finally:
            active_error = sys.exc_info()[0] is not None
            try:
                telemetry.record(
                    self.job_dir,
                    "stage_adapter",
                    telemetry.elapsed_ms(started),
                    stage=self.current_stage,
                    outcome=outcome,
                    details={
                        "action": action,
                        "operation_timeout_seconds": operation_timeout,
                    },
                )
            except Exception:
                if not active_error:
                    raise

    def _run_adapter_process(
        self,
        action: str,
        *,
        operation_timeout: int | None = None,
        cancel_interruptible: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> AdapterResult:
        if not self.adapter.is_file():
            raise OrchestrationError(f"Strategy Lab stage adapter is unavailable: {self.adapter}")
        result_path = self.job_dir / ".orchestrator-result.json"
        try:
            result_path.unlink()
        except FileNotFoundError:
            pass
        env = os.environ.copy()
        env.update(
            JOB_ID=self.job_id,
            STRATEGY_LAB_STAGE_RESULT_FILE=str(result_path),
            STRATEGY_LAB_WORKER_PID=str(os.getpid()),
            STRATEGY_LAB_RUN_DIR=str(self.job_dir.parent.parent),
            STRATEGY_LAB_JOBS_DIR=str(self.job_dir.parent),
            STRATEGY_LAB_ACTIVE_FILE=str(self.active_path),
        )
        if operation_timeout is not None:
            env["STRATEGY_LAB_OPERATION_TIMEOUT"] = str(operation_timeout)
        if extra_env:
            env.update(extra_env)
        proc = subprocess.Popen(
            [self.shell, str(self.adapter), action, self.job_id],
            env=env,
            start_new_session=True,
            pass_fds=self._fd_pass(),
        )
        started = time.monotonic()
        while proc.poll() is None:
            if cancel_interruptible and self.cancel_requested():
                self._terminate_process_group(proc)
                raise CancellationRequested("Strategy Lab cancellation requested")
            if operation_timeout is not None and time.monotonic() - started >= operation_timeout:
                self._terminate_process_group(proc)
                raise StageTimedOut(self.current_stage)
            time.sleep(0.05)
        status = proc.returncode
        if self.cancel_requested() and cancel_interruptible:
            raise CancellationRequested("Strategy Lab cancellation requested")
        if status == 124:
            raise StageTimedOut(self.current_stage)
        if status == 125:
            raise CancellationRequested("Strategy Lab cancellation requested")
        if not result_path.is_file():
            raise OrchestrationError(f"Strategy Lab stage adapter did not produce a result for {action} (status {status})")
        value = _load_json(result_path)
        try:
            result_path.unlink()
        except FileNotFoundError:
            pass
        kind = value.get("kind")
        message = value.get("message", "")
        initial_state = value.get("initial_state", "")
        if kind not in VALID_RESULT_KINDS or not isinstance(message, str) or not isinstance(initial_state, str):
            raise OrchestrationError(f"Strategy Lab stage adapter returned an invalid result for {action}")
        if status != 0 and kind not in {"timeout", "cancel"}:
            raise OrchestrationError(f"Strategy Lab stage adapter failed for {action} with status {status}")
        if kind == "timeout":
            raise StageTimedOut(self.current_stage)
        if kind == "cancel":
            raise CancellationRequested("Strategy Lab cancellation requested")
        return AdapterResult(kind=kind, message=message, initial_state=initial_state)

    def _operation_limit(self, stage: str) -> int:
        return _positive_env(STAGE_LIMIT_ENV[stage])

    def _quic_enabled(self) -> bool:
        if self.mode != "extended":
            return False
        path = self.job_dir / "quic-enabled"
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise OrchestrationError("Strategy Lab QUIC execution setting is unavailable") from exc
        if value not in {"0", "1"}:
            raise OrchestrationError("Strategy Lab QUIC execution setting is invalid")
        return value == "1"

    def _handle_result(self, stage: str, result: AdapterResult) -> str | None:
        if result.kind == "pass":
            self._pass(stage, result.message)
            return None
        if result.kind == "accessible":
            self._pass(stage, result.message)
            return "TARGET_ACCESSIBLE"
        if result.kind == "prerequisite":
            self._update_stage(stage, "FAIL", result.message)
            return "PARTIAL"
        self._update_stage(stage, "FAIL", result.message or "Strategy Lab stage failed internally.")
        return "ERROR"

    def _run_regular_stage(self, stage: str) -> str | None:
        self._begin(stage)
        timeout = None
        if stage in STAGE_LIMIT_ENV:
            timeout = self.budget.timeout_for(stage, self._operation_limit(stage))
        result = self._run_adapter(stage, operation_timeout=timeout, cancel_interruptible=stage not in {"00", "10", "20"})
        if stage == "30" and result.kind == "pass":
            try:
                message = protocol_presentation.stage30_message(
                    self.language,
                    self.mode,
                    self._quic_enabled(),
                    _load_json(self.job_dir / "network.json"),
                )
            except protocol_presentation.ProtocolPresentationError as exc:
                raise OrchestrationError(f"Strategy Lab network presentation is invalid: {exc}") from exc
            result = AdapterResult(kind="pass", message=message, initial_state=result.initial_state)
        return self._handle_result(stage, result)

    def _run_stage80(self) -> str | None:
        if self.mode != "extended":
            self._skip("80", _message(self.language, "stage80_skip"))
            return None
        self._begin("80")
        self.budget.begin_stage80()
        for action in ("80-tcp", "80-quic", "80-udp"):
            self.check_cancel()
            timeout = self.budget.timeout_for("80", self._operation_limit("80"))
            result = self._run_adapter(action, operation_timeout=timeout)
            if result.kind != "pass":
                return self._handle_result("80", result)
        quic = _load_json(self.job_dir / "quic.json")
        udp = _load_json(self.job_dir / "udp.json")
        try:
            message = protocol_presentation.stage80_message(self.language, quic, udp)
        except protocol_presentation.ProtocolPresentationError as exc:
            raise OrchestrationError(f"Strategy Lab extended presentation is invalid: {exc}") from exc
        self._pass("80", message)
        return None

    def shortlist_count(self) -> int:
        value = _load_json(self.job_dir / "shortlist.json")
        count = value.get("count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise OrchestrationError("Final shortlist result is unavailable or invalid.")
        return count

    def _restore(self, outcome: str) -> str:
        self.current_stage = "90"
        state_persistence.update_stage(self.job_id, str(self.state_path), "90", "RUNNING", "")
        state_persistence.append_event(
            self.job_id, str(self.state_path), str(self.events_path), "90", "RUNNING", RUNNING_EVENTS["90"]
        )
        try:
            result = self._run_adapter("restore", cancel_interruptible=False)
        except Exception:
            result = AdapterResult("error", "")
        if result.kind == "pass":
            key = {"RUNNING": "restore_running", "STOPPED": "restore_stopped"}.get(result.initial_state, "restore_noop")
            message = _message(self.language, key)
            self._update_stage("90", "PASS", message)
            return outcome
        message = _message(self.language, "restore_failed")
        self._update_stage("90", "FAIL", message)
        return "RESTORE_FAILED"

    def _clear_active_pointer(self) -> None:
        try:
            current = self.active_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return
        except OSError:
            return
        if current != self.job_id:
            return
        try:
            self.active_path.unlink()
        except FileNotFoundError:
            pass

    def finish(self, outcome: str, canceled: bool) -> int:
        if self.finalizing:
            return EX_OK
        self.finalizing = True
        outcome = self._restore(outcome)
        final_state = terminal_state(outcome)
        report_status = terminal_report_status(outcome)
        count = 0
        if outcome == "SUCCESS":
            try:
                count = self.shortlist_count()
            except OrchestrationError:
                outcome = "ERROR"
                final_state = terminal_state(outcome)
                report_status = terminal_report_status(outcome)
        try:
            telemetry.record(
                self.job_dir,
                "job_total",
                telemetry.elapsed_ms(self.run_started),
                stage="99",
                outcome=outcome.lower(),
                details={
                    "canceled": canceled,
                    "scope": "job-start-through-mandatory-restoration",
                },
            )
        except Exception:
            outcome = "ERROR"
            final_state = terminal_state(outcome)
            report_status = terminal_report_status(outcome)
        message = terminal_message(self.language, self.mode, outcome, canceled, count)
        self.current_stage = "99"
        self._update_stage("99", report_status, message)
        try:
            self._run_adapter(
                "eligibility",
                cancel_interruptible=False,
                extra_env={
                    "STRATEGY_LAB_FINAL_STATE": final_state,
                    "STRATEGY_LAB_FINAL_OUTCOME": outcome,
                },
            )
        except Exception:
            pass
        state_persistence.update_job(
            self.job_id, str(self.state_path), final_state, outcome, "99", canceled, message
        )
        try:
            self._run_adapter("clear-active", cancel_interruptible=False)
        except Exception:
            self._clear_active_pointer()
        return EX_OK

    def hold_after_stop(self) -> None:
        raw = os.environ.get("WORKER_HOLD_SECONDS", "0")
        try:
            seconds = int(raw, 10)
        except ValueError as exc:
            raise UsageError("invalid Strategy Lab worker hold") from exc
        if seconds < 0:
            raise UsageError("invalid Strategy Lab worker hold")
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check_cancel()
            if Budget.now() >= self.budget.standard_deadline:
                raise StageTimedOut("20")
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))

    def run(self) -> int:
        self.install_signals()
        try:
            self.budget.record_initial()
            state_persistence.update_job(self.job_id, str(self.state_path), "running", "", "00", False, "")
            inventory_started = time.monotonic()
            inventory_outcome = "error"
            try:
                inventory = resources.ensure_job_inventory(self.job_dir)
                inventory_outcome = "pass"
            finally:
                telemetry.record(
                    self.job_dir,
                    "resource_inventory_snapshot",
                    telemetry.elapsed_ms(inventory_started),
                    stage="00",
                    outcome=inventory_outcome,
                    details={
                        "resource_inventory_id": (
                            inventory.inventory_id if inventory_outcome == "pass" else ""
                        )
                    },
                )
            for stage in ("00", "10", "20", "30", "40", "50", "60", "70"):
                self.check_cancel()
                outcome = self._run_regular_stage(stage)
                if stage == "20":
                    self.hold_after_stop()
                if outcome == "TARGET_ACCESSIBLE":
                    state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "accessible_skip"))
                    return self.finish(outcome, False)
                if outcome == "PARTIAL":
                    state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "prerequisite_skip"))
                    return self.finish(outcome, False)
                if outcome == "ERROR":
                    state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "error_skip"))
                    return self.finish(outcome, False)
            self.check_cancel()
            outcome = self._run_stage80()
            if outcome == "ERROR":
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "error_skip"))
                return self.finish(outcome, False)
            self.check_cancel()
            self.budget.require("85")
            outcome = self._run_regular_stage("85")
            if outcome == "ERROR":
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "error_skip"))
                return self.finish(outcome, False)
            self.check_cancel()
            count = self.shortlist_count()
            return self.finish("SUCCESS" if count > 0 else "NO_CANDIDATE", False)
        except CancellationRequested:
            try:
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "cancel_skip"))
            except Exception:
                pass
            return self.finish("PARTIAL", True)
        except StageTimedOut as exc:
            self.current_stage = exc.stage
            try:
                self._update_stage(exc.stage, "TIMEOUT", _message(self.language, "stage_timeout"))
            except Exception:
                pass
            try:
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "timeout_skip"))
            except Exception:
                pass
            return self.finish("TIMEOUT", False)
        except Exception as exc:
            message = f"Strategy Lab Python orchestration failed internally: {exc}"
            try:
                self._update_stage(self.current_stage, "FAIL", message)
            except Exception:
                pass
            try:
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "error_skip"))
            except Exception:
                pass
            return self.finish("ERROR", False)
        finally:
            self.restore_signals()


def main(argv: list[str] | tuple[str, ...]) -> int:
    args = list(argv)
    if len(args) != 1:
        raise UsageError("orchestrate requires exactly one Strategy Lab job id")
    job_id = args[0]
    if not state_persistence.JOB_ID_RE.fullmatch(job_id):
        raise UsageError("invalid Strategy Lab job id")
    return Orchestrator(job_id).run()
