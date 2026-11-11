#!/usr/bin/env python3
"""P3 Strategies native form RU/EN source contract, not owner GUI acceptance."""
from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[1]
form = ET.parse(root / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml").getroot()
view = (root / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
ids = [field.findtext("id") for field in form.findall("./field") if field.findtext("id")]
targets = {
    "zapret.general.enabled", "zapret.general.waninterface", "zapret.general.divertport",
    "zapret.strategy.trafficargs", "zapret.strategy.extraargs", "zapret.hostlist.mode",
    "zapret.hostlist.youtubedomains", "zapret.hostlist.telegramips",
    "zapret.hostlist.userdomains", "zapret.hostlist.excludedomains",
}
assert len(ids) == len(set(ids)) and set(ids) == targets | {"zapret.hostlist.excludeipset"}
for field in form.findall("./field"):
    if field.findtext("id") in targets:
        assert field.findtext("label") and field.findtext("help"), "English form fallback lost"
info = next(field.findtext("text", "") for field in form.findall("./field")
            if field.findtext("type") == "info")
assert info.count('id="zapretStrategiesInfoSource"') == 1
assert "blockcheck2" in info and "--new" in info
assert "function localizeStrategiesForm()" in view
assert "const info = form.find('#zapretStrategiesInfoSource');" in view
assert "if (info.length) info.html(strategiesInfoRU);" in view
assert "formatTokenizersUI();\n                localizeStrategiesForm();" in view
assert "localizeExcludeIPSet();" in view
assert "const isRussian = ((document.documentElement.lang || '')" in view
assert "row.find('div[data-for^=\"help_for_\"] small').html(help);" in view
assert "const visible = row.find('.help-block').first();" in view
assert "this.textContent = strategiesLabelsRU[id];" in view
assert "row.addClass('zapret-exclude-ipset-inline-help-only')" in view
assert "visibility: hidden !important;" in view
segment = view.split("function localizeStrategiesForm()", 1)[1].split("function localizeExcludeIPSet()", 1)[0]
assert ".val(" not in segment and ".value =" not in segment, "UI i18n must not write user data"
for name in ("strategiesLabelsRU", "strategiesHelpRU"):
    match = re.search(r"const " + name + r" = \{(.*?)\n        \};", view, re.DOTALL)
    assert match, f"RU dictionary missing: {name}"
    keys = re.findall(r"^\s*'(zapret\.[^']+)':", match.group(1), re.MULTILINE)
    assert len(keys) == 10 and set(keys) == targets, f"RU {name} map incomplete: {keys}"
if shutil.which("node"):
    scripts = re.findall(r"<script>(.*?)</script>", view, re.DOTALL)
    assert len(scripts) == 1
    checked = subprocess.run(["node", "--check"], input=scripts[0], text=True,
                             capture_output=True, check=False)
    assert checked.returncode == 0, checked.stderr
print("PASS: 10 Strategies field IDs, native help/F5, RU info, EN fallback, unchanged values")
