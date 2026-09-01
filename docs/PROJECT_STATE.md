# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-09-01
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
- last owner-live accepted package revision: `_2`;
- owner-live accepted testing corrective: `os-zapret2-restyle-0.5.0_2.pkg` / `v0.5.0_2`;
- testing source/tag target: `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- testing package SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- testing publication workflow: `31917806438`;
- current stable Web/pkg release/tag remains `v0.5.0`;
- current stable package remains `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- stable full release workflow: `31916256043`, PASS;
- stable GitHub Pages/pkg repository remains the `v0.5.0_1` release repository;
- internal service key: `zapret`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

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
- `v0.5.0` remains the stable Web/pkg release; the owner-live accepted `_2` corrective is not automatically promoted to the stable Pages/pkg repository.

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

The owner-selected research conclusion and Phase A owner-live observation are complete. The bounded Phase B source PoC is implemented in the `0.5.0_3` candidate and awaits owner-live packet qualification.

Research authority: [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

Owner-live evidence: [`verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md`](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md).

Established durable facts:

- ordinary Telegram TCP/service traffic remains routed through the owner's existing external proxy and is outside the target bypass problem;
- modern Telegram calls use Telegram API signaling plus separately negotiated WebRTC transport with dynamic STUN/TURN endpoint IP+port and UDP P2P/reflector capabilities;
- current upstream Zapret2 provides the native `--payload=stun` plus 16-zero-byte fake/repeats=2 baseline for stateful-DPI STUN interference;
- FreeBSD `ipfw` cannot raw-payload-filter STUN before userspace, so OPNsense cannot safely copy Linux `50-stun4all` as global all-UDP interception;
- with P2P disabled on both same-LAN clients, Phase A observed TURN Allocate to `91.108.9.100:1400` and Telegram Reflector Hello to `91.108.9.40:597`, both outbound-only;
- the same call established with two-way audio and no perceived delay while Telegram TCP/SOCKS stayed bidirectional, so audible success masked the broken observed UDP route;
- the captured 40-byte Telegram Reflector Hello is not STUN and will not be selected by the official `--payload=stun` profile;
- Phase A localizes failure no later than relay establishment but does not prove whether the upstream mechanism is stateful DPI, stateless filtering/IP blocking or another blackhole;
- existing Generic UDP Strategy Lab remains unsuitable as a truthful automatic call tester.

Implemented Phase B boundary:

- temporary `/var/run` request marker, so reboot returns the PoC to OFF;
- plugin-owned `zapret2_tgvoice` and staging IPFW tables populated from the normalized managed Telegram IPv4 set;
- all-port outbound UDP diversion only to `table(zapret2_tgvoice)` through the existing divert socket;
- first/high-priority `--filter-l3=ipv4`, `--filter-udp=*`, `--filter-l7=stun`, Telegram-IPSET profile with `--payload=stun` and the upstream 16-zero-byte fake/repeats=2 action;
- transactional table swap and ordinary runtime/tree/rule rollback integration;
- `configctl zapret telegram_voice_enable|status|disable` control and dedicated IPFW packet/byte status;
- regression coverage proving OFF leaves the user strategy unchanged, ON remains destination-scoped, and failed rule replacement restores the previous table.

No production GUI, global STUN/all-Internet UDP interception, UDP/443 drop, reflector classifier or Telegram-specific Strategy Lab branch was added.

## Immediate next boundary

The next boundary is owner-live qualification of the exact `0.5.0_3` candidate:

- keep P2P disabled on both Telegram clients and the existing TCP/SOCKS proxy unchanged;
- record dedicated helper status/counters before, during and after the call;
- capture the Telegram-range UDP path with the helper ON;
- complete an OFF/ON/OFF cycle and verify exact rule/table/profile cleanup.

Acceptance is packet-based: Phase B must create inbound TURN/STUN and sustained bidirectional Telegram UDP that are absent from baseline and disappear again after rollback. A still-audible call without that UDP evidence is not a pass because TCP fallback is already working.

Do not add a Telegram Reflector action in the first PoC. Investigate that protocol separately only if TURN replies are restored but the UDP call path still fails.

The cancellation/internal-failure containment regression remains backlog work.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
