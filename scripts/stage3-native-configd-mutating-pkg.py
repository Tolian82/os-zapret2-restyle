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


def load_product_candidate():
    """Reuse exact packaged product candidate gate, never a test-only copy."""
    import sys
    source=(HERE.parent/'src/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_candidate.py')
    need(source.is_file() and not source.is_symlink(),
         'NATIVE_PKG_PRODUCT_CANDIDATE_GATE_MISSING')
    sys.path.insert(0,str(source.parent))
    spec=importlib.util.spec_from_file_location('native_pkg_candidate',source)
    product=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(product)
    return product


def validate_candidate(path,digest,revision):
    need(isinstance(revision,str) and revision.isdecimal() and
         re.fullmatch('[0-9a-f]{64}',digest or '') is not None,
         'MUTATING_NATIVE_PKG_IDENTITY_INVALID')
    product=load_product_candidate()
    try:
        return product.inspect_archive(path,'0.6.2_'+revision,digest)
    except product.CandidateRefusal as exc:
        raise Refusal(str(exc)) from None


def attest_candidate_fd9(product,path,digest,revision,expected_inode):
    try:
        return product.inspect_with_original_fd9(
            path,'0.6.2_'+revision,digest,expected_inode)
    except product.CandidateRefusal as exc:
        raise Refusal(str(exc)) from None


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
                       late_journal_fault=False,ci_operator_ticket=None):
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
    late_grant=os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER')=='1'
    if late_grant:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER_CI')=='1' and
             os.environ.get('GITHUB_ACTIONS')=='true' and not late_journal_fault,
             'NATIVE_LATE_GRANT_MODE_NOT_DISPOSABLE')
    late_archive=os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER')=='1'
    if late_archive:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER_CI')=='1' and
             os.environ.get('GITHUB_ACTIONS')=='true' and not late_grant and
             not late_journal_fault,
             'NATIVE_LATE_ARCHIVE_MODE_NOT_DISPOSABLE')
    post_final=os.environ.get('ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER')=='1'
    if post_final:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER_CI')=='1' and
             os.environ.get('GITHUB_ACTIONS')=='true' and
             not late_grant and not late_archive and not late_journal_fault,
             'NATIVE_POST_FINAL_ARCHIVE_MODE_NOT_DISPOSABLE')
    stdin_mode=os.environ.get('ZAPRET2_STAGE3_NATIVE_STDIN_PKG')=='1'
    if stdin_mode:
        need(os.environ.get('ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI')=='1' and
             os.environ.get('GITHUB_ACTIONS')=='true' and
             not late_grant and not late_archive and not post_final and
             not late_journal_fault,
             'NATIVE_STDIN_PKG_MODE_NOT_DISPOSABLE')
    live_witness=os.environ.get('ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS')=='1'
    if live_witness:
        need(stdin_mode and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS_CI')=='1' and
             os.environ.get('GITHUB_ACTIONS')=='true' and
             os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK')=='1' and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_SIGNED_CONSUMED')!='1' and
             not late_grant and not late_archive and not post_final and
             not late_journal_fault,
             'CI_LIVE_WITNESS_NOT_DISPOSABLE_BEFORE_NATIVE_PKG')
    stdin_path_swap=os.environ.get('ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP')=='1'
    if stdin_path_swap:
        need(stdin_mode and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP_CI')=='1' and
             os.environ.get('GITHUB_ACTIONS')=='true',
             'NATIVE_STDIN_PATH_SWAP_NOT_DISPOSABLE')
    need(native.REVISION==revision and old.ARCHIVE_SHA==delegate.load(
         'stage3-native-configd-detached-fd9.py').SHA_OLD,
         'NATIVE_SOURCE_REVISION_OR_PUBLISHED_OLD_UNQUALIFIED')
    ticket=delegate.load('stage3-native-configd-fd9-handoff.py').ticket(
        os.environ['ZAPRET2_NATIVE_PROJECT_SHA'])
    need(isinstance(ticket,str) and len(ticket)==32,
         'ROOT_CONFIGD_TRANSFER_TICKET_INVALID')
    candidate=Path(os.environ.get('ZAPRET2_STAGE3_NATIVE_PKG_PATH',''))
    candidate_attestation=validate_candidate(candidate,selected_sha,revision)
    product=load_product_candidate()
    need(candidate_attestation.get('status')=='READ_ONLY_NATIVE_PKG_ARCHIVE_BOUND' and
         candidate_attestation.get('sha256')==selected_sha,
         'PRODUCT_CANDIDATE_INITIAL_INSPECTION_NOT_PROVEN')
    need(isinstance(expected_inode,int) and expected_inode>0 and
         os.fstat(9).st_ino==expected_inode,
         'WORKER_FD9_NOT_ORIGINAL_BEFORE_MUTATING_PKG')
    locked.check_fd9()
    delegate.verify_old_cold_admission(archive)
    attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)
    initial=old.run('pkg','info','-R','--raw-format','json',NAME)
    need(old.installed_manifest_from_json(initial)['version']=='0.6.2_1',
         'GENUINE_OLD_PKGDB_VERSION_CHANGED_BEFORE_PKG')
    config_before=Path('/conf/config.xml').read_bytes()
    need(isinstance(ci_operator_ticket,dict),
         'SIGNED_OPERATOR_GRANT_TICKET_REQUIRED_BEFORE_PKG')
    grant_guard=load('stage3-native-configd-operator-grant-ci.py')
    handoff=load('stage3-native-configd-fd9-handoff.py')
    approval=grant_guard.verify(
        handoff.ROOT,ci_operator_ticket,os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
        archive,candidate,old.ARCHIVE_SHA,selected_sha,revision,locked.check_fd9,
        nonce=ticket,live_phase='consume' if live_witness else None)
    need(approval['ci_operator_signature_verified'] is True and
         approval['ci_original_fd9_held_during_grant_admission'] is True and
         approval['ci_resigned_false_old_new_head_denied'] is True and
         approval['ci_owner_approval_authenticated'] is False,
         'SIGNED_OPERATOR_GRANT_NOT_NATIVE_FD9_QUALIFIED')
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
            attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)
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
            return {'schema':1,**approval,
                    'status':'REFUSED_TEST_ONLY_REAL_NATIVE_DISPATCH_LATE_JOURNAL',
                    'real_owner_check_invoked':True,
                    'product_candidate_fd9_rechecked':True,
                    'native_mutating_pkg_dispatch_reached':False,
                    'original_fd9_retained_at_refusal':True,
                    'native_mutating_pkg_invoked':False,
                    'lh08_ac11_accepted':False}
        # Identical final owner admission helper used by existing native _89.
        # NO controller-side gap: this same detached child owns FD9 throughout.
        attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)
        if late_grant or late_archive:
            # Initial RSA verification and genuine old Status passed.
            # Pause with original FD9 until controller changes signed bytes.
            base=load('stage3-native-configd-detached-fd9.py')
            locked.check_fd9()
            base.create_owned(handoff.PREPKG_READY,json.dumps({
                'sha':os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
                'pid':os.getpid(),'original_fd9_inode':expected_inode,
                'nonce_sha256':hashlib.sha256(ticket.encode()).hexdigest(),
                'initial_signed_grant_verified':True,
                'native_mutating_pkg_invoked':False
            },sort_keys=True).encode())
            need(base.wait_file(handoff.PREPKG_RESUME,55)==
                 (b'RESUME_TEST_ONLY_AFTER_LATE_ARCHIVE_BYTE_TAMPER'
                  if late_archive else
                  b'RESUME_TEST_ONLY_AFTER_LATE_SIGNED_BYTE_TAMPER'),
                 'LATE_FINAL_GRANT_OR_ARCHIVE_BARRIER_NOT_RELEASED')
            locked.check_fd9()
        # Re-verify the very same signed scope and real archive bytes under
        # continuously owned historical FD9 immediately before pkg dispatch.
        second=grant_guard.verify(
            handoff.ROOT,ci_operator_ticket,os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
            archive,candidate,old.ARCHIVE_SHA,selected_sha,revision,locked.check_fd9,
            nonce=ticket,live_phase='status' if live_witness else None)
        need(second==approval,'FD9_SIGNED_OPERATOR_GRANT_DRIFT_BEFORE_PKG')
        if post_final:
            # This second barrier is AFTER successful final signed-grant/SHA
            # verification. A disposable controller now changes the actual
            # archive bytes while the same worker continuously retains FD9.
            # The post-barrier archive gate must veto BEFORE any pkg dispatch.
            base=load('stage3-native-configd-detached-fd9.py')
            locked.check_fd9()
            base.create_owned(handoff.PREPKG_READY,json.dumps({
                'sha':os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
                'pid':os.getpid(),'original_fd9_inode':expected_inode,
                'nonce_sha256':hashlib.sha256(ticket.encode()).hexdigest(),
                'final_signed_grant_verified':True,
                'native_mutating_pkg_invoked':False
            },sort_keys=True).encode())
            need(base.wait_file(handoff.PREPKG_RESUME,55)==
                 b'RESUME_TEST_ONLY_AFTER_POST_FINAL_ARCHIVE_BYTE_TAMPER',
                 'POST_FINAL_ARCHIVE_DISPATCH_BARRIER_NOT_RELEASED')
            locked.check_fd9()
        # Dispatch-side last archive identity+SHA recheck under original FD9.
        # This only narrows the path-open TOCTOU; pkg still opens a pathname.
        # A privileged caller may replace bytes AFTER this check.
        attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)
        if stdin_mode:
            # Test-only verified byte snapshot. The package manager consumes
            # stdin, not the candidate filename, under inherited original FD9.
            # No pkg bypass is avoided for unrelated privileged callers.
            stream=load('stage3-native-pkg-stdin-ci.py')
            frozen=stream.freeze_exact_candidate(
                candidate,selected_sha,revision,locked.check_fd9)
            if stdin_path_swap:
                # Unlike _129: REAL controller changes the PATH to a
                # different inode AFTER immutable snapshot but BEFORE pkg.
                base=load('stage3-native-configd-detached-fd9.py')
                locked.check_fd9()
                base.create_owned(handoff.PREPKG_READY,json.dumps({
                    'sha':os.environ['ZAPRET2_NATIVE_PROJECT_SHA'],
                    'pid':os.getpid(),'original_fd9_inode':expected_inode,
                    'nonce_sha256':hashlib.sha256(ticket.encode()).hexdigest(),
                    'signed_grant_verified':True,
                    'frozen_snapshot_sha256':frozen.sha256,
                    'frozen_snapshot_inode':frozen.inode,
                    'frozen_snapshot_complete':True,
                    'native_mutating_pkg_invoked':False
                },sort_keys=True).encode())
                need(base.wait_file(handoff.PREPKG_RESUME,55)==
                     b'RESUME_TEST_ONLY_AFTER_STDIN_SNAPSHOT_PATH_REBIND',
                     'CI_STDIN_PATH_SWAP_BARRIER_NOT_RELEASED')
                locked.check_fd9()
                changed=candidate.lstat()
                need(stat.S_ISREG(changed.st_mode) and
                     changed.st_dev==frozen.dev and changed.st_ino!=frozen.inode and
                     hashlib.sha256(candidate.read_bytes()).hexdigest()!=selected_sha,
                     'CI_STDIN_CANDIDATE_PATH_NOT_ACTUALLY_REBOUND')
            def verified_stdin_dispatch(_candidate_path, environment):
                return stream.install_frozen_stdin(
                    frozen,environment,locked.check_fd9)
            rc,out,err=delegate.admitted_pkg_dispatch(
                archive,candidate,env,dispatch=verified_stdin_dispatch)
        else:
            rc,out,err=delegate.admitted_pkg_dispatch(archive,candidate,env)
        locked.check_fd9()
        calls=delegate.count_calls(folder)-first
        actual=stopped.load('stage2-opnsense-real-unsafe-owner-replacement.py').installed_identity()
        target=NAME+'|0.6.2_'+revision
        accept_pkg_effect(rc,out,err,actual,target,calls)
        source_for_manifest=candidate
        observed_rebound_sha=None
        if stdin_path_swap:
            # Prove the attacker-controlled pathname stayed corrupt THROUGH
            # actual pkg. Compare the installed files to immutable bytes,
            # never to the deliberately substituted candidate pathname.
            changed=candidate.lstat()
            observed_rebound_sha=hashlib.sha256(candidate.read_bytes()).hexdigest()
            need(changed.st_ino!=frozen.inode and
                 observed_rebound_sha!=selected_sha,
                 'CI_STDIN_REBOUND_DID_NOT_SURVIVE_REAL_PKG')
            source_for_manifest=folder/'native-frozen-reference.pkg'
            fdref=os.open(source_for_manifest,
                          os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fdref,'wb') as reference:
                reference.write(frozen.data)
                reference.flush()
                os.fsync(reference.fileno())
            need(hashlib.sha256(source_for_manifest.read_bytes()).hexdigest()==selected_sha,
                 'CI_STDIN_FROZEN_MANIFEST_SOURCE_CHANGED')
        else:
            need(hashlib.sha256(candidate.read_bytes()).hexdigest()==selected_sha,
                 'OFFICIAL_NATIVE_PACKAGE_BYTES_CHANGED_DURING_PKG')
        manifest,pkgdb=clean.installed_pkg_manifest(source_for_manifest)
        files=clean.verify_installed_files(source_for_manifest,manifest)
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
        return {'schema':1,**approval,
                'status':'PASS_TEST_ONLY_CONFIGD_NATIVE_PKG_UNDER_ORIGINAL_FD9',
                'original_fd9_retained_during_actual_pkg':True,
                'real_pkg_exit':rc,
                'real_old_hook_delegated_lock_calls':calls,
                'installed_native_package_identity':actual,
                'exact_native_successor_sha256':selected_sha,
                'product_candidate_fd9_rechecked':True,
                'ci_pkg_consumed_verified_stdin_bytes':stdin_mode,
                'ci_pkg_stdin_avoids_candidate_path_reopen':stdin_mode,
                'ci_stdin_path_rebound_after_snapshot':stdin_path_swap,
                'ci_stdin_frozen_manifest_verified':stdin_path_swap,
                'ci_stdin_rebound_sha256':observed_rebound_sha,
                'ci_stdin_original_frozen_inode':frozen.inode if stdin_path_swap else None,
                'installed_files_modes_verified':True,
                'new_service_cold_under_transferred_fd9':True,
                'foreign_config_values_preserved':True,
                'native_mutating_pkg_invoked':True,
                'stock_firmware_web_protected':False,
                'root_pkg_bypass_protected':False,
                'running_owner_proven':False,
                'interrupted_pkg_rollback_proven':False,
                'lh08_ac11_accepted':False}
