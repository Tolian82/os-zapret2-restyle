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
**Current handoff identity:** `v0.4.1_21` published / owner-live UI accepted

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current packaged revision: `PLUGIN_REVISION=21` / `v0.4.1_21`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_21.pkg` / `v0.4.1_21`;
- `_21` testing-package SHA-256: `17d74cfe804bdcc3984961185d0b29ef1c15329b6079dcf1ea2417ea16e3848a`;
- `_21` source merge/testing-tag target: `02cbd27d3c6a533bdaa9b44bf90e9510c8a4af29`;
- `_21` publication workflow run: `31898795618`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_N`: **no**.

Machine `_21` publication evidence: [`verification/evidence/testing-publications/v0.4.1_21.md`](verification/evidence/testing-publications/v0.4.1_21.md).

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

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_21` preserves the existing model-backed default/load/save source contract.

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
- focused project validation and FreeBSD-15 package qualification passed before source merge;
- source was squash-merged as `02cbd27d3c6a533bdaa9b44bf90e9510c8a4af29`;
- testing package `os-zapret2-restyle-0.4.1_21.pkg` was published and verified with SHA-256 `17d74cfe804bdcc3984961185d0b29ef1c15329b6079dcf1ea2417ea16e3848a`;
- owner-live verification accepted the native perimeter/grid and Russian cross-page menu persistence.

Source patch record: [`patches/v0.4.1_21.md`](patches/v0.4.1_21.md).

## Immediate engineering boundary — Laboratory IP targets

The next selected product task is to let Laboratory accept and test an IP address as well as a domain.

The architecture audit has established that this is feasible but must **not** be implemented as a validator-only change:

1. current PHP and shell input boundaries reject IP literals and must classify `domain` versus canonical IPv4;
2. Stage-00/40 state, IPv4 search-epoch binding, firewall attribution and final `--ipset-ip=<target>` profile generation already contain useful IP scaffolding;
3. Generic UDP can use a fixed IPv4 target directly;
4. current TLS candidate code must not be unlocked unchanged because an IPv4 endpoint currently falls back to plain TCP-connect evidence, which is insufficient for a truthful TLS/DPI-bypass PASS;
5. web/TLS/QUIC IP testing needs destination IP separated from service hostname/SNI and certificate identity; the existing request layer already supports fixed-IP + hostname probing via curl `--resolve` and OpenSSL SNI/hostname verification;
6. initial implementation should be IPv4-first because current search-epoch canonicalization is IPv4-specific;
7. add a conditional/optional Host/SNI service identity for IP targets and report semantically unsupported bare-IP protocol branches as skipped/unsupported rather than false PASS;
8. keep Model C, lifecycle, budgets, cleanup/restoration and deterministic result attribution unchanged;
9. separately prove Enable QUIC OFF/default persistence across reload/revisit when that backlog row is selected.

Detailed audit/owner handoff: [`verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md).

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
