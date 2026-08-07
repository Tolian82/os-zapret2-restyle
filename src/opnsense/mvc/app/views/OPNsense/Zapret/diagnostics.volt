{# Copyright (C) 2026 Umur Gorur. All rights reserved. #}
<script>
$(document).ready(function () {
    var activeJobId = '', pollTimer = null, circularTimer = null, renderedProfiles = [];
    var udpPayloadMaxBytes = 4096;
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
        IDLE:'ОЖИДАНИЕ', QUEUED:'В ОЧЕРЕДИ', PREPARING:'ПОДГОТОВКА', PENDING:'ОЖИДАНИЕ', RUNNING:'ВЫПОЛНЯЕТСЯ',
        STOP_REQUESTED:'ОСТАНОВКА ЗАПРОШЕНА', COMPLETED:'ЗАВЕРШЕНО', PASS:'УСПЕШНО', FAIL:'ОШИБКА', FAILED:'ОШИБКА',
        ERROR:'ОШИБКА', TIMEOUT:'ТАЙМ-АУТ', SKIPPED:'ПРОПУЩЕНО', CANCELLED:'ОТМЕНЕНО', RESTORE_FAILED:'ВОССТАНОВЛЕНИЕ НЕ ВЫПОЛНЕНО'
    } : {
        IDLE:'IDLE', QUEUED:'QUEUED', PREPARING:'PREPARING', PENDING:'PENDING', RUNNING:'RUNNING',
        STOP_REQUESTED:'STOP REQUESTED', COMPLETED:'COMPLETED', PASS:'PASS', FAIL:'FAIL', FAILED:'FAILED', ERROR:'ERROR',
        TIMEOUT:'TIMEOUT', SKIPPED:'SKIPPED', CANCELLED:'CANCELED', RESTORE_FAILED:'RESTORE FAILED'
    };
    var outcomeLabels = isRussian ? {
        SUCCESS:'Успешно', NO_CANDIDATE:'Рабочие стратегии не найдены', TARGET_ACCESSIBLE:'Цель доступна без обхода',
        PARTIAL:'Частичный результат', TIMEOUT:'Тайм-аут', ERROR:'Ошибка', RESTORE_FAILED:'Ошибка восстановления'
    } : {
        SUCCESS:'Success', NO_CANDIDATE:'No working candidate', TARGET_ACCESSIBLE:'Target accessible without bypass',
        PARTIAL:'Partial result', TIMEOUT:'Timeout', ERROR:'Error', RESTORE_FAILED:'Restoration failed'
    };
    var modeLabels = isRussian ? {standard:'Основной', extended:'Расширенный'} : {standard:'Standard', extended:'Extended'};
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
        'Введите домен, который в настоящее время блокируется вашим интернет-провайдером, и нажмите «Запустить». Основной режим проверки ограничен 150 секундами, расширенный — 270 секундами. После завершения будут показаны стабильные стратегии, которые обеспечили доступ к сайту.',
        'Изучите результат и добавьте необходимый профиль в используемую стратегию на странице «Настройки».'
    ] : [
        'Enter a domain that is currently blocked by your ISP and click “Run.” Standard mode is limited to 150 seconds and extended mode to 270 seconds. Stable strategies that successfully provide access to the site will be reported after completion.',
        'Review the results and add the required profile to the strategy currently in use on the “Settings” page.'
    ];
    var ui = isRussian ? {
        running:'Strategy Lab выполняет проверку.', completed:'Проверка завершена.', cancel:'Остановка запрошена. Выполняется обязательное восстановление Zapret2.',
        failed:'Проверка завершилась с ошибкой.', noCandidates:'Стабильные кандидаты не найдены.', circularReady:'Можно временно проверить найденные стратегии в браузере.',
        udpPair:'Для общей UDP-проверки укажите одновременно порт и payload-файл.', udpSize:'Payload-файл должен иметь размер от 1 до 4096 байт.',
        udpRead:'Не удалось прочитать payload-файл.', copy:'Копировать профиль', copied:'Профиль скопирован.', copyFailed:'Не удалось скопировать профиль.',
        progress:'Прогресс', restorationPass:'Успешно', requestFailed:'Ошибка запроса: '
    } : {
        running:'Strategy Lab is running.', completed:'The check is complete.', cancel:'Cancellation requested. Mandatory Zapret2 restoration is running.',
        failed:'The check ended with an error.', noCandidates:'No stable candidates were found.', circularReady:'The candidates can now be tested temporarily in a browser.',
        udpPair:'Generic UDP testing requires both a port and a payload file.', udpSize:'The payload file must contain between 1 and 4096 bytes.',
        udpRead:'The payload file could not be read.', copy:'Copy profile', copied:'Profile copied.', copyFailed:'The profile could not be copied.',
        progress:'Progress', restorationPass:'Pass', requestFailed:'Request failed: '
    };

    var guidance = $('#strategyLabSummary').empty();
    strategyLabGuidance.forEach(function (paragraph, index) {
        $('<p/>').text(paragraph).css('margin-bottom', index === strategyLabGuidance.length - 1 ? 0 : '10px').appendTo(guidance);
    });

    function esc(value) { return $('<div/>').text(value == null ? '' : String(value)).html(); }
    function label(map, key) { return map[key] || key || '—'; }
    function apiPost(url, data, done) {
        $.ajax({type:'POST', url:url, data:data || {}, dataType:'json', timeout:200000,
            success:function (reply) { done(reply || {}); }, error:function (xhr, status) { done({status:'error', message:ui.requestFailed + status}); }});
    }
    function terminal(state) { return state === 'completed' || state === 'error'; }
    function setBusy(busy) {
        $('#strategyLabBtn_progress').toggleClass('fa fa-spinner fa-pulse', busy);
        $('#strategyLabBtn').prop('disabled', busy); $('#strategyLabCancelBtn').prop('disabled', !busy || !activeJobId);
    }
    function stopPolling() { if (pollTimer !== null) { clearTimeout(pollTimer); pollTimer = null; } }
    function toggleUdpInput() { $('#strategyLabUdpRow').toggle($('#strategyLabMode').val() === 'extended'); }
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
        if (replay.attempt_count != null) return String(replay.pass_count || 0) + '/' + String(replay.attempt_count);
        return replay.verified === true ? (isRussian ? 'проверено' : 'verified') : '—';
    }
    function renderResultSummary(data) {
        var visible = terminal(data.state); $('#strategyLabResultBox').toggle(visible); if (!visible) return;
        $('#strategyLabResultTarget').text(data.target || '—');
        $('#strategyLabResultMode').text(label(modeLabels, data.mode));
        $('#strategyLabResultOutcome').text(label(outcomeLabels, data.outcome || data.state));
        $('#strategyLabResultRestoration').text(data.restoration && data.restoration.verified === true ? ui.restorationPass : '—');
    }
    function renderShortlist(data) {
        var items = shortlist(data), html = ''; renderedProfiles = [];
        items.forEach(function (item, index) {
            var profile = String(item.profile || item.strategy || ''), profileIndex = renderedProfiles.push(profile) - 1;
            var mark = index === 0 ? ' <span class="label label-success">#1</span>' : '';
            html += '<tr><td>' + (index + 1) + mark + '</td><td>' + esc(item.protocol || 'tls13') + '</td><td>' + esc(item.port || '—') + '</td>' +
                '<td>' + esc(item.family || '—') + '</td><td>' + esc(endpointText(item) || '—') + '</td><td>' + esc(replayText(item)) + '</td>' +
                '<td><pre style="margin:0;white-space:pre-wrap;">' + esc(profile) + '</pre><button type="button" class="btn btn-xs btn-default strategyLabCopyProfile" data-profile-index="' + profileIndex + '">' + esc(ui.copy) + '</button></td></tr>';
        });
        $('#strategyLabShortlist tbody').html(html); $('#strategyLabShortlistBox').toggle(items.length > 0);
        var circularReady = data.circular_eligible === true; $('#circularControls').toggle(circularReady);
        if (data.state === 'completed') { if (circularReady) $('#strategyLabMessage').text(ui.circularReady); else if (!items.length) $('#strategyLabMessage').text(ui.noCandidates); }
    }
    function renderJob(data) {
        renderProgress(data); renderStages(data); renderResultSummary(data); renderShortlist(data);
        $('#strategyLabRaw').text(JSON.stringify(data, null, 2)); $('#strategyLabJob').text(data.job_id || activeJobId || '—');
        $('#strategyLabState').text(label(statusLabels, String(data.state || data.status || 'idle').toUpperCase()));
        if (data.message) $('#strategyLabMessage').text(data.message);
    }
    function copyProfile(profile) {
        if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(profile);
        return new Promise(function (resolve, reject) {
            var area = $('<textarea/>').val(profile).css({position:'fixed',left:'-9999px'}).appendTo('body'); area[0].select();
            try { document.execCommand('copy') ? resolve() : reject(); } catch (error) { reject(error); } area.remove();
        });
    }
    $(document).on('click', '.strategyLabCopyProfile', function () {
        var profile = renderedProfiles[Number($(this).attr('data-profile-index'))] || ''; if (!profile) return;
        copyProfile(profile).then(function () { $('#strategyLabMessage').text(ui.copied); }, function () { $('#strategyLabMessage').text(ui.copyFailed); });
    });
    function fetchResult() {
        if (!activeJobId) return;
        apiPost('/api/zapret/strategy_lab/result', {job_id:activeJobId}, function (data) {
            renderJob(data); setBusy(false);
            if (data.state === 'completed') $('#strategyLabMessage').text(data.message || ui.completed);
            else if (data.state === 'error') $('#strategyLabMessage').text(data.message || ui.failed);
        });
    }
    function pollStatus() {
        if (!activeJobId) return;
        apiPost('/api/zapret/strategy_lab/status', {job_id:activeJobId}, function (data) {
            renderJob(data); if (terminal(data.state)) { stopPolling(); fetchResult(); return; }
            setBusy(true); pollTimer = setTimeout(pollStatus, 1000);
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
    function startStrategyLab(target, mode, udpPort, udpPayloadBase64) {
        apiPost('/api/zapret/strategy_lab/start', {target:target,mode:mode,language:isRussian?'ru':'en',udp_port:udpPort,udp_payload_base64:udpPayloadBase64}, function (data) {
            if (data.status !== 'ok' || !data.job_id) { setBusy(false); $('#strategyLabMessage').text(data.message || ui.failed); return; }
            activeJobId=data.job_id; $('#strategyLabJob').text(activeJobId); pollStatus();
        });
    }
    $('#strategyLabMode').change(toggleUdpInput);
    $('#strategyLabBtn').click(function () {
        var target=$('#strategyLabDomainInput').val().trim(), mode=$('#strategyLabMode').val(); if (!target) return;
        stopPolling(); activeJobId=''; renderedProfiles=[]; $('#strategyLabStages tbody,#strategyLabShortlist tbody').empty();
        $('#strategyLabShortlistBox,#strategyLabResultBox,#circularControls').hide(); $('#strategyLabRaw').text(''); $('#strategyLabMessage').text(ui.running); setBusy(true);
        renderProgress({current_stage:'00',progress:{percent:0,stage_key:'target_initialization'}});
        if (mode !== 'extended') { startStrategyLab(target,mode,'',''); return; }
        var udpPort=$('#strategyLabUdpPort').val().trim(), fileInput=document.getElementById('strategyLabUdpPayload');
        var payloadFile=fileInput&&fileInput.files?fileInput.files[0]:null;
        if (!udpPort&&!payloadFile) { startStrategyLab(target,mode,'',''); return; }
        if (!udpPort||!payloadFile) { setBusy(false); $('#strategyLabMessage').text(ui.udpPair); return; }
        if (payloadFile.size<1||payloadFile.size>udpPayloadMaxBytes) { setBusy(false); $('#strategyLabMessage').text(ui.udpSize); return; }
        var reader=new FileReader();
        reader.onload=function(event){var encoded=String((event.target&&event.target.result)||''),delimiter=encoded.indexOf(',');
            if(delimiter<0||!encoded.substring(delimiter+1)){setBusy(false);$('#strategyLabMessage').text(ui.udpRead);return;}
            startStrategyLab(target,mode,udpPort,encoded.substring(delimiter+1));};
        reader.onerror=function(){setBusy(false);$('#strategyLabMessage').text(ui.udpRead);}; reader.readAsDataURL(payloadFile);
    });
    $('#strategyLabCancelBtn').click(function(){if(!activeJobId)return;apiPost('/api/zapret/strategy_lab/cancel',{job_id:activeJobId},function(data){renderJob(data);$('#strategyLabMessage').text(ui.cancel);});});

    function pollCircular() {
        apiPost('/api/zapret/circular/status',{},function(data){
            var state=data.state||data.status||'idle'; $('#circularState').text(label(statusLabels,String(state).toUpperCase()));
            $('#circularMessage').text(circularMessages[state] || data.message || ''); $('#circularRaw').text(JSON.stringify(data,null,2));
            var live=['queued','preparing','running','stop_requested'].indexOf(state)!==-1; $('#circularStartBtn').prop('disabled',live); $('#circularStopBtn').prop('disabled',!live);
            if(live)circularTimer=setTimeout(pollCircular,1000);
        });
    }
    $('#circularStartBtn').click(function(){if(!activeJobId)return;if(circularTimer!==null)clearTimeout(circularTimer);apiPost('/api/zapret/circular/start',{job_id:activeJobId},function(){pollCircular();});});
    $('#circularStopBtn').click(function(){apiPost('/api/zapret/circular/stop',{},function(){pollCircular();});});

    apiPost('/api/zapret/strategy_lab/status',{job_id:'-'},function(data){if(!data.job_id)return;activeJobId=data.job_id;renderJob(data);if(terminal(data.state)){setBusy(false);fetchResult();}else{setBusy(true);pollStatus();}});
    toggleUdpInput(); pollCircular();
});
</script>

<section class="page-content-main"><div class="container-fluid">
<div class="row"><section class="col-xs-12"><div class="content-box"><div class="content-box-header"><h3>{{ lang._('Test Domain Connectivity') }}</h3></div>
<div class="content-box-main"><div class="table-responsive"><table class="table table-striped"><tbody><tr><td style="width:200px;">{{ lang._('Domain') }}</td><td><input type="text" class="form-control" id="testDomainInput" placeholder="example.com"/></td><td style="width:150px;"><button class="btn btn-primary" id="testDomainBtn" type="button">{{ lang._('Test') }} <i id="testDomainBtn_progress"></i></button></td></tr></tbody></table></div><pre id="testDomainResult" style="max-height:300px;overflow-y:auto;white-space:pre-wrap;">{{ lang._('Enter a domain and click Test to check HTTPS connectivity.') }}</pre></div></div></section></div>
<div class="row"><section class="col-xs-12"><div class="content-box"><div class="content-box-header"><h3>{{ lang._('Strategy Lab') }}</h3></div><div class="content-box-main">
<div class="table-responsive"><table class="table table-striped"><tbody><tr><td style="width:200px;">{{ lang._('Blocked Domain') }}</td><td><input type="text" class="form-control" id="strategyLabDomainInput" placeholder="rutracker.org"/></td><td style="width:160px;"><select class="form-control" id="strategyLabMode"><option value="standard">{{ lang._('Standard') }}</option><option value="extended">{{ lang._('Extended') }}</option></select></td><td style="width:190px;"><button class="btn btn-primary" id="strategyLabBtn" type="button">{{ lang._('Run') }} <i id="strategyLabBtn_progress"></i></button> <button class="btn btn-warning" id="strategyLabCancelBtn" type="button" disabled>{{ lang._('Stop') }}</button></td></tr>
<tr id="strategyLabUdpRow" style="display:none;"><td>{{ lang._('Generic UDP (optional)') }}</td><td><input type="number" min="1" max="65535" class="form-control" id="strategyLabUdpPort" placeholder="53"/></td><td colspan="2"><input type="file" class="form-control" id="strategyLabUdpPayload"/> <small>{{ lang._('Request payload file, 1–4096 bytes. Both port and file are required.') }}</small></td></tr></tbody></table></div>
<div id="strategyLabSummary"></div><p><strong>Job:</strong> <code id="strategyLabJob">—</code> &nbsp; <strong>{{ lang._('Status') }}:</strong> <span id="strategyLabState">idle</span></p><p id="strategyLabMessage"></p>
<div id="strategyLabProgressBox"><div class="progress" style="margin-bottom:5px;"><div id="strategyLabProgressBar" class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" style="width:0%;">0%</div></div><p id="strategyLabProgressText"></p></div>
<div class="table-responsive"><table class="table table-condensed" id="strategyLabStages"><thead><tr><th>#</th><th>{{ lang._('Stage') }}</th><th>{{ lang._('Status') }}</th><th>{{ lang._('Details') }}</th></tr></thead><tbody></tbody></table></div>
<div id="strategyLabResultBox" class="well" style="display:none;"><h4>{{ lang._('Result summary') }}</h4><div class="row"><div class="col-sm-3"><strong>{{ lang._('Target') }}:</strong> <span id="strategyLabResultTarget">—</span></div><div class="col-sm-3"><strong>{{ lang._('Mode') }}:</strong> <span id="strategyLabResultMode">—</span></div><div class="col-sm-3"><strong>{{ lang._('Outcome') }}:</strong> <span id="strategyLabResultOutcome">—</span></div><div class="col-sm-3"><strong>{{ lang._('Restoration') }}:</strong> <span id="strategyLabResultRestoration">—</span></div></div></div>
<div id="strategyLabShortlistBox" style="display:none;"><h4>{{ lang._('Stable candidates') }}</h4><div class="table-responsive"><table class="table table-striped" id="strategyLabShortlist"><thead><tr><th>#</th><th>{{ lang._('Protocol') }}</th><th>{{ lang._('Port') }}</th><th>{{ lang._('Family') }}</th><th>{{ lang._('Endpoints') }}</th><th>{{ lang._('Replay') }}</th><th>{{ lang._('Complete Traffic Strategy profile') }}</th></tr></thead><tbody></tbody></table></div></div>
<div id="circularControls" class="well" style="display:none;"><h4>{{ lang._('Temporary circular validation') }}</h4><button class="btn btn-success" id="circularStartBtn" type="button">{{ lang._('Start') }}</button> <button class="btn btn-warning" id="circularStopBtn" type="button" disabled>{{ lang._('Stop') }}</button><span style="margin-left:10px;"><strong>{{ lang._('Status') }}:</strong> <span id="circularState">idle</span></span><p id="circularMessage" style="margin-top:10px;"></p><pre id="circularRaw" style="max-height:200px;overflow-y:auto;white-space:pre-wrap;font-size:11px;"></pre></div>
<details><summary>{{ lang._('Full output (advanced)') }}</summary><pre id="strategyLabRaw" style="max-height:400px;overflow-y:auto;white-space:pre-wrap;font-size:11px;"></pre></details>
</div></div></section></div></div></section>