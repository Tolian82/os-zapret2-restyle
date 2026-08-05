# 2026-08-05 — Unified Strategy Lab shortlist

Patch candidate: `v0.3.2_35`.

Stage 85 now consumes all verified protocol branches produced before it. Standard mode remains TLS 1.3-only. Extended mode selects one best exact-replayed profile for each available protocol in the fixed order TLS 1.3, TLS 1.2, HTTP, QUIC, and configured UDP.

The exact-profile replay runner now activates the correct temporary runtime, firewall, and endpoint probe implementation for each protocol. Generic UDP domain output is bound to the selected IPv4 evidence because it has no domain-layer selector.

The user-visible list and the circular-test input are separated. `items` contains the unified display list, while `circular_items` contains only three-to-five TLS 1.3 candidates. Existing historical TLS 1.3-only shortlist files remain accepted.

Focused verification is provided by `scripts/test-strategy-lab-unified-shortlist.sh` and is wired into the mandatory domain-diagnostics suite. Patch `_36` remains blocked until all GitHub checks and the FreeBSD package build for `_35` complete successfully.
