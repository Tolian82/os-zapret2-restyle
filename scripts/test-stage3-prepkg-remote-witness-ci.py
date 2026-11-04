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
import ssl
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
        cls.ca_key, cls.ca_cert = root / "ca-key.pem", root / "ca.crt"
        cls.rogue_ca_key, cls.rogue_ca_cert = root / "rogue-ca-key.pem", root / "rogue-ca.crt"

        def openssl(*args):
            subprocess.run(["/usr/bin/openssl", *map(str, args)],
                           capture_output=True, check=True, timeout=15)

        def ca(key, certificate, common_name):
            openssl("genpkey", "-algorithm", "RSA", "-pkeyopt",
                    "rsa_keygen_bits:2048", "-out", key)
            openssl("req", "-x509", "-new", "-sha256", "-key", key,
                    "-out", certificate, "-days", "1", "-subj", "/CN=" + common_name,
                    "-addext", "basicConstraints=critical,CA:TRUE",
                    "-addext", "keyUsage=critical,keyCertSign,cRLSign")

        ca(cls.ca_key, cls.ca_cert, "CI-Witness-CA")
        ca(cls.rogue_ca_key, cls.rogue_ca_cert, "CI-Foreign-CA")

        def issue(name, signer_cert, signer_key, usage, san=None):
            private = root / (name + ".key")
            request = root / (name + ".csr")
            certificate = root / (name + ".crt")
            extensions = root / (name + ".ext")
            openssl("genpkey", "-algorithm", "RSA", "-pkeyopt",
                    "rsa_keygen_bits:2048", "-out", private)
            openssl("req", "-new", "-key", private, "-out", request,
                    "-subj", "/CN=" + name)
            extensions.write_text(
                "basicConstraints=critical,CA:FALSE\n"
                "keyUsage=digitalSignature,keyEncipherment\n"
                "extendedKeyUsage=" + usage + "\n" +
                ("subjectAltName=" + san + "\n" if san is not None else ""))
            openssl("x509", "-req", "-in", request, "-CA", signer_cert,
                    "-CAkey", signer_key, "-CAcreateserial", "-out", certificate,
                    "-days", "1", "-sha256", "-extfile", extensions)
            return private, certificate

        cls.tls_server_key, cls.tls_server_cert = issue(
            "ci-server", cls.ca_cert, cls.ca_key, "serverAuth", "IP:127.0.0.1")
        cls.tls_client_key, cls.tls_client_cert = issue(
            "ci-client", cls.ca_cert, cls.ca_key, "clientAuth")
        cls.tls_rogue_key, cls.tls_rogue_cert = issue(
            "ci-rogue", cls.rogue_ca_cert, cls.rogue_ca_key, "clientAuth")
        cls.tls_wronghost_key, cls.tls_wronghost_cert = issue(
            "ci-wronghost", cls.ca_cert, cls.ca_key, "serverAuth",
            "DNS:wrong.invalid")
        cls.tls_other_client_key, cls.tls_other_client_cert = issue(
            "ci-other-client", cls.ca_cert, cls.ca_key, "clientAuth")
        cls.tls_other_server_key, cls.tls_other_server_cert = issue(
            "ci-other-server", cls.ca_cert, cls.ca_key, "serverAuth",
            "IP:127.0.0.1")
        cls.server_sha = hashlib.sha256(
            ssl.PEM_cert_to_DER_cert(cls.tls_server_cert.read_text())).hexdigest()
        cls.client_sha = hashlib.sha256(
            ssl.PEM_cert_to_DER_cert(cls.tls_client_cert.read_text())).hexdigest()

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
                                 "serve", str(self.db), str(self.secret),
                                 str(self.ca_cert), str(self.tls_server_cert),
                                 str(self.tls_server_key), str(self.client_sha)],
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

    def send(self, obj, ca=None, cert=None, key=None, server_sha=None):
        return witness.request(self.port, obj, str(ca or self.ca_cert),
                               str(cert or self.tls_client_cert),
                               str(key or self.tls_client_key),
                               server_sha or self.server_sha)

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
                                  "serve", str(self.db), str(self.secret),
                                  str(self.ca_cert), str(self.tls_server_cert),
                                  str(self.tls_server_key), str(self.client_sha)],
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


    def test_mtls_wrong_client_ca_refused_before_sqlite_transaction(self):
        self.refused_mtls(self.req(), ca=self.ca_cert,
                          cert=self.tls_rogue_cert, key=self.tls_rogue_key)
        self.assertEqual(self.rows(), ([], 0))

    def test_mtls_wrong_server_ca_refused_before_sqlite_transaction(self):
        self.refused_mtls(self.req(), ca=self.rogue_ca_cert)
        self.assertEqual(self.rows(), ([], 0))

    def test_mtls_missing_client_certificate_refused_before_sqlite(self):
        import ssl
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
                                             cafile=str(self.ca_cert))
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=3) as tcp:
                with context.wrap_socket(tcp, server_hostname="127.0.0.1") as wire:
                    wire.settimeout(3)
                    wire.sendall((json.dumps(self.req()) + "\n").encode())
                    self.assertEqual(wire.recv(4096), b"")
        except (ssl.SSLError, OSError):
            pass  # TLS server may reject before or after client handshake returns.
        self.assertEqual(self.rows(), ([], 0))

    def test_mtls_plain_tcp_request_does_not_touch_sqlite(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=3) as tcp:
            tcp.settimeout(3)
            tcp.sendall((json.dumps(self.req()) + "\n").encode())
            tcp.shutdown(socket.SHUT_WR)
            try:
                tcp.recv(4096)
            except OSError:
                pass
        self.assertEqual(self.rows(), ([], 0))

    def test_mtls_server_wrong_san_refused(self):
        self.stop_server()
        previous = (self.tls_server_cert, self.tls_server_key)
        self.tls_server_cert, self.tls_server_key = (
            self.tls_wronghost_cert, self.tls_wronghost_key)
        try:
            self.start_server()
            self.refused_mtls(self.req())
            self.assertEqual(self.rows(), ([], 0))
        finally:
            self.stop_server()
            self.tls_server_cert, self.tls_server_key = previous
            self.start_server()

    def test_mtls_client_cert_cannot_be_server_cert(self):
        # EKU serverAuth is not authorized for the client role.
        self.refused_mtls(self.req(), cert=self.tls_server_cert,
                          key=self.tls_server_key)
        self.assertEqual(self.rows(), ([], 0))

    def test_mtls_valid_ca_other_client_identity_pin_refused(self):
        self.refused_mtls(self.req(), cert=self.tls_other_client_cert,
                          key=self.tls_other_client_key)
        self.assertEqual(self.rows(), ([], 0))

    def test_mtls_valid_ca_same_hostname_other_server_pin_refused(self):
        self.stop_server()
        previous = (self.tls_server_cert, self.tls_server_key)
        self.tls_server_cert, self.tls_server_key = (
            self.tls_other_server_cert, self.tls_other_server_key)
        try:
            self.start_server()
            with self.assertRaisesRegex(witness.Refusal,
                                        "CLIENT_SERVER_CERT_PIN_MISMATCH"):
                self.send(self.req())
            self.assertEqual(self.rows(), ([], 0))
        finally:
            self.stop_server()
            self.tls_server_cert, self.tls_server_key = previous
            self.start_server()

    def test_mtls_missing_server_pin_refused_without_network_mutation(self):
        with self.assertRaisesRegex(witness.Refusal, "CLIENT_SERVER_CERT_PIN_REQUIRED"):
            witness.request(self.port, self.req(), str(self.ca_cert),
                            str(self.tls_client_cert), str(self.tls_client_key), "bad")
        self.assertEqual(self.rows(), ([], 0))

    def refused_mtls(self, data, **kwargs):
        import ssl
        with self.assertRaises((ssl.SSLError, OSError, witness.Refusal)):
            self.send(data, **kwargs)

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
                               "serve", str(self.db), str(self.secret),
                               str(self.ca_cert), str(self.tls_server_cert),
                               str(self.tls_server_key), str(self.client_sha)],
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=5)
        self.assertEqual(proc.returncode, 78)
        self.assertIn(b"WITNESS_DISPOSABLE_CI_OPTIN_REQUIRED", proc.stderr)


if __name__ == "__main__":
    unittest.main()
