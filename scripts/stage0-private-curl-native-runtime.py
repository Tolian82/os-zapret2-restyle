#!/usr/bin/env python3
"""Stage 0: execute EXACT historical private curl ELF in disposable FreeBSD 15.1.

No pkg install, FreeBSD.conf edits, user configuration, external requests or
historical package hooks. Native FreeBSD 15.1 is not installed OPNsense 26.7.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

PACKAGE_SHA256 = '1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f'
ELF_SHA256 = 'e4af7ba05b6ad8dd997aefeae3a9c15a08be2700534d043cd93c7987f97c451f'
ROOT = '/usr/local/libexec/zapret2-restyle/curl-impersonate/'
NEEDED = ('libc++.so.1', 'libc.so.7', 'libcxxrt.so.1',
          'libgcc_s.so.1', 'libm.so.5', 'libthr.so.3')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def get_archive_member(package, member):
    result = subprocess.run(['tar', '-xOf', str(package), member],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=25, check=False)
    if result.returncode:
        raise ValueError('expected private package member missing: ' + member)
    return result.stdout


def confirm_archives(package):
    raw = Path(package).read_bytes()
    if digest(raw) != PACKAGE_SHA256:
        raise ValueError('archived stable package SHA-256 mismatch')
    binary = get_archive_member(package, ROOT + 'bin/curl-impersonate')
    if digest(binary) != ELF_SHA256 or binary[:4] != b'\x7fELF':
        raise ValueError('archived private executable SHA-256 / ELF mismatch')
    profile = get_archive_member(package, ROOT + 'CHROME_PROFILE').decode('ascii').strip()
    if not re.fullmatch(r'chrome[0-9]+', profile):
        raise ValueError('published Chrome profile format invalid')
    return binary, profile


def interpret_ldd(output):
    if re.search(r'(?im)\bnot found\b', output):
        raise ValueError('private ELF dependency was not resolved')
    resolved = {}
    for name in NEEDED:
        match = re.search(r'(?m)^\s*' + re.escape(name) + r'\s*=>\s*(/[^\s(]+)', output)
        if not match:
            raise ValueError('missing required resolved runtime soname: ' + name)
        resolved[name] = match.group(1)
    return resolved


def check_http3_version(output):
    if 'HTTP3' not in output:
        raise ValueError('private ELF did not advertise HTTP3')
    if not re.search(r'(?m)^Protocols:.*\bhttps\b', output, re.IGNORECASE):
        raise ValueError('private ELF did not advertise HTTPS')


def run_native(package, json_file):
    if os.uname().sysname != 'FreeBSD' or os.uname().machine != 'amd64':
        raise ValueError('native runtime evidence requires actual FreeBSD amd64')
    userland = subprocess.run(['freebsd-version', '-u'], capture_output=True,
                              text=True, timeout=10, check=True).stdout.strip()
    if not re.match(r'^15\.1(?:[.-]|$)', userland):
        raise ValueError('qualification VM must be FreeBSD 15.1, observed: ' + userland)

    binary_bytes, profile = confirm_archives(package)
    with tempfile.TemporaryDirectory(prefix='stage0-private-curl-') as scratch:
        target = Path(scratch) / 'curl-impersonate'
        target.write_bytes(binary_bytes)
        target.chmod(0o700)
        ldd = subprocess.run(['ldd', str(target)], text=True, capture_output=True,
                             timeout=15, check=False)
        if ldd.returncode:
            raise ValueError('native FreeBSD loader failed to inspect ELF dependencies')
        libraries = interpret_ldd(ldd.stdout + '\n' + ldd.stderr)
        for lib, location in libraries.items():
            if not Path(location).is_file():
                raise ValueError('missing native library file for ' + lib)

        version = subprocess.run([str(target), '-V'], text=True, capture_output=True,
                                 timeout=15, check=False)
        if version.returncode:
            raise ValueError('exact archived private ELF failed actual -V execution')
        check_http3_version(version.stdout)

        # No listening test endpoint, so exit 7 (connection refused) or 28
        # (timeout) demonstrates parse, loader and loopback attempt, not TLS.
        # The binary sees the real archived Chrome profile and ECH=false.
        cmd = [str(target), '-q', '--impersonate', profile,
               '--noproxy', '*', '--ech', 'false', '--connect-timeout', '1',
               '--max-time', '2', '--silent', '--show-error',
               '--output', os.devnull, 'https://127.0.0.1:1/']
        smoke = subprocess.run(cmd, text=True, capture_output=True,
                               timeout=12, check=False)
        if smoke.returncode not in (7, 28):
            raise ValueError('archived Chrome/ECH-off loopback parse failed, rc='
                             + str(smoke.returncode))
    report = {
        'source': 'immutable-published-0.6.2_1-archive',
        'proof': 'actual-execution-in-disposable-FreeBSD-15.1-amd64-not-OPNsense',
        'freebsd_userland': userland,
        'archive_sha256': PACKAGE_SHA256,
        'private_elf_sha256': ELF_SHA256,
        'private_elf_loader_executed': True,
        'required_sonames_resolved_in_vm': libraries,
        'curl_https_http3_advertised': True,
        'chrome_profile_from_archive': profile,
        'ech_off_cli_loopback_accepted': True,
        'public_tls_chrome_clienthello_verified': False,
        'real_http3_quic_handshake_verified': False,
        'opnsense_target_runtime_and_provider_verified': False,
        'opnsense_signed_repo_catalog_verified': False,
        'owner_appliance_modified': False,
    }
    Path(json_file).write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print('STAGE0_ARCHIVED_PRIVATE_ELF_NATIVE=PASS')
    print('STAGE0_ARCHIVED_PRIVATE_ELF_JSON=' + json.dumps(report, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    try:
        run_native(args.package, args.json)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, 'STAGE0_ARCHIVED_PRIVATE_ELF_NATIVE=FAIL: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
