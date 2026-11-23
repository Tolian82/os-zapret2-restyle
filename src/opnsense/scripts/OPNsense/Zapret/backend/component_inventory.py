#!/usr/bin/env python3
"""TZ6v5 S04a neutral component fact classifier (NO physical authority).

This module has no filesystem, process, network, kernel, Config or FD9 access.
It is a pure typed projection of *already independently qualified* evidence
obtained by future platform-specific read-only probes. It cannot attest an
owner or authorize start, stop, restart, SIGKILL, reload or repair. Never use
the output as a replacement for the original protected FD9 owner attester.
"""
from __future__ import annotations

from collections.abc import Mapping

SCHEMA = 1
COMPONENT_ENUMS = {
    "plugin": frozenset(("installed", "absent", "unknown")),
    "engine": frozenset(("valid", "absent", "invalid", "unknown")),
    "config": frozenset(("initialized", "absent", "invalid", "unknown")),
    "manifest": frozenset(("valid", "missing", "stale", "invalid", "unknown")),
    "runtime": frozenset((
        "RUNNING", "STOPPED", "INCOMPLETE",
        "FOREIGN_OR_UNVERIFIED", "UNKNOWN",
    )),
}


class ComponentModelError(ValueError):
    """An unqualified input cannot be interpreted as component evidence."""


def classify(facts: Mapping[str, str]) -> dict:
    """Classify only validated enum facts. NEVER grant physical permissions.

    The caller must supply independent evidence from original platform
    mechanisms; this projection itself cannot verify a claimed RUNNING owner.
    Any missing, extra, wrong-typed, or unexpected value fails closed.
    """
    if type(facts) is not dict or set(facts) != set(COMPONENT_ENUMS):
        raise ComponentModelError("UNQUALIFIED_COMPONENT_FACT_KEYS")
    values = {}
    for key, choices in COMPONENT_ENUMS.items():
        value = facts[key]
        if type(value) is not str or value not in choices:
            raise ComponentModelError("UNQUALIFIED_COMPONENT_FACT_VALUE")
        values[key] = value

    runtime = values["runtime"]
    if runtime == "FOREIGN_OR_UNVERIFIED":
        code = "FOREIGN_OWNER"
    elif runtime == "INCOMPLETE":
        code = "RUNTIME_INCOMPLETE"
    elif values["plugin"] == "absent":
        code = "PLUGIN_NOT_INSTALLED"
    elif values["plugin"] == "unknown":
        code = "PLUGIN_UNVERIFIED"
    elif values["engine"] == "absent":
        code = "ENGINE_NOT_INSTALLED"
    elif values["engine"] == "invalid":
        code = "ENGINE_INVALID"
    elif values["engine"] == "unknown":
        code = "ENGINE_UNVERIFIED"
    elif values["config"] == "absent":
        code = "CONFIG_UNINITIALIZED"
    elif values["config"] == "invalid":
        code = "CONFIG_INVALID"
    elif values["config"] == "unknown":
        code = "CONFIG_UNVERIFIED"
    elif values["manifest"] == "missing":
        code = "MANIFEST_UNAVAILABLE"
    elif values["manifest"] == "stale":
        code = "MANIFEST_STALE"
    elif values["manifest"] == "invalid":
        code = "MANIFEST_INVALID"
    elif values["manifest"] == "unknown":
        code = "MANIFEST_UNVERIFIED"
    elif runtime == "UNKNOWN":
        code = "RUNTIME_UNVERIFIED"
    elif runtime == "RUNNING":
        code = "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION"
    else:
        code = "COMPONENTS_PRESENT_REQUIRES_PREFLIGHT"

    return {
        "schema": SCHEMA,
        "components": values,
        "classification": code,
        "authorization": "NONE",
        "physical_transition_allowed": False,
        "original_fd9_attestation_required": True,
    }
