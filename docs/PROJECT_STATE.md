# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-10-05
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

The owner's clarified October 1 decision **supersedes only inclusion of the three-origin TCP/UDP policy in the plugin product**, not the policy itself: three-origin post-reboot operation remains mandatory in the independent laboratory. Only **Telegram Voice UDP** is approved for new `os-zapret2-restyle` product integration. Requirements and ordering: [Telegram Voice UDP product contract](REQUIREMENTS.md); [exact next step](START_HERE.md); [approved three-stage roadmap](ROADMAP.md). The approved gates are (1) repeated current-oracle `MEDIA_PASS` through OPNsense; (2) remote real Windows/Android P2P-disabled `CALL_PASS` with sustained bidirectional UDP and audible two-way speech; (3) only then integration of the validated UDP strategy/rules/IPSET/lifecycle into the plugin with OPNsense-config-backed GUI state and restart/reboot recovery.

The plugin already has a service lifecycle. Its temporary `telegram_voice` proof of concept uses an ephemeral `/var/run` marker; persistent configuration in the existing Settings GUI **is required for the eventual product stage**, not already implemented. Start with only an enable/disable checkbox if one reliable strategy suffices; configurable parameters or a dedicated page require test evidence. Production targets/interfaces and firewall rule ownership must be derived/managed, not hard-coded for the current laboratory.

**Two separately owned goals coexist.** The plugin remains **UDP-only** under the three approved stages; Squid, sing-box, external parent, PF proxy rules, SOCKS and TNAS routes stay outside its product implementation. **The laboratory, however, retains the entire three-origin LAN/router-local/SOCKS Telegram TCP-versus-UDP policy and must preserve or recover its selected functional state after OPNsense and TNAS reboot.** Its TCP/TLS traffic is intended to reach the experimental external parent, Telegram UDP the selected Zapret2 treatment, and the TNAS voice path OPNsense. Prefer verified native OPNsense GUI/services for lab persistence, and a supported documented mechanism if a requirement is not exposed in GUI. Router-local Telegram-specific selection is a lab goal, not a blanket automatic proxy for all console applications. All **plugin** source, configuration-model, GUI and lifecycle changes are made **only through GitHub**; laboratory settings are maintained separately. The complete TCP/proxy architecture and clean-install TCP delivery are not approved additional product stages; the `tgcalls` laboratory/controller remains outside the package. [The laboratory contract/reboot runbook](architecture/TELEGRAM_TRAFFIC_POLICY.md) owns configuration and checks.

**2026-10-03 reaffirmed mission:** local ISP DPI restricts **Telegram voice UDP** (owner-established premise). We seek **Zapret2 UDP desynchronization through existing OPNsense `192.168.1.2` and that SAME local ISP**, not a new VPN/UDP tunnel/alternate gateway or substitute provider. Telegram **TCP/TLS is ALREADY WORKING** through PF/Squid and matching sing-box→Squid, using **external `185.203.117.88:33128`, the owner's GUI-configured Squid parent**. LAN/SOCKS tests confirmed TCP parent behavior. The HTTP parent is not the UDP voice path; sing-box UDP `direct` still uses current WAN/DPI and applicable IPFW/Zapret2. Preserve the current working TCP GUI/ACL/proxy settings. WAN PCAP results alone cannot localize the exact upstream UDP loss site, distinct from the owner-provided ISP-blocking premise. [Normative requirements](REQUIREMENTS.md) · [existing live operations](architecture/TELEGRAM_LAB_OPERATIONS.md).

**Current measured stage 1 evidence:** pinned TNAS Docker `tgcalls_cli` sent 60 intact genuine 40-byte Reflector Hellos through its selected `/32 via OPNsense` in each A1 and A2 run, accompanied by 120 correctly ordered zero16 fake datagrams. A1 fake UDP checksums intentionally invalid; A2 fake checksums all valid. Both zero captured incoming pinned-reflector replies, peers Reconnecting/BWE zero, exit 1: **`WIRE_OK / NO_REPLY_UNKNOWN`, NOT `MEDIA_PASS`**. A1→A2 checksum change alone insufficient. Prior fragment families and historical observations stay recorded separately. [A1](verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) · [A2](verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md).

**October 5 source/topology conclusions:** owner confirms TNAS and OPNsense share one LAN/virtual switch. In pinned CLI reflector mode both local clients use the external UDP reflector through OPNsense; signaling alone is in-process, P2P is disabled and the configured reflector is not TCP. The local P2P smoke does not test provider DPI. A2's measured WAN TTL=63 for all genuine/fake packets is not a limited-TTL experiment. Separate fake packets, explicit TTL expiry, bad UDP checksums and genuine IP-fragment reassembly must not be conflated. The CLI's shared `establishedAt` can be set by either peer; exit 0 alone does not implement the project's stronger both-peer and bidirectional-UDP gate. [Source-grounded discussion, primary references and original-versus-later Desktop log distinction](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md).

**Next boundary:** [START_HERE](START_HERE.md) selects RTC/ICMP observability in the existing runner, then a bounded limited-fake-TTL hypothesis relative to A2 on the same OPNsense/ISP route. This is planned and untested; no numeric TTL, new runner or appliance change is delivered by this documentation update. Full procedure belongs to the [Docker campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#next-experiment-limited-fake-ttl-planned-not-run). Same-endpoint healthy-route control remains optional causal diagnosis, not a mandatory new exit; existing inventory helper is optional. Repeated Docker media success precedes real-call connection/UDP/sound acceptance and eventual UDP-only integration. Preserve working TCP and the retired status of `192.168.1.140`.

### Durable evidence and current uncertainty

- Historical September 5 `MEDIA_PASS` through the now-retired `192.168.1.140` route belongs to the old laboratory binary/epoch, not the current OPNsense provider path. No current independent working control exists; the third-party upstream `192.168.80.1` is inaccessible.
- The owner reported a fixed-reflector CLI call established through OPNsense `192.168.1.2` on September 22, but positive CLI output and full strategy-to-flow correlation remain unavailable. Do not erase the report or attribute it definitively to reverse fragmentation.
- The qualified current tgcalls source is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; binary SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; local P2P smoke passed. Later fully correlated reverse and combined fake-fragment runs had correct on-wire output but no reflector replies/media; fakefrag8+original instead had documented local PF real-packet loss.
- **October 2 real Windows → remote Android call:** both clients P2P disabled; owner reported clear, uninterrupted sound. Concurrent owner-supplied UDP-only LAN/WAN PCAPs and before/after counters show 90 identical non-STUN 40-byte UDP requests to one Telegram endpoint, 9 STUN requests to another, all 99 originals byte-identical across NAT, 18 additional zero16 WAN fakes and *zero inbound Telegram UDP*. Voice rule `19000` 0/0→99/6624, exactly 90×68 + 9×56 IPv4 bytes. Current outbound PFIL IPFW→PF confirmed; no hook changes. Actual audible media transport unproven (possibly TCP, not captured). Record **REAL_CALL_AUDIO_REPORTED_GOOD / VOICE_IPFW_CAPTURE_PASS / UDP_MEDIA_NOT_OBSERVED**, NOT `CALL_PASS` or source attribution. [Full owner-PCAP hashes and correlated analysis](verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md). The separate TNAS `MEDIA_PASS` gate remains open. The owner's later clarification establishes that Windows **did not use OPNsense as its system-wide default gateway**; it was configured as proxy. Subsequent direct LAN Ethernet frame inspection nevertheless confirms all 99 observed Telegram UDP datagrams were sent to OPNsense's LAN MAC (independently identified using DNS replies from `192.168.1.2`) and forwarded/NATed by its WAN. The audible transport of that early call remains unmeasured. The subsequent seven controlled calls below completed the historical route/capture follow-up; no new per-candidate human call is requested.
- **October 2 seven-call controlled route follow-up:** Windows `192.168.1.107` used **only default IPv4 gateway `192.168.1.2`**; owner reports Telegram itself connected but all seven voice calls (#2–#8) failed. Fourteen independent LAN/WAN TCP+UDP PCAPs show **390 original outbound Telegram UDP datagrams** (345 repeated non-STUN 40-byte reflector Hellos, 45 STUN requests), all matched by payload byte-for-byte after OPNsense NAT, **90** extra 16-byte STUN fakes and **zero inbound Telegram UDP** in these capture windows. Concurrent LAN TCP differed (direct Telegram TCP/80 in #2–4; local Squid :3128 in #5; local SOCKS :1080 in #6–8), while WAN parent TCP remained active. The specific client application/proxy attribution of these TCP flows was not independently captured. Restoring the **other preferred Windows default `192.168.3.140`** led to **owner-reported established voice calls**, but no paired *successful-route PCAP* or exact per-call Telegram proxy setting was included; do not conclude UDP media/pass or a provider-specific root cause. [Exact A/B route transcript, counts, timestamps and private-PCAP hashes](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md). **Optional causal diagnostic:** capture a successful alternate-gateway call only if separately needed; the separate fixed-reflector `MEDIA_PASS` and formal UDP `CALL_PASS` remain open.
- **Checksums independently validated for the October 2 seven-call WAN captures:** all **390 matched UDP originals** and all **90 16-byte WAN STUN fakes** have **valid recorded IPv4 header and UDP post-NAT pseudoheader checksums** (480/480 for each). The original LAN datagrams were also valid. No captured local UDP checksum corruption explains these **unfragmented** failed attempts; this neither proves upstream delivery nor settles why Telegram replies are absent. [Complete per-call evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md).
- **October 2 newer, independently timed Windows Telegram Desktop WebRTC debug attempt:** owner reports OPNsense `192.168.1.2` exclusively as default gateway, no Telegram app proxy, voice call still did not establish an encrypted connection. Private `last_call_log` covers **16:16:44–16:17:04**, demonstrates received bidirectional app signaling and remote relay candidates, correct-NIC reflector probes/TURN request dispatch **without any confirmed usable ICE pair/remote DTLS handshake**, then `NativeNetworkingImpl timeout 20011 ms`. Failures `10051`/`10049` occur on secondary Windows TnasOnline and iSCSI NIC candidates, not the correct NIC; do not confuse `DTLS setup complete` during remote configuration with actual secured media. The separately uploaded later main-log copy used by that report starts only **16:27** and cannot be combined with the earlier call timeline. An original earlier copy matching the 16:16 attempt is separately identified by SHA-256 in the October 5 source review above. [Sanitized event sequence and original private SHA-256s](verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md). The absence of matching same-call PCAP means this strengthens, but cannot be byte-correlated to, the earlier seven-call zero-reply signature. Alternate-route capture is optional for separate causal analysis, not the next strategy-screening task; approved UDP gates remain open.
- October 1 `telegram_voice` was ON and complete. with 14 managed table entries and STUN-only `stun-zero-fake-repeats-2`. It intercepted 60 packets, emitted 60 valid unchanged non-STUN 40-byte Reflector Hellos, received no WAN replies, and the reflector CLI returned exit 1 with both peers `Reconnecting`. The current helper does not transform this Hello; voice success is **not** verified.
- September 30 and October 1 LAN HTTPS and SOCKS5 HTTP/HTTPS tests passed through Squid to external parent `185.203.117.88:33128`. Additional October 1 owner verification after the TNAS HTTPS route correction again obtained `HTTP=200` and a matching Squid `FIRSTUP_PARENT` tunnel. These are lab-only TCP facts. The retained TNAS reflector/HTTPS routes through `192.168.1.2` are lab routes, not product defaults.

Detailed protocol research and current oracle: [Telegram UDP research](research/TELEGRAM_VOICE_UDP.md), [Telegram Voice emulation architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Current testbed TCP/route recovery: [laboratory traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md). Results and archive identities: [September 23–October 1 evidence](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md); [original positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md). Preserve the successfully applied lab configuration and backup artifacts; do not change running TCP services merely to align the documentation.

**2026-10-01 owner-live lab inventory closed for the currently measured configuration.** [The operations runbook](architecture/TELEGRAM_LAB_OPERATIONS.md) records GUI and effective file ownership, Squid/sing-box RC/configd startup, the complete OPNsense→TNAS SSH setup, verified manual route script and precise commands, and the Voice ON-after-reboot failure mode. [The dated measurements](verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md) preserve full owner-provided sing-box GUI JSON and current file fingerprints. The OPNsense console is **csh**, and the local SSH binary is **`/usr/local/bin/ssh`**; default console commands must respect this. The owner deliberately rejected TNAS route Cron/configd and Docker autostart: both routes are checked/restored **manually** through the tested OPNsense SSH script after a TNAS reboot, and the container is started on demand. At this epoch Telegram Voice is **requested=on/effective=on**, 14 entries/rule 19000, but this experimental state is ephemeral and reverts to OFF after an OPNsense reboot unless explicitly re-enabled. Native Zapret boot startup alone does **not** preserve Voice ON.

**Latest owner source-audit/boot decision:** [GUI versus helper, IPFW capture and PF/NAT order](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) are now documented. Helper Voice and GUI use the **same dvtws2 process and managed Telegram dataset**, but the separate Voice rule matches all UDP ports **to Telegram IPs**; ordinary GUI port rules match listed ports **to any WAN IP**, and adding `--filter-udp=*` in GUI cannot produce equivalent capture under current numerical-only extractor. No repeated encryption; current STUN-only Voice does not transform non-STUN Reflector Hello. The owner explicitly forbids **Cron/periodic telegram-voice-enable**: any lab workaround must be **once at OPNsense startup after normal Zapret2 is ready**, or be replaced by a separately approved native plugin redesign. The October 2 owner's prior read-only `pfilctl heads` already showed IPv4 WAN output IPFW→PF for the earlier call epoch; recheck only after boot/hook changes. **No boot fix has been deployed or tested by this documentation change.**

**Lab permanence is an approved requirement but not a verified result.** October 1 LAN HTTPS and SOCKS TCP parent checks passed, but router-origin Telegram automatic selection, SOCKS UDP, Squid/sing-box regenerated state, **automatic OPNsense Voice-helper ON recovery**, alias synchronization and **the selected manual route-script procedure after an actual TNAS reboot** have not been jointly accepted after reboot. TNAS route auto-recovery and Docker autostart are **not** required by the owner. Manual recovery commands are a contingency, not successful automatic reboot acceptance. Retain the working TCP configuration while making supported lab persistence changes in a separately controlled test.

Package identity stays `VERSION=0.5.0`, `PLUGIN_REVISION=3`; remote `_4` remains unpublished and paused. The owner-approved product behavior is **planned**, not yet implemented or qualified.

**2026-10-03 A2 superseding outcome:** The owner's first Docker A2 run passed unique saved/effective A2, Voice ON/table14, owner TNAS route guard and pinned host-network Docker. Independent LAN/WAN PCAP analysis: 60 genuine 40-byte Hello preserved after NAT; 120 zero16 fakes with **120/120 valid UDP checksums** precede every original in exact 60/60 triplets; no pinned reflector replies on either interface, zero capture drops. Both peers Reconnecting, BWE zero, CLI exit 1. **A2 CONFIG_PASS/WIRE_OK/NO_REPLY_UNKNOWN; MEDIA_PASS OPEN**. Relative to A1, removing only `:badsum` proved insufficient in this epoch; do not infer provider drop stage or reflector readiness. [Measured A2 evidence](verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md). A fresh healthy same-endpoint control is optional causal diagnostic; it is not an independent-UDP-exit prerequisite before any further controlled same-ISP Zapret2 research. Retired `.140` prohibited; keep TCP/proxy and A2 lab baseline unchanged.
## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
