#!/usr/bin/env python3
"""Fail-closed CI scope gate: only the exact P5c FD9 read-only dispatch delta.

A new unrelated mutation in shared zapret_service.sh still requires native
Strategy Lab checks. Reuse this gate only for CI classification, not runtime.
"""
from __future__ import annotations

import re
import subprocess
import sys

SERVICE = "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
DISPATCH_BEFORE = '''        native-voice-preview-draft)
            native_voice_preview_draft_service "${2:-}" "${3:-}"
            ;;'''
DISPATCH_ADDITION = '''        strategy-preview)
            [ "$#" -eq 2 ] || return 64
            [ -x "${PYTHON_RUNTIME}" ] && [ -r "${BACKEND_DIR}/strategy_preview_route.py" ] ||
                return 69
            "${PYTHON_RUNTIME}" "${BACKEND_DIR}/strategy_preview_route.py" preview "$2"
            ;;
'''
PYTHON_GATE = "start|restart|reconfigure|telegram-voice-enable|telegram-voice-disable|shared-apply-*|strategy-lab"
PYTHON_PREVIEW = "start|restart|reconfigure|telegram-voice-enable|telegram-voice-disable|strategy-preview|shared-apply-*|strategy-lab"
FD9_GATE = "|native-voice-preview-draft|telegram-voice-enable|"
FD9_PREVIEW = "|native-voice-preview-draft|strategy-preview|telegram-voice-enable|"


def expected_p5c_delta(before: str) -> str | None:
    if before.count(DISPATCH_BEFORE) != 1 or before.count(PYTHON_GATE) != 1 or before.count(FD9_GATE) != 1:
        return None
    return (before
            .replace(DISPATCH_BEFORE, DISPATCH_ADDITION + DISPATCH_BEFORE, 1)
            .replace(PYTHON_GATE, PYTHON_PREVIEW, 1)
            .replace(FD9_GATE, FD9_PREVIEW, 1))


def is_preview_only(before: str, after: str) -> bool:
    expected = expected_p5c_delta(before)
    return expected is not None and after == expected


def self_test() -> None:
    source = "before\n" + DISPATCH_BEFORE + "\n" + PYTHON_GATE + "\n" + FD9_GATE + "\n"
    modified = expected_p5c_delta(source)
    assert modified is not None
    assert is_preview_only(source, modified)
    assert not is_preview_only(source, modified + "# unexpected\n")
    assert not is_preview_only(source, source)
    assert not is_preview_only(source.replace(PYTHON_GATE, ""), modified)
    print("CI_P5C_SERVICE_SCOPE_FAST=PASS")


def git_file(revision: str) -> str:
    if re.fullmatch(r"[a-f0-9]{40}", revision) is None:
        raise ValueError("full commit sha required")
    return subprocess.run(
        ["git", "show", revision + ":" + SERVICE],
        check=True, capture_output=True, text=True, timeout=10
    ).stdout


def main(args: list[str]) -> int:
    if args == ["--self-test"]:
        self_test()
        return 0
    if len(args) != 2:
        return 64
    before, after = git_file(args[0]), git_file(args[1])
    print("P5C_ONLY_SERVICE_DELTA=" + ("true" if is_preview_only(before, after) else "false"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
