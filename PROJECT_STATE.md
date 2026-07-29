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
Milestone 7 — completion of approved plugin functionality

Current priority:
Finish the current documentation synchronization, then move project documentation
into docs/, verify strategy-to-list behavior, and complete the functionality already
approved in REQUIREMENTS.md.

Last completed:
Milestone 6 infrastructure and release audit, including the first successful official
v0.1.0 release and permanent separation of native Pages repository paths from flat
GitHub Release artifact staging.

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
- Supervisor continuously verifies that the monitored PID still identifies the configured dvtws2 binary.
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
- LIFE-005 watchdog removal implemented; live regression verification pending.
- LIFE-006 rc.d entry point lacks a project-owned zapret_enable source.
- LIFE-007 PID checks do not verify process identity.
- LIFE-008 supervisor stop escalates without checking exit.
- LIFE-009 lifecycle serialization implemented; live verification pending.

Open Architecture Debt:

- ARCH-001 supervisor-only runtime failure-detection decision implemented; verification pending.
- ARCH-002 package lifecycle policy.
- ARCH-003 launcher/supervisor/lifecycle responsibility boundaries decided; later focused supervisor checks remain.

Immediate next actions:

1. Install the watchdog-removal commit on the test OPNsense system and run normal
   start, status, restart, reconfigure, Apply, stop, PID, and firewall regression tests.
2. Confirm no watchdog files or active references remain in the installed system.
3. After successful verification, add only the first proven supervisor health check
   in a separate focused commit.
4. Continue transactional reconfigure, rollback, firewall snapshot, atomic backup,
   rc.d, and package-lifecycle audit.


==================================================
CURRENT PACKAGE AND RELEASE DIRECTION — 2026-07-29
==================================================

Approved:

- Project-owned pkg repository on GitHub Pages.
- GitHub Release assets and checksums.
- Initial ABI target FreeBSD:15:amd64 / supported OPNsense 26.7.
- Standard OPNsense Firmware GUI installation and updates.
- No manual SSH setup step for normal users.
- Automatic one-time runtime bootstrap on first GUI Apply or Start.
- Separate command blocks for checks and installation.

Implemented in the current package-lifecycle change:

- missing dvtws2 triggers setup.sh before lifecycle startup;
- setup remains outside pkg post-install to avoid nested pkg operations;
- lifecycle action timeouts allow the initial compilation;
- package message no longer instructs manual setup.

Next priority:

1. Live-verify PKG-001 with a package reinstall and first GUI Apply.
2. Implement GitHub Pages pkg-repository publication and the first v0.1.0 test release.
3. Verify GUI repository installation and removal of unknown-repository status.

==================================================
RELEASE INFRASTRUCTURE IMPLEMENTATION — 2026-07-29
==================================================

Release infrastructure implementation started:
- tag and VERSION validation remains mandatory;
- release package is built in FreeBSD 15;
- pkg repo generates the FreeBSD:15:amd64 catalogue;
- GitHub Release receives the package and SHA256SUMS;
- GitHub Pages receives the repository catalogue and zapret2-restyle.conf;
- the first v0.1.0 publication remains a prerelease pending live GUI verification.

Immediate next actions:
1. Commit and push the release infrastructure change.
2. Configure GitHub Pages source as GitHub Actions.
3. Create and push tag v0.1.0.
4. Verify the workflow, Release assets, Pages repository, pkg update, and GUI package state.
5. Record live results and close or update PKG-002.

==================================================
RELEASE PREFLIGHT UPDATE — 2026-07-29
==================================================

The current Milestone 6 implementation now validates the generated package archive,
not only its expected filename. scripts/verify-release-package.sh extracts
+MANIFEST and verifies the approved package name, VERSION plus PLUGIN_REVISION, and
project repository URL before pkg-repository generation and publication.

Immediate next step:
Commit this focused preflight change, then configure GitHub Pages for GitHub Actions
and create the v0.1.0 tag only after the repository is clean.


==================================================
FINAL RELEASE WORKFLOW AUDIT — 2026-07-29
==================================================

The pre-tag audit found and corrected a release-blocking catalogue assertion:
modern `pkg repo` output uses `meta.conf` and `data.pkg`, not `meta.pkg`. The workflow
now validates the actual repository format before either Release or Pages publication.

The first v0.1.0 repository remains explicitly unsigned and is acceptable only for
prerelease testing. Repository signing is recorded as mandatory before a stable
release. README now contains the one-time repository registration procedure and the
normal Firmware GUI installation path.

Immediate next action:
Commit this focused pre-tag correction, push main, confirm a clean repository, and
then create tag v0.1.0 for live workflow verification.

## First v0.1.0 workflow audit result

Validation and FreeBSD build succeeded. Publication stopped when the generic artifact
uploader rejected the colon in `FreeBSD:15:amd64`. The prepared fix preserves the
native pkg path, adds flat release-assets staging, and updates affected actions to
Node.js 24-capable versions. Next: commit, retag v0.1.0, and repeat the release audit.

==================================================
MILESTONE 6 CLOSED / MILESTONE 7 OPENED — 2026-07-29
==================================================

Milestone 6 is complete.

Completed and verified:
- Backend, lifecycle, supervisor, packaging, and release audit work required for the
  first official release.
- Project-owned GitHub Pages pkg repository and GitHub Release pipeline.
- Native `FreeBSD:15:amd64` Pages layout retained for pkg consumers.
- Separate flat `release-assets/` staging for generic GitHub Actions artifacts.
- GitHub Pages environment configured to permit release tags through a tag rule.
- First official v0.1.0 release published successfully.

Current Milestone 7 focus:
Complete the functionality already approved in REQUIREMENTS.md before considering
interface redesign or new product scope.

Ordered next work:
1. Move internal project documentation into the conventional `docs/` directory and
   update all links and reading-order references.
2. Verify that strategies are actually applied to their intended list targets,
   including `<HOSTLIST:youtube>`, `<IPSET:telegram>`, and `<HOSTLIST:user>`.
3. Audit and complete every already-declared requirement until the existing product
   scope works predictably on a real OPNsense system.

Explicitly out of current scope:
- navigation redesign;
- general OPNsense UX research;
- first-run redesign;
- Service, Diagnostics, Maintenance, Status, or Strategy UX audits;
- design work not required by the existing approved functionality.

UX is not a separate project objective. Interface work is considered when required to
support expanded functionality or when the current interface demonstrably prevents use
of an implemented capability. Otherwise the interface remains stable.
