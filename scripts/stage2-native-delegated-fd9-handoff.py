#!/usr/local/bin/python3
"""One-use native OPNsense old-hook FD9 delegation feasibility, NEVER a product updater.

The genuine published old 0.6.2_1 service and all hooks remain untouched.
A private executable LOCKF_BIN shim is allowed only by a root-owned ticket
from this one-use FD9 holder. No shim, ticket or bypass ships in the plugin.
This cannot protect stock firmware/Web or direct privileged pkg.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
LOCK = Path('/var/run/zapret2-lifecycle.lock')
OPTIN = 'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF'
PREFIX = 'STAGE2_DELEGATED_FD9='
NAME = 'os-zapret2-restyle'
OUTER = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 0 9; '
         'exec /usr/local/bin/python3 "$2" --inner "$3" "$4" "$5"')


class Refusal(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Refusal(why)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def qualify():
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64' and
         os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get(OPTIN) == '1' and
         os.environ.get('ZAPRET2_STAGE2_LOCKED_COLD_REVALIDATION') == '1' and
         os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK') == '1' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1',
         'DISPOSABLE_26_7_NATIVE_DELEGATION_OPTIN_REQUIRED')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def trusted_inode(path, mode):
    need(path.is_file() and not path.is_symlink(), 'DELEGATION_TICKET_UNTRUSTED')
    st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
         st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == mode,
         'DELEGATION_TICKET_MODE_OR_OWNER_UNTRUSTED')
    return st


def ticket_validate(data, observed_fd, nonce, expected_holder):
    need(isinstance(data, dict) and
         set(data) == {'nonce', 'holder_pid', 'dev', 'ino'} and
         isinstance(data['nonce'], str) and len(data['nonce']) == 64 and
         secrets.compare_digest(data['nonce'], nonce) and
         isinstance(data['holder_pid'], int) and
         data['holder_pid'] == expected_holder and expected_holder > 1 and
         isinstance(data['dev'], int) and isinstance(data['ino'], int) and
         data['dev'] == observed_fd.st_dev and
         data['ino'] == observed_fd.st_ino,
         'DELEGATED_LOCK_TICKET_INCORRECT')


def shim_arguments(argv):
    need(len(argv) == 4 and argv[:2] == ['-s', '-t'] and
         argv[2] in ('0', '1', '5', '30') and argv[3] == '9',
         'UNEXPECTED_DELEGATED_LOCK_REQUEST')


def independent_challenge():
    # The trusted holder must really keep the original FD9 busy.
    p = subprocess.run(['/bin/sh', '-c',
                        'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',
                        'sh', str(LOCK)], capture_output=True,
                       text=True, timeout=6, check=False)
    need(p.returncode == 75, 'ORIGINAL_FD9_NOT_ACTUALLY_EXCLUSIVE')


def shim(argv):
    qualify()
    shim_arguments(argv)
    path = Path(os.environ.get('ZAPRET2_STAGE2_DELEGATED_TICKET', ''))
    folder = path.parent
    need(folder.is_dir() and not folder.is_symlink() and
         folder.stat().st_uid == 0 and
         stat.S_IMODE(folder.stat().st_mode) == 0o700,
         'DELEGATION_DIRECTORY_UNTRUSTED')
    trusted_inode(path, 0o600)
    need(LOCK.is_file() and not LOCK.is_symlink(), 'ORIGINAL_FD9_LOCK_MISSING')
    st = LOCK.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1,
         'ORIGINAL_FD9_INODE_UNTRUSTED')
    fd = os.fstat(9)
    need(st.st_dev == fd.st_dev and st.st_ino == fd.st_ino,
         'DELEGATED_CHILD_FD9_NOT_HISTORICAL_INODE')
    holder = os.environ.get('ZAPRET2_STAGE2_DELEGATED_HOLDER', '')
    need(holder.isdecimal(), 'DELEGATED_HOLDER_UNQUALIFIED')
    pid = int(holder)
    data = json.loads(path.read_text(encoding='utf-8'))
    ticket_validate(data, fd,
                    os.environ.get('ZAPRET2_STAGE2_DELEGATED_NONCE', ''), pid)
    try:
        os.kill(pid, 0)
    except OSError:
        raise Refusal('DELEGATED_PARENT_HOLDER_NOT_ALIVE') from None
    independent_challenge()
    # The private directory is 0700 and marker is create/opened with O_NOFOLLOW.
    # No caller can derive success from this marker without real ticket checks.
    marker = folder / 'delegated.calls'
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
    fdout = os.open(marker, flags, 0o600)
    try:
        os.write(fdout, b'ACCEPTED\n')
    finally:
        os.close(fdout)
    return 0


def count_calls(folder):
    marker = folder / 'delegated.calls'
    if not marker.exists():
        return 0
    trusted_inode(marker, 0o600)
    content = marker.read_bytes()
    need(content and len(content) <= 4096 and
         all(line == b'ACCEPTED' for line in content.splitlines()),
         'DELEGATED_CALL_MARKER_MALFORMED')
    return len(content.splitlines())


def run_pkg(path, env):
    # Actual native root pkg, NOT a mock. Only permitted on throwaway guest
    # after the real old closed-owner and authentic hook gate.
    proc = subprocess.Popen(
        ['/usr/sbin/pkg', '-o', 'REPO_AUTOUPDATE=false', 'add', '-f',
         str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, pass_fds=(9,), start_new_session=True)
    try:
        out, err = proc.communicate(timeout=230)
    except subprocess.TimeoutExpired:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate(timeout=8)
        raise Refusal('NATIVE_PKG_UNBOUNDED_WITH_DELEGATED_FD9') from None
    return proc.returncode, out, err


def inside_lock(archive, successor, expected_sha):
    qualify()
    old = load('stage0-installed-predecessor-readonly.py')
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    stopped = load('stage2-opnsense-real-native-stopped-upgrade.py')
    clean = stopped.clean
    native = stopped.native
    need(len(expected_sha) == 64 and re.fullmatch(r'[a-f0-9]{64}', expected_sha),
         'BAD_NATIVE_SUCCESSOR_SHA')
    need(successor.is_file() and not successor.is_symlink() and
         clean.digest(successor) == expected_sha,
         'NATIVE_SUCCESSOR_PACKAGE_CHANGED')
    locked.check_fd9()
    need(locked.inside_lock(archive)['status'] ==
         'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC',
         'REAL_OLD_COLD_ADMISSION_UNQUALIFIED')
    locked.check_fd9()
    config_before = Path('/conf/config.xml').read_bytes()
    initial = old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME)
    need(old.installed_manifest_from_json(initial)['version'] == '0.6.2_1',
         'REAL_OLD_PKGDB_VERSION_CHANGED')
    service = Path(old.SERVICE)
    with tempfile.TemporaryDirectory(prefix='stage2-fd9-delegation-') as d:
        folder = Path(d)
        os.chmod(folder, 0o700)
        script = folder / 'trusted-old-lockf'
        script.write_bytes(Path(__file__).read_bytes())
        script.chmod(0o700)
        nonce = secrets.token_hex(32)
        fd9 = os.fstat(9)
        ticket = folder / 'owner-ticket.json'
        ticket.write_text(json.dumps({
            'nonce': nonce, 'holder_pid': os.getpid(),
            'dev': fd9.st_dev, 'ino': fd9.st_ino
        }), encoding='utf-8')
        ticket.chmod(0o600)
        env = os.environ.copy()
        env.update({
            'LOCKF_BIN': str(script),
            'ZAPRET2_STAGE2_DELEGATED_TICKET': str(ticket),
            'ZAPRET2_STAGE2_DELEGATED_NONCE': nonce,
            'ZAPRET2_STAGE2_DELEGATED_HOLDER': str(os.getpid())
        })
        # Authentic unchanged old Status, but with a *private test-only*
        # delegated lock call. Root stock hook/service bytes stay unchanged.
        status = subprocess.run(
            [str(service), 'status'], env=env, pass_fds=(9,),
            capture_output=True, text=True, timeout=18, check=False)
        need(status.returncode == 1 and
             'zapret is not running' in status.stdout,
             'GENUINE_OLD_STATUS_NOT_COLD_UNDER_DELEGATION:' +
             str(status.returncode))
        before_calls = count_calls(folder)
        need(before_calls >= 1, 'ORIGINAL_OLD_LOCKF_OVERRIDE_NOT_ACTUALLY_CALLED')
        locked.check_fd9()
        need(old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME) == initial and
             Path('/conf/config.xml').read_bytes() == config_before,
             'PREFLIGHT_MODIFIED_ORIGINAL_STATE')
        rc, out, err = run_pkg(successor, env)
        locked.check_fd9()
        native_calls = count_calls(folder) - before_calls
        new_identity = native.NAME + '|' + native.VERSION + '_' + native.REVISION
        identity = stopped.load('stage2-opnsense-real-unsafe-owner-replacement.py')
        observed_identity = identity.installed_identity()
        observed = {
            'real_pkg_rc': rc,
            'old_test_status_delegate_calls': before_calls,
            'delegated_lock_calls_during_native_pkg': native_calls,
            'installed_after_actual_pkg': observed_identity,
            'native_successor_sha256': expected_sha,
            'original_published_archive_sha256': old.ARCHIVE_SHA,
            'real_fd9_retained_through_pkg': True,
            'native_pkg_hook_output_success_signature':
                'os-zapret2-restyle was installed.' in out,
            'hook_refusal_diagnostic_observed': any(
                text in out + err for text in (
                    'incomplete zapret lifecycle',
                    'cannot determine zapret service state',
                    'could not be stopped')),
            'config_bytes_changed': Path('/conf/config.xml').read_bytes() != config_before,
            'shim_installed_into_product': False,
        }
        print('STAGE2_DELEGATED_PRE_DISPOSAL=' +
              json.dumps(observed, sort_keys=True), flush=True)
        need(clean.digest(successor) == expected_sha,
             'NATIVE_SUCCESSOR_ARCHIVE_MUTATED')
        # Even when pkg returns zero, requiring actual delegated hook calls
        # is critical: otherwise pkg may have stripped LOCKF_BIN and bypassed
        # a refusing real hook exactly as in the known unsafe _79 case.
        need(native_calls >= 1, 'NATIVE_PKG_DID_NOT_INVOKE_DELEGATED_OLD_LOCKF')
        need(rc == 0 and observed_identity == new_identity and
             observed['native_pkg_hook_output_success_signature'] and
             not observed['hook_refusal_diagnostic_observed'],
             'NATIVE_DELEGATED_PKG_SUCCESS_OR_HOOK_UNQUALIFIED')
        manifest, pkgdb = clean.installed_pkg_manifest(successor)
        files = clean.verify_installed_files(successor, manifest)
        # Do NOT call clean.cold_status() while the original FD9 remains
        # exclusive: its ordinary new Status would independently reacquire
        # the lock and reproduce the historical _88 self-contention.
        new_service = Path('/usr/local') / native.SERVICE
        post = subprocess.run(
            [str(new_service), 'status'], env=env, pass_fds=(9,),
            capture_output=True, text=True, timeout=18, check=False)
        need(post.returncode == 1 and
             post.stdout.strip() == 'zapret is not running',
             'NEW_SERVICE_STATUS_UNQUALIFIED_UNDER_OWNED_FD9:' +
             str(post.returncode))
        need(count_calls(folder) > before_calls + native_calls,
             'NEW_SERVICE_DID_NOT_USE_PRIVATE_DELEGATED_FD9')
        for name in clean.PRESERVED:
            marker = Path(name)
            need(not marker.exists() and not marker.is_symlink(),
                 'NEW_SERVICE_RESTART_OR_RUNTIME_MARKER_PRESENT')
        service_status = {'real_new_status_exit': post.returncode,
                          'new_status_uses_temporary_fd9_delegation': True}
        cold = stopped.verify_cold_runtime()
        preserved = stopped.prove_preserved_config(
            config_before, Path('/conf/config.xml').read_bytes())
        return {'schema': 1,
                'status': 'PASS_TEST_ONLY_DELEGATED_NATIVE_OLD_HOOK_HANDOFF',
                'real_original_fd9_continuous': True,
                'old_predecessor_status_under_delegation': 'STOPPED',
                'genuine_old_hook_lock_invocations_during_pkg': native_calls,
                'real_native_successor_sha256': expected_sha,
                'installed_native_package_identity': observed_identity,
                'installed_files_verified': bool(files),
                'installed_native_dependency_manifest_verified': bool(pkgdb),
                'new_service_cold': bool(service_status),
                'new_kernel_cold': bool(cold),
                'config_registered_without_foreign_changes': bool(preserved),
                'test_only_lockf_env_override': True,
                'production_pkg_or_hooks_modified': False,
                'stock_firmware_web_covered': False,
                'direct_root_pkg_covered': False,
                'running_owner_proven': False,
                'negative_no_pkg_invocation_proven_here': False,
                'crash_rollback_proven': False,
                'supported_product_updater_implemented': False,
                'lh08_ac11_accepted': False,
                'owner_appliance_modified': False}


def execute(archive):
    qualify()
    stopped = load('stage2-opnsense-real-native-stopped-upgrade.py')
    native, clean = stopped.native, stopped.clean
    native.gate()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    built = native.build()
    need(built['status'] == 'PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY' and
         built['project_sha'] == os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA'),
         'NATIVE_BUILD_SOURCE_QUALIFICATION_FAILED')
    pkg = native.ROOT / built['output']
    expected = built['real_native_pkg']['sha256']
    need(pkg.is_file() and not pkg.is_symlink() and
         clean.digest(pkg) == expected, 'BUILT_PACKAGE_SHA_MISMATCH')
    installed = stopped.load('stage0-opnsense-installed-predecessor.py')
    need(installed.install_and_verify(archive)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'ORIGINAL_AUTHENTIC_PREDECESSOR_NOT_INSTALLED')
    guard = stopped.load('stage0-opnsense-prepkg-readonly.py')
    need(guard.snapshot(archive)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'REAL_OLD_STOPPED_PRECONDITION_MISSING')
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    need(locked.LOCK == LOCK, 'NONHISTORICAL_FD9_PATH')
    p = subprocess.run(
        ['/bin/sh', '-c', OUTER, 'sh', str(LOCK),
         str(Path(__file__).resolve()), str(archive), str(pkg), expected],
        capture_output=True, text=True, timeout=310, check=False)
    need(p.returncode == 0, 'NATIVE_DELEGATION_EXPERIMENT_REFUSED:' +
         p.stderr[-550:])
    lines = [line[len(PREFIX):] for line in p.stdout.splitlines()
             if line.startswith(PREFIX)]
    need(len(lines) == 1, 'NO_SINGLE_AUTHENTIC_HANDOFF_WITNESS')
    result = json.loads(lines[0])
    need(result.get('status') == 'PASS_TEST_ONLY_DELEGATED_NATIVE_OLD_HOOK_HANDOFF'
         and result.get('lh08_ac11_accepted') is False,
         'FALSE_PRODUCT_UPGRADE_AUTHORIZATION')
    return result


def main():
    try:
        if len(sys.argv) == 5 and sys.argv[1] == '--inner':
            result = inside_lock(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
        elif len(sys.argv) == 2 and sys.argv[1].startswith('-s'):
            # No alternative shim syntax; callers pass -s -t <timeout> 9.
            raise Refusal('UNEXPECTED_SHIM_ARGUMENT_SHAPE')
        elif len(sys.argv) == 5 and sys.argv[1] == '-s':
            return shim(sys.argv[1:])
        elif len(sys.argv) == 2:
            result = execute(Path(sys.argv[1]))
        else:
            raise Refusal('REQUIRES_EXACT_GUEST_ARGS')
        print(PREFIX + json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError,
            subprocess.SubprocessError) as exc:
        print(PREFIX + 'REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
