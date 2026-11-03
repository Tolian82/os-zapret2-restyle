#!/usr/local/bin/python3
"""One-use actual OPNsense configd worker inline native-pkg veto.

An incoming authentic +POST_INSTALL reloads configd by terminating its
current worker. Never execute mutating native pkg *inside that worker*.
Prove the exact self-termination hazard and refuse before pkg, preserving
installed predecessor and owned Config/IPFW/processes/markers. One-use CI
only; the stock firmware route and direct root pkg remain unsupported.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ACTION = Path('/usr/local/opnsense/service/conf/actions.d/actions_zapret2_stage3_ci.conf')
DIAGNOSTIC = Path('/tmp/zapret2-stage3-configd-inline-ci.witness')
ARCHIVE = Path('/tmp/os-zapret2-restyle-0.6.2_1.pkg')
PREFIX = 'STAGE3_CONFIGD_INLINE_VETO='
OLD_SHA = '1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f'


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def gate(head):
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD'
         and os.uname().machine == 'amd64'
         and os.environ.get('GITHUB_ACTIONS') == 'true'
         and os.environ.get('ZAPRET2_STAGE3_CONFIGD_INLINE_VETO') == '1',
         'ROOT_DISPOSABLE_NATIVE_CONFIGD_ONLY')
    need(re.fullmatch(r'[a-f0-9]{40}', head or '') is not None
         and head == os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA'),
         'EXACT_NATIVE_HEAD_NOT_ATTESTED')
    old = load('stage0-installed-predecessor-readonly.py')
    need(ARCHIVE.is_file() and not ARCHIVE.is_symlink()
         and old.digest(ARCHIVE.read_bytes()) == OLD_SHA,
         'AUTHENTIC_PUBLISHED_OLD_ARCHIVE_UNTRUSTED')


def command(args, timeout=30):
    p = subprocess.run(args, capture_output=True, text=True,
                       timeout=timeout, check=False)
    if p.returncode == 1 and args[:1] == ['/usr/bin/pgrep']:
        raise Refusal('REAL_CONFIGD_WORKER_PGREP_NO_MATCH')
    if p.returncode == 1 and args[:1] == ['/bin/ps']:
        raise Refusal('REAL_CONFIGD_WORKER_ANCESTRY_PS_GONE')
    need(p.returncode == 0, 'CONFIGD_NATIVE_COMMAND_REFUSED:' +
         str(p.returncode) + ':' + p.stderr[-190:])
    return p.stdout


def parent_of(pid):
    x = command(['/bin/ps', '-o', 'ppid=', '-p', str(pid)], 5).strip()
    need(re.fullmatch(r'[0-9]+', x) is not None,
         'CONFIGD_CALLER_PARENT_UNKNOWN')
    return int(x)


def worker_ancestry():
    target = Path('/var/run/configd.pid')
    need(target.is_file() and not target.is_symlink(),
         'REAL_CONFIGD_DAEMON_PID_MISSING')
    root = target.read_text().strip()
    need(re.fullmatch(r'[0-9]+', root) is not None,
         'REAL_CONFIGD_DAEMON_PID_INVALID')
    workers = command(['/usr/bin/pgrep','-P',root,'-f',
                       '/usr/local/opnsense/service/configd.py console'],5)
    found = workers.split()
    need(len(found) == 1 and found[0].isdecimal(),
         'REAL_CONFIGD_WORKER_AMBIGUOUS')
    worker = int(found[0])
    parent = os.getppid()
    for _ in range(10):
        if parent == worker:
            return {'worker_ancestor': True,
                    'real_worker_pid': worker, 'real_parent_pid':int(root)}
        need(parent > 1 and parent != int(root),
             'NOT_INSIDE_ACTUAL_CONFIGD_WORKER')
        parent = parent_of(parent)
    raise Refusal('NOT_INSIDE_ACTUAL_CONFIGD_WORKER')


def actual_incoming_hook():
    p = HERE.parent/'pkg/+POST_INSTALL'
    need(p.is_file() and not p.is_symlink(),
         'INCOMING_PACKAGE_POST_INSTALL_HOOK_MISSING')
    source = p.read_text()
    for witness in ('reload_configd_actions()', 'CONFIGD_PID_FILE=',
                    'CONFIGD_WORKER_PATTERN=', 'configd_old_worker',
                    'KILL_BIN', '-TERM', 'reload_configd_actions; then'):
        need(witness in source,
             'GENUINE_INCOMING_HOOK_WORKER_KILL_NOT_PROVEN:' + witness)
    return 'INCOMING_POST_INSTALL_TERMINATES_CURRENT_CONFIGD_WORKER'


def inside(head):
    gate(head)
    old = load('stage0-installed-predecessor-readonly.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    raw = old.run('pkg','info','-R','--raw-format','json','os-zapret2-restyle')
    need(old.installed_manifest_from_json(raw)['version'] == '0.6.2_1',
         'PUBLISHED_INSTALLED_OLD_IDENTITY_NOT_PROVEN')
    need(guard.snapshot(ARCHIVE)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'GENUINE_OLD_OWNER_NOT_COLD')
    hook = actual_incoming_hook()
    unknown_reason = ''
    try:
        ancestry = worker_ancestry()
    except Refusal as exc:
        # Unknown/vanished/ambiguous configd worker is an independent
        # fail-closed reason, NOT proof of a safe synchronous transaction.
        # Only bounded worker-census/ancestry failures qualify.
        supported = {
            'REAL_CONFIGD_WORKER_PGREP_NO_MATCH',
            'REAL_CONFIGD_WORKER_ANCESTRY_PS_GONE',
            'REAL_CONFIGD_WORKER_AMBIGUOUS',
            'NOT_INSIDE_ACTUAL_CONFIGD_WORKER',
        }
        need(str(exc) in supported, 'UNQUALIFIED_CONFIGD_PROBE:' + str(exc))
        ancestry = {'worker_ancestor':False}
        unknown_reason = str(exc)
    confirmed = ancestry['worker_ancestor']
    return {'schema':1,
            'status':('PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION'
                      if confirmed else
                      'PASS_REAL_CONFIGD_UNKNOWN_WORKER_REFUSED_BEFORE_PKG'),
            'worker_is_real_configd_ancestor':confirmed,
            'configd_worker_census_qualified':confirmed,
            'unknown_worker_refusal_reason':unknown_reason,
            'incoming_hook_targets_configd_worker_by_source':True,
            'incoming_hook_terminates_that_worker':confirmed,
            'hook_diagnostic':hook,
            'historical_published_old_verified':True,
            'native_pkg_called_inside_configd_worker':False,
            'stock_firmware_web_intercepted':False,
            'independent_pkg_worker_implemented':False,
            'lh08_ac11_accepted':False,'owner_appliance_modified':False}


def script_bytes(head):
    path = str(Path(__file__).resolve())
    need(re.fullmatch(r'/[a-zA-Z0-9_./-]+',path) is not None,
         'TEMP_ACTION_SCRIPT_PATH_UNTRUSTED')
    return ('[veto]\n'
            'command:/usr/bin/env GITHUB_ACTIONS=true '
            'ZAPRET2_STAGE3_CONFIGD_INLINE_VETO=1 '
            'ZAPRET2_NATIVE_PROJECT_SHA=' + head +
            ' /usr/local/bin/python3 ' + path + ' --inside ' + head + '\n'
            'parameters:\n'
            'type:script_output\n'
            'message:read-only test of real configd pkg self-reload hazard\n'
            'timeout:90\n').encode()


def attested_action(content):
    need(ACTION.is_file() and not ACTION.is_symlink(),
         'OWNED_TEST_CONFIGD_ACTION_MISSING_OR_SYMLINK')
    st = ACTION.lstat()
    need(st.st_uid == 0 and st.st_nlink == 1
         and stat.S_ISREG(st.st_mode)
         and stat.S_IMODE(st.st_mode) == 0o600
         and ACTION.read_bytes() == content,
         'TEST_CONFIGD_ACTION_MODIFIED_OR_FOREIGN')



def write_inner_witness(label):
    """Bounded root-only CI verdict; never logs config.xml or raw service text."""
    need(os.geteuid() == 0 and
         os.environ.get('ZAPRET2_STAGE3_CONFIGD_INLINE_VETO') == '1',
         'DISPOSABLE_CONFIGD_DIAGNOSTIC_NOT_ALLOWED')
    safe = re.sub(r'[^A-Za-z0-9_:.-]', '_', str(label)[:155])
    fd = os.open(DIAGNOSTIC, os.O_WRONLY | os.O_CREAT |
                 os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'w') as out:
        out.write(safe + '\n')
        out.flush()
        os.fsync(out.fileno())


def read_and_remove_inner_witness():
    if not DIAGNOSTIC.exists() and not DIAGNOSTIC.is_symlink():
        return 'INNER_PYTHON_NOT_SEEN'
    need(DIAGNOSTIC.is_file() and not DIAGNOSTIC.is_symlink(),
         'INNER_DIAGNOSTIC_UNTRUSTED')
    st = DIAGNOSTIC.lstat()
    need(st.st_uid == 0 and st.st_nlink == 1
         and stat.S_ISREG(st.st_mode)
         and stat.S_IMODE(st.st_mode) == 0o600
         and st.st_size <= 170,
         'INNER_DIAGNOSTIC_OWNER_OR_MODE_UNTRUSTED')
    data = DIAGNOSTIC.read_text().strip()
    need(re.fullmatch(r'[A-Za-z0-9_:.-]{3,160}', data) is not None,
         'INNER_DIAGNOSTIC_INVALID')
    DIAGNOSTIC.unlink()
    return data


def execute(head):
    gate(head)
    guest = load('stage0-opnsense-guest-readonly.py')
    installed = load('stage0-opnsense-installed-predecessor.py')
    old = load('stage0-installed-predecessor-readonly.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    managed = load('stage2-managed-prepkg-veto-witness.py')
    need(guest.evaluate(guest.observe())['status'] ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY',
         'NOT_ONE_USE_OFFICIAL_OPNSENSE_26_7')
    need(not ACTION.exists() and not ACTION.is_symlink()
         and not DIAGNOSTIC.exists() and not DIAGNOSTIC.is_symlink(),
         'LAB_CONFIGD_ACTION_OR_RESULT_ALREADY_EXISTS')
    need(installed.install_and_verify(ARCHIVE)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'AUTHENTIC_OLD_BASELINE_INSTALL_UNVERIFIED')
    need(guard.snapshot(ARCHIVE)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_OLD_NOT_COLD_BEFORE_CONFIGD')
    before = managed.owner_snapshot(old, guard, ARCHIVE)
    payload = script_bytes(head)
    fd = os.open(ACTION, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW, 0o600)
    diagnostic = 'INNER_PYTHON_NOT_SEEN'
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        attested_action(payload)
        command(['/usr/sbin/service','configd','restart'],45)
        registry = command(['/usr/local/sbin/configctl',
                            'configd','actions'],25)
        need('zapret2_stage3_ci' in registry,
             'REGISTERED_TEST_CONFIGD_ACTION_NOT_VISIBLE')
        output = command(['/usr/local/sbin/configctl',
                          'zapret2_stage3_ci','veto'],100)
        rows = [x.split(PREFIX,1)[1].strip()
                for x in output.splitlines() if PREFIX in x]
        # The action is fixed, root-owned and parameterless; never print
        # arbitrary configd output. Preserve only its bounded shape/category.
        if len(rows) != 1:
            normalized = re.sub(r'[^A-Za-z0-9_: .-]', '?', output[:75])
            inner_reason = read_and_remove_inner_witness()
            raise Refusal('REAL_CONFIGCTL_RESULT_MISSING:LINES_' +
                          str(len(rows)) + ':BYTES_' + str(len(output)) +
                          ':SUMMARY_' + normalized + ':INNER_' + inner_reason)
        witness = json.loads(rows[0])
        expected = {
            'PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION',
            'PASS_REAL_CONFIGD_UNKNOWN_WORKER_REFUSED_BEFORE_PKG',
        }
        need(witness.get('status') in expected
             and witness.get('worker_is_real_configd_ancestor') is
             (witness.get('status') ==
              'PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION')
             and witness.get('native_pkg_called_inside_configd_worker')
             is False and witness.get('lh08_ac11_accepted') is False,
             'REAL_CONFIGD_WORKER_VETO_NOT_VERIFIED')
    finally:
        try:
            diagnostic = read_and_remove_inner_witness()
            attested_action(payload)
            ACTION.unlink()
            command(['/usr/sbin/service','configd','restart'],45)
        except Exception as exc:
            raise Refusal('TEST_ACTION_CLEANUP_FAILED:' + str(exc)[:180]) from None
    need(diagnostic in {
         'PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION',
         'PASS_REAL_CONFIGD_UNKNOWN_WORKER_REFUSED_BEFORE_PKG'},
         'INPROCESS_VETO_DID_NOT_RECORD_REAL_PYTHON_WITNESS:' + diagnostic)
    need(managed.owner_snapshot(old,guard,ARCHIVE) == before,
         'VETO_CHANGED_PKGDB_FILE_MODES_CONFIG_MARKERS_PROCESS_OR_IPFW')
    return {'schema':1,
            'status':('PASS_TEST_ONLY_REAL_CONFIGD_PREPKG_WORKER_VETO'
                      if witness['worker_is_real_configd_ancestor'] else
                      'PASS_TEST_ONLY_REAL_CONFIGD_UNKNOWN_WORKER_VETO'),
            'configd_worker_ancestry_actually_verified':
                witness['worker_is_real_configd_ancestor'],
            'unknown_worker_refusal_reason':
                witness.get('unknown_worker_refusal_reason', ''),
            'original_pkgdb_files_modes_config_process_ipfw_unchanged':True,
            'configd_action_registered_invoked_then_removed':True,
            'mutating_native_pkg_invoked_after_old_baseline':False,
            'stock_web_firmware_protected':False,
            'detached_supervisor_implemented':False,
            'lh08_ac11_accepted':False,'owner_appliance_modified':False}


def main():
    try:
        need(len(sys.argv)==2 or
             (len(sys.argv)==3 and sys.argv[1]=='--inside'),
             'EXACT_TEST_ONLY_ARGUMENTS_REQUIRED')
        report=(inside(sys.argv[2]) if len(sys.argv)==3
                else execute(sys.argv[1]))
        if len(sys.argv)==3:
            write_inner_witness(report['status'])
        print(PREFIX+json.dumps(report,sort_keys=True),flush=True)
        return 0
    except (Refusal,OSError,ValueError,KeyError,TypeError,
            subprocess.SubprocessError) as exc:
        if len(sys.argv)==3 and sys.argv[1]=='--inside':
            try:
                write_inner_witness('REFUSED:'+str(exc))
            except (Refusal,OSError):
                pass
        print(PREFIX+'REFUSED:'+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.exit(main())
