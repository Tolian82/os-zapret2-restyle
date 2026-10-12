#!/usr/bin/env python3
"""Single original Voice FD9/Config lock spans owner, old evidence, PREPARED."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
from voice_native_recovery_quiescence import _locked_config
from voice_native_prepare_one_lock import prepare_native_voice_one_lock


class OneOriginalLockTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="voice-one-lock-")
        self.addCleanup(temp.cleanup)
        base=Path(temp.name)
        self.config=base/"config.xml"
        self.config.write_text("<opnsense/>")
        self.runtime=base/"runtime"
        self.runtime.mkdir()
        self.whole=base/"whole"
        self.whole.mkdir(mode=0o700)
        self.ledger_path=base/"ipfw"
        self.ledger_path.mkdir(mode=0o700)
        self.journal=VoiceCutoverJournal(self.whole)
        self.ledger=VoiceOwnershipStore(self.ledger_path)
        self.events=[]
        self.epoch={"config":"a"*64,"runtime":"b"*64,
                    "engine":"c"*64,"supervisor":"d"*64,"firewall":"e"*64}
        self.owner="e"*64
        self.probe=type("Probe",(),{"expected":{"engine":"native"}})()
        self.call_args=None

    def run_coordinator(self, *, lock=True, seed_error=None, previous_error=None,
                        result_bad=False, bad_candidate=False):
        fd=os.open(self.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            def check(name, *args, **kwargs):
                self.events.append(name)
                self.assertEqual(fd,kwargs["config_fd"])
                self.assertIs(kwargs["require_lifecycle_owner"],owner)
                _locked_config(self.config,fd,(os.geteuid(),os.getegid()))
            def owner():
                self.events.append("FD9")
            def qualify(*args, **kwargs):
                check("qualify",*args,**kwargs)
                if bad_candidate:
                    raise ValueError("simulated forged orchestrator release")
                return ({"tables":{"zapret2_voice_telegram":["91.108.13.10"]}},
                        {"enabled_services":["telegram"]})
            def seed(*args, **kwargs):
                check("seed",*args,**kwargs)
                if seed_error:
                    raise OSError("simulated owner failure")
                return {"state":"native-ordinary-ipfw-owner-sealed",
                        "owned_ipfw_sha256":self.owner,
                        "safe_to_enable_voice":False,
                        "must_continue_prepared_under_same_locks":True}
            def old(*args, **kwargs):
                check("previous",*args,**kwargs)
                if previous_error:
                    raise OSError("simulated checkpoint failure")
                return {"state":"native-previous-five-domains-sealed",
                        "previous":self.epoch,
                        "previous_backup":self.whole/"previous",
                        "process_evidence":self.whole/"process-evidence",
                        "security_evidence":self.whole/"process-security-policy",
                        "previous_observer":object(),
                        "safe_to_enable_voice":False}
            def staged(*args, **kwargs):
                check("candidate",*args,**kwargs)
                self.assertEqual(self.whole/"previous",kwargs["previous_backup"])
                self.assertEqual(self.probe.expected,kwargs["expected_scripts"])
                if not result_bad:
                    from voice_cutover_journal import VoiceCutoverJournal
                    with patch.object(VoiceCutoverJournal,"read",return_value={
                        "schema":4,"phase":"prepared","previous":self.epoch,
                        "check":"z"*64
                    }):
                        return {"state":"native-voice-stage-and-forward-prepared",
                                "whole_check":"z"*64,
                                "previous_install_image":"sealed-not-installed",
                                "safe_to_enable_voice":False}
                return {"state":"wrong","safe_to_enable_voice":False}
            # This test has a synthetic sealed journal ONLY at the exact
            # verification boundary; no direct disk-journal writes.
            def synthetic_read():
                return {"schema":4,"phase":"prepared","previous":self.epoch,
                        "check":"z"*64}
            with patch("voice_native_prepare_one_lock.qualify_saved_voice_release",qualify),\
                 patch("voice_native_prepare_one_lock.bootstrap_native_ordinary_ipfw_owner",seed),\
                 patch("voice_native_prepare_one_lock.prepare_native_previous_evidence",old),\
                 patch("voice_native_prepare_one_lock.prepare_saved_release_forward_intent",staged),\
                 patch.object(self.journal,"read",side_effect=synthetic_read):
                return prepare_native_voice_one_lock(
                    journal=self.journal,ledger=self.ledger,
                    config_path=self.config,active_runtime=self.runtime,
                    source_config=self.config.parent/"candidate.xml",
                    source_runtime=self.config.parent/"candidate-runtime",
                    release_dir=self.config.parent/"release",
                    managed_source=self.config.parent/"managed",
                    ordinary_source=self.config.parent/"ordinary",
                    tcp_ports=self.config.parent/"tcp",
                    udp_ports=self.config.parent/"udp",
                    physical_wan="vtnet1",divert_port=989,
                    probe=self.probe,kernel_reader=object(),
                    security_reader=object(),ipfw_adapter=object(),
                    config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                    require_lifecycle_owner=owner,
                )
        finally:
            os.close(fd)

    def test_one_original_config_fd_across_all_three_live_operations(self):
        before=self.config.read_bytes()
        result=self.run_coordinator()
        self.assertEqual("native-voice-original-lock-prepared",result["state"])
        self.assertEqual(["qualify","seed","previous","candidate"],
                         [x for x in self.events if x!="FD9"])
        self.assertEqual(before,self.config.read_bytes())
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(result["public_voice_apply"])

    def test_unlocked_config_denies_before_bootstrap(self):
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.run_coordinator(lock=False)
        self.assertEqual(["FD9"],self.events,
                         "owner check is allowed; no seed or disk write")

    def test_bad_saved_gui_release_does_not_seed_or_block_legacy(self):
        with self.assertRaises(ValueError):
            self.run_coordinator(bad_candidate=True)
        self.assertEqual(["qualify"],
                         [x for x in self.events if x!="FD9"])
        self.assertIsNone(self.ledger.owned())

    def test_owner_failure_never_captures_old_process_or_candidate(self):
        with self.assertRaises(OSError):
            self.run_coordinator(seed_error=True)
        self.assertEqual(["qualify","seed"],[x for x in self.events if x!="FD9"])

    def test_previous_failure_never_stages_candidate(self):
        with self.assertRaises(OSError):
            self.run_coordinator(previous_error=True)
        self.assertEqual(["qualify","seed","previous"],
                         [x for x in self.events if x!="FD9"])

    def test_foreign_prepared_result_refuses_completion(self):
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.run_coordinator(result_bad=True)
        self.assertEqual(["qualify","seed","previous","candidate"],
                         [x for x in self.events if x!="FD9"])


if __name__=="__main__":
    unittest.main(verbosity=2)
