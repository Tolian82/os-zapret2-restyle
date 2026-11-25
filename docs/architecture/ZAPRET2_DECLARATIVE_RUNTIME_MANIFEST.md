# Утверждённая архитектура единой декларативной конфигурации Zapret2

> **Новая нормативная редакция:** [ТЗ_6v5](TZ_6v5.md) и [обязательный step-by-step S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md). Этот документ остаётся подробным контрактом ранее утверждённой архитектуры; старые ссылки на ТЗ_6v4/P0–P5 описывают исходное решение, а не текущий порядок разработки.

**Статус:** архитектура принята 22.11.2026, S10c2 уточнён и утверждён владельцем 25.11.2026. S07–S09 и часть S10 приняты как source/CI, единый физический исполнитель и owner-live ещё НЕ приняты. [RFC #1229](https://github.com/Tolian82/os-zapret2-restyle/issues/1229), [DEV-065/066/067](../PROJECT_PRINCIPLES.md), [ТЗ_6v4 §6.1–6.2](TZ_6v4.md), [план](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). Зафиксированная аппаратная версия пользователя: `_117` RUNNING после ручного Stop→Start; Lab `RESTORE_FAILED`, YouTube Found ещё не приняты. Source-only версия в текущем документальном PR `_121` **не** означает новый собранный `.pkg`.

## 1. Единственный источник истины по слоям

1. **Настройки пользователей:** существующий штатный XML Config OPNsense (`/conf/config.xml`, модель `OPNsense/Zapret`) с одним существующим writer; для pfSense в будущем — собственный XML adapter. Не сохранять второй редактируемый XML или JSON вместо основного Config, не добавлять второго Config writer.
2. **Данные:** сохраняемые отдельные текстовые домены YouTube/User/Found, IPSet Telegram/Discord/X/SIP/Custom, доменные/IP-исключения, шаблоны стратегий и параметры Voice, управляемые существующим реестром `registry.sh` и `storage.sh`/GUI list API. Не дублировать их содержимое в основной JSON. Нативные временные inbox/debug поколения — только transient Auto; Found/managed постоянны и меняются через P1/CAS/ACK.
3. **Чистый генератор:** читает XML и зарегистрированные данные, валидирует enum, типы, права/пути, effective enablement, WAN, Target Mode, порядок стратегий, Voice и пер-профильную native learning/first-match. Сборка не запускает `dvtws2`, не меняет Config, IPFW или running state.
4. **Результат:** ОДИН главный immutable, schema-versioned `manifest.json`, защищённый original FD9/seal и связанный exact generation, со ссылками на *проверенные* profile/strategy/Voice/Auto/IPFW/native source-map/`dvtws.args`; без доменов/IP/текстов стратегий inline. Разрешены несколько архивных sealed поколений для существующего защищённого rollback, но только ОДИН активный манифест владельца.
5. **Исполнитель:** ОДИН исходный `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` предоставляет **start/stop/restart/reload/status** под original FD9. `restart` — полная композиция единственных физических Stop→Start; `reload` — **отдельная live-операция только для подтверждённых изменяемых списков**, без Stop/Start; `status` — read-only. `reconfigure` — legacy фасад Apply planner, а не альтернативный процессный владелец. Исполнитель не парсит XML, не определяет Target Mode и не компилирует настройки. GUI/Apply/Lab/pkg/Install Version сохраняют текущий protected rollback.

## 2. Контракт главного файла — пример, не реализованная схема

```json
{
  "schema": 1,
  "generation": "0123456789abcdef0123456789abcdef",
  "target_mode": "auto",
  "service": {"enabled": true, "wan_ref": "general.waninterface", "divert_port": 989},
  "lists": {
    "youtube_manual": {"enabled": false, "ref": "hostlist.youtube.manual"},
    "youtube_found": {"enabled": true, "ref": "hostlist.youtube.found"},
    "youtube_effective": {"enabled": true, "ref": "hostlist.youtube"},
    "exclude_domains": {"enabled": true, "ref": "hostlist.exclude"},
    "exclude_ipset": {"enabled": false, "ref": "ipset.exclude"}
  },
  "profiles_ref": "profiles.json",
  "order_ref": "profile-order.json",
  "voice_ref": "voice.json",
  "learning_ref": "learning.json",
  "engine_args_ref": "dvtws.args",
  "native_source_map_ref": "auto-detect-source-map.json",
  "ipfw_plan_ref": "ipfw-plan.json"
}
```

Имена/поля предварительные, окончательно закрепляются после RED→GREEN сопоставления с действующим генератором. `ref` не произвольный файловый путь: только разрешённая запись текущего каталога/точный sealed generation. Запретить path traversal, симлинки, чужого владельца, произвольный пользовательский include, shell `source`/`eval`, неограниченные рекурсивные ссылки. Проверка SHA/размера immutable структурных артефактов при preflight и перед активацией. **Содержимое Found/managed — контролируемое mutable hot-reload**, нельзя навсегда pin по неизменяемому SHA в immutable манифесте, иначе сломаем обновление без рестарта; проверять состояние по существующему P1/CAS/ACK.

## 3. Правила effective enabled/disabled

| Узел | enabled | disabled / отказ |
|---|---|---|
| Global service | сохранено включение, валидны WAN/компоненты и манифест | `general.enabled=false` означает намеренно STOPPED; автоматическое обучение не запускает службу |
| YouTube/User manual | непустой нормализованный список используется хотя бы одним профилем | пустой ручной список OFF не отменяет уже известный Found/managed |
| YouTube/User Found | зарегистрированный managed target подключён и допускает дальнейший hot-write | пустой начальный Found **не означает** отключение обучающего источника |
| Exclude Domains | список валиден и содержит хотя бы одну запись | пустой → disabled, некорректный непустой → ошибка, а не silent OFF |
| Exclude IPSet | проверенный IP/CIDR список непустой | пустой → disabled, /0/full-family/ошибочный текст → отказ |
| Voice: Telegram/Discord/X/SIP/Custom | явно ON в сохранённых настройках **и** валидные параметры, непустой целевой IPSet | OFF сохраняет редактируемый черновик, не создаёт Voice capture; ON с пустым IPSet = ошибка |
| Auto native learning | `mode=auto` **и** есть подходящие рабочие HOSTLIST профили, подтверждённая per-profile карта | `all/list` не создают обучающие профили; auto без подходящих профилей обязан объяснить причину |

Не смешивать `requested` (явный пользовательский выбор) и `effective_enabled` (реальное включение в скомпилированном runtime). Для диагностики выдавать `reason`/`configured_count` через отдельный status/plan, не дублировать пользовательские данные в манифесте.

## 4. Target Mode и первые совпадения профилей

| mode | Основные профили | Обучение |
|---|---|---|
| `all` | работать по портам, если у профиля нет явного селектора; явные `<HOSTLIST:X>`/`<IPSET:X>` сохраняются | OFF |
| `list` | действующие зарегистрированные известные HOSTLIST/IPSET, явный селектор приоритетнее значения по умолчанию | OFF |
| `auto` | те же рабочие профили и после них подходящие native learning clone по утверждённому ТЗ_6v4 | ON, на том же единственном dvtws2 |

Рабочий порядок и точную карту **финальных нативных** номеров привязать к поколению и exact `dvtws.args`; нельзя угадывать номер по названию профиля. На каждом `--hostlist-auto` собственный native inbox, оригинальный P2/minute, Found→managed через существующие CAS/WAL/ACK без перезапуска. `<HOSTLIST:auto>` не включать неявно. IPSET-only/Voice и смешанные источники не создают неразрешённый доменный origin.

### 4.1. Утверждённая интеграция S08 с одним original generator (S10c2)

**Решение владельца 25.11.2026.** Сохранить единственную существующую производственную сборку `orchestrator_build_release()` и штатные `registry.sh`, `storage.sh`, `target_mode.sh`, `profile_policy.py`. Только оригинальный генератор создаёт `dvtws.args`, `release/managed`, Voice/IPFW и native source-map. S07/S08 — **чистая проверка** этих результатов, не альтернативный генератор и не новый физический исполнитель. Отдельные HOSTLIST и IPSET могут иметь индивидуальные TCP/UDP/L7/Lua стратегии; `--new`, first-match, порядок профилей и explicit-over-default сохраняются. Профиль с несколькими selectors разворачивается прежним нормализатором, а не новым алгоритмом S08.

**Путь данных и право владения (ровно один existing Apply):**

1. При уже удерживаемом исходном FD9 и существующих Config/list/P1 locks взять тот же авторизованный candidate snapshot: `traffic.input`, raw manual HOSTLIST, IPSET, Exclude и подтверждённые owned/Found или planned P1 after-image. Никаких повторных GUI/Config reads, незапечатанного нового источника истины и нового writer.
2. Тот же original orchestrator создаёт native release, применяет прежние HOSTLIST/IPSET normalize, compose_known, Voice и exclusions. Перед final seal S07/S08 через уже принятые pure `compile_target_profiles`, `compile_resources`, `inspect_original`, `snapshot` сравнивают ожидаемую семантику с **фактическими** `release/managed`, `dvtws.args`, Voice/IPFW, native profile order и original source-map. Для Auto сверяется настоящий source `traffic.input`/strategy SHA; для List/All source-map законно отсутствует, не выдумывать его.
3. Передавать данные проверяющему коду из уже имеющегося контекста сборки, **не** сохранять очищаемую оригинальным `targets_prepare_managed` папку `.input`, не восстанавливать raw данные из готовых файлов и не вызывать второго генератора. Подлинная identity/provenance и original seal/journal/root refs повторно проверяются перед физической мутацией: незапечатанный preview не является разрешением на Start/Reload/Restart или PREPARED→ACTIVATING.
4. Несовпадение source→generated bytes/refs/profiles, устаревший P1/Config snapshot, tamper и неизвестные IDs → fail closed **до** runtime/Config/IPFW mutation с сохранением прежнего владельца. Результат и причина в существующем bounded Apply diagnostic (`stage`, `code`, registered `resource_id`, operation/generation), без raw domains/IP/Lua/Config и без второго журнала. Если изменённое состояние уже затронуто, только original FD9 semantic rollback или честное UNCERTAIN.
5. Содержимое live Found/managed не фиксировать неизменяемым SHA в root JSON: его изменяет только старый P1/CAS/WAL/ACK. Не подменять после построения candidate подтверждённый planned Found snapshot произвольным новым чтением.

**Auto выключен:** `all` и `list` продолжают обычные отдельные HOSTLIST/IPSET стратегии и **не требуют** learning/source-map/inbox/debug/minute; manual и ранее подтверждённые owned списки не удаляются. `auto` создаёт только допущенные per-profile HOSTLIST learners при настоящей original attribution; IPSET-only, смешанные/неоднозначные и Voice не становятся доменными learners, `<HOSTLIST:auto>` не включается скрыто. Сохранить прежние List/All schema2 и Auto schema3 до отдельной нативной квалификации физического исполнения.

**Масштабируемость:** общий цикл проверки перечисляет разрешённые `(TYPE, NAME, STORAGE_KEY)` через **единственные** `registry.sh`/`storage.sh` и лимиты безопасности; `len(managed) == 7` из текущего S08b не должен стать новым product ABI или препятствием для регистрации дополнительных ресурсов. При интеграции исправить это фиксированное предположение на source-derived registered set **без создания второго списка ключей**. Существующие специальные YouTube/User Found и пять именованных Voice-сервисов не обобщаются автоматически. Добавление третьего–пятого GUI HOSTLIST, нового IPSET editor или разрешения Auto learning для него — отдельный scope с проверкой GUI/API/registry/ownership, **не** скрытая задача S10c2. Добавление пятой стратегии в рамках существующих лимитов не создаёт нового Apply/launcher/FD9 entrypoint.

**Приёмка S10c2:** эквивалентность настоящему original producer для `all|list|auto`, независимые HOSTLIST/IPSET/Voice/Exclude, несколько ordered `--new` стратегий, manual+owned Found, Auto OFF; отдельный synthetic extended-registry fixture для адаптера, с неизменным original registry production. Отказ до мутации при дрейфе источника/файла/ссылки; правдивая стадия ошибки и сохранение previous runtime. Проверять свой source→generated pipeline и native ownership, **не** установленное upstream автоматическое перечитывание списков движком. Сама эта спецификация не включает физический Start/Stop, смену journal phase, остановку трафика или выпуск .pkg.

## 5. Чистая установка, независимо наблюдаемые состояния

**Пятиосевая модель (не один общий флаг):** (a) сам **пакет плагина** установлен или отсутствует — при отсутствии пакета его скрипт/GUI физически недоступны, это зона `pkg`/интерфейса платформы; (b) **бинарный движок** Zapret2 установлен, исполняем и совместим либо `ENGINE_NOT_INSTALLED`/`ENGINE_INVALID`; (c) пользовательские настройки сохранены/инициализированы либо `CONFIG_UNINITIALIZED`/`CONFIG_INVALID`; (d) валидный активный sealed манифест есть либо `MANIFEST_UNAVAILABLE`/`MANIFEST_INVALID`/`MANIFEST_STALE`; (e) native runtime фактически STOPPED/RUNNING/INCOMPLETE/FOREIGN_OR_UNVERIFIED (не делать вывод только по PID).

**First install 0 → 1:** после чистой установки допустимы полностью отсутствующие модельные поля и `dvtws2`, несуществующие списки и runtime поколение. GUI и read-only статус работают; сервис остаётся STOPPED, никакого самостоятельного скачивания двигателя и первого старта. Только один раз, при *доказанном* отсутствии сохранённого пользовательского состояния, создавать уже согласованные YouTube Domains/базовую TCP/QUIC стратегию и безопасное default service OFF. При повторной установке **никогда** не переписывать сохранённые списки/Config. Ввод 'Установить версию' — явное штатное действие загрузки/установки upstream engine с проверкой и журналом, не замена plugin `.pkg`. Пустой конфиг нельзя считать командой остановки неизвестного процесса.

**Start contract:** чистая инсталляция без binary/config/manifest возвращает устойчивое название причины и не затрагивает чужой IPFW, PID, процессы и журналы. **Stop contract:** после частичного повреждения Config обязан выполнять безопасную остановку только ранее **подтверждённого** original owner из защищённого журнала/epoch; отсутствие editable JSON не повод оставлять известный собственный процесс без штатного Stop и не повод вслепую убивать PID. **Status contract:** read-only, не инициирует установку, сборку, Apply, Stop/Start или исправление, отображает состояние компонентов и причину неготовности.

### 5.1. WAN-only и лаборатория до первого обычного запуска — подтверждённый контракт

[ТЗ_6v5 `6.1](TZ_6v5.md), [LC-06/LC-11/LC-12](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md) и нативные [G05](../verification/G05_WAN_ONLY_NATIVE.md)/[G08](../verification/G08_PRESTART_LAB_NATIVE.md) являются обязательными регрессионными ограничениями. Важно **не** сделать новый immutable manifest условием сохранения WAN или запуска лаборатории.

- **Settings WAN-only Save:** при `Enabled=OFF`, отсутствии upstream binary и вообще отсутствующем ordinary release можно записать `general.waninterface` через existing `SharedConfigCommit::persist()`/original FD9 без compiler/engine/IPFW. Не уничтожать user-empty Strategy/list и не backfill defaults при reinstall; при существующем sealed Common owner оставлять полную исходную транзакционность.
- **Порядок Lab preflight:** saved WAN → real WAN resolution via existing `wan_preflight`/`config_resolve_interface()` (включая разрешённые assigned TUN/OPT) → engine installed/valid → Job authorization. Missing WAN = `wan-required` прежде `engine-not-installed`; invalid mapping = `wan-invalid`. Все эти ошибки предшествуют созданию Job/временных процессов и изменениям Config/IPFW.
- **Lab readiness независима от ordinary runtime:** после сохранения WAN и явной установки upstream Standard/Extended (и предусмотренная Circular) имеют доступ к собственной transient job-конфигурации даже без ordinary active `manifest.json`, `dvtws.args`, пользовательской Traffic Strategy или когда служба `STOPPED` и никогда не стартовала. Это **не** разрешение обычному `zapret_service.sh start` обходить проверку sealed manifest.
- **Restore:** Lab в таком сценарии обязана вернуть `STOPPED→STOPPED`, удалить только собственные temporary processes/IPFW и не менять Config/обычную стратегию. При сохранённом RUNNING owner остаётся прежнее `RUNNING→RUNNING` и все original FD9/epoch/rollback guards.

**G08 исторически PASS на native OPNsense (09.11.2026)** для двух настоящих HTTP Job с Stage40 TARGET_ACCESSIBLE и Stage90 STOPPED; после новой архитектуры это необходимо повторить на изменённом exact head, а не считать автоматически реализованным. Обязательная проверка [S06/S09/S15/S17](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), acceptance **V5-11**.

### 5.2. Новый reload diff и полная команда restart

[Нормативный контракт ТЗ_6v5 `5.1–5.4](TZ_6v5.md) уточняет эту исходную архитектуру. **Пять команд** `start/stop/restart/reload/status`, при этом restart=полный защищённый Stop→Start, reload **не перезапускает** engine/supervisor и не меняет IPFW/FD9 owner. Текущие ссылки root JSON/managed/Found остаются единственным активным runtime representation.

**Граница применимости:** если compiled effective structural fingerprint (native argv/profile order/source-map/Target Mode/Voice/WAN/IPFW/list refs) совпал, а поменялись лишь содержимые **уже подключённых** проверенных HOSTLIST/IPSet — кандидат reload-safe. **Автоматическое перечитывание изменённых файлов и принудительное перечитывание по SIGHUP при следующем пакете — аксиомы из [единственного канона `manual.en.md`](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md), не требующие и не допускающие повторной проверки.** Native evidence относится **только к действиям нашего плагина**: корректным refs/write/CAS, target PID/FD9, IPFW, выбору действия, ошибкам и GUI. Любая структурная перемена или mixed diff — full restart. При неполном состоянии — fail closed. Отсутствие изменений — no-op. Отдельный P1/CAS/ACK live Found hot-update сохраняется, а ordinary WAN-only Save и Prestart Lab не требуют manifest/Start/reload.

**Apply выполняет одну защищённую операцию**, plan→validate→commit→selected action→attest→Config/rollback, без второго writer. Для reload различать подтверждённые **плагином** запись/доставку сигнала (`RELOAD_REQUESTED`) и его собственное подтверждённое завершение операции (`APPLIED_VERIFIED`, с указанием объёма); не утверждать, что следующий пакет уже обработан. **Не требовать отдельного теста перечитывания списка двигателем:** оно описано каноном. Failed reload не вызывает тайный restart. Контракт CLI оставляет место ограниченным дополнительным параметрам (первоначально `status --json` и read-only `reload --check`) и закрывает arbitrary argv/path/PID/signal; ошибки native `dvtws2`/supervisor проходят в ограниченном typed receipt и существующий GUI RU/EN только в пределах lifecycle ошибок. Старые мёртвые Start/Stop/Restart translations адаптировать либо удалить.

### 5.3. Только ручной guarded force + локальная help без открытия runtime

В [ТЗ_6v5 §5.5–5.6](TZ_6v5.md), [DEV-070](../PROJECT_PRINCIPLES.md) одобрены `start|stop|restart --force`. Это **не** шестой lifecycle owner и **не** обход sealed manifest/FD9. Force разрешает **лишь** подтверждённую эскалацию остановки собственных зависших child/supervisor: sealed owner/epoch/PID+birth+exe+argv → normal graceful/TERM + bounded wait → повторная attestation → targeted KILL того же процесса → проверенный STOPPED/P2/IPFW. Вся цепочка сохраняет original durable operation и fail-closed на stale pidfile, foreign/reused/unverified PID, FD9 BUSY, PREPARED или orphan; `start --force` не убивает healthy RUNNING; `restart --force` не запускает из intentionally STOPPED. При ошибке KILL нет нового Start/ложного success, текущий receipt фиксирует typed причина/stage без второго writer.

`zapret_service.sh --help` и `zapret_service.sh <action> --help` выводят краткое usage/описания пяти команд, `--force`, `status --json` и `reload --check` **без захвата FD9 и IO**. `reload --force`, `status --force`, unknown/duplicate options — rc64 без side effects. GUI Apply/Auto/Boot/Lab/pkg не вправе автоматически использовать `--force`.

**Тесты V5-15/16 — только собственный lifecycle на disposable OPNsense**, не проверка движка Zapret2 из [upstream канона](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md). Отсутствие штатной возможности прекратить процесс не даёт права на `killall`, широкое удаление PID-файлов или чужих IPFW.

## 6. Ретрансляция ошибок движка, supervisor и Apply

Один нормализованный диагностический конверт, schema-versioned: `timestamp`, `stage` (`install|config|manifest|wan|ipfw|engine-start|engine-stop|voice|auto-minute|apply|lab-restore`), `code`, `operation_id`, `generation`, `exit_status` (или `null`), `runtime_state`, `message`, `stderr_excerpt` (строго ограниченный размер, очищенный от секретов и полных пользовательских списков), `log_ref` (только доверенный файл). Пример кодов: `ENGINE_NOT_INSTALLED`, `CONFIG_UNINITIALIZED`, `MANIFEST_INVALID`, `WAN_UNAVAILABLE`, `IPFW_ATTACH_FAILED`, `ENGINE_EXIT_EARLY`, `LAB_RESTORE_FAILED`. Выделять `native tool stderr` и причинную стадию, не сводить всё к одной фразе «Запуск не удался».

Ошибки `dvtws2`, supervisor, setup, configd/renderer, IPFW, original P2 и Lab принимать в ограниченную долговечную диагностическую запись с существующими защищёнными правилами владения/ротации; показывать нормализованный код в GUI и `status --json` (проектное расширение, не действующий CLI). Не публиковать полный `config.xml`, сырые домены/IP из буферов, токены, весь `debug.log` и полные args с потенциально чувствительными данными. Никаких логов от status-запроса, способных случайно запустить исполнение. Terminal status должен отражать факт физического RUNNING/STOPPED/INCOMPLETE, а не успокоительный текст об успешном Apply.

## 7. Применение, откат и миграция без второго писателя

1. На подготовке GUI/Config однозначно читается штатным platform adapter. Компилятор строит candidate manifest и отдельные списки/Voice/стратегии/IPFW/args; проверяется тип/владелец/полная связь ссылок и exact profile map.
2. При `Apply` единственный прежний FD9 и durable `shared_apply_operation` защищают подготовку, sealed original owner, конфигурацию, выбор NO_CHANGE/RELOAD/RESTART/START/STOP/SAVE_ONLY и rollback; нельзя добавлять второй журнал/Config writer.
3. На `Boot` `zapret_service.sh` проверяет sealed активный манифест и только затем исполняет подготовленные аргументы. При stale/foreign/failure — отказ, никакого silent fallback на неаутентифицированный старый runtime.
4. На live Auto `Found/managed` содержимое меняется по оригинальной CAS/FD9/P1/ACK, `dvtws2` перечитывает файл без остановки или переподписания структурного JSON.
5. Вводить ПОЭТАПНО: (A) сравнение старых параметров и новых в pure dryrun для `all/list/auto`, Voice ON/OFF, exclusions; (B) read-only `status --json` плюс clean-install/no-engine тест; (C) staged manifest в текущем sealed release без активации; (D) один authoritative runtime consumer в `zapret_service.sh` без самостоятельной GUI/Apply/installer логики старта; (E) реальный disposable OPNsense Lab running/stopped/timeout/error/rollback, pkg-update; (F) только затем test `.pkg` на owner, отдельные проверки YouTube/User native per-profile Found.

**ПЕРВЫЙ обязательный гейт:** отсутствие бинарника, конфига, манифеста и корректная диагностика должны PASS до внедрения автоматического запуска. Сразу проверять несовпадающие/пропавшие/изменённые файлы, повреждённые JSON/refs, двойной owner, foreign PID/IPFW и отсутствие write side effects.

## 8. Платформенная переносимость XML vs JSON

**Обязательный выбор:** native OPNsense/pfSense GUI-настройки остаются XML, общее ядро Zapret2 получает скомпилированный JSON. При переносе на pfSense заменяется XML-модель/адаптер сохранения и пути platform services, *не* контракты JSON, реестра/Target Mode, engine аргументов, проверок State/Voice/Auto. Избегать параллельных JSON и XML runtime манифестов, которые расходятся. XML-парсинг даёт штатная платформа, а JSON-манифест остаётся внутренним бинарно проверенным artifact release. Не обещать перенос без проверки пакетов, FreeBSD ABI, IPFW и служб на целевой pfSense версии.

**Результат:** пользователь меняет списки, режим, приоритет и Voice без редактирования Start/Stop; изменение физического старта/остановки требует правки одного `zapret_service.sh`; чистый маршрут без движка безопасен; причины неисправности диагностируются по устойчивому коду и настоящему исходному stderr, без смешения во множестве не связанных скриптов.
