# ТЗ_6v5 S10b2b1 — проверка истинной пары original argv → schema3 argv под исходным FD9

**База:** [S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319) открыт. Приняты [S10a #1320](https://github.com/Tolian82/os-zapret2-restyle/pull/1320), [S10b1 #1321](https://github.com/Tolian82/os-zapret2-restyle/pull/1321), [S10b2a #1322](https://github.com/Tolian82/os-zapret2-restyle/pull/1322); на `main` — `v0.6.5_201 23dd4953`. **Это только S10b2b1, не GO всего S10b2b/S10 и не S11.**

## Установленная проблема исходных доказательств

Исходные S08c `NativeParity` и S08d `EffectiveSnapshot` строятся на `dvtws.args` до промоции Auto. Штатный `auto_detect_origin_map.promote_learning_release()` сохраняет *старые точные байты* в `release/dvtws.original.args`, заменяет `release/dvtws.args` и пишет `release/auto-detect-generation.json` schema3. Это **разные** SHA; прежний S09b `attest_sealed_original()` сверяет `native.original_args_sha256` с текущим `dvtws.args`, поэтому нельзя подменять source proof или объявлять S09b прежним «PASS» для промотированного schema3.

Нельзя задним числом генерировать новые native args, менять S08d fingerprint с оригинальных исходных данных на произвольные postpromotion bytes или присваивать дополнительный FD9/Config/P1 writer. В существующем source-map хранится оригинальная карта first-match; в оригинальном schema3 proof — карта working/learning профилей.

## Новый nonactivating source bridge

`backend/neutral_schema3_source_bridge.py` — **import-only** оригинальный read-only адаптер; внутренняя установленная точка `attest_schema3_under_fd9()` требует `voice_ipfw_adapter.require_lifecycle_lock()`, берёт только уже существующие фиксированные `shared_apply_seal.WORK` и `shared_apply_operation.DEFAULT_ROOT`.

`_attest_original_schema3()`:
- Требует единственную исходную `SharedApplyOperation(PREPARED)` без Found и без ещё прикреплённого manifest; сверяет точную generation, оригинальный **PHP logical** `detail.candidate` и исходный sealed `plan.json` через S10a `_journal`/`_original_plan_matches`. Не придумывает Python-версию PHP digest.
- Под дескрипторами `O_NOFOLLOW` оригинальных `shared-work/<id>/release` читает `bundle-seal.json`, `auto-detect-source-map.json`, старый `dvtws.original.args`, конечный `dvtws.args` и `auto-detect-generation.json`; проверяет UID, число ссылок, режим `0600/0644` **именно для оригинального schema3-promoter**, размеры, inode/mtime/ctime и повторы.
- Вызывает **существующую оригинальную** `auto_detect_origin_map.verify_learning_promotion(work, original_php_candidate)`, сравнивает результат с canonical sealed schema3 JSON. Никакого второго `plan_learning_tier` или fallback на активные аргументы.
- Требует исходный S08c `NativeParity` со статусом `ORIGINAL_SOURCE_PARITY_ONLY` и родными original/proposed SHA; исходный S08d `EffectiveSnapshot` обязан соответствовать **старым**, не новым argv. Сверяет действительный original source-map, рабочие номера, first-match и количество/номера/hostlist learning профилей с типизированной S08c структурой.
- Перепроверяет оригинальную seal целиком и **все пять** фиксированных файлов, прежний PREPARED journal и каталог перед возвратом receipt. Не изменяет release, Config, WAN, IPFW, процессы или P1; `authorization=NONE`, `physical_transition_allowed=False`, `promotion_allowed=False`.

**Важно:** активный `S10a manifest` по действующей схеме S09a всё ещё требует `EffectiveSnapshot` финального argv, который S08d по соглашению отказывается создавать для argv с `--hostlist-auto`. Поэтому данный этап **не подмешивает новый тип proof в старые S09b/S10a**: он достоверно устанавливает пару, а S10b2b2 должен согласовать целевую S09/root semantic schema3 projection без фальсификации `EffectiveSnapshot`. Для `auto` без подходящих HOSTLIST-клонов двухуровневая карта не создаётся; этот метод **отказывает**, а старый источник `dvtws.args` остаётся прежним. Для list/all ничего не меняется.

## Реальная проверка (без живого маршрутизатора)

`scripts/test-tz6v5-s10b2b1-original-schema3-preimage.py` использует настоящие `OriginalSharedGeneration`/S08c P2e, оригинальный `auto_detect_origin_map.preflight_learning_tier` и `promote_learning_release`, штатный `shared_apply_seal.create_seal`, настоящий `SharedApplyOperation(PREPARED)`. На точно тех же сохранённых байтах проверяются old/new SHA, first-match и voice/IPFW из S08c/S08d, отсутствие записи. Дополнительно — подмена Original/Promoted args, source/active map, неправильные PHP candidate/epoch, отсутствие promotion, чужой symlink, torn pending, неверные S08c/S08d/mode/count, преждевременный RESTORED, race во время native verify и отсутствие FD9.

**Критерий S10b2b1 GO:** exact-head CI с настоящим P2e + оригинальный FreeBSD/native matrix + postmerge main. **Критерий S10 целиком по-прежнему NO-GO:** ещё нужны S10b2b2 truthful final effective/root (Auto) и positive original FD9 gate с runtime WAN/Config/IPFW/process предобразами, S10c crash/rollback/P1 CAS. S11 Start/Stop/Reload отдельно. Никакой публичный `os-zapret2-restyle-0.6.5_202.pkg` не выпускается, пользовательское устройство не трогается.
