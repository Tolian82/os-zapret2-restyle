# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_168`. `VERSION=0.5.2`; `PLUGIN_REVISION=168`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_167` HEAD `eb2518e`, [CI #38840666241](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38840666241): Voice, Project, FreeBSD 15 package — **PASS**; [testing package contract #38840666255](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38840666255) — **PASS**. Не live STUN/MEDIA/CALL.

## Окончательное решение владельца — 16.10.2026

**Ведётся разработка конечного решения по ТЗ, без сохранения старого Telegram PoC, пятиресурсного rollback, reverse migration, исторических recovery WAL/receipt и их тестов.** Не поддерживать совместимость с отменённым private backend. Удалять ненужные подграфы целиком, без многомесячного последовательного дублирования legacy схем. Корректная обработка ошибок действующего единого Apply остаётся частью штатной архитектуры, но не поводом сохранять старый PoC.

## Текущий участок: этап 6

**`_168`:** выводятся manual legacy PoC routes, previous-five/reverse-plan/WAL/receipt/restore executors, старые `shared-apply-legacy-*` команды и GUI-панель восстановления старого Telegram PoC. Удаляются историческая migration assessment и связанные тесты. Пять профилей, единый Voice+Strategies dvtws2/Config/FD9 Apply, нормальные Start/Stop и IPFW не меняются. CI и FreeBSD package guards теперь запрещают возвращение удалённых модулей.

**Следующее действие:** подтвердить `_168` exact-HEAD Voice/Project/FreeBSD; исправлять только выявленные реальные зависимости. Затем удалить оставшийся private `voice_cutover_*`/PoC подграф и отключить legacy blocking в штатном пути, сохраняя только текущий единый Apply. Не выпускать testing package до source-code gate; owner-live после одной поставки.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_168` не опубликована.
