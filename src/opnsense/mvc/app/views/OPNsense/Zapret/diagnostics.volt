{# Copyright (C) 2026 Umur Gorur. All rights reserved. #}
<script>
$(document).ready(function () {
    var activeJobId = '', pollTimer = null, circularTimer = null, renderedProfiles = [];
    var historicalView = false, savedLookupToken = 0, savedJobKey = 'zapret2.strategyLab.selectedSavedJob';
    var udpPayloadMaxBytes = 4096, discoveryRetryLimit = 5;
    var strategyLabBusy = false, quicPreferenceReady = false, quicPreferenceSaving = false;
    var udpPayloadSelection = {generation:0, ready:false, reading:false, fileName:'', bytes:0, base64:''};
    var isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
    var stageLabels = isRussian ? {
        target_initialization:'Подготовка цели', lifecycle_snapshot:'Снимок состояния', service_stop:'Остановка службы',
        network_precheck:'Проверка сети', clean_baseline:'Прямая доступность', family_screening:'Проверка семейств',
        family_expansion:'Расширение параметров', stability:'Проверка стабильности', extended:'Расширенные протоколы',
        shortlist:'Формирование результата', restore:'Восстановление Zapret2', report:'Итоговый отчёт'
    } : {
        target_initialization:'Target initialization', lifecycle_snapshot:'Lifecycle snapshot', service_stop:'Service stop',
        network_precheck:'Network precheck', clean_baseline:'Clean baseline', family_screening:'Family screening',
        family_expansion:'Parameter expansion', stability:'Stability verification', extended:'Extended protocols',
        shortlist:'Final shortlist', restore:'Zapret2 restoration', report:'Final report'
    };
    var statusLabels = isRussian ? {
        IDLE:'ожидание', QUEUED:'В ОЧЕРЕДИ', PREPARING:'ПОДГОТОВКА', PENDING:'ОЖИДАНИЕ', RUNNING:'ВЫПОЛНЯЕТСЯ',
        CANCEL_REQUESTED:'ОСТАНОВКА ЗАПРОШЕНА', STOP_REQUESTED:'ОСТАНОВКА ЗАПРОШЕНА', COMPLETED:'ЗАВЕРШЕНО',
        PASS:'УСПЕШНО', FAIL:'ОШИБКА', FAILED:'ОШИБКА', ERROR:'ОШИБКА', TIMEOUT:'ТАЙМ-АУТ', SKIPPED:'ПРОПУЩЕНО',
        CANCELLED:'ОТМЕНЕНО', RESTORE_FAILED:'ВОССТАНОВЛЕНИЕ НЕ ВЫПОЛНЕНО'
    } : {
        IDLE:'idle', QUEUED:'QUEUED', PREPARING:'PREPARING', PENDING:'PENDING', RUNNING:'RUNNING',
        CANCEL_REQUESTED:'CANCELLATION REQUESTED', STOP_REQUESTED:'STOP REQUESTED', COMPLETED:'COMPLETED', PASS:'PASS',
        FAIL:'FAIL', FAILED:'FAILED', ERROR:'ERROR', TIMEOUT:'TIMEOUT', SKIPPED:'SKIPPED', CANCELLED:'CANCELED',
        RESTORE_FAILED:'RESTORE FAILED'
    };
    var outcomeLabels = isRussian ? {
        SUCCESS:'Успешно', NO_CANDIDATE:'Рабочие стратегии не найдены', TARGET_ACCESSIBLE:'Цель доступна без обхода',
        PARTIAL:'Частичный результат', TIMEOUT:'Тайм-аут', ERROR:'Ошибка', RESTORE_FAILED:'Ошибка восстановления'
    } : {
        SUCCESS:'Success', NO_CANDIDATE:'No working candidate', TARGET_ACCESSIBLE:'Target accessible without bypass',
        PARTIAL:'Partial result', TIMEOUT:'Timeout', ERROR:'Error', RESTORE_FAILED:'Restoration failed'
    };
    var modeLabels = isRussian ? {standard:'Стандартный', extended:'Расширенный'} : {standard:'Standard', extended:'Extended'};
    var circularMessages = isRussian ? {
        idle:'Временная циклическая проверка не запущена.', queued:'Циклическая проверка поставлена в очередь.',
        preparing:'Выполняется подготовка временной циклической проверки.', running:'Временная циклическая проверка активна.',
        stop_requested:'Запрошена остановка циклической проверки.', completed:'Циклическая проверка завершена, состояние Zapret2 восстановлено.',
        error:'Циклическая проверка завершилась ошибкой.', restore_failed:'Не удалось доказать восстановление Zapret2; повторный запуск заблокирован.'
    } : {
        idle:'Temporary circular validation is idle.', queued:'Circular validation is queued.',
        preparing:'Temporary circular validation is being prepared.', running:'Temporary circular validation is active.',
        stop_requested:'Circular validation stop was requested.', completed:'Circular validation finished and Zapret2 was restored.',
        error:'Circular validation ended with an error.', restore_failed:'Zapret2 restoration could not be proven; retry is blocked.'
    };
    var strategyLabGuidance = isRussian ? [
        'Введите домен, IPv4- или IPv6-адрес, который в настоящее время блокируется вашим интернет-провайдером, и нажмите «Запустить». Для IP-цели при необходимости укажите Host / SNI реального сервиса. Основной режим проверки ограничен 150 секундами, расширенный — 270 секундами. После завершения будут показаны стабильные стратегии, которые обеспечили доступ к цели.',
        'Изучите результат и добавьте необходимый профиль в используемую стратегию на странице «Настройки».'
    ] : [
        'Enter a domain, IPv4 or IPv6 address that is currently blocked by your ISP and click “Run.” For an IP target, provide the real service Host / SNI when needed. Standard mode is limited to 150 seconds and extended mode to 270 seconds. Stable strategies that successfully provide access to the target will be reported after completion.',
        'Review the results and add the required profile to the strategy currently in use on the “Settings” page.'
    ];
    var ui = isRussian ? {
        running:'Strategy Lab выполняет проверку.', completed:'Проверка завершена.', cancel:'Остановка запрошена. Выполняется обязательное восстановление Zapret2.',
        failed:'Проверка завершилась с ошибкой.', noCandidates:'Стабильные кандидаты не найдены.', circularReady:'Можно временно проверить найденные стратегии в браузере.',
        udpPair:'Для общей UDP-проверки укажите одновременно порт и payload-файл.', udpSize:'Payload-файл должен иметь размер от 1 до 4096 байт.',
        udpRead:'Не удалось прочитать payload-файл.', udpReading:'Чтение выбранного payload-файла…', udpReady:'Файл подготовлен к отправке', udpBytes:'байт',
        udpNotReady:'Payload-файл выбран, но ещё не подготовлен к отправке.', udpHelp:'Файл запроса должен иметь размер 1–4096 байт. Для проверки необходимо указать и порт, и файл.',
        chooseFile:'Выбрать файл', noFileSelected:'Файл не выбран',
        quicHelp:'Если включено, QUIC-стратегии проверяются даже когда контрольная проверка показывает, что QUIC заблокирован.',
        quicSaveFailed:'Не удалось сохранить настройку Enable QUIC.',
        copy:'Копировать профиль', copied:'Профиль скопирован.', copyFailed:'Не удалось скопировать профиль.',
        copyJob:'Копировать Job ID', jobCopied:'Job ID скопирован.', jobCopyFailed:'Не удалось скопировать Job ID.',
        circularTitle:'Временная циклическая проверка', circularHelp:'Только для 3–5 подтверждённых TLS 1.3 стратегий: до 5 минут временно чередует тестовые варианты для проверки сайта в браузере. Запускает отдельный dvtws2 и IPFW-перехват для целевых адресов, что может затронуть другие устройства сети. Настройки Стратегий не сохраняются; после завершения выполняется восстановление Zapret2.',
        savedJobLabel:'Сохранённое задание', openSavedJob:'Открыть результат', savedJobInvalid:'Укажите ID вида job.XXXX.', savedJobUnavailable:'Сохранённый результат не найден или задание не завершено.',
        unverifiedReplay:'не подтверждено', savedProfiles:'Сохранённые профили (финальное воспроизведение не подтверждено)', unverifiedScope:'без подтверждённого финального воспроизведения',
        progress:'Прогресс', restorationPass:'Успешно', requestFailed:'Ошибка запроса: ',
        statusRetry:'Статус Strategy Lab временно недоступен. Повторная попытка…', statusFailed:'Не удалось получить актуальный статус Strategy Lab.',
        testDomainTitle:'Тестирование соединения с доменом', testDomainHelp:'Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.',
        testAction:'Проверка', strategyLabTitle:'Лаборатория стратегий', blockedDomain:'Заблокированный домен / IP', serviceHostLabel:'Host / SNI (опционально)',
        serviceHostHelp:'Для IP-цели укажите имя сервиса, если TLS/HTTP/QUIC должны использовать отдельный Host / SNI.',
        genericUdpLabel:'UDP порт (опционально)', runAction:'Запуск', enableQuic:'Включить QUIC',
        modeLabel:'Режим', ipv6OptIn:'IPv6',
        resultSummary:'Сводка результатов', family:'Семейство', endpoints:'Назначения', outcome:'Результат', restoration:'Восстановление', replay:'Ответы',
        completeProfile:'Полный профиль Стратегий Трафика', fullOutput:'Полный вывод (расширенный)', stateLabel:'Состояние',
        verifiedScope:'Подтверждено финальным воспроизведением', scopeTcp:'TLS/TCP 443', scopeHttp:'HTTP/TCP 80', scopeQuic:'QUIC/UDP 443', scopeUdp:'другой UDP',
        scopeExplanation:'Испытанные, но не прошедшие кандидаты сюда не входят. HTTP/TCP 80 не подтверждает доступ по TLS/TCP 443 или QUIC/UDP 443.'
    } : {
        running:'Strategy Lab is running.', completed:'The check is complete.', cancel:'Cancellation requested. Mandatory Zapret2 restoration is running.',
        failed:'The check ended with an error.', noCandidates:'No stable candidates were found.', circularReady:'The candidates can now be tested temporarily in a browser.',
        udpPair:'Generic UDP testing requires both a port and a payload file.', udpSize:'The payload file must contain between 1 and 4096 bytes.',
        udpRead:'The payload file could not be read.', udpReading:'Reading the selected payload file…', udpReady:'Payload ready to send', udpBytes:'bytes',
        udpNotReady:'A payload file is selected but is not ready to send yet.', udpHelp:'Request payload file, 1–4096 bytes. Both port and file are required.',
        chooseFile:'Choose file', noFileSelected:'No file selected',
        quicHelp:'When enabled, QUIC candidates are tested even when the control probe reports QUIC as blocked.',
        quicSaveFailed:'The Enable QUIC setting could not be saved.',
        copy:'Copy profile', copied:'Profile copied.', copyFailed:'The profile could not be copied.',
        copyJob:'Copy Job ID', jobCopied:'Job ID copied.', jobCopyFailed:'Could not copy Job ID.',
        circularTitle:'Temporary circular validation', circularHelp:'Only for 3–5 verified TLS 1.3 strategies: temporarily cycles test profiles for up to 5 minutes to check the site in a browser. Runs a separate dvtws2 and IPFW interception for target addresses, potentially affecting other network clients. Saved Traffic Strategies are not changed; Zapret2 is restored afterward.',
        savedJobLabel:'Saved job', openSavedJob:'Open result', savedJobInvalid:'Enter a valid job ID such as job.XXXX.', savedJobUnavailable:'Saved result not found or job is not completed.',
        unverifiedReplay:'not verified', savedProfiles:'Saved profiles (final replay not verified)', unverifiedScope:'without verified final replay',
        progress:'Progress', restorationPass:'Pass', requestFailed:'Request failed: ',
        statusRetry:'Strategy Lab status is temporarily unavailable. Retrying…', statusFailed:'The current Strategy Lab status could not be read.',
        testDomainTitle:'Test Domain Connectivity', testDomainHelp:'Enter a domain and click Test to check HTTPS connectivity.',
        testAction:'Test', strategyLabTitle:'Strategy Lab', blockedDomain:'Blocked Domain / IP', serviceHostLabel:'Host / SNI (optional)',
        serviceHostHelp:'For an IP target, provide the service name when TLS/HTTP/QUIC must use a separate Host / SNI identity.',
        genericUdpLabel:'Generic UDP (optional)', runAction:'Run', enableQuic:'Enable QUIC',
        modeLabel:'Mode', ipv6OptIn:'IPv6',
        resultSummary:'Result summary', family:'Family', endpoints:'Endpoints', outcome:'Outcome', restoration:'Restoration', replay:'Replay',
        completeProfile:'Complete Traffic Strategy profile', fullOutput:'Full output (advanced)', stateLabel:'State',
        verifiedScope:'Verified by final profile replay', scopeTcp:'TLS/TCP 443', scopeHttp:'HTTP/TCP 80', scopeQuic:'QUIC/UDP 443', scopeUdp:'other UDP',
        scopeExplanation:'Tested candidates that failed qualification are excluded. HTTP/TCP 80 does not establish TLS/TCP 443 or QUIC/UDP 443 access.'
    };

    function setButtonText(selector, text) {
        var button=$(selector), icons=button.find('i').detach();
        button.empty().text(text + ' '); if (icons.length) button.append(icons);
    }
    function applyStaticLocalization() {
        var testBox=$('#testDomainInput').closest('.content-box');
        var strategyBox=$('#strategyLabDomainInput').closest('.content-box');
        testBox.find('.content-box-header h3').first().text(ui.testDomainTitle);
        strategyBox.find('.content-box-header h3').first().text(ui.strategyLabTitle);
        setButtonText('#testDomainBtn', ui.testAction);
        $('#testDomainResult').text(ui.testDomainHelp);
        $('#strategyLabDomainInput').closest('tr').find('td').first().text(ui.blockedDomain);
        $('#strategyLabServiceHostRow').find('td').first().text(ui.serviceHostLabel);
        $('#strategyLabServiceHostHelp').text(ui.serviceHostHelp);
        $('#strategyLabUdpRow').find('td').first().text(ui.genericUdpLabel);
        $('#strategyLabUdpPayloadButton').text(ui.chooseFile);
        $('#strategyLabUdpPayloadName').text(udpPayloadSelection.fileName || ui.noFileSelected);
        setButtonText('#strategyLabBtn', ui.runAction);
        $('#strategyLabQuicRow').find('td').first().text(ui.enableQuic);
        $('#strategyLabModeLabel').text(ui.modeLabel + ':');
        $('#strategyLabIpv6Label').text(ui.ipv6OptIn);
        $('#strategyLabMode option[value="standard"]').text(modeLabels.standard);
        $('#strategyLabMode option[value="extended"]').text(modeLabels.extended);
        var modeFontReference=$('#strategyLabInputsTable > tbody > tr > td.zapret-field-label').first();
        $('#strategyLabModeLabel').css({'font-size':modeFontReference.css('font-size'),'line-height':modeFontReference.css('line-height')});
        $('#strategyLabState,#circularState').text(label(statusLabels,'IDLE'));
        $('#strategyLabResultSummaryTitle').text(ui.resultSummary);
        $('#strategyLabResultOutcome').prev('strong').text(ui.outcome + ':');
        $('#strategyLabResultRestoration').prev('strong').text(ui.restoration + ':');
        $('#strategyLabSavedJobLabel').text(ui.savedJobLabel + ':');
        $('#strategyLabOpenSavedJob').text(ui.openSavedJob);
        $('#strategyLabCopyJob').attr('title',ui.copyJob).attr('aria-label',ui.copyJob);
        $('#circularControls h4').first().text(ui.circularTitle);
        $('#strategyLabCircularHelp').text(ui.circularHelp);
        var headers=$('#strategyLabShortlist thead th');
        headers.eq(3).text(ui.family); headers.eq(4).text(ui.endpoints); headers.eq(5).text(ui.replay); headers.eq(6).text(ui.completeProfile);
        $('#strategyLabRaw').closest('details').find('summary').first().text(ui.fullOutput);
    }

    var guidance = $('#strategyLabSummary').empty();
    strategyLabGuidance.forEach(function (paragraph, index) {
        $('<p/>').text(paragraph).css('margin-bottom', index === strategyLabGuidance.length - 1 ? 0 : '10px').appendTo(guidance);
    });
    $('#strategyLabUdpHelp').text(ui.udpHelp);
    $('#strategyLabQuicHelp').text(ui.quicHelp);
    applyStaticLocalization();

    function esc(value) { return $('<div/>').text(value == null ? '' : String(value)).html(); }
    function label(map, key) { return map[key] || key || '—'; }
    function apiPost(url, data, done) {
        $.ajax({type:'POST', url:url, data:data || {}, dataType:'json', timeout:200000,
            success:function (reply) { done(reply || {}); },
            error:function (xhr, status) { done({status:'error', transient:true, message:ui.requestFailed + status}); }});
    }
    function terminal(state) { return state === 'completed' || state === 'error'; }
    function jobSnapshot(data) {
        var jobId = String((data && data.job_id) || ''), state = String((data && data.state) || '');
        return /^job\.[A-Za-z0-9]+$/.test(jobId) && ['queued','running','cancel_requested','completed','error'].indexOf(state) !== -1;
    }
    function transientReply(data) { return !!(data && (data.transient === true || data.status === 'busy')); }
    function circularSnapshot(data) {
        var state = String((data && data.state) || '');
        return ['idle','queued','preparing','running','stop_requested','completed','error','restore_failed'].indexOf(state) !== -1;
    }
    function setBusy(busy) {
        strategyLabBusy = busy;
        $('#strategyLabBtn_progress').toggleClass('fa fa-spinner fa-pulse', busy);
        $('#strategyLabBtn').prop('disabled', busy); $('#strategyLabCancelBtn').prop('disabled', !busy || !activeJobId);
        $('#strategyLabIpv6Enabled').prop('disabled', busy);
        $('#strategyLabEnableQuic').prop('disabled', busy || !quicPreferenceReady || quicPreferenceSaving);
        $('#strategyLabUdpPayload,#strategyLabUdpPayloadButton,#strategyLabUdpPort,#strategyLabServiceHostInput').prop('disabled', busy);
        $('#strategyLabSavedJobInput,#strategyLabOpenSavedJob').prop('disabled', busy);
    }
    function stopPolling() { if (pollTimer !== null) { clearTimeout(pollTimer); pollTimer = null; } }
    function schedulePoll(callback) { stopPolling(); pollTimer = setTimeout(callback, 1000); }
    function toggleExtendedInput() {
        var extended = $('#strategyLabMode').val() === 'extended';
        $('#strategyLabUdpRow,#strategyLabQuicRow').toggle(extended);
    }
    function isIpv4Target(value) {
        var parts=String(value || '').split('.');
        if (parts.length !== 4) return false;
        for (var index=0;index<parts.length;index++) {
            if (!/^(0|[1-9][0-9]{0,2})$/.test(parts[index])) return false;
            var number=Number(parts[index]);
            if (number < 0 || number > 255) return false;
        }
        return true;
    }
    function toggleServiceIdentity() {
        var isIp=isIpv4Target($('#strategyLabDomainInput').val().trim());
        $('#strategyLabServiceHostRow').toggle(isIp);
        if (!isIp) $('#strategyLabServiceHostInput').val('');
    }
    function showInputError(message) {
        $('#strategyLabMessage').addClass('text-danger').text(message);
    }
    function clearInputError() {
        $('#strategyLabMessage').removeClass('text-danger');
    }
    function renderUdpPayloadSelection(kind, message) {
        var state=$('#strategyLabUdpPayloadState');
        state.removeClass('text-danger text-success text-muted');
        if (kind === 'error') state.addClass('text-danger');
        else if (kind === 'ready') state.addClass('text-success');
        else state.addClass('text-muted');
        state.text(message || '');
    }
    function renderUdpPayloadFileName(fileName) {
        $('#strategyLabUdpPayloadName').text(fileName || ui.noFileSelected);
    }
    function resetUdpPayloadSelection() {
        udpPayloadSelection.generation += 1;
        udpPayloadSelection.ready=false; udpPayloadSelection.reading=false;
        udpPayloadSelection.fileName=''; udpPayloadSelection.bytes=0; udpPayloadSelection.base64='';
        renderUdpPayloadFileName('');
        renderUdpPayloadSelection('', '');
    }
    function udpBytesToBase64(bytes) {
        var binary='';
        for (var offset=0;offset<bytes.length;offset+=4096) {
            binary+=String.fromCharCode.apply(null,bytes.subarray(offset,Math.min(offset+4096,bytes.length)));
        }
        return window.btoa(binary);
    }
    function stageUdpPayloadFile(file, done) {
        var generation=udpPayloadSelection.generation+1;
        udpPayloadSelection.generation=generation;
        udpPayloadSelection.ready=false; udpPayloadSelection.reading=!!file;
        udpPayloadSelection.fileName=file&&file.name?String(file.name):'';
        udpPayloadSelection.bytes=0; udpPayloadSelection.base64='';
        renderUdpPayloadFileName(udpPayloadSelection.fileName);
        if (!file) {
            renderUdpPayloadSelection('', '');
            if (done) done(false);
            return;
        }
        renderUdpPayloadSelection('info', ui.udpReading + ' ' + udpPayloadSelection.fileName);
        var reader=new FileReader();
        reader.onload=function(event){
            if (generation !== udpPayloadSelection.generation) return;
            var buffer=event.target&&event.target.result;
            if (!buffer || typeof buffer.byteLength !== 'number') {
                udpPayloadSelection.reading=false; renderUdpPayloadSelection('error', ui.udpRead); showInputError(ui.udpRead); if (done) done(false); return;
            }
            var bytes=new Uint8Array(buffer);
            if (bytes.byteLength<1||bytes.byteLength>udpPayloadMaxBytes) {
                udpPayloadSelection.reading=false; renderUdpPayloadSelection('error', ui.udpSize); showInputError(ui.udpSize); if (done) done(false); return;
            }
            try {
                udpPayloadSelection.base64=udpBytesToBase64(bytes);
            } catch (error) {
                udpPayloadSelection.reading=false; renderUdpPayloadSelection('error', ui.udpRead); showInputError(ui.udpRead); if (done) done(false); return;
            }
            udpPayloadSelection.bytes=bytes.byteLength; udpPayloadSelection.ready=true; udpPayloadSelection.reading=false;
            renderUdpPayloadSelection('ready', ui.udpReady + ': ' + udpPayloadSelection.fileName + ', ' + udpPayloadSelection.bytes + ' ' + ui.udpBytes + '.');
            clearInputError();
            if (done) done(true);
        };
        reader.onerror=function(){
            if (generation !== udpPayloadSelection.generation) return;
            udpPayloadSelection.reading=false; renderUdpPayloadSelection('error', ui.udpRead); showInputError(ui.udpRead); if (done) done(false);
        };
        reader.readAsArrayBuffer(file);
    }
    function loadQuicPreference() {
        apiPost('/api/zapret/strategy_lab_settings/quic', {}, function (data) {
            if (data.status === 'ok') $('#strategyLabEnableQuic').prop('checked', data.enabled === true);
            else { $('#strategyLabEnableQuic').prop('checked', false); showInputError(data.message || ui.quicSaveFailed); }
            quicPreferenceReady = true; quicPreferenceSaving = false; setBusy(strategyLabBusy);
        });
    }
    function saveQuicPreference(enabled, previous) {
        quicPreferenceSaving = true; setBusy(strategyLabBusy);
        apiPost('/api/zapret/strategy_lab_settings/quic', {enabled:enabled?'1':'0'}, function (data) {
            quicPreferenceSaving = false;
            if (data.status !== 'ok') {
                $('#strategyLabEnableQuic').prop('checked', previous);
                showInputError(data.message || ui.quicSaveFailed);
            } else {
                $('#strategyLabEnableQuic').prop('checked', data.enabled === true);
                clearInputError();
            }
            setBusy(strategyLabBusy);
        });
    }
    function fallbackPercent(stage) {
        return ({'00':0,'10':9,'20':18,'30':27,'40':36,'50':45,'60':55,'70':64,'80':73,'85':82,'90':91,'99':100})[String(stage || '00')] || 0;
    }
    function renderProgress(data) {
        var progress = data.progress || {}, percent = Number(progress.percent);
        if (!isFinite(percent)) percent = fallbackPercent(data.current_stage);
        percent = Math.max(0, Math.min(100, percent));
        var stageKey = progress.stage_key || ((Array.isArray(data.stages) ? data.stages : []).filter(function (s) { return s.number === data.current_stage; })[0] || {}).key || '';
        $('#strategyLabProgressBar').css('width', percent + '%').attr('aria-valuenow', percent).text(percent + '%');
        $('#strategyLabProgressText').text(ui.progress + ': ' + percent + '% — ' + label(stageLabels, stageKey));
    }
    function renderStages(data) {
        var html = '';
        (Array.isArray(data.stages) ? data.stages : []).forEach(function (stage) {
            var state = stage.status || 'PENDING';
            var style = state === 'PASS' ? 'success' : (state === 'RUNNING' ? 'primary' :
                ((state === 'ERROR' || state === 'FAIL' || state === 'FAILED' || state === 'RESTORE_FAILED') ? 'danger' :
                ((state === 'SKIPPED' || state === 'CANCELLED') ? 'warning' : 'default')));
            html += '<tr><td>' + esc(stage.number) + '</td><td>' + esc(label(stageLabels, stage.key)) + '</td>' +
                '<td><span class="label label-' + style + '">' + esc(label(statusLabels, state)) + '</span></td><td>' + esc(stage.message) + '</td></tr>';
        });
        $('#strategyLabStages tbody').html(html);
    }
    function shortlist(data) { return data.shortlist && Array.isArray(data.shortlist.items) ? data.shortlist.items : []; }
    function verifiedReplay(item) { return !!(item && item.profile_replay && item.profile_replay.verified === true); }
    function savedJobId(value) { return /^job\.[A-Za-z0-9]+$/.test(String(value || '')); }
    function displayJobId(jobId) {
        var value=String(jobId || ''), valid=savedJobId(value);
        $('#strategyLabJob').text(value || '—');
        $('#strategyLabCopyJob').prop('disabled',!valid).toggle(valid)
            .removeClass('strategy-lab-job-copied').attr('title',ui.copyJob).attr('aria-label',ui.copyJob);
        $('#strategyLabCopyJobFeedback').text('');
    }
    function selectedSavedJob() {
        try { var saved=sessionStorage.getItem(savedJobKey); return savedJobId(saved) ? saved : ''; }
        catch (error) { return ''; }
    }
    function rememberSavedJob(jobId) {
        try {
            if (savedJobId(jobId)) sessionStorage.setItem(savedJobKey, jobId);
            else sessionStorage.removeItem(savedJobKey);
        } catch (error) { /* session storage is optional; manual read still works */ }
    }
    function endpointText(item) {
        var values = [], seen = {};
        (Array.isArray(item.endpoints) ? item.endpoints : []).forEach(function (endpoint) {
            var value = endpoint.selected_ip || endpoint.remote_ip || endpoint.address || '';
            if (value && !seen[value]) { seen[value] = true; values.push(value); }
        });
        return values.join(', ');
    }
    function replayText(item) {
        var replay = item.profile_replay || {};
        if (replay.attempt_count != null) {
            var counts=String(replay.pass_count == null ? 0 : replay.pass_count) + '/' + String(replay.attempt_count);
            return verifiedReplay(item) ? counts : counts + ' (' + ui.unverifiedReplay + ')';
        }
        return verifiedReplay(item) ? (isRussian ? 'проверено' : 'verified') : '—';
    }
    function renderResultSummary(data) {
        var visible = terminal(data.state); $('#strategyLabResultBox').toggle(visible); if (!visible) return;
        $('#strategyLabResultTarget').text(data.target || '—');
        $('#strategyLabResultMode').text(label(modeLabels, data.mode) + ' / IPv6 ' + (data.ipv6_enabled === true ? (isRussian ? 'вкл.' : 'on') : (isRussian ? 'выкл.' : 'off')));
        $('#strategyLabResultOutcome').text(label(outcomeLabels, data.outcome || data.state));
        $('#strategyLabResultRestoration').text(data.restoration && data.restoration.verified === true ? ui.restorationPass : '—');
    }
    function renderProtocolScope(data, items) {
        var notice = $('#strategyLabProtocolScope');
        if (data.mode !== 'extended' || data.state !== 'completed') { notice.hide().text(''); return; }
        var counts = {tcp443:0,http80:0,quic443:0,udp:0}, unverified=0;
        items.forEach(function (item) {
            if (!verifiedReplay(item)) { unverified++; return; }
            var port = Number(item.port), protocol = String(item.protocol || '');
            if ((protocol === 'tls13' || protocol === 'tls12') && port === 443) counts.tcp443++;
            else if (protocol === 'http' && port === 80) counts.http80++;
            else if (protocol === 'quic' && port === 443) counts.quic443++;
            else if (protocol === 'udp') counts.udp++;
        });
        notice.text(ui.verifiedScope + ': ' +
            ui.scopeTcp + ' — ' + counts.tcp443 + '; ' +
            ui.scopeHttp + ' — ' + counts.http80 + '; ' +
            ui.scopeQuic + ' — ' + counts.quic443 + '; ' +
            ui.scopeUdp + ' — ' + counts.udp + '.' +
            (unverified ? ' ' + unverified + ' ' + ui.unverifiedScope + '.' : '') +
            ' ' + ui.scopeExplanation).show();
    }
    function renderShortlist(data) {
        var items = shortlist(data), html = ''; renderedProfiles = [];
        renderProtocolScope(data, items);
        items.forEach(function (item, index) {
            var profile = String(item.profile || item.strategy || ''), profileIndex = renderedProfiles.push(profile) - 1;
            var mark = index === 0 ? ' <span class="label label-success">#1</span>' : '';
            html += '<tr><td>' + (index + 1) + mark + '</td><td>' + esc(item.protocol || 'tls13') + '</td><td>' + esc(item.port || '—') + '</td>' +
                '<td>' + esc(item.family || '—') + '</td><td>' + esc(endpointText(item) || '—') + '</td><td>' + esc(replayText(item)) + '</td>' +
                '<td><pre style="margin:0;white-space:pre-wrap;">' + esc(profile) + '</pre><button type="button" class="btn btn-xs btn-default strategyLabCopyProfile" data-profile-index="' + profileIndex + '">' + esc(ui.copy) + '</button></td></tr>';
        });
        $('#strategyLabShortlist tbody').html(html); $('#strategyLabShortlistBox').toggle(items.length > 0);
        $('#strategyLabShortlistBox h4').first().text(items.some(function (item) { return !verifiedReplay(item); }) ? ui.savedProfiles : (isRussian ? 'Стабильные кандидаты' : 'Stable candidates'));
        var circularReady = data.circular_eligible === true && !historicalView; $('#circularControls').toggle(circularReady);
        if (data.state === 'completed') { if (circularReady) $('#strategyLabMessage').text(ui.circularReady); else if (!items.length) $('#strategyLabMessage').text(ui.noCandidates); }
    }
    function renderJob(data) {
        if (!jobSnapshot(data)) return false;
        clearInputError(); renderProgress(data); renderStages(data); renderResultSummary(data); renderShortlist(data);
        $('#strategyLabRaw').text(JSON.stringify(data, null, 2)); displayJobId(data.job_id);
        $('#strategyLabState').text(label(statusLabels, String(data.state).toUpperCase()));
        if (data.message) $('#strategyLabMessage').text(data.message);
        return true;
    }
    function renderTransientStatus() {
        $('#strategyLabMessage').text(ui.statusRetry);
        if (activeJobId) displayJobId(activeJobId);
    }
    function copyProfile(profile) {
        if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(profile);
        return new Promise(function (resolve, reject) {
            var area = $('<textarea/>').val(profile).css({position:'fixed',left:'-9999px'}).appendTo('body'); area[0].select();
            try { document.execCommand('copy') ? resolve() : reject(); } catch (error) { reject(error); } area.remove();
        });
    }
    $('#strategyLabCopyJob').on('click', function () {
        var id=$('#strategyLabJob').text().trim(), button=$(this);
        if (!savedJobId(id)) return;
        copyProfile(id).then(function () {
            if ($('#strategyLabJob').text().trim() !== id) return;
            button.addClass('strategy-lab-job-copied').attr('title',ui.jobCopied).attr('aria-label',ui.jobCopied);
            $('#strategyLabCopyJobFeedback').text(ui.jobCopied);
        }, function () {
            $('#strategyLabCopyJobFeedback').text(ui.jobCopyFailed);
        });
    });
    $(document).on('click', '.strategyLabCopyProfile', function () {
        var profile = renderedProfiles[Number($(this).attr('data-profile-index'))] || ''; if (!profile) return;
        copyProfile(profile).then(function () { $('#strategyLabMessage').text(ui.copied); }, function () { $('#strategyLabMessage').text(ui.copyFailed); });
    });
    function openSavedResult(jobId) {
        if (strategyLabBusy) return;
        if (!savedJobId(jobId)) { showInputError(ui.savedJobInvalid); return; }
        var lookup=++savedLookupToken;
        apiPost('/api/zapret/strategy_lab/result', {job_id:jobId}, function (data) {
            if (strategyLabBusy || lookup !== savedLookupToken) return;
            if (!jobSnapshot(data) || data.job_id !== jobId || !terminal(data.state)) {
                $('#strategyLabMessage').text((data && data.message) || ui.savedJobUnavailable);
                return;
            }
            stopPolling(); historicalView=true; activeJobId=jobId;
            $('#strategyLabSavedJobInput').val(jobId);
            rememberSavedJob(jobId); renderJob(data); setBusy(false);
        });
    }
    $('#strategyLabOpenSavedJob').click(function () {
        clearInputError(); openSavedResult($('#strategyLabSavedJobInput').val().trim());
    });
    $('#strategyLabSavedJobInput').on('keydown', function (event) {
        if (event.key === 'Enter') { event.preventDefault(); $('#strategyLabOpenSavedJob').click(); }
    });
    function fetchResult() {
        if (!activeJobId) return;
        apiPost('/api/zapret/strategy_lab/result', {job_id:activeJobId}, function (data) {
            if (!jobSnapshot(data)) {
                setBusy(false);
                if (!transientReply(data)) $('#strategyLabMessage').text(data.message || ui.statusFailed);
                return;
            }
            renderJob(data); setBusy(false);
            if (data.state === 'completed') $('#strategyLabMessage').text(data.message || ui.completed);
            else if (data.state === 'error') $('#strategyLabMessage').text(data.message || ui.failed);
        });
    }
    function pollStatus() {
        if (!activeJobId) return;
        apiPost('/api/zapret/strategy_lab/status', {job_id:activeJobId}, function (data) {
            if (!jobSnapshot(data)) {
                if (transientReply(data)) { renderTransientStatus(); setBusy(true); schedulePoll(pollStatus); return; }
                stopPolling(); setBusy(false); $('#strategyLabMessage').text(data.message || ui.statusFailed); return;
            }
            renderJob(data);
            if (terminal(data.state)) { stopPolling(); fetchResult(); return; }
            setBusy(true); schedulePoll(pollStatus);
        });
    }
    function discoverActive(attempt) {
        apiPost('/api/zapret/strategy_lab/status', {job_id:'-'}, function (data) {
            if (jobSnapshot(data)) {
                historicalView=false; activeJobId=data.job_id; renderJob(data);
                if (terminal(data.state)) { setBusy(false); fetchResult(); }
                else { setBusy(true); pollStatus(); }
                return;
            }
            if (data.status === 'idle') {
                activeJobId=''; setBusy(false);
                var remembered=selectedSavedJob();
                if (remembered) openSavedResult(remembered);
                return;
            }
            if (transientReply(data) && attempt < discoveryRetryLimit) {
                renderTransientStatus(); setBusy(true); schedulePoll(function(){ discoverActive(attempt + 1); }); return;
            }
            activeJobId=''; setBusy(false); $('#strategyLabMessage').text(data.message || ui.statusFailed);
        });
    }

    $('#testDomainBtn').click(function () {
        var domain = $('#testDomainInput').val().trim(); if (!domain) return;
        $('#testDomainBtn_progress').addClass('fa fa-spinner fa-pulse'); $('#testDomainResult').text(isRussian ? 'Проверка...' : 'Testing...');
        ajaxCall('/api/zapret/diagnostics/testdomain', {domain:domain}, function (data) {
            $('#testDomainBtn_progress').removeClass('fa fa-spinner fa-pulse');
            $('#testDomainResult').text(data.status === 'ok' ? data.result : (isRussian ? 'Ошибка: ' : 'Error: ') + (data.message || (isRussian ? 'Неизвестная ошибка' : 'Unknown error')));
        });
    });
    function startStrategyLab(target, serviceHost, mode, enableQuic, udpPort, udpPayloadBase64, ipv6Enabled) {
        apiPost('/api/zapret/strategy_lab/start', {target:target,service_host:serviceHost,mode:mode,language:isRussian?'ru':'en',enable_quic:enableQuic,udp_port:udpPort,udp_payload_base64:udpPayloadBase64,ipv6_enabled:ipv6Enabled}, function (data) {
            if (data.status === 'busy' && /^job\.[A-Za-z0-9]+$/.test(String(data.job_id || ''))) {
                activeJobId=data.job_id; displayJobId(activeJobId); setBusy(true); pollStatus(); return;
            }
            if (data.status !== 'ok' || !data.job_id) {
                if (transientReply(data)) { renderTransientStatus(); setBusy(true); discoverActive(0); return; }
                setBusy(false); showInputError(data.message || ui.failed); return;
            }
            activeJobId=data.job_id;
            renderJob({job_id:activeJobId,state:'queued',target:target,mode:mode,ipv6_enabled:ipv6Enabled==='1',current_stage:'00',progress:{percent:0,stage:'00',stage_key:'target_initialization',message:''},stages:[]});
            $('#strategyLabMessage').text(ui.running); setBusy(true); pollStatus();
        });
    }
    $('#strategyLabMode').change(toggleExtendedInput);
    $('#strategyLabDomainInput').on('input', toggleServiceIdentity);
    $('#strategyLabEnableQuic').change(function () {
        var enabled=$(this).prop('checked'), previous=!enabled;
        saveQuicPreference(enabled, previous);
    });
    $('#strategyLabUdpPayloadButton').click(function () {
        if ($(this).prop('disabled')) return;
        var input=document.getElementById('strategyLabUdpPayload');
        if (input) input.click();
    });
    $('#strategyLabUdpPayload').change(function () {
        var file=(this.files&&this.files.length)?this.files[0]:null;
        stageUdpPayloadFile(file);
    });
    $('#strategyLabBtn').click(function () {
        var target=$('#strategyLabDomainInput').val().trim(), mode=$('#strategyLabMode').val(); if (!target) return;
        var serviceHost=isIpv4Target(target)?$('#strategyLabServiceHostInput').val().trim():'';
        var enableQuic=$('#strategyLabEnableQuic').prop('checked')?'1':'0';
        var ipv6Enabled=$('#strategyLabIpv6Enabled').prop('checked')?'1':'0';
        var udpPort='', nativeFile=null, fileInput=null;
        if (mode === 'extended') {
            udpPort=$('#strategyLabUdpPort').val().trim(); fileInput=document.getElementById('strategyLabUdpPayload');
            nativeFile=fileInput&&fileInput.files&&fileInput.files.length?fileInput.files[0]:null;
            var hasPayload=udpPayloadSelection.ready||udpPayloadSelection.reading||!!nativeFile;
            if (!!udpPort !== !!hasPayload) { showInputError(ui.udpPair); return; }
            if (udpPayloadSelection.reading) { showInputError(ui.udpNotReady); return; }
        }
        function beginStart(payloadBase64) {
            clearInputError(); stopPolling(); activeJobId=''; displayJobId(''); historicalView=false; savedLookupToken++; rememberSavedJob(''); renderedProfiles=[]; $('#strategyLabStages tbody,#strategyLabShortlist tbody').empty();
            $('#strategyLabShortlistBox,#strategyLabResultBox,#circularControls').hide(); $('#strategyLabRaw').text(''); $('#strategyLabMessage').text(ui.running); setBusy(true);
            $('#strategyLabState').text(label(statusLabels,'QUEUED'));
            renderProgress({current_stage:'00',progress:{percent:0,stage_key:'target_initialization'}});
            startStrategyLab(target,serviceHost,mode,enableQuic,udpPort,payloadBase64,ipv6Enabled);
        }
        if (mode !== 'extended' || !udpPort) { beginStart(''); return; }
        if (udpPayloadSelection.ready) { beginStart(udpPayloadSelection.base64); return; }
        if (!nativeFile) { showInputError(ui.udpPair); return; }
        stageUdpPayloadFile(nativeFile, function (ready) {
            if (ready && udpPayloadSelection.ready) beginStart(udpPayloadSelection.base64);
        });
    });
    $('#strategyLabCancelBtn').click(function(){
        if(!activeJobId)return;
        apiPost('/api/zapret/strategy_lab/cancel',{job_id:activeJobId},function(data){
            if (jobSnapshot(data)) { renderJob(data); $('#strategyLabMessage').text(ui.cancel); setBusy(true); schedulePoll(pollStatus); return; }
            if (transientReply(data)) { renderTransientStatus(); setBusy(true); schedulePoll(pollStatus); return; }
            $('#strategyLabMessage').text(data.message || ui.statusFailed);
        });
    });

    function pollCircular() {
        apiPost('/api/zapret/circular/status',{},function(data){
            if (!circularSnapshot(data)) {
                if (transientReply(data)) { circularTimer=setTimeout(pollCircular,1000); return; }
                $('#circularMessage').text(data.message || ''); return;
            }
            var state=data.state; $('#circularState').text(label(statusLabels,String(state).toUpperCase()));
            $('#circularMessage').text(circularMessages[state] || data.message || '');
            $('#circularRaw').text(ui.stateLabel + ': ' + label(statusLabels,String(state).toUpperCase()));
            var live=['queued','preparing','running','stop_requested'].indexOf(state)!==-1; $('#circularStartBtn').prop('disabled',live); $('#circularStopBtn').prop('disabled',!live);
            if(live)circularTimer=setTimeout(pollCircular,1000);
        });
    }
    $('#circularStartBtn').click(function(){if(!activeJobId)return;if(circularTimer!==null)clearTimeout(circularTimer);apiPost('/api/zapret/circular/start',{job_id:activeJobId},function(){pollCircular();});});
    $('#circularStopBtn').click(function(){apiPost('/api/zapret/circular/stop',{},function(){pollCircular();});});

    loadQuicPreference(); discoverActive(0);
    toggleExtendedInput(); toggleServiceIdentity(); pollCircular();
});
</script>
<style>
.diagnostics-form-table {
    table-layout:fixed;
    width:100%;
}
.diagnostics-form-table > tbody > tr > td.zapret-field-label {
    width:25%;
    white-space:nowrap;
    vertical-align:middle;
}
.diagnostics-form-table > tbody > tr > td.zapret-field-value {
    vertical-align:middle;
}
#strategyLabModeCell {
    width:260px;
}
.strategy-lab-mode-control {
    display:flex;
    align-items:center;
    justify-content:flex-end;
    gap:8px;
}
#strategyLabModeLabel,#strategyLabIpv6Label {
    flex:0 0 auto;
    text-align:right;
    white-space:nowrap;
}
#strategyLabMode {
    width:160px;
    flex:0 0 160px;
}
.strategy-lab-ipv6-box {
    width:160px;
    flex:0 0 160px;
    display:flex;
    align-items:center;
    justify-content:flex-start;
    margin:0;
    min-height:24px;
}
#strategyLabIpv6Enabled { margin:0; }
.strategy-lab-file-picker {
    display:flex;
    align-items:center;
    gap:8px;
    min-width:0;
    margin-bottom:4px;
}
.strategy-lab-native-file-input {
    position:absolute;
    left:-10000px;
    width:1px;
    height:1px;
    opacity:0;
    overflow:hidden;
}
.strategy-lab-job-inline { display:inline-flex; align-items:center; vertical-align:middle; white-space:nowrap; gap:3px; }
.strategy-lab-copy-job {
    position:relative; display:inline-flex; width:24px; height:22px;
    padding:0; border:0; border-radius:3px; background:transparent;
    color:#5cb85c; vertical-align:middle; cursor:pointer;
}
.strategy-lab-copy-job::before,.strategy-lab-copy-job::after {
    content:''; position:absolute; box-sizing:border-box;
    width:12px; height:11px; border:2px solid currentColor; border-radius:2px;
}
.strategy-lab-copy-job::before { left:5px; top:3px; }
.strategy-lab-copy-job::after { left:9px; top:7px; }
.strategy-lab-copy-job:hover,.strategy-lab-copy-job:focus,.strategy-lab-job-copied {
    color:#449d44; background:rgba(92,184,92,.14);
}
.strategy-lab-copy-job:focus-visible { outline:2px solid #5cb85c; outline-offset:1px; }
.strategy-lab-copy-job:disabled { opacity:.45; cursor:default; }
#strategyLabUdpPayloadName {
    min-width:0;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}
</style>

<div class="content-box __mb"><div class="content-box-header"><h3>{{ lang._('Test Domain Connectivity') }}</h3></div>
<div class="content-box-main"><div class="table-responsive"><table class="table table-striped diagnostics-form-table" id="testDomainTable"><tbody><tr><td class="zapret-field-label">{{ lang._('Domain') }}</td><td class="zapret-field-value"><input type="text" class="form-control" id="testDomainInput" placeholder="example.com"/></td><td style="width:150px;"><button class="btn btn-primary" id="testDomainBtn" type="button">{{ lang._('Test') }} <i id="testDomainBtn_progress"></i></button></td></tr></tbody></table></div><pre id="testDomainResult" style="max-height:300px;overflow-y:auto;white-space:pre-wrap;">{{ lang._('Enter a domain and click Test to check HTTPS connectivity.') }}</pre></div></div>
<div class="content-box"><div class="content-box-header"><h3>{{ lang._('Strategy Lab') }}</h3></div><div class="content-box-main">
<div class="table-responsive"><table class="table table-striped diagnostics-form-table" id="strategyLabInputsTable"><tbody><tr><td class="zapret-field-label">{{ lang._('Blocked Domain / IP') }}</td><td class="zapret-field-value"><input type="text" class="form-control" id="strategyLabDomainInput" placeholder="rutracker.org / 203.0.113.10 / 2001:db8::10"/></td><td id="strategyLabModeCell"><div class="strategy-lab-mode-control"><span id="strategyLabModeLabel">Mode:</span><select class="form-control" id="strategyLabMode"><option value="standard">{{ lang._('Standard') }}</option><option value="extended">{{ lang._('Extended') }}</option></select></div><div class="strategy-lab-mode-control"><span id="strategyLabIpv6Label">IPv6</span><label class="strategy-lab-ipv6-box"><input type="checkbox" id="strategyLabIpv6Enabled" value="1" aria-label="IPv6" /></label></div></td><td style="width:190px;"><button class="btn btn-primary" id="strategyLabBtn" type="button">{{ lang._('Run') }} <i id="strategyLabBtn_progress"></i></button> <button class="btn btn-warning" id="strategyLabCancelBtn" type="button" disabled>{{ lang._('Stop') }}</button></td></tr>
<tr id="strategyLabServiceHostRow" style="display:none;"><td class="zapret-field-label">Host / SNI (optional)</td><td class="zapret-field-value"><input type="text" class="form-control" id="strategyLabServiceHostInput" placeholder="example.com"/></td><td colspan="2"><small id="strategyLabServiceHostHelp"></small></td></tr>
<tr id="strategyLabUdpRow" style="display:none;"><td class="zapret-field-label">{{ lang._('Generic UDP (optional)') }}</td><td class="zapret-field-value"><input type="number" min="1" max="65535" class="form-control" id="strategyLabUdpPort" placeholder="53"/></td><td colspan="2"><div class="strategy-lab-file-picker"><button type="button" class="btn btn-default" id="strategyLabUdpPayloadButton" aria-controls="strategyLabUdpPayload">Choose file</button><span id="strategyLabUdpPayloadName" class="text-muted" aria-live="polite">No file selected</span><input type="file" class="strategy-lab-native-file-input" id="strategyLabUdpPayload" tabindex="-1" aria-hidden="true"/></div><small id="strategyLabUdpHelp"></small><br/><small id="strategyLabUdpPayloadState" class="text-muted"></small></td></tr>
<tr id="strategyLabQuicRow" style="display:none;"><td class="zapret-field-label">{{ lang._('Enable QUIC') }}</td><td class="zapret-field-value"><input type="checkbox" id="strategyLabEnableQuic" disabled/></td><td colspan="2"><small id="strategyLabQuicHelp"></small></td></tr></tbody></table></div>
<div id="strategyLabSummary"></div>
<div class="form-inline" id="strategyLabSavedJobControls" style="margin:10px 0;">
    <label for="strategyLabSavedJobInput" id="strategyLabSavedJobLabel">Saved job:</label>
    <input type="text" class="form-control input-sm" id="strategyLabSavedJobInput" placeholder="job.XXXXXXXX" maxlength="100" autocomplete="off" style="max-width:220px;" />
    <button type="button" class="btn btn-default btn-sm" id="strategyLabOpenSavedJob">Open result</button>
</div>
<p><strong>Job:</strong> <span class="strategy-lab-job-inline"><code id="strategyLabJob">—</code><button type="button" id="strategyLabCopyJob" class="strategy-lab-copy-job" style="display:none;" title="Copy Job ID" aria-label="Copy Job ID" disabled></button></span><span id="strategyLabCopyJobFeedback" class="sr-only" aria-live="polite"></span> &nbsp; <strong>{{ lang._('Status') }}:</strong> <span id="strategyLabState">idle</span></p><p id="strategyLabMessage"></p>
<div id="strategyLabProgressBox"><div class="progress" style="margin-bottom:5px;"><div id="strategyLabProgressBar" class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" style="width:0%;">0%</div></div><p id="strategyLabProgressText"></p></div>
<div class="table-responsive"><table class="table table-condensed" id="strategyLabStages"><thead><tr><th>#</th><th>{{ lang._('Stage') }}</th><th>{{ lang._('Status') }}</th><th>{{ lang._('Details') }}</th></tr></thead><tbody></tbody></table></div>
<div id="strategyLabResultBox" class="well" style="display:none;"><h4 id="strategyLabResultSummaryTitle">{{ lang._('Result summary') }}</h4><div class="row"><div class="col-sm-3"><strong>{{ lang._('Target') }}:</strong> <span id="strategyLabResultTarget">—</span></div><div class="col-sm-3"><strong>{{ lang._('Mode') }}:</strong> <span id="strategyLabResultMode">—</span></div><div class="col-sm-3"><strong>{{ lang._('Outcome') }}:</strong> <span id="strategyLabResultOutcome">—</span></div><div class="col-sm-3"><strong>{{ lang._('Restoration') }}:</strong> <span id="strategyLabResultRestoration">—</span></div></div></div>
<p id="strategyLabProtocolScope" class="text-muted" style="display:none;margin:12px 0;"></p>
<div id="strategyLabShortlistBox" style="display:none;"><h4>{{ lang._('Stable candidates') }}</h4><div class="table-responsive"><table class="table table-striped" id="strategyLabShortlist"><thead><tr><th>#</th><th>{{ lang._('Protocol') }}</th><th>{{ lang._('Port') }}</th><th>{{ lang._('Family') }}</th><th>{{ lang._('Endpoints') }}</th><th>{{ lang._('Replay') }}</th><th>{{ lang._('Complete Traffic Strategy profile') }}</th></tr></thead><tbody></tbody></table></div></div>
<div id="circularControls" class="well" style="display:none;"><h4>{{ lang._('Temporary circular validation') }}</h4><p id="strategyLabCircularHelp" class="text-muted"></p><button class="btn btn-success" id="circularStartBtn" type="button">{{ lang._('Start') }}</button> <button class="btn btn-warning" id="circularStopBtn" type="button" disabled>{{ lang._('Stop') }}</button><span style="margin-left:10px;"><strong>{{ lang._('Status') }}:</strong> <span id="circularState">idle</span></span><p id="circularMessage" style="margin-top:10px;"></p><pre id="circularRaw" style="max-height:200px;overflow-y:auto;white-space:pre-wrap;font-size:11px;"></pre></div>
<details><summary>{{ lang._('Full output (advanced)') }}</summary><pre id="strategyLabRaw" style="max-height:400px;overflow-y:auto;white-space:pre-wrap;font-size:11px;"></pre></details>
</div></div>