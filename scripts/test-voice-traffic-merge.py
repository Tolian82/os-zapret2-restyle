#!/usr/bin/env python3
"""Single-engine Voice+ordinary profile merge regression."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
spec = importlib.util.spec_from_file_location("voice_traffic_merge", BACKEND/"voice_traffic_merge.py")
assert spec and spec.loader
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)

VOICE = "--name=voice-telegram\n--filter-l3=ipv4\n--ipset=/managed/ipset-telegram.txt\n--filter-udp=*\n--filter-l7=stun\n--payload=stun\n"
A2 = "--filter-udp=596-599\n--filter-l7=unknown\n--payload=unknown\n--ipset=/managed/ipset-telegram.txt\n"
STRATEGIES = "--filter-tcp=443\n--filter-l7=tls\n--new\n" + A2


class OneEngineMergeTests(unittest.TestCase):
    def test_all_off_preserves_regular_strategy_byte_for_byte(self):
        for ordinary in (STRATEGIES, STRATEGIES + "\n", STRATEGIES[:-1]):
            with self.subTest(text=ordinary):
                self.assertEqual(ordinary, merge.merge_profiles("", ordinary))

    def test_voice_before_user_and_one_explicit_boundary(self):
        result = merge.merge_profiles(VOICE, STRATEGIES)
        self.assertTrue(result.startswith("--name=voice-telegram"))
        self.assertIn("--payload=stun\n--new\n--filter-tcp=443", result)
        self.assertEqual(2, result.count("\n--new\n"))
        self.assertTrue(result.endswith(STRATEGIES))
        self.assertIn(A2, result)
        self.assertEqual(1, result.count("--name=voice-telegram"))

    def test_several_services_keep_profile_order_and_original_user(self):
        other = "--name=voice-discord\n--filter-l3=ipv4\n--filter-udp=1400\n"
        result = merge.merge_profiles(VOICE + "--new\n" + other, STRATEGIES)
        self.assertLess(result.index("--name=voice-telegram"), result.index("--name=voice-discord"))
        self.assertLess(result.index("--name=voice-discord"), result.index("--filter-tcp=443"))
        self.assertTrue(result.endswith(STRATEGIES))

    def test_reject_duplicate_poc_profile_identity_and_corrupt_boundaries(self):
        invalid = (
            "",
            "--new\n" + STRATEGIES,
            STRATEGIES + "--new\n",
            "--name=voice-telegram\n" + STRATEGIES,
            "--name=telegram-voice-poc\n" + STRATEGIES,
            "hello\x00world",
            "hello\rworld",
        )
        for ordinary in invalid:
            with self.subTest(ordinary=ordinary):
                with self.assertRaises(merge.VoiceMergeError):
                    merge.merge_profiles(VOICE, ordinary)
        with self.assertRaises(merge.VoiceMergeError):
            merge.merge_profiles("--new\n" + VOICE, STRATEGIES)
        with self.assertRaises(merge.VoiceMergeError):
            merge.merge_profiles(VOICE + "--new\n", STRATEGIES)

    def test_cli_candidate_creation_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            voice, user, output = folder/"voice", folder/"ordinary", folder/"merged"
            voice.write_text(VOICE)
            user.write_text(STRATEGIES)
            argv = [sys.executable, str(BACKEND/"voice_traffic_merge.py"), str(voice), str(user), str(output)]
            success = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(0, success.returncode, success.stderr)
            self.assertTrue(output.read_text().endswith(STRATEGIES))
            unchanged = output.read_bytes()
            again = subprocess.run(argv, capture_output=True, text=True)
            self.assertNotEqual(0, again.returncode)
            self.assertEqual(unchanged, output.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
