# ТЗ_6v5 — S03c2: реальный native G05 → G03 configd → G08 до первого обычного Start


## Первая native попытка — установлен точный блокирующий этап, НЕ PASS

[OPNsense disposable G08 run #45108567546](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45108567546) на HEAD `2ea7203311702d31a72c0abb096f7a829084b419`: **G05 authentic native PASS**, включая WAN-first, engine-second, HTTPS Config persistence, пустые пользовательские стратегии и reinstall того же CI pkg. Следующий независимый stock G03 `configd setup_install v1.0.7` дал `G03_SETUP_WORKER_REPORTED_FAILURE`; до настоящих двух Lab jobs выполнение не дошло. Причина пока **не установлена**. Это не Stage90/99 FAIL, не runtime V5 GREEN и не основание править product source без диагностики.

В следующем test-only HEAD G08 при `g03.dispatch_and_poll()` отказе сохраняет **ровно существующий** `g03.bounded_disposable_failure_evidence()`: ограниченный/redacted `/var/log/zapret2/setup.log` + root-owned setup state/missing path markers, а затем возвращает typed `S03C2_G03_FIRST_CONFIGD_INSTALL_REFUSED` / `S03C2_G03_SAME_RELEASE_REINSTALL_REFUSED`. Никакого автоматического повторного Start/Stop/force и никаких новых свидетелей. **CI нового HEAD ожидается.**


**Исходная точка:** `main 09a8947d026b156909e9e4d1e76a6bfd94fceeb6`, `v0.6.5_134`, PR #1243 S03c1 exact-head disposable native PASS 7/7. Этот checkpoint — **source-only candidate `v0.6.5_135`** в ветке `feat/tz6v5-s03c2-auth-native-prestart`. `os-zapret2-restyle-0.6.5_135.pkg` **НЕ выпущен, не опубликован и не устанавливался владельцу**. Нативная приёмка в одноразовой CI-OPNsense **временно собирает тот же pkg локально в госте** с official Mk и проверяет SHA-256: это временный тестовый артефакт внутри VM, а НЕ testing release S19. На пользовательской OPNsense последняя подтверждённая установленная версия `_117.pkg`, её не трогали.

## 1. Обнаруженная ошибка композиции старого нативного теста

Исторический [G08 native runner](../../scripts/stage2-opnsense-g08-prestart-lab.py) вызывал `g03.main()` из [G03](../../scripts/stage2-opnsense-g03-first-install.py). Однако современный `g03.main()` после действительной установки/переустановки `v1.0.7` продолжает **отдельную регрессию** `five_hostlist_native_apply()`, которая запускает обычный `dvtws2`, затем выполняет обычный `stop/start/restart` и оставляет общий FD9-owner. Это противоречит инварианту **G08/LC-12: ни одного обычного Start до двух Lab Job**.

**Исправление только в тестовой композиции G08:** отдельный `actual_g03_upstream_install_without_ordinary_start(g03)` вызывает действующие `g03.status()`, `g03.native_template_snapshot()`, **дважды реальный `g03.dispatch_and_poll()`** (он делает именно stock `configctl zapret setup_install v1.0.7`), проверяет установленный нативный release marker, exact `refs/tags/v1.0.7^{commit}`, сохранность Config и IPFW, отсутствующие PID/FD9 owner/обычный процесс. **G03 standalone не модифицируется** и сохраняет свой обычный самостоятельный five-list lifecycle тест. Второй OPNsense guest для G03 не запускается.

## 2. Source + S2 native acceptance без моков

В **одном** [G08 disposable OPNsense 26.7 workflow](../../.github/workflows/g08-native-prestart-lab.yml) применяется тот же уже установленный сценарий:

| Порядок | Фактический путь | Обязательный native witness |
| --- | --- | --- |
| 1 — G04 | Official Mk временно собирает единственный локальный pkg `_135` в disposable guest, выполняет настоящий `pkg add`, сохраняя SHA-256 | Native конфигурация OPNsense в `/conf/config.xml`, исходно Enabled OFF и WAN пустой; обычный Zapret2 ещё не стартовал |
| 2 — G05 до engine | Настоящий HTTPS cookie+CSRF `/ui/zapret`, `/api/zapret/settings/apply` и configd/Voice/Lab preflight | `wan-required` до target/engine/Job. Сохранён WAN (lo0 затем wan), без установленного upstream, без dvtws2, со штатным original FD9 и SharedConfigCommit; пустые Traffic Strategy/YouTube сохраняются, повторная установка того же pkg сохраняет Config |
| 3 — G05 engine-second | Реальные GUI, configd и CLI при WAN saved, upstream absent | `engine-not-installed` до Job, no Config/PID/IPFW mutation |
| 4 — G03 without first Start | Stock configd `setup_install v1.0.7` + stock native status, дважды; НЕ запускать `g03.main()` с five-list lifecycle | Installed exact tag, status STOPPED, Config byte-exact и IPFW unchanged, engine installed, no owner journal/PID; нет обычного Start или hidden five-list regression |
| 5 — G08 | Два настоящих authenticated HTTPS Lab `start/status/result`: Standard RU и Extended EN | Два разных `job.*`, Stage00/10/20/30/40/**90/99 PASS**, `TARGET_ACCESSIBLE` по публичному TLS control, Stage50 SKIPPED; Stage90 `restoration.verified=true` и `STOPPED→STOPPED` |
| 6 — G08 cleanup witness | Native `zapret_service.sh status`, process census, Config bytes, all real IPFW numbers | No ordinary process/PID/FD9 new owner; никаких оставшихся owner-active `19000–19099/19100–19131`, все чужие правила и `65534/65535` сохраняются. `19132–19139` и reserved future `19140–19200` не считаются нашими |

**Дополнительное усиление S03c2:** сохранённые User Domains тоже должны быть пустыми перед первым Lab; у terminal Stage99 проверяется именно PASS, а не только наличие `current_stage=99`. Read-only stock WAN resolver, настоящий native PHP/OPNsense Config и HTTP API участвуют без injected `wan_preflight.sh` из S03c1. Никаких `SIGSTOP/SIGCONT`, владельческих PID kill, широкого IPFW flush, нового Config writer или эксперимента с upstream HOSTLIST reread.

## 3. CI и строгое толкование

Workflow проверяет оба Python-скрипта компиляцией, затем [G08 prestart fixture](../../scripts/stage2-opnsense-g08-prestart-lab.py) `--self-test` как дополнительный негативный контроль и **один native guest**, без второго G03 job. Exact-head native success выдаёт:

```
G03_NATIVE=...PASS_G03_REAL_CONFIGD_FIRST_INSTALL_AND_REINSTALL...
S03C2_G03_NATIVE_INSTALL_ONLY_BEFORE_FIRST_START=PASS
G08_NATIVE_PRESTART={"status":"PASS_G08_REAL_STANDARD_EXTENDED_BEFORE_FIRST_NORMAL_START",...}
S03C2_AUTHENTIC_G05_G03_G08_BEFORE_FIRST_START=PASS
S03C2_UNIFIED_LAUNCHER_AND_OWNER_LIVE_NOT_CLAIMED=1
```

**До настоящего CI эти строки — ОЖИДАЕМЫЕ, не утверждения об успешном запуске.** При FAIL первична конкретная нативная причина (Config/Job/stage/IPFW/tag/network), а не подгонка фикстур. Контрольная цель `yandex.ru` — внешний заведомо доступный TLS control; при его недоступности нельзя записывать Stage40 или Stage90 «успешно». Реальный Stage50 обход блокировки и DPI bypass этим тестом не проверяются.

Этот checkpoint обновляет **baseline действующего старого launcher `v0.6.5_135`**, а **НЕ** подтверждает ещё не написанный единый runtime S04–S14. После реализации V5 launch эти же G05→G03→G08 regressions должны быть повторены на exact-head.

## 4. Оставшийся S03, нельзя переходить на S04

- Genuine native output/failure for `--force` operator vs foreign/reused PID, birth/epoch, FD9 BUSY/PREPARED and `INCOMPLETE`; только одноразовые аттестуемые процессы.
- Full `--help`/strict action options, dynamic native Error envelope + existing lifecycle RU/EN emitter→GUI caller (только Start/Stop/Restart and adjacent Apply/Lab/pkg/Boot).
- Full effective state decision `SAVE_ONLY|NO_CHANGE|RELOAD|RESTART|START|STOP|REFUSE`, including old/next WAN/mixed, no PID/IPFW change for safe reload, no hidden restart.
- #1224 RUNNING→RUNNING restoration Stage90/99 from native traces, #1223 Auto actual Found ingress; native V5-17 inclusive IPFW port/rules and guarded recovery.
- **S03 overall NO-GO** until those remaining RED/acceptance witnesses. S04–S20 NOT RUN. **No owner appliance actions or S19 published package.**
