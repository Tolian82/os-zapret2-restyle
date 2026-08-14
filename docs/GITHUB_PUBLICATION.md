# GitHub rules and publication discipline

Status: **CANONICAL / MANDATORY LEVEL 1**
Updated: 2026-08-14

This file is the single normative home for rules about **working with GitHub for this project**: repository access, preflight, branches, PRs, CI, merges, testing-package publication, full releases, and repository hygiene.

Other rule domains:

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — documentation governance (`DOC-*`);
- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — project-development/version/product rules (`DEV-*`);
- [`CHAT_RULES.md`](CHAT_RULES.md) — owner/assistant communication semantics (`CHAT-*`).

Read this file completely before GitHub mutation.

## A. GitHub access and preflight

GH-001. **Use the connected GitHub plugin/connector first for every supported repository operation.** It is the primary repository interface for reads and writes.

GH-002. **A fallback transport is narrow and evidence-based.** Use it only when the GitHub plugin is responding but one exact required operation/permission is confirmed missing or when a read-only bulk operation is not exposed. Do not replace the connected plugin as the normal workflow.

GH-003. **If required authoritative GitHub state cannot be read safely, stop mutation.** Do not guess branch heads, PR heads, release identity, CI state, or permissions.

GH-004. **Pin the exact `main` SHA before mutation.** The task branch base and all broad investigation references must be tied to an explicit current commit, not an assumed moving branch state.

GH-005. **Read current package identity before a delivery.** Resolve `VERSION` and `PLUGIN_REVISION`, applying `DEV-027`–`DEV-040`; do not infer candidate identity from a stale title, tag, README, or previous chat.

GH-006. **Read the current handoff/state/rules required by Level 1 before mutation.** Apply `DOC-016`, then read the current-task specialist documents named by `START_HERE.md`.

GH-007. **Preflight is scope/risk based.** Always check exact `main`, candidate identity, current handoff/state, and relevant same-scope open PR state. Expand to CI runs, permissions, releases, branches, artifacts, or full tree only when the scope/risk needs them.

GH-008. **Broad investigation uses one pinned recursive tree as an index when practical.** Resolve the exact SHA once, obtain the tree, and fetch only files/objects needed from that immutable snapshot rather than repeatedly rediscovering repository structure.

GH-009. **Owner-canon/documentation reconciliation is broad by definition.** When `CHAT-009` applies, inspect every active/current-looking authority capable of contradicting the new canon, while preserving historical records under `DOC-004`–`DOC-005`.

## B. Branch and logical-scope discipline

GH-010. **One logical scope uses one task branch and one PR.** Branch from the exact verified `main` SHA; unrelated work gets another scope.

GH-011. **Same-root-cause corrections stay in the same PR.** A stale test, fixture, documentation contract, or CI assertion exposed by the intended change is repaired in that PR rather than split into artificial follow-up PRs before merge.

GH-012. **Do not mix unrelated opportunistic cleanup into a task branch.** Preserve reviewability and causality.

GH-013. **A Ready PR is the default for complete intended work.** Use Draft only for intentionally incomplete work that must be published before it is merge-ready.

GH-014. **Branch/PR/commit identity follows the exact current candidate prefix.** Unless a specific repository mechanism requires otherwise, PR titles, branch-commit subjects, and final squash subjects use `v<VERSION>_<PLUGIN_REVISION>:` even for docs/governance changes that intentionally do not bump metadata.

GH-015. **A docs/governance/CI-only delivery may advance `main` without changing package metadata.** Apply `DEV-033`; its title prefix still names the current package candidate so repository chronology remains anchored.

## C. Validation and CI failure handling

GH-016. **Validate before publication/merge.** Run the focused checks required by scope and the repository CI contract. Never merge based on an unverified older head.

GH-017. **Read exact failed-job evidence before changing source, tests, workflow, or branch state.** A plausible explanation is not enough (`DEV-012`).

GH-018. **A confirmed same-scope defect is corrected in the same PR.** Update the PR head and re-run applicable checks.

GH-019. **A stale test or CI assertion is corrected, not obeyed as obsolete product authority.** Apply `DEV-013` and preserve the current intended architecture.

GH-020. **An external runner/network/action/dependency outage does not justify speculative source changes.** Retry the unchanged applicable job/run when appropriate or diagnose infrastructure first (`DEV-014`).

GH-021. **Only successful checks for the latest mergeable head authorize merge.** If the head changes, prior successful checks do not prove the new head.

GH-022. **Never report a skipped/unrun job as PASS.** A legitimately path-skipped package build is `SKIPPED`, not a successful package qualification (`DEV-011`).

GH-023. **Path-gated package builds remain meaningful.** Packaged-source or package/CI infrastructure changes run the required FreeBSD package qualification; pure docs/governance changes may skip package build when the workflow classifies them as non-package changes.

## D. PR merge and post-merge verification

GH-024. **Merge only the exact verified PR head.** Use expected-head protection when available so a moved head cannot be merged accidentally.

GH-025. **Normal project integration is one squash merge per logical scope.** The resulting `main` commit subject uses the exact candidate prefix and describes the logical change.

GH-026. **Verify the resulting `main` after merge.** Confirm the new SHA and applicable `main` integrity/release-classification behavior rather than assuming the PR result automatically proves post-merge state.

GH-027. **Published history is forward-only.** Never force-update `main`, rewrite an already-published release, move a published tag to another commit, or hide a failed publication by rewriting history. Repair forward with another logical change.

GH-028. **Temporary branches are completion machinery, not permanent clutter.** After merge/completion, compare against `main`; preserve useful unique work first, otherwise delete the temporary task/publication branch and verify normal branch state.

GH-029. **Routine branch cleanup is performed without a separate owner confirmation.** Apply `CHAT-010` and `CHAT-022`; escalate only a real permission/tooling/safety boundary.

GH-030. **Normal steady-state branch hygiene is `main` plus explicitly retained long-lived recovery/work branches.** Do not leave obsolete task/publication branches after their work is safely integrated.

## E. Repository artifact and secret hygiene

GH-031. **Do not commit transport/scratch/backup artifacts.** `.orig`, `.rej`, `.patch`, `.diff`, `.b64`, `.base64`, `.bak`, split-part artifacts, editor backups, and equivalent temporary files are not repository state unless an explicit approved artifact format requires them.

GH-032. **Never publish secrets or sensitive private configuration.** Credentials, tokens, private configuration, private exploit details, or unredacted sensitive logs do not belong in public issues, PRs, commits, release assets, or repository documentation.

GH-033. **Repository hygiene checks are part of normal CI.** Do not disable or weaken them merely to make an otherwise incorrect tree pass.

## F. Owner testing-package publication

GH-034. **Interpret owner package shorthand through `CHAT-015`–`CHAT-016`.** A testing package is persistent GitHub delivery, not an ephemeral Actions artifact unless the owner explicitly requested build evidence only.

GH-035. **A testing package is tied to an immutable exact source identity.** Verify candidate version/revision, source commit/tag, uploaded `.pkg`, and checksum/digest as applicable.

GH-036. **Testing-package publication does not promote the stable project package repository.** No stable Pages/pkg-repository update or full-release claim occurs merely because a `.pkg` is published for testing.

GH-037. **Testing package bytes remain retrievable after workflow completion.** Use a persistent GitHub release/prerelease asset or equivalent approved persistent GitHub surface; Actions artifacts/local container files alone are build evidence.

GH-038. **Temporary testing-publication branches are removed after successful publication once unique work is safely preserved.** Do not leave version-specific publisher branches as permanent process state.

## G. Full release publication

GH-039. **Interpret `релиз` through `CHAT-017` and `DEV-039`.** A full release is not complete until the package repository/Web-install boundary is verified.

GH-040. **A full release requires explicit owner release authority.** Do not infer a stable release merely because CI is green or a package exists.

GH-041. **A full release uses the exact current candidate.** It may publish the current `_N`; publication itself does not reset revision (`DEV-038`).

GH-042. **A full release must pass the README gate.** Apply `DOC-038`–`DOC-039` before release preparation.

GH-043. **Release preparation merge identity is explicit.** The verified merge subject is `v<VERSION>_<PLUGIN_REVISION>: Prepare release v<VERSION>` (optionally with the repository's squash PR suffix where accepted by validation).

GH-044. **The semantic release tag is immutable and points to the exact release-preparation merge.** If `v<VERSION>` already exists at another commit, do not move it; choose a new owner-approved project version for a later full release.

GH-045. **A full GitHub Release contains the exact package and checksum assets and is not marked as a testing prerelease.** Verify the released asset identity against the source candidate.

GH-046. **A full release publishes and verifies the matching `FreeBSD:15:amd64` project package repository.** Confirm the generated repository metadata/package location and OPNsense Web install/update availability.

GH-047. **A second-component transition is guarded by `DEV-036`–`DEV-037`.** It must start at `_1`, include explicit full-release preparation, and perform the documentation-line rollover defined by `DOC-028`–`DOC-030`.

GH-048. **A third-component transition is guarded by `DEV-034`–`DEV-035`.** It starts at `_1` but does not trigger a full release unless the same exact merge is explicitly a release-preparation merge.

## H. Release-trigger behavior

GH-049. **Every `main` merge is classified, but ordinary changes do not publish a release.** Same-`VERSION` merges finish with no tag/release dispatch unless they are the exact explicit release-preparation case.

GH-050. **A third-component-only `VERSION` change requires `_1` and is accepted as a development-stage transition without release by default.** Release occurs only with explicit release-preparation identity.

GH-051. **A first/second-component transition requires `_1` and explicit full-release preparation.** A second-component transition without that authority is a failed governance boundary, not an implicit release.

GH-052. **An explicit release-preparation merge at the current candidate creates/verifies the semantic tag and dispatches the full release workflow.** Post-release verification remains mandatory.

## I. Documentation and process synchronization

GH-053. **Every GitHub delivery applies the same-scope documentation reconciliation required by `DOC-036`–`DOC-037`.** Do not create a second GitHub-specific copy of documentation rules here.

GH-054. **`INDEX.md`, rule books, handoff/state/roadmap, and current ledger are updated only when their bounded roles actually change.** Do not touch documents mechanically just to increase the number of files in a PR.

GH-055. **GitHub procedure changes are recorded here first.** Assign the next `GH-*` ID, then update affected workflows/tests/quick-reference documents under `DOC-008` in the same logical scope.

GH-056. **Legacy decision records are rationale/history, not competing current procedure.** Where an older GitHub decision was superseded, keep it marked historical/superseded; do not merge its obsolete mandatory behavior back into this file.
