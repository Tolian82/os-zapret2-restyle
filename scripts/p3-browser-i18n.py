#!/usr/bin/env python3
"""P3 RU/EN Chromium smoke on a disposable, installed OPNsense 26.7.

Tests the actual server-selected root user profile locale, native Strategies
and Voice forms, popup + F5 Full Help source, unsaved editing, reload and one
read-only Voice invalid-IPSET validation. Never clicks Apply or Save Draft.
The owner appliance A12-A16 acceptance remains a separate gate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

RESULT_DIR = Path("dist")
ORIGIN = "https://127.0.0.1:18443"
SERVICES = ("telegram", "discord", "x", "sip", "custom")
FIELDS_GENERAL = (
    "zapret.general.waninterface",
    "zapret.general.divertport",
    "zapret.strategy.trafficargs",
    "zapret.strategy.extraargs",
    "zapret.hostlist.mode",
    "zapret.hostlist.youtubedomains",
    "zapret.hostlist.telegramips",
    "zapret.hostlist.userdomains",
    "zapret.hostlist.excludedomains",
    "zapret.hostlist.excludeipset",
)
FIELDS_VOICE = tuple(
    "zapret.voice." + n + ".args" for n in SERVICES
) + tuple("zapret.hostlist." + n + "ips" for n in SERVICES)


class Refusal(Exception):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refusal(reason)


def control(page, field: str):
    loc = page.locator('[id="' + field + '"]')
    need(loc.count() == 1, "NATIVE_FIELD_ID_MISSING_OR_DUPLICATED_" + field)
    return loc


def caption(page, field: str) -> str:
    loc = page.locator('[id="control_label_' + field + '"] > b')
    need(loc.count() == 1, "NATIVE_CAPTION_MISSING_" + field)
    return loc.inner_text().strip()


def help_source(page, field: str) -> str:
    loc = page.locator(
        '[id="row_' + field + '"] div[data-for="help_for_' + field + '"] small'
    )
    need(loc.count() == 1, "NATIVE_POPUP_SOURCE_MISSING_" + field)
    return loc.inner_text()


def value_snapshot(page, fields: tuple[str, ...]) -> dict[str, str]:
    # Retain values only in memory for read-only comparison; never print them.
    return {f: control(page, f).input_value() for f in fields}


def model_digest(source: dict) -> str:
    return hashlib.sha256(
        json.dumps(source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def wait_locale(page, mode: str) -> None:
    actual = page.evaluate("document.documentElement.lang || ''")
    need(actual.lower().startswith(mode), "PROFILE_HTML_LOCALE_WRONG_" + mode)


def wait_native_load(page, endpoint: str, url: str, form_id: str) -> None:
    # Only real installed GUI form/GET; no mocked route or page.set_content.
    with page.expect_response(
        lambda res: endpoint in res.url and res.status == 200,
        timeout=55000,
    ):
        page.goto(ORIGIN + url, wait_until="domcontentloaded", timeout=55000)
    page.locator("form#" + form_id).wait_for(timeout=45000)


def f5_and_wait(page, endpoint: str) -> None:
    with page.expect_response(
        lambda res: endpoint in res.url and res.status == 200,
        timeout=55000,
    ):
        page.reload(wait_until="domcontentloaded", timeout=55000)


def native_form_toggle(page, form_id: str, kind: str):
    # Genuine OPNsense toggle only: exact ID, or a single native toggle
    # within this form; never create a control or manipulate hidden styles.
    need(kind in ("show_advanced", "show_all_help"), "BAD_NATIVE_TOGGLE_KIND")
    exact = page.locator('[id="' + kind + '_' + form_id + '"]')
    if exact.count() == 1:
        return exact
    form = page.locator('form#' + form_id)
    need(form.count() == 1, "NATIVE_FORM_MISSING_" + form_id)
    alternatives = form.locator('[id^="' + kind + '_"]')
    if alternatives.count() == 1:
        return alternatives
    ids = page.locator('[id^="' + kind + '_"]').evaluate_all(
        "els => els.map(x => x.id).filter(x => /^[A-Za-z0-9_]+$/.test(x)).slice(0, 6)"
    )
    raise Refusal("NATIVE_TOGGLE_MISSING_OR_AMBIGUOUS_" + kind +
                  ":in_form=" + str(alternatives.count()) +
                  ":on_page=" + ",".join(ids))


def verify_help_cycle(page, form_id: str, field: str, token: str) -> None:
    before = control(page, field).input_value()
    source_text = help_source(page, field)
    need(token in source_text, "NATIVE_HELP_NOT_LOCALIZED_" + field)
    # OPNsense 26.7 form_input_tr.volt renders the real help inside
    # div[data-for="help_for_FIELD"]; help_block_FIELD is reserved for
    # validation errors and is never the Full Help container.
    source = page.locator(
        '[id="row_' + field + '"] div[data-for="help_for_' + field + '"]'
    )
    need(source.count() == 1, "NATIVE_HELP_SOURCE_MISSING_" + field)
    icon = page.locator('[id="help_for_' + field + '"]')
    need(icon.count() == 1, "NATIVE_HELP_ICON_MISSING_" + field)
    toggle = native_form_toggle(page, form_id, "show_all_help")
    # The global help state may have been restored from sessionStorage.
    # Normalize it through the native UI rather than manipulating DOM/CSS.
    if "fa-toggle-on" in (toggle.get_attribute("class") or ""):
        toggle.click()
    source.wait_for(state="hidden", timeout=12000)
    icon.click()
    source.wait_for(state="visible", timeout=12000)
    need(token in source.inner_text(), "NATIVE_POPUP_NOT_LOCALIZED_" + field)
    need(control(page, field).input_value() == before, "POPUP_CHANGED_VALUE_" + field)
    icon.click()
    source.wait_for(state="hidden", timeout=12000)
    toggle.click()
    source.wait_for(state="visible", timeout=12000)
    need(token in source.inner_text(), "FULL_HELP_NOT_LOCALIZED_" + field)
    need(control(page, field).input_value() == before, "FULL_HELP_CHANGED_VALUE_" + field)
    toggle.click()
    source.wait_for(state="hidden", timeout=12000)
    need(control(page, field).input_value() == before, "HIDE_HELP_CHANGED_VALUE_" + field)

def check_resource_help_cache(page, mode: str) -> str:
    """Real native Help + backend response, without mocked routing or mutation."""
    toggle = native_form_toggle(page, "frm_GeneralSettings", "show_all_help")
    if "fa-toggle-on" in (toggle.get_attribute("class") or ""):
        toggle.click()
    # The Full Help cache read may already have fired or completed; a fresh
    # expect_response event is not guaranteed. Still use the native toggle.
    toggle.click()
    panel = page.locator("#zapretExtraResourceHelp")
    # The cache list lives under a separate collapsible Service table.
    # Open it using its real GUI header, never force CSS visibility.
    service_body = page.locator("#zapretServiceBody")
    need(service_body.count() == 1, "P4B_SERVICE_BODY_MISSING")
    if not service_body.is_visible():
        page.locator("#zapretServiceHeader").click()
        service_body.wait_for(state="visible", timeout=6000)
    if not panel.is_visible():
        state = page.evaluate("""() => ({
            icon_on: document.getElementById('show_all_help_frm_GeneralSettings')
                     ?.classList.contains('fa-toggle-on') || false,
            panel_display: document.getElementById('zapretExtraResourceHelp')
                           ?.style.display || '',
            service_visible: !!document.getElementById('zapretServiceBody')
                              ?.getBoundingClientRect().height
        })""")
        raise Refusal("P4B_NATIVE_HELP_PANEL_HIDDEN:" +
                      "icon_on=" + str(state["icon_on"]) +
                      ":panel_display=" + str(state["panel_display"]) +
                      ":service_visible=" + str(state["service_visible"]))
    # Read the same production cache-only API with the browser's real
    # authenticated jQuery session. Never forge the response or mutate Config.
    data = page.evaluate("""async () => {
        try {
            return await new Promise(resolve => {
                $.ajax({
                    type: 'POST',
                    url: '/api/zapret/service/resourcesInventory',
                    dataType: 'json',
                    timeout: 10000
                }).done(resolve).fail(() => resolve({status: 'unavailable'}));
            });
        } catch (error) {
            return {status: 'unavailable'};
        }
    }""")
    need(isinstance(data, dict), "P4B_REAL_CACHE_RESPONSE_INVALID")
    if data.get("status") != "ok":
        text = "Кэш списка ресурсов недоступен" if mode == "ru" else "The resource list cache is unavailable"
        panel.locator("p").first.wait_for(state="visible", timeout=12000)
        need(text in panel.inner_text(), "P4B_UNAVAILABLE_MUST_STAY_UNKNOWN_" + mode)
        need(panel.locator("ul.zapret-resource-list li").count() == 0,
             "P4B_UNAVAILABLE_MUST_NOT_SHOW_CACHED_FILES")
        status = "unavailable"
    else:
        need(type(data.get("installed")) is bool and
             isinstance(data.get("lua"), list) and isinstance(data.get("bin"), list),
             "P4B_REAL_CACHE_SHAPE_INVALID")
        panel.locator(".zapret-resource-columns").wait_for(state="visible", timeout=12000)
        optional_note = ("Дополнительные ресурсы пока не установлены" if mode == "ru"
                         else "Additional Resources have not been installed")
        if data["installed"]:
            need(optional_note not in panel.inner_text(),
                 "P4B_INSTALLED_HAS_FALSE_ABSENCE_NOTICE")
        else:
            need(optional_note in panel.inner_text(),
                 "P4B_NATIVE_ONLY_ABSENCE_NOTICE_MISSING")
        # Each category can independently be empty. Do not mistakenly
        # demand zero empty-state rows when the other category has files.
        empty = "Нет установленных файлов" if mode == "ru" else "No installed files"
        expected = []
        for kind in ("lua", "bin"):
            if data[kind]:
                expected.extend(entry["name"] for entry in data[kind])
            else:
                expected.append(empty)
        rendered = panel.locator("ul.zapret-resource-list > li").all_inner_texts()
        need(rendered == expected, "P4B_NATIVE_RESOURCES_HIDDEN_OR_CHANGED_" + mode)
        status = "ok-optional" if data["installed"] else "ok-native-only"
    toggle.click()
    return status


def check_strategies(page, mode: str) -> tuple[dict[str, str], str]:
    wait_native_load(page, "/api/zapret/settings/get", "/ui/zapret", "frm_GeneralSettings")
    wait_locale(page, mode)
    expected = (
        ("Стратегия обработки трафика", "Режим выбора целей", "Как найти стратегию")
        if mode == "ru" else
        ("Traffic Strategy", "Target Mode", "How to find your strategy")
    )
    need(caption(page, "zapret.strategy.trafficargs") == expected[0], "STRATEGY_LABEL_WRONG_" + mode)
    need(caption(page, "zapret.hostlist.mode") == expected[1], "TARGET_MODE_LABEL_WRONG_" + mode)
    need(caption(page, "zapretStrategiesInfoSource") == expected[2], "STRATEGY_INFO_LABEL_WRONG_" + mode)
    need(page.locator('[id="zapretStrategiesInfoSource"]').count() == 1, "STRATEGY_INFO_SPAN_MISSING")
    mode_field = control(page, "zapret.hostlist.mode")
    options = mode_field.evaluate(
        "s=>Array.from(s.options).map(x=>({value:x.value,text:x.textContent.trim()}))"
    )
    need({x["value"] for x in options if x["value"]} == {"all", "list", "auto"},
         "MODE_VALUES_CHANGED")
    if mode == "ru":
        by_id = {x["value"]: x["text"] for x in options}
        need(by_id["auto"] == "Автоопределение заблокированных доменов",
             "TARGET_MODE_AUTO_TRANSLATION_MISSING")
    else:
        need(all("Автоопределение" not in x["text"] for x in options),
             "EN_TARGET_MODE_USES_RU")
    initial = value_snapshot(page, FIELDS_GENERAL)
    need("zapret.hostlist.mode" in initial, "TARGET_MODE_SNAPSHOT_MISSING")
    field = control(page, "zapret.hostlist.userdomains")
    marker = "\np3-ci-only.example.test"
    field.fill(initial["zapret.hostlist.userdomains"] + marker)
    # Extra Arguments is a native advanced form row. Open native Advanced
    # Mode only when its help icon is hidden, not by rewriting styles.
    advanced_help = page.locator('[id="help_for_zapret.strategy.extraargs"]')
    need(advanced_help.count() == 1, "STRATEGIES_ADVANCED_HELP_MISSING")
    if not advanced_help.is_visible():
        advanced = native_form_toggle(page, "frm_GeneralSettings", "show_advanced")
        advanced.click()
        advanced_help.wait_for(state="visible", timeout=12000)
    # P4: verify the newly rendered native popup/Full Help, not just source XML.
    p4_token = "входящих/исходящих счётчиков conntrack" if mode == "ru" else "incoming/outgoing conntrack counter"
    verify_help_cycle(page, "frm_GeneralSettings", "zapret.strategy.trafficargs", p4_token)
    info_token = ("Если Лаборатория подтвердила отдельный профиль" if mode == "ru"
                  else "If the Lab verified an independent profile")
    need(info_token in page.locator("#zapretStrategiesInfoSource").inner_text(),
         "P4_STRATEGIES_TRANSFER_INFO_MISSING_" + mode)
    help_token = "Не обязательно глобальные" if mode == "ru" else "Not necessarily global"
    verify_help_cycle(page, "frm_GeneralSettings", "zapret.strategy.extraargs", help_token)
    cache_state = check_resource_help_cache(page, mode)
    need(field.input_value().endswith(marker), "STRATEGY_EDIT_CHANGED_BY_HELP")
    # Restore the unsaved probe before F5, avoiding any native dirty-form
    # browser warning; still assert the persisted value after actual reload.
    field.fill(initial["zapret.hostlist.userdomains"])
    f5_and_wait(page, "/api/zapret/settings/get")
    wait_locale(page, mode)
    need(value_snapshot(page, FIELDS_GENERAL) == initial, "STRATEGIES_F5_SAVED_OR_CHANGED_VALUES")
    return initial, cache_state


def check_lab_guidance(page, mode: str) -> bool:
    # Real authenticated Laboratory page; no route interception, synthetic DOM,
    # settings POST, Run/Stop, or service/FD9/IPFW change.
    page.goto(ORIGIN + "/ui/zapret/diagnostics", wait_until="domcontentloaded", timeout=45000)
    wait_locale(page, mode)
    paragraphs = page.locator("#strategyLabSummary p")
    paragraphs.nth(3).wait_for(timeout=20000)
    need(paragraphs.count() == 4, "P4_NATIVE_LAB_GUIDANCE_PARAGRAPHS_" + mode)
    transfer = paragraphs.nth(2).inner_text()
    caveat = paragraphs.nth(3).inner_text()
    transfer_token = ("новый --new нужен только для самостоятельного профиля"
                      if mode == "ru" else
                      "use --new only for a genuinely independent profile")
    caveat_token = ("HTTP/TLS, QUIC и произвольный UDP не взаимозаменяемы"
                    if mode == "ru" else
                    "HTTP/TLS, QUIC and generic UDP are not interchangeable")
    need(transfer_token in transfer and "--in-range" in transfer and
         "--out-range" in transfer, "P4_NATIVE_LAB_TRANSFER_MISSING_" + mode)
    need(caveat_token in caveat, "P4_NATIVE_LAB_PROTOCOL_SCOPE_MISSING_" + mode)
    return True


def check_voice(page, mode: str) -> tuple[dict[str, str], bool]:
    wait_native_load(page, "/api/zapret/voice/load", "/ui/zapret/voice", "frm_VoiceSettings")
    wait_locale(page, mode)
    labels = (
        ("Telegram — параметры", "Параметры передачи голоса", "Проверить")
        if mode == "ru" else
        ("Telegram Parameters", "Voice Transmission Parameters", "Validate")
    )
    need(caption(page, "zapret.voice.telegram.args") == labels[0], "VOICE_ARGS_LABEL_WRONG_" + mode)
    section = control(page, "zapret.voice.telegram.enabled").locator(
        "xpath=ancestor::table[1]/thead/tr/th/div/b"
    )
    need(section.count() == 1 and section.inner_text().strip() == labels[1],
         "VOICE_SECTION_WRONG_" + mode)
    need(page.locator("#voiceValidate").inner_text().strip() == labels[2],
         "VOICE_VALIDATE_LABEL_WRONG_" + mode)
    need(caption(page, "zapretVoiceInfoSource") ==
         ("Как работают голосовые профили" if mode == "ru" else "About Voice Profiles"),
         "VOICE_INFO_LABEL_WRONG_" + mode)
    initial = value_snapshot(page, FIELDS_VOICE)
    for name in SERVICES:
        help_text = help_source(page, "zapret.hostlist." + name + "ips")
        need("<IPSET:" + name + ">" in help_text, "VOICE_SERVICE_SELECTOR_MISSING_" + name)
    help_token = "другие Lua-действия" if mode == "ru" else "Other Lua actions"
    verify_help_cycle(page, "frm_VoiceSettings", "zapret.voice.telegram.args", help_token)
    # Invalid IPSET is a read-only validation: no Save Draft, Apply, start,
    # stop or configd mutation request. All five service IPSETs are checked
    # even while services are disabled.
    ip_field = control(page, "zapret.hostlist.telegramips")
    ip_field.fill("999.999.999.999")
    page.wait_for_function(
        "()=>{let b=document.querySelector('#voiceValidate');return !!b && !b.disabled;}",
        timeout=45000,
    )
    with page.expect_response(
        lambda res: res.request.method == "POST" and
        res.url.split("?")[0].endswith("/api/zapret/voice/validate"),
        timeout=55000,
    ) as response:
        page.locator("#voiceValidate").click()
    reply = response.value
    need(reply.status == 200, "VOICE_VALIDATE_HTTP_STATUS")
    payload = reply.json()
    need(isinstance(payload, dict) and payload.get("result") == "failed",
         "VOICE_INVALID_IPSET_WAS_ACCEPTED")
    errors = payload.get("validations", {})
    need(isinstance(errors, dict) and "zapret.hostlist.telegramips" in errors,
         "VOICE_VALIDATION_FIELD_NOT_REPORTED")
    # Check the real visible native status and localized field rendering,
    # never trust an opaque model source-only translation assertion.
    status = page.locator("#voiceValidationStatus")
    expected_prefix = (
        "Исправьте отмеченные поля" if mode == "ru"
        else "Correct highlighted fields"
    )
    page.wait_for_function(
        "prefix=>document.querySelector('#voiceValidationStatus')?.textContent?.startsWith(prefix)",
        arg=expected_prefix, timeout=20000,
    )
    txt = status.inner_text()
    if mode == "ru":
        need("Исправьте отмеченные поля" in txt and "Invalid" not in txt,
             "RU_VOICE_ERROR_UNTRANSLATED")
    else:
        need("Correct" in txt or "Fix" in txt or "marked" in txt,
             "EN_VOICE_ERROR_NOT_DISPLAYED")
    ip_field.fill(initial["zapret.hostlist.telegramips"])
    f5_and_wait(page, "/api/zapret/voice/load")
    wait_locale(page, mode)
    need(value_snapshot(page, FIELDS_VOICE) == initial, "VOICE_F5_SAVED_OR_CHANGED_VALUES")
    return initial, True


def login(page) -> None:
    page.goto(ORIGIN + "/index.php", wait_until="domcontentloaded", timeout=45000)
    page.locator('input[name="usernamefld"]').fill("root")
    # A disposable guest's initial login only; never log this value.
    page.locator('input[name="passwordfld"]').fill("opnsense")
    submits = page.locator('button[type="submit"],input[type="submit"]')
    if submits.count():
        submits.first.click()
    else:
        page.locator('input[name="passwordfld"]').press("Enter")


def browser_run(mode: str) -> None:
    from playwright.sync_api import sync_playwright

    need(mode in ("ru", "en") and os.environ.get("GITHUB_ACTIONS") == "true"
         and os.environ.get("ZAPRET2_P3_NATIVE_LOCALE") == "1",
         "DISPOSABLE_P3_BROWSER_OPTIN_REQUIRED")
    path = RESULT_DIR / ("p3-browser-i18n-" + mode + ".json")
    need(not path.exists() and not path.is_symlink(), "P3_LOCALE_RECEIPT_PREEXISTS")
    with sync_playwright() as pw:
        browser_args = {'executable_path': os.environ['STAGE5_LOCAL_CHROMIUM']} if os.environ.get('STAGE5_LOCAL_CHROMIUM') else {}
        browser = pw.chromium.launch(headless=True, **browser_args)
        try:
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            login(page)
            strategies, cache_state = check_strategies(page, mode)
            voice, validated = check_voice(page, mode)
            lab_guidance = check_lab_guidance(page, mode)
            context.close()
        finally:
            browser.close()
    identity = model_digest({"strategies": strategies, "voice": voice})
    if mode == "ru":
        old = RESULT_DIR / "p3-browser-i18n-en.json"
        need(old.is_file() and not old.is_symlink(), "EN_PROFILE_RECEIPT_MISSING")
        prior = json.loads(old.read_text(encoding="utf-8"))
        need(prior.get("result") == "PASS_P3_INSTALLED_BROWSER_RUEN" and
             prior.get("locale") == "en" and
             prior.get("model_digest") == identity,
             "MODEL_VALUES_CHANGED_BETWEEN_EN_AND_RU_USER_PROFILES")
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "result": "PASS_P3_INSTALLED_BROWSER_RUEN",
        "locale": mode,
        "real_browser": True,
        "logged_in_user_profile": "root",
        "strategies_form_checked": True,
        "voice_form_checked": True,
        "native_popup_and_full_help_checked": True,
        "f5_values_unchanged": True,
        "readonly_voice_error_checked": validated,
        "strategy_lab_p4_guidance_checked": lab_guidance,
        "strategies_p4_native_full_help_checked": True,
        "resource_help_cache_state": cache_state,
        "resource_help_actual_backend_checked": True,
        "apply_or_save_sent": False,
        "model_digest": identity,
        "owner_appliance_touched": False,
    }
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    print("P3_INSTALLED_PROFILE_LOCALE=" + mode + " PASS (no user data or credentials printed)")


def self_test() -> None:
    a = {"voice": {"telegram": "x"}, "strategies": {"mode": "all"}}
    b = {"strategies": {"mode": "all"}, "voice": {"telegram": "x"}}
    need(model_digest(a) == model_digest(b), "DIGEST_NOT_DETERMINISTIC")
    need(model_digest(a) != model_digest({"voice": {"telegram": "other"}}),
         "DIGEST_DID_NOT_DETECT_CHANGED_VALUES")
    # The disposable guest may not have PHP's optional POSIX extension.
    # Keep a negative safety witness on Linux and a source contract that
    # never requires posix_geteuid() to exist before allowing native checks.
    guard = (Path(__file__).with_name("p3-native-profile-locale.php")
             .read_text(encoding="utf-8"))
    need("!function_exists('posix_geteuid')" not in guard and
         "function_exists('posix_geteuid')" in guard and
         "/usr/bin/id -u 2>/dev/null" in guard and
         "fileowner('/conf/config.xml')" in guard and
         "posix_getpwnam('wwwonly')" in guard and
         "/usr/bin/id -u wwwonly" in guard and
         "REFUSED_CONFIG_OWNER_UNEXPECTED" in guard and
         "is_writable('/conf/config.xml')" in guard and
         "stage5-browser-wan-ci.pub" in guard and
         "REFUSED_GUEST_WITNESS_INVALID" in guard,
         "P3_GUEST_GUARD_IS_NOT_EXTENSION_OPTIONAL_AND_CI_BOUND")
    if sys.platform.startswith("linux") and shutil.which("php"):
        proof = subprocess.run(
            ["php", str(Path(__file__).with_name("p3-native-profile-locale.php")),
             "en_US"],
            env={**os.environ, "GITHUB_ACTIONS": "true",
                 "ZAPRET2_P3_NATIVE_LOCALE": "1"},
            text=True, capture_output=True, check=False, timeout=15,
        )
        need(proof.returncode == 2 and
             "P3_PROFILE_LOCALE=REFUSED_NOT_FREEBSD" in proof.stderr and
             not proof.stdout,
             "P3_PHP_GUEST_GUARD_ACCEPTED_NON_BSD_RUNNER")
    print("P3_BROWSER_LOCALE_SELF_TEST=PASS_ONLY_OFFLINE")


def main() -> int:
    try:
        args = sys.argv[1:]
        if args == ["--self-test"]:
            self_test()
        elif args in (["--en-browser"], ["--ru-browser"]):
            browser_run(args[0][2:4])
        else:
            raise Refusal("P3_BROWSER_LOCALE_BAD_MODE")
        return 0
    except (Refusal, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print("P3_BROWSER_LOCALE=REFUSED:" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
