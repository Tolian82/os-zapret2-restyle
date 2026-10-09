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
    for marker in ("base_form", "frm_VoiceSettings", "/api/zapret/voice/load",
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
    check("voiceIPFWDetail" in view and
          "prepared-needs-previous-verification" in view and
          "interrupted-needs-kernel-runtime-review" in view and
          "committed-needs-cleanup-review" in view and
          "Незавершённая подготовка" in view and
          "Interrupted cutover" in view,
          "Native Voice diagnostic needs bilingual whole-runtime crash guidance")
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
    check("function localizeVoiceErrors(errors)" in view and
          "handleFormValidation('frm_VoiceSettings', localizeVoiceErrors(" in view and
          "Некорректный IPv4/CIDR" in view and
          "Смещение UDP-фрагмента fake" in view,
          "Russian native Voice field validation guidance is missing")
    check("/api/zapret/voice/validate" in view and
          "getFormData('frm_VoiceSettings')" in view and
          'id="voiceValidate"' in view and
          'id="voiceValidationStatus"' in view,
          "Voice GUI missing syntax-only Validate control")
    for term in ("'Проверить'", "'Validate'", "'Синтаксис проверен (без применения)'",
                 "'Syntax checked (not applied)'"):
        check(term in view, f"Voice validation UI missing localization {term}")
    validator = SRC / "controllers/OPNsense/Zapret/Api/VoiceCandidateValidator.php"
    voice_validator = validator.read_text(encoding="utf-8")
    check("class VoiceCandidateValidator" in voice_validator and
          "function check(" in voice_validator and
          "Config::" not in voice_validator and "configdRun" not in voice_validator,
          "Voice candidate syntax check must not mutate active config")
    check("public function validateAction()" in status_php,
          "Voice read-only syntax validation action is unavailable")
    check("public function loadAction()" in status_php and
          "VoiceSettingsSnapshot::digest($nodes)" in status_php and
          "VoiceApplyCandidate::prepare($current, $fields, $sync['snapshot'])" in status_php and
          "VoiceApplyCandidate.php" in status_php and
          "finally {" in status_php,
          "Voice form load and validation must use one locked freshness check")
    check("voiceSnapshot.val(record.snapshot)" in view and
          "id: 'zapret.sync.snapshot'" in view and
          "record.snapshot" in view,
          "Voice GUI must retain the same model snapshot as the loaded fields")
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
