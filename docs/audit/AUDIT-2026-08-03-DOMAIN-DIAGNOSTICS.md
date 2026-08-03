# Domain connectivity negative-result audit

Date: 2026-08-03

Base implementation commit:
`fe518e7a4ebbfe827ca41d107fda8f7e4fcb8666`

Verified release:
`v0.3.1` / `os-zapret2-restyle-0.3.1_1.pkg`

==================================================
FINDING DIAG-002
==================================================

Title:
Negative domain-connectivity results disappear from the Diagnostics page

Classification:
RESOLVED / release published / owner live verified

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

==================================================
ORIGINAL DEFECT
==================================================

The shell script already formatted negative outcomes such as TLS handshake failure,
connection reset, timeout, DNS failure, connection refusal, and generic curl failure.
It then exited with curl's non-zero status.

OPNsense `script_output` treated that as command-execution failure and discarded the
formatted stdout. `Backend::configdRun()` returned an empty string, the API incorrectly
reported `status=ok`, and the browser replaced the result field with empty text.

A remote connectivity failure was therefore incorrectly represented as failure to
execute the diagnostic itself.

==================================================
REMEDIATION
==================================================

Implemented behavior:

1. Invalid invocation and invalid domain input remain non-zero execution errors.
2. Every completed curl probe emits the full existing multiline report.
3. After emitting a valid probe result, the wrapper exits zero so configd preserves
   stdout even when the destination is unreachable.
4. The MVC controller rejects an actually empty configd response and returns an
   explicit API error.
5. Focused automated tests cover timeout, connection reset, generic curl failure,
   invalid input, and the empty-response guard.

==================================================
ACCEPTANCE CRITERIA
==================================================

- Positive probes display DNS, HTTPS details, timings, and `SUCCESS`.
- Timeout displays the complete report ending in `=== Result: TIMEOUT ===`.
- Connection reset displays the complete report ending in
  `=== Result: CONNECTION RESET (likely DPI blocking) ===`.
- TLS, DNS, refusal, and generic curl outcomes follow the same complete-report path.
- Invalid input remains an execution error.
- An actual empty backend response becomes a visible API error rather than a blank
  successful result.

==================================================
VERIFICATION EVIDENCE
==================================================

Automated and release evidence:

- shell syntax validation passed;
- PHP syntax validation passed;
- focused diagnostics contract tests passed;
- pull-request CI and FreeBSD package build passed;
- annotated tag `v0.3.1` was published;
- package `os-zapret2-restyle-0.3.1_1.pkg`, checksum, and Pages/pkg repository were
  published through the release workflow.

Owner live evidence:

On 2026-08-03 the project owner explicitly reported that release/package `0.3.1_1`
was personally checked and everything in it was implemented correctly.

This owner statement closes the required live gate for DIAG-002. It confirms the
working release behavior without inventing additional commands, logs, or outputs that
were not supplied in the report.

==================================================
FINAL STATUS
==================================================

DIAG-002 is resolved and live verified. No further correction or version rollback is
required. Later releases continue forward from v0.3.1.
