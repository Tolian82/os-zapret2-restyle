#!/usr/bin/env python3
"""Native FD9/Config-lock Voice rollback quiescence gate (read-only).

A real on-appliance command confirms every managed Voice process is absent
AND the kernel Voice IPFW interval/tables match the previous durable owner.
No process stop/start, file restore, IPFW mutation or journal transition
is performed. The result only permits a FUTURE complete five-resource
coordinator to consider file rollback: it never authorizes Voice ON.
"""
from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
import stat
import sys

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_journal import BOUND_FIELD, VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore, fingerprint, canonical_manifest
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_probe import FreeBSDVoiceProcessProbe
import voice_ipfw_runtime as native

EXPECTED_SCRIPTS = {
    "engine": "/usr/local/etc/zapret2/binaries/my/dvtws2",
    "daemon": "/usr/sbin/daemon",
    "monitor": "/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh",
}
PIDFILES = {
    "engine": "/var/run/dvtws2.pid",
    "daemon": "/var/run/zapret2-supervisor-daemon.pid",
    "monitor": "/var/run/zapret2-supervisor-monitor.pid",
}


class NativeQuiescenceError(RuntimeError):
    pass


def _locked_config(path: Path, fd: int, owner: tuple[int, int]) -> None:
    """Verify owner, inode, regular-file identity and exclusive live flock."""
    from voice_cutover_config_restore import _pinned_regular
    info = _pinned_regular(path, fd, owner=owner)
    if info.st_nlink != 1:
        raise NativeQuiescenceError("Config has unexpected hardlinks")
    # An independent open of the same inode MUST contend with the caller's
    # lock. This refuses the common mistake of just passing an open fd.
    second = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        try:
            fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
        else:
            fcntl.flock(second, fcntl.LOCK_UN)
            raise NativeQuiescenceError("OPNsense Config flock is not held")
    finally:
        os.close(second)


def inspect_quiescence(
    cutover: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    previous_backup: Path, probe: FreeBSDVoiceProcessProbe,
    adapter: FreeBSDIPFWAdapter, *,
    config_path: Path, locked_config_fd: int, config_owner: tuple[int, int],
    require_lifecycle_owner,
) -> dict:
    """Require observed stopped roles + exact old kernel IPFW under BOTH locks.

    A prepared or committed cutover cannot roll back via this path.
    In a pending IPFW transition, the previous owner and desired hash must
    both match the whole journal; no foreign staging rules/tables are
    allowed even if a manifest happens to look correct.
    """
    if not callable(require_lifecycle_owner) or \
       not isinstance(probe, FreeBSDVoiceProcessProbe) or \
       not isinstance(adapter, FreeBSDIPFWAdapter) or \
       adapter.allow_mutations is not False or \
       probe.expected != EXPECTED_SCRIPTS or \
       probe.pidfiles != PIDFILES or \
       Path(probe.previous_backup) != Path(previous_backup):
        raise NativeQuiescenceError("untrusted native Voice quiescence source")
    if type(config_owner) is not tuple or len(config_owner) != 2 or \
       any(type(n) is not int or n < 0 for n in config_owner):
        raise NativeQuiescenceError("untrusted native Config owner")
    require_lifecycle_owner()
    _locked_config(Path(config_path), locked_config_fd, config_owner)
    original = cutover.read()
    if original is None or original["phase"] != "mutating" or \
       original["schema"] < 2:
        raise NativeQuiescenceError("no mutating bound Voice cutover")
    previous_files = bound_resource_fingerprints(
        previous_backup, original["previous"]
    )
    if previous_files != {
        "config": original["previous"]["config"],
        "runtime": original["previous"]["runtime"],
    }:
        raise NativeQuiescenceError("unbound previous Config/runtime")
    prior = ledger.owned()
    pending = ledger.pending()
    if prior is None or fingerprint(canonical_manifest(prior)) != \
       original["previous"]["firewall"]:
        raise NativeQuiescenceError("IPFW ledger does not own previous state")
    if pending is not None and (
        pending["phase"] != "mutating" or
        pending["previous_sha256"] != original["previous"]["firewall"] or
        pending["desired_sha256"] != original["candidate"][BOUND_FIELD]
    ):
        raise NativeQuiescenceError("IPFW pending transition not bound to whole intent")
    if adapter.rule_base != prior["rule_base"] or \
       adapter.rule_max != prior["rule_max"]:
        raise NativeQuiescenceError("IPFW adapter outside previous owner interval")

    def sample() -> None:
        seen = probe.probe()
        if seen.get("engine", {}).get("state") != "stopped" or \
           seen.get("supervisor", {}).get("state") != "stopped":
            raise NativeQuiescenceError("Voice engine or supervisor still running")
        for key in ("process", "daemon", "monitor"):
            row = (seen["engine"] if key == "process" else
                   seen["supervisor"]).get(key)
            if not isinstance(row, dict) or row.get("pid") is not None or \
               row.get("start_ns") is not None:
                raise NativeQuiescenceError("stale Voice PID still present")
        if observe_owned_ipfw(ledger, adapter) != original["previous"]["firewall"]:
            raise NativeQuiescenceError("kernel IPFW is not previous owner")

    sample()
    require_lifecycle_owner()
    _locked_config(Path(config_path), locked_config_fd, config_owner)
    sample()
    if cutover.read() != original or ledger.owned() != prior or \
       ledger.pending() != pending or \
       bound_resource_fingerprints(previous_backup, original["previous"]) != previous_files:
        raise NativeQuiescenceError("quiescent Voice evidence changed between reads")
    require_lifecycle_owner()
    _locked_config(Path(config_path), locked_config_fd, config_owner)
    return {
        "state": "stopped-and-previous-ipfw",
        "config_lock": "verified",
        "lifecycle_lock": "verified",
        "voice_processes": "stopped",
        "owned_ipfw": "previous",
        "whole_phase": "mutating",
        "can_enable_voice": False,
        "can_complete_rollback": False,
    }


def main(argv: list[str]) -> int:
    """Installed, owner-only read-only diagnostic beneath service lockf FD9."""
    if len(argv) != 2 or argv[1] != "inspect":
        print("usage: voice_native_recovery_quiescence.py inspect", file=sys.stderr)
        return 64
    try:
        native.require_native_lock()
        journal = VoiceCutoverJournal(native.WHOLE)
        ledger = VoiceOwnershipStore(native.LEDGER)
        probe = FreeBSDVoiceProcessProbe(
            EXPECTED_SCRIPTS, PIDFILES, native.WHOLE / "previous",
        )
        fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = inspect_quiescence(
                journal, ledger, native.WHOLE / "previous", probe,
                FreeBSDIPFWAdapter(19000, 19010), config_path=native.CONFIG,
                locked_config_fd=fd, config_owner=(0, 0),
                require_lifecycle_owner=native.require_native_lock,
            )
        finally:
            os.close(fd)
        print("native-voice-quiescence=" + result["state"])
        print("whole-cutover-phase=" + result["whole_phase"])
        print("voice-enable=blocked")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("ERROR: native Voice quiescence refused: " + str(exc),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
