# ТЗ_6v5 — S03c1: native-disposable Strategy Lab WAN-first / engine-second refusal before Job

**База:** принятый `main v0.6.5_133` / `72027e4b8d120466ae55d81aa4e4cfb278b0154d`. **Кандидат:** `v0.6.5_134` — тесты, CI и документация; файл `os-zapret2-restyle-0.6.5_134.pkg` **не создавался и не публиковался**. Владелец устройства последний раз подтвердил установленный `_117.pkg`; реальная OPNsense не изменялась. Исходные контракты: [S00–S20 / S03](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), [проверка G05](../verification/G05_WAN_ONLY_NATIVE.md), [G08](../verification/G08_PRESTART_LAB_NATIVE.md), [S02 route map](ZAPRET2_TZ6V5_S02_ACTUAL_LIFECYCLE_ROUTE_AUDIT.md).

## Фактический путь, который тестируется

[Новый исполняемый S03c1 probe](../../scripts/test-tz6v5-s03c-prestart-lab-native.py) запускает **оригинальный production** `/bin/sh src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh start ...` из неизменённого `src/`. Через `MODULE_DIR` он читает **реальные** `strategy_lab/{common,state,target,firewall,runtime,udp_input,retention,launch,query}.sh`, пользуется настоящими `/usr/bin/lockf` и `/usr/local/bin/jq` disposable OPNsense 26.7. Применяется существующий `start_job()` в `strategy_lab/launch.sh`, НЕ извлечённый `sed` mock-helper.

**Ровно одна подставляемая граница:** `SCRIPT_DIR/wan_preflight.sh require` — тестовый исполняемый файл в одноразовом `/tmp`, который возвращает предписанный результат `wan-required`, `wan-invalid`, `wan-unavailable` либо `wan-ready`. **Это не исходный native PHP/OPNsense Config WAN resolver и не реальная запись WAN.** Все другие функции Lab, preflight order, RU/EN ответ и отсутствие Job проверяются на production shell. Данные о том, откуда пришёл ответ native WAN, **не заявляются**. Для истинного G05/F5/G08 необходим отдельный полноценный authenticated HTTPS/Config/engine-second/native Job тест после создания будущего launcher, как написано в ТЗ.

**Предохранители до любого исполнения:** `FreeBSD + root + GITHUB_ACTIONS=true + ZAPRET2_S03C_DISPOSABLE_NATIVE=1`, отсутствие установленного `/usr/local/etc/zapret2/binaries/my/dvtws2`, `/var/run/dvtws2.pid`, нормального dvtws2 и Lab-worker в реальном process census; доступность реальных `lockf`/`jq`. Все `STRATEGY_LAB_RUN_DIR`, `JOBS_DIR`, `LOG_DIR`, `LOCK_FILE` — частные `/tmp` пути. `DAEMON_BIN`, `WORKER_SCRIPT`, `TRANSACTION_SCRIPT` указывают на **неисполняемый отсутствующий файл**, чтобы даже при дефекте предиката не запустить фоновую работу. Нет `pkg add`, Config writer, install/Start/Stop/kill, IPFW mutation. **Никаких запусков на маршрутизаторе владельца.**

## Матрица actual CLI refusal

| Case | WAN boundary (изолированная подстановка) | Lab / язык | Ожидаемый реальный ответ | Exit |
| --- | --- | --- | --- | --- |
| missing_standard_ru | `wan-required` | Standard RU | `reason:wan-required`, «Укажите WAN интерфейс» | 64 |
| missing_extended_en | `wan-required` | Extended EN | `reason:wan-required`, «Select a WAN interface» | 64 |
| missing_extended_ru | `wan-required` | Extended RU | такой же RU reason, без Job | 64 |
| invalid_standard_en | `wan-invalid` | Standard EN | `reason:wan-invalid` | 64 |
| preflight_unavailable | `wan-unavailable` + nonzero | Standard EN | `reason:wan-unavailable` | 69 |
| engine_missing_standard_ru | `wan-ready`, engine отсутствует | Standard RU | `reason:engine-not-installed`, «Служба zapret2 не установлена» | 64 |
| engine_missing_extended_en | `wan-ready`, engine отсутствует | Extended EN | `reason:engine-not-installed`, EN message | 64 |

**Намеренно недопустимая цель** `!invalid_target` во всех семи запросах проверяет **приоритет WAN/движка до валидации цели**, но не подразумевает создание Job. После каждого запуска обязательны: точный JSON `status:error,reason,message`, отсутствие любого `job.*`, `active.job`/`latest.job`, неизменный SHA-256 native `/conf/config.xml`, byte-exact `ipfw -q list` (включая отказ при unloaded module), отсутствие normal PID и engine, отсутствие неожиданного stderr. Запускаются штатные модули и real native shell, не физический Lab search. Локальный real WAN resolver отдельно имеет существующие исходные [PHP-кейсы](../../scripts/test-wan-first-preflight.php) и [G05 route cases](../../scripts/test-g05-wan-route.sh), но **не связаны как один installed HTTP свидетель** данным тестом.

### Вход в CI и результаты

S03c1 подключён к уже существующему [P2e disposable OPNsense CI](../../.github/workflows/p2e-original-shared-build-native.yml) **до** скачивания/компиляции upstream в том же госте. Linux preflight специально вызывает fixture с явным opt-in и **требует отказ `S03C_FREEBSD_ROOT_ONLY`** до любых побочных действий. FreeBSD root выполняет семь реальных отказов.

Ожидаемые маркеры:
```
S03C1_GENUINE_LAB_ENTRYPOINT_ON_DISPOSABLE_NATIVE=PASS
S03C1_G05_G08_FULL_INSTALLED_NATIVE_NOT_CLAIMED=1
S03C1_PHYSICAL_START_STOP_OR_FORCE_NOT_TESTED=1
```

**Gate S03c1:** только реальный exact-HEAD CI PASS с семью результатами. При отказе либо неожиданном изменении файла/правил — FAIL, не удалять проверку и не подменять native исходником/grep. Этот checkpoint сам по себе **не закрывает весь S03**.

## Ещё не выполнено: S03c2 и остальной S03

1. Полный **native G05→G03→G08**: реальный PHP OPNsense Config и authenticated WAN-only Save при Enabled OFF, пустых Strategy/YouTube/User, без upstream; затем установка upstream без первого обычного Start; Standard RU/Extended EN **реальные Job с Stage90 STOPPED→STOPPED** и актуальные firewall boundaries/owner receipts. Старый [G08 PASS 09.11](../verification/G08_PRESTART_LAB_NATIVE.md) — историческое свидетельство старой архитектуры, а не PASS единого будущего launcher. **Новый testing `.pkg` не выпускать до S19**, поэтому нельзя маскировать отсутствие установленного нового кода историческим G08.
2. Нативные строгие `start|stop|restart --force`: exact PID/birth/exe/argv/epoch, PREPARED/foreign/FD9 BUSY, гарантированный no-kill для чужого, без второго dvtws2; исходный `launcher_stop` с SIGKILL не есть новая V5-15 реализация. Только контролируемые disposable процессы, не владелец.
3. Реальные `--help`/invalid CLI, terminal rc/stage + RU/EN **только** Start/Stop/Restart/связанных Apply/Lab/pkg/Boot; effective Reload/Restart отказ и no hidden fallback, exact V5-17 owner-active IPFW inclusive bounds.
4. #1224 Lab Stage90/99 RUNNING→RUNNING/STOPPED→STOPPED, #1223 Auto Found — **реальные** входные события или проверенные fixtures, не придуманное поведение upstream. До этих доказательств **S03 NO-GO, S04–S20 NOT RUN.**

**Статус:** S03c1 — instrumented native refusal baseline в CI; это ожидаемый **GREEN старого безопасного preflight**, а не новый expected RED для отсутствующего launcher и не полноценно принятый G05/G08. До получения exact-head CI результат: **PENDING**.
