# os-zapret2-restyle — краткий master plan

## Завершённая поставка — stable v0.5.8 (24 October 2026)

The owner accepted the new cached Lua/BIN Full Help (H1) on published `v0.5.7_48`, signed off the [final acceptance report](verification/evidence/2026-10-24-v0.5.8-owner-acceptance-and-release-authorization.md), explicitly closed M6, and **authorized full stable `v0.5.8` publication**. The exact release-preparation identity is `VERSION=0.5.8`, `PLUGIN_REVISION=1`. First verify release PR CI and FreeBSD15 `0.5.8_1.pkg`; then immutable tag/GitHub non-prerelease release and Pages package repository/Web setup.

Prior M0–M6 campaign remains owner-closed; **M6 cold-boot/IPFW/Voice regression was not performed** and is not relabelled PASS, and selected M2/M3/M5 negative cases remain unverified. M4 normal-path native BIN/Lua/Stage-90 restoration passed on installed `_47`. No extra clean reinstall development (cancelled by owner), repeated Strategy Lab Jobs, or new fault injections. Treat publication readiness separately from unobserved owner Web-upgrade clicks. See [acceptance board](verification/EXTRA_RESOURCES_ACCEPTANCE.md), [normative requirements](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) and [release plan](releases/v0.5.8.md).

Once the release succeeds, update current project state with exact tag, package SHA-256, pkg metadata and public availability; then stop the finished project rather than reopening historical milestones.

## Текущий приоритет — Remove Additional Resources, Stage 1 read-only planner

Owner-approved on 24 October 2026: add a bilingual **Remove Additional Resources** button below Install, visible only in native Advanced mode. The future action physically removes all non-upstream Lua/BIN (including manual/orphan files) but only **after** a read-only native compatibility preflight confirms both saved Strategies and Voice (including meaningful disabled drafts) can use **only the installed Git HEAD standard resources**. On incompatible/unknown dependency, warn and perform no mutation. Use existing snapshot/rollback/native FD9/Stop→Start; on success cache/Help reports additional resources not installed and new Lab Jobs see upstream-only inventory. [Requirements](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) · [implementation plan](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md). **Required penultimate pre-release documentation gate:** revise README.md “Useful runtime paths” with `/usr/local/etc/zapret2/lua/` and `/usr/local/etc/zapret2/files/fake/`; revise “Additional Resources — installed Lua/BIN help” to describe the optional expanded integrity-verified Lua/BIN pack from [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources), without promising universal DPI bypass. See [updated specification](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) and [plan Stage 12](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md). **Stage 1 merged and source/FreeBSD15 CI qualified** ([PR #577](https://github.com/Tolian82/os-zapret2-restyle/pull/577)). **`v0.5.9_2` qualified Stage 2 upstream-only temporary view/native Blob resolver (PR #578); `v0.5.9_3` adds real common native Strategies candidate compilation test over that view**; complete saved Strategies compiler compatibility, Voice, transaction, GUI and installed appliance remain pending. No testing package or stable release authorized. The already owner-authorized v0.5.8 delivery is a separate earlier scope.

## Предыдущий приоритет — Additional Resources implementation

Stage-4 source update v0.5.7_18 adds bounded dynamic TLS BIN/Lua nodes to the existing Stage-60 graph using reviewed installed descriptors and job inventory; native on-appliance execution/health evidence and package lifecycle repairs remain open. No release is authorized by this step.


**Immediate blocking priority (v0.5.7_15 source):** narrow correction for
owner-installed 0.5.7_10 failed kernel cold-state observation (ipfw/ipdivert
unloaded, FreeBSD ipfw exit 71), preserving committed journal and the
already merged ECH-off Chrome behavior. The old installed PRE-DEINSTALL still fails for this cold state; new PRE-INSTALL must refuse replacement rather than claim safe migration. Owner-installed boot/restart
acceptance is required before further dynamic Lua/BIN job execution.

The owner explicitly started the approved [five-stage implementation plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md)
on 22 October 2026. Catalog-side Stage 1 capability metadata and validation
are [merged and CI-verified](https://github.com/Tolian82/zapret2-extra-resources/commit/ccdd8fae375e9d3fcb2592a803e10a10d52c49f2);
the plugin has a new read-only immutable-revision catalog/collision preflight
in source (`v0.5.7_9`), including a new manually invoked bilingual Settings-page GUI and bounded result polling, refusal of direct setup bypass, preservation of pending upstream rollback evidence, and a lifecycle-serialized transaction plus guarded upstream-retention backend; installed OPNsense verification remains open. GUI is source-wired, **not owner-tested**; dynamic candidate generation is source-tested, while installed package/live execution is not yet proved. Stage 2 native restart and upstream interruption/recovery remain acceptance gates. The separate stable `v0.5.7_1` release was published 22 October 2026 ([evidence](verification/evidence/2026-10-22-v0.5.7-full-release-publication.md)); this does not authorize publishing the new Additional Resources feature.

## Previously prioritized — accepted Strategy Lab release preparation

The [target requirements](REQUIREMENTS.md) and [detailed English plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) include the owner's 21 October 2026 correction: **a verified target TLS handshake OR QUIC handshake OR genuine final HTTP response individually proves reachability**. HTTP/1.1 and HTTP/2 are equally positive when observed; 4xx/5xx replies count as accessible. Get the current FreeBSD `latest` curl-impersonate at each build per ugorur, with lexiforest as upstream reference, no version pin, and one supported Chrome profile. Direct HTTPS success by handshake or response skips QUIC.

Последовательность принятых этапов:

1. Поставка готового клиента FreeBSD `latest` без закреплённой версии и выбор доступного Chrome-профиля.
2. Migrate Standard/Model C and finalists to the handshake **OR** authentic HTTP-response classifier.
3. Extended TLS 1.2/cleartext HTTP and target QUIC handshake **OR** genuine HTTP/3 response (no mandatory HTTP3 GET).
4. Ограниченное расширение QUIC-каталога в конечном бюджете.
5. Достоверные результаты, RU/EN и совместимость сохранённых заданий: **Stage 5 CLOSED по явному решению владельца**, с принятыми GUI/F5/RU/EN/сохранёнными заданиями; неаудированные частные варианты остаются ограничениями доказательств ([запись приёмки](verification/evidence/2026-10-22-v0.5.6_17-owner-stage5-closure-stage6-stop-gui.md)).
6. Поставка и приёмка установленного пакета: **выборочный Stage 6 runtime/Stop PASS** на установленном `_17`: Stop через GUI 2 раза, затем нормальная служба RUNNING, нет активного Job, временных IPFW `19100–19131`, слушателя `9989` и видимого временного worker. [Квалификация и границы V1–V11](verification/evidence/2026-10-22-v0.5.6_17-stage6-installed-hygiene.md). **Stage 6 ACCEPTED / CLOSED по решению владельца от 22.10.2026**, в согласованных границах наблюдений; непроверенные положительные QUIC-кандидаты и отдельные матричные случаи не объявляются PASS. **Релиз запрещён до отдельного распоряжения владельца.**

The owner has accepted the bounded Stages 1–6 completion and authorized a subsequent full `v0.5.7_1` package release with a README capability audit, retained prior credits and GUI polish. The [v0.5.6_3 testing package](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_3) passed FreeBSD15 CI and owner-installed default Chrome HTTPS/TLS and UDP443 HTTP3-only checks with certificate verification; [evidence](verification/evidence/2026-10-21-v0.5.6_3-owner-live-chrome-tls-quic.md). Owner's additional forced TLS1.2-only GitHub test passed with verified certificate, HTTP2 200 and exit 0, so **Stage 1 V1 is fully accepted**. Stage 2 Standard/Model C source integration passed CI and was delivered as [testing package v0.5.6_5](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_5). On 22 October 2026 the owner accepted the `_13` GUI behavior and closed Stage 3 by decision, without claiming verified QUIC bypass for a blocked HTTP/3 service. Stage 4 catalog extension was published and installed as `_14` (13 QUIC entries), but owner Extended `x.com` exposed a Stage-80 direct-QUIC premature whole-job exit that drops Stage-70 stable TLS candidates. Corrective testing candidate `_15` was source-CI qualified and [published](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_15); it preserves the separate QUIC result and mandatory Stage-85 TLS replay; [owner evidence](verification/evidence/2026-10-22-v0.5.6_14-xcom-direct-quic-premature-termination.md). The owner-supplied `_15` Extended `x.com` GUI observation [passes the bounded Stage-4 acceptance](verification/evidence/2026-10-22-v0.5.6_15-owner-xcom-extended-stage4-pass.md): 13 QUIC candidates tested, no QUIC winner, two protocol-correct TLS/HTTP finalists with 1/1 replay and restoration-success summary. Stage 4 is closed for this scenario. Published `_16` introduced read-only saved-job lookup, selected-history F5 and legacy replay-proof guard; published `_17` added the inline Job ID clipboard and RU/EN circular help. Owner confirms saved-job retrieval, GUI operation, F5 and RU/EN PASS, explicitly **closed Stage 5**, and subsequently reported **two consecutive GUI Stop PASS** observations for Stage 6. Stage 6 now has owner live installed post-Stop restoration/cleanup hygiene PASS within the recorded scope; full-matrix gaps remain explicitly unverified, while the owner has **accepted and closed Stage 6 within the documented scope**. The earlier stable `v0.5.7_1` was published; further release promotion of later development candidates requires a separate owner instruction. Do not rerun accepted tests or treat an unproven QUIC bypass as success. No Firefox, ordinary curl fallback, mandatory HTTP body, upstream version pin, Python/Model C replacement or new recovery architecture. The existing published v0.5.6 tag/assets remain immutable; the separately authorized stable v0.5.7 release was published and verified through the exact-subject release trigger and FreeBSD15 Pages/pkg workflow.

## Основной завершённый путь

- Независимый native OPNsense plugin, обычный runtime/service lifecycle, Traffic Strategy и HOSTLIST/IPSET.
- Zapret2 Service GUI для upstream install/update/reinstall/downgrade; Diagnostics и asynchronous Strategy Lab.
- Python orchestration, adaptive search, конечные бюджеты, Model C, source-port attribution/leasing и readiness.
- Generic UDP exact bytes, persisted Enable QUIC и QUIC candidate search; domain/IPv4 + optional Host/SNI, truthful results и fixed-IP replay.
- Owner-live закрытие выбранных сценариев линии v0.4.x и стабильная поставка [v0.5.0](releases/v0.5.0.md).
- Общий backend Voice/Strategies, подтверждённый Voice Apply, сохранность Voice-конфигурации и принятый GUI/RU/EN; подтверждённый Strategies Apply после исправления большого неизменённого запроса. Границы доказательств — в [PROJECT_STATE](PROJECT_STATE.md).
- Полный [v0.5.6](releases/v0.5.6.md) опубликован через GitHub/FreeBSD15/Pages. Установка владельцем через GUI остаётся неподтверждённой, без повторного открытия завершённой разработки.

## Telegram Voice — закрытая кампания

Владелец завершил исследования 20.10.2026 с отрицательным результатом на прямом UDP OPNsense. Положительный pfSense-контроль оказался связан с VPN-маршрутом; он не доказывает Zapret2-обход того же прямого провайдера. `MEDIA_PASS=false`, `CALL_PASS=false`; точная причина потери ответа не установлена. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

Старые предложения capture, fake/TTL, SOCKS/UDP и реальных звонков не являются активной очередью. Возобновление требует нового явного задания владельца. GUI/Config/Apply и действующие профили сохраняются.

## Независимая лаборатория и persistence

Сохранённое направление вне текущей HTTP-модернизации: штатная OPNsense persistence и квалификация LAN/router-local/SOCKS при конкретном новом задании. Рабочие TCP/TLS parent-пути и отдельный UDP/Zapret2 тракт не объединяются. Non-GUI sing-box/ACL/alias/snapshot и фактический reboot проверяются только в относящемся к ним сценарии.

Ручные OPNsense→TNAS SSH/host-route repair остаются ручными; route Cron/configd/boot scheduling и Docker autostart не планируются. Старые Telegram-проверки из runbooks не возобновляются автоматически. Исторические факты и команды: [operations](architecture/TELEGRAM_LAB_OPERATIONS.md), [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md), [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [helper](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). Эти направления не добавляют TCP/proxy/routes в плагин.

## Сохранённый будущий backlog

- Cancellation/internal-failure containment; circular start/stop/TTL и stale-session recovery при конкретном основании.
- Diagnostics persistence/reload; retention/cleanup; reboot/residue regression.
- Runtime/service reliability и package/runtime visibility; дальнейшие точечные RU/EN исправления.
- IPv6 Laboratory target support — отдельная архитектурная задача.
- **Дополнительные Lua/BLOB ресурсы — owner-approved 22.10.2026; catalog descriptor/validator Stage 1 merged and checked, plugin-side Stages 2–5 pending.** Отдельная ручная кнопка «Установить дополнительные ресурсы» / “Install Additional Resources” под статусом на странице «Стратегия»; источник [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources). Установка транзакционная, **по явному нажатию при запущенной службе** с обязательным **Stop→Start и health-check Zapret2** перед успехом; при `Stopped` сначала требуется штатный Start. Без перезаписи штатных/пользовательских файлов и без загрузки автоматически при смене upstream-релиза. Динамический `ResourceInventory` + **генерация совместимых кандидатов из фактически установленных Lua/BIN без hardcode имён файлов и без переписывания кода при обновлении набора**, адресный `--lua-init`, конечный бюджет, прежние стратегии не меняются. [Утверждённое ТЗ](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) и [принятый пятиэтапный рабочий план](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md). **Кнопка и интеграция реализованы в исходниках до `v0.5.7_22`; приёмка на установленной OPNsense и актуальная публикация этого функционала ещё не проведены.**

Эти направления не превращаются в обязательные блокеры текущей HTTP-модернизации или прежних релизов без конкретного затронутого сценария.

## Отложенные исследования

Candidate parallel width выше трёх, endpoint parallelism, cross-batch keep-warm, BLOB/Lua/discovery optimization и Model-C timeout/deadline audit открываются только при новом конкретном дефекте/потребности, материальном изменении архитектуры либо выборе владельца. Завершённые измерения сохранены в истории.

Текущая граница — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [ledger](history/current/v0.5.x.md). Roadmap не накапливает ревизионные отчёты.
