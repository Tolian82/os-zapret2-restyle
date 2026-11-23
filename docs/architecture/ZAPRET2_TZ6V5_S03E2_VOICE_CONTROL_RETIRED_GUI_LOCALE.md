# ТЗ_6v5 — S03e2: Voice без прямой Start/Stop и action-specific RU/EN ошибки Strategies

**Дата:** 23.11.2026. **Base:** merged `main 9127b9f3`, source-only `0.6.5_137` ([S03e1 #1246](https://github.com/Tolian82/os-zapret2-restyle/pull/1246)). **Кандидат:** `0.6.5_138`, ветка `fix/tz6v5-s03e2-voice-readonly-lifecycle-locale`. `0.6.5_138.pkg` **не собирался, не публиковался и не установлен**. Owner OPNsense не затронута.

## Решение владельца (23.11.2026)

**Не добавлять отдельную ветку визуализации Start/Stop ошибки в Voice.** Отдельная кнопка «Запустить/Остановить» на странице Voice не нужна: нет независимой Voice-службы. Удалить сам `#voiceServiceControl` и его Ajax lifecycle-handler **сейчас**, не создавая другой путь управления жизненным циклом.

Это решение не отменяет единый физический Start/Stop в ТЗ_6v5 и не удаляет общие системные службы OPNsense: Стратегии/системные сервисы продолжают использовать свои исторические entrypoints до S04–S20. Не подменять удаление кнопки фиктивной успешной GUI проверкой.

## Дельта в исходниках

1. `src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt`: удалены HTML кнопки `#voiceServiceControl`, прежний JS click-handler `POST /api/zapret/service/start|stop`, его pending-control state, связанные RU/EN надписи и CSS slot. **Сохранены** пассивные `#voiceServiceState`, версия, `#voiceIPFWState`, `/api/zapret/service/runtime` + `/api/zapret/voice/inspect`, Voice Validate, Saved Draft, единый `/api/zapret/voice/apply` и shared Apply reconciliation. Отдельных сообщений о сбое Voice lifecycle-кнопки теперь нет и не требуется. Системный OPNsense `updateServiceControlUI('zapret')` пока оставлен в исходном виде; его штатный toolbar входит в общий S17 route audit, и его поведение **не** приравнивается к удалённой кнопке.
2. `general.volt`: `#zapretServiceControl` продолжает POST того же `/api/zapret/service/{start|stop}`. При отсутствии server.message RU/EN резервное сообщение теперь **учитывает action**: Start → ошибка запуска/WAN; Stop → ошибка остановки/проверка службы и журнала. Заголовок ошибки **управления службой**, не неверное «Ошибка применения настроек». Серверная `gettext` и ограниченная существующая локализация остаются. Никакой runtime/service/FD9/API код не изменён.
3. `scripts/test-voice-gui-contract.py`: изменены реальные Node-тесты GUI-гейтов и presenter — требуется отсутствие Voice lifecycle button; проверяются shared Apply/Save Draft, uncertain failure, RU/EN состояние Voice/IPFW и неразблокирование при сомнительном snapshot.
4. `scripts/test-tz6v5-s03e-public-cli-locale-red-native.py`: **настоящий original public CLI expected-RED неизменен**; source-routes из старого S03e1 обновлены в соответствии с новым owner-approved интерфейсом. Исторический RED неправильного Stop fallback и Voice `.always` хранится в SHA `9fc31056` / документе S03e1, не стирается.
5. `scripts/test-tz6v5-s03e2-gui-lifecycle-handler.py`: выделяет **фактический** production JavaScript listener Strategies и исполняет его в Node с инертными jQuery/AJAX заглушками. Проверяет RU+EN Start/Stop errors, известный server message route, собственно endpoint, busy rejection, success refresh. Никогда не выполняет реальный HTTP/configd/Start/Stop.
6. `scripts/p3-browser-i18n.py`: в уже существующем CI с настоящим Chromium и установленной одноразовой OPNsense проверяет отсутствие прямой Voice-кнопки при RU и EN. Для Strategies каждый клик Start/Stop выполняется настоящим браузером и production обработчиком, **но Playwright перехватывает HTTP** и выдаёт фиктивный ответ 503; `/api/zapret/service/runtime` и `resourcesStatus` тоже подменены строго в отдельной вкладке, чтобы сделать кнопку доступной на чистой системе. Ни один запрос Start/Stop не попадает в native backend; это browser GUI delivery доказательство, **не** native producer и не физический lifecycle. Без перехвата реальный Start/Stop в данном CI запрещён.

## Приёмка и границы доказательства

| Доказательство | Назначение | Статус до CI |
| --- | --- | --- |
| Source + Node actual extracted event handler RU/EN | Ошибка соответствует Start или Stop, Voice read-only, проверка регрессий shared Apply | **PENDING exact-head CI** |
| Legacy S03e1 original CLI on disposable OPNsense | Только настоящий старый public CLI, FD9 STATUS/invalid params expected RED; не запускать двигатель | **PENDING exact-head CI** |
| RU/EN actual OPNsense Chromium with intercepted HTTP 503 | Production GUI click + modal RU/EN and removal of Voice DOM, **without native request** | **PENDING exact-head CI** |
| RU/EN GUI with genuine native lifecycle `UserException` producer | Actual backend error→browser delivery, not an intercepted response | **NOT TESTED / NO-GO** |
| Physical RUNNING→RUNNING / STOPPED→STOPPED Lab, Auto learning, new CLI/force/reload | Независимые требования S03 и последующих этапов | **NOT CLAIMED** |

**GO для S03e2 source-correction** допустим только после exact-head CI и просмотра diff. **Полный S03 остаётся NO-GO**, S04–S20 не начаты. Факт успешной инертной Node-модели нельзя называть успешным реальным GUI кликом; реальный Chromium с перехваченным HTTP нельзя считать проверкой native error producer или физической службы. Установленный владелец `_117.pkg`, системные службы и пользовательские списки/Config/IPFW не изменялись; новый `.pkg` до S19 не выпускать.

Связанные документы: [ТЗ_6v5](TZ_6v5.md), [план S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), [S03e1 native/source RED](ZAPRET2_TZ6V5_S03E_PUBLIC_CLI_LOCALE_RED_NATIVE.md), [задача #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225).
