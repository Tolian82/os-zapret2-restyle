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
[ ] Inventory package lifecycle scripts
[ ] Inventory setup, build, CI, and release logic
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
[ ] Fresh installation test on clean OPNsense
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
[ ] Public stable release
