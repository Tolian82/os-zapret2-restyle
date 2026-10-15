# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: сначала закончить код, затем **одна** testing поставка и живые испытания. Действующая база `v0.5.2_146` в [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза. GUI/ТЗ не менять.

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

1. **CI:** предыдущий HEAD `c7f51bf` (`_145`) прошёл Validate Project, Voice candidates и FreeBSD 15 package build (Actions `38761330203`). Новый `_146` с Telegram native configctl адаптерами проверяется отдельно.
2. **FreeBSD:** подтвердить настоящую package-сборку для `_146`; предыдущий `_145` PASS не доказывает новый HEAD.
3. **Legacy PoC:** `_146` привязал публичные Telegram enable/disable/status к native Config/FD9/Apply/inspect. Работающий Phase-B блокирует автоматическое переключение до квалифицированной миграции; исторические rollback/migration файлы пока сохранены. Живая миграция ещё не проверена.
4. **Финальная приёмка кода:** исправлены XML подсказки Validate / all-OFF draft / Apply (`_144`) и ложная API/RU ошибка о недоступности ON (`_145`). При этом all-OFF draft не подменяет native Apply. Далее только реальные GUI/API → Config → generator/IPFW → lifecycle и package разрывы.

После фактического закрытия — «код готов к испытаниям», **не** `MEDIA_PASS/CALL_PASS`.

## После кодовой готовности

Одна согласованная GitHub testing поставка, затем OPNsense GUI/CONFIG/BOOT и фактический UDP/STUN, двусторонний MEDIA/CALL тест. Старый `v0.5.0_3` и `misconfigured / unknown-repository` не являются проверкой новой ветки. Без merge/stable до согласованных результатов.

Для каждого требования отдельно фиксируются **source implemented**, **CI/package verified**, **owner-live confirmed**. Новую разработку начинать только после проверки production entrypoint и конкретного отсутствующего/сломавшегося поведения. Точная очередь — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [ledger](history/current/v0.5.x.md).
