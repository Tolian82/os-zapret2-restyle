#!/usr/bin/env python3
"""Unwired read-only FreeBSD kern.proc.args PID argv source.

FreeBSD's kern.proc.args.<PID> returns NUL-delimited kernel-exposed argv.
Unlike human-readable ps command output, this preserves argument boundaries.
IMPORTANT: FreeBSD permits process-title changes; kernel-exposed argv alone
is NOT immutable execve provenance or readiness proof. This source must be
corroborated with process start, executable path, ownership, lifecycle locks,
kernel IPFW, and actual on-appliance acceptance before production activation.

Raw sysctl reads are bounded, never write, and surround each three-role read
with stable process-probe identity. Linux CI injects fake raw reads.
"""
from __future__ import annotations

import ctypes
import os
import platform

from voice_process_recovery_evidence import (
    ProcessEvidenceError, _expected_paths,
)

MAX_BYTES = 128 * 1024
MAX_TOKENS = 512
MAX_TOKEN = 8192
ROLES = ("engine", "daemon", "monitor")


class KernelArgvError(ValueError):
    pass


def _valid_pid(pid):
    return type(pid) is int and 1 < pid <= 4194304


def parse_kernel_argv(raw: bytes) -> list[str]:
    """Fail-closed decoder for the exact byte form (NUL-delimited, no shell)."""
    if not isinstance(raw, bytes) or not 2 <= len(raw) <= MAX_BYTES or \
       raw[-1] != 0:
        raise KernelArgvError("missing or unbounded kernel argv record")
    parts = raw[:-1].split(b"\x00")
    if not 1 <= len(parts) <= MAX_TOKENS:
        raise KernelArgvError("kernel argv has invalid token count")
    result = []
    for item in parts:
        if not item or len(item) > MAX_TOKEN or \
           any(not 33 <= c <= 126 for c in item):
            # Reject empty, non-ASCII, NUL-ambiguous, whitespace-containing
            # arguments: this conservative launcher currently creates none.
            raise KernelArgvError("unsafe or ambiguous kernel argv argument")
        result.append(item.decode("ascii"))
    return result


def sysctl_kernel_argv(pid: int) -> bytes:
    """Read only kern.proc.args.<PID> via FreeBSD libc sysctlbyname.

    Two syscall steps (length then bytes). Identity must be re-probed by
    caller, since either process might exit/reuse its pid between steps.
    """
    if not _valid_pid(pid) or platform.system() != "FreeBSD":
        raise KernelArgvError("native FreeBSD and valid process PID required")
    libc = ctypes.CDLL(None, use_errno=True)
    fn = libc.sysctlbyname
    fn.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                   ctypes.POINTER(ctypes.c_size_t),
                   ctypes.c_void_p, ctypes.c_size_t]
    fn.restype = ctypes.c_int
    name = f"kern.proc.args.{pid}".encode("ascii")
    length = ctypes.c_size_t(0)
    if fn(name, None, ctypes.byref(length), None, 0) != 0:
        raise KernelArgvError("FreeBSD sysctl argv length query failed")
    if not 2 <= length.value <= MAX_BYTES:
        raise KernelArgvError("kernel argv length outside safe bound")
    buffer = ctypes.create_string_buffer(length.value)
    filled = ctypes.c_size_t(length.value)
    if fn(name, buffer, ctypes.byref(filled), None, 0) != 0 or \
       not 2 <= filled.value <= length.value:
        raise KernelArgvError("FreeBSD kernel argv changed or read failed")
    result = buffer.raw[:filled.value]
    parse_kernel_argv(result)
    return result


class FreeBSDKernelArgvReader:
    """Three-role read-only adapter for inspect_restarted_argv (not wired)."""

    def __init__(self, expected_paths, process_probe, *, raw_reader=None):
        _expected_paths(expected_paths)
        self.expected_paths = dict(expected_paths)
        self.process_probe = process_probe
        self.raw_reader = sysctl_kernel_argv if raw_reader is None else raw_reader

    def observe_argv(self):
        before = self.process_probe.probe()
        if not isinstance(before, dict) or set(before) != {"engine", "supervisor"}:
            raise KernelArgvError("missing native process instance inventory")
        engine = before.get("engine")
        supervisor = before.get("supervisor")
        if not isinstance(engine, dict) or not isinstance(supervisor, dict) or \
           engine.get("state") != "running" or \
           supervisor.get("state") != "running":
            raise KernelArgvError("restarted Voice roles are not all running")
        if not isinstance(engine.get("process"), dict) or \
           not isinstance(supervisor.get("daemon"), dict) or \
           not isinstance(supervisor.get("monitor"), dict):
            raise KernelArgvError("incomplete native three-role instance inventory")
        roles = {"engine": engine["process"],
                 "daemon": supervisor["daemon"],
                 "monitor": supervisor["monitor"]}
        pids = []
        for role in ROLES:
            row = roles[role]
            if set(row) != {"pid", "start_ns", "executable"} or \
               not _valid_pid(row["pid"]) or \
               type(row["start_ns"]) is not int or row["start_ns"] <= 0 or \
               row["executable"] != self.expected_paths[role]:
                raise KernelArgvError("unsafe native Voice process instance")
            pids.append(row["pid"])
        if len(set(pids)) != len(ROLES):
            raise KernelArgvError("Voice roles share a PID")
        sampled = {}
        for role in ROLES:
            row = roles[role]
            raw = self.raw_reader(row["pid"])
            sampled[role] = {**row, "argv": parse_kernel_argv(raw)}
        after = self.process_probe.probe()
        if after != before:
            raise KernelArgvError("process PID or start identity changed during argv reads")
        return {"engine": sampled["engine"],
                "supervisor": {"daemon": sampled["daemon"],
                               "monitor": sampled["monitor"]}}
