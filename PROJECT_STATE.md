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
Document the completed MVC, GUI API, ACL, Menu, and configd audit block, then audit service lifecycle and runtime hooks.

Last completed:
Static audit block for MVC, GUI API, ACL, Menu, and configd interfaces.

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

The authoritative detailed audit record is AUDIT.md.

==================================================
NEXT ACTIONS
==================================================

1. Commit AUDIT.md and all synchronized Engineering Memory updates.
2. Audit service lifecycle, rc.d scripts, syshooks, plugin hooks, supervisor, and
   watchdog behavior.
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
