#!/usr/bin/env python3
"""Real production common-runtime status function with isolated process evidence.

No subprocess, PID, firewall or kernel mutation in tests. This verifies
all five Voice profile reports remain bound to one common release engine.
"""
from pathlib import Path
import hashlib
import shutil
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
        (release/"traffic.conf").write_text("--filter-udp=443\n")
        managed=release/"managed"
        managed.mkdir()
        voice_hashes={}
        for name in selected:
            raw=b"91.108.13.10\n"
            (managed/f"ipset-{name}.txt").write_bytes(raw)
            voice_hashes[name]=hashlib.sha256(raw).hexdigest()
        # A regular Strategies STUN profile may consume the IPSET of a
        # service whose Voice toggle is disabled.
        raw=b"198.51.100.0/24\n"
        (managed/"ipset-custom.txt").write_bytes(raw)
        ordinary_hashes={"custom":hashlib.sha256(raw).hexdigest()}
        (release/"voice-plan.json").write_text(json.dumps({
            "schema":1,
            "profiles":[{
                "service":x,"enabled":True,"wan":"WAN",
                "target_count":1,"ports":[[443,443]],
                "profile_sha256":hashlib.sha256(("voice-"+x).encode()).hexdigest(),
            } for x in selected],
            "capture":{
                "logical_wan":"WAN","wan":"vtnet1",
                "voice":[{
                    "service":x,"destination_count":1,"ports":[[443,443]]
                } for x in selected],
            },
            "source":{"ipset_sha256":voice_hashes,
                      "ordinary_scope_ipset_sha256":ordinary_hashes},
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
                self.assertEqual("voice-"+service,report["profile_id"])
                self.assertEqual("vtnet1",report["wan"])
                self.assertEqual("443",report["udp_ports"])
                self.assertEqual(1,report["ipset_entries"])
                self.assertRegex(report["profile_revision"],r"^[0-9a-f]{12}$")

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
                    self.assertNotIn("profile_id",result["services"][name])
                    self.assertNotIn("udp_ports",result["services"][name])

    def test_tampered_profile_scope_metadata_is_never_displayed(self):
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            path=rel/"voice-plan.json"
            original=json.loads(path.read_text())
            changes=(
                lambda p: p["capture"]["voice"][0].update({"ports":[[3478,3478]]}),
                lambda p: p["capture"].update({"wan":"unsafe interface"}),
                lambda p: p["profiles"][0].update({"target_count":2}),
                lambda p: p["profiles"][0].update({"profile_sha256":"bad"}),
            )
            for alter in changes:
                with self.subTest(alter=changes.index(alter)):
                    plan=json.loads(json.dumps(original))
                    alter(plan)
                    path.write_text(json.dumps(plan))
                    with self.assertRaises(VoiceInspectError):
                        self.run_probe(rel,manifest,True,True)
            path.write_text(json.dumps(original))
            report=self.run_probe(rel,manifest,False,False)
            self.assertEqual("stopped",report["state"])
            self.assertEqual("vtnet1",report["services"]["telegram"]["wan"])

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

    def test_live_installed_ordinary_stun_ipset_and_traffic_are_exact(self):
        # Release was sealed earlier; active files are the bytes actually
        # consumed by the one process. Verify drift without touching IPFW.
        with tempfile.TemporaryDirectory() as root:
            rel,manifest=self.plan(root)
            active=Path(root)/"active"
            shutil.copytree(rel,active)
            observed=[]
            def matches(src,dst):
                observed.append(src.relative_to(rel).as_posix())
                return src.is_file() and dst.is_file() and (
                    src.read_bytes()==dst.read_bytes()
                )
            def probe():
                return inspect_common_runtime(
                    rel,manifest,active=active,
                    installed_match=matches,
                    process_check=lambda pid,exe: True)
            self.assertEqual("running",probe()["state"])
            self.assertIn("managed/ipset-custom.txt",observed)
            self.assertIn("managed/ipset-telegram.txt",observed)
            self.assertIn("traffic.conf",observed)
            for path,changed in (
                ("traffic.conf","--filter-udp=*\n"),
                ("managed/ipset-telegram.txt","8.8.8.8\n"),
                ("managed/ipset-custom.txt","91.108.13.10\n"),
                ("dvtws.args","--port=9999\n"),
            ):
                with self.subTest(path=path):
                    target=active/path
                    original=target.read_bytes()
                    target.write_text(changed)
                    report=probe()
                    self.assertEqual("unverified-release",report["state"])
                    self.assertFalse(report["source_verified"])
                    self.assertFalse(report["engine_verified"])
                    self.assertFalse(report["call_verified"])
                    target.write_bytes(original)
                    self.assertEqual("running",probe()["state"])
            (active/"managed/ipset-custom.txt").unlink()
            self.assertEqual("unverified-release",probe()["state"])

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
