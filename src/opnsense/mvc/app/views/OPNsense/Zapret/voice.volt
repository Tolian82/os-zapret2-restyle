{# Draft staging of the native Voice form. No Apply endpoint or runtime change until full validation/rollback is complete. #}
<script>
$(document).ready(function () {
    "use strict";
    var isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
    var ru = isRussian;
    var text = ru ? {
        navStrategy: 'Стратегии', navVoice: 'Передача голоса', navLab: 'Лаборатория',
        general: 'Основные настройки', wan: 'Интерфейс WAN для голоса',
        infoTitle: 'Как работают голосовые профили',
        infoText: 'Страница настраивает перехват исходящего UDP/STUN в общем движке Zapret2. Каждый включённый профиль требует IPSET и нативные аргументы dvtws2. Non-STUN остаётся в «Стратегиях». Включённый профиль не означает успешный голосовой звонок.',
        parameters: 'Параметры передачи голоса', destinations: 'IP-адреса назначения',
        service: 'Служба Zapret2', apply: 'Применить', start: 'Запустить', stop: 'Остановить', repositoryReleases: 'Релизы репозитория',
        notice: 'Форма v0.5.1_1 находится в разработке. Применение заблокировано до завершения валидации, единого движка, IPFW и восстановления после загрузки. Текущая служба не изменяется.',
        status: 'Статус', running: 'Запущена', stopped: 'Остановлена', error: 'Ошибка',
        loading: 'Загрузка…', incomplete: 'Неизвестно',
        wanHelp: 'Исходящий WAN для перехвата голосового UDP. Пустое значение наследует WAN страницы «Стратегии». Выбор WAN не меняет маршруты.',
        enableHelp: 'Включает отдельный STUN-профиль и адресный перехват UDP. Если галочка снята, параметры и IP-адреса сохраняются.',
        argsHelp: 'Один нативный STUN-профиль dvtws2: --filter-udp, --filter-l7=stun, --payload=stun и необязательные действия --lua-desync. Имя профиля и IPSET задаёт плагин. Не вводите --new, TCP или команды shell. Это не означает, что звонок заработает.',
        ipHelp: 'Общий с «Стратегиями» IPSET. Один IPv4-адрес или CIDR в строке. Пустой список нельзя применять при включённой службе; нет автоматической замены на любой адрес.'
    } : {
        navStrategy: 'Strategies', navVoice: 'Voice Transmission', navLab: 'Laboratory',
        general: 'General Settings', wan: 'Voice WAN Interface',
        infoTitle: 'About Voice Profiles',
        infoText: 'This page configures outgoing UDP/STUN interception in the shared Zapret2 engine. Each enabled profile requires an IPSET and native dvtws2 arguments. Non-STUN remains in Strategies. An enabled profile does not prove a working voice call.',
        parameters: 'Voice Transmission Parameters', destinations: 'Destination IP Addresses',
        service: 'Zapret2 Service', apply: 'Apply', start: 'Start', stop: 'Stop', repositoryReleases: 'Repository Releases',
        notice: 'The v0.5.1_1 form is under development. Apply is locked until validation, single-engine/IPFW handling and boot recovery are complete. Current runtime is not modified.',
        status: 'Status', running: 'Started', stopped: 'Stopped', error: 'Error',
        loading: 'Loading…', incomplete: 'Unknown',
        wanHelp: 'Outgoing WAN used for voice UDP interception. Empty selection inherits Strategies WAN. WAN selection does not change routing.',
        enableHelp: 'Enables this STUN profile and destination-scoped UDP interception. Disabling keeps parameters and addresses.',
        argsHelp: 'One native dvtws2 STUN profile: --filter-udp, --filter-l7=stun, --payload=stun and optional --lua-desync actions. The plugin supplies profile identity and IPSET. Do not enter --new, TCP options or shell commands. This is not proof of working calls.',
        ipHelp: 'Shared IPSET, available in Strategies. One IPv4 address or CIDR per line. Empty sets must not be enabled or implicitly match any destination.'
    };
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
            if (label.length) label.text(names[key] + (ru ? ' — параметры' : ' Parameters'));
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
            else if (/^zapret\.voice\.[^.]+\.args$/.test(id)) help.text(text.argsHelp);
            else if (/^zapret\.hostlist\.(telegram|discord|x|sip|custom)ips$/.test(id)) help.text(text.ipHelp);
        });
    }
    $('a[href="/ui/zapret"]').text(text.navStrategy);
    $('a[href="/ui/zapret/voice"]').text(text.navVoice);
    $('a[href="/ui/zapret/diagnostics"]').text(text.navLab);
    $('#voiceServiceTitle').text(text.service);
    $('#voiceStatusLabel').text(text.status + ':');
    $('#voiceApply').text(text.apply).prop('disabled', true);
    $('#voiceImplementationNotice').text(text.notice);
    localizeForm();
    mapDataToFormUI({'frm_VoiceSettings':'/api/zapret/settings/get'}).done(function () {
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
            </td></tr></tbody>
        </table>
    </div></div>
<section class="grid-bottom-reserve __mt">
    <div class="alert content-box" style="margin-bottom: 0;">
        <button class="btn btn-primary __mr" id="voiceApply" type="button" disabled>Apply</button>
        <span id="voiceImplementationNotice" aria-live="polite"></span>
    </div>
</section>
