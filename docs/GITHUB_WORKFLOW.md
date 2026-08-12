# os-zapret2-restyle — GitHub workflow

Official repository: `Tolian82/os-zapret2-restyle`
Primary branch: `main`
Authoritative procedure: `docs/GITHUB_PUBLICATION.md`
Active GitHub-only package-delivery decision:
`docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`
Active evidence-first decision:
`docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`
Active title decision:
`docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`

Read every authority selected for the task completely through EOF. If a tool truncates or clamps a file, fetch the remaining ranges before acting.

## GitHub plugin boundary

Use the connected GitHub plugin first. A narrow fallback is allowed only when the plugin
is responding and one exact function or permission is confirmed missing. If the plugin
is unavailable, non-responsive, or cannot provide the authoritative state required for
safe work, stop GitHub work, inform the project owner, and wait for explicit direction.
Do not switch transports automatically.

At the 2026-08-07 verification the repository returned no configured rulesets. The
current plugin installation returned `403 Resource not accessible by integration` for
repository Actions-permission settings and branch-protection settings. These facts must
be re-verified before being treated as current; the `403` is a connector permission
boundary, not proof that the corresponding GitHub controls are disabled.

## Before every mutation

Inspect current `main`, candidate metadata, relevant PRs and branches, available
workflows, active/failed/successful runs, reusable artifacts, tags, releases, assets, and
actual tool permissions. Do not create a new mechanism until this inventory proves it is
needed.

## Ordinary change

1. record exact `main` SHA and logical scope;
2. derive `v<VERSION>_<PLUGIN_REVISION>:` from the proposed head;
3. prepare and validate one logical change with affected documentation;
4. publish one task branch and one Ready PR;
5. keep same-scope repairs in that PR;
6. require successful checks for the latest mergeable head;
7. squash merge with expected head SHA and the exact versioned subject;
8. verify `main` and remove the temporary task branch.

Draft is optional. A PR branch may contain multiple same-scope commits; `main` receives
one logical squash commit.

## Owner package delivery

Any owner request for package/patch bytes for testing, installation, or delivery means a persistent GitHub-hosted `.pkg`, unless the owner explicitly requests build/CI evidence only and no package delivery.

Examples include `пакет`, `пакет для тестирования`, `тестовый пакет`, `дай пакет`, `собери пакет`, `патч`, and `патч для установки`.

An Actions artifact is intermediate build evidence. It is not final owner delivery and a sandbox/local package link is never the project package.

The wording `не релиз, а пакет` means no stable/full project release, no semantic version promotion, no Pages, and no pkg-repository promotion. It still requires persistent GitHub publication of the requested testing `.pkg`. The technical prerelease/tag used to host it is a testing-package container, not a semantic/full project release.

The package request itself supplies publication authority for the deterministic testing candidate; do not ask for a second confirmation merely because the GitHub storage mechanism uses a prerelease object.

## Testing package publication

Publishing an already verified testing package is not a code PR and is not a full project release.

1. derive the exact candidate from current `main`, `VERSION`, and `PLUGIN_REVISION`;
2. prefer direct GitHub package-asset publication when verified `.pkg` bytes already exist;
3. bind reused Actions artifacts by exact run ID, artifact ID/name, and digest;
4. verify `+MANIFEST` for package version and FreeBSD 15 amd64 identity;
5. publish only the testing `.pkg` asset, without Pages or pkg repository;
6. verify target SHA, tag, prerelease flag, asset, digest/size, and direct URL;
7. document the source/build/publication identity;
8. clean the temporary publication branch.

Use the single generic `.github/workflows/publish-prerelease.yml` only when automated
build-and-publish is actually required. One candidate may have only one active
publication run.

If CI has built the package but persistent GitHub publication has not occurred, call the state `BUILD ARTIFACT READY / GITHUB PACKAGE PUBLICATION PENDING`, not `PACKAGE READY FOR OWNER TESTING`.

## Failure rule

Read the job log before changing anything. A confirmed external GitHub/runner/network
action failure causes no source change and permits at most one unchanged rerun after
recovery. Do not switch runners, create replacement branches, add version-specific
workflows, or schedule unbounded retries without evidence of a source defect.

Loss of GitHub-plugin availability is a separate stop condition: report it to the owner
and do not continue GitHub work through a fallback transport without new explicit
direction.

## Full release

A real release that changes `VERSION` to `X.Y.Z` and resets revision to `1` uses the
release-preparation subject:

`vX.Y.Z_1: Prepare release vX.Y.Z`

The release trigger creates semantic tag `vX.Y.Z` and dispatches the full Release
workflow. Stable release and pkg-repository promotion remain subject to existing product
and live-verification gates.

Current versions, active PRs, package candidates, and next actions belong in
`docs/PROJECT_STATE.md`.
