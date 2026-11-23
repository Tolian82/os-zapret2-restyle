# TZ6v5 S03e3c — genuine PHP Stop/Restart HTTP RED, original FD9 BUSY, RU/EN

23.11.2026 · source-only `v0.6.5_141` · base accepted `main 2dcd0a45` (`v0.6.5_140`, [PR #1251](https://github.com/Tolian82/os-zapret2-restyle/pull/1251)).

## Цель и ожидаемый RED

Предыдущий S03e3b проверил **настоящий shell Stop/Restart rc75** при доказанном занятом original FD9; при этом реальный `configctl zapret stop|restart` завершился процессным rc0 и непустым ответом. Но он **не проверял PHP API, HTTPS и GUI**. Штатный OPNsense 26.7 `ApiMutableServiceControllerBase::stopAction/restartAction` возвращает `['response' => Backend::configdRun(...)]` без terminal service proof. Существующий обработчик Strategies `.done` считает HTTP success основанием только для refresh; он не выводит ошибку Stop.

**Красная проверка должна доказать** настоящий `HTTP 200` с `response: string` для *обоих* действий под реальным FD9 BUSY, и то, что GUI Stop не показывает ошибку. **Если PHP честно отвергает операцию и HTTP не 200, тест отказывается: прежний дефект не подтверждён.** Никакие HTTP-ответы Stop/Restart не перехватываются; статусный read-only endpoint разрешено искусственно показывать как installed/RUNNING исключительно для доступа к кнопке, без подстановки физического engine.

## Только одноразовая нативная OPNsense, без опасного Stop

- Тестовая VM: OPNsense 26.7, установлен точный `.pkg` из текущего PR в CI, upstream `dvtws2` отсутствует, нет supervisor, Lab job, protected update, другой active FD9/foreign owner. Сверяются оригинальный `actions_zapret.conf`, установленный `zapret_service.sh`, root/состояние файлов и уникальный test-only SSH ключ текущего VM.
- Host Chromium через локальный HTTPS-туннель `127.0.0.1:18443`; root test account VM. В госте `test-tz6v5-s03e3c-native-http-fd9-hold.py` захватывает **тот же** original `/var/run/zapret2-lifecycle.lock` дескриптором FD9 через нативный FreeBSD `lockf`, а независимый contender гарантирует BUSY до ответа `READY`.
- После READY Chromium authenticates, получает настоящую Strategies страницу; read-only `service/runtime` и `resourcesStatus` показывают кнопку Stop (upstream в VM не существует). Browser click `POST /api/zapret/service/stop` и аутентифицированный jQuery `POST /api/zapret/service/restart` идут в **настоящий установленный PHP+configd** и проверяют `HTTP 200`, ключ `response`, отсутствие GUI Stop error и строго два mutation HTTP `stop,restart`, никакого `start`. Restart — API, **не** отдельная кнопка GUI.
- Только классификация `response` как `EMPTY|OK|OTHER_REDACTED` (не stdout сырого configd, не Config XML и не args). Чередование EN и RU выполняется штатным test-only PHP locale до каждого FD9 witness, не внутри snapshot.
- FD9 остаётся занят не менее 112 секунд после capture baseline; даже при EOF/SSH hangup — drain. Требуется отсутствие ещё работающего `zapret_service.sh stop|restart`; только потом snapshot Config SHA, IPFW read SHA, отсутствие engine/supervisor совпадают. Любое расхождение/неполный ответ/недоказанное удержание FD9 — FAIL. Тестовый holder и ключ удаляются из одноразовой VM по завершении.

## Точные границы

Это **нативный producer→PHP→HTTP→GUI ожидаемый RED**, а не реализация нового lifecycle. Не выполняется Stop/Restart реально работающей службы; callback `restart` до физической ветки не проходит. `Status --json`, `--force`, `reload`, долговечный код/stage, System Services Restart и физический rollback остаются за последующими этапами. Ошибки не копируются в GUI как сырые строки.

**Реальный RED PASS, первоначальный источник:** [installed OPNsense Chromium #45142099971](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45142099971): отдельно EN и RU — Stop HTTP 200, Restart HTTP 200, оба PHP `response` = OTHER_REDACTED, сообщение Stop GUI не появляется, original FD9 BUSY доказан и Config/IPFW/engine неизменны. Прежний WAN-only Apply/F5 и P3 EN/RU регрессии PASS. Первоначальный draft #1252 **NO-GO** из-за нарушения GH-014: коммиты `_141` до увеличения `PLUGIN_REVISION`. Исправлено без force-push чистым [PR #1253](https://github.com/Tolian82/os-zapret2-restyle/pull/1253): исходный атомарный commit уже содержит `_141`; его **exact-head CI PENDING**. Это RED исходного HTTP/GUI поведения, **не** GREEN продукта.

**Текущий статус: native RED witness GO, release/merge пока NO-GO, PR только draft. Full S03 NO-GO; S04–S20 не начинать.** Ни публичного `os-zapret2-restyle-0.6.5_141.pkg`, ни изменений на рабочей OPNsense.

[ТЗ_6v5](TZ_6v5.md) · [пошаговый план](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md) · [старый FD9 RED](ZAPRET2_TZ6V5_S03E3B_CONFIGD_LOCKED_STOP_RESTART_RED.md) · [Issue #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225).
