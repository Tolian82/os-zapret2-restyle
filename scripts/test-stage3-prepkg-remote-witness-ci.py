#!/usr/bin/env python3
"""CI-only real socket/SQLite/RSA witness tests, never a pkg upgrade."""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import select
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


witness = load("ci_witness_network", "stage3-prepkg-remote-witness-ci.py")
verifier = load("ci_witness_signature", "stage3-prepkg-signed-status.py")


class DurableWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keyroot = tempfile.TemporaryDirectory(prefix="ci-key-")
        root = Path(cls.keyroot.name)
        cls.secret = root / "ephemeral-private.pem"
        cls.public = root / "ephemeral-public.pem"
        for args in (("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
                      "-out", str(cls.secret)),
                     ("pkey", "-in", str(cls.secret), "-pubout", "-out", str(cls.public))):
            subprocess.run(["/usr/bin/openssl", *args], capture_output=True,
                           check=True, timeout=15)
        cls.pub = cls.public.read_bytes()
        cls.keysha = hashlib.sha256(cls.pub).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.keyroot.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ci-remote-witness-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "operations.sqlite"
        self.env = {**os.environ, "ZAPRET2_CI_REMOTE_WITNESS_ONLY": "1"}
        init = subprocess.run([sys.executable, str(HERE / "stage3-prepkg-remote-witness-ci.py"),
                               "init", str(self.db)], env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(init.returncode, 0, init.stderr.decode())
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)
        self.server = None
        self.port = None
        self.start_server()
        self.serial = 0
        self.op = "1" * 64
        self.op2 = "2" * 64
        self.payload = "a" * 64
        self.checkpoint = "b" * 64

    def tearDown(self):
        self.stop_server()

    def start_server(self):
        proc = subprocess.Popen([sys.executable, "-u",
                                 str(HERE / "stage3-prepkg-remote-witness-ci.py"),
                                 "serve", str(self.db), str(self.secret)],
                                env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        self.server = proc
        self.addCleanup(self.stop_server)
        readable, _, _ = select.select([proc.stdout], [], [], 8)
        self.assertTrue(readable, "CI witness port handshake timed out")
        line = proc.stdout.readline().strip()
        self.assertTrue(line.startswith("CI_WITNESS_PORT="),
                        "server failed: " + line)
        self.port = int(line.split("=", 1)[1])

    def stop_server(self):
        proc = self.server
        if proc is None:
            return
        self.server = None
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        proc.stdout.close()
        proc.stderr.close()

    def req(self, action="RESERVE", operation=None, payload=None, cp=None,
            cpseq=6, challenge=None, drop=False):
        self.serial += 1
        answer = {"action": action, "operation_id": operation or self.op,
                  "payload_sha256": payload or self.payload,
                  "checkpoint_sha256": cp or self.checkpoint,
                  "checkpoint_sequence": cpseq,
                  "challenge_sha256": challenge or ("%064x" % self.serial)}
        if drop:
            answer["drop_after_commit"] = True
        return answer

    def send(self, obj):
        return witness.request(self.port, obj)

    def verified(self, data, seq):
        raw, sig = self.send(data)
        reply = verifier.verify_response(
            raw, sig, self.pub, self.keysha, data["challenge_sha256"],
            data["operation_id"], data["payload_sha256"],
            data["checkpoint_sha256"], data["checkpoint_sequence"], seq,
            int(time.time()))
        self.assertFalse(reply["production_pkg_authorized"])
        self.assertFalse(reply["independent_remote_witness_deployed"])
        return reply

    def refused(self, data):
        with self.assertRaises((witness.Refusal, OSError, ValueError)):
            self.send(data)

    def rows(self):
        with sqlite3.connect(self.db) as con:
            return (con.execute("SELECT op,payload,checkpoint,state,witness_seq "
                                "FROM operations ORDER BY op").fetchall(),
                    con.execute("SELECT count(*) FROM challenges").fetchone()[0])

    def test_real_signed_reserve_and_consume_independent_process(self):
        self.assertEqual(self.verified(self.req(), 7)["operation_action"], "RESERVED")
        self.assertEqual(self.verified(self.req("CONSUME"), 8)["operation_action"], "CONSUMED")
        records, nonces = self.rows()
        self.assertEqual((len(records), records[0][3], nonces), (1, "CONSUMED", 2))

    def test_lost_commit_reply_has_durable_status_readback_with_fresh_nonce(self):
        self.verified(self.req(), 7)
        before = self.rows()
        self.refused(self.req("CONSUME", drop=True))  # Commit succeeds before socket closes.
        after = self.rows()
        self.assertEqual(after[0][0][3], "CONSUMED")
        self.assertEqual(after[1], before[1] + 1)
        self.assertEqual(self.verified(self.req("STATUS"), 8)["operation_action"], "CONSUMED")
        self.assertEqual(self.verified(self.req("CONSUME"), 8)["operation_action"], "CONSUMED")
        self.assertEqual(len(self.rows()[0]), 1)

    def test_signed_status_after_real_process_restart(self):
        self.verified(self.req(), 7)
        self.verified(self.req("CONSUME"), 8)
        before = self.rows()
        self.stop_server()
        self.start_server()
        self.assertEqual(self.verified(self.req("STATUS"), 8)["operation_action"], "CONSUMED")
        self.assertEqual(self.rows()[0], before[0])

    def test_two_real_concurrent_socket_reservations_one_winner(self):
        first = self.req("RESERVE", operation=self.op)
        second = self.req("RESERVE", operation=self.op2)
        def submit(value):
            try:
                return self.send(value)
            except (witness.Refusal, OSError):
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, (first, second)))
        self.assertEqual(sum(bool(x) for x in results), 1)
        self.assertEqual(len(self.rows()[0]), 1)

    def test_reusing_same_nonce_rejected_even_for_status(self):
        original = self.req()
        self.verified(original, 7)
        self.refused(original)
        after = self.rows()
        self.assertEqual(after[1], 1)
        item = self.req("STATUS")
        self.verified(item, 7)
        self.refused(item)

    def test_second_operation_cannot_spend_consumed_checkpoint(self):
        self.verified(self.req(), 7)
        self.verified(self.req("CONSUME"), 8)
        self.refused(self.req("RESERVE", operation=self.op2))
        self.assertEqual(self.rows()[0][0][3], "CONSUMED")

    def test_pending_operation_blocks_other_identity(self):
        self.verified(self.req(), 7)
        self.refused(self.req("RESERVE", operation=self.op2, cp="c" * 64))
        self.assertEqual(len(self.rows()[0]), 1)

    def test_abort_then_new_operation_can_reserve_same_checkpoint(self):
        self.verified(self.req(), 7)
        self.assertEqual(self.verified(self.req("ABORT"), 8)["operation_action"], "ABORTED")
        self.refused(self.req("CONSUME"))
        self.assertEqual(self.verified(self.req("RESERVE", operation=self.op2), 9)
                         ["operation_action"], "RESERVED")
        self.assertEqual(len(self.rows()[0]), 2)

    def test_witness_sequence_monotonic_when_checkpoint_sequence_decreases(self):
        self.assertEqual(self.verified(self.req(cpseq=10), 11)["operation_action"], "RESERVED")
        self.assertEqual(self.verified(self.req("ABORT", cpseq=10), 12)["operation_action"], "ABORTED")
        next_op = self.req("RESERVE", operation=self.op2, cp="c" * 64, cpseq=1)
        self.assertEqual(self.verified(next_op, 13)["operation_action"], "RESERVED")

    def test_status_wrong_stored_payload_and_checkpoint_refused(self):
        self.verified(self.req(), 7)
        self.refused(self.req("STATUS", payload="d" * 64))
        self.refused(self.req("STATUS", cp="c" * 64))
        self.refused(self.req("STATUS", cpseq=7))
        self.assertEqual(self.rows()[0][0][3], "RESERVED")

    def test_changed_payload_for_same_id_and_terminal_conflict_refused(self):
        self.verified(self.req(), 7)
        self.refused(self.req("CONSUME", payload="c" * 64))
        self.verified(self.req("CONSUME"), 8)
        self.refused(self.req("ABORT"))
        self.refused(self.req("RESERVE"))
        self.assertEqual(len(self.rows()[0]), 1)

    def test_fake_key_and_wrong_external_sequence_fail_client_verifier(self):
        record = self.req()
        raw, sig = self.send(record)
        with self.assertRaisesRegex(verifier.Refusal, "STATUS_WITNESS_KEY_FINGERPRINT_MISMATCH"):
            verifier.verify_response(raw, sig, self.pub, "f" * 64,
                                     record["challenge_sha256"], self.op,
                                     self.payload, self.checkpoint, 6, 7, int(time.time()))
        with self.assertRaisesRegex(verifier.Refusal, "STATUS_WITNESS_SEQUENCE_MISMATCH"):
            verifier.verify_response(raw, sig, self.pub, self.keysha,
                                     record["challenge_sha256"], self.op,
                                     self.payload, self.checkpoint, 6, 9, int(time.time()))

    def test_invalid_schema_does_not_create_operation_or_consume_nonce(self):
        for changes in ({"operation_id": "broken"},
                        {"checkpoint_sequence": True},
                        {"action": "UPGRADE"},
                        {"extra": "unsafe"}):
            obj = self.req()
            obj.update(changes)
            self.refused(obj)
        self.assertEqual(self.rows(), ([], 0))

    def test_missing_operation_and_outage_fail_closed(self):
        self.refused(self.req("STATUS"))
        self.stop_server()
        with self.assertRaises((OSError, witness.Refusal)):
            self.send(self.req())

    def test_corrupted_database_refuses_without_auto_recreation(self):
        self.stop_server()
        self.db.write_bytes(b"not an SQLite journal")
        attempt = subprocess.run([sys.executable, str(HERE / "stage3-prepkg-remote-witness-ci.py"),
                                  "serve", str(self.db), str(self.secret)],
                                 env=self.env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(attempt.returncode, 78)
        self.assertIn(b"CI_WITNESS_REFUSED", attempt.stderr)
        self.assertEqual(self.db.read_bytes(), b"not an SQLite journal")

    def test_ci_root_rollback_counterexample_remains_possible(self):
        # Snapshot of same-host SQLite before any operation: NOT remote trust.
        old_bytes = self.db.read_bytes()
        self.verified(self.req(), 7)
        self.verified(self.req("CONSUME"), 8)
        self.assertEqual(self.rows()[0][0][3], "CONSUMED")
        self.stop_server()
        self.db.write_bytes(old_bytes)
        self.db.chmod(0o600)
        self.start_server()
        # A privileged CI root can restore old DB bytes and reuse a checkpoint.
        replay = self.verified(self.req(), 7)
        self.assertEqual(replay["operation_action"], "RESERVED")
        self.assertFalse(replay["witness_latest_external_authoritative"])

    def test_authority_not_approved_and_no_pkg_execution_paths(self):
        source = (HERE / "stage3-prepkg-remote-witness-ci.py").read_text()
        for forbidden in ("pkg add", "pkg upgrade", "pkg delete", "os.system(",
                          "shell=True", "0.0.0.0", "witness_owner_approved=True"):
            self.assertNotIn(forbidden, source)
        self.assertIn('("127.0.0.1", 0)', source)
        self.assertFalse(self.verified(self.req(), 7)["production_pkg_authorized"])

    def test_cli_disallows_execution_without_disposable_opt_in(self):
        env = dict(os.environ)
        env.pop("ZAPRET2_CI_REMOTE_WITNESS_ONLY", None)
        proc = subprocess.run([sys.executable, str(HERE / "stage3-prepkg-remote-witness-ci.py"),
                               "serve", str(self.db), str(self.secret)],
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=5)
        self.assertEqual(proc.returncode, 78)
        self.assertIn(b"WITNESS_DISPOSABLE_CI_OPTIN_REQUIRED", proc.stderr)


if __name__ == "__main__":
    unittest.main()
