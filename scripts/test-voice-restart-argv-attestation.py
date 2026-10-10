#!/usr/bin/env python3
"""New-process exact argv offline proof: stable tests with no router access."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_process_recovery_evidence as process
import voice_restart_argv_attestation as restart

PATHS = {
    "engine": "/usr/local/etc/zapret2/binaries/my/dvtws2",
    "daemon": "/usr/sbin/daemon",
    "monitor": "/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh",
}
SUPERVISOR = {
    "daemon": [PATHS["daemon"], "-P", "/var/run/voice-monitor.pid",
               "-f", PATHS["monitor"]],
    "monitor": ["/bin/sh", PATHS["monitor"]],
}


class Probe:
    def __init__(self, data):
        self.data = data
    def probe(self):
        return copy.deepcopy(self.data)


class Reader:
    def __init__(self, data):
        self.data = data
        self.calls = 0
        self.edit_at = None
        self.callback = None
    def observe_argv(self):
        self.calls += 1
        if self.callback is not None:
            self.callback(self.calls)
        result = copy.deepcopy(self.data)
        if self.calls == self.edit_at:
            result["engine"]["start_ns"] += 1
        return result


class RestartArgvTests(unittest.TestCase):
    def fixture(self, directory, *, old_running=True):
        root = Path(directory)
        config = root / "config.xml"
        config.write_text("<opnsense/>")
        config.chmod(0o600)
        runtime = root / "runtime"
        runtime.mkdir()
        args = runtime / "dvtws.args"
        args.write_bytes(b"--filter-udp=443  --dpi-desync=fake\n\t--port=989\n")
        priv = root / "private"
        priv.mkdir(mode=0o700)
        backup_dir = priv / "previous"
        snap = backup.capture_previous(config, runtime, backup_dir)
        state = "running" if old_running else "stopped"
        def old(role,pid):
            return {"pid": pid if old_running else None,
                    "start_ns": pid * 1000000000 if old_running else None,
                    "executable": PATHS[role]}
        old_observation = {
            "engine": {"state":state,"process":old("engine",101),
                       "runtime_args_sha256":snap["runtime"]["dvtws.args"]["sha256"]},
            "supervisor":{"state":state,"daemon":old("daemon",102),
                          "monitor":old("monitor",103)},
        }
        old_dir = priv / "process"
        process.capture_process_evidence(
            Probe(old_observation), backup_dir, old_dir, PATHS,
        )
        expected_engine = [
            PATHS["engine"], "--filter-udp=443", "--dpi-desync=fake",
            "--port=989", "--sockarg=0x200", "--user=nobody",
        ]
        current = {
            "engine":{"pid":201,"start_ns":201000000000,
                      "executable":PATHS["engine"],"argv":expected_engine},
            "supervisor":{
                "daemon":{"pid":202,"start_ns":202000000000,
                          "executable":PATHS["daemon"],"argv":SUPERVISOR["daemon"]},
                "monitor":{"pid":203,"start_ns":203000000000,
                           "executable":PATHS["monitor"],"argv":SUPERVISOR["monitor"]},
            },
        }
        return backup_dir,old_dir,current,args

    def run_proof(self, pair, current=None, supervisor=None, reader=None):
        saved,evidence,default,unused = pair
        return restart.inspect_restarted_argv(
            saved,evidence,PATHS,
            SUPERVISOR if supervisor is None else supervisor,
            Reader(default if current is None else current) if reader is None else reader,
        )

    def assert_denied(self, result):
        self.assertEqual("blocked", result["state"])
        for field in ("can_activate", "can_recover_automatically", "safe_to_mutate",
                      "safe_to_finish_intent", "media_pass", "startup_ready"):
            self.assertIs(result[field],False)

    def test_exact_awk_tokenization_and_stable_new_instances_are_review_only(self):
        with tempfile.TemporaryDirectory() as d:
            pair=self.fixture(d)
            saved,evidence,current,args=pair
            expected=restart.expected_engine_argv(saved,PATHS["engine"])
            self.assertEqual(current["engine"]["argv"],expected)
            reader=Reader(current)
            report=self.run_proof(pair,reader=reader)
            self.assertEqual("review-required",report["state"])
            self.assertEqual("new-process-argv-matches-sealed-launcher-plan",
                             report["reason"])
            self.assertFalse(report["can_activate"])
            self.assertFalse(report["startup_ready"])
            self.assertFalse(report["media_pass"])
            self.assertEqual(2,reader.calls)
            self.assertEqual(201,report["instances"]["engine"]["pid"])
            self.assertEqual(64,len(report["engine_argv_sha256"]))
            self.assertEqual(b"--filter-udp=443  --dpi-desync=fake\n\t--port=989\n",
                             args.read_bytes())
            self.assertEqual("<opnsense/>",(Path(d)/"config.xml").read_text())

    def test_argv_order_extra_flag_missing_trailer_and_tampered_supervisor(self):
        cases=("reordered","missing","extra","trailer","daemon","monitor",
               "partial","missing-role","duplicate-pid","bool-pid",
               "prior-pid-reused","older-start","stale-supervisor")
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                pair=self.fixture(d)
                candidate=copy.deepcopy(pair[2])
                if case=="reordered":
                    a=candidate["engine"]["argv"]
                    a[1],a[2]=a[2],a[1]
                elif case=="missing":
                    candidate["engine"]["argv"].pop(2)
                elif case=="extra":
                    candidate["engine"]["argv"].append("--bogus")
                elif case=="trailer":
                    candidate["engine"]["argv"][-1]="--user=root"
                elif case=="daemon":
                    candidate["supervisor"]["daemon"]["argv"][1]="-Q"
                elif case=="monitor":
                    candidate["supervisor"]["monitor"]["argv"].append("unknown")
                elif case=="partial":
                    del candidate["supervisor"]["monitor"]
                elif case=="missing-role":
                    del candidate["engine"]
                elif case=="duplicate-pid":
                    candidate["supervisor"]["daemon"]["pid"]=201
                elif case=="bool-pid":
                    candidate["engine"]["pid"]=True
                elif case=="prior-pid-reused":
                    candidate["engine"]["pid"]=101
                    candidate["engine"]["start_ns"]=101000000000
                elif case=="older-start":
                    candidate["engine"]["start_ns"]=100000000000
                elif case=="stale-supervisor":
                    candidate["supervisor"]["monitor"]["start_ns"]=103000000000
                self.assert_denied(self.run_proof(pair,current=candidate))

    def test_changed_pid_during_double_observation_is_never_authorized(self):
        with tempfile.TemporaryDirectory() as d:
            pair=self.fixture(d)
            reader=Reader(pair[2])
            reader.edit_at=2
            self.assert_denied(self.run_proof(pair,reader=reader))
            self.assertEqual(2,reader.calls)

    def test_saved_runtime_unsafe_or_stopped_prior_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            pair=self.fixture(d,old_running=False)
            self.assert_denied(self.run_proof(pair))
        for variant in ("corrupt-args","duplicate-managed","binary-args",
                        "symlink-args","missing-evidence","bad-evidence"):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as d:
                saved,evidence,current,args=self.fixture(d)
                if variant=="corrupt-args":
                    (saved/"runtime/dvtws.args").write_bytes(b"different")
                elif variant=="duplicate-managed":
                    args.write_bytes(b"--sockarg=0x10\n")
                    # A new matching snapshot is necessary for this case.
                    (saved/"runtime/dvtws.args").write_bytes(b"--sockarg=0x10\n")
                elif variant=="binary-args":
                    (saved/"runtime/dvtws.args").write_bytes(b"\x00bad\n")
                elif variant=="symlink-args":
                    f=saved/"runtime/dvtws.args"
                    f.unlink()
                    f.symlink_to(args)
                elif variant=="missing-evidence":
                    (evidence/"processes.json").unlink()
                else:
                    (evidence/"processes.json").write_text('{"modified": true}')
                self.assert_denied(self.run_proof((saved,evidence,current,args)))

    def test_duplicate_management_flag_rejected_from_valid_sealed_backup(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            config=base/"config.xml";config.write_bytes(b"<opnsense/>");config.chmod(0o600)
            runtime=base/"runtime";runtime.mkdir()
            (runtime/"dvtws.args").write_bytes(b"--port=989 --sockarg=0x13\n")
            parent=base/"private";parent.mkdir(mode=0o700)
            snapshot=parent/"previous"
            backup.capture_previous(config,runtime,snapshot)
            with self.assertRaises(restart.RestartArgvError):
                restart.expected_engine_argv(snapshot, PATHS["engine"])

    def test_expected_supervisor_plan_or_reader_failure_denied(self):
        with tempfile.TemporaryDirectory() as d:
            pair=self.fixture(d)
            for bad in (
                {},
                {"daemon": ["/bin/evil"],"monitor":SUPERVISOR["monitor"]},
                {"daemon":SUPERVISOR["daemon"],"monitor":["/bin/sh","/tmp/evil"]},
                {"daemon":SUPERVISOR["daemon"],"monitor":["/bin/sh","bad space"]},
            ):
                self.assert_denied(self.run_proof(pair,supervisor=bad))
            class BrokenReader:
                def observe_argv(self):
                    raise OSError("read-only native kernel argv source unavailable")
            self.assert_denied(self.run_proof(pair,reader=BrokenReader()))
            self.assert_denied(self.run_proof(pair,reader=object()))


if __name__=="__main__":
    unittest.main(verbosity=2)
