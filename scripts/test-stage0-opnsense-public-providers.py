#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('audit', str(Path(__file__).with_name('stage0-opnsense-public-providers.py')))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PublicProviders(unittest.TestCase):
    def setUp(self):
        ctx = tempfile.TemporaryDirectory()
        self.addCleanup(ctx.cleanup)
        self.root = Path(ctx.name)
        self.html = self.root / 'index.html'
        self.plist = self.root / 'plist'
        self.defaults = self.root / 'defaults.mk'
        self.plugins = self.root / 'plugins.mk'
        # 50+ unrelated packages exercise full index, avoid single-source regex.
        names = [f'unrelated-{i}.pkg' for i in range(55)] + [f'{p}-1.pkg' for p in audit.REQUIRED]
        self.set_index(names)
        self.plist.write_text('/usr/local/bin/python3\n')
        self.defaults.write_text('\n'.join(['VERSIONBIN= /usr/local/sbin/opnsense-version',
                                            '_PLUGIN_ABI!= ${VERSIONBIN} -a', 'PYTHONLINK= /usr/local/bin/python3',
                                            '_PLUGIN_PYTHON!=${PYTHONLINK} -V', 'PLUGIN_PYTHON?= 313',
                                            'PLUGIN_ABIS?=\t26.7']))
        self.plugins.write_text('PLUGIN_DEPENDS\n${PKG} query \'%n: { version: "%v", origin: "%o" }\'')

    def set_index(self, names):
        self.html.write_text('<h1>Index of /pub/opnsense/FreeBSD:15:amd64/26.7/latest/All/</h1>\n'
                             + ''.join('<a href="%s">%s</a>\n' % (n, n) for n in names))

    def check(self):
        return audit.audit(self.html, self.plist, self.defaults, self.plugins)

    def test_public_candidates_and_no_target_claim(self):
        x = self.check()
        self.assertEqual(x['public_candidates']['python313'], ['python313-1.pkg'])
        self.assertTrue(x['generic_python_link_in_core_plist'])
        self.assertFalse(x['public_repo_provider_origin_verified'])
        self.assertFalse(x['generic_python_link_installed_owner_verified'])
        self.assertFalse(x['target_elf_loader_and_libraries_verified'])

    def test_alternative_git_lite_and_version_independent(self):
        names = [f'unrelated-{i}.pkg' for i in range(55)] + [f'{p}-3.9_4.pkg' for p in audit.REQUIRED if p != 'git'] + ['git-lite-2.1.pkg']
        self.set_index(names)
        self.assertEqual(self.check()['public_candidates']['git'], [])
        self.assertTrue(self.check()['public_candidates']['git-lite'])

    def test_missing_required_provider_fails(self):
        names = [f'unrelated-{i}.pkg' for i in range(55)] + [f'{p}-1.pkg' for p in audit.REQUIRED if p != 'python313']
        self.set_index(names)
        with self.assertRaisesRegex(ValueError, 'python313'):
            self.check()

    def test_wrong_mirror_and_missing_source_link_fail(self):
        self.html.write_text('fake mirror, no OPNsense identity')
        with self.assertRaisesRegex(ValueError, 'does not identify'):
            self.check()
        self.set_index([f'unrelated-{i}.pkg' for i in range(55)] + [f'{p}-1.pkg' for p in audit.REQUIRED])
        self.plist.write_text('/usr/local/bin/python3.13\n')
        with self.assertRaisesRegex(ValueError, 'generic Python link'):
            self.check()

    def test_missing_native_pkg_query_refused(self):
        self.plugins.write_text('no metadata source')
        with self.assertRaisesRegex(ValueError, 'package manifest generator'):
            self.check()

    def test_file_href_security(self):
        c = audit.PackageHrefParser()
        c.feed('<a href="../python313-1.pkg">bad</a><a href="%2e%2e/foo.pkg">bad</a><a href="https://evil.invalid/a.pkg">bad</a><a href="python313-3.13.20.pkg">good</a><a href="pkgconf-3.0.7%2C1.pkg">encoded</a>')
        self.assertEqual(c.filenames, {'python313-3.13.20.pkg', 'pkgconf-3.0.7,1.pkg'})


if __name__ == '__main__':
    unittest.main()
