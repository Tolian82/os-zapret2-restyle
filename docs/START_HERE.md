# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_191`. `VERSION=0.5.2`; `PLUGIN_REVISION=191`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить весь код по ТЗ пяти Voice-сервисов, затем полноценный релиз и только после него реальные испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_190` HEAD `0fe4f11`, [CI #38946969246](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38946969246): Voice/Project/FreeBSD 15 **PASS**, [delivery contract #38946969196](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38946969196) — PASS. CI не доказывает реальный UDP/STUN/MEDIA/CALL.

## Окончательное решение владельца — 16.10.2026

**Ведётся разработка конечного решения по ТЗ, без сохранения старого Telegram PoC, пятиресурсного rollback, reverse migration, исторических recovery WAL/receipt и их тестов.** Не поддерживать совместимость с отменённым private backend. Удалять ненужные подграфы целиком, без многомесячного последовательного дублирования legacy схем. Корректная обработка ошибок действующего единого Apply остаётся частью штатной архитектуры, но не поводом сохранять старый PoC.

## Текущая граница: релиз после программной готовности

**Последнее решение владельца 16.10.2026:** завершить всё программирование по неизменному ТЗ пяти Voice-сервисов, затем **выпустить полноценный релиз**, и лишь после него проводить owner-live GUI/CONFIG/BOOT/STUN/MEDIA/CALL испытания. Ни промежуточных установок, ни live-тестов до релиза; релиз при известных критических дефектах также недопустим. Исправления в рабочем коде и exact-HEAD CI остаются обязательными до выпуска.

**`_191` — общий Apply двух страниц:** исходный `SettingsController::applyAction` классифицировал post-FD9 `InvalidArgumentException` как обычную редактируемую ошибку, а `general.volt` разрешал повтор после неизвестного AJAX-ответа. Теперь «Стратегии» применяют тот же post-dispatch `requires_review` и браузерный single-flight/reload gate, что и Voice, без изменения общего engine/IPFW и компоновки страницы. Существующая PHP concurrency regression расширена на обе страницы; контракт Strategies проверяет timeout/review wiring. **Следующее действие:** дождаться exact-HEAD CI Voice/Project/FreeBSD `_191`, затем провести конечный аудит нереализованных требований по ТЗ и выпустить полноценный релиз по `GH-039`–`GH-052`, не начиная owner-live до релиза.

Старый Telegram PoC, Phase-B migration, marker и private recovery исключены решением владельца; удаление завершено ранее. Полная история ревизий находится только в [current ledger](history/current/v0.5.x.md).

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_191` не опубликована.
