#!/usr/bin/env python3
"""Read qualified terminal failures from the original lifecycle owners."""
from __future__ import annotations

from pathlib import Path
import re

from component_inventory import classify
from component_inventory_opnsense import _read_fixed, probe_engine

_CODES = {
    "restore-failed": ("RESTORE_FAILED",
                       "Original Apply rollback failed; operator review required"),
    "requires-review": ("APPLY_REQUIRES_REVIEW",
                        "Original Apply requires operator review"),
}


_SETUP_RELEASE_LIST_FAILURE = re.compile(
    rb"failed\ncause=release-list-unavailable\n(?:operation=([0-9a-f]{32})\n)?"
)
SETUP_STATUS = Path("/var/db/zapret2-restyle/setup.status")
SETUP_PID = Path("/var/run/zapret2-restyle/setup.pid")


def _setup_worker_absent() -> bool:
    # Treat any launcher PID file as potentially active. Status does not
    # inspect its contents, match a process or repair a stale file.
    try:
        SETUP_PID.lstat()
    except FileNotFoundError:
        return True
    return False


def _read_setup_failure(facts: dict) -> dict | None:
    if (facts["plugin"], facts["engine"], facts["manifest"], facts["runtime"]) != (
            "installed", "absent", "missing", "STOPPED"):
        return None
    if not _setup_worker_absent():
        return None
    try:
        before = SETUP_STATUS.lstat()
        record = _read_fixed(SETUP_STATUS, 128, 0)
    except FileNotFoundError:
        return None
    matched = _SETUP_RELEASE_LIST_FAILURE.fullmatch(record)
    if matched is None:
        return None
    if _read_fixed(SETUP_STATUS, 128, 0) != record:
        raise ValueError("RACING_ORIGINAL_SETUP_STATUS")
    after = SETUP_STATUS.lstat()
    if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("RACING_ORIGINAL_SETUP_STATUS")
    if not _setup_worker_absent() or probe_engine() != "absent":
        return None
    return {
        "source": "original-setup-status",
        "action": "setup-install", "stage": "install",
        "code": "SETUP_RELEASE_LIST_UNAVAILABLE",
        "message": "Last recorded first install could not obtain the stable release list",
        "operation_id": matched[1].decode("ascii") if matched[1] is not None else None,
        "timestamp": None, "generation": None,
        "exit_status": None, "runtime_before": None, "runtime_after": None,
        "verification": "refused", "stderr_excerpt": None, "log_ref": None,
    }


def read_qualified_failure(report: dict, *, reader=None) -> dict | None:
    """Return exactly one original qualified failure; errors fail to unknown.

    report must be a complete genuine S04 model, not caller-supplied runtime
    labels. Recheck the original file before and after projection; a changing
    original journal may not be interpreted as the most recent stable event.
    """
    if type(report) is not dict or report != classify(report.get("components")):
        raise ValueError("S05B_UNTRUSTED_COMPONENT_EVIDENCE")
    facts = report["components"]
    # A pending/failed journal is already classified as stale+incomplete by
    # the S04 original reader. Foreign IPFW, a healthy RUNNING state and an
    # incomplete state with a DIFFERENT cause cannot authorize this diagnosis.
    pending = facts["runtime"] == "INCOMPLETE" and facts["manifest"] == "stale"
    stopped = facts["runtime"] == "STOPPED" and facts["manifest"] == "valid"
    if not (pending or stopped):
        return _read_setup_failure(facts)
    from shared_apply_operation import SharedApplyOperation, _validate_record
    if reader is None:
        reader = lambda: SharedApplyOperation(owner=0).read()
    first = reader()
    if first is None:
        return None
    stable = _validate_record(first)
    phase = stable["phase"]
    if stopped:
        if phase != "committed" or "failure" not in stable:
            return None
        if reader() != first:
            raise ValueError("S05B_RACING_ORIGINAL_EXIT_JOURNAL")
        event = stable["failure"]
        return {
            "source": "original-shared-apply-journal",
            "action": "runtime-failure", "stage": "engine-stop",
            "code": event["code"],
            "message": "Original supervisor observed engine exit after ready",
            "operation_id": event["operation_id"],
            "timestamp": event["observed_at"],
            "generation": None, "exit_status": None,
            "runtime_before": "RUNNING", "runtime_after": "STOPPED",
            "verification": "uncertain",
            "stderr_excerpt": None, "log_ref": None,
        }
    if phase == "requires-review" and "failure" in stable:
        # The original launcher attested only a failed readiness check;
        # absence of a live PID cannot prove child exit or native exit rc.
        event = stable["failure"]
        if reader() != first:
            raise ValueError("S05B_RACING_ORIGINAL_EARLY_JOURNAL")
        return {
            "source": "original-shared-apply-journal",
            "action": "voice-apply" if stable["detail"]["page"] == "voice" else "apply",
            "stage": "engine-start",
            "code": event["code"],
            "message": ("Original engine did not produce a verified live PID"
                        if event["cause"] == "no-live-pid" else
                        "Original engine lost verified readiness during startup"),
            "operation_id": event["operation_id"],
            "timestamp": event["observed_at"],
            "generation": None, "exit_status": None,
            "runtime_before": None, "runtime_after": "INCOMPLETE",
            "verification": "uncertain",
            "stderr_excerpt": None, "log_ref": None,
        }
    if phase not in _CODES:
        return None
    if reader() != first:
        raise ValueError("S05B_RACING_ORIGINAL_APPLY_JOURNAL")
    # _validate_record has already established exact schema, safe op ID and
    # page; neither candidate SHA nor raw changed_fields enter public Status.
    code, message = _CODES[phase]
    return {
        "source": "original-shared-apply-journal",
        "action": "voice-apply" if stable["detail"]["page"] == "voice" else "apply",
        "stage": "apply",
        "code": code,
        "message": message,
        "operation_id": stable["detail"]["id"],
        "timestamp": None,  # original journal has NO event timestamp
        "generation": None,  # candidate hash is NOT a verified live generation
        "exit_status": None,  # original journal stores NO native process exit rc
        "runtime_before": None,
        "runtime_after": "INCOMPLETE",
        "verification": "uncertain",
        "stderr_excerpt": None,
        "log_ref": None,
    }
