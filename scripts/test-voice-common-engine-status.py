#!/usr/bin/env python3
"""Real production common-runtime status function with isolated process evidence.

No subprocess, PID, firewall or kernel mutation in tests. This verifies
all five Voice profile reports remain bound to one common release engine.
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_live_inspect import (
    inspect_common_runtime, VoiceInspectError, SERVICES,
    _same_installed_file, _native_process_matches,
)

class CommonRuntimeEvidence(unittest.TestCase):
    def plan(self, root, selected=("telegram",)):
        release=Path(root)/"release"
        release.mkdir()
        (release/"dvtws.args").write_text("--filter-udp=443\n")
        (release/"voice-plan.json").write_text(json.dumps({
            "schema":1,
            "profiles":[{"service":x,"enabled":True} for x in selected],
            "capture":{"voice":[{"service":x} for x in selected]},
        }))
        manifest={"tables":{f"zapret2_voice_{x}":["91.108.13.10"] for x in selected}}
        return release,manifest

    def run_probe(self, release,manifest,engine,monitor,matched=True):
        evidence=[]
        def process(path,exe):
            evidence.append(exe)
            return engine if "dvtws2" in exe else monitor
        result=inspect_common_runtime(
            release,manifest,active=release,
            installed_match=lambda a,b: matched and a.name==b.name,
            process_check=process)
        self.assertEqual(2,len(evidence))
        return result

    def test_all_five_enabled_share_single_running_engine(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root,SERVICES)
            result=self.run_probe(rel,manifest,True,True)
            self.assertEqual("running",result["state"])
            self.assertTrue(result["source_verified"])
            self.assertTrue(result["engine_verified"])
            self.assertTrue(result["supervisor_verified"])
            self.assertFalse(result["call_verified"])
            self.assertEqual(set(SERVICES),set(result["services"]))
            for service in SERVICES:
                report=result["services"][service]
                self.assertTrue(report["configured"])
                self.assertTrue(report["capture_verified"])
                self.assertEqual("engine-present",report["runtime_state"])
                self.assertFalse(report["media_verified"])

    def test_disabled_four_services_are_not_running_daemons(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            result=self.run_probe(rel,manifest,True,True)
            self.assertEqual("engine-present",result["services"]["telegram"]["runtime_state"])
            for name in SERVICES:
                if name!="telegram":
                    self.assertEqual("disabled",result["services"][name]["runtime_state"])
                    self.assertFalse(result["services"][name]["configured"])
                    self.assertFalse(result["services"][name]["media_verified"])

    def test_stopped_or_partial_engine_cannot_claim_voice(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            for engine,supervisor,expected in (
                (False,False,"stopped"),(True,False,"partial"),(False,True,"partial")
            ):
                with self.subTest(engine=engine,supervisor=supervisor):
                    report=self.run_probe(rel,manifest,engine,supervisor)
                    self.assertEqual(expected,report["state"])
                    self.assertEqual("engine-not-confirmed",
                                     report["services"]["telegram"]["runtime_state"])

    def test_source_drift_never_reports_confirmed_runtime(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            result=self.run_probe(rel,manifest,True,True,matched=False)
            self.assertEqual("unverified-release",result["state"])
            self.assertFalse(result["source_verified"])
            self.assertFalse(result["engine_verified"])
            self.assertFalse(result["supervisor_verified"])

    def test_profile_capture_and_kernel_disagreement_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            manifest["tables"]["zapret2_voice_discord"]=["8.8.8.8"]
            with self.assertRaisesRegex(VoiceInspectError,"disagreement"):
                self.run_probe(rel,manifest,True,True)
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            path=rel/"voice-plan.json"
            original=json.loads(path.read_text())
            original["profiles"].append({"service":"telegram","enabled":True})
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(VoiceInspectError,"disagreement"):
                self.run_probe(rel,manifest,True,True)

    def test_unavailable_plan_does_not_fabricate_enabled_services(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            (rel/"voice-plan.json").unlink()
            with self.assertRaisesRegex(VoiceInspectError,"unavailable"):
                self.run_probe(rel,manifest,True,True)

    def test_dangerous_source_links_and_missing_pid_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            target=p/"plan";target.write_text("x")
            link=p/"link";link.symlink_to(target)
            self.assertFalse(_same_installed_file(target,link))
            self.assertFalse(_native_process_matches(p/"absent.pid","/not/there"))

if __name__=="__main__":
    unittest.main(verbosity=2)
