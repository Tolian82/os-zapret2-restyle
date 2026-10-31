#!/usr/bin/env python3
"""Stage 0 public OPNsense 26.7 SOURCE/MIRROR candidate audit only.

Never accesses a host package database, executes a package, or claims real
installed/repository provenance. The HTML mirror listing is NOT signed pkg data.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote

CORE_SHA = 'ac08367416c1d66dea87df0ef0de24c315b5d5bc'
PLUGINS_SHA = '79a5f88b7b27a706c10511ea5587c9d0e0dbdced'
REPO_CONTEXT = '/opnsense/FreeBSD:15:amd64/26.7/latest/All/'
REQUIRED = ('opnsense', 'python313', 'php85', 'pkg', 'git', 'jq', 'luajit', 'pkgconf', 'gmake')


class PackageHrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.filenames = set()

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'a':
            return
        href = unquote(dict(attrs).get('href', ''))
        # Accept only a plain filename, not a malicious path, encoded slash or URL.
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+,-]*\.pkg', href):
            self.filenames.add(href)


def select_candidates(index):
    matched = {}
    for name in REQUIRED + ('git-lite',):
        matches = sorted(x for x in index if re.fullmatch(re.escape(name) + r'-[0-9][A-Za-z0-9._+,-]*\.pkg', x))
        matched[name] = matches
    missing = [name for name in REQUIRED if not matched[name] and
               not (name == 'git' and matched['git-lite'])]
    # A mirror's metadata/entitlement can change independently of installed host.
    return matched, missing


def audit(archive_html, core_plist, defaults, plugins):
    html = Path(archive_html).read_bytes()
    plist = Path(core_plist).read_bytes()
    defaults_text = Path(defaults).read_text(encoding='utf-8')
    plugins_text = Path(plugins).read_text(encoding='utf-8')
    if b'Index of' not in html or b'FreeBSD:15:amd64/26.7/latest/All' not in html:
        raise ValueError('mirror listing does not identify expected public OPNsense path')
    parser = PackageHrefParser()
    parser.feed(html.decode('utf-8', 'replace'))
    if len(parser.filenames) < 50:
        raise ValueError('incomplete or suspicious public package index (<50 files)')
    found, absent = select_candidates(parser.filenames)
    if absent:
        raise ValueError('public mirror missing required candidate names: ' + ', '.join(absent))
    if b'/usr/local/bin/python3\n' not in b'\n' + plist:
        raise ValueError('pinned official core plist lacks generic Python link')
    required_defaults = (
        'VERSIONBIN=', '_PLUGIN_ABI!=', '${VERSIONBIN} -a',
        'PYTHONLINK=', '_PLUGIN_PYTHON!=', '${PYTHONLINK} -V', 'PLUGIN_PYTHON?=',
    )
    for token in required_defaults:
        if token not in defaults_text:
            raise ValueError('official defaults missing ' + token)
    if 'PLUGIN_ABIS?=\t26.7' not in defaults_text:
        raise ValueError('official defaults fallback not accounted for')
    for token in ('PLUGIN_DEPENDS', "${PKG} query", '%n:', 'version: "%v"', 'origin: "%o"'):
        if token not in plugins_text:
            raise ValueError('official package manifest generator missing ' + token)
    return {
        'schema': 1,
        'scope': 'public-source-and-unsigned-mirror-listing-not-actual-opnsense-host',
        'upstream_sources': {'opnsense_core_ref_sha': CORE_SHA,
                             'opnsense_plugins_ref_sha': PLUGINS_SHA},
        'mirror_listing_path_context': REPO_CONTEXT,
        'input_sha256': {'mirror_html': hashlib.sha256(html).hexdigest(),
                         'core_plist': hashlib.sha256(plist).hexdigest(),
                         'defaults_mk': hashlib.sha256(defaults_text.encode()).hexdigest(),
                         'plugins_mk': hashlib.sha256(plugins_text.encode()).hexdigest()},
        'public_filename_count': len(parser.filenames),
        'public_candidates': found,
        'public_repo_provider_origin_verified': False,
        'public_mirror_signed_catalog_verified': False,
        'generic_python_link_in_core_plist': True,
        'generic_python_link_installed_owner_verified': False,
        'opnsense_product_abi_installed_verified': False,
        'plugin_abi_fallback_26_7_is_not_qualification': True,
        'official_native_pkg_dep_origin_resolver': 'pkg query actual installed package',
        'target_elf_loader_and_libraries_verified': False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-html', type=Path, required=True)
    p.add_argument('--core-plist', type=Path, required=True)
    p.add_argument('--defaults-mk', type=Path, required=True)
    p.add_argument('--plugins-mk', type=Path, required=True)
    p.add_argument('--json', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.archive_html, args.core_plist, args.defaults_mk, args.plugins_mk)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print('STAGE0_PUBLIC_OPNSENSE_PROVIDERS=' + json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
