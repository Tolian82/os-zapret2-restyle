# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-09-22
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

The current task is to make a call establish and carry bidirectional media through OPNsense in the rebuilt tgvoice laboratory. Phase A/B, the rebuild/local runtime gate and local wire corrections are completed facts; the current media goal remains open.

Authorities and evidence:

- [research, transport changes and interpretation](research/TELEGRAM_VOICE_UDP.md);
- [temporary emulator/oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md);
- [Phase A observation](verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md) and [Phase B zero-fake failure](verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md);
- [historical 2026-09-05 control](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md);
- [current build/runtime qualification](verification/evidence/2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md);
- [current unmodified OPNsense baseline](verification/evidence/2026-09-20-telegram-voice-current-opnsense-baseline.md);
- [post-NAT position-8 test sequence and restoration](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md).

Established facts:

- **`192.168.1.140` is no longer a working route**, by the owner's explicit correction. It is retired from the active test plan and cannot serve as a current independent control. Its September 5 `MEDIA_PASS` remains a fact about that old epoch and old binary only.
- The owner reports a Telegram voice-transport change as the reason for rebuilding the laboratory. Official tgcalls sources confirm networking and MTProto transport changes; some are disabled by default. The research distinguishes these changes from unverified production rollout and actual Windows/Android negotiation.
- The active tgcalls pin is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; binary SHA-256 is `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. The local P2P run established both sides at 0.039 seconds, collected five records per side, had non-zero BWE and exited 0.
- The build-only `linux-x86_64-no-v2wasm-18-19` adaptation leaves 11/13/14 networking intact. Current reflector runs use engine `13.0.0` on both peers; using current sources alone does not prove parity with every current client configuration.
- The September 20 no-desynchronization run to `91.108.13.10:596` traversed OPNsense correctly: 60 outbound Hello datagrams, preserved payloads and valid checksums, no incoming UDP replies.
- The September 21 pre-NAT checksum defect and subsequent recapture of first fragments were corrected in temporary runner `tgvoice_ipfrag8_postnat_v2.py`. The qualified final run produced 60 ordered pairs, 60 valid reassembled UDP checksums, no original duplicates and no incoming reflector packets.
- That final 15-second CLI run still had both peers `Reconnecting`, no established call, 15 bitrate records per side, zero BWE, no reported errors and exit 1. Result: local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, not `MEDIA_PASS`.
- Restoration is to the recorded pre-test state. Normal rules 19000/19001 were already absent before the post-NAT experiments; restoring that snapshot does not prove normal Zapret forwarding was re-enabled. The existing listener on 989 remained; temporary rule 18990/listener 990 were removed and IPv4 hook order restored.
- Docker `host` is the owner's selected topology, with no independent container IP/MAC. Routing belongs to TNAS; use the measured path through `192.168.1.2` and only bounded endpoint-route changes if necessary. Never prescribe restoration to the retired gateway.
- TNAS/OPNsense console execution is already available. Temporary key-only SSH may automate it later, but does not block experiments.
- The laboratory stays outside installed plugin paths. No GUI, permanent controller/API/configd action, daemon, Generic UDP semantic change or package-owned lab is authorized.

The runtime update to Zapret2 `v1.0.5.2` is owner-reported; exact measured binary/Lua hashes are in the September 21 evidence. The remote `_4` branch remains unpublished and paused, and package identity remains `0.5.0_3`.

## Immediate next boundary

Follow the exact next action in [`START_HERE.md`](START_HERE.md): continue controlled experiments from the qualified post-NAT wire path toward repeated `MEDIA_PASS`, then a real remote Windows/Android `CALL_PASS`. There is no current independent working control. Its absence limits a causal `NETWORK_FAIL` claim; it does not block searching for a working call. A failed restoration remains overriding `RESTORE_FAILED`.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
