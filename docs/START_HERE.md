# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.3_3`. `VERSION=0.5.3`, `PLUGIN_REVISION=3`. Владелец 17.10.2026 открыл исправляющий этап и поручил сначала записать подход/план, затем выполнить его. Переход `_1`, исправление `_2` и точная подготовка релиза интегрированы в `main`; полный [релиз `v0.5.3`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) и FreeBSD pkg-репозиторий опубликованы. Приёмка установленной страницы и голосового канала отдельно открыта.

## Наблюдение установленного 0.5.3_2

Владелец 17.10.2026 подтвердил установку пакета `0.5.3_2` на FreeBSD:15:amd64 и открытие Voice через GUI. Это закрывает прежний дефект 404 из `0.5.2_194`, но выявляет новые блокеры: RU-страница выводит английскую native help, выбор WAN выдаёт `Shared model candidate is not normalized`, backend-error остаётся по-английски; на Voice показан избыточный селектор upstream releases. Статус общего сервиса на снимке «Неизвестно» при upstream version v1.0.5.2; рабочее состояние двигателя не подтверждено.

В `_3` исправлены native help target, обработка выпадающих полей реальной OPNsense-модели в detached XML кандидате, перевод ошибок и убрано управление upstream releases с Voice (общий Start/Stop/status сохранён). Исправление `_3` в `main` из [PR #335](https://github.com/Tolian82/os-zapret2-restyle/pull/335), [CI #39031185860](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39031185860) подтвердил Voice/Project/FreeBSD15 pkg. **Проверочный [pkg v0.5.3_3](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_3/os-zapret2-restyle-0.5.3_3.pkg) опубликован и подтверждён [workflow #39032016190](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39032016190). Стабильный релиз/Pages/pkg-репозиторий содержит _2, живая приёмка _3 не выполнялась.**

## Точное следующее действие

**Установить и принять проверочный пакет `_3` на OPNsense (GitHub testing prerelease, не обновление стабильного Firmware-репозитория).** Сначала зафиксировать текущие pkg/runtime, затем установить скачанный пакет и проверить: native справку RU/EN (иконка и «вся справка»), WAN без внутреннего исключения, корректную валидацию, отсутствие release selector на Voice, сохранённый общий статус/Start/Stop. Только после этих результатов переходить к Save/Apply/boot/STUN/MEDIA/CALL согласно [приёмке](VOICE_CODE_COMPLETION_GATE.md).

## Минимальное чтение

[План v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Приёмка](VOICE_CODE_COMPLETION_GATE.md) · [Полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md). Действуют `DEV-007`, `DEV-011`, `DEV-018` и `CHAT-003`; текущие факты — в [PROJECT_STATE](PROJECT_STATE.md), хронология — в [ledger](history/current/v0.5.x.md).
