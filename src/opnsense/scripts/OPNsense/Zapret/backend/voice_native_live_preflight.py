#!/usr/bin/env python3
"""Live FreeBSD Voice engine/supervisor baseline BEFORE any cutover journal.

Owner-only read-only OPNsense diagnostic. Unlike post-rollback attestation it
needs NO previous backup or cutover journal, so a real installed/working
legacy Voice-OFF system can be inspected BEFORE native Voice Apply.

The existing lifecycle FD9 and ORIGINAL Config flock must remain held. Fixed
FreeBSD pidfiles and native ps PID/start readings bracket TWO samples of
actual kernel argv (NUL framing) and kernel executable path, compared with a
strictly pinned current dvtws.args and immutable supervisor launch command.
No unknown/active Voice journal, pending IPFW transaction or partial/foreign
process is accepted. NOTHING is written, no kernel rules edited and no
activation/Voice ON/automatic restoration is authorized.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys

from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_restart_argv_attestation import (
    MAX_ARGUMENT_FILE, MAX_ARGV, FIXED_TRAILER, _valid_token,
)
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
from voice_cutover_config_restore import _pinned_regular
from voice_native_live_ipfw import observe_ordinary_ipfw, observe_legacy_poc_ipfw
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native

DIR=os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0)
READ=os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_NONBLOCK",0)
ROLES=("engine","daemon","monitor")


class LivePreflightError(RuntimeError):
    pass


def _owner_dir(fd):
    st=os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.geteuid() or (
        st.st_mode&0o022 or st.st_nlink<2
    ):
        raise LivePreflightError("untrusted live Voice runtime directory")
    return (st.st_dev,st.st_ino)


def _current_engine_args(active_runtime):
    """Open pinned runtime directory and exact dvtws.args without following links."""
    fd=os.open(active_runtime,DIR)
    try:
        parent=_owner_dir(fd)
        root=os.lstat(active_runtime)
        if not stat.S_ISDIR(root.st_mode) or (
            root.st_dev,root.st_ino
        )!=parent:
            raise LivePreflightError("active Voice runtime path was substituted")
        child=os.open("dvtws.args",READ,dir_fd=fd)
        try:
            before=os.fstat(child)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or (
                before.st_uid!=os.geteuid() or before.st_mode&0o022
                or not 0<before.st_size<=MAX_ARGUMENT_FILE
            ):
                raise LivePreflightError("untrusted active Voice argument file")
            raw=os.read(child,MAX_ARGUMENT_FILE+1)
            after=os.fstat(child)
            if (before.st_dev,before.st_ino,before.st_size,
                before.st_mtime_ns,before.st_ctime_ns)!=(
                after.st_dev,after.st_ino,after.st_size,
                after.st_mtime_ns,after.st_ctime_ns,
            ) or len(raw)!=before.st_size:
                raise LivePreflightError("live Voice arguments changed while reading")
            on_disk=os.stat("dvtws.args",dir_fd=fd,follow_symlinks=False)
            if (on_disk.st_dev,on_disk.st_ino)!=(before.st_dev,before.st_ino):
                raise LivePreflightError("active Voice argv pathname replaced")
            if _owner_dir(fd)!=parent:
                raise LivePreflightError("runtime directory changed during audit")
        finally:
            os.close(child)
    finally:
        os.close(fd)
    if not raw or any(b not in (9,10,32) and not 33<=b<=126 for b in raw):
        raise LivePreflightError("unrepresentable live Voice launcher argument")
    tokens=[part.decode("ascii") for part in raw.split()]
    if not tokens or len(tokens)+3>MAX_ARGV or (
        any(not _valid_token(x) or x.startswith(("--sockarg=","--user="))
            for x in tokens)
    ):
        raise LivePreflightError("unsafe current Voice argv tokens")
    return (
        [EXPECTED_SCRIPTS["engine"],*tokens,*FIXED_TRAILER],
        hashlib.sha256(raw).hexdigest(),
        parent,
        (before.st_dev,before.st_ino,before.st_uid,
         stat.S_IMODE(before.st_mode),before.st_size),
    )


def _journals_idle(whole_root,ledger_root):
    """No journal mutation or directory creation; unknown paths fail closed."""
    root=Path(whole_root)
    if os.path.lexists(root):
        if VoiceCutoverJournal(root).read() is not None or os.listdir(root):
            raise LivePreflightError("pending or retained native Voice rollback evidence")
    ledger=Path(ledger_root)
    if os.path.lexists(ledger):
        owner=VoiceOwnershipStore(ledger)
        if owner.pending() is not None:
            raise LivePreflightError("pending Voice IPFW mutation")
        # This baseline is only for the ordinary unseeded legacy owner.
        # An existing native ownership ledger needs the separate sealed
        # owner+kernel comparison, never an unowned structural inspection.
        if owner.owned() is not None:
            raise LivePreflightError("native IPFW ownership requires journal-aware review")


def _instances(snapshot):
    if not isinstance(snapshot,dict) or set(snapshot)!={"engine","supervisor"}:
        raise LivePreflightError("invalid live Voice process report")
    e,s=snapshot["engine"],snapshot["supervisor"]
    if e.get("state")!="running" or s.get("state")!="running":
        raise LivePreflightError("one or more Voice processes are not running")
    rows={"engine":e["process"],"daemon":s["daemon"],"monitor":s["monitor"]}
    result={}
    for role in ROLES:
        row=rows[role]
        if not isinstance(row,dict) or set(row)!={"pid","start_ns","executable"} or (
            row["executable"]!=EXPECTED_SCRIPTS[role]
            or type(row["pid"]) is not int or not 1<row["pid"]<=4194304
            or type(row["start_ns"]) is not int or row["start_ns"]<=0
        ):
            raise LivePreflightError("foreign live Voice process identity")
        result[role]={"pid":row["pid"],"start_ns":row["start_ns"]}
    if len(set(item["pid"] for item in result.values()))!=3:
        raise LivePreflightError("duplicate native Voice process PID")
    return result


def inspect_live_preflight(
    *, config_path,active_runtime,whole_root,ledger_root,probe,kernel_reader,
    ipfw_adapter,config_fd,config_owner,require_lifecycle_owner,
    legacy_poc_ipv4=None,
):
    """Read-only physical baseline, no predecessor evidence or rollback needed."""
    if not callable(require_lifecycle_owner) or (
        not isinstance(probe,FreeBSDVoiceProcessProbe)
        or probe.expected!=EXPECTED_SCRIPTS or probe.pidfiles!=PIDFILES
        or not isinstance(kernel_reader,FreeBSDKernelArgvReader)
        or not isinstance(ipfw_adapter,FreeBSDIPFWAdapter)
        or ipfw_adapter.allow_mutations is not False
    ):
        raise LivePreflightError("untrusted live FreeBSD process source")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    info=_pinned_regular(Path(config_path),config_fd,owner=config_owner)
    _journals_idle(whole_root,ledger_root)
    expected_engine,argument_sha,parent_inode,first_arg_inode=_current_engine_args(
        Path(active_runtime)
    )
    expected={
        "engine":expected_engine,
        **canonical_supervisor_argv(EXPECTED_SCRIPTS),
    }
    first=probe.observe_processes()
    instances=_instances(first)
    observe_kernel = (lambda: observe_ordinary_ipfw(ipfw_adapter,expected["engine"])) if legacy_poc_ipv4 is None else (lambda: observe_legacy_poc_ipfw(ipfw_adapter,expected["engine"],legacy_poc_ipv4))
    first_ipfw=observe_kernel()
    for _ in range(2):
        for role in ROLES:
            pid=instances[role]["pid"]
            if kernel_reader.argv(pid)!=expected[role] or (
                kernel_reader.binary(pid)!=SYSTEM_PATHS[role]
            ):
                raise LivePreflightError("live FreeBSD argv or executable does not match")
        require_lifecycle_owner()
        _locked_config(Path(config_path),config_fd,config_owner)
        if probe.observe_processes()!=first:
            raise LivePreflightError("live native Voice PID/start changed during audit")
    second_ipfw=observe_kernel()
    if first_ipfw!=second_ipfw:
        raise LivePreflightError("kernel IPFW changed during pre-cutover audit")
    repeated_sha=_current_engine_args(Path(active_runtime))
    if repeated_sha[1:3]!=(argument_sha,parent_inode) or (
        repeated_sha[3]!=first_arg_inode
    ) or (
        os.fstat(config_fd).st_dev,os.fstat(config_fd).st_ino
    )!=(info.st_dev,info.st_ino):
        raise LivePreflightError("current Voice runtime or Config inode changed")
    _journals_idle(whole_root,ledger_root)
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    is_old_poc = legacy_poc_ipv4 is not None
    return {
        "state":("live-legacy-poc-process-ipfw-observed-not-readiness" if is_old_poc
                 else "live-legacy-process-argv-observed-not-readiness"),
        "instances":instances,
        "active_argument_sha256":argument_sha,
        "argv":"matching-current-runtime",
        "kernel_executable":"matching-fixed-launcher-images",
        "kernel_ipfw":("legacy-poc-structure-only-not-owned" if is_old_poc
                       else "ordinary-structure-only-not-owned"),
        "kernel_ipfw_structure_sha256":first_ipfw["structure_sha256"],
        "kernel_ipfw_rule_count":(first_ipfw["ordinary_rule_count"]+1 if is_old_poc
                                  else first_ipfw["rule_count"]),
        "kernel_ipfw_voice_tables":("absent" if is_old_poc
                                    else first_ipfw["voice_tables"]),
        "kernel_ipfw_legacy_table":("present" if is_old_poc
                                   else first_ipfw["legacy_table"]),
        "legacy_ipfw_previous":(first_ipfw["previous_ipfw"] if is_old_poc
                                else None),
        "safe_to_enable_voice":False,
        "safe_to_start":False,
        "safe_to_mutate":False,
        "media_pass":False,
    }


def main(argv):
    if argv!=["inspect"]:
        print("usage: voice_native_live_preflight.py inspect",file=sys.stderr)
        return 64
    fd=None
    try:
        native.require_native_lock()
        backup=native.WHOLE/"previous"
        probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS,PIDFILES,backup)
        fd=os.open(native.CONFIG,os.O_RDWR|getattr(os,"O_NOFOLLOW",0))
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        report=inspect_live_preflight(
            config_path=native.CONFIG,active_runtime=native.ACTIVE_ROOT,
            whole_root=native.WHOLE,ledger_root=native.LEDGER,
            probe=probe,kernel_reader=FreeBSDKernelArgvReader(),
            ipfw_adapter=FreeBSDIPFWAdapter(19000,19010),
            config_fd=fd,config_owner=(0,0),
            require_lifecycle_owner=native.require_native_lock,
        )
        print("native-voice-live-preflight="+report["state"])
        print("native-voice-argv="+report["argv"])
        print("native-voice-kernel-image="+report["kernel_executable"])
        print("native-voice-kernel-ipfw="+report["kernel_ipfw"])
        print("native-voice-ordinary-rules="+str(report["kernel_ipfw_rule_count"]))
        print("native-voice-voice-tables="+report["kernel_ipfw_voice_tables"])
        print("native-voice-legacy-table="+report["kernel_ipfw_legacy_table"])
        print("voice-on=blocked")
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print("ERROR: native Voice live preflight refused: "+str(exc),file=sys.stderr)
        return 69
    finally:
        if fd is not None: os.close(fd)


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
