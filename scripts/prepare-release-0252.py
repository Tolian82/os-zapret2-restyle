#!/usr/bin/env python3

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"Expected text not found in {path}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def append_once(path: str, marker: str, section: str) -> None:
    text = read(path)
    if marker in text:
        return
    write(path, text.rstrip() + "\n\n" + section.strip() + "\n")


post_install = dedent(r'''\
#!/bin/sh

# Register the plugin, refresh OPNsense integration, and render its initial
# template. Runtime preparation is intentionally separate from the pkg
# transaction. During an upgrade, restore a service that the replacement
# pre-install hook stopped successfully.

SERVICE_SCRIPT="/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
CONFIGCTL="/usr/local/sbin/configctl"
REGISTER_SCRIPT="/usr/local/opnsense/scripts/firmware/register.php"
CONFIGURE_PLUGINS="/usr/local/etc/rc.configure_plugins"
UPGRADE_RESTART_MARKER="/var/run/zapret2-restyle/pkg-upgrade.restart"

if [ ! -x "${REGISTER_SCRIPT}" ]; then
    echo "ERROR: OPNsense plugin registration helper is unavailable" >&2
    exit 1
fi

if ! "${REGISTER_SCRIPT}" install os-zapret2-restyle >/dev/null 2>&1; then
    echo "ERROR: os-zapret2-restyle could not be registered in OPNsense" >&2
    exit 1
fi

if [ -x "${CONFIGURE_PLUGINS}" ]; then
    if ! "${CONFIGURE_PLUGINS}" POST_INSTALL >/dev/null 2>&1; then
        echo "ERROR: OPNsense post-install plugin refresh failed" >&2
        exit 1
    fi
fi

if [ -x /usr/local/sbin/configctl ]; then
    /usr/local/sbin/configctl template reload OPNsense/Zapret >/dev/null 2>&1 || true
fi

if [ -n "${PKG_UPGRADE:-}" ] && [ -f "${UPGRADE_RESTART_MARKER}" ]; then
    [ -x "${CONFIGCTL}" ] && [ -x "${SERVICE_SCRIPT}" ] || {
        echo "ERROR: zapret service control is unavailable after package upgrade" >&2
        exit 1
    }

    service_output=$("${CONFIGCTL}" zapret start 2>&1)
    service_result=$?
    if [ "${service_result}" -ne 0 ] || [ "${service_output}" != "OK" ]; then
        printf '%s\n' "${service_output}" >&2
        echo "ERROR: zapret service could not be started after package upgrade" >&2
        exit 1
    fi

    if ! "${SERVICE_SCRIPT}" status >/dev/null 2>&1; then
        echo "ERROR: zapret service did not reach running state after package upgrade" >&2
        exit 1
    fi

    rm -f "${UPGRADE_RESTART_MARKER}"
fi

cat <<'MESSAGE'

os-zapret2-restyle was installed.

To install the zapret2 runtime, run:

/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install

MESSAGE

exit 0
''')
write("pkg/+POST_INSTALL", post_install)

release_trigger = dedent(r'''\
name: Release trigger

on:
  push:
    branches: [main]

permissions:
  actions: write
  contents: write

concurrency:
  group: release-trigger-${{ github.sha }}
  cancel-in-progress: false

jobs:
  trigger:
    name: Create verified release tag
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Validate release merge
        id: release
        shell: bash
        run: |
          set -euo pipefail

          VERSION_VALUE=$(tr -d '[:space:]' < VERSION)
          REVISION=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' Makefile | head -1)
          SUBJECT=$(git log -1 --pretty=%s)
          ESCAPED_VERSION=${VERSION_VALUE//./\\.}

          [[ "${VERSION_VALUE}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
          [[ "${REVISION}" =~ ^[1-9][0-9]*$ ]]
          grep -Eq '^PLUGIN_NAME=[[:space:]]+zapret2-restyle$' Makefile
          grep -Eq '^PLUGIN_VERSION!=[[:space:]]+/bin/cat \$\{\.CURDIR\}/VERSION$' Makefile

          RELEASE=false
          TAG=

          if [[ "${SUBJECT}" =~ ^release:\ prepare\ v${ESCAPED_VERSION}(\ \(#[0-9]+\))?$ ]]; then
            RELEASE=true
            TAG="v${VERSION_VALUE}"
          elif [[ "${SUBJECT}" =~ ^release:\ prepare\ v${ESCAPED_VERSION}_${REVISION}(\ \(#[0-9]+\))?$ ]]; then
            RELEASE=true
            TAG="v${VERSION_VALUE}_${REVISION}"
          fi

          echo "release=${RELEASE}" >> "${GITHUB_OUTPUT}"
          if [ "${RELEASE}" = true ]; then
            echo "tag=${TAG}" >> "${GITHUB_OUTPUT}"
          else
            echo "No release preparation subject detected; nothing to publish."
          fi

      - name: Create immutable tag
        if: steps.release.outputs.release == 'true'
        shell: bash
        env:
          TAG: ${{ steps.release.outputs.tag }}
        run: |
          set -euo pipefail

          git fetch --force --tags origin

          if git show-ref --verify --quiet "refs/tags/${TAG}"; then
            TAG_COMMIT=$(git rev-list -n 1 "refs/tags/${TAG}")
            [ "${TAG_COMMIT}" = "${GITHUB_SHA}" ] || {
              echo "Tag ${TAG} already points to ${TAG_COMMIT}, expected ${GITHUB_SHA}" >&2
              exit 1
            }
          else
            git config user.name github-actions[bot]
            git config user.email 41898282+github-actions[bot]@users.noreply.github.com
            git tag -a "${TAG}" "${GITHUB_SHA}" -m "os-zapret2-restyle ${TAG}"
            git push origin "refs/tags/${TAG}"
          fi

      - name: Dispatch release workflow
        if: steps.release.outputs.release == 'true'
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.release.outputs.tag }}
        run: |
          set -euo pipefail

          if gh release view "${TAG}" >/dev/null 2>&1; then
            echo "Release ${TAG} is already published."
            exit 0
          fi

          if gh run list \
            --workflow release.yml \
            --branch "${TAG}" \
            --json status \
            --limit 20 \
            --jq 'any(.[]; .status == "queued" or .status == "in_progress")' \
            | grep -qx true
          then
            echo "Release workflow for ${TAG} is already active."
            exit 0
          fi

          gh workflow run release.yml --ref "${TAG}"
''')
write(".github/workflows/release-trigger.yml", release_trigger)

release_workflow = dedent(r'''\
name: Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  validate:
    name: Validate release
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Validate tag and package metadata
        shell: bash
        run: |
          set -euo pipefail

          TAG_VALUE="${GITHUB_REF_NAME#v}"
          VERSION_VALUE=$(tr -d '[:space:]' < VERSION)
          REVISION=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' Makefile | head -1)

          [[ "${VERSION_VALUE}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
          [[ "${REVISION}" =~ ^[1-9][0-9]*$ ]]

          if [[ "${TAG_VALUE}" =~ ^([0-9]+\.[0-9]+\.[0-9]+)_([1-9][0-9]*)$ ]]; then
            [ "${BASH_REMATCH[1]}" = "${VERSION_VALUE}" ]
            [ "${BASH_REMATCH[2]}" = "${REVISION}" ]
          else
            [[ "${TAG_VALUE}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
            [ "${TAG_VALUE}" = "${VERSION_VALUE}" ]
          fi

          grep -Eq '^PLUGIN_NAME=[[:space:]]+zapret2-restyle$' Makefile
          grep -Eq '^PLUGIN_VERSION!=[[:space:]]+/bin/cat \$\{\.CURDIR\}/VERSION$' Makefile

      - name: Install validation tools
        run: sudo apt-get update && sudo apt-get install -y libxml2-utils

      - name: Validate project files
        shell: bash
        run: |
          set -euo pipefail
          find src -type f -name '*.xml' -exec xmllint --noout {} \;
          find src -type f -name '*.sh' -exec sh -n {} \;
          find pkg -type f -exec sh -n {} \;
          find scripts -type f -name '*.sh' -exec sh -n {} \;
          docker run --rm -v "${PWD}":/app -w /app php:8.2-cli sh -c '
            set -e
            find src -type f -name "*.php" -exec php -l {} \;
            find src -type f -name "*.inc" -exec php -l {} \;
          '

  build:
    name: Build package and repository
    runs-on: ubuntu-latest
    needs: validate

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Read release metadata
        id: release
        shell: bash
        run: |
          set -euo pipefail
          VERSION_VALUE=$(tr -d '[:space:]' < VERSION)
          REVISION=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' Makefile | head -1)
          if [[ -n "${REVISION}" && "${REVISION}" != "0" ]]; then
            PACKAGE_VERSION="${VERSION_VALUE}_${REVISION}"
          else
            PACKAGE_VERSION="${VERSION_VALUE}"
          fi
          echo "version=${VERSION_VALUE}" >> "${GITHUB_OUTPUT}"
          echo "asset=os-zapret2-restyle-${PACKAGE_VERSION}.pkg" >> "${GITHUB_OUTPUT}"

      - name: Build package and pkg repository inside FreeBSD VM
        uses: vmactions/freebsd-vm@v1
        with:
          release: '15.0'
          usesh: true
          prepare: pkg install -y jq
          run: |
            sh scripts/build-pkg.sh
            sh scripts/verify-release-package.sh
            sh scripts/build-pkg-repository.sh

      - name: Verify release outputs
        shell: bash
        run: |
          set -euo pipefail
          test -f "dist/${{ steps.release.outputs.asset }}"
          test -f "pages/FreeBSD:15:amd64/${{ steps.release.outputs.asset }}"
          test -f "pages/FreeBSD:15:amd64/meta.conf"
          test -f "pages/FreeBSD:15:amd64/data.pkg"
          test -f "pages/FreeBSD:15:amd64/packagesite.pkg"
          test -f "pages/FreeBSD:15:amd64/SHA256SUMS"
          test -f "pages/zapret2-restyle.conf"

      - name: Stage release assets
        shell: bash
        run: |
          set -euo pipefail
          rm -rf release-assets
          mkdir -p release-assets
          cp "dist/${{ steps.release.outputs.asset }}" release-assets/
          cp "pages/FreeBSD:15:amd64/SHA256SUMS" release-assets/

      - name: Upload release build
        uses: actions/upload-artifact@v7
        with:
          name: release-build
          path: release-assets
          if-no-files-found: error

      - name: Upload GitHub Pages artifact
        uses: actions/upload-pages-artifact@v4
        with:
          path: pages

  publish-release:
    name: Publish GitHub Release
    runs-on: ubuntu-latest
    needs: build

    steps:
      - uses: actions/download-artifact@v8
        with:
          name: release-build
          path: release-build

      - name: Create GitHub release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            release-build/*.pkg
            release-build/SHA256SUMS
          draft: false
          prerelease: true
          generate_release_notes: true

  deploy-pages:
    name: Publish pkg repository
    runs-on: ubuntu-latest
    needs: build
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Deploy GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
''')
write(".github/workflows/release.yml", release_workflow)

release_test = dedent(r'''\
#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TRIGGER_WORKFLOW="${ROOT_DIR}/.github/workflows/release-trigger.yml"
RELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/release.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

test -f "${TRIGGER_WORKFLOW}" || fail "release trigger workflow is missing"
test -f "${RELEASE_WORKFLOW}" || fail "release workflow is missing"

grep -Fq 'branches: [main]' "${TRIGGER_WORKFLOW}" || fail "trigger is not limited to main"
if grep -Fq 'paths:' "${TRIGGER_WORKFLOW}"; then
    fail "trigger still excludes package-revision release subjects"
fi
grep -Fq 'actions: write' "${TRIGGER_WORKFLOW}" || fail "actions write permission is missing"
grep -Fq 'contents: write' "${TRIGGER_WORKFLOW}" || fail "contents write permission is missing"
grep -Fq 'TAG="v${VERSION_VALUE}"' "${TRIGGER_WORKFLOW}" || fail "version release tag is missing"
grep -Fq 'TAG="v${VERSION_VALUE}_${REVISION}"' "${TRIGGER_WORKFLOW}" || fail "package revision release tag is missing"
grep -Fq 'release=${RELEASE}' "${TRIGGER_WORKFLOW}" || fail "non-release no-op contract is missing"
grep -Fq "if: steps.release.outputs.release == 'true'" "${TRIGGER_WORKFLOW}" || fail "release steps are not gated"
grep -Fq 'git rev-list -n 1 "refs/tags/${TAG}"' "${TRIGGER_WORKFLOW}" || fail "existing tag target is not verified"
grep -Fq 'git tag -a "${TAG}" "${GITHUB_SHA}"' "${TRIGGER_WORKFLOW}" || fail "annotated tag creation is missing"
grep -Fq 'gh release view "${TAG}"' "${TRIGGER_WORKFLOW}" || fail "published release idempotence check is missing"
grep -Fq 'gh workflow run release.yml --ref "${TAG}"' "${TRIGGER_WORKFLOW}" || fail "release dispatch is missing"
grep -Fq 'workflow_dispatch:' "${RELEASE_WORKFLOW}" || fail "release workflow cannot be dispatched"
grep -Fq 'BASH_REMATCH[2]' "${RELEASE_WORKFLOW}" || fail "package revision tag validation is missing"
grep -Fq 'actions/checkout@v6' "${RELEASE_WORKFLOW}" || fail "release checkout is not on the supported runtime major"

echo "Release trigger contract tests passed."
''')
write("scripts/test-release-trigger.sh", release_test)

replace_once(
    "scripts/test-package-lifecycle-restart.sh",
    '''grep -q '"${SERVICE_SCRIPT}" status' "${POST_HOOK}" ||
    fail "post-install does not verify replacement service state"
''',
    '''grep -q '"${SERVICE_SCRIPT}" status' "${POST_HOOK}" ||
    fail "post-install does not verify replacement service state"
grep -q 'REGISTER_SCRIPT="/usr/local/opnsense/scripts/firmware/register.php"' "${POST_HOOK}" ||
    fail "post-install does not use the OPNsense plugin registration helper"
grep -q '"${REGISTER_SCRIPT}" install os-zapret2-restyle' "${POST_HOOK}" ||
    fail "post-install does not register the installed plugin"
grep -q '"${CONFIGURE_PLUGINS}" POST_INSTALL' "${POST_HOOK}" ||
    fail "post-install does not use the OPNsense POST_INSTALL lifecycle mode"
if grep -q 'rc.configure_plugins zapret2' "${POST_HOOK}"; then
    fail "post-install still passes the plugin name as a lifecycle mode"
fi
'''
)

replace_once(
    "README.md",
    "Version 0.2.5 is the current prerelease line; this source tree builds package revision 2.",
    "Version 0.2.5 is the current prerelease line; package revision 2 fixes OPNsense plugin registration during direct pkg installation and refreshes integration through the proper POST_INSTALL lifecycle mode."
)
replace_once(
    "README.md",
    "Normal plugin installation and updates are performed through the OPNsense Firmware GUI.\nThe package installation itself remains quick and does not download or compile the\nzapret2 runtime.",
    "Normal plugin installation and updates are performed through the OPNsense Firmware GUI.\nDirect `pkg add` installation is also registered in OPNsense by the package hook, so\nFirmware no longer lists an installed package as `(misconfigured)`. The package hook\nthen refreshes plugin integration using the OPNsense `POST_INSTALL` lifecycle mode.\nThe package installation itself remains quick and does not download or compile the\nzapret2 runtime."
)

replace_once(
    "docs/CHANGELOG.md",
    "### Fixed\n\n- Made `setup.sh install` preserve",
    "### Fixed\n\n- Registered `os-zapret2-restyle` explicitly from `+POST_INSTALL`, preventing direct\n  `pkg add` installation from appearing as `(misconfigured)` in Firmware > Plugins.\n- Passed the correct `POST_INSTALL` lifecycle mode to `rc.configure_plugins` instead\n  of incorrectly passing the internal plugin name.\n- Added package-revision release tags so an unpublished corrected package revision can\n  be published immutably as `vX.Y.Z_R` without moving an existing SemVer tag.\n- Made `setup.sh install` preserve"
)

replace_once(
    "docs/PROJECT_STATE.md",
    "Current phase:\nLIFE-014 stopped-service setup correction implemented for package revision 2\n\nCurrent priority:\nPublish and build the package-revision-2 correction, then repeat setup.sh install\nwith both running and stopped service states before completing the CFG-001 reboot matrix.",
    "Current phase:\nPKG-009 post-install registration correction prepared for package 0.2.5_2\n\nCurrent priority:\nPublish immutable package revision release v0.2.5_2 with correct OPNsense registration,\nthen advance immediately to release v0.2.6 with package revision reset to 1."
)
replace_once(
    "docs/PROJECT_STATE.md",
    "Known blockers:\nPackage 0.2.5_1 preserves service state across pkg upgrade, but live verification\nfound that setup.sh install unconditionally restarts a service that was stopped before\nruntime installation. Package revision 2 captures the initial complete service state,\nrestarts and verifies only a previously running service, and verifies that a stopped\nservice remains stopped. CI/package build and focused OPNsense verification remain.",
    "Known blockers:\nDirect `pkg add` installs the package files but bypasses OPNsense firmware/install.sh,\nso the current +POST_INSTALL must register `os-zapret2-restyle` explicitly. Its current\n`rc.configure_plugins zapret2` call also supplies an invalid lifecycle mode. Package\n0.2.5_2 corrects both paths and retains the LIFE-014 stopped-service setup correction."
)
append_once(
    "docs/PROJECT_STATE.md",
    "CURRENT CORRECTIVE WORK — PKG-009",
    dedent(r'''\
==================================================
CURRENT CORRECTIVE WORK — PKG-009 — 2026-08-01
==================================================

Direct installation of package 0.2.5_1 through `pkg add` left the package present but
absent from `<system><firmware><plugins>`, so Firmware > Plugins displayed
`os-zapret2-restyle (misconfigured)`. OPNsense's normal firmware installer performs
package installation and then calls `register.php install`; direct pkg installation
does not execute that outer installer.

The package hook now invokes the idempotent OPNsense registration helper explicitly,
then calls `rc.configure_plugins POST_INSTALL`. The previous argument `zapret2` was not
a plugin identifier to that script; it was interpreted as an unknown lifecycle mode.
Focused static coverage rejects the old call and requires registration plus the exact
POST_INSTALL mode.

The correction is prepared for immutable package-revision release `v0.2.5_2`. Package
revision tags use `vX.Y.Z_R` and are validated against both VERSION and
PLUGIN_REVISION; existing release tags are never moved.
''')
)

append_once(
    "docs/AUDIT.md",
    "PKG-009 — DIRECT PKG INSTALLATION LEAVES THE PLUGIN MISCONFIGURED",
    dedent(r'''\
==================================================
PKG-009 — DIRECT PKG INSTALLATION LEAVES THE PLUGIN MISCONFIGURED
==================================================

Classification:
broken / remediated in source / package verification required

Affected locations:

- pkg/+POST_INSTALL
- scripts/test-package-lifecycle-restart.sh
- OPNsense `/usr/local/opnsense/scripts/firmware/register.php`
- OPNsense `/usr/local/etc/rc.configure_plugins`

Affected chain:

direct `pkg add`
        ↓
package +POST_INSTALL
        ↓
plugin files exist but firmware plugin registration is absent
        ↓
Firmware > Plugins reports installed=1, configured=0, `(misconfigured)`

Evidence:

- `pkg info os-zapret2-restyle` reported installed package 0.2.5_1 from
  Zapret2Restyle.
- Firmware > Plugins displayed `os-zapret2-restyle (misconfigured)`.
- OPNsense firmware/install.sh performs `register.php install <package>` after the pkg
  transaction; direct `pkg add` does not run that outer step.
- The package hook called `rc.configure_plugins zapret2`, but that script interprets
  its first argument as lifecycle mode and expects `POST_INSTALL`, not a plugin name.

Impact:

- Direct package installation leaves OPNsense package state and configured-plugin state
  inconsistent.
- Firmware GUI may offer repair controls and cannot represent the installed plugin as
  normally configured.
- POST_INSTALL-specific integration refresh is skipped.

Remediation:

1. Invoke `register.php install os-zapret2-restyle` from +POST_INSTALL.
2. Fail installation when the registration helper is unavailable or registration fails.
3. Invoke `rc.configure_plugins POST_INSTALL`.
4. Add focused static coverage that requires both calls and rejects the old argument.

Acceptance criteria:

- clean direct `pkg add` records `os-zapret2-restyle` in
  `<system><firmware><plugins>`;
- Firmware > Plugins shows the installed version without `(misconfigured)`;
- repeated install/upgrade registration remains idempotent;
- package build and archive verification pass;
- existing service-state preservation remains unchanged.

Remediation status:
Implemented for package 0.2.5_2. CI/package build and focused OPNsense installation
verification remain required.
''')
)

append_once(
    "docs/DECISIONS.md",
    "DEC-2026-08-01 — PACKAGE POST-INSTALL OWNS DIRECT PKG REGISTRATION",
    dedent(r'''\
==================================================
DEC-2026-08-01 — PACKAGE POST-INSTALL OWNS DIRECT PKG REGISTRATION
==================================================

Status:
Active.

Decision:

The package +POST_INSTALL hook explicitly invokes the OPNsense firmware registration
helper for `os-zapret2-restyle` before refreshing integration with
`rc.configure_plugins POST_INSTALL`. The hook fails closed when registration or the
available integration refresh fails. Registration remains idempotent, so the same hook
works for Firmware installation, direct `pkg add`, reinstall, and upgrade.

Reason:

OPNsense's Firmware installer registers a plugin after the pkg transaction, but direct
`pkg add` executes only package hooks. Without explicit registration, package files are
installed while Firmware records configured=0 and displays `(misconfigured)`. The
previous `rc.configure_plugins zapret2` call also passed a plugin name where the script
expects a lifecycle mode.

Consequences:

- direct pkg installation and Firmware installation converge on the same configured
  plugin state;
- `POST_INSTALL` is the only accepted lifecycle argument in this hook;
- registration failure is visible rather than silently suppressed;
- focused package-hook tests preserve this contract.

Affected documents:

- pkg/+POST_INSTALL
- scripts/test-package-lifecycle-restart.sh
- README.md
- docs/PROJECT_STATE.md
- docs/AUDIT.md
- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/ARCHITECTURE.md
- docs/DEVLOG.md
- docs/ROADMAP.md
- docs/REQUIREMENTS.md
- docs/CHANGELOG.md

==================================================
DEC-2026-08-01 — IMMUTABLE PACKAGE-REVISION RELEASE TAGS
==================================================

Status:
Active.

Decision:

A corrected package revision may be published without changing VERSION by using the
immutable tag `vX.Y.Z_R`, where `X.Y.Z` equals VERSION and `R` equals
PLUGIN_REVISION. The canonical squash subject is `release: prepare vX.Y.Z_R`.
Ordinary project-version releases continue to use `vX.Y.Z` and reset
PLUGIN_REVISION to 1. Existing tags are never moved.

Reason:

The existing `v0.2.5` tag permanently identifies package 0.2.5_1, while current main
contains the unpublished package 0.2.5_2 candidate. Publishing that distinct package
must not rewrite the earlier release and should remain reproducible from its own exact
source commit.

Consequences:

- release-trigger runs on main pushes but no-ops successfully for non-release subjects;
- both tag forms are validated against repository metadata before publication;
- package-revision releases and project-version releases use the same package,
  checksum, GitHub Release, and Pages/pkg repository pipeline;
- `v0.2.5_2` may publish package 0.2.5_2, followed by normal `v0.2.6`.

Affected documents:

- .github/workflows/release-trigger.yml
- .github/workflows/release.yml
- scripts/test-release-trigger.sh
- docs/DECISIONS.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/ARCHITECTURE.md
- docs/GITHUB_WORKFLOW.md
- docs/PROJECT_STATE.md
- docs/DEVLOG.md
- docs/CHANGELOG.md
''')
)

append_once(
    "docs/WORKING_CONVENTIONS.md",
    "PACKAGE POST-INSTALL REGISTRATION RULE",
    dedent(r'''\
==================================================
PACKAGE POST-INSTALL REGISTRATION RULE
==================================================

The package +POST_INSTALL hook must explicitly register
`os-zapret2-restyle` through the OPNsense firmware registration helper. It then
refreshes integration using the exact lifecycle mode `POST_INSTALL`. Passing the
internal name `zapret2` to `rc.configure_plugins` is prohibited because that argument
is a lifecycle event, not a plugin identifier. The direct `pkg add` path must finish
with the same configured-plugin state as installation through Firmware.

A package revision that must be published while VERSION is unchanged uses immutable
tag `vX.Y.Z_R` and canonical release subject `release: prepare vX.Y.Z_R`. A normal
new project version continues to use `vX.Y.Z` and resets PLUGIN_REVISION to 1.
''')
)

append_once(
    "docs/DEVELOPMENT_GUIDE.md",
    "PACKAGE-REVISION RELEASE PROCEDURE",
    dedent(r'''\
==================================================
PACKAGE-REVISION RELEASE PROCEDURE
==================================================

When an approved release publishes an unpublished package revision without changing
VERSION:

1. confirm VERSION is `X.Y.Z` and PLUGIN_REVISION is `R`;
2. complete the packaged change and synchronized documentation;
3. publish the release-preparation PR with final squash subject
   `release: prepare vX.Y.Z_R`;
4. the release trigger creates immutable tag `vX.Y.Z_R`;
5. the Release workflow validates both components and publishes
   `os-zapret2-restyle-X.Y.Z_R.pkg`, SHA256SUMS, GitHub prerelease, and Pages/pkg
   repository metadata;
6. verify that Firmware/pkg sees the same package version.

For direct pkg installation verification, confirm both package inventory and
`<system><firmware><plugins>` registration. The plugin must not appear as
`(misconfigured)`, and the package hook must use `rc.configure_plugins POST_INSTALL`.
''')
)

replace_once(
    "docs/ARCHITECTURE.md",
    '''pkg add
  -> +POST_INSTALL
  -> rc.configure_plugins
  -> template reload
  -> print setup command
''',
    '''pkg add
  -> +POST_INSTALL
  -> register.php install os-zapret2-restyle
  -> rc.configure_plugins POST_INSTALL
  -> template reload
  -> print setup command
'''
)
append_once(
    "docs/ARCHITECTURE.md",
    "PACKAGE-REVISION RELEASE CONTROL PLANE",
    dedent(r'''\
==================================================
PACKAGE-REVISION RELEASE CONTROL PLANE
==================================================

Project-version releases use immutable tag `vX.Y.Z`. An unpublished corrected package
revision with unchanged VERSION uses immutable tag `vX.Y.Z_R`, matching
PLUGIN_REVISION. Both forms pass through the same release workflow and publish the
package archive, SHA256SUMS, GitHub prerelease, and current Pages/pkg repository.
The release trigger recognizes only the canonical release subjects and no-ops for
ordinary main commits; it never moves an existing tag.
''')
)

append_once(
    "docs/DEVLOG.md",
    "2026-08-01 — POST-INSTALL REGISTRATION AND PACKAGE-REVISION RELEASE",
    dedent(r'''\
==================================================
2026-08-01 — POST-INSTALL REGISTRATION AND PACKAGE-REVISION RELEASE
==================================================

Confirmed from live OPNsense output:

- package 0.2.5_1 was installed from Zapret2Restyle;
- Firmware > Plugins displayed `(misconfigured)`;
- direct pkg installation had not added the plugin to the firmware plugin list;
- +POST_INSTALL passed `zapret2` to a script that expects lifecycle mode
  `POST_INSTALL`.

Implemented:

- explicit idempotent registration of `os-zapret2-restyle`;
- correct POST_INSTALL integration refresh with fail-closed error handling;
- focused lifecycle-hook contract coverage;
- immutable `vX.Y.Z_R` package-revision release support without moving the existing
  `vX.Y.Z` tag;
- release-workflow validation for VERSION and PLUGIN_REVISION;
- synchronized package lifecycle, release workflow, architecture, audit, requirements,
  state, roadmap, changelog, and user documentation.

The first use of the new path is package release `v0.2.5_2`; the next requested
project release is `v0.2.6`.
''')
)

replace_once(
    "docs/ROADMAP.md",
    "10. Build revision 2 and repeat running/stopped setup plus forced-stop verification.\n11. Reboot and verify that startup renders and activates the saved configuration.",
    "10. [x] Correct direct pkg registration and the rc.configure_plugins POST_INSTALL call.\n11. Publish immutable package-revision release v0.2.5_2.\n12. Publish project release v0.2.6 with PLUGIN_REVISION reset to 1.\n13. Reboot and verify that startup renders and activates the saved configuration."
)
roadmap = read("docs/ROADMAP.md")
roadmap = roadmap.replace("12. Reconcile CFG-001", "14. Reconcile CFG-001")
roadmap = roadmap.replace("13. Resume GUI management", "15. Resume GUI management")
roadmap = roadmap.replace("14. Add installed runtime-version", "16. Add installed runtime-version")
roadmap = roadmap.replace("15. Obtain and present", "17. Obtain and present")
roadmap = roadmap.replace("16. Notify when", "18. Notify when")
roadmap = roadmap.replace("17. Allow selection", "19. Allow selection")
roadmap = roadmap.replace("18. Display runtime", "20. Display runtime")
roadmap = roadmap.replace("19. After the project owner", "21. After the project owner")
write("docs/ROADMAP.md", roadmap)

replace_once(
    "docs/REQUIREMENTS.md",
    "- Package post-install must register the plugin, render required templates, and print:\n",
    "- Package post-install must register `os-zapret2-restyle` through the OPNsense\n  firmware registration helper, refresh integration using lifecycle mode\n  `POST_INSTALL`, render required templates, and print:\n"
)
replace_once(
    "docs/REQUIREMENTS.md",
    "- Package removal must synchronously stop the service before plugin files disappear.\n",
    "- Direct `pkg add`, Firmware installation, reinstall, and upgrade must leave the\n  package recorded in the OPNsense configured-plugin list; an installed package must\n  not be shown as `(misconfigured)`.\n- Package removal must synchronously stop the service before plugin files disappear.\n"
)

append_once(
    "docs/GITHUB_WORKFLOW.md",
    "PACKAGE-REVISION RELEASES",
    dedent(r'''\
==================================================
PACKAGE-REVISION RELEASES
==================================================

The normal release tag is `vX.Y.Z` and requires VERSION `X.Y.Z`. When the explicitly
requested release is an unpublished package revision with VERSION unchanged, the tag
is `vX.Y.Z_R`, where `R` exactly equals PLUGIN_REVISION. Its canonical release squash
subject is `release: prepare vX.Y.Z_R`.

The main release-trigger workflow inspects every main push, succeeds without action for
ordinary subjects, and creates a tag only for one of the two canonical release forms.
The Release workflow validates both VERSION and, for revision tags, PLUGIN_REVISION.
Existing tags and releases remain immutable. Package revision publication never
rewrites `vX.Y.Z`.
''')
)

(ROOT / ".github/workflows/prepare-release-0252.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
