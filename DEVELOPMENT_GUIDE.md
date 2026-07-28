# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How do we develop this project?

Purpose:
Describe the repeatable development workflow.

Updated when:
The workflow changes.

Read after:
WORKING_CONVENTIONS.md

Do not store here:
Architecture, project status or decision rationale.

==================================================
REPOSITORY
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Working tree:
/root/os-zapret2-restyle

Branch:
main

==================================================
STANDARD WORKFLOW
==================================================

1. Restore project context using the reading order in INDEX.md.

2. Check repository state.

cd /root/os-zapret2-restyle
git status --short
git branch --show-current
git log -1 --oneline

3. Record the objective, scope, expected verification, and affected documents.

4. Perform the required audit or investigation and record results in AUDIT.md.

5. For every non-OK finding, record its stable ID, exact affected locations,
   chain, evidence, impact, verification plan, remediation plan, acceptance
   criteria, required documentation updates, and current status.

6. Before starting the next audit block or changing code, update, review, and
   commit all affected Engineering Memory documents.

7. Create a backup when changing live files.

8. Apply a minimal change.

9. Validate.

Examples:

git diff --check

/bin/sh -n script.sh

php -l file.php

10. Review the complete diff.

11. Run focused live tests.

12. Update every affected document, including audit and current-state records.

13. Stage explicit files only.

14. Review staged diff.

15. Commit one logical change.

16. Push and verify origin/main.

==================================================
REPOSITORY LAYERS
==================================================

Repository source:
/root/os-zapret2-restyle/src/

Installed plugin:
/usr/local/opnsense/

Runtime:
/usr/local/etc/zapret2/

Repository source is authoritative.

==================================================
AUDIT WORKFLOW
==================================================

Inventory:

GUI
↓

MVC
↓

configd
↓

shell
↓

backend
↓

runtime

Classify every interface:

OK
broken
unused
duplicate
inherited
requires live test

Record the inventory, classifications, broken chains, evidence, and required
live tests in AUDIT.md.

Only after the relevant audit result has been documented may inherited code be
removed or a broken chain be changed.

A completed audit block follows this sequence:

investigate
↓
verify evidence
↓
record detailed findings and plans in AUDIT.md
↓
update PROJECT_STATE.md, DEVLOG.md, ROADMAP.md, and DECISIONS.md when applicable
↓
review and commit the complete documentation state
↓
only then start remediation or the next audit block

An audit block is not complete before the documentation commit. A finding is not
ready for remediation until its verification plan, remediation plan, acceptance
criteria, and documentation impact are recorded.

commit the documentation state
↓
start remediation or the next audit step

==================================================
FINDING AND ARCHITECTURE-DEBT WORKFLOW
==================================================

When an audit result is discovered:

investigate
↓
classify as Finding or Architecture Debt
↓
record full evidence and plans in AUDIT.md

For a Finding with no blocking Architecture Debt:

verify scope
↓
implement minimal remediation
↓
run acceptance tests
↓
update audit status and affected documents
↓
commit

For Architecture Debt or a blocked Finding:

Open
↓
Discussion
↓
record approved behavior in DECISIONS.md
↓
update architecture and specialist documents
↓
Implementation
↓
Verification
↓
Documentation
↓
Closed

Do not implement a dependent Finding before the controlling Architecture Debt reaches
Decision status.
