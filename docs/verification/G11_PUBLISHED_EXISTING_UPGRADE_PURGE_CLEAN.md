# G11 — обновление действующего плагина, проверка, purge и чистая установка

**Утверждённый приоритет владельца, 10.11.2026:** сначала локальное обновление существующей установки, затем полная проверка, обычное удаление из GUI, локальная переустановка с сохранением параметров, повторная полная проверка, запакованный локальный purge, чистая локальная установка и её полная приёмка — **девять шагов** по [ТЗ v1.3 §8.1](../architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md). Прежняя пятишаговая G11 последовательность заменена. Для установки применять только прямой GitHub `.pkg` через `fetch → pkg add -f → pkg info`, без внешних SH-установщиков; недостающие manifest dependencies предварительно разрешаются только штатным `pkg install -r OPNsense`.

## Owner acceptance for `v0.6.3_52` and v0.6.4 release decision — 11 November 2026

The owner reported `pkg info -x os-zapret2-restyle` = `os-zapret2-restyle-0.6.3_52` after an in-place package update; Strategy Lab worked again. Next the owner completed full packaged purge and clean installation of the same testing `.pkg`. With saved WAN, Lab worked both on a clean/empty Config before initial ordinary Start (STOPPED) and after saving a valid populated strategy with ordinary service RUNNING. The domain connection test worked. The owner explicitly accepted **the full Voice Transmission service test scope**. After review of the formal nine-step plan, the owner clarified that **ordinary GUI uninstall → reinstall → user settings preservation was tested previously and worked**; this historic evidence is accepted without demanding a redundant physical repetition on the same `_52`.

These are owner statements about actual functional behavior, not a captured Stage60 graph, provider/media packet capture, physical IPv6 WAN or first GUI upstream setup receipt. Previous native G03 first runtime install and GUI contracts, G10/G11 disposable published-package lifecycle and ordinary GUI uninstall have their own separate qualified proof. The new stable [`v0.6.4_1.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.4/os-zapret2-restyle-0.6.4_1.pkg) has subsequently been **published and verified** through the [full release workflow](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42947369851), with tag `b3473d5d95055cb76d8a2c8add176f4615e282d5` and package SHA-256 `f9e0fa8ceca542ea618fc1f67e88311c80ceda4bb0bc00d7ac94e5398f860be7`. Do not claim that this exact final stable archive has already been owner-installed or that each fault/physical-IPv6/media row A01–A22 was rerun on `_52`. These are distinct acceptance layers. [Release notes](../releases/v0.6.4.md).

## Owner-live Stage50 forensic evidence — _47 (10.11.2026)

Проверены два локальных сохранённых Job (`job.gaL6kG`, `job.7d8aJZ`) и read-only watch на FreeBSD 15.1-p6 с `os-zapret2-restyle-0.6.3_47`. Native WAN preflight: `vtnet1`, scoped IPFW `19100 divert 9989` создан, Stage90 удалил. В обоих логах dvtws2: `Loaded 1 hosts` → `binding divert4 socket` → `Running as UID=65534 GID=65534` → `file_open_test: Permission denied` → `cannot access hostlist file`. Причина — ancestor `/var/run/zapret2-restyle` режим `0750 root:wheel` и отсутствие search permission для nobody. Старые CI fixture проверяли только job dir `0711`, runtime `0755` и hostlist `0644`, не их предка. Дополнительно `readiness.json` ложно сообщал `log_clean=true` при этой ошибке. Published _50 uses only an ephemeral root:nobody `0640` hostlist in `/var/run`; owner-private job ancestors remain closed. Exact-head native G06 RUNNING/Voice Stage50 7/7 and Stage90/99 (original FD9 preserved), G09 STOPPED Stage50/60/90, CI PASS. **Physical owner installed verification is still OPEN**; prior _47 failure is not a PASS for _50 (#1022).

**Latest source handoff (11.11.2026):** `v0.6.3_53` — documentation/publication record only, no `_53.pkg`. The immutable current owner-testing artifact is [`v0.6.3_52.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_52/os-zapret2-restyle-0.6.3_52.pkg) (source/tag `92a883b50466cb33da7ed062f821b743c45c485f`, SHA-256 `6ddf9ff0c3cb3c0a849d86eba32897aa5c65f3c08a56bef910f078ed3129b48e`, `FreeBSD:15:amd64`), [publisher #42941989161](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42941989161). Native root→nobody hostlist and 15/15 Stage60 literal-IP control passed, but the owner must confirm `www.youtube.com` real-domain Stage60 and STOPPED/RUNNING Stage90 on installed `_52`. The historical `_50` owner failure below is retained as failure evidence.

## Публикационные исходные данные

- Stable predecessor: [v0.6.3](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.3), пакет `os-zapret2-restyle-0.6.3_1.pkg`, SHA-256 `eecae7fd21665dd74311323e9359467065663ba6a5662bd0d1c31d847296d0be`.
- **Current published testing successor**: [`v0.6.3_52.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_52/os-zapret2-restyle-0.6.3_52.pkg), immutable source/tag `92a883b50466cb33da7ed062f821b743c45c485f`, SHA-256 `6ddf9ff0c3cb3c0a849d86eba32897aa5c65f3c08a56bef910f078ed3129b48e`, ABI FreeBSD:15:amd64. [Publisher #42941989161](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42941989161) published and verified the exact pkg; automatic record PR denied only by Actions permission. Real native G09 FreeBSD root→nobody hostlist read PASS; Stage50 7/7, Stage60 15/15 on routed public literal-IP control, Stage90 STOPPED restored. **Owner-live Stage60 domain and all G11 A01–A22 are OPEN**; stable Pages/pkg unchanged. The historical `_50` owner trial remains documented below.
- `v0.6.3_34` — only docs/publication record after `_33`; **no `_34.pkg`**. Stable Pages/pkg repository stays on `_1`.

**New G10A nine-stage native smoke (source-only _35, test-only):** `scripts/stage11-published-nine-step-native.py` and `.github/workflows/g11-published-nine-step-native.yml` exercise exact **published** `_1` and `_33` archive SHA and the original companion asset (historical test evidence only); new installations use direct `.pkg`/`pkg add -f` and no file:// pkg repo. It tests stock server-side Firmware removal/menu cache, user Config/runtime preservation, the installed self-deleting purge and initial clean defaults. This **does not** on its own prove full two-pass functional regression, RUNNING original stable _1 upgrade, physical GUI clicks, or A01–A22. These remain explicit negative receipt fields until actually tested. Do not invite owner before full G10A gate.

**CL-01-PERSIST (new owner decision 10.11.2026):** after normal Firmware/pkg uninstall the root-owned standalone `purge-os-zapret2-restyle.sh` MUST survive at the same console path, even if all GUI service/menu files are gone. The physical `.pkg` owns only the share/ template, the native `+POST_INSTALL` copies it atomically to the unowned target; a second, explicit `--purge` without any reinstall must remove Config/upstream/Lua/BIN/Voice/Lab/FD9/owned IPFW/repo **and the script itself**, preserving private backup and all unrelated resources. When pkg is still present, purge first invokes its native `pkg delete` and performs identical cleanup. Separate native positive gates cover BOTH orders; previous `_33` owner testing did not. Historical already-published `.pkg` remains immutable.

**G01-TTY root cause and binding fix (10.11.2026):** published `_33` uses `exec /usr/bin/env python3 - "$@" <<'PY'`, occupying stdin with the Python program; its interactive `input()` therefore sees EOF every time. Owner `--purge` failure is a script bug, not absence of confirmation intent. **No backup or files were removed.** Next source uses `/dev/tty`, requires true interactive terminal and exact phrase before any backup, refuses non-tty/incorrect/EOF; CI-only disposable automation keeps its separate gated path. Do not ask owner to retry `_33` for purge; wait for published corrected `.pkg` and successful native terminal tests.

**Owner-live receipt 10.11.2026 — published `v0.6.3_33.pkg`:** native `fetch` → `pkg add -f` → `pkg info` succeeded on existing installation; saved settings retained after upgrade and after normal GUI uninstall/reinstall; server menu disappeared correctly; Zapret2 runtime manually installed and service started; Lab worked both STOPPED and after reinstall; Extra Lua/BIN install/remove through GUI worked. This supports only the actually observed portions of steps 1–6, **not** the complete two-pass regression/A01–A22. The owner called packaged `--purge`, which printed a read-only inventory but **refused** with `EOF when reading a line` at the exact confirmation prompt; consequently no cleanup, backup or proof of clean state. A later normal GUI uninstall removed the packaged script, while saved Config/upstream/Lua/BIN remain by design. **Steps 7–9 OPEN.** New UX requirement: no purge «Полезные ссылки» on Strategies page in any locale; only README/G01/G11 and root CLI expose these commands.

**Nine-stage smoke result:** [#42777032678](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42777032678) **PASS** for published `_1` STOPPED predecessor → published `_33` and all nine ordered native smoke phases, with menu invalidation, Config retention, package local purge self-delete and clean defaults. The receipt explicitly refuses to claim complete A01–A22, two comprehensive regressions or old `_1` RUNNING upgrade. A separate source-only `_36` native witness tests the last item under unchanged physical `_33` assets; none of this instructs the owner to install before full G10A.

## Owner G11 clean reinstall receipt — 10 ноября 2026, exact published `_40`

На реальной OPNsense владелец выполнил `--dry-run`, подтверждённый `--purge` с `PURGE COMPLETE` и приватным Config backup, проверил отсутствие пакета, скрипта, runtime, собственных каталогов и `dvtws2`; после повторного `pkg add -f` получил `zapret-config=initialized`, правильные defaults `Traffic Strategy` и `YouTube Domains`, успешный setup `v1.0.7`, RUNNING no-action, работу Voice и Extra BIN. **Stage 10 FAIL** при RUNNING с пустым профилем: `Zapret2 is in an incomplete or unknown state`. **Stage 50 FAIL** независимо от RUNNING/STOPPED и наполненности стратегии: `Temporary candidate infrastructure failed: candidate system adapter wan failed`; Stage90 restoration PASS, Stage99 ERROR. До установки runtime при полностью пустых полях нижний Apply выдаёт общий RU preflight вместо специально запрошенного сообщения об установке службы; корректный доступ к WAN dropdown в этом состоянии требует уточнённого GUI теста. Эти FAIL не равны отсутствующему Lua/BIN: Stage50 отказывает при разрешении WAN до launch временного dvtws2. Полная G11 A01–A22 НЕ ПРИНЯТА; отдельно требуется native original-FD9 qualification и новый тестовый пакет.

## Published `v0.6.3_43` native evidence and next owner gate

[Publisher #42839892447](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42839892447) successfully built and verified [`v0.6.3_43.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_43/os-zapret2-restyle-0.6.3_43.pkg), but failed **after publication** because GitHub Actions cannot create its required record PR. Its pushed evidence branch is completed manually in docs-only `_44`; no package rebuild or stable promotion. [G06](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42836322198) native original-FD9 RUNNING/no-action Stage10/90 PASS, [G09](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42836322103) real STOPPED Stage50/60/90 PASS, [G11 no-runtime HTTPS + G05 WAN-only](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42838740717) PASS, and [Chromium WAN select/Apply/F5](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42838739432) PASS. **Physical owner G11 `_43`, actual blocked ISP DPI, IPv6 and real Voice media are NOT TESTED.**

## G11 owner `v0.6.3_43` regression — source candidate `_45`, OPEN

Owner physically upgraded `_40 → _43`, then independently performed full approved purge/true clean install. With valid selected WAN and working upstream, Lab Stage00/10/20/30/40 PASS but Stage50 FAIL: clean STOPPED/RUNNING, empty/populated strategies → `candidate system adapter wan failed` before a temporary runtime or `readiness.json`; existing RUNNING upgrade → independent `candidate runtime did not become ready`; all preserve Stage90 STOPPED/RUNNING correctly. User-empty lower Apply without installed upstream still returns generic RU preflight, despite LC-06D. This evidence supersedes the earlier inference of owner compatibility from disposable OPNsense PASS. [P0 issue #1022](https://github.com/Tolian82/os-zapret2-restyle/issues/1022) OPEN.

Source-only `v0.6.3_45` corrects only the Stage50 canonical saved-WAN adapter and hardens actual G09 candidate readiness proof. It is **not published or owner-tested**. The missing-upstream GUI message and real RUNNING candidate readiness remain separately blocked; do not purge/reinstall again to obtain evidence.

## G11 source-only `v0.6.3_46` — LC-06E/LC-12D

Уровень готовности: **CI/native ещё не подтверждены, owner G11 OPEN**. После слияния source-only `_45` ([PR #1023](https://github.com/Tolian82/os-zapret2-restyle/pull/1023)) осталось два разных блокера: нижний Apply без upstream и failed runtime on upgraded RUNNING. Для первого native G11 заново проходит первичную установку с настоящим `strategy.trafficargs` и десятью `hostlist.youtubedomains`, а не прежнюю искусственную очистку, сохраняет WAN-only и проверяет точный ответ во всех состояниях формы. Для второго добавлен проверяемый `failure_kind` из фактических PID/socket/log observations без увеличения тайм-аута и без утверждения, что сам запуск на системе владельца починен. Стратегия, Voice, WAN-only, FD9, foreign IPFW и Stage90 должны остаться без регрессий.

## G11 owner testing package `v0.6.3_47` — physical acceptance OPEN

Immutable testing [native `.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_47/os-zapret2-restyle-0.6.3_47.pkg), SHA-256 `df53719f8c7463caa901af1a2f4eda3efdf6b3858fc1a60af4ebe4963ff237fc`, exact source/tag `f47eb7dbdf37fde1a3a99aaf048bed28e373c25f`, FreeBSD:15:amd64. The native G06 Stage50 7/7 PID/divert/stable-readiness and Stage90/99 RUNNING restoration are OPNsense 26.7 **test-guest** evidence, not ISP DPI/YouTube acceptance. Owner should run normal `fetch` → `pkg add -f` → `pkg info` upgrade first, without pre-uninstall/purge, and verify real Stage50/90 with RUNNING, then separately stop/empty/config cases. Preserve historical owner `_43` FAIL in issue #1022 until actual owner retest. Package publisher successfully verified GitHub asset before its separate PR-creation authorization failure; publication facts recorded in `docs/verification/evidence/testing-publications/v0.6.3_47.md`.

## G11 LC-12E — native RUNNING→Stage50→RUNNING qualification (source-only `v0.6.3_47`)

Following PR #1024 (merged `45e90854`), the real initial seeded no-runtime Strategies API test and Chromium WAN/F5 both passed on one disposable OPNsense 26.7 guest; owner browser RU display and owner hardware still require acceptance. The original G06 running-service Lab test canceled at Stage10 and missed Stage50. New one-VM G06 witness enters **RUNNING with populated ordinary strategy plus Voice**, uses a routed public TCP-negative control, waits for Stage50 and asserts each family's actual PID/divert/log readiness, cancels via installed API and compares original FD9, runtime artifact hashes, Config and foreign IPFW after Stage90/99. This is NOT proof of a DPI bypass nor of the owner's upgraded RUNNING issue until hardware evidence repeats the result. Issue #1022 stays OPEN, no `_46.pkg` publication from a synthetic network control.

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
