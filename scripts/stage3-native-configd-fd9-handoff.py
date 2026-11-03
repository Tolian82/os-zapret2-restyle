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
PREPKG_READY=ROOT/'native-prepkg-ready'
PREPKG_RESUME=ROOT/'native-prepkg-resume'
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


def native_pkg_mode():
    """Exact one-shot disposable native pkg mutation under authenticated old FD9."""
    value=os.environ.get('ZAPRET2_STAGE3_NATIVE_MUTATING_PKG','')
    need(value in ('','1'),'NATIVE_MUTATING_PKG_MODE_INVALID')
    if value:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI')=='1' and
             os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK')=='1' and
             os.environ.get('ZAPRET2_NATIVE_BUILD_CI')=='1' and
             os.environ.get('ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF')=='1' and
             readonly_query_mode() and not late_journal_mode() and not fault_mode(),
             'NATIVE_MUTATING_PKG_NOT_DISPOSABLE_OR_MODE_CONFLICT')
    return value=='1'


def native_late_journal_mode():
    """One-use authentic dispatch negative under original FD9, never product."""
    value=os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL','')
    need(value in ('','1'),'NATIVE_LATE_JOURNAL_MODE_INVALID')
    if value:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL_CI')=='1' and
             native_pkg_mode() and not late_journal_mode() and not fault_mode(),
             'NATIVE_LATE_JOURNAL_NOT_DISPOSABLE')
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
    if native_late_journal_mode():
        extra+=('ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL=1 '
                'ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL_CI=1 ')
    if native_pkg_mode():
        extra+=('ZAPRET2_STAGE3_NATIVE_MUTATING_PKG=1 '
                'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI=1 '
                'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK=1 '
                'ZAPRET2_NATIVE_BUILD_CI=1 '
                'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF=1 ')
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


def load_product_handoff():
    """Use product source shared with the future installed supervisor."""
    path=HERE.parent/'src/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_handoff.py'
    need(path.is_file() and not path.is_symlink(),
         'PRODUCT_NATIVE_FD9_TRANSPORT_MISSING')
    spec=importlib.util.spec_from_file_location('native_pkg_handoff',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accept_rights(conn,head):
    product=load_product_handoff()
    try:
        fd,fields=product.receive_original_fd9(
            conn,head=head,nonce=ticket(head))
    except product.HandoffRefusal as exc:
        raise base.Refusal(str(exc)) from None
    try:
        os.dup2(fd,9)
        need(os.fstat(9).st_ino==fields['inode'],'FD9_DUPLICATION_FAILED')
        # No ACK or pkg before the real historical old-owner revalidation.
        base.cold_owner_held()
        return fields
    finally:
        if fd!=9:
            os.close(fd)


def worker(head):
    qualify(head)
    fault=fault_mode()
    query_enabled=readonly_query_mode()
    late_journal=late_journal_mode()
    pkg_enabled=native_pkg_mode()
    native_late=native_late_journal_mode()
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
        if pkg_enabled:
            # Exactly one configd transferred FD9 owns the complete native
            # replacement; no controller-side pkg and no production hook edit.
            signed=json.loads(base.trusted(TICKET))
            need(set(signed)=={'head','nonce','package_path','package_sha256',
                                'revision'} and signed['head']==head and
                 signed['nonce']==fields['nonce'],
                 'NATIVE_PKG_ROOT_TICKET_CHANGED_AFTER_ACK')
            os.environ['ZAPRET2_STAGE3_NATIVE_PKG_PATH']=signed['package_path']
            transaction=load('stage3-native-configd-mutating-pkg.py')
            try:
                verdict=transaction.native_transaction(
                    base.OLD,signed['package_sha256'],signed['revision'],fields['inode'],
                    late_journal_fault=native_late)
            except Exception as exc:
                # An interrupted real pkg has UNKNOWN state, never PASS.
                raise base.Refusal('NATIVE_MUTATING_PKG_WORKER_FAILED:'+
                                   type(exc).__name__+':'+str(exc)[:90]) from None
            base.create_owned(DONE,json.dumps({
                **verdict,'sha':head,'pid':os.getpid(),
                'original_fd9_inode':fields['inode'],
                'nonce_sha256':digest,
                'native_mutating_pkg_invoked':not native_late},sort_keys=True).encode())
            return
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
    native_pkg_mode()
    native_late_journal_mode()
    need(base.trusted(ACTION)==action_bytes(head),'CONFIGD_ACTION_CHANGED')
    nonce=ticket(head)
    for p in (SOCKET,PIDFILE,READY,RELEASE,DONE,FAILED,QUERY,PREPKG_READY,PREPKG_RESUME):
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


def wait_native_pkg_done(limit=270):
    """Bounded success/error witness; fail immediately on worker failure."""
    expiry=time.monotonic()+limit
    while time.monotonic()<expiry:
        if FAILED.exists() or FAILED.is_symlink():
            raise base.Refusal('NATIVE_PKG_WORKER_FAILED_NO_SUCCESS:'+
                               base.trusted(FAILED,200).decode('ascii','replace'))
        if DONE.exists() or DONE.is_symlink():
            return base.trusted(DONE,3000)
        time.sleep(.2)
    raise base.Refusal('NATIVE_PKG_WORKER_RESULT_TIMED_OUT_UNKNOWN_STATE')


def execute(head):
    qualify(head)
    query_enabled=readonly_query_mode()
    late_journal=late_journal_mode()
    pkg_enabled=native_pkg_mode()
    native_late=native_late_journal_mode()
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
    native_archive=None
    native_archive_sha=None
    native_revision=None
    if pkg_enabled:
        stopped=load('stage2-opnsense-real-native-stopped-upgrade.py')
        clean=stopped.clean
        native=stopped.native
        native.gate()
        clean.plugin_absent()
        stopped.check_old_archive(base.OLD)
        built=native.build()
        need(built.get('status')=='PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY' and
             built.get('project_sha')==head,
             'OFFICIAL_NATIVE_CANDIDATE_BUILD_UNQUALIFIED')
        native_archive=native.ROOT/built['output']
        product_rel='opnsense/scripts/OPNsense/Zapret/backend/native_pkg_handoff.py'
        need(native.archived_file(native_archive,product_rel)==
             (HERE.parent/'src'/product_rel).read_bytes(),
             'OFFICIAL_NATIVE_ARCHIVE_FD9_TRANSPORT_BYTES_UNQUALIFIED')
        native_archive_sha=built['real_native_pkg']['sha256']
        native_revision=native.REVISION
        need(native_archive.is_file() and not native_archive.is_symlink() and
             clean.digest(native_archive)==native_archive_sha,
             'OFFICIAL_NATIVE_CANDIDATE_ARCHIVE_CHANGED')
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
    ticket_data={'head':head,'nonce':nonce}
    if pkg_enabled:
        ticket_data.update(package_path=str(native_archive),
                           package_sha256=native_archive_sha,
                           revision=native_revision)
    base.create_owned(TICKET,json.dumps(ticket_data,sort_keys=True).encode())
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
        if native_late:
            # Initial real old-owner admission has passed under original FD9.
            armed=json.loads(base.wait_file(PREPKG_READY,55))
            need(armed.get('sha')==head and armed.get('pid')==ready['pid'] and
                 armed.get('original_fd9_inode')==ready['original_fd9_inode'] and
                 armed.get('nonce_sha256')==ready['nonce_sha256'],
                 'NATIVE_PKG_PRE_DISPATCH_BARRIER_NOT_AUTHENTIC')
            journal=load('stage0-opnsense-old-unknown-owner.py')
            journal.ensure_no_journal()
            journal_parent_created=journal.create_disposable_root_if_absent()
            need(journal.create_owned_corrupt_journal() is True,
                 'KNOWN_INVALID_NATIVE_LATE_JOURNAL_NOT_CREATED')
            journal.verify_corrupt_journal()
            base.create_owned(PREPKG_RESUME,
                              b'RESUME_TEST_ONLY_AFTER_CORRUPT_JOURNAL')
        done=json.loads(wait_native_pkg_done() if pkg_enabled
                        else base.wait_file(DONE,45))
        if native_late:
            need(done.get('status')=='REFUSED_TEST_ONLY_REAL_NATIVE_DISPATCH_LATE_JOURNAL' and
                 done.get('sha')==head and done.get('pid')==ready['pid'] and
                 done.get('original_fd9_inode')==ready['original_fd9_inode'] and
                 done.get('nonce_sha256')==ready['nonce_sha256'] and
                 done.get('real_owner_check_invoked') is True and
                 done.get('native_mutating_pkg_dispatch_reached') is False and
                 done.get('native_mutating_pkg_invoked') is False and
                 done.get('original_fd9_retained_at_refusal') is True and
                 done.get('lh08_ac11_accepted') is False,
                 'REAL_NATIVE_PKG_LATE_REFUSAL_NOT_QUALIFIED')
            journal.verify_corrupt_journal()
            journal_verified=True
        elif pkg_enabled:
            expected_identity='os-zapret2-restyle|0.6.2_'+native_revision
            need(done.get('status')=='PASS_TEST_ONLY_CONFIGD_NATIVE_PKG_UNDER_ORIGINAL_FD9' and
                 done.get('sha')==head and done.get('pid')==ready['pid'] and
                 done.get('original_fd9_inode')==ready['original_fd9_inode'] and
                 done.get('nonce_sha256')==ready['nonce_sha256'] and
                 done.get('native_mutating_pkg_invoked') is True and
                 done.get('real_pkg_exit')==0 and
                 done.get('installed_native_package_identity')==expected_identity and
                 done.get('exact_native_successor_sha256')==native_archive_sha and
                 done.get('original_fd9_retained_during_actual_pkg') is True and
                 done.get('installed_files_modes_verified') is True and
                 done.get('foreign_config_values_preserved') is True and
                 done.get('lh08_ac11_accepted') is False,
                 'NATIVE_CONFIGD_PKG_OR_OWNERSHIP_ATTESTATION_UNQUALIFIED')
        elif late_journal:
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
        if (late_journal or native_late) and journal_verified:
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
    if pkg_enabled and not native_late:
        need(load('stage2-opnsense-real-unsafe-owner-replacement.py').installed_identity()
             =='os-zapret2-restyle|0.6.2_'+native_revision,
             'POST_CONFIGD_NATIVE_PKG_INSTALLED_IDENTITY_DRIFT')
        need(load('stage2-opnsense-real-native-clean-install.py').digest(native_archive)
             ==native_archive_sha,
             'POST_CONFIGD_NATIVE_PKG_ARCHIVE_DRIFT')
    else:
        need(managed.owner_snapshot(old,guard,base.OLD)==before,
             'HANDOFF_CHANGED_ORIGINAL_PKG_CONFIG_PROCESS_IPFW')
    for p in ((TICKET,READY,DONE,RELEASE,QUERY,PREPKG_READY,PREPKG_RESUME)
              if native_late else
              (TICKET,READY,DONE,RELEASE,QUERY) if query_enabled else
              (TICKET,READY,DONE,RELEASE)):
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
                'PASS_TEST_ONLY_CONFIGD_NATIVE_LATE_JOURNAL_NO_PKG'
                if native_late else
                'PASS_TEST_ONLY_CONFIGD_NATIVE_PKG_UNDER_ORIGINAL_FD9'
                if pkg_enabled else
                'PASS_TEST_ONLY_CONFIGD_FD9_LATE_JOURNAL_VETO_BEFORE_PKG'
                if late_journal else
                'PASS_TEST_ONLY_CONFIGD_FD9_NATIVE_PKG_READ_ONLY_QUERY'
                if query_enabled else
                'PASS_TEST_ONLY_CONFIGD_SCM_RIGHTS_CONTINUOUS_FD9'),
            'late_owner_refused_before_pkg':late_journal or native_late,
            'native_pkg_read_only_query_under_detached_fd9':query_enabled,
            'native_mutating_pkg_under_detached_fd9':pkg_enabled and not native_late,
            'native_successor_sha256':native_archive_sha if pkg_enabled else None,
            'configd_to_detached_fd9_handoff_without_unlock_gap':True,
            'worker_survives_configd_restart_with_same_pid':True,
            'old_package_config_process_ipfw_unchanged':not pkg_enabled or native_late,
            'native_mutating_pkg_invoked':pkg_enabled and not native_late,
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
