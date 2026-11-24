# ТЗ_6v5 S09b — проверка настоящих sealed-файлов исходного генератора

**Этап:** [S09 #1316](https://github.com/Tolian82/os-zapret2-restyle/issues/1316); вход: [S09a](ZAPRET2_TZ6V5_S09A_ROOT_SCHEMA.md), [S08c](ZAPRET2_TZ6V5_S08_PURE_COMPILER_NATIVE_GO.md), [S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md). **Неактивирующий контроль; не новый seal и не второй исполнитель.**

## Пользовательский результат и граница

Единственный оригинальный `orchestrator_build_release` сохраняет исходные `dvtws.args` и (только при `auto`) `auto-detect-source-map.json`. Оригинальный `shared_apply_seal.py` до и после чтения проверяет **весь** существующий sealed `candidate.xml/plan.json/release`. Добавленная `neutral_root_refs.py` сверяет строго ограниченный detached JSON-корень из S09a с **реальными байтами этого же оригинального поколения**, а не с доверенным заявлением о файлах.

Оригинальный генератор закрепляет `0600` на окончательно составленном `dvtws.args` **после** возможной атомарной замены global-exclusion; для его отдельно создаваемой native-Voice версии — то же. Это обязательное совпадение с уже принятым S09a-контрактом, без переписывания аргументов, выбора профилей или дублирования генератора.

Дескрипторы файлов открываются через `dir_fd` и `O_NOFOLLOW|O_NONBLOCK`: доверенный parent shared-work → basename `[0-9a-f]{32}` → ровно `release` → фиксированные `dvtws.args`/`auto-detect-source-map.json`, без произвольных путей из manifest. Проверяются владелец, точный `0600`, обычный файл с `nlink=1`, размер, dev/inode, режим, uid/gid, `mtime/ctime` до/после чтения и повторная идентичность имени в каталоге. Исходные seal, файлы и каталог проверяются повторно перед выдачей результата. Для `all/list` оригинальная source-map **запрещена**; для `auto` обязательны generation, конечный argv SHA и существующий статус original nonactivating source-map. Встраивать профили, домены, IP, argv, Voice или P1 в JSON нельзя.

Входные S08c `NativeParity` и S08d `EffectiveSnapshot` **не являются полномочиями**. Возвращаемое immutable-свидетельство имеет `authorization=NONE`, `physical_transition_allowed=False`, `reattest_under_original_fd9=True`. Нет доступа к Config, dvtws2, PID, IPFW, изменяемым P1/Found, нет сигнала, Start/Stop/Reload, внешних процессов или новых Config/manifest/FD9 writers. Существующий mutable CAS/P1/ACK остаётся единственным владельцем содержимого списков; только имена managed-ссылок присутствуют в JSON.

## Проверка и критерии GO

`scripts/test-tz6v5-s09b-sealed-root-refs.py`:
- строгие положительные sealed `list`/`auto`, совпадение root/seal/original argv SHA, отсутствие каких-либо записей при read-only проверке;
- missing, overwritten, oversized, wrong mode, symlink/cycle, hardlink, wrong owner, symlink release, stale generation, mutated root, wrong native parity;
- целенаправленная замена inode между первой и второй проверкой, обязанная закончиться отказом;
- **реальная интеграция** исходного S08c → P2e `orchestrator_build_release` для `list` и `auto`, затем оригинальный `create_seal`/`verify_seal` и аттестация точных физически записанных файлов. S08d `snapshot()` вычисляет structural fingerprint **на тех же настоящих original argv/SourceMap/ordered selectors/WAN/Voice-capture/ports/managed-ресурсах**, без подмены готовым синтетическим digest; самостоятельная S08d CI-матрица также сохраняется.

Исходный seal в тестах создаётся **до** detached JSON-корня. Это свидетельство исходного поколения; оно не доказывает, что JSON уже стал частью активного sealed release. S10 должен решить размещение и атомарную стыковку root с original owner **без циклической зависимости seal SHA → root → seal**, а затем повторить аттестацию под original FD9 перед активацией/rollback. Нельзя интерпретировать S09b как доказательство будущей физической транзакции.

**Закрытие S09** допускается после успеха точного head CI, real original generator/seal positive и tamper/race negatives; установленная OPNsense и выпущенный `.pkg` для этого шага не нужны. Переход к S10 выполняется по утверждённому порядку. WAN-only Save и pre-Start Strategy Lab остаются независимыми от ordinary active manifest.
