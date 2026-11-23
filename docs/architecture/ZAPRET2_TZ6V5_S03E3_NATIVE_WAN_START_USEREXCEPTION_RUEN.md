# ТЗ_6v5 S03e3a — настоящая pre-dispatch ошибка Start из native WAN → Chromium RU/EN

**23.11.2026 · кандидат исходников `v0.6.5_139` · base `main a54659bd` (`_138`, [PR #1248](https://github.com/Tolian82/os-zapret2-restyle/pull/1248) MERGED).**

## Цель и ограничения

Заполнить доказательный пробел S03e2: там HTTP 503 для Start/Stop был перехвачен Playwright и не приходил от PHP. Здесь **только Start при отсутствии сохранённого WAN** должен вернуть реальный `UserException` из *установленного* `ServiceController::startAction()` → OPNsense HTTP → реальный `general.volt` → видимый диалог в двух локалях. Stop/Restart, ошибки после dispatch, Lab/Auto/force/reload **не объявляются проверенными**.

### Предохранители до сетевого POST

- Только fresh disposable OPNsense 26.7 native clean install, `GITHUB_ACTIONS=true`, `ZAPRET2_STAGE5_BROWSER_WAN=1`, root, нессылочный уникальный CI SSH marker; последнее условие дополнительно проверено в существующей настройке гостя.
- В собственном госте под `/usr/local/opnsense/...` проверить действительный метод `startAction()` (вызов `configdRun('zapret wan_preflight')`, ветку `wan-required` и исключение **раньше** `parent::startAction()`). Затем исполнить **реальный** `/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh require` и требовать ровно `wan-required`, rc 0. Это read-only проверка модели, штатного XML, IP-адреса интерфейса; никакой фальшивой WAN-ошибки или замены PHP-функции.
- `scripts/test-tz6v5-s03e3-native-wan-refusal.py --prepare` сохраняет только SHA256 байтов `/conf/config.xml` и tuple `(rc,stdout,stderr)` реального `/sbin/ipfw -q list` и утверждения об отсутствующем процессе `dvtws2`/supervisor. На `--verify` требует полное совпадение и повторный `wan-required`. Чистая проверка не модифицирует XML, FD9, kernel, runtime или старые списки.
- В `scripts/stage5-browser-wan.py --s03e3-{en,ru}-browser` синтетическими являются **только read-only** `/api/zapret/service/runtime` и `resourcesStatus`, чтобы показать кнопку в чистой установленной системе без движка. **Маршрут `/api/zapret/service/start` не перехватывается**. Ожидаются HTTP отказ, точное allowlisted WAN UserException, видимое сообщение и заголовок RU/EN. Любой неожиданный Start/Stop/Restart запрос, успех или другой HTTP отказ → NO-GO.
- Для каждого языка: отдельно locale `en_US`/`ru_RU` штатным существующим **disposable-only** `p3-native-profile-locale.php` (один OPNsense Config writer **вне** snapshot), native prepare → Chromium → native verify. После этого возвращаем язык в EN и запускаем прежнюю проверку WAN-only нижнего Apply, без потери прежних G05/P3 свидетельств.

### Иерархия свидетельств и приёмка

| Объект | Что может быть PASS | Что не доказано |
| --- | --- | --- |
| Действительный native `wan_preflight` + installed PHP `UserException` | Неподменённый HTTP Start ответ и диалог RU/EN на чистом госте; предохранительный отказ до physical dispatcher, exact Config/IPFW invariants | Успешный физический Start, ошибка при уже выбранном WAN |
| Старое S03e1 CLI FD9 expected RED, S03e2 intercepted HTTP | Независимый регрессионный baseline | Новый CLI/force/reload и настоящие ошибки Stop/Restart |
| S03 e3a | **PENDING exact-head disposable native CI**; до PASS нельзя присвоить GO | Полный S03 всё ещё **NO-GO** |

**Никакого пользовательского `.pkg`**; CI вправе собирать одноразовый package, который не публикуется. Рабочая OPNsense `_117` не затрагивается. Код `src/`, FD9, IPFW, package lifecycle, WB/Commit, пользовательские списки не меняются. Следующая итерация S03 должна отдельно доказать Stop/Restart producer delivery при неизменённом старом владельце, не подменяя её этим WAN кейсом.

Связанные: [ТЗ_6v5](TZ_6v5.md), [S03e2](ZAPRET2_TZ6V5_S03E2_VOICE_CONTROL_RETIRED_GUI_LOCALE.md), [план S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), [Issue #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225).
