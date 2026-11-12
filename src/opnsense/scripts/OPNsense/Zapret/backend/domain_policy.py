#!/usr/bin/env python3
"""Single semantic normalizer for managed HOSTLIST domain fields.

PHP preflight (inspect) and shell candidate builder (single) call this
same Python parser. Auto-detect planning uses a qualified offline PSL and
complete list snapshots; it performs no writes or profile attribution itself.
No Config, IPFW, service, FD9, or release mutations.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
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
PSL_PATH = Path(__file__).with_name("data") / "public_suffix_list.dat"
MAX_PSL_BYTES = 2 * 1024 * 1024


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


class AutoDomainPolicyError(ValueError):
    """Stable, content-free diagnostic; callers must retain unprocessed input."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _ascii_host(host: str) -> str:
    """Strict discovery/PSL hostname, unlike the legacy manual URL adapter."""
    if not isinstance(host, str) or not host or len(host) > 1024:
        raise AutoDomainPolicyError("invalid_host")
    # Native raw events are hostnames, never URLs, modifiers, wildcards or IPs.
    host = host.lower()
    if host.endswith("."):
        host = host[:-1]
    if not host or host.startswith(".") or ".." in host or any(
        c.isspace() or ord(c) < 32 or c in "/:!?^*#[]\\\x7f" for c in host
    ):
        raise AutoDomainPolicyError("invalid_host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise AutoDomainPolicyError("ip_literal")
    if re.fullmatch(r"[0-9.]+", host, re.ASCII):
        raise AutoDomainPolicyError("ip_literal")
    ascii_host = host
    if not host.isascii() or any(part.startswith("xn--") for part in host.split(".")):
        try:
            # The stdlib's IDNA2003 would change e.g. faß.de into fass.de.
            # IDNA2008 retains the name; no compatibility/transitional mapping.
            import idna
        except ImportError:
            raise AutoDomainPolicyError("idna_unavailable") from None
        try:
            ascii_host = idna.encode(host, strict=True).decode("ascii")
        except (idna.IDNAError, UnicodeError):
            raise AutoDomainPolicyError("invalid_idna") from None
    elif any(part[2:4] == "--" for part in host.split(".")):
        raise AutoDomainPolicyError("invalid_idna")
    if len(ascii_host) > 253 or any(
        len(part) > 63 or not PART_RE.fullmatch(part)
        for part in ascii_host.split(".")
    ):
        raise AutoDomainPolicyError("invalid_host")
    return ascii_host


class PublicSuffixList:
    """PSL longest-rule/wildcard/exception algorithm with both divisions.

    No implicit '*' for an unknown suffix: discovery must fail closed.
    Normal operation loads only the hash-bound list shipped with this module.
    """

    def __init__(self, raw: bytes, expected_sha256: str):
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_PSL_BYTES:
            raise AutoDomainPolicyError("invalid_psl")
        self.sha256 = hashlib.sha256(raw).hexdigest()
        if self.sha256 != expected_sha256:
            raise AutoDomainPolicyError("psl_hash_mismatch")
        self.exact: set[str] = set()
        self.wildcard: set[str] = set()
        self.exception: set[str] = set()
        self.counts = {"ICANN": 0, "PRIVATE": 0}
        active = None
        markers = []
        try:
            lines = raw.decode("utf-8").splitlines()
        except UnicodeError:
            raise AutoDomainPolicyError("invalid_psl") from None
        for line in lines:
            line = line.strip()
            marker = re.fullmatch(r"// ===(BEGIN|END) (ICANN|PRIVATE) DOMAINS===", line)
            if marker:
                action, section = marker.groups()
                if (action == "BEGIN" and active is not None) or (
                    action == "END" and active != section
                ):
                    raise AutoDomainPolicyError("invalid_psl_sections")
                active = section if action == "BEGIN" else None
                markers.append((action, section))
                continue
            if not line or line.startswith("//"):
                continue
            if active is None:
                raise AutoDomainPolicyError("invalid_psl_sections")
            rule = line.split()[0]
            target = self.exact
            if rule.startswith("!"):
                target, rule = self.exception, rule[1:]
            elif rule.startswith("*."):
                target, rule = self.wildcard, rule[2:]
            # Rule syntax is stricter than a discovery's optional final dot.
            if rule.endswith("."):
                raise AutoDomainPolicyError("invalid_psl_rule")
            try:
                rule = _ascii_host(rule)
            except AutoDomainPolicyError as error:
                if error.code == "idna_unavailable":
                    raise
                raise AutoDomainPolicyError("invalid_psl_rule") from None
            if rule in target:
                raise AutoDomainPolicyError("duplicate_psl_rule")
            target.add(rule)
            self.counts[active] += 1
        if markers != [("BEGIN", "ICANN"), ("END", "ICANN"),
                       ("BEGIN", "PRIVATE"), ("END", "PRIVATE")] or not all(self.counts.values()):
            raise AutoDomainPolicyError("invalid_psl_sections")
        if any(rule.split(".", 1)[-1] not in self.wildcard or "." not in rule
               for rule in self.exception):
            raise AutoDomainPolicyError("invalid_psl_exception")

    @classmethod
    def load(cls, path: Path = PSL_PATH) -> PublicSuffixList:
        try:
            metadata_path = path.with_suffix(".json")
            if path.is_symlink() or metadata_path.is_symlink():
                raise AutoDomainPolicyError("psl_unavailable")
            with metadata_path.open("rb") as stream:
                raw_metadata = stream.read(4097)
            if len(raw_metadata) > 4096:
                raise AutoDomainPolicyError("invalid_psl_metadata")
            metadata = json.loads(raw_metadata)
            if not isinstance(metadata, dict) or metadata.get("schema_version") != 1 or not (
                re.fullmatch(r"[a-f0-9]{40}", metadata.get("commit", "")) and
                re.fullmatch(r"[a-f0-9]{64}", metadata.get("sha256", "")) and
                metadata.get("source") == "https://github.com/publicsuffix/list" and
                metadata.get("license") == "MPL-2.0"
            ):
                raise AutoDomainPolicyError("invalid_psl_metadata")
            with path.open("rb") as stream:
                raw = stream.read(MAX_PSL_BYTES + 1)
            result = cls(raw, metadata["sha256"])
            result.commit = metadata["commit"]
            return result
        except (OSError, ValueError, TypeError) as error:
            if isinstance(error, AutoDomainPolicyError):
                raise
            raise AutoDomainPolicyError("psl_unavailable") from None

    def registrable_domain(self, hostname: str) -> str:
        host = _ascii_host(hostname)
        labels = host.split(".")
        matched = exception = 0
        for index in range(len(labels)):
            suffix = ".".join(labels[index:])
            count = len(labels) - index
            if suffix in self.exception:
                exception = max(exception, count - 1)
            if suffix in self.exact:
                matched = max(matched, count)
            if index and suffix in self.wildcard:
                matched = max(matched, count + 1)
        length = exception or matched
        if not length:
            if host in self.wildcard:
                raise AutoDomainPolicyError("public_suffix")
            raise AutoDomainPolicyError("unknown_suffix")
        if len(labels) <= length:
            raise AutoDomainPolicyError("public_suffix")
        return ".".join(labels[-length-1:])


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
        try:
            host = _ascii_host(host)
        except AutoDomainPolicyError as error:
            if error.code == "idna_unavailable":
                raise
            raise DomainPolicyError(kind, line_no, "invalid_domain") from None

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


def _list_entries(text: str, kind: str = "user") -> list[tuple[str, bool, bool]]:
    try:
        normalized = normalize(text, kind)["normalized"]
    except (ValueError, TypeError):
        # A broken exclusion snapshot cannot be silently skipped.
        raise AutoDomainPolicyError("invalid_list_snapshot") from None
    rows = []
    for entry in normalized.splitlines():
        flags = entry[:len(entry) - len(entry.lstrip("!^"))]
        rows.append((entry[len(flags):], "!" in flags, "^" in flags))
    return rows


def _covers(host: str, entry: tuple[str, bool, bool]) -> bool:
    domain, _, exact = entry
    return host == domain or (not exact and host.endswith("." + domain))


def plan_auto_additions(discoveries: list[dict], hostlists: dict[str, str],
                        automatic: dict[str, str], global_exclude: str = "", *,
                        psl: PublicSuffixList | None = None) -> dict:
    """Plan idempotent changes from a complete, already-attributed snapshot.

    hostlists contains ALL manual HOSTLIST components and the editable shared
    'auto' file. automatic contains only proven auto-owned components/rows;
    manual entries must never be labelled as owned. No file/config writes.
    The caller supplies map-eligible observations only (no IPSET/Voice events).
    Unknown/stale/ambiguous hostlist attribution is None, never inferred here.
    """
    if not isinstance(hostlists, dict) or "auto" not in hostlists or not isinstance(automatic, dict):
        raise AutoDomainPolicyError("incomplete_list_snapshot")
    if not isinstance(discoveries, list) or len(discoveries) > 100000 or any(
        not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", key)
        for key in hostlists
    ) or not set(automatic).issubset(hostlists):
        raise AutoDomainPolicyError("invalid_auto_input")
    # Verify the PSL even for an empty batch; never substitute last-two-labels.
    psl = psl if psl is not None else PublicSuffixList.load()
    manual = {name: _list_entries(text) for name, text in hostlists.items()}
    owned = {name: _list_entries(text) for name, text in automatic.items()}
    global_rows = _list_entries(global_exclude, "exclude")
    exclusions = [row for entries in [*manual.values(), *owned.values()]
                  for row in entries if row[1]]
    grouped: dict[str, set[str]] = {}
    rejected, excluded = [], []
    for index, event in enumerate(discoveries):
        try:
            if not isinstance(event, dict) or set(event) != {"hostname", "hostlist"} or not (
                event["hostlist"] is None or isinstance(event["hostlist"], str)
            ):
                raise AutoDomainPolicyError("invalid_discovery")
            # Resolve the map-supplied attribution BEFORE collapsing the host.
            origin = event["hostlist"] if event["hostlist"] in hostlists else "auto"
            host = _ascii_host(event["hostname"])
            root = psl.registrable_domain(host)
            if any(_covers(name, row) for name in (host, root) for row in global_rows):
                excluded.append({"index": index, "code": "global_exclusion"})
                continue
            if any(_covers(name, row) for name in (host, root) for row in exclusions):
                excluded.append({"index": index, "code": "hostlist_exclusion"})
                continue
            grouped.setdefault(root, set()).add(origin)
        except AutoDomainPolicyError as error:
            rejected.append({"index": index, "code": error.code})

    additions: dict[str, list[str]] = {}
    removals: dict[str, list[str]] = {}
    routes = []
    for root, origins in sorted(grouped.items()):
        # Previous auto-owned rows also carry provenance across worker batches.
        previous = {name for name, entries in owned.items() if (root, False, False) in entries}
        origins = origins | previous
        destination = next(iter(origins)) if len(origins) == 1 else "auto"
        # On ambiguity, relocate ONLY auto-owned plain rows. Never edit manual
        # text, exact positives or negative entries, even in a supplied snapshot.
        for name in sorted(previous - {destination}):
            removals.setdefault(name, []).append(root)
        target_rows = manual[destination] + owned.get(destination, [])
        covered = any(not row[1] and _covers(root, row) for row in target_rows)
        if not covered:
            additions.setdefault(destination, []).append(root)
        routes.append({"root": root, "destination": destination,
                       "reason": "ambiguous" if len(origins) > 1 else "attributed",
                       "result": "covered" if covered else "add"})
    return {"schema_version": 1, "result": "partial" if rejected else "ok",
            "psl_sha256": psl.sha256, "additions": additions, "removals": removals,
            "routes": routes, "excluded": excluded, "unprocessed": rejected}


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
    subs.add_parser("auto-plan")
    subs.add_parser("psl-status")
    single = subs.add_parser("single")
    single.add_argument("kind", choices=FIELDS)
    single.add_argument("source", type=Path)
    single.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "psl-status":
            psl = PublicSuffixList.load()
            print(json.dumps({"schema_version": 1, "sha256": psl.sha256,
                              "commit": psl.commit, "rules": psl.counts}))
        elif args.command == "auto-plan":
            payload = json.loads(_read_bounded(sys.stdin.buffer))
            if not isinstance(payload, dict) or set(payload) != {
                "discoveries", "hostlists", "automatic", "global_exclude"
            }:
                raise AutoDomainPolicyError("invalid_auto_input")
            print(json.dumps(plan_auto_additions(**payload), separators=(",", ":")))
        elif args.command == "inspect":
            payload = json.loads(_read_bounded(sys.stdin.buffer))
            if not isinstance(payload, dict) or set(payload) != {"kind", "text"}:
                raise ValueError("invalid domain inspection payload")
            result = normalize(payload["text"], payload["kind"])
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        else:
            _single(args.kind, args.source, args.target)
        return 0
    except AutoDomainPolicyError as error:
        print(json.dumps({"schema_version": 1, "result": "unprocessed", "code": error.code}))
        return 2
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
