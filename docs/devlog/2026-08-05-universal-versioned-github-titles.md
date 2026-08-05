# 2026-08-05 — Restore universal versioned GitHub titles

## Scope

Correct the GitHub governance regression introduced by PR #82 without rewriting the
already merged `main` history.

## Root cause

The governance modernization intentionally separated package metadata changes from
non-packaged governance/documentation/CI changes, but incorrectly treated title identity
as part of that separation. This allowed unversioned conventional titles and led to the
squash subject `governance: modernize GitHub delivery`.

## Correction

- restored the universal `v<VERSION>_<PLUGIN_REVISION>:` prefix for every PR title;
- required the same prefix for every work and repair commit subject in a PR branch;
- required the same prefix for the final squash commit subject in `main`;
- retained unchanged package metadata for governance/documentation/CI-only changes;
- added PR workflow enforcement for titles and branch commit subjects;
- added post-merge `main` integrity enforcement for the squash subject;
- updated active governance documentation and decision authority;
- retained the historical incorrectly titled commit unchanged under the no-history-
  rewrite rule.

## Current candidate

`VERSION=0.3.2`

`PLUGIN_REVISION=24`

Required prefix:

`v0.3.2_24:`

## Expected verification

- PR title validation passes only with the exact prefix;
- every commit in the corrective PR branch passes the same prefix check;
- documentation/governance-only path classification skips the FreeBSD package build;
- full project validation passes;
- squash merge uses `v0.3.2_24: Restore universal versioned GitHub titles`;
- post-merge `main` integrity confirms the final subject and core identity.
