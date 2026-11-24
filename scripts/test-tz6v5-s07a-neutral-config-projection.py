#!/usr/bin/env python3
"""S07a source-level RED/GREEN acceptance, not installed native proof."""
import builtins
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from config_projection_opnsense import (xml_snapshot, registered_ids, read_saved,
                                      NativeProjectionError)
from neutral_config_model import (project, ConfigModelError, SourceId)

ROWS = b'''registry_build()
{
    printf 'HOSTLIST\\tyoutube\\t--hostlist\\thostlist.youtube\\t1\\n'
    printf 'HOSTLIST\\tauto\\t--hostlist\\thostlist.auto\\t0\\n'
    printf 'IPSET\\ttelegram\\t--ipset\\tipset.telegram\\t1\\n'
}
registry_validate()
{
}
'''

def xml(general='<enabled>0</enabled><waninterface>opt0</waninterface><divertport>989</divertport><ports>80,443</ports><autorestart>off</autorestart>', hostlist='<mode>auto</mode><userdomains></userdomains>', voice='', strategy=''):
    return ('<opnsense><other>untouched</other><OPNsense><Zapret>'
            f'<general>{general}</general><hostlist>{hostlist}</hostlist>'
            f'<voice>{voice}</voice><strategy>{strategy}</strategy>'
            '</Zapret></OPNsense></opnsense>').encode()

class S07Pure(unittest.TestCase):
    def source(self, raw=None):
        return project(xml_snapshot(xml() if raw is None else raw), registered_ids(ROWS))

    def test_saved_wan_is_not_guessed_from_Opt_Tun_and_model_immutable(self):
        out = self.source()
        self.assertEqual((out.enabled, out.saved_wan, out.wan_state), (False, 'opt0', 'NEEDS_NATIVE_RESOLUTION'))
        self.assertEqual((out.divert_port, out.ports, out.target_mode), (989, (80,443), 'auto'))
        self.assertEqual(tuple((x.kind,x.name,x.content_required) for x in out.registered_sources),
                         (('HOSTLIST','youtube',True),('HOSTLIST','auto',False),('IPSET','telegram',True)))
        self.assertEqual(out.authorization, 'NONE')
        self.assertFalse(out.physical_transition_allowed)
        self.assertIsNone(out.voice[0].enabled)
        self.assertFalse(next(x for x in out.list_fields if x.key == 'userdomains').empty is None)
        self.assertTrue(next(x for x in out.list_fields if x.key == 'userdomains').empty)
        self.assertFalse(next(x for x in out.list_fields if x.key == 'youtubedomains').present)
        with self.assertRaises(FrozenInstanceError):
            out.enabled = True
        self.assertNotIn('secret', repr(self.source(xml(voice='<telegram><args>secret</args></telegram>'))))

    def test_missing_vs_empty_and_valid_tunnel_selection(self):
        for val, state in (('', 'EMPTY'), ('tun0', 'NEEDS_NATIVE_RESOLUTION'), ('opt123', 'NEEDS_NATIVE_RESOLUTION')):
            out = self.source(xml(general=f'<enabled>1</enabled><waninterface>{val}</waninterface>'))
            self.assertEqual((out.saved_wan, out.wan_state), (val, state))
        self.assertEqual(self.source(xml(general='<enabled>0</enabled>')).wan_state, 'MISSING')
        self.assertIsNone(self.source(xml(general='')).enabled)

    def test_invalid_scalar_and_duplicate_fail_closed(self):
        bads = [xml(general='<enabled>2</enabled>'),
                xml(general='<divertport>0</divertport>'),
                xml(general='<ports>80,,443</ports>'),
                xml(general='<autorestart>everysecond</autorestart>'),
                xml(general='<waninterface>opt0;rm</waninterface>'),
                xml(hostlist='<mode>learn</mode>'),
                xml(voice='<telegram><enabled>true</enabled></telegram>'),
                xml(general='<enabled>0</enabled><enabled>1</enabled>'),
                xml(hostlist='<random>unknown</random>'),
                xml(voice='<telegram><args>abc</args></telegram><telegram/>'),
                xml().replace(b'</Zapret>', b'</Zapret><Zapret/>'),
                b'<!DOCTYPE foo><opnsense/>',
                b'<opnsense><OPNsense><Zapret/></OPNsense><OPNsense/></opnsense>',
                b'<opnsense><Zapret/></opnsense>']
        for bad in bads:
            with self.subTest(bad=bad[:80]):
                with self.assertRaises((ConfigModelError, NativeProjectionError)):
                    self.source(bad)

    def test_registry_source_reuses_real_declared_rows_and_refuses_unknown(self):
        self.assertEqual(len(registered_ids(ROWS)), 3)
        for bad in (ROWS.replace(b'HOSTLIST', b'MYSTERY', 1),
                    ROWS.replace(b'--ipset', b'--hostlist'),
                    ROWS.replace(b'ipset.telegram', b'hostlist.telegram'),
                    ROWS.replace(b'1\\n\'\n}', b'1\\n\'\n    printf \'HOSTLIST\\tyoutube\\t--hostlist\\thostlist.youtube\\t1\\n\'\n}')):
            with self.subTest(bad=bad[-100:]):
                with self.assertRaises((ConfigModelError, NativeProjectionError)):
                    registered_ids(bad)

    def test_untrusted_registry_object_rejected(self):
        tree = xml_snapshot(xml())
        for registry in (tuple(), (SourceId('HOSTLIST','youtube','ipset.youtube',True),),
                         (SourceId('HOSTLIST','youtube','hostlist.youtube',True),)*2):
            with self.assertRaises(ConfigModelError):
                project(tree, registry)

    def test_canonical_registry_source_has_exact_current_ids(self):
        source = (BACKEND / "registry.sh").read_bytes()
        ids = registered_ids(source)
        self.assertEqual([(i.kind, i.name) for i in ids],
                         [("HOSTLIST", "youtube"), ("HOSTLIST", "user"), ("HOSTLIST", "auto"),
                          ("IPSET", "telegram"), ("IPSET", "discord"), ("IPSET", "x"),
                          ("IPSET", "sip"), ("IPSET", "custom")])

    def test_existing_bounded_reader_supplies_bytes_without_writes(self):
        calls = []
        def reader(path, limit, owner):
            calls.append((str(path), limit, owner))
            return xml() if str(path) == '/conf/config.xml' else ROWS
        with patch.object(builtins, 'open', side_effect=AssertionError('write/open')), \
             patch('subprocess.Popen', side_effect=AssertionError('spawn')), \
             patch('os.open', side_effect=AssertionError('side effect')):
            out = read_saved(reader=reader, config_owner=123, config=Path('/conf/config.xml'),
                             registry=Path('/fixed/registry.sh'))
        self.assertFalse(out.physical_transition_allowed)
        self.assertEqual(calls, [('/conf/config.xml', 16777216, 123),
                                 ('/fixed/registry.sh', 131072, 0)])

if __name__ == '__main__':
    unittest.main(verbosity=2)
