#!/usr/bin/env python3
"""Fail-closed offline contracts for read-only historical old-owner screening."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

PRODUCT = Path(__file__).resolve().parent.parent / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(PRODUCT))
import native_pkg_old_owner as m


def completed(data=b'', rc=0, err=b''):
    return SimpleNamespace(returncode=rc, stdout=data, stderr=err)


class PredecessorScreenContracts(unittest.TestCase):
    def test_installed_pkgdb_exactly_one(self):
        self.assertEqual(m.installed_manifest(b'{"name":"os-zapret2-restyle"}')['name'], m.NAME)
        for invalid in (b'garbage', b'[]', b'[{},{}]', b'null', b'14'):
            with self.subTest(invalid=invalid), self.assertRaises(m.OwnerRefusal):
                m.installed_manifest(invalid)

    def test_four_historical_hooks_must_match_byte_for_byte(self):
        scripts={p:'#!/bin/sh\nexit 0\n' for p in m.PHASES}
        manifest={'name':m.NAME,'version':'0.6.2_1',
                  'arch':'freebsd:15:x86:64', 'origin':'local/os-zapret2-restyle',
                  'abi':'FreeBSD:15:amd64','scripts':scripts}
        def query(argv,**_):
            if argv[1]=='-tf':
                return completed(b'usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh\n')
            if argv[-1]=='+MANIFEST':
                return completed(json.dumps(manifest).encode())
            return completed(b'# historical service')
        with patch.object(m,'read_command',side_effect=query):
            self.assertEqual(m.check_four_hooks(Path('/tmp/old.pkg'),manifest,'0.6.2_1'),
                             b'# historical service')
            mutated=json.loads(json.dumps(manifest))
            mutated['scripts']['pre-deinstall']='#!/bin/sh\nexit 1\n'
            with self.assertRaisesRegex(m.OwnerRefusal,'HOOK_BODY_MISMATCH'):
                m.check_four_hooks(Path('/tmp/old.pkg'),mutated,'0.6.2_1')
            mutated['scripts']=dict(scripts, other='#!/bin/sh\n')
            with self.assertRaisesRegex(m.OwnerRefusal,'HOOKS_UNQUALIFIED'):
                m.check_four_hooks(Path('/tmp/old.pkg'),mutated,'0.6.2_1')

    def test_cold_kernel_process_and_journal_negatives(self):
        def query(argv,**_):
            if argv[0]=='/bin/ps':
                return completed(b'PID old process\n')
            if argv[0]=='/sbin/kldstat':
                return completed(rc=1)
            return completed(rc=71,err=b'Protocol not available')
        with patch.object(m,'MARKERS',()), patch.object(m,'read_command',side_effect=query):
            self.assertEqual(m.cold_screen(),'COLD_NO_JOURNAL_PROCESS_OR_LOADED_IPFW')
        with patch.object(m,'MARKERS',()), patch.object(m,'read_command',side_effect=lambda argv,**kw:
                completed(b'/usr/local/sbin/dvtws2\n') if argv[0]=='/bin/ps' else query(argv,**kw)):
            with self.assertRaisesRegex(m.OwnerRefusal,'PROCESS_OR_UNKNOWN'):
                m.cold_screen()
        with patch.object(m,'MARKERS',()), patch.object(m,'read_command',side_effect=lambda argv,**kw:
                completed(rc=0) if argv[:4]==['/sbin/kldstat','-q','-m','ipfw'] else query(argv,**kw)):
            with self.assertRaisesRegex(m.OwnerRefusal,'NOT_PROVEN_COLD'):
                m.cold_screen()

    def test_foreign_journal_symlink_refuses_without_deleting(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/'marker'
            marker.symlink_to(Path(folder)/'missing')
            with patch.object(m,'MARKERS',(marker,)):
                with self.assertRaisesRegex(m.OwnerRefusal,'JOURNAL_MARKER_OR_PIDFILE'):
                    m.cold_screen()
            self.assertTrue(marker.is_symlink())

    def test_positive_held_fd9_read_only_screen_has_no_pkg_authority(self):
        version='0.6.2_1'
        baseline=b'{"name":"os-zapret2-restyle","version":"0.6.2_1"}'
        calls=[]
        def query(argv,**_):
            calls.append(tuple(argv))
            if argv[1]=='info':
                return completed(baseline)
            if argv[1]=='which':
                return completed((m.NAME+'-'+version+'\n').encode())
            self.fail('unexpected query: '+repr(argv))
        def read_bytes(path, **_):
            return (b'#!/bin/sh\nold',0o755) if path==m.SERVICE else (b'<config/>',0o600)
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m.os,'uname',return_value=SimpleNamespace(sysname='FreeBSD',machine='amd64')),\
             patch.object(m.native_pkg_handoff,'verify_original_lock') as fd9,\
             patch.object(m,'read_command',side_effect=query),\
             patch.object(m,'check_four_hooks',return_value=b'#!/bin/sh\nold'),\
             patch.object(m,'regular_root_bytes',side_effect=read_bytes),\
             patch.object(m,'cold_screen',return_value='COLD'):
            result=m.inspect_stopped(Path('/root/old.pkg'),version,987)
        self.assertEqual(result['status'],'READ_ONLY_STOPPED_PREDECESSOR_SCREENED')
        self.assertFalse(result['old_owner_qualified'])
        self.assertTrue(result['config_readonly_snapshot_only'])
        self.assertFalse(result['config_ownership_authorized'])
        self.assertFalse(result['pkg_invoked'])
        self.assertFalse(result['lh08_ac11_accepted'])
        self.assertEqual(fd9.call_count,2)
        self.assertEqual([c[1] for c in calls],['info','which','info'])

    def test_pkgdb_drift_refuses(self):
        n=[0]
        def query(argv,**_):
            if argv[1]=='info':
                n[0]+=1
                return completed(b'{"name":"old"}' if n[0]==1 else b'{"name":"new"}')
            return completed((m.NAME+'-0.6.2_1').encode())
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m.os,'uname',return_value=SimpleNamespace(sysname='FreeBSD',machine='amd64')),\
             patch.object(m.native_pkg_handoff,'verify_original_lock'),\
             patch.object(m,'read_command',side_effect=query),\
             patch.object(m,'check_four_hooks',return_value=b'service'),\
             patch.object(m,'regular_root_bytes',side_effect=lambda p,**kw:(b'service',0o755) if p==m.SERVICE else (b'config',0o600)),\
             patch.object(m,'cold_screen',return_value='COLD'):
            with self.assertRaisesRegex(m.OwnerRefusal,'PKGDB_CHANGED'):
                m.inspect_stopped(Path('/root/old.pkg'),'0.6.2_1',22)

    def test_read_only_command_timeout_is_refusal(self):
        import subprocess
        with patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired('pkg',1)):
            with self.assertRaisesRegex(m.OwnerRefusal,'QUERY_UNAVAILABLE'):
                m.read_command(['/usr/sbin/pkg','info'])

    def test_no_native_mutation_is_reachable(self):
        source=(PRODUCT/'native_pkg_old_owner.py').read_text()
        for forbidden in ("'pkg', 'add'", "'pkg', 'upgrade'", "'pkg', 'delete'",'os.system(', 'os.execvp(',
                          'ipfw add', 'ipfw delete', 'os.unlink(', 'os.rename('):
            self.assertNotIn(forbidden,source)
        self.assertIn("'old_owner_qualified': False",source)
        self.assertNotIn('call_status(',source)


if __name__ == '__main__':
    unittest.main()
