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
**Current handoff identity:** `v0.4.1_16`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=16`;
- current source candidate: `PLUGIN_REVISION=16` / `v0.4.1_16`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- testing-package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- source merge and testing-tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publication workflow run: `31882091770`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by this testing publication: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_16.md`](verification/evidence/testing-publications/v0.4.1_16.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, or Generic UDP baseline work without fresh contradictory evidence.

Accepted owner-live evidence now includes:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, real three-candidate execution and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: when OFF, Stage 80 reports QUIC strategy search disabled while the independent Generic UDP path still runs normally;
- visible Stage-90 restoration on the tested paths.

Generic UDP evidence:
[`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md).

QUIC OFF/UI follow-up evidence:
[`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md).

The QUIC OFF live run proves execution semantics only. **Persistence across page reload/revisit remains pending** until the OFF value is observed after an actual reload/revisit.

## Selected implementation work — RU/EN UI cleanup

The owner selected the following Strategy Lab/Diagnostics presentation work for implementation:

1. Temporary circular validation idle block:
   - remove ordinary-display JSON braces `{` / `}`;
   - replace raw `{"state":"idle"}` presentation with localized ordinary text;
   - RU target: `Состояние: ОЖИДАНИЕ`;
   - EN target: `State: IDLE`;
   - raw JSON, if retained, belongs only in an explicitly advanced/raw area.
2. `Full output (advanced)` must be localized; RU target: `Полный вывод (расширенный)`.
3. `Enter a domain and click Test to check HTTPS connectivity.` must have RU/EN output; RU target: `Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.`
4. Result/table labels must be localized:
   - `Family` -> `Семейство`;
   - `Endpoints` -> `Назначения`;
   - `Outcome` -> `Результат`;
   - `Restoration` -> `Восстановление`;
   - `Replay` -> `Ответы`;
   - `Complete Traffic Strategy profile` -> `Полный профиль Стратегий Трафика`.
5. Main labels/actions:
   - `Run` -> `Запуск`;
   - `Test Domain Connectivity` -> `Тестирование соединения с доменом`;
   - `Blocked Domain` -> EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`;
   - `Enable QUIC` -> RU `Включить QUIC`.
6. Final acceptance must explicitly inspect both RU and EN modes so neither language leaks labels from the other.

Obvious spelling slips from the conversational task are normalized to intended product strings (`Run`, `QUIC`, `Ответы`, `Включить`).

## Immediate next task

Next work is now two-part and must remain explicit in documentation:

1. verify **Enable QUIC OFF/default persistence** across reload/revisit;
2. implement the selected RU/EN/circular-idle presentation cleanup above, then perform live RU/EN acceptance.

After those rows, continue the risk-selected regression backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
