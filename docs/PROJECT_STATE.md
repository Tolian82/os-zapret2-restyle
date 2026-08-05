# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_15.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Patch 13 activated Strategy Lab on the Diagnostics page and retired the synchronous Blockcheck integration.

The 2026-08-05 source audit confirmed that the repository is structurally complete and buildable, but the activated Strategy Lab is not yet contract-complete. The approved corrective series is now active.

Open corrective findings include:

- cancel state is not persisted atomically;
- active stage 60, 70, and 80 runners are not cancellation-aware;
- normal completion is always reported as `PARTIAL`;
- final messages can be factually wrong because of module override order;
- stage 85 can execute before stage 80;
- extended work can exceed the documented time budget;
- `RESTORE_FAILED` can be represented as normal completion;
- restoration evidence and circular eligibility are weaker than the approved contract;
- IP target semantics are implicit;
- tests do not execute the complete state machine.

Corrective authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=15`. No tag, release, release asset, or pkg-repository publication is authorized while the corrective series is active.

Next action: Patch 2 of the corrective series — atomically persist Strategy Lab cancellation state. Owner-assisted live OPNsense verification remains deferred until every corrective implementation patch has completed the serial GitHub delivery gate.
