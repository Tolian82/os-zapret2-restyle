# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_14.pkg`

- Patches 1–11: complete and merged.
- Patch 11 merged as `c178106c02ee1fc3c849a6d174fe881d84c4a704`; task branch removed.
- Patch 12: temporary circular live validation in delivery.
- Patch 13: blocked by the serial gate.

Patch 12 adds a separate temporary circular-validation session for a completed domain Strategy Lab job with a shortlist of three to five stable candidates. It uses one target-scoped dvtws2 runtime, upstream Zapret2 `circular`, bidirectional firewall interception, a bounded TTL, explicit stop/status actions, and mandatory restoration of the exact initial Zapret2 service state. It never changes the saved Traffic Strategy. `VERSION=0.3.2`; `PLUGIN_REVISION=14`; no release publication is authorized.

Next action: completely process Patch 12 before Patch 13.
