# 2026-08-04 — Strategy Lab architecture approved

==================================================
OBJECTIVE
==================================================

Replace the current synchronous Diagnostics Blockcheck implementation with a staged,
asynchronous Strategy Lab while preserving lifecycle safety, bounded execution, useful
online progress, partial results after cancellation, and exact restoration of the
normal Zapret2 service.

==================================================
COMPLETED IN THIS PATCH
==================================================

- Recorded the full approved Strategy Lab architecture before source implementation.
- Defined the asynchronous start/status/events/cancel/result job contract.
- Defined numbered stages 00 through 99.
- Defined operation, stage, standard, and extended timeout budgets.
- Defined exact RUNNING-to-RUNNING and STOPPED-to-STOPPED restoration.
- Defined mandatory normal Zapret2 stop and verification before baseline tests.
- Defined one active job, one active candidate strategy, and at most two endpoint probes
  under that same strategy.
- Fixed the QUIC precheck to `yandex.ru:443`, IPv4, ALPN `h3`, timeout 2 seconds, and
  exit-status-only classification.
- Defined family-first TLS 1.3 screening, accepted-family expansion, 3/3 stability, and
  shortlist ranking.
- Defined later TLS 1.2, HTTP, QUIC, UDP, and circular patches.
- Recorded the approved English and Russian short report messages.
- Replaced canceled-stage presentation with:
  - Russian: `SKIPPED — отменено`;
  - English: `SKIPPED — canseled`.
- Defined cancellation as a partial normal result followed by mandatory cleanup and
  restoration.
- Defined the final replacement of the old synchronous Blockcheck chain.

==================================================
LIVE EVIDENCE USED FOR THE PLAN
==================================================

The project owner supplied OPNsense measurements:

- Zapret2 stop: approximately 2.06 seconds;
- Zapret2 start/restoration: approximately 6.51 seconds;
- normal stop removed dvtws2, supervisor, and plugin-owned IPFW rules;
- normal start restored service processes and rule 19000;
- DNS A/AAAA checks completed well below one second;
- direct TLS 1.3 to `yandex.ru` succeeded;
- direct TLS 1.3 to `telegram.org` and `web.telegram.org` reached the 2-second connect
  timeout;
- fixed QUIC/IPv4 precheck returned status 124;
- no IPv6 default route existed and the IPv6 control connection failed.

These results establish the initial timeout budgets. Runtime capability tests remain
dynamic and do not hardcode a provider-wide blacklist.

==================================================
DELIVERY DECISIONS
==================================================

The complete work is split into 13 independent patches.

Patch N+1 is not prepared until patch N has passed every PR check, been squash merged,
completed every post-merge GitHub workflow, cleaned its task branch, and been verified
on `main` with no remaining GitHub processing.

All owner-assisted manual OPNsense checks are deferred until every implementation patch
has completed this serial GitHub gate. Each individual patch still requires focused
automated tests, syntax/static validation, standard CI, package build where applicable,
post-merge processing, and synchronized documentation.

==================================================
FILES ADDED OR UPDATED
==================================================

Added:

- `docs/architecture/STRATEGY_LAB.md`;
- `docs/decisions/DEC-2026-08-04-strategy-lab.md`;
- `docs/audit/DIAG-001-strategy-lab.md`;
- `docs/devlog/2026-08-04-strategy-lab-plan.md`.

Updated:

- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`.

No source, package hook, workflow, `VERSION`, `Makefile`, or package revision is changed.

==================================================
NEXT ACTION
==================================================

Complete all GitHub processing for this documentation patch. Only after the PR checks,
squash merge, post-merge workflows, automatic branch cleanup, `main` verification, and
branch-absence verification are complete may Patch 2 preparation begin.
