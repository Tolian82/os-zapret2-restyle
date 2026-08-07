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

Strategy Lab shell-era live debugging is paused at owner-tested `v0.3.3_17`.

Current objective:
**migrate appropriate Strategy Lab orchestration to Python incrementally, preserve the existing product/lifecycle contract, then resume the owner-assisted live matrix.**

Primary plan:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

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
- [ ] Patch 1 — verify OPNsense Python interpreter/dependency model; add minimal packaged Python foundation and compatibility launcher without product-behavior change.
- [ ] Patch 2 — move job state, progress, events, and structured persistence to Python with exact JSON compatibility.
- [ ] Patch 3 — move stage machine, budgets, cancellation, and terminal finalization to Python while retaining audited lifecycle adapters.
- [ ] Patch 4 — move finite request/probe execution and DNS/TLS/HTTP parsing to Python; preserve return code/stdout/stderr/timeout separately and close the target-type/DNS diagnostic defect class by tests.
- [ ] Patch 5 — move candidate runtime and Stage-50 family screening orchestration to Python; preserve explicit readiness, PID/divert, privilege, log, probe, and cleanup evidence.
- [ ] Patch 6 — move expansion, stability, and extended-protocol orchestration to Python.
- [ ] Patch 7 — complete Python result/shortlist ownership and remove obsolete shell orchestration/load-order surfaces.
- [ ] Patch 8 — reconcile remaining GUI status/polling/progress/reload defects against the stable Python backend contract and prepare the designated live candidate.

If a listed patch exceeds one logical change, split it. Do not compress the migration into a monolithic rewrite.

Every packaged migration patch must pass applicable focused tests, normal CI, and the FreeBSD 15 package build. Testing-prerelease publication follows the owner's standing installable-patch authority without another routine confirmation.

==================================================
CONFIRMED DEFECTS CARRIED INTO MIGRATION
==================================================

These remain open until replacement evidence closes them:

- [ ] Stage 50 still returns `Temporary candidate runtime failed internally.` on `_17`; exact `_17` runtime root cause not yet established.
- [ ] Fresh job can immediately display visible `ERROR` before terminal evidence.
- [ ] `Strategy Lab returned no output.` can appear during active work.
- [ ] Visible GUI progress can remain at 0% while backend stages advance, then jump to 100%.
- [ ] Shell-global target type can be corrupted from `domain` to `A`.
- [ ] DNS parser can match question-section text rather than a proved answer record.
- [ ] DNS failure diagnostics flatten timeout, command failure, and parser rejection.
- [ ] Terminal reload/state presentation can resurrect retained terminal work incorrectly.
- [ ] Candidate readiness fatal-log classification can miss fatal runtime text.

Migration may remove the implementation mechanism behind an item, but the item is closed only by focused regression and required live/UI verification.

==================================================
POST-MIGRATION OWNER-ASSISTED VERIFICATION GATE
==================================================

Resume `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` only after the Python path reaches the designated functional parity gate.

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

Documentation/governance-only migration planning changes do not change `VERSION` or `PLUGIN_REVISION` and do not require a new package. The first source migration patch begins from `VERSION=0.3.3`, `PLUGIN_REVISION=17` and advances package revision only when packaged source changes are made.
