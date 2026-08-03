# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered implementation stages and completion status.

Updated when:
A stage starts, completes, changes order, or gains approved work.

Read after:
DEVLOG.md

Do not store here:
Detailed history, architecture explanations, or decision rationale.

==================================================
CURRENT STAGE
==================================================

Milestone 8 — GUI maintenance and managed upstream components

Current status:
Task 1, Zapret2 Service and bol-van/zapret2 stable-release management, is COMPLETE and
live verified. Release v0.3.0 is the publication gate for this completed work package.

==================================================
MILESTONE 8 — ORDERED WORK
==================================================

Task 1 — Zapret2 Service and upstream runtime releases

1. [x] Detect installed runtime presence and exact stable tag.
2. [x] Expose complete Started/Stopped/Error state to the GUI.
3. [x] Add Start/Stop controls.
4. [x] Add `setup.sh show` for the latest stable releases.
5. [x] Add exact `setup.sh install VERSION` for install, reinstall, upgrade, and
   downgrade.
6. [x] Add latest-stable behavior for setup without an explicit version.
7. [x] Add stable-release caching, locked refresh, atomic replacement, and stale
   fallback.
8. [x] Add one-parameter configd selected-release launch.
9. [x] Add asynchronous GUI setup polling and operation-state controls.
10. [x] Prevent passive release-list failures from producing a global red modal.
11. [x] Prepare ipdivert/ipfw before dvtws2 cold-start launch.
12. [x] Preserve Started and Stopped states through ordinary and forced package
    replacement.
13. [x] Preserve the existing configd watcher while replacement actions are loaded.
14. [x] Normalize runtime Lua/blob permissions for dvtws2 privilege drop.
15. [x] Keep an atomic active-release marker independent of candidate Git HEAD.
16. [x] Add automatic rollback of upstream checkout, compiled binaries, active tag,
    and complete service state after failed candidate activation.
17. [x] Live-verify release cache reuse.
18. [x] Live-verify cold reboot without manual kernel-module loading.
19. [x] Live-verify forced package replacement while Started.
20. [x] Live-verify forced package replacement while Stopped.
21. [x] Live-verify Stopped selected-release installation.
22. [x] Live-verify running GUI downgrade v1.0.4 → v1.0.3.
23. [x] Accept the Zapret2 Service construction as working.
24. [ ] Publish immutable v0.3.0, package 0.3.0_1, release assets, and Pages/pkg
    repository.
25. [ ] Record completed publication evidence.

Task 2 — Newer stable-release notification

1. [ ] Define the notification state independently from release selection.
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

Do not invent the repository, layout, manifest, integrity model, or update semantics.

==================================================
COMPLETED MILESTONES
==================================================

Milestone 1 — Independent project foundation
Status: COMPLETE

- independent repository and identity;
- LICENSE, NOTICE, and attribution;
- VERSION as the single version source;
- build, CI, and release skeleton.

Milestone 2 — Backend v2 and transactional settings runtime
Status: COMPLETE

- parser, target registry, Target Mode, profile normalization, target and blob
  resolution, validation, generation, activation, rollback, and diagnostics;
- transactional Settings Apply;
- field-level validation errors.

Milestone 3 — Service lifecycle hardening
Status: COMPLETE FOR IMPLEMENTED SCOPE

- launcher and supervisor separation;
- process identity and stale-PID checks;
- serialized mutating operations;
- firewall lifecycle consolidation;
- controlled runtime-failure cleanup;
- cold-start firewall preparation.

Milestone 4 — OPNsense integration
Status: COMPLETE FOR IMPLEMENTED SCOPE

- MVC model, controllers, views, and forms;
- ACL and menu integration;
- configd actions;
- templates, syshooks, rc.d, and package hooks;
- status and diagnostics paths.

Milestone 5 — Profile pipeline normalization
Status: COMPLETE AND LIVE VERIFIED

- count-carrying profile pipeline;
- HOSTLIST and IPSET placeholders;
- mixed selector expansion;
- preserved user-authored `--new` boundaries;
- static and live strategy evidence.

Milestone 6 — Project-owned release and pkg repository
Status: COMPLETE

- GitHub Release publication;
- GitHub Pages FreeBSD:15:amd64 pkg repository;
- package archive verification;
- automated immutable release-tag handoff;
- approved unsigned repository configuration.

Milestone 7 — Approved functionality completion
Status: COMPLETE BY PROJECT-OWNER DECISION

The milestone closed the independent baseline and retained unperformed checks as a
focused regression backlog rather than falsely marking them as passed.

==================================================
POST-v0.3.0 REGRESSION BACKLOG
==================================================

These items are not blockers for the accepted Zapret2 Service release unless a later
change touches their chain:

- controlled dvtws2 crash and supervisor recovery;
- complete diagnostics/blockcheck timeout-chain behavior;
- duplicate diagnostics route reconciliation;
- remaining audit findings unrelated to release management;
- selected settings invalid/valid Apply evidence where later changes touch CFG-001;
- plugin removal/reinstall scenarios beyond the already tested preservation policy.

==================================================
DEFERRED WORK
==================================================

Not current objectives unless separately approved:

- general navigation or broad visual redesign;
- expansion beyond HOSTLIST and IPSET placeholder families;
- GROUP or TARGETSET placeholders;
- repository signing;
- automatic deletion of runtime, user configuration, logs, or shared dependencies on
  plugin removal;
- unapproved BLOB repository assumptions.

==================================================
NEXT RELEASE GATE
==================================================

v0.3.0 publication is complete only when:

1. the release-preparation PR is merged with exact subject
   `release: prepare v0.3.0`;
2. annotated tag v0.3.0 points to that merge;
3. Release validation and FreeBSD package build pass;
4. `os-zapret2-restyle-0.3.0_1.pkg` and SHA256SUMS are published;
5. the matching FreeBSD:15:amd64 Pages/pkg repository is deployed;
6. publication evidence is recorded without changing the immutable tag.
