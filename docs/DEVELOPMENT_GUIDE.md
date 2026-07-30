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


==================================================
DELIVERING COMMANDS TO THE TEST SYSTEM
==================================================

Present commands in separate sequential blocks:

1. Checks and other.
2. Installation.
3. Minimal live verification only when required by the changed behavior.

A validation block must not perform installation, commit, push, restart, or other
mutation. An installation block may group related package build, publication, and
installation commands. Avoid shell variables in commands intended for the default
OPNsense csh root shell unless the whole block is executed explicitly by /bin/sh.

==================================================
CURRENT IMPLEMENTATION PRIORITY
==================================================

For Milestone 7, choose work in this order:

1. Finish the current documentation synchronization.
2. Move internal documentation into `docs/` and update references.
3. Verify strategy application to named HOSTLIST and IPSET targets.
4. Compare actual behavior with REQUIREMENTS.md.
5. Implement and live-test missing or defective approved behavior in focused commits.

Do not start a general UX audit or redesign programme during this work. A focused
interface change is appropriate only when required by the functionality being
implemented or when the current interface prevents use of that functionality.

Keep process discussion proportional to the project. Existing guidance is sufficient;
prefer coding and verification over adding more methodological text unless practice
exposes a concrete gap.


## Package lifecycle verification

Every lifecycle change must be verified as one complete sequence on a supported clean
OPNsense test system:

1. Build the package and inspect its manifest scripts.
2. Install through pkg/Firmware without running `setup.sh` manually.
3. Confirm the detached bootstrap reaches `ready` and produces executable dvtws2.
4. Confirm Start and Apply do not invoke package installation or compilation.
5. Upgrade/reinstall and confirm old deinstall hooks do not delete the preserved runtime.
6. Delete the package and confirm service/process/rule cleanup occurs before files vanish.
7. Confirm the downloaded engine, generated state, logs, locks, PID files and safely
   removable managed dependencies are gone.
8. Confirm menu, ACL, configd actions and templates no longer remain active.
9. Record commands, observed output and remaining limitations in DEVLOG/AUDIT before
   declaring the lifecycle verified.
