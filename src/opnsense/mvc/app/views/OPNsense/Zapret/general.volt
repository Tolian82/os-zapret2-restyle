{#
    Copyright (C) 2026 Umur Gorur
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
#}

<script>
    $(document).ready(function() {
        const data_get_map = {'frm_GeneralSettings': "/api/zapret/settings/get"};
        const isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
        const runtimeText = {
            title: isRussian ? 'Служба Zapret2' : 'Zapret2 Service',
            repositoryReleases: isRussian ? 'Релизы репозитория' : 'Repository Releases',
            started: isRussian ? 'Запущена' : 'Started',
            stopped: isRussian ? 'Остановлена' : 'Stopped',
            error: '{{ lang._("Error") }}',
            start: '{{ lang._("Start") }}',
            stop: '{{ lang._("Stop") }}',
            apply: '{{ lang._("Apply") }}',
            applying: isRussian ? 'Применение…' : 'Applying…',
            installing: isRussian ? 'Установка…' : 'Installing…',
            loading: isRussian ? 'Загрузка…' : 'Loading…',
            unavailable: isRussian ? 'Недоступно' : 'Unavailable',
            notInstalled: isRussian ? 'Не установлен' : 'Not installed',
            statusUnavailable: isRussian
                ? 'Невозможно достоверно определить состояние службы'
                : 'The service state cannot be verified',
            operationFailed: isRussian
                ? 'Установка Zapret2 завершилась с ошибкой. Подробности: /var/log/zapret2/setup.log'
                : 'Zapret2 installation failed. See /var/log/zapret2/setup.log for details.',
            setupError: isRussian ? 'Ошибка установки Zapret2' : 'Zapret2 setup error',
            applyError: isRussian ? 'Ошибка применения настроек' : 'Settings Apply failed',
            applyReview: isRussian
                ? 'Результат обновления upstream не подтверждён. Обновите страницу и проверьте версию и службу перед повтором. Подробности: /var/log/zapret2/setup.log'
                : 'Upstream update result is unconfirmed. Reload and inspect the version and service before retrying. See /var/log/zapret2/setup.log.'
        };
        const extrasText = {
            install: isRussian ? 'Установить дополнительные ресурсы' : 'Install Additional Resources',
            remove: isRussian ? 'Удалить дополнительные ресурсы' : 'Remove Additional Resources',
            removePlanTitle: isRussian ? 'План удаления дополнительных ресурсов' : 'Additional Resources removal plan',
            removePlanInfo: isRussian ? 'Будут удалены дополнительные файлы: ' : 'Additional files selected for removal: ',
            removeWarning: isRussian
                ? 'Будут безвозвратно удалены только дополнительные Lua/BIN. Zapret2 будет остановлен и запущен с сохранёнными Strategies+Voice. Для подтверждения введите: '
                : 'Only additional Lua/BIN will be permanently deleted. Zapret2 will restart using saved Strategies+Voice. Type to confirm: ',
            removeConfirm: isRussian ? 'Подтвердить удаление' : 'Confirm removal',
            removeCancel: isRussian ? 'Отмена' : 'Cancel',
            removeRejected: isRussian ? 'Удаление отклонено. Проверьте состояние и повторно откройте актуальный план.' :
                'Removal rejected. Check the state and open a new plan before another request.',
            removeUncertain: isRussian ? 'Результат удаления не подтверждён. Не повторяйте запрос; проверьте состояние операции.' :
                'Removal outcome is unconfirmed. Do not repeat the request; inspect the operation state.',
            removeFailed: isRussian ? 'Удаление не завершено. Проверьте восстановление и журнал.' :
                'Removal failed. Review recovery state and the log.',
            removeRestored: isRussian
                ? 'Удаление не завершено. Исходные дополнительные ресурсы и состояние службы восстановлены.'
                : 'Removal failed. The original Additional Resources and service state were restored.',
            removeCompleted: isRussian ? 'Дополнительные ресурсы удалены' : 'Additional Resources removed',
            removeNoop: isRussian ? 'Дополнительных файлов для удаления нет.' : 'No additional resources require removal.',
            removePlanError: isRussian ? 'Не удалось получить подтверждённый план удаления. Файлы не изменены.' :
                'Could not obtain the verified removal plan. No files were changed.',
            firstStart: isRussian ? 'Сначала запустите Zapret2' : 'Start Zapret2 first',
            unavailable: isRussian ? 'Состояние ресурсов недоступно' : 'Resource status unavailable',
            notInstalled: isRussian ? 'Дополнительные ресурсы не установлены' : 'Additional Resources not installed',
            downloading: isRussian ? 'Загрузка ресурсов…' : 'Downloading resources…',
            verifying: isRussian ? 'Проверка файлов…' : 'Verifying resources…',
            installing: isRussian ? 'Установка и перезапуск Zapret2…' : 'Installing and restarting Zapret2…',
            recovering: isRussian ? 'Восстановление после ошибки…' : 'Restoring previous resources…',
            failed: isRussian ? 'Не удалось установить ресурсы' : 'Resource installation failed',
            restoreFailed: isRussian ? 'Не удалось восстановить прежнее состояние' : 'Previous state could not be restored',
            review: isRussian ? 'Требуется проверка результата перед повторной попыткой' :
                'Review the previous result before trying again',
            ready: isRussian ? 'Установлено' : 'Installed',
            restored: isRussian ? 'Дополнительные ресурсы восстановлены' : 'Additional Resources restored',
            removing: isRussian ? 'Удаление дополнительных ресурсов…' : 'Removing Additional Resources…',
            lua: 'Lua', bin: 'BIN',
            native: isRussian ? 'Из установленной версии Zapret2' : 'Included in installed Zapret2',
            other: isRussian ? 'Остальные установленные ресурсы' : 'Other installed resources',
            installHelp: isRussian
                ? 'Дополнительные ресурсы пока не установлены. Нажмите «Установить дополнительные ресурсы», чтобы добавить новые .lua и .bin файлы.'
                : 'Additional Resources have not been installed. Click “Install Additional Resources” to add extra .lua and .bin files.',
            listUnavailable: isRussian ? 'Кэш списка ресурсов недоступен. Обновление списка выполняется после установки или смены версии Zapret2.'
                : 'The resource list cache is unavailable. It is updated after installation or a Zapret2 version change.',
            none: isRussian ? 'Нет установленных файлов' : 'No installed files',
            log: '/var/log/zapret2/extra-resources.log'
        };
        let extraPoll = null;
        let extraPollAttempts = 0;
        let helpInventoryLoaded = false;
        let helpInventoryRequest = false;
        let helpInventoryPendingRefresh = false;
        let resourceHelpWasVisible = false;
        let helpInventoryLastInstalled = false;
        let extraStateKnown = false;
        let extraBusy = false;
        let extraInstallPending = false;
        let extraRemovePending = false;
        let extraRemoveOperation = '';
        let extraExpectedOperation = '';
        let extraNeedsReview = false;
        let runtimePoll = null;
        let runtimeWasBusy = false;
        let runtimeStatusInFlight = false;
        let releaseNeedsReview = false;
        let releaseExpectedVersion = '';
        let releaseOriginalVersion = '';
        let releaseOriginalService = '';
        let releaseObservedBusy = false;
        let releaseApplyStartedAt = 0;
        const releaseApplyDeadlineMs = 10 * 60 * 1000;
        let currentServiceState = 'error';
        let currentRuntimeInstalled = false;
        let releaseApplyPending = false;
        let strategiesApplyPending = false;
        let strategiesApplyNeedsReview = false;

        // The Telegram IPSET is also editable on Voice Transmission. Include
        // its original value in the Strategies POST as a concurrency token.
        // A stale browser tab is rejected before the model or runtime changes.
        const telegramBaseline = $('<input/>', {
            type: 'hidden', id: 'zapret.sync.telegramips_baseline'
        });
        $('#frm_GeneralSettings').append(telegramBaseline);


        // P3: one UI-only dictionary, keyed by immutable native form IDs.
        // English native OPNsense form text remains the fallback.
        const strategiesLabelsRU = {
            'zapret.general.enabled': 'Включить',
            'zapret.general.waninterface': 'Интерфейс WAN',
            'zapret.general.divertport': 'Порт Divert',
            'zapret.strategy.trafficargs': 'Стратегия обработки трафика',
            'zapret.strategy.extraargs': 'Дополнительные аргументы',
            'zapret.hostlist.mode': 'Режим выбора целей',
            'zapret.hostlist.youtubedomains': 'Домены YouTube',
            'zapret.hostlist.telegramips': 'IPSET Telegram',
            'zapret.hostlist.userdomains': 'Пользовательские домены',
            'zapret.hostlist.excludedomains': 'Исключить домены'
        };
        const strategiesHelpRU = {
            'zapret.general.enabled':
                'Включить общую службу Zapret2 для стратегий и голосовых профилей.',
            'zapret.general.waninterface':
                'Интерфейс WAN, на котором применяется обход DPI. Voice использует тот же WAN.',
            'zapret.general.divertport':
                'Порт сокета ipfw divert (обычно 989). Меняйте при конфликте с другой службой.',
            'zapret.strategy.trafficargs':
                'Нативная стратегия <code>dvtws2</code>. Независимые профили разделяются <code>--new</code>; ' +
                'для потока выбирается первый подходящий профиль по порядку движка. ' +
                'Один HOSTLIST/IPSET можно использовать в разных профилях.<br/>' +
                'Внутри одного профиля допускаются несколько последовательных <code>--payload</code> и ' +
                '<code>--lua-desync</code>. Не разделяйте их <code>--new</code> без необходимости.<br/>' +
                '<code>--filter-tcp</code>/<code>--filter-udp</code> выбирают порты профиля и влияют на охват ' +
                'IPFW; <code>--filter-l7</code> выбирает протокол. Диапазоны, payload и Lua принадлежат ' +
                'выбранному профилю.<br/>' +
                'Цели: <code>&lt;HOSTLIST:youtube&gt;</code>, <code>&lt;HOSTLIST:user&gt;</code>, ' +
                '<code>&lt;IPSET:telegram&gt;</code>. Нельзя дважды подключать один и тот же ' +
                'файл списка одного типа внутри профиля. Нативный dry-run проверяет синтаксис, а не успех обхода DPI.',
            'zapret.strategy.extraargs':
                'Добавляются после Traffic Strategy в итоговую командную строку <code>dvtws2</code>. ' +
                '<b>Не обязательно глобальные:</b> параметры профиля могут относиться к последнему профилю. ' +
                'Перед изменением проверьте объединённую команду.',
            'zapret.hostlist.mode':
                'Действует только для профилей без явного <code>&lt;HOSTLIST:name&gt;</code> или ' +
                '<code>&lt;IPSET:name&gt;</code>.<br/>' +
                '«Весь трафик» не ограничивает списки целей; «Только из списков» использует YouTube, Telegram IPs ' +
                'и пользовательские домены; «Автоопределение» дополнительно включает обнаруженные заблокированные домены.<br/>' +
                'Это выбор цели движком, а не фильтр портов перехвата IPFW. Глобальные исключения действуют отдельно.',
            'zapret.hostlist.youtubedomains':
                'Источник <code>&lt;HOSTLIST:youtube&gt;</code>, один домен в строке. ' +
                '<code>example.com</code> учитывает нативное поведение поддоменов; ' +
                '<code>^example.com</code> — только точный домен; <code>!example.com</code> — локальное ' +
                'исключение HOSTLIST; <code>!^example.com</code> — локальное исключение точного домена.<br/>' +
                'При вставке HTTP(S)-ссылки остаётся имя хоста. Маску нельзя сочетать с <code>!</code> ' +
                'или <code>^</code>; ошибки модификаторов указывают строку. Локальное <code>!</code> ' +
                '<b>не равно</b> глобальному исключению домена.',
            'zapret.hostlist.telegramips':
                'Общий со страницей Voice <code>&lt;IPSET:telegram&gt;</code>. ' +
                'Один IPv4/IPv6-адрес или CIDR в строке, без имён хостов и охвата всего семейства.',
            'zapret.hostlist.userdomains':
                'Источник <code>&lt;HOSTLIST:user&gt;</code>, один домен в строке. ' +
                '<code>example.com</code> учитывает поддомены; <code>^example.com</code> — только точный домен; ' +
                '<code>!example.com</code> — локальное исключение; <code>!^example.com</code> — только ' +
                'точный домен.<br/>' +
                'HTTP(S)-ссылка приводится к имени хоста. Маски несовместимы с <code>!</code>/<code>^</code>; ' +
                'конфликтующие правила отклоняются с указанием строки. Локальное <code>!</code> ' +
                'не действует на другие профили и глобальные исключения.',
            'zapret.hostlist.excludedomains':
                'Глобально исключить домены из обхода DPI, по одному в строке. ' +
                'Это отдельная политика, не локальный <code>!example.com</code> в HOSTLIST.<br/>' +
                'Модификаторы <code>!</code> и <code>^</code> здесь запрещены. ' +
                'Проверка Python сообщает строку некорректного домена.'
        };
        const strategiesInfoRU =
            'Запустите <b>blockcheck2</b> на странице ' +
            '<a href="/ui/zapret/diagnostics">Диагностика</a> или по SSH:<br/>' +
            '<code>cd /usr/local/etc/zapret2 &amp;&amp; env IFACE_WAN=your_wan_if /bin/sh blockcheck2.sh</code><br/><br/>' +
            'Изучите результат <b>SUMMARY</b> и добавьте профиль в поле ' +
            '<b>Стратегия обработки трафика</b>. HTTP, HTTPS/TLS, TCP и UDP могут ' +
            'сосуществовать. Независимые профили разделяются <code>--new</code>. ' +
            'Не заменяйте существующую многопрофильную стратегию без проверки объединения.';

        const strategiesInfoEN =
            'Run <b>blockcheck2</b> from the ' +
            '<a href="/ui/zapret/diagnostics">Diagnostics</a> page or via SSH:<br/>' +
            '<code>cd /usr/local/etc/zapret2 &amp;&amp; env IFACE_WAN=your_wan_if /bin/sh blockcheck2.sh</code><br/><br/>' +
            'Review the working strategy from the <b>SUMMARY</b> output and add the profile ' +
            'to the unified <b>Traffic Strategy</b> field. HTTP, HTTPS/TLS, TCP and UDP ' +
            'profiles may coexist; separate independent profiles with <code>--new</code>. ' +
            'Do not overwrite an existing multi-profile strategy without checking how to merge.';

        function localizeStrategiesForm() {
            const form = $('#frm_GeneralSettings');
            // form_input_tr renders <span id=...> for info; XML <text>
            // is documentation, NOT a rendered DOM anchor.
            const info = form.find('#zapretStrategiesInfoSource');
            if (info.length) info.html(isRussian ? strategiesInfoRU : strategiesInfoEN);
            if (!isRussian) return;
            // Native section title lives in the <thead> of its field's
            // table. Preserve the existing collapse icon and behavior.
            [
                ['zapret.general.enabled', 'Общие настройки'],
                ['zapret.strategy.trafficargs', 'Стратегия обхода DPI'],
                ['zapret.hostlist.mode', 'Цели']
            ].forEach(function(entry) {
                const field = document.getElementById(entry[0]);
                if (!field) return;
                $(field).closest('table').children('thead').find('th b').first().text(entry[1]);
            });
            form.find('#control_label_zapretStrategiesInfoSource > b').text('Как найти стратегию');
            Object.keys(strategiesLabelsRU).forEach(function(id) {
                const input = document.getElementById(id) ||
                              document.getElementById(id.replace(/\./g, '_'));
                if (!input) return;
                const row = $(input).closest('tr');
                // Stock OPNsense form_input_tr uses div.control-label > b,
                // not an HTML <label> element. Never replace help icons.
                row.find('div.control-label > b').first().text(strategiesLabelsRU[id]);
                $(input).attr('aria-label', strategiesLabelsRU[id]);
                const help = strategiesHelpRU[id];
                // Source for both native popup and F5 Full Help.
                row.find('div[data-for^="help_for_"] small').html(help);
                const visible = row.find('.help-block').first();
                if (visible.length && visible.text().trim()) visible.html(help);
            });
        }

        // Preserve the existing Exclude IPSet inline-only F5 help layout.
        function localizeExcludeIPSet() {
            const field = document.getElementById('zapret.hostlist.excludeipset') ||
                          document.getElementById('zapret_hostlist_excludeipset');
            if (!field) return;
            const row = $(field).closest('tr');
            // Same layout as Exclude Domains: retain the explanation under
            // the textarea, but never duplicate it in OPNsense's third
            // (right-hand) help column, even after F5/full-help toggle.
            // Scoped to one field and both RU/EN; no other native help moves.
            row.addClass('zapret-exclude-ipset-inline-help-only');
            if (!isRussian) return;
            row.find('div.control-label > b').first().text('Исключить IPSet');
            $(field).attr('aria-label', 'Исключить IPSet');
            const help = 'Глобальное исключение IP-адресов назначения из обхода DPI после подключения нативной политики. ' +
                'По одному IPv4/IPv6-адресу или CIDR-сети в строке. Пересекающиеся и соседние сети объединяются. ' +
                'Недопустимы имена доменов, индексы зон IPv6, 0.0.0.0/0, ::/0 и эквивалентный полный охват сети. ' +
                'Пустое поле сохраняет прежнее поведение. Домены указываются отдельно в «Исключить домены».';
            row.find('div[data-for^="help_for_"] small').html(help);
            const visible = row.find('.help-block').first();
            if (visible.length) visible.html(help);
        }

        // Native OptionField values remain all/list/auto regardless of locale.
        const targetModeLabelsRU = {
            all: 'Весь трафик на указанных портах',
            list: 'Только указанные домены',
            auto: 'Автоопределение заблокированных доменов'
        };
        function localizeTargetModeOptions() {
            if (!isRussian) return;
            const select = document.getElementById('zapret.hostlist.mode');
            if (!select) return;
            Array.prototype.forEach.call(select.options, function(option) {
                if (Object.prototype.hasOwnProperty.call(targetModeLabelsRU, option.value)) {
                    option.textContent = targetModeLabelsRU[option.value];
                }
            });
        }

        function reloadSettings() {
            return mapDataToFormUI(data_get_map).done(function() {
                const currentField = document.getElementById('zapret.hostlist.telegramips');
                telegramBaseline.val(currentField ? currentField.value : '');
                formatTokenizersUI();
                localizeStrategiesForm();
                localizeExcludeIPSet();
                localizeTargetModeOptions();
                $('.selectpicker').selectpicker('refresh');
            });
        }

        // Localize ONLY known validation outputs from the Python-backed
        // domain/IPSET bridges and the native model. Never expose arbitrary
        // backend text or submitted user values in a translated field error.
        function localizeStrategiesFieldErrors(errors) {
            if (!isRussian || !errors || typeof errors !== 'object' ||
                Array.isArray(errors)) return errors || {};
            const fixed = {
                'Please enter a valid port number.': 'Укажите корректный номер порта.',
                'Please enter comma-separated port numbers.': 'Укажите номера портов через запятую.',
                'Please enter IPv4/IPv6 addresses or CIDR networks; full-family coverage is forbidden.':
                    'Укажите IPv4/IPv6-адреса или сети CIDR. Охват всего семейства запрещён.',
                'Enter IPv4/IPv6 address or CIDR per line; /0 and full-family unions are forbidden.':
                    'Укажите по одному IPv4/IPv6-адресу или CIDR в строке. /0 и охват всего семейства запрещены.',
                'Select a WAN interface': 'Укажите WAN-интерфейс.',
                'Selected WAN interface is not assigned or unavailable':
                    'Выбранный WAN-интерфейс не назначен или недоступен.',
                'Invalid bounded domain field': 'Некорректный или слишком большой список доменов.',
                'Native IPSET preflight refused invalid addresses or networks':
                    'IPSET содержит некорректные адреса или сети.',
                'Native IPSET preflight unavailable':
                    'Невозможно проверить IPSET: проверка недоступна.'
            };
            const domain = {
                'Missing domain': 'Отсутствует домен',
                'Repeated ! or ^ modifier': 'Повторён модификатор ! или ^',
                'Modifiers are not permitted in Exclude Domains':
                    'Модификаторы запрещены в глобальном списке исключений доменов',
                'Modifiers cannot be combined with wildcard domains':
                    'Нельзя сочетать модификаторы и домены с маской',
                'IP addresses and networks are not allowed in domain lists':
                    'IP-адреса и сети не допускаются в списках доменов',
                'Invalid domain': 'Некорректный домен',
                'Conflicting rules for the same domain':
                    'Противоречащие правила для одного домена'
            };
            const result = {};
            Object.keys(errors).forEach(function(key) {
                const message = errors[key];
                if (typeof message !== 'string') { result[key] = message; return; }
                if (Object.prototype.hasOwnProperty.call(fixed, message)) {
                    result[key] = fixed[message];
                    return;
                }
                const match = /^(.+) \(line ([1-9][0-9]{0,6})\)$/.exec(message);
                if (match && Object.prototype.hasOwnProperty.call(domain, match[1])) {
                    result[key] = domain[match[1]] + ' (строка ' + match[2] + ')';
                    return;
                }
                const ipset = /^Invalid IPSET [A-Za-z ()]{1,80}(?: at line ([1-9][0-9]{0,6}))?$/.exec(message);
                if (ipset) {
                    result[key] = 'Некорректный IPSET' +
                        (ipset[1] ? ' (строка ' + ipset[1] + ')' : '') + '.';
                    return;
                }
                result[key] = 'Ошибка проверки поля. Исправьте значение или проверьте журнал Zapret2.';
            });
            return result;
        }

        // Keep known pre-dispatch errors localized like the rest of the UI.
        // Other PHP exception strings are not suitable as UI translations.
        function localizeStrategiesApplyError(message, reason) {
            // Server gettext and browser language can differ.
            if (reason === 'runtime-not-installed') {
                return isRussian
                    ? 'Требуется установка службы zapret2'
                    : 'The zapret2 service must be installed';
            }
            // Only fixed, allowlisted native preflight stages supplied by the
            // PHP contract may be displayed. No raw exception/config text.
            if (typeof reason === 'string' && reason.indexOf('native-preflight-') === 0) {
                const stage = reason.slice('native-preflight-'.length);
                const allowed = /^(root-gate|bootstrap|model|decode|candidate|wan-required|candidate-plan|candidate-validation|candidate-xml|candidate-size|workspace|render|runtime-build|seal|bundle-verify|config-preflight|runtime-preflight|wan-candidate|wan-lifecycle|wan-runtime-owner|wan-kernel|wan-model)$/;
                if (allowed.test(stage)) {
                    return isRussian
                        ? 'Нативная проверка не пройдена (этап: ' + stage + '). Изменения не применены.'
                        : 'Native Strategies preflight rejected before Apply (' + stage + ')';
                }
            }
            if (typeof reason === 'string' && reason.indexOf('strategies-preflight-') === 0) {
                const stage = reason.slice('strategies-preflight-'.length);
                const allowed = /^(lifecycle-guard|model|runtime-status|normalization|candidate-validation|candidate-xml|envelope|dispatch-guard)$/;
                if (allowed.test(stage)) {
                    return isRussian
                        ? 'Предварительная проверка настроек не пройдена (этап: ' + stage + '). Изменения не применены.'
                        : 'Strategies preflight failed before native Apply (' + stage + ')';
                }
            }
            if (!isRussian) return message;
            const translations = {
                'Select a WAN interface': 'Укажите WAN интерфейс',
                'The zapret2 service must be installed': 'Требуется установка службы zapret2',
                'Selected WAN interface is not assigned or unavailable':
                    'Указанный WAN интерфейс не назначен или недоступен',
                'Candidate changes fields outside the owning form':
                    'Кандидат изменяет поля, не принадлежащие форме «Стратегии».',
                'Candidate changes a foreign field':
                    'Кандидат изменяет постороннее поле конфигурации.',
                'Shared change map omits candidate field':
                    'В списке изменений отсутствует поле кандидата.',
                'Shared change map includes unchanged field':
                    'В списке изменений указано неизменённое поле.',
                'Strategies candidate field validation refused':
                    'Проверка изменённого поля стратегии не пройдена.',
                'Missing or invalid Strategies baseline; reload this page':
                    'Исходное состояние стратегии не подтверждено. Обновите страницу.',
                'Shared Apply request is too large; shorten the destination lists':
                    'Размер изменённых данных превышает допустимый лимит передачи. Настройки не применены.'
            };
            return translations[message] ||
                'Предварительная проверка настроек не пройдена. Изменения не применены.';
        }
        // Display-only receipt from five fixed SettingsController TARGET_FIELDS.
        // Unexpected lines must never echo untrusted text or change Apply state.
        function localizeStrategiesNormalizationSummary(lines) {
            const labels = {
                'YouTube Domains': 'Домены YouTube',
                'Telegram IPs': 'IPSET Telegram',
                'User Domains': 'Пользовательские домены',
                'Exclude Domains': 'Исключить домены',
                'Exclude IPSet': 'Исключить IPSet'
            };
            const fallback = isRussian
                ? 'Подробности нормализации недоступны. Проверьте сохранённые настройки.'
                : 'Normalization details unavailable. Verify saved settings.';
            if (!Array.isArray(lines)) return [fallback];
            return lines.map(function(line) {
                if (typeof line !== 'string') return fallback;
                const match = /^(YouTube Domains|Telegram IPs|User Domains|Exclude Domains|Exclude IPSet): normalized ([0-9]{1,9}), removed duplicates ([0-9]{1,9})$/.exec(line);
                if (!match || !Object.prototype.hasOwnProperty.call(labels, match[1])) {
                    return fallback;
                }
                return isRussian ? labels[match[1]] + ': нормализовано ' + match[2] +
                    ', удалено повторов ' + match[3] : line;
            });
        }

        function showRuntimeError(title, message) {
            BootstrapDialog.show({
                type: BootstrapDialog.TYPE_DANGER,
                title: title,
                message: $('<div/>').text(message),
                buttons: [{
                    label: '{{ lang._("Close") }}',
                    action: function(dialog) { dialog.close(); }
                }]
            });
        }

        function setRuntimeBusy(busy) {
            // Controls must stay locked for both operations, but each Apply
            // button owns only its own spinner.
            const controlsBusy = !!busy || releaseApplyPending || releaseNeedsReview ||
                strategiesApplyPending || strategiesApplyNeedsReview ||
                extraBusy || extraInstallPending || extraNeedsReview || extraRemovePending;
            const releaseAvailable = $('#zapretReleaseSelect option').filter(function() {
                return /^v[0-9]+(?:\.[0-9]+)+$/.test(this.value);
            }).length > 0;
            const serviceControllable = currentRuntimeInstalled &&
                (currentServiceState === 'started' || currentServiceState === 'stopped');

            $('#zapretServiceControl').prop('disabled', controlsBusy || !serviceControllable);
            $('#zapretReleaseSelect').prop('disabled', controlsBusy || !releaseAvailable);
            $('#zapretReleaseApply').prop('disabled', controlsBusy || !releaseAvailable);
            // Lower Strategies Apply is a separate action/spinner, but must
            // never compete with an Additional Resources lifecycle transaction.
            $('#reconfigureAct').prop('disabled', controlsBusy);
            $('#zapretReleaseApplyText').text(releaseApplyPending ? runtimeText.applying : runtimeText.apply);
            $('#zapretReleaseApplyProgress').toggleClass('fa fa-spinner fa-pulse', releaseApplyPending);
            const extrasAllowed = currentRuntimeInstalled && currentServiceState === 'started' &&
                extraStateKnown && !controlsBusy;
            $('#zapretExtraInstall').prop('disabled', !extrasAllowed);
            $('#zapretExtraInstall').attr('title', currentServiceState === 'stopped'
                ? extrasText.firstStart : (extraNeedsReview ? extrasText.review : extrasText.install));
            // Native backend busy is shared by Install and Remove. Both buttons
            // stay locked, but a Remove worker owns only the Remove spinner.
            $('#zapretExtraProgress').toggleClass('fa fa-spinner fa-pulse',
                extraInstallPending || (extraBusy && !extraRemovePending));
            $('#zapretExtraRemove').prop('disabled', !extrasAllowed || extraRemovePending);
            $('#zapretExtraRemoveProgress').toggleClass('fa fa-spinner fa-pulse', extraRemovePending);
        }

        function reconcileStrategiesApplyControls() {
            $('#reconfigureAct').prop('disabled',
                strategiesApplyPending || strategiesApplyNeedsReview);
            $('#reconfigureActProgress').toggleClass('fa fa-spinner fa-pulse',
                strategiesApplyPending);
            setRuntimeBusy(runtimeWasBusy);
        }

        // The runtime worker can finish between polls, or its status endpoint
        // can transiently fail while native FD9 is held. Correlate the desired
        // release with a real busy observation OR a changed committed version.
        // An unchanged-version replay with no busy evidence remains uncertain.
        function releaseTerminalOutcome(data, target, previous, service, observedBusy) {
            if (!data || data.busy) return 'pending';
            const progressed = observedBusy || (previous !== target && data.version === target);
            if (!progressed) return 'pending';
            // A failed initial setup can correctly leave installed=0.
            if (data.setup === 'failed') return 'failed';
            const expectedService = service === 'error' ? 'stopped' : service;
            if (data.installed && data.setup === 'ready' &&
                data.version === target && data.service === expectedService) {
                return 'success';
            }
            return 'pending';
        }

        function stopRuntimePolling() {
            if (runtimePoll !== null) {
                window.clearInterval(runtimePoll);
                runtimePoll = null;
            }
        }

        function ensureRuntimePolling(busy) {
            if ((releaseApplyPending || busy) && runtimePoll === null) {
                runtimePoll = window.setInterval(refreshRuntime, 2000);
            } else if (!releaseApplyPending && !busy) {
                stopRuntimePolling();
            }
        }

        function finishReleaseOperation(needsReview, failureMessage) {
            releaseApplyPending = false;
            releaseNeedsReview = releaseNeedsReview || !!needsReview;
            releaseExpectedVersion = '';
            releaseOriginalVersion = '';
            releaseOriginalService = '';
            releaseObservedBusy = false;
            releaseApplyStartedAt = 0;
            if (failureMessage) {
                showRuntimeError(runtimeText.setupError, failureMessage);
            }
        }

        // Exactly the five visible LC-09 categories. API uncertainty,
        // inconsistent setup receipts and malformed native states fail closed.
        function classifyRuntimeStatus(data) {
            if (!data || data.status !== 'ok' ||
                typeof data.installed !== 'boolean' ||
                typeof data.busy !== 'boolean' ||
                typeof data.version !== 'string' ||
                ['started', 'stopped', 'error'].indexOf(data.service) === -1 ||
                ['ready', 'installing', 'failed', 'unknown'].indexOf(data.setup) === -1) {
                return 'error';
            }
            if (data.busy) return data.setup === 'installing' ? 'installing' : 'error';
            if (data.setup === 'installing') return 'error';
            if (!data.installed) {
                return data.setup === 'unknown' && data.service === 'error' &&
                    data.version === '' ? 'not-installed' : 'error';
            }
            if (!/^v[0-9]+(?:\.[0-9]+)+$/.test(data.version)) return 'error';
            return data.service === 'started' || data.service === 'stopped'
                ? data.service : 'error';
        }

        function renderRuntime(data) {
            const category = classifyRuntimeStatus(data);
            const installed = !!(data && data.installed === true);
            const service = data && ['started', 'stopped', 'error'].indexOf(data.service) !== -1
                ? data.service
                : 'error';
            const busy = !!(data && data.busy);
            const badge = $('#zapretServiceStatus');
            const serviceButton = $('#zapretServiceControl');
            const wasBusy = runtimeWasBusy;
            let failureReported = false;

            if (releaseApplyPending && (busy || (data && data.setup === 'installing'))) {
                releaseObservedBusy = true;
            }
            if (releaseApplyPending) {
                const outcome = releaseTerminalOutcome(data, releaseExpectedVersion,
                    releaseOriginalVersion, releaseOriginalService, releaseObservedBusy);
                if (outcome === 'success') {
                    finishReleaseOperation(false, '');
                    helpInventoryLoaded = false;
                    requestResourceHelpInventory(true);
                } else if (outcome === 'failed') {
                    failureReported = true;
                    finishReleaseOperation(false, runtimeText.operationFailed);
                }
            }

            // Unknown native receipt must also lock the release Install
            // control; the backend independently repeats this refusal.
            if (data && data.reason === 'status-unavailable') {
                releaseNeedsReview = true;
            }
            currentRuntimeInstalled = installed;
            if (!busy) {
                currentServiceState = category === 'started' || category === 'stopped'
                    ? category : 'error';
            }
            badge.removeClass('label-success label-default label-danger label-info');
            badge.attr('title', data && data.reason === 'status-unavailable'
                ? runtimeText.statusUnavailable : '');

            if (category === 'installing') {
                // Native setup holds FD9; do not mistake transient stopped or
                // error service status for terminal installation failure.
                badge.addClass('label-info').text(runtimeText.installing);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.hide().prop('disabled', true);
            } else if (category === 'not-installed') {
                badge.addClass('label-default').text(runtimeText.notInstalled);
                $('#zapretRuntimeVersion').text('—');
                serviceButton.hide().prop('disabled', true);
            } else if (category === 'started') {
                badge.addClass('label-success').text(runtimeText.started);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.show().text(runtimeText.stop).prop('disabled', busy);
            } else if (category === 'stopped') {
                badge.addClass('label-default').text(runtimeText.stopped);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.show().text(runtimeText.start).prop('disabled', busy);
            } else {
                badge.addClass('label-danger').text(runtimeText.error);
                $('#zapretRuntimeVersion').text(data && data.version || '—');
                serviceButton.hide().prop('disabled', true);
            }

            if (wasBusy && !busy && data && data.setup === 'failed' && !failureReported &&
                !releaseApplyPending) {
                showRuntimeError(runtimeText.setupError, runtimeText.operationFailed);
            }
            runtimeWasBusy = busy;
            setRuntimeBusy(busy);
            ensureRuntimePolling(busy);
        }

        function renderRuntimeRequestFailure() {
            if (releaseApplyPending || runtimeWasBusy) {
                // Transient API failures are not evidence that native setup
                // failed. Preserve the last valid view and continue polling.
                ensureRuntimePolling(runtimeWasBusy);
                setRuntimeBusy(runtimeWasBusy);
                return;
            }
            // No verified state means a new install is NOT safe to dispatch.
            releaseNeedsReview = true;
            currentRuntimeInstalled = false;
            currentServiceState = 'error';
            $('#zapretServiceStatus')
                .removeClass('label-success label-default label-danger label-info')
                .addClass('label-danger')
                .text(runtimeText.error)
                .attr('title', runtimeText.statusUnavailable);
            $('#zapretRuntimeVersion').text('—');
            $('#zapretServiceControl').hide().prop('disabled', true);
            setRuntimeBusy(false);
        }

        function refreshRuntime() {
            if (releaseApplyPending && releaseApplyStartedAt &&
                Date.now() - releaseApplyStartedAt >= releaseApplyDeadlineMs) {
                finishReleaseOperation(true, runtimeText.applyReview);
                ensureRuntimePolling(runtimeWasBusy);
                setRuntimeBusy(runtimeWasBusy);
            }
            // Never stack multiple 30s status requests while setup.lock/FD9
            // is held: one request in flight is sufficient.
            if (runtimeStatusInFlight) return;
            runtimeStatusInFlight = true;
            return $.ajax({
                type: 'POST',
                url: '/api/zapret/service/runtime',
                dataType: 'json',
                timeout: 30000
            }).done(renderRuntime).fail(renderRuntimeRequestFailure).always(function() {
                runtimeStatusInFlight = false;
            });
        }

        function refreshReleases(selectedVersion) {
            const select = $('#zapretReleaseSelect');
            select.prop('disabled', true).empty().append(
                $('<option/>').attr('value', '').text(runtimeText.loading)
            );

            return $.ajax({
                type: 'POST',
                url: '/api/zapret/service/releases',
                dataType: 'json',
                timeout: 60000
            }).done(function(data) {
                select.empty();
                if (!data || data.status !== 'ok' || !Array.isArray(data.releases)) {
                    select.append($('<option/>').attr('value', '').text(runtimeText.unavailable));
                    setRuntimeBusy(runtimeWasBusy);
                    return;
                }

                data.releases.forEach(function(release) {
                    select.append($('<option/>').attr('value', release).text(release));
                });
                if (selectedVersion && select.find('option[value="' + selectedVersion + '"]').length) {
                    select.val(selectedVersion);
                }
                setRuntimeBusy(runtimeWasBusy);
            }).fail(function() {
                select.empty().append($('<option/>').attr('value', '').text(runtimeText.unavailable));
                setRuntimeBusy(runtimeWasBusy);
            });
        }

        function isResourceAdvancedEnabled() {
            return $('#show_advanced_frm_GeneralSettings').hasClass('fa-toggle-on');
        }

        function updateResourceAdvancedVisibility() {
            $('#zapretExtraRemoveRow').toggle(isResourceAdvancedEnabled());
        }

        // This is the native OPNsense Advanced toggle, independent of Help.
        const resourceAdvancedIcon = document.getElementById('show_advanced_frm_GeneralSettings');
        if (resourceAdvancedIcon && window.MutationObserver) {
            const observer = new MutationObserver(updateResourceAdvancedVisibility);
            observer.observe(resourceAdvancedIcon, {attributes: true, attributeFilter: ['class']});
        }
        updateResourceAdvancedVisibility();

        function isResourceHelpEnabled() {
            // Native OPNsense 26.7 full-help toggle for frm_GeneralSettings.
            return $('#show_all_help_frm_GeneralSettings').hasClass('fa-toggle-on');
        }

        function renderResourceHelpInventory(data) {
            const panel = $('#zapretExtraResourceHelp');
            panel.empty();
            if (!data || data.status !== 'ok') {
                // A missing/corrupt cache is UNKNOWN, never evidence of absence.
                panel.append($('<p/>').text(extrasText.listUnavailable));
                return;
            }
            helpInventoryLastInstalled = !!data.installed;
            if (!data.installed) {
                panel.append($('<p/>').text(extrasText.installHelp));
                return;
            }
            const legend = $('<div/>', {'class': 'zapret-resource-legend'});
            $('<span/>', {'class': 'text-success'}).text(extrasText.native).appendTo(legend);
            $('<span/>', {'class': 'text-info'}).text(extrasText.other).appendTo(legend);
            panel.append(legend);
            const columns = $('<div/>', {'class': 'zapret-resource-columns'});
            [['lua', extrasText.lua], ['bin', extrasText.bin]].forEach(function(pair) {
                const name = pair[0];
                const items = Array.isArray(data[name]) ? data[name] : [];
                const column = $('<div/>', {'class': 'zapret-resource-column'});
                $('<strong/>').text(pair[1] + ' (' + items.length + ')').appendTo(column);
                const list = $('<ul/>', {'class': 'list-unstyled zapret-resource-list'});
                items.forEach(function(item) {
                    if (!item || typeof item.name !== 'string' ||
                        !/^[A-Za-z0-9_.+\-]+\.(lua|bin)$/.test(item.name)) return;
                    $('<li/>').addClass(item.origin === 'upstream' ? 'text-success' : 'text-info')
                        .text(item.name).appendTo(list);
                });
                if (!list.children().length) {
                    $('<li/>', {'class': 'text-muted'}).text(extrasText.none).appendTo(list);
                }
                column.append(list);
                columns.append(column);
            });
            panel.append(columns);
        }

        function requestResourceHelpInventory(force) {
            if (!isResourceHelpEnabled()) return;
            if (helpInventoryRequest) {
                helpInventoryPendingRefresh = helpInventoryPendingRefresh || !!force;
                return;
            }
            if (helpInventoryLoaded && !force) return;
            helpInventoryRequest = true;
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesInventory',
                dataType: 'json',
                timeout: 10000
            }).done(function(data) {
                helpInventoryLoaded = !!data && data.status === 'ok';
                if (isResourceHelpEnabled()) renderResourceHelpInventory(data);
            }).fail(function() {
                if (isResourceHelpEnabled()) renderResourceHelpInventory(null);
            }).always(function() {
                helpInventoryRequest = false;
                if (helpInventoryPendingRefresh) {
                    helpInventoryPendingRefresh = false;
                    requestResourceHelpInventory(true);
                }
            });
        }

        function updateResourceHelpVisibility() {
            const enabled = isResourceHelpEnabled();
            const panel = $('#zapretExtraResourceHelp');
            panel.toggle(enabled);
            // Every new help opening reads the cheap CACHE again, not Git.
            if (enabled && !resourceHelpWasVisible) {
                panel.text(extrasText.loading);
                requestResourceHelpInventory(true);
            }
            resourceHelpWasVisible = enabled;
        }

        // Observe the same icon controlled by OPNsense's full-help switch,
        // including keyboard shortcuts; do not introduce a second help toggle.
        const resourceHelpIcon = document.getElementById('show_all_help_frm_GeneralSettings');
        if (resourceHelpIcon && window.MutationObserver) {
            const observer = new MutationObserver(updateResourceHelpVisibility);
            observer.observe(resourceHelpIcon, {attributes: true, attributeFilter: ['class']});
        }
        updateResourceHelpVisibility();

        function extrasLabel(data) {
            const phase = data && data.phase || 'unknown';
            const installed = data && data.installed;
            const detail = data && typeof data.detail === 'string' ? data.detail : '';

            // Active transactions and unsafe recovery must never be
            // represented as a completed installation or absence.
            switch (phase) {
                case 'downloading': return extrasText.downloading;
                case 'verifying': return extrasText.verifying;
                case 'installing': return extrasText.installing;
                case 'recovering': return extrasText.recovering;
                case 'removing': return extrasText.removing;
                case 'restore_failed': return extrasText.restoreFailed + ' · ' + extrasText.log;
                case 'recovery_required': return extrasText.review + ' · ' + extrasText.log;
                case 'failed':
                    // R1 deliberate Remove failure AFTER verified native rollback.
                    // Other installation failures retain their real error label.
                    if (installed === true && /^REMOVE_FAILED_RESTORED:/.test(detail)) {
                        return extrasText.restored;
                    }
                    return extrasText.failed + ' · ' + extrasText.log;
            }

            // The same validated inventory cache drives full Help and this
            // summary. An unknown cache is NOT "not installed".
            if (installed !== true && installed !== false) return extrasText.unavailable;
            if (phase === 'not_installed' && installed) {
                return extrasText.review + ' · ' + extrasText.log;
            }
            if (!installed) return extrasText.notInstalled;
            if (phase === 'restored') return extrasText.restored;
            if (phase === 'ready') {
                const revision = /^[a-f0-9]{40}$/.test(data.revision || '') ?
                    ' · ' + data.revision.slice(0, 12) : '';
                return extrasText.ready + ': Lua ' + (data.lua || 0) +
                    ', BIN ' + (data.bin || 0) + revision;
            }
            if (phase === 'no_recovery_needed') return extrasText.ready;
            // Unknown/foreign receipt: do not advertise Ready by inference.
            return extrasText.unavailable;
        }

        function stopExtrasPolling() {
            if (extraPoll !== null) {
                window.clearInterval(extraPoll);
                extraPoll = null;
            }
            extraPollAttempts = 0;
        }

        // A fast operation may finish without a polled busy=1 transition.
        // Match the persisted terminal receipt to this exact user click.
        function extraOperationTerminal(data, operation) {
            return !!operation && !!data && data.operation === operation &&
                !data.busy && ['ready', 'failed', 'restore_failed',
                    'recovery_required'].indexOf(data.phase) !== -1;
        }

        // Never interpret a different job's receipt as successful Remove.
        function extraRemoveTerminal(data, operation) {
            return /^[a-f0-9]{32}$/.test(operation || '') && !!data &&
                data.operation === operation && data.busy === false &&
                ['not_installed', 'ready', 'failed', 'restore_failed',
                    'recovery_required'].indexOf(data.phase) !== -1;
        }

        // Read-only dry_run_only plans intentionally have ready=false: only
        // the authenticated POST + server-side current plan can authorize mutation.
        function validExtraRemovePlan(data) {
            return !!data && data.status === 'ok' && data.ready === false &&
                Number.isInteger(data.lua) && data.lua >= 0 &&
                Number.isInteger(data.bin) && data.bin >= 0 &&
                Number.isInteger(data.total) && data.total === data.lua + data.bin &&
                /^[a-f0-9]{64}$/.test(data.inventory_sha256 || '');
        }

        function renderExtras(data) {
            if (!data || data.status !== 'ok') {
                extraStateKnown = false;
                extraNeedsReview = true;
                extraBusy = false;
                $('#zapretExtraState').text(extrasText.unavailable);
                stopExtrasPolling();
                setRuntimeBusy(runtimeWasBusy);
                return;
            }

            extraStateKnown = true;
            extraBusy = !!data.busy;
            // F5 during a confirmed native Remove: reattach only to the
            // persisted correlated worker, never issue a second mutation.
            if (!extraRemovePending && !extraInstallPending && data.phase === 'removing' &&
                data.busy === true && /^[a-f0-9]{32}$/.test(data.operation || '')) {
                extraRemovePending = true;
                extraRemoveOperation = data.operation;
            }
            if ((data.phase === 'removing' && !data.busy && !extraRemovePending) ||
                (data.phase === 'not_installed' && data.installed === true)) {
                // Inconsistent or interrupted receipt: disable mutating controls
                // until explicit review instead of treating an idle PID as success.
                extraNeedsReview = true;
            }
            if (typeof data.installed === 'boolean') {
                if (helpInventoryLoaded && helpInventoryLastInstalled !== data.installed) {
                    // A cache-backed install/removal boundary changed while
                    // Help is open. Re-read the same cache, never scan Git.
                    helpInventoryLoaded = false;
                    requestResourceHelpInventory(true);
                }
                helpInventoryLastInstalled = data.installed;
            }
            if (['restore_failed', 'recovery_required'].indexOf(data.phase) >= 0) {
                extraNeedsReview = true;
            }
            $('#zapretExtraState').text(extrasLabel(data));
            if (extraInstallPending && extraOperationTerminal(data, extraExpectedOperation)) {
                helpInventoryLoaded = false;
                requestResourceHelpInventory(true);
                extraInstallPending = false;
                extraExpectedOperation = '';
                if (data.phase !== 'ready') {
                    extraNeedsReview = true;
                }
                refreshRuntime();
            }
            if (extraRemovePending && extraRemoveTerminal(data, extraRemoveOperation)) {
                const success = data.phase === 'not_installed' &&
                    data.installed === false && data.lua === 0 && data.bin === 0;
                extraRemovePending = false;
                extraRemoveOperation = '';
                if (success) {
                    helpInventoryLoaded = false;
                    requestResourceHelpInventory(true);
                    $('#zapretExtraState').text(extrasText.removeCompleted);
                } else {
                    extraNeedsReview = true;
                    // REMOVE_FAILED_RESTORED is emitted only AFTER the
                    // original native owner and resource inodes were restored.
                    const restored = data.phase === 'failed' && data.installed === true &&
                        typeof data.detail === 'string' &&
                        /^REMOVE_FAILED_RESTORED:/.test(data.detail);
                    $('#zapretExtraState').text(restored ? extrasText.removeRestored :
                        (data.phase === 'restore_failed' ? extrasText.restoreFailed :
                            extrasText.removeFailed) + ' · ' + extrasText.log);
                }
                refreshRuntime();
            }
            if (extraNeedsReview && !extraRemovePending &&
                ['ready', 'not_installed'].indexOf(data.phase) >= 0) {
                $('#zapretExtraState').text(extrasText.review + ' · ' + extrasText.log);
            }
            if (extraInstallPending || extraRemovePending || extraBusy) {
                if (extraPoll === null) {
                    extraPollAttempts = 0;
                    extraPoll = window.setInterval(refreshExtrasStatus, 2000);
                }
            } else {
                stopExtrasPolling();
            }
            setRuntimeBusy(runtimeWasBusy);
        }

        function refreshExtrasStatus() {
            if (++extraPollAttempts > 300) {
                extraNeedsReview = true;
                extraInstallPending = false;
                extraRemovePending = false;
                extraRemoveOperation = '';
                extraBusy = false;
                stopExtrasPolling();
                $('#zapretExtraState').text(extrasText.review + ' · ' + extrasText.log);
                setRuntimeBusy(runtimeWasBusy);
                return;
            }
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesStatus',
                dataType: 'json',
                timeout: 15000
            }).done(renderExtras).fail(function() {
                extraStateKnown = false;
                if (extraRemovePending && extraRemoveOperation) {
                    // A temporary status transport failure must not lead to
                    // a second destructive request or an invented success.
                    $('#zapretExtraState').text(extrasText.removeUncertain);
                    setRuntimeBusy(runtimeWasBusy);
                    return;
                }
                extraNeedsReview = true;
                extraBusy = false;
                stopExtrasPolling();
                $('#zapretExtraState').text(extrasText.unavailable);
                setRuntimeBusy(runtimeWasBusy);
            });
        }

        $('#zapretServiceTitle').text(runtimeText.title);
        $('#zapretRepositoryReleasesLabel').text(runtimeText.repositoryReleases);

        $('#zapretServiceControl').off('click').on('click', function(event) {
            event.preventDefault();
            if (strategiesApplyPending || strategiesApplyNeedsReview || runtimeWasBusy ||
                extraBusy || extraInstallPending || extraNeedsReview ||
                (currentServiceState !== 'started' && currentServiceState !== 'stopped')) {
                return;
            }

            const button = $(this);
            const action = currentServiceState === 'started' ? 'stop' : 'start';
            button.prop('disabled', true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/' + action,
                dataType: 'json',
                timeout: 600000
            }).done(function() {
                refreshRuntime();
                updateServiceControlUI('zapret');
            }).fail(function(xhr) {
                const message = xhr && xhr.responseJSON && xhr.responseJSON.message;
                showRuntimeError(runtimeText.applyError,
                    typeof message === 'string' && message
                        ? localizeStrategiesApplyError(message) :
                    (isRussian ? 'Не удалось запустить Zapret2. Проверьте WAN интерфейс.' :
                        'Zapret2 could not be started. Check the WAN interface.'));
                refreshRuntime();
            });
        });

        $('#zapretReleaseApply').off('click').on('click', function(event) {
            event.preventDefault();
            const version = $('#zapretReleaseSelect').val();
            if (!version || runtimeWasBusy || releaseApplyPending ||
                strategiesApplyPending || strategiesApplyNeedsReview ||
                extraBusy || extraInstallPending || extraNeedsReview) {
                return;
            }

            // First install has service=error until the selected engine exists;
            // guard already-installed invalid owners, not a blank first setup.
            if ((currentRuntimeInstalled &&
                currentServiceState !== 'started' && currentServiceState !== 'stopped') ||
                releaseNeedsReview) return;
            releaseApplyPending = true;
            releaseExpectedVersion = version;
            releaseOriginalVersion = $('#zapretRuntimeVersion').text();
            releaseOriginalService = currentServiceState;
            releaseObservedBusy = false;
            releaseApplyStartedAt = Date.now();
            setRuntimeBusy(true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/install',
                data: {'version': version},
                dataType: 'json',
                timeout: 30000
            }).done(function(data) {
                // Start polling independently of whether the first status
                // response actually catches busy=1.
                ensureRuntimePolling(false);
                refreshRuntime();
                refreshReleases(data && data.version ? data.version : version);
            }).fail(function() {
                // A transport timeout may happen after dispatch. Never
                // silently unlock a potentially live second transaction.
                finishReleaseOperation(true, runtimeText.applyReview);
                ensureRuntimePolling(false);
                setRuntimeBusy(runtimeWasBusy);
                refreshRuntime();
            });
        });

        $('#zapretExtraInstallText').text(extrasText.install);
        $('#zapretExtraRemoveText').text(extrasText.remove);
        // Match the existing Install button's rendered dimensions; no new
        // bespoke CSS button size or alternative OPNsense styling.
        $('#zapretExtraRemove').css({
            width: $('#zapretExtraInstall').outerWidth() + 'px',
            height: $('#zapretExtraInstall').outerHeight() + 'px'
        });
        updateResourceAdvancedVisibility();
        $('#zapretExtraRemove').off('click').on('click', function(event) {
            event.preventDefault();
            if (!isResourceAdvancedEnabled() || !extraStateKnown ||
                extraBusy || extraInstallPending || extraRemovePending || extraNeedsReview ||
                runtimeWasBusy || releaseApplyPending || strategiesApplyPending ||
                strategiesApplyNeedsReview || currentServiceState !== 'started') return;
            extraRemovePending = true;
            extraRemoveOperation = '';
            setRuntimeBusy(runtimeWasBusy);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesRemovePlan',
                dataType: 'json',
                timeout: 130000
            }).done(function(plan) {
                if (!validExtraRemovePlan(plan)) {
                    extraRemovePending = false;
                    showRuntimeError(extrasText.removePlanTitle, extrasText.removePlanError);
                    return;
                }
                if (plan.total === 0) {
                    extraRemovePending = false;
                    BootstrapDialog.show({
                        type: BootstrapDialog.TYPE_INFO,
                        title: extrasText.removePlanTitle,
                        message: $('<div/>').text(extrasText.removeNoop),
                        buttons: [{
                            label: '{{ lang._("Close") }}',
                            action: function(dialog) { dialog.close(); }
                        }]
                    });
                    return;
                }
                const phrase = 'REMOVE ' + plan.total;
                const message = $('<div/>');
                $('<p/>').text(extrasText.removePlanInfo +
                    'Lua: ' + plan.lua + ', BIN: ' + plan.bin + '.').appendTo(message);
                $('<p/>').text(extrasText.removeWarning + phrase).appendTo(message);
                const confirmation = $('<input/>', {
                    type: 'text', 'class': 'form-control',
                    autocomplete: 'off', spellcheck: 'false',
                    'aria-label': phrase
                }).appendTo(message);
                let submitted = false;
                BootstrapDialog.show({
                    type: BootstrapDialog.TYPE_WARNING,
                    title: extrasText.removePlanTitle,
                    message: message,
                    closable: true,
                    onshown: function(dialog) {
                        const approve = dialog.getButton('zapretConfirmRemove');
                        approve.prop('disabled', true);
                        confirmation.on('input', function() {
                            approve.prop('disabled', confirmation.val() !== phrase);
                        }).trigger('focus');
                    },
                    onhide: function() {
                        if (!submitted) {
                            extraRemovePending = false;
                            setRuntimeBusy(runtimeWasBusy);
                        }
                    },
                    buttons: [{
                        label: extrasText.removeCancel,
                        action: function(dialog) { dialog.close(); }
                    }, {
                        id: 'zapretConfirmRemove',
                        label: extrasText.removeConfirm,
                        cssClass: 'btn-danger',
                        action: function(dialog) {
                            if (submitted || confirmation.val() !== phrase ||
                                !isResourceAdvancedEnabled() || extraNeedsReview) return;
                            submitted = true;
                            dialog.close();
                            // Exactly one authenticated POST. Any lost reply
                            // is ambiguous; never auto-resubmit the mutation.
                            $.ajax({
                                type: 'POST',
                                url: '/api/zapret/service/resourcesRemove',
                                data: {
                                    inventory_sha256: plan.inventory_sha256,
                                    confirmation: phrase
                                },
                                dataType: 'json',
                                timeout: 35000
                            }).done(function(receipt) {
                                if (receipt && ['ok', 'uncertain'].indexOf(receipt.status) >= 0 &&
                                    /^[a-f0-9]{32}$/.test(receipt.operation || '') &&
                                    (receipt.status !== 'ok' || receipt.started === true)) {
                                    extraRemoveOperation = receipt.operation;
                                    $('#zapretExtraState').text(extrasText.removing);
                                    refreshExtrasStatus();
                                    return;
                                }
                                extraRemovePending = false;
                                if (receipt && receipt.status === 'rejected' &&
                                    receipt.started === false) {
                                    showRuntimeError(extrasText.removePlanTitle, extrasText.removeRejected);
                                } else if (receipt && receipt.status === 'unavailable' &&
                                    receipt.started === false) {
                                    showRuntimeError(extrasText.removePlanTitle, extrasText.removePlanError);
                                } else {
                                    extraNeedsReview = true;
                                    $('#zapretExtraState').text(extrasText.removeUncertain);
                                }
                                refreshExtrasStatus();
                            }).fail(function() {
                                // No operation ID: we cannot prove it did not start.
                                extraRemovePending = false;
                                extraNeedsReview = true;
                                $('#zapretExtraState').text(extrasText.removeUncertain);
                                refreshRuntime();
                                setRuntimeBusy(runtimeWasBusy);
                            });
                        }
                    }]
                });
            }).fail(function() {
                extraRemovePending = false;
                showRuntimeError(extrasText.removePlanTitle, extrasText.removePlanError);
            }).always(function() {
                setRuntimeBusy(runtimeWasBusy);
            });
        });
        $('#zapretExtraState').text(extrasText.notInstalled);
        $('#zapretExtraInstall').off('click').on('click', function(event) {
            event.preventDefault();
            if (!extraStateKnown || extraBusy || extraInstallPending || extraNeedsReview ||
                runtimeWasBusy || releaseApplyPending || strategiesApplyPending ||
                strategiesApplyNeedsReview || currentServiceState !== 'started') {
                return;
            }
            extraInstallPending = true;
            extraExpectedOperation = '';
            setRuntimeBusy(true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesInstall',
                dataType: 'json',
                timeout: 30000
            }).done(function(data) {
                if (!data || data.status !== 'ok' || !data.started ||
                    !/^[a-f0-9]{32}$/.test(data.operation || '')) {
                    extraNeedsReview = true;
                    extraInstallPending = false;
                    $('#zapretExtraState').text(extrasText.failed);
                } else {
                    extraExpectedOperation = data.operation;
                }
                refreshExtrasStatus();
            }).fail(function() {
                extraInstallPending = false;
                extraExpectedOperation = '';
                extraNeedsReview = true;
                $('#zapretExtraState').text(extrasText.failed + ' · ' + extrasText.log);
                refreshRuntime();
            });
        });

        reloadSettings();
        refreshRuntime();
        refreshReleases();
        refreshExtrasStatus();

        // One original-FD9 Apply, same result handling as Voice. A network
        // timeout is not proof that native Config/runtime/IPFW were untouched.
        $("#reconfigureAct").off('click').on('click', function(event) {
            event.preventDefault();
            if (strategiesApplyPending || strategiesApplyNeedsReview ||
                extraBusy || extraInstallPending || extraNeedsReview || runtimeWasBusy ||
                releaseApplyPending) return;
            strategiesApplyPending = true;
            reconcileStrategiesApplyControls();

            function finishApply() {
                strategiesApplyPending = false;
                reconcileStrategiesApplyControls();
                updateServiceControlUI('zapret');
                refreshRuntime();
            }
            function needsReview() {
                strategiesApplyNeedsReview = true;
                showRuntimeError(runtimeText.applyError, runtimeText.applyReview);
            }

            $.ajax({
                type: 'POST',
                url: '/api/zapret/settings/apply',
                data: getFormData('frm_GeneralSettings'),
                dataType: 'json',
                // Native configdpRun may run for 600s. A short default
                // timeout must not invite another Apply during that worker.
                timeout: 630000
            }).done(function(data) {
                handleFormValidation('frm_GeneralSettings',
                    localizeStrategiesFieldErrors((data && data.validations) || {}));
                if (data && data.result === 'saved' && data.status === 'ok') {
                    reloadSettings().done(function() {
                        if (data.normalized && Array.isArray(data.normalization)) {
                            BootstrapDialog.show({
                                type: BootstrapDialog.TYPE_INFO,
                                title: isRussian ? 'Настройки нормализованы' : '{{ lang._("Settings normalized") }}',
                                message: $('<div/>').text(localizeStrategiesNormalizationSummary(data.normalization).join('\n'))
                                    .css('white-space', 'pre-line'),
                                buttons: [{
                                    label: '{{ lang._("Close") }}',
                                    action: function(dialog) { dialog.close(); }
                                }]
                            });
                        }
                    }).fail(function() {
                        // Applied, but our original Telegram baseline could
                        // not be refreshed. Do not retry from a stale form.
                        needsReview();
                    }).always(finishApply);
                } else {
                    if (!data || data.result !== 'failed' ||
                        data.requires_review === true) {
                        needsReview();
                    } else if (typeof data.message === 'string' && data.message) {
                        // Only explicitly rejected, pre-dispatch errors are
                        // editable without a new Config snapshot.
                        showRuntimeError(runtimeText.applyError,
                            localizeStrategiesApplyError(data.message, data.reason));
                    }
                    finishApply();
                }
            }).fail(function() {
                needsReview();
                finishApply();
            });
        });

        updateServiceControlUI('zapret');
    });
</script>

<style>
    /* The native help toggle must not create a duplicate third-column help
       for Exclude IPSet. The inline .help-block under its textarea remains
       visible, matching Exclude Domains in RU and EN. */
    #frm_GeneralSettings tr.zapret-exclude-ipset-inline-help-only > td:nth-child(3) {
        visibility: hidden !important;
    }
    #zapretExtraResourceHelp { padding: 12px 4px 4px; }
    .zapret-resource-legend { display: flex; flex-wrap: wrap; gap: 6px 24px; margin-bottom: 12px; }
    .zapret-resource-columns { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; }
    .zapret-resource-column { min-width: 0; }
    .zapret-resource-list { max-height: 360px; overflow-y: auto; margin-top: 8px; }
    .zapret-resource-list li { overflow-wrap: anywhere; line-height: 1.6; }
    @media (max-width: 700px) {
        .zapret-resource-columns { grid-template-columns: minmax(0, 1fr); }
    }
    #zapretServiceLine {
        display: grid;
        grid-template-columns: max-content max-content 14ch 12ch 4ch max-content minmax(130px, 150px) max-content;
        align-items: center;
        column-gap: 8px;
        min-height: 34px;
        min-width: max-content;
        white-space: nowrap;
    }

    #zapretRuntimeVersion {
        display: inline-block;
        width: 14ch;
    }

    #zapretServiceControlSlot {
        display: inline-block;
        width: 12ch;
    }

    #zapretServiceControl {
        min-width: 12ch;
    }

    #zapretServiceLine .zapret-service-spacer {
        display: inline-block;
        width: 4ch;
    }

    #zapretReleaseSelect {
        width: 150px;
        min-width: 130px;
    }
</style>

<div class="content-box __mb">
    {{ partial("layout_partials/base_form",['fields':generalForm,'id':'frm_GeneralSettings']) }}

    <div class="table-responsive">
        <table class="table table-striped table-condensed" style="table-layout: fixed; width: 100%; margin-bottom: 0;">
            <colgroup>
                <col style="width: 25%;" />
                <col style="width: 40%;" />
                <col style="width: 35%;" />
            </colgroup>
            <thead id="zapretServiceHeader" style="cursor: pointer;">
                <tr>
                    <th colspan="3">
                        <div style="padding-bottom: 5px; padding-top: 5px; font-size: 16px;">
                            <i id="zapretServiceCollapseIcon" class="fa fa-angle-down" aria-hidden="true"></i>
                            &nbsp;
                            <b id="zapretServiceTitle">Zapret2 Service</b>
                        </div>
                    </th>
                </tr>
            </thead>
            <tbody id="zapretServiceBody" class="collapsible">
                <tr>
                    <td colspan="3">
                        <div id="zapretServiceLine">
                            <b>{{ lang._("Status") }}:</b>
                            <span id="zapretServiceStatus" class="label label-danger">{{ lang._("Error") }}</span>
                            <strong id="zapretRuntimeVersion">—</strong>
                            <span id="zapretServiceControlSlot">
                                <button class="btn btn-default" id="zapretServiceControl" type="button" disabled style="display: none;">
                                    {{ lang._("Start") }}
                                </button>
                            </span>
                            <span class="zapret-service-spacer" aria-hidden="true"></span>
                            <label id="zapretRepositoryReleasesLabel" for="zapretReleaseSelect" style="margin-bottom: 0;">
                                Repository Releases
                            </label>
                            <select class="form-control" id="zapretReleaseSelect" disabled>
                                <option value="">Loading…</option>
                            </select>
                            <button class="btn btn-primary" id="zapretReleaseApply" type="button" disabled>
                                <span id="zapretReleaseApplyText">{{ lang._("Apply") }}</span>
                                <i id="zapretReleaseApplyProgress"></i>
                            </button>
                        </div>
                    </td>
                </tr>
                <tr>
                    <td colspan="3">
                        <div id="zapretExtraResourcesLine" style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                            <button class="btn btn-default" id="zapretExtraInstall" type="button" disabled>
                                <span id="zapretExtraInstallText">Install Additional Resources</span>
                                <i id="zapretExtraProgress"></i>
                            </button>
                            <span id="zapretExtraState" role="status" aria-live="polite"></span>
                        </div>
                        <div id="zapretExtraRemoveRow" style="display:none; margin-top:8px;">
                            <button class="btn btn-default text-info" id="zapretExtraRemove" type="button" disabled>
                                <span id="zapretExtraRemoveText">Remove Additional Resources</span>
                                <i id="zapretExtraRemoveProgress"></i>
                            </button>
                        </div>
                        <div id="zapretExtraResourceHelp" style="display:none;" aria-live="polite"></div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
<section class="grid-bottom-reserve __mt">
    <div class="alert content-box" style="display: flex; align-items: center; margin-bottom: 0;">
        <button
            class="btn btn-primary __mr"
            id="reconfigureAct"
            type="button">
            {{ lang._("Apply") }} <i id="reconfigureActProgress"></i>
        </button>
    </div>
</section>
