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
import pty
import shutil
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time

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
    need(m is not None and m.group(1) == '114', 'NATIVE_BOOTSTRAP_REVISION_NOT_114')
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
        # Test-only expectation from the exact-head checkout; operator must
        # authenticate the expected commit separately for any real deployment.
        expected_commit = built['project_sha']
        # A disposable FreeBSD pseudo-TTY exercises *only* the human-approval
        # record mechanics. These CI-supplied digest lines are synthetic and
        # MUST NEVER be reported as real operator/publisher attestation.
        approval_tool = HERE / 'stage3-prepkg-operator-approval.py'
        need(approval_tool.is_file() and not approval_tool.is_symlink(),
             'OPERATOR_APPROVAL_TEST_TOOL_MISSING')
        reviewed = private / 'ci-operator-reviewed'
        reviewed.mkdir(mode=0o700)
        sources = (
            (seed, reviewed / 'stage3-prepkg-trust-seed.py'),
            (trusted_eval, reviewed / 'stage3-prepkg-verified-eval.py'),
            (public, reviewed / 'approved-public.pem'),
            (incoming, reviewed / (NAME + '-' + version + '.pkg')),
            (old_archive, reviewed / (NAME + '-' + old.VERSION + '.pkg')),
        )
        for source_path, target in sources:
            shutil.copyfile(source_path, target)
            target.chmod(0o600)
        pin_values = [hashlib.sha256(Path(src).read_bytes()).hexdigest()
                      for src in (seed, trusted_eval, public)]
        pin_values += [expected_commit, version, expected,
                       old.VERSION, old.ARCHIVE_SHA]
        confirm = 'APPROVE ' + expected_commit + ' ' + version
        receipt = reviewed / 'operator-pins.json'
        manual = [sys.executable, '-I', '-B', str(approval_tool),
                  'record', str(receipt)]
        master_fd, slave_fd = pty.openpty()
        try:
            proc = subprocess.Popen(manual, stdin=slave_fd, stdout=slave_fd,
                                    stderr=subprocess.PIPE, close_fds=True,
                                    cwd='/root', env=isolated_env)
            os.close(slave_fd)
            slave_fd = -1
            os.write(master_fd, ('\n'.join(pin_values + [confirm]) + '\n').encode())
            _, manual_err = proc.communicate(timeout=40)
            need(proc.returncode == 0 and receipt.exists(),
                 'CI_PTY_MANUAL_PINS_REFUSED:' + manual_err.decode()[-240:])
        finally:
            os.close(master_fd)
            if slave_fd >= 0:
                os.close(slave_fd)
        inspected = run([sys.executable, '-I', '-B', str(approval_tool),
                         'inspect', str(receipt), *(str(x[1]) for x in sources)],
                        80)
        need(inspected.returncode == 0 and
             inspected.stdout.startswith('ZAPRET2_OPERATOR_APPROVAL='),
             'CI_OPERATOR_PIN_READONLY_INSPECT_REFUSED:' + inspected.stderr[-220:])
        approved = json.loads(inspected.stdout.split('=', 1)[1])
        need(approved['status'] == 'PASS_RECORDED_PINS_AND_PRIVATE_BYTES_ONLY' and
             approved['source_commit'] == expected_commit and
             all(approved[x] is False for x in (
                 'operator_source_authenticated', 'signer_authenticated',
                 'signed_manifest_verified', 'pkg_authorized', 'pkg_invoked',
                 'old_owner_qualified', 'supported_entrypoint_implemented',
                 'lh08_ac11_accepted')),
             'CI_PINS_WRONGLY_CLAIM_PRODUCTION_AUTHORITY')
        denied = run([sys.executable, '-I', '-B', str(approval_tool),
                      'record', str(reviewed / 'second-approval' /
                                    'operator-pins.json')], 20)
        need(denied.returncode == 78 and
             'REAL_INTERACTIVE_OPERATOR_TTY_REQUIRED' in denied.stderr,
             'NONINTERACTIVE_OPERATOR_APPROVAL_ACCEPTED')
        receipt.chmod(0o644)
        denied = run([sys.executable, '-I', '-B', str(approval_tool),
                      'inspect', str(receipt),
                      *(str(x[1]) for x in sources)], 20)
        need(denied.returncode == 78 and
             'OPERATOR_PRIVATE_SOURCE_MODE_OR_SIZE_REFUSED' in denied.stderr,
             'WORLD_READABLE_OPERATOR_PINS_ACCEPTED')
        receipt.chmod(0o600)
        key_copy = reviewed / 'approved-public.pem'
        key_bytes = key_copy.read_bytes()
        key_copy.write_bytes(b'MALICIOUS_KEY\n' + key_bytes)
        denied = run([sys.executable, '-I', '-B', str(approval_tool),
                      'inspect', str(receipt),
                      *(str(x[1]) for x in sources)], 20)
        need(denied.returncode == 78 and
             'OPERATOR_PIN_SHA256_MISMATCH:public_key_sha256' in denied.stderr,
             'TAMPERED_OPERATOR_PUBLIC_KEY_ACCEPTED')
        key_copy.write_bytes(key_bytes)
        # This is a DIFFERENT ephemeral RSA identity from the signed pkg
        # provenance key, generated solely on a one-use OPNsense CI VM. A
        # real operator must authenticate its fingerprint out of band.
        approval_private = reviewed / 'ci-only-operator-authority-private.pem'
        approval_public = reviewed / 'operator-approval-authority.pem'
        approval_sig = reviewed / 'operator-pins.sig'
        keygen = run(['/usr/bin/openssl','genpkey','-algorithm','RSA',
                      '-pkeyopt','rsa_keygen_bits:2048',
                      '-out',str(approval_private)], 35)
        need(keygen.returncode == 0, 'CI_OPERATOR_AUTHORITY_KEYGEN_FAILED')
        exported = run(['/usr/bin/openssl','pkey','-in',str(approval_private),
                        '-pubout','-out',str(approval_public)], 20)
        need(exported.returncode == 0, 'CI_OPERATOR_AUTHORITY_EXPORT_FAILED')
        approval_public.chmod(0o600)
        approval_private.chmod(0o600)
        authority_sha = hashlib.sha256(approval_public.read_bytes()).hexdigest()
        need(authority_sha != key_pin,
             'CI_OPERATOR_AUTHORITY_MUST_DIFFER_FROM_CLAIMS_SIGNER')
        def seal_receipt():
            signed = run(['/usr/bin/openssl','dgst','-sha256','-sign',
                          str(approval_private),'-out',str(approval_sig),
                          str(receipt)], 20)
            need(signed.returncode == 0, 'CI_OPERATOR_RECEIPT_SIGNING_FAILED')
            approval_sig.chmod(0o600)
        seal_receipt()
        # Separate, byte-exact SHA-pinned and RSA-signed CI-only approval
        # policy snapshot. This is NOT a monotonic one-use token database.
        policy_path = reviewed / 'operator-approval-policy.json'
        policy_sig = reviewed / 'operator-approval-policy.sig'
        policy_now = int(time.time())
        policy_fields = {
            'schema': 'zapret2-prepkg-approval-policy-v1',
            'repository': 'Tolian82/os-zapret2-restyle',
            'authority_sha256': authority_sha,
            'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
            'sequence': 1, 'issued_at': policy_now-5,
            'not_before': policy_now-5, 'not_after': policy_now+1800,
            'revoked_receipt_sha256': [],
            'revoked_authority_sha256': [],
        }
        def seal_policy():
            policy_fields['receipt_sha256'] = hashlib.sha256(
                receipt.read_bytes()).hexdigest()
            raw = (json.dumps(policy_fields,sort_keys=True,
                              separators=(',',':'))+'\n').encode()
            policy_path.write_bytes(raw)
            policy_path.chmod(0o600)
            approved = run(['/usr/bin/openssl','dgst','-sha256','-sign',
                            str(approval_private),'-out',str(policy_sig),
                            str(policy_path)], 20)
            need(approved.returncode == 0,
                 'CI_APPROVAL_POLICY_RSA_SIGNING_FAILED')
            policy_sig.chmod(0o600)
            return hashlib.sha256(raw).hexdigest()
        policy_sha = seal_policy()
        # The readonly seed receives ONLY paths; all digest/commit expectations
        # originate from the private manual receipt, never caller argv.
        launcher = [sys.executable,'-I','-B','-c',trusted_code,
                    '--operator-receipt',str(receipt),
                    '--operator-authority',authority_sha,str(approval_public),
                    str(approval_sig),
                    '--approval-policy',policy_sha,str(policy_path),str(policy_sig),
                    '--verified-verifier',str(verifier),
                    '--signed-provenance',str(key_copy),str(claims),
                    str(signature),str(standalone)]
        tail = ['inspect-predecessor',str(incoming),version,
                str(old_archive),old.VERSION]
        good = run(launcher + tail)
        need(good.returncode == 0 and
             'ZAPRET2_PREPKG_TRUST_SEED=RECEIPT_RSA_VERIFIED_ANCHOR_NOT_OWNER_AUTHENTICATED'
                 in good.stderr and
             'ZAPRET2_PREPKG_TRUST_SEED=SIGNED_POLICY_TIME_AND_REVOCATION_MATCHED_NOT_ONE_USE'
                 in good.stderr and
             'ZAPRET2_PREPKG_TRUST_SEED=RECEIPT_PINS_BOUND_NOT_AUTHENTICATED'
                 in good.stderr and
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
        original_receipt = receipt.read_bytes()
        for field, bad, reason in (
            ('verifier_sha256', '0'*64, 'VERIFIER_SHA'),
            ('public_key_sha256', '0'*64, 'PUBLIC_KEY_SHA'),
            ('source_commit', 'f'*40, 'SOURCE_COMMIT'),
            ('source_commit', 'bad-commit', 'MALFORMED_COMMIT'),
            ('incoming_sha256', '0'*64, 'MALFORMED_INCOMING_SHA'),
            ('predecessor_sha256', '0'*64, 'MALFORMED_OLD_SHA'),
            ('incoming_sha256', 'c'*64, 'VALID_BUT_UNAPPROVED_INCOMING_SHA'),
            ('predecessor_sha256', 'c'*64, 'VALID_BUT_UNAPPROVED_OLD_SHA'),
        ):
            changed = json.loads(original_receipt)
            changed[field] = bad
            receipt.write_bytes(json.dumps(changed,sort_keys=True,
                                           separators=(',',':')).encode())
            # Both the receipt signature AND the provenance signature are
            # cryptographically valid in these negative cases.
            seal_receipt()
            # The CI policy issuer *also* reauthorizes this changed receipt
            # and updates the expected policy SHA. The final mismatch must
            # still be caught by independent signed provenance/archives.
            launcher[12] = seal_policy()
            denied = run(launcher+tail,45)
            need(denied.returncode == 78 and 'REFUSED:' in denied.stderr and
                 'VERIFIED_SIGNED_SHA256:' not in denied.stderr and
                 (reason not in ('VALID_BUT_UNAPPROVED_INCOMING_SHA',
                                 'VALID_BUT_UNAPPROVED_OLD_SHA') or
                  'SIGNED_PROVENANCE_ARCHIVES_NOT_IN_OPERATOR_RECEIPT'
                  in denied.stderr),
                 'RECEIPT_NEGATIVE_NOT_REFUSED:' + reason)
            receipt.write_bytes(original_receipt)
            seal_receipt()
            launcher[12] = seal_policy()
            installed_unchanged(old,old_archive,host,baseline)
        # Both signatures still validate for a policy which is *itself*
        # explicitly expired, premature, revoked or outside the allowed
        # duration. The original historical old package must never change.
        original_policy = dict(policy_fields)
        for name, change, expected_refusal in (
            ('expired', {'not_after': policy_now-1},
             'APPROVAL_POLICY_NOT_CURRENT'),
            ('future', {'not_before':policy_now+100,
                        'issued_at':policy_now+100},
             'APPROVAL_POLICY_NOT_CURRENT'),
            ('too_long', {'not_after': policy_now+86400},
             'APPROVAL_POLICY_UNBOUNDED_OR_INVALID_WINDOW'),
            ('revoked_receipt', {
                 'revoked_receipt_sha256':[
                     hashlib.sha256(receipt.read_bytes()).hexdigest()]},
             'OPERATOR_RECEIPT_REVOKED_IN_POLICY'),
            ('revoked_authority', {
                 'revoked_authority_sha256':[authority_sha]},
             'OPERATOR_APPROVAL_AUTHORITY_REVOKED_IN_POLICY'),
            ('wrong_authority', {'authority_sha256':'b'*64},
             'APPROVAL_POLICY_WRONG_IDENTITY_OR_RECEIPT'),
            ('boolean_sequence', {'sequence': True},
             'APPROVAL_POLICY_NONINTEGER:sequence'),
        ):
            policy_fields.update(change)
            launcher[12] = seal_policy()
            denied = run(launcher+tail,45)
            need(denied.returncode == 78 and
                 expected_refusal in denied.stderr and
                 'VERIFIED_SHA256:' not in denied.stderr,
                 'SIGNED_APPROVAL_POLICY_NEGATIVE_ACCEPTED:' + name)
            policy_fields.clear()
            policy_fields.update(original_policy)
            launcher[12] = seal_policy()
            installed_unchanged(old,old_archive,host,baseline)
        # A modified snapshot must reject even before its signature is
        # checked when its separately expected exact digest no longer agrees.
        original_policy_bytes=policy_path.read_bytes()
        original_policy_sig=policy_sig.read_bytes()
        policy_path.write_bytes(original_policy_bytes+b'ATTACKER')
        denied=run(launcher+tail,45)
        need(denied.returncode == 78 and
             'APPROVAL_POLICY_NOT_INDEPENDENTLY_PINNED' in denied.stderr,
             'MODIFIED_APPROVAL_POLICY_ACCEPTED')
        # If a caller swaps the expected SHA but not the signature,
        # the real detached RSA operation must independently reject it.
        launcher[12]=hashlib.sha256(policy_path.read_bytes()).hexdigest()
        denied=run(launcher+tail,45)
        need(denied.returncode == 78 and
             'OPERATOR_RECEIPT_SIGNATURE_INVALID' in denied.stderr and
             'VERIFIED_SHA256:' not in denied.stderr,
             'FORGED_APPROVAL_POLICY_SIGNATURE_ACCEPTED')
        policy_path.write_bytes(original_policy_bytes)
        policy_sig.write_bytes(original_policy_sig)
        launcher[12]=seal_policy()
        # Tampering after approval must fail before loading external verifier.
        receipt.write_bytes(original_receipt+b'\nATTACKER')
        denied=run(launcher+tail,45)
        need(denied.returncode == 78 and
             'OPERATOR_RECEIPT_SIGNATURE_INVALID' in denied.stderr and
             'VERIFIED_SHA256:' not in denied.stderr,
             'UNSIGNED_CHANGED_OPERATOR_RECEIPT_ACCEPTED')
        receipt.write_bytes(original_receipt)
        seal_receipt()
        original_authority_sig=approval_sig.read_bytes()
        approval_sig.write_bytes(b'forged-receipt-signature')
        denied=run(launcher+tail,45)
        need(denied.returncode == 78 and
             'OPERATOR_RECEIPT_SIGNATURE_INVALID' in denied.stderr and
             'VERIFIED_SHA256:' not in denied.stderr,
             'FORGED_OPERATOR_RECEIPT_SIGNATURE_ACCEPTED')
        approval_sig.write_bytes(original_authority_sig)
        original_public=approval_public.read_bytes()
        approval_public.write_bytes(b'FAKE APPROVAL KEY\n'+original_public)
        denied=run(launcher+tail,45)
        need(denied.returncode == 78 and
             'OPERATOR_AUTHORITY_NOT_INDEPENDENTLY_PINNED' in denied.stderr,
             'WRONG_AUTHORITY_PUBLIC_KEY_ACCEPTED')
        approval_public.write_bytes(original_public)
        installed_unchanged(old,old_archive,host,baseline)
        for cmd,reason in (
            (launcher[:6]+[str(receipt)+'-wrong']+launcher[7:]+tail,
             'WRONG_OPERATOR_RECEIPT_PATH'),
            (launcher[:8]+['0'*64]+launcher[9:]+tail,
             'WRONG_OPERATOR_APPROVAL_ANCHOR'),
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
        # Valid CI-signature on the wrong source commit must NOT permit
        # external source execution even with an unchanged signed archive SHA.
        assertions['source_commit'] = 'f' * 40
        seal()
        denied = run(launcher+tail,45)
        need(denied.returncode == 78 and
             'SIGNED_PROVENANCE_SOURCE_COMMIT_NOT_APPROVED' in denied.stderr and
             'ZAPRET2_PREPKG_VERIFY_EXEC=VERIFIED_SIGNED_SHA256:' not in denied.stderr,
             'SIGNED_UNAPPROVED_SOURCE_COMMIT_ACCEPTED')
        installed_unchanged(old,old_archive,host,baseline)
        assertions['source_commit'] = expected_commit
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
        denied=run(launcher[:16]+[str(verifier_link)]+launcher[17:]+tail,45)
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
            'signed_source_commit_matched_independent_expectation': True,
            'operator_source_commit_authenticated': False,
            'ci_operator_pty_receipt_record_and_inspect_verified': True,
            'receipt_pins_bound_to_seed_and_signed_archive_claims': True,
            'ci_ephemeral_detached_approval_signature_verified': True,
            'ci_ephemeral_signed_bounded_policy_verified': True,
            'approval_policy_expiry_and_revocation_negatives_verified': True,
            'approval_policy_authoritative_freshness': False,
            'approval_token_one_use_consumption_implemented': False,
            'operator_authority_approved_out_of_band': False,
            'receipt_operator_issuer_authenticated': False,
            'independent_production_issuer_approved': False,
            'operator_pin_record_is_release_authentication': False,
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
