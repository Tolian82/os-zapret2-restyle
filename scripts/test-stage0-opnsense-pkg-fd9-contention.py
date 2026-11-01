#!/usr/bin/env python3
"""Offline contracts for synthetic native pkg/FD9 interlock characterization."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

source = Path(__file__).with_name("stage0-opnsense-pkg-fd9-contention.py")
spec = importlib.util.spec_from_file_location("pkg_fd9", source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE = ["old:pre-install", "old:post-install",
        "new:pre-install:FD9_BUSY", "new:post-install:FD9_BUSY"]


class PkgFd9Contracts(unittest.TestCase):
    def test_fixture_hooks_use_real_native_lockf_nonblocking_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            body = m.phase_script("new", "pre-install", p / "trace", p / "fd9.lock")
            self.assertIn("/usr/bin/lockf -s -t 0 9", body)
            self.assertIn("9>", body)
            self.assertIn("exit 73", body)
            self.assertIn("new:pre-install:FD9_BUSY", body)
            self.assertNotIn("zapret_service.sh", body)
            self.assertNotIn("pkg delete", body)

    def test_both_new_hooks_reject_fd9_contention(self):
        for phase in ("pre-install", "post-install"):
            with self.subTest(phase=phase):
                body = m.phase_script("new", phase, Path("/tmp/trace"), Path("/tmp/lock"))
                self.assertIn(phase + ":FD9_BUSY", body)
                self.assertIn("exit 73", body)

    def test_old_hooks_are_inert_trace_only(self):
        for phase in m.PHASES:
            with self.subTest(phase=phase):
                body = m.phase_script("old", phase, Path("/tmp/trace"), Path("/tmp/lock"))
                self.assertIn("exit 0", body)
                self.assertNotIn("lockf", body)

    def test_malformed_role_or_phase_refused(self):
        for role, phase in (("any", "pre-install"), ("old", "execute"), ("new; exit 0", "post-install")):
            with self.subTest(role=role, phase=phase), self.assertRaises(m.Refusal):
                m.phase_script(role, phase, Path("/tmp/a"), Path("/tmp/b"))

    def test_actual_pkg_replacement_despite_both_hook_errors_is_hazard(self):
        self.assertEqual(m.classify(0, m.NAME + "|" + m.NEW, b"new\n", BASE),
                         "PKG_REPLACED_FIXTURE_DESPITE_BOTH_FD9_HOOK_REFUSALS")

    def test_clean_refusal_requires_old_pkg_preserved_and_nonzero(self):
        self.assertEqual(m.classify(1, m.NAME + "|" + m.OLD, b"old\n", BASE),
                         "PKG_REFUSED_AND_PRESERVED_OLD_FIXTURE")

    def test_pkg_success_must_not_be_mistaken_for_clean_refusal(self):
        self.assertEqual(m.classify(0, m.NAME + "|" + m.OLD, b"old\n", BASE),
                         "PARTIAL_OR_INCONSISTENT_PKG_STATE_AFTER_LOCK_CONFLICT")

    def test_partial_mixed_pkgdb_and_payload_is_hazard(self):
        for identity, content in ((m.NAME + "|" + m.NEW, b"old\n"),
                                  (m.NAME + "|" + m.OLD, b"new\n"),
                                  ("ABSENT", None)):
            with self.subTest(identity=identity):
                self.assertEqual(m.classify(1, identity, content, BASE),
                                 "PARTIAL_OR_INCONSISTENT_PKG_STATE_AFTER_LOCK_CONFLICT")

    def test_missing_or_duplicate_busy_trace_refused(self):
        for rows in (BASE[:3], BASE + ["new:pre-install:FD9_BUSY"],
                     [BASE[1], BASE[0], *BASE[2:]]):
            with self.subTest(rows=rows), self.assertRaises(m.Refusal):
                m.classify(1, m.NAME + "|" + m.OLD, b"old\n", rows)

    def test_non_target_refuses_before_build_or_pkg(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        guest = mock.Mock()
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             mock.patch.object(m, "build") as builder, \
             mock.patch.object(m, "command") as cmd:
            with self.assertRaisesRegex(m.Refusal, "REQUIRES_ROOT_FREEBSD_AMD64"):
                m.prove(guest)
            builder.assert_not_called()
            cmd.assert_not_called()
            guest.observe.assert_not_called()

    def test_private_pkg_name_is_not_real_plugin(self):
        self.assertNotEqual(m.NAME, "os-zapret2-restyle")
        self.assertIn("stage0", m.NAME)
        self.assertNotIn("os-zapret2-restyle", m.NAME)

    def test_result_has_explicit_product_safety_false(self):
        code = source.read_text(encoding="utf-8")
        for marker in ("transaction_owner_gate_implemented", "product_safety_acceptance_passed",
                       "stage0_closed", "real_predecessor_replaced", "private_pkgdb_and_payload"):
            self.assertIn(marker, code)
        self.assertIn('os.O_NOFOLLOW', code)
        self.assertNotIn("pkg delete", code)
        self.assertNotIn('"--force"', code)


if __name__ == "__main__":
    unittest.main()
