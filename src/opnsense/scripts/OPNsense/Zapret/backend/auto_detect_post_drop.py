#!/usr/bin/env python3
"""#1052 P2: single original-FD9 sealed observer/producer and PID gates.

The existing configd/service FD9 owner authorizes a source-bound schema-2
candidate, verifies the native raw/debug layout before starting the ONE
engine, seals immutable pretraffic identities and restores exact producer
inode ownership after the engine drops credentials but before IPFW divert.
No second start route, collector, Config writer, ACK or daemon.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
from pathlib import Path
import pwd
import stat
import subprocess
import sys
from typing import Callable

from auto_detect_fd import OwnerToken, _owner_snapshot
from auto_detect_debug_window import _read_exact, DebugWindowRefused
from auto_detect_queue import DurableInbox, QueueSafetyError
from auto_detect_storage import (
    ROOT, RAW_PATH, DEBUG_PATH, ENGINE_USER,
    ROOT_MODE, FILE_MODE, PENDING_MODE, _parent,
    _learning_names, StorageRefused,
)

class PostDropRefused(RuntimeError):
    """A changed original inode/process prevents IPFW activation."""


@dataclass(frozen=True)
class OriginalProducer:
    root: Path
    root_uid: int
    root_gid: int
    engine_uid: int
    engine_gid: int
    # One ordered identity per actual original producer file, never raw data.
    identities: tuple[tuple[int, int, int], ...]
    # Additional learning files are structural-only until original FD9
    # runtime seal, multiple-inbox receipts, and ACK are connected.
    learning_names: tuple[str, ...] = ()


def _check_layout(root: Path, root_uid: int, root_gid: int, engine_gid: int,
                  learning_names: tuple[str, ...] = ()) -> None:
    try:
        names = _learning_names(learning_names)
    except StorageRefused as exc:
        raise PostDropRefused("unsafe_original_learning_source_names") from exc
    try:
        info = root.lstat()
        pending = (root / "pending").lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != root_uid or
                info.st_gid != engine_gid or
                stat.S_IMODE(info.st_mode) != ROOT_MODE or
                not stat.S_ISDIR(pending.st_mode) or pending.st_uid != root_uid or
                pending.st_gid != root_gid or
                stat.S_IMODE(pending.st_mode) != PENDING_MODE or
                set(os.listdir(root)) -
                ({"pending", "inbox.txt", "debug.log", "worker.lock"} | set(names))):
            raise PostDropRefused("unsafe_original_producer_layout")
        lock = root / "worker.lock"
        if lock.exists() or lock.is_symlink():
            st = lock.lstat()
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != root_uid or
                    st.st_gid != root_gid or st.st_nlink != 1 or
                    stat.S_IMODE(st.st_mode) != 0o600):
                raise PostDropRefused("unsafe_original_producer_lock")
    except (OSError, ValueError) as exc:
        raise PostDropRefused("original_producer_layout_unavailable") from exc


def _identity(path: Path, *, uid: tuple[int, ...], gid: int,
              expected: tuple[int, int, int] | None = None) -> tuple[int, int, int]:
    try:
        entry = path.lstat()
    except OSError as exc:
        raise PostDropRefused("original_producer_entry_unavailable") from exc
    inode = (entry.st_dev, entry.st_ino, entry.st_nlink)
    if (not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1 or
            stat.S_IMODE(entry.st_mode) != FILE_MODE or
            entry.st_uid not in uid or entry.st_gid != gid or
            (expected is not None and inode != expected)):
        raise PostDropRefused("original_producer_inode_drift")
    return inode


def _capture(root: Path, *, root_uid: int, root_gid: int, engine_uid: int,
             engine_gid: int, learning_names: tuple[str, ...] = (),
             queue_fd: int | None = None) -> OriginalProducer:
    """Testable scoped precursor. Does not change either producer file."""
    if (not isinstance(root, Path) or not root.is_absolute() or
            type(root_uid) is not int or root_uid < 0 or
            type(root_gid) is not int or root_gid < 0 or
            type(engine_uid) is not int or engine_uid <= 0 or
            type(engine_gid) is not int or engine_gid <= 0 or
            root_uid == engine_uid):
        raise PostDropRefused("unqualified_original_producer_identity")
    # The original P2a queue flock is the ONLY serialization owner for
    # prelaunch raw/old-inode state. The FD9 caller retains its independent
    # common Apply lock; this short nested P2a lock is not a new worker.
    # Neither a nonempty prior native debug history nor foreign-generation
    # pending may be inherited by a new original shared-FD9 observer.
    try:
        _check_layout(root, root_uid, root_gid, engine_gid, learning_names)
        queue = DurableInbox(root, owner_uid=root_uid, writer_gid=engine_gid)
        # An in-flight bound Apply holds P2a BEFORE Config. Borrow that
        # exact OFD, rather than opening/locking worker.lock a second time.
        with (queue.exclusive() if queue_fd is None else queue.inherited_exclusive(queue_fd)):
            _check_layout(root, root_uid, root_gid, engine_gid, learning_names)
            if queue.segments():
                raise PostDropRefused("unprocessed_original_pending_prelaunch")
            identities = []
            for name in ("inbox.txt", "debug.log", *learning_names):
                path = root / name
                stat_before, bytes_before = _read_exact(
                    path, owner_uid=root_uid, writer_gid=engine_gid)
                identity = _identity(path, uid=(root_uid,), gid=engine_gid)
                if bytes_before or stat_before.st_size or identity != (
                        stat_before.st_dev, stat_before.st_ino, stat_before.st_nlink):
                    raise PostDropRefused("nonempty_or_changed_original_pretraffic_inode")
                identities.append(identity)
            if identities[0][:2] == identities[1][:2]:
                raise PostDropRefused("aliased_original_raw_and_debug")
            if len({ident[:2] for ident in identities}) != len(identities):
                raise PostDropRefused("aliased_original_producer_inode")
            _check_layout(root, root_uid, root_gid, engine_gid, learning_names)
            return OriginalProducer(root, root_uid, root_gid,
                                    engine_uid, engine_gid, tuple(identities),
                                    learning_names)
    except (QueueSafetyError, DebugWindowRefused, OSError) as exc:
        raise PostDropRefused("original_pretraffic_queue_or_inode_unavailable") from exc


PROVENANCE_FIELDS = ("release_seal_sha256", "original_args_sha256",
                     "final_args_sha256", "native_map_sha256",
                     "source_map_sha256", "witness_sha256")


def match_zero_cut(record, sources, producer, seed_raw, provenance, *, historical=False):
    """Return exact pretraffic bytes for ACTIVATED or explicitly historical RESTORED.

    `producer` MUST be obtained via the existing auto_detect_post_drop._capture
    while borrowing the original P2a descriptor. The caller must independently
    verify original locks, record, root/seal and physical runtime before/after.
    This comparator never reads a mutable file or invents a running owner.
    """
    def refuse():
        raise ValueError('first_learning_zero_cut_not_exact')

    if (type(historical) is not bool or type(record) is not dict or
            record.get('phase') != ('restored' if historical else 'activated') or
            record.get('manifest', {}).get('schema') != 2 or
            any(k in record for k in ('previous', 'previous_manifest', 'found')) or
            any(type(record.get(k)) is not str or
                not re.fullmatch(r'[0-9a-f]{64}', record[k])
                for k in ('first_running_sha256', 'first_pretraffic_sha256')) or
            type(seed_raw) is not bytes or
            hashlib.sha256(seed_raw).hexdigest() != record['first_pretraffic_sha256']):
        refuse()
    detail = record['detail']
    generation = detail['id']
    candidate = detail['candidate']
    if (not re.fullmatch(r'[0-9a-f]{32}', generation) or
            not re.fullmatch(r'[0-9a-f]{64}', candidate) or
            detail['base'] == candidate or
            type(sources) is not tuple or not 1 <= len(sources) <= 255):
        refuse()
    import json
    seed = json.loads(seed_raw)
    if (type(provenance) is not dict or set(provenance) != set(PROVENANCE_FIELDS) or
            any(type(v) is not str or not re.fullmatch(r'[0-9a-f]{64}', v)
                for v in provenance.values())):
        refuse()
    if (type(seed) is not dict or set(seed) != (set(PROVENANCE_FIELDS) |
            {'schema', 'kind', 'generation', 'owner_candidate_sha256',
             'files', 'learning', 'ack_authorized'}) or
            (json.dumps(seed, sort_keys=True, separators=(',', ':')) + '\n').encode() != seed_raw or
            any(seed[k] != v for k, v in provenance.items()) or
            type(seed.get('schema')) is not int or
            seed['schema'] != 3 or seed.get('kind') != 'original-fd9-learning-pretraffic-zero' or
            seed.get('generation') != generation or
            seed.get('owner_candidate_sha256') != candidate or
            seed.get('ack_authorized') is not False):
        refuse()
    names = tuple(Path(path).name for _, _, path in sources)
    if (any(type(number) is not int or not 1 <= number <= 255 or
            path != str(producer.root / f'learning-{generation}-{number}.txt')
            for number, _, path in sources) or
            names != producer.learning_names or
            len(set(names)) != len(names) or
            len(producer.identities) != 2 + len(names) or
            len(set(row[:2] for row in producer.identities)) != len(producer.identities) or
            any(type(row) is not tuple or len(row) != 3 or
                any(type(value) is not int for value in row) or
                row[0] < 0 or row[1] <= 0 or row[2] != 1
                for row in producer.identities)):
        refuse()
    expected_files = [dict(name=name, device=dev, inode=ino, nlink=links)
                      for name, (dev, ino, links) in
                      zip(('inbox.txt', 'debug.log', *names), producer.identities)]
    expected_learning = [dict(native_number=number, hostlist=hostlist, path=path,
                              device=dev, inode=ino, offset=0,
                              prefix_sha256=hashlib.sha256(b'').hexdigest())
                         for (number, hostlist, path), (dev, ino, _) in
                         zip(sources, producer.identities[2:])]
    # Strict JSON equality also rules out booleans substituting for integers.
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'))
    if (canonical(seed.get('files')) != canonical(expected_files) or
            canonical(seed.get('learning')) != canonical(expected_learning)):
        refuse()
    return seed_raw


def _zero_cut_provenance(workspace, sources, producer):
    """Recompute original pretraffic provenance from exact sealed input and inodes."""
    from auto_detect_epoch_receipts import _canonical
    from auto_detect_origin_map import ORIGIN_FILE
    from auto_detect_owner import _secure_bytes, MAX_ARGS, MAX_MAP
    from shared_apply_seal import verify_seal

    release = workspace / "release"
    def digest(raw):
        return hashlib.sha256(raw).hexdigest()
    return {
        "release_seal_sha256": digest(_canonical(verify_seal(workspace, owner=0))),
        "original_args_sha256": digest(_secure_bytes(release / "dvtws.original.args", MAX_ARGS, 0)),
        "final_args_sha256": digest(_secure_bytes(release / "dvtws.args", MAX_ARGS, 0)),
        "native_map_sha256": digest(_secure_bytes(release / "auto-detect-generation.json", MAX_MAP, 0)),
        "source_map_sha256": digest(_secure_bytes(release / ORIGIN_FILE, MAX_MAP, 0)),
        "witness_sha256": digest(_witness_line_learning(producer, sources).encode()),
    }


def _reattest(witness: OriginalProducer, owner_alive: Callable[[], bool]) -> tuple[str, ...]:
    """Repair only original *open inodes* after real engine credential drop.

    Both paths are verified before the first fchown, so an unsafe debug file
    cannot cause a partial 'successful' repair of the raw inbox. FDs use
    O_NOFOLLOW and are never created/replaced. Abort before IPFW on any drift.
    """
    if not isinstance(witness, OriginalProducer) or not callable(owner_alive):
        raise PostDropRefused("missing_original_fd9_witness")
    root = witness.root
    try:
        names = _learning_names(witness.learning_names)
    except StorageRefused as exc:
        raise PostDropRefused("untrusted_original_learning_witness") from exc
    if len(witness.identities) != 2 + len(names):
        raise PostDropRefused("incomplete_original_producer_witness")
    _check_layout(root, witness.root_uid, witness.root_gid,
                  witness.engine_gid, names)
    paths = tuple(root / name for name in ("inbox.txt", "debug.log", *names))
    for path, prior in zip(paths, witness.identities):
        _identity(path, uid=(witness.root_uid, witness.engine_uid),
                  gid=witness.engine_gid, expected=prior)
    if owner_alive() is not True:
        raise PostDropRefused("original_engine_owner_changed")
    changed = []
    for path, prior in zip(paths, witness.identities):
        if owner_alive() is not True:
            raise PostDropRefused("original_engine_owner_changed")
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as exc:
            raise PostDropRefused("original_producer_fd_unavailable") from exc
        try:
            before = os.fstat(fd)
            if ((before.st_dev, before.st_ino, before.st_nlink) != prior or
                    not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                    stat.S_IMODE(before.st_mode) != FILE_MODE or
                    before.st_gid != witness.engine_gid or
                    before.st_uid not in (witness.root_uid, witness.engine_uid)):
                raise PostDropRefused("original_producer_open_inode_drift")
            # Upstream dvtws2 --user=nobody may chown its hostlist on startup.
            # Repair the very same open inode, never pathname-following chown.
            if before.st_uid == witness.engine_uid:
                os.fchown(fd, witness.root_uid, witness.engine_gid)
                changed.append(path.name)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_nlink) != prior or
                    after.st_uid != witness.root_uid or
                    after.st_gid != witness.engine_gid or
                    stat.S_IMODE(after.st_mode) != FILE_MODE):
                raise PostDropRefused("original_producer_reownership_failed")
        except OSError as exc:
            raise PostDropRefused("original_producer_reownership_failed") from exc
        finally:
            os.close(fd)
        _identity(path, uid=(witness.root_uid,), gid=witness.engine_gid,
                  expected=prior)
    _check_layout(root, witness.root_uid, witness.root_gid,
                  witness.engine_gid, names)
    for path, prior in zip(paths, witness.identities):
        _identity(path, uid=(witness.root_uid,), gid=witness.engine_gid,
                  expected=prior)
    if owner_alive() is not True:
        raise PostDropRefused("original_engine_owner_changed")
    return tuple(changed)


def native_capture_before_launch() -> OriginalProducer:
    """Original FD9-only pretraffic proof: empty exact physical inodes."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise PostDropRefused("native_root_fd9_only")
    try:
        nobody = pwd.getpwnam(ENGINE_USER)
        if nobody.pw_uid <= 0 or nobody.pw_gid <= 0:
            raise PostDropRefused("unqualified_original_engine_user")
        _parent(ROOT, 0)
        return _capture(ROOT, root_uid=0, root_gid=0, engine_uid=nobody.pw_uid,
                        engine_gid=nobody.pw_gid)
    except (OSError, KeyError, ValueError) as exc:
        raise PostDropRefused("original_producer_native_identity_unavailable") from exc


def native_restore_before_ipfw(witness: OriginalProducer, owner: OwnerToken,
                               *, runner=subprocess.run) -> tuple[str, ...]:
    """Original FD9-only post-drop call. Requires exact original PID/birth/exe.

    Passing an arbitrary alive=True flag cannot invoke the native entry.
    Never call outside the original single-process shared Apply under FD9.
    """
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(owner, OwnerToken) or not isinstance(witness, OriginalProducer) or
            witness.root != ROOT or witness.root_uid != 0 or witness.root_gid != 0 or
            not owner.executable.startswith("/") or owner.pid <= 1):
        raise PostDropRefused("native_original_fd9_owner_required")
    try:
        return _reattest(witness, lambda: _owner_snapshot(owner, runner))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PostDropRefused("native_original_process_unavailable") from exc


def native_authorize_original_release(release: Path) -> None:
    """Read-only authorization of the exact original sealed schema-2 candidate.

    Called by both pre-journal release preflight and installed runtime launch
    under the ORIGINAL FD9. A syntactically valid --hostlist-auto alone is not
    an authorization: the same root-owned sealed workspace, native source
    profiles, candidate digest and final argv must all agree. No producer
    file, Config, journal or process is changed here.
    """
    import json
    from auto_detect_owner import MAP_NAME, MAX_ARGS, MAX_MAP, _secure_bytes, _valid_map
    from auto_detect_origin_map import verify_original_promotion
    from shared_apply_seal import WORK, verify_seal
    from voice_live_inspect import COMMON_ACTIVE

    owner_uid = os.geteuid()  # Production CLI permits only FreeBSD uid 0 + FD9.
    if not isinstance(release, Path) or not release.is_absolute():
        raise PostDropRefused("invalid_original_observer_release")
    if (release != COMMON_ACTIVE and
            (release.name != "release" or release.parent.parent != WORK or
             re.fullmatch(r"[a-f0-9]{32}", release.parent.name) is None)):
        raise PostDropRefused("observer_release_outside_original_owner")
    directory = release.lstat()
    if (not stat.S_ISDIR(directory.st_mode) or
            directory.st_uid != owner_uid or directory.st_mode & 0o022):
        raise PostDropRefused("untrusted_original_observer_release_directory")
    raw = _secure_bytes(release / MAP_NAME, MAX_MAP, owner_uid)
    argv = _secure_bytes(release / "dvtws.args", MAX_ARGS, owner_uid)
    try:
        mapping = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise PostDropRefused("corrupt_original_observer_generation") from exc
    if (not isinstance(mapping, dict) or
            not isinstance(mapping.get("generation"), str) or
            not re.fullmatch(r"[a-f0-9]{32}", mapping["generation"]) or
            not isinstance(mapping.get("owner_candidate_sha256"), str) or
            not re.fullmatch(r"[a-f0-9]{64}", mapping["owner_candidate_sha256"])):
        raise PostDropRefused("unqualified_original_observer_generation")
    operation = mapping["generation"]
    digest = mapping["owner_candidate_sha256"]
    work = WORK / operation
    if release not in (work / "release", COMMON_ACTIVE):
        raise PostDropRefused("observer_release_outside_original_owner")
    # Verify the immutable candidate bundle before comparing this release;
    # live ACTIVE_DIR is an exact copy only after the existing atomic install.
    verify_seal(work, owner=owner_uid)
    expected = verify_original_promotion(work, digest)
    _valid_map(raw, {"id": operation, "candidate": digest}, argv)
    if (expected["generation"] != operation or
            expected["final_args_sha256"] != mapping["final_args_sha256"] or
            _secure_bytes(work / "release" / MAP_NAME, MAX_MAP, owner_uid) != raw or
            _secure_bytes(work / "release" / "dvtws.args", MAX_ARGS, owner_uid) != argv):
        raise PostDropRefused("original_observer_differs_from_sealed_candidate")
    # The valid map and original source are prerequisites to the ORIGINAL
    # pretraffic/epoch proof, not a bypass around that later proof.


def native_prepare_original_producer() -> None:
    """Create/verify original native producer before launch, under FD9 only.

    A retained raw/debug/pending from any prior generation is never reset
    or reassigned. The original capture/seal-epoch gate separately demands
    genuine empty, distinct inodes before any new observer starts.
    """
    from auto_detect_storage import prepare_native
    prepare_native()


# Route the sole original FD9 through the existing immutable
# pretraffic -> committed process epoch. Release authorization is read-only
# and never by itself permits launch, receipt ACK or native file deletion.
def _original_epoch_queue(learning_names: tuple[str, ...] = ()):
    from auto_detect_epoch_receipts import EpochReceipts
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise PostDropRefused("native_root_fd9_epoch_only")
    _parent(ROOT, 0)
    native_user = pwd.getpwnam(ENGINE_USER)
    if native_user.pw_uid <= 0 or native_user.pw_gid <= 0:
        raise PostDropRefused("unqualified_original_epoch_engine")
    _check_layout(ROOT, 0, 0, native_user.pw_gid, learning_names)
    return (DurableInbox(ROOT, owner_uid=0, writer_gid=native_user.pw_gid),
            EpochReceipts(writer_gid=native_user.pw_gid))


def native_seal_original_epoch(generation: str, candidate: str) -> None:
    from auto_detect_epoch_receipts import HEX32, HEX64
    from shared_apply_seal import WORK
    if (not isinstance(generation, str) or not HEX32.fullmatch(generation)
            or not isinstance(candidate, str) or not HEX64.fullmatch(candidate)):
        raise PostDropRefused("invalid_original_epoch_candidate")
    queue, receipts = _original_epoch_queue()
    with queue.exclusive():
        receipts.seal_pretraffic(
            queue, workspace=WORK / generation, candidate_sha256=candidate)


def native_finish_original_epoch(generation: str, *, reviewed: bool = False) -> None:
    from auto_detect_epoch_receipts import HEX32
    from auto_detect_owner import (attest_epoch_finalizing_generation,
                                   attest_reviewed_native_generation)
    if not isinstance(generation, str) or not HEX32.fullmatch(generation):
        raise PostDropRefused("invalid_original_epoch_generation")
    # The reviewed rescue uses the SAME original queue/pretraffic receipt,
    # never a new epoch or a different owning generation. It is deliberately
    # separate from the ordinary first Apply and from the public minute gate.
    attester = (attest_reviewed_native_generation if reviewed
                else attest_epoch_finalizing_generation)
    proof = attester(generation)
    if proof.generation != generation or proof.operation_id != generation:
        raise PostDropRefused("precommit_original_owner_differs")
    queue, receipts = _original_epoch_queue()
    with queue.exclusive():
        receipts.finish_running(
            proof, queue, attest=lambda: attester(generation))




# TZ6v4: the SAME original FD9 owner now has a schema3-native command
# surface. Nothing invokes these verbs from common Apply/launcher yet.
# The writer and minute/ACK paths remain deliberately schema2-only until
# multi-inbox P2 proves managed-before-native transfer and retirement.
def _learning_release_sources(
    release: Path, *, work_parent: Path | None = None,
) -> tuple[Path, str, tuple[tuple[int, str, str], ...]]:
    """Attest the exact sealed original candidate and optional active copy.

    Root-only FreeBSD/FD9 is enforced by original_fd9_command, *not* by a
    supplied release pathname. A fresh generation must be root-sealed,
    match the original source/argv and have a reproducible approved N-map.
    """
    from auto_detect_owner import (
        _secure_bytes, _valid_learning_active, MAP_NAME, MAX_ARGS, MAX_MAP,
    )
    from auto_detect_origin_map import ORIGIN_FILE, verify_learning_promotion
    from shared_apply_seal import WORK, verify_seal
    from voice_live_inspect import COMMON_ACTIVE
    import json

    uid = os.geteuid()
    if (not isinstance(release, Path) or not release.is_absolute() or
            release.is_symlink() or not release.is_dir() or
            release.stat().st_uid != uid or release.stat().st_mode & 0o022):
        raise PostDropRefused("learning_untrusted_release_directory")
    raw_map = _secure_bytes(release / MAP_NAME, MAX_MAP, uid)
    try:
        mapping = json.loads(raw_map)
        generation = mapping["generation"]
        candidate = mapping["owner_candidate_sha256"]
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise PostDropRefused("learning_untrusted_generation_map") from exc
    if (not isinstance(generation, str) or
            not re.fullmatch(r"[0-9a-f]{32}", generation) or
            not isinstance(candidate, str) or
            not re.fullmatch(r"[0-9a-f]{64}", candidate)):
        raise PostDropRefused("learning_unqualified_operation")
    workspace = (WORK if work_parent is None else work_parent) / generation
    sealed = workspace / "release"
    if release not in ((sealed, COMMON_ACTIVE) if work_parent is None else (sealed,)):
        raise PostDropRefused("learning_release_outside_original_owner")
    verify_seal(workspace, owner=uid)
    expected = verify_learning_promotion(workspace, candidate)
    if json.loads(raw_map) != expected:
        raise PostDropRefused("learning_active_map_not_same_sealed_candidate")
    for name, limit in (
        (MAP_NAME, MAX_MAP),
        ("dvtws.args", MAX_ARGS),
        ("dvtws.original.args", MAX_ARGS),
        (ORIGIN_FILE, MAX_MAP),
        ("dvtws.args.global-policy.json", 16384),
    ):
        if name == "dvtws.args.global-policy.json":
            has_active = (release / name).exists() or (release / name).is_symlink()
            has_sealed = (sealed / name).exists() or (sealed / name).is_symlink()
            if has_active != has_sealed:
                raise PostDropRefused("learning_active_exclusion_policy_drift")
            if not has_active:
                continue
        if _secure_bytes(release / name, limit, uid) != _secure_bytes(
                sealed / name, limit, uid):
            raise PostDropRefused("learning_active_release_not_same_sealed_candidate")
    source = json.loads(_secure_bytes(release / ORIGIN_FILE, MAX_MAP, uid))
    approved = _valid_learning_active(
        raw_map, {"id": generation, "candidate": candidate}, source,
        _secure_bytes(release / "dvtws.original.args", MAX_ARGS, uid),
        _secure_bytes(release / "dvtws.args", MAX_ARGS, uid))
    native_generation, _ = _qualified_learning_sources(approved, ROOT)
    if native_generation != generation:
        raise PostDropRefused("learning_source_foreign_generation")
    return workspace, candidate, approved


def native_prepare_learning_producer(release: Path, *, queue_fd: int | None = None) -> None:
    """Prepare linked Auto inboxes only after original stopped retirement.

    First bound activation prepared inboxes before Config FD4. A linked
    stopped successor must borrow FD3, attest completed previous retirement,
    then create fresh N-inboxes under the original P2a owner.
    """
    from auto_detect_storage import prepare_native_learning
    from shared_apply_operation import SharedApplyOperation
    from voice_live_inspect import COMMON_ACTIVE

    workspace, candidate, sources = _learning_release_sources(release)
    _, names = _qualified_learning_sources(sources, ROOT)
    record = SharedApplyOperation(owner=0).read()
    if queue_fd is None:
        if type(record) is dict and record.get("manifest", {}).get("schema") == 2:
            raise PostDropRefused("bound_learning_prepare_requires_inherited_queue")
        prepare_native_learning(names)
        return
    if (release != COMMON_ACTIVE or type(queue_fd) is not int or queue_fd != 3 or
            type(record) is not dict or record.get("manifest", {}).get("schema") != 2):
        raise PostDropRefused("bound_learning_prepare_scope_required")
    if "previous" not in record:
        # The first-bound coordinator already created the protected files.
        # Never create or repair a first generation while holding Config.
        before = _learning_pretraffic_owner(
            workspace, candidate, queue_fd, learning_names=names)
        queue, _ = _original_epoch_queue(names)
        with queue.inherited_exclusive(queue_fd):
            if _learning_pretraffic_owner(
                    workspace, candidate, queue_fd, learning_names=names) != before:
                raise PostDropRefused("first_bound_learning_prepare_changed")
        return
    # Before any new inode, authenticate the completed predecessor twice
    # against the exact base-only root and its original terminal archive.
    before = _learning_pretraffic_owner(
        workspace, candidate, queue_fd, learning_names=names, preparing=True)
    if _learning_pretraffic_owner(
            workspace, candidate, queue_fd, learning_names=names, preparing=True) != before:
        raise PostDropRefused("bound_learning_prepare_preimage_changed")
    prepare_native_learning(names)
    if (_learning_release_sources(release) != (workspace, candidate, sources) or
            _learning_pretraffic_owner(
                workspace, candidate, queue_fd, learning_names=names) != before):
        raise PostDropRefused("bound_learning_prepare_postimage_changed")


def _learning_pretraffic_owner(workspace: Path, candidate: str, queue_fd: int | None,
                              *, learning_names: tuple[str, ...] = (),
                              preparing: bool = False) -> tuple[dict, str | None] | None:
    """Verify original bound pretraffic under the inherited P2a lock."""
    from shared_apply_operation import SharedApplyOperation
    from shared_apply_seal import WORK
    from neutral_root_stage import verify_original_operation_pins
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    bound = type(record) is dict and record.get("manifest", {}).get("schema") == 2
    if queue_fd is None:
        if bound:
            raise PostDropRefused("bound_learning_requires_inherited_queue")
        return None
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(queue_fd) is not int or queue_fd < 3 or queue_fd in (4, 9) or
            not bound or record["phase"] != "activating" or "found" in record or
            workspace != WORK / record["detail"]["id"] or
            candidate != record["detail"]["candidate"] or
            (preparing and ("previous" not in record or not learning_names))):
        raise PostDropRefused("bound_learning_queue_scope_required")
    verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
    retired = None
    if "previous" in record:
        from auto_detect_origin_map import verify_learning_start_successor
        from neutral_schema3_quiescent_preimage import (
            EPOCH_ROOT, _retired_ready_digest, _verify_retired_history,
            _verify_idle_producer,
        )

        detail, prior = record["detail"], record["previous"]
        if (record.get("previous_manifest", {}).get("schema") != 2 or
                prior.get("id") == detail["id"] or prior.get("candidate") != candidate or
                detail["base"] != candidate or detail["changed_fields"] != [] or
                detail["page"] != "strategies" or not learning_names):
            raise PostDropRefused("bound_learning_start_predecessor_required")
        try:
            verify_learning_start_successor(WORK / prior["id"], workspace, candidate)
            queue, receipts = _original_epoch_queue(() if preparing else learning_names)
            with queue.inherited_exclusive(queue_fd):
                if preparing:
                    _verify_idle_producer(queue, receipts)
                retired = _retired_ready_digest(EPOCH_ROOT, prior["id"], 0)
                _verify_retired_history(record, queue, receipts, retired)
                if _retired_ready_digest(EPOCH_ROOT, prior["id"], 0) != retired:
                    raise PostDropRefused("bound_learning_start_retirement_changed")
        except (OSError, ValueError, RuntimeError) as exc:
            raise PostDropRefused("bound_learning_start_retirement_unverified") from exc
    if store.read() != record:
        raise PostDropRefused("bound_learning_queue_owner_changed")
    return record, retired


def native_capture_learning_before_launch(release: Path, *, queue_fd: int | None = None) -> str:
    """Exact original P2a zero-cut witness for every learning native file."""
    from voice_live_inspect import COMMON_ACTIVE
    workspace, candidate, sources = _learning_release_sources(release)
    if queue_fd is not None and release != COMMON_ACTIVE:
        raise PostDropRefused("bound_learning_active_release_required")
    _, names = _qualified_learning_sources(sources, ROOT)
    owner = _learning_pretraffic_owner(workspace, candidate, queue_fd, learning_names=names)
    _parent(ROOT, 0)
    identity = pwd.getpwnam(ENGINE_USER)
    if identity.pw_uid <= 0 or identity.pw_gid <= 0:
        raise PostDropRefused("learning_engine_identity_missing")
    witness = _capture(
        ROOT, root_uid=0, root_gid=0,
        engine_uid=identity.pw_uid, engine_gid=identity.pw_gid,
        learning_names=names, queue_fd=queue_fd)
    if (_learning_release_sources(release) != (workspace, candidate, sources) or
            _learning_pretraffic_owner(workspace, candidate, queue_fd, learning_names=names) != owner):
        raise PostDropRefused("bound_learning_capture_owner_changed")
    return _witness_line_learning(witness, sources)


def native_seal_learning_epoch(
    generation: str, candidate: str, wire: str, *, queue_fd: int | None = None,
) -> None:
    from auto_detect_epoch_receipts import HEX32, HEX64
    from voice_live_inspect import COMMON_ACTIVE
    if (not isinstance(generation, str) or not HEX32.fullmatch(generation) or
            not isinstance(candidate, str) or not HEX64.fullmatch(candidate) or
            not isinstance(wire, str)):
        raise PostDropRefused("learning_invalid_pretraffic_request")
    workspace, observed_candidate, sources = _learning_release_sources(
        COMMON_ACTIVE)
    if (workspace.name != generation or observed_candidate != candidate):
        raise PostDropRefused("learning_epoch_candidate_not_original")
    _, names = _qualified_learning_sources(sources, ROOT)
    queue, receipts = _original_epoch_queue(names)
    identity = pwd.getpwnam(ENGINE_USER)
    owner = _learning_pretraffic_owner(workspace, candidate, queue_fd, learning_names=names)

    def same_owner() -> bool:
        return (_learning_release_sources(COMMON_ACTIVE) == (
            workspace, candidate, sources) and
            _learning_pretraffic_owner(workspace, candidate, queue_fd, learning_names=names) == owner)
    with (queue.exclusive() if queue_fd is None else queue.inherited_exclusive(queue_fd)):
        receipts.seal_learning_pretraffic(
            queue, workspace=workspace, candidate_sha256=candidate,
            wire=wire, root_gid=0, engine_uid=identity.pw_uid,
            attest=same_owner)


def native_restore_learning_before_ipfw(
    wire: str, pid_text: str, executable: str,
    generation: str, candidate: str,
) -> None:
    from voice_live_inspect import COMMON_ACTIVE
    workspace, observed_candidate, sources = _learning_release_sources(
        COMMON_ACTIVE)
    if (workspace.name != generation or observed_candidate != candidate):
        raise PostDropRefused("learning_postdrop_not_same_candidate")
    witness = _witness_read_learning(wire, sources)
    owner = _original_owner_from_pid(pid_text, executable)
    native_restore_before_ipfw(witness, owner)
    if _learning_release_sources(COMMON_ACTIVE) != (
            workspace, candidate, sources):
        raise PostDropRefused("learning_postdrop_owner_changed")


def native_finish_first_bound_learning_epoch_locked(record: dict, *, config_fd: int,
                                                     config_digest: str, queue_fd: int) -> dict:
    """Finish the original first Auto epoch using borrowed FD9/P2a/FD4."""
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from auto_detect_owner import attest_learning_epoch_finalizing_generation
    from neutral_root_stage import verify_original_operation_pins
    from neutral_schema3_previous_physical import _full_prior_tree, _running_native
    from shared_apply_operation import SharedApplyOperation, _first_running_pin_matches, DIGEST
    from shared_apply_seal import WORK
    from voice_ipfw_adapter import require_lifecycle_lock, FreeBSDIPFWAdapter, shared_release_manifest
    from voice_firewall_transaction import verify_prior_state
    from voice_live_inspect import COMMON_ACTIVE, CHILD_PID, MONITOR_PID

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(record) is not dict or record.get("phase") != "epoch-finalizing" or
            "previous" in record or "previous_manifest" in record or "found" in record or
            record.get("manifest", {}).get("schema") != 2 or
            type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
            type(queue_fd) is not int or queue_fd < 3 or queue_fd in (9, config_fd) or
            any(type(record.get(key)) is not str or not DIGEST.fullmatch(record[key])
                for key in ("first_running_sha256", "first_pretraffic_sha256"))):
        raise PostDropRefused("first_bound_epoch_scope_required")
    detail = record["detail"]
    if config_digest != detail["candidate"]:
        raise PostDropRefused("first_bound_epoch_config_changed")
    store = SharedApplyOperation(owner=0)
    work = WORK / detail["id"]
    release = work / "release"

    def attest():
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        if store.read() != record:
            raise PostDropRefused("first_bound_epoch_owner_changed")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        _full_prior_tree(work, COMMON_ACTIVE, 0)
        proof = attest_learning_epoch_finalizing_generation(detail["id"])
        running = _running_native(release, owner_uid=0, child_pidfile=CHILD_PID,
                                  monitor_pidfile=MONITOR_PID)
        if (proof.operation_id != detail["id"] or proof.generation != detail["id"] or
                proof.owner_candidate_sha256 != config_digest or
                (proof.owner.pid, proof.owner.started) != (running.pid, running.started) or
                not _first_running_pin_matches(record, running, config_fd,
                    pretraffic_sha256=record["first_pretraffic_sha256"])):
            raise PostDropRefused("first_bound_epoch_running_changed")
        desired = shared_release_manifest(release)
        if desired["rule_base"] != 19000 or desired["rule_max"] not in (19010, 19099):
            raise PostDropRefused("first_bound_epoch_kernel_scope_invalid")
        verify_prior_state(FreeBSDIPFWAdapter(19000, 19099), desired, desired)
        if store.read() != record:
            raise PostDropRefused("first_bound_epoch_owner_changed")
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return proof

    proof = attest()
    workspace, candidate, sources = _learning_release_sources(COMMON_ACTIVE)
    if (workspace != work or candidate != config_digest or sources != proof.learning):
        raise PostDropRefused("first_bound_epoch_source_changed")
    _, names = _qualified_learning_sources(sources, ROOT)
    queue, receipts = _original_epoch_queue(names)
    with queue.inherited_exclusive(queue_fd):
        os.fsync(config_fd)
        data = receipts.finish_learning_running(proof, queue, workspace=work,
            attest=attest, expected_pretraffic_sha256=record["first_pretraffic_sha256"])
        if (data.get("pretraffic_sha256") != record["first_pretraffic_sha256"] or
                receipts.verify_learning_stopped_epoch(proof, workspace=work) != data or
                attest() != proof):
            raise PostDropRefused("first_bound_epoch_readback_changed")
        return data


def native_finish_learning_epoch(generation: str) -> None:
    """Finish original schema3 receipt only after real shared Apply PID gate."""
    from auto_detect_epoch_receipts import HEX32
    from auto_detect_owner import attest_learning_epoch_finalizing_generation
    from voice_live_inspect import COMMON_ACTIVE
    if not isinstance(generation, str) or not HEX32.fullmatch(generation):
        raise PostDropRefused("learning_invalid_running_generation")
    attester = attest_learning_epoch_finalizing_generation
    proof = attester(generation)
    from shared_apply_operation import SharedApplyOperation, _first_running_pin_scope
    record = SharedApplyOperation(owner=0).read()
    if (record is not None and record["detail"]["id"] == generation and
            _first_running_pin_scope(record) and record["manifest"]["schema"] == 2):
        # A bound first Auto generation must not bypass its durable pair or
        # acquire another queue lock through the legacy FD9-only command.
        raise PostDropRefused("first_bound_epoch_requires_original_config_queue")
    workspace, candidate, sources = _learning_release_sources(COMMON_ACTIVE)
    if (proof.operation_id != generation or
            workspace.name != generation or
            proof.owner_candidate_sha256 != candidate or
            proof.learning != sources):
        raise PostDropRefused("learning_running_owner_not_same_generation")
    _, names = _qualified_learning_sources(sources, ROOT)
    queue, receipts = _original_epoch_queue(names)
    with queue.exclusive():
        receipts.finish_learning_running(
            proof, queue, workspace=workspace,
            attest=lambda: attester(generation))


# P2k8i: the two half-calls are a *single* original-FD9 shell operation.
# No new lock, Config parser, queue owner or on-disk witness is introduced.
# The compact witness crosses launcher_start_once as an exact positional
# argument, never through a detached daemon or a public worker.
_WITNESS = re.compile(r"^p2k8i:([0-9]+):([0-9]+):([0-9]+):([0-9]+):([0-9]+):([0-9]+)$")


def _witness_line(witness: OriginalProducer) -> str:
    if (not isinstance(witness, OriginalProducer) or
            witness.learning_names or len(witness.identities) != 2):
        raise PostDropRefused("legacy_fd9_witness_cannot_encode_learning_inboxes")
    a, b = witness.identities
    return "p2k8i:" + ":".join(str(v) for v in (*a, *b))


def _witness_read(line: str) -> OriginalProducer:
    if not isinstance(line, str) or len(line) > 192:
        raise PostDropRefused("invalid_original_fd9_prelaunch_witness")
    found = _WITNESS.fullmatch(line)
    if found is None:
        raise PostDropRefused("invalid_original_fd9_prelaunch_witness")
    values = tuple(int(x) for x in found.groups())
    if any(n > (1 << 64) - 1 for n in values) or values[2] != 1 or values[5] != 1:
        raise PostDropRefused("invalid_original_fd9_prelaunch_witness")
    # Do not call native_capture_before_launch() again here: the verified
    # upstream credential drop legitimately chowns inbox.txt to nobody.
    # _reattest() immediately checks both protected named/open inodes against
    # this original prelaunch witness and rejects every other UID.
    _parent(ROOT, 0)
    native_user = pwd.getpwnam(ENGINE_USER)
    if native_user.pw_uid <= 0 or native_user.pw_gid <= 0:
        raise PostDropRefused("unqualified_original_engine_user")
    return OriginalProducer(
        ROOT, 0, 0, native_user.pw_uid, native_user.pw_gid,
        (values[:3], values[3:]),
    )



# TZ6v4: versioned, complete post-drop evidence across the same original
# launch argument. The existing six-u64 p2k8i wire stays LEGACY-ONLY and
# cannot silently truncate N learning inodes. These codecs are NOT new CLI
# operations: the actual FD9 entrypoint must first verify a sealed schema3
# map, resolve the expected tuples, and seal a matching original epoch.
_LEARNING_WITNESS = re.compile(
    r"^p2k8i3:([0-9a-f]{32}):([1-9][0-9]{0,2}):([0-9a-f]{64}):([0-9:]+)$")
_MAX_LEARNING_WITNESS = 16384
_U64_MAX = (1 << 64) - 1


def _qualified_learning_sources(
    sources: tuple[tuple[int, str, str], ...], root: Path,
) -> tuple[str, tuple[str, ...]]:
    """Only an independently attested native-number/hostlist/path map fits.

    The caller must obtain these tuples from _valid_learning_proposal (and
    later the sealed active schema3 owner), not by trusting debug or argv
    guesses. The codec checks exact paths and numbering but cannot by
    itself authorize that caller or a new runtime.
    """
    if (type(sources) is not tuple or not 1 <= len(sources) <= 255 or
            not isinstance(root, Path) or not root.is_absolute()):
        raise PostDropRefused("unqualified_learning_fd9_source_set")
    names = []
    for row in sources:
        if (type(row) is not tuple or len(row) != 3 or
                type(row[0]) is not int or not 1 <= row[0] <= 255 or
                type(row[1]) is not str or not
                re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", row[1]) or
                type(row[2]) is not str):
            raise PostDropRefused("unqualified_learning_fd9_profile")
        path = Path(row[2])
        if (not path.is_absolute() or path.parent != root or
                path.name != f"learning-{path.name[9:41]}-{row[0]}.txt"):
            raise PostDropRefused("unqualified_learning_fd9_path")
        names.append(path.name)
    try:
        _learning_names(tuple(names))
    except StorageRefused as exc:
        raise PostDropRefused("unqualified_learning_fd9_names") from exc
    generation = names[0][9:41]
    if any(name[9:41] != generation for name in names):
        raise PostDropRefused("mixed_learning_fd9_generations")
    return generation, tuple(names)


def _learning_source_digest(sources: tuple[tuple[int, str, str], ...]) -> str:
    # Pin attribution as well as native paths; changing hostlist while
    # keeping the same inode names must invalidate the FD9 witness.
    canonical = "\x00".join(
        f"{number}: {hostlist}: {path}" for number, hostlist, path in sources)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _learning_identity_values(identities: tuple[tuple[int, int, int], ...],
                              count: int) -> tuple[int, ...]:
    if (type(identities) is not tuple or len(identities) != count + 2 or
            len(identities) > 257):
        raise PostDropRefused("incomplete_learning_fd9_inode_set")
    values = []
    seen = set()
    for item in identities:
        if (type(item) is not tuple or len(item) != 3 or
                any(type(n) is not int or n < 0 or n > _U64_MAX for n in item) or
                item[1] == 0 or item[2] != 1 or item[:2] in seen):
            raise PostDropRefused("unqualified_learning_fd9_inode")
        seen.add(item[:2])
        values.extend(item)
    return tuple(values)


def _witness_line_learning(
    witness: OriginalProducer, sources: tuple[tuple[int, str, str], ...],
) -> str:
    """Encode the FULL original producer inode set; never drop N identities."""
    if not isinstance(witness, OriginalProducer):
        raise PostDropRefused("missing_learning_fd9_capture")
    generation, names = _qualified_learning_sources(sources, witness.root)
    if witness.learning_names != names:
        raise PostDropRefused("learning_fd9_capture_not_source_bound")
    values = _learning_identity_values(witness.identities, len(names))
    digest = _learning_source_digest(sources)
    line = f"p2k8i3:{generation}:{len(names)}:{digest}:" + ":".join(map(str, values))
    if len(line) > _MAX_LEARNING_WITNESS:
        raise PostDropRefused("learning_fd9_wire_exceeds_limit")
    return line


def _witness_decode_learning(
    line: str, sources: tuple[tuple[int, str, str], ...], *,
    root: Path, root_uid: int, root_gid: int,
    engine_uid: int, engine_gid: int,
) -> OriginalProducer:
    """Refuse missing, extra, reordered or cross-generation prelaunch inodes.

    The names are obtained separately from the sealed native profile map.
    This primitive performs NO file repair; _reattest reopens every path
    and verifies each inode under the original process/FD9 authority.
    """
    generation, names = _qualified_learning_sources(sources, root)
    if (type(line) is not str or len(line) > _MAX_LEARNING_WITNESS):
        raise PostDropRefused("invalid_learning_fd9_witness")
    found = _LEARNING_WITNESS.fullmatch(line)
    if (found is None or found[1] != generation or
            int(found[2]) != len(names) or str(int(found[2])) != found[2] or
            found[3] != _learning_source_digest(sources)):
        raise PostDropRefused("learning_fd9_witness_generation_or_count")
    tokens = found[4].split(":")
    if len(tokens) != 3 * (len(names) + 2) or any(
            not token or len(token) > 20 or
            str(int(token)) != token for token in tokens):
        raise PostDropRefused("learning_fd9_witness_inode_count")
    values = tuple(int(token) for token in tokens)
    identities = tuple(tuple(values[i:i + 3])
                       for i in range(0, len(values), 3))
    _learning_identity_values(identities, len(names))
    if (type(root_uid) is not int or type(root_gid) is not int or
            type(engine_uid) is not int or type(engine_gid) is not int or
            root_uid < 0 or root_gid < 0 or engine_uid <= 0 or
            engine_gid <= 0 or root_uid == engine_uid):
        raise PostDropRefused("invalid_learning_fd9_engine_identity")
    return OriginalProducer(root, root_uid, root_gid, engine_uid, engine_gid,
                            identities, names)


def _witness_read_learning(
    line: str, sources: tuple[tuple[int, str, str], ...],
) -> OriginalProducer:
    """Native FD9-only companion to the sealed, schema3 qualified map."""
    _parent(ROOT, 0)
    native_user = pwd.getpwnam(ENGINE_USER)
    if native_user.pw_uid <= 0 or native_user.pw_gid <= 0:
        raise PostDropRefused("unqualified_original_engine_user")
    return _witness_decode_learning(
        line, sources, root=ROOT, root_uid=0, root_gid=0,
        engine_uid=native_user.pw_uid, engine_gid=native_user.pw_gid)



def _original_owner_from_pid(pid_text: str, executable: str) -> OwnerToken:
    if (not isinstance(pid_text, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", pid_text)
            or not isinstance(executable, str) or not executable.startswith("/")
            or not executable.endswith("/dvtws2") or "\x00" in executable or
            any(c.isspace() for c in executable)):
        raise PostDropRefused("invalid_original_launcher_identity")
    pid = int(pid_text)
    try:
        reply = subprocess.run(
            ["/bin/ps", "-ww", "-p", str(pid), "-o", "lstart=", "-o", "command="],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PostDropRefused("original_launcher_process_unavailable") from exc
    if reply.returncode or reply.stderr or len(reply.stdout) > 131072:
        raise PostDropRefused("original_launcher_process_unavailable")
    lines = reply.stdout.strip().splitlines()
    if len(lines) != 1:
        raise PostDropRefused("original_launcher_process_unavailable")
    fields = lines[0].split(maxsplit=5)
    if len(fields) != 6:
        raise PostDropRefused("original_launcher_process_unavailable")
    started = " ".join(fields[:5])
    token = OwnerToken(pid, started, executable)
    if not _owner_snapshot(token, subprocess.run):
        raise PostDropRefused("original_launcher_owner_changed")
    return token


def original_fd9_command(args: list[str]) -> int:
    """Restricted internal CLI, only from inherited original held FD9.

    A source-verified promoted release may pass the read-only authorize
    gate, but the original pretraffic/queue and post-drop process proof are
    still mandatory before the engine can be connected to IPFW.
    """
    shapes = {"authorize": 2, "prepare": 1, "capture": 1,
              "restore": 4, "seal-epoch": 3, "finish-epoch": 2,
              "finish-reviewed-epoch": 2,
              "authorize-learning": 2, "prepare-learning": 2,
              "capture-learning": 2, "seal-learning-epoch": 4,
              "restore-learning": 6, "finish-learning-epoch": 2}
    borrowed = bool(args and args[-1] == "--inherited-queue")
    if borrowed:
        if args[0] not in ("prepare-learning", "capture-learning", "seal-learning-epoch"):
            return 64
        args = args[:-1]
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not args or len(args) != shapes.get(args[0], -1)):
        return 64
    queue_fd = 3 if borrowed else None
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()  # REAL original same-OFD held FD9, no new lock.
        if args[0] == "authorize":
            native_authorize_original_release(Path(args[1]))
            print("original-fd9-observer=authorized")
        elif args[0] == "prepare":
            native_prepare_original_producer()
            print("original-fd9-producer=prepared")
        elif args[0] == "capture":
            print(_witness_line(native_capture_before_launch()))
        elif args[0] == "restore":
            # Caller already started the single original engine. A false
            # witness, missing original FD9 or replaced process refuses.
            witness = _witness_read(args[1])
            owner = _original_owner_from_pid(args[2], args[3])
            native_restore_before_ipfw(witness, owner)
            print("original-fd9-postdrop=attested")
        elif args[0] == "seal-epoch":
            native_seal_original_epoch(args[1], args[2])
            print("original-fd9-pretraffic=sealed")
        elif args[0] == "finish-reviewed-epoch":
            native_finish_original_epoch(args[1], reviewed=True)
            print("original-fd9-reviewed-epoch=attested")
        elif args[0] == "authorize-learning":
            _learning_release_sources(Path(args[1]))
            print("original-fd9-learning-release=authorized")
        elif args[0] == "prepare-learning":
            native_prepare_learning_producer(Path(args[1]), queue_fd=queue_fd)
            print("original-fd9-learning-producer=prepared")
        elif args[0] == "capture-learning":
            print(native_capture_learning_before_launch(Path(args[1]), queue_fd=queue_fd))
        elif args[0] == "seal-learning-epoch":
            native_seal_learning_epoch(args[1], args[2], args[3], queue_fd=queue_fd)
            print("original-fd9-learning-pretraffic=sealed")
        elif args[0] == "restore-learning":
            native_restore_learning_before_ipfw(
                args[1], args[2], args[3], args[4], args[5])
            print("original-fd9-learning-postdrop=attested")
        elif args[0] == "finish-learning-epoch":
            native_finish_learning_epoch(args[1])
            print("original-fd9-learning-running-epoch=attested")
        else:
            native_finish_original_epoch(args[1])
            print("original-fd9-running-epoch=attested")
        return 0
    except Exception as exc:
        # Catch the original FD9 adapter's refusal as well as process errors.
        # Do not print a traceback, raw argv or any private Config/hostlist.
        # No raw domain, process argv or private witness leaks in diagnostics.
        print("original-fd9-postdrop-refused=" + type(exc).__name__,
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(original_fd9_command(sys.argv[1:]))
