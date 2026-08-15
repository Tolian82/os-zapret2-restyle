# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.x` selected owner-live scope closed; `v0.5.0_1` release preparation uses that accepted runtime basis.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace owner-live evidence for rows that require appliance behavior.

## Accepted baseline and execution rows

| Scenario | Result |
|---|---|
| Standard blocked domain, initial Zapret2 RUNNING | **PASS** |
| Standard blocked domain, initial Zapret2 STOPPED | **PASS** |
| Extended TLS 1.2 / HTTP semantics | **PASS** |
| Model C normal production execution | **PASS / LOCKED** |
| QUIC ON candidate execution/observability | **OWNER-LIVE PASS** |
| QUIC OFF execution suppresses QUIC catalog | **OWNER-LIVE PASS** |
| Generic UDP exact-byte path | **OWNER-LIVE PASS** |
| Enable QUIC saved state survives Laboratory reload/revisit | **OWNER-LIVE PASS — 2026-08-16** |
| Laboratory native OPNsense frame and RU/EN navigation | **OWNER-LIVE PASS** |
| Target already accessible | **COMPLETE BY OWNER CONFIRMATION** |
| Settings Apply validation/guards and service-state correctness | **COMPLETE BY OWNER CONFIRMATION** |

Enable QUIC persistence evidence: `docs/verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md`.

## `_23` truthful-result / domain / IPv4 closeout

| Scenario | Result |
|---|---|
| `rutracker.net` stable finalists survive Stage 85 with HTTP `502` | **OWNER-LIVE PASS — `job.9juf8H`** |
| `rutracker.org` ordinary-domain regression | **OWNER-LIVE PASS — `job.TYjdSR`** |
| additional negative domain control (`telegram.org`) | **OWNER-LIVE PASS — truthful `NO_CANDIDATE`** |
| bare IPv4 certificate-identity failure | **OWNER-LIVE PASS — `PARTIAL` + Host/SNI guidance, `job.3HeCEP`** |
| IPv4 + real Host/SNI remains pinned to entered destination | **OWNER-LIVE PASS — `job.W0lKTv`** |
| final working IP profile contains `--ipset-ip=<target>` and exact replay | **OWNER-LIVE PASS — `job.W0lKTv`** |
| Extended Generic UDP against bare IPv4 | **OWNER-LIVE PASS — `job.HNnp5P`** |
| bare-IP QUIC without Host/SNI | **OWNER-LIVE PASS — SKIPPED, zero tested candidates** |
| Host/SNI QUIC fixed-IP hostname-verified attempts | **OWNER-LIVE PASS — four real candidates attempted** |
| Stage-90 cleanup/restoration after selected IP runs | **OWNER-LIVE PASS** |

Durable closeout evidence: `docs/verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`.

## Remaining regression inventory

These rows remain useful future regression coverage and are not silently promoted to mandatory release gates:

- cancellation/internal-failure containment;
- circular lifecycle start/stop/TTL and stale-session recovery;
- broader retention/reboot residue coverage;
- broader Diagnostics persistence/reload coverage.

## Release use

The owner explicitly selected `v0.5.0_1` after the current selected owner-live scope was closed. The release-preparation patch changes version/release metadata and documentation only; it does not introduce new runtime behavior requiring a replacement live matrix.
