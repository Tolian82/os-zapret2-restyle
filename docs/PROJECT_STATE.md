# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Current version, branch, phase, priority, last completed work, blockers, or next actions change.

Read after:
INDEX.md

Do not store here:
Decision history, permanent rules, detailed workflow, architecture details, or product requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
os-zapret2-restyle

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Branch:
main

Published prerelease tag commit:
4ae28965be3661b5b0309d398d924186657662f4

Development tree:
/root/os-zapret2-restyle

Version source:
VERSION

Current version:
0.2.5

Current package revision:
1

Verified package:
os-zapret2-restyle-0.2.2_1

Published prerelease package:
os-zapret2-restyle-0.2.4_1

Current phase:
Preparing prerelease v0.2.5 with the LIFE-014 package/runtime activation lifecycle

Current priority:
Publish prerelease v0.2.5 and package 0.2.5_1, then verify upgrade stop/start state
preservation and setup-driven runtime refresh before the CFG-001 reboot matrix.

Known blockers:
Package 0.2.4_1 replaces plugin files during upgrade without restarting a service
that was already running. Its old +PRE_DEINSTALL also suppresses stop failure, so an
upgrade can continue into a mixed state with new files and old processes. Source
remediation is complete and is being prepared for publication as v0.2.5 / package
0.2.5_1; package and live verification remain.

==================================================
CURRENT CORRECTIVE WORK — LIFE-014 — 2026-08-01
==================================================

Live upgrade to package 0.2.4_1 confirmed that pkg replaced plugin files while the
old dvtws2 and supervisor processes remained active. The old processes retained the
pre-0.2.4 descriptor behavior until manually terminated and the service was started
again. The same test confirmed that +PRE_DEINSTALL hides stop failure with `|| true`.

Approved source remediation for prerelease v0.2.5 / package 0.2.5_1:

- new +PRE_INSTALL records whether a complete service was running and stops it before
  the old package hook and file replacement;
- +PRE_DEINSTALL retains the same fail-closed stop contract for removal and later upgrades;
- synchronous stop and the stopped-state check are mandatory, and failure aborts pkg;
- new +POST_INSTALL starts and verifies the service only when that marker exists;
- a service that was stopped before upgrade remains stopped;
- setup.sh install performs an exact-OK service restart after the new dvtws2 is built
  and verified;
- transactional runtime staging and rollback remain a separate future change.

Local static verification and PR CI passed for the implementation commit. Release
package publication and the live upgrade matrix remain required.

==================================================
CURRENT DEVELOPMENT DELIVERY POLICY — 2026-07-31
==================================================

The default delivery path for an ordinary requested project change is:

working branch
        ↓
one atomic commit
        ↓
Draft PR
        ↓
required CI
        ↓
Ready for review
        ↓
squash merge
        ↓
verify `main`

The project owner has granted standing authority to complete this ordinary patch
cycle without asking separately for branch creation, commit, branch publication,
PR creation, Ready transition, squash merge, or cleanup of the temporary branch
created for that task. An explicit request to stop at analysis, a local commit, a
branch, a PR, or a patch overrides the default and defines the stopping point.

Release publication remains a separate scope. One explicit request to make a
release authorizes the complete verified release cycle without repeated approvals,
but an ordinary development request does not authorize a tag, GitHub Release, pkg
repository publication, or package publication. The current documentation change
does not create another release or modify an existing release.

The detailed standing-authority and escalation boundaries are maintained in
DECISIONS.md, WORKING_CONVENTIONS.md, DEVELOPMENT_GUIDE.md, and
GITHUB_WORKFLOW.md.

Publication transport is selected from available capabilities: authenticated
GitHub integration/API, authenticated ordinary Git, then GitHub CLI. Missing `gh`
alone is not a blocker and must not stop an authorized patch or release while an
approved authenticated alternative is available.

Project-response preflight is mandatory: complete the INDEX.md reading sequence
before any substantive diagnosis, command, change, or publication action. Before
delivering OPNsense commands, reject POSIX-only constructs unless the block explicitly
enters and exits `sh`. Release authorization already granted for a named version
survives a transport fallback and must not be requested again.

The repository root `AGENTS.md` is the machine-discoverable enforcement layer for
this gate. It requires complete reading and explicitly names DECISIONS.md,
WORKING_CONVENTIONS.md, and DEVELOPMENT_GUIDE.md as the methodology and principles
that must be understood before selecting an implementation or publication path.

Release-trigger automation is implemented in source: a canonical release-preparation
merge that changes VERSION creates the immutable tag through GitHub Actions and
dispatches the existing Release workflow. Static contract verification is assigned to
CI; the next explicitly approved release supplies the first live end-to-end evidence.

==================================================
CURRENT CORRECTIVE WORK — LIFE-009 — 2026-08-01
==================================================

Package 0.2.3_1 live evidence confirmed that descriptor 9 for
`/var/run/zapret2-lifecycle.lock` was inherited by both daemon wrappers, dvtws2,
the supervisor shell, and supervisor sleep. Therefore every later Apply waited 30
seconds and failed with status 75 although no competing lifecycle task existed.

The 0.2.4_1 correction closes descriptor 9 on both long-lived daemon launch commands
and adds a focused CI regression test. Live OPNsense verification confirmed that the
new dvtws2 and supervisor trees no longer retain descriptor 9, the lock is free after
startup, and a changed strategy reaches dvtws.args and the active process. The
descriptor correction is live verified; the broader LIFE-009 concurrency/failure
matrix and the CFG-001 reboot persistence check remain open.

Publication evidence:

- tag v0.2.4 resolves to 4ae28965be3661b5b0309d398d924186657662f4;
- Release workflow run 30691963458 completed successfully;
- GitHub prerelease assets are os-zapret2-restyle-0.2.4_1.pkg and SHA256SUMS;
- GitHub Pages serves the matching FreeBSD:15:amd64 package and repository metadata.

==================================================
CURRENT CORRECTIVE WORK — CFG-001 — 2026-07-31
==================================================

Development base:
0f379a0117e64d44d1f8987f3f5a806b67ac6fbd

Confirmed defect:

- configd actions of type `script` encode command failure as non-empty
  `Error (N)`;
- both MVC reconfigure paths accepted every non-empty response as success;
- start did not regenerate zapret.conf from saved OPNsense settings;
- therefore Apply could report success while the previous runtime remained active,
  and reboot could reuse the stale generated file.

Source remediation included in prerelease candidate 0.2.3_1:

- both MVC paths require the exact response `OK`;
- zapret_service.sh owns template refresh before start and reconfigure;
- failed Settings Apply restores the previous persistent model and generated
  template while the orchestrator preserves the previous runtime;
- a focused configuration-activation regression test covers exact `OK`, encoded
  `Error (N)`, process failure, and lifecycle refresh ownership.

Both changed PHP files parse successfully with php-parser. Native `php -l` passed in
CI. The release workflow built and published package 0.2.3_1 successfully; focused
OPNsense live verification remains open.

==================================================
PUBLISHED PRERELEASE — v0.2.3 — 2026-07-31
==================================================

Confirmed publication state:

- annotated tag v0.2.3 resolves to commit da3d8e7ddbb16561bfdc5628daa483b97f3bb9f4;
- GitHub Actions Release run 30662375815 completed successfully;
- Validate release, Build package and repository, Publish GitHub Release, and
  Publish pkg repository all passed;
- GitHub Release v0.2.3 is published as a prerelease rather than a stable baseline;
- release assets include os-zapret2-restyle-0.2.3_1.pkg and SHA256SUMS;
- GitHub Pages serves meta.conf, data.pkg, packagesite.pkg, SHA256SUMS, the package,
  and zapret2-restyle.conf successfully;
- version 0.2.2 / package 0.2.2_1 remains the latest live-verified baseline.

The publication gate is closed. CFG-001 remains open only for focused invalid Apply,
valid Apply, exact GUI error, and reboot verification on OPNsense.

==================================================
RELEASE BASELINE — v0.2.2 — 2026-07-30
==================================================

Release v0.2.2 is the current clean project baseline.

Confirmed release state:

- main and annotated tag v0.2.2 resolve to commit fc6b208;
- VERSION is 0.2.2 and PLUGIN_REVISION is 1;
- verified package is os-zapret2-restyle-0.2.2_1;
- the release package passed scripts/verify-release-package.sh;
- package installation and runtime operation were confirmed on OPNsense;
- the GitHub Pages pkg repository was rebuilt and updated for 0.2.2_1;
- inherited upstream tags v1.6.1 through v1.7.2 were removed from origin;
- no source changes were made after repository publication and package verification.

Release v0.2.2 also fixes the documentation-delivery baseline:

- scripts/verify-release-package.sh is executable and may be invoked directly;
- docs/GITHUB_WORKFLOW.md is the specialist release/publication procedure;
- INDEX.md is the mandatory documentation recovery entry point;
- historical v0.2.2 development used unified Git patches and owner-supplied
  archives; that delivery mechanism is now optional rather than mandatory.

Current development baseline:

- the exact current commit in the official GitHub repository is authoritative;
- the full base SHA is fixed before work begins;
- no owner-supplied archive is required for committed and pushed repository state;
- unpublished local changes must be pushed first or transferred explicitly;
- a logical change is published as one atomic commit;
- direct fast-forward publication to `main` requires explicit project-owner
  instruction;
- a branch, pull request, or patch is optional and used only when requested or
  when pre-`main` validation is required;
- no particular GitHub client, including GitHub CLI, is mandatory.

The public README strategy example remains intentionally unchanged by explicit project-owner instruction.

==================================================
AUTHORITATIVE CURRENT RESULT — 2026-07-30
==================================================

A complete package installation and runtime start has been verified on OPNsense.

Confirmed package chain:

1. the package installs through pkg;
2. +POST_INSTALL registers plugin files, reloads templates, and prints the explicit runtime setup command;
3. runtime preparation is started manually with:
   /usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install
4. setup installs required dependencies without making pkg installation perform nested package work;
5. setup obtains the pinned bol-van/zapret2 release v1.0.3;
6. setup builds executable binaries/my/dvtws2;
7. configd actions are registered and callable through configctl;
8. templates generate the runtime configuration;
9. Backend v2 parses, normalizes, resolves, validates, and generates runtime arguments;
10. lifecycle code installs the ipfw divert rule;
11. dvtws2 starts;
12. supervisor starts and monitors the configured process identity;
13. service status reaches ready/ok.

Live evidence from the installed system:

- package: os-zapret2-restyle-0.2.1_8;
- execution status: 13|13|ready|ok;
- dvtws2 process present;
- supervisor process present;
- expected PID files present;
- ipfw divert rule present;
- ipfw.ko and ipdivert.ko loaded;
- HOSTLIST and IPSET target files loaded by dvtws2;
- four runtime profiles generated from the tested strategy.

The final startup failure found during the test was not an installation defect. The preset requested shorthand blob name tls7, so the resolver correctly looked for files/fake/tls7.bin. After the preset was updated to use an available real blob filename, the service started successfully.

The public README strategy example is intentionally left unchanged for now by explicit project-owner instruction. It will be rewritten in a later dedicated documentation pass.

==================================================
CURRENTLY CONFIRMED
==================================================

Project and distribution:

- independent repository and package identity;
- package/plugin name os-zapret2-restyle;
- internal OPNsense service and configd namespace zapret;
- VERSION as the single version source;
- Makefile PLUGIN_NAME remains zapret2 as required by the OPNsense framework;
- GitHub Release assets and GitHub Pages pkg repository;
- FreeBSD:15:amd64 repository layout for supported OPNsense 26.7;
- repository configuration uses ordinary https:// and signature_type: none;
- generated package metadata and archive preflight validation.

Runtime and backend:

- modular Backend v2;
- unified Traffic Strategy;
- placeholders limited to <HOSTLIST:name> and <IPSET:name>;
- automatic one-selector-per-runtime-profile normalization;
- user-authored --new boundaries retained;
- Target Mode;
- global domain exclusions;
- strict domain and IP validation;
- candidate build and validation;
- transactional Apply design, with the CFG-001 response/boot correction implemented
  in source and still awaiting focused live verification;
- atomic runtime activation and rollback;
- launcher, firewall, dvtws2, and supervisor lifecycle;
- process identity validation for dvtws2 and supervisor;
- lockf-backed lifecycle serialization;
- supervisor-only runtime failure detection;
- runtime cleanup on launch or monitored-process failure;
- blob shorthand resolves directly to files/fake/<name>.bin;
- native upstream blob declarations containing ':' remain unchanged.

Package lifecycle:

- pkg installation does not download, compile, or install runtime dependencies;
- +POST_INSTALL prints the exact setup command;
- +PRE_DEINSTALL stops the service synchronously;
- +POST_DEINSTALL is a no-op and does not restart configd;
- package removal preserves runtime and shared dependencies;
- setup uses bol-van/zapret2 pinned to v1.0.3;
- setup backend is the approved single backend for the first Milestone 8 GUI Maintenance feature.

Live behavior:

- valid configuration reached 13|13|ready|ok;
- HOSTLIST:youtube, HOSTLIST:user, IPSET:telegram, and hostlist exclusion data were loaded;
- invalid candidate data preserves the active runtime, service PID, and ipfw rules;
- invalid IP input fails during target validation;
- corrected preset using an existing blob starts successfully.


==================================================
MILESTONE TRANSITION — 2026-07-30
==================================================

Milestone 7 is closed by explicit project-owner decision. The published v0.2.2 baseline remains the verified foundation. Remaining upgrade, removal, reinstall, reboot, controlled-failure, timeout-chain, and GUI/API live tests were not falsely marked as passed; they remain in the focused regression backlog and may be executed when relevant to later changes.

Milestone 8 is now active. Ordered priorities:

1. GUI management of bol-van/zapret2 stable releases through the existing backend:
   /usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh
   The GUI must report the installed version, obtain the available stable-release list, notify about updates, allow release selection, install a selected release, update to a newer release, and repeat installation of the current release. Runtime presence and runtime/service health must be displayed as separate states.
2. GUI management of an additional BLOB repository. The repository URL, manifest, file layout, integrity model, and update contract are intentionally deferred until the project owner supplies the repository.

All OPNsense console instructions are written for the default csh root shell. When POSIX sh is mandatory, the instruction must explicitly enter sh and explicitly run exit before returning to csh-oriented commands.

==================================================
OPEN VERIFICATION WORK
==================================================

The following are not yet classified as fully live verified:

1. package upgrade from an earlier revision to 0.2.1_8;
2. package removal while the service is running;
3. preservation of runtime and dependencies after package removal;
4. package reinstall over preserved runtime;
5. full OPNsense reboot and automatic service-start behavior;
6. controlled dvtws2 crash and supervisor cleanup/recovery behavior;
7. direct diagnostics route behavior;
8. complete GUI → MVC → configd → backend API live matrix;
9. blockcheck behavior across the complete browser/PHP/configd/script timeout chain;
10. classification of the currently unused reconfigure API endpoint.

These are remaining tests, not evidence that the implemented architecture is broken.

==================================================
CURRENT AUDIT FINDINGS
==================================================

Authoritative detailed records are in AUDIT.md.

Still open or requiring live verification:

- CFG-001 Settings Apply/configd response and boot template synchronization;
- API diagnostics route duplication and direct-route behavior;
- stale GUI help text referring to removed HTTP/HTTPS strategy fields;
- blockcheck timeout inconsistency;
- unused reconfigure endpoint classification;
- rc.d enable-source behavior;
- remaining package upgrade/remove/reinstall/reboot tests;
- focused supervisor failure-path verification.

Closed or implementation-complete findings include:

- duplicate firewall_rules_present() declaration;
- disconnected inherited watchdog removal;
- PID identity hardening;
- conditional supervisor kill escalation;
- lifecycle serialization;
- setup launcher executable mode;
- wrong upstream zapret repository;
- nested package-managed runtime lifecycle;
- GitHub Pages repository URL scheme;
- release workflow catalogue filename;
- native ABI artifact staging.

==================================================
IMMEDIATE NEXT ACTIONS
==================================================

1. Publish prerelease v0.2.5 and package 0.2.5_1 from the verified release-preparation merge.
2. Upgrade a running 0.2.4_1 service and confirm old PIDs stop before replacement and
   new PIDs start after replacement.
3. Upgrade with the service already stopped and confirm it remains stopped.
4. Force a stop failure and confirm pkg aborts before replacing files.
5. Run setup.sh install and confirm the runtime rebuild is followed by lifecycle refresh.
6. Reboot OPNsense and confirm that config.xml, zapret.conf, dvtws.args, process arguments, PID ownership, supervisor, and ipfw state agree.
7. Resume the Milestone 8 stable-release GUI work package.

==================================================
WORKING RULES FOR RESUMPTION
==================================================

Before changing code:

1. read docs/INDEX.md;
2. follow the mandatory reading order;
3. inspect the actual repository tree;
4. read the current GitHub `main`, record its full SHA, and verify that any local
   checkout contains no unpublished state required by the change;
5. use AUDIT.md Finding IDs for remediation work;
6. record approved concepts in DECISIONS.md;
7. update every affected document in the same logical commit;
8. never infer current state from chat history alone.

Release v0.2.2 at fc6b208 and package 0.2.2_1 remain the verified baseline.
CFG-001 was published as prerelease v0.2.3 / package 0.2.3_1 at da3d8e7, where live
testing exposed the LIFE-009 descriptor-inheritance defect. The correction is
published as v0.2.4 / package 0.2.4_1 and still requires the focused lock, Apply, and
reboot verification recorded above.


==================================================
2026-07-31 — GITHUB-COMMIT DEVELOPMENT BASELINE
==================================================

Current development policy:

- the exact current GitHub commit, normally `main`, is the source baseline;
- all changed content, file modes, and synchronized documentation form one atomic
  logical commit;
- repository files are not edited directly in the OPNsense console;
- before publication, static validation and complete diff review must pass;
- immediately before publication, confirm that `main` still points to the recorded
  base SHA;
- direct publication to `main` is fast-forward only and requires explicit
  project-owner instruction;
- force-push is prohibited;
- the working-branch and PR workflow is the default ordinary publication path;
- a unified patch is an explicit narrower delivery mode, not a publication prerequisite;
- after publication, perform the one build and one focused verification required
  by the logical change;
- temporary files, logs, diagnostics, installed-system configuration, and other files
  outside the repository are not restricted by this rule.

Local-only exception:
GitHub does not contain uncommitted or unpushed changes from the project owner's
OPNsense checkout. If they are relevant, stop and request that they be committed
and pushed or explicitly transferred as an archive or patch. The old requirement
for a fresh archive before every multi-file change is superseded.
