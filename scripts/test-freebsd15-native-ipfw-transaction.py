#!/usr/bin/env python3
"""Stage 5: real FreeBSD 15.1 IPFW transaction/rollback in a disposable CI VM.

Opt-in only; NEVER execute on an installed OPNsense appliance.
Uses the production capture-plan compiler, transaction algorithm and native
FreeBSDIPFWAdapter. The VM is first attested as default-allow-only with no
plugin rules or Voice tables. No WAN traffic, OPNsense Config or dvtws2.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_capture_plan import compile_capture_plan
from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError,
    apply_transaction, cleanup_committed, prepare_desired,
    rollback_uncommitted, table_contents_equal, verify_prior_state,
)
from voice_ipfw_adapter import FreeBSDIPFWAdapter

MARKER = "STAGE5_NATIVE_TRANSACTION"
BASE = 19000
LAST = 19010
DIVERT = 9989
ORDINARY_TCP = "18080"
OPT_IN = "ZAPRET2_ISOLATED_FREEBSD_VM_TRANSACTION_TEST"


def load_native_guard(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"native VM guard missing: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(targets: dict[str, list[str]]) -> dict:
    """Use actual production plan and manifest compiler, not hand-coded IPFW rules."""
    profiles = []
    for service in SERVICES:
        if service not in targets:
            continue
        addresses = targets[service]
        profiles.append({
            "enabled": True,
            "service": service,
            "wan": "WAN",
            "ipset_path": (
                f"/usr/local/etc/zapret2/runtime-v2/managed/ipset-{service}.txt"
            ),
            "profile_sha256": hashlib.sha256(
                (service + "\n" + "\n".join(addresses)).encode("ascii")
            ).hexdigest(),
            "targets": addresses,
            "target_count": len(addresses),
            "ports": [[596, 599]],
        })
    capture = compile_capture_plan(
        {"schema": 1, "wan": "WAN", "profiles": profiles},
        BASE, LAST, DIVERT, physical_wan="lo0",
    )
    return prepare_desired(capture, ORDINARY_TCP, "")


class FailOneRuleInstall:
    """Inject one rejected kernel command, then allow the REAL rollback.

    This is an injected process-level failure, not a fake IPFW backend:
    all non-rejected operations execute against the actual FreeBSD kernel.
    """
    def __init__(self, number: int):
        self.number = number
        self.rejected = 0

    def __call__(self, argv, **kwargs):
        if self.rejected == 0 and argv[:4] == [
            "/sbin/ipfw", "-qf", "add", str(self.number),
        ]:
            self.rejected = 1
            return subprocess.CompletedProcess(
                argv, 75, stdout="", stderr="intentional isolated-VM fault"
            )
        return subprocess.run(argv, **kwargs)


def clean_vm(adapter, permitted_rules: dict[int, set[tuple[str, ...]]],
             permitted_tables: dict[str, list[list[str]]],
             default_rules: str) -> None:
    """Remove ONLY verified script-owned objects, never sweep numeric ranges."""
    installed = adapter.list_rules(BASE, LAST)
    for number, argv in installed.items():
        if tuple(argv) not in permitted_rules.get(number, set()):
            raise RuntimeError("unrecognized IPFW rule; refusing cleanup mutation")
    for name, alternatives in permitted_tables.items():
        observed = adapter.get_table(name)
        if observed is not None and not any(
            table_contents_equal(observed, candidate) for candidate in alternatives
        ):
            raise RuntimeError("unrecognized IPFW table; refusing cleanup mutation")
    for number in sorted(installed, reverse=True):
        adapter.delete_rule(number)
    for name in sorted(permitted_tables, reverse=True):
        if adapter.get_table(name) is not None:
            adapter.destroy_table(name)
    if adapter.list_rules(BASE, LAST):
        raise RuntimeError("IPFW rules remain after isolated VM cleanup")
    for name in permitted_tables:
        if adapter.get_table(name) is not None:
            raise RuntimeError("IPFW tables remain after isolated VM cleanup")
    final_rules = subprocess.run(
        ["/sbin/ipfw", "-q", "list"],
        capture_output=True, text=True, check=False, timeout=15,
    )
    if final_rules.returncode != 0 or final_rules.stdout != default_rules:
        raise RuntimeError("foreign IPFW rule baseline changed during VM test")


def run() -> int:
    if os.getenv(OPT_IN) != "1":
        print(f"{MARKER}=SKIP: isolated VM opt-in not set")
        return 0
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        print(f"{MARKER}=SKIP: requires disposable FreeBSD root")
        return 0

    table_guard = load_native_guard("test-freebsd15-native-ipfw-table.py", "table_guard")
    packet_guard = load_native_guard("test-freebsd15-native-ipfw-packet.py", "packet_guard")
    if not table_guard.prerequisite():
        print(f"{MARKER}=SKIP: native FreeBSD VM prerequisite absent")
        return 0
    version = subprocess.run(
        ["freebsd-version", "-u"], capture_output=True, text=True,
        check=False, timeout=15,
    )
    if version.returncode != 0 or not version.stdout.startswith("15.1"):
        raise RuntimeError("native transaction requires FreeBSD 15.1")
    packet_guard.ensure_guest_kernel_ready()

    adapter = FreeBSDIPFWAdapter(BASE, LAST, allow_mutations=True)
    baseline = subprocess.run(
        ["/sbin/ipfw", "-q", "list"], capture_output=True, text=True,
        check=False, timeout=15,
    )
    if baseline.returncode != 0 or not table_guard.safe_default_rules(baseline.stdout):
        raise RuntimeError("IPFW is not exclusively default-allow in disposable VM")
    permitted_names = [
        TABLE_PREFIX + service + suffix
        for service in SERVICES
        for suffix in ("", "_stage")
    ]
    if adapter.list_rules(BASE, LAST) or any(
        adapter.get_table(name) is not None for name in permitted_names
    ):
        raise RuntimeError("existing Voice kernel ownership; refusing mutation")

    previous = {"rule_base": BASE, "rule_max": LAST, "rules": {}, "tables": {}}
    first = manifest({"telegram": ["127.0.0.1", "::1"]})
    second = manifest({
        "telegram": ["127.0.0.1", "2001:db8::1"],
        "discord": ["198.51.100.10", "2001:db8:1::1"],
    })
    permitted_rules: dict[int, set[tuple[str, ...]]] = {}
    permitted_tables: dict[str, list[list[str]]] = {}
    for state in (first, second):
        for number, argv in state["rules"].items():
            permitted_rules.setdefault(number, set()).add(tuple(argv))
        for name, values in state["tables"].items():
            permitted_tables.setdefault(name, []).extend((values, []))
            permitted_tables.setdefault(name + "_stage", []).extend((values, []))

    try:
        apply_transaction(adapter, previous, first)
        cleanup_committed(adapter, previous, first)
        verify_prior_state(adapter, first, first)

        # Force rejection AFTER the old rule set has been deleted and the
        # first new rule has been added. Verify real IPFW restoration.
        fault = FailOneRuleInstall(BASE + 1)
        failing = FreeBSDIPFWAdapter(
            BASE, LAST, allow_mutations=True, runner=fault,
        )
        try:
            apply_transaction(failing, first, second)
        except VoiceFirewallError as error:
            if "previous owned state restored" not in str(error):
                raise RuntimeError("fault path did not report exact restoration") from error
        else:
            raise RuntimeError("injected FreeBSD rule-install rejection was ignored")
        if fault.rejected != 1:
            raise RuntimeError("native rule injection did not reach kernel cutover")
        verify_prior_state(adapter, first, first)

        # Also test rollback AFTER a successful native precommit cutover.
        apply_transaction(adapter, first, second)
        rollback_uncommitted(adapter, first, second)
        verify_prior_state(adapter, first, first)

        # Commit path must remove old snapshots and retain both families.
        apply_transaction(adapter, first, second)
        cleanup_committed(adapter, first, second)
        verify_prior_state(adapter, second, second)

        # Retire Discord and verify post-commit table cleanup preserves Telegram.
        apply_transaction(adapter, second, first)
        cleanup_committed(adapter, second, first)
        verify_prior_state(adapter, first, first)
    finally:
        clean_vm(adapter, permitted_rules, permitted_tables, baseline.stdout)

    print(
        f"{MARKER}=PASS: FreeBSD15.1 real dual-stack install/fault/"
        "rollback/commit/retire/cleanup"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as error:
        print(f"{MARKER}=FAIL: {error}", file=sys.stderr)
        sys.exit(1)
