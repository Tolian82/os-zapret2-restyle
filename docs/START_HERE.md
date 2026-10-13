# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_6`. `VERSION=0.5.2`; `PLUGIN_REVISION=4`. Линия состояния — `v0.5.x`. 13.10.2026 владелец поручил открыть новый этап общего Voice/Strategies backend без релиза и перенести старые отчёты из активной документации в историю.

## Текущая граница

В `_6` исправлен порядок безопасного Apply: наличие собственного IPFW подтверждается до `firewall_prepare`; кандидат внутри active runtime отвергается. Регрессии обоих отказов добавлены. GUI ON не подключён до native Config/recovery.

В `_5` сервис получил общий `apply_runtime.sh`: после полного candidate build можно переключить один dvtws2/launcher/supervisor и общий IPFW через install/verify, сохранив предыдущий runtime и таблицы до native Config commit. При отказе предусмотрен проверяемый rollback. Код ещё не используется GUI: для безопасного подключения требуются штатный Config worker и восстановление после прерывания операции.

В _4 оба PHP-контроллера готовят полную модель через общий чистый `Api/SettingsApply.php`: применяют только whitelist своей формы, вычисляют карту изменений и сохраняют свидетельство зависимости от одного поколения Voice/Strategies/hostlist/general. `requireUnchanged` отказывает перед будущей активацией при изменении этого поколения, но не блокирует чужие разделы OPNsense. Проверки обеих форм добавлены в действующий PHP тест. Это код подготовки, а не публичное применение ON: FD9-worker/native Config save/runtime activation ещё не подключены.

Этап 1 сохраняется: общий candidate build создаёт полный runtime пяти Voice-сервисов и ordinary Strategies. В `_3` общий `firewall.sh` получил `firewall_shared_runtime install|rollback|commit|verify` через существующий IPFW adapter. Владение выводится из `voice-plan.json` и ordinary port artifacts предыдущего установленного release; отдельный Voice ledger не используется.

Install проверяет живые объекты до изменения, сохраняет stage-таблицы для возврата до общего commit. Commit удаляет только подтверждённые прежние/stage-таблицы; rollback возвращает previous. Первое включение допускает отсутствие previous; Stop/global OFF используют пустое желаемое состояние. Проверяются фактические правила/таблицы после установки, отката и очистки. CLI требует FreeBSD root и исходный удерживаемый FD9. Общая проверка lock перенесена в adapter; private executor делегирует ей.

Полный generator → firewall цикл проверен с подставным kernel adapter: все пять, обновление IPSET, повтор, все Voice OFF, Stop, отказ/возврат и чужие объекты. Это не доказательство реальных WAN-пакетов или power-cut. Normal service/GUI пока не вызывает новый путь; интеграция — этап 3. PR #328 Draft; frontend и ТЗ сохраняются.

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

Stable Web/pkg: `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`; опубликованный testing: `v0.5.0_3`. Открытие `v0.5.2_6` не публикует новый пакет и не подтверждает GUI/CONFIG/BOOT или MEDIA_PASS/CALL_PASS.
