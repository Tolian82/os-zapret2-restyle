# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: сначала закончить код, затем **одна** testing поставка и живые испытания. Действующая база `v0.5.2_148` в [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза. GUI/ТЗ не менять.

## Реализовано в коде (не равно live PASS)

| Поведение | Источник проверки |
|---|---|
| Пять Voice-профилей, IPv4 IPSET, native Config и stale snapshots | `VoiceController.php`, `SettingsApply.php`, `test-voice-gui-contract.py` |
| Один генератор полного Voice+Strategies runtime и port/IPSET files | `backend/orchestrator.sh`, `test-voice-common-runtime.py` |
| Соответствие STUN-args/портов/WAN/IPSET/divert реальному IPFW manifest | `voice_ipfw_adapter._verify_shared_voice_engine`, `test-voice-common-runtime.py` |
| FD9 общий Apply двух страниц, Config save/commit/rollback | `zapret_service.sh`, `apply_runtime.sh`, `test-shared-apply-{run,execute}.sh` |
| Normal Stop/Start/boot и truthful inspect/GUI status | `zapret_service.sh`, `voice.volt`, `test-shared-apply-{stop,boot}.sh` |

Эти функции **уже существуют**, повторная разработка запрещена без конкретного нового дефекта. Изолированная проверка не доказывает реальный STUN или звонок.

## Оставшаяся работа перед testing package

1. **CI:** предыдущий HEAD `9a6ccf5` (`_147`) успешно прошёл Validate Project и Voice candidates (Actions `38766216983`). `_148` с фактическим rule/counters status требует собственного latest-HEAD CI.
2. **FreeBSD:** предыдущий `_147` FreeBSD 15 package build SUCCESS (Actions `38766216983`). Новый `_148` требует собственной сборки.
3. **Legacy PoC:** `_146` привязал публичные Telegram enable/disable/status к native Config/FD9/Apply/inspect. Работающий Phase-B блокирует автоматическое переключение до квалифицированной миграции; исторические rollback/migration файлы пока сохранены. Живая миграция ещё не проверена.
4. **Финальная приёмка кода:** `_144–_145` исправили native GUI/help/draft UX, `_146–_147` — Telegram configctl compatibility, `_148` — фактические native IPFW rule и доступные counters. Далее только доказанные GUI/API/Config/lifecycle/package разрывы; all-OFF draft не подменяет Apply.

После фактического закрытия — «код готов к испытаниям», **не** `MEDIA_PASS/CALL_PASS`.

## После кодовой готовности

Одна согласованная GitHub testing поставка, затем OPNsense GUI/CONFIG/BOOT и фактический UDP/STUN, двусторонний MEDIA/CALL тест. Старый `v0.5.0_3` и `misconfigured / unknown-repository` не являются проверкой новой ветки. Без merge/stable до согласованных результатов.

Для каждого требования отдельно фиксируются **source implemented**, **CI/package verified**, **owner-live confirmed**. Новую разработку начинать только после проверки production entrypoint и конкретного отсутствующего/сломавшегося поведения. Точная очередь — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [ledger](history/current/v0.5.x.md).
