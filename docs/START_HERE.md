# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_161`. `VERSION=0.5.2`; `PLUGIN_REVISION=161`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца: завершить программный код пяти Voice-сервисов по неизменному ТЗ, затем одна testing-поставка и owner-live испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_160` HEAD `5c54aba`, [CI #38804868113](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38804868113) — **PASS** Voice candidates, Validate Project и Build FreeBSD 15 package; PR title и testing delivery contract — PASS. Это CI/package qualification, не проверка STUN/MEDIA/CALL на устройстве.

Реализованы: один общий Voice+Strategies runtime/`dvtws2`, пять профилей с managed IPv4 IPSET, scoped STUN/UDP/WAN/IPFW, общий native FD9/Config Apply, normal Start/Stop/boot и read-only GUI status/rules/counters. Не развивать параллельную реализацию без воспроизводимого дефекта.

## Текущий участок: этап 6

**`_161`:** удалён больше не вызываемый из production `voice_native_forward_prepare.py` (old schema-4 PREPARED executor). Исторический файл `scripts/test-voice-native-forward-prepare.py` остаётся **только фикстурой** для проверок downstream forward Stop/IPFW/supervisor/Config и подготавливает настоящий schema-4 journal через уже существующий `VoiceCutoverJournal.begin_runtime_bound` с оригинальным Config flock. Его отдельные тесты отменённого PREPARED протокола и CI-step удалены. FreeBSD tar guard запрещает старый executable module; общий FD9 Apply, миграция, read-only preview не изменены.

**Следующее действие:** подтвердить полную матрицу Voice, Project, FreeBSD package на `_161`; при конкретных ошибках фикстуры исправить её в этой же ревизии. Далее закрывать только доказанные незавершённые требования по ТЗ — без циклического расширения recovery. Не делать testing release раньше кодовой готовности.

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_161` не опубликована.
