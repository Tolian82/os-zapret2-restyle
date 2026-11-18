#!/usr/bin/env python3
"""#1052 P3: compose effective known HOSTLISTs from manual and owned sources.

The real managed-target builder is the only product caller. A complete
sealed auto-owned snapshot is read under the existing destination flock.
Missing storage does not create any file or change the original manual build.
No native observer, writer, Config mutation, hot reload, or ACK is enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

from auto_detect_destination_commit import (
    DestinationRefused, SHARED_FOUND_NAMES, _qualified_shared_found_batch,
    _shared_found_assert_missing, _target, _replace,
    exclusive_destination_lock,
)
from auto_detect_gui_hostlist import AUTO_LOCK, AUTO_HOSTLIST
from auto_detect_owned_sources import (KNOWN_HOSTLISTS, OWNED_ROOT, read_owned,
                                       OwnedSourcesRefused)
from domain_policy import (normalize, _list_entries, _covers, DomainPolicyError,
                           AutoDomainPolicyError, MAX_INPUT_BYTES)


class EffectiveKnownRefused(RuntimeError):
    """Reject partial provenance or unsafe output rather than lose manual rows."""


def compose_known(manual: dict[str, str], owned: dict[str, str]) -> dict[str, str]:
    """Preserve manual modifiers and order; append only uncovered plain rows."""
    if (not isinstance(manual, dict) or not isinstance(owned, dict) or
            set(manual) != set(KNOWN_HOSTLISTS) or
            set(owned) != set(KNOWN_HOSTLISTS) or
            any(type(v) is not str for v in (*manual.values(), *owned.values()))):
        raise EffectiveKnownRefused('incomplete_known_hostlist_components')
    entries = {}
    negatives = []
    for name in KNOWN_HOSTLISTS:
        original = manual[name]
        normal = normalize(original, name)['normalized']
        canonical = normal + ('\n' if normal else '')
        if original != canonical:
            raise EffectiveKnownRefused('noncanonical_managed_hostlist')
        entries[name] = _list_entries(original, name)
        negatives.extend(row for row in entries[name] if row[1])
    result = {}
    for name in KNOWN_HOSTLISTS:
        manual_hosts = {row[0] for row in entries[name]}
        lines = manual[name].splitlines()
        for row in _list_entries(owned[name], name):
            host, excluded, exact = row
            if excluded or exact:
                raise EffectiveKnownRefused('noncanonical_automatic_hostlist')
            if host in manual_hosts or any(_covers(host, neg) for neg in negatives):
                continue
            if host not in lines:
                lines.append(host)
        effective = '\n'.join(lines) + ('\n' if lines else '')
        if len(effective.encode('utf-8')) > MAX_INPUT_BYTES:
            raise EffectiveKnownRefused('effective_hostlist_too_large')
        result[name] = effective
    return result


def compose_stage(youtube: Path, user: Path, *,
                  root: Path = OWNED_ROOT, lock: Path = AUTO_LOCK,
                  owner_uid: int = 0) -> dict:
    """Edit only detached staging outputs, never Config or private sources.

    A failed second replace rejects the entire detached release; it is not
    published by the original builder on any nonzero result.
    """
    paths = {'youtube': Path(youtube), 'user': Path(user)}
    if any(not path.is_absolute() for path in paths.values()) or len(set(paths.values())) != 2:
        raise EffectiveKnownRefused('unsafe_staging_paths')
    root = Path(root)
    if not root.exists() and not root.is_symlink():
        if read_owned(root, owner_uid=owner_uid) is not None:
            raise EffectiveKnownRefused('unqualified_source_absence')
        return {'status': 'uninitialized', 'changed': []}
    with exclusive_destination_lock(Path(lock), owner_uid):
        owned = read_owned(root, owner_uid=owner_uid)
        if owned is None:
            raise EffectiveKnownRefused('source_disappeared_under_lock')
        before = {name: _target(path, owner_uid)[0] for name, path in paths.items()}
        try:
            manual = {name: before[name].decode('utf-8') for name in paths}
        except UnicodeError as exc:
            raise EffectiveKnownRefused('invalid_managed_hostlist_encoding') from exc
        merged = compose_known(manual, owned)
        changed = []
        for name in KNOWN_HOSTLISTS:
            content = merged[name].encode('utf-8')
            if before[name] != content:
                _replace(paths[name], before[name], content, owner_uid)
                changed.append(name)
        return {'status': 'composed', 'changed': changed}



def _verify_planned_preimages_locked(verified: dict, targets: dict, *,
                                      owned_root: Path, owner_uid: int) -> None:
    """One P2-locked physical witness shared by detached build and Apply gate."""
    current = read_owned(Path(owned_root), owner_uid=owner_uid)
    if current is None:
        raise EffectiveKnownRefused("planned_known_owner_uninitialized")
    for name in SHARED_FOUND_NAMES:
        before, _after, identity, status = verified[name]
        path = targets[name]
        if status == "missing":
            if name != "auto":
                raise EffectiveKnownRefused("planned_known_missing")
            _shared_found_assert_missing(path, owner_uid)
        else:
            content, st = _target(path, owner_uid)
            observed = (st.st_dev, st.st_ino, st.st_ctime_ns,
                        st.st_mtime_ns, st.st_size)
            if content != before or observed != identity:
                raise EffectiveKnownRefused("planned_preimage_drift")
        if name in KNOWN_HOSTLISTS and current[name].encode() != before:
            raise EffectiveKnownRefused("planned_known_owner_drift")


def verify_planned_preimages(rows: dict, *, targets: dict,
                             owned_root: Path = OWNED_ROOT,
                             lock: Path = AUTO_LOCK, owner_uid: int = 0) -> dict:
    """Read-only post-seal check; not a lock held through later activation.

    A minute write between detached build and FD9 executor must be detected.
    This DOES NOT authorize commit or solve the Config+three-file crash window.
    """
    if (not isinstance(targets, dict) or
            list(targets) != list(SHARED_FOUND_NAMES) or
            any(not isinstance(targets[name], Path) or
                    not targets[name].is_absolute() for name in SHARED_FOUND_NAMES) or
            targets["youtube"] != Path(owned_root) / "youtube.txt" or
            targets["user"] != Path(owned_root) / "user.txt"):
        raise EffectiveKnownRefused("unsafe_planned_known_root")
    verified = _qualified_shared_found_batch(rows)
    with exclusive_destination_lock(Path(lock), owner_uid):
        _verify_planned_preimages_locked(
            verified, targets, owned_root=Path(owned_root), owner_uid=owner_uid)
    return {"status": "planned-preimages-current", "commit_authorized": False}


def compose_stage_planned(
    youtube: Path, user: Path, rows: dict, *, targets: dict,
    owned_root: Path = OWNED_ROOT, lock: Path = AUTO_LOCK,
    owner_uid: int = 0,
) -> dict:
    """Bind one original FD9 P1 after-image to the DETACHED runtime only.

    The minute writer and this operation share the existing P2 destination
    lock. A change after the earlier Config/P1 stage means REFUSE and rebuild
    a fresh request, never use old positives or overwrite a new discovery.
    Nothing in the live owner, native Config, IPFW or original journal moves.
    This is not the later all-resource commit or a successful Apply.
    """
    paths = {"youtube": Path(youtube), "user": Path(user)}
    if (list(targets) != list(SHARED_FOUND_NAMES) or
            any(not isinstance(targets[name], Path) or
                not targets[name].is_absolute() for name in SHARED_FOUND_NAMES) or
            any(not p.is_absolute() for p in paths.values()) or
            len(set(paths.values())) != 2 or
            targets["youtube"] != Path(owned_root) / "youtube.txt" or
            targets["user"] != Path(owned_root) / "user.txt"):
        raise EffectiveKnownRefused("unsafe_planned_known_root")
    verified = _qualified_shared_found_batch(rows)
    with exclusive_destination_lock(Path(lock), owner_uid):
        _verify_planned_preimages_locked(
            verified, targets, owned_root=Path(owned_root), owner_uid=owner_uid)
        staged = {name: _target(path, owner_uid)[0] for name, path in paths.items()}
        try:
            manual = {name: staged[name].decode("utf-8") for name in paths}
        except UnicodeError as exc:
            raise EffectiveKnownRefused("invalid_planned_managed_encoding") from exc
        prospective = {
            name: verified[name][1].decode("utf-8")
            for name in KNOWN_HOSTLISTS
        }
        merged = compose_known(manual, prospective)
        changed = []
        for name in KNOWN_HOSTLISTS:
            data = merged[name].encode("utf-8")
            if staged[name] != data:
                _replace(paths[name], staged[name], data, owner_uid)
                changed.append(name)
        # "auto" after is authenticated in rows but cannot become the live
        # shared destination until the ORIGINAL joint Config/file transaction.
        return {"status": "planned-detached", "changed": changed,
                "auto_live_committed": False, "config_committed": False}


def compose_native_planned(youtube: Path, user: Path, operation: str) -> dict:
    """Only the original FD9 native shared candidate may request this mode."""
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation)):
        raise EffectiveKnownRefused("native_original_fd9_required")
    from voice_ipfw_adapter import require_lifecycle_lock
    from shared_apply_seal import WORK, _stat

    require_lifecycle_lock()
    work = WORK / operation
    _stat(WORK, 0, directory=True)
    _stat(work, 0, directory=True)
    expected = work / "release" / "managed" / ".input"
    if (Path(youtube) != expected / "hostlist-youtube.out" or
            Path(user) != expected / "hostlist-user.out"):
        raise EffectiveKnownRefused("foreign_detached_stage")
    raw, _ = _target(work / "plan.json", 0)
    if len(raw) > 4 * 1024 * 1024:
        raise EffectiveKnownRefused("oversized_planned_bundle")
    try:
        plan = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise EffectiveKnownRefused("invalid_planned_bundle") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("commit_authorized") is not False or
            not isinstance(plan.get("found_batch"), dict)):
        raise EffectiveKnownRefused("unqualified_planned_bundle")
    return compose_stage_planned(
        Path(youtube), Path(user), plan["found_batch"],
        targets={"youtube": OWNED_ROOT / "youtube.txt",
                 "user": OWNED_ROOT / "user.txt",
                 "auto": AUTO_HOSTLIST},
    )


def verify_native_planned(operation: str) -> dict:
    """Post-seal native FD9 gate, before ANY original lifecycle mutation."""
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation)):
        raise EffectiveKnownRefused("native_original_fd9_required")
    from voice_ipfw_adapter import require_lifecycle_lock
    from shared_apply_seal import WORK, _stat, verify_seal

    require_lifecycle_lock()
    work = WORK / operation
    _stat(WORK, 0, directory=True)
    _stat(work, 0, directory=True)
    # All bytes of the original private plan AND detached release must still
    # match the original shared Apply seal before comparing live sources.
    verify_seal(work, owner=0)
    raw, _ = _target(work / "plan.json", 0)
    if len(raw) > 4 * 1024 * 1024:
        raise EffectiveKnownRefused("oversized_planned_bundle")
    try:
        plan = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise EffectiveKnownRefused("invalid_planned_bundle") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("commit_authorized") is not False or
            not isinstance(plan.get("found_batch"), dict)):
        raise EffectiveKnownRefused("unqualified_planned_bundle")
    return verify_planned_preimages(
        plan["found_batch"],
        targets={"youtube": OWNED_ROOT / "youtube.txt",
                 "user": OWNED_ROOT / "user.txt",
                 "auto": AUTO_HOSTLIST},
    )




def prepare_native_found_intent(
        operation: str, config_fd: int, candidate_digest: str) -> dict:
    """Original Config -> P2 -> existing journal, before any file mutation.

    Import-only staging primitive. ONLY a future original PHP Config::lock
    owner can pass its genuine inherited Config FD, plus original FD9. It
    MUST NOT be dispatched by the current GUI or ordinary shell Apply, since
    full Config+three-file write/recovery is deliberately still gated.
    """
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation) or
            type(config_fd) is not int or config_fd < 3 or
            not isinstance(candidate_digest, str) or
            not re.fullmatch(r"[a-f0-9]{64}", candidate_digest)):
        raise EffectiveKnownRefused("native_original_config_fd9_required")
    import hashlib
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd)
    from shared_apply_seal import WORK, _stat, verify_seal
    from shared_apply_operation import SharedApplyOperation
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    _stat(WORK, 0, directory=True)
    work = WORK / operation
    _stat(work, 0, directory=True)
    signed = verify_seal(work, owner=0)
    raw, _ = _target(work / "plan.json", 0)
    if (len(raw) > 4 * 1024 * 1024 or
            hashlib.sha256(raw).hexdigest() !=
            signed.get("sha256", {}).get("plan.json")):
        raise EffectiveKnownRefused("native_found_sealed_plan_changed")
    try:
        plan = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise EffectiveKnownRefused("native_found_plan_invalid") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            not isinstance(plan.get("dependencies"), str) or
            not re.fullmatch(r"[a-f0-9]{64}", plan["dependencies"]) or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("config_revision") != plan["dependencies"] or
            plan["found_intent"].get("commit_authorized") is not False or
            not isinstance(plan.get("found_batch"), dict) or
            not isinstance(plan.get("changed_fields"), list)):
        raise EffectiveKnownRefused("native_found_plan_not_qualified")
    detail = {"id": operation, "page": "strategies",
              "base": plan["dependencies"], "candidate": candidate_digest,
              "changed_fields": plan["changed_fields"]}
    verified = _qualified_shared_found_batch(plan["found_batch"])
    targets = {"youtube": OWNED_ROOT / "youtube.txt",
               "user": OWNED_ROOT / "user.txt",
               "auto": AUTO_HOSTLIST}
    # The invoking PHP owner holds the original Config lock for the WHOLE
    # call. P2 is acquired AFTER Config, then held THROUGH original journal
    # fsync, preventing minute writers from changing physical preimages.
    with exclusive_destination_lock(AUTO_LOCK, 0):
        _verify_planned_preimages_locked(
            verified, targets, owned_root=OWNED_ROOT, owner_uid=0)

        def original_witness(attested: bytes) -> bool:
            if attested != raw:
                return False
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            verify_seal(work, owner=0)
            _verify_planned_preimages_locked(
                verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
            return True

        record = SharedApplyOperation(owner=0).prepare_found(
            detail, raw, original_witness)
        _verify_planned_preimages_locked(
            verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return {"result": "original-found-intent-durable",
            "phase": record["phase"],
            "commit_authorized": False,
            "restore_authorized": False}


def classify_planned_file_images(
    rows: dict, *, targets: dict, owned_root: Path = OWNED_ROOT,
    lock: Path = AUTO_LOCK, owner_uid: int = 0,
    journal_phase: str | None = None,
    post_images: dict | None = None,
    staged_images: dict | None = None,
) -> dict:
    """READ ONLY image evidence from the original sealed three-source plan.

    The optional original FD9 ready/installed staged inode witnesses can
    attribute a physical after-image, not authorize rollback/replay.
    Merely identical bytes never prove writer ownership; Config, runtime,
    lifecycle and journal remain untouched.
    """
    if (not isinstance(targets, dict) or
            list(targets) != list(SHARED_FOUND_NAMES) or
            any(not isinstance(targets[name], Path) or
                    not targets[name].is_absolute() for name in SHARED_FOUND_NAMES) or
            len(set(targets.values())) != len(SHARED_FOUND_NAMES) or
            targets["youtube"] != Path(owned_root) / "youtube.txt" or
            targets["user"] != Path(owned_root) / "user.txt"):
        raise EffectiveKnownRefused("unsafe_cold_found_targets")
    verified = _qualified_shared_found_batch(rows)
    with exclusive_destination_lock(Path(lock), owner_uid):
        current = read_owned(Path(owned_root), owner_uid=owner_uid)
        if current is None:
            raise EffectiveKnownRefused("cold_found_owner_uninitialized")
        states = {}
        for name in SHARED_FOUND_NAMES:
            before, after, identity, initial_status = verified[name]
            path = targets[name]
            try:
                observed, st = _target(path, owner_uid)
            except DestinationRefused as exc:
                if (name == "auto" and initial_status == "missing" and
                        isinstance(exc.__cause__, FileNotFoundError)):
                    _shared_found_assert_missing(path, owner_uid)
                    states[name] = "before"
                    continue
                raise
            if name in KNOWN_HOSTLISTS and current[name].encode("utf-8") != observed:
                raise EffectiveKnownRefused("cold_found_owner_mismatch")
            physical = (st.st_dev, st.st_ino, st.st_ctime_ns,
                        st.st_mtime_ns, st.st_size)
            if initial_status == "present" and observed == before and physical == identity:
                states[name] = "before"
            elif observed == after and after != before:
                states[name] = "after-image"
            else:
                # Same-byte inode replacements and foreign content are NOT
                # evidence of the original writer or a valid rollback.
                raise EffectiveKnownRefused("cold_found_unknown_image")
        # Source-only cold proof of the SAME original per-file FD9 ready /
        # installed WAL. Validate actual file inode + mtime + SHA while the
        # original P2 lock remains held. A ready temp may have disappeared
        # after a crash; absence is NOT permission to re-create/rollback it.
        stage_evidence = None
        if staged_images is not None:
            from shared_apply_operation import (
                _validate_found_stages, SharedOperationError)
            try:
                _validate_found_stages(staged_images)
            except SharedOperationError as exc:
                raise EffectiveKnownRefused("cold_found_invalid_staged_wal") from exc
            if journal_phase not in (
                    "found-files-writing", "found-files-written",
                    "found-config-saving", "found-config-saved"):
                raise EffectiveKnownRefused("cold_found_stage_outside_writing")
            changed = [
                name for name in SHARED_FOUND_NAMES
                if verified[name][0] != verified[name][1]]
            if any(name not in changed for name in staged_images):
                raise EffectiveKnownRefused("cold_found_stage_unchanged_source")
            stage_evidence = {}
            # The original writer changes sources in fixed canonical order.
            # No later stage can exist without all earlier ones installed.
            for index, name in enumerate(changed):
                stage = staged_images.get(name)
                if stage is None:
                    if name in staged_images:
                        raise EffectiveKnownRefused("cold_found_staged_null")
                    if journal_phase != "found-files-writing":
                        raise EffectiveKnownRefused("cold_found_incomplete_staged_wal")
                    if states[name] != "before":
                        raise EffectiveKnownRefused("cold_found_unstaged_after_image")
                    stage_evidence[name] = "not-started"
                    continue
                if any(staged_images.get(previous, {}).get("state") != "installed"
                       for previous in changed[:index]):
                    raise EffectiveKnownRefused("cold_found_staged_out_of_order")
                pin = stage["pin"]
                expected_bytes = verified[name][1]
                if (pin["size"] != len(expected_bytes) or
                        pin["sha256"] != hashlib.sha256(expected_bytes).hexdigest()):
                    raise EffectiveKnownRefused("cold_found_staged_plan_mismatch")
                if stage["state"] == "installed" or states[name] == "after-image":
                    if states[name] != "after-image":
                        raise EffectiveKnownRefused("cold_found_installed_not_present")
                    observed, st = _target(targets[name], owner_uid)
                    identity = (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size)
                    pinned = tuple(pin[key] for key in
                                   ("device", "inode", "mtime_ns", "size"))
                    if identity != pinned or hashlib.sha256(observed).hexdigest() != pin["sha256"]:
                        raise EffectiveKnownRefused("cold_found_staged_inode_changed")
                    stage_evidence[name] = ("installed-after" if stage["state"] == "installed"
                                            else "ready-but-after")
                elif stage["state"] == "ready" and states[name] == "before":
                    stage_evidence[name] = "ready-but-before"
                else:
                    raise EffectiveKnownRefused("cold_found_unqualified_staged_state")
            for name in SHARED_FOUND_NAMES:
                if name not in changed:
                    stage_evidence[name] = "unchanged-before"
                    if states[name] != "before":
                        raise EffectiveKnownRefused("cold_found_untouched_source_drift")
            if journal_phase in (
                    "found-files-written", "found-config-saving", "found-config-saved"):
                if (set(staged_images) != set(changed) or
                        any(stage["state"] != "installed"
                            for stage in staged_images.values()) or
                        post_images is None):
                    raise EffectiveKnownRefused("cold_found_complete_staged_proof_required")
        # The physical inode/time attestation is distinct from a byte match.
        # A cold foreign writer with identical content must be refused.
        if post_images is not None:
            from shared_apply_operation import _validate_found_post, SharedOperationError
            try:
                _validate_found_post(post_images)
            except SharedOperationError as exc:
                raise EffectiveKnownRefused("cold_found_untrusted_post_pins") from exc
            for name in SHARED_FOUND_NAMES:
                pin = post_images[name]
                if pin["status"] == "missing":
                    _shared_found_assert_missing(targets[name], owner_uid)
                    continue
                data, st = _target(targets[name], owner_uid)
                identity = (st.st_dev, st.st_ino, st.st_ctime_ns,
                            st.st_mtime_ns, st.st_size)
                expected = tuple(pin[key] for key in
                                 ("device", "inode", "ctime_ns", "mtime_ns", "size"))
                if (identity != expected or
                        hashlib.sha256(data).hexdigest() != pin["sha256"]):
                    raise EffectiveKnownRefused("cold_found_postimage_inode_changed")
        # Evaluate phase/physical consistency under this SAME destination
        # lock. No matching bytes alone prove which writer made them.
        if journal_phase is not None:
            if journal_phase not in (
                    "prepared", "found-files-writing", "found-files-written",
                    "found-config-saving", "found-config-saved"):
                raise EffectiveKnownRefused("cold_found_unknown_journal_phase")
            if journal_phase == "prepared" and any(
                    state != "before" for state in states.values()):
                raise EffectiveKnownRefused("cold_found_unexpected_prepared_image")
            if journal_phase in ("found-files-written", "found-config-saving",
                                 "found-config-saved"):
                for name in SHARED_FOUND_NAMES:
                    old, new, _, _ = verified[name]
                    if states[name] != ("after-image" if new != old else "before"):
                        raise EffectiveKnownRefused("cold_found_written_phase_diverged")
    receipt = {
        "result": "read-only-cold-image-classification",
        "image": ("all-before" if all(s == "before" for s in states.values())
                  else "contains-unattributed-after"),
        "states": states,
        "commit_authorized": False,
        "restore_authorized": False,
    }
    if stage_evidence is not None:
        receipt["stage_evidence"] = stage_evidence
    return receipt


def classify_native_planned(operation: str) -> dict:
    """No new Config owner: original FD9, original journal and sealed plan."""
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation)):
        raise EffectiveKnownRefused("native_original_fd9_required")
    from voice_ipfw_adapter import require_lifecycle_lock
    from shared_apply_seal import WORK, _stat, verify_seal
    from shared_apply_operation import (SharedApplyOperation, FOUND_FILE_PHASES,
                                        FOUND_CONFIG_PHASES)
    import hashlib

    require_lifecycle_lock()
    record = SharedApplyOperation(owner=0).read()
    if (record is None or record["phase"] not in (
            "prepared", *FOUND_FILE_PHASES, *FOUND_CONFIG_PHASES) or
            "found" not in record or
            record["detail"]["id"] != operation or
            record["detail"]["page"] != "strategies"):
        raise EffectiveKnownRefused("cold_found_not_original_pending_operation")
    work = WORK / operation
    _stat(WORK, 0, directory=True)
    _stat(work, 0, directory=True)
    verify_seal(work, owner=0)
    raw, _ = _target(work / "plan.json", 0)
    if (len(raw) > 4 * 1024 * 1024 or
            hashlib.sha256(raw).hexdigest() != record["found"]["plan_sha256"]):
        raise EffectiveKnownRefused("cold_found_original_plan_changed")
    try:
        plan = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise EffectiveKnownRefused("invalid_cold_found_plan") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            plan.get("dependencies") != record["detail"]["base"] or
            plan.get("changed_fields") != record["detail"]["changed_fields"] or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("config_revision") != record["detail"]["base"] or
            plan["found_intent"].get("commit_authorized") is not False or
            not isinstance(plan.get("found_batch"), dict)):
        raise EffectiveKnownRefused("unqualified_cold_found_plan")
    return classify_planned_file_images(
        plan["found_batch"],
        targets={"youtube": OWNED_ROOT / "youtube.txt",
                 "user": OWNED_ROOT / "user.txt",
                 "auto": AUTO_HOSTLIST},
        journal_phase=record["phase"],
        post_images=record["found"].get("post"),
        staged_images=record["found"].get("stages"),
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == 'classify-planned':
        try:
            receipt = classify_native_planned(argv[1])
            # Only bounded status tokens; never print private domains or
            # imply that this diagnostic authorizes any mutation.
            print('found-image=' + receipt['image'])
            return 0
        except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
                DomainPolicyError, AutoDomainPolicyError,
                ValueError, RuntimeError, OSError, UnicodeError):
            print('ERROR: original FD9 cold HOSTLIST image unknown',
                  file=sys.stderr)
            return 69
    if len(argv) == 2 and argv[0] == 'verify-planned':
        try:
            verify_native_planned(argv[1])
            return 0
        except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
                DomainPolicyError, AutoDomainPolicyError,
                ValueError, RuntimeError, OSError, UnicodeError):
            print('ERROR: original FD9 sealed HOSTLIST preimage drift',
                  file=sys.stderr)
            return 2
    if len(argv) == 4 and argv[0] == 'compose-planned':
        try:
            compose_native_planned(Path(argv[1]), Path(argv[2]), argv[3])
            return 0
        except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
                DomainPolicyError, AutoDomainPolicyError,
                ValueError, RuntimeError, OSError, UnicodeError):
            print('ERROR: original FD9 prospective HOSTLIST mismatch',
                  file=sys.stderr)
            return 2
    if len(argv) != 3 or argv[0] != 'compose':
        print('ERROR: native effective HOSTLIST invocation refused', file=sys.stderr)
        return 2
    # Portable offline builders have no native auto-owned storage. Their
    # strictly read-only no-op is required for existing Linux source tests;
    # only root on FreeBSD may read or mutate an initialized owned source.
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        try:
            if read_owned(OWNED_ROOT, owner_uid=0) is None:
                return 0
        except (OwnedSourcesRefused, OSError):
            pass
        print('ERROR: native effective HOSTLIST invocation refused', file=sys.stderr)
        return 2
    try:
        compose_stage(Path(argv[1]), Path(argv[2]))
        return 0
    except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
            DomainPolicyError, AutoDomainPolicyError, ValueError, OSError):
        print('ERROR: protected effective HOSTLIST composition unavailable', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
