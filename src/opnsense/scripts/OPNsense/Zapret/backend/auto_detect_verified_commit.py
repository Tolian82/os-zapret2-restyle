#!/usr/bin/env python3
"""#1052 P2k4: dormant current-generation P2k3->P2k2b fallback transaction.

The queue lock spans the caller's operation, and the same target-file lock
spans *both* the canonical P1 snapshot/decision and the durable destination
journal. No public native worker, pending acknowledgment or GUI is enabled.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from auto_detect_destination_commit import (DestinationCommit, DestinationRefused,
                                            _target, _read)
from auto_detect_fd import probe_pending_fd
from auto_detect_owner import attest_running_generation, GenerationProof
from auto_detect_verified_batch import prepare_verified_batch, BatchRefused
from domain_policy import PublicSuffixList


class VerifiedCommitRefused(RuntimeError):
    """Do not acknowledge/delete pending on any missing owner or list proof."""


def commit_verified_fallback(writer: DestinationCommit, pending: Path, *,
                             snapshot: Callable,
                             attest: Callable = attest_running_generation,
                             inspect: Callable = probe_pending_fd,
                             psl: PublicSuffixList | None = None) -> dict:
    """Physically commit a fully verified passive-observer fallback batch.

    snapshot() runs INSIDE the shared destination lock and must return a full
    authoritative GUI/Config snapshot: (manual hostlists INCLUDING the exact
    current shared auto file, auto-owned components, global exclude). This
    integration point is intentionally NOT registered in configd: the real
    native GUI/Config reader is not yet coordinated with this lock. Tests use
    an explicit controlled adapter, not production activation or FD9 proof.
    """
    if (not isinstance(writer, DestinationCommit) or not writer.queue._held or
            not callable(snapshot) or not callable(attest) or not callable(inspect)):
        raise VerifiedCommitRefused("original_queue_and_snapshot_reader_required")
    pending = Path(pending)
    with writer.exclusive_targets():
        try:
            state = snapshot()
            if (not isinstance(state, tuple) or len(state) != 3 or
                    not isinstance(state[0], dict) or
                    not isinstance(state[1], dict) or
                    type(state[2]) is not str or
                    "auto" not in state[0] or
                    any(type(v) is not str for v in (*state[0].values(),
                                                    *state[1].values())) or
                    not set(state[1]).issubset(state[0])):
                raise VerifiedCommitRefused("incomplete_authoritative_gui_snapshot")
            lists, owned, excluded = state
            physical, _ = _target(writer.targets["auto"], writer.receipts.uid)
            if lists["auto"].encode("utf-8") != physical:
                raise VerifiedCommitRefused("shared_hostlist_snapshot_not_current")
            proof = attest()
            if not isinstance(proof, GenerationProof):
                raise VerifiedCommitRefused("original_generation_missing")
            batch = prepare_verified_batch(writer.queue, writer.receipts, pending,
                                           lists, owned, excluded, attest=attest,
                                           inspect=inspect, psl=psl)
            if (attest() != proof or batch.generation != proof.generation or
                    batch.ack_authorized is not False):
                raise VerifiedCommitRefused("original_generation_changed_before_commit")
            folder, intent, raw = writer._source(proof, pending)
            if (batch.pending_name != intent["pending_name"] or
                    batch.pending_sha256 != intent["pending_sha256"] or
                    batch.debug_end_offset != intent["debug_end_offset"] or
                    batch.debug_end_sha256 != intent["debug_end_sha256"]):
                raise VerifiedCommitRefused("prepared_policy_not_original_intent")
            additions = batch.policy["additions"]
            if (batch.policy["result"] != "ok" or batch.policy["unprocessed"] or
                    batch.policy["removals"] or
                    set(additions) - {"auto"}):
                raise VerifiedCommitRefused("not_safe_shared_fallback_policy")
            effects = ({"auto": {"add": additions["auto"], "remove": []}}
                       if additions.get("auto") else {})

            # An interrupted P2k2b plan may have written its auto row before
            # the checkpoint. On replay P1 now sees the row and reports no
            # *new* addition. Accept only rows already physically present or
            # still required by this P1 decision; never replay foreign sinks.
            plan_path = folder / "destination" / "plan.json"
            if plan_path.exists() or plan_path.is_symlink():
                plan = json.loads(_read(plan_path, writer.receipts.uid))
                writes = plan.get("writes") if isinstance(plan, dict) else None
                if (not isinstance(writes, dict) or set(writes) - {"auto"} or
                        any(not isinstance(v, dict) or v.get("remove") != []
                            for v in writes.values())):
                    raise VerifiedCommitRefused("foreign_or_owned_relocation_plan")
                if "auto" in writes:
                    previous = writes["auto"].get("add")
                    if not isinstance(previous, list) or any(
                        type(host) is not str or
                        (host not in additions.get("auto", []) and
                         host not in physical.decode("utf-8").splitlines())
                        for host in previous
                    ):
                        raise VerifiedCommitRefused("old_plan_not_supported_by_current_policy")
            result = writer._locked_commit(folder, intent, raw, effects)
            if result.get("ack_authorized") is not False:
                raise VerifiedCommitRefused("destination_checkpoint_must_not_ack")
            return result
        except (DestinationRefused, BatchRefused, ValueError, KeyError,
                UnicodeError, OSError, TypeError) as exc:
            raise VerifiedCommitRefused("original_owner_policy_or_destination_refused") from exc


def run_native_verified_commit_worker() -> None:
    raise VerifiedCommitRefused("gui_config_fd9_and_ack_not_authorized")


if __name__ == "__main__":
    run_native_verified_commit_worker()