# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source candidate: `os-zapret2-restyle-0.3.2_24.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–11 are complete in source.

Completed corrective contracts:

- atomic localized cancellation and bounded termination of active stage 60, 70, and 80 process trees;
- one explicit monotonic stage sequence with truthful terminal state, outcome, and localized messages;
- one 150-second standard deadline and one optional 120-second extended allowance with a shared stage-80 budget;
- semantic service, process, runtime, effective-strategy, firewall, and temporary-state restoration verification;
- backend-authoritative circular eligibility after completed `SUCCESS`, shortlist PASS, and restoration PASS;
- one normalized domain-only target contract across API, shell, probes, and GUI;
- complete mock-driven API/configd-to-worker integration coverage for stages 00–99, polling recovery, result persistence, circular validation, lifecycle outcomes, and cleanup;
- repository artifact hygiene enforced by CI;
- stale tracked backups and superseded remote task/release branches removed;
- historical delivery records explicitly separated from current behavioral authority.

Source status:

- no open Strategy Lab corrective source finding remains;
- no tag, release, release asset, or pkg-repository publication has been made for the corrective source candidate;
- normal steady-state branch authority is `main`; `recovery/base` is preserved separately by decision;
- task branches remain temporary and are removed after squash merge.

Current authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/decisions/DEC-2026-08-05-repository-artifact-hygiene.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=24`. Patch 11 changes repository governance and documentation only, so package metadata remains unchanged.

Next action: run the consolidated owner-assisted live OPNsense verification matrix. Release preparation remains blocked until that evidence is recorded and explicit release authorization is given.
