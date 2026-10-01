# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-10-01
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

## Telegram Voice UDP: current product scope and measured state

The owner's October 1 decision **supersedes** the former permanent three-origin TCP/UDP policy goal. Only **Telegram Voice UDP** is approved for new `os-zapret2-restyle` product integration. Requirements and ordering: [Telegram Voice UDP product contract](REQUIREMENTS.md); [exact next step](START_HERE.md); [approved three-stage roadmap](ROADMAP.md). The approved gates are (1) repeated current-oracle `MEDIA_PASS` through OPNsense; (2) remote real Windows/Android P2P-disabled `CALL_PASS` with sustained bidirectional UDP and audible two-way speech; (3) only then integration of the validated UDP strategy/rules/IPSET/lifecycle into the plugin with OPNsense-config-backed GUI state and restart/reboot recovery.

The plugin already has a service lifecycle. Its temporary `telegram_voice` proof of concept uses an ephemeral `/var/run` marker; persistent configuration in the existing Settings GUI **is required for the eventual product stage**, not already implemented. Start with only an enable/disable checkbox if one reliable strategy suffices; configurable parameters or a dedicated page require test evidence. Production targets/interfaces and firewall rule ownership must be derived/managed, not hard-coded for the current laboratory.

**TCP/TLS, Squid, sing-box, external parent proxy, PF redirect rules, SOCKS and selected TNAS routes remain experimental laboratory infrastructure and are not current plugin integration requirements.** Preserve the working TCP laboratory configuration unchanged. OPNsense-native GUI persistence for that separate lab setup is allowed. Automatic router-console proxy configuration has been cancelled. Previous tasks for a persistent three-origin TCP policy, PF-alias synchronization as product scope and SOCKS UDP integration are no longer approved product work. Whole-system clean-install TCP/proxy delivery and final TCP architecture are not included in the three approved work stages. The temporary `tgcalls` laboratory/controller is also excluded from the plugin package.

### Durable evidence and current uncertainty

- Historical September 5 `MEDIA_PASS` through the now-retired `192.168.1.140` route belongs to the old laboratory binary/epoch, not the current OPNsense provider path. No current independent working control exists; the third-party upstream `192.168.80.1` is inaccessible.
- The owner reported a fixed-reflector CLI call established through OPNsense `192.168.1.2` on September 22, but positive CLI output and full strategy-to-flow correlation remain unavailable. Do not erase the report or attribute it definitively to reverse fragmentation.
- The qualified current tgcalls source is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; binary SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; local P2P smoke passed. Later fully correlated reverse and combined fake-fragment runs had correct on-wire output but no reflector replies/media; fakefrag8+original instead had documented local PF real-packet loss.
- October 1 `telegram_voice` was ON and complete, with 14 managed table entries and STUN-only `stun-zero-fake-repeats-2`. It intercepted 60 packets, emitted 60 valid unchanged non-STUN 40-byte Reflector Hellos, received no WAN replies, and the reflector CLI returned exit 1 with both peers `Reconnecting`. The current helper does not transform this Hello; voice success is **not** verified.
- September 30 and October 1 LAN HTTPS and SOCKS5 HTTP/HTTPS tests passed through Squid to external parent `185.203.117.88:33128`. Additional October 1 owner verification after the TNAS HTTPS route correction again obtained `HTTP=200` and a matching Squid `FIRSTUP_PARENT` tunnel. These are lab-only TCP facts. The retained TNAS reflector/HTTPS routes through `192.168.1.2` are lab routes, not product defaults.

Detailed protocol research and current oracle: [Telegram UDP research](research/TELEGRAM_VOICE_UDP.md), [Telegram Voice emulation architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Current testbed TCP/route recovery: [laboratory traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md). Results and archive identities: [September 23–October 1 evidence](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md); [original positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md). Preserve the successfully applied lab configuration and backup artifacts; do not change running TCP services merely to align the documentation.

Package identity stays `VERSION=0.5.0`, `PLUGIN_REVISION=3`; remote `_4` remains unpublished and paused. The owner-approved product behavior is **planned**, not yet implemented or qualified.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
