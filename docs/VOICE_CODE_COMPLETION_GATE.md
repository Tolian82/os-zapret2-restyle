# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: закончить полный код пяти сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), затем одна testing-поставка и живые испытания. База разработки `v0.5.2_167`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза.

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

1. **CI/FreeBSD:** `_166` HEAD `8746aee` успешно прошёл Voice/Project/FreeBSD 15 ([CI #38827533621](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38827533621)). `_167` требует отдельного latest-head PASS, включая FreeBSD package и сохранённый исторический redo reader.
2. **Этап 6:** `_152–_167` удалили старые private forward mutators. `_167` превращает `voice_native_forward_runtime.py` в read-only validator исторического sealed marker и сохраняет `voice_cutover_file_rollback` recovery. Удалённый writer не был частью штатного Apply. Дальше только реальная карта оставшихся legacy entrypoints и содержимое пакета, не расширять восстановление.
3. **Миграция:** работающий Phase-B блокирует автоматическое native переключение до отдельной проверенной миграции. Чистая установка, старый marker и OFF имеют разные критерии.
4. **Owner-live:** после завершения кода/сборки проверить GUI/CONFIG/BOOT и WAN UDP/STUN; MEDIA/CALL остаются самостоятельными испытаниями. TCP parent/TNAS/Docker не входят в plugin.

После кодовой готовности — одна GitHub testing-поставка, затем owner-live. Не делать stable или merge преждевременно. Для каждого пункта различать **source implemented**, **CI/package verified** и **owner-live confirmed**.

Точное действие — [START_HERE](START_HERE.md); факты — [PROJECT_STATE](PROJECT_STATE.md); хронология — [ledger](history/current/v0.5.x.md).
