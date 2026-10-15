# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_162`. `VERSION=0.5.2`; `PLUGIN_REVISION=162`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_161` HEAD `ff7cc54`, [CI #38807350980](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38807350980) — **PASS** Validate Voice candidates, Validate Project и Build FreeBSD 15 package. PR title и testing delivery contract также проверены. Это CI/package qualification, а не OPNsense live STUN/MEDIA/CALL.

Реализованы и не подлежат повторному созданию без дефекта: пять Voice-профилей, общий Voice+Strategies `dvtws2`/FD9/Config Apply, scoped UDP/STUN/WAN/IPFW, normal Start/Stop/boot, read-only GUI status/rules/counters.

## Текущий участок: этап 6

**`_162`:** из `voice_native_forward_config.py` удалены устаревший private Config writer `persist_forward_candidate_config` и marker-arm helper. Он не имел caller в normal GUI/configd/boot/shared Apply/backend. Сохранён **только read-only reader** старого inode-bound `forward-config-redo.json` и проверка candidate prefix: прежний `voice_cutover_config_restore.py` использует это для fail-closed восстановления исторического частичного состояния. Dedicated old writer suite заменён на проверки чтения, checksum, inode/source, phase и отказа на чужих данных. Общий native saver и migration не менялись.

**Следующее действие:** подтвердить полную матрицу Voice/Project/FreeBSD для точного HEAD `_162`; при конкретной регрессии исправить её в этой же ревизии. Затем сверить следующий old forward executor с caller map и критериями ТЗ, не вырезая необходимый rollback. Без testing release до кодовой готовности.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_162` не опубликована.
