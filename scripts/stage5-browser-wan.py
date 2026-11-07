#!/usr/bin/env python3
"""Disposable OPNsense Chromium WAN selection + LOWER Apply + F5 acceptance."""
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

SELECT = 'select[id="zapret.general.waninterface"],select[id="zapret_general_waninterface"]'
RESULT = Path('dist/stage5-browser-wan-result.json')

class Refusal(Exception):
    pass

def need(ok, reason):
    if not ok:
        raise Refusal(reason)

def choose(items, previous):
    for target in ('vtnet0', 'wan'):
        if any(x['value'] == target and not x['disabled'] and target != previous for x in items):
            return target
    raise Refusal('NO_DISPOSABLE_WAN_OPTION_DIFFERENT_FROM_CURRENT')

def field_options(page):
    field = page.locator(SELECT)
    need(field.count() == 1, 'NATIVE_WAN_FIELD_MISSING_OR_AMBIGUOUS')
    return field.evaluate('e=>Array.from(e.options).map(o=>({value:o.value,disabled:o.disabled}))')

def real_browser():
    from playwright.sync_api import sync_playwright
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE5_BROWSER_WAN') == '1',
         'REAL_BROWSER_DISPOSABLE_CI_OPTIN_REQUIRED')
    origin = 'https://127.0.0.1:18443'
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(origin + '/index.php', wait_until='domcontentloaded', timeout=45000)
            page.locator('input[name="usernamefld"]').fill('root')
            page.locator('input[name="passwordfld"]').fill('opnsense')
            submits = page.locator('button[type="submit"],input[type="submit"]')
            if submits.count():
                submits.first.click()
            else:
                page.locator('input[name="passwordfld"]').press('Enter')
            with page.expect_response(lambda r: '/api/zapret/settings/get' in r.url and r.status == 200, timeout=45000):
                page.goto(origin + '/ui/zapret', wait_until='domcontentloaded', timeout=45000)
            page.locator('form#frm_GeneralSettings').wait_for(timeout=45000)
            need(page.locator('#zapretReleaseApply').count() == 1 and
                 page.locator('#reconfigureAct').count() == 1,
                 'TWO_NATIVE_APPLY_BUTTONS_NOT_DISTINGUISHABLE')
            # The public bug report is for a STOPPED service. First prove
            # WAN preference persistence independently of a live lo0 -> WAN
            # engine/IPFW migration, which is a distinct lifecycle scenario.
            enabled = page.locator('input[type="checkbox"][id="zapret.general.enabled"],input[type="checkbox"][id="zapret_general_enabled"]')
            need(enabled.count() == 1, 'NATIVE_ENABLED_CHECKBOX_MISSING')
            enabled.uncheck()
            need(not enabled.is_checked(), 'DISPOSABLE_STOPPED_FORM_NOT_DISABLED')
            field = page.locator(SELECT)
            target = choose(field_options(page), field.input_value())
            field.select_option(value=target)
            need(field.input_value() == target, 'WAN_NOT_SELECTED_IN_BROWSER')
            # Original installed Volt/jQuery dispatch, not an injected request.
            with page.expect_response(lambda r: r.request.method == 'POST' and
                 r.url.split('?')[0].endswith('/api/zapret/settings/apply'), timeout=625000) as response:
                page.locator('#reconfigureAct').click()
            actual = response.value
            need(actual.status == 200, 'LOWER_APPLY_HTTP_' + str(actual.status))
            payload = actual.json()
            if not (isinstance(payload, dict) and payload.get('result') == 'saved' and
                    payload.get('status') == 'ok'):
                # Disposable guest only: emit bounded, redacted control-plane
                # diagnostics, never the candidate, XML, form data or credentials.
                message = payload.get('message', '') if isinstance(payload, dict) else ''
                message = message if isinstance(message, str) else ''
                safe_message = (message[:180] if re.fullmatch(
                    r"[A-Za-z0-9 .,:_()/'\-]{1,180}", message) else 'REDACTED_OR_EMPTY')
                validations = payload.get('validations', {}) if isinstance(payload, dict) else {}
                fields = sorted(key for key in validations if isinstance(key, str) and
                                re.fullmatch(r'[A-Za-z0-9.]{1,100}', key)) if isinstance(validations, dict) else []
                raise Refusal('LOWER_APPLY_NOT_COMMITTED:wan=' + target +
                    ':result=' + str(payload.get('result') if isinstance(payload, dict) else 'not-object') +
                    ':review=' + str(payload.get('requires_review') if isinstance(payload, dict) else '?') +
                    ':message=' + safe_message + ':validation_fields=' + ','.join(fields))
            # Real F5 and completion of the native form's GET, not a mock reload.
            with page.expect_response(lambda r: '/api/zapret/settings/get' in r.url and r.status == 200, timeout=45000):
                page.reload(wait_until='domcontentloaded', timeout=45000)
            page.wait_for_function('v=>document.querySelector("select[id=\\"zapret.general.waninterface\\"],select[id=\\"zapret_general_waninterface\\"]")?.value===v', arg=target, timeout=45000)
            need(page.locator(SELECT).input_value() == target, 'WAN_LOST_AFTER_F5')
            need(not page.locator('input[type="checkbox"][id="zapret.general.enabled"],input[type="checkbox"][id="zapret_general_enabled"]').is_checked(),
                 'STOPPED_ENABLED_FLAG_NOT_PERSISTED_AFTER_F5')
            context.close()
        finally:
            browser.close()
    return {'status': 'PASS_REAL_NATIVE_CHROMIUM_LOWER_WAN_APPLY_F5',
            'selected_wan': target, 'real_browser_click': True,
            'confirmed_saved_response': True, 'f5_persisted': True,
            'wan_dpi_bypass_tested': False,
            'stopped_disabled_wan_persistence_only': True,
            'active_wan_switch_tested': False, 'owner_appliance_modified': False}

def native_confirm():
    need(sys.platform.startswith('freebsd') and os.geteuid() == 0 and
         os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE5_BROWSER_WAN') == '1',
         'NATIVE_CONFIRM_DISPOSABLE_CI_REQUIRED')
    need(RESULT.is_file() and not RESULT.is_symlink(), 'BROWSER_RECEIPT_MISSING')
    record = json.loads(RESULT.read_text())
    need(record.get('status') == 'PASS_REAL_NATIVE_CHROMIUM_LOWER_WAN_APPLY_F5' and
         record.get('real_browser_click') is True and
         record.get('f5_persisted') is True, 'BROWSER_NOT_ATTESTED')
    wan = ET.parse('/conf/config.xml').getroot().findtext('./OPNsense/Zapret/general/waninterface')
    enabled = ET.parse('/conf/config.xml').getroot().findtext('./OPNsense/Zapret/general/enabled')
    need(wan == record['selected_wan'] and enabled == '0' and
         record.get('stopped_disabled_wan_persistence_only') is True and
         record.get('active_wan_switch_tested') is False,
         'REAL_NATIVE_STOPPED_CONFIG_AND_BROWSER_WAN_DISAGREE')
    print('PASS_STAGE5_REAL_BROWSER_STOPPED_AND_NATIVE_CONFIG_WAN=' + wan)

def self_test():
    from playwright.sync_api import sync_playwright
    assert choose([{'value':'vtnet0','disabled':False}], '') == 'vtnet0'
    try:
        choose([{'value':'foreign','disabled':False}], '')
    except Refusal:
        pass
    else:
        raise Refusal('FOREIGN_WAN_OPTION_ACCEPTED')
    with sync_playwright() as pw:
        args = {'executable_path':os.environ['STAGE5_LOCAL_CHROMIUM']} if os.environ.get('STAGE5_LOCAL_CHROMIUM') else {}
        browser = pw.chromium.launch(headless=True, **args)
        try:
            page = browser.new_page()
            page.set_content('<form id="frm_GeneralSettings"><input type="checkbox" id="zapret.general.enabled" checked><select id="zapret.general.waninterface"><option value="lo0">lo0</option><option value="vtnet0">WAN</option></select></form><span id="frm_GeneralSettings"></span><button id="reconfigureAct" onclick="window.clicked=1">Apply</button>')
            need(page.locator('#frm_GeneralSettings').count() == 2, 'DUPLICATE_NATIVE_ID_FIXTURE_INVALID')
            page.locator('form#frm_GeneralSettings').wait_for(timeout=3000)
            page.locator('input[type="checkbox"][id="zapret.general.enabled"]').uncheck()
            need(not page.locator('input[type="checkbox"][id="zapret.general.enabled"]').is_checked(),
                 'OFFLINE_STOPPED_CHECKBOX_NOT_CHANGED')
            page.locator(SELECT).select_option(choose(field_options(page),'lo0'))
            page.locator('#reconfigureAct').click()
            need(page.evaluate('window.clicked') == 1 and page.locator(SELECT).input_value() == 'vtnet0', 'OFFLINE_BROWSER_CLICK_FAILED')
        finally:
            browser.close()
    print('PASS_STAGE5_BROWSER_OFFLINE_HARNESS_ONLY')

def main():
    try:
        if sys.argv[1:] == ['--self-test']:
            self_test()
        elif sys.argv[1:] == ['--browser']:
            need(not RESULT.exists() and not RESULT.is_symlink(), 'RECEIPT_PREEXISTS')
            result = real_browser()
            RESULT.parent.mkdir(parents=True,exist_ok=True)
            RESULT.write_text(json.dumps(result,sort_keys=True)+'\n')
            print('STAGE5_NATIVE_BROWSER_WAN='+json.dumps(result,sort_keys=True))
        elif sys.argv[1:] == ['--native-confirm']:
            native_confirm()
        else:
            raise Refusal('USAGE_SELF_TEST_BROWSER_NATIVE_CONFIRM')
        return 0
    except (Refusal, OSError, ValueError, KeyError, ET.ParseError) as e:
        print('STAGE5_NATIVE_BROWSER_WAN=REFUSED:' + str(e), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
