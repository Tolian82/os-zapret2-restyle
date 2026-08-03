# os-zapret2-restyle — GitHub workflow

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the official repository maintained and how are releases controlled?

Purpose:
Define repository identity, source baseline, authorization boundaries, release control,
and publication verification. Exact pull-request event discipline is delegated to
`GITHUB_PUBLICATION.md`.

Updated when:
Repository policy, release authorization, automation, or distribution verification
changes.

Read after:
`REQUIREMENTS.md`.

Do not store here:
Runtime architecture, product requirements, current task status, or chronological
release history.

==================================================
OFFICIAL REPOSITORY
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Primary branch:
`main`

Default source baseline:
The exact current `main` commit recorded before work starts.

No archive is required for state already committed and pushed. Uncommitted or unpushed
owner state must be published or transferred explicitly before it can be used.

==================================================
AUTHORIZATION BOUNDARIES
==================================================

Ordinary development requests authorize:

- one task branch;
- one atomic logical commit;
- one ready pull request;
- one complete check set;
- one squash merge;
- verification of `main`.

Requests limited to analysis, review, patch, branch, or pull request stop at that named
boundary.

A release requires an explicit request for the exact version. Ambiguous continuation
language is not release authority. The assistant must never select a project version
independently.

One explicit request for version X authorizes its complete verified release path:
release preparation, pull request, merge, immutable tag, GitHub Release, assets,
GitHub Pages/pkg repository, and final checks.

==================================================
FORWARD-ONLY VERSION POLICY
==================================================

Published versions are immutable.

Never:

- move a published tag;
- replace assets under a published release;
- roll `VERSION` back to an earlier release;
- reuse a version for different source;
- rewrite published repository history.

A later approved release uses a higher version. The current owner-approved next release
is `v0.3.2` with package `os-zapret2-restyle-0.3.2_1.pkg`.

==================================================
CURRENT DELIVERY PROTOCOL
==================================================

`docs/GITHUB_PUBLICATION.md` is the specialist authority. Its active protocol is:

one logical change
        ↓
one atomic commit
        ↓
one ready pull request
        ↓
one complete check set
        ↓
one squash merge
        ↓
verify `main`

Do not use Draft → Ready by default. Do not publish multi-file work through sequential
contents-API commits. Do not modify the final branch while checks run. A failed cycle is
closed and replaced with one clean cycle.

==================================================
PULL-REQUEST PROTOCOL FIELDS
==================================================

Before opening a pull request, inspect all workflows triggered by the planned event.

The current PR-title contract is:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

For `v0.3.2`:

`v0.3.2_1: Improve GitHub publication discipline`

A release squash subject is a separate field:

`release: prepare v0.3.2`

The PR must not be opened using the squash subject as its title.

==================================================
ATOMIC API PUBLICATION
==================================================

For GitHub integration/API delivery:

1. Prepare all final content and modes.
2. Create one blob per changed file.
3. Create one tree based on the recorded `main` tree.
4. Create one commit with the recorded `main` as its sole parent.
5. Recheck `main` for concurrency.
6. Publish the task branch directly at that commit.
7. Open one ready pull request.

A missing optional client such as `gh` is not a blocker while the GitHub integration or
an authenticated Git remote can complete the work.

==================================================
RELEASE GATES
==================================================

The release path may begin only when:

- exact version authority is explicit;
- required source and CI verification is complete;
- mandatory live evidence is recorded or explicitly confirmed by the owner;
- owner acceptance is recorded when required;
- `PROJECT_STATE.md` records `RELEASE_AUTHORIZED`.

An owner statement that a named package was tested and everything works satisfies the
owner-supplied live-verification gate for that package. Record the statement as owner
evidence without inventing unavailable command output.

==================================================
AUTOMATED RELEASE RUNBOOK
==================================================

1. Change `VERSION` to the explicitly approved new version.
2. Set `PLUGIN_REVISION=1` for the new version.
3. Synchronize release-facing and engineering documentation.
4. Publish one atomic release-preparation pull request with the package-candidate title.
5. Pass one complete pull-request check set.
6. Squash merge with exact subject `release: prepare vX.Y.Z`.
7. `release-trigger.yml` validates the merge and creates or verifies the immutable tag.
8. `release-trigger.yml` explicitly dispatches `release.yml` at that tag.
9. `release.yml` validates, builds in FreeBSD 15, verifies the package, publishes the
   GitHub prerelease and assets, and deploys the Pages/pkg repository.
10. Verify distribution completely before offering installation commands.

The release trigger never moves an existing tag. A direct tag push remains an emergency
fallback only when repository automation is genuinely unavailable.

==================================================
POST-RELEASE CHECKLIST
==================================================

Verify all of the following:

- release merge is current `main`;
- tag resolves to that merge;
- Release trigger succeeded;
- Release workflow succeeded;
- exact package asset exists;
- `SHA256SUMS` exists;
- Pages deployment succeeded;
- repository configuration is published;
- `meta.conf`, `data.pkg`, and `packagesite.pkg` exist;
- the exact package candidate is visible in the public pkg repository.

Only then provide OPNsense package installation or upgrade commands.

==================================================
LOCAL-ONLY STATE AND CONCURRENCY
==================================================

GitHub cannot expose local uncommitted owner state. Stop before overwriting or
reconstructing it.

If `main` changes after the base SHA is recorded, do not publish the prepared branch.
Reconcile the change against the new `main`, rebuild the atomic commit, and rerun checks.
Force-push and direct history rewriting are prohibited.

==================================================
HISTORY RESPONSIBILITY
==================================================

Release results belong in `DEVLOG.md` or a focused file under `docs/devlog/`, audit
evidence belongs under `AUDIT.md` or `docs/audit/`, and user-visible release content
belongs in `CHANGELOG.md` and `docs/releases/`.
