#!/usr/bin/env python3
"""CI-only CAS witness: real locks, signed checkpoints, races and rollback."""
import concurrent.futures
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
SOURCE=HERE/"stage3-prepkg-monotonic-witness.py"
spec=importlib.util.spec_from_file_location("ci_monotonic_witness",SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ORIGINAL_CANONICAL_ROOT=m.canonical_root


class WitnessProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="zapret2-117-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.journal=self.root/"approval-ledger"
        self.journal.mkdir(mode=0o700)
        self.store=self.root/"witness-store"
        self.store.mkdir(mode=0o700)
        self.scratch=self.root/"rsa-private-scratch"
        self.scratch.mkdir(mode=0o700)
        self.private=self.root/"test-private.pem"
        self.pub=self.root/m.checkpoint.PUBLIC
        self.doc=self.root/m.checkpoint.CHECKPOINT
        self.sig=self.root/m.checkpoint.SIGNATURE
        for cmd in (
            ["genpkey","-algorithm","RSA",
             "-pkeyopt","rsa_keygen_bits:2048","-out",str(self.private)],
            ["pkey","-in",str(self.private),
             "-pubout","-out",str(self.pub)],
        ):
            subprocess.run(["/usr/bin/openssl",*cmd],capture_output=True,
                           check=True,timeout=20)
        self.keysha=hashlib.sha256(self.pub.read_bytes()).hexdigest()
        original_temp=tempfile.TemporaryDirectory
        def temp_factory(*a,**kw):
            kw["dir"]=str(self.scratch)
            return original_temp(*a,**kw)
        def private_bytes(path,name):
            return {m.checkpoint.PUBLIC:self.pub,
                    m.checkpoint.CHECKPOINT:self.doc,
                    m.checkpoint.SIGNATURE:self.sig}[name].read_bytes()
        def native_local_directory(path):
            from contextlib import contextmanager
            @contextmanager
            def opened():
                fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    yield fd
                finally:
                    os.close(fd)
            return opened()
        for p in (patch.object(m.ledger,"qualify_runtime"),
                  patch.object(m.ledger,"private_root",
                               side_effect=native_local_directory),
                  patch.object(m.ledger,"root_owner",return_value=True),
                  patch.object(m,"canonical_root"),
                  patch.object(m.checkpoint,"private_input",
                               side_effect=private_bytes),
                  patch.object(m.checkpoint.tempfile,"TemporaryDirectory",
                               side_effect=temp_factory)):
            p.start()
            self.addCleanup(p.stop)
        self.authority="a"*64
        self.spend(1,"b"*64,"c"*64)
        self.first=self.sign(1)

    def spend(self,index,receipt,policy):
        return m.ledger.consumption(str(self.journal),self.authority,
                                    policy,receipt,index) if index>1 else (
            m.ledger.initialize(str(self.journal)),
            m.ledger.consumption(str(self.journal),self.authority,
                                 policy,receipt,1))[1]

    def entry(self,seq):
        path=sorted(self.journal.glob("spent-*.json"))[seq-1]
        return path,json.loads(path.read_bytes())

    def sign(self,seq,**override):
        path,record=self.entry(seq)
        body={"schema":m.checkpoint.SCHEMA,
              "repository":m.ledger.REPO,"sequence":seq,
              "head_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
              "authority_sha256":record["authority_sha256"],
              "policy_sha256":record["policy_sha256"],
              "receipt_sha256":record["receipt_sha256"]}
        body.update(override)
        self.doc.write_bytes((json.dumps(body,sort_keys=True,
                              separators=(",",":"))+"\n").encode())
        subprocess.run(["/usr/bin/openssl","dgst","-sha256","-sign",
                        str(self.private),"-out",str(self.sig),str(self.doc)],
                       check=True,capture_output=True,timeout=15)
        return hashlib.sha256(self.doc.read_bytes()).hexdigest()

    def init(self):
        return m.bootstrap(str(self.store),str(self.journal),self.keysha,
                           str(self.pub),self.first,str(self.doc),str(self.sig))

    def compare(self):
        return m.compare(str(self.store),str(self.journal),self.keysha,
                         str(self.pub),str(self.doc),str(self.sig))

    def publish(self,sha,seq=1,prior=None):
        return m.publish(str(self.store),str(self.journal),self.keysha,
                         str(self.pub),sha,str(self.doc),str(self.sig),
                         seq,prior or self.first)

    def next_record(self):
        self.spend(2,"d"*64,"e"*64)
        return self.sign(2)

    def test_bootstrap_then_compare_current_not_production(self):
        boot=self.init()
        self.assertEqual(boot["status"],"CI_WITNESS_BOOTSTRAP_UNTRUSTED_LOCAL_ONLY")
        report=self.compare()
        self.assertEqual(report["sequence"],1)
        self.assertEqual(report["checkpoint_sha256"],self.first)
        for flag in ("witness_latest_independently_anchored",
                     "witness_root_rollback_resistant",
                     "witness_remote_service_deployed",
                     "cross_store_atomic_transaction_implemented",
                     "production_pkg_authorized","pkg_invoked"):
            self.assertFalse(report[flag])
        with self.assertRaisesRegex(m.Refusal,"ALREADY_BOOTSTRAPPED"):
            self.init()

    def test_advance_cas_and_compare_latest_without_caller_sha(self):
        self.init()
        second=self.next_record()
        with self.assertRaises(m.Refusal):
            self.compare()  # Local ahead; remote still seq1
        result=self.publish(second)
        self.assertEqual(result["sequence"],2)
        self.assertEqual(self.compare()["checkpoint_sha256"],second)
        with self.assertRaisesRegex(m.Refusal,"CAS_STALE_OR_CONCURRENT"):
            self.publish(second)
        self.assertEqual(len(list(self.store.glob("state-*"))),2)

    def test_two_real_simultaneous_publications_only_one_wins(self):
        self.init()
        sha=self.next_record()
        def run_one(_):
            try:
                self.publish(sha)
                return "PASS"
            except m.Refusal:
                return "REFUSED"
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(run_one,range(2)))
        self.assertEqual(result.count("PASS"),1)
        self.assertEqual(result.count("REFUSED"),1)
        self.assertEqual(self.compare()["sequence"],2)

    def test_local_tail_rollback_refused_by_store_latest(self):
        self.init()
        sha=self.next_record()
        self.publish(sha)
        path,_=self.entry(2)
        saved=path.read_bytes()
        path.unlink()
        self.assertEqual(m.ledger.inspect(str(self.journal))["spent"],1)
        self.sign(1)
        with self.assertRaises(m.Refusal):
            self.compare()
        path.write_bytes(saved)
        path.chmod(0o600)
        self.sign(2)
        self.assertEqual(self.compare()["sequence"],2)

    def test_full_root_rollback_of_both_stores_still_possible(self):
        self.init()
        sha=self.next_record()
        self.publish(sha)
        old_record=self.store/"state-000000000002.json"
        old_record.unlink()
        path,_=self.entry(2)
        path.unlink()
        self.sign(1)
        # Deliberate counterexample: same VM root can restore both past states.
        report=self.compare()
        self.assertEqual(report["sequence"],1)
        self.assertFalse(report["witness_root_rollback_resistant"])
        self.assertFalse(report["witness_latest_independently_anchored"])

    def test_absent_service_or_missing_state_fails_closed(self):
        self.init()
        missing=self.root/"missing"/"witness-store"
        with self.assertRaises(OSError):
            m.compare(str(missing),str(self.journal),self.keysha,
                      str(self.pub),str(self.doc),str(self.sig))
        # An actual command must return 78, not success, for an unreachable
        # witness (no fallback to a locally supplied hash).
        args=["compare",str(missing),str(self.journal),self.keysha,
              str(self.pub),str(self.doc),str(self.sig)]
        self.assertEqual(m.main(args),78)
        (self.store/"state-000000000001.json").unlink()
        with self.assertRaisesRegex(m.Refusal,"UNINITIALIZED_OR_TOO_MANY"):
            self.compare()

    def test_partial_remote_append_poison_blocks_all(self):
        self.init()
        sha=self.next_record()
        with m.directory(str(self.store)) as fd,m.exclusive(fd):
            entries,prev=m.records(fd)
            with self.assertRaisesRegex(m.Refusal,"INJECTED_INTERRUPTED_APPEND"):
                m.write_record(fd,2,2,sha,
                    json.loads(self.doc.read_bytes())["head_sha256"],
                    self.keysha,prev,fail_after_create=True)
        with self.assertRaises(m.Refusal):
            self.compare()
        with self.assertRaises(m.Refusal):
            self.publish(sha)
        self.assertEqual((self.store/"state-000000000002.json").stat().st_size,0)

    def test_invalid_or_corrupt_remote_history_refused(self):
        self.init()
        item=self.store/"state-000000000001.json"
        original=item.read_bytes()
        item.write_bytes(b'{"broken":')
        with self.assertRaises(m.Refusal):
            self.compare()
        item.write_bytes(original)
        item.chmod(0o666)
        with self.assertRaises(m.ledger.Refusal):
            self.compare()
        item.chmod(0o600)
        extra=self.store/"attacker.tmp"
        extra.write_bytes(b"x")
        with self.assertRaisesRegex(m.Refusal,"UNKNOWN_OR_PARTIAL"):
            self.compare()
        extra.unlink()
        self.assertEqual(self.compare()["sequence"],1)

    def test_unapproved_key_and_wrong_expected_cas_refuse(self):
        self.init()
        sha=self.next_record()
        with self.assertRaisesRegex(m.Refusal,"CAS_STALE_OR_CONCURRENT"):
            self.publish(sha,prior="f"*64)
        with self.assertRaisesRegex(m.Refusal,"SIGNER_ROTATION_UNAPPROVED"):
            m.publish(str(self.store),str(self.journal),"f"*64,str(self.pub),
                      sha,str(self.doc),str(self.sig),1,self.first)
        self.pub.write_bytes(b"attacker")
        with self.assertRaises(m.Refusal):
            self.publish(sha)

    def test_unsigned_or_wrong_checkpoint_cannot_advance(self):
        self.init()
        sha=self.next_record()
        self.sig.write_bytes(b"forged")
        with self.assertRaises(m.Refusal):
            self.publish(sha)
        self.assertEqual(len(list(self.store.glob("state-*"))),1)
        self.assertEqual(m.ledger.inspect(str(self.journal))["last_sequence"],2)

    def test_private_root_and_bad_commands_refuse(self):
        for path in ("/tmp/witness-store","relative/witness-store",
                     "/root/../tmp/witness-store","/root//witness-store",
                     "/root/other","/root/x/witness-store/"):
            with self.subTest(path=path),self.assertRaises(m.Refusal):
                ORIGINAL_CANONICAL_ROOT(path)
        for args in ([],["pkg"],["compare"],["publish","x"],
                     ["bootstrap"],["compare","a","b"]):
            self.assertEqual(m.main(args),78)

    def test_source_never_calls_native_pkg_or_network(self):
        src=SOURCE.read_text()
        self.assertIn("fcntl.flock(opened,fcntl.LOCK_EX|fcntl.LOCK_NB)",src)
        self.assertIn("os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW",src)
        self.assertIn("os.fsync(output)",src)
        self.assertIn("REMOTE_WITNESS_CAS_STALE_OR_CONCURRENT",src)
        self.assertIn("witness_latest_independently_anchored",src)
        for forbidden in ("subprocess.run(","pkg add","pkg upgrade",
                          "pkg delete","os.execv(","os.system(",
                          "requests.","urllib.request","socket."):
            self.assertNotIn(forbidden,src)


if __name__=="__main__":
    unittest.main()
