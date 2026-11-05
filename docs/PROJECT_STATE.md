# os-zapret2-restyle — текущее состояние v0.6.x

Текущий этап — **`v0.6.2_137`**; `VERSION=0.6.2`, `PLUGIN_REVISION=137`, package candidate: `os-zapret2-restyle-0.6.2_137.pkg` (**SOURCE-ONLY; NOT BUILT / NOT PUBLISHED**).

State-line scope: **`v0.6.x`**. Current-work flow: `START_HERE -> PROJECT_STATE -> version-line archive` (owner-facing archive pointers follow).

Previously completed version lines: [v0.1.x archive](history/archive/v0.1.x.md), [v0.2.x archive](history/archive/v0.2.x.md), [v0.3.x archive](history/archive/v0.3.x.md), [v0.4.x archive](history/archive/v0.4.x.md). Historical detail for the current line: [v0.6.x ledger](history/current/v0.6.x.md).

## Текущий приоритет и границы работ (5 ноября 2026)

Владелец утвердил возврат к обычному нативному плагину OPNsense: [ТЗ v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) и [план v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md). Отменены внешние SQLite-свидетели, RSA-подписи разрешений, криптографические одноразовые операции, собственные управляющие шлюзы перед `pkg`, предупреждения для root и предположение о гарантированном veto в `+PRE_INSTALL`. Исторический реальный опыт `_74` показал, что отказ хука может не остановить `pkg add -f`, но **не** создаёт требования внешней инфраструктуры доверия.

В исходной ревизии `_137` удалены неиспользуемые экспериментальные `native_pkg_*.py`, `stage3-prepkg-*`, связанные Stage 3 тесты и approval-only CI. В проверке чистой установки Stage 2 удалена зависимость от экспериментального managed CLI; проверка реального `pkg`, hooks, установленных файлов, Status и Config сохранена. Действующая техническая документация и ссылки пересмотрены после удаления. Завершение подтверждается только проверками точного PR head; установленная нативная сборка пока не принята.

## Что фактически уже есть в source

- `Makefile` содержит `PLUGIN_NAME=zapret2-restyle`, реальные `PLUGIN_DEPENDS` и официальный `Mk/plugins.mk`.
- `scripts/build-pkg.sh` уже является 19-строчной обёрткой над `scripts/native-opnsense-package.py`; эта нативная сборка проверялась в CI OPNsense. Создавать другой пакетный движок не требуется.
- Существуют `compatibility.json`, целевые ABI/provider проверки, работающие компоненты `zapret`, Config/Apply, Strategies, Voice, Exclude, Lab, Extra Resources.
- Долг работы: довести native package до полноценной установки и квалификации; перенести реальные shell/PHP/configd/hooks Python-вызовы с фиксированной `python3.13` на единый поддерживаемый контракт.
- `src/opnsense/scripts/OPNsense/Zapret/setup.sh` ещё временно включает общий FreeBSD repo и устанавливает системные зависимости; это надо убрать в пользу штатного OPNsense `pkg`.
- Четыре существующих `pkg/+...` hooks требуют обычной проверенной установки, RUNNING/STOPPED обновления, переустановки и удаления. Никакого менеджера авторизации pkg не создаём.
- Экспериментальные pkg-approval backend/CLI/tests/CI удалены из `_137` source-кандидата; действующий `main` получает изменение только после exact-head CI и merge. Исторические записи не служат runtime-зависимостями.

## IPFW/PF — окончательные решения

| Назначение | IPFW **номера правил**, не порты |
|---|---|
| Обычный Zapret2 / Strategies | `19000–19010` |
| Strategy Lab | `19100–19131` |

Не разрабатывать новые проверки чужих правил, распределитель номеров, журнал владения, отслеживание `ipfw flush`, автоматическое восстановление или переписывание IPFW. Существующую безопасную холодную загрузку IPFW сохраняем. `pfctl -d; pfctl -e` оставляем без изменения: OPNsense-only `sync_fw_hooks.py` и `pfilctl` в этом плане исключены. Портирование на pfSense — будущая отдельная задача, её не затрудняем ненужной OPNsense-специфичной архитектурой.

## Выпуск, границы доказательств и приёмка

**Опубликовано:** полноценный стабильный [v0.6.2](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.2), неизменный пакет `0.6.2_1.pkg`. `_137` — только новая исходная ревизия с удалением отменённой инфраструктуры, на устройстве владельца ничего не менялось.

**Подтверждено:** ранее принятые функции текущего выпуска имеют свои независимые CI/installed доказательства, не переписываются и не проходят заново отменённые лабораторные кампании. IPv6 на IPv4-only owner stand был явно waived; непроверенные WAN/Voice media не называем PASS.

**Нужно до готовности:** закончить уже существующий Mk-билдер, штатные зависимости и Python, сервис/configd/hooks, выполнить ограниченную финальную нативную приёмку **одного** конечного пакета и зафиксировать точный SHA-256. Отдельное разрешение обязательно для публикации или изменений на устройстве владельца.

**Навигация:** [START_HERE](START_HERE.md) · [ROADMAP](ROADMAP.md) · [ТЗ](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) · [план](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) · [исторический ledger](history/current/v0.6.x.md) · [релиз](releases/v0.6.2.md).
