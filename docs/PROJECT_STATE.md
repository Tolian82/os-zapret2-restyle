# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_18.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–4 are complete in source.

Completed corrective contracts:

- authoritative corrective architecture and audit baseline;
- atomic localized cancel persistence;
- bounded cancellation of active stage 60, 70, and 80 process trees;
- one explicit monotonic active stage sequence;
- stage 80 precedes final shortlist stage 85;
- standard mode records stage 80 as skipped;
- worker finalization no longer calls load-order hook entrypoints.

Open corrective findings:

- normal completion is still reported as `PARTIAL`;
- final messages still depend on successive message modules;
- extended work can exceed the documented time budget;
- `RESTORE_FAILED` can still be represented as normal completion;
- restoration evidence and circular eligibility are weaker than the approved contract;
- IP target semantics are implicit;
- tests do not yet execute the complete API-to-worker state machine.

Corrective authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=18`. No tag, release, release asset, or pkg-repository publication is authorized while the corrective series is active.

Next action: Corrective Patch 5 — truthful terminal state, outcome, and localized message generation. Owner-assisted live OPNsense verification remains deferred until every corrective implementation patch has completed the serial GitHub delivery gate.
