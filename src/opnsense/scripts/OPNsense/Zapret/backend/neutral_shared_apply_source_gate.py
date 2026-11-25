#!/usr/bin/env python3
"""S10c2b1: read-only ORIGINAL FD9 source -> managed-file preseal witness.

The existing shared_apply_prepare_service is the only installed caller.
This module never creates a Config writer, journal, release, PID, or IPFW
operation. Pure compilation is NOT an authorization to activate. The original
FD9 owner must re-attest its seal, P1 and previous runtime at physical commit.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from config_projection_opnsense import registered_ids, xml_snapshot
from neutral_config_model import project
from neutral_target_compiler import compile_target_profiles, parse_original_policy
from neutral_resource_compiler import (
    compile_resources, compare_original_managed_bytes, parse_original_storage)
from shared_apply_seal import _stat
from voice_profile_compiler import SERVICES

FIELDS = (
    "strategy", "youtube", "user", "telegram", "discord", "x", "sip",
    "custom", "exclude_domains", "exclude_ipset", "mode", "port", "wan")
MARKER = b"S10C2B1_ORIGINAL_INPUT_V1"
MAX_PIPE = 12 * 1024 * 1024
MAX_XML = 16 * 1024 * 1024
MAX_FILE = 4 * 1024 * 1024
_ID = re.compile(r"[a-f0-9]{32}\Z")


class OriginalSourceGateRefused(ValueError):
    """No user data, paths, WAN, domains, addresses or Lua in errors."""


@dataclass(frozen=True)
class SourceGateReceipt:
    mode: str
    candidate_input_sha256: str
    managed_locators: tuple[str, ...]
    status: str = "ORIGINAL_NONACTIVATING_SOURCE_MANAGED_PARITY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def decode_pipe(raw: bytes) -> dict[str, bytes]:
    """Exact fixed framing: original shell uses printf %s\\0, never argv secrets."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_PIPE or not raw.endswith(b"\0"):
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_PIPE")
    chunks = raw[:-1].split(b"\0")
    if len(chunks) != 1 + len(FIELDS) or chunks[0] != MARKER:
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_FIELDS")
    data = dict(zip(FIELDS, chunks[1:]))
    for name in ("strategy", "youtube", "user", "exclude_domains"):
        if len(data[name]) > MAX_FILE:
            raise OriginalSourceGateRefused("INVALID_ORIGINAL_FIELD_SIZE")
    for name in ("telegram", "discord", "x", "sip", "custom", "exclude_ipset"):
        if len(data[name]) > 262144:
            raise OriginalSourceGateRefused("INVALID_ORIGINAL_FIELD_SIZE")
    if (len(data["strategy"]) > 262144 or
            data["mode"] not in (b"all", b"list", b"auto") or
            not re.fullmatch(rb"[0-9]{1,5}", data["port"]) or
            not re.fullmatch(rb"[A-Za-z][A-Za-z0-9_.:-]{0,63}", data["wan"])):
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_SOURCE_SELECTOR")
    return data


def _read(path: Path, uid: int, maximum: int, *, allow_empty: bool = False) -> bytes:
    """Read one existing owned single-link file with no symlink or replacement."""
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid or
            before.st_mode & 0o022 or before.st_nlink != 1 or
            before.st_size > maximum or (not allow_empty and before.st_size == 0)):
        raise OriginalSourceGateRefused("UNTRUSTED_ORIGINAL_FILE")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        pinned = os.fstat(fd)
        if (pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise OriginalSourceGateRefused("ORIGINAL_FILE_CHANGED")
        data = os.read(fd, maximum + 1)
        after = os.fstat(fd)
        latest = path.lstat()
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                  value.st_mtime_ns, value.st_ctime_ns)
        if len(data) != before.st_size or identity(before) != identity(after) or (
                identity(before) != identity(latest)):
            raise OriginalSourceGateRefused("ORIGINAL_FILE_CHANGED")
        return data
    finally:
        os.close(fd)


def qualify_source_to_managed(*, work: Path, sources: Path,
                              inputs: dict[str, bytes],
                              owned_known: dict[str, bytes] | None,
                              runtime_auto: bytes | None = None,
                              owner_uid: int = 0,
                              active_managed: Path = Path(
                                  "/usr/local/etc/zapret2/runtime-v2/managed")) -> SourceGateReceipt:
    """Pure observational witness of actual producer staged files.

    The original native wrapper supplies P2-qualified owned after-images.
    This import-only function is also exercised with the genuine original
    disposable P2e generator; it has no authority or physical effects.
    """
    if (not isinstance(work, Path) or not isinstance(sources, Path) or
            not isinstance(active_managed, Path) or not work.is_absolute() or
            not sources.is_absolute() or not active_managed.is_absolute() or
            not _ID.fullmatch(work.name) or type(owner_uid) is not int or
            owner_uid < 0 or type(inputs) is not dict or
            set(inputs) != set(FIELDS) or
            any(type(value) is not bytes for value in inputs.values())):
        raise OriginalSourceGateRefused("UNQUALIFIED_ORIGINAL_CONTEXT")
    inputs = decode_pipe(MARKER + b"\0" + b"\0".join(inputs[key] for key in FIELDS) + b"\0")
    release = work / "release"
    managed = release / "managed"
    for directory in (work.parent, work, release, managed):
        _stat(directory, owner_uid, directory=True)
    xml = _read(work / "candidate.xml", owner_uid, MAX_XML)
    saved = project(xml_snapshot(xml),
                    registered_ids(_read(sources / "registry.sh", owner_uid, 128 * 1024)))
    if (saved.target_mode != inputs["mode"].decode("ascii") or
            saved.divert_port != int(inputs["port"]) or
            saved.saved_wan != inputs["wan"].decode("ascii")):
        raise OriginalSourceGateRefused("ORIGINAL_CONFIG_SOURCE_DRIFT")
    traffic = _read(work / "traffic.input", owner_uid, 262145, allow_empty=True)
    if traffic != inputs["strategy"] + b"\n":
        raise OriginalSourceGateRefused("ORIGINAL_STRATEGY_SOURCE_DRIFT")
    registry = saved.registered_sources
    expected_registry = b"".join((
        f"{row.kind}\t{row.name}\t"
        f"{'--hostlist' if row.kind == 'HOSTLIST' else '--ipset'}\t"
        f"{row.storage_key}\t{int(row.content_required)}\n").encode("ascii")
        for row in registry)
    if _read(work / "target-registry.tsv", owner_uid, 128 * 1024) != expected_registry:
        raise OriginalSourceGateRefused("ORIGINAL_REGISTRY_SOURCE_DRIFT")
    original_storage = _read(sources / "storage.sh", owner_uid, 128 * 1024)
    storage = parse_original_storage(original_storage)
    expected_catalog = b"".join((
        f"{row.storage_key}\t{row.provider}\t{row.locator}\n").encode("ascii")
        for row in storage.entries)
    if _read(work / "storage-catalog.tsv", owner_uid, 128 * 1024) != expected_catalog:
        raise OriginalSourceGateRefused("ORIGINAL_STORAGE_SOURCE_DRIFT")
    policy = parse_original_policy(_read(sources / "target_mode.sh", owner_uid, 128 * 1024))
    targets = compile_target_profiles(saved, traffic, policy)
    prepared = {
        "hostlist.youtube": inputs["youtube"],
        "hostlist.user": inputs["user"],
        "hostlist.exclude": inputs["exclude_domains"],
        "ipset.exclude": inputs["exclude_ipset"],
    }
    for service in SERVICES:
        prepared["ipset." + service] = inputs[service]
    # The original registry is extensible; an unrepresented GUI source is NOT
    # silently mapped to existing User data. Future editors require an
    # explicit same-operation source binding, otherwise fail closed.
    expected = {row.storage_key for row in storage.entries if row.provider == "managed"}
    if set(prepared) != expected | {"hostlist.exclude", "ipset.exclude"}:
        raise OriginalSourceGateRefused("ORIGINAL_MANAGED_SOURCE_SET_DRIFT")
    resources = compile_resources(
        saved, targets, storage, prepared, owned_known,
        runtime_auto=runtime_auto, voice_managed_root=active_managed)
    observed = {}
    for row in storage.entries:
        if row.provider == "managed":
            observed[row.locator] = _read(managed / row.locator, owner_uid, MAX_FILE,
                                          allow_empty=True)
    for filename in ("hostlist-exclude.txt", "ipset-exclude.txt"):
        observed[filename] = _read(managed / filename, owner_uid, MAX_FILE, allow_empty=True)
    matched = compare_original_managed_bytes(resources, storage, observed)
    # Re-attest the two independent input source locations and strategy file
    # before handing control to original Auto/schema2 and eventual seal.
    if (xml != _read(work / "candidate.xml", owner_uid, MAX_XML) or
            traffic != _read(work / "traffic.input", owner_uid, 262145, allow_empty=True) or
            original_storage != _read(sources / "storage.sh", owner_uid, 128 * 1024) or
            expected_registry != _read(work / "target-registry.tsv", owner_uid, 128 * 1024)):
        raise OriginalSourceGateRefused("ORIGINAL_INPUT_CHANGED_DURING_CHECK")
    return SourceGateReceipt(saved.target_mode, hashlib.sha256(xml).hexdigest(), matched)


def _owned_under_original_p2(work: Path, uid: int) -> dict[str, bytes] | None:
    """Read original known P1 snapshot; never replace it with generated files."""
    from auto_detect_destination_commit import (
        SHARED_FOUND_NAMES, _qualified_shared_found_batch, exclusive_destination_lock)
    from auto_detect_effective_known import _verify_planned_preimages_locked
    from auto_detect_gui_hostlist import AUTO_LOCK, AUTO_HOSTLIST
    from auto_detect_owned_sources import OWNED_ROOT, KNOWN_HOSTLISTS, read_owned

    plan = json.loads(_read(work / "plan.json", uid, MAX_FILE))
    if type(plan) is not dict:
        raise OriginalSourceGateRefused("INVALID_ORIGINAL_PLAN")
    found = ("found_intent" in plan, "found_batch" in plan)
    if found[0] != found[1]:
        raise OriginalSourceGateRefused("INCOMPLETE_ORIGINAL_FOUND_PLAN")
    with exclusive_destination_lock(AUTO_LOCK, uid):
        if found[0]:
            if (plan.get("page") != "strategies" or
                    plan.get("result") != "prepared" or
                    type(plan["found_intent"]) is not dict or
                    plan["found_intent"].get("commit_authorized") is not False):
                raise OriginalSourceGateRefused("INVALID_ORIGINAL_FOUND_INTENT")
            validated = _qualified_shared_found_batch(plan["found_batch"])
            targets = {"youtube": OWNED_ROOT / "youtube.txt",
                       "user": OWNED_ROOT / "user.txt", "auto": AUTO_HOSTLIST}
            _verify_planned_preimages_locked(
                validated, targets, owned_root=OWNED_ROOT, owner_uid=uid)
            return {name: validated[name][1] for name in KNOWN_HOSTLISTS}
        known = read_owned(OWNED_ROOT, owner_uid=uid)
        return None if known is None else {
            name: known[name].encode("utf-8") for name in KNOWN_HOSTLISTS}


def native_original_fd9(operation: str, raw_pipe: bytes) -> SourceGateReceipt:
    """Only the installed original FD9 wrapper can invoke this native action."""
    from voice_ipfw_adapter import require_lifecycle_lock
    from shared_apply_seal import WORK
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            type(operation) is not str or not _ID.fullmatch(operation)):
        raise OriginalSourceGateRefused("NATIVE_ORIGINAL_FD9_REQUIRED")
    require_lifecycle_lock()
    inputs = decode_pipe(raw_pipe)
    work = WORK / operation
    known = _owned_under_original_p2(work, 0)
    auto_bytes = None
    # Shared Auto is a runtime provider, NOT a managed hostlist and never
    # becomes an implicit learner. Only read its native source if referenced.
    if b"<HOSTLIST:auto>" in inputs["strategy"]:
        auto_bytes = _read(Path("/usr/local/etc/zapret2/ipset/auto-domains.txt"),
                           0, MAX_FILE, allow_empty=True)
    receipt = qualify_source_to_managed(
        work=work, sources=Path(__file__).parent, inputs=inputs,
        owned_known=known, runtime_auto=auto_bytes, owner_uid=0)
    require_lifecycle_lock()
    return receipt


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 64
    try:
        raw = sys.stdin.buffer.read(MAX_PIPE + 1)
        native_original_fd9(args[0], raw)
        return 0
    except (ValueError, RuntimeError, OSError, TypeError, UnicodeError,
            KeyError, IndexError, json.JSONDecodeError):
        # Stable, content-free diagnostic; original Apply owns the single
        # preflight-rejected=runtime-build response and stage journal.
        print("ERROR: original source-to-managed candidate parity refused",
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
