# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-09-05
**Current handoff identity:** `v0.5.0_3` — fixed-reflector control `MEDIA_PASS`; host-only exact-route/OPNsense-console baseline next

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

Installed Zapret2 runtime pin: [`verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

Phase C companion build/runtime evidence: [`verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md`](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md).

Fixed-reflector control and host-topology evidence: [`verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md).

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

## Telegram voice / UDP — measured state and temporary Phase C laboratory

Read the current [research](research/TELEGRAM_VOICE_UDP.md) and [temporary emulator/oracle architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md) before further Telegram Voice work.

Established live facts:

- Phase A/B and the failed STUN zero-fake provider result remain unchanged;
- the pinned companion binary remains SHA-256 `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a`;
- on 2026-09-05 fixed current endpoint `91.108.13.10:596` passed a fresh 15-second real-reflector run: both peers established, 15 bitrate records per side, non-zero BWE, no errors, exit 0;
- this is exact-endpoint control `MEDIA_PASS`; the run used TNAS `192.168.1.100` through ordinary gateway `192.168.1.140`, so it did not traverse OPNsense;
- the owner requires the existing TOS/Docker network named `host` and no other Docker network;
- Docker host mode gives the container no independent IP or MAC. DHCP can identify only the TNAS host MAC; it cannot issue a separate `192.168.1.239` lease to this container;
- pfSense DHCP may assign routes by the visible TNAS MAC, but those routes belong to the TNAS host namespace and affect every host-network workload that uses the same destination;
- the laboratory therefore requires an endpoint-specific reflector `/32` route via OPNsense `192.168.1.2`, supplied either by the owner-controlled DHCP policy or by a temporary explicit route transaction; the TNAS default gateway is not changed and restoration is proved;
- repeated tests are launched from the OPNsense console over temporary key-only SSH to TNAS, invoking `docker exec tgvoice-lab ...`;
- the Telegram Voice laboratory is temporary research tooling only: no GUI, permanent backend/API/configd surface, daemon or package-owned subsystem;
- the existing Generic UDP Strategy Lab and permanent plugin code remain unchanged.

The remote `_4` fragmentation branch remains unpublished and paused.

## Immediate next action

1. From OPNsense, establish temporary key-only SSH command execution on TNAS `192.168.1.100`.
2. Record `ip route get 91.108.13.10` on TNAS and require the known control route through `192.168.1.140`.
3. Add only `91.108.13.10/32 via 192.168.1.2` on TNAS and require `ip route get` to show that gateway.
4. From the OPNsense console, start a fresh `docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15` while OPNsense captures LAN/WAN traffic and counters.
5. Remove only the owned `/32` route and prove restoration through `192.168.1.140`; restoration failure is `RESTORE_FAILED`.
6. Only after the no-desynchronization baseline, use temporary non-packaged console scripts for the bounded candidate matrix.
7. Remove the temporary route/SSH/scripts when research closes.

Do not modify the GUI or permanent Strategy Lab implementation. Do not publish `_4`, intercept all Internet UDP, globally drop UDP/443, or bundle `tgcalls`/Linux into the OPNsense package.

