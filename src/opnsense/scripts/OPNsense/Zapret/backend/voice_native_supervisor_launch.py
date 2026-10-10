#!/usr/bin/env python3
"""Exact installed Zapret single-supervisor restart command contract.

Fixed paths are the same literals as voice_native_process_lifecycle.sh and
supervisor.sh. No user/candidate-provided launcher argument is accepted.
The canonical plan is sealed into version-2 previous process-security policy,
whose checksum is recorded by the schema-3 whole Voice journal.

FreeBSD kernel may expose a normalized daemon/process title; mismatch is
FAIL-CLOSED until proven with a real appliance capture, never guessed.
"""
from __future__ import annotations

from voice_restart_argv_attestation import _expected_supervisor, _digest

ROOT = "/usr/local/opnsense/scripts/OPNsense/Zapret"
ENGINE = "/usr/local/etc/zapret2/binaries/my/dvtws2"
DAEMON = "/usr/sbin/daemon"
LOOP = ROOT + "/supervisor_loop.sh"
SERVICE = ROOT + "/zapret_service.sh"
ENGINE_PID = "/var/run/dvtws2.pid"
DAEMON_PID = "/var/run/zapret2-supervisor-daemon.pid"
MONITOR_PID = "/var/run/zapret2-supervisor-monitor.pid"
LOG = "/var/log/zapret2/supervisor.log"
PATHS = {"engine": ENGINE, "daemon": DAEMON, "monitor": LOOP}


class SupervisorLaunchError(ValueError):
    pass


def canonical_supervisor_argv(scripts: dict) -> dict:
    """Do not accept alternate filesystem roots, scripts or daemon flags."""
    if scripts != PATHS:
        raise SupervisorLaunchError("foreign installed Voice launcher paths")
    output = {
        "daemon": [
            DAEMON, "-P", DAEMON_PID, "-p", MONITOR_PID,
            "-o", LOG, "-f", LOOP, ENGINE_PID, SERVICE, ENGINE,
        ],
        "monitor": ["/bin/sh", LOOP, ENGINE_PID, SERVICE, ENGINE],
    }
    return _expected_supervisor(PATHS, output)


def verified_supervisor_argv(scripts: dict, argv: dict) -> dict:
    """Strict equality, not caller-selected prefixes or optional flags."""
    expected = canonical_supervisor_argv(scripts)
    if argv != expected:
        raise SupervisorLaunchError(
            "supervisor argv differs from immutable installed launch plan"
        )
    return expected


def supervisor_plan_sha256(scripts: dict) -> str:
    return _digest(canonical_supervisor_argv(scripts))
