# Native Voice — лаборатория TNAS / OPNsense

**Текущий рубеж, 20.10.2026:** на установленном `0.5.5_7`/engine `v1.0.5.2` **TTL7 selective fake WAN PASS**, без UDP RX и без звонка. Стратегия #4 восстановлена. **Source contract Hello/response подтверждён на `tgcalls@efd330c`**: Hello 40 байт, входящий ответ только с выбранного IP:port, первые 12 байт peer tag совпадают; это условие перехода `ReflectorPort` в `READY`, не гарантия MEDIA. Текущий список Telegram-серверов из среды ассистента не получен. **Официальный список получен owner-live: 616 записей, `91.108.13.10:596–599` присутствуют. После этого TTL7 повторён и выполнен контроль без TTL7 — оба дали 120 fake / 60 original UDP в WAN, 0 reply, call=no. Исходный ordinary Strategy #4 активен; `zapret` работает. **Текущий независимый контроль через `192.168.1.140` пройден:** один 15s текущего `tgcalls_cli` на том же `91.108.13.10:596` дал Call established=yes, обе стороны Established, BWE nonzero, CLI exit0, маршрут TNAS через OPNsense восстановлен (RESTORE PASS). [Owner-live положительный контроль](../verification/evidence/2026-10-20-tgvoice-gateway-140-positive-control.md). Следующий контроль владельца — `192.168.4.1`, доступный TNAS только via `.1.140`; выяснить топологию read-only до сетевых изменений.** [A/B evidence](../verification/evidence/2026-10-20-telegram-ttl7-vs-no-ttl-control.md). [Protocol evidence](../verification/evidence/2026-10-20-tgcalls-reflector-protocol-readonly.md). [TTL7 evidence](../verification/evidence/2026-10-20-telegram-ttl7-wan-owner-live.md). A1/A2/A3a уже завершены; не повторять их без нового основания.

**Текущий новый owner-live факт (20.10.2026):** GOST OpenWrt `auto :1070?udp=true` подтвердил SOCKS5 UDP ASSOCIATE и на `eth2 Out` **6×UDP64 + 1×STUN20** после отправки через SOCKS5 (но `STUN_RESPONSE=TIMEOUT`). Два дополнительных ограниченных pinned 15s `tgcalls_cli` через OPNsense `.1.2` и прямым маршрутом через OpenWrt `.1.236` оба `Reconnecting`/call=no/BWE=no/exit1; исходный TNAS `91.108.13.10/32 via .1.2 proto dhcp metric 1024` восстановлен `RESTORE=PASS`. Встроенный `tgcalls_cli` отправляет **direct non-STUN UDP и не использует SOCKS5/GOST или HTTP CONNECT**, так что попытка включения Podkop UDP-through-TCP и OPNsense Squid SSLPorts 563 не проверяется этим CLI. Владелец сообщил о переключении Podkop без улучшения, итоговая настройка неизвестна. **Следующий контроль (сначала read-only):** проверить интерфейсы/NAT/route pfSense `.1.140`, затем один guarded `/32` pfSense direct-call с одновременным pfSense LAN+WAN `tcpdump` и наблюдением TCP к `185.203.117.88:33128` — без PF/NAT/proxy changes. [Последние измерения](../verification/evidence/2026-10-20-gost-udp-associate-socks-stun-and-repeated-tgvoice-direct-routes.md).

Этот документ — **актуальная точка входа для тестов Telegram Voice**. Старые [A1/A2 runner](../../tools/telegram-voice-lab/run-a1-opnsense.sh), [PoC/runbook](TELEGRAM_LAB_OPERATIONS.md), [campaign](TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md) и архивы фиксируют прежний эксперимент, но не являются командами запуска нового общего backend: их ожидания `zapret2_tgvoice`, отдельного helper и старого UDP 596–599 устарели. **Не запускать старый runner на работающем native Voice** без перепроверки его preflight и побочных эффектов; не создавать второй divert listener или второй `dvtws2`.

## Доступ и подтверждённая топология

| Компонент | Адрес, доступ или роль | Статус 19.10.2026 |
|---|---|---|
| OPNsense | LAN `192.168.1.2`; WAN `vtnet1`; native общий `dvtws2`/supervisor/IPFW | Установленная `0.5.3_28`: Config Telegram ON, журнал `committed`, runtime `ready` |
| TNAS | `192.168.1.100`, LAN `ovs_eth1` | Доступен по SSH с OPNsense |
| TNAS SSH | `tolian@192.168.1.100`, порт `9222`; клиент OPNsense `/usr/local/bin/ssh`; локальный ключ `/root/.ssh/id_ed25519_tgvoice_lab` | SSH выполнен; warning о non-PQ KEX не помешал соединению |
| Docker Engine | `/Volume1/@apps/DockerEngine/dockerd/bin/docker` на TNAS | `tgvoice-lab` — `true host` (запущен, network=host) |
| Генератор | `/results/tgcalls_cli` внутри контейнера | SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc` |
| Фиксированный endpoint | `91.108.13.10:596` | Маршрут и включение в IPSET подтверждены; **ответ рефлектора НЕ получен** |
| IPFW native Voice | `19000 divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1` | Таблица — 14 CIDR; `91.108.13.10` входит в `91.108.12.0/22` |

Read-only команда `ip -4 route get 91.108.13.10 from 192.168.1.100` на TNAS вернула `via 192.168.1.2 dev ovs_eth1`. Это **зафиксированный маршрут /32 к указанному адресу**, не доказательство маршрутизации всего Telegram или его динамических IP. При следующих загрузках маршрут, интерфейсы, Docker и SSH проверяются снова. Внешний upstream `192.168.80.1` находится вне контроля этой лаборатории. Старый маршрут через `192.168.1.140` не используется и не должен возвращаться.

SSH-предупреждение `connection is not using a post-quantum key exchange algorithm` — предупреждение о криптографическом свойстве SSH-сессии, а не ошибка IPFW, UDP или Voice. Не отключать проверку host key, не копировать приватный ключ и не публиковать логи, содержащие секреты.

## Безопасные read-only проверки готовности

Команды ниже выполнять от root на OPNsense. Интерактивная консоль OPNsense по умолчанию csh: многострочные POSIX-блоки запускать через `/bin/sh`, а не вставлять в csh по частям.

```sh
pkg info -x os-zapret2-restyle
configctl zapret status
configctl zapret voice_lifecycle_inspect
configctl zapret voice_inspect
ipfw -a show 19000
ipfw table zapret2_voice_telegram list
```

```sh
/usr/local/bin/ssh -T -p 9222 \
  -i /root/.ssh/id_ed25519_tgvoice_lab \
  -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes \
  tolian@192.168.1.100 /bin/sh -s <<'TNAS'
ip -4 route get 91.108.13.10 from 192.168.1.100
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
"$DOCKER" inspect -f '{{.State.Running}} {{.HostConfig.NetworkMode}}' tgvoice-lab
"$DOCKER" exec tgvoice-lab sha256sum /results/tgcalls_cli
TNAS
```

**Допуск к испытанию:** `saved_voice_on=true`, `telegram.configured=true`, `engine_verified=true`, `supervisor_verified=true`, `voice_inspect.state=ready`, `committed` journal; таблица существует и содержит endpoint; реальный маршрут TNAS идёт через `192.168.1.2`; Docker host mode, верный SHA бинарника. Проверить один раз перед серией; любое несовпадение означает **не начинать** новый тест, а локализовать конкретный предикат.

## Один 15-секундный reflector smoke test (без мутации сети)

```sh
echo "=== BEFORE ==="
ipfw -a show 19000
/usr/local/bin/ssh -T -p 9222 \
  -i /root/.ssh/id_ed25519_tgvoice_lab \
  -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes \
  tolian@192.168.1.100 /bin/sh -s <<'TNAS'
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
route=$(ip -4 route get 91.108.13.10 from 192.168.1.100) || exit 10
printf '%s\n' "$route"
echo "$route" | grep -q 'via 192.168.1.2 dev ovs_eth1' || exit 11
"$DOCKER" exec tgvoice-lab test -x /results/tgcalls_cli || exit 12
"$DOCKER" exec tgvoice-lab sha256sum /results/tgcalls_cli
command -v timeout >/dev/null 2>&1 || exit 13
timeout -k 5 60 "$DOCKER" exec tgvoice-lab \
  /results/tgcalls_cli --mode reflector \
  --reflector 91.108.13.10:596 --duration 15
rc=$?
echo "TGCALLS_EXIT=$rc"
exit "$rc"
TNAS
echo "=== AFTER ==="
ipfw -a show 19000
configctl zapret voice_inspect
```

Этот `tgcalls_cli --mode reflector` запускает **два клиента Caller/Callee с локальным обменом signaling**, но обе UDP-ветки обращаются к внешнему адресу рефлектора; это не реальный входящий звонок. Команда ничего не меняет в plugin Config, маршрутах, `ipfw` или `dvtws2`. `TGCALLS_EXIT=1` и `Reconnecting` — не PASS медиасессии, даже когда счётчик Voice растёт. После теста проверять, что `configctl zapret status` и `voice_inspect` остаются здоровыми.

**Критичное разделение протоколов:** эта зафиксированная попытка использовала старый reflector/Hello UDP/596; она **не равна STUN-пробе**. Native Telegram args `--filter-udp=* --filter-l7=stun --payload=stun --lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2` может перехватить исходящий пакет через IPFW, но не обязана выбрать STUN-desync действие для non-STUN Hello. Счётчик IPFW подтверждает только попадание в правило, не отправку fake, не ответ сервера и не успешную работу STUN.

## План измерений и критерия перехода

| Этап | Что выполнить | Доказательство / решение |
|---|---|---|
| A0. Read-only baseline | Зафиксировать `pkg`, Config/Voice/journal, pid супервизора, WAN, маршрут, 14 CIDR, container/binary SHA, IPFW до | Состояние `ready/committed`, сервис запущен; без этого **STOP** |
| A1. Рефлектор | Один запуск выше на 15 секунд; IPFW counters до/после, `TGCALLS_EXIT`, Caller/Callee и duration | `IPFW_CAPTURE_PASS` при росте counters; `MEDIA_PASS` только при фактически подтверждённом двустороннем соединении; зафиксированное A1 даёт capture PASS, call FAIL |
| A2. LAN/WAN packet proof | Одновременно наблюдать `tcpdump` на входящем LAN OPNsense и исходящем `vtnet1`, фильтр `host 91.108.13.10 and udp port 596`; сохранять в отдельный временный каталог с ограниченным временем и без публикации секретных PCAP | Разделить LAN TX, WAN TX, WAN RX, возможные extra fake, checksum/TTL и потери по этапам; **не утверждать WAN delivery по IPFW счётчику** |
| A3. Native profile-specific STUN | Подготовить отдельный согласованный STUN-aware генератор/валидный STUN пакет с ожидаемым responder; сопоставить payload с `--filter-l7=stun`, с текущими args и наблюдением `dvtws2` | `STUN_MATCH/TX/RX` по протокольным пакетам и ответам; **Hello не подменяет STUN-тест** |
| A4. Controlled comparator | Если не отвечает рефлектор, отдельно установить достижимость/ожидаемость ответа endpoint, различить сеть, IPv4 NAT, PFIL и сервер; сравнить минимальные строго изолированные кандидаты в лабораторной серии | Только после PCAP и доказанного влияния; изменения маршрутов/PFIL/IPFW/профиля — отдельный разрешённый тест, с plan/rollback и доказанным возвратом |
| A5. Telegram client acceptance | После промежуточного сетевого успеха: реальный Telegram Windows/Android, контролируемые P2P и proxy условия, лог реального endpoint, двустороннее аудио | `CALL_PASS` только если звонок установлен и обе стороны слышат друг друга; manual test — финальный этап, не нужен для каждого A1/A2 |

Сбор PCAP следует начинать **без изменения правил IPFW, PFIL, NAT, squid/sing-box или уже работающего single `dvtws2`**. Для будущего A2 не предполагать постоянную готовность `tcpdump`/владение `ovs_eth1` OPNsense; сначала проверить актуальные интерфейсы. Не публиковать без необходимости полный PCAP или токены/персональные данные звонков. Исторические гипотезы limited fake TTL, checksum и post-NAT IPFW/PF order находятся в [campaign](TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md) и [research](../research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md), **не применяются автоматически**.

## Текущая точка возобновления

A0/A1 завершены ранее; после обновления до `0.5.5_1` владелец повторно подтвердил здоровый native runtime без конфигурационных изменений. **A2 на `0.5.5_1` выполнен:** LAN `vtnet0` и WAN `vtnet1` PCAP по `91.108.13.10:596` содержат по 180 строк; правило 19000 выросло на 60 packets / 4080 bytes. В выведенной части WAN виден `16,16,40` byte UDP payload pattern, TTL 63, `udp sum ok`, внешних ответов в выведенных фрагментах нет, клиент `Reconnecting`. [Источник с границами вывода](../verification/evidence/2026-10-19-native-voice-a2-lan-wan-capture.md).

**Последующее owner-live чтение сохранённого PCAP (A2):** LAN 6 источников вида адрес:порт ×30, WAN 60 оригинальных UDP 40 байт +120 полностью нулевых UDP 16 байт, **0 входящих ответов** на WAN/LAN. В оригинальном Reflector Hello на смещении 4 нет `0x2112a442` (STUN Magic Cookie, RFC 8489), значит это не валидная STUN-проба. Фейки соответствуют zero16 repeats2, но их принадлежность native STUN или обычным Strategy пока не установлена. [Полное evidence](../verification/evidence/2026-10-19-native-voice-a2-lan-wan-capture.md).

**Селекторы проверены владельцем:** `traffic.conf` native профиль №1 `voice-telegram` принимает только `stun/stun` на любых UDP-портах в Telegram IPSET; обычный профиль №4 принимает `unknown` на UDP `596-599`, с двумя zero16 fake. Именно №4 подходит под A2 Reflector Hello. A2 **не испытывал native STUN**, что не является дефектом STUN-профиля.

**A3a выполнен 19.10.2026 на `0.5.5_1`:** один корректный STUN20 из TNAS `192.168.1.100` на `91.108.13.10:3478` (в Telegram IPSET, вне ordinary профиля №4) породил два полностью нулевых 16-byte fake и оригинальный 20-byte STUN; все три на WAN с TTL 63 и `udp sum ok`, `SSH_EXIT=0`; ответа сокету в течение 2 с не было. **Native Voice STUN outbound/fake PASS**, responder на `:3478` неизвестен, STUN_RX и звонок OPEN. [A3a evidence](../verification/evidence/2026-10-19-native-voice-a3a-stun-outbound.md).

**ICMP traceroute после A3a выполнена:** TTL-limited ICMP пробы с OPNsense `vtnet1` подтвердили ответ `91.108.13.10` на hop 12; видимы hops 1–3, 5–7, остальные не отвечали. Не делать выводов о позиции DPI или UDP/596. [Полный hop trace/TTL7 manifest](../verification/evidence/2026-10-19-reflector-hop-trace-ttl7-first-candidate.md).

**Приостановлено (19.10.2026):** ранее предложенный TTL7 для ordinary Strategy №4 не дошёл до live runtime и вызвал в GUI `Результат применения неизвестен`. Root Config и active runtime сохранили прежний профиль без `:ip_ttl=7`. **Не вводить `pktmod:ip_ttl=7` как замену**: `pktmod` изменяет текущий реальный пакет, а эксперимент касается только fake. Upstream `fake` допускает параметр `ip_ttl`, но факт принятия конкретной команды в установленном dvtws2 и stage validator ещё не проверен. Точная первопричина отказа GUI не установлена. Следующий шаг read-only уточнить installed Lua contract/rejection, без Save/Apply, firewall изменений, Docker reflector и прежних A0–A3a.

**19.10.2026 — TTL7 GUI Apply BLOCKED (без сетевого опыта):** владелец попытался заменить `fake ... repeats=2` на `...:ip_ttl=7` **в обычном поле «Стратегии»**; GUI ответил `Результат применения неизвестен`. Последующее root **read-only** наблюдение: journal phase `committed`, `page=voice`, changed_fields `voice.telegram.enabled` (без новой committed Strategies-операции); `/conf/config.xml` Strategy `SAVED_OLD_EXACT=1`, `SAVED_TTL7_EXACT=0`, active `runtime-v2/traffic.conf` `ACTIVE_OLD_EXACT=1`, `ACTIVE_TTL7_EXACT=0`; `SPLIT_LUA=false` в обоих **сохранённых** текстах, service `running`; `/var/run/zapret2-execution.status` по-прежнему `8|8|ready|ok|2026-10-19T15:34:03+0300|release build is ready`. **Новый сетевой тест с TTL7 не проводился и не разрешён до выяснения причины Apply.** Скриншот прежнего Voice `Telegram Parameters` с `fake:payload=unknown` относится к другой странице и запрещён штатным STUN валидатором, его не следует изменять. Точная исходная причина сбоя Strategies Apply пока неизвестна. В установленном PHP `SettingsController::applyAction` не различает returned `preflight-rejected=...` и послеоперационную неопределённость, а catch `Throwable` может маркировать и pre-dispatch отказ как requires_review. **Следующая точка:** посмотреть только последние приватные `shared-work` кандидат-артефакты (наличие, флаги без XML секретов) и сообщения об ошибках в configd/PHP логах, **не повторяя Apply**, затем исправить конкретный blocker/диагностику кода, если подтверждён.

**Обновление 20.10.2026 (новее приведённой выше истории блокировки):** после успешного Strategies Apply в `_7` тест TTL7 выполнен, wire proof подтверждён, Strategy #4 восстановлена; ни одного входящего UDP/596 ответа и ни одного соединения. [Подробный протокол](../verification/evidence/2026-10-20-telegram-ttl7-wan-owner-live.md). Пока не установлен протокольный контракт и рабочий responder для целевого Hello, следующий опыт не запускать; TTL sweep и изменение Voice STUN №1 не являются текущей задачей.
