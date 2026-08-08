"""Python-owned Strategy Lab stage orchestration for Migration Patch 3."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from . import state as state_persistence

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
EX_TEMPFAIL = 75
EX_TIMEOUT = 124
EX_CANCELED = 125

STAGE_ORDER = ("00", "10", "20", "30", "40", "50", "60", "70", "80", "85", "90", "99")
VALID_RESULT_KINDS = {"pass", "accessible", "prerequisite", "error", "timeout", "cancel"}
STAGE_LIMIT_ENV = {
    "30": "STRATEGY_LAB_NETWORK_BUDGET",
    "40": "STRATEGY_LAB_BASELINE_BUDGET",
    "50": "STRATEGY_LAB_CANDIDATE_BUDGET",
    "60": "STRATEGY_LAB_EXPANSION_BUDGET",
    "70": "STRATEGY_LAB_STABILITY_BUDGET",
    "80": "STRATEGY_LAB_EXTENDED_BUDGET",
    "85": "STRATEGY_LAB_PROFILE_BUDGET",
}

MESSAGES = {
    "en": {
        "timeout": "ERROR — Strategy Lab time budget was exhausted.",
        "cancel": "CANCELED — Strategy Lab cancellation was requested.",
        "signal": "CANCELED — Strategy Lab worker was interrupted by a signal.",
        "internal": "ERROR — Strategy Lab failed internally.",
        "accessible_skip": "Skipped because the target is already reachable without DPI bypass.",
        "prerequisite_skip": "Skipped because a prerequisite failed.",
        "error_skip": "Skipped because an earlier stage failed internally.",
        "cancel_skip": "Skipped because cancellation was requested.",
        "timeout_skip": "Skipped because the Strategy Lab time budget was exhausted.",
        "stage80_skip": "SKIPPED — Extended testing is disabled in Standard mode.",
        "restore_running": "PASS — Initial running zapret state restored.",
        "restore_stopped": "PASS — Initial stopped zapret state restored.",
        "restore_noop": "PASS — No zapret service restoration was required.",
        "restore_failed": "FAIL — Initial zapret service state could not be restored safely.",
    },
    "ru": {
        "timeout": "ОШИБКА — Исчерпан лимит времени Strategy Lab.",
        "cancel": "ОТМЕНЕНО — Запрошена отмена Strategy Lab.",
        "signal": "ОТМЕНЕНО — Работа Strategy Lab прервана сигналом.",
        "internal": "ОШИБКА — Внутренняя ошибка Strategy Lab.",
        "accessible_skip": "Пропущено: цель уже доступна без обхода DPI.",
        "prerequisite_skip": "Пропущено из-за ошибки обязательной предварительной проверки.",
        "error_skip": "Пропущено из-за внутренней ошибки предыдущего этапа.",
        "cancel_skip": "Пропущено из-за запроса отмены.",
        "timeout_skip": "Пропущено: исчерпан лимит времени Strategy Lab.",
        "stage80_skip": "ПРОПУЩЕНО — Расширенная проверка отключена в режиме Standard.",
        "restore_running": "ПРОЙДЕНО — Исходное запущенное состояние zapret восстановлено.",
        "restore_stopped": "ПРОЙДЕНО — Исходное остановленное состояние zapret восстановлено.",
        "restore_noop": "ПРОЙДЕНО — Восстановление состояния службы zapret не требовалось.",
        "restore_failed": "ОШИБКА — Исходное состояние службы zapret не удалось безопасно восстановить.",
    },
}

RUNNING_EVENTS = {
    "90": "Restore initial service state",
}


class OrchestrationError(RuntimeError):
    pass


class UsageError(OrchestrationError):
    pass


class StageTimedOut(OrchestrationError):
    def __init__(self, stage: str):
        super().__init__(stage)
        self.stage = stage


class CancellationRequested(OrchestrationError):
    pass


class SignalRequested(OrchestrationError):
    pass


@dataclass(frozen=True)
class AdapterResult:
    kind: str
    message: str
    initial_state: str = ""


@dataclass
class Budget:
    started: float
    standard_seconds: int
    extended_seconds: int
    stage80_started: float | None = None

    @classmethod
    def from_environment(cls) -> "Budget":
        return cls(
            started=cls.now(),
            standard_seconds=_positive_env("STRATEGY_LAB_STANDARD_BUDGET"),
            extended_seconds=_positive_env("STRATEGY_LAB_EXTENDED_TOTAL_BUDGET"),
        )

    @staticmethod
    def now() -> float:
        return time.monotonic()

    @property
    def standard_deadline(self) -> float:
        return self.started + self.standard_seconds

    @property
    def extended_deadline(self) -> float:
        return self.started + self.extended_seconds

    @property
    def stage80_deadline(self) -> float | None:
        if self.stage80_started is None:
            return None
        return self.stage80_started + _positive_env("STRATEGY_LAB_EXTENDED_BUDGET")

    def record_initial(self) -> None:
        raw = os.environ.get("STRATEGY_LAB_INITIAL_EPOCH", "")
        if raw:
            try:
                initial_epoch = int(raw, 10)
            except ValueError as exc:
                raise UsageError("invalid Strategy Lab initial epoch") from exc
            if initial_epoch > 0:
                elapsed = max(0, int(time.time()) - initial_epoch)
                self.started -= elapsed

    def begin_stage80(self) -> None:
        self.stage80_started = self.now()

    def remaining(self, stage: str) -> float:
        deadline = self.extended_deadline if stage == "80" else self.standard_deadline
        if stage == "80" and self.stage80_deadline is not None:
            deadline = min(deadline, self.stage80_deadline)
        return deadline - self.now()

    def require(self, stage: str) -> None:
        if self.remaining(stage) <= 0:
            raise StageTimedOut(stage)

    def timeout_for(self, stage: str, requested: int) -> int:
        self.require(stage)
        remaining = self.remaining(stage)
        return max(1, min(requested, int(remaining) if remaining >= 1 else 1))


def _positive_env(name: str) -> int:
    raw = os.environ.get(name, "")
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise UsageError(f"invalid Strategy Lab budget: {name}") from exc
    if value <= 0:
        raise UsageError(f"invalid Strategy Lab budget: {name}")
    return value


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise OrchestrationError(f"Strategy Lab JSON is unavailable or invalid: {path}") from exc
    if not isinstance(value, dict):
        raise OrchestrationError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _message(language: str, key: str) -> str:
    return MESSAGES.get(language, MESSAGES["en"]).get(key, MESSAGES["en"][key])


def terminal_state(outcome: str) -> str:
    if outcome in {"SUCCESS", "TARGET_ACCESSIBLE"}:
        return "completed"
    if outcome == "PARTIAL":
        return "partial"
    if outcome == "RESTORE_FAILED":
        return "error"
    return "error"


def terminal_report_status(outcome: str) -> str:
    if outcome in {"SUCCESS", "TARGET_ACCESSIBLE"}:
        return "PASS"
    if outcome == "PARTIAL":
        return "CANCELED"
    return "FAIL"


def terminal_message(language: str, mode: str, outcome: str, canceled: bool, count: int) -> str:
    ru = language == "ru"
    if outcome == "SUCCESS":
        if ru:
            if mode == "extended":
                return f"Готово. Найдено стабильных кандидатов: {count}. Расширенная проверка завершена."
            return f"Готово. Найдено стабильных кандидатов: {count}."
        if mode == "extended":
            return f"Done. Found {count} stable candidates. Extended testing completed."
        return f"Done. Found {count} stable candidates."
    if outcome == "TARGET_ACCESSIBLE":
        return "Цель доступна без DPI bypass." if ru else "Target is reachable without DPI bypass."
    if outcome == "NO_CANDIDATE":
        return "Рабочая стратегия не найдена." if ru else "No working strategy was found."
    if outcome == "PARTIAL":
        if canceled:
            return "Проверка отменена. Система восстановлена в исходное состояние." if ru else "Test canceled. System restored to its initial state."
        return "Проверка завершена частично из-за ошибки предварительной проверки." if ru else "Test ended partially because a prerequisite failed."
    if outcome == "RESTORE_FAILED":
        return "Не удалось восстановить исходное состояние службы zapret." if ru else "Initial zapret service state could not be restored."
    if outcome == "TIMEOUT":
        return "Проверка остановлена: исчерпан лимит времени." if ru else "Test stopped because the time budget was exhausted."
    return "Внутренняя ошибка Strategy Lab." if ru else "Strategy Lab failed internally."


class Orchestrator:
    def __init__(self, job_id: str):
        if not state_persistence.JOB_RE.fullmatch(job_id):
            raise UsageError("invalid Strategy Lab job id")
        jobs_dir = Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-strategy-lab/jobs"))
        run_dir = Path(os.environ.get("STRATEGY_LAB_RUN_DIR", "/var/run/zapret2-strategy-lab"))
        self.job_id = job_id
        self.job_dir = jobs_dir / job_id
        self.state_path = self.job_dir / "status.json"
        self.events_path = self.job_dir / "events.ndjson"
        self.active_path = Path(os.environ.get("STRATEGY_LAB_ACTIVE_FILE", str(run_dir / "active-job")))
        self.result_path = self.job_dir / "python-stage-result.json"
        self.adapter = Path(os.environ.get("STRATEGY_LAB_STAGE_ADAPTER", "/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage_adapter.sh"))
        self.shell = os.environ.get("STRATEGY_LAB_SHELL_BIN", "/bin/sh")
        if not self.adapter.is_file():
            raise OrchestrationError(f"Strategy Lab stage adapter is unavailable: {self.adapter}")
        if not os.path.isfile(self.shell) or not os.access(self.shell, os.X_OK):
            raise OrchestrationError(f"Strategy Lab shell is unavailable: {self.shell}")
        state = _load_json(self.state_path)
        mode = state.get("mode")
        language = state.get("language")
        if mode not in {"standard", "extended"} or language not in {"en", "ru"}:
            raise OrchestrationError("Strategy Lab job mode/language is invalid")
        self.mode = mode
        self.language = language
        self.budget = Budget.from_environment()
        self.current_stage = "00"
        self.finalizing = False
        self.signal_requested: int | None = None

    def install_signals(self) -> None:
        def handler(signum: int, _frame: object) -> None:
            self.signal_requested = signum

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    def _fd_pass(self) -> tuple[int, ...]:
        try:
            os.fstat(9)
        except OSError:
            return ()
        return (9,)

    def cancel_requested(self) -> bool:
        state = _load_json(self.state_path)
        return bool(state.get("cancel_requested", False))

    def check_cancel(self) -> None:
        if self.signal_requested is not None:
            raise SignalRequested(str(self.signal_requested))
        if self.cancel_requested():
            raise CancellationRequested("Strategy Lab cancellation requested")

    def _update_stage(self, stage: str, status: str, message: str) -> None:
        state_persistence.update_stage(self.job_id, str(self.state_path), stage, status, message)
        state_persistence.append_event(
            self.job_id, str(self.state_path), str(self.events_path), stage, status,
            message or f"Stage {stage}: {status}",
        )

    def _begin(self, stage: str) -> None:
        self.current_stage = stage
        self._update_stage(stage, "RUNNING", "")

    def _pass(self, stage: str, message: str) -> None:
        self._update_stage(stage, "PASS", message)

    def _skip(self, stage: str, message: str) -> None:
        self.current_stage = stage
        self._update_stage(stage, "SKIPPED", message)

    def _terminate_process_group(self, proc: subprocess.Popen) -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 1.0
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _run_adapter(
        self,
        action: str,
        *,
        operation_timeout: int | None = None,
        cancel_interruptible: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> AdapterResult:
        try:
            self.result_path.unlink()
        except FileNotFoundError:
            pass
        env = os.environ.copy()
        env.update(
            STRATEGY_LAB_STAGE_RESULT=str(self.result_path),
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
        if not self.result_path.is_file():
            raise OrchestrationError(f"Strategy Lab stage adapter did not produce a result for {action} (status {status})")
        value = _load_json(self.result_path)
        try:
            self.result_path.unlink()
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
        quic = _load_json(self.job_dir / "quic.json").get("status", "")
        udp = _load_json(self.job_dir / "udp.json").get("status", "")
        if not isinstance(quic, str) or not isinstance(udp, str):
            raise OrchestrationError("Strategy Lab extended status summary is invalid")
        if self.language == "ru":
            message = f"PASS — Расширенная проверка завершена; QUIC={quic}, UDP={udp}."
        else:
            message = f"PASS — Extended testing completed; QUIC={quic}, UDP={udp}."
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
        message = terminal_message(self.language, self.mode, outcome, canceled, count)
        self.current_stage = "99"
        self._update_stage("99", report_status, message)
        # Eligibility is part of the terminal snapshot. Publish it before changing
        # state to completed/partial/error so result/status readers never observe
        # a terminal job with stale circular_eligibility fields.
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
                self._update_stage(exc.stage, "FAIL", _message(self.language, "timeout"))
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "timeout_skip"))
            except Exception:
                pass
            return self.finish("TIMEOUT", False)
        except SignalRequested:
            try:
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "cancel_skip"))
            except Exception:
                pass
            return self.finish("PARTIAL", True)
        except Exception:
            try:
                if self.current_stage in STAGE_ORDER:
                    self._update_stage(self.current_stage, "FAIL", _message(self.language, "internal"))
                state_persistence.skip_unfinished(self.job_id, str(self.state_path), _message(self.language, "error_skip"))
            except Exception:
                pass
            return self.finish("ERROR", False)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise UsageError("orchestrate requires exactly one job id")
    return Orchestrator(args[0]).run()
