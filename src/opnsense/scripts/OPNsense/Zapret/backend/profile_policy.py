#!/usr/bin/env python3
"""One Python implementation of the existing staged strategy-profile contract.

Parser and normalizer shell entrypoints keep their external ABI; Python handles
--new boundaries, placeholder syntax/indexing, and selector profile expansion.
This module does not interpret dvtws2 options, own Config, IPFW, FD9 or Apply.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import re
import sys
import tempfile

PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_.-]*>", re.ASCII)
SELECTOR = re.compile(r"<(HOSTLIST|IPSET):[A-Za-z0-9][A-Za-z0-9_.-]*>", re.ASCII)
NAMED_NEW = re.compile(r"--new=([A-Za-z0-9_.-]+)\Z", re.ASCII)
MAX_PROFILES = 4096


class ProfilePolicyError(ValueError):
    pass


def _safe_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ProfilePolicyError("profile input missing or unsafe")
    return path.read_bytes()


def _lines(data: bytes) -> list[str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProfilePolicyError("profile input must be UTF-8") from exc
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.removesuffix("\r") for line in lines]


def _profile_bytes(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_file(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise ProfilePolicyError("unsafe profile output path")
    path.write_bytes(data)


def split_profiles(data: bytes) -> list[bytes]:
    """Mirror existing parser.sh --new (including --new=name and blank case)."""
    lines = _lines(data)
    groups: list[list[str]] = [[]]
    nonempty = False
    for lineno, line in enumerate(lines, 1):
        separator = line.strip()
        match = NAMED_NEW.fullmatch(separator)
        if separator == "--new" or match:
            if not nonempty:
                raise ProfilePolicyError(f"empty strategy profile before --new at line {lineno}")
            if len(groups) >= MAX_PROFILES:
                raise ProfilePolicyError("too many strategy profiles")
            groups.append([] if match is None else ["--name=" + match.group(1)])
            nonempty = False
            continue
        groups[-1].append(line)
        if line.strip():
            nonempty = True
    if len(groups) == 1 and not nonempty:
        return []
    if not nonempty:
        raise ProfilePolicyError("empty strategy profile after the final --new")
    return [_profile_bytes(group) for group in groups]


def _tokens(data: bytes) -> list[tuple[str, str]]:
    """Generic placeholder index: unique TYPE/NAME in first-seen order."""
    seen: dict[tuple[str, str], None] = {}
    for line in _lines(data):
        for token in PLACEHOLDER.finditer(line):
            typ, name = token.group()[1:-1].split(":", 1)
            seen[(typ, name)] = None
    return list(seen)


def validate_syntax(data: bytes, profile_no: int) -> None:
    for lineno, line in enumerate(_lines(data), 1):
        if "<" in PLACEHOLDER.sub("", line) or ">" in PLACEHOLDER.sub("", line):
            raise ProfilePolicyError(
                f"invalid placeholder syntax in profile {profile_no}, line {lineno}: expected <TYPE:NAME>"
            )


def _supported(data: bytes) -> list[tuple[str, str]]:
    seen: dict[tuple[str, str], None] = {}
    for line in _lines(data):
        for token in SELECTOR.finditer(line):
            typ, name = token.group()[1:-1].split(":", 1)
            seen[(typ, name)] = None
    return list(seen)


def expand_profiles(source: list[bytes]) -> list[bytes]:
    expanded: list[bytes] = []
    for profile_no, data in enumerate(source, 1):
        validate_syntax(data, profile_no)
        selectors = _supported(data)
        if len(selectors) <= 1:
            expanded.append(data)
            continue
        text = data.decode("utf-8")
        for selected in selectors:
            def replace(token: re.Match[str]) -> str:
                typ, name = token.group()[1:-1].split(":", 1)
                return token.group() if (typ, name) == selected else ""
            expanded.append(SELECTOR.sub(replace, text).encode("utf-8"))
            if len(expanded) > MAX_PROFILES:
                raise ProfilePolicyError("too many normalized profiles")
    return expanded


def _read_profiles(workdir: Path, count: int) -> list[bytes]:
    if count < 0 or count > MAX_PROFILES:
        raise ProfilePolicyError("invalid profile count")
    count_text = _safe_file(workdir / "profile-count").decode("ascii").strip()
    if count_text != str(count):
        raise ProfilePolicyError("profile count does not match staged parser count")
    if count == 0:
        return []
    return [_safe_file(workdir / f"profile-{index}.conf") for index in range(1, count + 1)]


def _replace_profiles(workdir: Path, files: list[bytes]) -> None:
    """Prepare all output before switching. Restore original files on failure."""
    if not workdir.is_dir() or workdir.is_symlink():
        raise ProfilePolicyError("profile work directory missing or unsafe")
    if len(files) > MAX_PROFILES:
        raise ProfilePolicyError("too many strategy profiles")
    with tempfile.TemporaryDirectory(prefix=".profiles-python-", dir=workdir) as temp:
        stage = Path(temp) / "stage"
        backup = Path(temp) / "backup"
        stage.mkdir()
        backup.mkdir()
        for no, content in enumerate(files, 1):
            _write_file(stage / f"profile-{no}.conf", content)
        _write_file(stage / "profile-count", f"{len(files)}\n".encode("ascii"))
        originals = [p for p in workdir.glob("profile-*.conf") if p.is_file() or p.is_symlink()]
        originals.extend([workdir / "profile-count"] if (workdir / "profile-count").exists() else [])
        if any(p.is_symlink() for p in originals):
            raise ProfilePolicyError("unsafe existing profile path")
        moved: list[Path] = []
        installed: list[Path] = []
        try:
            for path in originals:
                path.rename(backup / path.name)
                moved.append(path)
            for path in sorted(stage.glob("profile-*.conf"), key=lambda p: int(p.stem.split("-")[1])):
                destination = workdir / path.name
                path.rename(destination)
                installed.append(destination)
            destination = workdir / "profile-count"
            (stage / "profile-count").rename(destination)
            installed.append(destination)
        except OSError:
            for path in installed:
                path.unlink(missing_ok=True)
            for path in moved:
                (backup / path.name).rename(path)
            raise


def command_parse(workdir: Path) -> int:
    if not workdir.is_dir() or workdir.is_symlink():
        raise ProfilePolicyError("parser work directory missing or unsafe")
    groups = split_profiles(_safe_file(workdir / "traffic.input"))
    _replace_profiles(workdir, groups)
    return len(groups)


def command_normalize(workdir: Path, count: int) -> int:
    source = _read_profiles(workdir, count)
    if count == 0:
        return 0
    expanded = expand_profiles(source)
    _replace_profiles(workdir, expanded)
    return len(expanded)


def command_index(source: Path, target: Path) -> None:
    tokens = _tokens(_safe_file(source))
    data = "".join(f"{typ}\t{name}\n" for typ, name in tokens).encode("utf-8")
    if not target.parent.is_dir() or target.is_symlink():
        raise ProfilePolicyError("placeholder output path unsafe")
    with tempfile.NamedTemporaryFile(prefix=".profile-index-", dir=target.parent, delete=False) as stream:
        staged = Path(stream.name)
        try:
            stream.write(data)
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
    try:
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    split = subs.add_parser("parse")
    split.add_argument("workdir", type=Path)
    check = subs.add_parser("validate")
    check.add_argument("number", type=int)
    check.add_argument("source", type=Path)
    index = subs.add_parser("index")
    index.add_argument("source", type=Path)
    index.add_argument("target", type=Path)
    normalize = subs.add_parser("normalize")
    normalize.add_argument("workdir", type=Path)
    normalize.add_argument("count", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "parse":
            print(command_parse(args.workdir))
        elif args.command == "validate":
            validate_syntax(_safe_file(args.source), args.number)
        elif args.command == "index":
            command_index(args.source, args.target)
        else:
            print(command_normalize(args.workdir, args.count))
        return 0
    except (OSError, UnicodeError, ProfilePolicyError, ValueError) as exc:
        # Never include strategy text or other user-controlled contents in logs.
        print(f"ERROR: profile policy: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
