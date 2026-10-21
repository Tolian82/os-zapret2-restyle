# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.6_1`. `VERSION=0.5.6`, `PLUGIN_REVISION=1`. Изменение только документационное; опубликованный пакет остаётся прежним.

## Текущая задача — подробный план модернизации Strategy Lab

Утверждённый [подробный план разработки](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) и [ТЗ](REQUIREMENTS.md) (`BH-01`–`BH-12`) скорректированы 21.10.2026 по новой инструкции владельца. **Одного доказанного TLS- или QUIC-handshake с целевым endpoint достаточно для положительной доступности; прикладной HTTP-ответ/HTTP3 GET не обязателен.** HTTP-измерения, если есть, остаются отдельной диагностикой. Шесть этапов, схема Python/Model C, атрибуция, ранний выход и восстановление сохранены.

Владелец сохраняет равноправие HTTP/1.1 и HTTP/2 (если наблюдаются), штатное согласование TLS Chrome и пропуск QUIC после успешного прямого HTTPS TLS-handshake. Принудительная TLS 1.2 — отдельная ветка Extended. **На каждой новой сборке берём доступный пакет FreeBSD `latest` по схеме ugorur, ориентируясь на upstream lexiforest, без закрепления или отбора по версии**; один поддерживаемый Chrome-профиль выбирается из фактического бинарника. Повторное согласование этих пунктов не требуется.

**Граница:** код, клиент внутри pkg и новые HTTP3-проверки ещё не реализованы. Аудит исходников не является приёмкой установленного пакета. Состояние реализации и предыдущей поставки — в [PROJECT_STATE](PROJECT_STATE.md).

## Единственное следующее действие

**После отдельной команды владельца начать реализацию этапа 1: включить готовый FreeBSD `latest` curl-impersonate в приватную поставку плагина, выбрать один реально поддерживаемый Chrome-профиль, проверить целевые TLS/QUIC-handshake.** При начале нового этапа применять действующие правила версии; эта документационная запись сохраняет `v0.5.6_1`. Уже утверждённые критерии не переоткрывать.

Результат этапа 1: клиент и лицензии внутри pkg, фактическая исполняемость, CA, профиль, SHA-256 конечного пакета и реальные TLS/QUIC-handshake на FreeBSD 15. **Версия внешнего curl-impersonate не закрепляется и не проверяется как условие допуска; HTTP-ответ необязателен.** Сквозной переход исходников — этап 2. Полный Web/pkg-релиз не назначен.

## Минимальное чтение по этапу

1. [REQUIREMENTS](REQUIREMENTS.md) — разделы Strategy Lab и `BH-01`–`BH-12`.
2. [Подробный план](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) — аудит, технические решения и этап 1.
3. Для изменения поиска: [основная архитектура](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [adaptive search](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [budgets](architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).
4. Для Extended/результатов: [QUIC control](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [unified shortlist](architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md), [прежняя live-матрица](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

## Сохранённые границы

- Полный [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; GitHub/FreeBSD15/Pages проверены, установка `0.5.6_1` через GUI владельцем не подтверждена. Это не блокирует документационную работу. [Запись публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Telegram Voice-исследования закрыты владельцем с отрицательным результатом в его прямом тракте. Новые звонки, STUN/capture, TTL/fake и маршрутные опыты не входят в текущую работу. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).
