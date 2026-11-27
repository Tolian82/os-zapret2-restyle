"""Original FD9 archival of a first restored zero-cut Auto operation.

The RESTORED WAL stays current. Historical receipts never authorize an owner.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import os
import stat
import json
import sys
import pwd

from shared_apply_seal import WORK, verify_seal
from auto_detect_storage import ROOT as PRODUCER_ROOT, ENGINE_USER
from auto_detect_epoch_receipts import ROOT as EPOCH_ROOT, _read, _canonical, _write_once, _sync
from shared_apply_operation import SharedApplyOperation, restored_first_learning, OP_ID, _config_observation_witness
from voice_ipfw_adapter import require_lifecycle_lock
from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
from auto_detect_queue import DurableInbox
from auto_detect_post_drop import (_capture, _learning_release_sources, _qualified_learning_sources,
    match_zero_cut, _zero_cut_provenance)
from auto_detect_fd import FDState, _probe_attested_original_inode
from neutral_root_stage import verify_original_operation_pins, _verify_original_pinned_root
from voice_live_inspect import COMMON_ACTIVE, CHILD_PID, MONITOR_PID
from neutral_schema3_quiescent_preimage import (_zero_processes, _empty_kernel, _cold_files,
    _safe_empty_directory, _reject_cold_recovery_residue, _run_bound_restore_joined,
    _relay_first_recovery_trace, DAEMON_PID, SCRIPT)

ARCHIVE_ROOT = WORK.parent / 'shared-aborted-first'

class ArchiveRefused(RuntimeError):
    pass


@dataclass(frozen=True)
class Slot:
    source: Path
    archived: Path


def _stat_dir(path, uid):
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != uid or st.st_mode & 0o022:
        raise ArchiveRefused('untrusted_archive_directory')
    return st


def _pin(st):
    return (st.st_dev, st.st_ino, st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode))


def _present(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _open_parent(path, uid):
    before = _pin(_stat_dir(path, uid))
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if _pin(os.fstat(fd)) != before or _pin(_stat_dir(path, uid)) != before:
            raise ArchiveRefused('archive_parent_changed')
        return fd, before
    except BaseException:
        os.close(fd)
        raise


def _layout(slots, uid):
    if type(slots) is not tuple or len(slots) != 3 or any(type(s) is not Slot for s in slots):
        raise ArchiveRefused('exact_three_archive_slots_required')
    paths = tuple(p for s in slots for p in (s.source, s.archived))
    if any(not isinstance(p, Path) or not p.is_absolute() or '..' in p.parts or p == p.parent for p in paths):
        raise ArchiveRefused('invalid_archive_path')
    if len(set(paths)) != 6 or any(a in b.parents for a in paths for b in paths if a != b):
        raise ArchiveRefused('overlapping_archive_slots')
    rows = []
    for s in slots:
        left, right = _present(s.source), _present(s.archived)
        if left == right:
            raise ArchiveRefused('archive_source_destination_ambiguous')
        parent_a, parent_b = (_stat_dir(p, uid) for p in (s.source.parent, s.archived.parent))
        selected = s.source if left else s.archived
        obj = _stat_dir(selected, uid)
        if obj.st_dev != parent_a.st_dev or obj.st_dev != parent_b.st_dev:
            raise ArchiveRefused('archive_cross_device_refused')
        rows.append((selected, _pin(obj), _pin(parent_a), _pin(parent_b)))
    if len({row[1][:2] for row in rows}) != 3:
        raise ArchiveRefused('archive_directory_alias')
    # Only a prefix of the declared moves is a legitimate crash image.
    flags = tuple(row[0] == slot.archived for slot, row in zip(slots, rows))
    if flags != tuple(sorted(flags, reverse=True)):
        raise ArchiveRefused('archive_out_of_order')
    return tuple(rows)


def archive_original_zero_directories(slots, *, uid, attest, scope, after_move=None):
    """Move work, epoch, producer (in that order). Producer lock moves last.

    `scope()` must assert the original authority (not just return truthy).
    `attest(paths)` must return immutable, equality-comparable *content and
    source inode* evidence for the selected live/archived locations, not a
    Boolean. It must itself enforce same original held queue OFD at selected
    producer path. The caller closes that OFD before any fresh preparation.
    No independent journal. On error the original terminal WAL stays live;
    next invocation revalidates the exact prefix, not an inferred progress flag.
    `after_move` is for local fault injection only, never a production CLI.
    """
    if not callable(attest) or not callable(scope):
        raise ArchiveRefused('original_archive_authority_required')

    def observe():
        if scope() is not True:
            raise ArchiveRefused('original_archive_scope_changed')
        layout = _layout(slots, uid)
        evidence = attest(tuple(row[0] for row in layout))
        if evidence is None or isinstance(evidence, bool):
            raise ArchiveRefused('original_archive_evidence_required')
        if _layout(slots, uid) != layout or scope() is not True:
            raise ArchiveRefused('original_archive_observation_changed')
        return layout, evidence

    first, proof = observe()
    if observe() != (first, proof):
        raise ArchiveRefused('original_archive_preimage_changed')
    expected = first
    for index, slot in enumerate(slots):
        if expected[index][0] == slot.archived:
            continue
        if observe() != (expected, proof):
            raise ArchiveRefused('original_archive_before_move_changed')
        a, ap = _open_parent(slot.source.parent, uid)
        try:
            b, bp = _open_parent(slot.archived.parent, uid)
            try:
                row = expected[index]
                if (ap, bp) != row[2:] or _present(slot.archived) or _pin(_stat_dir(slot.source, uid)) != row[1]:
                    raise ArchiveRefused('original_archive_move_image_changed')
                if scope() is not True:
                    raise ArchiveRefused('original_archive_scope_changed')
                os.rename(slot.source.name, slot.archived.name, src_dir_fd=a, dst_dir_fd=b)
                if after_move is not None:
                    after_move(index)
                os.fsync(a)
                os.fsync(b)
            finally:
                os.close(b)
        finally:
            os.close(a)
        expected = tuple((slot.archived, *row[1:]) if j == index else row for j, row in enumerate(expected))
        if observe() != (expected, proof):
            raise ArchiveRefused('original_archive_after_move_changed')
    # A lost reply or interruption after rename and before fsync is not a
    # permission to admit a new owner until all parent entries are durable.
    for slot in slots:
        for parent in (slot.source.parent, slot.archived.parent):
            fd, _ = _open_parent(parent, uid)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    if observe() != (expected, proof) or any(row[0] != slot.archived for row, slot in zip(expected, slots)):
        raise ArchiveRefused('original_archive_terminal_readback_changed')
    return proof


def _private_dir(path, mode, *, create):
    if create and not _present(path):
        path.mkdir(mode=mode)
        path.chmod(mode)
        _sync(path.parent)
    if _present(path):
        info = _stat_dir(path, 0)
        if stat.S_IMODE(info.st_mode) != mode:
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_PRIVATE_DIRECTORY_REQUIRED')


def _slots(record, *, create=False):
    op = record['detail']['id']
    if not restored_first_learning(record) or not OP_ID.fullmatch(op):
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_OWNER_REQUIRED')
    folder = ARCHIVE_ROOT / op
    _stat_dir(ARCHIVE_ROOT.parent, 0)
    for path, mode in ((ARCHIVE_ROOT, 0o700), (folder, 0o700),
                       (folder / 'work', 0o700), (folder / 'producer-parent', 0o711)):
        _private_dir(path, mode, create=create)
    if _present(folder) and set(os.listdir(folder)) - {'work', 'epoch', 'producer-parent', 'restored.json'}:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_FOREIGN_ENTRY')
    slots = (Slot(WORK / op, folder / 'work' / op),
             Slot(EPOCH_ROOT / op, folder / 'epoch'),
             Slot(PRODUCER_ROOT, folder / 'producer-parent' / 'producer'))
    for parent, allowed in ((WORK, {op}), (EPOCH_ROOT, {op}),
            (folder / 'work', {op}), (folder / 'producer-parent', {'producer'})):
        if _present(parent) and set(os.listdir(parent)) - allowed:
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_FOREIGN_SOURCE')
    # Source parents remain until the next original Apply. No automatic
    # removal of unknown or detached work or other historical epochs.
    for parent in (WORK, EPOCH_ROOT):
        _stat_dir(parent, 0)
    paths = []
    for slot in slots:
        live, archived = _present(slot.source), _present(slot.archived)
        if live == archived:
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_AMBIGUOUS_SOURCE')
        paths.append(slot.source if live else slot.archived)
    flags = tuple(path == slot.archived for path, slot in zip(paths, slots))
    if flags != tuple(sorted(flags, reverse=True)):
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_ORDER_REQUIRED')
    if _present(folder / 'restored.json') and (not all(flags) or
            _read(folder / 'restored.json', 0) != _canonical(record)):
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_RECEIPT_CHANGED')
    return folder, slots, tuple(paths)


def _source_evidence(record, paths, queue_fd, scope, *, drain=False):
    work, epoch, producer = paths
    detail = record['detail']
    scope()
    verify_original_operation_pins(record=record, parent=work.parent, owner_uid=0)
    raw_root = _verify_original_pinned_root(detail=detail, binding=record['manifest'],
                                           parent=work.parent, owner_uid=0)
    root = json.loads(raw_root)
    if root['service']['enabled'] is not True or root['service']['target_mode'] != 'auto':
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_ROOT_MODE_REQUIRED')
    workspace, candidate, sources = _learning_release_sources(work / 'release', work_parent=work.parent)
    if workspace != work or candidate != detail['candidate']:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_SOURCE_CHANGED')
    _, names = _qualified_learning_sources(sources, PRODUCER_ROOT)
    _private_dir(epoch, 0o700, create=False)
    if set(os.listdir(epoch)) != {'pretraffic.json'}:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_SEED_ONLY_REQUIRED')
    identity = pwd.getpwnam(ENGINE_USER)
    def pin(path):
        st = path.lstat()
        return (st.st_dev, st.st_ino, st.st_nlink, st.st_size, st.st_mtime_ns,
                st.st_ctime_ns, st.st_uid, st.st_gid, st.st_mode)
    seed = epoch / 'pretraffic.json'
    source_paths = tuple(producer / name for name in ('inbox.txt', 'debug.log', *names))
    pins = tuple(pin(path) for path in (work / 'manifest.json', seed, *source_paths))
    raw = _read(seed, 0)
    actual = _capture(producer, root_uid=0, root_gid=0, engine_uid=identity.pw_uid,
        engine_gid=identity.pw_gid, learning_names=names, queue_fd=queue_fd)
    historical = replace(actual, root=PRODUCER_ROOT)
    match_zero_cut(record, sources, historical, raw,
        _zero_cut_provenance(work, sources, historical), historical=True)
    if drain:
        for path, (dev, ino, _) in zip(source_paths, actual.identities):
            if _probe_attested_original_inode(path, dev, ino, writer_gid=identity.pw_gid,
                    attest_owner=scope) is not FDState.DRAINED:
                raise ArchiveRefused('FIRST_ABORT_ARCHIVE_FD_NOT_DRAINED')
    if (tuple(pin(path) for path in (work / 'manifest.json', seed, *source_paths)) != pins or
            _read(seed, 0) != raw or tuple(row[:3] for row in pins[2:]) != actual.identities):
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_INODES_CHANGED')
    scope()
    return raw_root, raw, pins


def archive_first_restored_locked(operation, witness, *, config_fd, queue_fd):
    if (not sys.platform.startswith('freebsd') or os.geteuid() != 0 or
            not isinstance(operation, str) or not OP_ID.fullmatch(operation) or
            config_fd != 4 or queue_fd != 3):
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_NATIVE_REQUIRED')
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if not restored_first_learning(record) or record['detail']['id'] != operation:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_OWNER_REQUIRED')
    def scope():
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        if store.read() != record:
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_WAL_CHANGED')
        _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
        _safe_empty_directory(COMMON_ACTIVE, 0)
        _safe_empty_directory(COMMON_ACTIVE.with_name('runtime-v2-backups'), 0)
        _reject_cold_recovery_residue(COMMON_ACTIVE)
        return True
    scope()
    folder, slots, paths = _slots(record)
    def attest(paths, *, drain=False):
        scope()
        detail = record['detail']
        plan_sha = verify_seal(paths[0], owner=0)['sha256']['plan.json']
        if witness != _config_observation_witness(detail, plan_sha, detail['base']):
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_CONFIG_BASE_REQUIRED')
        kernel = _empty_kernel(paths[0] / 'release')
        if kernel not in ('native-kernel-absent', 'native-managed-kernel-empty'):
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_KERNEL_NOT_EMPTY')
        return kernel, _source_evidence(record, paths, queue_fd, scope, drain=drain)
    original = attest(paths, drain=True)
    folder, slots, paths = _slots(record, create=True)
    if attest(paths) != original:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_PREIMAGE_CHANGED')
    result = archive_original_zero_directories(slots, uid=0, attest=attest, scope=scope)
    if result != original:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_RESULT_CHANGED')
    if (_slots(record)[2] != tuple(slot.archived for slot in slots) or
            attest(tuple(slot.archived for slot in slots), drain=True) != original or store.read() != record):
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_READBACK_REQUIRED')
    _cold_files(COMMON_ACTIVE, COMMON_ACTIVE.with_name('runtime-v2-backups'), PRODUCER_ROOT, EPOCH_ROOT, 0)
    _safe_empty_directory(WORK, 0)
    _write_once(folder, 'restored.json', _canonical(record), 0)
    if _slots(record)[2] != tuple(slot.archived for slot in slots) or store.read() != record:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_RECEIPT_CHANGED')
    return {'result': 'original-first-restored-archived', 'id': operation}


def native_archive_first_restored(operation):
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_NATIVE_REQUIRED')
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if not restored_first_learning(record) or record['detail']['id'] != operation:
        raise ArchiveRefused('FIRST_ABORT_ARCHIVE_OWNER_REQUIRED')
    _, slots, paths = _slots(record)
    queue = DurableInbox(paths[2], owner_uid=0, writer_gid=pwd.getpwnam(ENGINE_USER).pw_gid)
    with queue.exclusive(existing_only=True):
        if store.read() != record or _slots(record)[2] != paths:
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_OWNER_CHANGED')
        fd = queue.locked_fd
        reply = _run_bound_restore_joined(['/usr/local/bin/php', str(SCRIPT / 'shared_apply_config.php'),
            'ordinary-first-archive', operation, record['detail']['page'], '--queue-fd=' + str(fd)],
            pass_fds=(9, fd), capture_output=True, budget=180)
        if (reply.returncode != 0 or type(reply.stdout) is not bytes or len(reply.stdout) > 4096 or
                reply.stdout.count(b'\n') != 1 or not reply.stdout.endswith(b'\n') or
                json.loads(reply.stdout) != {'result': 'original-first-restored-archived', 'id': operation} or
                store.read() != record or _slots(record)[2] != tuple(slot.archived for slot in slots)):
            _relay_first_recovery_trace(reply.stderr)
            raise ArchiveRefused('FIRST_ABORT_ARCHIVE_NATIVE_RECEIPT_REQUIRED')
