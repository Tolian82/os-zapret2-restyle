# ТЗ_6v5 — S03a: настоящий прежний генератор → воспроизводимый expected RED

**Граница этого checkpoint:** `main 3742188bb2418627242099ab55ae1b83ad8a20bd` / `v0.6.5_131` — неизменённая эталонная реализация. Тестовая ветка `feat/tz6v5-s03-original-generator-red`, будущая метка исходников `v0.6.5_132`; **пакет `os-zapret2-restyle-0.6.5_132.pkg` не создан и не опубликован**. На owner OPNsense последняя подтверждённая `_117.pkg`, никаких действий.

Источник требований: [S03](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md) после [S02 all-caller source map](ZAPRET2_TZ6V5_S02_ACTUAL_LIFECYCLE_ROUTE_AUDIT.md), спецификация [ТЗ_6v5](TZ_6v5.md). **S03a — только первая исполняемая порция S03. Это не GO по всему S03, не native установленного engine, не S04.**

## 1. Новый исполняемый evidence, не mocks/grep

`scripts/test-tz6v5-s03-original-red.py` **импортирует существующий** `scripts/test-p2e-original-shared-build.py::OriginalSharedGeneration`. Он реально вызывает `orchestrator_build_release ... shared-candidate` через исходные `common/config/parser/registry/storage/targets/target_mode/profile_normalizer/profile_pipeline/exclude/blobs/ports/generator/validator/stage/orchestrator.sh`; подпроцесс выполняет оригинальный Python Voice compiler и `auto_detect_origin_map.py emit`. Параметризация **только тестового** `OriginalSharedGeneration.build()` расширена на synthetic `youtube_domains`, `user_domains`, `rule_max`; defaults ранее существовавших тестов сохранены. S03 явно передаёт актуальную нормальную границу `19099`. Upstream native `dvtws2` в этом source-only построении отсутствует.

Продуктовые `src/` файлы **не менялись**, нет второго компилятора или придуманной «эталонной модели», нет Config save/FD9/IPFW mutation/Start/остановки traffic. Сохраняются фактические байты `dvtws.args` и реальные source-map записи, затем нормализуется **только** случайный путь временного тестового каталога. Анонимный SHA-256 реального и нормализованного вывода, номер/тип/порядок нативных профилей, режим/Voice, наличие `manifest.json`, исходный отклик help/status записываются в JSON **без пользовательских доменов или raw Config**.

### Matrix реальных исходных запусков

| Case | Input / ожидаемая наблюдаемая семантика | Verification |
| --- | --- | --- |
| `implicit_all` | один implicit TCP profile, Target Mode all, нет автоматически добавленного HOSTLIST/IPSet | real generated args; expected native profile count=1 |
| `implicit_list` | тот же исходный профиль, Target Mode list, injected YouTube/Telegram/User | native profile count=3 |
| `implicit_auto` | те же три обычных профиля, Auto Mode пока inert source candidate | native profile count=3; actual nonactivating source map |
| `youtube_explicit_list` | authored `<HOSTLIST:youtube>` остаётся приоритетнее default list injection | actual emitter |
| `ordered_auto_voice` | genuine Voice + TCP YouTube → QUIC YouTube → TCP User, неизменный first-match / source-origin | exact `known-hostlist` order and native numbers; three eligible learning copies |
| `global_exclusions_auto` | генерируемые domain/IPSet exclusions по действующему Stage3 | real final argv and map |
| `empty_strategy_all` | разрешённая пустая Traffic Strategy | native engine-base args, no fabricated profile |
| `large_manual_list` | 1024 synthetic YouTube + 1024 synthetic User domains | existing registry/storage/normalization on real producer; no raw list in CI log |
| `bad_hostlist_selector` | неизвестная `<HOSTLIST:absent>` | actual generator nonzero, no successful release claim |
| `invalid_target_mode` | bogus `HOSTLIST_MODE` | actual generator nonzero, no successful release claim |

Никаких присвоений доменов по «пользовательскому индексу»: profile/source identity сравнивается с настоящим `auto-detect-source-map.json`.

## 2. Настоящие expected-RED (не успех реализации)

| Test target | Реальный старый код / вызываемый путь | Нужный V5 contract |
| --- | --- | --- |
| `AUTO_LEARNING_FAIL_THRESHOLD_MISSING` | После `orchestrator_build_release` вызывается настоящий `auto_detect_origin_map.plan_learning_tier`; сейчас каждый `--hostlist-auto` не сопровождается `--hostlist-auto-fail-threshold=1`. Старая P2 (другой путь) не является оправданием отсутствия в schema3 learning. | Точно `--hostlist-auto-fail-threshold=1` для каждого eligible learning clone; проверять только переданные нашим генератором параметры, не upstream алгоритм |
| `CLI_GLOBAL_HELP_UNIMPLEMENTED` | Прямой запуск исходного `zapret_service.sh --help` в offline source workspace; текущий dispatch отдаёт usage rc64 | `--help` → rc0, без FD9/process/Config/IPFW |
| `CLI_RELOAD_HELP_UNIMPLEMENTED` | Прямой запуск `zapret_service.sh reload --help`; текущий dispatch не имеет verb `reload` | пять публичных команд и nested read-only help; невозможен hidden restart |
| `REFERENCE_MANIFEST_UNAVAILABLE` | Реальный offline candidate builder; нет V5 reference-only root manifest с `generation/refs/dvtws.args` | immutable sealed ref-only JSON с anti-tamper и отдельными list/Voice/IPFW/source refs |

**Дополнительный native disposable RED (строго под явным opt-in):** `ZAPRET2_S03_DISPOSABLE_NATIVE=1` + `GITHUB_ACTIONS=true`, `FreeBSD` и root, **нет installed dvtws2/child pid**, приватный temp `LIFECYCLE_LOCK_FILE`. Только тогда выполняется настоящий CLI `zapret_service.sh status --json`. Негативные каналы `STATUS_READONLY_FD9_SIDE_EFFECT` (создан временный lockfile) и `STATUS_JSON_UNIMPLEMENTED` (нет machine-readable state). Запрет выполнять этот тест на owner или любом установленном engine абсолютный. Ни IPFW, ни ordinary Start не вызываются.

## 3. Проверка RED отрицательным контролем

```sh
# На преднамеренно пустом, disposable FreeBSD/OPNsense guest:
ZAPRET2_S03_DISPOSABLE_NATIVE=1 GITHUB_ACTIONS=true \
  python3 scripts/test-tz6v5-s03-original-red.py --capture \
    --disposable-native-status --report /tmp/tz6v5-s03-original-source-red.json

# Нормативный контракт должен упасть (выход НЕ 0):
python3 scripts/test-tz6v5-s03-original-red.py --target \
  --report /tmp/tz6v5-s03-original-source-red.json

# Gate разрешает только точный ожидаемый набор недостатков:
python3 scripts/test-tz6v5-s03-original-red.py --verify-red \
  --report /tmp/tz6v5-s03-original-source-red.json
```

Встроено в уже действующий [P2e/P2g/P2i one disposable OPNsense CI](https://github.com/Tolian82/os-zapret2-restyle/blob/main/.github/workflows/p2e-original-shared-build-native.yml), перед native dvtws2 preview. Наличие доказанного RED в JSON **не превращает** ещё не написанный функционал в PASS. При фактическом исправлении RED перестаёт совпадать, тест должен быть переведён в GREEN с настоящим positive behaviour и CI обязан остановиться до явной замены.

## 4. Оставшийся объём S03 — НЕ выполнен этим PR

- S03 **полный** old/next effective-diff matrix `NO_CHANGE/RELOAD/RESTART/START/STOP/SAVE_ONLY/REFUSE`: refs-only, modified bytes, mixed/profile-order/DPI/Voice/WAN/divert/foreign; no PID/IPFW changes при действительно адресном Reload и точный terminal `RELOAD_REQUESTED`.
- Full G05→G08 **реальный** WAN-only Save без engine/manifest + штатная установка engine **до первого обычного Start** + Standard RU/Extended EN Lab native state restore. Не конструировать mock-only PASS и не повторять Lab ошибку owner без disposable guest.
- Реальные foreign/stale/reused PID, manifest tamper, `--force` owner/birth/epoch guard (включая отрицательные KILL), FD9 BUSY/PREPARED, terminal `INCOMPLETE`, upstream/pkg recovery и one physical writer; `--help` edge cases.
- Lifecycle-only RU/EN producer→consumer from real Strategies/Voice/GUI/Apply/System Services/Boot/Lab/pkg и удаления старых ключей; старые сохранённые receipts.
- Actual Lab stage90/99 RED и Auto live learning/Found RED **только по достоверной независимой disposable physical трассе**, не по вымышленным событиям. Upstream `manual.en.md` canonical: reread/SIGHUP/auto failure behaviour не тестировать.
- Separate existing [IPFW numeric bounds tests](../../scripts/test-ipfw-number-scope.py) нужны на exact HEAD; привязанные V5-17 only 19000–19099 / 19100–19131, никогда 19132–19139, future-only 19140–19200 и rule 65534. Эти тесты проверяют только numeric range, не выдумывают сигнатуры foreign IPFW.

**Статус на момент создания PR:** S03a infrastructure SOURCE IMPLEMENTED, native CI / target-RED witness **PENDING до exact-head успешных CI логов**. **Полный S03 — NO-GO до оставшейся матрицы. S04–S20 NOT RUN.** Документ не даёт разрешения собирать/ставить `.pkg` владельцу.
