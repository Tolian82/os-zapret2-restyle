#!/usr/bin/env python3
"""Read-only native GUI Voice selection preflight under the original FD9.

The one-lock, one-source parser produces a read-only preview of saved choices.
No writable stage, native PREPARED, ledger, IPFW or Config mutation exists here.
"""
from __future__ import annotations

import fcntl
from pathlib import Path
import json
import os
import sys

from voice_native_lifecycle_router import _locked_config
from voice_native_saved_draft_candidate import preview_saved_draft_candidate
from voice_ipfw_adapter import require_lifecycle_lock

CONFIG = Path("/conf/config.xml")


def preview(mask: str, original_config_sha: str) -> dict:
    require_lifecycle_lock()
    fd = os.open(CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner = (os.geteuid(), os.getegid())
        require_lifecycle_lock()
        _locked_config(CONFIG, fd, owner)
        result = preview_saved_draft_candidate(
            config_path=CONFIG, mask=mask,
            expected_sha=original_config_sha,
            config_fd=fd, config_owner=owner,
            require_lifecycle_owner=require_lifecycle_lock,
        )
        require_lifecycle_lock()
        _locked_config(CONFIG, fd, owner)
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
