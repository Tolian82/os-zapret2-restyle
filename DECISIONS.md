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
