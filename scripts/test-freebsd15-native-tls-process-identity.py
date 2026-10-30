#!/usr/bin/env python3
"""Read-only kernel argv + existing native PID/start-time witness in disposable FreeBSD 15.1.

Never authorizes owner-appliance commands or claims packet-specific Lua selection.
"""
from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
MARKER = 'NATIVE_TLS_PROCESS_ARGV_IDENTITY'
GUARD = 'ZAPRET2_ISOLATED_FREEBSD_VM_WAN_PROCESS_TEST'
MAX_ARGV = 262144


class IdentityError(ValueError):
    pass


def decode_kernel_argv(raw: bytes) -> tuple[bytes, ...]:
    if not isinstance(raw, bytes) or not 3 <= len(raw) <= MAX_ARGV or raw[-1:] != b'\0':
        raise IdentityError('missing, oversized or truncated kernel argv')
    args = tuple(raw[:-1].split(b'\0'))
    if len(args) < 2 or any(not arg or b'\n' in arg or b'\r' in arg for arg in args):
        raise IdentityError('malformed kernel argv tokens')
    return args


def exact_argv(kernel_raw: bytes, expected: list[str]) -> str:
    if not isinstance(expected, list) or len(expected) < 2 or len(expected) > 4096:
        raise IdentityError('invalid expected executable argv')
    try:
        tokens = tuple(x.encode('utf-8') for x in expected)
    except (AttributeError, UnicodeError) as exc:
        raise IdentityError('invalid expected argument encoding') from exc
    if any(not x or b'\0' in x or b'\r' in x or b'\n' in x for x in tokens):
        raise IdentityError('invalid expected argument token')
    observed = decode_kernel_argv(kernel_raw)
    if observed != tokens:
        raise IdentityError('live kernel argv differs from expected exact vector')
    return hashlib.sha256(kernel_raw).hexdigest()


def static_test() -> None:
    expected = ['/tmp/native-dvtws2', '--port=989', '--lua-init=@/path/private.lua',
                '--new', '--filter-l7=tls', '--lua-desync=fake:blob=private']
    raw = b'\0'.join(s.encode() for s in expected) + b'\0'
    assert exact_argv(raw, expected) == hashlib.sha256(raw).hexdigest()
    negatives = (
        (raw[:-1], expected), (raw+b'\0', expected), (b'', expected),
        (raw.replace(b'--port=989',b'--port=990'), expected),
        (raw, expected[:-1]), (raw, expected+["--more=1"]),
        (raw, [expected[1], expected[0],*expected[2:]]),
        (b'/bin/sh\0-c\0'+raw, expected),
        (raw, [*expected[:-1],'--lua-desync=fake:blob=changed']),
        (raw, [*expected[:-1], 'bad\x00token']),
        (b'head\0\0tail\0', ['head','tail']),
        (raw, [*expected[:-1], 'bad\nnewline']),
    )
    for bad, desired in negatives:
        try:
            exact_argv(bad, desired)
        except IdentityError:
            pass
        else:
            raise AssertionError('kernel argv mismatch accepted')
    print('NATIVE_TLS_PROCESS_ARGV_STATIC=PASS: 12 exact-argv negative cases; no shell/ps string ambiguity')


def static_attest_test() -> None:
    """Prove the double-observation contract without a FreeBSD kernel."""
    expected = ['/tmp/dvtws2', '--filter-tcp=443']
    raw = b'\0'.join(x.encode() for x in expected) + b'\0'
    fixed = (('engine.pid', 30001, 'Fri Oct 30 20:00:00 2026'),
             ('supervisor.pid', 30002, 'Fri Oct 30 20:00:00 2026'))

    class Controller:
        def __init__(self, readings):
            self.readings = list(readings)
        def process_witness(self, *, pid_files):
            return self.readings.pop(0)

    original = globals()['kernel_args']
    try:
        globals()['kernel_args'] = lambda pid: raw
        report = attest(Controller([fixed, fixed]),
                        (Path('engine.pid'), Path('supervisor.pid')), expected)
        assert report['observations'] == 2 and not report['phase_b_permitted']
        assert report['packet_specific_lua_action'] == 'UNVERIFIED'
        replacement = (('engine.pid', 30101, 'Fri Oct 30 20:00:00 2026'), fixed[1])
        try:
            attest(Controller([fixed, replacement]),
                   (Path('engine.pid'), Path('supervisor.pid')), expected)
        except IdentityError:
            pass
        else:
            raise AssertionError('PID rollover witness accepted')
        readings = iter((raw, b'/tmp/dvtws2\0--filter-tcp=444\0'))
        globals()['kernel_args'] = lambda pid: next(readings)
        try:
            attest(Controller([fixed, fixed]),
                   (Path('engine.pid'), Path('supervisor.pid')), expected)
        except IdentityError:
            pass
        else:
            raise AssertionError('mid-observation kernel argv change accepted')
    finally:
        globals()['kernel_args'] = original
    print('NATIVE_TLS_PROCESS_ATTEST_STATIC=PASS: stable double-read; PID rollover/argv turnover rejected')


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('native companion missing: '+path.name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def kernel_args(pid: int) -> bytes:
    if type(pid) is not int or pid <= 1:
        raise IdentityError('invalid native engine PID')
    # FreeBSD's dynamic PID component is not a resolvable sysctl(8) name;
    # resolve its *parent* MIB, then append the numeric PID via libc sysctl(3).
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        mapper = libc.sysctlnametomib
        mapper.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int),
                           ctypes.POINTER(ctypes.c_size_t)]
        mapper.restype = ctypes.c_int
        parent = (ctypes.c_int * 16)()
        count = ctypes.c_size_t(len(parent))
        if mapper(b'kern.proc.args', parent, ctypes.byref(count)) != 0 or count.value != 3:
            raise IdentityError('native process args MIB unavailable')
        oid = (ctypes.c_int * 4)(parent[0], parent[1], parent[2], pid)
        reader = libc.sysctl
        reader.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint, ctypes.c_void_p,
                           ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p,
                           ctypes.c_size_t]
        reader.restype = ctypes.c_int
        buffer = (ctypes.c_ubyte * MAX_ARGV)()
        size = ctypes.c_size_t(MAX_ARGV)
        if reader(oid, 4, ctypes.cast(buffer, ctypes.c_void_p),
                  ctypes.byref(size), None, 0) != 0:
            raise IdentityError('native kernel argv read failed errno=' +
                                str(ctypes.get_errno()))
        if not 3 <= size.value <= MAX_ARGV:
            raise IdentityError('native kernel argv empty or oversized')
        return bytes(buffer[:size.value])
    except AttributeError as exc:
        raise IdentityError('native FreeBSD libc sysctl interface unavailable') from exc


def attest(controller, pidfiles: tuple[Path, Path], expected: list[str]) -> dict:
    """Read-only double observation: owner PID/time + exact argv, no selection claim."""
    first = controller.process_witness(pid_files=pidfiles)
    if len(first) != 2:
        raise IdentityError('native process owner incomplete')
    raw_first = kernel_args(first[0][1])
    digest = exact_argv(raw_first, expected)
    raw_second = kernel_args(first[0][1])
    last = controller.process_witness(pid_files=pidfiles)
    if first != last or raw_first != raw_second:
        raise IdentityError('native engine process generation changed during observation')
    return {'status':'NATIVE_PROCESS_ARGS_MATCH_ONLY', 'argv_sha256':digest,
            'observations':2, 'configured_profile_selected':'UNVERIFIED',
            'packet_specific_lua_action':'UNVERIFIED', 'installed_a07':'OPEN',
            'installed_a08':'OPEN', 'phase_b_permitted':False}


def native(engine: Path) -> None:
    gate = module('native_process_gate', HERE/'test-freebsd15-native-wan-process-continuity.py')
    gate.require_isolated_freebsd()
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise IdentityError('pinned upstream executable missing')
    controller = gate.production_controller()
    backend = HERE.parent/'src/opnsense/scripts/OPNsense/Zapret/backend'
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    fake = module('native_tls_fake_profile', HERE/'test-freebsd15-native-tls-fake.py')
    with tempfile.TemporaryDirectory(prefix='stage5-native-argv-') as folder:
        root = Path(folder)
        # dvtws2 may drop privilege before opening the temporary Lua resources.
        root.chmod(0o755)
        argv = [str(engine),*fake.compiled(root,engine.parent.parent,'baseline')]
        processes = []
        paths = (root/'engine.pid',root/'supervisor.pid')
        try:
            with (root/'engine.log').open('wb') as log:
                proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                        start_new_session=True)
                processes.append(proc)
                monitor = subprocess.Popen(['/bin/sleep','30'],stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL,start_new_session=True)
                processes.append(monitor)
                paths[0].write_text(str(proc.pid)+'\n',encoding='ascii')
                paths[1].write_text(str(monitor.pid)+'\n',encoding='ascii')
                time.sleep(.5)
                if proc.poll() is not None or monitor.poll() is not None:
                    raise IdentityError('native engine/monitor startup failed')
                proven = attest(controller,paths,argv)
                if (proven['status']!='NATIVE_PROCESS_ARGS_MATCH_ONLY' or
                        proven['packet_specific_lua_action']!='UNVERIFIED' or
                        proven['phase_b_permitted']):
                    raise IdentityError('misleading native process proof')
                for altered in (argv[:-1],argv+['--new'],
                                [*argv[:-1],'--lua-desync=drop'],
                                [argv[0],argv[2],argv[1],*argv[3:]]):
                    try:
                        attest(controller,paths,altered)
                    except IdentityError:
                        pass
                    else:
                        raise IdentityError('replaced or reordered expected argv accepted')
                controller.terminate(monitor)
                try:
                    attest(controller,paths,argv)
                except (controller.CaptureError,IdentityError):
                    pass
                else:
                    raise IdentityError('terminated monitor accepted')
                replacement = subprocess.Popen(['/bin/sleep','30'],stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL,start_new_session=True)
                processes.append(replacement)
                paths[1].write_text(str(replacement.pid)+'\n',encoding='ascii')
                if attest(controller,paths,argv)['status']!='NATIVE_PROCESS_ARGS_MATCH_ONLY':
                    raise IdentityError('replacement monitor not reattested')
                # Test stale owner engine identity, not a real installed restart.
                paths[0].write_text(str(monitor.pid)+'\n',encoding='ascii')
                try:
                    attest(controller,paths,argv)
                except (controller.CaptureError, IdentityError):
                    pass
                else:
                    raise IdentityError('stale engine PID accepted')
        finally:
            for proc in reversed(processes):
                controller.terminate(proc)
            if any(proc.poll() is None for proc in processes):
                raise IdentityError('native-owned test processes survived cleanup')


def main() -> int:
    if len(sys.argv)==2 and sys.argv[1]=='--static':
        static_test()
        static_attest_test()
        return 0
    if len(sys.argv)!=2:
        raise IdentityError('usage: --static or /pinned/dvtws2')
    static_test()
    static_attest_test()
    native(Path(sys.argv[1]).resolve())
    print(MARKER+'=PASS: FreeBSD15.1 real dvtws2 kernel NUL-argv equals exact expected profile; PID/start unchanged, stale/reordered refused, cleaned')
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,AssertionError) as exc:
        print(MARKER+'=FAIL: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
