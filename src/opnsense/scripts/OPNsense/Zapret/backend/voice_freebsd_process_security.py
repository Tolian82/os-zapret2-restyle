#!/usr/bin/env python3
"""Unwired, non-authorizing FreeBSD native process image + credential witness.

Reads kernel text vnode pathname with kern.proc.pathname.<PID> and numeric
EUID/RUID/SVUID/EGID/RGID/SVGID from fixed FreeBSD ps columns. The running
script role is deliberately different from its kernel interpreter image.
All observations are bounded and bracketed by stable PID + start-token probes.

Path and UID/GID parity do NOT establish executable content integrity,
immutable execve argv, socket readiness or permission to restore anything.
Expected credentials and kernel images are caller-provided and NOT yet
bound to a durable Voice desired-state journal. No production caller.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import platform
import re
import subprocess

from voice_process_recovery_evidence import (
    ProcessEvidenceError, _expected_paths,
)

ROLES = ("engine", "daemon", "monitor")
FIELDS = ("euid", "ruid", "svuid", "egid", "rgid", "svgid")
MAX_PATH_BYTES = 4096
MAX_PS_BYTES = 512
PID_MAX = 4194304
ID_MAX = (1 << 32) - 1
PS_PREFIX = ("/bin/ps", "-p")
PS_COLUMNS = ("-o", "pid=", "-o", "uid=", "-o", "ruid=",
              "-o", "svuid=", "-o", "gid=", "-o", "rgid=",
              "-o", "svgid=")


class ProcessSecurityError(ValueError):
    pass


def _safe_path(value):
    if not isinstance(value, str) or not 1 < len(value) <= MAX_PATH_BYTES or \
       not Path(value).is_absolute() or ".." in Path(value).parts or \
       any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ProcessSecurityError("untrusted expected native kernel image")
    return value


def _identities(rows, expected_scripts):
    if not isinstance(rows, dict) or set(rows) != {"engine", "supervisor"}:
        raise ProcessSecurityError("missing three-role Voice process inventory")
    e, s = rows["engine"], rows["supervisor"]
    if not isinstance(e, dict) or not isinstance(s, dict) or \
       e.get("state") != "running" or s.get("state") != "running" or \
       not isinstance(e.get("process"), dict) or \
       not isinstance(s.get("daemon"), dict) or \
       not isinstance(s.get("monitor"), dict):
        raise ProcessSecurityError("partial or stopped native process inventory")
    values = {"engine": e["process"], "daemon": s["daemon"],
              "monitor": s["monitor"]}
    seen = set()
    for role in ROLES:
        row = values[role]
        if set(row) != {"pid", "start_ns", "executable"}:
            raise ProcessSecurityError("untrusted three-role identity")
        pid, start = row["pid"], row["start_ns"]
        if type(pid) is not int or not 1 < pid <= PID_MAX or \
           type(start) is not int or start <= 0 or \
           row["executable"] != expected_scripts[role] or pid in seen:
            raise ProcessSecurityError("unsafe native PID/start/executable identity")
        seen.add(pid)
    return values


def parse_kernel_path(raw):
    if not isinstance(raw, bytes) or not 2 <= len(raw) <= MAX_PATH_BYTES or \
       raw[-1] != 0 or raw.count(b"\0") != 1:
        raise ProcessSecurityError("untrusted kernel pathname bytes")
    try:
        return _safe_path(raw[:-1].decode("ascii"))
    except UnicodeError as exc:
        raise ProcessSecurityError("non-ASCII native process pathname") from exc


def sysctl_kernel_path(pid):
    """Bounded read of FreeBSD's kernel text vnode path, never a mutation."""
    if type(pid) is not int or not 1 < pid <= PID_MAX or \
       platform.system() != "FreeBSD":
        raise ProcessSecurityError("native FreeBSD with valid PID required")
    libc = ctypes.CDLL(None, use_errno=True)
    sysctl = libc.sysctlbyname
    sysctl.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                       ctypes.POINTER(ctypes.c_size_t),
                       ctypes.c_void_p, ctypes.c_size_t]
    sysctl.restype = ctypes.c_int
    oid = f"kern.proc.pathname.{pid}".encode("ascii")
    length = ctypes.c_size_t(0)
    if sysctl(oid, None, ctypes.byref(length), None, 0) != 0 or \
       not 2 <= length.value <= MAX_PATH_BYTES:
        raise ProcessSecurityError("FreeBSD process pathname length unavailable")
    buffer = ctypes.create_string_buffer(length.value)
    filled = ctypes.c_size_t(length.value)
    if sysctl(oid, buffer, ctypes.byref(filled), None, 0) != 0 or \
       not 2 <= filled.value <= length.value:
        raise ProcessSecurityError("FreeBSD process pathname read failed")
    data = buffer.raw[:filled.value]
    parse_kernel_path(data)
    return data


def ps_numeric_credentials(pid, *, runner=None):
    """Read native FreeBSD real/effective/saved IDs; no shell or usernames."""
    if type(pid) is not int or not 1 < pid <= PID_MAX:
        raise ProcessSecurityError("invalid native process PID")
    argv = (*PS_PREFIX, str(pid), *PS_COLUMNS)
    if runner is None:
        if platform.system() != "FreeBSD":
            raise ProcessSecurityError("native FreeBSD ps credential source required")
        result = subprocess.run(argv, check=False, text=True, timeout=5,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env={"LC_ALL": "C", "PATH": "/bin:/usr/bin"})
        if result.returncode != 0:
            raise ProcessSecurityError("native FreeBSD credential query failed")
        output = result.stdout
    else:
        output = runner(argv)
    if not isinstance(output, str) or len(output.encode("utf-8")) > MAX_PS_BYTES:
        raise ProcessSecurityError("invalid or oversized numeric credential data")
    lines = [row for row in output.splitlines() if row.strip()]
    if len(lines) != 1:
        raise ProcessSecurityError("missing or ambiguous numeric credential row")
    tokens = lines[0].split()
    if len(tokens) != 7 or any(re.fullmatch(r"[0-9]{1,10}", x) is None for x in tokens):
        raise ProcessSecurityError("non-numeric FreeBSD credential column")
    numbers = [int(x) for x in tokens]
    if numbers[0] != pid or any(x > ID_MAX for x in numbers[1:]):
        raise ProcessSecurityError("credential row does not belong to PID")
    return dict(zip(FIELDS, numbers[1:]))


def _expected_map(expected_scripts, kernel_images, credentials):
    _expected_paths(expected_scripts)
    if not isinstance(kernel_images, dict) or set(kernel_images) != set(ROLES) or \
       not isinstance(credentials, dict) or set(credentials) != set(ROLES):
        raise ProcessSecurityError("incomplete trusted role image/credential requirements")
    for role in ROLES:
        _safe_path(kernel_images[role])
        row = credentials[role]
        if not isinstance(row, dict) or set(row) != set(FIELDS) or \
           any(type(value) is not int or not 0 <= value <= ID_MAX
               for value in row.values()):
            raise ProcessSecurityError("ambiguous expected numeric process credentials")


class FreeBSDProcessSecurityReader:
    """Read-only source for future lock-held restart certification, NOT wired."""

    def __init__(self, expected_scripts, kernel_images, credentials,
                 process_probe, *, path_reader=None, ps_reader=None):
        _expected_map(expected_scripts, kernel_images, credentials)
        self.expected_scripts = dict(expected_scripts)
        self.kernel_images = dict(kernel_images)
        self.credentials = {role: dict(credentials[role]) for role in ROLES}
        self.probe = process_probe
        self.path_reader = path_reader or sysctl_kernel_path
        self.ps_reader = ps_reader

    def observe_security(self):
        before = self.probe.probe()
        identities = _identities(before, self.expected_scripts)
        rows = {}
        for role in ROLES:
            identity = identities[role]
            pid = identity["pid"]
            path = parse_kernel_path(self.path_reader(pid))
            creds = ps_numeric_credentials(pid, runner=self.ps_reader)
            if path != self.kernel_images[role] or creds != self.credentials[role]:
                raise ProcessSecurityError("foreign native kernel image or UID/GID")
            rows[role] = {"pid": pid, "start_ns": identity["start_ns"],
                          "image": path, "credentials": creds}
        if self.probe.probe() != before:
            raise ProcessSecurityError("native process identity changed during inspection")
        return rows

    def inspect_twice(self):
        """Non-authorizing repeated observation; never infer startup readiness."""
        first = self.observe_security()
        if self.observe_security() != first:
            raise ProcessSecurityError("native process image/credentials changed")
        return {"state": "review-required", "reason": "matching-process-path-and-ids-only",
                "roles": first, "can_activate": False,
                "can_recover_automatically": False, "safe_to_mutate": False,
                "startup_ready": False, "media_pass": False}
