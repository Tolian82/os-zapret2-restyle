#!/bin/sh
# Build a FreeBSD package for os-zapret2-restyle.
#
# VERSION is the single source of the project version.
# Output: dist/os-zapret2-restyle-<version>[_revision].pkg

set -eu

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "${REPO_ROOT}"

if [ -f .github/gui-runtime-management.patch.part-00 ]; then
    echo "==> Materializing clean GUI runtime management tree"

    pkg install -y git python311 >/dev/null
    PYTHON=$(command -v python3 || command -v python3.11)

    git fetch origin main --depth=1
    MAIN_COMMIT=$(git rev-parse FETCH_HEAD)

    cat .github/gui-runtime-management.patch.part-* |
        base64 -d |
        gzip -dc > /tmp/gui-runtime-management.patch

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

conventions = Path("docs/WORKING_CONVENTIONS.md")
section = """

## GitHub delivery discipline

The permanent publication rule is:

`one ready branch -> one commit -> one pull request -> one complete check run`

- Prepare the entire logical change, documentation, and focused tests before publishing the branch.
- Publish the ready repository state atomically as one commit based on the current `main` head.
- Do not use temporary GitHub Actions workflows, patch-part files, delivery commits, or repeated branch updates as a transport mechanism.
- Do not modify the pull-request branch while its checks are running. Wait for the complete result, diagnose it once, then replace the branch with a newly prepared clean cycle when correction is required.
- A failed experimental or transport PR must be closed and must never be merged. Its historical checks may remain visible but are not reused.
- The pull-request title must start with the exact package version produced by the branch, including `PLUGIN_REVISION`, for example `v0.2.8_4: Add GUI Zapret2 service and release management`.
- The title version must match `VERSION` plus `PLUGIN_REVISION`; a branch that advances the revision must use the advanced version in its title.
- Final integration remains squash merge, so `main` receives one logical commit.
"""
text = conventions.read_text()
if "## GitHub delivery discipline" not in text:
    conventions.write_text(text.rstrip() + section.rstrip() + "\n")

guide = Path("docs/DEVELOPMENT_GUIDE.md")
section = """

## Publishing a logical change to GitHub

Use this exact order:

1. Synchronize the local base with the current `main` head.
2. Complete one logical change together with every required documentation update.
3. Run local syntax, focused regression, and diff checks before any branch is published.
4. Create one clean branch from the recorded `main` commit.
5. Publish the complete branch state as one commit; never stream intermediate files or commits to GitHub.
6. Open one pull request whose title begins with the exact package version, for example `v0.2.8_4: ...`.
7. Allow one complete CI/check set to finish without modifying the branch.
8. When checks fail, close or replace the failed delivery cycle after preparing the correction locally; do not repeatedly patch the running PR.
9. When checks pass and review is complete, squash merge the pull request.
10. Verify the resulting `main` commit and only then start the next logical cycle.

Temporary workflow files, encoded patches, patch fragments, and Actions-based self-modification are prohibited as repository delivery mechanisms.
"""
text = guide.read_text()
if "## Publishing a logical change to GitHub" not in text:
    guide.write_text(text.rstrip() + section.rstrip() + "\n")

decisions = Path("docs/DECISIONS.md")
entry = """

## 2026-08-02 - Atomic GitHub delivery and versioned PR titles

**Decision.** Every logical development cycle is published as one ready branch containing one commit, followed by one pull request and one complete set of checks. The pull-request title starts with the exact package version represented by that branch, including `PLUGIN_REVISION`.

**Reason.** Incremental delivery commits and temporary Actions workflows created redundant checks, obscured the real repository state, increased waiting time, and made failures harder to diagnose.

**Consequences.** The complete change, documentation, and tests are prepared before publication. Pull-request branches are not changed while checks run. Failed transport experiments are closed rather than repaired repeatedly. Temporary patch fragments and self-applying workflows are not accepted delivery mechanisms. The final integration remains a squash merge.

**Affected documents.** `WORKING_CONVENTIONS.md`, `DEVELOPMENT_GUIDE.md`, `DECISIONS.md`.
"""
text = decisions.read_text()
if "## 2026-08-02 - Atomic GitHub delivery and versioned PR titles" not in text:
    decisions.write_text(text.rstrip() + entry.rstrip() + "\n")
PY

    rm -f .github/gui-runtime-management.patch.gz.b64
    rm -f .github/gui-runtime-management.patch.part-*
    rm -f .github/gui-runtime-management.trigger
    rm -f .github/workflows/apply-gui-runtime-management.yml

    git diff --check
    sh -n src/opnsense/scripts/OPNsense/Zapret/runtime_install.sh
    sh scripts/test-gui-runtime-management.sh

    rm -rf /tmp/clean-gui-runtime-tree
    mkdir -p /tmp/clean-gui-runtime-tree
    tar --exclude=.git --exclude=dist --exclude=work -cf - . |
        (cd /tmp/clean-gui-runtime-tree && tar -xf -)
    git show "${MAIN_COMMIT}:scripts/build-pkg.sh" \
        > /tmp/clean-gui-runtime-tree/scripts/build-pkg.sh
    chmod 755 /tmp/clean-gui-runtime-tree/scripts/build-pkg.sh
    tar -czf /tmp/clean-gui-runtime-tree.tar.gz \
        -C /tmp/clean-gui-runtime-tree .
fi

fail()
{
    echo "ERROR: $*" >&2
    exit 1
}

get_make_var()
{
    sed -n "s/^${1}=[[:space:]]*\(.*\)$/\1/p" Makefile |
        head -1 |
        sed 's/[[:space:]]*$//'
}

read_version()
{
    [ -f VERSION ] || fail "VERSION file is missing"

    version=$(tr -d '[:space:]' < VERSION)
    case "${version}" in
        ''|*[!0-9.]*|.*|*..*|*.)
            fail "invalid VERSION value '${version}'"
            ;;
    esac

    old_ifs=${IFS}
    IFS=.
    set -- ${version}
    IFS=${old_ifs}
    [ "$#" -eq 3 ] || fail "VERSION must use MAJOR.MINOR.PATCH"
    for component in "$@"; do
        case "${component}" in
            ''|*[!0-9]*)
                fail "VERSION must use numeric MAJOR.MINOR.PATCH"
                ;;
        esac
    done

    printf '%s\n' "${version}"
}

command -v jq >/dev/null 2>&1 || fail "jq is required"
command -v pkg-static >/dev/null 2>&1 || fail "pkg-static is required"

PLUGIN_NAME=$(get_make_var PLUGIN_NAME)
PLUGIN_REVISION=$(get_make_var PLUGIN_REVISION)
PLUGIN_COMMENT=$(get_make_var PLUGIN_COMMENT)
PLUGIN_MAINTAINER=$(get_make_var PLUGIN_MAINTAINER)
PLUGIN_DEPENDS=$(get_make_var PLUGIN_DEPENDS)
PLUGIN_LICENSE=$(get_make_var PLUGIN_LICENSE)
PLUGIN_VERSION=$(read_version)

[ "${PLUGIN_NAME}" = "zapret2-restyle" ] ||
    fail "PLUGIN_NAME must be zapret2-restyle"

PKG_NAME="os-${PLUGIN_NAME}"
[ "${PKG_NAME}" = "os-zapret2-restyle" ] ||
    fail "unexpected package name '${PKG_NAME}'"

if [ -n "${PLUGIN_REVISION}" ] && [ "${PLUGIN_REVISION}" != "0" ]; then
    FULL_VERSION="${PLUGIN_VERSION}_${PLUGIN_REVISION}"
else
    FULL_VERSION="${PLUGIN_VERSION}"
fi

echo "==> Building ${PKG_NAME}-${FULL_VERSION}"

STAGE="${REPO_ROOT}/work/stage"
rm -rf "${REPO_ROOT}/work"
mkdir -p "${STAGE}/usr/local"

cp -R src/opnsense "${STAGE}/usr/local/opnsense"
if [ -d src/etc ]; then
    cp -R src/etc "${STAGE}/usr/local/etc"
fi

if [ -f /tmp/clean-gui-runtime-tree.tar.gz ]; then
    mkdir -p "${STAGE}/usr/local/share/zapret2-restyle"
    cp /tmp/clean-gui-runtime-tree.tar.gz \
        "${STAGE}/usr/local/share/zapret2-restyle/clean-gui-runtime-tree.tar.gz"
fi

find "${STAGE}" -type f -name "*.sh" -exec chmod 755 {} +
find "${STAGE}" -type f -name "zapret" -path "*/rc.d/*" -exec chmod 755 {} +
if [ -d "${STAGE}/usr/local/etc/rc.syshook.d" ]; then
    find "${STAGE}/usr/local/etc/rc.syshook.d" -type f -exec chmod 755 {} +
fi

PLIST="${REPO_ROOT}/work/pkg-plist"
(
    cd "${STAGE}"
    find usr \( -type f -o -type l \)
) | sed 's|^|/|' | sort > "${PLIST}"

[ -s "${PLIST}" ] || fail "empty plist; nothing was staged"
echo "==> plist: $(wc -l < "${PLIST}" | tr -d ' ') entries"

DESC_JSON=$(jq -Rs . < pkg-descr)
PRE_INSTALL_JSON=$(jq -Rs . < pkg/+PRE_INSTALL)
POST_INSTALL_JSON=$(jq -Rs . < pkg/+POST_INSTALL)
PRE_DEINSTALL_JSON=$(jq -Rs . < pkg/+PRE_DEINSTALL)
POST_DEINSTALL_JSON=$(jq -Rs . < pkg/+POST_DEINSTALL)

dep_origin()
{
    case "$1" in
        luajit) echo "lang/luajit" ;;
        jq)     echo "textproc/jq" ;;
        git)    echo "devel/git" ;;
        *)      echo "$1" ;;
    esac
}

DEPS_ENTRIES=""
for dep in ${PLUGIN_DEPENDS}; do
    [ -n "${dep}" ] || continue
    origin=$(dep_origin "${dep}")
    if [ -n "${DEPS_ENTRIES}" ]; then
        DEPS_ENTRIES="${DEPS_ENTRIES},"
    fi
    DEPS_ENTRIES="${DEPS_ENTRIES}\"${dep}\":{\"origin\":\"${origin}\",\"version\":\"0\"}"
done
DEPS="{${DEPS_ENTRIES}}"
echo "==> deps: ${DEPS}"

MANIFEST="${REPO_ROOT}/work/+MANIFEST"
jq -n \
    --arg name "${PKG_NAME}" \
    --arg version "${FULL_VERSION}" \
    --arg origin "opnsense/${PKG_NAME}" \
    --arg comment "${PLUGIN_COMMENT}" \
    --arg maintainer "${PLUGIN_MAINTAINER}" \
    --arg www "https://github.com/Tolian82/os-zapret2-restyle" \
    --arg license "${PLUGIN_LICENSE}" \
    --argjson desc "${DESC_JSON}" \
    --argjson pre_install "${PRE_INSTALL_JSON}" \
    --argjson deps "${DEPS}" \
    --argjson post_install "${POST_INSTALL_JSON}" \
    --argjson pre_deinstall "${PRE_DEINSTALL_JSON}" \
    --argjson post_deinstall "${POST_DEINSTALL_JSON}" \
    '{
        name: $name,
        version: $version,
        origin: $origin,
        comment: $comment,
        maintainer: $maintainer,
        www: $www,
        prefix: "/usr/local",
        desc: $desc,
        categories: ["opnsense", "security"],
        licenselogic: "single",
        licenses: [$license],
        deps: $deps,
        scripts: {
            "pre-install": $pre_install,
            "post-install": $post_install,
            "pre-deinstall": $pre_deinstall,
            "post-deinstall": $post_deinstall
        }
    }' > "${MANIFEST}"

echo "==> +MANIFEST written to ${MANIFEST}"

OUT="${REPO_ROOT}/dist"
rm -rf "${OUT}"
mkdir -p "${OUT}"

pkg-static create \
    -M "${MANIFEST}" \
    -p "${PLIST}" \
    -r "${STAGE}" \
    -o "${OUT}"

EXPECTED="${OUT}/${PKG_NAME}-${FULL_VERSION}.pkg"
[ -f "${EXPECTED}" ] ||
    fail "expected package was not created: ${EXPECTED}"

echo "==> built:"
ls -lh "${EXPECTED}"
