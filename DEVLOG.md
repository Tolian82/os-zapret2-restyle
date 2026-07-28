# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What was done?

Purpose:
Record completed work, confirmed tests, failed attempts, and chronological
development progress.

Updated when:
A meaningful work unit is completed or tested.

Read after:
ARCHITECTURE.md

Do not store here:
Permanent rules, decision rationale, or future product requirements.

==================================================
2026-07-28 — INDEPENDENT PROJECT FOUNDATION
==================================================

Completed:

- Established os-zapret2-restyle as an independent project.
- Preserved attribution to bol-van and Umur Gorur in LICENSE and NOTICE.
- Approved independent package identity.
- Approved VERSION as the version source.
- Established independent build, CI, and release infrastructure.
- Removed inherited repository assumptions from build-package identity.
- Excluded attribution files from legacy-reference checks.

Goal:

Build and install the plugin on a clean supported OPNsense system without
runtime, build, or installation dependencies on another OPNsense zapret plugin
repository.

==================================================
2026-07-28 — BACKEND V2
==================================================

Completed:

- Backend v2 modular architecture.
- Unified Traffic Strategy.
- Generic <TYPE:name> placeholders.
- HOSTLIST/IPSET target registry.
- Target Mode.
- Domain and IPv4/CIDR normalization.
- Strict target validation.
- Wildcard domain canonicalization.
- Exclude Domains.
- Blob resolution.
- Port extraction.
- Generated dvtws2 arguments.
- Candidate validation.
- Atomic activation and restoration.
- Launcher and supervisor separation.
- ipfw lifecycle.
- Execution stages.
- Safe reconfigure.
- Transactional Apply.
- Field-level GUI errors.
- Normalized GUI reload.
- Explicit visible Apply button.

==================================================
2026-07-28 — CONFIRMED LIVE TESTS
==================================================

- Target placeholders resolve to separate managed files.
- *.googlevideo.com becomes googlevideo.com.
- Invalid 999.999.999.999 reports targets|failed.
- Invalid candidate leaves PID unchanged.
- Invalid candidate leaves active runtime unchanged.
- Invalid candidate leaves ipfw unchanged.
- Normal runtime reaches 13|13|ready|ok.

==================================================
2026-07-28 — ENGINEERING MEMORY SYSTEM
==================================================

Completed:

- Added INDEX.md.
- Added PROJECT_STATE.md.
- Added DECISIONS.md.
- Added WORKING_CONVENTIONS.md.
- Added DEVELOPMENT_GUIDE.md.
- Defined mandatory reading order.
- Defined one-document-one-question responsibility.
- Defined DOCUMENT ROLE blocks.
- Defined documentation synchronization with code.
- Defined that approved concepts must be recorded in DECISIONS.md.
- Restyled README.md, ARCHITECTURE.md, DEVLOG.md, and ROADMAP.md without losing
  their previous useful content.

==================================================
CURRENT WORK
==================================================

Current priority:

Complete the API and inherited-reference audit.

Audit scope:

- GUI JavaScript API calls.
- MVC API URLs.
- Controller actions.
- Model operations.
- Configd actions.
- Shell entry points.
- Backend functions.
- rc scripts.
- syshooks.
- Plugin hooks.
- Filesystem paths.
- Package lifecycle scripts.
- Setup logic.
- Build and release logic.
- External URLs.
- Diagnostic commands.

==================================================
KNOWN CAUTIONS
==================================================

- Do not commit /usr/local/etc/zapret2.
- Do not commit runtime, binaries, logs, PID files, backups, or secrets.
- Use FreeBSD-compatible commands.
- Give commands strictly in execution order.
- Do not guess OPNsense HTML or CSS structure.
- The field-width experiment was reverted and remains out of scope.
