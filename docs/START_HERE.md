# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-09-03
**Current handoff identity:** `v0.5.0_3` — Phase A/B complete; installed Zapret2 fragmentation capability confirmed; unpublished `_4` candidate paused; Phase C Telegram traffic-emulation oracle selected

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

## Telegram voice / UDP — measured state and selected Phase C

Read these two specialist authorities completely before further Telegram Voice mutation:

- [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md) — research, Phase A/B interpretation and protocol evidence;
- [`architecture/TELEGRAM_VOICE_EMULATION_LAB.md`](architecture/TELEGRAM_VOICE_EMULATION_LAB.md) — current emulator/oracle architecture, result taxonomy, strategy order and exact implementation sequence.

Established live facts:

- with P2P disabled, the client sent a 28-byte TURN Allocate request to Telegram port `1400` and a separate 40-byte non-STUN Reflector Hello to ports `596–599`;
- both families were outbound-only on the tested provider path;
- a separate generic STUN endpoint at `141.101.90.1:3478` replied bidirectionally, so this is not a universal UDP/STUN outage;
- working two-way sound was masked by the existing Telegram TCP path through the router-local and external proxy chain;
- the normal Telegram UDP strategy covered only `80,443,5222,8888`, so it did not process the observed voice endpoints;
- `v0.5.0_3` correctly emitted two zero16 fakes before every STUN request but restored no reply; runtime/lifecycle passed and provider effectiveness failed;
- the same STUN-only profile left every Reflector Hello unchanged, so Phase B did not test any reflector-specific bypass;
- the appliance runs Zapret2 `v1.0.4` at `2c21faa80e1acb71ddceb8b49176f266b7d33f05`, and native ordered/reverse IPv4 fragmentation is available;
- offline packet transformation can prove only `WIRE_OK`; it cannot predict the provider response.

The remote branch `v0.5.0_4-telegram-voice-ipfrag` at `3ecdd1b3326fe7655e1d7df9edd51808e2a68dc9` contains a prepared STUN-only ordered-position-8 candidate. It has no PR, exact-head CI, merge, package or live result. Preserve it as unique experimental work, but do not merge or publish it as-is. Phase C evidence decides whether it is rebased/reworked, replaced or rejected.

## Immediate next action

Build the Phase C automatic oracle around official `TelegramMessenger/tgcalls` commit `78d07f3e46a4bb12b611ccc2816ff59ca63a83fb`:

1. create a reproducible Linux/WSL2 companion artifact outside the OPNsense package and record its digest;
2. use `tgcalls_cli --mode reflector` with one fixed Telegram reflector `IP:596–599` and obtain `MEDIA_PASS` on an independently unblocked path;
3. capture that control run and confirm wire equivalence to the real 40-byte Hello/retry/media framing;
4. run a no-desync baseline through the blocked provider against the same endpoint;
5. verify whether WAN-out IPFW sees the pre- or post-NAT source, then add a temporary exact-flow/exact-destination/exact-port runner with transactional cleanup;
6. test reflector fragmentation in bounded order: position 8 ordered, position 8 reverse, then evidence-driven alternate positions; test fake-plus-fragment only after standalone families;
7. add the correlated 28-byte TURN Allocate probe as a secondary oracle;
8. repeat any media winner, then perform one final real remote-participant P2P-disabled call.

Use the result classes `WIRE_OK`, `TURN_REPLY`, `REFLECTOR_READY`, `MEDIA_PASS`, `CALL_PASS`, `NO_REPLY_UNKNOWN`, `NETWORK_FAIL` and `RESTORE_FAILED` exactly as defined in the architecture document. A silent endpoint without a recent exact-endpoint control is inconclusive. An arbitrary UDP reply is not success. Audio without sustained UDP is not success.

Do not bundle `tgcalls`/Bazel/Linux into the OPNsense package, intercept all Internet UDP, globally drop UDP/443, expose a production GUI, increase fake repeats blindly, or publish `_4` before this oracle is established.

The previously selected Strategy Lab cancellation/internal-failure containment regression remains useful backlog work but is not the immediate task.
