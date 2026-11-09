# Поэтапный план — восстановление полного жизненного цикла Zapret2 Restyle

**Статус:** согласованный порядок будущей реализации; ни один этап ниже не объявляется выполненным созданием этого документа.
**Основание:** [ТЗ v1.1](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md), решение владельца от 8 ноября 2026, дефекты [#970](https://github.com/Tolian82/os-zapret2-restyle/issues/970)–[#973](https://github.com/Tolian82/os-zapret2-restyle/issues/973).
**Текущая техническая база:** опубликованное `v0.6.3_1.pkg` с наблюдаемыми дефектами; следующая ветка документации `v0.6.3_2` **не содержит исправлений**, новых runtime-пакетов и live acceptance.
**Один источник требований:** указанное ТЗ; этот план задаёт порядок, продукты и объективные выходные проверки. Если есть расхождение, новое утверждённое решение владельца и ТЗ имеют приоритет.
**Релиз:** новый пакет и его версия/суффикс определяются только в момент реального исходного PR и публикации; источник/архив/CI/owner-live всегда фиксируются отдельными SHA-256 и evidence. Предварительные номера будущих `_N` не резервируются.

## 0. Правила выполнения этапов

1. **Строго по порядку.** Этап получает статус `PASS` только при реально выполненном указанном результате и доказательстве. `OPEN`, `IN_PROGRESS`, `FAIL`, `BLOCKED`, `NOT TESTED` не превращаются в PASS. Ошибка этапа исправляется в его пределах, без скачка к последующим работам.
2. **Один проверяемый инкремент — один логический PR**, если действующие `DEV-017`/`GH-011` не требуют объединить изменения одного корневого дефекта. Реальная пара `main` и candidate revision перечитывается перед каждым PR; `PLUGIN_REVISION` увеличивается один раз за каждый eventual merge, включая документацию. `VERSION` не меняется автоматически.
3. Перед кодом проверять **настоящие текущие entrypoints, их потребителей, существующие тесты и package/native ABI**. Не создавать вторые менеджеры процесса, пакета или запущенных профилей вместо уже принятого общего `configd` + FD9 owner.
4. **Безопасность:** чужой IPFW и другой Config неизменны; обычные собственные правила только `19000–19010`, Lab только `19100–19131`; никакого глобального PF disable/enable, массового kill, опасного cleanup без доказанного владения. Voice — тот же общий двигатель.
5. Тесты разделяются на `SOURCE` (статические/юнит), `INSTALLED-CI` (настоящий FreeBSD 15 / OPNsense 26.7 disposable-guest + реальный пакeт) и `OWNER-LIVE` (действительные действия в GUI пользователя). Исторический PASS на `_188` не подменяет новое чистое `v0.6.3_1` или следующую сборку.
6. Не выполнять полное разрушительное удаление на production автоматически; `--purge` требует явного согласия, проверенного backup и ownership. В CI можно использовать только специально подготовленный disposable guest.
7. Любое непройденное доказательство — конкретный blocker с привязкой к тесту и этапу. Блокеры не скрывать; последующие работы не открывать для обхода. Обновлять [START_HERE](../START_HERE.md), [PROJECT_STATE](../PROJECT_STATE.md), [ROADMAP](../ROADMAP.md) только когда изменился действительный факт/вектор следующей работы.

## Этап 01 — самостоятельная полная очистка (ПЕРВЫМ)

**Задача:** CL-01. **Никакая другая реализация не начинается до подтверждения результата этого этапа.**

**Что сделать:** разработать `scripts/purge-os-zapret2-restyle.sh`, распространяемый независимо от установленного пакета (прямая поддерживаемая ссылка/скрипт в репозитории или release artifact). По умолчанию — `--dry-run`; перед реальным действием backup Config + инвентаризация; `--purge` и явная фраза подтверждения. Отдельно поддержать чистый случай «пакета уже нет, параметры остались» и повторный вызов. В полном режиме очищать подтверждённые только Zapret2 pkg/firmware registration, scoped process/FD9/IPFW, `OPNsense.Zapret` в config.xml через штатный Config API, engine checkout, пользовательские/optional Lua/BIN, lab jobs, логи, слои меню/cache, собственные runtime и temp files, выделенный repo file; `--keep-repo` — сознательный режим *не полного* удаления repo. Не трогать OPNsense-системные и общие зависимости.

**Проверки:** безопасный dry-run (никаких изменений), контроль backup до mutation, foreign PID/FD9/IPFW/Config/symlink отрицательные сценарии, реальное удаление на одноразовой OPNsense, идемпотентность повторного dry-run, наличие восстановления из backup, отсутствие всех Zapret2-only следов и stale Services меню. Общие пакеты/чужой Config/прочие меню сравнить по снимкам.

**Выход / gate G01:** автономный скрипт проверен на disposable installed/uninstalled system; очистка воспроизводит чистое состояние без side-effects; выполнена **A01** и первая часть **A20**. Только после этого переход к этапу 02.

## Этап 02 — нормальное удаление через GUI без уничтожения данных

**Задача:** LC-02, [#971](https://github.com/Tolian82/os-zapret2-restyle/issues/971).

**Что сделать:** установить точный механизм OPNsense firmware unregister/генерации меню; точечно исправить штатные `pkg` hooks/registration/menu refresh, не вызывая full-purge. Обычный uninstall сохраняет Config, upstream Git/bin, сохранённые Extra Lua/BIN, но снимает package-owned UI, меню, службу/owned rules.

**Проверки:** реальный Firmware GUI Uninstall, отсутствие пунктов Services даже после F5 и Ctrl+F5, открытие чужих плагинов, проверка `pkg info` и registration, данные runtime/Config прежние. После GUI Reinstall эти данные и пользовательский профиль доступны; повторный uninstall не оставляет дубликатов.

**Выход G02:** owner/installed UI-сценарии **A18, A19** с подтверждёнными server-side menu/result; `CL-01` не участвует в обычном uninstall.

## Этап 03 — первая установка upstream через GUI

**Задача:** LC-03/04, [#970](https://github.com/Tolian82/os-zapret2-restyle/issues/970).

**Что сделать:** снять ошибочную блокировку верхнего Apply при `installed=0` в `general.volt`; пройти реальную цепь `ServiceController` → `setup_launcher` → `setup_transaction` → `setup.sh`. Создать корректную отдельную first-install ветку для состояния **без** прошлого release marker, Git HEAD и бинарника; существующую rollback-ветку RUNNING/STOPPED upgrade не ослаблять. Установку делать через GUI/configd, **не** в pkg hook, без ручной CLI-команды как обязательного этапа.

**Проверки:** чистое отсутствие `dvtws2`, реальная кнопка Install, выбранная версия `v1.0.7`, реальные GUI-progress/error/status; fault-инъекции download/compile/interruption/retry и сравнение runtime Config/FD9. Повторная установка и существующий update/rollback отдельно.

**Выход G03:** **A02–A04**; `installed` и `service` после успешного setup достоверны, первая установка не требует несуществующего «предыдущего» engine.

## Этап 04 — утверждённые значения YouTube после чистой установки

**Задача:** LC-05, [ТЗ §4](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md#4-стартовые-значения-полей-после-истинно-чистой-установки).

**Что сделать:** один раз записать в существующую нативную модель/штатный `OPNsense.Zapret` Config **ровно десять доменов в утверждённом порядке** только при полном отсутствии самого узла Zapret на первой установке пакета; существующий (в том числе пустой) узел является пользовательской конфигурацией и исключает запись:
`youtube.com`, `googlevideo.com`, `yt.be`, `youtu.be`, `ytimg.com`, `youtubei.googleapis.com`, `youtube.googleapis.com`, `youtube-nocookie.com`, `ggpht.com`, `ssl.gstatic.com`.

Точное поле Traffic Strategy берётся непосредственно из ТЗ: TCP `80,443` с HTTP fake `http_iana_org` + HTTP multisplit, TLS multisplit; затем **один** `--new`, UDP `443` QUIC fake `fake_default_quic:repeats=5`. Использовать `<HOSTLIST:youtube>` для обоих профилей. `--blob=http_iana_org` развернуть через существующий resolver в `files/fake/http_iana_org.bin`. Не подставлять прежний `tls7`; не скачивать Additional Resources. GUI отображает **сохранённые в `config.xml` поля** ещё до установки движка; Enabled остаётся выключенным, WAN остаётся невыбранным. Выполнить один штатный `Config::save()` через модель из `+POST_INSTALL` после регистрации плагина, до template reload; **без новых модельных `<Default>`, init/read-time fallback или альтернативного хранилища**. Повторный `pkg add` с уже существующим `OPNsense.Zapret` должен быть no-op для Zapret Config, независимо от заполненности Traffic Strategy / YouTube Domains.

**Проверки:** реальный clean `pkg add` → один Config save → inspect `/conf/config.xml` с точными двумя строковыми значениями и отсутствием автоматического WAN/Enabled → свежий GUI first-render/F5 без fallback; сохранение вручную пустой стратегии и отсутствие самовосстановления; reinstall/upgrade с **существующим даже пустым** узлом без дополнительного Config save или изменения сохранённого XML; только total-purge возвращает первую запись. На **реальной** чистой OPNsense выполнить parser → placeholders → blobs → native generator/validator → `dvtws2 --dry-run` → активный Apply/Start для TCP и UDP; проверить реальные собственные IPFW и Stop, отсутствие optional BIN/Lua.

**Выход G04:** **A05, A06, A08**, отсутствие повторного заполнения пользовательского пустого поля. Source-only существование `http_iana_org.bin` и built-in `fake_default_quic` не заменяет installed-native proof.

## Этап 05 — WAN сохраняется сам по себе

**Задача:** LC-06/LC-06A/LC-06B/LC-06C — обязательный WAN-first на всех путях запуска.

**Что сделать:** GUI/API сохраняют WAN независимо от `Enabled`, наличия Traffic Strategy, hostlists/IPSet и даже отсутствия upstream; не требуют обычный runtime-build для безопасного изменения Config. На RUNNING система должна применять защищённую native runtime-транзакцию с rollback; проверка logical/interface mapping сохраняет работающие real WAN/TUN/OPT случаи.

**Проверки:** WAN-only Apply с полностью пустыми полями, выключенной службой, установленной/неустановленной службой и F5; отсутствие создания собственных IPFW; отдельные отрицательные tests invalid interface/readonly; RUNNING WAN-change rollback без потери Voice.

**Обязательный WAN-first gate, проходящий через G05/G07/G08:** пересмотреть весь production call graph — GUI Start, configd start/restart/reconfigure, reboot, Shared Apply (включая одновременное изменение WAN), Voice-only, Standard/Extended/Circular Lab и worker. Сначала saved/effective WAN, затем интерфейс mapping, затем upstream/strategies/Voice/Job/IPFW. Прокинуть `wan-required`/ `wan-invalid` в локализованный GUI. Не блокировать WAN-only Save, Stop, setup, uninstall или recovery. Нельзя считать холодный native WAN Save из PR #985 закрытием runtime WAN-first.

**G05 `_18` установленный native S2:** [OPNsense 26.7 #42640788056](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42640788056) PASS для WAN-first через Strategies/Voice/Standard+Extended+Circular Lab и configd, до Job, с корректными RU/EN JSON-ошибками, затем engine-second после сохранения WAN без upstream. Слияние PR #992 ожидает исправления маршрутизации исторических S3 workflow, случайно запущенных Lab mock-фикстурой и упавших на GitHub HTTP 403. **Выход G05:** **A07** и WAN-часть **A17**; owner-live и реальная VPN/IPsec среда квалифицируются отдельно в G07/G08/G11, лаборатория видит сохранённый WAN без первого Start.

## Этап 06 — пустая Traffic Strategy, no-action и Voice-only

**Задача:** LC-07.

**Сначала эксперимент:** на настоящей FreeBSD/OPNsense `v1.0.7` проверить `dvtws2` без пользовательских десинхронизационных профилей (валидный divert-port, `--dry-run`, реальный жизненный цикл, PID, packet trace, отсутствие вредных действий). Записать точную команду и результат. **Не считать `no_action` в upstream достаточным доказательством.**

**Ветка A (поддерживается):** разрешить пустую Traffic Strategy в `orchestrator.sh`, `generator.sh`, `validator.sh` и все связанном runtime-build, без обычных перехватывающих IPFW-правил, пока нет активных обычных профилей.

**Ветка B (не поддерживается):** минимальный управляемый idle без engine-process в режиме, когда нет ни одной стратегии и Voice OFF, честный статус «Остановлена» при сохранённом `Enabled`, никаких фиктивных no-op rules или заявленного RUNNING PID.

**В обеих ветках:** если Voice Transmission имеет валидные активные профили, общий original FD9 owner запускает один `dvtws2` и только Voice rules, не требует ordinary traffic strategy. Добавление первой/удаление последней ordinary strategy, Voice-only ↔ combined ↔ inactive проходит штатным Apply и transactional rollback.

**Проверки:** real engine, IPv4 (+IPv6 когда доступен) scoped IPFW, foreign rules untouched; concurrent operation, Stop/Restart/reboot, Voice enabled/disabled и отказ runtime-build.

**Выход G06:** **A09, A11**; допускается пользовательская действительно пустая стратегия без вмешательства в трафик.

## Этап 07 — GUI Start/Apply/Stop/Restart и правдивые RU/EN состояния

**Задача:** LC-08/09/10, [#972](https://github.com/Tolian82/os-zapret2-restyle/issues/972).

**Что сделать:** определить конкретные ошибки первого Start и нижнего Apply; возвращать/показывать фактические native ошибки с этапом, не подавлять результат AJAX callback. Ровно пять локализованных категорий: `Не установлен / Not installed`, `Установка… / Installing…`, `Остановлена / Stopped`, `Запущена / Started`, `Ошибка / Error`. Неисполненная или неопределённая операция — код и безопасная диагностика внутри `Ошибка`, **никаких** «Требуется проверка» и ложного Start. Не показывать ошибку как успех по таймауту или потерянному ответу.

**Проверки:** WAN-first matrix: одновременно missing WAN + missing engine + invalid profile — первым только `wan-required`, no mutation. Выбранный, но invalid WAN — `wan-invalid`; затем отдельный upstream missing; отключённый Save/Stop/Install остаются доступны. GUI actual button clicks с disabled/WAN missing/invalid profile/missing binary, running PID check/FD9/IPFW and normal Stop/Restart/Apply; RU, EN и reload; невозможность повторно отправить то же неопределённое действие, когда оно выполняется.

**Выход G07:** **A10, A16, A17** и точные сообщения в двух локалях; никакого generic-only `preflight failed`.

## Этап 08 — Laboratory Standard/Extended ДО первого запуска

**Задача:** LC-11/12.

**Что сделать:** и client, и native API/worker preflight: **вначале сохранённый, назначенный и разрешимый WAN** (`wan-required`: «Укажите WAN интерфейс» / “Select a WAN interface”; `wan-invalid` отдельно), **затем** реальное наличие upstream (`not installed` с RU/EN переводом). Независимость от `Enabled`, основной Traffic Strategy, запуска общего сервиса хотя бы один раз. Использовать временную стратегию Laboratory, scoped rules, сохранить/восстановить STOPPED состояние; при RUNNING — восстановить RUNNING, original FD9, Config/Voice.

**Проверки:** одновременно нет WAN/upstream — сначала WAN; после выбора WAN без upstream — не установлен, без Job/daemon/IPFW. Затем впервые установленный upstream + сохранённый WAN + никогда не запускавшийся обычный engine, реальная authenticated Standard и Extended job; отдельные ранние отказы без движка/WAN; cancel/error/timeouts со strict restore; WAN/IPv6 route boundaries.

**Выход G08:** **A12, A13, A14** с genuine installed Job/Stage/restore, не только mock или доступный внешний endpoint.

## Этап 09 — устранение Stage-60 internal ERROR на blocked target

**Задача:** LC-13, [#973](https://github.com/Tolian82/os-zapret2-restyle/issues/973).

**Что сделать:** восстановить фактическое native Stage 50→60 по сохранённым job evidence; определить ошибку worker/parallel/exit mapping, исправить конкретный путь. При отсутствии TLS-семейства завершать `NO_CANDIDATE` честно, при внутренней ошибке показывать причину, не терять Stage-90 restoration; после позитивного результата требовать подтверждения доступности именно целевого заблокированного endpoint.

**Проверки:** натуральный Stage 50 no-family и Stage 60, positive family, negative family, worker exception, cancellation and timeout, Stage 90/99; TLS verify, Host/SNI, IPv4/IPv6 и QUIC по утверждённым режимам.

**Выход G09:** **A15**; реальный blocked-target сценарий не заканчивается бессодержательным internal error при отсутствии кандидатов.

## Этап 10 — полный native regression, точный тестовый пакет

**Задача:** LC-14/15, defects #970–#973. Это **инженерная** приёмка SOURCE/INSTALLED-CI, не подмена последующего owner-live.

**Что сделать:** из принятого точного source SHA собрать **один настоящий native OPNsense пакет**, запустить CI на disposable гостях «действительно чистая установка после purge» и «исторический RUNNING/Voice owner» с настоящими pkg/hooks/configd/FD9/IPFW, Additional Resources, firmware GUI, reboot и защищённым recovery. Для применимых сценариев одно физическое `.pkg` передаётся между гостями **без пересборки**; фиксировать SHA-256 и точные номера пакета/сборки. Проверить поправленные критические пути A01–A22 с границами SOURCE/INSTALLED-CI; не выдавать CI HTTP 200 или mocked Lab за реальный браузерный результат.

**Доставка для owner-live:** после принятия source/installed evidence и положительных обязательных CI пройти штатные GitHub PR merge и **опубликовать точный тестовый пакет** через project testing publisher, включая immutable package SHA, GitHub asset, companion installer и publication record по действующим GH-/CHAT-правилам. **Не считать локальную сборку или короткоживущий Actions artifact доступным владельцу пакетом.** Тестовая публикация не повышает стабильный Web/pkg repo и не означает разрешение на полный релиз.

**Выход G10:** SOURCE + disposable INSTALLED-CI для всех применимых A01–A22 прошли; доступен воспроизводимый GitHub testing package из точного принятого source merge SHA, подтверждены installer, ABI, контрольные суммы, опубликованные assets. Owner-live проверки на собственном устройстве **ещё PENDING** — их следующий этап G11.

## Этап 11 — owner-live GUI-приёмка и закрытие ТЗ

**Что сделать:** установить **именно опубликованный в G10** тестовый кандидат через предусмотренный штатный путь на OPNsense владельца и пройти обязательные сценарии браузера: default ten domains/TCP+QUIC, индикация Service/Apply/Install/Start, сохранение WAN без engine, пустая стратегия/Voice-only, обе лаборатории до первого Start, Stage-60 реальный заблокированный endpoint, штатный GUI uninstall без stale Services links, повторная установка, безопасный отдельный purge **только после явного согласия на разрушение данных**. Проверить RU/EN и поведение после F5/перезагрузки. Владелец не обязан запускать разрушительные тесты на продуктивном шлюзе: использовать выделенный стенд либо отдельное явное разрешение с backup.

**Документация:** после реальной приёмки согласовать README, встроенную RU/EN Help, START_HERE/PROJECT_STATE/ROADMAP/INDEX, release notes, guide скрипта purge, installation instructions, точные SHA/owner-live evidence и актуальные незакрытые ограничения; закрывать #970–#973 **только по соответствующим подтверждённым сценариям**.

**Выход G11:** пользовательская GUI-приёмка на **точной версии опубликованного тестового пакета** фактически прошла по обязательным A01–A22 в применимых owner-live строках; нет подтверждённых блокеров; документация/статусы честно фиксируют что PASS, FAIL и NOT TESTED. **Полный стабильный релиз — отдельно после явного решения владельца, обязательных release gates и неизменяемой публикации в GitHub Release + Pages/pkg; сам G11 не уполномочивает автоматически публиковать stable.**

## Контрольный журнал переходов

| Этап | Gate | Статус на дату создания плана | Первый требуемый свидетель |
|---|---|---|---|
| 01 — полный purge | G01 | **INSTALLED-CI PASS** [native #42505329364](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42505329364); **OWNER-LIVE/GUI NOT TESTED** | Actual package installed, post-uninstall residuals and RUNNING lo0/dvtws2, owned IPFW, Config backup/dry-run verified |
| 02 — обычное GUI удаление | G02 | **INSTALLED-CI PASS** [PR #979](https://github.com/Tolian82/os-zapret2-restyle/pull/979); **OWNER-LIVE PENDING** | POST_DEINSTALL firmware unregister + 3600s MenuSystem cache invalidation, preserve Config/upstream/Extra, same-archive reinstall |
| 03 — первый GUI setup | G03 | **INSTALLED-CI PASS** [PR #980](https://github.com/Tolian82/os-zapret2-restyle/pull/980); **OWNER GUI PENDING** | First install v1.0.7 without previous runtime |
| 04 — defaults TCP+QUIC | G04 | **LC-05 native Config INSTALLED-CI PASS** [PR #982](https://github.com/Tolian82/os-zapret2-restyle/pull/982), [real OPNsense #42522906720](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42522906720); **A06 engine/native Start/Stop INSTALLED-CI PASS** [PR #983](https://github.com/Tolian82/os-zapret2-restyle/pull/983), [native #42526188241](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42526188241); **installed-native HTTPS first Apply PASS** [PR #984](https://github.com/Tolian82/os-zapret2-restyle/pull/984), [native #42530805976](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42530805976); **physical owner GUI NOT TESTED** | Ten domains and exact two profiles, installed binary dry-run |
| 05 — независимое сохранение WAN | G05 | **Cold WAN Save/F5 PASS** [#986](https://github.com/Tolian82/os-zapret2-restyle/pull/986); **RUNNING full Apply + Voice/FD9/IPFW WAN roundtrip PASS** [#988](https://github.com/Tolian82/os-zapret2-restyle/pull/988), 16/16; **STOPPED sealed-owner full WAN Apply PASS** [#989](https://github.com/Tolian82/os-zapret2-restyle/pull/989); **instrumented automatic rollback PASS** [#990](https://github.com/Tolian82/os-zapret2-restyle/pull/990); **real assigned TUN/OPT full native Apply PASS** [#991](https://github.com/Tolian82/os-zapret2-restyle/pull/991); **cold WAN-first GUI/configd/Voice/Lab `_18` installed-native S2 PASS** [#42646971454](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42646971454), [PR #992](https://github.com/Tolian82/os-zapret2-restyle/pull/992) merged `ae9efc5b`;  owner-live/real VPN/IPsec OPEN | STOPPED common owner with committed journal must invoke full Apply and restart engine, reverse back with Voice preserved. Automatic failure rollback remains separate from explicit reverse Apply |
| 06 — empty + Voice-only | G06 | **IN PROGRESS:** `_19` real no-action v1.0.7 S2 PASS, `_20` pure Voice merger merged, `_21` zero ordinary parser/validator/IPFW [PR #995](https://github.com/Tolian82/os-zapret2-restyle/pull/995) exact-head CI PASS merged, `_22` one installed original-FD9 G06 Voice-only/combined/no-action S2 PENDING | A09/A11 require actual installed-native PASS, exact zero ordinary divert, stable no-action PID/Stop/Start and foreign Config/IPFW; post-activation fault rollback separately OPEN |
| 07 — Start/Apply/status i18n | G07 | BLOCKED BY G06 | Native AJAX/PID/FD9 + RU/EN states |
| 08 — Standard/Extended Lab pre-Start | G08 | BLOCKED BY G07 | Two actual jobs before first ordinary Start |
| 09 — Stage-60 no-family | G09 | BLOCKED BY G08 | Real failed-target Job and final restore |
| 10 — native regression + GitHub testing package | G10 | BLOCKED BY G09 | A01–A22 source/installed CI, same archive SHA, verified testing publication |
| 11 — owner-live acceptance and docs | G11 | BLOCKED BY G10 | Exact published testing package tested in GUI; stable only by separate authorization |

**Следующая инженерная задача после PR #984:** **G05/LC-06** — настоящий cookie/CSRF `POST /api/zapret/settings/apply` с изменением только WAN на установленной одноразовой OPNsense с ещё отсутствующим upstream, затем с явно сохранёнными пустыми strategy/domains; обычный OPNsense Config save + F5/Get, без runtime/IPFW/engine и без backfill после same-archive reinstall. Под original FD9, реальный устаревший Telegram baseline/invalid logical WAN/foreign or incomplete owner должны отказать без записи; RUNNING WAN-change обязан идти только через полноценную existing native Apply/rollback. G04 first HTTPS Apply уже INSTALLED-CI PASS. G01/G02/G03 и LC-05-Config G04 имеют INSTALLED-CI PASS; owner-browser для всех остаётся NOT TESTED до G11. План последовательно уточняется **только** по результатам завершённых измеряемых этапов или новых решений владельца; принятая цель не меняется молча.
