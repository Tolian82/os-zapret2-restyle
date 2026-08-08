# DEC-2026-08-09 — Risk-based live release gates

Status: Active
Date: 2026-08-09

## Context

The Strategy Lab hardening and Python-migration work accumulated an 18-row OPNsense
live matrix. That matrix is valuable as a regression inventory, but its release wording
incorrectly turned every row into an unconditional blocker for every stable release.

The distinction matters after corrective `_27`. The owner installed
`v0.3.3_27` on 2026-08-08 and repeated the live Standard `rutracker.org` path that had
exposed the `_25` Stage-50 and `_26` Stage-40 defects. The run passed stages 00, 10, 20,
30, 40, 50, 60, 70, 85 and 90; Stage 80 was intentionally skipped in Standard mode;
Stage 99 truthfully reported `NO_CANDIDATE`. Stage 90 explicitly reported that temporary
processes/rules were removed and the initially running Zapret2 service was restored
healthy.

That evidence closes the defects for which `_26` and `_27` were created. Requiring the
owner to execute unrelated cancellation, circular, retention, reload, localization,
reboot and synthetic-failure scenarios solely to permit a stable release would add a
blanket process gate without evidence that those surfaces are release blockers.

## Decision

The 18-row OPNsense matrix remains the canonical live regression inventory. It is not an
all-or-nothing release checklist.

For each stable release, select mandatory live rows from current risk and evidence:

- a live-only defect corrected by the candidate requires replacement appliance evidence;
- behavior materially changed where CI cannot establish the relevant OPNsense/runtime
  semantics requires an applicable live row;
- restoration/lifecycle safety affected by the candidate requires live restoration
  evidence;
- any known critical defect, `RESTORE_FAILED`, unverified restoration, or unexplained
  temporary-runtime/firewall residue blocks release;
- an explicitly selected mandatory row must PASS before release;
- rows unrelated to the candidate remain recommended regression coverage and may be run
  independently without blocking release merely because they are still pending.

A mandatory live PASS needs enough owner evidence to bind the exact candidate, terminal
behavior and applicable lifecycle-restoration outcome. A fixed exhaustive forensic bundle
is not required for every successful smoke row; deeper logs/state/firewall/process
artifacts become mandatory when the claimed behavior cannot otherwise be established or
when a failure must be diagnosed.

CI, FreeBSD package verification and live evidence remain complementary. This decision
does not permit CI to manufacture a live PASS or permit a live smoke test to replace
required automated coverage.

## v0.4.0 release application

For the `v0.4.0 / 0.4.0_1` release boundary, Scenario 1 is the mandatory owner-assisted
post-migration live row because it directly exercises the corrected Python DNS baseline,
Stage-50 candidate-local isolation, continued Stage-60/70 execution, truthful terminal
`NO_CANDIDATE`, cleanup and restoration of an initially running service.

Owner evidence from `v0.3.3_27` on 2026-08-08 marks Scenario 1 PASS. Rows 2–18 remain in
the regression inventory but are not blockers for `v0.4.0` in the absence of a new known
critical defect on those surfaces. Their pending state must not be rewritten as PASS.

The separate adaptive-search A/B/C experiment gates are unaffected. No warm-runtime or
adaptive-search mechanism becomes production-approved through this release decision.

## Supersession

This decision supersedes active wording that requires every row of
`STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` to PASS before any stable release, including the
blanket interpretation in the 2026-08-07 Python-migration decision. It does not rewrite
historical devlogs that accurately describe the gate in force when they were written.

## Affected documents

- `docs/INDEX.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/REQUIREMENTS.md`
- `docs/DEVELOPMENT_GUIDE.md`
- `docs/DECISIONS.md`
- `docs/DEVLOG.md`
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`
- `docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md`
