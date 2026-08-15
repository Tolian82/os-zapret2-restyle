#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VIEW="${VIEW:-${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt}"
GENERAL="${GENERAL:-${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt}"
SETTINGS="${SETTINGS:-${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabSettingsController.php}"
MODEL="${MODEL:-${ROOT_DIR}/src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml}"
MENU="${MENU:-${ROOT_DIR}/src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml}"
fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }
EN_FIRST='Enter a domain that is currently blocked by your ISP and click “Run.” Standard mode is limited to 150 seconds and extended mode to 270 seconds. Stable strategies that successfully provide access to the site will be reported after completion.'
EN_SECOND='Review the results and add the required profile to the strategy currently in use on the “Settings” page.'
RU_FIRST='Введите домен, который в настоящее время блокируется вашим интернет-провайдером, и нажмите «Запустить». Основной режим проверки ограничен 150 секундами, расширенный — 270 секундами. После завершения будут показаны стабильные стратегии, которые обеспечили доступ к сайту.'
RU_SECOND='Изучите результат и добавьте необходимый профиль в используемую стратегию на странице «Настройки».'

require "${VIEW}" "document.documentElement.lang || ''"
require "${VIEW}" 'var strategyLabGuidance = isRussian'
require "${VIEW}" '.text(paragraph)'
require "${VIEW}" '.appendTo(guidance)'
require "${VIEW}" "${EN_FIRST}"
require "${VIEW}" "${EN_SECOND}"
require "${VIEW}" "${RU_FIRST}"
require "${VIEW}" "${RU_SECOND}"

# Owner-selected deterministic RU/EN diagnostics presentation.
require "${VIEW}" "testDomainTitle:'Тестирование соединения с доменом'"
require "${VIEW}" "testDomainHelp:'Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.'"
require "${VIEW}" "testAction:'Проверка'"
require "${VIEW}" "strategyLabTitle:'Лаборатория стратегий'"
require "${VIEW}" "blockedDomain:'Заблокированный домен / IP'"
require "${VIEW}" "genericUdpLabel:'UDP порт (опционально)'"
require "${VIEW}" "runAction:'Запуск'"
require "${VIEW}" "enableQuic:'Включить QUIC'"
require "${VIEW}" "modeLabel:'Режим'"
require "${VIEW}" "navStrategy:'Стратегия'"
require "${VIEW}" "navLaboratory:'Лаборатория'"
require "${VIEW}" "family:'Семейство'"
require "${VIEW}" "endpoints:'Назначения'"
require "${VIEW}" "outcome:'Результат'"
require "${VIEW}" "restoration:'Восстановление'"
require "${VIEW}" "replay:'Ответы'"
require "${VIEW}" "completeProfile:'Полный профиль Стратегий Трафика'"
require "${VIEW}" "fullOutput:'Полный вывод (расширенный)'"
require "${VIEW}" "stateLabel:'Состояние'"
require "${VIEW}" "testDomainTitle:'Test Domain Connectivity'"
require "${VIEW}" "testDomainHelp:'Enter a domain and click Test to check HTTPS connectivity.'"
require "${VIEW}" "strategyLabTitle:'Strategy Lab'"
require "${VIEW}" "blockedDomain:'Blocked Domain / IP'"
require "${VIEW}" "genericUdpLabel:'Generic UDP (optional)'"
require "${VIEW}" "modeLabel:'Mode'"
require "${VIEW}" "navStrategy:'Strategy'"
require "${VIEW}" "navLaboratory:'Laboratory'"
require "${VIEW}" "completeProfile:'Complete Traffic Strategy profile'"
require "${VIEW}" "fullOutput:'Full output (advanced)'"
require "${VIEW}" "stateLabel:'State'"
require "${VIEW}" "var modeLabels = isRussian ? {standard:'Стандартный', extended:'Расширенный'} : {standard:'Standard', extended:'Extended'};"
require "${VIEW}" "IDLE:'ожидание'"
require "${VIEW}" "IDLE:'idle'"
require "${VIEW}" 'applyStaticLocalization();'
require "${VIEW}" "strategyBox.find('.content-box-header h3').first().text(ui.strategyLabTitle);"
require "${VIEW}" "\$('#strategyLabUdpRow').find('td').first().text(ui.genericUdpLabel);"
require "${VIEW}" "\$('#strategyLabModeLabel').text(ui.modeLabel + ':');"
require "${VIEW}" "\$('#strategyLabMode option[value=\"standard\"]').text(modeLabels.standard);"
require "${VIEW}" "\$('#strategyLabMode option[value=\"extended\"]').text(modeLabels.extended);"
require "${VIEW}" "\$('#strategyLabState,#circularState').text(label(statusLabels,'IDLE'));"
require "${VIEW}" "\$('a[href=\"/ui/zapret\"]').text(ui.navStrategy);"
require "${VIEW}" "\$('a[href=\"/ui/zapret/diagnostics\"]').text(ui.navLaboratory);"

# Owner-live _20 showed that neutralizing .page-content-main removed the normal
# OPNsense perimeter itself. Laboratory now renders content boxes directly in
# the platform-owned page wrapper, like Strategy, rather than creating and then
# overriding a second page wrapper.
require "${VIEW}" '<div class="content-box __mb"><div class="content-box-header">'
require "${VIEW}" '<div class="content-box"><div class="content-box-header"><h3>{{ lang._('
if grep -Fq 'class="page-content-main"' "${VIEW}" || grep -Fq '.page-content-main {' "${VIEW}"; then
    fail 'Laboratory must not create or override page-content-main; OPNsense owns the page perimeter'
fi

# Both Diagnostics tables retain the accepted common native-style 25% field grid.
require "${VIEW}" 'class="table table-striped diagnostics-form-table" id="testDomainTable"'
require "${VIEW}" 'class="table table-striped diagnostics-form-table" id="strategyLabInputsTable"'
require "${VIEW}" '.diagnostics-form-table > tbody > tr > td.zapret-field-label'
require "${VIEW}" 'width:25%;'
require "${VIEW}" 'class="zapret-field-label">'
require "${VIEW}" 'class="zapret-field-value"><input type="text" class="form-control" id="testDomainInput"'
require "${VIEW}" 'class="zapret-field-value"><input type="text" class="form-control" id="strategyLabDomainInput"'
require "${VIEW}" 'class="zapret-field-value"><input type="number" min="1" max="65535" class="form-control" id="strategyLabUdpPort"'
require "${VIEW}" 'class="zapret-field-value"><input type="checkbox" id="strategyLabEnableQuic" disabled/>'
if grep -Fq 'width:250px;' "${VIEW}" || grep -Fq 'min-width:250px;' "${VIEW}"; then
    fail 'fixed 250px Laboratory label column returned; native OPNsense 25% grid is required'
fi
if grep -Fq 'font-size:12px;' "${VIEW}"; then
    fail 'blocked-domain label must use normal UI typography; 12px workaround returned'
fi

# Mode label remains right-aligned next to the selector, and its actual computed
# font size/line height are copied from the same native field-label reference.
require "${VIEW}" 'class="strategy-lab-mode-control"'
require "${VIEW}" 'id="strategyLabModeLabel">Mode:'
require "${VIEW}" 'justify-content:flex-end;'
require "${VIEW}" 'text-align:right;'
require "${VIEW}" "var modeFontReference=\$('#strategyLabInputsTable > tbody > tr > td.zapret-field-label').first();"
require "${VIEW}" "'font-size':modeFontReference.css('font-size')"
require "${VIEW}" "'line-height':modeFontReference.css('line-height')"

# Sidebar canonical names stay language-neutral in Menu.xml, while both plugin
# pages deterministically apply RU/EN labels from the active OPNsense HTML lang.
require "${MENU}" 'General VisibleName="Strategy"'
require "${MENU}" 'Diagnostics VisibleName="Laboratory"'
require "${GENERAL}" "document.documentElement.lang || ''"
require "${GENERAL}" "\$('a[href=\"/ui/zapret\"]').text(isRussian ? 'Стратегия' : 'Strategy');"
require "${GENERAL}" "\$('a[href=\"/ui/zapret/diagnostics\"]').text(isRussian ? 'Лаборатория' : 'Laboratory');"

# Ordinary circular status must be human text, not raw JSON/braces.
require "${VIEW}" "\$('#circularRaw').text(ui.stateLabel + ': ' + label(statusLabels,String(state).toUpperCase()));"
if grep -Fq "\$('#circularRaw').text(JSON.stringify(data,null,2))" "${VIEW}"; then
    fail 'ordinary circular state still exposes raw JSON'
fi

# Preserve the already implemented persisted Enable QUIC contract: default OFF,
# save on change, reload from model-backed settings endpoint.
require "${VIEW}" "apiPost('/api/zapret/strategy_lab_settings/quic', {},"
require "${VIEW}" "apiPost('/api/zapret/strategy_lab_settings/quic', {enabled:enabled?'1':'0'}"
require "${VIEW}" 'loadQuicPreference();'
require "${SETTINGS}" '$model->strategylab->enablequic = $raw;'
require "${SETTINGS}" "'enabled' => (string)\$model->strategylab->enablequic === '1'"
require "${MODEL}" '<enablequic type="BooleanField">'
require "${MODEL}" '<Default>0</Default>'

echo 'PASS: Laboratory uses the OPNsense-owned page perimeter, accepted 25% field grid and matched mode typography; Strategy/Laboratory navigation stays deterministic RU/EN on both plugin pages; persistence contracts remain guarded'
