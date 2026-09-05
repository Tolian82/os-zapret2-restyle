# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-09-05
State-line scope: **`v0.5.x`**

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- rule books: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md), [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md), [`CHAT_RULES.md`](CHAT_RULES.md), [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology: [`history/current/v0.5.x.md`](history/current/v0.5.x.md);
- completed `v0.4.x` archive: [`history/archive/v0.4.x.md`](history/archive/v0.4.x.md).

Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Repository and release facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.5.0`;
- current source candidate revision: `_3`;
- package candidate: `os-zapret2-restyle-0.5.0_3.pkg`;
- published testing candidate: `os-zapret2-restyle-0.5.0_3.pkg` / `v0.5.0_3`;
- testing source/tag target: `34adca978b3b6769972591872209c166ec9c6eb6`;
- testing package SHA-256: `b88accee3fc7510e3b54ed65bb525be65c79aba8e5e02193435b431a3a4c253f`;
- testing publication workflow: `33536081824`, PASS on attempt 2;
- last owner-live accepted package revision: `_2`;
- owner-live accepted testing corrective: `os-zapret2-restyle-0.5.0_2.pkg` / `v0.5.0_2`;
- current stable Web/pkg release/tag remains `v0.5.0`;
- current stable package remains `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- stable full release workflow: `31916256043`, PASS;
- stable GitHub Pages/pkg repository remains the `v0.5.0_1` release repository;
- internal service key: `zapret`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_3.md`](verification/evidence/testing-publications/v0.5.0_3.md).

Owner-live `_2` evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

Stable release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked product facts carried into `v0.5.x`

- DNS is working; historical DNS timeout investigation is closed absent fresh evidence.
- Model C is the only normal production Stage-60 Strategy Lab runtime.
- Automatic Model-B/Model-A production fallback remains removed.
- Lua/BLOB/discovery/readiness optimization questions closed by accepted measurements remain closed for the current architecture.
- Strategy Lab supports domains and canonical IPv4 targets; IPv6 Laboratory target input remains deferred.
- IPv4 targets may use separate optional Host/SNI while traffic stays pinned to the entered IP.
- Working fixed-IP profiles use `--ipset-ip=<target>` and exact final replay.
- HTTP application `4xx`/`5xx` does not erase otherwise valid authenticated/intercepted DPI-path evidence.
- Bare-IP TLS identity failure reports `PARTIAL` + Host/SNI guidance.
- Bare-IP QUIC without Host/SNI is skipped before candidate execution; Host/SNI QUIC performs real fixed-IP hostname verification.
- Generic UDP remains independent of Host/SNI and QUIC.
- Enable QUIC is explicit, persisted, defaults OFF, and its reload/revisit persistence is owner-live accepted.
- Strategy Lab cleanup/restoration remains mandatory and selected live jobs preserve exact initial service state.
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted.
- The native OPNsense Laboratory layout and deterministic Strategy Lab RU/EN text localization contract remain accepted.
- Strategy Lab owns the visible Generic UDP file-picker labels; browser/OS-native file-input chrome is not exposed.
- Owner-live verification confirms the `_2` RU/EN file-picker presentation and selected-filename/file-selection path work as intended.
- `v0.5.0` remains the stable Web/pkg release; neither the owner-live accepted `_2` corrective nor the published-but-unaccepted `_3` candidate promoted the stable Pages/pkg repository.

## Completed `v0.5.0_2` corrective

The post-release file-picker localization defect is closed.

Completed boundary:

- browser-native visible file-input chrome identified as the localization leak;
- Laboratory-owned EN `Choose file` / `No file selected` and RU `Выбрать файл` / `Файл не выбран` presentation implemented;
- actual selected filename remains visible;
- FileReader/Base64 staging, 1–4096-byte validation, busy-state behavior and Generic UDP API semantics preserved;
- regression coverage added;
- exact-head source CI and FreeBSD-15 package qualification passed in run `31917466421`;
- source PR `#269` squash-merged as `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- prerelease `v0.5.0_2` published and verified with SHA-256 `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- publication-record reconciliation completed through PR `#270` and its evidence-state closure;
- owner confirmed the live `_2` result works as intended.

No further package correction belongs to this scope.

## Telegram voice / UDP research state

Phase A observation, Phase B zero-fake measurement, the companion build/runtime gate and one fixed-reflector control are complete. Phase C remains a temporary console-driven research campaign, not a product subsystem.

Authorities:

- [research and interpretation](research/TELEGRAM_VOICE_UDP.md);
- [temporary emulator/oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md);
- [Phase A evidence](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md);
- [Phase B evidence](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md);
- [installed runtime pin](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md);
- [companion build/runtime result](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md);
- [fixed-reflector control and host-topology result](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md).

Established durable facts:

- the Phase A/B protocol interpretation and failed zero16/repeats=2 provider result remain unchanged;
- the qualified `tgcalls_cli` SHA-256 is `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a`;
- fixed endpoint `91.108.13.10:596` passed a 15-second real-reflector run on 2026-09-05: both sides established, 15 bitrate records per side, non-zero BWE, no errors and exit 0;
- that exact-endpoint control `MEDIA_PASS` used TNAS `192.168.1.100` through `192.168.1.140` and did not traverse OPNsense;
- the owner requires the existing Docker `host` network only;
- a host-network container has no per-container IP or MAC. DHCP sees the TNAS host identity, so it cannot assign this container a separate `192.168.1.239` lease or per-container gateway;
- pfSense DHCP can still assign routes by the visible TNAS MAC, but their scope is the TNAS host namespace rather than this one container;
- the provider-path selector is one exact endpoint `/32` route on TNAS through `192.168.1.2`, delivered by owner-controlled DHCP policy or a bounded explicit route transaction, never a TNAS default-route change;
- OPNsense-console orchestration uses temporary key-only SSH to TNAS plus `docker exec`; every route/runtime mutation requires exact restoration;
- no Telegram Voice GUI, permanent plugin controller/API/configd action, installed daemon or package-owned laboratory is authorized;
- temporary console scripts live outside installed plugin paths and are removed when the research closes;
- the existing Generic UDP Strategy Lab and permanent production code remain unchanged.

The remote `_4` branch remains unpublished and paused. The control result does not authorize a package revision or stable publication.

## Immediate next boundary

Prove the exact `/32` route transaction for `91.108.13.10` from control gateway `192.168.1.140` to OPNsense `192.168.1.2` and back. Establish temporary key-only invocation from the OPNsense console to TNAS, then run the same endpoint with no desynchronization while recording OPNsense LAN/WAN evidence and counters.

Only after that baseline may temporary non-packaged console scripts run the bounded reflector matrix. Silence without the fresh control is `NO_REPLY_UNKNOWN`; any failed route/runtime restoration is `RESTORE_FAILED` and overrides other results.

The Telegram Voice laboratory will not become permanent plugin code. A later proven production strategy/helper would require a separate owner decision.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
