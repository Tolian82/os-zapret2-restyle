# Strategy Lab hardening closure

## Current closure state

Status: **REOPENED BY THIRD AUDIT — CORRECTIVE SERIES IN PROGRESS**

The earlier hardening series and the `_6` live-evidence corrections remain valid historical evidence for the exact source states they tested. A third source audit on 2026-08-07 found seven additional defects or inconsistencies, recorded in:

`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`

Therefore the repository must no longer describe Strategy Lab source/CI closure as final. The `_6` owner-assisted live scenario-1 retest is paused. A later FreeBSD 15 amd64 package produced after the approved third-audit corrective series will become the next live candidate.

## Earlier hardening source/CI evidence

The corrective series from revision 25 through revision 46 addressed the accepted source findings recorded in `AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

Implemented source contracts included:

- strict runtime cleanup, readiness, deadline, stale-worker, and serialized-state safety;
- local-only automated traffic interception and endpoint-bound proof;
- complete exact-replay Traffic Strategy profiles across supported protocols;
- validated generic UDP input;
- immutable circular parent evidence, private sessions, owner identity, stale restoration, and retry blocking;
- Settings lifecycle coordination;
- persisted terminal-result reload and structured profile-copy presentation;
- deterministic progress and Russian/English presentation;
- removal of transitional aliases and duplicate hooks as understood at that stage;
- lock-protected evidence-preserving retention;
- one authoritative nonrecursive Strategy Lab corrective CI matrix.

Revision 46 changed no Strategy Lab runtime behavior. It froze the then-known documentation authority and live-appliance release gate.

## FreeBSD 15 package correction

Status: **COMPLETE IN HISTORICAL LINE**

The revision 46 pull-request package artifact was built by the general CI workflow on FreeBSD 14.2 and was excluded from live verification. The subsequent package workflow correction moved the PR package builder to FreeBSD 15 and enforced manifest ABI `FreeBSD:15:amd64` / `freebsd:15:x86:64`.

The current third-audit corrective series preserves the same package target: **FreeBSD 15 amd64 only**.

## Live-evidence `_5` and `_6` history

The `_5` live scenario-1 attempt proved the semantic PID detection correction but then exposed candidate-runtime and restoration failures. Those failures remain historical evidence.

Revision `_6` subsequently corrected:

- stage-50 candidate runtime ownership/teardown; and
- stage-90 bounded restoration startup/recovery.

The exact `_6` pull-request head for the restoration correction passed full CI and produced a FreeBSD 15 package artifact, and post-merge `main` CI also passed. No `_6` testing prerelease was published and no `_6` owner-assisted OPNsense retest was performed.

The third audit now supersedes `_6` as the next live-test candidate because additional source defects were identified before that retest.

## Third-audit corrective sequence

Status: **OPEN**

Approved order:

1. Patch 1 — third-audit documentation and corrective plan;
2. Patch 2 — ordinary stale recovery and timeout chain;
3. Patch 3 — circular stale recovery lifecycle ownership;
4. Patch 4 — remove load-order overrides and obsolete hooks;
5. Patch 5 — serialize worker state transitions;
6. Patch 6 — complete RU/EN progress localization;
7. Patch 7 — integrated third-audit regression gate;
8. Patch 8 — source/CI closure and live-test handoff.

Stable findings `SL3-001` through `SL3-007`, affected files, evidence, remediation plans, acceptance criteria, and patch mapping are authoritative in `AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

## Automated gate requirement

Every packaged corrective patch must pass the latest applicable repository gates, including:

- exact versioned PR and commit-title identity;
- PHP, XML, and shell validation;
- focused regression for its logical scope;
- the mandatory Strategy Lab corrective matrix;
- project lifecycle, release, governance, and repository-hygiene contracts;
- FreeBSD 15 package build and manifest inspection when package inputs change;
- post-merge `main` verification.

Patch 1 and Patch 8 are documentation-only and do not change package metadata.

## Live appliance status

Status: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**

The authoritative live plan remains:

`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`

No live PASS is inferred from CI, mocked integration tests, or package build success. Scenario 1 resumes only after Patch 8 designates a new FreeBSD 15 amd64 candidate. Dependent scenarios remain blocked until scenario 1 passes.

## Release status

Status: **BLOCKED ON CORRECTIVE SERIES AND LIVE MATRIX**

The current work does not authorize or perform:

- stable release declaration;
- pkg-repository promotion;
- GitHub Pages promotion;
- production-readiness declaration.

Testing prerelease publication for a later candidate still requires separate exact owner authorization under the GitHub publication rules.

## Reopening rule

A source audit or live failure reopens only the affected logical contract. The correction must use a new versioned patch, update the relevant authority and evidence, pass the full applicable regression/CI/package gates, and repeat the affected live scenario plus dependent scenarios where required.
