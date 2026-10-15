# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: закончить полный код пяти сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), затем одна testing-поставка и живые испытания. База разработки `v0.5.2_153`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза.

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

1. **CI/FreeBSD:** `_152` HEAD `70547df` подтвердил Validate Project и FreeBSD 15 package, но Voice candidates упал в оставшемся старом утверждении о CLI ([Actions #38784711559](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38784711559)). `_153` обновляет этот contract и убирает Python-маршрут private COMMIT. Для `_153` нужны **свои три** подтверждённые проверки; до их завершения общий успех не объявлять.
2. **Этап 6:** Telegram enable/disable/status уже идут через native Config/FD9/Apply/inspect. `_152–_153` удалили два old mutating shell CLI маршрута и закрыли соответствующие Python entrypoints `prepare-from-draft-and-apply`/`execute-prepared`. PREPARED остаётся изолированной исторической подготовкой без COMMIT. Остальные старые Python cutover modules и package content требуют inventory callers/keep/transition/delete, сохраняя необходимые аварийные гарантии.
3. **Миграция:** работающий Phase-B блокирует автоматическое native переключение до отдельной проверенной миграции. Чистая установка, старый marker и OFF имеют разные критерии.
4. **Owner-live:** после завершения кода/сборки проверить GUI/CONFIG/BOOT и WAN UDP/STUN; MEDIA/CALL остаются самостоятельными испытаниями. TCP parent/TNAS/Docker не входят в plugin.

После кодовой готовности — одна GitHub testing-поставка, затем owner-live. Не делать stable или merge преждевременно. Для каждого пункта различать **source implemented**, **CI/package verified** и **owner-live confirmed**.

Точное действие — [START_HERE](START_HERE.md); факты — [PROJECT_STATE](PROJECT_STATE.md); хронология — [ledger](history/current/v0.5.x.md).
