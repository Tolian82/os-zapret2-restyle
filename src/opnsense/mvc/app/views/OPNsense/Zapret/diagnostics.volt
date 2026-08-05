{# Copyright (C) 2026 Umur Gorur. All rights reserved. #}
<script>
$(document).ready(function () {
    var activeJobId = '', pollTimer = null, circularTimer = null;
    var udpPayloadMaxBytes = 4096;
    var isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
    var strategyLabGuidance = isRussian ? [
        'Введите домен, который в настоящее время блокируется вашим интернет-провайдером, и нажмите «Запустить». Основной режим проверки ограничен 150 секундами, расширенный — 270 секундами. После завершения будут показаны стабильные стратегии, которые обеспечили доступ к сайту.',
        'Изучите результат и добавьте необходимый профиль в используемую стратегию на странице «Настройки».'
    ] : [
        'Enter a domain that is currently blocked by your ISP and click “Run.” Standard mode is limited to 150 seconds and extended mode to 270 seconds. Stable strategies that successfully provide access to the site will be reported after completion.',
        'Review the results and add the required profile to the strategy currently in use on the “Settings” page.'
    ];
    var ui = isRussian ? {
        running:'Strategy Lab выполняет проверку.', completed:'Проверка завершена.',
        cancel:'Остановка запрошена. Выполняется обязательное восстановление Zapret2.',
        failed:'Проверка завершилась с ошибкой.', noCandidates:'Стабильные кандидаты не найдены.',
        circularReady:'Можно временно проверить найденные стратегии в браузере.',
        udpPair:'Для общей UDP-проверки укажите одновременно порт и payload-файл.',
        udpSize:'Payload-файл должен иметь размер от 1 до 4096 байт.',
        udpRead:'Не удалось прочитать payload-файл.',
        requestFailed:'Ошибка запроса: '
    } : {
        running:'Strategy Lab is running.', completed:'The check is complete.',
        cancel:'Cancellation requested. Mandatory Zapret2 restoration is running.',
        failed:'The check ended with an error.', noCandidates:'No stable candidates were found.',
        circularReady:'The candidates can now be tested temporarily in a browser.',
        udpPair:'Generic UDP testing requires both a port and a payload file.',
        udpSize:'The payload file must contain between 1 and 4096 bytes.',
        udpRead:'The payload file could not be read.',
        requestFailed:'Request failed: '
    };

    var guidance = $('#strategyLabSummary').empty();
    strategyLabGuidance.forEach(function (paragraph, index) {
        $('<p/>').text(paragraph).css('margin-bottom', index === strategyLabGuidance.length - 1 ? 0 : '10px').appendTo(guidance);
    });

    function esc(value) { return $('<div/>').text(value == null ? '' : String(value)).html(); }
    function apiPost(url, data, done) {
        $.ajax({type:'POST', url:url, data:data || {}, dataType:'json', timeout:15000,
            success:function (reply) { done(reply || {}); },
            error:function (xhr, status) { done({status:'error', message:ui.requestFailed + status}); }});
    }
    function terminal(state) { return state === 'completed' || state === 'error'; }
    function setBusy(busy) {
        $('#strategyLabBtn_progress').toggleClass('fa fa-spinner fa-pulse', busy);
        $('#strategyLabBtn').prop('disabled', busy);
        $('#strategyLabCancelBtn').prop('disabled', !busy || !activeJobId);
    }
    function stopPolling() {
        if (pollTimer !== null) { clearTimeout(pollTimer); pollTimer = null; }
    }
    function toggleUdpInput() {
        $('#strategyLabUdpRow').toggle($('#strategyLabMode').val() === 'extended');
    }
    function renderStages(data) {
        var html = '';
        (Array.isArray(data.stages) ? data.stages : []).forEach(function (stage) {
            var state = stage.status || 'PENDING';
            var style = state === 'PASS' ? 'success' : (state === 'RUNNING' ? 'primary' :
                ((state === 'ERROR' || state === 'FAILED' || state === 'RESTORE_FAILED') ? 'danger' :
                ((state === 'SKIPPED' || state === 'CANCELLED') ? 'warning' : 'default')));
            html += '<tr><td>' + esc(stage.number) + '</td><td>' + esc(stage.key) + '</td>' +
                '<td><span class="label label-' + style + '">' + esc(state) + '</span></td><td>' + esc(stage.message) + '</td></tr>';
        });
        $('#strategyLabStages tbody').html(html);
    }
    function shortlist(data) {
        return data.shortlist && Array.isArray(data.shortlist.items) ? data.shortlist.items : [];
    }
    function renderShortlist(data) {
        var items = shortlist(data), html = '';
        items.forEach(function (item, index) {
            var mark = index === 0 ? ' <span class="label label-success">#1</span>' : '';
            html += '<tr><td>' + (index + 1) + mark + '</td><td>' + esc(item.family) + '</td>' +
                '<td><pre style="margin:0;white-space:pre-wrap;">' + esc(item.strategy) + '</pre></td></tr>';
        });
        $('#strategyLabShortlist tbody').html(html);
        $('#strategyLabShortlistBox').toggle(items.length > 0);
        var circularReady = data.circular_eligible === true;
        $('#circularControls').toggle(circularReady);
        if (data.state === 'completed') {
            if (circularReady) $('#strategyLabMessage').text(ui.circularReady);
            else if (!items.length) $('#strategyLabMessage').text(ui.noCandidates);
        }
    }
    function renderJob(data) {
        renderStages(data);
        renderShortlist(data);
        $('#strategyLabRaw').text(JSON.stringify(data, null, 2));
        $('#strategyLabJob').text(data.job_id || activeJobId || '—');
        $('#strategyLabState').text(data.state || data.status || '—');
        if (data.message) $('#strategyLabMessage').text(data.message);
    }
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
            renderJob(data);
            if (terminal(data.state)) { stopPolling(); fetchResult(); return; }
            setBusy(true); pollTimer = setTimeout(pollStatus, 1000);
        });
    }

    $('#testDomainBtn').click(function () {
        var domain = $('#testDomainInput').val().trim();
        if (!domain) return;
        $('#testDomainBtn_progress').addClass('fa fa-spinner fa-pulse');
        $('#testDomainResult').text('Testing...');
        ajaxCall('/api/zapret/diagnostics/testdomain', {domain:domain}, function (data) {
            $('#testDomainBtn_progress').removeClass('fa fa-spinner fa-pulse');
            $('#testDomainResult').text(data.status === 'ok' ? data.result : 'Error: ' + (data.message || 'Unknown error'));
        });
    });

    function startStrategyLab(target, mode, udpPort, udpPayloadBase64) {
        apiPost('/api/zapret/strategy_lab/start', {
            target:target,
            mode:mode,
            language:isRussian ? 'ru' : 'en',
            udp_port:udpPort,
            udp_payload_base64:udpPayloadBase64
        }, function (data) {
            if (data.status !== 'ok' || !data.job_id) {
                setBusy(false);
                $('#strategyLabMessage').text(data.message || ui.failed);
                return;
            }
            activeJobId = data.job_id;
            $('#strategyLabJob').text(activeJobId);
            pollStatus();
        });
    }

    $('#strategyLabMode').change(toggleUdpInput);
    $('#strategyLabBtn').click(function () {
        var target = $('#strategyLabDomainInput').val().trim();
        var mode = $('#strategyLabMode').val();
        if (!target) return;
        stopPolling(); activeJobId = '';
        $('#strategyLabStages tbody,#strategyLabShortlist tbody').empty();
        $('#strategyLabShortlistBox,#circularControls').hide();
        $('#strategyLabRaw').text(''); $('#strategyLabMessage').text(ui.running); setBusy(true);

        if (mode !== 'extended') {
            startStrategyLab(target, mode, '', '');
            return;
        }

        var udpPort = $('#strategyLabUdpPort').val().trim();
        var fileInput = document.getElementById('strategyLabUdpPayload');
        var payloadFile = fileInput && fileInput.files ? fileInput.files[0] : null;
        if (!udpPort && !payloadFile) {
            startStrategyLab(target, mode, '', '');
            return;
        }
        if (!udpPort || !payloadFile) {
            setBusy(false);
            $('#strategyLabMessage').text(ui.udpPair);
            return;
        }
        if (payloadFile.size < 1 || payloadFile.size > udpPayloadMaxBytes) {
            setBusy(false);
            $('#strategyLabMessage').text(ui.udpSize);
            return;
        }

        var reader = new FileReader();
        reader.onload = function (event) {
            var encoded = String((event.target && event.target.result) || '');
            var delimiter = encoded.indexOf(',');
            if (delimiter < 0 || !encoded.substring(delimiter + 1)) {
                setBusy(false);
                $('#strategyLabMessage').text(ui.udpRead);
                return;
            }
            startStrategyLab(target, mode, udpPort, encoded.substring(delimiter + 1));
        };
        reader.onerror = function () {
            setBusy(false);
            $('#strategyLabMessage').text(ui.udpRead);
        };
        reader.readAsDataURL(payloadFile);
    });
    $('#strategyLabCancelBtn').click(function () {
        if (!activeJobId) return;
        apiPost('/api/zapret/strategy_lab/cancel', {job_id:activeJobId}, function (data) {
            renderJob(data); $('#strategyLabMessage').text(ui.cancel);
        });
    });

    function pollCircular() {
        apiPost('/api/zapret/circular/status', {}, function (data) {
            $('#circularState').text(data.state || data.status || 'idle');
            $('#circularMessage').text(data.message || '');
            $('#circularRaw').text(JSON.stringify(data, null, 2));
            var live = ['queued','preparing','running','stop_requested'].indexOf(data.state) !== -1;
            $('#circularStartBtn').prop('disabled', live);
            $('#circularStopBtn').prop('disabled', !live);
            if (live) circularTimer = setTimeout(pollCircular, 1000);
        });
    }
    $('#circularStartBtn').click(function () {
        if (!activeJobId) return;
        if (circularTimer !== null) clearTimeout(circularTimer);
        apiPost('/api/zapret/circular/start', {job_id:activeJobId}, function (data) {
            $('#circularMessage').text(data.message || ''); pollCircular();
        });
    });
    $('#circularStopBtn').click(function () {
        apiPost('/api/zapret/circular/stop', {}, function (data) {
            $('#circularMessage').text(data.message || ''); pollCircular();
        });
    });

    apiPost('/api/zapret/strategy_lab/status', {job_id:'-'}, function (data) {
        if (data.job_id && !terminal(data.state)) {
            activeJobId = data.job_id; setBusy(true); renderJob(data); pollStatus();
        }
    });
    toggleUdpInput();
    pollCircular();
});
</script>

<section class="page-content-main"><div class="container-fluid">
<div class="row"><section class="col-xs-12"><div class="content-box">
<div class="content-box-header"><h3>{{ lang._('Test Domain Connectivity') }}</h3></div>
<div class="content-box-main"><div class="table-responsive"><table class="table table-striped"><tbody><tr>
<td style="width:200px;">{{ lang._('Domain') }}</td><td><input type="text" class="form-control" id="testDomainInput" placeholder="example.com"/></td>
<td style="width:150px;"><button class="btn btn-primary" id="testDomainBtn" type="button">{{ lang._('Test') }} <i id="testDomainBtn_progress"></i></button></td>
</tr></tbody></table></div><pre id="testDomainResult" style="max-height:300px;overflow-y:auto;white-space:pre-wrap;">{{ lang._('Enter a domain and click Test to check HTTPS connectivity.') }}</pre></div>
</div></section></div>

<div class="row"><section class="col-xs-12"><div class="content-box">
<div class="content-box-header"><h3>{{ lang._('Strategy Lab') }}</h3></div><div class="content-box-main">
<div class="table-responsive"><table class="table table-striped"><tbody><tr>
<td style="width:200px;">{{ lang._('Blocked Domain') }}</td><td><input type="text" class="form-control" id="strategyLabDomainInput" placeholder="rutracker.org"/></td>
<td style="width:160px;"><select class="form-control" id="strategyLabMode"><option value="standard">{{ lang._('Standard') }}</option><option value="extended">{{ lang._('Extended') }}</option></select></td>
<td style="width:190px;"><button class="btn btn-primary" id="strategyLabBtn" type="button">{{ lang._('Run') }} <i id="strategyLabBtn_progress"></i></button> <button class="btn btn-warning" id="strategyLabCancelBtn" type="button" disabled>{{ lang._('Stop') }}</button></td>
</tr><tr id="strategyLabUdpRow" style="display:none;">
<td>{{ lang._('Generic UDP (optional)') }}</td>
<td><input type="number" min="1" max="65535" class="form-control" id="strategyLabUdpPort" placeholder="53"/></td>
<td colspan="2"><input type="file" class="form-control" id="strategyLabUdpPayload"/> <small>{{ lang._('Request payload file, 1–4096 bytes. Both port and file are required.') }}</small></td>
</tr></tbody></table></div>
<div id="strategyLabSummary"></div><p><strong>Job:</strong> <code id="strategyLabJob">—</code> &nbsp; <strong>State:</strong> <span id="strategyLabState">idle</span></p><p id="strategyLabMessage"></p>
<div class="table-responsive"><table class="table table-condensed" id="strategyLabStages"><thead><tr><th>#</th><th>{{ lang._('Stage') }}</th><th>{{ lang._('Status') }}</th><th>{{ lang._('Details') }}</th></tr></thead><tbody></tbody></table></div>
<div id="strategyLabShortlistBox" style="display:none;"><h4>{{ lang._('Stable candidates') }}</h4><div class="table-responsive"><table class="table table-striped" id="strategyLabShortlist"><thead><tr><th>#</th><th>{{ lang._('Family') }}</th><th>{{ lang._('Strategy') }}</th></tr></thead><tbody></tbody></table></div></div>
<div id="circularControls" class="well" style="display:none;"><h4>{{ lang._('Temporary circular validation') }}</h4>
<button class="btn btn-success" id="circularStartBtn" type="button">{{ lang._('Start') }}</button> <button class="btn btn-warning" id="circularStopBtn" type="button" disabled>{{ lang._('Stop') }}</button>
<span style="margin-left:10px;"><strong>{{ lang._('Status') }}:</strong> <span id="circularState">idle</span></span><p id="circularMessage" style="margin-top:10px;"></p><pre id="circularRaw" style="max-height:200px;overflow-y:auto;white-space:pre-wrap;font-size:11px;"></pre></div>
<details><summary>{{ lang._('Full output (advanced)') }}</summary><pre id="strategyLabRaw" style="max-height:400px;overflow-y:auto;white-space:pre-wrap;font-size:11px;"></pre></details>
</div></div></section></div>
</div></section>
