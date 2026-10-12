#!/usr/bin/env python3
"""Native Voice initial ordinary IPFW bootstrap; no kernel mutations."""
from __future__ import annotations
import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_firewall_ledger import VoiceOwnershipStore
from voice_cutover_guard import check_pending
from voice_native_initial_ipfw_seed import bootstrap_native_ordinary_ipfw_owner


def fixture(file, name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/file)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

source=fixture("test-voice-native-live-preflight.py","initial_voice_ipfw_live_fixture")
source_probe=source.fixtures


class InitialNativeOwnerTests(unittest.TestCase):
    def setUp(self):
        self.live=source.LivePreflightTests()
        self.live.setUp()
        self.addCleanup(self.live.doCleanups)
        self.path=self.live.config.parent
        self.live.ledger.mkdir(mode=0o700)
        self.store=VoiceOwnershipStore(self.live.ledger)
        self.ordinary=self.path/"ordinary.resolved.conf"
        self.ordinary.write_text("--filter-tcp=443\n--filter-udp=596\n")
        self.live.runtime.joinpath("dvtws.args").write_text(
            "--port=989\n" + self.ordinary.read_text()
        )
        self.live.expected["engine"]=[
            source.EXPECTED_SCRIPTS["engine"],"--port=989",
            "--filter-tcp=443","--filter-udp=596",*source.FIXED_TRAILER,
        ]
        self.live.commands[101]=" ".join(self.live.expected["engine"])
        self.live.argv["engine"]=(
            "\x00".join(self.live.expected["engine"])+"\x00"
        ).encode("ascii")
        self.live.probe.reader=source_probe.FakePs(self.live.commands)
        self.live.fake_ipfw.rules=(
            "00001 allow ip from any to any\n"
            "19000 divert 989 tcp from any to any 443 out not diverted not sockarg xmit vtnet1\n"
            "19001 divert 989 udp from any to any 596 out not diverted not sockarg xmit vtnet1\n"
            "65535 allow ip from any to any\n"
        )
        self.lock_calls=[]
        self.legacy=patch("voice_native_initial_ipfw_seed.require_no_legacy",
                          return_value=None)
        self.legacy.start()
        self.addCleanup(self.legacy.stop)

    def execute(self, *, lock=True, wan="vtnet1", port=989):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return bootstrap_native_ordinary_ipfw_owner(
                whole_root=self.live.whole,ledger=self.store,
                config_path=self.live.config,active_runtime=self.live.runtime,
                ordinary_source=self.ordinary,physical_wan=wan,
                divert_port=port,probe=self.live.probe,
                kernel_reader=self.live.kernel,ipfw_adapter=self.live.adapter,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_native_preflight_to_exact_ordinary_ledger_seed(self):
        previous_xml=self.live.config.read_bytes()
        report=self.execute()
        self.assertEqual("native-ordinary-ipfw-owner-sealed",report["state"])
        self.assertEqual(report["previous"],self.store.owned())
        self.assertTrue(report["must_continue_prepared_under_same_locks"])
        self.assertFalse(report["safe_to_enable_voice"])
        self.assertEqual(previous_xml,self.live.config.read_bytes())
        self.assertFalse(self.live.whole.exists())
        self.assertEqual("native-ipfw-owned",check_pending(
            self.live.whole,self.live.ledger)["reason"])
        self.assertTrue(all(call[1] in ("-q","table")
                            for call in self.live.fake_ipfw.calls))
        self.assertGreaterEqual(len(self.lock_calls),4)

    def test_unlocked_config_rejected_before_seeding(self):
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.execute(lock=False)
        self.assertIsNone(self.store.owned())

    def test_foreign_rule_or_wan_refused(self):
        for wan in ("vtnet2","", "vtnet1;"):
            with self.subTest(wan=wan):
                with self.assertRaises((OSError,RuntimeError,ValueError)):
                    self.execute(wan=wan)
                self.assertIsNone(self.store.owned())
        self.live.fake_ipfw.rules=self.live.fake_ipfw.rules.replace(
            "19000 divert 989 tcp","19000 divert 988 tcp",
        )
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.execute()
        self.assertIsNone(self.store.owned())

    def test_changed_or_unrepresentable_ordinary_source_refused(self):
        for source_text in ("--filter-tcp=80\n--filter-udp=596\n",
                            "--filter-tcp=443\n--filter-udp=595\n",
                            "☃\n"):
            with self.subTest(text=source_text):
                self.ordinary.write_text(source_text)
                with self.assertRaises((OSError,RuntimeError,ValueError)):
                    self.execute()
                self.assertIsNone(self.store.owned())

    def test_duplicate_and_existing_owner_are_not_reseeded(self):
        self.execute()
        before=self.store.owned()
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.execute()
        self.assertEqual(before,self.store.owned())

    def test_postseed_failure_leaves_owner_and_blocks_legacy_restart(self):
        with patch("voice_native_initial_ipfw_seed.observe_owned_ipfw",
                   side_effect=OSError("power cut after ledger fsync")):
            with self.assertRaises(OSError):
                self.execute()
        self.assertIsNotNone(self.store.owned())
        self.assertFalse(check_pending(
            self.live.whole,self.live.ledger)["safe_to_mutate"])


if __name__=="__main__":
    unittest.main(verbosity=2)
