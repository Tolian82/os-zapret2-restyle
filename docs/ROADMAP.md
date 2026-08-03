# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered implementation and delivery stages.

Updated when:
A stage starts, completes, changes order, or gains approved work.

Read after:
`DEVLOG.md`.

Do not store here:
Detailed history, architecture rationale, or complete procedures.

==================================================
CURRENT STAGE
==================================================

Milestone 8 — GUI maintenance and managed upstream components

Current source candidate:
`v0.3.2_2`

Current work:
Complete the ordinary package patch that enforces one remote task branch and automatic
post-merge cleanup. This patch is not a project release.

==================================================
PATCH v0.3.2_2 SCOPE
==================================================

- [x] Verify accidental v0.3.2 preparation branches are absent.
- [x] Verify there are no open pull requests.
- [x] Keep `VERSION=0.3.2`.
- [x] Advance `PLUGIN_REVISION` to `2`.
- [x] Define exactly one remote task branch per logical cycle.
- [x] Require blobs/tree/commit completion before branch creation.
- [x] Prohibit `-clean`, `-final`, `-atomic`, `-fixed`, `-retry`, and `-publish`
  sibling branches.
- [x] Distinguish package patch from project release.
- [x] Add automatic cleanup of the merged same-repository head branch.
- [x] Add focused CI contract coverage.
- [x] Synchronize current state, workflow, decision, patch notes, and development log.

Normal PR CI, package build, squash merge, automatic branch deletion, and final `main`
verification are the delivery checks for this patch.

==================================================
COMPLETED BASELINE
==================================================

Task 1 — Zapret2 Service and upstream runtime releases
Status: COMPLETE AND LIVE VERIFIED

Diagnostics DIAG-002
Status: RESOLVED AND OWNER LIVE VERIFIED

Published release:
`v0.3.2`

Published package:
`os-zapret2-restyle-0.3.2_1.pkg`

==================================================
NEXT PRODUCT TASKS
==================================================

Task 2 — Newer stable-release notification

1. [ ] Define notification state independently from release selection.
2. [ ] Compare the active stable tag with the validated cached release list.
3. [ ] Show a passive notification when a newer stable release exists.
4. [ ] Avoid repeated API calls and avoid converting discovery failure into service
   Error.
5. [ ] Add focused tests and live verification.

Task 3 — Additional BLOB repository management

Status: BLOCKED ON OWNER-SUPPLIED CONTRACT

Do not invent repository, layout, manifest, integrity, or update semantics.

==================================================
REGRESSION BACKLOG
==================================================

- controlled dvtws2 crash and supervisor recovery;
- blockcheck browser/PHP/configd/script timeout chain;
- duplicate diagnostics route reconciliation;
- unrelated lifecycle and audit findings;
- removal/reinstall scenarios beyond the accepted preservation policy.
