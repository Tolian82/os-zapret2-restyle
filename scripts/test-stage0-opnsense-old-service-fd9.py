#!/usr/bin/env python3
"""Offline rejection checks; native OPNsense tests prove the real installed path."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location(
    "old_fd9", Path(__file__).with_name("stage0-opnsense-old-service-fd9.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OldServiceFD9(unittest.TestCase):
    def test_status_environment_only_isolated_fd9(self):
        lock = Path("/tmp/stage0-test/lifecycle.lock")
        env = m.status_env(lock)
        self.assertEqual(env["LIFECYCLE_LOCK_FILE"], str(lock))
        self.assertEqual(env["LOCKF_BIN"], "/usr/bin/lockf")

    def test_only_readonly_original_status_command(self):
        calls = []
        with patch.object(m.subprocess, "run") as run:
            run.return_value = SimpleNamespace(returncode=1, stdout=m.EXPECTED_STATUS)
            m.call_status(Path("/tmp/isolated.lock"))
            calls.extend(run.call_args.args[0])
        self.assertEqual(calls, [m.SERVICE, "status"])

    def test_verified_stopped_only(self):
        m.prove_stopped(SimpleNamespace(returncode=1, stdout=m.EXPECTED_STATUS))
        for rc, output in ((0, "zapret is running"), (2, "incomplete"),
                           (1, "wrong output"), (75, "")):
            with self.subTest(rc=rc, output=output), self.assertRaises(m.pre.Refusal):
                m.prove_stopped(SimpleNamespace(returncode=rc, stdout=output))

    def test_nonempty_or_symlinked_journal_refuses(self):
        with patch.object(m.SHARED_JOURNAL.__class__, "exists", return_value=True):
            with self.assertRaisesRegex(m.pre.Refusal, "JOURNAL"):
                m.assert_fresh_no_shared_journal()

    def test_old_status_lock_holder_is_real_lockf(self):
        self.assertIn("/usr/bin/lockf -s -t 1 9", m.HOLDER_SCRIPT)
        self.assertIn("exec 9>", m.HOLDER_SCRIPT)
        self.assertIn("/bin/sleep 3", m.HOLDER_SCRIPT)
        self.assertNotIn("stop", m.HOLDER_SCRIPT)
        self.assertNotIn("start", m.HOLDER_SCRIPT)

    def test_guest_witness_must_be_real_provenance_before_status(self):
        with patch.object(m.pre, "run", return_value=b"guest"),              patch.object(m.pre, "run_guest", side_effect=m.pre.Refusal("SHA256_MISMATCH")),              patch.object(m, "call_status", side_effect=AssertionError("must not run")):
            with self.assertRaisesRegex(m.pre.Refusal, "SHA256_MISMATCH"):
                m.verify(Path("/tmp/not-an-archive.pkg"))


if __name__ == "__main__":
    unittest.main()
