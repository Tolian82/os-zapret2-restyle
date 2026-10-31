#!/usr/bin/env python3
"""Real Git index mode tests and isolated fake action/GUI callpaths."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('stage0-configd-callpath-audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CallPath(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        self.actions = audit.ACTIONS
        body = '''[start]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh start
type:script
[stop]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh stop
type:script
[status]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status; exit 0
type:script_output
[voice_inspect]
command:/usr/local/bin/python3.13 /usr/local/opnsense/scripts/OPNsense/Zapret/backend/voice_live_inspect.py; exit 0
type:script_output
[strategy_lab_start]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh start
type:script_output
[setup_install]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh install
type:script
[extra_resources_install]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh install
type:script
[shared_apply]
command:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh shared-apply-run
type:script_output
'''
        self.write(self.actions,body)
        for path in ('zapret_service.sh','strategy_lab_launcher.sh','setup_launcher.sh','extra_resources_launcher.sh'):
            self.write('src/opnsense/scripts/OPNsense/Zapret/'+path,'#!/bin/sh\n')
        self.write('src/opnsense/scripts/OPNsense/Zapret/backend/voice_live_inspect.py','print(1)\n')
        self.write(audit.CONTROLLERS+'FakeController.php', '''<?php
$backend->configdRun('zapret stop', false, 10);
$backend->configdRun($command, false, 10);
''')
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Test','-c','user.email=test@local', 'commit','-qm','fixture'],check=True)

    def write(self,path,text):
        dest=self.root / path
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(text)

    def test_positive_and_mode_warning(self):
        result=audit.audit(self.root)
        self.assertEqual(result['registered_actions'],8)
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['explicit_python_actions'],['voice_inspect'])
        self.assertIn('stop',result['source_mode_review'])
        self.assertEqual(result['unresolved_controller_refs'],1)
        self.assertFalse(result['owner_target_qualified'])
        src='src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'
        subprocess.run(['git','-C',str(self.root),'update-index','--chmod=+x',src],check=True)
        next_result=audit.audit(self.root)
        self.assertNotIn('stop',next_result['source_mode_review'])
        with self.assertRaisesRegex(ValueError,'wrong exact HEAD'):
            audit.audit(self.root, '0'*40)

    def test_unknown_controller_and_missing_script_rejected(self):
        ref=audit.CONTROLLERS+'FakeController.php'
        self.write(ref,"<?php\n$backend->configdRun('zapret missing', false, 10);\n")
        issue=audit.audit(self.root)['errors']
        self.assertTrue(any('unknown configd action missing' in s for s in issue))
        reg=self.root/self.actions
        reg.write_text(reg.read_text().replace('strategy_lab_launcher.sh','absent_script.sh'))
        issue=audit.audit(self.root)['errors']
        self.assertTrue(any('missing tracked source' in s for s in issue))
        with self.assertRaisesRegex(ValueError,'missing required configd'):
            audit.parse_actions('[start]\ncommand:/usr/local/test.sh\ntype:script\n')


if __name__ == '__main__':
    unittest.main()
