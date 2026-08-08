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

Strategy Lab migration is source-complete and owner-assisted post-migration testing is
active. Latest owner-tested candidate `v0.3.3_26` fails at Stage 40 on a DNS deadline
mismatch; corrective source candidate is `_27`.

Current objective:
**repeat Scenario 1 on the qualified `_27` source/package boundary through Stage 40/50,
then continue the owner-assisted live matrix; the separately approved adaptive-search
design remains the next Strategy Lab search-quality source series, not evidence that the
current live defects are closed.**

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
- [ ] Corrective `_27` — widen DNS deadline to 15 seconds and enclosing Stage-40 envelope
  to 20 seconds; source/CI merged, repeat Scenario 1 for owner live evidence.

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

These remain open until replacement evidence closes them:

- [ ] `_26` repeatedly fails Stage 40 because the 2-second DNS deadline is shorter than
  an observed valid 8–10-second local-Unbound response; `_27` correction pending live retest.
- [ ] `_25` Stage-50 aggregate abort is corrected in `_26` source but still needs live
  verification after `_27` allows Scenario 1 to reach Stage 50.
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

The matrix is resumed. Scenario 1 currently selects `_27`; dependent rows remain blocked
until Scenario 1 passes.

Then verify:

- [ ] Standard blocked domain with initial Zapret2 RUNNING.
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

Stable release preparation and pkg-repository promotion remain blocked until the post-migration live matrix passes.

Corrective `_27` remains `VERSION=0.3.3` and uses `PLUGIN_REVISION=27`. Testing-prerelease
publication remains separate from source/CI qualification and stable release promotion
remains blocked on the complete live matrix.
