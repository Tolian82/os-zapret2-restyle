# GitHub PR completion watchdog — operational and security scope

**Source-only candidate:** v0.6.2_84; implementation tracked by [Issue #850](https://github.com/Tolian82/os-zapret2-restyle/issues/850).
**Canonical requirements:** [GH-063–GH-065](../GITHUB_PUBLICATION.md). This guide describes implementation, not additional normative rule IDs.

## Trigger, trust and data sources

- `.github/workflows/pr-completion-watchdog.yml` runs on completion of relevant PR workflows (`workflow_run`), every 30 minutes as a delayed `schedule` fallback, via manual `workflow_dispatch`, and once on main push when the watcher workflow itself is introduced or edited.
- The privileged watcher **checks out only trusted default branch main**; it never fetches, checks out, sources or executes PR branch code. The GitHub workflow supplies a minimally scoped token: `contents: read`, `actions: read`, `pull-requests: read`, `issues: write`. It never calls merge, touches protected branch settings, packages software or reaches any appliance.
- `scripts/github_pr_watchdog.py` reads only owner-managed OPEN PRs targeting `main`, their current head SHA, changed-file paths, GitHub workflow run statuses, available job/step summaries and previous GitHub Issue comments. Expected workflow names are derived from the checked-in trusted default-branch `.github/workflows/*.yml` PR path filters, not a constant 16. Unsupported or inconsistent trigger policies fail closed (no READY).
- Classify `CI_IN_PROGRESS`, `CHECK_FAILED`, `CHECK_STALLED` (no job/step progress for ~30 minutes, advisory only), `STALE_BASE` and `READY_FOR_OWNER_REVIEW`. Only **completed successful latest current-head runs for every expected workflow** count. Cancelled, skipped, missing, wrong SHA, unsuccessful or pending checks are never green.
- Actionable states create a PR issue comment with a unique marker and current SHA/status. Existing identical head/state comments suppress repeats, including repeated scheduled invocations. Failure messages may include failed run/job/step URL **but never raw job logs or untrusted PR title/body**. The comment warns that it is not a merge/review substitute.

## Setup, smoke and operational acceptance

1. Verify the workflow exists on the *actual main* branch following an exact-head, fully qualified merge. A workflow file sitting only in a PR is NOT an installed monitor.
2. Verify the controlled GitHub Actions run triggered by the merge push to `main` for the watcher file, including a green offline negative regression suite and read-only scan outcome. Confirm subsequent events or scheduled executions before relying on unattended monitoring. GitHub scheduled runs can be delayed or disabled by platform settings.
3. Ensure repository Actions policy allows the declared `issues: write` token scope, and the owner is subscribed to the relevant PR/repository GitHub notifications; the script cannot guarantee external email/app delivery. A no-PR smoke proves that the watcher ran, **not** that an owner received a comment; a real actionable PR notification must be witnessed separately.
4. Operational source tests: `python3 scripts/test_github_pr_watchdog.py -v`. They exercise valid/invalid scoped workflow triggers, count-independent required sets, green/red/missing/old-head/cancelled/skipped/stalled/merge-conflict/draft states, duplicate suppression, owner-only scope and refusal to run untrusted code.
5. No always-on ChatGPT agent is launched by this workflow. GitHub notifications prompt **manual owner/developer follow-up**, not autonomous remediation or merge. Review/version/branch protection and package lifecycle safety gates still apply.

**Boundaries:** no installed product package, pkg hooks, native runtime, WAN, owner device, published stable release or LH-08/AC-11 acceptance is modified by this automation. Do not close #850 before actual workflow activation is shown; report notification permissions/unverified owner delivery explicitly.
