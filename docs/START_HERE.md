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
**Current handoff identity:** `v0.4.1_19` source candidate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=19` / `v0.4.1_19`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_18.pkg` / `v0.4.1_18`;
- `_18` testing-package SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- `_18` source merge/testing-tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- `_18` publication workflow run: `31889449879`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_N`: **no**.

Machine `_18` publication evidence: [`verification/evidence/testing-publications/v0.4.1_18.md`](verification/evidence/testing-publications/v0.4.1_18.md).

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

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_19` preserves the existing model-backed default/load/save source contract.

## `_18` owner-live follow-up — corrective selected

The owner installed published `_18` and supplied a live Russian-mode Laboratory screenshot.

Confirmed working:

- `Лаборатория стратегий`;
- `UDP порт (опционально)`;
- `Заблокированный домен / IP` is on one line.

The same screenshot selected `_19` because:

- the `_18` 12 px workaround made the blocked-domain label visibly too small;
- the owner rejected the resulting field alignment and requires domain / UDP / QUIC controls to use one explicit common x-position with normal typography;
- RU mode dropdown must show `Стандартный` / `Расширенный`, while EN remains `Standard` / `Extended`;
- add right-aligned `Режим:` / `Mode:` immediately before the mode selector;
- RU ordinary idle must show `ожидание`, EN remains `idle`;
- sidebar entries become EN `Strategy` / `Laboratory`, RU `Стратегия` / `Лаборатория`.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md).

## `_19` selected implementation

`_19` is a narrow Laboratory presentation/layout corrective package candidate:

- remove the 12 px blocked-domain label workaround and use normal UI typography;
- keep `Заблокированный домен / IP` on one line with an explicit fixed label/value-column contract;
- align domain input, Generic UDP input and Enable QUIC checkbox at one common value-column x-position;
- RU mode values: `Стандартный` / `Расширенный`; EN: `Standard` / `Extended`;
- right-aligned mode label: RU `Режим:` / EN `Mode:`;
- ordinary idle: RU `ожидание` / EN `idle`;
- navigation canonical names: `Strategy` / `Laboratory`, with deterministic RU presentation `Стратегия` / `Лаборатория` on the Laboratory page;
- no Strategy Lab search/runtime semantics are changed;
- previous circular-idle and Enable QUIC persistence source contracts remain guarded.

Source patch record: [`patches/v0.4.1_19.md`](patches/v0.4.1_19.md).

## Immediate acceptance after `_19` publication

1. verify RU normal typography and one-line blocked-domain label;
2. verify domain / UDP / QUIC controls are aligned;
3. verify `Режим:`, `Стандартный`, `Расширенный`, `Статус: ожидание`;
4. verify sidebar `Стратегия` / `Лаборатория`;
5. verify EN `Mode:`, `Standard`, `Extended`, `Status: idle`, `Strategy` / `Laboratory` and no RU leakage;
6. separately prove Enable QUIC OFF/default persistence across reload/revisit;
7. next product plan: add Laboratory target support for IP addresses as well as domains;
8. continue the remaining risk-selected backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
