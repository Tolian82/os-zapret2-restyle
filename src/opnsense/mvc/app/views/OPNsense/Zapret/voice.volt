{# The original Voice GUI uses the common Strategies/Voice Apply for both ON and OFF. #}
<script>
$(document).ready(function () {
    "use strict";
    var isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
    var ru = isRussian;
    var text = ru ? {
        navStrategy: 'Стратегии', navVoice: 'Передача голоса', navLab: 'Лаборатория',
        general: 'Основные настройки', wan: 'Интерфейс WAN для голоса',
        infoTitle: 'Как работают голосовые профили',
        infoText: 'UDP/STUN-профили пяти сервисов используют общий движок Zapret2 и штатную операцию Apply вместе со «Стратегиями». «Применить» сохраняет настройки и переключает runtime/IPFW с проверяемым возвратом при ошибке. «Сохранить черновик» доступно только для выключенных профилей и не перезапускает службу. Работающий старый Telegram PoC требует отдельной миграции. Non-STUN остаётся в «Стратегиях».',
        parameters: 'Параметры передачи голоса', destinations: 'IP-адреса назначения',
        service: 'Служба Zapret2', apply: 'Применить', validate: 'Проверить', saveDraft: 'Сохранить черновик', applied: 'Настройки сохранены и применены к общему движку Zapret2', applyFailed: 'Применение не подтверждено — проверьте ошибки и состояние службы', applyReview: 'Результат применения неизвестен. Проверьте состояние службы и восстановление перед повторной попыткой; обновите страницу.', draftSaved: 'Черновик сохранён, без применения к службе', draftFailed: 'Черновик не сохранён', checkOk: 'Синтаксис проверен (без применения)', previewDraft: 'Проверить сохранённый черновик', previewOk: 'Черновики проверены под блокировкой службы; изменения не применены', previewFailed: 'Черновики должны быть сначала сохранены выключенными; проверьте настройки', checkFailed: 'Исправьте отмеченные поля', checkError: 'Проверка недоступна', start: 'Запустить', stop: 'Остановить', repositoryReleases: 'Релизы репозитория',
        notice: 'Кнопка «Применить» использует единый native Apply для включённых и выключенных профилей, с проверкой Config, runtime и IPFW. «Сохранить черновик» сохраняет только выключенные профили без переключения службы. При незавершённом применении или работающем старом Telegram PoC требуется проверка состояния; не запускайте повторное применение вслепую.',
        status: 'Статус', running: 'Запущена', stopped: 'Остановлена', error: 'Ошибка',
        loading: 'Загрузка…', incomplete: 'Неизвестно',
        recoveryTitle: 'Восстановление старого Telegram PoC',
        recoveryAbsent: 'Журнал старого PoC отсутствует — восстановление не подтверждено',
        recoveryOther: 'Обнаружен другой журнал Voice — проверьте его отдельно',
        recoveryIncomplete: 'Незавершённое восстановление — нужна ручная проверка',
        recoveryReceipt: 'Диск проверен — после загрузки проверьте IPFW и процессы',
        recoveryUnknown: 'Статус восстановления недоступен — применение заблокировано',
        ipfwStatus: 'IPFW — передача голоса', ipfwReady: 'Общий движок и правила подтверждены', ipfwStopped: 'Общая служба остановлена, IPFW очищен',
        ipfwEmpty: 'Новая Voice-конфигурация не активирована', ipfwInterrupted: 'Незавершённое применение',
        ipfwBlocked: 'Требуется проверка правил', ipfwUnknown: 'Статус недоступен',
        cutoverPrepared: 'Незавершённая подготовка — проверьте прежнее состояние',
        cutoverMutating: 'Прервано переключение — требуется проверка служб и IPFW',
        cutoverCommitted: 'Переключение зафиксировано — проверьте завершение очистки',
        wanHelp: 'Исходящий WAN для перехвата голосового UDP. Пустое значение наследует WAN страницы «Стратегии». Выбор WAN не меняет маршруты.',
        enableHelp: 'Включённый STUN-профиль применяется общей кнопкой «Применить». Для «Сохранить черновик» все голосовые профили должны быть выключены. Параметры и IPSET сохраняются при выключении.',
        argsHelp: 'Один нативный STUN-профиль dvtws2: <code>--filter-udp</code>, <code>--filter-l7=stun</code>, <code>--payload=stun</code> и необязательные действия <code>--lua-desync</code>. Имя профиля и IPSET задаёт плагин. Не вводите <code>--new</code>, TCP или команды shell. Это не означает, что звонок заработает.',
        ipHelp: 'Общий со «Стратегиями» IPSET. Один IPv4-адрес или CIDR в строке. Пустой список нельзя применять при включённой службе; нет автоматической замены на любой адрес.'
    } : {
        navStrategy: 'Strategies', navVoice: 'Voice Transmission', navLab: 'Laboratory',
        general: 'General Settings', wan: 'Voice WAN Interface',
        infoTitle: 'About Voice Profiles',
        infoText: 'Five UDP/STUN profiles share the existing Zapret2 engine and the native Strategies/Voice Apply transaction. Apply saves settings and switches runtime/IPFW with verified rollback on failure. Save inactive draft only stores disabled profiles without restarting the service. An active old Telegram PoC requires a separate migration. Non-STUN remains in Strategies.',
        parameters: 'Voice Transmission Parameters', destinations: 'Destination IP Addresses',
        service: 'Zapret2 Service', apply: 'Apply', validate: 'Validate', saveDraft: 'Save inactive draft', applied: 'Settings saved and applied to the shared Zapret2 engine', applyFailed: 'Apply not confirmed — review validation and current service state', applyReview: 'Apply result is uncertain. Inspect service and recovery status before retrying; reload this page.', draftSaved: 'Draft saved to Config; runtime unchanged', draftFailed: 'Draft was not saved', checkOk: 'Syntax checked (not applied)', previewDraft: 'Preview saved Voice drafts', previewOk: 'Saved drafts checked under service lock; no changes applied', previewFailed: 'Save disabled Voice drafts before preview; check the settings', checkFailed: 'Correct highlighted fields', checkError: 'Validation unavailable', start: 'Start', stop: 'Stop', repositoryReleases: 'Repository Releases',
        notice: 'Apply uses the single native transaction for enabled and disabled Voice profiles, checking Config, runtime and IPFW. Save inactive draft only persists disabled profiles without restarting the service. If Apply was interrupted or the old Telegram PoC is running, inspect the actual state before retrying.',
        status: 'Status', running: 'Started', stopped: 'Stopped', error: 'Error',
        loading: 'Loading…', incomplete: 'Unknown',
        recoveryTitle: 'Previous Telegram PoC recovery',
        recoveryAbsent: 'No old PoC journal — recovery not established',
        recoveryOther: 'Another Voice journal exists — review it separately',
        recoveryIncomplete: 'Incomplete recovery — manual review required',
        recoveryReceipt: 'Disk proof verified — verify IPFW and processes after boot',
        recoveryUnknown: 'Recovery status unavailable — activation blocked',
        ipfwStatus: 'Voice IPFW', ipfwReady: 'Shared engine and IPFW verified', ipfwStopped: 'Shared service stopped; IPFW cleared',
        ipfwEmpty: 'New Voice configuration not activated', ipfwInterrupted: 'Interrupted apply',
        ipfwBlocked: 'Firewall review required', ipfwUnknown: 'Status unavailable',
        cutoverPrepared: 'Interrupted preparation — verify previous runtime',
        cutoverMutating: 'Interrupted cutover — inspect services and IPFW',
        cutoverCommitted: 'Cutover committed — verify cleanup completion',
        wanHelp: 'Outgoing WAN used for voice UDP interception. Empty selection inherits Strategies WAN. WAN selection does not change routing.',
        enableHelp: 'Enabled STUN profiles use the shared Apply button. Save inactive draft requires all Voice profiles to be OFF. Disabled services retain their parameters and destinations.',
        argsHelp: 'One native dvtws2 STUN profile: <code>--filter-udp</code>, <code>--filter-l7=stun</code>, <code>--payload=stun</code> and optional <code>--lua-desync</code> actions. The plugin supplies profile identity and IPSET. Do not enter <code>--new</code>, TCP options or shell commands. This is not proof of working calls.',
        ipHelp: 'Shared IPSET, available in Strategies. One IPv4 address or CIDR per line. Empty sets must not be enabled or implicitly match any destination.'
    };
    // Validation messages arrive as a fixed, trusted server-side English
    // allowlist. Translate their meaning without replacing native form/help DOM
    // or touching the user's configuration. Unknown error text stays intact.
    function localizeVoiceErrors(errors) {
        if (!ru || !errors || typeof errors !== 'object') return errors || {};
        var fixed = {
            'IPv4/CIDR list is too large': 'Список IPv4/CIDR слишком большой',
            'Too many destination addresses': 'Слишком много адресов назначения',
            'UDP ports must be numeric intervals or *': 'Порты UDP должны быть числами, диапазонами или *',
            'Invalid UDP port selector': 'Некорректный выбор UDP-портов',
            'UDP port is outside 1–65535': 'UDP-порт вне диапазона 1–65535',
            'Only the native fake Lua action is currently supported': 'Пока поддерживается только нативное Lua-действие fake',
            'Fake blob must be whole bytes of 0xHEX': 'Поддельные данные должны состоять из целых байтов 0xHEX',
            'Fake repeats must be 1–10': 'Количество повторов fake — от 1 до 10',
            'Fake TTL must be 1–255': 'TTL fake — от 1 до 255',
            'UDP fake fragment offset must be a multiple of 8': 'Смещение UDP-фрагмента fake должно быть кратно 8',
            'Invalid fake option flag': 'Некорректный флаг параметра fake',
            'Unverified native fake option': 'Неподтверждённый нативный параметр fake',
            'Missing fake blob or invalid fragmentation combination': 'Нет данных fake или недопустимое сочетание фрагментации',
            'STUN parameters are too long': 'Параметры STUN слишком длинные',
            'Only single-token native ASCII arguments are permitted': 'Допускаются только одиночные нативные аргументы ASCII',
            'Only native STUN filtering is allowed': 'Допускается только нативная фильтрация STUN',
            'Unsupported UDP out-range selector': 'Неподдерживаемое значение UDP out-range',
            'Unexpected Voice form fields': 'В запросе есть посторонние поля',
            'Voice settings and IPSET fields are required': 'Требуются настройки голоса и поля IPSET',
            'Invalid Voice WAN selection': 'Некорректный выбор голосового WAN',
            'Service checkbox and parameters are required': 'Требуются переключатель службы и параметры',
            'IPSET must be a text list': 'IPSET должен быть текстовым списком',
            'Enabled Voice service requires destination IPs': 'Для включённой службы нужны IP-адреса назначения',
            'Voice validation failed': 'Проверка параметров голоса завершилась ошибкой',
            'Voice draft could not be saved': 'Не удалось сохранить черновик передачи голоса',
            'Native Voice ON still needs the shared IPFW cutover; apply only OFF profiles': 'Включение голосовых профилей ещё не готово; применять можно только выключенные',
            'Zapret lifecycle is busy; retry after diagnostics finish': 'Служба занята лабораторией — дождитесь завершения диагностики',
            'Zapret lifecycle became busy before applying': 'Служба занята — применение отменено до сохранения',
            'Settings saved, but Zapret reconfigure failed; inspect current runtime before retrying': 'Настройки сохранены, но перезапуск Zapret2 завершился ошибкой; проверьте фактическое состояние службы',
            'Voice activation is not available yet; save only disabled service drafts': 'Применение голоса пока недоступно; сохраните черновик с выключенными сервисами',
            'Strategies WAN must be configured before Voice': 'Сначала настройте WAN на странице «Стратегии».',
            'Independent Voice WAN cannot be isolated by the shared engine yet; select the Strategies WAN': 'Отдельный WAN для голоса пока нельзя изолировать в общем движке. Выберите WAN из страницы «Стратегии».',
            'Missing Voice form': 'Не получена форма передачи голоса',
            'Voice configuration baseline is missing. Reload the Voice page.': 'Нет исходной версии настроек. Обновите страницу передачи голоса.',
            'Voice or shared Strategies settings changed in another tab. Reload the Voice page.': 'Параметры передачи голоса или общие настройки стратегий были изменены в другой вкладке. Обновите страницу.',
            'POST request required': 'Требуется запрос POST',
            'Enable Zapret2 before preparing saved Voice drafts': 'Включите Zapret2 перед проверкой сохранённых голосовых профилей',
            'Existing native Voice ON cannot be prepared from inactive drafts': 'Активированный профиль нельзя проверить как выключенный черновик',
            'Invalid saved Voice selection': 'Некорректный выбор голосового профиля',
            'Select at least one Voice service to preview': 'Выберите хотя бы один голосовой профиль для проверки',
            'Save inactive Voice parameters and IPSET changes before native preview': 'Сначала сохраните параметры голоса и IPSET с выключенными профилями',
            'Saved native Voice preview unavailable': 'Предпросмотр сохранённых голосовых профилей недоступен',
            'Saved Voice drafts or Config generation changed; reload and retry': 'Черновики или конфигурация изменились; обновите страницу и повторите проверку'
        };
        var dynamic = [
            [/^Invalid IPv4\/CIDR at line ([0-9]+)$/, 'Некорректный IPv4/CIDR в строке $1'],
            [/^CIDR contains host bits at line ([0-9]+)$/, 'В CIDR заданы биты хоста в строке $1'],
            [/^Duplicate fake option: ([A-Za-z0-9_]+)$/, 'Повторяется параметр fake: $1'],
            [/^Repeated (--[a-z0-9-]+) at line ([0-9]+)$/, 'Повторяется $1 в строке $2'],
            [/^Forbidden or unverified dvtws2 parameter at line ([0-9]+)$/, 'Запрещённый или неподтверждённый параметр dvtws2 в строке $1'],
            [/^Required native STUN option missing: (--[a-z0-9-]+)$/, 'Отсутствует обязательный параметр STUN: $1'],
            [/^UDP ports and destinations overlap with (telegram|discord|x|sip|custom)$/, 'UDP-порты и адреса пересекаются с профилем $1']
        ];
        var result = {};
        Object.keys(errors).forEach(function (key) {
            var message = errors[key];
            if (typeof message !== 'string') { result[key] = message; return; }
            if (Object.prototype.hasOwnProperty.call(fixed, message)) {
                result[key] = fixed[message];
                return;
            }
            result[key] = message;
            for (var i = 0; i < dynamic.length; i++) {
                if (dynamic[i][0].test(message)) {
                    result[key] = message.replace(dynamic[i][0], dynamic[i][1]);
                    break;
                }
            }
        });
        return result;
    }

    var names = {telegram:'Telegram', discord:'Discord', x:'X (Twitter)', sip:'SIP (VoIP)', custom:'Custom'};
    function localizeForm() {
        var form = $('#frm_VoiceSettings');
        var titles = {
            'General Settings': text.general,
            'Voice WAN Interface': text.wan,
            'Voice Transmission Parameters': text.parameters,
            'About Voice Profiles': text.infoTitle,
            'Destination IP Addresses': text.destinations
        };
        // Use exact original text rather than translating arbitrarily sized
        // containers: preserve form labels, help icons and native OPNsense chrome.
        form.find('label,th,h3,b,legend').each(function () {
            var element = $(this);
            var original = $.trim(element.text());
            if (Object.prototype.hasOwnProperty.call(titles, original)) {
                element.contents().filter(function () { return this.nodeType === 3; })
                    .each(function () { this.textContent = this.textContent.replace(original, titles[original]); });
            }
        });
        Object.keys(names).forEach(function (key) {
            var id = 'zapret.voice.' + key + '.args';
            var input = document.getElementById(id) || document.getElementById(id.replace(/\./g, '_'));
            if (!input) return;
            var label = $(input).closest('tr').find('label').first();
            var original = names[key] + ' Parameters';
            var translated = names[key] + (ru ? ' — параметры' : ' Parameters');
            // Replacing the label's entire HTML would destroy native help icons.
            label.find('*').addBack().contents().filter(function () {
                return this.nodeType === 3 && this.textContent.indexOf(original) !== -1;
            }).each(function () {
                this.textContent = this.textContent.replace(original, translated);
            });
        });
        form.find('tr').each(function () {
            var row = $(this);
            if (row.text().indexOf('This page configures outgoing STUN') !== -1) {
                var info = row.find('td').last();
                if (info.length) info.text(text.infoText);
            }
            var field = row.find('input,textarea,select').first();
            var id = (field.attr('id') || '').replace(/_/g, '.');
            var help = row.find('.help-block').first();
            if (!help.length) return;
            if (id === 'zapret.voice.waninterface') help.text(text.wanHelp);
            else if (/^zapret\.voice\.[^.]+\.enabled$/.test(id)) help.text(text.enableHelp);
            else if (/^zapret\.voice\.[^.]+\.args$/.test(id)) help.html(text.argsHelp);
            else if (/^zapret\.hostlist\.(telegram|discord|x|sip|custom)ips$/.test(id)) help.html(text.ipHelp);
        });
    }
    $('a[href="/ui/zapret"]').text(text.navStrategy);
    $('a[href="/ui/zapret/voice"]').text(text.navVoice);
    $('a[href="/ui/zapret/diagnostics"]').text(text.navLab);
    $('#voiceServiceTitle').text(text.service);
    $('#voiceStatusLabel').text(text.status + ':');
    $('#voiceRecoveryLabel').text(text.recoveryTitle + ':');
    // This value comes from the same locked config.xml snapshot as the form
    // itself. Keep Validate disabled until that paired read succeeds.
    var voiceSnapshot = $('<input/>', {
        type: 'hidden', id: 'zapret.sync.snapshot'
    });
    $('#frm_VoiceSettings').append(voiceSnapshot);
    $('#voiceValidate').text(text.validate).prop('disabled', true);
    $('#voicePreviewDraft').text(text.previewDraft).prop('disabled', true);
    $('#voiceSaveDraft').text(text.saveDraft).prop('disabled', true);
    $('#voiceApply').text(text.apply).prop('disabled', true);
    $('#voiceValidate').on('click', function () {
        var button = $(this);
        if (button.prop('disabled')) return;
        button.prop('disabled', true);
        $('#voiceValidationStatus').text(text.loading);
        $.ajax({
            type: 'POST',
            url: '/api/zapret/voice/validate',
            data: getFormData('frm_VoiceSettings'),
            dataType: 'json',
            timeout: 30000
        }).done(function (reply) {
            handleFormValidation('frm_VoiceSettings', localizeVoiceErrors((reply && reply.validations) || {}));
            if (reply && reply.result === 'validated') {
                $('#voiceValidationStatus').text(text.checkOk);
            } else {
                $('#voiceValidationStatus').text(text.checkFailed);
            }
        }).fail(function () {
            $('#voiceValidationStatus').text(text.checkError);
        }).always(function () {
            button.prop('disabled', false);
        });
    });
    // This is an actual read-only native preflight behind the existing
    // Zapret lifecycle FD9 and original Config flock. It NEVER invokes the
    // stateful PREPARED producer or changes Config, dvtws2 or IPFW.
    $('#voicePreviewDraft').on('click', function () {
        var button = $(this);
        if (button.prop('disabled')) return;
        button.prop('disabled', true);
        $('#voiceValidationStatus').text(text.loading);
        $.ajax({
            type: 'POST',
            url: '/api/zapret/voice/previewDraft',
            data: getFormData('frm_VoiceSettings'),
            dataType: 'json',
            timeout: 45000
        }).done(function (reply) {
            handleFormValidation('frm_VoiceSettings', localizeVoiceErrors(
                (reply && reply.validations) || {}
            ));
            if (reply && reply.result === 'previewed' &&
                reply.saved === false && reply.prepared === false &&
                reply.applied === false && Number.isInteger(reply.selected_profiles) &&
                reply.selected_profiles >= 1 && reply.selected_profiles <= 5 &&
                typeof reply.candidate_xml_sha256 === 'string' &&
                /^[a-f0-9]{64}$/.test(reply.candidate_xml_sha256)) {
                $('#voiceValidationStatus').text(text.previewOk);
            } else {
                $('#voiceValidationStatus').text(text.previewFailed);
            }
        }).fail(function () {
            $('#voiceValidationStatus').text(text.previewFailed);
        }).always(function () {
            button.prop('disabled', !/^[a-f0-9]{64}$/.test(voiceSnapshot.val() || ''));
        });
    });
    $('#voiceSaveDraft').on('click', function () {
        var button = $(this);
        if (button.prop('disabled')) return;
        button.prop('disabled', true);
        $('#voiceValidationStatus').text(text.loading);
        $.ajax({
            type: 'POST',
            url: '/api/zapret/voice/saveDraft',
            data: getFormData('frm_VoiceSettings'),
            dataType: 'json',
            timeout: 30000
        }).done(function (reply) {
            handleFormValidation('frm_VoiceSettings', localizeVoiceErrors((reply && reply.validations) || {}));
            if (reply && reply.result === 'saved' && reply.applied === false &&
                typeof reply.snapshot === 'string' && /^[a-f0-9]{64}$/.test(reply.snapshot)) {
                // Keep the same browser tab editable after a successful write.
                // On a conflict, do not advance the token or erase user edits.
                voiceSnapshot.val(reply.snapshot);
                $('#voiceValidationStatus').text(text.draftSaved);
            } else {
                $('#voiceValidationStatus').text(text.draftFailed);
            }
        }).fail(function () {
            $('#voiceValidationStatus').text(text.draftFailed);
        }).always(function () {
            button.prop('disabled', !/^[a-f0-9]{64}$/.test(voiceSnapshot.val() || ''));
        });
    });
    // A timeout or an explicit requires_review can mean the root worker is
    // still mutating or retained crash evidence. Do not offer blind retries.
    var voiceApplyNeedsReview = false;
    $('#voiceApply').on('click', function () {
        var button = $(this);
        if (button.prop('disabled')) return;
        button.prop('disabled', true);
        $('#voiceValidationStatus').text(text.loading);
        $.ajax({
            type: 'POST',
            url: '/api/zapret/voice/apply',
            data: getFormData('frm_VoiceSettings'),
            dataType: 'json',
            // configdpRun permits 600s; a shorter browser deadline must
            // never invite a second Apply while the original still runs.
            timeout: 630000
        }).done(function (reply) {
            handleFormValidation('frm_VoiceSettings', localizeVoiceErrors((reply && reply.validations) || {}));
            if (reply && reply.saved === true && typeof reply.snapshot === 'string' &&
                /^[a-f0-9]{64}$/.test(reply.snapshot)) {
                // The failed backend apply may already have saved Config.
                // Refresh the concurrency token without pretending Apply succeeded.
                voiceSnapshot.val(reply.snapshot);
            }
            if (reply && reply.result === 'saved' && reply.applied === true &&
                typeof reply.snapshot === 'string' && /^[a-f0-9]{64}$/.test(reply.snapshot)) {
                voiceSnapshot.val(reply.snapshot);
                $('#voiceValidationStatus').text(text.applied);
                refreshRuntime();
                refreshVoiceIPFW();
            } else if (reply && reply.requires_review === true) {
                voiceApplyNeedsReview = true;
                $('#voiceValidationStatus').text(text.applyReview);
                refreshRuntime();
                refreshVoiceIPFW();
            } else {
                $('#voiceValidationStatus').text(text.applyFailed);
            }
        }).fail(function () {
            voiceApplyNeedsReview = true;
            $('#voiceValidationStatus').text(text.applyReview);
            refreshRuntime();
            refreshVoiceIPFW();
        }).always(function () {
            button.prop('disabled', voiceApplyNeedsReview ||
                !/^[a-f0-9]{64}$/.test(voiceSnapshot.val() || ''));
        });
    });
    $('#voiceImplementationNotice').text(text.notice);
    $('#voiceIPFWLabel').text(text.ipfwStatus + ':');
    localizeForm();
    mapDataToFormUI({'frm_VoiceSettings':'/api/zapret/voice/load'}).done(function (loaded) {
        var record = loaded && loaded['frm_VoiceSettings'];
        if (record && typeof record.snapshot === 'string' &&
            /^[a-f0-9]{64}$/.test(record.snapshot)) {
            voiceSnapshot.val(record.snapshot);
            $('#voiceValidate').prop('disabled', false);
            $('#voicePreviewDraft').prop('disabled', false);
            $('#voiceSaveDraft').prop('disabled', false);
            $('#voiceApply').prop('disabled', false);
        } else {
            $('#voiceValidationStatus').text(text.checkError);
        }
        formatTokenizersUI();
        $('.selectpicker').selectpicker('refresh');
        localizeForm();
    });
    var runtimeState = 'error', runtimeInstalled = false, runtimeBusy = false;
    function setServiceControlsBusy(busy) {
        runtimeBusy = busy;
        var controllable = runtimeInstalled && (runtimeState === 'started' || runtimeState === 'stopped');
        $('#voiceServiceControl').prop('disabled', busy || !controllable);
        var releasesAvailable = $('#voiceReleaseSelect option').filter(function () {
            return /^v[0-9]+(?:\.[0-9]+)+$/.test(this.value);
        }).length > 0;
        $('#voiceReleaseSelect,#voiceReleaseApply').prop('disabled', busy || !releasesAvailable);
    }
    function refreshRuntime() {
        return $.ajax({type:'POST', url:'/api/zapret/service/runtime', dataType:'json', timeout:30000})
            .done(function (reply) {
                runtimeInstalled = !!(reply && reply.installed);
                runtimeState = runtimeInstalled ? reply.service : 'error';
                var started = runtimeState === 'started', stopped = runtimeState === 'stopped';
                $('#voiceServiceState')
                    .removeClass('label-success label-default label-danger')
                    .addClass(started ? 'label-success' : stopped ? 'label-default' : 'label-danger')
                    .text(started ? text.running : stopped ? text.stopped : text.error);
                $('#voiceRuntimeVersion').text((reply && reply.version) || '—');
                $('#voiceServiceControl')
                    .toggle(started || stopped)
                    .text(started ? text.stop : text.start);
                setServiceControlsBusy(!!(reply && reply.busy));
            }).fail(function () {
                runtimeInstalled = false;
                runtimeState = 'error';
                $('#voiceServiceState').removeClass('label-success label-default').addClass('label-danger').text(text.incomplete);
                $('#voiceRuntimeVersion').text('—');
                $('#voiceServiceControl').hide();
                setServiceControlsBusy(true);
            });
    }
    function refreshVoiceIPFW() {
        return $.ajax({type:'POST',url:'/api/zapret/voice/inspect',dataType:'json',timeout:30000})
            .done(function (reply) {
                var state = reply && reply.state;
                var label = state === 'ready' ? text.ipfwReady :
                            state === 'stopped' ? text.ipfwStopped :
                            state === 'uninitialized' ? text.ipfwEmpty :
                            state === 'interrupted' ? text.ipfwInterrupted :
                            state === 'inspection-error' ? text.ipfwUnknown :
                            text.ipfwBlocked;
                var details = {
                    'prepared-needs-previous-verification': text.cutoverPrepared,
                    'interrupted-needs-kernel-runtime-review': text.cutoverMutating,
                    'committed-needs-cleanup-review': text.cutoverCommitted
                };
                $('#voiceIPFWDetail').text(
                    state === 'interrupted' && reply &&
                    typeof reply.condition === 'string' &&
                    Object.prototype.hasOwnProperty.call(details, reply.condition)
                        ? details[reply.condition] : ''
                );
                $('#voiceIPFWState')
                    .removeClass('label-success label-default label-danger')
                    .addClass(state === 'ready' ? 'label-success' :
                              (state === 'uninitialized' || state === 'stopped')
                                  ? 'label-default' : 'label-danger')
                    .text(label);
            }).fail(function () {
                $('#voiceIPFWState').removeClass('label-success label-default')
                    .addClass('label-danger').text(text.ipfwUnknown);
                $('#voiceIPFWDetail').text('');
            });
    }
    function refreshVoiceRecovery() {
        return $.ajax({
            type: 'POST', url: '/api/zapret/voice/recoveryStatus',
            dataType: 'json', timeout: 40000
        }).done(function (reply) {
            var state = reply && reply.state;
            var safe = reply && reply.safe_to_mutate === false &&
                reply.safe_to_start === false &&
                reply.public_voice_apply === false &&
                reply.boot_recovery_validated === false;
            var labels = {
                'no-legacy-five-domain-journal-observed': text.recoveryAbsent,
                'not-a-legacy-five-domain-journal': text.recoveryOther,
                'legacy-five-domain-incomplete-manual-review': text.recoveryIncomplete,
                'legacy-whole-disk-valid-live-boot-recheck-required': text.recoveryReceipt
            };
            var known = safe && Object.prototype.hasOwnProperty.call(labels, state);
            $('#voiceRecoveryState')
                .removeClass('label-success label-default label-danger')
                .addClass(known && state === 'no-legacy-five-domain-journal-observed'
                    ? 'label-default' : 'label-danger')
                .text(known ? labels[state] : text.recoveryUnknown);
        }).fail(function () {
            $('#voiceRecoveryState')
                .removeClass('label-success label-default')
                .addClass('label-danger').text(text.recoveryUnknown);
        });
    }
    function refreshReleases() {
        var select = $('#voiceReleaseSelect');
        select.prop('disabled',true).empty().append($('<option/>').val('').text(text.loading));
        return $.ajax({type:'POST',url:'/api/zapret/service/releases',dataType:'json',timeout:60000})
            .done(function (reply) {
                select.empty();
                if (reply && reply.status === 'ok' && Array.isArray(reply.releases)) {
                    reply.releases.forEach(function (release) {
                        select.append($('<option/>').val(release).text(release));
                    });
                }
                if (!select.children().length) {
                    select.append($('<option/>').val('').text(text.incomplete));
                }
                setServiceControlsBusy(runtimeBusy);
            }).fail(function () {
                select.empty().append($('<option/>').val('').text(text.incomplete));
                setServiceControlsBusy(true);
            });
    }
    $('#voiceServiceControl').on('click', function () {
        if (runtimeBusy || !runtimeInstalled || !['started','stopped'].includes(runtimeState)) return;
        var action = runtimeState === 'started' ? 'stop' : 'start';
        setServiceControlsBusy(true);
        $.ajax({type:'POST',url:'/api/zapret/service/' + action,dataType:'json',timeout:600000})
            .always(function () { refreshRuntime(); updateServiceControlUI('zapret'); });
    });
    $('#voiceReleaseApply').on('click', function () {
        var version = $('#voiceReleaseSelect').val();
        if (runtimeBusy || !/^v[0-9]+(?:\.[0-9]+)+$/.test(version || '')) return;
        setServiceControlsBusy(true);
        $.ajax({type:'POST',url:'/api/zapret/service/install',data:{version:version},dataType:'json',timeout:30000})
            .always(function () { refreshReleases(); refreshRuntime(); updateServiceControlUI('zapret'); });
    });
    $('#voiceServiceHeader').on('click', function () {
        $('#voiceServiceBody').toggle();
        $('#voiceServiceCollapseIcon').toggleClass('fa-angle-down fa-angle-right');
    });
    $('#voiceRepositoryReleasesLabel').text(text.repositoryReleases);
    $('#voiceReleaseApply').text(text.apply);
    refreshRuntime();
    refreshVoiceIPFW();
    refreshVoiceRecovery();
    refreshReleases();
    updateServiceControlUI('zapret');
});
</script>

<style>
    #voiceServiceLine {
        display: grid;
        grid-template-columns: max-content max-content 14ch 12ch 4ch max-content minmax(130px,150px) max-content;
        column-gap: 8px;
        align-items: center;
        min-width: max-content;
        min-height: 34px;
        white-space: nowrap;
    }
    #voiceRuntimeVersion { display: inline-block; width: 14ch; }
    #voiceServiceControlSlot, #voiceServiceControl { min-width: 12ch; }
    .voice-service-spacer { display: inline-block; width: 4ch; }
    #voiceReleaseSelect { width:150px; min-width:130px; }
    #frm_VoiceSettings textarea {max-width:100%; box-sizing:border-box;}
    @media (max-width: 767px) {
        #frm_VoiceSettings input, #frm_VoiceSettings select {max-width:100%;}
    }
</style>
<div class="content-box __mb">
    {{ partial("layout_partials/base_form",['fields':voiceForm,'id':'frm_VoiceSettings']) }}
    <div class="table-responsive">
        <table class="table table-striped table-condensed" style="table-layout: fixed; width: 100%; margin-bottom: 0;">
            <colgroup><col style="width:25%;"><col style="width:40%;"><col style="width:35%;"></colgroup>
            <thead id="voiceServiceHeader" style="cursor:pointer;"><tr><th colspan="3">
                <div style="padding: 5px 0; font-size:16px;">
                    <i id="voiceServiceCollapseIcon" class="fa fa-angle-down" aria-hidden="true"></i>
                    &nbsp;<b id="voiceServiceTitle">Zapret2 Service</b>
                </div>
            </th></tr></thead>
            <tbody id="voiceServiceBody" class="collapsible"><tr><td colspan="3">
                <div id="voiceServiceLine">
                    <b id="voiceStatusLabel">Status:</b>
                    <span id="voiceServiceState" class="label label-danger">—</span>
                    <strong id="voiceRuntimeVersion">—</strong>
                    <span id="voiceServiceControlSlot"><button type="button" class="btn btn-default" id="voiceServiceControl" disabled style="display:none">Start</button></span>
                    <span class="voice-service-spacer" aria-hidden="true"></span>
                    <label for="voiceReleaseSelect" id="voiceRepositoryReleasesLabel" style="margin-bottom:0;">Repository Releases</label>
                    <select class="form-control" id="voiceReleaseSelect" disabled><option value="">Loading…</option></select>
                    <button type="button" class="btn btn-primary" id="voiceReleaseApply" disabled>Apply</button>
                </div>
            </td></tr>
            <tr><td colspan="3">
                <b id="voiceIPFWLabel">Voice IPFW:</b>
                <span id="voiceIPFWState" class="label label-default">—</span>
                <span id="voiceIPFWDetail" aria-live="polite"></span>
            </td></tr>
            <tr><td colspan="3">
                <b id="voiceRecoveryLabel">Previous Telegram PoC recovery:</b>
                <span id="voiceRecoveryState" class="label label-danger" aria-live="polite">—</span>
            </td></tr></tbody>
        </table>
    </div></div>
<section class="grid-bottom-reserve __mt">
    <div class="alert content-box" style="margin-bottom: 0;">
        <button class="btn btn-default __mr" id="voiceValidate" type="button" disabled>Validate</button>
        <button class="btn btn-default __mr" id="voicePreviewDraft" type="button" disabled>Preview saved Voice drafts</button>
        <button class="btn btn-default __mr" id="voiceSaveDraft" type="button" disabled>Save inactive draft</button>
        <button class="btn btn-primary __mr" id="voiceApply" type="button" disabled>Apply</button>
        <span id="voiceValidationStatus" aria-live="polite"></span>
        <span id="voiceImplementationNotice" aria-live="polite"></span>
    </div>
</section>
