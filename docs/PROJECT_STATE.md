# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_13.pkg`

- Patches 1–10: complete and merged.
- Patch 10 merged as `4c47c15739ee146b0e48db0f9b3d14c4d3739c2b`; task branch removed.
- Patch 11: configured request-response UDP branch in delivery.
- Patches 12–13: blocked by the serial gate.

Patch 11 requires explicit UDP port and request payload, otherwise records a safe skip. Configured testing requires a response and uses sequential Zapret2 UDP-fragment candidates. `VERSION=0.3.2`; `PLUGIN_REVISION=13`; no release publication is authorized.

Next action: completely process Patch 11 before Patch 12.
