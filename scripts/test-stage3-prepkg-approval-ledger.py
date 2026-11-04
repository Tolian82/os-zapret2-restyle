#!/usr/bin/env python3
"""Off-target source-only one-use ledger contracts; never a pkg gateway."""
import concurrent.futures
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "stage3-prepkg-approval-ledger.py"
spec = importlib.util.spec_from_file_location("stage3_ci_ledger", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ORIGINAL_PRIVATE_ROOT = m.private_root


@contextlib.contextmanager
def temporary_directory_fd(folder):
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


class LocalLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="zapret2-115-ledger-")
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "approval-ledger"
        self.ledger.mkdir(mode=0o700)
        self.assertEqual(stat.S_IMODE(self.ledger.stat().st_mode), 0o700)
        # Only platform & /root UID ancestry are synthetic on ubuntu-latest.
        # Real flock, O_EXCL, bytes, fsync, symlink/mode and FDs remain real.
        p1 = patch.object(m, "qualify_runtime")
        p2 = patch.object(m, "private_root",
                          side_effect=lambda d: temporary_directory_fd(d))
        p3 = patch.object(m, "root_owner", return_value=True)
        for p in (p1, p2, p3):
            p.start()
            self.addCleanup(p.stop)
        self.authority = "a" * 64
        self.receipt = "b" * 64
        self.policy = "c" * 64

    def start(self):
        answer = m.initialize(str(self.ledger))
        self.assertEqual(answer["status"], "CI_LEDGER_INITIALIZED_NOT_PRODUCTION")
        self.assertFalse(answer["pkg_invoked"])
        self.assertEqual(self.ledger.joinpath("ledger.lock").stat().st_size, 0)

    def use(self, index=1, receipt=None, policy=None, **options):
        return m.consumption(str(self.ledger), self.authority,
                             policy or chr(ord("c") + index-1) * 64,
                             receipt or chr(ord("b") + index-1) * 64,
                             index, **options)

    def test_initialization_private_lock_and_no_duplicate(self):
        self.start()
        self.assertEqual(stat.S_IMODE(
            (self.ledger / "ledger.lock").stat().st_mode), 0o600)
        with self.assertRaisesRegex(m.Refusal, "LEDGER_ALREADY_INITIALIZED"):
            m.initialize(str(self.ledger))
        report = m.inspect(str(self.ledger))
        self.assertEqual(report["spent"], 0)
        self.assertFalse(report["production_pkg_authorized"])

    def test_exact_one_use_and_monotonic_seq_across_reopen(self):
        self.start()
        result = self.use()
        self.assertEqual(result["status"],
                         "CI_LOCAL_ATOMIC_SPENT_NOT_PRODUCTION_AUTHORITY")
        self.assertFalse(result["production_pkg_authorized"])
        self.assertFalse(result["durable_external_rollback_protection"])
        self.assertEqual(m.inspect(str(self.ledger))["last_sequence"], 1)
        with self.assertRaisesRegex(m.Refusal, "LEDGER_SEQUENCE_REPLAY_OR_GAP"):
            self.use()
        with self.assertRaisesRegex(m.Refusal, "LEDGER_SEQUENCE_REPLAY_OR_GAP"):
            self.use(index=3, receipt="d"*64, policy="e"*64)
        self.assertEqual(self.use(index=2, receipt="d"*64,
                                  policy="e"*64)["sequence"], 2)
        self.assertEqual(m.inspect(str(self.ledger))["spent"], 2)
        with self.assertRaisesRegex(m.Refusal, "LEDGER_RECEIPT_ALREADY_SPENT"):
            self.use(index=3, receipt=self.receipt, policy="f"*64)
        with self.assertRaisesRegex(m.Refusal, "LEDGER_POLICY_ALREADY_SPENT"):
            self.use(index=3, receipt="f"*64, policy="e"*64)

    def test_competing_operations_real_flock_and_exclusive_file(self):
        self.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: self._try_consume(), range(2)))
        self.assertEqual(outcomes.count("PASS"), 1)
        self.assertEqual(len([x for x in outcomes if x.startswith("REFUSED")]), 1)
        self.assertEqual(m.inspect(str(self.ledger))["spent"], 1)
        with self.assertRaises(m.Refusal):
            self.use()

    def _try_consume(self):
        try:
            self.use()
            return "PASS"
        except m.Refusal as exc:
            return "REFUSED:" + str(exc)

    def test_crash_after_exclusive_create_poisoned_and_stops_next(self):
        self.start()
        with self.assertRaisesRegex(m.Refusal, "INJECTED_INTERRUPTED_INTENT"):
            self.use(fail_after_create=True)
        self.assertEqual(len(list(self.ledger.glob("spent-*"))), 1)
        with self.assertRaises(m.Refusal):
            m.inspect(str(self.ledger))
        with self.assertRaises(m.Refusal):
            self.use()
        # An interrupted intent is never auto-deleted or retried.
        self.assertEqual(len(list(self.ledger.glob("spent-*"))), 1)

    def test_damaged_entry_hardlink_or_writable_blocks(self):
        self.start()
        self.use()
        entry = list(self.ledger.glob("spent-*"))[0]
        original = entry.read_bytes()
        entry.write_bytes(b'{"incomplete":')
        with self.assertRaisesRegex(m.Refusal, "LEDGER_CORRUPT_JSON"):
            m.inspect(str(self.ledger))
        entry.write_bytes(original)
        entry.chmod(0o666)
        with self.assertRaisesRegex(m.Refusal, "LEDGER_FILE_NOT_ROOT_PRIVATE"):
            m.inspect(str(self.ledger))
        entry.chmod(0o600)
        other = self.ledger / "other-hardlink"
        os.link(entry, other)
        with self.assertRaises(m.Refusal):
            m.inspect(str(self.ledger))
        other.unlink()
        self.assertEqual(m.inspect(str(self.ledger))["spent"], 1)

    def test_modified_chain_or_missing_middle_blocks(self):
        self.start()
        self.use()
        self.use(index=2, receipt="d"*64, policy="e"*64)
        entries = sorted(self.ledger.glob("spent-*"))
        first = json.loads(entries[0].read_text())
        first["previous_entry_sha256"] = "f"*64
        entries[0].write_text(json.dumps(first) + "\n")
        with self.assertRaisesRegex(m.Refusal, "LEDGER_CHAIN_OR_SEQUENCE"):
            m.inspect(str(self.ledger))
        # Next sequence cannot proceed after a malformed chain.
        with self.assertRaises(m.Refusal):
            self.use(index=3, receipt="f"*64, policy="9"*64)

    def test_symlink_unknown_file_and_truncated_lock_fail(self):
        self.start()
        marker = self.ledger / "rogue.tmp"
        marker.write_bytes(b"attacker")
        with self.assertRaisesRegex(m.Refusal, "LEDGER_UNKNOWN_OR_PARTIAL_ENTRY"):
            m.inspect(str(self.ledger))
        marker.unlink()
        lock = self.ledger/"ledger.lock"
        lock.write_bytes(b"ATTACKER")
        with self.assertRaisesRegex(m.Refusal, "LEDGER_LOCK_UNTRUSTED"):
            m.inspect(str(self.ledger))
        lock.unlink()
        lock.symlink_to(self.ledger/"target")
        with self.assertRaises((m.Refusal, OSError)):
            m.inspect(str(self.ledger))

    def test_digest_sequence_or_legacy_args_refused(self):
        self.start()
        for bad in ("0"*64, "g"*64, "abc"):
            with self.subTest(bad=bad), \
                 self.assertRaisesRegex(m.Refusal, "LEDGER_INVALID_DIGEST"):
                m.consumption(str(self.ledger), bad, self.policy,
                              self.receipt, 1)
        for bad in (0, -1, 1.0, True, 513):
            with self.subTest(bad=bad), \
                 self.assertRaisesRegex(m.Refusal, "LEDGER_INVALID_SEQUENCE"):
                m.consumption(str(self.ledger), self.authority, self.policy,
                              self.receipt, bad)
        for argv in ([], ["upgrade"], ["consume"],
                     ["consume", "x", "y", "z"],
                     ["consume", "x", "y", "z", "1", "false"],
                     ["initialize", str(self.ledger), "extra"]):
            with self.subTest(args=argv):
                self.assertEqual(m.main(argv), 78)
        self.assertEqual(m.inspect(str(self.ledger))["spent"], 0)

    def test_unsafe_root_paths_refused_in_actual_path_checker(self):
        # Real directory traversal validator, no test monkeypatch.
        for path in ("/tmp/approval-ledger", "/root/../tmp/approval-ledger",
                     "/root//approval-ledger", "approval-ledger",
                     "/root/other", "/root/approval-ledger/"):
            with self.subTest(path=path), self.assertRaises(m.Refusal):
                with ORIGINAL_PRIVATE_ROOT(path):
                    pass

    def test_explicit_offtarget_nonproduction_source_contract(self):
        source = SOURCE.read_text()
        self.assertIn("fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)",
                      source)
        self.assertIn("os.O_CREAT | os.O_EXCL |", source)
        self.assertIn("os.fsync(written)", source)
        self.assertIn("os.fsync(fd)", source)
        self.assertIn("LEDGER_INJECTED_INTERRUPTED_INTENT", source)
        self.assertIn("CI_ONLY_DISPOSABLE_FREEBSD_ROOT_REQUIRED", source)
        for forbidden in ("subprocess.run(", "subprocess.Popen(",
                          "pkg add", "pkg upgrade", "pkg delete", "os.system("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(m, "upgrade_package"))
        self.assertFalse(hasattr(m, "install_package"))


if __name__ == "__main__":
    unittest.main()
