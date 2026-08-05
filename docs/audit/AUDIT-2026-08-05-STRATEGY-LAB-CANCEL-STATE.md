# Audit update — Strategy Lab cancel-state persistence

Date: 2026-08-05
Corrective patch: 2
Finding: `SL-COR-001`

## Source remediation

`SL-COR-001 — Cancel transition is not persisted` is remediated in source.

The cancel endpoint now:

- writes the cancellation control atomically;
- persists `state=cancel_requested` and `cancel_requested=true` through atomic replacement;
- records the first UTC cancel-request timestamp;
- records a localized message;
- returns the exact persisted snapshot;
- preserves the first timestamp across repeated requests;
- does not mutate terminal jobs;
- preserves or reasserts the request after a late non-terminal update.

## Automated evidence

`scripts/test-strategy-lab-cancel-state.sh` covers persisted response equality, repeated cancel, localization, concurrent polling, late worker updates, terminal immutability, valid JSON, and temporary-file cleanup.

## Remaining boundary

This patch does not claim that an already running stage 60, 70, or 80 child process stops promptly. `SL-COR-002` remains open and is the next corrective patch.

## Verification status

Remediated in source; pull-request and post-merge CI/package gates are required. Owner-assisted live OPNsense verification remains deferred until the full corrective series is complete.
