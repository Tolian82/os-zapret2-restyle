#!/usr/bin/env python3
"""Native kernel argv + executable pathname vs old sealed three-role launcher."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))

from voice_native_kernel_argv import (
    FreeBSDKernelArgvReader, KernelArgvError, inspect_native_kernel_argv,
    SYSTEM_PATHS,
)
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS
from voice_restart_argv_attestation import expected_engine_argv


def fixture(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


close=fixture("test-voice-cutover-close.py","kernel_gate_archive_fixture")


class KernelArgvGateTests(unittest.TestCase):
    def setUp(self):
        self.test=close.ArchiveWholeRollbackTests()
        self.test.setUp()
        self.addCleanup(self.test.doCleanups)
        self.test.archive()
        self.original=self.test.before
        self.real=self.test.fx.fx.fx.fx
        self.saved=self.real.fx.backup
        self.expected={
            "engine":expected_engine_argv(self.saved,EXPECTED_SCRIPTS["engine"]),
            **canonical_supervisor_argv(EXPECTED_SCRIPTS),
        }
        self.fake_argv={
            role:("\x00".join(self.expected[role])+"\x00").encode("ascii")
            for role in ("engine","daemon","monitor")
        }
        self.pids={"engine":201,"daemon":202,"monitor":203}
        self.fake_image={
            role:(SYSTEM_PATHS[role]+"\x00").encode("ascii")
            for role in self.pids
        }
        self.calls=[]
        self.reader=FreeBSDKernelArgvReader(
            raw_argv_reader=self.argv_reader,raw_path_reader=self.image_reader,
        )

    def argv_reader(self,pid):
        self.calls.append(("argv",pid))
        return self.fake_argv[next(r for r,v in self.pids.items() if v==pid)]

    def image_reader(self,pid):
        self.calls.append(("image",pid))
        return self.fake_image[next(r for r,v in self.pids.items() if v==pid)]

    def inspect(self,reader=None,lock=True):
        def callback(**kwargs):
            return inspect_native_kernel_argv(
                kernel_reader=self.reader if reader is None else reader,**kwargs,
            )
        return self.test.fx._do(callback,lock)

    def test_exact_kernel_argv_image_with_real_rollback_archive_and_two_pass(self):
        self.assertEqual("archived-awaiting-native-acceptance",
                         self.test.boot()["whole_closure"])
        result=self.inspect()
        self.assertEqual("kernel-argv-and-binary-match-previous-not-readiness",
                         result["state"])
        self.assertEqual(self.original["check"],result["whole_check"])
        self.assertEqual(self.pids,{role:item["pid"] for role,item
                                    in result["instances"].items()})
        self.assertFalse(result["safe_to_close_intent"])
        self.assertFalse(result["safe_to_start"])
        self.assertFalse(result["voice_on"])
        self.assertFalse(result["media_pass"])
        self.assertEqual(12,len(self.calls))
        self.assertEqual(self.original["previous"],self.test.before["previous"])
        self.assertIsNone(self.test.journal.read())
        self.assertIs(self.test.guard()["safe_to_mutate"],False)

    def test_postboot_epoch_changed_but_identical_argv_is_only_observation(self):
        self.real.state["engine"]["process"]["start_ns"]+=1000000000
        self.real.state["supervisor"]["daemon"]["start_ns"]+=1000000000
        self.real.state["supervisor"]["monitor"]["start_ns"]+=1000000000
        boot=self.test.boot()
        self.assertNotEqual("process-epoch-matches-not-readiness",
                            boot["previous_receipt"])
        result=self.inspect()
        self.assertEqual("kernel-argv-and-binary-match-previous-not-readiness",
                         result["state"])
        self.assertFalse(result["safe_to_start"])
        self.assertFalse(result["voice_on"])

    def test_refuses_kernel_arg_mutation_per_role(self):
        for role in self.pids:
            with self.subTest(role=role):
                old=self.fake_argv[role]
                self.fake_argv[role]=old[:-1]+b"--unexpected\x00"
                with self.assertRaises((ValueError,RuntimeError,OSError)):
                    self.inspect()
                self.fake_argv[role]=old

    def test_refuses_foreign_kernel_image_and_unterminated_or_nonascii(self):
        for role in self.pids:
            old=self.fake_image[role]
            self.fake_image[role]=b"/bin/foreign\x00"
            with self.assertRaises((ValueError,RuntimeError,OSError)):
                self.inspect()
            self.fake_image[role]=old
        self.fake_argv["engine"]=self.fake_argv["engine"][:-1]
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect()
        self.fake_argv["engine"]=b"\xff\x00"
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect()

    def test_mutation_between_kernel_samples_is_rejected(self):
        counter={"n":0}
        def change_on_read(pid):
            counter["n"]+=1
            if counter["n"]==4:
                self.fake_argv["engine"]=b"/bin/foreign\x00"
            return self.argv_reader(pid)
        sample=FreeBSDKernelArgvReader(
            raw_argv_reader=change_on_read,raw_path_reader=self.image_reader,
        )
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect(sample)
        self.assertIs(self.test.guard()["safe_to_mutate"],False)

    def test_process_epoch_race_between_ps_samples_refuses(self):
        def race(pid):
            if pid==203:
                self.real.state["supervisor"]["monitor"]["start_ns"]+=999999
            return self.argv_reader(pid)
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect(FreeBSDKernelArgvReader(
                raw_argv_reader=race,raw_path_reader=self.image_reader,
            ))

    def test_flock_and_ipfw_kernel_preflight_mandatory(self):
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect(lock=False)
        k=self.real.kernel
        old=k.rules.get(19000)
        k.rules[19000]=close.f.roots.prune_fixture.reclaim_fixture.fixtures.receipt_tests.kernel_fixture.TCP
        try:
            with self.assertRaises((ValueError,RuntimeError,OSError)):
                self.inspect()
        finally:
            if old is None:
                k.rules.pop(19000,None)
            else:
                k.rules[19000]=old

    def test_sealed_runtime_args_changed_does_not_accept(self):
        self.real.live.joinpath("dvtws.args").write_text("--port=999\n")
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect()
        self.assertIs(self.test.guard()["safe_to_mutate"],False)


if __name__=="__main__":
    unittest.main(verbosity=2)
