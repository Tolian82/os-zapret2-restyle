# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_153`. `VERSION=0.5.2`; `PLUGIN_REVISION=153`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: сначала завершить полный код по ТЗ, затем одну testing-поставку и живые испытания. **Без релиза и установки на OPNsense**.

## Проверенная реализация

Уже реализованы, не разрабатывать заново: пять Voice-сервисов с общими IPv4 IPSET; Voice+Strategies в одном `traffic.conf`/`dvtws.args` через `orchestrator_build_release`; проверка STUN/UDP/WAN/IPSET/divert/IPFW; общий FD9/Config Apply обеих страниц, Start/Stop/boot и read-only GUI inspector с реальным номером IPFW-правила/счётчиками. Source/CI не подтверждают owner-live GUI/CONFIG/BOOT, STUN/MEDIA/CALL.

**Предыдущий HEAD `_152`** — `70547df`, [CI #38784711559](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38784711559): Validate Project и FreeBSD 15 package **успешны**, Validate Voice candidates **ошибка** старого теста `test-voice-native-prepare-route.py`, ожидавшего уже удалённую shell-команду. Testing-package delivery contract и проверка названия PR были успешны.

## Точная следующая граница

**Изменение `_153` (этап 6):** старый Python `voice_native_prepare_route.py` больше не поддерживает `prepare-from-draft-and-apply` или `apply_continuously`, и не вызывает private COMMIT. `voice_native_apply_route.py` теперь отвергает `execute-prepared` при прямом CLI-запуске; внутренний код старой миграции/аварийных свидетелей пока сохранён. Актуализированы старые тесты: PREPARED без запуска и fail-closed отказ старого CLI. Штатный общий Voice/Strategies Apply и его frontend не менялись.

**Следующее действие:** получить **полный CI и FreeBSD 15** на новом HEAD `_153`; по конкретным ошибкам исправлять только соответствующий contract. Затем продолжить этап 6 с проверяемым списком реальных callers/imports/installable files: удалить неиспользуемые private модули без обрезания нужной Phase-B миграции. Не переходить к testing release, пока кодовые границы ТЗ не закрыты.

## Минимальное чтение

После AGENTS и Level-1 rule books: [контроль завершения](VOICE_CODE_COMPLETION_GATE.md), [план этапов 6–7](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [ТЗ и утверждённый раздел 12](architecture/VOICE_TRANSMISSION_GUI.md). Durable facts — [PROJECT_STATE](PROJECT_STATE.md), хронология — [working ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_153` не опубликована.
