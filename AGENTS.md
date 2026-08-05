# AGENTS.md

This repository has a mandatory, risk-based documentation preflight.

Before project work:

1. Read this file, `docs/INDEX.md`, and `docs/PROJECT_STATE.md`.
2. Read only the specialist documents relevant to the requested scope.
3. Read `docs/GITHUB_PUBLICATION.md` immediately before a GitHub mutation.
4. Treat the project owner's current instruction as the highest scope boundary.
5. Use current repository state and GitHub data; chat history is supporting context only.

A complete read of every audit, decision, devlog, architecture, roadmap, and requirement
file is required only for a repository-wide audit or genuine full-context recovery. It is
not a blocking prerequisite for every diagnosis, command, or small change.

==================================================
GITHUB DELIVERY RULES
==================================================

`docs/GITHUB_PUBLICATION.md` is the final authority for GitHub delivery mechanics.
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` supersedes earlier active
wording that required one unpublished commit, one CI run, immediate PR abandonment after
a failure, or complete suspension of later analysis while checks run.
`docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` controls title and
commit-subject identity for every GitHub-delivered change.

Default ordinary delivery:

one logical change
        ↓
one task branch and one pull request
        ↓
focused local/static validation
        ↓
required checks for the latest PR state
        ↓
one squash merge into `main`
        ↓
verify the resulting `main`

Rules:

- Keep one logical scope per pull request.
- A PR branch may contain multiple same-scope work or repair commits. The permanent
  `main` history remains one logical commit through squash merge.
- Every PR title, every work or repair commit subject in the PR branch, and the final
  squash commit subject in `main` must begin with the exact current package-candidate
  prefix `v<VERSION>_<PLUGIN_REVISION>:` derived from the PR head. This applies to code,
  documentation, governance, CI, maintenance, and release-preparation changes alike.
- Governance/documentation/CI-only changes do not increment `VERSION` or
  `PLUGIN_REVISION`; they use the unchanged current package-candidate prefix.
- Open a Ready PR when the content is ready for review and merge. Draft is reserved for
  intentional work in progress or early design discussion.
- CI success is required for the latest mergeable PR state, not for every historical
  commit or workflow run.
- A same-scope failure is normally repaired in the same branch and PR. Close and replace
  a PR only when its base, scope, or history is materially wrong or the change is
  abandoned.
- While CI runs, independent analysis and preparation may continue separately. Do not
  mutate the checked PR with unrelated work and do not merge a dependent successor
  before its prerequisite is integrated.
- Before merge, verify that the intended squash subject retains the exact package-
  candidate prefix used by the PR title. Never substitute an unversioned conventional
  subject such as `docs:`, `ci:`, `governance:`, or `chore:`.
- Use expected head SHA when merging. Never force-update `main`.
- Branch cleanup is repository hygiene. Cleanup failure must be diagnosed, but it does
  not invalidate an otherwise successful code merge.
- Use repository-native auto-merge and automatic head-branch deletion when enabled;
  otherwise use the documented connector/manual merge and cleanup fallback.
- No specific client is mandatory. Select the available GitHub connector/API, local
  `git`, or `gh` according to the operation and verified permissions.

==================================================
REQUEST SCOPE AND AUTHORIZATION
==================================================

- analyse, diagnose, explain, review, audit: inspect and report; do not mutate.
- patch only, branch only, PR only: stop at the named boundary.
- fix, add, change, implement, complete: perform the ordinary branch → PR → checks →
  squash-merge → verification cycle unless the owner states a stopping point.
- release version X.Y.Z: perform the authorized release pipeline for that exact version.

Do not ask for routine branch names, commit messages, PR text, test selection, CI
inspection, same-scope repair, squash merge, or temporary branch cleanup when the owner
has authorized the ordinary delivery cycle.

Stop for owner input only on material product/architecture ambiguity, relevant unpublished
owner state, unavailable credentials or protected authority, destructive changes to user
data or pre-existing remote objects, history rewriting/direct-main publication, an
unresolvable required-check failure, or mandatory live OPNsense evidence available only
from the owner.

==================================================
PATCH AND RELEASE BOUNDARY
==================================================

A package patch and a project release are different operations.

- An ordinary packaged change keeps `VERSION`, increments `PLUGIN_REVISION` once, and
  creates no tag, GitHub Release, release asset, or pkg-repository publication.
- A governance/documentation/CI-only change outside packaged plugin contents changes
  neither `VERSION` nor `PLUGIN_REVISION`.
- A project release changes `VERSION`, resets `PLUGIN_REVISION` to `1`, and requires
  explicit owner authorization for that exact version.
- Published tags, releases, assets, and versions are immutable and forward-only.

All three change classes still use the exact current package-candidate prefix in PR and
commit subjects.

==================================================
OPNSENSE COMMAND RULE
==================================================

OPNsense console commands target the default root `csh` shell. POSIX-only syntax must be
placed between an explicit standalone `sh` command and a matching standalone `exit`.
