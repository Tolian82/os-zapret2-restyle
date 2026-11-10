# G01 — независимая полная очистка Zapret2 Restyle

**Статус (8 ноября 2026): G01 INSTALLED-CI PASS, owner-live NOT TESTED.** Source `v0.6.3_3` merged through PR #975 (main `b247b725`), 25/25 CI, 37 fast checks and [G01 native PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42505329364). Disposable OPNsense 26.7 exercised genuine v1.0.7 installed purge, post-uninstall leftovers and RUNNING lo0/dvtws2 with owned IPFW and private Config backup. **Нельзя запускать `--purge` на рабочем шлюзе без отдельного явного согласия и backup.** Owner-live GUI not tested; stable released package remains `v0.6.3_1`.

**Источники:** [утверждённое ТЗ v1.1](../architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md), [строгий план G01–G11](../architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_PLAN.md), [автономный скрипт](../../scripts/purge-os-zapret2-restyle.sh), [позитивно-негативные source-тесты](../../scripts/test-purge-os-zapret2-restyle.py), [одноразовый native-guest smoke](../../scripts/stage2-opnsense-real-native-purge.py) и [CI workflow](../../.github/workflows/g01-native-disposable-purge.yml).

## Назначение и границы

Независимая от установленного пакета команда очищает **только** Zapret2 Restyle в случаях, когда нужно воспроизвести настоящую первую установку. Поддерживается ситуация «пакет удалён, но модель, upstream, bin/lua, журналы и служебные хвосты остались».

Различайте:
- **Штатный Uninstall в Firmware GUI / `pkg delete`:** сохраняет настройки, upstream движок, пользовательские Lua/BIN, логи **и root-owned исполняемую unowned копию `purge-os-zapret2-restyle.sh` по прежнему пути**. GUI/меню удаляются штатными hooks. `.pkg` содержит шаблон под `/usr/local/share/zapret2-restyle/`, `+POST_INSTALL` атомарно устанавливает непринадлежащий пакету CLI. Повторно устанавливать пакет только ради purge после uninstall НЕ требуется.
- **G01 `--dry-run` или без аргументов:** исключительно инвентаризация; не создаёт и даже не открывает на запись существующий FD9-lock, не изменяет конфигурацию и не удаляет данные. Наличие процессов отображается как **неподтверждённое** до защищённой проверки владельца после backup в режиме `--purge`. Выводит наличие пакета, GUI registration, сохранённого subtree, конкретных скриптов и директорий, статусы процесса, scoped IPFW, зарезервированных Voice-таблиц и файла репозитория; **не** выводит IP-списки, токены или содержимое Config.
- **G01 `--purge` (и при установленном, и при уже удалённом пакете):** требует root, действительную OPNsense / FreeBSD, точную фразу `PURGE OS-ZAPRET2-RESTYLE`, подтверждённые владельцы путей/правил и приватный backup всего `/conf/config.xml` **до первой необратимой операции**. Основной пакет удаляется через настоящий `pkg delete` с hooks; регистрация — через родной `firmware/register.php remove`; только `OPNsense.Zapret` удаляется нативным Config API под блокировкой. Дополнительно удаляются проверенные Zapret-only upstream, custom/Extra Lua/BIN, лабораторные job, state, логи и orphan GUI files. Чужие Config/другие плагины/общие зависимости не удаляются.
- **`--keep-repo`:** явно сохраняет только `/usr/local/etc/pkg/repos/zapret2-restyle.conf` для повторной установки через GUI. Это не *полностью* чистый результат по repository и всегда сообщается в отчёте.
- **`--yes-disposable`:** существует исключительно для подтверждённого CI-disposable гостя только при одновременных `ZAPRET2_PURGE_DISPOSABLE_GUEST=1`, `ZAPRET2_G01_DISPOSABLE_NATIVE=1`, `GITHUB_ACTIONS=true` и действительном виртуальном FreeBSD-госте. Это **не** документированный обход подтверждения на физическом устройстве.

## Ограничения и безопасные отказы

Внутренние symlink-алиасы оригинального upstream v1.0.7 (его Makefile создаёт ссылки на бинарники) допускаются **только внутри проверенного отдельного дерева Zapret2**: удаляется сама ссылка, а не её цель за пределами дерева. Отдельные symlink в корне пути или любой родительской директории запрещены.

Пути намеренно перечислены точно, без масок `/usr/local/*`, `/var/run/*` или общих `rm -rf`. При symlink в самом пути удаления или его родителях, non-root-owned файлах, изменённом содержимом repo file, неизвестном FD9/process owner, неподтверждённых IPFW правилах 19000–19010 / 19100–19131, ошибке приватного backup, неуспешном pkg/Config/native GUI — **отказ**, а не попытка угадать. После отказа, случившегося после `pkg delete`, отчёт должен объяснить необходимость ручной проверки; автоматический rollback уже уничтоженного файла не обещается. Исходный OPNsense Config backup остаётся под `/root/zapret2-restyle-purge-backups/` с правами 0700/0600.

Вся логика `ipfw` ограничена существующими, явно распознанными `divert` правилами: обычный сервис 989, Laboratory 9989, Voice-таблицы только пяти известных сервисов и их `_stage`. Скрипт не загружает модуль IPFW, не запускает `pfctl -d/-e`, не трогает чужие правила и не выполняет `pkg autoremove`. Для достижения чистого состояния используется штатная команда обновления меню OPNsense; не нужно удалять всю firmware/system конфигурацию.

## Набор проверок и доказательств

До принятия G01 должны быть реальные receipts для:

1. Отсутствия мутаций на `--dry-run` — до установки, после native pkg install, после полного purge, а также после штатного GUI uninstall.
2. Правильных `--purge` backup SHA/0600, сохранения других Config/firmware registrations, полного удаления root-owned custom Lua/BIN, state/jobs/logs, repo, runtime и исходной GUI-регистрации.
3. Реального служебного RUNNING → native hook stop → нет PID/FD9/IPFW и точного real rule/table cleanup, включая обнаружение чужих правил и сохранившихся процессов.
4. GUI: отсутствие Services → Zapret DPI Bypass после удаления без необходимости ручного Ctrl+F5; корректное положение Community Plugins при `--keep-repo`.
5. Повторного dry-run без остатков. В случае ошибки — не считать состояние чистым, пока manual/postcheck не подтверждён.
6. Честного разделения `SOURCE` / `INSTALLED-CI` / `OWNER-LIVE`, отдельные SHA-256, результаты `NOT TESTED` и нерешённые блокеры. Только после этого можно закрыть G01 и начать G02.

**Пока эти доказательства отсутствуют, данный документ является инструкцией для ревью и CI-тестового стенда, а не разрешением запускать деструктивную очистку на продуктивной OPNsense.**
