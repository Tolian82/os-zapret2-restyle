#!/usr/bin/env python3
"""Offline native-deinstall contract tests; actual pkg execution is CI guest-only."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location(
    "deinstall", Path(__file__).with_name("stage0-opnsense-old-deinstall.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalDeinstall(unittest.TestCase):
    def test_native_delete_does_not_bypass_original_hooks(self):
        self.assertEqual(m.DELETE[-2:], ("-y", m.pre.NAME))
        for unsafe in ("-I", "-f", "--force", "--no-scripts",
                       "--script-no-exec", "--accept-missing", "-a"):
            self.assertNotIn(unsafe, m.DELETE)

    def test_original_stopped_trace_is_accepted(self):
        trace = "+ [ -x /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh ]\n" \
                "+ /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status\n" \
                "+ service_status=1\n+ exit 0\n"
        with TemporaryDirectory() as d, patch.object(m, "run_command",
                return_value=SimpleNamespace(returncode=0, stderr=trace)):
            self.assertTrue(m.trace_original_pre_deinstall("#!/bin/sh\nexit 0", Path(d)))

    def test_original_trace_must_show_status_and_stopped(self):
        for trace in ("+ exit 0\n", "+ /some/zapret_service.sh status\n+ exit 0\n",
                      "+ /some/zapret_service.sh status\n+ service_status=0\n+ exit 0\n"):
            with self.subTest(trace=trace), TemporaryDirectory() as d, \
                 patch.object(m, "run_command", return_value=SimpleNamespace(
                     returncode=0, stderr=trace)):
                with self.assertRaises(m.pre.Refusal):
                    m.trace_original_pre_deinstall("#!/bin/sh\nexit 0", Path(d))

    def test_pre_deinstall_stop_path_refuses(self):
        trace = "+ /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status\n" \
                "+ service_status=1\n" \
                "+ /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh stop\n"
        with TemporaryDirectory() as d, patch.object(m, "run_command",
                return_value=SimpleNamespace(returncode=0, stderr=trace)):
            with self.assertRaisesRegex(m.pre.Refusal, "UNEXPECTED_STOP"):
                m.trace_original_pre_deinstall("#!/bin/sh\nexit 0", Path(d))

    def test_failed_pkg_delete_never_claimed_clean(self):
        with patch.object(m, "run_command", return_value=SimpleNamespace(
                returncode=1, stderr="pkg refused", stdout="")):
            with self.assertRaisesRegex(m.pre.Refusal, "NATIVE_OLD_PKG_DELETE_REFUSED"):
                m.native_delete()

    def test_archive_provenance_refusal_happens_before_delete(self):
        with patch.object(m.pre, "run", return_value=b"isolated"), \
             patch.object(m.pre, "run_guest", side_effect=m.pre.Refusal("OLD_SERVICE_BYTES_MISMATCH")), \
             patch.object(m, "native_delete", side_effect=AssertionError("must not delete")):
            with self.assertRaisesRegex(m.pre.Refusal, "OLD_SERVICE_BYTES_MISMATCH"):
                m.verify(Path("/tmp/not-an-archive.pkg"))


if __name__ == "__main__":
    unittest.main()
