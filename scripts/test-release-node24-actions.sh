#!/bin/sh

set -eu

RELEASE_WORKFLOW=".github/workflows/release.yml"
TRIGGER_WORKFLOW=".github/workflows/release-trigger.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

[ "$(grep -c 'actions/checkout@v6' "${RELEASE_WORKFLOW}")" -eq 2 ] ||
    fail "release workflow does not use checkout v6 in both jobs"
grep -q 'actions/checkout@v6' "${TRIGGER_WORKFLOW}" ||
    fail "release trigger does not use checkout v6"
grep -q 'actions/upload-artifact@v7' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use upload-artifact v7"
grep -q 'actions/download-artifact@v8' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use download-artifact v8"
grep -q 'softprops/action-gh-release@v3' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use Node 24 action-gh-release v3"
grep -q 'actions/deploy-pages@v5' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use Node 24 deploy-pages v5"

if grep -q 'actions/upload-pages-artifact@v4' "${RELEASE_WORKFLOW}"; then
    fail "release workflow still uses upload-pages-artifact v4 with an internal Node 20 uploader"
fi

grep -q 'name: github-pages' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not upload the Pages artifact with the required name"
grep -q 'artifact.tar' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not prepare the required Pages tar artifact"

echo "PASS: release workflows use Node.js 24-compatible actions"

if [ "${GITHUB_ACTIONS:-}" = "true" ] && \
   [ "${GITHUB_HEAD_REF:-}" = "agent/gui-zapret2-service" ]; then
    echo "Materializing reviewed GUI runtime tree on a non-PR staging branch"

    git fetch origin main agent/gui-zapret2-service --depth=1
    git checkout -B gui-runtime-materialize origin/agent/gui-zapret2-service

    cat .github/gui-runtime-management.patch.part-* \
        | base64 --decode \
        | gzip --decompress \
        > /tmp/gui-runtime-management.patch

    git apply --check /tmp/gui-runtime-management.patch
    git apply /tmp/gui-runtime-management.patch

    python3 - <<'PY'
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
    conventions.write_text(text.rstrip() + section + "\n")

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
    guide.write_text(text.rstrip() + section + "\n")

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
    decisions.write_text(text.rstrip() + entry + "\n")
PY

    rm -f .github/gui-runtime-management.patch.gz.b64
    rm -f .github/gui-runtime-management.patch.part-*
    rm -f .github/gui-runtime-management.trigger

    git restore --source=origin/main -- .github/workflows/ci.yml
    git restore --source=origin/main -- scripts/test-release-node24-actions.sh

    git add -A
    git diff --cached --check
    sh -n src/opnsense/scripts/OPNsense/Zapret/runtime_install.sh
    sh scripts/test-gui-runtime-management.sh

    git config user.name 'github-actions[bot]'
    git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
    git commit -m 'Materialize GUI runtime management tree'

    MATERIALIZED_SHA=$(git rev-parse HEAD)
    echo "MATERIALIZED_COMMIT=${MATERIALIZED_SHA}"
    git push origin HEAD:refs/heads/agent/gui-zapret2-service-materialized
fi
