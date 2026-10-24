# Дополнительные ресурсы Zapret2 — GUI, установка и Strategy Lab (ТЗ)

**Status:** owner-approved requirements (22 October 2026), amended 23 October 2026 for exact resource-set reconciliation. Source implementation now includes the manual Settings button, resource transaction, dynamic BIN/Lua search candidates, and per-click terminal status correlation (`v0.5.7_20`). These remain unverified on installed OPNsense; package publication and stable release are separate decisions.

## 1. Назначение и терминология

Публичный каталог: **[Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources)**.

Каталог содержит дополнительные:
- **Lua-модули** (`.lua`) — сценарии/функции обработки трафика для штатного движка Zapret2;
- **BLOB-файлы** (`.bin`) — файлы с образцами сетевых пакетов / payload, используемые в fake/seqovl и иных поддерживаемых нативных приёмах.

Они **не являются ML-моделями** и не называются «моделями» ни в UI, ни в справке. Слово «стратегии» также не заменяет «ресурсы»: готовые стратегии в плагине существовали раньше, а ресурсы — их зависимости и расширения.

Название отдельной кнопки:
- RU: **«Установить дополнительные ресурсы»**;
- EN: **“Install Additional Resources”**.

**Надпись согласована окончательно:** сохранять именно эти названия RU/EN без замены при повторной установке и без смешения с штатным `«Применить» / “Apply”`. Повторное нажатие той же кнопки выполняет безопасную повторную проверку/установку (при наличии обновления — обновление ресурсов); второй кнопки не создавать.

## 2. Расположение и поведение GUI

Страница: существующая **«Стратегия»** (`src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt`). Размещение сверено с предоставленным владельцем снимком панели состояния.

- Кнопка в **новой второй строке под левым блоком «Статус:»**, под статусом/версией службы, в верхней области управления Zapret2.
- Визуально привязать к левому краю секции состояния; строка должна оставаться на месте при изменении `Запущена/Остановлена/Error` и при RU/EN/F5.
- Не помещать внутрь выпадающего списка релизов и не менять расположение/смысл кнопок **«Остановить/Запустить»**, верхней **«Применить»** (установка выбранного upstream-релиза) и нижней **«Применить»** (сохранение стратегий).
- Нативный OPNsense стиль, без новой вкладки или страницы; доступная подпись, компактный индикатор выполнения и рядом текстовый статус дополнений (например, не установлены / установлены Lua N, BIN M / ошибка).
- RU/EN переводить не только кнопку, но и статусы, справку, понятные сообщения о конфликтах и ошибках. Загрузка не должна выглядеть как применение пользовательских стратегий.
- Кнопка доступна только при пригодном установленном runtime, **полностью запущенной службе** (`Started`) и отсутствии несовместимой операции (setup/release install, обычный Apply, обслуживаемый запуск/остановка, уже идущая установка дополнений). Если служба остановлена, кнопку блокировать с локализованной подсказкой «Сначала запустите Zapret2» / “Start Zapret2 first”; это исключает фиктивный «перезапуск» ранее остановленной службы. Не допускать повторного запуска или параллельных операций.
- Длительная операция идёт через существующий привилегированный асинхронный configd/backend-контракт со статусом и конечным polling, **не** через долгий синхронный AJAX, который может потерять результат.
- По завершении **установки и обязательного перезапуска службы** показать фактически установленную версию/ревизию ресурсов и количество Lua/BIN, **не** выдавать результат за проверку эффективности стратегии; ошибки установки, перезапуска и восстановления показывать раздельно, без ложного `PASS`.
- Кнопка установки дополнений **не выполняет** ни верхний, ни нижний Apply автоматически и не переписывает сохранённую конфигурацию стратегий.

## 3. Источник, граница установки и жизненный цикл

- **Отдельное явное действие:** новые ресурсы не скачиваются автоматически при любой установке/переключении upstream Zapret2, при pkg-установке плагина, запуске службы или открытии страницы.
- Источник фиксирован на наш управляемый каталог `Tolian82/zapret2-extra-resources`, без произвольных URL от пользователя в первой версии GUI.
- Получать согласованную **неизменяемую** ревизию набора (тег или проверенный commit), проверять манифест и контрольные суммы **до** изменения рабочего дерева. Текущий снимок каталога содержит **19 Lua + 54 BIN = 73 уникальных файлов**; это факт 22.10.2026, **не** неизменный список и не захардкоженный лимит лаборатории.
- Штатные пути на OPNsense:
  - `/usr/local/etc/zapret2/lua/<name>.lua`;
  - `/usr/local/etc/zapret2/files/fake/<name>.bin`.
- Источник содержит `lua/` и `files/fake/`, как и ожидает ResourceInventory; `LICENSE`, `NOTICE`, `CONTRIBUTORS.md`, `inventory/sources.json`, `docs/ALIASES.md` доступны для аудита и сохраняются в управляемой метаинформации инсталляции, не загружаются в dvtws2 как Lua.
- Не перезаписывать файлы upstream **ни выбранной установленной версии, ни более свежей**; перед монтажом сравнить имена, контрольные суммы и происхождение файлов. При имени с другим содержимым — конфликт с отчётом, **не** тихая подмена. By the owner's 23 October amendment, existing untracked Lua/BIN are replaced or removed only by the manual exact-set reconciliation transaction after their original bytes have been durably backed up; upstream-owned files are never overwritten.
- Не копировать дубликаты по содержимому и не создавать лишние алиасы. Для существующих стратегий, ссылающихся на удалённые алиасы, обеспечить отдельную проверку совместимости и понятную диагностику без неявного переписывания текста стратегии.
- Безопасность: запрет обхода путей и symlink, строгий список расширений/путей, проверка формата и размера файлов, закрытые права на временные файлы, итоговые права `0644` на Lua/BIN и `0755` на каталоги для UID/GID 65534.
- Выполнить транзакционную установку: предварительная загрузка/проверка → снимок **только управляемых файлов** и состояния → публикация файлов → инвентаризация/проверка → **обязательный контролируемый перезапуск Zapret2** → проверка готовности всей службы → commit либо rollback. При сбое вернуть прежние дополнительные файлы, штатные файлы Zapret2 и исходное состояние службы. Ошибка сети до публикации не меняет работающий runtime. Любая ошибка перезапуска или health-check означает **ошибку всей установки**, а не успех копирования файлов.
- **Решение владельца (22.10.2026): после каждого успешного нажатия «Установить дополнительные ресурсы» обязателен именно перезапуск службы Zapret2, а не перезагрузка всей OPNsense.** Даже если повторная загрузка не изменила состав файлов, после успешной проверки/установки выполнить `Stop → Start` через **существующий** serialized lifecycle с проверкой нового PID/работоспособности и сохранением настройки службы. Завершённым успехом считать только `Started → restarted healthy Started`; простого копирования файлов или записи `ResourceInventory` недостаточно. При сбое запуска восстановить прежний управляемый набор и попробовать вернуть прежнюю рабочую службу; если восстановление не удалось, явно сообщить `RESTORE_FAILED`. Запуск нового Job после установки формирует свежий инвентарь, но это **не отменяет** обязательного service restart для данного GUI-действия. Из состояния `Stopped` установку кнопкой не начинать: сначала штатный Start, затем отдельное нажатие кнопки.
- Последующее обновление/понижение версии официального Zapret2 **не инициирует новую загрузку** дополнений, но обязано **сохранить уже установленные управляемые файлы** и проверять конфликты с целевой версией. При невозможности сохранения не выдавать успешную установку; обеспечить rollback или явную ошибку. During an explicitly requested manual resource reconciliation, untracked Lua/BIN are backed up and brought into the approved exact set; during upstream version switching, old and target inventories and verified rollback are required before any removal.

## Exact resource-set amendment (owner-approved 23 October 2026)

After a successful manual Additional Resources operation, the top-level
`lua/*.lua` and `files/fake/*.bin` files MUST equal the union of the
resources tracked by the **locally installed upstream Zapret2 Git HEAD** and
the verified Lua/BIN catalog at its immutable extra-resources commit.
These sets change with both upstream and extra-catalog revisions; never
hardcode names or counts. Verify upstream blob bytes against its local Git
tree before mutation. For an identical path in both catalogs, upstream
owns the file; if bytes differ, stop before touching the service.

An untracked Lua/BIN that is neither upstream nor the desired extra is
an orphan, even when created by a user or a previous failed installation.
An untracked file whose name collides with a desired extra is replaceable.
Back up and hash **all** untracked pre-operation Lua/BIN (orphans and
replacements) durably under the existing transaction before native Stop.
After native Stop, remove or replace only the planned untracked files,
install verified extras, check exact inventory and digests, then restart
and attest a newly running native service process. On any failure restore
all previous bytes and ownership metadata, and restore service state.
Refuse unexpected symlinks, tracked-file drift, unresolved transactions,
and saved configuration references to resources scheduled for removal.
No user strategy, Voice settings, HOSTLIST/IPSET or OPNsense Config values
may be modified by this operation.

An upstream-version switch is a separate transaction: capture the old and
target Git resource inventories before checkout, preserve old tracked and
untracked bytes, then reconcile without automatically downloading extras.
Until this switch-specific old/target rollback is proved, uncertain
switches must be blocked rather than pretending the manual sync covers them.

### Release-switch source increment (v0.5.7_32)

An old/target Git resource inventory and exact-set check now guard the
upstream checkout. The updater refuses pre-existing orphan files,
colliding target names and modified tracked blobs before mutation, and
checks the final exact set before native service restart. No automatic
orphan deletion is yet enabled for upstream switching: it still requires
a separately attested all-untracked snapshot and recoverable rollback.
This is an incomplete intermediate implementation of the accepted final
contract, not a change to the owner's approved target behavior.

## 4. Strategy Lab: обязательные функциональные требования

1. **Автоматическая регистрация.** После успешной установки доступные дополнительные `.lua` и `.bin` обнаруживаются текущим `ResourceInventory`. Новый Job формирует свежий снимок каталогов; ранее созданные Job не менять задним числом. Проверять читаемость и непустое содержимое. Важно: **обнаружение не равно участию в поиске**.
2. **Полностью динамическая генерация кандидатов.** Текущий **native** поисковый граф расширяется на основании **фактически присутствующих** `.bin` и `.lua` из нового `ResourceInventory`, а не фиксированного списка имён в исходном коде. При добавлении/удалении файлов новые задания автоматически получают/теряют совместимые кандидаты **без исправления или пересборки плагина**. Пригодность BIN определять по проверяемому содержимому или декларативному описанию возможностей; вызываемые функции Lua, аргументы, роли и зависимости — по корректным описаниям, поставляемым как данные с ресурсами, а не статическому Python-перечню. Описание не заменяет фактическое наличие файла; Lua без проверяемого контракта не выполняется вслепую и помечается `unsupported`. Привязка протокола, payload и зависимостей конкретного кандидата остаётся явной и воспроизводимой в `CandidateSpec`. Не формировать декартово произведение.
3. **Адресная загрузка Lua.** В `dvtws2` инициализировать только необходимые конкретному кандидату зависимости `--lua-init` в правильном порядке, сохраняя обязательные базовые runtime-модули. В Model C объединять зависимости лишь внутри выбранной ограниченной совместимой группы; не загружать все 19 Lua во все задания, избегать дублирования функций и конфликтов.
4. **Адаптивный конечный поиск.** Сохранить Stage 50 / Stage 60, Model C, реальное evidence-based планирование, ограничения времени, отмену, безопасное восстановление и текущую семантику PASS/PARTIAL/FAIL. **Не создавать декартово произведение всех 73 файлов**, не проверять бессмысленные несочетаемые BLOB/Lua/протоколы. Состав каталога может расти — планировщик остаётся конечным.
5. **Нулевая мутация пользовательских стратегий.** Никакой автоматической правки/удаления/переноса существующих Traffic Strategy, Voice Transmission, HOSTLIST/IPSET и сохранённых пользовательских полей. Старые стратегии продолжают работать, если используют штатные файлы и функции.

Дополнительное разграничение: установка файлов не обещает, что каждую позицию нужно обязательно прогнать в одном Job; речь об **eligible search coverage** всех совместимых ресурсов в поддерживаемых протокольных семействах. **Количество 73 — снимок репозитория от 22.10.2026, не константа в лаборатории**. При выборе кандидатов фиксировать явные причины `eligible`, `unsupported`, `missing`, `pruned`, `deferred`, а успешные рекомендации содержат точные зависимости и пути для воспроизводимости. **Согласованный рабочий план:** [ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md](ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md).

## 5. Связь со штатной архитектурой

- GUI/контроллер/конфигд расширяются по существующему `general.volt → ServiceController → configd → setup/runtime lifecycle`, но **без добавления нового второго механизма управления службой**.
- `ResourceInventory`: `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/resources.py`.
- Кандидаты/зависимости: `strategy_lab_py/candidate_spec.py`.
- Native graph: `strategy_lab_py/search_graph.py`.
- Стандартное выполнение Stage 60: `strategy_lab_py/stage60_model_c.py`.
- Сохраняются требования `STRATEGY_LAB_ADAPTIVE_SEARCH.md` к идентичности кандидатов, source-port attribution, budget, PID/firewall cleanup и состоянию исходной службы.
- Данная задача **не** создаёт отдельную страницу «Ресурсы», не подменяет существующие стратегии, не переделывает независимую Voice-подсистему и не запускает старые Telegram-исследования.

## 6. Минимальная приёмка и доказательства

**GUI и состояние:**
- Кнопка именно под статусом в RU и EN, F5 и смена текста состояния не сдвигают первую строку.
- Обе существующие «Применить» и Start/Stop сохраняют прежнее назначение.
- Установка возможна только отдельным нажатием при запущенном Zapret2; повтор без изменений не дублирует файлы/не изменяет стратегии, **но также выполняет обязательный перезапуск**. При `Stopped` кнопка недоступна с понятной RU/EN подсказкой.
- После успеха служба действительно **перезапущена** и снова `Started`, а не просто сохранила старый PID: зафиксированы stop/start и успешная проверка состояния. После отказа вернуть исходное `Started` и старые файлы либо явно показать ошибку восстановления; нет зависших PID, lock или ipfw правил. Начальное `Stopped` — заблокированный сценарий без сетевых/файловых изменений.
- Недоступный GitHub, испорченный манифест/хеш, symlink/path traversal, конфликт имени, нехватка места и сбой при публикации не портят текущую установку.

**Ресурсы и поиск:**
- После успешной установки новый Job видит новые ресурсы и записывает `ResourceInventory` (в том числе количества и необходимые исходные идентификаторы).
- Убедиться, что хотя бы один новый **реально совместимый** BIN и один новый **реально совместимый** Lua-модуль представлены достижимыми кандидатами, а не только учтены в инвентаре; точный выбор для приёмки определяется при реализации. **Проверить динамику:** добавить и удалить BIN и Lua (с данными вызова/зависимостей) без изменения Python/пакета — следующий Job обновляет кандидатов; старый Job остаётся неизменным.
- Поиск не грузит невостребованные Lua; отсутствие требуемого ресурса даёт объяснимый skip, не ложный `PASS`.
- Ограничение времени/адаптивность/реставрация службы/сохранённые пользовательские стратегии не регрессируют.
- При смене upstream-релиза сохранённые дополнения не исчезают молча; новый конфликт блокируется/объясняется.

## 7. Последовательность реализации

1. Бэкенд установки и защиты текущих файлов, транзакции/rollback, **обязательный restart и проверка здоровья службы до фиксации успеха**.
2. Компактный GUI-контрол и RU/EN-помощь/состояние на странице «Стратегия».
3. Реальное расширение `CandidateSpec`/search graph через совместимые дополнительные ресурсы, без неконтролируемого роста.
4. Узкие контрактные тесты и один наблюдаемый owner-live сценарий; без нового архитектурного цикла, не повторять закрытые кампании.
5. Отдельная квалификация пакета и релиз **только по явной команде владельца**.

**Решение владельца 22.10.2026:** кнопка на странице «Стратегия» имеет окончательную подпись RU «Установить дополнительные ресурсы» / EN “Install Additional Resources”; каталог GitHub и пять требований Strategy Lab выше обязательны. Ранее планировавшаяся автоматическая загрузка при переключении runtime **заменена** ручной установкой. После каждого успешного нажатия **перезапуск службы Zapret2 обязателен** с проверкой здоровья, без перезагрузки OPNsense. Пока служба `Stopped`, сначала требуется штатный Start. Старые файлы и стратегии не изменяются автоматически.

## 8. Owner-approved final acceptance and repair contract (24 October 2026)

This section clarifies the accepted resource-sync policy without removing existing runtime safety requirements.

### Two distinct operational paths

**Normal package replacement and manual Additional Resources installation** retain existing configuration, user strategies, managed resource provenance, native lifecycle guarantees and verified rollback. The Additional Resources button is allowed only for a fully Started service; it is not a repair control. A successful manual action restarts the service even when resource contents are unchanged.

**Explicit recovery clean reinstall** is a separately selected operator action for a damaged or inconsistent plugin installation that cannot be safely replaced through the normal path. Its required result is a clean installable/operational plugin that can be configured through OPNsense; retention of the plugin's prior strategies, settings, jobs, managed resources and transaction history is best effort, not a success prerequisite. Only plugin-owned package/runtime/configuration state may be reset. OPNsense system configuration, firewall safety, other plugins, other people's data and unrelated runtime state must not be damaged. This contract does not promise repair of a broken operating system, filesystem or FreeBSD pkg database. A broken/unverifiable native owner may not be silently treated as Stopped: a repair path must be explicit, observable, bounded and tested. Console access through the hypervisor is confirmed available.

The explicit recovery procedure may initially be console-based; a second Web UI, new background service or general-purpose Git recovery engine is **not** required. Do not promise that generic `pkg add -f` already repairs all damaged states: package hooks currently reject incomplete owner state. First test existing recovery capabilities; implement only the smallest demonstrated missing repair path.

### Exact resource-set ownership and retained strategy references

The final manual resource set is exactly the local installed upstream Git HEAD tracked Lua/BIN union the immutable, verified extra catalog. Unknown pre-existing files, including an untracked filename matching a catalog payload, are backed up and attested before replacement/removal. A historical untracked name alone is never sufficient reason to refuse reconciliation. The specific old `files/fake/fake_http_lichess.bin` failure is **one historical example**, not a hard-coded requirement or a privileged exception.

At the same path, identical upstream and catalog content is represented once with upstream ownership; different content is a blocking conflict. No installed user strategy may be silently edited. Detect references to removed resources **and to changed resource contents** before mutation; when compatibility of a referenced replacement is not established, fail safely with a concrete explanation rather than unexpectedly changing the meaning of an existing strategy. Unsupported resources remain visible to inventory but are never run without an acceptable capability descriptor. Installed resources plus reviewed descriptors, not filenames in Python, determine bounded native candidate eligibility.

On upstream release changes use the same ownership/conflict semantics, with independent old/target snapshots and transaction safety. The operation must not automatically download a new extra catalog. Ordinary valid upstream switches must remain usable; unknown or conflicting states may fail closed without pretending that the switch succeeded.

### Practical boundaries and evidence

A safely blocked operation counts as correct only for the specified invalid/unknown state; it cannot replace successful handling of legitimate, supported operations. Automatic reconstruction of arbitrarily dirty, independently edited Git index/worktree bytes is not a deliverable. Retain current read-only inspection and hard no-destructive-reset boundary; defer experimental per-path write-ahead provenance absent a reproduced blocking defect or a separate owner decision.

The test candidate must be persistently published as an immutable `v0.5.7_N` testing package **before** the final live acceptance campaign. Confirm the actual package bytes, provenance, successful FreeBSD 15 build and the installed OPNsense behavior separately. During acceptance, distinguish a clean repair installation from a normal preserving update; test both. Only after all mandatory acceptance gates pass, prepare the separately owner-approved stable `v0.5.8` release with a new package identity and a separate release-package verification.

The owner has confirmed independent hypervisor-console access. Test actual owner-live operations where source CI cannot provide their evidence. The owner-approved bounded execution and acceptance board is [EXTRA_RESOURCES_ACCEPTANCE.md](../verification/EXTRA_RESOURCES_ACCEPTANCE.md); it is the sole operational checklist and cannot invent PASS results.

