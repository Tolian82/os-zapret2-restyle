# Release v0.3.2 preparation

Date: 2026-08-03

Base release commit:
`c0208cc7286f320167f735099a7de48b9177b734`

==================================================
SCOPE
==================================================

Prepare the owner-approved forward release v0.3.2 as a governance and documentation
patch. Runtime code and plugin behavior remain identical to the live-verified v0.3.1
baseline.

==================================================
RELEASE METADATA
==================================================

- `VERSION`: 0.3.2
- `PLUGIN_REVISION`: 1
- expected tag: `v0.3.2`
- expected package: `os-zapret2-restyle-0.3.2_1.pkg`
- repository target: `FreeBSD:15:amd64`

==================================================
COMPLETED DOCUMENTATION WORK
==================================================

- Recorded successful owner live verification of v0.3.1 / package 0.3.1_1.
- Closed DIAG-002 as resolved and live verified.
- Added `GITHUB_PUBLICATION.md` to the mandatory reading order.
- Made one ready PR and one check set the default instead of Draft → Ready.
- Added explicit delivery-stage gates.
- Required exact release authority and prohibited inferred version choice.
- Recorded immutable forward-only release progression with no version rollback.
- Distinguished package-candidate PR titles from release squash subjects.
- Required one blobs/tree/commit operation for multi-file API publication.
- Required failed delivery cycles to be closed and replaced rather than repaired.
- Required complete release/pkg-repository verification before installation commands.

==================================================
RELEASE PROTOCOL
==================================================

Pull-request title:

`v0.3.2_1: Improve GitHub publication discipline`

Squash subject:

`release: prepare v0.3.2`

The pull request is opened ready for review only after the final atomic commit exists.
The branch remains unchanged during one complete check set.

==================================================
VERIFICATION PLAN
==================================================

1. Validate the final changed-file scope and atomic parent relationship.
2. Pass the PR-title workflow on the first `opened` event.
3. Pass the complete CI validation and FreeBSD package build once.
4. Squash merge with the exact release subject.
5. Verify tag, Release trigger, Release workflow, package, checksum, and Pages/pkg
   repository.
6. Provide installation guidance only after the exact 0.3.2_1 package is public.
