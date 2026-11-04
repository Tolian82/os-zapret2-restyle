#!/usr/bin/env python3
"""Off-target real RSA checkpoint tests; do not claim an external trust root."""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"stage3-prepkg-checkpoint-witness.py"
spec=importlib.util.spec_from_file_location("ci_witness", SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ORIGINAL_PRIVATE_INPUT=m.private_input


@contextlib.contextmanager
def private_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


class CheckpointWitnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="zapret2-116-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.journal=self.root/"approval-ledger"
        self.journal.mkdir(mode=0o700)
        self.key=self.root/"ci-witness-private.pem"
        self.public=self.root/m.PUBLIC
        self.snapshot=self.root/m.CHECKPOINT
        self.signature=self.root/m.SIGNATURE
        self.authority="a"*64
        self.scratch=self.root/"scratch"
        self.scratch.mkdir(mode=0o700)
        for args in (["genpkey","-algorithm","RSA","-pkeyopt",
                      "rsa_keygen_bits:2048","-out",str(self.key)],
                     ["pkey","-in",str(self.key),"-pubout",
                      "-out",str(self.public)]):
            subprocess.run(["/usr/bin/openssl",*args],
                           capture_output=True,check=True,timeout=20)
        self.keysha=hashlib.sha256(self.public.read_bytes()).hexdigest()
        original_temp=tempfile.TemporaryDirectory
        def make_temp(*args,**kw):
            kw["dir"]=str(self.scratch)
            return original_temp(*args,**kw)
        def file_data(path,kind):
            return {m.PUBLIC:self.public,m.CHECKPOINT:self.snapshot,
                    m.SIGNATURE:self.signature}[kind].read_bytes()
        for p in (patch.object(m.ledger,"qualify_runtime"),
                  patch.object(m.ledger,"private_root",side_effect=private_directory),
                  patch.object(m.ledger,"root_owner",return_value=True),
                  patch.object(m,"private_input",side_effect=file_data),
                  patch.object(m.tempfile,"TemporaryDirectory",
                               side_effect=make_temp)):
            p.start()
            self.addCleanup(p.stop)
        m.ledger.initialize(str(self.journal))
        self.spend(1,"b"*64,"c"*64)
        self.spend(2,"d"*64,"e"*64)
        self.latest=self.seal(2)

    def spend(self,sequence,receipt,policy):
        return m.ledger.consumption(str(self.journal),self.authority,
                                    policy,receipt,sequence)

    def entry(self,sequence):
        path=sorted(self.journal.glob("spent-*.json"))[sequence-1]
        return path,json.loads(path.read_bytes())

    def seal(self,journal_sequence,**changes):
        path,record=self.entry(journal_sequence)
        doc={"schema":m.SCHEMA,"repository":m.ledger.REPO,
             "sequence":journal_sequence,
             "head_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
             "authority_sha256":record["authority_sha256"],
             "receipt_sha256":record["receipt_sha256"],
             "policy_sha256":record["policy_sha256"]}
        doc.update(changes)
        self.snapshot.write_bytes(
            (json.dumps(doc,sort_keys=True,separators=(",",":"))+"\n").encode())
        self.sign()
        return hashlib.sha256(self.snapshot.read_bytes()).hexdigest()

    def sign(self):
        subprocess.run(["/usr/bin/openssl","dgst","-sha256","-sign",
                        str(self.key),"-out",str(self.signature),
                        str(self.snapshot)],capture_output=True,
                       check=True,timeout=15)

    def verify(self,checkpoint=None,key=None):
        return m.verify(str(self.journal),key if key is not None else self.keysha,
                        str(self.public),
                        checkpoint if checkpoint is not None else self.latest,
                        str(self.snapshot),str(self.signature))

    def deny(self,reason,checkpoint=None,key=None):
        with self.assertRaisesRegex(m.Refusal,reason):
            self.verify(checkpoint,key)

    def test_genuine_rsa_and_exact_latest_head(self):
        status=self.verify()
        self.assertEqual(status["checkpoint_sequence"],2)
        self.assertTrue(status["signature_verified"])
        for field in ("checkpoint_out_of_band_latest_authenticated",
                      "witness_signer_owner_approved",
                      "witness_external_independent_storage",
                      "root_rollback_resistance_proven",
                      "production_one_use_pkg_gate","pkg_invoked"):
            self.assertFalse(status[field])

    def test_delete_last_entry_leaves_valid_local_chain_but_refuses(self):
        path,_=self.entry(2)
        payload=path.read_bytes()
        path.unlink()
        self.assertEqual(m.ledger.inspect(str(self.journal))["spent"],1)
        self.deny("WITNESS_LEDGER_SEQUENCE_OR_HEAD_ROLLBACK")
        path.write_bytes(payload)
        path.chmod(0o600)
        self.verify()

    def test_signed_mismatch_head_and_last_receipt(self):
        current=self.seal(2,head_sha256="f"*64)
        self.deny("WITNESS_LEDGER_SEQUENCE_OR_HEAD_ROLLBACK",current)
        current=self.seal(2,receipt_sha256="f"*64)
        self.deny("WITNESS_LEDGER_LAST_ENTRY_IDENTITY_MISMATCH",current)

    def test_old_signed_checkpoint_does_not_match_latest_pin(self):
        older=self.seal(1)
        self.deny("WITNESS_LATEST_CHECKPOINT_SHA_MISMATCH")
        self.deny("WITNESS_LEDGER_SEQUENCE_OR_HEAD_ROLLBACK",older)

    def test_full_rollback_with_unanchored_old_sha_is_still_possible(self):
        old=self.seal(1)
        path,_=self.entry(2)
        bytes_before=path.read_bytes()
        path.unlink()
        self.deny("WITNESS_LATEST_CHECKPOINT_SHA_MISMATCH")
        replay=self.verify(old)
        self.assertEqual(replay["checkpoint_sequence"],1)
        self.assertFalse(replay["checkpoint_out_of_band_latest_authenticated"])
        self.assertFalse(replay["root_rollback_resistance_proven"])
        path.write_bytes(bytes_before)
        path.chmod(0o600)

    def test_changed_checkpoint_and_forged_signature(self):
        self.snapshot.write_bytes(self.snapshot.read_bytes()+b"ATTACKER")
        self.deny("WITNESS_LATEST_CHECKPOINT_SHA_MISMATCH")
        newly_claimed=hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        self.deny("WITNESS_CHECKPOINT_RSA_SIGNATURE_INVALID",newly_claimed)
        self.seal(2)
        self.signature.write_bytes(b"forged")
        self.deny("WITNESS_CHECKPOINT_RSA_SIGNATURE_INVALID")

    def test_wrong_or_untrusted_key_fingerprint(self):
        self.deny("WITNESS_OUT_OF_BAND_KEY_SHA_REQUIRED",key="0"*64)
        self.deny("WITNESS_PUBLIC_KEY_SHA_MISMATCH",key="f"*64)
        self.public.write_bytes(b"attacker public PEM")
        self.deny("WITNESS_PUBLIC_KEY_SHA_MISMATCH")

    def test_signed_invalid_schema_integer_and_duplicate_key(self):
        for changes,reason in (
            ({"sequence":True},"WITNESS_SEQUENCE_NOT_POSITIVE_INTEGER"),
            ({"schema":"wrong"},"WITNESS_CHECKPOINT_SCHEMA_OR_REPOSITORY"),
            ({"repository":"other"},"WITNESS_CHECKPOINT_SCHEMA_OR_REPOSITORY"),
            ({"head_sha256":"0"*64},"WITNESS_CHECKPOINT_BAD_DIGEST")):
            with self.subTest(reason=reason):
                sha=self.seal(2,**changes)
                self.deny(reason,sha)
        self.seal(2)
        raw=self.snapshot.read_bytes()
        self.snapshot.write_bytes(raw.rstrip(b"\n")[:-1]+b',"sequence":3}')
        self.sign()
        sha=hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        self.deny("WITNESS_CHECKPOINT_LEDGER_DUPLICATE_JSON_KEY",sha)

    def test_private_path_and_no_legacy_cli(self):
        for p in ("/tmp/"+m.PUBLIC,"relative/"+m.PUBLIC,
                  "/root/../tmp/"+m.PUBLIC,"/root//"+m.PUBLIC,
                  "/root/not-key.pem","/root/folder/"+m.PUBLIC+"/"):
            with self.subTest(path=p),self.assertRaises(m.Refusal):
                ORIGINAL_PRIVATE_INPUT(p,m.PUBLIC)
        for args in ([],["upgrade"],["verify"],["consume","root"]):
            self.assertEqual(m.main(args),78)

    def test_never_pkg_or_production_witness(self):
        source=SOURCE.read_text()
        self.assertEqual(source.count("subprocess.run("),1)
        self.assertIn("ledger.entries_locked(fd)",source)
        self.assertIn("ledger.lock_ledger(fd)",source)
        for term in ("WITNESS_LATEST_CHECKPOINT_SHA_MISMATCH",
                     "checkpoint_out_of_band_latest_authenticated",
                     "root_rollback_resistance_proven"):
            self.assertIn(term,source)
        for bad in ("pkg add","pkg upgrade","pkg delete","os.execv(",
                    "os.system(","os.rename("):
            self.assertNotIn(bad,source)


if __name__=="__main__":
    unittest.main()
