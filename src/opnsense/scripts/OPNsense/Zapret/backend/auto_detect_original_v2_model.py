#!/usr/bin/env python3
"""#1052 P2k8p: one original Config-held P1 -> v2 destination transaction.

The original PHP OPNsense Model/Config::lock and inherited original queue
open-file description are the only authorities. The native debug observer
has UNKNOWN known-hostlist attribution, so its fresh roots go only to the
explicit shared auto-domains.txt. Existing sealed auto-owned known-list
rows may be relocated using the SINGLE canonical P1 domain policy.
No Config writer, second queue, legacy v1 journal, standalone worker or ACK.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Callable

from auto_detect_cursor_chain import (CursorChain, CursorChainRefused,
                                      _checkpoint, _evidence_unchanged,
                                      _completed_debug_evidence_unchanged)
from auto_detect_debug_window import ADD, MAX_RAW, MAX_WINDOW, _raw_hosts, _read_exact, _hostname
from auto_detect_destination_commit import (DestinationCommit, DestinationRefused,
                                            _edit, _target, qualified_destination_plan)
from auto_detect_epoch_receipts import ReceiptRefused, _read
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_v2_source import (qualified_current_source,
                                            detached_original_raw, OriginalSourceRefused)
from auto_detect_owner import GenerationProof, attest_running_generation
from auto_detect_owned_sources import (KNOWN_HOSTLISTS, OwnedSourcesRefused,
                                       read_owned)
from domain_policy import (AutoDomainPolicyError, DomainPolicyError,
                           PublicSuffixList, normalize, plan_auto_additions)
from auto_detect_effective_known import (EffectiveKnownRefused, compose_known,
                                         preview_live_known_after_readonly)
from voice_live_inspect import COMMON_ACTIVE

MAX_MODEL_TEXT = 4 * 1024 * 1024
MAX_EXCLUDE_TEXT = 1 << 20


class V2OriginalConfigRefused(RuntimeError):
    """Preserve original pending and GUI-edited target files on uncertainty."""


def _domains(proof: GenerationProof, intent: dict, raw: bytes, *,
             owner_uid: int, writer_gid: int | None) -> list[dict]:
    """Recheck exactly the protected native P2k1 event subwindow after append.

    Later native debug events may have been appended to the same inode;
    never accidentally consume them for a preceding immutable intent.
    """
    if intent["evidence"] == "raw-first":
        # The original P2a pending inode and SHA, live P2c/FD9 identity,
        # all-PID P2b drain and Config-held CAS are the provenance.
        # Diagnostic debug cannot invent known HOSTLIST attribution.
        if not _evidence_unchanged(proof, intent, owner_uid, writer_gid):
            raise V2OriginalConfigRefused("raw_first_source_not_attested")
        hosts = _raw_hosts(raw)
        if len(hosts) != intent["candidate_count"]:
            raise V2OriginalConfigRefused("raw_first_candidate_count_changed")
        return [{"hostname": host, "hostlist": None} for host in hosts]
    if intent["evidence"] != "native-debug":
        raise V2OriginalConfigRefused("unqualified_original_observation_mode")
    info, data = _read_exact(Path(proof.debug_path), owner_uid=owner_uid,
                             writer_gid=writer_gid)
    start, end = intent["debug_start_offset"], intent["debug_end_offset"]
    if (info.st_dev != intent["debug_device"] or
            info.st_ino != intent["debug_inode"] or
            type(start) is not int or type(end) is not int or
            start < 0 or end <= start or end > len(data) or
            hashlib.sha256(data[:start]).hexdigest() != intent["debug_start_sha256"] or
            hashlib.sha256(data[:end]).hexdigest() != intent["debug_end_sha256"]):
        raise V2OriginalConfigRefused("v2_native_debug_prefix_changed")
    segment = data[start:end]
    if not segment.endswith(b"\n") or b"\x00" in segment or b"\r" in segment:
        raise V2OriginalConfigRefused("v2_native_debug_segment_invalid")
    if (not raw or not raw.endswith(b"\n") or b"\x00" in raw or b"\r" in raw):
        raise V2OriginalConfigRefused("v2_original_raw_incomplete")
    try:
        hosts = [name.decode("ascii") for name in raw.split(b"\n")[:-1]]
        candidates: list[str] = []
        for line in segment.splitlines():
            decoded = line.decode("ascii")
            if " : adding to " in decoded:
                event = ADD.fullmatch(decoded)
                if (event is None or event["path"] != proof.raw_path or
                        int(event["profile"]) != proof.observer_native_number or
                        not _hostname(event["host"])):
                    raise V2OriginalConfigRefused("v2_native_unqualified_positive")
                candidates.append(event["host"])
    except UnicodeError as exc:
        raise V2OriginalConfigRefused("v2_native_debug_not_ascii") from exc
    if (len(candidates) != intent["candidate_count"] or
            candidates != hosts or not candidates):
        raise V2OriginalConfigRefused("v2_native_raw_debug_not_one_to_one")
    # The genuine trailing native observer has no known HOSTLIST selector.
    # Never guess YouTube/User by spelling or earlier native profile numbers.
    return [{"hostname": host, "hostlist": None} for host in candidates]



# ТЗ_6v4 / #1052: one existing P2 model's candidate decoder, not a writer.
# Its caller must first pin physical native file ranges through original
# FD9/epoch/P2b and must not advance ANY cursor merely from this preview.
def preview_learning_domains(map_raw: bytes, owner: dict, original: bytes,
                             argv: bytes, native_rows: dict[str, bytes],
                             debug_window: bytes) -> list[dict[str, str]]:
    """Map exact native append windows to the already-existing P1 format.

    Each native_rows value must be the unread, independently attested byte
    window for ONE live --hostlist-auto file, not the full historical file.
    Debug lines alone do not establish a native append. Conversely, raw
    rows cannot gain known HOSTLIST attribution without this strict positive
    debug pairing. On uncertainty the outer original P2 must retain source
    bytes, cursor and pending/ACK state and retry or use its *separately
    qualified* raw-first path. This function performs NO filesystem, Config,
    service, cursor, inode or network writes.
    """
    from auto_detect_owner import GenerationRefused, _valid_learning_proposal

    try:
        approved = _valid_learning_proposal(map_raw, owner, original, argv)
    except (GenerationRefused, ValueError, TypeError, KeyError) as exc:
        raise V2OriginalConfigRefused("unqualified_learning_native_map") from exc
    if (not approved or type(native_rows) is not dict or
            set(native_rows) != {path for _, _, path in approved} or
            type(debug_window) is not bytes or
            len(debug_window) > MAX_WINDOW or
            (debug_window and not debug_window.endswith(b"\\n")) or
            b"\\x00" in debug_window or b"\\r" in debug_window):
        raise V2OriginalConfigRefused("unqualified_learning_native_window")

    known_by_path = {path: (number, hostlist) for number, hostlist, path in approved}
    raw_by_path: dict[str, list[str]] = {}
    total = len(debug_window)
    for path, segment in native_rows.items():
        if type(segment) is not bytes or len(segment) > MAX_RAW:
            raise V2OriginalConfigRefused("unbounded_learning_native_raw")
        total += len(segment)
        if total > MAX_RAW:
            raise V2OriginalConfigRefused("oversized_combined_learning_window")
        try:
            raw_by_path[path] = _raw_hosts(segment) if segment else []
        except (ValueError, TypeError) as exc:
            raise V2OriginalConfigRefused("invalid_learning_native_raw") from exc

    paired: dict[str, list[str]] = {path: [] for path in known_by_path}
    observations: list[dict[str, str]] = []
    for line in debug_window.splitlines(keepends=True):
        if not line.endswith(b"\\n"):
            raise V2OriginalConfigRefused("incomplete_learning_debug_line")
        try:
            decoded = line[:-1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise V2OriginalConfigRefused("untrusted_learning_debug_encoding") from exc
        if " : adding to " not in decoded:
            continue
        event = ADD.fullmatch(decoded)
        if event is None:
            raise V2OriginalConfigRefused("invalid_learning_native_debug_event")
        path = event["path"]
        identity = known_by_path.get(path)
        if identity is None or int(event["profile"]) != identity[0]:
            raise V2OriginalConfigRefused("foreign_learning_profile_or_path")
        host = event["host"]
        if not _hostname(host):
            raise V2OriginalConfigRefused("invalid_learning_positive_host")
        paired[path].append(host)
        if len(paired[path]) > len(raw_by_path[path]) or (
                paired[path][-1] != raw_by_path[path][len(paired[path]) - 1]):
            # A debug positive emitted before the native write cannot
            # advance the source; a different or reordered row cannot
            # borrow provenance from another profile.
            raise V2OriginalConfigRefused("learning_positive_without_matching_raw")
        observations.append({"hostname": host, "hostlist": identity[1]})

    if any(paired[path] != rows for path, rows in raw_by_path.items()):
        raise V2OriginalConfigRefused("learning_raw_without_exact_debug_evidence")
    return observations



def _validate_partial_plan(folder: Path, writer: DestinationCommit,
                           effects: dict, eligible: set[str]) -> None:
    """Original P2k8d fail-closed interrupted physical plan replay.

    A checkpoint is handled separately: later GUI deletions must never be
    undone. Before checkpoint, an already-written destination may only be
    completed when every previous change is still allowed by current P1.
    """
    plan_path = folder / "destination" / "plan.json"
    checkpoint_path = folder / "destination" / "checkpoint.json"
    if not plan_path.exists() and not plan_path.is_symlink():
        return
    if checkpoint_path.exists() or checkpoint_path.is_symlink():
        return
    plan = json.loads(_read(plan_path, writer.receipts.uid))
    writes = plan.get("writes") if isinstance(plan, dict) else None
    if not isinstance(writes, dict) or set(writes) - set(writer.targets):
        raise V2OriginalConfigRefused("unknown_original_partial_target_plan")
    # A saved partial plan is the exact original transaction. Current P1
    # may naturally see fewer effects after the first physical targets were
    # written; it must NEVER introduce an unplanned new target/effect and
    # then ACK the raw as if those new effects had been durably handled.
    for name, current in effects.items():
        saved = writes.get(name, {"add": [], "remove": []})
        if (not isinstance(saved, dict) or
                any(item not in saved.get(field, [])
                    for field in ("add", "remove") for item in current[field])):
            raise V2OriginalConfigRefused("new_effects_outside_original_partial_plan")
    for name, change in writes.items():
        if (not isinstance(change, dict) or
                type(change.get("add")) is not list or
                type(change.get("remove")) is not list):
            raise V2OriginalConfigRefused("invalid_original_partial_effect")
        old_add, old_remove = change["add"], change["remove"]
        if ((name == "auto" and old_remove) or
                (name != "auto" and old_add) or
                any(type(x) is not str or x not in eligible
                    for x in old_add + old_remove)):
            raise V2OriginalConfigRefused("previous_unqualified_original_effect")
        physical, _ = _target(writer.targets[name], writer.receipts.uid)
        lines = set(physical.decode("utf-8").splitlines())
        if name == "auto" and any(
                x not in effects.get("auto", {}).get("add", []) and
                x not in lines for x in old_add):
            raise V2OriginalConfigRefused("old_auto_addition_no_longer_allowed")
        if name != "auto" and any(
                x not in effects.get(name, {}).get("remove", []) and
                x in lines for x in old_remove):
            raise V2OriginalConfigRefused("old_known_removal_no_longer_allowed")


def _original_live_known_after_locked(
    folder: Path, intent: dict, writer: DestinationCommit,
    manual: dict[str, str], owned: dict[str, str],
    effects: dict, proof: GenerationProof, attest: Callable,
) -> dict | None:
    """Original RUNNING P2 → same slot's managed CAS; no second writer.

    Called ONLY under original queue -> Config -> GUI destination locks.
    At first preparation the existing read-only PID/birth/argv witness proves
    the active files match current Config + protected owned before-images.
    After a partial source/managed crash, replay instead reads the immutable
    original slot WAL; never infer a prior managed inode from a changed source.
    """
    if not writer.queue._held or not writer._gui_held or attest() != proof:
        raise V2OriginalConfigRefused("original_live_owner_locks_required")
    registered = ("youtube", "user")
    canonical = {}
    for name in registered:
        normalized = normalize(manual[name], name)["normalized"]
        canonical[name] = normalized + (chr(10) if normalized else "")

    plan_path = folder / "destination" / "plan.json"
    old_plan = None
    if plan_path.exists() or plan_path.is_symlink():
        old_plan, _ = qualified_destination_plan(
            folder, intent, writer.receipts.uid, targets=writer.targets)
        # Never silently "upgrade" an already physically partial old source
        # WAL into unpinned live writes. Source-only AUTO slots remain valid.
        if "live" not in old_plan:
            if set(old_plan["writes"]) & set(registered):
                raise V2OriginalConfigRefused("unsealed_original_live_preimage")
            return None
        decisions = {
            name: old_plan["writes"].get(name, {"add": [], "remove": []})
            for name in registered
        }
    else:
        if not set(effects) & set(registered):
            return None
        decisions = {
            name: effects.get(name, {"add": [], "remove": []})
            for name in registered
        }

    # The P1-owned source may already be AFTER following a partial crash.
    # _edit is idempotent for its original add/remove effects; a foreign
    # rewrite is separately rejected by the old destination plan's CAS.
    after_owned = {
        name: _edit(owned[name].encode("utf-8"),
                    decisions[name]["add"], decisions[name]["remove"]).decode("utf-8")
        for name in registered
    }
    expected = compose_known(canonical, after_owned)
    if old_plan is None:
        preview = preview_live_known_after_readonly(
            canonical, effects, active=COMMON_ACTIVE,
            owned_root=writer.targets["youtube"].parent,
            owner_uid=writer.receipts.uid, attest=attest)
        if (preview["status"] != "read-only-live-after-images" or
                preview["operation"] != proof.operation_id or
                preview["generation"] != proof.generation or
                preview["pid"] != proof.owner.pid or
                preview["started"] != proof.owner.started or
                preview["commit_authorized"] is not False or
                preview["ack_authorized"] is not False):
            raise V2OriginalConfigRefused("live_original_preview_owner_mismatch")
        live = {}
        for name in preview["changed"]:
            row = preview["files"][name]
            path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
            if (row["path"] != str(path) or
                    row["after_sha256"] != hashlib.sha256(
                        expected[name].encode("utf-8")).hexdigest()):
                raise V2OriginalConfigRefused("live_original_expected_after_drift")
            live[name] = {
                "path": path,
                "before_sha256": row["before_sha256"],
                "after": expected[name].encode("utf-8"),
            }
    else:
        live = {}
        for name, row in old_plan["live"].items():
            path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
            new_bytes = expected[name].encode("utf-8")
            if (row["path"] != str(path) or
                    row["after"] != hashlib.sha256(new_bytes).hexdigest()):
                raise V2OriginalConfigRefused("live_original_replay_conflict")
            live[name] = {
                "path": path, "before_sha256": row["before"],
                "after": new_bytes,
            }
    if attest() != proof:
        raise V2OriginalConfigRefused("live_original_owner_changed_before_cas")
    return live


def commit_with_original_v2_model(
    writer: DestinationCommit, pending: Path, *,
    owned_root: Path, manual_hostlists: dict[str, str], global_exclude: str,
    attest: Callable = attest_running_generation,
    inspect: Callable = probe_pending_fd,
    psl: PublicSuffixList | None = None,
    running_live: bool = False,
) -> dict:
    """Only the original PHP Config-locked child may call this in product.

    A test may inject process/FD/PSL witnesses, but the real fixed native
    entry additionally requires inherited BOTH original queue and Config
    file-lock open descriptions. The method itself NEVER permits ACK.
    """
    if (not isinstance(writer, DestinationCommit) or
            not writer.queue._held or
            not isinstance(pending, Path) or
            pending.parent != writer.queue.pending or
            type(global_exclude) is not str or
            len(global_exclude.encode("utf-8")) > MAX_EXCLUDE_TEXT or
            not isinstance(manual_hostlists, dict) or
            set(manual_hostlists) != set(KNOWN_HOSTLISTS) or
            any(type(value) is not str or
                len(value.encode("utf-8")) > MAX_MODEL_TEXT
                for value in manual_hostlists.values()) or
            not callable(attest) or not callable(inspect) or
            type(running_live) is not bool):
        raise V2OriginalConfigRefused("original_config_model_and_queue_required")
    try:
        root = Path(owned_root)
        expected = {"auto", *KNOWN_HOSTLISTS}
        if (not root.is_absolute() or set(writer.targets) != expected or
                writer.targets["auto"].parent == root or
                any(writer.targets[key] != root / (key + ".txt")
                    for key in KNOWN_HOSTLISTS)):
            raise V2OriginalConfigRefused("original_known_owned_targets_not_exact")
        proof = qualified_current_source(attest(), writer.queue)
        chain = CursorChain(writer.receipts, writer.queue)
        tip = chain.tip(proof)
        intent = tip.open_intent
        folder = tip.open_folder
        if (intent is None or folder is None or
                intent["pending_name"] != pending.name or
                pending not in writer.queue.segments()):
            raise V2OriginalConfigRefused("original_v2_uncommitted_slot_required")
        original = pending.lstat()
        if (inspect(pending, original.st_dev, original.st_ino, owner=proof.owner,
                    writer_gid=writer.queue.writer_gid) is not FDState.DRAINED or
                attest() != proof):
            raise V2OriginalConfigRefused("original_p2b_writer_not_drained")
        raw = detached_original_raw(writer.queue, pending)
        if ((original.st_dev, original.st_ino, len(raw),
             hashlib.sha256(raw).hexdigest()) !=
                (intent["pending_device"], intent["pending_inode"],
                 intent["pending_size"], intent["pending_sha256"])):
            raise V2OriginalConfigRefused("original_raw_not_prepared_v2")
        with writer.exclusive_targets():
            owned = read_owned(root, owner_uid=writer.receipts.uid)
            if owned is None or set(owned) != set(KNOWN_HOSTLISTS):
                raise V2OriginalConfigRefused("unsealed_known_owned_baseline")
            # Checkpoint already exists: genuine P2k2b only returns prior
            # result, never replays a positive after a later GUI deletion.
            completed = _checkpoint(folder, intent, writer.receipts.uid,
                                    targets=writer.targets)
            if completed is not None:
                if (attest() != proof or
                        not _completed_debug_evidence_unchanged(
                            proof, intent, writer.receipts.uid,
                            writer.receipts.writer_gid)):
                    raise V2OriginalConfigRefused(
                        "original_completed_debug_not_attested")
                # Never reapply a domain that the GUI removed after this
                # exact original Config checkpoint was durably completed.
                return completed[0]
            # After an independent diagnostic cut, the previously sealed
            # original intent AND original Config-prepared plan prove the
            # native event already passed strict debug/raw correlation.
            # Re-evaluate current P1 from the same authenticated RAW hosts,
            # never attributing a known HOSTLIST by guess. No fresh plan or
            # effect may be invented; preimage CAS is required for replay.
            if _evidence_unchanged(proof, intent, writer.receipts.uid,
                                   writer.receipts.writer_gid):
                observations = _domains(
                    proof, intent, raw, owner_uid=writer.receipts.uid,
                    writer_gid=writer.receipts.writer_gid)
            else:
                if (intent["evidence"] != "native-debug" or
                        not _completed_debug_evidence_unchanged(
                            proof, intent, writer.receipts.uid,
                            writer.receipts.writer_gid)):
                    raise V2OriginalConfigRefused(
                        "original_unqualified_partial_debug_cut")
                qualified_destination_plan(
                    folder, intent, writer.receipts.uid,
                    targets=writer.targets)
                hosts = _raw_hosts(raw)
                if len(hosts) != intent["candidate_count"]:
                    raise V2OriginalConfigRefused(
                        "original_partial_raw_count_changed")
                observations = [{"hostname": host, "hostlist": None}
                                for host in hosts]
            if attest() != proof:
                raise V2OriginalConfigRefused(
                    "original_generation_changed_during_debug")
            final, _ = _target(writer.targets["auto"], writer.receipts.uid)
            current_manual = {**manual_hostlists, "auto": final.decode("utf-8")}
            policy = plan_auto_additions(observations, current_manual, owned,
                                         global_exclude, psl=psl)
            additions, removals = policy["additions"], policy["removals"]
            eligible = {route["root"] for route in policy["routes"]
                        if route["destination"] == "auto"}
            if (policy["result"] != "ok" or policy["unprocessed"] or
                    set(additions) - {"auto"} or
                    set(removals) - set(KNOWN_HOSTLISTS) or
                    any(domain not in eligible for domain in
                        [*additions.get("auto", []),
                         *(x for names in removals.values() for x in names)])):
                raise V2OriginalConfigRefused("original_p1_unknown_native_attribution")
            effects = {}
            if additions.get("auto"):
                effects["auto"] = {"add": additions["auto"], "remove": []}
            for key in KNOWN_HOSTLISTS:
                if removals.get(key):
                    effects[key] = {"add": [], "remove": removals[key]}
            _validate_partial_plan(folder, writer, effects, eligible)
            if (attest() != proof or
                    inspect(pending, original.st_dev, original.st_ino,
                            owner=proof.owner,
                            writer_gid=writer.queue.writer_gid) is not FDState.DRAINED or
                    detached_original_raw(writer.queue, pending) != raw or
                    not _completed_debug_evidence_unchanged(
                        proof, intent, writer.receipts.uid,
                        writer.receipts.writer_gid)):
                raise V2OriginalConfigRefused("original_generation_or_fd_changed_before_write")
            live = (_original_live_known_after_locked(
                folder, intent, writer, manual_hostlists, owned, effects,
                proof, attest) if running_live else None)
            result = writer._locked_commit(
                folder, intent, raw, effects, live=live)
            if (read_owned(root, owner_uid=writer.receipts.uid) is None or
                    _checkpoint(folder, intent, writer.receipts.uid,
                                targets=writer.targets) is None or
                    attest() != proof or result["ack_authorized"] is not False):
                raise V2OriginalConfigRefused("original_v2_checkpoint_not_verified")
            return result
    except (OSError, TypeError, ValueError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalSourceRefused, CursorChainRefused,
            DestinationRefused, OwnedSourcesRefused, AutoDomainPolicyError,
            DomainPolicyError, EffectiveKnownRefused) as exc:
        raise V2OriginalConfigRefused("original_config_v2_commit_refused") from exc
