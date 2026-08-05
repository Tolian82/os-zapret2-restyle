# DEC-2026-08-05 — Universal versioned GitHub titles

Status: Active
Date: 2026-08-05

## Context

The project owner previously approved a permanent rule that all visible GitHub delivery
names identify the current working package candidate. The governance patch merged in PR
#82 unintentionally weakened that rule by allowing unversioned conventional titles such
as `governance:`, `docs:`, `ci:`, and `chore:` for non-packaged changes. The same PR was
then squash-merged with the unversioned subject `governance: modernize GitHub delivery`.

The merged commit remains immutable and is retained as historical evidence. Rewriting
`main` to rename it would violate the project's no-history-rewrite rule.

## Decision

Restore and strengthen universal package-candidate identity.

1. Derive the current title prefix from the proposed PR head:
   - `VERSION` provides the semantic version;
   - `PLUGIN_REVISION` in `Makefile` provides the source/package revision;
   - non-zero revision format: `v<VERSION>_<PLUGIN_REVISION>:`;
   - zero revision format: `v<VERSION>:`.
2. Require the exact derived prefix at the start of:
   - every pull-request title;
   - every work commit subject in the PR branch;
   - every same-scope repair commit subject in the PR branch;
   - every final squash commit subject in `main`.
3. Apply the rule to every project change class:
   - runtime or product code;
   - package and repository inputs;
   - documentation;
   - governance;
   - CI and workflow automation;
   - maintenance and cleanup;
   - release preparation.
4. Governance/documentation/CI-only changes do not increment `VERSION` or
   `PLUGIN_REVISION`; they use the unchanged current package-candidate prefix.
5. Conventional type words may appear only after the required prefix when useful, for
   example `v0.3.2_24: CI — enforce versioned commit subjects`.
6. Explicit squash merge operations must pass or preserve the exact versioned title.
   An operator must not replace a valid PR title with an unversioned squash subject.

## Enforcement

- `.github/workflows/pr-title.yml` validates the PR title and every commit subject between
  the PR base and head.
- `.github/workflows/ci.yml` validates the final pushed `main` commit subject during the
  lightweight post-merge integrity check.
- `scripts/test-github-branch-hygiene.sh` validates that the universal rule is present and
  that unversioned conventional exceptions are absent.

## Consequences

- Every GitHub-visible change can be associated immediately with the exact working
  candidate.
- Documentation and CI changes remain traceable without falsely incrementing package
  metadata.
- Same-scope repair commits remain allowed, but each repair keeps the same package-
  candidate identity.
- A PR cannot pass title checks when any branch commit uses an unversioned subject.
- A wrongly titled squash commit causes the `main` integrity workflow to fail and must be
  recorded and corrected forward; history is not rewritten.

## Supersession and amendment

This decision amends the `Titles and package metadata` subsection of
`DEC-2026-08-05-efficient-github-delivery.md` and supersedes any wording that permits
unversioned project-delivery subjects for governance, documentation, CI, or maintenance
changes.

It does not restore the obsolete one-commit, one-check-set, mandatory Draft, serial-wait,
or close-and-recreate rules.

## Affected controls

- `AGENTS.md`;
- `docs/INDEX.md`;
- `docs/PROJECT_STATE.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
- `.github/workflows/pr-title.yml`;
- `.github/workflows/ci.yml`;
- `scripts/test-github-branch-hygiene.sh`;
- `docs/devlog/2026-08-05-universal-versioned-github-titles.md`.
