#!/usr/bin/env python3
"""Check/update the packaged PSL from an explicit official upstream git commit.

Developer-only, offline after git fetch. Never downloads on the appliance or
changes Config/runtime/lists. Publish a refreshed snapshot by the normal pkg PR.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/domain_policy.py"
SPEC = importlib.util.spec_from_file_location("domain_policy", MODULE)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


def git(checkout, *args):
    result = subprocess.run(["git", "-C", str(checkout), *args],
                            capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError("upstream git object unavailable")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-checkout", type=Path)
    parser.add_argument("--commit")
    args = parser.parse_args()
    try:
        if args.upstream_checkout is not None or args.commit is not None:
            if args.upstream_checkout is None or not re.fullmatch(r"[a-f0-9]{40}", args.commit or ""):
                raise ValueError("supply official checkout and full immutable commit")
            remote = git(args.upstream_checkout, "remote", "get-url", "origin").decode().strip()
            if remote.removesuffix(".git") != "https://github.com/publicsuffix/list":
                raise ValueError("official publicsuffix/list origin required")
            git(args.upstream_checkout, "cat-file", "-e", args.commit + "^{commit}")
            raw = git(args.upstream_checkout, "show", args.commit + ":public_suffix_list.dat")
            if b"https://mozilla.org/MPL/2.0/" not in raw[:1000]:
                raise ValueError("upstream license notice missing")
            digest = hashlib.sha256(raw).hexdigest()
            psl = policy.PublicSuffixList(raw, digest)
            if psl.registrable_domain("x.user.github.io") != "user.github.io" or (
                psl.registrable_domain("video.example.co.uk") != "example.co.uk"
            ):
                raise ValueError("ICANN/PRIVATE qualification failed")
            metadata = {"schema_version": 1, "source": "https://github.com/publicsuffix/list",
                        "commit": args.commit, "sha256": digest, "license": "MPL-2.0"}
            # These are tracked developer source files, not the live worker store.
            # A partial edit is refused by load/hash checks and cannot pass CI.
            policy.PSL_PATH.write_bytes(raw)
            policy.PSL_PATH.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
        psl = policy.PublicSuffixList.load()
        print(json.dumps({"result": "qualified", "commit": psl.commit,
                          "sha256": psl.sha256, "rules": psl.counts}))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("ERROR: PSL source qualification failed: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
