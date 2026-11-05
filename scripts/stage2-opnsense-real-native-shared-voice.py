#!/usr/bin/env python3
"""Installed native common Strategies/Telegram Voice owner on disposable OPNsense.

Runs only after a real published RUNNING -> source-built Mk package replacement.
Uses the existing original-FD9 configctl Telegram adapter and shared Apply,
with TCP and scoped UDP confined to lo0. No live WAN or media evidence.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
JOURNAL = Path('/var/db/zapret2/shared-apply/operation.json')
TARGET = '192.0.2.42/32'  # RFC 5737 documentation-only; never send packets.
OPTIN = 'ZAPRET2_STAGE2_REAL_COMMON_VOICE'


class Refusal(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def module(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace('-', '_').replace('.', '_'), HERE / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def checked_rules(lines):
    """Never accept a second engine's rule or a non-loopback UDP capture."""
    matches = [line.strip() for line in lines if re.match(r'^190(?:0\d|10)\s', line)]
    need(len(matches) == 2, 'COMMON_OWNER_MUST_HAVE_EXACTLY_TWO_SCOPED_RULES')
    voice, ordinary = matches
    need(voice.startswith('19000 ') and 'divert 989 udp ' in voice and
         'table(zapret2_voice_telegram)' in voice and
         'not diverted' in voice and 'xmit lo0' in voice,
         'VOICE_RULE_NOT_DESTINATION_SCOPED_TO_LOOPBACK')
    need(ordinary.startswith('19001 ') and 'divert 989 tcp ' in ordinary and
         '65431' in ordinary and 'not diverted' in ordinary and
         'xmit lo0' in ordinary, 'ORDINARY_RULE_NOT_LOOPBACK_ONLY')
    return matches


def checked_journal(raw):
    need(isinstance(raw, dict) and raw.get('schema') == 1 and
         raw.get('phase') == 'committed' and
         isinstance(raw.get('detail'), dict) and
         raw['detail'].get('page') == 'voice' and
         re.fullmatch(r'[a-f0-9]{32}', str(raw['detail'].get('id', ''))),
         'NATIVE_COMMON_JOURNAL_NOT_COMMITTED_VOICE')
    return raw['detail']['id']


def test_contracts():
    base = ['19000 divert 989 udp from any to table(zapret2_voice_telegram) '
            'out not diverted not sockarg xmit lo0',
            '19001 divert 989 tcp from any to any 65431 '
            'out not diverted not sockarg xmit lo0']
    assert checked_rules(base) == base
    sample = {'schema': 1, 'phase': 'committed',
              'detail': {'page': 'voice', 'id': 'a' * 32}}
    assert checked_journal(sample) == 'a' * 32
    negatives = [base[:1], base + [base[0]],
                 [base[0].replace('lo0', 'vtnet1'), base[1]],
                 [base[0].replace('table(zapret2_voice_telegram)', 'any'), base[1]],
                 [base[0], base[1].replace('65431', '443')],
                 [base[1], base[0]]]
    for rows in negatives:
        try:
            checked_rules(rows)
        except Refusal:
            pass
        else:
            raise AssertionError('unsafe common rule set accepted')
    for bad in ({}, {'schema': 1, 'phase': 'activating', 'detail': sample['detail']},
                {'schema': 1, 'phase': 'committed',
                 'detail': {'page': 'strategies', 'id': 'a' * 32}}):
        try:
            checked_journal(bad)
        except Refusal:
            pass
        else:
            raise AssertionError('foreign/nonterminal common owner accepted')
    # Regression: a failed installed PHP -r command must never disclose its
    # source code or a future user field through public CI exception text.
    class FailingCommand:
        def cmd(self, args, timeout):
            from types import SimpleNamespace
            return SimpleNamespace(returncode=69, stdout='', stderr='secret')
    try:
        invoke(FailingCommand(), '/usr/local/bin/php', '-r',
               'SECRET_PRIVATE_PHP_PROGRAM')
    except Refusal as error:
        assert str(error) == 'INSTALLED_ACTION_REFUSED:php:rc=69'
    else:
        raise AssertionError('private PHP source leaked or action accepted')
    print('PASS: native shared Voice loopback/journal/error-redaction contracts')


def invoke(active, *args, timeout=300):
    response = active.cmd(list(args), timeout=timeout)
    # Arguments can contain a complete private PHP program or user payload.
    # Report only the fixed executable name and exit code, never argv contents.
    need(response.returncode == 0, 'INSTALLED_ACTION_REFUSED:' +
         Path(str(args[0])).name + ':rc=' + str(response.returncode))
    return response.stdout


def prepare_fixture(active, boot):
    need(not JOURNAL.exists() and not JOURNAL.is_symlink(),
         'FOREIGN_SHARED_OWNER_EXISTS_BEFORE_VOICE_TEST')
    old = active.CONFIG.read_bytes()
    foreign = boot.config_except_model(old)
    strategies = boot.protected_model_values(old)
    boot.canonicalize_disposable_model()
    php = r'''require_once('script/load_phalcon.php');
$config = \OPNsense\Core\Config::getInstance();
$config->lock();
try {
    $model = new \OPNsense\Zapret\Zapret();
    $nodes = $model->getNodes();
    foreach (['telegram','discord','x','sip','custom'] as $name) {
        if (($nodes['voice'][$name]['enabled'] ?? '0') !== '0') {
            throw new \RuntimeException('Fixture requires all Voice OFF');
        }
    }
    $nodes['hostlist']['telegramips'] = '192.0.2.42/32';
    $nodes['voice']['telegram']['args'] = "--filter-udp=3478\n--filter-l7=stun\n--payload=stun\n--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2";
    $model->setNodes($nodes);
    // The isolated lo0 test interface is not an end-user selectable WAN.
    // Match the accepted _145 native synthetic MVC canonicalization: the
    // installed serializer runs, but UI InterfaceField validation is not a
    // requirement for the deliberately isolated testing fixture.
    if (!$model->serializeToConfig(false, true)) {
        throw new \RuntimeException('Fixture model validation refused');
    }
    $config->save(['description'=>'Disposable scoped Voice OFF fixture']);
} catch (\Throwable $error) {
    fwrite(STDERR, "DISPOSABLE_NATIVE_VOICE_FIXTURE_REFUSED\n");
    exit(69);
} finally {
    $config->unlock();
}
'''
    invoke(active, '/usr/local/bin/php', '-r', php, timeout=60)
    saved = active.CONFIG.read_bytes()
    need(boot.config_except_model(saved) == foreign and
         boot.protected_model_values(saved) == strategies,
         'VOICE_FIXTURE_CHANGED_STRATEGIES_OR_FOREIGN_CONFIG')
    root = ET.fromstring(saved)
    voice = root.find('./OPNsense/Zapret/voice')
    need(voice is not None and
         voice.findtext('./telegram/enabled') == '0' and
         'filter-udp=3478' in (voice.findtext('./telegram/args') or '') and
         root.findtext('./OPNsense/Zapret/hostlist/telegramips') == TARGET,
         'VOICE_OFF_FIXTURE_NOT_SERIALIZED_BY_INSTALLED_MODEL')
    return saved, foreign, strategies


def witness(active, engine_sha, *, running):
    status = active.action('status')
    need((status.returncode == 0 and 'zapret is running' in status.stdout)
         if running else status.returncode == 1 and
         status.stdout.strip() == 'zapret is not running',
         'COMMON_NATIVE_SERVICE_STATUS_INCORRECT')
    report = json.loads(invoke(active, '/usr/local/sbin/configctl',
                               'zapret', 'voice_inspect', timeout=60))
    need(report.get('source') == 'native-common' and
         report.get('state') == ('ready' if running else 'stopped'),
         'COMMON_NATIVE_READONLY_INSPECT_NOT_ATTESTED')
    st = JOURNAL.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
         st.st_mode & 0o077 == 0 and st.st_size < 8192,
         'COMMON_JOURNAL_FILE_NOT_SECURE')
    owner = checked_journal(json.loads(JOURNAL.read_text()))
    need(hashlib.sha256(active.ENGINE.read_bytes()).hexdigest() == engine_sha,
         'PINNED_NATIVE_ENGINE_CHANGED')
    if not running:
        need(report.get('rule_count') == 0 and
             not active.plugin_rules() and not active.PID.exists(),
             'STOP_LEFT_ACTIVE_COMMON_OWNER')
        return {'id': owner, 'state': 'stopped'}
    pidfile = active.PID
    need(pidfile.is_file() and not pidfile.is_symlink(),
         'COMMON_ENGINE_PIDFILE_MISSING')
    pid = pidfile.read_text().strip()
    need(pid.isdecimal() and int(pid) > 1,
         'COMMON_ENGINE_PID_INVALID')
    process = active.cmd(['/bin/ps', '-p', pid, '-o', 'command='], timeout=20)
    need(process.returncode == 0 and
         process.stdout.strip().split(' ')[0] == str(active.ENGINE),
         'COMMON_ENGINE_NOT_REAL_PINNED_DVTWS2')
    rules = checked_rules(active.plugin_rules())
    need(report.get('rule_count') == 2 and report.get('table_count') == 1 and
         report.get('runtime', {}).get('engine_verified') is True and
         report.get('runtime', {}).get('supervisor_verified') is True and
         report.get('runtime', {}).get('services', {}).get('telegram', {}).get('configured') is True,
         'COMMON_VOICE_RUNTIME_OR_IPFW_NOT_ATTESTED')
    table = invoke(active, '/sbin/ipfw', 'table',
                   'zapret2_voice_telegram', 'list', timeout=20)
    need(TARGET in table, 'VOICE_TABLE_NOT_EXACT_TEST_DESTINATION')
    return {'id': owner, 'pid': int(pid), 'rules': rules}


def execute():
    active = module('stage2-opnsense-real-native-active-service.py')
    boot = module('stage2-opnsense-real-native-boot-syshook.py')
    need(os.environ.get(OPTIN) == '1', 'EXPLICIT_COMMON_VOICE_CI_OPTIN_REQUIRED')
    engine_sha = active.guest_preflight()
    before = active.live_state(engine_sha)
    _, foreign, strategies = prepare_fixture(active, boot)
    need(active.live_state(engine_sha) == before,
         'VOICE_OFF_FIXTURE_MODIFIED_EXISTING_ENGINE')
    invoke(active, '/usr/local/sbin/configctl', 'zapret',
           'telegram_voice_enable', timeout=600)
    saved = active.CONFIG.read_bytes()
    root = ET.fromstring(saved)
    need(root.findtext('./OPNsense/Zapret/voice/telegram/enabled') == '1' and
         boot.config_except_model(saved) == foreign and
         boot.protected_model_values(saved) == strategies,
         'COMMON_APPLY_DID_NOT_ATOMICALLY_SAVE_REQUESTED_VOICE')
    first = witness(active, engine_sha, running=True)
    need(first['pid'] != before['pid'], 'COMMON_APPLY_REUSED_ORDINARY_PID')
    python_down = active.action('stop', python_down=True)
    need(python_down.returncode == 69 and
         'shared/Voice ownership requires qualified Python' in python_down.stderr,
         'PYTHON_DOWN_SHARED_OWNER_STOP_WAS_NOT_REFUSED')
    need(witness(active, engine_sha, running=True) == first and
         active.CONFIG.read_bytes() == saved,
         'PYTHON_DOWN_REFUSAL_CHANGED_SHARED_OWNER')
    invoke(active, '/usr/local/sbin/configctl', 'zapret', 'stop', timeout=180)
    stopped = witness(active, engine_sha, running=False)
    need(stopped['id'] == first['id'] and active.CONFIG.read_bytes() == saved,
         'NATIVE_COMMON_STOP_CHANGED_JOURNAL_OR_CONFIG')
    invoke(active, '/usr/local/sbin/configctl', 'zapret', 'start', timeout=600)
    second = witness(active, engine_sha, running=True)
    need(second['id'] == first['id'] and second['pid'] != first['pid'] and
         second['rules'] == first['rules'] and active.CONFIG.read_bytes() == saved,
         'COMMON_START_DID_NOT_RESTORE_SAME_SEALED_OWNER')
    return {'schema': 1, 'status': 'PASS_REAL_INSTALLED_NATIVE_COMMON_VOICE',
            'native_apply_via_existing_configctl': True,
            'original_fd9_common_journal_committed': True,
            'single_real_engine': True, 'loopback_only': True,
            'python_down_shared_stop_refused_before_mutation': True,
            'native_stop_start_restored_owner': True,
            'config_preserved_during_stop_start': True,
            'web_gui_click_tested': False, 'voice_media_tested': False,
            'owner_appliance_modified': False}


def main():
    if sys.argv[1:] == ['--self-test']:
        test_contracts()
        return 0
    try:
        need(sys.argv[1:] == ['run'], 'RUN_OR_SELF_TEST_REQUIRED')
        result = execute()
    except (Refusal, OSError, KeyError, ValueError, ET.ParseError) as exc:
        print('STAGE2_REAL_COMMON_VOICE=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_REAL_COMMON_VOICE=' + json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
