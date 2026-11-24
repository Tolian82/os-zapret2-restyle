#!/usr/bin/env python3
"""S08a exact native original Target Mode shell vs pure target precompiler.

Tests read production source; no service, native Config, FD9, engine or IPFW.
The subprocesses invoke original shell ONLY on disposable test-owned files.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/backend'
if not BACKEND.is_dir():
    BACKEND = ROOT / 'backend'  # local S0 synthetic compatibility only
sys.path.insert(0, str(BACKEND))

import profile_policy
from neutral_config_model import RequestedConfig, SourceId
from neutral_target_compiler import (parse_original_policy, compile_target_profiles,
                                     TargetCompileError)

POLICY = BACKEND / 'target_mode.sh'
REGISTRY = BACKEND / 'registry.sh'
STRATEGY = (b'--filter-tcp=443\n--filter-l7=tls\n--lua-desync=fake\n'
            b'--new\n--filter-udp=443\n--lua-desync=fake\n')
EXPLICIT = (b'--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n'
            b'--new\n--filter-udp=443\n<IPSET:telegram>\n--lua-desync=fake\n')
MIXED = (b'--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n'
         b'--new\n--filter-tcp=80\n--lua-desync=fake\n')


def config(mode='auto'):
    return RequestedConfig(
        enabled=False, saved_wan='opt0', wan_state='NEEDS_NATIVE_RESOLUTION',
        divert_port=989, ports=(80, 443), autorestart='off', target_mode=mode,
        lab_enablequic=False, voice=(), list_fields=(), legacy_strategy=(),
        registered_sources=(
            SourceId('HOSTLIST','youtube','hostlist.youtube',True),
            SourceId('HOSTLIST','user','hostlist.user',True),
            SourceId('HOSTLIST','auto','hostlist.auto',False),
            SourceId('IPSET','telegram','ipset.telegram',True),
            SourceId('IPSET','discord','ipset.discord',True),
            SourceId('IPSET','x','ipset.x',True),
            SourceId('IPSET','sip','ipset.sip',True),
            SourceId('IPSET','custom','ipset.custom',True)))


def source_policy():
    # Real repo tests always use the original source, never an imitation.
    return parse_original_policy(POLICY.read_bytes())


class S08aOriginalParity(unittest.TestCase):
    def test_same_native_default_rows_for_list_and_auto_no_implicit_learner(self):
        defaults = source_policy()
        rows = {entry.mode: entry.defaults for entry in defaults.modes}
        self.assertEqual(rows['all'], ())
        self.assertEqual(rows['list'], rows['auto'])
        self.assertEqual(rows['auto'], (
            ('HOSTLIST', 'youtube'), ('IPSET', 'telegram'), ('HOSTLIST','user')))
        self.assertNotIn(('HOSTLIST','auto'), rows['auto'])

    def test_all_modes_and_explicit_targets_against_original_shell(self):
        if not REGISTRY.is_file() or not POLICY.is_file():
            self.skipTest('local synthetic S0: exact original shell parity only in GitHub CI')
        policy = source_policy()
        for mode in ('all','list','auto'):
            for label, strategy in (('default',STRATEGY), ('explicit',EXPLICIT),
                                    ('mixed',MIXED), ('empty', b'')):
                with self.subTest(mode=mode,case=label):
                    out = compile_target_profiles(config(mode), strategy, policy)
                    self.assertEqual(out.status,'SOURCE_TARGETS_ONLY')
                    self.assertEqual(out.authorization,'NONE')
                    self.assertIs(out.physical_transition_allowed, False)
                    originals = profile_policy.split_profiles(strategy)
                    self.assertEqual(len(out.profiles), len(originals))
                    with tempfile.TemporaryDirectory(prefix='s08a-native-policy-') as tmp:
                        directory = Path(tmp)
                        for idx, original in enumerate(originals,1):
                            (directory / f'profile-{idx}.conf').write_bytes(original)
                        script = '''set -eu
common_error() { printf '%s\\n' "$*" >&2; }
. "$1"
. "$2"
registry_build "$3/registry.tsv"
target_mode_apply_all "$3" "$4" "$5" "$3/registry.tsv"
'''
                        proc = subprocess.run(
                            ['/bin/sh','-c',script,'s08',str(REGISTRY),str(POLICY),
                             str(directory),str(len(originals)),mode],
                            text=True,capture_output=True,timeout=20,check=False)
                        self.assertEqual(proc.returncode,0,'Original native Target Mode refused')
                        for idx, projection in enumerate(out.profiles,1):
                            native = (directory / f'profile-{idx}.conf').read_bytes()
                            self.assertEqual(projection.content, native,
                                             f'{mode}/{label}: changed original targeting')
                            self.assertEqual(projection.normalized,
                                tuple(profile_policy.expand_profiles([native])))
                            self.assertEqual(projection.source_number, idx)

    def test_explicit_wins_and_stays_in_original_order(self):
        policy=source_policy()
        out=compile_target_profiles(config('auto'), EXPLICIT, policy)
        self.assertEqual(out.profiles[0].authored, (('HOSTLIST','user'),))
        self.assertEqual(out.profiles[1].authored, (('IPSET','telegram'),))
        self.assertEqual(out.profiles[0].content,
                         profile_policy.split_profiles(EXPLICIT)[0])
        self.assertNotIn(b'<HOSTLIST:youtube>',out.profiles[0].content)
        self.assertEqual(out.profiles[0].source_number,1)
        self.assertEqual(out.profiles[1].source_number,2)
        with self.assertRaises(FrozenInstanceError):
            out.mode='list'

    def test_unknown_ids_and_unqualified_inputs_refuse(self):
        policy=source_policy()
        for wrong in (b'--filter-tcp=443\n<HOSTLIST:ghost>\n',
                      b'--filter-tcp=443\n<IPSET:unknown>\n',
                      b'--filter-tcp=443\n<HOSTLIST:user\n',
                      b'--filter-tcp=443\n--new\n', b'\0bad'):
            with self.subTest(wrong=wrong):
                with self.assertRaises(TargetCompileError):
                    compile_target_profiles(config(),wrong,policy)
        for broken in (replace(config(),target_mode=None),
                       replace(config(),target_mode='learn'),
                       replace(config(),authorization='OWNER'),
                       replace(config(),physical_transition_allowed=True),
                       replace(config(),registered_sources=()),
                       replace(config(),registered_sources=(SourceId('HOSTLIST','user','hostlist.user',True),))):
            with self.subTest(broken=broken.target_mode):
                with self.assertRaises(TargetCompileError):
                    compile_target_profiles(broken,STRATEGY,policy)
        with self.assertRaises(TargetCompileError):
            compile_target_profiles(config(),b'x'*300000,policy)

    def test_original_policy_untrusted_mutations_refuse(self):
        src=POLICY.read_bytes()
        for tampered in (
            src.replace(b'printf \'HOSTLIST\\tyoutube',b'printf \'IPSET\\tyoutube',1),
            src.replace(b'printf \'HOSTLIST\\tyoutube',b'printf \'HOSTLIST\\tghost',1),
            src.replace(b'list)',b'list-old)',1),
            src.replace(b"printf 'IPSET\\ttelegram\\n'",b'echo untrusted',1),
            b'not shell',
        ):
            with self.subTest(tampered=hash(tampered)):
                try:
                    maybe=parse_original_policy(tampered)
                except TargetCompileError:
                    continue
                with self.assertRaises(TargetCompileError):
                    compile_target_profiles(config(),STRATEGY,maybe)


if __name__=='__main__':
    unittest.main(verbosity=2)
