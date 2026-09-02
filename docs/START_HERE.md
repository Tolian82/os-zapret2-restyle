# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-09-02
**Current handoff identity:** `v0.5.0_3` — zero-fake network gate failed; ordered Telegram-scoped IPv4-fragmentation candidate designed; installed Zapret2 runtime pin is the next gate

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

## Telegram voice / UDP — Phase B zero-fake baseline measured

The owner-selected research is recorded in [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md). Phase A evidence is [`verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md`](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md); the completed Phase B comparison is [`verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md`](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md).

Durable Phase A result:

- with P2P disabled on both clients, Telegram-range TURN Allocate and Reflector Hello candidates remained outbound-only;
- calls could still have two-way sound through the concurrent TCP/SOCKS fallback;
- Telegram Reflector Hello is a separate 40-byte non-STUN protocol packet.

The published default-OFF `v0.5.0_3` PoC adds a Telegram-IPv4-scoped all-port UDP IPFW rule and a first-priority Zapret2 STUN profile using two 16-zero-byte fakes before the original request. Its temporary controls remain:

- `configctl zapret telegram_voice_enable`;
- `configctl zapret telegram_voice_status`;
- `configctl zapret telegram_voice_disable`.

The clean P2P-disabled remote-participant OFF/ON/OFF comparison established:

- helper OFF: 9 TURN Allocate requests and 90 Reflector Hello packets, all outbound-only;
- helper ON: the table/profile/rule became active, the helper counter incremented, and every one of 9 TURN requests was preceded on WAN by exactly two valid 16-zero-byte datagrams;
- the 90 non-STUN reflector packets remained unchanged, confirming correct L7 discrimination;
- helper ON still produced 0 inbound TURN/STUN packets and no sustained bidirectional Telegram UDP;
- disable removed the helper table/profile/rule state and restored the ordinary rule layout while the service remained running.

Therefore the implementation/lifecycle boundary passed, but the mandatory provider/network gate failed. The upstream zero-fake/repeats=2 baseline is ineffective on the tested path and is not product-accepted. It remains default OFF and no production GUI is authorized.

## Immediate next action

Pin the exact Zapret2 runtime installed on the owner's appliance:

```csh
git -C /usr/local/etc/zapret2 describe --tags --exact-match
git -C /usr/local/etc/zapret2 rev-parse HEAD
grep -Fn -- 'send:ipfrag:ipfrag_pos_udp' /usr/local/etc/zapret2/blockcheck2.d/standard/90-quic.sh
```

The pinned Zapret2 v1.0.4 source and current upstream both define the next candidate as:

```text
--lua-desync=send:ipfrag:ipfrag_pos_udp=8
--lua-desync=drop
```

If the installed runtime confirms that primitive, the next packaged-source scope is `0.5.0_4`: replace only the failed helper action with ordered position-8 IPv4 fragmentation while preserving the existing Telegram IPv4 table/rule, default-OFF control, counters and rollback lifecycle.

The WAN capture for that experiment must use `ip proto 17` plus Telegram network ranges, not a direct STUN-cookie BPF, because the first fragment has only the UDP header and the second has the STUN payload.

Success still requires correct on-wire fragment pairs, an inbound TURN/STUN response and sustained bidirectional Telegram UDP. Correct fragments without a reply are a network failure and cannot distinguish dropped fragments from pure Telegram destination/path blocking.

Do not add fake-plus-fragment combinations, reverse order, alternate positions, reflector handling, global UDP/443 blocking, global all-UDP interception or a production GUI before this single candidate is measured.

The previously selected Strategy Lab cancellation/internal-failure containment regression remains useful backlog work but is not the immediate task.
