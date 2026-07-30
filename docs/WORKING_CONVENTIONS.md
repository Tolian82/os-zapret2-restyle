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
- One logical change per commit.
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
PATCH RULES
==================================================

- Make minimal reviewable changes.
- Verify before staging.
- Review the complete diff.
- Stop immediately if validation fails.
- Do not continue after a failed patch.

==================================================
TESTING RULES
==================================================

Run appropriate syntax checks.

Run:

git diff --check

Perform focused live tests when behavior changes.

Never claim a test passed unless it was actually executed.

==================================================
GIT RULES
==================================================

Preferred sequence:

inspect
backup
patch
validate
review diff
live test
git add explicit paths
review staged diff
commit
verify
push
verify origin

==================================================
DOCUMENT SYNCHRONIZATION
==================================================

Code and affected documentation belong in the same logical commit.

Approved concepts and rules must be recorded in DECISIONS.md and reflected in
the appropriate specialist documents.

Changes to document structure, document responsibilities, reading order, audit
method, development workflow, or documentation-maintenance rules are
architectural changes. They require a decision entry and synchronized updates to
all affected documents in the same logical commit.

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
COMMAND BLOCK SEPARATION
==================================================

Operational instructions must separate read-only validation from state-changing
actions. Do not combine them in one shell block.

Use these headings and responsibilities:

- Checks and other: status inspection, dry runs, git apply --check, syntax checks,
  diff review, staging, and staged-diff validation.
- Installation: git apply, commit, push, package build or installation, service
  restart, and other commands that change repository or system state.

Keep package publication and installation commands together where possible, but
never mix them with the preceding validation block. Commands must remain in actual
execution order and must be valid for the OPNsense root shell or explicitly invoke
/bin/sh when POSIX shell syntax is required.

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
GIT-FIRST UNIFIED PATCH RULE
==================================================

Repository changes are exchanged as unified Git patches. The normal artifact is a
`.patch` file that can be checked and applied with Git and that includes both content
changes and required file-mode changes.

Required sequence:

prepare one logical patch
↓
git apply --check <patch>
↓
git apply <patch>
↓
git diff --check
↓
review the complete diff
↓
run focused validation and live tests
↓
commit one logical change

The assistant prepares the actual patch artifact. The project owner must not be asked to
recreate repository changes manually from prose or console-editing commands.

Do not modify tracked repository files directly from the OPNsense console with `vi`,
`ee`, `nano`, `sed -i`, `perl -pi`, Python rewrite scripts, `cat >`, `echo >>`, or
equivalent mutation commands.

This rule does not restrict temporary files, logs, diagnostics, generated build output,
installed-system configuration, or files outside the repository.

`git format-patch` / `git am` remain valid when preserving existing commit metadata is a
specific requirement, but they are not prerequisites for preparing an ordinary unified
Git patch.

==================================================
AUTHORITATIVE ARCHIVE BASELINE FOR PATCHES
==================================================

A multi-file patch is prepared only against the project owner's actual working
tree or an archive made from that tree. GitHub, model memory, chat fragments,
and separately supplied diffs are not substitutes for the working-tree baseline.

The project owner supplies the archive after the change has been discussed and
approved and the instruction to prepare the patch has been given.

The standard archive name is:

`os-zapret2-restyle-<short_commit_sha>.tar.gz`

The archive is authoritative only for the next logical patch. After that patch
is committed, the previous archive is obsolete and a new archive from the new
commit becomes the baseline for subsequent work.

A patch artifact is ready for delivery only after it has passed
`git apply --check` against an unchanged copy of the supplied archive baseline.
When a valid baseline is unavailable, request a new archive instead of
reconstructing the repository.
