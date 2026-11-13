#!/usr/bin/env python3
"""P2k 13 bounded actual-filesystem debug/raw cursor candidate tests, no worker."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
import sys

BACKEND = (Path(__file__).resolve().parents[1] /
           "src/opnsense/scripts/OPNsense/Zapret/backend")
sys.path.insert(0, str(BACKEND))

from auto_detect_fd import OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_debug_window import (
    Cursor, DebugWindowRefused, empty_epoch, propose_window,
    run_native_debug_collector,
)


class DebugWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='p2k-debug-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.base.chmod(0o700)
        self.raw = self.base / 'inbox.txt'
        self.debug = self.base / 'debug.log'
        self.raw.write_bytes(b'')
        self.debug.write_bytes(b'')
        self.proof = GenerationProof(
            OwnerToken(4321, 'Fri Nov 13 10:00:00 2026', '/usr/local/sbin/dvtws2'),
            'a' * 32, 'a' * 32, 'b' * 64, str(self.raw), str(self.debug), 2,
            ((0, 'unknown-native-default', None),
             (1, 'known-hostlist', 'youtube'), (2, 'observer', None)))
        self.cursor = empty_epoch(self.proof, owner_uid=os.geteuid())

    def add(self, host='unknown.p2k.invalid', profile=2, path=None):
        path = str(self.raw) if path is None else path
        self.debug.write_bytes(self.debug.read_bytes() + (
            '2026-11-13 13:15:30 : ' + host + ' : profile ' + str(profile) +
            ' (tail) : client 127.0.0.1:5325 : proto http : adding to ' + path + '\n'
        ).encode('ascii'))
        return host.encode('ascii') + b'\n'

    def window(self, raw):
        return propose_window(self.proof, self.cursor, raw, owner_uid=os.geteuid())

    def rejects(self, raw, message):
        with self.assertRaisesRegex(DebugWindowRefused, message):
            self.window(raw)

    def test_matches_real_upstream_positive_and_returns_offset_candidate(self):
        raw = self.add()
        w = self.window(raw)
        self.assertEqual(len(w.candidates), 1)
        self.assertEqual(w.candidates[0].native_number, 2)
        self.assertEqual(w.candidates[0].debug_offset, 0)
        self.assertEqual(w.proposed_cursor.offset, self.debug.stat().st_size)
        self.assertEqual(w.proposed_cursor.prefix_sha256,
                         hashlib.sha256(self.debug.read_bytes()).hexdigest())
        self.assertEqual(self.cursor.offset, 0)  # no implicit advancement

    def test_fail_counter_rst_and_not_adding_are_not_positives(self):
        self.debug.write_bytes(b'2026 : unknown.p2k.invalid : profile 2 (tail) : '
                               b'client 127.0.0.1:33 : proto http : fail counter 1/1\n'
                               b'2026 : unknown.p2k.invalid : profile 2 (tail) : '
                               b'client 127.0.0.1:33 : proto http : NOT adding, duplicate detected\n')
        raw = self.add()
        w = self.window(raw)
        self.assertEqual(len(w.candidates), 1)
        self.assertGreater(w.candidates[0].debug_offset, 0)
        self.debug.write_bytes(self.debug.read_bytes().replace(b': adding to ', b': NOT adding to '))
        self.rejects(raw, 'raw_and_positive_debug_not_one_to_one')

    def test_debug_precedes_append_no_raw_is_not_proof(self):
        self.add()
        self.rejects(b'', 'invalid_or_incomplete_raw_segment')
        self.rejects(b'another.p2k.invalid\n', 'raw_and_positive_debug_not_one_to_one')

    def test_missing_extra_and_misordered_events_refused(self):
        one = self.add('first.p2k.invalid')
        two = self.add('second.p2k.invalid')
        self.rejects(one, 'raw_and_positive_debug_not_one_to_one')
        self.rejects(two + one, 'raw_and_positive_debug_not_one_to_one')
        self.assertEqual(len(self.window(one + two).candidates), 2)

    def test_cross_profile_and_wrong_output_path_refused(self):
        raw = self.add(profile=1)
        self.rejects(raw, 'unauthorized_native_profile_or_host')
        self.debug.write_bytes(b'')
        raw = self.add(path='/tmp/fake-inbox.txt')
        self.rejects(raw, 'ambiguous_or_wrong_native_add_event')

    def test_incomplete_debug_and_partial_raw_refused(self):
        raw = self.add()
        self.debug.write_bytes(self.debug.read_bytes().rstrip(b'\n'))
        self.rejects(raw, 'debug_window_oversized_or_incomplete')
        self.debug.write_bytes(self.debug.read_bytes() + b'\n')
        self.rejects(raw.rstrip(b'\n'), 'invalid_or_incomplete_raw_segment')

    def test_cursor_different_generation_or_replacement_refused(self):
        raw = self.add()
        self.cursor = replace(self.cursor, generation='c' * 32)
        self.rejects(raw, 'untrusted_or_other_generation_cursor')
        self.cursor = replace(self.cursor, generation='a' * 32)
        earlier = self.debug.read_bytes()
        keep_fd = os.open(self.debug, os.O_RDONLY)
        try:
            self.debug.unlink()
            self.debug.write_bytes(earlier)
        finally:
            os.close(keep_fd)
        self.rejects(raw, 'debug_cursor_replaced_truncated_or_rewritten')

    def test_cursor_prefix_tamper_detected_even_if_offset_kept(self):
        raw = self.add()
        w = self.window(raw)
        raw2 = b'later.p2k.invalid\n'
        self.cursor = w.proposed_cursor
        self.add('later.p2k.invalid')
        w2 = self.window(raw2)
        self.assertEqual(len(w2.candidates), 1)
        now = self.debug.read_bytes()
        self.debug.write_bytes(b'X' + now[1:])
        self.rejects(raw2, 'debug_cursor_replaced_truncated_or_rewritten')

    def test_native_file_owner_group_mode_links_required(self):
        raw = self.add()
        self.debug.chmod(0o666)
        self.rejects(raw, 'unsafe_native_debug_file')
        self.debug.chmod(0o600)
        linked = self.base / 'extra.log'
        os.link(self.debug, linked)
        self.rejects(raw, 'unsafe_native_debug_file')

    def test_symlink_and_invalid_host_fail_closed(self):
        raw = self.add()
        self.debug.unlink()
        self.debug.symlink_to(self.raw)
        self.rejects(raw, 'unsafe_native_debug_file')
        self.debug.unlink()
        self.debug.write_bytes(b'')
        self.add('valid.p2k.invalid')
        self.rejects(b'bad..p2k.invalid\n', 'unqualified_raw_host')

    def test_unowned_existing_debug_history_refuses_new_epoch(self):
        self.add()
        with self.assertRaisesRegex(DebugWindowRefused, 'unowned_existing_debug_history'):
            empty_epoch(self.proof, owner_uid=os.geteuid())

    def test_explicit_native_group_paths_require_exact_0710_and_0660(self):
        gid = os.getgid()
        if gid <= 0:
            self.skipTest('Requires unprivileged test gid for group-mode opt-in')
        self.base.chmod(0o710)
        self.debug.chmod(0o660)
        c = empty_epoch(self.proof, owner_uid=os.geteuid(), writer_gid=gid)
        raw = self.add()
        w = propose_window(self.proof, c, raw, owner_uid=os.geteuid(),
                           writer_gid=gid)
        self.assertEqual(len(w.candidates), 1)
        self.base.chmod(0o770)
        with self.assertRaisesRegex(DebugWindowRefused,
                                    'unsafe_native_debug_parent'):
            propose_window(self.proof, c, raw, owner_uid=os.geteuid(),
                           writer_gid=gid)

    def test_public_entrypoint_is_off(self):
        with self.assertRaisesRegex(DebugWindowRefused,
                                    'read_only_candidates_not_authorized_for_ack'):
            run_native_debug_collector()


if __name__ == '__main__':
    unittest.main()
