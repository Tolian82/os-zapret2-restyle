#!/usr/bin/env python3
"""Pure composition of staged Voice and existing ordinary dvtws2 profiles.

This is an inert build helper. It neither enables the old Telegram Voice PoC
nor starts another dvtws2 process. When all Voice services are OFF, the
ordinary profile text is preserved exactly (including trailing whitespace).
"""
from __future__ import annotations

from pathlib import Path
import sys


class VoiceMergeError(ValueError):
    pass


def merge_profiles(voice: str, ordinary: str) -> str:
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
    # Native first-match STUN semantics make an ordinary STUN profile
    # ambiguous when Voice is prepended. Reject conservatively until a
    # full destination/port-scope comparison is available.
    if any(token in ("--filter-l7=stun", "--payload=stun") for token in lines):
        raise VoiceMergeError(
            "ordinary Strategies also contain STUN; review competing profile priority before enabling Voice"
        )
    voice_lines = [line.strip() for line in voice.splitlines() if line.strip()]
    if not voice_lines or voice_lines[0] == "--new" or voice_lines[-1] == "--new":
        raise VoiceMergeError("Voice generator produced an empty profile boundary")
    if not any(line.startswith("--name=voice-") for line in voice_lines):
        raise VoiceMergeError("missing generated Voice identity")
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
