# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.3_4`. `VERSION=0.5.3`, `PLUGIN_REVISION=4`. Владелец 17.10.2026 открыл исправляющий этап и поручил сначала записать подход/план, затем выполнить его. Переход `_1`, исправление `_2` и точная подготовка релиза интегрированы в `main`; полный [релиз `v0.5.3`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) и FreeBSD pkg-репозиторий опубликованы. Приёмка установленной страницы и голосового канала отдельно открыта.

## Наблюдение установленного 0.5.3_2

Владелец 17.10.2026 подтвердил установку пакета `0.5.3_2` на FreeBSD:15:amd64 и открытие Voice через GUI. Это закрывает прежний дефект 404 из `0.5.2_194`, но выявляет новые блокеры: RU-страница выводит английскую native help, выбор WAN выдаёт `Shared model candidate is not normalized`, backend-error остаётся по-английски; на Voice показан избыточный селектор upstream releases. Статус общего сервиса на снимке «Неизвестно» при upstream version v1.0.5.2; рабочее состояние двигателя не подтверждено.

В `_3` исправлены native help target, обработка выпадающих полей реальной OPNsense-модели в detached XML кандидате, перевод ошибок и убрано управление upstream releases с Voice (общий Start/Stop/status сохранён). Исправление `_3` в `main` из [PR #335](https://github.com/Tolian82/os-zapret2-restyle/pull/335), [CI #39031185860](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39031185860) подтвердил Voice/Project/FreeBSD15 pkg. **Проверочный [pkg v0.5.3_3](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.3_3/os-zapret2-restyle-0.5.3_3.pkg) опубликован и подтверждён [workflow #39032016190](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39032016190). Стабильный релиз/Pages/pkg-репозиторий содержит _2; результаты установленного `_3` описаны ниже.**

## Наблюдение установленного 0.5.3_3

Владелец 17.10.2026 подтвердил установку проверочного `0.5.3_3` с точным SHA-256 `f3fc9e09d5713587c8381d5d44e86192e6908c3c623d434ebb80e618bd7db40d`. Снимок GUI подтверждает русские native help, отсутствие селектора релизов и работу выбора WAN/кнопки «Проверить» без прежней нормализационной ошибки. Однако общий статус UI ошибочно показывает «Неизвестно»: `configctl zapret setup_status` сообщил `installed=1; service=started; version=v1.0.5.2; setup=ready; busy=0`. Независимый `voice_inspect` сообщил `state=uninitialized; remedy=common-apply-required`, то есть Voice runtime/IPFW пока не активирован. Отдельный read-only `configctl zapret voice_lifecycle_inspect` вернул `Execute error`. Последующий штатно заблокированный read-only вызов показал `VoiceLifecycleRouteError: unsafe or replaced native Config inode`: OPNsense 26.7 использует `wwwonly:wheel` для `/conf/config.xml`, а скрипт ожидал `root:wheel`. Это ошибка проверки владельца в плагине, не доказательство повреждения Config.

Кандидат `_4` исправляет правдивое отображение общего Zapret2/неподтверждённого Voice и дефект точного владельца Config в read-only lifecycle inspector и соседнем saved-draft preview. Сохраняются точные inode/device/nlink, root-сервисная FD9-блокировка, строгий именованный владелец `wwwonly:wheel` и Config flock, без разблокирования Start/Stop или Apply. CI и installed `_4` ещё не подтверждены.

## Точное следующее действие

Проверить исправленную `_4` по CI, затем опубликовать проверочный пакет и отдельно подтвердить на OPNsense GUI статус общей службы, а также успешность `configctl zapret voice_lifecycle_inspect` и read-only preview. **Дополнительных команд владельцу до доставки _4 не требуется.** Применение/boot/STUN/MEDIA/CALL остаются следующими этапами только после этого рубежа. [Приёмка](VOICE_CODE_COMPLETION_GATE.md).

## Минимальное чтение

[План v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Приёмка](VOICE_CODE_COMPLETION_GATE.md) · [Полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md). Действуют `DEV-007`, `DEV-011`, `DEV-018` и `CHAT-003`; текущие факты — в [PROJECT_STATE](PROJECT_STATE.md), хронология — в [ledger](history/current/v0.5.x.md).
