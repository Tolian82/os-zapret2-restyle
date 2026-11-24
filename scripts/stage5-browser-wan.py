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

def native_wan_start_error_browser(mode):
    """Genuine installed controller WAN UserException; only READ-ONLY display endpoints mocked.

    Requires native guest witness --prepare with wan-required before this run;
    guest --verify later compares Config/IPFW/engine. No HTTP Start interception.
    """
    from playwright.sync_api import sync_playwright
    need(mode in ('en', 'ru') and os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE5_BROWSER_WAN') == '1',
         'S03E3_DISPOSABLE_BROWSER_OPTIN_REQUIRED')
    origin = 'https://127.0.0.1:18443'
    with sync_playwright() as pw:
        options = {'executable_path': os.environ['STAGE5_LOCAL_CHROMIUM']} if os.environ.get('STAGE5_LOCAL_CHROMIUM') else {}
        browser = pw.chromium.launch(headless=True, **options)
        try:
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            calls = []
            def runtime_display(route):
                route.fulfill(status=200, content_type='application/json',
                              body=json.dumps({'status':'ok','installed':True,'busy':False,
                                               'version':'v1.0.7','setup':'ready','service':'stopped'}))
            def resources_display(route):
                route.fulfill(status=200, content_type='application/json',
                              body=json.dumps({'status':'ok','installed':False,
                                               'busy':False,'phase':'not_installed'}))
            # No route for Start/Stop/Restart: mutation reaches actual PHP.
            page.route('**/api/zapret/service/runtime', runtime_display)
            page.route('**/api/zapret/service/resourcesStatus', resources_display)
            page.on('request', lambda req: calls.append(req.method + ':' + req.url.split('?')[0].rsplit('/',1)[-1])
                    if '/api/zapret/service/' in req.url and req.method == 'POST' else None)
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
            need(page.evaluate("document.documentElement.lang || ''").lower().startswith(mode),
                 'S03E3_REAL_PROFILE_LOCALE_WRONG_' + mode)
            page.wait_for_function(
                "() => {let b=document.querySelector('#zapretServiceControl');"
                "return !!b && !b.disabled && b.offsetWidth>0 && b.textContent.trim().length>0;}",
                timeout=20000)
            with page.expect_response(lambda r: r.request.method == 'POST' and
                    r.url.split('?')[0].endswith('/api/zapret/service/start'), timeout=30000) as result:
                page.locator('#zapretServiceControl').click(timeout=20000)
            response = result.value
            need(response.status >= 400, 'S03E3_NATIVE_START_NOT_REJECTED')
            body = response.json()
            message = body.get('errorMessage') if isinstance(body, dict) else None
            native_title = body.get('errorTitle') if isinstance(body, dict) else None
            need(isinstance(native_title, str) and len(native_title) > 0,
                 'S03E3_ACTUAL_NATIVE_USEREXCEPTION_TITLE_MISSING')
            need(message in ('Select a WAN interface','Укажите WAN интерфейс',
                             'Укажите WAN-интерфейс.'),
                 'S03E3_ACTUAL_NATIVE_WAN_USEREXCEPTION_NOT_RETURNED_KEYS_' +
                 (','.join(sorted(body))[:120] if isinstance(body, dict) else 'NOT_JSON_OBJECT'))
            expected = 'Укажите WAN интерфейс' if mode == 'ru' else 'Select a WAN interface'
            page.get_by_text(expected, exact=False).first.wait_for(state='visible', timeout=15000)
            title = 'Ошибка управления службой' if mode == 'ru' else 'Service operation failed'
            page.get_by_text(title, exact=False).first.wait_for(state='visible', timeout=15000)
            need(calls.count('POST:start') == 1 and
                 'POST:stop' not in calls and 'POST:restart' not in calls,
                 'S03E3_UNEXPECTED_MUTATING_HTTP')
            context.close()
        finally:
            browser.close()
    print('S03E3_GENUINE_NATIVE_START_USEREXCEPTION_BROWSER_' + mode.upper() + '=PASS')


def s03e3c_native_stop_restart_http_red(mode, green=False):
    """Actual installed PHP POST Stop + Restart while SSH guest holds original FD9.

    The only browser mocks are read-only runtime and resources display,
    needed to show the Stop control without an installed upstream engine.
    Mutation HTTP is never intercepted. RED and GREEN are separate explicit modes.
    """
    import select
    import subprocess
    from playwright.sync_api import sync_playwright

    need(mode in ('en', 'ru') and os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE5_BROWSER_WAN') == '1',
         'S03E3C_DISPOSABLE_NATIVE_BROWSER_ONLY')
    root = Path(os.environ['RUNNER_TEMP']) / 'zapret2-browser-ssh'
    key = root / 'key'
    known = root / 'known_hosts'
    need(key.is_file() and known.is_file(),
         'S03E3C_EPHEMERAL_DISPOSABLE_SSH_IDENTITY_MISSING')

    ssh = [
        'ssh', '-T', '-i', str(key), '-p', '32222',
        '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-o', 'UserKnownHostsFile=' + str(known),
        '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=6',
        'root@127.0.0.1',
        'env', 'GITHUB_ACTIONS=true', 'ZAPRET2_STAGE5_BROWSER_WAN=1',
        '/usr/local/bin/python3', '/root/s03e3c-native-http-fd9-hold.py', '--hold',
    ]
    holder = subprocess.Popen(ssh, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, bufsize=1)
    passed = False
    observed = {}
    try:
        ready, _, _ = select.select([holder.stdout], [], [], 45)
        need(bool(ready) and holder.stdout.readline().strip() ==
             'S03E3C_ORIGINAL_FD9_BUSY_READY' and holder.poll() is None,
             'S03E3C_NATIVE_ORIGINAL_FD9_NOT_PROVEN_BUSY')
        origin = 'https://127.0.0.1:18443'
        with sync_playwright() as pw:
            options = {'executable_path': os.environ['STAGE5_LOCAL_CHROMIUM']} if os.environ.get('STAGE5_LOCAL_CHROMIUM') else {}
            browser = pw.chromium.launch(headless=True, **options)
            try:
                context = browser.new_context(ignore_https_errors=True)
                page = context.new_page()
                mutating_calls = []
                def runtime_display(route):
                    route.fulfill(status=200, content_type='application/json',
                                  body=json.dumps({'status':'ok','installed':True,'busy':False,
                                                   'version':'v1.0.7','setup':'ready',
                                                   'service':'started'}))
                def resources_display(route):
                    route.fulfill(status=200, content_type='application/json',
                                  body=json.dumps({'status':'ok','installed':False,
                                                   'busy':False,'phase':'not_installed'}))
                page.route('**/api/zapret/service/runtime', runtime_display)
                page.route('**/api/zapret/service/resourcesStatus', resources_display)
                page.on('request', lambda req:
                    mutating_calls.append(req.url.split('?')[0].rsplit('/', 1)[-1])
                    if req.method == 'POST' and
                       req.url.split('?')[0].endswith(('/api/zapret/service/stop',
                                                      '/api/zapret/service/restart',
                                                      '/api/zapret/service/start'))
                    else None)
                page.goto(origin + '/index.php', wait_until='domcontentloaded',
                          timeout=45000)
                page.locator('input[name="usernamefld"]').fill('root')
                page.locator('input[name="passwordfld"]').fill('opnsense')
                submits = page.locator('button[type="submit"],input[type="submit"]')
                if submits.count():
                    submits.first.click()
                else:
                    page.locator('input[name="passwordfld"]').press('Enter')
                with page.expect_response(
                    lambda r: '/api/zapret/settings/get' in r.url and r.status == 200,
                    timeout=45000):
                    page.goto(origin + '/ui/zapret',
                              wait_until='domcontentloaded', timeout=45000)
                need(page.evaluate("document.documentElement.lang || ''").lower().startswith(mode),
                     'S03E3C_ACTUAL_INSTALLED_BROWSER_LOCALE_WRONG_' + mode)
                page.locator('form#frm_GeneralSettings').wait_for(timeout=45000)
                page.wait_for_function(
                    "() => {let b=document.querySelector('#zapretServiceControl');"
                    "return !!b && !b.disabled && b.offsetWidth>0 &&"
                    "b.textContent.trim().length>0;}", timeout=25000)
                need(page.locator('#zapretServiceControl').inner_text().strip().lower() in
                     ('stop', 'остановить', 'стоп'),
                     'S03E3C_NATIVE_STRATEGIES_CONTROL_NOT_STOP')
                with page.expect_response(
                    lambda r: r.request.method == 'POST' and
                    r.url.split('?')[0].endswith('/api/zapret/service/stop'),
                    timeout=110000) as stop_result:
                    page.locator('#zapretServiceControl').click(timeout=20000)
                stop = stop_result.value
                # Restart has no separate Strategies button. Invoke installed
                # OPNsense's real restartAction through authenticated jQuery.
                with page.expect_response(
                    lambda r: r.request.method == 'POST' and
                    r.url.split('?')[0].endswith('/api/zapret/service/restart'),
                    timeout=110000) as restart_result:
                    page.evaluate("""() => {
                      $.ajax({type:'POST',
                              url:'/api/zapret/service/restart',
                              dataType:'json', timeout:100000});
                    }""")
                restart = restart_result.value
                error_title = ('Ошибка управления службой' if mode == 'ru'
                               else 'Service operation failed')
                if green:
                    # A genuine UserException from installed PHP must surface
                    # as HTTP failure, not a fake 200 or intercepted fixture.
                    for label, response in (('stop', stop), ('restart', restart)):
                        need(400 <= response.status < 600,
                             'S03E3D_NATIVE_HTTP_DID_NOT_REFUSE_' + label)
                        payload = response.json()
                        need(isinstance(payload, dict) and
                             isinstance(payload.get('errorMessage'), str) and
                             len(payload['errorMessage']) > 10 and
                             isinstance(payload.get('errorTitle'), str) and
                             bool(payload['errorTitle']),
                             'S03E3D_INSTALLED_USEREXCEPTION_NOT_DELIVERED_' + label)
                        need(payload['errorMessage'] not in
                             ('zapret-api-lifecycle-v1:stop:stopped',
                              'zapret-api-lifecycle-v1:restart:running'),
                             'S03E3D_RAW_TERMINAL_RECEIPT_LEAK')
                        # S05c2a: genuine held original FD9, not a mocked
                        # HTTP failure. Both verb-specific fixed refusals
                        # must survive shell -> configd -> PHP exactly.
                        expected_fd9 = ('Zapret2 Stop refused: original lifecycle lock is busy.'
                                        if label == 'stop' else
                                        'Zapret2 Restart refused: original lifecycle lock is busy.')
                        need(payload['errorMessage'] == expected_fd9,
                             'S05C2A_REAL_NATIVE_FD9_CAUSE_NOT_DELIVERED_' + label)
                        observed[label] = 'FD9_BUSY_VERIFIED'
                    page.get_by_text(error_title, exact=False).first.wait_for(
                        state='visible', timeout=15000)
                    stop_message = ('Остановка Zapret2 отклонена: другая операция удерживает блокировку службы.'
                                    if mode == 'ru' else
                                    'Zapret2 Stop refused: original lifecycle lock is busy.')
                    page.get_by_text(stop_message, exact=False).first.wait_for(
                        state='visible', timeout=15000)
                else:
                    need(stop.status == 200 and restart.status == 200,
                         'S03E3C_OLD_NATIVE_API_HTTP_STATUS_CHANGED')
                    for label, response in (('stop',stop),('restart',restart)):
                        payload = response.json()
                        need(isinstance(payload, dict) and
                             isinstance(payload.get('response'), str),
                             'S03E3C_INHERITED_PHP_RESPONSE_SHAPE_CHANGED_' + label)
                        text_response = payload['response'].strip()
                        observed[label] = ('EMPTY' if not text_response else
                                           'OK' if text_response == 'OK' else
                                           'OTHER_REDACTED')
                    page.wait_for_timeout(400)
                    need(page.get_by_text(error_title, exact=False).count() == 0,
                         'S03E3C_OLD_GUI_ALREADY_DISPLAYS_STOP_FAILURE')
                need(mutating_calls == ['stop', 'restart'],
                     'S03E3C_UNEXPECTED_NATIVE_MUTATING_HTTP_ROUTE')
                context.close()
            finally:
                browser.close()
        passed = True
    finally:
        if holder.stdin and not holder.stdin.closed:
            try:
                holder.stdin.write('VERIFY\n' if passed else 'ABORT\n')
                holder.stdin.flush()
                holder.stdin.close()
                holder.stdin = None
            except (BrokenPipeError, OSError):
                pass
        try:
            output, _ = holder.communicate(timeout=165)
        except subprocess.TimeoutExpired:
            # Remote guest is already disposable. Abort rather than claim
            # success; the native holder's own bounded drain still owns FD9.
            raise Refusal('S03E3C_NATIVE_HOLDER_TIMEOUT') from None
        if passed:
            need(holder.returncode == 0 and
                 'S03E3C_NATIVE_HTTP_CONFIG_IPFW_ENGINE_UNCHANGED=PASS' in output,
                 'S03E3C_NATIVE_POST_HTTP_WITNESS_NOT_CONFIRMED')
    if green:
        print('S03E3D_GENUINE_NATIVE_PHP_STOP_RESTART_HTTP_GREEN_' + mode.upper() + '=' +
              json.dumps({'real_http_stop':stop.status,
                          'real_http_restart':restart.status,
                          'backend_response':observed,
                          'localized_stop_failure_visible':True,
                          'verified_fd9_busy_cause_visible':True,
                          'original_fd9_busy':True,
                          'native_config_ipfw_engine_unchanged':True,
                          'physical_stop_restart_executed':False}, sort_keys=True))
    else:
        print('S03E3C_GENUINE_PHP_STOP_RESTART_HTTP_RED_' + mode.upper() + '=' +
              json.dumps({'http_stop':200, 'http_restart':200,
                          'inherited_response_class':observed,
                          'old_gui_stop_failure_visible':False,
                          'original_fd9_busy':True,
                          'native_config_ipfw_engine_unchanged':True,
                          'physical_stop_restart_executed':False}, sort_keys=True))


def real_browser():
    from playwright.sync_api import sync_playwright
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE5_BROWSER_WAN') == '1',
         'REAL_BROWSER_DISPOSABLE_CI_OPTIN_REQUIRED')
    origin = 'https://127.0.0.1:18443'
    with sync_playwright() as pw:
        browser_args = {'executable_path': os.environ['STAGE5_LOCAL_CHROMIUM']} if os.environ.get('STAGE5_LOCAL_CHROMIUM') else {}
        browser = pw.chromium.launch(headless=True, **browser_args)
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
                 r.url.split('?')[0].endswith('/api/zapret/settings/apply'), timeout=90000) as response:
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


def s05c2c_missing_engine_http():
    """Real authenticated API under saved WAN, no GUI click or route mocking."""
    from playwright.sync_api import sync_playwright
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE5_BROWSER_WAN') == '1',
         'S05C2C_DISPOSABLE_CHROMIUM_ONLY')
    origin = 'https://127.0.0.1:18443'
    with sync_playwright() as pw:
        options = {'executable_path': os.environ['STAGE5_LOCAL_CHROMIUM']} if os.environ.get('STAGE5_LOCAL_CHROMIUM') else {}
        browser = pw.chromium.launch(headless=True, **options)
        try:
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(origin + '/index.php', wait_until='domcontentloaded', timeout=45000)
            page.locator('input[name="usernamefld"]').fill('root')
            page.locator('input[name="passwordfld"]').fill('opnsense')
            submit = page.locator('button[type="submit"],input[type="submit"]')
            if submit.count():
                submit.first.click()
            else:
                page.locator('input[name="passwordfld"]').press('Enter')
            with page.expect_response(
                    lambda r: '/api/zapret/settings/get' in r.url and r.status == 200,
                    timeout=45000):
                page.goto(origin + '/ui/zapret', wait_until='domcontentloaded', timeout=45000)
            page.locator('form#frm_GeneralSettings').wait_for(timeout=45000)
            # Service GUI control is intentionally DISABLED without upstream:
            # send one authenticated direct POST using the page's real AJAX
            # CSRF handling. Never intercept a mutation or claim a GUI click.
            result = page.evaluate("""async () => new Promise(resolve => {
                jQuery.ajax({
                    type:'POST', url:'/api/zapret/service/start',
                    dataType:'json', timeout:90000
                }).done((body, _text, xhr) =>
                    resolve({status:xhr.status,body:body}))
                  .fail(xhr =>
                    resolve({status:xhr.status,body:xhr.responseJSON||null}));
            })""")
            need(isinstance(result, dict) and
                 400 <= result.get('status', 0) < 600,
                 'S05C2C_ACTUAL_START_HTTP_NOT_REFUSED')
            body = result.get('body')
            need(isinstance(body, dict) and
                 body.get('errorMessage') ==
                     'Zapret2 Start refused: engine is not installed.' and
                 isinstance(body.get('errorTitle'), str) and
                 len(body['errorTitle']) > 0,
                 'S05C2C_ACTUAL_ORIGINAL_CAUSE_NOT_DELIVERED')
            context.close()
        finally:
            browser.close()
    print('S05C2C_NATIVE_SAVED_WAN_REAL_AUTHENTICATED_HTTP_ENGINE_ABSENT=PASS')

def main():
    try:
        if sys.argv[1:] == ['--self-test']:
            self_test()
        elif sys.argv[1:] in (['--s03e3-en-browser'], ['--s03e3-ru-browser']):
            native_wan_start_error_browser('en' if 'en' in sys.argv[1] else 'ru')
        elif sys.argv[1:] in (['--s03e3c-en-browser'], ['--s03e3c-ru-browser']):
            s03e3c_native_stop_restart_http_red('en' if 'en' in sys.argv[1] else 'ru')
        elif sys.argv[1:] in (['--s03e3d-en-browser'], ['--s03e3d-ru-browser']):
            s03e3c_native_stop_restart_http_red('en' if 'en' in sys.argv[1] else 'ru', green=True)
        elif sys.argv[1:] == ['--s05c2c-absent-engine-browser']:
            s05c2c_missing_engine_http()
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
