# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-09-04

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

## Telegram voice / UDP DPI-bypass — PHASE C EMULATION ORACLE SELECTED

Owner-selected authority: [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

Current architecture: [`architecture/TELEGRAM_VOICE_EMULATION_LAB.md`](architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

- [x] establish Telegram signaling versus WebRTC/STUN/TURN/P2P/reflector traffic model
- [x] inspect `Waujito/youtubeUnblock`, `remittor/zapret-openwrt` and native `bol-van/zapret2` behavior/boundaries
- [x] separate universal STUN recognition from provider-specific DPI-bypass effectiveness
- [x] reject global UDP/443 drop and global all-UDP userspace interception as defaults
- [x] complete P2P-disabled Phase A and preserve redacted evidence without raw PCAP
- [x] implement/publish the default-OFF Telegram-IPv4-scoped `v0.5.0_3` STUN zero-fake PoC
- [x] complete the clean remote-participant P2P-disabled helper OFF/ON/OFF live comparison
- [x] prove helper scope/counters, exact two-fake on-wire order, STUN-only action and live cleanup
- [x] measure the provider/network gate: 0 inbound TURN/STUN and no sustained bidirectional Telegram UDP — **FAIL**
- [x] inspect/document exact Zapret2 UDP/IP-fragmentation semantics and FreeBSD divert applicability
- [x] define one ordered position-8, Telegram-destination-scoped fragmentation candidate and on-wire acceptance contract
- [x] pin the owner appliance to Zapret2 `v1.0.4` / `2c21faa80e1acb71ddceb8b49176f266b7d33f05`
- [x] preserve the prepared STUN-only `_4` source branch without opening/publishing it
- [x] identify official pinned `tgcalls_cli` as an account-free real-reflector media oracle
- [x] define the separate `WIRE_OK`, `TURN_REPLY`, `REFLECTOR_READY`, `MEDIA_PASS` and `CALL_PASS` gates
- [x] select fixed-endpoint, fresh-flow and independent-unblocked-control experimental discipline
- [x] build and digest-pin the TOS/Linux tgcalls companion outside the OPNsense package
- [x] pass the bounded local two-peer runtime/statistics gate without misclassifying it as reflector media success
- [ ] prove one fixed reflector with `MEDIA_PASS` on an independent unblocked path and capture wire-equivalence ground truth
- [ ] measure the same fixed endpoint through the blocked provider with no desynchronization
- [ ] verify PF/NAT/IPFW source visibility and add an exact-flow/exact-reflector/exact-port candidate runner with transactional cleanup
- [ ] test reflector fragmentation: position 8 ordered, position 8 reverse, then evidence-driven alternate positions
- [ ] add a transaction-correlated 28-byte TURN Allocate probe as the secondary oracle
- [ ] repeat any media winner across runs/endpoints and complete one final remote P2P-disabled real call
- [ ] rework, replace or close the paused `_4` branch from Phase C evidence before choosing a package/GUI scope

Phase A evidence: [`verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md`](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md).

Phase B evidence: [`verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md`](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md).

Phase C companion evidence: [`verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md`](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md).

The `v0.5.0_3` candidate remains default OFF and is not product-accepted. Its runtime/lifecycle passed, but zero-fake/repeats=2 did not restore TURN or sustained Telegram UDP. Because that profile selected only STUN, it did not test the separate Reflector Hello path. The remote `_4` branch is unpublished experimental work, not the current package identity. Stable Pages/pkg publication remains on `v0.5.0_1`.

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

**Control-validate the build-pinned official tgcalls companion against one fixed real reflector, then route that exact endpoint through OPNsense and measure the no-desynchronization baseline before any narrowly scoped strategy matrix.** Do not publish the prepared STUN-only `_4` candidate until the automatic oracle determines whether it is relevant, incomplete or ineffective.

Release notes for the current stable release: [`releases/v0.5.0.md`](releases/v0.5.0.md).
