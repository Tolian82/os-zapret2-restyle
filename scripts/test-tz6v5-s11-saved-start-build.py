#!/usr/bin/env python3
"""S11 read-only original saved-unchanged Auto Start build admission scope."""
import copy
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
    "src/opnsense/scripts/OPNsense/Zapret/backend"))
from shared_apply_operation import (
    _saved_start_plan_scope, SharedOperationError, native_bound_saved_start_build_gate)

digest = "b" * 64
candidate = {"general": {"enabled": "1"}, "hostlist": {"mode": "auto"}}
plan = {"page": "strategies", "result": "prepared", "dependencies": digest,
        "changed_fields": [], "candidate": candidate}
_saved_start_plan_scope(plan, digest)
options = {"all": {"selected": "0"}, "list": {"selected": "0"},
           "auto": {"selected": "1"}}
_saved_start_plan_scope({**plan, "candidate": {**candidate, "hostlist": {"mode": options}}}, digest)
bad = [
    {**plan, "page": "voice"},
    {**plan, "changed_fields": ["general.enabled"]},
    {**plan, "dependencies": "c" * 64},
    {**plan, "found_intent": {}},
    {**plan, "found_batch": {}},
    {**plan, "candidate": {**candidate, "general": {"enabled": "0"}}},
    {**plan, "candidate": {**candidate, "hostlist": {"mode": "list"}}},
    {**plan, "candidate": {**candidate, "hostlist": {"mode": {"auto": {"selected": "1"}, "all": {"selected": "1"}}}}},
]
for item in bad:
    try:
        _saved_start_plan_scope(item, digest)
    except SharedOperationError:
        continue
    raise AssertionError("S11 SAVED START ACCEPTED INVALID DETACHED PLAN")
with patch("shared_apply_operation.sys.platform", "linux"):
    try:
        native_bound_saved_start_build_gate("a" * 32)
    except SharedOperationError:
        pass
    else:
        raise AssertionError("S11 non-native admission was allowed")
print("S11_SAVED_START_BUILD_READONLY_SOURCE=PASS")
