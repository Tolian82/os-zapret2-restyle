# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: закончить полный код пяти сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), затем одна testing-поставка и живые испытания. База разработки `v0.5.2_165`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза.

## Реализовано в коде (не равно live PASS)

| Поведение | Источник проверки |
|---|---|
| Пять Voice-профилей, IPv4 IPSET, native Config и stale snapshots | `VoiceController.php`, `SettingsApply.php`, `test-voice-gui-contract.py` |
| Один генератор полного Voice+Strategies runtime | `backend/orchestrator.sh`, `test-voice-common-runtime.py` |
| Соответствие STUN/UDP/ports/WAN/IPSET/divert/IPFW | `voice_ipfw_adapter._verify_shared_voice_engine` |
| Один FD9 Apply обеих страниц, Config save/rollback | `zapret_service.sh`, `apply_runtime.sh`, `test-shared-apply-{run,execute}.sh` |
| Normal Stop/Start/boot, verified GUI status/IPFW rule/counters | `zapret_service.sh`, `voice.volt`, `test-shared-apply-{stop,boot}.sh` |

Повторная разработка этих функций запрещена без воспроизводимого нового дефекта. Автоматическая проверка не доказывает STUN/MEDIA/CALL.

## Открытые границы перед testing package

1. **CI/FreeBSD:** `_164` HEAD `2622d4b` полностью прошёл Voice, Project и FreeBSD 15 ([CI #38813372416](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38813372416)). Для `_165` нужна отдельная проверка exact HEAD и отсутствие old candidate engine executor в package.
2. **Этап 6:** `_152–_165` устраняют независимые PREPARED/Config/IPFW/supervisor/candidate engine executors. `_165` заменяет запуск старого engine в тестовой подготовке на sealed schema-4 journal и штатный `voice_ipfw_runtime.activate_verified`; common Apply и previous rollback не изменены. Далее старый forward Stop оценивать только по реальным зависимостям.
3. **Миграция:** работающий Phase-B блокирует автоматическое native переключение до отдельной проверенной миграции. Чистая установка, старый marker и OFF имеют разные критерии.
4. **Owner-live:** после завершения кода/сборки проверить GUI/CONFIG/BOOT и WAN UDP/STUN; MEDIA/CALL остаются самостоятельными испытаниями. TCP parent/TNAS/Docker не входят в plugin.

После кодовой готовности — одна GitHub testing-поставка, затем owner-live. Не делать stable или merge преждевременно. Для каждого пункта различать **source implemented**, **CI/package verified** и **owner-live confirmed**.

Точное действие — [START_HERE](START_HERE.md); факты — [PROJECT_STATE](PROJECT_STATE.md); хронология — [ledger](history/current/v0.5.x.md).
