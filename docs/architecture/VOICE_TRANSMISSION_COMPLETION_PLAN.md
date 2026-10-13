# «Передача голоса» — подробный проект плана этапа v0.5.2

**Этап: `v0.5.2_65`, без релиза. План принят к выполнению 13.10.2026 прямым поручением владельца начать программирование согласно плану.** Архитектура, семь этапов и контроль используются как рабочая очередь. План подготовлен 13.10.2026 на кодовой базе `v0.5.1_174` и перенесён в новый этап. Последний исходный снимок — commit `11a8fdc12b602c4b4174b03b504a66f9b0af04c8`, Draft PR #328. При открытии этапа меняются VERSION/PLUGIN_REVISION и документация; исходники frontend/backend и поведение службы не изменяются.

## Текущий следующий шаг

`_63–_65` implement a deliberately bounded cancel for an *unchanged* live old owner. Original FD9/Config flock, old full snapshot bytes, marker, 3 kernel process identities, scoped IPFW and sealed predecessor are re-verified before the existing journal is atomically marked `restored`. Failures remain blocked; there is no alternate actuator, automatic boot clearance or mutation of engine/kernel/Config. Next work must be the **actual** single reversible live legacy-to-common executor plus FreeBSD owner-live and STUN/MEDIA/CALL acceptance.

`_62` устраняет найденную CI фикстурную ошибку (`LOG` при `set -u`) без изменения правил durable STOP intent. Далее — законченный единственный rollback executor, а не добавление бесконечных фаз безопасности. Операторскую команду arm не запускать на production до доступного полноценного восстановления и настоящей проверки FreeBSD.

`_61` исправляет регрессию CI после появления новой команды в общем FD9 router и оставляет функциональное состояние `_59–_60` неизменным: durable old STOP intent зафиксирован в ОДНОМ common Apply journal, но живой legacy пока не отключается. **Операторское arm не использовать на рабочей системе** — оно блокирует обычное включение службы, пока не существует завершённого безопасного legacy rollback executor.

`_59–_60` устраняют неопределённость отсутствующего durable STOP intent для одного sealed candidate. Без дополнительного WAL расширена **существующая запись** `SharedApplyOperation`: `legacy_predecessor` хранит проверенный 64-hex SHA-256 digest old previous-five + immutable reverse-plan, разрешён исключительно при Voice `prepared` без прошлого common owner. Операторская `shared-apply-legacy-arm ID` проходит FD9 и проверяет running old kernel argv/IPFW, detached new release, Config и sealed old snapshot. Команда записывает лишь intent; она **не останавливает старый PoC**. При reboot `legacy-prepared` нельзя автоматически закрыть как обычный `prepared`, а generic `record activating` теперь гарантированно отвергается. Это означает, что до готовности reversible executor **arm намеренно блокирует normal lifecycle**; на рабочую OPNsense пока не запускать. Следующая доработка — единственный исполнитель для live stop/replace/Config commit, с проверенным revert предыдущих процессов/IPFW/Config и восстановлением после power-cut. В конце — реальные GUI/STUN/MEDIA/CALL тесты.

`_58` фиксирует CI-регрессию `_57` от изменения outer FD9 command list, добавляет отдельную проверку strict path-binding для старой previous-capture: sealed candidate в root `shared-work/<ID>` + отсутствие любого common journal owner + безопасный `legacy-backup` path. Два read-only candidate audits по разные стороны полного previous-five snapshot должны совпасть; при дрейфе snapshot остаётся для анализа и никакой cutover не разрешается. Следующий этап — связать это проверенное immutable previous evidence с одним общим journal, строго записываемым undo intent **до** каждого действия над old engine/IPFW/Config. Сейчас любые попытки live mutation намеренно отклоняются; FreeBSD power cut и Telegram STUN/CALL не подтверждены.

`_57` впервые готовит полный **предыдущий recoverable live-PoC snapshot в пространстве конкретного общего Voice-кандидата**, не обращаясь к старому самостоятельному cutover журналу. Операторская `shared-apply-legacy-capture <id>` после обеих защищённых `_56` проверок сохраняет Config/runtime/marker/IPFW + реальные kernel argv/security/process инвентари и immutable reverse-plan через уже существующий проверенный `voice_native_legacy_predecessor_route.py capture-common <id>`. На всех этапах прежний engine/IPFW/Config остаются нетронутыми, результат `legacy-handoff-authorized=0`. Следующая реальная задача — единый durable stop/IPFW/one-engine/new Config commit с гарантированным возвратом этого снапшота при сбое питания; до его реализации операторский capture не считается разрешением Voice ON.

В `_56` найден функциональный дефект `_54–_55`: диагностика старого владельца была реализована под FD9 **внутри функции**, но не включена во внешний lifecycle lock router. Без FD9 production проверка FreeBSD владельца гарантированно отказывала. Оба операторских read-only маршрута теперь привязаны к родному FD9. Новый `shared-apply-legacy-qualify` принимает только 32-hex ID sealed общих Voice ON candidate/Config, валидирует штатный merged dvtws2 runtime и точное старое IPFW/argv свидетельство, затем повторяет seal/Config. Нет нового WAL/daemon/frontend/independent backend и никаких действий над live old owner. Следующий шаг — **один обратимый миграционный executor** с durable old snapshot и восстановлением process/IPFW/Config после неуспеха; до этого `legacy-handoff-authorized=0`, ручные FreeBSD проверки обязательны.

`_55` подключил к общему FD9 read-only операторскому audit прежний полный FreeBSD legacy PoC inspector, не копируя ни строчки его kernel/IPFW/argv парсера. Положительный статус требует уже существующие строгие проверки marker/state/managed IPSET, полного argv/image трёх kernel процессов, old IPFW rule interval и полной таблицы, оригинального Config flock. Повторный common process census до и после снимает гонку на входном уровне. Это закрывает **только диагностическое** доказательство фактического old-state: handoff остаётся запрещён без защищённого инвентаря/восстановления old kernel/process/Config при любом сбое. Не строим второй runtime, не меняем GUI/ТЗ.

`_54` — первый read-only шлюз миграции работающего legacy под FD9: старое дерево, PID dvtws2 и supervisor, full census и старое состояние IPFW наблюдаются без каких-либо изменений. Команда `shared-apply-legacy-audit` сообщает `legacy-live-observed=1` и `legacy-handoff-authorized=0`, так как старое наличие правил ещё не является exact ownership/rollback witness. Дальше потребуется строгий kernel/argv proof и возврат legacy при любом сбое, а затем настоящий FreeBSD owner-live. Нельзя принимать диагностический статус за готовую миграцию.

В `_53` устранена причина неопределённости при промежуточном `rename`: только для нового общего Apply служебные atomic пути получают тот же 32-hex ID, что и durable shared journal. Прерванный `activating` с отсутствующим active теперь может возобновить строго старого common owner, если `.stage.<id>` byte-for-byte соответствует sealed new, а ровно один `.old.<id>` либо `runtime-v2-<id>` — sealed previous; native Config, процессы и IPFW подтверждены до и после restore. Восстановление копирует прежний sealed release штатным installer, не потребляет и не стирает следы crash. PID-only residuals до `_53`, mixed/unknown kernels/processes/configs и конфликт обоих old artifacts остаются blocked. Далее нужны настоящие FreeBSD owner-live/power-cut и переход с работающего legacy, а не очередной отдельный runtime/backend.

В `_52` устранён ещё один конкретный случай зависшего `activating`: если новый complete sealed runtime уже установлен (после atomic rename, до сохранения `activated`), а native Config по-прежнему принадлежит previous committed common owner, root FD9 перепроверяет bundles/installed source, процессы и IPFW и использует существующий `_50` cold rollback в предыдущий runtime. Запись `restored` производится только через новый phase-bound CLI `finish-activating`, не ошибочно через `finish-activated`. Состояния, в которых active tree исчезло, лежит в .old.PID или частично перенесено, **не** признаются автоматически восстановленными: требуется ещё доказать связь с предыдущим владельцем без предположений по PID/времени.

В `_51` production `atomic_install_tree` останавливает установку вместо удаления существующих PID-stage/PID-old и не переносит runtime в занятый backup. Сохранение остаточных деревьев после сбоя — необходимая предпосылка проверяемого восстановления `activating`, но ещё не его автоматическое выполнение. Следующая разработка должна отличать первичный stage, перенос старого release и финальный rename, подтверждая владельца по durable operation, предыдущий Config и состояние IPFW/процессов; неизвестные каталоги не удалять.

В `_50` штатный FD9 получил ограниченный rollback до Config save после `activated`: холодное состояние, новый installed runtime точно совпадает с sealed candidate, previous committed common Config сохранён, kernel и все процессы пусты. Общий atomic helper устанавливает предыдущий release, оставляет failed candidate в backup; после независимой проверки тот же journal отмечает `restored`. Отсутствие previous, внешние объекты, частичная установка, уже изменённый Config и любой живой процесс остаются блокирующими. Фронтенд и ТЗ не меняются; это не завершает stage-4 для других crash-сценариев.

В `_49` добавлен первый конкретный сценарий boot recovery `activating`: если в журнале существует `previous` committed общего владельца, native Config совпадает с его sealed candidate, активное дерево byte-for-byte совпадает с его release, dvtws2/monitor и IPFW отсутствуют — запись того же журнала может перейти в `restored`. Это **только неповреждённая предыдущая установка**, не откат частично изменённой системы. Дальше требуется проверяемый безопасный механизм для `activated` и частично мутировавшей `activating`. Статусы, пять сервисов, frontend и ТЗ неизменны.

Этапы 1–2 реализованы через общие generator и firewall. Этап 3 подключил обе штатные формы к одному root FD9 executor: полный candidate, native Config save, процессы, IPFW и подтверждённые транзакционные фазы. В `_47` проверен переход только с **остановленного** legacy; в `_48` исправлен производственный путь отката (`$$` вместо буквального `$`). Не закрыты power-cut восстановление `activating`/`activated`, handoff работающего legacy, удаление дублирования и owner-live приёмка. Это не меняет ТЗ, GUI или пять сервисов и не означает выпуск релиза.

Нормативный контракт — [раздел 12 ТЗ](VOICE_TRANSMISSION_GUI.md#12-общий-backend-со-стратегиями-утверждено-13102026). Разделы 1–11 ТЗ, пять сервисов Telegram / Discord / X / SIP / Custom, поля, компоновка и функциональная приёмка остаются неизменными. Промежуточная проверка одного профиля не заменяет полный результат.

## 1. Конечная архитектура и границы работы

Обе страницы передают свои поля в один общий Apply. Он строит полный кандидат из модели `OPNsense.Zapret`, проверяет ordinary и Voice вместе, меняет один runtime и свои IPFW-объекты, сохраняет настройки через штатный OPNsense Config. Start/stop/reconfigure/boot используют тот же генератор, firewall, launcher и supervisor. Отдельного Voice-писателя XML, второго процесса или самостоятельного протокола применения нет.

| Постоянные и производные данные | Владелец |
|---|---|
| ON/OFF, аргументы, WAN, общие IPSET | Только постоянная модель `OPNsense.Zapret` |
| Изменения формы «Стратегии» | Её whitelist полей; сохраняется остальная модель |
| Изменения формы Voice | Её whitelist полей; пять общих IPSET сохраняются в существующих `hostlist.*` |
| Полный runtime, процессы, свои таблицы и правила | Общий lifecycle `zapret_service.sh` под существующим FD9 |
| Манифест действующего runtime и владения IPFW | Производное описание того, что установила общая служба; не второй источник предпочтений |
| Незавершённый Apply | Одна ограниченная общая запись операции и необходимые previous/candidate копии; не набор независимых Voice-журналов |

Существующие формы `forms/voice.xml`, `forms/general.xml`, меню, расположение полей, стили и пользовательская логика по ТЗ не перепроектируются. В views допускается только необходимая техническая привязка уже предусмотренных результатов/статусов к новому API и замена временных OFF-only сообщений. Это не изменение требований к frontend; точный объём такой привязки показывается отдельным diff на этапе 5.

TCP/Squid/sing-box/PF/NAT, маршруты, Laboratory и Docker не входят в переделку. Нельзя ускорять работу снятием защиты чужих процессов/правил, ограничением страницы одним сервисом или удалением сценариев отказа.

## 2. Карта изменения компонентов

Сокращения путей: `Api/` — `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/`; `backend/` — `src/opnsense/scripts/OPNsense/Zapret/backend/`. В таблице указаны точки работы, а не требование изменить каждый файл независимо от необходимости.

| Компоненты текущего кода | Решение | Этап |
|---|---|---|
| `Api/SettingsController.php`, `VoiceController.php`, `StrategySettingsPayload.php`, `VoiceSettingsPayload.php` | Сохранить endpoints и границы полей; обе Apply-команды делегируют одному механизму | 3 |
| `VoiceApplyCandidate.php`, `VoiceCandidateValidator.php`, `VoiceSettingsSnapshot.php`, `VoiceCandidateXml.php` | Повторно использовать чистую подготовку/валидацию/снимок; собрать общий кандидат, не писать рабочий Config напрямую | 1, 3 |
| `Zapret.xml`, template `zapret.conf`, `backend/registry.sh`, `storage.sh`, `targets.sh` | Существующие пять сервисов и IPSET остаются; при необходимости добавить только штатную миграцию/метаданные модели | 1, 4 |
| `voice_model_export.py`, `voice_profile_compiler.py`, `voice_capture_plan.py`, `voice_traffic_merge.py` | Сохранить полезные преобразования; подключить к общему release и уточнить проверку пересечений | 1, 2 |
| `voice_release_stage.py`, `voice_native_render_saved.sh` | Использовать опыт сборки и изолированного native template render; убрать отдельный неактивный Voice bundle из целевого рабочего пути | 1, 6 |
| `backend/orchestrator.sh`, `generator.sh`, `validator.sh`, `ports.sh` | Один полный кандидат и одна активация; ordinary parser не расширяет перехват из-за Voice wildcard | 1–4 |
| `backend/firewall.sh`, `voice_ipfw_adapter.py`, полезные функции `voice_firewall_transaction.py` / `voice_firewall_ledger.py` | Обобщить владение и операции пяти таблиц в общий firewall; не переносить весь private координатор | 2, 4 |
| `backend/atomic.sh`, `launcher.sh`, `supervisor.sh` | Сохранить установку/возврат runtime и управление одной службой; устранить конкретные пробелы отката/прерывания | 2–4 |
| `zapret_service.sh`, `actions_zapret.conf`, `Api/ServiceController.php`, штатные syshook и package hooks | Одна сериализация, обычные start/stop/reconfigure/boot, совместимые команды Telegram | 3, 4 |
| `backend/telegram_voice.sh`, старые marker/prepend | Ограниченная миграция, затем вывод из рабочего пути; ON/OFF читается из модели | 4, 6 |
| `voice_native_*`, `voice_cutover_*`, старые ручные dispatch/configd paths | Разобрать зависимости; переносить только нужные гарантии, удалить неиспользуемую отдельную инфраструктуру | 6 |
| `views/voice.volt`, технические bindings `general.volt`, существующий runtime/inspect API | Согласовать ответы и фактические статусы без новой формы или дизайна | 3, 5 |
| `scripts/test-voice-*`, общие activation/lifecycle/firewall checks, `.github/workflows/ci.yml` | Оставить проверки поведения; убрать проверки удалённого протокола после переноса гарантий | В соответствующем этапе, окончательно 6 |

Предлагаемый предел новых производственных точек интеграции — три небольших общих компонента: `Api/SettingsApply.php` (общий вход/ответ), `src/opnsense/scripts/OPNsense/Zapret/apply_settings.php` (штатная модель и Config в привилегированном worker), `backend/apply_runtime.sh` (узкий вызов существующего orchestrator под уже взятым FD9). Названия предварительные; если существующий файл покрывает ответственность, отдельный файл не нужен. Перенос или переименование пригодного IPFW adapter не означает создание нового backend. Дополнительный координатор требует изменения согласованного плана с конкретным обоснованием.

## 3. Контракт общего Apply

### Последовательность одной операции

1. Контроллер принимает полную форму, проверяет права, whitelist и исходный snapshot. Он не сохраняет модель заранее. Запрос передаётся worker через ограниченный серверный механизм: фиксированная команда, созданный сервером идентификатор, приватный файл `0600`; клиент не задаёт путь, shell-команду или полный системный XML.
2. Общая служба берёт существующий lifecycle FD9. Worker под штатным Config lock читает свежую модель, накладывает только поля этой формы, фиксирует previous preferences и фактический running/stopped state, затем строит detached candidate. Устаревшие релевантные поля дают отказ до изменений.
3. Под FD9, но без долгого удержания Config lock, кандидат рендерится в изолированной области штатным template engine. Общий generator создаёт все профили, списки, аргументы и план IPFW. Проверяются native engine/Lua/resources, WAN, пересечения и владение. Действующая служба продолжает работать.
4. Непосредственно перед первым изменением worker снова берёт Config lock, перечитывает текущую модель и сверяет зависимости кандидата. Изменение WAN, ordinary, shared IPSET или применяемых Voice-полей требует нового кандидата/отказа. Правка unrelated страниц не заменяется старой копией всего XML.
5. Под тем же FD9 и Config lock фиксируется ограниченная запись незавершённой операции, затем общий orchestrator активирует candidate или сохраняет stopped состояние. Previous runtime и собственные правила остаются пригодными для возврата. На этом шаге ещё не объявляется успех.
6. После подтверждения активации штатный OPNsense Config сохраняет новые поля с нормальной revision/history/backup/notification семантикой. При ошибке сохранения возвращается previous runtime/IPFW и, если необходимо, только изменённые этой операцией поля через штатное сохранение. Перед возвратом полей повторно проверяется их текущая версия; более поздняя чужая правка не перезаписывается, конфликт восстановления даёт явный отказ. Не выполняется самостоятельная Python-запись всего `/conf/config.xml`.
7. Успех возвращается после проверки согласованности preferences/runtime/IPFW и завершения общей записи операции. Ошибка отката отличается от обычного failed Apply и видна оператору. Повтор того же кандидата не создаёт вторую службу, второй prepend или дополнительные правила.

Runtime переключается перед финальным сохранением preferences, чтобы ошибка запуска не оставляла новое сохранённое состояние. Неатомарное окно между двумя системами покрывается одной общей записью операции и проверяемым recovery. Её минимальные данные: идентификатор/фаза, previous/candidate версии и хеши, изменяемые поля, previous running/stopped, собственные firewall manifests и ссылки на уже нужные runtime backups. Нет отдельной серии receipt для каждой вспомогательной функции.

**Проверка платформы до подключения Apply:** на целевой версии OPNsense подтвердить запуск PHP worker, порядок `lock → model → save`, фактическое освобождение lock внутри `Config::save()`, notifications и отсутствие взаимной блокировки с configd. Нельзя считать Config lock непрерывно удержанным после native save: повторная работа с Config требует нового lock и проверки текущих полей. Worker не вызывает вложенный `configd reconfigure`, который повторно ждёт свой FD9; он вызывает общий adapter напрямую. Дочерние daemon/monitor закрывают FD9, как проверяется существующим lifecycle-lock тестом.

Эта интеграционная проверка — ограниченная входная задача этапа 3. Если платформенный контракт не позволяет предложенный порядок, предъявляется один воспроизводимый разрыв и исправление общего Apply до его включения. Построение альтернативной Voice-транзакционной платформы не является продолжением этого этапа.

### Поведение службы

| Исходное состояние | Apply | Штатный Start/Boot/Stop |
|---|---|---|
| Общая служба включена и работает | Проверить полный кандидат, переключить общий runtime, сохранить preferences | Start/Restart/Boot используют тот же генератор |
| Общая служба включена, вручную остановлена | Проверить и сохранить preferences; процессы не запускать | Явный Start/Restart запускает; normal boot следует сохранённому `general.enabled` |
| `general.enabled=0` | Проверить и сохранить Voice preferences; процесс и перехват не включать | Normal boot не включает Zapret |
| Все Voice OFF | Сохранить их тексты/IPSET; полный ordinary runtime без Voice-профилей/правил | Stop убирает только свои runtime-объекты, preferences остаются |
| Первого runtime ещё нет | Принять состояние отсутствующей предыдущей службы; не требовать работающую триаду или старый ledger | Первый штатный Start строит полный runtime при установленном engine |
| Незавершённая/повреждённая операция | Подтверждённый общий recovery либо явный безопасный отказ | Здоровый завершённый Apply не блокирует последующий boot/start; неоднозначность не очищается молча |

Ручной Stop и глобальная OFF — разные состояния существующей общей службы. План не добавляет отдельный Voice boot-флаг или новый постоянный запрет автозапуска после обычного Stop. Если форма «Стратегии» явно изменяет глобальное включение, применяется её существующий контракт; Voice Apply не меняет его скрыто.

## 4. Этапы изменения кода

### Этап 1. Полный Voice-кандидат в общем генераторе

**Результат:** из одной постоянной модели общий generator создаёт runtime для всех пяти сервисов и ordinary Strategies; без изменения действующей системы.

**Код:** чистые Voice candidate/validator/export/compiler/merge helpers; `orchestrator.sh`, `generator.sh`, `validator.sh`, существующий template и target pipeline по необходимости.

- Передавать generator полный staged candidate, а не только уже сохранённый OFF-draft или маску включения.
- Использовать изолированный native template render по известному XML-кандидату; не вызывать глобальный template reload ради предварительной проверки.
- Сформировать enabled Voice-профили в порядке Telegram → Discord → X → SIP → Custom, затем ordinary через `--new`. All-OFF оставляет ordinary текст неизменным.
- Использовать те же нормализованные `hostlist.*` файлы; OFF сохраняет введённые данные, но не создаёт профиль/перехват.
- Проверять параметры, engine/Lua и файлы. Прямое выполнение пользовательского текста через shell исключено. Временный allowlist сверить с полным назначением ТЗ; ограничение не выдаётся за реализованную поддержку.
- Проверить пересечения IP/портов/профилей. Уточнить нынешний blanket reject ordinary STUN: отказ должен объяснять действительный конфликт или недоказанную изоляцию, не ломать разрешённые non-STUN Strategies.
- Разрешать Voice WAN наследование/совпадение с общим WAN. Разный WAN до доказанной изоляции явно отклонять; не менять Strategies WAN скрыто.

**Переход:** all-OFF, каждый сервис по отдельности и все пять с непересекающимися IP/портами дают правильный полный candidate; ошибочный кандидат не меняет Config/runtime/IPFW. Использовать существующие compiler/capture/merge проверки и один сценарий общего generator. Пять сервисов входят уже в этот этап, не добавляются пятью независимыми очередями.

### Этап 2. Пять таблиц и общий безопасный firewall

Текущая задача: подключить `voice-plan.json` и ordinary port artifacts общего release к существующему IPFW adapter через `firewall.sh`; выполнить install/update/all-OFF/stop и возврат до commit. Использовать предыдущий release как производное описание владения, без отдельного Voice ledger. Проверка — полный generator → общий firewall с отказами и сохранением чужих объектов; этап 3 подключит этот путь к публичному Apply.

**Результат:** общий firewall устанавливает, обновляет и возвращает scoped перехват всех включённых сервисов вместе с ordinary правилами.

**Код:** `firewall.sh`, `ports.sh`, `orchestrator.sh`, `atomic.sh`; пригодные IPFW adapter/manifest/transaction функции. Не переносить зависимость на самостоятельный `VoiceOwnershipStore` как второго владельца.

- Расширить текущую работу Telegram table до пяти именованных таблиц, staging/commit/restore и одного общего ownership manifest.
- В Voice правилах всегда использовать destination table, UDP-порты и разрешённый физический `xmit` после разрешения logical WAN. `*` не передавать в ordinary numeric port extractor и не превращать в `to any`.
- Сохранить local/forwarded capture, защиту от повторного divert и корректный порядок Voice/ordinary правил.
- Проверять номерной диапазон, имя/содержимое таблиц и живое владение до первого удаления/изменения. Номер или имя сами по себе не доказывают владение. Чужие объекты дают явный отказ.
- На update/delete/all-OFF и rollback удалять только подтверждённые собственные объекты, возвращать предыдущие таблицы/правила и убирать свои завершённые staging-объекты. Не скрывать ошибку table destroy как успешную очистку.
- First start с отсутствующими собственными объектами допустим; требование обязательного старого ledger/работающего engine убирается из нового пути.

**Переход:** install/update/remove/all-OFF и ошибка между заменой runtime/таблиц/правил возвращают согласованный previous state. Чужая таблица/правило сохранены. Проверки общего adapter выполняются в Linux с fault injection и на FreeBSD; проверка реальных WAN-пакетов завершается на этапе 7.

### Этап 3. Общий Apply обеих страниц

**`_47` — тестируемый quiescent legacy→common migration.** Добавлен интеграционный shell-сценарий на существующем `apply_runtime.sh`: при полностью остановленных dvtws2/supervisor и пустом owned IPFW прежняя legacy-директория (без нового `voice-plan.json`) сохраняется штатным atomic backup, запускается общий runtime, а отказ до Config save восстанавливает именно прежнюю директорию и пустой kernel. Успешный повторный Apply оставляет старый backup доступным; работающий legacy-процесс по-прежнему отвергается. Это **не** автоматическая остановка и не эксперимент над живым OPNsense; API GUI и утверждённое ТЗ не менялись. Переход с running legacy требует отдельного доказанного live-owner handoff; FreeBSD owner-live и реальный STUN/call acceptance всё ещё не завершены.

**`_46`: корректировка изоляции Linux runtime-теста.** Существующий `test-voice-common-apply-runtime.sh` загружает production `apply_runtime.sh` и только затем подменяет внешний full-process census для чистой имитации engine/kernel; иначе source переопределял fake и вызывал отсутствующий `common_pidfile_read` в стенде. Отдельный `test-voice-common-engine-census.sh` продолжает запускать именно production-код census и проверяет реальные ветви отказа. Защитный pre-journal отказ при незарегистрированном dvtws2 остаётся в production без изменений. На последнем HEAD требуется получить полный CI PASS, FreeBSD owner-live ещё не выполнялся.

**`_44`–`_45`:** предварительная попытка PID-парковки оставила в коде буквальный суффикс `$` и неверную регрессию. В `_48` исправлены реальная подстановка `$$` и проверка сохранения чужих parked release.

**`v0.5.2_43` — предотвращение ложного `requires-review` при обычном legacy/foreign runtime.** В общем `backend/apply_runtime.sh` read-only `apply_runtime_probe` отделён от мутирующего `apply_runtime_preflight`. Под исходным FD9, после detached Config preflight и до durable фаз `prepared/activating`, `shared_apply_execute_service` проверяет полноту candidate, engine/supervisor, соответствие common active release и фактический IPFW. Запущенная legacy-установка без `voice-plan.json`, частичный monitor и чужой kernel/IPFW отвергаются кодом 69 **без записи** новой транзакции и без firewall_prepare. Когда проверки пройдены, тот же probe повторяется внутри runtime activation после durable intent, чтобы отказать при гонке внешних изменений. В тестах отдельно проверено, что негативные случаи не вызывают `record:prepared`, `record:requires-review`, Config::save или изменение firewall. Это только безопасное предотвращение ложного зависания; автоматическая live migration legacy→common и FreeBSD owner-live ещё требуют проверки.

**`v0.5.2_42` — read-only свидетельства процессов общего движка и пяти Voice-профилей.** Единственный существующий endpoint `voice/inspect` после подтверждения общего sealed owner и kernel IPFW дополнительно проверяет PID `dvtws2`, PID supervisor и точное совпадение установленного `runtime-v2/voice-plan.json` и `dvtws.args` с тем же sealed release. Имена включённых профилей сопоставляются одновременно с `voice-plan.profiles`, `capture.voice` и фактическими IPFW таблицами. Для всех пяти служб возвращаются отдельные `configured`, `capture_verified`, `runtime_state`, `media_verified=false`; для всей операции — `runtime.state`, `engine_verified`, `supervisor_verified`, `source_verified`, `call_verified=false`. Это НЕ пять независимых демонов и не подтверждение прохождения STUN, медиа или звонков. Нет новых писателей, WAL или изменений GUI. После контрольных тестов требуется FreeBSD owner-live/call acceptance.

**`v0.5.2_41` — read-only native common IPFW inspection:** существующая `voice/inspect` теперь различает legacy IPFW ledger и новый подтверждённый common owner из единого durable journal. Когда owner committed (либо у `restored` есть предыдущий committed owner), инспектор подтверждает целостность source bundle, совпадение page/dependencies/changed_fields с sealed plan и фактические kernel IPFW правила/таблицы по manifest общего release; при совпадении возвращает `state=ready`, `source=native-common`, `condition=common-ipfw-verified-only`, **`can_activate=false`**. Все pending-фазы немедленно возвращают `interrupted`, без обращения к IPFW. Чужие или частичные правила остаются blocked; если common owner отсутствует, сохраняется legacy inspection. Это статус только IPFW, НЕ подтверждение живых dvtws2, успешного STUN или звонка. GUI, ТЗ, FD9 runtime и native Config не изменены. Запрошена проверка CI ревизии `_41`, живые FreeBSD tests отдельно.

**`_40` — устранение опасного ложного rollback после native Config save.** `SharedConfigCommit::persist()` теперь классифицирует исключение на повторной блокировке Config, построении модели, чтении saved Config и последующей разблокировке как `SharedConfigSaveUncertain`, а не pre-save error. Корневой worker проверяет сериализацию и полную запись JSON receipt; ошибки после подтверждённого сохранения возвращают код 70 и оставляют журнал на проверку. Отрицательные PHP-тесты моделируют сбой relock после реального сохранения и несерилизуемое подтверждение. Автоматический откат runtime при уже записанном Config запрещён. FreeBSD owner-live квалификация всё ещё нужна.

**v0.5.2_38–_39:** root PHP staging и native Config worker теперь самостоятельно проверяют оригинальный FD9: inode, владение root, удерживаемый flock. Не появляется новый lock, Config writer или WAL. Linux тест проверяет заблокированный FD9, свободный, чужой и symlink. Полный CI на `_37` завершился PASS для Voice candidates, но Project не прошёл позднюю Strategy Lab matrix из-за устаревшей метки пакета `_28` в PROJECT_STATE; `_39` синхронизирует primary metadata и добавляет ранний тест, чтобы предотвратить повторение. FreeBSD owner-live, полноценное mutating-phase recovery и выпуск релиза ещё не подтверждены.

В `_29`–`_37` устранён неисправный CI YAML, который скрывал выполнение полной CI матрицы. Устаревшие регрессии OFF-only Voice и legacy reconfigure Strategies переведены на ожидаемый **общий** ON/OFF native FD9 контракт, тесты холодного восстановления/Stop/Restart проверяют фактические фазы и коды отказов, а не заблокированное состояние фиктивного mock. Voice candidates PASS на `_37`; общий Project и FreeBSD package требуют отдельной проверки. Публичные Apply endpoints уже подключены в `_27`–`_28`, но до реальной FreeBSD appliance qualification статус стадии — source-integrated, not owner-accepted.

Подэтапы `_26`–`_28`: internal `shared-apply-run` объединил native candidate staging/build и execute в один оригинальный FD9. В stored `plan.json` добавлено поле `page`; native Config worker требует совпадения страницы перед preflight/save. Действие `zapret shared_apply` — единственная bounded base64url configd точка входа. Без правки frontend штатные `VoiceController::applyAction` и `SettingsController::applyAction` вызывают её после pure model validation; отпускают PHP Config lock до root FD9, а worker повторяет snapshot и validation. В Strategies сохранены normalizeIpList/normalizeDomainList и прежний формат ответа. В Voice нет прежней записи OFF-only перед `reconfigure` — Voice ON теперь попадает в общий кандидат. Успешный GUI-ответ требует финальный `applied-id`, при отказе не обещается автоматический rollback. Всё ещё нужны live FreeBSD qualification, безопасная миграция текущего legacy runtime, recovery mutating-фаз и статусы по ТЗ. Нет релиза и разрешения на эксплуатацию.

Подэтап `_25`: штатные `stop` и `restart` теперь отличают native common committed owner от legacy runtime в original FD9 service_with_lifecycle_lock. Native `stop` не перезаписывает OPNsense Config и не пытается очистить неизвестные IPFW правила, а использует прежний обратимый IPFW transaction с желаемым empty manifest; проверяет полный installed release, sealed source, Config и engine/monitor state. `restart` запускает после того же stop прежний native common boot. Ошибка проверки или промежуточная неудача не ведёт к legacy fallback. Это не завершает powercut recovery при partial native stop и не включает public GUI Apply.

Подэтапы `_23`–`_24`. Единственный durable journal переносит предшествующего committed common owner через повторный Apply и безопасный `restored`. Благодаря этому ранний rollback над native engine больше не запускает legacy. Для `config-saved` штатный FD9 проверяет полный bundle seal, saved native Config, отсутствие engine/monitor и пустой IPFW; только тогда запускает прежний общий runtime и доводит journal до `committed`. При неизвестном live ownership сохраняется запрет любых действий, old-PoC fallback исключён. Следующие этапы: mutating-phase recovery, native stop/restart, GUI Apply и appliance acceptance.

Подэтап `_22`: исправлен точный CLI-regex в штатном `recover-prepared` и добавлена failure-path проверка на Python. Это не расширяет разрешённые recovery-фазы: только source-intact `prepared` до начала мутаций может перейти в `restored`. Неподтверждённая runtime/Config/IPFW операция по-прежнему запрещает legacy startup.

Подэтап `_21`: самый ранний power-cut после `prepared` безопасно и автоматически закрывается только при root FD9, целостном sealed candidate, неизменном identity и повторной проверке journal. До записи durable `activating` исполнитель не совершает runtime/Config/IPFW мутаций, поэтому разрешено `prepared → restored` и затем обычный start через old guard. `activating/activated/config-saved` остаются `blocked`, никакого общего автоматического rollback без независимых Config/kernel/engine witnesses. Результаты тестируются на actual lifecycle wrapper и isolated operation-store.

Подэтапы `_18`–`_20`: внутренний full Config/plan/release после общего detached build получает один content-integrity seal, который проверяется перед активацией kernel и снова до native Config save; неизвестные/изменённые файлы отвергаются без произвольного fallback. Успешно committed native owner теперь может быть повторно запущен штатным `start/reconfigure` под тем же FD9 при совпадении journal, saved OPNsense Config и sealed release. Старый Telegram PoC не запускается поверх общего owner. `service_with_lifecycle_lock` покрыт собственным shell fault-injection тестом. Незавершённые фазы после power cut ещё не восстанавливаются автоматически, stop/restart и обе публичные GUI-кнопки остаются в работе.

Подэтапы `_14`–`_17`: PHP `shared_apply_config.php` — единственная native Config preflight/save seam на основе сохранённого plan и свежей модели. В штатном `zapret_service.sh` один FD9-хозяин `shared-apply-execute` выполняет фазовую durable транзакцию: loaded plan → real runtime activate → shared native Config save/readback → shared IPFW commit. Исключение backend pre-save = 69 допускает rollback только после подтверждённого `apply_runtime_restore`; после save unknown и post-save failure операция остаётся review-blocked. `_16` защищает legacy lifecycle от запуска поверх committed common owner; только новый common Apply с root FD9 может подготовить следующего owner. `_17` проверяет единый shell-код fault injection. Пока не готова надёжная crash resume/normal boot, **публичный Voice ON и кнопки не переключены**.

Подэтап `_13`: устранён пропущенный источник нового runtime — полноценный detached Config XML теперь рендерится **штатным OPNsense Python template system** в собственный приватный target root, а не через `configctl template reload` текущего Config. Один внутренний FD9 маршрут `shared-apply-build` делает: decoded request → locked native Config `SettingsApply` → owned-fields candidate/full XML → штатный offline `OPNsense/Zapret` template (+TARGETS) → `orchestrator_build_release(..., shared-candidate, candidate.xml)`. Это весь common candidate и все пять сервисов из той же модели; live Config/IPFW/engine не изменяются. До stage exit/UI: связать подготовленный plan/release с единой durable операцией и runtime switch, native save, rollback/reboot recovery.

Подэтап `_12`: существующий FD9 dispatcher получил внутреннее `shared-apply-record` без configd action; одна общая операция записывает проверяемые фазы в root-owned 0700 directory через атомарную замену 0600 JSON и fsync. Read-only `voice_cutover_guard.py` проверяет этот же common record наряду с bounded old PoC evidence, не создавая второй watcher/worker. `prepared`/`activating`/`activated`/`config-saved`, неопределённость и испорченное evidence запрещают lifecycle, подтверждённые `committed`/`restored` разрешают. Критический незавершённый рубеж: присоединить `SharedConfigCommit::transact()` к root-owned FD9 worker, staged candidate/full generator, native Config transaction и recovery; до этого GUI ON остаётся OFF-only.

Подэтап `_11` собрал в существующем `apply_settings.php` общую последовательность Config/runtime (`SharedConfigCommit::transact`), без создания второго внешнего coordinator. Обязательные зависимости worker: проверка того же FD9, **один** durable operation record, вызовы существующего runtime bridge. До native Config save откат разрешён только после подтверждённого успешного `activate`; при неопределённой активации, частичном Config save или неполном post-save commit сохраняется состояние «requires-review», а не выдуманный success. Порядок и отказ проверяются PHP fault cases; следующий рубеж — физический FD9 worker/receipt/recovery и обе GUI кнопки.

Подэтап `_10`: согласована фактическая двухфазная IPFW проверка. `verify-staged` под FD9 проверяет активные правила, новые таблицы и неизменные старые таблицы в staging до Config save. `verify` остаётся строгой окончательной проверкой без staging после commit. Этот рубеж не подключает публичный Apply и не заменяет durable recovery.

Подэтап `_9`: компонент `apply_settings.php` вызывает штатные `model->serializeToConfig(false, true)` и `Config::save()` только после повторной проверки актуального поколения и own-field merge. После освобождения lock внутри `Config::save` он приобретает новый Config lock, проверяет фактически сохранённую модель и сообщает об обнаруженной гонке. Ошибка native save, которая могла произойти после части записи, явно требует review и не выдаётся за rollback. Это лишь внутренняя часть привилегированного worker; публичный Apply/FD9 orchestration и единое прерываемое recovery пока не подключены.

Подэтап `_8`: общий чистый `mergeForCommit` готовит штатный `model->setNodes` из свежей модели, а не из устаревшего whole-model preview. Runtime-dependent поля проверяются через generation SHA, изменение unrelated модельных групп не теряется. Полное native save/history и recovery ещё не подключены.

Подэтап `_7`: обе формы создают in-memory detached полный системный XML через общий `SettingsApply` и один существующий scoped XML serializer. Разрешены только own whitelist, оба reject чужие изменения; unrelated OPNsense узлы сохраняются. Это подготовка для native Config/FD9 worker, не persistence и не activation.

Текущая задача `_4`: объединить in-memory подготовку обеих форм и дать будущему worker проверяемую generation/dependency границу без Config/runtime/IPFW-записей. Проверка — действующий PHP сценарий обеих форм, whitelist, shared Telegram IPSET, unrelated OPNsense change и stale generation. Следующая кодовая задача: native worker под FD9, Config lock/save и полный runtime switch/rollback. Эти подзадачи не закрывают этап до работающих GUI Apply.

**Результат:** штатная кнопка применяет всю Voice-форму и все пять сервисов; «Стратегии» используют тот же Apply и не теряют Voice. Полный цикл OFF→ON / edit ON / add / remove / all OFF / repeat работает.

**Зависимости:** этапы 1–2. **Код:** два Settings/Voice controllers, payload/snapshot helpers, общий Apply worker/adapter, `zapret_service.sh`, `actions_zapret.conf`; минимальная привязка уже существующей кнопки к полному ответу.

- В начале выполнить ограниченную проверку native PHP/Config/FD9 контракта из раздела 3 на целевой платформе. После неё зафиксировать окончательный порядок работы в небольшом интеграционном сценарии, не в новом общем rule book.
- Заменить нынешнее save-then-reconfigure и восстановление целого старого `oldNodes` у «Стратегий» общей последовательностью. Voice Apply перестаёт отвергать любой ON.
- Использовать свежий snapshot, own-field merge и повторную проверку зависимостей непосредственно перед мутацией. Гонки двух форм, shared Telegram IPSET и unrelated Config edits имеют явный результат без lost update.
- Убрать необходимость «сначала все OFF, потом enable-mask». Preview/validate остаются без побочных эффектов. Существующий saveDraft, если ещё нужен GUI, использует тот же общий путь и не становится обходом валидации/сохранения.
- Реализовать native save/history и общий rollback при engine/firewall/Config failure. Статус сохранения, применения, сохранённого stopped состояния, stale request и failed rollback различается в API.
- All-OFF и повторный Apply считаются штатными действиями. При global OFF/исходном Stop сохранять preferences без запуска. Runtime отсутствующего engine не устанавливать автоматически кнопкой Voice Apply.

**Переход:** через настоящий API/GUI пройдён полный цикл всех пяти сервисов, изменение Strategies сохраняет Voice, обычная ошибка возвращает прежнее состояние, ошибка возврата честно видна. Это первый функциональный рубеж полной формы; boot/миграция ещё не объявляются принятыми. Проверки: общий Apply с native OPNsense Config, own-field concurrency и ограниченные fault cases, а не новая серия private receipts.

### Этап 4. Общий lifecycle, normal boot и ограниченная миграция

**Результат:** обычные start/stop/reconfigure/restart/runtime-failure/boot обслуживают ту же модель; старый Telegram PoC больше не отдельный источник ON.

**Код:** `zapret_service.sh`, `orchestrator.sh`, `firewall.sh`, `atomic.sh`, launcher/supervisor, штатные syshook/package hooks, `Zapret.xml` и native migration при необходимости; `telegram_voice.sh` и существующие configctl compatibility commands.

- Подключить общий generator/firewall ко всем путям, включая отсутствие previous runtime и stopped start. Собственный PID проверяется перед stop; чужой или неоднозначный состав процессов не останавливается по предположению.
- Общий Stop/runtime-failure убирает все свои Voice/ordinary runtime-правила и процессы, сохраняя preferences. Healthy committed operation не блокирует start/reconfigure навсегда.
- Normal boot читает постоянные ON/OFF и `general.enabled`, собирает runtime до ручного действия. Использовать текущий штатный hook, без второго Voice daemon, Cron или независимого восстановителя.
- Прерывание между runtime switch и Config save, внутри native save и до финального commit проверять в одном общем recovery. Выбирать подтверждённую consistent версию; повреждённый/чужой Config или неоднозначное владение требуют явного отказа. Родной backup/history используется по контракту Core; самостоятельный whole-XML restore поверх чужих правок не вводится.
- Миграцию выполнить одной ограниченной процедурой с native model migration/version metadata. Old marker может быть входом первого подтверждённого импорта, но после успешного commit не участвует в определении ON. Удаляется только подтверждённый собственный старый marker/runtime artifact и только после готовности возврата.
- `telegram_voice_*` совместимо меняют ту же модель и вызывают общий lifecycle; старую постоянную строку нельзя принимать за доказательство успеха.
- Частные незавершённые журналы неопубликованной `_174` не поддерживать как второй вечный продуктовый протокол. Их наличие диагностируется; безопасный переход или ручное восстановление имеет явную конечную границу, без автоматического удаления неизвестного evidence.

| Вход миграции | Ожидаемый результат |
|---|---|
| Подтверждённый работающий old PoC ON | Однократный импорт Telegram preferences и переход на общий runtime без двойного prepend/process; ошибка возвращает previous |
| Явный old OFF | OFF сохраняется, самопроизвольного включения нет |
| Marker потерян после reboot, выбора недостаточно | Не угадывать ON/OFF; явная диагностика и выбор владельца, затем обычное сохранение |
| Чистая установка | Пять OFF, штатные пустые/исходные поля, без marker и лишнего capture |
| Уже успешно мигрировано | Повторный импорт не выполняется; источник — постоянная модель |

**Переход:** матрица миграции и normal lifecycle пройдена на OPNsense VM; normal reboot ON/OFF/global OFF проверен до ручного Apply. Crash cases подтверждают recovery/честный отказ, не ложный success. Package upgrade сохраняет исходное running/stopped поведение общей службы. Окончательная owner-live приёмка остаётся в этапе 7.

### Этап 5. Фактические статусы и завершение API-привязки

**Результат:** существующая страница показывает предусмотренные ТЗ результаты, ошибки и фактическое состояние пяти сервисов; временная логика «применение только OFF» удалена.

**Код:** `VoiceController.php`, общий runtime/inspect API, `voice.volt` и только необходимые технические bindings. Формы, меню, разметка и стили не перепроектируются.

- Различать saved preference и active profile: галочка ON сама по себе не означает фактический работающий capture. Сопоставлять сохранённую/активную версию, выбранный WAN, профили, IPSET, правила и состояние общей службы.
- Использовать существующие строки и места статусов, вернуть per-service данные через API. Общий TCP-счётчик не служит доказательством Voice capture.
- Показать validation/stale/apply/rollback/recovery ошибки на предусмотренном месте, включая сохранение при stopped/global OFF. Обновить snapshot после корректного результата.
- Preview/validate/inspect/recoveryStatus остаются безопасными; не объявляют активацию по наличию старого receipt. Удалить временные OFF-only тексты и ошибочные assumptions в JS; сохранить RU/EN.

**Переход:** форма соответствует ТЗ, обе страницы перечитывают сохранённое состояние; сообщения совпадают с фактическим runtime. Продемонстрирован полный GUI сценарий и отказ, без новых полей или сокращённых возможностей. Проверяются ответы/наблюдаемое поведение, а не неизменность старых ошибочных строк.

### Этап 6. Удаление отдельной Voice-инфраструктуры

**Результат:** поставляемый пакет имеет один рабочий backend; прежняя private архитектура не остаётся скрытой зависимостью или вторым путём управления.

**Зависимости:** этапы 3–5 работают через общий путь. **Код:** неиспользуемые `voice_native_*`/`voice_cutover_*`, old legacy framework/CLI routes, отдельные writers/guards, ненужный staging bundle; связанные tests/configd/CI entries.

- Построить конечную карту вызовов из GUI/API/configd/boot/CLI и inventory устанавливаемых файлов. Для каждой группы отметить keep / fold into common / delete; удалять после проверки отсутствия используемого caller.
- Перенести существенные failure/concurrency/ownership/power-cut сценарии в общие тесты. Сохранить пригодные validators/compiler/adapter и точечные процессные guards; не портировать каждый старый тест вместе с его протоколом.
- Вывести old marker prepend, отдельный raw Config writer и здоровый-state blocking guard. Для legacy evidence оставлять только необходимую диагностику/ограниченный переход, не самостоятельную ordinary Apply цепочку.
- Обновить Linux/FreeBSD jobs, package inventory и checks, которые сейчас требуют удаляемые имена/receipt. Git и исторический ledger сохраняют прежний код/доказательства; копия удалённого framework в active package не нужна.
- Проверить конечную сложность: один Config saver, один full generator, один firewall owner, один launcher/supervisor, один lifecycle lock и один путь восстановления операции.

**Переход:** входные точки обеих страниц и службы проходят только через общий backend; удаляемые файлы не устанавливаются и не импортируются; сохранённые сценарии поведения проходят. Представить source/runtime/test/docs diff отдельно: число строк или тестов само по себе не является приёмкой.

### Этап 7. Полная приёмка, пакет и завершение PR

**Результат:** выполнено полное ТЗ GUI/CONFIG/BOOT; PR можно оценивать как завершённую разработку, отдельно от поиска рабочего media preset.

**Среда:** сначала контролируемая OPNsense VM с целевым engine, затем owner-live appliance по действующим правилам. Только offline tests не закрывают этот этап.

- Выполнить все десять обязательных проверок раздела 10 ТЗ и матрицу ниже: пять сервисов, разные корректные IP/порты, ошибки и чужие объекты, обе страницы, нормальный reboot до ручного enable.
- На фактическом WAN проверить forwarded LAN, другой LAN/VLAN, local UDP и SOCKS-created UDP отдельно: выбранный профиль/пакетный эффект, original-pass/action-OFF, отсутствие capture для чужих IP/портов/WAN и повторного divert.
- Проверить один процесс, сохранность A2/non-STUN и существующих LAN/SOCKS TCP-to-parent сценариев. TNAS/Docker остаются ручными; не внедрять маршруты/autostart для прохождения теста.
- Проверить native Config history/backup/notification, upgrade и чистую установку, отсутствие лишних файлов/таблиц/процессов. Приложить наблюдения и точную версию окружения.
- Выполнить необходимые CI и FreeBSD package checks на окончательном HEAD. После завершения сохраняются текущие правила review/merge/testing/stable publication; подготовка этого плана не разрешает публикацию WIP или изменение работающего appliance.
- Зафиксировать GUI/CONFIG/BOOT результат отдельно. Telegram `MEDIA_PASS`/`CALL_PASS` и квалификация Discord/X/SIP требуют собственных сетевых опытов; нельзя объявлять их по успеху сборки. Кампания стратегии не блокирует приёмку корректной общей страницы и продолжается отдельно.

**Переход:** нет открытого обязательного GUI/CONFIG/BOOT пункта ТЗ; остаточные исследования preset явно отделены. PR #328 перестаёт быть Draft только по правилам проекта после этой границы.

## 5. Связь приёмки ТЗ с этапами

| Пункт раздела 10 ТЗ | Что предъявляется | Этапы |
|---|---|---|
| 1. Сохранение двух форм, OFF-текст, no lost update | Native save, повторное открытие, stale формы и shared Telegram IPSET | 3, 5, 7 |
| 2. Валидация и native ресурсы | Ошибка поля/строки без изменения live; installed engine принимает разрешённый candidate | 1, 3, 7 |
| 3. Профиль/table/порты/WAN и original-pass | Каждый сервис и несколько одновременно; чужой scope не получает действие | 1, 2, 7 |
| 4. LAN/VLAN/local/SOCKS UDP | Отдельные пакетные наблюдения на выбранном WAN | 2, 4, 7 |
| 5. Ordinary, один engine, no broad capture | Ordinary сохранён; один общий путь без лишнего prepend/divert | 1, 2, 4, 6, 7 |
| 6. Failed Apply/коллизия/Stop | Согласованный previous state, чужие объекты целы, preferences сохранены | 2–4, 7 |
| 7. Upgrade/миграция/повтор/CLI | Пять явных случаев миграции, идемпотентность и реальные ответы совместимых команд | 3, 4, 7 |
| 8. Reboot до ручного enable | ON/OFF/global OFF восстановлены по сохранённой модели | 4, 7 |
| 9. LAN/SOCKS TCP и ручная лаборатория | Регрессия существующего пути без изменений маршрутов/Docker | 7 |
| 10. GUI/CONFIG/BOOT отдельно от media | Раздельные результаты без ложного объявления рабочего preset | 7 и отдельная кампания |

## 6. Проверки и управление разработкой

Проверки организуются по шести видам поведения: (1) модель/own fields/concurrency, (2) compiler и полный runtime, (3) firewall scope/ownership, (4) общий Apply/failure/rollback, (5) lifecycle/migration/boot, (6) GUI/API/package/live capture. Это шесть групп, не требование шести или 116 отдельных тестов. Существующие полезные сценарии повторно используются; тест, который фиксирует только удаляемый private helper, не сохраняется ради счётчика.

Внутри этапа запускать подходящие проверки изменённого поведения и обязательные project checks. Полную дорогую live matrix выполнять на интеграционных рубежах и окончательном HEAD; повторять отдельную проверку при изменённом поведении, новом отказе или новой платформе. Реальные native/FreeBSD и power-cut границы не заменяются mocks.

Контроль исполнения:

1. Перед кодом этапа записать в этом плане краткую задачу: сценарий, конечный diff scope, проверка успеха. Промежуточные технические подзадачи не превращаются в новые самостоятельные этапы.
2. Закрывать этап только по указанному результату. Commit helper/manifest/теста не означает процент готовности пользовательского сценария.
3. Один логический объём в текущей feature branch/PR; каждый commit с packaged code получает следующую ревизию по правилам проекта. Семь этапов не обещают ровно семь commit и не назначают заранее номера версий.
4. После двух последовательных технических поставок без продвижения критерия приёмки остановить расширение реализации и разобрать конкретный блокер общего пути. Следующая работа должна закрывать сценарий или предъявлять пересмотр плана; новая цепочка журналов не считается прогрессом.
5. Для нового persistent artifact/координатора сначала показать воспроизводимый отказ и почему существующий общий механизм его не покрывает. Не добавлять защитный слой лишь потому, что его можно отдельно протестировать.
6. Текущий следующий шаг хранить в START_HERE; выполненный факт — в PROJECT_STATE; событие/доказательство — в существующем working ledger. Детали плана не копировать во все документы. Отчёт этапа: результат, затронутый код, проверка, остаточный риск, следующий шаг.
7. Изменение архитектуры, frontend требований или объёма ТЗ возвращать на обсуждение владельца. Обычные локальные решения внутри согласованного этапа не требуют повторного согласования каждого helper.

Не задавать календарный срок по числу имеющихся строк или тестов. Оценку оставшихся работ уточнять после интеграционного рубежа этапа 3: тогда уже существует полный Apply, а оставшийся объём — lifecycle/миграция, статусы, удаление и приёмка. Если этап 3 не достигается, это обнаруженный блокер архитектуры, а не повод бесконечно объявлять готовность внутренних модулей.

## 7. Условия согласования и исторический материал

Приняты к выполнению три технических решения: общий привилегированный Apply под существующим FD9 со штатным Config save; проверка/активация full runtime перед финальным сохранением с ограниченным общим recovery; перенос нужных гарантий и последующее удаление отдельной Voice-инфраструктуры. Предлагаемая очередность — 1 → 2 → 3 → 4 → 5 → 6 → 7. Этапы 1–2 проверяют полный кандидат и перехват, этап 3 даёт полный публичный Apply; они не сокращают итоговое ТЗ.

Таблицы и порог двух технических поставок управляют этой переделкой и не создают новые общие правила `DEV-*`/`DOC-*`. Поручение владельца начать программирование по плану снимает прежнюю границу согласования; архитектура и ТЗ не пересматриваются.

Прежний большой план сохранён в [истории линии](../history/stages/v0.5.1/WORKING_LEDGER.md#архив-прежнего-плана-voice-перед-объединением-backend) и [неизменяемом исходном снимке](https://github.com/Tolian82/os-zapret2-restyle/blob/bf20957715b5dc7f965c207d6def8fb1411f7298/docs/architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md). Он содержит полезные сценарии и доказательства, но не является текущей очередью. Для текущих фактов читать [PROJECT_STATE](../PROJECT_STATE.md), для следующего действия — [START_HERE](../START_HERE.md), для полного неизменного результата — [ТЗ страницы](VOICE_TRANSMISSION_GUI.md).
