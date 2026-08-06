# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Which engineering rules are already settled?

Purpose:
Store permanent project identities, engineering principles and working rules.

Updated when:
A permanent rule or approved convention changes.

Read after:
DECISIONS.md

Do not store here:
Current project status, history, roadmap or implementation details.

==================================================
STABLE IDENTITIES
==================================================

Project:
os-zapret2-restyle

Repository:
os-zapret2-restyle

Installed package:
os-zapret2-restyle

Makefile PLUGIN_NAME:
zapret2-restyle

MVC namespace:
OPNsense\Zapret

Internal service:
zapret

Configd namespace:
zapret

Version source:
VERSION

==================================================
ENGINEERING PRINCIPLES
==================================================

- Correctness over speed.
- Preserve working behavior before optimization.
- One logical scope per pull request; `main` receives one squash commit.
- Repository source is authoritative.
- Generated runtime is never committed.
- Validate before activation.
- Transactional Apply is mandatory.
- Do not remove inherited references mechanically.
- Audit before refactoring.
- Documentation is part of the project architecture.
- Changes to the documentation system are architectural changes.
- Every approved rule must be recorded in the applicable project documents.

==================================================
AUDIT RULES
==================================================

Every inherited reference must be classified before removal.

Allowed classifications:

OK
broken
unused
duplicate
inherited
requires live test

The word "zapret" alone is not evidence of obsolete inheritance.

AUDIT.md is the authoritative register for audit scope, verified chains, broken
chains, classifications, live-test requirements, and remediation status.

Each audit block is considered complete only after all affected Engineering
Memory documents have been updated, reviewed, and committed. Until then, work
must not proceed to the next audit block or to code changes.

Every non-OK finding must have a stable ID, exact affected locations, chain,
evidence, impact, verification plan, remediation plan, acceptance criteria,
required documentation updates, and remediation status in AUDIT.md.

A broken chain must be recorded before it is fixed. After verification, its audit
status must be updated rather than silently removed.

==================================================
CHANGE RULES
==================================================

- Make minimal reviewable changes.
- Fix the exact GitHub base commit before editing.
- Keep one logical scope in one task branch and pull request.
- Same-scope work and repair commits may remain in that branch; `main` receives one
  squash commit.
- Include all affected documentation and Git file-mode changes in the same logical
  scope.
- Validate before publication.
- Review the complete diff.
- Diagnose validation failures from exact evidence and repair same-scope defects in the
  same PR.
- Do not merge or publish a failed or partially validated latest head.

==================================================
TESTING RULES
==================================================

Run appropriate syntax checks.

Run:

git status --short
git diff --check
git diff --stat

Perform focused live tests when behavior changes.

Never claim a test passed unless it was actually executed.

==================================================
GIT RULES
==================================================

Preferred sequence:

use the connected GitHub plugin first
read current GitHub main
record full base SHA
inventory relevant PRs, branches, workflows, runs, artifacts, tags, releases, and assets
confirm required state is published
change one logical unit
validate
review diff
git add explicit paths when using a local checkout
review staged diff when using a local checkout
commit or publish same-scope repair commits
recheck remote main against base SHA
publish one working branch
open one Ready PR when the diff is ready
wait for required CI on the latest head
repair same-scope failures in the same PR
squash merge with the expected head SHA
verify published commit
clean the temporary branch
build and perform focused live verification when applicable

A narrow fallback transport is allowed only when the GitHub plugin is responding and one
exact function or permission is confirmed missing. If the plugin is unavailable,
non-responsive, or cannot provide the authoritative state required for safe work, stop
all GitHub work, inform the owner, and wait for explicit direction.

==================================================
DOCUMENT SYNCHRONIZATION
==================================================

Code and affected documentation belong in the same logical change.

Approved concepts and rules must be recorded in DECISIONS.md and reflected in
the appropriate specialist documents.

Changes to document structure, document responsibilities, reading order, audit
method, development workflow, or documentation-maintenance rules are
architectural changes. They require a decision entry and synchronized updates to
all affected documents in the same logical change.

==================================================
ENGINEERING MEMORY WORKFLOW
==================================================

Every development stage begins with documentation and ends with documentation.

Before starting work:

- Record the objective.
- Record the implementation plan.
- Record the expected verification.

During work:

- Record approved concepts immediately.
- Record new permanent rules immediately.
- Record architecture changes immediately.
- Record important discoveries that affect later work.

After finishing work:

- Record what was completed.
- Record what was verified.
- Record what failed or remains unresolved.
- Update current project state.
- Update roadmap completion.
- Record the next planned stage.

Engineering Memory is maintained continuously during development rather than
written only after the work is finished.

==================================================
FINDINGS AND ARCHITECTURE DEBT
==================================================

Findings and Architecture Debt are separate engineering records.

A Finding records a confirmed implementation defect, inconsistency, obsolete or
unused interface, duplicate, or concrete operational risk. It must include evidence,
a verification plan, a remediation plan, acceptance criteria, and affected documents.
Resolved Findings remain in AUDIT.md as history.

Architecture Debt records an unresolved design question. It is not an implementation
defect and must not be "fixed" in code before the intended behavior is approved in
DECISIONS.md.

Architecture Debt follows this lifecycle:

Open
↓
Discussion
↓
Decision
↓
Implementation
↓
Verification
↓
Documentation
↓
Closed

Architecture Debt cannot be closed directly. It closes only after a recorded decision,
required implementation, verification, and synchronized documentation.

A Finding must not be remediated while an open Architecture Debt item determines its
intended behavior.

==================================================
MANDATORY RESPONSE PREFLIGHT
==================================================

For every new or resumed project context:

1. Obey the repository-root `AGENTS.md`, then read `INDEX.md` and `PROJECT_STATE.md`.
2. Read the specialist documents relevant to the requested scope.
3. Complete a full repository-wide reading only for a repository-wide audit or genuine
   full-context recovery; it is not a blocking prerequisite for every diagnosis,
   command, or small change.
4. Read the current active decision and procedure for any GitHub mutation.
5. Re-read the relevant specialist document when any workflow or command detail is
   uncertain; memory and earlier chat output are not substitutes.
6. If OPNsense commands will be delivered, identify the target shell as root csh and
   perform the command-dialect check below before sending them.

A brief progress notice may be sent while context is being restored, but it must not
claim conclusions that have not yet been verified.

==================================================
COMMAND BLOCK SEPARATION
==================================================

Operational instructions must separate read-only validation from state-changing
actions. Do not combine them in one shell block.

Use these headings and responsibilities:

- Checks and other: status inspection, dry runs, git apply --check, syntax checks,
  diff review, staging, and staged-diff validation.
- Installation: optional git apply, commit, publication, package build or
  installation, service restart, and other commands that change repository or
  system state.

Keep package publication and installation commands together where possible, but
never mix them with the preceding validation block. Commands must remain in actual
execution order and must be valid for the OPNsense root shell or explicitly invoke
/bin/sh when POSIX shell syntax is required.

The default and mandatory presentation target for OPNsense console instructions is the root csh shell. Do not silently assume sh, bash, or another shell. If POSIX sh is required, show an explicit `sh` command before the POSIX block and an explicit `exit` command after it. Commands that follow `exit` must again be valid csh commands.

Before sending an OPNsense command block, inspect it for POSIX-only constructs,
including `$(...)`, `name=value` shell assignments, `export`, `if ...; then`,
`$((...))`, and shell functions. Replace them with csh-safe commands where practical.
If any are required, place the complete affected sequence between explicit standalone
`sh` and `exit` commands. A command copied from a Linux, CI, or local development
shell is never assumed to be valid on the OPNsense console without this check.

==================================================
FOCUS, SUFFICIENCY, AND INTERFACE STABILITY
==================================================

The project is a small applied addon with a defined scope. Prefer reasonable
sufficiency over speculative completeness or unnecessary abstraction.

Current priorities:

1. Make the already approved functionality work correctly.
2. Verify it on a real supported OPNsense system.
3. Keep documentation synchronized at a level that supports development and recovery.
4. Discuss future expansion only without displacing current implementation work.

UX is supporting work rather than a standalone objective. Consider interface changes
when expanded functionality needs them or when the existing interface demonstrably
blocks an implemented capability. Otherwise keep the interface stable.

Do not begin general audits or redesigns of Navigation, First Run, Service,
Diagnostics, Maintenance, Status, or Strategy while the current approved functionality
remains incomplete.

Project guidance should normally be treated as recommendations and priorities. Use
hard requirements only where correctness, compatibility, release safety, or repository
consistency genuinely depends on them.

Approximate effort preference, not a quota:

- 60% coding;
- 15% documentation;
- 15% discussion of current work;
- 8% discussion of future work;
- 2% broader process or philosophical discussion.

## Runtime lifecycle ownership

Package lifecycle and runtime bootstrap changes are one architectural unit. Code hooks,
setup backend, service boundaries, configd integration, verification instructions, and
all affected documentation must be committed together. Runtime setup uses the single
`setup.sh install` backend, initially exposed as the exact post-install command and later
through a GUI maintenance action.

Package upgrade preserves service state: replacement +PRE_INSTALL synchronously stops
the installed running service before the old hook and file replacement; +PRE_DEINSTALL
keeps the same fail-closed contract for removal and subsequent upgrades; new
+POST_INSTALL starts replacement code. A stopped service stays stopped. Stop failure
aborts the package operation and is never suppressed. Incomplete
runtime state is cleaned but is not automatically promoted to running. Successful
`setup.sh install` captures complete service state before runtime mutation. It refreshes
and verifies a previously running service, while a stopped service remains stopped and
is verified as such before setup reports ready. Incomplete or unknown initial state
fails closed. Runtime build staging and rollback remain a separate logical change.

==================================================
AUDIT IDENTIFIER AND LIVE-EVIDENCE RULES
==================================================

- Every AUDIT.md Finding ID is globally unique within the document.
- Existing IDs are never reused for a later unrelated finding.
- Cross-references must be updated when a duplicate historical ID is corrected.
- A finding may be marked live verified only when the exact package/runtime evidence is recorded.
- Static verification, package archive verification, and live OPNsense verification are distinct states.
- A working package built from an uncommitted tree is not a reproducible project baseline until the
  source and synchronized documentation are committed.

==================================================
BLOB SHORTHAND RULE
==================================================

- Supported shorthand is --blob=<name>.
- It resolves directly to files/fake/<name>.bin.
- The .bin suffix is omitted in the strategy.
- There is no implicit alias table.
- Native upstream --blob=name:value declarations containing ':' remain untouched.
- Missing files are hard errors and must not be silently substituted.

==================================================
GITHUB-COMMIT DEVELOPMENT RULE
==================================================

The default source baseline is an exact commit in the official GitHub repository,
normally the current `main` commit. Record the full SHA before editing and obtain all
file content and Git modes from that commit.

Required sequence:

use the connected GitHub plugin first
↓
read and record current `main` SHA and complete the pre-mutation inventory
↓
prepare one logical multi-file change
↓
run focused validation and review the complete diff
↓
publish one task branch and one Ready PR when the diff is ready
↓
keep same-scope work and repair commits in that PR
↓
pass required CI for the latest mergeable head
↓
squash merge with the expected head SHA and exact versioned subject
↓
verify `main` and clean the temporary branch
↓
build and perform focused verification when applicable

The working-branch and PR path is the default for ordinary requested development work.
Standing project-owner authorization covers branch creation, same-scope commits, Ready
PR creation, required-check inspection, same-scope repair, squash merge, verification of
`main`, and cleanup of the temporary branch created for that task. No repeated
confirmation is required.

Direct publication to `main` requires explicit project-owner instruction and must be a
fast-forward from the recorded base. Never force-push. A unified patch is used only when
explicitly requested or when relevant local-only state is transferred in that form.

The connected GitHub plugin is the mandatory first repository interface. When it is
responding but one exact function or permission is confirmed missing, authenticated Git,
`gh`, another API, or the web UI may be used only for that narrow operation. Return to
the plugin for subsequent supported reads and writes.

If the GitHub plugin is unavailable, non-responsive, or cannot provide the authoritative
state required for safe work, stop all GitHub work, inform the owner, and wait for
explicit direction. Do not continue through a fallback transport, automation, or
scheduled tracker merely to preserve progress. Missing `gh` alone is not a blocker while
the plugin or another explicitly permitted narrow fallback safely covers the operation.

Publication means branch, versioned work or repair commits, one Ready PR, required CI on
the latest head, squash merge, verification of `main`, and branch cleanup; a local patch
is not a published result. Release assets and the pkg repository additionally require
the explicit release authority defined below.

Do not modify tracked repository files directly from the OPNsense console with `vi`,
`ee`, `nano`, `sed -i`, `perl -pi`, Python rewrite scripts, `cat >`, `echo >>`, or
equivalent mutation commands.

This rule does not restrict temporary files, logs, diagnostics, generated build output,
installed-system configuration, or files outside the repository.

When a unified patch is explicitly selected, it must include all content and file-mode
changes and pass `git apply --check` against its exact base. This is an optional transfer
mode, not the default prerequisite for repository work.

==================================================
STANDING DELIVERY AUTHORIZATION
==================================================

An instruction to fix, add, change, implement, or complete an ordinary project
task authorizes the complete default PR cycle. The assistant selects routine
branch, commit, PR, and test details from the current source and documentation.

Explicit stopping points override the default. If the owner asks only for analysis,
diagnosis, review, a local change, a patch, a branch, or a PR, stop at that point.

Do not request confirmation for deterministic routine choices or for the Ready,
squash-merge, and temporary-task-branch cleanup steps after required checks pass.

One explicit request to make a release authorizes its complete verified release
pipeline. An ordinary development request does not authorize a version tag,
GitHub Release, package publication, or pkg-repository publication.

Stop for owner direction only on material architecture/product ambiguity, relevant
unpublished local state, an unresolvable required check failure, GitHub-plugin
unavailability, new credentials or protected authority, destructive work affecting user
data or pre-existing remote objects, force-push/history rewriting/direct-main
publication, or mandatory live OPNsense evidence available only from the owner.

When owner input is genuinely required, ask one consolidated question with the
evidence and a recommended choice. Never ask the owner to confirm facts available
from the repository, GitHub, CI, documentation, or read-only diagnostics.

Package revision handling is routine. Increment `PLUGIN_REVISION` once for an
ordinary change to packaged files or package behavior while `VERSION` is unchanged.
Reset it to `1` when an explicitly requested new project version changes `VERSION`.
A governance/documentation-only change outside package contents changes neither
value; path-applicable CI supplies the required verification without implying a release.

==================================================
LOCAL-ONLY STATE EXCEPTION
==================================================

GitHub is authoritative only for state that has been committed and pushed. It
cannot expose uncommitted or unpushed changes in the project owner's local
OPNsense checkout.

If local-only changes are relevant to the requested work:

1. stop before editing;
2. ask the owner to commit and push them, or explicitly transfer them as an
   archive or patch;
3. establish the exact transferred baseline;
4. never reconstruct or overwrite the unpublished state from memory.

A clean checkout synchronized with the recorded GitHub commit requires no
archive. Backups of live files outside the repository remain governed by the
separate operational backup rules.

==================================================
GUI MAINTENANCE BACKEND RULE
==================================================

The existing `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` is the single approved backend for GUI management of bol-van/zapret2 releases. The GUI must not introduce a second independent installer. User-visible requirements are release discovery, installed-version reporting, update notification, release selection, installation, update, and repeat installation. Internal download or Git operations remain backend implementation details and are not the name of the GUI task.

The additional BLOB repository is an approved later GUI work item, but its repository and technical contract remain undefined until supplied by the project owner. Do not invent a URL, manifest, directory layout, version scheme, integrity policy, or update behavior.

==================================================
REPOSITORY ARTIFACT HYGIENE
==================================================

Tracked editor backups, merge rejects, ad-hoc patches, transport fragments, encoded
payloads, and local backup files are forbidden in the authoritative tree. This includes
`*.orig`, `*.rej`, `*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, and
editor `*~` files. Build output remains ignored separately.

Historical records may remain when they are genuine engineering evidence, but a record
whose wording can be confused with current behavior must carry an explicit historical
or superseded status banner and point to the current authority.

`scripts/test-repository-hygiene.sh` is a mandatory CI gate. It rejects forbidden
tracked artifacts and verifies the active documentation authority markers. Exceptions
require a separate recorded decision and a narrow reviewed allowlist; none currently
exist.

Normal steady-state branch authority is `main`. `recovery/base` is preserved as a
separate recovery reference. Ordinary task, repair, release-preparation, and transport
branches are temporary and are removed after their work is superseded or squash merged.
