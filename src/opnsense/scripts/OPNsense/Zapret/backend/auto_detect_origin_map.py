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


def _capture_file(path: Path) -> bytes:
    import stat
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_mode & 0o022 or before.st_size > ARGS_LIMIT):
        raise AttributionError("unsafe staged original-generator artifact")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        actual = os.fstat(fd)
        if (before.st_ino, before.st_dev, before.st_size) != (
                actual.st_ino, actual.st_dev, actual.st_size):
            raise AttributionError("changed original-generator stage")
        content = os.read(fd, ARGS_LIMIT + 1)
        final = os.fstat(fd)
        if (len(content) > ARGS_LIMIT or
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


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] != "emit":
        return 64
    workspace = Path(argv[2])
    try:
        publish_origin_map(workspace, workspace / "release", argv[3])
    except (AttributionError, OSError, ValueError, UnicodeError) as exc:
        # The original Apply remains valid on a source-map failure because
        # P2c cannot authorize a missing map. No partial map is published.
        print("P2d origin capture unavailable: " + str(exc), file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
