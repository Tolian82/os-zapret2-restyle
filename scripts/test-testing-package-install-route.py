#!/usr/bin/env python3
"""Fast source contract: immutable GitHub testing delivery is .pkg ONLY."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def need(ok, text):
    if not ok:
        raise SystemExit("FAIL: pkg-only testing delivery: " + text)

make = (ROOT / "Makefile").read_text()
publisher = (ROOT / ".github/workflows/publish-prerelease.yml").read_text()
stage5 = (ROOT / ".github/workflows/stage5-native-cross-clean-running.yml").read_text()
chat = (ROOT / "docs/CHAT_RULES.md").read_text().split("CHAT-027.", 1)[1].split("## Cross-reference",1)[0]
gh = (ROOT / "docs/GITHUB_PUBLICATION.md").read_text().split("GH-060.",1)[1].split("GH-061.",1)[0]
spec = (ROOT / "docs/architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md").read_text()
readme = (ROOT / "README.md").read_text()

need("python${PLUGIN_PYTHON} gmake pkgconf luajit git jq ca_root_nss" in make,
     "native package dependencies were dropped")
need(not (ROOT / "scripts/install-testing-package.sh.in").exists(),
     "legacy companion installer template is still active")
for token in ('echo "asset=os-zapret2-restyle-${PACKAGE_VERSION}.pkg"',
              'gh release create "${TAG}" "dist/${ASSET}"',
              "Verify package manifest and digest",
              '.abi == "FreeBSD:15:amd64"',
              'publication-record/${TAG}',
              '- direct package asset: [${ASSET}](${ASSET_URL})'):
    need(token in publisher, "publisher lacks " + token)
for token in ("INSTALLER", 'dist/${INSTALLER}', "install-testing-package.sh.in",
              ".sh installer", "installer asset", "Generate exact-SHA native installer"):
    need(token not in publisher, "publisher still creates an installer: " + token)
need('pkg install -y -r OPNsense $dependencies' in stage5 and
     'pkg add -f "$package"' in stage5 and
     'm["deps"]' in stage5 and
     "scripts/install-testing-package.sh.in" not in stage5,
     "Guest D must install physical .pkg after official manifest dependencies")
for value in ("fetch -o /root/os-zapret2-restyle-<actual-version>.pkg",
              "pkg add -f /root/os-zapret2-restyle-<actual-version>.pkg",
              "pkg info -x os-zapret2-restyle"):
    need(value in chat, "CHAT-027 missing pkg command " + value)
for name, body in (("CHAT-027",chat),("GH-060",gh)):
    need("shell" in body.lower() or "SH-установщик" in body,
         name + " must prohibit shell installer delivery")
    need("pkg add -f" in body, name + " must use native pkg add")
    need("sh /root/install-" not in body and "fetch → sh" not in body,
         name + " still requires shell installation")
need("pkg add -f" in spec and "pkg add -f" in readme,
     "spec/README missing native pkg add route")
print("PASS: testing publisher delivers only .pkg, official dependencies and pkg add -f")
