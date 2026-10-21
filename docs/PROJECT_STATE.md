# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.6_2`**. Полный релиз опубликован; активное направление — подготовленная модернизация Strategy Lab через curl-impersonate. Stage 1 build integration is committed on the development branch but has not passed package CI or been owner-tested. Stages 2–6 remain unimplemented. The only next action задаёт [START_HERE](START_HERE.md). State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Версия, пакет и граница доставки

- `VERSION=0.5.6`, `PLUGIN_REVISION=2`, package candidate: `os-zapret2-restyle-0.5.6_2.pkg`.
- Полный Web/pkg-релиз [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; immutable tag, pkg/SHA256SUMS и FreeBSD15 Pages/pkg deployment подтверждены. SHA-256 пакета: `9c4ba669ae0ac453bb59da37b240234b7b2c44b49482b88eb98c14108a3dc6fe`. [Доказательство публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Обновление владельцем через OPNsense GUI до `0.5.6_1` не подтверждено. Новое оформление ТЗ не меняет этот факт и не является новой сборкой.
- Поддерживаемая платформа: OPNsense 26.7 / FreeBSD 15 amd64, Python 3.13. Служба `zapret`, общий dvtws2/supervisor и native lifecycle сохраняются.

## Strategy Lab — текущий код и согласованное направление

Audit was based on restyle `8b31fa49cfcf00617f3137b8eb7bc80427d1f19f` and recorded upstream snapshots. On 21 October 2026, the owner approved **three independent sufficient reachability signals: verified target TLS handshake, verified target QUIC handshake, OR genuine final target HTTP response (including 4xx/5xx, without requiring a body)**. The available FreeBSD `latest` client is fetched anew per build without upstream version pin; one supported Chrome profile is selected. [Integration map](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md).

**Реализовано в текущем исходном коде:** Python-планировщик, Model C как единственный нормальный production-путь, CandidateSpec/ResourceInventory, фиксированный endpoint epoch и source-port атрибуция, конечные бюджеты, отмена, Stage 90. Основной клиент пока обычный curl с HTTP/1.1/ограничением TLS; QUIC-кандидат пока проверяется handshake OpenSSL, а не HTTP3 GET. В Stage 80 есть четыре QUIC-кандидата; QUIC уже может быть источником Stage-85 результата. Ранний `TARGET_ACCESSIBLE` уже завершает задание до поиска/Extended.

**Approved requirements and implementation boundary:** `BH-01`–`BH-12` and six stages of the [English plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md). Stage 1 build integration exists on the active source branch but is not yet FreeBSD/owner-live accepted; stages 2–6 are not implemented. Reachability will use the handshake-or-HTTP-response rule and unpinned FreeBSD `latest` acquisition. An authentic HTTP response is affirmative evidence (not merely diagnostics); HTTP/ALPN/body fields not actually observed stay unknown. Direct HTTPS success by TLS **or** HTTP response skips QUIC. No Firefox, ordinary curl fallback, replacement Python scheduler or new recovery architecture.

| Этап | Состояние |
| --- | --- |
| Аудит, уточнение требований и подробное планирование | Завершены на уровне документации |
| 1. Private FreeBSD latest curl-impersonate bundling | Source implementation submitted for CI; installed OPNsense acceptance pending |
| 2. Сквозной TLS-handshake Standard | Не начат |
| 3. Extended и целевой QUIC-handshake | Не начат |
| 4. Расширение QUIC-каталога и допуск по бюджету | Не начат |
| 5. Результаты, GUI и сохранённые задания | Не начат |
| 6. Приёмка установленного пакета | Не начат |

The [existing live matrix](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md) demonstrates previous behavior only; it does not prove this new Chrome handshake-or-HTTP path. New evidence V1–V11 is defined in the detailed plan; none of these rows has been accepted yet.

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
