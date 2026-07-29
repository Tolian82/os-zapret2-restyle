# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered implementation stages and completion status.

Updated when:
A stage starts, completes, changes order, or gains approved work.

Read after:
DEVLOG.md

Do not store here:
Detailed history, architecture explanations, or decision rationale.

==================================================
CURRENT STAGE
==================================================

API and inherited-reference audit

Working cycle:

[x] Record the stage plan
[ ] Perform the stage
[x] Define actionable finding IDs and remediation-record requirements
[x] Record detailed remediation plans for the completed MVC/API block
[x] Record discoveries and approved concepts for the completed MVC/API block
[x] Record completed MVC/API work and verification
[x] Record remaining work and the next audit block

==================================================
STAGE 1 — VERSION 0.1.0 FOUNDATION
==================================================

[x] Backend v2 foundation
[x] Unified Traffic Strategy
[x] Generic HOSTLIST/IPSET targets
[x] Transactional Apply
[x] Safe Reconfigure
[x] Runtime validation and rollback
[x] Initial public project documentation
[x] Independent package identity
[x] Independent build and release infrastructure
[x] Engineering Memory System

==================================================
STAGE 2 — API AND INHERITED-REFERENCE AUDIT
==================================================

[x] Record audit objective and scope
[x] Record Engineering Memory work cycle
[x] Inventory GUI JavaScript API calls
[x] Inventory MVC API URLs
[x] Inventory controller actions
[ ] Inventory model operations and configuration paths
[x] Inventory configd actions
[ ] Inventory shell entry points and backend functions
[~] Inventory rc scripts, syshooks, and plugin hooks (syshook chains recorded;
    rc.d overlap and remaining hooks still under audit)
[ ] Inventory filesystem and generated-template paths
[~] Inventory package lifecycle scripts (GUI-first bootstrap implemented; remaining upgrade/deinstall audit open)
[~] Inventory setup, build, CI, and release logic (repository/release model approved; publication pending)
[ ] Inventory external repositories, URLs, and downloads
[ ] Classify every inherited reference
[x] Create AUDIT.md and record verified and broken interface chains
[x] Add verification plans, remediation plans, acceptance criteria, and stable IDs
[ ] Remove only confirmed obsolete dependencies
[ ] Run live API and lifecycle tests

==================================================
STAGE 3 — VERSION 0.2.0
==================================================

[ ] Traffic Strategy structural validator
[ ] Empty-profile validation
[ ] Invalid --new placement validation
[ ] Missing-filter validation
[ ] Malformed TCP/UDP filter validation
[ ] Unknown placeholder type validation
[ ] Unknown target name validation
[ ] Unresolved placeholder validation
[ ] Profile and line numbers in errors
[ ] Focused backend test fixtures
[ ] CI checks for Backend v2
[ ] Package file inclusion verification
[ ] Package name and filename verification
[ ] Package build test
[ ] Fresh GUI installation test on clean OPNsense
[ ] Upgrade behavior test
[ ] Uninstall behavior test
[ ] Legacy configuration migration review

==================================================
STAGE 4 — VERSION 0.3.0
==================================================

[ ] Strategy presets
[ ] Expanded diagnostics

==================================================
STAGE 5 — VERSION 0.4.0
==================================================

[ ] Maintenance page
[ ] Plugin update management
[ ] zapret2 update management

==================================================
STAGE 6 — VERSION 1.0.0
==================================================

[ ] Stable package installation on supported OPNsense systems
[ ] Upgrade and rollback tests
[ ] Production-ready documentation
[ ] Public stable release through project pkg repository

==================================================
PERMANENT AUDIT AND ARCHITECTURE-DEBT TRACK
==================================================

[x] Establish AUDIT.md and actionable Finding format.
[x] Separate Findings from Architecture Debt.
[x] Require documentation commit before the next audit block or remediation.
[ ] Complete lifecycle and runtime audit.
[ ] Complete package lifecycle audit.
[ ] Resolve Architecture Debt through DECISIONS.md before dependent implementation.
[ ] Remediate verified Findings in small logical commits.
[ ] Verify and close Findings without deleting audit history.


==================================================
FIRST PUBLIC TEST RELEASE — VERSION 0.1.0
==================================================

[x] Approve project-owned pkg repository model
[x] Approve GitHub Pages publication and GitHub Release assets
[x] Approve FreeBSD:15:amd64 initial ABI target
[x] Remove manual SSH runtime-setup requirement from normal installation flow
[ ] Live-verify automatic first-start runtime bootstrap
[x] Generate pkg repository metadata with pkg repo
[x] Publish repository configuration file
[ ] Publish package and SHA-256 checksums
[ ] Verify install and update through OPNsense Firmware GUI
[ ] Tag and publish v0.1.0 public test release

==================================================
MILESTONE 6 — DISTRIBUTION AND RELEASE
==================================================

Status:
In progress.

Ordered work:
1. Add deterministic pkg-repository generation for FreeBSD:15:amd64.
2. Update the tag release workflow to build on FreeBSD 15.
3. Publish package and SHA256SUMS through GitHub Releases.
4. Publish pkg repository metadata and client configuration through GitHub Pages.
5. Publish v0.1.0 as a prerelease.
6. Connect the repository on the OPNsense test system.
7. Verify pkg update and Firmware GUI package detection.
8. Verify clean installation, upgrade, reinstallation, and removal paths.
9. Update AUDIT.md, PROJECT_STATE.md, DEVLOG.md, README.md, and CHANGELOG.md with live results.
10. Promote a later release from prerelease only after distribution acceptance criteria pass.

Acceptance criteria:
- tag equals VERSION;
- package is built for the approved ABI;
- pkg repo metadata is generated by pkg repo, not handwritten;
- GitHub Release and GitHub Pages are produced from the same tag workflow;
- OPNsense no longer reports the package as unknown-repository after repository refresh;
- installation and updates are available through the standard Firmware GUI;
- normal users do not run setup.sh manually.

Milestone 6 release preflight update:

[x] Read package version from VERSION during package construction.
[x] Use the independent project URL in package metadata.
[x] Add archive-level verification of package name, version, and www before publication.
[ ] Live-verify the preflight in the first v0.1.0 tag workflow.


Milestone 6 final pre-tag audit:

[x] Validate current pkg repository catalogue names (`meta.conf`, `data.pkg`, `packagesite.pkg`).
[x] Document one-time repository registration and Firmware GUI installation.
[x] Make the unsigned prerelease repository state explicit.
[ ] Live-verify repository generation and Pages publication from tag v0.1.0.
[ ] Add repository signing before stable-release promotion.
