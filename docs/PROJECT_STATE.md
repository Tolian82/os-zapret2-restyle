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
Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=1`
Current published release tag: `v0.4.1`
Current published package: `os-zapret2-restyle-0.4.1_1.pkg`
Latest owner-tested runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Published v0.4.1 identity:

- release-preparation merge `c53e1c1656517fa764f97a175bb82eea02dbc374`;
- merge tree `74e3a67cb25c0e80bc0c00f7214e8c00c3daa7b9`;
- semantic tag `v0.4.1`;
- annotated tag object `8c860a01def48a3b84943a43ba0c5a30d9f37055` targeting the exact merge;
- Release workflow run `31596979559` — SUCCESS;
- GitHub Release ID `369226460`;
- package `os-zapret2-restyle-0.4.1_1.pkg`;
- package size `180305` bytes;
- package digest `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`;
- GitHub Pages deployment `5869308071` — SUCCESS;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`.

The workflow-created GitHub Release currently has `prerelease=true`; this is the existing
release-workflow behavior and does not change the semantic tag/package identity above.

The `0.4.1_1` package has been built, checksum-verified, attached to the GitHub Release and
published to the project `FreeBSD:15:amd64` Pages/pkg repository. It has not yet been
claimed as separately installed on the owner appliance in the durable evidence record.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/patches/v0.4.0_26.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate.

==================================================
ACCEPTED OWNER-LIVE RUNTIME BASIS
==================================================

The v0.4.1 release-preparation change did not alter Strategy Lab runtime behavior beyond the
published and owner-tested `v0.4.0_26` testing line. The selected live basis remains
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

Earlier accepted evidence retains the Model-C working-candidate path, source-port collision
correction and Model-B fallback/reference behavior.

==================================================
V0.4.1 CONTENT SINCE V0.4.0
==================================================

The v0.4.1 line promotes the completed adaptive-search/runtime work from the v0.4.0 testing
series:

- immutable Python `CandidateSpec` and job-scoped `ResourceInventory` evidence;
- deterministic native Zapret2 Stage-60 graph with candidate-defined resources/ranges and
  fixed endpoint epoch;
- Stage-50 priority evidence without a Stage-60 family reachability hard gate;
- bounded deadline containment, stability/finalist validation and timing telemetry;
- measured cold Model A correctness/reference;
- accepted width-three warm Model B fallback/reference with corrected failed-probe
  attribution;
- preferred one-worker Model C dispatcher;
- `preferred-free-else-alternate` controlled source-port leasing with fresh fallback lease;
- `eligible-work-v1` finite parent budgets derived after Stage 30 from measured eligible
  work.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

The v0.4.1 release cycle is complete:

- release-preparation PR #185 — MERGED;
- required PR title/CI/FreeBSD 15 build — PASS;
- exact merge commit — VERIFIED;
- semantic tag `v0.4.1` — VERIFIED at exact merge;
- Release trigger run `31596967737` — SUCCESS;
- Release workflow run `31596979559` — SUCCESS;
- package/checksum publication — VERIFIED;
- GitHub Release publication — VERIFIED;
- Pages/pkg repository deployment — VERIFIED.

No further v0.4.1 publication work is pending. The next engineering cycle can proceed from
`main` while retaining the broader owner-assisted Strategy Lab scenario matrix as
risk-selected regression backlog rather than an all-or-nothing release blocker.
