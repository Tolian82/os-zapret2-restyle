# DEC-2026-08-02 — Atomic GitHub publication, release gates, and forward-only versions

Status: Approved and extended
Original date: 2026-08-02
Extended: 2026-08-03

## Decision

Every logical development cycle is published as one ready branch containing one atomic
commit, followed by one ready pull request, one complete check set, and one squash merge.

The pull-request title begins with the exact package candidate represented by the branch:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

A release-preparation squash subject is a separate protocol field:

`release: prepare v<VERSION>`

The PR title is computed before the pull request is opened. The normal path does not use
Draft → Ready, title edits, or branch changes to trigger additional checks.

Multi-file GitHub/API publication creates all blobs, one tree, and one commit. It must
not stream the change through sequential contents-API commits.

A failed delivery cycle is closed and replaced by one clean cycle. It is not repaired by
additional commits, repeated check retriggers, title edits, Ready transitions, or
force-push.

Release authority requires an explicit project-owner request for the exact version.
Ambiguous continuation wording does not authorize a release and the assistant does not
choose a project version independently.

Published versions are immutable and development is forward-only. Existing tags,
releases, and assets are never moved, replaced, reused, or rolled back. A later release
uses a higher explicitly approved version.

Required live verification is a release gate. It is satisfied by recorded evidence or
an explicit project-owner statement that the named package was tested successfully.
Owner evidence is recorded honestly without inventing commands or output.

Before installation instructions are delivered, the release workflow, tag, package,
checksum, Pages deployment, repository metadata, and exact public pkg version are all
verified.

## Reason

The v0.3.1 cycle exposed avoidable GitHub noise and protocol failures:

- release preparation started from ambiguous continuation wording instead of an
  explicit version request;
- the first release pull-request title used the release squash subject rather than the
  package-candidate title required by `pr-title.yml`;
- opening, editing, and Ready transitions generated redundant title-check runs;
- sequential contents-API updates created multiple preparation commits before squash;
- installation instructions were considered before the complete public distribution
  channel had been verified.

The release itself was later checked by the project owner and package `0.3.1_1` was
confirmed correct. The problem was the efficiency and determinism of the GitHub process,
not the released plugin.

## Consequences

- Code, tests, documentation, and file modes are complete before publication.
- The final task branch represents one atomic commit based on the recorded current
  `main`.
- A pull request is opened ready for review with the correct title on its first event.
- The branch remains unchanged during its single check set.
- Pull-request title and release squash subject are never confused.
- Failed cycles remain historical evidence but are never merged or incrementally
  repaired.
- `PROJECT_STATE.md` records a delivery stage and later-stage work cannot bypass it.
- Release versions only advance; published versions are never rolled back.
- Package installation commands follow full public-distribution verification.

## Current application

The project owner has:

- confirmed successful live verification of release/package `v0.3.1` /
  `os-zapret2-restyle-0.3.1_1.pkg`;
- approved the workflow corrections above;
- explicitly authorized forward release `v0.3.2`.

Expected v0.3.2 package:

`os-zapret2-restyle-0.3.2_1.pkg`

## Affected documentation

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/PROJECT_STATE.md`
- `docs/GITHUB_WORKFLOW.md`
- `docs/GITHUB_PUBLICATION.md`
- `docs/audit/AUDIT-2026-08-03-DOMAIN-DIAGNOSTICS.md`
- `docs/devlog/DEVLOG-2026-08-03-RELEASE-v0.3.1.md`
- `docs/devlog/DEVLOG-2026-08-03-RELEASE-v0.3.2.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
- `docs/releases/v0.3.1.md`
- `docs/releases/v0.3.2.md`
- `README.md`

The detailed operational procedure is authoritative in
`docs/GITHUB_PUBLICATION.md`.
