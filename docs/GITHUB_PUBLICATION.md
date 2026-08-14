# GitHub rules — Правила работы с GitHub

**Status:** CANONICAL · MANDATORY LEVEL 1
**Updated:** 2026-08-15

This file is the fourth canonical rule book and the single normative home for working with GitHub in this project: repository access, preflight, branches, PRs, CI, merges, testing packages, full releases, documentation synchronization, and repository hygiene. The filename `GITHUB_PUBLICATION.md` is intentionally retained; its scope is all GitHub work, not publication only.

Other canonical rule domains:

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — documentation governance (`DOC-*`);
- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — project-development/version/product rules (`DEV-*`);
- [`CHAT_RULES.md`](CHAT_RULES.md) — owner/assistant communication semantics (`CHAT-*`).

Read this file completely before GitHub mutation.

## Quick route by task

- access and preflight: `GH-001`–`GH-008`;
- branch and PR scope: `GH-010`–`GH-015`;
- validation and CI: `GH-016`–`GH-023`;
- merge, post-merge verification, cleanup: `GH-024`–`GH-030`;
- repository/secret hygiene: `GH-031`–`GH-033`;
- testing package: `GH-034`–`GH-038`, `GH-060`–`GH-061`;
- full release: `GH-039`–`GH-048`;
- release-trigger behavior: `GH-049`–`GH-052`;
- documentation/process synchronization: `GH-053`–`GH-059`.

## GitHub access and preflight

GH-001. **Use the connected GitHub plugin/connector first for every supported repository operation.** It is the primary repository interface for reads and writes.

GH-002. **A fallback transport is narrow and evidence-based.** Use it only when the GitHub plugin is responding but one exact required operation or permission is confirmed missing, or when a necessary read-only bulk operation is not exposed. Do not replace the connector as the normal workflow.

GH-003. **If required authoritative GitHub state cannot be read safely, stop mutation.** Do not guess branch heads, PR heads, release identity, CI state, or permissions.

GH-004. **Pin the exact `main` SHA before mutation.** The task branch base and broad investigation references are tied to an explicit current commit, not an assumed moving branch.

GH-005. **Read current package identity before a delivery.** Resolve `VERSION` and `PLUGIN_REVISION` and apply `DEV-027`–`DEV-040`; never infer candidate identity from a stale title, tag, README, or previous chat.

GH-006. **Complete the mandatory cold-start/current-authority reading before mutation.** Apply `DOC-016`, then read every current-task specialist document selected by `START_HERE.md` through EOF. Reuse of already-read unchanged Level-1 material is allowed only under `DOC-049`.

GH-007. **Preflight is scope/risk based.** Always check exact `main`, candidate identity, current handoff/state, and relevant same-scope open PR state. Expand to CI runs, permissions, releases, branches, artifacts, or full tree only when scope/risk requires them.

GH-008. **Broad investigation uses one pinned recursive tree as an index when practical.** Resolve the exact SHA once and fetch only the files/objects needed from that immutable snapshot rather than repeatedly rediscovering repository structure.

GH-009. **[ОТМЕНЕНО] Owner-canon/documentation reconciliation is broad by definition.** This rule previously required inspection of every active/current-looking authority whenever owner canon was recorded. The owner cancelled it on 2026-08-14 because permanent rule IDs, explicit dependency registries, targeted reconciliation under `DOC-008`, link validation, and scope/risk-based inspection provide stronger consistency without forcing a repository-wide audit for every canon change. The ID and original meaning remain permanently reserved.

## Branch and logical-scope discipline

GH-010. **One logical engineering/source scope uses one task branch and one source PR.** Branch from the exact verified `main` SHA; unrelated work gets another scope. The bounded post-publication documentation-record PR required by `GH-060`–`GH-061` is the explicit delivery-tail exception because immutable publication facts do not exist before the source merge and publication; that tail contains no product/package change.

GH-011. **Same-root-cause corrections stay in the same PR.** A stale test, fixture, documentation contract, or CI assertion exposed by the intended change is repaired in that PR; this is the GitHub application of `DEV-017`.

GH-012. **Do not mix unrelated opportunistic cleanup into a task branch.** Preserve reviewability and causality.

GH-013. **A Ready PR is the default for complete intended work.** Use Draft only for intentionally incomplete work that must be published before it is merge-ready.

GH-014. **Branch, PR, commit, and squash identity follows the exact current candidate prefix.** Unless a specific mechanism requires otherwise, subjects use `v<VERSION>_<PLUGIN_REVISION>:` under `DEV-027`–`DEV-028`, including docs/governance changes that intentionally do not bump metadata.

GH-015. **A docs/governance/CI-only delivery may advance `main` without changing package metadata.** Apply `DEV-033`; its title prefix still names the current package candidate so chronology stays anchored.

## Validation and CI failure handling

GH-016. **Validate the latest head with checks proportionate to the changed scope.** Pure documentation changes run the documentation, rule-reference, link, release-governance, and repository-integrity checks that can be affected, without mechanically running the full product matrix. Product or packaged-source changes run the applicable full product validation. CI/workflow changes run their affected CI contracts and run the full product matrix when they change general validation logic. Never merge based on an unverified older head.

GH-017. **Read exact failed-job evidence before changing source, tests, workflow, or branch state.** Apply `DEV-012`; a plausible explanation is not enough.

GH-018. **A confirmed same-scope defect is corrected in the same PR.** Update the PR head and rerun applicable checks.

GH-019. **A stale test or CI assertion is corrected, not obeyed as obsolete product authority.** Apply `DEV-013` and preserve current intended architecture.

GH-020. **An external runner, network, action, service, or dependency outage does not justify speculative source changes.** Apply `DEV-014` and diagnose infrastructure first.

GH-021. **Only successful checks for the latest mergeable head authorize merge.** If the head changes, prior successful checks do not prove the new head.

GH-022. **Never report a skipped or unrun job as PASS.** A legitimately path-skipped build is `SKIPPED`, not successful qualification, under `DEV-011`.

GH-023. **Path-gated package builds remain meaningful.** Packaged-source or package/CI-infrastructure changes run required FreeBSD package qualification; pure docs/governance changes may skip package build when the workflow classifies them as non-package changes.

## PR merge and post-merge verification

GH-024. **Merge only the exact verified PR head.** Use expected-head protection when available so a moved head cannot be merged accidentally.

GH-025. **Normal project integration is one squash merge per logical scope.** The resulting `main` subject uses the exact candidate prefix and describes the logical change.

GH-026. **Verify the resulting `main` after merge.** Confirm the new SHA and applicable main-integrity/release-classification behavior rather than assuming PR checks automatically prove post-merge state.

GH-027. **Published release identity and bytes are forward-only.** Never force-update `main`, move a published tag to another commit, replace already-published package/checksum assets under the same release identity, or hide a failed publication by rewriting history. Repair substantive publication errors forward. Human-facing release notes may be transparently corrected when that edit does not change the release identity, tag target, binary/checksum assets, or conceal a publication defect.

GH-028. **Temporary branches are completion machinery, not permanent clutter.** After merge/completion, preserve useful unique work first; otherwise delete the temporary task/publication branch and verify normal branch state.

GH-029. **Routine branch cleanup needs no separate owner confirmation.** Apply `CHAT-010` and `CHAT-022`; escalate only a real permission, tooling, or safety boundary.

GH-030. **Normal steady-state branch hygiene is `main` plus explicitly retained long-lived recovery/work branches.** Do not leave obsolete task/publication branches after safe integration.

## Repository artifact and secret hygiene

GH-031. **Do not commit transport, scratch, or backup artifacts.** `.orig`, `.rej`, `.patch`, `.diff`, `.b64`, `.base64`, `.bak`, split parts, editor backups, and equivalent temporary files are not repository state unless an explicitly approved artifact format requires them.

GH-032. **Never publish secrets or sensitive private configuration.** Credentials, tokens, private configuration, private exploit details, or unredacted sensitive logs do not belong in public issues, PRs, commits, release assets, or repository documentation.

GH-033. **Repository hygiene checks are part of normal CI.** Do not disable or weaken them merely to make an incorrect tree pass.

## Owner testing-package publication

GH-034. **Interpret owner package shorthand through `CHAT-015`, `CHAT-016`, and `CHAT-027`.** A testing package is persistent GitHub delivery, not an ephemeral Actions artifact unless the owner explicitly requests build evidence only.

GH-035. **A testing package is tied to the immutable exact merged commit that introduced the current package identity.** Verify that the publication source is already an ancestor of current `main`, that its parent has a different package identity, and that candidate version/revision, tag target, uploaded `.pkg`, and checksum/digest all agree. Do not publish a current candidate from a later docs-only/governance commit merely because `VERSION` and `PLUGIN_REVISION` still match.

GH-036. **Testing-package publication does not promote the stable project package repository.** No stable Pages/pkg-repository update or full-release claim occurs merely because a `.pkg` is published for testing.

GH-037. **Testing package bytes remain retrievable after workflow completion.** Use a persistent GitHub release/prerelease asset or equivalent approved persistent GitHub surface; Actions artifacts, local files, sandbox files, and chat attachments are build evidence or transport artifacts, not package delivery.

GH-038. **Temporary testing-publication branches are removed after successful publication once unique work is safely preserved.** Do not leave version-specific publisher branches as permanent process state.

GH-060. **An owner package/patch command is complete only after direct GitHub testing-package delivery when a package candidate is involved.** For the shorthand governed by `CHAT-015`–`CHAT-016`: finish the source scope under the normal PR/CI/exact-head merge rules; when the command creates a new package candidate, immediately publish that exact candidate from its candidate-defining merged source commit through the generic testing publisher without asking for a second publication confirmation; verify prerelease/tag target, uploaded `.pkg`, checksum/digest, and publication-branch cleanup; complete the publication-record tail required by `GH-061` and `DOC-037`; and only then report completion with the direct GitHub `.pkg` asset URL. A source PR, merge, CI package artifact, local `.pkg`, sandbox download, or chat attachment is not package completion. If GitHub publication is concretely blocked, report that blocker and do not substitute a chat-delivered package/archive. The product boundary remains `DEV-040`, and owner-facing file delivery obeys `CHAT-027`.

GH-061. **Successful testing-package publication automatically creates one bounded Draft publication-record PR, and that PR is part of completion.** The generic publisher creates a branch from the then-current `main`, writes a machine-generated evidence record under `docs/verification/evidence/testing-publications/` containing the immutable candidate/tag/asset/digest/workflow facts, and opens a Draft docs-only PR with the current candidate prefix. The assistant then, without requesting new owner permission, reconciles only the additional bounded current documentation whose role actually changed, marks the exact-head PR ready, requires applicable documentation/governance CI to pass, squash-merges it, verifies the resulting `main`, and cleans the temporary branch. The publication-record PR must contain no product/package source, package metadata, workflow/script, repository-output, or binary change; it exists solely because these publication facts did not exist before source merge. A package/patch delivery that required this tail is not complete while that PR is absent, open, failed, unverified, or unmerged. Documentation ownership follows `DOC-037`.

## Full release publication

GH-039. **Interpret `релиз` through `CHAT-017` and `DEV-039`.** A full release is not complete until the package repository/Web-install boundary is verified.

GH-040. **A full release requires explicit owner release authority.** Do not infer a stable release merely because CI is green or a package exists.

GH-041. **A full release uses the exact current candidate.** It may publish the current `_N`; publication itself does not reset revision under `DEV-038`.

GH-042. **A full release must pass the README gate.** Apply `DOC-038`–`DOC-039` before release preparation.

GH-043. **Release-preparation merge identity is explicit.** The verified merge subject is `v<VERSION>_<PLUGIN_REVISION>: Prepare release v<VERSION>` with only repository-accepted squash suffix variation.

GH-044. **The semantic release tag is immutable and points to the exact release-preparation merge.** If `v<VERSION>` already exists at another commit, do not move it; use a new owner-approved project version for a later release.

GH-045. **A full GitHub Release contains the exact package and checksum assets and is not a testing prerelease.** Verify released asset identity against the source candidate.

GH-046. **A full release publishes and verifies the matching `FreeBSD:15:amd64` project package repository.** Confirm generated repository metadata, package location, and OPNsense Web install/update availability.

GH-047. **A second-component transition is guarded by `DEV-036`–`DEV-037`.** It starts at `_1`, includes explicit full-release preparation, and performs the documentation-line rollover in `DOC-028`–`DOC-030`.

GH-048. **A third-component transition is guarded by `DEV-034`–`DEV-035`.** It starts at `_1` but does not trigger a full release unless the same exact merge is explicitly release preparation.

## Release-trigger behavior

GH-049. **Every `main` merge is classified, but ordinary changes do not publish a release.** Same-`VERSION` merges finish with no tag/release dispatch unless they are the exact explicit release-preparation case.

GH-050. **A third-component-only `VERSION` change requires `_1` and is accepted as a development-stage transition without release by default.** Release occurs only with explicit release-preparation identity.

GH-051. **A first/second-component transition requires `_1` and explicit full-release preparation.** A second-component transition without owner authority under `DEV-036`–`DEV-037` is a failed governance boundary, not an implicit release.

GH-052. **An explicit release-preparation merge at the current candidate creates or verifies the semantic tag and dispatches the full release workflow.** Post-release verification remains mandatory.

## Documentation and process synchronization

GH-053. **Every GitHub delivery applies documentation reconciliation.** Apply `DOC-036`, `DOC-037`, and `DOC-047`. Facts/contracts/handoff/plan/rules known before source merge are reconciled in that logical source PR. Facts that exist only after successful immutable testing-package publication—such as release/tag identity, asset digest, publication workflow result, and automatic publisher-branch cleanup—are reconciled immediately in the bounded docs-only publication-record PR required by `GH-060`–`GH-061`; this is the explicit post-publication exception to the same-source-PR rule and must contain no product/package change. Otherwise use an evidence-based no-op when nothing documented changed.

GH-054. **Touch bounded documents only when their role requires it.** Apply `DOC-011`, `DOC-012`, and `DOC-047`; do not mechanically edit state, handoff, roadmap, or rule books merely to increase PR file count.

GH-055. **GitHub-rule changes are recorded here first.** Add or amend the persistent `GH-*` rule, then reconcile affected references and checks under `DOC-008` and `DOC-042`–`DOC-045` in the same logical scope.

GH-056. **Legacy GitHub decisions are rationale/history, not competing current procedure.** Where an older decision was superseded, preserve it as history and do not merge obsolete behavior back into this file.

GH-057. **The repository tree must be self-consistent at merge.** Active canonical paths, navigation, current state/handoff, rule references, tests, and local documentation links must resolve together; known dangling or contradictory current references block merge under `DOC-019`, `DOC-045`, `DOC-047`, and `DOC-053`.

GH-058. **A canonical rule-book change must pass cross-reference integrity validation.** The bidirectional registries, active rule-body references, and rule lifecycle state must agree under `DOC-042`–`DOC-045` before merge.

GH-059. **Deleting or renaming documentation is a repository-wide reference migration.** Apply `DOC-053`: migrate affected tracked Markdown links and active navigation in the same logical scope, then require the internal-link validator to pass. Do not keep an obsolete duplicate document merely to preserve an in-repository link when those references can be migrated cleanly.

## Cross-reference registry

### Outbound references

<!-- RULE-XREF-OUT-BEGIN -->
| Source rule | Target rules |
|---|---|
| `GH-005` | `DEV-027`–`DEV-040` |
| `GH-006` | `DOC-016`, `DOC-049` |
| `GH-011` | `DEV-017` |
| `GH-014` | `DEV-027`, `DEV-028` |
| `GH-015` | `DEV-033` |
| `GH-017` | `DEV-012` |
| `GH-019` | `DEV-013` |
| `GH-020` | `DEV-014` |
| `GH-022` | `DEV-011` |
| `GH-029` | `CHAT-010`, `CHAT-022` |
| `GH-034` | `CHAT-015`, `CHAT-016`, `CHAT-027` |
| `GH-039` | `DEV-039`, `CHAT-017` |
| `GH-041` | `DEV-038` |
| `GH-042` | `DOC-038`, `DOC-039` |
| `GH-047` | `DOC-028`–`DOC-030`, `DEV-036`, `DEV-037` |
| `GH-048` | `DEV-034`, `DEV-035` |
| `GH-051` | `DEV-036`, `DEV-037` |
| `GH-053` | `DOC-036`, `DOC-037`, `DOC-047` |
| `GH-054` | `DOC-011`, `DOC-012`, `DOC-047` |
| `GH-055` | `DOC-008`, `DOC-042`–`DOC-045` |
| `GH-057` | `DOC-019`, `DOC-045`, `DOC-047`, `DOC-053` |
| `GH-058` | `DOC-042`–`DOC-045` |
| `GH-059` | `DOC-053` |
| `GH-060` | `DOC-037`, `DEV-040`, `CHAT-015`, `CHAT-016`, `CHAT-027` |
| `GH-061` | `DOC-037` |
<!-- RULE-XREF-OUT-END -->

### Inbound references

<!-- RULE-XREF-IN-BEGIN -->
| Target rule | Referenced by |
|---|---|
| `GH-004` | `DOC-049`, `CHAT-012` |
| `GH-006` | `DOC-016` |
| `GH-010`–`GH-014` | `CHAT-010` |
| `GH-011` | additionally `DEV-017` |
| `GH-015` | `DEV-033`, `CHAT-010` |
| `GH-016`–`GH-023` | `CHAT-010` |
| `GH-024`–`GH-030` | `CHAT-010`, `CHAT-018` |
| `GH-026` | additionally `DOC-049` |
| `GH-034`–`GH-038` | `DEV-040`, `CHAT-015`, `CHAT-016`, `CHAT-027` |
| `GH-039` | `DOC-038`, `DEV-039`, `CHAT-017` |
| `GH-040` | `DOC-038`, `CHAT-017` |
| `GH-041` | `DOC-038`, `DEV-038`, `CHAT-017` |
| `GH-042`–`GH-044` | `DOC-038`, `CHAT-017` |
| `GH-045`, `GH-046` | `DOC-038`, `DEV-039`, `CHAT-017` |
| `GH-047` | `DEV-036`, `DEV-037`, `CHAT-017` |
| `GH-048`–`GH-050` | `CHAT-017` |
| `GH-051` | `DEV-036`, `DEV-037`, `CHAT-017` |
| `GH-052` | `CHAT-017` |
| `GH-053` | `DOC-037`, `DOC-047` |
| `GH-054` | `DOC-047` |
| `GH-060` | `DOC-037`, `DOC-047`, `DEV-040`, `CHAT-015`, `CHAT-016`, `CHAT-027` |
| `GH-061` | `DOC-037`, `DOC-047`, `DEV-040`, `CHAT-015`, `CHAT-016`, `CHAT-027` |
<!-- RULE-XREF-IN-END -->

## Rule lifecycle

- `GH-009` — **ОТМЕНЕНО**, 2026-08-14; no replacement.

Cancelled/replaced IDs remain physically in this file and are never recycled.
