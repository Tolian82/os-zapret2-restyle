# 2026-08-05 — Strategy Lab Patch 12

Implemented temporary circular live validation for completed domain Strategy Lab jobs.

The session accepts only a shortlist of three to five stable candidates and builds one target-scoped dvtws2 profile using the upstream Zapret2 `circular` orchestrator. Incoming and outgoing TCP/443 traffic is intercepted so the failure detector can rotate strategies. The saved Traffic Strategy is never modified.

The launcher exposes start, status, and stop operations. The worker owns the shared lifecycle lock for the complete session, applies a bounded TTL, cleans temporary runtime and firewall state, and restores the exact initial Zapret2 service state on normal stop, timeout, signal, launch failure, or runtime failure. Stale workers and lifecycle-lock failures are reported explicitly.

Patch 13 remains responsible for connecting the Diagnostics GUI to the asynchronous Strategy Lab API and retiring the synchronous Blockcheck path.
