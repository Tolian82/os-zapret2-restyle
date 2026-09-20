# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-09-20
**Current handoff identity:** `v0.5.0_3` — Windows/Android reflector parity recorded; Zapret2 v1.0.5.2 requalification and fresh `.2` baseline next

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=3`;
- published testing candidate: `v0.5.0_3` / `os-zapret2-restyle-0.5.0_3.pkg`;
- testing source/tag target: `34adca978b3b6769972591872209c166ec9c6eb6`;
- testing package SHA-256: `b88accee3fc7510e3b54ed65bb525be65c79aba8e5e02193435b431a3a4c253f`;
- testing publication workflow: `33536081824`, PASS on attempt 2;
- last owner-live accepted testing corrective: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository remains on `_1`; neither `_2` nor `_3` promoted it.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_3.md`](verification/evidence/testing-publications/v0.5.0_3.md).

Historical Zapret2 v1.0.4 runtime pin: [`verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

Windows/Android source-parity and 2026-09-20 live-matrix evidence: [`verification/evidence/2026-09-20-telegram-voice-win-android-source-parity.md`](verification/evidence/2026-09-20-telegram-voice-win-android-source-parity.md).

Phase C companion build/runtime evidence: [`verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md`](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md).

Fixed-reflector control and host-topology evidence: [`verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md).

Owner-live corrective evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

Stable release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted product boundary

The completed `v0.4.x` line and the post-release `_2` corrective are accepted owner-live unless fresh evidence contradicts them.

Key facts include:

- Model C is the only normal production Stage-60 runtime;
- Strategy Lab supports domain and canonical IPv4 targets;
- optional Host/SNI keeps service identity separate from a fixed IPv4 destination;
- fixed-IP final profiles include `--ipset-ip=<target>` and exact replay;
- authenticated/intercepted HTTP `4xx`/`5xx` remains valid DPI-path evidence;
- bare IPv4 TLS identity failure reports `PARTIAL` + Host/SNI guidance;
- bare-IP QUIC without Host/SNI is skipped before execution;
- Host/SNI QUIC performs real fixed-IP hostname-verified attempts;
- Generic UDP remains independent;
- Enable QUIC defaults OFF, is explicit/persisted, and its reload/revisit persistence is owner-live accepted;
- Strategy Lab cleanup/restoration remains mandatory;
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted;
- Strategy Lab owns its visible Generic UDP file-picker labels, so RU/EN presentation follows OPNsense language rather than browser/OS native file-input chrome;
- the owner verified the `_2` localized picker and file-selection path on the live appliance.

## Closed `v0.5.0_2` corrective

The English localization leak (`Выбор файла` / `Не выбран ни один файл` rendered by the browser/OS) was corrected by hiding the visible native file-input chrome and rendering Laboratory-owned picker text.

The source correction, full CI/FreeBSD-15 qualification, testing-package publication, publication-record tail and focused owner-live check are complete. The owner confirmed that `v0.5.0_2` works as intended. No further source change belongs to this scope.

## Telegram voice / UDP — measured state and temporary Phase C laboratory

Read the current [research](research/TELEGRAM_VOICE_UDP.md) and [temporary emulator/oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md) before further Telegram Voice work.

Established live facts:

- Phase A/B and the failed STUN zero-fake result remain unchanged;
- the owner uses Windows and Android for real Telegram calls; Telegram-iOS is not a client authority for this research;
- Telegram Desktop source head `4d4da471fbee771c10e173a83c003ba1728989f1` pins tgcalls `24694f64b03e301ec2c90792566046e61a2c4967`;
- current Android reflector/network source matches that same reference for `ReflectorPort.cpp`, `NativeNetworkingImpl.cpp`, and `EncryptedConnection.cpp`;
- the qualified CLI harness stays at tgcalls `e3069322a3d1e16ecb11a5e302242e59ddd7f09e`, binary SHA-256 `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a`; its compatibility claim is intentionally limited to the reflector wire/media path;
- the historical 2026-09-05 `91.108.13.10:596` run reached `MEDIA_PASS`, but `192.168.1.140` is **not** an independent DPI-free control because both `.140` and OPNsense `.2` precede the same MTS/MGTS DPI;
- current provider research uses `192.168.1.2`; do not switch to `.140` as a control criterion;
- on Zapret2 v1.0.4, reflector fragmentation at position 8 ordered/reverse plus ordered 16/24/32 was emitted correctly on WAN but obtained no reflector reply or media establishment;
- the owner has since upgraded the installed Zapret2 runtime to `v1.0.5.2`; the v1.0.4 captures remain historical and do not qualify the new runtime;
- the owner requires the existing TOS/Docker network named `host`; no Telegram Voice GUI/permanent subsystem is authorized;
- the existing Generic UDP Strategy Lab and permanent plugin code remain unchanged.

The remote `_4` fragmentation branch remains unpublished and paused.

## Immediate next action

1. Refresh/start the existing TOS `tgvoice-lab` recipe and verify the qualified binary plus `/results/source-provenance.txt`.
2. Require TNAS `ip route get <current-reflector-ip>` to use OPNsense `192.168.1.2`; do not use `.140` as a control route.
3. Requalify the required Zapret2 `v1.0.5.2` Lua/desync primitives on the live appliance.
4. Select a current Telegram reflector endpoint and run a fresh no-desynchronization baseline through `.2`.
5. Continue with bounded candidate families only after that current-runtime/current-endpoint baseline.
6. Preserve exact cleanup for every temporary IPFW/dvtws2 mutation and archive the resulting evidence.

Do not modify the GUI or permanent Strategy Lab implementation. Do not publish `_4`, intercept all Internet UDP, globally drop UDP/443, or bundle `tgcalls`/Linux into the OPNsense package.
