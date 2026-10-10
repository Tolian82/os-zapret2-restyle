# «Передача голоса» — задание на реализацию и переход от telegram_voice

### v0.5.1_36 — восстановление байтов с исходными правами перед будущим live swap

После ранее внедрённого `native-voice-restore-stage` штатный исполнитель FD9 теперь строит вторую, отдельно опубликованную приватную копию `restore-install-image`. Файлы в ней имеют исходные права из неизменяемого snapshot (Config, файлы, вложенные каталоги, корень `runtime-v2`), а внешний каталог остаётся `0700`. Исходные байты и права дважды проверяются независимым наблюдателем. Действие по-прежнему **не переключает** живые `/conf/config.xml` и `runtime-v2`, IPFW, dvtws2 или supervisor; для этого нужен единый транзакционный владелец Config и lifecycle, UID/GID-политика и доказанное восстановление после перезагрузки. Snapshot schema 1 без исходного режима корневого runtime нельзя превращать в install image.


### v0.5.1_30 — настоящий backup предыдущего runtime перед Voice cutover

Штатная операция `zapret_service.sh native-voice-checkpoint` исполняется под общим FreeBSD lockf FD9, проверяет, что старый Zapret2 полностью работающий (один dvtws2, supervisor и правила), что legacy Telegram PoC отключён, текущий native OFF-кандидат с WAN и портом привязан к действующему `dvtws.args`, а текущий `/conf/config.xml`, IPFW и реальные argv не расходятся. Только тогда `voice_cutover_checkpoint.py` запускает существующий `capture_previous` и атомарно сохраняет полный Config, дерево `runtime-v2`, sealed manifests в `/var/db/zapret2/voice-cutover/previous` с fsync. После публикации snapshot исходники, процесс и kernel IPFW проверяются ещё раз. Повторная перезапись существующего snapshot запрещена. Создание чистого snapshot **не** включает native Voice, **не** создаёт pending whole-journal и **не** блокирует старый сервис. Снята возможность опасного раннего IPFW seed: захват владения правилами теперь требует durable PREPARED whole-cutover schema2+ и сверенного старого Config/runtime snapshot; до этого действие не меняет IPFW ledger. Это реальная производственная часть безопасного восстановления после будущего переключения, но не завершённый switch или автоматический reboot recovery. Новый GUI Voice ON не разрешён.

### v0.5.1_31 — подготовка восстановления реальных байтов Config/runtime под общим FD9

В производственный `zapret_service.sh` добавлено отдельное действие `native-voice-restore-stage`, выполняемое только под тем же `lockf` FD9. Внутри на FreeBSD запускается `voice_cutover_restore_prepare.py prepare`, который требует общий `VoiceCutoverJournal` schema 2+ в фазе `mutating` и существующее ранее доказанное владение IPFW. Прошлый полный снимок `/var/db/zapret2/voice-cutover/previous` проверяется относительно SHA поля `previous.config` и `previous.runtime`; прежние Config и дерево dvtws2 **материализуются** через `prepare_restore_stage()` во вновь созданный `/var/db/zapret2/voice-cutover/restore-staged` с защитой от ссылок/подмен, атомарным rename и fsync. Без валидного журнала и ownership операция отказывается; повторно перезаписывать уже подготовленный каталог нельзя. Все текущие процессы, `ipfw`, `/conf/config.xml` и активный runtime остаются нетронутыми. Остающаяся отдельная задача — под тем же общим транзакционным владельцем действительно вернуть восстановленные байты в штатные пути, запустить один прежний dvtws2 и supervisor, восстановить IPFW, удостоверить пять ресурсов и закрыть журналы. До этого ни Voice ON, ни безусловный automatic recovery не разрешены.

### v0.5.1_29 — IPFW нельзя коммитить раньше общего runtime

Исправлен критический порядок _28: функция реального IPFW Apply создаёт `VoiceOwnershipStore.begin/mark_mutating`, меняет `ipfw` и **сохраняет прежний committed ownership и stage-таблицы** до решения общего `VoiceCutoverJournal`. Только при фазе `committed` отдельная операция `native-voice-ipfw-commit`, выполняемая через штатный `zapret_service.sh` с FD9, делает `ownership.commit`, удаляет временные/отставшие таблицы и завершает намерение IPFW. При ошибке старта supervisor/переключения до общего коммита операция `native-voice-ipfw-rollback` допускается исключительно при фазе `mutating` общего журнала, после остановки candidate dvtws2 (PID-файл удалён), и восстанавливает строго доказанные старые правила и содержимое таблиц. При чужих/неизвестных правилах откат блокируется, журнал остаётся. Общий журнал НЕ закрывается автоматически ни IPFW commit, ни rollback: это ответственность будущей транзакции Config, дерева релиза, движка и supervisor. До её реализации GUI Voice ON заблокирован. _28 не имеет полностью зелёного CI (Strategy Lab job-contract), что не следует скрывать.

### v0.5.1_28 — производственный исполнитель IPFW с журналом и жизненным циклом

`voice_ipfw_runtime.py` выполняется только на FreeBSD под root и проверяет тот же FD9 lockf, что используется для всех штатных операций Zapret2. `zapret_service.sh` теперь знает действия `native-voice-ipfw-seed` и `native-voice-ipfw-activate`. Первое реально принимает во владение уже установленный OFF-обычный набор правил, если отсутствуют Telegram PoC marker и обе старые таблицы, running dvtws2 совпадает с проверенным родным ELF/argv, текущий XML совпадает с pinned SHA и IPFW-правила ровно соответствуют манифесту. Результат постоянный в `/var/db/zapret2/voice-ipfw`, но ядро не меняется. Второе имеет реальные вызовы ядра через FreeBSDIPFWAdapter с staged адресными таблицами и безопасным rollback в пределах IPFW; без ожидающего общего cutover-журнала schema2+ в фазе `mutating` и точных SHA манифеста/argv его нельзя вызвать успешно. После применения проверяются экземпляр движка и журнал владения. Действия подключены к реальному service dispatcher и его lockf, но не к GUI: необходимое транзакционное переключение всей системы (Config, release, dvtws2, supervisor, IPFW, reboot) ещё предстоит закончить. Это не работающий Telegram call и не основание устанавливать ON.

### v0.5.1_26 — готовый артефакт передачи одного движка и IPFW

После получения `voice-native-candidate/traffic.conf` штатный orchestrator запускает `generator_build_args_mapped` ВТОРОЙ раз с тем же divert, Lua, BLOB и global exclude: новый `voice-native-candidate/dvtws.args` содержит единый Voice+Strategies-порядок, но не заменяет активный `runtime-v2/dvtws.args`. Далее CLI `voice_handoff_preflight.py` сверяет XML `/conf/config.xml`, исходные ordinary-профили и tcp/udp артефакты, содержимое engine argv, пути таблиц и хеши IPSET и создаёт внутри приватного кандидата `desired-ipfw.json` строго в формате `VoiceOwnershipStore.canonical_manifest()`, плюс `handoff-proof.json` с хешем манифеста. В IPFW-манифесте отдельные правила Voice идут до обычных tcp/udp, у Voice обязателен `to table(zapret2_voice_<service>)` и выбранный WAN. Ни IPFW, ни процесс dvtws2 при генерации не меняются.

Сейчас кандидат имеет `activation_authorized=false`, а ON по-прежнему блокируется service preflight; это защищает уже работающий старый PoC и обычные «Стратегии». Следующий практический шаг — применить готовый манифест в настоящем owner-controlled cutover с возвратом старого движка, таблиц, supervisor и Config после отказа и с обработкой reboot. Только затем включать ON в GUI.

### v0.5.1_25 — единый Voice-кандидат собирается в настоящем orchestrator

В `orchestrator_build_release()` непосредственно после `telegram_voice_build_effective_traffic` вызывается `orchestrator_stage_native_voice`, использующий установленный `voice_release_stage.py` и фиксированные входы: `/conf/config.xml`, `release/managed`, `release/traffic-user.conf`, фактический `WAN_IF` из `config_resolve_interface`, `DIVERT_PORT` и выделенный диапазон IPFW. Генерируется каталог `release/voice-native-candidate/` с приватными файлами `voice.conf`, `traffic.conf` (единый dvtws2: Voice STUN → ordinary), `profile-plan.json`, `capture-plan.json` и `metadata.json` с `activation_authorized=false`. Информация о целевых IPv4 должна точно соответствовать обычным управляемым IPSET одного и того же релиза. Несовпадения приводят к остановке сборки до подмены live runtime.

Этот шаг подключает готовый Native-компилятор к **реальному производственному пути** старта/переконфигурации, а не к очередной отключённой модели. Но он **не** выбирает `voice-native-candidate/traffic.conf` как действующий runtime и **не** включает Voice ON: старый Telegram PoC продолжает создавать обычный `traffic.conf` и свои scoped IPFW-правила до транзакционной миграции. ON блокируется также в сервисном preflight. После этого этапа оставшийся технический разрыв — безопасная активация с IPFW/rollback/boot и разрешение нового GUI Apply. Подтверждение генерации не является подтверждением голосового соединения.

### v0.5.1_23 — реальная кнопка «Применить» для выключенных Voice-профилей

Реализован отдельный `POST /api/zapret/voice/apply`: при всех пяти `enabled=0` сохраняет изменения существующей модели OPNsense и вызывает реальную штатную `configdRun('zapret reconfigure', false, 180)`. До записи контроллер сверяет snapshot, проверяет права и дважды спрашивает Strategy Lab guard. Даже если черновик уже сохранён, операция делает reconfigure для обновления общих IPSET в обычной службе; пустое изменение не создаёт дополнительную ревизию Config. `applied=true` возможен только при фактическом ответе `OK` от reconfigure. При ошибке — `saved=true`, `applied=false`, `requires_review=true`; нельзя считать прежний runtime автоматически восстановленным. ON выбранный или прежний категорически отвергается: нет ни копирования STUN в dvtws2, ни установки нового IPFW. GUI содержит две независимые кнопки «Сохранить черновик» (без runtime) и «Применить выключенные профили» (общая служба), плюс отдельный installer релизов. Запрос на независимый Voice WAN пока не поддерживается.

Это функционально действующий Apply только для совместимой **OFF-конфигурации**. Полностью согласованный Voice Apply с ON, одной общей транзакцией Config/runtime/IPFW, резервным восстановлением и миграцией legacy PoC всё ещё не завершён; не публиковать продукт как готовый UDP/Telegram voice.


### v0.5.1_21: реальное сохранение выключенных профилей (2026-10-10)

Первый настоящий шаг от только диагностической страницы к работающей конфигурации: кнопка **«Сохранить черновик»** вызывает `POST /api/zapret/voice/saveDraft`. Контроллер сравнивает единственный загруженный snapshot со всеми актуальными полями «Стратегий», Voice и IPSET, использует тот же `VoiceApplyCandidate::prepare`, затем сохраняет отредактированные данные через **штатную модель OPNsense** `setNodes` / `serializeToConfig` / `Config::save`. Проверка прав `throwReadOnly` и модельная валидация обязательны. Успешный ответ содержит `result=saved`, `applied=false`, число изменённых полей и новый snapshot; повторное идентичное сохранение не создаёт новой ревизии. Ошибка/устаревшая вкладка не стирает форму. Все пять сервисов обязаны остаться OFF как в исходном состоянии, так и в поданном кандидате.

**Это НЕ Voice Apply:** новая кнопка не запускает configd, dvtws2, IPFW, миграцию PoC или перезагрузку; сохранение ON запретить, пока старый `config_voice_staged_only_guard` не заменён квалифицированным новым runtime. Текущий общий IPSET Telegram и остальные общие целевые списки сохраняются как входные настройки и **могут повлиять на следующий обычный запуск Zapret2** — это прямо объясняется в GUI. В окончательном продукте штатная «Применить» заменит временный draft-путь после реального одно-движкового транзакционного подключения. Нынешняя цель следующего кода: реальный Apply и безопасная генерация WAN/IPFW/engine, а не новые mock-only проверки.

### Нативная проверка общего lockf FD9 (v0.5.1_20, test-only)

**v0.5.1_20 — native lifecycle FD9 interoperability qualification (2026-10-10):** Added a non-activating isolated regression `scripts/test-voice-native-lifecycle-lock-interop.py` that opens ONLY private temporary lock inodes. Linux/FreeBSD exercise independent-descriptor flock contention. On actual FreeBSD 15, the test invokes the same `/usr/bin/lockf -s -t ... 9` inherited-FD contract used by `zapret_service.sh`: Python flock must block it, release must permit it, lockf's kernel ownership must survive helper exit while shell FD9 remains open, and an unrelated inode must not be blocked. Both Voice candidate CI and FreeBSD 15 package CI execute the test. This tests kernel cooperation, NOT retention of Config::save() flock or a working Config+configd transactional handoff. No Voice Apply, GUI mutation, live firewall change or PoC migration. PLUGIN_REVISION=20 (DEV-032); exact-HEAD CI/FreeBSD acceptance pending. v0.5.1_19 full CI initially failed an intermittent Strategy Lab async lifecycle mock (unexpected error rather than completed); focused job rerun was requested, with no weakening of the safety assertion.

Только общность BSD `flock` / FreeBSD `lockf` для **одного inode** подтверждается в изолированном тесте. В реальном Apply пока нет непрерывного транзакционного владельца Config+lifecycle: нельзя удерживать PHP flock на lifecycle lock во время обычного `configdRun('zapret reconfigure')`, так как сам shell-dispatch пытается захватить тот же lockf через независимый процесс. `Config::save()` снимает Config-flock, поэтому даже два последовательных положительных опроса блокировки не делают handoff атомарным. Не включать GUI Voice Apply до явного общего сериализатора/владельца, одной фиксированной очередности замков, durable rollback и boot replay.

### Регрессия Strategy Lab: корректное моделирование двух уровней Voice gate

- Сценарий `test-strategy-lab-lifecycle-cases.sh` намеренно создаёт **искусственный** `SERVICE_BACKEND` с пустыми mocked shell-модулями. После введения обязательного `voice_cutover_guard.py` тест завершался ошибкой 69 из-за отсутствующего Python-файла. В этом тестовом backend теперь создаётся отдельный mock read-only guard с управляемым `MOCK_VOICE_INTENT_PENDING`. **Production `voice_cutover_guard.py` и его непрерывные проверки не подменяются**; их поведение с реальными двумя файлами журналов и правами тестирует `test-voice-cutover-boot-guard.py`.
- Проверяются **два разных отказа**. Если pending установлен ДО запуска работника, родительский `service_with_lifecycle_lock()` возвращает 69 и работник вообще не вызывается. Если pending обнаруживается в `strategy_lab_internal_dispatch()` у уже владеющего fd9 работника, внутренний `strategy-lab-stop` тоже возвращает 69 и не останавливает старый runtime. Только при чистом guard тестовая старая служба проходит штатный stop. Эти сценарии нельзя объединять: код выхода работника не равен коду ранней защиты родителя.
- Ранее устранённая Linux/FreeBSD-разница расположения `python3.13` остаётся отдельным исправлением. Тестовая заглушка guard — не production bypass и не автоматическое восстановление Voice. Полная CI и FreeBSD 15 должны быть проверены на **последнем SHA** до публикации.


### Ревизия fail-closed gate и совместимость Strategy Lab (2026-10-09)

- Переходный `voice_cutover_guard.py` уже защищает реальные start/stop/reconfigure, однако начальная реализация `zapret_service.sh` жёстко проверяла только `/usr/local/bin/python3.13`. Это корректно на **FreeBSD production**, но ломало интеграционный Strategy Lab на Linux runner до выполнения теста: `ERROR: native Voice journal inspection is unavailable` и код 69. Исправление сохраняет абсолютный production путь и жёсткий отказ, если guard недоступен. **Только** при выполнении исходников из неустановленного `BACKEND_DIR` (репозиторий/тестовый стенд), когда штатного FreeBSD-пути нет, допускается обнаружить доступный `python3.13` через PATH для выполнения того же guard. Никакого флага отключения проверки на рабочем OPNsense не добавлено.
- Регрессионный `test-voice-cutover-boot-guard.py` теперь дополнительно действительно вызывает выделенную shell-функцию с тестовым backend и проверяет пропуск чистой проверки (0), передачу отказа (69), production-абсолютный путь и отсутствие обхода.
- Выявлена дополнительная ветка: внутренний `strategy_lab_internal_dispatch` наследует проверенный lockf fd 9 и вызывает `start_service`/`stop_service` **без** `service_with_lifecycle_lock`. Поэтому в `strategy-lab-start` и `strategy-lab-stop` перед изменениями также встроен read-only `preflight_voice_cutover_journals`; read-only `strategy-lab-status` и `strategy-lab-evidence` доступны для диагностики. Регрессионный тест проверяет обе ветки и строгий порядок `guard → mutator`.
- Это по-прежнему защита рабочего маршрутизатора от незавершённой будущей транзакции, а не включение native Voice Apply. При наличии damaged/pending journal эксплуатационное восстановление требует подтверждения владельца и полного состояния; нельзя чистить intent вручную наугад.


- Дополнительно `voice_cutover_backup.bound_resource_fingerprints(snapshot, previous)` выполняет read-only проверку целого snapshot и вычисляет согласованные SHA256 прежнего `config.xml` (байты) и дерева runtime (канонический manifest с файлами, правами, размерами). Если в полном `VoiceCutoverJournal.previous` эти две записи отличаются от фактических копий, переход блокируется. Три остальные компонента журнала (`engine`, `firewall`, `supervisor`) пока должны проверяться отдельными production adapters. `test-voice-cutover-backup.py` связывает реальное файловое хранилище с `VoiceCutoverJournal.new_record` и проверяет отказ при подмене runtime.


### Долговечное сохранение предыдущего Config + runtime (новый изолированный контракт, 2026-10-09)

- Новый `backend/voice_cutover_backup.py` сохраняет **реальные байты прежнего `config.xml` и дерева `runtime-v2`**, в отличие от `voice_cutover_journal.py`, который хранит только SHA256 решений и пяти ресурсов. Это отдельный pure filesystem staging API `capture_previous(config, runtime, output)` и read-only `inspect_previous(output)`, **без CLI / configd entrypoint / автоматического восстановления**.
- Только write-once private output под каталогом владельца 0700; файлы содержимого 0600, исходные права записываются в JSON manifest для будущего restore adapter. Прямое копирование обычных файлов с O_NOFOLLOW, отказ от source symlink/special/hardlink, лимиты на размер и число файлов. Каждая запись fsync, атомарная публикация каталога через rename в том же родительском каталоге, fsync родителя. Манифест запечатан `manifest.sha256`, содержит размер/тип/моду/хеш каждого файла и структуру каталогов.
- После копирования код **повторно читает исходный XML и все файлы runtime**: изменения в середине snapshot приводят к ошибке и удалению только неполной временной копии, без публикации кандидата и без изменения живой службы. `inspect_previous` проверяет seal, файл config, каждый файл runtime, права и отсутствие отсутствующих или посторонних объектов.
- `scripts/test-voice-cutover-backup.py` проверяет успешный backup+readback, приватные права, readonly integrity, подмену/порчу/дополнительные файлы, symlink, чужие права и гонку изменения config или runtime. Linux/FreeBSD 15 CI, проверка наличия Python-модуля в pkg.
- **Ограничение:** runtime-дерево с symlink сегодня блокируется до определения безопасной политики линков для реально установленного пакета. В резервной копии пока **нет восстановимых данных IPFW/process/supervisor** — их отдельно должен сохранить и сверить production adapter, связав snapshot с durable whole-runtime journal под Config+lifecycle lock. Это не готовый, не установленный и не проверенный на живой OPNsense restore; auto-replay отсутствует.


### Усиление атомарного отката при ошибке второго rename (2026-10-09)

- `backend/atomic.sh::atomic_restore_tree` теперь при указанной проверенной резервной копии **не удаляет активный релиз заранее**. Он переносит активный runtime во временный `DEST.rollback-old.PID`, пытается переименовать backup в DEST и, если второй `mv` отказал, переносит временно отложенный релиз назад. Только после успешного восстановления backup временный старый кандидат удаляется. Если временный путь уже существует (возможный остаток неоконченного переключения), функция не меняет каталоги и требует отдельной диагностики.
- При `BACKUP=\"\"` сохраняется исторический сценарий первой установки: удаляется неудачный кандидат при отсутствии более старого релиза. При неудаче возвращения временного релиза каталог остаётся на диске с явной ошибкой, без автоматического удаления данных. Это дополнительная защита от ошибки операции, **но не гарантия power-loss atomicity**: между rename возможен разрыв видимого пути; полное восстановление после power-loss должно опираться на durable whole-runtime journal.
- `scripts/test-voice-atomic-rollback-preflight.sh` применяет настоящий `atomic.sh` к тестовым каталогам и проверяет missing/symlink backup, отказ второго `mv` после отставления активного релиза, конфликтующий `rollback-old` и успешный restore. Тест выполняется в Linux + FreeBSD 15 CI.


### Безопасный базовый откат runtime дерева (2026-10-09)

- При аудите реального `backend/atomic.sh::atomic_restore_tree` найден дефект: при указанном `BACKUP_DIR`, который отсутствует, старый порядок **сначала удалял активный runtime**, и только потом проверял backup. Исправление в PR #328 проверяет абсолютный путь, существование настоящего каталога и отсутствие symlink **до** любого удаления current runtime. При отсутствующей/небезопасной копии функция теперь отказывает, оставляя действующую версию нетронутой. Правильная копия восстанавливается штатно, включая каталог предыдущего `dvtws2` релиза.
- `scripts/test-voice-atomic-rollback-preflight.sh` вызывает действующий `atomic.sh` на приватном mock runtime и проверяет missing/symlink backup (current tree остаётся целым), затем успешный restore из корректной копии. CI исполняет это на Linux и FreeBSD 15. Это **общий rollback safety fix**, используемый существующими Strategies; он сам не делает Voice Apply транзакционным и не гарантирует восстановление после потери питания.


### Fail-closed реального service lifecycle при незавершённом Voice-журнале (2026-10-09)

- `backend/voice_cutover_guard.py` — настоящий **read-only boot/lifecycle gate**, вызываемый `zapret_service.sh::service_with_lifecycle_lock()` после успешного `/usr/bin/lockf` и **до** `service_dispatch`. Он ничего не создаёт, не меняет и не восстанавливает, не запускает IPFW/dvtws2/configd. Без аргументов проверяет два фиксированных root-private каталога: `/var/db/zapret2/voice-cutover` и `/var/db/zapret2/voice-ipfw`. Отсутствие обоих или пустые валидные каталоги пропускает обычный runtime.
- Любой незавершённый whole-runtime intent (`prepared`/`mutating`/`committed`), per-IPFW pending intent, **уже принятое native IPFW ownership** или непроверенные/повреждённые ledger/symlink/права доступа **блокируют legacy Start/Stop/Reconfigure/PoC Enable/Disable и вызываемые через service wrapper runtime-failure/Strategy Lab mutations**. Невозможно разрешать старому движку перезаписывать IPFW, уже принадлежащий native Voice, даже после завершения intent. Код отказа `69` отличается от кода занятости `lockf` `75`.
- При чистом состоянии существующие Start/Stop/Reconfigure продолжают работать. В необычном случае уже незавершённого журнала даже глобальный Stop намеренно блокируется, чтобы не стереть свидетельства частичного применения; статус и `voice_inspect` остаются read-only доступными. Самостоятельная очистка журналов не предусмотрена: нужна проверенная процедура восстановления. После будущего внедрения production native Voice adapter legacy-only dispatcher должен быть заменён на явную маршрутизацию по владельцу, не простое выключение этой проверки.
- `scripts/test-voice-cutover-boot-guard.py` покрывает clean/empty, все стадии целого журнала, отдельный IPFW pending, ownership без pending, corruption/symlink/mode и порядок `lockf → gate → dispatch`. Исполняется Linux/FreeBSD CI; проверка contents пакета фиксирует наличие guard. Это **только защита lifecycle**, а не реализация resume/replay после перезагрузки.


### Read-only интеграция общего журнала в диагностику страницы

- В отличие от mock-only активатора, `voice_live_inspect.py` **уже вызывается штатным configd read-only `zapret voice_inspect`**. Теперь перед IPFW-проверкой он проверяет `/var/db/zapret2/voice-cutover` (если такой приватный каталог существует). Долговечный `prepared`/`mutating`/`committed` intent немедленно даёт `state=interrupted`, `can_activate=false` и фиксированное `condition`; IPFW-проверки не могут скрыть незавершённое переключение, даже если собственный `voice-ipfw` каталог отсутствует. Некорректные права, symlink или повреждение журнала дают fail-closed `inspection-error`. Отсутствующий whole-runtime journal сохраняет прежнюю IPFW диагностику.
- GUI отображает статус и короткую RU/EN подсказку о фазе: проверка прежнего состояния, прерванная замена компонентов или проверка cleanup после фиксации. Это только текст и чтение; статус **не запускает восстановление**, не принимает решение пользователя, не активирует новый профайл и не разблокирует Apply.
- `scripts/test-voice-live-inspect.py` с реальным файловым `VoiceCutoverJournal` и mock IPFW проверяет приоритет всех трёх фаз и отсутствие kernel-чтений после обнаружения pending-intent. `scripts/test-voice-gui-contract.py` закрепляет RU/EN представление состояния. Для live эксплуатации всё ещё обязателен будущий единый lockf/recovery и owner approval acceptance.


### Whole-system Voice cutover: ещё отключённый протокол транзакции (2026-10-09)

- `backend/voice_cutover_coordinator.py` — **исключительно adapter-injected mock contract**, без CLI и без использования из `zapret_service.sh`/GUI. Никакая реальная мутация невозможна по умолчанию: `simulate_cutover(..., test_only_mutations=False)` отказывает до вызова адаптера. Для теста требуется явный `test_only_mutations=True` и оба замка (Config и lifecycle) от тестового адаптера. Нельзя переносить эту проверку в runtime простым включением флага.
- Порядок фиксации для будущего native Apply: проверенные старые Config/tree/one-engine/supervisor/IPFW + отсутствие старого PoC + свежий candidate → fsync **prepared** intent → fsync **mutating** intent → замена staging runtime → остановка только старого dvtws2 → старт единственного нового → owned IPFW → supervisor → проверка нового → сохранение нового Config → повторная проверка → fsync committed intent → проверенный post-commit cleanup → удаление intent. Это именно проектный mock-contract, а не утверждение, что указанная последовательность уже внедрена в плагин.
- Ошибка до committed: мок-координатор в обратном порядке восстанавливает старый Config/tree/IPFW/engine/supervisor; удаляет intent **только после независимой проверки всего старого состояния**. Ошибка в любой части отката сохраняет durable intent для manual review. Ошибка uncertain commit и post-commit cleanup **не вызывает самовольного rollback**, потому что решение могло уже пережить рестарт. Отдельные unit tests делают fault injection в каждую фазу, включая неполную запись журнала, сбой живого firewall и boot review.
- `backend/voice_cutover_journal.py` — **файловый журнал всего runtime отдельно от Voice IPFW ownership ledger**. Только приватный каталог 0700 / файл 0600 владельца, `O_NOFOLLOW`, no hardlink, bounded JSON, SHA256 integrity, write+fsync+rename+fsync directory. Записи: `prepared`, `mutating`, `committed`, отпечатки пяти прежних ресурсов (config, runtime, engine, firewall, supervisor) и трёх артефактов нового кандидата. Прерванные операции `inspect()` только классифицирует, **не исправляет автоматически**. Реальный жизненный цикл должен согласованно держать этот журнал и существующий `voice_firewall_ledger.py` под единым `lockf`.
- `scripts/test-voice-cutover-coordinator.py` подмешивает фактический offline staged XML/Voice/ordinary/IPFW proof и моделирует процесс/конфигурацию, затем проверяет полный happy path, rollback на каждой фазе, отказ в подтверждении состояния и сохранение intent при неоднозначности. `scripts/test-voice-cutover-journal.py` использует настоящий файловый fsync-журнал и проверяет restart/permissions/corruption/stale stages. Эти тесты входят в Linux/FreeBSD CI и пакет содержит оба новых Python-компонента.
- **Открытые блокеры production:** Adapter для реального OPNsense Config commit с блокировками, замена legacy PoC без конкурирующих маркеров, native FreeBSD dvtws2/installed Lua preflight, общий IPFW ownership cutover, durable restart reconciliation между двумя журналами, автоматическая загрузка persistent ON после перезагрузки и owner-live медиатест. Пока этого нет, новый `Apply` остаётся disabled, PR Draft.


### Offline preflight перед реальным единым переключением (черновик, 2026-10-09)

- `backend/voice_handoff_preflight.py` — **чистая безмутационная проверка** согласования опубликованного только в staging кандидата: `metadata.json`, `profile-plan.json`, `capture-plan.json`, `voice.conf`, `traffic.conf`, реальные аргументы `dvtws.args`, список портов обычной стратегии. Она восстанавливает IPFW scope из профилей, проверяет хеш каждого Voice-профиля, управляемых IPSET, исходного XML (наличие pinned SHA), объединённого и обычного трафика, ровно один divert socket, один непрерывный merged traffic и отсутствие старого `telegram-voice-poc`.
- Для обычных TCP/UDP IPFW-портов добавлена независимая нормализация, сопоставляемая CI со штатным `backend/ports.sh::ports_extract_file` именно по исходной *ordinary* стратегии, **не** по merged Voice+ordinary: Voice-порты захватываются своими узко адресованными правилами. Подмена портов в caller-плане блокируется.
- `scripts/test-voice-handoff-preflight.py` и `scripts/test-voice-generator-interop.py` запускаются в Linux и FreeBSD 15 CI с реальным `generator.sh` и `ports.sh`, но без `dvtws2`, IPFW или записи `config.xml`. Результат preflight всегда `activation_authorized=false`. Отдельно ещё нужны trusted ownership/legacy migration, lock-held config commit, реальный installed Lua/dvtws2, отказоустойчивый rollback и reboot replay.
- Исправлен FreeBSD CI тест `test-voice-targets-integration.py`: временная тестовая `python3` ссылка на установленный `python3.13` только внутри приватного PATH запуска подпроцесса. Это **не** изменение системного Python маршрутизатора; отрицательный тест обязан видеть ошибку CIDR host bits, а не отсутствие интерпретатора.


- `scripts/test-voice-targets-integration.py` дополнительно прогоняет **все пять** списков IPv4/CIDR через реальный `targets_prepare_managed()` и тот же Python Voice release compiler: Telegram IPSET остаётся общим со «Стратегиями», порядок/дедупликация должны совпасть, включённые профили получают правильный IPFW table, CIDR с битами хоста отвергается. Проверка входит в Linux + FreeBSD CI и не обращается к живому IPFW/dvtws2.

### Перехват ошибок ДО IPFW и проверка связи со штатным generator.sh (Draft, 2026-10-09)

- Два отдельных ранних safety gate защищают текущую службу от ещё не реализованной Voice ON. `zapret_service.sh::preflight_native_voice_before_firewall()` выполняется непосредственно после актуализации шаблона и **до** `firewall_prepare` в обоих `start_service` и `reconfigure_service`. `orchestrator_native_start()` повторно проверяет Voice ON **до** проверки `runtime_is_complete` и **до** `orchestrator_cleanup_runtime`, иначе неподдерживаемый ON мог бы остановить старый процесс/правила или ошибочно вернуть «ready». Глобальный Zapret OFF допускает штатный stop даже при сохранённой Voice ON. В reconfigure сборка кандидата предшествует остановке действующего runtime.
- `scripts/test-voice-staged-runtime-guard.sh` (в CI) проверяет OFF/ON/некорректные флаги, порядок операций у service entry, отсутствие cleanup после отказа START и разрешение global OFF без live IPFW.
- `scripts/test-voice-generator-interop.py` проверяет целостность цепочки `config.xml → voice_release_stage.py → voice_traffic_merge.py → реальный backend/generator.sh → dvtws.args` вместе с `voice_firewall_transaction.prepare_desired()` для IPv4-таблиц и отдельных номеров Voice/ordinary TCP/UDP. Проверяются один `--port`/один набор аргументов движка, порядок Voice перед Strategies, сохранение A2/обычного трафика, OFF byte-for-byte и отклонение старого PoC или конкурирующего ordinary STUN. **Это offline staging**, не запуск `dvtws2` и не подтверждение работы UDP на WAN.
- `voice_release_stage.py` теперь сохраняет в staging metadata SHA256 исходного config.xml и повторно хеширует **в конце** источники config.xml, IPSET и ordinary traffic. Конфигурация, изменённая параллельным GUI/другим оператором при сборке, не принимается. Источник XML/ordinary и managed targets не должен быть symlink, есть лимит размера входных данных. Staging-файлы и родительский каталог синхронизируются на диск. Регрессии `scripts/test-voice-release-stage.py` инъецируют изменения XML/managed/ordinary в процессе сборки, проверяют отказ и отсутствие публикации неконсистентного кандидата.
- Финальный Apply **обязан заново проверять** источник и модель под Config/lifecycle lock, проверять установленный FreeBSD IPFW/dvtws2 и откатывать саму службу; hash/preflight/staging не делают весь процесс атомарным автоматически. Снятие staged-only ограничений, legacy cutover, boot restore и owner-live media acceptance остаются открытыми.


### План Voice Apply и защита от тихой активации (черновой этап)

- `Api/VoiceApplyCandidate.php` готовит **в памяти** единую следующую конфигурацию после проверки SHA256 baseline, полного whitelist и `VoiceCandidateValidator`. Только IPSET включённых сервисов нормализуются с дедупликацией и подсчётом адресов; параметры и списки выключенных сервисов остаются редактируемыми черновиками. Обычные `general`, `strategy`, `strategylab` и прочие `hostlist` поля не изменяются. Возвращаются изменившиеся поля и список включённых служб. `VoiceController.validateAction` повторно использует этот же план, но отдаёт только syntax-only результат, **не сохраняет** модель.
- Перед подготовкой проверяется выбранный WAN: при отсутствии Strategies WAN или независимом Voice WAN кандидат блокируется с ошибкой у поля. Раздельный WAN остаётся **функциональным требованием**, не имитируется до проверки признака входящего divert/dvtws2. Включённый service с независимым WAN нельзя активировать через один общий движок.
- Пока отсутствует подтверждённый cutover, штатная shell-конфигурация из GUI переносит только пять Boolean Voice ON/OFF в `VOICE_*_REQUESTED` через Jinja guarded fields. `config_voice_staged_only_guard()` вызывается в `orchestrator_build_release` до сборки профилей. Любой явный saved Voice ON или невалидный флаг завершает **создание legacy-релиза с ошибкой**, а не молча проигнорирует сохранённую галочку и не объявит Voice включённым. Пять OFF оставляют обычные Strategies/существующий PoC-путь без изменений. Это временная fail-closed защита, не реализация native ON.
- В фазе реализации нового runtime этот guard должен исчезнуть **только одновременно** с проверенным однодеменным переходом на общий профиль/IPv4-таблицы, сохранением в `config.xml` под lock, аварийным journal/rollback и boot. До этого активный режим страницы не объявляется готовым.
- PHP-тест `scripts/test-voice-apply-candidate.php` проверяет нормализацию и OFF-drafts, сохранение unrelated settings, stale-tabs, IP/port collisions и WAN; shell-тест `scripts/test-voice-staged-runtime-guard.sh` проверяет отсутствие silent activation через старый PoC.


### Атомарная загрузка GUI и обнаружение устаревших вкладок (Draft, 2026-10-09)

- Для страницы «Передача голоса» `VoiceController::loadAction()` теперь отдаёт **поля native модели и SHA256 baseline из одного чтения под Config lock**, а `mapDataToFormUI` сохраняет baseline как hidden `zapret.sync.snapshot`. Кнопка «Проверить» становится активной только после успешной загрузки совпадающих полей и baseline. Это устраняет гонку двух отдельных запросов за конфигурацией и её контрольной версией.
- `VoiceSettingsSnapshot.php` детерминированно отслеживает все общие группы `general`, `strategy`, `voice`, `hostlist` (без unrelated Laboratory). Изменение Telegram IPSET, обычного Traffic Strategy, WAN, других Voice параметров и любого общего IPSET отклоняет устаревшую форму при Validate. Сравнение выполняется **под Config lock**; на Apply такую же проверку потребуется повторить непосредственно перед транзакционной записью и активацией, а не считать прошлый Validate разрешением на запись.
- `VoiceController::validateAction()` сверяет snapshot с текущей моделью, удаляет sync-метаданные, проверяет whitelist `VoiceSettingsPayload::overlay()`, затем `VoiceCandidateValidator::check()`. Нет `save()`, `reconfigure`, IPFW, запусков `dvtws2` и смены PoC. Сообщения о конфликте переведены RU/EN.
- PHP-интеграционный тест `scripts/test-voice-api-concurrency.php` использует заглушки модели/Config, проверяет load, digest, stale ordinary и Telegram, injection/отсутствующий baseline, unlock и отсутствие записи; отдельный GUI-contract проверяет endpoint/hidden token. Это ещё **не owner-live GUI acceptance**.


### Native Voice GUI — проверка до сохранения (v0.5.1_1, Draft)

- Добавлена кнопка **«Проверить» / Validate** на штатной странице. Она посылает только несохранённые поля формы на `/api/zapret/voice/validate` в `Api/VoiceController.php`. `VoiceCandidateValidator.php` выполняет чистую проверку IPv4/CIDR, допустимых STUN/UDP параметров и пересечений адрес+порт между включёнными сервисами; OFF может сохранять незавершённые черновики.
- Проверка **не читает и не меняет** активные правила IPFW, не вызывает `configctl reconfigure`, не изменяет `config.xml`, не запускает и не останавливает `dvtws2`. Ошибки отображаются через штатный `handleFormValidation`, на русской странице переводятся в RU, в английской сохраняются EN. **Применить / Apply по-прежнему disabled.**
- Принятие формы означает только проверку синтаксиса GUI и отсутствия очевидных пересечений, **не** доказательство работоспособности установленной версии dvtws2, Lua, IPFW, boot recovery, Telegram MEDIA_PASS или готовности к активации.
- Согласованность валидаторов проверяется CI по отдельным PHP регрессиям и Python/PHP differential parity; OPNsense GUI живьём ещё не проверен. Перед включением Apply предстоят штатный общий lifecycle lock, повторная авторитетная Python-валидация полного кандидата, транзакционный runtime/FreeBSD IPFW, migration и rollback.


### Следующий разработческий контракт — миграция временного Telegram Voice

- `backend/voice_migration_plan.py` читает `config.xml`, старый `/var/run` marker и старый active `telegram-voice-poc.state` только для построения плана. У сохранённых новых галочек приоритет над временным marker после **успешного** перехода; отсутствие marker после перезагрузки само по себе не означает явного выбора OFF.
- Различаются clean install (пять OFF), отсутствие сохранённого выбора при старом временном ON (нужно первое явное решение пользователя), сохранившийся live PoC без marker (неоднозначно, блокировать), persist ON/OFF при live PoC (только атомарная миграция с rollback), уже сохранённые новые предпочтения без старого PoC.
- Код **ничего не переносит и не удаляет**; его результаты требуется связать с общим lockf/reconfigure/restore и устранением старого prepend/IPFW. Никакого автоматического импорта transient ON в новую постоянную галочку.
- Добавлены CI FreeBSD + Python тесты миграции. Новая read-only строка GUI IPFW явно относится к новому подсистемному набору правил, а не к живому старому PoC.

### Продолжение Draft PR #328 — native IPFW и GUI-диагностика

- `voice_ipfw_adapter.py`: строго ограниченный FreeBSD-IPFW адаптер (путь `/sbin/ipfw`, argv без shell, bounded list/table parsing, интерфейс и rule number allowlist). По умолчанию только чтение; разрешение мутаций предусмотрено исключительно под доверенным lifecycle-lock с предварительным журналом. **Ещё не подключён к production.**
- `voice_live_inspect.py` + native configd `voice_inspect` + `Api/VoiceController.php`: проверяемый status (uninitialized/ready/interrupted/foreign/stage), вывод на Voice-странице **RU и EN**. API не предоставляет запись/Apply и не запускает IPFW-мутации. Отсутствующий журнал не считается успешной активацией.
- В IPFW transaction/ledger/GUI-inspection равные IPv4-таблицы сравниваются как множества уникальных адресов: `ipfw table list` может менять порядок по отношению к полям GUI. Повторные адреса по-прежнему запрещены.
- Зафиксирован консервативный конфликт ordinary STUN и новых Voice STUN-профилей. Non-STUN обычные профили, включая A2, при сборке продолжают сохраняться.
- Более широкая, ограниченная валидация fake TTL/badsum/ipfrag/out-range основана на документированных native параметрах, но **проверка Installed dvtws2/Lua на OPNsense и wire acceptance ещё обязательна**.
- FreeBSD-15 CI теперь исполняет регрессию IPFW адаптера и инспектора, проверяет в пакете все новые Python-модули. Статус точного последнего head всегда проверяется отдельно перед merge.


**Статус:** УТВЕРЖДЁННОЕ НАПРАВЛЕНИЕ И ДИЗАЙН · РЕАЛИЗАЦИЯ НАЧАТА В ЧЕРНОВИКЕ PR #328 · НЕ ГОТОВО К ПРИМЕНЕНИЮ/РЕЛИЗУ

**Решения:** 2026-10-08. **Документ обновлён:** 2026-10-09. Проверенная база исходников: `fc43abc6ea38a9b7aa097c4fbecfa6b276514526`, пакет `0.5.0_3`.

**Разработка v0.5.1_1 (черновик, 2026-10-09):** [PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328) создан из проверенного `main` `3f9951c928ac2521c3551c8311d58ed755947007`. В ветке добавлены базовая модель Voice и пять общих IPSET-полей, новая native форма/маршрут/меню, двуязычный текст и справка, общая строка службы, а также статическая проверка формы в CI. `VERSION=0.5.1`, `PLUGIN_REVISION=1` существуют **только в черновой ветке**; доступные опубликованные пакеты остаются `0.5.0`. **Кнопка Voice Apply намеренно отключена.** Новые IPSET уже добавлены в реестр/нормализатор, а старый `telegram_voice` marker/prepend/IPFW всё ещё работает в исходном пути запуска, миграция и сохраняемый boot lifecycle отсутствуют. До слияния необходимо реализовать и проверить контракт из разделов 5–10, выполнить документационную сверку и тесты. Не устанавливать WIP package как готовый Voice-плагин.

**Назначение:** основной технический документ для следующей темы; читать после обязательных правил из [START_HERE](../START_HERE.md). Этот документ сохраняет решения владельца, описывает существующий механизм, задаёт границы реализации, миграции и приёмки. Он не устанавливает новую конфигурацию на OPNsense и не объявляет найденным обход DPI.

### Реализация в Draft PR #328 — текущий инженерный статус

- Уже добавлены штатная форма/меню, RU/EN-справка, модель пяти сервисов и IPSET-поля; Telegram продолжает использовать одно `hostlist.telegramips`.
- `backend/registry.sh`, `storage.sh`, `targets.sh`, `orchestrator.sh` и `zapret.conf` расширены на четыре новые именованные IPSET. Они нормализуются и доступны для явных ordinary placeholders, без изменения политики неявного Target Mode.
- `backend/voice_profile_compiler.py` — **пока самостоятельный, не подключённый к Apply/runtime** компилятор кандидата. Принимает фиксированные пять сервисов, IPv4/CIDR, `--filter-udp=*` или числовые диапазоны, `--filter-l7=stun`, `--payload=stun`, необязательное проверенное прежним PoC действие `--lua-desync=fake:blob=0xHEX:repeats=N`. Добавляет управляемые name/IPv4/IPSET, проверяет пересечения IP+портов, запрещает `--new`, произвольные файлы/процесс/системные опции, shell-токены. Разработческий allowlist дополнен документированными параметрами **fake-only**: `ip_ttl=1..255`, `badsum`, `ipfrag`, `ipfrag_pos_udp` с выравниванием по 8, `ipfrag_disorder`, а также ограниченным `--out-range` для UDP. Он отвергает неподтверждённые комбинации (например `badsum+ipfrag`), shell и фрагментацию оригинала `send/drop`. **Расширенная native-семантика пока проверена только парсером**, не установленным на маршрутизаторе `dvtws2` и фактическими WAN-пакетами. Эти возможности нельзя объявить working до engine/live qualifications. Это **временный строгий allowlist**, не отмена полного утверждённого назначения страницы.
- `backend/voice_capture_plan.py` получает строго валидированный JSON-план, резервирует последовательные номера в границах plugin-owned диапазона (с двумя слотами для обычных TCP/UDP правил), создаёт только декларативные правила `udp from any to table(zapret2_voice_<service>) [port] out not diverted not sockarg xmit WAN`. При all-port поле UDP-порта опускается, но адресная таблица **обязательна**. Проверяются WAN, managed paths, IPv4/CIDR, очерёдность, непересечение, collision с диапазоном правил. Скрипт **не выполняет** команд `ipfw` и пока не устанавливает таблицы: kernel transaction, проверка чужих правил и rollback остаются отдельной задачей.
- `backend/voice_release_stage.py` строит **неактивный candidate bundle** из сохранённой модели, строгого STUN-компилятора и декларативного IPFW-плана. Он сверяет каждый enabled IPSET с `managed/ipset-*.txt` нормализованного **того же кандидата**, проверяет физический интерфейс после логического WAN и формирует приватный каталог (`0700`, файлы `0600`). Кандидат содержит явные `mode=staged-only`, `activation_authorized=false`, хеши списков и профилей; несоответствие до окончания сборки не меняет прежний каталог. Физический `xmit` не берётся слепо из логического `WAN`. Это **пока не подключено к штатной активации, IPFW/boot и Apply**.
- `backend/voice_traffic_merge.py` создаёт единый текст профилей: Telegram → Discord → X → SIP → Custom, затем `--new` и **неизменённые байты обычных пользовательских профилей** (включая non-STUN A2). Когда все Voice OFF, обычный текст сохраняется побайтно. Коллизия с `--name=telegram-voice-poc`/зарезервированным `--name=voice-*` и пустые границы отклоняются. Его объединённый файл `traffic.conf` можно включить в staged bundle по желанию; подключение к нормальному `generator_build_args_mapped` и отключение прежнего hard-coded prepend — **ещё не сделано**.
- `backend/voice_firewall_activation.py` сейчас связывает проверенный старый state, durable intent, mock IPFW replacement, commit ownership, проверяемый cleanup и завершение intent; отдельные тесты проходят ON/change/OFF и fault-injection/restart. Это **только adapter-injected mock-контракт**, а не включённый FreeBSD IPFW/GUI lifecycle: runtime adapter, общий lockf, возврат dvtws2 и crash recovery после частичного состояния ещё не реализованы.
- `backend/voice_firewall_ledger.py` — **ещё не подключённый к production** долговечный журнал с `ownership.json` и `intent.json` в приватном каталоге владельца (подходящий будущий путь: `/var/db/zapret2/voice-ipfw`, не `/var/run`). Формат нормализует IPFW rules/tables и проверяет границы/синтаксис; запись временного файла, `fsync`, `rename`, `fsync` каталога; файлы `0600`, каталог `0700`, проверка собственника/ссылок и SHA256 целостности. **SHA256 не аутентифицирует злоумышленника**, доверие зависит от владельца каталога и штатного lifecycle lock. Перед любым изменением должно быть сохранено `prepared` → `mutating` intent, за которым следует проверенный commit владения; намерение удаляется только после проверки полного желаемого live-состояния без staging-таблиц. `inspect()` после перерыва работает **только на чтение**, различает `previous-intact`, `desired-intact` и `manual-review` (частичный или неизвестный live state). Не реализовано автоматическое восстановление при неоднозначности; старый PoC не импортируется и не принимается за подтверждённое владение. В CI есть отказные тесты, но пока отсутствуют FreeBSD adapter, интеграция с реальным `lockf`, crash-restart workflow и boot-acceptance.
- В `voice_firewall_transaction.py` подготовлены `plan_postcommit_cleanup()` и `cleanup_committed()`: после подтверждённого commit они проверяют live правила и точные значения собственных старых/staging таблиц; удаляют только соответствующие таблицы, допускают повторный вызов после частичного cleanup и отказываются удалять чужое. Исправлена защита от возможного удаления чужого правила при коллизии внутри `add_rule`: откатываются лишь достоверно добавленные правила. **Проверки проводятся на mock IPFW**, а реальная атомарность/паузы при переключении нескольких IPFW правил на FreeBSD пока не доказаны.
- `backend/voice_firewall_transaction.py` — **пока только adapter-injected core**, без подключения к IPFW/production. Строго проверяет ранее утверждённый trusted ownership manifest, сравнивает реальные правила plugin-owned диапазона и собственные таблицы до любых изменений, отказывается заменять неизвестное/изменённое правило. Подготавливает отдельные `*_stage` таблицы, переключает IPv4 наборы, заменяет только прежние известные номера, а при ошибке на каждом этапе откатывает предыдущие правила/таблицы (или выдаёт явную ошибку неполного отката). Unit tests используют in-memory IPFW с failure injection. **Нельзя вызывать в production до реализации runtime-адаптера, долговечного ownership manifest, журналирования/восстановления после crash, post-commit cleanup, миграции старого PoC и проверки на FreeBSD**. Успешный тест алгоритма не равен IPFW live acceptance.
- `VoiceSettingsPayload.php` — пока чистый whitelist-overlay будущей Voice Apply с ограничением полей Voice, пятью общими IPSET и проверкой freshness общего Telegram IPSET через существующий `StrategySettingsPayload`. **Это подготовка, а не работающий API Apply.** PHP-регрессии проверяют границы двух форм.
- `backend/voice_model_export.py` читает только постоянный XML-узел `OPNsense/Zapret` из `config.xml`, преобразует пять ON/OFF галочек, raw аргументы, общий Voice WAN и совместно используемые IPSET в JSON-кандидат с правами `0600`; если legacy config ещё без секции Voice, все пять профилей по умолчанию OFF. Нет доступа к конфигурациям Squid/sing-box, нет изменения XML, нет старого `/var/run` marker и нет создания второго dvtws2. Цепочка XML → профиль → декларативный IPFW план покрыта отдельными тестами, **но сама пока не подключена к транзакционному Apply/boot**.
- Существующий `SettingsController.php` теперь накладывает только whitelist полей формы «Стратегии» через `StrategySettingsPayload.php` (и проверяется в PHP CI): он не трогает сохранённую секцию `voice`, остальные IPSET или Laboratory. Существующая страница «Стратегии» теперь дополнительно передаёт снимок исходного Telegram IPSET, сервер сравнивает его при Apply под конфигурационной блокировкой и отклоняет старую вкладку до сохранения. **Вторую сторону этого контракта** (будущая Voice Apply) ещё необходимо реализовать; новая кнопка остаётся заблокированной.

- Пока нет доказанного разграничения контекста одного divert/dvtws2 на двух WAN, компилятор отвергает отличный от Strategies WAN до применения; интерфейс не выбирает маршрут.
- Нет нового Apply, подключения компилятора к общему запуску, расширенного IPFW, миграции с PoC или восстановления после reboot. **Старая реализация продолжает работать в исходном установленном пакете; параллельно новая не активируется**. Кнопка Apply остаётся заблокированной.
- Добавлены регрессионные контракты `scripts/test-voice-shared-ipsets.sh` и `scripts/test-voice-profile-compiler.py`; CI на последнем коммите ещё должен подтвердить их вместе с полным проектным набором.

Это разделение временных этапов разработки не означает согласие выпустить ограниченный/пустой Voice функционал как готовый `v0.5.1`: необходимо закончить разделы 5–10 и пройти owner-live. Старый PoC будет удалён **только в момент** завершённой атомарной миграции, не в параллельном пути.

## 1. Цель и изменение прежнего плана

Создать в **os-zapret2-restyle** отдельную штатную страницу **«Передача голоса»** между **«Стратегии»** и **«Лаборатория»**. Она управляет постоянными настройками перехвата UDP и STUN-профилями **Telegram / Discord / X (Twitter) / SIP (VoIP) / Custom** в существующей службе Zapret2. Это управление конфигурацией, не встроенная лаборатория и не второй голосовой демон.

Владелец утвердил отдельную страницу и изменяемые параметры **сейчас**. Поэтому прежнее требование «сначала MEDIA_PASS/CALL_PASS, затем только одна галочка в существующих Settings; отдельную страницу делать лишь при дополнительных доказательствах» заменено этим заданием. Успешные голосовые тесты по-прежнему необходимы для объявления конкретной стратегии рабочей; они больше не блокируют создание страницы, управляемых профилей и постоянного состояния.

Практическая исследовательская цель сохраняется: воспроизводимое соединение реального Telegram-звонка через OPNsense `192.168.1.2` и тот же WAN/провайдера, затем проверка речи. Рабочая TCP/TLS-связка Squid/sing-box/PF → parent `185.203.117.88:33128` остаётся отдельной лабораторной инфраструктурой. Новая страница не меняет прокси, маршруты, NAT или TCP. Адреса стенда не становятся настройками по умолчанию продукта.

## 2. Окончательные решения владельца

| Вопрос | Утверждённое поведение |
|---|---|
| Название и место | «Передача голоса», после «Стратегии», до «Лаборатория» |
| Дизайн | Тот же native OPNsense дизайн и примерно та же компоновка, что у «Стратегии» |
| WAN | Отдельный выбор в самом верху страницы; это интерфейс исходящего перехвата |
| LAN / входящие интерфейсы | Не добавлять ни список, ни переключатель ограничения по входу |
| Локальный UDP OPNsense | Всегда участвует при совпадении WAN, назначения и других условий; отдельной галочки нет |
| Сохранение после загрузки | Всегда восстанавливать сохранённый выбор через обычный lifecycle; отдельной галочки нет |
| Сервисы | Пять строк/групп: Telegram, Discord, X (Twitter), SIP (VoIP), Custom. Twitter и X — один сервис |
| Включение | Своя галочка у каждого сервиса, не текстовый `enabled=Yes/No` |
| Параметры | Свое многострочное поле у каждого сервиса |
| IPSET | Отдельное многострочное поле IPv4/CIDR для каждого сервиса по образцу «Стратегии» |
| Выключенный сервис | Не создаёт свой профиль/перехват, но сохраняет введённые параметры и адреса |
| Non-STUN | Настраивается в «Стратегии»; второго поля non-STUN на новой странице нет |
| Служба | Один общий dvtws2, штатные запуск/остановка/переконфигурация Zapret2 |
| Применение | Явная кнопка «Применить» внизу, проверка до изменения действующего runtime |

Отменены прежние предложения добавить «Ограничивать по входящим интерфейсам», «Входящие интерфейсы», «Обрабатывать локальный UDP OPNsense» и «Восстанавливать после загрузки». Не возвращать их в макет или модель как скрытые необязательные переключатели.

## 3. Внешний вид и компоновка

Эталон — действующая страница «Стратегии» в исходниках [general.xml](../../src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml), [general.volt](../../src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt) и предоставленный владельцем снимок её тёмной темы. Снимок содержит частную конфигурацию: публично его не публиковать. Реализация должна использовать общие native компоненты, а не копировать только цвета изображения.

Последовательность сверху вниз:

| Секция | Содержимое |
|---|---|
| **Основные настройки** | Одна строка выбора WAN |
| **Параметры передачи голоса** | Telegram: галочка и textarea; затем такие же пары Discord, X (Twitter), SIP (VoIP), Custom |
| **IP-адреса назначения** | Пять подписанных textarea: IPSET Telegram, Discord, X (Twitter), SIP (VoIP), Custom |
| **Служба Zapret2** | Общий статус/версия и штатные общие сервисные элементы по образцу «Стратегии»; не отдельная Voice-служба |
| Нижняя строка | Оранжевая штатная кнопка **«Применить»** |

Сохранять подписи слева и поля справа, ширину полей, отступы, чередование строк, сворачиваемые заголовки со стрелкой, значки справки и пояснения под полями. Пять сервисов — части одной формы; не отдельные вкладки, карточки или dashboard. Использовать `layout_partials/base_form` и имеющиеся OPNsense компоненты. Наследовать выбранную светлую/тёмную тему; не фиксировать тёмные цвета. Интерфейс следует языку OPNsense: RU/EN, без своего выбора языка. На узком экране поля не выходят из рамки формы, порядок сохраняется.

Сервисная строка показывает состояние **всей службы**. Рядом с сервисами допустимы короткие фактические сообщения о применении/ошибке, но галочка не должна изображать доказанный работающий звонок. «Включено», «настроено», «перехватывает» и «звонок работает» — разные утверждения.

## 4. Как работает сейчас

Подробная текущая эксплуатационная справка находится в [telegram_voice: конфигурация и восстановление](TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). На проверенной базе:

- `configctl zapret telegram_voice_enable`, `telegram_voice_disable`, `telegram_voice_status` — существующие действия **без аргументов**. Универсальной команды `voice_enable` пока нет.
- `/var/run/zapret2-telegram-voice-poc.enabled` — временный запрос ON. После измеренного reboot 7 октября он исчез, helper стал OFF; обычные GUI-стратегии сохранились. Последующее ручное enable восстановило native ON/table14/rule, но не доказало автоматическое восстановление или успешный звонок.
- `backend/telegram_voice.sh` добавляет перед GUI-профилями фиксированный IPv4 Telegram STUN-профиль: все UDP-порты, managed Telegram IPSET, `filter-l7=stun`, `payload=stun`, `fake` с **16 нулевыми байтами** и `repeats=2`. Явного короткого TTL, badsum и фрагментации в нём нет.
- Дополнительное правило IPFW перехватывает `udp from any to table(zapret2_tgvoice) out not diverted not sockarg xmit <WAN>` и отправляет его в тот же divert/dvtws2. Оно не выбирает LAN. Текущие `vtnet1`, `989`, `19000` и 14 префиксов — измеренные параметры стенда.
- GUI Telegram IPSET и helper уже используют **одно** поле `OPNsense.Zapret.hostlist.telegramips`, из него строятся managed файл и IPFW-таблица. Отдельные PF aliases и снимок sing-box не синхронизируются с ним автоматически.
- Обычный GUI-перехват извлекает числовые UDP-порты из `traffic-user.conf` и направлен `to any`; `*` там сейчас отвергается. Поэтому вставить STUN-команду в «Стратегии» недостаточно для эквивалентного адресно-ограниченного перехвата всех UDP-портов.
- Оба источника профилей работают в **одном** dvtws2. IPFW выбирает захват, затем движок — первый подходящий профиль. Более ранний STUN-helper может перекрыть поздний GUI STUN-профиль. `payload` внутри выбранного профиля не заменяет правильные фильтры выбора профиля.
- Сейчас один общий WAN берётся из `general.waninterface` / `WAN_IF`. Отдельного WAN для Voice пока нет.

Текущая Telegram non-STUN A2 остаётся в «Стратегии»: IPv4, Telegram IPSET, UDP `596–599`, `filter-l7=unknown`, `payload=unknown`, `fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2`. Это не универсальный профиль для всех остальных голосовых пакетов. В A1/A2 helper был ON и не менялся; оба опыта не получили ответов рефлектора. Таблица результатов и протокол — в [кампании](TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md).

## 5. Целевая модель и формат полей

Ниже — **технический контракт реализации**, выведенный из утверждённого интерфейса. Имена новых XML/API-полей ещё не существуют; их фиксируют вместе с кодом. Не выдавать обсуждавшиеся `voice.stun`, `ip_ttl=` или `blob=16` за уже поддерживаемый конфигурационный API.

Постоянная модель содержит: общий выбранный Voice WAN и по каждому из пяти сервисов `enabled`, текст параметров, ссылку на его единственный IPSET. `enabled` задаётся галочкой. Данные живут в штатной конфигурации OPNsense, а не в `/tmp`, `/var/run` или вручную отредактированном generated-файле.

### Многострочное поле параметров

Использовать **native dvtws2 аргументы профиля**, согласованно со «Стратегиями», с проверяемым ограниченным контекстом одного Voice/STUN-профиля. Не вводить параллельный произвольный INI-язык без необходимости. В этом поле:

- задаются UDP-порты (`--filter-udp=*` либо числа/диапазоны), STUN-фильтр/нагрузка, диапазон обработки и упорядоченные native Lua-действия;
- область первой реализации — `--filter-l7=stun` и `--payload=stun`; другие протоколы остаются в «Стратегии». Обязательные строки должны быть видны в начальном шаблоне и проверяться, а не скрыто подменяться;
- IPv4, имя/идентичность профиля и IPSET добавляет генератор из формы. Вводить второе назначение, `--new`, TCP-фильтр, параметры процесса/divert/daemon или произвольный путь конфигурации здесь нельзя;
- отсутствующее fake-действие означает пропуск подходящих оригиналов без fake, при сохранении выбранного перехвата. Это полезный контроль; выключение всей галочки удаляет и профиль, и его дополнительный перехват;
- native синтаксис, порядок действий и ошибки должны сохраняться. Не выполнять введённое как shell и не превращать текст в неограниченные аргументы запуска процесса;
- неверный синтаксис/неподдерживаемая возможность даёт ошибку конкретного сервиса/строки до изменения конфигурации. Поле остаётся доступным для исправления.

**Пример переноса нынешнего STUN-helper, не рекомендуемая рабочая стратегия:**

```text
--filter-udp=*
--filter-l7=stun
--payload=stun
--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2
```

Это сохраняет известную семантику; оно не исправляет non-STUN Hello и не объявляется обходом DPI. Telegram получает такой шаблон для прозрачного перехода. Другие сервисы первоначально OFF, без вымышленных рабочих IP-диапазонов/стратегий. Включение требует непустого корректного IPSET и валидного профиля. На чистой установке автоматического включения голосовых сервисов нет. Установка пакета не должна сама начинать эксперимент.

### Параметры, ради которых делаем редактируемое поле

| Параметр | Что меняет / как представляется | Ограничение |
|---|---|---|
| UDP-порты | Native `--filter-udp=`; `*` или ограниченный список | IPFW и профиль должны выражать одинаковую область; `*` разрешён только вместе с destination IPSET |
| Протокол/нагрузка | `--filter-l7=stun`, `--payload=stun` | Первоначальная страница — STUN; название сервиса само протокол не распознаёт |
| Область пакетов | Native `--out-range=...` либо отсутствие ограничения | Проверить native единицы/синтаксис установленного движка, не навязывать TCP `-d10` голосу |
| Fake включён/нет | Наличие или отсутствие Lua `fake` | Управляет действием; галочка сервиса управляет также захватом |
| Fake-содержимое и длина | `blob=0x...`, native built-in/подготовленный доступный BLOB | `zero16` — 16 байт UDP payload, не длина IP-пакета; `blob=16` не поддерживаемая запись размера |
| Число fake | `repeats=N` внутри соответствующего действия | Больше повторов не означает лучше; исходное значение helper — 2 |
| TTL fake | `ip_ttl=N` внутри fake или отсутствие override | Ограничивать fake, не оригинал. TTL уменьшается на L3-хопах; подходящее значение требует наблюдений |
| Авто-TTL | Только native механизм, если подтверждён установленными Lua/engine | Не определяет DPI магически; отсутствие обратного TTL требует явно проверенной семантики fallback. Не выдумывать новый синтаксис |
| Checksum fake | Обычная native checksum или `badsum` | Проверять фактический WAN после NAT; checksum оригиналов должна оставаться правильной |
| Фрагментация fake | Native `ipfrag`, `ipfrag_pos_udp`, `ipfrag_disorder` у fake | Отдельно от оригинала; выравнивание позиции по 8, пригодность длины/порядка и WAN-проверка |
| Фрагментация оригинала | Согласованные `send:ipfrag:...` и `drop` | Продвинутый режим: запретить случайное удаление оригинала без замены; не менять PFIL автоматически |

Первые полезные регулируемые величины для отдельного **STUN**-опыта — область перехвата, fake payload/размер, repeats, fake TTL, checksum и диапазон обработки. Фрагментация остаётся отдельной исследовательской гипотезой, не способом по умолчанию. Для текущего Telegram **non-STUN** эти эксперименты по-прежнему задаются в «Стратегии». Каждая смена параметра требует имени опыта, полного before/after и результата, как определено [контрактом кампании](TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#how-any-helper-change-is-recorded).

Авто-TTL, BLOB-файлы и сложные действия допускаются только после проверки доступных ресурсов и native валидации; UI не обещает отсутствующие возможности. До кода зафиксировать поддерживаемый allowlist и негативные примеры в тестах. Не добавлять самодельные `filter-l7=sip/rtp/telegram_voice` или фильтр «размер пакета» без существующей реализации. Discord IP Discovery, DTLS, Reflector Hello, SIP signaling и RTP не становятся STUN от подписи сервиса; их отдельная обработка принадлежит «Стратегиям».

### Один IPSET на сервис

Одна строка — один IPv4 или CIDR; действующие нормализация/дедупликация/валидация как у «Стратегии». IPv6 и DNS-списки в этой первой реализации не добавляются: существующий целевой контракт IPv4 сохраняется. Пустой список у включённого сервиса — ошибка, **никогда не `to any`**. Широкий явный список — выбор пользователя; он не должен появляться как неявная замена пустому.

Telegram на обеих страницах редактирует существующее **одно поле** `hostlist.telegramips`: не создавать копию `voice.telegram.ips` с расходящимися данными. Аналогично новые named IPSET должны быть доступны ordinary Strategies без второго независимого списка; предлагаемые имена `<IPSET:discord>`, `<IPSET:x>`, `<IPSET:sip>`, `<IPSET:custom>` необходимо реализовать/проверить в реестре target-ов, они ещё не доступны в текущем пакете. Generic parser не получает hard-coded стратегий по имени сервиса.

Из одного нормализованного набора строятся managed-файл для dvtws2 и соответствующая IPFW-таблица. Выключение Voice не удаляет список: обычный GUI-профиль может продолжать его использовать. Правка на одной странице видна на другой; Apply из устаревшей открытой формы не должен молча стирать чужие новые параметры. Этот механизм не синхронизирует PF aliases Squid или sing-box `ip_cidr`.

## 6. Перехват и выбор профиля

В целевом runtime для каждого включённого сервиса создаётся адресно-ограниченный UDP-перехват на выбранном Voice WAN, с его портами и managed IPSET. Затем в **одном** обычном dvtws2 располагаются Voice STUN-профили в фиксированном порядке Telegram → Discord → X → SIP → Custom, каждый отделён `--new`, затем текущие ordinary GUI-профили. Не смешивать блоки разных сервисов и не помещать non-STUN A2 внутрь STUN-блока.

**Без LAN-выбора:** исходящий IPFW `out ... xmit WAN` охватывает пересылаемый LAN/VLAN UDP и созданные на OPNsense сокеты, включая sing-box UDP `direct`, если остальные условия совпали. `recv` для локально созданного пакета нет; добавление обязательного LAN/recv исключило бы его. `not sockarg` не значит «весь локальный трафик исключён»: это условие socket cookie. Сохранять защиту от повторного перехвата, но отдельно проверять реальную локальную/SOCKS доставку. Создание Voice-страницы само по себе не доказывает, что SOCKS UDP ASSOCIATE работает.

**WAN не задаёт маршрут.** Выбор интерфейса не устанавливает gateway/route-to и не заставляет TNAS, клиента или sing-box выходить через него. Если маршрут выводит пакет иначе, статус должен показывать соответствующую область, а тест — несовпадение. Выбор «как у Стратегий» наследует общий WAN; явный выбор хранит Voice override и не меняет обычный `general.waninterface`.

**Обязательная инженерная проверка перед реализацией независимого WAN:** текущий backend принимает один общий WAN. Недостаточно добавить dropdown и подставить интерфейс только в одно правило. Надо проверить доступные dvtws2/FreeBSD признаки входа в общий divert и не допустить применения Voice-профиля к пакету, который вошёл по обычному правилу на другом WAN. Зафиксировать решение и тест двух разных WAN в implementation PR. Если выбранная версия движка не позволяет нужную изоляцию, показать явную ошибку несовместимого выбора до Apply и согласовать ограничение; не объявлять независимый WAN реализованным и не менять общий WAN молча. Согласованный интерфейс от этого не превращается в выбор LAN.

Пересечение IPSET/портов двух включённых STUN-профилей не позволяет одновременно применить оба: действует native first-match. До Apply выявлять пересечение с разными действиями, показывать конкретные сервисы и требовать устранить неоднозначность; одинаковое покрытие можно нормализовать только с сохранением понятной идентичности. Также выявлять конкурирующие обычные STUN-профили и объяснять приоритет Voice. Отключение Voice не запрещает действовать отдельной ordinary-стратегии, если её собственный перехват остаётся.

Capture и action проверяются отдельно. Non-STUN, захваченный all-port Voice правилом, может дальше обрабатываться подходящим ordinary-профилем. Если он ни с чем не совпал, оригинал проходит штатно. Не превращать wildcard в глобальное UDP `1-65535 to any`, не добавлять второй listener и не менять порядок IPFW/PF для страницы. Перекрытие правил не должно создавать повторный divert или повторную генерацию fake.

## 7. Сохранение, запуск, статус и применение

Применение проходит обычный lifecycle: валидация модели → нормализация IPSET → генерация полного кандидата → проверка движком и правил → транзакционная активация. Ошибка до активации сохраняет прежние постоянные данные/runtime/PID/правила; ошибка активации возвращает согласованное предыдущее состояние. Таблицы/правила принадлежат плагину, номера выделяются с проверкой коллизий; нельзя удалять чужие правила.

Boot/start/reconfigure читают **одну постоянную модель**. Включённые сервисы восстанавливаются автоматически штатным запуском Zapret2, выключенные остаются выключенными. Остановленная/глобально отключённая служба не включается вопреки общему выбору; сохранённые настройки Voice при этом не теряются. Никаких Cron, периодического enable, отдельного watcher/daemon или второго конкурирующего boot hook. Не требуется выполнять enable перед каждым звонком или после каждого reboot после принятой реализации.

Статус каждого сервиса должен различать: сохранённое желание, состояние общей службы, реально активный профиль/его идентичность, нормализованный IPSET/число адресов, эффективный WAN и порты, реальные table/rule и counters, ошибку применения. Постоянная строка `strategy=stun-zero-fake-repeats-2` уже не может описывать изменяемое действие. Нужны actual profile/normalized arguments или fingerprint с однозначной связью с ними. Статус OFF не означает автоматическое стирание введённой стратегии. Generated state-файлы остаются наблюдением, не источником желаемого состояния.

Сохранить совместимость `telegram_voice_enable|disable|status` как адаптеров Telegram к **той же постоянной модели** и lifecycle; не оставлять параллельное управление marker-ом. В новой реализации enable/disable сохраняют Telegram ON/OFF, без свободных strategy-аргументов и без управления остальными сервисами. Это изменение семантики документировать при выпуске. Статус сохраняет нужные старым лабораторным проверкам поля, но сообщает фактические изменяемые значения; runner и тесты обновляются совместно там, где старые PoC-имена были обязательны. Новую универсальную CLI/API-команду можно назвать в implementation PR, но текущим существующим интерфейсом её не считать.

## 8. Что заменяем и что сохраняем

| Сейчас | Действие при реализации |
|---|---|
| Единственный hard-coded Telegram STUN-builder | Заменить параметризованной генерацией Voice-профилей пяти сервисов в общем runtime |
| `/var/run/...enabled` как единственный запрос ON | Вывести из роли authority; единственный источник — постоянная модель. Старый marker удалить только после успешного перехода |
| Hard-coded strategy/scope в статусе | Заменить фактическим описанием выбранного/активного профиля |
| Telegram-only table/state lifecycle | Обобщить на включённые сервисы, сохранить транзакционность, rollback, ownership и cleanup |
| configctl Telegram действия | Сохранить имена как совместимые адаптеры, исключить независимый путь включения |
| Один Telegram IPSET в «Стратегии» | Сохранить тот же dataset; показать его и на новой странице |
| GUI Telegram unknown A2, остальные ordinary-стратегии | Сохранить без автоматического перемещения/переписывания; их будущая настройка — отдельный опыт |
| Общая служба/boot hook | Расширить существующий путь, не создавать вторую службу или восстановитель |
| Squid, sing-box, PF redirects/NAT, лабораторные SSH/маршруты/Docker | Сохранить; это не предмет демонтажа Voice-страницы |
| Исторические fragment-runner-ы и незавершённая `_4` ветка | Не включать в продукт, не мержить как готовую реализацию; исторические доказательства не удалять |

Миграция обязана сохранить existing Strategies/IPSET и общий service preference. Для существующего выбранного Telegram ON заранее снять точную конфигурацию/эффективное состояние; перенос ON сделать **один раз, явно и проверяемо**, не выводить его из наличия пакета/номера правила. Старый marker мог уже исчезнуть при reboot, поэтому отсутствие marker не доказывает намеренное OFF: если durable preference ещё нет, оператор выбирает галочку при первом применении. На чистой установке все сервисы OFF. Миграция и откат не должны включать ранее выключенный общий сервис.

Перед удалением старой реализации проверить её вызовы, package hooks, configd, state cleanup и лабораторный runner. Не оставлять старый prepend рядом с новым: это даст конкурирующие профили/источники ON. После неудачного перехода восстановить старое действующее состояние; после удачного повторный Apply/boot не должен импортировать старое состояние заново. Неподтверждённые когда-то обсуждавшиеся Cron/boot-файлы не считать установленными и не удалять по предположению.

## 9. Карта реализации для следующей темы

| Область | Исходная точка и работа |
|---|---|
| Меню/страница | [Menu.xml](../../src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml), controller/forms/view по образцу General; новые route/form/view и ACL зарегистрировать штатно |
| Постоянная модель | [Zapret.xml](../../src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml), migrations/API Settings; voice WAN, пять enabled/args, shared datasets, no lost-update при двух формах |
| Формы/переводы | Существующие general.xml/general.volt и каталоги переводов; тот же base_form/сервисный компонент, RU/EN/theme/responsive |
| Генерация конфигурации | [zapret.conf template](../../src/opnsense/service/templates/OPNsense/Zapret/zapret.conf), реестр/нормализация IPSET, проверка native аргументов и файловых ресурсов |
| Профили и lifecycle | [telegram_voice.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/telegram_voice.sh), [orchestrator.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh), общий service dispatch; заменить PoC authority и не дублировать профиль |
| Перехват | [firewall.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh), [ports.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/ports.sh); scoped wildcard и порты, таблицы, WAN isolation, rollback/cleanup |
| Native команды/boot | [actions_zapret.conf](../../src/opnsense/service/conf/actions.d/actions_zapret.conf), [zapret_service.sh](../../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh), существующий [20-zapret](../../src/etc/rc.syshook.d/start/20-zapret); один источник состояния |
| Регрессии | Существующие profile/config-activation/Telegram phase-B/lifecycle/GUI tests; обновить изменившийся контракт и добавить существенные случаи ниже |
| Лаборатория/документы | Адаптировать проверку helper identity при миграции, записать новую исходную конфигурацию; не переписывать результаты старых A1/A2 |

В начале разработки проверить текущий `main`, установленные возможности dvtws2/Lua и связанные исходники. Эта проверка обновляет технические детали, а не отменяет утверждённую компоновку. Номер будущего пакета назначается по правилам версий на момент реализации; эта документационная запись **не** выпускает `_4` и не меняет `0.5.0_3`.

## 10. Порядок работы и ожидаемые результаты

| Шаг | Работа | Проверяемый результат |
|---|---|---|
| 1 | Контракт модели, native allowlist, shared IPSET, миграция, источник WAN/доступная изоляция общего движка | В implementation PR определены конкретные поля/API и обработка каждого ограничения; нет второго источника ON или неработающего WAN dropdown |
| 2 | MVC-страница и меню по эталону, RU/EN, редактирование/ошибки/общий статус | Страница соответствует секциям выше, пять пар полей и пять IPSET, без отменённых галочек и LAN-выбора |
| 3 | Генератор профилей и адресного перехвата, постоянный lifecycle/CLI compatibility | Enable/OFF/Apply/start/stop/reconfigure согласованы; старый PoC не дублируется; ordinary Strategies сохранены |
| 4 | Целевые регрессии, native validation, package/CI по правилам проекта | Доказана конфигурационная корректность, rollback и package integration; не утверждается сетевой обход |
| 5 | Контролируемая owner-live проверка применения и OPNsense reboot | Выбранные профили/списки/правила возвращаются без ручного enable; OFF и global OFF тоже сохраняются; TCP-путь не нарушен |
| 6 | Возобновить кампанию на явно записанной новой исходной конфигурации | Один меняемый параметр на опыт; WIRE/REFLECTOR/MEDIA/CALL различаются, старые отрицательные тесты не повторяются без нового основания |

Эти шаги — ближайший implementation scope. Существующая RTC/ICMP/limited-fake-TTL задача остаётся в [кампании](TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md), но не является предварительным условием для создания этой страницы. Кандидаты и числовые TTL здесь не назначены.

### Обязательные проверки приёмки

1. Сохранение/повторное открытие двух страниц: галочки, многострочные параметры и нормализованные IPSET совпадают; OFF сохраняет текст; нет потери чужой правки из устаревшей формы.
2. Включённый сервис без валидного IPSET/аргументов не применяется; поля ошибки указывают строку. Запрещённые `--new`, TCP/process options и shell-конструкции не меняют runtime. Не поддерживаемые engine/Lua ресурсы не объявляются рабочими.
3. Один enabled STUN-профиль даёт правильный managed-файл/table/порты/WAN; несколько дают отделённые профили и контролируемые пересечения. Неподходящий IP/порт/WAN не получает чужое действие, original-pass и action-OFF действительно сохраняют оригинал.
4. Forwarded LAN, другой LAN/VLAN, локальный UDP и SOCKS-created UDP проверяются отдельно на одном выбранном WAN. Проверка capture не подменяется ростом общего TCP-счётчика; требуется выбранный профиль и пакетный эффект.
5. Обычная A2/non-STUN и прочие стратегии не переписаны; нет второго dvtws2, повторного divert, лишнего STUN prepend, глобального all-UDP перехвата или автоматического PFIL/NAT изменения.
6. Failed Apply/активация/коллизия таблиц возвращают согласованный previous state, не оставляют stage-таблиц/чужих удалённых правил. Общая остановка убирает свои runtime-правила, но сохраняет preference.
7. Upgrade/миграция ON, OFF, потерянного старого marker и чистой установки имеют разные явные ожидания; повторный Apply идемпотентен. Существующие configctl действия и runner не дают ложного PASS по старой постоянной строке.
8. После OPNsense reboot измерение выполняется **до ручного enable/Apply**: сохранённые ON и OFF, служба, фактические профили/таблицы/правила/WAN и оригиналы соответствуют pre-reboot. Потребность запустить enable вручную означает незакрытый persistence gate.
9. Сохранены отдельные LAN/SOCKS TCP-to-parent проверки лаборатории. TNAS `/32` и Docker остаются ручными: пользоваться [существующим runbook](TELEGRAM_LAB_OPERATIONS.md), не внедрять route Cron или autostart.
10. Конфигурационная/GUI/boot приёмка записывается отдельно от результатов звонка. Для рабочего Telegram preset нужны повторяемый Docker `MEDIA_PASS` и затем реальный UDP `CALL_PASS`; Discord/X/SIP не объявляются проверенными по Telegram-тесту.

## 11. Короткое задание для новой темы

> Реализуем страницу «Передача голоса» в os-zapret2-restyle по docs/architecture/VOICE_TRANSMISSION_GUI.md. Сначала прочитать AGENTS.md и обязательные документы в порядке START_HERE. Дизайн как у «Стратегии», меню между «Стратегии» и «Лаборатория», WAN сверху, пять сервисов с галочками/параметрами и отдельными общими IPSET. LAN-выбора и галочек local UDP/boot нет; локальный UDP включён в область, выбранное состояние постоянно. Non-STUN остаётся в «Стратегии». Заменяем временный hard-coded helper штатной моделью/lifecycle, один dvtws2. Существующие TCP/Squid/sing-box/PF/маршруты не переделываем. Страница, миграция и boot ещё не реализованы; рабочая голосовая стратегия ещё не доказана. Вести реализацию через GitHub/CI по правилам проекта, с проверками из этого задания.

### Read-only cross-journal recovery correlation (2026-10-09)
The future restorer MUST link sealed previous Config/runtime backup to the whole-cutover intent and old canonical IPFW ownership manifest to the separate IPFW ledger; checks are now staged offline in `voice_cutover_recovery_preflight.py`. Preflight rejects mismatched old IPFW fingerprints, absent/unsafe evidence, orphan intents and incompatible phases; all responses prohibit mutation and automatic recovery. Whole-cutover schema 1 does not bind the desired IPFW manifest or contain the complete engine/supervisor restoration state: no unattended restart replay and no Voice Apply until the missing native adapter and contract are qualified. Existing legacy PoC and lifecycle fail-closed guard stay in force.

### Журнал Voice v2: привязка целевого IPFW, без активации (2026-10-09)

- Действующий schema 1 остаётся читаемым для диагностики и существующих mock-тестов. Новый **только тестовый** `VoiceCutoverJournal.begin_bound` формирует schema 2 с `candidate.firewall_manifest_sha256`, вычисленным из строго нормализованного `canonical_manifest(desired)` и IPFW ledger `fingerprint`. Эта запись проходит ту же fsync/rename/checksum цепочку на переходах prepared → mutating → committed, и `voice_cutover_guard.py` продолжает блокировать любое незавершённое состояние.
- Read-only `inspect_recovery` для schema 2 сравнивает **оба** прежний и целевой IPFW-хеши с отдельным ledger; неверный desired manifest, чужой intent и прежнее владение после committed запрещены. После удаления отдельного IPFW-intent совпадение committed-ownership с v2-целью даёт только `review-required`, **не право на восстановление**.
- Версия 1 не получила задним числом «доказательство» целевого состояния: если schema 1 не знает desired IPFW, постфактум его нельзя угадать. Хеши не доказывают реальные kernel rules, состояние dvtws2 и supervisor; для Apply нужны квалифицированные native adapters, блокировки и проверки перезагрузки.

### Удаление кнопки Voice Apply из черновой формы (2026-10-09)

По прямому решению владельца проекта из `voice.volt` удалена неработающая кнопка `voiceApply` (Apply настроек Voice), в JS удалено обращение к её селектору. На странице **остаются** `voiceValidate` (только проверка), `voiceReleaseApply` (установка версии пакета, а не настроек Voice), наблюдение за IPFW и контроль существующей службы. Ни один Voice Save/Apply API не включается; кэш введённых полей и сохранённая модель не меняются до будущей согласованной реализации. `VoiceApplyCandidate` используется как side-effect-free нормализатор/validator и не является вызываемым Apply API. Текущие ранее документированные макеты нижней строки с кнопкой «Применить» относятся только к исходному дизайну и **заменены этим решением для Draft**. Старый Telegram PoC, журнал блокировки и действующая OPNsense не изменяются.

### Копия для будущего восстановления — без применения к системе (2026-10-09)
`voice_cutover_restore_stage.py` готовит **отдельную проверенную копию** прежних `config.xml` и `runtime-v2` в приватной временной области; действующие пути и процессы не меняет. Исходный сохранённый snapshot и результат проверяются по одинаковому манифесту, хешам файлов и ссылке на whole-cutover journal. Пока файл не прошёл полную проверку, целевой staging-каталог не публикуется. Копирование не следует symlink, не перезаписывает существующий каталог, оставляет файлы staged 0600 и хранит исходные mode только в манифесте. Нет CLI/configd, автоматического восстановления, интеграции с производственным Config, supervisor или IPFW. Этот код не означает готовую native Voice Apply.

### Проверяемый прежний процессный состав (Draft v0.5.1_3)

Новый `backend/voice_process_recovery_evidence.py` — **только изолированный файловый контракт**: в качестве источника ему передаётся read-only тестовый адаптер. Он трижды считывает неизменное состояние прежнего `dvtws2` и двух supervisor-ролей (daemon/monitor), требует согласованного running/stopped, разных PID + start token и точных ожидаемых executable identity. Значение `runtime_args_sha256` сопоставляется с верифицированным `dvtws.args` в существующем приватном snapshot runtime. Запись 0600 в 0700 отдельном каталоге содержит контрольные суммы engine и supervisor, которыми затем связывают `VoiceCutoverJournal.previous`; проверка после перезапуска читает их без запуска процессов. Отсутствуют настоящие FreeBSD ps/pidfile adapters, доказательство живых kernel processes, перезапуск, уничтожение старого PoC и автоматический restore. Запрещено считать это разрешением на Voice Apply.

### FreeBSD read-only `ps`/PID-файлы, v0.5.1_4

`voice_native_process_probe.py` реализует отдельный **не подключённый к жизненному циклу** reader для подтверждения физического состава старой службы. Читает только три фиксированных PID-файла с запретом symlink и native `/bin/ps` через список argv (без shell), а также глобальный process inventory. При ON допускает строго один dvtws2 и точно одну пару daemon/monitor; проверяет полные PID и стартовые идентификаторы, что служебные команды соответствуют ожидаемым абсолютным токенам. При OFF одного лишь отсутствия PID-файлов недостаточно: процессный список тоже должен не содержать соответствующих запусков. Существуют проверки на дубли, чужие процессы, исчезновение и изменения команд. Данная проверка ещё не гарантирует полное соответствие аргументов живого dvtws2 файлу `dvtws.args`; это открытый gate перед активацией и owner-live FreeBSD acceptance. Запуск и остановка процессов по-прежнему отсутствуют, старый telegram_voice не демонтируется.

### Коррекция чтения процесса FreeBSD, v0.5.1_5

В системном выводе `ps` могут встречаться пустые строки. Ранний строгий парсер отвергал даже полностью остановленную службу из-за пустой строки в тестовом `ps` output. Читаем только непустые строки, но **всё ещё отвергаем некорректные непустые строки, неизвестные процессы и дубли**. Добавлены соответствующие регрессии. Эта корректировка не включает live Voice Apply и не меняет прежние правила IPFW или supervisor.

### Проверка пяти ресурсов при восстановлении (v0.5.1_6)

`voice_cutover_full_recovery.py` связывает одновременно прежний `config.xml`, runtime tree, `dvtws2`, supervisor и IPFW через долговечный cutover journal и отдельный IPFW ledger. Старые `config/runtime` берутся только из проверенной резервной копии, `engine/supervisor` — только из приватной процессной записи v0.5.1_3, `firewall` — из whole-cutover journal с IPFW-cross-check. **Реальное текущее состояние пока предоставляет только тестовый, внедряемый извне read-only observer.** Для каждой из пяти областей требуются строгие SHA256 и две неизменные последовательные записи; в конце повторно проверяются сохранённые источники и оба журнала. Неизвестный, частично изменённый, повреждённый, нестабильный или committed state блокируется. Полное совпадение с предыдущим состоянием обозначает `review-required`, но **никогда** не даёт разрешение на Apply, replay, очистку журнала или восстановление автоматически. Новые желаемые hash для Config/runtime/engine/supervisor отсутствуют в schema 2, поэтому certified committed недостижим. После холодного reboot PID+start identity прежнего процесса не может считаться действительным: нужен отдельно проверенный новый запуск. На работающий OPNsense этот код не влияет.

### IPFW kernel ownership read-only witness (v0.5.1_7)

`voice_native_ipfw_ownership.py` использует существующий **только читающий** FreeBSD IPFW adapter: запрашивает реальные правила в нашем номерном диапазоне и все пять адресных таблиц вместе с возможными `_stage`. Подтверждение допускается только при точном совпадении правил и множеств IPv4-адресов с проверенным журналом `VoiceOwnershipStore`; для IPSET порядок вывода значения не имеет. Любой неизвестный/пропавший объект или оставшийся `_stage` вызывает отказ. Результат — SHA256 канонического **записанного** ownership manifest, но **не** разрешение применять его, удалять записи, мигрировать прежний PoC или восстанавливать что-либо. Нормальный runtime `zapret_service.sh` этот модуль не вызывает. Весь остальной процесс/Config/kernel cutover остаётся незавершённым.

### Независимое чтение текущих Config/runtime (v0.5.1_8)

`voice_native_file_observer.py` — отдельный невключённый в production жизненный цикл **read-only** модуль для сравнения текущих Config и дерева runtime с прежними приватными резервными копиями. Он вычисляет точно те же canonical SHA256, что `voice_cutover_backup.bound_resource_fingerprints`, но не создаёт файлов и не заменяет runtime. Обход директорий привязан к открытым файловым дескрипторам (`dir_fd`, `O_NOFOLLOW`), запрещает ссылки, hardlink, специальные типы и чужого владельца, ограничивает суммарный размер, число объектов, глубину и повторно сканирует все данные, отказывая при изменении между сканированиями. Новый observer **не гарантирует владение native lifecycle/config locks** и не удостоверяет dvtws2/supervisor или live IPFW: это отдельные открытые блокирующие проверки. Откат и Apply не подключены.

### Полная композиция read-only наблюдений прежнего экземпляра (v0.5.1_9)

`voice_native_full_observer.py` собирает в одну структуру пять SHA256: реальные Config/runtime (из `voice_native_file_observer`), runtime-anchored engine/supervisor (из верифицированной приватной прежней записи и текущего `probe`) и реальное состояние принадлежащих плагину IPFW правил/таблиц (из `voice_native_ipfw_ownership`). Компонент подключён **только к изолированным тестам**, без службы/GUI/автоматического вызова. `voice_cutover_full_recovery.inspect_full_recovery` повторно наблюдает состав и сопоставляет его с обоими журналами. Если после перезагрузки `dvtws2` получил новый PID/время запуска, его нельзя признавать тем же экземпляром по старой записи: требуется отдельный критерий восстановления и доказательство актуального native argv. Даже при пяти совпадениях результат — только `review-required`; любые `can_activate`, `safe_to_mutate`, `can_recover_automatically`, `safe_to_finish_intent` остаются `false`. Production dual-lock и реальный транзакционный исполнитель ещё не сделаны.

### Дополнительное доказательство режима Config (v0.5.1_10)

Контракт пяти SHA256 в старом журнале намеренно хранит `config` как хеш **содержимого**, поэтому он не видит изменение `chmod` без изменения XML. При проверке состояния **прежнего экземпляра** `NativePreviousObserver` теперь обязательно связывает `LiveFileObserver` с `previous_backup` и подтверждает сохранённый `manifest.config.mode`. Даже совпадающие байты XML при отличающихся правах файловой системы приводят к `blocked`, без попыток исправить права автоматически. Проверка не меняет прежнюю schema или режим работы установленного плагина.

### Проверка argv нового экземпляра после перезапуска — v0.5.1_11

`voice_restart_argv_attestation.py` создаёт точный список аргументов прежней проверенной конфигурации: разбивает сохранённый `dvtws.args` на отдельные токены по той же модели, что `launcher_prepare_argv` (`awk`, **без shell-интерпретации кавычек**), а затем добавляет фактические служебные аргументы `--sockarg=0x200` и `--user=nobody`. Тестовый read-only provider должен предоставить именно **массив kernel argv**, а не человекочитаемую строку `ps`. Дважды независимо сверяются точные аргументы dvtws2, daemon и monitor, независимые PID и более поздний start token относительно приватной записи до переключения. Любая неоднозначность, изменившийся source, чужие аргументы или повторение старого экземпляра запрещены. **Семантическое совпадение аргументов ещё не подтверждает наличие UDP socket или передачу голоса**, не считается восстановлением и не разрешает Apply. Настоящий FreeBSD argv reader, доказательство readiness и production lifecycle всё ещё отсутствуют.

### Kern.proc.args: получение реального NUL-разделённого argv (v0.5.1_12)

Добавлен не подключённый к runtime модуль `voice_freebsd_kernel_argv.py`, который в FreeBSD получает аргументы через `sysctlbyname("kern.proc.args.<PID>")`: два read-only вызова sysctl для определения длины и чтения данных с жёстким лимитом. Аргументы возвращаются в NUL-разделённом виде и не требуют неоднозначного парсинга `ps`. Реальные данные OPNsense **ещё не проверены**: в CI подставные raw-byte ответы и до/после проверяется стабильность идентичностей всех трёх процессов. Более того, системный API допускает изменение process title, поэтому даже прочитанный kernel argv нельзя считать криптографическим подтверждением `execve`, стабильной работы UDP, готовности звонка или разрешением применять/восстанавливать конфигурацию. Без native lock, проверки фактического binary pathname/credentials и live qualification никакой Apply не допускается. Официальное описание FreeBSD: https://man.freebsd.org/cgi/man.cgi?query=sysctlbyname&sektion=3.

### Проверка kernel executable и полномочий процесса (v0.5.1_13)

Read-only модуль `voice_freebsd_process_security.py` проверяет для трёх ролей (`dvtws2`, daemon, supervisor monitor) сразу два источника FreeBSD: `kern.proc.pathname.<PID>` — путь запущенного text vnode, и `/bin/ps -p PID` с **числовыми** EUID/RUID/SVUID/EGID/RGID/SVGID. Перед и после чтений сверяются PID и start token. **Имя скрипта supervisor не обязано совпадать с kernel executable:** при запуске через `/bin/sh` проверяется `/bin/sh` и отдельно прежний путь скрипта в таблице процессов. Ожидаемые пользователи, группы и настоящие бинарные пути должны быть независимо согласованы с производственной конфигурацией и приняты на живой OPNsense; сейчас это входные тестовые константы, не разрешение на активацию. На FreeBSD 15 CI проверяем реальные sysctl/ps только относительно собственного тестового процесса. Совпадение не доказывает хеш бинарного файла или готовность передачи голоса; работающий Telegram PoC не изменён. Документация API: https://man.freebsd.org/cgi/man.cgi?query=sysctlbyname&sektion=3 и https://man.freebsd.org/cgi/man.cgi?query=ps&sektion=1.

### FreeBSD 15: фактический ABI чтения kernel argv (v0.5.1_17)

В FreeBSD 15 CI #38008380039 подтверждено: sysctlbyname("kern.proc.args.<PID>") возвращает ENOENT/2; sysctlnametomib("kern.proc.args") выдаёт числовой MIB из трёх компонентов, а sysctl(MIB + PID) возвращает длину argv собственного процесса (68 байт). Несвязанный с runtime, read-only voice_freebsd_kernel_argv.py теперь использует этот нативный числовой вызов с ограничением размера до чтения, повторным контролем длины, строгим NUL-разбором и проверкой прежней PID/start identity вокруг всех ролей.

Linux/FreeBSD тесты отдельно внедряют ошибки преобразования OID, неверную глубину MIB, отказ/изменение длины и неоднозначные аргументы. Нативный self-process smoke обязателен в FreeBSD 15 CI. Этот API не доказывает неизменность execve argv, подлинность процесса, пригодность медиа или возможность безопасного reboot/recovery; live Voice Apply остаётся отключённым.

### FreeBSD 15: исправление числового MIB для process pathname (v0.5.1_16)

Нативный CI run 38006536188 доказал: sysctlbyname("kern.proc.pathname.<PID>") возвращает ENOENT/2, а sysctlnametomib("kern.proc.pathname") выдаёт MIB из трёх компонентов; числовой sysctl с дополнительным PID даёт 26 байт длины pathname собственного процесса. Неподключённый к production модуль voice_freebsd_process_security.py теперь использует именно числовой интерфейс с двумя ограниченными чтениями, строгим NUL/ASCII pathname, независимым ps UID/GID и повторной проверкой PID/start identity.

Linux выполняет инъекционные ABI fault-тесты; FreeBSD 15 обязан дополнительно выполнить настоящий self-process sysctl+ps тест. Это не подтверждает фактические полномочия процессов на пользовательской OPNsense, не авторизует Apply или автоматическое recovery.

### Долговечная политика kernel-image/UID/GID (v0.5.1_14)

В прежнем schema-2 whole-cutover журнале есть SHA256 старых пяти ресурсов и желаемого IPFW, но не зафиксировано, какие именно kernel pathname и реальные/эффективные/сохранённые UID/GID допустимы у трёх процессов. Новый изолированный `voice_security_policy_evidence.py` сохраняет отдельный приватный, неизменяемый в пределах транзакции объект политики (0700 каталог, 0600 файл, SHA256 и fsync) с точной привязкой к прежним fingerprint Config/runtime/dvtws2/supervisor/IPFW. В `VoiceCutoverJournal` появилась **schema 3**, где кроме прежнего `firewall_manifest_sha256` фиксируется `process_security_policy_sha256`. Старые schema 1/2 продолжают читаться. При полной read-only triage schema 3 требует реального файла политики и стабильного double-read независимого reader, подтверждает kernel executable path и UID/GID каждого процесса, а также старые PID+start tokens. Любая неполнота — blocked; совпадение — исключительно `review-required`, не разрешение менять что-либо. **Ожидаемые UID/GID ещё задаются внешним источником и не подтверждены на вашей OPNsense**, поэтому их сохранение не превращает policy в production authority. Native lock, восстановление и реальная передача голоса не активированы.

### Исправление синтаксиса новой схемы политики (v0.5.1_15)

Первый CI `_14` прервался на импорте нового модуля из-за ошибочной запятой в Python dictionary comprehension; тесты не запускались. Исправлено отдельной кодовой ревизией `_15`, согласно DEV-032. Добавлена обязательная компиляция затронутых модулей через `python3.13 -m py_compile` перед новым функциональным тестом в Linux и FreeBSD 15 CI. Контракт по-прежнему остаётся read-only, без права изменять IPFW, запускать движок или автоматически восстанавливать конфигурацию.
