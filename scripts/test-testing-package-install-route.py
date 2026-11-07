#!/usr/bin/env python3
"""Fast non-root smoke for SHA-bound testing installer; no OPNsense mutation."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def need(value, label):
    if not value:
        raise SystemExit("FAIL: installer regression: " + label)


make = (ROOT / "Makefile").read_text()
need("python${PLUGIN_PYTHON} gmake pkgconf luajit git jq ca_root_nss" in make,
     "real native deps were dropped")
template = (ROOT / "scripts/install-testing-package.sh.in").read_text()
need(template.count("@PACKAGE_VERSION@") == 1 and
     template.count("@PACKAGE_SHA256@") == 1, "template placeholders")
need("pkg install -r OPNsense $MISSING" in template and
     'pkg add -f "$PKG"' in template and
     "pkg add -M" not in template and "pfctl" not in template,
     "must use official dependency solver then normal pkg add")
workflow = (ROOT / ".github/workflows/publish-prerelease.yml").read_text()
for value in ("Generate exact-SHA native installer",
              'gh release create "${TAG}" "dist/${ASSET}" "dist/${INSTALLER}"',
              "PUBLISHED_INSTALLER_CHANGED", "--arg installer"):
    need(value in workflow, "publisher missing: " + value)
chat = (ROOT / "docs/CHAT_RULES.md").read_text().split("CHAT-027.", 1)[1]
need("sh /root/install-os-zapret2-restyle-<actual-version>.sh" in chat,
     "owner instruction still requires manual dependency list")
gh = (ROOT / "docs/GITHUB_PUBLICATION.md").read_text().split("GH-060.", 1)[1]
need("companion SHA-pinned" in gh, "GH-060 not updated")
need("## Installing a testing package without manually managing dependencies"
     in (ROOT / "README.md").read_text(), "README not reconciled")

digest = "a" * 64
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    installer = root / "installer.sh"
    installer.write_text(template.replace("@PACKAGE_VERSION@", "0.6.2_185")
                         .replace("@PACKAGE_SHA256@", digest))
    subprocess.run(["sh", "-n", str(installer)], check=True)
    bins = root / "bin"
    bins.mkdir()
    mocks = {
        "opnsense-version": "#!/bin/sh\necho 26.7\n",
        "pkg": """#!/bin/sh
printf 'pkg %s\n' "$*" >> "$MOCK_TRACE"
case "$1" in
 config) echo FreeBSD:15:amd64 ;;
 query)
    [ "$3" = os-zapret2-restyle ] && { echo 0.6.2_185; exit 0; }
    case " ${MOCK_PRESENT:-} " in
       *" $3 "*) case " ${MOCK_OLD:-} " in
                    *" $3 "*) echo 0.5 ;;
                    *) echo 1.0 ;;
                   esac ;;
       *) exit 1 ;;
    esac ;;
 version) [ "$2" = -t ] || exit 2
          [ "$3" = 0.5 ] && echo '<' || echo '=' ;;
 install) [ "${MOCK_DEP_FAIL:-0}" != 1 ] ;;
 add) exit 0 ;;
 check) exit 0 ;;
 *) exit 2 ;;
esac
""",
        "fetch": """#!/bin/sh
while [ "$#" -gt 0 ]; do
 case "$1" in -o) p=$2; shift 2 ;; *) shift ;; esac
done
printf bytes > "$p"
""",
        "sha256": "#!/bin/sh\necho " + digest + "\n",
        "tar": "#!/bin/sh\necho '{}'\n",
        "php": """#!/bin/sh
case "$2" in
 *PHP_EOL*) printf 'git 1.0\njq 1.0\npython313 1.0\n' ;;
 *) echo 'git jq python313' ;;
esac
""",
    }
    for name, source in mocks.items():
        path = bins / name
        path.write_text(source)
        path.chmod(0o755)
    trace = root / "trace"
    scenarios = (
        # All installed: no pkg install, no auto/manual changes.
        ("all-satisfied", "git jq python313", "", "0", None),
        # Only missing dependency must reach official repo.
        ("one-missing", "git jq", "", "0", "python313"),
        # Only outdated dependency and missing dependency need resolution.
        ("outdated", "git jq", "jq", "0", "jq python313"),
        # Refusal is before pkg add.
        ("dependency-failure", "git jq", "", "1", "python313"),
    )
    for label, present, old, failure, expected in scenarios:
        trace.write_text("")
        env = dict(os.environ, PATH=str(bins) + ":" + os.environ["PATH"],
                   MOCK_TRACE=str(trace), MOCK_DEP_FAIL=failure,
                   MOCK_PRESENT=present, MOCK_OLD=old)
        run = subprocess.run(["sh", str(installer)], capture_output=True,
                             text=True, env=env)
        record = trace.read_text()
        need((run.returncode == 0) == (failure == "0"),
             label + ": expected result")
        expected_install = ("pkg install -r OPNsense " + expected) if expected else None
        need((expected_install in record) if expected_install else
             ("pkg install " not in record),
             label + ": wrong dependency transaction")
        need(("pkg add -f" in record) == (failure == "0"),
             label + ": pkg add/abort order")
        need("pkg set " not in record, label + ": automatic flag mutated")
print("PASS: native OPNsense installer preserves automatic dependencies and fails closed")
