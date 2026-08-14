#!/usr/bin/env python3
"""Validate tracked local Markdown links and local Markdown heading fragments."""

from __future__ import annotations

import html
import pathlib
import re
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.M)
FENCE = re.compile(r"^\s*(```|~~~)")
ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
SETEXT = re.compile(r"^\s*(=+|-+)\s*$")
HTML_ID = re.compile(r"\b(?:id|name)=[\"']([^\"']+)[\"']", re.I)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
INLINE_CODE = re.compile(r"`[^`]*`")
TAG = re.compile(r"<[^>]+>")
PUNCT = re.compile(r"[^\w\- ]", re.UNICODE)


def fail(errors: list[str]) -> None:
    print("FAIL: invalid local Markdown links:", file=sys.stderr)
    for item in errors:
        print(f"  - {item}", file=sys.stderr)
    raise SystemExit(1)


def tracked_markdown() -> list[pathlib.Path]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "*.md"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [ROOT / rel for rel in proc.stdout.splitlines() if rel]


def markdown_text(path: pathlib.Path) -> str:
    """Decode current UTF-8 and legacy Level-3 Markdown without rewriting history.

    Replacement decoding preserves ASCII Markdown link syntax/destinations even when an
    old historical file contains isolated non-UTF-8 bytes. Current/new documentation
    remains subject to the repository's normal UTF-8/style contracts; this reader merely
    avoids requiring a destructive encoding migration of retained history to validate links.
    """

    return path.read_bytes().decode("utf-8", errors="replace")


def strip_fenced_code(text: str) -> str:
    result: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            result.append("")
            continue
        result.append("" if fence else line)
    return "\n".join(result)


def destination(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    return value.split()[0] if value else ""


def github_slug(raw: str) -> str:
    value = html.unescape(raw)
    value = INLINE_CODE.sub(lambda m: m.group(0).strip("`"), value)
    value = TAG.sub("", value)
    value = value.strip().lower()
    value = PUNCT.sub("", value)
    value = re.sub(r"\s+", "-", value)
    return value


def markdown_anchors(path: pathlib.Path) -> set[str]:
    text = markdown_text(path)
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    lines = text.splitlines()
    in_fence: str | None = None

    for index, line in enumerate(lines):
        fence_match = FENCE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if in_fence is None:
                in_fence = marker
            elif in_fence == marker:
                in_fence = None
            continue
        if in_fence:
            continue

        for explicit in HTML_ID.findall(line):
            anchors.add(urllib.parse.unquote(explicit).lower())

        heading: str | None = None
        atx = ATX.match(line)
        if atx:
            heading = atx.group(2)
        elif index + 1 < len(lines) and line.strip() and SETEXT.match(lines[index + 1]):
            heading = line.strip()

        if heading is None:
            continue
        base = github_slug(heading)
        if not base:
            continue
        seen = counts.get(base, 0)
        slug = base if seen == 0 else f"{base}-{seen}"
        counts[base] = seen + 1
        anchors.add(slug)

    return anchors


def local_target(source: pathlib.Path, raw: str) -> tuple[pathlib.Path, str] | None:
    dest = html.unescape(destination(raw))
    if not dest or dest.startswith("#"):
        fragment = urllib.parse.unquote(dest[1:]) if dest.startswith("#") else ""
        return source, fragment
    if dest.startswith("//") or SCHEME.match(dest):
        return None

    parsed = urllib.parse.urlsplit(dest)
    if parsed.scheme or parsed.netloc:
        return None
    path_text = urllib.parse.unquote(parsed.path)
    fragment = urllib.parse.unquote(parsed.fragment)
    if not path_text:
        return source, fragment
    if path_text.startswith("/"):
        target = ROOT / path_text.lstrip("/")
    else:
        target = source.parent / path_text
    return target.resolve(), fragment


def main() -> None:
    errors: list[str] = []
    anchor_cache: dict[pathlib.Path, set[str]] = {}
    files = tracked_markdown()

    for source in files:
        text = markdown_text(source)
        searchable = strip_fenced_code(text)
        raw_links = [match.group(1) for match in INLINE_LINK.finditer(searchable)]
        raw_links.extend(match.group(1) for match in REFERENCE_DEF.finditer(searchable))

        for raw in raw_links:
            resolved = local_target(source, raw)
            if resolved is None:
                continue
            target, fragment = resolved
            rel_source = source.relative_to(ROOT)
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(f"{rel_source}: local link escapes repository: {destination(raw)}")
                continue

            if not target.exists():
                errors.append(f"{rel_source}: missing target: {destination(raw)}")
                continue

            if fragment and target.is_file() and target.suffix.lower() == ".md":
                fragment_key = fragment.lower()
                if fragment_key not in anchor_cache.setdefault(target, markdown_anchors(target)):
                    rel_target = target.relative_to(ROOT)
                    errors.append(f"{rel_source}: missing Markdown anchor #{fragment} in {rel_target}")

    if errors:
        fail(errors)
    print(f"PASS: {len(files)} tracked Markdown files have resolvable local links and Markdown anchors")


if __name__ == "__main__":
    main()
