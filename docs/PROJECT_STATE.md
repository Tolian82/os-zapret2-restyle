# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.5_1`**: официальный TNAS laboratory, проверка UDP media path и full Web/pkg release, согласованный владельцем 19.10.2026. Источник единственного следующего действия — [START_HERE](START_HERE.md); фактический стенд и тестовая матрица — [native TNAS runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md). State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Версия, пакет и граница доставки

- `VERSION=0.5.5`, `PLUGIN_REVISION=1`; package candidate: `os-zapret2-restyle-0.5.5_1.pkg`. **Полный релиз v0.5.5 опубликован:** exact release-preparation merge `58412c4cf5ae99dd43a92f43305fa44a2aabeaaa`, неизменяемый annotated tag `v0.5.5`, [GitHub Release](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.5) с пакетом и SHA256SUMS, SHA-256 пакета `df060cf423f16ef87a0bb6c6450da12234f6500bc40a6b72046bcb8bafdda4df`, [workflow #39248958989](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39248958989) завершился успешным развёртыванием Pages/pkg. Независимая проверка доступности репозитория из этой среды не выполнена; владелец может проверить обновление в GUI. [Evidence](verification/evidence/2026-10-19-v0.5.5-full-release-publication.md). Предыдущий stable full release — `v0.5.4_1`. Это явно порученный новый этап, **полный Web/pkg v0.5.4 опубликован** из `b3c57106`: [релиз](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4), [workflow](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39172936035) SUCCESS Validate/Build/Publish Release/Deploy Pages; sha256 пакета `3cf80db941a701024c15936371ee2d30fb7ef12c0b5209608ff633ba2f9d6bb9`. Владелец подтвердил установку/обновление до `_1` и сохранение всех настроек Voice Transmission после обновления пакета без изменения значений (19.10.2026). Это подтверждает сохранность Config, но не runtime/IPFW после самостоятельной перезагрузки или работоспособность звонка. [Owner-live evidence](verification/evidence/2026-10-19-v0.5.4_1-voice-upgrade-config-persistence.md).
- Последний пакет с **подтверждённым полноценным Voice Apply на устройстве**: `os-zapret2-restyle-0.5.3_28`, source [PR #377](https://github.com/Tolian82/os-zapret2-restyle/pull/377), [CI #39165184611](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39165184611), прежний [testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3_28). Он успешно применил native Telegram ON с `committed` и `ready` на реальной OPNsense, без rollback/errors.
- Предыдущая полная Web/pkg поставка: [v0.5.3](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) (`0.5.3_2`), [исторические доказательства](verification/evidence/2026-10-17-v0.5.3-release-publication.md). Новый [v0.5.4](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4) имеет подтверждённые tag, pkg, SHA256 и Pages через GitHub Actions, отдельная [запись публикации](verification/evidence/2026-10-19-v0.5.4-full-release-publication.md).
- Платформа OPNsense 26.7 / FreeBSD 15 amd64, native Python 3.13. Единая служба `zapret`, один `dvtws2` и один supervisor; нативная общая транзакция Config/FD9/runtime/IPFW. Новые отдельные Voice daemon/PoC и старый `192.168.1.140` маршрут не являются текущей архитектурой.

## Приёмка на устройстве — подтверждено

| Уровень | Факт | Граница |
|---|---|---|
| Обновление пакета | После обновления до `0.5.4_1` **все настройки Voice Transmission остались точно такими же, как до обновления** | OWNER-LIVE: подтверждение владельца 19.10.2026; проверка значений конфигурации, не runtime/успешного звонка |
| Настройки и Apply | Telegram `saved_voice_on=true`, остальные Voice профили OFF; journal `committed`, Config digest соответствует Voice runtime | Включение профиля подтверждено на установленной `_28`; повторный Apply на `_1` не проверялся |
| Runtime | `configctl zapret status` running; `voice_inspect.state=ready`, `engine_verified=true`, `supervisor_verified=true` | Конфигурация и процесс подтверждены, но звонок не проверен |
| IPFW | native `19000 divert 989 udp ... table(zapret2_voice_telegram) ... xmit vtnet1`, 14 CIDR, `udp_ports=1-65535` | Подготовлен захват для совпадающих UDP destination |
| TNAS | `192.168.1.100`, `ovs_eth1`, SSH TCP/9222, Docker `tgvoice-lab` host mode; reflector route через OPNsense `192.168.1.2` | Только проверенный фиксированный адрес `91.108.13.10`; reboot/вся Telegram сеть не проверены |
| A1, 15 сек | `tgcalls_cli` v13.0.0; IPFW rule 19000 вырос с 0/0 до **60 / 4080**; Caller и Callee `Reconnecting`, return 1, `Call established=no` | `IPFW_CAPTURE_PASS`; **MEDIA/CALL FAIL/NOT VERIFIED** |

[Подробный протокол и пределы доказательства](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md). Вызов реального клиента, ответ от фиксированного Telegram reflector, валидная STUN RX, отправка fake и медиапоток пока не подтверждены; в последнем `voice_inspect` `telegram.media_verified=false`, `call_verified=false`. Native `capture_verified=true` — структурная/конфигурационная проверка IPFW, а `rule_packets=60` — счётчик трафика, не ответ удалённой стороны.

## Стабильное расположение наблюдений Voice в текущем кандидате

- **OWNER-LIVE, 19.10.2026: принято.** Владелец подтвердил, что диагностические статусы всех пяти Voice-сервисов остаются под чекбоксом как при скрытой, так и при открытой «справке»; также подтвердил правильные RU-названия трёх пунктов меню после открытия GUI/F5 и при переходе к другим разделам. Обе UI-задачи закрыты; это не приёмка media/call. [Evidence](verification/evidence/2026-10-19-v0.5.4_5-voice-ui-menu-owner-acceptance.md).
- `v0.5.4_5` опубликован в [GitHub testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4_5) как [`os-zapret2-restyle-0.5.4_5.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.4_5/os-zapret2-restyle-0.5.4_5.pkg), source/tag `0a4f0d89771d1845e297aa3beec94f1df7235e6b`, SHA-256 `6413b902f2e9a21c0633a55966b36ba3d97561bd082474edfa1939f2939a12e6`, FreeBSD 15 amd64. Стабильная публикация OPNsense GUI/pkg остаётся `v0.5.4_1`; пользовательская проверка расположения под флажком при обоих состояниях справки позднее выполнена успешно (см. evidence выше). [Publication record](verification/evidence/testing-publications/v0.5.4_5.md).


- Пакет `v0.5.4_4` опубликован как [testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4_4) для ручной установки, источник `ff5c4bf1e73fee6d25e99ec7e6c06e18f121556f`, SHA-256 `1eae13071c9a2fce5157771e5b5a6ca2cd6e13b68934c1a4df4ee52249415759`. GUI/pkg-репозиторий остаётся на `v0.5.4_1`. Автоматическая проверка CI успешна, соответствие образцам 02.jpg / 03.jpg на OPNsense пока не подтверждено владельцем. [Протокол публикации](verification/evidence/testing-publications/v0.5.4_4.md).
- Кандидат `v0.5.4_5` исправляет подтверждённый владельцем недостаток компоновки `_4`: диагностические подписи Telegram, Discord, X, SIP и Custom **всегда** располагаются под чекбоксом в том же втором столбце, независимо от состояния индивидуальной и общей справки. Штатный текст справки появляется после подписи, не сдвигая её. Изменён только CSS и документация/контракт GUI; form XML, Config, runtime, IPFW и Apply не меняются. Owner-live приёмка `_5` подтверждена (см. evidence выше).

## Исправление локализации меню в текущем кандидате

- Пакет `v0.5.4_3` опубликован как [testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4_3) для ручной установки (FreeBSD 15 amd64). SHA-256 `48fb66921a0a1bbfb095368fda15a9b81bfa1c66c9bf05978ee02aa73088845e`, source/tag `0874252239cc20066179ac843cc9d31342c60010`. Полный стабильный релиз/GUI-репозиторий остаётся `v0.5.4_1`; owner-live F5/cross-page проверка `_3` не выполнена. [Evidence](verification/evidence/testing-publications/v0.5.4_3.md).


- В `v0.5.4_3` RU названия трёх пунктов Zapret перемещены из JavaScript отдельных страниц в штатное серверное расширение `MenuContainer`. Выбор языка следует глобальной настройке OPNsense с приоритетом пользовательской; другие языки используют исходные английские `Menu.xml`/gettext. Старые DOM-перезаписи удалены; в `_3` устранены пробелы в конце строк представления, обнаруженные проверкой целостности после слияния `_2`; регрессионная матрица охватывает русский/английский язык и пользовательский приоритет. Владелец подтвердил корректные RU-названия после открытия GUI/F5 и при переходах между страницами — отдельное owner-live доказательство выше.

## Следующий технический рубеж

1. **Выполнено:** полный релиз v0.5.4_1, PR #379, CI, tag, GitHub pkg+SHA256 и Pages/pkg-repository. Обновление пакета до `_1` и неизменность настроек Voice Transmission подтверждены владельцем; post-upgrade runtime/IPFW и MEDIA/CALL остаются открыты.
2. После релиза A2: синхронно захватить LAN и WAN `host 91.108.13.10 and udp port 596`, сравнить направления и размеры/контрольные суммы/TTL, ответы и счётчик IPFW; без изменения маршрута/IPFW/PFIL.
3. Затем A3: отдельный валидный STUN-aware тест с подтверждённым STUN responder; текущая reflector Hello-проба не соответствует фильтру STUN профиля. A4 изолированные сравнения/изменения **только** после точного сетевого доказательства. A5 реальный двусторонний звонок — окончательная отдельная приёмка.

## История и навигация

[Полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [оригинальный план этапа v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [релиз/хронология v0.5.3](releases/v0.5.3.md) · [текущий ledger v0.5.x](history/current/v0.5.x.md). Исторические old PoC `zapret2_tgvoice`/A1/A2 и отдельный helper доступны через [INDEX](INDEX.md), но не являются активной инструкцией native-плагина.

## Архивы завершённых линий

- [v0.1.x archive](history/archive/v0.1.x.md) · [v0.2.x archive](history/archive/v0.2.x.md) · [v0.3.x archive](history/archive/v0.3.x.md) · [v0.4.x archive](history/archive/v0.4.x.md).
