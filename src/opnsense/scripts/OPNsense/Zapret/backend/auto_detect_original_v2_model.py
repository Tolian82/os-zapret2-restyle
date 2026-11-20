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
            (debug_window and not debug_window.endswith(b"\n")) or
            b"\x00" in debug_window or b"\r" in debug_window):
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
        if not line.endswith(b"\n"):
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



# TZ6v4 STEP 4: one existing P1 policy and effective-known composer,
# with original source attribution BEFORE the PSL collapse. This projection
# is not itself a durable Found/live write nor an original cursor ACK.
def preview_learning_p1_effects(
    observations: list[dict], manual_hostlists: dict[str, str],
    owned_found: dict[str, str], shared_found: str,
    global_exclude: str, *, psl: PublicSuffixList | None = None,
) -> dict:
    """Derive all three permanent Found effects and both active images.

    Requires a COMPLETE original Config/Found snapshot, not a partial
    observation-to-one-field shortcut. The caller must prove P2/P2b/P2c
    native-to-map provenance independently and still use the same original
    destination WAL for every durable write. Rejections keep ALL source
    bytes pending; unknown source cannot be guessed from its hostname.
    """
    if (not isinstance(observations, list) or
            not 0 < len(observations) <= 4096 or
            any(not isinstance(row, dict) or
                set(row) != {"hostname", "hostlist"} or
                type(row["hostname"]) is not str or
                row["hostlist"] not in KNOWN_HOSTLISTS
                for row in observations) or
            not isinstance(manual_hostlists, dict) or
            set(manual_hostlists) != set(KNOWN_HOSTLISTS) or
            not isinstance(owned_found, dict) or
            set(owned_found) != set(KNOWN_HOSTLISTS) or
            any(type(s) is not str or len(s.encode("utf-8")) > MAX_MODEL_TEXT
                for s in (*manual_hostlists.values(), *owned_found.values())) or
            type(shared_found) is not str or
            len(shared_found.encode("utf-8")) > MAX_MODEL_TEXT or
            type(global_exclude) is not str or
            len(global_exclude.encode("utf-8")) > MAX_EXCLUDE_TEXT):
        raise V2OriginalConfigRefused("learning_p1_incomplete_registered_sources")
    try:
        canonical = {}
        for name in KNOWN_HOSTLISTS:
            normal = normalize(manual_hostlists[name], name)["normalized"]
            canonical[name] = normal + ("\n" if normal else "")
        # The same canonical P1 logic is shared with the old source-only
        # observer, GUI and manual paths; attribution is already exact.
        planned = plan_auto_additions(
            observations, {**canonical, "auto": shared_found},
            owned_found, global_exclude, psl=psl)
        if (planned["result"] != "ok" or planned["unprocessed"] or
                set(planned["additions"]) - {"auto", *KNOWN_HOSTLISTS} or
                set(planned["removals"]) - set(KNOWN_HOSTLISTS) or
                planned["removals"].get("auto")):
            raise V2OriginalConfigRefused("learning_p1_unprocessed_requires_retention")
        effects = {}
        found_after = {}
        for name in (*KNOWN_HOSTLISTS, "auto"):
            add = planned["additions"].get(name, [])
            remove = planned["removals"].get(name, [])
            if add or remove:
                effects[name] = {"add": add, "remove": remove}
            before = (shared_found if name == "auto" else owned_found[name])
            found_after[name] = _edit(
                before.encode("utf-8"), add, remove)
        known_after = compose_known(
            canonical,
            {name: found_after[name].decode("utf-8")
             for name in KNOWN_HOSTLISTS})
        return {
            "effects": effects,
            "found_after": found_after,
            "managed_after": {
                name: known_after[name].encode("utf-8")
                for name in KNOWN_HOSTLISTS
            },
            "routes": planned["routes"],
            "excluded": planned["excluded"],
            "psl_sha256": planned["psl_sha256"],
            "commit_authorized": False,
            "cleanup_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (AutoDomainPolicyError, DomainPolicyError, EffectiveKnownRefused,
            DestinationRefused, UnicodeError, ValueError, TypeError, KeyError,
            AttributeError) as exc:
        raise V2OriginalConfigRefused("learning_p1_sources_or_psl_refused") from exc


def preview_original_learning_p1_locked(
    writer: DestinationCommit, proof, workspace: Path, *,
    owned_root: Path, manual_hostlists: dict[str, str],
    global_exclude: str, attest, inspect=probe_pending_fd,
    psl: PublicSuffixList | None = None, running_live: bool = False,
) -> dict:
    """Original P2a/P2b/P2c + GUI locked native → P1 → live plan, NO writes.

    Original PHP Config::lock supplies the exact manual values. P2a and the
    original GUI destination flock MUST already be held; the attester must
    prove the current schema3 terminal-running FD9 owner independently.
    Neither a preview nor a drained FD authorizes cleanup before a future
    durable original per-slot WAL + active managed checkpoint.
    """
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_original_v2_source import (
        attest_original_learning_drained_candidate_locked,
        preview_original_learning_candidates_locked,
    )

    if (not isinstance(writer, DestinationCommit) or
            not writer.queue._held or not getattr(writer, "_gui_held", False)
            or not isinstance(proof, LearningGenerationProof)
            or not isinstance(workspace, Path) or not workspace.is_absolute()
            or not isinstance(owned_root, Path) or not owned_root.is_absolute()
            or not callable(attest) or not callable(inspect) or
            type(running_live) is not bool or
            set(writer.targets) != {"auto", *KNOWN_HOSTLISTS} or
            writer.targets["auto"].parent == owned_root or
            any(writer.targets[name] != owned_root / (name + ".txt")
                for name in KNOWN_HOSTLISTS) or
            attest() != proof):
        raise V2OriginalConfigRefused("original_learning_config_p2_gui_owner_required")
    try:
        candidate = attest_original_learning_drained_candidate_locked(
            writer.queue, writer.receipts, proof, workspace,
            attest=attest, inspect=inspect)
        original_owned = read_owned(owned_root, owner_uid=writer.receipts.uid)
        if original_owned is None:
            raise V2OriginalConfigRefused("original_learning_found_ledger_absent")
        shared_bytes, shared_stat = _target(
            writer.targets["auto"], writer.receipts.uid)
        projection = preview_learning_p1_effects(
            candidate["observations"], manual_hostlists, original_owned,
            shared_bytes.decode("utf-8"), global_exclude, psl=psl)
        live = None
        if running_live:
            canonical = {}
            for name in KNOWN_HOSTLISTS:
                normalized = normalize(manual_hostlists[name], name)["normalized"]
                canonical[name] = normalized + ("\n" if normalized else "")
            # Reuse the SAME live preimage inspector and managed composer;
            # this is neither a new Config writer nor a standalone reload.
            aligned = preview_live_known_after_readonly(
                canonical, projection["effects"],
                active=COMMON_ACTIVE, owned_root=owned_root,
                owner_uid=writer.receipts.uid, attest=attest)
            if (aligned["owner_schema"] != 3 or
                    aligned["generation"] != proof.generation or
                    aligned["operation"] != proof.operation_id or
                    aligned["pid"] != proof.owner.pid or
                    aligned["started"] != proof.owner.started or
                    aligned["commit_authorized"] is not False or
                    aligned["ack_authorized"] is not False):
                raise V2OriginalConfigRefused("learning_p1_live_generation_not_same")
            live = {}
            for name in aligned["changed"]:
                row = aligned["files"][name]
                path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
                after_bytes = projection["managed_after"][name]
                if (row["path"] != str(path) or
                        row["after_sha256"] !=
                        hashlib.sha256(after_bytes).hexdigest()):
                    raise V2OriginalConfigRefused("learning_p1_live_after_not_exact")
                live[name] = {
                    "path": path,
                    "before_sha256": row["before_sha256"],
                    "after": after_bytes,
                }
        # The native writer ignores the P2a flock. P1/PSL can take time:
        # prove the SAME debug+N native physical windows again before
        # returning the proposal to the original Config/WAL owner.
        after = preview_original_learning_candidates_locked(
            writer.queue, writer.receipts, proof, workspace, attest=attest)
        same_owned = read_owned(owned_root, owner_uid=writer.receipts.uid)
        same_shared, same_stat = _target(
            writer.targets["auto"], writer.receipts.uid)
        physical = lambda st: (st.st_dev, st.st_ino, st.st_size,
                               st.st_ctime_ns, st.st_mtime_ns)
        if (after["observations"] != candidate["observations"] or
                after["native_cursors"] != candidate["native_cursors"] or
                after["debug_end_offset"] != candidate["debug_end_offset"] or
                after["debug_end_sha256"] != candidate["debug_end_sha256"] or
                same_owned != original_owned or
                same_shared != shared_bytes or
                physical(same_stat) != physical(shared_stat) or
                attest() != proof):
            raise V2OriginalConfigRefused("learning_p1_owner_or_sources_changed")
        return {
            "source": candidate,
            "p1": projection,
            "live": live,
            "commit_authorized": False,
            "cleanup_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, TypeError, ValueError, KeyError, AttributeError,
            ReceiptRefused, OriginalSourceRefused, DestinationRefused,
            OwnedSourcesRefused, EffectiveKnownRefused) as exc:
        raise V2OriginalConfigRefused("original_learning_p1_preview_refused") from exc


def _recover_original_learning_partial_locked(
        writer: DestinationCommit, proof, workspace: Path,
        slot: Path, intent: dict, *, owned_root: Path,
        manual_hostlists: dict[str, str], global_exclude: str,
        attest, inspect, psl: PublicSuffixList | None,
) -> dict:
    """Resume ONE already-published original WAL preimage, never a new P1.

    The caller holds the original Config OFD, P2a and GUI locks and FD9.
    Reconstruct old automatic sources ONLY when the exact originally
    published CAS hashes permit a deterministic inverse. Recompute the
    existing P1 policy against THOSE old sources, require identical
    add/remove effects, exact managed before+after images and file paths.
    A completed or foreign plan, changed manual/excludes, altered inode,
    ambiguous inverse, or native-prefix mutation refuses rather than
    overwriting a GUI edit. No live native row removal or ACK occurs.
    """
    from auto_detect_original_v2_source import (
        attest_original_learning_sealed_prefix_locked,
    )
    from auto_detect_destination_commit import _file_identity
    if (not isinstance(writer, DestinationCommit) or
            not writer.queue._held or not getattr(writer, "_gui_held", False)
            or not isinstance(intent, dict) or intent.get("schema") != 3 or
            not isinstance(slot, Path) or
            not isinstance(owned_root, Path) or
            not owned_root.is_absolute() or
            set(writer.targets) != {"auto", *KNOWN_HOSTLISTS} or
            any(writer.targets[name] != owned_root / (name + ".txt")
                for name in KNOWN_HOSTLISTS) or
            not callable(attest) or attest() != proof):
        raise V2OriginalConfigRefused("learning_partial_original_locks_required")
    plan, raw_plan = qualified_destination_plan(
        slot, intent, writer.receipts.uid, targets=writer.targets)
    if (plan.get("schema") != 3 or "live" not in plan or
            (slot / "destination" / "checkpoint.json").exists() or
            (slot / "destination" / "checkpoint.json").is_symlink()):
        raise V2OriginalConfigRefused("learning_partial_sealed_plan_required")
    prefix = attest_original_learning_sealed_prefix_locked(
        writer.queue, writer.receipts, proof, workspace, intent,
        attest=attest, inspect=inspect)
    if (prefix["source_intent_sha256"] != plan["source_intent_sha256"]
            or not prefix["p2b_drained"]):
        raise V2OriginalConfigRefused("learning_partial_source_changed")

    # Original auto-owned P1 sources cannot be recomputed from a partly
    # installed Found. Reconstruct the BEFORE snapshot from the sealed
    # per-target plan only. If edits/reordering make it ambiguous, REFUSE.
    original = {}
    all_names = (*KNOWN_HOSTLISTS, "auto")
    for name in all_names:
        path = writer.targets[name]
        data, st = _target(path, writer.receipts.uid)
        write = plan["writes"].get(name)
        if write is None:
            original[name] = data.decode("utf-8")
            continue
        saved = (
            write["before_device"], write["before_inode"],
            write["before_ctime_ns"], write["before_mtime_ns"],
            write["before_size"],
        )
        current_sha = hashlib.sha256(data).hexdigest()
        if current_sha == write["before"] and _file_identity(st) == saved:
            before = data
        elif current_sha == write["after"] and (
                write["after"] != write["before"]):
            before = _edit(data, write["remove"], write["add"])
            if hashlib.sha256(before).hexdigest() != write["before"]:
                raise V2OriginalConfigRefused(
                    "learning_partial_nonreversible_old_found")
        else:
            raise V2OriginalConfigRefused(
                "learning_partial_foreign_found_edit")
        original[name] = before.decode("utf-8")
    if read_owned(owned_root, owner_uid=writer.receipts.uid) is None:
        raise V2OriginalConfigRefused("learning_partial_owned_ledger_absent")

    projected = preview_learning_p1_effects(
        intent["observations"], manual_hostlists,
        {name: original[name] for name in KNOWN_HOSTLISTS},
        original["auto"], global_exclude, psl=psl)
    expected_effects = {
        name: {"add": item["add"], "remove": item["remove"]}
        for name, item in plan["writes"].items()
    }
    if projected["effects"] != expected_effects:
        raise V2OriginalConfigRefused(
            "learning_partial_p1_differs_from_sealed_plan")
    canonical = {}
    for name in KNOWN_HOSTLISTS:
        normalized = normalize(manual_hostlists[name], name)["normalized"]
        canonical[name] = normalized + ("\n" if normalized else "")
    before_managed = compose_known(
        canonical, {name: original[name] for name in KNOWN_HOSTLISTS})
    live = {}
    for name in KNOWN_HOSTLISTS:
        expected_before = before_managed[name].encode("utf-8")
        expected_after = projected["managed_after"][name]
        row = plan["live"].get(name)
        if row is None:
            if expected_before != expected_after:
                raise V2OriginalConfigRefused(
                    "learning_partial_missing_live_after")
            continue
        path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
        if (row["path"] != str(path) or
                row["before"] != hashlib.sha256(expected_before).hexdigest() or
                row["after"] != hashlib.sha256(expected_after).hexdigest() or
                expected_before == expected_after):
            raise V2OriginalConfigRefused(
                "learning_partial_live_plan_not_original")
        current, st = _target(path, writer.receipts.uid)
        if hashlib.sha256(current).hexdigest() == row["before"]:
            if _file_identity(st) != (
                    row["before_device"], row["before_inode"],
                    row["before_ctime_ns"], row["before_mtime_ns"],
                    row["before_size"]):
                raise V2OriginalConfigRefused(
                    "learning_partial_gui_live_preimage_changed")
        elif hashlib.sha256(current).hexdigest() != row["after"]:
            raise V2OriginalConfigRefused(
                "learning_partial_foreign_live_image")
        live[name] = {
            "path": path, "before_sha256": row["before"],
            "after": expected_after,
        }
    recheck = attest_original_learning_sealed_prefix_locked(
        writer.queue, writer.receipts, proof, workspace, intent,
        attest=attest, inspect=inspect)
    if recheck != prefix or attest() != proof:
        raise V2OriginalConfigRefused("learning_partial_source_raced")
    # The EXISTING original CAS writer checks physical per-target inode
    # identity again and writes Found before managed then one checkpoint.
    completion = writer._locked_commit(
        slot, intent, _canonical({"observations": intent["observations"]}),
        projected["effects"], live=live)
    verified, checkpoint_raw = qualified_destination_plan(
        slot, intent, writer.receipts.uid, targets=writer.targets)
    if (verified != plan or checkpoint_raw != raw_plan or
            completion.get("plan_sha256") !=
            hashlib.sha256(raw_plan).hexdigest() or
            completion.get("ack_authorized") is not False or
            attest() != proof):
        raise V2OriginalConfigRefused("learning_partial_checkpoint_not_original")
    return completion


def commit_with_original_learning_first_slot(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path,
        owned_root: Path, manual_hostlists: dict[str, str],
        global_exclude: str, attest, inspect=probe_pending_fd,
        psl: PublicSuffixList | None = None,
) -> dict:
    """Import-only original FD4/FD9 schema3 P1 → SAME destination WAL.

    Original PHP must own the actual Config::lock, inherited Config OFD,
    original P2a queue lock and original terminal FD9 running generation.
    The existing DestinationCommit writes PERMANENT Found first and live
    managed after, with one source-bound plan/checkpoint. The source is a
    working native HOSTLIST: this method NEVER removes native rows, moves
    a cursor, acknowledges or restarts dvtws2. The original minute does
    not dispatch this method until full cleanup/recovery is proven.
    """
    import sys
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_epoch_receipts import _canonical
    from auto_detect_cursor_chain import CursorChain

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(owned_root, Path) or not owned_root.is_absolute() or
            not isinstance(config_path, Path) or not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            not writer.queue._held or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or
              writer.receipts.uid != 0 or writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused("learning_original_config_fd9_model_required")

    def config_held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused("learning_original_config_owner_changed")

    try:
        config_held()
        chain = CursorChain(writer.receipts, writer.queue)
        prepared = chain.prepare_learning_first_slot(
            proof, workspace, attest=attest, inspect=inspect)
        slot = prepared["slot"]
        encoded = _read(slot / "intent.json", writer.receipts.uid)
        if hashlib.sha256(encoded).hexdigest() != prepared["intent_sha256"]:
            raise V2OriginalConfigRefused("learning_original_intent_changed")
        intent = json.loads(encoded)
        raw = _canonical({"observations": intent["observations"]})
        with writer.exclusive_targets():
            config_held()
            plan_file = slot / "destination" / "plan.json"
            checkpoint_file = slot / "destination" / "checkpoint.json"
            if checkpoint_file.exists() or checkpoint_file.is_symlink():
                # A *completed* original checkpoint cannot be recomputed
                # after the GUI removes a Found entry. Return exactly the
                # already committed result, no new writes or policy replay.
                plan, plan_raw = qualified_destination_plan(
                    slot, intent, writer.receipts.uid, targets=writer.targets)
                checkpoint = json.loads(_read(checkpoint_file, writer.receipts.uid))
                expected = {
                    "schema": 1, "kind": "destination-and-cursor-committed",
                    "generation": intent["generation"],
                    "pending_name": "learning-00000000",
                    "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
                    "evidence": "learning-native-debug",
                    "committed_cursor_offset": intent["debug_end_offset"],
                    "committed_cursor_sha256": intent["debug_end_sha256"],
                    "ack_authorized": False,
                }
                if checkpoint != expected or attest() != proof:
                    raise V2OriginalConfigRefused("learning_checkpoint_replay_mismatch")
                config_held()
                return checkpoint
            if plan_file.exists() or plan_file.is_symlink():
                # The ONLY original WAL partial-replay path. It restores
                # the previous P1 snapshot from the protected published
                # preimages and refuses ambiguous GUI edits; never treats
                # postlaunch native suffixes as part of this old intent.
                resumed = _recover_original_learning_partial_locked(
                    writer, proof, workspace, slot, intent,
                    owned_root=owned_root, manual_hostlists=manual_hostlists,
                    global_exclude=global_exclude, attest=attest,
                    inspect=inspect, psl=psl)
                config_held()
                return resumed
            projection = preview_original_learning_p1_locked(
                writer, proof, workspace, owned_root=owned_root,
                manual_hostlists=manual_hostlists,
                global_exclude=global_exclude, attest=attest,
                inspect=inspect, psl=psl, running_live=True)
            source = projection["source"]
            if (source["observations"] != intent["observations"] or
                    source["debug_end_offset"] != intent["debug_end_offset"] or
                    source["debug_end_sha256"] != intent["debug_end_sha256"] or
                    len(intent["native"]) != len(proof.learning) or
                    any(
                        row["path"] not in source["native_cursors"] or
                        row["end_offset"] != source["native_cursors"][
                            row["path"]].offset or
                        row["end_sha256"] != source["native_cursors"][
                            row["path"]].prefix_sha256 or
                        (row["device"], row["inode"]) != (
                            source["native_cursors"][row["path"]].device,
                            source["native_cursors"][row["path"]].inode)
                        for row in intent["native"]) or
                    projection["live"] is None or
                    projection["commit_authorized"] is not False or
                    projection["cleanup_authorized"] is not False or
                    projection["ack_authorized"] is not False):
                raise V2OriginalConfigRefused("learning_original_p1_not_same_sealed_source")
            config_held()
            result = writer._locked_commit(
                slot, intent, raw, projection["p1"]["effects"],
                live=projection["live"])
            plan, plan_raw = qualified_destination_plan(
                slot, intent, writer.receipts.uid, targets=writer.targets)
            if (not (slot / "destination" / "checkpoint.json").exists() or
                    result.get("plan_sha256") !=
                    hashlib.sha256(plan_raw).hexdigest() or
                    result.get("ack_authorized") is not False or
                    attest() != proof):
                raise V2OriginalConfigRefused("learning_original_destination_not_durable")
            config_held()
            return result
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, CursorChainRefused,
            OriginalSourceRefused, ValueError,
            DestinationRefused, OwnedSourcesRefused, EffectiveKnownRefused,
            AutoDomainPolicyError, DomainPolicyError, OSError, TypeError,
            KeyError, AttributeError, UnicodeError) as exc:
        raise V2OriginalConfigRefused(
            "learning_original_config_wal_commit_refused") from exc


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
