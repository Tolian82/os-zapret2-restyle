# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: закончить полный код пяти сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), затем одна testing-поставка и живые испытания. База разработки `v0.5.2_185`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза.

## Реализовано в коде (не равно live PASS)

| Поведение | Источник проверки |
|---|---|
| Пять Voice-профилей, IPv4 IPSET, native Config и stale snapshots | `VoiceController.php`, `SettingsApply.php`, `test-voice-gui-contract.py` |
| Один генератор полного Voice+Strategies runtime | `backend/orchestrator.sh`, `test-voice-common-runtime.py` |
| Соответствие STUN/UDP/ports/WAN/IPSET/divert/IPFW | `voice_ipfw_adapter._verify_shared_voice_engine` |
| Один FD9 Apply обеих страниц, Config save/error handling | `zapret_service.sh`, `apply_runtime.sh`, `test-shared-apply-{run,execute}.sh` |
| Normal Stop/Start/boot, verified GUI status/IPFW rule/counters | `zapret_service.sh`, `voice.volt`, `test-shared-apply-{stop,boot}.sh` |

Повторная разработка этих функций запрещена без воспроизводимого нового дефекта. Автоматическая проверка не доказывает STUN/MEDIA/CALL.

## Открытые границы перед testing package

1. **Квалификация CI/FreeBSD:** `_180` HEAD `a5a1b16` [CI #38907807528](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38907807528) — Voice, Project, FreeBSD 15 **PASS**; testing package contract — PASS. `_181` HEAD `3405301` [CI #38913309729](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38913309729) полностью прошла Voice, Project, FreeBSD 15 и delivery contract. `_182` HEAD `10e9652` [CI #38920675327](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38920675327) прошла Voice, Project, FreeBSD 15 и testing contract. `_183` HEAD `c14a214` [CI #38924849815](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38924849815) Voice/Project/FreeBSD 15 PASS. `_184` исправила API-level ложное `ready/stopped`, Voice CI PASS, Project CI указала на устаревшую PHP concurrency фикстуру. `_185` обновляет её для fail-closed API статуса, требует собственной Voice/Project/FreeBSD 15 exact-HEAD квалификации. Автотесты не доказывают реальный звонок.
2. **Этап 6 — удаление дублирования:** `_168–_180` убрали PoC marker, legacy migrations, rollback, отдельный IPFW/процессный Python-граф и 95 файлов с тестами; `_181` завершила удаление неиспользуемого частного process shell, подтверждённое CI и проверкой FreeBSD-пакета. Этап 6 закрыт на уровне кода и поставки, не owner-live. Не возвращать восстановление старого Telegram PoC.
3. **Миграция:** миграция работающего Phase-B и old marker больше не входит в ТЗ разработки: чистый native Voice + Strategies Config/Apply baseline. Обновить guards, не тратить время на backwards compatibility.
4. **Owner-live:** после завершения кода/сборки проверить GUI/CONFIG/BOOT и WAN UDP/STUN; MEDIA/CALL остаются самостоятельными испытаниями. TCP parent/TNAS/Docker не входят в plugin.

После кодовой готовности — одна GitHub testing-поставка, затем owner-live. Не делать stable или merge преждевременно. Для каждого пункта различать **source implemented**, **CI/package verified** и **owner-live confirmed**.

Точное действие — [START_HERE](START_HERE.md); факты — [PROJECT_STATE](PROJECT_STATE.md); хронология — [ledger](history/current/v0.5.x.md).
