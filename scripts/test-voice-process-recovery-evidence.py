#!/usr/bin/env python3
"""No-appliance lifecycle evidence tests: only temporary files and fake probes."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_cutover_journal as journal
import voice_process_recovery_evidence as p

PATHS={"engine":"/usr/local/etc/zapret2/binaries/my/dvtws2",
       "daemon":"/usr/sbin/daemon",
       "monitor":"/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"}


class Probe:
    def __init__(self, observed):
        self.observed=observed
        self.calls=0
    def probe(self):
        self.calls+=1
        return copy.deepcopy(self.observed)


class EvidenceTests(unittest.TestCase):
    def setup(self,root,running=True):
        base=Path(root)
        config=base/"config.xml"
        config.write_text("<opnsense/>")
        config.chmod(0o600)
        runtime=base/"runtime"
        runtime.mkdir()
        (runtime/"dvtws.args").write_bytes(b"--port=989\n--filter-tcp=443\n")
        private=base/"private"
        private.mkdir(mode=0o700)
        backup_path=private/"previous"
        snapshot=backup.capture_previous(config,runtime,backup_path)
        sha=snapshot["runtime"]["dvtws.args"]["sha256"]
        def proc(role,n):
            return {"pid":100+n if running else None,
                    "start_ns":100000000+n if running else None,
                    "executable":PATHS[role]}
        state="running" if running else "stopped"
        observed={"engine":{"state":state,"process":proc("engine",1),
                            "runtime_args_sha256":sha},
                  "supervisor":{"state":state,"daemon":proc("daemon",2),
                                "monitor":proc("monitor",3)}}
        return backup_path,private/"processes",observed,config,runtime

    def test_captured_processes_bind_to_journal_after_reopen(self):
        for running in (True,False):
            with self.subTest(running=running),tempfile.TemporaryDirectory() as d:
                saved,target,observed,config,runtime=self.setup(d,running)
                adapter=Probe(observed)
                hashes=p.capture_process_evidence(adapter,saved,target,PATHS)
                self.assertEqual(3,adapter.calls)
                expected={**backup.bound_resource_fingerprints(saved),
                          **hashes, "firewall":"e"*64}
                proof={name:"f"*64 for name in journal.PROOF_NAMES}
                record=journal.new_record(expected,proof)
                self.assertEqual(hashes["engine"],record["previous"]["engine"])
                report=p.inspect_process_evidence(target,saved,PATHS,record["previous"])
                self.assertEqual("evidence-only",report["state"])
                self.assertIs(report["can_activate"],False)
                self.assertIs(report["can_recover_automatically"],False)
                self.assertEqual(hashes,report["previous"])
                self.assertEqual("stopped" if not running else "running",
                                 report["observation"]["engine"]["state"])
                self.assertEqual(b"<opnsense/>",config.read_bytes())
                self.assertEqual(b"--port=989\n--filter-tcp=443\n",
                                 (runtime/"dvtws.args").read_bytes())
                with self.assertRaises(p.ProcessEvidenceError):
                    p.capture_process_evidence(adapter,saved,target,PATHS)

    def test_partial_foreign_duplicate_or_invalid_pid_rejected(self):
        cases=("partial","wrong-exe","same-pid","stale-pid","bool-pid",
               "stale-args","extra","bad-path","negative-start")
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,target,observed,config,runtime=self.setup(d)
                if case=="partial":
                    observed["supervisor"]["state"]="stopped"
                elif case=="wrong-exe":
                    observed["supervisor"]["monitor"]["executable"]="/bin/sh"
                elif case=="same-pid":
                    observed["supervisor"]["monitor"]["pid"]=observed["engine"]["process"]["pid"]
                elif case=="stale-pid":
                    observed["engine"]["process"]["pid"]=None
                elif case=="bool-pid":
                    observed["engine"]["process"]["pid"]=True
                elif case=="stale-args":
                    observed["engine"]["runtime_args_sha256"]="a"*64
                elif case=="extra":
                    observed["engine"]["unknown"]="yes"
                elif case=="bad-path":
                    bad={**PATHS,"engine":"../dvtws2"}
                elif case=="negative-start":
                    observed["supervisor"]["daemon"]["start_ns"]=-1
                with self.assertRaises(p.ProcessEvidenceError):
                    p.capture_process_evidence(Probe(observed),saved,target,
                                               bad if case=="bad-path" else PATHS)
                self.assertFalse(target.exists())
                self.assertEqual(b"<opnsense/>",config.read_bytes())

    def test_mid_probe_change_and_bad_journal_digest_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            saved,target,observed,config,runtime=self.setup(d)
            class ChangingProbe:
                def __init__(self): self.calls=0
                def probe(self):
                    self.calls+=1
                    result=copy.deepcopy(observed)
                    if self.calls>=2:
                        result["engine"]["process"]["pid"]+=1
                    return result
            with self.assertRaises(p.ProcessEvidenceError):
                p.capture_process_evidence(ChangingProbe(),saved,target,PATHS)
            self.assertFalse(target.exists())
            p.capture_process_evidence(Probe(observed),saved,target,PATHS)
            with self.assertRaises(p.ProcessEvidenceError):
                p.inspect_process_evidence(target,saved,PATHS,{"engine":"0"*64,
                                                              "supervisor":"0"*64})
            self.assertEqual("evidence-only",
                             p.inspect_process_evidence(target,saved,PATHS)["state"])

    def test_corrupt_symlink_missing_or_foreign_evidence_never_accepted(self):
        for case in ("corrupt","symlink","missing","extra","runtime-change","world-readable"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,target,observed,config,runtime=self.setup(d)
                p.capture_process_evidence(Probe(observed),saved,target,PATHS)
                record=target/"processes.json"
                if case=="corrupt": record.write_text('{"broken":true}')
                elif case=="symlink":
                    record.unlink()
                    record.symlink_to(config)
                elif case=="missing": record.unlink()
                elif case=="extra": (target/"foreign").write_text("x")
                elif case=="runtime-change": (saved/"runtime/dvtws.args").write_text("bad")
                else: record.chmod(0o644)
                with self.assertRaises((p.ProcessEvidenceError,backup.VoiceBackupError,OSError)):
                    p.inspect_process_evidence(target,saved,PATHS)
                self.assertEqual(b"<opnsense/>",config.read_bytes())

    def test_existing_or_linked_destination_never_overwritten(self):
        for case in ("exists","symlink","file","fsync"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,target,observed,config,runtime=self.setup(d)
                sentinel=Path(d)/"sentinel"
                sentinel.write_text("unchanged")
                if case=="exists":
                    target.mkdir()
                    (target/"keep").write_text("untouched")
                elif case=="symlink":
                    target.symlink_to(sentinel)
                elif case=="file":
                    target.write_text("untouched")
                if case=="fsync":
                    with patch.object(p,"_sync_dir",side_effect=OSError("fsync fail")):
                        with self.assertRaises(OSError):
                            p.capture_process_evidence(Probe(observed),saved,target,PATHS)
                else:
                    with self.assertRaises(p.ProcessEvidenceError):
                        p.capture_process_evidence(Probe(observed),saved,target,PATHS)
                self.assertEqual("unchanged",sentinel.read_text())
                if case=="fsync":
                    self.assertFalse(target.exists())
                    self.assertFalse(list(target.parent.glob(".voice-process-evidence-*")))
                elif case=="exists":
                    self.assertEqual("untouched",(target/"keep").read_text())


if __name__=="__main__":
    unittest.main(verbosity=2)
