# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-09-23
**Current handoff identity:** `v0.5.0_3` — standalone reflector fragmentation sweep is wire-qualified and silent; test fragmented fake + qualified reverse24 next

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

## Telegram voice / UDP — current laboratory task

**Current task: establish and repeat a call carrying bidirectional media through OPNsense in the rebuilt tgvoice laboratory.** The September 23 reverse position-24 run is now correlated with its CLI: the final planned standalone fragment position is locally wire-correct and restoration passed, but the call still failed. The standalone position sweep therefore closes without `MEDIA_PASS`. The earlier owner-reported success remains separate. Next is one bounded fragmented-fake + qualified reverse24 candidate; acceptance remains repeatable `MEDIA_PASS`, followed by a real Windows/Android call.

Read the [research](research/TELEGRAM_VOICE_UDP.md), [temporary laboratory architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [September 21 ordered test evidence](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md), [earlier September 22 successful-call observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md), [post-reboot reverse position-8 repeat](verification/evidence/2026-09-22-telegram-voice-reverse8-postreboot.md), [reverse position-32 result](verification/evidence/2026-09-23-telegram-voice-reverse32.md), and [reverse position-16 result](verification/evidence/2026-09-23-telegram-voice-reverse16.md), and [reverse position-24 result / next family](verification/evidence/2026-09-23-telegram-voice-reverse24.md).

Current facts:

- The owner explicitly retired `192.168.1.140`: it is no longer a working route. Do not use it as a current control, require a detour through it, or assume restoration must return to it. The 2026-09-05 success remains historical evidence only.
- The owner reports that Telegram changed voice transport; this motivated rebuilding tgvoice. The research records the verified upstream networking/MTProto changes and their flags. It does not infer a universal client/server rollout date from source commits.
- The active tgcalls source is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; `/results/tgcalls_cli` SHA-256 is `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. Its local P2P gate passed on 2026-09-20. The older binary is retired.
- The current command uses engine `13.0.0` on both peers with no custom-parameter override. These are engine versions, not Telegram application versions. Windows/Android transport parity still needs evidence.
- The no-desynchronization OPNsense baseline sent 60 valid 40-byte Reflector Hellos through NAT, with zero replies.
- The corrected post-NAT runner `tgvoice_ipfrag8_postnat_v2.py` (`postnat-nofrag-v2`) then emitted 60 complete ordered fragment pairs with valid reassembled UDP checksums and no unfragmented originals. Zero packets returned from the reflector; both peers stayed `Reconnecting`, BWE was zero, and the 15-second call exited 1.
- The September 21 ordered run is **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS` in that run**. This does not classify the later owner-reported successful call. No currently working independent control is established.
- Reverse position-8 syntax/source validation is complete. The September 22 archive records a loaded profile, empty LAN/WAN captures filtered to `91.108.13.10`, zero hits on rule 18990 and `RESTORE_OK`; it contains no companion call log.
- The owner confirmed **the earlier call established and routing was correct during the call**, then identified the tool as the same `tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15` command. Its positive summary remains unavailable, so strategy/media attribution for that observation is still open.
- After reboot, TNAS restored the endpoint route through `192.168.1.2` on `ovs_eth1` with source `192.168.1.100`; the container is running with `network=host`. The September 22 21:04:34–21:04:49 UTC CLI run used the same binary hash. Its capture contains 60 complete reverse pairs, all checksums valid and payloads matched to the primary LAN flow, no unfragmented originals and zero reflector replies. Both peers stayed `Reconnecting`, BWE was zero and exit was 1: **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS` for this repeat**.
- Normal rules 19000/19001 were present before and after this post-reboot run. Temporary 18990/990 were removed, listener 989 retained, and IPFW/PFIL/socket snapshots restored exactly.
- The September 23 07:06:36–07:06:51 UTC reverse position-32 run used the same route, binary and runtime. It emitted 60 complete reverse pairs: IP length 36 at offset 32, then length 52 at offset 0/MF=1. All checksums and primary-LAN payload matches passed; no original duplicates or replies appeared. Both peers remained `Reconnecting`, BWE was zero, exit was 1 and restoration was exact: **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS`**. The short-UDP guard was not exercised by these 40-byte Hellos.
- The September 23 07:29:23–07:29:38 UTC guarded reverse position-16 run used the same route, binary and runtime. Rule 18990 counted 60/4080; WAN contains 60 complete reverse pairs with IP length 52 at offset 16 followed by length 36 at offset 0/MF=1. All IPv4/reassembled UDP checksums and primary-LAN payload matches passed; no unfragmented originals or replies appeared. Both peers remained `Reconnecting`, BWE was zero, exit was 1 and restoration was exact: **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS`**. All intercepted payloads were 40 bytes, so the <=8-byte guard was not exercised.
- The September 23 12:45:54–12:46:09 UTC guarded reverse position-24 run emitted 60 complete reverse pairs with two equal IP length-44 fragments per Hello, offset 24/MF=0 first then offset 0/MF=1. IPv4 and reassembled UDP checksums were valid, all 60 primary-LAN payloads matched, no unfragmented originals or reflector replies appeared, both peers stayed `Reconnecting`, BWE was zero, exit was 1 and restoration was exact: **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS`**. This closes standalone fragment-position widening for the current reflector epoch.
- The next prepared runner is `tgvoice_fakefrag8_reverse24_postnat_v1.py`, revision `postnat-fakefrag8-reverse24-v1`, SHA-256 `c4ee47779d778f50b04e48ffe744f5d098d3fb32863133b7d3a8d7ed6c633d24`. It adds one 40-byte zero fake with bad UDP checksum and random IPv4 ID, fragmented ordered at UDP position 8, before the already-qualified real reverse24 serialization.
- Docker remains on the existing `host` network. Tests already work from the TNAS and OPNsense consoles; optional SSH automation is not a prerequisite for the next experiment.
- The runtime is owner-reported Zapret2 `v1.0.5.2`; exact binary/Lua identities and the limits of restoration are in the latest evidence. The older v1.0.4 pin is historical.

## Immediate next action

1. Run `tgvoice_fakefrag8_reverse24_postnat_v1.py --after-nat` on OPNsense, wait for `READY: FAKEFRAG8 + REVERSE24 AFTER NAT [postnat-fakefrag8-reverse24-v1]`, then run the same 15-second fixed-reflector CLI on TNAS with a distinct `fakefrag8-reverse24` console/RTC prefix.
2. Keep endpoint `91.108.13.10:596`, route through `192.168.1.2`, current tgcalls hash, engine `13.0.0`, runtime hashes and the real reverse24 path fixed. The only new attack component is one checksum-invalid 40-byte zero fake fragmented ordered at position 8 before each real Hello.
3. Qualify four WAN fragments per intercepted Hello: fake length 28 offset 0/MF=1, fake length 60 offset 8/MF=0, then real length 44 offset 24/MF=0 and real length 44 offset 0/MF=1. The fake pair must have an intentionally invalid reassembled UDP checksum and a different IPv4 ID from the real pair; the real pair must remain checksum-valid and payload-exact. Rule 18990 should still count only the 60 intercepted originals.
4. Preserve the earlier successful-call report separately. A fake+fragment success must be repeated with fresh flow/process state before moving to the real Windows/Android gate. A silent but wire-correct result remains `NO_REPLY_UNKNOWN` without a fresh independent control.
5. Reach and repeat `MEDIA_PASS`, then verify a remote P2P-disabled Windows/Android call with two-way sound and sustained bidirectional UDP (`CALL_PASS`).

The laboratory remains temporary console tooling. Keep package identity `0.5.0_3`, Generic UDP and production plugin code unchanged; `_4` remains unpublished and paused. No GUI/permanent laboratory subsystem, all-Internet UDP interception, global UDP/443 drop or bundled tgcalls/Linux belongs to this task.
