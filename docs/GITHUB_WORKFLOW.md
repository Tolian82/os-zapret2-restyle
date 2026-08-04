# os-zapret2-restyle — GitHub workflow

Official repository: https://github.com/Tolian82/os-zapret2-restyle
Primary branch: `main`
Published release: `v0.3.2`
Published package: `os-zapret2-restyle-0.3.2_1.pkg`
Current patch candidate: `os-zapret2-restyle-0.3.2_10.pkg`

Patch `v0.3.2_10` adds Strategy Lab stability confirmation and shortlist construction. It is an ordinary package patch: keep `VERSION=0.3.2`, set `PLUGIN_REVISION=10`, and create no tag, GitHub Release, release asset, or pkg-repository publication.

Mandatory delivery remains:

one logical change → all blobs → one tree → one atomic commit → one final task branch → one ready PR → complete checks → one squash merge → automatic branch deletion → verified `main`.

PR title:

`v0.3.2_10: Add Strategy Lab stability shortlist`

Patch 9 may not start until Patch 8 completes the full serial gate in `docs/GITHUB_PUBLICATION.md` and `docs/architecture/STRATEGY_LAB.md`.
