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
**Current handoff identity:** `v0.4.1_17`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=17` / `v0.4.1_17`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_17.pkg` / `v0.4.1_17`;
- testing-package SHA-256: `92d7d3320246380bef53c7d37364895315e12d55b958c8a5fd657ba9ab213dbf`;
- source merge and testing-tag target: `ebf071122b2613c4fe56b5af4e5e9f07c99e9122`;
- publication workflow run: `31887296681`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by this testing publication: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_17.md`](verification/evidence/testing-publications/v0.4.1_17.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

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

Enable QUIC OFF/default persistence across an actual reload/revisit remains a live acceptance row. `_17` preserves and regression-guards the source persistence contract: model default OFF, save-on-change, load-on-page-open.

## `_17` implementation and automated acceptance — PASS

The owner-selected Strategy Lab / Diagnostics presentation cleanup is now published in `_17`:

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
7. Focused regression coverage asserts that the persisted Enable QUIC contract remains intact and default OFF.

Acceptance completed before source merge:

- exact latest-head PR CI: PASS;
- complete Strategy Lab corrective matrix: PASS;
- focused diagnostics localization/circular/persistence contract: PASS;
- FreeBSD-15 package build/inspection: PASS;
- exact-head source merge: `ebf071122b2613c4fe56b5af4e5e9f07c99e9122`;
- persistent testing prerelease/package verification: PASS.

Source patch record: [`patches/v0.4.1_17.md`](patches/v0.4.1_17.md).

## Immediate owner-live acceptance

After installing `v0.4.1_17`:

1. verify the listed visible labels and circular idle presentation in **Russian** mode;
2. verify the same screen in **English** mode and confirm no RU/EN leakage;
3. set Enable QUIC OFF, reload/revisit Diagnostics and verify OFF is restored; also confirm fresh/default state is OFF where applicable;
4. then continue the risk-selected regression backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
