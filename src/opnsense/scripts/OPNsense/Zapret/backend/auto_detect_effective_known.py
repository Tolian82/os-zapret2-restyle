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
    DestinationRefused, SHARED_FOUND_NAMES, _qualified_shared_found_batch, _edit,
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



def inspect_live_known_readonly(
    manual: dict[str, str], *,
    active: Path = Path("/usr/local/etc/zapret2/runtime-v2"),
    owned_root: Path = OWNED_ROOT,
    owner_uid: int = 0,
    attest=None,
) -> dict:
    """TZ6V2-07: read-only, SAME-generation live known-file witness.

    The eventual minute caller MUST already hold original FD9 -> Config ->
    P2, and MUST obtain manual from that locked native Config Model. The
    default attester independently verifies owner, PID/birth, executable,
    full kernel argv, sealed generation, and original journal. This helper
    does not acquire authority, replace files, checkpoint or ACK pending.
    No read-side result may authorize a later write without rechecking its
    physical inode images inside the original destination transaction.
    """
    from auto_detect_owner import (
        GenerationProof, LearningGenerationProof, MAX_ARGS,
        attest_running_generation,
    )

    attest = attest_running_generation if attest is None else attest
    if not callable(attest):
        raise EffectiveKnownRefused("invalid_live_owner_attester")
    before_owner = attest()
    if not isinstance(before_owner, (GenerationProof, LearningGenerationProof)):
        raise EffectiveKnownRefused("live_owner_not_attested")

    active = Path(active)
    if not active.is_absolute() or not Path(owned_root).is_absolute():
        raise EffectiveKnownRefused("relative_live_known_root")
    args, _ = _target(active / "dvtws.args", owner_uid)
    if (len(args) > MAX_ARGS or
            hashlib.sha256(args).hexdigest() != before_owner.final_args_sha256):
        raise EffectiveKnownRefused("live_argv_not_original_generation")
    try:
        tokens = args.decode("utf-8").split()
    except UnicodeError as exc:
        raise EffectiveKnownRefused("invalid_live_argv_encoding") from exc
    selectors = [value[len("--hostlist="):] for value in tokens
                 if value.startswith("--hostlist=")]
    if len(selectors) > 256 or not all(selectors):
        raise EffectiveKnownRefused("invalid_live_hostlist_selectors")

    actual_paths = {
        name: active / "managed" / ("hostlist-" + name + ".txt")
        for name in KNOWN_HOSTLISTS
    }
    used = set(selectors)
    # Shared auto lives at its independent direct runtime path, and is
    # intentionally not a known managed source.
    allowed = {str(path) for path in actual_paths.values()} | {
        str(AUTO_HOSTLIST)
    }
    if used - allowed:
        raise EffectiveKnownRefused("foreign_live_hostlist_selector")
    if isinstance(before_owner, LearningGenerationProof):
        # The original exact kernel-argv owner attests the generator's
        # complete schema3 source/native map first. Only hostlists
        # authorized by that map may claim a corresponding working file.
        mapped = {name for _number, name, _path in before_owner.learning}
    else:
        mapped = {name for _number, status, name in before_owner.profiles
                  if status == "known-hostlist"}
    if (not mapped.issubset(set(KNOWN_HOSTLISTS)) or
            {name for name, path in actual_paths.items()
             if str(path) in used} != mapped):
        raise EffectiveKnownRefused("native_profile_managed_selector_mismatch")

    owned = read_owned(Path(owned_root), owner_uid=owner_uid)
    if owned is None:
        raise EffectiveKnownRefused("unqualified_live_known_owned_snapshot")
    expected = compose_known(manual, owned)
    files = {}
    for name in KNOWN_HOSTLISTS:
        path = actual_paths[name]
        actual, st = _target(path, owner_uid)
        files[name] = {
            "path": str(path),
            "source_sha256": hashlib.sha256(owned[name].encode("utf-8")).hexdigest(),
            "expected_sha256": hashlib.sha256(expected[name].encode("utf-8")).hexdigest(),
            "actual_sha256": hashlib.sha256(actual).hexdigest(),
            "physical": [st.st_dev, st.st_ino, st.st_ctime_ns,
                         st.st_mtime_ns, st.st_size],
            "aligned": actual == expected[name].encode("utf-8"),
        }

    # A drifted process or replaced file between snapshot and result is NOT
    # a stable before-image for any future write. No signals or services.
    for name in KNOWN_HOSTLISTS:
        actual, st = _target(actual_paths[name], owner_uid)
        pin = files[name]
        if (hashlib.sha256(actual).hexdigest() != pin["actual_sha256"] or
                [st.st_dev, st.st_ino, st.st_ctime_ns,
                 st.st_mtime_ns, st.st_size] != pin["physical"]):
            raise EffectiveKnownRefused("live_known_changed_during_inspection")
    if attest() != before_owner:
        raise EffectiveKnownRefused("live_owner_changed_during_inspection")
    return {
        "status": "read-only-active-known-witness",
        "owner_schema": 3 if isinstance(before_owner, LearningGenerationProof) else 2,
        "generation": before_owner.generation,
        "operation": before_owner.operation_id,
        "pid": before_owner.owner.pid,
        "started": before_owner.owner.started,
        "referenced_known": sorted(mapped),
        "files": files,
        "aligned": all(files[name]["aligned"] for name in KNOWN_HOSTLISTS),
        "commit_authorized": False,
        "ack_authorized": False,
    }


def preview_live_known_after_readonly(
    manual: dict[str, str], effects: dict, *,
    active: Path = Path("/usr/local/etc/zapret2/runtime-v2"),
    owned_root: Path = OWNED_ROOT,
    owner_uid: int = 0,
    attest=None,
) -> dict:
    """TZ6V2-07 P2: calculate exact future active managed-file images.

    Call ONLY inside the original FD9 -> native Config -> P2 critical
    section, from the original Model's locked manual snapshot. Do not use
    this returned preview as authorization to write: the original minute
    destination WAL must still seal the BEFORE physical inodes, AFTER
    hashes, owner epoch, per-file CAS/recovery and the final checkpoint.
    """
    if (not isinstance(effects, dict) or
            set(effects) - {"auto", *KNOWN_HOSTLISTS} or
            any(not isinstance(change, dict) or
                set(change) != {"add", "remove"} or
                not isinstance(change["add"], list) or
                not isinstance(change["remove"], list) or
                (name == "auto" and change["remove"])
                for name, change in effects.items())):
        raise EffectiveKnownRefused("unqualified_live_known_effects")

    witness = inspect_live_known_readonly(
        manual, active=active, owned_root=owned_root,
        owner_uid=owner_uid, attest=attest)
    # Schema2 observer can only relocate existing known-owned rows.
    # Schema3's FULL original generator + FD9 + same-PID owner is the only
    # mode allowed to propose NEW known Found additions in this preview.
    # The eventual writer must still CAS the existing original WAL slot.
    if (witness["owner_schema"] != 3 and
            any(name in KNOWN_HOSTLISTS and change["add"]
                for name, change in effects.items())):
        raise EffectiveKnownRefused("unqualified_live_known_effects")
    if not witness["aligned"]:
        raise EffectiveKnownRefused("live_known_preimage_not_aligned")

    owned = read_owned(Path(owned_root), owner_uid=owner_uid)
    if owned is None:
        raise EffectiveKnownRefused("missing_live_owned_source")
    prospective = {}
    for name in KNOWN_HOSTLISTS:
        original = owned[name].encode("utf-8")
        if hashlib.sha256(original).hexdigest() != witness["files"][name]["source_sha256"]:
            raise EffectiveKnownRefused("live_owned_source_changed_during_preview")
        edits = effects.get(name, {"add": [], "remove": []})
        modified = _edit(original, edits["add"], edits["remove"])
        prospective[name] = modified.decode("utf-8")
    after = compose_known(manual, prospective)

    records = {}
    changed = []
    for name in KNOWN_HOSTLISTS:
        previous = witness["files"][name]
        digest = hashlib.sha256(after[name].encode("utf-8")).hexdigest()
        records[name] = {
            "path": previous["path"],
            "before_sha256": previous["actual_sha256"],
            "after_sha256": digest,
            "source_before_sha256": previous["source_sha256"],
            "source_after_sha256": hashlib.sha256(
                prospective[name].encode("utf-8")).hexdigest(),
            "before_physical": previous["physical"],
            "changed": digest != previous["actual_sha256"],
        }
        if records[name]["changed"]:
            changed.append(name)
    # Between two P2-locked observations an external non-cooperating writer
    # may have changed a file. The preview must not imply a stable image.
    for name in KNOWN_HOSTLISTS:
        value, st = _target(Path(records[name]["path"]), owner_uid)
        pin = records[name]
        if (hashlib.sha256(value).hexdigest() != pin["before_sha256"] or
                [st.st_dev, st.st_ino, st.st_ctime_ns,
                 st.st_mtime_ns, st.st_size] != pin["before_physical"]):
            raise EffectiveKnownRefused("live_known_physical_preview_drift")
    if attest is None:
        from auto_detect_owner import attest_running_generation
        attest = attest_running_generation
    from auto_detect_owner import GenerationProof, LearningGenerationProof
    final_owner = attest()
    if (not isinstance(final_owner, (GenerationProof, LearningGenerationProof)) or
            (3 if isinstance(final_owner, LearningGenerationProof) else 2)
            != witness["owner_schema"] or
            final_owner.owner.pid != witness["pid"] or
            final_owner.owner.started != witness["started"] or
            final_owner.operation_id != witness["operation"] or
            final_owner.generation != witness["generation"]):
        raise EffectiveKnownRefused("live_known_preview_owner_drift")
    return {
        "status": "read-only-live-after-images",
        "generation": witness["generation"],
        "operation": witness["operation"],
        "pid": witness["pid"],
        "started": witness["started"],
        "changed": changed,
        "files": records,
        "commit_authorized": False,
        "ack_authorized": False,
    }


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
        operation: str, config_fd: int, candidate_digest: str, *,
        runtime_mode: str | None = None, base_digest: str | None = None,
        stopped_only: bool = False) -> dict:
    """Original Config -> P2 -> existing journal, before any file mutation.

    Production PHP passes the freshly locked base digest, not a copied
    plan dependency. The existing native PREPARED-only fixture may omit it.
    The private bound writer requires the fresh digest and a stopped owner.
    No runtime or Config save is authorized by PREPARED.
    """
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation) or
            type(config_fd) is not int or config_fd < 3 or
            not isinstance(candidate_digest, str) or
            not re.fullmatch(r"[a-f0-9]{64}", candidate_digest) or
            (base_digest is not None and
             (type(base_digest) is not str or
              not re.fullmatch(r"[a-f0-9]{64}", base_digest))) or
            type(stopped_only) is not bool or
            (stopped_only and (base_digest is None or runtime_mode not in ("0", "1")))):
        raise EffectiveKnownRefused("native_original_config_fd9_required")
    import hashlib
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd)
    from shared_apply_seal import WORK, _stat, verify_seal
    from shared_apply_operation import SharedApplyOperation, committed_owner
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
    if base_digest is not None and base_digest != plan["dependencies"]:
        raise EffectiveKnownRefused("native_found_base_config_changed")
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
    store = SharedApplyOperation(owner=0)
    with exclusive_destination_lock(AUTO_LOCK, 0):
        _verify_planned_preimages_locked(
            verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
        if runtime_mode is not None:
            from voice_live_inspect import examine_shared
            current = store.read()
            previous = committed_owner(current)
            if previous is None or previous["candidate"] != detail["base"]:
                raise EffectiveKnownRefused("native_found_predecessor_unverified")
            prior = examine_shared(current)
            states = ("stopped",) if stopped_only else ("ready", "stopped")
            if prior is None or prior.get("state") not in states:
                raise EffectiveKnownRefused("native_found_predecessor_unverified")

        def original_witness(attested: bytes) -> bool:
            if attested != raw:
                return False
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            verify_seal(work, owner=0)
            _verify_planned_preimages_locked(
                verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
            return True

        record = store.prepare_found(
            detail, raw, original_witness, runtime_mode=runtime_mode)
        _verify_planned_preimages_locked(
            verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return {"result": "original-found-intent-durable",
            "phase": record["phase"],
            "commit_authorized": False,
            "restore_authorized": False}


def begin_native_bound_found_save_locked(
        operation: str, config_fd: int, candidate_digest: str, *,
        base_digest: str, runtime_mode: str, source_fd: int,
        before_save, queue_fd: int | None = None) -> dict:
    """Private original PHP begin boundary, not a CLI or activation permit.

    The original Config owner must still hold FD4 and supply the fresh
    pre-serialization Model digest. P2a, if required, is owned by its
    parent BEFORE Config and remains held across save and readback.
    Read the retained original generator frame on a separate pipe, not
    the before-save handshake stdin. Only the existing original WAL/CAS
    writes below. Keep this import-only until bound runtime/recovery closes.
    """
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from auto_detect_destination_commit import (
        _bound_found_queue_scope, shared_apply_bound_found_files_original_fd9)
    from neutral_shared_apply_source_gate import read_inherited_original_source
    from shared_apply_operation import SharedApplyOperation, committed_owner, committed_manifest
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not re.fullmatch(r"[a-f0-9]{32}", operation) or
            any(type(value) is not str or not re.fullmatch(r"[a-f0-9]{64}", value)
                for value in (base_digest, candidate_digest)) or
            runtime_mode not in ("0", "1") or not callable(before_save) or
            type(config_fd) is not int or config_fd < 3 or config_fd == 9 or
            type(source_fd) is not int or source_fd < 3 or source_fd in (config_fd, 9) or
            (queue_fd is not None and
             (type(queue_fd) is not int or queue_fd < 3 or
              queue_fd in (config_fd, source_fd, 9)))):
        raise EffectiveKnownRefused("bound_found_original_save_transport_refused")
    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    current = store.read()
    previous = committed_owner(current)
    pin = committed_manifest(current)
    if (previous is None or previous["candidate"] != base_digest or
            previous["id"] == operation or
            ((pin is not None and pin["schema"] == 2) != (queue_fd is not None))):
        raise EffectiveKnownRefused("bound_found_original_save_predecessor_refused")
    # Authenticate the inherited open description BEFORE any PREPARED
    # mutation. Exiting this scope never unlocks the parent's P2a.
    with _bound_found_queue_scope(queue_fd):
        raw = read_inherited_original_source(source_fd)
        if store.read() != current:
            raise EffectiveKnownRefused("bound_found_original_save_owner_changed")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        prepare_native_found_intent(
            operation, config_fd, candidate_digest, runtime_mode=runtime_mode,
            base_digest=base_digest, stopped_only=True)
    # The existing writer re-adopts (does not reacquire) that SAME P2a,
    # binds the exact raw source to PREPARED, and holds P2 through ready.
    return shared_apply_bound_found_files_original_fd9(
        operation, config_fd, raw_pipe=raw, config_digest=base_digest,
        before_save=before_save, queue_fd=queue_fd)


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



def recover_native_found_prepared_pristine(
        operation: str, *, config_fd: int, config_digest: str,
        queue_fd: int | None = None) -> dict:
    """Original FD9/Config/P2 cold PREPARED closure for a proven predecessor.

    IMPORT ONLY: the future existing PHP Config::lock owner must supply the
    fresh WHOLE native Model digest while it holds the exact inherited fd4.
    This function is deliberately NOT a CLI, configd or GUI action. It
    performs one existing-journal fsync and NO Config/file/runtime/IPFW write.
    First-install without a physically proven previous owner stays pending.
    A later WAL phase is never recoverable via this pristine-only path.
    """
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation) or
            type(config_fd) is not int or config_fd < 3 or
            not isinstance(config_digest, str) or
            not re.fullmatch(r"[a-f0-9]{64}", config_digest)):
        raise EffectiveKnownRefused("native_found_pristine_original_owner_required")
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd)
    from shared_apply_operation import SharedApplyOperation
    from shared_apply_seal import WORK, _stat, verify_seal
    from voice_ipfw_adapter import require_lifecycle_lock
    from voice_live_inspect import examine_pending_found_previous

    require_lifecycle_lock()
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    pending = store.read()
    if (pending is None or pending["phase"] != "prepared" or
            "found" not in pending or pending["detail"]["id"] != operation or
            pending["detail"]["page"] != "strategies" or
            pending["detail"]["base"] != config_digest):
        raise EffectiveKnownRefused("native_found_pristine_phase_or_config_drift")
    predecessor = pending.get("previous")
    if predecessor is None or predecessor["candidate"] != config_digest:
        # No predecessor is NOT proof that no foreign process/IPFW exists.
        raise EffectiveKnownRefused("native_found_pristine_predecessor_unproven")
    _stat(WORK, 0, directory=True)
    work = WORK / operation
    _stat(work, 0, directory=True)
    seal = verify_seal(work, owner=0)
    raw, plan_stat = _target(work / "plan.json", 0)
    # The seal authenticates bytes, not a pathname's inode. Pin the actual
    # original file identity as well as the immutable plan hash.
    plan_pin = (plan_stat.st_dev, plan_stat.st_ino, plan_stat.st_ctime_ns,
                plan_stat.st_mtime_ns, plan_stat.st_size)
    if (len(raw) > 4 * 1024 * 1024 or
            hashlib.sha256(raw).hexdigest() !=
            pending["found"]["plan_sha256"] or
            hashlib.sha256(raw).hexdigest() !=
            seal.get("sha256", {}).get("plan.json")):
        raise EffectiveKnownRefused("native_found_pristine_seal_changed")
    try:
        plan = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise EffectiveKnownRefused("native_found_pristine_plan_invalid") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            plan.get("dependencies") != config_digest or
            plan.get("changed_fields") != pending["detail"]["changed_fields"] or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("config_revision") != config_digest or
            plan["found_intent"].get("commit_authorized") is not False):
        raise EffectiveKnownRefused("native_found_pristine_plan_not_qualified")
    verified = _qualified_shared_found_batch(plan.get("found_batch"))
    targets = {"youtube": OWNED_ROOT / "youtube.txt",
               "user": OWNED_ROOT / "user.txt", "auto": AUTO_HOSTLIST}

    from auto_detect_destination_commit import (
        _bound_found_queue_scope, _attest_bound_found_predecessor)
    from auto_detect_epoch_receipts import EpochReceipts
    from neutral_schema3_quiescent_preimage import _verify_idle_producer
    retired = pending.get("previous_manifest", {}).get("schema") == 2
    if retired != (queue_fd is not None) or (retired and (
            pending["found"].get("runtime_mode") != "0" or
            ("manifest" in pending and pending["manifest"]["schema"] != 1))):
        raise EffectiveKnownRefused("native_found_pristine_queue_scope_refused")
    # An incomplete root staging operation is evidence, not authority.
    # Do not repair, remove or bind it during a pristine recovery.
    from neutral_root_stage import ROOT_NAME, PENDING_NAME
    def check_unbound():
        if retired and "manifest" not in pending:
            for name in (ROOT_NAME, PENDING_NAME):
                path = work / name
                if path.exists() or path.is_symlink():
                    raise EffectiveKnownRefused("native_found_pristine_unbound_root_requires_review")

    # FD9 -> inherited P2a (if learning) -> native Config -> P2.
    # Preserve the exact historical owner and idle producer throughout.
    with _bound_found_queue_scope(queue_fd) as queue, exclusive_destination_lock(AUTO_LOCK, 0):
        def observe_previous():
            check_unbound()
            result = examine_pending_found_previous(pending)
            if retired:
                physical = _attest_bound_found_predecessor(pending, config_fd, queue)
                idle = _verify_idle_producer(queue, EpochReceipts(
                    owner_uid=0, writer_gid=queue.writer_gid))
                if result["state"] != "stopped":
                    raise EffectiveKnownRefused("native_found_pristine_retired_not_stopped")
                return result, physical, idle
            return result, None, None
        def attest_original(unchanged_plan: bytes, old: dict | None) -> bool:
            if unchanged_plan != raw or old != predecessor:
                return False
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != pending:
                return False
            # Another self-consistent seal is NOT the original sealed
            # transaction: refuse before the journal becomes RESTORED.
            if verify_seal(work, owner=0) != seal:
                return False
            current_raw, current_stat = _target(work / "plan.json", 0)
            if (current_raw != raw or
                    (current_stat.st_dev, current_stat.st_ino,
                     current_stat.st_ctime_ns, current_stat.st_mtime_ns,
                     current_stat.st_size) != plan_pin):
                return False
            _verify_planned_preimages_locked(
                verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
            prior_again = observe_previous()
            return (prior_again[0]["id"] == predecessor["id"] and
                    prior_again[0]["state"] in ("ready", "stopped") and
                    prior_again == observed)

        _verify_planned_preimages_locked(
            verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
        observed = observe_previous()
        if (observed[0]["id"] != predecessor["id"] or
                observed[0]["state"] not in ("ready", "stopped")):
            raise EffectiveKnownRefused("native_found_pristine_runtime_unproven")
        completed = store.finish_found_prepared_pristine(
            operation, raw, attest_original)
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    return {"result": "original-found-prepared-pristine-restored",
            "phase": completed["phase"],
            "previous_id": predecessor["id"], "runtime_state": observed[0]["state"],
            "config_saved": False, "files_written": False,
            "service_restarted": False}



def classify_native_planned(operation: str, *, config_fd: int | None = None) -> dict:
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
    if config_fd is not None:
        from auto_detect_original_lock_handoff import (
            CONFIG_PATH, assert_inherited_config_fd)
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    record = store.read()
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
    evidence = classify_planned_file_images(
        plan["found_batch"],
        targets={"youtube": OWNED_ROOT / "youtube.txt",
                 "user": OWNED_ROOT / "user.txt",
                 "auto": AUTO_HOSTLIST},
        journal_phase=record["phase"],
        post_images=record["found"].get("post"),
        staged_images=record["found"].get("stages"),
    )
    if config_fd is not None:
        # Still under the inherited original FD9 and Config lock, observe
        # only the already-sealed PREVIOUS common runtime and its exact IPFW.
        # A healthy old owner is information, NEVER an authorization.
        from voice_live_inspect import examine_pending_found_previous
        previous_runtime = examine_pending_found_previous(record)
        # The minute collector may have updated a source while we inspected
        # the old engine. Require exactly the same current P2 images again.
        # This is diagnostic; no one may later use its receipt to skip a
        # fresh lock-held preimage check before writing.
        again = classify_planned_file_images(
            plan["found_batch"],
            targets={"youtube": OWNED_ROOT / "youtube.txt",
                     "user": OWNED_ROOT / "user.txt",
                     "auto": AUTO_HOSTLIST},
            journal_phase=record["phase"],
            post_images=record["found"].get("post"),
            staged_images=record["found"].get("stages"))
        if again != evidence or store.read() != record:
            raise EffectiveKnownRefused("cold_found_changed_during_runtime_read")
        # Native Config remains pinned by original fd4 and original FD9.
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return {**evidence, "journal_phase": record["phase"],
                "previous_runtime": previous_runtime}
    return {**evidence, "journal_phase": record["phase"]}


def finish_native_bound_stopped_found_locked(operation: str, digest: str, *,
                                             config_fd: int,
                                             queue_fd: int | None = None) -> dict:
    """Original disabled two-bound Found promotion; no Config or engine writer.

    The original found-config-saved WAL is the durable promotion intent.
    Preserve all three P1 post-image pins until terminal readback. Unknown
    or interrupted partial trees stay nonterminal; never repair them here.
    """
    import subprocess
    from auto_detect_destination_commit import (
        _native_found_wal_context, _bound_found_native_witness,
        _attest_found_after_locked, _bound_found_queue_scope,
        _attest_bound_found_predecessor)
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from auto_detect_minute import inspect_inert_release
    from neutral_root_stage import _verify_original_pinned_root
    from neutral_schema3_previous_physical import (
        FinalBoundRuntimeReceipt, attest_bound_candidate_final_under_fd9)
    from neutral_schema3_quiescent_preimage import (
        _cold_recovery_trees, _reject_cold_recovery_residue, _run_bound_restore_joined,
        _zero_processes, _safe_empty_directory, _empty_kernel,
        _verify_idle_producer, _verify_retired_history,
        CHILD_PID, MONITOR_PID, DAEMON_PID, PRODUCER_ROOT, COMMON_ACTIVE, SCRIPT)
    from shared_apply_seal import WORK, verify_seal, _stat
    from voice_ipfw_adapter import require_lifecycle_lock
    from auto_detect_epoch_receipts import EpochReceipts, _read
    from auto_detect_learning_retirement import RETIRE_DIR, READY

    store, record, raw, rows, targets, attest = _native_found_wal_context(
        operation, config_fd)
    detail = record["detail"]
    prior = record.get("previous")
    prior_schema = record.get("previous_manifest", {}).get("schema")
    retired = prior_schema == 2
    if (record["phase"] not in ("found-config-saving", "found-config-saved") or
            record.get("manifest", {}).get("schema") != 1 or
            prior_schema not in (1, 2) or
            (retired != (queue_fd is not None)) or
            type(prior) is not dict or prior["candidate"] != detail["base"] or
            digest != detail["candidate"] or
            record["found"].get("runtime_mode") != "0" or
            (record["phase"] == "found-config-saving" and
             detail["base"] == detail["candidate"])):
        raise EffectiveKnownRefused("bound_stopped_found_finish_scope_refused")
    active = COMMON_ACTIVE
    old_work, new_work = WORK / prior["id"], WORK / detail["id"]
    backup_root = active.with_name("runtime-v2-backups")
    backup = backup_root / (active.name + "-" + detail["id"])
    old_hash = verify_seal(old_work, owner=0)["sha256"]["release"]
    new_hash = verify_seal(new_work, owner=0)["sha256"]["release"]
    if old_hash == new_hash:
        raise EffectiveKnownRefused("bound_stopped_found_ambiguous_tree")
    pristine = (old_hash, None, None, None)
    staged = (old_hash, new_hash, None, None)
    parked = (None, new_hash, old_hash, None)
    backed_up = (None, new_hash, None, old_hash)
    installed = (new_hash, None, None, old_hash)
    interrupted = {staged: "staged", parked: "parked", backed_up: "backed-up"}
    # An original retired owner requires its P2a inherited BEFORE PHP
    # acquired native Config. No new queue lock under this Config/P2 scope.
    with _bound_found_queue_scope(queue_fd) as queue, exclusive_destination_lock(AUTO_LOCK, store.owner):
        witness = _bound_found_native_witness(store, record, attest)

        def retired_history(current):
            if not retired:
                return None
            if queue is None or not queue._held or current.get("previous") != prior:
                raise EffectiveKnownRefused("bound_stopped_found_original_retirement_required")
            receipts = EpochReceipts(owner_uid=0, writer_gid=queue.writer_gid)
            ready = (receipts._generation(prior["id"], create=False) /
                     RETIRE_DIR / READY)
            raw_ready = _read(ready, 0)
            ready_hash = hashlib.sha256(raw_ready).hexdigest()
            # Historical ACK/archive is independently checkable after the
            # old physical tree moves to park or backup; unlike live-owner
            # proof it does not assume old tree is still ACTIVE_DIR.
            _verify_retired_history(current, queue, receipts, ready_hash)
            idle = _verify_idle_producer(queue, receipts)
            if (_read(ready, 0) != raw_ready or
                    _verify_idle_producer(queue, receipts) != idle or
                    store.read() != current):
                raise EffectiveKnownRefused("bound_stopped_found_retirement_changed")
            return ready_hash, idle

        def pinned_after(current):
            return (witness is not None and witness(current) and
                    read_owned(OWNED_ROOT, owner_uid=store.owner) is not None and
                    _attest_found_after_locked(rows, targets, current, uid=store.owner))

        def observe(current):
            store._attest_bound_found_checkpoint(current, pinned_after)
            for key, d, work in (("previous_manifest", prior, old_work),
                                 ("manifest", detail, new_work)):
                root = json.loads(_verify_original_pinned_root(
                    detail=d, binding=current[key], parent=WORK, owner_uid=0))
                if key == "previous_manifest" and retired:
                    if (root["service"]["enabled"] is not True or
                            root["service"]["target_mode"] != "auto"):
                        raise EffectiveKnownRefused("bound_stopped_found_old_auto_root_required")
                elif (root["service"]["enabled"] is not False or
                        root["service"]["target_mode"] not in ("all", "list") or
                        inspect_inert_release(work / "release", owner_uid=0) != "inactive"):
                    raise EffectiveKnownRefused("bound_stopped_found_inert_root_required")
            _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
            if not retired:
                _safe_empty_directory(PRODUCER_ROOT, 0)
            history = retired_history(current)
            _reject_cold_recovery_residue(active)
            trees = _cold_recovery_trees(
                active, detail["id"], old_hash, new_hash, phase="activating",
                restored=False, owner_uid=0)
            if trees not in (pristine, installed, *interrupted):
                raise EffectiveKnownRefused("bound_stopped_found_unknown_tree_requires_review")
            kernels = (_empty_kernel(old_work / "release"), _empty_kernel(new_work / "release"))
            if kernels[0] != kernels[1]:
                raise EffectiveKnownRefused("bound_stopped_found_kernel_changed")
            _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
            store._attest_bound_found_checkpoint(current, pinned_after)
            return trees, kernels, history

        before = observe(record)
        if observe(record) != before:
            raise EffectiveKnownRefused("bound_stopped_found_preimage_changed")
        if retired and before[0] == pristine:
            # Before the very first rename, also require the ORIGINAL old
            # stopped Auto owner with native birth/epoch/P2b proof, not
            # merely a matching historical checksum. Later crash recovery
            # relies on anchored READY/ACK and exact physical park/backup.
            old_proof = _attest_bound_found_predecessor(record, config_fd, queue)
            if (len(old_proof) != 4 or old_proof[3] != before[2][0] or
                    old_proof[0] != old_hash or old_proof[1] != before[1][0]):
                raise EffectiveKnownRefused("bound_stopped_found_old_retired_owner_changed")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        os.fsync(config_fd)
        if record["phase"] == "found-config-saving":
            # A distinct locked Config after-image and exact original P1
            # post-images qualify recovery, not a claim save returned.
            if before[0] != pristine:
                raise EffectiveKnownRefused("bound_stopped_found_unsaved_tree_changed")
            record = store.advance_found_config(
                "found-config-saved", detail, raw,
                lambda phase, plan: observe(record) == before,
                bound_attest=pinned_after)
        if before[0] != installed:
            if observe(record) != before:
                raise EffectiveKnownRefused("bound_stopped_found_install_preimage_changed")
            if before[0] == pristine:
                command = (
                    "/bin/sh", "-c", '. "$1"; . "$2"; atomic_install_tree "$3" "$4" "$5" "$6"',
                    "zapret-bound-stopped-found", str(SCRIPT / "backend/common.sh"),
                    str(SCRIPT / "backend/atomic.sh"), str(new_work / "release"),
                    str(active), str(backup_root), detail["id"])
            else:
                command = (
                    "/bin/sh", "-c", '. "$1"; . "$2"; atomic_resume_tree "$3" "$4" "$5" "$6" "$7" "$8"',
                    "zapret-bound-stopped-resume", str(SCRIPT / "backend/common.sh"),
                    str(SCRIPT / "backend/atomic.sh"), str(new_work / "release"),
                    str(old_work / "release"), str(active), str(backup_root),
                    detail["id"], interrupted[before[0]])
            try:
                reply = _run_bound_restore_joined(
                    command, pass_fds=(9, config_fd), budget=60, capture_output=True)
            except (OSError, subprocess.SubprocessError):
                raise EffectiveKnownRefused("bound_stopped_found_install_outcome_uncertain") from None
            if reply.returncode != 0 or reply.stdout != (str(backup) + "\n").encode():
                raise EffectiveKnownRefused("bound_stopped_found_install_outcome_uncertain")
        expected = (installed, before[1], before[2])
        if observe(record) != expected:
            raise EffectiveKnownRefused("bound_stopped_found_installed_tree_changed")

        # The original atomic shell copies the candidate. Sync the actual
        # installed and parked trees and their parent directories before
        # the original terminal WAL, then requalify every source and pin.
        def sync_path(path, directory=False):
            info = _stat(path, 0, directory=directory)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW |
                         (os.O_DIRECTORY if directory else 0))
            try:
                opened = os.fstat(fd)
                if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino):
                    raise EffectiveKnownRefused("bound_stopped_found_sync_inode_changed")
                os.fsync(fd)
            finally:
                os.close(fd)

        for tree in (active, backup):
            for root, dirs, names in os.walk(tree, topdown=False, followlinks=False):
                directory = Path(root)
                for name in names:
                    sync_path(directory / name)
                for name in dirs:
                    _stat(directory / name, 0, directory=True)
                sync_path(directory, directory=True)
        sync_path(backup_root, directory=True)
        sync_path(active.parent, directory=True)

        def terminal_witness(current):
            if observe(current) != expected:
                return False
            receipt = attest_bound_candidate_final_under_fd9(
                current, config_fd=config_fd, config_digest=digest,
                enabled=False, runtime_mode="0",
                retired_ready_sha256=before[2][0] if retired else None,
                expected_idle_producer=before[2][1] if retired else None,
                queue_fd=queue_fd)
            return (type(receipt) is FinalBoundRuntimeReceipt and
                    receipt.generation == detail["id"] and
                    receipt.root_sha256 == current["manifest"]["root_sha256"] and
                    receipt.config_sha256 == digest and
                    receipt.release_sha256 == new_hash and receipt.running is None and
                    receipt.epoch_sha256 is None and receipt.kernel_state == expected[1][0] and
                    receipt.retired_ready_sha256 == (
                        before[2][0] if retired else None) and
                    receipt.idle_producer == (
                        before[2][1] if retired else None) and
                    receipt.authorization == "NONE" and
                    receipt.physical_transition_allowed is False and
                    observe(current) == expected)

        result = {**record, "phase": "committed"}
        result.pop("found")
        result = store._persist_found_checkpoint(record, result, terminal_witness)
        if store.read() != result:
            raise EffectiveKnownRefused("bound_stopped_found_terminal_readback_changed")
        return {"result": "committed", "mode": "0"}


def advance_native_found_locked(action: str, operation: str, digest: str,
                                *, config_fd: int, queue_fd: int | None = None) -> dict:
    from auto_detect_destination_commit import (
        _attest_found_after_locked, _native_found_wal_context,
        _recover_found_preimages_locked, _bound_found_native_witness,
        _attest_bound_found_predecessor, _bound_found_queue_scope,
    )
    from shared_apply_operation import FOUND_RESTORING, FOUND_ROLLBACK_FROM
    from voice_live_inspect import examine_pending_found_previous

    store, record, raw, rows, targets, attest = _native_found_wal_context(
        operation, config_fd)
    detail = record["detail"]
    phase = record["phase"]
    if queue_fd is not None and (
            action not in ("recover-found-locked", "confirm-found-save-locked") or
            (phase != "prepared" and "manifest" not in record) or
            record.get("previous_manifest", {}).get("schema") != 2):
        raise EffectiveKnownRefused("bound_found_original_queue_scope_refused")
    if action == "recover-found-locked" and phase == "prepared":
        return recover_native_found_prepared_pristine(
            operation, config_fd=config_fd, config_digest=digest, queue_fd=queue_fd)
    with _bound_found_queue_scope(queue_fd) as queue, exclusive_destination_lock(AUTO_LOCK, store.owner):
        original_bound = _bound_found_native_witness(store, record, attest)
        bound_attest = None
        if original_bound is not None:
            if action not in ("recover-found-locked", "confirm-found-save-locked"):
                raise EffectiveKnownRefused("bound_found_runtime_witness_required")
            physical = _attest_bound_found_predecessor(record, config_fd, queue)

            def bound_attest(current):
                return (original_bound(current) and
                        _attest_bound_found_predecessor(current, config_fd, queue) == physical)

            store._attest_bound_found_checkpoint(record, bound_attest)
        if read_owned(OWNED_ROOT, owner_uid=store.owner) is None:
            raise EffectiveKnownRefused("found_source_owner_unavailable")
        if action == "recover-found-locked" and digest == detail["base"] and (
                phase in FOUND_ROLLBACK_FROM | {FOUND_RESTORING}):
            prior = examine_pending_found_previous(record)
            if prior["state"] not in ("ready", "stopped"):
                raise EffectiveKnownRefused("found_rollback_predecessor_unverified")
            result = _recover_found_preimages_locked(
                rows, targets, store=store, record=record, plan_bytes=raw, uid=store.owner,
                attest=lambda: attest() and examine_pending_found_previous(record) == prior,
                bound_attest=bound_attest)
            return {"result": result["phase"]}

        if digest != detail["candidate"]:
            raise EffectiveKnownRefused("found_candidate_config_not_saved")

        def after_images() -> bool:
            return attest() and _attest_found_after_locked(
                rows, targets, record, uid=store.owner)

        if action in ("confirm-found-save-locked", "recover-found-locked"):
            if phase == "found-config-saving":
                # A cold candidate-image match does NOT prove that OUR
                # Config::save returned, even with all three pinned HOSTLISTs.
                # Only the original in-flight PHP save/readback handoff may
                # durably confirm this phase. Preserve the uncertain WAL
                # without claiming success or triggering any runtime change.
                if action == "recover-found-locked":
                    raise EffectiveKnownRefused(
                        "found_config_save_candidate_uncertain_requires_review")
                # Config::save flushes but does not fsync the native Config
                # handle. The freshly loaded Model still describes these bytes.
                os.fsync(config_fd)
                record = store.advance_found_config(
                    "found-config-saved", detail, raw,
                    lambda next_phase, plan: after_images(),
                    bound_attest=bound_attest)
            elif (action != "recover-found-locked" or phase != "found-config-saved" or
                  not after_images()):
                raise EffectiveKnownRefused("found_recovery_phase_or_files_unknown")
            if bound_attest is not None and action == "recover-found-locked":
                # Never hand a saved bound transaction to the unbound
                # legacy executor. Its pending evidence remains intact.
                raise EffectiveKnownRefused("bound_found_runtime_witness_required")
            return {"result": record["phase"], "mode": record["found"]["runtime_mode"]}

        if bound_attest is not None:
            # File/Config reconciliation is not permission to invoke the
            # old unbound runtime route. The original bound runtime witness
            # is required before any of these phases may advance.
            raise EffectiveKnownRefused("bound_found_runtime_witness_required")
        next_phase = action.removeprefix("found-runtime-")
        if next_phase == "activating":
            prior = examine_pending_found_previous(record)
            if prior["state"] not in ("ready", "stopped"):
                raise EffectiveKnownRefused("found_runtime_predecessor_unverified")
        record = store.advance_found_runtime(next_phase, record, raw, after_images)
        return {"result": record["phase"]}


def recover_native_bound_found_locked(operation: str, digest: str, *,
                                       config_fd: int, queue_fd: int | None = None) -> dict:
    """One original locked Config image chooses forward or rollback.

    A saved/partially installed bound successor never reaches the legacy
    actuator. There is no fallback on a failed physical proof.
    """
    from auto_detect_destination_commit import _native_found_wal_context
    from shared_apply_operation import FOUND_ROLLBACK_FROM, FOUND_RESTORING
    store, record, _, _, _, attest = _native_found_wal_context(operation, config_fd)
    detail, phase = record["detail"], record["phase"]
    retired = record.get("previous_manifest", {}).get("schema") == 2
    if (record.get("manifest", {}).get("schema") != 1 or
            record.get("previous_manifest", {}).get("schema") not in (1, 2) or
            record["found"].get("runtime_mode") != "0" or
            retired != (queue_fd is not None) or
            not attest() or store.read() != record):
        raise EffectiveKnownRefused("bound_found_recovery_scope_refused")
    if (phase in ("found-config-saving", "found-config-saved") and
            digest == detail["candidate"] and
            (phase == "found-config-saved" or detail["base"] != digest)):
        return finish_native_bound_stopped_found_locked(
            operation, digest, config_fd=config_fd, queue_fd=queue_fd)
    if (phase in FOUND_ROLLBACK_FROM | {FOUND_RESTORING} and
            digest == detail["base"]):
        return advance_native_found_locked("recover-found-locked", operation,
            digest, config_fd=config_fd, queue_fd=queue_fd)
    raise EffectiveKnownRefused("bound_found_recovery_image_refused")


def native_bound_retired_found_save_original_fd9(operation: str) -> int:
    """Original FD9 borrowed P2a -> original PHP Config -> P1/Config.

    This private source-FIFO handoff has NO public Apply, Stop or activation
    authority. Before starting PHP, require a genuinely completed old
    schema2 retirement with exact immutable epoch ACK/archive and drained
    historical FDs. A partial/UNKNOWN owner leaves WAL/P1/Config untouched.
    The PHP child rechecks the same old owner and P2a open description
    before writing, then returns only a nonterminal Config-save receipt.
    """
    import pwd
    import stat
    import subprocess
    from auto_detect_owner import attest_learning_stopped_generation
    from auto_detect_learning_retirement import (
        retired_learning_stopped, RETIRE_DIR, READY)
    from auto_detect_epoch_receipts import EpochReceipts, _read
    from auto_detect_queue import DurableInbox
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from auto_detect_fd import _probe_original_inode
    from shared_apply_operation import (
        SharedApplyOperation, committed_manifest, committed_owner,
        restored_retired_found_owner)
    from shared_apply_seal import WORK, verify_seal
    from neutral_root_stage import verify_original_operation_pins
    from neutral_schema3_previous_physical import _full_prior_tree
    from neutral_schema3_quiescent_preimage import (
        _empty_kernel, _zero_processes, _verify_idle_producer,
        CHILD_PID, MONITOR_PID, DAEMON_PID)
    from voice_live_inspect import COMMON_ACTIVE
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not re.fullmatch(r"[a-f0-9]{32}", operation) or
            not stat.S_ISFIFO(os.fstat(0).st_mode)):
        raise EffectiveKnownRefused("bound_retired_original_fd9_fifo_required")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    old = committed_owner(record)
    pin = committed_manifest(record)
    restored = restored_retired_found_owner(record)
    if (type(record) is not dict or
            (record.get("phase") != "committed" and not restored) or
            type(pin) is not dict or pin.get("schema") != 2 or
            type(old) is not dict or operation in (old["id"], record["detail"]["id"]) or
            "found" in record or "failure" in record):
        raise EffectiveKnownRefused("bound_retired_terminal_schema2_required")
    verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
    candidate = WORK / operation
    sealed = verify_seal(candidate, owner=0)
    raw = (candidate / "plan.json").read_bytes()
    if (len(raw) > 4 * 1024 * 1024 or
            hashlib.sha256(raw).hexdigest() != sealed["sha256"]["plan.json"]):
        raise EffectiveKnownRefused("bound_retired_candidate_plan_changed")
    plan = json.loads(raw)
    if (type(plan) is not dict or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            plan.get("dependencies") != old["candidate"] or
            plan.get("candidate", {}).get("general", {}).get("enabled") != "0" or
            type(plan.get("found_intent")) is not dict or
            plan["found_intent"].get("commit_authorized") is not False or
            plan["found_intent"].get("config_revision") != old["candidate"] or
            type(plan.get("found_batch")) is not dict):
        raise EffectiveKnownRefused("bound_retired_found_candidate_required")
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    if gid <= 0:
        raise EffectiveKnownRefused("bound_retired_original_queue_gid_required")
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    receipts = EpochReceipts(owner_uid=0, writer_gid=gid)

    with queue.exclusive(existing_only=True):
        def attest():
            require_lifecycle_lock()
            if store.read() != record:
                raise EffectiveKnownRefused("bound_retired_owner_changed")
            return (attest_learning_stopped_generation(restored_record=record)
                    if restored else attest_learning_stopped_generation())

        def inspect(path, device, inode, *, owner, writer_gid):
            return _probe_original_inode(
                path, device, inode, owner=owner, writer_gid=writer_gid,
                attest_owner=lambda: attest().owner == owner)

        def snapshot():
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
            proof = attest()
            if (proof.operation_id != old["id"] or proof.generation != old["id"] or
                    proof.owner_candidate_sha256 != old["candidate"]):
                raise EffectiveKnownRefused("bound_retired_historical_owner_changed")
            ready = (receipts._generation(proof.generation, create=False) /
                     RETIRE_DIR / READY)
            ready_bytes = _read(ready, 0)
            if not retired_learning_stopped(
                    receipts, queue, proof, WORK / old["id"],
                    attest=attest, inspect=inspect, repair=False):
                raise EffectiveKnownRefused("bound_retired_ack_archive_incomplete")
            _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
            state = (_full_prior_tree(WORK / old["id"], COMMON_ACTIVE, 0),
                     _empty_kernel(WORK / old["id"] / "release"),
                     _verify_idle_producer(queue, receipts),
                     hashlib.sha256(ready_bytes).hexdigest())
            if _read(ready, 0) != ready_bytes or attest() != proof or store.read() != record:
                raise EffectiveKnownRefused("bound_retired_epoch_proof_changed")
            return state

        before = snapshot()
        if snapshot() != before or verify_seal(candidate, owner=0) != sealed:
            raise EffectiveKnownRefused("bound_retired_pre_php_proof_changed")
        # Original parent owns FD9 + P2a first; PHP gets FD3 inherited by
        # open-description, acquires native Config FD4 only afterwards and
        # transfers the exact original source FIFO as FD5 to the existing
        # save/confirm child. No timeout/kill: parent keeps P2a until join.
        command = (
            "/usr/local/bin/php",
            "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php",
            "found-bound-save", operation, "strategies", "0",
            "--queue-fd=" + str(queue.locked_fd))
        result = subprocess.run(
            command, stdin=sys.stdin.buffer, stdout=subprocess.PIPE,
            pass_fds=(9, queue.locked_fd), check=False, close_fds=True)
        if result.returncode not in (0, 64, 69, 70) or len(result.stdout) > 16384:
            return 70
        if result.stdout:
            sys.stdout.buffer.write(result.stdout)
            sys.stdout.buffer.flush()
        return result.returncode


def native_bound_retired_found_finish_original_fd9(operation: str) -> int:
    """Retired-old bound finalizer: same original FD9 and P2a -> PHP FD4.

    The original saved WAL/Config/P1 is the ONLY promotion intent. Never
    synthesize old Active from a PID, launch an engine, or guess a missing
    archive/ACK. PHP and its original physical finisher join before P2a
    is released, even when no terminal receipt can be accepted.
    """
    import pwd
    import subprocess
    from auto_detect_queue import DurableInbox
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from shared_apply_operation import SharedApplyOperation
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not re.fullmatch(r"[a-f0-9]{32}", operation)):
        raise EffectiveKnownRefused("bound_retired_finish_original_fd9_required")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if (type(record) is not dict or
            record.get("phase") not in ("found-config-saving", "found-config-saved") or
            record.get("detail", {}).get("id") != operation or
            record.get("previous_manifest", {}).get("schema") != 2 or
            record.get("manifest", {}).get("schema") != 1 or
            "found" not in record):
        raise EffectiveKnownRefused("bound_retired_finish_original_wal_required")
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    if gid <= 0:
        raise EffectiveKnownRefused("bound_retired_finish_original_queue_gid_required")
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    with queue.exclusive(existing_only=True):
        if store.read() != record:
            raise EffectiveKnownRefused("bound_retired_finish_owner_changed")
        result = subprocess.run(
            ("/usr/local/bin/php",
             "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php",
             "found-bound-finish", operation, "strategies",
             "--queue-fd=" + str(queue.locked_fd)),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            pass_fds=(9, queue.locked_fd), check=False, close_fds=True)
        if result.returncode not in (0, 64, 69, 70) or len(result.stdout) > 16384:
            return 70
        if result.stdout:
            sys.stdout.buffer.write(result.stdout)
            sys.stdout.buffer.flush()
        return result.returncode


def native_found_recover_original_fd9(operation: str) -> int:
    """One existing PHP Config recovery, with P2a BEFORE Config when required."""
    import pwd
    import subprocess
    from auto_detect_queue import DurableInbox
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from shared_apply_operation import SharedApplyOperation, FOUND_ROLLBACK_FROM, FOUND_RESTORING
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not re.fullmatch(r"[a-f0-9]{32}", operation)):
        raise EffectiveKnownRefused("native_found_recovery_fd9_required")
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if (type(record) is not dict or "found" not in record or
            record["detail"]["id"] != operation or record["detail"]["page"] != "strategies"):
        raise EffectiveKnownRefused("native_found_recovery_owner_required")
    bound = record.get("manifest", {}).get("schema") == 1 and (
        record.get("previous_manifest", {}).get("schema") in (1, 2))
    retired = record.get("previous_manifest", {}).get("schema") == 2
    # A PREPARED record may precede candidate root binding; the original
    # locked pristine verifier proves the old epoch and all three preimages.
    if retired and not bound and (record["phase"] != "prepared" or "manifest" in record):
        raise EffectiveKnownRefused("bound_retired_found_recovery_pin_refused")
    command = ["/usr/local/bin/php",
               "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php",
               "found-bound-recover" if bound and record["phase"] != "prepared" else "found-recover",
               operation, "strategies"]

    def invoke(fd=None):
        require_lifecycle_lock()
        if store.read() != record:
            raise EffectiveKnownRefused("native_found_recovery_owner_changed")
        args = command if fd is None else command + ["--queue-fd=" + str(fd)]
        result = subprocess.run(args, stdin=subprocess.DEVNULL,
                                pass_fds=(9,) if fd is None else (fd, 9),
                                check=False, close_fds=True)
        return result.returncode if result.returncode in (0, 64, 69, 70) else 70

    if retired:
        if record["phase"] not in FOUND_ROLLBACK_FROM | {FOUND_RESTORING, "found-config-saved", "prepared"}:
            raise EffectiveKnownRefused("bound_retired_found_recovery_phase_refused")
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise EffectiveKnownRefused("native_found_recovery_queue_gid_unqualified")
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
        with queue.exclusive(existing_only=True):
            return invoke(queue.locked_fd)
    return invoke()


def _managed_refusal_trace(error: BaseException) -> None:
    """Report bounded source locations only, including suppressed exception context."""
    modules = {
        "neutral_shared_apply_source_gate": "M01",
        "neutral_schema3_previous_physical": "M02",
        "auto_detect_destination_commit": "M03",
        "shared_apply_operation": "M04",
        "auto_detect_original_lock_handoff": "M05",
        "voice_ipfw_adapter": "M06",
        "voice_firewall_transaction": "M07",
        "auto_detect_owner": "M08",
        "neutral_root_stage": "M09",
        "shared_apply_seal": "M10",
        "neutral_schema3_quiescent_preimage": "M11",
        "auto_detect_owned_sources": "M12",
        "auto_detect_minute": "M13",
        "extra_resources_upstream_guard": "M14",
    }
    seen = set()
    emitted = set()
    try:
        while error is not None and id(error) not in seen and len(seen) < 8:
            seen.add(id(error))
            tb = error.__traceback__
            for _ in range(128):
                if tb is None:
                    break
                module = modules.get(tb.tb_frame.f_globals.get("__name__"))
                line = tb.tb_lineno
                if module is not None and 0 < line <= 99999 and (module, line) not in emitted:
                    print(f"S10_MANAGED_TRACE={module}:{line}", file=sys.stderr, flush=True)
                    emitted.add((module, line))
                    if len(emitted) >= 32:
                        return
                tb = tb.tb_next
            # A deliberate 'raise ... from None' must not hide the source
            # location from this private diagnostic; never print its text.
            error = error.__cause__ or error.__context__
    except (OSError, ValueError, TypeError):
        pass


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "bound-retired-finish-original":
        try:
            return native_bound_retired_found_finish_original_fd9(argv[1])
        except (ValueError, RuntimeError, OSError, UnicodeError, KeyError,
                TypeError, AttributeError):
            print("ERROR: original bound retired Found finish scope refused",
                  file=sys.stderr)
            return 69
    if len(argv) == 2 and argv[0] == "bound-retired-save-original":
        try:
            return native_bound_retired_found_save_original_fd9(argv[1])
        except (ValueError, RuntimeError, OSError, UnicodeError, KeyError,
                TypeError, AttributeError):
            print("ERROR: original bound retired Found save scope refused",
                  file=sys.stderr)
            return 69
    if len(argv) == 2 and argv[0] == "recover-found-original":
        try:
            return native_found_recover_original_fd9(argv[1])
        except (ValueError, RuntimeError, OSError, UnicodeError, KeyError):
            print("ERROR: original Found recovery scope refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "attest-ordinary-save-locked":
        if len(argv) != 3:
            return 64
        try:
            from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
            from shared_apply_operation import SharedApplyOperation, SharedOperationError
            from shared_apply_seal import WORK
            from voice_ipfw_adapter import require_lifecycle_lock

            if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
                raise SharedOperationError("native ordinary Config save required")
            require_lifecycle_lock()
            assert_inherited_config_fd(4, CONFIG_PATH, owner_uid=None)
            SharedApplyOperation(owner=0).attest_unbound_config_save(
                argv[1], argv[2], shared_work_parent=WORK)
            assert_inherited_config_fd(4, CONFIG_PATH, owner_uid=None)
            require_lifecycle_lock()
            print(json.dumps({"result": "original-ordinary-save-verified", "id": argv[1]}))
            return 0
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            print("ERROR: original ordinary locked Config save refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "write-managed-handoff-locked":
        if len(argv) != 3:
            return 64
        try:
            from neutral_shared_apply_source_gate import native_write_managed_handoff_locked
            record = native_write_managed_handoff_locked(
                argv[1], argv[2], sys.stdin.buffer, config_fd=4)
            print(json.dumps({"result": record["phase"], "id": record["detail"]["id"]},
                             separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            _managed_refusal_trace(error)
            print("ERROR: original managed locked write outcome refused", file=sys.stderr)
            return 69
    if argv and argv[0] in ("begin-managed-config-save-locked", "confirm-managed-config-save-locked"):
        if len(argv) != 3:
            return 64
        saved = argv[0] == "confirm-managed-config-save-locked"
        try:
            from neutral_shared_apply_source_gate import native_checkpoint_managed_config_fd9

            record = native_checkpoint_managed_config_fd9(argv[1], argv[2], config_fd=4, saved=saved)
            print(json.dumps({"result": record["phase"], "id": record["detail"]["id"]},
                             separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            _managed_refusal_trace(error)
            print("ERROR: original managed locked Config phase refused", file=sys.stderr)
            return 69
    if argv and argv[0] in ("guard-first-running-base-shell", "guard-first-running-base-stopped"):
        if len(argv) not in (3, 4) or (len(argv) == 4 and argv[3] != "--inherited-queue"):
            return 64
        try:
            from neutral_schema3_quiescent_preimage import (
                native_guard_first_running_base_shell_locked,
                native_guard_first_running_base_stopped_shell_locked)
            if argv[0] == "guard-first-running-base-shell":
                pid, monitor = native_guard_first_running_base_shell_locked(
                    argv[1], argv[2], config_fd=4,
                    queue_fd=3 if len(argv) == 4 else None)
                print(f"first-running-base-shell=qualified:{pid}:{monitor}")
            else:
                native_guard_first_running_base_stopped_shell_locked(
                    argv[1], argv[2], config_fd=4,
                    queue_fd=3 if len(argv) == 4 else None)
                print("first-running-base-stopped=qualified")
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
            print("ERROR: original first running base guard refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "guard-first-enabled-shell":
        if len(argv) not in (4, 5) or (len(argv) == 5 and argv[4] != "--inherited-queue"):
            return 64
        try:
            from neutral_schema3_quiescent_preimage import native_guard_first_enabled_shell_locked
            native_guard_first_enabled_shell_locked(argv[1], argv[2], argv[3], config_fd=4,
                queue_fd=3 if len(argv) == 5 else None)
            print("first-enabled-shell=qualified")
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
            print("ERROR: original first enabled shell guard refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "write-first-enabled-handoff-locked":
        if len(argv) not in (3, 4) or (len(argv) == 4 and argv[3] != "--inherited-queue"):
            return 64
        try:
            from neutral_schema3_quiescent_preimage import native_write_first_enabled_handoff_locked
            reply = native_write_first_enabled_handoff_locked(
                argv[1], argv[2], sys.stdin.buffer, config_fd=4,
                queue_fd=3 if len(argv) == 4 else None)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
            print("ERROR: original first enabled handoff refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "write-first-disabled-handoff-locked":
        if len(argv) != 3:
            return 64
        try:
            from neutral_schema3_quiescent_preimage import native_write_first_disabled_handoff_locked
            reply = native_write_first_disabled_handoff_locked(
                argv[1], argv[2], sys.stdin.buffer, config_fd=4)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
            print("ERROR: original first disabled handoff refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "recover-first-config-locked":
        if len(argv) not in (3, 4) or (len(argv) == 4 and argv[3] != "--inherited-queue"):
            return 64
        try:
            from neutral_schema3_quiescent_preimage import finish_first_config_recovery_locked
            reply = finish_first_config_recovery_locked(argv[1], argv[2], config_fd=4,
                queue_fd=3 if len(argv) == 4 else None)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
            print("ERROR: original first Config recovery refused", file=sys.stderr)
            return 69
    if argv and argv[0] in ("finish-ordinary-restore-locked", "recover-managed-config-locked"):
        if len(argv) not in (3, 4) or (len(argv) == 4 and argv[3] != "--inherited-queue"):
            return 64
        try:
            from neutral_schema3_quiescent_preimage import (
                finish_bound_cold_restore_locked, finish_managed_config_recovery_locked,
            )
            finish = (finish_managed_config_recovery_locked if argv[0] == "recover-managed-config-locked"
                      else finish_bound_cold_restore_locked)
            reply = finish(
                argv[1], argv[2], config_fd=4, queue_fd=3 if len(argv) == 4 else None)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            if argv[0] == "recover-managed-config-locked":
                _managed_refusal_trace(error)
            print("ERROR: original ordinary locked cold restore refused", file=sys.stderr)
            return 69
    if argv and argv[0] in ("begin-found-save-locked", "begin-bound-found-save-locked"):
        bound = argv[0] == "begin-bound-found-save-locked"
        inherited_queue = (bound and len(argv) == 6 and
                           argv[5] == "--inherited-queue")
        if (len(argv) != (6 if inherited_queue else 5) or
                argv[3] not in ("0", "1") or
                (bound and argv[3] != "0") or
                not re.fullmatch(r"[a-f0-9]{64}", argv[4])):
            return 64
        if len(argv) == 6 and not inherited_queue:
            return 64
        try:
            from auto_detect_destination_commit import shared_apply_found_files_original_fd9

            def wait_for_save():
                # stdout signals that the before-save WAL is durable.
                # The original PHP parent releases stdin after Config::save,
                # including on failure. EOF also releases P2 after parent death.
                print("ready", flush=True)
                sys.stdin.buffer.read(1)

            if bound:
                # Exact original locked transport only. A schema2 retired
                # owner REQUIRES inherited P2a; schema1 forbids it.
                # Never infer an epoch/ACK from matching Config bytes.
                from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
                from shared_apply_operation import SharedApplyOperation, committed_manifest
                from voice_ipfw_adapter import require_lifecycle_lock
                if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
                    raise EffectiveKnownRefused("bound_found_native_owner_required")
                require_lifecycle_lock()
                assert_inherited_config_fd(4, CONFIG_PATH, owner_uid=None)
                pin = committed_manifest(SharedApplyOperation(owner=0).read())
                if (type(pin) is not dict or
                        pin.get("schema") not in (1, 2) or
                        (pin["schema"] == 2) != inherited_queue):
                    raise EffectiveKnownRefused("bound_found_queue_schema_required")
                begin_native_bound_found_save_locked(
                    argv[1], 4, argv[2], runtime_mode=argv[3], base_digest=argv[4],
                    source_fd=5, before_save=wait_for_save,
                    queue_fd=3 if inherited_queue else None)
            else:
                prepare_native_found_intent(
                    argv[1], 4, argv[2], runtime_mode=argv[3], base_digest=argv[4])
                shared_apply_found_files_original_fd9(argv[1], 4, before_save=wait_for_save)
            return 0
        except (ValueError, RuntimeError, OSError, UnicodeError):
            print("ERROR: original found-data save scope refused", file=sys.stderr)
            return 69
    finish_queue = (len(argv) == 4 and argv[3] == "--inherited-queue")
    if argv and argv[0] == "recover-bound-found-locked" and (
            len(argv) == 3 or (len(argv) == 4 and argv[3] == "--inherited-queue")):
        try:
            reply = recover_native_bound_found_locked(
                argv[1], argv[2], config_fd=4,
                queue_fd=3 if len(argv) == 4 else None)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, UnicodeError, KeyError, TypeError):
            print("ERROR: original bound Found recovery refused", file=sys.stderr)
            return 69
    if argv and argv[0] == "finish-bound-found-locked" and (
            len(argv) == 3 or finish_queue):
        try:
            reply = finish_native_bound_stopped_found_locked(
                argv[1], argv[2], config_fd=4,
                queue_fd=3 if finish_queue else None)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, UnicodeError):
            print("ERROR: original bound stopped Found finish refused", file=sys.stderr)
            return 69
    inherited_queue = (len(argv) == 4 and argv[3] == "--inherited-queue" and
                       argv[0] in ("recover-found-locked", "confirm-found-save-locked"))
    if inherited_queue or (len(argv) == 3 and argv[0] in (
            "recover-found-locked", "confirm-found-save-locked",
            "found-runtime-activating", "found-runtime-activated",
            "found-runtime-config-saved", "found-runtime-epoch-finalizing",
            "found-runtime-committed")):
        try:
            reply = advance_native_found_locked(
                argv[0], argv[1], argv[2], config_fd=4,
                queue_fd=3 if inherited_queue else None)
            print(json.dumps(reply, separators=(",", ":")))
            return 0
        except (ValueError, RuntimeError, OSError, UnicodeError):
            print("ERROR: original found Apply phase refused", file=sys.stderr)
            return 69
    if len(argv) == 3 and argv[0] == 'recover-prepared-locked':
        try:
            # Authenticated by ORIGINAL FD9 + actual inherited Config fd4,
            # not an alternate owner or independently reopened config file.
            # This is private to original PHP's root Config-lock command.
            receipt = recover_native_found_prepared_pristine(
                argv[1], config_fd=4, config_digest=argv[2])
            print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
            return 0
        except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
                DomainPolicyError, AutoDomainPolicyError,
                ValueError, RuntimeError, OSError, UnicodeError):
            print('ERROR: original PREPARED pristine native recovery refused',
                  file=sys.stderr)
            return 69
    if len(argv) == 2 and argv[0] == 'classify-locked':
        try:
            # fd4 is the original OPNsense Config::lock open description
            # explicitly inherited from the existing PHP Config owner;
            # fd9 is the SAME lifecycle lock, never a guessed new owner.
            evidence = classify_native_planned(argv[1], config_fd=4)
            print(json.dumps({
                "schema": 1, "result": evidence["result"],
                "journal_phase": evidence["journal_phase"],
                "image": evidence["image"], "states": evidence["states"],
                "stage_evidence": evidence.get("stage_evidence"),
                "previous_runtime": evidence["previous_runtime"],
                "commit_authorized": False, "restore_authorized": False,
            }, sort_keys=True, separators=(",", ":")))
            return 0
        except (EffectiveKnownRefused, OwnedSourcesRefused, DestinationRefused,
                DomainPolicyError, AutoDomainPolicyError,
                ValueError, RuntimeError, OSError, UnicodeError):
            print('ERROR: original locked Config+FD9+P2 cold image unavailable',
                  file=sys.stderr)
            return 69
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
