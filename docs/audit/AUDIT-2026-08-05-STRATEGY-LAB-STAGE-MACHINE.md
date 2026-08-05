# Audit update — Explicit Strategy Lab stage machine

Date: 2026-08-05
Corrective patch: 4
Findings: `SL-COR-005` and the load-order portion of `SL-COR-004`

## Source remediation

Active worker control no longer depends on successive definitions of `strategy_lab_skip_unfinished()` or `strategy_lab_skip_remaining()` from stability, extended, QUIC, and UDP modules.

A single worker-owned stage machine now executes:

```text
60 -> 70 -> 80 -> 85
```

The complete worker progression is therefore monotonic:

```text
00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99
```

Stage 80 is explicitly skipped in standard mode. Stage 85 is not entered until stage 80 has completed or been skipped, so circular eligibility can no longer be exposed from a pre-extended shortlist merely because of hook load order.

Legacy hook definitions remain inert inside computational modules and are scheduled for removal in the repository-hygiene patch. No active worker path calls them.

## Automated evidence

`scripts/test-strategy-lab-stage-machine.sh` executes standard and extended paths with controlled runners, asserts exact stage order, and rejects active references to the old hook entrypoints.

## Remaining boundaries

- Corrective Patch 5 must replace the default `PARTIAL` result and load-order message variables.
- Corrective Patch 6 must enforce one overall deadline and one shared stage-80 budget.
- Circular backend/GUI eligibility remains Corrective Patch 8.
