# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-28
**Current handoff identity:** `v0.5.0_2` owner-live accepted; Telegram voice / UDP Phase A live observation complete, bounded Phase B UDP-path PoC is the next evidence gate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=2`;
- owner-live accepted testing corrective: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- testing source/tag target: `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- testing package SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- testing publication workflow: `31917806438`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository remains on `_1`; `_2` did **not** promote it.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

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

## Telegram voice / UDP — Phase A owner-live complete

The owner-selected research and confirmed live observation are recorded in [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md). The redacted capture record is [`verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md`](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md).

Durable Phase A result:

- both call participants were on the same LAN with Telegram P2P disabled;
- the Windows 11 test client sent TURN Allocate requests to `91.108.9.100:1400` and Telegram Reflector Hello packets to `91.108.9.40:597`;
- both Telegram-range UDP candidates remained outbound-only; no reply was captured and PF reported outbound-only state;
- no direct/private-peer UDP candidate appeared;
- the call nevertheless established with two-way audio and no perceived delay;
- concurrent bidirectional Telegram TCP/SOCKS activity supports TCP/proxy fallback as the only observed working route;
- the exact upstream cause remains unclassified: the observation does not distinguish stateful STUN DPI from stateless UDP/IP filtering or another relay blackhole.

The live capture also exposed a protocol boundary: the official Zapret2 `--payload=stun` baseline can select the TURN Allocate requests but does not classify Telegram's separate 40-byte Reflector Hello packet.

No Telegram Voice source/runtime implementation was added. Raw PCAP data is not stored in the repository.

## Immediate next action

The next eligible implementation boundary is a deliberately small, separately authorized Phase B PoC:

- all destination-port UDP interception only toward the plugin-managed Telegram IPv4 table;
- existing `dvtws2` socket/process;
- native `--payload=stun` plus 16-zero-byte fake, `repeats=2`;
- explicit firewall/profile/packet counters;
- no production GUI, global UDP/443 drop, all-Internet UDP interception or reflector-specific action.

Future validation must use P2P disabled on both clients and compare helper OFF/ON/OFF. Audible sound is not the pass condition because TCP fallback already masks the UDP failure. PASS requires inbound TURN/STUN plus a sustained bidirectional Telegram UDP path while the helper is ON, followed by exact rollback evidence.

This handoff is documentation-only. The Phase B source PoC remains a separate explicit task.

The previously selected Strategy Lab cancellation/internal-failure containment regression remains useful backlog work but is not the immediate task.
