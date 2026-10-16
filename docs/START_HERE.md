# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_179`. `VERSION=0.5.2`; `PLUGIN_REVISION=179`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_176` HEAD `2f66022`, [CI #38904110487](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38904110487): **Voice/Project/FreeBSD 15 PASS**; package delivery contract — PASS. Это не подтверждение MEDIA/CALL на OPNsense.

## Окончательное решение владельца — 16.10.2026

**Ведётся разработка конечного решения по ТЗ, без сохранения старого Telegram PoC, пятиресурсного rollback, reverse migration, исторических recovery WAL/receipt и их тестов.** Не поддерживать совместимость с отменённым private backend. Удалять ненужные подграфы целиком, без многомесячного последовательного дублирования legacy схем. Корректная обработка ошибок действующего единого Apply остаётся частью штатной архитектуры, но не поводом сохранять старый PoC.

## Текущий участок: этап 6

**`_168`:** выводятся manual legacy PoC routes, previous-five/reverse-plan/WAL/receipt/restore executors, старые `shared-apply-legacy-*` команды и GUI-панель восстановления старого Telegram PoC. Удаляются историческая migration assessment и связанные тесты. Пять профилей, единый Voice+Strategies dvtws2/Config/FD9 Apply, нормальные Start/Stop и IPFW не меняются. CI и FreeBSD package guards теперь запрещают возвращение удалённых модулей.

**`_169`:** удалены Phase-B prepend/marker/Telegram-only IPFW table/rule. Voice использует только общий Apply, обычные Strategies — портовые правила. **`_170`:** исправлен устаревший тест сборщика и синхронизирована release identity после выявленных ошибок `_169` ([CI #38872692193](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38872692193)). **`_173`:** Из общего журнала Apply удалены отменённые `legacy-*` состояния и `arm-legacy` CLI (~23 КБ), обновлена Strategy Lab фикстура и удалён исторический boot-guard test. `_172` [CI #38899325896](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38899325896): Voice/Project FAIL из-за старых тестовых зависимостей. Далее — квалифицировать `_173` и удалить оставшийся private `voice_cutover_*` подграф.

**`_174`:** из Voice status удалены чтение исторического `voice-cutover` и возможность считать старый private IPFW ledger рабочим runtime. Статус теперь только от общего shared Apply; без владельца выдаётся `uninitialized`, не READY. Обновлены регрессии общего engine/IPFW/status. Дальше удалить old `voice_cutover_*` import graph и private CLI; `_174` требует собственного exact-HEAD CI.

**`_175`:** `voice_native_lifecycle_router.py` переведён с PoC cutover/backup/old-IPFW импортов на `shared_apply_operation.native_lifecycle_gate` и прямую read-only проверку Config inode/flock. Удалён CLI `legacy-poc-preflight`. Результаты saved ON/OFF теперь говорят об общем Apply, а не о «неподключённом» native. Обновлён regression saved/config-flock/candidate/shared pending. После CI `_175` — удаление неиспользуемого `voice_cutover_*` private graph.

**`_176`:** read-only GUI Voice draft preview больше не зависит от старого `voice_ipfw_runtime` и private quiescence. Разбор сохранённых профилей перенесён на общий Config/flock verifier; отдельный неиспользуемый publisher XML `prepare_saved_draft_candidate` удалён. Оставлены проверки маски, hash, точности XML и отсутствия записей. Далее — полное удаление `voice_cutover_*` и зависимого private graph. Нужен exact-HEAD CI.

**`_177`:** целиком удалён старый Telegram cutover/previous-five/private IPFW граф: 95 исходников и тестов (~0,93 МБ), включая все `voice_cutover_*` и неиспользуемые связанные executors/CI. Из `zapret_service.sh` убраны старые ручные команды checkpoint/restore/five-resource/old IPFW; входы пяти Voice GUI-профилей и общего Apply сохранены. FreeBSD package guard теперь запрещает возврат старого графа. Квалификация exact HEAD `_177` требуется. Далее завершить зачистку остаточных комментариев/CLI оболочек и подтвердить функциональный сценарий по ТЗ.

**`_178`:** после большой очистки `_177` [CI #38906538711](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38906538711) обнаружена устаревшая тестовая заглушка `preflight_voice_cutover_journals`, тогда как реальный production использует `preflight_shared_apply_journal`. Все соответствующие Common Apply/Stop/Boot/FD9 регрессии переключены на новый contract; журнал проверяется только через `native_lifecycle_gate`, без PoC-модулей. Требуется exact-HEAD CI новой ревизии.

**`_179`:** обновлены три дополнительные фикстуры, обнаруженные в `_178` [CI #38906963122](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38906963122): `test-shared-apply-saved-recovery.sh`, `test-shared-apply-activated-staged.sh`, `test-shared-apply-render.py` теперь ожидают `preflight_shared_apply_journal`. Runtime и удалённый private PoC не менялись. Требуется полный exact-HEAD CI.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_179` не опубликована.
