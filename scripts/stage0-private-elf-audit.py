#!/usr/bin/env python3
"""Read-only, exact-digest, static ELF dependency inventory for historical pkg.

Never executes the private ELF or loads its shared libraries. Its required
sonames/interpreter are hints, NOT qualified target OPNsense provider proofs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

PRIVATE_PATH = '/usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate'


def hash_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def checked(command, **opts):
    completed = subprocess.run(command, check=False, capture_output=True,
                               timeout=45, **opts)
    if completed.returncode:
        raise ValueError('static tool failed: %s: %s' %
                         (command[0], completed.stderr.decode('utf-8', 'replace')[:300]))
    return completed.stdout


def parse_readelf(data):
    lines = data.decode('utf-8', 'replace').splitlines()
    def capture(pattern):
        for line in lines:
            match = re.search(pattern, line)
            if match:
                return match.group(1).strip()
        return None
    needed = sorted(set(re.findall(r'Shared library:\s*\[([^\]]+)\]', '\n'.join(lines))))
    path_values = {}
    for name in ('RPATH', 'RUNPATH'):
        value = capture(r'\(%s\).*Library (?:rpath|runpath):\s*\[([^\]]+)\]' % name)
        if value is not None:
            path_values[name.lower()] = value
    return {
        'elf_class': capture(r'^\s*Class:\s*(ELF\d+)'),
        'data_encoding': capture(r'^\s*Data:\s*(.+)$'),
        'os_abi': capture(r'^\s*OS/ABI:\s*(.+)$'),
        'machine': capture(r'^\s*Machine:\s*(.+)$'),
        'interpreter': capture(r'Requesting program interpreter:\s*([^\]]+)'),
        'needed': needed,
        'dynamic_paths': path_values,
    }


def inspect(package, expected_package_hash, expected_elf_hash, readelf='readelf', tar='tar'):
    package = Path(package).resolve(strict=True)
    if hash_file(package) != expected_package_hash.lower():
        raise ValueError('package digest mismatch')
    binary = checked([tar, '-xOf', str(package), PRIVATE_PATH])
    digest = hashlib.sha256(binary).hexdigest()
    if digest != expected_elf_hash.lower():
        raise ValueError('private ELF digest mismatch')
    if len(binary) < 20 or binary[:4] != b'\x7fELF' or binary[4:6] != bytes([2, 1]):
        raise ValueError('expected ELF64 little-endian binary')
    if int.from_bytes(binary[18:20], 'little') != 62:
        raise ValueError('expected x86_64 ELF machine')
    with tempfile.TemporaryDirectory(prefix='stage0-elf-') as temp:
        target = Path(temp) / 'private-curl.elf'
        target.write_bytes(binary)
        output = checked([readelf, '-W', '-h', '-l', '-d', str(target)])
    parsed = parse_readelf(output)
    if parsed['elf_class'] != 'ELF64' or not parsed['machine'] or 'X86-64' not in parsed['machine']:
        raise ValueError('readelf architecture mismatch')
    return {
        'proof': 'static-elf-from-published-package-not-target-runtime',
        'package_sha256': expected_package_hash.lower(),
        'private_elf_sha256': digest,
        'private_elf_bytes': len(binary),
        **parsed,
        'target_opnsense_library_providers_verified': False,
        'target_opnsense_interpreter_verified': False,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--expected-package-sha256', required=True)
    ap.add_argument('--expected-elf-sha256', required=True)
    ap.add_argument('--readelf', default='readelf')
    ap.add_argument('--tar', default='tar')
    ap.add_argument('--json', type=Path, required=True)
    args = ap.parse_args()
    for value in (args.expected_package_sha256, args.expected_elf_sha256):
        if re.fullmatch('[0-9a-fA-F]{64}', value) is None:
            ap.error('SHA-256 must be exactly 64 hex characters')
    result = inspect(args.package, args.expected_package_sha256,
                     args.expected_elf_sha256, args.readelf, args.tar)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('STAGE0_STATIC_ELF_READ_ONLY=' + json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
