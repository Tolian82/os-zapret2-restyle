# G11 — обновление действующего плагина, проверка, purge и чистая установка

**Приоритет владельца, 10.11.2026:** не удалять предыдущую инсталляцию, пока
не проверено обычное обновление. Испытания выполняются именно в следующем
порядке: (1) `v0.6.3_1 → v0.6.3_29`, (2) проверка работающего плагина,
(3) полный purge утверждённым G01 скриптом, (4) чистая установка `_29`,
(5) приёмка clean-install по ТЗ A01–A22.

## Публикационные исходные данные

- Stable predecessor: [v0.6.3](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.3), пакет `os-zapret2-restyle-0.6.3_1.pkg`, SHA-256 `eecae7fd21665dd74311323e9359467065663ba6a5662bd0d1c31d847296d0be`.
- Testing successor: [v0.6.3_29](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.3_29), source `0ba0c5fcf041201465c647b94597e51c2a1ac40a`, пакет SHA-256 `c5ceab0088d22205f46b2260e25e1d93c1500a59d8a19afa7b63b4d8f7f6e852`, pinned installer SHA-256 `0106dd9ce92203dced4aa82220ac393a38c6f5ff287480a332c51632641619e2`.
- `v0.6.3_30` — после публикации только docs/source, **не** опубликованный пакет.

## Почему нужен дополнительный native gate

[Предыдущий G10 S3](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42716247017)
использовал исторический RUNNING predecessor `v0.6.2_1`, а не
публичный `v0.6.3_1`; полная 5-шаговая последовательность владельца на
точных опубликованных байтах в одном native guest тогда не выполнялась.

Для этого введён скрипт `scripts/stage11-published-upgrade-purge-clean.py` и
один нативный workflow `g11-published-upgrade-purge-clean.yml`. На
**изолированной** OPNsense 26.7 он сверяет опубликованные архивы и
SHA, ставит реальный stable `_1` с оригинальными pkg hooks, сохраняет
пользовательскую конфигурацию штатным Config API, создаёт временный
**локальный file:// FreeBSD pkg каталог**, делает настоящий
`pkg upgrade -r G11PublishedAcceptance os-zapret2-restyle` на физических
байтах `_29`, проверяет Config/регистрацию/FD9/IPFW, устанавливает
реальный upstream `v1.0.7` и запускает только loopback `lo0:65431`.
После этого запускает G01 `--dry-run` и полный `--purge --yes-disposable`
с проверкой приватного Config backup и отсутствия остатка, затем штатный
`pkg install -r G11PublishedAcceptance os-zapret2-restyle` того же `_29`
и проверяет defaults, отсутствие сохранённого старого Config и автозапуска.

**Граница доказательства:** это реальный каталог и штатный
`pkg upgrade`, но локальный CI file:// **не** подтверждает пункт
обновления в реальном GUI System → Firmware. Для такого способа нужен
опубликованный и явно подключённый отдельный тестовый каталог, а не
изменение стабильного Pages/pkg. До точного PASS нативной проверки не
заявлять готовность пользователя. Owner-live browser/DPI/IPv6/Voice
media ещё NOT TESTED.

## Последовательность для владельца (после положительного native gate)

**0. Подготовка:** внешний backup Config и окна обслуживания; сохранить
до обновления версию, состояние службы и заполненные поля. Не публиковать
`/conf/config.xml` и другие частные данные.

**1. Обновление без предварительного удаления:** опубликованный
SHA-pinned installer использует обычные штатные pkg hooks и
`pkg add -f` с проверкой точного SHA, но **не** GUI Firmware update.

```sh
fetch -o /tmp/install-os-zapret2-restyle-0.6.3_29.sh https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_29/install-os-zapret2-restyle-0.6.3_29.sh
sha256 -q /tmp/install-os-zapret2-restyle-0.6.3_29.sh
# Должно быть: 0106dd9ce92203dced4aa82220ac393a38c6f5ff287480a332c51632641619e2
sh /tmp/install-os-zapret2-restyle-0.6.3_29.sh
pkg info -x os-zapret2-restyle
```

**2. Проверка обновлённой инсталляции:** страница и меню, сохранность
пользовательских Traffic Strategy, YouTube Domains, WAN, Voice и Extra,
статус/Start/Stop/Apply, обе Lab, восстановление и reboot. При проблеме
**не переходить к purge**: сохранить диагностику и исследовать дефект.

**3. Полный G01 purge:** только после завершения пункта 2, отдельного
явного согласия на потерю всех данных Zapret2 и проверки backup.
Использовать immutable ref к `scripts/purge-os-zapret2-restyle.sh`;
сначала `--dry-run`, затем `--purge` с интерактивной фразой
`PURGE OS-ZAPRET2-RESTYLE`. Никакого `--yes-disposable` на устройстве.
G01 скрипт сам создаёт приватный backup под
`/root/zapret2-restyle-purge-backups/`. По умолчанию удаляет
проектный repo config, upstream и Extra Lua/BIN, настройки, состояние.
Не удаляет чужие OPNsense настройки или зависимости.

**4. Чистая установка:** повторить **тот же** SHA-pinned installer `_29`
из пункта 1. Он не требует оставленного проектного pkg-репозитория:
достаёт опубликованный архив и использует официальный OPNsense repo
только для необходимых зависимостей.

**5. First-install приёмка:** ровно десять YouTube доменов, начальная
TCP+QUIC стратегия и единственный `--new`, пустой WAN, Enabled=off,
GUI upstream `v1.0.7` Install, WAN-only Save, пустая strategy/Voice-only,
Standard/Extended Lab до первого обычного Start, Stage-60, GUI кнопки,
RU/EN/F5, reboot, штатный GUI uninstall/reinstall и остальные A01–A22.
Не считать успешный loopback сетевой проверкой ISP DPI/IPv6/media.

**Не подменять** тест реального Firmware GUI локальным pkg add или
внутренним CI-каталогом; стабильный Web/pkg репозиторий не изменять.
Полный purge рабочего шлюза разрушителен и не запускается нами.

## First exact-head native attempt (diagnostic, not accepted)

[Native #42744121612](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42744121612) on PR #1006 downloaded both release assets with correct SHA, installed real `_1`, executed genuine **repository-driven** `pkg upgrade` to `_29`, and reported `PASS_G11_PUBLISHED_STOCK_PKG_UPGRADE_WITH_USER_CONFIG=1` (exact old user/foreign Config preserved). The run then **FAILED** while preparing upstream `v1.0.7`: stock setup exited 69 before service Start, purge, or clean reinstall. The initial harness redacted the actual error class, so its root cause is **not yet established**. A source-policy CI refusal also required classifying this script as a *Stage 11 test fixture* rather than production. Follow-up now emits only a fixed sanitized setup-error class and retains all fail-closed conditions. Neither G11 full-chain nor owner GUI is accepted based on this first attempt.

[Native rerun #42744914816](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42744914816) again proved exact `_1` → `_29` `pkg upgrade` and Config preservation, but `setup.sh install v1.0.7` again exited 69 before purge. The first classification matched no registered error pattern: **do not guess upstream networking or runtime root cause**. Next diagnostic logs only bounded `ERROR:` lines from synthetic disposable-guest setup output. Source CI and compatibility policy on head `5bdaa987` PASS; native still FAIL.

[Third native run #42745411439](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42745411439) also **PASS** exact published `_1 → _29` stock `pkg upgrade` + user/foreign Config preservation, then refused at upstream setup before purge. Root cause **identified** using redacted diagnostic: `ERROR: incomplete or foreign upstream path: /usr/local/etc/zapret2; inspect before retry`. The previous fixture had called **low-level** `setup.sh install v1.0.7`, which correctly rejects the template-only `/usr/local/etc/zapret2` created by stock package hooks. This is a **test-fixture invocation defect**, not proof of a product failure. The corrected fixture must invoke the exact GUI-supported original FD9-protected `setup_transaction.sh install v1.0.7`, which explicitly stages a true first install while preserving native template-only entries. Do not delete the template directory, weaken its owner guard or claim the complete 5-step run PASS before new native evidence.

[Fourth native run #42745920924](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42745920924) used the **correct** stock `setup_transaction.sh install v1.0.7`: published `_1→_29` `pkg upgrade` and exact Config preservation PASS again, then original `zapret_service.sh start` refused rc=1 after upstream setup. The fixture had preserved its test `general/enabled=0` across upgrade (correct behavior) but never explicitly Enabled it before intentionally starting its test loopback service. The follow-up now enables **only the disposable CI `lo0:65431` profile** through locked native `Config::save()` *after* upgrade preservation proof; then requires real Start/PID/owned IPFW, diagnoses fixed sanitized native errors and still refuses on any nonzero status. Full G01 purge and clean install remain pending until this exact-head native path passes.
