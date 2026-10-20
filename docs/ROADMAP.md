# os-zapret2-restyle — краткий master plan

## Текущий приоритет — v0.5.5: квалифицировать Telegram UDP responder

На установленном testing `0.5.5_7` владелец 20.10.2026 подтвердил успешные no-op и изменённый Strategies Apply. В том же пакете (engine `v1.0.5.2`) впервые выполнен ранее блокированный **один TTL7 WAN-эксперимент** с ordinary Strategy #4. [Полный протокол](verification/evidence/2026-10-20-telegram-ttl7-wan-owner-live.md).

1. **Закрыто: Strategies Apply.** Сценарии с неизменёнными и изменёнными обычными стратегиями работают на устройстве. Редактирование огромных target-списков требует отдельного транспорта и не принято.
2. **Закрыто: wire proof fake TTL7 и возврат настроек.** 120 fake UDP/16 вышли с TTL=7, 60 оригинальных UDP/40 — с TTL=63, отображённые контрольные суммы корректны. Original Strategy #4 восстановлена через GUI, `zapret` работает. **Нет входящих UDP и вызов не установлен**; TTL7 — не проверенный media-bypass.
3. **Открыто: UDP responder / media.** Ранее A2 подтвердил исходящие non-STUN Hello (без ответа), A3a — отдельный native STUN TX/fake к не квалифицированному responder на UDP/3478. STUN_RX и двусторонний звонок не доказаны.
4. **Owner-live reflector list PASS, UDP A/B completed:** pinned `tgcalls@efd330c` sends non-STUN Reflector Hello; OPNsense SOCKS/Squid and pfSense returned **616** official reflector entries including `91.108.13.10:596–599`. Local `configd` proxy HTTP(S) via Squid was configured and is separate from UDP. After this, the repeated fake-TTL7 trial and one **no-TTL Strategy #4 control** both emitted 120 fake + 60 original WAN UDP and had **0 replies/no call**, with fake TTL 7 vs 63, original TTL 63. [Measured A/B](verification/evidence/2026-10-20-telegram-ttl7-vs-no-ttl-control.md). **Owner-approved bounded independent route check:** current TNAS shows `192.168.1.140` directly connected via `ovs_eth1`; `192.168.4.1` is reached **via .1.140**, not directly. **Completed: `.1.140` pinned same-endpoint 15s control MEDIA_PASS**, Call established=yes @1.561s, both Established, BWE nonzero, CLI0, exact reflector-route restore PASS. [Positive owner-live evidence](verification/evidence/2026-10-20-tgvoice-gateway-140-positive-control.md). `.4.1` remains HOLD pending **read-only topology/source validation**; TNAS has no direct .4.0/24 attachment. [Original test plan](verification/evidence/2026-10-20-alternate-140-and-4-1-control-plan.md). No broad network defaults/IPFW/Voice/proxy edits or TTL sweep.

**Owner clarifies alternate network:** pfSense `.1.140` routes selected Telegram traffic via OpenWrt VM `192.168.1.236` with Podkop TCP/TLS and youtubeUnblock UDP. Screenshot Telegram section STUN selector on, UDP fake 6×64, no TTL/checksum strategy, no UDP port filter or QUIC; pinned reflector Hello is **non-STUN**, so causal attribution to youtubeUnblock is open. **Completed:** direct `.1.236` same-oracle 15s test `call=no`, CLI1, route restore PASS. Owner clarifies **real Telegram uses GOST SOCKS5 `.1.236:1070`**, whereas `tgcalls_cli` makes **direct UDP** and does not exercise that SOCKS. pfSense Squid `telegram_sites ssl::server_name` sends selected HTTPS through parent, not generic UDP. Podkop Telegram community uses GOST `127.0.0.1:1088` upstream parent with UDP-through-TCP off. **Next controlled test:** original reflector through OPNsense `.1.2` with **ordinary unknown fake #4 disabled temporarily**, keeping native STUN unchanged; require real original-only WAN 40-byte packet proof and exact GUI restoration. [Corrected architecture and outcome](verification/evidence/2026-10-20-openwrt-236-youtubeunblock-topology.md). `.4.1` SSH strict host-key failure does not justify disabling verification.

Текущие факты — [PROJECT_STATE](PROJECT_STATE.md), next step — [START_HERE](START_HERE.md). Ранние неуспешные Apply и гипотезы TTL сохранены в [historical evidence](verification/evidence/2026-10-19-reflector-hop-trace-ttl7-first-candidate.md).

## Основной завершённый путь

- Независимый native OPNsense plugin, обычный runtime/service lifecycle, Traffic Strategy и HOSTLIST/IPSET.
- Zapret2 Service GUI для upstream install/update/reinstall/downgrade; Diagnostics и asynchronous Strategy Lab.
- Python orchestration, adaptive search и finite budgets; выбор Model C, source-port attribution/leasing и readiness.
- Generic UDP exact bytes, наблюдаемый QUIC и persisted Enable QUIC; domain/IPv4 + optional Host/SNI, truthful results и точный fixed-IP replay.
- Owner-live закрытие линии v0.4.x; stable [v0.5.0](releases/v0.5.0.md), принятый file-picker corrective `_2` и опубликованный testing `_3`.
- Форма/модель Voice и PoC начинались в v0.5.1; общий page/lifecycle реализован в feature-коде v0.5.2, но owner-live приёмка ещё не выполнена. [Архив](history/stages/v0.5.1/README.md).

## Отдельная Telegram media campaign после page/migration baseline

- Продолжать на одной записанной базе через OPNsense/того же ISP, существующий current-oracle Docker runner и один меняемый параметр. Уже измеренные A1/A2, standalone fragment positions и старые отрицательные опыты не повторять без нового основания.
- Завершить retained runner tooling: RTC logs, bounded ICMP, saved/effective/source/target/process checks, semantic pre/post state и owned remote cleanup. Drift останавливает опыт; восстановление подтверждается отдельно.
- Проверить ограниченную fake-TTL гипотезу по [campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md): не более четырёх начальных значений, фиксированные endpoint/runtime/route, точный stop/restore contract. Это гипотеза, не принятый preset.
- Для media-positive кандидата — три свежих успешных повторения и action-only control, затем реальный клиент с проверенным endpoint, двусторонним UDP и звуком. После MEDIA_PASS/CALL_PASS зафиксировать квалифицированный preset; configuration PASS не заменяет их.
- Если восстанавливаемо, сопоставить September 22 positive CLI evidence. Иначе выбирать один ограниченный опыт по текущему transport, не возобновлять fragment sweep.
- Same-endpoint read-only inventory и alternate-gateway successful-call capture остаются optional causal diagnostics. Не делать обязательный новый UDP exit и не использовать человеческие звонки для каждого кандидата.

## Независимая лаборатория и persistence

- Сохранять документированную LAN/router-local/SOCKS базу: отдельные TCP/TLS parent и UDP/Zapret2 пути. Router-local без explicit SOCKS и SOCKS UDP ASSOCIATE требуют отдельной квалификации.
- Предпочитать штатный OPNsense GUI/persistence; проверить сохранность non-GUI sing-box/ACL/alias/snapshot при regeneration и reboot. Уже рабочие LAN/SOCKS TCP-parent пути сохраняются.
- Persistence выбранного Voice теперь реализуется общей native страницей; дополнительный hook/Cron enable не создаётся. После reboot проверить effective profiles, процессы/правила, LAN/SOCKS/router-local TCP и релевантный UDP до ручного исправления.
- Ручные OPNsense→TNAS SSH/два host-route repair проверены; после реального TNAS reboot остаётся owner-manual проверка восстановления. Без route Cron/configd/boot scheduling и Docker autostart.

Факты и команды находятся в [operations](architecture/TELEGRAM_LAB_OPERATIONS.md), [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md), [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md) и [helper reference](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). Эти задачи не добавляют TCP/proxy/routes в plugin.

## Сохранённый будущий backlog

- Cancellation/internal-failure containment; circular start/stop/TTL и stale-session recovery.
- Diagnostics persistence/reload; retention/cleanup; reboot/residue regression.
- Runtime/service reliability и package/runtime visibility при новом основании; дальнейший RU/EN review выбранных дефектов.
- IPv6 Laboratory target support — отдельная архитектурная задача.
- Дополнительный BLOB repository GUI — только после согласованного технического контракта владельца.

Эти направления не становятся автоматически долгом страницы или уже опубликованного v0.5.0.

## Отложенные исследования

Candidate parallel width выше трёх, endpoint parallelism, cross-batch keep-warm, BLOB/Lua/discovery optimization и Model-C timeout/deadline audit открываются только при новом конкретном дефекте/потребности, материальном изменении архитектуры либо выборе владельца. Завершённые измерения сохранены в истории.

Текущая граница — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [working ledger](history/current/v0.5.x.md). Roadmap не накапливает ревизионные отчёты.
