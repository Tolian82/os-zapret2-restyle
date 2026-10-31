#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hook_audit', HERE / 'stage0-hook-lifecycle-audit.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class HookAuditFixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        subprocess.check_call(['git', 'init', '-q', str(self.root)])
        scripts = {
            mod.HOOKS[0]: '"${SERVICE_SCRIPT}" status\n"${LOCKF_BIN}" -s -t 5 9\n) 9>"$LIFECYCLE_LOCK_FILE"\nSHARED_APPLY_JOURNAL=x\n"${SERVICE_SCRIPT}" stop\nPYTHON_BIN=python3.13\n',
            mod.HOOKS[1]: '"${SERVICE_SCRIPT}" status\nunknown owner; incomplete zapret lifecycle\n"${SERVICE_SCRIPT}" stop\n',
            mod.HOOKS[2]: '# No service actions\n',
            mod.HOOKS[3]: 'REPLACEMENT_RESTART_MARKER=x\nCONFIGCTL=abc\nKILL_BIN=kill\n"${KILL_BIN}" -TERM "${configd_old_worker}"\nconfigd_new_worker=x\nEXTRA_PYTHON=python3.13\n',
            mod.SERVICE: 'shared_apply_operation.py\nipfw\n',
        }
        for path, content in scripts.items():
            loc = self.root / path
            loc.parent.mkdir(parents=True, exist_ok=True)
            loc.write_text(content)
        subprocess.check_call(['git', '-C', str(self.root), 'add', '.'])
        subprocess.check_call(['git', '-C', str(self.root), '-c', 'user.name=CI', '-c', 'user.email=ci@example.invalid', 'commit', '-qm', 'fixture'])
        self.head = mod.cmd(self.root, 'rev-parse', 'HEAD')

    def test_exact_head_inventory_flags_risks(self):
        report = mod.inventory(self.root, self.head)
        flags = report['observations']
        self.assertTrue(flags['incoming_preinstall_requires_python_for_cold_path'])
        self.assertTrue(flags['old_predeinstall_stop_has_no_hook_fd9'])
        self.assertTrue(flags['postdeinstall_no_service_action'])
        self.assertTrue(flags['postinstall_configd_worker_signal'])
        self.assertTrue(flags['source_service_is_nonexecutable'])
        self.assertFalse(report['target_pkg_hook_execution_order_tested'])
        self.assertEqual(report['paths'][mod.HOOKS[0]]['matches']['service_status'], [1])

    def test_refuses_moved_head(self):
        with self.assertRaisesRegex(ValueError, 'HEAD mismatch'):
            mod.inventory(self.root, '0' * 40)

    def test_refuses_untracked_missing_hook(self):
        subprocess.check_call(['git', '-C', str(self.root), 'rm', '-q', mod.HOOKS[2]])
        subprocess.check_call(['git', '-C', str(self.root), '-c', 'user.name=CI', '-c', 'user.email=ci@example.invalid', 'commit', '-qm', 'missing'])
        with self.assertRaisesRegex(ValueError, 'missing authoritative tracked'):
            mod.inventory(self.root, mod.cmd(self.root, 'rev-parse', 'HEAD'))

    def test_working_tree_edits_cannot_affect_audit(self):
        (self.root / mod.HOOKS[1]).write_text('changed outside exact head\n')
        report = mod.inventory(self.root, self.head)
        self.assertTrue(report['observations']['old_predeinstall_stop_has_no_hook_fd9'])

    def test_executable_git_mode_is_not_auto_assumed(self):
        p = self.root / mod.SERVICE
        p.chmod(0o755)
        subprocess.check_call(['git', '-C', str(self.root), 'add', mod.SERVICE])
        subprocess.check_call(['git', '-C', str(self.root), '-c', 'user.name=CI', '-c', 'user.email=ci@example.invalid', 'commit', '-qm', 'make executable'])
        report = mod.inventory(self.root, mod.cmd(self.root, 'rev-parse', 'HEAD'))
        self.assertFalse(report['observations']['source_service_is_nonexecutable'])


if __name__ == '__main__':
    unittest.main()
