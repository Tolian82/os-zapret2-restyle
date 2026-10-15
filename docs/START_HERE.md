# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_158`. `VERSION=0.5.2`; `PLUGIN_REVISION=158`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: закончить функциональный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live. Без релиза и установки на OPNsense.

## Последняя квалификация

`_157` HEAD `6b4efcf` полностью прошёл [CI #38797108434](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38797108434): Validate Voice candidates, Validate Project и Build FreeBSD 15 package — SUCCESS. PR title и testing delivery contract тоже PASS. Это не подтверждает реальные STUN/MEDIA/CALL.

Уже реализованы: общий Voice+Strategies runtime/`dvtws2`, пять профилей, managed IPv4 IPSET, scoped STUN/UDP/WAN/IPFW, единый FD9/Config Apply, normal Stop/Start/boot и read-only GUI status/rules/counters. Не повторять без воспроизводимого дефекта.

## Текущий рубеж этапа 6

`_158`: после caller-аудита удалены source-only old `voice_native_prepare_route.py`, два его private shell workers `voice_native_render_saved.sh` и `voice_native_build_release.sh`, плюс две operator-specific тестовые матрицы. Действующие миграционные witnesses и общий Voice/Strategies Apply не изменены. Сборщик больше не удаляет несуществующий Prepare route; FreeBSD CI по-прежнему запрещает все retired paths в package tar.

**Точное следующее действие:** проверить Voice/Project/FreeBSD CI на HEAD `_158`, затем продолжить адресный keep/fold/delete по фактическим legacy caller-цепочкам. Testing package после полного кодового завершения, не сейчас.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План этапов](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_158` ещё не опубликована.
