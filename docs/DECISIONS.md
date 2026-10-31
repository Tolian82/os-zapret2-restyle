# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Why was this approved?

Purpose:
Record every approved engineering concept and decision with its reason,
consequences, and affected documents.

Updated when:
A new concept is approved, an active decision changes, or an earlier decision is superseded.

Read after:
PROJECT_STATE.md

Do not store here:
Current task status, implementation history, detailed procedures, or full architecture descriptions.

==================================================
DECISION FORMAT
==================================================

Date:
YYYY-MM-DD

Decision:
What was approved.

Reason:
Why it was approved.

Consequences:
What this changes or constrains.

Affected documents:
Which project documents must remain synchronized.

Status:
Active, superseded, rejected, or historical.

==================================================
2026-07-28 — INDEPENDENT PROJECT IDENTITY
==================================================

Decision:
The project is an independent project named os-zapret2-restyle.

Installed package:
os-zapret2-restyle

Makefile PLUGIN_NAME:
zapret2-restyle

Reason:
The project must not depend on the identity or repository structure of the old
plugin. OPNsense adds the os- package prefix automatically.

Consequences:
All package, build, CI, and release logic must use the independent project
identity.

Affected documents:
PROJECT_STATE.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md
README.md

Status:
Active

==================================================
2026-07-28 — INTERNAL SERVICE NAME REMAINS ZAPRET
==================================================

Decision:
The internal service name and configd namespace remain zapret.

Reason:
They are stable integration identifiers. Renaming them would create migration
and integration risk without practical benefit.

Consequences:
The presence of the word zapret in service or configd integration is not by
itself evidence of obsolete inheritance.

Affected documents:
WORKING_CONVENTIONS.md
ARCHITECTURE.md

Status:
Active

==================================================
2026-07-28 — VERSION IS THE SINGLE VERSION SOURCE
==================================================

Decision:
VERSION is the only source of project version information.

Reason:
Multiple independent version values eventually diverge and create incorrect
packages or releases.

Consequences:
Makefile, build scripts, CI, package metadata, and release automation must read
or validate VERSION instead of maintaining separate versions.

Affected documents:
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md

Status:
Active

==================================================
2026-07-28 — DOCUMENTATION IS PART OF ARCHITECTURE
==================================================

Decision:
Project documentation is part of the project architecture.

Reason:
The project is expected to evolve over a long period. Critical knowledge must
live in the repository and not depend on chat history or memory.

Consequences:
A code change or approved concept is incomplete until all affected documentation
is updated in the same logical commit.

Affected documents:
INDEX.md
PROJECT_STATE.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md
DEVLOG.md
ROADMAP.md
REQUIREMENTS.md
README.md
CHANGELOG.md

Status:
Active

==================================================
2026-07-28 — EVERY APPROVED CONCEPT MUST BE RECORDED
==================================================

Decision:
Every approved concept must be recorded in DECISIONS.md and, when applicable,
in the corresponding specialist document.

Reason:
Important decisions must not remain only in discussion history.

Consequences:
Whenever a concept is approved, the same logical commit must update DECISIONS.md
and every affected document.

Affected documents:
DECISIONS.md
All specialist documents as applicable

Status:
Active

==================================================
2026-07-28 — ONE DOCUMENT, ONE QUESTION
==================================================

Decision:
Each engineering memory document must answer one primary question.

Question mapping:

INDEX.md
Where should I look?

PROJECT_STATE.md
Where is the project now?

DECISIONS.md
Why was this approved?

WORKING_CONVENTIONS.md
Which rules are already settled?

DEVELOPMENT_GUIDE.md
How do we work?

ARCHITECTURE.md
How is the system built?

DEVLOG.md
What was done?

ROADMAP.md
What should be done next?

REQUIREMENTS.md
What must the product do?

Reason:
Single-responsibility documents reduce duplication, ambiguity, and context
recovery time.

Consequences:
Information that answers a different question must be moved to the correct
document rather than duplicated without need.

Affected documents:
INDEX.md
All engineering memory documents

Status:
Active

==================================================
2026-07-28 — INDEX IS THE ENTRY POINT
==================================================

Decision:
INDEX.md is the entry point to the engineering memory system.

Reason:
A reader must be able to determine immediately where each type of information
belongs and which document to read next.

Consequences:
INDEX.md contains the document map, mandatory reading order, and responsibility
boundaries. It must not duplicate full project content.

Affected documents:
INDEX.md
PROJECT_STATE.md
README.md

Status:
Active

==================================================
2026-07-28 — DOCUMENT ROLE BLOCK IS REQUIRED
==================================================

Decision:
Every internal engineering memory document begins with a DOCUMENT ROLE block.

The block states:

- Question answered.
- Purpose.
- Updated when.
- Read after.
- What must not be stored there.

Reason:
A document opened in isolation must explain its responsibility immediately.

Consequences:
New internal documents must include this block. Existing internal documents
must be migrated gradually.

Affected documents:
INDEX.md
PROJECT_STATE.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md
DEVLOG.md
ROADMAP.md
REQUIREMENTS.md

Status:
Active

==================================================
2026-07-28 — MANDATORY CONTEXT RESTORATION ORDER
==================================================

Decision:
The mandatory reading order is:

1. INDEX.md
2. PROJECT_STATE.md
3. DECISIONS.md
4. WORKING_CONVENTIONS.md
5. DEVELOPMENT_GUIDE.md
6. ARCHITECTURE.md
7. DEVLOG.md
8. ROADMAP.md
9. REQUIREMENTS.md

Reason:
This order moves from navigation, to current state, to reasons, to settled
rules, to workflow, to architecture, to history, to future work, and finally
to product requirements.

Consequences:
README.md and all context-restoration instructions must use this order.

Affected documents:
INDEX.md
PROJECT_STATE.md
README.md
DEVELOPMENT_GUIDE.md

Status:
Active

==================================================
2026-07-28 — QUICK CONTEXT BEFORE FULL DETAILS
==================================================

Decision:
Documents should expose a concise quick-context section before full details
where useful.

Reason:
Most context restoration should take seconds, not require rereading hundreds of
lines.

Consequences:
PROJECT_STATE.md must expose version, branch, phase, priority, last completed
work, next action, and blockers near the top.

Affected documents:
PROJECT_STATE.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md

Status:
Active

==================================================
2026-07-28 — ENGINEERING DOCUMENT STYLE
==================================================

Decision:
Internal engineering memory documents use clear section separators such as:

==================================================
SECTION NAME
==================================================

They use minimal decorative Markdown and avoid unnecessary fenced code blocks.

Reason:
The documents are operational memory for engineers, not primarily presentation
documents for GitHub.

Consequences:
Internal documents should favor fast scanning, plain paths, plain commands,
short labels, and clearly separated sections.

Affected documents:
All engineering memory documents

Status:
Active

==================================================
2026-07-28 — SMALL VERIFIED CHANGES
==================================================

Decision:
Large work must be split into small independent logical changes.

Reason:
Large automatically generated patches and monolithic temporary scripts are
difficult to validate and have already caused avoidable failures.

Consequences:
Each logical change must be reviewed, validated, staged explicitly, committed,
pushed, and verified before proceeding.

Affected documents:
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md

Status:
Active

==================================================
2026-07-28 — ONE LOGICAL COMMIT INCLUDES DOCUMENTATION
==================================================

Decision:
Code and all documentation affected by that code belong in the same logical
commit.

Reason:
Separate documentation commits allow project state and implementation to drift
apart.

Consequences:
Before every commit, review whether project state, decisions, conventions,
workflow, architecture, roadmap, requirements, user documentation, or release
history changed.

Affected documents:
All project documents as applicable

Status:
Active

==================================================
2026-07-28 — AUDIT BEFORE REFACTORING
==================================================

Decision:
Perform the API and inherited-reference audit before further broad refactoring
or feature expansion.

Reason:
The project must understand every active interface and inherited dependency
before removing or restructuring code.

Consequences:
The next engineering stage is static inventory followed by live OPNsense tests.

Affected documents:
PROJECT_STATE.md
DEVLOG.md
ROADMAP.md
ARCHITECTURE.md

Status:
Active

==================================================
2026-07-28 — DO NOT REMOVE REFERENCES MECHANICALLY
==================================================

Decision:
Every inherited-looking reference must be classified before removal.

Reason:
Some retained names and paths are intentional integration identifiers,
licensing records, or required engine references.

Consequences:
Each match must be traced through caller, handler, effect, and replacement.

Allowed classifications:

OK
broken
unused
duplicate
inherited
requires live test

Affected documents:
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md

Status:
Active

==================================================
2026-07-28 — TRANSACTIONAL APPLY IS REQUIRED
==================================================

Decision:
Apply must remain transactional.

Reason:
Invalid configuration must never destroy a working service state.

Consequences:
Candidate runtime is built and validated before activation. Failure must
preserve persistent configuration, active runtime, PID, and ipfw state. A
post-activation failure must restore the previous runtime.

Affected documents:
WORKING_CONVENTIONS.md
ARCHITECTURE.md
REQUIREMENTS.md
DEVLOG.md

Status:
Active

==================================================
2026-07-28 — REPOSITORY SOURCE IS AUTHORITATIVE
==================================================

Decision:
The repository src tree is authoritative.

Reason:
Changes made only to installed files are temporary and are lost during rebuild
or reinstall.

Consequences:
Every live-system fix must be represented under /root/os-zapret2-restyle/src
before the work is considered complete.

Affected documents:
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md

Status:
Active


==================================================
2026-07-28 — ENGINEERING MEMORY IS A LIVING SYSTEM
==================================================

Decision:
The Engineering Memory System is an active part of development, not static
documentation.

Reason:
The repository must preserve plans, current work, completed work, approved
concepts, discoveries, and next actions so development can resume without
depending on chat history or memory.

Consequences:
Every development stage follows this lifecycle:

1. Define the objective.
2. Record the plan before implementation.
3. Perform the work.
4. Record new concepts, rules, architecture changes, and discoveries as they
   appear.
5. Complete the stage.
6. Record completed work, confirmed results, remaining work, and the next stage.

Affected documents:
PROJECT_STATE.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVLOG.md
ROADMAP.md
DEVELOPMENT_GUIDE.md

Status:
Active

==================================================
MAINTENANCE RULE
==================================================

For every newly approved concept:

1. Add a dated decision entry here.
2. Record the decision, reason, consequences, and affected documents.
3. Update every affected specialist document.
4. Include all related changes in the same logical commit.
5. Mark older decisions as superseded instead of silently deleting history.


==================================================
2026-07-28 — AUDIT.MD IS AN OFFICIAL ENGINEERING MEMORY DOCUMENT
==================================================

Decision:
Add AUDIT.md as the authoritative register of technical audit state.

Reason:
Audit evidence, verified chains, broken chains, classifications, live-test
requirements, and remediation status must not exist only in chat history or be
spread across current-state and history documents.

Consequences:
Every completed audit step is recorded in AUDIT.md. Broken chains are recorded
before remediation. After a fix and verification, the existing entry is updated
with the new status and evidence rather than silently removed.

Affected documents:
INDEX.md
PROJECT_STATE.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md
DEVLOG.md
ROADMAP.md
AUDIT.md

Status:
Active

==================================================
2026-07-28 — DOCUMENTATION-SYSTEM CHANGES ARE ARCHITECTURAL CHANGES
==================================================

Decision:
Changes to document structure, responsibilities, reading order, audit method,
development workflow, decision recording, and documentation-maintenance rules
are architectural changes.

Reason:
The Engineering Memory System controls how project state, decisions, evidence,
and future work are reconstructed. Changing that system changes the engineering
architecture of the project itself.

Consequences:
Such changes require a DECISIONS.md entry, synchronized updates to every affected
specialist document, review in the same logical commit, and explicit reflection
in current state and development history when applicable.

Affected documents:
INDEX.md
PROJECT_STATE.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
DEVLOG.md
ROADMAP.md
AUDIT.md

Status:
Active

==================================================
2026-07-28 — EVERY APPROVED RULE MUST BE DOCUMENTED
==================================================

Decision:
Every approved project rule must be recorded in DECISIONS.md and in the
applicable specialist documents.

Reason:
A rule that exists only in discussion cannot be reliably recovered, audited, or
enforced in later work.

Consequences:
No approved rule is considered active project memory until the related
documentation is updated. Rule changes are committed together with all affected
documents.

Affected documents:
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
INDEX.md

Status:
Active


==================================================
2026-07-28 — AUDIT BLOCKS REQUIRE A DOCUMENTATION COMMIT BEFORE CONTINUATION
==================================================

Decision:
An audit block is considered complete only after all affected Engineering Memory
documents have been updated, reviewed, and committed. Work must not proceed to
the next audit block or to code remediation before that synchronization point.

Reason:
Audit knowledge must remain recoverable from the repository at every stage and
must not exist only in chat history or an uncommitted working tree.

Consequences:
Every audit block ends with a documentation-only synchronization commit when no
code change is yet approved. PROJECT_STATE.md, AUDIT.md, DEVLOG.md, ROADMAP.md,
and DECISIONS.md are updated as applicable before work continues.

Affected documents:
INDEX.md
AUDIT.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
PROJECT_STATE.md
DEVLOG.md
ROADMAP.md

Status:
Active

==================================================
2026-07-28 — AUDIT FINDINGS REQUIRE ACTIONABLE REMEDIATION RECORDS
==================================================

Decision:
Every non-OK audit finding must have a stable ID and record exact affected
locations, the damaged or uncertain chain, evidence, impact, verification plan,
remediation plan, acceptance criteria, required documentation updates, and
current remediation status.

Reason:
A list of problem titles is insufficient for controlled remediation. The project
must preserve what is wrong, where it is wrong, how to prove it, how to repair it,
and how to know the repair is complete.

Consequences:
AUDIT.md becomes the authoritative technical-debt and remediation register.
Finding IDs may be referenced from DEVLOG.md, CHANGELOG.md, commits, tests, and
pull requests. Fixed findings remain in the register with updated status and
verification evidence.

Affected documents:
AUDIT.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
INDEX.md
DEVLOG.md

Status:
Active

==================================================
2026-07-28 — FINDINGS AND ARCHITECTURE DEBT ARE SEPARATE RECORD TYPES
==================================================

Decision:
Separate audit results into Findings and Architecture Debt.

A Finding describes a confirmed implementation defect, inconsistency, obsolete or
unused interface, duplicate, or concrete operational risk.

Architecture Debt describes an unresolved design question whose intended behavior must
be approved before dependent code changes.

Reason:
Implementation defects and design questions require different workflows. Treating both
as generic TODO items encourages code changes before architecture is decided and makes
completion criteria ambiguous.

Consequences:

- AUDIT.md contains distinct Finding and Architecture Debt sections.
- Every Finding includes evidence, verification and remediation plans, acceptance
  criteria, affected documents, and remediation status.
- Architecture Debt follows Open, Discussion, Decision, Implementation, Verification,
  Documentation, and Closed.
- Architecture Debt cannot be closed directly.
- A DECISIONS.md entry is mandatory before implementation of Architecture Debt.
- A Finding cannot be remediated while open Architecture Debt determines its intended
  behavior.
- Resolved Findings and closed Architecture Debt remain in audit history.

Affected documents:
AUDIT.md
INDEX.md
PROJECT_STATE.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md
DEVLOG.md
ROADMAP.md
DECISIONS.md

Status:
Active


==================================================
2026-07-28 — MUTATING LIFECYCLE OPERATIONS USE ONE GLOBAL LOCK
==================================================

Decision:
Serialize start, stop, restart, reconfigure, and runtime-failure through one
FreeBSD lockf-backed mutex in zapret_service.sh. Keep status read-only and
unlocked. Interactive lifecycle commands wait for a bounded interval;
runtime-failure uses an immediate try-lock and ignores a callback that is stale
because another lifecycle operation already owns the runtime.

Reason:
MVC configuration locking ends before backend execution, while all lifecycle
entry points mutate shared runtime trees, backups, PID files, supervisor state,
stage state, and ipfw rules. File-system atomic activation and unique candidate
workspaces do not protect that combined state. Queuing an old supervisor callback
behind reconfigure could tear down the replacement runtime.

Consequences:

- zapret_service.sh is the lifecycle serialization boundary.
- At most one mutating lifecycle operation may own shared runtime state.
- status remains responsive during long operations.
- A busy interactive command returns a clear temporary-failure result without
  modifying runtime state.
- A runtime-failure callback that cannot acquire the lock immediately exits
  without cleanup.
- Focused concurrency and forced-termination live tests are required before
  LIFE-009 is closed.

Affected documents:
ARCHITECTURE.md
AUDIT.md
DECISIONS.md
PROJECT_STATE.md
DEVLOG.md
CHANGELOG.md

Status:
Active

==================================================
2026-07-29 — SUPERVISOR IS THE ONLY RUNTIME FAILURE DETECTOR
==================================================

Decision:
Remove watchdog.sh and watchdog_loop.sh as disconnected inherited code. Keep
supervisor_loop.sh as the only runtime failure detector. Do not add broader health
checks in the same removal commit. Add only explicitly required and inexpensive
checks to the supervisor later, one focused commit at a time.

Responsibility boundaries:

- launcher starts and stops dvtws2 and owns its PID handling;
- supervisor detects runtime failure and invokes runtime-failure;
- zapret_service.sh serializes mutating lifecycle operations;
- runtime-failure performs centralized cleanup;
- supervisor does not rebuild, reconfigure, or independently restart the service;
- no separate cron or daemon watchdog is supported.

Reason:
The watchdog files were not connected to cron, configd, syshooks, package hooks,
GUI, service lifecycle, or supervisor. They contained obsolete HTTP_ARGS and
HTTPS_ARGS behavior and would create a second competing failure-recovery mechanism.
Keeping the removal separate from supervisor enhancement makes the change small,
reversible, and easy to verify.

Consequences:

- watchdog.sh and watchdog_loop.sh are removed from the project;
- existing supervisor behavior remains unchanged in the removal commit;
- regression testing is required before supervisor enhancement;
- future health checks must be detection-only and introduced separately;
- ARCH-001 is decided and LIFE-005 moves to verification;
- ARCH-003 responsibility boundaries are partially resolved.

Affected documents:
ARCHITECTURE.md
AUDIT.md
DECISIONS.md
PROJECT_STATE.md
DEVLOG.md
CHANGELOG.md

Status:
Active


==================================================
2026-07-29 — SUPERVISOR CHILD IDENTITY IS VERIFIED CONTINUOUSLY
==================================================

Decision:
As the first post-watchdog supervisor hardening step, verify on every monitoring
interval that the PID from dvtws2.pid still identifies the configured absolute
dvtws2 binary. Treat disappearance or identity mismatch as the same detected runtime
failure and use the existing runtime-failure callback.

Reason:
A one-time PID read followed only by kill -0 can follow a recycled PID and leave a
failed zapret runtime falsely classified as healthy. Process identity is the minimum
check directly required by the supervisor's existing responsibility.

Consequences:

- supervisor_start passes DVTWS_BIN explicitly to supervisor_loop.sh;
- the loop checks liveness and command identity through FreeBSD /bin/ps;
- the supervisor remains detection-only;
- no runtime-directory, firewall, restart, reconfigure, generation, or repair logic
  is added in this commit;
- broader health checks require separate evidence and separate commits.

Affected documents:
ARCHITECTURE.md
AUDIT.md
DECISIONS.md
PROJECT_STATE.md
DEVLOG.md
CHANGELOG.md

Status:
Active


==================================================
2026-07-29 — OWN PKG REPOSITORY AND GUI-FIRST INSTALLATION
==================================================

Status: Partially superseded by DEC-2026-07-30. Distribution and GUI-first installation
remain approved; the first-Start/Apply bootstrap mechanism below is historical.

Decision:
Publish os-zapret2-restyle through a project-owned FreeBSD pkg repository on GitHub
Pages, with GitHub Releases carrying package assets and checksums. The first public
test release targets FreeBSD:15:amd64 / supported OPNsense 26.7 systems. Installation
and later updates must be available through the standard OPNsense Firmware GUI.

The package must not require the user to run setup.sh over SSH. Runtime bootstrap is
performed automatically on the first configd Start or Apply when dvtws2 is absent.
Do not invoke setup.sh from the pkg post-install hook because setup.sh performs pkg
operations and a maintainer script runs while the package transaction owns the pkg
database lock.

Reason:
A locally added standalone package appears as unknown-repository/misconfigured and
cannot participate cleanly in normal GUI updates. A GUI-installed plugin also must
not leave a manual shell-only completion step. Deferring bootstrap to the first
normal lifecycle action avoids a nested package-manager transaction while preserving
a complete GUI workflow.

Consequences:

- GitHub Pages repository metadata is generated with pkg repo.
- GitHub Release and repository publication are part of the release pipeline.
- The first repository ABI is FreeBSD:15:amd64.
- start/restart/reconfigure receive a 600-second configd timeout.
- missing runtime triggers setup once under the lifecycle mutex.
- package post-install instructions no longer require a manual setup command.
- runtime updates after initial installation remain a separate Maintenance design.

Affected documents:
ARCHITECTURE.md
AUDIT.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
PROJECT_STATE.md
DEVLOG.md
ROADMAP.md
README.md
CHANGELOG.md

Status:
Active


==================================================
2026-07-29 — OPERATIONAL COMMANDS USE SEPARATE BLOCKS
==================================================

Decision:
User-facing development instructions separate read-only checks from state-changing
installation actions. Package publication and installation may be grouped together,
but not with validation. Commands remain in real execution order and account for the
default OPNsense csh root shell.

Reason:
This reduces copy/paste interruptions, prevents accidental mutation during validation,
and saves repeated test time.

Consequences:
WORKING_CONVENTIONS.md and DEVELOPMENT_GUIDE.md define the permanent format.

Status:
Active
==================================================
2026-07-29 — RELEASE TAG PUBLISHES BOTH GITHUB RELEASE AND PKG REPOSITORY
==================================================

Decision:
A version tag matching VERSION triggers one release workflow that validates the tree,
builds the package on FreeBSD 15, creates the FreeBSD:15:amd64 pkg repository with
pkg repo, publishes package and checksum assets to GitHub Releases, and deploys the
repository catalogue plus client configuration to GitHub Pages.

Reason:
The package and repository metadata must be generated from the same validated source
revision. A single tag-triggered pipeline prevents release assets, pkg indexes, VERSION,
and the published repository from drifting apart.

Consequences:
- vMAJOR.MINOR.PATCH must equal VERSION;
- release builds target FreeBSD 15 for the first supported ABI;
- GitHub Pages contains FreeBSD:15:amd64 repository metadata generated by pkg repo;
- GitHub Releases contain the package and SHA256SUMS;
- the first release remains marked prerelease until GUI installation and update are
  verified on OPNsense;
- release publication requires GitHub Pages to use GitHub Actions as its source.

Affected documents:
ARCHITECTURE.md
AUDIT.md
DECISIONS.md
DEVELOPMENT_GUIDE.md
DEVLOG.md
PROJECT_STATE.md
README.md
ROADMAP.md
CHANGELOG.md

Status:
Active


==================================================
DECISION — PRERELEASE REPOSITORY VALIDATION AND SIGNING BOUNDARY
==================================================

Date: 2026-07-29
Status: Approved

Decision:
The release workflow must validate the real current-format outputs of `pkg repo`: at
minimum `meta.conf`, `data.pkg`, and `packagesite.pkg`. A successful package build is
not sufficient for publication.

The v0.1.0 test repository may be published unsigned only as an explicitly documented
prerelease using `signature_type: "none"`. At the time of this decision, repository
signing was considered mandatory before any
release is promoted as stable.

Consequences:
- an obsolete expected filename cannot block a valid first release;
- users are not misled about repository authenticity guarantees;
- stable release acceptance now includes signed repository metadata and live
  verification on OPNsense.

Affected documents:
.github/workflows/release.yml, repository/zapret2-restyle.conf, README.md, AUDIT.md,
PROJECT_STATE.md, ROADMAP.md, DEVLOG.md, CHANGELOG.md.

## 2026-07-29 — Separate native pkg paths from generic CI artifact paths

Decision:
The published pkg repository keeps the conventional `${ABI}` directory name,
including colons. Generic GitHub Actions artifacts use a separate flat staging
directory. GitHub Pages continues through the official Pages artifact action, which
archives the complete site before uploading it.

Reason:
FreeBSD pkg clients and established OPNsense community repositories use native ABI
paths, while the generic artifact service rejects colons for cross-platform
filesystem compatibility.

Consequences:
- no nonstandard ABI renaming is introduced;
- GitHub Release receives files from `release-assets`;
- GitHub Pages receives the complete native pkg repository tree;
- official workflow actions track supported Node.js runtimes.

==================================================
2026-07-29 — COMPLETE APPROVED FUNCTIONALITY BEFORE DESIGN EXPANSION
==================================================

Decision:
Milestone 7 prioritizes completion and verification of the functionality already
approved in REQUIREMENTS.md. General UX audits, design redesigns, and unrelated new
functionality are deferred.

Reason:
The project is a small applied OPNsense plugin. Its immediate value depends on the
existing declared functions working correctly, not on broad product or interface
research.

Consequences:
The next work is ordered as follows:
1. move internal documentation into `docs/`;
2. verify strategy application to concrete HOSTLIST and IPSET targets;
3. close gaps between REQUIREMENTS.md and actual verified behavior.

Navigation, first-run flow, Service, Diagnostics, Maintenance, Status, and Strategy UX
remain unchanged unless an implementation need within the approved scope requires a
focused adjustment.

Affected documents:
PROJECT_STATE.md
ROADMAP.md
DEVLOG.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
AUDIT.md

Status:
Active

==================================================
2026-07-29 — UX IS SUPPORTING WORK, NOT A STANDALONE PROJECT GOAL
==================================================

Decision:
UX work is considered when it is needed to support expanded functionality or when the
existing interface objectively prevents use of an implemented capability. Otherwise
the interface remains stable.

Reason:
A standalone UX programme would divert effort from completing the plugin's small,
defined functional scope.

Consequences:
No general Navigation & Workflow audit is planned. Later interface work should be
proportional to actual functionality and operational need.

Affected documents:
PROJECT_STATE.md
ROADMAP.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md

Status:
Active

==================================================
2026-07-29 — PROJECT GUIDANCE USES PRIORITIES AND RECOMMENDATIONS
==================================================

Decision:
Except where correctness, compatibility, release safety, or repository consistency
requires a firm rule, project process guidance should be expressed as priorities and
recommendations rather than an expanding set of rigid doctrines.

The project follows reasonable sufficiency: use the least complexity needed for a
reliable implementation of the approved scope.

Reason:
Excessive process rules constrain practical engineering and can turn project
organization into work that competes with the addon itself.

Consequences:
The approximate effort balance is a planning preference, not a quota:
- 60% coding;
- 15% documentation;
- 15% current-work discussion;
- 8% future-work discussion;
- 2% broader process or philosophical discussion.

Documentation should preserve useful decisions without attempting to predict and
regulate every possible future nuance.

Affected documents:
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
PROJECT_STATE.md

Status:
Active

==================================================
2026-07-29 — ENGINEERING DOCUMENTATION MOVED TO DOCS/
==================================================

Decision:

Store the complete engineering documentation system in the repository `docs/`
directory.

The following files remain in the repository root because they are project entry
points, licensing or attribution files, build metadata, or package metadata:

- README.md
- LICENSE
- NOTICE
- VERSION
- Makefile
- pkg-descr

The GitHub issue and pull-request templates remain under `.github/`.

Reason:

This provides a conventional open-source repository layout while preserving a clear
root README and keeping the engineering memory system together in one directory.

Consequences:

- Internal development starts from `docs/INDEX.md`.
- Repository-root references must use the `docs/` prefix.
- References between documents inside `docs/` may use short relative names.
- CI checks must validate the new documentation paths.
- Future engineering documents belong under `docs/` unless their platform role
  requires another standard location.

Affected documents:

README.md
docs/INDEX.md
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/DEVLOG.md
docs/CHANGELOG.md
docs/DECISIONS.md
.github/workflows/ci.yml

==================================================
2026-07-29 — AUTOMATIC RUNTIME PROFILE NORMALIZATION
==================================================

Status:
Approved and implemented.

Decision:

The Traffic Strategy keeps user-authored standalone `--new` separators, but a
user is never required to add extra separators or duplicate strategy parameters
only because one profile contains several target placeholders.

A separate backend module, `profile_normalizer.sh`, runs after
`target_mode_apply_all` and before placeholder indexing and target resolution.
For every parsed profile:

- zero supported placeholders leave the profile unchanged;
- one unique supported placeholder leaves the profile unchanged;
- multiple unique supported placeholders produce one runtime profile per
  placeholder;
- each generated profile contains exactly one unique selector and all original
  non-selector strategy text;
- generated profile order follows the selectors' first appearance;
- repeated occurrences of the same selector do not produce duplicate profiles.

The only supported selector families are permanently `HOSTLIST:*` and
`IPSET:*`. `GROUP`, `TARGETSET`, and generic future placeholder families are not
part of the design.

The normalizer must be idempotent and must stage the complete result before
replacing parser output. Downstream target resolution remains responsible for
emitting `--new` between runtime profiles.

Reason:

Target isolation is a backend execution requirement, not a configuration burden
that should force users to copy long dvtws2 strategy blocks. A dedicated,
target-name-independent transformation keeps parser, resolver, and generator
responsibilities narrow while producing correct one-target runtime profiles.

Consequences:

- User configuration remains compact and readable.
- Target Mode generated selectors and explicit selectors follow the same path.
- Resolver behavior remains generic for any registered HOSTLIST or IPSET name.
- Runtime profile count may exceed the number of user-authored profiles.
- Tests must cover zero, one, mixed, repeated, and three-or-more selectors,
  user `--new` boundaries, order preservation, and idempotence.

Affected documents:

- docs/ARCHITECTURE.md
- docs/REQUIREMENTS.md
- docs/DEVLOG.md
- docs/PROJECT_STATE.md
- docs/ROADMAP.md
- README.md

==================================================
2026-07-29 — COUNT-CARRYING PROFILE PIPELINE CONTRACT
==================================================

Decision:
The parsed-profile preparation chain uses a dedicated count-carrying pipeline API.
Each pipeline step accepts WORKDIR and PROFILE_COUNT, performs one transformation or
validation step, and prints the resulting positive PROFILE_COUNT on success.

The approved profile pipeline is:

- parse;
- build target registry;
- apply Target Mode;
- normalize runtime profiles;
- index placeholders.

Reason:
These operations form one ordered transformation chain and share the same profile
collection state. A common contract makes count propagation explicit, removes
stage-specific count handling from the orchestrator, and prevents later steps from
silently using a stale profile count.

Consequences:
`profile_pipeline.sh` owns the adapters and validates every count transition.
Underlying specialist modules retain their focused public APIs. Artifact-building,
activation, launcher, firewall, and supervisor modules are not forced into the profile
count contract because they do not transform a profile collection.

Affected documents:
ARCHITECTURE.md
PROJECT_STATE.md
DEVLOG.md
ROADMAP.md
README.md

Status:
Active


==================================================
2026-07-29 — REPOSITORY REMAINS EXPLICITLY UNSIGNED
==================================================

Status:
Approved

Decision:
The project-owned FreeBSD pkg repository continues to use:

`signature_type: "none"`

This is the approved repository mode for version 0.2.0 and subsequent releases
until a separate future decision explicitly changes it.

This decision supersedes the earlier requirement that repository signing must be
implemented before a release can be promoted from prerelease to stable.

Reason:
The repository is distributed through GitHub Pages over HTTPS, built and
published by the project release workflow, and follows the same practical model
used by established third-party OPNsense repositories. The project currently
chooses operational simplicity over maintaining an additional private signing
key and key-distribution lifecycle.

Consequences:
- the repository configuration must explicitly contain
  `signature_type: "none"`;
- no `pubkey` or `fingerprints` path is required;
- pkg does not independently authenticate repository metadata;
- HTTPS protects transport but does not provide an independent pkg signing
  boundary;
- a future move to `pubkey` or `fingerprints` requires a new recorded
  architecture decision and migration plan;
- absence of repository signing is no longer a stable-release blocker.

Affected documents:
repository/zapret2-restyle.conf
README.md
docs/AUDIT.md
docs/CHANGELOG.md
docs/DECISIONS.md
docs/DEVLOG.md
docs/PROJECT_STATE.md
docs/REQUIREMENTS.md
docs/ROADMAP.md

==================================================
2026-07-29 — STATIC PKG REPOSITORY USES ORDINARY HTTPS
==================================================

Status:
Approved

Decision:
The GitHub Pages pkg repository configuration must use ordinary
`https://`.

Reason:
`pkg+https://` enables SRV mirror handling and fails for this static
GitHub Pages repository.

Consequences:
- `repository/zapret2-restyle.conf` uses ordinary HTTPS.
- `signature_type: "none"` remains unchanged.
- The correction is published as v0.2.1.
- The immutable v0.2.0 release is not modified.


## DEC-2026-07-30 — Package lifecycle owns runtime installation and removal

Status: Approved and implemented.

Decision:

- `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` is an internal package
  lifecycle backend. No supported installation flow asks the user to run it manually.
- Runtime installation is initiated by `+POST_INSTALL`, not by first Start or Apply.
- Runtime removal is initiated automatically during package deinstallation and removes
  all downloaded/compiled runtime content and plugin-owned state.
- Dependencies installed by the backend are recorded and are removed only when pkg
  confirms they are not required by another package.
- Install and uninstall workers run outside the pkg script process tree and wait for the
  outer pkg transaction before changing the package database.
- Upgrade deinstall hooks preserve runtime and managed dependency state.

Reason:

A package shown as installed must have a deterministic automatic bootstrap, while a
removed package must not leave an unmanaged engine installation behind. Service start
must remain a runtime operation and must not perform package management or compilation.

Consequences:

- `+POST_INSTALL`, `+PRE_DEINSTALL`, `+POST_DEINSTALL`, `setup.sh`,
  `setup_launcher.sh`, configd actions, and service runtime checks form one lifecycle.
- Future GUI maintenance functions must reuse this backend rather than create a second
  engine-management implementation.
- Upstream/Lua/BLOB version control and GUI reporting remain deferred roadmap work.

Affected documents:

- ARCHITECTURE.md
- REQUIREMENTS.md
- DEVELOPMENT_GUIDE.md
- PROJECT_STATE.md
- DEVLOG.md
- ROADMAP.md
- README.md
- CHANGELOG.md


==================================================
DECISION — SEPARATE PLUGIN PKG LIFECYCLE FROM RUNTIME SETUP
==================================================

Date:
2026-07-30

Status:
Approved.

Decision:

- Package installation registers the OPNsense plugin and renders its templates only.
- `+POST_INSTALL` must not download sources, install FreeBSD packages, or compile zapret2.
- After package installation, the user is shown this explicit one-time command:

  `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install`

- A future GUI maintenance action may call the same setup backend.
- `+PRE_DEINSTALL` synchronously stops the service before package files disappear.
- Removing the plugin package preserves the downloaded runtime, plugin configuration,
  and system-wide dependencies. Destructive runtime cleanup is a separate explicit
  maintenance operation, not a package deinstall side effect.
- `+POST_DEINSTALL` must not restart configd.
- Runtime installation uses a fixed upstream release instead of the moving default
  branch. The initial pinned release is bol-van/zapret2 `v1.0.3`.

Reason:

The package transaction must remain short and deterministic. Network access, dependency
installation, source download, and compilation are independent runtime preparation work.
Detached cleanup and configd restart during package removal introduced races and made a
successful pkg transaction an unreliable indicator of runtime state.

Reference review:

The close reference `ugorur/os-zapret2` confirms the useful split between quick pkg
installation and a separate `setup.sh` bootstrap, and the safe practice of stopping the
service in `+PRE_DEINSTALL`. Its `configd restart` in `+POST_DEINSTALL` and moving-branch
runtime update are intentionally not copied.

Consequences:

- Plugin-installed and runtime-ready are distinct states.
- Start and Apply fail clearly until dvtws2 exists.
- Package removal does not delete `/usr/local/etc/zapret2` or shared dependencies.
- Reinstallation may reuse the preserved runtime.
- Runtime version changes require an explicit project change and documentation update.

Affected documents:

- AUDIT.md
- ARCHITECTURE.md
- PROJECT_STATE.md
- DEVLOG.md
- ROADMAP.md
- REQUIREMENTS.md
- README.md
- CHANGELOG.md

==================================================
DEC-2026-07-30 — LIVE-VERIFIED PACKAGE BASELINE AND BLOB NAME CONTRACT
==================================================

Status:
Approved and live verified.

Context:
Package 0.2.1_8 installed successfully, explicit runtime setup built dvtws2 from the
pinned zapret2 release, and the complete runtime reached ready/ok. A startup failure was
then traced to a preset requesting --blob=tls7 while no files/fake/tls7.bin existed.

Decision:

1. The package installation architecture is accepted as working.
2. The active package lifecycle remains:
   - quick pkg installation;
   - explicit setup.sh install;
   - synchronous service stop in +PRE_DEINSTALL;
   - no configd restart in +POST_DEINSTALL;
   - preserved runtime and dependencies on plugin removal.
3. Shorthand --blob=<name> means exactly files/fake/<name>.bin.
4. No implicit historical blob alias table is introduced.
5. Presets must use names corresponding to actual available .bin files.
6. The public README strategy example is intentionally left unchanged until a later
   dedicated rewrite, by explicit project-owner instruction.
7. The tested working tree must be committed with synchronized Engineering Memory so
   the verified package becomes reproducible from Git history.

Reason:

- direct filename mapping is deterministic, inspectable, and easy to validate;
- hidden aliases would add compatibility behavior not approved by the architecture;
- the live evidence proves the package, setup, backend, launcher, firewall, dvtws2,
  and supervisor chain works when the preset references a real blob;
- preserving runtime on plugin removal avoids destructive behavior and matches the
  approved separation between plugin package and runtime installation.

Consequences:

- missing shorthand blob files remain hard validation/startup errors;
- preset maintenance owns the choice of valid blob filenames;
- documentation and comments must not imply that tls7 is a built-in alias;
- remaining work is lifecycle/API live verification, not installation redesign.

Affected documents:

- PROJECT_STATE.md
- AUDIT.md
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md
- ARCHITECTURE.md
- DEVLOG.md
- ROADMAP.md
- REQUIREMENTS.md
- CHANGELOG.md


==================================================
DEC-2026-07-30 — GIT-FIRST UNIFIED PATCH WORKFLOW
==================================================

Status:
Superseded on 2026-07-31 by
DEC-2026-07-31 — GITHUB COMMIT IS THE DEFAULT DEVELOPMENT BASELINE.
Unified patches remain an optional delivery method when explicitly requested.

Decision:

1. Changes to files tracked by the project repository are delivered as reviewable
   unified Git patches.
2. The standard transfer format between the assistant's prepared change and the project
   owner's working tree is a patch accepted by `git apply`; when commit metadata is
   intentionally required, `git format-patch` and `git am` may be used instead.
3. A normal project patch must contain every required content change and every required
   Git file-mode change.
4. The project owner applies the supplied patch through Git, reviews `git diff`, runs the
   documented validation, and commits one logical change.
5. Repository files must not be edited directly in the OPNsense console with editors or
   ad-hoc mutation commands such as `vi`, `ee`, `nano`, `sed -i`, `perl -pi`, Python
   rewrite scripts, `cat >`, or `echo >>`.
6. The assistant must prepare the actual patch artifact instead of substituting a prose
   plan or asking the project owner to reproduce the changes manually.
7. The rule applies only to repository files. Temporary files, logs, diagnostics, build
   output, installed-system configuration, and other files outside the repository remain
   available for normal operational work.

Reason:

Unified Git patches are reproducible, reviewable, reversible, and compatible with the
project's established remote collaboration workflow. Direct console editing risks
unrecorded divergence between the repository, generated package, and installed system.
A patch also permits file-mode corrections, including executable-bit changes, to remain
part of the same auditable logical change.

Consequences:

- `git apply --check` is the mandatory preflight for supplied unified patches.
- `git apply` is the normal application command after successful preflight.
- `git diff --check` and full diff review follow application.
- Direct repository-file editing instructions are not part of the normal workflow.
- `git format-patch` is optional rather than required for every change.
- The executable mode of `scripts/verify-release-package.sh` is corrected to 100755.

Affected documents:

- PROJECT_STATE.md
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md
- DEVLOG.md

==================================================
DEC-2026-07-30 — PATCHES USE THE SUPPLIED WORKING-TREE ARCHIVE
==================================================

Status:
Superseded on 2026-07-31 by
DEC-2026-07-31 — GITHUB COMMIT IS THE DEFAULT DEVELOPMENT BASELINE.
An archive remains an exceptional transfer method for relevant unpublished local
state, not a prerequisite for normal repository work.

Decision:
Multi-file patches are prepared only against the project owner's actual working
tree archive. The archive is supplied after the proposed change has been fully
agreed. Its standard name is
`os-zapret2-restyle-<short_commit_sha>.tar.gz`.

GitHub, model memory, chat fragments, and standalone diffs may provide context,
but they must not be used to reconstruct the patch baseline. A patch is ready
only after `git apply --check` succeeds against an unchanged copy of the supplied
archive. After the patch is committed, that archive is obsolete and a new
archive from the resulting commit becomes the next baseline.

Reason:
Patch context and file modes must match the project owner's real uncommitted or
committed working tree. Reconstruction creates incomplete patches and application
failures.

Consequences:
- request an archive only after changes are agreed and patch preparation begins;
- do not force an incompatible patch into the tree;
- do not reconstruct a multi-file baseline from GitHub or memory;
- use one archive for one subsequent logical patch;
- verify every delivered patch with `git apply --check` against that archive.

Affected documents:
- INDEX.md
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md
- GITHUB_WORKFLOW.md
- PROJECT_STATE.md
- DEVLOG.md

==================================================
DEC-2026-07-30 — CLOSE MILESTONE 7 AND OPEN GUI MAINTENANCE
==================================================

Status:
Approved.

Decision:
Milestone 7 is closed by explicit project-owner decision. Remaining lifecycle, reboot, controlled-failure, timeout-chain, and GUI/API live tests are not marked as passed; they remain a focused regression backlog. Milestone 8 starts with GUI management of published stable bol-van/zapret2 releases through the existing `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` backend. The required user-visible functions are installed-version reporting, available-release listing, update notification, release selection, installation, update, and repeat installation. Runtime presence and runtime/service health are separate reported states.

The second ordered task is GUI management of an additional BLOB repository. Its URL and technical contract will be supplied later by the project owner and must not be invented.

Reason:
The verified v0.2.2 baseline is sufficient to move development to the approved maintenance functionality, while preserving unperformed evidence work honestly. Reusing setup.sh preserves one installation backend and avoids divergent lifecycle implementations.

Consequences:
- ROADMAP.md moves to Milestone 8;
- remaining Milestone 7 tests stay recorded as regression backlog;
- setup.sh remains the single backend for engine release operations;
- no BLOB repository design is approved until the owner supplies it;
- affected implementation decisions require focused verification and synchronized documentation.

Affected documents:
- PROJECT_STATE.md
- ROADMAP.md
- AUDIT.md
- DEVLOG.md
- CHANGELOG.md
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md

==================================================
DEC-2026-07-30 — OPNSENSE CONSOLE INSTRUCTIONS TARGET CSH
==================================================

Status:
Approved.

Decision:
All OPNsense console command instructions target the default root csh shell unless a POSIX shell is explicitly required. A POSIX block must explicitly begin with `sh` and explicitly end with `exit`. Commands after `exit` again target csh. Normal Git verification is `git status --short`, `git diff --check`, and `git diff --stat`; full `git diff` is reserved for targeted debugging or review when specifically needed.

Reason:
Implicit shell changes cause prompt confusion, syntax errors, and commands that do not match the actual OPNsense root environment.

Consequences:
All future command blocks and documentation examples must follow this convention.

Affected documents:
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md
- DEVLOG.md
- PROJECT_STATE.md

==================================================
DEC-2026-07-31 — GITHUB COMMIT IS THE DEFAULT DEVELOPMENT BASELINE
==================================================

Status:
Active. The default PR/merge authorization is extended by
DEC-2026-07-31 — STANDING AUTHORIZATION FOR ORDINARY PATCH DELIVERY.

Decision:

1. The authoritative baseline for normal development is an exact commit in the
   official GitHub repository, normally the current `main` commit.
2. Before changing files, read the current `main`, record its full SHA, and derive
   all content and Git file modes from that commit.
3. The project owner does not need to supply a working-tree archive for state that
   is already committed and pushed to GitHub.
4. GitHub cannot expose uncommitted or unpushed changes in the owner's OPNsense
   checkout. If such state is relevant, it must first be committed and pushed or
   transferred explicitly as an archive or patch. It must never be guessed.
5. One logical change, including all affected documentation and file-mode changes,
   is represented by one atomic multi-file commit.
6. Direct publication to `main` is permitted only after explicit project-owner
   instruction. Immediately before moving `main`, verify that it still points to
   the recorded base SHA. The update must be fast-forward; force-push is prohibited.
7. A working branch, pull request, or unified patch is optional. Use one when the
   project owner requests it or when live validation must occur before `main`
   changes.
8. No particular GitHub client is mandatory. GitHub CLI is not a prerequisite;
   an authenticated GitHub integration/API or ordinary Git may be used according
   to the available environment.
9. Backups of live OPNsense configuration and runtime files are a separate
   operational safeguard and are not replaced by the GitHub source baseline.
10. The normal engineering cycle remains:
    one logical change → one atomic commit → one build → one focused verification.

Reason:

The connected GitHub repository now provides the complete committed source tree,
file modes, history, and exact commit identity. Requiring the owner to create and
transfer a new archive for every change duplicates the same committed state and
slows development. An exact GitHub SHA is reproducible and sufficient while the
owner's checkout is clean and synchronized. The exceptional path remains necessary
because unpublished local state cannot be observed remotely.

Consequences:

- normal work begins from a recorded GitHub SHA rather than a supplied archive;
- remote `main` is rechecked before publication to prevent overwriting concurrent
  work;
- direct `main` publication is never inferred from a general request to analyse or
  prepare changes;
- atomic Git tree/commit operations may publish multi-file changes without a
  sequence of partial per-file commits;
- branch/PR and patch workflows remain available without being mandatory;
- historical patch/archive records remain in DECISIONS.md, DEVLOG.md, and released
  CHANGELOG sections as history;
- current workflow documents must no longer require a fresh archive or `gh`.

Affected documents:

- INDEX.md
- PROJECT_STATE.md
- DECISIONS.md
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md
- DEVLOG.md
- GITHUB_WORKFLOW.md
- CHANGELOG.md
- README.md

==================================================
DEC-2026-07-31 — STANDING AUTHORIZATION FOR ORDINARY PATCH DELIVERY
==================================================

Status:
Active.

Decision:

1. A project-owner request to fix, add, change, implement, or otherwise complete
   an ordinary development task includes standing authority for its normal
   repository delivery cycle unless the request defines a narrower stopping point.
2. The default cycle is a working branch from the recorded `main` SHA, one atomic
   commit, Draft PR, required CI, Ready transition, squash merge, verification of
   the resulting `main`, and cleanup of the temporary branch created for that task.
   No separate confirmation is required for those steps.
3. The assistant may choose the branch name, commit message, PR title and body,
   focused tests, and ordinary CI retry or same-scope correction needed to complete
   the approved task. Any correction remains limited to the same logical scope;
   unrelated work requires a separate change. Before branch publication, amend the
   local commit when needed. After publication, add a same-scope correction commit
   instead of rewriting the branch; squash merge still produces one `main` commit.
4. A request that explicitly says analyse, diagnose, review, prepare only, create a
   patch only, publish to a branch only, or open a PR only stops at that boundary.
   The explicit current instruction always overrides the default cycle.
5. The assistant must not ask again about settled identities, recorded architecture,
   required documentation synchronization, package-revision handling, branch naming,
   commit wording, PR wording, CI waiting, Ready transition, squash merge, or cleanup
   of its own merged temporary branch when the documentation and current source make
   the answer deterministic.
6. Package-revision handling is routine and does not require a separate question:
   an ordinary change that affects packaged files or package behavior increments
   `PLUGIN_REVISION` once when `VERSION` is unchanged; an explicitly requested new
   project version resets `PLUGIN_REVISION` to `1`; a governance/documentation-only
   change outside package contents changes neither value. The standard CI package
   job and validation are the build/verification stage for the documentation-only
   change; no separate release build or publication is implied.
7. One explicit project-owner request to make a release authorizes the complete
   release cycle for that requested version: release preparation, release PR and
   merge, verified tag creation, GitHub Release publication, GitHub Pages/pkg
   repository publication, asset publication, and post-publication verification.
   Do not request separate approval at every release stage. A development request
   that does not explicitly request a release grants none of this release authority.
8. Stop and request direction only when at least one of these boundaries is reached:
   - materially different product or architecture choices remain unresolved by the
     current instruction and project documentation;
   - relevant uncommitted or unpushed owner state may be overwritten;
   - required CI, build, or verification fails and cannot be corrected safely inside
     the same logical scope;
   - credentials, protected-environment approval, or new external authority is
     required;
   - a destructive operation affects user data or a pre-existing owner branch, tag,
     release, published package, or repository history;
   - force-push, history rewriting, or direct publication to `main` is proposed;
   - exact live OPNsense evidence that only the owner can obtain is a mandatory gate.
9. Direct push to `main`, force-push, and history rewriting are never the default.
   Ordinary development reaches `main` through the verified PR merge path.
10. When a stop boundary genuinely requires owner input, ask one consolidated
    question containing the relevant evidence and a recommended choice. Do not ask
    the owner to confirm information that can be obtained from the current repository,
    GitHub, CI, project documentation, or available read-only diagnostics.

Reason:

The CFG-001 cycle showed that repeated questions about publication, PR readiness,
and merge added latency after the change and its tests were already complete. A
stable default path preserves review, CI, atomicity, and branch protection while
removing confirmations whose answers are already determined by the approved task
and repository rules.

Consequences:

- ordinary requested patches can move from implementation through verified merge
  without a second authorization round;
- analysis-only and deliberately limited delivery requests remain non-mutating past
  their stated boundary;
- release authority is granted once by an explicit release request rather than by
  repeated stage confirmations;
- destructive, ambiguous, permission-expanding, and unpublished-local-state cases
  still stop for owner direction;
- the PR is the normal main-protection boundary, so direct pushes are unnecessary;
- failed verification is never hidden or treated as success.

Affected documents:

- PROJECT_STATE.md
- DECISIONS.md
- WORKING_CONVENTIONS.md
- DEVELOPMENT_GUIDE.md
- GITHUB_WORKFLOW.md
- DEVLOG.md
- CHANGELOG.md

==================================================
DEC-2026-07-31 — RELEASE CFG-001 AS PRERELEASE v0.2.3
==================================================

Status:
Active.

Decision:

Publish the CFG-001 configuration-activation correction as prerelease v0.2.3 with
PLUGIN_REVISION reset to 1 and package name os-zapret2-restyle-0.2.3_1.pkg. Keep
v0.2.2 and its package immutable. Do not classify v0.2.3 as a verified stable
baseline until invalid Apply, valid Apply, and reboot behavior are confirmed on the
supported OPNsense system.

Reason:

The existing v0.2.2 tag and Release already identify the verified 0.2.2_1 baseline.
A new unique SemVer tag is required to publish a new package through the tag-driven
release workflow. Publishing a prerelease makes the corrected package available for
the exact live verification that remains open without rewriting an earlier release or
claiming unperformed evidence.

Consequences:

- VERSION becomes 0.2.3;
- PLUGIN_REVISION becomes 1;
- the expected tag is v0.2.3;
- GitHub Actions builds and publishes package 0.2.3_1 and the matching pkg repository;
- v0.2.2 / 0.2.2_1 remains the last verified release baseline until focused live
  evidence is recorded;
- CFG-001 remains open after publication and closes only after its acceptance matrix
  passes on OPNsense.

Affected documents:

- VERSION
- Makefile
- README.md
- docs/PROJECT_STATE.md
- docs/AUDIT.md
- docs/DECISIONS.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/REQUIREMENTS.md
- docs/CHANGELOG.md
- docs/SECURITY.md

==================================================
DEC-2026-08-01 — CLOSE LIFECYCLE LOCK FD IN LONG-LIVED CHILDREN
==================================================

Status:
Active.

Decision:

Keep descriptor 9 as the lifecycle lock descriptor owned by the short-lived
`zapret_service.sh` operation, but explicitly close it on both long-lived
`daemon(8)` launch commands before starting dvtws2 or the supervisor. Cover both
launch sites with a focused regression test. Publish the correction through the
next immutable prerelease v0.2.4 with package revision 1.

Reason:

Live OPNsense evidence from 0.2.3_1 showed descriptor 9 inherited by both daemon
wrappers, the supervisor, dvtws2, and supervisor sleep. The owning shell could exit,
but those children retained the same open file description and therefore the lock.
Every later GUI Apply waited 30 seconds and returned status 75 although no competing
lifecycle operation existed. The immutable v0.2.3 tag cannot publish a corrected
package, so the tag-driven release requires a new SemVer tag.

Consequences:

- the lifecycle shell retains serialization until its operation completes;
- long-lived runtime processes cannot extend lock ownership past that operation;
- later Apply, start, stop, restart, and reconfigure may acquire the mutex normally;
- VERSION becomes 0.2.4 and PLUGIN_REVISION remains/reset to 1;
- expected package is os-zapret2-restyle-0.2.4_1.pkg;
- LIFE-009 and CFG-001 remain open until focused OPNsense verification passes.

Affected documents:

- VERSION
- README.md
- docs/ARCHITECTURE.md
- docs/AUDIT.md
- docs/DECISIONS.md
- docs/PROJECT_STATE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — DISCOVER PUBLICATION TRANSPORTS BEFORE ESCALATION
==================================================

Status:
Active.

Decision:

For every authorized repository publication, discover the capabilities available
in the current environment and select the first safe authenticated path: GitHub
integration/API, ordinary Git remote, then GitHub CLI. A missing executable or one
unavailable client is not a blocker while another approved path can perform the
operation. Do not ask the project owner to select the transport or install an
optional client. Do not report a completed local patch as the end result of an
authorized publication cycle.

An ordinary publication is complete only after task branch publication, one atomic
commit, Draft PR, required CI, Ready transition, squash merge, and verification of
the resulting `main`. Release tag, assets, package, and pkg repository remain under
the separate explicit release-authority rule.

Reason:

The documentation already stated that GitHub CLI was optional, but did not contain
an explicit capability-discovery and fallback procedure. As a result, an available
authenticated GitHub integration was overlooked and missing `gh` was incorrectly
reported as a publication blocker after local preparation.

Consequences:

- publication transport is an internal implementation detail;
- lack of `gh` alone cannot stop authorized work;
- all available approved transports must be checked before escalation;
- truthful reporting distinguishes local preparation, CI package artifacts, merged
  source publication, and an explicitly authorized release publication.

Affected documents:

- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/GITHUB_WORKFLOW.md
- docs/PROJECT_STATE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — ENFORCE DOCUMENTATION AND CSH RESPONSE PREFLIGHT
==================================================

Status:
Active.

Decision:

Treat mandatory documentation recovery as a blocking response preflight. In every
new or resumed project context, complete the INDEX.md reading sequence before
project diagnosis, commands, repository mutation, or publication. A platform-required
progress notice may only announce that recovery is in progress.

Before sending OPNsense commands, perform a second blocking check against the default
root csh dialect. POSIX-only constructs require an explicit `sh` entry and `exit`
return. The release procedure must preserve authorization for the named release across
transport fallback and provide one static csh-safe tag trigger if all available model
environments lack tag-write credentials.

Reason:

The csh and documentation-first rules were already recorded, but a release command
was still produced from chat context with POSIX `$(...)` syntax. The release workflow
also described transport selection without an explicit tag-creation runbook or a rule
that existing authorization survives a transport retry. Converting both rules into
named preflight gates and a deterministic runbook removes those execution ambiguities.

Consequences:

- no substantive project response precedes complete documentation recovery;
- every OPNsense command block is checked for shell dialect before delivery;
- one approval for a named release is not requested again after a transport failure;
- ordinary patches remain fully publishable through GitHub App/API without `gh`;
- a genuine missing tag-write credential is reported once as a capability boundary,
  with one csh-safe trigger action rather than a repeated approval question;
- governance-only documentation changes do not alter VERSION or PLUGIN_REVISION.

Affected documents:

- docs/INDEX.md
- docs/PROJECT_STATE.md
- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/GITHUB_WORKFLOW.md
- docs/DEVLOG.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — ROOT AGENTS PREFLIGHT EXPOSES THE ENGINEERING METHOD
==================================================

Status:
Active.

Decision:

Add a repository-root `AGENTS.md` whose first and blocking instruction is to read
`docs/INDEX.md` and the complete mandatory Engineering Memory sequence before any
substantive project response or action. Explicitly identify DECISIONS.md,
WORKING_CONVENTIONS.md, and DEVELOPMENT_GUIDE.md as the approved methodology and
principles that must be understood before choosing an implementation, command, or
publication path.

`AGENTS.md` is an enforcement entry point, not a second source of project truth. The
specialist documents remain authoritative and must contain the full rules.

Reason:

The documentation-first and root-csh rules already existed, but they were bypassed
when work resumed from chat context. A root agent instruction is discovered earlier
by repository-aware coding agents and turns the documentation entry point into a
workspace-level gate without duplicating the complete Engineering Memory.

Consequences:

- repository-aware agents encounter the preflight before normal project work;
- summaries, memory, and chat context cannot substitute for complete reading;
- the methodology and settled principles are read before implementation details;
- INDEX.md remains the first Engineering Memory document and owns the reading order;
- governance-only enforcement changes do not alter VERSION or PLUGIN_REVISION.

Affected documents:

- AGENTS.md
- README.md
- docs/INDEX.md
- docs/PROJECT_STATE.md
- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — RELEASE MERGE CREATES AND DISPATCHES ITS TAG
==================================================

Status:
Active.

Decision:

The normal authorized release path no longer requires an owner-side tag push. A
release-preparation squash merge to `main` changes VERSION and uses the exact subject
`release: prepare vX.Y.Z` with the optional GitHub `(#PR)` suffix. A dedicated
GitHub Actions workflow validates that contract, creates or verifies the immutable
annotated tag at the merge commit, and explicitly dispatches the existing Release
workflow at that tag.

The Release workflow continues to accept direct `v*` tag pushes for emergency and
compatibility use and additionally accepts `workflow_dispatch`. A tag created with
the workflow GITHUB_TOKEN is followed by explicit dispatch because GitHub suppresses
ordinary recursive workflow events created by that token.

Reason:

Branch, commit, PR, CI, and merge operations were available through the connected
GitHub integration, but tag-ref creation was not. The v0.2.4 release therefore paused
for a manual owner action after release authority had already been granted. Moving the
trigger into repository-owned Actions makes the approved release deterministic and
keeps credentials inside the existing protected publication boundary.

Consequences:

- one release approval remains sufficient for the normal full release cycle;
- the release-preparation PR title/squash subject is a validated protocol field;
- only merges that change VERSION and match the canonical subject can create a tag;
- an existing tag is never moved and must already resolve to the merge commit;
- an existing release or active Release run makes a trigger retry a no-op;
- manual tag push remains a fallback rather than a normal instruction;
- VERSION and PLUGIN_REVISION do not change for this release-infrastructure patch.

Affected documents:

- .github/workflows/ci.yml
- .github/workflows/release.yml
- .github/workflows/release-trigger.yml
- scripts/test-release-trigger.sh
- docs/AUDIT.md
- docs/ARCHITECTURE.md
- docs/DECISIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/DEVLOG.md
- docs/GITHUB_WORKFLOW.md
- docs/PROJECT_STATE.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — UPDATES ACTIVATE REPLACEMENT PLUGIN AND RUNTIME CODE
==================================================

Status:
Active.

Decision:

During a pkg upgrade, the replacement package's +PRE_INSTALL runs first, records
whether the installed service is fully running, stops it synchronously, and verifies
the canonical stopped state. This makes the correction effective even when the old
package's +PRE_DEINSTALL is defective. +PRE_DEINSTALL retains the same fail-closed
stop contract for removal and later upgrades. Any stop failure aborts pkg. The new
+POST_INSTALL starts and verifies the service with replacement code only when it was
fully running before the upgrade. A service that was stopped remains stopped;
incomplete runtime state is cleaned but is not automatically promoted to running.

After setup.sh install successfully builds and verifies dvtws2, it invokes the normal
service restart lifecycle and requires the exact configd `OK` response before setup
status becomes ready. If the saved configuration disables the service, that lifecycle
refresh leaves it stopped by configuration.

Transactional build/staging and rollback of the complete upstream runtime are not
part of this change and remain a separate logical improvement.

Reason:

Live upgrade to 0.2.4_1 produced replacement files with old dvtws2 and supervisor
processes still active because stop failure was suppressed and post-install did not
restore service state. setup.sh likewise could replace the binary without activating
it. Successful installation/update must make replacement code effective, while a
failed stop must prevent a mixed old-process/new-file state.

Consequences:

- new +PRE_INSTALL is embedded in the package manifest and owns the earliest upgrade stop;
- PKG_UPGRADE and a transient /var/run marker transfer only the prior running state;
- package stop failure is no longer hidden;
- post-upgrade start failure is visible and the restart marker is retained for retry;
- package removal retains its stop-only, runtime-preserving behavior;
- setup.lock and lifecycle lock remain separate serialization boundaries;
- PLUGIN_REVISION increments from 1 to 2 while VERSION remains 0.2.4;
- live running/stopped/failed-stop/setup verification is required.

Affected documents:

- Makefile
- pkg/+PRE_INSTALL
- pkg/+PRE_DEINSTALL
- pkg/+POST_INSTALL
- scripts/build-pkg.sh
- scripts/test-package-lifecycle-restart.sh
- src/opnsense/scripts/OPNsense/Zapret/setup.sh
- .github/workflows/ci.yml
- docs/PROJECT_STATE.md
- docs/AUDIT.md
- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/ARCHITECTURE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/REQUIREMENTS.md
- docs/CHANGELOG.md
- README.md

==================================================
DEC-2026-08-01 — RELEASE LIFE-014 AS PRERELEASE v0.2.5
==================================================

Status:
Active.

Decision:

Publish the LIFE-014 package/runtime activation correction as immutable prerelease
v0.2.5 with PLUGIN_REVISION reset to 1 and package name
os-zapret2-restyle-0.2.5_1.pkg. Keep v0.2.4 and package 0.2.4_1 immutable. Do not
classify v0.2.5 as a verified stable baseline until the running, stopped,
failed-stop, setup-driven refresh, and reboot checks are recorded on OPNsense.

Reason:

The existing v0.2.4 tag identifies the already published descriptor-fix tree and
cannot publish the later LIFE-014 source. A new SemVer tag is required to build and
publish the corrected package through the automated release trigger while retaining
honest separation between publication evidence and live lifecycle verification.

Consequences:

- VERSION becomes 0.2.5;
- PLUGIN_REVISION resets from 2 to 1;
- expected tag is v0.2.5;
- expected package is os-zapret2-restyle-0.2.5_1.pkg;
- the release-preparation squash subject is `release: prepare v0.2.5`;
- v0.2.4 / 0.2.4_1 remains immutable;
- LIFE-014 remains open until its live acceptance matrix passes.

Affected documents:

- VERSION
- Makefile
- README.md
- docs/PROJECT_STATE.md
- docs/AUDIT.md
- docs/DECISIONS.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — RUNTIME SETUP PRESERVES COMPLETE SERVICE STATE
==================================================

Status:
Active.

Decision:

Before setup.sh install changes the runtime tree, it must classify the service as
completely running or completely stopped through the canonical service status. After
building and verifying dvtws2, setup restarts through configd and verifies running
state only when the service was initially running. An initially stopped service is
not restarted and must still report the canonical stopped state before setup records
ready. Incomplete or unknown initial state fails closed before runtime mutation.

Reason:

Live package 0.2.5_1 verification showed that unconditional configctl restart correctly
activated a rebuilt runtime for a running service but also started a service that was
explicitly stopped before setup. Runtime installation is not an operator request to
change service state.

Consequences:

- running setup continues to activate and verify the replacement binary;
- stopped setup updates runtime files without starting dvtws2 or supervisor;
- setup never reports ready unless the final state matches the initial complete state;
- transactional staging and rollback of the upstream runtime remain separate work;
- VERSION remains 0.2.5 and PLUGIN_REVISION increments from 1 to 2.

Affected documents:

- Makefile
- src/opnsense/scripts/OPNsense/Zapret/setup.sh
- scripts/test-package-lifecycle-restart.sh
- README.md
- docs/PROJECT_STATE.md
- docs/AUDIT.md
- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/ARCHITECTURE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/REQUIREMENTS.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-02 — GUI REUSES SETUP.SH FOR UPSTREAM RELEASE MANAGEMENT
==================================================

Status:
Active.

Decision:

Add a native collapsible `Zapret2 Service` section to the Settings page. The section
displays canonical service health, installed upstream release tag, existing Start/Stop
control, the four stable releases returned by `setup.sh show`, and an Apply action for
the selected release. All controls remain on one horizontal line at normal desktop
width and may wrap only for narrow responsive layouts.

Release installation, repeat installation, upgrade, and downgrade must continue through
`setup.sh install VERSION`. ServiceController may validate and authorize the selected
tag but must not reproduce GitHub release discovery, checkout, build, dependency, or
service-state logic. The long-running setup process is launched outside configd and the
GUI polls a read-only status adapter. setup.sh itself is not changed by this GUI work.

Use OPNsense standard controls and gettext labels. English is the default. The two
plugin-specific labels that are not guaranteed to exist in the OPNsense language
catalogue provide a Russian form selected from the active OPNsense document language;
the plugin does not add its own language selector or alter OPNsense language settings.

Reason:

The command-line backend already implements the approved latest/four-release discovery,
strict published-tag validation, build path, and complete service-state preservation.
Reusing it keeps one authoritative runtime-management implementation and makes the
approved functionality accessible without SSH. Asynchronous launch prevents a long
build from occupying a normal web request while preserving visible progress and error
state.

Consequences:

- ServiceController gains read-only release/runtime endpoints and a selected-release
  install endpoint;
- setup_launcher.sh accepts `install VERSION` and provides read-only status output;
- configd registers release-list and setup-status actions;
- the existing base service Start/Stop endpoints remain authoritative;
- no release is installed unless it is both syntactically valid and still present in
  the current four-release setup.sh output;
- installed version and service health remain separate displayed values;
- focused CI coverage and one package revision increment are required;
- live OPNsense rendering and install/reinstall/upgrade/downgrade verification remain
  required before this package candidate becomes a verified baseline.

Affected documents:

- Makefile
- src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php
- src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt
- src/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh
- src/opnsense/service/conf/actions.d/actions_zapret.conf
- scripts/test-gui-runtime-management.sh
- .github/workflows/ci.yml
- docs/PROJECT_STATE.md
- docs/DECISIONS.md
- docs/ARCHITECTURE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/REQUIREMENTS.md
- docs/CHANGELOG.md

==================================================
DECISION — REPOSITORY ARTIFACT AND AUTHORITY HYGIENE
==================================================

Accepted on 2026-08-05. Tracked backup/merge/patch/transport artifacts are forbidden,
historical records that can be mistaken for current behavior require explicit status
banners, CI enforces the contract, and remote steady state is `main` plus preserved
`recovery/base`. Full rationale: `docs/decisions/DEC-2026-08-05-repository-artifact-hygiene.md`.

==================================================
2026-08-08 — ADAPTIVE NATIVE-ZAPRET2 STRATEGY LAB SEARCH
==================================================

Decision:

Replace the original family-first/accepted-family-only Strategy Lab search target with an
adaptive native-Zapret2 search architecture owned by Python. Stage-50 results become
ranking evidence rather than a hard Stage-60 allowlist. Introduce an explicit
`CandidateSpec`, job-scoped installed `ResourceInventory`, four BLOB resource classes,
candidate-defined optional output ranges, a golden native-Zapret2 reachability corpus,
fixed search-epoch endpoint comparison, two-level discovery/final validation, fail-fast
3/3 stability and a normal two-to-three-winner early stop.

Keep the main search budget on IPv4/TCP/TLS. IPv6 remains capability-gated and lower
priority. QUIC keeps only the existing fixed IPv4 UDP/443 capability/precheck; do not
expand a QUIC bypass-strategy search branch.

Do not decide the temporary dvtws2 execution model from theory. Compare cold Model A,
multiple warm-worker Model B and compatible warm-bucket/dispatcher Model C on OPNsense.
Controlled source-port dispatch, common Lua preload, lazy buckets and true parallel
candidate probing remain hypotheses until measured. Any warm discovery winner remains
cold-reference verifiable.

Reopen all timeout constants for telemetry-driven review and require
`operation <= candidate <= stage <= job` containment.

Reason:

The Python migration preserved deliberate first-generation simplifications that can hide
working native Zapret2 combinations and repeat process/resource startup for every
candidate. Current Zapret2 semantics support BLOB-free/built-in/inline/file-backed Lua
strategies and startup-time resource initialization, while ordered first-match profiles
mean `--new` alone cannot select an arbitrary preloaded candidate. Search reachability and
runtime acceleration therefore need separate, evidence-driven designs.

Consequences:

- old family acceptance cannot permanently eliminate a search branch;
- fixed `--out-range=-d10` is removed from the target architecture;
- external `.bin` resources are optional rather than structurally required;
- classic zapret/nfqws1 strategy syntax is not used as search or translation input;
- upstream Zapret2 `blockcheck2` may inform methodology but is not imported as shell
  orchestration;
- source implementation is split into `_28`–`_33`;
- A/B/C runtime selection is deferred until the dedicated experiment evidence exists;
- current `_27` executable behavior remains unchanged by this documentation-only
  decision.

Affected documents:

- `docs/INDEX.md`
- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/REQUIREMENTS.md`
- `docs/architecture/STRATEGY_LAB.md`
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`
- `docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`
- `docs/devlog/2026-08-08-strategy-lab-adaptive-search-design.md`

Status:
Active design decision; `_28` hard-gate removal is published and owner-tested in
`v0.4.0_2`, while `_29` CandidateSpec/ResourceInventory and active-adapter policy cleanup
are implemented in `0.4.0_3` source and `_30` native graph/golden/resource/range behavior
is implemented in `0.4.0_4`. `_31` live ordering/fixed endpoint epoch/winner bounds/
timing telemetry is implemented in the `0.4.0_5` source candidate. `_32`–`_33` and the
evidence-gated runtime experiments remain pending.

==================================================
2026-08-09 — RISK-BASED LIVE RELEASE GATES
==================================================

Decision:

Keep the 18-row Strategy Lab OPNsense matrix as the canonical live regression inventory,
but select mandatory stable-release rows from current change risk, live-only defects and
lifecycle/restoration safety instead of blocking every release on every pending row.

For `v0.4.0`, owner-tested `v0.3.3_27` Scenario 1 is the mandatory post-migration live
row and is PASS: Stage 40, Stage 50, Stages 60/70 and Stage 90 pass; terminal
`NO_CANDIDATE` is truthful. Rows 2–18 remain pending regression coverage without a false
PASS claim and do not block v0.4.0 solely because they are pending.

Full rationale and supersession:
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Status:
Active.

## 2026-10-22 — zapret2 v1.0.6 review: no plugin changes

**Decision:** The owner upgraded the upstream zapret2 engine to v1.0.6 through the OPNsense GUI and confirmed normal operation. After reviewing `veryquick`, `COVERAGE`, `CURL_PAD`, and `PACE`, no changes to Strategy Lab are justified or approved.

**Reason:** The current single-target laboratory already implements adaptive search and early stopping; the other reviewed features do not address an identified need. Direct tests of `telegram.org` (`149.154.167.99:443`) failed to establish TCP both with and without the service; native `dvtws2` `syndata` modified outgoing SYN packets but did not restore connectivity. The exact external filtering mechanism remains unproven.

**Consequences:** No new requirements or work items; code, GUI, roadmap, version, package, and release plans remain unchanged. **Status: Closed.**

==================================================
2026-10-23 — DEFERRED IDEAS FROM ZAPRET2-FORK REVIEW
==================================================

Decision:
Preserve two upstream-inspired engineering ideas for possible future discussion.
The owner approved recording them, not implementing them:

1. Consider a bounded independent Lua guard timer for temporary Strategy Lab
   dvtws2 instances as a final safeguard against orphan processes if their
   controller crashes. Never apply this timer to the normal managed service;
   avoid truncating valid test budgets. A timer is not a replacement for
   lifecycle ownership, IPFW cleanup, or Stage-90 restoration.
2. Consider a small set of explicit upstream compatibility contract checks
   when qualifying a new bol-van/zapret2 version. Cover only concrete fragile
   assumptions used by this plugin (for example dvtws2 invocation, Lua/BIN
   resource-loading semantics). Prefer behavior checks when feasible and avoid
   duplicating existing CI and tests.

Reason:
Review of zapret-discordyoutube/zapret2-fork identified reusable safety and
maintenance techniques, but its Windows WinDivert implementation is not a
FreeBSD dvtws2 solution. The relevant reference examples are:
- https://github.com/bol-van/zapret2/commit/98757082b856a9fb5345fd2cc4650f83fae0d32c
  (guard timer in blockcheck2, including FreeBSD);
- https://github.com/zapret-discordyoutube/zapret2-fork/blob/main/nfq2/winnative/tests/check_upstream.py
  (checks that critical upstream assumptions remain true).

Consequences:
Both items remain discussion-only ideas, not approved technical requirements,
architecture changes, implementation tasks, or roadmap commitments. Do not
change current Strategy Lab or upstream setup code, add broad test suites,
bump the package revision, or alter the active Additional Resources and
cold-IPFW recovery priorities on this basis. Reevaluate each idea against
current code, existing safeguards, measured risks, and owner approval before
any implementation. GitHub Issue #514 was created in error rather than using
the established Engineering Memory document.

Affected documents:
docs/DECISIONS.md

Status:
Active decision to retain the ideas for future discussion; implementation
not approved.

## 2026-10-23 — Limited Network Inspection Theory

Decision:
Adopt the following concise theoretical framework for future DPI/TSPU research:

**Limited Network Inspection Theory.** A TSPU is not a connection endpoint, but an on-path observer with finite computational resources. It reconstructs IP/TCP/TLS traffic and examines TLS fingerprints and encrypted-flow behavior. Deeper inspection costs more resources; greater simplification increases the risk that the DPI's interpretation diverges from the endpoint's actual connection state. Two conceptual circumvention principles follow: **desynchronization** — DPI and server interpret the same stream differently; **mimicry** — a concealed connection becomes harder to distinguish from permitted traffic. Overload exposes inspection capacity limits, but the outcome depends on failure policy: traffic may be forwarded or blocked. Zapret2's architecture, separating a C packet-processing core from Lua traffic-manipulation logic, provides a framework for investigating these principles.

Reason:
This unifies the TCP/TLS reconstruction limits, TLS fingerprinting, and encrypted-proxy behavior discussed in the Zapret Wiki and the upstream bol-van/zapret2 manual. It is a conceptual model, not proof of any particular TSPU implementation or overload response.

Consequences:
Research and discussion only. No new strategy, test, overload experiment, requirement, implementation task, roadmap commitment, package change, or change to current development priorities is approved by this entry.

Affected documents:
docs/DECISIONS.md

Status:
Active owner-approved theoretical concept; implementation not approved.


## 2026-10-24 — No direct Strategy Lab persistent Apply button

**Decision:** Do not add a Lab-side `Применить стратегию` or `Перенести в настройки` button, with or without a preview, to the current plugin scope. The owner explicitly declined the proposed UX change: «Значит мне показалось. Не будем такое делать.»

**Reason:** The owner was recalling a possible earlier UI field; checked historical `diagnostics.volt` sources at `v0.5.0`, `v0.5.2`, and `v0.5.6_17` and current `_47` provide **Copy profile** and temporary circular validation, not direct persistent Strategy Apply. Existing user-controlled Copy profile → paste in Strategies/Settings → Apply is retained.

**Consequences:** No GUI implementation, API action, automatic strategy rewrite, new milestone, backlog entry, package version bump or release change is authorized. Continue agreed M0–M7 Additional Resources acceptance work. Current source remains unchanged.

**Evidence:** [Owner decision and exact saved Job shortlist provenance](verification/evidence/2026-10-24-v0.5.7_47-shortlist-provenance-owner-live.md).

**Status:** Closed — do not implement.


## 2026-10-24 — Отмена разработки отдельной чистой переустановки плагина

**Решение владельца:** «Следующий инженерный шаг — реализация и изолированные тесты отдельного консольного механизма чистого восстановления - отметь, что делать мы не будем». **Отменить** новую консольную/Web функцию отдельной чистой переустановки повреждённого/несогласованного плагина и её изолированные/натурные испытания. Исключить из обязательных условий M5/M7 и текущей очереди разработки.

**Граница решения:** отмена касается **только нового самостоятельного clean-reinstall механизма**. Остаются обязательными безопасная штатная установка и обновление, транзакционное восстановление ресурсов при сбоях, существующие ограниченные операции recovery upstream, сохранение пользовательских настроек при обычном обновлении, строгий отказ при непроверенном native owner, защита системной конфигурации OPNsense и других плагинов. Не подменять отменённую функцию неявным `pkg add -f`, обходом package hooks или автоматическим удалением plugin-owned данных. Не возобновлять её без нового прямого решения владельца.

**Что осталось в плане:** M2 — подтверждение пригодного снимка VM и консоли; M3 — специальные конфликты и ссылки стратегий на изменённые/удалённые ресурсы; M5 — оставшиеся безопасные отрицательные тесты штатных операций и переключения upstream (существующие source CI уже прошли); M6 — реальная холодная загрузка с проверкой IPFW/ipdivert, службы, Voice, GUI, сохранности настроек и отсутствия временных ресурсов; M7 — окончательная приёмка и отдельно разрешаемый выпуск `v0.5.8` с Web-доставкой. M4 уже принят. Не повторять прошедшие Strategy Lab Job.

**Согласованные документы:** [нормативное ТЗ](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md), [план M0–M7](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md), [матрица приёмки](verification/EXTRA_RESOURCES_ACCEPTANCE.md), [исторический отменённый проект механизма](verification/EXTRA_RESOURCES_CLEAN_REPAIR_GATE.md), [текущая точка продолжения](START_HERE.md).

**Статус:** Решение действует. Разработка и тестирование нового clean-reinstall механизма **ОТМЕНЕНЫ**, не блокируют релиз.


## 2026-10-24 — Завершение прежней приёмки без релиза; кэшируемая справка Lua/BIN

**Решение владельца:** «Все остальные этапы закрываем. Релиз пока не выпускаем». Завершить прежнюю кампанию M0–M6 без новых испытаний. Невыполненные пункты M2 (снимок VM), M3 (особые коллизии и изменённые ссылки), M5 (отдельные отказы), M6 (холодная загрузка/IPFW/Voice) фиксировать как **закрытые по решению владельца, НЕ проверенные**, а не ложный PASS. M4 и реально выполненные испытания сохраняют подтверждённый результат. M7 приостановлено до отдельного разрешения стабильного выпуска. Ранее отменённую самостоятельную чистую переустановку не возобновлять.

**Новая задача:** при включённой штатной «Справке» на странице «Стратегия» сразу под кнопкой «Установить дополнительные ресурсы» показывать две колонки **всех фактически установленных Lua и BIN файлов**. Имена из Git HEAD установленного upstream Zapret2 — зелёным цветом темы OPNsense; остальные — синим. GUI читает **готовый кэш-файл**, обновляемый при изменении установленного набора или upstream, без повторного перечисления при открытии справки. До первой установки дополнительных ресурсов показывать описание действия кнопки. RU/EN и безопасное экранирование имён обязательны; штатные Apply, Start/Stop, настройки и ручная установка ресурсов сохраняются.

**Граница:** дополнительная задача реализуется как новый исходный кандидат 0.5.7_48; CI исходников не равняется испытаниям интерфейса на OPNsense. Стабильный v0.5.8 выпускать нельзя до отдельной команды владельца.

**Документы:** [ТЗ](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md), [приёмка](verification/EXTRA_RESOURCES_ACCEPTANCE.md), [продолжение](START_HERE.md).

**Статус:** утверждено.

## 2026-10-24 — Final H1 acceptance, M6 closure and explicit stable v0.5.8 release authorization

**Owner decision (verbatim):** «Я всё проверил. Всё отлично. Эту задачу по добавлению списка .lua и .bin закрываем. M6 и M7 закрываем если еще не закрыто. Отчёт о приёмке считаем сданным. Выпускаем релиз.»

**Scope:** The published `v0.5.7_48` Strategies Full Help two-column cached Lua/BIN enhancement (H1) is **PASS by owner sign-off**, and the final acceptance report is accepted. **M6 is CLOSED BY OWNER**; this is a process closure/waiver, **not** an assertion that a new cold reboot, postboot IPFW/ipdivert or complete Voice boot regression was actually performed. Historical M2/M3/M5 unrun fault/reference/snapshot cases also remain explicitly unverified. Earlier accepted M4 native Model C BIN/Lua execution, Stage-90 restoration, original Settings/Voice preservation and source negative CI keep their own evidence limits.

**Stable authorization:** This explicit instruction supersedes the former “stable release not authorized / M7 on hold” status. Prepare `VERSION=0.5.8`, `PLUGIN_REVISION=1`, exact source PR and FreeBSD15 build, then publish and verify a full **non-prerelease** GitHub `v0.5.8`, matching `0.5.8_1.pkg`/SHA256SUMS and public `FreeBSD:15:amd64` GitHub Pages repository for OPNsense Web install/update. **M7 publication is not technically PASS until all these independent checks succeed.** A user Web-upgrade click is not inferred from deploy success.

**Out of scope remains out:** no separately implemented console clean-reinstall mechanism, no forced managed-resource deletion, no repeated Strategy Lab jobs or new power-loss tests merely to requalify closed work. Normal update fail-closed/transactional protection and separate source-vs-owner-vs-release evidence remain unchanged.

**Evidence:** [final acceptance and release authorization](verification/evidence/2026-10-24-v0.5.8-owner-acceptance-and-release-authorization.md); [M0–M7 scoreboard](verification/EXTRA_RESOURCES_ACCEPTANCE.md); [stable release preparation](releases/v0.5.8.md).

**Status:** Owner sign-off complete. Stable release publication expressly authorized and in progress.

## 2026-10-26 — Native OPNsense Config persistence for Strategies/Voice; no repeat save during Remove

**Owner decision (verbatim):** «Отличные новости. Утверждаю такой подход. Зафиксируй.»

**Decision:** Keep the existing **native OPNsense Config persistence** as the sole authoritative Strategies/Voice settings writer. Ordinary user-edited Strategies Apply and Voice Apply retain the existing `SharedConfigCommit::persist()` path: validate only explicitly changed OPNsense model leaves, `serializeToConfig(false, true)`, then native `OPNsense\Core\Config::save()` under the existing lock and fresh readback. Never introduce a plugin-specific configuration file, second XML serializer, independent Config writer or duplicated Strategies/Voice field parser.

For **Remove Additional Resources**, keep the entire saved Strategies+Voice Config snapshot unchanged. Reuse `SharedApplyRequest::prepareSavedUnchanged()`, the existing common GUI candidate compiler and `SharedApplyConfigWorker::preflight()/saved()` digest/mode checks with `changed_fields=[]`. Do **not** call `SharedConfigCommit::persist()` or `Config::save()` just to remove Lua/BIN or restart an unchanged runtime; do not manufacture a new Config revision or overwrite user-owned fields. The existing Remove trial's shared Apply phase `config-saved` is a durable *verification of already-persisted unchanged settings*, **not** evidence of a new Config write.

**Reason:** Settings already survive reboot because OPNsense saves the native model. The existing `SharedConfigCommit::persist()` explicitly short-circuits on zero changed fields (`result=unchanged, saved=false`). Re-saving unchanged settings adds revision/backup noise and power-cut/partial-save risk without fixing the independent process, release or IPFW ownership problem.

**Consequences:** The next Remove `config-saved` cold-recovery increment must compare the entire unchanged saved Config digest, zero changed fields, exact prior common owner and the two existing durable journals, and delegate native process/release/IPFW recovery to already-existing common Apply mechanisms. **Never blindly invoke generic `shared_apply_recover_saved_service()` as an old-owner rollback:** its intended behavior can activate the *new* release. Only attestable previous-owner restoration may close the Remove transaction; any mixed/unknown state retains evidence and returns `RESTORE_FAILED`. Preserve Exclude Domains/`--hostlist-exclude`, existing Strategies+Voice semantics and all user settings. GUI Remove remains read-only pending source qualification and separate installed-appliance acceptance. This architectural decision **does not itself implement `config-saved` recovery**, authorize a package/release, or mark owner-live tests PASS.

**Source evidence:** `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php` (`applyAction`), `src/opnsense/scripts/OPNsense/Zapret/apply_settings.php` (`SharedConfigCommit::persist`), `src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php` (`save`/`saved`), `src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php` (`prepareSavedUnchanged`), and `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` (normal vs Remove common Apply).

**Affected documents:** [Remove specification](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md), [Remove implementation plan](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md), [current handoff](START_HERE.md), [current state](PROJECT_STATE.md).

**Status:** Active; approved implementation approach for the next `config-saved` recovery stage, not an installed implementation or acceptance result.


## 2026-10-28 — Direct Telegram voice: evidence-led assessment; separate STUN, media and MTProto

**Owner instruction:** Reassess direct Telegram voice calls in the existing OPNsense plugin, compare a third-party `telegram.lua` and the community `Telegram Direct` UDP/TCP recipes, and record the engineering direction. This is a new, bounded research request after the separately closed 2026-10-20 direct-UDP campaign, not a claim that its negative network result changed.

**Decision:** Evaluate direct one-to-one Telegram call connectivity as an endpoint-specific protocol problem before implementing another default DPI bypass. Retain the single Strategies+Voice `dvtws2` backend, native OPNsense persistence and shared Apply/IPFW ownership. The existing per-service Voice STUN configuration uses `--filter-udp=*` scoped to its destination IPSET, `--filter-l7=stun`, and `--payload=stun`: it selects STUN packets only, not all UDP media. The exact 2026-10-20 campaign observed outbound Telegram UDP with no inbound reflector responses and no `MEDIA_PASS`/`CALL_PASS`; the apparent pfSense positive control depended on VPN routing. Preserve those results and do not repeat the closed fake/TTL/fragmentation matrix without genuinely new evidence.

**Technical assessment:** Treat call signaling (MTProto/TCP), STUN/TURN connectivity, reflector/relay Hello and encrypted UDP media as distinct. Under upstream Zapret2, `mtproto_initial` is a recognized TCP payload; `fakemultisplit.lua` is TCP-only and cannot directly fix UDP calls. An IPSET restricted to Telegram ranges can catch Telegram-addressed relay traffic, but cannot be assumed to cover a dynamically negotiated P2P peer address outside the IPSET. Similarly, `--filter-udp=50000-59999 --payload=all --lua-desync=fake:blob=fake_default_udp:repeats=6` is a community hypothesis, not a measured working call fix; `--payload=all` includes non-STUN payloads and therefore requires strict endpoint, flow/range, and collateral-impact controls before any live trial. A dedicated `--filter-l7=stun --payload=stun` strategy alone cannot prove successful media delivery. Avoid global UDP capture, automatic per-port assumptions, forced QUIC blocking and new parallel runtime owners.

**Third-party source/provenance:** `p1ngroot/zapret2tg_bypass/windows_release/lua/telegram.lua` Git blob SHA-1 `5312b30897fcc579a4dd8329287670e9e22fb4dd` is different from all 19 Git blob SHA-1 values in `Tolian82/zapret2-extra-resources/lua` at catalog main `ccdd8fae375e9d3fcb2592a803e10a10d52c49f2`. The third-party module declares `telegram_bypass`, TLS, MTProto, HTTP, generic and smart functions, but its main `telegram_bypass` immediately rejects non-TCP packets; the UDP MTProto branch is unreachable through that advertised entrypoint. Source repository metadata declares no license (`license=null`) and no license file is present at repository root. Do not interpret unique checksums as proof of license permission or Zapret2 compatibility; importing/redistributing this third-party source needs verified redistribution permission, and runtime integration needs separate static/native tests. No plugin activation is authorized by this research decision.

**Evaluation order:** (1) Observe fresh real calls with P2P disabled (relay baseline) and enabled (peer-address baseline), recording outbound/inbound 5-tuples, IPv4/IPv6, routes, IPFW capture, Zapret2 `l7payload` classification and UDP response, without inspecting call content; (2) establish a stable same-ISP endpoint/control so no-reply is distinguishable from IP blackholing; (3) only if the provider's DPI mechanism remains plausible, run a small native `fake`/flow-scoped STUN versus non-STUN initial-packet comparison on the actual observed destination ports, with rollback and exact ordinary owner restoration; (4) require sustained bidirectional media and a real remote call before claiming success. `STUN observed`, `MEDIA_PASS`, and `CALL_PASS` remain separate evidence classes. Check candidate port-range proposals against actual captured destinations instead of hard-coding 50000–59999 as a protocol fact.

**Reason:** An additional Lua function or successful TCP MTProto session cannot restore a direct UDP path that is blocked by destination address or excludes the dynamically chosen peer. Measurement-first selection avoids another inconclusive sweep and protects unrelated UDP/QUIC traffic.

**Consequences:** Research and source provenance are recorded; existing Voice GUI, Strategies, installed configuration, runtime and stable `v0.6.0_1` are not changed. The old campaign remains historically closed; this new evaluation is open. No working voice strategy, tested Telegram media bypass, authorized Lua redistribution, package candidate or new release is claimed.

**Affected documents:** [ROADMAP.md](ROADMAP.md); existing contracts [Voice GUI](architecture/VOICE_TRANSMISSION_GUI.md) and [Telegram UDP research](research/TELEGRAM_VOICE_UDP.md) remain unchanged and are cited as current and historical technical foundations.

**Status:** Active owner-requested research assessment; implementation and third-party import remain gated by technical evidence and provenance rights.

## 2026-10-28 — Voice: UDP-порты для динамических клиентов и дополнительный IPv6

**Цель:** при сохранении штатных Voice IPSET для Telegram, Discord, X (Twitter), SIP (VoIP), Custom обеспечить второй, дополнительно ограниченный **только UDP-портами** путь к адресам динамических клиентов. Это относится к прямой передаче голоса через наш OPNsense/Zapret2 без VPN, прокси или сторонних обходных служб. Новая концепция утверждена для проектирования и последующей реализации, но ещё не реализована; MEDIA/CALL для неё не проверены.

- **Старое поведение не меняется:** у каждого включённого Voice-сервиса сохраняются его существующий IPv4 IPSET и собственные параметры STUN-профиля. Штатное `--filter-udp=*` в нём означает UDP 1–65535 **только по destination IPSET**, если пользователь сам не указал более узкие порты в параметрах.
- **Новый элемент GUI:** на одной строке с галочкой Telegram / Discord / X (Twitter) / SIP (VoIP) / «Настроенное пользователем» примерно через 1 см от неё надпись `UDP порты` (RU) / `UDP ports` (EN), справа — отдельное поле чисел/диапазонов, индивидуальное для данного сервиса. Значение принадлежит его Telegram/Discord/X/SIP/Custom Parameters и сохраняется штатной моделью OPNsense.
- **Новый общий переключатель:** слева от подписи `IPv6`, под заголовками «Параметры передачи голоса» и «Как работают голосовые профили», показывается отдельная галочка. При OFF дополнительный портовый захват охватывает любые назначения IPv4 (`0.0.0.0/0`); при ON — любые назначения IPv4 и IPv6 (`0.0.0.0/0` + `::/0`). Тумблер общий для пяти профилей и не меняет существующие IPv4 IPSET.
- **Адресные маски остаются внутренней семантикой нового capture:** не разрешать и не требовать вводить `0.0.0.0/0` или `::/0` в голосовые IPSET; хранить в новых полях **только портовые интервалы**, а не CIDR. Пустое дополнительное поле не включает `to any` и не отключает старый IPSET-путь.
- **Запрет коллизий:** до установки галочки включения любого из пяти профилей сравнить его новое непустое множество UDP-портов с полями уже включённых профилей. Любое пересечение отдельных портов или диапазонов (например, `50000-50100` и `50050-50200`) запрещает включение: галочка остаётся OFF и показывается локализованное предупреждение о занятом списке/пересечении. Та же проверка обязательна на backend при Apply/редактировании/восстановлении, чтобы обход проверки UI не активировал конфликт и не повредил прошлое рабочее состояние.
- **Движок:** сохранить одного штатного владельца Config/Apply/IPFW и общий `dvtws2`; реализовать независимые, упорядоченные области (старый IPv4-IPSET wildcard и новый destination-any на выбранных UDP-портах), с эквивалентными действиями профиля, без двойного divert/fake и нарушений first-match. Подтвердить IPv6 divert/IPFW на FreeBSD 15 и точную семантику исходного/целевого UDP-порта для исходящего от SIP-сервера и потоков от удалённых клиентов. Новые поля **не** превращаются в произвольные опции `dvtws2`.
- **Границы эффекта:** у нынешнего Voice-компилятора `--filter-l7=stun`, `--payload=stun`, IPv4-only IPSET; новый capture портов не делает RTP/SIP автоматически распознаваемыми и не обещает звонки. Пример `--filter-udp=50000-50100 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-repeats=6` — идея фильтрации портов, **не готовый синтаксис Zapret2**: для Zapret2 использовать нативные `--lua-desync=...` и подтверждённый набор L7. Port-only к любому IPv4/IPv6 всё ещё может затронуть посторонний UDP на выбранных портах, поэтому нужны ограниченные диапазоны, проверка эффектов и реальный двусторонний MEDIA/CALL.

**Порядок будущего выполнения:** 1) уточнить точный контракт двух областей и порядок first-match; 2) native GUI/RU/EN + Config-модель + валидация пересечений; 3) compiler/IPFW/IPv6 + транзакционное применение; 4) source/CI/FreeBSD15 и установленная OPNsense приёмка, включая OFF/ON, F5, restart, IPv6, перекрывающиеся интервалы и откат; 5) отдельно подтвердить реальные звонки. Новый релиз/пакет и изменение версии этим решением не разрешены. [Спецификация Voice](architecture/VOICE_TRANSMISSION_GUI.md).

**Уточнения принятого контракта:** общая галочка `IPv6` по умолчанию выключена для совместимости со старыми сохранёнными настройками. Поле `UDP порты` принимает числовые порты и диапазоны в пределах 1–65535 (например, `3478,50000-50100`); `*`, CIDR и неверные интервалы не должны создавать глобальный перехват. Нормализованные интервалы сравниваются на пересечение независимо от имени сервиса, выбранной стратегии и общей галочки IPv6, поскольку IPv4-охват остаётся общим. Тексты ошибок: RU «UDP-порты уже используются включённым профилем „{service}“. Пересечение: {ports}. Профиль не включён.»; EN «UDP ports are already used by enabled profile “{service}”. Overlap: {ports}. Profile was not enabled.». Повторная проверка при редактировании уже активного профиля и на авторитетном backend обязательна. Недействительный кандидат не меняет сохранённую конфигурацию или активный runtime.

**Статус и владение:** это утверждённая концепция для будущей реализации, не уже существующий режим. Отдельные нативные профили/правила могут понадобиться для сочетания destination-IPSET и дополнительной port-only области, но вторую независимую службу или владельца Config/Apply/IPFW не создавать. Новая область не подменяет действующие STUN-фильтры распознаванием RTP/SIP. Мотивирующий пример с `--dpi-desync` не является проверенным Zapret2-синтаксисом. Изменение кода, установка пакета, выпуск релиза и живое подтверждение звонков этим решением не заявляются.

## 2026-10-28 — Voice P2P: two capture scopes, shared IPFW rule, and verification ideas

**Status:** Engineering discussion supplement to the owner-approved **“Voice: UDP-порты для динамических клиентов и дополнительный IPv6”** entry above. The two-scope design was positively received by the owner; the implementation details and further research ideas here are **proposals to evaluate, not an assertion that they are implemented or separately approved**. The previous 2026-10-28 Telegram voice evidence assessment and the negative 2026-10-20 direct-UDP campaign remain valid.

### Proposed concrete GUI and behavior

- Preserve each service's existing **destination-IPSET Voice/STUN path** with its existing native `Parameters`, including `--filter-udp=*` when selected. IPSET membership, not a global destination wildcard, limits this path. Do not rewrite existing saved Parameters or interpret `*` as the new P2P port list.
- Add a **second, port-only P2P scope** to each enabled Telegram, Discord, X (Twitter), SIP (VoIP), and Custom service: the new `UDP ports` / `UDP порты` field limits capture by *outbound destination UDP ports*, independently of the remote IP. Internally that is destination-any IPv4; when the shared `IPv6` checkbox is ON, also destination-any IPv6. The user does not enter `0.0.0.0/0` or `::/0` into a Voice IPSET. An empty new field does not activate this additional scope. Reject `*`, CIDR, zero, reversed intervals, and ports outside 1–65535.
- Place the per-service port label/input on the same row as its existing enable checkbox, separated by responsive spacing (approximately 1 cm visually; CSS units, not a fixed physical measurement). Place the one shared `IPv6` checkbox below the two existing Voice headings/help rows. The checkbox defaults OFF for compatibility and affects **only the additional P2P scope**. The planned dual-stack capability of explicit destination-IPSET entries is independent of this checkbox.
- Keep RU/EN labels, field help, errors, disabled drafts, F5 persistence, and the existing native OPNsense Config writer. The proposed `UDP ports` field belongs to the corresponding service, not to a second hidden service or duplicate IPSET. The five editable native `Parameters` fields continue to own the validated STUN Lua behavior.

### Proposed implementation using one engine and one extra firewall rule

- Compile **two distinguishable profile classes per enabled service as needed**: the existing IPSET-scoped profile and a generated P2P profile with the same *approved* STUN/Lua action semantics but a different port and destination selector. Use distinct stable profile identities/fingerprints. Preserve existing IPSET profile behavior when the new P2P ports are empty; do not concatenate an IPSET filter onto the P2P profile, as that would negate support for unknown peer addresses. Generate selectors explicitly rather than blindly copying `--filter-udp=*` into the P2P branch.
- **Prefer one additional, plugin-owned IPFW `divert udp ... to any <aggregate-P2P-ports>` rule**, where the aggregate comprises only the non-overlapping, enabled P2P port intervals. Preserve the existing five destination-IPSET Voice capture rules, existing ordinary Strategies rules, WAN selection, loop guards (`out not diverted not sockarg`), single `dvtws2`, release ownership, locked Apply and rollback. This avoids allocating five extra rules against the current `19000–19010` owner range. Verify the actual FreeBSD 15 IPFW command, family behavior, rule ordering, and rule-number budget before making this the final design; a single rule also gives only aggregate IPFW counters.
- Profile selection is **first-match** and IPFW may divert a packet matching both capture scopes. Prove there is no repeated divert/fake; define deterministic ordering of IPSET and P2P profiles before ordinary Strategies, and verify interactions with ordinary STUN/UDP profiles and non-STUN passthrough. Port-only capture alone does not authorize a Lua modification of unrelated UDP.
- Keep **`Exclude Domains` strictly out of Voice/STUN** and do not resolve it into DNS A/AAAA. The separately planned global **`Exclude IPSet`** applies to both IPSET and P2P profiles at the dvtws2 profile-selection/action boundary. It prevents DPI modification for excluded IPs but **does not eliminate the overhead of initial IPFW divert capture**.
- Maintain one native Python port-interval normalizer for the prepared Voice candidate, including overlap detection and canonical interval representation; reuse its verified interval evidence in the GUI response, compiler, IPFW plan, attestations, and transaction. Duplicate validation in PHP/JavaScript is advisory only, not a competing canonical interpretation. Reject a candidate before Config/runtime/IPFW mutation if a stale tab, invalid interval, or profile collision is found.

### Proposed validation and user experience refinements

- On an attempted ON toggle, compare the proposed nonempty P2P port intervals with already enabled services regardless of L7 label or the shared IPv6 checkbox, because their IPv4 destination-any scopes would overlap. Keep the attempted checkbox OFF and show an RU/EN error naming the other service and the exact intersecting ports. Also validate changes **to an already-enabled port field**, both on Validate and on Apply; a frontend check is not sufficient for direct API requests or two open tabs. An empty new port field does not conflict with another empty field.
- Keep existing IPSET-based scope-conflict checks distinct from the new P2P-port exclusivity policy. In addition, examine intersections of the P2P ports with existing IPSET-scoped Voice and ordinary STUN/UDP selectors; do not silently let an earlier profile shadow a later one. The existing five Voice services may be OFF and saved as drafts without triggering P2P interception.
- Consider permitting a service with a valid, nonempty P2P port scope but **no destination IPSET**, because a direct peer may not belong to a known server network. This would replace the current mandatory-IPSET rule **only when the P2P scope is valid**; empty IPSET **and** empty P2P ports must never imply destination-any. **This extension is a separate proposal requiring explicit owner acceptance and tests**, not part of the already approved baseline.
- After implementing the dual-stack model, ensure IPv6-specific profiles and IPFW capture exist only when the selected interface/path supports the intended traffic, and report absent IPv6 WAN capability truthfully. Do not use the shared IPv6 toggle to disable ordinary IPv6 IPSET targets.
- Show read-only runtime evidence per service: configured P2P port intervals, effective IPv4/IPv6 scope, whether the P2P profile was actually compiled/activated, shared IPFW capture identity, packet counters (clearly scoped), applied profile fingerprint, and capture/processing/response distinctions. Do not equate an enabled checkbox or nonzero IPFW counter with a successful call.

### Further voice/DPI research ideas — not implementation requirements

1. **Observe actual ports before recommending presets.** P2P destination ports may be negotiated or randomized and can differ between STUN checks, relay, signaling and encrypted media. Do not present `50000-50100`, `19294-19344`, or `50000-59999` as universal Telegram/Discord defaults without captured evidence. Verify whether the outbound WAN flow needs destination-port or source-port matching after NAT; account for caller/callee and direct-P2P versus TURN/relay paths.
2. **Separate STUN from the complete call.** The current Voice compiler accepts `--filter-l7=stun` and `--payload=stun` only. A port-only P2P profile reusing this action remains STUN-only: it does not automatically process Telegram reflector Hello, Discord IP discovery, DTLS, RTP/SRTP or other encrypted media. Investigate upstream Zapret2-supported `discord` and corresponding payload classifiers in a separate bounded, version-pinned allowlist before any proposal to expand Voice beyond STUN; do not import zapret1 `--dpi-desync` syntax.
3. **Determine what DPI can actually be influenced.** Compare unmodified and selected native Zapret2 test traffic to the same observed peer/relay endpoints, distinguishing packet-classification blocks from IP blackholing, NAT/ICE failure, IPv6 reachability problems and relay fallback. A successful STUN exchange or MTProto/TCP connection is not evidence of bidirectional voice media. Avoid speculative global UDP/443, broad all-UDP capture, forced QUIC blocking or default fake payloads without per-flow evidence.
4. **Bound performance and collateral impact.** One shared port-only IPFW rule is cheaper to manage, not necessarily cheaper per packet. Verify CPU, packet rate, latency/jitter, packet loss, reinjection, unrelated UDP on the selected ports, and foreign rule ownership on real OPNsense/FreeBSD 15. Prefer fail-closed activation and exact rollback over silently broadening capture when an interval, L3 family or profile is unsupported.
5. **Truthful live acceptance.** Preserve separate `STUN_OBSERVED` / ICE reachability, `MEDIA_PASS`, `CALL_PASS`, and **direct P2P versus TURN/relay** attribution. A pass requires observed inbound responses and sustained two-way media for the relevant case; do not capture or store call content. A server or provider UDP/IP block may remain unsolved by DPI desynchronization.

### Candidate implementation touchpoints (discussion inventory, not a change authorization)

`src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt`; `src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/voice.xml`; `src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml`; `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceSettingsPayload.php`; `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateValidator.php`; `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceApplyCandidate.php`; `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateXml.php`; `src/opnsense/scripts/OPNsense/Zapret/backend/voice_model_export.py`; `src/opnsense/scripts/OPNsense/Zapret/backend/voice_profile_compiler.py`; `src/opnsense/scripts/OPNsense/Zapret/backend/voice_capture_plan.py`; `src/opnsense/scripts/OPNsense/Zapret/backend/voice_traffic_merge.py`; `src/opnsense/scripts/OPNsense/Zapret/backend/voice_ipfw_adapter.py`; `src/opnsense/scripts/OPNsense/Zapret/backend/voice_firewall_transaction.py`; `src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh`; `src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh`; `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`; `docs/architecture/VOICE_TRANSMISSION_GUI.md`. Exact changes and regression test coverage must be established in the future implementation plan, without duplicating existing native Config writers or parsers.

**Consequences:** This note adds engineering rationale, a preferred compact IPFW topology and explicit acceptance risks **without changing the accepted preceding Voice concept, current source, GUI, Config, installed runtime, version, package, release or roadmap priorities**. It does not authorize a new stable release or claim a working direct call. The additional P2P-only-without-IPSET capability, protocol allowlist expansion and per-service observability details remain proposals awaiting owner agreement.

## 2026-10-28 — Final universal IP-list /0 prohibition; Exclude IPSet and IPv6 first priority

**Owner's latest binding decision:** Prioritize the global `Exclude IPSet` and complete IPv4/IPv6 migration now. Preserve all recent Voice UDP-port/P2P GUI and capture discussions for later consideration; **do not implement them in this workstream**. Final prohibition: reject `0.0.0.0/0`, `::/0` and effectively equivalent complete-family unions in **every user-controlled IP inclusion or exclusion list**, explicitly including all five Voice IPSETs. This supersedes any earlier proposal to allow `/0` in Voice. Internal-only analytical wildcard for a hostless profile is not a user IPSET.

**Scope and authority:** [Current binding technical specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md) and [per-file staged plan](architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md) are the first-priority implementation authorities. `Exclude IPSet` is destination-IP based and mandatory for all executable ordinary Strategies and Voice profiles; `Exclude Domains` remains strictly domain-based, never converted through DNS and never injected into Voice/STUN. Keep single native Config/Apply/IPFW/`dvtws2` ownership and existing Voice page layout/STUN/ports; full dual-stack remains required for existing IPSET and Lab paths.

**Boundary:** This decision authorizes current task prioritization and documentation; it does **not** claim source implementation, a new package, a working IPv6 IPFW capture, media/call success, a P2P feature or a new stable release. Proceed with Stage 1 of the plan after Stage 0 documentation delivery; record source/CI/owner-installed results separately. Earlier Voice P2P idea entries remain **historical/deferred**, not competing current product instructions.

**Status:** Active owner-approved implementation target; Stage 0 documentation only until code and verification actually follow.

## 2026-10-28 — Approved Strategy Lab IPv6 checkbox, domain family gating and combined budgets

**Owner's approved UI layout:** On the **Strategy Lab page only**, preserve the `Режим:` / `Mode:` label and Standard/Extended selector in the first row. Add `IPv6` immediately beneath, with the label on the left and a single checkbox indicator aligned beneath the selector's left edge on the right, matching the owner's attached UI screenshot. The indicator may be round visually but is an independent checkbox, not a radio selection; default is unchecked. The Run/Stop buttons and Mode selector stay where they are. Keep RU/EN UI behavior. The deferred **Voice-page** IPv6/P2P redesign remains a different project.

**Owner's requested scope:** IPv6 OFF means Strategy Lab tests **IPv4 only**, regardless of AAAA presence; IPv6 ON permits **both IPv4 and IPv6** when the supplied domain and usable network support both. Domain with A only tests IPv4 even if checked; domain with AAAA only requires ON to run IPv6, otherwise report no enabled address family rather than an IPv4 strategy failure. An IPv4 literal remains only that IPv4; an IPv6 literal requires ON and never falls back to IPv4. Per-family tests must pin and attest the exact remote endpoint, preserving Host/SNI and replay identity.

**Owner-approved duration:** Standard mode **150 seconds for one eligible family**, **200 seconds for eligible dual-family** (+50); Extended mode **270 seconds for one**, **350 seconds for both** (+80). These are total job time envelopes, not a sequential restart of the complete budget per family. Checking IPv6 without eligible AAAA/IPv4 together does not add time. Existing adaptive-workload budget ownership must be reconciled within the approved totals, without double-counting the previous IPv6 eligibility bonus or weakening restoration/Stop safeguards.

**Implementation boundary:** Record this now in the current [dual-stack specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md), [Stage-6 per-file plan](architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md), and Strategy Lab/adaptive-budget specialist contracts. Stage 1 remains the immediate next development action. **Documentation-only approval:** no new GUI, runtime behavior, package, installed test or stable release is claimed.

## 2026-10-29 — Owner-approved global forward-only development model (test stand)

**Decision:** The plugin is developed on an experimental OPNsense test stand, not maintained as a production-compatible upgrade matrix. Implement and exercise exactly one **current** approved architecture. When a subsystem, parser, Config shape, strategy, owner or UI contract is replaced, remove the retired executable branch, migration-only check, dormant fallback, unused compatibility wrapper and obsolete matching regression in the same logical change. Do not keep hidden switches, alternative old implementations, version-detection branches or legacy sealed-runtime exceptions against the hypothetical need to go backward. Work boldly on the replacement in its proper source location rather than on an old/new parallel path. There is no default duty to automatically resume a previous package's sealed layout after installing an experimental new format. If fresh application of the new format is needed, surface that requirement and use the current native process.

**Recovery distinction:** Reverting a product decision means making a new reviewed GitHub change, using Git history; do not ship product-version fallback code. This does **not** cancel per-operation transactional integrity: temporary IPFW/Config/process changes must still be either committed coherently or cleaned up / brought back to the same transaction's immediate pre-operation state when an operation fails. That is not keeping an old parser, engine, strategy or configuration implementation alive. Preserve one Config and one native owner, fail-closed behavior, source/CI/FreeBSD tests and truthfulness about unverified owner-installed results. No unnecessary production-style migration matrix or rollback scaffold is required for this test stand.

**Current application:** In the v0.6.1 Exclude IPSet effort the one Python `ipset_policy.py` remains the semantic IPv4/IPv6 parser; the PHP `IPSetPolicyBridge.php` is strictly an invocation/transport adapter, not a second parser. Keep actual native `--ipset-exclude=` on every applicable Strategies/Voice runtime profile when the global list is populated. Delete the specific pre-Exclude-IPSet sealed-runtime and empty-field compatibility exceptions and their obsolete tests when performing the related current-source correction, not as parallel safety net. The owner's `v0.6.1_8` shell test showed `SAVED_IPSET=PASS` for all six lists and `PHP_BRIDGE=FAIL Native Python IPSET preflight unavailable`; this is a live defect to fix in the single current implementation, not a reason to revive an older PHP parser.

**Scope and evidence:** This decision is effective immediately and recorded as the permanent development principle `DEV-050`. This documentation decision does not itself modify program source, the installed appliance or package revision; the current defect and old-branch deletion require their own source verification and testing-package delivery. Historical decisions and immutable GitHub tags are preserved as history, not as live alternative architecture.

==================================================
2026-10-30 — VERSION-INDEPENDENT PYTHON ENTRYPOINTS
==================================================

Date:
2026-10-30

Decision:
Installed plugin Python entrypoints must not depend on literal minor-version
binary paths such as /usr/local/bin/python3.13 or /usr/local/bin/python3.11.
Use one verified fail-closed interpreter-resolution contract for shell, PHP,
configd, installation hooks and Python shebang entrypoints. Child Python
processes use sys.executable where already running under a verified
interpreter. Keep a test-only interpreter override when needed.

Reason:
Binary minor versions change with platform releases. The owner rightly
requested decoupling from binary path revisions. On 30 October 2026 the
apparent Python3.13 absence proved to be commands entered on pfSense rather
than OPNsense; that mistake does not invalidate the structural debt. The
real OPNsense 26.7.7 has both python3 and python3.13, but FreeBSD lang/python313
does not guarantee the generic python3 meta-port symlink.

Consequences:
Do not globally replace python3.13 with python3 without dependency and
installer guarantees. Verify exact installed runtime and minimum Python
features, no accidental fallback to an unsupported environment, correct
execution by OPNsense configd and cold-install hooks. Preserve current
fail-closed, FD9, native owner and transaction contracts. Version-specific
CI images and historical records may retain explicit interpreter identity
as test fixtures. The first actual packaged-source correction starts
v0.6.1_13 under DEV-032; documentation and unbundled diagnostic changes
properly retain v0.6.1_12 under DEV-033. Supporting FreeBSD16/pfSense
requires separate platform/package proof, not alias substitution.

Affected documents:
docs/START_HERE.md
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/verification/STAGE5_WAN_OWNER_REVIEW_CHECKPOINT.md
docs/verification/STAGE5_WAN_SINGLE_BASELINE_CAPTURE.md

Status:
Active

## 2026-10-30 — Version-independent external dependencies and portable platform boundaries

**Decision:** The owner approved a project-wide default of dependency-version independence, one authoritative machine-readable *external compatibility* manifest when version/range/ABI/pinned executable requirements are necessary, and a clearly separated reusable Zapret2 core and adapters for each **target installation platform**. The permanent normative requirement is [DEV-052](PROJECT_PRINCIPLES.md). The earlier 30 October Python-specific decision remains one application of this general policy, not a parallel rule.

**Reason:** The operating systems/distributions, packages, binaries, runtimes and kernel interfaces of target installation platforms will evolve. Minor package updates should not force search-and-replace through unrelated modules. Porting to any additional platform should reuse the tested core and implement only the required, qualified platform adapter rather than duplicating the application.

**Consequences:** The next package-source increment `v0.6.1_13` implements the approved Python-entrypoint part of the policy under the existing task. When implementation genuinely needs an external dependency version, ABI or supported range, store its authority in one manifest, with other ecosystem-required declarations generated from or checked against it. A config-only manifest with duplicate values still hardcoded in Makefile/PHP/shell would **not** satisfy the decision. Maintain `VERSION` and `PLUGIN_REVISION` as their existing independent project/package authorities. Do not assert compatibility with an additional target installation platform, its OS release or ABI until qualified; do not prebuild unapproved platform variants or revive legacy runtime branches.

**Affected documents:** `docs/PROJECT_PRINCIPLES.md`, `docs/DECISIONS.md`, `docs/START_HERE.md`, `docs/ROADMAP.md`, [implementation task #732](https://github.com/Tolian82/os-zapret2-restyle/issues/732).

**Status:** Active. Architectural policy recorded; package-source changes and platform qualification not yet implemented.

## 2026-10-30 — Python unification cancelled within the Exclude IPSet / IPv4/IPv6 specification

**Latest owner decision (superseding the implementation timing and scope of the Python-specific 2026-10-30 entries above):** Cross-project Python interpreter/runtime unification is **CANCELLED within the currently approved Exclude IPSet / IPv4/IPv6 technical specification**, including Stage 5 and subsequent stages. It is **not deferred to any later stage of this same specification**, and it is not a dependency, acceptance criterion, or release blocker for the active dual-stack work.

**Future boundary:** Python unification may be undertaken **after the present technical specification only under a new, separate owner-approved technical specification and implementation plan**. Previously recorded Python path/resolver requirements, [issue #732](https://github.com/Tolian82/os-zapret2-restyle/issues/732), and the closed/unmerged [PR #740](https://github.com/Tolian82/os-zapret2-restyle/pull/740) remain historical design input, not authorization to implement, resume, or reserve `v0.6.1_13`. The next actual `PLUGIN_REVISION` is determined by a separately approved packaged-source change under DEV-032/033.

**Unaffected canon:** Existing one-Python IPv4/IPv6 IPSET semantic compilation (`ipset_policy.py`), bug fixes required by the present work, general portability principle DEV-052, original native Config/FD9/IPFW ownership, and evidence/rollback gates remain in effect. This entry changes only the current scope/priority, not production code, package, installed appliance, or stable release.

**Current authority:** [Exclude IPSet specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md), [staged plan](architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md), and [START_HERE](START_HERE.md). **Status:** Current owner-approved scope correction; earlier Python implementation timing is superseded.

**2026-10-30 — Owner decision: advance one revision for every new `main` commit (supersedes the docs-only no-bump exception).** Within unchanged `VERSION=A.B.C`, each `main` commit, including documentation, tests, governance, CI and product changes, increments `PLUGIN_REVISION` exactly once (`_N -> _N+1`). A PR consumes exactly one revision relative to its current mergeable `main` base; fixup commits before merge do not consume more. An authorized `VERSION` transition resets to `_1`. Titles and squash subjects use the new source candidate. An incremented source identity does **not** mean its installable `.pkg` was built, published, tested or installed. Existing published assets and tags keep immutable historical identities. This decision supersedes the previous docs/CI no-bump guidance. Normative rules: [DEV-027–DEV-038](PROJECT_PRINCIPLES.md), [GH-014–GH-016, GH-035, GH-049, GH-061](GITHUB_PUBLICATION.md). First governed transition: `v0.6.1_12 -> v0.6.1_13` for source/governance only; published/owner-installed `_12` unchanged.

## 2026-10-31 — Installed acceptance without live IPv6 WAN on IPv4-only owner stand

**Owner's latest binding acceptance decision:** The OPNsense test stand currently has **no working IPv6 connectivity**. All remaining **live IPv6 traffic / WAN / browser / Strategy Lab IPv6 runs on that stand are SKIPPED / NOT TESTED**, explicitly **not failures and not blocking delivery/acceptance** of the `v0.6.1_30` testing package. No further live IPv6 experiment is requested. Preserve the already successful **three controlled native IPv6 FreeBSD 15.1 Stage 6 scenarios** and existing source/CI contracts without repeating them.

**Owner's observed installed IPv4 evidence (`v0.6.1_30`):** Screenshot of Standard Strategy Lab for `rutracker.org`, checkbox IPv6 ON but Stage30 output **"PASS — IPv4 и QUIC/IPv4 доступны; IPv6 недоступен; проверки IPv6 исключены"**. The IPv4-eligible path completes Stage85 with **three stable TLS 1.3 candidates**, Stage90 reports original Zapret2 service restored, Stage99 SUCCESS; optional cyclic browser check shows FINISHED and restoration confirmation. This proves the particular reported native IPv4 lab/restore behavior, **not IPv6 connectivity, IPv6 effectiveness, or a verified user-browser DPI bypass over WAN**. Enabling the checkbox does not fabricate an IPv6 probe when no IPv6 network exists.

**Scope and evidence boundary:** Accept Stage8 **without live IPv6-dependent tests** for this IPv4-only stand. Source/native IPv6 compatibility remains qualified by the separate isolated FreeBSD CI; real IPv6 WAN behavior is **UNTESTED BY ENVIRONMENT (owner-accepted waiver)**, never labeled PASS. Keep separately required non-IPv6 checks and explicit results factual; a later IPv6-capable deployment can optionally validate behavior as a new scope rather than retroactively declaring IPv6 on this stand. Testing package identity remains published/installed `_30`, source-only owner batch report revision `_32` is not a new package, and this decision does not by itself authorize stable release / package repository promotion.

**Status:** ACTIVE, supersedes prior wording treating missing owner-stand live IPv6 as a compulsory acceptance blocker. Existing IPv4-based acceptance and restore results accepted as reported; no further live IPv6 tests requested.

## 2026-10-31 — Full v0.6.2 release authorization after bounded installed Stage8 audit

**Binding owner instruction:** Publish a full stable **v0.6.2** release, including README functionality updates. The tested installed `v0.6.1_30` produced 18 PASS / 0 WARN / 0 FAIL for the read-only package/service, global Exclude profile, saved Config, native IPFW/Voice and resources-inventory checks. The owner had already accepted successful IPv4 Strategy Lab Stage85/90/99 and restoration. The previous decision waiving real IPv6 WAN trials on this IPv4-only stand is retained; native FreeBSD15.1 IPv6 evidence remains independent and is not labeled installed WAN success. No installed packet-level A07/A08 or Voice MEDIA/CALL PASS is inferred. The only authorized version transition is `VERSION=0.6.2`, revision `_1`, plus exact-full-release publication of GitHub Release assets, checksum and `FreeBSD:15:amd64` Pages/pkg; outcomes must be verified after execution.
