# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-10-08
**Current handoff identity:** `v0.5.0_3` — UDP-only product scope approved; stage 1 repeatable current-oracle MEDIA_PASS through OPNsense remains open; TCP/proxy is laboratory-only

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

Historical 2026-09-02 Zapret2 runtime pin: [`verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

Phase C companion build/runtime evidence: [`verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md`](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md).

Historical 2026-09-05 fixed-reflector control and host-topology evidence: [`verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md).

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

## Telegram Voice UDP — current owner-approved goal

**Product scope is Telegram Voice UDP only**, not permanent Telegram TCP/TLS or router-wide proxy integration. The owner approved three **sequential** stages: (1) reproduce and repeat `MEDIA_PASS` on the current tgcalls reflector oracle through OPNsense; (2) prove a remote P2P-disabled Windows/Android call with sustained bidirectional UDP and audible two-way sound (`CALL_PASS`); (3) integrate the **validated** Voice UDP configuration into `os-zapret2-restyle` with persistent OPNsense-config-backed control in the existing Settings GUI and full managed lifecycle. The normative product boundary is in [Requirements](REQUIREMENTS.md).

Product integration must own Telegram UDP interception, managed Telegram IPSET, proven Zapret2 strategy, restart/stop, conflict-safe firewall rule ownership, and reboot restoration. Use no fixed testbed addresses or hard-coded rule/interface identities. If one fixed strategy works reliably, add only an enable/disable switch to the existing Settings GUI; multiple modes/parameters or a separate page require experimental evidence. The current `/var/run` request marker is temporary PoC state, not the final persistent implementation. **Do not install an unreviewed local product boot hook.** The owner specifically requires **no Cron** for current laboratory Voice ON recovery: if the temporary helper remains necessary, restoration is **once per OPNsense boot only after normal Zapret2 readiness**, independently reviewed and owner-live tested.

**A separate, reboot-persistent three-origin laboratory is an explicit owner requirement.** [Read the exact owner-live operations runbook first](architecture/TELEGRAM_LAB_OPERATIONS.md): it inventories OPNsense startup/config paths, full sing-box GUI snapshot, Squid/parent/ACL, Voice ON-but-not-persistent trap, SSH access to TNAS on port 9222 and the manually operated TNAS route script. [The dated owner evidence](verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md) stores measured values/hashes. **The [helper configuration and IPFW/PF/NAT runbook](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) is mandatory reading before testing or deciding boot automation**: both helper and GUI use one dvtws2; the helper adds destination-scoped all-port Telegram UDP capture and a fixed STUN-only profile, while the current GUI A2 profile separately treats the non-STUN Hello on UDP596–599. No one-shot action has yet been installed. Preserve LAN, OPNsense router-local applications/shell and SOCKS5 Telegram traffic separation: TCP/TLS must reach the experimental Squid/sing-box/PF → external parent path as applicable; UDP must use the selected Zapret2 voice interception; TNAS voice tests route through OPNsense. After OPNsense reboot the lab is intended to recover its chosen working state, but **current experimental Voice ON does not survive reboot** because its request marker is under `/var/run`; temporary manual `configctl zapret telegram_voice_enable` (after checking service and selected baseline) is documented recovery, *not* boot acceptance. **The October 7 reboot now directly confirms the loss, and subsequent manual enable restored native ON/table14; [evidence](verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md).** **Latest owner exception:** TNAS's two specific lab routes are restored by a **manually executed, already owner-tested SSH script on OPNsense** after TNAS reboot; `tgvoice-lab` is deliberately started manually (`restart=no`). No Cron/configd/boot automation for TNAS routes or Docker. Prefer verified native OPNsense settings/GUI for the lab; only where GUI is insufficient select a verified supported alternative. Existing LAN/SOCKS TCP success and a successful owner-live **manual SSH route-script test** are retained, but router-origin Telegram selection, SOCKS UDP, full OPNsense regeneration, persistent Voice-helper ON and the **specific TNAS manual run after an actual reboot** are not yet qualified after reboot. [The lab contract and recovery runbook](architecture/TELEGRAM_TRAFFIC_POLICY.md) owns these obligations.

**This does not enlarge the plugin product scope.** Squid, sing-box, PF proxy redirects, external parent and TNAS lab routes remain outside the three approved product stages. Plugin source/GUI/lifecycle changes occur **only through GitHub** branch/PR/CI/merge; laboratory settings are administered independently through native OPNsense facilities wherever possible. No blanket proxy for every console process is required; the router-local objective concerns Telegram-specific lab traffic. No final TCP architecture or clean-install TCP delivery stages 4–5 are approved. The voice test controller/companion stays outside the package.

## Verified evidence and limitations

- The historical September 5 `MEDIA_PASS` used the old binary and now-retired `192.168.1.140` route, **not** OPNsense; do not restore that route as a control.
- The owner reported an established reflector CLI call through OPNsense on September 22. Its positive CLI output and exact matching strategy/profile/flow are not yet correlated. Keep the positive observation without declaring reverse8 proven.
- Existing ordered8, reverse8/16/24/32 and fakefrag8+reverse24 local wire experiments emitted their documented correct packets but did not deliver a correlated current `MEDIA_PASS`. Do not repeat the completed fragment sweep by inertia. The fakefrag8+original run had a separate local PF real-packet loss; tee changed ordering.
- The latest October 1 ON-helper control intercepted 60 Telegram UDP packets and sent 60 valid 40-byte **non-STUN** Reflector Hellos through the WAN with zero observed replies. Both peers stayed `Reconnecting`, BWE was zero, exit 1. The current STUN-only `stun-zero-fake-repeats-2` helper does not modify that Hello; ON/interception is not voice success.
- **October 2: real P2P-disabled Windows → remote Android call had good owner-reported sound, but two correlated owner-supplied UDP captures show 90 unchanged 40-byte Hello + 9 STUN originals outbound, 18 extra zero16 fakes on WAN, and *zero inbound Telegram UDP*. IPFW Voice rule counters increased exactly 99 packets / 6624 bytes matching those originals. This is a successful audible user observation and verified Voice *interception*, NOT proven UDP voice or formal `CALL_PASS`. TCP/media transport was not captured. [Full dated PCAP/hash analysis](verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md).** **Owner's gateway correction and independent PCAP recheck:** Windows default gateway was **not** OPNsense (configured as proxy), but all 99 observed Telegram UDP Ethernet frames went to the exact MAC that answered from `192.168.1.2`, then exited OPNsense WAN. Do not infer the route of unobserved media/TCP or assume all Telegram UDP was forced through OPNsense. That historical follow-up was completed by the seven controlled calls below; it is not a new per-candidate real-call instruction.
- **October 2 follow-up: owner controlled Windows' IPv4 default via OPNsense `192.168.1.2`; seven real voice calls (#2–#8) connected to Telegram but did not establish.** Independently parsed 14 concurrent TCP+UDP LAN/WAN PCAPs show **345 unchanged non-STUN 40-byte Hellos + 45 STUN originals**, all **390** NAT-forwarded on OPNsense WAN; **90** extra zero16 fakes and **zero captured incoming Telegram UDP** across all seven. LAN concurrently showed direct Telegram TCP/80 (calls 2–4), local Squid :3128 TCP (call 5) and local sing-box SOCKS :1080 TCP (calls 6–8); WAN Squid parent was active. These patterns alone do not identify per-process media or the source of any filtering. After returning Windows' preferred IPv4 default to `192.168.3.140`, the **owner reported calls established**; this positive route control lacks a captured successful-call media trace and may differ in app proxy settings. [Full dated seven-call evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md).
- **Follow-up packet-integrity check of calls #2–#8:** independent IPv4-header and post-NAT UDP-pseudoheader checksum validation passed for **all 480 captured outbound Telegram UDP datagrams** (390 originals + 90 fakes); there is no observed WAN checksum corruption in these **unfragmented** real-call packets. This does not prove packets reached Telegram or explain missing replies; use the [dated seven-call evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md), not September's fragment checksum behavior, when assessing this series.
- **October 2 newer standalone Telegram Desktop debug call (16:16) over the reported OPNsense-only default with no Telegram proxy:** private WebRTC log confirms *bidirectional app signaling/Opus/remote ICE candidate reception* but only outbound TURN/Reflector attempts on the intended `192.168.1.x` NIC, no established usable ICE/media path logged and `NativeNetworkingImpl timeout 20011 ms`. Windows also exposed TnasOnline and 192.168.192.x candidates, whose failed TURN sends are secondary-adapter errors, not evidence the proper NIC failed locally. A separately uploaded Telegram main startup log begins **11 minutes later**, not the same call. [Dated sanitized evidence/2 private-log hashes](verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md). No matched same-call PCAP; preserve earlier packet-level diagnosis. A successful alternate-route capture is optional causal diagnosis, not the current next task. The original earlier main-log copy is distinguished in the October 5 source review below.
- October 1 LAN HTTPS and SOCKS5 TCP/443 via Squid and the external parent have passed. Additional owner verification on October 1 again confirmed transparent TNAS HTTPS `HTTP=200` and Squid `FIRSTUP_PARENT`. These are **retained lab facts**, not new plugin requirements or proof of UDP voice.

Evidence: [September 22 positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md), [September 23–October 1 results](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [current media oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [current laboratory proxy and route recovery](architecture/TELEGRAM_TRAFFIC_POLICY.md), and [protocol research](research/TELEGRAM_VOICE_UDP.md).

## Actual current assignment — October 8 helper controls and reviewed execution plan

**DO NOT REINTERPRET THE GOAL:** The owner's local ISP restricts Telegram **voice UDP** with DPI. Find a **Zapret2 UDP strategy through the existing OPNsense `192.168.1.2` and SAME ISP WAN** that eventually restores real Telegram voice. Do NOT redirect this effort into a new VPN, UDP relay, other gateway/provider or TCP proxy project.

**Working TCP/TLS lane is settled and MUST remain intact:** OPNsense PF/Squid and the selected sing-box→Squid Telegram TCP route use **`185.203.117.88:33128`, the existing external parent configured in OPNsense's Squid GUI**. LAN/SOCKS parent HTTPS tests passed. Squid parent does not transport voice UDP; sing-box UDP `direct` still uses the local ISP/DPI and applicable IPFW/Zapret2. Neither the TCP path nor its GUI ownership needs redesign. [Binding contract](REQUIREMENTS.md) · [measured TCP/UDP separation](architecture/TELEGRAM_TRAFFIC_POLICY.md).

**Existing UDP research path:** TNAS host-network Docker `tgvoice-lab` uses the pinned current `tgcalls_cli`, fixed `91.108.13.10:596`, its existing destination `/32` via **OPNsense `192.168.1.2`**, then the local ISP. The qualified [A1/A2 one-command runner](../tools/telegram-voice-lab/run-a1-opnsense.sh) uses existing owner-tested OPNsense→TNAS SSH and manual route guard and archives the actual active strategy, Voice/IPFW, LAN/WAN captures and peer states. No per-candidate human calls, no new device routes/tunnels. Retired `192.168.1.140` is not a valid current Voice exit. The lab Voice helper's `/var/run` marker does not survive OPNsense reboot; TNAS host-route restoration after TNAS reboot is owner-selected **manual only**, no Cron or Docker autostart.

**Already measured:** A1 (60 genuine intact 40-byte Hellos + 120 correctly ordered intentionally invalid-checksum fakes) and A2 (same 60 genuine + 120 correctly ordered **valid**-checksum fakes) both reached the local NATed WAN in exact [fake, fake, genuine] triplets. Both recorded **zero** incoming reflector responses, both peers Reconnecting, BWE zero, CLI exit 1. Thus **both `WIRE_OK / NO_REPLY_UNKNOWN`, neither `MEDIA_PASS`**; the one-variable checksum change alone was insufficient. WAN silence does not independently identify the exact upstream discard point. [A1 report](verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) · [A2 report](verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md).

**Confirmed by the October 7 documentation/source review:** TNAS and OPNsense share the owner's LAN/virtual switch, but reflector-mode caller and callee both address the external `91.108.13.10:596` through OPNsense/WAN. Only signaling is bridged in-process; the passed local P2P smoke is a separate binary gate. A2 emitted fakes and originals with WAN TTL=63, so it did not test deliberately short-lived fakes. TTL decreases and expires whole packets; fake rejection, invalid UDP checksum and genuine IP-fragment reassembly are distinct mechanisms. CLI exit 0 alone is weaker than the project's both-peer/bidirectional-UDP acceptance. [Full October 5 discussion, source review and limits](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md).

**Mandatory helper baseline for every trial:** keep `telegram_voice` ON, the managed Telegram IPv4 target set and the fixed STUN zero16/repeats=2 profile unchanged. A1→A2 changed the GUI `unknown` Hello treatment, not the helper. The next fake-TTL comparison changes only that experimental GUI action; changing the STUN helper does not target the observed non-STUN Hello. The [per-trial control matrix and change-recording contract](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#telegram_voice-controls-for-every-trial) make helper state, source/profile identity, full target set, actual capture rule and before/after verification explicit. Future helper changes require a separate stated hypothesis and recorded old/new values; disabling the whole helper is not the candidate-action OFF control.

**Latest owner-live configuration result, October 7:** the before/reboot/after snapshots prove Voice ON→OFF while saved/effective GUI A2, target data and ordinary UDP/596–599 capture survived; manual `telegram_voice_enable` then restored native ON/table14/all-port rule19000 with zero counters. [Dated evidence and measurement limits](verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md). No automatic boot recovery or new call success is established. Before the next trial take the complete post-recovery baseline; do not repeat the reboot or unchanged A1/A2 merely to recover these already measured facts.

**Immediate engineering task:** extend the existing independent one-command runner with full RTC `--log-file`, bounded correlated ICMP capture, strict saved/effective candidate and fixed-helper checks (source/full profile/target set/actual process and semantic before/after state), and verified owned remote-process/container cleanup. Stop on baseline drift; do not silently enable the helper inside an acquisition. Current v4 acquisition is qualified for its measured A1/A2 runs, not for this new contract. Then prepare a distinct **limited-fake-TTL** candidate relative to A2, changing only fake `ip_ttl`. The [October 7 execution plan and expected outcomes](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#next-experiment-limited-fake-ttl-planned-not-run) bounds the initial screen to at most four TTL values and defines reply/local-delivery/ICE/media branches, a sustained observation window and three fresh successful candidate runs. Commit exact syntax, values and rollback; pass GitHub/CI before one csh-safe owner invocation. **No numeric TTL is selected, no runner change is delivered and no new media trial has run in this documentation scope.**

The first new network milestone is a valid reflector reply accepted by the library, followed by both peers Established and sustained bidirectional UDP. Repeat a winner on fresh flows and compare only its experimental action enabled/disabled on the same path, keeping Voice-helper/interception ON. A reply visible on WAN but absent at the client redirects work to local return delivery; an accepted reply with no media redirects it to ICE/media, not more blind TTL guesses. Do not repeat unchanged A1/A2 or the completed fragment sweep as a blind search. A separate healthy same-endpoint route remains **optional causal control**, not a new-egress prerequisite. The [read-only topology helper](architecture/TELEGRAM_VOICE_INDEPENDENT_CONTROL.md) is optional, not the next required command. The owner's practical priority remains real-call **connection through `.1.2` first**, then sound quality; Docker screening precedes human calls under the already selected workflow.

Repeat genuine current Docker `MEDIA_PASS` **through OPNsense and the local ISP** before a single final P2P-disabled Windows/Android call demonstrating sustained bidirectional UDP and audible speech (`CALL_PASS`). Only afterward implement **UDP-only** plugin integration with persistent existing Settings GUI control and managed IPFW/IPSET lifecycle. Package remains `0.5.0_3`; these corrections change no appliance configuration or package.
