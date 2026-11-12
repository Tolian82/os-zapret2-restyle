#!/usr/bin/env python3
"""P5b2b: exact installed real-builder/no-mutation witness, disposable guest only."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path('/conf/config.xml')
ENGINE = Path('/usr/local/etc/zapret2/binaries/my/dvtws2')
SERVICE = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh')
LOCK = Path('/var/run/zapret2-lifecycle.lock')
BACKEND = SERVICE.parent / 'backend'


def need(ok, why):
    if not ok:
        raise RuntimeError('P5B2B_REFUSED:' + why)


def run(*args, timeout=100):
    return subprocess.run(args, capture_output=True, timeout=timeout)


def tree(root):
    root = Path(root)
    if not root.exists() and not root.is_symlink():
        return ('absent',)
    need(not root.is_symlink(), 'root-symlink')
    if root.is_file():
        return ('file', hashlib.sha256(root.read_bytes()).hexdigest())
    need(root.is_dir(), 'unexpected-root-type')
    values = []
    bytes_seen = 0
    for d, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        files.sort()
        for name in dirs + files:
            item = Path(d) / name
            s = item.lstat()
            rel = item.relative_to(root).as_posix()
            need(len(values) < 12000, 'persistent-tree-too-large')
            if stat.S_ISLNK(s.st_mode):
                values.append((rel, 'link', os.readlink(item)))
            elif stat.S_ISDIR(s.st_mode):
                values.append((rel, 'dir', stat.S_IMODE(s.st_mode)))
            else:
                need(stat.S_ISREG(s.st_mode), 'persistent-type-unexpected')
                bytes_seen += s.st_size
                need(bytes_seen <= 256 * 1024 * 1024, 'persistent-bytes-too-many')
                values.append((rel, 'file', stat.S_IMODE(s.st_mode),
                               hashlib.sha256(item.read_bytes()).hexdigest()))
    return tuple(values)


def read_kernel(*argv):
    r = run(*argv, timeout=12)
    need(len(r.stdout) <= 2 * 1024 * 1024, 'ipfw-output-too-large')
    return (r.returncode, hashlib.sha256(r.stdout).hexdigest())


def snapshot():
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()
    ps = run('/bin/ps', '-ax', '-o', 'pid=', '-o', 'lstart=', '-o', 'command=', timeout=10)
    need(ps.returncode == 0, 'ps-failed')
    engines = tuple(sorted(x for x in ps.stdout.decode(errors='replace').splitlines()
                           if str(ENGINE) in x and 'p5b2b_native_witness' not in x))
    return {
        'fd9': (os.fstat(9).st_dev, os.fstat(9).st_ino),
        'config': tree(CONFIG), 'history': tree('/conf/backup'),
        'apply': tree('/var/db/zapret2/shared-apply'),
        'shared_work': tree('/var/db/zapret2/shared-work'),
        'runtime': tree('/usr/local/etc/zapret2/runtime-v2'),
        'extra': tree('/var/db/zapret2-restyle/extra-resources'),
        'args': tree('/usr/local/etc/zapret2/zapret.conf'),
        'hosts': tree('/usr/local/etc/zapret2/hostlist.txt'),
        'exclude': tree('/usr/local/etc/zapret2/hostlist-exclude.txt'),
        'pidfile': tree('/var/run/dvtws2.pid'), 'engine_ps': engines,
        'ipfw_rules': read_kernel('/sbin/ipfw', '-q', 'list'),
        'ipfw_tables': read_kernel('/sbin/ipfw', 'table', 'all', 'list'),
    }


def hold_fd9():
    need(LOCK.is_file() and not LOCK.is_symlink(), 'original-lock-not-present')
    fd = os.open(LOCK, os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if fd != 9:
            os.dup2(fd, 9, inheritable=True)
    finally:
        if fd != 9:
            os.close(fd)
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()


def preview_check(builder, label, candidate, expected_engine=None):
    before = snapshot()
    error = None
    result = None
    try:
        result = builder.preview_prepared_xml(candidate, native=True)
    except BaseException as exc:
        error = exc
    after = snapshot()
    need(before == after, 'preview-mutated-state:' + label)
    need(not list(Path('/tmp').glob('zapret-p5b-*')), 'preview-workspace-remains:' + label)
    if expected_engine:
        need(error is None, 'preview-build-refused:' + label + ':' +
             getattr(error, 'code', type(error).__name__))
        info = result.get('native_validation', {})
        need(info.get('mapped_validation') == 'native_mapped_valid' and
             info.get('engine_native_dry_run') == expected_engine and
             result.get('workspace_cleaned') is True and
             result.get('safe_to_apply') is False, 'native-validation-failed:' + label)
    return result, error


def set_guest_lo0():
    # Native model save is setup, BEFORE the read-only RUNNING preview.
    php = '''require_once("script/load_phalcon.php");
$c=\\OPNsense\\Core\\Config::getInstance();$c->lock();try{
$m=new \\OPNsense\\Zapret\\Zapret();
if(!$m->setNodeByReference("general.enabled","1") ||
 !$m->setNodeByReference("general.waninterface","lo0") ||
 count($m->performValidation(false)) || !$m->serializeToConfig(false,true))
 throw new \\RuntimeException("invalid disposable model");
$c->save(["description"=>"P5b2b disposable lo0 setup"]);
}finally{$c->unlock();}'''
    need(run('/usr/local/bin/php', '-r', php, timeout=30).returncode == 0,
         'guest-only-model-save-failed')


def native():
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_P5B2B_DISPOSABLE_NATIVE') == '1' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1' and
         platform.system() == 'FreeBSD' and os.geteuid() == 0 and
         Path('/usr/local/opnsense').is_dir() and SERVICE.is_file() and
         CONFIG.is_file() and
         run('pkg', 'info', '-e', 'os-zapret2-restyle', timeout=12).returncode == 0,
         'not-disposable-installed-OPNsense')
    need(not list(Path('/tmp').glob('zapret-p5b-*')), 'preexisting-preview-workspace')
    sys.path.insert(0, str(BACKEND))
    import strategy_preview_build as builder
    # Disposable-test diagnostic marker only. Keep every ORIGINAL module,
    # orchestrator and argument; identify the last static import on failure.
    # The marker is private to WORK, removed by the preview coordinator.
    expected_load = '    . "$BACKEND_DIR/$module.sh"'
    expected_call = 'done\norchestrator_build_release \\'
    need(builder.BUILD_SH.count(expected_load) == 1 and
         builder.BUILD_SH.count(expected_call) == 1,
         'builder-shell-diagnostic-anchor-unexpected')
    builder.BUILD_SH = builder.BUILD_SH.replace(
        expected_load,
        '    printf "%s" "$module" > "$WORK/p5b2b-checkpoint"\n' +
        expected_load, 1).replace(
        expected_call,
        'done\nprintf "orchestrator" > "$WORK/p5b2b-checkpoint"\n' +
        'orchestrator_build_release \\', 1)
    # Diagnostic-only observer: report ONLY the bounded stage/state enum,
    # never stage message, XML, hostlist, stderr or generated argument bytes.
    real_build = builder._run_builder
    original_popen = builder.subprocess.Popen

    def run_with_private_error_category(work):
        # Another targeted test instruments the same Popen to inject a real
        # KeyboardInterrupt. Keep that instrumentation untouched.
        if builder.subprocess.Popen is not original_popen:
            return real_build(work)
        logfile = work / 'p5b2b-private-stderr'
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
        descriptor = os.open(logfile, flags, 0o600)
        with os.fdopen(descriptor, 'wb') as private_stderr:
            def capture(*args, **kwargs):
                if args and isinstance(args[0], list) and \
                        len(args[0]) >= 4 and args[0][3] == 'p5b2a-build':
                    kwargs['stderr'] = private_stderr
                return original_popen(*args, **kwargs)
            with patch.object(builder.subprocess, 'Popen', side_effect=capture):
                try:
                    return real_build(work)
                except builder.PrivateBuildRefused:
                    private_stderr.flush()
                    data = logfile.read_bytes()[:32768].lower()
                    if not data:
                        category = 'NO_SHELL_STDERR'
                    elif b'parameter not set' in data or b'unbound variable' in data:
                        category = 'UNSET_SHELL_VARIABLE'
                    elif b'syntax error' in data:
                        category = 'SHELL_SYNTAX_ERROR'
                    elif b'permission denied' in data:
                        category = 'SHELL_PERMISSION'
                    elif b'not found' in data or b'no such file' in data:
                        category = 'SHELL_COMMAND_OR_FILE_MISSING'
                    else:
                        category = 'OTHER_NATIVE_BUILDER_REFUSAL'
                    print('P5B2B_SHELL_FAILURE_CLASS=' + category, file=sys.stderr)
                    raise

    def observe_builder_stage(work):
        try:
            return run_with_private_error_category(work)
        except builder.PrivateBuildRefused:
            stage_file = work / 'build-stage.status'
            if stage_file.is_file() and not stage_file.is_symlink() and \
                    stage_file.stat().st_size <= 4096:
                fields = stage_file.read_text(errors='replace').split('|', 5)
                if len(fields) == 6 and fields[2] in (
                        'config', 'parser', 'targets', 'ports', 'generator',
                        'validator', 'ready') and fields[3] in (
                        'running', 'failed', 'ok'):
                    print('P5B2B_LAST_STAGE=' + fields[2] + ':' + fields[3],
                          file=sys.stderr)
            marker = work / 'p5b2b-checkpoint'
            if marker.is_file() and not marker.is_symlink() and \
                    marker.stat().st_size < 36:
                value = marker.read_text(errors='replace').strip()
                if value in ('common', 'config', 'parser', 'registry', 'storage',
                             'targets', 'target_mode', 'profile_normalizer',
                             'profile_pipeline', 'exclude', 'blobs', 'ports',
                             'firewall', 'generator', 'validator', 'atomic',
                             'stage', 'launcher', 'supervisor', 'orchestrator',
                             'apply_runtime'):
                    print('P5B2B_LAST_LOADED=' + value, file=sys.stderr)
            raise
    builder._run_builder = observe_builder_stage
    hold_fd9()
    try:
        _, bad = preview_check(builder, 'invalid-xml', b'<opnsense/>')
        need(isinstance(bad, builder.PrivateBuildRefused) and
             bad.code == 'CANDIDATE_XML_MODEL_INVALID', 'invalid-xml-not-refused')
        need(not ENGINE.exists(), 'missing-runtime-precondition-false')
        result, failure = preview_check(builder, 'missing-runtime', CONFIG.read_bytes())
        need(failure is not None or
             result['native_validation']['engine_native_dry_run'] != 'passed',
             'missing-runtime-false-pass')
    finally:
        os.close(9)

    # Reuse existing installed G03 runtime setup ONLY; no legacy test matrices.
    spec = importlib.util.spec_from_file_location(
        'p5b2b_g03', ROOT / 'scripts/stage2-opnsense-g03-first-install.py')
    g03 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g03)
    state = g03.dispatch_and_poll()
    need(state['installed'] == '1' and state['service'] == 'stopped',
         'upstream-install-incomplete')
    hold_fd9()
    try:
        preview_check(builder, 'stopped', CONFIG.read_bytes(), 'passed')
        # Instrument cancellation at the REAL builder child wait. This is
        # not proof of arbitrary external process-kill recovery.
        real_popen = builder.subprocess.Popen
        def interrupted(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            if not (args and isinstance(args[0], list) and
                    len(args[0]) >= 4 and args[0][3] == 'p5b2a-build'):
                return child
            original_wait = child.wait
            calls = [0]
            def wait(timeout=None):
                calls[0] += 1
                if calls[0] == 1:
                    raise KeyboardInterrupt()
                return original_wait(timeout=timeout)
            child.wait = wait
            return child
        before = snapshot()
        with patch.object(builder.subprocess, 'Popen', side_effect=interrupted):
            try:
                builder.preview_prepared_xml(CONFIG.read_bytes(), native=True)
            except KeyboardInterrupt:
                pass
            else:
                raise RuntimeError('instrumented-cancel-not-observed')
        need(before == snapshot(), 'instrumented-cancel-mutated-state')
        need(not list(Path('/tmp').glob('zapret-p5b-*')),
             'instrumented-cancel-left-workspace')
    finally:
        os.close(9)
    set_guest_lo0()
    started = False
    try:
        command = run('/usr/local/sbin/configctl', 'zapret', 'start', timeout=100)
        need(command.returncode == 0, 'guest-running-start-refused')
        started = True
        need(run(str(SERVICE), 'status', timeout=20).returncode == 0,
             'guest-not-running')
        hold_fd9()
        try:
            preview_check(builder, 'running', CONFIG.read_bytes(), 'passed')
        finally:
            os.close(9)
    finally:
        if started:
            need(run('/usr/local/sbin/configctl', 'zapret', 'stop', timeout=90).returncode == 0,
                 'guest-stop-refused')
    print('P5B2B_NATIVE=' + json.dumps({
        'status': 'PASS_NATIVE_DETACHED_ORIGINAL_BUILD_NO_MUTATION',
        'scenarios': ['invalid-xml', 'missing-runtime', 'stopped',
                      'instrumented-cancel', 'running'],
        'owner-appliance': False, 'public-preview': False,
        'real-isp-dpi-bypass': False, 'owner-A11-A16': False,
    }, sort_keys=True))


def self_test():
    need(os.environ.get('ZAPRET2_P5B2B_DISPOSABLE_NATIVE') != '1',
         'no-native-optin-in-fast-mode')
    with tempfile.TemporaryDirectory(prefix='p5b2b-source-') as tmp:
        p = Path(tmp)
        need(tree(p) == (), 'empty-tree-bad')
        (p / 'test').write_text('one')
        original = tree(p)
        (p / 'test').write_text('two')
        need(original != tree(p), 'changed-data-not-detected')
    print('P5B2B_FAST=PASS')


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--self-test']:
            self_test()
        elif sys.argv[1:] == ['--native']:
            native()
        else:
            raise RuntimeError('explicit-self-test-or-native-required')
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print('P5B2B_NATIVE=REFUSED:' + str(error), file=sys.stderr)
        sys.exit(2)
