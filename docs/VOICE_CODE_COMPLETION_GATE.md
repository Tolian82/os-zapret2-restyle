# «Передача голоса» — контроль завершения без преждевременного релиза

Решение владельца 15.10.2026: закончить полный код пяти сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), затем одна testing-поставка и живые испытания. База разработки `v0.5.2_179`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), без релиза.

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

1. **CI/FreeBSD:** `_167` HEAD `eb2518e` прошёл [CI #38840666241](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38840666241) и FreeBSD testing contract. `_168` прошла [CI #38866582677](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38866582677); `_169` выявила два несоответствия проверки ([CI #38872692193](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38872692193)), исправленные в `_170`. `_170` [CI #38872971857](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38872971857) выявила устаревшее требование boot test к PoC marker/table; `_171` исправляет его; Voice CI PASS, но Project CI FAIL из-за трёх битых исторических ссылок. В `_172` ссылки исправлены и продакшен preflight перенесён на shared-only native-gate; `_172` CI обнаружила старую тестовую фикстуру. `_173` удаляет эти тестовые зависимости и отменённые `legacy-*` journal API; `_173` успешно прошла [CI #38900822687](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38900822687) (Voice, Project, FreeBSD 15). `_174` удаляет private status fallback. `_175` переподключает read-only lifecycle/candidate router к одному shared Apply owner; `_176` отвязала GUI preview от старой миграционной инфраструктуры; [CI #38904110487](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38904110487) Voice, Project, FreeBSD 15 PASS. `_177` удаляет старый Telegram cutover/private recovery код и тесты целиком, `_177` выявила устаревшие заглушки общего Apply в Voice CI; `_178` убирает их, `_178` выявила старые фикстуры saved/activated recovery; `_179` исправляет их и требует полной CI/FreeBSD квалификации.
2. **Этап 6 — новое решение владельца 16.10.2026:** не сохранять ни один старый Telegram PoC restore/migration protocol, пять доменов WAL/receipt, ручной откат или тесты такого отката. `_168` удаляет большой private legacy stack, связанные интерфейсы и GUI панель; `_169` удаляет Phase-B prepend и отдельный marker/IPFW; в `_177` удалить `voice_cutover_*` и зависимые private readers/guards, затем подтвердить отсутствие в пакете. Приёмка — один работающий backend и отсутствие заброшенных входов, а не корректное возвращение в старое состояние.
3. **Миграция:** миграция работающего Phase-B и old marker больше не входит в ТЗ разработки: чистый native Voice + Strategies Config/Apply baseline. Обновить guards, не тратить время на backwards compatibility.
4. **Owner-live:** после завершения кода/сборки проверить GUI/CONFIG/BOOT и WAN UDP/STUN; MEDIA/CALL остаются самостоятельными испытаниями. TCP parent/TNAS/Docker не входят в plugin.

После кодовой готовности — одна GitHub testing-поставка, затем owner-live. Не делать stable или merge преждевременно. Для каждого пункта различать **source implemented**, **CI/package verified** и **owner-live confirmed**.

Точное действие — [START_HERE](START_HERE.md); факты — [PROJECT_STATE](PROJECT_STATE.md); хронология — [ledger](history/current/v0.5.x.md).
