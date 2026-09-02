# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-09-02
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

The research, Phase A observation and bounded Phase B zero-fake experiment are complete. The `v0.5.0_3` runtime/lifecycle behaved as designed, but the strategy failed its provider/network acceptance gate.

Research authority: [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

Evidence:

- [Phase A live observation](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md);
- [Phase B STUN baseline live result](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md).

Established durable facts:

- ordinary Telegram TCP/service traffic remains routed through the owner's existing external proxy and is outside the target bypass problem;
- Telegram API signaling is separate from dynamically negotiated WebRTC STUN/TURN, P2P and reflector transport;
- FreeBSD `ipfw` cannot raw-payload-filter STUN before userspace, so a global copy of Linux `50-stun4all` remains unacceptable;
- the `v0.5.0_3` helper correctly limited all-port UDP diversion to 14 managed Telegram IPv4 ranges and selected only STUN for its Lua fake action;
- a clean P2P-disabled remote-participant OFF run produced 9 TURN Allocate requests and 90 Reflector Hello packets, all outbound-only;
- the matching ON run emitted exactly two valid 16-zero-byte fakes before every one of 9 TURN requests while leaving 90 non-STUN reflector packets unchanged;
- ON still produced no inbound TURN/STUN and no sustained bidirectional Telegram UDP;
- live disable removed the helper table/profile/rule state and restored the ordinary rule layout while the service stayed running;
- the official zero-fake/repeats=2 baseline therefore passed runtime/lifecycle qualification but failed provider/network effectiveness;
- the exact provider mechanism remains unclassified: destination-IP/direction filtering, relay policy, payload inspection unaffected by the fake, or another path blackhole remain possible;
- audible success remains non-probative because the TCP/SOCKS fallback can mask UDP failure.

No production GUI, global STUN/all-Internet UDP interception, UDP/443 drop or reflector action is accepted. The `v0.5.0_3` helper remains a default-OFF experimental control, not a product feature.

## Immediate next boundary

Inspect the exact current Zapret2 UDP/IP-fragmentation primitive and define a bounded, Telegram-destination-scoped next experiment before packaged-source implementation.

The design must specify FreeBSD/on-wire fragment behavior, counters, cleanup and the same P2P-disabled OFF/ON/OFF acceptance gate. It must explicitly state that fragmentation can test payload-aware filtering but cannot bypass a pure Telegram destination-IP block.

Do not tune repeats or manipulate Telegram Reflector Hello before this discrimination step. The cancellation/internal-failure containment regression remains backlog work.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
