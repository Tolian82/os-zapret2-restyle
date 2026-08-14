#!/usr/bin/env python3
"""Validate the four canonical rule books and their cross-reference registries."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOKS = {
    "DOC": ROOT / "docs" / "DOCUMENTATION_RULES.md",
    "DEV": ROOT / "docs" / "PROJECT_PRINCIPLES.md",
    "CHAT": ROOT / "docs" / "CHAT_RULES.md",
    "GH": ROOT / "docs" / "GITHUB_PUBLICATION.md",
}
RULE_START = re.compile(r"^(DOC|DEV|CHAT|GH)-(\d{3})\.\s", re.M)
SINGLE = re.compile(r"`?(DOC|DEV|CHAT|GH)-(\d{3})`?")
RANGE = re.compile(r"`?(DOC|DEV|CHAT|GH)-(\d{3})`?\s*[–-]\s*`?\1-(\d{3})`?")
OUT_BEGIN = "<!-- RULE-XREF-OUT-BEGIN -->"
OUT_END = "<!-- RULE-XREF-OUT-END -->"
IN_BEGIN = "<!-- RULE-XREF-IN-BEGIN -->"
IN_END = "<!-- RULE-XREF-IN-END -->"

DEEP_HISTORY_PREFIXES = (
    "docs/history/",
    "docs/decisions/",
    "docs/devlog/",
    "docs/audit/",
    "docs/patches/",
    "docs/releases/",
    "docs/verification/",
)
DEEP_HISTORY_FILES = {
    "docs/AUDIT.md",
    "docs/DECISIONS.md",
    "docs/DEVLOG.md",
    "docs/CHANGELOG.md",
}
TEXT_SUFFIXES = {".md", ".sh", ".py", ".yml", ".yaml", ".txt"}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def expand_refs(text: str) -> set[str]:
    refs: set[str] = set()
    masked = text
    for match in list(RANGE.finditer(text)):
        prefix, first, last = match.groups()
        start = int(first)
        end = int(last)
        if end < start:
            fail(f"descending rule range: {match.group(0)}")
        refs.update(f"{prefix}-{n:03d}" for n in range(start, end + 1))
    masked = RANGE.sub(" ", masked)
    for prefix, number in SINGLE.findall(masked):
        refs.add(f"{prefix}-{number}")
    return refs


def read_books() -> tuple[dict[str, str], dict[str, set[str]]]:
    texts: dict[str, str] = {}
    ids: dict[str, set[str]] = {}
    for prefix, path in BOOKS.items():
        if not path.is_file():
            fail(f"missing canonical rule book: {path.relative_to(ROOT)}")
        text = path.read_text(encoding="utf-8")
        texts[prefix] = text
        found = [f"{p}-{n}" for p, n in RULE_START.findall(text)]
        if not found:
            fail(f"no {prefix} rules found in {path.relative_to(ROOT)}")
        if len(found) != len(set(found)):
            fail(f"duplicate rule ID in {path.relative_to(ROOT)}")
        if any(not item.startswith(prefix + "-") for item in found):
            fail(f"wrong rule domain in {path.relative_to(ROOT)}")
        ids[prefix] = set(found)
    return texts, ids


def rule_blocks(text: str) -> list[tuple[str, str]]:
    registry_at = text.find("## Cross-reference registry")
    body = text if registry_at < 0 else text[:registry_at]
    matches = list(RULE_START.finditer(body))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks.append((f"{match.group(1)}-{match.group(2)}", body[start:end]))
    return blocks


def actual_pairs(texts: dict[str, str], known: set[str]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for source_book, text in texts.items():
        for source, block in rule_blocks(text):
            for target in expand_refs(block):
                if target == source:
                    continue
                if target not in known:
                    fail(f"{source} references nonexistent canonical rule {target}")
                if target.split("-", 1)[0] != source_book:
                    pairs.add((source, target))
    return pairs


def registry_section(text: str, begin: str, end: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        fail(f"registry markers {begin}/{end} must appear exactly once")
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    return text[start:stop]


def parse_registry_pairs(section: str, direction: str, known: set[str]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2 or "Source rule" in cells[0] or "Target rule" in cells[0]:
            continue
        left = expand_refs(cells[0])
        right = expand_refs(cells[1])
        if not left or not right:
            fail(f"unparseable registry row: {line}")
        for item in left | right:
            if item not in known:
                fail(f"registry references nonexistent canonical rule {item}")
        if direction == "out":
            pairs.update((source, target) for source in left for target in right)
        else:
            pairs.update((source, target) for target in left for source in right)
    return pairs


def validate_registries(texts: dict[str, str], actual: set[tuple[str, str]], known: set[str]) -> None:
    for book, text in texts.items():
        outbound = parse_registry_pairs(registry_section(text, OUT_BEGIN, OUT_END), "out", known)
        inbound = parse_registry_pairs(registry_section(text, IN_BEGIN, IN_END), "in", known)
        expected_out = {pair for pair in actual if pair[0].startswith(book + "-")}
        expected_in = {pair for pair in actual if pair[1].startswith(book + "-")}
        missing_out = sorted(expected_out - outbound)
        stale_out = sorted(outbound - expected_out)
        missing_in = sorted(expected_in - inbound)
        stale_in = sorted(inbound - expected_in)
        if missing_out or stale_out or missing_in or stale_in:
            fail(
                f"{book} registry mismatch; missing_out={missing_out}, stale_out={stale_out}, "
                f"missing_in={missing_in}, stale_in={stale_in}"
            )


def validate_active_references(known: set[str]) -> None:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    for rel in proc.stdout.splitlines():
        if rel in DEEP_HISTORY_FILES or rel.startswith(DEEP_HISTORY_PREFIXES):
            continue
        path = ROOT / rel
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for ref in expand_refs(text):
            if ref not in known:
                fail(f"active file {rel} references nonexistent canonical rule {ref}")


def main() -> None:
    texts, ids_by_book = read_books()
    known = set().union(*ids_by_book.values())
    actual = actual_pairs(texts, known)
    validate_registries(texts, actual, known)
    validate_active_references(known)
    print(
        "PASS: four canonical rule books have unique persistent IDs, valid active references, "
        "and exact bidirectional cross-reference registries"
    )


if __name__ == "__main__":
    main()
