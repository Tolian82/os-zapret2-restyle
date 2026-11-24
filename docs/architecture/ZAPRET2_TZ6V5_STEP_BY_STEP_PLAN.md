# ТЗ_6v5 — пошаговый план внедрения единого запуска (S00–S20)

**Действующее ТЗ:** [ТЗ_6v5](TZ_6v5.md). **Детали:** [декларативный runtime](ZAPRET2_DECLARATIVE_RUNTIME_MANIFEST.md), [FD9 lifecycle audit](ZAPRET2_CANONICAL_SERVICE_LIFECYCLE.md). [Старый P0–P5 план](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) сохраняется для истории и прежних доказательств, но **не** является активной очередью.

**Точка старта, 22.11.2026:** `main 62b64e82` = source-only `0.6.5_121`, никакого `_121.pkg`; у владельца опубликованный/установленный `_117.pkg`, последняя ручная Stop→Start = RUNNING, два Strategies Apply PASS. [Lab #1224](https://github.com/Tolian82/os-zapret2-restyle/issues/1224) stage90/99 RESTORE_FAILED, [Auto #1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223) native YouTube no Found и [UI routes #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225) OPEN. [Draft PR #1228](https://github.com/Tolian82/os-zapret2-restyle/pull/1228) — частичная pre-manifest реализация Lab/pkg на старой базе; не merge, не публиковать. После документационного merge источник и следующий номер revision определить заново, а не заимствовать `_121` из старого PR.

**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ПЕРЕД S01–S20 — DEV-069:** канон Zapret2: [официальный `manual.en.md`](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md). **Запрещено тестировать, правда ли ведёт себя движок так, как в нём прямо написано.** Для HOSTLIST/IPSet документированы автоматическое перечитывание файлов при изменении без restart и SIGHUP-принудительное перечитывание при следующем пакете; мы **безусловно принимаем** эти свойства. Гейты этого плана проверяют **только наш код и внешние неописанные руководством механизмы**: diff/refs, запись, owner/PID, FD9, IPFW, адресную доставку сигнала, no restart, rollback/GUI и прочую платформенную интеграцию. Никаких engine reread/probe/benchmark tests, native confirmations documented engine features или сравнений с upstream исходниками. [Правило применения](ZAPRET2_UPSTREAM_MANUAL_CANON.md).

**Метод:** выполнять **S00 → S01 → … → S20**; для каждого шага: (1) действие, (2) RED→GREEN/нативное свидетельство, (3) переход только при GO. При FAIL устранять конкретную причину **в том же шаге**, сохраняя контекст stage/rc/SHA; не компенсировать missing evidence масштабным новым защитным механизмом. Source tests, disposable OPNsense и owner-live — **разные уровни приёмки**.

**Наследуемый обязательный регрессионный сценарий WAN-first / Prestart Lab:** [LC-06/11/12](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md), [G05](../verification/G05_WAN_ONLY_NATIVE.md), [G08](../verification/G08_PRESTART_LAB_NATIVE.md), [ТЗ_6v5 `6.1](TZ_6v5.md). **Сохранить** Save только WAN при Enabled=OFF, без upstream, обычного runtime/active manifest или непустой пользовательской стратегии. После **явной** установки upstream Standard/Extended Laboratory обязаны запускаться **без первого обычного Start**, проверять STOPPED→STOPPED и отсутствие остаточных Lab IPFW; старый native G08 PASS не переносится автоматически на новое поколение. Отсутствие WAN → `wan-required` раньше отсутствия двигателя; сохранённый WAN + отсутствующий двигатель → `engine-not-installed` без Job. G05→G08 — обязательный source/native RED→GREEN до и после переделки launcher.

**Точный объём RU/EN (V5-12):** проверять **только** ошибки прежнего физического `Start/Stop/Restart` и связанные с этими переходами сообщения через GUI/Apply/Voice/Lab/pkg/boot. Не проводить аудит всех переводов Voice/Strategies/Lab. Для старых lifecycle ошибок — KEEP/ADAPT/REMOVE по действительным producer и GUI consumer; новые реальные ошибки единого Start/Stop/Restart — RU/EN через прежние механизмы. [ТЗ_6v5 `7.1](TZ_6v5.md).

**Новое обязательное расширение ТЗ_6v5 (V5-13/V5-14):** публичный `zapret_service.sh start|stop|restart|reload|status`, а при нижнем «Применить» pure diff-planner выбирает `NO_CHANGE|RELOAD|RESTART|START|STOP|SAVE_ONLY|REFUSE` по **effective** sealed state. `reload` допускается **только** для проверенного перечитывания содержимого уже подключённых HOSTLIST/IPSet без остановки dvtws2/supervisor/IPFW. Новые argv/Voice/Target Mode/WAN/divert и mixed changes → один full restart. Не считать `SIGHUP`/rc0 фактом уже выполненного reread; lazy engine reload допускает `RELOAD_REQUESTED`. При ошибка reload нет скрытого restart. Дополнительные CLI опции только allowlisted; native stderr/exit/stage и RU/EN **lifecycle-only** mappings. [Нормативный контракт `5.1–5.4](TZ_6v5.md). Предыдущий WAN-first/G05→G08 остаётся обязательным.

**Новые CLI требования V5-15/V5-16:** `start --force`, `stop --force`, `restart --force` **только для явного оператора и точного подтверждённого собственного зависшего PID/epoch**; bounded graceful stop → re-attest PID+birth/exe/argv → targeted SIGKILL только при необходимости → verified STOPPED/retirement before any Start. Никогда не убивать foreign/reused/unverified PID, не удалять pidfile/journal наугад и не обходить FD9; при неудаче INCOMPLETE, без второго `dvtws2`. Глобальный/командный `--help` read-only, без FD9/состояния, показывает пять команд и опции. `--force` запрещён для reload/status и не добавляется автоматически из Apply/Lab/Boot/pkg. [ТЗ_6v5 §5.5–5.6](TZ_6v5.md).

**Нумерация IPFW — обязательная V5-17:** Normal/Strategies/Voice `19000–19099`, действующий Lab `19100–19131`, **future-only** comparative `19140–19200` (не устанавливать/не чистить), всё остальное, в том числе `19132–19139` — не наше. **Номер правила — единственный критерий диапазона**, никаких новых collision/foreign-rule-expression/ownership scans. Все операции (включая force/rollback/purge) ограничиваются **своим активным диапазоном**. Главный launcher `RULE_BASE=19000; RULE_MAX=19099`; preview/orchestrator/purge совпадают. Системное 65534 не добавлять и не удалять, даже при точном совпадении старого `allow`; OPNsense сама может использовать `65534 deny`, `65535` — системный default. При замене подтверждённого RUNNING read-only policy preflight (`default_to_accept=1` либо строго доказанный cold-IPFW) обязан завершиться **до** любого Stop/`prepared`; `0` → отказ до изменения runtime/правил. При подтверждённом STOPPED **без restart markers и pending pkg-update record** policy gate не требуется, потому что запуск не производится. Если старый updater уже остановил RUNNING и оставил marker/operation.json, incoming PRE_INSTALL обязан gate повторить, не разрешая опасный postinstall restart; старую остановку он отменить не может. Для первой миграции с предшественника без нового gate — отдельно подтвердить поведение native protected updater. [ТЗ_6v5 §5.7](TZ_6v5.md). Существующие original FD9/process/journal гарантии остаются.

**Неприкосновенные инварианты:** один original FD9/Config writer/долговечный журнал, один `dvtws2`, original `shared_apply_operation`, native P1/P2/FD и WAL/ACK, только собственный IPFW; без SIGSTOP/SIGCONT, observer/second daemon, несанкционированных остановок для Auto, PID-journal deletion или угаданного recovery. Подтверждённый manual/Found/managed и исправный операторский Stop важнее неподтверждённых Auto-строк.

## G0 — документы, исходники и воспроизводимый RED (S00–S03)

### S00. Закрепить новую редакцию требований и маршрут

1. Создать `TZ_6v5.md` и данный план, расставить активные ссылки из накопительного P0–P5 плана, `ROADMAP`, `START_HERE`, `PROJECT_STATE`, `architecture/README`.
2. Зафиксировать DEV-065/066/067, текущие `_117`/`_121`, открытые Lab/Auto, отсутствие новой сборки.
3. Создать документационный PR с очередной действительной ревизией по `GH-014/015`. Проверить exact-head docs/version/link checks; **никакого product-source или пакета**.

**GO:** merged docs+next revision, без изменений действующего runtime. **NO-GO:** ссылки ведут на старую ACTIVE очередь или указана вымышленная сборка.

### S01. Пересмотреть PR #1228 на фактическом новом main

**Решение S01 от 23.11.2026:** [полная 12-файловая KEEP / REWORK / DROP матрица](ZAPRET2_TZ6V5_S01_PR1228_DISPOSITION.md), исходный PR #1228 закрыт без merge, не cherry-pick; новый текущий base = merged `main v0.6.5_129` (`c7167b0c`), один следующий source branch `feat/tz6v5-s01-s02-lifecycle-audit`, кандидат `_130` **только документация + revision**. S02/S03 не выполнены, S04–S20 не начаты; никаких новых `.pkg` и никаких owner actions. Историческое описание S01 ниже сохраняет первоначальные критерии.

1. Прочитать diff, CI/native failures и полный список 12 файлов #1228, особенно partial `original_fd9_lifecycle_transition` (только Lab/pkg) и pre-manifest `_121`.
2. Сверить с новой схемой: сначала clean-install/Status/чистый compiler; удалить/переработать конфликтующие предположения вместо слепого переноса старой реализации.
3. Либо безопасно rebase/rework тот же Draft PR, либо закрыть superseded с объяснением и открыть **один** новый product PR. Номер product revision = актуальный `main+1`, без параллельных PR с одинаковой ревизией.

**GO:** один актуальный исходный branch и детальное решение keep/rework/drop каждой старой правки. **NO-GO:** merge старого #1228 или неподтверждённый base.

### S02. Read-only audit реального маршрута запуска

**Read-only source inventory checkpoint 23.11.2026 (candidate `_131`):** [полная pinned route/physical writers/FD9/Config/IPFW/PID/error RU/EN карта](ZAPRET2_TZ6V5_S02_ACTUAL_LIFECYCLE_ROUTE_AUDIT.md) на `main _130 0b001459`. Source-level audit — GO, **но не native PASS** и не физическая эквивалентность кнопок. Три старых GUI-иконки остаются неподтверждёнными без реального tooltip/handler; входы в карту занесены, S03 должна сделать RED на реальных producer/consumer и old generator parity. Продуктовый код/пакеты/owner не изменены.


1. Зафиксировать frontend→API→configd→script для Strategies/Voice Play/Restart/Stop, System Services, двух Apply, Boot/recovery, Lab, protected pkg prepare/finish, Auto Restart, runtime-failure callback и upstream «Установить версию».
2. Для каждого зафиксировать где FD9, выбор Common/Voice/legacy owner, реальные `exec/kill/IPFW/Config` side effects, rollback/terminal receipts. Скриншотные иконки без проверки tooltip/handler **не** считать доказательством.
3. Снять карту current `zapret.conf` inline, XML `Zapret.xml`, `registry/storage`, `target_mode`, `profile_pipeline`, `auto_detect_origin_map`, Voice producers, `shared_apply_operation` и exact active source map.

4. Для **старого Start/Stop/Restart** составить ограниченный реестр `emitter → stage/reason/rc → GUI caller/handler → RU/EN`, включая физические переходы при Apply, Voice, Lab restore, pkg/boot. Не инвентаризировать посторонние ошибки валидации и списков.

5. Инвентаризация каждого реального GUI/configd/Apply/Boot/Lab/pkg вызова старого `reconfigure` и `restart`: есть ли hidden Stop→Start, как подтверждается terminal result, что сохранено в original FD9. Отдельно перечислить list-only paths и текущие P1/CAS/ACK/managed hot-writers. Выделить только lifecycle RU/EN строки для миграции.

6. **Контракт `--force` и `--help`:** провести read-only трассу existing `launcher_stop`, `supervisor_stop`, PID-файлов child/monitor, original FD9/epoch, identity/birth и protected Common/Legacy status. Отдельно зафиксировать, какие владельцы PID реально аттестуются, кто умеет graceful/timeout, почему `kill -9` по pidfile/`pkill` недопустим. Inventory существующих CLI парсеров и места выдачи help; `--force` не должен входить в GUI Apply и фоновые callback.

7. Inventory **всех активных** IPFW range consumers: `zapret_service.sh` `RULE_BASE/RULE_MAX`, orchestrator fallback, strategy preview, Python voice adapter/transaction, Lab firewall, purge (source+package copy), on-device configd actions, tests. Rule-number-only policy без нового ownership/collision scanner; особое внимание пробелу 19132–19139 и резерву 19140–19200.

**GO:** полная таблица физических writers и их callers, включая обходные paths и наследование FD9. **NO-GO:** проверены только публичные CLI три команды.

### S03. Сформировать RED-фикстуры на старом фактическом генераторе

**FORMAL S03 GO (original-code RED only, 23.11.2026):** [seven-point sourced evidence ledger](ZAPRET2_TZ6V5_S03_RED_BASELINE_GO.md), merged legacy sources `_149 20dc89c9`, prospective docs-only `_150`. Genuine source/native old generator/10-case effective diff, G05→G08, PID/FD9/force & strict CLI RED, lifecycle RU/EN, numeric-only IPFW boundaries and independent Stage20/Stage90 actual Auto Lab failure evidence are qualified. **S03 is not a unified-lifecycle GREEN gate**; no `--force` or `reload` implemented, Stage90/Auto owner defects #1223/#1224 remain OPEN. **NEXT S04** neutral read-only model only; S05–S20 still blocked by their own gates and no public pkg. Documentation exact-head CI PENDING.


**S03e3d source candidate (`_142`, 23.11.2026):** [single-original-FD9 post-dispatch terminal receipt + true native PHP Stop/Restart refusal RU/EN](ZAPRET2_TZ6V5_S03E3D_ORIGINAL_FD9_TERMINAL_RECEIPT.md). Private configd `type:script_output` invokes existing Stop/Restart with internal flag (same FD9); verified `shared_apply_status_service` within lock gates fixed success receipt. PHP fails closed via `UserException` if missing, GUI Stop never treats HTTP 200 without `verified` as successful. Earlier S03e3c native [RED](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45143375706) must become actual installed Chromium RU/EN **GREEN refusal** on lock-BUSY in disposable no-engine guest, Config/IPFW/engine intact. **Native real HTTPS GREEN** ([#45147056314](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45147056314)): HTTP 500 for both Stop/Restart EN+RU, genuine OPNsense UserException and visible GUI Stop denial, Config/IPFW/engine/FD9 invariant, WAN-only Apply/F5/P3 regressions PASS. At original head 12 workflows ended PASS (two Auto native tests required rerun); next HEAD adds **read-only actual installed configd action registration** to rule out false GREEN from unknown commands; its exact-head CI PENDING. No positive RUNNING physical Stop/Restart attested; full S03 NO-GO, S04 forbidden.


**S03e3k original Stage20 duration from existing telemetry (`_149`, 23.11.2026):** [S03e3j read-only extension](ZAPRET2_TZ6V5_S03E3J_STAGE20_NATIVE_SAMPLING.md): original Python orchestrator already records `timing-telemetry.json` (`phase=stage_adapter`, `stage=20`, monotonic `duration_ms`). Existing status/events lack child Stop rc or timestamps, but **original stage duration exists**. Reuse existing native CI and run **one** genuine Auto/Lab Stop; read original root-owned telemetry, strictly verify stage/outcome and original service/epoch/IPFW. Do NOT add another persistent log, wrapper, Stop/Start or runtime writer. Distinguish full adapter duration from inner Stop; rc remains UNKNOWN. Native original successful adapter Stage20 measured `4313ms` [native #45196553041](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45196553041) on SHA `6ae67428` (Stage20 PASS, Stage90 false RESTORE_FAILED); failing Stage20 timing/rc still unknown. Consolidated exact-head CI PENDING; full S03 NO-GO, S04 blocked.

**S03e3j original Stage20 bounded native sampling (`_148`, 23.11.2026):** [one disposable original-FD9 OPNsense with up to three genuine Auto schema3 Standard Lab sessions](ZAPRET2_TZ6V5_S03E3J_STAGE20_NATIVE_SAMPLING.md). Stop immediately on first Lab Stage20 refusal; source-level pre/post semantic/PID/IPFW/Config/epoch and approximate HTTP-observed Stage20 window only. Original `strategy_lab_py/state.py` has no saved child exit code or timestamps; never infer rc70/timeout10s from generic FAIL. Previous original Stage90 inbox-only false RESTORE_FAILED [exact native #45188864664](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45188864664) accepted as strict expected RED, NOT product fixed. **S03e3j first exact-head native real Stage20 RED observed** [native #45192186695](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45192186695) on `f6f51915`: first genuine Auto Lab Stage20 FAIL, physical RUNNING/epoch/Config/IPFW verified, no next Lab executed; estimated HTTP-observed window 0–5s is not original duration or original Stop rc. Final consolidated SHA CI PENDING; #1224/#1223 OPEN, S03 NO-GO/S04 prohibited.

**S03e3i active Auto schema3 learning + genuine RUNNING Lab (`_147`, 23.11.2026):** [separate actual OPNsense test](ZAPRET2_TZ6V5_S03E3I_AUTO_LEARNING_RUNNING_LAB.md): operator-equivalent HTTPS Strategies Apply chooses Auto; prove original FD9 native schema3 and per-N learning inbox, one dvtws2, original epoch; run un-cancelled Standard Lab, verify Stage90/99, RUNNING restoration, semantic Config/normal+foreign IPFW, new owner/epoch retirement if changed. No invented learning or forced repair. `_146` actual normal Common Lab PASS [#45178569477](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45178569477); **S03 native expected-RED verified** [#45186404328](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45186404328) (Lab Stage90/99 RESTORE_FAILED, only original native-map-bound per-generation inbox argv changed, one RUNNING engine and safe epoch/Config/IPFW); consolidated exact SHA CI PENDING, owner #1224 remains OPEN, Auto #1223 remains OPEN, S03 NO-GO/S04 blocked.

**S03e3h actual RUNNING Lab stage90/99 restoration baseline (`_146`, 23.11.2026):** [genuine installed OPNsense Common RUNNING→Strategy Lab Standard→RUNNING](ZAPRET2_TZ6V5_S03E3H_RUNNING_LAB_RESTORE.md), exact original FD9, real dvtws2/supervisor/one owner, terminal stage90/99, Config+IPFW before/after. This fills a distinct S03 RED evidence gap from STOPPED-only G08; a true Lab stage90 FAIL must remain FAIL with bounded read-only diagnostic, never synthetic GREEN or operator trial. **Exact-head native PENDING**; owner #1224 OPEN, Auto #1223 OPEN; full S03 NO-GO, S04 blocked. No product code change or released package.

**S03e3g Auto-native Stop fail-closed test candidate (`_145`, 23.11.2026):** [exact native source-only refusal/Boot boundary](ZAPRET2_TZ6V5_S03E3G_AUTO_STOP_NO_BOOT.md). Original published _107 schema2→schema3 test no longer invokes Boot after Stop rc!=0 or missing independently verified retirement; it emits only literal source-defined safe retirement guard categories and read-only post-Stop Status. Linux fast self-test validates no Boot on three refusal cases and one Boot on fully verified success. Common [G07 PASS #45160845481](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45160845481) and Legacy [PASS #45171380056](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45171380056) merged in _143/_144. Auto root cause #1223 remains OPEN; exact-head native CI PENDING; full S03 NO-GO, S04 prohibited.

**S03e3f native Legacy positive candidate (`_144`, 23.11.2026):** [true installed no-Common-journal Legacy positive HTTP Start/Restart/Stop + real engine/PID/IPFW](ZAPRET2_TZ6V5_S03E3F_LEGACY_POSITIVE_HTTP.md) uses separate disposable OPNsense guest and original FD9. The `v0.6.5_143` Common positive G07 on `c43e9173` [PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45160845481), [PR #1255](https://github.com/Tolian82/os-zapret2-restyle/pull/1255) merged to `main af4999a4`. **Legacy exact-head native CI PENDING**; no public pkg, no owner actions; S03 overall NO-GO, S04–S20 forbidden.

**S03e3e test-only candidate (`_143`, 23.11.2026):** existing disposable OPNsense G07 real installed Common engine lifecycle now requires *unmocked* PHP Stop/Restart HTTP `verified=true,action,state` receipts alongside the already-existing native engine PID/generation/IPFW/Status witnesses. Fast negative receipt-shape fixture rejects fake `response=OK` and mismatched actions. **Native exact-head result PENDING**; this does not qualify the separate Legacy branch or full S03. [Evidence contract](ZAPRET2_TZ6V5_S03E3E_COMMON_POSITIVE_TERMINAL_RECEIPT.md).

**S03e3c candidate (`_141`, 23.11.2026):** [actual PHP Stop/Restart HTTP + Strategies GUI RED on held original FD9](ZAPRET2_TZ6V5_S03E3C_NATIVE_PHP_STOP_RESTART_HTTP_RED.md). On disposable OPNsense cold installed guest, EN/RU authenticated Chromium executes real Stop click and separate HTTP Restart; neither POST is intercepted, read-only runtime only stubbed to expose the button. Native test-owned FD9 proves BUSY, drains configd children and demands unchanged Config/IPFW/engine. Expected old API returns `response` under HTTP 200 and old GUI does not show Stop error; no lifecycle code change or owner hardware operation. **Initial real native RED PASS** ([run #45142099971](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45142099971)): EN/RU HTTP 200 for both actions despite genuine FD9 BUSY, response OTHER_REDACTED, old GUI Stop failure absent, Config/IPFW/engine identical. Clean [PR #1253](https://github.com/Tolian82/os-zapret2-restyle/pull/1253) exact-head recheck PENDING; full S03 NO-GO, S04 forbidden.


**S03e3b native source candidate (`_140`, 23.11.2026):** [real original configd Stop/Restart denied by verified original FD9 BUSY](ZAPRET2_TZ6V5_S03E3B_CONFIGD_LOCKED_STOP_RESTART_RED.md) in disposable cold OPNsense: genuine `zapret_service.sh stop|restart` rc75, configd response categorized without raw text, no Config/IPFW/engine change and no pending native child. Existing inherited API returns `response` without service terminal proof; Strategies `.done` ignores that data. This is RED evidence only, not repaired Stop/Restart RU/EN consumer, no physical transitions. **Native RED PASS** ([#45138033995](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45138033995)): original shell Stop/Restart both rc75 under verified original FD9; real configctl returns process rc0 + OTHER_REDACTED nonempty stdout for both, so CLI rc0 is not service transition evidence. Config/IPFW/engine unchanged, old WAN-only/F5 and P3 RU/EN preserved. Revised exact-head CI required; full S03 NO-GO; S04 forbidden.


**S03e3a native WAN-error candidate (`_139`, 23.11.2026):** [реальный до-dispatch `wan-required` UserException → HTTPS → Chromium RU/EN](ZAPRET2_TZ6V5_S03E3_NATIVE_WAN_START_USEREXCEPTION_RUEN.md). На disposable OPNsense только до первого WAN Apply: native read-only preflight обязан подтвердить отсутствие WAN/engine; real Start POST не мокируется; test-only read-only runtime display допускается для включения кнопки; проверяется отсутствие Config/IPFW/engine изменений после отказа. Initial installed Chromium [RED #45133765736](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45133765736): true guest `wan-required` PASS, OPNsense `UserException` has `errorMessage`/`errorTitle` instead of `message`; fixed bounded `general.volt` consumer RU/EN. Исправленный реальный native Chromium [GREEN #45134904028](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45134904028) на точном `65125101`: и EN, и RU проходят настоящий PHP `UserException` при unmocked Start HTTP, `wan-required` до physical dispatch, Config/IPFW/engine неизменны, WAN-only Apply/F5 и P3 RU/EN сохранены. Для дальнейшего docs-only HEAD требуется повторный exact-head CI. **S03e3a native producer→GUI Start/WAN GO при подтверждённом общем CI**, это не Stop/Restart и не полное V5-12/V5-14; S03 overall NO-GO, S04 запрещён.

**S03e2 source correction candidate (`_138`, 23.11.2026):** [owner-approved Voice removal and Strategies lifecycle RU/EN action-specific fallback](ZAPRET2_TZ6V5_S03E2_VOICE_CONTROL_RETIRED_GUI_LOCALE.md). The independent Voice `#voiceServiceControl` Start/Stop button and handler are removed, NOT given a new error-display branch; passive runtime/Voice IPFW and shared Apply remain. Real Strategies JS handler is executed under inert RU/EN Node fixtures. The existing installed OPNsense Chromium RU/EN workflow additionally checks the removed Voice button and exercises Strategies GUI Start/Stop failures with **intercepted HTTP 503** only (never native Start/Stop). Node source fixtures are not browser clicks; intercepted browser HTTP is not native producer evidence. S03e2 source-correction **GO** after exact-head **8/8 workflows PASS** at `7331c0c9` ([native P2e](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45131323702), [installed Chromium EN/RU with intercepted HTTP](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45131323617), [full CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45131323620)); docs-only follow-up SHA must be rechecked before merge. Full S03 stays **NO-GO** pending native lifecycle error producer, new CLI/force/reload and remaining Lab/Auto evidence; S04 must not start. CI-only temporary `.pkg` is not a public/operator testing release.

**S03e1 merged (`_137`, 23.11.2026):** [PR #1246](https://github.com/Tolian82/os-zapret2-restyle/pull/1246) / `main 9127b9f3`, disposable native CI [#45115119169](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45115119169) PASS for original CLI expected RED. Historical old Voice `.always` route and wrong Strategies Stop fallback are retained in pinned S03e1 evidence. Neither source proof nor S03e2's inert JS fixture is a real RU/EN GUI-click PASS.

**S03e1 candidate (_137, 23.11.2026):** [real original public CLI/strict-option/Status expected RED on disposable OPNsense and separate PHP/Volt/configd lifecycle RU/EN source route](ZAPRET2_TZ6V5_S03E_PUBLIC_CLI_LOCALE_RED_NATIVE.md). Every mutation-capable option checked only while original FD9 is verified BUSY; no engine/Config/IPFW mutation. CI PENDING; neither new parser nor GUI locale native PASS; full S03 NO-GO.

**S03d candidate (_136, 23.11.2026):** [genuine disposable FreeBSD old `common_process_matches/launcher_stop` controlled PID/FD9 and CLI expected RED](ZAPRET2_TZ6V5_S03D_PID_FD9_FORCE_RED_NATIVE.md); one test-owned sleep only, private FD9, no installed engine. Reproduces silent PID cleanup, exe-only matching without sealed owner/birth/epoch, missing help/parser and actual FD9 BUSY refusal. CI pending. This is NOT operator `--force` support or proven force KILL safety; full S03 still NO-GO.

**S03c2 candidate (`_135`, 23.11.2026):** [genuine native G05 WAN-only saved Config/HTTPS → G03 real configd upstream installed, no ordinary Start → G08 Standard/Extended actual Job Stage90+99 STOPPED restoration](ZAPRET2_TZ6V5_S03C2_AUTH_NATIVE_PRESTART.md). Corrected stale G08 test composition: G03.main's later five-list test starts/rests engine; G08 must use G03's stock configd dispatch/poll only. Exact-head disposable CI PENDING. Temporary .pkg built only inside isolated VM, no testing release before S19 and no owner contact. Historical G08 `_26` PASS not reused as current native acceptance. S03 still NO-GO for force/PID/FD9/Help/Reload/lifecycle RU/EN and #1224/#1223.

**S03c1 candidate (`_134`, 23.11.2026):** [genuine unchanged Lab launcher, isolated FreeBSD lockf/jq, injected WAN boundary, seven typed/no-Job/Config/IPFW refusal cases](ZAPRET2_TZ6V5_S03C_PRESTART_LAB_REFUSAL_NATIVE.md) in existing disposable P2e CI. S03a (6 expected RED) and S03b (10 actual old generator effective diffs) have exact-head CI PASS and are merged `_132/_133`. **S03c1 not a full real native G05/G03/G08 or physical Lab restoration, and CI is pending.** Do not promote to S04 until full S03 including actual Config/WAN Save, PID/force, CLI, RU/EN lifecycle and Lab restoration is proven.

**S03b actual source diff candidate (`_133`, 23.11.2026):** [10-case normalised real generator `dvtws.args` + managed file SHA + source-map comparison](ZAPRET2_TZ6V5_S03_EFFECTIVE_DIFF_BASELINE.md) added to disposable OPNsense P2e; CI pending. In particular same argv for Auto→List requires semantic RESTART; same argv for changed YouTube/User/Exclude is **only candidate**, not confirmed reload. S03 still NO-GO pending G05→G08/FD9/PID/force/locale/native routes; S04 cannot start yet.


**S03a source candidate (23.11.2026, `_132`):** [реальный S03 old-generator matrix/CLI/learning/no-manifest native-disposable Status RED](ZAPRET2_TZ6V5_S03_ORIGINAL_GENERATOR_RED.md), using existing P2e production orchestrator and isolated FreeBSD workflow. **CI witness pending, S03 incomplete/NO-GO**: пункты G05→G08/diff/force/locale/native Lab и другие матрицы не закрыты; не переходить к S04 из-за одного RED набора.

1. Сохранить deterministic old baseline: итоговые `dvtws.args`, actual native profile order/source-map/IPFW/Voice для `all/list/auto`, explicit selectors, User vs YouTube first-match, empty/nonempty/large/invalid lists.
2. Написать RED на no-engine, no-Config, no-manifest, иностранные PID/IPFW, stale map, invalid refs и Stage/rc diagnostics; на status no side effects и one physical transition dispatcher. Добавить регрессию G05/G08: WAN-only Save при пустых user Strategy/hostlists и Enabled=OFF без upstream/manifest; WAN-first error precedence до Lab Job; реальный Standard/Extended Lab после установки engine до обычного Start.
3. Проверить, что тесты действительно вызывают производственный генератор/templates и **падают на доказуемом дефекте**; Lab stage90 RED и Auto learning RED добавлять по объективной физической трассе, не фальсифицируя событие.

4. RED-тесты старых переводов Start/Stop/Restart: показать реальные sources, доходимость до обоих языков; отдельно фикстуры исчезнувших source stages, чтобы stale lifecycle errors не пережили refactor. Сохранённые Lab/operation receipts не считать «мёртвыми» без проверки.

5. RED fixture **на наши действия**: old/next effective diff NO_CHANGE/list-only/refs/profile order/DPI/Voice/Target Mode/WAN/divert/mixed/foreign; `reload` сохраняет собственный PID/owned IPFW, доставляет сигнал только verified PID, правильно возвращает REQUESTED (когда подтверждена только доставка), failure не запускает hidden restart; CLI option rc64 и RU/EN lifecycle GUI. **Не писать тесты, исследующие, перечитывает ли движок списки и что делает SIGHUP:** это установлено каноном.

6. **RED CLI:** `start|stop|restart --force` только по явному admin, чужой/reused/stale PID/FD9 BUSY/PREPARED → refusal/no kill; owned hung TERM timeout→re-attest exact PID+birth→targeted SIGKILL→verified shutdown; stuck unkillable→INCOMPLETE/no replacement Start; healthy RUNNING `start --force` не убивает; STOPPED `restart --force` не стартует. `--help` global и per-command rc0 без FD9/IO, пять команд/опции; invalid `reload --force`, `status --force`, duplicate options и unknown rc64. Нет тестов поведения движка, указанного в upstream manual.

7. RED source/fixture на inclusive bounds 19000/19099 и 19100/19131, отвергание 19132/19139 и всех вне диапазонов, отсутствие touch 19140–19200 в текущем runtime, отсутствие `ipfw add 65534` от плагина и корректную числовую фильтрацию purge. Не создавать новые tests на поиск владельца/сигнатуры чужого IPFW-правила.

**GO:** baseline и воспроизводимый RED доступны CI. **NO-GO:** unit mocks или grep объявлены native доказательством.

## G1 — безопасная пустая система, статус и чистая конфигурация (S04–S09)

### S04. Независимый inventory компонентов

**FULL S04 GO (23.11.2026):** [formal physical five-case native acceptance and no-write evidence](ZAPRET2_TZ6V5_S04_NATIVE_INVENTORY_GO.md). Actual installed OPNsense reader, real fresh/G03/Config/RUNNING/foreign IPFW, source-byte-identity pre-install adapter exception, exact two native SUCCESS [#45215394069](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215394069) and five exact-head PR workflow gates PASS on `_153 / 7f4c6a4f`, merged `main 6a71e10e`. Pure S04 classifier and native adapter do not authorize lifecycle; no CLI `status --json` yet. **S05 NEXT; not yet implemented.** Historic candidate paragraphs below retain their original pending language intentionally.

**S04c candidate (`_153`, 23.11.2026):** [two-guest native real five-case no-write gate](ZAPRET2_TZ6V5_S04C_NATIVE_FIVE_STATE_MATRIX.md). No S04 GO until original installed reader and true physical Config/epoch/PID/IPFW/file-tree invariants pass on both exact-head disposable OPNsense guests. S05 blocked.

**S04b candidate (`_152`, 23.11.2026):** [OPNsense read-only component adapter](ZAPRET2_TZ6V5_S04B_OPNSENSE_READONLY_COMPONENT_ADAPTER.md) uses installed pkg, fixed binary/XML and existing original Common seal/manifest/runtime inspector. Source-only bounded tests; still requires five physical native no-write witnesses for full S04 GO. S05 remains blocked.

**S04a partial source implementation (`_151`, 23.11.2026):** [neutral five-axis component classifier and source-level GREEN matrix](ZAPRET2_TZ6V5_S04A_NEUTRAL_COMPONENT_MODEL.md). Pure typed facts from future platform adapter only, no owner attestation, no permission to Start/Stop, no IO/FD9; source CI pending. **This is NOT an installed/native S04 GO**: actual read-only component probes, 5 physical scenarios and no-write native evidence remain mandatory before S05.


1. Read-only различать package plugin (вне CLI, если не установлен), binary upstream Zapret2 valid/absent, saved Config initialized/absent/invalid, active sealed manifest valid/missing/stale, runtime RUNNING/STOPPED/INCOMPLETE/FOREIGN.
2. Протестировать матрицу «нет ни одного компонента», «есть plugin без engine», «есть engine без Config», «есть owner с повреждённым editable Config» и «foreign owner».
3. Отсутствующий manifest/config не разрешает новый Start или destructive Stop чужого процесса.

**GO:** достоверная component matrix, ноль побочных записей.

### S05. Read-only status и диагностический конверт

**S05d1 candidate (`_166`, 24.11.2026):** accepted [S05c3b #1281](https://github.com/Tolian82/os-zapret2-restyle/pull/1281) `main _165 4d75e6c32367` and postmerge CI/Chromium PASS. V5-12 ADAPT only the existing setup PHP pre-dispatch release-list refusal ignored by the GUI Install failure callback. Exact fixed safe UserException → explicit RU/EN reason; retain review lock and generic fallback. Existing real PHP/JS source tests, normal affected CI/native gates. No setup/cache/FD9/Config/journal changes, no new VM matrix, and no inference of asynchronous worker reason from rc69. Full S05 NO-GO.

**S05c3b current `_165` (24.11.2026):** accepted [S05c3a #1280](https://github.com/Tolian82/os-zapret2-restyle/pull/1280) `main _164 0887f1ce` genuinely produced original Legacy `configctl template reload` failure `stage 1/13/config/failed` with HTTP generic refusal and no Config/IPFW/engine mutation. In existing `refresh_generated_configuration`, emit fixed private `Start` refusal only after genuine failed reload + **successful original stage13 write** within inherited original FD9. Existing `start_verified errors:no`, PHP exact bounded UserException and Strategies Start RU/EN allowlist deliver safe reason. No new journal/writer/old CLI or general translations. Same native S03e3f test now demands real HTTP fixed error + original stage13, unchanged Config/IPFW/engine, restored package template and later Legacy positive Start/Restart/Stop. Source-only negative matrix + exact-head affected CI/native gates PENDING, full S05 NO-GO.

**S05c3a candidate (`_164`, 24.11.2026):** after [accepted S05c2c #1279](https://github.com/Tolian82/os-zapret2-restyle/pull/1279) `main f2c651dfd36b`, prove real `configctl template reload OPNsense/Zapret` failure on existing native S03e3f Legacy VM: temporarily invalid package-owned guest template, then genuine original FD9 authenticated Start HTTP reject, original `stage 1/13/config/failed`, unchanged Config/IPFW/engine, exact template restore and later genuine Legacy success. No production patch or separate VM. Native evidence PENDING, diagnostics code only after actual producer; S05 full NO-GO.

**S05c2b source candidate (`_162`, 24.11.2026):** the inherited PHP Start returns configd *transport*, not terminal RUNNING; original Common/Recovery Start has early returns bypassing a tail-only receipt. Add PRIVATE start_verified on the SAME FD9, exact native RUNNING receipt across Common/Recovery/Legacy, strict PHP+GUI Start success, existing WAN-first. Genuine G07 Common and saved-WAN original FD9 BUSY negative, S03e3f Legacy installed positive and Chromium RU/EN plus exact-head CI mandatory. Full S05 NO-GO.

**S05c2a accepted (`_161`, 24.11.2026):** [PR #1277](https://github.com/Tolian82/os-zapret2-restyle/pull/1277) merged `main aee02fc81` after 17/17 exact-head PASS incl. genuine installed EN/RU original-FD9_BUSY Stop/Restart unmocked HTTP and no Config/IPFW/engine changes; two private actions `errors:no` and PHP strict parser do not change public rc. Main-push CI/release PASS, independent main Chromium CANCELLED (not PASS). Remaining lifecycle causes unqualified.

**S05c1 source candidate (`_160`, 23.11.2026):** after [merged S05b2b2 #1275](https://github.com/Tolian82/os-zapret2-restyle/pull/1275) and main-push CI/Chromium PASS, physically test *plain* original `status` with actual FD9 in clean plugin-only, engine-no-config, RUNNING, BUSY and FOREIGN states; snapshot Config/pkg/journal/PID/IPFW/process before and after, compare old rc/stdout. Current shell `9>` opens with truncation, distinct from already read-only `status --json`. Genuine baseline RED demonstrated FD9-lockfile modification in cold+RUNNING on workflow #45264775710. Intermediate `9<>` native [#45265394738](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45265394738) hot RUNNING/BUSY/FOREIGN PASS, cold RED because it creates absent FD9. Candidate now switches existing FD9 plain Status to strictly noncreating `9<` using the SAME FreeBSD BSD flock; absent FD9 uses only the original native plain Status observer (Pythonless STOPPED-only exact rc/message) or fail-closed INCOMPLETE; no alternate lifecycle owner. The earlier pure-S04 fallback broke real Python-down P5c native #45266572120 and is explicitly rejected; P5c physical #45267339503 PASS with native Pythonless route. Historical S03e native fixture #45267339947 expected obsolete creation of private FD9 by plain Status; only that fixture is updated to no-create while preserving its real positive FD9 lock and BUSY Stop/Start/Restart checks. Mutators retain `9>`. Mandatory exact-head cold/hot revalidation and source-level negative checks still required. No complete no-write claim until physical PASS. S05 remains NO-GO.

**S05b2b2 candidate (`_159`, 23.11.2026):** after [merged S05b2b1 #1274](https://github.com/Tolian82/os-zapret2-restyle/pull/1274), real original launcher emits only fixed `no-live-pid` or `stability-unverified` first-failure cause. Original Apply keeps it across rollback and its existing FD9 `requires-review` writer records optional strict `ENGINE_START_UNVERIFIED` in the SAME schema-1 journal. Only independently S04-verified INCOMPLETE+stale and stable original journal may expose it via read-only Status. No native wait rc, no premature `ENGINE_EXIT_EARLY`, no raw stderr and no extra PID/IPFW owner. Source fixture + physical disposable early-start failure, old/new owner refusal and exact-head CI still required; **S05 full NO-GO**, S06+ blocked.

**S05b2b1 source candidate (v0.6.5_158, 23.11.2026):** S05b2a now merged [PR #1271](https://github.com/Tolian82/os-zapret2-restyle/pull/1271) after [genuine exact-head native PASS #45251208233](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45251208233); blocker #1272 resolved. The next bounded real launcher_start_once RED→GREEN removes two raw dvtws2.log stderr tails in early readiness failure paths while keeping fixed refusal reasons; it does not modify engine/Stop, original FD9, Config, IPFW, journal or physical status and does not invent a native exit code. Source S0 passed; exact-head CI PENDING. Authenticated early-process cause/rc, setup/pkg/Lab receipts, S05c GUI RU/EN and plain legacy Status FD9 no-write still OPEN, full S05 NO-GO; S06+ blocked, no published package.

**S05b2a candidate (`_157`, 23.11.2026):** [original supervisor post-ready exit receipt](ZAPRET2_TZ6V5_S05B2A_ORIGINAL_LATE_EXIT.md) uses the existing original FD9+SharedApplyOperation writer, fixed `ENGINE_EXIT_AFTER_READY` with strict original PID/owner/manifest/kernel and real STOPPED proof, no native rc claim; exact-head disposable native fault/negative stale callback/no-write + all existing regressions required. Early exit real rc, setup/Lab/pkg, GUI RU/EN and plain Status FD9 side effect remain for S05b2b/S05c; full S05 NO-GO.

**S05b1 candidate (`_156`, 23.11.2026):** [original SharedApply failure projection](ZAPRET2_TZ6V5_S05B1_ORIGINAL_APPLY_ERROR.md) is additive to S05a and uses only the original root-owned `restore-failed/requires-review` journal as a qualified producer. It never guesses engine rc, timestamp or active generation. Source tests + exact-head native Status no-write remain gates; broader S05b2 original causal engine/supervisor failures and S05c GUI/native errors remain open. Full S05 NO-GO.

**S05a candidate (`_155`, 23.11.2026):** [read-only JSON Status and compatibility gate](ZAPRET2_TZ6V5_S05A_READONLY_JSON_STATUS.md). Strict `status --json` is a pure projection of S04 native evidence; old plain `status` retained. Diagnostics without actual original producer remain explicitly null, never invented. Requires exact-head source CI plus disposable OPNsense no-write tests and truthful error producer/consumer work before complete S05 GO. S06+ blocked.

1. Реализовать `status --json` с прежним совместимым plain `status` и собственным верифицированным runtime/epoch/IPFW census; status **не** компилирует, не Apply, не стартует, не сохраняет.
2. Кодировать `timestamp/stage/code/operation_id/generation/exit_status/runtime_state/message/stderr_excerpt/log_ref`. Подключить реальные `dvtws2`, supervisor, setup, configd, IPFW, P2, Apply, Lab errors в существующее защищённое, ограниченное, ротируемое хранилище.
3. RED→GREEN для `ENGINE_NOT_INSTALLED`, `CONFIG_UNINITIALIZED`, `MANIFEST_UNAVAILABLE`, `MANIFEST_INVALID`, `ENGINE_EXIT_EARLY`, `WAN_UNAVAILABLE`, `IPFW_ATTACH_FAILED`, `LAB_RESTORE_FAILED`; ограничить/очистить stderr, секреты/домены/IP/args не раскрывать.

4. Сохранить уже существующие RU/EN сообщения о запуске/остановке/перезапуске и правдивом состоянии после ошибки; новый diagnostic code полезен GUI только если связан с действительным lifecycle failure. Не переделывать остальные сообщения.

5. Расширить diagnostic envelope `action,stage,code,exit_status,runtime_before/after,generation,verification,stderr_excerpt,log_ref` для пяти команд; native engine/supervisor early/delayed errors без raw sensitive args. `status --json` читает последнее событие, не пишет его. `reload --check` read-only, различает RELOAD_SAFE/RESTART_REQUIRED/NOT_RUNNING/REFUSE.

5. Диагностика force-эскалации: отличать FORCE_OWNER_UNVERIFIED, FORCE_TERMINATION_UNCONFIRMED, normal timeout, forced termination verified, rollback failed и original FD9 conflict; `status` показывает только реальные terminal state, журнал force_requested/action/operation_id без раскрытия full args. Глобальный/командный `--help` не вызывает Status/Config/engine/FD9/IO.

6. Read-only Status/GUI показывают только действующие выделенные IPFW-номера, не определяют «наше» по выражению, divert-порту или чужому namespace. Не расширять имеющиеся scope filters на будущий reserve.

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

6. Compiler/generator/preview должны использовать один active ordinary inclusive bound 19000–19099 и проверять только допустимые значения; разбиение ordinary/Lab/future остаётся явным, без объединения 19000–19200.

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

5. Native firewall candidate install/commit/rollback выполняет изменения только в активных 19000–19099 (ordinary) и 19100–19131 (Lab), **не** в future 19140–19200. Числовой фильтр достаточен для определения нашего диапазона; не создавать новый foreign-rule-identity control.

**GO:** immutable candidate preflight и crash recovery подтверждены; ни одна пользовательская data write не обойдена.

### S11. Единственный физический Start

1. В `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` создать ONE authoritative Start transition по authenticated active release/held FD9; не компилировать стратегии/парсить XML в нём.
2. Verify binary, saved owner, generation, current journal, WAN, IPFW and engine args/maps before starting ровно одного `dvtws2`/supervisor; attest terminal RUNNING.
3. Negative: no binary/manifest/Config, engine early exit, invalid WAN, foreign PID/IPFW, stale/mutated release, concurrent operation.

4. Для отказов **физического Start** проверить source/error stage/rc, существующее GUI уведомление в RU и EN; новый genuine Start error оформить в обеих локалях без висящего неиспользуемого ключа.

5. Реализовать общий результат пяти команд с кодом/стадией/exit и проверкой before/after. `restart` внутри dispatcher вызывает единственные physical Stop→Start; не вводить второй способ `exec`/`kill`. Системный `status` остаётся read-only; parse options строго action-specific.

6. `start --force`: при здоровом RUNNING не убивать/не дублировать; при подтверждённо зависшем прежнем своём owner выполнить ровно тот же единственный guarded stop primitive с bounded escalation, после verified STOPPED только обычный Start. Нет manifest/WAN/upstream/FD9 или owner не доказан — отказ; не превращать флаг в unrestricted recovery.

7. Launcher/получатели runtime передают точные `RULE_BASE=19000`, `RULE_MAX=19099`; не вводить скрытую копию старой границы `19010`. При Start не добавлять внешнее IPFW 65534: проверенная системная настройка `default_to_accept=1` либо честный отказ.

**GO:** exact Start state and errors; нет скрытой альтернативной ветки.

### S12. Единственный физический Stop

1. В том же файле реализовать ONE authoritative Stop verified previous owner; Stop не должен зависеть от возможности пересобрать теперь повреждённый редактируемый XML/new candidate.
2. Делегировать неизменённые P2/epoch/FD/N retirement и удаление **только подтверждённого** собственного IPFW, supervisor/engine cleanup, terminal STOPPED.
3. Native negative: late append, stopped/no owner, foreign owner, wrong epoch/lock, external IPFW missing (#1210 — отдельная диагностика, НЕ новый auto-heal), interrupted Stop/Resume; неизвестный owner → fail-closed, никакого `pkill`/`rm pid`.

4. Для отказов **физического Stop** проверить RU/EN уведомления в GUI и честное состояние; сообщения устаревшего Stop, чей producer исчез, адаптировать/удалить.

5. `restart` при RUNNING делает действительно полный graceful Stop→Start по original FD9 и P2/N/epoch retirement, затем terminal readiness + rollback на failure; при intentionally STOPPED не стартует. Ошибка второго Start не выдаёт success.

6. `stop --force` и stop-half `restart --force`: под original FD9 остановить свой monitor/respawn, штатная graceful Stop/TERM, bounded wait, затем re-attest точный PID+birth+exe/argv+epoch **непосредственно перед** адресным SIGKILL. Проверить death/no respawn/complete P2/retirement/IPFW. При unkillable/PID reuse/foreign/incomplete — fail-closed, никаких новых процессов или удаления журнала. Не тестировать силовое завершение на рабочем маршрутизаторе владельца.

7. Stop и `--force` не касаются ни одного правила за активными числовыми диапазонами, не делают глобальный `ipfw flush` и не используют future-reserved 19140–19200 как активную очистку. Проверить выживание посторонних 19132–19139.

**GO:** безопасный операторский Stop и подтверждённая защита чужого состояния.

### S13. Подключить все runtime callers к той же паре

1. Следуя S02, заменить физические ветки в Strategies/Voice toolbar, OPNsense service configd, Common/Voice Apply + `backend/apply_runtime.sh`, Lab, `pkg-update prepare/finish`, setup/upstream Install Version, Boot/recovery, auto-restart, runtime-failure callback.
2. Context (Lab/pkg/Apply) сохраняет свои validation/rollback/receipts, но не выбирает собственный Common vs legacy и не держит второй physical process/IPFW writer. При inherited FD9 **нет nested lock/CLI reentry**.
3. `restart/reconfigure` — guarded Stop→Start под непрерывным FD9; confirmed user STOPPED не запускается из-за scheduler. Проверить все handler/CLI paths автоматически и фактически на GUI.
4. Лаборатория не должна требовать ordinary sealed manifest/непустую пользовательскую Strategy или прежний release для работы с исходно STOPPED. Job-owned temporary runtime остаётся отделённым от обычного Start; при наличии ordinary owner Lab использует ту же original FD9 безопасность.

5. При переводе всех callers на единый физический Start/Stop заменить **только** их старые GUI error reason/translation mappings. Сохранить поддерживаемые исторические Lab restore и protected package recovery receipts; не трогать независимые Voice/Input/Strategy/Lab messages.

6. **Путь Apply:** заменить старый `reconfigure` на decision engine `NO_CHANGE|RELOAD|RESTART|START|STOP|SAVE_ONLY|REFUSE`; все toolbar/Voice/Lab/pkg/Boot делегируют к тем же guarded physical transitions. Для list-only применять reload без дублирующей команды restart. Обычный `reload` на STOPPED возвращает NOT_RUNNING, не Auto-start. Проверить System Services/reconfigure compatibility.

7. Дополнить strict CLI argument parser только `start|stop|restart --force` и `--help` global/per-action; `reload/status --force` отклонять до lock, GUI/Apply/Lab/Boot/pkg не проставляют force. Проверить один общий guarded process-kill path без второго dispatcher и корректный inheritance original FD9.

8. Перед подключением всех callers проверить, что Apply/Voice/Lab/Boot/pkg/purge используют **одинаковые** границы и не выходят из собственного active диапазона при rollback или interrupted transaction.

**GO:** один physical dispatcher и одна политика, все пути из S02 трассируются. **NO-GO:** альтернативный direct exec/kill/IPFW script.

### S14. Apply/Restart/Boot/rollback end-to-end

1. Проверить RUNNING/STOPPED, idempotence/refusal, unchanged+edited Strategies и Voice Apply, Config/list ownership, TUN WAN и one-engine/IPFW state.
2. Failure inject at promotion, early engine exit, crash Stop/Boot, protected upgrade, Setup install rollback; проверить предыдущий terminal semantic state, no stranded broken journal.
3. Проверить native N/debug retirement, P1/CAS/ACK/Found protection, service state после каждого результата; original restoration error важнее промежуточного успешного UI.

4. Инъекции отказов при Stop→Start/restart, failed Start after Stop и rollback: сверить фактическую причину/стадию с RU/EN уведомлением именно о service transition, исключить ложный «Restart successful».

5. End-to-end **интеграция плагина**, не тест Zapret2: заменить разрешённый active HOSTLIST/IPSet через existing writer, проверить неизменность собственного PID+birth/argv/supervisor+IPFW, целостность записанных файлов и доставку сигнала только authorized PID. `RELOAD_REQUESTED` означает выполненную доставку/запись, но не объявляет, что следующий пакет уже обработан. **Само автоматическое перечитывание и действие SIGHUP в движке не измерять и не доказывать.** При неудачном commit/signal — protected rollback либо UNCERTAIN без fallback restart; отдельная проверка нашего forced restart для structural/mixed и no-op.

6. End-to-end force path: обычный Stop без KILL; искусственно зависший **свой attested test process** → `stop --force` STOPPED, `restart --force` новый RUNNING ровно один, `start --force` только после устранения своего stale blocker; force-stop failure никогда не разрешает Start. Уникальные receipt/stage/exit, redacted stderr и ограниченное RU/EN lifecycle уведомление если показываем из GUI. Путь help не трогает Config/IPFW.

7. Native tests: Start/Stop/Restart/Reload/Apply и force с границами 19000,19099,19100,19131; произвольные другие значения, включая gap и 19140–19200, не изменены. При `default_to_accept != 1` fail-closed, никаких системных allow 65534.

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
2. Проверить **только параметры, которые наш генератор передаёт движку**, и правильность источника/фильтров/профиля по canonical `manual.en.md`; например, задан ли ожидаемый `--hostlist-auto-fail-threshold`, а не «действительно ли Zapret2 обнаруживает сбои по этому порогу». **Не испытывать** документированный upstream алгоритм Autohostlist failure detector, искусственно создавая блокировку, TIMEOUT или перехватывая трафик ради подтверждения его работы.
3. Использовать **зафиксированную ранее реальную запись или соответствующую документированному формату контролируемую fixture** как *готовый вход* для нашего P2. Проверять **только свою цепочку**: native inbox/profile N → source-map → P2/PSL/IDNA/Exclude → соответствующий `youtube_found`/`user_found` → сохранение managed → protected cleanup/WAL/ACK. Проверить порядок User, unknown shared, concurrent append, !/^ и invalid owner. Не проводить эксперимент для доказательства upstream Autohostlist detector или reread.

**GO:** на одноразовой OPNsense при заданном **достоверном событии-входе** доказано, что **плагин** доставляет его в нужный Found/managed, не перезапуская службу, с правильными source map/FD9/ACK. Сам upstream детектор и его критерии **не тестируются**. Фактическая owner ISP-проверка собственной конфигурации и атрибуции остаётся OPEN до S20.

### S17. Exact-head genuine native OPNsense gate

1. На одном одноразовом OPNsense 26.7/FreeBSD ABI подтвердить clean engine-absent status/GUI, compiler/ref tamper, Start/Stop/Status/Boot/Apply, Voice, WAN, Lab, Auto hot-reload/epoch. **Сначала G05→engine-second→G08:** WAN-only до upstream/manifest/Start; без WAN → `wan-required`, с WAN без движка → `engine-not-installed` и ноль Job; затем работа Standard/Extended при STOPPED и установленном engine.
2. Подтвердить защищённое STOPPED/RUNNING package-update, torn extraction, interrupted restore, no foreign IPFW cleanup, exactly one `dvtws2` и сохранность Config.
3. Собирать точные SHA/run IDs/log stage/rc. Failed attempt нельзя объявить PASS лишь потому, что rerun стал зелёным; исправлять причинный FAIL.

4. На disposable native OPNsense проверить RU/EN GUI отображение фактических отказов Start/Stop/Restart, в том числе вызванных через Apply/Lab/pkg; для опасных сценариев использовать контролируемые negative fixtures, а не устройство владельца.

5. На exact-head disposable OPNsense/FreeBSD **не проверять поведение движка, уже описанное каноном** (automatic HOSTLIST/IPSet reread, SIGHUP и next packet): это не критерий PASS/FAIL. Вместо этого проверить *свой* `reload` route и `status`: точные list ref/path, commit/CAS, verified destination PID, корректный системный вызов отправки сигнала, сохранение процесса/FD9/IPFW, semantic diff action, отказ для чужого owner, контролируемые ошибки собственного сервиса и RU/EN lifecycle GUI. Исходный [manual.en.md](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md) — **не hypothesis и не объект теста**, а нормативная аксиома.

6. На disposable FreeBSD/OPNsense (не на owner) positive/negative force tests: attested hung PID+birth and supervisor, pidfile stale/missing, PID reused/foreign, immutable owner changed while waiting, FD9 BUSY, sealed journal incomplete, process immune to SIGKILL, failed P2/IPFW retirement. Проверить отсутствие foreign kill/no duplicate engine и no-write `--help`. Не испытывать upstream documented capabilities.

7. Disposable OPNsense: только числовые диапазоны 19000–19099 и 19100–19131 для active cleanup; future comparative 19140–19200 не используется; любые чужие IPFW-номера не удаляются. Не делать дополнительный foreign-owner/collision inspector и не испытывать документированные свойства Zapret2 из канона.

**GO:** affected native scenarios on exact code candidate PASS, critical restore FAIL eliminated.

### S18. Перед тестовой публикацией

1. Сверить ТЗ_6v5 V5-01…V5-17 на уровне source/CI/native; OPEN owner-live строки не подменять.
2. Обновить facts `PROJECT_STATE`/`ROADMAP`/`START_HERE` и issue statuses только по доказательствам. Проверить exact candidate revision, зависимости/ABI, official Mk package build.
3. Squash merge **product** PR только после safety checks/native gate; не объявлять stable или pfSense support.

4. V5-12 проверять **только** по old/new Start/Stop/Restart-related UI errors: нет orphan keys от удалённого lifecycle, все существенные действующие отказные ветки имеют RU/EN, сохранённые старые записи читаются; общий аудит иных переводов не требуется.

5. Отдельный gate **V5-13/V5-14**: наше покрытие diff classifier и result codes, запись активного list и адресная доставка сигнала без Stop/PID/IPFW changes, structural/mixed guarded restart только один раз, no-op, OFF, incomplete refusal, no fallback, option allowlist и локализованные реальные lifecycle failures. **Не включать в PASS проверку работы механизма reread/SIGHUP Zapret2**, уже описанного `manual.en.md`. Никакой тестовой .pkg до PASS интеграции плагина.

6. **V5-15/16 release gate:** матрица force graceful→TERM→exact-owner SIGKILL, проверка отсутствия KILL при healthy RUNNING/normal Stop, no SIGKILL для foreign/reused/unverified, правильные `INCOMPLETE`/code при force failure, ни одного второго `dvtws2`, `--help` global/per command no FD9/mutation и parser invalid options rc64. Всё только по собственному коду плагина.

7. V5-17 gate: README, ТЗ, spec, launcher, orchestrator, preview, обе копии purge и source/native IPFW boundaries согласованы; вне диапазонов, 19132–19139 и future reserve никогда не затронуты; старого `RULE_MAX=19010` в активном коде нет, system 65534 не создаётся.

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
3. Auto: если при обычной эксплуатации уже существует квалифицированная native запись, проверить **только наш маршрут** YouTube/User source-map → Found→managed, тот же PID и отсутствие фонового restart; если события нет, использовать подтверждённую сохранённую fixture для плагинового теста и не требовать от владельца экспериментально вызывать upstream detector. Документированная upstream логика обнаружения не является объектом проверки, отсутствие внешнего события не опровергает канон.
4. Обычное удаление→повторная установка сохраняет настройки; отдельный deliberate purge проходит на тестовом устройстве. Проверить ошибки GUI и no-engine pathways.
5. Только после фактических свидетельств закрыть #1223/#1224/#1225/#1052; stable и pfSense — отдельные решения, не часть ТЗ_6v5 shipping.

6. Подтвердить RU/EN обратную связь **только по Start/Stop/Restart** и неудачным переходам службы в Apply/Lab; другие GUI переводы остаются вне V5-12.

7. Приёмка на owner OPNsense **после disposable native PASS нашей интеграции**: при изменении только содержимого активного HOSTLIST/IPSet «Применить» корректно сохраняет файл/направляет сигнал при необходимости и не меняет PID/IPFW; при изменении стратегии/порядка выбирает полноценный restart. Показать `RELOAD_REQUESTED` (плагин выполнил свой запрос) без необоснованного утверждения про уже обработанный пакет; ошибки — безопасный RU/EN code. **Не проверять** engine auto-reread/SIGHUP на устройстве и не выполнять опасные failure injection.

8. `--help`/формат CLI и обычные lifecycle действия можно показать владельцу без риска; **силовое завершение зависших PID испытывать только на disposable native**. На рабочей OPNsense `--force` применяется лишь сознательно оператором при реальной необходимости и после подтверждения владельца процесса. Не превращать отдельную команду в действие кнопки «Применить».

9. На устройстве владельца проверить нативную диагностику/состояние без принудительной порчи или удаления чужих IPFW-правил; доказательства очистки и границ собрать на disposable OPNsense. Реальный установленный пакет продолжает использовать диапазоны его опубликованной версии до отдельно утверждённого обновления.

**DONE:** функциональность подтверждена на соответствующих source/native/owner уровнях, включая WAN-first/G05→G08/V5-11, lifecycle RU/EN V5-12, native reload V5-13, пять команд/diagnostics V5-14 и безопасные force/help V5-15/16 и узкие диапазоны IPFW V5-17; любые непроверенные строки остаются OPEN.

---

## Учёт контрольных гейтов (исходное состояние)

| Гейт | Этапы | На 22.11.2026 | Документ завершения |
| --- | --- | --- | --- |
| G0 | S00–S03 | S00/S01/S02 merged; S03a actual-generator RED candidate `_132` wired to isolated P2e OPNsense (CI pending); whole S03 still NO-GO | [S02 map](ZAPRET2_TZ6V5_S02_ACTUAL_LIFECYCLE_ROUTE_AUDIT.md), [S03a RED](ZAPRET2_TZ6V5_S03_ORIGINAL_GENERATOR_RED.md); finish remaining S03 before S04 |
| G1 | S04–S09 | NOT RUN | empty-install/status/compiler parity + secure refs |
| G2 | S10–S14 | NOT RUN; #1228 только partial | five commands + safe Reload/Restart + FD9 rollback |
| G3 | S15–S18 | OPEN: Lab #1224, Auto #1223 | actual native restoration + Found |
| G4 | S19–S20 | NOT RUN для нового пакета | immutable published .pkg + owner evidence |

**Актуальная очередь после S02 source inventory checkpoint — S03 fail-first RED на настоящем генераторе, далее S04–S20.** Нет переноса старого #1228 и нет разрешения запускать S04 без доказательств S02/S03. Ни один этап не требует прямо сейчас менять работающий owner `_117`, повторять опасный Lab или вручную вмешиваться в PID, IPFW, native inbox или журнал.
