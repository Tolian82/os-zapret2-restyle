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
Latest published testing prerelease: `v0.4.0_25`
Latest owner-tested testing candidate: `v0.4.0_25` — source-port lease corrective owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Latest published/owner-live evidence:

- `_25` runtime commit `a5ecfbfd57820e30e5f2be450e510b96c00267e3`;
- `_25` package `os-zapret2-restyle-0.4.0_25.pkg`;
- publication: `docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`;
- owner-live PASS: `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

Current `_26` authority:

- `docs/patches/v0.4.0_26.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
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
ACCEPTED `_25` OWNER-LIVE BASELINE
==================================================

Extended `telegram.org`, `job.5yGde5`:

- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- `stopped_reason=graph_exhausted`;
- 16/16 candidates completed, zero winners;
- `.parallel.fallbacks=[]` — no Model-B or cold-Model-A fallback;
- Stage 60 duration `34198 ms`;
- total job duration `114759 ms`;
- final outcome `NO_CANDIDATE`;
- all six batches persisted `_25` lease evidence with
  `policy=preferred-free-else-alternate` and `foreign_port_action=skip-only`;
- this run encountered no occupied preferred port, so `collisions=[]` and
  `replacement_count=0` in every batch;
- Stage 90 restoration succeeded;
- post-job Zapret2 remained RUNNING;
- rules `19128-19130` left no residue.

This remains the clean no-fallback timing floor for `_26`. The prior `_23` shared-`42004`
collision defect is closed. Model B fallback still takes a fresh independent lease and the
focused `_25` lease test still covers alternate selection under a foreign occupied port.

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

For the accepted `_25` two-endpoint IPv4-only/QUIC-closed/no-UDP topology, `_26` therefore
keeps the exact existing `150 + 120 = 270 s` total and `120 s` Stage-80 parent. A two-endpoint
Extended job with IPv6, QUIC and Generic UDP all eligible receives `160 + 155 = 315 s`, with
Stage 80 `155 s`.

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

Source/CI target for `_26`:

- focused `scripts/test-strategy-lab-adaptive-budget.sh`;
- canonical Strategy Lab corrective matrix;
- Python orchestration/migration continuity;
- FreeBSD 15 package contract and package build.

Owner-live remains pending until `_26` is published. The selected live gate is one Extended
`telegram.org` run that proves the production Stage-30 measurement really activates
`eligible-work-v1`, persists a work matrix matching actual capabilities, produces the exact
effective budget, finishes without a new timeout/unexpected fallback, and restores Zapret2
cleanly.

The appliance does not need to fabricate IPv6, QUIC or Generic UDP. Optional branch increments
are source-tested deterministically; live evidence verifies production wiring and the actual
measured topology.
