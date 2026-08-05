# Devlog — Strategy Lab circular eligibility

Date: 2026-08-05
Logical patch: Corrective Patch 8
Package candidate: `0.3.2_22`

## Work completed

- Added one persisted worker-owned circular eligibility decision.
- Required completed `SUCCESS`, domain target, stages 85/90 PASS, verified restoration, and a valid 3–5 candidate shortlist.
- Recomputed eligibility in the circular launcher before every start.
- Returned structured rejection reasons.
- Kept active automated jobs as an independent lifecycle blocker.
- Changed Diagnostics controls to use only `circular_eligible=true`.
- Replaced obsolete 1–3 minute guidance with enforced 150/270-second limits.
- Added a focused eligibility matrix and synchronized documentation.

## Next logical patch

Corrective Patch 9 will make the target contract explicit across API, shell validation, probe behavior, and GUI wording.
