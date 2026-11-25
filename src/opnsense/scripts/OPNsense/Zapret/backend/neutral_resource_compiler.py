#!/usr/bin/env python3
"""TZ6v5 S08b: pure prepared-resource and Voice effective preview.

Only input snapshots supplied by the ORIGINAL owners are consumed; the
caller, not this module, verifies file provenance and original Config/FD9.
The results never authorize Apply, Start, reload or installation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Mapping

from neutral_config_model import RequestedConfig, SourceId
from neutral_target_compiler import TargetProjection

import domain_policy
import ipset_policy
from auto_detect_effective_known import compose_known, EffectiveKnownRefused
from auto_detect_owned_sources import KNOWN_HOSTLISTS
from voice_profile_compiler import compile_candidate, VoiceConfigurationError, SERVICES

_CATALOG_ROW = re.compile(
    r"printf '([a-z][a-z0-9_.-]*)\\t(managed|runtime)\\t([a-z0-9/.-]+)\\n'\Z"
)
_SOURCE_MAX = 128 * 1024
_ROOT_REQUIRED = ("hostlist.exclude", "ipset.exclude")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class ResourceCompileError(ValueError):
    """Safe code only, never echo untrusted HOSTLIST/Voice/IPSet content."""


@dataclass(frozen=True)
class StorageEntry:
    storage_key: str
    provider: str
    locator: str


@dataclass(frozen=True)
class OriginalStorage:
    source_sha256: str
    entries: tuple[StorageEntry, ...]


@dataclass(frozen=True)
class ResourceRecord:
    kind: str
    name: str
    storage_key: str
    provider: str
    locator: str
    linked: bool
    state: str
    entry_count: int | None
    byte_count: int | None
    content_sha256: str | None


@dataclass(frozen=True)
class ExclusionRecord:
    kind: str
    enabled: bool
    entry_count: int
    content_sha256: str


@dataclass(frozen=True)
class VoiceRecord:
    service: str
    enabled: bool
    draft_present: bool
    args_sha256: str | None
    native_profile_sha256: str | None


@dataclass(frozen=True)
class ResourceProjection:
    target_mode: str
    storage_source_sha256: str
    resources: tuple[ResourceRecord, ...]
    global_exclusions: tuple[ExclusionRecord, ...]
    voice: tuple[VoiceRecord, ...]
    voice_native_args_sha256: str | None
    owned_known_input: str
    manual_known_empty: tuple[str, ...]
    effective_known_empty: tuple[str, ...]
    status: str = "DETACHED_INPUT_PREVIEW_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_original_storage(source: bytes) -> OriginalStorage:
    """Extract authoritative storage_catalog_build() rows from the shell source."""
    if type(source) is not bytes or not source or len(source) > _SOURCE_MAX:
        raise ResourceCompileError("INVALID_STORAGE_SOURCE")
    try:
        text = source.decode("utf-8")
        block = text.split("\nstorage_catalog_build()\n{", 1)[1].split(
            "\nstorage_catalog_validate()\n{", 1)[0]
    except (UnicodeError, IndexError) as exc:
        raise ResourceCompileError("STORAGE_SOURCE_CHANGED") from exc
    records = []
    for line in block.splitlines():
        if not re.match(r"^\s*printf ", line):
            continue
        match = _CATALOG_ROW.fullmatch(line.strip())
        if not match:
            raise ResourceCompileError("STORAGE_DECLARATION_CHANGED")
        key, provider, locator = match.groups()
        parts = locator.split("/")
        if (locator.startswith("/") or any(part in ("", ".", "..") for part in parts)
                or not re.fullmatch(r"[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)?", key.split(".")[0])
                or not key.startswith(("hostlist.", "ipset."))):
            raise ResourceCompileError("INVALID_STORAGE_LOCATOR")
        records.append(StorageEntry(key, provider, locator))
    if (not records or len(records) > 128 or
            len(set(item.storage_key for item in records)) != len(records) or
            len(set((item.provider, item.locator) for item in records)) != len(records)):
        raise ResourceCompileError("INVALID_STORAGE_CATALOG")
    return OriginalStorage(_sha(source), tuple(records))


def _canonical_domain(raw: bytes, kind: str) -> tuple[bytes, int]:
    if type(raw) is not bytes:
        raise ResourceCompileError("INVALID_DOMAIN_INPUT")
    try:
        text = raw.decode("utf-8")
        evidence = domain_policy.normalize(text, kind)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ResourceCompileError("INVALID_" + kind.upper() + "_DOMAINS") from None
    normalized = evidence["normalized"]
    return (normalized + "\n" if normalized else "").encode("utf-8"), evidence["entry_count"]


def _canonical_ipset(raw: bytes, name: str) -> tuple[bytes, int]:
    if type(raw) is not bytes:
        raise ResourceCompileError("INVALID_IPSET_INPUT")
    try:
        normalized, proof = ipset_policy.parse_ipset(
            raw, name, collapse=name == "exclude")
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ResourceCompileError("INVALID_" + name.upper() + "_IPSET") from None
    return normalized.encode("utf-8"), proof["entry_count"]


def _owned_known(owned: Mapping[str, bytes] | None) -> dict[str, str] | None:
    """The caller must already hold original ownership/destination read proof.

    None only means NO SNAPSHOT SUPPLIED, not that Found has been disabled.
    A forged mapping cannot establish file ownership or authorize runtime.
    """
    if owned is None:
        return None
    if type(owned) is not dict or set(owned) != set(KNOWN_HOSTLISTS):
        raise ResourceCompileError("INCOMPLETE_OWNED_KNOWN_SNAPSHOT")
    result = {}
    for name in KNOWN_HOSTLISTS:
        raw = owned[name]
        if type(raw) is not bytes or len(raw) > 40 * 1024:
            raise ResourceCompileError("INVALID_OWNED_KNOWN_SNAPSHOT")
        normalized, _ = _canonical_domain(raw, name)
        if raw != normalized or any(
                line.startswith(("!", "^")) for line in raw.decode("utf-8").splitlines()):
            raise ResourceCompileError("NONCANONICAL_OWNED_KNOWN")
        result[name] = raw.decode("utf-8")
    return result


def compile_resources(requested: RequestedConfig, targets: TargetProjection,
                      storage: OriginalStorage, prepared: Mapping[str, bytes],
                      owned_known: Mapping[str, bytes] | None, *,
                      runtime_auto: bytes | None = None,
                      voice_managed_root: Path) -> ResourceProjection:
    """Check original-ready resource semantics and compose existing Voice producer.

    'prepared' contains detached RAW original GUI file-backed source bytes:
    every managed source declared by the original registry and storage source,
    plus two GLOBAL exclude inputs. It is not a copied XML hostlist field
    and does not prove filesystem ownership.
    No physical read, shell, side effect, or authority is performed here.
    """
    if (type(requested) is not RequestedConfig or requested.schema != 1 or
            requested.authorization != "NONE" or requested.physical_transition_allowed or
            type(targets) is not TargetProjection or targets.authorization != "NONE" or
            targets.physical_transition_allowed or targets.mode != requested.target_mode or
            type(storage) is not OriginalStorage or type(storage.entries) is not tuple or
            not _HEX.fullmatch(storage.source_sha256) or
            type(prepared) is not dict or
            not isinstance(voice_managed_root, Path) or not voice_managed_root.is_absolute()
            or ".." in voice_managed_root.parts):
        raise ResourceCompileError("UNQUALIFIED_RESOURCE_PREVIEW")

    registry = requested.registered_sources
    if (type(registry) is not tuple or not registry or
            any(type(item) is not SourceId for item in registry)):
        raise ResourceCompileError("INVALID_RESOURCE_REGISTRY")
    mapped = {row.storage_key: row for row in storage.entries}
    if (len(mapped) != len(storage.entries) or
            set(mapped) != {source.storage_key for source in registry} or
            len({source.storage_key for source in registry}) != len(registry)):
        raise ResourceCompileError("REGISTRY_STORAGE_MISMATCH")

    managed = {source.storage_key for source in registry
               if mapped[source.storage_key].provider == "managed"}
    # These identities are existing Voice/Found contracts, not a fixed
    # count of all registered managed HOSTLIST/IPSET sources. Newly declared
    # resources must be present and independently validated; no second
    # registry or implicit Auto/Voice eligibility is introduced here.
    required = {"hostlist.youtube", "hostlist.user"} | {
        "ipset." + name for name in SERVICES
    }
    if (not required.issubset(managed) or not managed or
            len(managed) > 128 or
            set(prepared) != managed | set(_ROOT_REQUIRED)):
        raise ResourceCompileError("INCOMPLETE_PREPARED_RESOURCES")
    if (any(type(value) is not bytes for value in prepared.values()) or
            (runtime_auto is not None and type(runtime_auto) is not bytes)):
        raise ResourceCompileError("INVALID_PREPARED_BYTES")
    if (len(requested.voice) != len(SERVICES) or
            tuple(item.service for item in requested.voice) != SERVICES):
        raise ResourceCompileError("INVALID_SAVED_VOICE")

    linked = set()
    for profile in targets.profiles:
        if (type(profile.effective) is not tuple or
                any(type(pair) is not tuple or len(pair) != 2 for pair in profile.effective)):
            raise ResourceCompileError("INVALID_TARGET_PROFILES")
        linked.update(profile.effective)
    for source in registry:
        if source.kind not in ("HOSTLIST", "IPSET"):
            raise ResourceCompileError("INVALID_RESOURCE_TYPE")
    if not linked.issubset({(source.kind, source.name) for source in registry}):
        raise ResourceCompileError("UNKNOWN_LINKED_SOURCE")

    youtube, _ = _canonical_domain(prepared["hostlist.youtube"], "youtube")
    user, _ = _canonical_domain(prepared["hostlist.user"], "user")
    manual = {"youtube": youtube.decode("utf-8"), "user": user.decode("utf-8")}
    owned = _owned_known(owned_known)
    known_effective = dict(manual)
    if owned is not None:
        try:
            known_effective = compose_known(manual, owned)
        except (EffectiveKnownRefused, ValueError, TypeError) as exc:
            raise ResourceCompileError("INVALID_EFFECTIVE_KNOWN") from None
    out = {
        "hostlist.youtube": known_effective["youtube"].encode("utf-8"),
        "hostlist.user": known_effective["user"].encode("utf-8"),
    }
    for source in registry:
        if source.kind == "IPSET" and mapped[source.storage_key].provider == "managed":
            out[source.storage_key], _ = _canonical_ipset(
                prepared[source.storage_key], source.name)
        elif (source.kind == "HOSTLIST" and source.name not in KNOWN_HOSTLISTS
              and mapped[source.storage_key].provider == "managed"):
            # A new editor must first be registered in the ORIGINAL domain
            # policy. Unknown names fail closed; never silently reuse User's
            # normalization or grant Auto learning to the new source.
            out[source.storage_key], _ = _canonical_domain(
                prepared[source.storage_key], source.name)
    exclude_domains, exclude_count = _canonical_domain(
        prepared["hostlist.exclude"], "exclude")
    exclude_ipset, exclude_ip_count = _canonical_ipset(
        prepared["ipset.exclude"], "exclude")

    entries = []
    for source in registry:
        cat = mapped[source.storage_key]
        if (source.kind.lower() + "." + source.name != source.storage_key or
                cat.provider not in ("managed", "runtime")):
            raise ResourceCompileError("UNQUALIFIED_STORAGE_REFERENCE")
        is_linked = (source.kind, source.name) in linked
        content = runtime_auto if cat.provider == "runtime" else out.get(source.storage_key)
        if cat.provider == "runtime" and source.storage_key != "hostlist.auto":
            raise ResourceCompileError("UNQUALIFIED_RUNTIME_RESOURCE")
        if cat.provider == "managed" and content is None:
            raise ResourceCompileError("UNPREPARED_MANAGED_RESOURCE")
        if is_linked and content is None:
            raise ResourceCompileError("LINKED_RESOURCE_NOT_PRESENT")
        if is_linked and source.content_required and not content:
            raise ResourceCompileError("LINKED_RESOURCE_EMPTY")
        if content is None:
            count = None
            state = "NOT_SUPPLIED"
        else:
            count = len(content.splitlines())
            state = ("READY" if content else
                     ("PRESENT_EMPTY_OPTIONAL" if not source.content_required
                      else "PRESENT_EMPTY_UNLINKED"))
        entries.append(ResourceRecord(
            source.kind, source.name, source.storage_key, cat.provider, cat.locator,
            is_linked, state, count, len(content) if content is not None else None,
            _sha(content) if content is not None else None))

    services = {x.service: x for x in requested.voice}
    profiles = None
    voice_hash = None
    native_profiles = {}
    if any(x.enabled is True for x in requested.voice):
        if requested.wan_state != "NEEDS_NATIVE_RESOLUTION" or not requested.saved_wan:
            raise ResourceCompileError("VOICE_REQUIRES_SAVED_WAN")
        data = {"strategy_wan": requested.saved_wan, "services": {
            name: {"enabled": services[name].enabled is True,
                   "args": services[name].args if services[name].args is not None else "",
                   "ips": prepared["ipset." + name].decode("utf-8")}
            for name in SERVICES
        }}
        try:
            profiles, native = compile_candidate(data, voice_managed_root)
        except (VoiceConfigurationError, ValueError, TypeError) as exc:
            raise ResourceCompileError("VOICE_CANDIDATE_INVALID") from None
        voice_hash = _sha(profiles.encode("utf-8"))
        native_profiles = {p["service"]: p["profile_sha256"] for p in native["profiles"]}
    voice_records = tuple(VoiceRecord(
        x.service, x.enabled is True, x.args_present,
        _sha(x.args.encode("utf-8")) if x.args is not None else None,
        native_profiles.get(x.service)) for x in requested.voice)
    return ResourceProjection(
        requested.target_mode, storage.source_sha256, tuple(entries),
        (ExclusionRecord("HOSTLIST", bool(exclude_domains), exclude_count,
                         _sha(exclude_domains)),
         ExclusionRecord("IPSET", bool(exclude_ipset), exclude_ip_count,
                         _sha(exclude_ipset))),
        voice_records, voice_hash,
        "SNAPSHOT_SUPPLIED_NO_AUTHORITY" if owned is not None else "NO_OWNED_SNAPSHOT_SUPPLIED",
        tuple(n for n in KNOWN_HOSTLISTS if not manual[n]),
        tuple(n for n in KNOWN_HOSTLISTS if not known_effective[n]))



def compare_original_managed_bytes(resources: ResourceProjection,
                                   storage: OriginalStorage,
                                   observed: Mapping[str, bytes]) -> tuple[str, ...]:
    """Read-only expected-vs-actual witness for ORIGINAL built managed bytes.

    Observed is populated by the ORIGINAL FD9 holder from its single
    candidate release and keyed by ORIGINAL storage locators, not by guessed
    paths. This function does NOT open files, validate their ownership, seal,
    generation, or authorize any transition. The original caller must
    independently attest exact file identity/permissions and stable snapshot.
    """
    if (type(resources) is not ResourceProjection or
            resources.authorization != "NONE" or
            resources.physical_transition_allowed or
            type(storage) is not OriginalStorage or
            resources.storage_source_sha256 != storage.source_sha256 or
            type(observed) is not dict or
            type(resources.resources) is not tuple or
            len(resources.resources) != len(storage.entries) or
            tuple(row.storage_key for row in resources.resources) !=
            tuple(entry.storage_key for entry in storage.entries) or
            len(resources.global_exclusions) != 2):
        raise ResourceCompileError("UNQUALIFIED_MANAGED_PARITY")

    expected: dict[str, tuple[str, int]] = {}
    for row, entry in zip(resources.resources, storage.entries):
        if (type(row) is not ResourceRecord or type(entry) is not StorageEntry or
                row.storage_key != entry.storage_key or
                row.provider != entry.provider or row.locator != entry.locator):
            raise ResourceCompileError("MANAGED_REFERENCE_MISMATCH")
        if entry.provider != "managed":
            continue
        if (type(row.content_sha256) is not str or
                not _HEX.fullmatch(row.content_sha256) or
                type(row.byte_count) is not int or row.byte_count < 0 or
                entry.locator in expected):
            raise ResourceCompileError("MANAGED_EXPECTATION_MISSING")
        expected[entry.locator] = row.content_sha256, row.byte_count

    for index, (kind, filename) in enumerate((
            ("HOSTLIST", "hostlist-exclude.txt"),
            ("IPSET", "ipset-exclude.txt"))):
        row = resources.global_exclusions[index]
        if (type(row) is not ExclusionRecord or row.kind != kind or
                type(row.content_sha256) is not str or
                not _HEX.fullmatch(row.content_sha256) or filename in expected):
            raise ResourceCompileError("INVALID_EXCLUSION_EXPECTATION")
        # Actual length is checked by the hash (not the domain entry count).
        expected[filename] = row.content_sha256, -1

    if not expected or set(observed) != set(expected):
        raise ResourceCompileError("ORIGINAL_MANAGED_SET_MISMATCH")
    for locator, (digest, length) in expected.items():
        value = observed[locator]
        if (type(value) is not bytes or len(value) > domain_policy.MAX_INPUT_BYTES or
                (length >= 0 and len(value) != length) or
                _sha(value) != digest):
            raise ResourceCompileError("ORIGINAL_MANAGED_BYTES_MISMATCH")
    return tuple(sorted(expected))
