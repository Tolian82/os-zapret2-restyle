# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.6_1`. `VERSION=0.5.6`, `PLUGIN_REVISION=1`. Текущее изменение — только документация; опубликованный пакет остаётся прежним.

## Текущая задача — подробный план модернизации Strategy Lab

Предварительный план преобразован в [подробный план разработки](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) после проверки производственных путей лаборатории, `ugorur/os-zapret2` и `lexiforest/curl-impersonate`. В [ТЗ](REQUIREMENTS.md) явно определены конечный результат и требования `BH-01`–`BH-12`. План содержит шесть последовательных этапов, точки изменения кода, критерии завершения и минимальную матрицу доказательств.

Владелец согласовал штатное согласование TLS выбранного Chrome-профиля; положительную оценку HTTP/1.1 наравне с HTTP/2; завершение поиска без HTTP/3, когда основной HTTPS доступен напрямую. Принудительная TLS 1.2 остаётся отдельной проверкой Extended. Эти решения больше не являются открытыми вопросами.

**Граница:** код, клиент внутри pkg и новые HTTP3-проверки ещё не реализованы. Аудит исходников не является приёмкой установленного пакета. Состояние реализации и предыдущей поставки — в [PROJECT_STATE](PROJECT_STATE.md).

## Единственное следующее действие

**После отдельной команды владельца начать реализацию этапа 1 подробного плана: включить готовый FreeBSD `curl-impersonate` в приватную поставку плагина и зафиксировать один поддерживаемый Chrome-профиль.** При начале нового этапа применить текущие правила версии; эта документационная запись сохраняет `v0.5.6_1`. Повторное согласование уже принятых HTTP/TLS решений не требуется.

Результат этапа 1: клиент и лицензии входят в pkg, известны версия/ABI/SHA-256/профиль, в целевой FreeBSD среде выполнены реальные HTTPS и HTTP3 GET. Исходники лаборатории переключаются сквозным этапом 2. Полный Web/pkg-релиз не назначен.

## Минимальное чтение по этапу

1. [REQUIREMENTS](REQUIREMENTS.md) — разделы Strategy Lab и `BH-01`–`BH-12`.
2. [Подробный план](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) — аудит, технические решения и этап 1.
3. Для изменения поиска: [основная архитектура](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [adaptive search](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [budgets](architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).
4. Для Extended/результатов: [QUIC control](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [unified shortlist](architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md), [прежняя live-матрица](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

## Сохранённые границы

- Полный [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; GitHub/FreeBSD15/Pages проверены, установка `0.5.6_1` через GUI владельцем не подтверждена. Это не блокирует документационную работу. [Запись публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Telegram Voice-исследования закрыты владельцем с отрицательным результатом в его прямом тракте. Новые звонки, STUN/capture, TTL/fake и маршрутные опыты не входят в текущую работу. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).
