#!/usr/bin/env python3
"""Native FreeBSD Voice process reader with fake ps, real private pidfile fixtures."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_process_recovery_evidence as evidence
import voice_native_process_probe as native

PATHS={"engine":"/usr/local/etc/zapret2/binaries/my/dvtws2",
       "daemon":"/usr/sbin/daemon",
       "monitor":"/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"}
COMMANDS={101:PATHS["engine"]+" --port=989 --sockarg=0x200",
          102:PATHS["daemon"]+" -P /var/run/zapret2-supervisor-daemon.pid -f "+PATHS["monitor"],
          103:"/bin/sh "+PATHS["monitor"]}


class FakePs:
    def __init__(self, commands=None, bad_detail=None):
        self.commands=commands if commands is not None else COMMANDS.copy()
        self.calls=[]
        self.bad_detail=bad_detail
    def __call__(self, argv):
        self.calls.append(argv)
        if "-A" in argv:
            return "1 /sbin/init\n"+"\n".join(f"{pid} {command}" for pid,command in self.commands.items())+"\n"
        pid=int(argv[argv.index("-p")+1])
        command=self.commands[pid]
        if self.bad_detail==pid:
            command+="+changed"
        return f"{pid} Fri Oct  9 20:25:17 2026 {command}\n"


class NativeProcessProbeTests(unittest.TestCase):
    def fixture(self, root, running=True):
        base=Path(root)
        c=base/"config.xml"
        c.write_text("<opnsense/>")
        c.chmod(0o600)
        r=base/"runtime"
        r.mkdir()
        (r/"dvtws.args").write_text("--port=989\n")
        private=base/"private"
        private.mkdir(mode=0o700)
        saved=private/"previous"
        backup.capture_previous(c,r,saved)
        pidfiles={role:str(base/f"{role}.pid") for role in PATHS}
        # Inject absolute private fixture pidfiles in lieu of /var/run without
        # weakening the production constructor's fixed-path policy.
        pidfiles={role:f"/var/run/voice-fixture-{role}.pid" for role in PATHS}
        instance=native.FreeBSDVoiceProcessProbe(PATHS,pidfiles,saved,ps_reader=FakePs())
        fixture_paths={role:base/f"{role}.pid" for role in PATHS}
        instance.pidfiles={role:str(path) for role,path in fixture_paths.items()}
        if running:
            for n,(role,path) in enumerate(fixture_paths.items(),101):
                path.write_text(str(n)+"\n")
                path.chmod(0o600)
        return instance,private/"evidence",r,c

    def test_native_mock_probe_round_trip_and_private_capture(self):
        with tempfile.TemporaryDirectory() as d:
            probe,target,runtime,config=self.fixture(d)
            result=probe.probe()
            self.assertEqual("running",result["engine"]["state"])
            self.assertEqual({101,102,103},
                             {result["engine"]["process"]["pid"],
                              result["supervisor"]["daemon"]["pid"],
                              result["supervisor"]["monitor"]["pid"]})
            self.assertGreater(result["engine"]["process"]["start_ns"],0)
            self.assertTrue(all(cmd[0]=="/bin/ps" for cmd in probe.reader.calls))
            self.assertTrue(all("kill" not in cmd for cmd in probe.reader.calls))
            digests=evidence.capture_process_evidence(
                probe,probe.previous_backup,target,PATHS
            )
            report=evidence.inspect_process_evidence(
                target,probe.previous_backup,PATHS,digests
            )
            self.assertEqual(digests,report["previous"])
            self.assertEqual("--port=989\n",(runtime/"dvtws.args").read_text())

    def test_clean_stopped_requires_global_process_absence(self):
        with tempfile.TemporaryDirectory() as d:
            probe,target,runtime,config=self.fixture(d,running=False)
            probe.reader=FakePs({})
            self.assertEqual("stopped",probe.probe()["engine"]["state"])
            with self.assertRaises(evidence.ProcessEvidenceError):
                probe.reader=FakePs(COMMANDS)
                probe.probe()

    def test_partial_ambiguous_duplicate_and_changed_command_rejected(self):
        for case in ("missing-pidfile","duplicate","extra-engine","missing-monitor",
                     "detail-changed","unowned-pidfile","symlink-pidfile"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                probe,target,runtime,config=self.fixture(d)
                if case=="missing-pidfile":
                    Path(probe.pidfiles["daemon"]).unlink()
                elif case=="duplicate":
                    Path(probe.pidfiles["monitor"]).write_text("101\n")
                elif case=="extra-engine":
                    probe.reader=FakePs({**COMMANDS,104:COMMANDS[101]})
                elif case=="missing-monitor":
                    probe.reader=FakePs({101:COMMANDS[101],102:COMMANDS[102]})
                elif case=="detail-changed":
                    probe.reader=FakePs(bad_detail=103)
                elif case=="unowned-pidfile":
                    Path(probe.pidfiles["daemon"]).chmod(0o666)
                else:
                    pid=Path(probe.pidfiles["monitor"])
                    pid.unlink()
                    pid.symlink_to(probe.pidfiles["engine"])
                with self.assertRaises(evidence.ProcessEvidenceError):
                    probe.probe()
                self.assertFalse(target.exists())

    def test_nonblank_malformed_ps_row_remains_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            probe,target,runtime,config=self.fixture(d,running=False)
            class CorruptPs(FakePs):
                def __call__(self, argv):
                    if "-A" in argv:
                        return "1 /sbin/init\nnon-numeric invalid process\n"
                    return super().__call__(argv)
            probe.reader=CorruptPs({})
            with self.assertRaises(evidence.ProcessEvidenceError):
                probe.probe()

    def test_untrusted_pidfile_map_rejected_at_constructor(self):
        with tempfile.TemporaryDirectory() as d:
            probe,target,runtime,config=self.fixture(d)
            for pidfiles in (
                {"engine":"/tmp/engine.pid", "daemon":"/var/run/daemon.pid",
                 "monitor":"/var/run/monitor.pid"},
                {"engine":"/var/run/same.pid", "daemon":"/var/run/same.pid",
                 "monitor":"/var/run/monitor.pid"},
            ):
                with self.assertRaises(evidence.ProcessEvidenceError):
                    native.FreeBSDVoiceProcessProbe(PATHS,pidfiles,probe.previous_backup,
                                                    ps_reader=FakePs())


if __name__=="__main__":
    unittest.main(verbosity=2)
