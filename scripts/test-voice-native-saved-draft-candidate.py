#!/usr/bin/env python3
"""One original FD9/Config inode flock: GUI OFF drafts -> isolated ON XML."""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from xml.dom import minidom

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_saved_draft_candidate import (
    prepare_saved_draft_candidate, NativeDraftCandidateError, PREFIX, SERVICES,
)

def make_xml() -> bytes:
    profiles="".join(
        f"<{s}><enabled>0</enabled><args>--filter-udp=*\n--filter-l7=stun\n--payload=stun</args></{s}>"
        for s in SERVICES
    )
    ipsets="".join(f"<{s}ips>91.108.0.0/16</{s}ips>" for s in SERVICES)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<opnsense><system><password>OLD_SECRET</password></system>'
        '<OPNsense><Other><mode>unchanged</mode></Other><Zapret>'
        '<general><enabled>1</enabled><waninterface>WAN</waninterface></general>'
        '<strategy><trafficargs>--filter-tcp=443</trafficargs></strategy>'
        '<voice><waninterface>WAN</waninterface>' + profiles + '</voice>'
        '<hostlist><mode>all</mode>' + ipsets +
        '<youtubedomains>youtube.com</youtubedomains></hostlist>'
        '</Zapret></OPNsense></opnsense>'
    ).encode()

class SavedDraftCandidateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="native-voice-saved-draft-")
        self.addCleanup(t.cleanup)
        self.parent=Path(t.name)
        self.live=self.parent/"config.xml"
        self.old=make_xml()
        self.live.write_bytes(self.old)
        self.live.chmod(0o600)
        self.destination=self.parent/"voice-build-input"
        self.digest=hashlib.sha256(self.old).hexdigest()
        self.hits=0

    def build(self,mask="10000",digest=None,lock=True):
        fd=os.open(self.live,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            def owner():
                self.hits+=1
            return prepare_saved_draft_candidate(
                config_path=self.live, destination=self.destination,
                mask=mask, expected_sha=digest or self.digest,
                config_fd=fd, config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=owner,
            )
        finally:
            os.close(fd)

    def test_one_config_inode_produces_complete_candidate_without_mutation(self):
        r=self.build("10001")
        self.assertEqual("native-voice-private-saved-draft-xml",r["state"])
        self.assertFalse(r["safe_to_enable_voice"])
        self.assertFalse(r["public_voice_apply"])
        self.assertEqual(self.digest,r["previous_config_sha256"])
        self.assertGreaterEqual(self.hits,2)
        self.assertEqual(self.old,self.live.read_bytes())
        self.assertEqual({"config.xml"},{p.name for p in self.destination.iterdir()})
        self.assertEqual(0o700,self.destination.stat().st_mode&0o777)
        self.assertEqual(0o600,(self.destination/"config.xml").stat().st_mode&0o777)
        old=minidom.parseString(self.old)
        new=minidom.parseString((self.destination/"config.xml").read_bytes())
        self.assertEqual(
            old.getElementsByTagName("system")[0].toxml(),
            new.getElementsByTagName("system")[0].toxml(),
        )
        voice=new.getElementsByTagName("voice")[0]
        self.assertEqual(["1","0","0","0","1"],[
            voice.getElementsByTagName(s)[0].getElementsByTagName("enabled")[0].firstChild.data
            for s in SERVICES
        ])
        self.assertEqual("OLD_SECRET",
                         new.getElementsByTagName("password")[0].firstChild.data)
        self.assertEqual([],list(self.parent.glob(PREFIX+"*")))
        with self.assertRaises(NativeDraftCandidateError):
            self.build()
        self.assertEqual(self.old,self.live.read_bytes())

    def test_old_config_baseline_and_locked_inode_required(self):
        with self.assertRaises(NativeDraftCandidateError):
            self.build(digest="0"*64)
        self.assertFalse(self.destination.exists())
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.build(lock=False)
        self.assertFalse(self.destination.exists())

    def test_reject_invalid_mask_and_partial_stage(self):
        for value in ("", "00000", "1", "111111", "1010x", "100\n0"):
            with self.assertRaises(NativeDraftCandidateError):
                self.build(mask=value)
            self.assertFalse(self.destination.exists())
        (self.parent/(PREFIX+"orphan")).mkdir(mode=0o700)
        with self.assertRaises(NativeDraftCandidateError):
            self.build(mask="11111")
        self.assertFalse(self.destination.exists())

    def test_saved_draft_must_have_off_flags_and_previous_arguments(self):
        self.live.write_bytes(self.old.replace(
            b"<telegram><enabled>0</enabled>",b"<telegram><enabled>1</enabled>"
        ))
        self.digest=hashlib.sha256(self.live.read_bytes()).hexdigest()
        with self.assertRaises(NativeDraftCandidateError):
            self.build()
        self.assertFalse(self.destination.exists())
        self.live.write_bytes(self.old.replace(
            b"--filter-udp=*\n--filter-l7=stun\n--payload=stun",b""
        ))
        self.digest=hashlib.sha256(self.live.read_bytes()).hexdigest()
        with self.assertRaises(NativeDraftCandidateError):
            self.build()
        self.assertFalse(self.destination.exists())

    def test_reject_foreign_xml_anchors_and_entities(self):
        for updated in (
            self.old.replace(b"</Zapret>",b"</Zapret><Zapret/>"),
            b'<!DOCTYPE opnsense [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + self.old,
            self.old.replace(b"<voice>",b"<voice><telegram/>"),
        ):
            self.live.write_bytes(updated)
            self.digest=hashlib.sha256(updated).hexdigest()
            with self.assertRaises(NativeDraftCandidateError):
                self.build()
            self.assertFalse(self.destination.exists())

if __name__=="__main__":
    unittest.main(verbosity=2)
