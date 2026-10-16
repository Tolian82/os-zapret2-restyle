# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_166`. `VERSION=0.5.2`; `PLUGIN_REVISION=166`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_165` HEAD `6ca0576`, [CI #38826485428](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38826485428) — успешно прошли Validate Voice candidates, Validate Project и Build FreeBSD 15 package. Дополнительно успешны testing-package governance, FreeBSD 15 testing-package qualification и проверка PR title. Это CI/package qualification, но не OPNsense live STUN/MEDIA/CALL.

Реализованы и сохраняются: пять Voice-профилей, общий Voice+Strategies `dvtws2`/FD9/Config Apply, scoped UDP/STUN/IPFW, normal Start/Stop/boot, RU/EN GUI и read-only status/counters. Не дублировать без доказанного дефекта.

## Текущий участок: этап 6

**`_166`:** удалён `voice_native_forward_stop.py` — private stage, останавливавший прежний engine и переставлявший runtime в старом несобранном forward cutover. В рабочем GUI/configd/boot/shared Apply нет его вызовов, а в тестах его использовал только `test-voice-native-forward-stop.py`, удалённый вместе с ним. Тест `test-voice-native-forward-runtime.py` с реальными crash/rollback сценариями остаётся, как и `voice_native_process_actions.py` / `voice_native_process_lifecycle.sh` (проверяемый предыдущий stop/start и `stop-candidate-engine`). Общие IPFW PRECOMMIT tests не зависят от old forward stop. Добавлены source/package guards; frontend, normal Apply и миграция не менялись.

**Следующее действие:** проверить Voice candidates, Validate Project и FreeBSD 15 package на точном HEAD `_166`; исправить только реальные same-scope регрессии без новой ревизии. Затем по реальной карте вызовов оценить старый forward-runtime *writer*, не вырезая read-only `_read_redo` и historic recovery. Testing release не выпускать до завершения кода.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_166` не опубликована.
