# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Current version, branch, priority, last completed work, blockers, or next actions change.

Read after:
INDEX.md

Do not store here:
Decision history, permanent rules, detailed workflow, architecture details, or product requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
os-zapret2-restyle

Current version:
0.1.0

Current branch:
main

Baseline tag:
restyle-start

Development tree:
/root/os-zapret2-restyle

Current phase:
API and inherited-reference audit execution

Current priority:
Live-verify lifecycle locking, firewall state detection, and process-identity
hardening, then continue the remaining lifecycle and package-lifecycle audit.

Last completed:
Hardened launcher and supervisor PID handling so stale or reused PIDs cannot be
treated as plugin-owned processes or receive lifecycle signals (LIFE-007 and
LIFE-008); live verification remains pending.

Current work cycle:
Investigate → verify → record audit evidence → update Engineering Memory → commit → continue or remediate.

Known blockers:
None.

==================================================
SOURCE OF TRUTH
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Branch:
main

Development tree:
/root/os-zapret2-restyle

Version source:
VERSION

Before proposing or applying code:

1. Read INDEX.md.
2. Follow the mandatory reading order.
3. Inspect the actual current repository files.
4. Check the current branch and commit.
5. Check the working tree.
6. Do not rely only on chat history, installed files, or memory.

==================================================
CURRENTLY CONFIRMED
==================================================

- Independent project repository exists.
- Independent package identity is established.
- Independent build, CI, and release infrastructure exists.
- Required attribution and provenance are preserved.
- Backend v2 modular architecture exists.
- Unified Traffic Strategy exists.
- Generic HOSTLIST and IPSET target handling exists.
- Target Mode exists.
- Global domain exclusions exist.
- Wildcard domain input is accepted and canonicalized.
- Strict domain and IP target validation exists.
- Candidate runtime generation and validation exist.
- Transactional Apply exists.
- Safe service reconfigure exists.
- Atomic runtime activation and rollback exist.
- Launcher, ipfw, and supervisor lifecycle exist.
- GUI field-level Apply errors exist.

Confirmed live behavior:

- Invalid candidate configuration preserves active runtime.
- Invalid candidate configuration preserves service PID.
- Invalid candidate configuration preserves active ipfw rules.
- Invalid IP input such as 999.999.999.999 fails at target validation.
- A valid configuration reached 13|13|ready|ok.

==================================================
CURRENT PRIORITY
==================================================

Complete and preserve the API and inherited-reference audit before remediation.

Completed static audit block:

- GUI settings and diagnostics entry points.
- Menu and ACL scope.
- MVC page routes.
- GUI API calls.
- API controller to configd action mapping.
- Configd action existence for start, stop, restart, reconfigure, status,
  blockcheck, and testdomain.

Documented findings:

- Duplicate diagnostics page controller route requires live verification.
- Settings help text still refers to removed HTTP and HTTPS strategy fields.
- Diagnostics text still refers to the removed HTTPS Strategy field.
- Blockcheck timeout chain is inconsistent: browser and configd use 600 seconds,
  PHP waits 650 seconds, and blockcheck.sh allows 1500 seconds.
- The service reconfigure API endpoint is not called by the current GUI and
  requires classification by live or external-interface testing.

The authoritative detailed audit record is AUDIT.md. Each non-OK finding now
requires exact affected locations, a verification plan, a remediation plan,
acceptance criteria, required documentation updates, and a stable finding ID.

Initial lifecycle evidence recorded:

- Boot uses start/20-zapret → configctl zapret start → configd →
  zapret_service.sh.
- Shutdown uses stop/20-zapret → configctl zapret stop → configd →
  zapret_service.sh.
- A separate rc.d/zapret entry point converges on the same service script; whether
  it participates in automatic boot remains a live-test question (LIFE-001).

==================================================
NEXT ACTIONS
==================================================

1. Commit the detailed finding records, remediation plans, audit synchronization
   rule, and initial lifecycle evidence.
2. Continue the incomplete service lifecycle block: rc.d registration, plugin
   hooks, supervisor, watchdog, launcher, firewall, failure paths, and cleanup.
3. Record every verified chain, overlap, broken path, and required live test in
   AUDIT.md before changing code.
4. Continue with backend, runtime paths, packaging, setup, build, CI, release,
   external URL, and diagnostics audits.
5. Run focused live tests for items marked requires live test.
6. Fix only confirmed issues as separate logical commits.
7. Update AUDIT.md after each remediation and verification.
8. Resume the Traffic Strategy structural validator after the complete audit.

==================================================
CURRENT AUDIT SCOPE
==================================================

The next engineering phase must inventory:

- GUI JavaScript API calls.
- MVC API URLs.
- Controller classes and actions.
- Model reads and writes.
- Persistent configuration paths.
- Configd actions.
- Shell command targets and arguments.
- Backend functions.
- rc scripts.
- syshooks.
- OPNsense plugin hooks.
- Generated templates.
- Filesystem paths.
- Package lifecycle scripts.
- Setup scripts.
- Build scripts.
- GitHub Actions workflows.
- Release scripts.
- External repository URLs.
- External downloads.
- Diagnostic commands.

Each item must be classified as:

OK
broken
unused
duplicate
inherited
requires live test

==================================================
KNOWN RISKS
==================================================

- Old project references may still exist in API, paths, setup, lifecycle, or build logic.
- Some retained zapret names are intentional and must not be removed mechanically.
- Watchdog, supervisor, rc, and syshook lifecycle paths may overlap and require tracing.
- Installed files may differ from repository source during live testing.
- Documentation can drift unless updated in the same logical commit as affected code.

==================================================
STATE UPDATE RULE
==================================================

Update this document only when the current operational state changes.

Typical triggers:

- Version changed.
- Branch or baseline changed.
- Current phase changed.
- Current priority changed.
- A major step was completed.
- A blocker appeared or was removed.
- Immediate next actions changed.

Do not use this document as a history archive.

==================================================
CURRENT LIFECYCLE AUDIT STATE
==================================================

Statically verified:

- Boot syshook → configctl → configd start → service wrapper → Backend v2.
- Shutdown syshook → configctl → configd stop → service wrapper.
- Candidate build, validation, activation, launcher, firewall, supervisor start order.
- Supervisor, firewall, launcher stop order.
- Runtime-failure cleanup removes divert rules and stops the child process.

Open lifecycle Findings:

- LIFE-004 duplicate firewall_rules_present() declaration.
- LIFE-005 disconnected inherited watchdog files.
- LIFE-006 rc.d entry point lacks a project-owned zapret_enable source.
- LIFE-007 PID checks do not verify process identity.
- LIFE-008 supervisor stop escalates without checking exit.
- LIFE-009 lifecycle serialization implemented; live verification pending.

Open Architecture Debt:

- ARCH-001 watchdog architecture.
- ARCH-002 package lifecycle policy.
- ARCH-003 launcher/supervisor/watchdog responsibility boundaries.

Immediate next actions:

1. Run the focused LIFE-009 concurrency, stale-callback, forced-termination, and
   non-blocking status live tests.
2. Complete transactional reconfigure, rollback, firewall snapshot, atomic backup,
   and package-lifecycle audit.
3. Run the LIFE-006 service/rcvar live tests.
4. Record all remaining lifecycle evidence before further remediation.
