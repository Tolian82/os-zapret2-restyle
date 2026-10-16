# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_176`. `VERSION=0.5.2`; `PLUGIN_REVISION=176`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_173` HEAD `b096b5a`, [CI #38900822687](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38900822687): Voice, Project и FreeBSD 15 package — **PASS**; testing delivery contract — **PASS**. Это не live STUN/MEDIA/CALL.

## Окончательное решение владельца — 16.10.2026

**Ведётся разработка конечного решения по ТЗ, без сохранения старого Telegram PoC, пятиресурсного rollback, reverse migration, исторических recovery WAL/receipt и их тестов.** Не поддерживать совместимость с отменённым private backend. Удалять ненужные подграфы целиком, без многомесячного последовательного дублирования legacy схем. Корректная обработка ошибок действующего единого Apply остаётся частью штатной архитектуры, но не поводом сохранять старый PoC.

## Текущий участок: этап 6

**`_168`:** выводятся manual legacy PoC routes, previous-five/reverse-plan/WAL/receipt/restore executors, старые `shared-apply-legacy-*` команды и GUI-панель восстановления старого Telegram PoC. Удаляются историческая migration assessment и связанные тесты. Пять профилей, единый Voice+Strategies dvtws2/Config/FD9 Apply, нормальные Start/Stop и IPFW не меняются. CI и FreeBSD package guards теперь запрещают возвращение удалённых модулей.

**`_169`:** удалены Phase-B prepend/marker/Telegram-only IPFW table/rule. Voice использует только общий Apply, обычные Strategies — портовые правила. **`_170`:** исправлен устаревший тест сборщика и синхронизирована release identity после выявленных ошибок `_169` ([CI #38872692193](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38872692193)). **`_173`:** Из общего журнала Apply удалены отменённые `legacy-*` состояния и `arm-legacy` CLI (~23 КБ), обновлена Strategy Lab фикстура и удалён исторический boot-guard test. `_172` [CI #38899325896](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38899325896): Voice/Project FAIL из-за старых тестовых зависимостей. Далее — квалифицировать `_173` и удалить оставшийся private `voice_cutover_*` подграф.

**`_174`:** из Voice status удалены чтение исторического `voice-cutover` и возможность считать старый private IPFW ledger рабочим runtime. Статус теперь только от общего shared Apply; без владельца выдаётся `uninitialized`, не READY. Обновлены регрессии общего engine/IPFW/status. Дальше удалить old `voice_cutover_*` import graph и private CLI; `_174` требует собственного exact-HEAD CI.

**`_175`:** `voice_native_lifecycle_router.py` переведён с PoC cutover/backup/old-IPFW импортов на `shared_apply_operation.native_lifecycle_gate` и прямую read-only проверку Config inode/flock. Удалён CLI `legacy-poc-preflight`. Результаты saved ON/OFF теперь говорят об общем Apply, а не о «неподключённом» native. Обновлён regression saved/config-flock/candidate/shared pending. После CI `_175` — удаление неиспользуемого `voice_cutover_*` private graph.

**`_176`:** read-only GUI Voice draft preview больше не зависит от старого `voice_ipfw_runtime` и private quiescence. Разбор сохранённых профилей перенесён на общий Config/flock verifier; отдельный неиспользуемый publisher XML `prepare_saved_draft_candidate` удалён. Оставлены проверки маски, hash, точности XML и отсутствия записей. Далее — полное удаление `voice_cutover_*` и зависимого private graph. Нужен exact-HEAD CI.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_176` не опубликована.
