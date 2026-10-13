# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_20`. `VERSION=0.5.2`; `PLUGIN_REVISION=20`. Линия состояния — `v0.5.x`. 13.10.2026 владелец поручил открыть новый этап общего Voice/Strategies backend без релиза и перенести старые отчёты из активной документации в историю.

## Текущая граница

В `_18` общий detached Config/plan/release получил отдельный проверяемый integrity seal **в том же** shared-work ID, а не второй WAL: SHA-256 candidate.xml, plan.json и полного дерева release, atomically/fsync сохранение. Проверка выполняется до `prepared` и непосредственно перед native Config save; изменение кандидата после активации вызывает проверяемый runtime restore или оставляет `requires-review`. `_19` добавил штатный native boot для только `committed` owner: оригинальный FD9, целостность seal, readback saved Config и прежний общий `apply_runtime_activate/commit`. `_20` добавил тест настоящего `service_with_lifecycle_lock` с проверкой отсутствия legacy fallback при committed/pending/foreign owner. Power-cut recovery нетерминальных фаз и публичные GUI-кнопки обеих страниц пока ещё не подключены.

В `_14` добавлен `shared_apply_config.php`: root OPNsense Config worker повторно читает заранее сохранённый form plan под штатным lock, проверяет fresh dependency generation и все owned changed fields. `preflight` ничего не сохраняет; `save` вызывает тот же `SharedConfigCommit::persist()` и строго различает pre-save отказ 69 от неопределённой native Config записи 70. В `_15` `zapret_service.sh shared-apply-execute <id> <page>` свёл **одну** реальную внутреннюю транзакцию под исходным FD9: preflight → durable prepared/activating → `apply_runtime_activate` → durable activated → native Config save → durable config-saved → `apply_runtime_commit` → committed. Любой uncertain outcome оставляет recovery evidence, pre-save отказ с подтверждённым runtime restore завершает `restored`. В `_16` существующий lifecycle guard дополнительно запрещает legacy start/reconfigure при успешно `committed` общем runtime, а исключение для следующего common Apply требует root-held FD9. В `_17` введён сквозной shell fault-injection тест самого сервисного исполнителя (а не переописанной логики). По-прежнему **не подключены**: публичные кнопки обеих страниц, автоматическое reboot recovery, native boot routing, миграция старого PoC, корректные статусы/полная приёмка. Эти недостающие рубежи нельзя обходить простым включением Voice ON.

В `_13` реализована недостающая **полная native offline сборка** из текущего OPNsense Config + запроса формы. `shared_apply_request.php` читает Config под штатным lock, проверяет baseline и поля формы через существующий `SettingsApply`, создаёт полный detached XML и собственный план в root-only `/var/db/zapret2/shared-work/<id>`. `shared_apply_render.py` использует штатные модули `modules.config.Config` и `modules.template.Template(target_root_directory=...)`, рендерит `OPNsense/Zapret` с проверкой неизменного списка +TARGETS, не вызывает live `configctl template reload`. В сервисе `shared-apply-build` последовательно вызывает staging, template и штатный `orchestrator_build_release` с вариантом `shared-candidate` **под одним FD9**. Не копируются/не переписываются live Config, IPFW, dvtws2, release. Добавлены unit и GUI-form candidate tests. Следующий обязательный шаг — привязать итоговый release и план к единой фазовой транзакции `transact`, запустить runtime, выполнить native save, durable commit/recovery и подключить кнопки обеих страниц. Публичный Apply пока прежний.

В `_12` появилось долговечное единое состояние общего Apply — `backend/shared_apply_operation.py` в `/var/db/zapret2/shared-apply/operation.json`. Запись каждой разрешённой фазы происходит атомарно через fsync + rename + fsync каталога, только root под уже существующим FD9; сервис содержит внутренний `shared-apply-record`, не добавленный в configd. Тот же штатный `voice_cutover_guard.py` теперь запрещает start/stop/reconfigure при pending/corrupt/orphan/symlink evidence общей операции. Терминальные `committed` и `restored` не блокируют обычный lifecycle; опасные результаты `requires-review`/`restore-failed` блокируют. Test suite проверяет порядок фаз, identity, восстановление, запрет перезаписи незавершённого состояния, сохранение доказательств и отсутствие CLI-мутаций без root FD9. Важная граница: PHP `transact` ещё не соединён с вызовами общего worker и реальным interruption recovery, поэтому публичный Voice ON не включён.

В `_11` внутренний `apply_settings.php::SharedConfigCommit::transact()` связывает общий runtime и native Config в фиксированном порядке под требованием существующего FD9: fresh model check, durable intent callback, runtime activation, Config save/readback, IPFW commit, окончательная запись. Отказ до Config save вызывает проверяемый runtime rollback; неясный результат native save или ошибка post-save cleanup сохраняют право recovery вместо ложного rollback. В текущей ревизии FD9 guard, durable operation record и activation остаются обязательными callback-интерфейсами будущего привилегированного service worker, публичный GUI к ним ещё НЕ подключён. Сквозной PHP тест проверяет порядок фаз, отсутствие мутации без FD9/record, restore до save и честный review после uncertain save.

В `_10` устранён реальный разрыв общего IPFW Apply: после `install` staged-снимки старых таблиц необходимы до native Config commit. Поэтому общий adapter теперь предоставляет отдельную read-only `verify-staged` (проверка новых правил, таблиц и обязательных старых snapshots), а финальный `verify` используется только до установки и после rollback/commit. Покрыты реальные изменения IPSET, исчезновение/порча snapshots и сквозной shell rollback. Исправлен mock Strategy Lab lifecycle, который не создавал `apply_runtime.sh` и потому обрывал проверку до самого Strategy Lab.

В `_9` появился внутренний `src/opnsense/scripts/OPNsense/Zapret/apply_settings.php` — узкий компонент native `Config::save` с проверкой поколения, own-field merge `_8`, штатной историей/backup и post-save readback под новым flock. Save/IO race не трактуется как успешный откат: до подключения общего FD9 worker и interruption recovery он не вызывается GUI/configd. CI включает отдельный PHP тест native lock/save, no-op, stale and post-save conflict.

В `_8` добавлен чистый native-save merge для обеих страниц: `SettingsApply::mergeForCommit` заново проверяет зависимости, применяет только изменённые поля через существующие whitelist и сохраняет более поздние несвязанные изменения модели (например, Strategy Lab). Защита от injected Voice fields, stale divert port и неполного changed-map покрыта PHP тестом. Вызывать должен будущий привилегированный Config worker после получения FD9 и свежего Config lock. Никакого самостоятельного Config writer или публичного ON Apply не создаётся.

В `_7` обе формы могут сформировать один проверяемый detached `config.xml` через `SettingsApply::renderCandidateXml`. Расширен существующий XML renderer: Voice и Strategies имеют независимые whitelist полей, общую полную модель, проверку `changed_fields`, защиты от чужих узлов/DTD/дублированных mounts и no-op без перезаписи исходного XML. До native FD9 worker это остаётся только чистой подготовкой, не второй точкой persistence. Тест обеих форм дополнен сценариями порчи candidate и preservation.

В `_6` исправлен порядок безопасного Apply: наличие собственного IPFW подтверждается до `firewall_prepare`; кандидат внутри active runtime отвергается. Регрессии обоих отказов добавлены. GUI ON не подключён до native Config/recovery.

В `_5` сервис получил общий `apply_runtime.sh`: после полного candidate build можно переключить один dvtws2/launcher/supervisor и общий IPFW через install/verify, сохранив предыдущий runtime и таблицы до native Config commit. При отказе предусмотрен проверяемый rollback. Код ещё не используется GUI: для безопасного подключения требуются штатный Config worker и восстановление после прерывания операции.

В _4 оба PHP-контроллера готовят полную модель через общий чистый `Api/SettingsApply.php`: применяют только whitelist своей формы, вычисляют карту изменений и сохраняют свидетельство зависимости от одного поколения Voice/Strategies/hostlist/general. `requireUnchanged` отказывает перед будущей активацией при изменении этого поколения, но не блокирует чужие разделы OPNsense. Проверки обеих форм добавлены в действующий PHP тест. Это код подготовки, а не публичное применение ON: FD9-worker/native Config save/runtime activation ещё не подключены.

Этап 1 сохраняется: общий candidate build создаёт полный runtime пяти Voice-сервисов и ordinary Strategies. В `_3` общий `firewall.sh` получил `firewall_shared_runtime install|rollback|commit|verify` через существующий IPFW adapter. Владение выводится из `voice-plan.json` и ordinary port artifacts предыдущего установленного release; отдельный Voice ledger не используется.

Install проверяет живые объекты до изменения, сохраняет stage-таблицы для возврата до общего commit. Commit удаляет только подтверждённые прежние/stage-таблицы; rollback возвращает previous. Первое включение допускает отсутствие previous; Stop/global OFF используют пустое желаемое состояние. Проверяются фактические правила/таблицы после установки, отката и очистки. CLI требует FreeBSD root и исходный удерживаемый FD9. Общая проверка lock перенесена в adapter; private executor делегирует ей.

Полный generator → firewall цикл проверен с подставным kernel adapter: все пять, обновление IPSET, повтор, все Voice OFF, Stop, отказ/возврат и чужие объекты. Это не доказательство реальных WAN-пакетов или power-cut. Normal service/GUI пока не вызывает новый путь; интеграция — этап 3. PR #328 Draft; frontend и ТЗ сохраняются.

## Проверяемый блокер CI

На HEAD `_11` целевой job Voice candidates успешно завершён; отдельный guard `Pull request title` отказывает при проверке исторического коммита `02bd7df` с текстом `docs: Record v0.5.2_8 ...`, ожидая префикс `v0.5.2_8:`. Согласно действующему `GH-014` переписывание прошлой истории только для переименования ревизии запрещено. Не выполнять force-push или ослабление guard автоматически; данный конфликт требуется разрешить в пределах правил перед merge. Отдельный полный Validate Project ещё может содержать независимые failures; проверять latest-run evidence. Содержимое продукта и наличие ошибки commit subjects не смешивать.

## Следующее действие

**Этап 3 — общий Apply обеих страниц.** Следующий шаг — привилегированный PHP/FD9 worker и атомарная native Config-интеграция с повторной проверкой общего кандидата. До включения API подтвердить контракт lock/save на OPNsense 26.7.3, затем подключить full candidate и общий firewall к существующему orchestrator. Сохранить предыдущий release и stage-таблицы до полного commit; при engine/Config failure использовать общий rollback. Не добавлять отдельный Voice lifecycle/WAL/receipt.

## Минимальное чтение по текущей задаче

После обязательного порядка AGENTS читать только:

1. [План v0.5.2](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) — компоненты, этапы, проверки и контроль выполнения.
2. [ТЗ страницы](architecture/VOICE_TRANSMISSION_GUI.md), включая утверждённый раздел 12.
3. [ARCHITECTURE](ARCHITECTURE.md) — существующие общие точки интеграции; [Service architecture](architecture/ZAPRET2_SERVICE.md) при работе с сервисным API.

Для конкретного изменения затем читать соответствующие исходники и проверки. Исторические private модули и lab runbooks загружаются по доказанной необходимости текущего сценария, не всем списком.

## Контроль продолжения

Результат каждого этапа и необходимые проверки определены в [разделе 6 плана](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md#6-проверки-и-управление-разработкой). Контроль принят вместе с поручением на реализацию. Отчёт содержит результат ТЗ, изменённый код, проверку, остаточный риск и следующий шаг. Счётчики строк/тестов и новый helper не заменяют функциональный рубеж.

## История и публикация

Полные прежние документы сохранены в [архиве этапа v0.5.1](history/stages/v0.5.1/README.md). Они не входят в текущую очередь или обязательное чтение. Текущая хронология — [working ledger v0.5.x](history/current/v0.5.x.md).

Stable Web/pkg: `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`; опубликованный testing: `v0.5.0_3`. Открытие `v0.5.2_11` не публикует новый пакет и не подтверждает GUI/CONFIG/BOOT или MEDIA_PASS/CALL_PASS.
