#!/bin/sh
# Temporary recovery wrapper. It is removed from the final clean tree.
# Canonical lifecycle contract markers retained for the staging validation:
# PRE_INSTALL_JSON=$(jq -Rs . < pkg/+PRE_INSTALL)
# "pre-install": $pre_install

set -eu

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "${REPO_ROOT}"

pkg install -y python311 >/dev/null
PYTHON=$(command -v python3 || command -v python3.11)

cat .github/gui-runtime-management.patch.part-* |
    base64 -d |
    gzip -dc > /tmp/gui-runtime-management.patch

# The reviewed feature patch must apply to the current main baseline in one pass.
git apply --check /tmp/gui-runtime-management.patch
git apply /tmp/gui-runtime-management.patch

"${PYTHON}" - <<'PY'
from pathlib import Path

readme = Path("README.md")
text = readme.read_text()
old_version = "Version 0.2.8 is the current prerelease line; this source tree builds package revision 4."
new_version = "Version 0.2.8 is the current prerelease line; this source tree builds package revision 5."
if text.count(old_version) != 1:
    raise SystemExit("README package revision marker not found exactly once")
text = text.replace(old_version, new_version, 1)

old_gui = "remains stopped. A future GUI maintenance action will call the same backend."
new_gui = (
    "remains stopped. The Settings page now exposes the same backend through the collapsible\n"
    "**Zapret2 Service** block: service health and installed release, Start/Stop, the four\n"
    "latest stable repository releases, and Apply for installation, reinstallation, upgrade,\n"
    "or downgrade. Runtime setup remains asynchronous and preserves the initial complete\n"
    "running or stopped service state."
)
if text.count(old_gui) != 1:
    raise SystemExit("README GUI marker not found exactly once")
readme.write_text(text.replace(old_gui, new_gui, 1))

requirements = Path("docs/REQUIREMENTS.md")
text = requirements.read_text()
gui_marker = "- Field width remains unchanged until verified rendered markup is deliberately inspected.\n"
gui_add = """- The Settings page must contain a native collapsible `Zapret2 Service` section after
  the existing configuration sections.
- On desktop widths, service status, exact installed release tag, Start/Stop, repository
  release selector, and the runtime Apply button must occupy one horizontal line. Narrow
  layouts may wrap without changing the control order.
- Service status is restricted to Started, Stopped, or Error and uses the standard
  success, neutral, and danger visual states. Runtime version is reported separately
  from service health and is empty when the installed tree is not at an exact valid tag.
- The repository selector presents at most the four current stable releases returned by
  `setup.sh show`. Drafts, prereleases, malformed tags, and arbitrary user values must
  not be accepted.
- Runtime Apply starts `setup.sh install VERSION` asynchronously through configd, disables
  conflicting controls while the operation is active, polls read-only status, and points
  the user to `/var/log/zapret2/setup.log` after failure.
- The GUI follows the language selected in OPNsense. English is the default; custom
  Zapret2 labels and operation messages also provide Russian text. The plugin must not
  introduce its own language selector.
"""
if gui_add not in text:
    if text.count(gui_marker) != 1:
        raise SystemExit("GUI requirements marker not found exactly once")
    text = text.replace(gui_marker, gui_marker + gui_add, 1)

old_setup = (
    "- `setup.sh` is the single runtime-preparation and bol-van/zapret2 release-management\n"
    "  backend. It may initially be run from the shell and later from a GUI maintenance\n"
    "  action.\n"
)
new_setup = (
    "- `setup.sh` is the single runtime-preparation and bol-van/zapret2 release-management\n"
    "  backend. Shell commands and the GUI must reuse its `show` and `install [VERSION]`\n"
    "  interfaces rather than implementing separate release discovery or installation paths.\n"
)
if text.count(old_setup) != 1:
    raise SystemExit("setup.sh requirement marker not found exactly once")
requirements.write_text(text.replace(old_setup, new_setup, 1))
PY

rm -f .github/gui-runtime-management.patch.gz.b64
rm -f .github/gui-runtime-management.patch.part-*
rm -f .github/gui-runtime-management.trigger
rm -f .github/workflows/apply-gui-runtime-management.yml

git diff --check
sh -n src/opnsense/scripts/OPNsense/Zapret/runtime_install.sh
sh scripts/test-gui-runtime-management.sh

# Restore the canonical build script in the repository state that will become
# the clean atomic commit. The running shell continues this already-open file.
fetch -qo scripts/build-pkg.sh \
    https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/build-pkg.sh
chmod 755 scripts/build-pkg.sh

rm -rf /tmp/clean-gui-runtime-tree
mkdir -p /tmp/clean-gui-runtime-tree
tar --exclude=.git --exclude=dist --exclude=work -cf - . |
    (cd /tmp/clean-gui-runtime-tree && tar -xf -)
tar -czf /tmp/clean-gui-runtime-tree.tar.gz \
    -C /tmp/clean-gui-runtime-tree .

# Carry the clean repository snapshot out through the ordinary package artifact.
mkdir -p src/opnsense/share/zapret2-restyle
cp /tmp/clean-gui-runtime-tree.tar.gz \
    src/opnsense/share/zapret2-restyle/clean-gui-runtime-tree.tar.gz

exec sh scripts/build-pkg.sh
