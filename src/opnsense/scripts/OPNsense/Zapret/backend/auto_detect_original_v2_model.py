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
from auto_detect_debug_window import (ADD, MAX_RAW, MAX_WINDOW, _raw_hosts,
                                      _read_exact, _hostname, DebugWindowRefused)
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


def preview_learning_checkpoint_native_compaction_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        owned_root: Path, manual_hostlists: dict[str, str],
        global_exclude: str, attest, inspect=probe_pending_fd,
        psl: PublicSuffixList | None = None,
) -> dict:
    """Read-only ORIGINAL FD9/P2a/GUI checkpoint → exact per-N removal proof.

    The PHP caller must additionally hold genuine Config::lock/FD4, and
    supply its LOCKED current manual/exclude values. This internal function
    is deliberately NOT a production entry point, does not call native
    rotation, and never grants cleanup/ACK. It derives candidates solely
    from the original durable first-slot observation and a completed
    Found+managed WAL, never from raw debug text or file-name guesses.

    Only a hostname in the SEALED native prefix whose PSL root was added
    to the SAME known Found AND the active managed image may be proposed
    for removal. Later native bytes remain verbatim and must accompany a
    full-image digest/size when a future original FD9 mutation uses P2a.
    """
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_original_v2_source import (
        attest_original_learning_sealed_prefix_locked,
    )
    from auto_detect_epoch_receipts import _canonical
    from auto_detect_debug_window import _read_exact, _raw_hosts
    from domain_policy import _list_entries
    if (not isinstance(writer, DestinationCommit) or
            not writer.queue._held or not getattr(writer, "_gui_held", False)
            or not isinstance(proof, LearningGenerationProof) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(owned_root, Path) or not owned_root.is_absolute() or
            not isinstance(manual_hostlists, dict) or
            set(manual_hostlists) != set(KNOWN_HOSTLISTS) or
            not callable(attest) or not callable(inspect) or
            set(writer.targets) != {"auto", *KNOWN_HOSTLISTS} or
            any(writer.targets[name] != owned_root / (name + ".txt")
                for name in KNOWN_HOSTLISTS) or attest() != proof):
        raise V2OriginalConfigRefused("learning_compaction_original_locks_required")
    try:
        # Reuse the SAME immutable original cursor slot, FD9/epoch/P2b.
        # Its first source still pins the prelaunch inode numbers, even
        # though dvtws2 may have appended more rows in the same files.
        sealed = CursorChain(writer.receipts, writer.queue).prepare_learning_first_slot(
            proof, workspace, attest=attest, inspect=inspect)
        slot = sealed["slot"]
        intent_raw = _read(slot / "intent.json", writer.receipts.uid)
        intent = json.loads(intent_raw)
        plan, plan_raw = qualified_destination_plan(
            slot, intent, writer.receipts.uid, targets=writer.targets)
        saved_cp = json.loads(_read(
            slot / "destination" / "checkpoint.json", writer.receipts.uid))
        expected_cp = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": proof.generation,
            "pending_name": "learning-00000000",
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "evidence": "learning-native-debug",
            "committed_cursor_offset": intent["debug_end_offset"],
            "committed_cursor_sha256": intent["debug_end_sha256"],
            "ack_authorized": False,
        }
        if (saved_cp != expected_cp or
                plan.get("schema") != 3 or
                "live" not in plan or
                plan["source_intent_sha256"] !=
                hashlib.sha256(intent_raw).hexdigest() or
                not any(plan["writes"].get(name, {}).get("add")
                        for name in KNOWN_HOSTLISTS) or
                attest() != proof):
            raise V2OriginalConfigRefused("learning_compaction_checkpoint_unqualified")
        owned = read_owned(owned_root, owner_uid=writer.receipts.uid)
        if owned is None:
            raise V2OriginalConfigRefused("learning_compaction_owned_ledger_missing")
        shared_bytes, _ = _target(writer.targets["auto"], writer.receipts.uid)
        for name, change in plan["writes"].items():
            data, _ = _target(writer.targets[name], writer.receipts.uid)
            if (change["path"] != str(writer.targets[name]) or
                    hashlib.sha256(data).hexdigest() != change["after"]):
                raise V2OriginalConfigRefused("learning_compaction_gui_postimage_changed")
        canonical = {}
        for name in KNOWN_HOSTLISTS:
            normal = normalize(manual_hostlists[name], name)["normalized"]
            canonical[name] = normal + ("\n" if normal else "")
        expected_managed = compose_known(canonical, owned)
        active_now = {}
        for name in KNOWN_HOSTLISTS:
            active_path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
            data, _ = _target(active_path, writer.receipts.uid)
            if data != expected_managed[name].encode("utf-8"):
                raise V2OriginalConfigRefused("learning_compaction_active_managed_diverged")
            active_now[name] = data
        for name, row in plan["live"].items():
            live_path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
            if (row["path"] != str(live_path) or
                    hashlib.sha256(active_now[name]).hexdigest() != row["after"]):
                raise V2OriginalConfigRefused("learning_compaction_sealed_live_changed")

        # The current canonical P1 policy must still accept the ORIGINAL
        # observations with exactly the SAME owner source. New negatives,
        # shared ambiguity, global excludes, or policy drift veto removal.
        current_p1 = preview_learning_p1_effects(
            intent["observations"], manual_hostlists, owned,
            shared_bytes.decode("utf-8"), global_exclude, psl=psl)
        if (current_p1["effects"] or current_p1["excluded"] or
                current_p1["commit_authorized"] is not False or
                current_p1["cleanup_authorized"] is not False):
            raise V2OriginalConfigRefused("learning_compaction_policy_changed")
        psl_obj = psl if psl is not None else PublicSuffixList.load()
        routes = {
            (row["root"], row["destination"])
            for row in current_p1["routes"] if row["reason"] == "attributed"
        }
        exact_rows = {
            name: {
                row[0] for row in _list_entries(owned[name], name)
                if not row[1] and not row[2]
            }
            for name in KNOWN_HOSTLISTS
        }
        eligible = {
            name: set(plan["writes"].get(name, {}).get("add", [])) &
                  exact_rows[name]
            for name in KNOWN_HOSTLISTS
        }
        # Require the actual sealed managed-change WAL for that source.
        # Already-covered rows and shared/ambiguous routes remain native;
        # this first-slot preflight never retroactively treats them as new.
        for name in KNOWN_HOSTLISTS:
            if name not in plan["live"]:
                eligible[name] = set()
        originals = {
            (row["hostname"], row["hostlist"])
            for row in intent["observations"]
        }
        proposed = []
        for index, (number, name, pathname) in enumerate(proof.learning):
            source = intent["native"][index]
            if ((source["native_number"], source["hostlist"],
                 source["path"]) != (number, name, pathname)):
                raise V2OriginalConfigRefused("learning_compaction_profile_map_changed")
            st, data = _read_exact(
                Path(pathname), owner_uid=writer.receipts.uid,
                writer_gid=writer.queue.writer_gid)
            end = source["end_offset"]
            if ((st.st_dev, st.st_ino) !=
                    (source["device"], source["inode"]) or
                    not 0 <= end <= len(data) or
                    hashlib.sha256(data[:end]).hexdigest() !=
                    source["end_sha256"] or
                    (data and not data.endswith(b"\n"))):
                raise V2OriginalConfigRefused("learning_compaction_native_source_changed")
            prefix = data[:end]
            old_hosts = _raw_hosts(prefix) if prefix else []
            late = data[end:]
            if late:
                _raw_hosts(late)
            kept = []
            removed = []
            for hostname in old_hosts:
                root = psl_obj.registrable_domain(hostname)
                if (root in eligible[name] and
                        (root, name) in routes and
                        (hostname, name) in originals):
                    removed.append(hostname)
                else:
                    kept.append(hostname)
            replacement = (
                ("".join(host + "\n" for host in kept)).encode("ascii") +
                late)
            if removed:
                if len(replacement) >= len(data):
                    raise V2OriginalConfigRefused(
                        "learning_compaction_postimage_not_smaller")
                proposed.append({
                    "native_number": number, "hostlist": name,
                    "path": Path(pathname),
                    "expected_identity": (st.st_dev, st.st_ino),
                    "sealed_prefix": (end, source["end_sha256"]),
                    "expected_native_image": (
                        len(data), hashlib.sha256(data).hexdigest()),
                    "replacement": replacement,
                    "removed": tuple(removed),
                })
        # Never let a partial cross-N read authorize a later mutation
        # without another original epoch/P2b qualification.
        verified = attest_original_learning_sealed_prefix_locked(
            writer.queue, writer.receipts, proof, workspace, intent,
            attest=attest, inspect=inspect)
        if (verified["source_intent_sha256"] !=
                hashlib.sha256(intent_raw).hexdigest() or
                attest() != proof):
            raise V2OriginalConfigRefused("learning_compaction_original_epoch_raced")
        return {
            "generation": proof.generation,
            "source_intent_sha256": hashlib.sha256(intent_raw).hexdigest(),
            "checkpoint_sha256": hashlib.sha256(
                _canonical(saved_cp)).hexdigest(),
            "profiles": proposed,
            "commit_authorized": False,
            "cleanup_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, OriginalSourceRefused, CursorChainRefused,
            DestinationRefused, OwnedSourcesRefused, EffectiveKnownRefused,
            AutoDomainPolicyError, DomainPolicyError,
            DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "learning_compaction_checkpoint_preview_refused") from exc


def seal_original_learning_native_rebind_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path,
        owned_root: Path, manual_hostlists: dict[str, str],
        global_exclude: str, attest, inspect=probe_pending_fd,
        psl: PublicSuffixList | None = None,
) -> dict:
    """Seal ONE cross-N native transition in the ORIGINAL first cursor slot.

    This is the pre-mutation journal phase ONLY. Under original P2a+GUI,
    genuine inherited Config FD4 and original FD9/P2b, write once one
    bounded root-only receipt for each actual native profile, then ONE
    aggregate manifest. The manifest is published LAST. Every selected
    removed row is already in the original permanent Found→live managed
    checkpoint. The original native P2a physical helper, same-PID list
    reload and per-native pending ACK are NOT called or authorized here.

    No second queue, runtime journal, separate Config writer or automatic
    minute invocation. The same generation/cursor-chain-v2/00000000
    already owns the original source and destination receipts.
    """
    import os
    import re
    import sys
    from auto_detect_epoch_receipts import (
        _canonical, _write_once, _directory, _sync,
    )
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_cursor_chain import CursorChainRefused
    from auto_detect_queue import QueueSafetyError

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or
            not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not writer.queue._held or
            not getattr(writer, "_gui_held", False) or
            not isinstance(owned_root, Path) or
            not owned_root.is_absolute() or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or
              writer.receipts.uid != 0 or writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused("learning_rebind_original_fd4_fd9_required")

    def config_held() -> None:
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused("learning_rebind_owner_changed")

    try:
        config_held()
        if writer.queue.segments():
            # No detached original pending may be lost behind a new plan.
            raise V2OriginalConfigRefused("learning_rebind_existing_pending")
        candidate = preview_learning_checkpoint_native_compaction_locked(
            writer, proof, workspace, owned_root=owned_root,
            manual_hostlists=manual_hostlists,
            global_exclude=global_exclude, attest=attest, inspect=inspect,
            psl=psl)
        if (not candidate["profiles"] or
                candidate["commit_authorized"] is not False or
                candidate["cleanup_authorized"] is not False or
                candidate["ack_authorized"] is not False):
            raise V2OriginalConfigRefused("learning_rebind_no_qualified_profile")
        slot = (writer.receipts.root / proof.generation /
                "cursor-chain-v2" / "00000000")
        _directory(slot, writer.receipts.uid)
        intent_raw = _read(slot / "intent.json", writer.receipts.uid)
        intent = json.loads(intent_raw)
        if (hashlib.sha256(intent_raw).hexdigest() !=
                candidate["source_intent_sha256"] or
                len(intent["native"]) != len(proof.learning) or
                not 1 <= len(proof.learning) <= 255):
            raise V2OriginalConfigRefused("learning_rebind_intent_not_same_generation")
        qualified = {item["native_number"]: item
                     for item in candidate["profiles"]}
        if (len(qualified) != len(candidate["profiles"]) or
                set(qualified) - {row[0] for row in proof.learning}):
            raise V2OriginalConfigRefused("learning_rebind_unqualified_profile_set")
        packed: list[tuple[str, bytes]] = []
        for index, (number, name, pathname) in enumerate(proof.learning):
            source = intent["native"][index]
            if ((source["native_number"], source["hostlist"],
                 source["path"]) != (number, name, pathname) or
                    source["device"] < 0 or source["inode"] <= 0):
                raise V2OriginalConfigRefused("learning_rebind_origin_changed")
            selected = qualified.get(number)
            pending = None
            expected_full = None
            expected_after = None
            removed = []
            if selected is not None:
                if (selected["hostlist"] != name or
                        selected["path"] != Path(pathname) or
                        selected["expected_identity"] !=
                        (source["device"], source["inode"]) or
                        selected["sealed_prefix"] !=
                        (source["end_offset"], source["end_sha256"]) or
                        not selected["removed"] or
                        len(selected["removed"]) > 4096):
                    raise V2OriginalConfigRefused(
                        "learning_rebind_selected_source_changed")
                expected_full = {
                    "size": selected["expected_native_image"][0],
                    "sha256": selected["expected_native_image"][1],
                }
                expected_after = {
                    "size": len(selected["replacement"]),
                    "sha256": hashlib.sha256(
                        selected["replacement"]).hexdigest(),
                }
                removed = list(selected["removed"])
                # Deterministic original pending name, bound to the immutable
                # source and full preimage. A future physical phase can
                # distinguish pre-link, post-link, post-replace and FD-tail
                # states without guessing a random alias after a crash.
                digest = hashlib.sha256(
                    _canonical({
                        "generation": proof.generation,
                        "native_number": number,
                        "intent": candidate["source_intent_sha256"],
                        "checkpoint": candidate["checkpoint_sha256"],
                        "source": expected_full,
                    })).hexdigest()[:32]
                pending = (
                    f"native-{proof.generation}-{number}-{digest}.txt")
            record = {
                "schema": 3,
                "kind": "original-learning-native-rebind-profile",
                "generation": proof.generation,
                "sequence": 0,
                "native_number": number,
                "hostlist": name,
                "path": pathname,
                "old_device": source["device"],
                "old_inode": source["inode"],
                "sealed_end_offset": source["end_offset"],
                "sealed_end_sha256": source["end_sha256"],
                "full_preimage": expected_full,
                "replacement": expected_after,
                "removed": removed,
                "pending_name": pending,
                "ack_authorized": False,
            }
            packed.append((f"{number:03d}.json", _canonical(record)))

        # A bounded manifest covers ALL N records by their ordered digests.
        # Even 255 profiles fit: each record is separately 16 KiB-bound.
        total_hash = hashlib.sha256(
            b"".join(hashlib.sha256(raw).digest()
                     for _, raw in packed)).hexdigest()
        manifest = {
            "schema": 3,
            "kind": "original-learning-native-rebind-manifest",
            "generation": proof.generation,
            "sequence": 0,
            "owner_pid": proof.owner.pid,
            "owner_start": proof.owner.started,
            "native_map_sha256": proof.native_map_sha256,
            "source_intent_sha256": candidate["source_intent_sha256"],
            "checkpoint_sha256": candidate["checkpoint_sha256"],
            "profiles_count": len(packed),
            "profiles_sha256": total_hash,
            "physical_rotation_authorized": False,
            "ack_authorized": False,
        }
        encoded_manifest = _canonical(manifest)
        folder = slot / "native-rebind"
        if folder.exists() or folder.is_symlink():
            _directory(folder, writer.receipts.uid)
        else:
            config_held()
            folder.mkdir(mode=0o700)
            _sync(slot)
        allowed = {"manifest.json"} | {name for name, _ in packed}
        listed = set(os.listdir(folder))
        if listed - allowed:
            raise V2OriginalConfigRefused("learning_rebind_foreign_receipts")
        if "manifest.json" in listed and listed != allowed:
            raise V2OriginalConfigRefused("learning_rebind_incomplete_manifest")
        # Existing partial records may only resume with the IDENTICAL
        # protected source/P1/checkpoint. Never rewrite old records, never
        # reinterpret a new native suffix as an old completed transaction.
        for name, raw in packed:
            if name in listed and _read(
                    folder / name, writer.receipts.uid) != raw:
                raise V2OriginalConfigRefused("learning_rebind_prior_record_conflict")
        if "manifest.json" in listed and _read(
                folder / "manifest.json", writer.receipts.uid) != encoded_manifest:
            raise V2OriginalConfigRefused("learning_rebind_prior_manifest_conflict")
        # Publish individual N records only after the original Config/owner
        # and prior receipts are re-attested, then fsync the single manifest.
        config_held()
        for name, raw in packed:
            _write_once(folder, name, raw, writer.receipts.uid)
        # Native writers do NOT take P2a: reject newly appended sources
        # before publishing this manifest, with no unlink/replace/ACK.
        second = preview_learning_checkpoint_native_compaction_locked(
            writer, proof, workspace, owned_root=owned_root,
            manual_hostlists=manual_hostlists, global_exclude=global_exclude,
            attest=attest, inspect=inspect, psl=psl)
        if (second != candidate or
                set(os.listdir(folder)) -
                ({name for name, _ in packed} | {"manifest.json"})):
            raise V2OriginalConfigRefused("learning_rebind_source_changed_before_seal")
        config_held()
        _write_once(folder, "manifest.json", encoded_manifest,
                    writer.receipts.uid)
        if (_read(folder / "manifest.json", writer.receipts.uid) !=
                encoded_manifest or
                set(os.listdir(folder)) != allowed):
            raise V2OriginalConfigRefused("learning_rebind_manifest_not_durable")
        return {
            "generation": proof.generation,
            "manifest_sha256": hashlib.sha256(
                encoded_manifest).hexdigest(),
            "profiles_count": len(packed),
            "rotation_count": len(qualified),
            "physical_rotation_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, CursorChainRefused, OriginalLockRefused,
            DestinationRefused, OwnedSourcesRefused, OriginalSourceRefused,
            EffectiveKnownRefused, QueueSafetyError,
            AutoDomainPolicyError, DomainPolicyError, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "learning_rebind_original_journal_refused") from exc


def _native_rebind_stable_snapshot(path: Path, uid: int, writer_gid: int,
                                   *, allowed_links: tuple[int, ...]) -> tuple:
    """A read-only, bounded, no-follow native inode witness (1 or 2 links).

    Original native learning files are written by a non-cooperating dvtws2
    process. Never infer that the P2a flock serializes its append. The
    stable named/open/named inode, metadata and content are all required;
    the caller must still re-attest the all-N snapshot and the owner.
    """
    import os
    import stat
    from auto_detect_queue import _stat_regular, MAX_SEGMENT

    def identity(st):
        return (st.st_dev, st.st_ino, st.st_size, st.st_ctime_ns,
                st.st_mtime_ns, st.st_nlink, st.st_uid, st.st_gid,
                stat.S_IMODE(st.st_mode))

    before = _stat_regular(path, uid, max_size=MAX_SEGMENT,
                           writer_gid=writer_gid)
    if before.st_nlink not in allowed_links:
        raise V2OriginalConfigRefused("native_rebind_unexpected_hardlinks")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if identity(opened) != identity(before):
            raise V2OriginalConfigRefused("native_rebind_open_inode_changed")
        data = bytearray()
        while len(data) < before.st_size:
            part = os.read(fd, min(65536, before.st_size - len(data)))
            if not part:
                raise V2OriginalConfigRefused("native_rebind_short_read")
            data.extend(part)
        closed = os.fstat(fd)
    finally:
        os.close(fd)
    named = _stat_regular(path, uid, max_size=MAX_SEGMENT,
                          writer_gid=writer_gid)
    if (identity(before) != identity(closed) or
            identity(closed) != identity(named) or
            len(data) != before.st_size or
            (data and not data.endswith(b"\n")) or
            b"\r" in data or b"\x00" in data):
        raise V2OriginalConfigRefused("native_rebind_unstable_or_incomplete_content")
    return before, bytes(data), identity(named)


def inspect_original_learning_native_rebind_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        forward_wal_source: bool = False,
) -> dict:
    """Read-only original cross-N PREPARED→physical-state observation.

    Does NOT call prepare_learning_first_slot(): its old-epoch root-inode
    requirement intentionally refuses AFTER any physical rename. Instead,
    read the immutable source/checkpoint/manifest under the SAME original
    P2a+GUI+inherited Config FD and exact current FD9 generation. Require
    retention of the old inode and its complete preimage even when a new
    live native inode was installed; keep old-FD and new-path append suffix
    separate. No post-swap cursor, native ACK or product permission.
    """
    import os
    import re
    import sys
    from auto_detect_epoch_receipts import _canonical, _directory
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_destination_commit import _file_identity
    from auto_detect_queue import QueueSafetyError, NATIVE_PENDING
    from auto_detect_debug_window import _raw_hosts, DebugWindowRefused

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not getattr(writer, "_gui_held", False) or
            type(writer.queue.writer_gid) is not int or
            writer.queue.writer_gid <= 0 or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or
            not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or
              writer.receipts.uid != 0 or writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused("learning_rebind_inspector_original_owner_required")

    def held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused("learning_rebind_inspector_owner_changed")

    try:
        held()
        writer.queue._verify()
        slot = (writer.receipts.root / proof.generation /
                "cursor-chain-v2" / "00000000")
        folder = slot / "native-rebind"
        _directory(slot, writer.receipts.uid)
        _directory(folder, writer.receipts.uid)
        intent_raw = _read(slot / "intent.json", writer.receipts.uid)
        intent = json.loads(intent_raw)
        epoch_raw = _read(
            writer.receipts.root / proof.generation / "epoch.json",
            writer.receipts.uid)
        plan, plan_raw = qualified_destination_plan(
            slot, intent, writer.receipts.uid, targets=writer.targets)
        checkpoint_raw = _read(
            slot / "destination" / "checkpoint.json", writer.receipts.uid)
        checkpoint = json.loads(checkpoint_raw)
        manifest_raw = _read(folder / "manifest.json", writer.receipts.uid)
        manifest = json.loads(manifest_raw)
        if (intent.get("schema") != 3 or
                intent.get("kind") != "original-learning-cursor-prepared" or
                intent.get("generation") != proof.generation or
                intent.get("operation_id") != proof.operation_id or
                intent.get("owner_pid") != proof.owner.pid or
                intent.get("owner_start") != proof.owner.started or
                intent.get("owner_candidate_sha256") !=
                proof.owner_candidate_sha256 or
                intent.get("final_args_sha256") != proof.final_args_sha256 or
                intent.get("native_map_sha256") != proof.native_map_sha256 or
                intent.get("epoch_sha256") != hashlib.sha256(epoch_raw).hexdigest() or
                len(intent.get("native", [])) != len(proof.learning) or
                not 1 <= len(proof.learning) <= 255 or
                plan.get("schema") != 3 or
                "live" not in plan or
                plan.get("source_intent_sha256") !=
                hashlib.sha256(intent_raw).hexdigest()):
            raise V2OriginalConfigRefused("learning_rebind_inspector_original_intent_drift")
        expected_cp = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": proof.generation,
            "pending_name": "learning-00000000",
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "evidence": "learning-native-debug",
            "committed_cursor_offset": intent["debug_end_offset"],
            "committed_cursor_sha256": intent["debug_end_sha256"],
            "ack_authorized": False,
        }
        if checkpoint != expected_cp:
            raise V2OriginalConfigRefused("learning_rebind_inspector_checkpoint_changed")
        # During the *exact original second-slot P2k2b* a FIRST-slot
        # postimage can legitimately become a SECOND-slot postimage. Do
        # not weaken the physical/owner checks: accept this evolution
        # ONLY with the same protected write-once second-slot plan.
        # No plan, foreign plan, or random GUI edit remains a refusal.
        forward_plan = None
        if forward_wal_source:
            second = slot.parent / "00000001"
            _directory(second, writer.receipts.uid)
            source_raw = _read(
                second / "intent.json", writer.receipts.uid)
            source = json.loads(source_raw)
            forward_plan, forward_plan_raw = qualified_destination_plan(
                second, source, writer.receipts.uid,
                targets=writer.targets)
            if (source.get("sequence") != 1 or
                    source.get("generation") != proof.generation or
                    source.get("owner_pid") != proof.owner.pid or
                    source.get("owner_start") != proof.owner.started or
                    source.get("native_rebind_manifest_sha256") !=
                    hashlib.sha256(manifest_raw).hexdigest() or
                    forward_plan.get("source_intent_sha256") !=
                    hashlib.sha256(source_raw).hexdigest() or
                    "live" not in forward_plan):
                raise V2OriginalConfigRefused(
                    "learning_rebind_inspector_forward_wal_unqualified")
        # A third same-generation transaction may advance the SECOND
        # checkpoint's after-images, but ONLY through its own already
        # protected and source-bound original destination plan. Merely
        # seeing a third source intent MUST NOT relax GUI/CAS guards.
        third_plan = None
        if forward_plan is not None:
            third_slot = slot.parent / "00000002"
            third_plan_path = third_slot / "destination" / "plan.json"
            if third_plan_path.exists() or third_plan_path.is_symlink():
                _directory(third_slot, writer.receipts.uid)
                third_raw = _read(
                    third_slot / "intent.json", writer.receipts.uid)
                third_source = json.loads(third_raw)
                third_plan, _ = qualified_destination_plan(
                    third_slot, third_source, writer.receipts.uid,
                    targets=writer.targets)
                if (third_source.get("sequence") != 2 or
                        third_source.get("generation") != proof.generation or
                        third_source.get("owner_pid") != proof.owner.pid or
                        third_source.get("owner_start") !=
                        proof.owner.started or "live" not in third_plan):
                    raise V2OriginalConfigRefused(
                        "learning_rebind_inspector_third_plan_not_original")

        def original_pin(row, st):
            return _file_identity(st) == (
                row["before_device"], row["before_inode"],
                row["before_ctime_ns"], row["before_mtime_ns"],
                row["before_size"])

        def matches_target(name, path, expected_after, *, managed=False):
            data, st = _target(path, writer.receipts.uid)
            digest = hashlib.sha256(data).hexdigest()
            if digest == expected_after:
                return True
            if forward_plan is None:
                return False
            kind = "live" if managed else "writes"
            prior = forward_plan[kind].get(name)
            next_before = expected_after
            if prior is not None:
                if (prior["path"] != str(path) or
                        prior["before"] != expected_after):
                    return False
                next_before = prior["after"]
                if (digest == prior["after"] or
                        (digest == prior["before"] and
                         original_pin(prior, st))):
                    return True
            if third_plan is None:
                return False
            successor = third_plan[kind].get(name)
            return (successor is not None and
                    successor["path"] == str(path) and
                    successor["before"] == next_before and
                    (digest == successor["after"] or
                     (digest == successor["before"] and
                      original_pin(successor, st))))

        def matches_transition(name, path, prior, *, managed=False):
            data, st = _target(path, writer.receipts.uid)
            digest = hashlib.sha256(data).hexdigest()
            if prior["path"] != str(path):
                return False
            if (digest == prior["after"] or
                    (digest == prior["before"] and original_pin(prior, st))):
                return True
            if third_plan is None:
                return False
            successor = third_plan[
                "live" if managed else "writes"].get(name)
            return (successor is not None and
                    successor["path"] == str(path) and
                    successor["before"] == prior["after"] and
                    (digest == successor["after"] or
                     (digest == successor["before"] and
                      original_pin(successor, st))))
        # Post-commit GUI edits or active managed changes invalidate the
        # old source plan, even if the old root-only receipt still exists.
        for name, change in plan["writes"].items():
            if (change["path"] != str(writer.targets[name]) or
                    not matches_target(
                        name, writer.targets[name], change["after"])):
                raise V2OriginalConfigRefused("learning_rebind_inspector_found_diverged")
        for name, change in plan["live"].items():
            path = COMMON_ACTIVE / "managed" / ("hostlist-" + name + ".txt")
            if (change["path"] != str(path) or
                    not matches_target(
                        name, path, change["after"], managed=True)):
                raise V2OriginalConfigRefused("learning_rebind_inspector_managed_diverged")
        if forward_plan is not None:
            # Also qualify second-slot writes to targets never written
            # by the first slot (e.g. newly discovered shared auto).
            for name, item in forward_plan["writes"].items():
                path = writer.targets[name]
                if not matches_transition(name, path, item):
                    raise V2OriginalConfigRefused(
                        "learning_rebind_inspector_forward_found_unsafe")
            for name, item in forward_plan["live"].items():
                path = (COMMON_ACTIVE / "managed" /
                        ("hostlist-" + name + ".txt"))
                if not matches_transition(
                        name, path, item, managed=True):
                    raise V2OriginalConfigRefused(
                        "learning_rebind_inspector_forward_live_unsafe")
        file_names = [f"{number:03d}.json"
                      for number, _, _ in proof.learning]
        entries = set(os.listdir(folder))
        required = set(file_names) | {"manifest.json"}
        if entries not in (required, required | {"observed"}):
            raise V2OriginalConfigRefused("learning_rebind_inspector_incomplete_manifest")
        raw_rows = [_read(folder / name, writer.receipts.uid)
                    for name in file_names]
        source_sha = hashlib.sha256(intent_raw).hexdigest()
        checkpoint_sha = hashlib.sha256(
            _canonical(checkpoint)).hexdigest()
        expected_manifest = {
            "schema": 3,
            "kind": "original-learning-native-rebind-manifest",
            "generation": proof.generation,
            "sequence": 0,
            "owner_pid": proof.owner.pid,
            "owner_start": proof.owner.started,
            "native_map_sha256": proof.native_map_sha256,
            "source_intent_sha256": source_sha,
            "checkpoint_sha256": checkpoint_sha,
            "profiles_count": len(file_names),
            "profiles_sha256": hashlib.sha256(b"".join(
                hashlib.sha256(x).digest() for x in raw_rows)).hexdigest(),
            "physical_rotation_authorized": False,
            "ack_authorized": False,
        }
        if (manifest != expected_manifest or
                manifest_raw != _canonical(manifest)):
            raise V2OriginalConfigRefused("learning_rebind_inspector_manifest_mismatch")
        rows = [json.loads(x) for x in raw_rows]
        selected_pending: set[str] = set()
        for i, (number, name, pathname) in enumerate(proof.learning):
            row, first = rows[i], intent["native"][i]
            source_fields = {
                "schema": 3, "kind": "original-learning-native-rebind-profile",
                "generation": proof.generation, "sequence": 0,
                "native_number": number, "hostlist": name, "path": pathname,
                "old_device": first["device"], "old_inode": first["inode"],
                "sealed_end_offset": first["end_offset"],
                "sealed_end_sha256": first["end_sha256"],
                "ack_authorized": False,
            }
            if (raw_rows[i] != _canonical(row) or
                    set(row) != set(source_fields) | {
                        "full_preimage", "replacement", "removed", "pending_name"
                    } or any(row.get(k) != v for k, v in source_fields.items())):
                raise V2OriginalConfigRefused("learning_rebind_inspector_profile_mismatch")
            full, replacement, pending, removed = (
                row["full_preimage"], row["replacement"],
                row["pending_name"], row["removed"])
            if full is None:
                if (replacement is not None or pending is not None or
                        removed != []):
                    raise V2OriginalConfigRefused("learning_rebind_inspector_unselected_changed")
                continue
            if (not isinstance(full, dict) or
                    set(full) != {"size", "sha256"} or
                    type(full["size"]) is not int or
                    not first["end_offset"] <= full["size"] <= 4*1024*1024 or
                    type(full["sha256"]) is not str or
                    re.fullmatch(r"[0-9a-f]{64}", full["sha256"]) is None or
                    not isinstance(replacement, dict) or
                    set(replacement) != {"size", "sha256"} or
                    type(replacement["size"]) is not int or
                    not 0 <= replacement["size"] < full["size"] or
                    type(replacement["sha256"]) is not str or
                    re.fullmatch(r"[0-9a-f]{64}", replacement["sha256"]) is None or
                    type(removed) is not list or
                    not 1 <= len(removed) <= 4096 or
                    any(type(s) is not str for s in removed) or
                    type(pending) is not str or
                    NATIVE_PENDING.fullmatch(pending) is None):
                raise V2OriginalConfigRefused("learning_rebind_inspector_invalid_profile_image")
            digest = hashlib.sha256(
                _canonical({
                    "generation": proof.generation,
                    "native_number": number, "intent": source_sha,
                    "checkpoint": checkpoint_sha,
                    "source": full,
                })).hexdigest()[:32]
            if pending != f"native-{proof.generation}-{number}-{digest}.txt":
                raise V2OriginalConfigRefused("learning_rebind_inspector_pending_not_bound")
            selected_pending.add(pending)
        if {p.name for p in writer.queue.segments()} - selected_pending:
            raise V2OriginalConfigRefused("learning_rebind_inspector_foreign_pending")
        snapshots = {}
        observations = []
        observed_seed_by_name = {}
        for index, (number, name, pathname) in enumerate(proof.learning):
            record = rows[index]
            old = (record["old_device"], record["old_inode"])
            live = Path(pathname)
            if live.parent != writer.queue.root:
                raise V2OriginalConfigRefused("learning_rebind_inspector_foreign_live_root")
            st, data, witness = _native_rebind_stable_snapshot(
                live, writer.receipts.uid, writer.queue.writer_gid,
                allowed_links=(1, 2))
            snapshots[live] = (witness, hashlib.sha256(data).hexdigest())
            end = record["sealed_end_offset"]
            known = record["full_preimage"]
            pending_name = record["pending_name"]
            retained_path = (writer.queue.pending / pending_name
                             if pending_name is not None else None)
            if retained_path is None:
                if ((st.st_dev, st.st_ino) != old or st.st_nlink != 1 or
                        end > len(data) or
                        hashlib.sha256(data[:end]).hexdigest() !=
                        record["sealed_end_sha256"]):
                    raise V2OriginalConfigRefused("learning_rebind_inspector_untouched_profile_drift")
                # Unselected N profiles may also have genuine new native
                # append rows AFTER the first committed cursor slot.
                # They are never silently claimed processed.
                unread = data[end:]
                if unread:
                    _raw_hosts(unread)
                observations.append({
                    "native_number": number, "hostlist": name,
                    "phase": "untouched",
                    "old_tail_size": len(unread),
                    "old_tail_sha256": hashlib.sha256(unread).hexdigest(),
                    "new_tail_size": 0,
                    "new_tail_sha256": hashlib.sha256(b"").hexdigest(),
                    "inode_seed": None,
                })
                continue
            if not retained_path.exists() and not retained_path.is_symlink():
                # This is PREPARED and no hardlink exists, OR the original
                # retained source was lost. A renamed new inode is forbidden.
                if ((st.st_dev, st.st_ino) != old or st.st_nlink != 1 or
                        len(data) != known["size"] or
                        hashlib.sha256(data).hexdigest() != known["sha256"] or
                        end > len(data) or
                        hashlib.sha256(data[:end]).hexdigest() !=
                        record["sealed_end_sha256"]):
                    raise V2OriginalConfigRefused("learning_rebind_inspector_missing_old_pending")
                # The first-slot cursor ended at 'end', NOT at the later
                # full P1 image. P1's compaction snapshot may already
                # contain undiscovered late rows; never mark them read.
                old_tail, new_tail = data[end:], b""
                if old_tail:
                    _raw_hosts(old_tail)
                phase = "prepared-unmodified"
            else:
                pinned, old_data, pinned_witness = _native_rebind_stable_snapshot(
                    retained_path, writer.receipts.uid,
                    writer.queue.writer_gid, allowed_links=(1, 2))
                snapshots[retained_path] = (
                    pinned_witness, hashlib.sha256(old_data).hexdigest())
                if ((pinned.st_dev, pinned.st_ino) != old or
                        len(old_data) < known["size"] or
                        hashlib.sha256(old_data[:known["size"]]).hexdigest() !=
                        known["sha256"] or
                        end > len(old_data) or
                        hashlib.sha256(old_data[:end]).hexdigest() !=
                        record["sealed_end_sha256"]):
                    raise V2OriginalConfigRefused("learning_rebind_inspector_retained_preimage_changed")
                # In particular, rows appended AFTER the original
                # committed source cursor but BEFORE the compaction P1
                # snapshot belong to the still-unprocessed old tail.
                old_tail = old_data[end:]
                if old_tail:
                    _raw_hosts(old_tail)
                if (st.st_dev, st.st_ino) == old:
                    if (st.st_nlink != 2 or pinned.st_nlink != 2 or
                            data != old_data):
                        raise V2OriginalConfigRefused("learning_rebind_inspector_broken_hardlink")
                    phase = ("linked-unreplaced" if not old_tail
                             else "linked-source-grew")
                    new_tail = b""
                else:
                    if st.st_nlink != 1 or pinned.st_nlink != 1:
                        raise V2OriginalConfigRefused("learning_rebind_inspector_unexpected_post_swap_links")
                    after = record["replacement"]
                    if (len(data) < after["size"] or
                            hashlib.sha256(data[:after["size"]]).hexdigest() !=
                            after["sha256"]):
                        raise V2OriginalConfigRefused("learning_rebind_inspector_new_live_image_diverged")
                    # The replacement may include rows copied from the
                    # old unprocessed tail; no proof that ANY of those
                    # rows were processed in this cursor slot. Seed the
                    # new physical inode at ZERO, never at postimage end.
                    # Future original P1/ACK must deduplicate/reconcile
                    # cross-inode observations rather than skip them.
                    new_tail = data
                    if new_tail:
                        _raw_hosts(new_tail)
                    phase = ("replaced-retained" if not old_tail and not new_tail
                             else "replaced-with-unprocessed-tails")
            # This is ONLY the durable physical inode BASELINE.
            # The old unprocessed tail starts at original FIRST-SLOT end,
            # not the later P1 full preimage boundary. The NEW file's
            # initial replacement may itself contain unprocessed old rows,
            # therefore NEW cursor starts at ZERO. Both tails remain
            # UNPROCESSED after the seed is written.
            inode_seed = None
            if phase.startswith("replaced-"):
                inode_seed = {
                    "schema": 3,
                    "kind": "original-learning-native-inode-seed",
                    "generation": proof.generation,
                    "sequence": 0,
                    "native_number": number,
                    "hostlist": name,
                    "live_path": pathname,
                    "manifest_sha256": hashlib.sha256(
                        manifest_raw).hexdigest(),
                    "old_pending_name": pending_name,
                    "old_pending_inode": {
                        "device": old[0], "inode": old[1],
                        "cut_offset": end,
                        "cut_sha256": record["sealed_end_sha256"],
                    },
                    "old_pending_proven_preimage": known,
                    "new_live_inode": {
                        "device": st.st_dev, "inode": st.st_ino,
                        "cut_offset": 0,
                        "cut_sha256": hashlib.sha256(b"").hexdigest(),
                    },
                    "new_live_proven_postimage": record["replacement"],
                    "cursor_advanced": False,
                    "ack_authorized": False,
                }
                observed_seed_by_name[f"{number:03d}.json"] = inode_seed
            observations.append({
                "native_number": number,
                "hostlist": name, "phase": phase,
                "old_tail_size": len(old_tail),
                "old_tail_sha256": hashlib.sha256(old_tail).hexdigest(),
                "new_tail_size": len(new_tail),
                "new_tail_sha256": hashlib.sha256(new_tail).hexdigest(),
                "inode_seed": inode_seed,
            })
        # If any previous original write-once physical seeds exist,
        # verify EACH against the exact live/retained inode and manifest.
        # A stale seeded profile cannot be silently re-rooted after
        # restart or an unexpected second rename.
        observed_folder = folder / "observed"
        if observed_folder.exists() or observed_folder.is_symlink():
            _directory(observed_folder, writer.receipts.uid)
            observed_names = set(os.listdir(observed_folder))
            if not observed_names.issubset(observed_seed_by_name):
                raise V2OriginalConfigRefused(
                    "learning_rebind_inspector_foreign_or_stale_seed")
            for seed_name in observed_names:
                if _read(observed_folder / seed_name,
                         writer.receipts.uid) != _canonical(
                             observed_seed_by_name[seed_name]):
                    raise V2OriginalConfigRefused(
                        "learning_rebind_inspector_prior_seed_drift")
        # Re-attest all N files (including retained hardlinks) at the end,
        # NOT just the last profile: dvtws2 can append without P2a lock.
        if {p.name for p in writer.queue.segments()} - selected_pending:
            raise V2OriginalConfigRefused("learning_rebind_inspector_pending_changed")
        for path, (witness, sha) in snapshots.items():
            _, content, after = _native_rebind_stable_snapshot(
                path, writer.receipts.uid, writer.queue.writer_gid,
                allowed_links=(1, 2))
            if witness != after or hashlib.sha256(content).hexdigest() != sha:
                raise V2OriginalConfigRefused("learning_rebind_inspector_all_n_race")
        held()
        return {
            "schema": 3,
            "kind": "original-learning-native-rebind-inspection",
            "generation": proof.generation,
            "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "profiles": observations,
            "physical_rotation_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, OriginalLockRefused, DestinationRefused,
            OwnedSourcesRefused, EffectiveKnownRefused, QueueSafetyError,
            DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "learning_rebind_original_physical_inspection_refused") from exc


def seal_original_learning_post_inode_seed_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
) -> dict:
    """Write-once original per-N post-rename inode baseline, never tail ACK.

    Records live INSIDE the original first-slot native-rebind/observed
    journal. They prove that the expected native postimage is now at an
    actual new inode, while the ORIGINAL old inode remains in P2a pending.
    The old cut offset is the committed FIRST native source slot end,
    and the NEW native inode always begins at offset ZERO. The expected
    complete preimage and replacement remain independent verified image
    witnesses, NOT cursor advances. Every newer/unclaimed row (even one
    already copied into the replacement) is UNPROCESSED.

    A crash after any individual write is recoverable solely by the
    original manifest/owner and an identical live inode; a later append
    is tolerated, but a second rename or lost old pending is refused.
    This import-only primitive MUST NOT call rotate(), unlink(), ACK or
    the installed minute/Apply/launcher.
    """
    import os
    from auto_detect_epoch_receipts import (
        _canonical, _directory, _write_once, _sync,
    )
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_queue import QueueSafetyError

    def qualified_owner():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused(
                "learning_inode_seed_original_owner_changed")
    try:
        # The inspector checks genuine original P2a+GUI+Config FD4,
        # source/checkpoint/manifest, all N live and pending inodes, then
        # reads them ALL a second time for concurrent native appends.
        before = inspect_original_learning_native_rebind_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest)
        seeds = {
            f'{row["native_number"]:03d}.json': row["inode_seed"]
            for row in before["profiles"] if row["inode_seed"] is not None
        }
        if (not seeds or
                before["physical_rotation_authorized"] is not False or
                before["ack_authorized"] is not False):
            raise V2OriginalConfigRefused(
                "learning_inode_seed_no_proven_physical_rotation")
        slot = (writer.receipts.root / proof.generation /
                "cursor-chain-v2" / "00000000")
        folder = slot / "native-rebind"
        _directory(folder, writer.receipts.uid)
        observed = folder / "observed"
        qualified_owner()
        if observed.exists() or observed.is_symlink():
            _directory(observed, writer.receipts.uid)
        else:
            observed.mkdir(mode=0o700)
            _sync(folder)
        names = set(os.listdir(observed))
        if names - set(seeds):
            raise V2OriginalConfigRefused(
                "learning_inode_seed_foreign_or_replaced_profile")
        for name, row in seeds.items():
            if name in names and _read(
                    observed / name, writer.receipts.uid) != _canonical(row):
                raise V2OriginalConfigRefused(
                    "learning_inode_seed_previous_inode_changed")
        qualified_owner()
        for name, row in sorted(seeds.items()):
            _write_once(observed, name, _canonical(row),
                        writer.receipts.uid)
        # Late append may grow either inode after the first cut: it is
        # deliberately NOT an alteration of the immutable cursor BASE.
        # Recheck all N and prior recorded seeds before reporting success.
        after = inspect_original_learning_native_rebind_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest)
        if (after["manifest_sha256"] != before["manifest_sha256"] or
                {f'{row["native_number"]:03d}.json': row["inode_seed"]
                 for row in after["profiles"] if row["inode_seed"] is not None}
                != seeds or
                set(os.listdir(observed)) != set(seeds)):
            raise V2OriginalConfigRefused(
                "learning_inode_seed_changed_during_commit")
        qualified_owner()
        return {
            "schema": 3,
            "kind": "original-learning-post-inode-seeded",
            "generation": proof.generation,
            "manifest_sha256": after["manifest_sha256"],
            "seeds": len(seeds),
            "cursor_advanced": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, OriginalLockRefused,
            DestinationRefused, QueueSafetyError) as exc:
        raise V2OriginalConfigRefused(
            "learning_inode_seed_original_transaction_refused") from exc


def preview_original_learning_forward_windows_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
        sealed_window: dict | None = None,
) -> dict:
    """Read-only original P2a/FD4/FD9/P2b cross-N forward native cut.

    The FIRST committed source cursor, not P1's later full native snapshot,
    defines unread OLD-pending bytes. Every NEW live inode is unread from
    offset ZERO. Duplicated copies between old/native are folded by exact
    native profile/hostlist/hostname, and ONLY a strictly matching genuine
    later positive debug event can qualify a distinct unprocessed domain.
    Never attribute based on hostname, list filename, PSL or debug alone.

    No independent queue, Config owner, P1 writer, new epoch, ACK, cursor
    fsync, hostlist edit or production minute invocation exists here.
    The original destination/active checkpoint and all N post-rename seeds
    must already be durable. Source-only until a forward WAL transaction
    and actual same-engine native/P2b retirement are implemented.
    """
    import os
    import sys
    from auto_detect_epoch_receipts import _canonical, _directory
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_queue import QueueSafetyError, MAX_SEGMENT
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_fd import FDState
    from auto_detect_debug_window import (
        _read_exact, _raw_hosts, _hostname, ADD,
        MAX_WINDOW, MAX_RAW, MAX_EVENTS,
    )

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sealed_window is not None and (
                type(sealed_window) is not dict or
                set(sealed_window) != {"debug", "native"} or
                type(sealed_window.get("debug")) is not dict or
                type(sealed_window.get("native")) is not list or
                len(sealed_window["native"]) != len(proof.learning))) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or writer.receipts.uid != 0 or
              writer.queue.uid != 0)) or attest() != proof):
        raise V2OriginalConfigRefused(
            "learning_forward_original_fd4_fd9_owner_required")
    uid, gid = writer.receipts.uid, writer.queue.writer_gid

    def held() -> None:
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH else uid)
        if attest() != proof:
            raise V2OriginalConfigRefused("learning_forward_owner_changed")

    def read_candidate() -> dict:
        forward_plan_present = (
            (writer.receipts.root / proof.generation /
             "cursor-chain-v2" / "00000001" /
             "destination" / "plan.json").exists())
        original = inspect_original_learning_native_rebind_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest,
            forward_wal_source=forward_plan_present)
        if (original["ack_authorized"] is not False or
                original["physical_rotation_authorized"] is not False or
                len(original["profiles"]) != len(proof.learning)):
            raise V2OriginalConfigRefused("learning_forward_original_inspection_unqualified")
        slot = (writer.receipts.root / proof.generation /
                "cursor-chain-v2" / "00000000")
        folder = slot / "native-rebind"
        observed = folder / "observed"
        _directory(observed, uid)
        intent_raw = _read(slot / "intent.json", uid)
        intent = json.loads(intent_raw)
        manifest = _read(folder / "manifest.json", uid)
        if (original["manifest_sha256"] != hashlib.sha256(manifest).hexdigest() or
                intent.get("schema") != 3 or
                intent.get("generation") != proof.generation or
                len(intent["native"]) != len(proof.learning)):
            raise V2OriginalConfigRefused("learning_forward_original_intent_changed")
        original_debug_end = intent["debug_end_offset"]
        debug_path = writer.queue.root / "debug.log"
        debug_stat, debug_bytes = _read_exact(
            debug_path, owner_uid=uid, writer_gid=gid)
        if ((debug_stat.st_dev, debug_stat.st_ino) !=
                (intent["debug_device"], intent["debug_inode"]) or
                type(original_debug_end) is not int or
                not 0 <= original_debug_end <= len(debug_bytes) or
                hashlib.sha256(debug_bytes[:original_debug_end]).hexdigest()
                != intent["debug_end_sha256"] or
                (debug_bytes and not debug_bytes.endswith(b"\n"))):
            raise V2OriginalConfigRefused("learning_forward_original_debug_cursor_drift")
        # On replay, the first durable second-slot intent pins the
        # historical end. NEW writes AFTER the sealed end must not be
        # stolen into the already prepared forward transaction.
        frozen_debug = (sealed_window["debug"] if sealed_window is not None
                        else None)
        debug_end = (frozen_debug["end"] if frozen_debug is not None
                     else len(debug_bytes))
        if (type(debug_end) is not int or
                not original_debug_end <= debug_end <= len(debug_bytes)):
            raise V2OriginalConfigRefused("learning_forward_frozen_debug_cut_invalid")
        later_debug = debug_bytes[original_debug_end:debug_end]
        if len(later_debug) > MAX_WINDOW:
            raise V2OriginalConfigRefused("learning_forward_debug_window_limit")
        # Retain an exact immutable cursor for each native inode, including
        # the ORIGINAL old pending even when a write occurred before P1's
        # full-image compaction snapshot, and the NEW live at ZERO.
        pinned_sources = [(debug_path, debug_stat.st_dev, debug_stat.st_ino)]
        native_cursors = []
        seen_raw: dict[tuple[int, str, str], set[str]] = {}
        previously_processed: set[tuple[int, str, str]] = set()
        candidate_unique: set[tuple[int, str, str]] = set()
        total_unread = 0
        native_by_debug_path = {}
        for index, (number, name, pathname) in enumerate(proof.learning):
            first = intent["native"][index]
            physical = original["profiles"][index]
            if ((first["native_number"], first["hostlist"], first["path"]) !=
                    (number, name, pathname) or
                    (physical["native_number"], physical["hostlist"]) !=
                    (number, name)):
                raise V2OriginalConfigRefused("learning_forward_changed_native_map")
            path = Path(pathname)
            if path.parent != writer.queue.root or path in native_by_debug_path:
                raise V2OriginalConfigRefused("learning_forward_foreign_profile_path")
            native_by_debug_path[pathname] = (number, name)
            live_st, live_data, _ = _native_rebind_stable_snapshot(
                path, uid, gid, allowed_links=(1,))
            pinned_sources.append((path, live_st.st_dev, live_st.st_ino))
            prior_end = first["end_offset"]
            expected_old = (first["device"], first["inode"])
            seed_name = f"{number:03d}.json"
            path_old = None
            if physical["phase"] == "untouched":
                if (seed_name in os.listdir(observed) or
                        (live_st.st_dev, live_st.st_ino) != expected_old or
                        prior_end > len(live_data) or
                        hashlib.sha256(live_data[:prior_end]).hexdigest() !=
                        first["end_sha256"]):
                    raise V2OriginalConfigRefused("learning_forward_untouched_source_changed")
                frozen = (sealed_window["native"][index]
                          if sealed_window is not None else None)
                old_end = (frozen["old_end"] if frozen is not None
                           else len(live_data))
                if (type(old_end) is not int or
                        not prior_end <= old_end <= len(live_data)):
                    raise V2OriginalConfigRefused("learning_forward_frozen_old_live_cut_invalid")
                old_prefix, old_tail, new_rows = (
                    live_data[:prior_end], live_data[prior_end:old_end], b"")
                native_cursors.append({
                    "native_number": number, "hostlist": name,
                    "old_path": pathname, "old_device": live_st.st_dev,
                    "old_inode": live_st.st_ino, "old_start": prior_end,
                    "old_end": old_end,
                    "old_end_sha256": hashlib.sha256(
                        live_data[:old_end]).hexdigest(),
                    "new_path": None, "new_device": None, "new_inode": None,
                    "new_start": None, "new_end": None,
                    "new_end_sha256": None,
                })
            elif physical["phase"].startswith("replaced-"):
                seed_raw = _read(observed / seed_name, uid)
                seed = json.loads(seed_raw)
                if (seed_raw != _canonical(physical["inode_seed"]) or
                        seed != physical["inode_seed"] or
                        seed["manifest_sha256"] != original["manifest_sha256"] or
                        seed["old_pending_inode"]["cut_offset"] != prior_end or
                        seed["old_pending_inode"]["cut_sha256"] !=
                        first["end_sha256"] or
                        seed["new_live_inode"]["cut_offset"] != 0 or
                        seed["new_live_inode"]["cut_sha256"] !=
                        hashlib.sha256(b"").hexdigest() or
                        (live_st.st_dev, live_st.st_ino) !=
                        (seed["new_live_inode"]["device"],
                         seed["new_live_inode"]["inode"])):
                    raise V2OriginalConfigRefused("learning_forward_unqualified_inode_seed")
                path_old = writer.queue.pending / seed["old_pending_name"]
                if path_old not in writer.queue.segments():
                    raise V2OriginalConfigRefused("learning_forward_old_pending_not_retained")
                old_st, old_data, _ = _native_rebind_stable_snapshot(
                    path_old, uid, gid, allowed_links=(1,))
                if ((old_st.st_dev, old_st.st_ino) != expected_old or
                        prior_end > len(old_data) or
                        hashlib.sha256(old_data[:prior_end]).hexdigest() !=
                        first["end_sha256"]):
                    raise V2OriginalConfigRefused("learning_forward_old_preimage_mismatch")
                pinned_sources.append((path_old, old_st.st_dev, old_st.st_ino))
                frozen = (sealed_window["native"][index]
                          if sealed_window is not None else None)
                old_end = (frozen["old_end"] if frozen is not None
                           else len(old_data))
                new_end = (frozen["new_end"] if frozen is not None
                           else len(live_data))
                if (type(old_end) is not int or type(new_end) is not int or
                        not prior_end <= old_end <= len(old_data) or
                        not 0 <= new_end <= len(live_data)):
                    raise V2OriginalConfigRefused("learning_forward_frozen_rebound_cut_invalid")
                old_prefix, old_tail, new_rows = (
                    old_data[:prior_end], old_data[prior_end:old_end],
                    live_data[:new_end])
                native_cursors.append({
                    "native_number": number, "hostlist": name,
                    "old_path": str(path_old), "old_device": old_st.st_dev,
                    "old_inode": old_st.st_ino, "old_start": prior_end,
                    "old_end": old_end,
                    "old_end_sha256": hashlib.sha256(
                        old_data[:old_end]).hexdigest(),
                    "new_path": pathname, "new_device": live_st.st_dev,
                    "new_inode": live_st.st_ino, "new_start": 0,
                    "new_end": new_end,
                    "new_end_sha256": hashlib.sha256(
                        live_data[:new_end]).hexdigest(),
                })
            else:
                # PREPARED / linked-unreplaced is not a qualified second
                # post-rename source cut. Never silently treat old aliases
                # as independent native cursors.
                raise V2OriginalConfigRefused("learning_forward_incomplete_native_rebind")
            if (sealed_window is not None and
                    native_cursors[-1] != sealed_window["native"][index]):
                raise V2OriginalConfigRefused("learning_forward_frozen_native_cursor_changed")
            total_unread += len(old_tail) + len(new_rows)
            if total_unread > MAX_RAW:
                raise V2OriginalConfigRefused("learning_forward_native_raw_window_limit")
            # First-slot observations are already accounted. Reading a
            # new physical image must not replay those entries as a new
            # discovery; all other new distinct rows still need debug.
            prior_hosts = _raw_hosts(old_prefix) if old_prefix else []
            unread_old = _raw_hosts(old_tail) if old_tail else []
            unread_new = _raw_hosts(new_rows) if new_rows else []
            for host in prior_hosts:
                previously_processed.add((number, name, host))
            for host in unread_old:
                seen_raw.setdefault((number, name, host), set()).add("old")
            for host in unread_new:
                seen_raw.setdefault((number, name, host), set()).add("new")
        for key in seen_raw:
            if key not in previously_processed:
                candidate_unique.add(key)
        # Exact post-first-slot positive provenance, never spelling or
        # copying a late raw line from one inode into the other.
        debug_unique = set()
        for line in later_debug.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                raise V2OriginalConfigRefused("learning_forward_incomplete_debug_line")
            try:
                event_text = line[:-1].decode("ascii")
            except UnicodeError as exc:
                raise V2OriginalConfigRefused(
                    "learning_forward_debug_not_ascii") from exc
            if " : adding to " not in event_text:
                continue
            match = ADD.fullmatch(event_text)
            if match is None or not _hostname(match["host"]):
                raise V2OriginalConfigRefused("learning_forward_unqualified_positive")
            profile = native_by_debug_path.get(match["path"])
            if profile is None or int(match["profile"]) != profile[0]:
                raise V2OriginalConfigRefused("learning_forward_foreign_positive")
            key = (profile[0], profile[1], match["host"])
            if key not in seen_raw:
                # Debug was emitted BEFORE native append: cannot use it
                # to advance, especially on an unpaired/foreign profile.
                raise V2OriginalConfigRefused("learning_forward_debug_not_in_native")
            debug_unique.add(key)
            if len(debug_unique) > MAX_EVENTS:
                raise V2OriginalConfigRefused("learning_forward_event_limit")
        if not candidate_unique.issubset(debug_unique):
            raise V2OriginalConfigRefused("learning_forward_native_lacks_debug_provenance")
        # Every duplicate old/new row has one authenticated original
        # profile; never collapse across YouTube and User.
        observations = [
            {"hostname": host, "hostlist": name}
            for number, name, host in sorted(candidate_unique)
        ]
        return {
            "generation": proof.generation,
            "first_slot_sha256": hashlib.sha256(intent_raw).hexdigest(),
            "manifest_sha256": original["manifest_sha256"],
            "debug": {
                "device": debug_stat.st_dev, "inode": debug_stat.st_ino,
                "start": original_debug_end,
                "start_sha256": intent["debug_end_sha256"],
                "end": debug_end,
                "end_sha256": hashlib.sha256(
                    debug_bytes[:debug_end]).hexdigest(),
            },
            "native": native_cursors,
            # Preserve exact profile provenance before the normal P1
            # projection loses N (two YouTube learning clones may
            # discover the SAME hostname independently).
            "native_observations": [
                {"native_number": number, "hostlist": name,
                 "hostname": host}
                for number, name, host in sorted(candidate_unique)],
            "observations": observations,
            "deduped_cross_inode": sum(
                1 for key, paths in seen_raw.items()
                if len(paths) == 2 and key not in previously_processed),
            "sources": pinned_sources,
            "p2b_drained": False,
            "commit_authorized": False,
            "ack_authorized": False,
        }

    try:
        held()
        before = read_candidate()
        if (sealed_window is not None and
                (before["debug"] != sealed_window["debug"] or
                 before["native"] != sealed_window["native"])):
            raise V2OriginalConfigRefused("learning_forward_frozen_window_changed")
        # Independently probe the ORIGINAL P2b whole-machine FD state of
        # ALL original native paths, retained pending and debug inode.
        # Busy old dvtws2 FDs cause a REFUSAL, not SIGSTOP/SIGCONT.
        for path, device, inode in before["sources"]:
            if (attest() != proof or
                    inspect(path, device, inode, owner=proof.owner,
                            writer_gid=gid) is not FDState.DRAINED or
                    attest() != proof):
                raise V2OriginalConfigRefused("learning_forward_original_p2b_not_drained")
        after = read_candidate()
        if before != after:
            raise V2OriginalConfigRefused("learning_forward_changed_during_p2b")
        held()
        result = {key: value for key, value in after.items()
                  if key != "sources"}
        result["p2b_drained"] = True
        return result
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, OriginalLockRefused, QueueSafetyError,
            DestinationRefused, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused("learning_forward_original_window_refused") from exc


def _original_learning_forward_progress_record(
        intent: dict, source_raw: bytes, checkpoint_raw: bytes,
        checkpoint: dict) -> dict:
    """One durable cursor tip over the ORIGINAL N receipts, never a native ACK.

    The second-slot per-N records carry every old/new inode cut. Their
    ordered SHA/count and the committed original P2k2b checkpoint are the
    only source of cursor authority; do not copy a possibly newer live size.
    """
    return {
        "schema": 3, "kind": "original-learning-forward-cursor-progress",
        "generation": intent["generation"], "sequence": 1,
        "owner_pid": intent["owner_pid"],
        "owner_start": intent["owner_start"],
        "operation_id": intent["operation_id"],
        "native_map_sha256": intent["native_map_sha256"],
        "first_slot_sha256": intent["first_slot_sha256"],
        "native_rebind_manifest_sha256":
            intent["native_rebind_manifest_sha256"],
        "source_intent_sha256": hashlib.sha256(source_raw).hexdigest(),
        "destination_plan_sha256": checkpoint["plan_sha256"],
        "destination_checkpoint_sha256":
            hashlib.sha256(checkpoint_raw).hexdigest(),
        "profiles_count": intent["profiles_count"],
        "native_cursor_receipts_sha256": intent["profiles_sha256"],
        "debug": intent["debug"],
        "cursor_advanced": True, "native_pending_ack_authorized": False,
        "native_cleanup_authorized": False, "generation_retired": False,
    }


def prepare_original_learning_forward_second_slot_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Seal ONE immutable original post-native forward source slot, no P1.

    Existing original P2a+GUI+Config FD4+FD9/P2b are the only authorities.
    This is cursor-chain-v2/00000001, NOT a second queue or process owner.
    Per-N write-once receipts are staged FIRST; the one aggregate intent is
    published LAST. That intent binds an exact source and debug window,
    all-N cursor SHA and the hash of the COMPLETE attributed observations.

    After the aggregate intent is written, recovery reattests ONLY those
    exact old/new native prefix cuts and debug cut, even if dvtws2 appended
    more bytes afterwards. Later bytes cannot silently join this WAL.
    Before intent exists, conflicting partial records fail closed rather
    than consuming any new rows to impersonate the interrupted window.
    No cursor advancement, P1, Found, active rewrite, ACK or product hook.
    """
    import os
    import sys
    from auto_detect_epoch_receipts import (
        _canonical, _directory, _read, _write_once, _sync,
    )
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_queue import QueueSafetyError

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or writer.receipts.uid != 0 or
              writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused(
            "learning_second_slot_original_fd4_fd9_required")

    def held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused("learning_second_slot_owner_changed")

    def observation_digest(rows):
        # One single canonical stream hash, even when 4096 observations
        # would exceed the 16 KiB limit of any INDIVIDUAL private receipt.
        return hashlib.sha256(json.dumps(
            rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def profile_records(candidate):
        if (type(candidate.get("native")) is not list or
                len(candidate["native"]) != len(proof.learning)):
            raise V2OriginalConfigRefused("learning_second_slot_invalid_native_count")
        packed = []
        for i, (number, name, pathname) in enumerate(proof.learning):
            cursor = candidate["native"][i]
            if (cursor.get("native_number") != number or
                    cursor.get("hostlist") != name or
                    cursor.get("new_path") not in (None, pathname)):
                raise V2OriginalConfigRefused("learning_second_slot_native_profile_drift")
            rec = {
                "schema": 3,
                "kind": "original-learning-forward-native-cut",
                "generation": proof.generation, "sequence": 1,
                "first_slot_sha256": candidate["first_slot_sha256"],
                "manifest_sha256": candidate["manifest_sha256"],
                "native_number": number, "hostlist": name,
                "cursor": cursor,
                "cursor_advanced": False, "ack_authorized": False,
            }
            packed.append((f"{number:03d}.json", _canonical(rec)))
        return packed

    def intent_for(candidate, packed):
        return {
            "schema": 3,
            "kind": "original-learning-forward-second-slot-prepared",
            "generation": proof.generation,
            "sequence": 1,
            "owner_pid": proof.owner.pid,
            "owner_start": proof.owner.started,
            "operation_id": proof.operation_id,
            "owner_candidate_sha256": proof.owner_candidate_sha256,
            "final_args_sha256": proof.final_args_sha256,
            "native_map_sha256": proof.native_map_sha256,
            "first_slot_sha256": candidate["first_slot_sha256"],
            "native_rebind_manifest_sha256": candidate["manifest_sha256"],
            "debug": candidate["debug"],
            "profiles_count": len(packed),
            "profiles_sha256": hashlib.sha256(b"".join(
                hashlib.sha256(raw).digest() for _, raw in packed)).hexdigest(),
            "observations_count": len(candidate["observations"]),
            "observations_sha256": observation_digest(
                candidate["observations"]),
            # The original P2k2b DestinationCommit consumes the exact
            # immutable observation stream. A digest alone is NOT enough
            # to reconstruct P1 after a partial Found/managed CAS crash.
            # The existing 16 KiB original receipt bound refuses large
            # batches, retaining every source byte for a smaller future cut.
            "observations": candidate["observations"],
            "deduped_cross_inode": candidate["deduped_cross_inode"],
            "cursor_advanced": False,
            "commit_authorized": False,
            "ack_authorized": False,
        }

    try:
        held()
        chain = (writer.receipts.root / proof.generation /
                 "cursor-chain-v2")
        _directory(chain, writer.receipts.uid)
        names = set(os.listdir(chain))
        if names not in (
                {"00000000"}, {"00000000", "00000001"},
                {"00000000", "00000001", "00000002"}):
            raise V2OriginalConfigRefused("learning_second_slot_foreign_chain")
        if "00000002" in names and not (
                (chain / "00000001" / "cursor-progress.json").exists() and
                (chain / "00000001" / "destination" /
                 "checkpoint.json").exists()):
            # The new folder does NOT authorize a partially committed
            # or entirely missing second-slot cursor checkpoint.
            raise V2OriginalConfigRefused(
                "learning_third_slot_requires_second_progress")
        slot = chain / "00000001"
        if slot.exists() or slot.is_symlink():
            _directory(slot, writer.receipts.uid)
            if set(os.listdir(slot)) - {
                    "native", "intent.json", "destination",
                    "cursor-progress.json"}:
                raise V2OriginalConfigRefused("learning_second_slot_foreign_journal")
            if (slot / "cursor-progress.json").exists() or (
                    slot / "cursor-progress.json").is_symlink():
                if not (slot / "destination" / "checkpoint.json").exists():
                    raise V2OriginalConfigRefused(
                        "learning_second_slot_progress_without_checkpoint")
            if ((slot / "destination").exists() or
                    (slot / "destination").is_symlink()):
                _directory(slot / "destination", writer.receipts.uid)
                if "intent.json" not in os.listdir(slot) or (
                        set(os.listdir(slot / "destination")) -
                        {"plan.json", "checkpoint.json"}):
                    raise V2OriginalConfigRefused(
                        "learning_second_slot_destination_before_source_intent")
        else:
            slot.mkdir(mode=0o700)
            _sync(chain)
        native = slot / "native"
        if native.exists() or native.is_symlink():
            _directory(native, writer.receipts.uid)
        else:
            if (slot / "intent.json").exists():
                raise V2OriginalConfigRefused("learning_second_slot_manifest_without_native")
            native.mkdir(mode=0o700)
            _sync(slot)

        existing = slot / "intent.json"
        if existing.exists() or existing.is_symlink():
            # Intent is the ONLY complete transition. Never rebuild it
            # from a newer source, even when the appenders have continued.
            record_raw = _read(existing, writer.receipts.uid)
            record = json.loads(record_raw)
            rows = []
            expected_names = []
            for number, _, _ in proof.learning:
                receipt_name = f"{number:03d}.json"
                expected_names.append(receipt_name)
                data = _read(native / receipt_name, writer.receipts.uid)
                row = json.loads(data)
                if (type(row) is not dict or
                        row.get("schema") != 3 or
                        row.get("kind") != "original-learning-forward-native-cut" or
                        row.get("generation") != proof.generation or
                        row.get("sequence") != 1 or
                        row.get("native_number") != number or
                        row.get("cursor_advanced") is not False or
                        row.get("ack_authorized") is not False or
                        data != _canonical(row)):
                    raise V2OriginalConfigRefused("learning_second_slot_corrupt_native_record")
                rows.append(row)
            slot_names = set(os.listdir(slot))
            if (not {"native", "intent.json"}.issubset(slot_names) or
                    slot_names - {"native", "intent.json", "destination",
                                  "cursor-progress.json"} or
                    ("cursor-progress.json" in slot_names and
                     "destination" not in slot_names) or
                    set(os.listdir(native)) != set(expected_names) or
                    record_raw != _canonical(record)):
                raise V2OriginalConfigRefused("learning_second_slot_incomplete_sealed_journal")
            frozen = {
                "debug": record["debug"],
                "native": [row["cursor"] for row in rows],
            }
            replay = preview_original_learning_forward_windows_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect,
                sealed_window=frozen)
            packed = profile_records(replay)
            for (name, raw), row in zip(packed, rows):
                if _canonical(row) != raw:
                    raise V2OriginalConfigRefused(
                        "learning_second_slot_replayed_profile_changed")
            if record != intent_for(replay, packed):
                raise V2OriginalConfigRefused(
                    "learning_second_slot_original_manifest_drift")
            if "cursor-progress.json" in slot_names:
                # Cursor progress is meaningful ONLY after the same
                # original destination WAL completed. A foreign or
                # partially committed checkpoint never advances N.
                _, plan_raw = qualified_destination_plan(
                    slot, record, writer.receipts.uid,
                    targets=writer.targets)
                cp_raw = _read(
                    slot / "destination" / "checkpoint.json",
                    writer.receipts.uid)
                cp = json.loads(cp_raw)
                expected_cp = {
                    "schema": 1,
                    "kind": "destination-and-cursor-committed",
                    "generation": proof.generation,
                    "pending_name": "learning-00000001",
                    "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
                    "evidence": "learning-native-debug",
                    "committed_cursor_offset": record["debug"]["end"],
                    "committed_cursor_sha256":
                        record["debug"]["end_sha256"],
                    "ack_authorized": False,
                }
                if (cp != expected_cp or cp_raw != _canonical(cp) or
                        _read(slot / "cursor-progress.json",
                              writer.receipts.uid) != _canonical(
                                  _original_learning_forward_progress_record(
                                      record, record_raw, cp_raw, cp))):
                    raise V2OriginalConfigRefused(
                        "learning_second_slot_progress_not_source_bound")
            held()
            return {
                "generation": proof.generation,
                "sequence": 1, "slot": str(slot),
                "intent_sha256": hashlib.sha256(record_raw).hexdigest(),
                "profiles_count": len(packed),
                "observations_count": len(replay["observations"]),
                "cursor_advanced": False, "commit_authorized": False,
                "ack_authorized": False,
            }

        candidate = preview_original_learning_forward_windows_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (not candidate["observations"] or
                candidate["p2b_drained"] is not True or
                candidate["commit_authorized"] is not False or
                candidate["ack_authorized"] is not False):
            raise V2OriginalConfigRefused("learning_second_slot_no_proven_observations")
        packed = profile_records(candidate)
        allowed = {name for name, _ in packed}
        existing_records = set(os.listdir(native))
        if existing_records - allowed:
            raise V2OriginalConfigRefused("learning_second_slot_foreign_profile_receipt")
        for name, raw in packed:
            if name in existing_records and _read(
                    native / name, writer.receipts.uid) != raw:
                raise V2OriginalConfigRefused(
                    "learning_second_slot_interrupted_source_conflict")
        prepared = _canonical(intent_for(candidate, packed))
        held()
        for name, raw in packed:
            _write_once(native, name, raw, writer.receipts.uid)
        # A native append AFTER individual per-N write-once receipts is
        # safe ONLY when the exact ORIGINAL snapshot can be reattested.
        # New bytes are deliberately excluded from this immutable intent.
        second = preview_original_learning_forward_windows_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect,
            sealed_window={"debug": candidate["debug"],
                           "native": candidate["native"]})
        if (second != candidate or
                set(os.listdir(native)) != allowed):
            raise V2OriginalConfigRefused(
                "learning_second_slot_prefix_changed_before_manifest")
        held()
        _write_once(slot, "intent.json", prepared, writer.receipts.uid)
        if (set(os.listdir(slot)) != {"native", "intent.json"} or
                _read(existing, writer.receipts.uid) != prepared):
            raise V2OriginalConfigRefused(
                "learning_second_slot_aggregate_intent_not_durable")
        return {
            "generation": proof.generation,
            "sequence": 1, "slot": str(slot),
            "intent_sha256": hashlib.sha256(prepared).hexdigest(),
            "profiles_count": len(packed),
            "observations_count": len(candidate["observations"]),
            "cursor_advanced": False, "commit_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, OriginalLockRefused, QueueSafetyError,
            DestinationRefused, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "learning_second_slot_original_source_or_journal_refused") from exc


def seal_original_learning_forward_progress_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Advance the ORIGINAL durable per-N cursor tip after second P2k2b.

    SOURCE ONLY: the caller already holds original P2a, GUI/Found and
    inherited PHP Config FD4; FD9/epoch and ALL native/debug P2b drains
    are reattested by the existing second-slot source replay. The source
    cuts are immutable even if both old pending and new live later grow.
    Progress is not permission to unlink pending, compact live native
    files, ACK the producer or retire a generation. No second queue,
    Config writer, daemon, Apply or service restart is introduced.
    """
    import sys
    from auto_detect_epoch_receipts import _canonical, _write_once
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_queue import QueueSafetyError
    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or
            not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or writer.receipts.uid != 0 or
              writer.queue.uid != 0)) or attest() != proof):
        raise V2OriginalConfigRefused(
            "learning_forward_progress_original_fd4_fd9_required")

    def held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused(
                "learning_forward_progress_owner_changed")

    try:
        held()
        prepared = prepare_original_learning_forward_second_slot_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        slot = Path(prepared["slot"])
        source_raw = _read(slot / "intent.json", writer.receipts.uid)
        source = json.loads(source_raw)
        if (prepared["sequence"] != 1 or
                prepared["intent_sha256"] !=
                hashlib.sha256(source_raw).hexdigest() or
                source.get("kind") !=
                "original-learning-forward-second-slot-prepared" or
                source.get("generation") != proof.generation or
                source.get("cursor_advanced") is not False or
                source.get("ack_authorized") is not False):
            raise V2OriginalConfigRefused(
                "learning_forward_progress_source_not_sealed")
        plan, plan_raw = qualified_destination_plan(
            slot, source, writer.receipts.uid, targets=writer.targets)
        cp_raw = _read(
            slot / "destination" / "checkpoint.json",
            writer.receipts.uid)
        checkpoint = json.loads(cp_raw)
        expected_cp = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": proof.generation,
            "pending_name": "learning-00000001",
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "evidence": "learning-native-debug",
            "committed_cursor_offset": source["debug"]["end"],
            "committed_cursor_sha256": source["debug"]["end_sha256"],
            "ack_authorized": False,
        }
        if (checkpoint != expected_cp or
                cp_raw != _canonical(checkpoint) or
                plan.get("schema") != 3 or "live" not in plan):
            raise V2OriginalConfigRefused(
                "learning_forward_progress_checkpoint_not_committed")

        # A completed journal is not enough if GUI/managed has since
        # changed. Observe EVERY second-slot destination after-image,
        # including a source absent from the first-slot write set.
        def destinations_still_committed():
            third_slot = slot.parent / "00000002"
            third_plan_path = third_slot / "destination" / "plan.json"
            third_plan = None
            if third_plan_path.exists() or third_plan_path.is_symlink():
                third_raw = _read(
                    third_slot / "intent.json", writer.receipts.uid)
                third_source = json.loads(third_raw)
                third_plan, _ = qualified_destination_plan(
                    third_slot, third_source, writer.receipts.uid,
                    targets=writer.targets)
                if (third_source.get("generation") != proof.generation or
                        third_source.get("sequence") != 2 or
                        "live" not in third_plan):
                    raise V2OriginalConfigRefused(
                        "learning_progress_third_plan_unqualified")
            def committed(name, path, row, kind):
                data, st = _target(path, writer.receipts.uid)
                digest = hashlib.sha256(data).hexdigest()
                if row["path"] != str(path):
                    return False
                if digest == row["after"]:
                    return True
                if third_plan is None:
                    return False
                later = third_plan[kind].get(name)
                if (later is None or later["path"] != str(path) or
                        later["before"] != row["after"]):
                    return False
                return (digest == later["after"] or
                        (digest == later["before"] and
                         _file_identity(st) == (
                             later["before_device"],
                             later["before_inode"],
                             later["before_ctime_ns"],
                             later["before_mtime_ns"],
                             later["before_size"])))
            for name, row in plan["writes"].items():
                if not committed(
                        name, writer.targets[name], row, "writes"):
                    raise V2OriginalConfigRefused(
                        "learning_forward_progress_found_changed")
            for name, row in plan["live"].items():
                path = (COMMON_ACTIVE / "managed" /
                        ("hostlist-" + name + ".txt"))
                if not committed(name, path, row, "live"):
                    raise V2OriginalConfigRefused(
                        "learning_forward_progress_managed_changed")

        destinations_still_committed()
        progress = _canonical(_original_learning_forward_progress_record(
            source, source_raw, cp_raw, checkpoint))
        held()
        # The preceding source replay includes independently drained
        # P2b for EVERY old and new inode. Recheck before publishing and
        # after fsync. Append-only tails are retained, not ACKed.
        if (prepare_original_learning_forward_second_slot_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest,
                inspect=inspect) != prepared):
            raise V2OriginalConfigRefused(
                "learning_forward_progress_source_changed_before_seal")
        destinations_still_committed()
        _write_once(
            slot, "cursor-progress.json", progress, writer.receipts.uid)
        if (_read(slot / "cursor-progress.json",
                  writer.receipts.uid) != progress or
                prepare_original_learning_forward_second_slot_locked(
                    writer, proof, workspace, config_fd=config_fd,
                    config_path=config_path, attest=attest,
                    inspect=inspect) != prepared):
            raise V2OriginalConfigRefused(
                "learning_forward_progress_postseal_source_changed")
        destinations_still_committed()
        held()
        return {
            "generation": proof.generation, "sequence": 1,
            "source_intent_sha256":
                hashlib.sha256(source_raw).hexdigest(),
            "progress_sha256": hashlib.sha256(progress).hexdigest(),
            "profiles_count": source["profiles_count"],
            "cursor_advanced": True, "native_pending_ack_authorized": False,
            "native_cleanup_authorized": False, "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, DestinationRefused,
            OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, QueueSafetyError, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "learning_forward_progress_source_or_checkpoint_refused") from exc


def preview_original_learning_late_tails_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd, sealed_window: dict | None = None,
) -> dict:
    """Read ONLY the next physical old-pending/new-live N-profile suffixes.

    The already published second-slot cursor-progress checkpoint is a strict
    prerequisite. Reuse the same original P2a/GUI/FD4/FD9/P2b/Found owner;
    first replay the exact committed cut, then read current physically
    attested debug and N-inode cuts. No new source WAL, P1, ACK or unlink.
    """
    from auto_detect_epoch_receipts import _read
    from auto_detect_original_lock_handoff import OriginalLockRefused
    from auto_detect_queue import QueueSafetyError
    from auto_detect_learning_tails import qualify_learning_forward_late_delta
    try:
        if (not isinstance(writer, DestinationCommit) or
                not writer.queue._held or
                not getattr(writer, "_gui_held", False) or
                not isinstance(workspace, Path) or
                not workspace.is_absolute() or
                workspace.name != proof.generation or
                not callable(attest) or not callable(inspect)):
            raise V2OriginalConfigRefused(
                "learning_late_tail_original_locks_required")
        slot = (writer.receipts.root / proof.generation /
                "cursor-chain-v2" / "00000001")
        path_progress = slot / "cursor-progress.json"
        if not path_progress.exists() and not path_progress.is_symlink():
            raise V2OriginalConfigRefused(
                "learning_late_tail_second_cursor_not_committed")
        recorded = _read(path_progress, writer.receipts.uid)

        def current_progress():
            return seal_original_learning_forward_progress_locked(
                writer, proof, workspace,
                config_fd=config_fd, config_path=config_path,
                attest=attest, inspect=inspect)

        advanced = current_progress()
        if (advanced["progress_sha256"] !=
                hashlib.sha256(recorded).hexdigest() or
                advanced["cursor_advanced"] is not True or
                advanced["native_pending_ack_authorized"] is not False):
            raise V2OriginalConfigRefused(
                "learning_late_tail_cursor_progress_not_original")
        source_raw = _read(slot / "intent.json", writer.receipts.uid)
        source = json.loads(source_raw)
        if (hashlib.sha256(source_raw).hexdigest() !=
                advanced["source_intent_sha256"] or
                source["generation"] != proof.generation or
                source["sequence"] != 1 or
                source["profiles_count"] != len(proof.learning)):
            raise V2OriginalConfigRefused(
                "learning_late_tail_source_not_sealed")
        frozen = {
            "debug": source["debug"],
            "native": [
                json.loads(_read(
                    slot / "native" / f"{number:03d}.json",
                    writer.receipts.uid))["cursor"]
                for number, _, _ in proof.learning],
        }
        original = preview_original_learning_forward_windows_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect,
            sealed_window=frozen)
        if (original["native"] != frozen["native"] or
                original["debug"] != frozen["debug"] or
                original["observations"] != source["observations"]):
            raise V2OriginalConfigRefused(
                "learning_late_tail_second_cut_not_original")
        current = preview_original_learning_forward_windows_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect,
            sealed_window=sealed_window)
        result = qualify_learning_forward_late_delta(
            original, current, proof.learning)
        if (current_progress() != advanced or
                _read(path_progress, writer.receipts.uid) != recorded or
                attest() != proof):
            raise V2OriginalConfigRefused(
                "learning_late_tail_owner_or_progress_raced")
        return {
            "generation": proof.generation,
            "previous_sequence": 1,
            "source_intent_sha256": advanced["source_intent_sha256"],
            "cursor_progress_sha256": advanced["progress_sha256"],
            **result,
        }
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, QueueSafetyError,
            DestinationRefused, DebugWindowRefused,
            OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError) as exc:
        raise V2OriginalConfigRefused(
            "learning_late_tail_source_or_owner_refused") from exc


def prepare_original_learning_third_slot_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Original third-source write-once adapter, NOT another WAL writer."""
    from auto_detect_learning_third_slot import prepare_third_source_locked
    return prepare_third_source_locked(
        writer, proof, workspace, config_fd=config_fd,
        config_path=config_path, attest=attest, inspect=inspect)


def _original_learning_third_progress_record(
        intent: dict, source_raw: bytes, checkpoint_raw: bytes,
        checkpoint: dict, postimages: dict) -> dict:
    """One ORIGINAL, read-only post-P1 third N cursor receipt; never ACK.

    The physical destination postimage is pinned separately from the
    original WAL checkpoint so a later GUI same-content inode replacement
    cannot impersonate the post-commit state of this cursor tip.
    """
    return {
        "schema": 3, "kind": "original-learning-third-cursor-progress",
        "generation": intent["generation"], "sequence": 2,
        "owner_pid": intent["owner_pid"],
        "owner_start": intent["owner_start"],
        "operation_id": intent["operation_id"],
        "native_map_sha256": intent["native_map_sha256"],
        "first_slot_sha256": intent["first_slot_sha256"],
        "native_rebind_manifest_sha256":
            intent["native_rebind_manifest_sha256"],
        "previous_source_intent_sha256":
            intent["previous_source_intent_sha256"],
        "previous_cursor_progress_sha256":
            intent["previous_cursor_progress_sha256"],
        "source_intent_sha256": hashlib.sha256(source_raw).hexdigest(),
        "destination_plan_sha256": checkpoint["plan_sha256"],
        "destination_checkpoint_sha256":
            hashlib.sha256(checkpoint_raw).hexdigest(),
        "profiles_count": intent["profiles_count"],
        "native_cursor_receipts_sha256": intent["profiles_sha256"],
        "native_observations_sha256":
            intent["native_observations_sha256"],
        "observations_sha256": intent["observations_sha256"],
        "debug": intent["debug"],
        "destination_postimages": postimages,
        "cursor_advanced": True,
        "native_pending_ack_authorized": False,
        "native_cleanup_authorized": False,
        "generation_retired": False,
    }


def seal_original_learning_third_progress_locked(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Commit immutable third N logical cursor after original third P1.

    SOURCE ONLY. Reuse original P2a + GUI/Found + inherited Config FD4
    and FD9/P2b, ORIGINAL third intent and original destination WAL. The
    cursor tip binds every retained old/new N inode cut, debug cut,
    prior second tip, third plan/checkpoint and physically observed
    Found/managed after-inode identity. No ACK, unlink, native compaction,
    runtime service changes, generation retirement or Config writer.
    """
    import sys
    from auto_detect_epoch_receipts import _canonical, _write_once
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_queue import QueueSafetyError
    from auto_detect_destination_commit import _file_identity

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or
            not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or
            not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or
              writer.receipts.uid != 0 or writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused(
            "learning_third_progress_original_fd4_fd9_required")

    uid = writer.receipts.uid

    def held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH else uid)
        if attest() != proof:
            raise V2OriginalConfigRefused(
                "learning_third_progress_owner_changed")

    def original_source():
        return prepare_original_learning_third_slot_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)

    def all_postimages(plan):
        # Before writing any cursor receipt, verify the exact physical
        # third after-image for every CAS destination, including both
        # permanent Found and current active managed HOSTLIST files.
        pinned = {}
        for kind in ("writes", "live"):
            grouped = {}
            for name, row in sorted(plan[kind].items()):
                if kind == "writes":
                    path = writer.targets[name]
                else:
                    path = (COMMON_ACTIVE / "managed" /
                            ("hostlist-" + name + ".txt"))
                data, st = _target(path, uid)
                digest = hashlib.sha256(data).hexdigest()
                if (row["path"] != str(path) or
                        digest != row["after"] or
                        not st.st_ino or not st.st_nlink == 1):
                    raise V2OriginalConfigRefused(
                        "learning_third_progress_destination_not_after")
                device, inode, ctime, mtime, size = _file_identity(st)
                grouped[name] = {
                    "path": str(path), "sha256": digest,
                    "device": device, "inode": inode,
                    "ctime_ns": ctime, "mtime_ns": mtime,
                    "size": size,
                }
            pinned[kind] = grouped
        return pinned

    try:
        held()
        prepared = original_source()
        slot = Path(prepared["slot"])
        source_raw = _read(slot / "intent.json", uid)
        source = json.loads(source_raw)
        if (prepared.get("sequence") != 2 or
                prepared.get("intent_sha256") !=
                hashlib.sha256(source_raw).hexdigest() or
                source.get("kind") !=
                "original-learning-third-slot-prepared" or
                source.get("generation") != proof.generation or
                source.get("cursor_advanced") is not False or
                source.get("ack_authorized") is not False or
                source.get("commit_authorized") is not False):
            raise V2OriginalConfigRefused(
                "learning_third_progress_source_unsealed")
        # This is still the existing DestinationCommit and its original
        # source-bound plan codec, not a fresh second writer.
        plan, plan_raw = qualified_destination_plan(
            slot, source, uid, targets=writer.targets)
        cp_raw = _read(
            slot / "destination" / "checkpoint.json", uid)
        checkpoint = json.loads(cp_raw)
        expected_cp = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": proof.generation,
            "pending_name": "learning-00000002",
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "evidence": "learning-native-debug",
            "committed_cursor_offset": source["debug"]["end"],
            "committed_cursor_sha256": source["debug"]["end_sha256"],
            "ack_authorized": False,
        }
        if (cp_raw != _canonical(checkpoint) or
                checkpoint != expected_cp or
                plan.get("schema") != 3 or
                "live" not in plan or
                plan.get("source_intent_sha256") !=
                hashlib.sha256(source_raw).hexdigest() or
                plan.get("previous_cursor_progress_sha256") !=
                source["previous_cursor_progress_sha256"]):
            raise V2OriginalConfigRefused(
                "learning_third_progress_checkpoint_not_committed")

        # Even a checkpointed third plan must not override a later GUI
        # modification; compare physical identities, not just byte SHA.
        pinned = all_postimages(plan)
        progress = _canonical(_original_learning_third_progress_record(
            source, source_raw, cp_raw, checkpoint, pinned))
        held()
        if (original_source() != prepared or
                all_postimages(plan) != pinned):
            raise V2OriginalConfigRefused(
                "learning_third_progress_source_or_postimages_raced")
        # When a prior third cursor tip was published, a foreign GUI
        # rewrite that restores the SAME bytes has a new ctime/mtime.
        # Refuse it explicitly instead of letting write-once signal
        # a generic conflicting receipt; never re-pin a new inode.
        prior_progress_path = slot / "cursor-progress.json"
        if (prior_progress_path.exists() or
                prior_progress_path.is_symlink()):
            if _read(prior_progress_path, uid) != progress:
                raise V2OriginalConfigRefused(
                    "learning_third_progress_postimage_identity_changed")
        _write_once(
            slot, "cursor-progress.json", progress, uid)
        if (_read(slot / "cursor-progress.json", uid) != progress or
                original_source() != prepared or
                all_postimages(plan) != pinned):
            raise V2OriginalConfigRefused(
                "learning_third_progress_postseal_drift")
        held()
        return {
            "generation": proof.generation, "sequence": 2,
            "source_intent_sha256": hashlib.sha256(source_raw).hexdigest(),
            "progress_sha256": hashlib.sha256(progress).hexdigest(),
            "destination_plan_sha256":
                hashlib.sha256(plan_raw).hexdigest(),
            "destination_checkpoint_sha256":
                hashlib.sha256(cp_raw).hexdigest(),
            "profiles_count": source["profiles_count"],
            "cursor_advanced": True,
            "native_pending_ack_authorized": False,
            "native_cleanup_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, DestinationRefused,
            QueueSafetyError, DebugWindowRefused, OSError, ValueError,
            TypeError, KeyError, AttributeError, UnicodeError) as exc:
        raise V2OriginalConfigRefused(
            "learning_third_progress_source_or_checkpoint_refused") from exc


def _recover_original_learning_partial_locked(
        writer: DestinationCommit, proof, workspace: Path,
        slot: Path, intent: dict, *, owned_root: Path,
        manual_hostlists: dict[str, str], global_exclude: str,
        attest, inspect, psl: PublicSuffixList | None,
        config_fd: int | None = None,
        config_path: Path | None = None,
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
    from auto_detect_epoch_receipts import _canonical
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
    def original_source_recheck():
        # Reuse ONE original P2a/P2b source attester. The second slot has
        # TWO immutable native inode cursors, and must not be examined by
        # the first-slot single-inode prefix attester.
        if intent.get("sequence") in (1, 2):
            if config_fd is None or config_path is None:
                raise V2OriginalConfigRefused(
                    "learning_forward_partial_requires_original_config_fd")
            if intent["sequence"] == 1:
                answer = prepare_original_learning_forward_second_slot_locked(
                    writer, proof, workspace, config_fd=config_fd,
                    config_path=config_path, attest=attest, inspect=inspect)
            else:
                answer = prepare_original_learning_third_slot_locked(
                    writer, proof, workspace, config_fd=config_fd,
                    config_path=config_path, attest=attest, inspect=inspect)
            return {
                "source_intent_sha256": answer["intent_sha256"],
                "p2b_drained": True,
                "commit_authorized": False,
                "ack_authorized": False,
            }
        return attest_original_learning_sealed_prefix_locked(
            writer.queue, writer.receipts, proof, workspace, intent,
            attest=attest, inspect=inspect)
    prefix = original_source_recheck()
    if (prefix["source_intent_sha256"] != plan["source_intent_sha256"]
            or not prefix["p2b_drained"] or
            prefix["commit_authorized"] is not False or
            prefix["ack_authorized"] is not False):
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
    recheck = original_source_recheck()
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


def commit_with_original_learning_forward_second_slot(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path,
        owned_root: Path, manual_hostlists: dict[str, str],
        global_exclude: str, attest, inspect=probe_pending_fd,
        psl: PublicSuffixList | None = None,
) -> dict:
    """Original schema3 second-slot P1 -> SAME Found/managed P2k2b WAL.

    This import-only primitive is NOT connected to Apply, minute, or
    dvtws2. Never infer observations after the durable 00000001 intent:
    the original forward source reattests exactly its immutable old
    pending/new live/debug cuts, even while newer writes grow each inode.
    The ONE existing P2a/GUI/PHP inherited Config FD4 and owner FD9
    remain locked throughout, and the existing DestinationCommit alone
    writes permanent Found first, active managed next, then checkpoint.
    An interrupted original plan reuses the SAME old preimages and P1,
    never a fresh candidate or an independent config/storage writer.
    No physical native source cleanup, cursor advancement or ACK here.
    """
    import sys
    from auto_detect_epoch_receipts import _canonical
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_destination_commit import _file_identity

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(owned_root, Path) or not owned_root.is_absolute() or
            set(writer.targets) != {"auto", *KNOWN_HOSTLISTS} or
            any(writer.targets[name] != owned_root / (name + ".txt")
                for name in KNOWN_HOSTLISTS) or
            not isinstance(config_path, Path) or not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or
              writer.receipts.uid != 0 or writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused(
            "learning_forward_original_config_fd9_model_required")

    def config_held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused(
                "learning_forward_original_config_owner_changed")

    def original_second_source():
        result = prepare_original_learning_forward_second_slot_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (result["sequence"] != 1 or
                result["cursor_advanced"] is not False or
                result["commit_authorized"] is not False or
                result["ack_authorized"] is not False):
            raise V2OriginalConfigRefused(
                "learning_forward_unqualified_original_source")
        return result

    try:
        config_held()
        with writer.exclusive_targets():
            config_held()
            prepared = original_second_source()
            slot = Path(prepared["slot"])
            encoded = _read(slot / "intent.json", writer.receipts.uid)
            if hashlib.sha256(encoded).hexdigest() != prepared["intent_sha256"]:
                raise V2OriginalConfigRefused(
                    "learning_forward_source_intent_changed")
            intent = json.loads(encoded)
            if (intent["sequence"] != 1 or
                    intent["generation"] != proof.generation or
                    not intent["observations"]):
                raise V2OriginalConfigRefused(
                    "learning_forward_second_slot_not_original")
            raw = _canonical({"observations": intent["observations"]})
            checkpoint_file = slot / "destination" / "checkpoint.json"
            plan_file = slot / "destination" / "plan.json"
            if checkpoint_file.exists() or checkpoint_file.is_symlink():
                # A completed original checkpoint cannot reapply a user
                # deletion or use newer native observations.
                plan, plan_raw = qualified_destination_plan(
                    slot, intent, writer.receipts.uid, targets=writer.targets)
                checkpoint = json.loads(
                    _read(checkpoint_file, writer.receipts.uid))
                expected = {
                    "schema": 1,
                    "kind": "destination-and-cursor-committed",
                    "generation": proof.generation,
                    "pending_name": "learning-00000001",
                    "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
                    "evidence": "learning-native-debug",
                    "committed_cursor_offset": intent["debug"]["end"],
                    "committed_cursor_sha256": intent["debug"]["end_sha256"],
                    "ack_authorized": False,
                }
                if checkpoint != expected or attest() != proof:
                    raise V2OriginalConfigRefused(
                        "learning_forward_checkpoint_replay_changed")
                config_held()
                return checkpoint
            if plan_file.exists() or plan_file.is_symlink():
                recovered = _recover_original_learning_partial_locked(
                    writer, proof, workspace, slot, intent,
                    owned_root=owned_root,
                    manual_hostlists=manual_hostlists,
                    global_exclude=global_exclude, attest=attest,
                    inspect=inspect, psl=psl,
                    config_fd=config_fd, config_path=config_path)
                config_held()
                return recovered
            old_owned = read_owned(
                owned_root, owner_uid=writer.receipts.uid)
            if old_owned is None:
                raise V2OriginalConfigRefused(
                    "learning_forward_found_sources_absent")
            before_shared, before_stat = _target(
                writer.targets["auto"], writer.receipts.uid)
            candidate = preview_learning_p1_effects(
                intent["observations"], manual_hostlists,
                old_owned, before_shared.decode("utf-8"),
                global_exclude, psl=psl)
            # The same original live known composer/reloader proof as
            # first-slot P1. Never write Found without current same-PID
            # managed after-images.
            canonical = {}
            for name in KNOWN_HOSTLISTS:
                normalized = normalize(
                    manual_hostlists[name], name)["normalized"]
                canonical[name] = (
                    normalized + ("\n" if normalized else ""))
            aligned = preview_live_known_after_readonly(
                canonical, candidate["effects"],
                active=COMMON_ACTIVE, owned_root=owned_root,
                owner_uid=writer.receipts.uid, attest=attest)
            if (aligned["owner_schema"] != 3 or
                    aligned["generation"] != proof.generation or
                    aligned["operation"] != proof.operation_id or
                    aligned["pid"] != proof.owner.pid or
                    aligned["started"] != proof.owner.started or
                    aligned["commit_authorized"] is not False or
                    aligned["ack_authorized"] is not False):
                raise V2OriginalConfigRefused(
                    "learning_forward_live_generation_changed")
            live = {}
            for name in aligned["changed"]:
                row = aligned["files"][name]
                path = (COMMON_ACTIVE / "managed" /
                        ("hostlist-" + name + ".txt"))
                after = candidate["managed_after"][name]
                if (row["path"] != str(path) or
                        row["after_sha256"] !=
                        hashlib.sha256(after).hexdigest()):
                    raise V2OriginalConfigRefused(
                        "learning_forward_live_after_mismatch")
                live[name] = {
                    "path": path,
                    "before_sha256": row["before_sha256"],
                    "after": after,
                }
            # Native appenders ignore P2a. Reattest the *frozen* second
            # source and every GUI Found preimage after potentially slow
            # PSL/live work. Any foreign GUI edit fails before P2k2b.
            repeat = original_second_source()
            new_owned = read_owned(
                owned_root, owner_uid=writer.receipts.uid)
            new_shared, new_stat = _target(
                writer.targets["auto"], writer.receipts.uid)
            if (repeat != prepared or new_owned != old_owned or
                    new_shared != before_shared or
                    _file_identity(new_stat) != _file_identity(before_stat)):
                raise V2OriginalConfigRefused(
                    "learning_forward_p1_sources_changed_before_wal")
            config_held()
            result = writer._locked_commit(
                slot, intent, raw, candidate["effects"], live=live)
            plan, plan_raw = qualified_destination_plan(
                slot, intent, writer.receipts.uid, targets=writer.targets)
            expected = {
                "schema": 1,
                "kind": "destination-and-cursor-committed",
                "generation": proof.generation,
                "pending_name": "learning-00000001",
                "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
                "evidence": "learning-native-debug",
                "committed_cursor_offset": intent["debug"]["end"],
                "committed_cursor_sha256": intent["debug"]["end_sha256"],
                "ack_authorized": False,
            }
            if (result != expected or
                    not checkpoint_file.exists() or
                    attest() != proof):
                raise V2OriginalConfigRefused(
                    "learning_forward_destination_checkpoint_not_durable")
            config_held()
            return result
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, DestinationRefused,
            OwnedSourcesRefused, EffectiveKnownRefused,
            AutoDomainPolicyError, DomainPolicyError,
            OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError) as exc:
        raise V2OriginalConfigRefused(
            "learning_forward_original_config_wal_refused") from exc


def commit_with_original_learning_third_slot(
        writer: DestinationCommit, proof, workspace: Path, *,
        config_fd: int, config_path: Path,
        owned_root: Path, manual_hostlists: dict[str, str],
        global_exclude: str, attest, inspect=probe_pending_fd,
        psl: PublicSuffixList | None = None,
) -> dict:
    """Original schema3 third-slot P1 -> SAME Found/managed P2k2b WAL.

    This import-only primitive is NOT connected to Apply, minute, or
    dvtws2. Never infer observations after the durable 00000002 intent:
    the original forward source reattests exactly its immutable old
    pending/new live/debug cuts, even while newer writes grow each inode.
    The ONE existing P2a/GUI/PHP inherited Config FD4 and owner FD9
    remain locked throughout, and the existing DestinationCommit alone
    writes permanent Found first, active managed next, then checkpoint.
    An interrupted original plan reuses the SAME old preimages and P1,
    never a fresh candidate or an independent config/storage writer.
    No physical native source cleanup, cursor advancement or ACK here.
    """
    import sys
    from auto_detect_epoch_receipts import _canonical
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
    )
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_destination_commit import _file_identity

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(owned_root, Path) or not owned_root.is_absolute() or
            set(writer.targets) != {"auto", *KNOWN_HOSTLISTS} or
            any(writer.targets[name] != owned_root / (name + ".txt")
                for name in KNOWN_HOSTLISTS) or
            not isinstance(config_path, Path) or not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and
             (config_path != CONFIG_PATH or
              writer.receipts.uid != 0 or writer.queue.uid != 0)) or
            attest() != proof):
        raise V2OriginalConfigRefused(
            "learning_third_original_config_fd9_model_required")

    def config_held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused(
                "learning_forward_original_config_owner_changed")

    def original_third_source():
        result = prepare_original_learning_third_slot_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (result["sequence"] != 2 or
                result["cursor_advanced"] is not False or
                result["commit_authorized"] is not False or
                result["ack_authorized"] is not False):
            raise V2OriginalConfigRefused(
                "learning_third_unqualified_original_source")
        return result

    try:
        config_held()
        with writer.exclusive_targets():
            config_held()
            prepared = original_third_source()
            slot = Path(prepared["slot"])
            encoded = _read(slot / "intent.json", writer.receipts.uid)
            if hashlib.sha256(encoded).hexdigest() != prepared["intent_sha256"]:
                raise V2OriginalConfigRefused(
                    "learning_forward_source_intent_changed")
            intent = json.loads(encoded)
            if (intent["sequence"] != 2 or
                    intent["generation"] != proof.generation or
                    not intent["observations"]):
                raise V2OriginalConfigRefused(
                    "learning_forward_third_slot_not_original")
            raw = _canonical({"observations": intent["observations"]})
            checkpoint_file = slot / "destination" / "checkpoint.json"
            plan_file = slot / "destination" / "plan.json"
            if checkpoint_file.exists() or checkpoint_file.is_symlink():
                # A completed original checkpoint cannot reapply a user
                # deletion or use newer native observations.
                plan, plan_raw = qualified_destination_plan(
                    slot, intent, writer.receipts.uid, targets=writer.targets)
                checkpoint = json.loads(
                    _read(checkpoint_file, writer.receipts.uid))
                expected = {
                    "schema": 1,
                    "kind": "destination-and-cursor-committed",
                    "generation": proof.generation,
                    "pending_name": "learning-00000002",
                    "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
                    "evidence": "learning-native-debug",
                    "committed_cursor_offset": intent["debug"]["end"],
                    "committed_cursor_sha256": intent["debug"]["end_sha256"],
                    "ack_authorized": False,
                }
                if checkpoint != expected or attest() != proof:
                    raise V2OriginalConfigRefused(
                        "learning_forward_checkpoint_replay_changed")
                config_held()
                return checkpoint
            if plan_file.exists() or plan_file.is_symlink():
                recovered = _recover_original_learning_partial_locked(
                    writer, proof, workspace, slot, intent,
                    owned_root=owned_root,
                    manual_hostlists=manual_hostlists,
                    global_exclude=global_exclude, attest=attest,
                    inspect=inspect, psl=psl,
                    config_fd=config_fd, config_path=config_path)
                config_held()
                return recovered
            old_owned = read_owned(
                owned_root, owner_uid=writer.receipts.uid)
            if old_owned is None:
                raise V2OriginalConfigRefused(
                    "learning_forward_found_sources_absent")
            before_shared, before_stat = _target(
                writer.targets["auto"], writer.receipts.uid)
            candidate = preview_learning_p1_effects(
                intent["observations"], manual_hostlists,
                old_owned, before_shared.decode("utf-8"),
                global_exclude, psl=psl)
            # The same original live known composer/reloader proof as
            # first-slot P1. Never write Found without current same-PID
            # managed after-images.
            canonical = {}
            for name in KNOWN_HOSTLISTS:
                normalized = normalize(
                    manual_hostlists[name], name)["normalized"]
                canonical[name] = (
                    normalized + ("\n" if normalized else ""))
            aligned = preview_live_known_after_readonly(
                canonical, candidate["effects"],
                active=COMMON_ACTIVE, owned_root=owned_root,
                owner_uid=writer.receipts.uid, attest=attest)
            if (aligned["owner_schema"] != 3 or
                    aligned["generation"] != proof.generation or
                    aligned["operation"] != proof.operation_id or
                    aligned["pid"] != proof.owner.pid or
                    aligned["started"] != proof.owner.started or
                    aligned["commit_authorized"] is not False or
                    aligned["ack_authorized"] is not False):
                raise V2OriginalConfigRefused(
                    "learning_forward_live_generation_changed")
            live = {}
            for name in aligned["changed"]:
                row = aligned["files"][name]
                path = (COMMON_ACTIVE / "managed" /
                        ("hostlist-" + name + ".txt"))
                after = candidate["managed_after"][name]
                if (row["path"] != str(path) or
                        row["after_sha256"] !=
                        hashlib.sha256(after).hexdigest()):
                    raise V2OriginalConfigRefused(
                        "learning_forward_live_after_mismatch")
                live[name] = {
                    "path": path,
                    "before_sha256": row["before_sha256"],
                    "after": after,
                }
            # Native appenders ignore P2a. Reattest the *frozen* second
            # source and every GUI Found preimage after potentially slow
            # PSL/live work. Any foreign GUI edit fails before P2k2b.
            repeat = original_third_source()
            new_owned = read_owned(
                owned_root, owner_uid=writer.receipts.uid)
            new_shared, new_stat = _target(
                writer.targets["auto"], writer.receipts.uid)
            if (repeat != prepared or new_owned != old_owned or
                    new_shared != before_shared or
                    _file_identity(new_stat) != _file_identity(before_stat)):
                raise V2OriginalConfigRefused(
                    "learning_forward_p1_sources_changed_before_wal")
            config_held()
            result = writer._locked_commit(
                slot, intent, raw, candidate["effects"], live=live)
            plan, plan_raw = qualified_destination_plan(
                slot, intent, writer.receipts.uid, targets=writer.targets)
            expected = {
                "schema": 1,
                "kind": "destination-and-cursor-committed",
                "generation": proof.generation,
                "pending_name": "learning-00000002",
                "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
                "evidence": "learning-native-debug",
                "committed_cursor_offset": intent["debug"]["end"],
                "committed_cursor_sha256": intent["debug"]["end_sha256"],
                "ack_authorized": False,
            }
            if (result != expected or
                    not checkpoint_file.exists() or
                    attest() != proof):
                raise V2OriginalConfigRefused(
                    "learning_forward_destination_checkpoint_not_durable")
            config_held()
            return result
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, DestinationRefused,
            OwnedSourcesRefused, EffectiveKnownRefused,
            AutoDomainPolicyError, DomainPolicyError,
            OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError) as exc:
        raise V2OriginalConfigRefused(
            "learning_forward_original_config_wal_refused") from exc


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
