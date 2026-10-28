#!/usr/bin/env python3
"""Stage 3: fail-closed final dvtws2 argv overlay and native IPSET audit.

One native candidate, one prepared IPSET manifest, no Config/IPFW/engine writes.
This operates after Strategies, Voice, templates/imports and Extra Arguments
have been assembled. It never edits the user-authored strategy or Voice plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from ipset_policy import IPSetError, LISTS, parse_ipset

class ExclusionError(ValueError):
    pass

PROFILE_LIMIT = 256
ARGS_LIMIT = 262144
NAME = re.compile(r"^[a-zA-Z0-9_.-]{1,100}$")
BASE = {"--port", "--lua-init", "--blob", "--daemon", "--user", "--uid", "--gid"}


def segments(text: str) -> list[list[str]]:
    if len(text.encode("utf-8")) > ARGS_LIMIT or "\x00" in text or "\r" in text:
        raise ExclusionError("invalid or oversized final engine argv")
    result: list[list[str]] = [[]]
    for token in text.split():
        if token == "--new" or token.startswith("--new="):
            if token != "--new" and not NAME.fullmatch(token[6:]):
                raise ExclusionError("invalid native named --new boundary")
            if not result[-1]:
                raise ExclusionError("empty profile before native --new")
            result.append([token] if token != "--new" else [])
            # Named --new is the first token of the NEW profile, not a tail
            # option of the previous one; output serialization handles it.
        else:
            result[-1].append(token)
    if not result[-1] or len(result) > PROFILE_LIMIT:
        raise ExclusionError("empty or excessive native profile sequence")
    return result


def visible(profile: list[str]) -> list[str]:
    return [token for token in profile if not token.startswith("--new=")]


def templates_and_imports(rows: list[list[str]]) -> tuple[dict[str, list[str]], list[str]]:
    templates: dict[str, list[str]] = {}
    kinds: list[str] = []
    for row in rows:
        tokens = visible(row)
        template = next((t for t in tokens if t == "--template" or t.startswith("--template=")), None)
        if sum(t == "--template" or t.startswith("--template=") for t in tokens) > 1:
            raise ExclusionError("repeated template selector")
        if template is None:
            kinds.append("profile")
            continue
        name = template.partition("=")[2]
        if not name:
            name_tokens = [t.partition("=")[2] for t in tokens if t.startswith("--name=")]
            if len(name_tokens) != 1:
                raise ExclusionError("unnamed native template must have one --name")
            name = name_tokens[0]
        if not NAME.fullmatch(name) or name in templates:
            raise ExclusionError("invalid or duplicate native template name")
        templates[name] = tokens
        kinds.append("template")
    return templates, kinds


def inherited(tokens: list[str], templates: dict[str, list[str]], seen: frozenset[str] = frozenset()) -> list[str]:
    # Mirrors effective filter visibility, not the native engine's internal
    # overwrite semantics. Ambiguous cycles are rejected before Apply.
    result = list(tokens)
    for token in tokens:
        if token.startswith("--import="):
            name = token.partition("=")[2]
            if not NAME.fullmatch(name) or name in seen or name not in templates:
                raise ExclusionError("unknown or cyclic native profile import")
            result.extend(inherited(templates[name], templates, seen | {name}))
        elif token == "--import":
            raise ExclusionError("unverifiable positional native import")
    return result


def is_stun(tokens: list[str]) -> bool:
    return any(t.startswith(("--filter-l7=", "--payload=")) and
               "stun" in t.partition("=")[2].split(",") for t in tokens)


def domain_aware(tokens: list[str]) -> bool:
    if any(t.startswith(("--hostlist=", "--hostlist-domains=", "--hostlist-auto="))
           for t in tokens):
        return True
    return any(t.startswith("--filter-l7=") and
               any(proto in ("http", "tls", "quic") for proto in t.partition("=")[2].split(","))
               for t in tokens)


def attest_manifest(release: Path, expected_ipset: Path) -> dict:
    try:
        manifest_path = release / "ipset-manifest.json"
        if manifest_path.is_symlink() or manifest_path.stat().st_size > 65536:
            raise ExclusionError("unsafe prepared IPSET manifest")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or set(data.get("lists", {})) != set(LISTS):
            raise ExclusionError("invalid prepared IPSET manifest")
        managed = release / "managed"
        if managed.is_symlink() or not managed.is_dir() or expected_ipset != managed / "ipset-exclude.txt":
            raise ExclusionError("unexpected prepared Exclude IPSet owner")
        for name in LISTS:
            path = managed / f"ipset-{name}.txt"
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 262144:
                raise ExclusionError("unsafe prepared IPSET file")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            evidence = data["lists"][name]
            if evidence.get("sha256") != digest or evidence.get("full_family") is not False:
                raise ExclusionError("prepared IPSET/manifest mismatch")
        return data
    except (OSError, ValueError, TypeError, KeyError) as error:
        if isinstance(error, ExclusionError):
            raise
        raise ExclusionError("missing or invalid prepared IPSET manifest") from error


def native_user_ipsets(rows: list[list[str]], templates: dict[str, list[str]],
                       reference_root: Path, release: Path, static_root: Path) -> None:
    """Close alternative native include/exclude IP inputs through ONE parser."""
    prefixes = ("--ipset=", "--ipset-exclude=")
    for number, row in enumerate(rows, 1):
        # Native repeated selectors in one profile are one effective user
        # destination list for the family-wide coverage prohibition.
        inclusions: list[bytes] = []
        exclusions: list[bytes] = []
        for token in inherited(visible(row), templates):
            if token.startswith(("--ipset-ip=", "--ipset-exclude-ip=")):
                name, data = token.split("=", 1)
                if not data or len(data) > 262144:
                    raise ExclusionError(f"profile {number}: oversized inline IPSET")
                item = data.replace(",", "\n").encode("utf-8")
                (exclusions if name == "--ipset-exclude-ip" else inclusions).append(item)
            elif token.startswith(prefixes):
                name, value = token.split("=", 1)
                path = Path(value)
                if not path.is_absolute() or ".." in path.parts:
                    raise ExclusionError(f"profile {number}: unsafe IPSET path")
                try:
                    relative = path.relative_to(reference_root)
                except ValueError:
                    try:
                        relative = path.relative_to(static_root)
                    except ValueError as error:
                        raise ExclusionError(f"profile {number}: external IPSET path forbidden") from error
                    source = static_root / relative
                else:
                    source = release / relative
                # Resolve only a direct regular file below the approved tree.
                # A symlink in ANY intermediate component is untrusted.
                relative_source = source.relative_to(release if source.is_relative_to(release) else static_root)
                root_path = release if source.is_relative_to(release) else static_root
                current = root_path
                for part in relative_source.parts:
                    current = current / part
                    if current.is_symlink():
                        raise ExclusionError(f"profile {number}: symlinked IPSET reference")
                info = source.stat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 262144:
                    raise ExclusionError(f"profile {number}: untrusted IPSET reference")
                (exclusions if name == "--ipset-exclude" else inclusions).append(source.read_bytes())
        for label, chunks in (("include", inclusions), ("exclude", exclusions)):
            if chunks:
                # Semantic parsing and full-family union are exactly the Stage 1
                # source of truth; no second ipaddress parser is introduced.
                try:
                    parse_ipset(b"\n".join(chunks), f"profile {number} native {label} IPSET")
                except IPSetError as error:
                    raise ExclusionError(str(error)) from error


def compose(text: str, domain_source: Path, domain_ref: str,
            ipset_source: Path, ipset_ref: str,
            reference_root: Path, release: Path, static_root: Path) -> str:
    rows = segments(text)
    attest_manifest(release, ipset_source)
    if (domain_source != release / "managed/hostlist-exclude.txt" or
        domain_ref != str(reference_root / "managed/hostlist-exclude.txt") or
        ipset_ref != str(reference_root / "managed/ipset-exclude.txt") or
        domain_source.is_symlink() or not domain_source.is_file()):
        raise ExclusionError("unsafe or missing domain/IP exclusion source")
    try:
        use_domains = domain_source.stat().st_size > 0
        use_ips = ipset_source.stat().st_size > 0
    except OSError as error:
        raise ExclusionError("missing candidate exclusion lists") from error
    templates, kinds = templates_and_imports(rows)
    output: list[list[str]] = []
    for row, kind in zip(rows, kinds):
        tokens = visible(row)
        effective = inherited(tokens, templates)
        voice = any(t.startswith("--name=voice-") for t in effective)
        stun = is_stun(effective)
        # The mapped generator historically appended a single domain exclude
        # at the very end. Remove that exact synthetic token and reassign only
        # to applicable ordinary domain-aware profiles. Do not strip user lists.
        tokens = [t for t in tokens if t != "--hostlist-exclude=" + domain_ref]
        if (voice or stun) and any(t.startswith(("--hostlist-exclude=",
                "--hostlist-exclude-domains=")) for t in effective if t != "--hostlist-exclude=" + domain_ref):
            raise ExclusionError("hostlist exclusions forbidden in Voice/STUN profiles")
        if (voice or stun) and kind == "profile":
            # Templates are not executable; their contents are checked at
            # importing profiles, where native STUN scope is known.
            pass
        if kind == "profile" and use_domains and not (voice or stun) and domain_aware(effective):
            tokens.append("--hostlist-exclude=" + domain_ref)
        if use_ips:
            # Always append AFTER all --import and user-supplied profile flags;
            # the template cannot override the mandatory last profile filter.
            tokens = [t for t in tokens if t != "--ipset-exclude=" + ipset_ref]
            tokens.append("--ipset-exclude=" + ipset_ref)
        output.append(([row[0]] if row[0].startswith("--new=") else []) + tokens)
    native_user_ipsets(output, templates, reference_root, release, static_root)
    blocks = []
    for idx, row in enumerate(output):
        if idx:
            blocks.append("--new" if not row[0].startswith("--new=") else row.pop(0))
        blocks.extend(row)
    return "\n".join(blocks) + "\n"


def audit(text: str, domain_source: Path, domain_ref: str,
          ipset_source: Path, ipset_ref: str,
          reference_root: Path, release: Path, static_root: Path) -> None:
    result = compose(text, domain_source, domain_ref, ipset_source, ipset_ref,
                     reference_root, release, static_root)
    if result != text.strip() + "\n":
        raise ExclusionError("native profile exclusion policy is missing or incorrectly ordered")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "audit"))
    parser.add_argument("argv_file", type=Path)
    parser.add_argument("domain_source", type=Path)
    parser.add_argument("domain_reference")
    parser.add_argument("ipset_source", type=Path)
    parser.add_argument("ipset_reference")
    parser.add_argument("reference_root", type=Path)
    parser.add_argument("release", type=Path)
    parser.add_argument("static_root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.argv_file.is_symlink() or args.argv_file.stat().st_size > ARGS_LIMIT:
            raise ExclusionError("unsafe engine argv")
        source = args.argv_file.read_text(encoding="utf-8")
        result = compose(source, args.domain_source, args.domain_reference,
                         args.ipset_source, args.ipset_reference, args.reference_root,
                         args.release, args.static_root)
        if args.action == "audit":
            if result != source.strip() + "\n":
                raise ExclusionError("native global exclusions do not match final executable profiles")
        elif result != source:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.argv_file.parent,
                                             prefix=".global-exclusion-", delete=False) as temp:
                stage = Path(temp.name)
                try:
                    temp.write(result)
                    temp.flush()
                    os.fsync(temp.fileno())
                except Exception:
                    stage.unlink(missing_ok=True)
                    raise
            os.replace(stage, args.argv_file)
        if args.action == "apply":
            # Immutable release-local proof distinguishes Stage 3 argv from a
            # predecessor release generated by earlier profile semantics.
            # Old releases have no marker and retain their original witness.
            witness = args.argv_file.with_name("dvtws.args.global-policy.json")
            if witness.is_symlink() or witness.exists():
                raise ExclusionError("global profile witness already exists")
            document = {
                "schema": 1,
                "argv_sha256": hashlib.sha256(args.argv_file.read_bytes()).hexdigest(),
                "profiles": len(segments(result)),
            }
            with witness.open("x", encoding="utf-8") as target:
                target.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
            witness.chmod(0o644)
    except (ExclusionError, OSError, UnicodeError) as error:
        print("ERROR: final profile exclusion refused: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
