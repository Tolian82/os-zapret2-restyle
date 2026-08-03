# Domain connectivity negative-result audit

Date: 2026-08-03

Base implementation commit:
fe518e7a4ebbfe827ca41d107fda8f7e4fcb8666

Release candidate:
v0.3.1 / os-zapret2-restyle-0.3.1_1

==================================================
FINDING DIAG-002
==================================================

Title:
Negative domain-connectivity results disappear from the Diagnostics page

Classification:
broken / remediated in source / release prepared / live verification required

Affected locations:

- `src/opnsense/scripts/OPNsense/Zapret/test_domain.sh`
- `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DiagnosticsController.php`
- `src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt`
- `src/opnsense/service/conf/actions.d/actions_zapret.conf`

Affected chain:

```text
Diagnostics Test Domain button
  -> /api/zapret/diagnostics/testdomain
  -> configdpRun('zapret testdomain')
  -> configd script_output action
  -> test_domain.sh
  -> curl connectivity result
```

Evidence:

- Successful HTTPS probes return curl status zero and their complete DNS, HTTPS, and
  final `SUCCESS` report reaches the result field.
- `test_domain.sh` already formatted negative results such as TLS handshake failure,
  connection reset, timeout, DNS failure, connection refused, and a generic curl
  failure.
- Before remediation, the script exited with the curl status after printing that
  report.
- OPNsense `script_output` treats a non-zero command as execution failure and does not
  return the command's stdout as the action result.
- `Backend::configdRun()` converts the resulting `Execute error` response to an empty
  string.
- `DiagnosticsController::testdomainAction()` returned `status=ok` even for that empty
  string, so the browser replaced the visible result with empty text.

Probable cause:

A remote connectivity failure was incorrectly used as the execution status of the
transport wrapper. For this diagnostic, the curl outcome is the data being measured;
it is not a failure to execute the diagnostic itself.

Impact:

Users receive no explanation when the tested domain is blocked, times out, resets the
connection, refuses the connection, or fails TLS. The negative path therefore hides the
most useful diagnostic result while the positive path works normally.

==================================================
REMEDIATION
==================================================

Implemented behavior:

1. `test_domain.sh` keeps non-zero exits for invalid invocation and invalid domain
   input.
2. After a valid curl probe completes, every curl result is emitted as the existing
   full multiline diagnostic report and the wrapper exits zero so configd preserves
   stdout.
3. `DiagnosticsController::testdomainAction()` rejects an empty backend response and
   returns an explicit API error instead of reporting empty output as success.
4. A focused mocked test verifies timeout, connection reset, generic curl failure,
   invalid input, and the controller's empty-response guard.
5. The correction is prepared for immutable release v0.3.1 with package revision 1.

Acceptance criteria:

- Positive results continue to show DNS, HTTPS timing/status details, and `SUCCESS`.
- Timeout shows the complete report ending in `=== Result: TIMEOUT ===`.
- Connection reset shows the complete report ending in
  `=== Result: CONNECTION RESET (likely DPI blocking) ===`.
- TLS, DNS, refusal, and generic curl outcomes follow the same complete-report path.
- Invalid domain input remains an execution error.
- An actual empty configd response produces a visible API error rather than a blank
  result field.
- PHP and shell syntax checks pass.
- The focused diagnostic contract test and the complete CI and release package builds
  pass.

==================================================
VERIFICATION STATUS
==================================================

Completed before release preparation:

- shell syntax validation for `test_domain.sh` and the focused test;
- focused mocked timeout, reset, generic failure, and invalid-input cases;
- PHP syntax validation for `DiagnosticsController.php`;
- pull-request CI, including the FreeBSD package build for the implementation commit.

Release verification required:

- release-preparation CI passes;
- annotated tag v0.3.1 points to the release-preparation merge;
- package `os-zapret2-restyle-0.3.1_1.pkg` and SHA256SUMS are published;
- the FreeBSD:15:amd64 Pages/pkg repository exposes the same package.

Required live OPNsense verification:

1. Upgrade to package 0.3.1_1.
2. Run Test Domain Connectivity against one reachable domain and confirm the existing
   positive report remains unchanged.
3. Run it against a domain or path that times out or is reset.
4. Confirm the result field displays the full DNS and HTTPS sections plus the final
   negative classification instead of becoming empty.
5. Confirm no global modal or browser transport error replaces the structured result.

Current status:
Source remediation and focused static verification are complete. Release publication
and live OPNsense rendering remain required before DIAG-002 is classified as fully
resolved.
