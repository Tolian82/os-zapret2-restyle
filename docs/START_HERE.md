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
**Current handoff identity:** published testing package `v0.4.1_18`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current packaged source revision: `PLUGIN_REVISION=18` / `v0.4.1_18`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_18.pkg` / `v0.4.1_18`;
- testing-package SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- source merge/testing-tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- publication workflow run: `31889449879`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_N`: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_18.md`](verification/evidence/testing-publications/v0.4.1_18.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, QUIC-OFF execution, or Generic UDP baseline work without fresh contradictory evidence.

Accepted owner-live evidence includes:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, all three current UDP candidates and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: OFF suppresses QUIC candidate execution while independent Generic UDP remains active;
- visible Stage-90 restoration on the tested flows.

Durable predecessor evidence:

- [`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md)
- [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md)

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_18` preserves the regression guard for the existing model-backed default/load/save contract.

## `_17` live RU follow-up — partial acceptance, corrective selected

The owner installed published `_17` and supplied live Russian-mode Diagnostics screenshots.

Confirmed working on the tested screen:

- `Тестирование соединения с доменом`, HTTPS guidance and `Проверка`;
- `Заблокированный домен / IP`, `Запуск`, `Включить QUIC`;
- translated result/stage labels including `Полный профиль Стратегий Трафика`;
- circular idle ordinary presentation is human text (`Статус: ОЖИДАНИЕ`, `Состояние: ОЖИДАНИЕ`) rather than raw JSON.

The same screenshots exposed the corrective boundary closed in `_18` source:

1. `Strategy Lab` remained untranslated;
2. `Generic UDP (optional)` remained untranslated;
3. `Заблокированный домен / IP` wrapped to two lines and the owner requested a small left shift shared by the domain input, Generic UDP value control and Enable QUIC control.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md).

## `_18` published corrective

Published `_18` contains the narrow Strategy Lab presentation/layout corrective:

- `Strategy Lab` -> RU `Лаборатория стратегий`;
- `Generic UDP (optional)` -> RU `UDP порт (опционально)`;
- EN explicitly remains `Strategy Lab` / `Generic UDP (optional)`;
- domain, Generic UDP and Enable QUIC value controls share one aligned column shifted slightly left from `_17`;
- RU `Заблокированный домен / IP` is kept on one line with a bounded label-column contract;
- no Strategy Lab search/runtime semantics were changed;
- focused regression coverage preserves prior RU/EN, circular idle and Enable QUIC persistence source contracts;
- latest-head CI, complete corrective matrix and FreeBSD-15 package qualification passed before exact-head source merge;
- persistent testing package/tag were published and verified from the candidate-defining source merge above.

Source patch record: [`patches/v0.4.1_18.md`](patches/v0.4.1_18.md).

## Immediate owner-live acceptance

1. install `v0.4.1_18`;
2. verify Russian `Лаборатория стратегий` and `UDP порт (опционально)`;
3. verify `Заблокированный домен / IP` is one line;
4. verify domain input, UDP port input and Enable QUIC checkbox are vertically aligned at the same new left position;
5. verify the same screen in English mode and confirm no RU/EN leakage;
6. separately prove Enable QUIC OFF/default persistence across reload/revisit;
7. continue the risk-selected backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
