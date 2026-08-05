# Devlog — Strategy Lab shared time budgets

Date: 2026-08-05
Logical patch: Corrective Patch 6
Package candidate: `0.3.2_20`

## Work completed

- Added a worker-owned absolute search-deadline module.
- Enforced the 150-second standard search budget.
- Added the optional 120-second extended allowance.
- Clipped stage operations to the remaining applicable budget.
- Converted stage 80 from three independent 120-second timeouts to one shared deadline.
- Prevented shortlist construction after the overall search deadline.
- Kept cleanup and restoration outside the search deadline.
- Persisted UTC deadline and budget evidence in the job status document.
- Added deterministic time-budget regression coverage.
- Updated the aggregate diagnostics contract, package revision, audit, patch record, roadmap, and project state.

## Architectural boundary

This patch changes time accounting and timeout enforcement only. It does not change lifecycle snapshot evidence, circular eligibility, target semantics, or the Strategy Lab candidate catalog.

## Next logical patch

Corrective Patch 7 will capture and verify semantic service-state evidence: expected supervisor and dvtws2 presence, active runtime identity, normal firewall ownership, temporary artifact cleanup, and saved Traffic Strategy immutability.
