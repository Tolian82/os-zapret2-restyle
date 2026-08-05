# GitHub publication and delivery discipline

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is one logical change delivered safely and efficiently through GitHub?

Purpose:
Define the authoritative branch, pull-request, CI, repair, merge, cleanup, patch, and
release procedure. This document describes required outcomes, not one mandatory client
or low-level API implementation.

Read immediately before any GitHub mutation.

==================================================
CORE OUTCOMES
==================================================

A normal delivery must produce:

- one clearly bounded logical pull request;
- a reviewable final diff;
- successful required checks for the latest mergeable PR state;
- one squash commit in `main`;
- verified resulting `main` state;
- no force-update or accidental mutation of unrelated refs;
- cleanup of the temporary task branch when the available repository mechanism permits.

The branch may contain multiple same-scope work and repair commits. Squash merge provides
one permanent logical commit in `main`. Commit count and historical workflow-run count are
not correctness metrics.

==================================================
CAPABILITY AND TRANSPORT DISCOVERY
==================================================

Before declaring publication blocked, inspect the capabilities and permissions actually
available in the current environment.

Preferred mechanism by operation:

- repository, PR, issue, review, status, and merge metadata: connected GitHub app/API;
- local editing, syntax tests, staging, and work commits: local checkout and ordinary
  `git` when available;
- commit construction without a checkout: Git data API when it is the practical safe
  transport;
- Actions jobs and logs: connected GitHub app/API, then `gh` when needed and available;
- tags, releases, and assets: repository release workflow, GitHub app/API, or `gh`;
- repository settings and protection: GitHub settings/API with verified administrative
  authority.

No particular client is a permanent project requirement. Missing `gh` alone is not a
blocker when another authenticated mechanism covers the operation. Conversely, do not
claim a connector can perform an operation until its actual function and permission have
been verified.

Low-level blob/tree/commit construction is an optional transport-specific method, not a
project architecture rule.

==================================================
NORMAL DEVELOPMENT FLOW
==================================================

1. Resolve the exact owner instruction and stopping boundary.
2. Read current `main`, current relevant PRs, and the specialist documentation.
3. Record the base SHA and confirm whether relevant owner-local state is unpublished.
4. Prepare one logical change and its directly affected documentation.
5. Run focused validation and review the complete diff.
6. Create or use one task branch for that logical PR.
7. Publish the change and open one Ready PR when the content is ready for review and
   merge. Use Draft only for intentional work in progress or early design discussion.
8. Let required checks evaluate the latest PR state.
9. Repair same-scope failures in the same branch and PR when safe.
10. Before merge, verify scope, mergeability, required checks, and exact expected head
    SHA.
11. Squash merge once.
12. Verify the resulting `main` commit and relevant post-merge/release workflows.
13. Remove the temporary branch through repository-native deletion or the documented
    fallback and verify repository hygiene.

An ordinary request to fix, add, change, implement, or complete authorizes this complete
cycle unless the owner explicitly stops at analysis, patch, branch, or PR.

==================================================
BRANCH AND PR RULES
==================================================

- One logical PR normally owns one temporary task branch.
- Do not create sibling branches merely to rename attempts as `-clean`, `-final`,
  `-atomic`, `-fixed`, `-retry`, or `-publish`.
- A valid PR is not abandoned merely because one check failed.
- A branch may receive same-scope repair commits. Do not add unrelated work while checks
  or review are in progress.
- Close and replace a PR only when its base, scope, or history is materially wrong, the
  intended change is abandoned, or safe repair in place is impossible.
- Ready means the content is ready to merge once gates pass. It does not mean CI has
  already finished.
- Draft is not a mandatory staging state.
- Use an expected head SHA for merge so GitHub rejects a race if the PR moved.
- Never force-push `main`, move a published tag, or delete a pre-existing owner branch.

A long corrective programme may use multiple dependent PRs. A successor may be analyzed
or prepared while its predecessor is in CI, but it must not be merged against an
unintegrated prerequisite. Independent PRs may proceed concurrently when their scopes do
not conflict.

==================================================
CI AND CHECK SEMANTICS
==================================================

The merge gate is the required result for the latest mergeable PR state.

Rules:

- Historical failed, canceled, or superseded workflow runs remain evidence but do not
  invalidate a later successful head.
- Updating a PR with a same-scope repair legitimately creates a new check set.
- Retry only failed jobs when an infrastructure or transient failure makes that safe.
- Configure PR workflow concurrency so a newer head cancels obsolete in-progress runs.
- CI is a barrier to merge, not a command to stop all independent analysis or
  preparation.
- Do not stack unrelated changes into a checked branch merely to keep working.
- A product/package PR should perform the meaningful package build once before merge.
- Documentation/governance-only PRs should not consume a FreeBSD package build unless a
  packaging input is affected.
- `main` push validation should be a lightweight integrity check; do not duplicate the
  complete expensive PR package build after every squash merge.

Never claim a check passed unless the exact workflow/job result was inspected.

==================================================
FAILURE HANDLING
==================================================

Classify a failure before acting:

1. Same-scope source or test defect:
   repair in the same PR and rerun checks for the new head.
2. Transient runner, network, dependency, or GitHub failure:
   rerun the failed job or workflow when no source change is required.
3. Incorrect title or PR metadata:
   correct the metadata and allow its targeted check to rerun.
4. Incorrect base, mixed scope, damaged history, or abandoned approach:
   close or replace the PR after recording why.
5. Required protected authority or credentials unavailable:
   stop at the exact boundary and report the evidence once.

Do not create replacement branches as a reflex. Preserve the PR discussion and check
history when the logical change remains valid.

==================================================
MERGE AND CLEANUP
==================================================

Preferred repository configuration:

- squash merge enabled as the normal method;
- merge-commit and rebase methods disabled when practical;
- required checks and pull requests enforced for `main`;
- force push and deletion of `main` prohibited;
- auto-merge enabled;
- automatic deletion of merged head branches enabled.

When repository-native auto-merge is available, enable it only after the PR is Ready,
scope is reviewed, and the intended squash title is known. Otherwise merge explicitly
after checks pass.

When repository-native branch deletion is unavailable, use
`.github/workflows/cleanup-merged-branch.yml` as the same-repository fallback.

Branch cleanup failure is a repository-hygiene defect. Diagnose and clean it, but do not
misreport an already verified squash merge as an unsuccessful code delivery.

==================================================
TITLE AND COMMIT POLICY
==================================================

Packaged changes may use:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

Governance, documentation, or CI-only changes outside packaged plugin contents may use a
clear conventional title such as:

- `governance: <change>`;
- `docs: <change>`;
- `ci: <change>`;
- `chore: <change>`.

The final squash title must describe the logical change. Package-candidate prefixes are
required only when the PR actually advances or represents packaged plugin behavior.

==================================================
PATCH VERSUS RELEASE
==================================================

Ordinary packaged patch:

- keep `VERSION` unchanged;
- increment `PLUGIN_REVISION` once;
- merge the logical change;
- create no tag, GitHub Release, release asset, or pkg-repository publication.

Governance/documentation/CI-only change outside packaged plugin contents:

- change neither `VERSION` nor `PLUGIN_REVISION`;
- run applicable validation;
- do not imply a release.

Project release:

- requires explicit authority for an exact new `VERSION`;
- changes `VERSION` and resets `PLUGIN_REVISION` to `1`;
- continues through the repository release trigger, tag, GitHub Release, assets, Pages,
  pkg repository, and post-publication verification;
- never moves or overwrites an already published version.

Ambiguous continuation language does not independently authorize a new release version.

==================================================
CONCURRENCY AND LOCAL STATE
==================================================

The recorded base SHA is a concurrency guard, not a ban on parallel thought.

- Reconcile before merge when `main` changes materially.
- Independent branches may proceed concurrently.
- Dependent work may be prepared separately but must integrate in prerequisite order.
- Relevant uncommitted or unpushed owner state cannot be recovered from GitHub. Ask for
  that state only when it materially affects the requested scope.

==================================================
SUPERSESSION
==================================================

This document and
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` supersede conflicting active
or historical wording that required:

- a final commit before any task branch may exist;
- exactly one source commit inside a PR branch;
- exactly one complete check set or workflow run;
- closing and replacing a valid PR after an ordinary CI failure;
- waiting for every check before beginning unrelated analysis or separate preparation;
- mandatory Draft → Ready transitions;
- low-level Git data API construction for every change;
- cleanup success as a condition for the truth of an already completed merge.
