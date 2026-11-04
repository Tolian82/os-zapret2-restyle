#!/usr/bin/env python3
"""Off-target manual record/inspection contracts; no trust root is invented."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "stage3-prepkg-operator-approval.py"
spec = importlib.util.spec_from_file_location("operator_pins", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fake_root_stat(original):
    fields = list(original)
    fields[4] = 0
    return os.stat_result(fields)


class OperatorApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.receipt = self.root / "operator-pins.json"
        self.filenames = (m.EXPECTED_BASENAMES +
            ("os-zapret2-restyle-0.6.2_111.pkg", "os-zapret2-restyle-0.6.2_1.pkg"))
        self.bytes = (b"print('seed')\n", b"print('verifier')\n",
                      b"public-key-fixture-not-a-signer\n",
                      b"candidate-archive-bytes", b"old-archive-bytes")
        self.paths = [self.root / filename for filename in self.filenames]
        for path, raw in zip(self.paths, self.bytes):
            path.write_bytes(raw)
            path.chmod(0o600)
        self.pins = {
            "seed_sha256": digest(self.bytes[0]),
            "verifier_sha256": digest(self.bytes[1]),
            "public_key_sha256": digest(self.bytes[2]),
            "source_commit": "a" * 40,
            "incoming_version": "0.6.2_111",
            "incoming_sha256": digest(self.bytes[3]),
            "predecessor_version": "0.6.2_1",
            "predecessor_sha256": digest(self.bytes[4]),
        }
        self.original_fstat = os.fstat
        self.original_lstat = os.lstat

    def no_platform(self):
        return patch.object(m, "qualify_runtime")

    def physical(self):
        # GitHub ubuntu-latest user is unprivileged and /tmp is not /root.
        # Retain real file descriptors, bytes, symlink/mode and inode checks,
        # spoof only UID and private-path ancestry. Native FreeBSD does neither.
        from contextlib import ExitStack
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(self.no_platform())
        stack.enter_context(patch.object(m, "private_path", return_value=str(self.root)))
        stack.enter_context(patch.object(m.os, "fstat",
                side_effect=lambda fd: fake_root_stat(self.original_fstat(fd))))
        stack.enter_context(patch.object(m.os, "lstat",
                side_effect=lambda path: fake_root_stat(self.original_lstat(path))))
        return stack

    def write_record(self, pins=None):
        fields = dict(self.pins if pins is None else pins)
        blob = dict(fields, schema=m.SCHEMA, repository=m.REPOSITORY,
                    trust_status=m.TRUST_STATUS)
        self.receipt.write_text(json.dumps(blob, sort_keys=True, separators=(",", ":")) + "\n")
        self.receipt.chmod(0o600)

    def test_schema_digests_versions_and_commit_enforced(self):
        self.assertEqual(m.validate_pins(self.pins), self.pins)
        for field, wrong in (("source_commit", "NOT-A-COMMIT"),
                             ("seed_sha256", "0" * 64),
                             ("verifier_sha256", "g" * 64),
                             ("incoming_version", "../0.6.2_111"),
                             ("predecessor_sha256", "0" * 64)):
            changed = dict(self.pins, **{field: wrong})
            with self.subTest(field=field), self.assertRaises(m.Refusal):
                m.validate_pins(changed)
        with self.assertRaises(m.Refusal):
            m.validate_pins(dict(self.pins, unexpected="unknown"))
        with self.assertRaises(m.Refusal):
            m.validate_pins(dict(self.pins, predecessor_version="0.6.2_111"))

    def test_record_requires_real_tty_and_no_unauthorized_write(self):
        with self.no_platform(), patch.object(m.sys, "stdin",
                types.SimpleNamespace(isatty=lambda: False)):
            with self.assertRaisesRegex(m.Refusal, "REAL_INTERACTIVE_OPERATOR_TTY_REQUIRED"):
                m.record_receipt(str(self.receipt))
        self.assertFalse(self.receipt.exists())

    def test_manual_record_needs_explicit_challenge_and_no_overwrite(self):
        self.physical()
        tokens = [self.pins[x] for x in m.PIN_FIELDS]
        challenge = "APPROVE " + self.pins["source_commit"] + " " + self.pins["incoming_version"]
        with patch.object(m.sys, "stdin", types.SimpleNamespace(isatty=lambda: True)), \
             patch.object(m.sys, "stdout", types.SimpleNamespace(isatty=lambda: True)):
            wrong = iter(tokens + ["NO"])
            with self.assertRaisesRegex(m.Refusal, "EXPLICIT_OPERATOR_CONFIRMATION_REQUIRED"):
                m.record_receipt(str(self.receipt), prompt=lambda _: next(wrong))
            self.assertFalse(self.receipt.exists())
            values = iter(tokens + [challenge])
            report = m.record_receipt(str(self.receipt),
                                      prompt=lambda _: next(values))
            self.assertEqual(report["status"], "PASS_MANUAL_PINS_RECORDED_ONLY")
            self.assertFalse(report["operator_source_authenticated"])
            self.assertFalse(report["pkg_authorized"])
            self.assertEqual(stat.S_IMODE(self.receipt.stat().st_mode), 0o600)
            original = self.receipt.read_bytes()
            values = iter(tokens + [challenge])
            with self.assertRaisesRegex(m.Refusal, "OPERATOR_RECEIPT_EXISTS_OR_UNSAFE"):
                m.record_receipt(str(self.receipt), prompt=lambda _: next(values))
            self.assertEqual(original, self.receipt.read_bytes())

    def test_readonly_inspect_matches_all_five_private_bytes(self):
        self.write_record()
        self.physical()
        result = m.inspect_receipt(str(self.receipt), list(map(str, self.paths)))
        self.assertEqual(result["status"], "PASS_RECORDED_PINS_AND_PRIVATE_BYTES_ONLY")
        for key in ("operator_source_authenticated", "signer_authenticated",
                    "signed_manifest_verified", "old_owner_qualified",
                    "supported_entrypoint_implemented", "pkg_invoked",
                    "pkg_authorized", "lh08_ac11_accepted"):
            self.assertIs(result[key], False)

    def test_mutated_seed_verifier_key_or_archives_fail_closed(self):
        self.write_record()
        self.physical()
        for i, path in enumerate(self.paths):
            with self.subTest(name=path.name):
                raw = path.read_bytes()
                path.write_bytes(raw + b"\nATTACKER")
                with self.assertRaisesRegex(m.Refusal, "OPERATOR_PIN_SHA256_MISMATCH"):
                    m.inspect_receipt(str(self.receipt), list(map(str, self.paths)))
                path.write_bytes(raw)

    def test_receipt_duplicate_key_foreign_identity_and_status_refused(self):
        self.write_record()
        self.physical()
        original = self.receipt.read_bytes()
        for changed in (
            original.rstrip()[:-1] + b',"seed_sha256":"1"}',
            original.replace(m.REPOSITORY.encode(), b"attacker/other"),
            original.replace(m.TRUST_STATUS.encode(), b"PKG_AUTHORIZED"),
        ):
            with self.subTest(changed=changed[:35]):
                self.receipt.write_bytes(changed)
                with self.assertRaises(m.Refusal):
                    m.inspect_receipt(str(self.receipt), list(map(str, self.paths)))
        self.receipt.write_bytes(original)

    def test_unsafe_receipt_mode_and_symlink_rejected(self):
        self.write_record()
        self.physical()
        self.receipt.chmod(0o666)
        with self.assertRaisesRegex(m.Refusal, "MODE_OR_SIZE_REFUSED"):
            m.inspect_receipt(str(self.receipt), list(map(str, self.paths)))
        self.receipt.unlink()
        self.receipt.symlink_to(self.paths[0])
        with self.assertRaises(m.Refusal):
            m.inspect_receipt(str(self.receipt), list(map(str, self.paths)))

    def test_private_path_rejects_traversal_and_wrong_basename(self):
        for path in ("/tmp/operator-pins.json",
                     "/root/../tmp/operator-pins.json",
                     "/root//operator-pins.json",
                     "/root/other.json", "operator-pins.json"):
            with self.subTest(path=path), self.assertRaises(m.Refusal):
                m.private_path(path, "operator-pins.json")

    def test_no_automatic_pins_or_package_mutation_commands(self):
        source = SOURCE.read_text()
        for bad in ("pkg add", "pkg upgrade", "pkg delete", "pkg install",
                    "subprocess.run(", "os.system(", "exec("):
            self.assertNotIn(bad, source)
        for args in (["upgrade"], ["install"], ["record"], ["inspect"],
                     ["issue-production-signer", "/root/operator-pins.json"]):
            with patch.object(m.sys, "stderr",
                              __import__("io").StringIO()) as stderr:
                self.assertEqual(m.main(args), 78)
                self.assertIn("READ_ONLY_RECORD_OR_INSPECT_ONLY", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
