# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_2`. `VERSION=0.5.2`; `PLUGIN_REVISION=2`. Линия состояния — `v0.5.x`. 13.10.2026 владелец поручил открыть новый этап общего Voice/Strategies backend без релиза и перенести старые отчёты из активной документации в историю.

## Текущая граница

Владелец поручил начать программирование согласно плану; семь этапов и контроль приняты к выполнению. В ревизии `_2` этап 1 подключает все пять Voice-сервисов к основным `traffic.conf` и `dvtws.args` общего candidate build. Ordinary/non-STUN, один divert, shared IPSET и числовые ordinary ports сохраняются; old marker/prepend не управляет новой сборкой. Проверка пересечений допускает доказанно раздельные ordinary STUN scopes.

Candidate build сам не запускает процессы, не меняет live Config/IPFW и не включает GUI Apply. При наличии installed engine его `--dry-run` проверяет параметры/файлы с candidate paths, без проверки Lua execution. Linux/FreeBSD CI включает полный common-runtime сценарий. PR #328 Draft; frontend и ТЗ не меняются.

## Следующее действие

**Этап 2 — общий firewall для пяти таблиц/правил, обновления, владения и отката.** Использовать полученный `voice-plan.json` и существующий firewall/adapter. Затем этап 3 — общий Apply обеих страниц. Не возвращаться к прежней private очереди WAL/receipt и не создавать отдельный Voice lifecycle.

## Минимальное чтение по текущей задаче

После обязательного порядка AGENTS читать только:

1. [План v0.5.2](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) — компоненты, этапы, проверки и контроль выполнения.
2. [ТЗ страницы](architecture/VOICE_TRANSMISSION_GUI.md), включая утверждённый раздел 12.
3. [ARCHITECTURE](ARCHITECTURE.md) — существующие общие точки интеграции; [Service architecture](architecture/ZAPRET2_SERVICE.md) при работе с сервисным API.

Для конкретного изменения затем читать соответствующие исходники и проверки. Исторические private модули и lab runbooks загружаются по доказанной необходимости текущего сценария, не всем списком.

## Контроль продолжения

Результат каждого этапа и необходимые проверки определены в [разделе 6 плана](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md#6-проверки-и-управление-разработкой). Контроль принят вместе с поручением на реализацию. Отчёт содержит результат ТЗ, изменённый код, проверку, остаточный риск и следующий шаг. Счётчики строк/тестов и новый helper не заменяют функциональный рубеж.

## История и публикация

Полные прежние документы сохранены в [архиве этапа v0.5.1](history/stages/v0.5.1/README.md). Они не входят в текущую очередь или обязательное чтение. Текущая хронология — [working ledger v0.5.x](history/current/v0.5.x.md).

Stable Web/pkg: `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`; опубликованный testing: `v0.5.0_3`. Открытие `v0.5.2_2` не публикует новый пакет и не подтверждает GUI/CONFIG/BOOT или MEDIA_PASS/CALL_PASS.
