#!/usr/bin/env python3
"""End-to-end staging-only five-resource prior instance observation, no router."""
from __future__ import annotations
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_cutover_journal as cutover
import voice_cutover_full_recovery as full
import voice_firewall_ledger as ledger
import voice_process_recovery_evidence as processes
from voice_native_full_observer import NativePreviousObserver
from voice_ipfw_adapter import FreeBSDIPFWAdapter

PATHS={"engine":"/usr/local/etc/zapret2/binaries/my/dvtws2",
       "daemon":"/usr/sbin/daemon",
       "monitor":"/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"}
OLD={"rule_base":19000,"rule_max":19010,"rules":{},"tables":{}}
PROOF={name:"f"*64 for name in cutover.PROOF_NAMES}


class ProcessProbe:
    def __init__(self,value):
        self.value=value
        self.calls=0
    def probe(self):
        self.calls+=1
        return copy.deepcopy(self.value)


class Kernel:
    def __init__(self):
        self.operations=[]
        self.foreign=None
    def __call__(self,argv,**kw):
        self.operations.append(tuple(argv))
        args=tuple(argv[1:])
        if args==("-q","list"):
            rows="00001 allow ip from any to any\n"
            if self.foreign:
                rows+="19000 "+self.foreign+"\n"
            rows+="65535 allow ip from any to any\n"
            return subprocess.CompletedProcess(argv,0,stdout=rows,stderr="")
        if len(args)==3 and args[0]=="table" and args[-1]=="info":
            return subprocess.CompletedProcess(
                argv,69,stdout="",stderr=f"Table {args[1]} does not exist")
        raise AssertionError("unexpected native kernel action: "+str(argv))


class IntegratedPriorTests(unittest.TestCase):
    def fixture(self,path):
        root=Path(path)
        config=root/"config.xml"
        config.write_text("<opnsense>original</opnsense>")
        config.chmod(0o600)
        runtime=root/"runtime"
        runtime.mkdir()
        (runtime/"dvtws.args").write_text("--port=989\n")
        priv=root/"private"
        priv.mkdir(mode=0o700)
        for name in ("whole","ipfw"):
            (priv/name).mkdir(mode=0o700)
        saved=priv/"previous"
        snapshot=backup.capture_previous(config,runtime,saved)
        def proc(role,pid):
            return {"pid":pid,"start_ns":pid*1000000000,
                    "executable":PATHS[role]}
        value={"engine":{"state":"running","process":proc("engine",101),
                          "runtime_args_sha256":snapshot["runtime"]["dvtws.args"]["sha256"]},
               "supervisor":{"state":"running","daemon":proc("daemon",102),
                             "monitor":proc("monitor",103)}}
        procdir=priv/"process"
        hashes=processes.capture_process_evidence(ProcessProbe(value),saved,procdir,PATHS)
        fw=ledger.VoiceOwnershipStore(priv/"ipfw")
        fw.seed(OLD)
        k=Kernel()
        native=FreeBSDIPFWAdapter(19000,19010,runner=k)
        journal=cutover.VoiceCutoverJournal(priv/"whole")
        previous={**backup.bound_resource_fingerprints(saved),**hashes,
                  "firewall":ledger.fingerprint(ledger.canonical_manifest(OLD))}
        journal.begin_bound(previous,PROOF,OLD)
        probe=ProcessProbe(value)
        observer=NativePreviousObserver(
            config=config,runtime=runtime,previous_backup=saved,
            process_evidence=procdir,expected_executables=PATHS,
            process_probe=probe,firewall_store=fw,firewall_adapter=native,
        )
        return observer,journal,fw,saved,procdir,config,runtime,probe,k

    def attest(self,components):
        observer,journal,fw,saved,procdir,*_=components
        return full.inspect_full_recovery(journal,fw,saved,procdir,PATHS,observer)

    def test_stable_native_components_feed_five_domain_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            parts=self.fixture(d)
            observer,journal,fw,saved,procdir,config,runtime,probe,k=parts
            snapshot=observer.observe()
            self.assertEqual(set(cutover.RESOURCE_NAMES),set(snapshot))
            self.assertEqual(journal.read()["previous"],snapshot)
            attested=self.attest(parts)
            self.assertEqual("review-required",attested["state"])
            self.assertEqual("all-previous-fingerprints-observed",attested["reason"])
            self.assertFalse(attested["can_recover_automatically"])
            self.assertFalse(attested["safe_to_mutate"])
            self.assertGreaterEqual(probe.calls,3)
            self.assertTrue(all(cmd[0]=="/sbin/ipfw" and
                                (cmd[1:]==("-q","list") or
                                 cmd[-1]=="info") for cmd in k.operations))
            self.assertEqual(b"<opnsense>original</opnsense>",config.read_bytes())

    def test_changed_file_proves_mixed_and_new_pid_proves_new_instance(self):
        for case in ("config","config-mode","runtime","pid","start-time","process-stopped"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                parts=self.fixture(d)
                observer,journal,fw,saved,procdir,config,runtime,probe,k=parts
                if case=="config":
                    config.write_text("<opnsense>different</opnsense>")
                elif case=="config-mode":
                    config.chmod(0o644)
                elif case=="runtime":
                    (runtime/"dvtws.args").write_text("--port=990\n")
                elif case=="pid":
                    probe.value["engine"]["process"]["pid"]=400
                elif case=="start-time":
                    probe.value["engine"]["process"]["start_ns"]+=1
                else:
                    probe.value["engine"]["state"]="stopped"
                    probe.value["supervisor"]["state"]="stopped"
                    for row in (probe.value["engine"]["process"],
                                probe.value["supervisor"]["daemon"],
                                probe.value["supervisor"]["monitor"]):
                        row["pid"]=None
                        row["start_ns"]=None
                result=self.attest(parts)
                self.assertEqual("blocked",result["state"])
                self.assertFalse(result["safe_to_mutate"])
                self.assertEqual(
                    "invalid-or-incomplete-whole-system-evidence" if case=="config-mode"
                    else "mixed-or-untrusted-previous-state",
                    result["reason"],
                )
                if case in ("pid","start-time","process-stopped"):
                    self.assertEqual("unknown-or-changed",result["domains"]["engine"])

    def test_foreign_kernel_owner_and_corrupt_previous_process_evidence_block(self):
        with tempfile.TemporaryDirectory() as d:
            parts=self.fixture(d)
            observer,journal,fw,saved,procdir,config,runtime,probe,k=parts
            k.foreign="allow ip from any to any"
            report=self.attest(parts)
            self.assertEqual("blocked",report["state"])
            self.assertFalse(report["can_activate"])
        with tempfile.TemporaryDirectory() as d:
            parts=self.fixture(d)
            observer,journal,fw,saved,procdir,config,runtime,probe,k=parts
            (procdir/"processes.json").write_text('{"tampered":true}')
            report=self.attest(parts)
            self.assertEqual("blocked",report["state"])
            self.assertEqual("invalid-or-incomplete-whole-system-evidence",
                             report["reason"])

    def test_missing_ipfw_owner_denied_and_no_automatic_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            parts=self.fixture(d)
            observer,journal,fw,saved,procdir,config,runtime,probe,k=parts
            (fw.directory/"ownership.json").unlink()
            report=self.attest(parts)
            self.assertEqual("blocked",report["state"])
            self.assertFalse(report["can_recover_automatically"])


if __name__=="__main__":
    unittest.main(verbosity=2)
