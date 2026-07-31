# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What was done?

Purpose:
Record completed work, confirmed tests, failed attempts, and chronological
development progress.

Updated when:
A meaningful work unit is completed or tested.

Read after:
ARCHITECTURE.md

Do not store here:
Permanent rules, decision rationale, or future product requirements.

==================================================
2026-07-28 — INDEPENDENT PROJECT FOUNDATION
==================================================

Completed:

- Established os-zapret2-restyle as an independent project.
- Preserved attribution to bol-van and Umur Gorur in LICENSE and NOTICE.
- Approved independent package identity.
- Approved VERSION as the version source.
- Established independent build, CI, and release infrastructure.
- Removed inherited repository assumptions from build-package identity.
- Excluded attribution files from legacy-reference checks.

Goal:

Build and install the plugin on a clean supported OPNsense system without
runtime, build, or installation dependencies on another OPNsense zapret plugin
repository.

==================================================
2026-07-28 — BACKEND V2
==================================================

Completed:

- Backend v2 modular architecture.
- Unified Traffic Strategy.
- Generic <TYPE:name> placeholders.
- HOSTLIST/IPSET target registry.
- Target Mode.
- Domain and IPv4/CIDR normalization.
- Strict target validation.
- Wildcard domain canonicalization.
- Exclude Domains.
- Blob resolution.
- Port extraction.
- Generated dvtws2 arguments.
- Candidate validation.
- Atomic activation and restoration.
- Launcher and supervisor separation.
- ipfw lifecycle.
- Execution stages.
- Safe reconfigure.
- Transactional Apply.
- Field-level GUI errors.
- Normalized GUI reload.
- Explicit visible Apply button.

==================================================
2026-07-28 — CONFIRMED LIVE TESTS
==================================================

- Target placeholders resolve to separate managed files.
- *.googlevideo.com becomes googlevideo.com.
- Invalid 999.999.999.999 reports targets|failed.
- Invalid candidate leaves PID unchanged.
- Invalid candidate leaves active runtime unchanged.
- Invalid candidate leaves ipfw unchanged.
- Normal runtime reaches 13|13|ready|ok.

==================================================
2026-07-28 — ENGINEERING MEMORY SYSTEM
==================================================

Completed:

- Added INDEX.md.
- Added PROJECT_STATE.md.
- Added DECISIONS.md.
- Added WORKING_CONVENTIONS.md.
- Added DEVELOPMENT_GUIDE.md.
- Defined mandatory reading order.
- Defined one-document-one-question responsibility.
- Defined DOCUMENT ROLE blocks.
- Defined documentation synchronization with code.
- Defined that approved concepts must be recorded in DECISIONS.md.
- Restyled README.md, ARCHITECTURE.md, DEVLOG.md, and ROADMAP.md without losing
  their previous useful content.


==================================================
2026-07-28 — API AUDIT PLAN RECORDED
==================================================

Planned:

- Audit GUI JavaScript API calls.
- Audit MVC endpoints, controllers, models, and configuration paths.
- Audit configd actions and shell command targets.
- Audit backend functions, rc scripts, syshooks, and plugin hooks.
- Audit package lifecycle, setup, build, CI, release, and external URLs.
- Classify every interface and inherited reference.
- Run focused live tests.
- Record discoveries during the audit.
- Record completed work and the next stage when the audit finishes.

Working rule confirmed:

Every stage begins by recording the plan and ends by recording results,
discoveries, remaining work, and the next stage.

==================================================
CURRENT WORK
==================================================

Current priority:

Complete the API and inherited-reference audit.

Audit scope:

- GUI JavaScript API calls.
- MVC API URLs.
- Controller actions.
- Model operations.
- Configd actions.
- Shell entry points.
- Backend functions.
- rc scripts.
- syshooks.
- Plugin hooks.
- Filesystem paths.
- Package lifecycle scripts.
- Setup logic.
- Build and release logic.
- External URLs.
- Diagnostic commands.

==================================================
KNOWN CAUTIONS
==================================================

- Do not commit /usr/local/etc/zapret2.
- Do not commit runtime, binaries, logs, PID files, backups, or secrets.
- Use FreeBSD-compatible commands.
- Give commands strictly in execution order.
- Do not guess OPNsense HTML or CSS structure.
- The field-width experiment was reverted and remains out of scope.


==================================================
2026-07-28 — AUDIT SYSTEM AND MVC/API AUDIT BLOCK
==================================================

Completed:

- Added AUDIT.md as the authoritative technical audit register.
- Made documentation-system changes explicit architectural changes.
- Required every approved rule to be recorded in project documentation.
- Required broken chains to be documented before remediation.
- Required each completed audit step to be documented before continuing.
- Mapped the settings and diagnostics GUI-to-configd chains.
- Verified Menu and ACL namespace alignment.
- Verified that GUI-referenced configd actions exist.

Findings recorded in AUDIT.md:

- Duplicate diagnostics page controller route.
- Obsolete HTTP/HTTPS Strategy field references in settings help text.
- Obsolete HTTPS Strategy references in diagnostics output and guidance.
- Inconsistent blockcheck timeout chain.
- Service reconfigure API endpoint not called by the current GUI and requiring
  further interface testing.

Next:

- Audit service lifecycle, rc.d, syshooks, plugin hooks, supervisor, watchdog,
  and possible lifecycle overlap.


==================================================
2026-07-28 — ACTIONABLE AUDIT FINDINGS AND INITIAL LIFECYCLE TRACE
==================================================

Completed:

- Required every audit block to end with updated, reviewed, and committed
  Engineering Memory before the next block or code remediation starts.
- Introduced stable finding IDs and a mandatory actionable finding structure.
- Expanded MVC-001, GUI-001, GUI-002, DIAG-001, and API-001 with exact affected
  files and symbols, affected chains, evidence, risks, verification plans,
  remediation plans, acceptance criteria, documentation impact, and status.
- Recorded the confirmed boot and shutdown syshook chains.
- Recorded LIFE-001 for possible overlap between automatic syshook lifecycle and
  the rc.d service entry point.
- Recorded LIFE-002 and LIFE-003 for focused boot, shutdown, and reboot tests.

Current result:

The MVC/GUI/API/configd block remains completed and now has actionable repair
plans. The lifecycle block is in progress; no lifecycle code remediation is
approved until its remaining static trace and required live tests are complete.

Next:

Continue lifecycle tracing through rc.d registration, plugin hooks, supervisor,
watchdog, launcher, firewall, failure paths, and cleanup, then synchronize and
commit the completed lifecycle block before moving on.

==================================================
2026-07-28 — LIFECYCLE AUDIT EVIDENCE AND ARCHITECTURE-DEBT MODEL
==================================================

Completed:

- Separated confirmed Findings from unresolved Architecture Debt.
- Defined the Architecture Debt lifecycle and prohibition on direct closure.
- Required a DECISIONS.md entry before dependent implementation.
- Required blocked Findings to remain unmodified until controlling architecture is
  decided.
- Recorded verified boot, shutdown, runtime start, runtime stop, and failure-cleanup
  chains.
- Recorded LIFE-004 through LIFE-008 with exact evidence, plans, and acceptance
  criteria.
- Opened ARCH-001 watchdog architecture, ARCH-002 package lifecycle policy, and
  ARCH-003 launcher/supervisor/watchdog responsibility boundaries.

No lifecycle code was changed.

Next:

- Complete reconfigure, rollback, firewall snapshot, atomic backup, package lifecycle,
  and concurrency audit.
- Perform required live tests.
- Commit the completed lifecycle audit documentation before remediation.


==================================================
2026-07-28 — LIFECYCLE MUTEX IMPLEMENTED (LIFE-009)
==================================================

Completed:

- Confirmed that MVC Config::lock() does not cover template reload or backend
  lifecycle execution.
- Confirmed that start, stop, restart, reconfigure, and runtime-failure previously
  had no common shell-level serialization boundary.
- Added one /usr/bin/lockf-backed mutex in zapret_service.sh.
- Serialized interactive mutating lifecycle commands with a bounded wait.
- Kept status read-only and non-blocking.
- Made runtime-failure use an immediate try-lock so an old supervisor callback
  cannot queue behind reconfigure and tear down the replacement runtime.
- Added a clear temporary-failure error for lock contention.
- Updated architecture, audit, decision, state, and changelog records.

Validation completed:

- POSIX shell syntax check for zapret_service.sh.
- Static verification that every public mutating service action passes through
  the common lock boundary.

Still required:

- Focused live concurrency and forced-termination tests on OPNsense.
- Normal start, stop, restart, reconfigure, Apply, status, and runtime-failure
  regression tests.

Next:

Live-verify LIFE-009, then continue the remaining lifecycle and package-lifecycle
analysis.

==================================================
2026-07-28 — FIREWALL STATE CHECK CONSOLIDATED (LIFE-004)
==================================================

Completed:

- Removed the duplicate firewall_rules_present() declaration from backend/firewall.sh.
- Preserved the existing firewall-presence behavior and retained one canonical implementation.
- Verified that all callers continue to resolve to the remaining function.
- Completed POSIX shell syntax validation for the project shell scripts.
- Updated the audit and changelog records.

Still required:

- Focused live verification of status, repeated start, incomplete-runtime detection,
  and firewall-presence detection before LIFE-004 is marked Resolved.

Next:

Continue the remaining Lifecycle/Runtime audit and live verification queue.
==================================================
2026-07-28 — PROCESS IDENTITY HARDENING (LIFE-007 / LIFE-008)
==================================================

Completed:

- Added one shared process-command identity check based on FreeBSD /bin/ps.
- Required launcher PID files to identify the configured absolute dvtws2 binary.
- Required supervisor PID files to identify the configured supervisor loop.
- Prevented stale or reused PIDs from receiving TERM or KILL.
- Made supervisor KILL escalation conditional after the grace period.
- Kept existing launcher, supervisor, and responsibility boundaries unchanged.
- Completed POSIX shell syntax and whitespace validation.

Still required:

- Live verification of /bin/ps command output on OPNsense.
- Normal lifecycle regression tests.
- Stale, malformed, dead, and unrelated live PID-file tests.

Next:

Run the focused live tests, then continue the remaining lifecycle and package-lifecycle audit.

==================================================
2026-07-29 — DISCONNECTED WATCHDOG REMOVED (LIFE-005 / ARCH-001)
==================================================

Decision implemented:

- Selected supervisor_loop.sh as the only runtime failure detector.
- Rejected a separate cron or daemon watchdog model.
- Required future supervisor health checks to be added separately and remain
  detection-only.

Code changes:

- Removed watchdog.sh.
- Removed watchdog_loop.sh.
- Removed the obsolete HTTP_ARGS / HTTPS_ARGS watchdog behavior with those files.
- Left existing supervisor behavior unchanged.

Validation completed:

- Repository search confirmed no active lifecycle, configd, syshook, package-hook,
  GUI, or cron integration depended on the removed files.
- POSIX shell syntax validation passed for all remaining shell scripts.

Still required:

- Install the updated files on OPNsense.
- Run normal lifecycle, Apply, PID, supervisor, and firewall regression tests.
- Confirm no watchdog files or active references remain on the installed system.

Next:

After successful regression verification, add only proven supervisor health checks
in separate focused commits.


==================================================
2026-07-29 — SUPERVISOR CHILD IDENTITY CHECK (LIFE-010)
==================================================

Implemented the first focused supervisor hardening commit after watchdog removal.

Code changes:

- Passed the configured absolute DVTWS_BIN path from orchestrator through
  supervisor_start to supervisor_loop.sh.
- Replaced kill -0-only monitoring with liveness plus FreeBSD ps command identity
  verification on every interval.
- Kept the existing single runtime-failure callback and detection-only boundary.
- Added no runtime-directory, firewall, restart, reconfigure, generation, or repair
  behavior.

Validation completed:

- POSIX shell syntax validation passed.
- Diff whitespace validation passed.
- All supervisor_start call sites were updated consistently.

Still required:

- Deploy through the package or copy the updated scripts.
- Run the minimal live check: status plus one process listing.

Next:

After live verification, evaluate the next supervisor health check independently.


==================================================
2026-07-29 — GUI-FIRST RUNTIME BOOTSTRAP AND RELEASE MODEL
==================================================

Approved:

- Own pkg repository through GitHub Pages.
- GitHub Release assets and checksums.
- First repository target FreeBSD:15:amd64 / OPNsense 26.7.
- Complete normal installation and updates through the OPNsense GUI.
- Separate command blocks for checks and installation.

Implemented:

- Added automatic setup.sh execution when a lifecycle start finds no dvtws2 binary.
- Kept bootstrap under the existing lifecycle lock.
- Added explicit post-setup binary verification.
- Added 600-second configd timeouts for start, restart, and reconfigure.
- Removed the manual setup command from the package post-install instructions.
- Bumped package revision to 0.1.0_2.

Verification required:

- Build and reinstall package.
- Remove or temporarily move dvtws2.
- Use GUI Apply or configctl start without running setup.sh manually.
- Confirm one-time bootstrap, service start, and no repeated bootstrap on restart.

Next:
Implement pkg repository and release publication in a separate focused commit.

==================================================
2026-07-29 — RELEASE PACKAGE ARCHIVE PREFLIGHT
==================================================

Finding PKG-003 was remediated before creating the first public tag.

Implemented:

- Added a reusable release-package verifier.
- Read +MANIFEST directly from the generated .pkg archive.
- Compared embedded package name, version, and project URL with repository sources.
- Inserted verification before pkg repo generation and publication.

Validation still required:

- Push the focused commit.
- Run the v0.1.0 tag workflow.
- Confirm the FreeBSD build log reports verified package metadata.
- Confirm publication jobs run only after that check succeeds.


==================================================
2026-07-29 — FINAL RELEASE WORKFLOW PREFLIGHT
==================================================

Audited the complete tag-to-release pipeline before creating v0.1.0. Found that the
workflow checked for `meta.pkg`, which is not part of the current pkg repository
format. Corrected validation to require `meta.conf`, `data.pkg`, and
`packagesite.pkg`; updated the Pages artifact action; made the unsigned prerelease
configuration explicit; and added the one-time repository registration procedure to
README. No tag was created during this audit.

## 2026-07-29 — First release-run audit: artifact path portability

The v0.1.0 workflow completed validation and the FreeBSD build, then stopped because
the generic artifact uploader rejected the colon in `FreeBSD:15:amd64`. Reviewed
established OPNsense repository layouts and the official Pages artifact action.
Preserved native `${ABI}` paths and added a flat release-assets staging boundary.

==================================================
2026-07-29 — MILESTONE 6 CLOSED AND MILESTONE 7 PRIORITIES APPROVED
==================================================

Completed:

- The first official v0.1.0 release was published successfully.
- The first release run exposed the generic artifact restriction on colon-containing
  native ABI paths.
- The release architecture now permanently separates the native Pages repository tree
  from flat GitHub Release asset staging.
- GitHub Pages environment protection was corrected to permit `v*` tags through a tag
  rule rather than an ineffective branch rule.
- Backend, lifecycle, supervisor, packaging, and release infrastructure work required
  for Milestone 6 was closed.

Approved next direction:

1. Move internal documentation into `docs/`.
2. Verify real strategy application for named HOSTLIST and IPSET targets.
3. Finish all functionality already approved in REQUIREMENTS.md before design work or
   scope expansion.

The previously discussed UX audit was rejected as unnecessary for the current small,
focused plugin. Navigation and the existing first-run, Service, Diagnostics,
Maintenance, Status, and Strategy interfaces remain unchanged for now. UX work may be
introduced later when expanded functionality needs it or when an existing interface
actually blocks use.

Working emphasis was clarified as an approximate planning guide rather than a quota:
about 60% coding, 15% documentation, 15% discussion of current work, 8% discussion of
future work, and 2% broader process or philosophical discussion.

==================================================
2026-07-29 — ENGINEERING DOCUMENTATION MOVED TO DOCS/
==================================================

Completed the first priority of Milestone 7.

Implemented:

- Created the repository `docs/` directory.
- Moved the complete engineering documentation system with `git mv`.
- Preserved README.md, LICENSE, NOTICE, VERSION, Makefile, and pkg-descr in the
  repository root.
- Updated the root README engineering-memory entry point and reading order.
- Updated GitHub Actions required-file checks for the new paths.
- Added documentation-location guidance to docs/INDEX.md.
- Recorded the layout decision in docs/DECISIONS.md.
- Updated current project state and roadmap.

No plugin runtime behavior, package content, service lifecycle, or GUI behavior was
changed.

Next:

Audit and verify real strategy application for named HOSTLIST and IPSET targets.

==================================================
2026-07-29 — RUNTIME PROFILE NORMALIZER IMPLEMENTED
==================================================

Implemented the approved automatic target-profile expansion.

Code changes:

- Added backend module `profile_normalizer.sh`.
- Loaded the module from `zapret_service.sh`.
- Inserted normalization after Target Mode and before placeholder indexing in
  `orchestrator_build_release()`.
- Made the orchestrator consume the normalized runtime profile count.
- Preserved user-authored profile ordering and generated downstream `--new`
  boundaries through the existing Target Resolver.
- Added staged replacement with restoration on replacement failure.
- Added focused shell tests and a CI execution step.

Verified test scenarios:

- no selector;
- one HOSTLIST selector;
- one IPSET selector;
- mixed HOSTLIST and IPSET selectors;
- two HOSTLIST selectors plus one IPSET selector;
- user-authored `--new` boundaries;
- repeated selector deduplication;
- second-pass idempotence.

Local verification completed:

- shell syntax validation passed;
- focused profile normalizer tests passed;
- repository diff whitespace validation passed.

Live OPNsense verification remains required before the runtime behavior is
classified as fully verified.

==================================================
2026-07-29 — PROFILE PIPELINE API IMPLEMENTED
==================================================

Implemented a count-carrying adapter layer for parsed-profile preparation.

Code changes:

- Added `backend/profile_pipeline.sh`.
- Standardized parse, registry, Target Mode, normalization, and placeholder-index
  steps on `WORKDIR + PROFILE_COUNT -> PROFILE_COUNT`.
- Made every pipeline transition validate its resulting positive count.
- Replaced direct profile-stage calls in `orchestrator_build_release()` with the
  ordered pipeline adapters.
- Kept specialist module APIs unchanged and avoided forcing non-profile stages into
  an unsuitable count contract.
- Added focused pipeline tests and CI execution.

Runtime target resolution, generated arguments, activation, and lifecycle behavior
remain unchanged.


==================================================
2026-07-29 — RELEASE 0.2.0 PREPARATION
==================================================

Approved the next project release as version 0.2.0.

Implemented release metadata changes:
- VERSION changed from 0.1.0 to 0.2.0.
- PLUGIN_REVISION reset from 2 to 1.
- Expected package version is 0.2.0_1.
- Expected release tag is v0.2.0.

Synchronized the current release documentation without rewriting the historical
v0.1.0 records.

Confirmed that the project repository remains explicitly unsigned using
`signature_type: "none"`. This decision supersedes the earlier requirement to
make repository signing mandatory before stable-release promotion.

Next:
Review the release diff, run validation, commit the release preparation, push
main, verify CI, and create the immutable v0.2.0 tag.

==================================================
2026-07-29 — PKG REPOSITORY URL CORRECTION
==================================================

Live verification of v0.2.0 found that `pkg+https://` caused pkg
to interpret the GitHub Pages repository as an SRV mirror.

Changing the URL to ordinary `https://` allowed OPNsense to update the
Zapret2Restyle catalogue successfully and expose
`os-zapret2-restyle 0.2.0_1`.

The source configuration was corrected and VERSION advanced to 0.2.1.
The immutable v0.2.0 tag remains unchanged.


2026-07-30 — PACKAGE-MANAGED INSTALL/REMOVE LIFECYCLE IMPLEMENTED

Scope:

- Replaced first-Start runtime bootstrap with automatic package post-install bootstrap.
- Added `setup_launcher.sh` and a configd setup action so setup work is detached from
  pkg's package-script process and can wait for the outer package transaction.
- Reworked `setup.sh` into internal `install` and `uninstall` lifecycle modes.
- Corrected the upstream repository to `https://github.com/bol-van/zapret.git`.
- Added managed-dependency ownership tracking under `/var/db/zapret2-restyle`.
- Reworked all three package hooks as one lifecycle: install registration/bootstrap,
  pre-remove stop/cleanup handoff, and post-remove registration refresh.
- Protected upgrade/reinstall from destructive uninstall cleanup with `PKG_UPGRADE` and
  a second installed-package check in the cleanup worker.
- Updated all affected engineering and user documentation in the same logical change.

Static verification completed:

- Shell files were made executable.
- Shell syntax and package construction still require local validation after this edit.

Live verification still required:

- clean GUI/pkg installation;
- automatic dependency installation and dvtws2 build;
- setup log and state behavior;
- service Start/Apply behavior after successful and failed bootstrap;
- upgrade/reinstall preservation;
- full package deletion and residual-file/process/rule/menu checks.


==================================================
2026-07-30 — Repository consistency before lifecycle live test
==================================================

- Reconciled current architecture and project-state text with DEC-2026-07-30.
- Marked the earlier first-Start/Apply bootstrap design as superseded rather than
  rewriting its historical decision record.
- Updated current package-version references to 0.2.1_2.
- Confirmed the intended package identity is `os-zapret2-restyle`; local framework
  development builds using `-devel` are not part of the release identity.

==================================================
2026-07-30 — SETUP LAUNCHER EXECUTABLE BIT CORRECTION
==================================================

Live evidence:

- plugin installation completed without starting runtime bootstrap;
- `configctl zapret setup install` returned exit 127;
- `actions_zapret.conf` invokes `setup_launcher.sh` directly;
- the repository launcher mode was `0644`, so it could not be executed directly.

Implemented as one logical change:

- changed `setup_launcher.sh` mode from `0644` to `0755`;
- increased `PLUGIN_REVISION` from `2` to `3`;
- synchronized current state, audit record, and changelog.

Pending live verification:

- package archive preserves mode `0755`;
- configd setup action starts the launcher;
- bootstrap state/log paths appear;
- configd and Web GUI remain healthy through install and uninstall.

==================================================
2026-07-30 — ZAPRET2 UPSTREAM REPOSITORY CORRECTION
==================================================

Live bootstrap of `0.2.1_3` successfully launched and compiled the downloaded tree,
but the configured bol-van/zapret repository produced `dvtws`, not the required
`dvtws2`. The setup backend then failed its runtime verification.

Implemented as one logical change:

- changed the runtime source to `https://github.com/bol-van/zapret2.git`;
- increased `PLUGIN_REVISION` from `3` to `4`;
- recorded the live failure and acceptance criteria.


==================================================
2026-07-30 — LIFECYCLE REFERENCE REVIEW AND APPROVED CORRECTION
==================================================

Re-read the Engineering Memory in its mandatory order and reviewed the current
`ugorur/os-zapret2` installation/removal implementation.

Useful reference patterns selected:

- quick package installation followed by a separate setup command;
- synchronous service stop in `+PRE_DEINSTALL` before service scripts disappear;
- preserving saved OPNsense configuration across package removal.

Patterns rejected:

- restarting configd from `+POST_DEINSTALL`;
- tracking the moving upstream default branch as the installed runtime version.

Recorded the approved correction in AUDIT.md and DECISIONS.md before changing code.
The implementation separates pkg lifecycle from runtime setup, prints the exact manual
setup command, preserves runtime/dependencies on package removal, and pins zapret2 v1.0.3.


Static implementation verification:

- all package hooks and shell scripts pass `sh -n`;
- `+POST_INSTALL` contains the exact approved setup command;
- package hooks no longer call `setup_launcher.sh install`, setup uninstall, or configd restart;
- setup no longer contains managed dependency deletion or moving-branch `git pull`;
- setup pins `ZAPRET_REF=v1.0.3`;
- package revision increased from 7 to 8.

Package build and live OPNsense verification remain pending.

==================================================
2026-07-30 — PACKAGE 0.2.1_8 LIVE INSTALLATION AND RUNTIME VERIFIED
==================================================

Prepared a complete repository archive and an installed-runtime audit snapshot, then
compared source, package metadata, installed files, configd actions, templates,
processes, PID files, kernel modules, ipfw state, and logs.

Live result:

- installed package: os-zapret2-restyle-0.2.1_8;
- pkg installation completed without nested runtime package work;
- explicit setup.sh install completed;
- setup used bol-van/zapret2 pinned to v1.0.3;
- executable binaries/my/dvtws2 was produced;
- configd remained operational;
- service start completed;
- dvtws2 and supervisor processes were present;
- ipfw divert state and required kernel modules were present;
- execution status reached 13|13|ready|ok;
- HOSTLIST:youtube, HOSTLIST:user, IPSET:telegram, and exclusion data were loaded;
- four runtime profiles were generated.

The final startup error encountered before success was isolated to the preset. It used
--blob=tls7, which requires files/fake/tls7.bin under the direct shorthand contract.
The file did not exist. After the project owner updated the preset to use an available
real blob filename, the service started successfully.

Documentation recovery performed:

- replaced stale PROJECT_STATE.md with an authoritative current state;
- rebuilt ROADMAP.md around completed milestones and remaining live tests;
- corrected duplicate Finding IDs in AUDIT.md;
- updated LIFE-010, LIFE-011, and LIFE-012 verification status;
- recorded the live package baseline and remaining lifecycle matrix;
- recorded the blob-name contract decision;
- synchronized architecture, requirements traceability, workflow, and changelog;
- intentionally left the public README strategy example unchanged by explicit instruction.

Remaining tests:

- upgrade;
- remove;
- preserved-runtime verification;
- reinstall;
- reboot;
- controlled runtime failure;
- full GUI/API matrix.

==================================================
2026-07-30 — UNIFIED STRATEGY GUIDANCE REMEDIATION
==================================================

Completed the source-level remediation for AUDIT findings GUI-001 and GUI-002.

Implemented as one logical change:

- replaced obsolete Settings guidance for separate HTTP and HTTPS Strategy fields;
- documented the unified Traffic Strategy workflow and explicit --new profile boundaries;
- replaced both static and dynamic Diagnostics references to the removed HTTPS Strategy field;
- added a warning to merge a blockcheck result with existing profiles rather than replacing a complete strategy blindly;
- increased package revision from 8 to 9;
- synchronized PROJECT_STATE.md, ROADMAP.md, AUDIT.md, DEVLOG.md, and CHANGELOG.md.

Static verification completed:

- general.xml parses successfully;
- repository search finds no remaining current MVC guidance that directs users to removed split strategy fields;
- no runtime or backend behavior was changed.

Pending live verification:

- rendered Settings information block;
- Diagnostics initial guidance;
- successful, partial, timeout, and error result paths.


==================================================
2026-07-30 — GIT-FIRST UNIFIED PATCH WORKFLOW AND VERIFY SCRIPT MODE
==================================================

Approved and documented the project's existing remote change-delivery method as a
permanent engineering rule.

Completed:

- established unified Git `.patch` files as the default delivery artifact;
- required `git apply --check` before patch application;
- required patch application through Git followed by full diff review and validation;
- prohibited direct console editing of tracked repository files;
- documented that ordinary unified patches do not require repository history or
  `git format-patch`;
- retained `git format-patch` / `git am` as an optional workflow when commit metadata must
  be preserved;
- corrected `scripts/verify-release-package.sh` from mode 100644 to executable mode
  100755.

Verification already completed before this change:

- the script successfully verified package metadata when invoked as
  `sh ./scripts/verify-release-package.sh dist/os-zapret2-restyle-0.2.1_9.pkg`;
- package `os-zapret2-restyle-0.2.1_9` installed successfully;
- configd actions were registered;
- the service reported running;
- obsolete split HTTP/HTTPS Strategy guidance was absent from installed MVC files;
- unified Traffic Strategy guidance was present.

Remaining verification for this logical change:

- apply the supplied patch with Git;
- invoke `./scripts/verify-release-package.sh` directly and confirm successful execution;
- review and commit the complete diff.

2026-07-30 — GitHub workflow and authoritative archive patch baseline

- added `docs/GITHUB_WORKFLOW.md` as the specialist procedure for commit, push,
  release preparation, release assets, and publication checks;
- made `INDEX.md` the mandatory context-recovery entry point and included the
  GitHub workflow in the required reading order and document map;
- established the project owner's actual working-tree archive as the only valid
  baseline for multi-file patch preparation;
- standardized archive names as
  `os-zapret2-restyle-<short_commit_sha>.tar.gz`;
- established that the archive is supplied after changes are agreed and is
  replaced after the resulting patch is committed;
- required successful `git apply --check` against an unchanged archive copy
  before a patch is delivered.

==================================================
2026-07-30 — RELEASE v0.2.2 BASELINE COMPLETED
==================================================

Completed the clean-baseline release cycle from commit fc6b208.

Confirmed:

- VERSION 0.2.2 with PLUGIN_REVISION 1;
- annotated tag v0.2.2 and origin/main both resolve to fc6b208;
- package os-zapret2-restyle-0.2.2_1 was built and passed the release-package verifier;
- package installation and runtime operation were confirmed on OPNsense;
- the GitHub Pages pkg repository was rebuilt and updated for 0.2.2_1;
- inherited upstream tags v1.6.1 through v1.7.2 were removed from origin;
- no source changes were introduced after release publication and package verification.

Release v0.2.2 includes the executable release verifier, the Git-first unified patch
workflow, docs/GITHUB_WORKFLOW.md, INDEX.md as the documentation recovery entry point,
and the owner-supplied short-SHA archive as the authoritative baseline for multi-file
patch preparation.

This documentation synchronization is a documentation-only follow-up. It does not alter
the package, runtime, GUI, Backend v2, service lifecycle, or repository metadata.

Next ordered work remains the open Milestone 7 live-test matrix: unified strategy
guidance, upgrade, removal, preserved-runtime reinstall, reboot, controlled dvtws2
termination, and GUI/API behavior.

==================================================
2026-07-30 — MILESTONE 7 CLOSURE AND MILESTONE 8 PRIORITIES
==================================================

Completed:

- Closed Milestone 7 by explicit project-owner decision.
- Preserved the unperformed upgrade, removal, reinstall, reboot, controlled-failure, timeout-chain, and GUI/API checks as a focused regression backlog rather than marking them passed.
- Opened Milestone 8.
- Set the first priority to GUI management of stable bol-van/zapret2 releases through the existing setup.sh backend: installed-version reporting, release listing and selection, update notification, installation, update, and repeat installation.
- Required separate reporting of runtime presence and runtime/service health.
- Set GUI management of an additional BLOB repository as the second priority, with all repository and contract details deferred until supplied by the project owner.
- Standardized all OPNsense console instructions on csh, with explicit `sh` entry and `exit` return when POSIX shell is mandatory.
- Standardized normal Git verification on `git status --short`, `git diff --check`, and `git diff --stat`; full diff output remains a debugging/review tool rather than the default workflow.

No source code, package version, package revision, runtime, or release artifact changed in this documentation-only work unit.

==================================================
2026-07-31 — GITHUB COMMIT BASELINE REPLACED MANDATORY ARCHIVES
==================================================

Completed:

- made the exact current commit in the official GitHub repository the default
  authoritative development baseline;
- required the full base SHA to be recorded before repository changes;
- removed the requirement for the project owner to supply a fresh working-tree
  archive for state already committed and pushed;
- retained archives and patches only as explicit transfer methods for relevant
  uncommitted or unpushed local state;
- required one logical multi-file change, including documentation and file modes,
  to be published as one atomic commit;
- allowed direct fast-forward publication to `main` only after explicit
  project-owner instruction and after rechecking that `main` still equals the
  recorded base SHA;
- prohibited force-push;
- retained working branches, pull requests, and unified patches as optional
  workflows;
- removed GitHub CLI as a mandatory dependency when an authenticated GitHub
  integration/API or ordinary Git is available;
- preserved live OPNsense backup requirements as a separate operational safety
  rule.

Documentation synchronized:

- INDEX.md;
- PROJECT_STATE.md;
- DECISIONS.md;
- WORKING_CONVENTIONS.md;
- DEVELOPMENT_GUIDE.md;
- GITHUB_WORKFLOW.md;
- CHANGELOG.md;
- README.md.

No plugin source, package version, package revision, runtime behavior, release
artifact, tag, or pkg repository content changed.

==================================================
2026-07-31 — CFG-001 CONFIGURATION ACTIVATION CORRECTION IMPLEMENTED
==================================================

Confirmed:

- live OPNsense evidence showed the previous dvtws2 strategy after Settings Apply
  and reboot;
- OPNsense configd actions of type `script` return exact `OK` on success and
  non-empty `Error (N)` on command failure;
- SettingsController and ServiceController accepted every non-empty response as
  success;
- the start lifecycle did not regenerate zapret.conf, while reconfigure did.

Implemented in source for package revision 2:

- require exact `OK` in both MVC reconfigure paths;
- move successful template-generation ownership into zapret_service.sh for both
  start and reconfigure;
- preserve Settings Apply rollback and report generated-template rollback failure
  separately;
- validate the configctl exit status and exact template-action response;
- add scripts/test-config-activation-contract.sh and run it in CI.

Static verification:

- the focused configuration-activation test passes;
- changed shell scripts pass `sh -n`;
- `git diff --check` passes;
- both changed PHP files parse successfully with php-parser;
- native `php -l` remains assigned to the existing containerized CI step because
  PHP is unavailable in the preparation environment.

Not yet claimed:

- package build;
- installation on OPNsense;
- invalid Apply rollback live behavior;
- valid Apply propagation through config.xml, zapret.conf, dvtws.args, and the
  process command line;
- reboot startup with the saved strategy.

==================================================
2026-07-31 — AUTONOMOUS ORDINARY PATCH DELIVERY DOCUMENTED
==================================================

Completed from GitHub `main` baseline
`506b20f3c56e1a174ba3f5aa9c2c769ad0338f55`:

- made working branch → one commit → Draft PR → CI → Ready → squash merge the
  default delivery path for an ordinary requested development task;
- recorded standing project-owner authorization for branch creation, commit,
  publication, PR creation, Ready transition, verified merge, and cleanup of the
  temporary task branch without repeated confirmation;
- defined explicit request wording as the stopping boundary for analysis-only,
  patch-only, branch-only, and PR-only work;
- defined one explicit release request as authority for the complete verified
  release pipeline without stage-by-stage confirmations;
- retained stop boundaries for unresolved architecture/product choices, unpublished
  local state, unresolvable checks, new credentials/authority, destructive work,
  force/history rewrite/direct-main publication, and mandatory owner-supplied live
  OPNsense evidence;
- documented that GitHub App commits may differ in commit metadata while remaining
  acceptable only after exact tree, mode, parent, and scope verification;
- defined routine package-revision handling and one consolidated blocking question
  only when required evidence or authority cannot be obtained independently;
- kept documentation-only governance changes outside package contents from changing
  `VERSION` or `PLUGIN_REVISION`; the standard CI package job remains the build-stage
  verification for this change.

Affected documentation:

- PROJECT_STATE.md;
- DECISIONS.md;
- WORKING_CONVENTIONS.md;
- DEVELOPMENT_GUIDE.md;
- GITHUB_WORKFLOW.md;
- DEVLOG.md;
- CHANGELOG.md.

No plugin source, runtime behavior, package revision, version, release tag, release
asset, or pkg repository content changed.

==================================================
2026-07-31 — PRERELEASE v0.2.3 PREPARATION
==================================================

Prepared the CFG-001 correction for installation and focused OPNsense verification
without modifying the immutable v0.2.2 release.

Release metadata:

- VERSION advanced from 0.2.2 to 0.2.3;
- PLUGIN_REVISION reset from 2 to 1;
- expected tag is v0.2.3;
- expected package is os-zapret2-restyle-0.2.3_1.pkg;
- GitHub Release remains a prerelease until Apply and reboot verification is recorded.

Documentation synchronized:

- current project state and roadmap now distinguish the verified v0.2.2 baseline
  from the v0.2.3 CFG-001 prerelease candidate;
- CFG-001 remains open pending invalid Apply, valid Apply, and reboot evidence;
- README version and unsigned-repository policy were aligned with active decisions;
- the security policy now identifies the latest prerelease and `main` as maintained;
- requirements now derive plugin version from VERSION instead of embedding a stale
  numeric value.

Next:

Publish the release-preparation PR, create v0.2.3 from the verified merged commit,
wait for the release workflow, verify the package and Pages repository, then install
0.2.3_1 on OPNsense for the focused CFG-001 test matrix.
