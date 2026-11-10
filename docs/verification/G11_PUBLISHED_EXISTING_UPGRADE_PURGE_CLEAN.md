# G11 — обновление действующего плагина, проверка, purge и чистая установка

**Утверждённый приоритет владельца, 10.11.2026:** сначала локальное обновление существующей установки, затем полная проверка, обычное удаление из GUI, локальная переустановка с сохранением параметров, повторная полная проверка, запакованный локальный purge, чистая локальная установка и её полная приёмка — **девять шагов** по [ТЗ v1.3 §8.1](../architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md). Прежняя пятишаговая G11 последовательность заменена. Для установки применять только прямой GitHub `.pkg` через `fetch → pkg add -f → pkg info`, без внешних SH-установщиков; недостающие manifest dependencies предварительно разрешаются только штатным `pkg install -r OPNsense`.

## Публикационные исходные данные

- Stable predecessor: [v0.6.3](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.3), пакет `os-zapret2-restyle-0.6.3_1.pkg`, SHA-256 `eecae7fd21665dd74311323e9359467065663ba6a5662bd0d1c31d847296d0be`.
- **Current published testing successor**: [v0.6.3_33](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.3_33), source `48564cde7910f0c3bb463aed9db65d2d6fbaf42f`, exact package SHA-256 `59f38d12bcd09496f8178af597a383062f7045c3e63f8120b964076fdae01b64`, historical companion SHA-256 `b7cef59e26e73c361f719d098e2a33f177de0bc506a113d9606f8237721f09ba` (immutable historical asset, not current installation method). **This physical testing package still needs full sequential nine-stage native gate before owner G11.** Historical `_29` remains immutable but is superseded for this G10A qualification.
- `v0.6.3_34` — only docs/publication record after `_33`; **no `_34.pkg`**. Stable Pages/pkg repository stays on `_1`.

**New G10A nine-stage native smoke (source-only _35, test-only):** `scripts/stage11-published-nine-step-native.py` and `.github/workflows/g11-published-nine-step-native.yml` exercise exact **published** `_1` and `_33` archive SHA and the original companion asset (historical test evidence only); new installations use direct `.pkg`/`pkg add -f` and no file:// pkg repo. It tests stock server-side Firmware removal/menu cache, user Config/runtime preservation, the installed self-deleting purge and initial clean defaults. This **does not** on its own prove full two-pass functional regression, RUNNING original stable _1 upgrade, physical GUI clicks, or A01–A22. These remain explicit negative receipt fields until actually tested. Do not invite owner before full G10A gate.

**Nine-stage smoke result:** [#42777032678](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42777032678) **PASS** for published `_1` STOPPED predecessor → published `_33` and all nine ordered native smoke phases, with menu invalidation, Config retention, package local purge self-delete and clean defaults. The receipt explicitly refuses to claim complete A01–A22, two comprehensive regressions or old `_1` RUNNING upgrade. A separate source-only `_36` native witness tests the last item under unchanged physical `_33` assets; none of this instructs the owner to install before full G10A.

## Почему нужен дополнительный native gate

[Предыдущий G10 S3](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42716247017)
использовал исторический RUNNING predecessor `v0.6.2_1`, а не
публичный `v0.6.3_1`; полная прежняя пятишаговая последовательность владельца на
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

## Последовательность для владельца (новая приёмка ещё не начата)

**Предварительное условие:** G10A завершён: опубликована версия с безопасным локальным purge-скриптом, проверена её установка/обновление на изолированной OPNsense, устранены регрессии. Исторический `v0.6.3_29` и [native #42746292077](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42746292077) подтверждают лишь часть прежнего, пятишагового варианта; они не завершают G10A.

**Обязательная установка по `CHAT-027` — только `.pkg`.** Для уже опубликованного `v0.6.3_33`:

```sh
fetch -o /root/os-zapret2-restyle-0.6.3_33.pkg https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_33/os-zapret2-restyle-0.6.3_33.pkg
pkg add -f /root/os-zapret2-restyle-0.6.3_33.pkg
pkg info -x os-zapret2-restyle
```

`pkg add -f` не скачивает недостающие зависимости: предварительно разрешать только фактически отсутствующие из `+MANIFEST` через официальный интерактивный `pkg install -r OPNsense`. Никаких внешних SH-установщиков и никаких отдельных тестовых pkg-репозиториев. Этот пример сам по себе не подтверждает прохождение полной приёмки G10A.

1. **Обновить действующую установку без предварительного удаления:** тем же опубликованным локальным пакетом через штатный `pkg add -f` из `CHAT-027`, с реальными `pkg` hooks; запомнить предыдущее состояние и проверить сохранность конфигурации.
2. **Полностью проверить функции после обновления:** GUI и все настройки, WAN-first, Strategies, Exclude/Targets, Voice, Extra Lua/BIN, Start/Stop/Restart/Apply, Standard/Extended Lab и восстановление, статусы RU/EN, перезагрузку. При дефекте остановиться до удаления.
3. **Штатно удалить плагин в GUI** (без purge), убедившись в исчезновении пунктов меню/службы/собственных IPFW при сохранённых Config/upstream/resources.
4. **Переустановить опубликованный локальный пакет**, снова через тот же `fetch → pkg add -f → pkg info` без нового pkg-репозитория и без самостоятельной проверки SHA.
5. **Подтвердить сохранение ВСЕХ пользовательских параметров:** включая сознательно пустые поля, WAN, стратегии, Exclude, Voice, пользовательские Lua/BIN; не записывать начальные шаблоны в существующую конфигурацию.
6. **Повторить всю функциональную проверку из шага 2** после обычного удаления и переустановки.
7. **Выполнить полный purge установленным вместе с пакетом локальным скриптом:** сначала `--dry-run`, затем отдельный `--purge` с действующим подтверждением/приватным backup. Скрипт выполняет штатное удаление плагина и проверенную очистку Zapret-only данных, включая **самого себя** (поддержать безопасное продолжение работы после удаления файла из pkg). Проверить отсутствие остаточного меню, файлов, Config-поддерева, runtime, принадлежащих процессов/IPFW и сохранность чужих настроек.
8. **Снова установить тот же опубликованный локальный пакет** штатной установкой `.pkg` `fetch → pkg add -f → pkg info`; без скрипта чистой установки, ручного SHA или дополнительного репозитория. В `config.xml` на этот раз нет прежних параметров плагина.
9. **Выполнить полную приёмку чистой установки** по A01–A22: точные первоначальные YouTube Domains/Traffic Strategy, первый upstream setup через GUI, WAN-only Save, пустая стратегия и Voice-only, Lab до первого старта, реальные Start/Apply/Stop, RU/EN, Stage 60, reboot/recovery и отсутствие регрессий.

**Сценарий остановки:** при регрессе на шагах 1–6 не выполнять разрушительный шаг 7. Перед полным purge требуется отдельное подтверждение, приватный backup и проверка сторонних Config/процессов/IPFW. Не выполнять `--yes-disposable` на пользовательском шлюзе. Фактическое физическое прохождение/браузер/сетевые DPI/IPv6/Voice-media тесты остаются отдельными доказательствами, а не следствием успеха CI.

## First exact-head native attempt (diagnostic, not accepted)

[Native #42744121612](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42744121612) on PR #1006 downloaded both release assets with correct SHA, installed real `_1`, executed genuine **repository-driven** `pkg upgrade` to `_29`, and reported `PASS_G11_PUBLISHED_STOCK_PKG_UPGRADE_WITH_USER_CONFIG=1` (exact old user/foreign Config preserved). The run then **FAILED** while preparing upstream `v1.0.7`: stock setup exited 69 before service Start, purge, or clean reinstall. The initial harness redacted the actual error class, so its root cause is **not yet established**. A source-policy CI refusal also required classifying this script as a *Stage 11 test fixture* rather than production. Follow-up now emits only a fixed sanitized setup-error class and retains all fail-closed conditions. Neither G11 full-chain nor owner GUI is accepted based on this first attempt.

[Native rerun #42744914816](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42744914816) again proved exact `_1` → `_29` `pkg upgrade` and Config preservation, but `setup.sh install v1.0.7` again exited 69 before purge. The first classification matched no registered error pattern: **do not guess upstream networking or runtime root cause**. Next diagnostic logs only bounded `ERROR:` lines from synthetic disposable-guest setup output. Source CI and compatibility policy on head `5bdaa987` PASS; native still FAIL.

[Third native run #42745411439](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42745411439) also **PASS** exact published `_1 → _29` stock `pkg upgrade` + user/foreign Config preservation, then refused at upstream setup before purge. Root cause **identified** using redacted diagnostic: `ERROR: incomplete or foreign upstream path: /usr/local/etc/zapret2; inspect before retry`. The previous fixture had called **low-level** `setup.sh install v1.0.7`, which correctly rejects the template-only `/usr/local/etc/zapret2` created by stock package hooks. This is a **test-fixture invocation defect**, not proof of a product failure. The corrected fixture must invoke the exact GUI-supported original FD9-protected `setup_transaction.sh install v1.0.7`, which explicitly stages a true first install while preserving native template-only entries. Do not delete the template directory, weaken its owner guard or claim the complete 5-step run PASS before new native evidence.

[Fourth native run #42745920924](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42745920924) used the **correct** stock `setup_transaction.sh install v1.0.7`: published `_1→_29` `pkg upgrade` and exact Config preservation PASS again, then original `zapret_service.sh start` refused rc=1 after upstream setup. The fixture had preserved its test `general/enabled=0` across upgrade (correct behavior) but never explicitly Enabled it before intentionally starting its test loopback service. The follow-up now enables **only the disposable CI `lo0:65431` profile** through locked native `Config::save()` *after* upgrade preservation proof; then requires real Start/PID/owned IPFW, diagnoses fixed sanitized native errors and still refuses on any nonzero status. Full G01 purge and clean install remain pending until this exact-head native path passes.

## Итог нативной приёмки двух опубликованных пакетов (10 ноября 2026)

[G11 native exact published-archive run #42746292077](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42746292077) — **SUCCESS**, exact head `d566d11c3e34ae8efcc39d9c561cfd74545da4d6`, published stable `_1` SHA-256 `eecae7fd21665dd74311323e9359467065663ba6a5662bd0d1c31d847296d0be`, published testing `_29` SHA-256 `c5ceab0088d22205f46b2260e25e1d93c1500a59d8a19afa7b63b4d8f7f6e852`. All subsequent tests used **these exact existing asset bytes**, not a freshly built `v0.6.3_31.pkg`.

- Genuine stock `pkg upgrade -r G11PublishedAcceptance` from installed published stable `_1` to testing `_29` PASS, user/foreign Config preserved. The stable predecessor was STOPPED at upgrade; earlier G10 tested RUNNING but from the historical `_0.6.2_1` predecessor, not a confirmed RUNNING `_1`.
- Native `setup_transaction.sh install v1.0.7` PASS: proper original FD9-locked first-runtime path that preserves template-only upstream root. Enabled changed from `0` to `1` **only after exact upgrade preservation** on disposable lo0:65431; real dvtws2 PID and scoped IPFW verified.
- G01 real `--dry-run` and full `--purge --yes-disposable` PASS under CI opt-ins, private config backup hash and permission checked, no stale saved Zapret/engine/PID/IPFW, foreign Config/repo preserved.
- Genuine stock `pkg install -r G11PublishedAcceptance` of SAME published `_29` from local disposable catalog PASS: exactly ten default domains, TCP/QUIC with one `--new`, previous user sentinel removed, WAN unset, Enabled off and no unexpected IPFW intercepts.
- **NOT TESTED:** owner Firmware GUI click/update source, user WAN traffic, DPI evasion, IPv6, Voice media, production purge and owner-specific settings. Native `file://` catalog was isolated to CI and never deployed to stable Pages/pkg.
