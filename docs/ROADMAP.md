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
`v0.3.2_3`

Current work:
Complete the ordinary package patch that localizes the initial Diagnostics Blockcheck
guidance according to the OPNsense language. This patch is not a project release.

==================================================
PATCH v0.3.2_3 SCOPE
==================================================

- [x] Keep `VERSION=0.3.2`.
- [x] Advance `PLUGIN_REVISION` to `3`.
- [x] Preserve English as the default and no-JavaScript fallback.
- [x] Select the approved Russian text when the OPNsense document language is Russian.
- [x] Render both versions as two text-only paragraphs.
- [x] Remove the obsolete English-only guidance.
- [x] Add focused localization contract coverage to CI.
- [x] Synchronize current state, workflow, changelog, patch notes, and development log.

Normal PR CI, package build, squash merge, automatic branch deletion, and final `main`
verification are the delivery checks for this patch.

==================================================
COMPLETED BASELINE
==================================================

Task 1 — Zapret2 Service and upstream runtime releases
Status: COMPLETE AND LIVE VERIFIED

Diagnostics DIAG-002
Status: RESOLVED AND OWNER LIVE VERIFIED

Publication governance package patch:
`v0.3.2_2` merged to `main`

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
