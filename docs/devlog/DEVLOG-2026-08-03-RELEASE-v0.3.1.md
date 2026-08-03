# Release v0.3.1 preparation

Date: 2026-08-03

Base implementation commit:
`fe518e7a4ebbfe827ca41d107fda8f7e4fcb8666`

==================================================
SCOPE
==================================================

Prepare the verified DIAG-002 correction as a new immutable patch release rather than
moving the existing v0.3.0 tag or replacing its published package.

==================================================
RELEASE METADATA
==================================================

- `VERSION`: 0.3.1
- `PLUGIN_REVISION`: 1
- expected tag: `v0.3.1`
- expected package: `os-zapret2-restyle-0.3.1_1.pkg`
- repository target: `FreeBSD:15:amd64`

==================================================
DOCUMENTATION
==================================================

Synchronized:

- README release and package identity;
- PROJECT_STATE current release and live-verification priority;
- CHANGELOG v0.3.1 entry;
- DIAG-002 audit release status;
- focused v0.3.1 release notes.

==================================================
RELEASE PATH
==================================================

1. Pass release-preparation pull-request CI.
2. Squash merge with exact subject `release: prepare v0.3.1`.
3. Let the repository-owned trigger create annotated tag v0.3.1.
4. Build and verify the package and pkg repository in the Release workflow.
5. Publish the GitHub prerelease, package, SHA256SUMS, and Pages/pkg repository.
6. Upgrade OPNsense and live-verify positive and negative diagnostics rendering.
