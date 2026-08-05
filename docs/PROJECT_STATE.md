# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_17.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Patch 13 activated Strategy Lab on the Diagnostics page and retired the synchronous Blockcheck integration.

Corrective Patches 1–3 are complete in source:

- the authoritative corrective contract and audit baseline are recorded;
- cancel requests are persisted atomically with localization and a stable timestamp;
- expansion, stability, extended TCP, QUIC, and configured UDP runners execute through a cancellation-aware process-tree boundary;
- a persisted cancel request terminates active descendants with bounded `TERM -> grace -> KILL` handling;
- the worker receives `TERM` only after the active runner tree is reaped and then enters existing mandatory cleanup and restoration;
- cancellation behavior is covered for stages 60, 70, and every stage-80 branch.

Open corrective findings include:

- the stage machine still depends on successive shell-function overrides;
- normal completion is always reported as `PARTIAL`;
- final messages can be factually wrong because of module override order;
- stage 85 can execute before stage 80;
- extended work can exceed the documented time budget;
- `RESTORE_FAILED` can be represented as normal completion;
- restoration evidence and circular eligibility are weaker than the approved contract;
- IP target semantics are implicit;
- tests do not yet execute the complete state machine.

Corrective authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=17`. No tag, release, release asset, or pkg-repository publication is authorized while the corrective series is active.

Next action: Corrective Patch 4 — replace load-order function overrides with an explicit monotonic stage machine. Owner-assisted live OPNsense verification remains deferred until every corrective implementation patch has completed the serial GitHub delivery gate.
