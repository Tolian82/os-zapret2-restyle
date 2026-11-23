#!/usr/bin/env python3
"""TZ6v5 S05b1: one read-only qualified error from original SharedApply journal.

No independent writer, PID match, file discovery, FD9 or invented dvtws2 rc.
The original SharedApplyOperation validates the *root-owned* fixed journal.
Only explicit terminal failure phases are errors: PREPARED is not failure.
"""
from __future__ import annotations

from component_inventory import classify

_CODES = {
    "restore-failed": ("APPLY_ROLLBACK_FAILED",
                       "Original Apply rollback failed; operator review required"),
    "requires-review": ("APPLY_REQUIRES_REVIEW",
                        "Original Apply requires operator review"),
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
    if facts["runtime"] != "INCOMPLETE" or facts["manifest"] != "stale":
        return None
    from shared_apply_operation import SharedApplyOperation, _validate_record
    if reader is None:
        reader = lambda: SharedApplyOperation(owner=0).read()
    first = reader()
    if first is None:
        return None
    stable = _validate_record(first)
    phase = stable["phase"]
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
