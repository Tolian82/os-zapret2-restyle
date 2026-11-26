#!/usr/bin/env python3
"""Original FD9 quiescent preimage for bound All/List/Auto Apply (read-only).

Reuse the installed retirement verifier, never retire, repair, initialize
a producer, remove PID files, load IPFW or advance the journal here.
A stopped old owner and a genuinely empty first-install scope are distinct.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import subprocess

from auto_detect_owner import _run, GenerationRefused, MAP_NAME
from auto_detect_minute import inspect_inert_release, MinuteRefused
from auto_detect_storage import ROOT as PRODUCER_ROOT
from auto_detect_epoch_receipts import ROOT as EPOCH_ROOT
from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_bound_preflight import _attest_bound_candidate, BoundRootRefused
from neutral_schema3_previous_physical import _full_prior_tree, PreviousPhysicalRefused
from neutral_schema3_saved_wan_preimage import (
    _attest_saved_wan, _native_call, _native_preflight, _native_wan,
    _qualified_config, SavedWanPreimageReceipt, SavedWanPreimageRefused,
    _DEVICE, _WAN_STATE_MARKERS,
)
from shared_apply_operation import (
    SharedApplyOperation, SharedOperationError, DEFAULT_ROOT, MANAGED_WRITING,
    MANAGED_CONFIG_SAVING,
)
from shared_apply_seal import WORK, SharedBundleError
from voice_ipfw_adapter import (
    FreeBSDIPFWAdapter, shared_release_manifest, require_lifecycle_lock,
)
from voice_firewall_transaction import verify_prior_state, VoiceFirewallError
from voice_live_inspect import (
    COMMON_ACTIVE, CHILD_PID, MONITOR_PID, CHILD_EXEC, MONITOR_EXEC,
    _ipfw_kernel_confirmed_absent,
)

SCRIPT = Path("/usr/local/opnsense/scripts/OPNsense/Zapret")
DAEMON_PID = Path("/var/run/zapret2-supervisor-daemon.pid")


class QuiescentPreimageRefused(ValueError):
    """Private nonauthorizing refusal."""


@dataclass(frozen=True)
class QuiescentPreimage:
    generation: str
    root_sha256: str
    previous_generation: str | None
    previous_release_sha256: str | None
    config_base_sha256: str
    config_candidate_sha256: str
    verified_wan_device: str | None
    old_state: str
    kernel_state: str
    retirement_state: str
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    original_executor_recheck_required: bool = True
    retired_ready_sha256: str | None = None
    idle_producer: tuple | None = None


def _present(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _safe_empty_directory(path: Path, uid: int) -> None:
    """No previous data, not even an empty foreign/symlink directory."""
    if not _present(path):
        return
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or
            info.st_mode & 0o022 or any(path.iterdir())):
        raise QuiescentPreimageRefused("QUIESCENT_RESIDUAL_DIRECTORY")


def _zero_processes(pidfiles: tuple[Path, ...], *, runner=subprocess.run) -> None:
    # Reuse original P2c's bounded native ps reader, not kill(0) failure.
    if any(_present(path) for path in pidfiles):
        raise QuiescentPreimageRefused("QUIESCENT_RESIDUAL_PIDFILE")
    raw = _run(runner, ["/bin/ps", "-A", "-ww", "-o", "pid=", "-o", "command="])
    seen = set()
    for line in raw.splitlines():
        row = line.split()
        if not row or not row[0].isdigit():
            raise QuiescentPreimageRefused("QUIESCENT_PROCESS_CENSUS_INVALID")
        pid = int(row[0])
        if pid in seen or (len(row) < 2 and pid not in (0, 1)):
            raise QuiescentPreimageRefused("QUIESCENT_PROCESS_CENSUS_INVALID")
        seen.add(pid)
        if len(row) < 2:
            continue
        command = row[1:]
        if (command[0] in (CHILD_EXEC, MONITOR_EXEC) or
                (command[0] == "/bin/sh" and MONITOR_EXEC in command[1:2]) or
                (command[0] in ("daemon:", "daemon", "/usr/sbin/daemon") and
                 any(token in (CHILD_EXEC, MONITOR_EXEC, "dvtws2",
                               "supervisor_loop.sh") or
                     token.startswith(("dvtws2[", "supervisor_loop.sh["))
                     for token in command[1:]))):
            raise QuiescentPreimageRefused("QUIESCENT_ORPHAN_PROCESS")
    if not seen or any(_present(path) for path in pidfiles):
        raise QuiescentPreimageRefused("QUIESCENT_PROCESS_CENSUS_CHANGED")


def _empty_kernel(release: Path) -> str:
    # Candidate manifest validates the actual native source. The original
    # cold-kernel classifier requires both modules absent + exact errno 71.
    # Otherwise verify the *whole* current allocated ordinary/Voice interval
    # and all managed active/stage tables using the existing read-only adapter.
    desired = shared_release_manifest(release)
    if (desired["rule_base"] != 19000 or
            desired["rule_max"] not in (19010, 19099)):
        raise QuiescentPreimageRefused("QUIESCENT_IPFW_SCOPE_INVALID")
    if _ipfw_kernel_confirmed_absent():
        return "native-kernel-absent"
    empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
    adapter = FreeBSDIPFWAdapter(19000, 19099)
    verify_prior_state(adapter, empty, desired)
    return "native-managed-kernel-empty"


def _cold_files(active: Path, backups: Path, producer: Path, epochs: Path,
                uid: int) -> None:
    # A missing journal predecessor alone is not a first-install proof.
    # Accept only absent/pristine empty roots, not migration/orphan residue.
    for path in (active, backups, producer, epochs):
        _safe_empty_directory(path, uid)
    parent = active.parent
    info = parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or
            info.st_mode & 0o022):
        raise QuiescentPreimageRefused("QUIESCENT_ACTIVE_PARENT_UNTRUSTED")
    for item in parent.iterdir():
        if item.name.startswith((f".{active.name}.stage.", f".{active.name}.old.")):
            raise QuiescentPreimageRefused("QUIESCENT_ATOMIC_RESIDUE")


def _retired_ready(producer: Path, uid: int) -> None:
    # The existing P2a exclusive() may CREATE a missing worker.lock.
    # Require the original lock already present; do not initialize anything
    # while merely attesting a retired generation.
    lock = producer / "worker.lock"
    info = lock.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or
            info.st_gid != uid or stat.S_IMODE(info.st_mode) != 0o600 or
            info.st_nlink != 1):
        raise QuiescentPreimageRefused("QUIESCENT_EXISTING_P2_LOCK_REQUIRED")
    response = _native_call((
        str(SCRIPT / "python_runtime.sh"),
        str(SCRIPT / "backend/auto_detect_minute.py"), "--retired-ready"))
    if response != b"auto-detect-retire=ready\n":
        raise QuiescentPreimageRefused("QUIESCENT_ORIGINAL_RETIREMENT_INCOMPLETE")


def _retired_ready_digest(epochs: Path, generation: str, uid: int) -> str:
    from hashlib import sha256
    from auto_detect_epoch_receipts import EpochReceipts, _directory, _read
    from auto_detect_learning_retirement import RETIRE_DIR, READY

    archive = EpochReceipts(epochs, owner_uid=uid)._generation(
        generation, create=False) / RETIRE_DIR
    _directory(archive, uid)
    return sha256(_read(archive / READY, uid)).hexdigest()


def _verify_retired_history(record: dict, queue, receipts, expected: str) -> None:
    """Reuse the original historical ACK/archive verifier after promotion."""
    from auto_detect_learning_gc import qualified_completed_learning
    from shared_apply_operation import DIGEST
    if (record.get("previous_manifest", {}).get("schema") != 2 or
            type(expected) is not str or not DIGEST.fullmatch(expected)):
        raise QuiescentPreimageRefused("BOUND_RETIRED_HISTORY_REQUIRED")
    prior = record["previous"]
    qualified_completed_learning(
        receipts, queue, prior["id"], expected_candidate=prior["candidate"],
        expected_ready_sha256=expected)


def _verify_idle_producer(queue, receipts) -> tuple:
    """Exact idle original root after retirement or with an inert owner.

    Caller already holds P2a, has qualified the inert or retired owner.
    No new files, no read of mutable archive paths.
    """
    from auto_detect_learning_retirement import _image
    queue._verify()
    if (not queue._held or queue.segments() or
            set(os.listdir(queue.root)) != {"pending", "worker.lock", "inbox.txt", "debug.log"}):
        raise QuiescentPreimageRefused("BOUND_RETIRED_IDLE_LAYOUT_CHANGED")
    rows = []
    for path in (queue.inbox, queue.root / "debug.log"):
        image, _, data = _image(path, receipts, queue)
        if data:
            raise QuiescentPreimageRefused("BOUND_RETIRED_IDLE_DATA_CHANGED")
        rows.append(tuple(image))
    return tuple(rows)


def _observe_idle_producer(producer: Path, uid: int) -> tuple | None:
    """Before Config locking only: allow absent or exact idle original root."""
    if not _present(producer):
        return None
    info = producer.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or
            info.st_mode & 0o022):
        raise QuiescentPreimageRefused("BOUND_IDLE_PRODUCER_UNTRUSTED")
    if not any(producer.iterdir()):
        _safe_empty_directory(producer, uid)
        return None
    from auto_detect_post_drop import _original_epoch_queue
    queue, receipts = _original_epoch_queue()
    if queue.root != producer or queue.uid != uid:
        raise QuiescentPreimageRefused("BOUND_IDLE_ORIGINAL_SCOPE_REQUIRED")
    with queue.exclusive(existing_only=True):
        return _verify_idle_producer(queue, receipts)


def _verify_prior_idle_inode_identity(queue, expected: tuple) -> None:
    """A later learning launch may append, never replace original idle inodes."""
    for path, row in zip((queue.inbox, queue.root / "debug.log"), expected):
        info = path.lstat()
        if (info.st_dev, info.st_ino) != tuple(row[:2]):
            raise QuiescentPreimageRefused("BOUND_PRIOR_IDLE_INODE_CHANGED")


def _attest_quiescent(*, generation: str, native: NativeParity,
                      effective: EffectiveSnapshot, enabled: bool,
                      parent: Path, journal_root: Path, owner_uid: int,
                      active: Path, backups: Path, producer: Path, epochs: Path,
                      pidfiles: tuple[Path, ...],
                      runner=subprocess.run) -> QuiescentPreimage:
    try:
        store = SharedApplyOperation(journal_root, owner=owner_uid)
        before = store.read()
        if (type(enabled) is not bool or type(native) is not NativeParity or
                native.mode not in ("all", "list", "auto") or
                type(before) is not dict or before.get("phase") != "prepared" or
                "found" in before or type(before.get("manifest")) is not dict or
                type(before.get("detail")) is not dict or
                before["detail"].get("id") != generation):
            raise QuiescentPreimageRefused("QUIESCENT_ORIGINAL_BOUND_REQUIRED")
        schema3 = native.mode == "auto" and enabled
        if before["manifest"].get("schema") != (2 if schema3 else 1):
            raise QuiescentPreimageRefused("QUIESCENT_BOUND_MODE_MISMATCH")
        detail = before["detail"]
        old = before.get("previous")
        if old is not None and old["candidate"] != detail["base"]:
            raise QuiescentPreimageRefused("QUIESCENT_PREVIOUS_BASE_MISMATCH")
        args = dict(generation=generation, native=native, effective=effective,
                    enabled=enabled, parent=parent, journal_root=journal_root,
                    owner_uid=owner_uid)
        def observe():
            retired_digest = idle_producer = None
            _zero_processes(pidfiles, runner=runner)
            if old is None:
                root = _attest_bound_candidate(**args, mode=native.mode, schema3=schema3)
                _cold_files(active, backups, producer, epochs, owner_uid)
                if any(item.name != generation for item in parent.iterdir()):
                    raise QuiescentPreimageRefused("QUIESCENT_OLD_WORK_RESIDUE")
                config = _qualified_config(
                    _native_preflight(generation, detail["page"]), detail, enabled)
                wan = _native_wan() if enabled else None
                old_hash = None
                old_state, retirement = "first-install-empty", "no-prior-data"
            else:
                saved = _attest_saved_wan(**args)
                if (type(saved) is not SavedWanPreimageReceipt or
                        saved.generation != generation or
                        saved.previous_state != "stopped" or
                        saved.previous_generation != old["id"] or
                        saved.config_base_sha256 != old["candidate"] or
                        saved.root_sha256 != before["manifest"]["root_sha256"] or
                        saved.authorization != "NONE" or
                        saved.physical_transition_allowed or saved.promotion_allowed):
                    raise QuiescentPreimageRefused("QUIESCENT_STOPPED_OWNER_REQUIRED")
                root = saved
                config = (saved.config_base_sha256, saved.config_candidate_sha256)
                wan = saved.verified_wan_device
                old_hash = _full_prior_tree(parent / old["id"], active, owner_uid)
                if _present(active / MAP_NAME):
                    bound_learning = before.get("previous_manifest", {}).get("schema") == 2
                    if bound_learning:
                        retired_digest = _retired_ready_digest(epochs, old["id"], owner_uid)
                    _retired_ready(producer, owner_uid)
                    if bound_learning:
                        idle_producer = _observe_idle_producer(producer, owner_uid)
                        if (idle_producer is None or _retired_ready_digest(
                                epochs, old["id"], owner_uid) != retired_digest):
                            raise QuiescentPreimageRefused("QUIESCENT_RETIREMENT_READY_CHANGED")
                    retirement = "original-epoch-ack-retired"
                else:
                    # Original inert classifier rejects native auto flags
                    # without the matching map. Do not infer an empty queue
                    # from List mode: require no unexplained producer bytes.
                    if inspect_inert_release(active, owner_uid=owner_uid) != "inactive":
                        raise QuiescentPreimageRefused("QUIESCENT_INERT_OWNER_INVALID")
                    idle_producer = _observe_idle_producer(producer, owner_uid)
                    retirement = ("inert-no-producer-data" if idle_producer is None else
                                  "inert-idle-producer")
                old_state = "committed-stopped"
            kernel = _empty_kernel(parent / generation / "release")
            _zero_processes(pidfiles, runner=runner)
            if old is None:
                _cold_files(active, backups, producer, epochs, owner_uid)
                if any(item.name != generation for item in parent.iterdir()):
                    raise QuiescentPreimageRefused("QUIESCENT_OLD_WORK_RESIDUE")
            else:
                if _full_prior_tree(parent / old["id"], active, owner_uid) != old_hash:
                    raise QuiescentPreimageRefused("QUIESCENT_ACTIVE_TREE_CHANGED")
            if ((enabled and (type(wan) is not str or not _DEVICE.fullmatch(wan) or
                              wan in _WAN_STATE_MARKERS)) or
                    (not enabled and wan is not None) or
                    root.root_sha256 != before["manifest"]["root_sha256"] or
                    config[:2] != (detail["base"], detail["candidate"]) or
                    store.read() != before):
                raise QuiescentPreimageRefused("QUIESCENT_ORIGINAL_PROOF_CHANGED")
            return QuiescentPreimage(generation, root.root_sha256,
                None if old is None else old["id"], old_hash,
                config[0], config[1], wan, old_state, kernel, retirement,
                retired_ready_sha256=retired_digest, idle_producer=idle_producer)
        first = observe()
        if (observe() != first or
                _attest_bound_candidate(**args, mode=native.mode, schema3=schema3).root_sha256 !=
                first.root_sha256 or store.read() != before):
            raise QuiescentPreimageRefused("QUIESCENT_PREIMAGE_RACED")
        return first
    except (QuiescentPreimageRefused, SavedWanPreimageRefused,
            BoundRootRefused, PreviousPhysicalRefused, SharedOperationError,
            SharedBundleError, VoiceFirewallError, GenerationRefused,
            MinuteRefused, OSError, TypeError, KeyError, ValueError, RuntimeError,
            subprocess.SubprocessError):
        raise QuiescentPreimageRefused("ORIGINAL_QUIESCENT_PREIMAGE_REFUSED") from None


@dataclass(frozen=True)
class StagedBoundRuntimeReceipt:
    generation: str
    root_sha256: str
    config_base_sha256: str
    release_sha256: str
    backup_sha256: str | None
    running: object
    kernel_state: str
    observed_config_sha256: str | None = None
    pretraffic_sha256: str | None = None
    retired_ready_sha256: str | None = None
    idle_producer: tuple | None = None


def attest_bound_quiescent_staged_under_fd9(record: dict, *, preimage: QuiescentPreimage,
                                            config_fd: int, config_digest: str,
                                            queue_fd: int | None = None,
                                            saved: bool = False) -> StagedBoundRuntimeReceipt:
    """Reversible ordinary cutover before Config::save, not cold recovery.

    Use the original in-flight quiescent preimage, not a reconstruction
    of the old state after installation. Inert and learning candidates
    from an empty or stopped predecessor qualify here, including an exact
    bound retired learning predecessor. Learning or retired history borrows
    the original queue acquired BEFORE Config, not a second flock.
    No PHP calls, process signals, IPFW writes or journal mutations.
    """
    import sys
    import json
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from neutral_root_stage import (
        verify_original_operation_pins, _verify_original_pinned_root, _original_plan_matches)
    from neutral_schema3_previous_physical import _running_native
    from voice_firewall_transaction import verify_staged_state
    from shared_apply_seal import _stat
    from auto_detect_owner import attest_bound_learning_staged_generation
    from auto_detect_post_drop import _original_epoch_queue, _qualified_learning_sources

    try:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                type(record) is not dict or type(preimage) is not QuiescentPreimage or
                type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
                type(saved) is not bool):
            raise QuiescentPreimageRefused("BOUND_STAGED_NATIVE_SCOPE_REQUIRED")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
        if (store.read() != record or record["phase"] not in ("activating", "activated") or
                "found" in record or record.get("manifest", {}).get("schema") not in (1, 2) or
                record.get("previous_manifest", {}).get("schema", 1) not in (1, 2) or
                (saved and record["phase"] != "activated")):
            raise QuiescentPreimageRefused("BOUND_STAGED_ORDINARY_REQUIRED")
        detail, pin = record["detail"], record["manifest"]
        learning = pin["schema"] == 2
        retired = record.get("previous_manifest", {}).get("schema") == 2
        prior_idle = preimage.idle_producer
        needs_queue = learning or retired or prior_idle is not None
        if ((needs_queue and (type(queue_fd) is not int or queue_fd < 3 or
                              queue_fd in (9, config_fd))) or
                (not needs_queue and queue_fd is not None)):
            raise QuiescentPreimageRefused("BOUND_STAGED_ORIGINAL_QUEUE_SCOPE_REQUIRED")
        prior = record.get("previous")
        old_id = None if prior is None else prior["id"]
        if (preimage.generation != detail["id"] or preimage.root_sha256 != pin["root_sha256"] or
                preimage.config_base_sha256 != detail["base"] or
                config_digest != detail["candidate" if saved else "base"] or
                preimage.config_candidate_sha256 != detail["candidate"] or
                preimage.previous_generation != old_id or preimage.authorization != "NONE" or
                preimage.physical_transition_allowed or preimage.promotion_allowed or
                preimage.original_executor_recheck_required is not True or
                preimage.kernel_state not in ("native-kernel-absent", "native-managed-kernel-empty") or
                (prior is None and (preimage.old_state != "first-install-empty" or
                                    preimage.retirement_state != "no-prior-data" or
                                    preimage.previous_release_sha256 is not None or
                                    prior_idle is not None)) or
                (prior is not None and (preimage.old_state != "committed-stopped" or
                                        preimage.retirement_state != (
                                            "original-epoch-ack-retired" if retired else
                                            ("inert-idle-producer" if prior_idle is not None else
                                             "inert-no-producer-data")) or
                                        prior["candidate"] != detail["base"])) or
                (retired != (preimage.retired_ready_sha256 is not None)) or
                (retired and prior_idle is None) or
                (prior_idle is not None and (type(prior_idle) is not tuple or
                                             len(prior_idle) != 2 or
                                             any(type(row) is not tuple or len(row) != 4
                                                 for row in prior_idle)))):
            raise QuiescentPreimageRefused("BOUND_STAGED_PREIMAGE_CHANGED")
        work = WORK / detail["id"]
        release = work / "release"
        name = COMMON_ACTIVE.name
        backup = COMMON_ACTIVE.with_name("runtime-v2-backups") / f"{name}-{detail['id']}"
        stage = COMMON_ACTIVE.parent / f".{name}.stage.{detail['id']}"
        parked = COMMON_ACTIVE.parent / f".{name}.old.{detail['id']}"

        def observe():
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise QuiescentPreimageRefused("BOUND_STAGED_OWNER_CHANGED")
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
            root = json.loads(_verify_original_pinned_root(
                detail=detail, binding=pin, parent=WORK, owner_uid=0))
            service = root["service"]
            enabled = preimage.verified_wan_device is not None
            if (root["schema"] != pin["schema"] or root["generation"] != detail["id"] or
                    service["enabled"] is not enabled or
                    service["target_mode"] not in ("all", "list", "auto") or
                    learning != (enabled and service["target_mode"] == "auto") or
                    (not learning and inspect_inert_release(release, owner_uid=0) != "inactive")):
                raise QuiescentPreimageRefused("BOUND_STAGED_ROOT_MODE_CHANGED")
            _stat(COMMON_ACTIVE.parent, 0, directory=True)
            _stat(backup.parent, 0, directory=True)
            tree = _full_prior_tree(work, COMMON_ACTIVE, 0)
            if _present(stage) or _present(parked):
                raise QuiescentPreimageRefused("BOUND_STAGED_ATOMIC_RESIDUE")
            old_tree = None
            if prior is None:
                # The pristine gate also allows an empty active directory.
                _safe_empty_directory(backup, 0)
            else:
                old_work = WORK / prior["id"]
                if (not _original_plan_matches(parent=WORK, generation=prior["id"],
                                               journal={"detail": prior}, owner_uid=0) or
                        (not retired and
                         inspect_inert_release(old_work / "release", owner_uid=0) != "inactive")):
                    raise QuiescentPreimageRefused("BOUND_STAGED_PREVIOUS_SOURCE_CHANGED")
                old_tree = _full_prior_tree(old_work, backup, 0)
                if old_tree != preimage.previous_release_sha256:
                    raise QuiescentPreimageRefused("BOUND_STAGED_BACKUP_CHANGED")
            idle = None
            if not learning:
                if prior_idle is not None:
                    queue, receipts = _original_epoch_queue()
                    with queue.inherited_exclusive(queue_fd):
                        if retired:
                            _verify_retired_history(record, queue, receipts, preimage.retired_ready_sha256)
                        idle = _verify_idle_producer(queue, receipts)
                        if idle != prior_idle:
                            raise QuiescentPreimageRefused("BOUND_STAGED_IDLE_PRODUCER_CHANGED")
                else:
                    _safe_empty_directory(PRODUCER_ROOT, 0)
            process = pretraffic = None
            if enabled:
                process = _running_native(release, owner_uid=0,
                                          child_pidfile=CHILD_PID, monitor_pidfile=MONITOR_PID)
                desired = shared_release_manifest(release)
                if desired["rule_base"] != 19000 or desired["rule_max"] not in (19010, 19099):
                    raise QuiescentPreimageRefused("BOUND_STAGED_KERNEL_SCOPE_INVALID")
                empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
                # Stopped prior has an empty physical kernel, even when its
                # sealed manifest describes previously enabled Voice rules.
                verify_staged_state(FreeBSDIPFWAdapter(19000, 19099), empty, desired)
                kernel = "native-managed-kernel-staged"
                if learning:
                    def attest():
                        return attest_bound_learning_staged_generation(record, config_fd)

                    proof = attest()
                    if (proof.generation != detail["id"] or proof.operation_id != detail["id"] or
                            proof.owner_candidate_sha256 != detail["candidate"] or
                            (proof.owner.pid, proof.owner.started) != (process.pid, process.started)):
                        raise QuiescentPreimageRefused("BOUND_STAGED_LEARNING_OWNER_CHANGED")
                    _, names = _qualified_learning_sources(proof.learning, PRODUCER_ROOT)
                    queue, receipts = _original_epoch_queue(names)
                    with queue.inherited_exclusive(queue_fd):
                        if retired:
                            _verify_retired_history(
                                record, queue, receipts, preimage.retired_ready_sha256)
                        pretraffic = receipts.verify_learning_running_pretraffic(
                            proof, queue, workspace=work, attest=attest)
                        if prior_idle is not None:
                            _verify_prior_idle_inode_identity(queue, prior_idle)
            else:
                _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
                kernel = _empty_kernel(release)
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise QuiescentPreimageRefused("BOUND_STAGED_OWNER_CHANGED")
            return StagedBoundRuntimeReceipt(detail["id"], pin["root_sha256"], detail["base"],
                                             tree, old_tree, process, kernel,
                                             config_digest, pretraffic,
                                             preimage.retired_ready_sha256, idle)

        first = observe()
        if observe() != first:
            raise QuiescentPreimageRefused("BOUND_STAGED_WITNESS_CHANGED")
        return first
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError,
            subprocess.SubprocessError):
        raise QuiescentPreimageRefused("BOUND_STAGED_PHYSICAL_ATTEST_REFUSED") from None


def _cold_recovery_trees(active: Path, generation: str, old_hash: str,
                         new_hash: str, *, phase: str, restored: bool,
                         owner_uid: int) -> tuple:
    """Read the existing atomic transaction paths before any recovery mutation.

    Both original seals have already qualified. Permit only an exact old
    or new active tree, a complete new stage and at most one exact old
    hold/backup. Never create, rename or remove anything here.
    """
    from shared_apply_seal import _stat, _release_hash

    _stat(active.parent, owner_uid, directory=True)
    name = active.name
    backup_root = active.with_name("runtime-v2-backups")
    if _present(backup_root):
        _stat(backup_root, owner_uid, directory=True)
    stage = active.parent / f".{name}.stage.{generation}"
    parked = active.parent / f".{name}.old.{generation}"
    backup = backup_root / f"{name}-{generation}"

    def read(path, allowed):
        if not _present(path):
            return None
        digest = _release_hash(path, owner_uid)
        if digest not in allowed:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_ARTIFACT_CHANGED")
        return digest

    active_sha = read(active, (old_hash, new_hash))
    stage_sha = read(stage, (new_hash,))
    parked_sha = read(parked, (old_hash,))
    backup_sha = read(backup, (old_hash,))
    if parked_sha is not None and backup_sha is not None:
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_DUPLICATE_PRIOR")
    if restored:
        if active_sha != old_hash:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_OLD_TREE_REQUIRED")
    elif active_sha is None:
        if (phase != "activating" or stage_sha is None or
                (parked_sha is None and backup_sha is None)):
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_RENAME_GAP_INVALID")
    elif active_sha != old_hash:
        if backup_sha is None or stage_sha is not None or parked_sha is not None:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_INSTALLED_TREE_INVALID")
    return active_sha, stage_sha, parked_sha, backup_sha


def _observe_cold_retired_predecessor(record: dict) -> tuple:
    """Read-only cold recovery proof for an already retired learning owner.

    Called before any Config lock is retained. Borrow only the existing
    P2a lock; never create a queue, finalize an epoch or reclaim history.
    The original historical verifier checks the sealed prior generation,
    full terminal ACK chain and every archived source inode and byte.
    """
    from auto_detect_post_drop import _original_epoch_queue

    prior = record["previous"]
    queue, receipts = _original_epoch_queue()
    if queue.root != PRODUCER_ROOT or queue.uid != 0 or receipts.root != EPOCH_ROOT:
        raise QuiescentPreimageRefused("BOUND_COLD_RETIRED_SCOPE_REQUIRED")
    with queue.exclusive(existing_only=True):
        ready = _retired_ready_digest(EPOCH_ROOT, prior["id"], 0)
        _verify_retired_history(record, queue, receipts, ready)
        idle = _verify_idle_producer(queue, receipts)
        if _retired_ready_digest(EPOCH_ROOT, prior["id"], 0) != ready:
            raise QuiescentPreimageRefused("BOUND_COLD_RETIRED_READY_CHANGED")
        return ready, idle


def _cold_rollback_config_image(record: dict, saved: dict) -> tuple:
    """Bind the old saved-model receipt to the sealed successor plan.

    The enclosing original FD9 recovery observes the complete physical
    state twice. Each read uses the same existing PHP Config owner, with
    no retained FD4 and no additional writer. An equal-image ACTIVATED
    is ambiguous: it must not enter automatic pre-save rollback.
    """
    import json
    from neutral_schema3_saved_wan_preimage import _qualify_ordinary_cold_config

    detail = record["detail"]
    raw = _native_call((
        "/usr/local/bin/php", str(SCRIPT / "shared_apply_config.php"),
        "ordinary-cold", detail["id"], detail["page"]))
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_CONFIG_RECEIPT_INVALID")
    image, digest, enabled = _qualify_ordinary_cold_config(json.loads(raw), record)
    if (digest != saved["snapshot"] or enabled != saved["enabled"] or
            image not in ("base-image", "base-equals-candidate") or
            (image == "base-equals-candidate" and record["phase"] != "activating")):
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_CONFIG_OUTCOME_UNCERTAIN")
    return image, digest, enabled


def _cold_locked_producer(record: dict, queue_fd: int | None) -> tuple:
    """Observe the original producer without acquiring P2a after Config."""
    from auto_detect_post_drop import _original_epoch_queue

    retired = record.get("previous_manifest", {}).get("schema") == 2
    if queue_fd is None:
        if retired:
            raise QuiescentPreimageRefused("BOUND_COLD_RETIRED_QUEUE_REQUIRED")
        _safe_empty_directory(PRODUCER_ROOT, 0)
        return None, None
    queue, receipts = _original_epoch_queue()
    if queue.root != PRODUCER_ROOT or queue.uid != 0 or receipts.root != EPOCH_ROOT:
        raise QuiescentPreimageRefused("BOUND_COLD_RETIRED_SCOPE_REQUIRED")
    with queue.inherited_exclusive(queue_fd):
        ready = None
        if retired:
            ready = _retired_ready_digest(EPOCH_ROOT, record["previous"]["id"], 0)
            _verify_retired_history(record, queue, receipts, ready)
        idle = _verify_idle_producer(queue, receipts)
        if retired and _retired_ready_digest(EPOCH_ROOT, record["previous"]["id"], 0) != ready:
            raise QuiescentPreimageRefused("BOUND_COLD_RETIRED_READY_CHANGED")
        return (ready, idle) if retired else None, idle


def attest_inert_bound_cold_recovery(record: dict, *, restored: bool,
                                     config_fd: int | None = None,
                                     config_digest: str | None = None,
                                     queue_fd: int | None = None) -> None:
    """Qualify only the existing original ordinary cold rollback route.

    Before the shell's existing parked/pristine/installed recovery, require
    exact pinned work, saved predecessor Config and no live process.
    An inert candidate may follow a pinned, fully retired learning owner
    only with the original archived ACK and empty producer proof. The
    original shell alone restores native staged IPFW and rename artifacts.
    Before terminal WAL restore require the whole old tree and empty
    kernel. Bind the old saved model to the candidate's original plan;
    an ambiguous equal-image ACTIVATED remains fenced. Learning
    candidates and Found remain outside this route.
    """
    from neutral_root_stage import (
        verify_original_operation_pins, _original_plan_matches)
    from shared_apply_seal import verify_seal
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    import json
    import sys

    require_lifecycle_lock()
    locked = config_fd is not None
    if ((locked and (not sys.platform.startswith("freebsd") or
                     os.geteuid() != 0 or type(config_fd) is not int or
                     config_fd < 3 or config_fd == 9 or
                     (queue_fd is not None and (type(queue_fd) is not int or
                      queue_fd < 3 or queue_fd in (9, config_fd))))) or
            (not locked and (config_digest is not None or queue_fd is not None))):
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_LOCK_SCOPE_INVALID")
    store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
    if (type(restored) is not bool or type(record) is not dict or
            store.read() != record or record.get("phase") not in (
                "activating", "activated") or "found" in record or
            record.get("manifest", {}).get("schema") != 1 or
            ("previous_manifest" in record and
             record["previous_manifest"]["schema"] not in (1, 2)) or
            type(record.get("previous")) is not dict or
            record["previous"]["candidate"] != record["detail"]["base"]):
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_OWNER_REQUIRED")

    def check_config_lock():
        if locked:
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            detail = record["detail"]
            if (config_digest != detail["base"] or
                    (detail["base"] == detail["candidate"] and record["phase"] != "activating")):
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_CONFIG_OUTCOME_UNCERTAIN")

    check_config_lock()

    def observe():
        require_lifecycle_lock()
        check_config_lock()
        if store.read() != record:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_JOURNAL_CHANGED")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        old, new = record["previous"], record["detail"]
        old_work, new_work = WORK / old["id"], WORK / new["id"]
        seals = []
        retired = record.get("previous_manifest", {}).get("schema") == 2
        for detail, work in ((old, old_work), (new, new_work)):
            seals.append(verify_seal(work, owner=0))
            if not _original_plan_matches(
                    parent=WORK, generation=detail["id"],
                    journal={"detail": detail}, owner_uid=0):
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_SOURCE_CHANGED")
            if detail == old and retired:
                # The full historical verifier below qualifies the exact
                # schema3 map/epoch against this already pinned release.
                continue
            if inspect_inert_release(work / "release", owner_uid=0) != "inactive":
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_SOURCE_CHANGED")
        saved_raw = saved = None
        if not locked:
            saved_raw = _native_call((
                "/usr/local/bin/php", str(SCRIPT / "shared_apply_config.php"),
                "saved", old["id"], old["page"]))
            saved = json.loads(saved_raw)
            if (type(saved) is not dict or set(saved) != {"result", "snapshot", "enabled"} or
                    saved["result"] != "committed" or saved["snapshot"] != old["candidate"] or
                    saved["enabled"] not in ("0", "1")):
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_CONFIG_CHANGED")
        _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
        if locked:
            retired_receipt, idle = _cold_locked_producer(record, queue_fd)
        else:
            retired_receipt = _observe_cold_retired_predecessor(record) if retired else None
            idle = (retired_receipt[1] if retired else
                    _observe_idle_producer(PRODUCER_ROOT, 0))
        # Refuse damaged/foreign stage, hold, backup and active trees before
        # the existing shell may mutate IPFW or rename anything. Repeat the
        # same read at terminal completion, not a separate recovery ledger.
        trees = _cold_recovery_trees(
            COMMON_ACTIVE, new["id"], seals[0]["sha256"]["release"],
            seals[1]["sha256"]["release"], phase=record["phase"],
            restored=restored, owner_uid=0)
        kernel = active_hash = None
        if restored:
            active_hash = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
            if active_hash != trees[0]:
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_ACTIVE_TREE_CHANGED")
            kernel = _empty_kernel(old_work / "release")
        config_image = (config_digest if locked else _cold_rollback_config_image(record, saved))
        check_config_lock()
        _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
        if store.read() != record:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_JOURNAL_CHANGED")
        return seals, saved_raw, active_hash, kernel, idle, trees, retired_receipt, config_image

    if observe() != observe():
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_PREIMAGE_CHANGED")


def _run_bound_restore_joined(command, *, budget: float, capture_output: bool = False,
                              pass_fds: tuple[int, ...], input_data: bytes | None = None) -> subprocess.CompletedProcess:
    """Deadline refuses success but cannot kill a physical shell/PHP parent.

    Both commands are synchronous, with no detached descendants. Wait for
    their completion even after timeout or interrupted receipt; never use
    subprocess.run(timeout=...), which kills only the direct child. This
    protects the original parent-owned P2a/Config lock on managed failures.
    """
    import time

    started = time.monotonic()
    output = subprocess.PIPE if capture_output else subprocess.DEVNULL
    with subprocess.Popen(command, stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL, stdout=output,
                          stderr=output, pass_fds=pass_fds, close_fds=True) as child:
        try:
            stdout, stderr = child.communicate(input=input_data, timeout=budget)
        except BaseException:
            # communicate(timeout) does NOT kill the child. Do not close
            # descriptors or unwind the original lock before joining it.
            child.communicate()
            raise
        if time.monotonic() - started >= budget:
            raise subprocess.TimeoutExpired(command, budget)
        return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)


def _reject_cold_recovery_residue(active: Path) -> None:
    """A PID-scoped interrupted recovery is not an original operation-ID gap."""
    import re

    name = re.escape(active.name)
    if any(re.fullmatch(r"\." + name + r"\.(?:stage|old)\.[0-9]{1,10}|" +
                        name + r"\.rollback-old\.[0-9]+", item.name)
           for item in active.parent.iterdir()):
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_RESIDUE")


def _restore_bound_parked_cold_locked(record: dict, *, config_fd: int,
                                      config_digest: str, queue_fd: int | None) -> bool:
    """Original ACTIVATING rename gap, with retained exact old and new trees.

    Only a missing active tree, complete new stage, exactly one old
    hold/backup and an empty physical kernel qualify. Copy the old sealed
    release using the existing atomic installer; consume neither artifact.
    """
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from shared_apply_seal import verify_seal

    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    if _present(COMMON_ACTIVE):
        return False
    if record["phase"] != "activating":
        raise QuiescentPreimageRefused("BOUND_COLD_PARKED_PHASE_INVALID")
    old, new = record["previous"], record["detail"]
    old_work, new_work = WORK / old["id"], WORK / new["id"]
    old_hash = verify_seal(old_work, owner=0)["sha256"]["release"]
    new_hash = verify_seal(new_work, owner=0)["sha256"]["release"]

    def exact():
        attest_inert_bound_cold_recovery(
            record, restored=False, config_fd=config_fd,
            config_digest=config_digest, queue_fd=queue_fd)
        _reject_cold_recovery_residue(COMMON_ACTIVE)
        trees = _cold_recovery_trees(
            COMMON_ACTIVE, new["id"], old_hash, new_hash, phase="activating",
            restored=False, owner_uid=0)
        if trees not in ((None, new_hash, old_hash, None),
                         (None, new_hash, None, old_hash)):
            raise QuiescentPreimageRefused("BOUND_COLD_PARKED_ARTIFACTS_INVALID")
        kernel = _empty_kernel(old_work / "release")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return trees, kernel

    before = exact()
    if exact() != before:
        raise QuiescentPreimageRefused("BOUND_COLD_PARKED_PREIMAGE_CHANGED")
    inherited = (9, config_fd) if queue_fd is None else (9, config_fd, queue_fd)
    try:
        result = _run_bound_restore_joined(
            ("/bin/sh", "-c", '. "$1"; . "$2"; atomic_install_tree "$3" "$4" "$5"',
             "zapret-bound-parked", str(SCRIPT / "backend/common.sh"),
             str(SCRIPT / "backend/atomic.sh"), str(old_work / "release"),
             str(COMMON_ACTIVE), str(COMMON_ACTIVE.with_name("runtime-v2-backups"))),
            pass_fds=inherited, budget=20)
    except (OSError, subprocess.SubprocessError):
        raise QuiescentPreimageRefused("BOUND_COLD_PARKED_RESTORE_OUTCOME_UNCERTAIN") from None
    if result.returncode != 0:
        raise QuiescentPreimageRefused("BOUND_COLD_PARKED_RESTORE_FAILED")
    attest_inert_bound_cold_recovery(
        record, restored=True, config_fd=config_fd,
        config_digest=config_digest, queue_fd=queue_fd)
    _reject_cold_recovery_residue(COMMON_ACTIVE)
    after = _cold_recovery_trees(
        COMMON_ACTIVE, new["id"], old_hash, new_hash, phase="activating",
        restored=True, owner_uid=0)
    if after != (old_hash, *before[0][1:]):
        raise QuiescentPreimageRefused("BOUND_COLD_PARKED_EVIDENCE_CHANGED")
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return True


def _restore_bound_installed_cold_locked(record: dict, *, config_fd: int,
                                         config_digest: str, queue_fd: int | None) -> bool:
    """Restore an exact installed inert candidate over a cold predecessor.

    Only an empty kernel or the exact staged candidate from EMPTY qualifies.
    A stopped prior's sealed rule manifest is not its physical kernel image.
    Reuse the original IPFW rollback and atomic installer; retain backups.
    Unknown/running-prior staged images and rename gaps remain fenced here.
    """
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from neutral_root_stage import _verify_original_pinned_root
    from shared_apply_seal import verify_seal, _release_hash
    from voice_firewall_transaction import verify_staged_state, rollback_uncommitted
    import json

    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    if not _present(COMMON_ACTIVE):
        return False
    old, new = record["previous"], record["detail"]
    old_work, new_work = WORK / old["id"], WORK / new["id"]
    old_hash = verify_seal(old_work, owner=0)["sha256"]["release"]
    new_hash = verify_seal(new_work, owner=0)["sha256"]["release"]
    active_hash = _release_hash(COMMON_ACTIVE, 0)
    if active_hash == old_hash:
        return False
    if active_hash != new_hash:
        raise QuiescentPreimageRefused("BOUND_COLD_INSTALLED_TREE_CHANGED")

    def exact():
        attest_inert_bound_cold_recovery(
            record, restored=False, config_fd=config_fd,
            config_digest=config_digest, queue_fd=queue_fd)
        if _cold_recovery_trees(
                COMMON_ACTIVE, new["id"], old_hash, new_hash, phase=record["phase"],
                restored=False, owner_uid=0) != (new_hash, None, None, old_hash):
            raise QuiescentPreimageRefused("BOUND_COLD_INSTALLED_BACKUP_REQUIRED")
        # Do not retry across an unexplained PID-named recovery rename gap.
        _reject_cold_recovery_residue(COMMON_ACTIVE)

    exact()
    release = new_work / "release"
    root = json.loads(_verify_original_pinned_root(
        detail=new, binding=record["manifest"], parent=WORK, owner_uid=0))
    desired = shared_release_manifest(release)
    if desired["rule_base"] != 19000 or desired["rule_max"] not in (19010, 19099):
        raise QuiescentPreimageRefused("BOUND_COLD_INSTALLED_KERNEL_SCOPE_INVALID")
    empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
    if not _ipfw_kernel_confirmed_absent():
        reader = FreeBSDIPFWAdapter(19000, 19099)
        try:
            verify_prior_state(reader, empty, desired)
        except VoiceFirewallError:
            if root["service"]["enabled"] is not True:
                raise QuiescentPreimageRefused("BOUND_COLD_DISABLED_STAGED_KERNEL")
            verify_staged_state(reader, empty, desired)
            exact()
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            # The original rollback rechecks exact staged rules/tables
            # itself before its first mutation, then verifies EMPTY.
            rollback_uncommitted(
                FreeBSDIPFWAdapter(19000, 19099, allow_mutations=True), empty, desired)
    _empty_kernel(release)
    exact()
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    inherited = (9, config_fd) if queue_fd is None else (9, config_fd, queue_fd)
    try:
        result = _run_bound_restore_joined(
            ("/bin/sh", "-c", '. "$1"; . "$2"; atomic_install_tree "$3" "$4" "$5"',
             "zapret-bound-installed", str(SCRIPT / "backend/common.sh"),
             str(SCRIPT / "backend/atomic.sh"), str(old_work / "release"),
             str(COMMON_ACTIVE), str(COMMON_ACTIVE.with_name("runtime-v2-backups"))),
            pass_fds=inherited, budget=20)
    except (OSError, subprocess.SubprocessError):
        raise QuiescentPreimageRefused("BOUND_COLD_INSTALLED_RESTORE_OUTCOME_UNCERTAIN") from None
    if result.returncode != 0:
        raise QuiescentPreimageRefused("BOUND_COLD_INSTALLED_RESTORE_FAILED")
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return True


def _remove_bound_pristine_stage_locked(record: dict, *, config_fd: int,
                                       queue_fd: int | None) -> bool:
    """Remove only the exact uninstalled stage, under original FD9/FD4.

    Caller already proved the fully restored old tree and empty kernel
    twice. Parked/backup recovery artifacts are deliberately preserved.
    Reuse the original atomic shell helper, never a new tree installer.
    """
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from shared_apply_seal import verify_seal

    if record["phase"] != "activating":
        return False
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    generation = record["detail"]["id"]
    name = COMMON_ACTIVE.name
    stage = COMMON_ACTIVE.parent / f".{name}.stage.{generation}"
    parked = COMMON_ACTIVE.parent / f".{name}.old.{generation}"
    backup = COMMON_ACTIVE.with_name("runtime-v2-backups") / f"{name}-{generation}"
    if not _present(stage) or _present(parked) or _present(backup):
        return False
    old_work = WORK / record["previous"]["id"]
    new_work = WORK / generation
    old_hash = verify_seal(old_work, owner=0)["sha256"]["release"]
    new_hash = verify_seal(new_work, owner=0)["sha256"]["release"]
    trees = _cold_recovery_trees(COMMON_ACTIVE, generation, old_hash, new_hash,
                                 phase="activating", restored=True, owner_uid=0)
    if trees != (old_hash, new_hash, None, None):
        raise QuiescentPreimageRefused("BOUND_COLD_PRISTINE_STAGE_CHANGED")
    if SharedApplyOperation(DEFAULT_ROOT, owner=0).read() != record:
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_JOURNAL_CHANGED")
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    inherited = (9, config_fd) if queue_fd is None else (9, config_fd, queue_fd)
    try:
        result = _run_bound_restore_joined(
            ("/bin/sh", "-c", '. "$1"; atomic_remove_tree "$2"',
             "zapret-bound-pristine", str(SCRIPT / "backend/atomic.sh"), str(stage)),
            pass_fds=inherited, budget=20)
    except (OSError, subprocess.SubprocessError):
        raise QuiescentPreimageRefused("BOUND_COLD_PRISTINE_STAGE_OUTCOME_UNCERTAIN") from None
    if result.returncode != 0 or _present(stage):
        raise QuiescentPreimageRefused("BOUND_COLD_PRISTINE_STAGE_REMOVE_FAILED")
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return True


def _finish_managed_recovery_locked(store, record: dict, *, config_fd: int,
                                    queue_fd: int | None, saved_image: str | None = None) -> dict:
    """Reconcile one managed file with the original Config and producer locked."""
    from auto_detect_destination_commit import (
        exclusive_destination_lock, _restore_bound_managed_file_locked,
        _attest_bound_managed_installed_locked,
    )
    from auto_detect_gui_hostlist import AUTO_LOCK
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from neutral_shared_apply_source_gate import _native_managed_running_digest
    from shared_apply_seal import _stat

    previous = WORK / record["previous"]["id"] / "release"
    candidate = WORK / record["detail"]["id"] / "release"
    active = COMMON_ACTIVE
    prefix = active.name
    backup = active.with_name("runtime-v2-backups") / f"{prefix}-{record['detail']['id']}"
    pidfiles = (CHILD_PID, MONITOR_PID, DAEMON_PID)
    # A pre-save interruption can leave the exact original engine running.
    # Select the physical witness from the process state, not the Config phase.
    running = any(_present(path) for path in pidfiles)
    expected_running = record["managed"].get("running_sha256")
    if running and expected_running is None:
        raise QuiescentPreimageRefused("MANAGED_RECOVERY_RUNNING_OWNER_REQUIRED")

    def observe():
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        _stat(active.parent, 0, directory=True)
        if _present(backup.parent):
            _stat(backup.parent, 0, directory=True)
        # A managed CAS owns no directory staging or atomic tree backups.
        if (_present(backup) or any(item.name.startswith((
                f".{prefix}.stage.", f".{prefix}.old.", f"{prefix}.rollback-old."))
                for item in active.parent.iterdir())):
            raise QuiescentPreimageRefused("MANAGED_COLD_TREE_TRANSACTION_PRESENT")
        if any(inspect_inert_release(path, owner_uid=0) != "inactive"
               for path in (previous, candidate)):
            raise QuiescentPreimageRefused("MANAGED_COLD_INERT_OWNER_REQUIRED")
        producer = _cold_locked_producer(record, queue_fd)
        if running:
            runtime = _native_managed_running_digest(previous, config_fd)
            if runtime != expected_running:
                raise QuiescentPreimageRefused("MANAGED_RECOVERY_RUNNING_OWNER_CHANGED")
        else:
            _zero_processes(pidfiles)
            runtime = _empty_kernel(previous)
            _zero_processes(pidfiles)
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return runtime, producer

    first = observe()

    def attest():
        return observe() == first

    with exclusive_destination_lock(AUTO_LOCK, 0):
        if saved_image is not None:
            # Persist the observed XML while its original lock is still held.
            os.fsync(config_fd)
        if saved_image == record["detail"]["candidate"]:
            def installed():
                _attest_bound_managed_installed_locked(store, record, parent=WORK, active=active)
                return attest()

            return store._checkpoint_managed_config(record, saved=True, attest=installed,
                                                    shared_work_parent=WORK)
        return _restore_bound_managed_file_locked(store, record, parent=WORK,
            active=active, attest=attest, saved_base=saved_image)


def finish_bound_cold_restore_locked(operation: str, config_digest: str, *,
                                     config_fd: int, queue_fd: int | None = None) -> dict:
    """Original PHP owns the native Config lock through the restored fsync."""
    import sys
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from shared_apply_operation import DIGEST, OP_ID

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not OP_ID.fullmatch(operation) or
            type(config_digest) is not str or not DIGEST.fullmatch(config_digest) or
            type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
            (queue_fd is not None and (type(queue_fd) is not int or queue_fd < 3 or
                                       queue_fd in (9, config_fd)))):
        raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_NATIVE_SCOPE_REQUIRED")
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
    record = store.read()
    if (type(record) is not dict or record["detail"]["id"] != operation or
            record["phase"] not in ("activating", "activated", MANAGED_WRITING) or
            "found" in record or record.get("manifest", {}).get("schema") != 1 or
            record.get("previous", {}).get("candidate") != config_digest or
            record["detail"]["base"] != config_digest):
        raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_ORIGINAL_OWNER_REQUIRED")

    def exact():
        _reject_cold_recovery_residue(COMMON_ACTIVE)
        if not _restore_bound_parked_cold_locked(
                record, config_fd=config_fd, config_digest=config_digest, queue_fd=queue_fd):
            _restore_bound_installed_cold_locked(
                record, config_fd=config_fd, config_digest=config_digest, queue_fd=queue_fd)
        attest_inert_bound_cold_recovery(
            record, restored=True, config_fd=config_fd,
            config_digest=config_digest, queue_fd=queue_fd)
        if _remove_bound_pristine_stage_locked(record, config_fd=config_fd, queue_fd=queue_fd):
            # The exact stage removal is the only physical mutation here.
            # Prove the old tree, Config, producer and kernel again before WAL.
            attest_inert_bound_cold_recovery(
                record, restored=True, config_fd=config_fd,
                config_digest=config_digest, queue_fd=queue_fd)
        _reject_cold_recovery_residue(COMMON_ACTIVE)
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return True

    expected = {**record, "phase": "restored"}
    if record["phase"] == MANAGED_WRITING:
        expected.pop("managed")
        result = _finish_managed_recovery_locked(store, record, config_fd=config_fd,
                                                queue_fd=queue_fd)
    else:
        result = store._advance_bound_ordinary("restored", record, exact)
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    if result != expected or store.read() != result:
        raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_READBACK_REQUIRED")
    return {"result": "original-bound-cold-restored", "id": operation}


def finish_managed_config_recovery_locked(operation: str, witness_sha256: str, *,
                                           config_fd: int, queue_fd: int | None = None) -> dict:
    """Recover only from the exact persisted Model observed by the FD4 owner."""
    import sys
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from shared_apply_operation import DIGEST, OP_ID, _config_observation_witness
    from shared_apply_seal import verify_seal

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not OP_ID.fullmatch(operation) or
            type(witness_sha256) is not str or not DIGEST.fullmatch(witness_sha256) or
            type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
            (queue_fd is not None and (type(queue_fd) is not int or queue_fd < 3 or
                                       queue_fd in (9, config_fd)))):
        raise QuiescentPreimageRefused("MANAGED_CONFIG_RECOVERY_NATIVE_SCOPE_REQUIRED")
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
    record = store.read()
    if (record is None or record["phase"] != MANAGED_CONFIG_SAVING or
            record["detail"]["id"] != operation):
        raise QuiescentPreimageRefused("MANAGED_CONFIG_RECOVERY_OWNER_REQUIRED")
    detail = record["detail"]
    base, candidate = detail["base"], detail["candidate"]
    if base == candidate:
        raise QuiescentPreimageRefused("MANAGED_CONFIG_RECOVERY_AMBIGUOUS_IMAGE")
    plan_sha = verify_seal(WORK / operation, owner=0)["sha256"]["plan.json"]
    images = {_config_observation_witness(detail, plan_sha, image): image
              for image in (base, candidate)}
    image = images.get(witness_sha256)
    if image is None or (image == candidate and "restore" in record["managed"]):
        raise QuiescentPreimageRefused("MANAGED_CONFIG_RECOVERY_IMAGE_REFUSED")

    phase = "committed" if image == candidate else "restored"
    result = _finish_managed_recovery_locked(store, record, config_fd=config_fd,
                                            queue_fd=queue_fd, saved_image=image)
    expected = {**record, "phase": phase}
    expected.pop("managed")
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    if result != expected or store.read() != result:
        raise QuiescentPreimageRefused("MANAGED_CONFIG_RECOVERY_READBACK_REQUIRED")
    return {"result": "original-managed-config-" + phase, "id": operation}


def native_finish_bound_cold_restore(record: dict) -> dict:
    """Existing FD9 caller -> original P2a if present -> PHP Config -> WAL."""
    import json
    import sys
    from auto_detect_post_drop import _original_epoch_queue

    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_NATIVE_SCOPE_REQUIRED")
    require_lifecycle_lock()
    store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
    if (type(record) is not dict or store.read() != record or
            record.get("phase") not in ("activating", "activated", MANAGED_WRITING, MANAGED_CONFIG_SAVING) or
            "found" in record or record.get("manifest", {}).get("schema") != 1 or
            record.get("previous", {}).get("candidate") != record["detail"]["base"]):
        raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_ORIGINAL_OWNER_REQUIRED")
    detail = record["detail"]
    recover_save = record["phase"] == MANAGED_CONFIG_SAVING
    action = "managed-save-recover" if recover_save else "ordinary-restore-finish"
    command = ["/usr/local/bin/php", str(SCRIPT / "shared_apply_config.php"),
               action, detail["id"], detail["page"]]

    def invoke(fd=None):
        require_lifecycle_lock()
        if store.read() != record:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_JOURNAL_CHANGED")
        args = command if fd is None else command + ["--queue-fd=" + str(fd)]
        try:
            reply = _run_bound_restore_joined(args, capture_output=True,
                                                pass_fds=(9,) if fd is None else (fd, 9),
                                                budget=90)
        except subprocess.SubprocessError:
            # Child may already have fsynced restored. Do not retry or
            # guess a terminal outcome from missing transport evidence.
            raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_NATIVE_OUTCOME_UNCERTAIN") from None
        if (reply.returncode != 0 or type(reply.stdout) is not bytes or
                len(reply.stdout) > 4096 or reply.stdout.count(b"\n") != 1 or
                not reply.stdout.endswith(b"\n")):
            raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_NATIVE_RECEIPT_REQUIRED")
        receipt = json.loads(reply.stdout)
        phase = "restored"
        if recover_save and receipt == {"result": "original-managed-config-committed", "id": detail["id"]}:
            phase = "committed"
        else:
            restored = "original-managed-config-restored" if recover_save else "original-bound-cold-restored"
            if receipt != {"result": restored, "id": detail["id"]}:
                raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_NATIVE_RECEIPT_REQUIRED")
        result = store.read()
        expected = {**record, "phase": phase}
        expected.pop("managed", None)
        if result != expected:
            raise QuiescentPreimageRefused("BOUND_COLD_RESTORE_READBACK_REQUIRED")
        return result

    retired = record.get("previous_manifest", {}).get("schema") == 2
    if _present(PRODUCER_ROOT):
        info = PRODUCER_ROOT.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022):
            raise QuiescentPreimageRefused("BOUND_IDLE_PRODUCER_UNTRUSTED")
    if retired or (_present(PRODUCER_ROOT) and any(PRODUCER_ROOT.iterdir())):
        queue, receipts = _original_epoch_queue()
        if queue.root != PRODUCER_ROOT or queue.uid != 0 or receipts.root != EPOCH_ROOT:
            raise QuiescentPreimageRefused("BOUND_COLD_RETIRED_SCOPE_REQUIRED")
        with queue.exclusive(existing_only=True):
            return invoke(queue.locked_fd)
    _safe_empty_directory(PRODUCER_ROOT, 0)
    return invoke()


def attest_quiescent_under_fd9(*, generation: str, native: NativeParity,
                              effective: EffectiveSnapshot, enabled: bool
                              ) -> QuiescentPreimage:
    """Only original root FD9, fixed installed paths; never a transition API."""
    try:
        require_lifecycle_lock()
    except (RuntimeError, OSError, ValueError):
        raise QuiescentPreimageRefused("QUIESCENT_ORIGINAL_FD9_REQUIRED") from None
    return _attest_quiescent(generation=generation, native=native,
        effective=effective, enabled=enabled, parent=WORK,
        journal_root=DEFAULT_ROOT, owner_uid=0, active=COMMON_ACTIVE,
        backups=COMMON_ACTIVE.with_name("runtime-v2-backups"),
        producer=PRODUCER_ROOT, epochs=EPOCH_ROOT,
        pidfiles=(CHILD_PID, MONITOR_PID, DAEMON_PID))
