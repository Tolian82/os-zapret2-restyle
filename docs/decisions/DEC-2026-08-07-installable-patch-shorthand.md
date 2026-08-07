# DEC-2026-08-07 — Installable patch shorthand

Status: **ACCEPTED**

## Decision

For this project, owner instructions such as:

- `дай мне патч для установки`;
- `дай мне ссылку для установки патча`;
- `дай мне команду для установки патча`;
- `собери патч для установки`;
- equivalent wording that clearly requests an installable patch from GitHub,

mean: complete the whole testing-prerelease publication cycle and return a direct OPNsense `.pkg` installation command.

The instruction itself is explicit owner authorization for the deterministically selected exact testing-prerelease tag and its single `.pkg` asset. No second publication confirmation is required.

Candidate selection:

1. Read current `main`, `VERSION`, and `PLUGIN_REVISION`.
2. If the current candidate is complete and unpublished, publish that exact candidate.
3. If additional packaged changes are required, create the next `PLUGIN_REVISION` through the normal Ready PR, CI, FreeBSD 15 package build, squash merge, and verification flow, then publish it.
4. Documentation/governance-only clarification does not by itself require a new package revision.

Publication uses the repository-owned `publish/v<VERSION>_<REVISION>` mechanism and `.github/workflows/publish-prerelease.yml`, which builds on FreeBSD 15, validates `+MANIFEST`, creates the testing prerelease, uploads the `.pkg`, verifies the Release, and deletes the temporary publication branch.

The normal user-facing result is one command of this form:

`pkg add -f https://github.com/Tolian82/os-zapret2-restyle/releases/download/v<VERSION>_<REVISION>/os-zapret2-restyle-<VERSION>_<REVISION>.pkg`

Do not substitute GitHub Actions ZIP artifacts, token setup, archive extraction, or multi-step artifact-download instructions when the owner asks for an installable patch.

## Boundaries

This shorthand does **not** authorize:

- a stable release;
- a semantic `VERSION` change;
- GitHub Pages publication;
- pkg-repository promotion;
- unrelated source changes;
- rewriting or replacing an already published immutable candidate.

## Reason

The owner uses “patch for installation” as an operational request, not as a request for a CI artifact. Earlier responses incorrectly exposed Actions artifacts and ZIP/token workflows, causing unnecessary work and ambiguity. A GitHub Release `.pkg` gives the intended one-command OPNsense installation path and matches the established project workflow.

## Consequences

- `docs/GITHUB_PUBLICATION.md` defines the shorthand as explicit publication authority.
- Future assistants must resolve the current candidate from GitHub state and complete the publication without asking for redundant confirmation.
- Final responses should default to the direct `pkg add -f` command after Release verification.
