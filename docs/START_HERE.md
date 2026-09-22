# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-09-22
**Current handoff identity:** `v0.5.0_3` — rebuilt Telegram Voice lab; ordered post-NAT fragmentation is `WIRE_OK / NO_REPLY_UNKNOWN`; successful media call is the current task

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

**Current task: establish a call with bidirectional media in the rebuilt laboratory through OPNsense.** The task is complete only after repeatable `MEDIA_PASS`, followed by a real Windows/Android call for product acceptance. Correct outbound packets alone do not complete it.

Read the [research](research/TELEGRAM_VOICE_UDP.md), [temporary laboratory architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), and [2026-09-21 test evidence](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md).

Current facts:

- The owner explicitly retired `192.168.1.140`: it is no longer a working route. Do not use it as a current control, require a detour through it, or assume restoration must return to it. The 2026-09-05 success remains historical evidence only.
- The owner reports that Telegram changed voice transport; this motivated rebuilding tgvoice. The research records the verified upstream networking/MTProto changes and their flags. It does not infer a universal client/server rollout date from source commits.
- The active tgcalls source is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; `/results/tgcalls_cli` SHA-256 is `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. Its local P2P gate passed on 2026-09-20. The older binary is retired.
- The current command uses engine `13.0.0` on both peers with no custom-parameter override. These are engine versions, not Telegram application versions. Windows/Android transport parity still needs evidence.
- The no-desynchronization OPNsense baseline sent 60 valid 40-byte Reflector Hellos through NAT, with zero replies.
- The corrected post-NAT runner `tgvoice_ipfrag8_postnat_v2.py` (`postnat-nofrag-v2`) then emitted 60 complete ordered fragment pairs with valid reassembled UDP checksums and no unfragmented originals. Zero packets returned from the reflector; both peers stayed `Reconnecting`, BWE was zero, and the 15-second call exited 1.
- Latest classification: **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS`**. No currently working independent control is established.
- Docker remains on the existing `host` network. Tests already work from the TNAS and OPNsense consoles; optional SSH automation is not a prerequisite for the next experiment.
- The runtime is owner-reported Zapret2 `v1.0.5.2`; exact binary/Lua identities and the limits of restoration are in the latest evidence. The older v1.0.4 pin is historical.

## Immediate next action

1. Keep the qualified binary, engine/configuration and `91.108.13.10:596` fixed. Record the actual TNAS route through OPNsense `192.168.1.2`; if a temporary exact `/32` is needed, restore the measured pre-test route afterward, with no hardcoded `192.168.1.140` assumption.
2. Use the corrected post-NAT interception and fragment exclusion as the starting point. Validate the installed Lua syntax for one isolated reverse-order position-8 candidate; then test position 32, followed by 16/24 only as evidence warrants. Earlier malformed runs are not negative network results for this setup.
3. For each fresh 15-second process, retain LAN/WAN evidence including non-initial fragments, counters, checksums, replies, both peer states, BWE, exit status and exact cleanup. Keep the old and revised runner filenames distinct.
4. Track transport parity explicitly. Any engine/custom-parameter comparison is a separate experiment based on the source findings; do not combine it with a fragment change or presume it fixes the unanswered initial Hello. Changing the endpoint starts a separate comparison epoch.
5. Repeat any candidate reaching `MEDIA_PASS`; then verify a remote P2P-disabled Windows/Android call with two-way sound and sustained bidirectional UDP (`CALL_PASS`). A fresh independent control would improve causal attribution, but absence of the retired route does not suspend the current task.

The laboratory remains temporary console tooling. Keep package identity `0.5.0_3`, Generic UDP and production plugin code unchanged; `_4` remains unpublished and paused. No GUI/permanent laboratory subsystem, all-Internet UDP interception, global UDP/443 drop or bundled tgcalls/Linux belongs to this task.
