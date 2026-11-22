# ТЗ_6v5 — S01: disposition of superseded PR #1228 (KEEP / REWORK / DROP)

**Дата:** 23.11.2026. **Решение:** старый Draft [#1228](https://github.com/Tolian82/os-zapret2-restyle/pull/1228) закрыт без merge; никаких cherry-pick/rebase его кода. Новая исходная база: `main` `c7167b0c035ee6dadd52db072e901bce95f79e41`, source-only `0.6.5_129` после объединения [#1237](https://github.com/Tolian82/os-zapret2-restyle/pull/1237). Следующая единая рабочая ветка `feat/tz6v5-s01-s02-lifecycle-audit`, кандидат source revision `0.6.5_130`. **Это решение S01, не реализация S02–S20 и не выпуск пакета.** На OPNsense владельца последняя подтверждённая установка `_117.pkg`; нового `_129.pkg` или `_130.pkg` не создавали.

**Источники:** [ТЗ_6v5](TZ_6v5.md), [активный S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), [канонический lifecycle](ZAPRET2_CANONICAL_SERVICE_LIFECYCLE.md), [DEV-065–071](../PROJECT_PRINCIPLES.md), [PR #1228 exact final source `3a634d8e`](https://github.com/Tolian82/os-zapret2-restyle/commit/3a634d8ee2697b29753c091d38bb6c09a376ba46), [owner review / old negative evidence](https://github.com/Tolian82/os-zapret2-restyle/pull/1228#issuecomment-7085824084), [Issue #1225 S01 evidence matrix](https://github.com/Tolian82/os-zapret2-restyle/issues/1225#issuecomment-7085821822).

## 1. Почему старый PR не переносим

Старый PR от `main _120` имел 12 изменённых файлов (+155/−64), кандидат `_121`, два коммита и только частичную `original_fd9_lifecycle_transition(start|stop, lab|pkg-update)`. Он перенаправлял вызовы `strategy_lab_internal_dispatch` и `pkg_update_prepare_service`/`pkg_update_finish_service` на общий селектор native Common/legacy, но оставлял отдельными публичные operator actions, Apply candidate transitions, Boot/recovery, installer, callbacks и существующие physical `shared_apply_boot_service`/`shared_apply_stop_service`. На текущем `main _129` функции `original_fd9_lifecycle_transition()` **нет**; выбор сервисного owner ещё встречается в нескольких существующих путях `zapret_service.sh`. Даже если добавить этот старый helper, он не реализует утверждённый общий Start/Stop/Status, sealed reference-only JSON manifest, pure XML adapter/compiler, five-command CLI, strict force/help, read-only status, безопасный Reload или apply diff classifier.

Ветка #1228 устарела по версии и архитектуре. Извлечённый mock-тест не доказывает реальное состояние OPNsense после Stop/Boot, FD9/epoch/Config/IPFW и Lab restoration. **Никаких production-частей #1228 не переносить автоматически**; они остаются историческим образцом поведения и тестовых случаев. Документационные требования уже перенесены в действующие ТЗ/правила через последующие объединённые PR; повторная запись старой редакции недопустима.

## 2. Полная инвентаризация 12 файлов #1228

| Файл старого PR | Решение | Сохраняем / перерабатываем / отбрасываем |
| --- | --- | --- |
| `.github/workflows/ci.yml` | **REWORK** | Сохранить намерение обязательного DEV-065 CI. Не переносить команду запуска старого helper-only теста без нового реального RED→GREEN и native gate (S02/S03/S11–S17). |
| `Makefile` | **DROP** | Старое изменение `PLUGIN_REVISION=120→121` не применимо к `main _129`. Для новой ветки использовать только следующий уникальный `_130`, без выдачи `.pkg`. |
| `docs/PROJECT_PRINCIPLES.md` | **KEEP CONTRACT / DROP OLD DIFF** | Сохраняем единый `zapret_service.sh` как владельца физического lifecycle (DEV-065), original FD9 и запрет второго writer; это уже нормативно в `main`. Не перезаписывать действующие DEV-066–071 старой редакцией. |
| `docs/PROJECT_STATE.md` | **DROP OLD HEAD / KEEP EVIDENCE** | Убрать как текущую дату/статус кандидата `_121` и заявленную частичную готовность; сохранить старый факт только исторически. Указать `main _129`, S01 audit, следующий S02 и отсутствие нового пакета. |
| `docs/ROADMAP.md` | **REWORK** | Сохранить single-file DEV-065 цель, заменить старую очередь на действующую S00–S20; не выдавать Lab/pkg delegation за реализованный unified lifecycle. |
| `docs/START_HERE.md` | **REWORK** | Сохранить ссылку на решение, но не копировать устаревший handoff `_121`; next action — S02 route audit и S03 RED на `main _129`. |
| `docs/architecture/TZ_6v4.md` | **KEEP CONTRACT / DROP OLD DIFF** | Один FD9/один исполнитель, first-match и native Auto инварианты действуют по ТЗ_6v5; нельзя подменить актуальные five-command, manifest и WAN-first требования старой правкой. |
| `docs/architecture/ZAPRET2_CANONICAL_SERVICE_LIFECYCLE.md` | **KEEP EVIDENCE / REWORK IMPLEMENTATION** | Использовать прежнюю карту owner/callers и обнаруженные дубли как вход S02, но не утверждать, что `original_fd9_lifecycle_transition` существует в текущем коде или что Lab/pkg уже unified. |
| `docs/architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md` | **KEEP HISTORY / DROP AS ACTIVE** | Сохраняем доказательства P0–P5 и P1/P2; для исполнения использовать только S00–S20, включая V5-08 и #1223. |
| `docs/history/current/v0.6.x.md` | **KEEP AS HISTORY** | Старый `_121` — исторический не принятый source candidate; не превращать запись в текущий milestone или опубликованный пакет. |
| `scripts/test-dev065-lifecycle-routing.sh` | **REWORK TEST CASES / DROP TEST AS PASS** | Полезны cases inherited FD9, sealed Common/legacy, PREPARED/foreign, WAN-first, pkg prepare/finish и invalid action. Старый shell test через `sed` выделял функцию и подменял physical методы mocks/grep; он не доказывает native Stop/Start, owner identity, retirement, IPFW или восстановление и не переносится как acceptance. |
| `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` | **DROP PATCH / KEEP SEMANTICS** | Не переносить 38-строчный частичный helper и четыре rewired Lab/pkg вызова. Под S11–S13 спроектировать заново **один** фактический Start и Stop в этом файле, authenticated inherited FD9, process/owner/epoch/WAN/IPFW/receipt guards и все callers; S04–S10 перед этим обязательны. |

`KEEP` означает сохранение требований/доказательств, **не** cherry-pick кода. `REWORK` означает новый код или тест по ТЗ_6v5 после S02/S03 RED. `DROP` означает отказ от старого patch/версии/claim, **не** отмену пользовательских гарантий.

## 3. Негативные свидетельства старого HEAD — НЕ приписывать текущему main

- CI: `FAIL WAN-FIRST: inherited-FD9 Laboratory start can bypass WAN-first before runtime`.
- Реальная схема3 на disposable native: `CANARY_RUNNING_SCHEMA3_EDITED_APPLY_REFUSED`, `original_config_child_rc69` / `OriginalLockRefused`.
- Native protected pkg update: `INTERRUPT_PRE_PKG_PREPARE_FAILED`.
- Историческая проверка PR title/version после продвижения `main`: stale source candidate / non-forward revision.
- У старого CI также фиксировались red jobs на PHP lint, но нельзя выводить новый root cause только из их состояния.

Эти свидетельства имеют смысл как **адресные RED-кейсы** в S03 и негативные native gates S14/S17. Их воспроизводимость на `main _129` ещё **не проверена** и не должна объявляться текущим дефектом без нового факта. Старые прогоны и комментарии: [#1228](https://github.com/Tolian82/os-zapret2-restyle/pull/1228), [#1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225).

## 4. Обязательные проверки, перенесённые в будущие этапы

| Этап | Требование к будущему тесту, а не текущий PASS |
| --- | --- |
| **S02** | Полный физический route map: Strategies/Voice кнопки и Apply, System Services, Boot, Lab, `pkg-update`, upstream `Установить версию`, Auto Restart и callbacks; какой именно original FD9, где выбирается Common/Voice/legacy и что реально делает process/IPFW. |
| **S03** | Настоящие fail-first RED на этом исходнике: inherited FD9 + no nested reacquire, PREPARED/foreign/invalid owner refusal, early WAN, no-engine/no-manifest, исходный native argv/profile parity, same-owner terminal verification. |
| **S04–S10** | Пустая установка без двигателя, WAN-only/Prestart Lab G05→G08, read-only `status --json` + structured bounded errors, XML model, deterministic pure compiler, sealed reference-only JSON, original WAL/FD9/rollback. |
| **S11–S14** | Одна реализация physical Start/Stop в `zapret_service.sh`, пять публичных команд, guarded explicit `--force` и no-write `--help`, все callers на том же владельце; Apply semantic diff: SAVE_ONLY/START/STOP/NO_CHANGE/RELOAD/RESTART/REFUSE, без скрытого Stop на Reload и без fallback restart после ошибки. |
| **S15–S16** | Lab #1224 RUNNING→RUNNING и STOPPED→STOPPED включая timeout/cancel; Auto #1223 проверять на заранее имеющемся native событии или fixture от native inbox до Found/managed без Apply/Restart. |
| **S17–S20** | Disposable native OPNsense exact-head, только собственный IPFW 19000–19099/19100–19131 (65534 и future reserved не трогать), затем после gates отдельный immutable testing `.pkg` и owner-live acceptance. |

Защита: never test documented upstream engine reread/SIGHUP/Autohostlist properties как гипотезу (DEV-069); проверяем только свою интеграцию. Ни второй writer Config, ни новый daemon/observer/SQLite, ни SIGSTOP, ни широкие IPFW sweep, ни принудительные остановки для Auto не допускаются. `#1210` external OPNsense firewall flush recovery — отдельная открытая проблема, не часть принятого IPFW numeric scope #1237.

## 5. Решение S01 и состояние следующего этапа

**S01 disposition: complete as review; code migration: zero.** Исходный Draft #1228 уже CLOSED unmerged. Для будущих S02/S03 используем **одну** новую ветку `feat/tz6v5-s01-s02-lifecycle-audit` от *точного* объединённого `main c7167b0c`, source-only candidate `_130`; не держим параллельные product PR с одинаковой ревизией, не восстанавливаем устаревшую ветку и не переносим old helper. Текущее изменение содержит только документацию и номер ревизии, **не** новый Start/Stop/Reload и **не** новую сборку.

**Gate S01 GO:** 12/12 путей классифицированы, старые failed gates перечислены, новый исходный базис и один рабочий branch определены, сохранены инварианты и явная передача в S02. **S02/S03 остаются NOT RUN** до реальной route inventory и fail-first tests; все S04–S20 остаются отдельными gate. #1223/#1224/#1225 остаются OPEN. Рабочий OPNsense владельца не затронут.
