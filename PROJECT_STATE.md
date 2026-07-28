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
Project memory foundation

Current priority:
Complete the engineering memory documents, then begin the API and inherited-reference audit.

Last completed:
Independent repository, package identity, attribution, build, CI, and release infrastructure.

Current documentation step:
Add INDEX.md and establish single-responsibility document roles.

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

Finish the engineering memory foundation.

Required documents:

1. INDEX.md
2. PROJECT_STATE.md
3. DECISIONS.md
4. WORKING_CONVENTIONS.md
5. DEVELOPMENT_GUIDE.md
6. ARCHITECTURE.md
7. DEVLOG.md
8. ROADMAP.md
9. REQUIREMENTS.md

After that, perform the complete API and inherited-reference audit.

==================================================
NEXT ACTIONS
==================================================

1. Commit INDEX.md, PROJECT_STATE.md, and DECISIONS.md as one documentation-system change.
2. Add WORKING_CONVENTIONS.md.
3. Add DEVELOPMENT_GUIDE.md.
4. Update ARCHITECTURE.md to contain architecture only.
5. Update DEVLOG.md with the documentation-system decisions.
6. Convert ROADMAP.md into ordered implementation stages.
7. Update README.md with the engineering memory entry point.
8. Begin the static API and inherited-reference inventory.
9. Test active interfaces on the installed OPNsense system.
10. Fix confirmed issues as separate logical commits.
11. Resume the Traffic Strategy structural validator after the audit.

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
