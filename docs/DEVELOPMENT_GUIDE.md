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

1. Obey the repository-root `AGENTS.md`, then read `INDEX.md`, `PROJECT_STATE.md`,
   and the specialist documents relevant to the requested scope.

   A full repository-wide reading is required only for a repository-wide audit or
   genuine full-context recovery. It is not a blocking prerequisite for every focused
   diagnosis, command, or small change. DECISIONS.md, WORKING_CONVENTIONS.md, and
   DEVELOPMENT_GUIDE.md remain authoritative for the parts of the methodology that
   apply to the current scope; chat context and prior summaries are supporting context
   only.

2. Establish the authoritative source baseline.

cd /root/os-zapret2-restyle
git status --short
git branch --show-current
git log -1 --oneline

Use the connected GitHub plugin first to read current `main` from the official
repository and record its full SHA. When a local checkout is used, confirm that it
corresponds to that commit and that no uncommitted or unpushed local state is required
by the change.

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

15. Keep one logical scope in one task branch and pull request. Same-scope work and
    repair commits may remain in the branch; the final permanent `main` history receives
    one squash commit.

16. Re-read remote `main` and confirm that it still points to the recorded base
    SHA.

17. For an ordinary requested development task, publish the working branch and open one
    Ready PR when the diff is ready for review. Use Draft only for intentional work in
    progress or early design discussion. No separate publication confirmation is
    required.

18. Wait for required CI on the latest head, diagnose exact failures, correct safe
    same-scope defects in the same PR, and squash merge after checks pass and the branch
    is mergeable. No separate merge confirmation is required unless the current request
    explicitly stops at the branch or PR boundary.

19. Verify the resulting `main` commit and clean up the temporary branch created for
    the task. Direct fast-forward publication to `main` remains an exceptional mode
    requiring explicit project-owner instruction.

20. Build once and run the focused live verification required by the change. For a
    documentation-only governance change outside package contents, leave package
    metadata unchanged and use path-applicable CI. A FreeBSD package build is required
    only when package inputs or the CI package contract are affected; no release is
    implied.

==================================================
REQUEST SCOPE AND STANDING AUTHORIZATION
==================================================

Interpret the project owner's current instruction as follows:

- analyse, diagnose, explain, review: inspect and report without repository
  publication;
- prepare only, patch only, branch only, PR only: perform the requested work and
  stop at the named boundary;
- fix, add, change, implement, complete: perform the complete ordinary branch →
  Ready PR → CI → squash-merge cycle, keeping same-scope repairs in that PR;
- publish candidate `vX.Y.Z_N`: publish only that explicitly authorized testing
  prerelease and asset, without GitHub Pages or pkg-repository promotion;
- make/release version X: perform the complete verified stable release cycle for that
  requested version, including its release-preparation PR, merge, tag, GitHub Release,
  package/pkg-repository publication, and post-publication checks.

For a normal release-preparation PR, set the final squash subject to exactly
`vX.Y.Z_1: Prepare release vX.Y.Z` with the optional GitHub `(#PR)` suffix. The VERSION
change on `main` then starts the repository-owned release trigger, which creates the tag
and dispatches the Release workflow. Do not ask the owner to push that tag manually
unless the repository automation itself is unavailable or fails at a genuine protected
authority boundary.

Do not ask for routine branch names, commit messages, PR text, test selection, CI
waiting, squash merge, or cleanup of the temporary branch created for the task. Derive
those choices from the exact source, affected Finding or work package, and current
documentation.

Use the connected GitHub plugin first for every repository inspection and mutation. If
the plugin is responding but one exact function or permission is confirmed missing, use
an authenticated Git remote, `gh`, another API, or the web UI only for that narrow
operation and then return to the plugin.

If the GitHub plugin is unavailable, non-responsive, or cannot provide the authoritative
repository state required for safe work, stop all GitHub work, inform the project owner,
and wait for explicit direction. Do not silently continue through another transport,
automation, or scheduled tracker. Missing `gh` alone is not a blocker while the plugin or
another explicitly permitted narrow fallback safely covers the operation.

Stop only when a material choice is not settled, relevant unpublished owner state
exists, a required check cannot be repaired within scope, the GitHub plugin is
unavailable, new authority or credentials are required, a destructive action affects
user data or pre-existing remote objects, force/history rewrite/direct-main publication
is proposed, or mandatory live OPNsense evidence must be supplied by the owner.

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

Before delivery, scan every OPNsense block for `$(...)`, POSIX assignments,
`export`, `if ...; then`, arithmetic expansion, and shell functions. Their presence
requires an explicit `sh` / `exit` boundary unless the command is rewritten in csh.
For fixed release identifiers and commit SHAs, prefer static pipelines such as
`git rev-parse origin/main | grep -qx '<full-sha>'` instead of command substitution.

==================================================
CURRENT IMPLEMENTATION PRIORITY
==================================================

The Strategy Lab initial delivery and corrective source series are complete. The active
next product gate is the consolidated owner-assisted OPNsense verification matrix
recorded in `docs/ROADMAP.md` and the corrective audit.

An explicitly authorized testing prerelease may be published solely to perform that live
verification. It does not authorize stable release promotion, GitHub Pages, or the pkg
repository. Do not begin another Strategy Lab feature or stable release preparation
before the required live evidence is recorded.

The additional BLOB repository remains a later GUI work item. Its repository, manifest,
versioning, integrity, and update contract remain undefined until supplied and approved
by the project owner.

Keep process discussion proportional to the project. Existing guidance is sufficient;
prefer implementation and verification over adding methodology unless practice exposes
a concrete repeatable gap.

## Package lifecycle verification

Every lifecycle change must be verified as one complete sequence on a supported clean
OPNsense test system:

1. Build the package and inspect its manifest scripts, including replacement
   +PRE_INSTALL, +POST_INSTALL, old-package +PRE_DEINSTALL behavior, and +POST_DEINSTALL.
2. Install through pkg/Firmware and confirm the explicit setup.sh install command is shown.
3. Run setup.sh install once while running and once while stopped. Confirm executable
   dvtws2 is produced, the running service is refreshed before setup becomes ready,
   and the stopped service remains stopped without runtime processes.
4. Confirm Start and Apply do not invoke package installation or compilation.
5. Upgrade while running: old PIDs stop before replacement, new PIDs start afterward,
   and stop/start errors are not hidden.
6. Upgrade while stopped and confirm it remains stopped; inject a stop failure and
   confirm pkg aborts before file replacement.
7. Reinstall and confirm the preserved runtime is reused without destructive cleanup.
8. Delete the package and confirm service/process/rule cleanup occurs before files vanish.
9. Confirm runtime, configuration, logs, and shared dependencies remain preserved.
10. Confirm menu, ACL, configd actions and templates no longer remain active.
11. Record commands, observed output and remaining limitations in DEVLOG/AUDIT before
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
   - setup.sh install obtains and verifies the selected published stable bol-van/zapret2 release;
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

1. Use the connected GitHub plugin first, read current `main`, and record its full SHA.
2. Obtain content and Git file modes from that commit.
3. Confirm that no relevant owner state exists only in a local checkout.
4. Make one minimal logical change in a separate preparation tree.
5. Include documentation required by the project's synchronization rules.
6. Include required Git mode changes, such as 100644 to 100755.
7. Run static validation and review the complete diff.
8. Publish one task branch and one Ready PR when the change is ready. Same-scope work and
   repair commits remain in that PR; permanent `main` receives one squash commit.
9. Immediately recheck that remote `main` still equals the base SHA before publication
   and again before merge.
10. Pass required CI for the latest head, then squash merge under the standing
    authorization. Use a narrower branch/PR/patch stopping point only when the current
    request specifies it.
11. Verify the published `main` commit, clean up the task-owned temporary branch, then
    perform one build and one focused verification when applicable. Direct publication
    to `main` remains exceptional and requires explicit instruction.

The GitHub plugin may construct blobs, trees, commits, branches, PRs, and merges when it
supports the operation. If the responding plugin lacks one exact function or permission,
a narrow authenticated fallback may perform only that operation. GitHub CLI is not a
required dependency.

If the plugin is unavailable, non-responsive, or cannot provide the authoritative state
required for safe work, stop GitHub work, inform the owner, and wait for explicit
direction. Transport selection is not silently delegated to another client.

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
