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

1. Check repository state.

cd /root/os-zapret2-restyle
git status --short
git branch --show-current
git log -1 --oneline

2. Create backup when changing live files.

3. Apply a minimal change.

4. Validate.

Examples:

git diff --check

/bin/sh -n script.sh

php -l file.php

5. Review the complete diff.

6. Run focused live tests.

7. Stage explicit files only.

8. Review staged diff.

9. Commit one logical change.

10. Push and verify origin/main.

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

Only after the audit may inherited code be removed.
