#!/usr/bin/env python3
"""Fail-closed G03 native routing: genuine setup changes vs P4 help-only text.

This read-only script runs on an isolated GitHub runner. It has no access to
OPNsense runtime state and never edits source or user configuration.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

VIEW = "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"
SETUP_PATHS = frozenset({
    "src/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh",
    "src/opnsense/scripts/OPNsense/Zapret/setup.sh",
    "scripts/test-g03-first-install.sh",
    "scripts/test-gui-upstream-progress.mjs",
    "scripts/stage2-opnsense-g03-first-install.py",
})
START = "const strategiesHelpRU = {"
END = "function localizeStrategiesForm()"


def without_help(text: str) -> str:
    """Mask only the existing static P3/P4 help dictionary and info strings.

    All runnable frontend code outside this bounded range must remain byte-for-
    byte identical for a help-only G03 exemption. A missing/ambiguous marker
    raises an error and forces the native gate instead of skipping it.
    """
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("missing or duplicated help boundary")
    first, last = text.index(START), text.index(END)
    if first >= last:
        raise ValueError("reversed help boundary")
    region = text[first:last]
    if region.count("const strategiesInfoRU =") != 1 or region.count("const strategiesInfoEN =") != 1:
        raise ValueError("unexpected help structure")
    return text[:first] + "<P4_HELP_ONLY> " + text[last:]


def native_required(changed: set[str], base_view: str, head_view: str) -> bool:
    if SETUP_PATHS & changed or VIEW not in changed:
        return True
    try:
        return without_help(base_view) != without_help(head_view)
    except ValueError:
        return True


def self_test() -> None:
    base = (
        "prefix;\nconst strategiesHelpRU = { a: 'old' };\n"
        "const strategiesInfoRU = 'ru';\nconst strategiesInfoEN = 'en';\n"
        "function localizeStrategiesForm() { return true; }\nsetup();\n"
    )
    updated = base.replace("a: 'old'", "a: 'new'")
    assert not native_required({VIEW}, base, updated)
    assert native_required({VIEW, next(iter(SETUP_PATHS))}, base, updated)
    assert native_required({VIEW}, base, updated.replace("setup();", "changedSetup();"))
    assert native_required({VIEW}, base, updated.replace(START, "const replacedHelp = {"))
    assert native_required(set(), base, updated)
    print("PASS: P4-help-only skips native G03; setup/runtime/unknown changes require it")


def run() -> None:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    required = True
    if event == "pull_request":
        base = os.environ.get("G03_BASE_SHA", "")
        head = os.environ.get("G03_HEAD_SHA", "")
        if not (re.fullmatch(r"[0-9a-f]{40}", base) and re.fullmatch(r"[0-9a-f]{40}", head)):
            raise ValueError("missing exact PR base/head SHA")
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", base, head], text=True, timeout=20,
        ).splitlines())
        if VIEW in changed and not SETUP_PATHS.intersection(changed):
            old = subprocess.check_output(
                ["git", "show", f"{base}:{VIEW}"], text=True, timeout=20,
            )
            new = subprocess.check_output(
                ["git", "show", f"{head}:{VIEW}"], text=True, timeout=20,
            )
            required = native_required(changed, old, new)
    result = "true" if required else "false"
    print("G03_NATIVE_REQUIRED=" + result + " (scope: source diff only)")
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        raise ValueError("GITHUB_OUTPUT is missing")
    with Path(output).open("a", encoding="utf-8") as stream:
        stream.write("native_required=" + result + "\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif sys.argv[1:] == ["--classify"]:
        run()
    else:
        raise SystemExit("usage: g03_native_scope.py --self-test|--classify")
