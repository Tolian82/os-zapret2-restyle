# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_24.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–10 are complete in source.

Completed corrective contracts:

- authoritative corrective architecture and audit baseline;
- atomic localized cancel persistence;
- bounded cancellation of active stage 60, 70, and 80 process trees;
- one explicit monotonic active stage sequence;
- final shortlist built only after applicable extended work;
- truthful terminal state and outcome mapping;
- `SUCCESS` and `NO_CANDIDATE` replace the stale default `PARTIAL`;
- `TIMEOUT`, `ERROR`, and `RESTORE_FAILED` are terminal `error` results;
- final localized messages no longer depend on module load order;
- one absolute 150-second standard search deadline;
- one optional 120-second extended allowance;
- one shared stage-80 deadline across TLS/HTTP, QUIC, and UDP branches;
- cleanup and restoration remain mandatory after search-budget exhaustion;
- initial and final service process, runtime, effective strategy, and normal firewall evidence are compared;
- temporary candidate process and Strategy Lab IPFW cleanup are verified;
- semantic mismatch is terminal `RESTORE_FAILED`;
- circular eligibility requires completed `SUCCESS`, a domain target, stages 85/90 PASS, verified restoration, and a valid 3–5 item shortlist;
- GUI circular controls follow the persisted backend decision only;
- Diagnostics guidance states the enforced 150/270-second limits;
- API, shell, probes, and GUI use one normalized domain-only target contract;
- bare IP, IPv6, URL, host:port, and malformed target inputs are rejected;
- a mock-driven API/configd-to-worker integration gate covers stages 00–99, results, recovery, circular validation, lifecycle outcomes, and cleanup;
- `status -` recovers the newest persisted job after page reload.

Open corrective finding:

- stale repository artifacts and superseded documentation remain to be cleaned.

Corrective authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=24`. No tag, release, release asset, or pkg-repository publication is authorized while the corrective series is active.

Next action: Corrective Patch 11 — repository hygiene and documentation authority cleanup. Owner-assisted live OPNsense verification remains deferred until the corrective source series and its serial GitHub delivery gate are complete.
