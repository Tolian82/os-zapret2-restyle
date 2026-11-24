# ТЗ_6v5 S10a — staged immutable root рядом с original release, без циклического seal

**Этап:** [S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319), вход [S09 GO #1316](https://github.com/Tolian82/os-zapret2-restyle/issues/1316), канон [S00–S20 §S10](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md). Это **внутренний атомарный PREPARED-кандидат**, а не физическая активация S10b/c и не S11 Start.

## Почему root не помещён в release

Исходный `shared_apply_seal.py` закрывает SHA всех файлов `work/release/**`, `candidate.xml` и `plan.json` одним `work/bundle-seal.json`. Схема S09a требует SHA точных **байтов** оригинального seal внутри каждого reference root. Если поместить root внутрь `release`, то seal содержит SHA root, а root содержит SHA seal: хеширование циклично и неизменно неразрешимо без изменения контракта. Создавать «второй seal», отдельную mutable JSON authority или исключать root из исходного inventory нельзя.

**Утверждаемый S10a layout (пока staged):** `shared-work/<generation>/release/` — один исходный sealed immutable inventory; `shared-work/<generation>/bundle-seal.json` — **единственный оригинальный** seal; `shared-work/<generation>/manifest.json` — жёстко аттестуемая immutable sibling-root, которая ссылается на SHA `bundle-seal.json`. Путь/ID владельца определяется только существующим `shared_apply_operation.py` при `PREPARED`, а не приходит из манифеста. Root вне исходного seal не означает «доверять» root: при каждом read требуется заново проверить exact original journal+sealed candidate+native source+S08c/S08d/S09. Переход к committed и проверка активного root — **не** часть S10a.

## Реальная граница и записи

`neutral_root_stage.py` добавляет приватный `stage_manifest` с обязательным `voice_ipfw_adapter.require_lifecycle_lock()` (тот же реальный FreeBSD root FD9), без нового CLI, GUI, writer Config или journal. Он принимает `RootCandidate` только из S09a, exact operation ID, текущий `PREPARED` original journal без Found intent, original `bundle-seal.json` и физическую S09b attestation, подтверждённые S08c native parity + S08d fingerprint. Сопоставляет оригинальный sealed `plan.json` с оригинальным журналом: `page`, `dependencies/base`, `changed_fields`, тип `candidate`; `candidate`-digest в журнале создан **исходным PHP `VoiceSettingsSnapshot::digest`**, и **не равен** SHA `candidate.xml` по определению — второй сериализатор PHP snapshot в Python **запрещён**.

Внутренний writer пишет не более 16 KiB в `.manifest.json.pending` с `O_EXCL`, `O_NOFOLLOW`, owner и `0600`, затем `fsync(fd)`, fail-if-exists `linkat` в `manifest.json`, `unlink` pending, `fsync(directory)`. После записи повторно проверяются original journal, source bytes, original seal, sha/режим/owner/inode root и отсутствие смены директории. Повторно использовать generation нельзя; при crash до/после hardlink незавершённый pending блокирует чтение/повторную запись. Никакой silent cleanup или rollback без исходной транзакции.

`attest_staged_candidate` — только чтение `PREPARED` и строгая проверка; возвращаемое `PreparedRootReceipt` всегда `authorization=NONE`, `physical_transition_allowed=False`, `promotion_allowed=False`. **Root не является активным и не указывает службе Start/Stop/Reload.** Вызов производственного writer из `zapret_service.sh` на этом шаге намеренно ещё не подключается: атомарный native Apply/rollback и восстановление старого owner остаются S10b/c.

## Проверки и честная приёмка

`scripts/test-tz6v5-s10a-root-stage.py` — 9 локально исполняемых сценариев на тестовом owner/ожидаемом S09b файле: list, auto, replay, collisions, pending/symlink, stale/mutated journal, mismatched original plan dependency, corrupted release, no FD9, tamper after stage, read-after PREPARED→ACTIVATING refusal. Отдельный CI-only сценарий использует **настоящий S08c→P2e original generator** и original seal для `list|auto`. Локальный S0 проверяет Python компиляцию и 9/9 контрактов; native producer нельзя выполнить вне полной исходной VM/репозитория и это **отдельное** CI evidence, а не локальный PASS.

**S10a GO ≠ S10 GO**. Для полного S10 ещё нужны original FD9 invocation in actual original service, exact staged root passing immutable references through real owner, atomic install/promote, PREPARED/ACTIVATING/ACTIVATED/Config-save uncertainty crash recovery, rollback P1 CAS and runtime/IPFW reconciliation. Никаких новых сигналов, процессов, IPFW/Config изменений; пользовательский маршрутизатор и публичный `.pkg` не трогаются. WAN-only Save и prestart Lab не получают новый блокирующий manifest prerequisite.
