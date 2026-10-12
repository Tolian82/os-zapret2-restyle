#!/usr/bin/env python3
"""Stage 3: audited ONE-TIME ordinary IPFW owner bootstrap.

Import-only, no CLI/configd/GUI/boot entrypoint. A future single-FD9 native
prepare coordinator must call this *immediately before* previous evidence and
PREPARED. Persisting the owner deliberately blocks the legacy service on a
power cut, until native recovery/owner reconciliation (never auto-unseed).
The kernel is READ ONLY: seed_verified persists ONLY a durable ledger owner.
"""
from __future__ import annotations

from pathlib import Path

from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, fingerprint
from voice_firewall_transaction import prepare_desired
from voice_handoff_preflight import _ordinary_ports
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_live_preflight import inspect_live_preflight, _current_engine_args
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_cutover_guard import check_pending
from voice_ipfw_runtime import require_no_legacy, seed_verified


class InitialIPFWSeedError(RuntimeError):
    pass


def bootstrap_native_ordinary_ipfw_owner(
    *, whole_root, ledger: VoiceOwnershipStore, config_path, active_runtime,
    ordinary_source, physical_wan, divert_port, probe: FreeBSDVoiceProcessProbe,
    kernel_reader: FreeBSDKernelArgvReader, ipfw_adapter: FreeBSDIPFWAdapter,
    config_fd, config_owner, require_lifecycle_owner,
) -> dict:
    """Prove ordinary IPFW with independent runtime argv and source ports.

    Rule numbers, port selectors and WAN are derived from existing production
    firewall compiler, NEVER copied from the observed kernel as new authority.
    IPFW ownership must be absent. A failed post-seed check keeps the owner
    and blocks the legacy wrapper; there is no unsafe automatic unseed.
    """
    if not isinstance(ledger, VoiceOwnershipStore) or (
        not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(ipfw_adapter, FreeBSDIPFWAdapter)
        or ipfw_adapter.allow_mutations is not False
        or (ipfw_adapter.rule_base, ipfw_adapter.rule_max) != (19000, 19010)
        or not callable(require_lifecycle_owner)
    ):
        raise InitialIPFWSeedError("untrusted native ordinary owner sources")

    def held():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)

    held()
    if ledger.owned() is not None or ledger.pending() is not None or (
        check_pending(Path(whole_root), ledger.directory) != {
            "state": "clear", "safe_to_mutate": True
        }
    ):
        raise InitialIPFWSeedError("native owner is already seeded or recovery pending")
    # This native preflight validates all 3 PID/start epochs, kernel argv,
    # kernel image and ordinary-only IPFW structure; it does NOT claim owner.
    report = inspect_live_preflight(
        config_path=Path(config_path), active_runtime=Path(active_runtime),
        whole_root=Path(whole_root), ledger_root=ledger.directory,
        probe=probe, kernel_reader=kernel_reader, ipfw_adapter=ipfw_adapter,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if report["state"] != "live-legacy-process-argv-observed-not-readiness" or (
        report["kernel_ipfw_voice_tables"] != "absent"
        or report["kernel_ipfw_legacy_table"] != "absent"
    ):
        raise InitialIPFWSeedError("legacy-free ordinary live baseline not proven")
    require_no_legacy(ipfw_adapter)
    source = Path(ordinary_source)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 4194304:
        raise InitialIPFWSeedError("missing or oversized ordinary Strategy source")
    raw = source.read_bytes()
    if not raw or any(value not in (9, 10, 13) and not 32 <= value <= 126 for value in raw):
        raise InitialIPFWSeedError("ordinary Strategies contain non-ASCII bytes")
    ordinary = raw.decode("ascii")
    tcp, udp = _ordinary_ports(ordinary)
    if not tcp and not udp:
        raise InitialIPFWSeedError("ordinary Strategies have no capture ports")
    engine, old_argv_hash, _, _ = _current_engine_args(Path(active_runtime))
    content = ordinary.split()
    positions = [
        idx for idx in range(len(engine) - len(content) + 1)
        if engine[idx:idx + len(content)] == content
    ]
    if not content or len(positions) != 1:
        raise InitialIPFWSeedError("ordinary Strategies do not match one live generator segment")
    ports = [value[7:] for value in engine if value.startswith("--port=")]
    if ports != [str(divert_port)] or type(divert_port) is not int or (
        not 1 <= divert_port <= 65535
    ):
        raise InitialIPFWSeedError("divert port differs from running generator")
    capture = {
        "schema": 1, "rule_base": 19000, "rule_max": 19010,
        "ordinary_rule_base": 19000, "divert_port": divert_port,
        "wan": physical_wan, "voice": [],
    }
    desired = prepare_desired(capture, tcp, udp)
    if desired["tables"] or not desired["rules"]:
        raise InitialIPFWSeedError("initial adoption is only for ordinary IPFW")
    # Never infer ownership from the structural preflight alone. The exact
    # generated argv MUST match every numbered kernel rule and zero tables.
    from voice_firewall_transaction import verify_prior_state
    verify_prior_state(ipfw_adapter, desired, desired)
    held()
    if ledger.owned() is not None or ledger.pending() is not None:
        raise InitialIPFWSeedError("IPFW owner raced initial adoption")
    if _current_engine_args(Path(active_runtime))[1] != old_argv_hash or (
        check_pending(Path(whole_root), ledger.directory) != {
            "state": "clear", "safe_to_mutate": True
        }
    ):
        raise InitialIPFWSeedError("native Config/runtime or journal drifted")
    require_no_legacy(ipfw_adapter)
    result = seed_verified(ledger, ipfw_adapter, desired)
    if result != "seeded" or (
        observe_owned_ipfw(ledger, ipfw_adapter) != fingerprint(canonical_manifest(desired))
    ):
        raise InitialIPFWSeedError("fresh native IPFW owner failed post-seed attestation")
    held()
    return {
        "state": "native-ordinary-ipfw-owner-sealed",
        "owned_ipfw_sha256": fingerprint(canonical_manifest(desired)),
        "previous": desired,
        "safe_to_enable_voice": False,
        "must_continue_prepared_under_same_locks": True,
    }
