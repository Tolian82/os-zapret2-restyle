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

Milestone 7 — completion and live verification of approved functionality

Current work package:
Documentation recovery and reproducible live-verified package baseline

[x] Reconstruct current state from repository, Git history, chat decisions, and runtime audit snapshot
[x] Confirm package installation and runtime start on OPNsense
[x] Confirm dvtws2, supervisor, ipfw, HOSTLIST, IPSET, and blob-backed strategy operation
[x] Replace stale current-state and roadmap text with authoritative current information
[x] Reconcile package lifecycle documentation with DEC-2026-07-30
[x] Correct duplicate audit Finding identifiers
[x] Record live verification in audit, decisions, devlog, architecture, and changelog
[ ] Commit the verified source and documentation as one logical change
[ ] Rebuild from the clean commit and compare behavior with the tested package

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

- official v0.1.0, v0.2.0, and corrective v0.2.1 release work;
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

Status: IN PROGRESS

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

Remaining ordered work:

1. Commit and reproduce the verified baseline.
2. Live-test package upgrade from an earlier revision.
3. Live-test removal while running.
4. Verify runtime/dependency preservation after removal.
5. Live-test reinstall over preserved runtime.
6. Reboot OPNsense and verify automatic service startup behavior.
7. Complete the GUI/API live matrix:
   - Save/Apply;
   - Start;
   - Stop;
   - Restart;
   - Status;
   - Diagnostics;
   - blockcheck;
   - test domain;
   - reconfigure classification.
8. Resolve stale GUI help text and timeout-chain findings.
9. Verify supervisor response to controlled dvtws2 termination.
10. Review REQUIREMENTS.md line by line and implement only remaining approved scope.

Acceptance criteria for Milestone 7 completion:

- every approved requirement is implemented or explicitly deferred by decision;
- package install, setup, upgrade, remove, reinstall, and reboot paths are live verified;
- GUI/API actions have a complete traced chain or an explicit classification;
- no open broken Finding lacks a remediation plan;
- project state is reproducible from a clean Git commit;
- Engineering Memory and public release records agree with the code.

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

Do not declare another stable baseline until:

1. the verified tree is committed;
2. a package is rebuilt from the clean commit;
3. upgrade/remove/reinstall/reboot tests are recorded;
4. current AUDIT.md findings are reconciled;
5. CHANGELOG.md and PROJECT_STATE.md describe the same package state.
