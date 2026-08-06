# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How do we develop this project?

Purpose:
Describe the repeatable investigation, implementation, GitHub delivery, publication,
and live-verification workflow.

Updated when:
The workflow changes.

Read after:
`WORKING_CONVENTIONS.md` and the active specialist decision for the task.

Do not store here:
Current project status, detailed history, or product architecture.

==================================================
REPOSITORY
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Normal owner checkout:
/root/os-zapret2-restyle

Primary branch:
main

==================================================
STANDARD WORKFLOW
==================================================

1. Complete the risk-based preflight.

   Read repository-root `AGENTS.md`, `docs/INDEX.md`, `docs/PROJECT_STATE.md`, and the
   specialist authorities relevant to the scope. Read `docs/GITHUB_PUBLICATION.md`
   immediately before any GitHub mutation. A full repository-wide reading is required
   only for a repository-wide audit or genuine context recovery.

2. Establish the exact source baseline.

   Record current remote `main` SHA. When a local checkout is used, confirm its branch,
   clean/relevant state, and relationship to that SHA. Do not guess unpublished owner
   state.

3. Record objective, logical scope, expected verification, affected documents, and base
   SHA.

4. For GitHub work, perform the pre-mutation inventory:

   - relevant PRs and branches;
   - existing workflows capable of the operation;
   - active, queued, failed, and successful runs;
   - artifacts, tags, releases, and assets;
   - actual connector/API/Git/`gh` permissions.

5. Investigate before editing. Record audit Findings or Architecture Debt when the task
   exposes them.

6. Apply one minimal logical change and update directly affected documentation.

7. Validate syntax, focused behavior, repository hygiene, and the complete diff.

8. Re-read remote `main`. Reconcile only if the base changed materially.

9. Publish one task branch and one Ready PR. Draft is used only for intentional work in
   progress.

10. Keep same-scope repair commits in the same PR. Do not add unrelated work.

11. Require successful checks for the latest mergeable head.

12. Verify expected head SHA, title prefix, scope, checks, and mergeability; squash merge
    once using the exact versioned subject.

13. Verify resulting `main` and remove the task branch.

14. Perform the focused live verification required by the change and record truthful
    evidence. CI/package success never substitutes for owner-appliance evidence.

==================================================
REQUEST SCOPE AND STANDING AUTHORIZATION
==================================================

Interpret owner instructions as follows:

- analyse, diagnose, explain, review, audit: inspect and report without mutation;
- prepare only, patch only, branch only, PR only: perform the requested work and stop at
  that boundary;
- fix, add, change, implement, complete: perform the ordinary branch → Ready PR → CI →
  squash merge → verification cycle;
- publish candidate `vX.Y.Z_N`: publish only the exact authorized testing prerelease and
  asset, without GitHub Pages or pkg-repository promotion;
- release version `X.Y.Z`: perform the complete authorized release pipeline for that
  exact version after its existing product/live gates.

Do not ask for routine branch names, commit/PR wording, test selection, CI inspection,
same-scope repair, Ready state, squash merge, or task-branch cleanup when the source and
documentation make them deterministic.

Stop only on material product/architecture ambiguity, relevant unpublished owner state,
an unresolvable required check, new credentials/protected authority, destructive work on
user data or pre-existing remote objects, force/history rewrite/direct-main publication,
or mandatory live evidence available only from the owner.

==================================================
PACKAGE METADATA
==================================================

Ordinary packaged change:

- keep `VERSION`;
- increment `PLUGIN_REVISION` once.

Governance/documentation/CI-only change outside packaged contents:

- change neither value;
- use the unchanged package-candidate title prefix;
- run path-applicable CI; do not claim or trigger package publication.

Explicit new full release:

- set the requested new `VERSION=X.Y.Z`;
- reset `PLUGIN_REVISION=1`;
- use PR/commit/squash subject `vX.Y.Z_1: Prepare release vX.Y.Z`.

==================================================
GITHUB ORDINARY DELIVERY
==================================================

The exact current candidate prefix is derived from the proposed PR head:

- non-zero revision: `v<VERSION>_<REVISION>:`;
- zero revision: `v<VERSION>:`.

It is required at the start of every PR title, every branch commit subject, and the final
squash subject.

One logical PR normally owns one temporary task branch. Same-scope repair commits are
allowed. Do not create sibling attempts named `-clean`, `-final`, `-fixed`, `-retry`, or
`-publish`. Close/replace a PR only when base, scope, or history is materially wrong or
the approach is abandoned.

Use expected head SHA for merge. Never force-update `main` or published tags.

==================================================
GITHUB FAILURE PROCEDURE
==================================================

Before acting, read the exact failed job log.

1. Same-scope source/documentation/test/title defect:
   repair in the same PR and validate the new head.
2. External GitHub, runner, network, action-distribution, or dependency failure:
   make zero source changes; after recovery, rerun the unchanged failed job/workflow at
   most once.
3. Second unchanged infrastructure failure:
   stop and report the exact log; do not redesign the workflow or create another branch.
4. Wrong PR metadata:
   correct metadata without replacement branch.
5. Wrong base/mixed scope/damaged history:
   record evidence before replacing the PR.

Speculative runner switching, replacement publication branches, duplicate trackers, and
unbounded scheduled retries are forbidden.

==================================================
TESTING PRERELEASE PUBLICATION
==================================================

A testing prerelease makes one approved candidate package available for live validation.
It is not an ordinary code PR and does not publish the pkg repository.

Required procedure:

1. Obtain explicit authority for exact tag `v<VERSION>_<REVISION>` and asset.
2. Inventory existing successful builds, artifacts, releases, and active publication
   runs.
3. When verified package bytes already exist, prefer direct Release API/UI/`gh` upload.
4. Bind reused Actions artifacts by exact workflow run ID, artifact ID/name, expiry, and
   digest.
5. Extract and verify package `+MANIFEST`:
   - exact package version;
   - `FreeBSD:15:amd64` ABI;
   - `freebsd:15:x86:64` architecture.
6. Create the prerelease at the exact intended source commit and attach only the verified
   `.pkg`.
7. Verify target SHA, tag, `draft=false`, `prerelease=true`, asset state, digest or size,
   and direct download URL.
8. Confirm that GitHub Pages and the pkg repository were not deployed.
9. Remove temporary publication branches.

Use `.github/workflows/publish-prerelease.yml` only when automated build-and-publish is
needed. Its only trigger branch is `publish/v<VERSION>_<REVISION>`. It performs FreeBSD
15 build/manifest verification, publishes one prerelease, verifies it, and deletes its
branch. One candidate may have only one active publication run.

==================================================
FULL RELEASE PROCEDURE
==================================================

A full project release remains separate from a testing prerelease.

1. Confirm exact owner authority and satisfied product/live gates.
2. Change `VERSION` to `X.Y.Z`; set revision to `1`.
3. Deliver the release-preparation change through one Ready PR using
   `vX.Y.Z_1: Prepare release vX.Y.Z`.
4. After verified squash merge, `release-trigger.yml` validates that title and creates
   immutable semantic tag `vX.Y.Z` at the merge commit.
5. The full Release workflow builds package and pkg repository from that tag, creates the
   GitHub Release, and deploys Pages.
6. Verify tag target, package, checksums, Release assets, Pages/pkg metadata, and direct
   installation path.

Never move or overwrite a published tag, release, asset, or package version.

==================================================
AUDIT WORKFLOW
==================================================

Inventory the active chain:

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

Classify interfaces as OK, broken, unused, duplicate, inherited, or requires live test.

Every non-OK Finding records stable ID, exact locations, chain, evidence, impact,
verification plan, remediation plan, acceptance criteria, required documentation, and
status. A Finding is recorded before remediation and retained afterward.

Architecture Debt follows:

Open → Discussion → Decision → Implementation → Verification → Documentation → Closed

Dependent implementation waits for the controlling decision.

==================================================
DELIVERING COMMANDS TO OPNsense
==================================================

Present commands in actual order and separate:

1. read-only checks;
2. state-changing installation/publication actions;
3. focused live verification.

OPNsense instructions target root `csh`. If POSIX syntax is required, show standalone
`sh`, then the full POSIX block, then standalone `exit`. Commands after `exit` return to
csh syntax.

Scan for `$(...)`, shell assignments, `export`, `if ...; then`, arithmetic expansion, and
functions before delivery.

==================================================
CURRENT IMPLEMENTATION PRIORITY
==================================================

Strategy Lab corrective source work is complete. The active product gate is the
owner-assisted live matrix.

Testing prereleases may be published only with explicit authority to make a specific
candidate available for that matrix. They do not satisfy the matrix and do not authorize
stable release or pkg-repository promotion.

Do not start unrelated Strategy Lab feature work while required live evidence remains
open.

==================================================
PACKAGE AND RUNTIME VERIFICATION
==================================================

For every affected package candidate distinguish:

1. static source verification;
2. package archive and manifest verification;
3. clean installation;
4. explicit runtime setup;
5. service Start/Status/Restart/Reconfigure/Apply/Stop;
6. upgrade, reinstall, removal, reboot, and controlled failure;
7. exact live acceptance evidence.

Package lifecycle and runtime setup changes are verified as one complete sequence on a
supported OPNsense system. Setup and GUI maintenance reuse the single
`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` backend.

Every result updates the applicable audit/devlog/current-state records. A source or CI
PASS is never reported as a live PASS.

==================================================
LOCAL-ONLY STATE
==================================================

GitHub cannot expose uncommitted or unpushed changes in the owner's OPNsense checkout.
When relevant local-only state exists:

1. stop before editing;
2. ask for commit/push or explicit archive/patch transfer;
3. establish exact transferred baseline and modes;
4. never reconstruct, discard, or overwrite the state from memory.

A clean checkout matching recorded GitHub SHA needs no archive. Unified patches are
optional, not the default repository baseline.
