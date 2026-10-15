# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_163`. `VERSION=0.5.2`; `PLUGIN_REVISION=163`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_162` HEAD `1d7e3d5`, [CI #38810202894](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38810202894) — успешно пройдены Validate Voice candidates, Validate Project и Build FreeBSD 15 package. Title и testing-package governance также прошли. Это проверки кода и пакета, не owner-live STUN/MEDIA/CALL.

Реализованы пять Voice-профилей, один общий Voice+Strategies `dvtws2`/FD9/Config Apply, scoped STUN/IPFW, normal Start/Stop/boot и GUI status. Повторной реализации не требуется.

## Текущий участок: этап 6

**`_163`:** удалён неиспользуемый производственный `voice_native_forward_ipfw.py`. Штатные GUI/configd/service/shared Apply не имели вызовов; прежний тест использовал его только для подготовки состояния downstream supervisor. Теперь `test-voice-native-forward-ipfw.py` подготавливает real IPFW PRECOMMIT через существующий `voice_ipfw_runtime.activate_verified`, сохраняя полезные rollback/failure/foreign-state сценарии и dependent supervisor tests. Source и FreeBSD package guards дополнены. Общий Apply, migration, GUI не изменены.

**Следующее действие:** подтвердить Voice, Project и FreeBSD 15 на точном HEAD `_163`, исправить только доказанные регрессии в той же ревизии. Далее закрывать оставшиеся фактические требования этапа 6 по проверенной карте рабочих вызовов, не расширяя recovery. Без testing release до полной кодовой готовности.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_163` не опубликована.
