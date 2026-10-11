# Voice Transmission — план завершения и стабилизации

**v0.5.1_86 (2026-10-11):** Stage 2 gains a NARROW recovery path for exactly one already-running native Voice candidate dvtws2 without supervisor. Under the SAME FD9 + original Config flock, the existing `voice_native_forward_apply.py` preflights immutable old install image/process policy/IPFW ownership, observes two stable engine-only PID/start snapshots, verifies candidate runtime redo/digest, actual FreeBSD kernel argv/executable and bounded IPFW PRECOMMIT, and dispatches new no-PID `stop-candidate-engine` through the existing pinned `voice_native_process_lifecycle.sh`. `FreeBSDVoiceProcessActions` independently repeats kernel/epoch gate before stop. After verified all-stopped state, it reuses EXACTLY the existing five-resource rollback (IPFW, runtime, Config, prior engine and supervisor). Foreign engine/partial supervisor/failed stop remain fail-closed with MUTATING evidence. Added real-file/simulated-kernel positive+negative tests to current Linux/FreeBSD Voice matrix. **NOT yet qualified for OPNsense/GUI ON or Telegram media; old-state finalization and other crash states remain open.**


**v0.5.1_83 (2026-10-11):** Corrected forward-failure test injection to distinguish PREPARED preflight refusal from post-MUTATING failure eligible for the existing five-resource rollback. `_82` CI failed on this fixture ordering mismatch rather than an exception in production rollback. No unsafe fallback added. Exact-head CI pending.


**v0.5.1_82 (2026-10-11):** Native private one-FD Voice forward Apply now requires the sealed previous install image BEFORE any process mutation and handles failures using the pre-existing `preflight_native_recovery` + `restore_previous_five_resources` on the SAME locked Config inode and original FD9. When the durable whole journal is MUTATING and all native process/IPFW evidence supports rollback, it restores the old five domains and reports a failed Apply; an incomplete/foreign recovery remains fail-closed with both journals retained. PREPARED failures never stop existing service; an already durable COMMITTED journal is NEVER rolled back (IPFW postcommit requires forward reconciliation). New real-filesystem/kernel-simulator late-failure regression and single-descriptor PREPARED/MUTATING/COMMITTED failure paths in Linux and FreeBSD CI. **Still OPEN:** partial one-engine/no-supervisor failure and crash states, durable previous-restart finalization, public service/GUI ON, real OPNsense acceptance.


**v0.5.1_81 (2026-10-11):** The EXISTING `voice_cutover_five_resource_rollback.py` now optionally accepts a borrowed already-locked original Config FD, so it can restore old engine/IPFW/runtime/Config/supervisor under the SAME original flock as private `voice_native_forward_apply.py`. It strictly checks the borrowed descriptor's inode/ownership and acquired flock, never obtains a second conflicting Config lock, and never closes/unlocks a borrowed FD. Its existing manual recovery caller (no borrowed FD) keeps original behavior. Added isolated real-filesystem + simulated process/IPFW tests proving one Config flock spans stop→IPFW→files→restart, rejects unlocked/foreign descriptors and retains the MUTATING journal. **Still OPEN:** safe automatic invocation by native forward on every failure, postcommit finish, production GUI/boot and real OPNsense qualification; do not call private Apply from GUI.


**v0.5.1_80 (2026-10-11):** `_79` real five-resource COMMIT integration test exposed one concrete API mismatch: existing `voice_ipfw_runtime.commit_verified(store, adapter, whole, proof)` takes four arguments, not five. The private native Apply now invokes that existing post-whole-commit IPFW function with the correct contract; no independent IPFW commit path or public ON authority is added. `_79` Voice CI passed 7/8 new coordinator tests, failure strictly at this call; `_80` exact-head CI and actual postcommit state verification required.


**v0.5.1_79 (2026-10-11):** Introduced PRIVATE `voice_native_forward_apply.py` to compose existing schema-4 PREPARED stop/runtime, one candidate engine, IPFW PRECOMMIT, candidate supervisor, and candidate Config under ONE ORIGINAL FD9 owner + ONE Config flock/inode, followed by independent double five-domain live attestation and durable whole COMMIT before existing `commit_verified` IPFW ownership/old-stage-table cleanup. The read-only witness recomputes the MUTATING predecessor digest from COMMITTED for retained runtime/redo evidence, verifies actual kernel process argv/PID-start and scoped IPFW, and retains previous backup/whole journal for postcommit cleanup. Includes genuine filesystem+simulated native IPFW commit tests and single-descriptor staged-order/failure tests in Linux/FreeBSD CI. **Not yet public Voice ON:** automatic same-FD prior rollback, postcommit cleanup/normal boot, GUI/configd wiring and real appliance are still OPEN; on ambiguous failure intent stays fail-closed.


**v0.5.1_78 (2026-10-11):** `_77` Voice CI passed 9/10 real changed-candidate Config tests; the remaining negative source-replacement fixture used unlink()+create, which can recycle the just-freed inode. Replaced it with a separately created same-byte, same-mode file and `os.replace()` while the original inode still exists, then explicitly assert different inode before expecting the existing forward-redo anti-replacement check to refuse rollback. Production Config/IPFW/native lifecycle writer unchanged. This is an isolated test-fixture correction; exact-head `_78` CI and FreeBSD 15 qualification required.


**v0.5.1_77 (2026-10-11):** The first `_76` Voice CI revealed the inherited `_69.._75` integration fixture used identical previous and staged Config bytes. Fixed `_77` test setup to generate a **distinct candidate XML BEFORE** the schema-4 PREPARED intent is sealed so success, prefix-power-cut replay and previous-restore tests exercise actual write mutation, not a no-op. The native candidate writer now correctly returns `candidate-config-unchanged` when desired and previous Config truly have identical bytes and mode (without manufacturing a redo). Original FD9, Config inode/flock, independent kernel/IPFW proof, write-ahead and no public Apply/COMMIT guarantees stay intact. `_76` Voice CI failed at its new test fixture; `_77` exact-head CI is required.


**Статус:** ЕДИНЫЙ АКТУАЛЬНЫЙ ПЛАН · Draft PR [#328](https://github.com/Tolian82/os-zapret2-restyle/pull/328) · 2026-10-11  
**Исходная ревизия аудита:** `v0.5.1_75`, `dc27412375731fc54f1df97a36f61c541f2f1790`. **Текущий кандидат реализации:** `v0.5.1_86` (Stage 2 начат). Версия пакета не опубликована, изменения ещё не устанавливались и не проверялись на реальной OPNsense.  
**Приоритет:** законченный пользовательский сценарий, не очередная подсистема проверки. Детальное утверждённое ТЗ и компоновка остаются в [VOICE_TRANSMISSION_GUI.md](VOICE_TRANSMISSION_GUI.md); сведения о стенде и фактических звонках — в отдельных исследовательских документах. Исторические задачи в ROADMAP, START_HERE и старых блоках архитектурного документа НЕ заменяют эту последовательность.

## Цель и определение готовности

Штатная страница «Передача голоса» после «Стратегии», перед «Лаборатория»: пять независимо сохраняемых профилей Telegram, Discord, X (Twitter), SIP (VoIP), Custom; по одной галочке, многострочному полю нативных STUN/dvtws2 параметров и совместному IPv4/CIDR IPSET для каждого; Voice WAN вверху; общий статус Zapret2; стандартная нижняя кнопка «Применить». Нет полей LAN/входных интерфейсов, опциональной галочки локального UDP или восстановления после reboot. Non-STUN остаётся в «Стратегиях». Сохранённые OFF-поля не стираются. Один общий dvtws2, общий lifecycle и модель Config без второго постоянного состояния; маршруты, Squid/sing-box/TCP/TLS, NAT/PF и исследовательский Docker не изменяем.

**Два разных результата:** (1) **GUI/CONFIG/BOOT PASS** — безопасно сохраняются, включаются, выключаются и восстанавливаются нужные UDP-профили, проверяется реальный IPFW capture и не нарушены ordinary Strategies; (2) **MEDIA_PASS / CALL_PASS** — отдельно измеренная передача UDP-медиа/двусторонней речи в конкретном Telegram-эксперименте. Готовая страница не требует заранее доказанной универсальной Telegram-стратегии, но ни одна стратегия не может объявляться рабочей по одному CI/counter/факту слышимого звука.

## Аудит уже выполненной работы — НЕ переписывать заново

| Область | Реализовано | Чего нет |
|---|---|---|
| OPNsense MVC и модель | `Menu.xml`, `IndexController`, `voice.xml`, `voice.volt`, `Zapret.xml`; 5 сервисов и shared IPSET; RU/EN, form snapshot/optimistic concurrency, read-only validate, OFF-only draft and Apply | Полноценный GUI ON Apply, единые точные per-service статусы, окончательная визуальная приёмка |
| Подготовка одного движка | `voice_model_export.py`, `voice_profile_compiler.py`, `voice_release_stage.py`, `voice_traffic_merge.py`, `voice_capture_plan.py`, генерация combined `dvtws.args` | Выбор кандидата как реально действующего Voice runtime штатной службы |
| Forward cutover | `voice_native_forward_prepare.py`, `voice_native_forward_stop.py`, `voice_native_forward_runtime.py`, `voice_native_candidate_engine_start.py`, `voice_native_forward_ipfw.py`, `voice_native_forward_supervisor.py` | Один production владелец всей цепочки, кандидатный Config, общий COMMIT |
| Защита и откат | Фактический Config restore `voice_cutover_config_restore.py`, write-ahead `voice_cutover_config_redo.py`, `voice_cutover_file_rollback.py`, `voice_cutover_five_resource_rollback.py`, native recovery, IPFW ledger, runtime redo и журналы | Согласование с forward-путём, аварийным runtime-failure, boot recovery и finish; не создавать заново готовый restore |
| Штатный lifecycle | Оригинальные service lockf FD9, Config flock, shared `zapret_service.sh` и orchestrator, частные безопасные native actions, fail-closed guard | Работающая public/configd точка ON Apply; отказ от параллельной legacy PoC authority, нормальный Voice boot |
| Проверки | Voice offline CI и FreeBSD 15 package build — PASS на `dc274123`; PR title PASS | Общий Project CI FAIL: `test-strategy-lab-live-matrix-contract.sh` не нашёл текущий `os-zapret2-restyle-0.5.1_75.pkg` в PROJECT_STATE; отсутствует on-device owner-live/UDP acceptance |

Текущий GUI разрешает сохранить/применить лишь профили OFF. Новый Config writer — это **прямая запись желаемой конфигурации**; готовый Config restore/redo относится к возврату предыдущих байтов. Нужен минимальный проверяемый прямой write-ahead, если он действительно не покрывается существующим intent; сохранять исходный inode `/conf/config.xml`, внешний FD9 и один непрерывный Config flock. Нельзя объявлять `Config::save()` в PHP атомарной частью FD9: её текущая семантика блокировок отличается.

## Очередность исполнения и критерии закрытия

### Этап 1 — Стабилизировать существующий код (ЗАКРЫТ на ff6431c)

1. Привести START_HERE, PROJECT_STATE, ROADMAP, INDEX, ТЗ, release notes и Draft PR к одной актуальной ревизии/границе готовности/плану; исторические записи пометить историческими вместо удаления доказательств.
2. Исправить конкретную ошибку общего CI: PROJECT_STATE должен содержать точную динамически ожидаемую идентичность пакета исходников `os-zapret2-restyle-0.5.1_75.pkg`, пометку «не опубликован». Подтвердить совместимость с существующим `test-strategy-lab-live-matrix-contract.sh`, а не ослаблять контракт фиктивным PASS.
3. Проверить активные GitHub PR/Issues/review threads: найден **один открытый Draft PR #328**, открытых Issues и незавершённых обсуждений ревью нет (снимок 2026-10-11). Не закрывать #328 до приёмки.
4. Пройти **на точном новом HEAD**: Voice CI, общий Project CI, governance/PR title, FreeBSD 15 package build. Для новых дефектов фиксировать воспроизводимый провал и устранять его, не создавать абстракции «на всякий случай».
5. Зафиксировать текущие подлинные пробелы интеграции и не путать mocked kernel/daemon/IPFW с owner-live. После успеха — переход к этапу 2.

**Результат:** на `ff6431c` полный CI (повторный Validate Project), Voice, governance и FreeBSD 15 PASS. Непостоянный первый сбой Strategy Lab circular-e2e не воспроизвёлся без изменения исходников. Документационная стабилизация не меняла ревизию; затем начался этап 2 с новым кодом `_76`.

### Этап 2 — Собрать один настоящий native Apply/rollback (ТЕКУЩИЙ)

**Усиление `_85`:** прежде чем старый five-resource rollback вызывает stop на живом кандидате, native coordinator обязан дважды подтвердить полный трёхролевой PID/start inventory и точные argv/путь исполняемого файла через FreeBSD kernel API, а также соответствие установленного runtime сохранённой кандидатной контрольной сумме. Engine-only/partial supervisor остаются blocked/manual, а не слепо убиваются. Проверка никаким образом не подтверждает доставку Telegram MEDIA_PASS.

**Реализация `_79`:** появился приватный `voice_native_forward_apply.py` с одним дескриптором Config/flock и одной FD9-арендой для уже готовых STOP → runtime → engine → IPFW PRECOMMIT → supervisor → forward Config; затем двойная независимая проверка всех пяти живых ресурсов, `journal.commit()` и штатный `commit_verified()` IPFW. Предшествующая MUTATING-сумма независимо восстанавливается из терминального COMMITTED для привязанных runtime/Config redo. Журнал/backup сохраняются до postcommit cleanup. **НЕ ЗАКРЫТО:** автоматический откат после неуспешной мутации должен использовать тот же уже захваченный Config FD, а существующий rollback уже может принимать один и тот же Config FD после `_81`, и автоматический вызов для состояний с подтверждённым полным процессным владением теперь подключён в `_82`; частичный один-engine/no-supervisor и аварийные crash-состояния ещё не охвачены. Любая неоднозначность пока fail-closed, не READY и без публичного маршрута. Реальный FreeBSD/GUI/boot также не принят.

**Уже реализовано в `_76`, исправлено в `_77–_78`:** отдельный **forward** candidate Config writer `voice_native_forward_config.py`, связанный с существующим schema-4 MUTATING, прежним backup, активным/runtime redo, pending IPFW, реальными ролями dvtws2+supervisor (kernel argv/binary), Config inode и непрерывными FD9/flock. Новое write-ahead `forward-config-redo.json` строго необходимо для прямой записи (existing `config-restore-redo.json` относится только к *обратной* записи прежних байтов). Writer не имеет публичного CLI; при обрыве candidate-prefix записи новый redo позволяет либо продолжить прямую запись под живым native gate, либо существующему Config restore безопасно восстановить прежние байты после остановки кандидата и восстановления IPFW в составе полного rollback. Текущие независимые модули ещё не дают общего COMMIT. Нельзя удалять redo/intent по одному успешному writer.

- Один owner под исходными FD9 и Config flock выполняет **без повторных реализаций** PREPARED → MUTATING → остановка предыдущих процессов → runtime swap → candidate engine → owned IPFW PRECOMMIT → supervisor → сохранение candidate Config → двойная независимая проверка всех пяти ресурсов → согласованный IPFW/whole COMMIT/finish.
- Проверить атомарность допустимого *логического* cutover через журналы и компенсирующий откат; не обещать аппаратную атомарность пяти системных ресурсов. Двойная проверка не заменяет внешнего блокирования.
- Для candidate Config использовать защищённый inode-постоянный writer под теми же блокировками и долговечным write-ahead с точным old/desired digest; на сбое не стирать intent/backup. Учитывать отличие PHP `Config::save()`.
- На ошибке после любой мутации остановить кандидата и использовать **готовый** full five-resource rollback; при неоднозначности оставить fail-closed pending и доступную оператору диагностику. Перед COMMIT обязательно проверить всю новую конфигурацию, не только живые IPFW правила.
- Запустить полный offline fault-injection интеграционный прогон от подготовленного старого состояния до нового/возврата старого, включая обрыв каждого перехода и повторное выполнение.

**Готово:** один ограниченный нативный исполнитель проверяемо применяет всю операцию и возвращает пять ресурсов; сценарий не требует ручного вызова частных шагов.

### Этап 3 — Штатный lifecycle, миграция и reboot

- Подключить один native исполнитель к существующим `zapret_service.sh`, configd и общему orchestrator без второго dvtws2, параллельного watcher или нового cron.
- Перенаправить `telegram_voice_enable/disable/status` как совместимые адаптеры к **той же постоянной модели**. Старый `telegram_voice.sh`, marker и hard-coded prepend выводить из authority **только после** проверенной явной миграции; отсутствие marker после reboot не доказывает OFF.
- Объединить `supervisor_loop.sh → runtime-failure` с новым владельцем; его асинхронное срабатывание не должно обойти журнал/rollback.
- Разделить **нормальный** reboot/start (автоматически восстановить сохранённый ON/OFF по Config) и **аварийный** incomplete transaction (полный доказанный recovery или fail-closed/manual review), без ложной готовности.
- Уважать глобальную OFF службу, Strategy Lab locks, сохранённый ordinary/non-STUN профиль и выбранный WAN. Пока два независимых WAN нельзя разделить в одном двигателе — до Apply отклонять несовместимый Voice WAN, не скрывать ограничение.

**Готово:** одно постоянное ON/OFF, одно служебное и одно IPFW владение; штатный restart/reconfigure/reboot работает без ручного enable, старый PoC больше не конкурент.

### Этап 4 — Закончить GUI по утверждённому макету

- Стандартная нижняя «Применить» должна одинаково объяснимо обрабатывать ON/OFF, save, duplicate tabs, disabled parameter retention, поле ошибки/строку, применённое состояние и interrupted/recovery.
- Показать для каждого сервиса сохранённый выбор отдельно от проверенного активного профиля, effective WAN/UDP-портов/IPSET и owner-rule/counter; не объявлять удачный звонок по статусу правила.
- Сверить реальную разметку со «Стратегиями»: native `base_form`, отступы и рамка, общая строка службы, RU/EN, help, светлая/тёмная темы, узкий экран. Не дублировать ненужные элементы установки/запуска службы, если уже есть общий корректный UI.
- Обновить подсказки, где осталось «draft does not save» или «Voice ON unavailable», только ПОСЛЕ действительной реализации. Не добавлять LAN/local UDP/boot toggles и отдельный non-STUN.

**Готово:** данные переживают reload, результаты/ошибки верны; UI соответствует эталону на устройстве.

### Этап 5 — Приёмка на настоящем FreeBSD/OPNsense

- До любых изменений: read-only baseline реальных `kern.proc.args`/pathname/UID, IPFW ownership, Config/runtime, версии ABI, проверка ordinary Strategies и резервных копий.
- Контролируемый живой Apply: один/несколько не пересекающихся Voice STUN профилей, IPSET/порт/WAN, OFF, глобальный OFF, повторы, отказные случаи, реальный rollback, нативные правила/таблицы, отсутствие второго движка.
- Отдельно проверить forwarded LAN/VLAN, OPNsense-local UDP и SOCKS-created UDP, не менять маршруты/PFIL/NAT/TCP proxy.
- Reboot **без ручного enable**; сравнить Config, runtime, процессы, supervisor, IPFW и счётчики с исходным сохранённым выбором. Нагрузку и recovery ошибки документировать.

**Готово:** записана owner-live доказательная база; нет регрессии обычного Zapret2 и жизненного цикла.

### Этап 6 — Протокол передачи Telegram UDP и голоса

- Использовать сохранённую лабораторную инфраструктуру, существующие PCAP/reflector/Docker инструменты и фактическую топологию OPNsense `192.168.1.2`, TNAS `192.168.1.100`, parent TCP/TLS proxy `185.203.117.88:33128`; старый gateway `192.168.1.140` не объявлять действующим путём UDP.
- Отдельно доказывать `WIRE_OK`, `REFLECTOR_REPLY`, `MEDIA_PASS`, `CALL_PASS` конкретного запуска; изменение счётчика IPFW или слышимый звук без UDP media capture не равно `CALL_PASS`.
- Не переносить непроверенные стратегии Telegram на Discord/X/SIP. Смена DPI-стратегии экспериментальна и не блокирует выпуск корректной страницы без заведомо рабочего preset.

**Готово:** результат медиатеста воспроизводимо записан и отделён от приёмки функций страницы.

### Этап 7 — Финальная приёмка, ревизии и публикация

- Полная регрессия проекта, Voice, normal lifecycle, FreeBSD 15 package, source/API/UI/docs, upgrade/migration/cold boot; независимое повторение критических сценариев.
- Итоговый аудит устранения временных PoC путей; описание оставшихся ограничений без ложных PASS.
- Завершить Draft PR #328 лишь после принятых критериев, согласовать выпуск по действующим правилам `GITHUB_PUBLICATION.md`; CI package build не означает опубликованный pkg.
- Каждый кодовый commit увеличивает последнюю цифру `PLUGIN_REVISION`; документация без изменения исходников её не увеличивает.

**Готово:** пользовательское ТЗ закрыто фактическими доказательствами и пакет действительно готов к выбранному каналу публикации.

## Антизацикливание

Ровно семь результатов выше являются границами задач. Новый самостоятельный журнал, schema, проверка, архив, карантин или промежуточная ревизия допустимы **только** для доказанного дефекта безопасности/согласованности внутри очередного этапа. Не повторять готовые Config restore, IPFW ledger, process attestation, cleanup или уже проверенные лабораторные гипотезы. Перед каждым исходным commit обозначать конкретный сломанный acceptance criterion и тест, который изменится. Разрешается больше одного commit на этап для реальных исправлений; запрещено считать рост номера ревизии мерой прогресса.

## Открытые риски и честные границы

1. Уже готовый restore **не** равен реализованному forward candidate Config persist; требуется проверить разрыв.
2. Изолированные FreeBSD-like тесты имитируют живое ядро, exec/daemon и IPFW; реальный производственный переход не квалифицирован.
3. Асинхронный `runtime-failure` supervisor, normal reboot и прежний Telegram PoC остаются интеграционными рисками.
4. Нормальный ON без восстановленной автоматической загрузки не соответствует ТЗ; emergency fail-closed нельзя подменять статусом READY.
5. CLI `telegram_voice_*` до миграции не являются единственным источником Voice preferences.
6. Поддержка разных Voice/Strategies WAN в общем dvtws2 пока ограничена; применение неверного WAN должно быть отклонено, а не молча изменить другой профиль.

**Точка продолжения:** сначала закрыть этап 1 реальным GitHub CI на текущем SHA, затем этап 2 (не дальнейший refactor cleanup). 
