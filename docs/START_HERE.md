# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_164`. `VERSION=0.5.2`; `PLUGIN_REVISION=164`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_163` HEAD `24dc0c4`, [CI #38811642907](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38811642907) — **успешно** завершены Validate Voice candidates, Validate Project и Build FreeBSD 15 package. Проверены версия, PR title и testing-package governance. Это квалификация CI/пакета, а не OPNsense live STUN/MEDIA/CALL.

Уже реализованы пять Voice-профилей, единый Voice+Strategies `dvtws2`/FD9/Config Apply, scoped UDP/STUN/IPFW, normal Start/Stop/boot и GUI status. Без воспроизводимого дефекта их не строить заново.

## Текущий участок: этап 6

**`_164`:** из production удалён неиспользуемый отдельный `voice_native_forward_supervisor.py`, из исходников и CI — его standalone test. Команда `start-candidate-supervisor` удалена из старого private shell actuator, поскольку не имеет других рабочих callers после отказа от отдельного forward Apply. Обычный `supervisor_start`, штатный общий lifecycle, старый rollback `stop/start`, фиксированный `start-candidate-engine` и shared IPFW PRECOMMIT остаются. Guard source/FreeBSD package проверяет отсутствие retired module. Frontend, shared Apply и migration не менялись.

**Следующее действие:** проверить все три обязательные CI-задачи Voice, Project и FreeBSD 15 на точном HEAD `_164`; исправить реальные регрессии без новой ревизии. Дальше продолжать этап 6 только по доказанной карте callers/пакета, сохраняя необходимые rollback/read-only функции. Никакого testing release до полной кодовой готовности.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_164` не опубликована.
