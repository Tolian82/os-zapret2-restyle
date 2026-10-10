#!/usr/bin/env python3
"""Real schema-3 sealed policy + two native kernel witnesses, no appliance mutation."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import voice_native_restart_integrity as integrity
import voice_freebsd_process_security as security
import voice_freebsd_kernel_argv as argv_kernel
import voice_process_recovery_evidence as process
import voice_security_policy_evidence as policy
import voice_cutover_journal as journal


def fixture(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, ROOT/"scripts"/filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


saved_fixture = fixture("test-voice-security-policy-evidence.py", "native_integrity_policy_fixture")
argv_fixture = fixture("test-voice-freebsd-kernel-argv.py", "native_integrity_argv_fixture")


class Probe:
    def __init__(self, state, expected):
        self.state = state
        self.expected = dict(expected)
        self.calls = 0
        self.change_after = None

    def probe(self):
        self.calls += 1
        result = copy.deepcopy(self.state)
        if self.change_after is not None and self.calls >= self.change_after:
            result["supervisor"]["monitor"]["start_ns"] += 1
        return result


def running(pid_base, saved, expected):
    args_digest = process._runtime_args_digest(
        __import__("voice_cutover_backup").inspect_previous(saved)
    )

    def row(name, pid):
        return {"pid": pid, "start_ns": pid*1000000000,
                "executable": expected[name]}

    return {
        "engine": {"state": "running", "process": row("engine", pid_base),
                   "runtime_args_sha256": args_digest},
        "supervisor": {"state": "running",
                       "daemon": row("daemon", pid_base+1),
                       "monitor": row("monitor", pid_base+2)},
    }


class NativeIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="voice-native-integrity-")
        self.addCleanup(temp.cleanup)
        self.fixture = saved_fixture.SecurityPolicyTests()
        self.ctx = self.fixture.setup(temp.name)
        self.whole, self.ledger, self.saved, self.evidence, self.security_dir, \
            self.previous, self.digest = self.ctx
        self.fixture.start(self.ctx)
        self.whole.mark_mutating()
        self.expected = dict(saved_fixture.SCRIPTS)
        self.state = running(201, self.saved, self.expected)
        self.probe = Probe(self.state, self.expected)
        self.images = {201: saved_fixture.IMAGES["engine"],
                       202: saved_fixture.IMAGES["daemon"],
                       203: saved_fixture.IMAGES["monitor"]}
        self.creds = {
            201: dict(saved_fixture.CREDS["engine"]),
            202: dict(saved_fixture.CREDS["daemon"]),
            203: dict(saved_fixture.CREDS["monitor"]),
        }
        self.argv = argv_fixture.RawProvider({
            201: argv_fixture.ENGINE,
            202: argv_fixture.SUPERVISOR["daemon"],
            203: argv_fixture.SUPERVISOR["monitor"],
        })
        self.sec_reader = security.FreeBSDProcessSecurityReader(
            self.expected, dict(saved_fixture.IMAGES),
            copy.deepcopy(saved_fixture.CREDS), self.probe,
            path_reader=self.kernel_path, ps_reader=self.credentials,
        )
        self.argv_reader = argv_kernel.FreeBSDKernelArgvReader(
            self.expected, self.probe, raw_reader=self.argv
        )
        self.locks = []

    def kernel_path(self, pid):
        return self.images[pid].encode("ascii") + b"\x00"

    def credentials(self, args):
        pid = int(args[args.index("-p")+1])
        values = [self.creds[pid][field] for field in security.FIELDS]
        return str(pid) + " " + " ".join(map(str, values)) + "\n"

    def attest(self):
        return integrity.attest_previous_restart(
            journal=self.whole, previous_backup=self.saved,
            process_evidence=self.evidence, security_evidence=self.security_dir,
            expected_scripts=self.expected,
            expected_supervisor_argv=argv_fixture.SUPERVISOR,
            security_reader=self.sec_reader, argv_reader=self.argv_reader,
            require_lifecycle_owner=lambda:self.locks.append("FD9"),
            require_config_owner=lambda:self.locks.append("flock"),
        )

    def test_bound_new_process_integrity_both_native_sources(self):
        result = self.attest()
        self.assertEqual("previous-restart-integrity-observed", result["state"])
        self.assertEqual("mutating", result["whole_intent_phase"])
        self.assertEqual(self.digest, result["security_policy_sha256"])
        self.assertEqual(201, result["instances"]["engine"]["pid"])
        for key in ("safe_to_enable_voice","safe_to_finish_intent",
                    "restart_ready","media_pass"):
            self.assertIs(result[key], False)
        self.assertGreaterEqual(len(self.locks), 8)
        self.assertEqual(self.locks[0:2], ["FD9","flock"])
        self.assertEqual("mutating", self.whole.read()["phase"])
        self.assertIsNotNone(self.ledger.owned())
        self.assertEqual([201,202,203]*4, self.argv.calls)

    def test_foreign_image_credential_or_argv_denied(self):
        for case in ("engine-image", "daemon-uid", "monitor-image",
                     "engine-argv", "daemon-argv", "monitor-argv"):
            with self.subTest(case=case):
                self.setUp()
                if case=="engine-image":
                    self.images[201]="/tmp/fake_dvtws2"
                elif case=="daemon-uid":
                    self.creds[202]["euid"]=65534
                elif case=="monitor-image":
                    self.images[203]=self.expected["monitor"]
                elif case=="engine-argv":
                    self.argv.values[201]=b"/bin/sh\x00evil\x00"
                elif case=="daemon-argv":
                    self.argv.values[202]+=b"--foreign\x00"
                else:
                    self.argv.values[203]=b"/bin/sh\x00/tmp/evil\x00"
                with self.assertRaises(integrity.NativeRestartIntegrityError):
                    self.attest()
                self.assertEqual("mutating", self.whole.read()["phase"])

    def test_unbound_schema_two_or_policy_tamper_denied(self):
        original=self.whole.read()
        record=journal.new_bound_record(
            self.previous, saved_fixture.PROOF, saved_fixture.IPFW
        )
        self.whole._store({**record,"phase":"mutating",
                          "check":journal._digest({**{k:v for k,v in record.items()
                                                     if k!="check"},"phase":"mutating"})})
        with self.assertRaises(integrity.NativeRestartIntegrityError):
            self.attest()
        self.whole._store(original)
        (self.security_dir/"policy.json").write_text("foreign")
        with self.assertRaises(integrity.NativeRestartIntegrityError):
            self.attest()

    def test_changed_process_between_security_and_argv_denied(self):
        # Independent readers may each return locally stable identities
        # but different PID/start identities. Cross-check cannot be skipped.
        before=self.sec_reader.inspect_twice
        def modify_between():
            result=before()
            self.state["engine"]["process"]["pid"]=301
            self.state["engine"]["process"]["start_ns"]=301000000000
            return result
        self.sec_reader.inspect_twice=modify_between
        with self.assertRaises(Exception):
            self.attest()
        self.assertEqual("mutating",self.whole.read()["phase"])

    def test_lost_lifecycle_or_config_lease_denied(self):
        for role in ("lifecycle","config"):
            with self.subTest(role=role):
                self.setUp()
                calls=[0]
                def lease():
                    calls[0]+=1
                    if calls[0]>=2:
                        raise integrity.NativeRestartIntegrityError("lease lost")
                with self.assertRaisesRegex(integrity.NativeRestartIntegrityError,"lease lost"):
                    integrity.attest_previous_restart(
                        journal=self.whole,previous_backup=self.saved,
                        process_evidence=self.evidence,
                        security_evidence=self.security_dir,
                        expected_scripts=self.expected,
                        expected_supervisor_argv=argv_fixture.SUPERVISOR,
                        security_reader=self.sec_reader,argv_reader=self.argv_reader,
                        require_lifecycle_owner=lease if role=="lifecycle" else lambda:None,
                        require_config_owner=lease if role=="config" else lambda:None,
                    )
                self.assertEqual("mutating",self.whole.read()["phase"])

    def test_partial_or_stopped_process_refused(self):
        self.state["supervisor"]["state"]="stopped"
        with self.assertRaises((integrity.NativeRestartIntegrityError,
                                security.ProcessSecurityError, ValueError)):
            self.attest()

    def test_different_probe_instances_not_trusted(self):
        different=Probe(self.state,self.expected)
        self.argv_reader.process_probe=different
        with self.assertRaises(integrity.NativeRestartIntegrityError):
            self.attest()


if __name__ == "__main__":
    unittest.main(verbosity=2)
