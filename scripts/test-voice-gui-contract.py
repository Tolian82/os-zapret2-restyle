#!/usr/bin/env python3
"""Static contract for the staged Voice Transmission GUI; not runtime validation."""
from pathlib import Path
import re
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
    for field in fields:
        check(not any(bad in field for bad in BAD_FIELDS), f"Forbidden toggle: {field}")
    check('<IPSET:telegram>' in ET.tostring(form, encoding="unicode") or
          'zapret.hostlist.telegramips' in fields,
          "Telegram must reuse hostlist.telegramips")
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
