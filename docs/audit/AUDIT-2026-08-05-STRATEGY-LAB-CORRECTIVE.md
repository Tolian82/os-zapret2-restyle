# Audit — Strategy Lab corrective baseline

Date: 2026-08-05
Baseline: `main` at `2cd12ee45ea99a0e3b23647a72b3af9d611db706`
Package candidate: `0.3.2_15`

## Scope

This audit records the source defects that must be corrected before owner-assisted live
OPNsense verification of the activated Strategy Lab.

## Repository integrity

The repository is structurally complete and the current package candidate is buildable.
The asynchronous API, configd actions, worker modules, candidate runtime, GUI polling,
circular controls, tests, and package inclusion paths are present. The synchronous
Blockcheck integration has been removed from the active product path.

No open pull request or parallel branch contains a ready corrective implementation for
the defects below. Useful historical lifecycle and regression patterns from old branches
already exist in `main`; old branches must not be merged wholesale.

## Findings

### SL-COR-001 — Cancel transition is not persisted

The cancel path creates the cancel file and prints modified JSON, but does not atomically
replace the persisted status snapshot. A subsequent status poll may return the previous
state.

Severity: critical.

### SL-COR-002 — Active probes are not cancellation-aware

The worker checks cancellation at early stage boundaries, but long stage 60, 70, and 80
runners can continue until their own timeout. Final processing can lose cancellation
semantics and finish as ordinary partial work.

Severity: critical.

### SL-COR-003 — Normal completion is always PARTIAL

The worker flow unconditionally finishes the post-search path with `outcome=PARTIAL`.
It does not distinguish successful shortlist, no candidate, or a genuinely incomplete
result.

Severity: critical.

### SL-COR-004 — Final messages are load-order dependent

Successive message modules override the same variables. The last loaded UDP message can
claim that all extended branches ran in standard mode and that circular validation is
inactive although it is active.

Severity: high.

### SL-COR-005 — Stage order is non-monotonic

The current override chain can execute stage 85 shortlist before stage 80 extended
branches. `current_stage` can therefore move backward and circular controls may become
visible before restoration.

Severity: high.

### SL-COR-006 — Extended timeout exceeds the documented budget

TLS/HTTP, QUIC, and UDP runners can each receive the full stage-80 timeout. The extended
stage can consume approximately three times its documented 120-second budget. No single
overall worker deadline closes the gap.

Severity: critical.

### SL-COR-007 — RESTORE_FAILED can be represented as completed

Finalization changes the outcome to `RESTORE_FAILED` but still writes terminal
`state=completed`.

Severity: critical.

### SL-COR-008 — Restoration evidence is weaker than the promise

The implementation primarily snapshots aggregate RUNNING/STOPPED state. The documented
contract promises enough runtime, supervisor, process, and firewall evidence to verify
semantic restoration and absence of temporary state.

Severity: high.

### SL-COR-009 — Circular eligibility is checked too early

The GUI reveals circular controls from target type and shortlist length without requiring
a successful terminal job and successful stage 90. Backend eligibility must be the
authoritative gate.

Severity: high.

### SL-COR-010 — IP target behavior contains hidden assumptions

The current backend can accept an IP target while implicitly using TCP/443 semantics.
An IP target needs explicit port and probe semantics and must not silently invent DNS or
SNI behavior.

Severity: medium.

### SL-COR-011 — Test coverage codifies intermediate behavior

Existing tests are focused and useful, but they do not execute the complete API-to-worker
state machine. Some lifecycle tests explicitly expect the stale `PARTIAL` outcome, and
cancel coverage uses an early artificial hold rather than an active stage 60/70/80
operation.

Severity: critical.

### REPO-HYG-001 — Stale tracked backup

`docs/PROJECT_STATE.md.orig` is a stale tracked backup and creates document-authority
ambiguity. It is not included in the package runtime, but should be removed in a separate
repository-hygiene patch.

Severity: low.

## Corrective authority

The required behavior and serial patch order are defined in:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`.

## Verification gate

This audit remains open until:

- all corrective patches are squash merged;
- all pull-request and post-merge workflows pass;
- the final integration regression matrix passes;
- owner-assisted live OPNsense verification confirms active cancellation, bounded
  timing, exact semantic restoration, circular start/stop, cleanup, and saved Traffic
  Strategy immutability.
