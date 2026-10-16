# «Передача голоса» — контроль завершения без преждевременного релиза

Актуальное решение владельца 16.10.2026: закончить полный код пяти сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), затем **полноценный релиз**, и только после него живые испытания. База разработки `v0.5.2_191`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза.

## Реализовано в коде (не равно live PASS)

| Поведение | Источник проверки |
|---|---|
| Пять Voice-профилей, IPv4 IPSET, native Config и stale snapshots | `VoiceController.php`, `SettingsApply.php`, `test-voice-gui-contract.py` |
| Один генератор полного Voice+Strategies runtime | `backend/orchestrator.sh`, `test-voice-common-runtime.py` |
| Соответствие STUN/UDP/ports/WAN/IPSET/divert/IPFW | `voice_ipfw_adapter._verify_shared_voice_engine` |
| Один FD9 Apply обеих страниц, Config save/error handling | `zapret_service.sh`, `apply_runtime.sh`, `test-shared-apply-{run,execute}.sh` |
| Normal Stop/Start/boot, verified GUI status/IPFW rule/counters | `zapret_service.sh`, `voice.volt`, `test-shared-apply-{stop,boot}.sh` |

Повторная разработка этих функций запрещена без воспроизводимого нового дефекта. Автоматическая проверка не доказывает STUN/MEDIA/CALL.

## Открытые границы перед полноценным релизом

1. **Exact-HEAD CI/FreeBSD:** `_190` HEAD `0fe4f11` [CI #38946969246](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38946969246) **Voice/Project/FreeBSD 15 PASS**, [delivery contract](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38946969196) PASS. `_191` устраняет ложный retry на второй странице общего Apply при post-dispatch exception/AJAX timeout, повторяет имеющиеся PHP safety checks для Strategies; собственная exact-HEAD квалификация требуется до релиза.
2. **Этап 6 — удаление дублирования:** `_168–_180` убрали PoC marker, legacy migrations, rollback, отдельный IPFW/процессный Python-граф и 95 файлов с тестами; `_181` завершила удаление неиспользуемого частного process shell, подтверждённое CI и проверкой FreeBSD-пакета. Этап 6 закрыт на уровне кода и поставки, не owner-live. Не возвращать восстановление старого Telegram PoC.
3. **Миграция:** миграция работающего Phase-B и old marker больше не входит в ТЗ разработки: чистый native Voice + Strategies Config/Apply baseline. Обновить guards, не тратить время на backwards compatibility.
4. **Owner-live после релиза:** после публикации полноценного установочного релиза проверить GUI/CONFIG/BOOT и WAN UDP/STUN; MEDIA/CALL остаются самостоятельными испытаниями. TCP parent/TNAS/Docker не входят в plugin.

После кодовой готовности — один полноценный релиз с проверкой README/пакетного репозитория по GH-039–GH-052, затем owner-live. Не выпускать незавершённый или известный критически неисправный пакет; промежуточных live-тестов до релиза нет. Для каждого пункта различать **source implemented**, **CI/package verified** и **owner-live confirmed**.

Точное действие — [START_HERE](START_HERE.md); факты — [PROJECT_STATE](PROJECT_STATE.md); хронология — [ledger](history/current/v0.5.x.md).
