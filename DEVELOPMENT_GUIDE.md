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

5. Create a backup when changing live files.

6. Apply a minimal change.

7. Validate.

Examples:

git diff --check

/bin/sh -n script.sh

php -l file.php

8. Review the complete diff.

9. Run focused live tests.

10. Update every affected document, including audit and current-state records.

11. Stage explicit files only.

12. Review staged diff.

13. Commit one logical change.

14. Push and verify origin/main.

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

A completed audit step follows this sequence:

investigate
↓
verify evidence
↓
record in AUDIT.md
↓
update PROJECT_STATE.md, DEVLOG.md, ROADMAP.md, and DECISIONS.md when applicable
↓
commit the documentation state
↓
start remediation or the next audit step
