#!/usr/bin/env python3
"""Single semantic normalizer for managed HOSTLIST domain fields.

PHP preflight (inspect) and shell candidate builder (single) call this
same Python parser. No Config, IPFW, service, FD9, or release mutations.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

MAX_INPUT_BYTES = 4 * 1024 * 1024
FIELDS = {
    "youtube": ("youtubedomains", "YouTube Domains", True),
    "user": ("userdomains", "User Domains", True),
    "exclude": ("excludedomains", "Exclude Domains", False),
}
PART_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\Z", re.ASCII)


class DomainPolicyError(ValueError):
    def __init__(self, kind: str, line: int, code: str):
        super().__init__(code)
        self.kind = kind
        self.line = line
        self.code = code

    def evidence(self) -> dict:
        field, _, _ = FIELDS[self.kind]
        return {"field": field, "line": self.line, "code": self.code}

    def diagnostic(self) -> str:
        _, label, _ = FIELDS[self.kind]
        return f"ERROR: {label}, line {self.line}: {self.code}"


def normalize(text: str, kind: str) -> dict:
    if kind not in FIELDS:
        raise ValueError("unknown domain field")
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("domain input is not bounded text")
    field, _, permit_modifiers = FIELDS[kind]
    entries: list[str] = []
    seen: dict[str, tuple[str, int]] = {}
    changed = duplicates = 0

    for line_no, raw in enumerate(text.splitlines(), 1):
        value = raw.strip()
        if not value:
            continue
        original = value
        prefix_match = re.match(r"[!^]*", value)
        prefix = prefix_match.group(0) if prefix_match else ""
        host = value[len(prefix):]
        if prefix and not permit_modifiers:
            raise DomainPolicyError(kind, line_no, "modifiers_not_allowed")
        if prefix.count("!") > 1 or prefix.count("^") > 1:
            raise DomainPolicyError(kind, line_no, "repeated_modifier")
        if not host:
            raise DomainPolicyError(kind, line_no, "missing_domain")

        host = re.sub(r"^https?://", "", host, flags=re.IGNORECASE)
        host = re.split(r"[/?#]", host, maxsplit=1)[0].strip()
        if host.startswith("*."):
            if prefix:
                raise DomainPolicyError(kind, line_no, "modifier_with_wildcard")
            host = host[2:]
        host = re.sub(r"^[,;:]+|[,;:]+$", "", host)
        host = host.strip(". \t\r\n\x00\x0b").lower()
        if not host:
            raise DomainPolicyError(kind, line_no, "missing_domain")
        if re.fullmatch(r"[0-9.]+", host, flags=re.ASCII) or "/" in host:
            raise DomainPolicyError(kind, line_no, "ip_in_domain_list")
        if len(host.encode("utf-8")) > 253 or ".." in host or any(
            len(part) > 63 or not PART_RE.fullmatch(part) for part in host.split(".")
        ):
            raise DomainPolicyError(kind, line_no, "invalid_domain")

        canonical_flags = ("!" if "!" in prefix else "") + ("^" if "^" in prefix else "")
        item = canonical_flags + host
        if item != original:
            changed += 1
        if host in seen:
            previous_flags, _ = seen[host]
            if previous_flags != canonical_flags:
                raise DomainPolicyError(kind, line_no, "conflicting_modifiers")
            duplicates += 1
            continue
        seen[host] = (canonical_flags, line_no)
        entries.append(item)

    return {
        "schema_version": 1,
        "field": field,
        "normalized": "\n".join(entries),
        "changed": changed,
        "duplicates": duplicates,
        "entry_count": len(entries),
    }


def _read_bounded(stream) -> str:
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("domain input exceeds maximum size")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("domain input must be UTF-8") from error


def _single(kind: str, source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError("domain input file missing or unsafe")
    if target.is_symlink() or target.parent.is_symlink() or not target.parent.is_dir():
        raise ValueError("domain output path is unsafe")
    with source.open("rb") as stream:
        content = _read_bounded(stream)
    normalized = normalize(content, kind)["normalized"]
    payload = (normalized + "\n" if normalized else "").encode("utf-8")
    name = None
    try:
        fd, name = tempfile.mkstemp(prefix=".domain-policy-", dir=target.parent)
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
        os.chmod(name, 0o644)
        os.replace(name, target)
        name = None
    finally:
        if name is not None:
            os.unlink(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("inspect")
    single = subs.add_parser("single")
    single.add_argument("kind", choices=FIELDS)
    single.add_argument("source", type=Path)
    single.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            payload = json.loads(_read_bounded(sys.stdin.buffer))
            if not isinstance(payload, dict) or set(payload) != {"kind", "text"}:
                raise ValueError("invalid domain inspection payload")
            result = normalize(payload["text"], payload["kind"])
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        else:
            _single(args.kind, args.source, args.target)
        return 0
    except DomainPolicyError as error:
        if args.command == "inspect":
            print(json.dumps({"schema_version": 1, "result": "failed", "error": error.evidence()}))
        else:
            print(error.diagnostic(), file=sys.stderr)
        return 2
    except (ValueError, OSError, TypeError, UnicodeError) as error:
        # Do not echo untrusted domain data, file contents, or raw JSON payloads.
        print("ERROR: domain policy input or runtime unavailable", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
