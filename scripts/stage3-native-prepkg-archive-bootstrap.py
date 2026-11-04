#!/usr/bin/env python3
"""One-use disposable OPNsense pre-pkg *read-only* archive bootstrap proof.

Extracts the already packaged current managed CLI/modules from an exactly
SHA-qualified incoming official native Mk archive BEFORE any replacement of
an authentic old 0.6.2_1 installation. This is NOT a deployable updater or
firmware/Web gateway; no pkg add/upgrade/remove after the old install occurs.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PRODUCT = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(PRODUCT))
import native_pkg_candidate as candidate

OPTIN = 'ZAPRET2_STAGE3_PREPKG_ARCHIVE_BOOTSTRAP'
MODULES = ('native_pkg_managed.py', 'native_pkg_handoff.py',
           'native_pkg_candidate.py', 'native_pkg_old_owner.py')
DEST = 'usr/local/opnsense/scripts/OPNsense/Zapret/backend/'
NAME = 'os-zapret2-restyle'
PREFIX = 'STAGE3_PREPKG_ARCHIVE_BOOTSTRAP='


class Refusal(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Refusal(why)


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def qualify():
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64' and os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get(OPTIN) == '1' and
         os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK') == '1' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1',
         'ONE_USE_NATIVE_KVM_BOOTSTRAP_OPTIN_REQUIRED')


def read_only(argv, timeout=30):
    try:
        p = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('ARCHIVE_READ_ONLY_TOOL_UNAVAILABLE:' + str(argv[0])) from None
    need(p.returncode == 0,
         'ARCHIVE_READ_ONLY_QUERY_REFUSED:' + str(argv[0]) + ':' + str(p.returncode))
    return p.stdout


def archive_members(path):
    entries = read_only(['/usr/bin/tar', '-tf', str(path)]).decode('utf-8').splitlines()
    need(entries, 'NATIVE_ARCHIVE_MEMBER_LIST_EMPTY')
    mapping = {}
    for name in MODULES:
        expected = DEST + name
        # Actual official OPNsense Mk pkg tar -tf uses /usr/local/...,
        # while other native tar variants may use repeated leading './'.
        # Accept *only* the exact expected absolute name or qualified relative
        # name; tar -xOf only reads bytes and never extracts to this path.
        # Refuse double-slash/parent-traversal aliases.
        exact = [e for e in entries if
                 '..' not in Path(e).parts and
                 (e == '/' + expected or
                  (not e.startswith('/') and e.lstrip('./') == expected))]
        need(len(exact) == 1, 'NATIVE_ARCHIVE_SOURCE_MEMBER_MISSING_OR_DUPLICATED:' +
             name + ':matching_count=' + str(len(exact)) +
             ':suffix_count=' + str(sum(e.endswith('/' + name) for e in entries)) +
             ':suffix_example=' + repr([e for e in entries if e.endswith('/' + name)][:1]))
        mapping[name] = exact[0]
    return mapping


def staged_source_from_native_archive(native_archive, version, expected_sha, directory):
    """Stage byte-equal trusted native product members; NEVER install the .pkg.

    The SHA is a trusted caller expectation, not a value copied from the
    potentially hostile package. This CI fixture alone is not a product
    entrypoint or a replacement for independent SHA provenance.
    """
    qualify()
    candidate.identity(native_archive, version, expected_sha)
    candidate.inspect_archive(native_archive, version, expected_sha)
    root = Path(directory)
    st = root.lstat()
    need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
         stat.S_IMODE(st.st_mode) == 0o700 and
         not root.is_symlink(), 'NATIVE_BOOTSTRAP_PRIVATE_DIRECTORY_UNTRUSTED')
    raw = read_only(['/usr/bin/tar', '-xOf', str(native_archive), '+MANIFEST'])
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError, TypeError):
        raise Refusal('NATIVE_BOOTSTRAP_ARCHIVE_MANIFEST_INVALID') from None
    need(isinstance(manifest, dict) and manifest.get('name') == NAME and
         manifest.get('version') == version and
         manifest.get('abi') == 'FreeBSD:15:amd64' and
         manifest.get('arch') == 'freebsd:15:x86:64',
         'NATIVE_BOOTSTRAP_ARCHIVE_IDENTITY_UNQUALIFIED')
    files = manifest.get('files')
    need(isinstance(files, dict), 'NATIVE_BOOTSTRAP_ARCHIVE_FILES_INVALID')
    members = archive_members(native_archive)
    expected = {}
    for name in MODULES:
        rel = DEST + name
        need('/' + rel in files,
             'NATIVE_BOOTSTRAP_SOURCE_ABSENT_FROM_MANIFEST:' + name)
        observed = read_only(['/usr/bin/tar', '-xOf', str(native_archive), members[name]])
        tracked = PRODUCT / name
        need(tracked.is_file() and not tracked.is_symlink() and
             0 < len(observed) < 512 * 1024 and
             hashlib.sha256(observed).digest() ==
             hashlib.sha256(tracked.read_bytes()).digest(),
             'NATIVE_BOOTSTRAP_TRACKED_SOURCE_BYTES_DIFFER:' + name)
        expected[name] = observed

    # A root-owned directory is constructed by the throwaway CI harness.
    # No hardlinks/symlinks and no unqualified writes to installed paths.
    for name, data in expected.items():
        target = root / name
        need(not target.exists() and not target.is_symlink(),
             'NATIVE_BOOTSTRAP_OUTPUT_ALREADY_EXISTS:' + name)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            n = 0
            while n < len(data):
                written = os.write(fd, data[n:])
                need(written > 0, 'NATIVE_BOOTSTRAP_WRITE_FAILED')
                n += written
            os.fsync(fd)
        finally:
            os.close(fd)
        info = target.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and
             info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600 and
             target.read_bytes() == data,
             'NATIVE_BOOTSTRAP_STAGED_BYTES_OR_OWNER_CHANGED:' + name)
    candidate.inspect_archive(native_archive, version, expected_sha)
    return root / 'native_pkg_managed.py'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def installed_unchanged(old, archive, hostname, before):
    after = (old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME),
             digest(old.SERVICE), digest('/conf/config.xml'))
    need(after == before and
         old.run_guest(archive, hostname)['status'] == 'PASS_READ_ONLY_PROVENANCE',
         'OLD_NATIVE_PKGDB_SERVICE_CONFIG_OR_HOOKS_CHANGED')


def execute(old_archive):
    qualify()
    guest = load('stage0-opnsense-guest-readonly.py', 'bootstrap_guest')
    guest.evaluate(guest.observe())
    old = load('stage0-installed-predecessor-readonly.py', 'bootstrap_old')
    installer = load('stage0-opnsense-installed-predecessor.py', 'bootstrap_installer')
    guard = load('stage0-opnsense-prepkg-readonly.py', 'bootstrap_guard')
    native = load('native-opnsense-package.py', 'bootstrap_native_builder')
    native.gate()
    built = native.build()
    need(built['status'] == 'PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY' and
         built['project_sha'] == os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA') and
         built['publication_approved'] is False,
         'NATIVE_BOOTSTRAP_OFFICIAL_MK_SOURCE_UNQUALIFIED')
    incoming = ROOT / built['output']
    expected = built['real_native_pkg']['sha256']
    revision = (ROOT / 'Makefile').read_text()
    m = re.search(r'(?m)^PLUGIN_REVISION=\s*([0-9]+)\s*$', revision)
    need(m is not None and m.group(1) == '105', 'NATIVE_BOOTSTRAP_REVISION_NOT_105')
    version = (ROOT / 'VERSION').read_text().strip() + '_' + m.group(1)
    need(installer.install_and_verify(old_archive)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'GENUINE_OLD_PACKAGE_NOT_INSTALLED')
    need(guard.snapshot(old_archive)['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'OLD_PREDECESSOR_NOT_COLD')
    host = old.run('hostname', '-s').decode().strip()
    baseline = (old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME),
                digest(old.SERVICE), digest('/conf/config.xml'))
    with tempfile.TemporaryDirectory(prefix='zapret2-native-archive-prepkg-', dir='/root') as temp:
        root = Path(temp)
        cli = staged_source_from_native_archive(incoming, version, expected, root)
        cmd = [sys.executable, '-B', str(cli), 'inspect-predecessor',
               str(old_archive), old.VERSION, old.ARCHIVE_SHA]
        response = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=135, check=False)
        need(response.returncode == 0 and
             response.stdout.startswith('ZAPRET2_MANAGED='),
             'ARCHIVED_NATIVE_MANAGED_PREDECESSOR_REFUSED:' +
             str(response.returncode) + ':' + response.stderr[-200:])
        try:
            value = json.loads(response.stdout.split('=', 1)[1])
        except (ValueError, UnicodeError):
            raise Refusal('ARCHIVED_NATIVE_MANAGED_RESULT_INVALID') from None
        need(value.get('status') == 'PASS_MANAGED_READ_ONLY_PREDECESSOR_SCREEN' and
             value.get('predecessor_cold_screened') is True and
             value.get('pkg_invoked') is False and
             value.get('old_owner_qualified') is False and
             value.get('lh08_ac11_accepted') is False,
             'ARCHIVED_NATIVE_MANAGED_OLD_OWNER_FALSE_AUTHORIZATION')
        incorrect = subprocess.run(cmd[:-1] + ['0' * 64], capture_output=True,
                                   text=True, timeout=30, check=False)
        need(incorrect.returncode == 78 and
             'ZAPRET2_MANAGED=REFUSED:' in incorrect.stderr,
             'ARCHIVED_NATIVE_MANAGED_WRONG_SHA_NOT_REFUSED')
        upgrade = subprocess.run([sys.executable, '-B', str(cli), 'upgrade',
                                  str(incoming), version, expected],
                                 capture_output=True, text=True, timeout=20, check=False)
        need(upgrade.returncode == 78 and
             'UPGRADE_NOT_IMPLEMENTED_NO_PKG' in upgrade.stderr,
             'ARCHIVED_NATIVE_MANAGED_UNSAFE_UPGRADE_NOT_REFUSED')
        # Wrong incoming SHA fails *before* staging any bytes in second directory.
        empty = root / 'wrong_sha'
        empty.mkdir(mode=0o700)
        try:
            staged_source_from_native_archive(incoming, version, '0' * 64, empty)
        except candidate.CandidateRefusal:
            pass
        else:
            raise Refusal('NATIVE_BOOTSTRAP_WRONG_INCOMING_SHA_ACCEPTED')
        need(not list(empty.iterdir()), 'REFUSED_NATIVE_BOOTSTRAP_WROTE_FILES')
        installed_unchanged(old, old_archive, host, baseline)
    installed_unchanged(old, old_archive, host, baseline)
    need(guard.snapshot(old_archive)['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'OLD_COLD_STATE_NOT_RETAINED')
    return {'status': 'PASS_ONE_USE_NATIVE_ARCHIVED_SOURCE_PREPKG_READONLY',
            'incoming_version': version, 'incoming_archive_sha256': expected,
            'predecessor_archive_sha256': old.ARCHIVE_SHA,
            'exact_native_product_modules_extracted': len(MODULES),
            'source_bytes_equal_verified_incoming_package': True,
            'genuine_old_installed_package_unchanged': True,
            'native_pkg_mutation_after_old_install': False,
            'old_owner_qualified': False,
            'supported_entrypoint_implemented': False,
            'firmware_web_root_pkg_protected': False,
            'lh08_ac11_accepted': False}


def main():
    if len(sys.argv) != 2:
        print(PREFIX + 'REFUSED:ORIGINAL_ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        answer = execute(Path(sys.argv[1]))
    except (Refusal, candidate.CandidateRefusal, OSError, ValueError, KeyError,
            TypeError, subprocess.SubprocessError) as exc:
        print(PREFIX + 'REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print(PREFIX + json.dumps(answer, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
