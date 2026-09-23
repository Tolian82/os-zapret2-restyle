# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-09-23

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

## `v0.5.0_3` current testing line — TELEGRAM VOICE LAB ACTIVE

- [x] keep package identity at `VERSION=0.5.0`, `PLUGIN_REVISION=3`
- [x] retire the `e3069322...` binary from active laboratory use
- [x] pin the only active tgcalls oracle to `efd330ca04f74706024a5abdfb5b41f4e4dd1065`
- [x] require a local P2P smoke gate and SHA-256 manifest for that current oracle
- [x] qualify current `efd330ca...` build/runtime on TNAS — **OWNER-LIVE PASS**, SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`
- [x] record owner runtime update to Zapret2 v1.0.5.2 for future live candidate epochs
- [x] keep this change lab/docs-only; no package payload or revision bump

## Telegram voice / UDP DPI-bypass — PHASE C TEMPORARY CONSOLE ORACLE

Owner-selected authority: [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

Current architecture: [`architecture/TELEGRAM_VOICE_EMULATION_LAB.md`](architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

- [x] complete Phase A/B observation and zero-fake runtime/network interpretation
- [x] pin Zapret2 `v1.0.4` and preserve unpublished `_4` work
- [x] build/digest-pin the TOS/Linux `tgcalls_cli` companion
- [x] pass the local P2P build/runtime gate
- [x] select fixed current endpoint `91.108.13.10:596`
- [x] retire `192.168.1.140` as a working route by owner correction; preserve the September 5 success only as historical evidence
- [x] record the rebuild motivation and verified upstream voice-transport changes, including default-off flags and remaining Windows/Android parity questions
- [x] establish that Docker `host` has no independent container IP/MAC
- [x] retain only the existing TOS/Docker `host` network by owner instruction
- [x] reject GUI and permanent Telegram Voice laboratory integration
- [x] run paired TNAS/OPNsense console tests; optional SSH automation is no longer an experiment prerequisite
- [ ] for any future route mutation, snapshot and restore the actual pre-test route; never assume `192.168.1.140` is usable
- [x] run current tgcalls against `91.108.13.10:596` through OPNsense with no desynchronization and capture LAN/WAN truth — **WIRE_OK / NO_REPLY_UNKNOWN**; 60/60 outbound packets survive forwarding/NAT, zero inbound replies
- [x] establish from current capture that the reflector baseline is non-STUN 40-byte Hello traffic; paused STUN-only `_4` is not a direct candidate
- [x] stage temporary non-packaged exact-endpoint runner and distinguish the corrected file as `tgvoice_ipfrag8_postnat_v2.py`
- [x] correct pre-NAT UDP checksum corruption and post-NAT first-fragment recapture
- [x] qualify ordered position-8 post-NAT wire output: 60 complete pairs, valid checksums, no replies; `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, call still fails
- [x] validate reverse position-8 syntax/source and run the distinct temporary runner; supplied endpoint captures and rule counters are empty, cleanup restored
- [x] record the owner's subsequent report that the call established and routing was correct at call time
- [x] identify the earlier reported successful tool as the same fixed-reflector CLI command; preserve that observation separately from failed repeats
- [x] restore the endpoint route after reboot and correlate the new CLI run with 60 valid reverse position-8 pairs; zero replies, `Reconnecting`, zero BWE, exit 1, exact restoration
- [x] prepare distinct guarded reverse position-32 runner and validate its short-packet pass-through/native fragmentation behavior offline
- [x] live-qualify reverse position 32 on the same endpoint/runtime: 60 valid reverse pairs, no replies/media, exact restoration
- [x] prepare distinct guarded reverse position-16 runner and pass 27 offline boundary/options cases
- [x] live-qualify guarded reverse position 16: 60 valid reverse pairs, no replies/media, exact restoration
- [x] prepare distinct guarded reverse position-24 runner with <=16-byte short-payload pass guard; Python syntax passed
- [x] live-qualify guarded reverse position 24: 60 valid equal-length reverse pairs, no replies/media, exact restoration; standalone fragment-position widening closed
- [x] prepare `tgvoice_fakefrag8_reverse24_postnat_v1.py`: one checksum-invalid 40-byte zero fake fragmented ordered at position 8, then qualified real reverse24
- [ ] live-test fragmented fake8 + reverse24 and qualify fake/real fragment identity, checksums, replies/media and exact restoration
- [ ] correlate the earlier positive CLI output if recovered; qualify a repeatable successful call
- [ ] assess engine/custom-parameter parity in separate source-guided experiments without changing fragmentation simultaneously
- [ ] achieve and repeat a real-reflector laboratory call through OPNsense: both peers established, both stats/BWE positive, exit 0 (`MEDIA_PASS`)
- [ ] add correlated TURN Allocate only as a secondary oracle
- [ ] repeat any winner and complete one final remote P2P-disabled real call
- [ ] remove temporary SSH/route/scripts, archive evidence and decide `_4`

Current test evidence: [`September 23 reverse position-24 result`](verification/evidence/2026-09-23-telegram-voice-reverse24.md), following [`reverse position-16`](verification/evidence/2026-09-23-telegram-voice-reverse16.md) and [`reverse position-32`](verification/evidence/2026-09-23-telegram-voice-reverse32.md) and [`September 22 post-reboot reverse position-8 repeat`](verification/evidence/2026-09-22-telegram-voice-reverse8-postreboot.md), with the separate [`earlier successful-call observation`](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md), following [`September 21 ordered post-NAT fragmentation`](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md). The [September 5 control](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md) is historical and its route is retired.

No GUI, permanent lab controller/API/daemon, Generic UDP semantic change or Telegram Voice lab package subsystem belongs to this work. Package identity remains `0.5.0_3`.

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

**Establish and repeat a call carrying bidirectional media through OPNsense.** The standalone reflector-fragmentation sweep is closed: ordered position 8 and reverse positions 8, 16, 24 and 32 are locally wire-qualified, but no fully correlated run received a reflector reply or media. The prepared next test is one fragmented checksum-invalid zero fake at position 8 followed by the already-qualified real reverse24 path. The earlier owner-reported success remains separate. Do not return to retired `192.168.1.140`; preserve Docker `host`, temporary tooling and package `0.5.0_3`.

Release notes for the current stable release: [`releases/v0.5.0.md`](releases/v0.5.0.md).
