# DEC-2026-08-04 — Strategy Lab architecture and serial delivery

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Why was the Strategy Lab architecture and patch sequence approved?

Purpose:
Record the decisions that govern replacement of the synchronous Diagnostics
Blockcheck implementation.

Read after:
`docs/DECISIONS.md`.

==================================================
DECISION
==================================================

The current synchronous Blockcheck implementation will be replaced by an asynchronous
Strategy Lab through the ordered 13-patch series defined in
`docs/architecture/STRATEGY_LAB.md`.

The first patch is documentation only and records the complete approved design before
source implementation begins.

==================================================
SUPERSESSION NOTICE — 2026-08-08
==================================================

This file records the original Strategy Lab decision and is retained as engineering
history. It is **partially superseded**:

- `docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md` supersedes item 14's
  family-first/accepted-family-only search rule;
- item 6 remains active for one Strategy Lab **job**, but its one-candidate-process
  interpretation is reopened for the A/B/C cold/warm experiment; deterministic candidate
  isolation remains mandatory;
- item 15 is superseded for the QUIC candidate-search branch; the fixed IPv4 UDP/443 QUIC
  precheck remains diagnostic evidence only;
- warm-worker/dispatcher/source-port/parallel-probe mechanisms are hypotheses until the
  dedicated experiment plan passes;
- the strict serial GitHub delivery rule below was already superseded by
  `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md` and current
  `docs/GITHUB_PUBLICATION.md`.

Lifecycle safety, cancellation, exact restoration, saved Traffic Strategy immutability,
stage numbering and the fixed QUIC precheck itself remain active unless a later decision
explicitly changes them.

==================================================
APPROVED PRODUCT BEHAVIOR
==================================================

1. The normal Zapret2 service must not influence a Strategy Lab test.
2. The initial service state is classified as RUNNING or STOPPED before mutation.
3. When initially running, normal dvtws2, supervisor, and plugin-owned rules are stopped
   and verified absent before baseline testing.
4. Every exit path cleans temporary runtime and restores the exact initial service state.
5. A restoration failure is `RESTORE_FAILED` and cannot be hidden by a successful or
   partial test result.
6. Only one Strategy Lab job and one candidate strategy may be active at a time.
7. Up to two different required endpoints may be probed concurrently under that same
   active strategy.
8. The GUI starts an asynchronous job, polls online progress, and provides a Stop test
   control.
9. Cancellation preserves completed results, marks interrupted and remaining stages as
   skipped, executes full restoration, and returns a partial result rather than an
   ordinary error.
10. Approved cancellation output is:
    - Russian: `SKIPPED — отменено`
    - English: `SKIPPED — canseled`
11. English is the default OPNsense-language output; Russian is selected for `ru*`.
12. Short reports use stable message keys and variable substitution.
13. The standard test has bounded operation, stage, and overall time budgets.
14. Strategy search is family-first, expands accepted families only, confirms each
    required endpoint 3 of 3 times, and recommends a shortlist of stable candidates.
15. Extended TLS 1.2, HTTP, QUIC, arbitrary UDP, and circular validation are separate
    later patches.
16. Permanent Traffic Strategy settings are never modified automatically by this work
    package.
17. The old synchronous Blockcheck path is removed only after the complete replacement
    exists.

==================================================
FIXED QUIC PRECHECK
==================================================

The precheck is fixed:

- `yandex.ru:443`;
- QUIC;
- ALPN `h3`;
- IPv4;
- timeout 2 seconds;
- success determined only by command exit status.

A failed IPv4 precheck excludes QUIC/IPv6 and every QUIC strategy branch. The runtime
algorithm does not add output interpretation, OpenSSL capability probing, or local
firewall-rule investigation around this decision.

2026-08-08 amendment: retain the fixed IPv4 UDP/443 precheck itself, but do not open a
Strategy Lab QUIC candidate-search branch on PASS or FAIL. The quoted branch-exclusion
behavior above is historical implementation context only.

==================================================
PATCH DELIVERY DECISION
==================================================

The complete series is strictly serialized.

Patch N+1 must not be prepared or published until patch N has:

- passed every pull-request check;
- been squash merged;
- produced the verified expected `main` commit;
- completed every workflow triggered by the merge;
- completed automatic branch cleanup;
- been verified to have no remaining task branch or unresolved GitHub processing.

This is a blocking work-package postulate, not a recommendation.

==================================================
MANUAL VERIFICATION DECISION
==================================================

Manual checks requiring project-owner participation are deferred until every
implementation patch has passed the serial GitHub gate.

Each patch still receives automated focused tests, syntax/static validation, standard
CI, package build where applicable, post-merge processing, and synchronized
documentation. After the final replacement patch, one consolidated owner-assisted
OPNsense matrix verifies the complete feature.

==================================================
REASON
==================================================

The current implementation combines a long browser request, PHP timeout, configd
timeout, shell timeout, service stop/start, PF/IPFW manipulation, upstream textual
output parsing, and incomplete restoration reporting in one wrapper. Adding strategy
search features directly to that path would increase safety and correctness risk.

A staged asynchronous implementation provides independently testable boundaries for
job state, lifecycle restoration, network prechecks, candidate isolation, strategy
search, stability, reporting, extended protocols, and final migration.

Strict serial delivery prevents later patches from being prepared against an unmerged,
failed, or still-processing predecessor. Deferring owner-assisted checks avoids asking
the owner to repeatedly install and test incomplete internal layers while preserving
full automated validation for every patch.

==================================================
CONSEQUENCES
==================================================

- Patch 1 changes documentation only and leaves package metadata unchanged.
- Every later source patch is one independently reviewable logical change.
- The Strategy Lab specialist document is the architecture authority for this work.
- The existing synchronous Blockcheck remains available until final replacement.
- No later Strategy Lab patch begins before the preceding patch clears the complete
  GitHub gate.
- Manual integration evidence is collected once after the entire implementation series.
- Any material change to the approved stages, messages, lifecycle, QUIC contract,
  timeout model, or patch order requires an updated decision before implementation.

==================================================
AFFECTED DOCUMENTS
==================================================

- `docs/architecture/STRATEGY_LAB.md`
- `docs/audit/DIAG-001-strategy-lab.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/devlog/2026-08-04-strategy-lab-plan.md`
- later code-patch documentation as listed in the specialist architecture

Status:
Partially superseded; see the 2026-08-08 search decision and 2026-08-06 GitHub decision.
