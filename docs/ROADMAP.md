# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-09-01

- Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md)
- Exact handoff: [`START_HERE.md`](START_HERE.md)
- Current-line detail: [`history/current/v0.5.x.md`](history/current/v0.5.x.md)

## Completed project path

- [x] Initial OPNsense plugin and independent project identity
- [x] Runtime/service lifecycle and transactional Apply
- [x] Unified Traffic Strategy and managed HOSTLIST/IPSET targets
- [x] Zapret2 Service GUI for upstream install/update/reinstall/downgrade
- [x] Diagnostics fixes and blockcheck redesign
- [x] Strategy Lab foundation and Python migration
- [x] Adaptive candidate search and timeout/budget containment
- [x] Model A/B/C experimentation and **Model C selection**
- [x] Model-C-only normal production execution
- [x] Source-port attribution/leasing and readiness hardening
- [x] Lua/BLOB/discovery measurement cycle and production decisions
- [x] Generic UDP exact-byte path and QUIC execution observability
- [x] Explicit persisted **Enable QUIC** execution control
- [x] Enable QUIC ON/OFF execution semantics
- [x] **Enable QUIC preference reload/revisit persistence — OWNER-LIVE PASS**
- [x] Strategy Lab RU/EN presentation and native OPNsense Laboratory layout
- [x] Laboratory domain + IPv4 targets with optional Host/SNI
- [x] Truthful HTTP `4xx`/`5xx`, bare-IP identity and QUIC result classification
- [x] Final fixed-IP `--ipset-ip=<target>` profile/replay
- [x] Selected Stage-90 restoration/residue owner-live coverage
- [x] `v0.4.x` owner-live feature closeout

## `v0.5.0_1` release transition — COMPLETE

- [x] owner explicitly selected second-component transition `v0.4.x -> v0.5.x`
- [x] close Enable QUIC preference persistence from owner confirmation
- [x] set `VERSION=0.5.0`
- [x] reset `PLUGIN_REVISION=1`
- [x] roll current documentation to `v0.5.x`
- [x] archive final `v0.4.x` line
- [x] complete README release review and feature presentation
- [x] exact-head complete CI — run `31915884270`
- [x] FreeBSD 15 package qualification — run `31915884270`
- [x] exact squash merge `v0.5.0_1: Prepare release v0.5.0` — `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`
- [x] immutable stable tag `v0.5.0` points to the exact release merge
- [x] stable GitHub Release package/checksum publication — workflow `31916256043`
- [x] matching Pages/pkg repository deployment and verification — workflow `31916256043`

Stable package: `os-zapret2-restyle-0.5.0_1.pkg`.

SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`.

Full release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

## `v0.5.0_2` file-picker localization corrective — COMPLETE

Fresh owner evidence selected a concrete post-release defect: the visible Generic UDP browser-native file picker could show Russian browser/OS labels while OPNsense/Strategy Lab was set to English.

- [x] identify browser-native `<input type="file">` chrome as the localization leak
- [x] keep the real native input only as the hidden file-selection mechanism
- [x] add Strategy Lab-owned RU/EN picker button and filename text
- [x] preserve selected filename, busy-state disabling, FileReader/Base64 staging and 1–4096-byte validation
- [x] add regression coverage forbidding return of the visible native `form-control` file picker
- [x] exact-head complete CI — run `31917466421`
- [x] FreeBSD 15 package qualification — run `31917466421`
- [x] exact squash merge for `v0.5.0_2` — `1ae952185dbae80ec34c0a89b441feddbe8b403a`
- [x] persistent GitHub testing-package publication — `v0.5.0_2`, workflow `31917806438`
- [x] bounded publication-record reconciliation — PR `#270` merged, generated evidence state closed afterward
- [x] focused owner-live RU/EN file-picker verification — **OWNER-LIVE PASS**

Testing package: `os-zapret2-restyle-0.5.0_2.pkg`.

SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

Owner-live evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

The stable Pages/pkg repository remains on `v0.5.0_1`; `_2` was not automatically promoted.

## Telegram voice / UDP DPI-bypass — PHASE B SOURCE COMPLETE, LIVE GATE OPEN

Owner-selected authority: [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

- [x] establish Telegram signaling versus WebRTC/STUN/TURN/P2P/reflector traffic model
- [x] inspect `Waujito/youtubeUnblock`, `remittor/zapret-openwrt` and native `bol-van/zapret2` behavior/boundaries
- [x] separate universal STUN recognition from provider-specific DPI-bypass effectiveness
- [x] reject global UDP/443 drop and global all-UDP userspace interception as Telegram Voice defaults
- [x] define the bounded Telegram-IP-scoped hybrid architecture
- [x] owner authorized and completed Phase A with P2P disabled on both clients
- [x] identify live Telegram-range TURN and reflector destinations/ports
- [x] establish that both observed UDP candidates were outbound-only
- [x] establish that working two-way sound was masked by concurrent TCP/SOCKS fallback
- [x] record that the exact upstream DPI/filtering mechanism remains unclassified
- [x] record the separate Telegram Reflector Hello versus Zapret2 STUN-classification boundary
- [x] preserve redacted owner-live evidence without committing the raw PCAP

Phase A evidence: [`verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md`](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md).

### Phase B — source PoC implemented, owner-live evidence pending

- [x] implement the small plugin-owned Telegram IPv4 `ipfw` table with atomic staging/swap
- [x] divert all destination-port UDP only toward that table through the existing dvtws2 socket
- [x] add the official STUN zero-fake/repeats=2 profile with deterministic first-profile ordering and both L7/profile and payload/Lua guards
- [x] expose temporary configd control and IPFW packet/byte counters without adding the production GUI
- [ ] run P2P-disabled helper OFF/ON/OFF comparison
- [ ] require inbound TURN/STUN plus sustained bidirectional Telegram UDP for PASS
- [x] cover exact rule/table/profile cleanup and failed-install table rollback synthetically
- [ ] verify exact rule/table/profile cleanup on the owner-live appliance
- [ ] investigate Telegram Reflector handling only if restored TURN replies are insufficient

The Phase B implementation is the `v0.5.0_3` source candidate. It remains default OFF and is not product-accepted before the packet-based live gate.

## Remaining regression / future backlog

These rows remain useful coverage or future product directions. They are **not** silently release debt for the completed stable `v0.5.0` release.

- [ ] cancellation/internal-failure containment regression
- [ ] circular lifecycle start/stop/TTL and stale-session recovery
- [ ] broader Diagnostics persistence/reload regression
- [ ] retention/cleanup boundary regression
- [ ] reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up as new evidence requires
- [ ] package/runtime version visibility follow-up
- [ ] RU/EN review beyond explicitly selected localization defects
- [ ] IPv6 Laboratory target support — requires a separate explicit architecture scope
- [ ] Additional BLOB repository GUI — wait for owner-supplied/approved technical contract

## Deferred research — do not reactivate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only for a concrete defect or explicit owner selection

## Current priority

**Install and owner-live qualify the exact `0.5.0_3` Phase B candidate with a P2P-disabled OFF/ON/OFF call cycle.** The live baseline is complete and the bounded PoC is implemented; PASS/FAIL must be based on helper counters, inbound TURN/STUN and sustained bidirectional Telegram UDP, not sound alone.

Release notes for the current stable release: [`releases/v0.5.0.md`](releases/v0.5.0.md).
