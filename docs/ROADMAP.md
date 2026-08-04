# os-zapret2-restyle — Roadmap

Milestone 8 current package candidate: `v0.3.2_10`.

Strict Strategy Lab serial gate: a later patch starts only after the previous patch passes PR title validation, Validate Project, FreeBSD package build, squash merge, `main` verification, task-branch removal, and all remaining GitHub processing.

Patch status:

- Patches 1–7: COMPLETE.
- Patch 8 — Stability, shortlist, and report: IN DELIVERY.
  - [x] Three sequential fresh-connection attempts.
  - [x] Sequential endpoint confirmation.
  - [x] Stable only after 3 of 3 complete passes.
  - [x] Persist partial stability results.
  - [x] Rank by stability and simplicity.
  - [x] Shortlist up to five and recommendation number one.
  - [x] Focused stability/shortlist regression.
  - [x] Package candidate `0.3.2_10`.
- Patch 9 — Extended TLS 1.2 and HTTP: BLOCKED BY PATCH 8 GATE.
- Patch 10 — QUIC strategy branch: BLOCKED.
- Patch 11 — Arbitrary UDP strategy branch: BLOCKED.
- Patch 12 — Temporary circular live validation: BLOCKED.
- Patch 13 — Final synchronous Blockcheck replacement: BLOCKED.

Owner-assisted OPNsense verification follows Patch 13.
