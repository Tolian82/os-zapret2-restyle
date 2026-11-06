# Stage 5 — матрица AC-01–AC-11 (ТЗ v1.5)

**Рабочая сверка, не разрешение на выпуск.** Публичный `v0.6.2 / 0.6.2_1.pkg` и устройство владельца не изменены.

**Доказанная основа:** [PR #941](https://github.com/Tolian82/os-zapret2-restyle/pull/941), точный SHA `fa91140ca37972b0222e1c43741c01e341aa03af`, 22 обязательных CI SUCCESS, слит в main `ca154cd5d66943b73383fda2d5b4d1b18fe99290`. [Настоящий reboot #42275072964](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42275072964) PASS с SHA физического пакета `211a7415582b1e9e9883b39428f58077e8d8cd905f40b1b3cf1abcff9c3dd280`. [Два гостя #42275073211](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42275073211) PASS с **другим** одним физическим архивом SHA `245ee23939c1419133afbe0f63913f9549fe45850aa31f2c66d403e0ef1c4eb8`. Эти два разных пакета не объединять в одно доказательство SHA.

**Послеслиянийный exact-main `_168`:** пять маршрутов завершились SUCCESS: [CI #42277347773](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42277347773), [Release trigger #42277347329](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42277347329), [single package #42277347413](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42277347413), [two-guest #42277347354](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42277347354), [RUNNING/Voice #42277347448](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42277347448). В main two-guest общий физический архив имеет **ещё один отдельный** SHA-256 `0c334c413920f6a3758f88fd5bf74ec72e3b6719be5de2e4f47dd58b835ed09b`. RUNNING workflow сначала получил гостевой сетевой `EACCES` при повторном GitHub Install и прошёл при повторе только упавшего задания **на том же source SHA**. Это доказывает работоспособный native сценарий, но не детерминированное исправление тестовой сети.

| Критерий | Статус | Конкретная граница |
| --- | --- | --- |
| AC-01 — единый Python invocation, Status/Stop | PASS (native) | Реальный установленный сервис, Python-down, исторический FD9 и обычный/common owner. |
| AC-02 — нет разбросанных minor Python в production | PASS (source) | Stage 1 policy и нативный runtime; конкретные пути в тестах не считаются production. |
| AC-03 — OPNsense pkg-зависимости | PASS (native 26.7) | Штатный целевой pkg; нельзя включать FreeBSD latest ради системных зависимостей. |
| AC-04 — единая матрица ABI/CPU/Python | PASS (заявленная матрица) | FreeBSD 15 amd64 / OPNsense 26.7; не утверждается поддержка всех версий. |
| AC-05 — единственный штатный Mk builder | PASS | Подтверждены package/manifest/private ELF и native Mk. |
| AC-06 — GUI/configd/service/Strategies/Voice/Lab/Exclude/Extra | PARTIAL | Реальные cookie/CSRF HTTPS/configd Apply, положительный `completed/TARGET_ACCESSIBLE` Lab, Exclude, Install/повторный Install/Remove 73 ресурсов PASS; **физические клики браузера, Voice media и DPI-заблокированный WAN не проверены**. В опубликованном `0.6.2_1` отмечен [открытый дефект #893](https://github.com/Tolian82/os-zapret2-restyle/issues/893) с сохранением WAN/Apply; `_170` includes a source-only correction for a genuine changed native InterfaceField/OptionField; **physical browser WAN selection/Apply/reload on `_170` remains NOT TESTED**. |
| AC-07 — имена, namespace, версии, upstream manager | PASS (native) | Сохранены `zapret`, `VERSION`/`PLUGIN_REVISION` и отдельный upstream manager. |
| AC-08 — modes/hooks/ELF/IPFW/PF | PASS (lo0, native) | 292 pkg-файла, 4 оригинальных hooks, private ELF, чужой IPFW сохранён. Общий FD9, правила 19000/19001 и Voice-таблица после нового ядра PASS; реальный WAN/потеря питания не доказаны. |
| AC-09 — CI/ABI/Python и **финальный пакет SHA** | PARTIAL | Один физический пакет доказан для пары гостей; reboot — **другая** сборка, а конкретный итоговый release-кандидат ещё не выбран. |
| AC-10 — актуальная документация согласована | OPEN | Исторические слова «не принято» остались в активных сводках `START_HERE` и `PROJECT_STATE`. Исправить без переписывания исторических доказательств. |
| AC-11 — штатный pkg install/update/reinstall/remove | PASS (native) | Проверены реальные сценарии и сохранение настроек, без нового внешнего SQLite/pkg-approval или универсального PRE_INSTALL veto. |

## Ещё не доказано

- **Физический браузер:** тестирование API не подтверждает клик кнопки. Нужен реальный browser E2E на disposable OPNsense, иначе `NOT TESTED`.
- **DPI на заблокированном WAN:** `TARGET_ACCESSIBLE` означает успешный worker и уже доступный HTTPS, **не** успешный обход блокировки.
- **IPv6:** реальный пакетный прогон отсутствует.
- **Медиа Voice:** реальный owner direct-provider Telegram media ранее не прошёл; успешные Apply/FD9/reboot не отменяют этот факт.
- **Abrupt power loss:** clean shutdown + другое ядро PASS, внезапное выключение `NOT TESTED`.
- **Рабочая OPNsense владельца:** ни этот тест, ни финальные docs не разрешают её менять.

## Следующие действия

1. **Выполнено для `_168`:** postmerge main CI, Release trigger, native single package, RUNNING/Voice и два гостя PASS; отдельно зафиксирована первая сетевая ошибка и повтор только неуспешного задания. Не считать это одним финальным опубликованным SHA.
2. Исправить только противоречащие **активные** документационные сводки по AC-10, не переписывать исторические отчёты.
3. Подтвердить физический GUI (либо честно `NOT TESTED`), зафиксировать реальные границы Voice media, WAN/IPv6 и внезапного питания.
4. Выбрать **один конечный физический release candidate** с SHA-256 и повторить необходимые native Install/RUNNING/reinstall/Remove/reboot проверки этого именно архива в рамках ТЗ; разные независимые сборки не считать одним SHA.
5. Выпустить короткий PASS/PARTIAL/NOT TESTED отчёт AC-01–AC-11. Публикация и установка на боевой системе — только после отдельного решения владельца.

Никаких новых механизмов авторизации, SQLite-свидетелей, перехвата pkg, отключения PF или чужих IPFW.
