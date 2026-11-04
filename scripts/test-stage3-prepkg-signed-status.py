#!/usr/bin/env python3
"""Executable RSA/challenge/status response tests; no remote server or pkg."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "stage3-prepkg-signed-status.py"
spec = importlib.util.spec_from_file_location("ci_signed_status", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SignedStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="zapret2-status-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.secret, self.public = root / "private.pem", root / "public.pem"
        self.msg, self.sig = root / "status.json", root / "status.sig"
        for args in (("genpkey", "-algorithm", "RSA", "-pkeyopt",
                      "rsa_keygen_bits:2048", "-out", str(self.secret)),
                     ("pkey", "-in", str(self.secret), "-pubout",
                      "-out", str(self.public))):
            subprocess.run(["/usr/bin/openssl", *args], check=True,
                           capture_output=True, timeout=20)
        self.pub = self.public.read_bytes()
        self.keysha = hashlib.sha256(self.pub).hexdigest()
        self.challenge = "c" * 64
        self.operation = "1" * 64
        self.payload = "a" * 64
        self.cp = "b" * 64
        self.now = 1800000000
        self.data = dict(schema=m.SCHEMA, repository=m.REPO,
                         issuer="CI_SIMULATED_WITNESS_NOT_OWNER_APPROVED",
                         operation_id=self.operation, payload_sha256=self.payload,
                         checkpoint_sha256=self.cp, checkpoint_sequence=6,
                         witness_sequence=9, challenge_sha256=self.challenge,
                         action="CONSUMED", issued_at=self.now - 10,
                         expires_at=self.now + 20)

    def seal(self, **update):
        data = dict(self.data, **update)
        raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return self.sign(raw)

    def sign(self, raw):
        self.msg.write_bytes(raw)
        subprocess.run(["/usr/bin/openssl", "dgst", "-sha256", "-sign",
                        str(self.secret), "-out", str(self.sig), str(self.msg)],
                       capture_output=True, check=True, timeout=10)
        return raw, self.sig.read_bytes()

    def verify(self, raw, sig, **expected):
        e = dict(expected_key_sha=self.keysha, challenge=self.challenge,
                 operation_id=self.operation, payload_sha=self.payload,
                 checkpoint_sha=self.cp, checkpoint_sequence=6,
                 witness_sequence=9, now=self.now)
        e.update(expected)
        return m.verify_response(raw, sig, self.pub, **e)

    def deny(self, code, raw, sig, **expected):
        with self.assertRaisesRegex(m.Refusal, code):
            self.verify(raw, sig, **expected)

    def test_exact_signed_consumed_reply_is_not_pkg_authority(self):
        raw, sig = self.seal()
        result = self.verify(raw, sig)
        self.assertEqual(result["operation_action"], "CONSUMED")
        self.assertTrue(result["signature_verified"])
        for key in ("production_pkg_authorized", "pkg_invoked", "nonce_one_use_proven",
                    "independent_remote_witness_deployed", "trusted_clock_proven",
                    "witness_latest_external_authoritative", "cross_store_pkg_atomicity_proven"):
            self.assertFalse(result[key])

    def test_signed_reserved_and_aborted_are_never_upgrade_grants(self):
        for state in ("RESERVED", "ABORTED"):
            with self.subTest(state=state):
                raw, sig = self.seal(action=state)
                self.assertEqual(self.verify(raw, sig)["operation_action"], state)

    def test_dropped_reply_replay_with_new_challenge_refused(self):
        raw, sig = self.seal()
        self.deny("STATUS_REQUEST_BINDING_MISMATCH:challenge_sha256", raw, sig,
                  challenge="d" * 64)
        # Replaying with the SAME challenge remains possible: there is no nonce ledger.
        self.assertFalse(self.verify(raw, sig)["nonce_one_use_proven"])

    def test_signed_wrong_operation_or_payload_refused(self):
        raw, sig = self.seal()
        self.deny("STATUS_REQUEST_BINDING_MISMATCH:operation_id", raw, sig,
                  operation_id="2" * 64)
        self.deny("STATUS_REQUEST_BINDING_MISMATCH:payload_sha256", raw, sig,
                  payload_sha="d" * 64)

    def test_wrong_latest_checkpoint_or_sequence_refused(self):
        raw, sig = self.seal()
        self.deny("STATUS_REQUEST_BINDING_MISMATCH:checkpoint_sha256", raw, sig,
                  checkpoint_sha="d" * 64)
        self.deny("STATUS_WITNESS_SEQUENCE_MISMATCH", raw, sig,
                  checkpoint_sequence=7)
        self.deny("STATUS_WITNESS_SEQUENCE_MISMATCH", raw, sig,
                  witness_sequence=10)

    def test_tamper_status_even_same_digest_inputs_refused(self):
        raw, sig = self.seal()
        self.deny("STATUS_RSA_SIGNATURE_INVALID", raw.replace(b'CONSUMED', b'RESERVED'), sig)

    def test_unsigned_or_forged_signature_refused(self):
        raw, sig = self.seal()
        self.deny("STATUS_RSA_SIGNATURE_INVALID", raw, b"forged")
        self.deny("STATUS_INPUT_SIZE_INVALID", raw, b"")

    def test_untrusted_key_or_public_pem_fingerprint_refused(self):
        raw, sig = self.seal()
        self.deny("STATUS_WITNESS_KEY_FINGERPRINT_MISMATCH", raw, sig,
                  expected_key_sha="d" * 64)
        with self.assertRaisesRegex(m.Refusal, "STATUS_INPUT_SIZE_INVALID"):
            m.verify_response(raw, sig, b"", self.keysha, self.challenge,
                              self.operation, self.payload, self.cp, 6, 9, self.now)

    def test_time_expiry_future_and_excessive_ttl(self):
        for kwargs in ({"now": self.now+21}, {"now": self.now-11}):
            raw, sig = self.seal()
            self.deny("STATUS_EXPIRED_FUTURE_OR_INVALID_WINDOW", raw, sig, **kwargs)
        raw, sig = self.seal(expires_at=self.now+500)
        self.deny("STATUS_EXPIRED_FUTURE_OR_INVALID_WINDOW", raw, sig)

    def test_untrusted_schema_action_and_boolean_sequence(self):
        for change in ({"issuer": "production-approved"}, {"action": "SUCCESS"},
                       {"action": []},
                       {"checkpoint_sequence": True}, {"witness_sequence": False},
                       {"repository": "foreign/repo"}):
            with self.subTest(change=change):
                raw, sig = self.seal(**change)
                with self.assertRaises(m.Refusal):
                    self.verify(raw, sig)

    def test_duplicate_key_and_nonfinite_json_refused_after_signature(self):
        raw, sig = self.sign((json.dumps(self.data)[0:-1] + ',"action":"CONSUMED"}').encode())
        self.deny("STATUS_DUPLICATE_JSON_KEY", raw, sig)
        raw, sig = self.sign((json.dumps(self.data)[0:-1] + ',"extra":NaN}').encode())
        self.deny("STATUS_NONFINITE_JSON_NUMBER", raw, sig)

    def test_source_has_no_pkg_network_or_operator_claim(self):
        source = SOURCE.read_text()
        for forbidden in ("pkg add", "pkg upgrade", "pkg delete", "socket.",
                          "urllib.request", "os.system(", "shell=True"):
            self.assertNotIn(forbidden, source)
        self.assertIn("CI_SIMULATED_WITNESS_NOT_OWNER_APPROVED", source)

    def test_cli_requires_opt_in_and_private_regular_files(self):
        raw, sig = self.seal()
        self.msg.chmod(0o600)
        self.sig.chmod(0o600)
        self.public.chmod(0o600)
        args = ["verify", self.keysha, self.challenge, self.operation, self.payload,
                self.cp, "6", "9", str(self.now), str(self.public), str(self.msg),
                str(self.sig)]
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(m.main(args), 78)
        with patch.dict(os.environ, {"ZAPRET2_CI_SIGNED_STATUS_ONLY": "1"}):
            self.assertEqual(m.main(args), 0)
            self.assertEqual(m.main(args[:3]), 78)
            self.msg.chmod(0o644)
            self.assertEqual(m.main(args), 78)
            self.msg.chmod(0o600)
            linked = self.msg.parent / "sym.json"
            linked.symlink_to(self.msg)
            args[-2] = str(linked)
            self.assertEqual(m.main(args), 78)


if __name__ == "__main__":
    unittest.main()
