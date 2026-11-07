#!/usr/bin/env python3
"""Stage 1.09 scoped native production policy duplication guard.

Historical Stage 0 witnesses, OPNsense fixtures, CI guest release locks and
runtime Python migration debt are intentionally NOT claimed to be migrated.
"""
from pathlib import Path, PurePosixPath
import argparse
import difflib
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ("scripts/native-opnsense-package.py",
              "scripts/build-pkg.sh",
              "scripts/compatibility-bootstrap.sh",
              "Makefile")
DISALLOWED = {
    "DUPLICATE_FREEBSD_ABI": re.compile(r"FreeBSD:[0-9]+:(?:amd64|arm64)"),
    "VERSIONED_PYTHON_EXECUTABLE": re.compile(r"/usr/local/bin/python3\.[0-9]+"),
    "INDEPENDENT_PYTHON_PACKAGE_DEPENDENCY": re.compile(
        r"(?m)^PLUGIN_DEPENDS\s*[:?+!]?=\s*python3[0-9]{2}\b"),
    "INDEPENDENT_PRODUCT_ABI_ASSIGNMENT": re.compile(
        r"(?m)^\s*(?:PRODUCT_ABI|OPNSENSE_ABI|ABI)\s*=\s*[\"']"),
    "INDEPENDENT_MK_PRODUCT_ABI_MATCH": re.compile(
        r"result\[\W?PLUGIN_ABI\W?\]\s*==\s*['\"]\d+\.")
}


class Refusal(ValueError):
    pass


def scan(sources):
    for path in PRODUCTION:
        if path not in sources:
            raise Refusal("MISSING_PRODUCTION_POLICY_CONSUMER:" + path)
        data = sources[path]
        for code, pattern in DISALLOWED.items():
            if pattern.search(data):
                raise Refusal(code + ":" + path)
    native = sources["scripts/native-opnsense-package.py"]
    if ("compat.check_target(policy, product, abi, cpu" not in native or
            "stage_policy(plugin)" not in native or
            'platform["freebsd_pkg_abi"]' not in native):
        raise Refusal("POLICY_CONSUMER_NOT_WIRED")
    if "python${PLUGIN_PYTHON}" not in sources["Makefile"]:
        raise Refusal("OFFICIAL_MK_PYTHON_RESOLUTION_MISSING")
    return {"status": "PASS_SCOPED_NATIVE_POLICY_SINGLE_SOURCE",
            "production_checked": len(PRODUCTION),
            "historical_fixture_exceptions": True}



SOURCE_EXTENSIONS = frozenset({
    ".py", ".sh", ".php", ".lua", ".xml", ".inc",
    ".conf", ".json", ".js", ".mk", ".pl", ".bash",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".go", ".rs", ".ts", ".tsx",
})
BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp",
    ".so", ".a", ".o", ".bin", ".dat", ".pyc",
    ".woff", ".woff2", ".ttf", ".otf", ".pdf",
    ".zip", ".pkg", ".gz", ".xz", ".bz2", ".zst",
})


def classify_path(path):
    """Classify actual changed paths, not a second product-file inventory."""
    p = PurePosixPath(path)
    if not path or any(part in ("..", ".", "") for part in p.parts):
        raise Refusal("UNQUALIFIED_CHANGED_PATH:" + path)
    if path.startswith(("src/", "pkg/")):
        return "production"
    if path.startswith("scripts/"):
        name = p.name
        if (name.startswith("test-") or
                (re.match(r"^stage[0-9]+-", name) and path not in PRODUCTION)):
            return "fixture"
        return "production"
    if len(p.parts) == 1 and (p.suffix.lower() in SOURCE_EXTENSIONS or
                              not p.suffix and path not in ("Makefile", "VERSION", "LICENSE")):
        return "unclassified"
    return "other"


def introduced_lines(old, new):
    before = old.splitlines(keepends=True)
    after = new.splitlines(keepends=True)
    delta = difflib.SequenceMatcher(None, before, after, autojunk=False)
    return "".join("".join(after[j1:j2])
                   for tag, i1, i2, j1, j2 in delta.get_opcodes()
                   if tag in ("insert", "replace"))


def scan_changed(changed):
    """Validate introduced production lines; preserve historical fixture identities."""
    checked = []
    for path, added_content in sorted(changed.items()):
        category = classify_path(path)
        if category == "unclassified":
            raise Refusal("UNCLASSIFIED_NEW_EXECUTION_PATH:" + path)
        if (category != "production" or
                PurePosixPath(path).suffix.lower() in BINARY_SUFFIXES):
            continue
        for code, pattern in DISALLOWED.items():
            if pattern.search(added_content):
                raise Refusal(code + ":" + path)
        checked.append(path)
    return checked


def git_text(revision, path, *, missing_ok=False):
    proc = subprocess.run(
        ["git", "show", revision + ":" + path],
        cwd=ROOT, capture_output=True, check=False, timeout=30)
    if proc.returncode:
        if missing_ok:
            return ""
        raise Refusal("CHANGED_GIT_BLOB_UNAVAILABLE:" + path)
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise Refusal("CHANGED_SOURCE_NOT_UTF8:" + path) from None


def changed_contents(base, head):
    """Read the exact Git diff, including previously unknown production paths."""
    for label, sha in (("base", base), ("head", head)):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise Refusal("UNQUALIFIED_GIT_" + label.upper())
    diff = subprocess.run(
        ["git", "diff", "--name-only", "-z", "--diff-filter=ACMR",
         "--no-ext-diff", base, head, "--"],
        cwd=ROOT, capture_output=True, check=False, timeout=30)
    if diff.returncode:
        raise Refusal("CHANGED_GIT_DIFF_FAILED")
    result = {}
    try:
        paths = [p.decode("utf-8") for p in diff.stdout.rstrip(b"\0").split(b"\0") if p]
    except UnicodeDecodeError:
        raise Refusal("CHANGED_GIT_PATH_NOT_UTF8") from None
    for path in paths:
        category = classify_path(path)
        if category == "unclassified":
            raise Refusal("UNCLASSIFIED_NEW_EXECUTION_PATH:" + path)
        if (category != "production" or
                PurePosixPath(path).suffix.lower() in BINARY_SUFFIXES):
            continue
        previous = git_text(base, path, missing_ok=True)
        current = git_text(head, path)
        result[path] = introduced_lines(previous, current)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    args = parser.parse_args()
    try:
        source = {p: (ROOT / p).read_text(encoding="utf-8") for p in PRODUCTION}
        report = scan(source)
        if bool(args.base_sha) != bool(args.head_sha):
            raise Refusal("CHANGED_SOURCE_REQUIRES_BASE_AND_HEAD")
        if args.base_sha:
            report["introduced_production_paths_checked"] = scan_changed(
                changed_contents(args.base_sha, args.head_sha))
        print(report)
    except (Refusal, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("STAGE1_POLICY_STATIC=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
