# Strategy Lab Diagnostics activation

The Diagnostics page uses the asynchronous Strategy Lab API as the only strategy-finding path.

## User flow

1. Enter a blocked domain and select Standard or Extended mode.
2. Start the job; the API returns `job_id` immediately.
3. The page polls status once per second and renders stages 00–99.
4. Stop requests set the cancellation flag; cleanup and exact Zapret2 restoration still run.
5. A completed job displays stable candidates and recommendation number one.
6. For domain jobs with three to five candidates, temporary circular validation may be started and stopped from the page.
7. The user manually reviews a candidate before changing the saved Traffic Strategy.

## Removed path

The synchronous `blockcheck.sh` wrapper, `zapret blockcheck` configd action, `blockcheckAction`, and ten-minute browser request are not part of the active or fallback architecture.

## Safety

Strategy Lab and circular validation share the Zapret2 lifecycle lock, use target-scoped temporary firewall rules, preserve partial structured results, and restore the exact initial service state. Circular validation never writes the saved Traffic Strategy.
