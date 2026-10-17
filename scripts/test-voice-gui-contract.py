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
CONTROLLER = SRC / "controllers/OPNsense/Zapret/VoiceController.php"
VIEW = SRC / "views/OPNsense/Zapret/voice.volt"
STRATEGIES_VIEW = SRC / "views/OPNsense/Zapret/general.volt"
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
    strategies_view = STRATEGIES_VIEW.read_text(encoding="utf-8")
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
    info = next((f.findtext("text", default="") for f in form.findall("./field")
                 if f.findtext("type") == "info"), "")
    check("Use Apply to validate, save and activate" in info and
          "Save inactive draft only stores all-OFF" in info and
          "Validate checks syntax without saving" in info,
          "Voice info contradicts implemented Apply/draft/validate")
    for service in SERVICES:
        checkbox = next((f for f in form.findall("./field")
                         if f.findtext("id") == f"zapret.voice.{service}.enabled"), None)
        help_text = checkbox.findtext("help", default="") if checkbox is not None else ""
        check("Apply validates, saves and activates" in help_text and
              "Save inactive draft requires all Voice services OFF" in help_text and
              "future activation" not in help_text,
              f"{service}: checkbox help contradicts the shared Apply")
    check("Включённый STUN-профиль применяется" in view and
          "Enabled STUN profiles use the shared Apply button" in view and
          "localizedHelp = text.enableHelp" in view and
          "info.text(text.infoText)" in view,
          "RU/EN dynamic help differs from actual shared Apply")
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
    check("function indexAction()" in controller and "getForm('voice')" in controller and
          "OPNsense/Zapret/voice" in controller, "Voice UI controller/form entry missing")
    for marker in ("base_form", "frm_VoiceSettings", "/api/zapret/voice/load",
                   "voiceServiceState", "voiceServiceControl", "voiceImplementationNotice"):
        check(marker in view, f"Voice view missing {marker}")
    for marker in ("'Передача голоса'", "'Voice Transmission'", "'Основные настройки'",
                   "'General Settings'", "'Параметры передачи голоса'",
                   "'Voice Transmission Parameters'", "'Как работают голосовые профили'",
                   "'About Voice Profiles'", "'Служба Zapret2'", "'Zapret2 Service'"):
        check(marker in view, f"Missing RU/EN translation: {marker}")
    check("/api/zapret/voice/inspect" in view and
          "refreshVoiceIPFW" in view and "voiceIPFWState" in view,
          "Voice read-only IPFW diagnostics are missing from GUI")
    check("voiceRecoveryLabel" not in view and
          "/api/zapret/voice/recoveryStatus" not in view,
          "Retired PoC recovery controls must not reappear in the five-profile GUI")
    status_api = SRC / "controllers/OPNsense/Zapret/Api/VoiceController.php"
    status_php = status_api.read_text(encoding="utf-8")
    check("showVoiceProfileObservations(reply)" in view and
          "voice-profile-observation" in view and
          "common-config-mismatch" in view and
          "common-profile-unverified" in view and
          "STUN-профиль, dvtws2 и IPFW подтверждены; звонок не проверен" in view and
          "STUN profile, dvtws2 and IPFW verified; call untested" in view and
          "refreshVoiceHealthSettled().always(function ()" in view and
          "hash_equals($committedDigest, $savedDigest)" in status_php and
          "'saved_enabled' => $enabled" in status_php and
          "voiceEffectiveWan: 'WAN'" in view and
          "voiceUdpPorts: 'UDP'" in view and
          "voiceIpsetCount: 'IPSET записей'" in view and
          "voiceProfileId: 'Applied profile'" in view and
          "profile.profile_id + '@' + profile.profile_revision" in view and
          "$status['profile_id'] = $id" in status_php and
          "$status['ipset_entries'] = $count" in status_php,
          "Voice GUI must show saved ON/OFF, applied profile, physical WAN, UDP and IPSET")
    # Match actual phases emitted by the single common Apply journal.
    native_inspector = (
        ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/voice_live_inspect.py"
    ).read_text(encoding="utf-8")
    check('"shared-apply-" + phase' in native_inspector and
          "voiceIPFWDetail" in view and
          all(f"'shared-apply-{phase}'" in view for phase in (
              "prepared", "activating", "activated", "config-saved",
              "restore-failed", "requires-review"
          )) and
          "Общее применение" in view and "Shared Apply" in view and
          "common-config-mismatch" in view and
          "common-profile-unverified" in view,
          "Voice GUI must explain actual shared Apply phases in RU/EN")
    check(all(term not in view for term in (
              "prepared-needs-previous-verification",
              "interrupted-needs-kernel-runtime-review",
              "committed-needs-cleanup-review",
              "Interrupted cutover", "old Telegram PoC",
              "старый Telegram PoC", "cutoverPrepared",
          )) and "old Telegram PoC" not in info,
          "Active Voice page must not suggest retired PoC migration")
    for term in ("'Общий движок и правила подтверждены'", "'Shared engine and IPFW verified'",
                 "'Новая Voice-конфигурация не активирована'", "'New Voice configuration not activated'"):
        check(term in view, f"Missing read-only Voice diagnostic localization: {term}")
    shared_php = (SRC / "controllers/OPNsense/Zapret/Api/SettingsApply.php").read_text(encoding="utf-8")
    check("public function inspectAction()" in status_php and
          "configdRun('zapret voice_inspect'" in status_php and
          "public function applyAction()" in status_php,
          "Voice diagnostics and shared native Apply must both be available")
    configd = (ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text(encoding="utf-8")
    check("[voice_recovery_status]" not in configd and
          "public function recoveryStatusAction()" not in status_php,
          "Private old-PoC recovery API must stay retired")
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
    # The owner's screenshots show all four controls occupying the full
    # horizontal row; a following inline validation span can be pushed off
    # screen together with help text. Preserve action IDs and dedicate a
    # visible, wrapping block to the actual AJAX result and a second to help.
    check(re.search(
          r'<div\s+id="voiceValidationStatus"[^>]*role="status"[^>]*></div>',
          view) is not None and
          '<div id="voiceImplementationNotice"></div>' in view and
          '#voiceValidationStatus, #voiceImplementationNotice {' in view and
          'display: block;' in view.split(
              '#voiceValidationStatus, #voiceImplementationNotice {', 1
          )[1].split('}', 1)[0] and
          'overflow-wrap: break-word;' in view.split(
              '#voiceValidationStatus, #voiceImplementationNotice {', 1
          )[1].split('}', 1)[0],
          "Voice Validate feedback and implementation notice must be "
          "separate wrapping visible blocks, never trailing inline spans")
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
        # Parse the second real browser client of the same FD9 Apply.
        strategies_script = re.search(r"<script>(.*?)</script>",
                                      strategies_view, re.DOTALL)
        check(strategies_script is not None,
              "Strategies GUI missing browser JavaScript")
        syntax = subprocess.run(
            ["node", "--check", "-"], input=strategies_script.group(1),
            text=True, capture_output=True, check=False,
        )
        check(syntax.returncode == 0,
              "Strategies GUI JS syntax: " + syntax.stderr)
        check("strategiesApplyPending" in strategies_script.group(1) and
              "strategiesApplyNeedsReview" in strategies_script.group(1) and
              "data.requires_review === true" in strategies_script.group(1) and
              "timeout: 630000" in strategies_script.group(1) and
              "reloadSettings().done" in strategies_script.group(1),
              "Strategies browser shared Apply review gate missing")
        parsed = subprocess.run(
            ["node", "--check", "-"], input=match.group(1),
            text=True, capture_output=True, check=False,
        )
        check(parsed.returncode == 0,
              "Voice browser JavaScript syntax error: " + parsed.stderr)
        check("voiceReleaseSelect" not in view and
              "voiceReleaseApply" not in view and
              "/api/zapret/service/releases" not in view and
              "/api/zapret/service/install" not in view,
              "Voice page contains unrequested upstream release manager")
        check('div[data-for^="help_for_"] small' in view and
              "row.find('.help-block').first()" in view and
              "localizedHelp" in view and
              "Shared model candidate is not normalized" in view and
              "result[key] = 'Ошибка проверки настроек." in view,
              "Native help source and validation messages are not localized")
        # Execute the real GUI Config mutation gate: both writers must be
        # single-flight; an uncertain Apply cannot be followed by draft save.
        mutation_gate = re.search(
            r"    function reconcileVoiceMutationControls\(\) \{.*?^    \}",
            match.group(1), re.DOTALL | re.MULTILINE,
        )
        check(mutation_gate is not None, "Voice Config mutation gate missing")
        gate_script = (
            "let voiceMutationPending=false,voiceControlPending=false,"
            "voiceApplyNeedsReview=false,token='a'.repeat(64),disabled=true;\n"
            + "const voiceSnapshot={val:()=>token};\n"
            + "function $(selector) {if(selector!=='#voiceSaveDraft,#voiceApply')"
              "throw Error('wrong controls');return {prop:(name,value)=>"
              "{if(name!=='disabled')throw Error('wrong prop');disabled=value;}};}\n"
            + mutation_gate.group(0) + "\n"
            + "function check(ok,label){if(!ok)throw Error(label);}\n"
            + "reconcileVoiceMutationControls();check(!disabled,'clean form blocked');\n"
            + "voiceMutationPending=true;reconcileVoiceMutationControls();"
              "check(disabled,'parallel Apply/Save Draft permitted');\n"
            + "voiceMutationPending=false;voiceControlPending=true;"
              "reconcileVoiceMutationControls();"
              "check(disabled,'service action permitted Config write');\n"
            + "voiceControlPending=false;voiceApplyNeedsReview=true;"
              "reconcileVoiceMutationControls();"
              "check(disabled,'unknown Apply permitted draft overwrite');\n"
            + "voiceApplyNeedsReview=false;token='';"
              "reconcileVoiceMutationControls();"
              "check(disabled,'missing baseline permitted write');\n"
        )
        gate_run = subprocess.run(
            ["node", "-"], input=gate_script, text=True,
            capture_output=True, check=False,
        )
        check(gate_run.returncode == 0,
              "Voice GUI Config mutation regression: " + gate_run.stderr)
        # Drive the actual Save Draft event handler with a minimal AJAX
        # harness. A rejected validation permits correction, but an unknown
        # result, network failure or post-write error must block retries.
        save_handler = re.search(
            r"    \$\('#voiceSaveDraft'\)\.on\('click', function \(\) \{.*?^    \}\);",
            match.group(1), re.DOTALL | re.MULTILINE,
        )
        check(save_handler is not None, "Voice Save Draft handler missing")
        save_script = (
            "let click,calls,voiceMutationPending=false,voiceControlPending=false,"
              "voiceApplyNeedsReview=false;\n"
            + "const text={loading:'loading',draftSaved:'saved',"
              "draftFailed:'failed',draftReview:'review'};\n"
            + "const button={disabled:false,prop(name,value){"
              "if(name!=='disabled')throw Error('bad property');"
              "if(value===undefined)return this.disabled;"
              "this.disabled=!!value;return this;}};\n"
            + "const display={value:'',text(value){if(value===undefined)"
              "return this.value;this.value=value;return this;}};\n"
            + "const voiceSnapshot={value:'a'.repeat(64),val(value){"
              "if(value!==undefined)this.value=value;return this.value;}};\n"
            + "function $(item){if(item===button)return button;"
              "if(item==='#voiceSaveDraft')return {on:(ev,fn)=>{click=fn;}};"
              "if(item==='#voiceValidationStatus')return display;"
              "throw Error('unexpected DOM target '+item);}\n"
            + "$.ajax=()=>{calls={};return {done(fn){calls.done=fn;return this;},"
              "fail(fn){calls.fail=fn;return this;},"
              "always(fn){calls.always=fn;return this;}};};\n"
            + "function getFormData(){return {};}"
              "function handleFormValidation(){}"
              "function localizeVoiceErrors(x){return x;}\n"
            + "function reconcileVoiceServiceStatus(){"
              "button.disabled=voiceMutationPending||voiceControlPending||"
              "voiceApplyNeedsReview;}\n"
            + save_handler.group(0) + "\n"
            + "function check(ok,why){if(!ok)throw Error(why);}\n"
            + "function start(){voiceMutationPending=false;"
              "voiceApplyNeedsReview=false;button.disabled=false;"
              "click.call(button);check(voiceMutationPending&&button.disabled,"
              "'save did not lock Config');}\n"
            + "start();calls.done({result:'failed',validations:{"
              "'zapret.voice.telegram.args':'invalid'}});calls.always();"
              "check(!voiceApplyNeedsReview&&!button.disabled,"
              "'pre-write validation rejection locked the form');\n"
            + "start();calls.fail();calls.always();"
              "check(voiceApplyNeedsReview&&button.disabled&&display.value==='review',"
              "'network failure allowed blind draft retry');\n"
            + "start();calls.done({result:'failed',requires_review:true,"
              "validations:{'zapret.voice.waninterface':'save failed'}});calls.always();"
              "check(voiceApplyNeedsReview&&button.disabled,"
              "'post-write error allowed blind draft retry');\n"
            + "start();calls.done(null);calls.always();"
              "check(voiceApplyNeedsReview&&button.disabled,"
              "'malformed result permitted Config write');\n"
            + "start();calls.done({result:'saved',applied:false,"
              "snapshot:'b'.repeat(64)});calls.always();"
              "check(!voiceApplyNeedsReview&&!button.disabled&&"
              "voiceSnapshot.val()==='b'.repeat(64),"
              "'confirmed draft failed to advance snapshot');\n"
        )
        save_run = subprocess.run(
            ["node", "-"], input=save_script, text=True,
            capture_output=True, check=False,
        )
        check(save_run.returncode == 0,
              "Voice Save Draft response regression: " + save_run.stderr)
        # Exercise the actual two-witness GUI gate and asynchronous settled
        # health join instead of only looking for marker strings. This must
        # not hit a browser, OPNsense or external service.
        aligned = re.search(
            r"    function voiceRuntimeAligned\(\) \{.*?^    \}",
            match.group(1), re.DOTALL | re.MULTILINE,
        )
        settled = re.search(
            r"    function refreshVoiceHealthSettled\(\) \{.*?^    \}",
            match.group(1), re.DOTALL | re.MULTILINE,
        )
        verified = re.search(
            r"    function voiceProfilesVerified\(reply\) \{.*?^    \}",
            match.group(1), re.DOTALL | re.MULTILINE,
        )
        check(aligned is not None and settled is not None and verified is not None,
              "Voice needs native profile proof, runtime status and settled health join")
        js_test = (
            "let runtimeInstalled = true, runtimeState = 'started', "
            "voiceInspectionState = 'ready';\n"
            + aligned.group(0) + "\n"
            + verified.group(0) + "\n"
            + "function check(ok, message) { if (!ok) throw Error(message); }\n"
            + "const names = ['telegram', 'discord', 'x', 'sip', 'custom'];\n"
            + "const disabled = () => ({saved_enabled:false,runtime:'disabled',"
              "media_verified:false,call_verified:false});\n"
            + "const allOff = () => Object.fromEntries(names.map(n => [n,disabled()]));\n"
            + "const ready = {state:'ready',profiles:allOff()};\n"
            + "check(voiceProfilesVerified(ready), 'valid native five OFF rejected');\n"
            + "const on = {...ready,profiles:allOff()};\n"
            + "on.profiles.telegram = {saved_enabled:true,runtime:'active',"
              "media_verified:false,call_verified:false,profile_id:'voice-telegram',"
              "profile_revision:'123456abcdef',wan:'vtnet1',udp_ports:'3478-3481',"
              "ipset_entries:2,rule:19000,rule_packets:7,rule_bytes:280};\n"
            + "check(voiceProfilesVerified(on), 'verified ON profile rejected');\n"
            + "const stopped = structuredClone(on); stopped.state='stopped';"
              "stopped.profiles.telegram.runtime='stopped';\n"
            + "check(voiceProfilesVerified(stopped), 'stopped ON profile rejected');\n"
            + "delete stopped.profiles.telegram.rule;\n"
            + "check(voiceProfilesVerified(stopped), 'stopped profile incorrectly requires live rule');\n"
            + "const invalid = (mutate) => { const copy=structuredClone(on);"
              "mutate(copy);check(!voiceProfilesVerified(copy),"
              "'contradictory five-profile observation accepted'); };\n"
            + "invalid(x => { delete x.profiles.telegram; x.profiles.ghost=disabled(); });\n"
            + "invalid(x => { x.profiles.telegram.runtime='disabled'; });\n"
            + "invalid(x => { x.profiles.telegram.profile_id='voice-sip'; });\n"
            + "invalid(x => { x.profiles.telegram.ipset_entries=0; });\n"
            + "invalid(x => { delete x.profiles.telegram.rule; });\n"
            + "invalid(x => { x.profiles.telegram.rule=0; });\n"
            + "invalid(x => { x.profiles.telegram.rule=65535; });\n"
            + "invalid(x => { x.profiles.telegram.rule='19000'; });\n"
            + "invalid(x => { x.profiles.telegram.media_verified=true; });\n"
            + "invalid(x => { x.profiles.sip.runtime='active'; });\n"
            + "invalid(x => { x.profiles.extra=disabled(); });\n"
            + "invalid(x => { x.state='stopped'; });\n"
            + "check(!voiceProfilesVerified({state:'ready',profiles:[]}),"
              "'array profiles accepted');\n"
            + "check(voiceRuntimeAligned(), 'ready running not recognized');\n"
            + "voiceInspectionState = 'stopped';\n"
            + "check(!voiceRuntimeAligned(), 'started with stopped IPFW falsely green');\n"
            + "runtimeState = 'stopped';\n"
            + "check(voiceRuntimeAligned(), 'stopped common owner not recognized');\n"
            + "voiceInspectionState = null;\n"
            + "check(!voiceRuntimeAligned(), 'unverified IPFW falsely green');\n"
            + "voiceInspectionState = 'ready';\n"
            + "check(!voiceRuntimeAligned(), 'stopped with running IPFW falsely green');\n"
            + "runtimeInstalled = false;\n"
            + "check(!voiceRuntimeAligned(), 'uninstalled plugin falsely green');\n"
            + "let failFirst, finishSecond, completed = false;\n"
            + "function refreshRuntime() { return new Promise((resolve, reject) => "
              "{ failFirst = reject; }); }\n"
            + "function refreshVoiceIPFW() { return new Promise((resolve) => "
              "{ finishSecond = resolve; }); }\n"
            + "const $ = { when: (...promises) => Promise.all(promises) };\n"
            + settled.group(0) + "\n"
            + "(async function () {\n"
            + "  const joined = refreshVoiceHealthSettled().then("
              "() => { completed = true; });\n"
            + "  failFirst(Error('runtime status unavailable'));\n"
            + "  await new Promise(resolve => setImmediate(resolve));\n"
            + "  check(!completed, 'health unlocked before inspect settled');\n"
            + "  finishSecond(); await joined;\n"
            + "  check(completed, 'health did not settle after both responses');\n"
            + "})().catch(e => { console.error(e); process.exitCode = 1; });\n"
        )
        executed = subprocess.run(
            ["node", "-"], input=js_test, text=True,
            capture_output=True, check=False,
        )
        check(executed.returncode == 0,
              "Voice async health reconciliation failed: " + executed.stderr)
        # Execute the actual state presentation with conflicting read-only
        # witnesses (owner-live: setup_status=started, voice_inspect=uninitialized).
        # This must present the common service truth without green Voice/Start.
        presenter = re.search(
            r"    function reconcileVoiceServiceStatus\(\) \{.*?^    \}",
            match.group(1), re.DOTALL | re.MULTILINE,
        )
        check(presenter is not None, "Voice service status presenter missing")
        badge_script = (
            "let runtimeInstalled=true,runtimeState='started',"
            "runtimeBusy=false,voiceInspectionState=null,"
            "voiceMutationPending=false,voiceControlPending=false,"
            "voiceApplyNeedsReview=false;\n"
            "const text={running:'Запущена',stopped:'Остановлена',error:'Ошибка',"
            "incomplete:'Неизвестно',runningUnverified:'Запущена · Voice не подтверждён',"
            "stoppedUnverified:'Остановлена · Voice не подтверждён',"
            "start:'Запустить',stop:'Остановить'};\n"
            "const badge={classes:'',value:'',removeClass(){this.classes='';return this;},"
            "addClass(value){this.classes=value;return this;},"
            "text(value){this.value=value;return this;}};\n"
            "const control={value:'',shown:false,toggle(value){this.shown=value;return this;},"
            "text(value){this.value=value;return this;}};\n"
            "function $(key){return key==='#voiceServiceState'?badge:"
            "key==='#voiceServiceControl'?control: (()=>{throw Error(key)})();}\n"
            "function voiceRuntimeAligned(){return runtimeInstalled && ("
            "(runtimeState==='started' && voiceInspectionState==='ready') ||"
            "(runtimeState==='stopped' && voiceInspectionState==='stopped'));}\n"
            "function setServiceControlsBusy(){control.disabled=!voiceRuntimeAligned();}\n"
            "function reconcileVoiceMutationControls(){}\n"
            + presenter.group(0) + "\n"
            "function assert(ok,msg){if(!ok)throw Error(msg)};\n"
            "reconcileVoiceServiceStatus();"
            "assert(badge.value===text.runningUnverified &&"
            "badge.classes==='label-warning','uninitialized Voice hid started Zapret2');"
            "assert(control.disabled,'unverified Voice unlocked Start/Stop');\n"
            "voiceInspectionState='ready';reconcileVoiceServiceStatus();"
            "assert(badge.value===text.running&&badge.classes==='label-success',"
            "'verified owner not shown green');\n"
            "runtimeState='stopped';voiceInspectionState=null;"
            "reconcileVoiceServiceStatus();"
            "assert(badge.value===text.stoppedUnverified &&"
            "badge.classes==='label-default','stopped service misreported');\n"
            "runtimeInstalled=false;runtimeState='error';"
            "reconcileVoiceServiceStatus();"
            "assert(badge.value===text.error && badge.classes==='label-danger',"
            "'runtime error falsely healthy');\n"
        )
        badge_run = subprocess.run(
            ["node", "-"], input=badge_script, text=True,
            capture_output=True, check=False,
        )
        check(badge_run.returncode == 0,
              "Voice live service-status display regression: " + badge_run.stderr)
    else:
        print("SKIP: Node.js is unavailable; browser JavaScript syntax was not checked")
    check("if (button.prop('disabled') || voiceMutationPending ||" in view and
          view.count("voiceControlPending || voiceApplyNeedsReview) return;") == 2 and
          "voiceMutationPending = false;\n            reconcileVoiceServiceStatus();" in view and
          "reconcileVoiceMutationControls();" in view,
          "Both Voice Config writers must share pending/review exclusion")
    check("voiceRuntimeAligned()" in view and
          "!voiceProfilesVerified(reply)" in view and
          "unverified ? 'unverified-profiles' : reportedState" in view and
          "showVoiceProfileObservations(unverified ? null : reply)" in view and
          "voiceControlPending = true" in view and
          "voiceInspectionState = null" in view and
          "voiceMutationPending = true" in view and
          "refreshVoiceHealthSettled().always(function ()" in view and
          "reconcileVoiceServiceStatus()" in view,
          "Voice Start/Stop and Apply must share the two-witness gate")
    # Both read-only inspector and GUI must expose the same verified,
    # per-profile IPFW rule identity. Counters may be unavailable on FreeBSD
    # but must never be fabricated or rounded in browser JavaScript.
    check("$seenRules = []" in status_php and
          "isset($seenRules[$rule])" in status_php and
          "$status['rule'] = $rule" in status_php and
          "['rule_packets', 'rule_bytes']" in status_php and
          "$value <= 9007199254740991" in status_php and
          "voiceRule: 'Правило IPFW'" in view and
          "voiceRule: 'IPFW rule'" in view and
          "voicePackets: 'Пакеты'" in view and
          "voiceBytes: 'Bytes'" in view and
          "Number.isSafeInteger(profile.rule_packets)" in view and
          "Number.isSafeInteger(profile.rule_bytes)" in view and
          "reply.state === 'stopped'" in view and
          "Number.isInteger(profile.rule)" in view,
          "Voice GUI must display only verified native IPFW rules and safe counters")
    # The optional OFF-only draft save remains separate from the real
    # ON/OFF native Apply, with the existing GUI layout unchanged.
    check('id="voiceSaveDraft"' in view and
          "$('#voiceSaveDraft').on('click'" in view and
          "'/api/zapret/voice/saveDraft'" in view,
          "Voice UI must expose the real inactive-draft save action")
    check("public function saveDraftAction()" in status_php and
          "serializeToConfig(false, true)" in status_php and
          "'requires_review' => true, 'validations'" in status_php and
          "VoiceSettingsSnapshot::digest($model->getNodes())" in status_php,
          "Voice draft must persist using the native model and fresh snapshot")
    check("Save inactive draft requires all Voice services OFF; use Apply to change active profiles" in status_php and
          "Применение голоса пока недоступно" not in view and
          "Для изменения активных профилей используйте «Применить»" in view and
          "Native Voice ON still needs the shared IPFW cutover" not in view and
          "'applied' => false" in status_php and
          "throwReadOnly()" in status_php,
          "Voice draft cannot claim activation or bypass write privileges")
    # The approved Voice GUI stays unchanged. Its existing Apply action
    # now calls the ONE native Strategies/Voice transaction under original
    # FD9, including ON. The release installer stays on Strategies.
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
    check('id="voiceValidate"' in view and
          "'/api/zapret/voice/validate'" in view,
          "Voice validation control must remain usable")
    check('"/api/zapret/settings/apply"' not in view and
          "'/api/zapret/service/install'" not in view,
          "Voice must not accidentally reuse Strategies Apply or the installer")
    print("PASS: native Voice localization and shared Apply without release installer")

if __name__ == "__main__":
    main()
