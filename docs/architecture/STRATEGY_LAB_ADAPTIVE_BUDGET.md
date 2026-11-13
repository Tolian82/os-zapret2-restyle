# Strategy Lab — finite family-qualified job budgets

**Status:** CURRENT CONTRACT. Production policy is `eligible-families-v2`, schema 2, owned by [adaptive_budget.py](../../src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py). [DS-25/DS-26](ZAPRET2_EXCLUDE_IPSET_SPEC.md) own the accepted family/budget requirements. The former `eligible-work-v1` endpoint/protocol bonuses and Stage-30 handoff are [historical](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).

## Ownership and eligibility

Budget policy owns finite parent envelopes and child admission. It does not select/rank candidates, change Model-C production, reinterpret network outcomes or replace restoration. Every deadline stays anchored to the original job `started_epoch`; adaptation never restarts the clock.

The current `AdaptiveBudgetOrchestrator` adapts after Stage 40 returns without a terminal outcome. It requires resolved endpoints and an available selected family. IPv6 route availability or a checked box alone does not earn extra time. The matrix uses `ipv6_enabled`, target kind, selected network and actual Stage-40 endpoint-family evidence with PASS/FAIL observations. Missing per-family evidence earns no dual-family bonus while preserving otherwise valid IPv4 jobs. IPv6-only operation requires its opted-in available family and evidence; IPv4 is no longer universally mandatory.

## Single per-job envelope

| Mode | One eligible family, including IPv6-only | Eligible A+AAAA work |
|---|---:|---:|
| Standard | 150 seconds | 200 seconds |
| Extended, total | 270 seconds | 350 seconds |

Default Standard/Extended portions are 150/120 seconds. Dual-family work adds 50 seconds to Standard and 30 to the Extended portion, producing 200+150=350. Stage 80 remains within the Extended portion and the overall parent. The calculator keeps lower configured test budgets and caps original portions with `min(base, 150)` / `min(base, 120)` before the family addition. Cached original bases prevent compounding on recalculation.

Extra endpoint count, QUIC availability and Generic UDP configuration remain observable workload dimensions but do not add independent job-wide bonuses. A domain without eligible AAAA work, an IPv4 literal, checked-only IPv6 or a lone IPv6 literal keeps a single-family envelope.

## Deadlines and persisted evidence

`standard_deadline = started_epoch + effective_standard`; the Standard overall deadline is the same. Extended overall deadline is `started_epoch + effective_standard + effective_extended`. A Stage-80 operation is bounded by both its finite local parent and overall deadline. Candidate/child bounds remain below their stage/job parents.

`adaptive-budget.json` records schema/policy, requested IPv6, eligible family matrix, original bases, the two family additions and effective Standard/Extended/search/Stage-80 seconds. Existing status fields and telemetry expose the effective budget/deadlines. Malformed required state or no available selected network family fails explicitly; old jobs never provide current capability evidence.

## Verification and history

[Existing adaptive-budget regression](../../scripts/test-strategy-lab-adaptive-budget.sh) verifies the current calculator. Current qualified native/owner evidence belongs to PROJECT_STATE and the dual-stack records; the old `_26` owner result is evidence for its historical `eligible-work-v1` topology, not a new run of v2. This documentation correction changes no runtime policy or tests.
