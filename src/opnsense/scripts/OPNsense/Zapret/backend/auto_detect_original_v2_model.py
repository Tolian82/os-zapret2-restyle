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
                                      _checkpoint, _debug_prefix)
from auto_detect_debug_window import ADD, _read_exact, _hostname
from auto_detect_destination_commit import (DestinationCommit, DestinationRefused,
                                            _target)
from auto_detect_epoch_receipts import ReceiptRefused, _read
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_v2_source import (qualified_current_source,
                                            detached_original_raw, OriginalSourceRefused)
from auto_detect_owner import GenerationProof, attest_running_generation
from auto_detect_owned_sources import (KNOWN_HOSTLISTS, OwnedSourcesRefused,
                                       read_owned)
from domain_policy import AutoDomainPolicyError, PublicSuffixList, plan_auto_additions

MAX_MODEL_TEXT = 1 << 20


class V2OriginalConfigRefused(RuntimeError):
    """Preserve original pending and GUI-edited target files on uncertainty."""


def _domains(proof: GenerationProof, intent: dict, raw: bytes, *,
             owner_uid: int, writer_gid: int | None) -> list[dict]:
    """Recheck exactly the protected native P2k1 event subwindow after append.

    Later native debug events may have been appended to the same inode;
    never accidentally consume them for a preceding immutable intent.
    """
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


def commit_with_original_v2_model(
    writer: DestinationCommit, pending: Path, *,
    owned_root: Path, manual_hostlists: dict[str, str], global_exclude: str,
    attest: Callable = attest_running_generation,
    inspect: Callable = probe_pending_fd,
    psl: PublicSuffixList | None = None,
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
            len(global_exclude.encode("utf-8")) > MAX_MODEL_TEXT or
            not isinstance(manual_hostlists, dict) or
            set(manual_hostlists) != set(KNOWN_HOSTLISTS) or
            any(type(value) is not str or
                len(value.encode("utf-8")) > MAX_MODEL_TEXT
                for value in manual_hostlists.values()) or
            not callable(attest) or not callable(inspect)):
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
        observations = _domains(proof, intent, raw, owner_uid=writer.receipts.uid,
                                writer_gid=writer.receipts.writer_gid)
        if attest() != proof:
            raise V2OriginalConfigRefused("original_generation_changed_during_debug")
        with writer.exclusive_targets():
            owned = read_owned(root, owner_uid=writer.receipts.uid)
            if owned is None or set(owned) != set(KNOWN_HOSTLISTS):
                raise V2OriginalConfigRefused("unsealed_known_owned_baseline")
            # Checkpoint already exists: genuine P2k2b only returns prior
            # result, never replays a positive after a later GUI deletion.
            completed = _checkpoint(folder, intent, writer.receipts.uid,
                                    targets=writer.targets)
            if completed is not None:
                if attest() != proof:
                    raise V2OriginalConfigRefused("original_generation_changed_before_replay")
                return completed[0]
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
                    not _debug_prefix(proof, intent["debug_end_offset"],
                                      intent["debug_end_sha256"],
                                      writer.receipts.uid, writer.receipts.writer_gid,
                                      intent["debug_device"], intent["debug_inode"])):
                raise V2OriginalConfigRefused("original_generation_or_fd_changed_before_write")
            result = writer._locked_commit(folder, intent, raw, effects)
            if (read_owned(root, owner_uid=writer.receipts.uid) is None or
                    _checkpoint(folder, intent, writer.receipts.uid,
                                targets=writer.targets) is None or
                    attest() != proof or result["ack_authorized"] is not False):
                raise V2OriginalConfigRefused("original_v2_checkpoint_not_verified")
            return result
    except (OSError, TypeError, ValueError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalSourceRefused, CursorChainRefused,
            DestinationRefused, OwnedSourcesRefused, AutoDomainPolicyError) as exc:
        raise V2OriginalConfigRefused("original_config_v2_commit_refused") from exc
