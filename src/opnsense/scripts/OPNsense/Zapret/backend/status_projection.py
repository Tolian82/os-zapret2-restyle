#!/usr/bin/env python3
"""TZ6v5 S05a pure, non-authorizing read-only Status projection.

Only the previously physically qualified S04 inventory may supply component
facts. Do not turn the projection into FD9/PID/IPFW/Config ownership authority.
No diagnostic producer is claimed: absent verified event means null fields.
"""
from __future__ import annotations

from datetime import datetime, timezone
from component_inventory import classify

SCHEMA = 1
RESULT_KEYS = frozenset(("schema", "components", "classification", "authorization",
                          "physical_transition_allowed",
                          "original_fd9_attestation_required"))
EXIT = {"RUNNING": 0, "STOPPED": 1, "INCOMPLETE": 2,
        "FOREIGN_OR_UNVERIFIED": 2, "UNKNOWN": 2}
SAFE_MESSAGES = {
    "RUNNING": "Original Common runtime verified running",
    "STOPPED": "No active Common runtime confirmed",
    "INCOMPLETE": "Runtime evidence incomplete",
    "FOREIGN_OR_UNVERIFIED": "Foreign or unverified runtime ownership",
    "UNKNOWN": "Runtime state could not be verified",
}


class StatusProjectionError(ValueError):
    pass


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def project(report: dict, observed_at: str) -> dict:
    if type(report) is not dict or set(report) != RESULT_KEYS:
        raise StatusProjectionError("STATUS_INVALID_S04_REPORT")
    if report["schema"] != 1 or type(report["schema"]) is not int or (
        report["authorization"] != "NONE" or
        report["physical_transition_allowed"] is not False or
        report["original_fd9_attestation_required"] is not True
    ):
        raise StatusProjectionError("STATUS_S04_AUTHORITY_REFUSED")
    expected = classify(report["components"])
    if report != expected:
        raise StatusProjectionError("STATUS_S04_FACTS_MISMATCH")
    if type(observed_at) is not str or len(observed_at) != 20 or not (
        observed_at.endswith("Z") and
        observed_at[4] == "-" and observed_at[7] == "-" and
        observed_at[10] == "T"
    ):
        raise StatusProjectionError("STATUS_TIMESTAMP_UNQUALIFIED")
    runtime = report["components"]["runtime"]
    return {
        "schema": SCHEMA,
        "timestamp": observed_at,
        "runtime_state": runtime,
        "status_exit_code": EXIT[runtime],
        "verification": "verified" if runtime in ("RUNNING", "STOPPED") else "uncertain",
        "components": report["components"],
        "code": report["classification"],
        "message": SAFE_MESSAGES[runtime],
        # The actual original producer/receipt is not yet connected. Never
        # synthesize an operation, diagnostic stage, generation or exit status.
        "stage": None, "operation_id": None, "generation": None,
        "exit_status": None, "stderr_excerpt": None, "log_ref": None,
        "requested": None, "effective": None,
        # Additive S05b1 field: a NULL here means no *qualified* existing
        # receipt, never proof that the engine experienced no failure.
        "last_error": None, "diagnostic_state": "not-qualified",
        "authorization": "NONE",
        "physical_transition_allowed": False,
    }


def unavailable(observed_at: str) -> dict:
    facts = {"plugin": "unknown", "engine": "unknown",
             "config": "unknown", "manifest": "unknown", "runtime": "UNKNOWN"}
    report = project(classify(facts), observed_at)
    report["code"] = "STATUS_UNAVAILABLE"
    report["diagnostic_state"] = "unavailable"
    report["message"] = "Read-only status evidence unavailable"
    return report
