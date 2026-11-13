#!/usr/bin/env python3
"""#1052 P2k8d: protected P1-owned relocation through existing P2k2b journal.

The authentic trailing native observer has unknown HOSTLIST provenance. It
may move *previously proven automatic* known-list rows into the editable shared
fallback, but may not attribute a fresh discovery by domain-name guessing.
Import-only: original Config/FD9 lock across the transaction is not wired,
and neither a native worker nor pending acknowledgment is enabled.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from auto_detect_destination_commit import DestinationCommit, DestinationRefused, _target
from auto_detect_epoch_receipts import _read, ReceiptRefused
from auto_detect_fd import probe_pending_fd
from auto_detect_owner import GenerationProof, attest_running_generation
from auto_detect_owned_sources import (KNOWN_HOSTLISTS, OwnedSourcesRefused,
                                       read_owned)
from auto_detect_verified_batch import prepare_verified_batch, BatchRefused
from domain_policy import PublicSuffixList


class VerifiedOwnedRefused(RuntimeError):
    """Keep the original pending on incomplete provenance or failed commit."""


def commit_verified_owned_relocation(writer: DestinationCommit, pending: Path, *,
                                     owned_root: Path, snapshot: Callable,
                                     attest: Callable = attest_running_generation,
                                     inspect: Callable = probe_pending_fd,
                                     psl: PublicSuffixList | None = None) -> dict:
    """Commit authentic fallback and known-owned relocation, never ACK.

    Only the original trailing observer is qualified, so new additions to
    known components remain forbidden. A future native caller MUST hold
    OPNsense Config::lock throughout this call. The injected snapshot does
    not itself establish original Config ownership.
    """
    if (not isinstance(writer, DestinationCommit) or not writer.queue._held or
            not callable(snapshot) or not callable(attest) or
            not callable(inspect)):
        raise VerifiedOwnedRefused('original_queue_and_config_snapshot_required')
    root = Path(owned_root)
    required = {'auto', *KNOWN_HOSTLISTS}
    if (not root.is_absolute() or set(writer.targets) != required or
            any(writer.targets[name] != root / (name + '.txt')
                for name in KNOWN_HOSTLISTS) or
            writer.targets['auto'].parent == root):
        raise VerifiedOwnedRefused('unqualified_known_owned_target_mapping')
    pending = Path(pending)
    with writer.exclusive_targets():
        try:
            actual_owned = read_owned(root, owner_uid=writer.receipts.uid)
            if actual_owned is None:
                raise VerifiedOwnedRefused('unknown_known_owned_origin')
            state = snapshot()
            if (not isinstance(state, tuple) or len(state) != 3 or
                    not isinstance(state[0], dict) or
                    set(state[0]) != required or
                    not isinstance(state[1], dict) or
                    set(state[1]) != set(KNOWN_HOSTLISTS) or
                    type(state[2]) is not str or
                    any(type(v) is not str for v in state[0].values()) or
                    any(type(v) is not str for v in state[1].values()) or
                    state[1] != actual_owned):
                raise VerifiedOwnedRefused('incomplete_or_stale_original_config_snapshot')
            manual, _, global_exclude = state
            current_auto, _ = _target(writer.targets['auto'], writer.receipts.uid)
            if manual['auto'].encode('utf-8') != current_auto:
                raise VerifiedOwnedRefused('shared_hostlist_snapshot_not_current')
            proof = attest()
            if not isinstance(proof, GenerationProof):
                raise VerifiedOwnedRefused('authentic_generation_missing')
            batch = prepare_verified_batch(
                writer.queue, writer.receipts, pending, manual, actual_owned,
                global_exclude, attest=attest, inspect=inspect, psl=psl,
                allow_owned_relocation=True)
            if (attest() != proof or batch.generation != proof.generation or
                    batch.ack_authorized is not False):
                raise VerifiedOwnedRefused('original_generation_changed_before_commit')
            folder, intent, raw = writer._source(proof, pending)
            if (batch.pending_name != intent['pending_name'] or
                    batch.pending_sha256 != intent['pending_sha256'] or
                    batch.debug_end_offset != intent['debug_end_offset'] or
                    batch.debug_end_sha256 != intent['debug_end_sha256']):
                raise VerifiedOwnedRefused('prepared_policy_not_original_intent')
            policy = batch.policy
            additions, removals = policy['additions'], policy['removals']
            eligible = {row['root'] for row in policy['routes']
                        if row['destination'] == 'auto'}
            if (policy['result'] != 'ok' or policy['unprocessed'] or
                    set(additions) - {'auto'} or
                    set(removals) - set(KNOWN_HOSTLISTS) or
                    any(domain not in eligible for domain in
                        [*additions.get('auto', []),
                         *(domain for names in removals.values() for domain in names)])):
                raise VerifiedOwnedRefused('unqualified_known_relocation_policy')
            effects = {}
            if additions.get('auto'):
                effects['auto'] = {'add': additions['auto'], 'remove': []}
            for name in KNOWN_HOSTLISTS:
                if removals.get(name):
                    effects[name] = {'add': [], 'remove': removals[name]}

            # P2k2b may have applied a shared addition and/or an owned
            # removal before its immutable checkpoint. Before completing
            # any such plan, compare every previous effect with the current
            # P1 decision and exact physical destinations under this lock.
            plan_file = folder / 'destination' / 'plan.json'
            checkpoint = folder / 'destination' / 'checkpoint.json'
            if (plan_file.exists() or plan_file.is_symlink()) and not (
                    checkpoint.exists() or checkpoint.is_symlink()):
                prior = json.loads(_read(plan_file, writer.receipts.uid))
                writes = prior.get('writes') if isinstance(prior, dict) else None
                if not isinstance(writes, dict) or set(writes) - required:
                    raise VerifiedOwnedRefused('foreign_relocation_plan')
                for name, effect in writes.items():
                    if (not isinstance(effect, dict) or
                            type(effect.get('add')) is not list or
                            type(effect.get('remove')) is not list):
                        raise VerifiedOwnedRefused('malformed_relocation_plan')
                    old_add, old_remove = effect['add'], effect['remove']
                    if ((name == 'auto' and old_remove) or
                            (name != 'auto' and old_add) or
                            any(type(domain) is not str or domain not in eligible
                                for domain in old_add + old_remove)):
                        raise VerifiedOwnedRefused('plan_no_longer_allowed_by_policy')
                    physical, _ = _target(writer.targets[name], writer.receipts.uid)
                    physical_rows = set(physical.decode('utf-8').splitlines())
                    if (name == 'auto' and any(
                        domain not in additions.get('auto', []) and
                        domain not in physical_rows for domain in old_add
                    )):
                        raise VerifiedOwnedRefused('prior_shared_addition_not_replayable')
                    if name != 'auto' and any(
                        domain not in removals.get(name, []) and
                        domain in physical_rows for domain in old_remove
                    ):
                        raise VerifiedOwnedRefused('prior_owned_removal_not_replayable')
            result = writer._locked_commit(folder, intent, raw, effects)
            if read_owned(root, owner_uid=writer.receipts.uid) is None:
                raise VerifiedOwnedRefused('known_owned_components_lost')
            if result.get('ack_authorized') is not False:
                raise VerifiedOwnedRefused('destination_checkpoint_must_not_ack')
            return result
        except (OwnedSourcesRefused, DestinationRefused, BatchRefused,
                ReceiptRefused, ValueError, KeyError, UnicodeError,
                OSError, TypeError, AttributeError) as exc:
            raise VerifiedOwnedRefused('original_owner_policy_or_owned_destination_refused') from exc


def commit_with_locked_original_model(writer: DestinationCommit, pending: Path, *,
                                      manual_hostlists: dict[str, str],
                                      global_exclude: str, owned_root: Path,
                                      attest: Callable = attest_running_generation,
                                      inspect: Callable = probe_pending_fd,
                                      psl: PublicSuffixList | None = None) -> dict:
    """Use a fresh original Config-locked Model, not an old P2k8a snapshot.

    Call only while the ORIGINAL OPNsense Config::lock() owner remains held,
    after the native queue has been locked. The caller must synchronously
    keep that PHP owner alive until this durable transaction returns. This
    import-only adapter grants no native caller/FD9 authorization.
    """
    if (not isinstance(writer, DestinationCommit) or
            not writer.queue._held or
            not isinstance(manual_hostlists, dict) or
            set(manual_hostlists) != set(KNOWN_HOSTLISTS) or
            any(type(text) is not str or len(text.encode('utf-8')) > (1 << 20)
                for text in manual_hostlists.values()) or
            type(global_exclude) is not str or
            len(global_exclude.encode('utf-8')) > (1 << 20)):
        raise VerifiedOwnedRefused('original_locked_model_required')

    # Only original Config provides the manual values. The editable final and
    # private auto-owned physical files are read under the SAME destination
    # flock already acquired by commit_verified_owned_relocation(); no stale
    # PHP final-file reader and no nested GUI flock.
    def snapshot():
        current, _ = _target(writer.targets['auto'], writer.receipts.uid)
        known = read_owned(Path(owned_root), owner_uid=writer.receipts.uid)
        if known is None:
            raise VerifiedOwnedRefused('unknown_known_owned_origin')
        return ({**manual_hostlists, 'auto': current.decode('utf-8')},
                known, global_exclude)

    return commit_verified_owned_relocation(
        writer, pending, owned_root=owned_root, snapshot=snapshot,
        attest=attest, inspect=inspect, psl=psl)


def run_native_verified_owned_worker() -> None:
    raise VerifiedOwnedRefused('native_config_fd9_and_ack_not_authorized')


if __name__ == '__main__':
    run_native_verified_owned_worker()
