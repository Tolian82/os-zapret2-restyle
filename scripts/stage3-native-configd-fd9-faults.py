#!/usr/bin/env python3
"""One-use, no-pkg OPNsense original-FD9 failure witness for Stage 3.04.

Runs genuine configctl actions against a disposable installed historical package.
A caller-side ACK is only provisional; independently owned FD9 is mandatory.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
PREFIX='STAGE3_CONFIGD_FD9_FAULTS='
CASES=('drop_ack','stall_ack','post_ack_exit')


def load(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),HERE/name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify(case,returncode,stdout,stderr,independent_lock_free):
    """Reject every fault, including provisional ACK followed by worker death."""
    if case not in CASES or not isinstance(returncode,int):
        raise ValueError('INVALID_FAULT_OBSERVATION')
    out=stdout+'\n'+stderr
    ack='ACKED_CONTINUOUS_FD9_TRANSFER' in out
    if case=='post_ack_exit':
        if not ack:
            raise ValueError('POST_ACK_CRASH_WAS_NOT_PROVEN_AFTER_ACK')
        status='REFUSED_ACKED_WORKER_EXITED_BEFORE_DURABLE_OWNERSHIP'
    else:
        if ack:
            raise ValueError('NON_ACK_CASE_WAS_ACCIDENTALLY_ADMITTED')
        status='REFUSED_MISSING_OR_TIMED_OUT_WORKER_ACK'
    if independent_lock_free is not True:
        raise ValueError('ORIGINAL_FD9_STILL_HELD_AFTER_FAULT')
    return {'schema':1,'case':case,'status':status,
            'configctl_returncode':returncode,
            'observed_provisional_ack':ack,
            'independent_original_fd9_free_after_abort':True,
            'package_mutation_invoked':False}


def root_only_file(path,allow_mode=None):
    st=path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or (
            allow_mode is not None and stat.S_IMODE(st.st_mode)!=allow_mode):
        raise RuntimeError('FOREIGN_TEST_ARTIFACT_NO_CLEANUP:'+path.name)


def run_case(m,managed,old,guard,head,case,baseline,original_inode):
    if m.ROOT.exists() or m.ROOT.is_symlink() or m.ACTION.exists() or m.ACTION.is_symlink():
        raise RuntimeError('FOREIGN_TEST_CASE_RESOURCE_PRESENT')
    m.ROOT.mkdir(mode=0o700)
    nonce=os.urandom(16).hex()
    m.base.create_owned(m.TICKET,json.dumps({'head':head,'nonce':nonce}).encode())
    os.environ['ZAPRET2_STAGE3_HANDOFF_FAULT']=case
    os.environ['ZAPRET2_STAGE3_HANDOFF_NEGATIVE']='1'
    action=m.action_bytes(head)
    m.base.create_owned(m.ACTION,action)
    try:
        m.base.run(['/usr/sbin/service','configd','restart'],45)
        actions=m.base.run(['/usr/local/sbin/configctl','configd','actions'],15)
        m.need('zapret2_stage3_handoff_ci' in actions,'REAL_CONFIGD_ACTION_UNREGISTERED')
        p=subprocess.run(['/usr/local/sbin/configctl','zapret2_stage3_handoff_ci','launch'],
                         capture_output=True,text=True,timeout=40,check=False)
        m.need(isinstance(p.returncode,int) and 0<=p.returncode<=255,
               'UNKNOWN_CONFIGD_FAULT_EXIT')
        # A worker may send ACK and then exit. Do not infer admission from
        # successful configctl, READY or ACK without an independent BUSY check.
        expiry=time.monotonic()+8
        while time.monotonic()<expiry and m.PIDFILE.exists():
            time.sleep(.2)
        m.need(not m.PIDFILE.exists() and not m.PIDFILE.is_symlink(),
               'FAILED_WORKER_DAEMON_STILL_ACTIVE')
        ready=m.wait_ready(head,nonce)
        m.need(ready['original_fd9_inode']==original_inode or original_inode is None,
               'FAULT_WORKER_ORIGINAL_LOCK_INODE_CHANGED')
        m.need(ready['native_pkg_mutation_invoked'] is False,
               'FAULT_WORKER_REPORTED_PKG_MUTATION')
        challenger=load('stage2-prepkg-locked-cold-revalidation.py')
        m.need(challenger.LOCK==m.base.LOCK,'WRONG_ORIGINAL_FD9_CHALLENGER')
        q=subprocess.run(['/bin/sh','-c',challenger.CHALLENGER,'sh',str(m.base.LOCK)],
                         text=True,capture_output=True,timeout=8,check=False)
        result=classify(case,p.returncode,p.stdout,p.stderr,q.returncode==0)
        m.need(managed.owner_snapshot(old,guard,m.base.OLD)==baseline,
               'NEGATIVE_CASE_MUTATED_OLD_PKG_CONFIG_PROCESS_IPFW')
    finally:
        # Only the strictly matching test action can be removed. No PID kill.
        m.need(m.base.trusted(m.ACTION)==action,'CONFIGD_FAULT_ACTION_CHANGED_NO_DELETE')
        m.ACTION.unlink()
        m.base.run(['/usr/sbin/service','configd','restart'],45)
    for path in (m.TICKET,m.READY):
        root_only_file(path,0o600)
        path.unlink()
    for path in (m.DONE,m.FAILED,m.RELEASE):
        if path.exists() or path.is_symlink():
            root_only_file(path,0o600)
            path.unlink()
    if m.SOCKET.exists() or m.SOCKET.is_symlink():
        st=m.SOCKET.lstat()
        m.need(stat.S_ISSOCK(st.st_mode) and st.st_uid==0 and
               stat.S_IMODE(st.st_mode)==0o600,
               'FOREIGN_FAULT_SOCKET_NO_DELETE')
        m.SOCKET.unlink()
    m.ROOT.rmdir()
    m.need(managed.owner_snapshot(old,guard,m.base.OLD)==baseline,
           'FAULT_POST_CLEANUP_CHANGED_INSTALLED_OLD_STATE')
    return result


def execute(head):
    m=load('stage3-native-configd-fd9-handoff.py')
    m.qualify(head)
    m.need(os.environ.get('ZAPRET2_STAGE3_HANDOFF_NEGATIVE')=='1',
           'DISPOSABLE_FAULT_INJECTION_NOT_OPTED_IN')
    m.need(not m.ROOT.exists() and not m.ROOT.is_symlink() and
           not m.ACTION.exists() and not m.ACTION.is_symlink(),
           'FAULT_MATRIX_RESOURCE_PREEXISTS')
    guest=load('stage0-opnsense-guest-readonly.py')
    installer=load('stage0-opnsense-installed-predecessor.py')
    old=load('stage0-installed-predecessor-readonly.py')
    guard=load('stage0-opnsense-prepkg-readonly.py')
    managed=load('stage2-managed-prepkg-veto-witness.py')
    m.need(guest.evaluate(guest.observe())['status']==
           'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY',
           'DISPOSABLE_OPNSENSE_26_7_REQUIRED')
    m.need(installer.install_and_verify(m.base.OLD)['status']==
           'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
           'REAL_PUBLISHED_OLD_PKG_UNQUALIFIED')
    m.need(guard.snapshot(m.base.OLD)['status']=='PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
           'REAL_OLD_NOT_COLD_STOPPED')
    baseline=managed.owner_snapshot(old,guard,m.base.OLD)
    m.need(not m.base.LOCK.is_symlink(),'FOREIGN_ORIGINAL_LOCK_SYMLINK')
    existed=m.base.LOCK.exists()
    initial_inode=m.base.LOCK.lstat().st_ino if existed else None
    results=[]
    for case in CASES:
        results.append(run_case(m,managed,old,guard,head,case,baseline,initial_inode))
        if initial_inode is None:
            # In each subsequent case, do NOT replace the test-created original
            # inode. It is the same historical lock path, never another lock.
            initial_inode=m.base.LOCK.lstat().st_ino
    if not existed:
        lock=m.base.LOCK
        m.need(lock.is_file() and not lock.is_symlink(),'TEST_LOCK_DISAPPEARED')
        fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW)
        try:
            st=os.fstat(fd)
            m.need(st.st_uid==0 and st.st_nlink==1 and
                   st.st_ino==initial_inode and st.st_ino==lock.lstat().st_ino,
                   'TEST_CREATED_ORIGINAL_LOCK_INODE_CHANGED')
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('TEST_CREATED_ORIGINAL_LOCK_STILL_BUSY') from None
            lock.unlink()
        finally:
            os.close(fd)
        m.need(not lock.exists() and not lock.is_symlink(),
               'TEST_CREATED_LOCK_ABSENCE_NOT_RESTORED')
    else:
        m.need(m.base.LOCK.is_file() and m.base.LOCK.lstat().st_ino==initial_inode,
               'PREEXISTING_ORIGINAL_LOCK_INODE_CHANGED')
    return {'schema':1,'status':'PASS_TEST_ONLY_ORIGINAL_FD9_FAULT_MATRIX',
            'cases':results,
            'all_fail_closed':True,'native_pkg_mutation_invoked':False,
            'original_package_config_process_ipfw_unchanged':True,
            'owner_appliance_modified':False,'lh08_ac11_accepted':False}


def main():
    try:
        if len(sys.argv)!=2 or re.fullmatch(r'[0-9a-f]{40}',sys.argv[1]) is None:
            raise ValueError('EXACT_HEAD_ARGUMENT_REQUIRED')
        report=execute(sys.argv[1])
        print(PREFIX+json.dumps(report,sort_keys=True),flush=True)
        return 0
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,
            subprocess.SubprocessError,socket.timeout) as exc:
        err=re.sub(r'[^A-Za-z0-9_.:-]','_',str(exc)[:160])
        print(PREFIX+'REFUSED:'+err,file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':
    sys.exit(main())
