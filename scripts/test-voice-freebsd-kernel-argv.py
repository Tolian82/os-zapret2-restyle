#!/usr/bin/env python3
"""Read-only native FreeBSD argv source: raw NUL bytes, stable process probes."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_process_recovery_evidence as process
import voice_restart_argv_attestation as contract
import voice_freebsd_kernel_argv as kernel

PATHS={
    "engine":"/usr/local/etc/zapret2/binaries/my/dvtws2",
    "daemon":"/usr/sbin/daemon",
    "monitor":"/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh",
}
SUPERVISOR={
    "daemon":[PATHS["daemon"],"-P","/var/run/voice-monitor.pid","-f",PATHS["monitor"]],
    "monitor":["/bin/sh",PATHS["monitor"]],
}
ENGINE=[PATHS["engine"],"--port=989","--sockarg=0x200","--user=nobody"]


class Probe:
    def __init__(self, data):
        self.data=data
        self.calls=0
        self.change_on=None
    def probe(self):
        self.calls+=1
        result=copy.deepcopy(self.data)
        if self.calls == self.change_on:
            result["engine"]["process"]["start_ns"]+=1
        return result


class RawProvider:
    def __init__(self,argv):
        self.values={
            pid:b"\x00".join(x.encode("ascii") for x in items)+b"\x00"
            for pid,items in argv.items()
        }
        self.calls=[]
        self.on_read=None
    def __call__(self,pid):
        self.calls.append(pid)
        if self.on_read:
            self.on_read(pid)
        return self.values[pid]


class ArgvReaderTests(unittest.TestCase):
    def live(self):
        def row(role,pid):
            return {"pid":pid,"start_ns":pid*1000000000,
                    "executable":PATHS[role]}
        state={
            "engine":{"state":"running","process":row("engine",201),
                      "runtime_args_sha256":"a"*64},
            "supervisor":{"state":"running","daemon":row("daemon",202),
                          "monitor":row("monitor",203)},
        }
        return state

    def argv(self):
        return {201:ENGINE,202:SUPERVISOR["daemon"],203:SUPERVISOR["monitor"]}

    def make(self, state=None, argv=None):
        state=self.live() if state is None else state
        argv=self.argv() if argv is None else argv
        probe=Probe(state)
        raw=RawProvider(argv)
        reader=kernel.FreeBSDKernelArgvReader(PATHS,probe,raw_reader=raw)
        return reader,probe,raw

    def test_roundtrip_preserves_exact_kernel_argument_boundaries(self):
        reader,probe,raw=self.make()
        result=reader.observe_argv()
        self.assertEqual(ENGINE,result["engine"]["argv"])
        self.assertEqual(SUPERVISOR["daemon"],result["supervisor"]["daemon"]["argv"])
        self.assertEqual(SUPERVISOR["monitor"],result["supervisor"]["monitor"]["argv"])
        self.assertEqual([201,202,203],raw.calls)
        self.assertEqual(2,probe.calls)

    def test_raw_argv_parser_forbids_lossy_or_ambiguous_data(self):
        invalid=(b"",b"\x00",b"/bin/sh",b"/bin/sh\x00\x00",
                 b"/bin/sh\x00--bad flag\x00",b"/bin/sh\x00\xff\x00",
                 b"/bin/sh\x00\x01\x00",b"/bin/sh\x00"*700,
                 b"/bin/sh\x00"+b"X"*(kernel.MAX_TOKEN+1)+b"\x00")
        for item in invalid:
            with self.subTest(raw=item):
                with self.assertRaises(kernel.KernelArgvError):
                    kernel.parse_kernel_argv(item)
        with self.assertRaises(kernel.KernelArgvError):
            kernel.parse_kernel_argv("/bin/sh")
        self.assertEqual(["/bin/sh","/path"],kernel.parse_kernel_argv(
            b"/bin/sh\x00/path\x00"))

    def test_unknown_stale_missing_or_duplicate_processes_fail_closed(self):
        cases=("stopped","missing","shared-pid","boolean-pid","foreign-path",
               "start-changed","missing-supervisor")
        for case in cases:
            with self.subTest(case=case):
                state=self.live()
                if case=="stopped":
                    state["supervisor"]["state"]="stopped"
                elif case=="missing":
                    state["engine"]["process"]["pid"]=None
                elif case=="shared-pid":
                    state["supervisor"]["monitor"]["pid"]=201
                elif case=="boolean-pid":
                    state["engine"]["process"]["pid"]=True
                elif case=="foreign-path":
                    state["engine"]["process"]["executable"]="/bin/echo"
                elif case=="start-changed":
                    pass
                elif case=="missing-supervisor":
                    del state["supervisor"]["monitor"]
                reader,probe,raw=self.make(state)
                if case=="start-changed":
                    probe.change_on=2
                with self.assertRaises((kernel.KernelArgvError,
                                        TypeError,KeyError)):
                    reader.observe_argv()

    def test_missing_kernel_data_does_not_fallback_to_parsed_ps(self):
        reader,probe,raw=self.make()
        raw.values[202]=b"/usr/sbin/daemon -P /var/run/test\x00"
        with self.assertRaises(kernel.KernelArgvError):
            reader.observe_argv()
        reader,probe,raw=self.make()
        raw.values[201]=b"bad output without NUL"
        with self.assertRaises(kernel.KernelArgvError):
            reader.observe_argv()

    def test_native_sysctl_never_executes_on_nonfreebsd(self):
        with patch.object(kernel.platform,"system",return_value="Linux"):
            with self.assertRaises(kernel.KernelArgvError):
                kernel.sysctl_kernel_argv(201)
        with self.assertRaises(kernel.KernelArgvError):
            kernel.sysctl_kernel_argv(True)

    def test_integration_into_non_authorizing_restart_semantics(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            config=root/"config.xml";config.write_text("<opnsense/>");config.chmod(0o600)
            runtime=root/"runtime";runtime.mkdir()
            (runtime/"dvtws.args").write_text("--port=989\n")
            private=root/"private";private.mkdir(mode=0o700)
            saved=private/"previous"
            manifest=backup.capture_previous(config,runtime,saved)
            def old(role,pid):
                return {"pid":pid,"start_ns":pid*1000000000,
                        "executable":PATHS[role]}
            prior={
                "engine":{"state":"running","process":old("engine",101),
                          "runtime_args_sha256":manifest["runtime"]["dvtws.args"]["sha256"]},
                "supervisor":{"state":"running","daemon":old("daemon",102),
                              "monitor":old("monitor",103)},
            }
            evidence=private/"process"
            process.capture_process_evidence(Probe(prior),saved,evidence,PATHS)
            reader,probe,raw=self.make()
            result=contract.inspect_restarted_argv(saved,evidence,PATHS,
                                                  SUPERVISOR,reader)
            self.assertEqual("review-required",result["state"])
            self.assertFalse(result["can_activate"])
            self.assertFalse(result["media_pass"])
            self.assertFalse(result["startup_ready"])
            self.assertEqual(4,probe.calls)
            self.assertEqual(6,len(raw.calls))
            raw.values[201]=b"\x00".join(a.encode() for a in
                                       ENGINE[:-1]+["--user=root"])+b"\x00"
            denied=contract.inspect_restarted_argv(saved,evidence,PATHS,
                                                   SUPERVISOR,reader)
            self.assertEqual("blocked",denied["state"])
            self.assertFalse(denied["safe_to_mutate"])


if __name__=="__main__":
    unittest.main(verbosity=2)
