# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_154`. `VERSION=0.5.2`; `PLUGIN_REVISION=154`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). По решению владельца 15.10.2026: сначала полностью реализовать код ТЗ пяти Voice-сервисов, затем **одна testing-поставка** и owner-live испытания. Без релиза и установки на OPNsense.

## Подтверждённая база

Уже реализованы, не переделывать без новой ошибки: единый Voice+Strategies runtime/`dvtws2`, пять Voice профилей, managed IPv4 IPSET, scoped STUN/UDP/WAN/IPFW, общий FD9/Config Apply и Start/Stop/boot, read-only native GUI rule/counters/attestation. CI не доказывает реальные MEDIA/CALL/STUN.

**Последний полный успешный HEAD:** `_153` `db20ef0`, [CI #38786982877](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38786982877): Validate Voice candidates, Validate Project и FreeBSD 15 package — **SUCCESS**.

## Текущий рубеж и следующий шаг

**`_154`, этап 6:** по статическому аудиту 118 backend-файлов найдены две настоящие ссылки на старые operator modules: `voice_native_legacy_predecessor_route.py` импортировал credentials из `voice_native_prepare_route.py`, а `voice_native_forward_stage_prepare.py` импортирует sealed witness из `voice_native_apply_route.py`. Первая зависимость перенесена в существующий `voice_freebsd_process_security.py`, пять старых shell PREPARED operator CLI удалены и `voice_native_prepare_route.py` исключается из package stage. Исходник для изолированных регрессий сохранён в Git. Вторую зависимость пока нельзя удалять без отдельной проверки; общий native Apply/GUI и legacy transition не меняются.

**Точное следующее действие:** подтвердить три CI/FreeBSD job на HEAD `_154` и убедиться в отсутствии `voice_native_prepare_route.py` в package staging/plist; затем продолжить keep/fold/delete аудит оставшегося private code на основании фактических callers. Не расширять старый recovery и не выпускать testing до кодовой готовности.

## Минимальное чтение

После AGENTS и четырёх rule books/ROADMAP/INDEX: [completion gate](VOICE_CODE_COMPLETION_GATE.md), [план 6–7](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), [ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_154` пока не опубликована.
