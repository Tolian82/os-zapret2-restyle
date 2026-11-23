# ТЗ_6v5 S03e3d — проверяемое завершение Stop/Restart внутри original FD9

**23.11.2026. Source-only candidate `v0.6.5_142`, base accepted `main ecaca1aa` (`v0.6.5_141`, [PR #1253](https://github.com/Tolian82/os-zapret2-restyle/pull/1253)).** Тестовый `os-zapret2-restyle-0.6.5_142.pkg` допустим только внутри disposable CI, не операторский/публичный релиз.

## RED фактического источника

[Реальная OPNsense Chromium RU/EN](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45143375706): при доказанно занятом original FD9 оба запроса Stop/Restart доходили до установленного PHP/configd, возвращали **HTTP 200** с `response=OTHER_REDACTED`, хотя ни один физический исполнитель не мог быть запущен. Кнопка Strategies Stop не показывала ошибку. Native Config/IPFW/engine unchanged. Это RED исходной ошибки, а не подтверждение успешной операции.

## Исправление с одним writer

1. Никакого второго демона/FD9 и никаких независимых файлов-журналов. Существующий `zapret_service.sh` сохраняет обычные вызовы `start|stop|restart` и привязку оригинальных FD9, Config, Native owner и IPFW. Не меняются `start`, `reconfigure`, Boot/Apply/Lab/Voice. Публичные shell/configctl `[stop]`/`[restart]` сохранены без изменения.
2. Приватные configd `[stop_verified]`/`[restart_verified]` имеют `type:script_output` и вызывают **тот же** shell и те же действия `stop|restart` только с `--configd-receipt`. Параметр удаляется **до** штатного dispatch. Никаких extra locks. Никаких параметров пользователя.
3. Внутри **уже захваченного original FD9**, после штатного результата 0, вызывается прежний read-only `shared_apply_status_service`. Точный `rc=1` (верифицированный STOPPED) для Stop либо `rc=0` (верифицированный RUNNING) для Restart выдаёт единственный allowlisted terminal marker `zapret-api-lifecycle-v1:stop:stopped` / `...:restart:running`. Выпуск маркера после снятия FD9 запрещён. Статус 2/неопределённость — rc70 без подтверждения; физический отказ/rc75 — без подтверждения. Никакого необоснованного `OK`.
4. Нативный `ServiceController::stopAction/restartAction` делает только соответствующий configd вызов и принимает один завершающий фиксированный receipt не длиннее 8192 байт (строгая регулярка). Пустой, длинный, повторный, повреждённый или иной output, включая исходный configd `OTHER_REDACTED`, становится `UserException` (в HTTP штатные OPNsense `errorMessage/errorTitle`). Сервер не выдаёт сырой stderr, IP, хосты, XML, PID или args. На успехе возвращает `response=OK,status=ok,verified=true,action,state` для совместимости.
5. Strategies GUI Stop показывает отказ с локальным RU/EN fallback, не отображает raw configd `message`. Даже HTTP 200 без `verified=true,action=stop,state=stopped` не является успехом. У Start прежний native WAN preflight отдельно (S03e3a), Voice не получает отдельную кнопку Stop. Restart — native API/System Services, не выдуманная кнопка Strategies.

## Обязательные доказательства

- Инертная shell матрица `rc0+STOPPED/RUNNING -> receipt`, `rc75/69/unknown/contradiction -> NO receipt`, исходник и GUI source без второго owner.
- **Нативная** установленная OPNsense 26.7, реально не запущенный upstream, до WAN Apply, test-only lockf занимает **original FD9** и независимый contender доказывает BUSY. Chromium EN/RU кликает настоящую Stop и вызывает настоящий HTTP Restart; мутационные URL **не перехватывать**. От обоих обязательны HTTP error, `errorMessage/errorTitle`, видимый локализованный отказ Stop и повторный неизменный SHA Config/IPFW/engine после safe drain. Старый S03e3c RED сравнивается историческим CI, но на текущем коде ожидается GREEN.
- Гарантированное физическое **положительное** завершение Stop/Restart при RUNNING и его terminal receipt пока **не подтверждены** данным холодным negative test. Сценарии не применять к рабочему маршрутизатору; отдельный native positive proof для каждой ветви Legacy/Common потребуется до полного S03 GO.
- Запрещены ложный HTTP 200, автоперезапуск движка ради тестирования, неподтверждённый Stop, SIGSTOP/SIGCONT, KILL по PID-файлу, изменение чужого IPFW, любые действия в диапазоне 19140–19200 и правило 65534.

**Кандидат S03e3d: CI PENDING.** До 4/4 exact-head PASS и native producer→consumer RU/EN — не merge. Даже после принятия этой узкой ошибки **full S03 остаётся NO-GO** (public CLI/force/reload/help + реальные Lab/Auto гейты); S04–S20 не начинать, публичный .pkg не выпускать.

[ТЗ](TZ_6v5.md) · [план](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md) · [S03e3c RED](ZAPRET2_TZ6V5_S03E3C_NATIVE_PHP_STOP_RESTART_HTTP_RED.md) · [issue #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225).
