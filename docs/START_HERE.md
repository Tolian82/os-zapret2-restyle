# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_1`. `VERSION=0.5.2`; `PLUGIN_REVISION=1`. Линия состояния — `v0.5.x`. 13.10.2026 владелец поручил открыть новый этап общего Voice/Strategies backend без релиза и перенести старые отчёты из активной документации в историю.

## Текущая граница

- Обновлены только версия/ревизия и документация. Работающий appliance, package repository, теги и релизы не меняются.
- PR [#328](https://github.com/Tolian82/os-zapret2-restyle/pull/328) остаётся Draft в существующей feature branch. Имя ветки с `v0.5.1_1` — историческое имя этой незавершённой работы; текущую версию определяют VERSION/Makefile.
- Архитектура общего backend утверждена; [подробный план](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) и контроль перенесены в этап `v0.5.2`. Продуктовый backend ещё не переделан, критерии его этапов не закрыты.
- Фронтэнд, пять сервисов и полное [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) сохранены. Одиночный STUN-профиль не является сокращённым результатом.

## Следующее действие

Обсудить и утвердить подробный проект плана кодовых изменений, уже подготовленный в предыдущей задаче. Перенос версии не объявляет технические решения плана реализованными. Первое кодовое задание после согласования — **этап 1: полный Voice-кандидат в общем генераторе**, включая все пять сервисов и ordinary Strategies.

Старая private очередь этапа 3/WAL/receipt не возобновляется. Не разрабатывать новый независимый Voice-владелец Config, firewall, процессов или boot.

## Минимальное чтение по текущей задаче

После обязательного порядка AGENTS читать только:

1. [План v0.5.2](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) — компоненты, этапы, проверки и контроль выполнения.
2. [ТЗ страницы](architecture/VOICE_TRANSMISSION_GUI.md), включая утверждённый раздел 12.
3. [ARCHITECTURE](ARCHITECTURE.md) — существующие общие точки интеграции; [Service architecture](architecture/ZAPRET2_SERVICE.md) при работе с сервисным API.

Для конкретного изменения затем читать соответствующие исходники и проверки. Исторические private модули и lab runbooks загружаются по доказанной необходимости текущего сценария, не всем списком.

## Контроль продолжения

Результат каждого этапа и необходимые проверки определены в [разделе 6 плана](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md#6-проверки-и-управление-разработкой). Контроль остаётся проектом для согласования вместе с планом. После его принятия отчёт содержит результат ТЗ, изменённый код, проверку, остаточный риск и следующий шаг. Счётчики строк/тестов и новый helper не заменяют функциональный рубеж.

## История и публикация

Полные прежние документы сохранены в [архиве этапа v0.5.1](history/stages/v0.5.1/README.md). Они не входят в текущую очередь или обязательное чтение. Текущая хронология — [working ledger v0.5.x](history/current/v0.5.x.md).

Stable Web/pkg: `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`; опубликованный testing: `v0.5.0_3`. Открытие `v0.5.2_1` не публикует новый пакет и не подтверждает GUI/CONFIG/BOOT или MEDIA_PASS/CALL_PASS.
