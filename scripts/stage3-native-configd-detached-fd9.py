#!/usr/local/bin/python3
"""One-use OPNsense configd -> FreeBSD daemon -> original FD9 survival witness.

NO modifying native pkg. A fixed, root-owned transient configd action starts
a detached supervisor whose child holds the authentic original FD9 and rechecks
cold owner. The controller restarts configd during that lock, checks external
busy refusal and releases the child through an exact test-owned marker.
This does not prove admission-to-pkg atomicity or protect stock firmware/Web.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
OLD=Path('/tmp/os-zapret2-restyle-0.6.2_1.pkg')
ACTION=Path('/usr/local/opnsense/service/conf/actions.d/actions_zapret2_stage3_detached_ci.conf')
PIDFILE=Path('/tmp/zapret2-stage3-detached-supervisor-ci.pid')
READY=Path('/tmp/zapret2-stage3-detached-ready-ci.json')
RELEASE=Path('/tmp/zapret2-stage3-detached-release-ci')
DONE=Path('/tmp/zapret2-stage3-detached-done-ci.json')
FAILED=Path('/tmp/zapret2-stage3-detached-failed-ci.category')
LOCK=Path('/var/run/zapret2-lifecycle.lock')
PREFIX='STAGE3_CONFIGD_DETACHED_FD9='
SHA_OLD='1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f'


class Refusal(Exception):
    pass


def need(ok,reason):
    if not ok:
        raise Refusal(reason)


def load(filename):
    spec=importlib.util.spec_from_file_location(
        filename.replace('-','_').replace('.','_'),HERE/filename)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def qualify(head):
    need(os.geteuid()==0 and os.uname().sysname=='FreeBSD' and
         os.uname().machine=='amd64' and
         os.environ.get('GITHUB_ACTIONS')=='true' and
         os.environ.get('ZAPRET2_STAGE3_DETACHED_FD9')=='1',
         'DISPOSABLE_OPNSENSE_ROOT_CI_REQUIRED')
    need(re.fullmatch(r'[a-f0-9]{40}',head or '') is not None and
         head==os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA'),
         'EXACT_NATIVE_PROJECT_HEAD_REQUIRED')
    old=load('stage0-installed-predecessor-readonly.py')
    need(OLD.is_file() and not OLD.is_symlink() and
         old.digest(OLD.read_bytes())==SHA_OLD,
         'AUTHENTIC_HISTORICAL_OLD_ARCHIVE_REQUIRED')


def run(args,seconds=30):
    p=subprocess.run(args,text=True,capture_output=True,check=False,
                     timeout=seconds)
    need(p.returncode==0,'TEST_NATIVE_COMMAND_REFUSED_'+str(p.returncode)+
         ':'+re.sub('[^A-Za-z0-9_.:-]','_',p.stderr[-90:]),
         )
    return p.stdout


def create_owned(path,data):
    need(isinstance(data,bytes) and len(data)<=1024,
         'TEST_RESULT_UNBOUNDED')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def trusted(path,maxsize=1024):
    need(path.is_file() and not path.is_symlink(),
         'TEST_OWNED_FILE_NOT_REGULAR:'+path.name)
    st=path.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid==0 and st.st_nlink==1
         and stat.S_IMODE(st.st_mode)==0o600 and 0<=st.st_size<=maxsize,
         'TEST_OWNED_FILE_INODE_UNTRUSTED:'+path.name)
    return path.read_bytes()


def wait_file(path,limit=45):
    expiry=time.monotonic()+limit
    while time.monotonic()<expiry:
        if path.exists() or path.is_symlink():
            return trusted(path)
        if path==READY and (FAILED.exists() or FAILED.is_symlink()):
            reason=trusted(FAILED,200).decode('ascii','replace').strip()
            need(re.fullmatch(r'[A-Za-z0-9_.:-]{3,190}',reason) is not None,
                 'DETACHED_WORKER_FAILURE_UNTRUSTED')
            raise Refusal('DETACHED_WORKER_DID_NOT_REACH_READY:'+reason)
        time.sleep(.2)
    raise Refusal('DETACHED_WORKER_RESULT_TIMED_OUT:'+path.name)


def check_original_fd9_busy():
    locked=load('stage2-prepkg-locked-cold-revalidation.py')
    need(locked.LOCK==LOCK,'WRONG_ORIGINAL_FD9_PATH')
    p=subprocess.run(['/bin/sh','-c',locked.CHALLENGER,'sh',str(LOCK)],
                     capture_output=True,text=True,timeout=8,check=False)
    need(p.returncode==75,'INDEPENDENT_ORIGINAL_FD9_NOT_BUSY:'+
         str(p.returncode))


def cold_owner_held():
    locked=load('stage2-prepkg-locked-cold-revalidation.py')
    locked.check_fd9()
    report=locked.inside_lock(OLD)
    need(report.get('status')=='PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC' and
         report.get('native_pkg_mutation_invoked') is False,
         'ORIGINAL_FD9_COLD_OWNER_UNQUALIFIED')
    locked.check_fd9()


def worker(head):
    qualify(head)
    # Authentic STOPPED predecessor may never have opened its FD9 path.
    # Match historical "exec 9>original-lock" by creating only that inode,
    # exclusive/no-symlink, with no rename, truncation or replacement.
    created=False
    try:
        fd=os.open(LOCK,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        created=True
    except FileExistsError:
        fd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW)
    old=LOCK.lstat()
    need(old.st_uid==0 and old.st_nlink==1 and stat.S_ISREG(old.st_mode)
         and old.st_dev==os.fstat(fd).st_dev
         and old.st_ino==os.fstat(fd).st_ino,
         'ORIGINAL_FD9_UNTRUSTED')
    # Put BSD flock on authentic descriptor *9*, as used by the old service.
    try:
        os.dup2(fd,9)
        if fd!=9:
            os.close(fd)
        need(os.fstat(9).st_ino==old.st_ino and
             os.fstat(9).st_dev==old.st_dev,'FD9_NOT_HISTORICAL_INODE')
        try:
            fcntl.flock(9,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal('ORIGINAL_FD9_BUSY_NO_WORKER_ADMISSION') from None
        cold_owner_held()
        create_owned(READY,json.dumps({
            'status':'HELD_AUTHENTIC_FD9_IN_DETACHED_WORKER',
            'pid':os.getpid(),'ppid':os.getppid(),
            'original_fd9_held':True,'cold_old_owner':True,
            'created_original_lock_inode':created,
            'original_fd9_inode':old.st_ino,
            'native_pkg_mutation_invoked':False,'schema':1,
            'sha':head},sort_keys=True).encode())
        wait_file(RELEASE,55)
        need(trusted(RELEASE)==b'RELEASE_TEST_ONLY',
             'DETACHED_RELEASE_MARKER_UNTRUSTED')
        cold_owner_held()
        create_owned(DONE,json.dumps({
            'status':'HELD_FD9_THROUGH_CONFIGD_RESTART',
            'pid':os.getpid(),'old_pkg_unchanged':True,
            'created_original_lock_inode':created,
            'original_fd9_inode':old.st_ino,
            'native_pkg_mutation_invoked':False,'schema':1,
            'sha':head},sort_keys=True).encode())
    finally:
        try:
            os.close(9)
        except OSError:
            pass


def action_bytes(head):
    path=str(Path(__file__).resolve())
    need(re.fullmatch(r'/[a-zA-Z0-9_./-]+',path) is not None,
         'TEST_ACTION_SCRIPT_PATH_UNTRUSTED')
    return ('[launch]\n'
            'command:/usr/bin/env GITHUB_ACTIONS=true '
            'ZAPRET2_STAGE3_DETACHED_FD9=1 '
            'ZAPRET2_STAGE2_LOCKED_COLD_REVALIDATION=1 '
            'ZAPRET2_NATIVE_PROJECT_SHA='+head+' '
            '/usr/local/bin/python3 '+path+' --launch '+head+'\n'
            'parameters:\n'
            'type:script_output\n'
            'message:One-use detached FD9 supervisor from configd\n'
            'timeout:30\n').encode()


def launch(head):
    qualify(head)
    need(trusted(ACTION)==action_bytes(head),
         'ACTION_CHANGED_DURING_REAL_CONFIGD_CALL')
    need(not PIDFILE.exists() and not PIDFILE.is_symlink() and
         not READY.exists() and not READY.is_symlink() and
         not RELEASE.exists() and not RELEASE.is_symlink() and
         not DONE.exists() and not DONE.is_symlink() and
         not FAILED.exists() and not FAILED.is_symlink(),
         'ONE_USE_SUPERVISOR_RESOURCES_ALREADY_PRESENT')
    # Real FreeBSD daemon(8) with independent supervisor PID file; no pkg.
    p=subprocess.run(['/usr/sbin/daemon','-f','-P',str(PIDFILE),
                      '/usr/local/bin/python3',str(Path(__file__).resolve()),
                      '--worker',head],
                     capture_output=True,text=True,timeout=20,check=False)
    need(p.returncode==0,'DETACHED_DAEMON_START_REFUSED_'+str(p.returncode))
    return {'schema':1,'status':'DETACHED_DAEMON_LAUNCH_RETURNED',
            'pkg_invoked':False,'head':head}


def inspect_ready(blob,head):
    d=json.loads(blob)
    need(isinstance(d,dict) and
         d.get('status')=='HELD_AUTHENTIC_FD9_IN_DETACHED_WORKER' and
         d.get('original_fd9_held') is True and
         d.get('cold_old_owner') is True and
         d.get('native_pkg_mutation_invoked') is False and
         d.get('sha')==head and
         isinstance(d.get('pid'),int) and d['pid']>1 and
         isinstance(d.get('ppid'),int) and d['ppid']>1 and
         isinstance(d.get('created_original_lock_inode'),bool) and
         isinstance(d.get('original_fd9_inode'),int) and
         d['original_fd9_inode']>0,
         'DETACHED_OLD_FD9_READY_NOT_QUALIFIED')
    return d


def execute(head):
    qualify(head)
    guest=load('stage0-opnsense-guest-readonly.py')
    installer=load('stage0-opnsense-installed-predecessor.py')
    old=load('stage0-installed-predecessor-readonly.py')
    guard=load('stage0-opnsense-prepkg-readonly.py')
    managed=load('stage2-managed-prepkg-veto-witness.py')
    need(guest.evaluate(guest.observe())['status']==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY',
         'DISPOSABLE_OPNSENSE_IDENTITY_UNQUALIFIED')
    for p in (ACTION,PIDFILE,READY,RELEASE,DONE,FAILED):
        need(not p.exists() and not p.is_symlink(),
             'PREEXISTING_TEST_RESOURCE_REFUSE:'+p.name)
    need(installer.install_and_verify(OLD)['status']==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'PUBLISHED_OLD_PACKAGE_INSTALL_PROVENANCE_UNVERIFIED')
    need(guard.snapshot(OLD)['status']=='PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_OLD_NOT_STOPPED_COLD')
    baseline=managed.owner_snapshot(old,guard,OLD)
    need(not LOCK.is_symlink(),'OLD_LOCK_PATH_SYMLINK_BEFORE_LAUNCH')
    lock_preexisting=LOCK.exists()
    prior_lock_inode=LOCK.lstat().st_ino if lock_preexisting else None
    create_owned(ACTION,action_bytes(head))
    released=False
    try:
        run(['/usr/sbin/service','configd','restart'],45)
        actions=run(['/usr/local/sbin/configctl','configd','actions'],15)
        need('zapret2_stage3_detached_ci' in actions,
             'REAL_CONFIGD_TEMPORARY_ACTION_UNREGISTERED')
        output=run(['/usr/local/sbin/configctl',
                    'zapret2_stage3_detached_ci','launch'],35)
        need('DETACHED_DAEMON_LAUNCH_RETURNED' in output,
             'CONFIGCTL_DID_NOT_OBSERVABLY_LAUNCH_DAEMON')
        ready=inspect_ready(wait_file(READY,45),head)
        check_original_fd9_busy()
        # The worker and FD9 must outlive the old configd worker; a genuine
        # configd restart occurs while the external root-held FD9 is busy.
        run(['/usr/sbin/service','configd','restart'],45)
        check_original_fd9_busy()
        need(inspect_ready(trusted(READY),head)==ready,
             'DETACHED_WORKER_READY_IDENTITY_CHANGED_AFTER_CONFIGD_RELOAD')
        create_owned(RELEASE,b'RELEASE_TEST_ONLY')
        released=True
        done=json.loads(wait_file(DONE,45))
        need(done.get('status')=='HELD_FD9_THROUGH_CONFIGD_RESTART' and
             done.get('pid')==ready['pid'] and
             done.get('sha')==head and
             done.get('created_original_lock_inode')==
                 ready['created_original_lock_inode'] and
             done.get('original_fd9_inode')==ready['original_fd9_inode'] and
             ready['created_original_lock_inode'] is (not lock_preexisting) and
             (prior_lock_inode is None or
              prior_lock_inode==ready['original_fd9_inode']) and
             done.get('native_pkg_mutation_invoked') is False,
             'DETACHED_WORKER_DID_NOT_COMPLETE_SAME_LOCKED_SESSION')
    finally:
        # Cooperative release only: never kill an unqualified PID from
        # untrusted pidfile content. The one-use VM is destroyed on failure.
        if not released and not RELEASE.exists() and not RELEASE.is_symlink():
            create_owned(RELEASE,b'RELEASE_TEST_ONLY')
        try:
            need(trusted(ACTION)==action_bytes(head),
                 'FOREIGN_TEST_ACTION_CANNOT_REMOVE')
            ACTION.unlink()
            run(['/usr/sbin/service','configd','restart'],45)
        except Exception as exc:
            raise Refusal('DISPOSABLE_CONFIGD_ACTION_CLEANUP_UNVERIFIED:'+
                          str(exc)[:180]) from None
    need(managed.owner_snapshot(old,guard,OLD)==baseline,
         'DETACHED_WORKER_MUTATED_INSTALLED_PACKAGE_FILES_CONFIG_PROCESS_IPFW')
    need(trusted(READY) and trusted(DONE) and
         trusted(RELEASE)==b'RELEASE_TEST_ONLY',
         'TEST_ONLY_RESULT_FILES_UNTRUSTED')
    for p in (READY,DONE,RELEASE):
        p.unlink()
    # pidfile(3) supervisor owns PIDFILE and must remove it on normal exit.
    expiry=time.monotonic()+8
    while time.monotonic()<expiry and PIDFILE.exists():
        time.sleep(.2)
    need(not PIDFILE.exists() and not PIDFILE.is_symlink(),
         'DETACHED_SUPERVISOR_PIDFILE_STILL_ACTIVE')
    if not lock_preexisting:
        # Only the exact inode created in this disposable test may be
        # removed; lock it independently before unlink, never by PID.
        need(LOCK.is_file() and not LOCK.is_symlink(),
             'CREATED_TEST_ORIGINAL_LOCK_NOT_PRESENT')
        fd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW)
        try:
            st=os.fstat(fd)
            need(st.st_uid==0 and st.st_nlink==1 and
                 st.st_ino==ready['original_fd9_inode'] and
                 st.st_dev==LOCK.lstat().st_dev,
                 'CREATED_TEST_ORIGINAL_LOCK_INODE_CHANGED')
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refusal('CREATED_TEST_LOCK_STILL_BUSY_NO_UNLINK') from None
            LOCK.unlink()
        finally:
            os.close(fd)
        need(not LOCK.exists() and not LOCK.is_symlink(),
             'ORIGINAL_LOCK_INITIAL_ABSENCE_NOT_RESTORED')
    else:
        need(LOCK.is_file() and not LOCK.is_symlink() and
             LOCK.lstat().st_ino==prior_lock_inode,
             'ORIGINAL_LOCK_EXISTING_INODE_CHANGED')
    return {'schema':1,
            'status':'PASS_TEST_ONLY_CONFIGD_INDEPENDENT_FD9_SURVIVED_RELOAD',
            'published_old_pkgdb_files_config_process_ipfw_unchanged':True,
            'real_configctl_action_registered_and_invoked':True,
            'real_daemon_supervisor_launched':True,
            'same_detached_worker_held_authentic_fd9_before_after_reload':True,
            'independent_busy_fd9_refusal_verified_twice':True,
            'test_only_action_and_markers_removed':True,
            'native_mutating_pkg_invoked':False,
            'actual_pkg_old_new_hooks_exercised_here':False,
            'unbroken_configd_to_fd9_handoff_proven':False,
            'post_final_owner_check_race_closed':False,
            'supported_GUI_or_stock_Web_updater_implemented':False,
            'lh08_ac11_accepted':False,
            'owner_appliance_modified':False}


def main():
    try:
        need((len(sys.argv)==2) or
             (len(sys.argv)==3 and sys.argv[1] in ('--launch','--worker')),
             'EXACT_DISPOSABLE_ARGS_REQUIRED')
        result=(execute(sys.argv[1]) if len(sys.argv)==2 else
                launch(sys.argv[2]) if sys.argv[1]=='--launch'
                else worker(sys.argv[2]))
        if result is not None:
            print(PREFIX+json.dumps(result,sort_keys=True),flush=True)
        return 0
    except (Refusal,OSError,ValueError,KeyError,TypeError,
            subprocess.SubprocessError) as exc:
        # Only a bounded category is visible; never dump arbitrary files.
        reason=re.sub(r'[^A-Za-z0-9_.:-]','_',str(exc)[:180])
        if len(sys.argv)==3 and sys.argv[1]=='--worker':
            try:
                create_owned(FAILED,reason.encode('ascii'))
            except (OSError,Refusal):
                pass
        print(PREFIX+'REFUSED:'+reason,file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':
    sys.exit(main())
