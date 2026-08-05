# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_19.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–5 are complete in source.

Completed corrective contracts:

- authoritative corrective architecture and audit baseline;
- atomic localized cancel persistence;
- bounded cancellation of active stage 60, 70, and 80 process trees;
- one explicit monotonic active stage sequence;
- final shortlist built only after applicable extended work;
- truthful terminal state and outcome mapping;
- `SUCCESS` and `NO_CANDIDATE` replace the stale default `PARTIAL`;
- `TIMEOUT`, `ERROR`, and `RESTORE_FAILED` are terminal `error` results;
- final localized messages no longer depend on module load order.

Open corrective findings:

- extended work can exceed the documented time budget;
- restoration evidence is weaker than the approved semantic contract;
- circular eligibility is not yet enforced by the corrected terminal contract;
- IP target semantics are implicit;
- tests do not yet execute the complete API-to-worker state machine.

Corrective authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=19`. No tag, release, release asset, or pkg-repository publication is authorized while the corrective series is active.

Next action: Corrective Patch 6 — shared overall and stage-80 time budgets. Owner-assisted live OPNsense verification remains deferred until every corrective implementation patch has completed the serial GitHub delivery gate.
