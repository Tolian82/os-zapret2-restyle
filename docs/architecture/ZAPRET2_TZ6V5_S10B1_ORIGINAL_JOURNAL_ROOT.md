# ТЗ_6v5 S10b1 — единственная долговечная привязка immutable root в original FD9 operation.json

**Активный этап:** [S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319), вход S10a GO ([PR #1320](https://github.com/Tolian82/os-zapret2-restyle/pull/1320), `main v0.6.5_199 a7544ab9`) и [S09 GO #1316](https://github.com/Tolian82/os-zapret2-restyle/issues/1316). **Это S10b1, не GO всего S10 и не S11.**

## Зачем нужна привязка к original operation

S10a создал `shared-work/<32hex>/manifest.json` как защищённый sibling исходного `release/`. Он содержит SHA **оригинального** `bundle-seal.json`. Вкладывать root в исходный sealed release нельзя: получится неразрешимая зависимость root SHA ↔ seal SHA. Но sibling-root после crash должен иметь долговечную **конкретную** привязку к единственному FD9 owner: одного наличия валидного JSON и прежнего seal недостаточно для авторизации будущего перехода.

S10b1 добавляет **ровно одно необязательное поле** `manifest` в существующий `/var/db/zapret2/shared-apply/operation.json` (schema 1 остаётся прежней; legacy-журналы читаются без миграции). Оригинальный `SharedApplyOperation._persist_record` — **единственный fsynced writer**. Никаких новых файлов-журналов/SQLite/второго seal, транзакций, Config writers, процесса или новых FD.

```json
{
  "manifest": {
    "schema": 1,
    "generation": "0123456789abcdef0123456789abcdef",
    "root_sha256": "sha256-of-original-staged-root",
    "seal_sha256": "sha256-of-original-bundle-seal",
    "candidate_sha256": "original-PHP-logical-candidate-digest"
  }
}
```

Значения в примере иллюстративны; реальный валидатор требует lowercase hex `[a-f0-9]{64}`, точную генерацию `detail.id`, exact `detail.candidate`, полные ключи без extras, запрещает `found` вместе с `manifest` и отсутствие подтверждённого `PREPARED`.

## Единственный original FD9 путь

`SharedApplyOperation.bind_prepared_manifest()` — **import-only метод исходного класса, без CLI/GUI/public Apply route**. Сначала проверяет именно действующий `voice_ipfw_adapter.require_lifecycle_lock()` и текущее `prepared` без `found` и без прежнего `manifest`. Затем вызывает **уже принятую S10a** `attest_staged_candidate`, которая при каждом чтении заново проходит S09b real sealed original refs, S08c/P2e source-map parity и S08d effective input; проверяет независимые SHA оригинального seal, root, generation и PHP candidate digest. Receipt строго `authorization=NONE`, `promotion_allowed=False`, `physical_transition_allowed=False`. После проверки исходного журнала atomic fsync-замена **того же** operation.json добавляет immutable pin. Сразу после commit — повторная S10a проверка. Если процесс оборвался после fsync или postcheck отказал, binding **остаётся в PREPARED** и новая операция **не начинается**: никаких тихих удалений или false COMMITTED.

Для привязанного record **generic** `advance("activating")` возвращает однозначный отказ `immutable root preactivation gate not implemented`. `advance("restored")` допускается только из исходного PREPARED без физической мутации и сохраняет digest pin для судебной проверки. Ранние исторические журналы без `manifest` по-прежнему идут через исходный жизненный цикл, не ломая работающую установленную версию. Это **не разрешение** новой S10 физической активации по старому пути: для неё S10b2 обязан сначала включить обязательный generation gate с новой предактивационной аттестацией в оригинальный сервис.

`found`-файлы, P1/CAS/ACK, mutable managed-hostlists **не** заморожены новым полем. WAN-only Save при service OFF и независимый prestart Lab не требуют этого поля. Ровно одна реализация Config.xml writer/FD9/IPFW owner сохраняется.

## Обязательная проверка и предел GO

`scripts/test-tz6v5-s10b1-original-journal-binding.py` запускает 11 fault/unit сценариев: подготовленный root и оригинальная цель/план, exact sealed binding, повторная запись, отсутствующий FD9, неверный generation/mode/enabled/native SHA, изменённые release/root, запрет привязанного activating, допустимый prepared→restored с pin, запрет forged keys/Found mix, подмена nonauthorizing receipt и crash после оригинального fsync до postverify. CI выполняет их на **оригинальном** `shared_apply_operation.py` + S10a + S09b; локальный S0 использовал только тестовый stub original FD9/journal из-за отсутствия локальной копии full original, не выдавая stub за native acceptance. Рядом остаются настоящие S08c/P2e и оригинальная полная защитная матрица FD9.

**S10b1 GO**, если exact-head CI/FreeBSD/OPNsense and postmerge main проверены; **S10 весь NO-GO** пока S10b2 не подключит обязательные PREPARED→ACTIVATING checks с native runtime/seal/Config/IPFW предобразами, а S10c не докажет power-cut/rollback/recovery и P1 CAS. Никакой публичный `_200.pkg` не публикуется и маршрутизатор владельца не затрагивается.
