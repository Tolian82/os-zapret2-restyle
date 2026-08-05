# Audit update — Strategy Lab end-to-end integration

Date: 2026-08-05
Corrective patch: 10
Finding: `SL-COR-009`

## Source remediation

The repository now contains one mock-driven integration harness that traverses the active chain:

```text
API/configd facade -> launcher -> lifecycle transaction -> worker
-> stages 00–99 -> status/result polling -> optional circular start/stop
```

The harness uses the real Strategy Lab launcher, worker, state machine, probe runner, result persistence, lifecycle restoration code, query endpoints, and circular launcher. Only external OPNsense/system/network dependencies and candidate catalogs are replaced by deterministic mocks.

It validates:

- standard success;
- extended success;
- no stable candidate;
- target already accessible;
- internal worker error;
- timeout;
- restoration failure;
- initial RUNNING restoration;
- initial STOPPED preservation;
- exact first-occurrence stage event order;
- persisted terminal JSON;
- saved Traffic Strategy immutability;
- latest-job polling recovery after page reload;
- true `idle` only when neither active nor persisted jobs exist;
- circular start, status, stop, and cleanup;
- absence of active-job, candidate-pid, and temporary-process residue.

The integration gate also executes the focused active-cancellation, shared-budget, semantic-restoration, and candidate-runtime cleanup suites.

## Product correction discovered by the harness

The previous `status -` path returned `idle` once a terminal job cleared the active marker. The query backend now returns the newest persisted job when no active job exists, allowing the existing Diagnostics page reload path to recover terminal progress and results. A completely empty job store still returns `idle`.

## Remaining boundary

Corrective Patch 11 is repository hygiene and authority cleanup. Live OPNsense validation remains the final owner-assisted gate after the source series is complete.
