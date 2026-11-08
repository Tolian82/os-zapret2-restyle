#!/usr/bin/env python3
"""Hard PR/VM fan-out budget: offline, zero-network GitHub policy regression."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MIGRATED_NATIVE = (
    'stage2-configd-worker-readonly.yml',
    'stage2-native-production-build.yml',
    'stage2-original-old-fd9-nonrecursive.yml',
    'stage2-real-firmware-unlock-bypass.yml',
    'stage2-real-held-fd9-native-pkg.yml',
    'stage2-real-native-boot-syshook.yml',
    'stage2-real-native-clean-install.yml',
    'stage2-real-native-force-reinstall.yml',
    'stage2-real-native-locked-unsafe-owner.yml',
    'stage2-real-native-running-upgrade.yml',
    'stage2-real-native-shared-voice.yml',
    'stage2-real-native-stopped-upgrade.yml',
    'stage2-real-native-unsafe-owner-replacement.yml',
    'stage2-real-native-voice-http.yml',
    'stage5-native-browser-wan.yml',
    'stage5-native-cross-clean-running.yml',
    'stage5-native-real-shared-voice-reboot.yml',
    'stage5-native-running-voice.yml',
    'stage5-native-single-artifact.yml',
)
CONCURRENCY_GROUP = ('group: ${{ github.workflow }}-${{ github.event_name }}-'
                     '${{ github.event.pull_request.number || github.run_id }}')
CANCEL = "cancel-in-progress: ${{ github.event_name == 'pull_request' }}"


def normalize_revision(contents):
    return re.sub(r'(?m)^(PLUGIN_REVISION=)[ \t]*\d+[ \t]*$',
                  r'\1 __REVISION__', contents)


class BudgetContracts(unittest.TestCase):
    def test_only_metadata_bump_is_nonsemantic(self):
        base = 'PLUGIN_NAME= zapret2-restyle\nPLUGIN_REVISION=    2\nPLUGIN_DEPENDS= python\n'
        bumped = base.replace('REVISION=    2', 'REVISION=    3')
        semantic = bumped.replace('DEPENDS= python', 'DEPENDS= python git')
        self.assertEqual(normalize_revision(base), normalize_revision(bumped))
        self.assertNotEqual(normalize_revision(base), normalize_revision(semantic))

    def test_all_native_vm_workflows_omit_version_only_makefile_trigger(self):
        found = list((ROOT / '.github/workflows').glob('*.yml'))
        self.assertGreaterEqual(len(found), 50)
        for path in found:
            content = path.read_text(encoding='utf-8')
            if 'vmactions/opnsense-vm' not in content and 'vmactions/freebsd-vm' not in content:
                continue
            self.assertNotRegex(content, r'(?m)^      - Makefile\s*$',
                                f'{path.name}: broad VM triggered by every revision')

    def test_all_19_expensive_migrated_workflows_have_pr_safe_concurrency(self):
        self.assertEqual(len(MIGRATED_NATIVE), len(set(MIGRATED_NATIVE)))
        self.assertEqual(len(MIGRATED_NATIVE), 19)
        for name in MIGRATED_NATIVE:
            body = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
            self.assertIn('  pull_request:', body, name)
            self.assertIn(CONCURRENCY_GROUP, body, name)
            self.assertIn(CANCEL, body, name)
            self.assertNotRegex(body, r'(?m)^      - Makefile\s*$', name)

    def test_native_workflow_yaml_change_does_not_self_trigger_vm(self):
        # Workflow YAML is checked by this fast PR gate; native replay is manual.
        for name in MIGRATED_NATIVE:
            body = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
            self.assertNotIn('      - .github/workflows/' + name, body, name)

    def test_core_ci_retains_exact_revision_only_semantic_classifier(self):
        body = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        for term in ('old_makefile=$(git show', 'new_makefile=$(git show',
                     'classified_changed', 'if [[ "${old_makefile}" == "${new_makefile}" ]]'):
            self.assertIn(term, body)
        self.assertIn('cancel-in-progress: ${{ github.event_name ==', body)

    def test_watchdog_hourly_fallback_and_ci_event(self):
        body = (ROOT / '.github/workflows/pr-completion-watchdog.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '7 * * * *'", body)
        self.assertIn('workflow_run:', body)
        self.assertIn('cancel-in-progress: false', body)
        self.assertNotIn("cron: '7,17,27,37,47,57 * * * *'", body)

    def test_canonical_rules_and_pr_gate_are_mandatory(self):
        rules = (ROOT / 'docs/GITHUB_PUBLICATION.md').read_text(encoding='utf-8')
        for identifier in range(66, 71):
            self.assertRegex(rules, rf'(?m)^GH-{identifier:03d}\. ')
        gate = (ROOT / '.github/workflows/pr-title.yml').read_text(encoding='utf-8')
        self.assertIn('python3 scripts/test-github-workflow-budget.py', gate)


if __name__ == '__main__':
    unittest.main(verbosity=2)
