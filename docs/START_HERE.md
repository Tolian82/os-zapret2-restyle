# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_167`. `VERSION=0.5.2`; `PLUGIN_REVISION=167`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_166` HEAD `8746aee`, [CI #38827533621](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38827533621) — успешно пройдены Validate Voice candidates, Validate Project и Build FreeBSD 15 package. Отдельный [testing-package contract #38827533644](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38827533644) также успешен. Это проверки кода и пакета, не owner-live STUN/MEDIA/CALL.

Реализованы пять Voice-профилей, единый Voice+Strategies `dvtws2`/FD9/Config Apply, scoped STUN/IPFW, normal Stop/Start/boot и GUI status. Не переоткрывать без воспроизводимого дефекта.

## Текущий участок: этап 6

**`_167`:** сохранена необходимая проверка исторического `forward-runtime-redo.json` в `voice_native_forward_runtime._read_redo` и неизменный импорт из `voice_cutover_file_rollback.py`. Удалены неиспользуемые private writer `install_forward_runtime`, `_arm`, `_copy_candidate` и связанные копирование/rename/redo fsync path: с удалением отдельного forward Stop не осталось production callers. Старый test-файл переведён на девять независимых read-only проверок исторического schema/digest/inode/permission/size/filename и запрета возврата mutator API. Source/package guards обновлены. Общий Apply, реальные rollback-компоненты, пять профилей и frontend не менялись.

**Следующее действие:** квалифицировать exact HEAD `_167` в Voice, Project и FreeBSD 15; исправлять только доказанные регрессии в той же ревизии. Затем проверить все оставшиеся реальные legacy entrypoints и конфигурацию миграции против критериев завершения этапа 6; при отсутствии кодовых пробелов переходить к подготовке одной testing-поставки только после документированного gate. Без релиза и установки сейчас.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_167` не опубликована.
