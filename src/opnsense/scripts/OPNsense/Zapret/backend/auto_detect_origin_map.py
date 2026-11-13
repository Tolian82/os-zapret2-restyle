#!/usr/bin/env python3
"""#1052 original-generator source attribution; nonactivating P2d capture.

The P0 full-generator proof has been promoted to the canonical installed
backend, preserving exact source→native ancestry and fail-closed semantics.
The only P2d producer is called from the ORIGINAL shared candidate builder
before original FD9 seal, after the actual final exclusion policy. It does
not append a native observer or authorize queue processing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

from auto_detect_storage import RAW_PATH, DEBUG_PATH

import profile_policy
from global_exclusions import ARGS_LIMIT, BASE, ExclusionError, is_stun, segments, templates_and_imports, visible


class AttributionError(ValueError):
    pass


def _text(data: bytes) -> str:
    if not isinstance(data, bytes) or len(data) > ARGS_LIMIT or b"\x00" in data:
        raise AttributionError("invalid or oversized generation artifact")
    try:
        return data.decode("utf-8")
    except UnicodeError as exc:
        raise AttributionError("generation artifact is not UTF-8") from exc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _has_ipset(data: bytes) -> bool:
    return (any(kind == "IPSET" for kind, _ in profile_policy._supported(data)) or
            any(t.partition("=")[0] in {"--ipset", "--ipset-ip"} for t in _text(data).split()))


def _native_list(tokens: list[str]) -> bool:
    return any(t.partition("=")[0] in {"--hostlist", "--hostlist-domains", "--hostlist-auto"}
               for t in tokens)


def _without_blob_shorthand(tokens: list[str]) -> list[str]:
    # The only token-removal transformation performed by existing blobs.sh.
    return [t for t in tokens if not (t.startswith("--blob=") and ":" not in t[7:])]


def build_map(*, generation: str, mode: str, strategy: bytes, bindings: bytes,
              effective: list[bytes], normalized: list[bytes], resolved: list[bytes],
              ordinary: bytes, voice: bytes, extra: bytes, preamble: bytes,
              assembled: bytes, final: bytes, overlays: tuple[str, ...]) -> dict:
    """Bind actual pipeline captures to final native numbers, without writes.

    ``effective`` is captured after Target Mode, ``normalized`` after Python
    expansion, ``resolved`` from the resolver's per-profile outputs BEFORE
    blobs, and ``assembled`` before the existing final exclusion pass.
    ``overlays`` names only that pass's exact generated exclusion tokens.
    Invalid/misaligned stages refuse the whole map rather than align by text.
    """
    if not isinstance(generation, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", generation):
        raise AttributionError("missing or invalid generation identity")
    if mode not in {"all", "list", "auto"}:
        raise AttributionError("invalid Target Mode")
    captures = [strategy, bindings, ordinary, voice, extra, preamble, assembled, final,
                *effective, *normalized, *resolved]
    for capture in captures:
        _text(capture)
    if any(len(group) > profile_policy.MAX_PROFILES for group in (effective, normalized, resolved)):
        raise AttributionError("too many captured profiles")
    selector_bindings = {}
    for line in _text(bindings).splitlines():
        selector, tab, native = line.partition("\t")
        if (not tab or not profile_policy.SELECTOR.fullmatch(selector)
                or selector in selector_bindings or len(native.split()) != 1):
            raise AttributionError("invalid captured registry/storage binding")
        selector_bindings[selector] = native
    try:
        originals = profile_policy.split_profiles(strategy)
        if len(originals) != len(effective):
            raise AttributionError("source/Target Mode profile count mismatch")
        expected = []
        origins = []
        for source_no, (source, targeted) in enumerate(zip(originals, effective), 1):
            # Target Mode can append selectors, never rewrite an authored profile.
            if not targeted.startswith(source):
                raise AttributionError("Target Mode capture changed source identity")
            suffix = _text(targeted[len(source):]).split()
            if any(not profile_policy.SELECTOR.fullmatch(t) for t in suffix):
                raise AttributionError("unrecognized Target Mode transformation")
            for expanded in profile_policy.expand_profiles([targeted]):
                expected.append(expanded)
                selected = profile_policy._supported(expanded)
                origins.append(dict(
                    source_number=source_no, source_sha256=_sha(source),
                    source_selectors=[f"<{kind}:{name}>" for kind, name in profile_policy._supported(source)],
                    authored_has_ipset=_has_ipset(source), source_has_ipset=_has_ipset(targeted),
                    selector=f"<{selected[0][0]}:{selected[0][1]}>" if len(selected) == 1 else None,
                    raw_native_list=_native_list(_text(targeted).split()),
                ))
        if expected != normalized or len(resolved) != len(expected):
            raise AttributionError("normalized capture lost source order or profile identity")

        resolved_rows = []
        for original, native in zip(normalized, resolved):
            tokens, replacements = _text(original).split(), _text(native).split()
            if len(tokens) != len(replacements):
                raise AttributionError("target resolution changed token count")
            bindings = {}
            for token, replacement in zip(tokens, replacements):
                if profile_policy.SELECTOR.fullmatch(token):
                    kind = token[1:].partition(":")[0]
                    option = "--hostlist=" if kind == "HOSTLIST" else "--ipset="
                    if (not replacement.startswith(option) or not replacement[len(option):].startswith("/")
                            or selector_bindings.get(token) != replacement):
                        raise AttributionError("unverifiable native selector replacement")
                    if token in bindings and bindings[token] != replacement:
                        raise AttributionError("inconsistent native selector replacement")
                    bindings[token] = replacement
                elif token != replacement:
                    raise AttributionError("target resolution changed an authored argument")
            row = _without_blob_shorthand(replacements)
            if len(segments("\n".join(row))) != 1:
                raise AttributionError("untracked inline native profile boundary")
            resolved_rows.append(row)
        ordinary_tokens = []
        for row in resolved_rows:
            if ordinary_tokens:
                ordinary_tokens.append("--new")
            ordinary_tokens.extend(row)
        if ordinary_tokens != _text(ordinary).split():
            raise AttributionError("blob/ordinary capture changed profile order or content")

        base = _text(preamble).split()
        if not base or any(t.partition("=")[0] not in BASE for t in base):
            raise AttributionError("unverifiable generated argument preamble")
        if any(not t.startswith(("--hostlist-exclude=/", "--ipset-exclude=/")) for t in overlays):
            raise AttributionError("unverifiable generated exclusion overlay")
        if len(overlays) != len(set(overlays)):
            raise AttributionError("duplicate generated exclusion identity")

        voice_tokens, extra_tokens = _text(voice).split(), _text(extra).split()
        traffic = voice_tokens + (["--new"] if voice_tokens and ordinary_tokens else []) + ordinary_tokens
        actual = _text(assembled).split()
        expected_tokens = base + traffic + extra_tokens
        # generator_build_args_mapped appends the synthetic domain exclusion.
        domain_tail = [t for t in overlays if t.startswith("--hostlist-exclude=")]
        if actual != expected_tokens + domain_tail:
            raise AttributionError("generator assembly is not the captured generation")
        before_rows, after_rows = segments(_text(assembled)), segments(_text(final))
        if len(before_rows) != len(after_rows) or any(
            [t for t in left if t not in overlays] != [t for t in right if t not in overlays]
            for left, right in zip(before_rows, after_rows)
        ):
            raise AttributionError("final policy changed native profile identity")
        _, kinds = templates_and_imports(after_rows)
        labels = [dict(role="voice") for _ in (segments(_text(voice)) if voice_tokens else [])]
        labels += [dict(origin, role="strategy") for origin in origins]
        if not labels:
            labels = [dict(role="engine-base")]
        if extra_tokens and extra_tokens[0] != "--new" and not extra_tokens[0].startswith("--new="):
            labels[-1] = dict(labels[-1], extra_modified=True)
        labels.extend(dict(role="extra") for token in extra_tokens
                      if token == "--new" or token.startswith("--new="))
        if len(labels) != len(after_rows):
            raise AttributionError("Voice/Extra composition changed native profile count")
    except (profile_policy.ProfilePolicyError, ExclusionError) as exc:
        raise AttributionError("unverifiable canonical profile structure") from exc

    records = []
    native_number = 0
    for ordinal, (row, kind, origin) in enumerate(zip(after_rows, kinds, labels), 1):
        tokens = visible(row)
        skip = "--skip" in tokens
        number = None
        if kind != "template" and not skip:
            native_number += 1
            number = native_number
        hostlist = None
        if skip or kind == "template":
            status = "non-executable-skip" if skip else "non-executable-template"
        elif origin["role"] == "voice":
            status = "excluded-voice"
        elif is_stun(tokens):
            status = "excluded-stun"
        elif origin.get("source_has_ipset") or _has_ipset("\n".join(tokens).encode()):
            status = "excluded-ipset"
        elif any(t == "--import" or t.startswith("--import=") for t in tokens):
            # Native dp_copy can replace targets and identity; never approximate it.
            status = "unknown-import"
        elif origin.get("raw_native_list"):
            status = "unknown-native-list"
        elif origin.get("extra_modified") or origin["role"] == "extra":
            status = "unknown-extra"
        elif (origin.get("selector") or "").startswith("<HOSTLIST:"):
            hostlist = origin["selector"][10:-1]
            status = "known-hostlist"
        else:
            status = "unknown-source"
        records.append(dict(
            id=f"{generation}:{ordinal}", native_number=number, role=origin["role"],
            source_number=origin.get("source_number"), source_sha256=origin.get("source_sha256"),
            source_selectors=origin.get("source_selectors", []),
            authored_has_ipset=origin.get("authored_has_ipset", False),
            source_has_ipset=origin.get("source_has_ipset", False),
            selector=origin.get("selector"), hostlist=hostlist, status=status,
        ))
    # Upstream appends a separate low-priority no_action profile numbered 0.
    records.append(dict(id=f"{generation}:default", native_number=0,
                        role="native-default", source_number=None, source_sha256=None,
                        source_selectors=[], authored_has_ipset=False, source_has_ipset=False,
                        selector=None, hostlist=None, status="unknown-native-default"))
    digest = hashlib.sha256()
    for capture in captures:
        digest.update(len(capture).to_bytes(8, "big"))
        digest.update(capture)
    return dict(schema=1, generation=generation, mode=mode,
                evidence="P0_DETACHED_GENERATOR_ONLY", final_args_sha256=_sha(final),
                strategy_sha256=_sha(strategy), captures_sha256=digest.hexdigest(), profiles=records)


def plan_trailing_observer(mapping: dict, original: bytes, *, owner_id: str,
                           owner_candidate_sha256: str, raw_path: str,
                           debug_path: str, tcp_ports: str) -> tuple[bytes, dict]:
    """Plan the P0 no-action tail from the original same-build source map.

    This is strictly an OFFLINE proposal: it never edits the sealed release,
    creates input/debug files, starts dvtws2, or authorizes a committed owner.
    Its schema-2-shaped output deliberately uses a non-authorizing marker.
    The original FD9 integration must separately validate file ownership,
    final native argv, real process and raw/debug identity before sealing an
    authorized schema-2 map. A proposed map MUST NOT reach the running owner.
    """
    if (not isinstance(original, bytes) or not original or len(original) > 256 * 1024
            or b"\x00" in original):
        raise AttributionError("invalid original argv")
    try:
        args = original.decode("utf-8").split()
    except UnicodeError as exc:
        raise AttributionError("invalid original encoding") from exc
    if (not isinstance(mapping, dict) or mapping.get("schema") != 1
            or mapping.get("mode") != "auto"
            or mapping.get("evidence") != NONACTIVATING
            or mapping.get("observer_attached") is not False
            or mapping.get("activation_authorized") is not False
            or mapping.get("final_args_sha256") != hashlib.sha256(original).hexdigest()
            or not isinstance(owner_id, str)
            or not re.fullmatch(r"[a-f0-9]{32}", owner_id)
            or mapping.get("generation") != owner_id
            or not isinstance(owner_candidate_sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", owner_candidate_sha256)):
        raise AttributionError("untrusted original source map or owner")
    if (len(args) < 2 or not args[0].startswith("--port=")
            or any(a.startswith("--hostlist-auto") for a in args)):
        raise AttributionError("existing auto observer or unsupported argv")
    if raw_path != str(RAW_PATH) or debug_path != str(DEBUG_PATH):
        raise AttributionError("unqualified observation file paths")
    if (not isinstance(tcp_ports, str) or
            not re.fullmatch(r"[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*", tcp_ports)):
        raise AttributionError("invalid TCP observer ports")
    items = tcp_ports.split(",")
    if len(items) > 256:
        raise AttributionError("too many TCP observer port selectors")
    seen_ports: set[int] = set()
    for item in items:
        start, dash, stop = item.partition("-")
        first, last = int(start), int(stop) if dash else int(start)
        if not 1 <= first <= last <= 65535:
            raise AttributionError("invalid TCP observer port range")
        selected = set(range(first, last + 1))
        if selected & seen_ports:
            raise AttributionError("overlapping TCP observer ports")
        seen_ports.update(selected)

    source_profiles = mapping.get("profiles")
    if not isinstance(source_profiles, list) or not 1 <= len(source_profiles) <= 255:
        raise AttributionError("invalid original native profiles")
    rows = []
    numbers = []
    defaults = 0
    for row in source_profiles:
        if not isinstance(row, dict):
            raise AttributionError("invalid original profile row")
        no, status, hostlist = row.get("native_number"), row.get("status"), row.get("hostlist")
        if no is not None:
            if type(no) is not int or not 0 <= no <= 254:
                raise AttributionError("invalid original profile number")
            numbers.append(no)
        if no == 0:
            defaults += 1
            if status != "unknown-native-default" or hostlist is not None:
                raise AttributionError("invalid implicit native default")
        if status == "known-hostlist":
            if (row.get("role") != "strategy" or row.get("authored_has_ipset")
                    or row.get("source_has_ipset") or not isinstance(hostlist, str)
                    or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", hostlist)
                    or row.get("selector") != f"<HOSTLIST:{hostlist}>"):
                raise AttributionError("untrusted known HOSTLIST provenance")
        elif hostlist is not None:
            raise AttributionError("non-HOSTLIST origin unexpectedly labeled")
        rows.append({"native_number": no, "status": status, "hostlist": hostlist})
    positives = [no for no in numbers if no > 0]
    if (defaults != 1 or len(numbers) != len(set(numbers))
            or set(positives) != set(range(1, len(positives) + 1))
            or len(positives) >= 255):
        raise AttributionError("nonsequential original executable profile order")

    observer = len(positives) + 1
    planned = [args[0], f"--hostlist-auto-debug={debug_path}", *args[1:],
               "--new", f"--filter-tcp={tcp_ports}", "--filter-l7=http,tls",
               f"--hostlist-auto={raw_path}", "--hostlist-auto-fail-threshold=1",
               "--hostlist-auto-retrans-reset=0"]
    output = ("\n".join(planned) + "\n").encode("utf-8")
    if len(output) > 256 * 1024:
        raise AttributionError("planned native arguments exceed safety limit")
    rows.append({"native_number": observer, "status": "observer", "hostlist": None})
    proposal = {"schema": 2, "generation": owner_id,
                "evidence": "P2F_OFFLINE_PLAN_ONLY",
                "owner_operation_id": owner_id,
                "owner_candidate_sha256": owner_candidate_sha256,
                "final_args_sha256": hashlib.sha256(output).hexdigest(),
                "mode": "auto", "raw_path": raw_path, "debug_path": debug_path,
                "observer_native_number": observer, "profiles": rows}
    return output, proposal


def lookup(mapping: dict, generation: str, final: bytes, native_number: int) -> dict | None:
    """A stale/missing number is unknown; the future worker uses shared fallback.

    Excluded records are returned as excluded, never converted to HOSTLIST.
    Protected map/process/debug/pending publication is a separate P2 boundary.
    """
    if (not isinstance(mapping, dict) or type(native_number) is not int or native_number < 0 or mapping.get("schema") != 1
            or mapping.get("generation") != generation
            or mapping.get("final_args_sha256") != _sha(final)):
        return None
    records = mapping.get("profiles")
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        return None
    matches = [row for row in records if row.get("native_number") == native_number]
    return dict(matches[0]) if len(matches) == 1 else None

# P2d same-build read-only provenance capture. Only the original orchestrator
# calls the CLI; there is no active observer, scheduler or second service owner.
import json
import os


ORIGIN_FILE = "auto-detect-source-map.json"
CAPTURE = "auto-detect-capture"
NONACTIVATING = "ORIGINAL_SHARED_GENERATOR_CAPTURE_NONACTIVATING"


def _capture_file(path: Path, limit: int = ARGS_LIMIT, owner_uid: int | None = None) -> bytes:
    import stat
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_mode & 0o022 or before.st_size > limit
            or (owner_uid is not None and before.st_uid != owner_uid)):
        raise AttributionError("unsafe staged original-generator artifact")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        actual = os.fstat(fd)
        if (before.st_ino, before.st_dev, before.st_size) != (
                actual.st_ino, actual.st_dev, actual.st_size):
            raise AttributionError("changed original-generator stage")
        content = os.read(fd, limit + 1)
        final = os.fstat(fd)
        if (len(content) > limit or
                (actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns) !=
                (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)):
            raise AttributionError("racing original-generator stage")
        return content
    finally:
        os.close(fd)


def _capture_profiles(trace: Path, name: str) -> list[bytes]:
    folder = trace / name
    if folder.is_symlink() or not folder.is_dir():
        raise AttributionError("missing original-generator profile stage")
    entries = sorted(folder.iterdir(), key=lambda x: int(x.name) if x.name.isdecimal() else -1)
    if any(not x.name.isdecimal() or x.name.startswith("0") for x in entries):
        raise AttributionError("unknown original-generator stage artifact")
    if len(entries) > profile_policy.MAX_PROFILES or (
            {int(x.name) for x in entries} != set(range(1, len(entries) + 1))):
        raise AttributionError("missing or duplicate profile stage")
    return [_capture_file(folder / str(n)) for n in range(1, len(entries) + 1)]


def publish_origin_map(workspace: Path, release: Path, mode: str) -> dict:
    """Bounded same-build source map; no mutation to engine args or Config.

    This is *not* auto_detect_owner.py's schema=2 generation authorization.
    Missing/mismatched origin data MUST never be interpreted as known HOSTLIST.
    """
    workspace, release = Path(workspace), Path(release)
    if (not re.fullmatch(r"[a-f0-9]{32}", workspace.name)
            or release != workspace / "release" or mode != "auto"
            or workspace.is_symlink() or release.is_symlink()
            or not workspace.is_dir() or not release.is_dir()):
        raise AttributionError("not an original common Auto-detect candidate")
    trace = workspace / CAPTURE
    if trace.is_symlink() or not trace.is_dir():
        raise AttributionError("original generator capture is missing")
    final = _capture_file(release / "dvtws.args")
    assembled = _capture_file(trace / "assembled")
    # Captured overlay tokens identify the only permitted generated exclusion
    # mutations (they are never reused as inclusion/HOSTLIST origins).
    overlay_bytes = _capture_file(trace / "overlays")
    overlays = tuple(overlay_bytes.decode("utf-8").splitlines())
    if len(overlays) > 2 or len(set(overlays)) != len(overlays):
        raise AttributionError("invalid original-generator exclusion overlay")
    voice_path = release / "voice.conf"
    if not voice_path.exists() or voice_path.is_symlink():
        raise AttributionError("missing explicit native Voice split artifact")
    result = build_map(
        generation=workspace.name, mode=mode,
        strategy=_capture_file(workspace / "traffic.input"),
        bindings=_capture_file(trace / "bindings"),
        effective=_capture_profiles(trace, "effective"),
        normalized=_capture_profiles(trace, "normalized"),
        resolved=_capture_profiles(trace, "resolved"),
        ordinary=_capture_file(release / "traffic-user.conf"),
        voice=_capture_file(voice_path),
        extra=_capture_file(release / "extra.conf"),
        preamble=_capture_file(trace / "preamble"),
        assembled=assembled, final=final, overlays=overlays,
    )
    result["evidence"] = NONACTIVATING
    result["observer_attached"] = False
    result["activation_authorized"] = False
    # The P2c consumer requires a DIFFERENT (not yet emitted) schema=2 map
    # and an actual trailing native observer. This file cannot pass that gate.
    destination = release / ORIGIN_FILE
    raw = (json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    if len(raw) > 262144:
        raise AttributionError("original generator map size exceeded")
    # Never expose an incomplete source map or silently replace a previous
    # generation's evidence. Both links are inside the same sealed release.
    pending = release / ("." + ORIGIN_FILE + ".pending")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("original generator map already exists")
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            with os.fdopen(fd, "wb", closefd=False) as output:
                output.write(raw)
                output.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        os.link(pending, destination)
    finally:
        pending.unlink(missing_ok=True)
    parent = os.open(release, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return result



def preflight_original_observer(workspace: Path, candidate_digest: str) -> dict:
    """Read-only preflight under the *existing* FD9 after native PHP Config proof.

    A verified source map and plan belong to the same shared-work ID; the
    candidate digest is obtained by the caller from native
    shared_apply_config preflight, never recomputed from a second parser.
    This returns a bounded proof *only to the caller*. No files are written,
    and it cannot create an authorized schema-2 map or process owner.
    """
    work = Path(workspace)
    uid = os.geteuid()
    if (not re.fullmatch(r"[a-f0-9]{32}", work.name)
            or not re.fullmatch(r"[a-f0-9]{64}", candidate_digest)
            or work.is_symlink() or not work.is_dir()
            or work.stat().st_uid != uid or work.stat().st_mode & 0o077):
        raise AttributionError("untrusted original common candidate workspace")
    release = work / "release"
    if (release.is_symlink() or not release.is_dir()
            or release.stat().st_uid != uid):
        raise AttributionError("untrusted shared release")
    plan = json.loads(_capture_file(work / "plan.json",
                                    limit=4 * 1024 * 1024, owner_uid=uid))
    if (not isinstance(plan, dict) or plan.get("page") not in {"voice", "strategies"}
            or not isinstance(plan.get("candidate"), dict)
            or not isinstance(plan.get("changed_fields"), list)
            or not isinstance(plan.get("dependencies"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", plan["dependencies"])):
        raise AttributionError("untrusted original native Apply plan")
    source = json.loads(_capture_file(release / ORIGIN_FILE, owner_uid=uid))
    original = _capture_file(release / "dvtws.args", owner_uid=uid)
    tcp = _capture_file(release / "tcp-ports.txt", owner_uid=uid).decode("ascii").strip()
    proposed, mapping = plan_trailing_observer(
        source, original, owner_id=work.name,
        owner_candidate_sha256=candidate_digest,
        raw_path=str(RAW_PATH),
        debug_path=str(DEBUG_PATH),
        tcp_ports=tcp,
    )
    if mapping["evidence"] != "P2F_OFFLINE_PLAN_ONLY":
        raise AttributionError("observer proposal unexpectedly authorizes activation")
    return {
        "evidence": "P2F_ORIGINAL_FD9_PREFLIGHT_NONACTIVATING",
        "generation": work.name,
        "native_candidate_sha256": candidate_digest,
        "original_args_sha256": hashlib.sha256(original).hexdigest(),
        "proposed_args_sha256": hashlib.sha256(proposed).hexdigest(),
        "observer_native_number": mapping["observer_native_number"],
    }


def _secure_new_file(path: Path, content: bytes) -> None:
    """Sealed-candidate workspace only; never replace an existing witness."""
    if path.exists() or path.is_symlink() or not isinstance(content, bytes):
        raise AttributionError("original generation output already exists")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o644)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def _authorized_projection(work: Path, digest: str) -> tuple[bytes, bytes, bytes, dict]:
    # Use the exact P2f original-FD9 gate; never infer origin from final argv.
    preflight_original_observer(work, digest)
    release = work / "release"
    original = _capture_file(release / "dvtws.args", owner_uid=os.geteuid())
    source = json.loads(_capture_file(release / ORIGIN_FILE, owner_uid=os.geteuid()))
    tcp = _capture_file(release / "tcp-ports.txt", owner_uid=os.geteuid()).decode("ascii").strip()
    proposed, record = plan_trailing_observer(
        source, original, owner_id=work.name,
        owner_candidate_sha256=digest, raw_path=str(RAW_PATH),
        debug_path=str(DEBUG_PATH), tcp_ports=tcp)
    record["evidence"] = "ORIGINAL_SHARED_GENERATOR_CAPTURE"
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    # The production owner's schema-2 verifier remains the one authority.
    from auto_detect_owner import _valid_map
    _valid_map(encoded, {"id": work.name, "candidate": digest}, proposed)
    return original, proposed, encoded, record


def stage_original_preview(workspace: Path, candidate_digest: str) -> dict:
    """Seal a real common-FD9 *inert* observer candidate, not a running map.

    Original engine argv is never changed. Unlike a live --hostlist-auto,
    this cannot collect raw events while the minute worker is absent.
    """
    work = Path(workspace)
    original, proposed, encoded, record = _authorized_projection(work, candidate_digest)
    release = work / "release"
    if _capture_file(release / "dvtws.args", owner_uid=os.geteuid()) != original:
        raise AttributionError("original engine argv changed during preview")
    record["evidence"] = "P2H_ORIGINAL_FD9_SEALED_PREVIEW_NONACTIVATING"
    record["activation_authorized"] = False
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    # There is deliberately no auto-detect-generation.json: the running-owner
    # consumer MUST reject the preview and ordinary dvtws.args is unchanged.
    names = ("auto-detect-observer-preview.args", "auto-detect-observer-preview.json")
    for name in names:
        if (release / name).exists() or (release / name).is_symlink():
            raise AttributionError("observer preview already staged")
    _secure_new_file(release / names[0], proposed)
    _secure_new_file(release / names[1], raw)
    folder = os.open(release, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                     getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(folder)
    finally:
        os.close(folder)
    verify_original_preview(work, candidate_digest)
    return record


def verify_original_preview(workspace: Path, candidate_digest: str) -> dict:
    """Regenerate and compare this sealed inert proposal with original bytes."""
    work = Path(workspace)
    original, proposed, _, expected = _authorized_projection(work, candidate_digest)
    release = work / "release"
    observed_args = _capture_file(release / "auto-detect-observer-preview.args",
                                  owner_uid=os.geteuid())
    observed = json.loads(_capture_file(release / "auto-detect-observer-preview.json",
                                        owner_uid=os.geteuid()))
    expected["evidence"] = "P2H_ORIGINAL_FD9_SEALED_PREVIEW_NONACTIVATING"
    expected["activation_authorized"] = False
    if (observed_args != proposed or observed != expected
            or _capture_file(release / "dvtws.args", owner_uid=os.geteuid()) != original
            or (release / "auto-detect-generation.json").exists()
            or (release / "auto-detect-generation.json").is_symlink()):
        raise AttributionError("original FD9 preview is stale, changed, or activated")
    # The real running-owner gate must refuse a nonactivating preview.
    from auto_detect_owner import _valid_map, GenerationRefused
    try:
        _valid_map(json.dumps(expected).encode(), {"id": work.name,
                   "candidate": candidate_digest}, proposed)
    except GenerationRefused:
        pass
    else:
        raise AttributionError("preview incorrectly authorizes running engine")
    return expected


def _require_original_fd9_cli(work: Path) -> None:
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0
            or work.parent != Path("/var/db/zapret2/shared-work")):
        raise AttributionError("original native FD9 staging only")
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] not in {"emit", "preflight", "preview", "verify-preview"}:
        return 64
    workspace = Path(argv[2])
    try:
        if argv[1] in {"preview", "verify-preview"}:
            _require_original_fd9_cli(workspace)
            record = (stage_original_preview(workspace, argv[3])
                      if argv[1] == "preview" else
                      verify_original_preview(workspace, argv[3]))
            print(json.dumps({"observer_native_number": record["observer_native_number"],
                              "generation": workspace.name}, sort_keys=True))
        elif argv[1] == "preflight":
            print(json.dumps(preflight_original_observer(workspace, argv[3]),
                             sort_keys=True, separators=(",", ":")))
        else:
            publish_origin_map(workspace, workspace / "release", argv[3])
    except (AttributionError, OSError, ValueError, UnicodeError, TypeError) as exc:
        # Neither read-only observation nor source-map publication can
        # authorize native observer activation or block a normal Apply.
        print("P2 source-only provenance unavailable: " + str(exc), file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
