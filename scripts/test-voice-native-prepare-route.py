#!/usr/bin/env python3
"""Operator native Voice route under one real Config FD9 simulation, no GUI."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_native_prepare_route as route
from voice_native_recovery_quiescence import _locked_config


class OperatorPrepareRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="voice-operator-prebuilt-")
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.input=base/"voice-operator-input"
        self.input.mkdir(mode=0o700)
        self.config=base/"config.xml"
        self.config.write_text("<opnsense/>")
        self.config.chmod(0o600)
        self.live=base/"runtime-live"
        self.live.mkdir(mode=0o700)
        self.whole=base/"voice-cutover"
        self.ledger=base/"voice-ipfw"
        self.calls=[]
        self.patches=[
            patch.object(route,"INPUT",self.input),
            patch.object(route.native,"CONFIG",self.config),
            patch.object(route.native,"ACTIVE_ROOT",self.live),
            patch.object(route.native,"WHOLE",self.whole),
            patch.object(route.native,"LEDGER",self.ledger),
            patch.object(route.native,"require_native_lock",lambda:self.calls.append("FD9")),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def input_files(self):
        for name in route.FILES:
            (self.input/name).write_text("0")
            (self.input/name).chmod(0o600)
        for name in route.DIRS:
            (self.input/name).mkdir(mode=0o700)

    def test_real_original_config_inode_flock_reaches_operator_coordinator(self):
        self.input_files()
        observed=[]
        def prepare(**kwargs):
            fd=kwargs["config_fd"]
            self.assertEqual(self.config,Path(kwargs["config_path"]))
            _locked_config(self.config,fd,kwargs["config_owner"])
            self.assertEqual(self.input/"voice-native-candidate",kwargs["release_dir"])
            self.assertEqual(self.input/"runtime",kwargs["source_runtime"])
            self.assertEqual(self.input/"config.xml",kwargs["source_config"])
            self.assertEqual("vtnet1",kwargs["physical_wan"])
            self.assertEqual(989,kwargs["divert_port"])
            self.assertIs(kwargs["security_reader"].probe,kwargs["probe"])
            observed.append(os.fstat(fd).st_ino)
            return {"state":"native-voice-original-lock-prepared",
                    "safe_to_enable_voice":False,"public_voice_apply":False}
        with patch.object(route,"prepare_native_voice_one_lock",side_effect=prepare):
            result=route.prepare_operator_prebuilt("vtnet1",989)
        self.assertEqual("native-voice-original-lock-prepared",result["state"])
        self.assertEqual([self.config.stat().st_ino],observed)
        self.assertGreaterEqual(len(self.calls),3)
        self.assertTrue(self.whole.is_dir())
        self.assertTrue(self.ledger.is_dir())
        self.assertEqual(self.config.read_text(),"<opnsense/>")

    def test_incomplete_source_refuses_before_ledger_or_original_config_open(self):
        self.input_files()
        (self.input/"tcp-ports.txt").unlink()
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989)
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_untrusted_operator_source_symlink_and_extra_file_denied(self):
        self.input_files()
        (self.input/"runtime").rmdir()
        (self.input/"runtime").symlink_to(self.live)
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989)
        self.assertFalse(self.ledger.exists())
        (self.input/"runtime").unlink()
        (self.input/"runtime").mkdir(mode=0o700)
        (self.input/"unknown").write_text("bad")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989)
        self.assertFalse(self.whole.exists())

    def test_invalid_wan_and_divert_rejected_before_any_file_action(self):
        for wan,port in (("vtnet1;",989),("vtnet1",0),("vtnet1",65536)):
            with self.subTest(wan=wan,port=port):
                with self.assertRaises((OSError,ValueError,RuntimeError)):
                    route.prepare_operator_prebuilt(wan,port)
        self.assertEqual([],self.calls)
        self.assertFalse(self.whole.exists())

    def test_shell_route_is_fd9_operator_only_not_configd(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        configd=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        self.assertIn("native_voice_prepare_prebuilt_service()",service)
        self.assertIn("native-voice-prepare-prebuilt)",service)
        locked=service.split("case \"${1:-}\" in",1)[-1]
        self.assertIn("native-voice-prepare-prebuilt|native-voice-apply-prepared",locked)
        self.assertNotIn("[voice_prepare_prebuilt]",configd)
        self.assertNotIn("native-voice-prepare-prebuilt",configd)


if __name__=="__main__":
    unittest.main(verbosity=2)
