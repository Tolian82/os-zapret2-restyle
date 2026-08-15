# os-zapret2-restyle — Current state for `v0.4.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-08-15
State-line scope: **`v0.4.x`**

This file contains current facts only (`DOC-026`–`DOC-030`).

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md);
- project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md);
- chat rules: [`CHAT_RULES.md`](CHAT_RULES.md);
- GitHub rules: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology/proof: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

## Repository and package facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.4.1`;
- packaged source revision: `_13`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_13.pkg` / `v0.4.1_13`;
- testing-package SHA-256: `7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`;
- `_13` source merge and testing-tag target: `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
- latest full Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- internal service key: `zapret`.

The exact `main` SHA is resolved at execution time under `GH-004`. The `_13` testing prerelease is persistent GitHub delivery only and does not update the stable Pages/pkg repository (`GH-034`–`GH-038`).

## Current product facts

- DNS is fixed/currently working. Historical DNS failures are not a current blocker without fresh direct reproducible evidence.
- Model C is the selected and only normal production Stage-60 runtime. A/B/C model selection is closed.
- source `_13` removes automatic normal-production `Model C -> Model B -> Model A cold` replay;
- Model-C infrastructure/selector/rendering/readiness/attribution/cleanup failure is an explicit bounded structural Stage-60 failure, not candidate PASS/FAIL and not a fallback trigger;
- Model B remains explicit warm/reference/benchmark tooling; Model A remains explicit cold correctness/reference tooling;
- legacy B->A fallback semantics may remain inside explicit reference/measurement modules, but are not reachable from the normal packaged Stage-60 production entry point;
- Lua initialization, BLOB lazy-loading/common-set, bounded GET-4K discovery, and cross-batch keep-warm questions are closed for the current architecture by accepted measured evidence.

Detailed measurements and proof links remain in the current `v0.4.x` ledger.

## Current architecture and safety facts

Normal Stage 60 routes through `strategy_lab_py/stage60_model_c_production.py`, which reuses the proven Model-C bucket engine while preserving:

- adaptive-search planner semantics;
- immutable CandidateSpec and job-scoped ResourceInventory identity;
- exact source-port-qualified attribution/leasing;
- profile-compatible physical segmentation inside logical planner batches;
- bounded readiness;
- finite adaptive budgets;
- bounded GET-4K discovery;
- cleanup/cancellation containment;
- Stage-90 semantic restoration.

The production owner deliberately converts Model-C infrastructure failure into a structural `Stage60ParallelError` that is not `WarmInfrastructureError`; this prevents the legacy Model-B/cold-Model-A replay handler from consuming normal production failures.

Current architecture entry points:

- [`ARCHITECTURE.md`](ARCHITECTURE.md);
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md);
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md).

Historical A/B/C experiment material is history/proof and does not represent current production choice.

## Current verification boundary

`_13` automated source acceptance, persistent testing-package publication, and owner-live Model-C-only regression are complete:

- PR `#230` exact verified head: `8e1af17ce4ccfaad4851329167b386741d0c9ee8`;
- focused Model-C production regression proves injected infrastructure failure does not invoke B/A reference paths;
- full Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package build/inspection qualification: PASS;
- source CI run: `31819116248`;
- verified head squash-merged as `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
- testing publication workflow run: `31838633599`;
- prerelease `v0.4.1_13` and package asset published and verified;
- tag target matches the `_13` source merge exactly;
- temporary publication branch was removed after success;
- installed owner package confirmed as `os-zapret2-restyle-0.4.1_13` on `FreeBSD:15:amd64`;
- `telegram.org` `job.6RhNa1`: `NO_CANDIDATE`, Model C `16/16`, graph exhausted, no fallback, verified clean `RUNNING -> RUNNING` restoration;
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Model C `16/16`, three stable shortlist entries, no fallback, verified clean `RUNNING -> RUNNING` restoration;
- `www.youtube.com` `job.7Kz5ro`: `SUCCESS`, Model C early stop at `7/16` with `enough_candidates`, three stable shortlist entries, no fallback, verified clean `RUNNING -> RUNNING` restoration.

Durable owner-live evidence:
[`verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md).

The current selected live-regression boundary is now **Standard blocked domain with initial Zapret2 STOPPED**. Required proof is exact semantic restoration to STOPPED, unchanged production strategy/configuration, truthful terminal result, and absence of temporary Strategy Lab process/socket/firewall residue.

## Current documentation and governance facts

- exactly four canonical general rule books exist: `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`;
- `GITHUB_PUBLICATION.md` is the fourth book, **Правила работы с GitHub**, despite the retained historical filename;
- owner shorthand `сделай патч` / `сделай пакет` / `выложи пакет` is GitHub-native delivery, not a request for chat-generated files;
- project patch/package delivery never uses chat/sandbox `.pkg`, `.zip`, `.tar.*`, `.patch`, `.diff`, Actions artifacts, or equivalent transport files as the completion result;
- a patch that creates a new package candidate automatically continues after exact-head source merge to persistent GitHub testing-package publication without a second owner confirmation;
- testing publication is pinned to the candidate-defining merged source commit: the source must be an ancestor of `main` and its parent must have a different package identity, so a later same-identity docs/governance commit cannot be published accidentally;
- successful testing publication creates a machine-evidence Draft `publication-record/...` PR; that bounded docs-only tail must be reconciled, validated, exact-head squash-merged, verified on `main`, and cleaned before the package/patch command is complete;
- rule IDs are permanent identities and are not cascade-renumbered when rules are inserted or reorganized;
- cancelled/replaced rules remain physically at their permanent IDs with explicit lifecycle markers; those IDs are never recycled;
- creating, refining, cancelling, and replacing rules has an explicit semantic decision boundary in `DOC-054`;
- each canonical book contains explicit inbound/outbound cross-reference registries and CI validates them against active rule bodies and lifecycle state;
- local Markdown links and local Markdown heading fragments are validated by CI;
- `START_HERE.md` is the exact `_N` handoff;
- current work follows one state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`; ledgers/decisions/devlogs/evidence preserve chronology and proof but are not parallel owners of current state;
- zero-memory recovery is context-first: handoff/state, then all four rule books, plan/index, then selected specialists;
- Level-1 material already read for an unchanged exact repository state may be reused; advancing `main` requires affected current/mandatory material to be reread;
- the former mandatory broad GitHub reconciliation rule is cancelled; consistency work uses targeted rule dependencies, reference/link validation, and scope/risk expansion instead of a mandatory repository-wide audit for every canon change;
- pure documentation PRs use focused documentation/governance integrity validation rather than mechanically running the complete product matrix; product/package changes retain full validation as applicable;
- this file is current state for `v0.4.x`;
- `ROADMAP.md` is the complete concise master plan;
- `INDEX.md` is the global navigation/integrity map;
- [`history/current/v0.4.x.md`](history/current/v0.4.x.md) is the current Level-2 chronology;
- obsolete duplicate quick-reference files `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md` have been removed after reference migration;
- active/new documentation uses clean standard Markdown; old Level-3 historical formatting is preserved unless deliberately migrated separately.

The normative mechanics behind these facts live only in the corresponding rule books and are not duplicated here.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).