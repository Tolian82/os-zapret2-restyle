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
**Current handoff identity:** `v0.5.0_4` source candidate — installed Zapret2 runtime supports the ordered position-8 IPv4-fragmentation primitive; exact-head qualification and testing publication are the next gates

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=4`;
- current source candidate: `v0.5.0_4` / `os-zapret2-restyle-0.5.0_4.pkg` — not yet published;
- latest published testing candidate: `v0.5.0_3` / `os-zapret2-restyle-0.5.0_3.pkg`;
- latest published testing source/tag target (`_3`): `34adca978b3b6769972591872209c166ec9c6eb6`;
- latest published testing package SHA-256 (`_3`): `b88accee3fc7510e3b54ed65bb525be65c79aba8e5e02193435b431a3a4c253f`;
- latest testing publication workflow (`_3`): `33536081824`, PASS on attempt 2;
- last owner-live accepted testing corrective: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository remains on `_1`; `_2`, `_3` and the unpublished `_4` source candidate have not promoted it.

Latest testing-publication evidence: [`verification/evidence/testing-publications/v0.5.0_3.md`](verification/evidence/testing-publications/v0.5.0_3.md).

Installed Zapret2 runtime pin: [`verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

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

## Telegram voice / UDP — ordered-fragmentation source candidate

The owner-selected research is recorded in [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md). Phase A evidence is [`verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md`](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md); the completed Phase B comparison is [`verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md`](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md).

Durable Phase A result:

- with P2P disabled on both clients, Telegram-range TURN Allocate and Reflector Hello candidates remained outbound-only;
- calls could still have two-way sound through the concurrent TCP/SOCKS fallback;
- Telegram Reflector Hello is a separate 40-byte non-STUN protocol packet.

All live captures kept the owner's normal Traffic Strategy and Telegram TCP redirection through a router-local proxy path to an external HTTP proxy enabled. The concurrent Telegram UDP profile was limited to ports `80,443,5222,8888` and MTProto payload; the observed TURN/reflector ports `596–599` and `1400` were outside that filter. This preserves the UDP comparison while reinforcing that audible calls can be masked by the existing TCP proxy path.

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

Therefore the implementation/lifecycle boundary passed, but the mandatory provider/network gate failed. The upstream zero-fake/repeats=2 baseline is ineffective on the tested path and is not product-accepted. It remains available only in the immutable `_3` package.

The owner then pinned the installed runtime as Zapret2 `v1.0.4`, commit `2c21faa80e1acb71ddceb8b49176f266b7d33f05`, and confirmed the native fragmentation-only `blockcheck2` form. The `0.5.0_4` source candidate replaces only the temporary helper action/status identity with:

```text
--lua-desync=send:ipfrag:ipfrag_pos_udp=8
--lua-desync=drop
```

The Telegram IPv4 table/rule, first-profile STUN selection, default-OFF CLI control, counters, byte-for-byte user-strategy preservation and rollback lifecycle remain unchanged. The regression contract requires ordered `send` before `drop` and forbids the failed zero-fake action inside the helper profile.

## Immediate next action

Run exact-head source CI and FreeBSD-15 package qualification, squash-merge only that verified head, and publish the resulting `v0.5.0_4` testing package. It remains experimental/default OFF and must not update the stable Pages/pkg repository.

Owner-live qualification must keep the normal Traffic Strategy, Telegram TCP proxy redirection and P2P-disabled remote participant unchanged. The WAN capture must use `ip proto 17` plus Telegram networks, not a direct STUN-cookie BPF, because the first fragment has only the UDP header and the second has the STUN payload.

Success still requires exact on-wire fragment pairs, no unfragmented original, an inbound TURN/STUN response and sustained bidirectional Telegram UDP. Correct fragments without a reply are a network failure and cannot distinguish provider fragment dropping from pure Telegram destination/path blocking.

Do not add fake-plus-fragment combinations, reverse order, alternate positions, reflector handling, global UDP/443 blocking, global all-UDP interception or a production GUI before this single candidate is measured. The Strategy Lab cancellation/internal-failure containment regression remains backlog work.
