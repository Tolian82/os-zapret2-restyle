#!/usr/bin/env python3
"""Strict read-only FreeBSD native Voice kernel argv and binary attestation.

This native-only inspector uses existing bounded FreeBSD numeric-MIB sysctl
readers for NUL-delimited kern.proc.args and the exact kern.proc.pathname
executable image. Never parse human ps command strings
as argv. A stable two-pass /bin/ps pid/start snapshot plus the sealed old
runtime and immutable supervisor launcher plan are required. An invalid/
normalized process title, different executable, changing PID/start epoch,
missing kernel data or unsupported FreeBSD format REFUSES (fail closed).

This is a separate diagnostic from boot review, NOT a process re-adoption,
not startup readiness, not media proof, not Voice ON, and not an authorization
to release legacy lifecycle, IPFW or the preserved rollback journal.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import sys

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import mutating_predecessor
from voice_cutover_close import inspect_close_placement
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import (
    EXPECTED_SCRIPTS, PIDFILES, _locked_config,
)
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_restart_argv_attestation import expected_engine_argv
from voice_freebsd_kernel_argv import parse_kernel_argv, sysctl_kernel_argv
from voice_freebsd_process_security import parse_kernel_path, sysctl_kernel_path
from voice_native_file_observer import observe_live_files
from voice_process_recovery_evidence import inspect_process_evidence
from voice_cutover_recovery_receipt import read_receipt
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_boot_recovery_review import inspect_boot_recovery
from voice_firewall_ledger import VoiceOwnershipStore
from voice_cutover_journal import VoiceCutoverJournal
import voice_ipfw_runtime as native

VALID_PIDS=range(2,4194305)
SYSTEM_PATHS={
    "engine": EXPECTED_SCRIPTS["engine"],
    "daemon": "/usr/sbin/daemon",
    "monitor": "/bin/sh",
}
ROLE_NAMES=("engine","daemon","monitor")


class KernelArgvError(RuntimeError):
    pass


class FreeBSDKernelArgvReader:
    """Existing kernel sysctl sources; injected byte readers only for offline CI."""

    def __init__(self,raw_argv_reader=None,raw_path_reader=None):
        self.raw_argv_reader=(
            sysctl_kernel_argv if raw_argv_reader is None else raw_argv_reader
        )
        self.raw_path_reader=(
            sysctl_kernel_path if raw_path_reader is None else raw_path_reader
        )

    @staticmethod
    def _pid(pid):
        if type(pid) is not int or pid not in VALID_PIDS:
            raise KernelArgvError("invalid native Voice kernel PID")
        return pid

    def argv(self,pid):
        try:
            return parse_kernel_argv(self.raw_argv_reader(self._pid(pid)))
        except (OSError,ValueError,TypeError) as exc:
            raise KernelArgvError("invalid FreeBSD kernel argument array") from exc

    def binary(self,pid):
        try:
            return parse_kernel_path(self.raw_path_reader(self._pid(pid)))
        except (OSError,ValueError,TypeError) as exc:
            raise KernelArgvError("invalid FreeBSD kernel binary pathname") from exc


def _live_instances(snapshot):
    if not isinstance(snapshot,dict) or set(snapshot)!={"engine","supervisor"}:
        raise KernelArgvError("malformed native Voice process snapshot")
    if snapshot["engine"]["state"]!="running" or (
        snapshot["supervisor"]["state"]!="running"
    ):
        raise KernelArgvError("native Voice processes not all running")
    src={
        "engine":snapshot["engine"]["process"],
        "daemon":snapshot["supervisor"]["daemon"],
        "monitor":snapshot["supervisor"]["monitor"],
    }
    result={}
    for role in ROLE_NAMES:
        row=src[role]
        if row["executable"]!=EXPECTED_SCRIPTS[role] or (
            type(row["pid"]) is not int or row["pid"] not in VALID_PIDS
            or type(row["start_ns"]) is not int or row["start_ns"]<=0
        ):
            raise KernelArgvError("foreign native Voice process role or epoch")
        result[role]={"pid":row["pid"],"start_ns":row["start_ns"]}
    if len({x["pid"] for x in result.values()})!=3:
        raise KernelArgvError("native Voice roles share a PID")
    return result


def inspect_native_kernel_argv(
    *,journal,ledger,previous_backup,process_evidence,security_evidence,
    install_image,config_path,active_runtime,probe,adapter,config_fd,
    config_owner,require_lifecycle_owner,kernel_reader=None,
):
    """Native FD9+Config flock read-only kernel argv/binary + epoch gate.

    Does NOT require equal epochs to old sealed receipt after reboot: exact
    old bytes/argv + current stable PID/start are observed separately.
    """
    if not isinstance(probe,FreeBSDVoiceProcessProbe) or (
        probe.expected!=EXPECTED_SCRIPTS or probe.pidfiles!=PIDFILES
        or Path(probe.previous_backup)!=Path(previous_backup)
        or not isinstance(adapter,FreeBSDIPFWAdapter)
        or adapter.allow_mutations is not False
    ):
        raise KernelArgvError("untrusted native Voice process/kernel sources")
    if kernel_reader is None:
        kernel_reader=FreeBSDKernelArgvReader()
    if not isinstance(kernel_reader,FreeBSDKernelArgvReader):
        raise KernelArgvError("untrusted native kernel argv reader")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    _pinned_regular(Path(config_path),config_fd,owner=config_owner)
    boot=inspect_boot_recovery(
        journal=journal,ledger=ledger,previous_backup=previous_backup,
        process_evidence=process_evidence,security_evidence=security_evidence,
        install_image=install_image,config_path=config_path,
        active_runtime=active_runtime,probe=probe,adapter=adapter,
        config_fd=config_fd,config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if boot["state"] not in (
        "previous-rollback-sealed-needs-manual-finalization",
        "previous-journal-archived-awaits-native-acceptance",
    ) or (
        boot["phase"]!="rolled_back" or boot["config"]!="previous"
        or boot["runtime"]!="previous" or boot["kernel"]!="previous"
        or boot["processes"]!="running" or boot["voice_on"] is not False
        or boot["safe_to_close_intent"] is not False
        or boot["previous_finalization"]!="sealed-awaiting-owner-acceptance"
    ):
        raise KernelArgvError("native old five-resource postrollback witness denied")
    place=inspect_close_placement(
        journal=journal,config_path=Path(config_path),
        active_runtime=Path(active_runtime),
    )
    terminal=place["record"]
    if terminal is None or terminal["phase"]!="rolled_back":
        raise KernelArgvError("no preserved original whole intent")
    orig=mutating_predecessor(terminal)
    sealed=inspect_process_evidence(
        process_evidence,previous_backup,EXPECTED_SCRIPTS,terminal["previous"],
    )
    if sealed["observation"]["engine"]["state"]!="running":
        raise KernelArgvError("previous sealed engine was not running")
    expected={
        "engine":expected_engine_argv(previous_backup,EXPECTED_SCRIPTS["engine"]),
        **canonical_supervisor_argv(EXPECTED_SCRIPTS),
    }
    saved=bound_resource_fingerprints(previous_backup,terminal["previous"])
    if observe_live_files(config_path,active_runtime,previous_backup=previous_backup)!=saved:
        raise KernelArgvError("old Config/runtime mutated during native probe")
    first=probe.probe()
    before=_live_instances(first)
    # Sysctl returns actual packed argv bytes, not ps text. procstat checks
    # the executable binary independently, e.g. monitor's /bin/sh interpreter.
    observed={}
    for role in ROLE_NAMES:
        pid=before[role]["pid"]
        argv=kernel_reader.argv(pid)
        binary=kernel_reader.binary(pid)
        if argv!=expected[role] or binary!=SYSTEM_PATHS[role]:
            raise KernelArgvError("kernel argv or executable differs from sealed plan")
        observed[role]={"pid":pid,"start_ns":before[role]["start_ns"],
                        "binary":binary}
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    after=_live_instances(probe.probe())
    if before!=after or journal.read()!=(
        terminal if place["state"]!="archived-awaiting-native-acceptance" else None
    ) or inspect_close_placement(
        journal=journal,config_path=Path(config_path),
        active_runtime=Path(active_runtime),
    )["record"]!=terminal or ledger.pending() is not None or (
        observe_live_files(config_path,active_runtime,previous_backup=previous_backup)!=saved
    ):
        raise KernelArgvError("native Voice process or whole rollback changed")
    for role in ROLE_NAMES:
        pid=before[role]["pid"]
        if kernel_reader.argv(pid)!=expected[role] or (
            kernel_reader.binary(pid)!=SYSTEM_PATHS[role]
        ):
            raise KernelArgvError("native kernel argv/binary changed between reads")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    return {
        "state":"kernel-argv-and-binary-match-previous-not-readiness",
        "whole_check":terminal["check"],"cutover_check":orig["check"],
        "instances":before,"kernel_argv":"matching","kernel_binary":"matching",
        "safe_to_start":False,"safe_to_close_intent":False,
        "media_pass":False,"voice_on":False,
    }


def main(argv):
    if argv!=["inspect"]:
        print("usage: voice_native_kernel_argv.py inspect",file=sys.stderr)
        return 64
    fd=None
    try:
        native.require_native_lock()
        journal=VoiceCutoverJournal(native.WHOLE)
        ledger=VoiceOwnershipStore(native.LEDGER)
        backup=native.WHOLE/"previous"
        probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS,PIDFILES,backup)
        fd=os.open(native.CONFIG,os.O_RDWR|getattr(os,"O_NOFOLLOW",0))
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=inspect_native_kernel_argv(
            journal=journal,ledger=ledger,previous_backup=backup,
            process_evidence=native.WHOLE/"process-evidence",
            security_evidence=native.WHOLE/"process-security-policy",
            install_image=native.WHOLE/"restore-install-image",
            config_path=native.CONFIG,active_runtime=native.ACTIVE_ROOT,
            probe=probe,adapter=FreeBSDIPFWAdapter(19000,19010),
            config_fd=fd,config_owner=(0,0),
            require_lifecycle_owner=native.require_native_lock,
        )
        print("native-kernel-argv="+result["state"])
        print("voice-enable=blocked")
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print("ERROR: Voice kernel argv inspection refused: "+str(exc),file=sys.stderr)
        return 1
    finally:
        if fd is not None: os.close(fd)


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
