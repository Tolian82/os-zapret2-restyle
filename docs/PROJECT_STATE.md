# os-zapret2-restyle — текущее состояние v0.6.x

Текущий этап — **`v0.6.2_140`**; `VERSION=0.6.2`, `PLUGIN_REVISION=140`, package candidate: `os-zapret2-restyle-0.6.2_140.pkg` (**SOURCE-ONLY; NOT PUBLISHED/OWNER-INSTALLED**).

State-line scope: **`v0.6.x`**. Current-work flow: `START_HERE -> PROJECT_STATE -> version-line archive` (owner-facing archive pointers follow).

Previously completed version lines: [v0.1.x archive](history/archive/v0.1.x.md), [v0.2.x archive](history/archive/v0.2.x.md), [v0.3.x archive](history/archive/v0.3.x.md), [v0.4.x archive](history/archive/v0.4.x.md). Historical detail for the current line: [v0.6.x ledger](history/current/v0.6.x.md).

## Текущий приоритет и границы работ (5 ноября 2026)

Владелец утвердил возврат к обычному нативному плагину OPNsense: [ТЗ v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) и [план v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md). Отменены внешние SQLite-свидетели, RSA-подписи разрешений, криптографические одноразовые операции, собственные управляющие шлюзы перед `pkg`, предупреждения для root и предположение о гарантированном veto в `+PRE_INSTALL`. Исторический реальный опыт `_74` показал, что отказ хука может не остановить `pkg add -f`, но **не** создаёт требования внешней инфраструктуры доверия.

Ревизия `_137` через [PR #907](https://github.com/Tolian82/os-zapret2-restyle/pull/907) **слита в main** после 15/15 успешных exact-head workflows и postmerge main CI. На одноразовой OPNsense 26.7 подтверждены **реальная сборка и чистая установка** штатного `Mk/plugins.mk`-пакета с проверкой hooks/файлов/Config; это не окончательная приёмка пакета и не установка у владельца. `_138` принят в [PR #908](https://github.com/Tolian82/os-zapret2-restyle/pull/908): 15/15 exact-head CI PASS, настоящая сборка/установка OPNsense 26.7, postmerge main CI PASS. `_139` принят: [PR #909](https://github.com/Tolian82/os-zapret2-restyle/pull/909) 15/15 exact-head PASS, real native build/install и main CI PASS. `_140` — отдельный исходный кандидат Python-down native Stop/Status для ordinary Strategies под FD9, не для активного shared Voice/Strategies владельца.

## Что фактически уже есть в source

- `Makefile` содержит `PLUGIN_NAME=zapret2-restyle`, реальные `PLUGIN_DEPENDS` и официальный `Mk/plugins.mk`.
- `scripts/build-pkg.sh` уже является 19-строчной обёрткой над `scripts/native-opnsense-package.py`; эта нативная сборка проверялась в CI OPNsense. Создавать другой пакетный движок не требуется.
- Существуют `compatibility.json`, целевые ABI/provider проверки, работающие компоненты `zapret`, Config/Apply, Strategies, Voice, Exclude, Lab, Extra Resources.
- Реальная нативная установка `.pkg` уже подтверждена на одноразовой OPNsense 26.7 для `_137`, но финальный package SHA и полная установленная приёмка ещё впереди. `_139` перенёс рабочие вызовы на единый validated Python launcher; `_140` ограниченно добавляет verified shell Stop при недоступном Python без общего журнала и тест холодной установленной системы. Активный shared-owner teardown остаётся открытым.
- В слитом `_138` `setup.sh` не включает FreeBSD-репозиторий, не обновляет и не ставит системные пакеты; проверяет обязательные зависимости `PLUGIN_DEPENDS` и отказывает на неоднозначном legacy FreeBSD.conf без записи. В принятом `_139` введён единый исполняемый Python policy launcher (15/15 exact-head PASS, postmerge main CI PASS).
- Четыре существующих `pkg/+...` hooks требуют обычной проверенной установки, RUNNING/STOPPED обновления, переустановки и удаления. Никакого менеджера авторизации pkg не создаём.
- Экспериментальная pkg-approval инфраструктура действительно удалена из `main` в `_137`; исторические свидетельства не являются runtime-зависимостями.

## IPFW/PF — окончательные решения

| Назначение | IPFW **номера правил**, не порты |
|---|---|
| Обычный Zapret2 / Strategies | `19000–19010` |
| Strategy Lab | `19100–19131` |

Не разрабатывать новые проверки чужих правил, распределитель номеров, журнал владения, отслеживание `ipfw flush`, автоматическое восстановление или переписывание IPFW. Существующую безопасную холодную загрузку IPFW сохраняем. `pfctl -d; pfctl -e` оставляем без изменения: OPNsense-only `sync_fw_hooks.py` и `pfilctl` в этом плане исключены. Портирование на pfSense — будущая отдельная задача, её не затрудняем ненужной OPNsense-специфичной архитектурой.

## Выпуск, границы доказательств и приёмка

**Опубликовано:** полноценный стабильный [v0.6.2](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.2), неизменный пакет `0.6.2_1.pkg`. `_137` слит в исходный `main` и квалифицировал реальные CI build/install; `_138` слит в `main`; `_139` слит в main, `_140` остаётся неопубликованным кандидатом ограниченного native lifecycle. На устройстве владельца ничего не менялось.

**Подтверждено:** ранее принятые функции текущего выпуска имеют свои независимые CI/installed доказательства, не переписываются и не проходят заново отменённые лабораторные кампании. IPv6 на IPv4-only owner stand был явно waived; непроверенные WAN/Voice media не называем PASS.

**Нужно до готовности:** закрепить существующий Mk-билдер за финальным SHA, завершить штатные зависимости и Python, сервис/configd/hooks, выполнить ограниченную финальную нативную приёмку **одного** конечного пакета и зафиксировать точный SHA-256. Отдельное разрешение обязательно для публикации или изменений на устройстве владельца.

**Навигация:** [START_HERE](START_HERE.md) · [ROADMAP](ROADMAP.md) · [ТЗ](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) · [план](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) · [исторический ledger](history/current/v0.6.x.md) · [релиз](releases/v0.6.2.md).
