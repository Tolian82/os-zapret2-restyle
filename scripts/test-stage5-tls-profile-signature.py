#!/usr/bin/env python3
"""No-network production-parser and fail-closed Lua action signature contract."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

signature = load('stage5_tls_signature', ROOT/'stage5-tls-profile-signature.py')

class Native:
    @staticmethod
    def segments(text):
        out=[]
        for row in text.split('--new'):
            if row.strip():out.append(row.strip().split())
        return out
    @staticmethod
    def templates_and_imports(rows):
        templates={}
        kinds=[]
        for row in rows:
            selected=[x.partition('=')[2] for x in row if x.startswith('--template=')]
            if selected:
                templates[selected[0]]=row
                kinds.append('template')
            else:kinds.append('profile')
        return templates,kinds
    @staticmethod
    def inherited(row, templates):
        output=list(row)
        for x in row:
            if x.startswith('--import='):
                name=x.partition('=')[2]
                if name not in templates:raise ValueError('unknown native import')
                output += templates[name]
        return output
    @staticmethod
    def visible(row):return list(row)

class SignatureTests(unittest.TestCase):
    def test_fake_split_header_and_independent_fingerprints(self):
        text=('--filter-tcp=443 --lua-desync=fake:blob=private:ttl=2'
              ' --new --filter-tcp=443 --lua-desync=fakedsplit:pos=host'
              ' --new --filter-tcp=443 --lua-desync=multisplit:pos=2'
              ' --new --filter-tcp=443 --lua-desync=pktmod:ip_ttl=23')
        rows=signature.candidate_signatures(text,Native,[1,2,3,4],4)
        self.assertEqual([['FAKE'],['FAKE_SPLIT'],['SPLIT'],['HEADER_MUTATION']],
                         [x['lua_action_families'] for x in rows])
        self.assertEqual(len({x['effective_profile_sha256'] for x in rows}),4)
        self.assertNotIn('private',str(rows))
        self.assertTrue(all(x['qualification']=='CONFIGURED_CANDIDATE_ONLY' for x in rows))

    def test_template_inheritance_and_ordinals(self):
        argv=('--template=tls_base --lua-desync=fake:blob=secret'
              ' --new=name1 --import=tls_base --filter-tcp=443'
              ' --new --filter-tcp=443 --lua-desync=tcpseg:pos=2')
        result=signature.candidate_signatures(argv,Native,[1,2],2)
        self.assertEqual(['FAKE'],result[0]['lua_action_families'])
        self.assertEqual(['SPLIT'],result[1]['lua_action_families'])
        self.assertEqual([1,2],[x['profile_index'] for x in result])

    def test_real_production_parser_when_checkout_available(self):
        # Exact CI checkout exercises global_exclusions, not only stub selectors.
        backend = ROOT.parent/'src/opnsense/scripts/OPNsense/Zapret/backend'
        if not backend.is_dir():
            return  # local isolated helper preflight has no repository checkout
        sys.path.insert(0,str(backend))
        import global_exclusions as native
        argv=('--template=base --lua-desync=fake:blob=private'
              ' --new=named --import=base --filter-tcp=443'
              ' --new --filter-tcp=443 --lua-desync=fakedsplit:pos=host')
        rows=signature.candidate_signatures(argv,native,[1,2],2)
        self.assertEqual(['FAKE'],rows[0]['lua_action_families'])
        self.assertEqual(['FAKE_SPLIT'],rows[1]['lua_action_families'])
        self.assertEqual([1,2],[x['profile_index'] for x in rows])

    def test_custom_unrecognized_not_promoted(self):
        result=signature.candidate_signatures('--lua-desync=secret_custom:param=private',Native,[1],1)
        self.assertEqual(['OTHER_OR_CUSTOM'],result[0]['lua_action_families'])
        self.assertNotIn('secret_custom',str(result))

    def test_none_and_multiple_actions(self):
        result=signature.candidate_signatures('--lua-desync=fake:blob=x --lua-desync=multisplit:pos=2 --new --filter-tcp=443',Native,[1,2],2)
        self.assertEqual(['FAKE','SPLIT'],result[0]['lua_action_families'])
        self.assertEqual(['NONE'],result[1]['lua_action_families'])
        self.assertEqual(2,result[0]['lua_action_count'])

    def test_invalid_action_token_fails_closed(self):
        for argv in ('--lua-desync','--lua-desync=','--lua-desync=bad/route:foo'):
            with self.subTest(argv=argv),self.assertRaises(signature.SignatureError):
                signature.candidate_signatures(argv,Native,[1],1)

    def test_no_selected_profile_no_disclosure(self):
        self.assertEqual([],signature.candidate_signatures('--lua-desync=fake:blob=secret',Native,[],1))

    def test_invalid_counts_and_indexes_fail_closed(self):
        for nums,total in (([0],1),([2],1),([1,1],1),([1],2),([True],1)):
            with self.subTest(nums=nums,total=total),self.assertRaises(signature.SignatureError):
                signature.candidate_signatures('--lua-desync=fake',Native,nums,total)

    def test_cannot_use_selected_action_as_runtime_or_a07_proof(self):
        report=str(signature.candidate_signatures('--lua-desync=fake:blob=secret',Native,[1],1))
        self.assertNotIn('selected',report)
        self.assertNotIn('VERIFIED',report)
        self.assertNotIn('A07',report)

if __name__=='__main__':unittest.main(verbosity=2)
