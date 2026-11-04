#!/usr/bin/env python3
"""Off-target source-only receipt-to-first-executable seed contracts."""
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SEED = HERE / "stage3-prepkg-trust-seed.py"
CODE = SEED.read_text()


def definitions():
    tree = ast.parse(CODE, str(SEED))
    assert isinstance(tree.body[-1], ast.Try)
    tree.body.pop()
    module = types.ModuleType("receipt_bound_trust_seed")
    exec(compile(tree, str(SEED), "exec"), module.__dict__)
    return module


def spoof_root(st):
    fields = list(st)
    fields[4] = 0
    return os.stat_result(fields)


def pins():
    return {
        "schema": "zapret2-prepkg-operator-pins-v1",
        "repository": "Tolian82/os-zapret2-restyle",
        "trust_status": "PINS_RECORDED_NOT_AUTHENTICATED",
        "seed_sha256": "a" * 64,
        "verifier_sha256": "b" * 64,
        "public_key_sha256": "c" * 64,
        "source_commit": "1" * 40,
        "incoming_version": "0.6.2_112",
        "incoming_sha256": "d" * 64,
        "predecessor_version": "0.6.2_1",
        "predecessor_sha256": "e" * 64,
    }


def argv():
    return ["-c", "--operator-receipt", "/root/review/operator-pins.json",
            "--operator-authority", "f" * 64,
            "/root/review/operator-approval-authority.pem",
            "/root/review/operator-pins.sig",
            "--approval-policy", "9" * 64,
            "/root/review/operator-approval-policy.json",
            "/root/review/operator-approval-policy.sig",
            "--verified-verifier", "/root/review/stage3-prepkg-verified-eval.py",
            "--signed-provenance", "/root/review/approved-public.pem",
            "/root/review/claims.json", "/root/review/sig",
            "/root/review/native-prepkg-standalone.py", "inspect-predecessor",
            "/root/review/os-zapret2-restyle-0.6.2_112.pkg", "0.6.2_112",
            "/root/review/os-zapret2-restyle-0.6.2_1.pkg", "0.6.2_1"]


class TrustSeedContracts(unittest.TestCase):
    def setUp(self):
        self.m = definitions()

    def test_no_pkg_mutation_or_untrusted_imports(self):
        self.assertIn("os.O_NOFOLLOW", CODE)
        self.assertIn("hmac.compare_digest", CODE)
        self.assertIn("exec(compiled,", CODE)
        self.assertIn("RECEIPT_PINS_BOUND_NOT_AUTHENTICATED", CODE)
        self.assertIn("OPERATOR_RECEIPT_REVOKED_IN_POLICY", CODE)
        self.assertIn("OPERATOR_APPROVAL_AUTHORITY_REVOKED_IN_POLICY", CODE)
        self.assertIn('["/usr/bin/openssl", "dgst", "-sha256", "-verify", public,', CODE)
        self.assertEqual(CODE.count("subprocess.run("), 1)
        for forbidden in ("pkg add", "pkg upgrade", "os.system(",
                          "os.execv(", "operator_source_authenticated=True"):
            self.assertNotIn(forbidden, CODE)

    def test_actual_c_rejects_legacy_and_mutating_argv(self):
        for tail in ([], ["upgrade"], ["--verified-verifier"],
                     ["--verified-verifier", "a" * 64,
                      "/root/review/stage3-prepkg-verified-eval.py",
                      "--expected-source-commit", "1" * 40,
                      "--signed-provenance", "b" * 64,
                      "/root/review/key.pem", "claims", "sig", "cli",
                      "inspect-predecessor", "incoming", "v", "old", "old-v"],
                     argv()[1:] + ["upgrade"]):
            with self.subTest(tail=tail[:3]):
                result = subprocess.run([sys.executable, "-I", "-B", "-c", CODE,
                                         *tail], capture_output=True,
                                        text=True, timeout=12)
                self.assertEqual(result.returncode, 78)
                self.assertIn("SIGNED_READ_ONLY_VERIFIER_COMMAND_REQUIRED",
                              result.stderr)
                self.assertNotIn("VERIFIED_SHA256:", result.stderr)

    def test_root_verifier_aliases_rejected(self):
        for bad in ("relative.py", "/tmp/stage3-prepkg-verified-eval.py",
                    "/root/../tmp/stage3-prepkg-verified-eval.py",
                    "/root//stage3-prepkg-verified-eval.py",
                    "/root/not-verifier.py"):
            with self.subTest(path=bad), self.assertRaises(SystemExit):
                self.m.trusted_root_path(bad)

    def test_receipt_root_path_denial_before_open(self):
        for bad in ("relative.json", "/tmp/operator-pins.json",
                    "/root/../tmp/operator-pins.json",
                    "/root//operator-pins.json", "/root/other.json",
                    "/root/review/operator-pins.json/"):
            with self.subTest(path=bad), \
                 patch.object(self.m.os, "open") as opened, \
                 self.assertRaises(SystemExit):
                self.m.operator_receipt(
                    bad, "f"*64, "/root/review/operator-approval-authority.pem",
                    "/root/review/operator-pins.sig", "9"*64,
                    "/root/review/operator-approval-policy.json",
                    "/root/review/operator-approval-policy.sig")
            opened.assert_not_called()

    def test_single_fd_receipt_and_schema_refusals(self):
        raw_open, raw_lstat, raw_fstat = os.open, os.lstat, os.fstat
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "review"
            root.mkdir(mode=0o700)
            record = root / "operator-pins.json"
            def lstat(path):
                if path == "/root":
                    return spoof_root(raw_lstat(td))
                if path == "/root/review":
                    return spoof_root(raw_lstat(root))
                if path == "/root/review/operator-pins.json":
                    return spoof_root(raw_lstat(record))
                return spoof_root(raw_lstat(path))
            def openfile(path, flags, *args, **kw):
                if path == "/root/review/operator-pins.json":
                    return raw_open(record, flags, *args, **kw)
                return raw_open(path, flags, *args, **kw)
            def write(data):
                record.unlink(missing_ok=True)
                record.write_bytes(data)
                record.chmod(0o600)
            valid = pins()
            with patch.object(self.m, "verify_detached_receipt",
                              return_value=True) as detached, \
                 patch.object(self.m, "verified_approval_policy",
                              return_value={"status": "read-only"}) as approved, \
                 patch.object(self.m.os, "lstat", side_effect=lstat), \
                 patch.object(self.m.os, "fstat",
                              side_effect=lambda fd: spoof_root(raw_fstat(fd))), \
                 patch.object(self.m.os, "open", side_effect=openfile):
                write(json.dumps(valid).encode())
                self.assertEqual(
                    self.m.operator_receipt("/root/review/operator-pins.json",
                                            "f"*64,
                                            "/root/review/operator-approval-authority.pem",
                                            "/root/review/operator-pins.sig",
                                            "9"*64,
                                            "/root/review/operator-approval-policy.json",
                                            "/root/review/operator-approval-policy.sig"),
                    valid)
                self.assertEqual(approved.call_count, 1)
                self.assertEqual(detached.call_count, 1)
                failures = [
                    json.dumps(dict(valid, source_commit="z" * 40)).encode(),
                    json.dumps(dict(valid, trust_status="AUTHENTICATED")).encode(),
                    json.dumps(dict(valid, repository="different/repo")).encode(),
                    json.dumps(dict(valid, public_key_sha256="0" * 64)).encode(),
                    json.dumps(dict(valid, incoming_version="0.6.2_1")).encode(),
                    json.dumps(valid).encode().rstrip().rstrip(b"}") +
                        b',"source_commit":"2"}',
                    b"not-json",
                    b" " * 4096,
                ]
                for data in failures:
                    with self.subTest(raw=data[:50]):
                        write(data)
                        with self.assertRaises(SystemExit) as exit_code:
                            self.m.operator_receipt(
                                "/root/review/operator-pins.json", "f"*64,
                                "/root/review/operator-approval-authority.pem",
                                "/root/review/operator-pins.sig", "9"*64,
                                "/root/review/operator-approval-policy.json",
                                "/root/review/operator-approval-policy.sig")
                        self.assertEqual(exit_code.exception.code, 78)
                write(json.dumps(valid).encode())
                record.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.operator_receipt(
                        "/root/review/operator-pins.json", "f"*64,
                        "/root/review/operator-approval-authority.pem",
                        "/root/review/operator-pins.sig", "9"*64,
                        "/root/review/operator-approval-policy.json",
                        "/root/review/operator-approval-policy.sig")
                record.unlink()
                record.symlink_to(root / "somewhere")
                with self.assertRaises(SystemExit):
                    self.m.operator_receipt(
                        "/root/review/operator-pins.json", "f"*64,
                        "/root/review/operator-approval-authority.pem",
                        "/root/review/operator-pins.sig", "9"*64,
                        "/root/review/operator-approval-policy.json",
                        "/root/review/operator-approval-policy.sig")

    def test_real_detached_rsa_and_pinned_separate_authority(self):
        # Independent test-only RSA key, never a production signer. A truly
        # signed receipt is needed before the verifier source can execute.
        original_temp = tempfile.TemporaryDirectory
        with original_temp(prefix="zapret113-rsa-") as td:
            root = Path(td)
            private = root / "ci-only-private.pem"
            public = root / "operator-approval-authority.pem"
            signed = root / "operator-pins.sig"
            message = json.dumps(pins(), sort_keys=True,
                                 separators=(",", ":")).encode()
            payload = root / "receipt.json"
            payload.write_bytes(message)
            subprocess.run(["/usr/bin/openssl", "genpkey", "-algorithm", "RSA",
                            "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)],
                           capture_output=True, check=True, timeout=15)
            subprocess.run(["/usr/bin/openssl", "pkey", "-in", str(private),
                            "-pubout", "-out", str(public)],
                           capture_output=True, check=True, timeout=15)
            subprocess.run(["/usr/bin/openssl", "dgst", "-sha256",
                            "-sign", str(private), "-out", str(signed),
                            str(payload)], capture_output=True,
                           check=True, timeout=15)
            authority_sha = hashlib.sha256(public.read_bytes()).hexdigest()

            def key_bytes(path, expected_basename):
                self.assertIn(expected_basename,
                              ("operator-approval-authority.pem", "operator-pins.sig"))
                return (public if expected_basename.endswith(".pem") else signed).read_bytes()

            def temp_root(*args, **kwargs):
                kwargs["dir"] = td
                return original_temp(*args, **kwargs)

            with patch.object(self.m, "authority_file", side_effect=key_bytes), \
                 patch.object(self.m.tempfile, "TemporaryDirectory",
                              side_effect=temp_root):
                self.assertTrue(self.m.verify_detached_receipt(
                    message, authority_sha, str(public), str(signed)))
                for wrong, data in (("changed bytes", message+b" "),
                                    ("changed claim", message.replace(b"0.6.2_112", b"0.6.2_999"))):
                    with self.subTest(reason=wrong), \
                         self.assertRaises(SystemExit):
                        self.m.verify_detached_receipt(
                            data, authority_sha, str(public), str(signed))
                with self.assertRaises(SystemExit):
                    self.m.verify_detached_receipt(
                        message, "0" * 64, str(public), str(signed))
                with self.assertRaises(SystemExit):
                    self.m.verify_detached_receipt(
                        message, "f" * 64, str(public), str(signed))
                tampered = signed.read_bytes()
                signed.write_bytes(b"bad detached signature")
                with self.assertRaises(SystemExit):
                    self.m.verify_detached_receipt(
                        message, authority_sha, str(public), str(signed))
                signed.write_bytes(tampered)
                self.assertTrue(self.m.verify_detached_receipt(
                    message, authority_sha, str(public), str(signed)))

    def test_operator_authority_path_traversal_rejected(self):
        for path in ("/tmp/operator-approval-authority.pem",
                     "/root/../tmp/operator-approval-authority.pem",
                     "/root/review/../operator-approval-authority.pem",
                     "/root/review/other.pem",
                     "/root//operator-approval-authority.pem",
                     "/root/operator-pins.sig/"):
            with self.subTest(path=path), \
                 self.assertRaises(SystemExit):
                self.m.authority_file(path, "operator-approval-authority.pem")

    def test_malformed_or_identical_operator_and_provenance_authority_refused(self):
        args = argv()
        data = pins()
        data["public_key_sha256"] = args[4]
        with patch.object(self.m.sys, "argv", args), \
             patch.object(self.m.os, "geteuid", return_value=0), \
             patch.object(self.m.os, "uname",
                          return_value=types.SimpleNamespace(sysname="FreeBSD",
                                                             machine="amd64")), \
             patch.object(self.m, "operator_receipt", return_value=data), \
             patch.object(self.m, "verified_verifier") as verifier, \
             self.assertRaises(SystemExit):
            self.m.main()
        verifier.assert_not_called()


    def test_signed_policy_current_receipt_and_revocation_negative_matrix(self):
        now = 1800000000
        receipt_bytes = json.dumps(pins(), sort_keys=True).encode()
        receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
        authority = "f" * 64
        expected = {
            "schema": "zapret2-prepkg-approval-policy-v1",
            "repository": "Tolian82/os-zapret2-restyle",
            "authority_sha256": authority,
            "receipt_sha256": receipt_sha,
            "sequence": 7, "issued_at": now-10,
            "not_before": now-10, "not_after": now+3500,
            "revoked_receipt_sha256": [], "revoked_authority_sha256": [],
        }
        verified = []
        def exercise(policy, when=now, sha_override=None, raw_override=None):
            raw = json.dumps(policy, sort_keys=True,
                             separators=(",", ":")).encode() if raw_override is None else raw_override
            digest = hashlib.sha256(raw).hexdigest()
            with patch.object(self.m, "authority_file", return_value=raw), \
                 patch.object(self.m, "verify_detached_receipt",
                              side_effect=lambda *a, **kw: verified.append(a) or True), \
                 patch.object(self.m.time, "time", return_value=when):
                return self.m.verified_approval_policy(
                    receipt_bytes, authority,
                    "/root/review/operator-approval-authority.pem",
                    digest if sha_override is None else sha_override,
                    "/root/review/operator-approval-policy.json",
                    "/root/review/operator-approval-policy.sig")
        self.assertEqual(exercise(expected), expected)
        self.assertEqual(verified[-1][0],
                         json.dumps(expected,sort_keys=True,separators=(",",":")).encode())
        bad = (
            (dict(expected, revoked_receipt_sha256=[receipt_sha]),
             "OPERATOR_RECEIPT_REVOKED_IN_POLICY"),
            (dict(expected, revoked_authority_sha256=[authority]),
             "OPERATOR_APPROVAL_AUTHORITY_REVOKED_IN_POLICY"),
            (dict(expected, receipt_sha256="b" * 64),
             "APPROVAL_POLICY_WRONG_IDENTITY_OR_RECEIPT"),
            (dict(expected, authority_sha256="b" * 64),
             "APPROVAL_POLICY_WRONG_IDENTITY_OR_RECEIPT"),
            (dict(expected, not_after=now-1),
             "APPROVAL_POLICY_NOT_CURRENT"),
            (dict(expected, not_before=now+100, issued_at=now+100,
                  not_after=now+1000),
             "APPROVAL_POLICY_NOT_CURRENT"),
            (dict(expected, not_after=now+5000),
             "APPROVAL_POLICY_UNBOUNDED_OR_INVALID_WINDOW"),
            (dict(expected, sequence=True),
             "APPROVAL_POLICY_NONINTEGER:sequence"),
            (dict(expected, sequence=0),
             "APPROVAL_POLICY_UNBOUNDED_OR_INVALID_WINDOW"),
            (dict(expected, revoked_receipt_sha256=[receipt_sha, receipt_sha]),
             "APPROVAL_POLICY_BAD_REVOKE_LIST:revoked_receipt_sha256"),
            (dict(expected, revoked_authority_sha256=["bad-hash"]),
             "APPROVAL_POLICY_BAD_REVOKE_LIST:revoked_authority_sha256"),
            (dict(expected, schema="wrong-schema"),
             "APPROVAL_POLICY_WRONG_IDENTITY_OR_RECEIPT"),
        )
        for case, reason in bad:
            with self.subTest(reason=reason), self.assertRaises(SystemExit):
                exercise(case)
        with self.assertRaises(SystemExit):
            exercise(expected, sha_override="0"*64)
        with self.assertRaises(SystemExit):
            exercise(expected, sha_override="a"*64)
        malformed = (
            b"not-json",
            json.dumps(expected).encode().rstrip(b"}")+
                b',"sequence":8}',
        )
        for raw in malformed:
            with self.subTest(raw=raw[:40]), self.assertRaises(SystemExit):
                exercise(expected,raw_override=raw)

    def test_actual_signed_policy_real_rsa_and_missing_signature(self):
        # A second standalone signed snapshot is mandatory. This RSA pair
        # is ephemeral and does not independently authenticate any owner.
        original_temp = tempfile.TemporaryDirectory
        with original_temp(prefix="zapret114-policy-") as folder:
            root = Path(folder)
            key = root/"key.pem"
            pub = root/"operator-approval-authority.pem"
            sig = root/"operator-approval-policy.sig"
            raw = b'{"schema":"zapret2-prepkg-approval-policy-v1"}\n'
            snapshot = root/"operator-approval-policy.json"
            snapshot.write_bytes(raw)
            for cmd in (
                ["/usr/bin/openssl", "genpkey", "-algorithm","RSA",
                 "-pkeyopt","rsa_keygen_bits:2048","-out",str(key)],
                ["/usr/bin/openssl", "pkey", "-in",str(key),
                 "-pubout","-out",str(pub)],
                ["/usr/bin/openssl", "dgst","-sha256","-sign",str(key),
                 "-out",str(sig),str(snapshot)],
            ):
                subprocess.run(cmd,check=True,capture_output=True,timeout=20)
            digest = hashlib.sha256(pub.read_bytes()).hexdigest()
            def source(path, filename):
                if filename.endswith(".pem"):return pub.read_bytes()
                if filename.endswith(".sig"):return sig.read_bytes()
                raise AssertionError(filename)
            def tempdir(*args,**kw):
                kw["dir"]=folder
                return original_temp(*args,**kw)
            with patch.object(self.m,"authority_file",side_effect=source), \
                 patch.object(self.m.tempfile,"TemporaryDirectory",
                              side_effect=tempdir):
                self.assertTrue(self.m.verify_detached_receipt(
                    raw,digest,str(pub),str(sig),
                    self.m.POLICY_SIGNATURE_BASENAME))
                with self.assertRaises(SystemExit):
                    self.m.verify_detached_receipt(
                        raw+b"x",digest,str(pub),str(sig),
                        self.m.POLICY_SIGNATURE_BASENAME)
                sig.write_bytes(b"forged")
                with self.assertRaises(SystemExit):
                    self.m.verify_detached_receipt(
                        raw,digest,str(pub),str(sig),
                        self.m.POLICY_SIGNATURE_BASENAME)

    def test_verified_verifier_bytes_freeze_and_tamper_refusal(self):
        raw_fstat, raw_lstat = os.fstat, os.lstat
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "stage3-prepkg-verified-eval.py"
            code = b'print("VERIFIED_ONLY")\n'
            script.write_bytes(code)
            script.chmod(0o600)
            digest = hashlib.sha256(code).hexdigest()
            with patch.object(self.m, "trusted_root_path"), \
                 patch.object(self.m.os, "fstat",
                              side_effect=lambda fd: spoof_root(raw_fstat(fd))), \
                 patch.object(self.m.os, "lstat",
                              side_effect=lambda p: spoof_root(raw_lstat(p))):
                self.assertEqual(
                    self.m.verified_verifier(str(script), digest), code)
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(script), "0" * 64)
                script.write_bytes(b"print('ATTACKER')\n")
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(script), digest)
                script.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(
                        str(script), hashlib.sha256(script.read_bytes()).hexdigest())
                script.unlink()
                script.symlink_to(Path(td) / "other")
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(script), digest)

    def test_receipt_target_version_refuses_before_verifier(self):
        args = argv()
        args[20] = "0.6.2_999"
        with patch.object(self.m.sys, "argv", args), \
             patch.object(self.m.os, "geteuid", return_value=0), \
             patch.object(self.m.os, "uname", return_value=types.SimpleNamespace(
                 sysname="FreeBSD", machine="amd64")), \
             patch.object(self.m, "operator_receipt", return_value=pins()), \
             patch.object(self.m, "verified_verifier") as source, \
             self.assertRaises(SystemExit) as refusal:
            self.m.main()
        self.assertEqual(refusal.exception.code, 78)
        source.assert_not_called()

    def test_seed_exec_receipt_derived_values_without_caller_pins(self):
        args = argv()
        stdout, stderr = io.StringIO(), io.StringIO()
        original = list(self.m.sys.argv)
        try:
            with patch.object(self.m.sys, "argv", list(args)), \
                 patch.object(self.m.os, "geteuid", return_value=0), \
                 patch.object(self.m.os, "uname", return_value=types.SimpleNamespace(
                     sysname="FreeBSD", machine="amd64")), \
                 patch.object(self.m, "operator_receipt", return_value=pins()) as receipt, \
                 patch.object(self.m, "verified_verifier",
                     return_value=b'import sys; print("VERIFIED_EXEC", sys.argv)\n') as verifier, \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.m.main()
            receipt.assert_called_once_with(args[2], args[4], args[5], args[6],
                                            args[8], args[9], args[10])
            verifier.assert_called_once_with(args[12], pins()["verifier_sha256"])
            self.assertIn("VERIFIED_EXEC", stdout.getvalue())
            self.assertIn("--expected-source-commit", stdout.getvalue())
            self.assertIn(pins()["source_commit"], stdout.getvalue())
            self.assertIn("--expected-archive-pins", stdout.getvalue())
            self.assertIn(pins()["incoming_sha256"], stdout.getvalue())
            self.assertIn(pins()["predecessor_sha256"], stdout.getvalue())
            self.assertIn(pins()["public_key_sha256"], stdout.getvalue())
            self.assertNotIn("--operator-receipt", stdout.getvalue())
            self.assertNotIn("--operator-authority", stdout.getvalue())
            self.assertNotIn("--approval-policy", stdout.getvalue())
            self.assertIn("SIGNED_POLICY_TIME_AND_REVOCATION_MATCHED_NOT_ONE_USE",
                          stderr.getvalue())
            self.assertIn("RECEIPT_RSA_VERIFIED_ANCHOR_NOT_OWNER_AUTHENTICATED",
                          stderr.getvalue())
            self.assertNotIn("--verified-verifier", stdout.getvalue())
            self.assertIn("RECEIPT_PINS_BOUND_NOT_AUTHENTICATED", stderr.getvalue())
        finally:
            self.m.sys.argv = original


if __name__ == "__main__":
    unittest.main()
