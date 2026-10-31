#!/usr/bin/env python3
"""Read-only Stage 0 inspection of a published FreeBSD pkg archive.

Archive contents are read via host tar without extraction or installed pkg mutation.
Expected release digest/name/version are independent CLI evidence inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HOOKS = ('pre-install', 'post-install', 'pre-deinstall', 'post-deinstall')
WATCH = (
    'usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh',
    'usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh',
    'usr/local/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh',
    'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_python_launcher.sh',
    'usr/local/etc/rc.syshook.d/start/20-zapret',
    'usr/local/etc/rc.syshook.d/stop/20-zapret',
    'usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate',
    'usr/local/libexec/zapret2-restyle/run-curl-impersonate.sh',
)

def shell(*args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f'archive inspection failed: {args[:2]}: {result.stderr.decode("utf-8", "replace")[:400]}')
    return result.stdout

def digest(data):
    return hashlib.sha256(data).hexdigest()

def archive_member(path):
    return path.lstrip('./')

def scan(package, tarbin, expected_name, expected_version, expected_sha):
    package = package.resolve(strict=True)
    sha = hashlib.sha256()
    with package.open('rb') as fd:
        for chunk in iter(lambda: fd.read(1024 * 1024), b''):
            sha.update(chunk)
    actual = sha.hexdigest()
    if actual != expected_sha.lower():
        raise ValueError(f'wrong package SHA256: actual {actual}, expected {expected_sha}')
    names = shell(tarbin, '-tf', str(package)).decode('utf-8', 'replace').splitlines()
    verbose = shell(tarbin, '-tvf', str(package)).decode('utf-8', 'replace').splitlines()
    if len(names) != len(verbose) or not names:
        raise ValueError('tar member/mode listing mismatch or empty package')
    if len(names) != len(set(names)):
        raise ValueError('duplicate archive member')
    attrs = {}
    for raw, long in zip(names, verbose):
        mode = long.split(maxsplit=1)[0]
        if not re.fullmatch(r'[dlbcps-][rwxSsTt-]{9}[+@.]?', mode):
            raise ValueError(f'unrecognized tar mode for {raw}: {mode}')
        name = archive_member(raw)
        attrs[name] = {'archive_member': raw, 'mode': mode, 'type': mode[0]}
    manifest_name = next((x for x in names if archive_member(x) == '+MANIFEST'), None)
    if manifest_name is None:
        raise ValueError('missing +MANIFEST')
    meta = json.loads(shell(tarbin, '-xOf', str(package), manifest_name))
    if meta.get('name') != expected_name or meta.get('version') != expected_version:
        raise ValueError(f'package identity mismatch: {meta.get("name")} {meta.get("version")}')
    scripts = meta.get('scripts')
    if not isinstance(scripts, dict) or any(not isinstance(scripts.get(key), str) or not scripts[key] for key in HOOKS):
        raise ValueError('missing/nontext pkg lifecycle hooks')
    hooks = {key: {'sha256': digest(scripts[key].encode('utf-8')), 'bytes': len(scripts[key].encode('utf-8'))} for key in HOOKS}
    observed = {}
    for path in WATCH:
        observed[path] = attrs.get(path)
    elf_path = WATCH[6]
    elf = {}
    if elf_path in attrs:
        blob = shell(tarbin, '-xOf', str(package), attrs[elf_path]['archive_member'])
        elf = {'sha256': digest(blob), 'bytes': len(blob), 'elf_magic': blob[:4].hex(),
               'elf_class': blob[4] if len(blob) >= 5 else None,
               'machine': int.from_bytes(blob[18:20], 'little') if len(blob) >= 20 else None}
    return {'schema': 1, 'input': str(package), 'sha256': actual, 'name': meta['name'], 'version': meta['version'],
            'origin': meta.get('origin'), 'abi': meta.get('abi'), 'arch': meta.get('arch'),
            'dependencies': meta.get('deps'), 'archive_entries': len(names),
            'symlinks': [key for key, item in attrs.items() if item['type'] == 'l'],
            'hooks': hooks, 'watch': observed, 'private_elf': elf,
            'members': [{'name': name, **data} for name, data in sorted(attrs.items())]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--tar', default='tar')
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-name', default='os-zapret2-restyle')
    parser.add_argument('--expected-version', required=True)
    parser.add_argument('--json', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-fA-F]{64}', args.expected_sha256):
        parser.error('expected SHA256 must be 64 hex digits')
    result = scan(args.package, args.tar, args.expected_name, args.expected_version, args.expected_sha256)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    print('STAGE0_OLD_PKG_READ_ONLY=' + json.dumps({key: result[key] for key in ('name', 'version', 'sha256', 'abi', 'arch', 'archive_entries', 'hooks', 'watch', 'private_elf')}, sort_keys=True))

if __name__ == '__main__':
    main()
