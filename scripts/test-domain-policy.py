#!/usr/bin/env python3
"""Unit and CLI checks for the single Python domain policy."""
from __future__ import annotations
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'src' / 'opnsense' / 'scripts' / 'OPNsense' / 'Zapret' / 'backend' / 'domain_policy.py'
SPEC = importlib.util.spec_from_file_location('domain_policy', MODULE)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class DomainPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.psl = policy.PublicSuffixList.load()

    def plan(self, events, *, manual=None, automatic=None, exclude=''):
        return policy.plan_auto_additions(
            [{'hostname': host, 'hostlist': origin} for host, origin in events],
            {'youtube': '', 'user': '', 'auto': '', **(manual or {})},
            automatic or {}, exclude, psl=self.psl)

    def test_auto_roots_respect_icann_private_and_depth(self):
        psl = policy.PublicSuffixList.load()
        for hostname, root in {
            'video.example.co.uk': 'example.co.uk',
            'a.b.c.user.github.io': 'user.github.io',
            'a.b.c.example.com': 'example.com',
        }.items():
            with self.subTest(hostname=hostname):
                self.assertEqual(psl.registrable_domain(hostname), root)

    def test_psl_wildcard_exception_and_private_wildcard(self):
        for host, root in {
            'a.b.ck': 'a.b.ck', 'www.ck': 'www.ck', 'x.www.ck': 'www.ck',
            'a.city.kawasaki.jp': 'city.kawasaki.jp',
            'x.tenant.appspot.com': 'tenant.appspot.com',
            'x.user.github.io': 'user.github.io',
            'A.B.Example.COM.': 'example.com',
        }.items():
            with self.subTest(host=host):
                self.assertEqual(self.psl.registrable_domain(host), root)

    def test_strict_idna_retains_internationalized_identity(self):
        for host, root in {
            'видео.пример.рф': 'xn--e1afmkfd.xn--p1ai',
            'www.faß.de': 'xn--fa-hia.de',
            'www.xn--fa-hia.de': 'xn--fa-hia.de',
            'www.食狮.公司.cn': 'xn--85x722f.xn--55qx5d.cn',
        }.items():
            with self.subTest(host=host):
                self.assertEqual(self.psl.registrable_domain(host), root)
        self.assertEqual(policy.normalize('!^ПРИМЕР.РФ', 'user')['normalized'],
                         '!^xn--e1afmkfd.xn--p1ai')

    def test_invalid_host_public_suffix_unknown_and_bounds(self):
        for host in ['', '.', 'co.uk', 'github.io', 'x.ck', 'ck', 'com',
                     'a.not-a-delegated-tld', 'localhost', '127.0.0.1',
                     '127.000.0.1', '2001:db8::1', '[::1]', '!example.com',
                     '^example.com', '*.example.com', 'https://example.com',
                     'example.com/path', 'a..example.com', 'bad_.com',
                     'a\x00.com', ' a.com', 'a.com ', 'a\u200d.com',
                     '💩.com', 'xn--a.com', 'a。com', '-bad.com',
                     'a'*64 + '.com', '.'.join(['a'*63]*4) + '.com']:
            with self.subTest(host=host), self.assertRaises(policy.AutoDomainPolicyError):
                self.psl.registrable_domain(host)
        longest = '.'.join(['a'*63, 'b'*63, 'c'*63, 'd'*57, 'com'])
        self.assertEqual(len(longest), 253)
        self.assertEqual(self.psl.registrable_domain(longest), 'd'*57 + '.com')

    def test_psl_missing_corrupt_and_unqualified_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'public_suffix_list.dat'
            with self.assertRaisesRegex(policy.AutoDomainPolicyError, 'psl_unavailable'):
                policy.PublicSuffixList.load(target)
            target.write_bytes(policy.PSL_PATH.read_bytes())
            metadata = json.loads(policy.PSL_PATH.with_suffix('.json').read_text())
            target.with_suffix('.json').write_text(json.dumps(metadata))
            self.assertEqual(policy.PublicSuffixList.load(target).sha256, self.psl.sha256)
            target.write_bytes(target.read_bytes() + b'\n')
            with self.assertRaisesRegex(policy.AutoDomainPolicyError, 'psl_hash_mismatch'):
                policy.PublicSuffixList.load(target)
            metadata['source'] = 'https://unqualified.invalid/list'
            target.with_suffix('.json').write_text(json.dumps(metadata))
            with self.assertRaisesRegex(policy.AutoDomainPolicyError, 'invalid_psl_metadata'):
                policy.PublicSuffixList.load(target)
        for data in [b'com\n',
                     b'// ===BEGIN ICANN DOMAINS===\ncom\n// ===END ICANN DOMAINS===\n',
                     b'// ===BEGIN ICANN DOMAINS===\n*.*.com\n// ===END ICANN DOMAINS===\n']:
            with self.subTest(data=data), self.assertRaises(policy.AutoDomainPolicyError):
                policy.PublicSuffixList(data, hashlib.sha256(data).hexdigest())

    def test_missing_idna_is_explicit_and_not_stdlib_fallback(self):
        with patch.dict(sys.modules, {'idna': None}):
            with self.assertRaisesRegex(policy.AutoDomainPolicyError, 'idna_unavailable'):
                self.psl.registrable_domain('www.faß.de')

    def test_multi_event_dedup_known_unknown_and_unmapped(self):
        got = self.plan([('a.example.co.uk', 'youtube'), ('b.c.example.co.uk', 'youtube'),
                         ('x.user.github.io', None), ('www.other.com', 'stale-list')])
        self.assertEqual(got['additions'], {
            'youtube': ['example.co.uk'], 'auto': ['other.com', 'user.github.io']})
        self.assertEqual(got['unprocessed'], [])
        self.assertFalse(any('^' in item for rows in got['additions'].values() for item in rows))

    def test_global_and_any_list_broad_exclusions(self):
        for where in ['youtube', 'user', 'auto', 'external']:
            got = self.plan([('a.b.example.com', 'youtube')],
                            manual={where: '!example.com'})
            self.assertEqual(got['additions'], {}, where)
            self.assertEqual(got['excluded'][0]['code'], 'hostlist_exclusion')
        self.assertEqual(self.plan([('www.example.com', 'youtube')],
                                  automatic={'user': '!example.com'})['additions'], {})
        got = self.plan([('x.example.com', 'youtube')], exclude='example.com')
        self.assertEqual(got['excluded'][0]['code'], 'global_exclusion')
        self.assertEqual(self.plan([('badexample.com', 'youtube')],
                                  manual={'user': '!example.com'})['additions'],
                         {'youtube': ['badexample.com']})

    def test_exact_exclusions_check_original_and_candidate_without_spreading(self):
        for prefix in ['!^', '^!']:
            manual = {'user': prefix + 'video.example.com'}
            self.assertEqual(self.plan([('video.example.com', 'youtube')], manual=manual)['additions'], {})
            for sibling in ['other.example.com', 'x.video.example.com']:
                self.assertEqual(self.plan([(sibling, 'youtube')], manual=manual)['additions'],
                                 {'youtube': ['example.com']})
            self.assertEqual(self.plan([('video.example.com', 'youtube')],
                                      manual={'user': prefix + 'example.com'})['additions'], {})
        # Excluded observations cannot invent an attribution conflict for others.
        got = self.plan([('video.example.com', 'user'), ('other.example.com', 'youtube')],
                        manual={'auto': '!^video.example.com'})
        self.assertEqual(got['additions'], {'youtube': ['example.com']})

    def test_manual_coverage_is_destination_local_and_preserves_flags(self):
        for entry in ['example.com', '^example.com']:
            self.assertEqual(self.plan([('www.example.com', 'youtube')],
                                      manual={'youtube': entry})['additions'], {})
        self.assertEqual(self.plan([('www.example.com', 'youtube')],
                                  manual={'user': 'example.com'})['additions'],
                         {'youtube': ['example.com']})
        manual = {'user': '!^voice.example.com\n^manual.net'}
        original = dict(manual)
        self.plan([('www.example.com', 'youtube')], manual=manual)
        self.assertEqual(manual, original)

    def test_conflicting_origins_same_root_always_go_shared(self):
        events = [('a.example.com', 'youtube'), ('b.example.com', 'user')]
        a, b = self.plan(events), self.plan(events[::-1])
        self.assertEqual(a, b)
        self.assertEqual(a['additions'], {'auto': ['example.com']})
        self.assertEqual(a['routes'][0]['reason'], 'ambiguous')
        self.assertEqual(self.plan([('a.example.com', 'youtube'), ('b.example.com', None)])['additions'],
                         {'auto': ['example.com']})

    def test_cross_batch_conflict_relocates_only_proven_owned_rows(self):
        got = self.plan([('b.example.com', 'user')],
                        manual={'youtube': '^manual.net'},
                        automatic={'youtube': 'example.com\n^exact.org\n!blocked.org'})
        self.assertEqual(got['removals'], {'youtube': ['example.com']})
        self.assertEqual(got['additions'], {'auto': ['example.com']})
        got = self.plan([('b.example.com', 'user')], automatic={'auto': 'example.com'})
        self.assertEqual((got['additions'], got['removals']), ({}, {}))

    def test_retry_idempotency_and_normal_deletion_then_rediscovery(self):
        events = [('a.example.com', 'youtube'), ('b.example.com', 'youtube')]
        first = self.plan(events)
        second = self.plan(events, automatic={'youtube': '\n'.join(first['additions']['youtube'])})
        self.assertEqual((second['additions'], second['removals']), ({}, {}))
        self.assertEqual(self.plan(events)['additions'], first['additions'])

    def test_invalid_events_remain_diagnosable_unprocessed(self):
        got = self.plan([('co.uk', None), ('www.example.com', 'youtube'), ('127.0.0.1', 'user')])
        self.assertEqual(got['result'], 'partial')
        self.assertEqual(got['additions'], {'youtube': ['example.com']})
        self.assertEqual(got['unprocessed'], [{'index': 0, 'code': 'public_suffix'},
                                             {'index': 2, 'code': 'ip_literal'}])

    def test_incomplete_or_broken_snapshot_cannot_bypass_exclusions(self):
        for hostlists, automatic, exclude in [({}, {}, ''), ({'auto': ''}, {'missing': ''}, ''),
                                             ({'auto': 'bad_.com'}, {}, ''),
                                             ({'auto': ''}, {}, '!example.com')]:
            with self.subTest(hostlists=hostlists), self.assertRaises(policy.AutoDomainPolicyError):
                policy.plan_auto_additions([], hostlists, automatic, exclude, psl=self.psl)

    def test_auto_cli_uses_packaged_psl_without_writes(self):
        payload = {'discoveries': [{'hostname': 'x.user.github.io', 'hostlist': None}],
                   'hostlists': {'auto': ''}, 'automatic': {}, 'global_exclude': ''}
        result = subprocess.run([sys.executable, str(MODULE), 'auto-plan'],
                                input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['additions'], {'auto': ['user.github.io']})
        status = subprocess.run([sys.executable, str(MODULE), 'psl-status'], text=True, capture_output=True)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)['sha256'], self.psl.sha256)

    def test_ordinary_and_legacy(self):
        for src, want in {
            ' EXAMPLE.COM  ': 'example.com',
            'https://Example.com/path?q=1': 'example.com',
            'HTTP://YouTube.com/': 'youtube.com',
            '*.Example.com': 'example.com',
            'Example.COM,': 'example.com',
            '': '',
        }.items():
            with self.subTest(src=src):
                self.assertEqual(policy.normalize(src, 'youtube')['normalized'], want)

    def test_modifiers(self):
        for src, want in {
            '!Example.com': '!example.com',
            '^Example.com': '^example.com',
            '!^Example.com': '!^example.com',
            '^!Example.com': '!^example.com',
            '!https://Example.com/path': '!example.com',
        }.items():
            with self.subTest(src=src):
                self.assertEqual(policy.normalize(src, 'user')['normalized'], want)
        result = policy.normalize('!^Example.com\n^!example.com', 'user')
        self.assertEqual((result['normalized'], result['duplicates']), ('!^example.com', 1))

    def test_invalid(self):
        for src, code, line in [
            ('example.com\n!example.com', 'conflicting_modifiers', 2),
            ('^example.com\nexample.com', 'conflicting_modifiers', 2),
            ('!!example.com', 'repeated_modifier', 1),
            ('^^example.com', 'repeated_modifier', 1),
            ('!^!example.com', 'repeated_modifier', 1),
            ('!', 'missing_domain', 1),
            ('^*.example.com', 'modifier_with_wildcard', 1),
            ('127.0.0.1', 'ip_in_domain_list', 1),
            ('example..com', 'invalid_domain', 1),
            ('bad-.example.com', 'invalid_domain', 1),
            ('bad_.com', 'invalid_domain', 1),
        ]:
            with self.subTest(src=src):
                with self.assertRaises(policy.DomainPolicyError) as context:
                    policy.normalize(src, 'youtube')
                self.assertEqual((context.exception.code, context.exception.line), (code, line))

    def test_exclude_is_separate(self):
        self.assertEqual(policy.normalize('Example.COM', 'exclude')['normalized'], 'example.com')
        for src in ('!example.com', '^example.com', '^!example.com'):
            with self.subTest(src=src):
                with self.assertRaises(policy.DomainPolicyError) as context:
                    policy.normalize(src, 'exclude')
                self.assertEqual(context.exception.code, 'modifiers_not_allowed')

    def test_deduplication(self):
        got = policy.normalize('Example.com\nexample.com\nOther.com', 'user')
        self.assertEqual(got['normalized'], 'example.com\nother.com')
        self.assertEqual((got['duplicates'], got['entry_count'], got['changed']), (1, 2, 2))

    def test_inspect_and_single_are_consistent_and_atomic(self):
        with tempfile.TemporaryDirectory(prefix='domain-policy-') as tmp:
            root = Path(tmp)
            source, target = root / 'input.txt', root / 'out.txt'
            source.write_text('^!Example.com\nPlain.com\n', encoding='utf-8')
            cmd = [sys.executable, str(MODULE)]
            result = subprocess.run(cmd + ['inspect'], input=json.dumps({
                'kind': 'youtube', 'text': source.read_text()
            }), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = json.loads(result.stdout)['normalized'] + '\n'
            written = subprocess.run(cmd + ['single', 'youtube', str(source), str(target)],
                                     capture_output=True, text=True)
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertEqual(target.read_text(), expected)
            source.write_text('Plain.com\n!Plain.com\n')
            rejected = subprocess.run(cmd + ['single', 'youtube', str(source), str(target)],
                                      capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn('line 2:', rejected.stderr)
            self.assertEqual(target.read_text(), expected)
            self.assertFalse(list(root.glob('.domain-policy-*')))
            invalid = subprocess.run(cmd + ['inspect'], input=json.dumps({
                'kind': 'youtube', 'text': source.read_text()
            }), text=True, capture_output=True)
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(json.loads(invalid.stdout)['error']['code'], 'conflicting_modifiers')




class TZ6v2EditorPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.psl = policy.PublicSuffixList.load()

    def found(self, source, text):
        return policy.normalize_found_editor(text, source, psl=self.psl)

    def test_found_sources_collapse_sort_and_dedupe_roots(self):
        for source in ("youtube", "user", "auto"):
            with self.subTest(source=source):
                found = self.found(source,
                    "New.Example.ORG\nVIDEO.EXAMPLE.COM\nexample.org\n")
                self.assertEqual(found["normalized"], "example.com\nexample.org")
                self.assertEqual((found["entry_count"], found["duplicates"]), (2, 1))
                self.assertEqual(self.found(source, "")["normalized"], "")

    def test_idna_and_private_psl_without_suffix_guess(self):
        normalized = self.found("youtube",
            "x.user.github.io\nвидео.пример.рф\nwww.faß.de\n")["normalized"]
        self.assertEqual(normalized,
            "user.github.io\nxn--e1afmkfd.xn--p1ai\nxn--fa-hia.de")
        for bad, reason in [
            ("example.unknownsuffix", "unknown_suffix"),
            ("com", "public_suffix"),
            ("127.0.0.1", "ip_literal"),
            ("https://example.com", "invalid_host"),
        ]:
            with self.subTest(bad=bad), self.assertRaises(policy.FoundEditorPolicyError) as exc:
                self.found("user", "ok.example.com\n" + bad)
            self.assertEqual(exc.exception.evidence(),
                {"source": "user", "line": 2, "code": reason})

    def test_all_found_editors_forbid_manual_flags(self):
        for source in ("youtube", "user", "auto"):
            for invalid in ("!example.com", "^example.com", "!^example.com"):
                with self.subTest(source=source, invalid=invalid):
                    with self.assertRaises(policy.FoundEditorPolicyError) as exc:
                        self.found(source, "ok.example.com\n" + invalid)
                    self.assertEqual(exc.exception.evidence(),
                        {"source": source, "line": 2, "code": "modifiers_not_allowed"})

    def test_manual_only_changed_sort_by_full_flags(self):
        draft = "z.example.com\n^test.example.net\n!^example.com\n!test.example.org"
        self.assertEqual(policy.normalize(draft, "user")["normalized"].splitlines()[0],
                         "z.example.com")  # untouched native path keeps order
        self.assertEqual(policy.normalize_manual_editor(draft, "user")["normalized"].splitlines(),
            ["!^example.com", "!test.example.org", "^test.example.net", "z.example.com"])
        self.assertEqual(policy.normalize_manual_editor("!Example.COM", "youtube")["normalized"],
                         "!example.com")

    def test_native_cli_positive_and_line_error_not_raw_text(self):
        cmd = [sys.executable, str(MODULE)]
        valid = subprocess.run(cmd + ["found-inspect"], text=True, capture_output=True,
            input=json.dumps({"source": "auto", "text": "new.example.org\nvideo.example.com"}))
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["normalized"], "example.com\nexample.org")
        bad = subprocess.run(cmd + ["found-inspect"], text=True, capture_output=True,
            input=json.dumps({"source": "user", "text": "ok.example.com\n!bad.example.org"}))
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)["error"],
            {"source": "user", "line": 2, "code": "modifiers_not_allowed"})
        self.assertNotIn("bad.example.org", bad.stdout)
        manual = subprocess.run(cmd + ["manual-edit"], text=True, capture_output=True,
            input=json.dumps({"kind": "youtube", "text": "z.example.com\n!example.org"}))
        self.assertEqual(manual.returncode, 0, manual.stderr)
        self.assertEqual(json.loads(manual.stdout)["normalized"], "!example.org\nz.example.com")

if __name__ == '__main__':
    unittest.main()
