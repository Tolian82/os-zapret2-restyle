# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.3_15`**: исправление поставки и наблюдаемая приёмка Voice. State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`. [START_HERE](START_HERE.md) задаёт следующее действие; [план](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) — порядок и критерии.

## Версия и поставка

- `VERSION=0.5.3`, `PLUGIN_REVISION=15`; package candidate: `os-zapret2-restyle-0.5.3_15.pkg`; [testing package `_9`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_9/os-zapret2-restyle-0.5.3_9.pkg) опубликован с SHA-256 `cd6c57f24668587109ac133605f2699d43869aef1b1bdb7f4babbb65cf9b2045` из source merge `e979517` (Voice/Project/FreeBSD15 CI #39068637403), владелец установил `_9`, GUI Apply отказал на стадии `candidate`; [проверочный пакет _7](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_7/os-zapret2-restyle-0.5.3_7.pkg) опубликован из `e402d896f1323c03bb89dbdb39a350f79fb0f596`, SHA-256 `38f656a4e295f7451b1dd192737dba41d8e2f4405929fa81aa3b324a49158913`; установленная проверка ожидается; прежний [проверочный пакет `_6`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_6/os-zapret2-restyle-0.5.3_6.pkg) опубликован, SHA-256 `0b1cd06883dbe67552cc2978e776f03cf173bb2b88812539aa377c3c03423e31`, owner-live pending; предыдущий [проверочный пакет `_5`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_5/os-zapret2-restyle-0.5.3_5.pkg) опубликован из `d91c8cb`, SHA-256 `3c4ca5acf76e22f0d0fc16c823849bc363030f137e36d1bea8c2bc2e1613b7da`; установленная `_5` не проверена. `_4` установлен владельцем и прошёл статус/lifecycle, но выявил GUI Validate/Apply blocker. Этап открыт прямым решением владельца 17.10.2026. Полный [релиз `v0.5.3`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) опубликован 17.10.2026, exact source/tag `376616af9e13963a27710bb3784b376855bb908d`; package `os-zapret2-restyle-0.5.3_2.pkg`, SHA256 `4ee03d677af571f3f23954a68fb086edfd0d8984f779efd7e9762091c640fc49`. [CI #39023792241](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39023792241) проверил Voice/Project/FreeBSD/.pkg Router; [release workflow #39024503035](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39024503035) выполнил GitHub Release и GitHub Pages FreeBSD repo. [Публикационные доказательства](verification/evidence/2026-10-17-v0.5.3-release-publication.md). Установленная `0.5.3_2` открывается, но выявлены локализация help, WAN preview и посторонний селектор релизов. Исправление `_3` интегрировано в `main` [`4cd362b`](https://github.com/Tolian82/os-zapret2-restyle/commit/4cd362bde1aba3357edf4e9776ffe5bc598d4361) и прошло [CI #39031185860](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39031185860) (Voice/Project/FreeBSD15 pkg). [Проверочный пакет _3](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_3/os-zapret2-restyle-0.5.3_3.pkg) опубликован из исходника `4cd362b`: [workflow #39032016190](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39032016190), SHA-256 `f3fc9e09d5713587c8381d5d44e86192e6908c3c623d434ebb80e618bd7db40d`, [публикационная запись](verification/evidence/testing-publications/v0.5.3_3.md). Стабильный Pages/pkg-репозиторий не обновлён; установленная `_3` проверена владельцем: RU/native help, WAN, проверка синтаксиса и компоновка подтверждены, но общий статус отображён неверно, а диагностика lifecycle вернула Execute error.
- Предыдущая версия `v0.5.2_194` опубликована и установлена владельцем; её [публикация](verification/evidence/2026-10-16-v0.5.2-release-publication.md) подтверждена, но `/ui/zapret/voice` на ней не открывается. Установка `v0.5.3_2` подтверждена владельцем выводом `pkg info` 17.10.2026.
- Целевая платформа — OPNsense 26.7 / FreeBSD 15 amd64 / Python 3.13. Наблюдённая система владельца — OPNsense 26.7.7 (FreeBSD 15 amd64).

## Приёмка read-only Validate установленного _6

Владелец подтвердил пакет `0.5.3_6` командой `pkg info -x` и показал после «Проверить» сообщение «Синтаксис проверен (без применения)» отдельной строкой при выбранном WAN без ошибки. Ошибка невидимого статуса и read-only GUI Validate **закрыты на установленной _6**. Это не запись Config и не активация Voice/IPFW. Следующий ожидаемый результат — штатный одинарный Telegram ON Apply с отдельными свидетельствами saved ON, общего Zapret2 и Voice/IPFW. Последний независимый saved-state был OFF; Apply и звонок не подтверждены.

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


## Проверенный блокер подготовки `_8`, коррекция `_9`

Owner-live `_8`: `EUID=0`, FD9 PHP PASS, native-gate и PHP model PASS; GUI `shared-apply-run voice` дважды rc69 при отсутствии `shared-apply` record и `/var/db/zapret2`, Zapret2 продолжает работать. CLI `telegram-envelope enable` использовал сохранённую OFF-конфигурацию, поэтому не диагностирует несохранённый GUI-кандидат. Доказан дефект наблюдаемости границы: pre-runtime отказ ошибочно выглядит как post-runtime неопределённость. `_9` возвращает ограниченный `preflight-rejected=<stage>` из native worker и классифицирует его как безопасный отказ до runtime с переводом на RU. Прочие результаты остаются неопределёнными. **Точный отказ стадий `_8` и успешный Apply/CALL ещё не подтверждены.**

## Актуальный блокер и решение владельца (18.10.2026)

На установленной `_9` реальный Telegram ON Apply завершился `preflight-rejected=candidate` ещё до общего native cutover. Voice saved OFF, `voice_inspect=uninitialized`, обычный Zapret2 работает. Владелец отклонил дальнейшие повторные диагностики service status и утвердил единственный WAN от «Стратегий» без выбора на Voice ([Issue #350](https://github.com/Tolian82/os-zapret2-restyle/issues/350)). В `_10` исходники переводят все Voice профили на `general.waninterface` без нового поля ввода; старое `voice.waninterface` остаётся инертным и не переписывает Config. Реальная причина отказа `candidate`, Apply и вызовы ещё не приняты; следующая проверка — на установленном `_10`, без утверждения, что WAN был доказанной причиной.

## v0.5.3_12 — конкретный дефект передачи STUN TextField default

Owner-live `_11`: GUI Telegram ON успешно прошёл Validate и candidate, но остановился на `runtime-build`; журнал сборки `4|8|blobs|failed|...|telegram.args: required --filter-udp is missing`, а `stage-error.log` содержал ту же ошибку. Исходный default `voice.telegram.args` определён в MVC `Zapret.xml`, однако при checkbox-only ON сохранённый `config.xml` мог не иметь физического `<args>`. Старый writer генерировал XML только по изменённым MVC-полям и не переносил default, в отличие от Python reader, который читает XML напрямую. `_12` гарантирует передачу полного валидированного `args` и IPSET каждого включённого Voice-профиля в detached XML, даже если эти поля не изменялись относительно MVC. Тесты проверяют GUI XML и root request с отсутствующим/пустым `args` и отсутствующим IPSET. Исправление пока проверяется в CI, реальный Apply/STUN/CALL не объявлен успешным.


## v0.5.3_13 — native dvtws2 validator and root-only candidate

На установленной `_12` пользователь прочитал `7|8|validator|failed|2026-10-18T13:10:47+0300|cannot access hostlist file .../release/managed/hostlist-exclude.txt`, `file_open_test: Permission denied`. Предыдущие Telegram args уже успешно попали в генератор и исчезла ошибка стадии 4/8. Исходный FD9 worker держит `/var/db/zapret2/shared-work/<id>` с root-only `0700`; `validator_validate_engine_mapped()` направлял `--dry-run` на файлы под этим закрытым корнем, в то время как `dvtws2` читает hostlists после drop privileges. `_13` изолирует только необходимые публичные runtime hostlist/IPSET в короткоживущем `0755` каталоге `/tmp`, сохраняет закрытыми XML/plan, проверяет отсутствие symlink/перехода за managed, очищает зеркало при любом результате. Включена целевая регрессия с симулированным nobody и неразрешёнными ссылками. CI/пакет/Apply/звонок остаются OPEN.


## v0.5.3_14 — первый общий Apply при уже работающих Стратегиях

После установленной `_13` owner-live подтвердил candidate build 8/8 READY, `SEALED`, shared journal none, saved Telegram OFF и старый runtime `LEGACY_NO_VOICE_PLAN`. До записи журнала `apply_runtime_probe` отказывал при отсутствии `voice-plan.json` у действующей стратегии. `_14` не отключает проверку: выводит строго ограниченный manifest предыдущих обычных TCP/UDP divert правил из проверенных legacy артефактов и сравнивает его с IPFW под оригинальным FD9, не принимая чужие правила/Voice таблицы. Только потом выполняется тот же единый native runtime/IPFW/Config Apply; rollback предшествующего состояния остаётся у общего адаптера. Реальный Telegram ON и звонок пока OPEN.

## Completed version-line archives

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)

## Обнаруженный blocker `v0.5.3_7` (17.10.2026)

На `0.5.3_6` configd подтверждает `shared-apply-run voice` со статусом 69. `CLI_MODEL_OK`, `NATIVE_GATE_RC=0`, но отдельный реальный PHP FD9-check выдаёт Fatal Error: `posix_geteuid()` undefined (`PHP_FD9_RC=255`). На устройстве не создан каталог native Apply, saved Voice OFF и Voice IPFW неактивен. Одна доказанная причина — отсутствие отдельно устанавливаемого `php85-posix` в OPNsense 26.7; Makefile _6 объявлял только Python. _7 объявляет `php85-posix` с правильным портом `sysutils/php85-posix`, проверяет packaged metadata, а PHP worker проверяет EUID fail-closed. [CI #39053386699](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39053386699) Voice/Project/FreeBSD15 PASS, [test package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_7/os-zapret2-restyle-0.5.3_7.pkg) SHA256 `38f656a4e295f7451b1dd192737dba41d8e2f4405929fa81aa3b324a49158913` опубликован workflow #39054050579 (встроенный createPR denied; record PR #346 создан через connector). Installed extension, PHP FD9 и успешный Apply ещё не подтверждены.

## Исправление OPNsense-зависимости v0.5.3_8

Владелец подтвердил штатным pkg, что php85-posix в доступных OPNsense репозиториях отсутствует. Кандидат _7 ошибочно требовал порт FreeBSD; _8 полностью удаляет зависимость и проверяет root эффективный UID через штатный /usr/bin/id -u (PHP proc_open с argv без shell). Сохраняются FD9/inode/flock; php -n тест гарантирует работу без расширения POSIX, FreeBSD package metadata не должно требовать php85-posix. Native Apply и Telegram CALL ещё не приняты.

## Candidate отказ с общим WAN — `_11`

После удаления самостоятельного Voice WAN GUI сообщает `preflight-rejected=candidate` на Telegram ON; визуально WAN больше не выбирается на Voice, отдельный `pkg info` новой попытки не представлен. Исходники OPNsense 26.7 `BaseListField` подтверждают динамический словарь `{value, selected}`; `VoiceSettingsSnapshot` ранее хэшировал и переводимый/динамический `value`, и невключённые опции, что допускает расхождение между PHP веб-процессом и configd без изменения Config. `_11` приводит массив опций к реально выбранным ключам, проверяет случай разных RU/EN опций и защиту при смене WAN/mode; раннее `candidate` детализируется на безопасные подстадии. Source [PR #354](https://github.com/Tolian82/os-zapret2-restyle/pull/354) объединён как `449d614` после успешного CI #39114110274 (Voice, Project, FreeBSD 15), [проверочный `.pkg` `_11`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_11/os-zapret2-restyle-0.5.3_11.pkg) опубликован с SHA-256 `d0e16200ab95411240b4beb5380d85c2616b5f9ac87bcec7f0a77e188721fc55` (workflow #39114638282; автоматический docs PR запрещён Actions, продолжено в PR #355 через connector). Стабильный pkg репозиторий не обновлялся. Root-origin failure после этой правки и Telegram media/call ещё требуют подтверждения на приборе.

## v0.5.3_12 — верифицированная testing-поставка

Source [PR #356](https://github.com/Tolian82/os-zapret2-restyle/pull/356) объединён как `5bfafc01de2183392b325de6538d4fb943b50ea5` после успешной [Voice/Project/FreeBSD15 CI #39117198942](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39117198942). [Пакет `os-zapret2-restyle-0.5.3_12.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_12/os-zapret2-restyle-0.5.3_12.pkg) опубликован как testing prerelease из точного merge commit, SHA-256 `ed28d1c071fb2dee1e2ee891634762a367fa675a48c561e2db2ce13731e6effe`; [publisher #39117736239](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39117736239) прошёл сборку/верификацию и отказал лишь при запрещённом API создания docs PR, которое закрывает connector PR #357. Stable pkg не менялся. Владелец ещё не проверил установленный `_12` Apply/IPFW/STUN/CALL.

## v0.5.3_13 — подтверждённая testing-публикация

[PR #358](https://github.com/Tolian82/os-zapret2-restyle/pull/358) merged into `b8c5c35635a472e2b642c373f8fc724811a18ce8` после PASS Voice/Project/FreeBSD15 CI #39119480095. [FreeBSD15 testing pkg `_13`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_13/os-zapret2-restyle-0.5.3_13.pkg) SHA-256 `7e090d0ff7a6f8db7c1d4e5290eb388313aed297fbdf5c6936d10fd345bba171` проверен и опубликован publisher #39120145999 (тег точно равен source merge). Последний шаг workflow — создание docs PR — заблокирован GitHub Actions permissions и завершён через connector PR #359. Stable Pages/pkg repo unchanged. Установка `_13`, Apply ON, IPFW/STUN и реальный звонок ещё требуют подтверждения владельца.

## v0.5.3_14 — опубликованная тестовая поставка

[PR #361](https://github.com/Tolian82/os-zapret2-restyle/pull/361) объединён как `be6669469049279713128d290cd649ba4fa96462` после успешных Voice/Project/FreeBSD15 CI #39123963640. [Тестовый FreeBSD15 пакет `_14`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_14/os-zapret2-restyle-0.5.3_14.pkg) SHA-256 `e790c48f1fe3f8e1a42e9e865bb35f8507520e09c8bc8905feb7647fc238360c` проверен и опубликован из точного source commit в publisher #39124542765. Только создание docs PR отказало по правам GitHub Actions; фиксируется через connector PR #362. Стабильный pkg репозиторий не обновлялся. На установленной `_14` ещё не подтверждены saved Voice ON, переход kernel IPFW и реальный CALL.

## `_15` — исправление реального CLI verify-legacy

Owner-live `_14`: GUI Apply снова пишет «Результат применения неизвестен», saved Voice ON не подтверждён. В `voice_ipfw_adapter.py` обнаружена неинициализированная переменная `legacy` внутри реального CLI `verify-legacy`; правильная проверка `prior_legacy`. Все предыдущие тесты этого исправления обходили вызов `main()`. `_15` исправляет вызов и проверяет точку входа прямым CLI-тестом, включая отказ при native predecessor. Отказы на безопасных этапах bundle/Config/runtime preflight показываются как preflight-rejected, постжурнальные uncertain состояния не маскируются. CI/pkg/установленный Apply/STUN/CALL ещё ожидаются.

## `_15` — опубликована тестовая версия

[PR #364](https://github.com/Tolian82/os-zapret2-restyle/pull/364) merged в `64ca0e4f46253aa52c78a7311125e985ef9e72df` после успешного Voice/Project/FreeBSD15 CI #39126436549, включая реальный CLI `verify-legacy` и проверку ревизий. [Тестовый пакет `_15`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_15/os-zapret2-restyle-0.5.3_15.pkg) SHA-256 `d1cc2fad37be7473beac86c8aeef42cc500a1d48763ba891e20fbf46b36f488e` создан и подтверждён publisher #39127051722. GitHub Actions не мог создать только документационный PR, запись идёт через connector PR #365. Stable pkg repo unchanged. Установка на OPNsense, успешный Voice Apply, сохранённый Telegram ON/IPFW и звонок **ещё не приняты**.
