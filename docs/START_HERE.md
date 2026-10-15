# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_156`. `VERSION=0.5.2`; `PLUGIN_REVISION=156`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: завершить код пяти Voice-сервисов по неизменному ТЗ, затем **одна testing-поставка** и owner-live приёмка. Без релиза и установки на OPNsense.

## Подтверждено

Не разрабатывать заново: общий Voice+Strategies generator и один `dvtws2`, пять Voice-профилей с managed IPv4 IPSET, scoped STUN/UDP/WAN/IPFW, общий FD9/Config Apply, normal Start/Stop/boot, фактические read-only GUI state/rules/counters. Автоматические проверки не подтверждают реальный STUN/MEDIA/CALL.

**Последний проверенный HEAD:** `_155` `2e06dbb`, [CI #38792544501](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38792544501): Validate Voice candidates, Validate Project, FreeBSD 15 package — **SUCCESS**. PR title и Testing package delivery contract — SUCCESS. FreeBSD package подтвердил отсутствие двух старых операторских маршрутов.

## Точная граница этапа 6

**`_156`:** завершена проверка всех 118 backend файлов и штатных top-level сервисных entrypoints: `voice_native_forward_apply.py` используется лишь старым `voice_native_apply_route.py` (уже исключённым из пакета) и исходниковыми regression tests. Отдельный mutating five-resource исполнитель теперь удаляется из package staging; существующий FreeBSD CI проверяет отсутствие всех трёх retired файлов в фактическом `.pkg`. Исходные исторические тесты сохраняются вне пакета; штатный shared Apply не затронут. Удаление старого source/test framework требует отдельного caller-аудита с сохранением нужных миграционных свидетелей.

**Следующее действие:** проверить полный CI/FreeBSD на точном `_156` и отсутствие old `forward_apply` в pkg tar; при ошибках исправить подтверждённый contract. Затем продолжить stage-6 keep/fold/delete для старых модулей и тестов без повторной разработки recovery. Testing release — только после завершения полного кода.

## Минимальное чтение

После AGENTS и Level-1: [completion gate](VOICE_CODE_COMPLETION_GATE.md), [план этапов](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), [ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_156` не опубликована.
