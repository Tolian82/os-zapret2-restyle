#!/usr/bin/env python3
"""Read-only Voice IPFW ownership inspector for FreeBSD OPNsense.

Never modifies kernel, dvtws2, config.xml or ledger. Do not use this utility
as an unattended repair daemon. When ownership is not proven, report blocked.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from voice_firewall_ledger import LedgerError, VoiceOwnershipStore
from voice_cutover_journal import CutoverJournalError, VoiceCutoverJournal
from voice_ipfw_adapter import (FreeBSDIPFWAdapter, IPFWAdapterError,
                                shared_release_manifest)
from voice_firewall_transaction import verify_prior_state
from shared_apply_operation import (SharedApplyOperation, SharedOperationError,
                                    committed_owner)
from shared_apply_seal import WORK, SharedBundleError, verify_seal
from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError, table_contents_equal,
)


class VoiceInspectError(RuntimeError):
    pass


def examine(store, adapter, cutover=None) -> dict:
    """Inspect without side effects; 'ready' requires exact owned kernel state.

    An incomplete whole-runtime Config/engine/IPFW transition takes priority
    even if this moment's individual IPFW rules happen to appear correct.
    """
    if cutover is not None:
        phase = cutover.inspect()
        if phase != "no-intent":
            return {
                "state": "interrupted",
                "condition": phase,
                "can_activate": False,
                "remedy": "whole-runtime-manual-review",
            }
    if store.pending() is not None:
        condition = store.inspect(adapter)
        return {
            "state": "interrupted",
            "condition": condition,
            "can_activate": False,
            "remedy": "manual-inspection" if condition == "manual-review"
                      else "verified-recovery-required",
        }

    expected = store.owned()
    if expected is None:
        return {
            "state": "uninitialized",
            "can_activate": False,
            "remedy": "explicit-ownership-adoption-required",
        }
    if adapter.rule_base != expected["rule_base"] or \
       adapter.rule_max != expected["rule_max"]:
        return {"state": "mismatched-range", "can_activate": False,
                "remedy": "manual-inspection"}

    # Inspect *all* service tables (even if OFF) to catch foreign/stale
    # tables before enabling a service for the first time.
    observed = adapter.list_rules(expected["rule_base"], expected["rule_max"])
    if observed != expected["rules"]:
        return {"state": "foreign-or-modified-rules", "can_activate": False,
                "remedy": "manual-inspection"}
    for name in SERVICES:
        table = TABLE_PREFIX + name
        if not table_contents_equal(adapter.get_table(table), expected["tables"].get(table)):
            return {
                "state": "foreign-or-modified-table",
                "service": name,
                "can_activate": False,
                "remedy": "manual-inspection",
            }
        if adapter.get_table(table + "_stage") is not None:
            return {
                "state": "orphan-stage-table",
                "service": name,
                "can_activate": False,
                "remedy": "manual-inspection",
            }
    return {"state": "ready", "can_activate": True,
            "rule_count": len(observed), "table_count": len(expected["tables"])}



# Reuse the single dvtws2/monitor process owner, not five invented daemons.
COMMON_ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
COMMON_QUERY = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/process_query.sh")
CHILD_PID = Path("/var/run/dvtws2.pid")
MONITOR_PID = Path("/var/run/zapret2-supervisor-monitor.pid")
CHILD_EXEC = "/usr/local/etc/zapret2/binaries/my/dvtws2"
MONITOR_EXEC = "/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"


def _native_process_matches(pidfile: Path, expected: str) -> bool:
    """Read only the original PID and exact binary token, never scan/kill."""
    try:
        meta = pidfile.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or \
           meta.st_nlink != 1 or meta.st_mode & 0o022 or meta.st_size > 32:
            return False
        pid_text = pidfile.read_text("ascii").strip()
        if not re.fullmatch(r"[0-9]{1,10}", pid_text) or int(pid_text) <= 1:
            return False
        pid = int(pid_text)
        os.kill(pid, 0)
        result = subprocess.run(
            [str(COMMON_QUERY), "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=4, check=False,
        )
        if result.returncode != 0 or len(result.stdout) > 65536:
            return False
        # Match existing common_process_matches: absolute executable token.
        return f" {expected} " in f" {result.stdout.strip()} "
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return False


def _same_installed_file(source: Path, installed: Path) -> bool:
    """Bounded read-only comparison, rejecting foreign and linked artifacts."""
    try:
        original, active = source.lstat(), installed.lstat()
        if any(not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or
               s.st_uid != 0 or s.st_mode & 0o022 or s.st_size > 1048576
               for s in (original, active)):
            return False
        return hashlib.sha256(source.read_bytes()).digest() == \
               hashlib.sha256(installed.read_bytes()).digest()
    except OSError:
        return False


def inspect_common_runtime(release: Path, manifest: dict, *,
                           active: Path = COMMON_ACTIVE,
                           process_check=_native_process_matches,
                           installed_match=_same_installed_file) -> dict:
    """Independent engine and five profile configuration evidence.

    'running' means the original launcher and supervisor process identities
    exist, the active runtime plan+argv match the one sealed source, and IPFW
    has already been independently checked by the caller. It never proves
    packet passage, STUN response, Telegram call or end-to-end media.
    """
    plan_path = release / "voice-plan.json"
    try:
        if plan_path.stat().st_size > 1048576:
            raise VoiceInspectError("oversized common runtime plan")
        plan = json.loads(plan_path.read_bytes())
    except (OSError, ValueError, UnicodeError) as error:
        raise VoiceInspectError("common runtime plan unavailable") from error
    profiles = plan.get("profiles") if isinstance(plan, dict) else None
    capture = plan.get("capture") if isinstance(plan, dict) else None
    rows = capture.get("voice") if isinstance(capture, dict) else None
    if not isinstance(profiles, list) or not isinstance(rows, list) or \
       len(profiles) > len(SERVICES) or len(rows) > len(SERVICES):
        raise VoiceInspectError("invalid common Voice runtime profile plan")
    profile_names = []
    for entry in profiles:
        if not isinstance(entry, dict) or entry.get("enabled") is not True or \
           entry.get("service") not in SERVICES:
            raise VoiceInspectError("untrusted common Voice profile")
        profile_names.append(entry["service"])
    capture_names = []
    for entry in rows:
        if not isinstance(entry, dict) or entry.get("service") not in SERVICES:
            raise VoiceInspectError("untrusted common Voice capture")
        capture_names.append(entry["service"])
    # All three representations must describe exactly the same enabled set.
    # Without this, per-service readiness could be a misleading partial view.
    manifest_names = [
        name for name in SERVICES if f"{TABLE_PREFIX}{name}" in manifest["tables"]
    ]
    expected = [name for name in SERVICES if name in profile_names]
    if len(set(profile_names)) != len(profile_names) or \
       len(set(capture_names)) != len(capture_names) or \
       expected != [name for name in SERVICES if name in capture_names] or \
       expected != manifest_names:
        raise VoiceInspectError("common Voice runtime profile/IPFW disagreement")
    # Kernel ownership alone does not prove that the one running dvtws2
    # still reads the sealed profile and destination files. In particular,
    # an ordinary Strategies STUN selector may use the managed IPSET of a
    # DISABLED Voice service (no dedicated Voice IPFW table exists for it).
    # Compare those installed bytes as well before reporting GUI "ready".
    source = plan.get("source")
    if not isinstance(source, dict):
        raise VoiceInspectError("missing common Voice staging source")
    voice_hashes = source.get("ipset_sha256")
    ordinary_hashes = source.get("ordinary_scope_ipset_sha256")
    if not isinstance(voice_hashes, dict) or not isinstance(ordinary_hashes, dict):
        raise VoiceInspectError("missing common STUN scope evidence")
    for scopes in (voice_hashes, ordinary_hashes):
        for name, digest in scopes.items():
            if name not in SERVICES or not isinstance(digest, str) or (
                not re.fullmatch(r"[a-f0-9]{64}", digest)
            ):
                raise VoiceInspectError("untrusted common STUN scope evidence")
    if set(voice_hashes) != set(profile_names):
        raise VoiceInspectError("common Voice IPSET scope differs from enabled profiles")
    names = ["voice-plan.json", "dvtws.args", "traffic.conf"]
    names += [f"managed/ipset-{service}.txt" for service in SERVICES
              if service in voice_hashes or service in ordinary_hashes]
    active_source = all(installed_match(release / name, active / name)
                        for name in names)
    engine = bool(process_check(CHILD_PID, CHILD_EXEC))
    monitor = bool(process_check(MONITOR_PID, MONITOR_EXEC))
    if not active_source:
        runtime_state = "unverified-release"
    elif engine and monitor:
        runtime_state = "running"
    elif not engine and not monitor:
        runtime_state = "stopped"
    else:
        runtime_state = "partial"
    service_states = {
        name: {
            "configured": name in expected,
            "capture_verified": name in expected,
            "runtime_state": (
                "engine-present" if runtime_state == "running"
                else "engine-not-confirmed"
            ) if name in expected else "disabled",
            "media_verified": False,
        }
        for name in SERVICES
    }
    return {
        "state": runtime_state,
        "engine_verified": bool(engine and active_source),
        "supervisor_verified": bool(monitor and active_source),
        "source_verified": active_source,
        "services": service_states,
        "call_verified": False,
    }


def examine_shared(record: dict | None, *, work_root: Path = WORK,
                   bundle_verify=verify_seal,
                   manifest_reader=shared_release_manifest,
                   adapter_factory=FreeBSDIPFWAdapter,
                   runtime_probe=inspect_common_runtime) -> dict | None:
    """Read-only IPFW status of the ONE committed common Strategies/Voice owner.

    Native release ownership always dominates the obsolete Voice-only ledger.
    A pending transaction is never treated as an active predecessor; the
    original FD9 executor alone may reconcile that state. This routine does
    NOT authorize future Apply, engine health or MEDIA_PASS/CALL_PASS.
    """
    if record is None:
        return None
    phase = record["phase"]
    if phase not in ("committed", "restored"):
        return {
            "state": "interrupted", "condition": "shared-apply-" + phase,
            "can_activate": False, "remedy": "verified-recovery-required",
            "source": "native-common",
        }
    owner = committed_owner(record)
    if owner is None:
        return None
    operation_id = owner["id"]
    work = work_root / operation_id
    bundle_verify(work)
    plan = json.loads((work / "plan.json").read_bytes())
    if not isinstance(plan, dict) or plan.get("page") != owner["page"] or \
       plan.get("dependencies") != owner["base"] or \
       plan.get("changed_fields") != owner["changed_fields"]:
        raise VoiceInspectError("native common owner does not match sealed candidate")
    manifest = manifest_reader(work / "release")
    adapter = adapter_factory(manifest["rule_base"], manifest["rule_max"])
    runtime = runtime_probe(work / "release", manifest)
    if not isinstance(runtime, dict) or runtime.get("state") not in (
        "running", "stopped", "partial", "unverified-release"
    ):
        raise VoiceInspectError("untrusted common runtime evidence")
    if runtime["state"] == "stopped":
        # An intentionally stopped committed owner keeps its native Config
        # and sealed release for the next Start. Empty IPFW is the EXPECTED
        # successful Stop result, not a foreign or partially installed rule.
        empty = {
            "rule_base": manifest["rule_base"], "rule_max": manifest["rule_max"],
            "rules": {}, "tables": {},
        }
        try:
            verify_prior_state(adapter, empty, empty)
        except VoiceFirewallError:
            return {
                "state": "foreign-or-modified-rules", "source": "native-common",
                "condition": "common-stopped-with-kernel-objects",
                "can_activate": False, "remedy": "manual-inspection",
                "runtime": runtime,
            }
        return {
            "state": "stopped", "source": "native-common",
            "condition": "common-runtime-stopped",
            "can_activate": False, "rule_count": 0, "table_count": 0,
            "runtime": runtime,
        }
    if runtime["state"] != "running":
        # A partially present monitor/engine or a mismatched active release
        # must not display green even if the IPFW happens to look correct.
        return {
            "state": "interrupted", "source": "native-common",
            "condition": "common-runtime-" + runtime["state"],
            "can_activate": False, "remedy": "manual-inspection",
            "runtime": runtime,
        }
    try:
        verify_prior_state(adapter, manifest, manifest)
    except VoiceFirewallError:
        return {
            "state": "foreign-or-modified-rules", "source": "native-common",
            "can_activate": False, "remedy": "manual-inspection",
            "runtime": runtime,
        }
    return {
        "state": "ready", "source": "native-common",
        "condition": "common-runtime-and-ipfw-verified", "can_activate": False,
        "rule_count": len(manifest["rules"]),
        "table_count": len(manifest["tables"]),
        "runtime": runtime,
    }


def main(args: list[str]) -> int:
    if len(args) != 1:
        print("usage: voice_live_inspect.py", file=sys.stderr)
        return 64
    try:
        # A whole-runtime cutover intent is stronger than a momentary IPFW
        # observation: deny readiness even when the per-IPFW ledger is absent.
        cutover_dir = Path("/var/db/zapret2/voice-cutover")
        cutover = None
        if cutover_dir.exists() or cutover_dir.is_symlink():
            cutover = VoiceCutoverJournal(cutover_dir)
            status = cutover.inspect()
            if status != "no-intent":
                print(json.dumps({
                    "state": "interrupted", "condition": status,
                    "can_activate": False, "remedy": "whole-runtime-manual-review",
                }, sort_keys=True))
                return 2
        # Native common ownership supersedes the historic Voice-IPFW ledger.
        # The shared journal itself is root-owned and fails closed on corruption.
        shared = SharedApplyOperation().read()
        common = examine_shared(shared)
        if common is not None:
            print(json.dumps(common, sort_keys=True))
            return 0 if common["state"] == "ready" else 2
        # Fixed private path. The production code must explicitly prepare
        # the directory under the existing lifecycle lock after migration.
        directory = Path("/var/db/zapret2/voice-ipfw")
        if not directory.exists() and not directory.is_symlink():
            print(json.dumps({"state": "uninitialized", "can_activate": False,
                              "remedy": "explicit-ownership-adoption-required"},
                             sort_keys=True))
            return 2
        store = VoiceOwnershipStore(directory)
        adapter = FreeBSDIPFWAdapter(19000, 19010)
        report = examine(store, adapter, cutover)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["state"] == "ready" else 2
    except (OSError, ValueError, VoiceFirewallError, LedgerError,
            IPFWAdapterError, CutoverJournalError, SharedOperationError,
            SharedBundleError, VoiceInspectError) as error:
        # Never dump kernel rule text, sensitive config or tables to stdout.
        print(json.dumps({
            "state": "inspection-error",
            "can_activate": False,
            "remedy": "manual-inspection",
            "error": type(error).__name__,
        }, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
