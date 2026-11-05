#!/usr/bin/env python3
"""Genuine OPNsense 26.7 shutdown/start syshook lifecycle on disposable QEMU.

prepare: after the accepted genuine RUNNING old pkg -> native replacement;
         installs only two passive *test* observation hooks, then the pinned
         VM action performs a real clean shutdown and fresh kernel boot.
verify:  reads after-stop and after-start observations from different kernels,
         proves real dvtws2 PID, lo0-only IPFW and retained saved Config.
No explicit start/stop in this test, no WAN, no Voice, no production hooks edit.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('/root/stage2-zapret-native-real-boot')
RECORD = ROOT / 'prepared.json'
OPTIN = 'ZAPRET2_STAGE2_REAL_BOOT_SYSHOOK'
HOOKS = {
    phase: Path('/usr/local/etc/rc.syshook.d') / phase /
           '21-zapret2-stage2-native-boot-observer'
    for phase in ('start', 'stop')
}
PRODUCT = {
    phase: Path('/usr/local/etc/rc.syshook.d') / phase / '20-zapret'
    for phase in ('start', 'stop')
}


def load_active():
    source = HERE / 'stage2-opnsense-real-native-active-service.py'
    spec = importlib.util.spec_from_file_location('native_boot_active', source)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


active = load_active()
Refusal = active.Refusal
need = active.need


def digest(data):
    return hashlib.sha256(data).hexdigest()


def boot_id():
    result = active.cmd(['/sbin/sysctl', '-n', 'kern.boottime'], timeout=20)
    need(result.returncode == 0 and result.stdout.strip() and
         not result.stderr.strip(), 'KERNEL_BOOT_ID_UNAVAILABLE')
    return result.stdout.strip()


def observe_bytes(phase):
    """Passive witness AFTER the real 20-zapret hook, never drives lifecycle."""
    name = str(ROOT / phase)
    return (
        '#!/bin/sh\n'
        '# Disposable CI observer: never starts/stops Zapret2.\n'
        'umask 077\n'
        '/sbin/sysctl -n kern.boottime > "' + name + '.bootid" 2>&1\n'
        '/usr/local/sbin/configctl zapret status > "' + name + '.status" 2> "' +
        name + '.status.err"\n'
        'printf "%s\\n" "$?" > "' + name + '.status.rc"\n'
        '/sbin/ipfw -q list > "' + name + '.ipfw" 2> "' +
        name + '.ipfw.err"\n'
        'printf "%s\\n" "$?" > "' + name + '.ipfw.rc"\n'
        'if [ -f /var/run/dvtws2.pid ]; then\n'
        '    /bin/cat /var/run/dvtws2.pid > "' + name + '.pid"\n'
        'else\n'
        '    printf "ABSENT\\n" > "' + name + '.pid"\n'
        'fi\n'
        'printf "COMPLETE\\n" > "' + name + '.done"\n'
        'exit 0\n'
    ).encode('ascii')


def regular_bytes(path, mode):
    st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and not path.is_symlink() and
         st.st_uid == 0 and stat.S_IMODE(st.st_mode) == mode,
         'DISPOSABLE_BOOT_FILE_NOT_OWNED:' + str(path))
    return path.read_bytes()


def write_owned(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(path, mode)
    dirfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def gate():
    need(os.environ.get(OPTIN) == '1' and os.environ.get('GITHUB_ACTIONS') ==
         'true', 'EXPLICIT_DISPOSABLE_BOOT_CI_OPTIN_REQUIRED')
    engine_sha = active.guest_preflight()
    for phase, installed in PRODUCT.items():
        source = active.ROOT / 'src/etc/rc.syshook.d' / phase / '20-zapret'
        need(installed.is_file() and not installed.is_symlink() and
             installed.read_bytes() == source.read_bytes(),
             'INSTALLED_' + phase.upper() + '_SYSHOOK_NOT_SOURCE')
        owner = active.required(['pkg', 'which', '-q', str(installed)],
                                'INSTALLED_SYSHOOK_OWNER_UNAVAILABLE')
        need(owner in (active.PACKAGE,
                       active.PACKAGE + '-' + active.qualified_revision()),
             'INSTALLED_' + phase.upper() + '_SYSHOOK_NOT_PKG_OWNED')
    return engine_sha


def config_except_model(raw):
    """Compare everything EXCEPT root revision and the test Zapret model."""
    import xml.etree.ElementTree as ET
    root = copy.deepcopy(ET.fromstring(raw))
    need(root.tag == 'opnsense' and len(root.findall('revision')) <= 1,
         'TEST_ONLY_CONFIG_ROOT_UNTRUSTED')
    for revision in root.findall('revision'):
        root.remove(revision)
    models = root.findall('./OPNsense')
    need(len(models) == 1 and len(models[0].findall('Zapret')) == 1,
         'TEST_ONLY_MODEL_SCOPE_AMBIGUOUS')
    models[0].remove(models[0].find('Zapret'))
    def clean(node):
        if not (node.text or '').strip():
            node.text = None
        node.tail = None
        for child in node:
            clean(child)
    clean(root)
    return ET.tostring(root, encoding='utf-8')


def protected_model_values(raw):
    """Pin configured runtime leaves; do not accept altered test Strategies."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(raw)
    matches = root.findall('./OPNsense/Zapret')
    need(len(matches) == 1, 'TEST_ONLY_ZAPRET_MODEL_AMBIGUOUS')
    model = matches[0]
    paths = (
        'general/enabled', 'general/waninterface',
        'general/ports', 'general/divertport',
        'strategy/trafficargs', 'strategy/extraargs',
        'hostlist/mode',
    )
    out = {}
    for path in paths:
        nodes = model.findall(path)
        need(len(nodes) == 1, 'TEST_ONLY_REQUIRED_FIELD_MISSING:' + path)
        out[path] = nodes[0].text or ''
    need(out['general/enabled'] == '1' and
         out['general/waninterface'] == 'lo0' and
         out['general/ports'] == '65431' and
         out['general/divertport'] == '989' and
         out['hostlist/mode'] == 'all' and
         '--filter-tcp=65431' in out['strategy/trafficargs'],
         'TEST_ONLY_STRATEGIES_NOT_APPROVED_LOOPBACK_PROFILE')
    return out


def canonicalize_disposable_model():
    """Normalize an artificial test XML via the INSTALLED native MVC model.

    A real saved GUI model has a version and schema defaults. The fixture
    produced by Stage0 hand-written ET.SubElement does not. At OS boot the
    OPNsense migration may fill defaults and alter that artificial subtree.
    Prepare through the official MVC model before the baseline, but refuse
    any change in prior user leaf values or unrelated Config contents.
    """
    model_path = Path('/usr/local/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml')
    source_path = active.ROOT / 'src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml'
    need(model_path.is_file() and not model_path.is_symlink() and
         model_path.read_bytes() == source_path.read_bytes(),
         'INSTALLED_MVC_MODEL_NOT_SOURCE_IDENTICAL')
    import xml.etree.ElementTree as ET
    model_definition = ET.fromstring(source_path.read_bytes())
    expected_version = model_definition.findtext('version')
    need(expected_version == '2.0.0',
         'UNQUALIFIED_MVC_MODEL_VERSION')
    initial = active.CONFIG.read_bytes()
    baseline = protected_model_values(initial)
    outside = config_except_model(initial)
    # No arbitrary calls from tests on the owner's hardware. gate() has
    # already verified source SHA, disposable CI VM, package and loopback.
    php = r"""require_once('script/load_phalcon.php');
$config = \OPNsense\Core\Config::getInstance();
$config->lock();
try {
    $model = new \OPNsense\Zapret\Zapret();
    // OPNsense BaseModel::toXML uses the CURRENT model version, not the
    // schema version. Its native default migration must run on our
    // unversioned synthetic Stage0 Config before serialization.
    if ($model->getVersion() !== '2.0.0' &&
        !$model->runMigrations()) {
        throw new \RuntimeException('MVC default migration refused');
    }
    if (!$model->serializeToConfig(false, true)) {
        throw new \RuntimeException('MVC model serialization refused');
    }
    $config->save(['description'=>'Disposable native boot fixture normalization']);
} catch (\Throwable $error) {
    fwrite(STDERR, "DISPOSABLE_MVC_FIXTURE_NORMALIZATION_REFUSED\n");
    exit(69);
} finally {
    $config->unlock();
}
"""
    result = active.cmd(['/usr/local/bin/php', '-r', php], timeout=60)
    need(result.returncode == 0,
         'DISPOSABLE_NATIVE_MVC_MODEL_NORMALIZATION_FAILED:rc=' +
         str(result.returncode))
    new = active.CONFIG.read_bytes()
    need(config_except_model(new) == outside,
         'MVC_NORMALIZATION_CHANGED_FOREIGN_CONFIG')
    need(protected_model_values(new) == baseline,
         'MVC_NORMALIZATION_CHANGED_STRATEGIES_VALUES')
    root = ET.fromstring(new)
    need(root.find('./OPNsense/Zapret').get('version') == expected_version,
         'MVC_MODEL_VERSION_NOT_SERIALIZED')
    return {'schema_version': expected_version, 'strategies_values_preserved': True,
            'foreign_config_preserved': True}


def prepare():
    engine_sha = gate()
    need(not ROOT.exists() and not ROOT.is_symlink(),
         'DISPOSABLE_WITNESS_SCOPE_ALREADY_EXISTS')
    for hook in HOOKS.values():
        need(not hook.exists() and not hook.is_symlink(),
             'FOREIGN_OR_STALE_OBSERVER_HOOK_PRESENT')
    running = active.live_state(engine_sha)
    model_witness = canonicalize_disposable_model()
    need(active.live_state(engine_sha) == running,
         'MVC_FIXTURE_NORMALIZATION_CHANGED_RUNNING_ENGINE_OR_IPFW')
    now = boot_id()
    need(now, 'PREBOOT_KERNEL_UNOBSERVABLE')
    ROOT.mkdir(mode=0o700)
    need(ROOT.stat().st_uid == 0 and
         stat.S_IMODE(ROOT.stat().st_mode) == 0o700,
         'DISPOSABLE_SCOPE_PERMISSIONS_NOT_RESTRICTED')
    record = {
        'schema': 1, 'project_sha': os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
        'installed_package': active.qualified_revision(),
        'prepared_boot_id': now, 'old_pid': running['pid'],
        'engine_sha256': engine_sha,
        'config_sha256': digest(active.CONFIG.read_bytes()),
        'source_start_sha256': digest(PRODUCT['start'].read_bytes()),
        'source_stop_sha256': digest(PRODUCT['stop'].read_bytes()),
        'loopback_only': True,
    }
    # Only the disposable root-owned VM keeps this synthetic Config fixture.
    # Never print its values into public Actions logs.
    write_owned(ROOT / 'preboot-config.xml', active.CONFIG.read_bytes(), 0o600)
    write_owned(RECORD, (json.dumps(record, sort_keys=True) + '\n').encode(),
                0o600)
    for phase, hook in HOOKS.items():
        write_owned(hook, observe_bytes(phase), 0o755)
        need(regular_bytes(hook, 0o755) == observe_bytes(phase),
             'OBSERVER_HOOK_CREATED_WRONG_BYTES:' + phase)
    return {'schema': 1, 'status': 'PREPARED_REAL_NATIVE_SYSHOOK_REBOOT',
            'source_sha': record['project_sha'], 'old_pid': running['pid'],
            'preboot_id': now, 'real_kernel_boot_after_shutdown_pending': True,
            'passive_start_and_stop_observers': True,
            'native_mvc_fixture_normalization': model_witness,
            'owner_appliance_modified': False}


def observed(phase):
    hook = HOOKS[phase]
    need(regular_bytes(hook, 0o755) == observe_bytes(phase),
         'TEST_ONLY_OBSERVER_CHANGED:' + phase)
    fields = {}
    for suffix in ('bootid', 'status', 'status.rc', 'ipfw', 'ipfw.rc', 'pid'):
        path = ROOT / (phase + '.' + suffix)
        value = regular_bytes(path, 0o600).decode('utf-8').strip()
        need(value != '' or suffix == 'ipfw',
             'OBSERVER_OUTPUT_EMPTY:' + phase + '.' + suffix)
        fields[suffix] = value
    need(regular_bytes(ROOT / (phase + '.done'), 0o600).decode().strip() ==
         'COMPLETE', 'PASSIVE_OBSERVER_INCOMPLETE:' + phase)
    need(fields['status.rc'] == '0' and fields['ipfw.rc'] == '0',
         'OBSERVER_CONFIGCTL_OR_IPFW_QUERY_FAILED:' + phase)
    return fields


def rule_lines(text):
    return [line for line in text.splitlines()
            if re.match(r'^190(?:0\d|10)\s', line)]



def redacted_semantic_leaf_delta(before, after):
    """Classify actual XML differences with tag IDs only; NEVER leak values.

    Keep unknown/user-defined tag names hashed, not merely their values.
    Both XML samples are disposable guest files and are never copied to CI.
    """
    import xml.etree.ElementTree as ET

    def normalized(raw):
        root = ET.fromstring(raw)
        if root.tag != 'opnsense':
            raise Refusal('BOOT_CONFIG_ROOT_UNQUALIFIED')
        for revision in root.findall('revision'):
            root.remove(revision)
        def clean(node):
            if not (node.text or '').strip():
                node.text = None
            node.tail = None
            for child in node:
                clean(child)
        clean(root)
        return root

    a, b = normalized(before), normalized(after)
    known = {'opnsense', 'OPNsense', 'Zapret', 'general', 'strategy',
             'enabled', 'revision', 'system', 'firmware', 'plugins',
             'waninterface', 'ports', 'divertport', 'trafficargs'}
    def label(tag):
        if tag in known:
            return tag
        return 'tag_' + hashlib.sha256(tag.encode('utf-8')).hexdigest()[:12]

    changes = []
    def walk(old, new, path):
        if len(changes) >= 32:
            return
        if old.tag != new.tag:
            changes.append({'path': path, 'kind': 'tag_reordered_or_replaced'})
            return
        if old.text != new.text:
            changes.append({'path': path, 'kind': 'text'})
        if old.attrib != new.attrib:
            changes.append({'path': path, 'kind': 'attribute'})
        if len(old) != len(new):
            changes.append({'path': path, 'kind': 'children_count'})
        for i, (left, right) in enumerate(zip(old, new)):
            # A tag fingerprint is safe even if this is an arbitrary
            # user-selected XML key, and the ordinal reveals no value.
            walk(left, right, path + '/' + label(left.tag) + ':' + str(i))

    walk(a, b, 'opnsense')
    left = a.find('./OPNsense/Zapret')
    right = b.find('./OPNsense/Zapret')
    return {'changed_paths': changes,
            'changes_truncated': len(changes) >= 32,
            'zapret_tree_identical': (
                left is not None and right is not None and
                ET.tostring(left) == ET.tostring(right)),
            'xml_parsed': True}


def prove_transition(record, stop, start, post, new_boot):
    need(new_boot != record['prepared_boot_id'] and
         stop['bootid'] == record['prepared_boot_id'] and
         start['bootid'] == new_boot,
         'GENUINE_DISTINCT_KERNEL_SHUTDOWN_AND_START_NOT_PROVEN')
    need(stop['status'] == 'zapret is not running' and
         stop['pid'] == 'ABSENT' and not rule_lines(stop['ipfw']),
         'REAL_SHUTDOWN_STOP_HOOK_LEFT_OWNED_RUNTIME')
    need(start['pid'].isdecimal() and int(start['pid']) > 1 and
         int(start['pid']) == post['pid'] and
         int(start['pid']) != record['old_pid'] and
         start['status'] == 'zapret is running as pid ' + start['pid'],
         'REAL_BOOT_START_DID_NOT_RESTORE_NEW_ENGINE_PID')
    lines = rule_lines(start['ipfw'])
    need(len(lines) == 1 and lines[0].startswith('19000 ') and
         'divert 989' in lines[0] and 'lo0' in lines[0] and
         '65431' in lines[0], 'BOOT_SYSHOOK_DID_NOT_RESTORE_LOOPBACK_IPFW')
    need(lines == post['rules'],
         'POSTBOOT_LIVE_RULE_DIFFERS_FROM_START_OBSERVER')
    return True


def verify():
    engine_sha = gate()
    need(ROOT.is_dir() and not ROOT.is_symlink() and
         ROOT.stat().st_uid == 0 and
         stat.S_IMODE(ROOT.stat().st_mode) == 0o700,
         'DISPOSABLE_WITNESS_SCOPE_UNTRUSTED')
    record = json.loads(regular_bytes(RECORD, 0o600).decode('utf-8'))
    need(record.get('schema') == 1 and
         record.get('project_sha') == os.environ['ZAPRET2_NATIVE_PROJECT_SHA'] and
         record.get('installed_package') == active.qualified_revision() and
         record.get('engine_sha256') == engine_sha and
         record.get('loopback_only') is True,
         'PREPARED_GUEST_PROJECT_AND_ENGINE_IDENTITY_MISMATCH')
    for phase in PRODUCT:
        need(digest(PRODUCT[phase].read_bytes()) ==
             record['source_' + phase + '_sha256'],
             'PRODUCTION_SYSHOOK_CHANGED_AFTER_REBOOT:' + phase)
    stop, start = observed('stop'), observed('start')
    new_boot = boot_id()
    new_running = active.live_state(engine_sha)
    prove_transition(record, stop, start, new_running, new_boot)
    prior_config = regular_bytes(ROOT / 'preboot-config.xml', 0o600)
    need(digest(prior_config) == record['config_sha256'],
         'PREBOOT_CONFIG_FORENSIC_BYTES_CHANGED')
    after_config = active.CONFIG.read_bytes()
    byte_identical = digest(after_config) == record['config_sha256']
    if not byte_identical:
        # Reuse the already-qualified native pkg Config contract: a genuine
        # OPNsense boot can rewrite <revision> and insignificant XML spacing.
        # Every other saved XML value/order/attribute must remain identical.
        # Never emit the actual saved Config bytes or user values in CI.
        source = HERE / 'stage2-opnsense-real-native-stopped-upgrade.py'
        spec = importlib.util.spec_from_file_location('native_boot_config_policy', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.normalized_config(prior_config) != module.normalized_config(after_config):
            raise Refusal('SAVED_CONFIG_SEMANTIC_CHANGE_ACROSS_REAL_BOOT:' +
                          json.dumps(redacted_semantic_leaf_delta(
                              prior_config, after_config), sort_keys=True))
    # Remove ONLY own exact test observers. Never remove production syshooks.
    for phase, hook in HOOKS.items():
        need(regular_bytes(hook, 0o755) == observe_bytes(phase),
             'REFUSE_TO_REMOVE_FOREIGN_OBSERVER:' + phase)
        hook.unlink()
    need(all(not p.exists() and not p.is_symlink()
             for p in HOOKS.values()),
         'DISPOSABLE_BOOT_OBSERVER_CLEANUP_FAILED')
    return {
        'schema': 1, 'status': 'PASS_REAL_INSTALLED_NATIVE_SYSHOOK_REBOOT',
        'observed_distinct_kernel_boot': True,
        'shutdown_stop_syshook_observed': True,
        'start_syshook_observed_without_explicit_service_start': True,
        'new_real_engine_pid': new_running['pid'],
        'single_loopback_rule_restored': True,
        'saved_config_semantic_values_preserved': True,
        'raw_config_bytes_unchanged': byte_identical,
        'only_revision_metadata_or_formatting_rewrite_permitted': True,
        'test_only_observers_removed': True,
        'common_strategies_voice_tested': False,
        'unexpected_power_loss_tested': False,
        'web_gui_click_tested': False,
        'owner_appliance_modified': False,
    }


def main():
    try:
        need(len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'verify'),
             'PREPARE_OR_VERIFY_REQUIRED')
        value = prepare() if sys.argv[1] == 'prepare' else verify()
    except (Refusal, OSError, KeyError, ValueError, UnicodeError,
            json.JSONDecodeError) as exc:
        print('STAGE2_REAL_BOOT=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_REAL_BOOT=' + json.dumps(value, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
