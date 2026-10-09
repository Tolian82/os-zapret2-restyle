#!/usr/bin/env python3
"""Static contract for the staged Voice Transmission GUI; not runtime validation."""
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src/opnsense/mvc/app"
MODEL = SRC / "models/OPNsense/Zapret/Zapret.xml"
FORM = SRC / "controllers/OPNsense/Zapret/forms/voice.xml"
MENU = SRC / "models/OPNsense/Zapret/Menu/Menu.xml"
CONTROLLER = SRC / "controllers/OPNsense/Zapret/IndexController.php"
VIEW = SRC / "views/OPNsense/Zapret/voice.volt"
SERVICES = ("telegram", "discord", "x", "sip", "custom")
BAD_FIELDS = ("laninterface", "incominginterface", "processlocaludp", "restoreonboot")

def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

def main() -> None:
    model = ET.parse(MODEL).getroot()
    form = ET.parse(FORM).getroot()
    menu = ET.parse(MENU).getroot()
    controller = CONTROLLER.read_text(encoding="utf-8")
    view = VIEW.read_text(encoding="utf-8")
    fields = [f.findtext("id") for f in form.findall("./field") if f.findtext("id")]
    required = ["zapret.voice.waninterface"]
    for name in SERVICES:
        required.extend((f"zapret.voice.{name}.enabled", f"zapret.voice.{name}.args"))
    for name in SERVICES:
        required.append(f"zapret.hostlist.{name}ips")
    check(fields == required, f"Voice form field order/identities changed: {fields!r}")
    check([f.findtext("label") for f in form.findall("./field") if f.findtext("type") == "header"] ==
          ["General Settings", "Voice Transmission Parameters", "Destination IP Addresses"],
          "Voice form is missing the native section headers")
    check(any(f.findtext("type") == "info" for f in form.findall("./field")),
          "Voice inline help/info is missing")
    for name in SERVICES:
        enable = model.find(f"./items/voice/{name}/enabled")
        args = model.find(f"./items/voice/{name}/args")
        ips = model.find(f"./items/hostlist/{name}ips")
        check(enable is not None and enable.get("type") == "BooleanField" and
              enable.findtext("Default") == "0", f"{name}: enabled must default OFF")
        check(args is not None and args.get("type") == "TextField",
              f"{name}: native parameters are not a TextField")
        check(ips is not None and ips.get("type") == "TextField",
              f"{name}: missing shared hostlist IPSET")
        check(f"<IPSET:{name}>" in ET.tostring(form, encoding="unicode") or
              f"&lt;IPSET:{name}&gt;" in FORM.read_text(encoding="utf-8"),
              f"{name}: field must document the exact shared placeholder")
    check(model.find("./items/voice/waninterface") is not None, "Voice WAN must be modeled")
    check(menu.find("./Services/Zapret/General").get("order") == "0", "Strategies menu order changed")
    check(menu.find("./Services/Zapret/Voice").get("order") == "1", "Voice menu order missing")
    check(menu.find("./Services/Zapret/Diagnostics").get("order") == "2", "Laboratory menu order changed")
    check("function voiceAction()" in controller and "getForm('voice')" in controller, "Voice route missing")
    for marker in ("base_form", "frm_VoiceSettings", "/api/zapret/settings/get",
                   "voiceServiceState", "voiceReleaseSelect", "voiceServiceControl",
                   "voiceRepositoryReleasesLabel", "voiceImplementationNotice"):
        check(marker in view, f"Voice view missing {marker}")
    for marker in ("'Передача голоса'", "'Voice Transmission'", "'Основные настройки'",
                   "'General Settings'", "'Параметры передачи голоса'",
                   "'Voice Transmission Parameters'", "'Как работают голосовые профили'",
                   "'About Voice Profiles'", "'Служба Zapret2'", "'Zapret2 Service'"):
        check(marker in view, f"Missing RU/EN translation: {marker}")
    check("/api/zapret/voice/inspect" in view and
          "refreshVoiceIPFW" in view and "voiceIPFWState" in view,
          "Voice read-only IPFW diagnostics are missing from GUI")
    for term in ("'Правила подтверждены'", "'Verified rules'",
                 "'Новая Voice-конфигурация не активирована'", "'New Voice configuration not activated'"):
        check(term in view, f"Missing read-only Voice diagnostic localization: {term}")
    status_api = SRC / "controllers/OPNsense/Zapret/Api/VoiceController.php"
    status_php = status_api.read_text(encoding="utf-8")
    check("public function inspectAction()" in status_php and
          "configdRun('zapret voice_inspect'" in status_php and
          "public function applyAction()" not in status_php,
          "Voice diagnostic API must be read-only and fail-closed")
    configd = (ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text(encoding="utf-8")
    check("[voice_inspect]" in configd and
          "voice_live_inspect.py; exit 0" in configd,
          "Native Voice inspection must use a fixed read-only configd action")
    for field in fields:
        check(not any(bad in field for bad in BAD_FIELDS), f"Forbidden toggle: {field}")
    check('<IPSET:telegram>' in ET.tostring(form, encoding="unicode") or
          'zapret.hostlist.telegramips' in fields,
          "Telegram must reuse hostlist.telegramips")
    check(r"\\\\." not in view,
          "Voice JavaScript regexes must escape a dot once, not twice")
    # Parse the exact inline browser JavaScript, not just regex for UI labels.
    match = re.search(r"<script>(.*?)</script>", view, re.DOTALL)
    check(match is not None, "Voice view is missing inline JavaScript")
    if shutil.which("node"):
        parsed = subprocess.run(
            ["node", "--check", "-"], input=match.group(1),
            text=True, capture_output=True, check=False,
        )
        check(parsed.returncode == 0,
              "Voice browser JavaScript syntax error: " + parsed.stderr)
    else:
        print("SKIP: Node.js is unavailable; browser JavaScript syntax was not checked")
    # Until transactional validation and IPFW ownership are implemented, the
    # configuration Apply control must not mutate persistent or live state.
    if "Draft staging of the native Voice form" in view:
        check(re.search(r'id="voiceApply"[^>]*disabled', view) is not None,
              "An incomplete Voice implementation must keep Apply disabled")
        check('"/api/zapret/settings/apply"' not in view,
              "Draft Voice GUI must not invoke the global Settings Apply endpoint")
    print("PASS: Voice GUI model, native form, menu, RU/EN guidance, staging guard")

if __name__ == "__main__":
    main()
