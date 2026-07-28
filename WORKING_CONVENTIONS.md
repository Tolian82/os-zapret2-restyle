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

Approved concepts must be recorded in DECISIONS.md and reflected in the
appropriate specialist document.

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
