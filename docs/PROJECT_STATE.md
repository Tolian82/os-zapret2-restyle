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

## Telegram traffic policy and voice state

The owner-selected goal is **«Воспроизводимая конфигурация того успеха»**: permanent identical Telegram traffic policy for LAN, router-local applications and SOCKS5 clients on OPNsense `192.168.1.2`; UDP through Zapret2 with active `telegram_voice`, TCP/TLS through Squid to parent `185.203.117.88:33128`, and TGVOICE routed through `192.168.1.2`.

Primary homes: [current configuration, helper semantics and reboot commands](architecture/TELEGRAM_TRAFFIC_POLICY.md), [new evidence through October 1](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [protocol research](research/TELEGRAM_VOICE_UDP.md). The [current ledger](history/current/v0.5.x.md) preserves chronology; individual fragmentation results remain reachable through [INDEX](INDEX.md).

Established facts:

- `192.168.1.140` is retired as a working Telegram exit. No alternative working exit exists; upstream `192.168.80.1` is a third-party router without owner access. Its inaccessibility limits causal attribution, not progress on the owned configuration.
- The laboratory was rebuilt after the owner's reported Telegram voice-transport change. Research distinguishes verified upstream networking/MTProto changes from unverified rollout/client parity.
- TNAS `192.168.1.100` / `ovs_eth1` and `tgvoice-lab` share the Docker `host` network. The fixed reflector route is through `192.168.1.2`; the separate `149.154.167.99/32` HTTPS test route is also selected through it. Container-only restart does not itself remove host routes.
- Active tgcalls source is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; binary SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. Its [local P2P gate](verification/evidence/2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md) passed. Current reflector runs use engine `13.0.0` and local in-process signaling, with no external Telegram API/TCP dependency for that signaling.
- The owner reported an established call and correct routing through `192.168.1.2`, identifying the fixed-reflector CLI. The [positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md) is retained; its original positive output and exact strategy attribution remain unavailable. Every later fully correlated documented repeat failed, which does not refute the earlier observation.
- Standalone ordered8 and reverse8/16/24/32 are locally wire-qualified without replies/media. The subsequent combined fakefrag8+reverse24 is also locally wire-qualified and silent. Fakefrag8+original instead lost real packets locally in PF; tee preserved real packets but emitted them before fake. These are distinct conclusions, not a blanket strategy verdict.
- Transparent LAN HTTPS through Squid to the parent was proven on September 30 after correcting the HTTPS endpoint route. Squid's `parentproxy.conf` selects the parent and disallows direct exit for admitted traffic.
- `singbox_squid_lan_policy_20260930_v2.py` successfully applied on October 1 at 03:47 UTC. It added loopback-only plain CONNECT `127.0.0.1:3130`, scoped Squid ACLs and sing-box IPv4 TCP/80,443 selection from a PF-alias snapshot. All five HTTP/HTTPS probes passed with parent evidence. UDP remains `direct` subject to output IPFW. The script did not alter PF/IPFW or enable voice.
- A previous failed v2 run restored files but left a Squid listener; a full `configctl proxy restart` released it. The successful later run is the latest applied state. v2's runtime rollback verification defect and the single unexplained TLS EOF remain recorded; successful reload output is not full restoration proof.
- Latest helper state is `requested=on`, `effective=on`, service running, active profile on, 14 entries, no stage table. The strategy is still `stun-zero-fake-repeats-2`, not reverse fragmentation. It intercepts Telegram IPv4 UDP on all ports but modifies only STUN.
- The October 1 04:15 UTC control sent 60 valid, unfragmented, non-STUN 40-byte Hellos through the helper/WAN. Rule 19000 increased 0→60 packets / 4080 bytes. No reply appeared; both peers stayed `Reconnecting`, BWE was zero, exit 1. Interception is proven; repeatable media is not.

## Open transition debt and next boundary

The permanent goal is not complete. Router-local traffic without explicit proxy is not covered by LAN `rdr`; SOCKS UDP is not separately wire-qualified; the current TCP policy is IPv4/80,443 only and uses a non-refreshing alias snapshot. `telegram_voice` is intentionally requested through an ephemeral `/var/run` marker and returns OFF at reboot. Persistent TNAS routing, service/config survival and the complete three-origin policy need reboot acceptance. Keep the successful configuration backups and use the recovery instructions until these gaps close.

The laboratory remains temporary outside the plugin; permanent router traffic policy is now owner-required and must not be rejected using the older lab-controller restriction. Follow [START_HERE](START_HERE.md) for the exact next task. Reach repeated `MEDIA_PASS` and a real remote `CALL_PASS`, preserving the prior positive report and truthful `NO_REPLY_UNKNOWN`/restoration results.

Runtime Zapret2 `v1.0.5.2` is owner-reported; the exact measured binary/Lua hashes are in [September 21 evidence](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md). The remote `_4` branch remains unpublished and paused; package identity stays `0.5.0_3`.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
