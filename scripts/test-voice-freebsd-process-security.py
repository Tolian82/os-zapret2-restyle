#!/usr/bin/env python3
"""Offline tests for FreeBSD kernel text path + numeric UID/GID, no live router."""
from __future__ import annotations

import copy
import ctypes
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_freebsd_process_security as security

SCRIPTS = {
    "engine": "/usr/local/etc/zapret2/binaries/my/dvtws2",
    "daemon": "/usr/sbin/daemon",
    "monitor": "/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh",
}
# The monitor's actual executable is /bin/sh, NOT the script path.
IMAGES = {"engine": SCRIPTS["engine"], "daemon": SCRIPTS["daemon"],
          "monitor": "/bin/sh"}
ROOT_CREDS = dict.fromkeys(security.FIELDS, 0)
NOBODY_CREDS = dict.fromkeys(security.FIELDS, 65534)
EXPECTED = {"engine": NOBODY_CREDS, "daemon": ROOT_CREDS,
            "monitor": ROOT_CREDS}


class ProcessProbe:
    def __init__(self, inventory):
        self.inventory = inventory
        self.calls = 0
        self.change_on = None

    def probe(self):
        self.calls += 1
        result = copy.deepcopy(self.inventory)
        if self.change_on == self.calls:
            result["engine"]["process"]["start_ns"] += 1
        return result


def inventory():
    def role(name, pid):
        return {"pid": pid, "start_ns": pid*1000000000,
                "executable": SCRIPTS[name]}
    return {
        "engine": {"state": "running", "process": role("engine", 201),
                   "runtime_args_sha256": "a"*64},
        "supervisor": {"state": "running", "daemon": role("daemon", 202),
                       "monitor": role("monitor", 203)},
    }


class FakeNative:
    def __init__(self):
        self.paths = {201: IMAGES["engine"], 202: IMAGES["daemon"],
                      203: IMAGES["monitor"]}
        self.creds = {201: NOBODY_CREDS.copy(), 202: ROOT_CREDS.copy(),
                      203: ROOT_CREDS.copy()}
        self.path_calls = []
        self.ps_calls = []
        self.fail_ps = False

    def path(self, pid):
        self.path_calls.append(pid)
        return self.paths[pid].encode("ascii") + b"\x00"

    def ps(self, argv):
        self.ps_calls.append(tuple(argv))
        if self.fail_ps:
            raise security.ProcessSecurityError("ps unavailable")
        if argv[0] != "/bin/ps" or argv[1] != "-p" or \
           tuple(argv[3:]) != security.PS_COLUMNS:
            raise AssertionError("unexpected ps argv")
        pid = int(argv[2])
        row = self.creds[pid]
        return " " .join([str(pid)] + [str(row[k]) for k in security.FIELDS]) + "\n"


class SecurityTests(unittest.TestCase):
    def make(self, state=None):
        probe = ProcessProbe(inventory() if state is None else state)
        native = FakeNative()
        reader = security.FreeBSDProcessSecurityReader(
            SCRIPTS, IMAGES, EXPECTED, probe,
            path_reader=native.path, ps_reader=native.ps,
        )
        return reader, probe, native

    def test_kernel_path_parser_requires_exact_single_nul_absolute_path(self):
        self.assertEqual("/bin/sh", security.parse_kernel_path(b"/bin/sh\x00"))
        bad = (b"", b"\x00", b"bin/sh\x00", b"/bin/sh",
               b"/bin/sh\x00\x00", b"/bin/sh\x00/evil\x00",
               b"/bin/../sh\x00", b"/bin/has space\x00",
               b"/bin/\xff\x00", b"/bin/sh\n\x00",
               b"/" + b"x"*security.MAX_PATH_BYTES + b"\x00")
        for value in bad:
            with self.subTest(raw=value[:30]):
                with self.assertRaises(security.ProcessSecurityError):
                    security.parse_kernel_path(value)

    def test_stable_three_roles_with_interpreter_and_exact_numeric_ids(self):
        reader, probe, native = self.make()
        result = reader.inspect_twice()
        self.assertEqual("review-required", result["state"])
        self.assertEqual("matching-process-path-and-ids-only", result["reason"])
        self.assertEqual("/bin/sh", result["roles"]["monitor"]["image"])
        self.assertEqual(65534, result["roles"]["engine"]["credentials"]["euid"])
        self.assertEqual([201,202,203,201,202,203], native.path_calls)
        self.assertEqual(4, probe.calls)
        self.assertEqual(6, len(native.ps_calls))
        for column in ("can_activate", "can_recover_automatically", "safe_to_mutate",
                       "startup_ready", "media_pass"):
            self.assertIs(result[column], False)

    def test_image_and_uid_mismatch_refuses_foreign_process(self):
        for case in ("engine-image", "monitor-image", "engine-uid",
                     "daemon-uid", "saved-gid"):
            with self.subTest(case=case):
                reader, probe, native = self.make()
                if case == "engine-image":
                    native.paths[201] = "/tmp/dvtws2"
                elif case == "monitor-image":
                    native.paths[203] = SCRIPTS["monitor"]
                elif case == "engine-uid":
                    native.creds[201]["euid"] = 0
                elif case == "daemon-uid":
                    native.creds[202]["ruid"] = 65534
                else:
                    native.creds[203]["svgid"] = 65534
                with self.assertRaises(security.ProcessSecurityError):
                    reader.inspect_twice()

    def test_pid_start_change_partial_foreign_and_duplicate_refused(self):
        for case in ("start-changed","duplicate-pid","boolean-pid",
                     "missing-monitor","wrong-script","stopped","negative-start"):
            with self.subTest(case=case):
                state = inventory()
                if case == "duplicate-pid":
                    state["supervisor"]["monitor"]["pid"] = 201
                elif case == "boolean-pid":
                    state["engine"]["process"]["pid"] = True
                elif case == "missing-monitor":
                    del state["supervisor"]["monitor"]
                elif case == "wrong-script":
                    state["supervisor"]["monitor"]["executable"] = "/tmp/evil"
                elif case == "stopped":
                    state["engine"]["state"] = "stopped"
                elif case == "negative-start":
                    state["engine"]["process"]["start_ns"] = -1
                reader, probe, native = self.make(state)
                if case == "start-changed":
                    probe.change_on = 2
                with self.assertRaises(security.ProcessSecurityError):
                    reader.observe_security()

    def test_non_numeric_wrong_pid_extra_line_and_failed_queries_rejected(self):
        for value in ("wrong-pid","non-numeric","extra-line","missing",
                      "overflow","exception"):
            with self.subTest(value=value):
                reader,probe,native = self.make()
                original = native.ps
                def bad(argv):
                    if value == "exception":
                        raise OSError("kernel unavailable")
                    result = original(argv)
                    if value == "wrong-pid":
                        return "999 " + " ".join(result.split()[1:]) + "\n"
                    if value == "non-numeric":
                        return result.replace("65534", "nobody", 1)
                    if value == "extra-line":
                        return result + result
                    if value == "missing":
                        return ""
                    if value == "overflow":
                        return "201 " + "4294967296 "*6 + "\n"
                    return result
                reader.ps_reader = bad
                with self.assertRaises((security.ProcessSecurityError, OSError)):
                    reader.observe_security()

    def test_constructor_requires_exact_image_credential_sets(self):
        reader,probe,native = self.make()
        for images, creds in (
            ({**IMAGES,"monitor":"/tmp/../bin/sh"},EXPECTED),
            ({**IMAGES,"monitor":"/bin/sh with space"},EXPECTED),
            ({"engine":IMAGES["engine"],"daemon":IMAGES["daemon"]},EXPECTED),
            (IMAGES,{**EXPECTED,"engine":{**NOBODY_CREDS,"euid":True}}),
            (IMAGES,{**EXPECTED,"engine":{**NOBODY_CREDS,"euid":-1}}),
            (IMAGES,{"engine":NOBODY_CREDS}),
        ):
            with self.subTest(images=images,creds=creds):
                with self.assertRaises(security.ProcessSecurityError):
                    security.FreeBSDProcessSecurityReader(
                        SCRIPTS, images, creds, probe,
                        path_reader=native.path, ps_reader=native.ps,
                    )

    def test_second_observation_drift_refused(self):
        reader,probe,native = self.make()
        read_path=native.path
        def changing_path(pid):
            if len(native.path_calls) == 3 and pid == 201:
                native.paths[201] = "/tmp/new_dvtws2"
            return read_path(pid)
        reader.path_reader=changing_path
        with self.assertRaises(security.ProcessSecurityError):
            reader.inspect_twice()

    @unittest.skipUnless(sys.platform.startswith("freebsd"),
                         "only the FreeBSD 15 CI VM has kernel process OIDs")
    def test_actual_freebsd_self_process_sysctl_and_numeric_ps(self):
        # Real read-only system calls in FreeBSD CI, but NEVER a service
        # PID, IPFW rule, Config mutation, or production Voice activation.
        pid = os.getpid()
        try:
            raw_path = security.sysctl_kernel_path(pid)
        except security.ProcessSecurityError as exc:
            # CI-only read-only probe; never substitute a fake for a failed
            # native check. Capture the actual OID/errno behavior on FreeBSD.
            libc = ctypes.CDLL(None, use_errno=True)
            byname = libc.sysctlbyname
            byname.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                               ctypes.POINTER(ctypes.c_size_t),
                               ctypes.c_void_p, ctypes.c_size_t]
            byname.restype = ctypes.c_int
            n = ctypes.c_size_t()
            ctypes.set_errno(0)
            name_rc = byname(f"kern.proc.pathname.{pid}".encode(),
                             None, ctypes.byref(n), None, 0)
            name_errno = ctypes.get_errno()
            nametomib = libc.sysctlnametomib
            nametomib.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int),
                                  ctypes.POINTER(ctypes.c_size_t)]
            nametomib.restype = ctypes.c_int
            mib = (ctypes.c_int * 24)()
            depth = ctypes.c_size_t(24)
            ctypes.set_errno(0)
            mib_rc = nametomib(b"kern.proc.pathname", mib,
                               ctypes.byref(depth))
            mib_errno = ctypes.get_errno()
            numeric_rc = None
            numeric_errno = None
            numeric_length = None
            if mib_rc == 0 and 0 < depth.value < 24:
                mib[depth.value] = pid
                native_sysctl = libc.sysctl
                native_sysctl.argtypes = [ctypes.POINTER(ctypes.c_int),
                                          ctypes.c_uint, ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_size_t),
                                          ctypes.c_void_p, ctypes.c_size_t]
                native_sysctl.restype = ctypes.c_int
                numeric_size = ctypes.c_size_t()
                ctypes.set_errno(0)
                numeric_rc = native_sysctl(mib, depth.value + 1, None,
                                           ctypes.byref(numeric_size), None, 0)
                numeric_errno = ctypes.get_errno()
                numeric_length = numeric_size.value
            self.fail(f"{exc}; FreeBSD read-only OID probe: "
                      f"byname_rc={name_rc} errno={name_errno} len={n.value}; "
                      f"nametomib_rc={mib_rc} errno={mib_errno} depth={depth.value}; "
                      f"numeric_rc={numeric_rc} errno={numeric_errno} "
                      f"len={numeric_length}")
        actual_path = security.parse_kernel_path(raw_path)
        self.assertTrue(actual_path.startswith("/"))
        creds = security.ps_numeric_credentials(pid)
        self.assertEqual(os.geteuid(),creds["euid"])
        self.assertEqual(os.getuid(),creds["ruid"])
        self.assertEqual(os.getegid(),creds["egid"])
        self.assertEqual(os.getgid(),creds["rgid"])

    def test_native_readers_never_run_on_linux(self):
        with patch.object(security.platform,"system",return_value="Linux"):
            with self.assertRaises(security.ProcessSecurityError):
                security.sysctl_kernel_path(201)
            with self.assertRaises(security.ProcessSecurityError):
                security.ps_numeric_credentials(201)
        with self.assertRaises(security.ProcessSecurityError):
            security.sysctl_kernel_path(True)
        with self.assertRaises(security.ProcessSecurityError):
            security.ps_numeric_credentials(0)


if __name__=="__main__":
    unittest.main(verbosity=2)
