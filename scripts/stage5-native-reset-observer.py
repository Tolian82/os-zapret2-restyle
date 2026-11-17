#!/usr/bin/env python3
"""Read-only, bounded Linux-host observation of one disposable AnyVM QEMU reset.

This module NEVER decides that a reboot succeeded; only the original strict
SSH kern.boottime check in stage5-native-hard-reset.py can authorize postboot.
Do not print serial bytes, SSH configuration, credentials, or guest addresses.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import socket
import stat
import subprocess

ANYVM_ACTION_ROOT = Path('/home/runner/work/_actions/vmactions/opnsense-vm')
MAX_SERIAL_DELTA = 128 * 1024


def qemu_argv(pid, proc_root=Path('/proc')):
    """Return exact live argv only for the existing snapshot AnyVM guest."""
    try:
        args = (proc_root / str(pid) / 'cmdline').read_bytes().split(b'\0')
        argv = [part.decode('utf-8') for part in args if part]
    except (OSError, UnicodeError):
        return []
    if (not argv or Path(argv[0]).name != 'qemu-system-x86_64' or
            '-snapshot' not in argv or
            not any('opnsense' in arg.lower() for arg in argv)):
        return []
    return argv


def serial_log_path(argv):
    """Discover existing chardev logfile; never add a new guest device."""
    if '-serial' not in argv or argv[argv.index('-serial') + 1:][:1] != ['chardev:serial0']:
        return None
    for i, arg in enumerate(argv[:-1]):
        if arg != '-chardev':
            continue
        parts = argv[i + 1].split(',')
        if 'id=serial0' not in parts or not parts[0] == 'socket':
            continue
        values = [part[8:] for part in parts if part.startswith('logfile=')]
        if len(values) != 1:
            continue
        path = Path(values[0])
        # Only the pinned AnyVM action's disposable output is acceptable.
        if (not path.is_absolute() or path.name.endswith('.serial.log') is False or
                ANYVM_ACTION_ROOT not in path.parents or
                'output' not in path.parts):
            continue
        return path
    return None


def safe_serial_size(path):
    if path is None:
        return None
    try:
        meta = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
        return None
    return meta.st_size


def serial_delta(path, baseline):
    """Output only booleans/counts; never disclose log text."""
    out = {'configured': path is not None, 'readable': False,
           'new_bytes': 0, 'truncated_since_baseline': False,
           'freebsd_kernel_signal': False, 'login_prompt_signal': False}
    size = safe_serial_size(path)
    if size is None or baseline is None:
        return out
    old = baseline if size >= baseline else 0
    out['truncated_since_baseline'] = size < baseline
    out['new_bytes'] = size - old
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            # Keep the newest bounded bytes if the console was chatty.
            stream.seek(max(old, size - MAX_SERIAL_DELTA))
            data = stream.read(MAX_SERIAL_DELTA)
    except OSError:
        return out
    out['readable'] = True
    out['freebsd_kernel_signal'] = bool(re.search(
        rb'(?:FreeBSD[/ ]|FreeBSD/amd64|Booting\s+from\s+|Loading\s+kernel|FreeBSD\s+is\s+a\s+registered)',
        data, flags=re.I))
    out['login_prompt_signal'] = bool(re.search(
        rb'(?:\blogin:\s|\bOPNsense\s+login:)', data, flags=re.I))
    return out


def ssh_forward_probe(timeout=2):
    """Read-only TCP/SSH-banner probe through existing SSH alias."""
    out = {'alias_loopback': False, 'tcp_accepts': False,
           'ssh_banner_seen': False}
    try:
        p = subprocess.run(['ssh', '-G', 'opnsense'], text=True,
                           capture_output=True, timeout=7, check=False)
        if p.returncode:
            return out
        entries = {}
        for line in p.stdout.splitlines():
            fields = line.split(None, 1)
            if len(fields) == 2 and fields[0] in ('hostname', 'port'):
                entries[fields[0]] = fields[1]
        host = entries.get('hostname', '')
        port = int(entries.get('port', '0'))
        if host not in ('localhost', '127.0.0.1', '::1') or not 1 <= port <= 65535:
            return out
        out['alias_loopback'] = True
        with socket.create_connection((host, port), timeout=timeout) as conn:
            out['tcp_accepts'] = True
            conn.settimeout(timeout)
            out['ssh_banner_seen'] = conn.recv(128).startswith(b'SSH-')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return out


def observe(pid, port, monitor_command, baseline_serial_size, serial_path):
    """Sanitized snapshot. Diagnostics cannot authorize a recovery step."""
    argv = qemu_argv(pid)
    out = {'same_snapshot_qemu_process': bool(argv),
           'hmp_responsive': False, 'hmp_running': False,
           'serial': serial_delta(serial_path, baseline_serial_size),
           'ssh_forward': ssh_forward_probe()}
    if argv:
        try:
            response = monitor_command(port, 'info status')
            out['hmp_responsive'] = '(qemu)' in response.lower() or 'VM status:' in response
            out['hmp_running'] = bool(re.search(
                r'\bVM status:\s*running\b', response, flags=re.I))
        except (OSError, TimeoutError, ValueError):
            pass
    return out
