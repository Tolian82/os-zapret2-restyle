# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered: Where is the project now?

Read after `AGENTS.md` and `docs/INDEX.md`. Historical implementation detail belongs in
`docs/patches/`, `docs/devlog/` and `docs/verification/evidence/` and must not override a
later current patch/live/release record.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current release-preparation source line: `VERSION=0.4.1`, `PLUGIN_REVISION=1`
Current source candidate: `os-zapret2-restyle-0.4.1_1.pkg`
Previous stable release: `v0.4.0`
Latest published testing prerelease: `v0.4.0_26`
Latest owner-tested runtime candidate: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

The owner has authorized the full `v0.4.1 / 0.4.1_1` release cycle. Release preparation
promotes the already accepted `_26` runtime without adding new runtime behavior.

Release-preparation authority:

- `docs/releases/v0.4.1.md`;
- `docs/devlog/2026-08-12-release-v0.4.1.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`;
- `docs/GITHUB_PUBLICATION.md`.

Active Strategy Lab implementation authority remains:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate.

==================================================
ACCEPTED RELEASE RUNTIME BASIS — `v0.4.0_26`
==================================================

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

Extended `telegram.org`, `job.xhdgCU`:

- `adaptive-budget.json` persisted `policy=eligible-work-v1`;
- measured matrix: Extended, 2 endpoints, IPv4 available, IPv6 unavailable, QUIC/IPv4
  closed, Generic UDP unconfigured;
- effective budgets: Standard `150 s`, Extended `120 s`, search `270 s`, Stage 80 `120 s`;
- telemetry recorded `phase=budget_adaptation`, `stage=30`, `outcome=pass`;
- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- `stopped_reason=graph_exhausted`, 16/16 candidates completed, zero winners;
- `.parallel.fallbacks=[]` — no Model-B or cold-Model-A fallback;
- Stage 60 duration `34209 ms`;
- total job duration `114644 ms`;
- final outcome `NO_CANDIDATE`;
- source-port ownership remained `preferred-free-else-alternate` / `skip-only`;
- Stage 90 restoration succeeded;
- post-job Zapret2 remained RUNNING;
- rules `19128-19130` left no residue.

This closes the current adaptive-budget production-wiring risk and supplies the selected
live release basis for v0.4.1. Earlier accepted evidence retains the Model-C working path,
source-port collision correction and Model-B fallback/reference behavior.

==================================================
RELEASE CONTENT SINCE `v0.4.0`
==================================================

The 0.4.0 testing line completed the previously approved adaptive-search and runtime-model
work rather than leaving it experimental:

- Python `CandidateSpec` and job-scoped `ResourceInventory` became immutable candidate
  evidence;
- Stage 50 became prioritization evidence rather than a Stage-60 reachability hard gate;
- Stage 60 moved to a deterministic native Zapret2 graph with candidate-defined resources,
  ranges and fixed endpoint epoch;
- deadline containment, stability/finalist validation and timing telemetry were completed;
- cold Model A was measured and retained as correctness fallback/reference;
- warm Model B was proven, corrected for failed-probe attribution, parallelized at width
  three and integrated as the immediate fallback/reference;
- Model C became the preferred one-worker bucket/source-port dispatcher;
- controlled source-port leasing now uses `preferred-free-else-alternate` and a fresh lease
  for fallback models;
- `eligible-work-v1` derives finite parent budgets after Stage 30 from measured eligible
  work rather than blindly enlarging one timeout.

No package/runtime source is intentionally changed by the v0.4.1 release-preparation patch
itself; only version/release metadata, release documentation and version-aware verification
contracts change.

==================================================
CURRENT VERIFICATION / RELEASE BOUNDARY
==================================================

All selected runtime gates inherited by v0.4.1 are complete on `_26`:

- focused adaptive-budget contract — PASS;
- canonical Strategy Lab corrective matrix — PASS;
- Python orchestration/migration continuity — PASS;
- FreeBSD 15 package contract/build — PASS;
- testing prerelease `v0.4.0_26` — PUBLISHED and verified;
- owner-live Extended `telegram.org`, `job.xhdgCU` — PASS;
- production Model C no-fallback path — PASS;
- Stage-90 restoration and temporary-rule cleanup — PASS.

The release-preparation PR must now pass its current CI/FreeBSD 15 package checks and be
squash-merged with exact subject:

`v0.4.1_1: Prepare release v0.4.1`

After that merge, the repository release trigger must create immutable semantic tag
`v0.4.1` at the merge commit and the Release workflow must publish and verify:

- package `os-zapret2-restyle-0.4.1_1.pkg`;
- matching `SHA256SUMS`;
- GitHub Release assets;
- matching `FreeBSD:15:amd64` Pages/pkg repository.

The semantic release tag is `v0.4.1`; `_1` is the package revision suffix.
