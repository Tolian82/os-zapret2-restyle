# os-zapret2-restyle — Roadmap

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered future work and gates without duplicating current-state or implementation history.

Updated when:
Priority, sequencing, or acceptance gates change.

Read after:
`docs/DEVLOG.md`.

Do not store here:
Detailed rationale, current live logs, or completed implementation internals.

==================================================
CURRENT PRIORITY
==================================================

Strategy Lab migration is source-complete. Owner-assisted `_27` testing passes the
release-selected Standard Scenario 1, including Stages 40/50, continued search and exact
Stage-90 restoration.

Current objective:
**prepare and release `v0.4.0 / 0.4.0_1`; retain the remaining live scenarios as a
risk-selected regression inventory and then continue the separately approved adaptive-
search source series.**

Primary plan:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Approved post-migration search redesign:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` and
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`.

Runtime/search experiment plan:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

==================================================
COMPLETED STRATEGY LAB FOUNDATION
==================================================

- [x] Initial asynchronous Strategy Lab delivery: architecture, lifecycle, network precheck, candidate runtime, family search, expansion, stability, extended protocols, circular validation, and Diagnostics activation.
- [x] Corrective source/CI series: cancellation, stage machine, terminal truthfulness, budgets, semantic restoration, circular eligibility, target contract, integration harness, repository hygiene, third-audit corrective matrix, and subsequent FreeBSD live corrections through `_17`.
- [x] Live stage-40 FreeBSD DNS correction verified.
- [x] Live stage-90 restoration correction verified repeatedly.
- [x] Final shell-era handoff recorded from owner-tested `_17` job `job.w0nXxQ`.
- [x] Python/PHP/shell migration responsibility boundary approved and documented.

==================================================
PYTHON MIGRATION SERIES
==================================================

- [x] Patch 0 — documentation and handoff; freeze `_17` live boundary and confirmed defect backlog.
- [x] Patch 1 (`_18`) — Python 3.13 packaged foundation and compatibility launcher.
- [x] Patch 2 (`_19`) — Python job state, progress, events, and structured persistence.
- [x] Patch 3 (`_20`) — Python stage machine, budgets, cancellation, and finalization.
- [x] Patch 4 (`_21`) — Python finite request/probe execution and Stage-30/40 parsing.
- [x] Patch 5 (`_22`) — Python candidate runtime and Stage-50 family screening.
- [x] Patch 6 (`_23`) — Python expansion, stability, and extended protocols.
- [x] Patch 7 (`_24`) — Python final result/shortlist ownership and obsolete automated-shell retirement.
- [x] Patch 8 (`_25`) — GUI/status reconciliation and post-migration live-gate handoff.
- [x] Corrective `_26` — Stage-50 candidate-local failure isolation; source/CI/package
  qualified and published, live verification still pending because `_26` now stops at Stage 40.
- [x] Corrective `_27` — widen DNS deadline to 15 seconds and enclosing Stage-40 envelope
  to 20 seconds; source/CI merged and owner Scenario 1 live PASS.

If a listed patch exceeds one logical change, split it. Do not compress the migration into a monolithic rewrite.

Every packaged migration patch must pass applicable focused tests, normal CI, and the FreeBSD 15 package build. Testing-prerelease publication follows the owner's standing installable-patch authority without another routine confirmation.

==================================================
APPROVED ADAPTIVE-SEARCH SERIES
==================================================

The 2026-08-08 design review approved a second, post-migration search-quality series.
This does not erase the `_27` live boundary above: existing corrective findings remain
open until replacement OPNsense evidence closes them.

Target authority:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`.

Experimental authority:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Planned source cycles:

- [ ] `_28` — remove Stage-50 `accepted` as a hard gate for Stage-60 candidate reachability;
- [ ] `_29` — add Python `CandidateSpec` and job-scoped installed `ResourceInventory`;
  remove candidate resource/search policy from the shell adapter;
- [ ] `_30` — native-Zapret2 adaptive search graph, golden/reference corpus,
  BLOB-free/built-in/inline/external resource paths, and candidate-defined output range;
- [ ] `_31` — adaptive neighbor ordering, fixed search-epoch endpoint binding, two-to-three
  winner early stop, and per-phase timing telemetry;
- [ ] `_32` — review every operation/candidate/stage/job deadline from measured telemetry
  and enforce deadline containment;
- [ ] `_33` — lightweight discovery, fail-fast 3/3 stability, and finalist cold long-GET/
  16-KiB validation.

Warm runtime is deliberately not preselected as one of these implementation facts.
Before a warm design becomes production, compare:

- A — cold one-candidate/one-process reference;
- B — multiple isolated warm dvtws2 workers, initially with sequential probes;
- C — one compatible warm candidate bucket with deterministic dispatcher.

Required measurements include cold-result equivalence, candidate attribution,
false PASS/FAIL, startup/readiness/probe/cleanup time, total search wall time, RSS,
state leakage, cancellation, IPFW/divert isolation and exact restoration. Controlled
source-port dispatch, common Lua preload, lazy buckets and true simultaneous candidate
testing remain separate hypotheses until their individual evidence passes.

QUIC is not an adaptive-search work item: retain only the existing fixed IPv4 UDP/443
capability/precheck. The target search budget is concentrated on IPv4/TCP/TLS; IPv6
remains capability-gated and lower priority.

==================================================
CONFIRMED DEFECTS CARRIED INTO MIGRATION
==================================================

Closed corrective items and remaining regression/presentation backlog:

- [x] `_26` Stage-40 DNS deadline mismatch — closed by `_27` Scenario 1 live PASS.
- [x] `_25` Stage-50 aggregate abort — closed by `_27` Stage-50 PASS and continuation
  through Stages 60/70.
- [ ] Fresh-job immediate `ERROR` was not reproduced on `_26`; retain until a complete
  Scenario-1 run confirms behavior.
- [ ] `Strategy Lab returned no output.` can appear during active work.
- [ ] Visible GUI progress improved on `_25` but needs complete-run confirmation.
- [ ] Patch-4 target-type/parser/failure-class corrections pass source regressions but
  still require final live closure.
- [ ] Terminal reload/state presentation can resurrect retained terminal work incorrectly.
- [ ] Candidate readiness fatal-log classification can miss fatal runtime text.
- [ ] `_26` `PARTIAL` summary wording can imply usable saved strategies when Stage 40
  prevented the search from running; handle as a separate presentation patch.

Migration may remove the implementation mechanism behind an item, but the item is closed only by focused regression and required live/UI verification.

==================================================
POST-MIGRATION OWNER-ASSISTED VERIFICATION GATE
==================================================

The matrix remains the canonical live regression inventory. Scenario 1 is PASS on `_27`.
Rows below are selected for future live execution by release/change risk; they are not
all unconditional blockers for every stable release.

Then verify:

- [x] Standard blocked domain with initial Zapret2 RUNNING (`_27`, v0.4.0 mandatory row).
- [ ] Standard blocked domain with initial Zapret2 STOPPED.
- [ ] Extended TLS 1.2 and HTTP.
- [ ] Extended QUIC when capability exists.
- [ ] Generic UDP request-response path.
- [ ] Already-accessible target.
- [ ] No-candidate outcome.
- [ ] Cancellation during active stages.
- [ ] Whole-worker/stage timeout and retained partial evidence.
- [ ] Controlled internal failure with exact restoration.
- [ ] Circular start/stop/TTL and stale recovery.
- [ ] Settings Apply lifecycle guards.
- [ ] Active and terminal Diagnostics reload behavior.
- [ ] Russian/English progress and result presentation.
- [ ] Retention behavior.
- [ ] Reboot/residue checks.

==================================================
RELEASE BOUNDARY
==================================================

Stable release preparation requires all release-selected live rows to PASS and no known
critical lifecycle/restoration defect. It does not require every unrelated regression
row to be manually executed. `v0.4.0` has its selected Scenario-1 live gate PASS on `_27`.

The active release cycle sets `VERSION=0.4.0` and resets `PLUGIN_REVISION=1`. After its
PR/FreeBSD 15 checks pass, the exact verified merge must flow through the repository tag,
Release, checksum and Pages/pkg publication pipeline. Adaptive-search `_28` starts only
after that release cycle is complete.
