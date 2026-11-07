#!/usr/bin/env python3
"""Guard the real owner package instruction against dependency-blind pkg add.

The native guest-D check separately exercises this route using the SAME
already-built archive and a fresh OPNsense appliance without preinstalled git.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def need(ok, detail):
    if not ok:
        raise SystemExit("FAIL: testing package install route: " + detail)


chat = (ROOT / "docs/CHAT_RULES.md").read_text()
rule = chat.split("CHAT-027.", 1)[1].split("\n\n", 1)[0]
need("pkg install git ca_root_nss jq gmake pkgconf luajit" in rule,
     "CHAT-027 must provision official prerequisite packages")
need("pkg add -f /root/os-zapret2-restyle-<actual-version>.pkg" in rule,
     "CHAT-027 must use native local archive installer after prerequisites")
need("Do NOT use `pkg install -f /path/to/archive.pkg`" in rule,
     "CHAT-027 must warn of observed native pkg solver crash")

publication = (ROOT / "docs/GITHUB_PUBLICATION.md").read_text()
rule = publication.split("GH-060.", 1)[1].split("\n\n", 1)[0]
need("(`fetch`, `pkg install git ca_root_nss jq gmake pkgconf luajit`, `pkg add -f`, `pkg info -x`)" in rule,
     "GH-060 must provision native deps before local pkg add")

readme = (ROOT / "README.md").read_text()
need("## Installing a testing package from a downloaded `.pkg`" in readme,
     "README lacks standalone archive instructions")
need("pkg install -n git ca_root_nss jq gmake pkgconf luajit" in readme and
     "pkg add -f /path/to/" in readme,
     "README missing approved dependency plan then local pkg route")
need("segfaulted" in readme, "README hides observed OPNsense solver crash")

make = (ROOT / "Makefile").read_text()
need("python${PLUGIN_PYTHON} gmake pkgconf luajit git jq ca_root_nss" in make,
     "required runtime Git dependency was silently dropped")

workflow = (ROOT / ".github/workflows/stage5-native-cross-clean-running.yml").read_text()
job = workflow.split("\n  install-same-archive-without-preinstalled-git:", 1)
need(len(job) == 2, "missing fresh native guest D regression")
guest = job[1]
for marker in (
    "needs: build-and-verify-clean-install",
    "actions/download-artifact@v8",
    "stage5-native-single-artifact.py verify",
    "if pkg info -q git",
    "pkg -o REPO_AUTOUPDATE=false install -n git ca_root_nss jq gmake pkgconf luajit",
    "pkg -o REPO_AUTOUPDATE=false install -y git ca_root_nss jq gmake pkgconf luajit",
    'pkg -o REPO_AUTOUPDATE=false add -f "$package"',
    "pkg info -q git",
    "pkg query '%R' git",
    'sha256 -q "$package"',
):
    need(marker in guest, "guest D lacks " + marker)
need("install -n -f" not in guest and "pkg add -M" not in guest,
     "guest D reintroduced crash-prone solver route or bypassed pkg safety")
print("PASS: canonical owner route and fresh OPNsense missing-git installation regression")
