#!/usr/bin/env python3
"""Read-only native GUI Voice selection preflight under the original FD9.

The one-lock, one-source parser is shared with the later private publisher.
No writable stage, native PREPARED, ledger, IPFW or Config mutation exists here.
"""
from __future__ import annotations

import fcntl
import json
import os
import sys

from voice_native_recovery_quiescence import _locked_config
from voice_native_saved_draft_candidate import preview_saved_draft_candidate
from voice_native_legacy_poc_guard import _require_no_legacy_poc
import voice_ipfw_runtime as native


def preview(mask: str, original_config_sha: str) -> dict:
    native.require_native_lock()
    fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner = (os.geteuid(), os.getegid())
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, owner)
        # The native Apply refuses an active legacy Telegram PoC marker or
        # runtime flag. Preview must refuse the SAME conflict, before its
        # "previewed" UI result; never imply the candidate is executable.
        _require_no_legacy_poc()
        result = preview_saved_draft_candidate(
            config_path=native.CONFIG, mask=mask,
            expected_sha=original_config_sha,
            config_fd=fd, config_owner=owner,
            require_lifecycle_owner=native.require_native_lock,
        )
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, owner)
        _require_no_legacy_poc()
        if result.get("state") != "native-voice-saved-draft-preview" or (
            result.get("safe_to_enable_voice") is not False
            or result.get("public_voice_apply") is not False
        ):
            raise RuntimeError("invalid native Voice preview seal")
        return result
    finally:
        os.close(fd)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] != "preview-draft":
        print("usage: voice_native_draft_preview_route.py preview-draft FIVE_BIT_MASK CONFIG_SHA256",
              file=sys.stderr)
        return 64
    try:
        report = preview(argv[1], argv[2])
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, RuntimeError, ValueError, KeyError):
        print("ERROR: native Voice saved-draft preview refused; Config or lifecycle changed",
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
