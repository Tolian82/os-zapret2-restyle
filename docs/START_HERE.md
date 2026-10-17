# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.3_2`. `VERSION=0.5.3`, `PLUGIN_REVISION=2`. Владелец 17.10.2026 открыл исправляющий этап и поручил сначала записать подход/план, затем выполнить его. Переход `_1`, исправление `_2` и точная подготовка релиза интегрированы в `main`; полный [релиз `v0.5.3`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) и FreeBSD pkg-репозиторий опубликованы. Приёмка установленной страницы и голосового канала отдельно открыта.

## Установленный результат и блокер

Опубликованный `v0.5.2_194` установлен владельцем через GUI на OPNsense 26.7.3_8 / FreeBSD 15. Переход из меню Voice Transmission на `/ui/zapret/voice` показывает «Страница не найдена». **Приёмка открытия GUI не пройдена**, прежнее утверждение о завершённой странице снято. Успешные CI и [публикация](verification/evidence/2026-10-16-v0.5.2-release-publication.md) остаются фактами только своих уровней.

В исходниках релиза меню требует UI `VoiceController::indexAction`, но присутствует только `IndexController::voiceAction` и отдельный API-контроллер. Штатный Router OPNsense не переводит такой URL в action IndexController. В ревизии `_2` добавлен штатный `VoiceController::indexAction` и целевой тест настоящего Router 26.7; готовность установленной страницы остаётся неподтверждённой.

## Точное следующее действие

**Принять установленный `v0.5.3_2` на OPNsense:** после обновления из System → Firmware → Plugins зафиксировать `pkg info os-zapret2-restyle`, открыть «Передача голоса» из меню и напрямую по `/ui/zapret/voice`, увидеть форму пяти сервисов и загрузку настроек, отсутствие ошибок страницы/API. Затем проверить остальные страницы и заголовки RU/EN. [Релиз подтверждён GitHub](verification/evidence/2026-10-17-v0.5.3-release-publication.md), но без owner-live наблюдения **GUI остаётся неподтверждённым**. Только после устранения возможного блокера идти по полному ТЗ: сохранение/Apply, один dvtws2/IPFW, reboot; UDP/STUN, MEDIA/CALL отдельно.

До фактического открытия установленной страницы результат называется «исправление подготовлено; работа установленной страницы не подтверждена». Затем выполняется полное исходное ТЗ: пять профилей, сохранение/Apply, общая служба/IPFW/boot; STUN/MEDIA/CALL принимаются отдельно. Найденный блокер не обходится новым этапом или перепроектированием общего backend.

## Минимальное чтение

[План v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Приёмка](VOICE_CODE_COMPLETION_GATE.md) · [Полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md). Действуют `DEV-007`, `DEV-011`, `DEV-018` и `CHAT-003`; текущие факты — в [PROJECT_STATE](PROJECT_STATE.md), хронология — в [ledger](history/current/v0.5.x.md).
