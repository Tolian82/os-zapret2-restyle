#!/usr/bin/env python3
"""Read-only STOPPED predecessor screening beneath the historical original FD9.

This is deliberately NOT old-owner admission or a pkg transaction gate.
The former installed package is verified against the exact supplied native
archive. No Status/Stop is invoked recursively while FD9 is held.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

try:
    from . import native_pkg_handoff
except ImportError:
    import native_pkg_handoff

NAME = 'os-zapret2-restyle'
SERVICE = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh')
CONFIG = Path('/conf/config.xml')
MARKERS = (
    Path('/var/db/zapret2/shared-apply'),
    Path('/var/run/zapret2-restyle/pkg-upgrade.restart'),
    Path('/var/run/zapret2-restyle/pkg-replacement.restart'),
    Path('/var/db/zapret2-restyle/extra-resources/transaction'),
    Path('/var/run/dvtws2.pid'),
    Path('/var/run/zapret2-supervisor-daemon.pid'),
    Path('/var/run/zapret2-supervisor-monitor.pid'),
)
PHASES = frozenset(('pre-install', 'post-install', 'pre-deinstall', 'post-deinstall'))
PROCESS_TOKENS = ('/dvtws2', '/supervisor_loop.sh', '/zapret_service.sh')


class OwnerRefusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise OwnerRefusal(reason)


def read_command(argv, *, allowed=(0,), timeout=12):
    """Only fixed read operations: no pkg add/upgrade, service, or IPFW writes."""
    try:
        p = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        raise OwnerRefusal('OLD_READ_ONLY_QUERY_UNAVAILABLE:' + argv[0]) from None
    require(p.returncode in allowed, 'OLD_READ_ONLY_QUERY_REFUSED:' + argv[0])
    return p


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_root_bytes(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise OwnerRefusal('OLD_OWNED_FILE_UNAVAILABLE:' + str(path)) from None
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and
                before.st_nlink == 1 and not (stat.S_IMODE(before.st_mode) & 0o022),
                'OLD_OWNED_FILE_UNTRUSTED:' + str(path) +
                ':uid=' + str(before.st_uid) +
                ':links=' + str(before.st_nlink) +
                ':mode=' + format(stat.S_IMODE(before.st_mode), '04o'))
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
        current = path.lstat()
        require((before.st_dev, before.st_ino, before.st_mtime_ns,
                 before.st_ctime_ns, before.st_size) ==
                (after.st_dev, after.st_ino, after.st_mtime_ns,
                 after.st_ctime_ns, after.st_size) and
                (current.st_dev, current.st_ino) == (after.st_dev, after.st_ino),
                'OLD_OWNED_FILE_CHANGED:' + str(path))
        return b''.join(chunks), stat.S_IMODE(after.st_mode)
    finally:
        os.close(fd)


def installed_manifest(raw):
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError, TypeError):
        raise OwnerRefusal('OLD_PKGDB_INVALID_JSON') from None
    if isinstance(data, list):
        require(len(data) == 1, 'OLD_PKGDB_NOT_EXACTLY_ONE_PACKAGE')
        data = data[0]
    require(isinstance(data, dict), 'OLD_PKGDB_NOT_OBJECT')
    return data


def check_four_hooks(archive, installed, version):
    """The archived hooks, not incoming code, are the old hook authority."""
    try:
        archived = json.loads(read_command(
            ['/usr/bin/tar', '-xOf', str(archive), '+MANIFEST']).stdout)
    except (ValueError, UnicodeError):
        raise OwnerRefusal('OLD_ARCHIVE_MANIFEST_INVALID') from None
    for source, data in (('OLD_ARCHIVE', archived), ('OLD_INSTALLED', installed)):
        require(isinstance(data, dict) and data.get('name') == NAME and
                data.get('version') == version,
                source + '_PACKAGE_IDENTITY_MISMATCH')
        hooks = data.get('scripts')
        require(isinstance(hooks, dict) and set(hooks) == PHASES and
                all(isinstance(hooks[p], str) and
                    hooks[p].startswith('#!/bin/sh\n') for p in PHASES),
                source + '_HOOKS_UNQUALIFIED')
    for field in ('arch', 'origin'):
        require(isinstance(archived.get(field), str) and archived[field] and
                archived[field] == installed.get(field),
                'OLD_PKGDB_' + field.upper() + '_MISMATCH')
    require(installed.get('abi') in (None, archived.get('abi')),
            'OLD_PKGDB_ABI_MISMATCH')
    require(all(installed['scripts'][p] == archived['scripts'][p] for p in PHASES),
            'OLD_INSTALLED_HOOK_BODY_MISMATCH')
    entries = read_command(['/usr/bin/tar', '-tf', str(archive)]).stdout.decode().splitlines()
    paths = [entry for entry in entries if entry.lstrip('./') == str(SERVICE).lstrip('/')]
    require(len(paths) == 1, 'OLD_ARCHIVED_SERVICE_ABSENT_OR_AMBIGUOUS')
    return read_command(['/usr/bin/tar', '-xOf', str(archive), paths[0]]).stdout


def cold_screen():
    for path in MARKERS:
        require(not path.exists() and not path.is_symlink(),
                'OLD_JOURNAL_MARKER_OR_PIDFILE_PRESENT:' + str(path))
    processes = read_command(['/bin/ps', '-ax', '-o', 'command=']).stdout.decode()
    require(not any(token in line for token in PROCESS_TOKENS
                    for line in processes.splitlines()), 'OLD_PROCESS_OR_UNKNOWN_OWNER_PRESENT')
    ipfw = read_command(['/sbin/kldstat', '-q', '-m', 'ipfw'], allowed=(0, 1))
    ipdivert = read_command(['/sbin/kldstat', '-q', '-m', 'ipdivert'], allowed=(0, 1))
    require(ipfw.returncode == ipdivert.returncode == 1,
            'OLD_KERNEL_IPFW_OR_IPDIVERT_NOT_PROVEN_COLD')
    rules = read_command(['/sbin/ipfw', '-q', 'list'], allowed=(71,))
    require(b'Protocol not available' in rules.stdout + rules.stderr,
            'OLD_IPFW_UNLOADED_EVIDENCE_MISSING')
    return 'COLD_NO_JOURNAL_PROCESS_OR_LOADED_IPFW'


def inspect_stopped(archive, version, original_fd9_inode):
    """A bounded witness ONLY. Not safe to dispatch pkg after this returns."""
    native_pkg_handoff.verify_original_lock(9, original_fd9_inode)
    require(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
            os.uname().machine == 'amd64', 'OLD_ROOT_FREEBSD_REQUIRED')
    pkg_args = ['/usr/sbin/pkg', 'info', '-R', '--raw-format', 'json', NAME]
    pkg_before = read_command(pkg_args).stdout
    installed = installed_manifest(pkg_before)
    old_service_archive = check_four_hooks(archive, installed, version)
    service, mode = regular_root_bytes(SERVICE)
    require(mode == 0o755 and service == old_service_archive,
            'OLD_INSTALLED_SERVICE_BYTES_OR_MODE_MISMATCH')
    owner = read_command(['/usr/sbin/pkg', 'which', '-q', str(SERVICE)]).stdout.decode().strip()
    require(owner in (NAME, NAME + '-' + version),
            'OLD_SERVICE_PKG_OWNERSHIP_UNPROVEN')
    config, _config_mode = regular_root_bytes(CONFIG)
    kernel = cold_screen()
    require(read_command(pkg_args).stdout == pkg_before,
            'OLD_PKGDB_CHANGED_DURING_SCREEN')
    service_after, mode_after = regular_root_bytes(SERVICE)
    config_after, _ = regular_root_bytes(CONFIG)
    require(service_after == service and mode_after == mode and config_after == config,
            'OLD_SERVICE_OR_CONFIG_CHANGED_DURING_SCREEN')
    cold_screen()
    native_pkg_handoff.verify_original_lock(9, original_fd9_inode)
    return {'status': 'READ_ONLY_STOPPED_PREDECESSOR_SCREENED',
            'installed_version': version, 'service_sha256': digest(service),
            'config_sha256': digest(config), 'kernel': kernel,
            'historical_status_called_under_fd9': False,
            'old_owner_qualified': False, 'pkg_invoked': False,
            'lh08_ac11_accepted': False}
