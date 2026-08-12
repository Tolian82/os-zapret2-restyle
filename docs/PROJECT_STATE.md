# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered: Where is the project now?

Read after `AGENTS.md` and `docs/INDEX.md`. Historical implementation detail belongs in
`docs/patches/`, `docs/devlog/` and `docs/verification/evidence/` and must not override a
later current patch/live record.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=26`
Current source candidate: `os-zapret2-restyle-0.4.0_26.pkg`
Latest published testing prerelease: `v0.4.0_26`
Latest owner-tested testing candidate: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Published `_26` identity:

- runtime commit `8ada9cba28916fff506f19b34f5ef3de16e2008e`;
- runtime tree `170c54cb8b8a354e4052898ea5db8b1e36a1bb61`;
- package `os-zapret2-restyle-0.4.0_26.pkg`;
- size `180306` bytes;
- digest `sha256:f5466c21c014bf594afcc80aac49b948db45513b33fe46d4857eded75bc8af8c`;
- publication workflow run `31584348303` — SUCCESS;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md`.

Latest accepted owner-live evidence:
`docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Current `_26` authority:

- `docs/patches/v0.4.0_26.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py`;
- `scripts/test-strategy-lab-adaptive-budget.sh`.

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate. `_26` does not change this architecture.

==================================================
ACCEPTED `_26` OWNER-LIVE BASELINE
==================================================

Extended `telegram.org`, `job.xhdgCU`:

- `adaptive-budget.json` persisted `policy=eligible-work-v1`;
- measured matrix: Extended, 2 endpoints, IPv4 available, IPv6 unavailable, QUIC/IPv4 closed,
  Generic UDP unconfigured;
- all adaptive additions were zero for that measured topology;
- effective budgets were exactly Standard `150 s`, Extended `120 s`, search `270 s`,
  Stage 80 `120 s`;
- `status.json` persisted the same numeric budgets and deadlines anchored to the original
  `started_at`;
- telemetry recorded `phase=budget_adaptation`, `stage=30`, `outcome=pass` with the same plan;
- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- `stopped_reason=graph_exhausted`;
- 16/16 candidates completed, zero winners;
- `.parallel.fallbacks=[]` — no Model-B or cold-Model-A fallback;
- Stage 60 duration `34209 ms`;
- total job duration `114644 ms`;
- final outcome `NO_CANDIDATE`;
- `_25` lease wrapper remained active with `policy=preferred-free-else-alternate` and
  `foreign_port_action=skip-only`;
- Stage 90 restoration succeeded;
- post-job Zapret2 remained RUNNING, pid `78016` at observation time;
- rules `19128-19130` left no residue.

This closes the selected `_26` production-wiring gate. Optional IPv6/QUIC/Generic-UDP
increments were correctly not charged because those branches were not eligible on this run;
their deterministic arithmetic remains covered by the focused `_26` source contract.

The accepted `_25` owner-live record remains the immediately preceding no-fallback timing
baseline at `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

==================================================
CURRENT `_26` CHANGE
==================================================

`_26` implements **adaptive finite Strategy Lab parent budgets derived after Stage 30 from
measured eligible work**. It does not increase one global timeout blindly and does not change
candidate/search semantics.

The persisted input matrix is:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

Policy identifier: `eligible-work-v1`.

The configured base budgets remain the calibrated floor:

- Standard `150 s`;
- Extended increment `120 s`;
- Stage 80 `120 s`;
- reference topology: up to two endpoints.

Measured optional work adds only bounded branch-specific headroom:

- each endpoint beyond two: `+30 s` Standard and `+15 s` Extended;
- available IPv6: `+5 s` per endpoint to the Standard parent for AAAA/TLSv6 baseline work;
- available Extended QUIC: `+20 s` from four candidates × the existing `5 s` envelope;
- configured Extended Generic UDP: `+15 s` from three candidates × the existing `5 s` envelope.

For the accepted two-endpoint IPv4-only/QUIC-closed/no-UDP topology, `_26` keeps exactly
`150 + 120 = 270 s` total and `120 s` Stage-80 parent; owner-live `job.xhdgCU` confirmed this
production behavior. A two-endpoint Extended job with IPv6, QUIC and Generic UDP all eligible
receives `160 + 155 = 315 s`, with Stage 80 `155 s` by deterministic source contract.

The adaptive plan is applied only after Stage-30 PASS. Deadlines remain anchored to the
original job start epoch; Stage 30 never resets the clock. The plan is persisted as
`adaptive-budget.json`, effective numeric deadlines remain in `status.json`, and
`timing-telemetry.json` receives a `budget_adaptation` event.

Stage 60 remains Model C -> Model B -> cold Model A. `_25` free-port leasing, exact endpoint/
source-port attribution, Stage 70/80/85 semantics, cancellation and Stage-90 restoration are
unchanged.

==================================================
CURRENT VERIFICATION BOUNDARY
==================================================

All selected `_26` gates are complete:

- focused adaptive-budget contract — PASS;
- canonical Strategy Lab corrective matrix — PASS;
- Python orchestration/migration continuity — PASS;
- FreeBSD 15 package contract/build — PASS;
- PR #182 squash merge — PASS;
- testing prerelease `v0.4.0_26` — PUBLISHED and verified;
- owner-live Extended `telegram.org`, `job.xhdgCU` — PASS;
- adaptive matrix/budget persistence — PASS;
- production Model C no-fallback path — PASS;
- Stage-90 restoration and temporary-rule cleanup — PASS.

`v0.4.0_26` is therefore the current published and owner-tested Strategy Lab candidate.
No new package revision is justified by this docs-only acceptance closeout.
