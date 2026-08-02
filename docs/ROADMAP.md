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

Current work package:
GUI Zapret2 Service and selected-release management through the existing setup.sh

Ordered work:

1. [x] Publish prerelease v0.2.3 and package 0.2.3_1 containing the CFG-001 correction.
2. [x] Diagnose the 0.2.3_1 Apply timeout as inherited lifecycle-lock descriptor 9.
3. [x] Publish prerelease v0.2.4 and package 0.2.4_1 with the LIFE-009 correction.
4. [x] Verify descriptor 9 is released after startup with 0.2.4_1.
5. [x] Verify valid Apply reaches dvtws.args and active process arguments.
6. [x] Implement LIFE-014: fail-closed pre-upgrade stop, state-preserving post-upgrade
   start, and setup-driven runtime refresh.
7. [x] Publish prerelease v0.2.5 / package 0.2.5_1 through the automated release trigger.
8. [x] Live-test running/stopped pkg upgrade and running setup with package 0.2.5_1.
9. [x] Diagnose stopped setup as an unconditional-restart defect and implement the
   package-revision-2 state-preservation correction.
10. [x] Publish the later corrective package line through v0.2.8.
11. [x] Diagnose incomplete GUI rendering after local 0.2.8_3 replacement as stale
   lighttpd/php-cgi workers rather than an unstarted OPNsense service.
12. [x] Add a final canonical Web GUI refresh to +POST_INSTALL without removing plugin
   registration, template rendering, setup instructions, or zapret state restoration.
13. [ ] Live-verify automatic Web GUI PID replacement and complete rendering with
   package candidate 0.2.8_4.
14. [ ] Complete any remaining reboot and forced-stop evidence when required by a
   touched lifecycle path.
15. [ ] Reconcile CFG-001 and record the next verified stable baseline.
16. [x] Resume management of bol-van/zapret2 stable releases through setup.sh.
17. [x] Add installed runtime-version detection and reporting.
18. [x] Obtain and present the available stable-release list: `setup.sh show` prints
   up to the four latest published stable releases.
19. [ ] Notify when a newer stable release is available.
20. [x] Allow command-line selection, installation, update, downgrade, and repeat
   installation of a published stable release through `setup.sh install VERSION`;
   no-argument setup and `install` select the latest stable release.
21. [ ] Live-verify `show`, default latest installation, explicit reinstall, upgrade,
   downgrade, and running/stopped service-state preservation on OPNsense.
22. [x] Add GUI endpoints and controls that invoke this same backend without duplicating
   release-discovery or installation logic.
23. [x] Display the installed runtime tag separately from runtime/service health.
24. [ ] Live-verify the GUI service/release controls, asynchronous polling, and the
   running/stopped reinstall, upgrade, and downgrade matrix on OPNsense.
25. [ ] Add an explicit newer-stable-release notification as a separate logical change.
26. [ ] After the project owner supplies the repository, design and implement GUI
   management of the additional BLOB repository. Until then, its URL, manifest,
   layout, integrity model, and update contract remain unspecified.

==================================================
COMPLETED MILESTONES
==================================================

Milestone 1 — Independent project foundation
Status: COMPLETE

- independent repository;
- attribution, LICENSE, NOTICE, provenance;
- stable project, package, and service identities;
- VERSION as the single version source;
- build and release skeleton.

Milestone 2 — Backend v2 and transactional runtime
Status: COMPLETE

- modular parser, target registry, Target Mode, profile normalization, target resolver,
  blob resolver, validation, generation, activation, rollback, lifecycle, and diagnostics;
- transactional Apply and active-runtime preservation;
- field-level validation errors.

Milestone 3 — Service lifecycle hardening
Status: COMPLETE, with focused live regression tests still scheduled

- separate launcher and supervisor;
- supervisor-only runtime failure detection;
- process identity checks;
- serialized mutating lifecycle operations;
- firewall lifecycle consolidation;
- stale PID protection;
- conditional kill escalation;
- runtime cleanup on failure.

Milestone 4 — OPNsense integration
Status: COMPLETE for implemented scope

- MVC model/controllers/views/forms;
- configd actions;
- templates;
- syshooks;
- rc.d entry point;
- package hooks;
- status and diagnostics paths.

Milestone 5 — Profile pipeline normalization
Status: COMPLETE AND LIVE VERIFIED

- count-carrying profile pipeline;
- one selector per runtime profile;
- HOSTLIST and IPSET support;
- mixed selectors expanded automatically;
- explicit user --new boundaries preserved;
- focused static tests and live strategy evidence.

Milestone 6 — Project-owned release and pkg repository
Status: COMPLETE

- official v0.1.0, v0.2.0, corrective v0.2.1, and later 0.2.x release work;
- GitHub Release publication;
- GitHub Pages pkg repository;
- native FreeBSD:15:amd64 layout;
- separate flat release-assets staging;
- package archive metadata verification;
- ordinary https:// repository URL;
- signature_type: none accepted by decision.

==================================================
MILESTONE 7 — APPROVED FUNCTIONALITY COMPLETION
==================================================

Status: COMPLETE BY PROJECT-OWNER DECISION

Completed in this milestone:

[x] Move Engineering Memory into docs/
[x] Implement and test runtime profile normalization
[x] Implement the count-carrying profile pipeline
[x] Verify named HOSTLIST and IPSET target application on OPNsense
[x] Verify complete package install → manual runtime setup → service start chain
[x] Verify bol-van/zapret2 v1.0.3 builds dvtws2
[x] Verify launcher, supervisor, firewall, and runtime status
[x] Correct package lifecycle so pkg does not perform nested runtime package work
[x] Preserve runtime and dependencies on plugin removal by policy
[x] Record the tested package baseline as 0.2.1_8
[x] Rebuild and verify package os-zapret2-restyle-0.2.2_1 from clean commit fc6b208
[x] Publish main and annotated tag v0.2.2 at commit fc6b208
[x] Update the GitHub Pages pkg repository for 0.2.2_1
[x] Synchronize the release workflow and authoritative archive patch process

Closure decision:

Milestone 7 was closed by explicit project-owner decision on 2026-07-30. The following uncompleted checks were not marked as passed and remain a focused regression backlog:

- package upgrade from an earlier revision;
- removal while running and preserved-runtime verification;
- reinstall over preserved runtime;
- full reboot and automatic service-start behavior;
- complete GUI/API live matrix and reconfigure classification;
- browser/PHP/configd/script blockcheck timeout-chain behavior;
- controlled dvtws2 termination and supervisor cleanup/recovery;
- remaining approved-requirement review.

These tests are retained as evidence work and may be executed when required by a later logical change.

==================================================
DEFERRED WORK
==================================================

The following are not current objectives unless a demonstrated functional blocker requires them:

- general navigation redesign;
- broad UX research;
- first-run wizard redesign;
- visual redesign of Service, Strategy, Status, Maintenance, or Diagnostics pages;
- expansion beyond approved HOSTLIST and IPSET placeholders;
- GROUP, TARGETSET, or other placeholder families;
- repository signing, unless approved by a later architecture decision;
- automatic removal of runtime or shared dependencies with plugin deletion.

The public README strategy example remains intentionally unchanged until a later dedicated rewrite.

==================================================
NEXT RELEASE GATE
==================================================

Do not declare the next stable baseline until:

1. affected CFG-001 and lifecycle behavior passes focused verification;
2. the selected Milestone 8 work package is implemented and verified;
3. affected regression-backlog tests are executed where the change touches their chain;
4. current AUDIT.md findings affected by the change are reconciled;
5. CHANGELOG.md and PROJECT_STATE.md describe the same package state.
