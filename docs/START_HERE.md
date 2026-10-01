# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-10-01
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

Product integration must own Telegram UDP interception, managed Telegram IPSET, proven Zapret2 strategy, restart/stop, conflict-safe firewall rule ownership, and reboot restoration. Use no fixed testbed addresses or hard-coded rule/interface identities. If one fixed strategy works reliably, add only an enable/disable switch to the existing Settings GUI; multiple modes/parameters or a separate page require experimental evidence. The current `/var/run` request marker is temporary PoC state, not the final persistent implementation. **Do not install a local ad-hoc boot hook.**

**A separate, reboot-persistent three-origin laboratory is an explicit owner requirement.** Preserve LAN, OPNsense router-local applications/shell and SOCKS5 Telegram traffic separation: TCP/TLS must reach the experimental Squid/sing-box/PF → external parent path as applicable; UDP must use the selected Zapret2 voice interception; TNAS voice tests route through OPNsense. After OPNsense and TNAS reboots the lab must recover the same selected functioning state, not merely retain files or rely on manual recovery. Prefer verified native OPNsense settings/GUI for the lab; only where GUI is insufficient select a verified supported alternative. Existing LAN/SOCKS TCP success is retained, but router-origin Telegram selection, SOCKS UDP, full service/config regeneration, Voice-helper ON recovery and TNAS host routes are not yet qualified after reboot. [The lab contract and recovery runbook](architecture/TELEGRAM_TRAFFIC_POLICY.md) owns these obligations.

**This does not enlarge the plugin product scope.** Squid, sing-box, PF proxy redirects, external parent and TNAS lab routes remain outside the three approved product stages. Plugin source/GUI/lifecycle changes occur **only through GitHub** branch/PR/CI/merge; laboratory settings are administered independently through native OPNsense facilities wherever possible. No blanket proxy for every console process is required; the router-local objective concerns Telegram-specific lab traffic. No final TCP architecture or clean-install TCP delivery stages 4–5 are approved. The voice test controller/companion stays outside the package.

## Verified evidence and limitations

- The historical September 5 `MEDIA_PASS` used the old binary and now-retired `192.168.1.140` route, **not** OPNsense; do not restore that route as a control.
- The owner reported an established reflector CLI call through OPNsense on September 22. Its positive CLI output and exact matching strategy/profile/flow are not yet correlated. Keep the positive observation without declaring reverse8 proven.
- Existing ordered8, reverse8/16/24/32 and fakefrag8+reverse24 local wire experiments emitted their documented correct packets but did not deliver a correlated current `MEDIA_PASS`. Do not repeat the completed fragment sweep by inertia. The fakefrag8+original run had a separate local PF real-packet loss; tee changed ordering.
- The latest October 1 ON-helper control intercepted 60 Telegram UDP packets and sent 60 valid 40-byte **non-STUN** Reflector Hellos through the WAN with zero observed replies. Both peers stayed `Reconnecting`, BWE was zero, exit 1. The current STUN-only `stun-zero-fake-repeats-2` helper does not modify that Hello; ON/interception is not voice success.
- October 1 LAN HTTPS and SOCKS5 TCP/443 via Squid and the external parent have passed. Additional owner verification on October 1 again confirmed transparent TNAS HTTPS `HTTP=200` and Squid `FIRSTUP_PARENT`. These are **retained lab facts**, not new plugin requirements or proof of UDP voice.

Evidence: [September 22 positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md), [September 23–October 1 results](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [current media oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [current laboratory proxy and route recovery](architecture/TELEGRAM_TRAFFIC_POLICY.md), and [protocol research](research/TELEGRAM_VOICE_UDP.md).

## Immediate next action — approved stage 1 only

Recover any existing positive CLI evidence if available; otherwise run one bounded, source-guided test addressing a specific unresolved hypothesis against the *current* non-STUN Reflector Hello and qualified tgcalls binary, with fixed reflector/route and correlated profile, hooks, counters, LAN/WAN captures, peer states and exit status. Do not conflate the historical success with later failures or claim provider DPI attribution from WAN silence without an independent working control. Preserve the already-working TCP laboratory path unchanged and independently track its required post-reboot acceptance in the lab runbook; neither manually re-enabling a helper nor restoring a route after reboot is acceptance. Repeat a genuine `MEDIA_PASS` before proceeding to real-client `CALL_PASS` and only then product integration.

The three approved stages are tracked in [ROADMAP](ROADMAP.md). Package identity stays `VERSION=0.5.0`, `PLUGIN_REVISION=3`; unpublished `_4` remains paused pending evidence. This documentation-only update changes no source, running appliance, testing package or release.
