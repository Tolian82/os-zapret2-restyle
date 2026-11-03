#!/usr/local/bin/python3
"""One-use disposable native pkg under configd-transferred historical FD9.

NOT an installable updater, stock firmware hook, or production service.
The authentic old four hooks and supported package files are unchanged.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
NAME='os-zapret2-restyle'


class Refusal(Exception):
    pass


def need(value,reason):
    if not value:
        raise Refusal(reason)


def load(name):
    spec=importlib.util.spec_from_file_location(
        name.replace('-','_').replace('.','_'),HERE/name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_candidate(path,digest,revision):
    """Preflight exact official-native-built archive; never trust a request path."""
    need(isinstance(revision,str) and revision.isdecimal() and
         re.fullmatch('[0-9a-f]{64}',digest or '') is not None,
         'MUTATING_NATIVE_PKG_IDENTITY_INVALID')
    need(path.name==f'{NAME}-0.6.2_{revision}.pkg' and
         path.is_file() and not path.is_symlink() and
         path.stat().st_uid==0 and
         hashlib.sha256(path.read_bytes()).hexdigest()==digest,
         'MUTATING_NATIVE_PKG_ARCHIVE_UNQUALIFIED')


def accept_pkg_effect(rc,out,err,installed,expected,native_calls):
    """Never equate pkg's successful exit with safe actual replacement."""
    need(native_calls>=1,'GENUINE_HISTORICAL_HOOK_FD9_DELEGATION_NOT_OBSERVED')
    need(rc==0 and installed==expected and
         'os-zapret2-restyle was installed.' in out and
         not any(x in out+err for x in (
             'incomplete zapret lifecycle',
             'cannot determine zapret service state',
             'could not be stopped')),
         'NATIVE_PKG_INSTALL_OR_OLD_HOOKS_UNQUALIFIED')
    return True


def qualify_late_native_refusal(exc, dispatch_reached):
    """Reject any response except the genuine last-owner journal refusal."""
    need(type(exc).__name__ == 'Refusal' and
         str(exc).startswith('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:') and
         dispatch_reached is False,
         'LATE_REAL_PKG_DISPATCH_VETO_UNQUALIFIED')
    return True


def native_transaction(archive,selected_sha,revision,expected_inode,
                       late_journal_fault=False):
    """Keep original FD9 in this detached worker through actual pkg add -f."""
    delegate=load('stage2-native-delegated-fd9-handoff.py')
    stopped=load('stage2-opnsense-real-native-stopped-upgrade.py')
    old=load('stage0-installed-predecessor-readonly.py')
    locked=load('stage2-prepkg-locked-cold-revalidation.py')
    clean=stopped.clean
    native=stopped.native
    need(os.environ.get('ZAPRET2_STAGE3_NATIVE_MUTATING_PKG')=='1' and
         os.environ.get('ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI')=='1',
         'DISPOSABLE_CONFIGD_NATIVE_MUTATING_PKG_OPTIN_REQUIRED')
    delegate.qualify()
    if late_journal_fault:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL')=='1' and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL_CI')=='1',
             'NATIVE_LATE_JOURNAL_TEST_OPTIN_REQUIRED')
    need(native.REVISION==revision and old.ARCHIVE_SHA==delegate.load(
         'stage3-native-configd-detached-fd9.py').SHA_OLD,
         'NATIVE_SOURCE_REVISION_OR_PUBLISHED_OLD_UNQUALIFIED')
    ticket=delegate.load('stage3-native-configd-fd9-handoff.py').ticket(
        os.environ['ZAPRET2_NATIVE_PROJECT_SHA'])
    need(isinstance(ticket,str) and len(ticket)==32,
         'ROOT_CONFIGD_TRANSFER_TICKET_INVALID')
    candidate=Path(os.environ.get('ZAPRET2_STAGE3_NATIVE_PKG_PATH',''))
    validate_candidate(candidate,selected_sha,revision)
    need(isinstance(expected_inode,int) and expected_inode>0 and
         os.fstat(9).st_ino==expected_inode,
         'WORKER_FD9_NOT_ORIGINAL_BEFORE_MUTATING_PKG')
    locked.check_fd9()
    delegate.verify_old_cold_admission(archive)
    initial=old.run('pkg','info','-R','--raw-format','json',NAME)
    need(old.installed_manifest_from_json(initial)['version']=='0.6.2_1',
         'GENUINE_OLD_PKGDB_VERSION_CHANGED_BEFORE_PKG')
    config_before=Path('/conf/config.xml').read_bytes()
    with tempfile.TemporaryDirectory(prefix='stage3-configd-native-fd9-') as folder_str:
        folder=Path(folder_str)
        os.chmod(folder,0o700)
        script=folder/'trusted-historical-lockf'
        script.write_bytes((HERE/'stage2-native-delegated-fd9-handoff.py').read_bytes())
        script.chmod(0o700)
        fd=os.fstat(9)
        token=secrets.token_hex(32)
        ticket_file=folder/'owner-ticket.json'
        ticket_file.write_text(json.dumps({
            'nonce':token,'holder_pid':os.getpid(),
            'dev':fd.st_dev,'ino':fd.st_ino}),encoding='utf-8')
        ticket_file.chmod(0o600)
        env=os.environ.copy()
        env.update({
            'LOCKF_BIN':str(script),
            'ZAPRET2_STAGE2_DELEGATED_TICKET':str(ticket_file),
            'ZAPRET2_STAGE2_DELEGATED_NONCE':token,
            'ZAPRET2_STAGE2_DELEGATED_HOLDER':str(os.getpid())})
        status=subprocess.run([str(old.SERVICE),'status'],env=env,
                              pass_fds=(9,),capture_output=True,text=True,
                              timeout=18,check=False)
        need(status.returncode==1 and
             'zapret is not running' in status.stdout,
             'AUTHENTIC_OLD_STATUS_UNQUALIFIED_DURING_CONFIGD_FD9')
        first=delegate.count_calls(folder)
        need(first>=1,'OLD_STATUS_DID_NOT_USE_AUTHENTIC_FD9_DELEGATION')
        locked.check_fd9()
        need(old.run('pkg','info','-R','--raw-format','json',NAME)==initial and
             Path('/conf/config.xml').read_bytes()==config_before,
             'PREPKG_OWNER_CHECK_MUTATED_OLD_STATE')
        if late_journal_fault:
            # Actual shared pkg dispatcher: replace mutating pkg with a
            # fail-closed tripwire so its invocation is always a test failure.
            handoff=load('stage3-native-configd-fd9-handoff.py')
            base=load('stage3-native-configd-detached-fd9.py')
            base.create_owned(handoff.PREPKG_READY,json.dumps({
                'sha':os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
                'pid':os.getpid(),'original_fd9_inode':expected_inode,
                'nonce_sha256':hashlib.sha256(ticket.encode()).hexdigest()
            },sort_keys=True).encode())
            need(base.wait_file(handoff.PREPKG_RESUME,55)==
                 b'RESUME_TEST_ONLY_AFTER_CORRUPT_JOURNAL',
                 'NATIVE_PKG_LATE_JOURNAL_BARRIER_NOT_RELEASED')
            dispatched=[]
            def forbidden_dispatch(path,environment):
                dispatched.append(True)
                raise Refusal('UNSAFE_REAL_NATIVE_PKG_DISPATCH_REACHED')
            try:
                delegate.admitted_pkg_dispatch(
                    archive,candidate,env,dispatch=forbidden_dispatch)
            except delegate.Refusal as exc:
                qualify_late_native_refusal(exc,bool(dispatched))
            else:
                raise Refusal('UNSAFE_REAL_NATIVE_PKG_OWNER_ACCEPTED')
            need(not dispatched and
                 old.run('pkg','info','-R','--raw-format','json',NAME)==initial and
                 Path('/conf/config.xml').read_bytes()==config_before,
                 'NATIVE_LATE_PKG_REFUSAL_CHANGED_OLD_STATE')
            locked.check_fd9()
            return {'schema':1,
                    'status':'REFUSED_TEST_ONLY_REAL_NATIVE_DISPATCH_LATE_JOURNAL',
                    'real_owner_check_invoked':True,
                    'native_mutating_pkg_dispatch_reached':False,
                    'original_fd9_retained_at_refusal':True,
                    'native_mutating_pkg_invoked':False,
                    'lh08_ac11_accepted':False}
        # Identical final owner admission helper used by existing native _89.
        # NO controller-side gap: this same detached child owns FD9 throughout.
        rc,out,err=delegate.admitted_pkg_dispatch(archive,candidate,env)
        locked.check_fd9()
        calls=delegate.count_calls(folder)-first
        actual=stopped.load('stage2-opnsense-real-unsafe-owner-replacement.py').installed_identity()
        target=NAME+'|0.6.2_'+revision
        accept_pkg_effect(rc,out,err,actual,target,calls)
        need(hashlib.sha256(candidate.read_bytes()).hexdigest()==selected_sha,
             'OFFICIAL_NATIVE_PACKAGE_BYTES_CHANGED_DURING_PKG')
        manifest,pkgdb=clean.installed_pkg_manifest(candidate)
        files=clean.verify_installed_files(candidate,manifest)
        need(bool(files) and bool(pkgdb),'INSTALLED_MANIFEST_OR_FILES_UNQUALIFIED')
        new_service=Path('/usr/local')/native.SERVICE
        after=subprocess.run([str(new_service),'status'],env=env,
                             pass_fds=(9,),capture_output=True,text=True,
                             timeout=18,check=False)
        need(after.returncode==1 and
             after.stdout.strip()=='zapret is not running' and
             delegate.count_calls(folder)>first+calls,
             'NEW_SERVICE_COLD_UNDER_ORIGINAL_CONFIGD_FD9_UNQUALIFIED')
        need(bool(stopped.verify_cold_runtime()),
             'NATIVE_PKG_LEFT_UNKNOWN_KERNEL_RUNTIME')
        need(bool(stopped.prove_preserved_config(
            config_before,Path('/conf/config.xml').read_bytes())),
            'NATIVE_PKG_CHANGED_FOREIGN_CONFIG')
        locked.check_fd9()
        return {'schema':1,
                'status':'PASS_TEST_ONLY_CONFIGD_NATIVE_PKG_UNDER_ORIGINAL_FD9',
                'original_fd9_retained_during_actual_pkg':True,
                'real_pkg_exit':rc,
                'real_old_hook_delegated_lock_calls':calls,
                'installed_native_package_identity':actual,
                'exact_native_successor_sha256':selected_sha,
                'installed_files_modes_verified':True,
                'new_service_cold_under_transferred_fd9':True,
                'foreign_config_values_preserved':True,
                'native_mutating_pkg_invoked':True,
                'stock_firmware_web_protected':False,
                'root_pkg_bypass_protected':False,
                'running_owner_proven':False,
                'interrupted_pkg_rollback_proven':False,
                'lh08_ac11_accepted':False}
