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
    need(m is not None and m.group(1) == '109', 'NATIVE_BOOTSTRAP_REVISION_NOT_109')
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
    # CI-only ephemeral signer: this proves the signed read-only mechanism,
    # NOT deployment of any operator-authenticated production signing key.
    source = HERE / 'native-prepkg-standalone.py'
    trusted_eval = HERE / 'stage3-prepkg-verified-eval.py'
    seed = HERE / 'stage3-prepkg-trust-seed.py'
    need(all(p.is_file() and not p.is_symlink() for p in
             (source, trusted_eval, seed)),
         'PREPKG_TRUSTED_TEST_SOURCES_MISSING')
    source_bytes = source.read_bytes()
    expected_script_sha = hashlib.sha256(source_bytes).hexdigest()
    verifier_bytes = trusted_eval.read_bytes()
    expected_verifier_sha = hashlib.sha256(verifier_bytes).hexdigest()
    trusted_code = seed.read_text()
    need(b'signed_claims(' in verifier_bytes and
         b'exec(executable,' in verifier_bytes and
         'verified_verifier(' in trusted_code and 'exec(compiled,' in trusted_code,
         'TRUST_SEED_OR_VERIFIER_CODE_MISSING')
    with tempfile.TemporaryDirectory(prefix='zapret2-signed-prepkg-ci-',
                                     dir='/root') as standalone_dir:
        private = Path(standalone_dir)
        standalone = private / 'native-prepkg-standalone.py'
        standalone.write_bytes(source_bytes)
        standalone.chmod(0o600)
        verifier = private / 'stage3-prepkg-verified-eval.py'
        verifier.write_bytes(verifier_bytes)
        verifier.chmod(0o600)
        secret = private / 'ci-test-private.pem'
        public = private / 'ci-test-public.pem'
        claims = private / 'signed-claims.json'
        signature = private / 'signed-claims.sig'
        isolated_env = {'PATH':'/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin',
                        'HOME':'/root', 'LANG':'C'}
        def run(argv, timeout=175):
            return subprocess.run(argv, capture_output=True, text=True,
                                  cwd='/root', env=isolated_env, timeout=timeout,
                                  check=False)
        result = run(['/usr/bin/openssl','genpkey','-algorithm','RSA',
                      '-pkeyopt','rsa_keygen_bits:2048','-out',str(secret)], 35)
        need(result.returncode == 0, 'EPHEMERAL_TEST_KEYGEN_FAILED')
        result = run(['/usr/bin/openssl','pkey','-in',str(secret),
                      '-pubout','-out',str(public)],20)
        need(result.returncode == 0,'EPHEMERAL_TEST_PUBKEY_EXPORT_FAILED')
        public.chmod(0o600)
        assertions = {'schema':'zapret2-prepkg-provenance-v1',
                      'repository':'Tolian82/os-zapret2-restyle',
                      'source_commit':built['project_sha'],
                      'entrypoint_sha256':expected_script_sha,
                      'incoming_version':version, 'incoming_sha256':expected,
                      'predecessor_version':old.VERSION,
                      'predecessor_sha256':old.ARCHIVE_SHA}
        def seal():
            claims.write_bytes(json.dumps(assertions,sort_keys=True,
                                          separators=(',',':')).encode())
            claims.chmod(0o600)
            signed = run(['/usr/bin/openssl','dgst','-sha256','-sign',
                          str(secret),'-out',str(signature),str(claims)], 20)
            need(signed.returncode == 0,'EPHEMERAL_TEST_SIGN_FAILED')
            signature.chmod(0o600)
        seal()
        key_pin = hashlib.sha256(public.read_bytes()).hexdigest()
        launcher = [sys.executable,'-I','-B','-c',trusted_code,
                    '--verified-verifier',expected_verifier_sha,str(verifier),
                    '--signed-provenance',key_pin,str(public),str(claims),
                    str(signature),str(standalone)]
        tail = ['inspect-predecessor',str(incoming),version,
                str(old_archive),old.VERSION]
        good = run(launcher + tail)
        need(good.returncode == 0 and
             'ZAPRET2_PREPKG_TRUST_SEED=VERIFIED_SHA256:' +
                expected_verifier_sha in good.stderr and
             'ZAPRET2_PREPKG_VERIFY_EXEC=VERIFIED_SIGNED_SHA256:' +
                expected_script_sha in good.stderr and
             good.stdout.startswith('ZAPRET2_PREPKG_STANDALONE='),
             'SIGNED_EXTERNAL_CLI_CANNOT_SCREEN_OLD:' +
             str(good.returncode)+':'+good.stderr[-300:])
        report=json.loads(good.stdout.split('=',1)[1])
        need(report.get('status')=='PASS_STANDALONE_PREPKG_READ_ONLY_COLD' and
             report.get('incoming_sha256')==expected and
             report.get('old_sha256')==old.ARCHIVE_SHA and
             len(report.get('modules_sha256',{}))==4 and
             report.get('pkg_invoked') is False and
             report.get('old_owner_qualified') is False and
             report.get('supported_mandatory_entrypoint') is False and
             report.get('lh08_ac11_accepted') is False,
             'SIGNED_EXTERNAL_CLI_FALSE_AUTHORIZATION')
        installed_unchanged(old,old_archive,host,baseline)
        for cmd,reason in (
            (launcher[:6]+['0'*64]+launcher[7:]+tail,'BAD_VERIFIER_SHA_PIN'),
            (launcher[:9]+['0'*64]+launcher[10:]+tail,'BAD_PUBLIC_KEY_PIN'),
            (launcher+['upgrade']+tail[1:],'MUTATING_COMMAND'),
            (launcher+tail[:1]+[str(incoming)+'-wrong']+tail[2:],'OTHER_ARCHIVE'),
        ):
            denied=run(cmd,45)
            need(denied.returncode==78 and 'REFUSED:' in denied.stderr and
                 'VERIFIED_SIGNED_SHA256:' not in denied.stderr,
                 'SIGNATURE_NEGATIVE_NOT_REFUSED:'+reason)
            installed_unchanged(old,old_archive,host,baseline)
        actual_signature=signature.read_bytes()
        signature.write_bytes(b'forged-signature')
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and
             'SIGNED_PROVENANCE_SIGNATURE_INVALID' in denied.stderr,
             'FORGED_SIGNATURE_ACCEPTED')
        signature.write_bytes(actual_signature)
        claims.write_bytes(claims.read_bytes().replace(expected.encode(),b'0'*64))
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and
             'SIGNED_PROVENANCE_SIGNATURE_INVALID' in denied.stderr,
             'UNSIGNED_CLAIMS_CHANGE_ACCEPTED')
        assertions['incoming_sha256']='0'*64
        seal()
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and 'REFUSED:' in denied.stderr,
             'SIGNED_WRONG_ARCHIVE_ACCEPTED')
        assertions['incoming_sha256']=expected
        seal()
        # Before the signed verifier may execute: wrong pinned SHA, changed
        # executable verifier canary, symlink, or writable file must refuse.
        verifier_canary = private / 'UNTRUSTED_VERIFIER_EXECUTED'
        verifier.write_bytes(b'from pathlib import Path\nPath(' +
                repr(str(verifier_canary)).encode() +
                b').write_text("BAD")\n' + verifier_bytes)
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and
             'VERIFIER_EXPECTED_SHA256_MISMATCH' in denied.stderr and
             'ZAPRET2_PREPKG_VERIFY_EXEC=VERIFIED_SIGNED_SHA256:' not in denied.stderr and
             not verifier_canary.exists(), 'UNVERIFIED_VERIFIER_SOURCE_EXECUTED')
        verifier.write_bytes(verifier_bytes)
        verifier.chmod(0o666)
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and
             'VERIFIER_PRIVATE_REGULAR_REQUIRED' in denied.stderr,
             'WORLD_WRITABLE_VERIFIER_ACCEPTED')
        verifier.chmod(0o600)
        verifier_link_dir = private/'verifier-symlink'
        verifier_link_dir.mkdir(mode=0o700)
        verifier_link = verifier_link_dir/'stage3-prepkg-verified-eval.py'
        verifier_link.symlink_to(verifier)
        denied=run(launcher[:7]+[str(verifier_link)]+launcher[8:]+tail,45)
        need(denied.returncode==78 and 'VERIFIER_OPEN_REFUSED' in denied.stderr,
             'SYMLINK_VERIFIER_ACCEPTED')
        installed_unchanged(old,old_archive,host,baseline)
        canary=private/'UNTRUSTED_SOURCE_EXECUTED'
        standalone.write_bytes(b'from pathlib import Path\nPath('+
                repr(str(canary)).encode()+b').write_text("BAD")\n'+source_bytes)
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and
             'EXTERNAL_SOURCE_EXPECTED_SHA256_MISMATCH' in denied.stderr and
             not canary.exists(),'TAMPERED_EXTERNAL_SOURCE_EXECUTED')
        standalone.write_bytes(source_bytes)
        standalone.chmod(0o666)
        denied=run(launcher+tail,45)
        need(denied.returncode==78 and
             'EXTERNAL_SOURCE_REGULAR_PRIVATE_ROOT_FILE_REQUIRED' in denied.stderr,
             'WORLD_WRITABLE_EXTERNAL_SOURCE_ACCEPTED')
        standalone.chmod(0o600)
        installed_unchanged(old,old_archive,host,baseline)
    installed_unchanged(old, old_archive, host, baseline)
    need(guard.snapshot(old_archive)['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'OLD_COLD_STATE_NOT_RETAINED')
    return {'status': 'PASS_ONE_USE_NATIVE_ARCHIVED_SOURCE_PREPKG_READONLY',
            'incoming_version': version, 'incoming_archive_sha256': expected,
            'predecessor_archive_sha256': old.ARCHIVE_SHA,
            'exact_native_product_modules_extracted': len(MODULES),
            'source_bytes_equal_verified_incoming_package': True,
            'standalone_no_checkout_pre_pkg_screened': True,
            'external_sha_verified_before_source_exec': True,
            'verifier_sha_verified_before_verifier_exec': True,
            'seed_code_from_ci_exact_head_only': True,
            'operator_trust_seed_authenticated': False,
             'ci_ephemeral_signed_provenance_verified': True,
             'operator_signer_authenticated': False,
            'trusted_eval_code_from_ci_exact_head_only': True,
            'trusted_production_distribution_implemented': False,
            'standalone_diagnostic_root_copy_only': True,
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
