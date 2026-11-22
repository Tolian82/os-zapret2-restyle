# ТЗ_6v5 — пошаговый план внедрения единого запуска (S00–S20)

**Действующее ТЗ:** [ТЗ_6v5](TZ_6v5.md). **Детали:** [декларативный runtime](ZAPRET2_DECLARATIVE_RUNTIME_MANIFEST.md), [FD9 lifecycle audit](ZAPRET2_CANONICAL_SERVICE_LIFECYCLE.md). [Старый P0–P5 план](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) сохраняется для истории и прежних доказательств, но **не** является активной очередью.

**Точка старта, 22.11.2026:** `main 62b64e82` = source-only `0.6.5_121`, никакого `_121.pkg`; у владельца опубликованный/установленный `_117.pkg`, последняя ручная Stop→Start = RUNNING, два Strategies Apply PASS. [Lab #1224](https://github.com/Tolian82/os-zapret2-restyle/issues/1224) stage90/99 RESTORE_FAILED, [Auto #1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223) native YouTube no Found и [UI routes #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225) OPEN. [Draft PR #1228](https://github.com/Tolian82/os-zapret2-restyle/pull/1228) — частичная pre-manifest реализация Lab/pkg на старой базе; не merge, не публиковать. После документационного merge источник и следующий номер revision определить заново, а не заимствовать `_121` из старого PR.

**Метод:** выполнять **S00 → S01 → … → S20**; для каждого шага: (1) действие, (2) RED→GREEN/нативное свидетельство, (3) переход только при GO. При FAIL устранять конкретную причину **в том же шаге**, сохраняя контекст stage/rc/SHA; не компенсировать missing evidence масштабным новым защитным механизмом. Source tests, disposable OPNsense и owner-live — **разные уровни приёмки**.

**Наследуемый обязательный регрессионный сценарий WAN-first / Prestart Lab:** [LC-06/11/12](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md), [G05](../verification/G05_WAN_ONLY_NATIVE.md), [G08](../verification/G08_PRESTART_LAB_NATIVE.md), [ТЗ_6v5 `6.1](TZ_6v5.md). **Сохранить** Save только WAN при Enabled=OFF, без upstream, обычного runtime/active manifest или непустой пользовательской стратегии. После **явной** установки upstream Standard/Extended Laboratory обязаны запускаться **без первого обычного Start**, проверять STOPPED→STOPPED и отсутствие остаточных Lab IPFW; старый native G08 PASS не переносится автоматически на новое поколение. Отсутствие WAN → `wan-required` раньше отсутствия двигателя; сохранённый WAN + отсутствующий двигатель → `engine-not-installed` без Job. G05→G08 — обязательный source/native RED→GREEN до и после переделки launcher.

**Точный объём RU/EN (V5-12):** проверять **только** ошибки прежнего физического `Start/Stop/Restart` и связанные с этими переходами сообщения через GUI/Apply/Voice/Lab/pkg/boot. Не проводить аудит всех переводов Voice/Strategies/Lab. Для старых lifecycle ошибок — KEEP/ADAPT/REMOVE по действительным producer и GUI consumer; новые реальные ошибки единого Start/Stop/Restart — RU/EN через прежние механизмы. [ТЗ_6v5 `7.1](TZ_6v5.md).

**Новое обязательное расширение ТЗ_6v5 (V5-13/V5-14):** публичный `zapret_service.sh start|stop|restart|reload|status`, а при нижнем «Применить» pure diff-planner выбирает `NO_CHANGE|RELOAD|RESTART|START|STOP|SAVE_ONLY|REFUSE` по **effective** sealed state. `reload` допускается **только** для проверенного перечитывания содержимого уже подключённых HOSTLIST/IPSet без остановки dvtws2/supervisor/IPFW. Новые argv/Voice/Target Mode/WAN/divert и mixed changes → один full restart. Не считать `SIGHUP`/rc0 фактом уже выполненного reread; lazy engine reload допускает `RELOAD_REQUESTED`. При ошибка reload нет скрытого restart. Дополнительные CLI опции только allowlisted; native stderr/exit/stage и RU/EN **lifecycle-only** mappings. [Нормативный контракт `5.1–5.4](TZ_6v5.md). Предыдущий WAN-first/G05→G08 остаётся обязательным.

**Неприкосновенные инварианты:** один original FD9/Config writer/долговечный журнал, один `dvtws2`, original `shared_apply_operation`, native P1/P2/FD и WAL/ACK, только собственный IPFW; без SIGSTOP/SIGCONT, observer/second daemon, несанкционированных остановок для Auto, PID-journal deletion или угаданного recovery. Подтверждённый manual/Found/managed и исправный операторский Stop важнее неподтверждённых Auto-строк.

## G0 — документы, исходники и воспроизводимый RED (S00–S03)

### S00. Закрепить новую редакцию требований и маршрут

1. Создать `TZ_6v5.md` и данный план, расставить активные ссылки из накопительного P0–P5 плана, `ROADMAP`, `START_HERE`, `PROJECT_STATE`, `architecture/README`.
2. Зафиксировать DEV-065/066/067, текущие `_117`/`_121`, открытые Lab/Auto, отсутствие новой сборки.
3. Создать документационный PR с очередной действительной ревизией по `GH-014/015`. Проверить exact-head docs/version/link checks; **никакого product-source или пакета**.

**GO:** merged docs+next revision, без изменений действующего runtime. **NO-GO:** ссылки ведут на старую ACTIVE очередь или указана вымышленная сборка.

### S01. Пересмотреть PR #1228 на фактическом новом main

1. Прочитать diff, CI/native failures и полный список 12 файлов #1228, особенно partial `original_fd9_lifecycle_transition` (только Lab/pkg) и pre-manifest `_121`.
2. Сверить с новой схемой: сначала clean-install/Status/чистый compiler; удалить/переработать конфликтующие предположения вместо слепого переноса старой реализации.
3. Либо безопасно rebase/rework тот же Draft PR, либо закрыть superseded с объяснением и открыть **один** новый product PR. Номер product revision = актуальный `main+1`, без параллельных PR с одинаковой ревизией.

**GO:** один актуальный исходный branch и детальное решение keep/rework/drop каждой старой правки. **NO-GO:** merge старого #1228 или неподтверждённый base.

### S02. Read-only audit реального маршрута запуска

1. Зафиксировать frontend→API→configd→script для Strategies/Voice Play/Restart/Stop, System Services, двух Apply, Boot/recovery, Lab, protected pkg prepare/finish, Auto Restart, runtime-failure callback и upstream «Установить версию».
2. Для каждого зафиксировать где FD9, выбор Common/Voice/legacy owner, реальные `exec/kill/IPFW/Config` side effects, rollback/terminal receipts. Скриншотные иконки без проверки tooltip/handler **не** считать доказательством.
3. Снять карту current `zapret.conf` inline, XML `Zapret.xml`, `registry/storage`, `target_mode`, `profile_pipeline`, `auto_detect_origin_map`, Voice producers, `shared_apply_operation` и exact active source map.

4. Для **старого Start/Stop/Restart** составить ограниченный реестр `emitter → stage/reason/rc → GUI caller/handler → RU/EN`, включая физические переходы при Apply, Voice, Lab restore, pkg/boot. Не инвентаризировать посторонние ошибки валидации и списков.

5. Инвентаризация каждого реального GUI/configd/Apply/Boot/Lab/pkg вызова старого `reconfigure` и `restart`: есть ли hidden Stop→Start, как подтверждается terminal result, что сохранено в original FD9. Отдельно перечислить list-only paths и текущие P1/CAS/ACK/managed hot-writers. Выделить только lifecycle RU/EN строки для миграции.

**GO:** полная таблица физических writers и их callers, включая обходные paths и наследование FD9. **NO-GO:** проверены только публичные CLI три команды.

### S03. Сформировать RED-фикстуры на старом фактическом генераторе

1. Сохранить deterministic old baseline: итоговые `dvtws.args`, actual native profile order/source-map/IPFW/Voice для `all/list/auto`, explicit selectors, User vs YouTube first-match, empty/nonempty/large/invalid lists.
2. Написать RED на no-engine, no-Config, no-manifest, иностранные PID/IPFW, stale map, invalid refs и Stage/rc diagnostics; на status no side effects и one physical transition dispatcher. Добавить регрессию G05/G08: WAN-only Save при пустых user Strategy/hostlists и Enabled=OFF без upstream/manifest; WAN-first error precedence до Lab Job; реальный Standard/Extended Lab после установки engine до обычного Start.
3. Проверить, что тесты действительно вызывают производственный генератор/templates и **падают на доказуемом дефекте**; Lab stage90 RED и Auto learning RED добавлять по объективной физической трассе, не фальсифицируя событие.

4. RED-тесты старых переводов Start/Stop/Restart: показать реальные sources, доходимость до обоих языков; отдельно фикстуры исчезнувших source stages, чтобы stale lifecycle errors не пережили refactor. Сохранённые Lab/operation receipts не считать «мёртвыми» без проверки.

5. RED fixture на old/next effective semantic diff: NO_CHANGE, HOSTLIST/IPSet bytes only, изменение source ref, reorder profiles, DPI/Voice/Target Mode/WAN/divert, mixed diff, stopped/incomplete/foreign. Доказуемо падают и тесты «reload не меняет PID/owned IPFW», lazy reread→REQUESTED, failure→no hidden restart, CLI unknown option rc64, old/new lifecycle GUI RU/EN.

**GO:** baseline и воспроизводимый RED доступны CI. **NO-GO:** unit mocks или grep объявлены native доказательством.

## G1 — безопасная пустая система, статус и чистая конфигурация (S04–S09)

### S04. Независимый inventory компонентов

1. Read-only различать package plugin (вне CLI, если не установлен), binary upstream Zapret2 valid/absent, saved Config initialized/absent/invalid, active sealed manifest valid/missing/stale, runtime RUNNING/STOPPED/INCOMPLETE/FOREIGN.
2. Протестировать матрицу «нет ни одного компонента», «есть plugin без engine», «есть engine без Config», «есть owner с повреждённым editable Config» и «foreign owner».
3. Отсутствующий manifest/config не разрешает новый Start или destructive Stop чужого процесса.

**GO:** достоверная component matrix, ноль побочных записей.

### S05. Read-only status и диагностический конверт

1. Реализовать `status --json` с прежним совместимым plain `status` и собственным верифицированным runtime/epoch/IPFW census; status **не** компилирует, не Apply, не стартует, не сохраняет.
2. Кодировать `timestamp/stage/code/operation_id/generation/exit_status/runtime_state/message/stderr_excerpt/log_ref`. Подключить реальные `dvtws2`, supervisor, setup, configd, IPFW, P2, Apply, Lab errors в существующее защищённое, ограниченное, ротируемое хранилище.
3. RED→GREEN для `ENGINE_NOT_INSTALLED`, `CONFIG_UNINITIALIZED`, `MANIFEST_UNAVAILABLE`, `MANIFEST_INVALID`, `ENGINE_EXIT_EARLY`, `WAN_UNAVAILABLE`, `IPFW_ATTACH_FAILED`, `LAB_RESTORE_FAILED`; ограничить/очистить stderr, секреты/домены/IP/args не раскрывать.

4. Сохранить уже существующие RU/EN сообщения о запуске/остановке/перезапуске и правдивом состоянии после ошибки; новый diagnostic code полезен GUI только если связан с действительным lifecycle failure. Не переделывать остальные сообщения.

5. Расширить diagnostic envelope `action,stage,code,exit_status,runtime_before/after,generation,verification,stderr_excerpt,log_ref` для пяти команд; native engine/supervisor early/delayed errors без raw sensitive args. `status --json` читает последнее событие, не пишет его. `reload --check` read-only, различает RELOAD_SAFE/RESTART_REQUIRED/NOT_RUNNING/REFUSE.

**GO:** действительный stage/rc + последняя ошибка показаны в CLI/GUI; no-write/secret tests PASS. **NO-GO:** зелёный Status лишь по PID.

### S06. Первый install и повторный install

1. На пустой fixture GUI/status доступны без engine/сохранённого профиля/manifest; ни скрытого install upstream, ни Start.
2. Единожды, **только при доказанном first-install**, штатным existing Config writer установить безопасный service OFF и утверждённые YouTube Domains + TCP/QUIC baseline. Разрешить впоследствии пустую Strategy.
3. Reinstall с сохранёнными пользовательскими YouTube/User/Found/IPSet/Exclude/Voice/WAN/Strategy обязан сохранить их без изменений; ordinary uninstall сохраняет, purge требует отдельного явного действия.
4. **WAN-first:** через прежний нижний GUI/API Apply сохранить только WAN (при пустых пользовательских Strategy/списках, Enabled=OFF и отсутствующем upstream), под original FD9 и SharedConfigCommit::persist(), без dvtws.args/manifest/engine/IPFW. Проверить нативный Config readback/F5, отсутствие normal PID/IPFW и сохранность пустых полей после reinstall. Для STOPPED со старым sealed owner требуется соответствующая полноценная транзакция, не слепой shortcut.

**GO:** empty→seed once→reinstall **и G05 WAN-only Save** PASS, no engine is safe. **NO-GO:** повторная установка перезаписывает текст или WAN требует обычного Start/манифеста.

### S07. XML OPNsense adapter → neutral model

1. Из текущей модели `OPNsense/Zapret` получить read-only валидный typed projection, без второго Config writer и shell execution.
2. Отделить platform XML/WAN/configd/pkg adapters от общего компилятора, для будущей pfSense оставить **интерфейс**, не добавлять неподтверждённый порт.
3. Проверить enum, отсутствующие поля/невалидные значения, прежний native WAN resolver (`wan_preflight`/`config_resolve_interface()` с допустимыми назначенными TUN/OPT, в том числе без IPv4), registered list IDs и лимиты. Не использовать stale `zapret.conf` для Lab WAN device.

**GO:** neutral model корректен и deterministic; Config ни разу не изменён.

### S08. Pure compiler target/resource/Voice/native

1. Переиспользовать `registry.sh`, `storage.sh`, `target_mode.sh`, `profile_pipeline.sh`, `auto_detect_origin_map.py`, Voice producers и уже принятый native 2-tier generator.
2. Детерминированно вычислять requested/effective: manual empty≠Found disabled, Found initially empty but live target, Exclude empty OFF/invalid FAIL, Voice checkbox ON + empty/invalid IPSet FAIL, OFF retains draft; `auto` только eligible learning, `list/all` без clone, явные selectors приоритетнее default.
3. Гарантировать все обычные working профили перед learning; known User не перехватывается YouTube learner, нет hidden `<HOSTLIST:auto>` или observer, exact final native number map.
4. Сравнить parity S03: actual `dvtws.args`, capture IPFW/Voice/source-map по каждой ветке. Pure compiler не управляет процессом/IPFW/FD9.

5. Сделать deterministic semantic structural fingerprint и чистый classification planner: content-only linked active HOSTLIST/IPSet refs кандидат RELOAD_SAFE; изменение argv, Source Map, IPFW, selectors, Voice, WAN, engine version или смешанные edits → RESTART_REQUIRED. Данные Found/managed остаются отдельным original mutable P1 path; не обещать runtime reload для неподключённого списка.

**GO:** parity и negative tests GREEN без изменение native first-match. **NO-GO:** новая схема молча меняет DPI args.

### S09. Root manifest и полная attestation refs

1. Зафиксировать JSON schema/root `schema/generation/service/resources/refs` с **только** флагами и verified references; все стратегии/порядок/Voice/Auto/IPFW/engine args — отдельные controlled generation artifacts.
2. Immutable generated artifacts: owner/mode/size/SHA/seal, отсутствие symlink/traversal/foreign files/циклов, exact `dvtws.args` + source-map generation. Re-attest при activation.
3. Live Found/managed content **не** фиксировать вечным SHA immutable JSON; разрешить только исходные P1/CAS/ACK hot-updates. В редакторе данные могут измениться до Apply, но active поколение не меняется преждевременно.
4. Test missing/stale/modified/oversize/invalid/foreign refs, race, old generation.
5. Active immutable JSON и `dvtws.args` — требования **ordinary** Start/Apply, не защищённого Lab Job со своей временной конфигурацией при сохранённом WAN и установленном engine.

6. Root manifest фиксирует structural fingerprint и список разрешённых mutable references без pin SHA их live contents. Переключение structural generation требует guarded restart; reload не публикует новый arbitrary active root/epoch без валидной operation receipt. Проверить tamper и валидность old/new refs.

**GO:** valid candidate + tamper refusals, без второго user-editable config.

## G2 — один sealed release и один физический исполнитель (S10–S14)

### S10. Candidate staging, original FD9, atomic promotion

1. Создавать manifest и sibling artifacts в существующем staged/release transaction, первоначально **без activation**. Compare existing active projection, не останавливая engine.
2. Под `shared_apply_operation.py`/original FD9 проверить immutable plan→candidate→sealed promotion→semantic rollback; предусмотреть crash после prepare/promote/restore, не создавать второй журнал/lock.
3. Не приводить старые исторические схемы runtime через новый compatibility fallback «на всякий случай» (DEV-050); сохранять только rollback конкретной текущей операции.

4. В рамках existing sealed `shared_apply_operation` предусмотреть staged list-only commit и protected rollback, проверку old bytes/revisions/CAS. Если multi-file изменение нельзя сделать семантически согласованным без Stop, classification = RESTART_REQUIRED до мутации; ни второй writer, ни второй журнал.

**GO:** immutable candidate preflight и crash recovery подтверждены; ни одна пользовательская data write не обойдена.

### S11. Единственный физический Start

1. В `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` создать ONE authoritative Start transition по authenticated active release/held FD9; не компилировать стратегии/парсить XML в нём.
2. Verify binary, saved owner, generation, current journal, WAN, IPFW and engine args/maps before starting ровно одного `dvtws2`/supervisor; attest terminal RUNNING.
3. Negative: no binary/manifest/Config, engine early exit, invalid WAN, foreign PID/IPFW, stale/mutated release, concurrent operation.

4. Для отказов **физического Start** проверить source/error stage/rc, существующее GUI уведомление в RU и EN; новый genuine Start error оформить в обеих локалях без висящего неиспользуемого ключа.

5. Реализовать общий результат пяти команд с кодом/стадией/exit и проверкой before/after. `restart` внутри dispatcher вызывает единственные physical Stop→Start; не вводить второй способ `exec`/`kill`. Системный `status` остаётся read-only; parse options строго action-specific.

**GO:** exact Start state and errors; нет скрытой альтернативной ветки.

### S12. Единственный физический Stop

1. В том же файле реализовать ONE authoritative Stop verified previous owner; Stop не должен зависеть от возможности пересобрать теперь повреждённый редактируемый XML/new candidate.
2. Делегировать неизменённые P2/epoch/FD/N retirement и удаление **только подтверждённого** собственного IPFW, supervisor/engine cleanup, terminal STOPPED.
3. Native negative: late append, stopped/no owner, foreign owner, wrong epoch/lock, external IPFW missing (#1210 — отдельная диагностика, НЕ новый auto-heal), interrupted Stop/Resume; неизвестный owner → fail-closed, никакого `pkill`/`rm pid`.

4. Для отказов **физического Stop** проверить RU/EN уведомления в GUI и честное состояние; сообщения устаревшего Stop, чей producer исчез, адаптировать/удалить.

5. `restart` при RUNNING делает действительно полный graceful Stop→Start по original FD9 и P2/N/epoch retirement, затем terminal readiness + rollback на failure; при intentionally STOPPED не стартует. Ошибка второго Start не выдаёт success.

**GO:** безопасный операторский Stop и подтверждённая защита чужого состояния.

### S13. Подключить все runtime callers к той же паре

1. Следуя S02, заменить физические ветки в Strategies/Voice toolbar, OPNsense service configd, Common/Voice Apply + `backend/apply_runtime.sh`, Lab, `pkg-update prepare/finish`, setup/upstream Install Version, Boot/recovery, auto-restart, runtime-failure callback.
2. Context (Lab/pkg/Apply) сохраняет свои validation/rollback/receipts, но не выбирает собственный Common vs legacy и не держит второй physical process/IPFW writer. При inherited FD9 **нет nested lock/CLI reentry**.
3. `restart/reconfigure` — guarded Stop→Start под непрерывным FD9; confirmed user STOPPED не запускается из-за scheduler. Проверить все handler/CLI paths автоматически и фактически на GUI.
4. Лаборатория не должна требовать ordinary sealed manifest/непустую пользовательскую Strategy или прежний release для работы с исходно STOPPED. Job-owned temporary runtime остаётся отделённым от обычного Start; при наличии ordinary owner Lab использует ту же original FD9 безопасность.

5. При переводе всех callers на единый физический Start/Stop заменить **только** их старые GUI error reason/translation mappings. Сохранить поддерживаемые исторические Lab restore и protected package recovery receipts; не трогать независимые Voice/Input/Strategy/Lab messages.

6. **Путь Apply:** заменить старый `reconfigure` на decision engine `NO_CHANGE|RELOAD|RESTART|START|STOP|SAVE_ONLY|REFUSE`; все toolbar/Voice/Lab/pkg/Boot делегируют к тем же guarded physical transitions. Для list-only применять reload без дублирующей команды restart. Обычный `reload` на STOPPED возвращает NOT_RUNNING, не Auto-start. Проверить System Services/reconfigure compatibility.

**GO:** один physical dispatcher и одна политика, все пути из S02 трассируются. **NO-GO:** альтернативный direct exec/kill/IPFW script.

### S14. Apply/Restart/Boot/rollback end-to-end

1. Проверить RUNNING/STOPPED, idempotence/refusal, unchanged+edited Strategies и Voice Apply, Config/list ownership, TUN WAN и one-engine/IPFW state.
2. Failure inject at promotion, early engine exit, crash Stop/Boot, protected upgrade, Setup install rollback; проверить предыдущий terminal semantic state, no stranded broken journal.
3. Проверить native N/debug retirement, P1/CAS/ACK/Found protection, service state после каждого результата; original restoration error важнее промежуточного успешного UI.

4. Инъекции отказов при Stop→Start/restart, failed Start after Stop и rollback: сверить фактическую причину/стадию с RU/EN уведомлением именно о service transition, исключить ложный «Restart successful».

5. End-to-end native reload: изменить только активный checked HOSTLIST/IPSet при RUNNING, подтвердить точный old/new PID+birth/argv/supervisor+IPFW и реальное reread без SIGSTOP; SIGHUP только verified owner. На lazy reread вернуть REQUESTED, пока не подтверждено, а failure/injected crash — rollback или UNCERTAIN без fallback restart. Сравнить с forced full restart для structural/mixed change и no-op.

**GO:** original FD9 tests + equivalent native tests PASS; rc=0 недостаточно без physical witness.

## G3 — известные дефекты и OPNsense native qualification (S15–S18)

### S15. Lab #1224 — доказать и исправить Stage 90/99

1. Read-only изучить `job.iDvhRh`, stage20/90/99 telemetry и genuine owner snapshot; на disposable OPNsense воспроизвести до-Lab RUNNING и STOPPED.
2. Исследовать original `runtime_args_hash` при валидной schema3 rotation и 10s Stop timeout **как гипотезы**, только с фактическим stage/rc. Не менять таймауты/guards наугад.
3. Исправить исключительно доказанный маршрут через canonical S13; проверить RUNNING→RUNNING, STOPPED→STOPPED на success/timeout/failure/cancel/interrupted restore.
4. **G08 before first Start:** после S06 WAN-only Save и штатной установки upstream (но ни одного ordinary Start), user Strategy и YouTube Domains намеренно пусты, Enabled=OFF, нет active ordinary manifest. Запустить настоящие `/api/zapret/strategy_lab/start/status/result` Standard RU и Extended EN. Подтвердить отдельные Jobs, Stage 90 `restoration.verified=true`, STOPPED→STOPPED, отсутствие обычного PID и owned IPFW 19000–19131, неизменность Config. Stage40 TARGET_ACCESSIBLE допустим и не доказывает DPI bypass.

**GO:** native semantic restoration + truthful Stage 90/99. **NO-GO:** manual Stop→Start считается Lab PASS.

### S16. Auto #1223 — native ingress до Found

1. Проверить реальный mode=auto/source-map, final profile N, unique native `--hostlist-auto` inbox, debug, IPFW counters, P2 minute, current owned generation.
2. Сопоставить прежний `--hostlist-auto-fail-threshold=1` с новыми клонами/default 3 как **неподтверждённую причину**; TIMEOUT/curl без native append не считается learning event.
3. Controlled native event → exact profile/inbox N → original P2/PSL/IDNA/Exclude → correct `youtube_found` / `user_found` → active managed → same PID hot reload → safe native cleanup; проверить User known priority, unknown shared, concurrent append, !/^, invalid owner, WAL/ACK.

**GO:** on disposable native **реальное подтверждённое** positive event и correct destination без Apply/restart. Owner ISP остаётся OPEN до S20.

### S17. Exact-head genuine native OPNsense gate

1. На одном одноразовом OPNsense 26.7/FreeBSD ABI подтвердить clean engine-absent status/GUI, compiler/ref tamper, Start/Stop/Status/Boot/Apply, Voice, WAN, Lab, Auto hot-reload/epoch. **Сначала G05→engine-second→G08:** WAN-only до upstream/manifest/Start; без WAN → `wan-required`, с WAN без движка → `engine-not-installed` и ноль Job; затем работа Standard/Extended при STOPPED и установленном engine.
2. Подтвердить защищённое STOPPED/RUNNING package-update, torn extraction, interrupted restore, no foreign IPFW cleanup, exactly one `dvtws2` и сохранность Config.
3. Собирать точные SHA/run IDs/log stage/rc. Failed attempt нельзя объявить PASS лишь потому, что rerun стал зелёным; исправлять причинный FAIL.

4. На disposable native OPNsense проверить RU/EN GUI отображение фактических отказов Start/Stop/Restart, в том числе вызванных через Apply/Lab/pkg; для опасных сценариев использовать контролируемые negative fixtures, а не устройство владельца.

5. На exact-head disposable OPNsense v1.0.7/FreeBSD проверить supported dvtws2 SIGHUP/list auto-reread (последующий пакет может быть необходим), hot mutable refs, semantic diff decisions, сохранность PID/IPFW и отсутствие другого writer. Проверить реальные stderr/rc причины Start/Stop/Restart/Reload, unsafe signal refusal, options parser и RU/EN lifecycle GUI. Старый upstream manpage сам по себе native PASS не даёт.

**GO:** affected native scenarios on exact code candidate PASS, critical restore FAIL eliminated.

### S18. Перед тестовой публикацией

1. Сверить ТЗ_6v5 V5-01…V5-14 на уровне source/CI/native; OPEN owner-live строки не подменять.
2. Обновить facts `PROJECT_STATE`/`ROADMAP`/`START_HERE` и issue statuses только по доказательствам. Проверить exact candidate revision, зависимости/ABI, official Mk package build.
3. Squash merge **product** PR только после safety checks/native gate; не объявлять stable или pfSense support.

4. V5-12 проверять **только** по old/new Start/Stop/Restart-related UI errors: нет orphan keys от удалённого lifecycle, все существенные действующие отказные ветки имеют RU/EN, сохранённые старые записи читаются; общий аудит иных переводов не требуется.

5. Отдельный gate **V5-13/V5-14**: перечень классифицированных полей и доказанные result codes, native списочный reload без Stop, structural restart, mixed restart только один раз, no-op, stop/off, incomplete refusal, no hidden auto fallback, action option allowlist, engine errors/локализованные lifecycle failures. Никакой тестовой .pkg до PASS.

**GO:** конкретный merged main SHA готов к **testing** .pkg, с сохранением owner-live OPEN.

## G4 — физическая testing доставка и owner acceptance (S19–S20)

### S19. Единственный опубликованный immutable testing пакет

1. Построить и опубликовать `os-zapret2-restyle-<version>.pkg` из **точного merged main source**, с реальными SHA-256, ABI, GitHub tag/direct asset URL и отдельной записью публикации по GH-034/035/060/061; **без SH** и без подмены Actions ZIP.
2. Подготовить native guarded updater для уже RUNNING `_117`; **не** предлагать unguarded `pkg add -f` поверх него. Для чистой установки проверить зависимости и отсутствие hidden engine install/Start.
3. Физическую установку на owner router выполнять только с его участием, console recovery и backup. Если нет owner receipt — статус NOT RUN, не PASS.

**GO:** опубликован реальный immutable `.pkg`, а затем отдельно подтверждён безопасный owner installation.

### S20. Владелец проверяет пользовательский результат

1. Зафиксировать before/after package version, engine/config/manifest/runtime, WAN/IPFW/Voice, Strategies + Voice toolbar Start/Restart/Stop/Status, unchanged/edited Apply, one `dvtws2`, сохранение ручных и Found списков. На **отдельной чистой тестовой установке** проверить WAN-only до upstream и Standard/Extended до первого ordinary Start, не очищая живые настройки владельца ради регрессии.
2. Strategy Lab: автоматическое восстановление RUNNING→RUNNING/STOPPED→STOPPED и failure handling; никаких команд manual restart вместо PASS.
3. Auto: после **подтверждённого** реального native YouTube/User события проверить соответствующие Found→managed, тот же PID/отсутствие фонового restart; если ISP native event не возник, указывать NOT VERIFIED, не выдавать TIMEOUT за доказательство.
4. Обычное удаление→повторная установка сохраняет настройки; отдельный deliberate purge проходит на тестовом устройстве. Проверить ошибки GUI и no-engine pathways.
5. Только после фактических свидетельств закрыть #1223/#1224/#1225/#1052; stable и pfSense — отдельные решения, не часть ТЗ_6v5 shipping.

6. Подтвердить RU/EN обратную связь **только по Start/Stop/Restart** и неудачным переходам службы в Apply/Lab; другие GUI переводы остаются вне V5-12.

7. Приёмка на owner OPNsense **после disposable native PASS**: при изменении только содержимого активного HOSTLIST/IPSet у «Применить» PID/IPFW не меняется; при изменении стратегии/порядка проверяется полноценный restart. Показать result `RELOAD_REQUESTED` отдельно от verified, а при ошибке — точную безопасную RU/EN причину. Не выполнять опасные failure injection на реальном роутере.

**DONE:** функциональность подтверждена на соответствующих source/native/owner уровнях, включая WAN-first/G05→G08/V5-11, lifecycle RU/EN V5-12, native reload V5-13 и пять команд/diagnostics V5-14; любые непроверенные строки остаются OPEN.

---

## Учёт контрольных гейтов (исходное состояние)

| Гейт | Этапы | На 22.11.2026 | Документ завершения |
| --- | --- | --- | --- |
| G0 | S00–S03 | S00 — документация в работе; S01–S03 не начаты | exact-head docs merge, audit, RED |
| G1 | S04–S09 | NOT RUN | empty-install/status/compiler parity + secure refs |
| G2 | S10–S14 | NOT RUN; #1228 только partial | five commands + safe Reload/Restart + FD9 rollback |
| G3 | S15–S18 | OPEN: Lab #1224, Auto #1223 | actual native restoration + Found |
| G4 | S19–S20 | NOT RUN для нового пакета | immutable published .pkg + owner evidence |

**Первое действие после завершения документационного PR — S01**, затем S02 и S03. Ни один этап не требует прямо сейчас менять работающий owner `_117`, повторять опасный Lab или вручную вмешиваться в PID, IPFW, native inbox или журнал.
