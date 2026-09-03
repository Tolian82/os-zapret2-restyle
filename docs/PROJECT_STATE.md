# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-09-03
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

Research, Phase A observation, Phase B zero-fake measurement and the installed-runtime capability pin are complete. The current selected work is Phase C: construct a truthful automatic traffic emulator/oracle before publishing another package candidate.

Authorities:

- [research and interpretation](research/TELEGRAM_VOICE_UDP.md);
- [current Phase C emulator/oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md);
- [Phase A live observation](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md);
- [Phase B STUN baseline live result](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md);
- [installed Zapret2 runtime pin](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

Established durable facts:

- ordinary Telegram TCP/service traffic remains routed through the owner's local/external proxy path and is outside the UDP bypass target;
- Telegram signaling is separate from dynamically negotiated WebRTC STUN/TURN, P2P and reflector transport;
- the clean P2P-disabled client emitted nine 28-byte TURN Allocate requests on port `1400` and ninety 40-byte non-STUN Reflector Hello packets on `596–599`; both families were outbound-only;
- a separate non-Telegram STUN endpoint at `141.101.90.1:3478` replied bidirectionally, so UDP/STUN was not universally blocked on the WAN path;
- audible two-way sound did not prove UDP because the concurrent TCP proxy fallback stayed available;
- the normal Telegram UDP strategy covered only `80,443,5222,8888`, so it did not intercept either captured voice family;
- `v0.5.0_3` correctly limited all-port UDP diversion to 14 managed Telegram IPv4 ranges, emitted exactly two valid zero16 fakes before every STUN request, left every reflector packet unchanged, and cleaned up correctly;
- that zero-fake profile passed runtime/lifecycle qualification but failed provider effectiveness: no TURN reply and no sustained bidirectional Telegram UDP;
- because the helper selected only STUN, Phase B does not test or disprove a reflector-specific desynchronization strategy;
- the provider mechanism remains unclassified: destination-IP/direction/routing policy, stateless payload filtering, fragment policy, relay policy or another blackhole remain possible;
- the appliance runtime is Zapret2 `v1.0.4` at `2c21faa80e1acb71ddceb8b49176f266b7d33f05` and supports native ordered and reverse IPv4 fragmentation;
- offline packet replay/transformation can predict exact wire output only; a control-proven live endpoint is required for a network verdict;
- official `tgcalls_cli` can emulate caller/callee signaling locally and route bidirectional WebRTC media through a real Telegram UDP reflector with TCP disabled.

The remote branch `v0.5.0_4-telegram-voice-ipfrag` at `3ecdd1b3326fe7655e1d7df9edd51808e2a68dc9` is one commit ahead of its `1bdb3eccf3b96707d6c314a0c364ca14ac2a190c` base. It contains a STUN-only ordered-position-8 implementation but has no PR, exact-head CI, merge, package publication or live result. It is preserved as unique experimental work and must be reworked from the future Phase C evidence rather than merged as-is.

No production GUI, global STUN/all-Internet UDP interception, global UDP/443 drop or blind fake-repeat widening is accepted. The `v0.5.0_3` helper remains default OFF and non-product.

## Immediate next boundary

Pin official `TelegramMessenger/tgcalls` commit `78d07f3e46a4bb12b611ccc2816ff59ca63a83fb` into a reproducible Linux/WSL2 companion artifact. Prove one fixed Telegram reflector `IP:596–599` on an independently unblocked path, then measure the same endpoint through the blocked provider.

After the oracle is valid, verify the PF/NAT/IPFW source identity and add a narrow temporary forwarded-flow IPFW/dvtws2 runner scoped to one reflector address and one port, plus the exact observable probe source tuple where available. Test the reflector family in this order: baseline, ordered position 8, reverse position 8, then evidence-driven alternate positions. Add a transaction-correlated 28-byte TURN Allocate probe as a secondary oracle.

Candidate outcomes use the explicit hierarchy `WIRE_OK -> TURN_REPLY/REFLECTOR_READY -> MEDIA_PASS -> CALL_PASS`. Silence without a fresh exact-endpoint control is `NO_REPLY_UNKNOWN`; restoration failure overrides every useful intermediate result. Repeat a winner before one final real remote P2P-disabled call.

Only after that result may the project rebase/rework, replace or close the paused `_4` branch and select a new package/GUI scope. The cancellation/internal-failure containment regression remains backlog work.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
