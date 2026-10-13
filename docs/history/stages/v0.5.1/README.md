# Архив этапа разработки v0.5.1

**Закрыт как прежнее направление 13.10.2026 при открытии `v0.5.2_1`.** Это архив этапа, а не закрытие линии `v0.5.x` и не выпуск релиза. Последний пакетный кандидат этапа — `v0.5.1_174`; конечная документационная база — commit `11a8fdc12b602c4b4174b03b504a66f9b0af04c8`, Draft PR #328.

## Результат и причина перехода

Форма пяти Voice-сервисов, постоянная модель, validators/compiler/capture plan и private Apply/rollback материал существуют. Полный публичный Apply, normal boot, ограниченная миграция и фактические статусы ещё не завершены. Большое количество private этапов и повторённых ревизионных отчётов не означает готовность страницы.

13.10.2026 владелец утвердил общий backend со «Стратегиями»: одна модель, полный генератор, сериализованные Apply/lifecycle и один процесс. Затем подготовлен подробный семиэтапный проект плана. Владелец поручил открыть `v0.5.2_1` без релиза и убрать неактуальную историю из обязательного чтения.

Старые «следующий actuator/WAL/receipt», private этап 3 и промежуточные запреты/предложения в снимках ниже являются историей. Они не заменяют текущие требования и очередь. Полезные гарантии отказа, concurrency и ownership остаются материалом для общего пути.

## Полные снимки

| Исходный документ | Полный исторический снимок |
|---|---|
| `docs/START_HERE.md` | [START_HERE.md](START_HERE.md) |
| `docs/PROJECT_STATE.md` | [PROJECT_STATE.md](PROJECT_STATE.md) |
| `docs/ROADMAP.md` | [ROADMAP.md](ROADMAP.md) |
| `docs/INDEX.md` | [INDEX.md](INDEX.md) |
| `docs/architecture/VOICE_TRANSMISSION_GUI.md` | [VOICE_TRANSMISSION_GUI.md](VOICE_TRANSMISSION_GUI.md) |
| `docs/architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md` | [COMPLETION_PLAN.md](COMPLETION_PLAN.md) |
| `docs/history/current/v0.5.x.md` | [WORKING_LEDGER.md](WORKING_LEDGER.md) |
| `docs/releases/v0.5.1.md` | [RELEASE_NOTES.md](RELEASE_NOTES.md) |

Снимки сохраняют весь прежний текст; только относительные ссылки преобразованы в ссылки на неизменяемую исходную версию. Код и оригинальные commits также доступны в Git. Сведения в снимках читаются при необходимости конкретного исторического факта, не автоматически перед каждым действием.

## Текущая работа

[START_HERE](../../../START_HERE.md) · [PROJECT_STATE](../../../PROJECT_STATE.md) · [план v0.5.2](../../../architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [неизменное ТЗ](../../../architecture/VOICE_TRANSMISSION_GUI.md).
