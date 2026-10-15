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
    check("voiceRecoveryLabel" in view and "voiceRecoveryState" in view and
          "/api/zapret/voice/recoveryStatus" in view and
          "refreshVoiceRecovery" in view and
          "Восстановление старого Telegram PoC" in view and
          "Previous Telegram PoC recovery" in view and
          "recoveryReceipt" in view and "recoveryIncomplete" in view,
          "Old PoC read-only bilingual GUI status is not present")
    check("showVoiceProfileObservations(reply)" in view and
          "voice-profile-observation" in view and
          "common-config-mismatch" in view and
          "common-profile-unverified" in view and
          "STUN-профиль, dvtws2 и IPFW подтверждены; звонок не проверен" in view and
          "STUN profile, dvtws2 and IPFW verified; call untested" in view and
          "refreshVoiceIPFW(); updateServiceControlUI('zapret')" in view and
          "hash_equals($committedDigest, $savedDigest)" in status_php and
          "'saved_enabled' => $enabled" in status_php,
          "Voice GUI must show independent saved ON/OFF and attested five-service runtime")
    check("voiceIPFWDetail" in view and
          "prepared-needs-previous-verification" in view and
          "interrupted-needs-kernel-runtime-review" in view and
          "committed-needs-cleanup-review" in view and
          "Незавершённая подготовка" in view and
          "Interrupted cutover" in view,
          "Native Voice diagnostic needs bilingual whole-runtime crash guidance")
    for term in ("'Общий движок и правила подтверждены'", "'Shared engine and IPFW verified'",
                 "'Новая Voice-конфигурация не активирована'", "'New Voice configuration not activated'"):
        check(term in view, f"Missing read-only Voice diagnostic localization: {term}")
    status_api = SRC / "controllers/OPNsense/Zapret/Api/VoiceController.php"
    status_php = status_api.read_text(encoding="utf-8")
    shared_php = (SRC / "controllers/OPNsense/Zapret/Api/SettingsApply.php").read_text(encoding="utf-8")
    check("public function inspectAction()" in status_php and
          "configdRun('zapret voice_inspect'" in status_php and
          "public function applyAction()" in status_php,
          "Voice diagnostics and OFF-only native Apply must both be available")
    configd = (ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text(encoding="utf-8")
    check("[voice_recovery_status]" in configd and
          "zapret_service.sh native-voice-legacy-boot-review" in configd and
          "public function recoveryStatusAction()" in status_php and
          "'zapret voice_recovery_status'" in status_php,
          "Recovery status must use the original FD9 read-only configd route")
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
          "SettingsApply::prepareVoice($current, $fields, $sync['snapshot'])" in status_php and
          "SettingsApply.php" in status_php and
          "VoiceApplyCandidate::prepare($previous, $submitted, $snapshot)" in shared_php and
          "VoiceSettingsSnapshot::digest($previous)" in shared_php and
          "VoiceSettingsSnapshot::requireFresh($live, $plan['dependencies'])" in shared_php and
          "finally {" in status_php,
          "Voice load/validation must retain the locked freshness gate through shared Apply")
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
    # The optional OFF-only draft save remains separate from the real
    # ON/OFF native Apply, with the existing GUI layout unchanged.
    check('id="voiceSaveDraft"' in view and
          "$('#voiceSaveDraft').on('click'" in view and
          "'/api/zapret/voice/saveDraft'" in view,
          "Voice UI must expose the real inactive-draft save action")
    check("public function saveDraftAction()" in status_php and
          "serializeToConfig(false, true)" in status_php and
          "VoiceSettingsSnapshot::digest($model->getNodes())" in status_php,
          "Voice draft must persist using the native model and fresh snapshot")
    check("Voice activation is not available yet" in status_php and
          "'applied' => false" in status_php and
          "throwReadOnly()" in status_php,
          "Voice draft cannot claim activation or bypass write privileges")
    # The approved Voice GUI stays unchanged. Its existing Apply action
    # now calls the ONE native Strategies/Voice transaction under original
    # FD9, including ON. The separately owned release installer is untouched.
    check("ipfwStopped:" in view and
          "state === 'stopped' ? text.ipfwStopped" in view and
          "'ready', 'stopped', 'uninitialized'" in status_php,
          "Committed common Stop must show neutral stopped IPFW, not failure")
    check('id="voiceApply"' in view and
          "$('#voiceApply').on('click'" in view and
          "'/api/zapret/voice/apply'" in view,
          "Unchanged Voice Apply must remain wired to its own API")
    # The same existing button must truthfully expose ON/OFF Apply. A
    # configd timeout is not an invitation to repeat a possibly live writer.
    check("$('#voiceApply').text(text.apply)" in view and
          "voiceApplyNeedsReview = true" in view and
          "reply.requires_review === true" in view and
          "timeout: 630000" in view and
          "text.applyReview" in view and
          "Apply inactive settings" not in view and
          "Voice activation remains unavailable" not in view,
          "Voice Apply must show real ON/OFF semantics and block uncertain retries")
    check("SharedApplyEnvelope::encode('voice'" in status_php and
          "'zapret shared_apply'" in status_php and
          "configdpRun(" in status_php and
          "applied-id=" in status_php and
          "throwReadOnly()" in status_php and
          "configdRun('zapret reconfigure'" not in status_php,
          "Voice ON/OFF Apply must call one native FD9 Config/runtime transaction")
    check('id="voiceReleaseApply"' in view and
          "$('#voiceReleaseApply').on('click'" in view and
          "'/api/zapret/service/install'" in view,
          "Removing settings Apply must not delete the repository installer")
    check('id="voiceValidate"' in view and
          "'/api/zapret/voice/validate'" in view,
          "Voice validation control must remain usable")
    check('"/api/zapret/settings/apply"' not in view and
          'id="voiceReleaseApply"' in view,
          "Voice must not accidentally reuse Strategies Apply or the installer")
    print("PASS: Voice GUI unchanged; existing Voice ON/OFF Apply uses common original FD9 native transaction")

if __name__ == "__main__":
    main()
