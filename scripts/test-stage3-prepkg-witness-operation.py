#!/usr/bin/env python3
"""CI-only witness reservation tests: true POSIX locks, RSA, idempotent reads."""
import concurrent.futures
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "stage3_ci_witness_op",HERE/"stage3-prepkg-witness-operation.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
prev=importlib.util.spec_from_file_location(
    "stage3_ci_witness_fixture",HERE/"test-stage3-prepkg-monotonic-witness.py")
fixture_module=importlib.util.module_from_spec(prev)
prev.loader.exec_module(fixture_module)


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.WitnessProtocolTests(
            methodName="test_bootstrap_then_compare_current_not_production")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.init()
        self.sub=self.fixture.root/"ci-operation-subdir"
        self.sub.mkdir(mode=0o700)
        self.store=self.sub/"witness-store"  # same VM; NOT remote
        self.store.mkdir(mode=0o700)
        for key,value in (("monotonic",fixture_module.m),
                          ("ledger",fixture_module.m.ledger),
                          ("checkpoint",fixture_module.m.checkpoint)):
            p=patch.object(m,key,value)
            p.start()
            self.addCleanup(p.stop)
        m.initialize(str(self.store))
        self.opid="1"*64
        self.other="2"*64
        self.payload="a"*64
        self.second_payload="b"*64

    def call(self,action,op=None,payload=None,remote=None):
        return m.transition(action,str(self.store),
                            str(remote or self.fixture.store),
                            str(self.fixture.journal),self.fixture.keysha,
                            str(self.fixture.pub),str(self.fixture.doc),
                            str(self.fixture.sig),op or self.opid,
                            payload or self.payload)

    def files(self):
        return sorted(self.store.glob("operation-*.json"))

    def test_reserve_exact_latest_and_replay_idempotent_without_new_append(self):
        first=self.call("RESERVE")
        self.assertEqual(first["status"],"CI_OPERATION_RESERVE_NOT_PKG_AUTHORIZATION")
        self.assertEqual(first["checkpoint_sequence"],1)
        self.assertFalse(first["idempotent_replay"])
        self.assertFalse(first["production_pkg_authorized"])
        second=self.call("RESERVE")
        self.assertEqual(second["operation_id"],self.opid)
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(len(self.files()),1)

    def test_commit_then_lost_response_status_and_idempotent_retry(self):
        self.call("RESERVE")
        answer=self.call("CONSUME")
        self.assertEqual(answer["status"],"CI_OPERATION_CONSUME_NOT_PKG_AUTHORIZATION")
        # The caller drops its successful response, then queries exact op ID.
        observed=m.status(str(self.store),self.opid)
        self.assertEqual(observed["status"],answer["status"])
        self.assertEqual(observed["checkpoint_sha256"],answer["checkpoint_sha256"])
        retry=self.call("CONSUME")
        self.assertTrue(retry["idempotent_replay"])
        self.assertEqual(len(self.files()),2)
        self.assertFalse(retry["witness_and_local_spend_atomic"])

    def test_abort_terminal_and_late_consume_refusal(self):
        self.call("RESERVE")
        result=self.call("ABORT")
        self.assertEqual(result["status"],"CI_OPERATION_ABORT_NOT_PKG_AUTHORIZATION")
        self.assertTrue(self.call("ABORT")["idempotent_replay"])
        with self.assertRaisesRegex(m.Refusal,"OPERATION_TERMINAL_STATUS_CONFLICT"):
            self.call("CONSUME")
        self.assertEqual(len(self.files()),2)

    def test_abort_opens_checkpoint_for_new_unique_operation_only(self):
        self.call("RESERVE")
        self.call("ABORT")
        result=self.call("RESERVE",self.other,self.second_payload)
        self.assertEqual(result["operation_id"],self.other)
        self.assertEqual(len(self.files()),3)

    def test_different_payload_same_id_refused_even_after_consumed(self):
        self.call("RESERVE")
        with self.assertRaisesRegex(m.Refusal,"OPERATION_ID_REUSED_FOR_DIFFERENT_PAYLOAD"):
            self.call("RESERVE",payload=self.second_payload)
        self.call("CONSUME")
        with self.assertRaisesRegex(m.Refusal,"OPERATION_ID_REUSED_FOR_DIFFERENT_PAYLOAD"):
            self.call("CONSUME",payload=self.second_payload)

    def test_two_concurrent_real_operations_only_one_winner(self):
        def submit(op,payload):
            try:
                self.call("RESERVE",op,payload)
                return "PASS"
            except (m.Refusal,m.monotonic.Refusal) as exc:
                return "REFUSED:"+str(exc)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(lambda p:submit(*p),
                                 [(self.opid,self.payload),
                                  (self.other,self.second_payload)]))
        self.assertEqual(values.count("PASS"),1)
        self.assertEqual(sum(v.startswith("REFUSED") for v in values),1)
        self.assertEqual(len(self.files()),1)

    def test_no_new_id_can_reuse_consumed_same_witness_checkpoint(self):
        self.call("RESERVE")
        self.call("CONSUME")
        with self.assertRaisesRegex(m.Refusal,"OPERATION_CHECKPOINT_ALREADY_CONSUMED"):
            self.call("RESERVE",self.other,self.second_payload)

    def test_missing_witness_and_split_latest_fail_closed(self):
        missing=self.fixture.root/"missing"/"witness-store"
        with self.assertRaises(m.Refusal):
            self.call("RESERVE",remote=missing)
        self.assertEqual(len(self.files()),0)
        self.call("RESERVE")
        sha=self.fixture.next_record()
        self.fixture.publish(sha)
        with self.assertRaisesRegex(m.Refusal,"OPERATION_WITNESS_CHANGED_DURING_PENDING"):
            self.call("CONSUME")
        self.assertEqual(len(self.files()),1)

    def test_partial_exclusive_create_poison_blocks_all_mutation_and_lookup(self):
        self.call("RESERVE")
        target=self.store/("operation-000000000002-"+self.opid+".json")
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        os.close(fd)
        for func in (lambda:self.call("CONSUME"),
                     lambda:self.call("ABORT"),
                     lambda:m.status(str(self.store),self.opid)):
            with self.assertRaises(m.Refusal):
                func()
        self.assertEqual(target.stat().st_size,0)

    def test_local_root_removes_all_operation_records_replay_possible(self):
        # CI demonstration of missing independent nonrollbackable witness:
        # root can delete BOTH local event files and re-reserve old op ID.
        self.call("RESERVE")
        self.call("CONSUME")
        for path in self.files():
            path.unlink()
        accepted=self.call("RESERVE")
        self.assertEqual(accepted["status"],"CI_OPERATION_RESERVE_NOT_PKG_AUTHORIZATION")
        self.assertFalse(accepted["owner_approved_transaction"])

    def test_corruption_unknown_mode_and_interrupted_state_refused(self):
        self.call("RESERVE")
        entry=self.files()[0]
        saved=entry.read_bytes()
        entry.write_bytes(b'{"partial":')
        with self.assertRaises(m.Refusal):
            self.call("CONSUME")
        entry.write_bytes(saved)
        entry.chmod(0o666)
        with self.assertRaises(m.ledger.Refusal):
            m.status(str(self.store),self.opid)
        entry.chmod(0o600)
        extra=self.store/"unfinished.tmp"
        extra.write_text("bad")
        with self.assertRaisesRegex(m.Refusal,"OPERATION_UNKNOWN_OR_PARTIAL_ENTRY"):
            self.call("CONSUME")
        extra.unlink()
        self.assertEqual(m.status(str(self.store),self.opid)["operation_id"],
                         self.opid)

    def test_bad_operation_identity_legacy_args_and_no_pkg(self):
        for bad in ("0"*64,"not-a-digest","f"*63):
            with self.subTest(bad=bad),self.assertRaisesRegex(
                    m.Refusal,"OPERATION_ID_OR_PAYLOAD_SHA_INVALID"):
                self.call("RESERVE",op=bad)
        for args in ([],["upgrade"],["consume"],["reserve","x"],
                     ["status","x"],["initialize","x","y"]):
            self.assertEqual(m.main(args),78)
        source=(HERE/"stage3-prepkg-witness-operation.py").read_text()
        self.assertIn("OPERATION_WITNESS_UNAVAILABLE_OR_SPLIT",source)
        self.assertIn("OPERATION_TERMINAL_STATUS_CONFLICT",source)
        self.assertIn("OPERATION_CHECKPOINT_ALREADY_CONSUMED",source)
        for forbidden in ("subprocess.run(","pkg add","pkg upgrade",
                          "pkg delete","os.system(","urllib.request","socket."):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
