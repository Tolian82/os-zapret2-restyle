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
        infoText: 'UDP/STUN-профили пяти сервисов используют общий движок Zapret2 и штатную операцию Apply вместе со «Стратегиями». «Применить» сохраняет настройки и переключает runtime/IPFW с проверяемым возвратом при ошибке. «Сохранить черновик» доступно только для выключенных профилей и не перезапускает службу. Голосовые профили применяются только через общий Apply; отдельной Voice-службы нет. Non-STUN остаётся в «Стратегиях».',
        parameters: 'Параметры передачи голоса', destinations: 'IP-адреса назначения',
        service: 'Служба Zapret2', apply: 'Применить', validate: 'Проверить', saveDraft: 'Сохранить черновик', applied: 'Настройки сохранены и применены к общему движку Zapret2', applyFailed: 'Применение не подтверждено — проверьте ошибки и состояние службы', applyReview: 'Результат применения неизвестен. Проверьте состояние общей службы перед повторной попыткой; обновите страницу.', draftSaved: 'Черновик сохранён, без применения к службе', draftFailed: 'Черновик не сохранён', draftReview: 'Результат сохранения черновика неизвестен. Перезагрузите страницу и проверьте настройки перед повторной попыткой.', checkOk: 'Синтаксис проверен (без применения)', previewDraft: 'Проверить сохранённый черновик', previewOk: 'Черновики проверены под блокировкой службы; изменения не применены', previewFailed: 'Черновики должны быть сначала сохранены выключенными; проверьте настройки', checkFailed: 'Исправьте отмеченные поля', checkError: 'Проверка недоступна', start: 'Запустить', stop: 'Остановить', repositoryReleases: 'Релизы репозитория',
        notice: 'Кнопка «Применить» использует единый native Apply для включённых и выключенных профилей, с проверкой Config, runtime и IPFW. «Сохранить черновик» сохраняет только выключенные профили без переключения службы. При незавершённом общем применении проверьте состояние Zapret2, Config и IPFW; не запускайте повторное применение вслепую.',
        status: 'Статус', running: 'Запущена', stopped: 'Остановлена', error: 'Ошибка',
        loading: 'Загрузка…', incomplete: 'Неизвестно',
        ipfwStatus: 'IPFW — передача голоса', ipfwReady: 'Общий движок и правила подтверждены', ipfwStopped: 'Общая служба остановлена, IPFW очищен',
        ipfwEmpty: 'Новая Voice-конфигурация не активирована', ipfwInterrupted: 'Незавершённое применение',
        ipfwBlocked: 'Требуется проверка правил', ipfwUnknown: 'Статус недоступен',

        sharedApplyPrepared: 'Общее применение подготовлено, но не завершено — проверьте состояние службы',
        sharedApplyActivating: 'Общее применение прервано при переключении runtime/IPFW — нужна проверка',
        sharedApplyActivated: 'Runtime/IPFW переключены; сохранение Config не подтверждено',
        sharedApplyConfigSaved: 'Config сохранён; завершение общего применения не подтверждено',
        sharedApplyRestoreFailed: 'Не удалось восстановить согласованное состояние общей службы — нужна проверка',
        sharedApplyRequiresReview: 'Общее применение требует проверки Config, службы и IPFW',
        commonConfigMismatch: 'Сохранённый Config не совпадает с активным профилем — требуется проверка',
        commonProfileUnverified: 'Профиль не подтверждён — проверьте Config и runtime',
        savedVoiceOn: 'Сохранено: ВКЛ', savedVoiceOff: 'Сохранено: ВЫКЛ',
        voiceActive: 'STUN-профиль, dvtws2 и IPFW подтверждены; звонок не проверен',
        voiceStopped: 'Служба остановлена; профиль сохранён',
        voiceDisabled: 'Дополнительный Voice-перехват выключен',
        voiceUnverified: 'Активность профиля не подтверждена',
        voiceEffectiveWan: 'WAN', voiceUdpPorts: 'UDP', voiceIpsetCount: 'IPSET записей',
        voiceProfileId: 'Применённый профиль', voiceRule: 'Правило IPFW',
        voicePackets: 'Пакеты', voiceBytes: 'Байты',
        wanHelp: 'Исходящий WAN для перехвата голосового UDP. Пустое значение наследует WAN страницы «Стратегии». Выбор WAN не меняет маршруты.',
        enableHelp: 'Включённый STUN-профиль применяется общей кнопкой «Применить». Для «Сохранить черновик» все голосовые профили должны быть выключены. Параметры и IPSET сохраняются при выключении.',
        argsHelp: 'Один нативный STUN-профиль dvtws2: <code>--filter-udp</code>, <code>--filter-l7=stun</code>, <code>--payload=stun</code> и необязательные действия <code>--lua-desync</code>. Имя профиля и IPSET задаёт плагин. Не вводите <code>--new</code>, TCP или команды shell. Это не означает, что звонок заработает.',
        ipHelp: 'Общий со «Стратегиями» IPSET. Один IPv4-адрес или CIDR в строке. Пустой список нельзя применять при включённой службе; нет автоматической замены на любой адрес.'
    } : {
        navStrategy: 'Strategies', navVoice: 'Voice Transmission', navLab: 'Laboratory',
        general: 'General Settings', wan: 'Voice WAN Interface',
        infoTitle: 'About Voice Profiles',
        infoText: 'Five UDP/STUN profiles share the existing Zapret2 engine and the native Strategies/Voice Apply transaction. Apply saves settings and switches runtime/IPFW with verified rollback on failure. Save inactive draft only stores disabled profiles without restarting the service. Voice profiles activate only through shared Apply, not a separate Voice service. Non-STUN remains in Strategies.',
        parameters: 'Voice Transmission Parameters', destinations: 'Destination IP Addresses',
        service: 'Zapret2 Service', apply: 'Apply', validate: 'Validate', saveDraft: 'Save inactive draft', applied: 'Settings saved and applied to the shared Zapret2 engine', applyFailed: 'Apply not confirmed — review validation and current service state', applyReview: 'Apply result is uncertain. Inspect the shared service state before retrying; reload this page.', draftSaved: 'Draft saved to Config; runtime unchanged', draftFailed: 'Draft was not saved', draftReview: 'Draft save result is unknown. Reload the page and inspect saved settings before retrying.', checkOk: 'Syntax checked (not applied)', previewDraft: 'Preview saved Voice drafts', previewOk: 'Saved drafts checked under service lock; no changes applied', previewFailed: 'Save disabled Voice drafts before preview; check the settings', checkFailed: 'Correct highlighted fields', checkError: 'Validation unavailable', start: 'Start', stop: 'Stop', repositoryReleases: 'Repository Releases',
        notice: 'Apply uses the single native transaction for enabled and disabled Voice profiles, checking Config, runtime and IPFW. Save inactive draft only persists disabled profiles without restarting the service. If shared Apply was interrupted, inspect Zapret2, Config and IPFW before retrying.',
        status: 'Status', running: 'Started', stopped: 'Stopped', error: 'Error',
        loading: 'Loading…', incomplete: 'Unknown',
        ipfwStatus: 'Voice IPFW', ipfwReady: 'Shared engine and IPFW verified', ipfwStopped: 'Shared service stopped; IPFW cleared',
        ipfwEmpty: 'New Voice configuration not activated', ipfwInterrupted: 'Interrupted apply',
        ipfwBlocked: 'Firewall review required', ipfwUnknown: 'Status unavailable',

        sharedApplyPrepared: 'Shared Apply prepared but not completed — inspect service state',
        sharedApplyActivating: 'Shared Apply interrupted while switching runtime/IPFW — review required',
        sharedApplyActivated: 'Runtime/IPFW activated; Config save not confirmed',
        sharedApplyConfigSaved: 'Config saved; shared Apply completion not confirmed',
        sharedApplyRestoreFailed: 'Shared service restoration failed — inspection required',
        sharedApplyRequiresReview: 'Shared Apply needs Config, service and IPFW review',
        commonConfigMismatch: 'Saved Config differs from active profile — review required',
        commonProfileUnverified: 'Profile not verified — inspect Config and runtime',
        savedVoiceOn: 'Saved: ON', savedVoiceOff: 'Saved: OFF',
        voiceActive: 'STUN profile, dvtws2 and IPFW verified; call untested',
        voiceStopped: 'Service stopped; profile saved',
        voiceDisabled: 'Additional Voice interception disabled',
        voiceUnverified: 'Profile activation not verified',
        voiceEffectiveWan: 'WAN', voiceUdpPorts: 'UDP', voiceIpsetCount: 'IPSET entries',
        voiceProfileId: 'Applied profile', voiceRule: 'IPFW rule',
        voicePackets: 'Packets', voiceBytes: 'Bytes',
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
            'Zapret lifecycle is busy; retry after diagnostics finish': 'Служба занята лабораторией — дождитесь завершения диагностики',
            'Zapret lifecycle became busy before applying': 'Служба занята — применение отменено до сохранения',
            'Settings saved, but Zapret reconfigure failed; inspect current runtime before retrying': 'Настройки сохранены, но перезапуск Zapret2 завершился ошибкой; проверьте фактическое состояние службы',
            'Save inactive draft requires all Voice services OFF; use Apply to change active profiles': 'Черновик можно сохранить только при всех выключенных профилях Voice. Для изменения активных профилей используйте «Применить»',
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
        if (button.prop('disabled') || voiceMutationPending ||
            voiceControlPending || voiceApplyNeedsReview) return;
        // Both Config writers must be exclusive, even after uncertain Apply.
        voiceMutationPending = true;
        reconcileVoiceServiceStatus();
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
            } else if (reply && reply.result === 'failed' &&
                reply.requires_review !== true && reply.validations &&
                typeof reply.validations === 'object' &&
                !Array.isArray(reply.validations) &&
                Object.keys(reply.validations).length > 0) {
                // Explicit pre-write validation rejection is safe to edit.
                $('#voiceValidationStatus').text(text.draftFailed);
            } else {
                // A malformed/ambiguous response may follow a Config write.
                voiceApplyNeedsReview = true;
                $('#voiceValidationStatus').text(text.draftReview);
            }
        }).fail(function () {
            // A browser timeout does not prove that Config::save failed.
            voiceApplyNeedsReview = true;
            $('#voiceValidationStatus').text(text.draftReview);
        }).always(function () {
            voiceMutationPending = false;
            reconcileVoiceServiceStatus();
        });
    });
    // A timeout or an explicit requires_review can mean the root worker is
    // still mutating or retained crash evidence. Do not offer blind retries.
    var voiceApplyNeedsReview = false;
    var voiceMutationPending = false;
    $('#voiceApply').on('click', function () {
        var button = $(this);
        if (button.prop('disabled') || voiceMutationPending ||
            voiceControlPending || voiceApplyNeedsReview) return;
        voiceMutationPending = true;
        voiceInspectionState = null;
        reconcileVoiceServiceStatus();
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
            } else if (reply && reply.requires_review === true) {
                voiceApplyNeedsReview = true;
                $('#voiceValidationStatus').text(text.applyReview);
            } else {
                $('#voiceValidationStatus').text(text.applyFailed);
            }
        }).fail(function () {
            voiceApplyNeedsReview = true;
            $('#voiceValidationStatus').text(text.applyReview);
        }).always(function () {
            // The root worker may have saved Config or committed IPFW even
            // when the browser reports an error. Do not unlock mutation
            // controls until BOTH independent live observations have settled.
            refreshVoiceHealthSettled().always(function () {
                voiceMutationPending = false;
                // An applied-id is durable, but the GUI may claim success
                // only after fresh generic + native status agree as well.
                if (!voiceApplyNeedsReview &&
                    $('#voiceValidationStatus').text() === text.applied &&
                    !voiceRuntimeAligned()) {
                    voiceApplyNeedsReview = true;
                    $('#voiceValidationStatus').text(text.applyReview);
                }
                reconcileVoiceServiceStatus();
            });
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
            reconcileVoiceMutationControls();
        } else {
            $('#voiceValidationStatus').text(text.checkError);
        }
        formatTokenizersUI();
        $('.selectpicker').selectpicker('refresh');
        localizeForm();
        refreshVoiceIPFW();
    });
    var runtimeState = 'error', runtimeInstalled = false, runtimeBusy = true;
    var voiceInspectionState = null, voiceControlPending = false;
    var voiceRuntimeEpoch = 0, voiceInspectionEpoch = 0;
    function voiceRuntimeAligned() {
        // setup_status is a general service indicator, not proof of native
        // Voice engine/IPFW. Both witnesses must describe one same state.
        return runtimeInstalled && (
            (runtimeState === 'started' && voiceInspectionState === 'ready') ||
            (runtimeState === 'stopped' && voiceInspectionState === 'stopped')
        );
    }
    function reconcileVoiceMutationControls() {
        // No Config write while another write/service operation is pending,
        // or when shared Apply has returned an indeterminate result.
        var fresh = /^[a-f0-9]{64}$/.test(voiceSnapshot.val() || '');
        $('#voiceSaveDraft,#voiceApply').prop('disabled',
            !fresh || voiceMutationPending || voiceControlPending ||
            voiceApplyNeedsReview);
    }
    function setServiceControlsBusy(busy) {
        runtimeBusy = !!busy;
        var controllable = voiceRuntimeAligned() &&
            !voiceMutationPending && !voiceControlPending && !voiceApplyNeedsReview;
        $('#voiceServiceControl').prop('disabled', runtimeBusy || !controllable);
        var releasesAvailable = $('#voiceReleaseSelect option').filter(function () {
            return /^v[0-9]+(?:\.[0-9]+)+$/.test(this.value);
        }).length > 0;
        $('#voiceReleaseSelect,#voiceReleaseApply').prop('disabled',
            runtimeBusy || voiceMutationPending || voiceControlPending ||
            voiceApplyNeedsReview || !releasesAvailable);
    }
    function reconcileVoiceServiceStatus() {
        var aligned = voiceRuntimeAligned() && !voiceMutationPending &&
            !voiceControlPending && !voiceApplyNeedsReview;
        var started = aligned && runtimeState === 'started';
        var stopped = aligned && runtimeState === 'stopped';
        // A generic started flag MUST NOT look green if the committed
        // Voice owner is interrupted, its Config differs, or IPFW is unknown.
        $('#voiceServiceState')
            .removeClass('label-success label-default label-danger')
            .addClass(started ? 'label-success' : stopped ? 'label-default' : 'label-danger')
            .text(started ? text.running : stopped ? text.stopped :
                  runtimeState === 'error' ? text.error : text.incomplete);
        $('#voiceServiceControl')
            .toggle(runtimeInstalled && ['started', 'stopped'].includes(runtimeState))
            .text(runtimeState === 'started' ? text.stop : text.start);
        setServiceControlsBusy(runtimeBusy);
        reconcileVoiceMutationControls();
    }
    function refreshRuntime() {
        var epoch = ++voiceRuntimeEpoch;
        // Invalidate the old "started" display while the new request runs.
        runtimeState = 'error';
        runtimeBusy = true;
        reconcileVoiceServiceStatus();
        return $.ajax({type:'POST', url:'/api/zapret/service/runtime', dataType:'json', timeout:30000})
            .done(function (reply) {
                if (epoch !== voiceRuntimeEpoch) return;
                runtimeInstalled = !!(reply && reply.installed);
                runtimeState = runtimeInstalled ? reply.service : 'error';
                $('#voiceRuntimeVersion').text((reply && reply.version) || '—');
                runtimeBusy = !!(reply && reply.busy);
                reconcileVoiceServiceStatus();
            }).fail(function () {
                if (epoch !== voiceRuntimeEpoch) return;
                runtimeInstalled = false;
                runtimeState = 'error';
                runtimeBusy = true;
                $('#voiceRuntimeVersion').text('—');
                reconcileVoiceServiceStatus();
            });
    }
    // Append read-only observations to existing checkbox help text, without
    // moving or replacing any of the five approved form fields/help icons.
    function showVoiceProfileObservations(reply) {
        ['telegram', 'discord', 'x', 'sip', 'custom'].forEach(function (name) {
            var id = 'zapret.voice.' + name + '.enabled';
            var input = document.getElementById(id) || document.getElementById(id.replace(/\./g, '_'));
            if (!input) return;
            var help = $(input).closest('tr').find('.help-block').first();
            if (!help.length) return;
            var observed = help.find('.voice-profile-observation');
            if (!observed.length) {
                observed = $('<span class="voice-profile-observation"></span>').appendTo(help);
            }
            var profile = reply && reply.profiles && reply.profiles[name];
            if (!profile || typeof profile.saved_enabled !== 'boolean' ||
                !['active', 'stopped', 'disabled'].includes(profile.runtime)) {
                observed.text(' · ' + text.voiceUnverified);
                return;
            }
            var saved = profile.saved_enabled ? text.savedVoiceOn : text.savedVoiceOff;
            var state = profile.runtime === 'active' ? text.voiceActive :
                        profile.runtime === 'stopped' ? text.voiceStopped :
                        text.voiceDisabled;
            var details = '';
            if (profile.saved_enabled && (profile.runtime === 'active' || profile.runtime === 'stopped') &&
                profile.profile_id === 'voice-' + name &&
                /^[a-f0-9]{12}$/.test(profile.profile_revision || '') &&
                typeof profile.wan === 'string' &&
                /^[A-Za-z][A-Za-z0-9_.:-]{0,63}$/.test(profile.wan) &&
                typeof profile.udp_ports === 'string' &&
                /^[0-9,-]{1,1024}$/.test(profile.udp_ports) &&
                Number.isInteger(profile.ipset_entries) &&
                profile.ipset_entries >= 1 && profile.ipset_entries <= 4096) {
                // These are confirmed release/IPFW scopes, not traffic
                // measurements. Use text(), never inject native data as HTML.
                details = ' · ' + text.voiceEffectiveWan + ': ' + profile.wan +
                    ' · ' + text.voiceUdpPorts + ': ' + profile.udp_ports +
                    ' · ' + text.voiceIpsetCount + ': ' + profile.ipset_entries +
                    ' · ' + text.voiceProfileId + ': ' +
                    profile.profile_id + '@' + profile.profile_revision;
                // The rule belongs to the already-attested native common
                // manifest; packet counters are observational, not proof of
                // bidirectional media or a successful call.
                if (profile.runtime === 'active' &&
                    Number.isInteger(profile.rule) &&
                    profile.rule >= 1 && profile.rule <= 65534) {
                    details += ' · ' + text.voiceRule + ': ' + profile.rule;
                    if (Number.isSafeInteger(profile.rule_packets) &&
                        profile.rule_packets >= 0) {
                        details += ' · ' + text.voicePackets + ': ' + profile.rule_packets;
                    }
                    if (Number.isSafeInteger(profile.rule_bytes) &&
                        profile.rule_bytes >= 0) {
                        details += ' · ' + text.voiceBytes + ': ' + profile.rule_bytes;
                    }
                }
            }
            observed.text(' · ' + saved + ' — ' + state + details);
        });
    }
    // A terminal native status is actionable only with the five exact
    // saved/installed profiles, not merely an object with five keys. Keep
    // malformed or contradictory observations from turning IPFW green or
    // authorizing a second Start/Stop while Config/runtime may disagree.
    function voiceProfilesVerified(reply) {
        var names = ['telegram', 'discord', 'x', 'sip', 'custom'];
        var profiles = reply && reply.profiles;
        if (!reply || !['ready', 'stopped'].includes(reply.state) ||
            !profiles || typeof profiles !== 'object' ||
            Array.isArray(profiles) || Object.keys(profiles).length !== names.length) {
            return false;
        }
        var requiredRuntime = reply.state === 'ready' ? 'active' : 'stopped';
        return names.every(function (name) {
            if (!Object.prototype.hasOwnProperty.call(profiles, name)) return false;
            var profile = profiles[name];
            if (!profile || typeof profile !== 'object' || Array.isArray(profile) ||
                typeof profile.saved_enabled !== 'boolean' ||
                profile.media_verified !== false || profile.call_verified !== false) {
                return false;
            }
            if (!profile.saved_enabled) return profile.runtime === 'disabled';
            return profile.runtime === requiredRuntime &&
                profile.profile_id === 'voice-' + name &&
                /^[a-f0-9]{12}$/.test(profile.profile_revision || '') &&
                typeof profile.wan === 'string' &&
                /^[A-Za-z][A-Za-z0-9_.:-]{0,63}$/.test(profile.wan) &&
                typeof profile.udp_ports === 'string' &&
                /^[0-9,-]{1,1024}$/.test(profile.udp_ports) &&
                Number.isInteger(profile.ipset_entries) &&
                profile.ipset_entries >= 1 && profile.ipset_entries <= 4096 &&
                (reply.state === 'stopped' ||
                    (Number.isInteger(profile.rule) &&
                     profile.rule >= 1 && profile.rule <= 65534));
        });
    }
    function refreshVoiceIPFW() {
        var epoch = ++voiceInspectionEpoch;
        voiceInspectionState = null;
        reconcileVoiceServiceStatus();
        return $.ajax({type:'POST',url:'/api/zapret/voice/inspect',dataType:'json',timeout:30000})
            .done(function (reply) {
                if (epoch !== voiceInspectionEpoch) return;
                var reportedState = reply && reply.state;
                var unverified = ['ready', 'stopped'].includes(reportedState) &&
                    !voiceProfilesVerified(reply);
                var state = unverified ? 'unverified-profiles' : reportedState;
                var label = state === 'ready' ? text.ipfwReady :
                            state === 'stopped' ? text.ipfwStopped :
                            state === 'uninitialized' ? text.ipfwEmpty :
                            state === 'interrupted' ? text.ipfwInterrupted :
                            state === 'inspection-error' ? text.ipfwUnknown :
                            text.ipfwBlocked;
                var details = {

                    'shared-apply-prepared': text.sharedApplyPrepared,
                    'shared-apply-activating': text.sharedApplyActivating,
                    'shared-apply-activated': text.sharedApplyActivated,
                    'shared-apply-config-saved': text.sharedApplyConfigSaved,
                    'shared-apply-restore-failed': text.sharedApplyRestoreFailed,
                    'shared-apply-requires-review': text.sharedApplyRequiresReview,
                    'common-config-mismatch': text.commonConfigMismatch,
                    'common-profile-unverified': text.commonProfileUnverified
                };
                $('#voiceIPFWDetail').text(
                    unverified ? text.commonProfileUnverified :
                    state === 'interrupted' && reply &&
                    typeof reply.condition === 'string' &&
                    Object.prototype.hasOwnProperty.call(details, reply.condition)
                        ? details[reply.condition] : ''
                );
                showVoiceProfileObservations(unverified ? null : reply);
                // A ready/stopped code without all five matching attested
                // profiles (stale or partial common owner) is not actionable.
                voiceInspectionState = ['ready', 'stopped'].includes(state) ? state : null;
                reconcileVoiceServiceStatus();
                $('#voiceIPFWState')
                    .removeClass('label-success label-default label-danger')
                    .addClass(state === 'ready' ? 'label-success' :
                              (state === 'uninitialized' || state === 'stopped')
                                  ? 'label-default' : 'label-danger')
                    .text(label);
            }).fail(function () {
                if (epoch !== voiceInspectionEpoch) return;
                voiceInspectionState = null;
                showVoiceProfileObservations(null);
                reconcileVoiceServiceStatus();
                $('#voiceIPFWState').removeClass('label-success label-default')
                    .addClass('label-danger').text(text.ipfwUnknown);
                $('#voiceIPFWDetail').text('');
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
                // A release-list outage must not fabricate service busy or
                // override independently attested Voice Start/Stop status.
                setServiceControlsBusy(runtimeBusy);
            });
    }
    function refreshVoiceHealthSettled() {
        // jQuery.when rejects early if one query fails. Normalize failure
        // into a completed observation so neither mutation control unlocks
        // until BOTH independent requests have actually settled.
        var settle = function (request) {
            return request.then(function () { return true; },
                                function () { return false; });
        };
        return $.when(settle(refreshRuntime()), settle(refreshVoiceIPFW()));
    }
    $('#voiceServiceControl').on('click', function () {
        if (runtimeBusy || voiceControlPending || voiceMutationPending ||
            voiceApplyNeedsReview || !voiceRuntimeAligned()) return;
        var action = runtimeState === 'started' ? 'stop' : 'start';
        voiceControlPending = true;
        voiceInspectionState = null;
        reconcileVoiceServiceStatus();
        $.ajax({type:'POST',url:'/api/zapret/service/' + action,dataType:'json',timeout:600000})
            .always(function () {
                // A successful API response is not proof that post-COMMIT
                // native runtime, IPFW and processes match the saved model.
                refreshVoiceHealthSettled().always(function () {
                    voiceControlPending = false;
                    updateServiceControlUI('zapret');
                    reconcileVoiceServiceStatus();
                });
            });
    });
    $('#voiceReleaseApply').on('click', function () {
        var version = $('#voiceReleaseSelect').val();
        if (runtimeBusy || voiceControlPending || voiceMutationPending ||
            voiceApplyNeedsReview || !/^v[0-9]+(?:\.[0-9]+)+$/.test(version || '')) return;
        voiceControlPending = true;
        voiceInspectionState = null;
        reconcileVoiceServiceStatus();
        $.ajax({type:'POST',url:'/api/zapret/service/install',data:{version:version},dataType:'json',timeout:30000})
            .always(function () {
                refreshReleases();
                refreshVoiceHealthSettled().always(function () {
                    voiceControlPending = false;
                    updateServiceControlUI('zapret');
                    reconcileVoiceServiceStatus();
                });
            });
    });
    $('#voiceServiceHeader').on('click', function () {
        $('#voiceServiceBody').toggle();
        $('#voiceServiceCollapseIcon').toggleClass('fa-angle-down fa-angle-right');
    });
    $('#voiceRepositoryReleasesLabel').text(text.repositoryReleases);
    $('#voiceReleaseApply').text(text.apply);
    refreshRuntime();
    refreshVoiceIPFW();
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
</tbody>
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
