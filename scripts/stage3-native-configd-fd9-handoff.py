#!/usr/bin/env python3
"""One-use test: transfer original held FD9 into independent configd-launched worker.

This tests SCM_RIGHTS/ACK continuity, not a supported updater. No mutating pkg.
The configd action, supervisor, ticket and socket live only in disposable CI.
"""
import array
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import importlib.util


def load(name):
    s=importlib.util.spec_from_file_location(name.replace('-','_'),HERE/name)
    x=importlib.util.module_from_spec(s)
    s.loader.exec_module(x)
    return x


base=load('stage3-native-configd-detached-fd9.py')
ACTION=Path('/usr/local/opnsense/service/conf/actions.d/actions_zapret2_stage3_handoff_ci.conf')
ROOT=Path('/tmp/zapret2-stage3-fd9-handoff-ci')
SOCKET=ROOT/'fd9.sock'
TICKET=ROOT/'ticket'
READY=ROOT/'ready'
DONE=ROOT/'done'
FAILED=ROOT/'failed'
RELEASE=ROOT/'release'
PIDFILE=ROOT/'supervisor.pid'
QUERY=ROOT/'pkg-readonly.json'
PREFIX='STAGE3_CONFIGD_ATOMIC_FD9='


def need(ok,reason):
    base.need(ok,reason)


def qualify(head):
    base.qualify(head)
    need(os.environ.get('ZAPRET2_STAGE3_ATOMIC_HANDOFF')=='1',
         'ONE_USE_ATOMIC_HANDOFF_OPTIN_REQUIRED')


def ticket(head):
    x=json.loads(base.trusted(TICKET,500))
    need(x.get('head')==head and
         re.fullmatch('[0-9a-f]{32}',x.get('nonce','')) is not None,
         'ROOT_TICKET_UNTRUSTED')
    return x['nonce']


def fault_mode():
    """Allow only fixed fault injection scenarios inside disposable OPNsense CI."""
    fault=os.environ.get('ZAPRET2_STAGE3_HANDOFF_FAULT','')
    if fault:
        need(os.environ.get('ZAPRET2_STAGE3_HANDOFF_NEGATIVE')=='1' and
             fault in ('drop_ack','stall_ack','post_ack_exit'),
             'UNQUALIFIED_TEST_ONLY_HANDOFF_FAULT')
    return fault


def readonly_query_mode():
    """One-use no-mutation native pkg boundary, never a production updater."""
    value=os.environ.get('ZAPRET2_STAGE3_READONLY_PKG','')
    need(value in ('','1'),'READ_ONLY_PKG_MODE_INVALID')
    if value:
        need(os.environ.get('ZAPRET2_STAGE3_READONLY_PKG_CI')=='1' and
             not fault_mode(),'READ_ONLY_PKG_MODE_UNQUALIFIED')
    return value=='1'


def late_journal_mode():
    """One-use final pre-pkg veto test; requires genuine read-only pkg admission."""
    value=os.environ.get('ZAPRET2_STAGE3_LATE_JOURNAL','')
    need(value in ('','1'),'LATE_JOURNAL_MODE_INVALID')
    if value:
        need(os.environ.get('ZAPRET2_STAGE3_LATE_JOURNAL_CI')=='1' and
             readonly_query_mode() and not fault_mode(),
             'LATE_JOURNAL_TEST_MODE_UNQUALIFIED')
    return value=='1'


def readonly_pkg_query(head,fields):
    """Actual installed native pkg read query while inherited historical FD9 lives."""
    need(os.fstat(9).st_ino==fields['inode'],
         'READ_ONLY_PKG_LOST_ORIGINAL_FD9_BEFORE_QUERY')
    base.cold_owner_held()
    proc=subprocess.run(['/usr/sbin/pkg','-o','REPO_AUTOUPDATE=false',
                         'query','%n|%v','os-zapret2-restyle'],
                        capture_output=True,text=True,timeout=8,check=False)
    need(proc.returncode==0 and
         proc.stdout.strip()=='os-zapret2-restyle|0.6.2_1',
         'READ_ONLY_PKG_QUERY_NOT_AUTHENTIC_OLD')
    base.cold_owner_held()
    need(os.fstat(9).st_ino==fields['inode'],
         'READ_ONLY_PKG_LOST_ORIGINAL_FD9_AFTER_QUERY')
    marker={'schema':1,'status':'NATIVE_PKG_QUERY_UNDER_TRANSFERRED_FD9',
            'sha':head,'pid':os.getpid(),
            'original_fd9_inode':fields['inode'],
            'nonce_sha256':hashlib.sha256(fields['nonce'].encode()).hexdigest(),
            'native_pkg_read_only_query_invoked':True,
            'native_mutating_pkg_invoked':False}
    base.create_owned(QUERY,json.dumps(marker,sort_keys=True).encode())
    return marker


def action_bytes(head):
    script=str(Path(__file__).resolve())
    need(re.fullmatch(r'/[A-Za-z0-9_./-]+',script) is not None,
         'ACTION_SCRIPT_PATH_UNTRUSTED')
    fault=fault_mode()
    extra=('ZAPRET2_STAGE3_HANDOFF_NEGATIVE=1 '
           'ZAPRET2_STAGE3_HANDOFF_FAULT='+fault+' ') if fault else ''
    if readonly_query_mode():
        extra+='ZAPRET2_STAGE3_READONLY_PKG=1 ZAPRET2_STAGE3_READONLY_PKG_CI=1 '
    if late_journal_mode():
        extra+='ZAPRET2_STAGE3_LATE_JOURNAL=1 ZAPRET2_STAGE3_LATE_JOURNAL_CI=1 '
    return ('[launch]\n'
            'command:/usr/bin/env GITHUB_ACTIONS=true '
            'ZAPRET2_STAGE3_DETACHED_FD9=1 '
            'ZAPRET2_STAGE3_ATOMIC_HANDOFF=1 '
            'ZAPRET2_STAGE2_LOCKED_COLD_REVALIDATION=1 '
            'ZAPRET2_NATIVE_PROJECT_SHA='+head+' '+extra+
            '/usr/local/bin/python3 '+script+' --launch '+head+'\n'
            'parameters:\n'
            'type:script_output\n'
            'message:One-use original FD9 SCM_RIGHTS no-pkg handoff\n'
            'timeout:30\n').encode()


def open_original_fd9():
    # Match historical exact path and identity; never truncate an old inode.
    created=False
    try:
        fd=os.open(base.LOCK,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        created=True
    except FileExistsError:
        fd=os.open(base.LOCK,os.O_RDWR|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd)
        path=base.LOCK.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid==0 and st.st_nlink==1 and
             (st.st_dev,st.st_ino)==(path.st_dev,path.st_ino),
             'ORIGINAL_FD9_UNTRUSTED_INODE')
        os.dup2(fd,9)
        fcntl.flock(9,fcntl.LOCK_EX|fcntl.LOCK_NB)
        base.cold_owner_held()
        return created,st.st_ino
    finally:
        if fd!=9:
            os.close(fd)


def accept_rights(conn,head):
    payload,anc,flags,_=conn.recvmsg(500,socket.CMSG_SPACE(16))
    fds=[]
    for level,kind,data in anc:
        if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
            chunk=array.array('i')
            chunk.frombytes(data[:len(data)-(len(data)%chunk.itemsize)])
            fds.extend(chunk.tolist())
    try:
        need(flags==0 and len(fds)==1,'MISSING_OR_EXTRA_FD9_RIGHTS')
        fields=json.loads(payload)
        need(fields.get('head')==head and fields.get('nonce')==ticket(head) and
             isinstance(fields.get('created'),bool) and
             isinstance(fields.get('inode'),int) and fields['inode']>0,
             'TRANSFER_TICKET_OR_OWNER_UNTRUSTED')
        fd=fds[0]
        st=os.fstat(fd)
        path=base.LOCK.lstat()
        need(st.st_uid==0 and st.st_nlink==1 and stat.S_ISREG(st.st_mode)
             and (st.st_dev,st.st_ino)==(path.st_dev,path.st_ino)
             and st.st_ino==fields['inode'],
             'TRANSFERRED_FD9_NOT_ORIGINAL_INODE')
        os.dup2(fd,9)
        need(os.fstat(9).st_ino==fields['inode'],'FD9_DUPLICATION_FAILED')
        # BSD flock state is held by the same open file description.
        base.cold_owner_held()
        return fields
    finally:
        for fd in fds:
            if fd!=9:
                os.close(fd)


def worker(head):
    qualify(head)
    fault=fault_mode()
    query_enabled=readonly_query_mode()
    late_journal=late_journal_mode()
    need(ROOT.is_dir() and not ROOT.is_symlink() and
         ROOT.stat().st_uid==0 and stat.S_IMODE(ROOT.stat().st_mode)==0o700,
         'ROOT_HANDOFF_DIRECTORY_UNTRUSTED')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
        listener.bind(str(SOCKET))
        os.chmod(SOCKET,0o600)
        listener.listen(1)
        listener.settimeout(20)
        with listener.accept()[0] as conn:
            conn.settimeout(15)
            fields=accept_rights(conn,head)
            digest=hashlib.sha256(fields['nonce'].encode()).hexdigest()
            ready={'status':'HANDOFF_WORKER_HOLDS_ORIGINAL_FD9',
                   'schema':1,'sha':head,'pid':os.getpid(),
                   'original_fd9_inode':fields['inode'],
                   'created_original_lock_inode':fields['created'],
                   'nonce_sha256':digest,'native_pkg_mutation_invoked':False}
            base.create_owned(READY,json.dumps(ready,sort_keys=True).encode())
            if query_enabled:
                # No ACK until genuine native read-only pkg query completes
                # under the already-transferred original FD9.
                readonly_pkg_query(head,fields)
            # Faults are *only* in a one-use CI fixture; os._exit causes
            # genuine kernel descriptor closure, not simulated exceptions.
            if fault=='drop_ack':
                os._exit(96)
            if fault=='stall_ack':
                time.sleep(17)
                os._exit(97)
            # Launcher still owns FD9 at ACK: no moment with no lock holder.
            conn.sendall(('ACK:'+fields['nonce']+':'+str(os.getpid())).encode())
            if fault=='post_ack_exit':
                os._exit(98)
    try:
        need(base.wait_file(RELEASE,55)==b'RELEASE_TEST_ONLY',
             'WORKER_RELEASE_NOT_AUTHORIZED')
        if late_journal:
            # The real old owner became unsafe AFTER successful native pkg query
            # and original FD9 ACK. Final check must veto before any pkg dispatch.
            gate=load('stage3-native-configd-final-gate.py')
            refusal=gate.deny_late_journal_before_pkg(
                base.cold_owner_held,fields['inode'],os.fstat(9).st_ino)
            base.create_owned(DONE,json.dumps({
                **refusal,'sha':head,'pid':os.getpid(),
                'original_fd9_inode':fields['inode'],
                'nonce_sha256':digest,'native_mutating_pkg_invoked':False},
                sort_keys=True).encode())
            return
        base.cold_owner_held()
        base.create_owned(DONE,json.dumps({
            'status':'FD9_CONTINUOUS_AFTER_CONFIGD_RESTART','schema':1,
            'sha':head,'pid':os.getpid(),'original_fd9_inode':fields['inode'],
            'nonce_sha256':digest,'native_pkg_mutation_invoked':False},
            sort_keys=True).encode())
    finally:
        os.close(9)


def launch(head):
    qualify(head)
    readonly_query_mode()
    late_journal_mode()
    need(base.trusted(ACTION)==action_bytes(head),'CONFIGD_ACTION_CHANGED')
    nonce=ticket(head)
    for p in (SOCKET,PIDFILE,READY,RELEASE,DONE,FAILED,QUERY):
        need(not p.exists() and not p.is_symlink(),
             'ONE_USE_HANDOFF_RESOURCE_ALREADY_PRESENT:'+p.name)
    created,inode=open_original_fd9()
    try:
        proc=subprocess.run(['/usr/sbin/daemon','-f','-P',str(PIDFILE),
                             '/usr/local/bin/python3',str(Path(__file__).resolve()),
                             '--worker',head],capture_output=True,text=True,
                            timeout=20,check=False)
        need(proc.returncode==0,'HANDOFF_DAEMON_START_REFUSED')
        expiry=time.monotonic()+18
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
            while True:
                try:
                    st=SOCKET.lstat()
                    need(stat.S_ISSOCK(st.st_mode) and st.st_uid==0 and
                         stat.S_IMODE(st.st_mode)==0o600,
                         'HANDOFF_SOCKET_INODE_UNTRUSTED')
                    conn.connect(str(SOCKET))
                    break
                except FileNotFoundError:
                    need(time.monotonic()<expiry,'HANDOFF_SOCKET_NOT_READY')
                    time.sleep(.1)
            conn.settimeout(15)
            message=json.dumps({'head':head,'nonce':nonce,
                                'created':created,'inode':inode}).encode()
            conn.sendmsg([message],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,
                                      array.array('i',[9]))])
            ack=conn.recv(120)
            ready=json.loads(base.trusted(READY))
            need(ack==('ACK:'+nonce+':'+str(ready.get('pid'))).encode() and
                 ready.get('status')=='HANDOFF_WORKER_HOLDS_ORIGINAL_FD9' and
                 ready.get('nonce_sha256')==hashlib.sha256(nonce.encode()).hexdigest() and
                 ready.get('original_fd9_inode')==inode and
                 ready.get('created_original_lock_inode') is created,
                 'FD9_HANDOFF_ACK_NOT_QUALIFIED')
            base.check_original_fd9_busy()
        return {'schema':1,'status':'ACKED_CONTINUOUS_FD9_TRANSFER',
                'head':head,'pkg_invoked':False}
    finally:
        os.close(9)


def wait_ready(head,nonce):
    limit=time.monotonic()+45
    while time.monotonic()<limit:
        if FAILED.exists() or FAILED.is_symlink():
            raise base.Refusal('HANDOFF_WORKER_FAILED:'+base.trusted(FAILED,200).decode())
        if READY.exists() or READY.is_symlink():
            x=json.loads(base.trusted(READY))
            need(x.get('status')=='HANDOFF_WORKER_HOLDS_ORIGINAL_FD9' and
                 x.get('sha')==head and x.get('native_pkg_mutation_invoked') is False and
                 x.get('nonce_sha256')==hashlib.sha256(nonce.encode()).hexdigest() and
                 isinstance(x.get('pid'),int) and x['pid']>1 and
                 isinstance(x.get('created_original_lock_inode'),bool) and
                 isinstance(x.get('original_fd9_inode'),int),
                 'FD9_HANDOFF_READY_UNQUALIFIED')
            return x
        time.sleep(.2)
    raise base.Refusal('FD9_HANDOFF_READY_TIMED_OUT')


def execute(head):
    qualify(head)
    query_enabled=readonly_query_mode()
    late_journal=late_journal_mode()
    guest=load('stage0-opnsense-guest-readonly.py')
    installer=load('stage0-opnsense-installed-predecessor.py')
    old=load('stage0-installed-predecessor-readonly.py')
    guard=load('stage0-opnsense-prepkg-readonly.py')
    managed=load('stage2-managed-prepkg-veto-witness.py')
    need(guest.evaluate(guest.observe())['status']==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY','NOT_DISPOSABLE_OPNSENSE')
    need(not ROOT.exists() and not ROOT.is_symlink(),
         'FOREIGN_HANDOFF_DIRECTORY_PRESENT')
    need(not ACTION.exists() and not ACTION.is_symlink(),
         'FOREIGN_CONFIGD_ACTION_PRESENT')
    need(installer.install_and_verify(base.OLD)['status']==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'OLD_INSTALLED_PROVENANCE_UNVERIFIED')
    need(guard.snapshot(base.OLD)['status']=='PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'OLD_OWNER_NOT_COLD_STOPPED')
    before=managed.owner_snapshot(old,guard,base.OLD)
    need(not base.LOCK.is_symlink(),'ORIGINAL_LOCK_PATH_SYMLINK')
    existed=base.LOCK.exists()
    inode=base.LOCK.lstat().st_ino if existed else None
    ROOT.mkdir(mode=0o700)
    nonce=secrets.token_hex(16)
    base.create_owned(TICKET,json.dumps({'head':head,'nonce':nonce}).encode())
    base.create_owned(ACTION,action_bytes(head))
    released=False
    journal_verified=False
    journal=None
    journal_parent_created=False
    try:
        base.run(['/usr/sbin/service','configd','restart'],45)
        actions=base.run(['/usr/local/sbin/configctl','configd','actions'],15)
        need('zapret2_stage3_handoff_ci' in actions,'HANDOFF_ACTION_NOT_REGISTERED')
        output=base.run(['/usr/local/sbin/configctl',
                         'zapret2_stage3_handoff_ci','launch'],35)
        need('ACKED_CONTINUOUS_FD9_TRANSFER' in output,
             'CONFIGD_DID_NOT_COMPLETE_ATOMIC_HANDOFF')
        ready=wait_ready(head,nonce)
        if query_enabled:
            attestation=json.loads(base.trusted(QUERY))
            need(attestation.get('status')=='NATIVE_PKG_QUERY_UNDER_TRANSFERRED_FD9' and
                 attestation.get('sha')==head and
                 attestation.get('pid')==ready['pid'] and
                 attestation.get('original_fd9_inode')==ready['original_fd9_inode'] and
                 attestation.get('nonce_sha256')==ready['nonce_sha256'] and
                 attestation.get('native_pkg_read_only_query_invoked') is True and
                 attestation.get('native_mutating_pkg_invoked') is False,
                 'NATIVE_PKG_QUERY_FD9_ATTESTATION_UNQUALIFIED')
        need(ready['created_original_lock_inode'] is (not existed) and
             (inode is None or ready['original_fd9_inode']==inode),
             'HANDOFF_ORIGINAL_INODE_CHANGED')
        base.check_original_fd9_busy()
        base.run(['/usr/sbin/service','configd','restart'],45)
        base.check_original_fd9_busy()
        need(wait_ready(head,nonce)==ready,'WORKER_IDENTITY_DRIFT_AFTER_RELOAD')
        if late_journal:
            # Inject only a known-invalid, test-owned journal in disposable VM,
            # AFTER genuine read-only pkg query/ACK, BEFORE final pkg dispatch.
            journal=load('stage0-opnsense-old-unknown-owner.py')
            journal.ensure_no_journal()
            journal_parent_created=journal.create_disposable_root_if_absent()
            need(journal.create_owned_corrupt_journal() is True,
                 'KNOWN_INVALID_LATE_JOURNAL_NOT_CREATED')
            journal.verify_corrupt_journal()
            base.check_original_fd9_busy()
        base.create_owned(RELEASE,b'RELEASE_TEST_ONLY')
        released=True
        done=json.loads(base.wait_file(DONE,45))
        if late_journal:
            need(done.get('status')=='REFUSED_LATE_JOURNAL_BEFORE_MUTATING_PKG' and
                 done.get('real_owner_check_invoked') is True and
                 done.get('native_mutating_pkg_dispatch_reached') is False and
                 done.get('reason')=='REAL_ORIGINAL_FD9_JOURNAL_VETO' and
                 done.get('pid')==ready['pid'] and done.get('sha')==head and
                 done.get('original_fd9_inode')==ready['original_fd9_inode'] and
                 done.get('nonce_sha256')==ready['nonce_sha256'] and
                 done.get('native_mutating_pkg_invoked') is False,
                 'LATE_OWNER_REACHED_PKG_OR_WRONG_VETO')
            journal.verify_corrupt_journal()
            journal_verified=True
        else:
            need(done.get('status')=='FD9_CONTINUOUS_AFTER_CONFIGD_RESTART' and
                 done.get('pid')==ready['pid'] and done.get('sha')==head and
                 done.get('original_fd9_inode')==ready['original_fd9_inode'] and
                 done.get('nonce_sha256')==ready['nonce_sha256'] and
                 done.get('native_pkg_mutation_invoked') is False,
                 'WORKER_DID_NOT_COMPLETE_CONTINUOUS_FD9_SESSION')
    finally:
        if not released and not RELEASE.exists() and not RELEASE.is_symlink():
            base.create_owned(RELEASE,b'RELEASE_TEST_ONLY')
        # Never remove a late journal on an unproven worker verdict: unknown
        # state must remain visible, not become a false clean owner.
        if late_journal and journal_verified:
            journal.remove_only_owned_journal()
            if journal_parent_created:
                parent=journal.JOURNAL.parent
                need(parent.is_dir() and not parent.is_symlink() and
                     stat.S_IMODE(parent.stat().st_mode)==0o700 and
                     not tuple(parent.iterdir()),
                     'OWNED_JOURNAL_PARENT_CHANGED_NO_DELETE')
                parent.rmdir()
        need(base.trusted(ACTION)==action_bytes(head),
             'CANNOT_CLEAN_CHANGED_CONFIGD_ACTION')
        ACTION.unlink()
        base.run(['/usr/sbin/service','configd','restart'],45)
    need(managed.owner_snapshot(old,guard,base.OLD)==before,
         'HANDOFF_CHANGED_ORIGINAL_PKG_CONFIG_PROCESS_IPFW')
    for p in ((TICKET,READY,DONE,RELEASE,QUERY) if query_enabled
              else (TICKET,READY,DONE,RELEASE)):
        need(base.trusted(p) is not None,'MISSING_OWNED_TEST_FILE')
        p.unlink()
    expiry=time.monotonic()+8
    while PIDFILE.exists() and time.monotonic()<expiry:
        time.sleep(.2)
    need(not PIDFILE.exists() and not PIDFILE.is_symlink(),
         'DAEMON_SUPERVISOR_PIDFILE_REMAINED')
    need(SOCKET.is_socket() and not SOCKET.is_symlink(),
         'HANDOFF_SOCKET_MISSING_OR_CHANGED')
    SOCKET.unlink()
    ROOT.rmdir()
    if not existed:
        fd=os.open(base.LOCK,os.O_RDWR|os.O_NOFOLLOW)
        try:
            st=os.fstat(fd)
            need(st.st_uid==0 and st.st_nlink==1 and
                 st.st_ino==ready['original_fd9_inode'] and
                 base.LOCK.lstat().st_ino==st.st_ino,
                 'CREATED_ORIGINAL_LOCK_INODE_CHANGED')
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise base.Refusal('ORIGINAL_LOCK_STILL_BUSY_NO_UNLINK') from None
            base.LOCK.unlink()
        finally:
            os.close(fd)
        need(not base.LOCK.exists() and not base.LOCK.is_symlink(),
             'ORIGINAL_LOCK_ABSENCE_NOT_RESTORED')
    else:
        need(base.LOCK.is_file() and base.LOCK.lstat().st_ino==inode,
             'PREEXISTING_ORIGINAL_LOCK_CHANGED')
    return {'schema':1,'status':(
                'PASS_TEST_ONLY_CONFIGD_FD9_LATE_JOURNAL_VETO_BEFORE_PKG'
                if late_journal else
                'PASS_TEST_ONLY_CONFIGD_FD9_NATIVE_PKG_READ_ONLY_QUERY'
                if query_enabled else
                'PASS_TEST_ONLY_CONFIGD_SCM_RIGHTS_CONTINUOUS_FD9'),
            'late_owner_refused_before_pkg':late_journal,
            'native_pkg_read_only_query_under_detached_fd9':query_enabled,
            'configd_to_detached_fd9_handoff_without_unlock_gap':True,
            'worker_survives_configd_restart_with_same_pid':True,
            'old_package_config_process_ipfw_unchanged':True,
            'native_mutating_pkg_invoked':False,
            'stock_web_firmware_or_direct_root_pkg_protected':False,
            'final_owner_check_to_pkg_race_closed':False,
            'lh08_ac11_accepted':False,'owner_appliance_modified':False}


def main():
    try:
        need(len(sys.argv)==2 or
             (len(sys.argv)==3 and sys.argv[1] in ('--launch','--worker')),
             'EXACT_DISPOSABLE_ARGUMENTS_REQUIRED')
        head=sys.argv[1] if len(sys.argv)==2 else sys.argv[2]
        result=(execute(head) if len(sys.argv)==2 else
                launch(head) if sys.argv[1]=='--launch' else worker(head))
        if result is not None:
            print(PREFIX+json.dumps(result,sort_keys=True),flush=True)
        return 0
    except (base.Refusal,OSError,ValueError,KeyError,TypeError,
            subprocess.SubprocessError,socket.timeout) as exc:
        reason=re.sub('[^A-Za-z0-9_.:-]','_',str(exc)[:180])
        if len(sys.argv)==3 and sys.argv[1]=='--worker':
            try:
                base.create_owned(FAILED,reason.encode('ascii'))
            except (OSError,base.Refusal):
                pass
        print(PREFIX+'REFUSED:'+reason,file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':
    sys.exit(main())
