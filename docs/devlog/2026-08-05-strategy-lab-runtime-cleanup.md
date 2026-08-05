# 2026-08-05 — Strategy Lab proof-based runtime cleanup

Patch candidate: `v0.3.2_26`.

Implemented one focused lifecycle correction for the temporary Strategy Lab `dvtws2` runtime. Cleanup now preserves PID evidence until process termination and divert-port release are proven, discovers reserved runtimes even when the PID file is stale or missing, escalates TERM to KILL within bounded waits, and fails closed when residue remains.

Candidate startup now requires the expected executable and reserved port identity, an occupied divert socket, a clean startup log, and survival through a readiness window.

Verification is supplied by `scripts/test-strategy-lab-runtime-cleanup.sh` and is wired into the mandatory domain-diagnostics contract suite. The next patch remains blocked until GitHub CI and package build for this commit complete successfully.
