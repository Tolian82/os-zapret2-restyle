# os-zapret2-restyle — краткий master plan

## Текущий приоритет — закончить нативный плагин OPNsense

**Решение владельца от 5 ноября 2026:** [ТЗ v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) и [конкретный план v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) заменили чрезмерную исследовательскую цепочку Stage 3.xx. Исключены внешняя авторизация обновлений, SQLite-свидетели, криптографические grant, обязательный pre-pkg admission, специальные предупреждения root и новые механизмы управления IPFW/PF.

**Уже реализовано:** `Makefile` с официальным `Mk/plugins.mk` и `PLUGIN_DEPENDS`, 19-строчный `scripts/build-pkg.sh` с вызовом `scripts/native-opnsense-package.py`, единый compatibility manifest и часть целевых OPNsense CI. Это надо завершать, **а не начинать заново**.

**Подтверждено `_137`:** отменённая pkg-authorization архитектура удалена, [PR #907](https://github.com/Tolian82/os-zapret2-restyle/pull/907) слит после 15/15 PASS; штатный Mk-билдер создал реальный `.pkg`, чистая установка на одноразовой OPNsense 26.7 прошла. **Принята `_138`:** отказ от самостоятельной установки системных пакетов и изменения stock FreeBSD repo в `setup.sh` принят после 15/15 exact-head PASS, postmerge CI PASS ([PR #908](https://github.com/Tolian82/os-zapret2-restyle/pull/908)). **Принята `_139`:** общий Python policy launcher с 15/15 exact-head PASS и postmerge CI SUCCESS ([PR #909](https://github.com/Tolian82/os-zapret2-restyle/pull/909)). **Принята `_140`:** ordinary Strategies Stop/Status при недоступном Python под FD9 с installed cold OPNsense smoke (15/15 exact-head PASS, postmerge CI PASS, [PR #910](https://github.com/Tolian82/os-zapret2-restyle/pull/910)). **Принята `_141`:** реальное штатное удаление установленного native `.pkg` и OPNsense firmware unregister на одноразовой 26.7, с сохранением непустого Config; [PR #911](https://github.com/Tolian82/os-zapret2-restyle/pull/911) слит после успешной точной CI. **Текущая `_142`:** проверить установленный холодный Start/Restart/Reconfigure при исправном Python и отсутствующем движке, без изменения Config/IPFW. Активный shared owner, Web/boot/full service и конечный SHA остаются открытыми.

## Пять проверяемых результатов

| Очередь | Работа | Критерий |
|---|---|---|
| 1 | Очистить отменённые `native_pkg_*`, `stage3-prepkg-*`, экспериментальные тесты и approval-only workflows; проверить активную документацию | Ненужная инфраструктура отсутствует в активном коде/CI, техдокументация согласована, relevant CI зелёный |
| 2 | Закончить существующий официальный нативный билд | Реальный `.pkg` собирается через `Mk/plugins.mk` и устанавливается на одноразовой OPNsense 26.7 |
| 3 | Передать системные зависимости OPNsense `pkg`, убрать FreeBSD repo toggle из `setup.sh`, унифицировать Python | Установленный пакет обеспечивает свои зависимости и реальные GUI/configd/backend-операции |
| 4 | Довести штатный сервис, четыре hooks и обычные обновления | Start/Stop/Restart/Status, RUNNING/STOPPED update, переустановка, сохранение Config и удаление работают |
| 5 | Оставить один CI/package/release конвейер и закончить приёмку | Один конечный SHA-256, конкретные PASS/NOT TESTED, отдельное разрешение на публикацию |

**IPFW:** документируем только номера правил обычного Zapret2 `19000–19010` и Strategy Lab `19100–19131`; не разрабатываем сканеры чужих правил, автоматическое восстановление после shaper flush, распределитель номеров. **PF:** оставляем существующую `pfctl -d; pfctl -e`; `pfilctl` и OPNsense-only `sync_fw_hooks.py` не исследуем. Уже имеющаяся безопасная холодная загрузка IPFW сохраняется.

## Чего не делаем

Не создаём собственный менеджер обновлений `pkg`, внешний сервер доверия, SQLite-журнал, одноразовые разрешения, защиту от root или независимые многоступенчатые согласования. Не переписываем рабочие Strategies/Voice/Exclude/Lab/Extra Resources без конкретного дефекта. Не возобновляем закрытые исследования ТСПУ, WAN/IPv6/Voice-media. Портирование на pfSense остаётся будущим отдельным направлением.

**Актуальная точка входа:** [START_HERE](START_HERE.md) · [PROJECT_STATE](PROJECT_STATE.md) · [план по файлам](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) · [история](history/current/v0.6.x.md). Новые Stage 3.xx для гипотетических угроз не создавать.
