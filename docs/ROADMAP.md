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
GUI management of bol-van/zapret2 stable releases through the existing setup.sh backend

Ordered work:

1. Add installed runtime-version detection and reporting.
2. Obtain and present the available stable-release list for bol-van/zapret2.
3. Notify when a newer stable release is available.
4. Allow selection and installation of a published stable release.
5. Support update to a newer release and repeat installation of the current release.
6. Display runtime presence separately from runtime/service health.
7. After the project owner supplies the repository, design and implement GUI management of the additional BLOB repository. Until then, its URL, manifest, layout, integrity model, and update contract remain unspecified.

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

- official v0.1.0, v0.2.0, corrective v0.2.1, and clean-baseline v0.2.2 release work;
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

1. the selected Milestone 8 work package is implemented and verified;
2. affected regression-backlog tests are executed where the change touches their chain;
3. current AUDIT.md findings affected by the change are reconciled;
4. CHANGELOG.md and PROJECT_STATE.md describe the same package state.
