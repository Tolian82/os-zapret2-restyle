# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What has been checked, what is broken, and what still requires verification?

Purpose:
Maintain the authoritative technical audit register for interfaces, inherited
references, broken chains, evidence, live-test requirements, remediation status,
and remaining audit scope.

Updated when:
An audit step starts or completes, evidence changes, a classification changes, a
live test is performed, or a recorded issue is remediated.

Read after:
PROJECT_STATE.md

Do not store here:
Decision rationale, permanent working rules, general development history, full
architecture descriptions, or product requirements.

==================================================
AUDIT METHOD
==================================================

Trace each interface through its complete chain:

caller
↓
route or handler
↓
action or command
↓
side effect
↓
runtime result

Allowed classifications:

OK
broken
unused
duplicate
inherited
requires live test

Audit records are separated into two classes:

Finding
A confirmed implementation defect, inconsistency, obsolete reference, duplicate,
unused interface, or risk that can be verified against the current implementation.

Architecture Debt
An unresolved design question that must be decided before dependent code is changed.
Architecture Debt is not treated as an implementation defect until a decision defines
the intended behavior.

Rules:

- Record evidence before remediation.
- Do not classify a retained zapret identity as obsolete by name alone.
- Do not remove inherited code until its callers, effects, and replacement are
  understood.
- Record required live tests explicitly.
- After remediation, update the existing entry with verification evidence.
- Complete and document one audit block before starting the next block.
- Every completed audit block must be committed with all affected documentation before
  the next block or remediation begins.
- Every Finding must include exact locations, evidence, impact, verification steps, a
  remediation plan, acceptance criteria, and affected documents.
- Architecture Debt must be discussed and resolved through DECISIONS.md before any
  dependent Finding is implemented.
- Architecture Debt cannot be closed directly. It moves through Open, Discussion,
  Decision, Implementation, Verification, Documentation, and Closed.

==================================================
FINDING RECORD FORMAT
==================================================

Every non-OK finding must include:

- Stable finding ID.
- Title and classification.
- Exact files, symbols, routes, actions, or runtime objects involved.
- The affected chain.
- Evidence.
- Probable cause, when known.
- Impact and risk.
- Verification plan.
- Remediation plan.
- Acceptance criteria.
- Required documentation updates.
- Current remediation status.

Finding IDs are stable references for DEVLOG.md, CHANGELOG.md, commits, pull
requests, tests, and later audit updates. A finding is never deleted merely because
it was fixed; its status and verification evidence are updated in place.

==================================================
AUDIT 1 — API AND INHERITED REFERENCES
==================================================

Date started:
2026-07-28

Status:
In progress

Objective:
Inventory and classify GUI, MVC, API, model, configd, shell, backend, runtime,
lifecycle, packaging, build, release, external URL, and diagnostic interfaces.

==================================================
COMPLETED BLOCK — MVC, GUI API, ACL, MENU, CONFIGD
==================================================

Settings chain — OK:

/ui/zapret
        ↓
IndexController::indexAction()
        ↓
general.volt
        ↓
/api/zapret/settings/get and /api/zapret/settings/apply
        ↓
OPNsense/Zapret template reload
        ↓
configctl zapret reconfigure
        ↓
zapret_service.sh
        ↓
Backend v2

Evidence:

- The settings page route and view exist.
- The GUI calls the settings API namespace.
- Apply performs template reload and invokes zapret reconfigure.
- The reconfigure configd action exists.

Domain-test chain — OK:

/ui/zapret/diagnostics
        ↓
IndexController::diagnosticsAction()
        ↓
diagnostics.volt
        ↓
/api/zapret/diagnostics/testdomain
        ↓
configctl zapret testdomain
        ↓
test_domain.sh

Blockcheck chain — broken:

/ui/zapret/diagnostics
        ↓
diagnostics.volt AJAX timeout: 600 seconds
        ↓
DiagnosticsController::blockcheckAction() configdpRun timeout: 650 seconds
        ↓
configd zapret blockcheck timeout: 600 seconds
        ↓
blockcheck.sh timeout: 1500 seconds

Impact:

- Configd can terminate the wrapper 900 seconds before the wrapper's default
  timeout.
- The browser stops waiting at the same boundary as configd and may not receive
  the final structured response.
- PHP is willing to wait longer than configd, so its timeout cannot make the
  wrapper's 1500-second limit effective.
- GUI guidance suggesting BLOCKCHECK_TIMEOUT=2700 applies only to a manual SSH
  invocation and does not repair the GUI chain.

Required remediation:

Choose and document one end-to-end timeout policy, ensure each outer layer waits
longer than the inner layer it supervises, and update user-visible duration text.

Live test required:

Run a domain test whose duration exceeds 600 seconds and confirm process cleanup,
JSON delivery, service restoration, pf restoration, and ipfw restoration.

==================================================
RECORDED FINDINGS
==================================================

--------------------------------------------------
MVC-001 — Duplicate diagnostics page route
--------------------------------------------------

Classification:
duplicate / requires live test

Affected locations:

- src/opnsense/mvc/app/controllers/OPNsense/Zapret/IndexController.php
  - IndexController::diagnosticsAction()
- src/opnsense/mvc/app/controllers/OPNsense/Zapret/DiagnosticsController.php
  - DiagnosticsController::indexAction()
- src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml
- src/opnsense/mvc/app/models/OPNsense/Zapret/ACL/ACL.xml
- src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt

Affected chain:

/ui/zapret/diagnostics
        ↓
IndexController::diagnosticsAction()
        ↓
OPNsense/Zapret/diagnostics

Possible secondary route:

/ui/zapret/diagnostics/index
        ↓
DiagnosticsController::indexAction()
        ↓
OPNsense/Zapret/diagnostics

Evidence:

- Both controller actions render the same template.
- Menu and current GUI navigation use /ui/zapret/diagnostics.
- No current repository caller of the secondary controller route was found.

Probable cause:
Historical MVC structure retained after diagnostics navigation was moved under
IndexController.

Impact and risk:

- Duplicate ownership of one page complicates maintenance.
- Future changes may be applied to one route assumption but not the other.
- Removing the secondary controller without live verification may break a direct,
  bookmarked, externally documented, or framework-generated route.

Verification plan:

1. Confirm the route selected by /ui/zapret/diagnostics.
2. Request /ui/zapret/diagnostics/index directly on OPNsense.
3. Inspect HTTP status, redirects, ACL behavior, and web access logs.
4. Search repository documentation, installed files, and external published links
   for the secondary route.
5. Confirm that no plugin framework convention requires the standalone controller.

Remediation plan:

1. If the secondary route has no required caller, remove
   DiagnosticsController.php.
2. Keep IndexController::diagnosticsAction() as the single page owner.
3. Re-run PHP syntax checks and route tests.
4. If the secondary route is required, document why it is retained and add an
   explicit compatibility comment instead of deleting it.

Acceptance criteria:

- Exactly one intentional page route remains, or both routes are documented as
  required compatibility interfaces.
- /ui/zapret/diagnostics opens successfully for an authorized user.
- Diagnostics API calls continue to work.
- No unexpected 404, redirect loop, or ACL regression occurs.

Required documentation updates:
AUDIT.md, PROJECT_STATE.md, DEVLOG.md, CHANGELOG.md when user-visible behavior
changes, and ARCHITECTURE.md if route ownership changes.

Remediation status:
Not started.

--------------------------------------------------
GUI-001 — Obsolete settings help text for split strategy fields
--------------------------------------------------

Classification:
broken / inherited

Affected location:

- src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml

Affected chain:

Settings help text
        ↓
HTTP Strategy field / HTTPS Strategy field
        ↓
fields do not exist in the current unified model

Evidence:
The form help text instructs users to put HTTP strategies in an HTTP field and
HTTPS/TLS strategies in an HTTPS field, while the current GUI exposes only the
unified Traffic Strategy field.

Probable cause:
User-facing text was not updated when the two-field model was replaced by the
unified Traffic Strategy architecture.

Impact and risk:

- The UI instructs users to use controls that are absent.
- Users may conclude that the installation or page is incomplete.
- The text conflicts with the approved Traffic Strategy architecture.

Verification plan:

1. Search all repository files and translations for HTTP Strategy and HTTPS
   Strategy references.
2. Confirm the actual label and semantics of the unified field.
3. Verify whether generated localization catalogs contain copied stale text.

Remediation plan:

1. Rewrite the help text around the unified Traffic Strategy field.
2. Explain that HTTP, HTTPS/TLS, TCP, and UDP profiles can coexist in the same
   strategy and are separated with --new where required.
3. Avoid describing implementation details that are not guaranteed by the
   validator.
4. Rebuild or refresh localization artifacts if the project later introduces
   generated translations.

Acceptance criteria:

- No settings-page text references removed HTTP or HTTPS Strategy fields.
- The help text accurately describes the unified Traffic Strategy model.
- The rendered form displays the new text without markup or layout regressions.

Required documentation updates:
AUDIT.md, DEVLOG.md, CHANGELOG.md, and README.md if equivalent user guidance is
present there.

Remediation status:
Not started.

--------------------------------------------------
GUI-002 — Obsolete diagnostics guidance for HTTPS Strategy
--------------------------------------------------

Classification:
broken / inherited

Affected location:

- src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt

Affected chain:

Blockcheck result and initial help text
        ↓
"copy into the HTTPS Strategy field"
        ↓
field no longer exists

Evidence:
diagnostics.volt contains both initial guidance and dynamic result text that
refer to the removed HTTPS Strategy field.

Probable cause:
Diagnostics copy was retained from the old split-field GUI after the unified
Traffic Strategy migration.

Impact and risk:

- The result workflow ends with an impossible action.
- Users may paste a strategy into an unrelated control or abandon a valid result.
- Diagnostics and settings pages describe different configuration models.

Verification plan:

1. Locate every static and dynamically generated occurrence in diagnostics.volt.
2. Run both successful and partial blockcheck result paths to identify all text
   variants shown to users.
3. Confirm how one blockcheck strategy should be represented inside Traffic
   Strategy, including profile separators.

Remediation plan:

1. Replace references to HTTPS Strategy with Traffic Strategy.
2. Explain whether the returned block is a complete strategy, a profile fragment,
   or a candidate that must be merged with existing profiles.
3. Preserve safe warnings about reviewing generated strategy text before Apply.
4. Test initial, successful, partial, timeout, and error result rendering.

Acceptance criteria:

- No diagnostics text references the removed field.
- Every result path points to the correct Traffic Strategy workflow.
- The guidance does not imply that raw output can always replace the full current
  strategy without review.

Required documentation updates:
AUDIT.md, DEVLOG.md, CHANGELOG.md, README.md if diagnostics usage is documented.

Remediation status:
Not started.

--------------------------------------------------
DIAG-001 — Inconsistent blockcheck timeout chain
--------------------------------------------------

Classification:
broken

Affected locations:

- src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt
  - AJAX timeout: 600000 milliseconds
- src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DiagnosticsController.php
  - configdpRun timeout: 650 seconds
- src/opnsense/service/conf/actions.d/actions_zapret.conf
  - blockcheck action timeout: 600 seconds
- src/opnsense/scripts/OPNsense/Zapret/blockcheck.sh
  - wrapper default timeout: 1500 seconds

Affected chain:

Browser: 600 seconds
        ↓
PHP API: 650 seconds
        ↓
configd: 600 seconds
        ↓
blockcheck.sh: 1500 seconds

Evidence:
The four configured boundaries are not a coherent supervision hierarchy.
Configd can terminate the command long before the wrapper's own timeout, while
the browser stops waiting at the same boundary as configd.

Probable cause:
Timeouts were changed independently in the browser, PHP, configd, and wrapper
layers without defining one end-to-end policy.

Impact and risk:

- Long blockcheck runs can be terminated by configd after 600 seconds.
- The browser can time out before receiving the API's final structured response.
- PHP's 650-second limit does not make the wrapper's 1500-second limit reachable.
- The GUI may show a generic transport failure while cleanup or service
  restoration continues separately.
- User guidance about BLOCKCHECK_TIMEOUT=2700 for SSH does not repair GUI runs.

Verification plan:

1. Determine the normal and worst-case duration of supported blockcheck modes.
2. Confirm configd timeout semantics and how it terminates child processes.
3. Confirm configdpRun timeout behavior and returned error structure.
4. Confirm browser behavior on timeout, disconnect, and late server completion.
5. Run a controlled test longer than 600 seconds.
6. During and after the test verify process cleanup, service state, pf state,
   ipfw state, temporary files, and final JSON response.

Remediation plan:

1. Approve one explicit end-to-end timeout policy.
2. Keep the wrapper as the innermost authoritative execution limit.
3. Configure each outer layer to wait longer than the inner layer, including a
   cleanup and response margin.
4. Use named constants or clearly cross-referenced values where practical to
   reduce future drift.
5. Update visible duration text and SSH guidance to distinguish GUI and manual
   execution.
6. Add focused tests for normal completion, wrapper timeout, configd failure,
   client timeout, and cleanup.

Acceptance criteria:

- The timeout hierarchy is documented and internally consistent.
- A run that completes within the wrapper limit returns structured JSON to the
  browser.
- A timed-out run terminates all descendants and restores service, pf, and ipfw
  state.
- No orphaned blockcheck process or stale temporary state remains.
- The GUI reports the actual failure layer and gives accurate next steps.

Required documentation updates:
AUDIT.md, DECISIONS.md for the approved timeout policy, ARCHITECTURE.md if the
supervision contract changes, DEVLOG.md, CHANGELOG.md, README.md or diagnostics
help where user-visible timing is described.

Remediation status:
Not started. Requires an approved timeout policy and focused live tests.

--------------------------------------------------
API-001 — Service reconfigure endpoint has no current GUI caller
--------------------------------------------------

Classification:
unused / requires live test

Affected location:

- src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php
  - ServiceController::reconfigureAction()

Affected chain:

/api/zapret/service/reconfigure
        ↓
ServiceController::reconfigureAction()
        ↓
configctl zapret reconfigure

Current settings Apply chain instead uses:

/api/zapret/settings/apply
        ↓
SettingsController
        ↓
configctl zapret reconfigure

Evidence:
No caller of /api/zapret/service/reconfigure was found in the current Volt views.

Probable cause:
The endpoint may be inherited, may implement a conventional OPNsense service API,
or may have been retained for external automation.

Impact and risk:

- Keeping an undocumented duplicate reconfigure entry point increases API surface.
- Removing it without checking conventions or external callers can break
  compatibility.
- Different entry points may evolve different validation or error behavior.

Verification plan:

1. Search all repository assets and installed files for the endpoint.
2. Inspect browser and configd access logs during normal GUI operations.
3. Compare with service-controller conventions in supported OPNsense plugins.
4. Check published API documentation and known external automation.
5. Invoke the endpoint on a test system and compare its behavior with Apply.

Remediation plan:

1. If required as a standard or public interface, retain and document its contract,
   authorization, validation scope, and intended callers.
2. If truly unused and nonstandard, remove the action in a dedicated compatibility
   cleanup commit.
3. Do not merge it into Settings Apply unless transactional semantics remain
   explicit and equivalent.

Acceptance criteria:

- The endpoint is either documented as intentional and tested, or removed after
  confirming no required caller.
- There is one clearly documented ownership model for settings Apply versus
  service-only reconfigure.

Required documentation updates:
AUDIT.md, ARCHITECTURE.md if the API contract changes, DEVLOG.md, CHANGELOG.md for
API removal or behavioral change, README.md if public use is supported.

Remediation status:
Not started.

--------------------------------------------------
A1-006 — ACL and API namespace alignment
--------------------------------------------------

Classification:
OK

Evidence:
ACL coverage includes ui/zapret/* and api/zapret/*, matching current menu, page,
and API namespaces.

--------------------------------------------------
A1-007 — Configd actions referenced by the audited GUI/API block
--------------------------------------------------

Classification:
OK

Evidence:
Actions exist for start, stop, restart, reconfigure, status, blockcheck, and
testdomain. No missing configd action was found in this completed block.

--------------------------------------------------
A1-008 — Retained zapret integration identities
--------------------------------------------------

Classification:
inherited / OK / intentional

Evidence:
MVC namespace OPNsense\Zapret, model mount //OPNsense/Zapret, internal service
zapret, configd namespace zapret, and related hook identities are consistent with
approved stable identities.

Constraint:
Do not rename these identities mechanically.

==================================================
ACTIVE BLOCK — SERVICE LIFECYCLE AND RUNTIME HOOKS
==================================================

Status:
In progress. This block is not complete and no lifecycle code change is approved.

Confirmed boot chain:

System start
        ↓
src/etc/rc.syshook.d/start/20-zapret
        ↓
configctl zapret start
        ↓
actions_zapret.conf [start]
        ↓
zapret_service.sh start
        ↓
Backend v2 lifecycle

Classification:
OK by static trace; focused boot test still required.

Confirmed shutdown chain:

System stop/reboot
        ↓
src/etc/rc.syshook.d/stop/20-zapret
        ↓
configctl zapret stop
        ↓
actions_zapret.conf [stop]
        ↓
zapret_service.sh stop

Classification:
OK by static trace; focused shutdown and reboot tests still required.

--------------------------------------------------
LIFE-001 — Possible overlap between syshook startup and rc.d service entry point
--------------------------------------------------

Classification:
requires live test

Affected locations:

- src/etc/rc.syshook.d/start/20-zapret
- src/etc/rc.syshook.d/stop/20-zapret
- src/opnsense/scripts/OPNsense/Zapret/rc.d/zapret
- src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
- src/opnsense/service/conf/actions.d/actions_zapret.conf

Affected chain:

Boot syshook
        ↓
configctl zapret start
        ↓
zapret_service.sh start

Parallel service entry point:

service zapret start / rc framework
        ↓
rc.d/zapret
        ↓
zapret_service.sh start

Evidence:
Both a start/stop syshook pair and an rc.d service wrapper exist and converge on
the same service script. Static inspection alone does not prove that rc.d/zapret
is automatically invoked during boot.

Risk:
If both mechanisms auto-start the service, duplicate start attempts, repeated
firewall programming, supervisor races, or misleading logs may occur. If rc.d is
manual-only, removing it would unnecessarily remove a useful standard service
entry point.

Verification plan:

1. Inspect rc.d metadata, rc.conf integration, package setup, and installed
   service registration.
2. Reboot a test OPNsense system with timestamped lifecycle logging enabled.
3. Record every invocation of rc.syshook, configctl, rc.d/zapret, and
   zapret_service.sh.
4. Confirm the number and ordering of launcher, firewall, and supervisor starts.
5. Test manual service zapret start, stop, restart, and status separately.

Remediation plan:

1. If syshook is the sole automatic lifecycle owner and rc.d is manual-only,
   retain both and document their distinct contracts.
2. If both auto-start, choose one automatic owner based on OPNsense conventions.
3. Make the retained start path idempotent even when invoked twice.
4. Remove or disable only the confirmed duplicate automatic registration.
5. Add lifecycle logging or tests sufficient to detect future overlap.

Acceptance criteria:

- A boot produces one intentional effective service start.
- A shutdown or reboot produces one intentional effective stop sequence.
- Manual service commands continue to work if rc.d is retained.
- Repeated start/stop requests are safe and do not duplicate firewall or
  supervisor state.

Required documentation updates:
AUDIT.md, PROJECT_STATE.md, ARCHITECTURE.md if lifecycle ownership changes,
DECISIONS.md if one owner is selected, DEVLOG.md, CHANGELOG.md for behavioral
changes, and DEVELOPMENT_GUIDE.md for new live-test procedures.

Remediation status:
Awaiting continued static audit and live verification.

--------------------------------------------------
LIFE-002 — Syshook startup chain
--------------------------------------------------

Classification:
OK / requires focused live test

Evidence:
The start syshook calls configctl rather than bypassing configd, and the configd
start action converges on zapret_service.sh.

Verification plan:
Confirm boot ordering, enabled/disabled behavior, logging, idempotence, and final
runtime readiness on a live OPNsense system.

Remediation plan:
No code change unless live evidence shows ordering, duplicate invocation, or
error-propagation defects.

Acceptance criteria:
One boot request reaches the expected ready state without duplicate runtime
objects.

--------------------------------------------------
LIFE-003 — Syshook shutdown chain
--------------------------------------------------

Classification:
OK / requires focused live test

Evidence:
The stop syshook calls configctl zapret stop, which converges on
zapret_service.sh stop.

Verification plan:
Test shutdown and reboot, confirming supervisor and launcher termination,
firewall cleanup, absence of orphan processes, and bounded completion time.

Remediation plan:
No code change unless live evidence identifies incomplete cleanup or ordering
problems.

Acceptance criteria:
Shutdown and reboot leave no zapret process, supervisor, PID file, or plugin-owned
firewall state behind.

==================================================
REMAINING AUDIT BLOCKS
==================================================

Next:

- Service lifecycle.
- rc.d scripts.
- syshooks.
- OPNsense plugin hooks.
- Supervisor and watchdog behavior.
- Duplicate or competing lifecycle paths.

Later:

- Model operations and persistent configuration paths.
- Shell entry points and backend functions.
- Runtime and generated-template paths.
- Package lifecycle and setup logic.
- Build, CI, and release logic.
- External repositories, URLs, and downloads.
- Diagnostic commands.
- Focused live tests for every requires live test item.

==================================================
REMEDIATION STATUS
==================================================

No code remediation has been performed for the findings above.

The next logical commit records the audit and documentation-system decisions
only. Code fixes must follow as separate minimal commits after the relevant audit
evidence and live-test requirements are complete.

==================================================
AUDIT RECORD FORMAT
==================================================

Finding record:

- Stable ID.
- Title and classification.
- Exact files, methods, routes, actions, or runtime paths.
- Broken or questionable chain.
- Evidence.
- Cause or likely origin.
- Impact and risk.
- Verification plan.
- Remediation plan.
- Acceptance criteria.
- Affected documentation.
- Current remediation status.

Architecture Debt record:

- Stable ARCH-XXX ID.
- Title and status.
- Design question.
- Why the question is architectural rather than an implementation defect.
- Options considered.
- Dependencies and related Findings.
- Required DECISIONS.md entry.
- Closure criteria.

A Finding that depends on open Architecture Debt must not be remediated until the
Architecture Debt reaches Decision status and the intended behavior is recorded.

==================================================
IN-PROGRESS BLOCK — SERVICE LIFECYCLE AND RUNTIME
==================================================

Status:
In progress. Static evidence is recorded below. No lifecycle remediation is
permitted until this block is completed, documented, committed, and required live
tests are performed.

Verified startup chain — OK:

OPNsense boot
        ↓
rc.syshook.d/start/20-zapret
        ↓
configctl zapret start
        ↓
actions_zapret.conf [start]
        ↓
zapret_service.sh start
        ↓
Backend v2 orchestrator

Verified shutdown chain — OK:

OPNsense shutdown or reboot
        ↓
rc.syshook.d/stop/20-zapret
        ↓
configctl zapret stop
        ↓
actions_zapret.conf [stop]
        ↓
zapret_service.sh stop

Verified runtime start order — OK:

build candidate
        ↓
validate candidate
        ↓
atomic activation
        ↓
start dvtws2 launcher
        ↓
install firewall rules
        ↓
start supervisor
        ↓
ready

Verified runtime stop order — OK:

stop supervisor
        ↓
remove firewall rules
        ↓
stop dvtws2 launcher

Verified failure cleanup — OK by static inspection:

A launcher, firewall, or supervisor start failure invokes runtime cleanup and
restores the previous runtime tree. The runtime-failure path removes divert rules
and stops the child process so traffic is not diverted to a missing handler.

--------------------------------------------------
LIFE-004 — duplicate firewall_rules_present() definition
--------------------------------------------------

Classification:
duplicate / confirmed

Location:
src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh

Evidence:
firewall_rules_present() is declared twice in the same sourced shell module. The
second declaration replaces the first at load time.

Impact:

- One implementation is dead code.
- A future edit to only the first declaration has no runtime effect.
- The two copies can silently diverge.
- Static review and maintenance are made unreliable.

Verification plan:

1. Locate every call to firewall_rules_present().
2. Compare both declarations byte-for-byte and semantically.
3. Run /bin/sh syntax validation after consolidation.
4. Live-test status, repeated start, incomplete-runtime detection, and firewall
   presence detection.

Remediation plan:

1. Select one canonical implementation.
2. Merge any useful comments into that implementation.
3. Remove the duplicate declaration only.
4. Do not alter firewall behavior in the same commit.
5. Update AUDIT.md, DEVLOG.md, PROJECT_STATE.md, and CHANGELOG.md when resolved.

Acceptance criteria:

- Exactly one declaration remains.
- All callers resolve to it.
- Shell syntax validation passes.
- Focused live tests preserve current behavior.

Remediation status:
Code remediated. The duplicate declaration was removed and one canonical
implementation remains. Static shell validation passed. Focused live verification
of status, repeated start, incomplete-runtime detection, and firewall-presence
detection is still required before the Finding can be marked Resolved.

--------------------------------------------------
LIFE-005 — watchdog files are disconnected from lifecycle
--------------------------------------------------

Classification:
unused / inherited / architecture-dependent

Locations:
watchdog.sh
watchdog_loop.sh

Evidence:

- No cron registration was found.
- No orchestrator, supervisor, syshook, package hook, configd action, model, or GUI
  path starts either watchdog file.
- watchdog.sh claims it runs from cron every minute.
- watchdog_loop.sh claims zapret_service.sh starts it under daemon(8).
- Neither claimed integration exists in the audited repository.
- watchdog.sh logs obsolete HTTP_ARGS and HTTPS_ARGS variables although Backend v2
  uses TRAFFIC_ARGS.

Impact:

- The files imply health-monitoring behavior that does not exist.
- Operators and maintainers can incorrectly assume automatic recovery is active.
- Enabling the files without a design decision could duplicate supervisor duties.

Verification plan:

1. Confirm no installed-system cron or generated configuration references exist.
2. Confirm no package lifecycle hook installs an external reference.
3. Decide ARCH-001 and ARCH-003 before modifying or removing the files.

Approved remediation:
Remove watchdog.sh and watchdog_loop.sh as disconnected inherited code. Keep the
existing supervisor as the only runtime failure detector. Do not add broader health
checks in this removal commit. After regression verification, add only explicitly
required, inexpensive supervisor checks in separate commits.

Implementation:

- Removed watchdog.sh.
- Removed watchdog_loop.sh.
- Removed the obsolete HTTP_ARGS / HTTPS_ARGS watchdog path with those files.
- No cron, configd, syshook, package-hook, GUI, or service integration was added.
- Existing supervisor behavior was intentionally left unchanged.

Verification plan:

1. Reinstall or copy the updated plugin files to the test OPNsense system.
2. Confirm neither watchdog file exists in the installed script directory.
3. Run start, status, restart, reconfigure, Apply, and stop regression tests.
4. Confirm dvtws2 and supervisor PID handling remains correct.
5. Confirm firewall rules appear on start and disappear on stop.
6. Confirm repository and installed-system searches contain no active watchdog path.

Acceptance criteria:

- No watchdog script is shipped or referenced as an active runtime component.
- Existing supervisor and lifecycle behavior pass regression tests unchanged.
- Only one runtime failure detector exists: supervisor_loop.sh.
- Any future supervisor health check is introduced by a separate focused commit.

Remediation status:
Resolved. Live regression confirmed normal status, stop, start, and restart; one
dvtws2 and one supervisor monitor remained active; expected supervisor PID files
were present; the divert rule remained installed; and no watchdog process, PID file,
or active non-documentation reference remained.

--------------------------------------------------
LIFE-006 — rc.d entry point lacks a project-owned zapret_enable source
--------------------------------------------------

Classification:
inherited / likely nonfunctional manual entry point / requires live test

Location:
src/opnsense/scripts/OPNsense/Zapret/rc.d/zapret

Evidence:
The script declares rcvar=zapret_enable and calls load_rc_config, but repository
search found no project code that writes zapret_enable=YES to rc.conf,
rc.conf.local, or an OPNsense rc configuration source. Normal boot uses syshooks
and configctl instead.

Risk:

- service zapret start may refuse to run because the rcvar is unset.
- service zapret onestart may work while the normal command does not.
- The rc.d path may be mistaken for a second supported automatic lifecycle.

Required live test:

service zapret status
service zapret start
service zapret onestart
sysrc zapret_enable

Remediation plan:
After live evidence and ARCH-002 review, choose one supported model: remove the
redundant rc.d entry point, integrate it correctly with OPNsense, or retain it only
as a clearly documented manual compatibility path. Do not create a second automatic
startup path.

Acceptance criteria:
There is one unambiguous automatic startup owner, and every retained manual service
command behaves as documented.

Remediation status:
Open; live test required.

--------------------------------------------------
LIFE-007 — PID checks do not verify process identity
--------------------------------------------------

Classification:
risk / remediated in code / live verification required

Locations:
src/opnsense/scripts/OPNsense/Zapret/backend/common.sh
src/opnsense/scripts/OPNsense/Zapret/backend/launcher.sh
src/opnsense/scripts/OPNsense/Zapret/backend/supervisor.sh

Evidence before remediation:
The checks relied on kill -0 against a PID read from a PID file. They did not verify
that the PID still belonged to dvtws2 or the expected supervisor loop.

Implemented remediation:

- Added common_process_matches(), which validates liveness and checks the full
  process command through FreeBSD /bin/ps.
- Launcher health and stop paths now require the command to contain the configured
  absolute DVTWS_BIN path.
- Supervisor health and stop paths now require the command to contain the configured
  absolute SUPERVISOR_LOOP path.
- The running supervisor loop now requires the monitored PID command to contain the
  configured absolute DVTWS_BIN path on every interval; PID reuse or identity change
  is reported through the existing runtime-failure callback.
- A missing, malformed, stale, or identity-mismatched PID file is removed by stop
  paths without signalling the referenced process.
- TERM/KILL escalation is performed only while the PID still identifies the expected
  plugin-owned process.

Impact:

- A stale PID file can report a false running state after PID reuse.
- Stop logic can signal an unrelated process.
- Runtime completeness checks can accept an invalid state.
- Restart can be skipped when the expected process is absent.

Verification plan:

1. Confirm /bin/ps -p PID -o command= output for daemon-managed dvtws2, the
   supervisor daemon, and the supervisor monitor on the supported OPNsense release.
2. Verify normal start, status, stop, restart, and reconfigure behavior.
3. Replace each plugin PID file with a live unrelated PID and confirm status rejects
   it and stop removes only the stale PID file.
4. Verify dead and malformed PID files are cleaned without errors.
5. Resolve ARCH-003 separately before changing responsibility boundaries or adding
   new restart policy.

Remediation plan:
Code remediation is complete. Keep the shared command-identity helper and adjust only
if live FreeBSD process-command output requires a narrower matching method.

Acceptance criteria:
A stale or reused PID cannot be treated as the expected process and cannot receive
TERM or KILL from the plugin.

Remediation status:
Code implemented; focused live verification required.

--------------------------------------------------
LIFE-008 — supervisor stop escalates without checking process exit
--------------------------------------------------

Classification:
risk / cleanup improvement

Location:
supervisor_stop_one()

Evidence before remediation:
The function sent TERM, slept one second, then sent KILL without checking whether the
process exited or still matched the expected supervisor loop.

Implemented remediation:
After TERM and the bounded one-second grace period, KILL is sent only if the PID is
still live and still identifies the configured supervisor loop. Identity mismatch
removes the stale PID file without signalling the referenced process.

Impact:
The unconditional escalation is harder to reason about, is inconsistent with the
launcher stop path, and compounds LIFE-007 if a PID file is stale or reused.

Verification plan:
Measure normal supervisor exit time and test already-exited, slow-exit, and stale-PID
cases after process identity protection is defined.

Remediation plan:
Code remediation is complete using a bounded one-second grace period and conditional,
identity-safe escalation. Extend the grace period only if live measurements show that
normal supervisor shutdown requires more time.

Acceptance criteria:
Normal exits do not receive KILL; escalation is conditional, bounded, and identity-safe.

Remediation status:
Code implemented together with LIFE-007; focused live verification required.

--------------------------------------------------
LIFE-009 — lifecycle operations were not serialized
--------------------------------------------------

Classification:
broken / remediated in code / live verification required

Location:
src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh

Affected entry points:

- start
- stop
- restart
- reconfigure
- runtime-failure

Unaffected read-only entry point:

- status

Damaged chain before remediation:

GUI Apply, configd, syshook, rc.d, or supervisor callback
        ↓
independent zapret_service.sh processes
        ↓
concurrent mutation of runtime-v2, runtime backups, PID files,
execution-stage state, supervisor state, and ipfw rules

Evidence:
The MVC Config::lock() protects only XML configuration mutation and is released
before template reload and configctl reconfigure. No shell-level lock existed in
the service wrapper or Backend v2. Unique candidate workspaces did not serialize
atomic activation, process control, firewall changes, or supervisor cleanup.

Impact:
Concurrent lifecycle commands could stop a replacement process, remove newly
installed firewall rules, overwrite execution-stage state, or race atomic
activation and rollback. A queued runtime-failure callback from an old supervisor
could also tear down a successfully replaced runtime.

Approved remediation:

1. Use one FreeBSD lockf-backed lifecycle mutex at
   /var/run/zapret2-lifecycle.lock.
2. Acquire it in zapret_service.sh, the common public lifecycle entry point.
3. Serialize start, stop, restart, and reconfigure with a bounded 30-second wait.
4. Keep status read-only and non-blocking.
5. Make runtime-failure use an immediate try-lock. If another lifecycle operation
   owns the lock, treat the callback as stale and do not queue cleanup behind the
   active operation.
6. Return EX_TEMPFAIL-compatible status 75 and a clear error when an interactive
   lifecycle command cannot acquire the lock.

Implementation:
The service wrapper now opens the lock file on file descriptor 9 and uses
/usr/bin/lockf against that descriptor. The kernel releases the lock when the
owning shell exits; the lock-file pathname may remain without representing a
stale lock.

Verification plan:

1. Run two reconfigure commands concurrently and confirm only one mutates runtime.
2. Run stop while reconfigure holds the lock and confirm bounded waiting or the
   documented busy error without partial cleanup.
3. Trigger a runtime-failure callback while reconfigure or stop owns the lock and
   confirm it exits without touching the replacement runtime.
4. Kill the lock-owning process and confirm a later command acquires the lock.
5. Confirm status remains responsive while another lifecycle command holds the lock.
6. Confirm normal start, stop, restart, reconfigure, Apply, and supervisor-failure
   behavior remains unchanged when there is no contention.

Acceptance criteria:

- At most one mutating lifecycle operation changes shared runtime state at a time.
- A stale supervisor callback cannot tear down a replacement runtime.
- Lock ownership is released automatically after normal exit, error, signal, or
  forced termination.
- status remains non-blocking.
- Busy commands fail clearly and do not alter runtime, PID files, firewall rules,
  backups, or stage state.

Required documentation updates:
AUDIT.md, ARCHITECTURE.md, DECISIONS.md, PROJECT_STATE.md, DEVLOG.md, and
CHANGELOG.md.

Remediation status:
Implemented; focused live verification pending before the Finding is marked
Resolved.

==================================================
ARCHITECTURE DEBT
==================================================

Lifecycle:
Open → Discussion → Decision → Implementation → Verification → Documentation → Closed

Architecture Debt cannot be closed directly. A DECISIONS.md entry is mandatory before
implementation. Dependent Findings remain blocked until the intended behavior is
approved.

--------------------------------------------------
LIFE-010 — supervisor loop monitored only PID liveness
--------------------------------------------------

Classification:
risk / remediated in code / live verification required

Location:
src/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh

Evidence before remediation:
After reading dvtws2.pid, the loop used only kill -0 against the original numeric PID.
If dvtws2 exited and the PID was reused before the next interval, the supervisor could
continue monitoring an unrelated process and fail to report runtime failure.

Implemented remediation:

- supervisor_start now passes the configured absolute DVTWS_BIN path to the loop;
- supervisor_loop.sh validates both liveness and the full FreeBSD ps command on every
  interval;
- an identity mismatch follows the existing single runtime-failure callback;
- no runtime-directory, firewall, restart, reconfigure, generation, or repair check
  was added in this commit.

Impact:
A recycled PID can no longer keep a failed runtime falsely classified as healthy.

Verification plan:

1. Deploy the package or updated scripts.
2. Confirm start or restart reaches running state.
3. Confirm exactly one dvtws2 and one supervisor monitor are present.
4. Confirm status remains running.

Acceptance criteria:

- Normal runtime remains stable under identity-aware monitoring.
- The loop receives the configured absolute dvtws2 path.
- Supervisor remains detection-only and invokes runtime-failure at most once per loop.
- No unrelated health check is introduced.

Remediation status:
Code implemented; static validation complete; focused live verification pending.

--------------------------------------------------
ARCH-001 — watchdog architecture is not defined
--------------------------------------------------

Status:
Decision recorded; implementation complete; verification pending

Decision:
The supervisor is the only runtime failure detector. The disconnected watchdog files
are removed. Broader health checks, if justified, are added incrementally to the
supervisor in separate commits and must remain detection-only.

Why architectural:
The answer changes lifecycle ownership, restart policy, logging, configuration,
packaging, and GUI behavior. It cannot be solved by merely wiring in existing files.

Approved model:

1. supervisor_loop.sh is the only runtime failure detector.
2. No separate cron or daemon watchdog is shipped.
3. Supervisor detects failures and delegates cleanup to runtime-failure; it does not
   rebuild configuration, reconfigure, or independently restart the service.
4. New health checks are added only when required, one focused commit at a time.

Dependencies:
LIFE-005 and ARCH-003.

Closure criteria:
Watchdog files removed; regression tests pass; responsibility boundaries are reflected
in architecture and live behavior; the first required supervisor health checks are
considered separately rather than bundled into watchdog removal.

--------------------------------------------------
ARCH-002 — package lifecycle policy is incomplete
--------------------------------------------------

Status:
Open

Design question:
Define supported install, upgrade, reinstall, downgrade, rollback, deinstall, and
cleanup behavior for configuration, runtime trees, PID files, logs, downloaded engine
artifacts, blobs, and generated state.

Why architectural:
Automatic deletion or preservation choices affect user data, rollback safety, package
manager behavior, and recovery. Current behavior must not be inferred solely from pkg
defaults.

Required investigation:
Inventory pkg scripts, plist actions, setup scripts, OPNsense plugin hooks, and live
install/upgrade/deinstall behavior on a test system.

Dependencies:
LIFE-006 and remaining package-lifecycle audit.

Closure criteria:
A complete lifecycle policy is approved in DECISIONS.md, implemented where necessary,
and verified by fresh-install, upgrade, reinstall, downgrade/rollback where supported,
and uninstall tests.

--------------------------------------------------
ARCH-003 — launcher, supervisor, and watchdog responsibilities overlap
--------------------------------------------------

Status:
Decision recorded; implementation in progress

Decision:
Launcher owns dvtws2 start/stop and child PID handling. Supervisor owns runtime failure
detection and calls runtime-failure. The lifecycle wrapper owns serialization and
cleanup dispatch. No independent watchdog exists.

Why architectural:
Without explicit boundaries, adding watchdog behavior or hardening PID handling can
create duplicate restarts, competing cleanup, or inconsistent status reporting.

Dependencies:
LIFE-005, LIFE-007, LIFE-008, and ARCH-001.

Remaining work:
Add only the supervisor health checks that are proven necessary, without giving the
supervisor restart, reconfigure, configuration-generation, or repair ownership.

Closure criteria:
Architecture diagram updated; watchdog removal and later focused health checks pass
failure-path tests; only one component owns each responsibility.


==================================================
PKG-001 — MANUAL RUNTIME SETUP BREAKS GUI-ONLY INSTALLATION
==================================================

Classification:
Finding

Evidence:
The installed package post-install message required the user to execute
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh manually. Without that command,
dvtws2 was absent and the service could not start. The package was otherwise visible
in the OPNsense GUI.

Impact:
Installation from Firmware > Plugins is incomplete without SSH access and cannot be
considered a normal OPNsense plugin installation.

Remediation:
When dvtws2 is missing, start and reconfigure automatically run setup.sh under the
existing lifecycle lock, verify the resulting binary, and continue. Increase configd
timeouts for lifecycle actions that may perform the one-time bootstrap. Do not run
setup.sh inside the pkg post-install transaction.

Acceptance criteria:

1. Install the package without running setup.sh manually.
2. Configure and Apply through the GUI.
3. Confirm setup runs automatically and dvtws2 is created.
4. Confirm the service starts and supervisor monitors it.
5. Confirm a later restart does not repeat setup while dvtws2 exists.
6. Confirm setup failure is reported and service startup does not continue.

Affected documents:
ARCHITECTURE.md, AUDIT.md, DECISIONS.md, PROJECT_STATE.md, DEVLOG.md, ROADMAP.md,
README.md, CHANGELOG.md

Remediation status:
Implemented; live verification required.


==================================================
PKG-002 — STANDALONE PACKAGE HAS NO MANAGED REPOSITORY
==================================================

Classification:
Finding

Evidence:
Firmware > Plugins displayed os-zapret2-restyle as misconfigured with repository
unknown-repository after local pkg add installation.

Impact:
The package cannot be installed or updated normally through the OPNsense GUI and its
origin cannot be reconciled with enabled repository metadata.

Remediation plan:
Publish a FreeBSD:15:amd64 pkg repository through GitHub Pages, generate metadata with
pkg repo, publish package assets and checksums through GitHub Releases, and provide a
repository configuration file.

Acceptance criteria:
The repository can be added once, pkg update succeeds, the plugin is listed from the
project repository in the GUI, and install/update completes through Firmware.

Remediation status:
Decision approved; implementation pending in the release-infrastructure commit.
