# Strategy Lab Diagnostics activation

The Diagnostics page uses the asynchronous Strategy Lab API as the only strategy-finding path.

## User flow

1. Enter a blocked domain and select Standard or Extended mode.
2. Start the job; the API returns `job_id` immediately.
3. The page polls status and renders stages 00–99, State, Outcome, and the retained structured result.
4. Stop requests persist cancellation, terminate the active bounded runner, and continue mandatory cleanup and restoration.
5. Reloading the page resumes an active job. With no active job, automatic discovery reports idle; an explicitly selected retained job remains available by its validated ID. See [persisted-result contract](STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md).
6. A completed `SUCCESS` job displays the stable shortlist and recommendation number one.
7. Temporary circular validation is available only when backend eligibility confirms a domain target, stages 85 and 90 PASS, verified restoration, and a three-to-five-item shortlist.
8. The user manually reviews a candidate before changing the saved Traffic Strategy.

## Removed path

The synchronous `blockcheck.sh` wrapper, `zapret blockcheck` configd action,
`blockcheckAction`, and ten-minute browser request are not part of the active or fallback
architecture.

## Safety

Strategy Lab and circular validation share the Zapret2 lifecycle lock, use target-scoped
temporary firewall rules, preserve partial structured evidence, and verify semantic
restoration. Circular validation never writes the saved Traffic Strategy.

GitHub delivery follows the canonical [GitHub rules](../GITHUB_PUBLICATION.md), not a second policy in this subsystem.

## Source history

The [full original page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_ACTIVATION.md) preserves earlier source versions, investigation notes and acceptance claims at their actual dates. [PROJECT_STATE](../PROJECT_STATE.md) owns current evidence; this page owns its bounded technical contract.
