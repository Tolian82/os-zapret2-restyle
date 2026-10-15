# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_157`. `VERSION=0.5.2`; `PLUGIN_REVISION=157`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: завершить функциональный код неизменного ТЗ пяти Voice-сервисов, затем **одна testing-поставка** и owner-live испытания. До тех пор без релиза и установки на OPNsense.

## Последняя квалификация

**`_156` HEAD `5ce7c49` — полный [CI #38795297308](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38795297308) SUCCESS:** Validate Voice candidates, Validate Project и FreeBSD 15 package (с отсутствием трёх old private файлов); PR title и Testing package delivery contract SUCCESS. Это source/package qualification, а не подтверждение живых STUN/MEDIA/CALL.

Уже реализовано: один общий Voice+Strategies full runtime/`dvtws2`, пять профилей с managed IPv4 IPSET, scoped STUN/UDP/WAN/IPFW, единый native FD9/Config Apply, обычные Start/Stop/boot, read-only status/rules/counters. Без доказанного дефекта эти функции не переписывать.

## Текущее изменение и следующий шаг

**`_157`, этап 6 — actual source deletion:** после исключения из package и подтверждения полного CI удалены устаревшие `voice_native_apply_route.py` и `voice_native_forward_apply.py` из source tree, плюс только два привязанных к ним старых mutating test suites. Отдельные проверки old executor повторного rollback из boot-теста удалены, но реальная read-only boot/recovery диагностика, sealed PREPARED witness и тесты целостности сохранены. `scripts/build-pkg.sh` больше не ищет удалённые исходники; FreeBSD tar check по-прежнему запрещает их появление. Старый PREPARED operator source остаётся только для source-level tests и исключён из package.

**Точное следующее действие:** проверить полный Voice/Project/FreeBSD CI на HEAD `_157`, затем продолжить карту использующихся и неиспользуемых legacy modules; удалять только по точным inbound callers, сохранить необходимую migration/read-only диагностику. После завершения функционального ТЗ — одна testing-поставка, не сейчас.

## Минимальное чтение

После `AGENTS.md` и rule books: [completion gate](VOICE_CODE_COMPLETION_GATE.md), [план этапов](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), [ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_157` не опубликована.
