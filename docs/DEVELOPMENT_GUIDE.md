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

2. Establish the authoritative source baseline.

cd /root/os-zapret2-restyle
git status --short
git branch --show-current
git log -1 --oneline

Read the current `main` from the official GitHub repository and record its full
SHA. When a local checkout is used, confirm that it corresponds to that commit
and that no uncommitted or unpushed local state is required by the change.

3. Record the objective, scope, expected verification, affected documents, and
   base SHA.

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

13. Stage explicit files only when using a local Git checkout.

14. Review staged diff when using a local Git checkout.

15. Create one atomic commit containing the complete logical change.

16. Re-read remote `main` and confirm that it still points to the recorded base
    SHA.

17. For an ordinary requested development task, publish the working branch and
    open one Draft PR. No separate publication confirmation is required.

18. Wait for required CI, correct same-scope failures when safe, mark the PR Ready,
    and squash merge after checks pass and the branch is mergeable. No separate
    merge confirmation is required unless the current request explicitly stops at
    the branch or PR boundary.

19. Verify the resulting `main` commit and clean up the temporary branch created for
    the task. Direct fast-forward publication to `main` remains an exceptional mode
    requiring explicit project-owner instruction.

20. Build once and run the focused live verification required by the change. For a
    documentation-only governance change outside package contents, leave package
    metadata unchanged; standard CI, including its package job, is the applicable
    build/verification stage and no separate release build is required.

==================================================
REQUEST SCOPE AND STANDING AUTHORIZATION
==================================================

Interpret the project owner's current instruction as follows:

- analyse, diagnose, explain, review: inspect and report without repository
  publication;
- prepare only, patch only, branch only, PR only: perform the requested work and
  stop at the named boundary;
- fix, add, change, implement, complete: perform the complete ordinary branch →
  Draft PR → CI → Ready → squash-merge cycle;
- make/release version X: perform the complete verified release cycle for that
  requested version, including its release-preparation PR, merge, tag, GitHub
  Release, package/pkg-repository publication, and post-publication checks.

Do not ask for routine branch names, commit messages, PR text, test selection, CI
waiting, Ready transition, squash merge, or cleanup of the temporary branch created
for the task. Derive those choices from the exact source, affected Finding or work
package, and current documentation.

Discover and use the publication capabilities already present in the working
environment. Prefer an authenticated GitHub integration/API, otherwise use an
authenticated ordinary Git remote, and use GitHub CLI when available. Missing `gh`
alone never justifies stopping, asking the owner to install it, or reporting the
change as unpublished. Stop only after every approved transport has been checked
and a standing escalation boundary remains.

Stop only when a material choice is not settled, relevant unpublished owner state
exists, a required check cannot be repaired within scope, new authority or credentials
are required, a destructive action affects user data or pre-existing remote objects,
force/history rewrite/direct-main publication is proposed, or mandatory live OPNsense
evidence must be supplied by the owner.

If input is required, ask one consolidated question with the evidence and a
recommended choice. Do not ask for information available through the repository,
GitHub, CI, project documentation, or read-only diagnostics.

Handle package metadata without a separate confirmation when the rule is
deterministic: increment `PLUGIN_REVISION` once for an ordinary packaged change with
unchanged `VERSION`; reset it to `1` for an explicitly requested new project version;
change neither value for governance/documentation-only work outside package contents.

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
REPOSITORY CHANGE DELIVERY
==================================================

Normal remote development begins from the exact current GitHub commit, not from
an owner-supplied archive.

Change preparation requirements:

1. Read the current `main` and record its full SHA.
2. Obtain content and Git file modes from that commit.
3. Confirm that no relevant owner state exists only in a local checkout.
4. Make one minimal logical change in a separate preparation tree.
5. Include documentation required by the project's synchronization rules.
6. Include required Git mode changes, such as 100644 to 100755.
7. Run static validation and review the complete diff.
8. Create one atomic commit.
9. Immediately recheck that remote `main` still equals the base SHA.
10. Publish an ordinary requested change through a working branch and Draft PR,
    pass required CI, then squash merge under the standing authorization. Use a
    narrower branch/PR/patch stopping point only when the current request specifies it.
11. Verify the published `main` commit, clean up the task-owned temporary branch,
    then perform one build and one focused verification. Direct publication to
    `main` remains exceptional and requires explicit instruction.

An authenticated GitHub integration/API may construct the blobs, tree, and
single commit atomically and then fast-forward the branch reference. GitHub CLI
is not a required dependency. Ordinary Git remains valid when available. Capability
discovery is mandatory before reporting a publication blocker; transport selection
is an implementation detail and is not delegated to the project owner.

Do not use console editors or ad-hoc rewrite commands to modify tracked repository files.
Operational work outside the repository remains permitted.

==================================================
HANDLING UNPUBLISHED LOCAL STATE
==================================================

GitHub cannot expose changes that exist only in `/root/os-zapret2-restyle` on the
project owner's OPNsense system.

If the owner reports relevant uncommitted or unpushed changes:

1. stop normal GitHub-baseline work;
2. ask the owner to commit and push the changes, or explicitly supply an archive
   or patch;
3. record the resulting exact commit or transferred tree as the baseline;
4. preserve its current tracked modifications and file modes;
5. do not reconstruct, discard, or overwrite it from GitHub or memory.

If an optional unified patch is requested, generate it from the exact established
baseline and require `git apply --check` before delivery. A clean checkout already
matching the recorded GitHub SHA requires no archive.
