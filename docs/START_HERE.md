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
**Current handoff identity:** `v0.4.1_21` source candidate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=21` / `v0.4.1_21`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_20.pkg` / `v0.4.1_20`;
- `_20` testing-package SHA-256: `5d5fae0a79054ad807a92ca7804d5984d63782927c667962b6395d48627ab64a`;
- `_20` source merge/testing-tag target: `d732965c143563352e18ac58c209aeb30a6d4feb`;
- `_20` publication workflow run: `31896330680`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_N`: **no**.

Machine `_20` publication evidence: [`verification/evidence/testing-publications/v0.4.1_20.md`](verification/evidence/testing-publications/v0.4.1_20.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, QUIC-OFF execution, Generic UDP, already-accessible-target, or Settings Apply work without fresh contradictory evidence.

Accepted owner-live/product facts include:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, all three current UDP candidates and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: OFF suppresses QUIC candidate execution while independent Generic UDP remains active;
- visible Stage-90 restoration on the tested flows;
- already-accessible-target behavior is complete by owner confirmation;
- Settings Apply validation/guards and post-Apply service-state correctness are complete by owner confirmation.

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_21` preserves the existing model-backed default/load/save source contract.

## `_20` owner-live UI follow-up — rejected perimeter/navigation

The owner installed `_20` and supplied direct screenshots of Laboratory, Strategy and a native OPNsense page.

Confirmed:

- the `_20` Laboratory page has lost the normal OPNsense outer content perimeter/frame;
- Strategy and the native OPNsense comparison page retain that normal platform spacing;
- on Laboratory with Russian OPNsense language the submenu is `Стратегия` / `Лаборатория`;
- after navigating to Strategy the same submenu reverts to English `Strategy` / `Laboratory`.

Root cause is bounded to presentation code: `_20` neutralizes `.page-content-main` globally inside `diagnostics.volt`, affecting the platform-owned wrapper, while deterministic submenu localization exists only on Laboratory and not on Strategy.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md).

## `_21` source implementation

Current `_21` candidate:

- removes the redundant Laboratory page wrapper and all Laboratory `.page-content-main` spacing overrides;
- renders Laboratory content boxes directly inside the platform-owned OPNsense page frame, matching the Strategy/native page structure rather than styling away the platform perimeter;
- preserves the accepted shared `25%` Diagnostics field grid and `Режим:` / `Mode:` typography synchronization;
- makes Strategy apply the same active-language submenu labels as Laboratory, so Russian stays `Стратегия` / `Лаборатория` on both pages and English stays `Strategy` / `Laboratory`;
- keeps Strategy Lab runtime/search, Generic UDP, QUIC, circular and settings semantics unchanged.

Source patch record: [`patches/v0.4.1_21.md`](patches/v0.4.1_21.md).

## Immediate delivery / verification boundary

Before `_21` is complete:

1. focused Laboratory native-frame/localization/persistence regression;
2. applicable complete project + Strategy Lab corrective matrix;
3. FreeBSD-15 package build/inspection qualification;
4. exact latest-head source merge;
5. persistent `v0.4.1_21` testing publication and bounded publication-record reconciliation.

After `_21` install:

1. visually confirm Laboratory has the same normal outer OPNsense perimeter as Strategy/native pages;
2. with Russian OPNsense language, switch Laboratory → Strategy → Laboratory and confirm the submenu stays `Стратегия` / `Лаборатория`;
3. quickly confirm the accepted field grid and `Режим:` typography did not regress;
4. no Strategy Lab execution rerun is required for this UI-only correction;
5. separately prove Enable QUIC OFF/default persistence across reload/revisit;
6. after `_21` UI acceptance, next engineering plan: add Laboratory target support for IP addresses as well as domains;
7. continue the remaining risk-selected backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
