# DIAG-001 — Strategy Lab replaces synchronous Blockcheck

Classification: remediated in source / requires live OPNsense verification

This specialist audit record supersedes the historical synchronous Blockcheck chain
recorded in the top-level audit register.

## Previous broken chain

The browser, MVC, configd, and wrapper used inconsistent synchronous timeout limits.
The browser could not reliably receive a final result, and process, firewall, and
service restoration were coupled to one long HTTP request.

## Source remediation

Package candidate `0.3.2_15` removes every synchronous strategy-finding entry point:

- `blockcheck.sh` is not packaged;
- configd has no `[blockcheck]` action;
- `DiagnosticsController` has no `blockcheckAction`;
- the GUI does not call `/api/zapret/diagnostics/blockcheck`;
- the ten-minute AJAX timeout is absent.

The replacement chain is asynchronous:

```text
Diagnostics GUI
  -> StrategyLabController start
  -> short configd launch action
  -> detached lifecycle-owned job
  -> status polling once per second
  -> structured result
  -> optional cancellation with mandatory restoration
```

Temporary circular validation is exposed only after a completed domain job produces
three to five stable candidates. It uses the same lifecycle lock and never writes the
saved Traffic Strategy.

## Static verification

Focused regressions verify removal of the legacy path, the four asynchronous API calls,
one-second polling, stage and shortlist rendering, circular controls, localization,
and package revision 15. The complete project validation and FreeBSD package build are
required before merge.

## Remaining live verification

Install candidate `0.3.2_15` on OPNsense and verify:

1. standard and extended jobs against a blocked domain;
2. cancellation during an active probe;
3. exact running-to-running and stopped-to-stopped Zapret2 restoration;
4. circular start/stop and target-scoped firewall cleanup;
5. saved Traffic Strategy immutability.

DIAG-001 may be classified fully closed only after this owner-assisted evidence is
recorded.
