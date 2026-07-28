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

A1-001 — duplicate diagnostics page route

Classification:
duplicate / requires live test

Evidence:

- IndexController::diagnosticsAction() renders OPNsense/Zapret/diagnostics.
- DiagnosticsController::indexAction() renders the same template.
- Menu and GUI links use /ui/zapret/diagnostics, which resolves through
  IndexController::diagnosticsAction().

Risk:
Removing the second controller without checking direct URLs or external links may
break an undocumented route.

Required live test:
Verify both /ui/zapret/diagnostics and /ui/zapret/diagnostics/index, inspect web
access logs or routing behavior, and search external documentation before removal.

A1-002 — obsolete settings help text

Classification:
broken / inherited

Evidence:
forms/general.xml tells users to place HTTP strategies in an HTTP field and
HTTPS/TLS strategies in an HTTPS field. The current GUI has one unified Traffic
Strategy field.

Impact:
User instructions refer to fields that do not exist.

Required remediation:
Rewrite the help text for the unified Traffic Strategy model.

A1-003 — obsolete diagnostics guidance

Classification:
broken / inherited

Evidence:
diagnostics.volt tells users to copy a working strategy into the HTTPS Strategy
field in both dynamic result text and initial help text. That field no longer
exists.

Impact:
The diagnostics workflow directs users to a removed GUI control.

Required remediation:
Refer to Traffic Strategy and explain how a blockcheck result maps to a unified
strategy profile.

A1-004 — inconsistent blockcheck timeout chain

Classification:
broken

Evidence:

- diagnostics.volt: 600000 milliseconds.
- actions_zapret.conf: 600 seconds.
- Api/DiagnosticsController.php: 650 seconds.
- blockcheck.sh: 1500 seconds by default.

Impact and required remediation:
See the broken blockcheck chain above.

A1-005 — service reconfigure API endpoint not used by current GUI

Classification:
unused / requires live test

Evidence:
ServiceController::reconfigureAction() exists, while the current Apply flow calls
reconfigure internally through SettingsController. No call to
/api/zapret/service/reconfigure was found in the current Volt views.

Risk:
The endpoint may be an intentional standard OPNsense service interface or used by
an external caller.

Required verification:
Search all repository assets, inspect installed UI behavior and access logs, and
check OPNsense service-controller conventions before removal or retention.

A1-006 — ACL and API namespace alignment

Classification:
OK

Evidence:
ACL coverage includes ui/zapret/* and api/zapret/*, matching current menu, page,
and API namespaces.

A1-007 — configd actions referenced by the audited GUI/API block

Classification:
OK

Evidence:
Actions exist for start, stop, restart, reconfigure, status, blockcheck, and
testdomain. No missing configd action was found in this completed block.

A1-008 — retained zapret integration identities

Classification:
inherited / OK / intentional

Evidence:
MVC namespace OPNsense\Zapret, model mount //OPNsense/Zapret, internal service
zapret, configd namespace zapret, and related hook identities are consistent with
approved stable identities.

Constraint:
Do not rename these identities mechanically.

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
