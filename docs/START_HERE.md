# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules (`DOC-*`):** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules (`DEV-*`):** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules (`CHAT-*`):** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules (`GH-*`):** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-15
**Current handoff identity:** `v0.4.1_23` source candidate; `v0.4.1_22` remains the published testing candidate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=23` / `v0.4.1_23`;
- current packaged revision: `PLUGIN_REVISION=22` / `v0.4.1_22`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_22.pkg` / `v0.4.1_22`;
- `_22` testing-package SHA-256: `07a82529a824b84894541d59c1eabddd56500b5efad9205f6bd9e9e6b4f811d9`;
- `_22` source merge/testing-tag target: `71baa9d0e7cd3e04535ff9b9ba87aefe8f4e8cfe`;
- `_22` publication workflow run: `31903303820`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_22`: **no**.

Machine `_22` publication evidence: [`verification/evidence/testing-publications/v0.4.1_22.md`](verification/evidence/testing-publications/v0.4.1_22.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, QUIC-OFF execution, Generic UDP, already-accessible-target, Settings Apply, or `_21` Laboratory presentation work without fresh contradictory evidence.

Accepted owner-live/product facts include:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, all three current UDP candidates and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: OFF suppresses QUIC candidate execution while independent Generic UDP remains active;
- visible Stage-90 restoration on the tested flows;
- already-accessible-target behavior is complete by owner confirmation;
- Settings Apply validation/guards and post-Apply service-state correctness are complete by owner confirmation;
- `_21` Laboratory outer frame/perimeter matches normal OPNsense presentation by owner confirmation;
- `_21` Russian `Стратегия` / `Лаборатория` remains localized across Laboratory ↔ Strategy navigation;
- the current Strategy Lab / Laboratory Russian-presentation task is closed by owner instruction; future concrete localization regressions are new defects.

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_22` preserves the existing model-backed default/load/save source contract.

Owner-live `_21` presentation evidence: [`verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md).

## `_20` owner-live UI follow-up — historical rejected perimeter/navigation

The owner installed `_20` and supplied direct screenshots of Laboratory, Strategy and a native OPNsense page.

Confirmed then:

- the `_20` Laboratory page lost the normal OPNsense outer content perimeter/frame;
- Strategy and the native OPNsense comparison page retained the normal platform spacing;
- on Laboratory with Russian OPNsense language the submenu was `Стратегия` / `Лаборатория`;
- after navigating to Strategy the same submenu reverted to English `Strategy` / `Laboratory`.

Root cause was bounded to presentation code: `_20` neutralized `.page-content-main` inside `diagnostics.volt`, affecting the platform-owned wrapper, while deterministic submenu localization existed only on Laboratory and not on Strategy.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md).

## `_21` implementation / acceptance status

`_21` is source-merged, published and owner-live accepted for the selected presentation scope:

- removes the redundant Laboratory page wrapper and all Laboratory `.page-content-main` spacing overrides;
- renders Laboratory content boxes directly inside the platform-owned OPNsense page frame, matching the Strategy/native page structure rather than styling away the platform perimeter;
- preserves the accepted shared `25%` Diagnostics field grid and `Режим:` / `Mode:` typography synchronization;
- makes Strategy apply the same active-language submenu labels as Laboratory, so Russian stays `Стратегия` / `Лаборатория` on both pages and English stays `Strategy` / `Laboratory`;
- keeps Strategy Lab runtime/search, Generic UDP, QUIC, circular and settings semantics unchanged;
- owner-live verification accepted the native perimeter/grid and Russian cross-page menu persistence.

Source patch record: [`patches/v0.4.1_21.md`](patches/v0.4.1_21.md).

## `_22` implementation / delivery status — Laboratory IPv4 targets

`_22` is source-merged and persistently published for owner-live verification. Exact source head qualification passed complete project CI and FreeBSD-15 package qualification before source merge; the source was squash-merged as `71baa9d0e7cd3e04535ff9b9ba87aefe8f4e8cfe` and that exact commit is the testing tag target.

Implemented contract:

1. the Laboratory target accepts either a normal domain or a canonical IPv4 address; IPv6 target input is intentionally deferred;
2. IPv4 targets expose a conditional/optional `Host / SNI` service identity, persisted separately from destination identity;
3. Stage 00 records `target_type=ip`; with Host/SNI the endpoint identity is the hostname while the fixed destination remains the entered IPv4;
4. Stage 40 skips DNS for IPv4 and performs a real TLS 1.3 request pinned to the entered IP; plain TCP connectivity is never accepted as TLS/DPI-bypass proof;
5. the search epoch keeps `endpoint=<service hostname>` and `selected_ip=<entered IPv4>` distinct when Host/SNI is present;
6. Stage-50/60 IP candidates are destination-IP/firewall scoped and do not add hostlist target binding; Model-C attribution and lifecycle ownership remain unchanged;
7. TLS 1.3, TLS 1.2 and HTTP candidate probes use protocol-aware requests against the fixed IP; QUIC uses Host/SNI when available and bare-IP QUIC is unsupported rather than falsely successful;
8. Generic UDP remains direct-IP and does not require Host/SNI;
9. final IP recommendations use the existing `--ipset-ip=<target>` selector and normal exact three-pass profile replay;
10. temporary circular browser validation remains domain-only;
11. Model C, budgets, source-port attribution, lifecycle locking, cleanup and exact Stage-90 restoration remain unchanged.

Published testing artifact:

- tag/release: `v0.4.1_22`;
- package: `os-zapret2-restyle-0.4.1_22.pkg`;
- SHA-256: `07a82529a824b84894541d59c1eabddd56500b5efad9205f6bd9e9e6b4f811d9`;
- source/tag target: `71baa9d0e7cd3e04535ff9b9ba87aefe8f4e8cfe`;
- publication workflow run: `31903303820`;
- stable Pages/pkg repository promoted: no.

The publisher completed package build/release verification and machine-evidence creation. Its final automatic PR-creation step was blocked by repository GitHub Actions token policy; the mandatory publication-record PR was therefore opened manually from the workflow-created `publication-record/v0.4.1_22` branch, with no product/package source change.

Source patch record: [`patches/v0.4.1_22.md`](patches/v0.4.1_22.md).

## Immediate live verification boundary

Install `v0.4.1_22` and verify only the newly selected product boundary:

1. run one ordinary domain to confirm the pre-existing domain path did not regress;
2. run a canonical IPv4 target without Host/SNI and confirm no plain TCP result is reported as successful TLS bypass;
3. run an IPv4 target plus its real Host/SNI and confirm the destination remains pinned to the entered IP while TLS/HTTP identity uses the hostname;
4. when a working result exists, confirm the complete recommended profile contains `--ipset-ip=<entered IPv4>` and exact profile replay succeeds;
5. in Extended mode, confirm Generic UDP works directly against an IPv4 target without requiring Host/SNI;
6. if QUIC is enabled, use Host/SNI for an IP target and confirm bare-IP QUIC cannot create a false PASS;
7. confirm Stage 90 restores the exact initial Zapret2 state and leaves no temporary Strategy Lab process/rule residue.

Enable QUIC OFF/default persistence across reload/revisit remains a separate live row. Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
