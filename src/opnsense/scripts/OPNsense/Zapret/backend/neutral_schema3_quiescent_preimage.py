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
from shared_apply_operation import SharedApplyOperation, SharedOperationError, DEFAULT_ROOT
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
                    _retired_ready(producer, owner_uid)
                    retirement = "original-epoch-ack-retired"
                else:
                    # Original inert classifier rejects native auto flags
                    # without the matching map. Do not infer an empty queue
                    # from List mode: require no unexplained producer bytes.
                    if inspect_inert_release(active, owner_uid=owner_uid) != "inactive":
                        raise QuiescentPreimageRefused("QUIESCENT_INERT_OWNER_INVALID")
                    _safe_empty_directory(producer, owner_uid)
                    retirement = "inert-no-producer-data"
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
                config[0], config[1], wan, old_state, kernel, retirement)
        first = observe()
        if (observe() != first or
                _attest_bound_candidate(**args, mode=native.mode, schema3=schema3).root_sha256 !=
                first.root_sha256 or store.read() != before):
            raise QuiescentPreimageRefused("QUIESCENT_PREIMAGE_RACED")
        return first
    except (QuiescentPreimageRefused, SavedWanPreimageRefused,
            BoundRootRefused, PreviousPhysicalRefused, SharedOperationError,
            SharedBundleError, VoiceFirewallError, GenerationRefused,
            MinuteRefused, OSError, TypeError, KeyError, ValueError,
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


def attest_bound_quiescent_staged_under_fd9(record: dict, *, preimage: QuiescentPreimage,
                                            config_fd: int, config_digest: str,
                                            queue_fd: int | None = None,
                                            saved: bool = False) -> StagedBoundRuntimeReceipt:
    """Reversible ordinary cutover before Config::save, not cold recovery.

    Use the original in-flight quiescent preimage, not a reconstruction
    of the old state after installation. Inert and learning candidates
    from an empty or stopped inert predecessor qualify here. Learning
    borrows the original queue acquired BEFORE Config, not a second flock.
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
                record.get("previous_manifest", {}).get("schema", 1) != 1 or
                (saved and record["phase"] != "activated")):
            raise QuiescentPreimageRefused("BOUND_STAGED_ORDINARY_REQUIRED")
        detail, pin = record["detail"], record["manifest"]
        learning = pin["schema"] == 2
        if ((learning and (type(queue_fd) is not int or queue_fd < 3 or
                          queue_fd in (9, config_fd))) or
                (not learning and queue_fd is not None)):
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
                                    preimage.previous_release_sha256 is not None)) or
                (prior is not None and (preimage.old_state != "committed-stopped" or
                                        preimage.retirement_state != "inert-no-producer-data" or
                                        prior["candidate"] != detail["base"]))):
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
                        inspect_inert_release(old_work / "release", owner_uid=0) != "inactive"):
                    raise QuiescentPreimageRefused("BOUND_STAGED_PREVIOUS_SOURCE_CHANGED")
                old_tree = _full_prior_tree(old_work, backup, 0)
                if old_tree != preimage.previous_release_sha256:
                    raise QuiescentPreimageRefused("BOUND_STAGED_BACKUP_CHANGED")
            if not learning:
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
                        pretraffic = receipts.verify_learning_running_pretraffic(
                            proof, queue, workspace=work, attest=attest)
            else:
                _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
                kernel = _empty_kernel(release)
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise QuiescentPreimageRefused("BOUND_STAGED_OWNER_CHANGED")
            return StagedBoundRuntimeReceipt(detail["id"], pin["root_sha256"], detail["base"],
                                             tree, old_tree, process, kernel,
                                             config_digest, pretraffic)

        first = observe()
        if observe() != first:
            raise QuiescentPreimageRefused("BOUND_STAGED_WITNESS_CHANGED")
        return first
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError,
            subprocess.SubprocessError):
        raise QuiescentPreimageRefused("BOUND_STAGED_PHYSICAL_ATTEST_REFUSED") from None


def attest_inert_bound_cold_recovery(record: dict, *, restored: bool) -> None:
    """Qualify only the existing original ordinary cold rollback route.

    Before the shell's existing parked/pristine/installed recovery, require
    exact pinned work, saved predecessor Config and no live process or
    producer. The original shell alone verifies and restores the native
    staged IPFW and rename artifacts. Before terminal WAL restore, require
    the whole restored old tree and empty managed kernel. Never infer an
    Auto epoch or a Found rollback from inert bytes.
    """
    from neutral_root_stage import (
        verify_original_operation_pins, _original_plan_matches)
    from shared_apply_seal import verify_seal, _release_hash

    require_lifecycle_lock()
    store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
    if (type(restored) is not bool or type(record) is not dict or
            store.read() != record or record.get("phase") not in (
                "activating", "activated") or "found" in record or
            record.get("manifest", {}).get("schema") != 1 or
            ("previous_manifest" in record and
             record["previous_manifest"]["schema"] != 1) or
            type(record.get("previous")) is not dict or
            record["previous"]["candidate"] != record["detail"]["base"]):
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_OWNER_REQUIRED")

    def observe():
        require_lifecycle_lock()
        if store.read() != record:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_JOURNAL_CHANGED")
        verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
        old, new = record["previous"], record["detail"]
        old_work, new_work = WORK / old["id"], WORK / new["id"]
        seals = []
        for detail, work in ((old, old_work), (new, new_work)):
            seals.append(verify_seal(work, owner=0))
            if (not _original_plan_matches(
                    parent=WORK, generation=detail["id"],
                    journal={"detail": detail}, owner_uid=0) or
                    inspect_inert_release(work / "release", owner_uid=0) != "inactive"):
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_SOURCE_CHANGED")
        saved_raw = _native_call((
            "/usr/local/bin/php", str(SCRIPT / "shared_apply_config.php"),
            "saved", old["id"], old["page"]))
        saved = json.loads(saved_raw)
        if (type(saved) is not dict or set(saved) != {"result", "snapshot", "enabled"} or
                saved["result"] != "committed" or saved["snapshot"] != old["candidate"] or
                saved["enabled"] not in ("0", "1")):
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_CONFIG_CHANGED")
        _safe_empty_directory(PRODUCER_ROOT, 0)
        _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
        kernel = active_hash = None
        if restored:
            active_hash = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
            kernel = _empty_kernel(old_work / "release")
            # The original parked recovery intentionally preserves exact
            # transaction artifacts. Unknown/partial residue cannot be
            # blessed by the terminal journal writer.
            name = COMMON_ACTIVE.name
            stage = COMMON_ACTIVE.parent / f".{name}.stage.{new['id']}"
            parked = COMMON_ACTIVE.parent / f".{name}.old.{new['id']}"
            backup = COMMON_ACTIVE.with_name("runtime-v2-backups") / f"{name}-{new['id']}"
            if _present(parked) and _present(backup):
                raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_DUPLICATE_PRIOR")
            for artifact, expected in (
                    (stage, seals[1]["sha256"]["release"]),
                    (parked, seals[0]["sha256"]["release"]),
                    (backup, seals[0]["sha256"]["release"])):
                if _present(artifact) and _release_hash(artifact, 0) != expected:
                    raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_ARTIFACT_CHANGED")
        _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
        if store.read() != record:
            raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_JOURNAL_CHANGED")
        return seals, saved_raw, active_hash, kernel

    if observe() != observe():
        raise QuiescentPreimageRefused("BOUND_COLD_RECOVERY_PREIMAGE_CHANGED")


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
