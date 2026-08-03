# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered implementation and release stages.

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

Current delivery stage:
`RELEASE_AUTHORIZED`

Current release work:
Publish forward release `v0.3.2` / package `0.3.2_1` with the approved GitHub
publication-discipline improvements.

==================================================
COMPLETED BASELINE
==================================================

Task 1 — Zapret2 Service and upstream runtime releases
Status: COMPLETE AND LIVE VERIFIED

Completed capabilities:

- installed runtime and exact stable-tag reporting;
- complete Started/Stopped/Error state;
- Start/Stop control;
- latest stable-release discovery and caching;
- exact install/reinstall/upgrade/downgrade selection;
- asynchronous GUI setup state;
- cold-start firewall preparation;
- package and runtime service-state preservation;
- runtime permission normalization;
- transactional candidate activation and rollback;
- release-cache, reboot, package replacement, and GUI release-operation live tests.

Diagnostics DIAG-002
Status: RESOLVED AND LIVE VERIFIED

- v0.3.1 / package 0.3.1_1 published;
- project owner personally checked package 0.3.1_1;
- owner confirmed everything in the release works correctly;
- positive and negative domain-diagnostic output is accepted as correct.

==================================================
V0.3.2 RELEASE CHECKLIST
==================================================

1. [x] Explicit owner approval for version `v0.3.2`.
2. [x] Record v0.3.1 owner live verification.
3. [x] Record forward-only immutable version policy.
4. [x] Add GitHub publication specialist document to the mandatory reading order.
5. [x] Define one ready PR and one check set.
6. [x] Define exact PR-title preflight and separate release squash subject.
7. [x] Define one blobs/tree/commit multi-file API path.
8. [x] Define clean replacement of failed delivery cycles.
9. [x] Define complete public-distribution verification before installation commands.
10. [ ] Publish one atomic release-preparation commit and ready pull request.
11. [ ] Pass the PR-title workflow on the initial PR title.
12. [ ] Pass one complete CI and FreeBSD package-build set.
13. [ ] Squash merge with `release: prepare v0.3.2`.
14. [ ] Verify tag `v0.3.2` at the merge commit.
15. [ ] Verify GitHub Release, package `0.3.2_1`, `SHA256SUMS`, and Pages/pkg
    repository.
16. [ ] Record completed v0.3.2 publication evidence.

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

1. [ ] Obtain the approved repository URL.
2. [ ] Define manifest, version, integrity, compatibility, and rollback contracts.
3. [ ] Define interaction with built-in and user-provided BLOB files.
4. [ ] Implement backend state and operations.
5. [ ] Add GUI controls only after the backend contract is approved.

Do not invent repository, layout, manifest, integrity, or update semantics.

==================================================
REGRESSION BACKLOG
==================================================

Retained for separate focused work:

- controlled dvtws2 crash and supervisor recovery;
- blockcheck browser/PHP/configd/script timeout-chain behavior;
- duplicate diagnostics route reconciliation;
- unrelated open lifecycle and audit findings;
- removal/reinstall scenarios beyond the accepted preservation policy.

==================================================
DEFERRED WORK
==================================================

Not current objectives unless separately approved:

- broad navigation or visual redesign;
- placeholder families beyond HOSTLIST and IPSET;
- GROUP or TARGETSET selectors;
- repository signing;
- destructive removal of runtime, configuration, logs, or shared dependencies;
- unapproved BLOB repository assumptions.
