# Audit update — Strategy Lab time budgets

Date: 2026-08-05
Corrective patch: 6
Finding: `SL-COR-005`

## Source remediation

Strategy Lab now records an absolute UTC search deadline when the worker starts.

The approved budgets are enforced as follows:

- standard mode receives one 150-second search budget;
- extended mode receives the same 150-second standard phase plus an additional 120-second allowance;
- stages 30, 40, 50, 60, and 70 receive the minimum of their own configured limit and the remaining standard-phase budget;
- stage 80 establishes one shared deadline and every TLS/HTTP, QUIC, and UDP branch consumes the remaining time from that same deadline;
- stage 85 cannot start after the applicable overall search deadline;
- stage 90 cleanup and semantic restoration remain outside the search deadline and therefore still run after timeout.

The persisted status document now records `started_at`, `standard_deadline_at`, `deadline_at`, standard and extended budget sizes, total search budget, and stage-80 start/deadline evidence.

## Automated evidence

`scripts/test-strategy-lab-time-budget.sh` uses a deterministic clock to verify:

- the exact 150-second standard deadline;
- the 270-second extended deadline;
- clipping of operations to the remaining standard phase;
- one shared 120-second stage-80 remainder across successive branches;
- refusal to start stage 85 after the overall deadline;
- runtime wiring of the budget module into the worker flow.

The test is part of the aggregate domain-diagnostics contract.

## Remaining boundaries

- Corrective Patch 7 must strengthen the semantic lifecycle snapshot and restoration verification.
- Corrective Patch 8 must enforce backend and GUI circular eligibility after successful restoration.
- Live OPNsense timing evidence remains deferred until the complete corrective series passes its serial source gate.
