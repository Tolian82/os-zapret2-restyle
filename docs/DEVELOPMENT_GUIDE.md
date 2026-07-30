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
installation commands. Avoid shell variables in commands intended for the default OPNsense csh root shell unless the whole block is executed explicitly by POSIX sh. All console instructions must target csh by default. When POSIX sh is mandatory, show `sh` as a separate command before the block and `exit` as a separate command after the block; commands after `exit` return to csh syntax.

==================================================
CURRENT IMPLEMENTATION PRIORITY
==================================================

For the active milestone, choose work in the order recorded in ROADMAP.md. For Milestone 8, the first work package is GUI management of bol-van/zapret2 stable releases through the existing setup.sh backend. The additional BLOB repository follows only after the project owner supplies its repository and contract.

Historical Milestone 7 ordering was:

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

==================================================
LIVE PACKAGE BASELINE VERIFICATION MATRIX
==================================================

For each candidate release baseline, verify and record these stages separately:

1. Static source verification
   - sh -n for all shell files;
   - focused profile normalizer and pipeline tests;
   - package hook inspection;
   - git diff --check.

2. Package archive verification
   - package name/version/origin/URL;
   - package file inventory;
   - executable modes;
   - +POST_INSTALL, +PRE_DEINSTALL, and +POST_DEINSTALL content;
   - no unintended runtime tree in the plugin package.

3. Clean install verification
   - pkg installation finishes;
   - configd and Web GUI remain healthy;
   - exact manual setup command is printed;
   - no runtime dependency installation or compilation occurs inside pkg installation.

4. Runtime setup verification
   - setup.sh install obtains pinned bol-van/zapret2 v1.0.3;
   - dependencies are available;
   - dvtws2 is built and executable;
   - setup state/logs reach ready;
   - repeated setup is deterministic.

5. Service verification
   - Start, Status, Restart, Reconfigure, Apply, and Stop;
   - PID identity and stale PID handling;
   - ipfw and kernel module state;
   - supervisor identity;
   - active runtime preservation on invalid candidate.

6. Lifecycle verification
   - upgrade;
   - removal while running;
   - no post-deinstall configd restart;
   - preserved runtime/dependencies;
   - reinstall;
   - reboot;
   - controlled dvtws2 failure.

Every test result must update AUDIT.md and DEVLOG.md. PROJECT_STATE.md and ROADMAP.md
must be updated whenever the current baseline or immediate next action changes.


==================================================
PATCH DELIVERY WORKFLOW
==================================================

The default remote-development delivery artifact is a unified Git patch, not a list of
commands that edits tracked files directly.

Patch preparation requirements:

1. Start from the exact supplied source baseline.
2. Make one minimal logical change in a separate preparation tree.
3. Include documentation required by the project's synchronization rules.
4. Include required Git mode changes, such as 100644 to 100755.
5. Generate a patch suitable for `git apply`.
6. Validate that the patch applies to the supplied baseline.
7. Deliver the `.patch` artifact to the project owner.

Patch application on the project working tree:

cd /root/os-zapret2-restyle && \
git status --short && \
git apply --check /path/to/change.patch && \
git apply /path/to/change.patch && \
git diff --check && \
git status --short

After application, review the complete diff, execute the documented syntax and focused
live tests, stage explicit paths, and commit one logical change.

Do not use console editors or ad-hoc rewrite commands to modify tracked repository files.
Operational work outside the repository remains permitted.

==================================================
PREPARING A PATCH FROM THE OWNER'S ARCHIVE
==================================================

1. Complete discussion and obtain approval for the logical change.
2. Receive `os-zapret2-restyle-<short_commit_sha>.tar.gz` from the project owner.
3. Treat the extracted tree, including its current tracked modifications and file
   modes, as the exact patch baseline.
4. Make the approved changes in a separate copy of that tree.
5. Generate one unified Git patch containing all code, mode, and documentation
   changes required by the logical change.
6. Extract or copy the original archive again and run `git apply --check` there.
7. Deliver the `.patch` artifact only after that check succeeds.
8. After the owner commits the patch, use a new archive from the new commit for
   the next change.

Do not rebuild the baseline from GitHub, model memory, chat excerpts, or a
standalone `git diff`.
