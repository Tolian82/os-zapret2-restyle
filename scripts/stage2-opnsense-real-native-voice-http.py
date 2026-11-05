#!/usr/bin/env python3
"""Authenticated OPNsense Voice web API on disposable native lo0 owner.

The stock UI's /api/zapret/voice/apply path is exercised through HTTPS and
an actual cookie-authenticated session, not direct configctl. This is NOT a
browser click or WAN/Voice media acceptance.
"""
import hashlib
import html.parser
import http.cookiejar
import ipaddress
import importlib.util
import json
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ORIGIN = 'https://127.0.0.1'
OPTIN = 'ZAPRET2_STAGE2_REAL_VOICE_HTTP'
SERVICES = ('telegram', 'discord', 'x', 'sip', 'custom')


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def exact_disposable_target(value):
    # Native IPSET may render an IPv4 /32 as either a CIDR or a host.
    # Require the SAME precise documentation address, never a larger range.
    try:
        return isinstance(value, str) and ipaddress.ip_network(
            value, strict=False) == ipaddress.ip_network('192.0.2.42/32')
    except ValueError:
        return False


def config_without_revision(raw):
    # OPNsense Config::save legitimately advances root revision metadata on
    # each successful GUI Apply; require every other XML value to survive.
    root = ET.fromstring(raw)
    need(root.tag == 'opnsense' and len(root.findall('revision')) <= 1,
         'INVALID_NATIVE_CONFIG_REVISION_SHAPE')
    for revision in root.findall('revision'):
        root.remove(revision)
    def normalize(node):
        if not (node.text or '').strip():
            node.text = None
        node.tail = None
        for child in node:
            normalize(child)
    normalize(root)
    return ET.tostring(root, encoding='utf-8')


def native_model_extra_fields(raw):
    # The native snapshot covers every general/strategy/voice/hostlist field.
    # Retain independent proof for any other Zapret XML subtree and attrs.
    root = ET.fromstring(raw)
    models = root.findall('./OPNsense/Zapret')
    need(len(models) == 1, 'NATIVE_ZAPRET_XML_MODEL_AMBIGUOUS')
    model = models[0]
    for child in list(model):
        if child.tag in ('general', 'strategy', 'voice', 'hostlist'):
            model.remove(child)
    def normalize(node):
        if not (node.text or '').strip():
            node.text = None
        node.tail = None
        for member in node:
            normalize(member)
    normalize(model)
    return ET.tostring(model, encoding='utf-8')


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_').replace('.', '_'), HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class Inputs(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'input':
            return
        item = dict(attrs)
        # OPNsense generates a random, per-session CSRF field NAME, not a
        # static __csrf_magic input. Match the exact stock base64url shape.
        name, value = item.get('name', ''), item.get('value', '')
        if item.get('type') == 'hidden' and re.fullmatch(r'[A-Za-z0-9_-]{16,64}', name) and \
                re.fullmatch(r'[A-Za-z0-9_-]{16,64}', value):
            self.values[name] = value


def form_fields(model, snapshot, *, port):
    """Exact five-service Voice form used by the installed jQuery page."""
    need(re.fullmatch('[a-f0-9]{64}', snapshot) is not None,
         'NOT_NATIVE_64_HEX_FORM_SNAPSHOT')
    need(port in ('3478', '3479'), 'UNSAFE_TEST_UDP_PORT')
    need(set(model['voice']) >= set(SERVICES) and
         set(model['hostlist']) >= {s + 'ips' for s in SERVICES},
         'INCOMPLETE_INSTALLED_VOICE_LOAD')
    result = [('zapret[sync][snapshot]', snapshot)]
    for name in SERVICES:
        item = model['voice'][name]
        enabled = str(item['enabled'])
        args = str(item['args'])
        need(enabled in ('0', '1'), 'UNTRUSTED_VOICE_ENABLED_VALUE')
        if name == 'telegram':
            need(enabled == '1' and any('--filter-udp=' + old in args for old in ('3478', '3479')) and
                 '--filter-l7=stun' in args and '--payload=stun' in args,
                 'NOT_EXPECTED_DISPOSABLE_VOICE_PROFILE')
            args = args.replace('--filter-udp=3478', '--filter-udp=' + port, 1).replace(
                '--filter-udp=3479', '--filter-udp=' + port, 1)
        result.extend((('zapret[voice][' + name + '][enabled]', enabled),
                       ('zapret[voice][' + name + '][args]', args),
                       ('zapret[hostlist][' + name + 'ips]',
                        str(model['hostlist'][name + 'ips']))))
    need(len(result) == 16 and result[-1][0] == 'zapret[hostlist][customips]',
         'VOICE_FORM_FIELD_SET_CHANGED')
    need(exact_disposable_target(dict(result)['zapret[hostlist][telegramips]']),
         'NOT_EXACT_TEST_ONLY_TELEGRAM_IPSET')
    return result


def test_contracts():
    fields = {'voice': {s: {'enabled': '0', 'args': ''} for s in SERVICES},
              'hostlist': {s + 'ips': '' for s in SERVICES}}
    fields['voice']['telegram'] = {'enabled': '1', 'args':
        '--filter-udp=3478\n--filter-l7=stun\n--payload=stun'}
    fields['hostlist']['telegramips'] = '192.0.2.42/32'
    a = form_fields(fields, 'a' * 64, port='3479')
    assert len(a) == 16 and ('zapret[voice][telegram][args]',
                             '--filter-udp=3479\n--filter-l7=stun\n--payload=stun') in a
    assert form_fields(fields, 'a' * 64, port='3478') != a
    for bad in ('', 'a' * 63, 'G' * 64):
        try:
            form_fields(fields, bad, port='3479')
        except Refusal:
            pass
        else:
            raise AssertionError('bad snapshot permitted')
    for port in ('*', '443', '0', '65536'):
        try:
            form_fields(fields, 'a' * 64, port=port)
        except Refusal:
            pass
        else:
            raise AssertionError('non-test UDP port permitted')
    bad = json.loads(json.dumps(fields))
    bad['hostlist']['telegramips'] = '0.0.0.0/0'
    try:
        form_fields(bad, 'a' * 64, port='3479')
    except Refusal:
        pass
    else:
        raise AssertionError('foreign IPSET permitted')
    baseline_xml = b'<opnsense><revision>1</revision><OPNsense><Zapret><voice>1</voice></Zapret></OPNsense></opnsense>'
    same_xml = b'<opnsense><revision>2</revision><OPNsense><Zapret><voice>1</voice></Zapret></OPNsense></opnsense>'
    drift_xml = same_xml.replace(b'<voice>1', b'<voice>0')
    assert config_without_revision(baseline_xml) == config_without_revision(same_xml)
    assert config_without_revision(baseline_xml) != config_without_revision(drift_xml)
    extra_original = b'<opnsense><OPNsense><Zapret version="2"><voice>1</voice><strategylab><enablequic>0</enablequic></strategylab></Zapret></OPNsense></opnsense>'
    extra_voice = extra_original.replace(b'<voice>1', b'<voice>0')
    extra_changed = extra_original.replace(b'<enablequic>0', b'<enablequic>1')
    assert native_model_extra_fields(extra_original) == native_model_extra_fields(extra_voice)
    assert native_model_extra_fields(extra_original) != native_model_extra_fields(extra_changed)
    assert exact_disposable_target('192.0.2.42')
    assert exact_disposable_target('192.0.2.42/32')
    assert not exact_disposable_target('192.0.2.40/29')
    assert not exact_disposable_target('0.0.0.0/0')
    parser = Inputs()
    parser.feed('<form method="post"><input type="hidden" name="abcdefghijklmnopqrstuv" '
                'value="0123456789abcdefghij-_" />'
                '<input type="hidden" name="cookie_test" value="1" /></form>')
    assert parser.values == {'abcdefghijklmnopqrstuv': '0123456789abcdefghij-_'}
    print('PASS: Voice HTTP form, dynamic OPNsense CSRF, token and scope negatives')


class GuestHttps:
    def __init__(self):
        # No outbound fetches, no external domains and no credentials outside
        # this disposable OPNsense VM's local TLS service.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.csrf_token = None
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            urllib.request.HTTPSHandler(context=ctx))

    def request(self, method, path, payload=None):
        need(path.startswith('/') and not path.startswith('//') and
             '?' not in path and '#' not in path,
             'UNTRUSTED_GUI_HTTP_PATH')
        body = urllib.parse.urlencode(payload).encode('utf-8') if payload is not None else None
        headers = {'User-Agent': 'Zapret2-disposable-native-web-acceptance',
                   'Referer': ORIGIN + '/ui/zapret/voice',
                   'Accept': 'application/json, text/html'}
        if method == 'POST' and path.startswith('/api/'):
            need(self.csrf_token is not None, 'AUTHENTICATED_GUI_CSRF_MISSING')
            headers['X-CSRFToken'] = self.csrf_token
        req = urllib.request.Request(ORIGIN + path, data=body, method=method,
                                     headers=headers)
        try:
            with self.client.open(req, timeout=30 if path != '/api/zapret/voice/apply' else 640) as res:
                code, data, final = res.status, res.read(2 * 1024 * 1024), res.geturl()
        except urllib.error.HTTPError as e:
            raise Refusal('GUI_HTTP_REJECTED_' + str(e.code) + ':' + path) from None
        except (urllib.error.URLError, OSError, TimeoutError):
            raise Refusal('GUI_HTTP_TRANSPORT_UNAVAILABLE:' + path) from None
        need(final.startswith(ORIGIN + '/') and len(data) <= 2 * 1024 * 1024,
             'GUI_HTTP_REDIRECT_OR_RESPONSE_UNTRUSTED')
        need(code == 200, 'GUI_HTTP_STATUS_' + str(code))
        return data.decode('utf-8', 'replace')

    def api(self, method, path, payload=None):
        text = self.request(method, path, payload)
        try:
            value = json.loads(text)
        except ValueError:
            raise Refusal('GUI_HTTP_EXPECTED_JSON:' + path) from None
        need(isinstance(value, dict), 'GUI_HTTP_WRONG_JSON_SHAPE')
        return value


def login(http):
    page = http.request('GET', '/index.php')
    parser = Inputs()
    parser.feed(page)
    payload = dict(parser.values)
    need(len(payload) == 1, 'DISPOSABLE_GUI_LOGIN_CSRF_MISSING_OR_AMBIGUOUS')
    # The standard root login is used solely on this disposable QEMU guest.
    # Never read or print user credentials or modify any real appliance user.
    payload.update({'usernamefld': 'root', 'passwordfld': 'opnsense', 'login': '1'})
    http.request('POST', '/index.php', payload)
    page = http.request('GET', '/ui/zapret/voice')
    need('frm_VoiceSettings' in page and 'voiceApply' in page,
         'INSTALLED_GUI_LOGIN_OR_VOICE_PAGE_UNAVAILABLE')
    # MVC page embeds the token that its jQuery AJAX calls send in the
    # X-CSRFToken header. It can change after login/session rotation.
    tokens = re.findall(r'X-CSRFToken\",\s*\"([A-Za-z0-9_-]{16,64})\"', page)
    need(len(set(tokens)) == 1, 'INSTALLED_GUI_AJAX_CSRF_MISSING_OR_AMBIGUOUS')
    http.csrf_token = tokens[0]
    return True


def assert_saved_only_voice(active, boot, original, *, expected_port):
    now = active.CONFIG.read_bytes()
    need(boot.config_except_model(now) == boot.config_except_model(original) and
         boot.protected_model_values(now) == boot.protected_model_values(original),
         'GUI_APPLY_CHANGED_STRATEGIES_OR_FOREIGN_CONFIG')
    root = ET.fromstring(now)
    args = root.findtext('./OPNsense/Zapret/voice/telegram/args') or ''
    need(root.findtext('./OPNsense/Zapret/voice/telegram/enabled') == '1' and
         '--filter-udp=' + expected_port in args and
         exact_disposable_target(root.findtext('./OPNsense/Zapret/hostlist/telegramips')),
         'GUI_APPLY_SAVED_WRONG_VOICE_PROFILE')
    return now


def execute():
    need(os.environ.get(OPTIN) == '1', 'EXPLICIT_DISPOSABLE_GUI_HTTP_OPTIN_REQUIRED')
    active = module('stage2-opnsense-real-native-active-service.py')
    common = module('stage2-opnsense-real-native-shared-voice.py')
    boot = module('stage2-opnsense-real-native-boot-syshook.py')
    engine_sha = active.guest_preflight()
    baseline = common.witness(active, engine_sha, running=True)
    original = active.CONFIG.read_bytes()
    http = GuestHttps()
    login(http)
    before = http.api('GET', '/api/zapret/voice/load')
    need('zapret' in before and re.fullmatch('[a-f0-9]{64}', str(before.get('snapshot'))) is not None,
         'AUTHENTICATED_GUI_LOAD_SNAPSHOT_MISSING')
    form = form_fields(before['zapret'], before['snapshot'], port='3479')
    stale = [(key, 'f' * 64 if key == 'zapret[sync][snapshot]' else value)
             for key, value in form]
    rejected = http.api('POST', '/api/zapret/voice/apply', stale)
    need(rejected.get('result') == 'failed' and rejected.get('applied') is False and
         rejected.get('requires_review') is False,
         'STALE_GUI_TOKEN_NOT_REJECTED_BEFORE_APPLY')
    need(active.CONFIG.read_bytes() == original and
         common.witness(active, engine_sha, running=True) == baseline,
         'STALE_GUI_POST_MUTATED_ENGINE_OR_CONFIG')
    applied = http.api('POST', '/api/zapret/voice/apply', form)
    need(applied.get('result') == 'saved' and applied.get('applied') is True and
         re.fullmatch('[a-f0-9]{64}', str(applied.get('snapshot'))) is not None,
         'AUTHENTICATED_GUI_APPLY_NOT_CONFIRMED')
    altered = assert_saved_only_voice(active, boot, original, expected_port='3479')
    current = common.witness(active, engine_sha, running=True)
    need(current['id'] != baseline['id'] and current['pid'] != baseline['pid'],
         'GUI_APPLY_DID_NOT_REPLACE_COMMON_OWNER')
    loaded = http.api('GET', '/api/zapret/voice/load')
    need(loaded.get('snapshot') == applied['snapshot'],
         'GUI_APPLY_RESPONSE_SNAPSHOT_DIFFERS_FROM_NATIVE_LOAD')
    # The installed page loads the new generation, then reverses the edit.
    restored_form = form_fields(loaded['zapret'], loaded['snapshot'], port='3478')
    restored = http.api('POST', '/api/zapret/voice/apply', restored_form)
    need(restored.get('result') == 'saved' and restored.get('applied') is True,
         'GUI_RESTORE_APPLY_UNCONFIRMED')
    assert_saved_only_voice(active, boot, altered, expected_port='3478')
    final = common.witness(active, engine_sha, running=True)
    need(final['id'] != current['id'], 'GUI_RESTORE_SHARED_COMMIT_ID_NOT_ADVANCED')
    need(final['pid'] != current['pid'], 'GUI_RESTORE_REAL_ENGINE_PID_NOT_ADVANCED')
    need(final['rules'] == baseline['rules'], 'GUI_RESTORE_SCOPED_IPFW_RULES_CHANGED')
    final_load = http.api('GET', '/api/zapret/voice/load')
    need(final_load.get('snapshot') == before['snapshot'],
         'GUI_RESTORE_MODEL_SNAPSHOT_DIFFERS_FROM_BASELINE')
    need(native_model_extra_fields(active.CONFIG.read_bytes()) ==
         native_model_extra_fields(original),
         'GUI_RESTORE_NATIVE_EXTRA_MODEL_FIELDS_CHANGED')
    # OPNsense's native model serialization may rewrite XML representation
    # while preserving every model field (proven by the authoritative
    # snapshot), all extra plugin groups and every unrelated Config field.
    # Record this difference openly; it is not byte-for-byte restoration.
    raw_same_except_revision = (
        config_without_revision(active.CONFIG.read_bytes()) ==
        config_without_revision(original))
    return {'schema': 1, 'status': 'PASS_REAL_NATIVE_AUTHENTICATED_VOICE_HTTP_APPLY',
            'installed_web_page_loaded': True, 'authenticated_native_http_api': True,
            'stale_snapshot_refused_before_mutation': True,
            'gui_apply_and_restore_committed_under_shared_fd9': True,
            'native_voice_model_snapshot_restored': True,
            'extra_plugin_xml_fields_unchanged': True,
            'full_xml_same_except_revision': raw_same_except_revision,
            'same_shared_engine_owner': True,
            'loopback_only': True, 'browser_button_click_tested': False,
            'voice_media_tested': False, 'owner_appliance_modified': False}


def main():
    if sys.argv[1:] == ['--self-test']:
        test_contracts()
        return 0
    try:
        need(sys.argv[1:] == ['run'], 'RUN_OR_SELF_TEST_REQUIRED')
        report = execute()
    except (Refusal, OSError, KeyError, ValueError, TypeError, ET.ParseError) as error:
        print('STAGE2_REAL_VOICE_HTTP=REFUSED:' + str(error), file=sys.stderr)
        return 2
    print('STAGE2_REAL_VOICE_HTTP=' + json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
