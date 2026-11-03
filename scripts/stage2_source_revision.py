#!/usr/bin/env python3
"""Fail-closed current candidate revision for native CI.

Historical evidence modules preserve their original pinned witness revisions.
Only current candidate drivers share this canonical Makefile source.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def revision_from_makefile(path=None):
    candidate = Path(path) if path is not None else ROOT / "Makefile"
    body = candidate.read_text(encoding="utf-8")
    declared = [line for line in body.splitlines()
                if line.lstrip().startswith("PLUGIN_REVISION")]
    matches = re.findall(r"(?m)^PLUGIN_REVISION=[ \t]*([1-9][0-9]{0,5})[ \t]*$", body)
    if len(declared) != 1 or len(matches) != 1:
        raise ValueError("NATIVE_SOURCE_REVISION_MISSING_OR_AMBIGUOUS")
    return matches[0]
