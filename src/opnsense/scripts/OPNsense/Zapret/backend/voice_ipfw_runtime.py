#!/usr/bin/env python3
"""Production FreeBSD IPFW executor for native Voice cutover.

This is a REAL kernel-mutating adapter behind the existing zapret_service.sh
FD9 lifecycle lock, never a separate daemon. There is deliberately no GUI
endpoint yet: actual Voice ON also requires Config, engine, supervisor and
reboot rollback in the same durable whole-system cutover.

Commands:
  seed      Verify and adopt the ALREADY RUNNING, Voice-OFF ordinary IPFW
            rules as prior trusted ownership. Never adopts the old PoC.
  activate  Install Voice+ordinary scoped rules with a durable PRECOMMIT
            ownership journal while the whole-system cutover is MUTATING.
            Retain old table snapshots until the entire service is ready.
  commit    Clean old IPFW tables and commit ownership ONLY after the
            whole-system cutover is durably COMMITTED.
  rollback  Restore the previous IPFW resources BEFORE whole-system commit,
            after the candidate dvtws2 has been stopped. Intent persists
            until Config/runtime/supervisor rollback is independently proven.

No caller-supplied paths or alternate IPFW binaries are accepted on FreeBSD.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import sys

from voice_firewall_ledger import (
    VoiceOwnershipStore, canonical_manifest, decode_manifest, fingerprint,
)
from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, verify_prior_state, apply_transaction,
    rollback_uncommitted, plan_postcommit_cleanup, cleanup_committed,
    table_contents_equal,
)
from voice_cutover_journal import VoiceCutoverJournal, BOUND_FIELD
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_freebsd_kernel_argv import parse_kernel_argv, sysctl_kernel_argv
from voice_freebsd_process_security import parse_kernel_path, sysctl_kernel_path

ACTIVE_ROOT = Path("/usr/local/etc/zapret2/runtime-v2")
CANDIDATE = ACTIVE_ROOT / "voice-native-candidate"
CONFIG = Path("/conf/config.xml")
LOCK = Path("/var/run/zapret2-lifecycle.lock")
LEDGER = Path("/var/db/zapret2/voice-ipfw")
WHOLE = Path("/var/db/zapret2/voice-cutover")
LEGACY_MARKER = Path("/var/run/zapret2-telegram-voice-poc.enabled")
LEGACY_TABLE = "zapret2_tgvoice"
ENGINE = "/usr/local/etc/zapret2/binaries/my/dvtws2"
PIDFILE = Path("/var/run/dvtws2.pid")
MAX_XML = 128 * 1048576
MAX_FILE = 4 * 1048576


class VoiceKernelRuntimeError(RuntimeError):
    pass


def _fail(reason: str) -> None:
    raise VoiceKernelRuntimeError(reason)


def _regular(path: Path, limit: int = MAX_FILE) -> bytes:
    if path.is_symlink() or not path.is_file():
        _fail("native Voice release file is not regular")
    info = path.stat()
    if info.st_uid != os.geteuid() or info.st_size > limit or info.st_nlink != 1:
        _fail("untrusted native Voice release file owner/size")
    return path.read_bytes()


def _hash_file(path: Path, limit: int) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        _fail("native Voice input is missing or oversized")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json_file(path: Path) -> dict:
    raw = _regular(path)
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise VoiceKernelRuntimeError("invalid native Voice JSON") from exc
    if not isinstance(result, dict):
        _fail("native Voice release record is not an object")
    return result


def require_native_lock() -> None:
    """Confirm FD9 refers to THE production lock and another FD contends.

    A process merely inheriting an unlocked FD9 must never masquerade as a
    lifecycle lock owner. FreeBSD /usr/bin/lockf -s uses flock semantics.
    """
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        _fail("native Voice IPFW actions require FreeBSD root")
    try:
        held, actual = os.fstat(9), os.stat(LOCK, follow_symlinks=False)
    except OSError as exc:
        raise VoiceKernelRuntimeError("existing lifecycle FD9 is required") from exc
    if not stat.S_ISREG(actual.st_mode) or actual.st_uid != 0 or \
       actual.st_dev != held.st_dev or actual.st_ino != held.st_ino:
        _fail("FD9 is not the existing Zapret2 lifecycle lock")
    test_fd = os.open(LOCK, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        try:
            fcntl.flock(test_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
        else:
            fcntl.flock(test_fd, fcntl.LOCK_UN)
            _fail("FD9 is open but the lifecycle lock is not held")
    finally:
        os.close(test_fd)


def load_candidate() -> tuple[dict, dict]:
    """Verify exact release-local IPFW digest + one-engine provenance."""
    if CANDIDATE.is_symlink() or not CANDIDATE.is_dir():
        _fail("native Voice candidate is missing")
    manifest = _json_file(CANDIDATE / "desired-ipfw.json")
    desired = decode_manifest(manifest)
    proof = _json_file(CANDIDATE / "handoff-proof.json")
    metadata = _json_file(CANDIDATE / "metadata.json")
    if proof.get("schema") != 1 or proof.get("state") != "preflight-only" or \
       proof.get("activation_authorized") is not False or \
       proof.get("desired_ipfw_sha256") != fingerprint(manifest):
        _fail("candidate IPFW does not match bounded handoff proof")
    if metadata.get("activation_authorized") is not False or \
       metadata.get("saved_xml_sha256") != proof.get("saved_xml_sha256"):
        _fail("candidate settings are not an inert pinned release")
    if _hash_file(CONFIG, MAX_XML) != proof["saved_xml_sha256"]:
        _fail("OPNsense Config changed after candidate compilation")
    native_argv = CANDIDATE / "dvtws.args"
    if _hash_file(native_argv, MAX_FILE) != proof.get("native_argv_sha256"):
        _fail("native dvtws2 argument file differs from approved handoff")
    if _hash_file(ACTIVE_ROOT / "dvtws.args", MAX_FILE) != proof["native_argv_sha256"]:
        _fail("the active runtime is NOT the approved native Voice engine")
    if desired["rule_base"] != 19000 or desired["rule_max"] != 19010:
        _fail("candidate IPFW interval differs from production plugin ownership")
    return desired, proof


def require_no_legacy(adapter: FreeBSDIPFWAdapter) -> None:
    if LEGACY_MARKER.exists() or LEGACY_MARKER.is_symlink():
        _fail("legacy Telegram Voice PoC marker exists; do not auto-adopt")
    if (ACTIVE_ROOT / "telegram-voice-poc.state").read_text().strip() != "disabled":
        _fail("active runtime contains the legacy Telegram Voice PoC")
    # The legacy table belongs to a different owner and is never adopted
    # into the canonical five-service Voice ownership manifest.
    if adapter._run("table", LEGACY_TABLE, "info", allow_missing=True) is not None:
        _fail("legacy Telegram Voice IPFW table still exists")
    if adapter._run("table", LEGACY_TABLE + "_stage", "info",
                    allow_missing=True) is not None:
        _fail("legacy Telegram Voice staging table still exists")


def require_engine_process(proof: dict) -> None:
    """Require exact kernel-exposed argv of one live candidate process.

    PID and argv checks alone do not certify media pass or full readiness;
    caller must also complete the whole-system supervisor cutover.
    """
    raw = _regular(PIDFILE, 40).strip()
    if not raw.isdecimal() or not 1 < int(raw) < 4194304:
        _fail("native Voice dvtws2 PID is missing or invalid")
    pid = int(raw)
    binary = parse_kernel_path(sysctl_kernel_path(pid))
    if binary != ENGINE:
        _fail("candidate engine PID refers to a different executable")
    actual = parse_kernel_argv(sysctl_kernel_argv(pid))
    expected = [ENGINE]
    for row in _regular(CANDIDATE / "dvtws.args").decode("utf-8").splitlines():
        expected.extend(row.split())
    expected += ["--sockarg=0x200", "--user=nobody"]
    if actual != expected:
        _fail("live dvtws2 kernel arguments differ from native Voice candidate")
    if _regular(PIDFILE, 40).strip() != raw:
        _fail("dvtws2 PID changed while checking native engine")


def seed_verified(store: VoiceOwnershipStore, adapter, desired: dict) -> str:
    """One-time audited ownership of existing Voice-OFF ordinary rules."""
    if store.pending() is not None:
        _fail("unfinished IPFW intent blocks initial ownership")
    if store.owned() is not None:
        if store.owned() != desired:
            _fail("already seeded IPFW ownership differs from live ordinary release")
        verify_prior_state(adapter, desired, desired)
        return "already-owned"
    # A fresh seed requires *no* Voice rule/table and exact live ordinary
    # rules generated by the current OPNsense release.
    verify_prior_state(adapter, desired, desired)
    store.seed(desired)
    return "seeded"


def _whole_matches(whole: VoiceCutoverJournal, desired: dict,
                   proof: dict, required_phase: str) -> None:
    record = whole.read()
    if record is None or record.get("schema", 0) < 2 or \
       record.get("phase") != required_phase or \
       record["candidate"].get(BOUND_FIELD) != fingerprint(canonical_manifest(desired)) or \
       record["candidate"].get("native_argv_sha256") != proof.get("native_argv_sha256"):
        _fail("no matching durable whole-system Voice cutover at required phase")


def activate_verified(store: VoiceOwnershipStore, adapter, desired: dict,
                      whole: VoiceCutoverJournal, proof: dict) -> str:
    """Install real IPFW with durable PRECOMMIT intent, never finalize early.

    The new one-engine dvtws2 must already be running, but the supervisor
    and Config are not yet transactionally committed. Keep both old table
    snapshots and old ownership until the entire system commits or rolls
    back. This is the kernel half of the complete Voice cutover.
    """
    _whole_matches(whole, desired, proof, "mutating")
    previous = store.owned()
    if previous is None or store.pending() is not None:
        _fail("IPFW ownership is absent or a prior cutover is still pending")
    verify_prior_state(adapter, previous, desired)
    store.begin(previous, desired)
    store.mark_mutating()
    try:
        apply_transaction(adapter, previous, desired)
    except Exception:
        # Only a fully restored previous state permits clearing the durable
        # intent. Ambiguous kernel state stays blocked across reboot.
        if store.inspect(adapter) == "previous-intact":
            store.abort(adapter)
        raise
    # The former target sets must still be available for a later rollback.
    plan_postcommit_cleanup(adapter, previous, desired)
    return "installed-pending-whole-commit"


def rollback_precommit_verified(store: VoiceOwnershipStore, adapter,
                                whole: VoiceCutoverJournal, proof: dict) -> str:
    """Restore the previous IPFW rules only while whole cutover is MUTATING.

    The production CLI refuses to roll back unless the candidate PID file
    has been removed by the overall orchestrator's launcher_stop operation.
    The whole Config/runtime/supervisor journal remains pending until
    independent previous-state recovery verification finishes.
    """
    pending = store.pending()
    if pending is None or pending["phase"] != "mutating":
        _fail("no uncommitted Voice IPFW transaction to roll back")
    from voice_firewall_ledger import decode_manifest
    previous = decode_manifest(pending["previous"])
    desired = decode_manifest(pending["desired"])
    _whole_matches(whole, desired, proof, "mutating")
    if store.owned() != previous:
        _fail("previous IPFW owner has already changed; rollback requires review")
    if store.inspect(adapter) == "previous-intact":
        store.abort(adapter)
        return "already-previous"
    rollback_uncommitted(adapter, previous, desired)
    store.abort(adapter)
    return "restored-previous"


def commit_verified(store: VoiceOwnershipStore, adapter,
                    whole: VoiceCutoverJournal, proof: dict) -> str:
    """Finish IPFW only AFTER the whole-engine/Config/supervisor commit."""
    pending = store.pending()
    if pending is None or pending["phase"] != "mutating":
        _fail("missing pending Voice IPFW ownership commit")
    from voice_firewall_ledger import decode_manifest
    previous = decode_manifest(pending["previous"])
    desired = decode_manifest(pending["desired"])
    _whole_matches(whole, desired, proof, "committed")
    old_owner = store.owned()
    if old_owner not in (previous, desired):
        _fail("IPFW ownership changed outside the Voice cutover")
    # The running desired rules, all active tables AND saved previous-stage
    # snapshots must still agree with the durable intent.
    plan_postcommit_cleanup(adapter, previous, desired)
    if old_owner == previous:
        store.commit(desired)
    cleanup_committed(adapter, previous, desired)
    store.finish(adapter)
    return "committed"


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("seed", "activate", "commit", "rollback"):
        print("usage: voice_ipfw_runtime.py seed|activate|commit|rollback", file=sys.stderr)
        return 64
    try:
        require_native_lock()
        desired, proof = load_candidate()
        if argv[1] == "seed":
            # An otherwise successful seed would make the ordinary legacy
            # lifecycle refuse further restarts as soon as the ledger owns
            # the plugin IPFW range. NEVER seed ahead of a complete,
            # separately prepared whole-system rollback transaction.
            from voice_cutover_backup import bound_resource_fingerprints
            intent = VoiceCutoverJournal(WHOLE).read()
            if intent is None or intent.get("phase") != "prepared" or \
               intent.get("schema", 0) < 2:
                _fail("native IPFW seed requires a prepared whole-service cutover")
            bound_resource_fingerprints(WHOLE / "previous", intent["previous"])
            # Persistent /var/db state is created only by an explicit
            # lifecycle-owned adoption operation, never by status or import.
            for directory in (LEDGER.parent, LEDGER):
                if directory.is_symlink():
                    _fail("unsafe Voice IPFW ledger directory")
                directory.mkdir(mode=0o700, exist_ok=True)
                info = directory.stat()
                if info.st_uid != 0 or info.st_mode & 0o077:
                    _fail("persistent Voice ledger directory is not root-private")
        store = VoiceOwnershipStore(LEDGER)
        adapter = FreeBSDIPFWAdapter(19000, 19010,
                                    allow_mutations=argv[1] in ("activate", "commit", "rollback"))
        if argv[1] == "seed":
            if proof.get("enabled_services") or desired["tables"]:
                _fail("only all-OFF ordinary runtime may be adopted")
            require_no_legacy(adapter)
            require_engine_process(proof)
            result = seed_verified(store, adapter, desired)
        else:
            if not proof.get("enabled_services"):
                _fail("native IPFW cutover requires at least one enabled Voice service")
            require_no_legacy(adapter)
            whole = VoiceCutoverJournal(WHOLE)
            if argv[1] == "rollback":
                # The overall orchestrator must stop the candidate FIRST,
                # then revert IPFW, restore tree/Config/previous engine and
                # only afterwards abort the durable whole-cutover journal.
                if PIDFILE.exists() or PIDFILE.is_symlink():
                    _fail("stop the candidate dvtws2 before Voice IPFW rollback")
                result = rollback_precommit_verified(
                    store, adapter, whole, proof
                )
            else:
                require_engine_process(proof)
                pid_before = _regular(PIDFILE, 40).strip()
                if argv[1] == "activate":
                    result = activate_verified(
                        store, adapter, desired, whole, proof
                    )
                else:
                    result = commit_verified(
                        store, adapter, whole, proof
                    )
                require_engine_process(proof)
                if _regular(PIDFILE, 40).strip() != pid_before:
                    _fail("Voice engine instance changed during IPFW transaction")
        print("native-voice-ipfw=" + result)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print("ERROR: native Voice IPFW operation refused: " + str(error),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
