# ТЗ_6v5 S03d — наблюдаемый RED старого PID/FD9/force, без доступа к реальному движку

**Исходная база:** merged `main f58c45f4ec82a22add5e4d1cf25ed9289f3f66b9` / `v0.6.5_135`, после [#1244](https://github.com/Tolian82/os-zapret2-restyle/pull/1244) (нативный G05→G03→G08 STOPPED→STOPPED PASS). **Кандидат исходников:** `v0.6.5_136`; **`os-zapret2-restyle-0.6.5_136.pkg` не собран/не опубликован**, пользовательская OPNsense (_117 по последнему подтверждению) не затронута. Следуем [плану S03](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md) и [ТЗ V5-15/V5-16](TZ_6v5.md). Тесты относятся к **старому коду**, не реализуют новый операторский force.

## Подтверждённые наблюдения исходников до нативного теста

- Настоящий `src/opnsense/scripts/OPNsense/Zapret/backend/common.sh::common_process_matches` получает PID, делает `kill -0` и сверяет строку `ps -p PID -o command=` с ожидаемым исполняемым путём; **birth/epoch, sealed generation и FD9-owner не аттестуются этим helper**.
- Настоящий `backend/launcher.sh::launcher_stop` молча удаляет stale/mismatched PID-файл, делает обычный `kill PID`, после тайм-аута `kill -KILL PID`, удаляет PID-файл — **без повторной аттестации PID+birth/epoch перед KILL**. Не считать это утверждённой force-эскалацией!
- `zapret_service.sh` имеет публичные `start|stop|restart|status` (и legacy internal verbs), но **ещё не имеет корректной V5-15/V5-16 обработки `--force`, `reload`, `--help`**. Вызов `start --force` сейчас не доказывает осознанное разрешение оператора.
- Завершённый [S03c2](ZAPRET2_TZ6V5_S03C2_AUTH_NATIVE_PRESTART.md) проверил только реальный STOPPED prestart Lab. Force/PID/FD9 не был его целью.

## Первые native NO-GO — установленный дефект фикстуры, не force

Первая попытка [#45111559386](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45111559386) на `de9a398c` прервалась **до сигнала**: `S03D_NATIVE_PS_DID_NOT_MATCH_CONTROLLED_SLEEP`. Во второй попытке [#45111935530](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45111935530) на `0ae51b9d` был получен реальный argv контролируемого child `/bin/sleep 90`, однако `common_process_matches` всё равно отказал.

**Проверенная причина:** в `backend/common.sh` стандартный `COMMON_PS_BIN` равен штатному `SCRIPT_DIR/process_query.sh`, а на чистом госте исходный `SCRIPT_DIR` не является installed `/usr/local/opnsense/...`. Сам helper не смог найти исполняемый native query adapter. Формат FreeBSD `ps` **не был первопричиной**. Исправлен **только тест**: `source_shell` связывает настоящий `SCRIPT_DIR`, `ZAPRET_PROCESS_QUERY_BIN` и `COMMON_PS_BIN` с исходным production `process_query.sh`, предварительно проверяет его исполнимость и продолжает использовать реальный FreeBSD `ps`/shell `kill`. Не подставлять stub/mock ps и не считать отказ helper доказательством force-безопасности. Текущий exact-head CI PENDING.

Third native [#45112537151](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45112537151) on `f41635b2`: real common→process_query→launcher PID stage progressed; FD9 stage failed with `S03D_REAL_FD9_BUSY_FORCE_DID_NOT_REFUSE`. The fixture now requires a positive uncontended **actual** `/usr/bin/lockf` control before treating a failed contender as proof of a held lock, and reports bounded actual `rc`/busy-message/elapsed on mismatch. No source/force product change; exact-head native CI PENDING.

**Точный FD9 fixture fix (FreeBSD lockf):** official [lockf(1)](https://man.freebsd.org/cgi/man.cgi?manpath=FreeBSD+15.1-RELEASE&query=lockf&sektion=1) distinguishes `lockf file command` from **`lockf -s -t seconds fd` without command**. Previous test mistakenly used `lockf -s -t 0 9 /bin/sleep`, thereby locking relative file named `9`, NOT inherited fd9; therefore its BUSY result was invalid even with a positive control of the same wrong form. Both positive check and competing check NOW use exact `lockf -s -t 0 9` no-command FD form; shell holder retains fd9 while its test-owned sleep runs. Product service uses the same FD-only syntax. No claim of an FD9 product defect; new exact-head CI PENDING.

## Реальный исполняемый тест, без макета `launcher_stop`

[Сценарий `test-tz6v5-s03d-pid-fd9-force-red-native.py`](../../scripts/test-tz6v5-s03d-pid-fd9-force-red-native.py) вызывается в **существующем** [P2e disposable OPNsense 26.7 CI](../../.github/workflows/p2e-original-shared-build-native.yml), до любой установки upstream. Перед действиями проверяет: **FreeBSD/root/`GITHUB_ACTIONS=true`/`ZAPRET2_S03D_DISPOSABLE_NATIVE=1`**, отсутствие реального `dvtws2`, PID файла и Lab-worker. На Linux неизменно отказывает **до** запуска каких-либо subprocess или файловых изменений: `S03D_FREEBSD_ROOT_ONLY`.

Тест запускает и source-ит **оригинальные** `common.sh`, `launcher.sh`, вызывает **реальные** `common_process_matches` и `launcher_stop`, без `sed` extraction и переопределения `kill/ps`. Для контроля создаёт **ровно один собственный** `/bin/sleep 90` через `subprocess.Popen`, запоминает PID и в `finally` завершает **только этот свой дочерний процесс**. Путь `DVTWS_BIN=/bin/sleep` устанавливается **только в изолированном source-helper** и означает демонстрацию недостаточности «совпало имя/exe» без sealed owner; в **обычном production `zapret_service.sh` DVTWS_BIN остаётся каноническим фиксированным путем**. Таким образом демонстрируется RED helper, **не** имитируется реальное захватывание чужого процесса маршрутизатора и **не** заявляется полный V5-15.

| Негативный вход в прежний исполняемый код | Наблюдаемый expected RED | Требование будущего GREEN |
| --- | --- | --- |
| Тестовый живой PID, exe специально не совпадает | Legacy `launcher_stop` не посылает сигнал, но удаляет непризнанный PID-файл и возвращает 0 | Точная классификация `FOREIGN` + отказ, не скрывать следы |
| Тестовый живой PID, совпадает путь `/bin/sleep`, но **нет** sealed owner/epoch/birth | Legacy `launcher_stop` адресно отправляет TERM **только тестовому child**, удаляет файл и возвращает 0 | Новый executor обязан отказать без настоящего sealed owner/epoch и убедиться в PID+birth, argv |
| Stale PID = 99999999, файл только в `/tmp` | Старый helper молча удаляет stale file, не сообщает `FORCE_OWNER_UNVERIFIED` | Строгое различение missing/stale/reused/foreign, без произвольной cleanup |
| `zapret_service.sh --help` и `reload --help` реальным original `/bin/sh` | Старый CLI возвращает usage rc64 (expected RED) | Read-only help rc0 без FD9/Config/IPFW |
| **Исходный FD9 действительно занят** тестовым `lockf` над приватным файлом в `/tmp`, `zapret_service.sh start --force` | Старый wrapper ждёт lock timeout и возвращает 75, ничего не запуская | Флаг никогда не обходит original FD9; в будущей реализации owner-force проверяется только под ним |

**Запреты в коде:** ни один чужой/системный PID не передаётся в `kill`; `stop --force` на действующем engine не вызывается; `/var/run/dvtws2.pid` и реальный `/var/run/zapret2-lifecycle.lock` не открываются на запись; IPFW только `-q list` до/после; Config только SHA; никаких Config writer, `pkg add`, Start успешного движка, SIGSTOP/SIGCONT или IPFW mutations. Реальный `start --force` допускается **только при заведомо удерживаемом приватном FD9**, так что production dispatcher недостижим. `lockf` и `ps` — настоящие FreeBSD утилиты.

## Gate и оставшиеся риски

- До exact-head CI следующий маркер только **ожидается**, а не объявлен PASS:
```
S03D_ACTUAL_SOURCE_PID_FD9_EXPECTED_RED=PASS
S03D_V5_15_FORCE_IMPLEMENTATION_NOT_CLAIMED=1
S03D_ACTUAL_FOREIGN_ROUTER_PID_NEVER_USED=1
```
- **GO для S03d** означает, что на disposable FreeBSD подтверждён старый unsafe RED плюс правильный реальный FD9 отказ и нет изменения Config/IPFW. Это **не** `--force` в продукте.
- **NO-GO для полного S03:** новый управляющий V5-15 требовательно должен иметь TERM→timeout→повторную PID+birth/exe/argv/epoch аттестацию→адресный KILL только своего, `INCOMPLETE` при невозможности остановки, no second engine. Отдельно остаются полноценная таблица строгого CLI Help/JSON/Reload и RU/EN lifecycle, #1224 RUNNING→RUNNING Lab restore, #1223 learning Found, full effective action diff. До этого **S04–S20 не начинать**, никакой S19 testing release.
