# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-10-01
**Current handoff identity:** `v0.5.0_3` — reproduce the reported success with permanent LAN / router-local / SOCKS traffic separation; TCP policy verified in a bounded scope, latest UDP control failed

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

Historical 2026-09-02 Zapret2 runtime pin: [`verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

Phase C companion build/runtime evidence: [`verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md`](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md).

Historical 2026-09-05 fixed-reflector control and host-topology evidence: [`verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md).

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

## Telegram — current owner goal

**«Воспроизводимая конфигурация того успеха».** The owner requires permanent traffic separation on OPNsense `192.168.1.2` for LAN, router-local command-line/app traffic and SOCKS5 clients: active `telegram_voice`, Telegram UDP through Zapret2, Telegram TCP/TLS through local Squid to parent `185.203.117.88:33128`. TGVOICE must use `192.168.1.2`. Persistence across reboot is part of the goal, not yet an established result.

The primary configuration/recovery home is [Telegram traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md). Read it, the [September 23–October 1 evidence](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), and [protocol research](research/TELEGRAM_VOICE_UDP.md) before further changes. Older experiment details are linked from the evidence/index and need not be rediscovered to choose the current task.

What this handoff establishes:

- Transparent LAN HTTPS passed through Squid to the parent after the separate HTTPS `/32` route was corrected on TNAS. The SOCKS policy then passed all five v2 probes on October 1 at 03:47 UTC and remains applied in the last reported state.
- The successful v2 run is `/root/singbox-lan-policy-20261001T034734Z-33814uhu`. The earlier 02:49 TLS failure rolled files back but left a Squid listener; a full proxy restart released it. Do not confuse that failed run with the later applied configuration.
- `telegram_voice` is ON in the latest snapshot, with 14 table entries and `stun-zero-fake-repeats-2`. The 04:15 UTC CLI control still failed: both peers `Reconnecting`, BWE zero, exit 1; rule 19000 increased by 60 packets / 4080 bytes and WAN showed 60 valid non-STUN Hello packets with no replies.
- The earlier owner-reported successful call through `192.168.1.2` is preserved. Its exact positive CLI output/configuration attribution remains open. Later failures do not erase it.
- Fakefrag8+reverse24 was already tested with valid local-WAN fake/real pairs; fakefrag8+original had a separate local PF defect; tee preserved the real packet but put it before the fake. The September 30 reverse8 repeat also failed. Do not restart the completed fragment-position sweep or call these different outcomes one undifferentiated failure.

## Immediate next action

1. Use the configuration/recovery document to retain the verified TCP path and selected TNAS routes. `192.168.1.140` is retired; `192.168.80.1` is outside owner control. There is no alternate working exit.
2. Complete the explicitly recorded transition debt: automatic router-local TCP/TLS selection, reboot persistence of `telegram_voice` and TNAS routes, service/config survival, and controlled PF-alias snapshot refresh. The current helper marker in `/var/run` returns OFF after reboot; the v2 script did not install a boot hook.
3. Verify LAN, local-origin and SOCKS as separate ingress cases, including a real SOCKS UDP ASSOCIATE path. Existing TCP/80,443 IPv4 checks must not be presented as proof for all Telegram TCP, IPv6 or SOCKS UDP.
4. Correlate the reported successful call if its original evidence is recovered; otherwise measure one bounded change against the recorded current baseline. Record hooks, effective profile, routes, binary hash, counters, packet evidence and CLI output together. Current non-STUN Hello traffic is not transformed by the STUN-only helper; do not blindly substitute fragmentation in that profile.
5. Repeat a qualified `MEDIA_PASS` with fresh flows, then verify a remote P2P-disabled Windows/Android call with two-way sound and sustained bidirectional UDP (`CALL_PASS`). Silence without an independent working control remains `NO_REPLY_UNKNOWN`.

This documentation update makes no appliance or package change. Keep package identity `0.5.0_3`; `_4` remains unpublished and paused. Permanent router traffic policy is now owner-required, while the laboratory controller itself remains temporary. No new GUI/permanent lab subsystem, Generic UDP change or bundled tgcalls/Linux is selected. The owner defines the work as an internal laboratory test; sanctions circumvention is not an objective.
