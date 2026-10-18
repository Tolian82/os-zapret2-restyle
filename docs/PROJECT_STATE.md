# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.4_1`**: официальный TNAS laboratory, проверка UDP media path и full Web/pkg release, согласованный владельцем 19.10.2026. Источник единственного следующего действия — [START_HERE](START_HERE.md); фактический стенд и тестовая матрица — [native TNAS runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md). State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Версия, пакет и граница доставки

- `VERSION=0.5.4`, `PLUGIN_REVISION=1`; package candidate: `os-zapret2-restyle-0.5.4_1.pkg`. Это явно порученный новый третий-компонентный этап и полный release preparation, а не незапрошенная перестройка backend. До выполнения CI/Release workflow **не** утверждать, что tag/pkg или Pages уже опубликованы.
- Последний проверенный пользователем пакет: `os-zapret2-restyle-0.5.3_28`, source [PR #377](https://github.com/Tolian82/os-zapret2-restyle/pull/377), [CI #39165184611](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39165184611), прежний [testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3_28). Он успешно применил native Telegram ON с `committed` и `ready` на реальной OPNsense, без rollback/errors.
- Предыдущая полная Web/pkg поставка: [v0.5.3](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) (`0.5.3_2`), [исторические доказательства](verification/evidence/2026-10-17-v0.5.3-release-publication.md). При появлении нового `v0.5.4` статус публикации обновляется только по подтверждённым тегу, pkg, SHA и Pages, не по плану.
- Платформа OPNsense 26.7 / FreeBSD 15 amd64, native Python 3.13. Единая служба `zapret`, один `dvtws2` и один supervisor; нативная общая транзакция Config/FD9/runtime/IPFW. Новые отдельные Voice daemon/PoC и старый `192.168.1.140` маршрут не являются текущей архитектурой.

## Приёмка на устройстве — подтверждено

| Уровень | Факт | Граница |
|---|---|---|
| Настройки и Apply | Telegram `saved_voice_on=true`, остальные Voice профили OFF; journal `committed`, Config digest соответствует Voice runtime | Включение профиля подтверждено на установленной `_28` |
| Runtime | `configctl zapret status` running; `voice_inspect.state=ready`, `engine_verified=true`, `supervisor_verified=true` | Конфигурация и процесс подтверждены, но звонок не проверен |
| IPFW | native `19000 divert 989 udp ... table(zapret2_voice_telegram) ... xmit vtnet1`, 14 CIDR, `udp_ports=1-65535` | Подготовлен захват для совпадающих UDP destination |
| TNAS | `192.168.1.100`, `ovs_eth1`, SSH TCP/9222, Docker `tgvoice-lab` host mode; reflector route через OPNsense `192.168.1.2` | Только проверенный фиксированный адрес `91.108.13.10`; reboot/вся Telegram сеть не проверены |
| A1, 15 сек | `tgcalls_cli` v13.0.0; IPFW rule 19000 вырос с 0/0 до **60 / 4080**; Caller и Callee `Reconnecting`, return 1, `Call established=no` | `IPFW_CAPTURE_PASS`; **MEDIA/CALL FAIL/NOT VERIFIED** |

[Подробный протокол и пределы доказательства](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md). Вызов реального клиента, ответ от фиксированного Telegram reflector, валидная STUN RX, отправка fake и медиапоток пока не подтверждены; в последнем `voice_inspect` `telegram.media_verified=false`, `call_verified=false`. Native `capture_verified=true` — структурная/конфигурационная проверка IPFW, а `rule_packets=60` — счётчик трафика, не ответ удалённой стороны.

## Следующий технический рубеж

1. Завершить полный релиз `v0.5.4_1`: exact CI, FreeBSD/pkg checksum, immutable semantic tag `v0.5.4`, GitHub release, Pages/pkg-repository и README gate. Исполнимость media **не** выдавать за успешную.
2. После релиза A2: синхронно захватить LAN и WAN `host 91.108.13.10 and udp port 596`, сравнить направления и размеры/контрольные суммы/TTL, ответы и счётчик IPFW; без изменения маршрута/IPFW/PFIL.
3. Затем A3: отдельный валидный STUN-aware тест с подтверждённым STUN responder; текущая reflector Hello-проба не соответствует фильтру STUN профиля. A4 изолированные сравнения/изменения **только** после точного сетевого доказательства. A5 реальный двусторонний звонок — окончательная отдельная приёмка.

## История и навигация

[Полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [оригинальный план этапа v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [релиз/хронология v0.5.3](releases/v0.5.3.md) · [текущий ledger v0.5.x](history/current/v0.5.x.md). Исторические old PoC `zapret2_tgvoice`/A1/A2 и отдельный helper доступны через [INDEX](INDEX.md), но не являются активной инструкцией native-плагина.

## Архивы завершённых линий

- [v0.1.x](history/archive/v0.1.x.md) · [v0.2.x](history/archive/v0.2.x.md) · [v0.3.x](history/archive/v0.3.x.md) · [v0.4.x](history/archive/v0.4.x.md).
