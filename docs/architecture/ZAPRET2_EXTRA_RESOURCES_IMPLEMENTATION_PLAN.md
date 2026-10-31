# План реализации дополнительных Lua/BLOB-ресурсов Zapret2

**Owner-approved 22 October 2026. Execution has started: catalog-side Stage 1 capability metadata and offline integrity validation are merged into [`Tolian82/zapret2-extra-resources`](https://github.com/Tolian82/zapret2-extra-resources/commit/ccdd8fae375e9d3fcb2592a803e10a10d52c49f2).** The [catalog integrity run](https://github.com/Tolian82/zapret2-extra-resources/actions/runs/39830826402) succeeded. This verifies two descriptor examples against source bytes; it does **not** implement the OPNsense installer, service restart, plugin GUI, or dynamic Strategy Lab execution. Stage 2 has begun with a source-only, read-only immutable-revision archive and collision preflight (`extra_resources_preflight.py`, action `zapret extra_resources_preflight`). It verifies catalog entries against actual downloaded bytes, refuses symlink/path and upstream/user-file collisions, and never writes runtime files. A separate testable transaction core now stages managed-file backups and staged payloads, writes a durable journal, applies filesystem replacements atomically, and supports fail-closed rollback and explicit RESTORE_FAILED; the source now has a privileged manual configd launcher, acquiring setup.lock before existing native FD9, using inherited Strategy Lab native stop/start callbacks and matching PID evidence. This remains an unverified integration until native FreeBSD/owner runs. Source now includes a whole-setup setup.lock wrapper with an internal non-recursive setup mode and the upstream preservation guard: verify managed bytes, reject target-tree collisions before checkout, snapshot only owned files, verify post-build and restore during rollback. Source v0.5.7_6 also rejects direct setup.sh install if managed extras exist, requiring the guarded transaction, and preserves interrupted upstream rollback evidence as RECOVERY_REQUIRED instead of deleting it. Source v0.5.7_9 adds the previously approved RU/EN button beneath the Settings-page Status block, backed by POST-only manual install/status API, strict Started/busy gate, finite polling, and installed source commit/Lua/BIN count. This still needs source CI and installed FreeBSD/owner acceptance; actual power-loss recovery across the upstream transaction and dynamic Strategy Lab candidate execution remain pending. In `v0.5.7_26` managed snapshot attestation no longer requires still-existing live resources after a partially mutated upstream checkout, while prepared-only cleanup retains a separate live-integrity check. Mutating-phase rollback still requires independently attested compiled binary snapshot / manifest and safe native lifecycle. Source v0.5.7_22 now saves an atomically synced upstream checkpoint of the original release/commit/service and binary backup before any mutation, and exposes strict read-only inspection under setup.lock. Explicit restore from an interrupted mutation is still NOT implemented and needs separate verification. No plugin package or full release has been delivered for this feature.

Source `v0.5.7_45` now additionally seals the exact old/target Git commits and target release after fetch, before resource pruning or Git checkout, in a synced target-identity sidecar under the original FD9. It uses immutable target SHA for checkout and verifies identity in recovery; this is source work awaiting CI and installed evidence, not authorization to reset a dirty partial checkout.
Нормативное ТЗ: [ZAPRET2_EXTRA_RESOURCES_GUI.md](ZAPRET2_EXTRA_RESOURCES_GUI.md).
Источник ресурсов: [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources).
Страница: **«Стратегия»**, RU **«Установить дополнительные ресурсы»**, EN **“Install Additional Resources”**. Ресурсы устанавливаются **только по нажатию кнопки** при запущенной службе, после каждой успешной операции обязательно **перезапустить Zapret2** и проверить его здоровье (даже при отсутствии новых файлов). OPNsense не перезагружается.

## Главный принцип — полностью динамический состав ресурсов

**Не создавать статический список имён дополнительных `.lua` и `.bin` ни в Python-коде лаборатории, ни в коде GUI, ни в установщике.** Состав каталогов меняется: файлы добавляются, обновляются и удаляются без изменения исходного кода плагина.

- **Источник истины о фактической доступности** — реальные читаемые файлы в `/usr/local/etc/zapret2/lua/*.lua` и `/usr/local/etc/zapret2/files/fake/*.bin`. При каждом **новом Job** существующий `ResourceInventory` создаёт новый снимок; сохранённые старые задания и их результат не переписываются. Никакая ссылка из каталога GitHub не подменяет отсутствие файла на OPNsense.
- **Формирование кандидатов — динамическое:** Python-планировщик строит допустимые расширения текущих нативных семейств из актуального `ResourceInventory` и **данных о возможностях**, не из жёстко прописанных имён `fake_tls_7`, `custom_funcs.lua` и т. п. Штатные golden-кандидаты сохраняются как стабильные регрессии, но не ограничивают новые ресурсы.
- **BIN:** определять пригодные семейства по достоверным признакам формата/содержимого (например, TLS ClientHello, QUIC Initial, STUN, generic UDP там, где уже поддерживается). Для неоднозначных payload использовать внешний декларативный дескриптор; не угадывать протокол исключительно по имени. Генерировать кандидатов только для совместимых протокола, транспорта и поддерживаемой нативной техники.
- **Lua:** различать функции DPI, общие зависимости, детекторы, специализированные служебные модули. Само присутствие файла **не** говорит, какие функции можно вызывать и с какими параметрами. Использовать небольшие проверяемые декларативные описания возможностей/зависимостей, поставляемые **как данные рядом с ресурсами**, а не hardcode в Python. Универсальный построитель применяет описание к обнаруженному файлу; незнакомая функция без безопасного описания остаётся в `ResourceInventory`, но не исполняется вслепую.
- Дескриптор/манифест **не является фиксированным разрешённым списком файлов**: с новым файлом и подходящим описанием он начинает участвовать без обновления плагина; при физическом удалении файла соответствующий кандидат исчезает из **новых** Job независимо от наличия записи в метаданных. Новые редакции/описания доставляются через тот же каталог ресурсов. Если требуется принципиально новая нативная функция, которой не поддерживает существующий универсальный построитель, зафиксировать её как `unsupported`, **не обещать** безопасного произвольного выполнения.
- `CandidateSpec` сохраняет точные зависимости и аргументы конкретного динамически созданного кандидата; используемый файл, описание и provenance должны быть воспроизводимы. В `Model C` инициализировать только необходимые Lua для выбранного ограниченного пакета кандидатов плюс обязательные базовые зависимости.
- **Не образовывать полное декартово произведение** ресурсов. Сохранить семантику Stage 50/60, конечный бюджет, адаптивные приоритеты, ограничения по протоколу, отмену и точное восстановление службы.

**Ключевая приёмка динамичности:** положить новый совместимый BIN → новый Job обнаружил его и породил допустимого кандидата; убрать BIN → в следующем Job кандидата нет; аналогично для нового Lua **с описанием вызова/зависимостей**. Во всех четырёх сценариях **без изменения/пересборки кода плагина**. Старый сохранённый Job не меняется. Для неподдерживаемого файла — запись причины исключения, а не ложная рекомендация.

## Exact-set reconciliation amendment — 23 October 2026

The owner superseded the previous blanket rule forbidding any change to
untracked Lua/BIN. The installed namespace must instead equal the local
upstream Git HEAD resource tree plus a pinned, checksum-verified extras
catalog. The manual installer saves all pre-existing untracked files,
removes orphans, replaces incoming-name collisions, validates the exact
result, and restarts via the existing native lifecycle; rollback restores
the former bytes and metadata. Upstream tracked files and saved strategies
are never silently modified. Uncertain upstream release switches require
old/target inventories and their own durable rollback before applying
automatic exact reconciliation. No engine reinstall is needed.

### Release-switch verification increment (v0.5.7_32)

New source verification checks both old and target upstream Git resource
trees and the managed extras inventory before/after checkout. Only
previously normalized, noncolliding changes are eligible. Automatic
orphan cleanup on an upstream switch remains blocked until all untracked
Lua/BIN can be durably snapshotted, attested, and restored after failure.

## Этап 1. Каталог и данные о возможностях

**Задача:** определить минимальный устойчивый контракт между каталогом, установщиком и динамической лабораторией.

1. Аудировать опубликованный набор; известный на 22.10.2026 снимок — **54 BIN и 19 Lua**, но число **не** является лимитом либо постоянным списком.
2. Устанавливать проверенную неизменяемую ревизию набора Git (commit/tag), сопоставлять пути и контрольные суммы, не принимать недостоверные/двойные файлы и обходы путей.
3. Разделить метаданные **целостности и происхождения** (`inventory/sources.json`) и минимальные **декларативные возможности для поиска**. Не придумывать отдельный язык программирования стратегии и не копировать штатную таблицу функций Zapret2.
4. Установить правила: классификация по содержимому для известных BIN; декларативные аргументы, экспортируемое действие, зависимости и протокол для Lua; при отсутствии достоверных данных — `unsupported` в новом Job, но файл всё равно виден.
5. Описать безопасный результат конфликта со штатным upstream (отказ до мутации) и неотслеживаемым Lua/BIN (резервная копия и замена в транзакции). Сохранить атрибуцию и NOTICE.

**Готово, когда:** есть проверяемый формат данных и образцы известных BIN/Lua; новые ресурсы могут быть добавлены в каталог с описанием без правки Python; старые стратегии и файлы не изменены.

## Этап 2. Транзакционный установщик и обязательный перезапуск

**Задача:** отдельная ручная операция, использующая действующий OPNsense configd и lifecycle, не новый сервис/второй Config writer.

1. Подготовить асинхронный backend с состояниями, конечным polling и логом, который отличает скачивание, проверку, установку, перезапуск, откат и ошибку восстановления.
2. Взаимоисключить установку со сменой upstream-релиза, Apply, стартом/остановкой и активной лабораторией; проверить порядок `setup.lock` и lifecycle FD9 **без повторного захвата блокировки и взаимной блокировки**.
3. До мутации проверить фиксированный source commit, список файлов, целостность, безопасность путей/ссылок, права и конфликты на диске. Штатные upstream-файлы не перезаписывать; неотслеживаемые Lua/BIN предварительно резервировать и заменять либо удалять по утверждённому 23.10.2026 правилу точного состава, с обязательным откатом.
4. Сохранить управляемые предыдущие файлы/метаданные и состояние службы, опубликовать новый набор атомарно в соответствующие каталоги и проверить итог.
5. **При любом успешном нажатии**, даже если содержимое не изменилось, выполнить настоящий перезапуск службы Zapret2 через её существующий native/common lifecycle, доказать замену процесса и нормальную работу. Только затем commit успешной установки.
6. При сбое вернуть управляемый прежний набор и рабочее состояние; если не удалось — явный `RESTORE_FAILED`, никогда ложный SUCCESS. Сохранить установленные ресурсы при последующей смене upstream-версии, но **не** запускать их загрузку автоматически.

**Готово, когда:** повторная установка идемпотентна для файлов, но всегда перезапускает запущенную службу; ошибка/обрыв/конфликт не повреждает установленную версию; обновление upstream сохраняет дополнения.

## Этап 3. GUI «Стратегия»

**Source correction in v0.5.7_20 (installed acceptance pending):** each click receives a fresh 128-bit operation identifier from the POST API, preserved through configd/launcher/worker into durable status. UI accepts completion only for that identifier; a fast job can finish without an observed daemon busy pulse. A previous terminal result cannot complete a new click.

**Задача:** добавить кнопку без нарушения существующей разметки и логики.

1. В `general.volt` разместить кнопку **во второй строке под блоком «Статус:»** слева. Не перемещать Start/Stop, список релизов и две разные кнопки Apply.
2. RU/EN: принятые названия, ход операции, итог Lua/BIN, ревизия источника, ошибка/restore, контекстная помощь. Сохранить F5/адаптивную раскладку.
3. Кнопка доступна только при полноценном `Started` и отсутствии конкурирующей операции; при `Stopped` объяснить необходимость штатного Start.
4. UI показывает **фактический** результат backend после health-check, а не успех AJAX-старта. Не инициировать Apply пользовательских стратегий.

**Готово, когда:** пользователю доступна однокнопочная операция с честным статусом; сервис и обе кнопки Apply продолжают работать как прежде.

## Этап 4. Динамическая генерация кандидатов Strategy Lab

**Задача:** сделать дополнения реальными кандидатами **без фиксированного перечня файлов**.

1. Оставить текущий `ResourceInventory` как механизм обнаружения; при необходимости дополнить его подтверждением содержимого и привязкой описаний, но **не** писать новый дублирующий сканер.
2. В существующий `search_graph.py` / planner встроить универсальную data-driven генерацию узлов из текущего snapshot и применимых capability-описаний. Текущий штатный нативный граф и golden-проверки остаются; дополнительный набор к нему *добавляется динамически*.
3. Выдавать каждому узлу семантические протокол/действие/параметры/зависимости и стабильную идентичность по фактическому ресурсу и ревизии. Неподходящий BIN, неподдерживаемый Lua и пропавший файл не становятся выполняемыми кандидатами.
4. В `CandidateSpec` и `stage60_model_c.py` не переписывать рабочую архитектуру: передавать зависимости выбранных кандидатов, сохранять ограниченные группы, readiness/attribution/IPFW/cleanup, бюджеты и отмену.
5. Отмечать для обнаруженных ресурсов `eligible`, `unsupported`, `missing`, `pruned` или `deferred` и причины. Не менять существующие Traffic Strategy, Voice, HOSTLIST/IPSET и сохранённые результаты Jobs.

**Готово, когда:** без обновления Python-кода добавление/удаление совместимых BIN и Lua(+description) меняет **новый** граф кандидатов; проверены хотя бы по одному исполняемому новому BIN и Lua. Старый набор остаётся доступен без новых ресурсов.

**Stage 4 source progress (`v0.5.7_18`, not installed proof):** reviewed TLS BIN and fake+split Lua descriptors now create bounded, native CandidateSpec/Stage-60 candidates via the existing per-job ResourceInventory; unsupported/missing/pruned are recorded and the golden graph is retained. Offline candidate-rendering tests are not proof of working DPI evasion or live native execution. Owner-installed stage-60 readiness/cancel/fallback and power-loss tests remain required.

## Этап 5. Проверка установленного пакета и подготовка выпуска

Провести **только узкие проверки этого функционала**: установка/обновление/без изменений, неработающий GitHub или некорректный hash, конфликт имени, откат после неисправного restart, Start/Stop после операции, обновление штатного Zapret2, GUI RU/EN/F5, динамическое появление/удаление BIN и Lua без правок Python, один новый исполняемый BIN и Lua в Job. Проверить отсутствие оставшихся PID/IPFW/lock, сохранение пользовательской конфигурации и адекватность причин skip.

**Готово, когда:** есть короткий отчёт «изменено / проверено / не подтверждено», один owner-live сценарий в установленной OPNsense и никаких регрессий текущей службы или лаборатории. Публикация релиза — **только по отдельному явному распоряжению владельца**.

## Правила выполнения

- Минимальные изменения в существующих компонентах, без нового отдельного GUI, новой архитектуры Apply, очередной лаборатории либо фонового автоматического обновления ресурсов.
- **Каждый этап — измеримый результат**, короткие целевые проверки и устранение блокирующего дефекта до перехода дальше. Не раздувать проект повторением закрытых тестов.
- Every new commit merged into `main` increments `PLUGIN_REVISION` exactly once, including documentation-only, governance, tests, and CI changes, under [DEV-032–DEV-033](../PROJECT_PRINCIPLES.md). This does not automatically create or publish an installable package or stable release. Do not initiate a stable release without the owner's authorization.
- Для каждого кандидата — нативная семантика zapret2, воспроизводимость и честное доказательство результата; наличие файла в каталоге не равно способности обойти DPI.


Source stage `v0.5.7_27` now seals saved compiled-binary SHA-256 file/dir inventory and installed-resource manifest identity in a synchronized sidecar before the schema-2 upstream checkpoint. Read-only attestation is required for prepared cleanup and immediate automatic rollback, but a separate controlled and owner-tested mutating-phase recovery executor is still pending.


Source `v0.5.7_28` implements explicitly invoked schema-2 mutating upstream recovery only for a fully STOPPED native owner under setup.lock→original FD9. It verifies saved compiled binary/resource evidence, Git checkout/tag, tracked working-tree cleanliness and foreign snapshot entries before mutation, and checks original service state after using native Start when applicable. Running/incomplete/foreign owners and untrusted evidence fail closed; installed OPNsense acceptance and old cold-IPFW package replacement remain open.

## Owner-approved completion plan — M0–M7 (24 October 2026)

**This completion plan supersedes the historical next-step proposal to implement experimental `_47` per-path Git-write provenance.** The existing `v0.5.7_46` source is the baseline, not an owner-installed acceptance. The five original feature stages remain normative; M0–M7 make their final acceptance finite. New, unapproved research is not a delivery gate; useful changes may be proposed with evidence and require owner approval to enlarge scope.

- **M0 — Requirements and completion contract:** reconcile requirements, plan, current handoff, and one acceptance board; no runtime mutation or package publication. A documentation-only merge into `main` still increments `PLUGIN_REVISION` under DEV-032–DEV-033. Gate: docs CI and main-integrity pass, no contradictory live-acceptance claims.
- **M1 — Testing-package qualification:** inspect immutable `0.5.7_46` candidate or the smallest later defect-fix revision; require current Project/Voice/FreeBSD15 build evidence. Publish one persistent `v0.5.7_N` testing package (not a stable release), verify tag, asset identity and SHA-256. Gate: exact installable package exists on GitHub.
- **M2 — Appliance baseline:** owner-assisted read-only status/inventory/transaction inspection, working hypervisor-console access and a recoverable VM snapshot or equivalent. Gate: known starting conditions and usable recovery access; stray untracked Lua/BIN do not automatically disqualify the baseline.
- **M3 — Normal install and GUI:** owner-live install/upgrade, Started-only manual extra-resource action, exact-set reconciliation of arbitrary orphan/colliding Lua/BIN, backed-up originals, actual Stop/Start and PID/health verification; repeat click, RU/EN, F5, two Apply buttons, retained strategies. Gate: original Stage 2/3 behavior passes on installed package.
- **M4 — Strategy Lab execution:** verify one real reviewed extra BIN and one reviewed Lua can produce and execute compatible bounded native Stage-60 candidates; adding/removing compatible described resources alters new Jobs without Python changes; no unwanted Lua, saved-Job mutation, or false bypass PASS. Gate: original Stage 4 accepted on installed package.
- **M5 — Failure and existing recovery:** targeted offline negative tests (network/hash/collision/Start/Stop/recovery), tracked/untracked upstream release-switch semantics, preservation of unrelated OPNsense state, and truthful fail-closed results. Gate: valid updates succeed; invalid/conflicting operations refuse safely or use the **existing** bounded transaction rollback/recovery when its original preconditions are met. **Owner decision 24 October 2026: no new separately selected console clean-plugin reinstall mechanism, associated tests or completion gate.** Do not add a universal automatic dirty Git recovery engine; no normal package-hook weakening. Full live destructive fault injection is not inferred from source CI.
- **M6 — Cold boot and regressions:** owner-live boot and postboot IPFW/ipdivert/native service health, Voice, GUI, saved normal-update settings, no PID/firewall/lock residue; use isolated fault simulations for destructive power-cut conditions. Gate: practical appliance regression checks pass.
- **M7 — Sign-off and stable preparation:** signed-off per-row evidence summary, current README/release/docs, no open mandatory blocker. After the owner separately authorizes stable publication, advance to `v0.5.8_1` under version policy, qualify the *exact release package*, publish GitHub and FreeBSD15 package repository, then verify OPNsense Web install/update. A passing `v0.5.7_N` test does not by itself prove the repackaged `v0.5.8_1` delivery.

Every step finishes with one of **PASS / FAIL / BLOCKED / NOT RUN**, the exact installed or source candidate, a specific evidence link or owner observation, and exactly one next action. A FAIL creates a smallest-scope repair and retest, not a new research campaign. The comprehensive operational checklist belongs only to [EXTRA_RESOURCES_ACCEPTANCE.md](../verification/EXTRA_RESOURCES_ACCEPTANCE.md); this section owns the approved milestones and gates.
