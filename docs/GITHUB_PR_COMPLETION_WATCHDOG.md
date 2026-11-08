# PR completion watchdog — architecture, history, and reusable installation guide

**Purpose:** Independently monitor pull requests (PRs) for completed, failed, delayed, or stale GitHub Actions checks and notify the responsible developer through deduplicated PR comments. This document is a **portable implementation manual**, not a fifth canonical rule book and not an autonomous PR-merging agent.

**Validated implementation:** `Tolian82/os-zapret2-restyle`, GitHub-native watchdog, initially introduced as `v0.6.2_84`, permission/delivery-hardened in `_90`, and corrected for Actions `jobs` pagination in merged `_125` (`df0cc6e4163a8b7cbb52acfaedf69f59a48d3d4a`); actual live open-PR notification delivery after `_125` was observed on PR #897 and again on PR #948 / failed PR #949. **Reusable with explicit adaptation**; copying these files without the adaptations in §7 is not supported.

**Canonical policy:** [GH-063–GH-065](GITHUB_PUBLICATION.md). **Local operations and incidents:** [project-specific runbook](verification/github-pr-completion-watchdog.md) and [403 investigation](verification/evidence/2026-11-03-v0.6.2_90-watchdog-delivery-403.md). This manual defines no additional normative `GH-*`/`DOC-*` rules.

## _125: Portable lesson — nested GitHub Actions jobs pagination

[Issue #894](https://github.com/Tolian82/os-zapret2-restyle/issues/894) was discovered during #892: the trusted-main watcher rejected `GET /actions/runs/{id}/jobs` because GitHub returns `{"total_count":N,"jobs":[...]}`, not the `{"workflow_runs":[...]}` envelope of `GET /actions/runs` and not the bare arrays of PR/files/comments endpoints. [Scheduled watchdog #41856709938](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41856709938) **FAILED**, with no guaranteed alert delivery. The reusable solution is explicit **endpoint-aware, bounded** pagination (strict `jobs`/`workflow_runs` keys and list members), not a permissive unwrap of arbitrary dict contents or suppression of errors. [Exact _125 evidence](verification/evidence/2026-11-04-v0.6.2_125-watchdog-paginated-jobs-and-actions-stall.md). **Issue #894 was subsequently closed after [a real open-PR READY comment on #897](https://github.com/Tolian82/os-zapret2-restyle/pull/897#issuecomment-6638756282)**, independent of the earlier passing offline tests. See the operational runbook for the current contract and later live alerts.

A workflow remains nonterminal when GitHub reports `in_progress`, even when every reported job **step** is SUCCESS. The stall notification uses the existing 30-minute advisory threshold; it never counts a missing/queued/running/failed workflow as READY, never silently merges, and cannot replace owner authorization. Retain the original trusted-main-only scripts and scheduled fallback. The installed trusted-main push trigger already includes the watcher workflow and **both Python source/test paths**; the separate live notification gate was observed on [#897](https://github.com/Tolian82/os-zapret2-restyle/pull/897#issuecomment-6638756282), and later [#948](https://github.com/Tolian82/os-zapret2-restyle/pull/948#issuecomment-6703929386) and [#949](https://github.com/Tolian82/os-zapret2-restyle/pull/949#issuecomment-6704094405). A created PR comment does **not** prove GitHub email/push delivery.

## 1. Why we created it

The development workflow had repeatedly left pull requests open long after their required CI checks had succeeded. A concrete incident was [PR #849](https://github.com/Tolian82/os-zapret2-restyle/pull/849), which remained open after going green until the developer was prompted again. GitHub Actions can finish independently, but an inactive ChatGPT conversation does **not** awaken or resume work in response to it. A GitHub Issue is a task record, **not** a running monitoring service. Hence, the owner requested a GitHub-hosted monitor that operates even while no assistant conversation is active.

Historical implementation milestones:

1. [Issue #850](https://github.com/Tolian82/os-zapret2-restyle/issues/850) captured the failure and acceptance criteria: detect green-but-open, failed, stalled, stale and wrong-head CI; no auto-merging; do not execute untrusted PR content.
2. [PR #851](https://github.com/Tolian82/os-zapret2-restyle/pull/851), source `_83`, recorded developer completion accountability and the governance contract [GH-063–GH-065](GITHUB_PUBLICATION.md).
3. [PR #852](https://github.com/Tolian82/os-zapret2-restyle/pull/852), source `_84`, installed the independent trusted-main GitHub Actions workflow, Python classifier, unit tests and the first operational guide.
4. [Watchdog run #630](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41643467036) correctly classified [PR #857](https://github.com/Tolian82/os-zapret2-restyle/pull/857) as `READY_FOR_OWNER_REVIEW`, but posting the PR comment failed with HTTP 403. The job had `Issues: write` and `PullRequests: read`; this was an **alert delivery failure**, not a CI-classification failure.
5. [PR #858](https://github.com/Tolian82/os-zapret2-restyle/pull/858), `_90`, added `pull-requests: write`, safe HTTP diagnostic categories, red error annotations with a GitHub Actions job-summary fallback, fewer workflow completion triggers, ten-minute scheduled checking, and one deduplicated closed-PR write probe.
6. [PR #895](https://github.com/Tolian82/os-zapret2-restyle/pull/895) merged the `_125` strict Actions `jobs`-response pagination and fail-closed stalled-run correction. [Issue #894](https://github.com/Tolian82/os-zapret2-restyle/issues/894) closed only after the [actual READY notification for open PR #897](https://github.com/Tolian82/os-zapret2-restyle/pull/897#issuecomment-6638756282); later [READY for #948](https://github.com/Tolian82/os-zapret2-restyle/pull/948#issuecomment-6703929386) and [CHECK_FAILED for #949](https://github.com/Tolian82/os-zapret2-restyle/pull/949#issuecomment-6704094405) also reached PR discussions.
7. The [closed-PR #857 write probe](https://github.com/Tolian82/os-zapret2-restyle/pull/857#issuecomment-6605845176) was delivered by [main watchdog run #41649845549](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41649845549). The first **real open PR** confirmation came on [PR #859](https://github.com/Tolian82/os-zapret2-restyle/pull/859#issuecomment-6606678272): `READY_FOR_OWNER_REVIEW`, exact head `63f673b3edd274de0ac137ebed2eb57ed1341956`, all **19** applicable workflows passed, in [watchdog run #41655639819](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41655639819). The developer, **not the watchdog**, then merged #859.

## 2. Components and source of truth

| Component | Canonical repository file | Role |
| --- | --- | --- |
| Scheduler and permissions | [`.github/workflows/pr-completion-watchdog.yml`](../.github/workflows/pr-completion-watchdog.yml) | Run GitHub Actions from trusted default branch on selected CI completion, schedule, manual dispatch and workflow-change push; grant narrowly needed API scopes |
| Read-only classifier and notifier | [`scripts/github_pr_watchdog.py`](../scripts/github_pr_watchdog.py) | Discover owner-managed open PRs, derive applicable checks from trusted workflow files, evaluate exact-head status, deduplicate and send comments |
| Runnable regression suite | [`scripts/test_github_pr_watchdog.py`](../scripts/test_github_pr_watchdog.py) | Validate state transitions, path filters, stale SHA, rate/permission errors, security and write delivery behavior |
| Repo-specific operations | [`docs/verification/github-pr-completion-watchdog.md`](verification/github-pr-completion-watchdog.md) | Local trigger configuration, incident-specific smoke, support workflow |
| Governing requirements | [`docs/GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) | GH-063 (Issues are not agents), GH-064 (developer must complete PR), GH-065 (independent alerts, real delivery verification) |

**Key separation:** the GitHub workflow is the always-available *platform service*; Python performs a bounded check only during a run; GitHub persists PR comments and run summaries; a person or separately authorized agent performs any repair/review/merge. There is **no resident daemon**, external server, or requirement to leave a chat open.

## 3. When it runs

Current `.github/workflows/pr-completion-watchdog.yml` has four triggers:

- **`workflow_run`**: only when a PR-triggered workflow **named `CI`** completes. This limits fanout; the initial design listened to many specialized workflow completions and generated numerous redundant/cancelled jobs.
- **`schedule`**: GitHub cron `7 * * * *`, an **hourly** fallback (GH-070, 8 November 2026; previous ten-minute cron is historical). GitHub Actions schedules are best effort: heavy load, disabled Actions, or account/repository restrictions can delay or suppress runs. There is **no strict ten-minute SLA**.
- **`workflow_dispatch`**: manual on-demand diagnosis or recheck.
- **`push`** to `main` when **any of these three paths** changes: `.github/workflows/pr-completion-watchdog.yml`, `scripts/github_pr_watchdog.py`, or `scripts/test_github_pr_watchdog.py`. This qualifies deployment/source or test-only edits without waiting for a schedule; unrelated product commits do not trigger this path.

The workflow has one serialized concurrency group `pr-completion-watchdog-${{ github.repository }}` with `cancel-in-progress: false`; its job has a 15-minute timeout. The workflow-run job is gated to `github.event.workflow_run.event == 'pull_request'`. Only a single triggering workflow is needed because **the classifier reads all applicable workflow results**, while the schedule detects specialized jobs finishing later than `CI`.

GitHub's automatic `GITHUB_TOKEN` is passed as `GH_TOKEN`, and the exact repository as `GH_REPOSITORY`. The job checks out **only** `github.event.repository.default_branch` with `persist-credentials: false`; it must never check out the PR head, evaluate a PR-supplied script, or treat PR title/body as trusted executable content.

## 4. How classification actually works

One run of `scripts/github_pr_watchdog.py` executes these stages:

1. **Discover** up to the configured pagination limit of `GET /repos/{owner}/{repo}/pulls?state=open&base=main`. Only open, **same-repository** head branches targeting `main` are considered. Fork PR heads are deliberately excluded.
2. **Pin the current PR SHA and scope:** refresh `GET /pulls/{number}`, read `GET /pulls/{number}/files`, and derive the expected GitHub workflow names dynamically from **trusted default-branch** `.github/workflows/*.yml` definitions with `on: pull_request`, their base-branch and path filters. This avoids a fragile hardcoded count such as 16 or 19.
3. **Inspect actual runs** through `GET /actions/runs?event=pull_request&head_sha={sha}`, selecting the latest attempt per workflow **for exactly the PR head**. Previous green commits or cancelled, skipped, missing, neutral, timed-out, or unsuccessful current runs **never** count as green. Read job/step timestamps through `GET /actions/runs/{run_id}/jobs` when checking progress.
4. **Classify the PR:** merge conflicts or stale base, failed required workflows, missing/running required workflows, a possible stall after approximately **30 minutes without relevant job/step progress**, or completed-success on **every** applicable current-head check with a ready, mergeable, non-draft PR.
5. **Alert only for actionable states**, by checking existing `GET /issues/{number}/comments` for the unique watchdog marker plus the **exact head SHA and state**. Refresh the PR head/state once more before `POST /issues/{number}/comments`. An existing matching comment prevents repeated cron alerts.
6. **Record delivery status:** every candidate gets a sanitized Actions job-summary entry. A successful POST means `COMMENT_POSTED`; already sent means `ALREADY_NOTIFIED`; head changed means `HEAD_CHANGED_SKIP`. A POST HTTP error leaves a **red workflow**, a fixed diagnostic classification and an Actions error annotation. Never equate a computed `READY` state or a job summary with successful delivery.

State meanings (these names are implementation contracts, not GitHub-native PR statuses):

| State | Detection | PR comment? |
| --- | --- | --- |
| `CI_IN_PROGRESS` | Missing/running checks not yet deemed stalled; Draft/not-yet-mergeable also cannot be READY | No |
| `CHECK_FAILED` | Latest exact-head required workflow failed, was cancelled, skipped, timed out or otherwise not successful; unsupported policy may also trigger this fail-closed state | Yes, once per SHA/state |
| `CHECK_STALLED` | Required checks missing too long or no relevant job/step progress for about 30 minutes | Yes, advisory |
| `STALE_BASE` | GitHub reports merge conflict or out-of-date base | Yes |
| `READY_FOR_OWNER_REVIEW` | Every applicable latest-head workflow completed successfully; open non-draft PR is mergeable | Yes, once per SHA/state |

**Non-goals and correctness limits:** The watchdog checks GitHub Actions workflow completion and its own restricted policy parser. It is **not** a substitute for all possible branch-protection status contexts, signed commits, mandatory reviews, package safety or human authorization. The 30-minute stall is a *signal to inspect*, not proof a runner is permanently dead. The final PR re-read narrows but cannot make GitHub comment posting and head mutation one atomic operation.

## 5. GitHub token permissions and safe error handling

At the current tested deployment the workflow requests:

```yaml
permissions:
  contents: read
  actions: read
  issues: write
  pull-requests: write
```

`issues: write` alone **did not suffice in one observed run**: [#630](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41643467036) got HTTP 403 posting to a PR's Issues-comments API even though the runner received it. Adding `pull-requests: write` was followed by **successful real writes** on closed #857 and open #859. This strongly supports the practical remediation but the original 403's exact GitHub-side cause was not conclusively identified; rate/policy/integration restrictions can also cause 403.

On an API failure, the implementation maps a bounded error body and allowlisted headers into `GITHUB_API_REFUSAL_{code}_INTEGRATION_ACCESS_DENIED`, `_SECONDARY_RATE_LIMIT`, `_PRIMARY_RATE_LIMIT`, or `_AUTHORIZATION_OR_POLICY` (plus safe request ID, accepted-permission hints and bounded Retry-After where available). **Raw GitHub error bodies, credentials, PR bodies/titles and runner secrets must never be written to logs or comments.** This classification is diagnostic, not a retry loop. A failure stays red and retains an inspectable `GITHUB_STEP_SUMMARY`, **not** a guaranteed push notification.

Security assumptions: trusted workflow source on protected default branch, untrusted open PR metadata treated as data, no arbitrary commands from PR, scope-limited token, GitHub Actions enabled, and no `merge`/approve/label/release/product/package/device mutation endpoint. The script reads current PR metadata, but its privileged write surface is **only** a deduplicated timeline comment.

## 6. Portability dependencies and limitations

This is **not a generic drop-in that works unchanged in every repository**. The current program intentionally contains project-specific policy:

| Source | Current assumption | Required adaptation in another project |
| --- | --- | --- |
| `scripts/github_pr_watchdog.py` | Base branch string `main` in API query, scope check and PR trigger-policy parser | Use the destination's real protected default/target branch and update unit tests consistently |
| Same Python file | At least one applicable workflow has literal name **`CI`** | Ensure a `pull_request` workflow named `CI` exists, or adapt `expected_workflows()` and tests to a different trusted required anchor |
| Same Python file | Only same-repository PR heads are monitored | Decide explicitly whether forks are in scope; **do not** enable running/privileging fork code without a security design |
| Same Python file | Supports workflow files ending `*.yml` with a restricted `on: pull_request`/`branches`/`paths`/`paths-ignore` subset, and restricted glob patterns | Audit every destination workflow's YAML trigger; extend the parser and tests **fail-closed** for any unsupported syntax, `.yaml`, complex globs, dynamic workflow dispatch, reusable workflows or custom rules; never silently ignore mandatory checks |
| `workflow_run` YAML | Watches only a workflow whose GitHub Actions display name is `CI` | Change that string to the destination's actual anchor workflow; keep the schedule for other checks finishing later |
| Workflow YAML | `push.branches: [main]` with the **workflow plus both watchdog Python paths** in `push.paths` | Adapt to destination default branch and paths; keep trusted-main-only checkout |
| Python file | `User-Agent` and markers use `zapret2` naming | Change to a unique destination marker and app identifier to avoid mixing historical comments or audits |
| Python file | A historical one-time deployment smoke is **hardcoded to already merged PR #857** | **Remove `smoke_original_pr_delivery(api)` and its `__main__` invocation when porting**, together with project-only marker/test, **or** replace with a newly reviewed, one-shot destination-specific test for an already-merged harmless PR. NEVER leave #857 hardcoded in a different repo |
| Source tests | Include exact original workflow path, marker, setup, comments and 403 smoke expectations | Update these fixtures to destination paths and the adapted workflow policy before declaring tests green |
| Page/job API | Bounds pagination at 10 × 100 records and API timeout to 25 seconds per request | Check scale/number of PRs/workflow runs and add bounded capacity/cost controls where needed |

Also verify Actions permissions and repository/org policies for `GITHUB_TOKEN`, workflow approval, commenter permissions, schedule execution, GitHub-hosted runners, and notifications/subscriptions. A GitHub installation or a new Issue does **not** automatically activate a watchdog.

## 7. Recreate it in another repository: step-by-step

**Prerequisites:** a GitHub repository with Actions enabled, protected trusted default branch (examples below use `main`), a `pull_request` CI workflow, permission to add workflows, and permission for the workflow token to post PR timeline comments.

1. **Establish the intended behavior and policy.** Decide which PRs count as owner-managed, which branch they target, exact required workflow names and path filters, expected actionability/stall threshold, notification recipient/subscriptions and whether to exclude forks. Require no unauthorized merge or untrusted PR execution.
2. **Copy the three current implementation files** from the pinned reference repository into a task branch of the destination repository, preserving the relative layout (or update paths/imports if changing it). Use GitHub's downloaded file contents at one **immutable source commit**, rather than separately copying moving `main` revisions:

   ```sh
   # Run inside a clone of the DESTINATION repository. Replace source SHA
   # with a verified immutable commit of Tolian82/os-zapret2-restyle.
   SOURCE_SHA=df0cc6e4163a8b7cbb52acfaedf69f59a48d3d4a
   SRC=https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/$SOURCE_SHA
   mkdir -p .github/workflows scripts
   curl -fL "$SRC/.github/workflows/pr-completion-watchdog.yml" -o .github/workflows/pr-completion-watchdog.yml
   curl -fL "$SRC/scripts/github_pr_watchdog.py" -o scripts/github_pr_watchdog.py
   curl -fL "$SRC/scripts/test_github_pr_watchdog.py" -o scripts/test_github_pr_watchdog.py
   ```

   **IMPORTANT:** the pinned example SHA is the immutable **merged `_125` jobs-envelope and real-standstill correction**, not a claim of the newest upstream head. Before committing, inspect and adapt the downloaded code. Source paths, security review and tests are authoritative; `curl` success is not acceptance.
3. **Remove project-specific historical smoke and rename markers.** The code at this source SHA calls `smoke_original_pr_delivery(api)` for merged PR #857 on matching main push. Delete this function, its `DELIVERY_SMOKE_MARKER`, the call in `__main__`, and the associated tests; or replace them with an explicitly reviewed destination-specific one-time smoke that cannot modify unrelated PRs. Select a project-unique comment marker and adjust tests.
4. **Adapt the base/CI/workflow policy.** Replace literal `main` where semantically required, update workflow `CI` display name and parser's mandatory CI anchor if appropriate, verify `.yml`/`.yaml` filename coverage, path glob semantics, trigger-policy coverage, fork scope and the intended set of mandatory checks. Unsupported workflow policies must cause **non-ready**, never silent success.
5. **Configure least required permissions.** Keep `contents: read`, `actions: read`, `issues: write`, `pull-requests: write` as observed to work with the PR timeline endpoint; avoid extra release/deployment/admin privileges. Keep `checkout` pinned to trusted default branch, `persist-credentials: false`, `workflow_run` limited to PR-origin `CI`, and bounded schedule/concurrency.
6. **Run fast regression tests before opening a PR.** The delivered code requires Python 3.13 in its workflow; the standard-library tests are runnable with the matching Python installed:

   ```sh
   python3.13 -m py_compile scripts/github_pr_watchdog.py scripts/test_github_pr_watchdog.py
   python3.13 scripts/test_github_pr_watchdog.py -v
   git diff --check
   ```

   Ensure tests cover exact-head success, failed, cancelled, skipped, missing, stale base, Draft, stalled, duplicate comments, simulated 403/rate limits and refusal to run PR code. Do not claim a test passed merely because it exists.
7. **Open a normal reviewed PR for installation** and require all applicable checks on its actual head SHA. On merge, verify the workflow file is on the real default branch. Merely placing it in a PR **does not deploy it**. A workflow listening for updates to its own file should run a trusted-main initial scan; if no open PR exists, that proves invocation only.
8. **Verify real comment delivery.** After installation, use a harmless controlled open PR with known required checks; deliberately exercise non-ready then green conditions. Confirm the bot posts one `READY_FOR_OWNER_REVIEW` comment **for the correct current head** and does not repeat it on the next schedule. An optional carefully scoped one-time closed-PR smoke can verify the write endpoint first; that smoke alone does not prove live open PR alerts.
9. **Exercise failure and recovery.** On a test PR (never deliberately degrade production CI), simulate/mock failed, stalled, old-head and permission-denied cases; confirm errors produce red Actions+summary and no false READY. Confirm a subsequent new head reclassifies and gives a separate notification. Verify watcher does not merge or change the target repository.
10. **Make operation durable.** Link this guide and the destination runbook in its documentation index; assign human ownership for failed or stalled PRs, monitor schedule/workflow settings and GitHub notifications. Keep `GH-064`-equivalent developer completion responsibility independent of this automation.

**Suggested installation acceptance matrix:**

| Test | Expected evidence |
| --- | --- |
| No open PRs | Run succeeds; output has `open_managed_prs: 0`, `alerts_posted: 0`; no comment is sent |
| Open PR, required checks still active | Classified `CI_IN_PROGRESS`, no premature READY |
| All relevant current-head checks successful | Single `READY_FOR_OWNER_REVIEW` comment containing exact SHA and number of expected workflows |
| Same state/head, repeated scheduled run | `ALREADY_NOTIFIED`; no extra comment |
| New commit pushed to PR | Old-head green ignored; recheck new SHA before READY |
| Cancelled/skipped/failed or missing required check | `CHECK_FAILED` or `CI_IN_PROGRESS`/`CHECK_STALLED`, never READY |
| Stale/dirty base, Draft, unknown mergeability | Correct advisory or non-READY state; no merge |
| Comment endpoint HTTP 403/429 | Red Actions job, safe error category, request ID if available, meaningful GitHub job summary; do **not** claim delivery |
| Actual open PR alert | Comment can be opened and its SHA/current-head/readiness verified in GitHub; no duplicates |

## 8. Troubleshooting and observability

- **No watcher run:** confirm the workflow is committed in the **default branch**, Actions/schedules enabled, event name exactly matches `CI`, the upstream workflow is `pull_request`-origin, and the workflow's `if` condition is satisfied. Manual `workflow_dispatch` helps isolate trigger vs classifier faults.
- **A PR is green in the UI, but no READY alert:** compare the head SHA and source PR's applicable workflow list; a missing specialized workflow, GitHub mergeability `null`, Draft, outdated base or late specialized check can legitimately prevent READY. The schedule is the fallback if specialized tests finish after the common CI. Check the job summary, not only the green/red workflow icon.
- **Many duplicate/cancelled watcher runs:** subscribe `workflow_run` to the single CI anchor, not every long-running workflow. Inspect concurrency group; retain periodic fallback and comment-level SHA/state deduplication.
- **HTTP 403 on PR comment despite `issues: write`:** inspect effective `GITHUB_TOKEN Permissions` in the runner header, include **`pull-requests: write`**, then read the sanitized category (`INTEGRATION_ACCESS_DENIED`, `SECONDARY_RATE_LIMIT`, etc.) and request ID. Check repository/org token restrictions and retry limits. No API token must be pasted into an issue/chat. Refusal remains RED.
- **The watcher itself is green, but owner did not receive an external notification:** a posted GitHub PR comment and an email/push notification are different. Check owner watching/subscription and notification preferences. GitHub does not guarantee email/push delivery, and a summary shown only inside Actions is not an alert.
- **Task stuck OPEN after watchdog posts READY:** this is expected unless a developer/reviewer actually continues the process. The watchdog is a *reporting instrument*, not an autonomous agent. The developer checks current main/revision, approvals, all required gates, performs merge and verifies post-merge main/branch cleanup.
- **Cannot parse a destination workflow:** fail closed. Extend `workflow_policy()` and its regression tests to support the destination's actual YAML, rather than removing difficult workflow checks from expected coverage.

## 9. Operational maintenance and change discipline

Monitor the workflow's Actions history, PR notification comments, scheduled execution and GitHub permissions after major repo/organization changes. Keep the actual workflow, classifier and tests in **one reviewed change** when modifying behavior; run fast contracts before long CI, then prove at least one real latest-head alert after deployment. Avoid recurring blind retries, unlimited API pagination and secrets in diagnostics. Evaluate other notification sinks (Issues, labels, external messaging) only as a separately authorized capability with audited permissions and delivery tests.

**Project-specific completion rule:** installing this monitoring infrastructure is a documentation/CI scope, not a product package release. In `Tolian82/os-zapret2-restyle`, `DEV-032`/`DEV-033` require the next `PLUGIN_REVISION` for a merged documentation-only change, but **do not** imply new `.pkg` publication or owner-appliance changes. Other projects should apply **their own** revision/release policy instead of copying ours by assumption.

## 10. Evidence and further reading

- [Original Issue #850](https://github.com/Tolian82/os-zapret2-restyle/issues/850), [governance PR #851](https://github.com/Tolian82/os-zapret2-restyle/pull/851), [initial watcher PR #852](https://github.com/Tolian82/os-zapret2-restyle/pull/852).
- [Observed 403 run #630](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41643467036), [fix PR #858](https://github.com/Tolian82/os-zapret2-restyle/pull/858), [written closed-PR #857 smoke comment](https://github.com/Tolian82/os-zapret2-restyle/pull/857#issuecomment-6605845176).
- [Real open PR #859 READY comment](https://github.com/Tolian82/os-zapret2-restyle/pull/859#issuecomment-6606678272), [successful watcher #41655639819](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41655639819).
- [GitHub Actions `workflow_run`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run), [GitHub REST issue-comment endpoint](https://docs.github.com/en/rest/issues/comments#create-an-issue-comment), [GitHub Actions `GITHUB_TOKEN` permissions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication).
