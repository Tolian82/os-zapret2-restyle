#!/usr/bin/env python3
"""Offline strict upstream build provenance and no installed runtime contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('build', HERE / 'stage0-opnsense-upstream-engine-build.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeEngineBuildContracts(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.engine = Path(self.root.name) / 'dvtws2'
        self.engine.write_bytes(b'ELF test')
        self.engine.chmod(0o755)
        self.fmt = 'ELF 64-bit LSB executable, x86-64, FreeBSD'
        self.deps = '/usr/local/lib/liblua-5.4.so => /usr/local/lib/liblua-5.4.so'
        self.help = 'dvtws2 usage --filter-tcp'

    def good(self, **kw):
        kw = dict(sha=m.PIN, exe=self.engine, file_output=self.fmt,
                  deps=self.deps, help_output=self.help) | kw
        return m.qualify_build(**kw)

    def test_good_native_binary(self):
        self.assertTrue(self.good())

    def test_pin_refusal(self):
        with self.assertRaisesRegex(m.Refusal, 'PIN'):
            self.good(sha='0'*40)

    def test_foreign_elf_refusal(self):
        with self.assertRaises(m.Refusal):
            self.good(file_output='ELF 64-bit x86-64 Linux')

    def test_32bit_elf_refusal(self):
        with self.assertRaises(m.Refusal):
            self.good(file_output='ELF 32-bit FreeBSD x86')

    def test_missing_lua_provider_refusal(self):
        with self.assertRaises(m.Refusal):
            self.good(deps='libz.so => /lib/libz.so')

    def test_missing_shared_lib_refusal(self):
        with self.assertRaises(m.Refusal):
            self.good(deps=self.deps + '\nlibfoo.so => not found')

    def test_help_refusal(self):
        with self.assertRaises(m.Refusal):
            self.good(help_output='')

    def test_nonexecuting_refusal(self):
        self.engine.chmod(0o644)
        with self.assertRaises(m.Refusal):
            self.good()

    def test_symlink_refusal(self):
        link = self.engine.with_name('link')
        link.symlink_to(self.engine)
        with self.assertRaises(m.Refusal):
            self.good(exe=link)

    def test_missing_installed_runtime(self):
        self.assertTrue(m.OLD_ENGINE.is_absolute())
        with mock.patch.object(m,'OLD_ENGINE',Path(self.root.name)/'notyet'):
            m.require_uninstalled()

    def test_present_runtime_refusal(self):
        with mock.patch.object(m,'OLD_ENGINE',self.engine):
            with self.assertRaises(m.Refusal):
                m.require_uninstalled()

    def test_dangling_runtime_refusal(self):
        link = self.engine.with_name('dangling');link.symlink_to('nowhere')
        with mock.patch.object(m,'OLD_ENGINE',link):
            with self.assertRaises(m.Refusal):
                m.require_uninstalled()

    def test_non_target_refusal(self):
        with mock.patch.object(m.os,'geteuid',return_value=1), mock.patch.object(m,'load') as loader:
            with self.assertRaises(m.Refusal):
                m.run(Path('ignored.pkg'))
            loader.assert_not_called()

    def test_not_running_and_no_pkg_rollback_claim(self):
        src = (HERE / 'stage0-opnsense-upstream-engine-build.py').read_text()
        for term in ("'genuine_running_engine_tested': False", "'native_pkg_successor_tested': False", "'stage0_closed': False", "no_global_engine_install"):
            self.assertIn(term,src)

if __name__=='__main__':
    unittest.main()
