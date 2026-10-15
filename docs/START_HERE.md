# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_160`. `VERSION=0.5.2`; `PLUGIN_REVISION=160`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Владелец решил завершить функциональный код пяти Voice-сервисов по неизменному ТЗ, затем выполнить одну testing-поставку и owner-live испытания. Релиза и установки на OPNsense пока нет.

## Последняя подтверждённая проверка

`_159` HEAD `6de03e6` — [CI #38801461001](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38801461001), повторная попытка: **PASS** Voice candidates, Project и FreeBSD 15 package. Первоначальный Strategy Lab e2e RESTORE_FAILED не воспроизвёлся на повторном прогоне того же кода. Это CI/package evidence, не живой STUN/MEDIA/CALL.

По кодовой матрице уже реализованы: один общий Voice+Strategies runtime/`dvtws2`, пять профилей, managed IPv4 IPSET, scoped STUN/UDP/WAN/IPFW, единый native FD9/Config Apply, штатные Stop/Start/boot, read-only GUI rules/counters/status. Не повторять без конкретного дефекта.

## Текущий рубеж этапа 6

**`_160`:** после caller-аудита 112 backend файлов и service/configd/shared Apply удаляются три orphan old PREPARED helpers: `voice_native_forward_stage_prepare.py`, `voice_native_previous_evidence_prepare.py` и `voice_native_initial_ipfw_seed.py`, плюс три protocol-specific test suites. `test-voice-native-apply-route.py` сокращён до negative entrypoint/package contract: больше не исполняет sealed private PREPARED протокол. FreeBSD tar inspection запрещает повторное появление этих файлов. Общий backend, read-only draft preview и необходимая guarded legacy migration не меняются.

**Точное следующее действие:** получить полный Voice/Project/FreeBSD CI на точном HEAD `_160`; затем проверить `voice_native_forward_prepare.py` и source-level test fixture dependency chain, удалять только после проверки отсутствия нужного caller. Рабочую миграцию и normal Apply не затрагивать. Не выпускать testing пока не завершён код ТЗ.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_160` ещё не опубликована.
