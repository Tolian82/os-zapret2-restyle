# Strategy Lab Diagnostics activation

The Diagnostics page uses the asynchronous Strategy Lab API as the only strategy-finding path.

## User flow

1. Enter a blocked domain and select Standard or Extended mode.
2. Start the job; the API returns `job_id` immediately.
3. The page polls status and renders stages 00–99, State, Outcome, and the retained structured result.
4. Stop requests persist cancellation, terminate the active bounded runner, and continue mandatory cleanup and restoration.
5. Reloading the page recovers the active job or newest persisted terminal job.
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

## GitHub delivery authority

The historical serial patch gate in `docs/architecture/STRATEGY_LAB.md` is superseded for
GitHub mechanics. Strategy Lab product and runtime contracts remain applicable, but branch,
PR, CI, repair, merge, and concurrency behavior follows:

- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

In particular, CI gates merge of the latest PR state; it does not prohibit separate
analysis or preparation. Same-scope failures are normally repaired in the same PR, and
squash merge creates the single logical commit in `main`.
