#!/usr/bin/env python3
"""Staging-only five-resource read-only observer composition.

Binds a complete *previous-instance* observation for a pending Voice cutover:
current Config/runtime canonical hashes, current engine/supervisor process
instance tokens, and exact owner-private live kernel IPFW rule/table witness.

This does not certify that a NEW process after reboot is the restored old
process: PID/start tokens must differ and require a separate post-boot semantic
attestation. The caller must hold both native locks, inject independently
trusted read-only process and kernel adapters and call full recovery preflight.
No CLI, service lifecycle hooks, automatic restore or Voice Apply.
"""
from __future__ import annotations

from pathlib import Path

from voice_process_recovery_evidence import (
    _fingerprints, _normalize, inspect_process_evidence,
)
from voice_native_file_observer import LiveFileObserver
from voice_native_ipfw_ownership import observe_owned_ipfw


class NativePreviousObserver:
    """Prepare a five-resource sample; never authorize mutation on its own."""

    def __init__(self, *, config: Path, runtime: Path, previous_backup: Path,
                 process_evidence: Path, expected_executables: dict,
                 process_probe, firewall_store, firewall_adapter,
                 file_observer=None):
        self.files = (file_observer if file_observer is not None
                      else LiveFileObserver(config, runtime, previous_backup))
        self.previous_backup = Path(previous_backup)
        self.process_evidence = Path(process_evidence)
        self.expected_executables = dict(expected_executables)
        self.process_probe = process_probe
        self.firewall_store = firewall_store
        self.firewall_adapter = firewall_adapter

    def observe(self) -> dict[str,str]:
        """One read-only observation; five-way preflight double-samples it."""
        old = inspect_process_evidence(
            self.process_evidence, self.previous_backup, self.expected_executables,
        )
        saved_args = old["observation"]["engine"]["runtime_args_sha256"]
        file_fingerprints = self.files.observe()
        processes = _normalize(self.process_probe.probe(),
                               self.expected_executables, saved_args)
        process_fingerprints = _fingerprints(processes)
        firewall_fingerprint = observe_owned_ipfw(
            self.firewall_store, self.firewall_adapter,
        )
        # Re-open original sealed prior process evidence after all live reads,
        # so a torn/corrupted previous record cannot silently be accepted.
        again = inspect_process_evidence(
            self.process_evidence, self.previous_backup, self.expected_executables,
        )
        if again["previous"] != old["previous"]:
            raise ValueError("previous Voice process evidence changed while observing")
        return {**file_fingerprints, **process_fingerprints,
                "firewall": firewall_fingerprint}
