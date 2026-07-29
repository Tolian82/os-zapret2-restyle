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
2026-07-28 — API AUDIT PLAN RECORDED
==================================================

Planned:

- Audit GUI JavaScript API calls.
- Audit MVC endpoints, controllers, models, and configuration paths.
- Audit configd actions and shell command targets.
- Audit backend functions, rc scripts, syshooks, and plugin hooks.
- Audit package lifecycle, setup, build, CI, release, and external URLs.
- Classify every interface and inherited reference.
- Run focused live tests.
- Record discoveries during the audit.
- Record completed work and the next stage when the audit finishes.

Working rule confirmed:

Every stage begins by recording the plan and ends by recording results,
discoveries, remaining work, and the next stage.

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


==================================================
2026-07-28 — AUDIT SYSTEM AND MVC/API AUDIT BLOCK
==================================================

Completed:

- Added AUDIT.md as the authoritative technical audit register.
- Made documentation-system changes explicit architectural changes.
- Required every approved rule to be recorded in project documentation.
- Required broken chains to be documented before remediation.
- Required each completed audit step to be documented before continuing.
- Mapped the settings and diagnostics GUI-to-configd chains.
- Verified Menu and ACL namespace alignment.
- Verified that GUI-referenced configd actions exist.

Findings recorded in AUDIT.md:

- Duplicate diagnostics page controller route.
- Obsolete HTTP/HTTPS Strategy field references in settings help text.
- Obsolete HTTPS Strategy references in diagnostics output and guidance.
- Inconsistent blockcheck timeout chain.
- Service reconfigure API endpoint not called by the current GUI and requiring
  further interface testing.

Next:

- Audit service lifecycle, rc.d, syshooks, plugin hooks, supervisor, watchdog,
  and possible lifecycle overlap.


==================================================
2026-07-28 — ACTIONABLE AUDIT FINDINGS AND INITIAL LIFECYCLE TRACE
==================================================

Completed:

- Required every audit block to end with updated, reviewed, and committed
  Engineering Memory before the next block or code remediation starts.
- Introduced stable finding IDs and a mandatory actionable finding structure.
- Expanded MVC-001, GUI-001, GUI-002, DIAG-001, and API-001 with exact affected
  files and symbols, affected chains, evidence, risks, verification plans,
  remediation plans, acceptance criteria, documentation impact, and status.
- Recorded the confirmed boot and shutdown syshook chains.
- Recorded LIFE-001 for possible overlap between automatic syshook lifecycle and
  the rc.d service entry point.
- Recorded LIFE-002 and LIFE-003 for focused boot, shutdown, and reboot tests.

Current result:

The MVC/GUI/API/configd block remains completed and now has actionable repair
plans. The lifecycle block is in progress; no lifecycle code remediation is
approved until its remaining static trace and required live tests are complete.

Next:

Continue lifecycle tracing through rc.d registration, plugin hooks, supervisor,
watchdog, launcher, firewall, failure paths, and cleanup, then synchronize and
commit the completed lifecycle block before moving on.

==================================================
2026-07-28 — LIFECYCLE AUDIT EVIDENCE AND ARCHITECTURE-DEBT MODEL
==================================================

Completed:

- Separated confirmed Findings from unresolved Architecture Debt.
- Defined the Architecture Debt lifecycle and prohibition on direct closure.
- Required a DECISIONS.md entry before dependent implementation.
- Required blocked Findings to remain unmodified until controlling architecture is
  decided.
- Recorded verified boot, shutdown, runtime start, runtime stop, and failure-cleanup
  chains.
- Recorded LIFE-004 through LIFE-008 with exact evidence, plans, and acceptance
  criteria.
- Opened ARCH-001 watchdog architecture, ARCH-002 package lifecycle policy, and
  ARCH-003 launcher/supervisor/watchdog responsibility boundaries.

No lifecycle code was changed.

Next:

- Complete reconfigure, rollback, firewall snapshot, atomic backup, package lifecycle,
  and concurrency audit.
- Perform required live tests.
- Commit the completed lifecycle audit documentation before remediation.


==================================================
2026-07-28 — LIFECYCLE MUTEX IMPLEMENTED (LIFE-009)
==================================================

Completed:

- Confirmed that MVC Config::lock() does not cover template reload or backend
  lifecycle execution.
- Confirmed that start, stop, restart, reconfigure, and runtime-failure previously
  had no common shell-level serialization boundary.
- Added one /usr/bin/lockf-backed mutex in zapret_service.sh.
- Serialized interactive mutating lifecycle commands with a bounded wait.
- Kept status read-only and non-blocking.
- Made runtime-failure use an immediate try-lock so an old supervisor callback
  cannot queue behind reconfigure and tear down the replacement runtime.
- Added a clear temporary-failure error for lock contention.
- Updated architecture, audit, decision, state, and changelog records.

Validation completed:

- POSIX shell syntax check for zapret_service.sh.
- Static verification that every public mutating service action passes through
  the common lock boundary.

Still required:

- Focused live concurrency and forced-termination tests on OPNsense.
- Normal start, stop, restart, reconfigure, Apply, status, and runtime-failure
  regression tests.

Next:

Live-verify LIFE-009, then continue the remaining lifecycle and package-lifecycle
analysis.

==================================================
2026-07-28 — FIREWALL STATE CHECK CONSOLIDATED (LIFE-004)
==================================================

Completed:

- Removed the duplicate firewall_rules_present() declaration from backend/firewall.sh.
- Preserved the existing firewall-presence behavior and retained one canonical implementation.
- Verified that all callers continue to resolve to the remaining function.
- Completed POSIX shell syntax validation for the project shell scripts.
- Updated the audit and changelog records.

Still required:

- Focused live verification of status, repeated start, incomplete-runtime detection,
  and firewall-presence detection before LIFE-004 is marked Resolved.

Next:

Continue the remaining Lifecycle/Runtime audit and live verification queue.
==================================================
2026-07-28 — PROCESS IDENTITY HARDENING (LIFE-007 / LIFE-008)
==================================================

Completed:

- Added one shared process-command identity check based on FreeBSD /bin/ps.
- Required launcher PID files to identify the configured absolute dvtws2 binary.
- Required supervisor PID files to identify the configured supervisor loop.
- Prevented stale or reused PIDs from receiving TERM or KILL.
- Made supervisor KILL escalation conditional after the grace period.
- Kept existing launcher, supervisor, and responsibility boundaries unchanged.
- Completed POSIX shell syntax and whitespace validation.

Still required:

- Live verification of /bin/ps command output on OPNsense.
- Normal lifecycle regression tests.
- Stale, malformed, dead, and unrelated live PID-file tests.

Next:

Run the focused live tests, then continue the remaining lifecycle and package-lifecycle audit.

==================================================
2026-07-29 — DISCONNECTED WATCHDOG REMOVED (LIFE-005 / ARCH-001)
==================================================

Decision implemented:

- Selected supervisor_loop.sh as the only runtime failure detector.
- Rejected a separate cron or daemon watchdog model.
- Required future supervisor health checks to be added separately and remain
  detection-only.

Code changes:

- Removed watchdog.sh.
- Removed watchdog_loop.sh.
- Removed the obsolete HTTP_ARGS / HTTPS_ARGS watchdog behavior with those files.
- Left existing supervisor behavior unchanged.

Validation completed:

- Repository search confirmed no active lifecycle, configd, syshook, package-hook,
  GUI, or cron integration depended on the removed files.
- POSIX shell syntax validation passed for all remaining shell scripts.

Still required:

- Install the updated files on OPNsense.
- Run normal lifecycle, Apply, PID, supervisor, and firewall regression tests.
- Confirm no watchdog files or active references remain on the installed system.

Next:

After successful regression verification, add only proven supervisor health checks
in separate focused commits.


==================================================
2026-07-29 — SUPERVISOR CHILD IDENTITY CHECK (LIFE-010)
==================================================

Implemented the first focused supervisor hardening commit after watchdog removal.

Code changes:

- Passed the configured absolute DVTWS_BIN path from orchestrator through
  supervisor_start to supervisor_loop.sh.
- Replaced kill -0-only monitoring with liveness plus FreeBSD ps command identity
  verification on every interval.
- Kept the existing single runtime-failure callback and detection-only boundary.
- Added no runtime-directory, firewall, restart, reconfigure, generation, or repair
  behavior.

Validation completed:

- POSIX shell syntax validation passed.
- Diff whitespace validation passed.
- All supervisor_start call sites were updated consistently.

Still required:

- Deploy through the package or copy the updated scripts.
- Run the minimal live check: status plus one process listing.

Next:

After live verification, evaluate the next supervisor health check independently.
