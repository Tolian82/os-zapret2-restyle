#!/usr/bin/env python3
"""Adapter-injected single-engine Voice cutover ordering contract (NOT WIRED).

This module has no CLI, no system commands and no router dependencies.
A future production adapter must implement durable intent, native Config
locking, one dvtws2, exact plugin-owned IPFW snapshots, safe rollback and
cold-boot review before exposing any GUI Apply. Even a passing mock test
is not permission to activate; all real operations remain disconnected.
"""
from __future__ import annotations

import re
from typing import Protocol

SHA = re.compile(r"^[a-f0-9]{64}$")


class CutoverError(RuntimeError):
    pass


class CutoverManualReview(CutoverError):
    """An ambiguous live state or rollback needs operator investigation."""


class CutoverRejected(CutoverError):
    """Candidate refused before any runtime changes."""


class CutoverAdapter(Protocol):
    def locks_held(self) -> bool: ...
    def verify_legacy_absent(self) -> None: ...
    def snapshot_previous(self) -> dict: ...
    def reverify_sources(self, proof: dict) -> None: ...
    def begin_intent(self, previous: dict, proof: dict) -> None: ...
    def mark_mutating(self) -> None: ...
    def install_candidate_tree(self) -> None: ...
    def stop_previous_engine(self) -> None: ...
    def start_candidate_engine(self) -> None: ...
    def install_owned_firewall(self) -> None: ...
    def start_candidate_supervisor(self) -> None: ...
    def verify_candidate(self) -> None: ...
    def persist_config(self) -> None: ...
    def commit_intent(self) -> None: ...
    def cleanup_retired(self) -> None: ...
    def finish_intent(self) -> None: ...
    def stop_candidate(self) -> None: ...
    def restore_config(self, previous: dict) -> None: ...
    def restore_tree(self, previous: dict) -> None: ...
    def restore_owned_firewall(self, previous: dict) -> None: ...
    def restore_previous_engine(self, previous: dict) -> None: ...
    def verify_previous(self, previous: dict) -> None: ...
    def abort_intent(self) -> None: ...


def validate_proof(proof: dict) -> None:
    if not isinstance(proof, dict) or proof.get("schema") != 1 or \
       proof.get("state") != "preflight-only" or \
       proof.get("activation_authorized") is not False:
        raise CutoverRejected("missing non-authorizing Voice handoff proof")
    for name in ("saved_xml_sha256", "merged_sha256", "native_argv_sha256"):
        if not isinstance(proof.get(name), str) or not SHA.fullmatch(proof[name]):
            raise CutoverRejected("candidate handoff fingerprint is invalid")
    enabled = proof.get("enabled_services")
    if not isinstance(enabled, list) or len(enabled) > 5 or \
       any(name not in ("telegram", "discord", "x", "sip", "custom")
           for name in enabled) or len(set(enabled)) != len(enabled):
        raise CutoverRejected("Voice service selection is malformed")
    for number in ("rule_base", "rule_max", "rule_count", "table_count"):
        if type(proof.get(number)) is not int:
            raise CutoverRejected("IPFW candidate range is malformed")
    if not 1 <= proof["rule_base"] <= proof["rule_max"] <= 65534 or \
       not 0 < proof["rule_count"] <= proof["rule_max"] - proof["rule_base"] + 1 or \
       not 0 <= proof["table_count"] == len(enabled):
        raise CutoverRejected("IPFW Voice rule/table ownership is inconsistent")


def simulate_cutover(adapter: CutoverAdapter, proof: dict, *,
                     test_only_mutations: bool = False) -> str:
    """Exercise stage/mutation/rollback order via injected test doubles ONLY.

    There is deliberately no production call site. A future implementation
    cannot just switch this flag in a configd action: it must first add
    concrete adapters, journal recovery and installed-native acceptance.
    """
    if not test_only_mutations:
        raise CutoverRejected("Voice cutover is not connected to OPNsense")
    validate_proof(proof)
    if not adapter.locks_held():
        raise CutoverRejected("native Config and lifecycle locks are required")
    # Neither probe may ever mutate. Verify no foreign or legacy PoC state:
    # the legacy transition must be an explicit separate adoption protocol.
    adapter.verify_legacy_absent()
    previous = adapter.snapshot_previous()
    if not isinstance(previous, dict) or not previous:
        raise CutoverRejected("missing trusted previous Config/runtime/IPFW snapshot")
    adapter.reverify_sources(proof)
    # Durable prepared + mutating intent MUST be fsync'd before first live
    # change. A failure here is an interrupted intent, NOT an implicit abort.
    adapter.begin_intent(previous, proof)
    try:
        adapter.mark_mutating()
    except Exception as exc:
        raise CutoverManualReview("cannot verify persisted mutating intent") from exc

    try:
        adapter.install_candidate_tree()
        adapter.stop_previous_engine()
        adapter.start_candidate_engine()
        adapter.install_owned_firewall()
        adapter.start_candidate_supervisor()
        adapter.verify_candidate()
        # Commit config only after the new engine, IPFW and supervisor pass
        # runtime verification. On failure restore saved previous Config too.
        adapter.persist_config()
        adapter.verify_candidate()
        adapter.commit_intent()
    except Exception as original:
        errors = []
        # Reverse EVERY component after an uncertain partial failure. The
        # methods must be idempotent; a failed command could have mutated
        # before reporting an error. Keep the durable intent until the
        # complete previous state has been independently verified.
        for operation in (
            adapter.stop_candidate,
            lambda: adapter.restore_config(previous),
            lambda: adapter.restore_tree(previous),
            lambda: adapter.restore_owned_firewall(previous),
            lambda: adapter.restore_previous_engine(previous),
            lambda: adapter.verify_previous(previous),
        ):
            try:
                operation()
            except Exception as error:
                errors.append(type(error).__name__)
        if errors:
            raise CutoverManualReview(
                "Voice cutover failed; rollback incomplete, durable intent retained"
            ) from original
        try:
            adapter.abort_intent()
        except Exception as exc:
            raise CutoverManualReview(
                "Voice previous state verified but pending intent cannot be cleared"
            ) from exc
        raise CutoverError("Voice candidate failed; verified previous state restored") from original

    # After a durable committed intent there is NO return to old Config,
    # because the operation may already have survived a power loss. Cleanup
    # must be retryable under the same lifecycle lock and never delete foreign
    # state or silently resolve an ambiguous partial transaction.
    try:
        adapter.cleanup_retired()
        adapter.verify_candidate()
        adapter.finish_intent()
    except Exception as exc:
        raise CutoverManualReview(
            "Voice committed but cleanup/reverification incomplete; review pending intent"
        ) from exc
    return "simulated-committed"
