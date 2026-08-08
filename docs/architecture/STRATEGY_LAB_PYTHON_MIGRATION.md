# Strategy Lab Python migration plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is Strategy Lab split between Python and the remaining OPNsense/FreeBSD shell boundaries after the approved incremental migration?

Purpose:
Record the migration sequence, authoritative ownership, compatibility invariants, test gates, and handoff into GUI/live reconciliation.

Updated when:
Migration scope, module ownership, compatibility boundaries, or patch sequence changes.

Read after:
`docs/ARCHITECTURE.md`, `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`, and `docs/PROJECT_STATE.md`.

Do not store here:
Chronological implementation logs or owner-assisted live evidence.

==================================================
STATUS
==================================================

Migration Patches 0–6 are complete. Migration Patch 7 is source candidate
`v0.3.3_24` and completes the automated Strategy Lab Python ownership boundary.

After `_24` qualification and merge, the only planned migration work is Patch 8:
GUI/status reconciliation followed by the owner-assisted post-migration OPNsense live gate.

The latest published and owner-tested live candidate remains `_17`. Source qualification of
`_18` through `_24` does not supersede that live evidence.

==================================================
OBJECTIVE
==================================================

Move Strategy Lab responsibilities that require structured state, reliable subprocess
handling, explicit scoping, parsing, cancellation, deterministic search policy and final
result assembly out of large sourced POSIX-shell orchestration into Python 3.13 without
rewriting unrelated plugin code or weakening OPNsense lifecycle safety.

The automated migration is complete when:

- public Strategy Lab API/state/result contracts remain compatible;
- lifecycle safety and exact restoration remain authoritative;
- Python is the single automated owner of state, stage progression, request/probe,
  candidate/search and final result policy;
- shell remains only where an audited system boundary or private circular-session contract
  is deliberate;
- obsolete competing automated shell owners are removed rather than retained as fallback;
- the owner-assisted OPNsense matrix can resume from a separately authorized post-migration
  testing candidate.

==================================================
TARGET FLOW AFTER PATCH 7
==================================================

```text
Diagnostics GUI / JavaScript
        ↓
OPNsense PHP MVC/API
        ↓
configd action
        ↓
zapret_service.sh / shared lifecycle lock
        ↓
strategy_lab_worker.sh
        ↓
Python strategy_lab_py/orchestrator.py
        ├─ state.py
        ├─ request.py / probe.py
        ├─ candidate.py / family.py
        ├─ search.py / extended.py
        └─ result.py
             ↓
        narrow shell system adapters
             ↓
FreeBSD/OPNsense: dvtws2, ipfw, drill/curl/openssl/nc, sockstat/ps, service lifecycle
```

PHP remains responsible for HTTP validation, OPNsense MVC/API integration and bounded
configd invocation. Patch 8 may reconcile GUI presentation with already persisted Python
state, but it must not take backend ownership back from Python.

==================================================
PYTHON RUNTIME CONTRACT
==================================================

Migration Patch 1 established:

- OPNsense 26.7 / FreeBSD 15 target;
- Python exactly 3.13;
- plugin dependency `python313` mapped to `lang/python313`;
- OPNsense-owned `/usr/local/bin/python3` production interpreter boundary;
- standard-library-only migration code;
- packaged `.py` sources under `src/opnsense/`.

FreeBSD CI invokes `/usr/local/bin/python3.13` explicitly.

==================================================
AUTHORITATIVE AUTOMATED OWNERSHIP
==================================================

Patch 2 — `strategy_lab_py/state.py`

- sole automated `status.json` / `events.ndjson` mutation owner;
- schema/revision/progress/stage/result/lifecycle/circular-eligibility persistence;
- atomic revisioned writes and stale reconciliation.

Private circular-session `state.json` is deliberately not part of this ownership and
remains shell-owned.

Patch 3 — `strategy_lab_py/orchestrator.py`

- stage order `00,10,20,30,40,50,60,70,80,85,90,99`;
- Standard/Extended wall-clock budgets;
- cancellation/signals/adapter process-group termination;
- mandatory Stage 90 restoration and Stage 99 convergence;
- terminal state/outcome/report/localized terminal message policy;
- restoration-failure override.

Patch 4 — `strategy_lab_py/request.py` and `probe.py`

- finite DNS/TLS/HTTP/TCP/QUIC-control request execution;
- stdout/stderr/return-code/timeout/termination evidence kept distinct;
- DNS ANSWER-section-aware A/AAAA parsing;
- Stage 30/40 network/baseline execution and public result compatibility.

Patch 5 — `strategy_lab_py/candidate.py` and `family.py`

- endpoint binding through the shared DNS parser;
- candidate runtime/readiness/fatal-log/interception policy;
- exact remote-IP and IPFW counter-growth evidence;
- ordered Stage-50 TLS 1.3 family screening and per-candidate timeout/cancellation.

Patch 6 — `strategy_lab_py/search.py` and `extended.py`

- Stage-60 accepted-family expansion catalog/order/early-stop policy;
- Stage-70 source de-duplication/ranking/three-attempt stability replay;
- Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP orchestration;
- one generalized candidate lifecycle for TLS 1.3, TLS 1.2, HTTP, QUIC and generic UDP;
- exact-endpoint QUIC and generic-UDP request execution through the request owner.

Patch 7 — `strategy_lab_py/result.py`

- complete user-ready profile construction and validation;
- deterministic final source collection/ranking;
- exact three-attempt replay of the complete profile that will be published;
- Standard and Extended unified shortlist selection;
- recommendation and TLS 1.3 circular subset publication;
- automated-job circular eligibility after verified restoration.

Final replay reuses `candidate.py`; Patch 7 does not create a second candidate state
machine.

==================================================
REMAINING SHELL RESPONSIBILITIES
==================================================

Shell remains authoritative only for deliberate boundaries such as:

- public service lifecycle entry points and shared lifecycle lock ownership;
- audited FreeBSD dvtws2/IPFW/process/file mutations and observations behind explicit
  adapters;
- short compatibility launch wrappers;
- private circular-session ownership/state and its immutable-parent consumer.

The replay-specific `strategy_lab_profile_candidate_adapter.sh` is a system adapter, not a
result/search owner. It receives a complete already validated profile, replaces only the
static domain selector with the temporary runtime hostlist required by dvtws2 when needed,
and delegates all other candidate system actions to the canonical candidate adapter.

Patch 7 physically retires these competing automated owners:

- `strategy_lab_profile_replay_runner.sh`;
- `strategy_lab/worker_result.sh`;
- `strategy_lab/worker_stage_machine.sh`.

Some older helper modules can remain packaged where compatibility/system/private-circular
code still sources them. Presence alone does not make them authoritative. No production
path may delegate Python-owned automated policy back to them.

==================================================
PERSISTENCE / RESULT COMPATIBILITY
==================================================

Existing evidence locations remain stable:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate/search/final evidence files required by public contracts.

Patch 4 preserves public `network.json` / `baseline.json`; richer subprocess evidence may
live in sidecars. Patches 5/6 preserve candidate/family/expansion/stability/extended/QUIC/
UDP public contracts.

Patch 7 preserves the unified shortlist contract while making Python its publisher:

- `count` and `items` for the public shortlist;
- deterministic `recommendation`;
- `circular_count` and `circular_items` as the replay-verified TLS 1.3 subset for private
  circular validation;
- complete user-ready `profile` plus structured replay evidence on published items.

==================================================
PROFILE / FINAL REPLAY CONTRACT
==================================================

Supported final protocol profiles:

- TLS 1.3 — TCP/443, TLS L7;
- TLS 1.2 — TCP/443, TLS L7;
- HTTP — TCP/80, HTTP L7;
- QUIC — UDP/443, QUIC L7;
- generic UDP — validated configured port, no L7 filter, validated job-local payload.

Each published profile contains one transport filter, optional protocol L7 filter, one
validated target selector, `--out-range=-d10`, and the candidate desynchronization
fragment. Runtime-only dvtws2 arguments, nested selectors/filters, placeholders and
`--new` are rejected.

Each final source is replayed exactly three times. A shortlist entry is accepted only when
all three attempts pass and each replay proves that the exact complete published profile
was used.

==================================================
STAGE / BUDGET / CANCELLATION CONTRACT
==================================================

Production stage order remains:

`00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99`.

Python owns the Standard 150-second budget, Extended +120-second budget, stage/operation
ceilings, Stage-80 shared deadline, typed timeout handling and cancellation process-group
termination.

Terminal mapping remains:

- `ERROR`, `TIMEOUT`, `RESTORE_FAILED` => state `error`, report FAIL;
- `SUCCESS`, `NO_CANDIDATE`, `TARGET_ACCESSIBLE`, `PARTIAL` => state `completed`, report PASS;
- restoration failure overrides the prior outcome.

Automated circular eligibility is evaluated only after Stage 90 restoration evidence and
before the terminal snapshot is published.

==================================================
LIFECYCLE SAFETY
==================================================

Mandatory invariants:

1. Snapshot exact initial Zapret2 state before mutation.
2. Use the shared lifecycle ownership boundary.
3. Stop normal runtime only through approved lifecycle paths.
4. Run one temporary candidate at a time.
5. Keep temporary firewall/divert ownership isolated.
6. Clean candidate runtime before moving to the next candidate.
7. Execute Stage 90 on normal completion, timeout, cancel, signal or internal error.
8. Restore initial RUNNING to healthy RUNNING and initial STOPPED to STOPPED.
9. Never hide restoration failure behind a successful result.
10. Saved Traffic Strategy remains immutable.
11. Final profile replay uses the same unified candidate readiness/interception/cleanup
    owner as search candidates.
12. Private circular sessions cannot mutate the parent automated result.

==================================================
CONFIRMED LIVE/UI BACKLOG
==================================================

At the frozen `_17` live boundary:

1. Standard `rutracker.org` still fails Stage 50; exact `_17` root cause is not established.
2. New-job GUI can show visible ERROR before terminal evidence.
3. Active GUI can show `Strategy Lab returned no output.` while work continues.
4. Visible progress can remain 0% until terminal.
5. Shell-global target-type corruption existed in the old shell baseline path.
6. DNS parser could accept non-answer A/AAAA text.
7. DNS diagnostics flattened timeout, command failure and parser rejection.
8. Terminal reload/state presentation can resurrect retained terminal work incorrectly.
9. Candidate readiness log classification could miss fatal runtime log evidence.

Patches 4–7 replace several old source mechanisms and add focused regressions, but source
migration alone does not close owner-observed defects. Patch 8 owns GUI/status reconciliation
and post-migration live evidence.

==================================================
MIGRATION PATCH SERIES
==================================================

- Patch 0 — documentation/handoff: **COMPLETE**.
- Patch 1 — Python platform/compatibility: **COMPLETE / `_18`**.
- Patch 2 — automated state/progress/persistence: **COMPLETE / `_19`**.
- Patch 3 — stage machine/budgets/cancellation/finalization: **COMPLETE / `_20`**.
- Patch 4 — finite request/probe execution/parsing: **COMPLETE / `_21`**.
- Patch 5 — candidate runtime/family screening: **COMPLETE / `_22`**.
- Patch 6 — expansion/stability/extended orchestration: **COMPLETE / `_23`**.
- Patch 7 — final profile/replay/shortlist/eligibility + competing shell-owner retirement:
  **CURRENT `_24` SOURCE CHANGE**.
- Patch 8 — GUI/status reconciliation and post-migration live gate: **NEXT**.

Patch 8 must not reopen automated backend ownership that Patches 2–7 already moved to
Python.

==================================================
PATCH 7 VERIFICATION
==================================================

Patch 7 requires all earlier migration regressions plus:

- Python 3.13 compile/import of `result.py`;
- complete profile build/validation for domain, IPv4 and generic UDP;
- exactly three complete-profile replay attempts per final source;
- exact-profile identity evidence on every accepted replay;
- Standard TLS 1.3 shortlist and Extended per-protocol shortlist behavior;
- circular TLS 1.3 subset and automated eligibility persistence;
- immutable private-circular consumption of the parent shortlist;
- absence of the retired automated shell replay/result/stage-machine owners;
- complete authoritative Strategy Lab corrective matrix;
- full repository CI;
- FreeBSD 15 VM with `python313` and migration continuity tests through Patch 7;
- FreeBSD 15 package/content/manifest verification.

The legacy e2e harness may provide a fixture-only replay callback through
`STRATEGY_LAB_PROFILE_REPLAY_RUNNER`; production does not set that variable and the former
production shell replay runner is removed. This test bridge is not a production fallback.

==================================================
CUTOVER RULE
==================================================

For each migrated responsibility:

1. Add the Python implementation behind the stable boundary.
2. Run focused parity tests.
3. Switch the authoritative call path once.
4. Verify there is one owner of mutation/control policy.
5. Remove obsolete competing shell implementation in the designated retirement scope.
6. Keep shell only for explicit audited system/private-session boundaries.

Patches 2–7 now satisfy this rule for the complete automated Strategy Lab path.

==================================================
HANDOFF TO PATCH 8
==================================================

After `_24` passes latest-head CI and FreeBSD 15 qualification and is squash-merged:

1. re-inventory `main` and the frozen `_17` owner evidence;
2. inspect persisted Python state/result contracts against Diagnostics GUI behavior;
3. correct stale/new-job state, active no-output, progress and terminal reload presentation
   without changing Python backend ownership;
4. run full CI and FreeBSD package qualification;
5. only with explicit publication authority, publish the designated post-migration testing
   candidate;
6. resume the owner-assisted OPNsense live matrix from Scenario 1 and retain evidence for
   every applicable row.

Stable release remains blocked until the required live matrix is PASS.
