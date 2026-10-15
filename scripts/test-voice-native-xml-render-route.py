#!/usr/bin/env python3
"""Root-private saved XML -> actual OPNsense template -> native PREPARED route."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_native_prepare_route as route
from voice_native_recovery_quiescence import _locked_config


class NativeXmlProducerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="voice-xml-producer-")
        self.addCleanup(t.cleanup)
        base=Path(t.name)
        self.live=base/"config.xml"
        self.live.write_text("<opnsense/>")
        self.live.chmod(0o600)
        self.runtime=base/"active-runtime"
        self.runtime.mkdir(mode=0o700)
        self.build=base/"voice-build-input"
        self.build.mkdir(mode=0o700)
        (self.build/"config.xml").write_text("<opnsense/>")
        (self.build/"config.xml").chmod(0o600)
        self.input=base/"voice-operator-input"
        self.whole=base/"voice-cutover"
        self.ledger=base/"voice-ipfw"
        self.render=base/"render.sh"
        self.render.write_text("#!/bin/sh\nexit 0\n")
        self.worker=base/"worker.sh"
        self.worker.write_text("#!/bin/sh\nexit 0\n")
        self.actions=[]
        patches=[
            patch.object(route,"BUILD_INPUT",self.build),
            patch.object(route,"INPUT",self.input),
            patch.object(route,"RENDER_WORKER",self.render),
            patch.object(route,"BUILD_WORKER",self.worker),
            patch.object(route.native,"CONFIG",self.live),
            patch.object(route.native,"ACTIVE_ROOT",self.runtime),
            patch.object(route.native,"WHOLE",self.whole),
            patch.object(route.native,"LEDGER",self.ledger),
            patch.object(route.native,"require_native_lock",lambda:self.actions.append("FD9")),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def build_input(self,**kwargs):
        self.assertEqual(self.build/"config.xml",kwargs["source_config"])
        self.assertEqual(self.build/"release",kwargs["staged_release"])
        self.assertEqual(self.input,kwargs["destination"])
        self.assertEqual("vtnet1",kwargs["physical_wan"])
        _locked_config(self.live,kwargs["config_fd"],kwargs["config_owner"])
        self.actions.append("operator-input")
        self.input.mkdir(mode=0o700)
        for name in route.FILES:
            (self.input/name).write_text("0")
            (self.input/name).chmod(0o600)
        for name in route.DIRS:
            (self.input/name).mkdir(mode=0o755 if name=="runtime" else 0o700)
        return {"state":"native-voice-detached-operator-input-published",
                "safe_to_enable_voice":False,"public_voice_apply":False}

    def prepared(self,**kwargs):
        _locked_config(self.live,kwargs["config_fd"],kwargs["config_owner"])
        self.assertEqual(self.input/"config.xml",kwargs["source_config"])
        self.actions.append("schema4-PREPARED")
        return {"state":"native-voice-original-lock-prepared",
                "safe_to_enable_voice":False,"public_voice_apply":False}

    def subprocess(self,cmd,**kwargs):
        self.assertTrue(kwargs["check"])
        fds=kwargs["pass_fds"]
        self.assertIn(9,fds)
        candidate_fds=[fd for fd in fds if fd!=9]
        self.assertEqual(1,len(candidate_fds))
        _locked_config(self.live,candidate_fds[0],(os.geteuid(),os.getegid()))
        if cmd == ["/bin/sh",str(self.render)]:
            self.assertEqual({"config.xml"},set(os.listdir(self.build)))
            (self.build/".voice-template-root").mkdir(mode=0o700)
            (self.build/"zapret.conf").write_text('ZAPRET_ENABLED="1"')
            (self.build/"zapret.conf").chmod(0o600)
            self.actions.append("opnsense-jinja")
        elif cmd == ["/bin/sh",str(self.worker)]:
            self.assertEqual(set(route.RENDERED_ENTRIES),set(os.listdir(self.build)))
            (self.build/".voice-build-workspace").mkdir(mode=0o700)
            (self.build/"release").mkdir(mode=0o700)
            self.actions.append("orchestrator")
        else:
            self.fail("unexpected native worker command")
        return subprocess.CompletedProcess(cmd,0)

    def test_template_release_prepare_share_one_original_config_flock(self):
        with patch.object(route.subprocess,"run",side_effect=self.subprocess), \
             patch.object(route,"require_saved_pair",return_value=None), \
             patch.object(route,"stage_native_operator_input",side_effect=self.build_input), \
             patch.object(route,"prepare_native_voice_one_lock",side_effect=self.prepared):
            state=route.prepare_operator_prebuilt("vtnet1",989,from_xml=True)
        self.assertEqual("native-voice-original-lock-prepared",state["state"])
        self.assertEqual(["opnsense-jinja","orchestrator","operator-input","schema4-PREPARED"],
                         [name for name in self.actions if name!="FD9"])
        self.assertEqual("<opnsense/>",self.live.read_text())

    def test_renderer_failure_never_builds_or_claims_previous_resources(self):
        with patch.object(route.subprocess,"run",
                          side_effect=subprocess.CalledProcessError(69,["/bin/sh"])) as runner, \
             patch.object(route,"stage_native_operator_input") as stage, \
             patch.object(route,"prepare_native_voice_one_lock") as prepared:
            with self.assertRaises(route.NativePrepareRouteError):
                route.prepare_operator_prebuilt("vtnet1",989,from_xml=True)
        self.assertEqual(1,runner.call_count)
        stage.assert_not_called()
        prepared.assert_not_called()
        self.assertFalse(self.input.exists())
        self.assertFalse(self.whole.exists())

    def test_foreign_saved_input_fails_before_any_worker(self):
        (self.build/"foreign").write_text("wrong")
        with patch.object(route.subprocess,"run") as runner:
            with self.assertRaises((RuntimeError,ValueError,OSError)):
                route.prepare_operator_prebuilt("vtnet1",989,from_xml=True)
        runner.assert_not_called()
        self.assertFalse(self.whole.exists())

    def test_template_renderer_is_isolated_not_live_config_reload(self):
        sh=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/voice_native_render_saved.sh").read_text()
        self.assertIn("template_ctl.py",sh)
        self.assertIn('"${SOURCE}/config.xml" -r "${ROOT}" OPNsense/Zapret',sh)
        commands="\n".join(
            line for line in sh.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("configctl template reload",commands)
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        configd=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        # Old isolated XML producer remains source-testable but its retired
        # operator command is not shipped or exposed by the normal service.
        self.assertNotIn("native-voice-prepare-xml)",service)
        self.assertNotIn("native-voice-prepare-xml",service.split("start|stop|restart|reconfigure",1)[-1])
        self.assertNotIn("native-voice-prepare-xml",configd)
        build=(ROOT/"scripts/build-pkg.sh").read_text()
        self.assertIn('rm "${PREPARE_ROUTE}"',build)


if __name__=="__main__":
    unittest.main(verbosity=2)
