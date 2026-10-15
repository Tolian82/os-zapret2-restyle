# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_165`. `VERSION=0.5.2`; `PLUGIN_REVISION=165`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_164` HEAD `2622d4b`, [CI #38813372416](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38813372416) — **успешно** завершились Validate Voice candidates, Validate Project и Build FreeBSD 15 package. Отдельные проверки testing delivery contract и versioned PR title также успешны. Это CI/package, но не живые STUN/MEDIA/CALL.

Уже реализованы пять Voice-профилей, один общий Voice+Strategies `dvtws2`/FD9/Config Apply, scoped UDP/STUN/IPFW, normal Start/Stop/boot и GUI status. Без нового воспроизводимого дефекта эти функции не создавать повторно.

## Текущий участок: этап 6

**`_165`:** из production удалён отдельный `voice_native_candidate_engine_start.py` и его test-only source suite. В `voice_native_process_lifecycle.sh` убрана только больше не вызываемая команда `start-candidate-engine`. Старый `stop-candidate-engine` пока сохранён в process-actions compatibility вместе с обычными `start/stop` для защищённого rollback. Тесты общего native IPFW PRECOMMIT теперь формируют schema-4 intent прямо через `NativeForwardPrepareTests.prepare` и `VoiceCutoverJournal.mark_mutating`, затем проверяют действующий `voice_ipfw_runtime.activate_verified`, без отдельного запуска процесса. Source/FreeBSD package guards обновлены; общий Apply, GUI, legacy migration и read-only witnesses не менялись.

**Следующее действие:** на точном HEAD `_165` подтвердить три проверки Voice/Project/FreeBSD 15; исправить конкретные регрессии этой же ревизии. Затем проверить отдельный старый `voice_native_forward_stop.py` и только по полной карте вызовов рассмотреть упрощение его тестового слоя, не трогая откат предыдущего состояния. Testing release — после завершения всей кодовой работы.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_165` не опубликована.
