# G02 — нормальный Firmware GUI uninstall, без полного purge

**Статус (8 ноября 2026):** SOURCE-кандидат `v0.6.3_5`. Реальная установленная OPNsense 26.7 и owner-live GUI-проверки **ещё PENDING**; не объявлять G02 PASS до получения соответствующих receipts. Стабильный пакет остаётся `v0.6.3_1`. G01 standalone destructive purge уже отдельно прошёл native CI и вошёл в main через PR #975.

## Установленная причина

В [штатном OPNsense 26.7 MenuSystem](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/mvc/app/models/OPNsense/Base/Menu/MenuSystem.php) объединённые файлы `Menu.xml` кешируются на диске в `opnsense_menu_cache.xml` с **TTL 3600 секунд**. После обычного удаления plugin-owned `Menu.xml` кеш без инвалидации продолжает содержать Services → Zapret. F5/Ctrl+F5 не исправляют состояние серверного кеша.

В штатном [firmware/remove.sh](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/scripts/firmware/remove.sh) выполняются `pkg remove`, затем `firmware/register.php remove` и обычный нативный lifecycle. При непосредственном `pkg delete` последовательная регистрация не гарантируется внешним GUI; native `+POST_DEINSTALL` закрывает этот путь идемпотентно.

## Исправление в G02

- `pkg/+POST_DEINSTALL` после удаления файлов вызывает штатное `firmware/register.php remove os-zapret2-restyle`. Этот вызов идемпотентен: при upgrade с новым `version`-маркером OPNsense штатно сохраняет регистрацию, при полном удалении удаляет её.
- Затем нативный PHP `OPNsense\Base\Menu\MenuSystem::invalidateCache()` сбрасывает **только кеш модели меню**. Следующий запрос frontend строит меню по реально установленным `Menu.xml`; без глобальной перезагрузки webgui/configd.
- Штатный `PRE_DEINSTALL` сохраняет защиту FD9, запрещает удаление при неизвестном владельце и корректно останавливает RUNNING. Новый G02 hook не останавливает процессы самостоятельно.
- Обычный Uninstall **не вызывает** G01 full purge, не удаляет `OPNsense.Zapret`, `/usr/local/etc/zapret2`, Extra Lua/BIN, hostlists, jobs и логи; не вызывает `pkg autoremove` сам и не управляет чужими IPFW/PF.
- Отказ регистрации или menu API — явно диагностируемая ошибка, а не ложный success.

## Приёмка A18/A19

**SOURCE:** `sh -n pkg/+POST_DEINSTALL`, [шесть быстрых тестов](../../scripts/test-g02-normal-uninstall.py): порядок registrar → cache API, safe failure при недоступности registrar/PHP, отсутствие полного purge/глобальной перезагрузки, сохранность пользовательского файла.

**INSTALLED-CI:** [ровно один targeted native workflow](../../.github/workflows/g02-native-disposable-normal-uninstall.yml), [нативный тест](../../scripts/stage2-opnsense-real-native-normal-uninstall.py). На одноразовой OPNsense 26.7 установить настоящий source-built `0.6.3_5.pkg`, физический SHA-256 сохранить. Заполнить настоящий `OPNsense.Zapret`, установить upstream `v1.0.7`, создать пользовательский Lua, построить серверное кеш-меню с Zapret. Выполнить **штатный OPNsense `firmware/remove.sh`**, проверить отсутствие пакета, меню, firmware registration, но неизменность Config, Lua и движка. Перестроить меню — Zapret отсутствует. Затем заново установить **тот же физический архив с тем же SHA** и подтвердить возвращение меню/регистрации и сохранённого Config/ресурсов.

**OWNER-LIVE:** после доставки тестового пакета (этап G10) пользователь реально удаляет plugin в Firmware GUI, без Ctrl+F5 видит исчезновение пунктов Services, а после GUI reinstall — возвращение интерфейса и сохранённых настроек/ресурсов. Не проводить разрушительный full purge на продуктивном шлюзе ради G02. Пока нет owner-installed evidence, отмечать **NOT TESTED**, даже если SERVER/native CI зелёный.

**G02 не равен G03:** первая установка upstream через GUI и устранение блокировки ServiceController остаются следующим отдельным этапом. Защита общего движка Voice/Strategies, FD9/IPFW и исторических upgrades не ослабляется.
