#!/usr/bin/env python3
"""Stage 1.09 scoped native production policy duplication guard.

Historical Stage 0 witnesses, OPNsense fixtures, CI guest release locks and
runtime Python migration debt are intentionally NOT claimed to be migrated.
"""
from pathlib import Path
import re
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


def main():
    try:
        print(scan({p: (ROOT / p).read_text(encoding="utf-8")
                    for p in PRODUCTION}))
    except (Refusal, OSError) as e:
        print("STAGE1_POLICY_STATIC=REFUSED:" + str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
