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
