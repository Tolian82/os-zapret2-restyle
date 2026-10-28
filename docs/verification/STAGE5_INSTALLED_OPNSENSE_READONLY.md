# Stage 5 — установленная OPNsense: безопасный сбор фактов

**Статус: installed acceptance OPEN.** Точный следующий кандидат: `v0.6.1_7` (`VERSION=0.6.1`, `PLUGIN_REVISION=7`, публикация выполнена, запуск на OPNsense владельца ещё не подтверждён). Предыдущий тестовый `v0.6.1_5` опубликован, но на OPNsense владельца **FAILED POST-INSTALL (69)** при загрузке старого native common Config. `_6` был установлен владельцем, но POST-INSTALL вернул Error 70 при восстановлении старого sealed runtime. Для следующей проверки использовать только [отдельный `_7` пакет](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.1_7/os-zapret2-restyle-0.6.1_7.pkg) (SHA-256 `0bb234363e7b3a518ca997c0249ec73b3973b49ab64ca418bd62c49190514a50`); успешное восстановление службы ещё не подтверждено. Последний стабильный `v0.6.0_1` **не может** подтвердить новую Stage 5.

## Что уже реализовано и чего этот инструмент не делает

В установленном плагине уже существует один штатный независимый `voice_live_inspect.py`: он проверяет сохранённый committed common-owner, настоящий процесс `dvtws2`, supervisor, sealed runtime, правила IPFW, таблицы и счётчики IPFW. Не нужен новый параллельный владелец конфигурации, правил или статуса.

`scripts/stage5-installed-evidence.py` — только тонкий **read-only** мост к существующему инспектору. Действие `collect` проверяет реальную установленную версию через `pkg query`, вызывает штатный инспектор и отдаёт его JSON. Действие `compare` сравнивает два JSON-снимка: ту же идентичность Config, те же owned rules/tables, те же Voice-сервисы и изменения счётчиков. Оно отвергает чужую/нестабильную конфигурацию и не выдаёт PASS для отсутствующих счётчиков.

**Запрещённые действия отсутствуют**: нет `ipfw add/delete/flush`, `Apply`, `service start/stop`, `Config::save()`, открытия сокета divert или изменения FD9. Снимки хранятся только в выбранных оператором временных файлах. Даже увеличение счётчиков **не различает IPv4 и IPv6** и не доказывает STUN response, Telegram call либо результат обработки `dvtws2`.

## Запуск только после фактической установки исправленного кандидата `0.6.1_7`

Последовательно выполнить в **root `csh`** на контрольной OPNsense. Важное условие — [тестовая версия `0.6.1_7`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.1_7/os-zapret2-restyle-0.6.1_7.pkg) опубликована отдельно от ошибочных `_5`/`_6`; использовать только проверенный файл из этого prerelease, с резервной копией конфигурации и сверкой SHA-256. После установки сначала подтвердить штатный запуск службы, без ручного вмешательства в IPFW. Если её нет — тест остановить, а не тестировать стабильный `v0.6.0`.

1. Проверить точную идентичность установленного пакета:

   ```sh
   pkg query '%v' os-zapret2-restyle
   ```

   Продолжать **только если результат `0.6.1_7`**.

2. Проверить штатное состояние существующей службы:

   ```sh
   /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status
   ```

3. Получить утилиту **из того же GitHub main после объединения её PR**. Код сначала можно просмотреть на GitHub; загрузка пишет только временный файл, не настройки OPNsense:

   ```sh
   /usr/bin/fetch -o /tmp/zapret-stage5-evidence.py https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/stage5-installed-evidence.py
   ```

4. Снять исходное состояние, не касаясь правил или Config:

   ```sh
   /usr/local/bin/python3.13 /tmp/zapret-stage5-evidence.py collect > /tmp/zapret-stage5-before.json
   ```

5. На контролируемом реальном устройстве выполнить IPv6 Voice/STUN-сеанс с назначением **в уже настроенном Voice IPSET** и соответствующим UDP-диапазоном. Не изменять IPFW ради этого теста; одновременно фиксировать реальное семейство назначения и результат сеанса независимо от счётчиков IPFW. При отсутствии IPv6 WAN или релевантного IPv6 назначения отметить тест `UNAVAILABLE`, не имитировать IPv6 через IPv4.

6. Снять состояние после трафика:

   ```sh
   /usr/local/bin/python3.13 /tmp/zapret-stage5-evidence.py collect > /tmp/zapret-stage5-after.json
   ```

7. Получить отчёт по неизменности owner/счётчиков:

   ```sh
   /usr/local/bin/python3.13 /tmp/zapret-stage5-evidence.py compare /tmp/zapret-stage5-before.json /tmp/zapret-stage5-after.json
   ```

Результат всегда обозначен `READ_ONLY_OBSERVATION`, `stage5_installed_acceptance=OPEN`, `ipv6_packet_proven=false`. `COUNTERS_INCREASED_FAMILY_UNKNOWN` говорит только о росте общих счётчиков Voice. `NO_COUNTER_INCREASE_OBSERVED` или недоступные счётчики — **не** доказательство неисправности IPv6.

## Финальные пункты Stage 5, которые этот скрипт намеренно не закрывает

Нужны отдельно зафиксированные на установленной `0.6.1_7` OPNsense: реальный IPv6 WAN и пакет назначения IPSET с STUN-обработкой `dvtws2` и корректной reinjection, подтверждение работы IPv4-only WAN, единый сохранённый Config / FD9 Apply, контролируемая ошибка активации с *точным* восстановлением предыдущих Config/PID/release/IPFW без воздействия на чужие правила. Непосредственную имитацию отказа `ipfw` выполнять только в изолированной VM; **не провоцировать сбои firewall на рабочем шлюзе**.

Успешный настоящий FreeBSD 15.1 VM `TABLE`/`IPV6_PACKET`/`TRANSACTION` из [PR #694](https://github.com/Tolian82/os-zapret2-restyle/pull/694) — дополнительное доказательство ядра, но не замена установленной приёмки. Stage 6 IPv6 Laboratory не объявлен готовым.
