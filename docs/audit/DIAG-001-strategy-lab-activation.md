# DIAG-001 — Strategy Lab replaces synchronous Blockcheck

Classification: source remediated / automated integration verified / requires live OPNsense verification

This specialist record supersedes the historical synchronous Blockcheck chain. Current behavior is governed by the corrective Strategy Lab contract and its audit.

## Active source chain

```text
Diagnostics GUI
  -> StrategyLabController
  -> short configd action
  -> detached lifecycle-owned worker
  -> stages 00–99
  -> persistent status/result polling
  -> optional backend-authorized circular validation
```

The synchronous `blockcheck.sh` wrapper, configd action, MVC action, and ten-minute browser request are absent from the active and fallback architecture.

## Verified source remediation

Candidate `0.3.2_24` has passed focused tests, the complete mock-driven API/configd-to-worker matrix, project validation, and FreeBSD package build. The source contract includes:

- normalized domain-only targets;
- atomic cancellation and active process-tree termination;
- bounded standard and extended deadlines;
- explicit terminal states and outcomes;
- mandatory semantic restoration and temporary-state cleanup;
- page-reload recovery of the newest persisted job;
- circular eligibility only after completed `SUCCESS`, stages 85 and 90 PASS, verified restoration, and a valid three-to-five-item shortlist;
- saved Traffic Strategy immutability.

## Remaining live verification

DIAG-001 remains open only for the consolidated owner-assisted OPNsense matrix in `docs/ROADMAP.md`. No release is authorized before that evidence is recorded.
