# Domain connectivity negative-result correction

Date: 2026-08-03

Base commit:
852d1b2938a4118a71ecea48cafb41132a15d0a4

Package candidate:
os-zapret2-restyle-0.3.0_2

==================================================
OBSERVED
==================================================

The Diagnostics page displayed the complete positive Test Domain Connectivity report,
but cleared the result field for a blocked, reset, refused, or timed-out destination.

Static trace confirmed that `test_domain.sh` produced the expected negative report and
then returned curl's non-zero status. Configd `script_output` classified that as command
failure, discarded stdout, and the MVC controller returned the resulting empty string as
successful data.

==================================================
IMPLEMENTED
==================================================

- Kept invalid invocation and invalid domain input as non-zero execution errors.
- Made every completed curl probe return the full existing multiline report through
  configd, regardless of whether the destination was reachable.
- Added an MVC guard so an actual empty backend response becomes an explicit API error.
- Added focused mocked cases for timeout, connection reset, generic curl failure, and
  invalid input.
- Added the diagnostic contract test to CI.
- Advanced `PLUGIN_REVISION` from 1 to 2 with `VERSION` unchanged at 0.3.0.
- Recorded the full Finding, remediation, acceptance criteria, and live-test plan in
  `docs/audit/AUDIT-2026-08-03-DOMAIN-DIAGNOSTICS.md`.

==================================================
VERIFICATION
==================================================

Completed during preparation:

- `sh -n src/opnsense/scripts/OPNsense/Zapret/test_domain.sh`;
- `sh -n scripts/test-domain-diagnostics-contract.sh`;
- `sh scripts/test-domain-diagnostics-contract.sh`;
- `php -l` for `DiagnosticsController.php`.

Expected CI gates:

- complete shell and PHP validation;
- focused domain diagnostics contract test;
- existing regression suite;
- FreeBSD package build for `os-zapret2-restyle-0.3.0_2`.

Remaining live verification:

Install the package candidate on OPNsense and confirm that both a successful domain and
a negative timeout/reset case render their complete multiline reports in the same
result field.
