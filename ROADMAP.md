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

[ ] Inventory GUI JavaScript API calls
[ ] Inventory MVC API URLs
[ ] Inventory controller actions
[ ] Inventory model operations and configuration paths
[ ] Inventory configd actions
[ ] Inventory shell entry points and backend functions
[ ] Inventory rc scripts, syshooks, and plugin hooks
[ ] Inventory filesystem and generated-template paths
[ ] Inventory package lifecycle scripts
[ ] Inventory setup, build, CI, and release logic
[ ] Inventory external repositories, URLs, and downloads
[ ] Classify every inherited reference
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
