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
**Current handoff identity:** `v0.4.1_18` source candidate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=18` / `v0.4.1_18`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_17.pkg` / `v0.4.1_17`;
- `_17` testing-package SHA-256: `92d7d3320246380bef53c7d37364895315e12d55b958c8a5fd657ba9ab213dbf`;
- `_17` source merge/testing-tag target: `ebf071122b2613c4fe56b5af4e5e9f07c99e9122`;
- `_17` publication workflow run: `31887296681`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_N`: **no**.

Machine `_17` publication evidence: [`verification/evidence/testing-publications/v0.4.1_17.md`](verification/evidence/testing-publications/v0.4.1_17.md).

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

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_18` preserves the `_17` regression guard for the existing model-backed default/load/save contract.

## `_17` live RU follow-up — partial acceptance, corrective selected

The owner installed published `_17` and supplied live Russian-mode Diagnostics screenshots.

Confirmed working on the tested screen:

- `Тестирование соединения с доменом`, HTTPS guidance and `Проверка`;
- `Заблокированный домен / IP`, `Запуск`, `Включить QUIC`;
- translated result/stage labels including `Полный профиль Стратегий Трафика`;
- circular idle ordinary presentation is human text (`Статус: ОЖИДАНИЕ`, `Состояние: ОЖИДАНИЕ`) rather than raw JSON.

The same screenshots exposed the current corrective boundary:

1. `Strategy Lab` remained untranslated;
2. `Generic UDP (optional)` remained untranslated;
3. `Заблокированный домен / IP` wrapped to two lines and the owner requested a small left shift shared by the domain input, Generic UDP value control and Enable QUIC control.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md).

## `_18` selected implementation

`_18` is a narrow Strategy Lab presentation/layout corrective package candidate:

- `Strategy Lab` -> RU `Лаборатория стратегий`;
- `Generic UDP (optional)` -> RU `UDP порт (опционально)`;
- EN explicitly remains `Strategy Lab` / `Generic UDP (optional)`;
- domain, Generic UDP and Enable QUIC value controls share one aligned column shifted slightly left from `_17`;
- RU `Заблокированный домен / IP` is kept on one line with a bounded label-column contract;
- no Strategy Lab search/runtime semantics are changed;
- focused regression coverage also preserves prior `_17` RU/EN, circular idle and Enable QUIC persistence source contracts.

Source patch record: [`patches/v0.4.1_18.md`](patches/v0.4.1_18.md).

## Immediate acceptance after `_18` publication

1. verify Russian `Лаборатория стратегий` and `UDP порт (опционально)`;
2. verify `Заблокированный домен / IP` is one line;
3. verify domain input, UDP port input and Enable QUIC checkbox are vertically aligned at the same new left position;
4. verify the same screen in English mode and confirm no RU/EN leakage;
5. separately prove Enable QUIC OFF/default persistence across reload/revisit;
6. continue the risk-selected backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
