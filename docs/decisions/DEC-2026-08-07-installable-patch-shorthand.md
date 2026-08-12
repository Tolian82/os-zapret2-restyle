# DEC-2026-08-07 — Installable patch shorthand

Status: **ACCEPTED / TRIGGER BROADENED 2026-08-13**

The publication mechanics in this decision remain active. The narrow phrase-matching trigger is superseded by `DEC-2026-08-13-github-only-package-delivery.md`.

## Decision

For this project, an owner request for a package/patch deliverable — including but not limited to:

- `дай мне патч для установки`;
- `дай мне ссылку для установки патча`;
- `дай мне команду для установки патча`;
- `собери патч для установки`;
- `пакет`;
- `пакет для тестирования`;
- `тестовый пакет`;
- `дай пакет`;
- `собери пакет`;
- equivalent wording that clearly requests package bytes for owner testing, installation, or delivery,

means: complete the whole testing-package publication cycle and return a persistent direct GitHub `.pkg` URL or csh-safe OPNsense `.pkg` installation command.

The instruction itself is explicit owner authorization for the deterministically selected exact testing-package tag and its single `.pkg` asset. No second publication confirmation is required.

The owner's wording `не релиз, а пакет` means no stable/full project release, no semantic `VERSION` promotion, no Pages and no pkg-repository promotion. It does **not** mean stop at a GitHub Actions artifact. The testing `.pkg` must still be persistently hosted on GitHub. The technical GitHub prerelease/tag used to hold that `.pkg` is a package-delivery container, not a stable/full project release.

Candidate selection:

1. Read current `main`, `VERSION`, and `PLUGIN_REVISION`.
2. If the current candidate is complete and unpublished, publish that exact candidate.
3. If additional packaged changes are required, create the next `PLUGIN_REVISION` through the normal Ready PR, CI, FreeBSD 15 package build, squash merge, and verification flow, then publish it.
4. Documentation/governance-only clarification does not by itself require a new package revision.

Publication uses the repository-owned testing-package mechanism. When repository-owned build-and-publish automation is needed, `publish/v<VERSION>_<REVISION>` and `.github/workflows/publish-prerelease.yml` build on FreeBSD 15, validate `+MANIFEST`, create the testing package prerelease, upload the `.pkg`, verify the GitHub asset, and delete the temporary publication branch.

When already verified package bytes exist, the evidence-first publication rules may reuse them directly instead of rebuilding.

The normal user-facing result is one command of this form:

`pkg add -f https://github.com/Tolian82/os-zapret2-restyle/releases/download/v<VERSION>_<REVISION>/os-zapret2-restyle-<VERSION>_<REVISION>.pkg`

Do not substitute GitHub Actions ZIP artifacts, token setup, archive extraction, local/container/sandbox files, or multi-step artifact-download instructions when the owner asks for a package.

## Boundaries

This shorthand does **not** authorize:

- a stable/full project release;
- an unrelated semantic `VERSION` change;
- GitHub Pages publication;
- pkg-repository promotion;
- unrelated source changes;
- rewriting or replacing an already published immutable candidate.

An owner request that explicitly says **build/CI evidence only and no package delivery** is the narrow exception that may stop at an Actions artifact.

## Reason

The owner uses package/patch wording as an operational request for a persistent GitHub deliverable, not as a request for an expiring CI artifact. Earlier wording listed only installation-specific phrases, which left `пакет для тестирования` ambiguous and allowed an incorrect Actions/sandbox delivery. A persistent GitHub `.pkg` gives the intended project-owned installation path and keeps package identity tied to repository history and documentation.

## Consequences

- `docs/GITHUB_PUBLICATION.md` defines all owner package requests as GitHub package-delivery authority unless the owner explicitly requests CI evidence only.
- `DEC-2026-08-13-github-only-package-delivery.md` controls the broader trigger and required-document EOF rule.
- Future assistants must resolve the current candidate from GitHub state and complete package publication without asking for redundant confirmation.
- Final responses should default to the direct GitHub `.pkg` URL or csh-safe `pkg add -f` command after publication verification.
