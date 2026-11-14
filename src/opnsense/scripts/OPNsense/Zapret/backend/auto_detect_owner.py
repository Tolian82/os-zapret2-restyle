#!/usr/bin/env python3
"""#1052 P2c: read-only shared-Apply/generation owner binding (not a worker).

A PID or a detached P0 map cannot authorize auto-list mutation. The original
common Apply journal, sealed release, installed exact argv, unique current
engine, original launcher PID, supervisor and producer map must ALL agree.
No producer of the required release map exists yet: current real deployments
fail closed until the ORIGINAL generator is integrated in the next P2 gate.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from auto_detect_fd import OwnerToken, _owner_snapshot
from global_exclusions import ExclusionError, segments
from shared_apply_operation import SharedApplyOperation, SharedOperationError, committed_owner, TERMINAL
from shared_apply_seal import WORK, SharedBundleError, verify_seal
from voice_live_inspect import (
    CHILD_EXEC, CHILD_PID, MONITOR_EXEC, MONITOR_PID, COMMON_ACTIVE,
)

MAP_NAME = "auto-detect-generation.json"
MAX_MAP = 1024 * 1024
MAX_ARGS = 256 * 1024
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX32 = re.compile(r"^[a-f0-9]{32}$")
ALLOWED = frozenset((
    "known-hostlist", "excluded-voice", "excluded-stun", "excluded-ipset",
    "unknown-import", "unknown-native-list", "unknown-extra", "unknown-source",
    "unknown-native-default", "non-executable-template", "non-executable-skip",
    "observer",
))


class GenerationRefused(ValueError):
    """Never turn an unknown or stale owner into an authorized target."""


@dataclass(frozen=True)
class GenerationProof:
    owner: OwnerToken
    operation_id: str
    generation: str
    final_args_sha256: str
    raw_path: str
    debug_path: str
    observer_native_number: int
    profiles: tuple[tuple[int | None, str, str | None], ...]


def _secure_bytes(path: Path, limit: int, owner_uid: int) -> bytes:
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_uid != owner_uid or before.st_mode & 0o022
            or not 0 < before.st_size <= limit):
        raise GenerationRefused("untrusted_protected_artifact")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        pinned = os.fstat(fd)
        if (pinned.st_dev, pinned.st_ino, pinned.st_size) != (
                before.st_dev, before.st_ino, before.st_size):
            raise GenerationRefused("changed_protected_artifact")
        data = os.read(fd, limit + 1)
        after = os.fstat(fd)
        if len(data) > limit or (pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise GenerationRefused("racing_protected_artifact")
        return data
    finally:
        os.close(fd)


def _pid(path: Path, uid: int) -> int:
    value = _secure_bytes(path, 32, uid).decode("ascii").strip()
    if not re.fullmatch(r"[0-9]{1,10}", value) or int(value) <= 1:
        raise GenerationRefused("invalid_launcher_pid")
    return int(value)


def _run(runner, argv: list[str]) -> str:
    result = runner(argv, capture_output=True, text=True, timeout=5, check=False)
    if (result.returncode != 0 or result.stderr or not result.stdout
            or len(result.stdout) > 131072):
        raise GenerationRefused("native_process_query_unavailable")
    return result.stdout


def _snapshot(runner, pid: int) -> tuple[str, list[str]]:
    lines = _run(runner, ["/bin/ps", "-ww", "-p", str(pid), "-o", "lstart=",
                          "-o", "command="]).strip().splitlines()
    if len(lines) != 1:
        raise GenerationRefused("missing_or_ambiguous_process")
    parts = lines[0].split(maxsplit=5)
    if len(parts) != 6:
        raise GenerationRefused("invalid_process_start")
    return " ".join(parts[:5]), parts[5].split()


def _valid_map(raw: bytes, owner: dict, argv: bytes) -> tuple[dict, tuple]:
    try:
        data = json.loads(raw)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise GenerationRefused("corrupt_generation_map") from exc
    required = {"schema", "generation", "evidence", "owner_operation_id",
                "owner_candidate_sha256", "final_args_sha256", "mode",
                "raw_path", "debug_path", "observer_native_number", "profiles"}
    if (not isinstance(data, dict) or set(data) != required or
            type(data["schema"]) is not int or data["schema"] != 2 or
            data["evidence"] != "ORIGINAL_SHARED_GENERATOR_CAPTURE" or
            data["mode"] != "auto" or
            data["owner_operation_id"] != owner["id"] or
            data["generation"] != owner["id"] or
            data["owner_candidate_sha256"] != owner["candidate"] or
            data["final_args_sha256"] != hashlib.sha256(argv).hexdigest()):
        raise GenerationRefused("stale_or_unauthorized_generation")
    for name in ("raw_path", "debug_path"):
        value = data[name]
        if (not isinstance(value, str) or not value.startswith("/")
                or len(value) > 512 or "\x00" in value or
                any(segment in ("", ".", "..") for segment in value[1:].split("/"))):
            raise GenerationRefused("unsafe_native_observation_path")
    if data["raw_path"] == data["debug_path"]:
        raise GenerationRefused("overlapping_raw_and_debug")
    tokens = argv.decode("utf-8").split()
    for flag, expected in (
        ("--hostlist-auto=", data["raw_path"]),
        ("--hostlist-auto-debug=", data["debug_path"]),
    ):
        matches = [t[len(flag):] for t in tokens if t.startswith(flag)]
        if matches != [expected]:
            raise GenerationRefused("observation_path_differs_from_native_argv")
    # The actual observer must be the trailing, no-action native profile.
    # An earlier action profile would affect first-match behavior; a guessed
    # observer number in metadata is never sufficient evidence.
    rows = segments(argv.decode("utf-8"))
    if not rows:
        raise GenerationRefused("missing_native_observer")
    observer_row = rows[-1]
    if ("--hostlist-auto=" + data["raw_path"] not in observer_row or
            "--hostlist-auto-retrans-reset=0" not in observer_row or
            any(t.startswith(("--lua-desync", "--import", "--ipset=",
                              "--hostlist=", "--payload")) for t in observer_row)):
        raise GenerationRefused("observer_has_action_or_unauthorized_selector")
    profiles = data["profiles"]
    if not isinstance(profiles, list) or not 1 <= len(profiles) <= 256:
        raise GenerationRefused("invalid_native_profile_map")
    seen = set()
    frozen = []
    for row in profiles:
        if not isinstance(row, dict) or set(row) != {"native_number", "status", "hostlist"}:
            raise GenerationRefused("invalid_native_profile_row")
        no, status, hostlist = row["native_number"], row["status"], row["hostlist"]
        if (no is not None and (type(no) is not int or no < 0 or no > 255)
                or status not in ALLOWED or
                hostlist is not None and (
                    not isinstance(hostlist, str) or
                    not re.fullmatch("[a-z][a-z0-9_-]{0,63}", hostlist))
                or status == "known-hostlist" and hostlist is None
                or status != "known-hostlist" and hostlist is not None
                or no in seen):
            raise GenerationRefused("ambiguous_or_invalid_native_profile")
        if no is not None:
            seen.add(no)
        frozen.append((no, status, hostlist))
    observer = data["observer_native_number"]
    if (type(observer) is not int or observer <= 0 or observer > 255
            or frozen.count((observer, "observer", None)) != 1
            or max((n for n in seen if n > 0), default=0) != observer
            or {n for n in seen if n > 0} != set(range(1, observer + 1))):
        raise GenerationRefused("observer_does_not_match_final_native_map")
    if (0, "unknown-native-default", None) not in frozen:
        raise GenerationRefused("missing_native_default")
    return data, tuple(frozen)


def _attest_core(*, journal: Path, work_root: Path, active: Path,
                 child_pidfile: Path, monitor_pidfile: Path,
                 runner, owner_uid: int,
                 epoch_finalizing_operation: str | None = None) -> GenerationProof:
    record = SharedApplyOperation(journal, owner=owner_uid).read()
    if epoch_finalizing_operation is None:
        # Public worker and ACK never trust an unfinished original epoch.
        if record is None or record["phase"] not in TERMINAL:
            raise GenerationRefused("missing_terminal_common_owner")
        owner = committed_owner(record)
    else:
        # Only the FD9-only entry below passes this exact operation identity.
        if (not isinstance(epoch_finalizing_operation, str) or
                not HEX32.fullmatch(epoch_finalizing_operation) or
                record is None or record["phase"] != "epoch-finalizing" or
                record["detail"]["id"] != epoch_finalizing_operation):
            raise GenerationRefused("unqualified_original_epoch_finalization")
        owner = record["detail"]
    if owner is None or not HEX32.fullmatch(owner["id"]) or not HEX64.fullmatch(owner["candidate"]):
        raise GenerationRefused("missing_committed_common_owner")
    work = work_root / owner["id"]
    verify_seal(work, owner=owner_uid)
    plan = json.loads(_secure_bytes(work / "plan.json", 4 * 1024 * 1024, owner_uid))
    if (not isinstance(plan, dict) or plan.get("page") != owner["page"]
            or plan.get("dependencies") != owner["base"]
            or plan.get("changed_fields") != owner["changed_fields"]):
        raise GenerationRefused("candidate_is_not_committed_owner")
    sealed_argv = _secure_bytes(work / "release" / "dvtws.args", MAX_ARGS, owner_uid)
    active_argv = _secure_bytes(active / "dvtws.args", MAX_ARGS, owner_uid)
    if sealed_argv != active_argv:
        raise GenerationRefused("active_runtime_not_same_sealed_argv")
    raw_map = _secure_bytes(work / "release" / MAP_NAME, MAX_MAP, owner_uid)
    active_map = _secure_bytes(active / MAP_NAME, MAX_MAP, owner_uid)
    if raw_map != active_map:
        raise GenerationRefused("active_generation_not_same_sealed_map")
    mapping, profiles = _valid_map(raw_map, owner, sealed_argv)

    pid, monitor = _pid(child_pidfile, owner_uid), _pid(monitor_pidfile, owner_uid)
    birth, command = _snapshot(runner, pid)
    expected = [CHILD_EXEC] + sealed_argv.decode("utf-8").split() + [
        "--sockarg=0x200", "--user=nobody"]
    if command != expected:
        raise GenerationRefused("running_engine_argv_differs_from_sealed_owner")
    _, monitor_command = _snapshot(runner, monitor)
    if not monitor_command or monitor_command[0] != MONITOR_EXEC or monitor == pid:
        raise GenerationRefused("missing_common_supervisor")
    census = _run(runner, ["/bin/ps", "-A", "-ww", "-o", "pid=", "-o", "command="])
    actual = []
    for line in census.splitlines():
        row = line.split()
        if len(row) >= 2 and row[1] == CHILD_EXEC:
            if not row[0].isdigit():
                raise GenerationRefused("untrusted_engine_census")
            actual.append(int(row[0]))
    if actual != [pid]:
        raise GenerationRefused("foreign_or_duplicate_engine")
    token = OwnerToken(pid, birth, CHILD_EXEC)
    if not _owner_snapshot(token, runner):
        raise GenerationRefused("engine_birth_or_executable_changed")
    if (_pid(child_pidfile, owner_uid), _pid(monitor_pidfile, owner_uid)) != (pid, monitor):
        raise GenerationRefused("launcher_owner_changed")
    if _snapshot(runner, pid) != (birth, command):
        raise GenerationRefused("engine_changed_during_owner_read")
    if SharedApplyOperation(journal, owner=owner_uid).read() != record:
        raise GenerationRefused("common_owner_changed_during_read")
    if (_secure_bytes(active / "dvtws.args", MAX_ARGS, owner_uid) != sealed_argv or
            _secure_bytes(active / MAP_NAME, MAX_MAP, owner_uid) != raw_map):
        raise GenerationRefused("active_release_changed_during_read")
    return GenerationProof(token, owner["id"], mapping["generation"],
                           mapping["final_args_sha256"], mapping["raw_path"],
                           mapping["debug_path"], mapping["observer_native_number"],
                           profiles)


def attest_running_generation(*, journal: Path = Path("/var/db/zapret2/shared-apply"),
                              work_root: Path = WORK, active: Path = COMMON_ACTIVE,
                              child_pidfile: Path = CHILD_PID,
                              monitor_pidfile: Path = MONITOR_PID,
                              runner=subprocess.run) -> GenerationProof:
    """Read-only native check; caller must re-attest immediately before ack.

    A passing snapshot is NOT a commit result and is NOT retained across ticks.
    """
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise GenerationRefused("root_freebsd_only")
    try:
        return _attest_core(journal=journal, work_root=work_root, active=active,
                            child_pidfile=child_pidfile, monitor_pidfile=monitor_pidfile,
                            runner=runner, owner_uid=0)
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.SubprocessError,
            SharedOperationError, SharedBundleError, ExclusionError) as exc:
        raise GenerationRefused("generation_owner_not_attested") from exc


def attest_epoch_finalizing_generation(operation_id: str, *,
                                       journal: Path = Path("/var/db/zapret2/shared-apply"),
                                       work_root: Path = WORK,
                                       active: Path = COMMON_ACTIVE,
                                       child_pidfile: Path = CHILD_PID,
                                       monitor_pidfile: Path = MONITOR_PID,
                                       runner=subprocess.run) -> GenerationProof:
    """Same-original-FD9 precommit proof, not a worker/ACK owner."""
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation_id, str) or
            not HEX32.fullmatch(operation_id)):
        raise GenerationRefused("native_root_epoch_finalizing_fd9_required")
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        return _attest_core(
            journal=journal, work_root=work_root, active=active,
            child_pidfile=child_pidfile, monitor_pidfile=monitor_pidfile,
            runner=runner, owner_uid=0,
            epoch_finalizing_operation=operation_id)
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.SubprocessError,
            SharedOperationError, SharedBundleError, ExclusionError) as exc:
        raise GenerationRefused("original_epoch_finalizing_not_attested") from exc


def main() -> int:
    raise SystemExit("P2c owner attester is not an active collector or installer")


if __name__ == "__main__":
    main()
