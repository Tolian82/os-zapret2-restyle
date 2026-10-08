# Telegram Voice UDP strategy campaign — Docker-first Reflector Hello experiments

**Updated 2026-10-08:** helper controls are now explicit for every trial. Owner snapshots measured helper ON → OFF after OPNsense reboot; subsequent manual enable restored native ON/table14/rule. GUI A2 survived unchanged. [Reboot/recovery evidence](../verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md). A1/A2 remain wire-only negative results; RTC/ICMP tooling, strict full-baseline validation, numeric TTL values and new media trials remain pending.

## Binding mission and owner constraints

**OWNER'S BINDING PREMISE:** The **local ISP DPI restricts Telegram voice UDP**. The goal is **Zapret2/dvtws2 UDP desynchronization through the existing OPNsense and SAME ISP WAN**, eventually enabling real voice. Telegram **TCP/TLS already works** via established PF/Squid and matching sing-box→Squid routes to **existing Squid GUI-configured external parent `185.203.117.88:33128`**; owner LAN/SOCKS HTTP/HTTPS checks passed. Squid's HTTP parent does not transport voice UDP, and sing-box UDP `direct` still uses the current WAN/IPFW/provider DPI. **Do not rework or replace the TCP proxy, propose a different UDP gateway/VPN/provider, or convert alternative-egress research into the project goal.** WAN captures prove emitted packets and absent recorded replies, not an exact DPI drop location.

**New explicit owner execution boundary:** **do not require another real Windows/Android call for each candidate.** Stage-1 candidate search runs **first and by default via the existing TNAS Docker `tgvoice-lab`**, with the qualified current `tgcalls_cli` fixed-reflector oracle. Real P2P-disabled Windows/Android `CALL_PASS` is a *final* validation only after a candidate has repeated fixed-reflector `MEDIA_PASS` through OPNsense. A captured alternate-gateway successful Windows call is an optional *separate diagnostic/control for causal attribution*, **not a prerequisite to the next qualified same-ISP Docker experiment**. No per-candidate real-person-call requests.

Before changing any strategy, commit goals, current evidence, precise candidate, test/restore procedure and success/unknown/failure classification to GitHub. After each **actual** measured laboratory run, attach sanitized outcome and archive/hash identities in a dated evidence document, reconcile `START_HERE`, `PROJECT_STATE`, roadmap and current chronology, and **only then** select another candidate. Do not conflate design, owner-reported Apply, observed wire transformation, remote reply and successful media.

Three approved product stages remain **unchanged**: repeated `MEDIA_PASS` on current Docker oracle -> real remote `CALL_PASS` with sustained two-way UDP and good sound -> only then approved Voice-UDP-only integration into the existing plugin Settings GUI, with IPSET/firewall lifecycle and persistent ON. Do not package temporary Docker runners, add a plugin page or implement recurring Cron as part of candidate research.

## telegram_voice controls for every trial

`telegram_voice` is an active part of the laboratory baseline. Its two roles are **destination-scoped all-port Telegram UDP interception** and a **fixed STUN profile** in the same dvtws2. The GUI supplies the separate experimental `unknown` profile for current Reflector Hello. Full configuration ownership, source-defined constants, command meanings and boot procedure belong to the [helper reference](TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md).

**We did not vary helper parameters in A1/A2. We do not vary them in the planned TTL series.** Earlier plan text already required helper ON and the actual runner checked it; this matrix makes those conditions and their evidence explicit. Changing STUN repeats/TTL does not test the non-STUN Hello. A helper/protocol redesign, if later justified by evidence, is a separate epoch and must follow the change-record contract below.

| Control | A1 | A2 / current restored baseline | Planned limited-fake-TTL series |
|---|---|---|---|
| Helper request/effective/profile | ON / ON / ON | ON / ON / ON | Fixed ON / ON / ON |
| Helper STUN action | zero16, repeats=2; no explicit short TTL | Identical | Identical; do not put the experimental TTL here |
| Telegram target set and all-port IPFW rule | Fixed managed set and destination-table capture | Same; current set has 14 prefixes | Freeze exact set, target membership and rule semantics, not just a count/number |
| Experimental GUI profile | IPv4, Telegram IPSET, UDP 596–599, `unknown` | Same | Same scope, until a separately documented comparison changes it |
| Candidate fake checksum | `badsum` | No `badsum`; WAN-valid in measured A2 | Keep A2 intent and verify on WAN |
| Candidate fake blob/repeats | zero16 / 2 | zero16 / 2 | Fixed zero16 / 2 |
| Candidate fake `ip_ttl` | No explicit override | No explicit override; measured WAN TTL=63 on October 3 | Only selected experimental variable; exact values/selector not yet qualified |
| Original forwarding, NAT/PFIL, binary, endpoint, routes, TCP parent | Frozen per epoch | Frozen per epoch | Preserve and measure; no simultaneous changes |

The actual A1/A2 reports prove helper ON/table14 and Voice-rule growth, not merely a GUI entry. The October 7 reboot audit establishes why this remains a mandatory precondition: normal Zapret2 and A2 can be running with helper OFF and no dedicated all-port rule. Manual enable has restored the native status/firewall baseline, but is not automatic boot acceptance or a new media pass.

### Before and after each trial

The existing v4 already rejects missing native Voice ON/table/target/rule before Docker and archives Voice/IPFW/PFIL before/after. Its full-profile identity and strict saved/effective/after-state checks still need the planned extension; do not describe this complete contract as already implemented:

1. Capture UTC and boot/configuration epoch, runner/candidate ID, installed package and dvtws2/Lua/helper-source identities. Read status fields even if `configctl` exits zero.
2. Verify requested/effective/active_profile ON, service running, one engine/divert listener, exact unchanged prepended helper profile and selected complete GUI candidate in saved/resolved/effective/process arguments.
3. Record actual IPFW rule content/order/divert/WAN, table contents and managed-set identity/membership, PFIL/NAT and required routes. `19000` may be TCP after reboot; 14 entries alone do not prove the right target set. Preserve working TCP parent settings.
4. Keep missing or changed baseline separate from strategy outcome: stop before traffic, archive the discrepancy, and never silently run enable/Apply or replace firewall rules. An operator-selected recovery is recorded separately and followed by a fresh verified baseline.
5. After the bounded trial, compare helper/profile/table/rule/route semantics and counter deltas; new PIDs and reset counters are not semantic equality. Unexpected drift makes the comparison unqualified, not evidence that DPI rejected the candidate. Preserve any packet evidence and report restoration/cleanup independently.

For a reboot audit specifically, collect the pristine after-boot snapshot **before** the runner's authorized route/container preparation or manual enable. The completed October 7 audit is not a new per-candidate reboot requirement. Automatic boot recovery is a separate open laboratory task; measured manual recovery plus a passing preflight allows the research series to proceed.

### How any helper change is recorded

Before a deliberate change, commit a candidate/epoch record with: hypothesis and affected protocol; full old/new helper state and profile; target-set/capture differences; GUI action differences; exact single variable; expected wire and status effects; commands/code version; stopping conditions and restoration. A source-coded helper change requires the normal GitHub qualification, not a manual edit on OPNsense.

After the trial, add timestamped saved/effective/process/status/table/rule evidence, observed packet/peer outcome, archive/hash identities, drift and restoration results to dated evidence; reconcile current state and next plan. Keep raw XML, credentials and private PCAP outside public GitHub. A baseline change starts a distinct comparison; do not merge it invisibly into the TTL series.

**Candidate-action OFF is not `telegram_voice_disable`.** Keep helper ON and capture unchanged while disabling only the candidate's experimental action. If a future test truly studies helper OFF/ON, name and measure both its capture and STUN-profile effects separately; it is not the current strategy efficacy control.

## Next experiment: limited fake TTL (planned, not run)

**План уточнён 7 октября 2026 года.** Текущая задача — воспроизводимое установление реального звонка через `.1.2`; сначала отсеиваем кандидаты существующей Docker-лабораторией. [Проверка топологии и прежней документации](../research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md) подтверждает внешний reflector-путь и отмечает исправленные неточности. [START_HERE](../START_HERE.md) остаётся текущей точкой входа.

**Гипотеза:** при правильной UDP checksum, zero16 и двух фейках перед оригиналом ограничение только TTL фейков может изменить поведение DPI, сохранив настоящим пакетам возможность достичь рефлектора. A2 с WAN TTL=63 этого не проверял. Наличие подходящего диапазона TTL, место DPI и достижимость рефлектора сейчас не доказаны. Ожидаемый результат каждого этапа ниже — проверяемые сведения или завершённая работа; успешный обход заранее не обещан.

### План действий и ожидаемые результаты

| Шаг | Действие | Ожидаемый проверяемый результат | Решение по результату |
|---|---|---|---|
| 0. Зафиксировать helper | Сверить полную исходную конфигурацию по матрице выше; в каждом опыте оставить helper ON и его STUN-параметры прежними | Отдельно подтверждены перехват, STUN-helper и GUI-кандидат; ручное восстановление после ребута не смешано с испытанием | При OFF или расхождении остановиться до трафика; записать восстановление отдельно |
| 1. Подготовить сбор данных | Дополнить существующий runner RTC-логом, ICMP, строгими проверками профиля и завершения | Проверенный через GitHub/CI инструмент; одна команда даёт один полный приватный архив и отдельный результат восстановления | При неполном сборе исправляем инструмент; сетевую гипотезу не объявляем неудачной |
| 2. Зафиксировать серию | Снять текущую конфигурацию, проверить семантику `ip_ttl`, записать кандидат и конечный список значений | Манифест с неизменными параметрами A2, ожидаемыми WAN TTL и точным возвратом к исходной конфигурации | Неизвестное положение DPI остаётся неизвестным; доступ к `.80.1` не нужен |
| 3. Проверить значения | По одному свежему 15-секундному запуску на значение; после каждого разобрать архив | Для каждого значения: корректность оригинала/фейков, судьба наблюдаемых ICMP/UDP, состояние каждого клиента | На первом принятом reflector-ответе прекращаем широкий перебор и разбираем следующий этап соединения; без ответов заканчиваем ограниченную серию |
| 4. Подтвердить успех | Повторить одинаковый кандидат на свежих потоках и сравнить его действие включённым/выключенным | Три успешных запуска кандидата и отдельное сравнение без него; повторяемость отделена от причинности | При сбое разбираем расхождение; при успехе без кандидата не приписываем восстановление его действию |
| 5. Проверить реальный звонок | Один контролируемый удалённый Windows/Android тест после повторяемого Docker-успеха | Сначала установление соединения через `.1.2` с подтверждённым двусторонним UDP, затем слышимая речь в обе стороны | Неустановившийся реальный звонок открывает разбор его конкретного endpoint/ICE/профиля; лабораторный результат не объявляется универсальным |
| 6. Сохранить рабочее решение | После обоих голосовых этапов реализовать UDP-only управление и отдельно проверить лабораторное восстановление | Проверенная стратегия, постоянная настройка GUI и управляемые правила; результаты перезагрузки записаны отдельно | Текущий временный `/var/run` marker и успешный ручной запуск не считаются постоянной настройкой |

### 1. Подготовка runner

Изменяется тот же [независимый одноразовый runner](../../tools/telegram-voice-lab/run-a1-opnsense.sh), а не плагин. Сохраняются проверенный SSH, существующий ручной route guard, Docker host, закреплённый бинарник, один свежий CLI-процесс на опыт, ограниченная длительность и один приватный архив. Пользователю не нужны вход на TNAS, несколько окон захвата или правка скрипта на маршрутизаторе.

Требуемые дополнения до сетевой серии:

- Передавать поддерживаемый CLI `--log-file` с уникальным путём в существующем results mount и включать RTC в архив. Неполный/отсутствующий лог помечать явно, сохраняя stdout/stderr, код CLI и PCAP; отсутствие лога не стирает измеренную отправку или ответ.
- Сохранять полные endpoint-scoped IP-захваты, включая не первые фрагменты. Добавить ограниченный адресами лаборатории и окном опыта сбор ICMP Time Exceeded/Destination Unreachable. Коррелировать процитированный внутренний пакет по адресу, протоколу, tuple, длинам и ID, насколько позволяет ICMP. Один IP ID недостаточен: A2 повторял его у фейков и оригинала. Не ограничивать ICMP только внешним IP рефлектора.
- Отдельно учитывать, что ICMP может цитировать фейк, оригинал или неидентифицированный пакет. Он не доказывает положение DPI; отсутствие ICMP не означает отсутствие истечения TTL. Если RTC показывает ошибку сокета после ICMP, исследовать эту последовательность, не приписывать её автоматически блокировке.
- Записывать dvtws2/Lua/helper-source identity, полное неизменное STUN-helper действие, сохранённый и реально активный GUI-кандидат, Voice/IPFW/PFIL, маршрут и фактические WAN TTL/checksum. Проверять [полную исходную конфигурацию до и после](#telegram_voice-controls-for-every-trial), включая точный IPSET и семантику правил. Требовать согласованный единственный **полный** кандидат в saved/effective, без лишних действий и конкурирующего перекрывающего профиля. В текущем v4 диагностические saved-флаги и наличие ожидаемой строки ещё не обеспечивают весь этот контракт; автоматически включать helper при ошибке нельзя.
- Подтверждать завершение именно созданного удалённого CLI-процесса при штатном окончании, таймауте и обрыве SSH. Завершение локального SSH/`docker exec` не считать само по себе доказательством завершения процесса внутри контейнера. Не останавливать чужие процессы или изначально работающий контейнер.
- Проверять финальное семантическое состояние ресурсов, которыми владеет запуск: capture PID, удалённый процесс, исходное состояние контейнера. Для профиля отдельно фиксировать состояние до/после и предусмотренный возврат; GUI Apply кандидата не является автоматической функцией текущего runner. Не скрывать проблему восстановления за успешной упаковкой архива.

Проверки на фикстурах/моках должны покрыть RTC, ICMP с другим внешним адресом, отличие фейка от оригинала по цитате, saved/effective mismatch, лишнее действие, неполный архив, таймаут/обрыв и cleanup. После PR/CI/merge — одна версия для владельца с csh-совместимой командой. CI подтверждает инструмент, но не сетевой обход. **Эти изменения ещё не реализованы.**

### 2. Манифест и бюджет TTL-серии

Неизменны: `91.108.13.10:596`; текущий SHA-256 бинарника и engine 13; TNAS `/32 via 192.168.1.2`; тот же WAN/провайдер; helper ON и Telegram IPSET; область профиля/`unknown`; zero16 с правильной checksum; repeats=2; пересылка оригинала; NAT/PFIL; остальные стратегии и рабочий TCP-parent. Не менять одновременно engine, payload, repeats, фрагментацию, endpoint или TCP.

До GUI Apply сохранить точный полный исходный профиль и процедуру его восстановления. Проверить установленную реализацию `fake:...:ip_ttl=N`, а затем в каждом опыте — **измеренный** WAN TTL фейка и неизменный нормальный TTL оригинала. Значение аргумента и значение на WAN не объявляются одинаковыми без проверки пути отправки.

**Рабочий бюджет первой серии: не более четырёх разных TTL, по одному 15-секундному запуску на значение.** Это предел исследовательской серии, а не доказательство, что четыре значения покроют неизвестный диапазон. Конкретные значения, порядок, ожидаемые WAN TTL и предел ожидания записать в отдельный манифест кандидата после проверки исходников и доступных сведений о пути. Если трассировка не отвечает, это не бесконечный блокер: выбор явно маркируется исследовательским, без утверждения «фейк дошёл за DPI». Двоичный поиск и автоматическое увеличение TTL до успеха не обоснованы.

Новому кандидату нужен отдельный selector/ID и проверенный вариант без экспериментального действия для контрольного сравнения. Текущий v4 принимает только A1/A2; запускать TTL под видом A2 нельзя. Синтаксис кандидата, контрольного варианта, значения и stop/restore должны быть записаны и проверены до передачи команды владельцу. **Числовой TTL этой документацией не выбран.**

### 3. Разбор каждого опыта и остановка

Каждый опыт — новый процесс, свежие peer/session tags и фактически проверенные LAN/NAT tuples. Один запуск — один архив; следующий опыт выбирается после его разбора. Нет фонового sweep и человеческого звонка на каждое значение.

| Наблюдение | Вывод | Следующее действие |
|---|---|---|
| Неверный маршрут/профиль, неправильный фактический TTL, повреждённый оригинал или неполное восстановление | Ошибка подготовки, формирования пакетов или восстановления; не отрицательный тест DPI | Остановиться и исправить конкретную границу; повтор испорченного опыта учитывать отдельно от новых значений |
| На WAN видны нужные фейки/оригиналы, ответа нет | `WIRE_OK / NO_REPLY_UNKNOWN` для этого значения, endpoint и времени | Разобрать ICMP/RTC и перейти к следующему записанному значению либо завершить бюджет; точка потери неизвестна |
| Ответ есть на WAN, но отсутствует на LAN/в сокете | Появился наблюдаемый разрыв обратной локальной доставки | Проверить именно этот NAT/PF/IPFW/маршрут/сокет по синхронным данным; перестать перебирать TTL |
| Пакет дошёл до клиента, но отвергнут проверкой адреса/tag/формата | Входящий UDP ещё не `REFLECTOR_READY` | Разобрать причину отказа текущей библиотеки и актуальность сессии |
| Библиотека приняла ответ | `REFLECTOR_READY` для конкретного участника, ещё не медиа | Остановить широкий TTL-перебор; проверить готовность второго участника, ICE/DTLS и последующий UDP |
| Оба Established, но нет устойчивого двустороннего обмена или полного наблюдения | Соединение продвинулось, `MEDIA_PASS` не доказан | Сохранить частичный успех и выбрать один тест следующей стадии; не возвращаться к широкому TTL-поиску |
| Оба Established, stats/BWE обоих, exit=0 и устойчивый коррелированный UDP через WAN | Предварительный `MEDIA_PASS` | Перейти к воспроизводимости |

Для этой серии устойчивость проверять по общему интервалу **не менее пяти секунд**, когда оба участника Established и продолжается двусторонний UDP после начального handshake. Единичные служебные ответы, наличие BWE или общая строка CLI «Call established» недостаточны. Если первое соединение возникло слишком поздно для такого окна, результат неполный; допустим **один отдельный 30-секундный повтор того же кандидата**, помеченный изменённой длительностью, без изменения других параметров. Это не доказательство слышимого звука: renderer CLI отбрасывает аудио.

Числа 60 Hello / 120 фейков относятся к старым 15-секундным сериям **без ответов**. После готовности рефлектора характер и число пакетов меняются; не требовать прежних суммарных чисел как условия успеха. Проверять две fake-копии на каждую действительно выбранную профилем датаграмму и отдельно последующий двусторонний обмен.

### 4. Повторяемость и реальный звонок

После первого полного `MEDIA_PASS` — минимальная последовательность **кандидат ON → действие кандидата OFF → ON → ON**, считая первый успешный запуск первым ON. Нужны **три успешных свежих ON-запуска с одинаковыми параметрами**; все четыре запуска сопровождаются теми же измерениями. Если длительность была изменена до 30 секунд, серия повторяемости начинается с первого полного результата на этой длительности. При первом неуспехе повторяемость не доказана: остановиться и разобрать отличие, не продолжать до удобных «трёх побед» с отбрасыванием неудач.

**OFF означает выключение только экспериментального действия. Voice-helper, перехват UDP, IPSET, маршруты и TCP-parent остаются прежними.** Helper целиком не выключать: это меняло бы две переменные. Контрольный вариант и восстановление подготовить до сравнения. Если OFF тоже работает, зафиксировать текущую доступность пути и не объявлять причинный эффект стратегии. Даже ON/OFF/ON — ограниченное наблюдение во времени, а не доказательство устройства DPI.

После повторяемого Docker-успеха — один ограниченный реальный Windows/Android звонок, удалённый участник и P2P OFF. Проверить маршрут до **реально выбранных приложением** адресов через `.1.2`, совпадение области стратегии, TCP-parent и синхронные LAN/WAN + клиентский лог. Сначала соединение и двусторонний UDP, затем речь в обе стороны; качество звука не ставится впереди решения проблемы соединения. Реальный клиент может выбрать другой endpoint/порт/engine; Docker-успех на UDP/596 не означает, что профиль 596–599 покрывает весь Telegram Voice.

Если реальный звонок не установился, сравнить его конкретный endpoint, выбор профиля и этап ICE с успешной лабораторией. Новое различие — отдельный документированный опыт, а не основание менять сразу все настройки. Только установленный реальный UDP-звонок с речью закрывает `CALL_PASS`; звук с неустановленным транспортом остаётся отдельным наблюдением.

### 5. Если вся ограниченная серия осталась без ответа

Опубликовать сводку значений, WAN TTL, сохранности оригиналов, ICMP/RTC, состояния обоих клиентов и приватных хешей. Восстановить зафиксированную исходную конфигурацию, проверить её; не оставлять последний непроверенный кандидат «рабочим». Это завершение конкретной серии с `NO_REPLY_UNKNOWN`, не вывод о невозможности любого обхода.

Следующая развилка определяется данными, до нового запуска:

- При локальной потере/ошибке библиотеки исследовать её, а не менять fake-параметры.
- При полном отсутствии обратных данных проверить актуальность выбранного рефлектора по первичному источнику и соответствие текущему клиенту. Публикация адреса в списке Telegram сама по себе не доказывает его доступность. Другой endpoint или engine — отдельная новая серия с собственной исходной проверкой на **том же OPNsense/провайдере**, без смешивания с TTL.
- Только после такого разбора выбрать один следующий механизм с конкретным основанием из источника/пакетов и ожидаемым наблюдаемым отличием от уже закрытых экспериментов. Сейчас «следующая выигрышная стратегия» не назначена.

Независимый рабочий путь к тому же endpoint может помочь причинному сравнению, **если он отдельно доступен**, но не является обязательным этапом. Не возвращать `192.168.1.140`, не требовать доступ к чужому `.80.1`, не переводить задачу на новый VPN/провайдера. Последующие интеграция UDP в плагин и лабораторная перезагрузочная приёмка идут по [roadmap](../ROADMAP.md); никаких boot-изменений этот план не устанавливает.

## Completed baseline and A1/A2 history

- Qualified pinned TNAS host-network Docker companion: `tgvoice-lab`; `/results/tgcalls_cli`; upstream source `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; qualified binary SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; caller/callee engines 13.0.0. The *local five-second P2P smoke gate passed*, verifying the binary, **not** remote reflector access.
- Current **pinned reflector epoch**: `91.108.13.10:596`, **15 seconds**, fresh `--mode reflector` per trial with both test peers within the qualified harness; TNAS host `192.168.1.100` on Docker `host`, selected **specific `91.108.13.10/32` TNAS host route via OPNsense `192.168.1.2`**, OPNsense WAN `vtnet1`, upstream `192.168.80.1`. An operator-tested independent SSH port-9222 connection and **manual** guarded TNAS-route script already exist. Docker/container and route recovery remain **manual-only** after TNAS reboot, by owner decision.
- Real-client October 2: one earlier audible successful real call had unproven media transport. Seven later deliberately OPNsense-gateway real calls failed media setup: 345 unchanged **40-byte non-STUN Reflector Hellos** + 45 STUN originals, all 390 NAT-forwarded on WAN, 90 additional zero16 STUN fakes, **no Telegram UDP replies** in seven captures. All **480** observed outbound WAN UDP datagrams had valid recorded IPv4/UDP checksums (unfragmented). A subsequent distinct Telegram Desktop WebRTC log received remote signaling/ICE candidates but timed out after ~20 seconds without a usable ICE/media connection. Do not convert these into an unfounded "Zapret2 does not work" verdict.
- Current temporary `telegram_voice_enable` prepends a **STUN-only** `--filter-l7=stun --payload=stun` fake profile and adds the **essential all-UDP-to-Telegram-IPSET** IPFW rule; it **does not transform** the identified non-STUN 40-byte Reflector Hello. GUI and helper share **one dvtws2**, not double encryption. The current IPFW outgoing hook was previously observed **before PF**; re-read actual `pfilctl heads` on a later boot.
- **Already completed; don't blindly retest:** unmodified current reflector baseline; ordered UDP-position-8 fragments; reverse position 8/16/24/32; fakefrag8 + reverse24; fakefrag8 + original (lost originals locally); and tee where original preceded fake. Their detailed `WIRE_OK / NO_REPLY_UNKNOWN` or local failure and restoration outcomes are preserved in existing [oracle architecture](TELEGRAM_VOICE_EMULATION_LAB.md) and [October 1 measured evidence](../verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md). A1 is **not** a claim that this old, complete fragmentation sweep is untested.
- The historical September 5 `MEDIA_PASS` used the **retired** `192.168.1.140` path and older testing epoch; do not silently reuse it as a current working control. The owner's September 22 positive-call report remains historically documented without verified attribution to the claimed fragment strategy.

**Historical first preflight (October 2, owner 16:17:38Z trial; since resolved): A1 was NOT present in the effective runtime, regardless of earlier reported GUI Apply.** The previous standalone one-command script successfully invoked the existing two-route guard, checked Voice ON/table14 and current PFIL, then returned **`PREFLIGHT_FAIL` before Docker**. Archived `runtime-v2/traffic.conf` contained **only STUN helper plus existing normal profiles**; ordinary IPFW UDP rule19002 lacked `596–599`. Its archive does not reveal whether A1 was saved in GUI but not activated or was never persisted. **Do not treat this preflight as an A1 network rejection and do not blindly change network/PFIL or add another candidate.** [Exact private-archive source evidence](../verification/evidence/2026-10-02-docker-a1-preflight-absent-effective-profile.md). The tracked single-command script now includes safe read-only persistence-vs-effective classification and emits one archive even on rejection, with no raw `/conf/config.xml` disclosure. Only when A1 is proven active will the first actual Docker A1 test begin.

**Second owner-verified preflight supersedes uncertainty about saved state:** V2 pinned one-command runner successfully read saved GUI Strategy on **2026-10-02 19:08:19 UTC**. All of A1's port/payload/fake markers are **NO**, while the Telegram IPSET marker is YES due to pre-existing profiles. Effective A1 and numeric UDP/596–599 IPFW rule are also absent. It correctly returned `A1_NOT_IN_SAVED_GUI` **before running Docker**. The root *state boundary* is now established as saved GUI, not failed runtime normalization or an ineffective UDP desync. *Why* a prior GUI Apply did not persist A1 is not established. [Private-source second-run evidence](../verification/evidence/2026-10-02-docker-a1-second-preflight-saved-gui-absent.md). Correct only the persistent ordinary GUI Strategy field, confirm Apply success, then rerun **the existing** installed one-command script. No new profile, runner, proxy changes or human calls until A1 actually gets a Docker wire/media observation.

**2026-10-03 third preflight advances A1 activation to measured PASS:** owner saved GUI A1, effective single-block A1 and ordinary UDP/596–599 capture rule are now all verified; Voice remains ON/table14 and original selective TNAS SSH route script reports both target host routes via OPNsense. **The fixed Docker test still has not run**: the existing v2 one-command runner's additional Linux `ip route get ... from` check incorrectly insisted on a `src` token even though the valid Linux reply uses `from`. [Exact third-archive evidence](../verification/evidence/2026-10-03-docker-a1-preflight-linux-route-from-mismatch.md). Amend the existing script (not GUI strategy or routes) to independently check assigned source NIC and the required `via`/`dev` path; regress both valid Linux output styles plus safety failures. After exact-head CI/merge, owner replaces only runner and obtains the **first genuine 15-second Docker A1 result**. Stop all further unsolicited GUI Apply, TCP/proxy adjustments, extra experimental strategy or human calls until the genuine A1 wire/media evidence exists.

**October 3 first actual A1 Docker run supersedes earlier preflight status:** preflight now PASS, fixed TNAS Docker reflector ran 15 seconds. Both CLI peers stayed Reconnecting, BWE zero, exit 1. Correlated **60** genuine LAN Hello -> byte-identical original NATed WAN, **120** WAN zero16 fake packets with *intentionally invalid* UDP checksums, all **60** triplets serialized **[fake, fake, original]** with valid IPv4 header checksums and valid original UDP checksums. **Zero replies from pinned target** on LAN/WAN; no tcpdump drops. Voice IPFW19000 +60/+4080 and ordinary19002 0 as expected due earlier destination-scoped interception. **A1 `WIRE_OK / NO_REPLY_UNKNOWN`; MEDIA_PASS still OPEN.** [Dated full source-grounded evidence](../verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md). **Do not schedule the unchanged A1 again or ask for real human calls.** The *next untested one-factor hypothesis* is A2 = same 16-zero two-repeat fake but **without `:badsum`**, testing valid-UDP-checksum fakes. Current one-command runner has a literal exact-A1 guard, so first document/CI-qualify explicit candidate-aware safeguards and a single-command A2 workflow **before** requesting a GUI A1→A2 Apply. This does not establish a uniquely responsible ISP/remote drop cause.

## Historical HELLO-FAKE-A1 design — subsequently applied and tested

The owner **reports that the following block has been added and Applied in the ordinary OPNsense GUI Strategy**. **Only GUI Apply is reported**; exact generated active profile and IPFW rules have not yet been re-measured at this new epoch.

```text
--filter-l3=ipv4
--filter-udp=596-599
<IPSET:telegram>
--payload=unknown
--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2

--new
```

**Only hypothesis to test:** the pinned Docker reflector's **non-STUN 40-byte Hello to UDP/596** will be classified/matched as `unknown` by the *actual installed* dvtws2, and this GUI profile will cause **two additional bad-checksum zero16 UDP fakes before/around each otherwise unmodified genuine Hello**. Check the actual order in the capture; it is **not yet observed** that the fake precedes the original or that `badsum` survives WAN PF/NAT. A local configuration/capture mismatch is `PROFILE_NOT_SELECTED` or `WIRE_FAIL` and must be fixed **before** any provider efficacy interpretation.

**Non-duplication / interception:** the temporary Voice helper remains ON for this first diagnostic epoch **only for its known destination-IP-scoped IPFW interception** and existing STUN profile. In the one active dvtws2 process, A1 should match non-STUN Hello while the helper's earlier profile addresses recognized STUN. The new ordinary GUI UDP port extractor also adds `596-599` to *common* outgoing WAN IPFW capture for **all destinations** on these ports, while the dvtws2 profile itself has the resolved Telegram IPSET. Keep this extra common-port capture exposure **bounded to the laboratory trial**; inspect the actual rules and consider removing the extra capture path from the eventual approved product design, retaining destination-scoped Voice interception. The IPSET must contain `91.108.13.10` (existing GUI includes `91.108.12.0/22`); check generated runtime and selection rather than assuming success.

**Caveat:** this A1 **nonfragmented 16-byte badsum fake before an intact genuine Hello** is a different local-wire hypothesis from the earlier **40-byte fragmented fake8** plus reverse24, but it is still a **fake-packet family test**, not evidence of a new upstream vulnerability. If LAN/WAN capture shows no fakes, re-examine generated config and installed classifier; don't request a real call to determine whether the profile is selected.

## Historical A2 implementation contract — completed single-command comparison

The [first real A1 wire evidence](../verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) **closes unmodified A1 as an unsuccessful media candidate in this pinned epoch**. A2 is explicitly only a checksum-only comparison: `fake:payload=unknown:blob=zero16:repeats=2`, with **no `:badsum`**. Keep all 596–599/Telegram-IPSET profile scope, `unknown` handling, two repeats, original forwarding, current Voice/STUN helper, fixed 15-second Docker oracle, existing owner route script, SSH, NAT/IPFW/PFIL and TCP parent infrastructure **unchanged**.

The source-controlled independent [same one-shot OPNsense runner](../../tools/telegram-voice-lab/run-a1-opnsense.sh) now supports **explicit** `TGVOICE_CANDIDATE=A2` for the new lab epoch (legacy absent variable defaults to A1). A2 must first be *explicitly* selected and saved in the **ordinary persistent GUI Strategy**, by replacing **only** A1's `:badsum` token, never appending a competing second overlapping candidate. Candidate-aware saved-GUI and effective one-block preflight must demand the **exact selected** fake line and reject coexistence of A1/A2 on the same matched profile; if it cannot establish the selected variant, it must stop *before Docker*. The manifest/result archive is labelled `candidate=A2` and `a2-UTC-unique.tgz`. No raw GUI XML, TCP parent config or private SSH material may be published.

**Owner operation after exact-head corrective CI and merge only:** update the **already installed** one-command script from the merged immutable GitHub SHA via already-working Squid `192.168.1.2:3128`; syntax-check and marker-check before replacing, then **one command** `TGVOICE_CANDIDATE=A2 /bin/sh /root/tgvoice-lab/run-a1-opnsense.sh` from OPNsense's default `csh` (the environment assignment is a shell feature: if invoking from csh use `env TGVOICE_CANDIDATE=A2 /bin/sh ...`). Do not ask the owner to log into TNAS, open multiple terminals, run real human calls or edit scripts on the firewall. After the first A2 archive, verify on WAN: expected two **valid UDP-checksum** 16-byte fakes then original per genuine Hello, exact absence of leftover badsum A1 and count/direction of replies; independent caller/callee `MEDIA_PASS` gates still apply. A2 is unmeasured until the owner returns this archive. If A2 fails to activate or the output differs, classify as preflight/wire behavior rather than server/DPI failure.

## A2 completed owner-live — supersedes pending steps above (2026-10-03)

The owner applied exact unique A2 and ran the merged explicit-selector v4 script. Fresh LAN/WAN captures independently proved 60 unmodified genuine WAN Reflector Hellos and **120 correct-UDP-checksum** zero16 A2 fakes in precise 60/60 two-before-one triplets, with **zero incoming pinned-reflector packets**. Both engine-13 peers remained Reconnecting/zero BWE, CLI exit 1. All GUI/runtime/Voice/route/Docker checks passed. [Full measured record](../verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md). A1 had intentionally **bad** fake checksums; A2 had **valid** fake checksums, but neither achieved a reply. This is insufficient to attribute the drop or conclude the remote endpoint is presently reachable.

**Current follow-up:** the [limited-fake-TTL plan](#next-experiment-limited-fake-ttl-planned-not-run) refines the October 3 source-guided-hypothesis boundary. Preserve A2 until the explicitly selected candidate/runner/rollback are ready; no new value or live trial is recorded yet. Same-endpoint independent control remains optional, working TCP stays intact and retired `192.168.1.140` stays retired.

## Existing A1/A2 runner contract — baseline for the planned extension

**Owner correction:** the original multi-console procedure is superseded. The laboratory already has an owner-tested, manually invoked OPNsense **`/root/tgvoice-lab/ensure-tnas-routes.sh`**, a restricted noninteractive SSH identity and trust for `tolian@192.168.1.100:9222`, and a host-network `tgvoice-lab` Docker oracle. Do **not** ask the owner to log into TNAS, manage multiple terminal windows, start tcpdump by hand or place shell heredocs into OPNsense **csh**. This section is the design contract for the separate, lab-only tracked executable [`tools/telegram-voice-lab/run-a1-opnsense.sh`](../../tools/telegram-voice-lab/run-a1-opnsense.sh). The GitHub source is canonical. One **explicit operator-invoked** `/bin/sh /root/tgvoice-lab/run-a1-opnsense.sh` must execute the entire single-candidate trial and produce **one local private `.tgz` archive**.

The runner, invoked **on OPNsense only**, must:

1. Create a unique, private `/root/tgvoice-lab/results/a1-UTC-unique/` work directory, reject concurrent A1 runs, log timestamps and runner revision, and finalize a `.tgz` result even on failure. **Never** include SSH private keys, Squid credentials, general network configuration backups or public call logs.
2. Snapshot/read-only-validate actual Zapret2 status (**inspect output text, not merely `configctl status` exit 0**), requested/effective/active Telegram Voice ON, managed IPSET containing the pinned target, generated **one-block** A1 selection in active `runtime-v2/traffic.conf`, destination-scoped Voice divert rule and A1 common UDP port rule, `pfilctl heads`, effective IPFW counters and normal TCP parent service status read-only. An absent helper or candidate is a **preflight failure archived**, **not** permission to change production GUI strategy/firewall or silently enable the helper.
3. Invoke **the exact existing** OPNsense `/bin/sh /root/tgvoice-lab/ensure-tnas-routes.sh` **once** as part of the operator's explicitly requested run; do not implement another route-repair script or a recurring watch. Preserve its guard and selective restoration of the existing two TNAS `/32` routes. The runner must independently verify through the already-established `/usr/local/bin/ssh`, restricted key and trusted host that the pinned reflector `91.108.13.10/32` actually routes **via `192.168.1.2 dev ovs_eth1 src 192.168.1.100`**.
4. Over the **same SSH link**, use the absolute TNAS Docker path `/Volume1/@apps/DockerEngine/dockerd/bin/docker`. Verify `tgvoice-lab` is Docker host network, the binary's SHA-256 matches qualified `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`, and the image/container is running. An explicit **manual runner execution** may start the *existing* container on demand if stopped; it must remember and restore an initially stopped container afterward. This is **not Docker boot autostart** or a second test harness.
5. From **the same script and before the Docker trial**, start two owned OPNsense tcpdump processes concurrently on `vtnet0` (host `192.168.1.100` and pinned reflector IP) and `vtnet1` (pinned reflector IP), filtering **`ip` rather than UDP-only** to retain non-initial IPv4 fragments. Confirm each owned process is still alive. **Do not kill existing tcpdump processes** or capture all unrelated WAN traffic.
6. Run **one and only one** fresh `docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15` via existing noninteractive SSH. Capture its full stdout/stderr and exact exit code; enforce a bounded failure timeout. **No real Telegram call, no second divert listener, no experimental 990 rule, no PFIL reorder, no Squid/sing-box restart, no automatic loop/repeated candidates.**
7. Automatically stop/wait for **only its two** tcpdump PIDs in all exit paths, collect after-trial Voice status/IPFW/PFIL, source PCAPs, capture process logs, route status and checksums, and produce a **single compressed archive with an exact local path and SHA-256**, reporting success of **data collection separately from `MEDIA_PASS`**. Do not publish raw archives to public GitHub: they contain sensitive network identifiers and packet payloads. The operator only retrieves/sends the one archived file; subsequent forensic analysis and new candidate selection are assistant-owned.
8. If any prerequisite fails, **do not fabricate a failed candidate verdict**: archive the preflight, emit clear `PRECHECK_FAILED`, and leave router services/GUI and the initially observed Docker-running state unchanged (apart from the **explicitly requested selective** pre-existing TNAS route repair). On a completed but unsuccessful CLI trial, archive `WIRE_UNVERIFIED / MEDIA_FAIL_OR_UNKNOWN` pending PCAP and peer-state analysis; do not conflate runner exit success with media success.

All actual appliance values must be measured at each trial; historical `ipfw 19000` and historical IPFW→PF hook order are evidence, not assumptions. No persistent OPNsense boot work is part of this runner. Any eventual script syntax or integration tests qualify *code*, not a claimed live network result.

### Historical A1 invocation — not the next TTL command

After the script is published, the owner may transfer it once to `/root/tgvoice-lab/run-a1-opnsense.sh` by their preferred method (or fetch its pinned GitHub raw file). **Only one OPNsense csh-safe command launches the entire experiment:**

```sh
/bin/sh /root/tgvoice-lab/run-a1-opnsense.sh
```

The script prints the final private archive path under `/root/tgvoice-lab/results/`. No interactive TNAS login, SSH prompt, extra window or manual PCAP management is required. On any preflight failure the owner simply supplies that **same** archive; the assistant investigates before scheduling another attempt.

## Result gates, next decision and limits

| Measured evidence | Honest status | Next action |
|---|---|---|
| A1 absent or `unknown` profile does not match 40-byte Hello; no A1 fake on WAN | `PROFILE_NOT_SELECTED` / `WIRE_FAIL` | Fix exact classifier/profile or unintended profile precedence **in the Docker lab**, after documenting. No real call. |
| Correct 16-byte zero fakes and original Hello visible, checksums/order verified; no valid reflector response | `WIRE_OK / NO_REPLY_UNKNOWN` | Retain WAN transformation and exact CLI negative outcome. Do **not** increase repeats or repeat identical A1 endlessly; select one **new** source-justified single-variable hypothesis, and record differences from completed fakefrag/fragment work before another test. |
| Valid reflector response received and qualified client accepts it | `REFLECTOR_READY` | Verify both peers' ICE state, stats/BWE and exit; **a single reply alone is not MEDIA_PASS**. |
| Both peers Established, non-zero BWE/stats on both, complete bilateral UDP and `tgcalls_exit=0` | provisional `MEDIA_PASS` | Repeat a fresh independent Docker process using the same exact selected candidate and fixed reflector. Only *repeated* MEDIA_PASS opens the real-user CALL_PASS gate. |
| No control-proven endpoint reply across all candidates, despite WIRE_OK | `NO_REPLY_UNKNOWN` (not proven strategy/provider cause) | Record ambiguity and choose one targeted new hypothesis or obtain a recent same-endpoint working-path control for *causal attribution*, without requiring live human calls for every candidate. |

**One-factor discipline:** do not mix helper OFF/ON, STUN repeats, GUI fake blob/badsum, fragment order, PFIL hook order, NAT, endpoint and binary changes in the same comparison. Every new epoch keeps the measured helper/interception state and known TCP paths fixed; candidate-action controls do not disable the helper. No real calls, no TCPSquid debugging and no recurring Cron before the Docker oracle shows a promising repeatable outcome.

**References:** [canonical Docker oracle and existing closed candidate order](TELEGRAM_VOICE_EMULATION_LAB.md), [TNAS SSH/route and operator-tested manual recovery](TELEGRAM_LAB_OPERATIONS.md), [GUI vs Voice destination capture and PFIL order](TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md), [existing cumulative past results](../verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [seven real-call LAN/WAN failures and checksum findings](../verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md), [subsequent WebRTC ICE timeout](../verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md).
