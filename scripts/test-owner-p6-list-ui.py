#!/usr/bin/env python3
"""Fast integrated boundary regression for owner v0.6.4_42 P1/Help failure.

Static checks intentionally cannot claim real OPNsense/browser/Config acceptance.
The companion PHP fixture executes the real privileged validation method with
the canonical Python bridges, not an independent test parser.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/opnsense"
model = ET.parse(SRC / "mvc/app/models/OPNsense/Zapret/Zapret.xml").getroot()
active = [
    "youtubedomains", "userdomains", "excludedomains",
    "telegramips", "discordips", "xips", "sipips", "customips", "excludeipset",
]
for name in active:
    node = model.find("./items/hostlist/" + name)
    assert node is not None and node.attrib.get("type") == "TextField", name
    assert node.find("Mask") is None, "duplicate OPNsense list grammar: " + name
assert model.find("./items/hostlist/domains/Mask") is not None, "legacy unowned domain mask changed"
assert model.find("./items/general/ports/Mask") is not None, "ports grammar changed"
assert model.find("./items/general/divertport").attrib["type"] == "PortField"
assert model.find("./items/general/waninterface").attrib["type"] == "InterfaceField"
assert model.find("./items/hostlist/mode").attrib["type"] == "OptionField"

php = (SRC / "scripts/OPNsense/Zapret/apply_settings.php").read_text()
assert "DomainSetPolicyBridge::inspect(" in php
assert "IPSetPolicyBridge::inspect(" in php
assert "public static function validateOwnedModelFields(" in php
assert "self::validateOwnedModelFields($model, $target, $plan['changed_fields']);" in php
assert "serializeToConfig(false, true)" in php
assert "$config->save([" in php
assert "Native OPNsense model rejected" in php

pages = {
    page: (SRC / ("mvc/app/views/OPNsense/Zapret/" + page + ".volt")).read_text()
    for page in ("general", "voice", "diagnostics")
}
assert "show_all_help_frm_GeneralSettings" in pages["general"]
assert "info.closest('tr').toggle(" in pages["general"]
assert "info.addClass('zapret-context-help')" in pages["general"]
assert "show_all_help_frm_VoiceSettings" in pages["voice"]
assert ".toggle($('#show_all_help_frm_VoiceSettings').hasClass('fa-toggle-on'))" in pages["voice"]
assert "id=\"strategyLabHelpToggle\"" in pages["diagnostics"]
assert 'id="zapretLabHelpBar"' in pages["diagnostics"], "Page-level help bar absent"
assert pages["diagnostics"].index('id="zapretLabHelpBar"') < pages["diagnostics"].index('id="testDomainTable"') < pages["diagnostics"].index('id="strategyLabInputsTable"'), "Help toggle must precede BOTH Laboratory sections"
assert pages["diagnostics"].count('id="strategyLabHelpToggle"') == 1, "Duplicate Laboratory Help control"
assert 'fa fa-info-circle fa-sm fa-fw text-primary' in pages["diagnostics"], "Help info icon must use native Form classes"
assert 'fa fa-toggle-off fa-fw text-danger' in pages["diagnostics"], "Help OFF icon must use native Form classes"
assert 'fa-toggle-on text-success' in pages["diagnostics"]
assert 'content-box-header zapret-lab-header' not in pages["diagnostics"], "Help stuck in subsection header"
assert 'content-box-header zapret-lab-page-header' not in pages["diagnostics"], "Custom dark Lab header still present"
assert '<table class="table table-striped table-condensed" style="table-layout: fixed; width: 100%;">' in pages["diagnostics"], "Native table header structure missing"
assert '<td colspan="3">' in pages["diagnostics"], "Native Form header row missing"
assert '<span class="pull-right">' in pages["diagnostics"], "Help toggle not aligned using native Form markup"
assert '<small id="strategyLabHelpLabel">help</small>' in pages["diagnostics"], "Native small Help label absent"
assert 'class="zapret-lab-help-toggle"' not in pages["diagnostics"], "Custom Help button styles remain"
assert 'role="button"' in pages["diagnostics"], "Keyboard-accessible native Help action missing"
assert "aria-controls=\"strategyLabSummary\"" in pages["diagnostics"]
assert "guidance.toggle(labHelpOn)" in pages["diagnostics"]
assert "strategyLabHelpToggle" in pages["diagnostics"]
assert "id=\"strategyLabSummary\" class=\"zapret-context-help\" style=\"display:none\"" in pages["diagnostics"]
assert "Введите домен, IPv4- или IPv6-адрес" in pages["diagnostics"]
assert "Лаборатория не сохраняет стратегию автоматически" in pages["diagnostics"]
for page, marker in [("general","#frm_GeneralSettings .zapret-context-help"),
                     ("voice","#frm_VoiceSettings .zapret-context-help"),
                     ("diagnostics","#strategyLabSummary.zapret-context-help")]:
    assert marker in pages[page], "Help style absent " + page
    assert "font-size: 13px" in pages[page], "Owner-approved 13px Help absent " + page

receipt = (ROOT / "docs/verification/evidence/2026-11-12-v0.6.4_42-owner-p6-findings.md").read_text()
assert "timer" in receipt.lower() and "NOT PRESENT" in receipt
print("P6_OWNER_LIST_MODEL_UI_FAST=PASS (real owner acceptance OPEN)")
