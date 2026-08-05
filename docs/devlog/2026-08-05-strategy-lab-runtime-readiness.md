# 2026-08-05 — Strategy Lab candidate readiness evidence

Patch candidate: `v0.3.2_32`.

Candidate startup readiness is now persisted instead of remaining an implicit control-flow check. Every candidate result records the exact temporary `dvtws2` PID, executable and command, reserved divert port, process identity, socket readiness, startup-log cleanliness, and readiness-window stability.

TCP/TLS/HTTP, QUIC, and configured UDP runners attach this evidence to their result and cannot report `all_pass=true` without a fully ready runtime.

Verification is supplied by `scripts/test-strategy-lab-runtime-readiness.sh` and is wired into the mandatory domain-diagnostics contract suite. Patch `_33` remains blocked until GitHub validation and the FreeBSD package build for this commit complete successfully.
