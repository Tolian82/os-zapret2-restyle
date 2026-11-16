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
import time
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
    except BaseException:
        # A transiently busy original lifecycle lock must NOT leak fd=9
        # when the next test attempt retries the exact same native inode.
        os.close(fd)
        raise
    else:
        if fd != 9:
            os.close(fd)
    from voice_ipfw_adapter import require_lifecycle_lock
    try:
        require_lifecycle_lock()
    except BaseException:
        os.close(9)
        raise


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
$strategy="--filter-tcp=6545\\n--filter-l7=http\\n<HOSTLIST:youtube>\\n--payload=http_req\\n--lua-desync=multisplit:pos=method+2\\n";
if(!$m->setNodeByReference("general.enabled","1") ||
 !$m->setNodeByReference("general.waninterface","lo0") ||
 !$m->setNodeByReference("general.ports","6545") ||
 !$m->setNodeByReference("strategy.trafficargs",$strategy) ||
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
    hold_fd9()
    try:
        _, bad = preview_check(builder, 'invalid-xml', b'<opnsense/>')
        need(isinstance(bad, builder.PrivateBuildRefused) and
             bad.code == 'CANDIDATE_XML_MODEL_INVALID', 'invalid-xml-not-refused')
    finally:
        os.close(9)
    # The original shared Voice+Strategies builder requires a resolvable WAN
    # even when the current service is STOPPED. Prepare a valid lo0 model on
    # this disposable guest OUTSIDE each measured preview operation, so a
    # missing engine cannot be mistaken for a missing-WAN candidate failure.
    set_guest_lo0()
    hold_fd9()
    try:
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
    native_installed_auto_handoff()



def native_installed_auto_handoff():
    """One real installed native shared-Apply/FD9 observer on the same VM.

    This checks actual source→installed runtime, real process owner, the
    registered configd minute and explicit Stop/new-ID Boot. The synthetic
    raw/debug rollover has separate native filesystem evidence; an idle
    installed cycle MUST NOT be reported as an actual native discovery.
    """
    import base64
    import re
    import xml.etree.ElementTree as ET

    cli = '/usr/local/sbin/configctl'
    active = Path('/usr/local/etc/zapret2/runtime-v2')
    epochs = Path('/var/db/zapret2/auto-detect-epochs')
    pidfile = Path('/var/run/dvtws2.pid')

    def current_identity():
        mapped = active / 'auto-detect-generation.json'
        need(mapped.is_file() and not mapped.is_symlink(),
             'installed-auto-generation-map-absent')
        data = json.loads(mapped.read_text())
        generation = data.get('generation')
        need(isinstance(generation, str) and
             re.fullmatch('[0-9a-f]{32}', generation) is not None,
             'installed-auto-generation-invalid')
        need(pidfile.is_file() and not pidfile.is_symlink(),
             'installed-auto-pidfile-missing')
        match = re.match(r'([0-9]+)(?:\s|$)', pidfile.read_text().strip())
        need(match is not None and int(match.group(1)) > 1,
             'installed-auto-pid-invalid')
        pid = match.group(1)
        ps = run('/bin/ps', '-p', pid, '-o', 'lstart=', timeout=12)
        need(ps.returncode == 0 and ps.stdout.strip(),
             'installed-auto-real-engine-not-running')
        need(run(str(SERVICE), 'status', timeout=25).returncode == 0,
             'installed-auto-owner-status-not-running')
        return generation, pid, ps.stdout

    def minute(expected):
        response = run(cli, 'zapret', 'auto_detect_minute', timeout=85)
        need(response.returncode == 0 and
             f'auto-detect-minute={expected}'.encode() in response.stdout,
             'installed-auto-configd-minute-not-' + expected)

    old = ET.fromstring(CONFIG.read_bytes())
    tg = old.find('./OPNsense/Zapret/hostlist/telegramips')
    baseline = '' if tg is None or tg.text is None else tg.text
    request = {'page': 'strategies',
               'fields': {'hostlist': {'mode': 'auto'}},
               'sync': {'telegramips_baseline': baseline}}
    token = base64.urlsafe_b64encode(
        json.dumps(request, separators=(',', ':')).encode()).decode().rstrip('=')
    # This is the actual GUI/backend transaction; never set auto in XML
    # behind the one authoritative Config writer.
    prepared = run(cli, 'zapret', 'shared_apply', 'strategies', token, timeout=240)
    if prepared.returncode != 0 or b'applied-id=' not in prepared.stdout:
        # The real configd path has bounded phase receipts; preserve them
        # without exposing the request envelope or user traffic.
        def brief(blob):
            line = blob.decode('utf-8', errors='replace').replace('\n', ' ')
            return re.sub(r'[A-Za-z0-9_-]{48,}', '[REDACTED]', line)[:320]
        # On the PRE-JOURNAL runtime-preflight refusal only, execute the
        # exact production validators against the existing private candidate.
        # This never changes Config, firewall, dvtws2 or Auto-detect sources.
        diagnostic = ''
        if b'preflight-rejected=runtime-preflight' in prepared.stdout:
            work_root = Path('/var/db/zapret2/shared-work')
            qualified = []
            if work_root.is_dir() and not work_root.is_symlink():
                for entry in work_root.iterdir():
                    if (re.fullmatch('[0-9a-f]{32}', entry.name) and
                            entry.is_dir() and not entry.is_symlink() and
                            (entry / 'release/auto-detect-generation.json').is_file()):
                        qualified.append(entry / 'release')
            if len(qualified) == 1:
                candidate = qualified[0]
                validator = str(BACKEND / 'validator.sh')
                shell = ('common_error() { printf "%s\\n" "$*" >&2; }; '
                         '. "$1"; shift; "$@"')
                # The shell calls the production functions; no simulated
                # validator result and no second FD9 ownership claims.
                for label, function, arguments in (
                    ('modes', 'validator_validate_runtime_modes', [str(candidate)]),
                    ('engine', 'validator_validate_engine_mapped',
                     [str(ENGINE), str(candidate / 'dvtws.args'),
                      str(active), str(candidate),
                      '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh']),
                ):
                    command = run('/bin/sh', '-c', shell, 'native-p2-probe',
                                  validator, function, *arguments, timeout=24)
                    diagnostic += ':' + label + '-rc=' + str(command.returncode)
                    if command.returncode != 0:
                        diagnostic += ':' + label + '-reason=' + brief(
                            command.stderr or command.stdout)
                        break
                else:
                    # A release-authorize call requires genuine original
                    # FD9. Do not bypass that guard just to classify failure.
                    hold_fd9()
                    try:
                        auth = subprocess.run([
                            '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
                            str(BACKEND / 'auto_detect_post_drop.py'),
                            'authorize', str(candidate),
                        ], capture_output=True, timeout=20, pass_fds=(9,),
                            check=False)
                    finally:
                        os.close(9)
                    diagnostic += ':observer-authorize-rc=' + str(auth.returncode)
                    if auth.returncode != 0:
                        diagnostic += ':observer-authorize-reason=' + brief(
                            auth.stderr or auth.stdout)
                    else:
                        # The remaining runtime probe only checks previous
                        # process/supervisor and exact shared IPFW ownership.
                        # Inspect those states, never mutate firewall rules.
                        processes = run('/bin/ps', 'ax', '-o', 'pid=', '-o',
                                        'command=', timeout=12)
                        if processes.returncode == 0:
                            census = [line for line in
                                      processes.stdout.decode(errors='replace').splitlines()
                                      if len(line.split()) >= 2 and
                                      line.split()[1] == str(ENGINE)]
                            diagnostic += ':engine-census-count=' + str(len(census))
                        else:
                            diagnostic += ':ps-rc=' + str(processes.returncode)
                        for marker, item in (
                            ('engine-pidfile', Path('/var/run/dvtws2.pid')),
                            ('supervisor-pidfile',
                             Path('/var/run/zapret2-supervisor-monitor.pid')),
                        ):
                            diagnostic += ':' + marker + '-present=' + str(
                                item.is_file() and not item.is_symlink())
                        kernel = run('/sbin/kldstat', '-q', '-m', 'ipfw', timeout=12)
                        diagnostic += ':ipfw-kernel-rc=' + str(kernel.returncode)
                        hold_fd9()
                        try:
                            fw = subprocess.run([
                                '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
                                str(BACKEND / 'voice_ipfw_adapter.py'),
                                'shared', 'verify', str(candidate), '-',
                            ], capture_output=True, timeout=25,
                                pass_fds=(9,), check=False)
                        finally:
                            os.close(9)
                        diagnostic += ':firewall-verify-rc=' + str(fw.returncode)
                        if fw.returncode != 0:
                            diagnostic += ':firewall-reason=' + brief(
                                fw.stderr or fw.stdout)
            else:
                diagnostic = ':candidate-count=' + str(len(qualified))
        if b'Execute error' in prepared.stdout:
            # The first real Apply may already have changed the engine,
            # Config or journal. Never retry/recover it speculatively here.
            # Record ONLY fixed structural statuses, no argv/domains/IDs.
            state = {'journal': 'absent', 'epoch': 'not-attributable'}
            journal = Path('/var/db/zapret2/shared-apply/operation.json')
            try:
                if journal.exists() or journal.is_symlink():
                    info = journal.lstat()
                    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
                            info.st_mode & 0o077 or info.st_size > 8192):
                        state['journal'] = 'unsafe'
                    else:
                        document = json.loads(journal.read_bytes())
                        stage = document.get('phase')
                        state['journal'] = (stage if stage in {
                            'prepared', 'activating', 'activated',
                            'config-saved', 'epoch-finalizing', 'committed',
                            'restored', 'restore-failed', 'requires-review',
                        } else 'invalid')
                        entry = document.get('detail')
                        identity = entry.get('id') if isinstance(entry, dict) else None
                        if isinstance(identity, str) and re.fullmatch('[0-9a-f]{32}', identity):
                            gen = epochs / identity
                            state['epoch'] = {
                                'pretraffic': (gen / 'pretraffic.json').is_file(),
                                'running': (gen / 'epoch.json').is_file(),
                                'retired': (gen / 'retired.json').is_file(),
                            }
                            state['candidate_release_present'] = (
                                Path('/var/db/zapret2/shared-work') /
                                identity / 'release').is_dir()
            except (OSError, ValueError, TypeError):
                state['journal'] = 'unreadable'
            state['live_generation_present'] = (
                active / 'auto-detect-generation.json').is_file()
            state['engine_pidfile_present'] = pidfile.is_file()
            state['supervisor_pidfile_present'] = Path(
                '/var/run/zapret2-supervisor-monitor.pid').is_file()
            state['producer_raw_present'] = Path(
                '/var/db/zapret2-auto-detect/inbox.txt').is_file()
            state['producer_debug_present'] = Path(
                '/var/db/zapret2-auto-detect/debug.log').is_file()
            try:
                current = ET.fromstring(CONFIG.read_bytes())
                mode_node = current.find('./OPNsense/Zapret/hostlist/mode')
                state['config_saved_auto'] = (
                    mode_node is not None and mode_node.text == 'auto')
            except (OSError, ET.ParseError):
                state['config_saved_auto'] = 'unreadable'
            if (state['journal'] == 'requires-review' and
                    state['live_generation_present']):
                # Post-error read-only comparison against the SAME exact
                # process token grammar as the original native P2c owner.
                # Report boolean results only: process argv stays private.
                try:
                    from auto_detect_owner import _snapshot as process_snapshot
                    child_pid = int(pidfile.read_text('ascii').strip())
                    monitor_pid = int(Path(
                        '/var/run/zapret2-supervisor-monitor.pid'
                    ).read_text('ascii').strip())
                    _, child_argv = process_snapshot(subprocess.run, child_pid)
                    _, monitor_argv = process_snapshot(subprocess.run, monitor_pid)
                    installed_argv = (active / 'dvtws.args').read_text().split()
                    state['engine_exact_native_argv'] = (
                        child_argv == [str(ENGINE), *installed_argv,
                                       '--sockarg=0x200', '--user=nobody'])
                    supervisor = str(SERVICE.parent / 'supervisor_loop.sh')
                    state['monitor_first_token_exact'] = bool(
                        monitor_argv and monitor_argv[0] == supervisor)
                    state['monitor_script_in_argv'] = (
                        supervisor in monitor_argv)
                    census = subprocess.run([
                        '/bin/ps', '-A', '-ww', '-o', 'pid=', '-o', 'command=',
                    ], capture_output=True, text=True, timeout=8, check=False)
                    if census.returncode == 0:
                        state['exact_engine_process_count'] = sum(
                            1 for line in census.stdout.splitlines()
                            if len(line.split()) >= 2 and
                            line.split()[1] == str(ENGINE))
                    entry = document.get('detail', {})
                    if isinstance(entry, dict):
                        name = entry.get('id', '')
                        if isinstance(name, str) and re.fullmatch('[0-9a-f]{32}', name):
                            plan = json.loads((Path('/var/db/zapret2/shared-work') /
                                               name / 'plan.json').read_bytes())
                            state['original_plan_matches_owner'] = (
                                isinstance(plan, dict) and
                                plan.get('dependencies') == entry.get('base') and
                                plan.get('changed_fields') == entry.get('changed_fields'))
                except (OSError, ValueError, TypeError,
                        subprocess.TimeoutExpired, RuntimeError) as error:
                    state['native_process_snapshot'] = type(error).__name__
                # The existing native firewall adapter's verify action is
                # strictly read-only. Capture only status, not rules/hosts.
                try:
                    hold_fd9()
                    try:
                        end = subprocess.run([
                            '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
                            str(BACKEND / 'voice_ipfw_adapter.py'),
                            'shared', 'verify', '-', str(active),
                        ], capture_output=True, timeout=25,
                            pass_fds=(9,), check=False)
                        state['final_ipfw_rc'] = end.returncode
                    finally:
                        os.close(9)
                except (OSError, subprocess.TimeoutExpired, RuntimeError):
                    state['final_ipfw_rc'] = 'unavailable'
                # Read only a bounded disposable-VM log suffix; emit a
                # fixed set of known diagnostic classifications, NEVER the
                # log text (which may contain private Config or argv).
                log = Path('/var/log/configd/latest.log')
                if log.is_file() and not log.is_symlink():
                    try:
                        with log.open('rb') as stream:
                            stream.seek(0, os.SEEK_END)
                            stream.seek(max(0, stream.tell() - 65536))
                            tail = stream.read(65536)
                        markers = {
                            'epoch-completion-refused':
                                b'shared Apply: original epoch completion refused',
                            'epoch-completion-unverified':
                                b'shared Apply: original epoch completion unverified',
                            'engine-process-census':
                                b'shared Apply: unexpected or untracked dvtws2 process',
                            'restore-failed': b'RESTORE_FAILED',
                        }
                        state['native_error_markers'] = sorted(
                            name for name, phrase in markers.items()
                            if phrase in tail)
                        match = re.search(
                            rb'original-fd9-postdrop-refused=([A-Za-z]{1,48})',
                            tail)
                        if match:
                            state['postdrop_exception_class'] = (
                                match.group(1).decode('ascii'))
                    except (OSError, ValueError):
                        state['native_error_markers'] = 'unavailable'
            print('P2_INSTALLED_ORIGINAL_FAILURE_STATE=' +
                  json.dumps(state, sort_keys=True), flush=True)
        need(False, 'installed-original-auto-shared-apply-refused:' +
             'rc=' + str(prepared.returncode) + ':stdout=' +
             brief(prepared.stdout) + ':stderr=' + brief(prepared.stderr) +
             diagnostic)
    running = True
    try:
        saved = ET.fromstring(CONFIG.read_bytes())
        mode = saved.find('./OPNsense/Zapret/hostlist/mode')
        need(mode is not None and mode.text == 'auto',
             'installed-auto-mode-not-saved-by-native-config')
        original_config = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        first_gen, first_pid, first_birth = current_identity()
        for _ in range(3):
            minute('idle')
            need(current_identity() == (first_gen, first_pid, first_birth),
                 'minute-restarted-installed-original-engine')
        # Read only the exact saved native preference under the original
        # lifecycle FD9. Do not risk executing a scheduled restart if the
        # disposable saved model is unexpectedly opted in.
        hold_fd9()
        try:
            preference = subprocess.run([
                '/usr/local/bin/php', str(SERVICE.parent / 'shared_apply_config.php'),
                'auto-restart',
            ], capture_output=True, timeout=25, pass_fds=(9,), check=False)
        finally:
            os.close(9)
        raw_preference = preference.stdout.strip()
        pref_label = (raw_preference.decode('ascii')
                      if raw_preference in {b'0:off', b'1:off',
                                            b'1:hourly', b'1:daily',
                                            b'1:weekly', b'1:monthly'}
                      else 'unqualified')
        saved_model = ET.fromstring(CONFIG.read_bytes())
        saved_setting = saved_model.find('./OPNsense/Zapret/general/autorestart')
        model_label = ('missing' if saved_setting is None else
                       saved_setting.text if saved_setting.text in {
                           'off', 'hourly', 'daily', 'weekly', 'monthly'
                       } else 'unqualified')
        print('P2_INSTALLED_AUTORESTART_PREF=' + json.dumps({
            'native_preference_rc': preference.returncode,
            'native_preference': pref_label,
            'saved_field': model_label,
        }, sort_keys=True), flush=True)
        if preference.returncode != 0:
            # This is an installed *read-only* exact failure classification:
            # no Config mutation, no domain/argv leakage, and no tick call.
            php_probe = r'''require_once('/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php');
$phase='uid';
try {
  if (\OPNsense\Zapret\Native\SharedApplyLifecycleLock::effectiveUid() !== 0) throw new \RuntimeException('uid');
  $phase='fd9';
  \OPNsense\Zapret\Native\SharedApplyLifecycleLock::assertHeld();
  $phase='framework';
  require_once('script/load_phalcon.php');
  $phase='config-lock';
  $c=\OPNsense\Core\Config::getInstance(); $c->lock();
  try {
    $phase='model';
    $m=new \OPNsense\Zapret\Zapret(); $nodes=$m->getNodes();
    $g=$nodes['general']??null;
    if (!is_array($g)) throw new \RuntimeException('invalid-general');
    $e=$g['enabled']??null;
    $a=$g['autorestart']??null;
    $enabled=($e==='1'?'1':($e==='0'?'0':'unqualified'));
    $auto=($a===null?'missing':($a===''?'empty':
      (in_array($a,['off','hourly','daily','weekly','monthly'],true)?$a:'unqualified')));
  } finally { $c->unlock(); }
  echo 'ok:'.$enabled.':'.$auto;
} catch (\Throwable $error) {
  echo 'refused:'.$phase;
}'''
            hold_fd9()
            try:
                probe = subprocess.run(['/usr/local/bin/php', '-r', php_probe],
                                       capture_output=True, timeout=25,
                                       pass_fds=(9,), check=False)
            finally:
                os.close(9)
            reply = probe.stdout.strip().decode('ascii', errors='replace')
            allowed = ({'ok:1:' + x for x in
                        ('missing', 'empty', 'off', 'hourly', 'daily',
                         'weekly', 'monthly', 'unqualified')} |
                       {'ok:0:' + x for x in
                        ('missing', 'empty', 'off', 'hourly', 'daily',
                         'weekly', 'monthly', 'unqualified')} |
                       {'refused:' + x for x in
                        ('uid', 'fd9', 'framework', 'config-lock', 'model')})
            print('P2_INSTALLED_AUTORESTART_PROBE=' + json.dumps({
                'rc': probe.returncode,
                'stage': reply if reply in allowed else 'unqualified',
            }, sort_keys=True), flush=True)
        need(preference.returncode == 0 and pref_label == '1:off',
             'default-off-native-preference-refused')
        tick = run(cli, 'zapret', 'auto_restart_tick', 'hourly', timeout=80)
        tick_label = (
            'disabled' if b'auto-restart=disabled' in tick.stdout else
            'inactive' if b'auto-restart=inactive' in tick.stdout else
            'not-due' if b'auto-restart=not-due' in tick.stdout else
            'stopped' if b'auto-restart=stopped' in tick.stdout else
            'execute-error' if b'Execute error' in tick.stdout else
            'other')
        print('P2_INSTALLED_AUTORESTART_TICK=' + json.dumps({
            'configctl_rc': tick.returncode, 'receipt': tick_label,
            'stderr_present': bool(tick.stderr),
        }, sort_keys=True), flush=True)
        need(tick.returncode == 0 and tick_label == 'disabled',
             'default-off-auto-restart-not-enforced')
        need(current_identity() == (first_gen, first_pid, first_birth),
             'off-restart-changed-engine')
        # This is an EXPLICIT Stop, not minute maintenance. After verified
        # old archive/ACK the normal common Boot must allocate a distinct ID.
        stopped = run(cli, 'zapret', 'stop', timeout=150)
        # The disposable test must never issue a second blind Stop after an
        # ambiguous first transaction; its VM is discarded on failure.
        running = False
        stop_receipt = (
            'execute-error' if b'Execute error' in stopped.stdout else
            'native-stopped' if b'native-common-stopped=' in stopped.stdout else
            'ok' if stopped.stdout.strip() == b'OK' else 'unqualified')
        retired = epochs / first_gen / 'retired.json'
        retired_present = retired.is_file() and not retired.is_symlink()
        stopped_diagnostic = {
            'configctl_rc': stopped.returncode,
            'receipt': stop_receipt,
            'stdout_length': len(stopped.stdout),
            'retired_present': retired_present,
            'engine_pidfile_present': pidfile.is_file(),
            'monitor_pidfile_present': Path(
                '/var/run/zapret2-supervisor-monitor.pid').is_file(),
            'active_observer_present': (
                active / 'auto-detect-generation.json').is_file(),
            'stderr_present': bool(stopped.stderr),
        }
        if (not pidfile.is_file() and not Path(
                '/var/run/zapret2-supervisor-monitor.pid').is_file()):
            # One read-only check of the exact common stopped IPFW state,
            # never repair/flush/retry the user's stopped original owner.
            try:
                hold_fd9()
                try:
                    stopped_fw = subprocess.run([
                        '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
                        str(BACKEND / 'voice_ipfw_adapter.py'),
                        'shared', 'verify', str(active), '-',
                    ], capture_output=True, timeout=25,
                        pass_fds=(9,), check=False)
                    stopped_diagnostic['stopped_ipfw_rc'] = stopped_fw.returncode
                finally:
                    os.close(9)
            except (OSError, subprocess.TimeoutExpired, RuntimeError):
                stopped_diagnostic['stopped_ipfw_rc'] = 'unavailable'
            stopped_diagnostic['pretraffic_present'] = (
                epochs / first_gen / 'pretraffic.json').is_file()
            stopped_diagnostic['epoch_present'] = (
                epochs / first_gen / 'epoch.json').is_file()
            # Strict *read-only* post-Stop owner and cursor evidence, using
            # the original physical FD9. Do NOT invoke retire-once, ACK or
            # the source-rotation mutators from the diagnostics.
            try:
                hold_fd9()
                try:
                    from auto_detect_owner import attest_stopped_generation
                    from auto_detect_cursor_chain import CursorChain
                    from auto_detect_queue import DurableInbox
                    from auto_detect_epoch_receipts import EpochReceipts
                    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
                    import pwd
                    try:
                        proof = attest_stopped_generation()
                        stopped_diagnostic['stopped_owner'] = 'attested'
                        gid = pwd.getpwnam(ENGINE_USER).pw_gid
                        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
                        # Existing original minute already created its
                        # queue lock. Refuse a missing lock to avoid creating
                        # or repairing any protected file in diagnosis.
                        if not queue.lock.is_file() or queue.lock.is_symlink():
                            raise RuntimeError('original_queue_lock_missing')
                        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
                        with queue.exclusive():
                            tip = CursorChain(receipts, queue).tip(proof)
                            stopped_diagnostic['pending_count'] = len(queue.segments())
                            stopped_diagnostic['cursor_open_intent'] = (
                                tip.open_intent is not None)
                            stopped_diagnostic['cursor_open_folder'] = (
                                tip.open_folder is not None)
                            stopped_diagnostic['raw_bytes'] = queue.inbox.stat().st_size
                            stopped_diagnostic['debug_bytes'] = Path(
                                proof.debug_path).stat().st_size
                    except (OSError, ValueError, TypeError, RuntimeError,
                            KeyError) as error:
                        stopped_diagnostic['stopped_owner'] = 'refused'
                        # Internal machine-only error slugs are safe; never
                        # print exception text containing private input.
                        reasons = []
                        current = error
                        for _ in range(4):
                            if current is None:
                                break
                            reason = str(current)
                            reasons.append({
                                'class': type(current).__name__[:48],
                                'code': (reason if re.fullmatch(
                                    '[a-z][a-z0-9_]{2,79}', reason)
                                    else 'unqualified'),
                            })
                            current = current.__cause__
                        stopped_diagnostic['retire_readonly_refusal'] = reasons
                finally:
                    os.close(9)
            except (OSError, ValueError, RuntimeError) as error:
                stopped_diagnostic['stopped_owner'] = 'probe-unavailable'
            try:
                log = Path('/var/log/configd/latest.log')
                if log.is_file() and not log.is_symlink():
                    with log.open('rb') as stream:
                        stream.seek(0, os.SEEK_END)
                        stream.seek(max(0, stream.tell() - 65536))
                        tail = stream.read(65536)
                    stopped_diagnostic['retire_refusal_class'] = next((
                        name for name in ('ReceiptRefused', 'GenerationRefused',
                                          'MinuteRefused', 'OriginalLockRefused',
                                          'RuntimeError', 'OSError', 'ValueError',
                                          'KeyError')
                        if (b'auto-detect-retire-refused=' + name.encode()) in tail
                    ), 'not-in-log')
            except OSError:
                stopped_diagnostic['retire_refusal_class'] = 'unavailable'
        print('P2_INSTALLED_ORIGINAL_STOP=' +
              json.dumps(stopped_diagnostic, sort_keys=True), flush=True)
        need(stopped.returncode == 0 and stop_receipt in {'ok', 'native-stopped'},
             'original-auto-explicit-stop-refused:' + stop_receipt)
        need(retired_present, 'old-installed-original-epoch-not-retired')
        need(hashlib.sha256(CONFIG.read_bytes()).hexdigest() == original_config,
             'stop-mutated-manual-model')
        boot = run(cli, 'zapret', 'start', timeout=240)
        need(boot.returncode == 0, 'original-auto-new-id-boot-refused')
        running = True
        second_gen, second_pid, second_birth = current_identity()
        need(second_gen != first_gen,
             'stopped-original-observer-reused-old-operation-id')
        minute('idle')
        need(current_identity() == (second_gen, second_pid, second_birth),
             'new-observer-minute-restarted-engine')
        need(hashlib.sha256(CONFIG.read_bytes()).hexdigest() == original_config,
             'new-id-boot-mutated-saved-manual-model')
        # Reuse the already-qualified P0 real FreeBSD loopback HTTP/RST
        # client against THIS installed service's original IPFW/FD9 owner.
        # All changes remain disposable-VM-only; no raw/debug forgery.
        import pwd
        from auto_detect_storage import RAW_PATH, DEBUG_PATH, ROOT as QUEUE_ROOT, ENGINE_USER
        from auto_detect_owner import attest_running_generation
        from auto_detect_cursor_chain import CursorChain
        from auto_detect_queue import DurableInbox
        from auto_detect_epoch_receipts import EpochReceipts
        test_port = 6545
        testcase = importlib.util.spec_from_file_location(
            'p5b2b_real_http_client', ROOT / 'scripts/test-p0-native-auto-observer.py')
        need(testcase is not None and testcase.loader is not None,
             'native-p0-traffic-client-unavailable')
        client = importlib.util.module_from_spec(testcase)
        testcase.loader.exec_module(client)
        synthetic_host = 'native-observer-p5b2b.example.org'
        need(RAW_PATH.is_file() and RAW_PATH.read_bytes() == b'',
             'native-source-not-idle-before-positive')
        def scoped_counters():
            reply = run('/sbin/ipfw', '-a', 'list', timeout=18)
            if reply.returncode != 0 or len(reply.stdout) > 1048576:
                return None, False
            counters = {}
            port_seen = False
            for line in reply.stdout.decode('utf-8', 'replace').splitlines():
                found = re.match(r'^\s*0*([0-9]+)\s+([0-9]+)\s+', line)
                if found and 19000 <= int(found[1]) <= 19010:
                    counters[int(found[1])] = int(found[2])
                    if '6545' in line and 'lo0' in line:
                        port_seen = True
            return counters, port_seen
        before_packets, _ = scoped_counters()

        need(client.exchange(synthetic_host, port=test_port, force_rst=True)
             == client.request(synthetic_host),
             'native-unknown-http-forwarding-failed')
        for _ in range(12):
            if RAW_PATH.read_text().splitlines() == [synthetic_host]:
                break
            time.sleep(.25)
        after_packets, scope_port_seen = scoped_counters()
        compiled = (active / 'dvtws.args').read_text()
        observed_raw = RAW_PATH.read_text().splitlines()
        observed_debug = DEBUG_PATH.read_text()
        packet_changed = (before_packets is not None and after_packets is not None and
                          any(after_packets.get(i, 0) > n for i, n in before_packets.items()))
        print('P2_INSTALLED_NATIVE_HTTP_SCOPE=' + json.dumps({
            'exact_known_tcp_profile': compiled.count('--filter-tcp=6545') >= 1,
            'native_auto_present': '--hostlist-auto=' in compiled,
            'observer_http_l7': '--filter-l7=http' in compiled,
            'scoped_ipfw_rule_has_lo0_test_port': scope_port_seen,
            'scoped_ipfw_packet_counter_changed': packet_changed,
            'scoped_rule_count': len(after_packets or {}),
            'raw_event_count': len(observed_raw),
            'debug_mentions_test_host': synthetic_host in observed_debug,
            'debug_has_profile_search': 'desync profile search' in observed_debug,
            'engine_identity_stable': current_identity() == (
                second_gen, second_pid, second_birth),
        }, sort_keys=True), flush=True)
        need(RAW_PATH.read_text().splitlines() == [synthetic_host],
             'native-unknown-raw-append-not-observed')
        old_map = json.loads((active / 'auto-detect-generation.json').read_bytes())
        number = old_map.get('observer_native_number')
        need(type(number) is int and number > 0,
             'native-observer-ordinal-unavailable')
        positive = [line for line in DEBUG_PATH.read_text().splitlines()
                    if synthetic_host in line and ' : adding to ' in line]
        need(len(positive) == 1 and
             f' : profile {number} (' in positive[0] and
             str(RAW_PATH) in positive[0],
             'native-profile-debug-source-correlation-missing')
        minute('processed')
        need(current_identity() == (second_gen, second_pid, second_birth),
             'native-positive-minute-restarted-engine')
        final_hosts = Path('/usr/local/etc/zapret2/ipset/auto-domains.txt')
        need(final_hosts.is_file() and not final_hosts.is_symlink() and
             'example.org' in final_hosts.read_text().splitlines(),
             'native-real-unknown-destination-not-committed')
        need(RAW_PATH.read_bytes() == b'',
             'native-processed-producer-not-rotated')
        hold_fd9()
        try:
            proof = attest_running_generation()
            need(proof.generation == second_gen, 'positive-ack-owner-changed')
            gid = pwd.getpwnam(ENGINE_USER).pw_gid
            queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
            with queue.exclusive():
                tip = CursorChain(EpochReceipts(owner_uid=0, writer_gid=gid),
                                  queue).tip(proof)
                need(tip.next_sequence >= 1 and
                     tip.open_intent is None and tip.open_folder is None and
                     not queue.segments(),
                     'native-positive-physical-ack-not-verified')
        finally:
            os.close(9)
        need(client.exchange(synthetic_host, port=test_port, force_rst=False)
             == client.request(synthetic_host),
             'native-known-after-ack-http-forwarding-failed')
        need(current_identity() == (second_gen, second_pid, second_birth) and
             hashlib.sha256(CONFIG.read_bytes()).hexdigest() == original_config,
             'native-positive-minute-changed-engine-or-manual-config')
        print('P2_INSTALLED_NATIVE_DISCOVERY=' + json.dumps({
            'result': 'PASS_NATIVE_UNKNOWN_HTTP_CONFIG_P1_PHYSICAL_ACK',
            'real_loopback_rst': True,
            'native_observer_profile_debug_correlated': True,
            'registrable_root_destination': True,
            'native_physical_ack': True,
            'pid_birth_unchanged': True,
            'manual_config_unchanged': True,
            'owner_appliance': False,
            'public_internet_dpi': False,
        }, sort_keys=True), flush=True)
        print('P2_INSTALLED_ORIGINAL_AUTO=' + json.dumps({
            'result': 'PASS_NATIVE_IDLE_MINUTE_STOP_NEW_ID_BOOT',
            'observed_minute_ticks': 5,
            'explicit_stop': True,
            'old_epoch_retired': True,
            'distinct_boot_generation': True,
            'default_auto_restart_off': True,
            'saved_config_unchanged_during_stop_boot': True,
            'native_discovery_traffic': True,
            'owner_appliance': False,
        }, sort_keys=True))
    finally:
        if running:
            final = run(cli, 'zapret', 'stop', timeout=150)
            # On an earlier failure second_gen may never have been created.
            # Do not mask the original reason with UnboundLocalError.
            stopped_generation = locals().get('second_gen', locals().get('first_gen'))
            retirement_ok = (stopped_generation is None or
                             (epochs / stopped_generation / 'retired.json').is_file())
            need(final.returncode == 0 and
                 b'Execute error' not in final.stdout and retirement_ok,
                 'installed-auto-final-generation-not-retired')


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
