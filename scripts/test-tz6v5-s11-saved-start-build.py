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
    _saved_start_plan_scope, SharedOperationError,
    native_bound_saved_start_build_gate, native_bound_saved_start_sealed_gate,
    native_bound_saved_start_record_prepared)

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
    try:
        native_bound_saved_start_sealed_gate("a" * 32)
    except SharedOperationError:
        pass
    else:
        raise AssertionError("S11 non-native sealed successor was allowed")
    try:
        native_bound_saved_start_record_prepared("a" * 32)
    except SharedOperationError:
        pass
    else:
        raise AssertionError("S11 non-native original WAL mutation was allowed")
# An invented source frame or nonnative caller must never bind a WAL.
from neutral_shared_apply_source_gate import (
    native_bind_saved_start_prepared_fd9, OriginalSourceGateRefused)
with patch("neutral_shared_apply_source_gate.sys.platform", "linux"):
    try:
        native_bind_saved_start_prepared_fd9("a" * 32, b"")
    except OriginalSourceGateRefused:
        pass
    else:
        raise AssertionError("S11 non-FreeBSD root bind accepted")
# The S10 authorizing witness is BoundRootReceipt (not the pre-stage
# PreparedRootReceipt); its safety bits remain NONE and False.
from dataclasses import replace
from neutral_shared_apply_source_gate import (
    SourceGateReceipt, _saved_start_bound_receipt_qualified)
from neutral_root_bound_preflight import BoundRootReceipt
from neutral_root_stage import PreparedRootReceipt
gen = "a" * 32
oldgen = "c" * 32
root = "d" * 64
seal = "e" * 64
old = {"id": oldgen, "page": "strategies", "base": digest,
       "candidate": digest, "changed_fields": []}
detail = {"id": gen, "page": "strategies", "base": digest,
          "candidate": digest, "changed_fields": []}
before = {"schema": 1, "phase": "prepared", "detail": detail,
          "previous": old, "previous_manifest": {
              "schema": 2, "generation": oldgen, "root_sha256": root,
              "seal_sha256": seal, "candidate_sha256": digest}}
bound = {**before, "manifest": {
    "schema": 2, "generation": gen, "root_sha256": root,
    "seal_sha256": seal, "candidate_sha256": digest}}
source = SourceGateReceipt("auto", digest, (),
    generation=gen, requested_enabled=True, native_candidate_sha256=digest)
receipt = BoundRootReceipt(gen, root, seal, digest)
assert _saved_start_bound_receipt_qualified(source, receipt, bound, before, gen) is True
for mismatch in (
    PreparedRootReceipt(gen, root, seal, digest),
    replace(receipt, generation=oldgen),
    replace(receipt, physical_transition_allowed=True),
    replace(receipt, promotion_allowed=True),
    replace(receipt, authorization="START"),
    replace(receipt, native_owner_preflight_required=False),
    replace(receipt, root_sha256="f" * 64),
    replace(receipt, original_seal_sha256="f" * 64),
    replace(receipt, original_candidate_sha256="f" * 64),
):
    try:
        _saved_start_bound_receipt_qualified(source, mismatch, bound, before, gen)
    except OriginalSourceGateRefused:
        pass
    else:
        raise AssertionError("S11 accepted wrong S10 bound receipt")
try:
    _saved_start_bound_receipt_qualified(source, receipt,
        {**bound, "phase": "activating"}, before, gen)
except OriginalSourceGateRefused:
    pass
else:
    raise AssertionError("S11 accepted prematurely activating bound WAL")

# The native FD3/FD4 prelaunch guard is not a portable or public actuator.
from auto_detect_effective_known import native_attest_saved_start_locked, EffectiveKnownRefused
with patch("auto_detect_effective_known.sys.platform", "linux"):
    try:
        native_attest_saved_start_locked("a" * 32, digest, config_fd=4, queue_fd=3)
    except EffectiveKnownRefused:
        pass
    else:
        raise AssertionError("S11 non-FreeBSD inherited lock gate accepted")
print("S11_SAVED_START_BUILD_READONLY_SOURCE=PASS")
