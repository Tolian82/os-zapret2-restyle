#!/usr/bin/env python3
"""STEP 15b3h1: STOPPED NEW-positive -> original P1 preflight (READ ONLY).

A stopped generation has no authoritative RUNNING managed-HOSTLIST owner.
Never call a running-generation DestinationCommit or invent a post-stop
Found/managed writer. This optional, original-FD9 guarded projection proves
only what the existing P1 policy WOULD do with exact remaining native+
debug positives, current manual/Found inputs, and unchanged physical files.

It is not wired to Stop, Restart, Apply, Boot or the minute collector.
"""
from __future__ import annotations

from pathlib import Path

from auto_detect_destination_commit import (
    DestinationCommit, DestinationRefused, _target, _file_identity,
)
from auto_detect_original_history import _held, _digest
from auto_detect_original_history_stop_new import (
    preview_original_learning_stopped_NEW_tail_locked,
)
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, preview_learning_p1_effects,
)
from auto_detect_owned_sources import (
    KNOWN_HOSTLISTS, OwnedSourcesRefused, read_owned,
)
from auto_detect_fd import probe_pending_fd
from auto_detect_owner import LearningGenerationProof, GenerationRefused
from auto_detect_epoch_receipts import ReceiptRefused
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError
from auto_detect_debug_window import DebugWindowRefused
from domain_policy import (
    PublicSuffixList, AutoDomainPolicyError, DomainPolicyError,
)


def _qualified_new_observations(source, proof):
    """Require explicit real native-N provenance, not a guessed hostlist."""
    if (type(source) is not dict or
            source.get("original_OLD_archive_physically_retired") is not True or
            source.get("all_NEW_native_and_debug_physically_pinned") is not True or
            source.get("current_final_destinations_inode_pinned") is not True or
            source.get("stopped_owner_freshly_reattested") is not True or
            source.get("native_pending_ack_authorized") is not False or
            source.get("generation_retired") is not False or
            source.get("generation") != proof.generation or
            type(source.get("remaining_new_native_bytes")) is not int or
            source["remaining_new_native_bytes"] < 0 or
            type(source.get("remaining_new_debug_bytes")) is not int or
            source["remaining_new_debug_bytes"] < 0):
        raise V2OriginalConfigRefused("stopped_p1_unqualified_original_NEW")

    observations = source.get("remaining_positive_native_observations")
    if type(observations) is not list or len(observations) > 4096:
        raise V2OriginalConfigRefused("stopped_p1_unqualified_positive_count")
    allowed = {(n, name) for n, name, _path in proof.learning}
    native = []
    for row in observations:
        if (type(row) is not dict or
                set(row) != {"native_number", "hostlist", "hostname"} or
                type(row["native_number"]) is not int or
                type(row["hostlist"]) is not str or
                type(row["hostname"]) is not str or
                not row["hostname"] or
                (row["native_number"], row["hostlist"]) not in allowed):
            raise V2OriginalConfigRefused("stopped_p1_foreign_positive_profile")
        native.append((row["native_number"], row["hostlist"], row["hostname"]))
    if native != sorted(set(native)):
        raise V2OriginalConfigRefused("stopped_p1_duplicate_or_out_of_order_positive")
    nbytes = source["remaining_new_native_bytes"]
    if ((nbytes == 0 and (native or
                          source.get("remaining_new_state") !=
                          "no-unread-native-bytes")) or
            (nbytes > 0 and (not native or
                             source.get("remaining_new_state") !=
                             "unconsumed-native-events"))):
        raise V2OriginalConfigRefused("stopped_p1_unattributed_NEW_bytes")
    # P1 gets proven owner HOSTLIST before its own PSL/eTLD+1 collapse.
    return [{"hostname": hostname, "hostlist": hostlist}
            for _, hostlist, hostname in native]


def preview_original_learning_stopped_NEW_p1_locked(
        writer: DestinationCommit, proof: LearningGenerationProof,
        workspace: Path, *, config_fd: int, config_path: Path,
        owned_root: Path, manual_hostlists: dict[str, str],
        global_exclude: str, attest, inspect=probe_pending_fd,
        psl: PublicSuffixList | None = None,
) -> dict:
    """Propose original P1 effects without WAL, native cleanup, ACK or writes.

    The inherited Config FD, original P2a+GUI and all-PID P2b remain
    authoritative. The P1 input is checked against two complete original
    STOPPED owner/NEW/OLD-retirement/destination proofs, not a stale map
    or hand-injected positive list. A new running engine is a refusal, not
    permission to replay an old generation into a current managed list.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (not isinstance(owned_root, Path) or not owned_root.is_absolute()
                or type(manual_hostlists) is not dict or
                set(manual_hostlists) != set(KNOWN_HOSTLISTS) or
                any(type(value) is not str for value in manual_hostlists.values())
                or type(global_exclude) is not str or
                not callable(inspect) or
                set(writer.targets) != {"auto", *KNOWN_HOSTLISTS} or
                writer.targets["auto"].parent == owned_root or
                any(writer.targets[name] != owned_root / (name + ".txt")
                    for name in KNOWN_HOSTLISTS)):
            raise V2OriginalConfigRefused("stopped_p1_original_registered_sources_required")

        args = dict(config_fd=config_fd, config_path=config_path,
                    attest=attest, inspect=inspect)
        before = preview_original_learning_stopped_NEW_tail_locked(
            writer, proof, workspace, **args)
        observations = _qualified_new_observations(before, proof)
        original_owned = read_owned(owned_root, owner_uid=writer.receipts.uid)
        if original_owned is None:
            raise V2OriginalConfigRefused("stopped_p1_original_owned_source_missing")
        shared, shared_st = _target(
            writer.targets["auto"], writer.receipts.uid)

        # The existing P1 is the sole source of PSL, exclusion, manual
        # coverage and cross-source policy. Never create a second parser.
        projected = None
        if observations:
            projected = preview_learning_p1_effects(
                observations, manual_hostlists, original_owned,
                shared.decode("utf-8"), global_exclude, psl=psl)
            if (projected["commit_authorized"] is not False or
                    projected["cleanup_authorized"] is not False or
                    projected["ack_authorized"] is not False):
                raise V2OriginalConfigRefused("stopped_p1_original_policy_authority_changed")

        current_owned = read_owned(owned_root, owner_uid=writer.receipts.uid)
        current_shared, current_st = _target(
            writer.targets["auto"], writer.receipts.uid)
        after = preview_original_learning_stopped_NEW_tail_locked(
            writer, proof, workspace, **args)
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (before != after or current_owned != original_owned or
                current_shared != shared or
                _file_identity(current_st) != _file_identity(shared_st)):
            raise V2OriginalConfigRefused("stopped_p1_owner_native_or_found_raced")

        return {
            "generation": proof.generation, "sequence": 2,
            "original_OLD_retired": True,
            "current_new_source_doubly_attested": True,
            "remaining_native_observations": (
                before["remaining_positive_native_observations"]),
            "remaining_native_bytes": before["remaining_new_native_bytes"],
            "p1_projection_available": projected is not None,
            "found_effects": projected["effects"] if projected else {},
            "found_after_sha256": ({
                name: _digest(data)
                for name, data in projected["found_after"].items()
            } if projected else {}),
            "managed_after_sha256": ({
                name: _digest(data)
                for name, data in projected["managed_after"].items()
            } if projected else {}),
            "psl_sha256": projected["psl_sha256"] if projected else None,
            "current_generation_managed_write_authorized": False,
            "stopped_p1_wal_checkpoint_created": False,
            "native_pending_ack_authorized": False,
            "native_cleanup_authorized": False,
            "generation_retired": False,
            "operator_stop_may_be_blocked": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            OwnedSourcesRefused, GenerationRefused, OriginalLockRefused,
            QueueSafetyError, DebugWindowRefused, AutoDomainPolicyError,
            DomainPolicyError) as exc:
        raise V2OriginalConfigRefused(
            "stopped_p1_original_locked_projection_unavailable") from exc


def main():
    raise SystemExit("Original STOPPED NEW P1 preview is not a worker")


if __name__ == "__main__":
    main()
