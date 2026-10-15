# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: сначала закончить код, затем **одна** testing поставка и живые испытания. Действующая база `v0.5.2_144` в [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза. GUI/ТЗ не менять.

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

1. **CI:** HEAD `39f771f` (`_143`) прошёл Validate Project, Voice candidates и FreeBSD 15 package build (Actions `38747912361`). Для `_144` требуется отдельный полный CI с проверкой пяти XML tooltip и действующего RU/EN Apply; старый PASS не переносится.
2. **FreeBSD:** получить успешную реальную package-сборку для `_144`; `_143` уже был SUCCESS, но не доказывает новый HEAD.
3. **Legacy PoC:** старые enable/disable ограждены от native owner, ordinary больше не создаёт инертный bundle. Generic status committed Voice/Strategies использует строгий read-only native inspector, настоящий legacy сохраняет прежний статус. Пакетные rollback/migration файлы не удалять без доказанной безопасной миграции.
4. **Финальная приёмка кода:** пять XML checkbox и info подсказок уже исправлены для Validate / OFF draft / native Apply; существующий RU/EN view согласован. Проверить только оставшиеся реальные GUI/API → Config → generator/IPFW → Apply → Stop/Start/boot и состав пакета, исправляя конкретные разрывы.

После фактического закрытия — «код готов к испытаниям», **не** `MEDIA_PASS/CALL_PASS`.

## После кодовой готовности

Одна согласованная GitHub testing поставка, затем OPNsense GUI/CONFIG/BOOT и фактический UDP/STUN, двусторонний MEDIA/CALL тест. Старый `v0.5.0_3` и `misconfigured / unknown-repository` не являются проверкой новой ветки. Без merge/stable до согласованных результатов.

Для каждого требования отдельно фиксируются **source implemented**, **CI/package verified**, **owner-live confirmed**. Новую разработку начинать только после проверки production entrypoint и конкретного отсутствующего/сломавшегося поведения. Точная очередь — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [ledger](history/current/v0.5.x.md).
