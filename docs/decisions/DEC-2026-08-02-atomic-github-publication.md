# DEC-2026-08-02 — Atomic GitHub publication and versioned pull-request titles

Status: Approved
Date: 2026-08-02

## Decision

Every logical development cycle is published as one ready branch containing one atomic commit, followed by one pull request and one complete check set. Final integration uses squash merge.

The pull-request title begins with the exact package candidate represented by the branch, including `PLUGIN_REVISION` when it is non-zero.

Required format:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

Example:

`v0.2.8_4: Add GUI Zapret2 service and release management`

A branch that advances the package revision must use the advanced revision in its title.

## Reason

Incremental transport commits, temporary Actions workflows, encoded patch fragments, and repeated branch changes generated redundant checks, obscured the real repository state, increased waiting time, and made failures harder to diagnose.

## Consequences

- Code, tests, documentation, and file modes are completed and checked before publication.
- The ready branch points directly to one atomic commit based on the recorded current `main` commit.
- The pull-request branch is not changed while checks are queued or running.
- A failed delivery cycle is closed and replaced with a new clean cycle after correction outside GitHub.
- Temporary workflows, Actions self-modification, patch-part transport, delivery-only trigger files, sequential content-API delivery commits, repair commits, repeated retriggers, and force-push repair are prohibited.
- Recovery, experimental, and noisy pull requests are never merged.
- The exact final commit and complete check set are verified before squash merge.

## Affected documentation

- `AGENTS.md`
- `docs/GITHUB_PUBLICATION.md`
- this decision record

The detailed operational procedure is authoritative in `docs/GITHUB_PUBLICATION.md`.
