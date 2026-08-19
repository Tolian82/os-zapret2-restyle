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
**Current handoff identity:** `v0.5.0_2` owner-live accepted; Telegram voice / UDP research selected by owner

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

## Owner-selected current research

The owner has selected **Telegram voice / UDP DPI-bypass research** as the new current task, superseding the previously selected cancellation/internal-failure regression as the immediate next action.

Task authority and starting evidence: [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md).

Scope:

- ordinary Telegram TCP/service reachability is already routed through an external proxy and is not the target of this work;
- determine how Telegram call setup/media uses UDP and what provider DPI actually blocks;
- investigate STUN-focused Zapret2-native desynchronization, UDP/443 suppression/fallback and other current mechanisms;
- establish what is universal versus provider-specific;
- decide whether the plugin needs a static helper, a new Strategy Lab service-aware search branch, a Generic UDP extension, a narrowly scoped firewall fallback, or another bounded design;
- produce a documented recommendation and live-verification plan before implementation is selected.

The owner-provided `youtubeUnblock`, `zapret-openwrt`, Zapret2 repository/manual/discussions links and the supplied STUN/UDP-443 examples are recorded in the research document and must be investigated rather than treated as already-approved presets.

## Immediate next action

Perform the research defined in [`research/TELEGRAM_VOICE_UDP.md`](research/TELEGRAM_VOICE_UDP.md): inspect the supplied projects/current Zapret2 source/manual/discussions and additional protocol/operator evidence, then document the Telegram voice traffic model, workaround mechanics, provider-dependence, recommended OPNsense integration and a reliable live test method.

Do **not** implement a Telegram voice source change or declare a universal strategy until that evidence is complete and the resulting architecture direction is owner-reviewed.

The previously selected Strategy Lab cancellation/internal-failure containment regression remains useful backlog work but is no longer the immediate task.
