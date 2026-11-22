# ТЗ_6v5 — единая декларативная конфигурация и точка управления Zapret2

**Редакция требований:** 22.11.2026. **Статус:** требования утверждены владельцем, реализация **не завершена**, новая сборка **не создана**. `ТЗ_6v5` — версия ТЗ, а не версия `.pkg`. Основа: [ТЗ_6v4](TZ_6v4.md), [утверждённый архитектурный контракт](ZAPRET2_DECLARATIVE_RUNTIME_MANIFEST.md), [DEV-065/066/067](../PROJECT_PRINCIPLES.md), [RFC #1229](https://github.com/Tolian82/os-zapret2-restyle/issues/1229). Исполнение: [пошаговый план ТЗ_6v5](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md).

**Неприкосновенный канон upstream:** [manual.en.md Zapret2 — master](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md) имеет нормативный приоритет во всём, что в нём прямо описано о работе движка. **Запрещены повторные испытания и проверка достоверности такого поведения**, включая штатное автоматическое перечитывание HOSTLIST/IPSet и обработку SIGHUP. Проверяем только **свою реализацию и то, что не описано в руководстве**, в соответствии с [DEV-069](../PROJECT_PRINCIPLES.md) и [правилами применения канона](ZAPRET2_UPSTREAM_MANUAL_CANON.md).

**Правило приоритета.** ТЗ_6v5 уточняет и заменяет противоречащие ему пункты ТЗ_6v4, прежде всего о построении runtime, физическом запуске и диагностике. Все не затронутые гарантии ТЗ_6v4 (двухуровневый native Auto, Source Map, P1/P2/FD9, пять списков GUI, исключения, Voice, Strategy Lab, rollback, ограничения на автономные остановки) **сохраняются**. ТЗ_6v2/6v3 и архив P0–P5 — исторические источники, но не альтернативный маршрут внедрения.

## 1. Цель и обязательная цепочка

**Пользователь управляет настройками → платформенный адаптер считывает их → чистый компилятор и валидатор формируют проверенное поколение → единственный исполнитель выполняет Start/Stop → read-only Status и диагностика подтверждают фактическое состояние.**

Результат должен одинаково работать при: (а) совершенно пустой инсталляции без движка и пользовательского runtime; (б) штатных сохранённых настройках; (в) Auto с обновлением Found на лету; (г) Voice ON/OFF; (д) Apply/Restart/Lab/pkg upgrade/engine-version maintenance; (е) неполных и ошибочных состояниях.

**Одна точка физического запуска не означает один файл со всем кодом.** В `zapret_service.sh` размещается ровно одна реализация каждого физического перехода Start и Stop и единый read-only Status. Валидатор, компилятор, парсер XML, политика доменов, генерация стратегий и подготовка транзакций остаются отдельными компонентами. Изменения аргументов запуска не требуют изменения алгоритмов Start/Stop.

## 2. Владелец каждого слоя (обязательная граница)

| Слой | Единственный источник или владелец | Запрещено |
| --- | --- | --- |
| Сохранённые настройки GUI | Штатный `/conf/config.xml` OPNsense, модель `OPNsense/Zapret` и существующий единственный writer | Второй writer Config; второй редактируемый XML/JSON |
| Редактируемые данные | Текущие текстовые YouTube/User/Found/managed, IPSet, Exclude и другие зарегистрированные файлы через `registry.sh` / `storage.sh` и текущий GUI API | Inline дубли содержимого в root manifest; несогласованный параллельный реестр |
| Platform adapter | Read-only извлечение и нормализация модели из XML: OPNsense сейчас, pfSense позже | FreeBSD/GUI/XML-специфика в общем компиляторе |
| Компилятор | Детерминированные Target Mode, effective flags, список и порядок нативных профилей, Voice/Auto/IPFW/`dvtws.args` | Запуск/останов `dvtws2`, собственное владение IPFW/FD9, редактирование пользовательского Config |
| Runtime release | **Один активный**, immutable и sealed `manifest.json` для поколения, со ссылками на проверенные отдельные артефакты | Непроверенный прямой запуск из GUI; произвольные пути/`source`/`eval` |
| Физические Start/Stop/Status | `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`, один original FD9 owner | Другие решения о запуске/остановке в Apply, Lab, Voice, installer, pkg и callback |
| Постоянные native находки | Исходный P1/P2, CAS/WAL/ACK, original FD9 и работающий `dvtws2` | Дополнительный daemon/SQLite, перезапуск ради минуты, новый writer Config |

Транзакционный `shared_apply_operation.py` и существующие sealed runtime/journal остаются **механизмом подготовки/активации/отката**, а не вторым владельцем физического Start/Stop. При наличии уже удерживаемого FD9 внутренний переход получает проверенный контекст унаследованного владельца; новый FD9 не захватывать.

## 3. Единый основной манифест — формат и доверие

Общий для OPNsense и будущей pfSense внутренний формат — **JSON, schema-versioned, immutable и generation-bound**. XML остаётся родным форматом сохранённых пользовательских настроек обеих платформ. **Ни отдельный XML runtime-manifest, ни изменяемый пользователем JSON Config не создаются.**

Нормативные классы полей (точные имена и final schema закрепляются тестовым parity-fixture до активации):

- `schema`, `generation`, `source_snapshot`/verified operation, выбранный `target_mode=all|list|auto`;
- `service`: requested/enabled и строго проверенные параметрические ссылки на WAN, порт divert и политику capture;
- `resources`: зарегистрированные логические ключи, `effective_enabled`, reason/flags, отличающие manual/Found/effective/Exclude/IPSet; **никаких строк доменов или IP**;
- `refs`: ordered profiles, immutable стратегии/Voice/Auto/source-map/`dvtws.args`/IPFW plan и их digest/size/owner receipts;
- раздельные `requested` и `effective` для диагностического projection; пользовательские списки/секреты не копируются в root manifest.

`ref` означает только разрешённый ID реестра или относительный файл **в точно указанном sealed generation**; это **не** открытый путь. Проверяются schema, типы, обязательные значения, generation, полный граф ссылок, владельцы/права, hardlink/symlink policy, realpath/nofollow, размер, SHA-256 неизменяемых артефактов, точный `dvtws.args` и original final native profile map. Исключить traversal, чужие файлы, произвольные include, циклы, shell-исполнение и подмену после валидации; повторно attest перед фактической активацией.

**Два режима изменяемости:** структурные файлы поколения immutable; живые тексты подтверждённых Found/managed обновляются **только** существующим P1/CAS/ACK по проверенным доверенным destination-ссылкам. Их текущий mutable content нельзя навсегда заморозить старым SHA immutable манифеста. Граница active generation при пользовательском Save/Apply не заменяется новым config «на лету» до законной транзакции Apply.

Манифест — **скомпилированная проекция** одного подтверждённого снимка, не второй источник пользовательской истины. Допускаются защищённые архивные поколения для rollback уже начатой операции; активный release — только один. Новый тип состояния не должен создавать параллельную таблицу owner/epoch/journal.

## 4. Компилятор, Target Mode и порядок стратегий

Компилятор читает штатный XML + существующие файлы с текущими лимитами и проверяет: enum, синтаксис и ресурсные пределы, WAN по факту IP-адреса на выбранном интерфейсе (включая разрешённые TUN/OPT), divert/ports, IPFW ownership, доступность движка **на этапе Start**, явные селекторы, голосовые параметры, exclusions, разрешённые профили и точную native argv projection.

| Mode | Нативные рабочие профили | Обучение |
| --- | --- | --- |
| `all` | Без неявных target-селекторов, явные `<HOSTLIST:X>`/`<IPSET:X>` сохранены | Нет |
| `list` | Существующая политика default известных HOSTLIST/IPSET только для профилей без явного селектора; сохранённый order | Нет |
| `auto` | Та же рабочая ступень, что `list`, **затем** разрешённые HOSTLIST learning clones | Только native `--hostlist-auto` соответствующего профиля |

`all` не обходит filter-tcp/udp/l7 и портовые ограничения. Первый **подходящий фактический нативный профиль** выигрывает; код не угадывает профиль по пользовательскому индексу. Обычные известные User/YouTube/IPSET/Voice профили идут **перед** learning clones; каждому eligible learning source — отдельный native inbox и exact source-map в данном generation, без финального observer. Для IPSET-only, смешанных/неоднозначных селекторов и Voice не выдумывать hostlist origin. `<HOSTLIST:auto>` используется **только явно**, shared Found не включает обход автоматически. Не делать brute-force испытаний нескольких стратегий и не путать найденную блокировку с доказанным обходом DPI.

### 4.1. Effective flags: не путать пусто, выключено и ошибку

| Ресурс | Правило |
| --- | --- |
| Global service | `general.enabled=false` → преднамеренно STOPPED; ON запускает только при всех подтверждённых предусловиях |
| Manual YouTube/User | Пустой список → manual disabled; это **не** выключает действующие Found/managed |
| Found/managed | Пустой на старте Found допустим для auto-профиля и активного destination hot-write; содержимое нельзя трактовать как обязательное включение стратегии |
| Exclude Domains/IPSet | Валидный пустой список → disabled; ошибочный непустой → отказ, для IPSet сохраняются запреты `/0`/full-family |
| Voice Telegram/Discord/X/SIP/Custom | Каждый модуль отдельно: checkbox OFF сохраняет draft, не порождает Voice capture; checkbox ON + пустой/неверный IPSet или аргументы → **validation failure**, не silent OFF |
| Auto learning | Только `auto` с хотя бы одним eligibility-proven source-map; `list/all` не создают learning и не включают auto-minute; отсутствие eligible learner объясняется в diagnostic reason |

Соблюдать оригинальные modifiers `!`, `^` и `!^`, PSL/IDNA, порядок source attribution **до** нормализации и Exclude; сохранить защиту User от преждевременного выбора обучающего YouTube. Не повышать PHP лимиты, не менять FormData+JSON, пять редакторов, один bottom Apply, RU/EN и Advanced-only Auto Restart default OFF.

## 5. Интерфейс единого исполнителя и подтверждение результата

**Пять публичных команд:** `zapret_service.sh start|stop|restart|reload|status`. `restart` — полноценный Stop→Start **через те же единственные физические переходы** под original FD9; `reload` — обновление только подтверждённых live-данных без остановки `dvtws2`, нового supervisor/owned IPFW или прекращения divert. `status` — read-only. Прежние `reconfigure`/configd entrypoints остаются совместимыми фасадами Apply planner, а не дополнительными физическими Start/Stop. Привилегированный внутренний вызов может передавать только проверенный release/operation ID, внешний CLI не принимает произвольные пути/argv.

- **Start:** проверяет единственного original owner, закрытость/согласованность предыдущей операции, sealed manifest + exact release, двигатель, WAN, ownership IPFW и конфигурацию capture; запускает ровно один supervisor/`dvtws2`, подтверждает реальное RUNNING и generation/owner; при отказе выдаёт причинную стадию и не оставляет ложного success.
- **Stop:** останавливает **только подтверждённый свой** runtime из действующих защищённых epoch/owner receipts, корректно завершает native retirement с исходными пределами и удаляет только подтверждённые plugin-owned IPFW; может безопасно остановить ранее аттестованный owner **даже если editable source или новый manifest недоступен**, если старое защищённое подтверждение достаточно. Не угадывает по PID и не удаляет чужие процессы/правила.
- **Status:** не запускает compiler/installer/repair, не создаёт файлы, не меняет FD9/journal/Config/службу, не трактует только PID или GUI enabled как RUNNING; показывает **физическое** RUNNING/STOPPED/INCOMPLETE/FOREIGN_OR_UNVERIFIED плюс доступность компонентов, active generation, requested/effective flags и последнюю квалифицированную ошибку. `status --json` — новый совместимый read-only формат, plain `status` сохранить.
- **Apply:** продолжает свои Prep/Validate/Commit/Rollback и единственный Config writer, активирует sealed candidate только внутри существующей durable operation и делегирует физические Stop/Start; при ошибке восстанавливает **семантически** предыдущий verified owner/state, не только возвращает rc=0.
- **Другие вызовы:** Strategies/Voice toolbar, OPNsense System Services, Strategy Lab, protected `pkg-update`, `Установить версию` *upstream engine* (не plugin pkg), Auto Restart и runtime-failure callbacks не реализуют второй service lifecycle. Временный Lab обязательно возвращает доэкспериментальное RUNNING→RUNNING и STOPPED→STOPPED на норме/ошибке/timeout/cancel.

Запрещены самопроизвольный Stop/Restart ради Auto-detect, `SIGSTOP/SIGCONT`, второй `dvtws2`, обход оригинального FD9, «лечебный» `pkill`, `rm pid`, широкий IPFW flush и автоматическое исправление чужого owner. Операторские explicit Stop/Restart/Apply имеют приоритет доступности над **неподтверждёнными** новыми Auto-событиями, сохраняя уже committed Found/managed и original safety (DEV-064).

### 5.1. Reload — только доказанные изменения без остановки

**Утверждённое требование:** при «Применить» сначала проверять, можно ли применить весь candidate без Stop/Start. Если да — `reload`. Если нет — один guarded полный `restart`. **Запрещено** переименовать старый `reconfigure` в `reload`, сохранив скрытую остановку.

**Аксиома из канона, без проверки:** [официальный `manual.en.md`](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md), разделы **Filtering by lists** и **Signals**, прямо устанавливает автоматическое перечитывание hostlist/ipset после изменения файлов **без перезапуска** и принудительное перечитывание по `SIGHUP` **при обработке следующего пакета**. Это истинное нормативное поведение Zapret2 — **не гипотеза, не native test gate и не требование повторно доказывать механизм**. Руководство здесь не задаёт алгоритм выбора действия в нашем GUI, FD9/Config writer, точный target PID, атомарность нескольких файлов, IPFW-таблицы и lifecycle плагина; **только эти наши неописанные в нём части** должны проверяться. Не подменять сведения канона ссылками на другие файлы исходников или local benchmarks.

**Все условия `RELOAD_SAFE` обязательны:**

1. Доказан оригинальный `RUNNING`: PID+birth+argv, supervisor, committed sealed generation, original FD9/epoch и только свои IPFW. Не должно быть pending/foreign/incomplete operation.
2. Pure compiler сравнил verified active и candidate. Неизменны engine executable/version, exact argv, native profile order/first-match/source map, Target Mode, Voice параметры, WAN, divert port/IPFW, logical list IDs и *пути* существующих ссылок. Может отличаться **только содержимое** уже подключённых и проверенных HOSTLIST/IPSet, включая Exclude. Изменение самой ссылки/селекторов, неиспользуемых данных или структурной схемы не превращается в reload.
3. Списки подготовлены и валидированы через текущий registry/storage, original FD9/`shared_apply_operation`/единственный Config writer, а protected Found/managed — через P1/CAS/ACK. Есть old-byte snapshots, revision checks и возможность доказуемого rollback. Для нескольких файлов нельзя обещать мгновенную атомарность видимости в движке: если нужен недостижимый all-or-nothing cutover — `RESTART_REQUIRED`.
4. Перед сигналом повторно проверить точный `dvtws2` PID+birth/argv owner. При необходимости `SIGHUP` отправляется **только** этому процессу, без `killall`, `SIGSTOP/SIGCONT`, остановки supervisor, изменения IPFW или второго engine.
5. **Проверяется наша операция, а не перечитывание Zapret2.** Подтвердить успешную запись/атомарную замену разрешённых файлов, сохранность own PID+birth/argv/supervisor/IPFW, адресную отправку `SIGHUP` (если нужна), корректный FD9/journal и ошибочные сценарии. В каноне сказано, что сигнал приводит к перечитыванию **при следующем пакете**: если плагин лишь доставил запрос, его собственный статус `RELOAD_REQUESTED` не должен притворяться подтверждением уже обработанного пакета; **отдельного эксперимента по проверке перечитывания в движке не требуется и проводить его запрещено**. `APPLIED_VERIFIED` описывает только действительно завершённые и проверенные шаги **плагина**, с явной границей объёма. При failed/partial list commit — восстановление предыдущего состояния и честный `RELOAD_UNCERTAIN/REQUIRES_REVIEW`. **Никакого тайного restart после failed reload**.

Прямой `reload` на намеренно STOPPED не делает Start: `NOT_RUNNING`. WAN-only Save при отсутствии движка/manifest и prestart Lab G05→G08 сохраняют независимость. Фоновый P2 Found/managed обновляется своим существующим hot-write механизмом и не вызывает команду reload службы автоматически.

### 5.2. Restart и правило выбора при «Применить»

`restart` — **полный** Stop→Start под одним original FD9 с original P2/epoch retirement, новым процессом и проверенным новым owner/IPFW, из текущей sealed операции. Если Start после Stop не удался, выполнять прежний semantic rollback по тому же журналу и честно показывать `RESTART_FAILED`/`RESTORE_FAILED`; никогда «Перезапущена» по одному rc. `restart` на намеренно STOPPED не должен скрыто запускать службу, для этого существует `start`. Auto-minute не инициирует restart.

**До мутаций** Apply planner сравнивает старый verified runtime и новый effective candidate:

| Состояние / изменение | Единственное решение |
| --- | --- |
| STOPPED + Enabled OFF | `SAVE_ONLY` |
| STOPPED + Enabled ON + готовый engine/WAN/manifest | `START` |
| RUNNING + Enabled OFF | `STOP` |
| RUNNING + effective snapshot полностью тот же | `NO_CHANGE` |
| RUNNING + только подтверждённые изменения содержимого подключённых HOSTLIST/IPSet | `RELOAD` |
| RUNNING + новые DPI args, профили, Lua/Voice, Target Mode, engine, WAN, divert/IPFW, порядок/source refs | `RESTART` |
| RUNNING + смешанные structural/list changes | `RESTART` **один раз**, без предварительного reload |
| INCOMPLETE/FOREIGN, stale owner, неподтверждённая attestation | `REFUSE` |

Решение не принимается по имени изменённого поля GUI. Сравниваются exact structural fingerprints, зарегистрированные mutable refs и активные поколения. Тот же original `shared_apply_operation` и `SharedConfigCommit` отвечают за atomicity, Config/list writes и rollback: **никакого второго writer или журнала**. Не выдавать HTTP 200 как verified success без terminal state. `NO_CHANGE` не посылает сигнал, `RELOAD_REQUESTED` не лжёт о фактической активации, и потеря подтверждения не вызывает перезапуска.

### 5.3. Расширяемые параметры CLI

Команды имеют вид `zapret_service.sh <action> [declared options]` (дополнены `start|stop|restart --force`, глобальным и командным `--help`; см. §5.5–5.6) со строгой проверкой action-specific allowlist, длины/количества аргументов и rc 64 `INVALID_ARGUMENT` для неподдерживаемых. Минимум: `status --json` read-only, `reload --check [--json]` read-only diff/preflight без signal/записи; остальные базовые команды без необязательных параметров. В будущем допустимы аутентифицированные root-only `--expect-generation=<id>`/`--operation=<sealed-id>` **только** после native qualification original FD9, не произвольные пути. Нельзя принимать произвольный `--manifest`, `--args`, PID, signal, shell fragments, `eval`, runtime env override. Прежние configd/installer/Lab внутренние action имена могут быть совместимыми фасадами, не новыми физическими процессными менеджерами.

### 5.4. Ошибки launcher, dvtws2 и жизненного цикла GUI RU/EN

Нормализованный lifecycle receipt: `schema, action, operation_id, code, stage, exit_status, runtime_before, runtime_after, active_generation, verification, stderr_excerpt, log_ref`. `verification=verified|requested|uncertain|refused` обязателен для честного различения engine reload requested и confirmed. Реальные причины native `dvtws2`/supervisor: stderr, early exit, signal, log stage и код, bounded sanitized excerpt. Запись в прежнее protected error storage (не отдельная БД/писатель); статус read-only видит последнюю ошибку, в том числе delayed engine exit. Не показывать конфиги/полный argv, приватные домены/IP, токены или full debug, не заменять известную первопричину общим «ошибка»; secondary rollback error отдельно.

Примеры кодов, реализовывать только при настоящем producer: `ENGINE_NOT_INSTALLED, WAN_REQUIRED, MANIFEST_INVALID, FD9_BUSY, FOREIGN_OWNER, ENGINE_EXIT_EARLY, STOP_FAILED, RESTART_FAILED, RESTART_REQUIRED, RELOAD_NOT_SUPPORTED, RELOAD_REQUESTED, RELOAD_FAILED, RELOAD_UNCERTAIN, RESTORE_FAILED`. Если engine cause неизвестна — `ENGINE_ERROR_UNCLASSIFIED` с bounded safe excerpt. GUI отображает релевантные ошибки этих пяти команд, прежде всего Start/Stop/Restart, через уже существующие RU/EN уведомления.

**V5-12 остаётся строго ограниченным** переводами старого Start/Stop/Restart и связанными service transitions из Apply/Voice/Lab/pkg/Boot: KEEP/ADAPT/REMOVE по реально достижимому producer; новые `RELOAD_*`/restart error добавляются RU/EN по аналогии, **только когда реально возникают**. Общий перевод других ошибок Voice/Strategies/Lab вне scope. Поддерживаемые исторические receipts не теряют читаемость.

**V5-13:** проверены **только интеграционные действия плагина**: list-only decision, безопасная запись, точная доставка сигнала (если требуется), отсутствие смены PID/supervisor/IPFW, NO_CHANGE без сигнала, structural/mixed→полный Restart, unsafe/uncertain→refuse. **Не проверять** автоматическое reread и SIGHUP-семантику самого Zapret2 — они уже нормативно установлены `manual.en.md`. **V5-14:** все пять команд/strict options/native error receipt/GUI RU+EN lifecycle путь имеют source+native доказательство до testing package.

### 5.5. Аварийный параметр `--force` — только для подтверждённого зависшего собственного процесса

**Решение владельца от 23.11.2026:** поддержать три команды оператора: `zapret_service.sh start --force`, `stop --force`, `restart --force`. Параметр означает **разрешение на ограниченную принудительную остановку только ранее аттестованного собственного зависшего runtime**, если штатная graceful Stop/TERM с установленным timeout не завершила процесс. **Не** означает обход FD9, sealed owner, process identity, journal/P1, чужого PID/IPFW, WAN/manifest или права на безусловное `kill -9`.

**Единая безопасная последовательность под original FD9:**

1. Команду с `--force` принимает только явно уполномоченный root CLI/подтверждённый администраторский context; GUI Apply, Lab, Auto-minute, boot, pkg updater, фоновые callbacks **никогда не добавляют флаг автоматически**. Сохранять факт явного использования в текущем protected operation receipt (action, force_requested, original owner, stage, result), без нового писателя Config и без постоянного включения режима.
2. Проверить, что PID (child `dvtws2`, monitor/supervisor, если требуется) принадлежит **именно текущему подтверждённому поколению плагина**: sealed owner/FD9/epoch, точный исполняемый файл и командная строка, PID **и время создания/birth**, process inventory и собственные IPFW. Не полагаться только на `/var/run/*.pid` или совпадение имени. Устаревший PID-файл, отсутствующий процесс, PID reuse и чужой экземпляр — разные состояния; если нет аттестации, `FORCE_OWNER_UNVERIFIED`/refusal, **ничего не убивать и не удалять наугад**.
3. Сначала запретить/остановить **только подтверждённый собственный** supervisor/respawn и сделать обычный защищённый graceful Stop/TERM с bounded wait. Если owner уже корректно остановлен — `stop --force` возвращает проверенный STOPPED без лишнего сигнала. Эскалация `SIGKILL` допускается **только если процесс сохранил тот же PID+birth+exe/argv+epoch после таймаута** и повторной проверки непосредственно перед сигналом. Между `TERM` и `KILL` повторная аттестация обязательна, чтобы не убить новый процесс после PID reuse. Никаких `pkill`/`killall`/wide PID scan как действия по умолчанию.
4. После эскалации отдельно проверить фактическое исчезновение старого child/monitor, отсутствие автоматического respawn и новых неаттестованных процессов; завершить существующий original P2/N/epoch retirement и очистить **только** подтверждённые plugin-owned IPFW по штатной процедуре. Нельзя считать `SIGKILL`/exit-status=0 успешным Stop. Если процесс не завершился, ownership изменился, journal не закончен или kernel rules не восстановлены — `FORCE_TERMINATION_UNCONFIRMED`/`INCOMPLETE`, прежние журналы остаются для восстановления, новый Start запрещён.
5. **`stop --force`**: только guarded Stop с возможной эскалацией; без запуска. **`restart --force`**: тот же guarded forced Stop, а затем **полный** стандартный Start **только после доказанного завершённого STOPPED/retirement**. Если Stop отказал — **никогда** не стартовать второй `dvtws2`; если последующий Start отказал — честный `RESTART_FAILED` и существующий semantic rollback, без фиктивного RUNNING. Намеренно STOPPED не становится RUNNING от `restart --force`.
6. **`start --force`**: если уже RUNNING и healthy — не убивать работающую службу, не запускать дубль (обычный idempotent/already-running результат). Если подтверждённый зависший **старый** собственный процесс препятствует Start — выполнить **ровно ту же** безопасную forced Stop/retirement и только затем обычный Start из валидного active release. Если старый owner недоказан, Config/WAN/engine/manifest не готовы или orphan/foreign — refusal, не широкая «автоочистка».
7. **Сохранность:** не менять пользовательские списки, XML, Config, debug/Found/managed, защищённые older/pending receipts ради `--force`; no second writer, no IPFW flush чужого диапазона, no SIGSTOP/SIGCONT. При любой неопределённости оставлять diagnosis/stage, а не маскировать дефект принудительным убийством. **Ни один принудительный путь не становится implicit fallback обычного Stop/Start/Apply/Reload.**

**Проверка V5-15:** на disposable OPNsense/контролируемом процессе: graceful success (без KILL), зависший подтверждённый child/monitor (TERM timeout→exact-owner KILL→verified STOPPED→Start при необходимости), уже STOPPED, healthy RUNNING, stale PID-file без процесса, PID reuse/foreign process, PREPARED/incomplete owner, FD9 busy, unkillable process, SIGKILL race и failure retirement/IPFW. В негативных случаях **ни один чужой PID/IPFW/Config не тронут**, двойного `dvtws2` нет, durable journal не стирается. На рабочей OPNsense владельца **не** провоцировать зависания/force-KILL ради теста.

### 5.6. `--help` — публичная безопасная справка

`zapret_service.sh --help` и `zapret_service.sh <command> --help` **обязаны возвращать краткую понятную справку** и завершаться с rc=0 **без захвата FD9, работы с PID/IPFW, чтения Config, компиляции, диагностики движка, файловых мутаций и запуска**. Показать usage, все пять команд, `--force` (только для `start|stop|restart` с предупреждением о проверке ownership), `status --json`, `reload --check [--json]`, текущие поддерживаемые разрешённые флаги и типовые коды отказов. Никакой секретной информации/путей к private runtime из справки.

Пример краткой формы:

```text
Usage: zapret_service.sh <start|stop|restart|reload|status> [options]
  start      Start the configured service
  stop       Gracefully stop the owned service
  restart    Full stop and start
  reload     Apply supported live list updates without restart
  status     Show actual service state
Options:
  --force    start/stop/restart only: allow guarded termination of a hung OWNED process
  --help     Show help and exit (also available per command)
  --json     status; with reload --check
  --check    reload: read-only eligibility check
```

Не поддерживаемые сочетания, например `reload --force`, `status --force`, повторяющиеся/неизвестные опции или `start --check` — `INVALID_ARGUMENT`/rc=64 **без побочных действий**. `--help` на уровне глобального и командного entrypoint отрабатывает **до** lifecycle dispatch/lock, без обхода безопасности иных вызовов. Новые future options — только явно добавленные в action-specific allowlist.

**Критерий V5-16:** текст обеих справок содержит актуальные команды/флаги, exit 0, подтверждённые no-write/no-lock/no-PID effects; parser отклоняет недопустимые комбинации. При обновлении интерфейса справка и тесты меняются одновременно.

## 6. Чистая установка и пять независимых состояний

На пустой OPNsense installation lifecycle раздельно оценивает: **plugin package** present/absent (если отсутствует, его GUI/CLI физически не существует: определить через platform/package manager), **engine binary** installed/valid/absent, **saved config** initialized/invalid/absent, **active sealed manifest** valid/stale/absent, **runtime** RUNNING/STOPPED/INCOMPLETE/FOREIGN_OR_UNVERIFIED. Нельзя объединять их в один boolean «установлено».

**First install:** нет движка, GUI settings и active release → GUI рендерится, `status` не падает, сообщает `ENGINE_NOT_INSTALLED`/`CONFIG_UNINITIALIZED`/`MANIFEST_UNAVAILABLE` по своему классу, физически STOPPED. Первый раз предзаполняются только уже утверждённые YouTube Domains и базовые YouTube TCP/QUIC **при доказанном отсутствии сохранённых данных**; глобальная служба OFF; не выполнять скрытое скачивание upstream или первый Start. Установка версии движка — **явное** действие через существующую процедуру, затем валидация, Apply и пользовательский Start. Пустая пользовательская Strategy допустима по установленному контракту GUI; это не инструкция стартовать невалидные профили.

**Reinstall/upgrade:** сохранившиеся Config/manual/Found/Exclude/Voice/WAN и статус service OFF не перезаписываются дефолтами; normal uninstall сохраняет пользовательские данные, отдельный explicit purge следует принятому контракту. Слабый/отсутствующий runtime manifest не авторизует новый Start и не уничтожает неизвестный процесс. Ни один «пустой конфиг» не означает команду Stop чужого процесса.

### 6.1. Обязательный WAN-first / Laboratory-before-first-Start (LC-06, LC-11, LC-12, G05/G08)

**Это сохранение уже принятого и реализованного поведения, а не новая возможность.** Нормативные источники: [LC-06/06A–C и LC-11/12](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md), [G05 — WAN-only native](../verification/G05_WAN_ONLY_NATIVE.md), [G08 — настоящая лаборатория до первого ordinary Start](../verification/G08_PRESTART_LAB_NATIVE.md). Историческая installed-native проверка G08 на одноразовой OPNsense 26.7 (09.11.2026) прошла для Standard и Extended при сохранённом WAN, пустых пользовательских Traffic Strategy/YouTube Domains, Enabled=OFF, ранее **никогда не запускавшемся обычном** dvtws2. Достигнутые Stage 40 TARGET_ACCESSIBLE и Stage 90 STOPPED подтверждают нормальный Lab workflow и восстановление, **но не** подбор DPI на заблокированном домене.

**Обязательная последовательность «WAN первым»:**

1. После чистой установки пользователь **может сохранить только** `general.waninterface` через обычный нижний Strategies Apply при `general.enabled=0`, отсутствующем upstream engine, пустых/непустых первоначальных defaults либо намеренно очищенных Traffic Strategy/списках. Под original FD9 и единственным `SharedConfigCommit::persist()` сохраняется ровно разрешённое изменение WAN в штатном `config.xml`; readback и F5 подтверждают результат. Никакого полного runtime-build, запуска dvtws2, новых IPFW-правил или требования существующего sealed active manifest. Пустые редактируемые поля и выбранный WAN сохраняются при reinstall. Для STOPPED с ранее sealed Common owner действуют прежние полные transaction gates; WAN-only fast path нельзя применять слепо к старому журналу.
2. **Перед** любым engine/model/strategy/manifest preflight и созданием `job.*`, включая direct configd и Standard/Extended/Circular Lab, проверить **сохранённый** WAN. WAN отсутствует → `wan-required`, RU «Укажите WAN интерфейс», EN “Select a WAN interface”; WAN выбран, но штатно не разрешается в подтверждённый назначенный physical interface → `wan-invalid`. Использовать действующий original `wan_preflight`/`config_resolve_interface()` для разрешённых WAN/OPT/TUN (включая документированные случаи без IPv4), не читать из stale `zapret.conf` и не считать несохранённый dropdown истиной. Для нормального Start также WAN-first; отсутствующий WAN запрещает активацию, **но не** пассивный Save, Stop, setup/install или read-only Status.
3. Только **после WAN** проверять установленность и исправность upstream Zapret2. WAN есть, но engine отсутствует → типизированный `engine-not-installed` (либо эквивалентная согласованная форма `ENGINE_NOT_INSTALLED` в unified status) **без создания Lab Job, PID, IPFW или изменения Config**. Наличие одного только WAN не делает отсутствующий движок работоспособным.
4. При валидном сохранённом WAN и **установленном** engine Standard и Extended Laboratory должны запускаться из обычного `STOPPED`/`Enabled=OFF` даже если нет пользовательской стратегии, обычных HOSTLIST/IPSet, ранее сгенерированных `dvtws.args`, active sealed runtime manifest, рабочего ordinary generation/PID и первого Start. Lab использует свою **временную** конфигурацию и проверенные ограниченные Lab IPFW/engine resources под original FD9 и сохранённым WAN; не компилирует/не активирует обычную службу и не подставляет искусственно непустой Traffic Strategy.
5. По normal/completion/cancel/error/timeout Lab сохраняет доэкспериментальное состояние: для этого сценария **STOPPED→STOPPED**, без обычного dvtws2, без остаточных лабораторных PID/IPFW (диапазон 19100–19131), без нового обычного sealed release и Config writer. Для изначального RUNNING продолжает действовать RUNNING→RUNNING. Чужие процессы/IPFW и неопределённые original FD9/journal запрещают опасное вмешательство; восстановление подтверждать реальным terminal receipt Stage 90, не одним HTTP успехом.

**Разделить readiness:** `WAN_SAVED` и `LAB_READY` не означают `ORDINARY_RUNTIME_READY`. Компилятор основного immutable JSON и его требование active sealed manifest относятся к ordinary Start/Apply; они **не являются предпосылкой Lab**, работающей со своей доверенной кратковременной job-конфигурацией. Не допускать обратной зависимости «для запуска лаборатории сначала надо создать рабочую стратегию и запустить обычную службу».

**Таблица обязательных отрицательных и положительных результатов:**

| Сохранённый WAN | Upstream engine | User strategy / обычный runtime | Результат |
| --- | --- | --- | --- |
| Не выбран | Нет либо есть | Любые | `wan-required` до engine и до Lab Job |
| Выбран, но не разрешается штатно | Есть | Любые | `wan-invalid` без Job/Config/IPFW мутации |
| Выбран и разрешён | Нет | Пустые / STOPPED | `engine-not-installed`, Job не создаётся |
| Выбран и разрешён | Есть | Пустые / STOPPED / нет active ordinary manifest | Standard и Extended Lab работают, Stage 90 проверяет STOPPED→STOPPED |
| Выбран и разрешён | Есть | RUNNING/сохранённый ordinary owner | Lab сохраняет исходный RUNNING→RUNNING и прежние FD9/Config/IPFW гарантии |

**Гейт приёмки V5-11:** использовать реальные [G05](../verification/G05_WAN_ONLY_NATIVE.md) → native upstream setup (без ordinary Start) → [G08](../verification/G08_PRESTART_LAB_NATIVE.md) на одном одноразовом OPNsense: cookie/CSRF нижний WAN-only Apply → F5 → физический `/conf/config.xml` → двигатель установлен → реальные `/api/zapret/strategy_lab/start/status/result` Standard RU + Extended EN → Stage 90 verified STOPPED и отсутствие временных ресурсов. Это обязательная regression строка **до** единого launcher cutover, повторяется **после** интеграции нового manifest/Status и на итоговом exact-head native тесте. Не выдавать старый G08 PASS за доказательство нового кода.

## 7. Единый контракт диагностики

Нормализованное ограниченное событие `schema`, `timestamp`, `stage` (`install/config/manifest/wan/ipfw/engine-start/engine-stop/voice/auto-minute/apply/lab-restore/pkg-update`), `code`, `operation_id`, `generation`, `exit_status` (nullable), `runtime_state`, `message`, bounded `stderr_excerpt`, проверенный `log_ref`. Источник: реальные ошибки native `dvtws2`, supervisor, setup, configd, renderer, IPFW, P1/P2 и Lab; **сохранять их причинный контекст**, а не всё заменять текстом «не удалось».

Обязательные примеры кодов: `ENGINE_NOT_INSTALLED`, `ENGINE_INVALID`, `CONFIG_UNINITIALIZED`, `CONFIG_INVALID`, `MANIFEST_UNAVAILABLE`, `MANIFEST_INVALID`, `MANIFEST_STALE`, `WAN_UNAVAILABLE`, `IPFW_ATTACH_FAILED`, `ENGINE_EXIT_EARLY`, `VOICE_TARGET_INVALID`, `LAB_RESTORE_FAILED`, `RUNTIME_INCOMPLETE`, `FOREIGN_OWNER`. Коды стабильные; исходный rc/exit/stderr отдельными полями. События записывать в существующее защищённое ограниченное/ротируемое диагностическое хранилище; статус/GUI читают **последнюю релевантную запись**, без формирования ложной новой ошибки от самого чтения.

Не раскрывать полный `config.xml`, IP/домены/списки, raw args/debug, токены и секреты; stderr whitelist/редакция, ограничение байт/строк, корректная UTF-8 и безопасный log-ref. Не выдавать success из-за подтверждения «процесс есть», если generation/IPFW/предыдущий runtime не восстановлены. CLI, GUI, конфигурационные операции и Lab обязаны показывать совместимую первопричину/стадию и правдивое итоговое состояние.

### 7.1. Только ошибки прежнего Start/Stop/Restart: актуальность RU/EN GUI

**Уточнённое решение владельца от 22.11.2026:** ревизия переводов при введении единого физического исполнителя касается **исключительно** ошибок и пользовательских уведомлений, связанных со **старым запуском, остановкой и перезапуском** обычной службы Zapret2. Проверять и исправлять нужно также те сообщения Apply, Lab, Voice, package update, boot/recovery и установки версии движка, **которые непосредственно сообщают о вызове/отказе/результате физического Start/Stop/Restart** или восстановлении прежнего service state. **Не требуется** общий аудит локализации всего GUI, IPSet, списков, отдельных полей валидации, поиска кандидатов Lab, обновления ресурсов или произвольных ошибок PHP.

**Что уже имеется и должно переиспользоваться:** `general.volt` содержит `localizeStrategiesApplyError()`, RU/EN уведомления об управлении службой; `voice.volt` содержит двуязычные статусы общего runtime и отдельные сообщения о неуспешной реконфигурации; `diagnostics.volt` и Lab worker messages локализуют остановку/восстановление `RUNNING/STOPPED/RESTORE_FAILED`; `ServiceController.php`/`SettingsController.php` применяют `gettext()` и структурированные `reason`. Это **места для точечного аудита**, а не разрешение переписывать все их словари.

**Граница охвата (строго):**

| Входит в V5-12 | Не входит |
| --- | --- |
| Старт/останов/перезапуск обычной службы по GUI, System Services, CLI/configd/boot и исходная RU/EN ошибка при их отказе | Остальные ошибки форм, редакторов, Target Mode, HOSTLIST/IPSet и native parsing, если они не означают отказ Start/Stop/Restart |
| Ошибка Stop/Start при Apply, Voice Apply, Lab restore, protected pkg-update, engine-version maintenance или callback, включая исходный/итоговый service state | Валидация Voice IPSet, исходных пользовательских данных, параметры/результаты поиска Lab, установки/загрузки ресурсов **как таковые** |
| Ошибки физического Start при engine absent/invalid, WAN guard, sealed manifest/argv/IPFW/FD9 owner, early exit и при повторном Start после Stop | Массовая переработка текущих `gettext`, словаря `localizeVoiceErrors()` или всех `native-preflight-*` исключительно ради унификации |

**Порядок миграции:**

1. **INVENTORY:** для **каждого старого lifecycle message** определить живую цепочку `source emitter/function → reason/stage/exit → configd/API → конкретная кнопка/обработчик GUI → русский и английский текст`, а также физический переход, который вызвал ошибку. Проверить исторические protected operation receipts и сохранённые Lab jobs: они могут по-прежнему требовать совместимого текста.
2. **KEEP:** сообщение по-прежнему реально возникает при canonical Start/Stop/Restart → оставить его в обеих локалях, даже если оно редко; проверить показ при соответствующей injected failure.
3. **ADAPT:** прежний lifecycle source или stage исчезает, но тот же смысл сохраняется в едином исполнителе → обновить выдаваемый `reason/code` и обе RU/EN ветки **вместе**, не оставляя недостижимую старую строку. Не делать общий rewrite не относящихся к lifecycle валидаций.
4. **REMOVE:** конкретное сообщение **о старом Start/Stop/Restart** подтверждённо больше не производится и не нужно для поддерживаемого восстановления/истории → удалить только этот obsolete key из русского и английского обработчиков и связанных тестов. Не трогать другие ошибки, даже если они находятся рядом в том же словаре.
5. **ADD:** новый реальный отказ физического Start/Stop/Restart (например invalid sealed manifest, engine early exit, FD9 conflict, невозможность восстановить state) полезен пользователю → добавить понятное RU/EN уведомление **через существующий GUI путь** с защищёнными `code/stage/rc` для диагностики. Нет доказуемого producer — нет нового переводного ключа.

Не смешивать `start_failed` с `stop_failed` или `restart_failed_after_stop`; не писать «перезапуск выполнен» без проверенного RUNNING. При недостоверном результате — честный локализованный статус и безопасная ссылка на диагностику, без сырых аргументов, IP/доменов/секретов и backend stderr. Сервисный Status читает факты, а не подменяет результат запуска.

**Гейт проверки:** точечная таблица `old lifecycle message → KEEP/ADAPT/REMOVE → new lifecycle producer → GUI receiver → RU/EN → test`; controlled negative tests и два языка браузера для маршрутов Start/Stop/Restart, включая вызовы из Apply/Lab/pkg **только в части переходов службы**. Для снятых ключей тест отсутствия и доказательство отсутствия старого producer/поддерживаемого replay. Никакого требования чистить всю локализацию продукта.

**V5-12:** в **подмножестве сообщений старого Start/Stop/Restart** нет необъяснённых недостижимых RU/EN ошибок; текущие и новые реальные lifecycle failures достигают нужной GUI-страницы и дают корректное сообщение на **обоих** языках, а obsolete переводы адаптированы/удалены без нарушения исторического чтения и без ложного успешного Start/Restart.

## 8. Непрерывный Auto и неизменность защищённого хранилища

Двухуровневая схема ТЗ_6v4 остаётся обязательной: каждая квалифицированная native строка → original minute P2 → origin map → PSL/Exclude/CAS → постоянный YouTube/User/shared Found → live managed HOSTLIST → **только после подтверждённого destination** безопасная очистка соответствующего native inbox. Пустые Found могут наполняться позже без изменения immutable manifest, `Apply` или Restart. Сохраняются original FD9/P2a/P2b/P2c, inode/FD/epoch и WAL/ACK, защита от concurrent append, неразрушительный отказ для устаревших источников. `zapret-hosts-auto.txt` не мигрировать. Не добавлять observer, отдельный писатель или остановку трафика ради диагностики.

**Граница проверки Auto по DEV-069:** разделы канона [Filtering by lists / Autohostlist failure detector](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md) описывают алгоритм детектора и его срабатывание; это **не объект наших испытаний**. Для проверки **нашего** двухуровневого Auto использовать достоверное уже сформированное native событие или входную fixture и контролировать лишь Source Map→P2→Found/managed→ACK, owner/FD9 и отсутствие нежелательного restart; не воспроизводить сетевую блокировку ради доказательства описанного upstream механизма.

## 9. Переносимость, границы проекта и известные дефекты

Модульное ядро компилятора и JSON/registry/diagnostic contracts platform-neutral. OPNsense adapter реализует чтение XML, configd/pkg/ownership, FreeBSD/OPNsense-specific WAN/IPFW. В будущем pfSense получает свой XML model/service/install adapter и собственную **отдельную** native compatibility qualification; никакого обещания, что текущий OPNsense package запускается на pfSense без проверки ABI/брандмауэра. Не вводить парный XML manifest «про запас».

**Не объявлены устранёнными:** [#1224](https://github.com/Tolian82/os-zapret2-restyle/issues/1224) Lab stage90/99 `RESTORE_FAILED`, [#1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223) YouTube native no Found, [#1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225) route parity; [#1210](https://github.com/Tolian82/os-zapret2-restyle/issues/1210) IPFW/routing reload — отдельный подтверждённый issue, без самовольного auto-repair. Draft [PR #1228](https://github.com/Tolian82/os-zapret2-restyle/pull/1228) реализует лишь часть старой делегации Lab/pkg; **не** является ТЗ_6v5. Порог native learning 1 vs default 3 — гипотеза/направленная проверка #1223, не доказанный корень. Уже рабочие owner Strategies Apply без/с изменениями не превращаются в новый FAIL.

## 10. Приёмка ТЗ_6v5 — доказуемые результаты

| ID | Обязательный проверяемый результат |
| --- | --- |
| V5-01 | Чистые plugin/engine/config/manifest/runtime сочетания; безопасные status/GUI и никакой автоматической установки/Start |
| V5-02 | Сохранение первого setup/default ONCE и неизменность всех пользовательских данных после reinstall |
| V5-03 | Pure compiler RED→GREEN и **эквивалентные** старому argv/capture/source-map результаты на `all/list/auto`, Voice ON/OFF, пустых/больших/неверных списках, exclusions и first-match |
| V5-04 | Ссылочный root JSON, полная structural attestation/ownership, tamper/stale rejection, immutable promotion и безопасный rollback |
| V5-05 | Один физический Start/Stop/Status и доказанная трассировка **каждого** UI/CLI/Apply/Lab/installer/pkg/callback пути к нему; нет второго process/IPFW writer и nested FD9 |
| V5-06 | RUNNING/STOPPED/INCOMPLETE и last-error `status --json` соответствуют реальной native картине; stderr/rc/stage сохраняются и редактируются |
| V5-07 | Native Lab RUNNING→RUNNING, STOPPED→STOPPED и ошибка/timeout/cancel/прерванное восстановление дают правдивые receipts |
| V5-08 | При **заранее данном** реальном native событии или достоверной fixture **наш плагин** доставляет данные через Source Map/P2 в правильные persistent Found и managed, без Apply/Restart; **не проверять** описанный в каноне upstream Autohostlist detector |
| V5-09 | Native OPNsense и защищённые upgrade/rollback, Voice/Strategies Apply, WAN и пакетные сценарии проходят на **точном** исходнике |
| V5-10 | Только после source/native приёмки, включая V5-11–V5-16, — один testing `.pkg` с SHA/ABI/source identity; отдельно owner-live проверка на физическом устройстве; stable/pfSense не объявлять по одному CI |
| V5-11 | WAN-only Save при `Enabled=OFF`, отсутствии upstream и отсутствии user strategy сохраняет WAN; после явной установки engine Standard/Extended Lab работают до первого ordinary Start без active runtime manifest, завершают Stage90 STOPPED→STOPPED и не оставляют ресурсов. Отсутствие WAN первее отсутствия движка, и ни один отказ не создаёт Job/IPFW |

| V5-12 | **Только для сообщений прежнего Start/Stop/Restart**, включая их физические переходы через Apply, Voice, Lab restore, package update и boot: source→reason/stage→GUI→RU/EN проверены; действующие сохранены/адаптированы, недостижимые старые переводы удалены в обеих локалях без ущерба историческому recovery; новые lifecycle failures информируют пользователя на двух языках. Остальные GUI-переводы вне охвата |
| V5-13 | На exact-head проверены только **наши** diff-planner, сохранение файлов, точная адресная доставка SIGHUP, unchanged PID/supervisor/IPFW и выбор NO_CHANGE/RELOAD/RESTART/START/STOP/SAVE_ONLY; **само перечитывание HOSTLIST/IPSet движком не испытывать**, оно принято из канона. Нет скрытого рестарта после ошибки |
| V5-14 | Пять команд и строгие action options, typed native dvtws2/supervisor errors, truthful verification, RU/EN lifecycle GUI delivery проверены на exact FreeBSD native перед тестовой сборкой |
| V5-15 | `start|stop|restart --force` ограничен явным оператором, original FD9 и точной owner/PID+birth/epoch аттестацией: TERM→bounded wait→повторная проверка→KILL только своему зависшему процессу; terminal Stop/retirement/IPFW проверяются, чужие процессы не затронуты, второй dvtws2 никогда не стартует |
| V5-16 | Глобальный/командный `--help` выдаёт актуальный usage с пятью командами и опциями, rc0 без FD9/Config/PID/IPFW; запрещённые `--force` сочетания и неизвестные options возвращают rc64 без побочных действий |

**Граница фактов на 22.11.2026:** merged documentation-only `main v0.6.5_121`, установленная у владельца тестовая `_117`, ручной Stop→Start RUNNING и два Strategies Apply PASS. ТЗ_6v5 — **критерий будущей реализации**, а не сообщение о завершённой работе. Исполнение идёт строго по [шагам и блокирующим гейтам](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md).
