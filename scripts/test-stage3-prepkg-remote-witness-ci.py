#!/usr/bin/env python3
"""CI-only real socket/SQLite/RSA witness tests, never a pkg upgrade."""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import re
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
        cls.operator_secret = root / "operator-private.pem"
        cls.operator_public = root / "operator-public.pem"
        subprocess.run(["/usr/bin/openssl", "genpkey", "-algorithm", "RSA",
                        "-pkeyopt", "rsa_keygen_bits:2048", "-out",
                        str(cls.operator_secret)], capture_output=True,
                       check=True, timeout=15)
        subprocess.run(["/usr/bin/openssl", "pkey", "-in",
                        str(cls.operator_secret), "-pubout", "-out",
                        str(cls.operator_public)], capture_output=True,
                       check=True, timeout=15)
        cls.operator_public.chmod(0o600)
        cls.operator_sha = hashlib.sha256(cls.operator_public.read_bytes()).hexdigest()
        # GitHub's exact checked-out PR head is passed explicitly to both
        # Ubuntu and disposable OPNsense. The VM may not expose .git or mark
        # its imported checkout safe for root; a git CLI read is not trust.
        cls.source_commit = os.environ.get("ZAPRET2_CI_EXPECTED_HEAD_SHA", "")
        if not re.fullmatch("[0-9a-f]{40}", cls.source_commit):
            raise RuntimeError("CI_EXACT_HEAD_SHA_EXPLICITLY_REQUIRED")
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
        self.serial = 0
        self.op = "1" * 64
        self.op2 = "2" * 64
        self.payload = "a" * 64
        self.checkpoint = "b" * 64
        self.old_version = "0.6.2_1"  # published old CI fixture identity
        revision = re.search(r"(?m)^PLUGIN_REVISION=\s*([0-9]+)\s*$",
                             (HERE.parent / "Makefile").read_text())
        self.assertIsNotNone(revision)
        self.new_version = (HERE.parent / "VERSION").read_text().strip() + "_" + revision.group(1)
        self.old_archive = self.root / ("os-zapret2-restyle-" + self.old_version + ".pkg")
        self.new_archive = self.root / ("os-zapret2-restyle-" + self.new_version + ".pkg")
        self.old_archive.write_bytes(b"CI-ONLY-SYNTHETIC-OLD-PACKAGE-BYTES-v1")
        self.new_archive.write_bytes(b"CI-ONLY-SYNTHETIC-NEW-PACKAGE-BYTES-v1")
        self.old_archive.chmod(0o600)
        self.new_archive.chmod(0o600)
        self.old_hash = hashlib.sha256(self.old_archive.read_bytes()).hexdigest()
        self.new_hash = hashlib.sha256(self.new_archive.read_bytes()).hexdigest()
        self.operator_grant = self.root / "operation-grant.json"
        self.operator_sig = self.root / "operation-grant.sig"
        now = int(time.time())
        entries = [
            {"operation_id": op, "payload_sha256": self.payload,
             "checkpoint_sha256": cp, "checkpoint_sequence": seq}
            for op, cp, seq in (
                (self.op, self.checkpoint, 6),
                (self.op2, self.checkpoint, 6),
                (self.op2, "c" * 64, 6),
                (self.op, self.checkpoint, 10),
                (self.op2, "c" * 64, 1))
        ]
        self.policy = {
            "schema": "zapret2-ci-operator-operation-grant-v1",
            "repository": "Tolian82/os-zapret2-restyle",
            "issuer": "CI_EPHEMERAL_OPERATOR_NOT_OWNER_APPROVED",
            "sequence": 1, "operator_authority_sha256": self.operator_sha,
            "status_signer_sha256": self.keysha,
            "client_leaf_sha256": self.client_sha,
            "source_commit": self.source_commit,
            "old_pkg_sha256": self.old_hash, "new_pkg_sha256": self.new_hash,
            "old_pkg_version": self.old_version, "new_pkg_version": self.new_version,
            "not_before": now - 60, "not_after": now + 600,
            "actions": ["RESERVE", "CONSUME", "ABORT", "STATUS"],
            "entries": entries
        }
        self.seal_policy()
        self.start_server()

    def tearDown(self):
        self.stop_server()

    def seal_policy(self, private=None):
        raw = (json.dumps(self.policy, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.operator_grant.write_bytes(raw)
        self.operator_grant.chmod(0o600)
        result = subprocess.run(
            ["/usr/bin/openssl", "dgst", "-sha256", "-sign",
             str(private or self.operator_secret)], input=raw,
            capture_output=True, check=True, timeout=10)
        self.operator_sig.write_bytes(result.stdout)
        self.operator_sig.chmod(0o600)

    def serve_args(self):
        return [sys.executable, "-u",
                str(HERE / "stage3-prepkg-remote-witness-ci.py"),
                "serve", str(self.db), str(self.secret),
                str(self.ca_cert), str(self.tls_server_cert),
                str(self.tls_server_key), str(self.client_sha),
                str(self.operator_grant), str(self.operator_sig),
                str(self.operator_public), str(self.operator_sha),
                self.source_commit, str(self.old_archive), str(self.new_archive)]

    def expect_refused_start(self, expected):
        self.stop_server()
        attempt = subprocess.run(self.serve_args(), env=self.env,
                                 capture_output=True, timeout=8)
        self.assertEqual(attempt.returncode, 78, attempt.stderr.decode())
        self.assertIn(expected.encode(), attempt.stderr)
        self.assertEqual(self.rows(), ([], 0))

    def start_server(self):
        proc = subprocess.Popen(self.serve_args(),
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
        attempt = subprocess.run(self.serve_args(),
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


    def test_signed_operator_grant_allows_only_exact_preapproved_operations(self):
        self.refused(self.req("RESERVE", operation="3" * 64))
        self.refused(self.req("RESERVE", payload="f" * 64))
        self.refused(self.req("RESERVE", cp="f" * 64))
        self.refused(self.req("RESERVE", cpseq=7))
        self.assertEqual(self.rows(), ([], 0))
        self.assertEqual(self.verified(self.req(), 7)["operation_action"], "RESERVED")
        self.assertEqual(self.rows()[1], 1)

    def test_signed_operator_grant_action_rights_refuse_before_sqlite(self):
        self.stop_server()
        self.policy["actions"] = ["STATUS"]
        self.seal_policy()
        self.start_server()
        self.refused(self.req("RESERVE"))
        self.assertEqual(self.rows(), ([], 0))

    def test_operator_signature_tamper_refuses_before_listening(self):
        raw = self.operator_grant.read_bytes()
        self.operator_grant.write_bytes(raw.replace(b'"old_pkg_sha256":"', b'"old_pkg_sha256":"f'))
        self.operator_grant.chmod(0o600)
        self.expect_refused_start("GRANT_OPERATOR_SIGNATURE_INVALID")

    def test_operator_detached_signature_substitution_refuses_before_listening(self):
        self.operator_sig.write_bytes(b"forged-operator")
        self.operator_sig.chmod(0o600)
        self.expect_refused_start("GRANT_OPERATOR_SIGNATURE_INVALID")

    def test_operator_signer_expected_fingerprint_wrong_refuses(self):
        self.operator_sha = "f" * 64
        self.expect_refused_start("GRANT_OPERATOR_AUTHORITY_FINGERPRINT_MISMATCH")

    def test_operator_signed_wrong_client_leaf_refuses(self):
        self.policy["client_leaf_sha256"] = "f" * 64
        self.seal_policy()
        self.expect_refused_start("GRANT_TRUST_ROLE_BINDING_MISMATCH:client_leaf_sha256")

    def test_operator_signed_wrong_response_key_refuses(self):
        self.policy["status_signer_sha256"] = "f" * 64
        self.seal_policy()
        self.expect_refused_start("GRANT_TRUST_ROLE_BINDING_MISMATCH:status_signer_sha256")

    def test_operator_wrong_repository_or_issuer_refuses_even_if_resigned(self):
        self.policy["repository"] = "attacker/fake"
        self.seal_policy()
        self.expect_refused_start("GRANT_SCHEMA_OR_ISSUER_INVALID")

    def test_operator_expired_or_future_grant_refuses_on_start(self):
        now = int(time.time())
        self.policy["not_before"], self.policy["not_after"] = now - 120, now - 60
        self.seal_policy()
        self.expect_refused_start("GRANT_EXPIRED_OR_NOT_YET_VALID")
        self.policy["not_before"], self.policy["not_after"] = now + 120, now + 240
        self.seal_policy()
        self.expect_refused_start("GRANT_EXPIRED_OR_NOT_YET_VALID")

    def test_operator_signed_grant_expiring_during_runtime_refuses_before_sqlite(self):
        self.stop_server()
        now = int(time.time())
        self.policy["not_before"], self.policy["not_after"] = now - 30, now + 2
        self.seal_policy()
        self.start_server()
        time.sleep(4)
        self.refused(self.req())
        self.assertEqual(self.rows(), ([], 0))

    def test_operator_valid_sig_but_duplicate_grant_entry_refuses(self):
        self.policy["entries"].append(dict(self.policy["entries"][0]))
        self.seal_policy()
        self.expect_refused_start("GRANT_DUPLICATE_ENTRY")

    def test_operator_private_file_mode_and_symlink_refuses(self):
        self.stop_server()
        self.operator_grant.chmod(0o644)
        self.expect_refused_start("GRANT_PRIVATE_FILE_UNSAFE")
        self.operator_grant.chmod(0o600)
        destination = self.root / "saved-grant.json"
        self.operator_grant.rename(destination)
        self.operator_grant.symlink_to(destination)
        self.expect_refused_start("CI_WITNESS_REFUSED")

    def test_operator_same_key_as_status_signer_refuses_roles(self):
        self.stop_server()
        self.public.chmod(0o600)
        self.operator_public = self.public
        self.operator_sha = self.keysha
        self.policy["operator_authority_sha256"] = self.operator_sha
        self.seal_policy(private=self.secret)
        self.expect_refused_start("GRANT_OPERATOR_AND_STATUS_SIGNER_MUST_DIFFER")

    def test_operator_old_client_legacy_serve_cannot_bypass_policy(self):
        args = self.serve_args()[:9]
        proc = subprocess.run(args, env=self.env, capture_output=True, timeout=8)
        self.assertEqual(proc.returncode, 78)
        self.assertIn(b"WITNESS_CLI_INVALID", proc.stderr)



    def test_measured_old_archive_tampered_after_start_is_refused(self):
        self.old_archive.write_bytes(b"CI-ROOT-REPLACED-OLD-ARCHIVE")
        self.refused(self.req())
        self.assertEqual(self.rows(), ([], 0))

    def test_measured_new_archive_tampered_after_start_is_refused(self):
        self.new_archive.write_bytes(b"CI-ROOT-REPLACED-INCOMING")
        self.refused(self.req())
        self.assertEqual(self.rows(), ([], 0))

    def test_measured_new_archive_missing_after_start_is_refused(self):
        self.new_archive.unlink()
        self.refused(self.req())
        self.assertEqual(self.rows(), ([], 0))

    def test_measured_old_archive_changed_after_reserve_blocks_consume(self):
        self.verified(self.req(), 7)
        original = self.rows()
        self.old_archive.write_bytes(b"MODIFIED-BETWEEN-RESERVE-AND-CONSUME")
        self.refused(self.req("CONSUME"))
        self.assertEqual(self.rows(), original)

    def test_measured_archive_bad_mode_refused_at_start(self):
        self.old_archive.chmod(0o666)
        self.expect_refused_start("GRANT_ARCHIVE_FILE_UNSAFE")

    def test_measured_archive_valid_signature_wrong_old_hash_refused(self):
        self.policy["old_pkg_sha256"] = "f" * 64
        self.seal_policy()
        self.expect_refused_start("GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST")

    def test_measured_archive_valid_signature_wrong_new_hash_refused(self):
        self.policy["new_pkg_sha256"] = "f" * 64
        self.seal_policy()
        self.expect_refused_start("GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST")

    def test_signed_grant_different_checkout_commit_refused_at_start(self):
        self.policy["source_commit"] = "f" * 40
        self.seal_policy()
        self.expect_refused_start("GRANT_SOURCE_COMMIT_NOT_EXPECTED")

    def test_signed_grant_different_package_basename_refused(self):
        self.policy["old_pkg_version"] = "8.8.8_1"
        self.seal_policy()
        self.expect_refused_start("GRANT_ARCHIVE_NAME_VERSION_INVALID")

    def test_archive_path_symlink_replacement_after_start_refused(self):
        target = self.root / "saved-package.pkg"
        self.old_archive.rename(target)
        self.old_archive.symlink_to(target)
        self.refused(self.req())
        self.assertEqual(self.rows(), ([], 0))

    def test_archive_hardlink_duplicate_refused(self):
        duplicate = self.root / "second-name.pkg"
        os.link(self.old_archive, duplicate)
        self.refused(self.req())
        self.assertEqual(self.rows(), ([], 0))

    def test_archive_replaced_with_same_bytes_is_not_false_identity_authority(self):
        # The test accepts identical content at a new inode at startup:
        # SHA verification is content, NOT proof that the installed pkgdb owns
        # these bytes or that the filename cannot be swapped after this check.
        self.old_archive.unlink()
        self.old_archive.write_bytes(b"CI-ONLY-SYNTHETIC-OLD-PACKAGE-BYTES-v1")
        self.old_archive.chmod(0o600)
        self.assertEqual(self.verified(self.req(), 7)["operation_action"], "RESERVED")
        self.assertFalse(self.verified(self.req("CONSUME"), 8)["production_pkg_authorized"])


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
        proc = subprocess.run(self.serve_args(),
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=5)
        self.assertEqual(proc.returncode, 78)
        self.assertIn(b"WITNESS_DISPOSABLE_CI_OPTIN_REQUIRED", proc.stderr)


if __name__ == "__main__":
    unittest.main()
