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
**Current handoff identity:** `v0.4.1_17` source candidate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=17` / `v0.4.1_17`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- `_16` SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- `_16` source/tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promotion for testing `_N`: **no**.

`_17` is not published until source CI, FreeBSD-15 qualification, exact-head merge, persistent testing publication and publication-record reconciliation complete.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, QUIC-OFF execution, or Generic UDP baseline work without fresh contradictory evidence.

Accepted owner-live evidence includes:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, all three current UDP candidates and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: OFF suppresses QUIC candidate execution while independent Generic UDP remains active;
- visible Stage-90 restoration on the tested flows.

Durable evidence:

- [`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md)
- [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md)

Enable QUIC OFF/default persistence across an actual reload/revisit remains a live acceptance row. The source persistence contract itself already exists and `_17` preserves it: model default OFF, save-on-change, load-on-page-open.

## `_17` selected implementation — Strategy Lab / Diagnostics RU-EN cleanup

The owner-selected presentation scope is implemented in source candidate `_17`:

1. Temporary circular validation ordinary state no longer renders raw JSON braces or `{"state":"idle"}`. It renders RU `Состояние: ОЖИДАНИЕ` / EN `State: IDLE`. Raw machine job JSON remains only in the explicitly advanced Strategy Lab output.
2. `Full output (advanced)` -> RU `Полный вывод (расширенный)`.
3. `Enter a domain and click Test to check HTTPS connectivity.` -> RU `Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.`
4. Result/table labels:
   - `Family` -> `Семейство`;
   - `Endpoints` -> `Назначения`;
   - `Outcome` -> `Результат`;
   - `Restoration` -> `Восстановление`;
   - `Replay` -> `Ответы`;
   - `Complete Traffic Strategy profile` -> `Полный профиль Стратегий Трафика`.
5. Main labels/actions:
   - `Run` -> `Запуск`;
   - `Test Domain Connectivity` -> `Тестирование соединения с доменом`;
   - EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`;
   - `Enable QUIC` -> RU `Включить QUIC`.
6. Deterministic presentation follows the selected OPNsense page language and keeps corresponding English strings in EN mode.
7. Focused regression coverage also asserts that the existing persisted Enable QUIC contract remains intact and default OFF.

Source patch record: [`patches/v0.4.1_17.md`](patches/v0.4.1_17.md).

## Immediate acceptance after publication

After `v0.4.1_17` is persistently published and installed:

1. verify the listed visible labels and circular idle presentation in **Russian** mode;
2. verify the same screen in **English** mode and confirm no RU/EN leakage;
3. set Enable QUIC OFF, reload/revisit Diagnostics and verify OFF is restored; also confirm fresh/default state is OFF where applicable;
4. then continue the risk-selected regression backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
