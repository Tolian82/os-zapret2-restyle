# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_159`. `VERSION=0.5.2`; `PLUGIN_REVISION=159`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Владелец решил закончить код по неизменному ТЗ пяти Voice-сервисов, после чего сделать **одну testing-поставку** и owner-live испытания. До того без релиза и установки на OPNsense.

## Последняя квалификация

`_158` HEAD `638ad10`, [CI #38799629806](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38799629806) — **PASS** Validate Voice candidates, Validate Project и Build FreeBSD 15 package. PR title и testing delivery contract PASS. Автоматические проверки не равны живым STUN/MEDIA/CALL.

Уже реализованы по коду: один общий Voice+Strategies full runtime/`dvtws2`, пять профилей, IPv4 managed IPSET, scoped STUN/UDP/WAN/IPFW, общий FD9/Config Apply, normal Stop/Start/boot и read-only GUI state/rules/counters. Без нового доказанного дефекта не переписывать.

## Текущая граница этапа 6

`_159`: удаляются три изолированных import-only компонента старого PREPARED, оставшиеся после удаления operator route: `voice_native_prepare_one_lock.py`, `voice_native_operator_input_stage.py`, `voice_native_saved_release_prepare.py`, а также три dedicated Python test suites. По реальным импортам эти модули не вызываются штатным service/configd/shared Apply; сохранены common generator, `voice_native_draft_preview_route.py`, read-only boot/migration witnesses и тесты общего Apply. Удалённые legacy tests больше не запускаются Linux CI; существующий package check сохраняет запрет retired operator filenames.

**Точное следующее действие:** квалифицировать полный Voice/Project/FreeBSD CI на HEAD `_159`; далее провести caller-driven keep/fold/delete для оставшейся private PREPARED ветки, прежде всего `voice_native_forward_stage_prepare.py` и её действительных зависимостей. Не расширять old recovery и не выпускать testing до кодовой готовности.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_159` ещё не опубликована.
