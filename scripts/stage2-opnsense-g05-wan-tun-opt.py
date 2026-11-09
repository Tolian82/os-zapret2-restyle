#!/usr/bin/env python3
"""G05 S2: assigned OPT -> real FreeBSD tun kernel interface as WAN.

Disposable OPNsense guest ONLY. Native Config adds one temporary OPT
assignment, normal authenticated HTTPS Apply binds real Voice/IPFW to tun,
and the same API restores the original WAN before removing the fixture.
No installed product file, production WAN resolver or real VPN is modified.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OPTIN = "ZAPRET2_G05_TUN_OPT_NATIVE"
STATUS = "PASS_G05_ASSIGNED_TUN_OPT_NATIVE_HTTPS_APPLY"
OPT = "opt0"
IP = "198.18.254.1"
PEER = "198.18.254.2"

# Test-only native OPNsense Config interface assignment, not Zapret Config.
# The exact XML node is absent before the test and removed after success.
PHP_ASSIGN = r'''
require_once("config.inc");
require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$root = $c->object();
if (!isset($root->interfaces)) { exit(71); }
$op = $argv[1] ?? '';
$node = $root->interfaces;
if ($op === 'add') {
    if (isset($node->opt0)) { exit(72); }
    $tun = $argv[2] ?? '';
    if (!preg_match('/^tun[0-9]{1,4}$/D', $tun)) { exit(73); }
    $opt = $node->addChild('opt0');
    $opt->addChild('if', $tun);
    $opt->addChild('enable', '1');
    $opt->addChild('descr', 'G05 disposable TUN fixture');
} elseif ($op === 'remove') {
    if (!isset($node->opt0) ||
        (string)($node->opt0->descr ?? '') !== 'G05 disposable TUN fixture' ||
        (string)($node->opt0->if ?? '') !== ($argv[2] ?? '')) { exit(74); }
    unset($node->opt0);
} elseif ($op === 'absent') {
    if (isset($node->opt0)) { exit(75); }
    exit(0);
} else { exit(76); }
$c->save();
'''


class Refusal(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        'g05_opt_' + name.replace('-', '_').replace('.', '_'), HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd(args, *, timeout=45):
    p = subprocess.run(args, capture_output=True, text=True,
                       timeout=timeout, check=False)
    return p


def good(args, what):
    p = cmd(args)
    need(p.returncode == 0, what + ':rc=' + str(p.returncode))
    return p.stdout.strip()


def php(mode, device=''):
    good(['/usr/local/bin/php', '-r', PHP_ASSIGN, mode, device],
         'G05_OPT_NATIVE_CONFIG_' + mode.upper())


def resolver(value):
    # The installed resolver, not a fork of its production mapping code.
    shell = ('common_error() { printf "%s\\n" "$*" >&2; }; '
             '. /usr/local/opnsense/scripts/OPNsense/Zapret/backend/config.sh; '
             'config_resolve_interface "$1"')
    return cmd(['/bin/sh', '-c', shell, 'g05-native-opt', value])


def opt_form(value, baseline):
    need(value in (OPT, 'lo0') and baseline in ('192.0.2.42', '192.0.2.42/32'),
         'G05_OPT_UNTRUSTED_HTTP_FORM')
    return [('zapret[sync][telegramips_baseline]', baseline),
            ('zapret[general][waninterface]', value)]


def addr_count(device):
    text = good(['/sbin/ifconfig', device], 'G05_OPT_IFCONFIG')
    return len(re.findall(r'^\s*inet\s+', text, flags=re.M))


def exact_config_except_fixture(before, after, boot):
    """All unrelated native Config, including Zapret model, is preserved."""
    def without_opt(raw):
        root = ET.fromstring(raw)
        interfaces = root.find('./interfaces')
        need(interfaces is not None, 'G05_OPT_NATIVE_INTERFACES_MISSING')
        opt = interfaces.find(OPT)
        if opt is not None:
            need(opt.findtext('descr') == 'G05 disposable TUN fixture',
                 'G05_OPT_FOREIGN_ASSIGNMENT_FOUND')
            interfaces.remove(opt)
        return ET.tostring(root, encoding='utf-8')
    need(boot.config_except_model(without_opt(before)) ==
         boot.config_except_model(without_opt(after)),
         'G05_OPT_FOREIGN_NATIVE_CONFIG_CHANGED')


def execute():
    for key in ('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK',
                'ZAPRET2_NATIVE_BUILD_CI',
                'ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST',
                'ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE',
                'ZAPRET2_STAGE2_REAL_ACTIVE_SERVICE',
                'ZAPRET2_STAGE2_REAL_COMMON_VOICE',
                'ZAPRET2_STAGE2_REAL_VOICE_HTTP',
                'ZAPRET2_G05_RUNNING_WAN_NATIVE',
                'ZAPRET2_G05_ROLLBACK_NATIVE', OPTIN):
        need(os.environ.get(key) == '1', 'G05_OPT_DISPOSABLE_OPTIN:' + key)
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.uname().sysname == 'FreeBSD' and os.geteuid() == 0 and
         Path('/usr/local/opnsense').is_dir(),
         'G05_OPT_REAL_DISPOSABLE_OPNSENSE_REQUIRED')
    active = load('stage2-opnsense-real-native-active-service.py')
    common = load('stage2-opnsense-real-native-shared-voice.py')
    voice = load('stage2-opnsense-real-native-voice-http.py')
    g05 = load('stage2-opnsense-g05-wan-running.py')
    save = load('stage2-opnsense-g05-wan-save.py')
    boot = load('stage2-opnsense-real-native-boot-syshook.py')
    engine_sha = active.guest_preflight()
    web = voice.GuestHttps()
    voice.login(web)
    before_model, baseline = g05.read_model(web)
    need(g05.logical_wan(before_model, save) == 'lo0' and
         before_model['voice']['telegram']['enabled'] == '1',
         'G05_OPT_BASELINE_NOT_ORIGINAL_RUNNING_VOICE')
    before_xml = active.CONFIG.read_bytes()
    old = g05.shared_owner(active, common, engine_sha, 'lo0')
    php('absent')
    # Discover and create a fresh tun clone; never adopt an existing device.
    created = good(['/sbin/ifconfig', 'tun', 'create'], 'G05_OPT_TUN_CREATE')
    need(re.fullmatch(r'tun[0-9]{1,4}', created) is not None,
         'G05_OPT_UNTRUSTED_NEW_TUN_NAME')
    device = created
    good(['/sbin/ifconfig', device, 'up'], 'G05_OPT_TUN_UP')
    need(addr_count(device) == 0, 'G05_OPT_CLONE_UNEXPECTED_IPV4')
    # No assignment at all: the existing resolver must refuse logical OPT.
    need(resolver(OPT).returncode != 0, 'G05_OPT_UNASSIGNED_ACCEPTED')
    php('add', device)
    need(resolver(OPT).stdout.strip() == device and
         resolver(OPT).returncode == 0,
         'G05_OPT_ASSIGNED_IPV4LESS_TUN_NOT_RESOLVED')
    # Real IPv4 on the P2P tunnel; no route or external VPN peer is invented.
    good(['/sbin/ifconfig', device, 'inet', IP, PEER, 'netmask', '255.255.255.252'],
         'G05_OPT_TUN_IPV4_ASSIGN')
    need(addr_count(device) == 1, 'G05_OPT_TUN_IPV4_NOT_PRESENT')
    mapped = resolver(OPT)
    need(mapped.returncode == 0 and mapped.stdout.strip() == device,
         'G05_OPT_IPV4_ASSIGNED_TUN_NOT_RESOLVED')
    with_fixture = active.CONFIG.read_bytes()
    exact_config_except_fixture(before_xml, with_fixture, boot)
    # InterfaceField returns native dynamic option lists. Adding opt0 changes
    # those lists without changing any saved Zapret model field, so snapshot
    # the current full model AFTER the temporary OPNsense assignment.
    fixture_model, fixture_baseline = g05.read_model(web)
    need(g05.logical_wan(fixture_model, save) == 'lo0' and
         fixture_baseline == baseline, 'G05_OPT_FIXTURE_CHANGED_NATIVE_ZAPRET')
    # Full original authenticated Strategies Apply; no test-specific HTTP API.
    applied = web.api('POST', '/api/zapret/settings/apply',
                      opt_form(OPT, fixture_baseline))
    need(applied.get('result') == 'saved' and applied.get('applied') is True,
         'G05_OPT_FULL_HTTPS_APPLY_REFUSED:' + str(applied.get('message', ''))[:140])
    on, new_baseline = g05.read_model(web)
    need(g05.logical_wan(on, save) == OPT, 'G05_OPT_MODEL_WAN_NOT_SAVED')
    g05.preserved_other_model(fixture_model, on)
    opt_owner = g05.shared_owner(active, common, engine_sha, device)
    need(opt_owner['id'] != old['id'] and opt_owner['pid'] != old['pid'],
         'G05_OPT_ENGINE_NOT_REPLACED')
    exact_config_except_fixture(before_xml, active.CONFIG.read_bytes(), boot)
    # Return to original WAN before removing the disposable OPT assignment.
    reversed_apply = web.api('POST', '/api/zapret/settings/apply',
                             opt_form('lo0', new_baseline))
    need(reversed_apply.get('result') == 'saved' and
         reversed_apply.get('applied') is True, 'G05_OPT_REVERSE_APPLY_REFUSED')
    after, _ = g05.read_model(web)
    voice.attest_complete_native_model(fixture_model, after)
    last = g05.shared_owner(active, common, engine_sha, 'lo0')
    need(last['id'] != opt_owner['id'] and last['pid'] != opt_owner['pid'] and
         last['rules'] == old['rules'], 'G05_OPT_REVERSE_VOICE_IPFW_NOT_RESTORED')
    exact_config_except_fixture(before_xml, active.CONFIG.read_bytes(), boot)
    # A configured OPT whose TUN device disappeared MUST refuse a new Apply.
    good(['/sbin/ifconfig', device, 'destroy'], 'G05_OPT_TUN_DESTROY')
    missing = resolver(OPT)
    need(missing.returncode != 0 and not missing.stdout.strip(),
         'G05_OPT_DISCONNECTED_TUN_ACCEPTED')
    old_xml = active.CONFIG.read_bytes()
    failed = web.api('POST', '/api/zapret/settings/apply',
                     opt_form(OPT, new_baseline))
    need(failed.get('result') == 'failed' and
         failed.get('applied') is not True and
         failed.get('requires_review') is not True,
         'G05_OPT_DISCONNECTED_HTTPS_WAN_NOT_REJECTED')
    need(active.CONFIG.read_bytes() == old_xml and
         g05.shared_owner(active, common, engine_sha, 'lo0') == last,
         'G05_OPT_DISCONNECTED_MUTATED_ACTIVE_OWNER')
    php('remove', device)
    final_xml = active.CONFIG.read_bytes()
    need(boot.config_except_model(before_xml) ==
         boot.config_except_model(final_xml),
         'G05_OPT_FIXTURE_NOT_REMOVED_CLEANLY')
    final_model, _ = g05.read_model(web)
    voice.attest_complete_native_model(before_model, final_model)
    need(g05.shared_owner(active, common, engine_sha, 'lo0') == last,
         'G05_OPT_FINAL_RUNTIME_CHANGED')
    return {
        'status': STATUS, 'source_sha': os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
        'assigned_logical_opt': OPT, 'real_tun_kernel_device': device,
        'ipv4less_opt_resolution': True, 'ipv4_assigned_opt_resolution': True,
        'native_authenticated_full_apply': True,
        'voice_ipfw_xmit_tun_verified': True,
        'authenticated_reverse_apply': True,
        'missing_tun_rejected_unchanged': True,
        'native_assignment_fixture_cleaned': True,
        'physical_owner_browser_tested': False,
        'real_vpn_tunnel_traffic_tested': False,
        'policy_ipsec_tested': False,
    }


def self_test():
    assert re.fullmatch(r'tun[0-9]{1,4}', 'tun0')
    assert re.fullmatch(r'tun[0-9]{1,4}', 'tun42')
    assert not re.fullmatch(r'tun[0-9]{1,4}', 'vtnet1')
    assert not re.fullmatch(r'tun[0-9]{1,4}', 'tun0;rm')
    assert PHP_ASSIGN.count("$node->addChild('opt0')") == 1
    assert "unset($node->opt0)" in PHP_ASSIGN
    assert opt_form('opt0', '192.0.2.42/32')[1][1] == 'opt0'
    for bad in ('vtnet1', 'tun0', 'unassigned0'):
        try:
            opt_form(bad, '192.0.2.42/32')
        except Refusal:
            pass
        else:
            raise AssertionError('untrusted interface accepted in test form')
    assert OPT == 'opt0' and IP.startswith('198.18.')
    print('PASS: G05 disposable OPT/TUN native assignment, exact scope and teardown fixture')


def main():
    if sys.argv[1:] == ['--self-test']:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ['run'], 'G05_OPT_EXPECTED_RUN_OR_SELF_TEST')
        report = execute()
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            ET.ParseError, subprocess.TimeoutExpired) as exc:
        print('G05_TUN_OPT_NATIVE=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('G05_TUN_OPT_NATIVE=' + json.dumps(report, sort_keys=True))
    return 0

if __name__ == '__main__':
    sys.exit(main())
