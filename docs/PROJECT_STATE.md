# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.6_1`**. Полный релиз опубликован; активное направление — подготовленная модернизация Strategy Lab через curl-impersonate. Код модернизации ещё не начат. Единственное следующее действие задаёт [START_HERE](START_HERE.md). State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Версия, пакет и граница доставки

- `VERSION=0.5.6`, `PLUGIN_REVISION=1`, package candidate: `os-zapret2-restyle-0.5.6_1.pkg`.
- Полный Web/pkg-релиз [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; immutable tag, pkg/SHA256SUMS и FreeBSD15 Pages/pkg deployment подтверждены. SHA-256 пакета: `9c4ba669ae0ac453bb59da37b240234b7b2c44b49482b88eb98c14108a3dc6fe`. [Доказательство публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Обновление владельцем через OPNsense GUI до `0.5.6_1` не подтверждено. Новое оформление ТЗ не меняет этот факт и не является новой сборкой.
- Поддерживаемая платформа: OPNsense 26.7 / FreeBSD 15 amd64, Python 3.13. Служба `zapret`, общий dvtws2/supervisor и native lifecycle сохраняются.

## Strategy Lab — текущий код и согласованное направление

Аудит выполнен по restyle `8b31fa49cfcf00617f3137b8eb7bc80427d1f19f` и зафиксированным исходникам двух upstream-проектов. [Карта интеграции и источники](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md).

**Реализовано в текущем исходном коде:** Python-планировщик, Model C как единственный нормальный production-путь, CandidateSpec/ResourceInventory, фиксированный endpoint epoch и source-port атрибуция, конечные бюджеты, отмена, Stage 90. Основной клиент пока обычный curl с HTTP/1.1/ограничением TLS; QUIC-кандидат пока проверяется handshake OpenSSL, а не HTTP3 GET. В Stage 80 есть четыре QUIC-кандидата; QUIC уже может быть источником Stage-85 результата. Ранний `TARGET_ACCESSIBLE` уже завершает задание до поиска/Extended.

**Согласовано, но ещё не реализовано:** конечный результат и требования `BH-01`–`BH-12` в [REQUIREMENTS](REQUIREMENTS.md), шесть этапов [подробного плана](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md). Принятые решения по HTTP/1.1, раннему пропуску HTTP/3 и штатному согласованию TLS окончательны для этого плана. Нового Python-планировщика, Firefox, обычного curl fallback и recovery-системы нет в объёме работ.

| Этап | Состояние |
| --- | --- |
| Аудит, уточнение требований и подробное планирование | Завершены на уровне документации |
| 1. Приватная поставка curl-impersonate | Не начат |
| 2. Сквозной основной HTTPS-поиск | Не начат |
| 3. Extended и HTTP3 GET | Не начат |
| 4. Расширение QUIC-каталога и допуск по бюджету | Не начат |
| 5. Результаты, GUI и сохранённые задания | Не начат |
| 6. Приёмка установленного пакета | Не начат |

Существующая [live-матрица](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md) сохраняет принятую функциональность прежней лаборатории: Model C, domain/IPv4 + Host/SNI, QUIC ON/OFF, Generic UDP, достоверные 4xx/5xx и восстановление. Она не доказывает ещё не реализованный Chrome/HTTP3 путь. Новая матрица и условия закрытия этапов находятся в подробном плане; результатов её выполнения пока нет.

## Сохранённые подтверждённые результаты остальных страниц

| Сценарий | Подтверждено | Граница доказательства |
| --- | --- | --- |
| Strategies Apply без изменений и с изменениями | Владелец принял на установленной `0.5.5_7` | Не доказывает поддержку редактирования очень больших списков; [evidence](verification/evidence/2026-10-20-v0.5.5_7-strategies-apply-owner-acceptance.md) |
| Voice Apply Telegram ON, общий runtime/IPFW | На `0.5.3_28`: journal committed, inspect ready, общий engine/supervisor, scoped IPFW | Подтверждает применение/перехват, не звонок; [evidence](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md) |
| Сохранность настроек Voice после обновления | Все значения сохранены при обновлении до `0.5.4_1` | Проверка конфигурации, не отдельная проверка reboot/runtime; [evidence](verification/evidence/2026-10-19-v0.5.4_1-voice-upgrade-config-persistence.md) |
| Размещение Voice-статусов и RU/EN меню | Владелец принял расположение при открытой/закрытой справке и переходы между страницами | UI-задачи закрыты; [evidence](verification/evidence/2026-10-19-v0.5.4_5-voice-ui-menu-owner-acceptance.md) |

Редактирование действительно больших списков по прежнему ограниченному транспортному конверту не принято как рабочий сценарий и не входит в текущую HTTP-модернизацию.

## Telegram Voice — закрытый результат исследований

Владелец завершил кампанию 20.10.2026. Через прямой тракт OPNsense доказаны исходящие original/fake UDP, но ответы рефлектора и рабочая медиасессия не получены: `MEDIA_PASS=false`, `CALL_PASS=false`. Контроли fake OFF и TTL7 не дали положительного результата; исходная Strategy #4 и проверенные временные маршруты восстановлены.

Положительный опыт через pfSense `.1.140` не является доказательством Zapret2-обхода того же прямого провайдера: обнаружены Telegram route через `ovpnc6`, NAT на VPN-адрес и первый traceroute hop `10.1.11.1`. Точный путь конкретной переадресованной сессии не подтверждён PCAP. GOST SOCKS UDP и OpenWrt STUN fake egress подтверждены отдельно, без доказанной Telegram-медиасессии. Точная причина отсутствия ответов на прямом OPNsense тракте не установлена.

GUI Voice, сохранённые параметры STUN и общий Apply остаются частью продукта. Закрытие исследования не означает удаления этих функций и не даёт им недоказанный статус рабочего Telegram preset. Старые предложения звонков, STUN, PF/NAT, захватов, TTL/fake и маршрутов не являются текущими задачами. [Заключительное доказательство](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

## История и навигация

[INDEX](INDEX.md) сохраняет ссылки на протоколы прошлых измерений и публикаций; [ledger v0.5.x](history/current/v0.5.x.md) — хронологию. Прежний накопительный снимок текущего состояния доступен [по неизменяемому Git commit](https://github.com/Tolian82/os-zapret2-restyle/blob/8b31fa49cfcf00617f3137b8eb7bc80427d1f19f/docs/PROJECT_STATE.md) как история, включая отменённые последующими решениями «следующие шаги».

## Архивы завершённых линий

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)
