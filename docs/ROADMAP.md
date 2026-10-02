# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-10-01

- Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md)
- Exact handoff: [`START_HERE.md`](START_HERE.md)
- Current-line detail: [`history/current/v0.5.x.md`](history/current/v0.5.x.md)

## Completed project path

- [x] Initial OPNsense plugin and independent project identity
- [x] Runtime/service lifecycle and transactional Apply
- [x] Unified Traffic Strategy and managed HOSTLIST/IPSET targets
- [x] Zapret2 Service GUI for upstream install/update/reinstall/downgrade
- [x] Diagnostics fixes and blockcheck redesign
- [x] Strategy Lab foundation and Python migration
- [x] Adaptive candidate search and timeout/budget containment
- [x] Model A/B/C experimentation and **Model C selection**
- [x] Model-C-only normal production execution
- [x] Source-port attribution/leasing and readiness hardening
- [x] Lua/BLOB/discovery measurement cycle and production decisions
- [x] Generic UDP exact-byte path and QUIC execution observability
- [x] Explicit persisted **Enable QUIC** execution control
- [x] Enable QUIC ON/OFF execution semantics
- [x] **Enable QUIC preference reload/revisit persistence — OWNER-LIVE PASS**
- [x] Strategy Lab RU/EN presentation and native OPNsense Laboratory layout
- [x] Laboratory domain + IPv4 targets with optional Host/SNI
- [x] Truthful HTTP `4xx`/`5xx`, bare-IP identity and QUIC result classification
- [x] Final fixed-IP `--ipset-ip=<target>` profile/replay
- [x] Selected Stage-90 restoration/residue owner-live coverage
- [x] `v0.4.x` owner-live feature closeout

## `v0.5.0_1` release transition — COMPLETE

- [x] owner explicitly selected second-component transition `v0.4.x -> v0.5.x`
- [x] close Enable QUIC preference persistence from owner confirmation
- [x] set `VERSION=0.5.0`
- [x] reset `PLUGIN_REVISION=1`
- [x] roll current documentation to `v0.5.x`
- [x] archive final `v0.4.x` line
- [x] complete README release review and feature presentation
- [x] exact-head complete CI — run `31915884270`
- [x] FreeBSD 15 package qualification — run `31915884270`
- [x] exact squash merge `v0.5.0_1: Prepare release v0.5.0` — `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`
- [x] immutable stable tag `v0.5.0` points to the exact release merge
- [x] stable GitHub Release package/checksum publication — workflow `31916256043`
- [x] matching Pages/pkg repository deployment and verification — workflow `31916256043`

Stable package: `os-zapret2-restyle-0.5.0_1.pkg`.

SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`.

Full release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

## `v0.5.0_2` file-picker localization corrective — COMPLETE

Fresh owner evidence selected a concrete post-release defect: the visible Generic UDP browser-native file picker could show Russian browser/OS labels while OPNsense/Strategy Lab was set to English.

- [x] identify browser-native `<input type="file">` chrome as the localization leak
- [x] keep the real native input only as the hidden file-selection mechanism
- [x] add Strategy Lab-owned RU/EN picker button and filename text
- [x] preserve selected filename, busy-state disabling, FileReader/Base64 staging and 1–4096-byte validation
- [x] add regression coverage forbidding return of the visible native `form-control` file picker
- [x] exact-head complete CI — run `31917466421`
- [x] FreeBSD 15 package qualification — run `31917466421`
- [x] exact squash merge for `v0.5.0_2` — `1ae952185dbae80ec34c0a89b441feddbe8b403a`
- [x] persistent GitHub testing-package publication — `v0.5.0_2`, workflow `31917806438`
- [x] bounded publication-record reconciliation — PR `#270` merged, generated evidence state closed afterward
- [x] focused owner-live RU/EN file-picker verification — **OWNER-LIVE PASS**

Testing package: `os-zapret2-restyle-0.5.0_2.pkg`.

SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

Owner-live evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

The stable Pages/pkg repository remains on `v0.5.0_1`; `_2` was not automatically promoted.

## `v0.5.0_3` current testing line — TELEGRAM VOICE LAB ACTIVE

- [x] keep package identity at `VERSION=0.5.0`, `PLUGIN_REVISION=3`
- [x] retire the `e3069322...` binary from active laboratory use
- [x] pin the only active tgcalls oracle to `efd330ca04f74706024a5abdfb5b41f4e4dd1065`
- [x] require a local P2P smoke gate and SHA-256 manifest for that current oracle
- [x] qualify current `efd330ca...` build/runtime on TNAS — **OWNER-LIVE PASS**, SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`
- [x] record owner runtime update to Zapret2 v1.0.5.2 for future live candidate epochs
- [x] keep this change lab/docs-only; no package payload or revision bump

## Telegram Voice UDP — three owner-approved stages

**Product boundary:** Telegram Voice UDP alone will become integrated into `os-zapret2-restyle`, after the approved media gates. Squid, sing-box, PF proxy rules, external parent proxy and TNAS routing remain **separate laboratory infrastructure**, not plugin deliverables. However, the owner requires that full three-origin lab separation and working proxy/routing **survive or automatically recover after reboot**, just as before reboot. This is a mandatory parallel **lab** track, not a new plugin product stage. No blanket proxy for every OPNsense console process, new TCP integration stage or complete product TCP clean-install scope is approved. Plugin code/config-model/GUI changes use **GitHub only**; lab settings prefer proven native OPNsense GUI/facilities. [Product requirements](REQUIREMENTS.md), [laboratory persistence contract](architecture/TELEGRAM_TRAFFIC_POLICY.md) and [current handoff](START_HERE.md) are authoritative.

### Parallel requirement — independent persistent laboratory (not plugin stage 4)

- [x] Prove the bounded October 1 LAN HTTPS and SOCKS5 Telegram IPv4 TCP/80,443 paths through Squid to the external parent. Retain the working setup unchanged for now.
- [ ] Maintain a single documented lab baseline for **LAN, router-local Telegram traffic and SOCKS5 clients** with separate TCP/TLS parent-proxy and Telegram UDP/Zapret2 paths. Router-local Telegram TCP/TLS without explicit SOCKS and SOCKS UDP ASSOCIATE are not yet qualified; this is not a request for global console proxy variables.
- [ ] Prefer supported OPNsense GUI configuration and service persistence for Squid, PF and eligible settings; explicitly verify how non-GUI sing-box/ACL/snapshot state survives regeneration. Do not invent GUI features or modify plugin code directly on the appliance.
- [ ] Restore the selected **Voice-helper ON** state after **OPNsense reboot**, **one time only** after regular Zapret2 is ready. **No Cron/recurring `telegram-voice-enable`**, per explicit owner decision. Current transient `/var/run` state is lost at reboot; no fix installed or owner-live validated yet. Before choosing a lab mechanism, honor the [source audit of GUI strategy versus destination-scoped Voice IPFW capture and PF/NAT order](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). Retain ordinary services, firewall state and ACL/alias synchronization without uncontrolled changes.
- [x] Install and owner-test **manual** OPNsense→TNAS Ed25519 SSH on port 9222 and a guarded two-host-route repair script on OPNsense; manual test passed with both current routes intact.
- [ ] After a future TNAS reboot, owner manually runs the verified route script and verifies actual route restoration. **No TNAS route Cron/configd/boot scheduling and no tgvoice-lab Docker autostart**, by explicit owner decision.
- [ ] Compare OPNsense pre/post-reboot snapshots and repeat service, LAN/SOCKS/router-local TCP-to-parent and separate relevant UDP/interception tests. Record individual failures; manual Voice re-enablement remains a fallback, **not automatic OPNsense recovery acceptance**. Separately verify the owner-selected *manual* TNAS routes after an actual TNAS reboot.

This parallel lab requirement is tracked in the [exact owner-live operations/reboot/SSH runbook](architecture/TELEGRAM_LAB_OPERATIONS.md) and [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md) and does **not** add Squid, sing-box, TCP proxy functionality, SOCKS integration or routes to the `os-zapret2-restyle` package.

### Completed research and lab setup (evidence, not product acceptance)

- [x] Phase A/B Telegram TURN/STUN and reflector traffic observation; STUN zero-fake helper mechanically qualified but did not restore UDP replies/media on the provider path.
- [x] Build and qualify the current `tgcalls_cli` oracle and local P2P smoke; fix reflector endpoint `91.108.13.10:596` for comparable epochs.
- [x] Preserve the historical September 5 reflector `MEDIA_PASS` via retired `192.168.1.140`; record the owner's September 22 established-call report through OPNsense without inventing strategy attribution.
- [x] Establish actual non-STUN 40-byte current Reflector Hello behavior, normal forwarding/NAT, post-NAT local fragmentation fidelity and all already-completed standalone reverse-position/combined-fake experiments without media replies.
- [x] Verify October 1 Telegram IPv4 TCP/80,443 over laboratory LAN/Squid/parent and SOCKS5/sing-box/Squid/parent, followed by renewed owner-live LAN HTTP 200 and Squid parent tunnel after route correction. Keep this working lab configuration unchanged.
- [x] Preserve the October 2 *early* real Windows → remote Android P2P-disabled call with good owner-reported sound: two matching PCAPs confirm 90 unchanged non-STUN Hellos + 9 STUN originals traversed Voice IPFW, plus 18 WAN fake payloads, *no inbound Telegram UDP*. Packet counters 99/6624 match originals exactly. **Not** UDP `CALL_PASS`; TCP/audio path was not recorded. [Exact evidence](verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md). Owner subsequently clarified Windows' **default gateway was not OPNsense**. Direct capture Ethernet analysis confirms the **observed 99 Telegram UDP originals nevertheless targeted OPNsense's LAN MAC**, matching its DNS-server source MAC; don't extrapolate this to all media. A repeat requires confirmed per-destination Windows routes to `192.168.1.2` and synchronized TCP+UDP captures.
- [x] Archive seven follow-up real Windows calls #2–#8 with **only OPNsense as IPv4 default**, all voice-connection failures despite Telegram connectivity: **14 correlated LAN/WAN TCP+UDP PCAPs**, 345 non-STUN reflector Hellos + 45 STUN originals all seen on WAN, 90 extra zero16 STUN fakes, **no captured inbound Telegram UDP**. After restoring other preferred gateway `192.168.3.140`, owner reports real calls connected; successful-route PCAP and identical in-app proxy conditions **not yet measured**. [Dated seven-call A/B evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md).
- [x] Preserve subsequent **16:16 October 2 Telegram Desktop WebRTC failure** from a separate private detailed call log with owner-reported OPNsense-only default and no app proxy: remote signaling/ICE candidate exchange works, correct-NIC reflector and TURN requests occur, **no confirmed ICE/DTLS secured media**, timeout at ~20 seconds; separate newer main log is not the same call. [Source-scoped sanitized evidence](verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md). No same-call PCAP or verified alternate successful media trace, so root cause/accepted gates unchanged.
- [x] Verify `telegram_voice` ON/interception of 60 current reflector Hellos in the October 1 control. These non-STUN packets were not transformed and no media established; the result is **not** `MEDIA_PASS`.

**Superseding owner test priority, October 2:** perform repeated experimental strategy qualification **in the existing TNAS Docker laboratory**, not by asking humans to make a real Telegram call for each candidate. The provider's Telegram DPI block is the owner-established premise; keep functioning Telegram TCP via external Squid parent unchanged. The operator reports that candidate `HELLO-FAKE-A1` has already been Applied in ordinary GUI Strategy, but **no wire profile/call outcome is yet known**. [Read and follow the complete campaign and preflight before experiment](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md). The fixed target remains `91.108.13.10:596`, current binary/engine pinned, TNAS `/32` through OPNsense and one new 15-second Docker test with simultaneous LAN/WAN IP captures.

### Stage 1 — reproduce a working UDP voice transport through OPNsense

- [x] Preserve owner's October 2 Docker-first decision and exact A1 GUI candidate **Applied-reported only**; [complete canonical plan](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md).
- [x] Replace multi-console, interactive-TNAS A1 procedure with one independently maintained OPNsense `sh` runner that invokes the **existing** owner-tested route guard and restricted SSH, verifies active A1/Voice/IPFW and pinned current Docker binary, owns two concurrent IP captures and one bounded 15-second fixed-reflector CLI invocation, cleans up and outputs one private `.tgz`. [Source](../tools/telegram-voice-lab/run-a1-opnsense.sh) · [campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md). Source and mocked test complete; live qualification still open.
- [ ] Verify generated A1/helper/IPFW/IPSET/routing baseline read-only; run one qualified **15-second pinned Docker reflector A1** on existing OPNsense path with WAN/LAN IP captures, peer stats/BWE/exit and honest `PROFILE_NOT_SELECTED` / `WIRE_OK` / `REFLECTOR_READY` / `MEDIA_PASS` distinctions.
- [ ] For any Docker media-positive candidate, repeat independent fixed-target fresh runs before a single bounded human real-client `CALL_PASS`; record every run's private PCAP hashes and bounded outcome in GitHub.

- [ ] Correlate existing September 22 positive CLI evidence if recoverable; otherwise choose one bounded source-guided experiment that resolves a specific remaining hypothesis for the *current* non-STUN reflector transport. Do not restart completed fragmentation-position sweeps by inertia.
- [ ] Freeze source/runtime/profile identity, endpoint, route, hook order and capture boundaries per experiment; preserve exact pre-test state and prove complete restoration.
- [ ] **Optional separate causal control, not the next screening task:** capture a successful Windows/Android call over the alternate `192.168.3.140` gateway with matching TCP+UDP/ICE and frozen application settings, *if* later needed to locate a path difference. Do not delay fixed-target Docker A1 or repeatedly request human calls as candidate screens.
- [ ] Repeat successful current-oracle `MEDIA_PASS` through OPNsense: both peers `Established`, stats and non-zero BWE on both, exit 0, and correlated UDP LAN/WAN packets. Missing replies without a fresh independent working control remain `NO_REPLY_UNKNOWN`, not a proven DPI diagnosis.

### Stage 2 — real Telegram client acceptance

- [ ] A remote Windows → Android P2P-disabled audible call **already occurred** on October 2, ahead of Stage 1 completion. Before marking `CALL_PASS`, explicitly verify sustained bidirectional UDP and sound in each direction; the supplied UDP captures contain **no Telegram UDP replies**. If needed, repeat a bounded call with simultaneous TCP/UDP metadata capture to identify the actual media route and distinguish fallback. Preserve the validated October 2 observation without treating it as Stage 2 completion.
- [ ] Repeat the positive case and preserve exact qualified strategy and scope for the eventual product.

### Stage 3 — integrate only proven Telegram Voice UDP into the plugin

- [ ] Make the proven UDP interception strategy, managed Telegram IPSET, firewall rule ownership/conflict prevention, start/stop/reconfigure/cleanup and reboot state part of `os-zapret2-restyle`.
- [ ] Persist the user's Voice setting in OPNsense configuration and expose it in the existing Settings GUI. Use a simple enable/disable control if one fixed strategy works reliably; only add parameter controls or a separate page when stages 1–2 establish a real need.
- [ ] Remove testbed address/interface/rule-number assumptions from production behavior; keep the temporary `tgcalls` lab outside the package. Verify lifecycle/restoration and restart/reboot persistence with appropriately selected owner-live tests.

**Not approved as product stages 4 or 5:** packaging/integrating Telegram TCP/TLS/proxy or SOCKS components, blanket router-console proxying, or end-to-end clean-install TCP/proxy delivery. **Separately,** OPNsense GUI-managed persistence and verified post-reboot recovery of lab Squid/PF/sing-box and the selected Voice-helper state **remain required lab work**, not stage-3 product scope. The owner explicitly opted for **manual** TNAS route repair after its reboot and manual Docker lab startup, not their automatic recovery.

Current [oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [protocol research](research/TELEGRAM_VOICE_UDP.md), [laboratory TCP/proxy/route recovery](architecture/TELEGRAM_TRAFFIC_POLICY.md), [current evidence](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md). `_4` remains an unpublished, paused historical candidate; do not merge its STUN-only fragment profile as the final product by inertia.

## Remaining regression / future backlog

These rows remain useful coverage or future product directions. They are **not** silently release debt for the completed stable `v0.5.0` release.

- [ ] cancellation/internal-failure containment regression
- [ ] circular lifecycle start/stop/TTL and stale-session recovery
- [ ] broader Diagnostics persistence/reload regression
- [ ] retention/cleanup boundary regression
- [ ] reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up as new evidence requires
- [ ] package/runtime version visibility follow-up
- [ ] RU/EN review beyond explicitly selected localization defects
- [ ] IPv6 Laboratory target support — requires a separate explicit architecture scope
- [ ] Additional BLOB repository GUI — wait for owner-supplied/approved technical contract

## Deferred research — do not reactivate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only for a concrete defect or explicit owner selection

## Current priority

**Stage 1 first: reproduce and repeat Telegram Voice UDP `MEDIA_PASS` through OPNsense with the current qualified reflector oracle.** Then achieve real remote Windows/Android `CALL_PASS`, and only after those gates integrate the proven UDP feature and persistent GUI control into the plugin (stage 3). Retain the working laboratory TCP/proxy configuration without adding it to product scope. Do not restart the completed fragmentation sweep or assume the retired alternate route works.

Release notes for the current stable release: [`releases/v0.5.0.md`](releases/v0.5.0.md).
