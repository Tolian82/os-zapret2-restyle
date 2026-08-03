# Release v0.3.1 completion and live verification

Date: 2026-08-03

Implementation commit:
`fe518e7a4ebbfe827ca41d107fda8f7e4fcb8666`

Release merge:
`c0208cc7286f320167f735099a7de48b9177b734`

==================================================
SCOPE
==================================================

Publish and verify the DIAG-002 correction that preserves complete negative Test Domain
Connectivity output.

==================================================
RELEASE METADATA
==================================================

- `VERSION`: 0.3.1
- `PLUGIN_REVISION`: 1
- tag: `v0.3.1`
- package: `os-zapret2-restyle-0.3.1_1.pkg`
- repository target: `FreeBSD:15:amd64`

==================================================
PUBLICATION
==================================================

Completed:

- release-preparation pull request merged with subject `release: prepare v0.3.1`;
- repository trigger created annotated tag `v0.3.1` at the release merge;
- Release workflow completed successfully;
- package, `SHA256SUMS`, GitHub prerelease, and Pages/pkg repository were published.

==================================================
OWNER LIVE VERIFICATION
==================================================

The project owner personally checked package `0.3.1_1` and explicitly confirmed on
2026-08-03 that everything in the release works correctly.

This owner evidence closes the pending DIAG-002 live-verification gate. The positive
and negative domain-diagnostic result path is accepted as working, and no rollback or
replacement of v0.3.1 is required.

==================================================
PROCESS LESSON
==================================================

The released plugin was correct, but its GitHub preparation produced avoidable noise:

- release intent was inferred too broadly;
- the first PR title used the release squash subject instead of the package-candidate
  title;
- title edits and Ready transitions generated redundant workflow runs;
- multi-file preparation used sequential contents-API commits.

The owner approved a corrected forward-only workflow for v0.3.2. The active procedure
is now maintained in `docs/GITHUB_PUBLICATION.md`.
