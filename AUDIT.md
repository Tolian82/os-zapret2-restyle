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

Rules:

- Record evidence before remediation.
- Do not classify a retained zapret identity as obsolete by name alone.
- Do not remove inherited code until its callers, effects, and replacement are
  understood.
- Record required live tests explicitly.
- After remediation, update the existing entry with verification evidence.
- Complete and document one audit block before starting the next block.
- An audit block is not complete until all affected Engineering Memory documents
  are updated and committed.

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
