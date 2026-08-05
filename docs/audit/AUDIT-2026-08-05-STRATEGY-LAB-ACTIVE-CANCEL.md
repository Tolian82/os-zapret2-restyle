# Audit update — Active Strategy Lab cancellation

Date: 2026-08-05
Corrective patch: 3
Finding: `SL-COR-002`

## Source remediation

`SL-COR-002 — Active probes are not cancellation-aware` is remediated in source for every currently active long search runner:

- stage 60 parameter expansion;
- stage 70 stability confirmation;
- stage 80 extended TLS/HTTP;
- stage 80 QUIC;
- stage 80 configured UDP.

The production worker now exports its PID and cancel-file path and selects dedicated wrappers around those runners. The common wrapper monitors the persisted control, terminates the complete visible descendant tree, waits a bounded grace interval, escalates remaining processes, reaps the root, and signals the worker only after cleanup.

The worker's existing signal trap remains the single transition to canceled finalization. It skips unfinished stages, invokes temporary candidate cleanup, restores the initial service state, and records the controlled partial result under the current terminal contract.

## Automated evidence

The active-cancel regression covers all five production runner classes with a real child process, verifies bounded termination and process absence, and confirms the worker trap receives control. It also checks production wiring and normal status propagation.

## Remaining boundaries

- Corrective Patch 4 must replace the load-order stage hooks.
- Corrective Patch 5 must correct final state/outcome classification.
- Corrective Patch 6 must provide a single overall deadline and shared stage-80 budget.
- Live OPNsense process, IPFW, and runtime cleanup evidence remains deferred to the final owner-assisted matrix.

## Verification status

Remediated in source; GitHub CI/package and post-merge gates remain mandatory before this finding is treated as published.
