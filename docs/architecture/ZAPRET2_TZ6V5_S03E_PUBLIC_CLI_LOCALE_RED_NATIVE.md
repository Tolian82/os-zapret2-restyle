# ТЗ_6v5 S03e1 — действительный public CLI options/FD9/Status RED + узкий RU/EN lifecycle route audit

**Дата / исходная база:** 23.11.2026; merged `main aa3e29937515e6238d2014dfa092fb736a463f15` / source `v0.6.5_136` (S03d, [#1245](https://github.com/Tolian82/os-zapret2-restyle/pull/1245)). Кандидат `v0.6.5_137` в ветке `feat/tz6v5-s03e-public-cli-locale-red`; это **только native/source RED оснастка и документация**. Нет новой реализации публичного CLI/force/reload, нет изменений production `src/`, нет опубликованного `_137.pkg` и нет действий на owner OPNsense (последняя установленная подтверждённая `_117.pkg`).

Основание: [S03, G0](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), [ТЗ_6v5 §5.3–5.6, 7.1](TZ_6v5.md), [S02 actual lifecycle route audit](ZAPRET2_TZ6V5_S02_ACTUAL_LIFECYCLE_ROUTE_AUDIT.md), [S03d actual native PID/FD9 RED](ZAPRET2_TZ6V5_S03D_PID_FD9_FORCE_RED_NATIVE.md).

## 1. Scope: настоящая исполняемая public CLI, без риска Start/Stop

Новый `scripts/test-tz6v5-s03e-public-cli-locale-red-native.py` работает в двух **явно раздельных** режимах:

- `--source-routes`: читает оригинальные `ServiceController.php`, `general.volt`, `voice.volt`, `actions_zapret.conf`, `zapret_service.sh` и проверяет точные producer→consumer пути. Это **только source-level** свидетельство действующих RU/EN сообщений и старых пробелов; никаких fake GUI-clicks, тестовых gettext translations, мокового backend или вывода native acceptance.
- `--native`: разрешён **только** FreeBSD root + `GITHUB_ACTIONS=true` + `ZAPRET2_S03E_DISPOSABLE_NATIVE=1`, установленная OPNsense структура; **до** появления любого upstream `dvtws2`, его PID/worker. Исходный `zapret_service.sh` реально запускается `/bin/sh` с оригинальными backend-модулями, системным FreeBSD `/usr/bin/lockf`; наблюдение IPFW — только `/sbin/ipfw -q list` и SHA существующего `/conf/config.xml` (до/после, неизменность). Только временный приватный FD9 в `/tmp`, никогда `/var/run/zapret2-lifecycle.lock`.

**Вызовы способные изменить engine (`start|stop|restart`) разрешены тестом ТОЛЬКО при реально удерживаемом FD9**, подтверждённом двумя native контрпроверками: `/usr/bin/lockf -s -t 0 9` без команды (положительный uncontended), затем такой же contender возвращает BUSY, пока отдельный test-owned `/bin/sleep` удерживает FD9. Лишь после этого 9 команд запускаются параллельно и должны вернуть `rc75` *до* dispatcher; никаких Stop/Start, PID/Config/IPFW, force-KILL, второго процесса. В `finally` убираются исключительно дочерние тестовые процессы и приватный temp каталог. Проверки помимо этого не используют сигналы или ошибки поведения upstream.

**First exact-head native run [#45114745111](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45114745111):** S03e1 source-only/negative Linux gate PASS, S03d native PASS; S03e native preflight **stopped before CLI** at `S03E_IPFW_READ_FAILED`. On cold OPNsense before any engine/module install, `/sbin/ipfw -q list` may return nonzero. Test-only fix stores complete `(rc, stdout, stderr)` before/after and requires exact equality (same approved S03d approach), never requires `rc0`, never loads the IPFW module or mutates rules. This was a fixture NO-GO, not CLI RED/native success. New exact-head CI PENDING.

## 2. Матрица ожидаемого поведения старого кода (RED, не новый контракт GREEN)

| Исходный public CLI path | Фактический старый expected RED | Нормативный будущий GREEN |
| --- | --- | --- |
| `--help`; `reload --help`, `reload --check`, `reload --check --json`, `reload --force`, unknown verb | usage `rc64`, без открытия FD9 | help `rc0` и `reload --check` typed read-only; `reload --force` / unknown `rc64` |
| `status` на cold guest | `rc1`, `zapret is not running`; открывает приватный FD9 | совместимый plain status, без побочных записей |
| `status --json`, `status --help`, `status --force`, `status --json --json`, `status --unknown` | **тот же** текст, rc и stderr, что и plain `status`; параметры не проверяются; `--json` **не JSON** | отдельный JSON/read-only и help `rc0`; illegal/duplicate options `rc64` до FD9 |
| `start|stop|restart --help`, дублированный `--force`, unknown flags, `stop --check` | При гарантированно удерживаемом original FD9 старый CLI ждёт timeout и отвечает `rc75` (а не мгновенный `--help rc0` или invalid `rc64`) | строгий argv parser действует **до** original FD9, возврат `rc0/64` без удержания lifecycle lock |
| `status --help` при занятом FD9 | old `rc75`, реальный status заходит в lock | гарантированное `rc0` без FD9 |
| Control: Config/IPFW, engine/PID | **хеш/снимки до-после идентичны**, настоящий engine отсутствует | при отказах всегда без изменения внешнего state |

**Условие CI:** старые expected-RED должны реально воспроизвестись на disposable FreeBSD; если новая реализация начала соблюдать контракт, старый expected-RED тест обязан FAIL и требует осознанной замены на позитивные GREEN-тесты. Никаких `unit mocks/grep` как доказательства физического процесса или GUI клика.

## 3. Узкий реальный исходный RU/EN producer→consumer маршрут

- **Strategies Start/Stop:** `general.volt` динамически POST `/api/zapret/service/{start|stop}`, при ошибке использует `localizeStrategiesApplyError` и RU/EN fallback. **Доказуемый пробел:** нынешний fallback для **обоих** действий говорит «Не удалось запустить Zapret2…» / “Zapret2 could not be started…” даже если действие было `stop`. **ADAPT** в будущем, не глобальный перевод всех UI.
- **Voice Start/Stop:** `voice.volt` POST того же endpoint, но handler использует `.always` для settled health и **не имеет `.fail` в том же callback**, значит из этого обработчика не видно явной локализованной ошибки операции; voice health отдельно обновляется. **ADAPT**, но нельзя утверждать, что другой общий GUI механизм совсем не показывает ошибку, пока не проведён настоящий GUI click.
- **API WAN-guard:** `ServiceController::startAction` `configdRun('zapret wan_preflight')`, затем `gettext` для WAN_REQUIRED/WAN_INVALID и `parent::startAction` после ready — **KEEP**. Это исходная OPNsense gettext точка; **передача в фактическую RU/EN UI** пока только source evidence.
- **Service System:** `actions_zapret.conf` реальные `[start]/[stop]/[restart]` ведут к оригинальному `zapret_service.sh`, не к другому engine. `ServiceController::reconfigureAction` использует старый stage-файл и выдаёт `UserException`; сохранённые ошибки нельзя объявлять мёртвыми до замены/теста. **KEEP/ADAPT**.
- **Lab и pkg:** текущий S03e1 не объявляет RU/EN lifecycle verification для этих контекстов и не меняет их receipts. Ни одного native GUI click, ни новой карты ошибок Start/Stop из Status не реализовано.

## 4. Встраивание и критерии

Используется **тот же** [P2e disposable OPNsense 26.7 workflow](../../.github/workflows/p2e-original-shared-build-native.yml), перед установкой upstream, после S03d. На Linux — `py_compile`, `--source-routes`, и **обязательный fail-closed native probe**, который должен дать `S03E_FAIL=S03E_FREEBSD_ROOT_ONLY` до выполнения любых subprocess/IO. Нативный PASS обозначается только после лога точного HEAD:
```
S03E_SOURCE_ROUTE_ONLY_PASS  # Linux source test
S03E_ACTUAL_ORIGINAL_SERVICE_CLI_EXPECTED_RED=PASS  # FreeBSD native
S03E_NEW_CLI_HELP_JSON_RELOAD_FORCE_NOT_IMPLEMENTED=1
```

**S03e1 GO**: exact-head real CLI RED + source route matrix, full CI success. **Полный S03 — NO-GO**: настоящая RU/EN GUI delivery по действиям Start/Stop/Restart, typed diagnostics, owned process force GREEN, RUNNING→RUNNING Lab #1224, Auto-detect #1223, complete effective-diff planner ещё не завершены. **S04–S20 NOT RUN. Никаких testing .pkg до S19.**
