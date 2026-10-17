# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.3_5`**: исправление поставки и наблюдаемая приёмка Voice. State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`. [START_HERE](START_HERE.md) задаёт следующее действие; [план](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) — порядок и критерии.

## Версия и поставка

- `VERSION=0.5.3`, `PLUGIN_REVISION=5`; package candidate: `os-zapret2-restyle-0.5.3_5.pkg`; [проверочный пакет `_5`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_5/os-zapret2-restyle-0.5.3_5.pkg) опубликован из `d91c8cb`, SHA-256 `3c4ca5acf76e22f0d0fc16c823849bc363030f137e36d1bea8c2bc2e1613b7da`; установленная `_5` не проверена. `_4` установлен владельцем и прошёл статус/lifecycle, но выявил GUI Validate/Apply blocker. Этап открыт прямым решением владельца 17.10.2026. Полный [релиз `v0.5.3`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) опубликован 17.10.2026, exact source/tag `376616af9e13963a27710bb3784b376855bb908d`; package `os-zapret2-restyle-0.5.3_2.pkg`, SHA256 `4ee03d677af571f3f23954a68fb086edfd0d8984f779efd7e9762091c640fc49`. [CI #39023792241](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39023792241) проверил Voice/Project/FreeBSD/.pkg Router; [release workflow #39024503035](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39024503035) выполнил GitHub Release и GitHub Pages FreeBSD repo. [Публикационные доказательства](verification/evidence/2026-10-17-v0.5.3-release-publication.md). Установленная `0.5.3_2` открывается, но выявлены локализация help, WAN preview и посторонний селектор релизов. Исправление `_3` интегрировано в `main` [`4cd362b`](https://github.com/Tolian82/os-zapret2-restyle/commit/4cd362bde1aba3357edf4e9776ffe5bc598d4361) и прошло [CI #39031185860](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39031185860) (Voice/Project/FreeBSD15 pkg). [Проверочный пакет _3](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_3/os-zapret2-restyle-0.5.3_3.pkg) опубликован из исходника `4cd362b`: [workflow #39032016190](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39032016190), SHA-256 `f3fc9e09d5713587c8381d5d44e86192e6908c3c623d434ebb80e618bd7db40d`, [публикационная запись](verification/evidence/testing-publications/v0.5.3_3.md). Стабильный Pages/pkg-репозиторий не обновлён; установленная `_3` проверена владельцем: RU/native help, WAN, проверка синтаксиса и компоновка подтверждены, но общий статус отображён неверно, а диагностика lifecycle вернула Execute error.
- Предыдущая версия `v0.5.2_194` опубликована и установлена владельцем; её [публикация](verification/evidence/2026-10-16-v0.5.2-release-publication.md) подтверждена, но `/ui/zapret/voice` на ней не открывается. Установка `v0.5.3_2` подтверждена владельцем выводом `pkg info` 17.10.2026.
- Целевая платформа — OPNsense 26.7 / FreeBSD 15 amd64 / Python 3.13. Наблюдённая система владельца — OPNsense 26.7.7 (FreeBSD 15 amd64).

## Наблюдение установленной _4 и коррекция _5

Владелец подтвердил установку `0.5.3_4`. Фактически исправлены отображение запущенной общей службы и read-only lifecycle inspector (возвращает `voice-saved-off-common-apply-available`, все Voice профили OFF). UI показывает Telegram ON в форме, но это не подтверждает сохранённый ON. Новые блокеры: обобщённая ошибка проверки на WAN и «Результат применения неизвестен». В `_5` исправлена **доказанная** ошибка классификации Throwable до вызова нативного FD9: нет основания помечать результат неизвестным до dispatch. Post-dispatch неопределённость сохранена. Полное объяснение ошибки XML/Config на устройстве и работа Voice Apply остаются OPEN. Ревизия `_5` протестирована [CI #39042954730](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39042954730) (Voice/Project/FreeBSD15 pkg) и опубликована как отдельный GitHub testing prerelease ([публикация #39043699207](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39043699207)). До проверки `_5` не выполнять слепой повторный Apply.

## Подтверждённый отказ и граница доказательств

| Сценарий | Факт |
|---|---|
| Открытие `/ui/zapret/voice` из меню в `_194` | Отказ: «Страница не найдена», сообщение и снимок владельца от 17.10.2026 |
| Причина в исходниках | В UI namespace отсутствует `VoiceController.php`; `voiceAction` находится в `IndexController`. API VoiceController не обслуживает `/ui/` |
| CI предыдущего пакета | Проверки исходников, симуляции и FreeBSD-сборка выполнены; не подтверждают открытие страницы |
| Новая поставка | `v0.5.3_2` опубликован и установлен; Voice GUI открывается, но RU help, dropdown WAN и сообщения ошибок не работают по ТЗ. `_3` установлен: RU справка, WAN и синтаксис подтверждены; IPFW не активирован, неверная общая подпись и lifecycle Execute error открыты; `_4` опубликован как проверочный пакет, исправляет общий статус и владельца Config в read-only inspector/saved draft; [CI #39038290885](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39038290885) и SHA256 подтверждены, installed проверка ожидается |
| Live `_3`: GUI + общее состояние | `_3` установлен, WAN validation/native RU help/список релизов исправлены. `setup_status` сообщает started, `voice_inspect` uninitialized, UI — «Неизвестно», `voice_lifecycle_inspect` — `Execute error`. `_4` проверен Voice/Project/FreeBSD, опубликован тестовым пакетом; строгий owner `wwwonly:wheel` для read-only lifecycle/saved-draft preview, inode/flock/FD9 без ослабления; установленный результат ещё не подтверждён | Проверка установленного `_4` и конкретная диагностика nonzero lifecycle |
| Полное GUI/CONFIG/BOOT/STUN/MEDIA/CALL | GUI route принят на `_2`; локализация/WAN ещё не приняты. Save/Apply/BOOT/STUN/MEDIA/CALL не подтверждены |

## Сохраняемая реализация и ограничения

В исходниках уже существуют пять профилей Telegram/Discord/X/SIP/Custom, формы RU/EN/help и shared IPSET, единая Config-модель, общий FD9 Apply обеих страниц, один dvtws2, scoped UDP/IPFW/WAN и normal Start/Stop/boot. Эти исходники являются базой исправления, а не доказательством готового установленного продукта. Проверки compiler/runtime/lifecycle сохраняются; следующий объём определяется найденным дефектом.

[ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) и общая архитектура остаются прежними. Старый Telegram PoC, marker, private rollback/migration не возвращаются. TCP/Squid/sing-box/PF/NAT, маршруты, TNAS и Docker вне текущей правки. Несовместимый Voice WAN явно отклоняется; глобальный UDP-to-any не допускается.

Уточнены существующие `DEV-007`, `DEV-011`, `DEV-018` и `CHAT-003`: каждый участок имеет наблюдаемый результат; блокер исправляется до перехода дальше; отчёт явно разделяет изменение, выполненную проверку и неподтверждённое. Новая переделка архитектуры найденным дефектом не обоснована.

## Сохраняемая продуктовая база

- DNS считается исправным; старое расследование закрыто до нового воспроизводимого отказа.
- Model C — единственный normal production Stage 60; автоматический A/B fallback удалён. Закрытые измерения Lua/BLOB/discovery/readiness не повторяются без нового основания.
- Strategy Lab поддерживает domain и canonical IPv4 с optional Host/SNI; трафик остаётся привязан к введённому IP, итоговый fixed-IP replay сохраняется. Bare-IP TLS даёт PARTIAL с guidance, bare-IP QUIC без Host/SNI пропускается; Generic UDP независим от Host/SNI/QUIC.
- Enable QUIC сохраняется, defaults OFF; ON/OFF execution и reload/revisit owner-live приняты. Generic UDP сохраняет exact bytes и принятый RU/EN file-picker путь.
- Model-C source-port attribution, конечные бюджеты, cleanup/cancel и Stage-90 восстановление исходной службы сохраняются. Общая архитектура Voice не меняет Laboratory.
- Нормальная служба использует один engine и общий lifecycle lock; Start/Apply/Reconfigure не устанавливают upstream engine автоматически. Его acquisition принадлежит setup/service-manager пути.
- IPv6 Laboratory и дополнительный BLOB GUI остаются отдельным будущим scope, не долгом этой страницы.

## Лаборатория и границы доказательств

Цель Telegram — воспроизводимые UDP-звонки через OPNsense `192.168.1.2` и того же провайдера. Старый UDP-маршрут через `.140` не является действующей базой. Рабочий лабораторный TCP/TLS через внешний Squid parent `185.203.117.88:33128` сохраняется отдельно; HTTP parent не переносит voice UDP.

A1/A2 дали проверенный WAN fake output без ответа/медиа; текущий рабочий Telegram preset и UDP CALL_PASS не доказаны. GUI/CONFIG/BOOT принимаются отдельно от MEDIA_PASS/CALL_PASS. После page/migration baseline продолжается [ограниченная Docker campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md).

Squid/sing-box/PF/TCP, маршруты, TNAS и Docker не входят в продуктовую переделку. Ручные TNAS host routes и запуск Docker сохраняются; route Cron/autostart не добавляется. При работе с appliance читать [операционный runbook](architecture/TELEGRAM_LAB_OPERATIONS.md), а не переносить его команды в plugin по умолчанию.

## Completed version-line archives

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)
