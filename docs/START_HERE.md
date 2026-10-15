# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_152`. `VERSION=0.5.2`; `PLUGIN_REVISION=152`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: сначала завершить полный код по ТЗ, затем одну testing-поставку и живые испытания. Пока **без релиза и установки на OPNsense**.

## Доказанные факты

Уже реализованы, **не делать повторно**: пять native Voice профилей/общие IPv4 IPSET, полный Voice+Strategies `traffic.conf` и `dvtws.args` через `orchestrator_build_release`, STUN/UDP/WAN/IPSET/divert/IPFW сверка через `voice_ipfw_adapter._verify_shared_voice_engine`, единый FD9/Config Apply двух страниц, normal Start/Stop/boot, read-only GUI inspector с per-service IPFW rule/counters.

**Последний квалифицированный HEAD:** `_151`, `688d291`, [Actions #38780979267](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38780979267) — Validate Project, Validate Voice candidates и Build FreeBSD 15 package **успешны**. Это CI/сборка, не owner-live GUI/CONFIG/BOOT, STUN/MEDIA/CALL PASS.

## Точный следующий шаг

**В `_152` начат этап 6:** устранены два old mutating private Voice CLI маршрута — `native-voice-apply-prepared` и `native-voice-prepare-apply-draft` — и их прямой service helper. Штатный `shared-apply-run`, Telegram compatibility, read-only inspect и миграционные/аварийные механизмы не менялись. Существующие тесты теперь запрещают эти два CLI пути.

**Далее:** подтвердить полный CI и FreeBSD 15 **именно для `_152`**, затем инвентаризировать остальные старые CLI/boot/configd entrypoints и устанавливаемые файлы с доказанным keep/transition/delete. Не считать весь old framework удалённым и не расширять recovery.

## Минимальное чтение

После AGENTS и Level-1 rule books: [контроль завершения](VOICE_CODE_COMPLETION_GATE.md), [план, этапы 6–7](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [утверждённое ТЗ](architecture/VOICE_TRANSMISSION_GUI.md). [Текущее состояние](PROJECT_STATE.md); [история](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_152` пока не опубликована.
