# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.3_1`. `VERSION=0.5.3`, `PLUGIN_REVISION=1`. Владелец 17.10.2026 открыл исправляющий этап и поручил сначала записать подход/план, затем выполнить его. Это переход этапа разработки, не публикация релиза.

## Установленный результат и блокер

Опубликованный `v0.5.2_194` установлен владельцем через GUI на OPNsense 26.7.3_8 / FreeBSD 15. Переход из меню Voice Transmission на `/ui/zapret/voice` показывает «Страница не найдена». **Приёмка открытия GUI не пройдена**, прежнее утверждение о завершённой странице снято. Успешные CI и [публикация](verification/evidence/2026-10-16-v0.5.2-release-publication.md) остаются фактами только своих уровней.

В исходниках релиза меню требует UI `VoiceController::indexAction`, но присутствует только `IndexController::voiceAction` и отдельный API-контроллер. Штатный Router OPNsense не переводит такой URL в action IndexController. Исправление ещё не внесено.

## Точное следующее действие

Выполнить шаги 1–3 [утверждённого плана v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md): исправить штатный UI route, проверить меню/права/form/view и RU/EN, добавить целевую проверку маршрутов на настоящем Router и распакованном `.pkg`, затем доставить исправляющее обновление через GUI-репозиторий. Сначала документационный переход `_1` интегрируется без release trigger; packaged-code исправление получает следующую ревизию. Это сохраняет штатное правило перехода VERSION с `_1`.

До фактического открытия установленной страницы результат называется «исправление подготовлено; работа установленной страницы не подтверждена». Затем выполняется полное исходное ТЗ: пять профилей, сохранение/Apply, общая служба/IPFW/boot; STUN/MEDIA/CALL принимаются отдельно. Найденный блокер не обходится новым этапом или перепроектированием общего backend.

## Минимальное чтение

[План v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Приёмка](VOICE_CODE_COMPLETION_GATE.md) · [Полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md). Действуют `DEV-007`, `DEV-011`, `DEV-018` и `CHAT-003`; текущие факты — в [PROJECT_STATE](PROJECT_STATE.md), хронология — в [ledger](history/current/v0.5.x.md).
