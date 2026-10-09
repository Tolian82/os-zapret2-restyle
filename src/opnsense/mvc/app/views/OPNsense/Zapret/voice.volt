{# Draft staging of the native Voice form. No Apply endpoint or runtime change until full validation/rollback is complete. #}
<script>
$(document).ready(function () {
    "use strict";
    var isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
    var ru = isRussian;
    var text = ru ? {
        navStrategy: 'Стратегии', navVoice: 'Передача голоса', navLab: 'Лаборатория',
        general: 'Основные настройки', wan: 'Интерфейс WAN для голоса',
        parameters: 'Параметры передачи голоса', destinations: 'IP-адреса назначения',
        service: 'Служба Zapret2', apply: 'Применить',
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
        parameters: 'Voice Transmission Parameters', destinations: 'Destination IP Addresses',
        service: 'Zapret2 Service', apply: 'Apply',
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
        form.find('tr').each(function () {
            var row = $(this);
            var cell = row.children('th,td').first();
            var visible = $.trim(cell.text());
            var mapping = {
                'General Settings': text.general,
                'Voice WAN Interface': text.wan,
                'Voice Transmission Parameters': text.parameters,
                'Destination IP Addresses': text.destinations
            };
            if (Object.prototype.hasOwnProperty.call(mapping, visible)) {
                // Preserve the native header/help chrome where possible.
                cell.find('label').first().text(mapping[visible]);
                if (!cell.find('label').length) {
                    cell.contents().filter(function () { return this.nodeType === 3; }).each(function () {
                        this.textContent = this.textContent.replace(visible, mapping[visible]);
                    });
                }
            }
        });
        Object.keys(names).forEach(function (key) {
            var field = $('#zapret\\.voice\\.' + key + '\\.args');
            field.closest('tr').find('td').first().find('label').first().text(names[key] + (ru ? ' — параметры' : ' Parameters'));
        });
        // Form-rendered help text is controlled here so it follows OPNsense,
        // not browser/OS locale. Native tokens remain unchanged.
        form.find('tr').each(function () {
            var row = $(this);
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
    function refreshRuntime() {
        $.ajax({type:'POST',url:'/api/zapret/service/runtime',dataType:'json',timeout:30000})
            .done(function (reply) {
                var status = reply && reply.installed ? reply.service : 'error';
                var label = status === 'started' ? text.running : status === 'stopped' ? text.stopped : text.error;
                $('#voiceServiceState').removeClass('label-success label-default label-danger')
                    .addClass(status === 'started' ? 'label-success' : status === 'stopped' ? 'label-default' : 'label-danger')
                    .text(label);
                $('#voiceRuntimeVersion').text(reply && reply.version || '—');
            }).fail(function () { $('#voiceServiceState').text(text.incomplete); });
    }
    refreshRuntime();
    updateServiceControlUI('zapret');
});
</script>
<div class="content-box __mb">
    {{ partial("layout_partials/base_form",['fields':voiceForm,'id':'frm_VoiceSettings']) }}
    <div class="table-responsive">
        <table class="table table-striped table-condensed" style="table-layout: fixed; width: 100%; margin-bottom: 0;">
            <thead><tr><th>
                <div style="padding: 5px 0; font-size: 16px;">
                    <i class="fa fa-angle-down" aria-hidden="true"></i>
                    &nbsp;<b id="voiceServiceTitle">Zapret2 Service</b>
                </div>
            </th></tr></thead>
            <tbody><tr><td>
                <span id="voiceStatusLabel">Status:</span>
                <span id="voiceServiceState" class="label label-danger">—</span>
                <strong id="voiceRuntimeVersion">—</strong>
            </td></tr></tbody>
        </table>
    </div>
</div>
<section class="grid-bottom-reserve __mt">
    <div class="alert content-box" style="margin-bottom: 0;">
        <button class="btn btn-primary __mr" id="voiceApply" type="button" disabled>Apply</button>
        <span id="voiceImplementationNotice" aria-live="polite"></span>
    </div>
</section>
