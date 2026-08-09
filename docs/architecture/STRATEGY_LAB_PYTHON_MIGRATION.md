# Strategy Lab Python migration plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is Strategy Lab split between Python, the remaining OPNsense/FreeBSD shell boundaries, and the Diagnostics presentation layer after the approved incremental migration?

Purpose:
Record migration ownership, compatibility invariants, Patch-8 GUI/status reconciliation, verification gates, and the handoff into owner-assisted live validation.

Updated when:
Migration scope, module ownership, compatibility boundaries, GUI/status reconciliation, or live-gate sequencing changes.

Read after:
`docs/ARCHITECTURE.md`, `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`, and `docs/PROJECT_STATE.md`.

Do not store here:
Chronological implementation logs or owner-assisted live evidence.

==================================================
STATUS
==================================================

Migration Patches 0–8 are complete through `v0.3.3_25`. Corrective `_26` preserved the
same ownership while isolating Stage-50 candidate-local failures, and corrective `_27`
fixed the bounded DNS/stage envelope. Owner Scenario 1 on published `_27` passes the
post-migration Stage-40/50/60/70/90 path and supplied the live gate used for v0.4.0.

The automated backend migration is complete: Python is the single automated owner of job
state, stage orchestration, requests/probes, candidate/search policy and final result
assembly. Patch 8 must not move those responsibilities back into PHP, JavaScript or shell.

The 2026-08-08 adaptive-search decision changes Python search policy without changing
this ownership boundary. `_28` makes Stage-50 acceptance affect priority but not
candidate-family reachability. `_29` adds `candidate_spec.py` and `resources.py`: Python
snapshots installed resources at job initialization, normalizes every candidate and
renders exact runtime arguments before invoking the narrow system adapter. `_30` adds
`search_graph.py`: Python validates and plans the native TLS 1.3 DAG, persists graph
evidence and carries the exact node spec through stability and profile rendering. `_31`
adds `endpoint_epoch.py` and `telemetry.py`: Stage 40 fixes endpoint identity, Stage 60
selects each next graph node from live evidence, finalist defaults shrink to three and
all Python owners contribute durable timing. Its remaining target contract is
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`; runtime-model hypotheses are gated by
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

The latest published and owner-tested testing candidate is `v0.4.0_2`; focused `_28`
reachability/restoration passes. The current `0.4.0_5` `_31` source candidate has no new
owner live evidence. Candidate/package publication state remains governed separately by
`docs/GITHUB_PUBLICATION.md`.

==================================================
OBJECTIVE
==================================================

Move responsibilities that benefit from structured state, reliable subprocess handling,
explicit scoping, parsing, cancellation, deterministic search policy and final result
assembly out of large sourced POSIX-shell orchestration into Python 3.13 while preserving
OPNsense lifecycle safety and public behavior.

The migration and reconciliation series is complete only when:

- public Strategy Lab API/state/result contracts remain compatible;
- lifecycle safety and exact restoration remain authoritative;
- Python is the single automated backend owner;
- shell remains only at audited system or private circular-session boundaries;
- obsolete competing automated shell owners stay removed;
- Diagnostics renders only persisted job state and progress rather than transport status;
- transient status-read failures do not fabricate terminal job state;
- active reload and terminal-idle behavior follow the persisted-result contract;
- the owner-assisted OPNsense matrix resumes on a separately authorized post-migration
  testing candidate and records the required evidence.

==================================================
TARGET FLOW AFTER PATCH 8 SOURCE RECONCILIATION
==================================================

```text
Diagnostics GUI / JavaScript
        ↓  validates persisted job snapshots; retries transient reads
OPNsense PHP MVC/API
        ↓  request validation + transient transport classification
configd action
        ↓
strategy_lab_launcher.sh / short launcher lock
        ↓  background daemon closes launcher FD 9
zapret_service.sh / shared lifecycle lock
        ↓
strategy_lab_worker.sh
        ↓
Python strategy_lab_py/orchestrator.py
        ├─ state.py
        ├─ request.py / probe.py
        ├─ candidate.py / candidate_spec.py / resources.py / family.py
        ├─ search.py / extended.py
        └─ result.py
             ↓
        narrow shell system adapters
             ↓
FreeBSD/OPNsense: dvtws2, ipfw, process/file observations, service lifecycle
```

PHP remains responsible for HTTP/API validation and bounded configd invocation. JavaScript
owns presentation only. Neither layer may derive automated backend truth independently of
the persisted Python-owned job snapshot.

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

Private circular-session `state.json` remains deliberately shell-owned.

Patch 3 — `strategy_lab_py/orchestrator.py`

- stage order `00,10,20,30,40,50,60,70,80,85,90,99`;
- Standard/Extended wall-clock budgets;
- cancellation/signals/adapter process-group termination;
- mandatory Stage 90 restoration and Stage 99 convergence;
- terminal state/outcome/report policy;
- restoration-failure override.

Patch 4 — `strategy_lab_py/request.py` and `probe.py`

- finite DNS/TLS/HTTP/TCP/QUIC-control request execution;
- distinct stdout/stderr/return-code/timeout/termination evidence;
- DNS ANSWER-section-aware A/AAAA parsing;
- Stage 30/40 network/baseline execution and public result compatibility.

Patch 5 — `strategy_lab_py/candidate.py` and `family.py`

- endpoint binding through the shared DNS parser;
- candidate runtime/readiness/fatal-log/interception policy;
- exact remote-IP and IPFW counter-growth evidence;
- ordered Stage-50 TLS 1.3 family screening and per-candidate timeout/cancellation.

Adaptive-search `_29` extends this owner with `strategy_lab_py/candidate_spec.py` and
`resources.py`: immutable normalized candidate evidence, one job-scoped installed
resource snapshot, exact candidate-minimal Lua/BLOB/range rendering and persisted
resource/spec identity. It does not change the fixed catalog or search graph.

Adaptive-search `_30` adds `strategy_lab_py/search_graph.py`: a validated seven-seed/
sixteen-node native Zapret2 DAG, semantic resource eligibility, exact golden candidates,
candidate-defined ranges and persisted planning/node evidence. Active Stage 50/60 no
longer obtains policy from flat TSV catalogs.

Patch 6 — `strategy_lab_py/search.py` and `extended.py`

- current `_31` Stage-60 graph exploration chooses one reachable node after every live
  PASS/FAIL while Stage-50 evidence remains priority rather than a reachability gate;
- every candidate and extended path verifies the fixed Stage-40 search-epoch identity;
- Stage-70 source de-duplication/ranking/three-attempt stability replay;
- Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP orchestration;
- one generalized candidate lifecycle across supported protocols;
- exact-endpoint QUIC and generic-UDP request execution through the request owner.

The accepted-family gate was part of the completed migration baseline and is superseded
by `_28`. The current QUIC candidate-search branch remains pre-redesign behavior; the
later adaptive target keeps only the fixed IPv4 UDP/443 QUIC precheck and concentrates
search on native Zapret2 TCP/TLS plus the approved non-QUIC extended branches.

Patch 7 — `strategy_lab_py/result.py`

- complete user-ready profile construction and validation;
- deterministic final source collection/ranking;
- exact three-attempt replay of the complete published profile;
- Standard and Extended unified shortlist selection;
- recommendation and TLS 1.3 circular subset publication;
- automated-job circular eligibility after verified restoration.

Final replay reuses `candidate.py`; there is no second candidate state machine.

==================================================
REMAINING SHELL RESPONSIBILITIES
==================================================

Shell remains authoritative only for deliberate boundaries such as:

- public service lifecycle entry points and shared lifecycle lock ownership;
- audited FreeBSD dvtws2/IPFW/process/file mutations and observations behind explicit
  adapters;
- short compatibility launch wrappers;
- private circular-session ownership/state and immutable-parent consumption.

The replay-specific `strategy_lab_profile_candidate_adapter.sh` is a system adapter, not a
result/search owner. Python replaces the validated static selector with the temporary
runtime hostlist and writes the exact argument file; the profile adapter only delegates
system actions to the canonical candidate adapter.

Patch 7 physically retired these competing automated owners:

- `strategy_lab_profile_replay_runner.sh`;
- `strategy_lab/worker_result.sh`;
- `strategy_lab/worker_stage_machine.sh`.

Some older helper modules may remain where compatibility/system/private-circular code still
sources them. Presence does not make them authoritative and no production path may delegate
Python-owned policy back to them.

==================================================
PATCH 8 GUI / STATUS RECONCILIATION
==================================================

The automated launcher serializes short launcher operations with a nonblocking lock on FD
9. Before `_25`, `start_job()` launched the long-lived background lifecycle process through
`daemon(8)` without closing that descriptor. The private circular launcher already closed
FD 9 correctly.

Patch 8 requires the automated daemon launch to close FD 9 before the worker starts. The
short start transaction remains serialized, but the background worker must not inherit the
launcher lock that status/result/cancel requests need.

Transport/read status is separate from job state:

- empty or invalid configd output is reported by PHP as `status:"error"` plus
  `transient:true`;
- AJAX/network failures use the same transient marker;
- a browser job snapshot is accepted only with a valid `job.*` ID and persisted state
  `queued`, `running`, `cancel_requested`, `completed`, or `error`;
- visible job state is derived only from `data.state`;
- `data.status` is transport/API metadata and must never be used as fallback job state;
- a transient read preserves the last valid rendered state/progress and schedules a retry;
- accepted start may render the known accepted job as queued Stage 00 until the first
  persisted snapshot arrives;
- persisted Python `progress.percent` is authoritative; the stage-to-percent map remains
  compatibility fallback only;
- initial Diagnostics discovery retries transient reads, resumes an actual active snapshot,
  and treats explicit `{status:"idle"}` as idle without resurrecting terminal history;
- private circular presentation also preserves its last valid state across transient/busy
  reads.

This reconciliation changes presentation/read semantics only. It does not create another
state writer or backend owner.

==================================================
PERSISTENCE / RESULT COMPATIBILITY
==================================================

Evidence locations remain stable:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate/search/final evidence files required by public contracts.

Patch 7 preserves the unified shortlist contract while making Python its publisher:

- `count` and `items` for the public shortlist;
- deterministic `recommendation`;
- `circular_count` and `circular_items` as replay-verified TLS 1.3 subset;
- complete user-ready `profile` plus structured replay evidence.

Patch 8 does not alter these persistence or result schemas. It makes Diagnostics consume
them consistently.

==================================================
PROFILE / FINAL REPLAY CONTRACT
==================================================

Supported final protocol profiles:

- TLS 1.3 — TCP/443, TLS L7;
- TLS 1.2 — TCP/443, TLS L7;
- HTTP — TCP/80, HTTP L7;
- QUIC — UDP/443, QUIC L7 in the current `_31` implementation only; the approved
  adaptive-search target removes QUIC candidate search and retains only the fixed precheck;
- generic UDP — validated configured port, no L7 filter, validated job-local payload.

In the current `_31` implementation each published profile contains one transport filter,
optional protocol L7 filter, one validated target selector, the candidate's optional
input/output range data, and the candidate desynchronization fragment. `-d8`, `-d10` and
absence are preserved exactly rather than inserted by shell. Runtime-only arguments,
nested selectors/filters,
placeholders and `--new` are rejected.

The adaptive-search target explicitly supersedes fixed `-d10`: `out-range` becomes
optional candidate data represented by `CandidateSpec`, and final profile replay must
preserve the exact range (or absence of range) that was actually tested.

Each final source is replayed exactly three times. A shortlist entry is accepted only when
all three attempts pass and each replay proves the exact complete published profile was
used.

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
4. Keep candidate identity, traffic effects and evidence deterministically isolated.
5. Keep temporary firewall/divert ownership isolated.
6. The current cold reference cleans candidate runtime before the next candidate; a
   future warm model may reuse job-owned runtime only after the A/B/C experiment proves
   cold-result equivalence, deterministic dispatch and no state leakage.
7. Execute Stage 90 on normal completion, timeout, cancel, signal or internal error.
8. Restore initial RUNNING to healthy RUNNING and initial STOPPED to STOPPED.
9. Never hide restoration failure behind a successful result.
10. Saved Traffic Strategy remains immutable.
11. Final profile replay uses the same unified candidate readiness/interception/cleanup owner.
12. Private circular sessions cannot mutate the parent automated result.
13. Long-lived automated or circular workers must not inherit short launcher serialization locks.

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

Patches 4–7 replaced several old backend mechanisms. Patch 8 `_25` adds focused source
reconciliation for the launcher-lock and GUI/status presentation mechanisms. None of these
owner-observed defects is closed until replacement live evidence exists.

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
  **COMPLETE / `_24`**.
- Patch 8 — GUI/status reconciliation and post-migration live gate: **COMPLETE / `_25`**.
- Corrective `_26` — Stage-50 candidate-local failure isolation: **COMPLETE / live closure
  proven by `_27` Scenario 1**.
- Corrective `_27` — Stage-40 DNS/stage deadline correction: **COMPLETE / owner Scenario 1
  live PASS; promoted into v0.4.0**.
- Adaptive-search `_28` — remove Stage-50 accepted-family hard gating while preserving
  accepted-first evidence priority: **COMPLETE / PUBLISHED AND OWNER-TESTED `v0.4.0_2`**.
- Adaptive-search `_29` — immutable normalized `CandidateSpec`, job-scoped installed
  `ResourceInventory`, exact Python rendering and active shell-adapter policy cleanup:
  **COMPLETE / `0.4.0_3` SOURCE**.
- Adaptive-search `_30` — native Zapret2 DAG, golden corpus, semantic resource branches
  and candidate-defined range preservation:
  **COMPLETE / `0.4.0_4` SOURCE**.
- Adaptive-search `_31` — live-evidence ordering, fixed endpoint epoch, two-to-three
  winners and timing telemetry:
  **CURRENT `0.4.0_5` SOURCE CANDIDATE / LIVE NOT CLAIMED**.

The remaining approved search-quality source sequence is `_32`–`_33` in
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` and `docs/ROADMAP.md`.

==================================================
PATCH 8 VERIFICATION
==================================================

Patch 8 source qualification requires all earlier migration regressions plus:

- automated daemon launch closes launcher FD 9;
- empty/invalid configd and AJAX failures are classified as transient reads;
- GUI renders automated state only from validated persisted job snapshots;
- transport status cannot masquerade as job state;
- active polling preserves the last valid state/progress and retries transient reads;
- accepted starts present queued Stage 00 until persisted state arrives;
- active reload resumes work, transient discovery retries, and explicit idle remains idle;
- private circular presentation remains stable across transient/busy reads;
- deliberate RU/EN transient status messaging;
- complete authoritative Strategy Lab corrective matrix;
- full repository CI/governance/hygiene checks;
- FreeBSD 15 package/content/manifest verification.

The focused regression is
`scripts/test-strategy-lab-gui-status-reconciliation.sh`.

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

Patches 2–7 satisfy this rule for the complete automated backend path. Patch 8 does not
alter that ownership; it reconciles presentation with the existing persisted state.

==================================================
HANDOFF TO POST-MIGRATION LIVE GATE
==================================================

After `_25` passes latest-head CI and FreeBSD 15 qualification and is squash-merged:

1. keep `_17` as the latest owner-tested evidence until a new candidate is actually tested;
2. publish `_25` only with explicit owner publication authority;
3. install the exact verified FreeBSD 15 package on the owner's OPNsense appliance;
4. resume Scenario 1 with `rutracker.org` and initial Zapret2 RUNNING;
5. capture GUI screenshot, final `status.json`, service/process/IPFW initial/final evidence,
   and candidate runtime log if a failure occurs;
6. close only defects proven by new evidence and repeat all affected/required live rows;
7. keep stable release and pkg-repository promotion blocked until the required live matrix
   is PASS.
