#!/usr/bin/env python3
"""Pure composition of staged Voice and existing ordinary dvtws2 profiles.

This is an inert build helper. It neither enables the old Telegram Voice PoC
nor starts another dvtws2 process. When all Voice services are OFF, the
ordinary profile text is preserved exactly (including trailing whitespace).
"""
from __future__ import annotations

from pathlib import Path
import ipaddress
import sys

from voice_profile_compiler import parse_ports


class VoiceMergeError(ValueError):
    pass


def profile_scope(tokens: list[str], ipsets: dict[str, list[str]]) -> tuple[list, list]:
    """Resolve only native selectors needed to prove STUN scopes disjoint.

    Paths refer to the candidate's lists, never the currently installed lists.
    Unknown selectors fail closed instead of reading arbitrary paths.
    """
    ports = []
    networks = []
    has_ipset = False
    # Ordinary Strategies may carry IPv6-only STUN. It cannot intercept
    # IPv4 Voice packets, but conflicting/ambiguous native L3 selectors
    # must NEVER be allowed to mask a later IPv4 selector.
    l3_selectors = [token.partition("=")[2] for token in tokens
                    if token.startswith("--filter-l3=")]
    if len(l3_selectors) > 1:
        raise VoiceMergeError("competing profile priority: duplicate STUN L3 selector")
    if l3_selectors:
        families = l3_selectors[0].split(",")
        if not families or any(family not in ("ipv4", "ipv6") for family in families) or (
            len(set(families)) != len(families)
        ):
            raise VoiceMergeError("competing profile priority: invalid STUN L3 selector")
        if "ipv4" not in families:
            return [], []
    for token in tokens:
        if token.startswith("--filter-udp="):
            try:
                ports.extend(parse_ports(token.partition("=")[2], "ordinary STUN"))
            except ValueError as exc:
                raise VoiceMergeError("competing profile priority: invalid STUN UDP ports") from exc
        elif token.startswith("--ipset=") or token.startswith("--ipset-ip="):
            has_ipset = True
            value = token.partition("=")[2]
            entries = value.split(",") if token.startswith("--ipset-ip=") else ipsets.get(value)
            if entries is None:
                raise VoiceMergeError("competing profile priority: cannot verify ordinary STUN IPSET")
            for entry in entries:
                try:
                    networks.append(ipaddress.IPv4Network(entry, strict=False))
                except ValueError as exc:
                    raise VoiceMergeError("competing profile priority: invalid STUN destination") from exc
    if not ports:
        if any(t.startswith("--filter-tcp=") for t in tokens):
            return [], []
        ports = [(1, 65535)]
    if not has_ipset:
        networks = [ipaddress.IPv4Network("0.0.0.0/0")]
    return ports, networks


def profile_tokens(text: str) -> list[list[str]]:
    profiles = [[]]
    for line in text.splitlines():
        if line.strip() == "--new":
            profiles.append([])
        else:
            profiles[-1].extend(line.split())
    return profiles


def check_stun_scopes(voice: str, ordinary: str, ipsets: dict[str, list[str]]) -> None:
    voice_scopes = [profile_scope(tokens, ipsets) for tokens in profile_tokens(voice)]
    for tokens in profile_tokens(ordinary):
        if not any(t.startswith(("--filter-l7=", "--payload=")) and
                   "stun" in t.partition("=")[2].split(",") for t in tokens):
            continue
        ports, networks = profile_scope(tokens, ipsets)
        for vp, vn in voice_scopes:
            if any(a <= d and c <= b for a, b in ports for c, d in vp) and any(
                    left.overlaps(right) for left in networks for right in vn):
                raise VoiceMergeError("competing profile priority: ordinary STUN overlaps Voice IP/UDP scope")


def merge_profiles(voice: str, ordinary: str, ipsets: dict[str, list[str]] | None = None) -> str:
    if not isinstance(voice, str) or not isinstance(ordinary, str):
        raise VoiceMergeError("native Voice and ordinary strategies must be text")
    if not ordinary.strip():
        raise VoiceMergeError("ordinary Traffic Strategy is empty")
    if "\x00" in ordinary or "\r" in ordinary or "\x00" in voice or "\r" in voice:
        raise VoiceMergeError("invalid NUL/CR in resolved strategy")
    lines = [line.strip() for line in ordinary.splitlines() if line.strip()]
    if lines and (lines[0] == "--new" or lines[-1] == "--new"):
        raise VoiceMergeError("ordinary Strategy starts or ends with an empty profile")
    if any(line.startswith("--name=voice-") or
           line == "--name=telegram-voice-poc" for line in lines):
        raise VoiceMergeError("ordinary Strategy collides with reserved Voice identity")
    if not voice:
        return ordinary
    voice_lines = [line.strip() for line in voice.splitlines() if line.strip()]
    if not voice_lines or voice_lines[0] == "--new" or voice_lines[-1] == "--new":
        raise VoiceMergeError("Voice generator produced an empty profile boundary")
    if not any(line.startswith("--name=voice-") for line in voice_lines):
        raise VoiceMergeError("missing generated Voice identity")
    if any(token.startswith(("--filter-l7=", "--payload=")) and
           "stun" in token.partition("=")[2].split(",") for token in ordinary.split()):
        check_stun_scopes(voice, ordinary, ipsets or {})
    # A single mandatory boundary separates Voice's last native profile
    # from the untouched first ordinary profile. Internal boundaries of
    # either source remain in their original relative order.
    return voice.rstrip("\n") + "\n--new\n" + ordinary


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: voice_traffic_merge.py STAGED_VOICE.conf USER_TRAFFIC.conf OUTPUT.conf",
              file=sys.stderr)
        return 64
    src_voice, src_ordinary, destination = map(Path, argv[1:])
    try:
        result = merge_profiles(src_voice.read_text(encoding="utf-8"),
                                src_ordinary.read_text(encoding="utf-8"))
        # A unique candidate path is owned by the calling staging transaction.
        # Refuse accidental changes to a pre-existing active traffic.conf.
        with destination.open("x", encoding="utf-8") as output:
            output.write(result)
    except (ValueError, OSError, UnicodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
