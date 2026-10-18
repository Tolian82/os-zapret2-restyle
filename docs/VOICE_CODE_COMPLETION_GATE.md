# «Передача голоса» — фактическая приёмка v0.5.3

17.10.2026 владелец установил опубликованный `0.5.2_194` через GUI и получил «Страница не найдена» на `/ui/zapret/voice`. **GUI-приёмка не пройдена.** Прежняя формулировка «код завершён» не означает соответствия установленной страницы ТЗ и снята.

[План v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) утверждён полностью. Текущая ревизия и следующий шаг — [START_HERE](START_HERE.md). [Публикация v0.5.2](verification/evidence/2026-10-16-v0.5.2-release-publication.md) и её успешные CI сохраняют силу только для проверенных ими уровней.

| Рубеж | Фактическое состояние | Что закроет |
|---|---|---|
| Маршрут меню | **Принято на устройстве**: `_2` установлена, Voice страница открывается и видны пять сервисов | Полная локализация/ошибки/WAN остаются отдельными сценариями |
| Регрессия и пакет | [CI #39023792241](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39023792241): Voice/Project/FreeBSD/package успешно, исходный и извлечённый `.pkg` проверены настоящим Router; негативный `_194` воспроизведён | Проверка маршрута в поставке закрыта, GUI браузер на устройстве — отдельный рубеж |
| Публикация v0.5.3 | **Подтверждена:** [GitHub Release](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3), [workflow](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39024503035), [evidence](verification/evidence/2026-10-17-v0.5.3-release-publication.md): tag/package/SHA256/Pages | Опубликованная поставка закрыта; установленный браузер — отдельная проверка |
| Открытие установленной страницы | В `_3` владелец подтвердил открытие, RU native help, WAN и синтаксическую проверку; общая служба «Неизвестно» остаётся дефектом `_3` | Проверить отображение общего статуса и read-only lifecycle на установленном `_4`; Save/Apply/boot/STUN — отдельно |
| GUI/CONFIG пяти профилей | В `_2` выявлены английские подсказки и ошибка WAN `Shared model candidate is not normalized`; `_3` находится в `main`, прошёл [CI #39031185860](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39031185860) и опубликован [проверочным пакетом](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_3/os-zapret2-restyle-0.5.3_3.pkg); owner-live результат не подтверждён | Полные пользовательские сценарии сохранения/валидации/Apply и отсутствие lost update |
| Публикация исправления _3 | [GitHub testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3_3) и [проверенный SHA-256](verification/evidence/testing-publications/v0.5.3_3.md) доступны; стабильный pkg-репозиторий не изменён | Установка _3 и GUI-приёмка на OPNsense отдельно |
| Проверка `_3` на устройстве | RU native help/WAN и удаление release selector подтверждены, синтаксис проверен. `setup_status=started`, Voice `uninitialized`; общий статус ошибочно «Неизвестно». `voice_lifecycle_inspect` завершился `Execute error`; причина получена read-only диагностикой: native inode owner проверял `root:wheel`, тогда как OPNsense 26.7 chowns Config как `wwwonly:wheel` | `_4` показывает общий started отдельно от неподтверждённого Voice; проверка owner `wwwonly:wheel` в скрипте проходит без ослабления проверок inode/flock/FD9, status отображён отдельно; результат установленной _4 |
| Поставка `_4` | [Тестовый пакет](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_4/os-zapret2-restyle-0.5.3_4.pkg) (SHA-256 `cba1c1a68a36a4d0cfbe61312157da338c386f9cde20e1395ada5e9393a0f37d`) опубликован из `449e777`, [Voice/Project/FreeBSD CI #39038290885](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39038290885) успешен, [evidence](verification/evidence/testing-publications/v0.5.3_4.md) | Установить `_4`, наблюдать предупреждение «Запущена · Voice не подтверждён», read-only lifecycle probe; реальные Apply/boot/STUN пока не приняты |
| Владелец установил _4 | Общая служба отображается как запущенная; lifecycle inspector без ошибки владельца, `saved_voice_on=false`. Но WAN показывает обобщённую ошибку, после попытки Apply результат обозначен неизвестным | В _5 классификация pre-FD9 ошибок проверяется исполняемым тестом; реальное значение ошибки подготовки и факт нативной записи ещё не подтверждены |
| Поставлен тестовый `_5` | [GitHub testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_5/os-zapret2-restyle-0.5.3_5.pkg), SHA-256 `3c4ca5acf76e22f0d0fc16c823849bc363030f137e36d1bea8c2bc2e1613b7da`, [CI #39042954730](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39042954730) Voice/Project/FreeBSD PASS. Нет подтверждения владельца | На установленной `_5` нажать только «Проверить», наблюдать точную стадию отказа или успешную синтаксическую проверку; Apply пока не повторять |
| Видимость результата «Проверить» | **Принято на установленной _6**: `pkg info` и GUI после «Проверить» показывают «Синтаксис проверен (без применения)» на отдельной строке; WAN без ошибки | Read-only Validate завершён; не доказывает сохранение/Apply |
| Первый Telegram ON Apply | Установленная `_8`: PHP FD9/root/gate/model подтвердились; GUI `shared-apply-run voice` rc69 дважды, durable journal и shared-work отсутствуют. `_9` даёт доверенный код стадии pre-runtime отказа вместо обобщённой неопределённости; не меняет engine/Config. [Testing pkg `_9`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_9/os-zapret2-restyle-0.5.3_9.pkg) опубликован, его установка подтверждена; Telegram ON Apply отказывает на ранней стадии `candidate` (Config не применён, saved OFF). Утверждено удаление отдельного Voice WAN выбора и наследование общего WAN, Issue #350; исходное значение `candidate` требует повторной проверки на `_10`. | Один Apply на установленной `_9`: определить точную стадию, устранить её ошибку, подтвердить saved ON, общий Zapret2 и Voice/IPFW; пока OPEN |
| Runtime/BOOT | Не подтверждено на OPNsense | Один dvtws2, scoped IPFW, Start/Stop, сохранение после reboot |
| UDP/STUN | Не подтверждено | Наблюдение пакетного результата и scope |
| MEDIA/CALL | Не подтверждено | Реальное двустороннее медиа и звонки по каждому квалифицируемому сервису |

Успешный нижний уровень не закрывает верхний: найденный в исходниках handler не равен отрисованной странице; отрисованная форма не равна успешному Apply; counters не равны звонку. Отчёт содержит «изменено / фактически проверено / остаётся неподтверждённым». Следующий участок не обходит обнаруженный блокер. Полное [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), пять сервисов и общий backend сохраняются.

## Обнаруженный недостаток snapshot в `_10`, кандидат `_11`

Текущая Voice-страница без отдельного WAN всё ещё возвращает `preflight-rejected=candidate` при Telegram ON. Подтверждение установленного `_10` по `pkg info` для этой попытки отсутствует. Источник OPNsense `BaseListField::getNodeData()` допускает отличающиеся локализованные `value` и наборы невключённых опций между web и CLI; SHA256 не должен включать эти UI-атрибуты. `_11` нормализует выбранные ключи и добавляет регрессию RU/EN с негативными проверками реальной смены WAN и mode. В случае сохранённого отказа пользователь увидит подстадию `candidate-plan/validation/xml/size`; successful Config/runtime/IPFW/CALL ещё не подтверждены.

## `_11` runtime-build failure / `_12` repair

Owner-live `_11`: native Apply остановился до IPFW/Config на `runtime-build`. Фактическая ошибка: `telegram.args: required --filter-udp is missing`, стадия 4/8 blobs. Доказан дефект подготовки: MVC default Telegram args не попадал в физический detached XML, когда менялся только enabled. В `_12` полный args/IPSET каждого включённого профиля материализуется независимо от MVC changed map (сохраняя его проверку для авторизации). CI и проверка на сервере ещё ожидаются; **реальный Telegram Call не принят**.

## Testing v0.5.3_12 — код проверен, устройство ожидается

После исправления XML-мостика Voice/Project/FreeBSD15 CI #39117198942 прошёл; [testing pkg `_12`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_12/os-zapret2-restyle-0.5.3_12.pkg) опубликован (SHA-256 `ed28d1c071fb2dee1e2ee891634762a367fa675a48c561e2db2ce13731e6effe`). Результат установки, Telegram ON Apply, сохранённый Config, IPFW/STUN и реальный CALL ещё не подтверждены владельцем.

## Установленная `_12`: validator 7/8, этап `_13`

Owner-live `pkg info -> _12`; stage 7/8 validator и точное `ERROR: installed engine rejected candidate: file_open_test: Permission denied` для `.../shared-work/<id>/release/managed/hostlist-exclude.txt`. Причина — native `dvtws2 --dry-run` с drop privileges не может пройти каталог приватной FD9-транзакции `0700`. `_13` сохраняет staging root-only и валидирует только публичные runtime-списки через временную копию, которую удаляет до Config/IPFW. Voice/Project/FreeBSD15 CI #39119480095 успешно; [testing pkg `_13`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_13/os-zapret2-restyle-0.5.3_13.pkg) опубликован (SHA-256 `7e090d0ff7a6f8db7c1d4e5290eb388313aed297fbdf5c6936d10fd345bba171`). Требуются установленная `_13`, подтверждение ON/runtime/IPFW/STUN и реального звонка.

## v0.5.3_14 — первый переход от обычных Стратегий

Owner-live `_13` confirmed READY 8/8, `LEGACY_NO_VOICE_PLAN`, `SEALED`, journal none, Telegram saved OFF. Native executor has a pre-journal guard refusing old running runtime without common ownership manifest. `_14` verifies exact previous root-owned Strategies runtime and kernel TCP/UDP divert rules before first common Apply and reuses the same journal/runtime/IPFW/Config transactions. CI and installed Telegram ON, common runtime/IPFW/STUN and actual call remain open.

## Testing v0.5.3_14 — ожидает установленной приёмки

Реализация первого перехода из живых обычных «Стратегий» проверена Voice/Project/FreeBSD15 CI #39123963640. [Тестовый пакет `_14`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_14/os-zapret2-restyle-0.5.3_14.pkg) опубликован из `be66694` (SHA-256 `e790c48f1fe3f8e1a42e9e865bb35f8507520e09c8bc8905feb7647fc238360c`). Успешная установка, native Apply/Config ON, общий IPFW/runtime и Telegram STUN/CALL на приборе ещё не подтверждены.

## `_15` — невозможность первой активации из-за unbound CLI variable

После owner-live `_14` GUI остаётся Voice unconfirmed / Apply unknown. Код `voice_ipfw_adapter.main()` содержал `if not legacy` (переменная не существует) в `verify-legacy` при живом old Strategies. Исправлено на `prior_legacy`. Для исключения ложного зелёного CI добавлен тест самой CLI-ветки, отдельная проверка safe-before-journal отказов в shell executor и сообщения GUI. До owner-live проверки `_15` сохранённый Telegram ON, общий runtime, IPFW, STUN/CALL не приняты.

## Testing package `_15`: проверен код, владелец ещё не подтвердил работу

Реальный код `verify-legacy` после исправления проверен вызовом CLI `main()`, а отказ до durable журнала возвращает ограниченную стадию вместо 'unknown'. Voice/Project/FreeBSD15 CI #39126436549 PASS. [Пакет `_15`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_15/os-zapret2-restyle-0.5.3_15.pkg) опубликован с SHA-256 `d1cc2fad37be7473beac86c8aeef42cc500a1d48763ba891e20fbf46b36f488e`. Успешный installed Apply/Config ON, общий runtime/IPFW/STUN и реальный CALL всё ещё OPEN.

## v0.5.3_16 — подтверждённая ошибка staged release на установленной `_15`

18.10.2026: owner-live `_15` Telegram ON Apply завершился rc69 до сохранения Config. В `configd` точный stderr: `runtime root must have mode 0755: .../shared-work/<id>/release`. `_16` финализирует именно release до bundle seal и проверяет режимы через штатный валидатор, сохраняя workspace 0700. Русский GUI перестаёт маскировать `bundle-verify/config-preflight/runtime-preflight`. CI/пакет и installed Telegram ON, IPFW, STUN/MEDIA/CALL ещё не приняты.

## Опубликованная `_16`: проверено в CI, не принято на OPNsense

Из исходного PR #366 `8c50c401` тесты Voice/Project/FreeBSD15 #39132346651 успешны. GitHub testing package опубликован #39132944747, SHA-256 `b55e5a2ed8d018918f4b0bd4a8bebd3703a2dbdffea3ff4ba0d9bf2b27ef246f`. После install требуется один Telegram ON Apply с явным подтверждением Config ON и общего runtime/IPFW. STUN/MEDIA/CALL принимаются отдельно. Публикация сама по себе не закрывает реальный дефект на устройстве.

## v0.5.3_17 — FreeBSD process census false duplicate; live gate OPEN

`_16` owner-live: successful candidate prep but refused at `runtime-preflight`; stderr `unexpected or untracked dvtws2 process`. Owner supplied actual PID-file 2848, genuine dvtws2 PID 2848, shell PID 9195 with dvtws2 pathname only in its argv field 7. Scanner previously matched *any* argument, hence counted an unrelated shell. `_17` matches the executable position only, with regression against shell mentions and two real engines. Until fresh installed Apply, `saved_voice_on=false`, shared Voice/IPFW uninitialized; STUN/MEDIA/CALL still OPEN.

## Testing `_17` подтверждена пакетом — owner-live проверка впереди

Source PR #368 merged `6501b0f`, source Voice/Project/FreeBSD15 CI #39134787692 PASS, testing release [v0.5.3_17](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3_17) SHA-256 `e306babb6d4515c3fac70653a3ba9ecdccf2eb9a7a7b95e53e359c0b7725d4aa`. Воспроизведённая ошибка `_16`: census учитывал PID 9195 shell как dvtws2 при настоящем PID 2848. `_17` исправляет фильтр executable token; настоящий второй процесс всё ещё должен отказываться. На установленной `_17` Config/runtime/IPFW/STUN/MEDIA/CALL пока не проверены.

## v0.5.3_19 — FreeBSD missing native Voice tables; installed result OPEN

On installed `_17`, `runtime-preflight` fails because FreeBSD 15 says `ipfw: failed to request table info: No such process` (rc71) for ten Voice tables that are normally absent until initial shared Apply. Existing Strategy divert 19000 TCP/19001 UDP (989, vtnet1) remain intact. `_18` contains narrow table-info rc71/diagnostic recognition and native CLI regression; real Telegram saved ON, new IPFW, STUN and bidirectional CALL not yet accepted.

## v0.5.3_19 packaged — live gate still pending

Source/FreeBSD15 CI #39142330715 PASS, source merge `ff43ed56`, [testing `_19`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3_19) SHA-256 `57ac0eb1b9ce873aa5821bf2c633d72af2bcd3d5ecf879f63de4fac854bd541f` published and verified. Owner confirmed on `_17` that FreeBSD15 uninitialized Voice table info uses rc71 and `No such process`; code now handles that narrow absence. Installed `_19` saved Voice ON, IPFW and bidirectional STUN/MEDIA/CALL not yet evidenced.

## v0.5.3_21 — native supervisor callback and blocked live recovery gate

Live `_19` requires-review: new dvtws2 launched 19:15:11 without supervisor, legacy runtime/IPFW remain, Config Telegram OFF. Exact code defect: absent service-level `SERVICE_SCRIPT` despite two uses inside `apply_runtime.sh` and executable check in `supervisor_start`. Tests previously mocked this variable and missed the failure. `_20` explicitly pins the native callback and regression-checks real service header plus full activation/restore forwarding. The already blocked `requires-review` journal is NOT auto-recovered; appliance safety and actual Telegram ON/IPFW/STUN/CALL still OPEN.

## v0.5.3_22 — operator-reviewed legacy handoff recovery is NOT end-to-end Voice success

Only attested original old Strategies state can authorize reattaching missing supervisor and committing restored journal under original FD9. User must confirm one successful common Telegram ON Apply after recovery. STUN/MEDIA/CALL remain OPEN until appliance results.

## Published `_22`, owner-live gate OPEN

Source CI #39148988899 PASS, FreeBSD15 testing pkg SHA-256 `0d2dca31eed8f12dafc616bdbeb4699599c0a9a498ff41ae3ca5355ecc719c78` published from `22fbbed3`. No owner-live recovery yet: persistent `requires-review` `_19`, old IPFW, no supervisor. Operator uses explicit FD9 `shared_recover_reviewed_legacy`, and separately tests Telegram ON and STUN/MEDIA/CALL. Never report saved Voice ON or working calls from static CI.
