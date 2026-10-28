#!/usr/bin/env python3
"""Single bounded, deterministic compiler for candidate-managed IPv4/IPv6 IPSETs.

No live IPFW, saved Config or active release writes. Batch mode is the authority;
legacy single-file mode delegates to the identical semantic parser.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
import tempfile

SCHEMA_VERSION = 1
MAX_BYTES = 262_144
MAX_ENTRIES = 4096
LISTS = ("telegram", "discord", "x", "sip", "custom", "exclude")
LABELS = {"telegram": "Telegram IPs", "discord": "DISCORD IPs", "x": "X IPs",
          "sip": "SIP IPs", "custom": "CUSTOM IPs", "exclude": "Exclude IPSet"}


class IPSetError(ValueError):
    """A labeled, line-aware invalid user IPSET."""


def parse_ipset(raw: bytes, label: str, *, collapse: bool = False) -> tuple[str, dict]:
    if len(raw) > MAX_BYTES:
        raise IPSetError(f"{label}: input exceeds {MAX_BYTES} bytes")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IPSetError(f"{label}: input is not UTF-8: {exc}") from exc
    lines = content.splitlines()
    if len(lines) > MAX_ENTRIES:
        raise IPSetError(f"{label}: exceeds {MAX_ENTRIES} input lines")
    normalized: list[str] = []
    seen: set[str] = set()
    networks: dict[int, list[ipaddress.IPv4Network | ipaddress.IPv6Network]] = {4: [], 6: []}
    for line_no, raw_line in enumerate(lines, 1):
        value = raw_line.strip()
        if not value:
            continue
        if '%' in value:
            raise IPSetError(f"{label}, line {line_no}: IPv6 zone indices are forbidden: '{value}'")
        try:
            parsed = ipaddress.ip_network(value, strict=True) if "/" in value else ipaddress.ip_address(value)
        except ValueError as exc:
            raise IPSetError(f"{label}, line {line_no}: invalid IP address or CIDR '{value}': {exc}") from exc
        network = parsed if isinstance(parsed, (ipaddress.IPv4Network, ipaddress.IPv6Network)) else ipaddress.ip_network(parsed)
        if network.prefixlen == 0:
            raise IPSetError(f"{label}, line {line_no}: full-family /0 is forbidden")
        if network.version == 6 and network.network_address.ipv4_mapped is not None:
            raise IPSetError(f"{label}, line {line_no}: IPv4-mapped IPv6 is not a supported user IPSET form")
        # /32 and /128 are exactly equivalent to hosts in native IPSET.
        canonical = str(network.network_address) if network.prefixlen == network.max_prefixlen else str(network)
        if canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)
            networks[network.version].append(network)
    unions = {family: list(ipaddress.collapse_addresses(networks[family])) for family in (4, 6)}
    for family in (4, 6):
        if any(net.prefixlen == 0 for net in unions[family]):
            raise IPSetError(f"{label}: combined IPv{family} networks cover the entire /0 address family")
    if collapse:
        normalized = [str(n.network_address) if n.prefixlen == n.max_prefixlen else str(n)
                      for family in (4, 6) for n in unions[family]]
    output = "".join(value + "\n" for value in normalized)
    manifest = {
        "sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "entry_count": len(normalized),
        "family_counts": {"ipv4": len(networks[4]), "ipv6": len(networks[6])},
        "union": {"ipv4": [str(net) for net in unions[4]],
                  "ipv6": [str(net) for net in unions[6]]},
        "full_family": False,
    }
    return output, manifest


def read_bounded(path: Path, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise IPSetError(f"{label}: input must be a regular file: {path}")
    with path.open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise IPSetError(f"{label}: input exceeds {MAX_BYTES} bytes")
    return data


def write_staged(destination: Path, content: bytes) -> None:
    # A private candidate subdirectory is staged before any output is replaced.
    destination.write_bytes(content)
    destination.chmod(0o644)


def batch(input_root: Path, managed: Path, manifest_path: Path) -> None:
    if not managed.is_dir() or managed.is_symlink():
        raise IPSetError(f"managed candidate directory must exist and not be a symlink: {managed}")
    if manifest_path.parent != managed.parent:
        raise IPSetError("manifest must be in the candidate release next to managed/")
    if manifest_path.is_symlink():
        raise IPSetError("manifest destination may not be a symlink")
    compiled: dict[str, bytes] = {}
    evidence: dict[str, dict] = {}
    for name in LISTS:
        content, witness = parse_ipset(read_bounded(input_root / f"{name}.txt", LABELS[name]),
                                       LABELS[name], collapse=name == "exclude")
        compiled[name] = content.encode("utf-8")
        evidence[name] = witness
    document = {"schema_version": SCHEMA_VERSION, "lists": evidence}
    witness_bytes = (json.dumps(document, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=True) + "\n").encode("utf-8")
    with tempfile.TemporaryDirectory(prefix=".ipset-policy-", dir=managed.parent) as scratch:
        stage = Path(scratch)
        for name, content in compiled.items():
            write_staged(stage / f"ipset-{name}.txt", content)
        write_staged(stage / "ipset-manifest.json", witness_bytes)
        # This candidate is not the active release. Validate ALL lists before
        # publishing ANY files; downstream activation owns final atomic swap.
        for name in LISTS:
            os.replace(stage / f"ipset-{name}.txt", managed / f"ipset-{name}.txt")
        os.replace(stage / "ipset-manifest.json", manifest_path)


def single(source: Path, target: Path, label: str) -> None:
    content, _ = parse_ipset(read_bounded(source, label), label)
    if target.is_symlink():
        raise IPSetError(f"{label}: destination may not be a symlink")
    target.write_text(content, encoding="utf-8")


def inspect(payload: object) -> dict:
    """Read-only semantic preview for GUI preflight, not an Apply authority.

    Uses the SAME parse_ipset invoked by the native batch. No file paths,
    Config, IPFW, proxy, network calls or auxiliary address parser.
    """
    if not isinstance(payload, dict) or set(payload) != set(LISTS):
        raise IPSetError("expected exactly six named IPSET strings")
    result: dict[str, dict] = {}
    networks: dict[str, dict[int, list]] = {}
    for name in LISTS:
        raw = payload[name]
        if not isinstance(raw, str):
            raise IPSetError(f"{LABELS[name]} must be a text list")
        output, proof = parse_ipset(raw.encode("utf-8"), LABELS[name],
                                  collapse=name == "exclude")
        result[name] = {"normalized": output.rstrip("\n"), **proof}
        networks[name] = {
            family: [ipaddress.ip_network(value) for value in proof["union"][f"ipv{family}"]]
            for family in (4, 6)
        }
    overlapping = []
    for index, left in enumerate(LISTS[:-1]):
        for right in LISTS[index + 1:-1]:
            if any(
                first.overlaps(second)
                for family in (4, 6)
                for first in networks[left][family]
                for second in networks[right][family]
            ):
                overlapping.append([left, right])
    return {"schema_version": SCHEMA_VERSION, "lists": result, "overlaps": overlapping}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("single", help="legacy API via shared parser")
    for positional in ("source", "target", "label"):
        one.add_argument(positional)
    many = sub.add_parser("batch", help="compile exactly six lists and a manifest")
    for positional in ("input_root", "managed_root", "manifest"):
        many.add_argument(positional)
    sub.add_parser("inspect", help="read-only six-list JSON stdin preflight")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            raw = sys.stdin.buffer.read(6 * MAX_BYTES + 16384 + 1)
            if len(raw) > 6 * MAX_BYTES + 16384:
                raise IPSetError("bounded inspect request exceeded")
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise IPSetError("invalid IPSET inspection request") from exc
            print(json.dumps(inspect(payload), separators=(",", ":")))
        elif args.command == "single":
            single(Path(args.source), Path(args.target), args.label)
        else:
            batch(Path(args.input_root), Path(args.managed_root), Path(args.manifest))
    except (IPSetError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
