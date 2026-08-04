# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Repository: https://github.com/Tolian82/os-zapret2-restyle
Primary branch: `main`
Published release: `v0.3.2`
Published package: `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_10.pkg`
Delivery stage: `DEVELOPMENT`

Strategy Lab serial baseline:

- Patches 1–7: complete and merged.
- Patch 7 merged as `ebccb91c7b4d5421ef7667bebbe759a88a1d78ed`; task branch removed.
- Patch 8: stability confirmation, shortlist, and recommendation in delivery.
- Patches 9–13: blocked by the serial gate.

Patch 8 requires three sequential fresh-connection passes for each stable candidate, sequential endpoint confirmation, a bounded shortlist of up to five candidates, and explicit recommendation number one. It keeps the legacy synchronous Blockcheck active and does not enable extended protocols or the dormant GUI.

`VERSION=0.3.2` remains unchanged. `PLUGIN_REVISION=10`. No release publication is authorized.

Next action: publish and completely process Patch 8 before preparing Patch 9. Owner-assisted OPNsense verification remains deferred until all 13 patches complete.
