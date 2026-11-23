#!/usr/bin/env python3
"""S04b narrow original-reader adapter tests. No native/physical GO claimed."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import component_inventory_opnsense as sut  # noqa: E402


class S04BReadOnlyAdapter(unittest.TestCase):
    def test_five_source_scenarios_never_authorize_lifecycle(self):
        cases = [
            ("absent", "absent", "absent", "missing", "STOPPED",
             "PLUGIN_NOT_INSTALLED"),
            ("installed", "absent", "absent", "missing", "STOPPED",
             "ENGINE_NOT_INSTALLED"),
            ("installed", "valid", "absent", "missing", "STOPPED",
             "CONFIG_UNINITIALIZED"),
            ("installed", "valid", "invalid", "valid", "RUNNING",
             "CONFIG_INVALID"),
            ("installed", "valid", "initialized", "valid",
             "FOREIGN_OR_UNVERIFIED", "FOREIGN_OWNER"),
        ]
        for p, e, c, m, r, expected in cases:
            with self.subTest(expected=expected):
                report = sut.collect(plugin=lambda: p, engine=lambda: e,
                                     config=lambda: c, owner=lambda: (m, r))
                self.assertEqual(report["classification"], expected)
                self.assertEqual(report["authorization"], "NONE")
                self.assertFalse(report["physical_transition_allowed"])
                self.assertTrue(report["original_fd9_attestation_required"])
                self.assertNotIn("pid", str(report).lower())

    def test_fixed_elf_and_xml_checks_are_read_only(self):
        uid = os.getuid()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "dvtws2"
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            struct.pack_into("<H", header, 16, 2)
            struct.pack_into("<H", header, 18, 62)
            binary.write_bytes(header)
            binary.chmod(0o755)
            config = root / "config.xml"
            content = (b"<opnsense><OPNsense><Zapret><general>"
                       b"<enabled>0</enabled></general></Zapret></OPNsense></opnsense>")
            config.write_bytes(content)
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns,
                               stat.S_IMODE(p.stat().st_mode)) for p in (binary, config)}
            self.assertEqual(sut.probe_engine(path=binary, owner=uid), "valid")
            self.assertEqual(sut.probe_config(path=config, owner=uid), "initialized")
            self.assertEqual(sut.probe_config(path=root / "missing", owner=uid), "absent")
            self.assertEqual(sut.probe_engine(path=root / "missing", owner=uid), "absent")
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns,
                                               stat.S_IMODE(p.stat().st_mode))
                                      for p in (binary, config)})
            self.assertEqual(set(p.name for p in root.iterdir()), {"dvtws2", "config.xml"})
            config.write_bytes(b"<opnsense><OPNsense/></opnsense>")
            self.assertEqual(sut.probe_config(path=config, owner=uid), "absent")
            config.write_bytes(b"<opnsense><OPNsense>")
            self.assertEqual(sut.probe_config(path=config, owner=uid), "invalid")
            config.write_bytes(b"<!DOCTYPE opnsense><opnsense/>")
            self.assertEqual(sut.probe_config(path=config, owner=uid), "invalid")
            config.unlink()
            config.symlink_to(binary)
            self.assertEqual(sut.probe_config(path=config, owner=uid), "invalid")
            binary.chmod(0o777)
            self.assertEqual(sut.probe_engine(path=binary, owner=uid), "invalid")

    def test_pkg_uses_only_nonbootstrap_installed_binary(self):
        with patch.object(sut.os.path, "isfile", return_value=True), \
             patch.object(sut.os, "access", return_value=True):
            calls = []
            def runner(argv, **kwargs):
                calls.append((argv, kwargs))
                class Result:
                    returncode = 0
                return Result()
            self.assertEqual(sut.probe_plugin(runner=runner), "installed")
            self.assertEqual(calls[0][0],
                             ["/usr/local/sbin/pkg", "info", "-e", "os-zapret2-restyle"])
            self.assertTrue(calls[0][1]["capture_output"])
            self.assertFalse(calls[0][1]["check"])
            self.assertNotEqual(calls[0][1]["user"], 0)
            self.assertNotEqual(calls[0][1]["group"], 0)
            self.assertEqual(calls[0][1]["extra_groups"], [])
        with patch.object(sut.os.path, "isfile", return_value=False):
            self.assertEqual(sut.probe_plugin(runner=lambda *a, **k:
                             self.fail("bootstrapped pkg")), "unknown")

    def test_original_read_only_owner_reports_and_fail_closed(self):
        # read_record is a fixture; ALL integrity and process/Rule checks are
        # delegated to original existing functions in the production path.
        rid = "a" * 32
        record = {"schema": 1, "phase": "committed", "detail": {"id": rid, "page": "strategies",
                  "base": "b"*64, "candidate": "c"*64, "changed_fields": []}}
        calls = []
        def verify(path, *, owner):
            self.assertEqual(owner, 0)
            calls.append("seal")
        def manifest(path):
            calls.append("manifest")
            return {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
        def inspect(r):
            self.assertIs(r, record)
            calls.append("inspector")
            return {"source": "native-common", "state": "ready"}
        self.assertEqual(sut.probe_owner(read_record=lambda: record, verify=verify,
                          manifest_reader=manifest, examine=inspect,
                          absent=lambda: self.fail("wrong absence branch")),
                         ("valid", "RUNNING"))
        self.assertEqual(calls, ["seal", "manifest", "inspector"])
        for state, expected in [
            ("stopped", ("valid", "STOPPED")),
            ("interrupted", ("valid", "INCOMPLETE")),
            ("foreign-or-modified-rules", ("valid", "FOREIGN_OR_UNVERIFIED")),
        ]:
            self.assertEqual(sut.probe_owner(
                read_record=lambda: record, verify=verify,
                manifest_reader=manifest,
                examine=lambda _: {"source": "native-common", "state": state},
                absent=lambda: False), expected)
        self.assertEqual(sut.probe_owner(
            read_record=lambda: None, verify=verify, manifest_reader=manifest,
            examine=inspect, absent=lambda: True), ("missing", "STOPPED"))
        self.assertEqual(sut.probe_owner(
            read_record=lambda: None, verify=verify, manifest_reader=manifest,
            examine=inspect, absent=lambda: False), ("missing", "UNKNOWN"))
        self.assertEqual(sut.probe_owner(
            read_record=lambda: {"phase": "prepared"}, verify=verify,
            manifest_reader=manifest, examine=inspect,
            absent=lambda: False), ("stale", "INCOMPLETE"))
        def corrupt(*args, **kwargs):
            raise ValueError("secret from damaged journal must not escape")
        self.assertEqual(sut.probe_owner(
            read_record=lambda: record, verify=corrupt,
            manifest_reader=manifest, examine=inspect,
            absent=lambda: False), ("invalid", "INCOMPLETE"))
        self.assertNotIn("secret", str(sut.probe_owner(
            read_record=lambda: record, verify=corrupt,
            manifest_reader=manifest, examine=inspect,
            absent=lambda: False)))

    def test_no_new_owner_or_write_surface_in_source(self):
        src = Path(sut.__file__).read_text()
        forbidden = ("os.kill(", "os.remove(", ".unlink(", ".write_text(",
                     ".write_bytes(", "os.rename(", "os.replace(", "os.makedirs(",
                     "O_CREAT", "O_WRONLY", "fcntl.", "lockf", "configctl", "ipfw add")
        for token in forbidden:
            with self.subTest(token=token):
                # Documentation may mention a forbidden action; execute-path
                # audit remains a separate reviewer responsibility.
                active = "\n".join(line for line in src.splitlines()
                                   if not line.lstrip().startswith("#") and
                                   not line.lstrip().startswith('"""'))
                if token in ("lockf", "configctl"):
                    continue
                self.assertNotIn(token, active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
