# DEC-2026-08-06 — Evidence-first GitHub operations

Status: Active
Date: 2026-08-06

## Context

Publication of prerelease `v0.3.3_4` exposed a repeatable process defect. A verified
FreeBSD 15 package already existed, but publication was repeatedly redesigned through
new branches, pull requests, workflows, runner changes, and scheduled retries. The first
external GitHub Actions outage was real, but the follow-up actions multiplied workflow
runs and branch clutter without increasing the probability of a correct publication.
The successful publication was finally completed by attaching the already verified
package directly to a prerelease targeted at the exact source commit.

A second repeatable defect was also confirmed: repository work became unreliable when
the connected GitHub plugin was not used as the first authoritative interface. Chat
memory, generic API calls, and improvised transports hid available repository state and
encouraged duplicate or mistimed operations.

The connector audit also established a required distinction between a missing plugin
function and plugin unavailability. At the 2026-08-07 verification, the repository
returned no configured rulesets, while the plugin installation returned
`403 Resource not accessible by integration` for repository Actions-permission settings
and branch-protection settings. The `403` proves a connector permission boundary only;
it does not prove that those GitHub controls are disabled. These time-sensitive facts
must be re-verified before later use.

The audit found these conflicting active rules and mechanisms:

| Topic | Conflicting source | Resolution |
|---|---|---|
| Repository transport | GitHub plugin was not consistently used first | use the connected GitHub plugin first; another transport is allowed only for the exact function or permission confirmed missing from a responding plugin |
| Plugin outage | fallback wording did not distinguish a missing function from an unavailable plugin | plugin unavailability stops all GitHub work; inform the owner and wait for explicit direction instead of switching transports automatically |
| PR state | `WORKING_CONVENTIONS.md` and `DEVELOPMENT_GUIDE.md` still required Draft | Ready is the default when content is ready; Draft is optional work-in-progress state |
| Branch commits | older rules required one atomic branch commit | one logical PR may contain same-scope repair commits; `main` receives one squash commit |
| Context preflight | older decisions required a complete reread before every response | use the risk-based preflight in `AGENTS.md`; full repository-wide recovery is required only when scope warrants it |
| Release squash title | `release-trigger.yml` expected unversioned `release: prepare vX.Y.Z` | release preparation uses the universal candidate prefix `vX.Y.Z_1: Prepare release vX.Y.Z` |
| Documentation-only CI | older text claimed the package job always runs | applicable path-gated CI is authoritative; package build is required only when package inputs change |
| Testing prerelease | older priority wording blocked every tag/asset before the live matrix | a testing prerelease may be published after exact owner authorization; stable release and pkg-repository promotion remain blocked |
| Candidate publication | version-specific workflows and publication PRs were used | publish an already verified artifact directly through Release API/UI/`gh`; otherwise use one generic prerelease workflow |
| Infrastructure failure | repeated runner/workflow changes followed external failure | read the job log first; external failure causes no source change and permits at most one unchanged rerun after recovery |
| Prose enforcement | exact wording and line placement were proposed as shell-test invariants | keep the operational rule in authoritative documentation; do not make wording or line placement a CI contract |

## Decision

### GitHub plugin first

- Use the connected GitHub plugin as the mandatory first interface for every repository
  inspection and mutation.
- Inspect the plugin's actual functions and permissions before declaring an operation
  blocked or selecting another transport.
- Use authenticated Git, `gh`, the web UI, or another API only when the plugin is
  responding and for the exact operation whose required plugin function or permission
  is confirmed absent.
- The fallback covers only that missing operation. Return to the GitHub plugin
  immediately for subsequent repository inspection and supported mutations.
- If the GitHub plugin stops responding, is unavailable, or cannot provide the
  authoritative repository state required to proceed safely, stop all GitHub work.
  Inform the project owner and wait for explicit direction. Do not continue through a
  fallback transport, automation, or scheduled tracker merely to preserve momentum.
- Chat history, web search, generic HTTP requests, and assumptions about the GitHub UI
  are not substitutes for plugin reads of current repository state.
- The plugin-first rule is maintained as project documentation, not as an exact-line or
  exact-wording assertion in a shell test.

### Pre-mutation inventory

Before any GitHub mutation, inspect through the GitHub plugin the exact current:

- `main` SHA and candidate metadata;
- relevant open and closed pull requests;
- task, publication, recovery, and owner branches;
- workflows capable of performing the operation;
- active, queued, failed, and successful workflow runs;
- tags, releases, assets, and reusable build artifacts;
- connector/plugin, ordinary Git, `gh`, and UI capabilities and permissions.

Do not create a new mechanism until the inventory proves that no existing mechanism
safely covers the operation.

### Ordinary code and governance delivery

- One logical scope uses one task branch and one pull request.
- Ready is the default PR state when the diff is ready for review and merge.
- Same-scope repairs remain in the same branch and PR.
- Every PR title, PR-branch commit subject, and final squash subject keeps the exact
  package-candidate prefix.
- Required checks gate only the latest mergeable PR state.
- Merge uses the expected head SHA and squash method.
- `main`, published tags, and published assets are never force-moved or rewritten.

### Candidate prerelease publication

Publication of an already verified candidate is a release operation, not a code PR.

1. Confirm exact owner authorization for the candidate tag and asset.
2. Prefer direct Release API/UI/`gh` upload when the verified package bytes already
   exist and their identity can be checked.
3. Reuse an immutable Actions artifact only by exact run ID, artifact ID/name, and
   digest; recheck the package `+MANIFEST` before publication.
4. Use the generic `.github/workflows/publish-prerelease.yml` only when repository-owned
   build-and-publish automation is actually needed.
5. Permit only one active publication run for a candidate.
6. A publication branch is temporary and does not receive a pull request.
7. Verify after publication: target commit SHA, tag, `draft=false`, `prerelease=true`,
   asset name, asset digest/size, and direct download URL.
8. A testing prerelease publishes neither GitHub Pages nor the pkg repository.
9. Remove the temporary publication branch after successful verification.

### Failure handling

- Read the exact failed job log through the GitHub plugin before changing source,
  workflow, runner, or branch.
- Same-scope source defects are repaired in the same PR.
- An external GitHub, runner, network, or action-distribution failure causes zero source
  changes. After the service recovers, at most one unchanged failed-job/workflow rerun
  is allowed.
- Do not switch runner operating systems, create `-final`/`-retry`/replacement branches,
  or introduce a new workflow without evidence that the current workflow is defective.
- A second unchanged infrastructure failure stops the operation for explicit diagnosis;
  it does not authorize further experiments.
- Scheduled monitoring must be bounded and unique. Duplicate trackers and unbounded
  automatic retries are forbidden.
- GitHub-plugin unavailability stops the entire GitHub operation and must be reported to
  the owner; it does not authorize an automatic fallback.

### Release preparation

A real project release remains separate from a testing prerelease. A release that changes
`VERSION` to `X.Y.Z` and resets `PLUGIN_REVISION` to `1` uses:

`vX.Y.Z_1: Prepare release vX.Y.Z`

The release trigger validates that versioned subject, creates the immutable semantic tag
`vX.Y.Z`, and dispatches the full Release workflow. Stable release and pkg-repository
promotion still require their existing product and live-verification gates.

## Priority and supersession

This decision has priority for GitHub transport selection, mutation, failure handling,
candidate prerelease publication, and release-preparation title mechanics.

It amends `DEC-2026-08-05-efficient-github-delivery.md` without changing its compatible
outcomes: one logical PR, same-scope repair in place, latest-head CI, squash merge,
expected head SHA, and no force-update of `main`.

It preserves `DEC-2026-08-05-universal-versioned-github-titles.md` and extends its
release-preparation application.

It supersedes conflicting active wording in:

- `docs/DECISIONS.md` entries that require mandatory Draft PRs, one branch commit,
  full-document rereading for every operation, or the unversioned release subject;
- GitHub sections of `docs/WORKING_CONVENTIONS.md` and `docs/DEVELOPMENT_GUIDE.md`;
- any version-specific prerelease publisher stored in `main`;
- any rule that permits bypassing an available GitHub-plugin operation without first
  checking the plugin;
- any rule that treats plugin unavailability as permission to continue automatically
  through another transport;
- any rule that treats external infrastructure failure as permission to alter source,
  runner, workflow, or branch without supporting evidence;
- any rule that makes the exact wording or line placement of the plugin-first prose a
  shell-test or CI invariant.

Historical records remain immutable evidence and are not deleted merely for cosmetic
cleanup.

## Affected controls

- `AGENTS.md`;
- `docs/INDEX.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/PROJECT_STATE.md`;
- `docs/devlog/2026-08-06-evidence-first-github-operations.md`;
- `.github/workflows/ci.yml`;
- `.github/workflows/publish-prerelease.yml`;
- `.github/workflows/release-trigger.yml`;
- `scripts/test-github-branch-hygiene.sh`;
- `scripts/test-release-trigger.sh`.
