# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-19
**Current handoff identity:** `v0.5.0_2` owner-live accepted; Telegram voice / UDP research complete, recommendation ready for owner review

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=2`;
- owner-live accepted testing corrective: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- testing source/tag target: `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- testing package SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- testing publication workflow: `31917806438`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository remains on `_1`; `_2` did **not** promote it.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

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

## Telegram voice / UDP research — conclusion ready

The owner-selected research is complete and recorded in [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

Current conclusion:

- modern Telegram calls use Telegram API signaling plus a separately negotiated WebRTC-based transport; STUN/TURN endpoint IP and port are supplied dynamically, and UDP P2P/reflector paths are supported;
- current upstream Zapret2 ships an official `50-stun4all` helper using native `--payload=stun` plus a 16-zero-byte fake with `repeats=2`;
- the technique is a well-founded baseline for stateful-DPI STUN interference, but Zapret2 itself does not claim it defeats stateless DPI or direct media/IP blocking;
- global UDP/443 drop is a QUIC fallback technique, not the recommended Telegram Voice default;
- Linux/OpenWrt can signature-filter STUN in the kernel, while FreeBSD `ipfw` cannot filter raw payload, so OPNsense must use a bounded interception design rather than copy `50-stun4all` literally;
- recommended first PoC: disable Telegram P2P for the test, verify the failed call's STUN destination with a WAN capture, then divert all UDP ports **only to plugin-managed Telegram IPv4 ranges** to the existing `dvtws2` socket and apply the official STUN baseline inside `dvtws2`;
- current Generic UDP Strategy Lab must not claim automatic Telegram-call success; if provider-specific tuning is later required, use an assisted real-call workflow rather than a synthetic UDP PASS.

No Telegram Voice product/source implementation is approved yet. The research recommendation must be owner-reviewed first.

## Immediate next action

Owner review of [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

If the owner accepts the recommendation, perform **Phase A live observation** on OPNsense/MTS-MGTS before source implementation: set Telegram P2P to Nobody/disabled for the test, reproduce a failed call, capture STUN destination IP/port and establish whether the failure occurs on Telegram-range STUN or later encrypted media.

Only if that evidence matches the research model should the next source patch implement the deliberately small Telegram-IP-scoped STUN PoC.

The previously selected Strategy Lab cancellation/internal-failure containment regression remains useful backlog work but is not the immediate task.
