#!/usr/bin/env python3
"""P3 Strategies native form RU/EN source contract, not owner GUI acceptance."""
from __future__ import annotations

import re
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[1]
form = ET.parse(root / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml").getroot()
view = (root / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
ids = [field.findtext("id") for field in form.findall("./field")
       if field.findtext("id") and field.findtext("type") != "info"]
targets = {
    "zapret.general.enabled", "zapret.general.waninterface", "zapret.general.divertport",
    "zapret.general.autorestart",
    "zapret.strategy.trafficargs", "zapret.strategy.extraargs", "zapret.hostlist.mode",
    "zapret.hostlist.youtubedomains", "zapret.hostlist.telegramips",
    "zapret.hostlist.userdomains", "zapret.hostlist.excludedomains",
}
assert len(ids) == len(set(ids)) and set(ids) == targets | {"zapret.hostlist.excludeipset"}
for field in form.findall("./field"):
    if field.findtext("id") in targets:
        assert field.findtext("label") and field.findtext("help"), "English form fallback lost"
info_field = next(field for field in form.findall("./field")
                  if field.findtext("type") == "info")
info = info_field.findtext("text", "")
assert info_field.findtext("id") == "zapretStrategiesInfoSource"
assert '<span id="zapretStrategiesInfoSource">' not in info
assert "blockcheck2" in info and "--new" in info
assert "function localizeStrategiesForm()" in view
assert "const info = form.find('#zapretStrategiesInfoSource');" in view
assert "const strategiesInfoEN =" in view
assert "if (info.length) info.html(isRussian ? strategiesInfoRU : strategiesInfoEN);" in view
assert "form.find('#control_label_zapretStrategiesInfoSource > b').text('Как найти стратегию')" in view
for field_id, translated in (
    ("zapret.general.enabled", "Общие настройки"),
    ("zapret.strategy.trafficargs", "Стратегия обхода DPI"),
    ("zapret.hostlist.mode", "Цели"),
):
    assert f"['{field_id}', '{translated}']" in view
assert "closest('table').children('thead').find('th b').first().text(entry[1]);" in view
assert "formatTokenizersUI();\n                localizeStrategiesForm();" in view
assert "localizeExcludeIPSet();" in view
assert "const isRussian = ((document.documentElement.lang || '')" in view
assert "row.find('[data-for=\"help_for_' + id + '\"] small').html(help);" in view
assert "const visible = document.getElementById('help_block_' + id);" in view
assert "const nativeLabel = document.getElementById('control_label_' + id);" in view
assert "$(nativeLabel).children('b').first().text(strategiesLabelsRU[id]);" in view
assert "row.find('div.control-label > b').first().text(strategiesLabelsRU[id]);" not in view
assert "$(input).attr('aria-label', strategiesLabelsRU[id]);" in view
assert "row.find('div.control-label > b').first().text('Исключить IPSet');" in view
assert "row.find('label')" not in view, "OPNsense 26.7 has no HTML label for form captions"
assert "row.addClass('zapret-exclude-ipset-inline-help-only')" in view
assert "showRuntimeError(runtimeText.applyError, runtimeText.strategiesReview);" in view
assert "apply: isRussian ? 'Установить версию' : 'Install Version'" in view
assert "#frm_GeneralSettings tr.zapret-exclude-ipset-inline-help-only > td:nth-child(3) > .help-block {" in view
assert "visibility: hidden !important;" not in view
segment = view.split("function localizeStrategiesForm()", 1)[1].split("function localizeExcludeIPSet()", 1)[0]
assert ".val(" not in segment and ".value =" not in segment, "UI i18n must not write user data"
for name in ("strategiesLabelsRU", "strategiesHelpRU"):
    match = re.search(r"const " + name + r" = \{(.*?)\n        \};", view, re.DOTALL)
    assert match, f"RU dictionary missing: {name}"
    keys = re.findall(r"^\s*'(zapret\.[^']+)':", match.group(1), re.MULTILINE)
    assert len(keys) == 11 and set(keys) == targets, f"RU {name} map incomplete: {keys}"
# The production model owns these immutable option keys; translating UI text
# must not change the selected value, submission or English fallback.
model = ET.parse(root / "src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml").getroot()
mode = model.find("./items/hostlist/mode/OptionValues")
assert mode is not None and {item.tag for item in mode} == {"all", "list", "auto"}
assert "const targetModeLabelsRU = {" in view
assert "function localizeTargetModeOptions()" in view
for key in ("all", "list", "auto"):
    assert re.search(r"^\s*" + key + r": '[^']+',?$", view, re.MULTILINE)
assert "document.getElementById('zapret.hostlist.mode')" in view
assert "option.textContent = targetModeLabelsRU[option.value];" in view
assert "option.value =" not in view
assert "function localizeAutoRestartOptions()" in view
assert ("localizeTargetModeOptions();\n                "
        "localizeAutoRestartOptions();\n                "
        "$('.selectpicker').selectpicker('refresh');") in view
controller = (root / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php").read_text()
assert "'reason' => 'native-preflight-' . $match[1]" in controller
assert "'reason' => 'strategies-preflight-' . $preflightStage" in controller
assert "preg_match('/^preflight-rejected=(root-gate|" in controller
assert "reason.indexOf('native-preflight-') === 0" in view
assert "reason.indexOf('strategies-preflight-') === 0" in view

# P3: Full Help must describe native semantics in BOTH languages.
# These are existing source help/popup records keyed by immutable model IDs,
# not a new strategy DSL or alternative runtime parser.
help_fields = {field.findtext("id"): field.findtext("help", "")
               for field in form.findall("./field") if field.findtext("id")}
required_help = {
    "zapret.strategy.trafficargs": (
        "--new", "--payload", "--lua-desync", "--filter-tcp",
        "--filter-udp", "--filter-l7", "IPFW", "HOSTLIST:user",
        "IPSET:telegram", "dry-run",
    ),
    "zapret.strategy.extraargs": (
        "Not necessarily global", "last profile", "dvtws2",
    ),
    "zapret.hostlist.mode": (
        "HOSTLIST:name", "IPSET:name", "IPFW", "Exclude Domains",
    ),
    "zapret.hostlist.youtubedomains": (
        "^example.com", "!example.com", "!^example.com", "wildcard",
        "line number", "global Exclude Domains",
    ),
    "zapret.hostlist.userdomains": (
        "^example.com", "!example.com", "!^example.com", "wildcard",
        "line number", "global exclusions",
    ),
    "zapret.hostlist.excludedomains": (
        "Globally exclude", "!example.com", "modifiers",
        "line",
    ),
}
for field_id, required in required_help.items():
    text = help_fields[field_id]
    for phrase in required:
        assert phrase in text, (field_id, "missing EN Full Help:", phrase)
# P4: native in-profile counter/payload filters and safe handler transfer
# must appear in the actual EN XML help and bilingual rendered form help.
for term in ("--in-range", "--out-range", "conntrack", "subsequent",
             "another independent profile", "Compare port, L7, target"):
    assert term in help_fields["zapret.strategy.trafficargs"], ("P4 EN help", term)
for term in ("--in-range", "--out-range", "входящих/исходящих",
             "следующие", "независимый профиль", "порядок профилей"):
    assert term in view, ("P4 RU help", term)
for term in ("If the Lab verified an independent profile",
             "Если Лаборатория подтвердила отдельный профиль"):
    assert term in view, ("P4 bilingual transfer guidance", term)
assert "cache-only" in view or "The resource list cache is unavailable" in view

# P4c1: keep upstream L7/payload documentation symmetric in EN/RU.
for item in ("http_req", "tls_client_hello", "quic_initial",
             "wireguard_initiation", "TCP/80", "TCP/443", "UDP/443"):
    assert item in help_fields["zapret.strategy.trafficargs"], ("P4c EN", item)
    assert item in view, ("P4c RU", item)
assert "not runnable strategies" in help_fields["zapret.strategy.trafficargs"]
assert "не готовые стратегии" in view

assert "Additional global dvtws2 arguments" not in view
assert "Additional global dvtws2 arguments" not in help_fields["zapret.strategy.extraargs"]
# The runtime RU help dictionary covers all 11 actual native fields;
# check that the six enhanced explanations are present there as well.
help_ru = re.search(
    r"const strategiesHelpRU = \{(.*?)\n        \};", view, re.DOTALL
)
assert help_ru
for phrase in (
    "первый подходящий профиль", "синтаксис, а не успех обхода",
    "Не обязательно глобальные", "последнему профилю",
    "фильтр портов перехвата IPFW", "!^example.com",
    "Локальное", "запрещены", "конфликтующие правила",
):
    assert phrase in help_ru.group(1), "RU help coverage: " + phrase
assert "row.find('[data-for=\"help_for_' + id + '\"] small').html(help);" in view
assert "const visible = document.getElementById('help_block_' + id);" in view
# Neither help path may ever write model, inputs, Config or process state.
help_segment = view.split("const strategiesHelpRU = {", 1)[1].split(
    "function localizeExcludeIPSet()", 1
)[0]
assert ".val(" not in help_segment and ".value =" not in help_segment

if shutil.which("node"):
    scripts = re.findall(r"<script>(.*?)</script>", view, re.DOTALL)
    assert len(scripts) == 1
    checked = subprocess.run(["node", "--check"], input=scripts[0], text=True,
                             capture_output=True, check=False)
    assert checked.returncode == 0, checked.stderr
    # Evaluate the real browser helper, not a copy: fixed stage codes have
    # localized RU/EN messages, while unknown codes never leak to RU users.
    helper = re.search(
        r"        function localizeStrategiesApplyError\(message, reason\) \{.*?^        \}",
        view, re.MULTILINE | re.DOTALL,
    )
    assert helper is not None
    run = subprocess.run(
        ["node", "-"],
        input=(
            "let isRussian=true;\n" + helper.group(0) + "\n"
            "function eq(a,b){if(a!==b)throw Error(a+' != '+b);}\n"
            "eq(localizeStrategiesApplyError('unused','runtime-not-installed'),"
            "'Требуется установка службы zapret2');\n"
            "eq(localizeStrategiesApplyError('ignored','native-preflight-candidate-xml'),"
            "'Нативная проверка не пройдена (этап: candidate-xml). Изменения не применены.');\n"
            "eq(localizeStrategiesApplyError('ignored','strategies-preflight-normalization'),"
            "'Предварительная проверка настроек не пройдена (этап: normalization). Изменения не применены.');\n"
            "eq(localizeStrategiesApplyError('PRIVATE','native-preflight-unknown'),"
            "'Предварительная проверка настроек не пройдена. Изменения не применены.');\n"
            "isRussian=false;\n"
            "eq(localizeStrategiesApplyError('ignored','native-preflight-candidate-xml'),"
            "'Native Strategies preflight rejected before Apply (candidate-xml)');\n"
            "eq(localizeStrategiesApplyError('ignored','strategies-preflight-normalization'),"
            "'Strategies preflight failed before native Apply (normalization)');\n"
        ),
        text=True, capture_output=True, check=False,
    )
    assert run.returncode == 0, run.stderr
# TZ6v2: five registered editor sources, old Model fields stay native,
# no standalone Auto Hostlist Save/Reload and no premature lossy Apply.
for marker in (
    "function mountFoundHostlists()",
    "function loadFiveHostlists()",
    "function foundHostlistDirty()",
    "function fiveHostlistIntent()",
    "'youtube_found', source: 'youtube', id: 'zapretYoutubeFound'",
    "'user_found', source: 'user', id: 'zapretUserFound'",
    "'shared_found', source: 'auto', id: 'zapretSharedFound'",
    "/api/zapret/settings/hostlistEditorsRead",
    "reloadSettings().done(loadFiveHostlists)",
    "multipart.append('found_intent', new Blob([JSON.stringify(intent)]",
    "processData: !intent",
    "const exact = ['youtube_manual', 'youtube_found', 'user_manual',",
    "data.commit_authorized === false",
    "data.config_revision",
    "fiveHostlistBase = data;",
    "foundHostlistDirty()",
    "toggle.attr('aria-expanded', String(!shown));",
):
    assert marker in view, ("TZ6v2 five-UI integration missing", marker)
for obsolete in (
    "blockUncommittedFoundEdits", "mountAutoHostlistEditor",
    "zapretAutoHostlistSave",
    "zapretAutoHostlistReload",
    "/api/zapret/settings/autoHostlistSave",
    "/api/zapret/settings/autoHostlistRead",
    "Saving does not Apply or restart the service",
):
    assert obsolete not in view, ("TZ6v2 legacy independent GUI save", obsolete)
assert "name: 'zapretSharedFound'" not in view
assert "commit_authorized=true" not in view
assert "One original-FD9 Apply" in view

if shutil.which("node"):
    form_code = view[view.index("        const foundHostlistFields"):
                     view.index("        function fiveHostlistStatus")]
    helpers = view[view.index("        function strategiesFormData()"):
                   view.index("        // Localize ONLY known validation")]
    click = view[view.index('        $("#reconfigureAct").off'):
                 view.index("        updateServiceControlUI('zapret');\n    });")]
    click = re.sub(r"\{\{[^{}]*\}\}", "fixture", click)
    fixture = r"""
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const values = {
    zapretYoutubeFound: "fresh.example.org\n", zapretUserFound: "",
    zapretSharedFound: "", "zapret.hostlist.youtubedomains": "manual.example.com",
    "zapret.hostlist.userdomains": "", "zapret.hostlist.excludedomains": ""
};
const document = {getElementById: id => ({value: values[id]})};
let handler, request;
const $ = selector => ({
    val: () => typeof selector === 'string' ? values[selector.slice(1)] : selector.value,
    off: () => ({on: (_, fn) => {handler = fn;}})
});
$.param = object => {
    assert.deepEqual(Object.keys(object), ['zapret']);
    return 'zapret%5Bsync%5D%5Btelegramips_baseline%5D=';
};
$.ajax = data => {
    assert.equal(request, undefined);
    request = data;
    const chain = {done: () => chain, fail: () => chain};
    return chain;
};
const getFormData = () => ({
    zapret: {sync: {telegramips_baseline: ''}},
    zapretYoutubeFound: values.zapretYoutubeFound,
    zapretUserFound: values.zapretUserFound, zapretSharedFound: values.zapretSharedFound
});
const isRussian = false, reconcileStrategiesApplyControls = () => {};
let strategiesApplyPending = false, strategiesApplyNeedsReview = false, previewPending = false,
    extraBusy = false, extraInstallPending = false, extraNeedsReview = false,
    runtimeWasBusy = false, releaseApplyPending = false;
"""
    invoke = r"""
const revision = createHash('sha256').update(Buffer.from('present\0')).digest('hex');
const empty = {status: 'empty', revision, content: ''};
fiveHostlistBase = {config_revision: 'd'.repeat(64), editors: {
    youtube_manual: {content: values['zapret.hostlist.youtubedomains']},
    user_manual: {content: ''}, youtube_found: empty, user_found: empty, shared_found: empty
}};
fiveHostlistReady = true;
handler({preventDefault() {}});
assert.equal(request.url, '/api/zapret/settings/apply');
assert.equal(request.type, 'POST');
assert.equal(request.processData, false);
assert.equal(request.contentType, false);
assert.equal(request.data.get('zapret[sync][telegramips_baseline]'), '');
const upload = request.data.get('found_intent');
assert.equal(upload.name, 'found-intent.json');
upload.text().then(value => {
    const payload = JSON.parse(value);
    assert.equal(payload.sources.youtube.draft, values.zapretYoutubeFound);
    assert.equal(payload.sources.youtube.base.revision, revision);
    console.log(value);
});
"""
    sent = subprocess.run(["node", "-"], input=fixture + form_code + helpers + click + invoke,
                          text=True, capture_output=True, check=False)
    assert sent.returncode == 0, sent.stderr
    parsed = json.loads(sent.stdout)
    assert list(parsed["sources"]) == ["youtube", "user", "auto"]
    if shutil.which("php"):
        native = root / "src/opnsense/scripts/OPNsense/Zapret/shared_apply_found_intent.php"
        decoded = subprocess.run(
            ["php", "-r", r'''
require $argv[1];
$data = OPNsense\Zapret\Native\SharedApplyFoundIntent::validateJson(
    stream_get_contents(STDIN), str_repeat('d', 64));
echo json_encode($data['sources']);
''', str(native)], input=sent.stdout, text=True, capture_output=True, check=False)
        assert decoded.returncode == 0, decoded.stderr + decoded.stdout
        assert json.loads(decoded.stdout) == parsed["sources"]

print("PASS: 11 Strategies field IDs, native help/F5, RU info, EN fallback, unchanged values")
