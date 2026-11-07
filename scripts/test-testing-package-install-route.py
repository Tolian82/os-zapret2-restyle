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
need("pkg install -f /root/os-zapret2-restyle-<actual-version>.pkg" in rule,
     "CHAT-027 must emit dependency-solving owner command")
need("Use dependency-resolving `pkg install -f`" in rule,
     "CHAT-027 must distinguish pkg install from pkg add")
need("pkg add -f /root/os-zapret2-restyle-<actual-version>.pkg" not in rule,
     "CHAT-027 reverted to dependency-blind installation")

publication = (ROOT / "docs/GITHUB_PUBLICATION.md").read_text()
rule = publication.split("GH-060.", 1)[1].split("\n\n", 1)[0]
need("(`fetch`, `pkg install -f`, `pkg info -x`)" in rule,
     "GH-060 delivery contract still advertises pkg add")

readme = (ROOT / "README.md").read_text()
need("## Installing a testing package from a downloaded `.pkg`" in readme,
     "README lacks standalone archive instructions")
need("pkg install -n -f" in readme and "pkg install -f" in readme,
     "README missing non-mutating plan or dependency-solving command")

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
    "pkg -o REPO_AUTOUPDATE=false install -n -f",
    "pkg -o REPO_AUTOUPDATE=false install -y -f",
    "pkg info -q git",
    "pkg query '%R' git",
    'sha256 -q "$package"',
):
    need(marker in guest, "guest D lacks " + marker)
need("pkg install -y git" not in guest and "pkg add -M" not in guest,
     "guest D masked missing dependencies or bypassed pkg safety")
print("PASS: canonical owner route and fresh OPNsense missing-git installation regression")
