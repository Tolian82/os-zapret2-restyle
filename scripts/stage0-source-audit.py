#!/usr/bin/env python3
"""Read-only full tracked-tree source audit for the native OPNsense Stage 0.

Inventory comes from Git's index (not filesystem globbing). Historical docs are
included in the complete file/mode inventory but excluded from active-code hits.
"""
import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

PATTERNS = {
    "python_minor": re.compile(r"python3\.\d+|python3\d{2,3}\b|EXPECTED_PYTHON\b"),
    "python_policy": re.compile(r"\b(?:PYTHON_BIN|EXTRA_PYTHON|PLUGIN_PYTHON)\b|/usr/local/bin/python3\b"),
    "python_process": re.compile(r"\bproc_open\s*\(|\bsubprocess(?:\.|\s+import)|\bsys\.executable\b"),
    "package_engine": re.compile(r"\bpkg-static\s+create\b|\bdep_origin\s*\(|\bget_make_var\s*\("),
    "dependency": re.compile(r"\bPLUGIN_DEPENDS\b|\bpkg\s+(?:install|add|fetch)\b|\b(?:pkgconf|gmake|luajit|python313)\b"),
    "repo_override": re.compile(r"FreeBSD\.conf|\b(?:REPOS_DIR|ENABLED_FREEBSD_REPO)\b"),
    "abi": re.compile(r"FreeBSD:\d+:[A-Za-z0-9_]+|\b(?:PLUGIN_ABI|ABI_VERSION)\b"),
}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def active(path):
    return (path.startswith(("src/", "pkg/", "scripts/", "repository/", ".github/workflows/"))
            or path in {"Makefile", "VERSION"})


def inspect(root):
    head = git(root, "rev-parse", "HEAD").decode().strip()
    records = []
    for item in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, blob, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise ValueError("unmerged index entry: " + raw_path.decode("utf-8", "replace"))
        path = raw_path.decode("utf-8", "surrogateescape")
        record = {"path": path, "mode": mode, "blob": blob, "active": active(path), "hits": []}
        if record["active"] and mode in {"100644", "100755"}:
            content = (root / path).read_bytes()
            if b"\0" not in content:
                for number, line in enumerate(content.decode("utf-8", "replace").splitlines(), 1):
                    types = [name for name, rule in PATTERNS.items() if rule.search(line)]
                    if types:
                        record["hits"].append({"line": number, "types": types,
                                               "snippet": line.strip()[:180]})
        records.append(record)
    return {"schema": 1, "head": head, "files": records}


def describe(report):
    records = report["files"]
    active_files = [r for r in records if r["active"]]
    hits = [(r["path"], h) for r in active_files for h in r["hits"]]
    mode_counts = Counter(r["mode"] for r in records)
    type_counts = Counter(t for _, h in hits for t in h["types"])
    service = next((r for r in records if r["path"] ==
                    "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"), None)
    return {"head": report["head"], "tracked": len(records), "active": len(active_files),
            "matching_lines": len(hits), "modes": dict(sorted(mode_counts.items())),
            "categories": dict(sorted(type_counts.items())),
            "service_mode": service["mode"] if service else "absent"}


def markdown(report):
    s = describe(report)
    lines = ["# Stage 0 — exact-head tracked source and executable-mode inventory", "",
             "**Evidence class:** source-only Git tree and checked-out file bytes; not a",
             "native OPNsense repository, installed package, live appliance or ELF qualification.",
             f"**HEAD:** \x60{s['head']}\x60", f"**Tracked files:** {s['tracked']}; "
             f"**active files:** {s['active']}; **matching lines:** {s['matching_lines']}.",
             f"**Modes:** \x60{json.dumps(s['modes'], sort_keys=True)}\x60; "
             f"**service source mode:** \x60{s['service_mode']}\x60.", "",
             "## Match categories (overlap allowed)", "",
             "| Category | Matching lines |", "|---|---:|"]
    for cat, number in s["categories"].items():
        lines.append(f"| \x60{cat}\x60 | {number} |")
    lines += ["", "## All active hits with source line and tracked mode", "",
              "\x60path:line [Git mode] (categories) excerpt\x60", ""]
    for rec in report["files"]:
        for hit in rec["hits"]:
            text = hit["snippet"].replace("\x60", "\\\x60")
            lines.append(f"- \x60{rec['path']}:{hit['line']}\x60 [\x60{rec['mode']}\x60] "
                         f"({', '.join(hit['types'])}): \x60{text}\x60")
    lines += ["", "## Full path/mode/blob map", "",
              "See the sibling machine-readable JSON artifact (\x60files[]\x60); unlike grep snippets,",
              "it includes every tracked path, unchanged files, Git blob SHA and symlink modes.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--expected-head", default="")
    args = parser.parse_args()
    root = args.root.resolve()
    report = inspect(root)
    if args.expected_head and args.expected_head != report["head"]:
        parser.error(f"exact-head mismatch: expected {args.expected_head}, observed {report['head']}")
    for target, content in ((args.json, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (args.markdown, markdown(report))):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    result = describe(report)
    print("STAGE0_SOURCE_AUDIT=READ_ONLY " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
